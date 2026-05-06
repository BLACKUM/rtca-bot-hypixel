import time
from aiohttp import web
from core.logger import log_info, log_error
from services.ban_manager import ban_manager
from services.request_log import request_log


def get_client_ip(request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote


class RateLimiter:
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60
        self.requests = {}
        self.last_cleanup = time.time()

    def is_rate_limited(self, ip):
        current_time = time.time()

        if current_time - self.last_cleanup > 60:
            self.last_cleanup = current_time
            for key in list(self.requests.keys()):
                self.requests[key] = [t for t in self.requests[key] if t > current_time - self.window_size]
                if not self.requests[key]:
                    del self.requests[key]

        if ip not in self.requests:
            self.requests[ip] = []

        self.requests[ip] = [t for t in self.requests[ip] if t > current_time - self.window_size]

        if len(self.requests[ip]) >= self.requests_per_minute:
            return True

        self.requests[ip].append(current_time)
        return False

    @web.middleware
    async def middleware(self, request, handler):
        ip = get_client_ip(request)
        method = request.method
        path = request.path
        query = request.query_string

        ban_entry = ban_manager.get_ban(ip)
        if ban_entry:
            log_error(f"Banned IP rejected: {ip} on {path} (reason: {ban_entry.get('reason')})")
            request_log.add(ip, method, path, query, 403)
            return web.json_response(
                {
                    "error": "Forbidden",
                    "message": "Your IP has been banned from this API.",
                    "reason": ban_entry.get("reason", "No reason provided"),
                },
                status=403,
            )

        if ip != "127.0.0.1" and self.is_rate_limited(ip):
            log_error(f"Rate limit exceeded for IP: {ip} on {path}")
            request_log.add(ip, method, path, query, 429)
            return web.json_response(
                {"error": "Too Many Requests", "message": "Rate limit exceeded. Please try again in a minute."},
                status=429
            )

        try:
            response = await handler(request)
            status = getattr(response, "status", 0)
            request_log.add(ip, method, path, query, status)
            return response
        except web.HTTPException as exc:
            request_log.add(ip, method, path, query, exc.status)
            raise
        except Exception:
            request_log.add(ip, method, path, query, 500)
            raise


class EndpointRateLimiter:
    def __init__(self, requests_per_window: int, window_seconds: int, name: str = "endpoint"):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.name = name
        self.requests: dict = {}

    def check(self, ip: str) -> tuple:
        current_time = time.time()
        timestamps = [t for t in self.requests.get(ip, []) if t > current_time - self.window_seconds]

        if len(timestamps) >= self.requests_per_window:
            oldest = min(timestamps)
            retry_after = int(self.window_seconds - (current_time - oldest)) + 1
            self.requests[ip] = timestamps
            return False, max(retry_after, 1)

        timestamps.append(current_time)
        self.requests[ip] = timestamps
        return True, 0


rate_limiter = RateLimiter(requests_per_minute=60)
solo_clear_limiter = EndpointRateLimiter(requests_per_window=1, window_seconds=60, name="solo_clear_ip")
solo_clear_uuid_limiter = EndpointRateLimiter(requests_per_window=1, window_seconds=60, name="solo_clear_uuid")

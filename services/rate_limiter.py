import time
from typing import Tuple
from aiohttp import web
from core.logger import log_info, log_error
from services.ban_manager import ban_manager
from services.request_log import request_log, sanitize_headers, sanitize_text


def get_client_ip(request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote


MAX_LOG_BODY_READ = 8192
MAX_LOG_BODY_PREVIEW = 500


async def build_request_details(request) -> Tuple[dict, str]:
    body_preview = ""
    content_length = request.content_length or 0

    if request.can_read_body and content_length and content_length <= MAX_LOG_BODY_READ:
        body = await request.read()
        content_type = (request.content_type or "").lower()
        if body:
            if "json" in content_type or content_type.startswith("text/") or "form" in content_type:
                body_preview = body.decode("utf-8", errors="replace")[:MAX_LOG_BODY_PREVIEW]
            else:
                body_preview = f"<{len(body)} bytes {request.content_type or 'binary'}>"
    elif request.can_read_body and content_length > MAX_LOG_BODY_READ:
        body_preview = f"<body omitted: {content_length} bytes>"

    peer = None
    if request.transport:
        peer = request.transport.get_extra_info("peername")

    details = {
        "scheme": request.scheme,
        "host": sanitize_text(request.host, 160),
        "remote": sanitize_text(request.remote, 80),
        "forwarded_for": sanitize_text(request.headers.get("X-Forwarded-For", ""), 240),
        "real_ip": sanitize_text(request.headers.get("X-Real-IP", ""), 80),
        "peer": f"{peer[0]}:{peer[1]}" if isinstance(peer, tuple) and len(peer) >= 2 else "",
        "user_agent": sanitize_text(request.headers.get("User-Agent", ""), 240),
        "referer": sanitize_text(request.headers.get("Referer", ""), 240),
        "origin": sanitize_text(request.headers.get("Origin", ""), 160),
        "content_type": sanitize_text(request.content_type or "", 120),
        "content_length": content_length,
        "headers": sanitize_headers(request.headers),
    }
    return details, body_preview


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
        details, body_preview = await build_request_details(request)

        ban_entry = ban_manager.get_ban(ip)
        if ban_entry:
            log_error(f"Banned IP rejected: {ip} on {path} (reason: {ban_entry.get('reason')})")
            details["blocked_reason"] = f"banned: {ban_entry.get('reason', 'No reason provided')}"
            request_log.add(ip, method, path, query, 403, body_preview=body_preview, details=details)
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
            details["blocked_reason"] = "rate limited"
            request_log.add(ip, method, path, query, 429, body_preview=body_preview, details=details)
            return web.json_response(
                {"error": "Too Many Requests", "message": "Rate limit exceeded. Please try again in a minute."},
                status=429
            )

        try:
            response = await handler(request)
            status = getattr(response, "status", 0)
            details["response_content_type"] = response.headers.get("Content-Type", "")
            details["response_content_length"] = response.headers.get("Content-Length", "")
            request_log.add(ip, method, path, query, status, body_preview=body_preview, details=details)
            return response
        except web.HTTPException as exc:
            details["exception"] = exc.reason or exc.__class__.__name__
            request_log.add(ip, method, path, query, exc.status, body_preview=body_preview, details=details)
            raise
        except Exception:
            details["exception"] = "Unhandled server error"
            request_log.add(ip, method, path, query, 500, body_preview=body_preview, details=details)
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

import time
from aiohttp import web
from core.logger import log_info, log_error

class RateLimiter:
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60
        self.requests = {}

    def is_rate_limited(self, ip):
        current_time = time.time()
        
        if ip not in self.requests:
            self.requests[ip] = []
            
        self.requests[ip] = [t for t in self.requests[ip] if t > current_time - self.window_size]
        
        if len(self.requests[ip]) >= self.requests_per_minute:
            return True
            
        self.requests[ip].append(current_time)
        return False

    @web.middleware
    async def middleware(self, request, handler):
        ip = request.remote
        
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()

        if ip == "127.0.0.1":
            return await handler(request)

        if self.is_rate_limited(ip):
            log_error(f"Rate limit exceeded for IP: {ip} on {request.path}")
            return web.json_response(
                {"error": "Too Many Requests", "message": "Rate limit exceeded. Please try again in a minute."},
                status=429
            )
            
        return await handler(request)

rate_limiter = RateLimiter(requests_per_minute=60)

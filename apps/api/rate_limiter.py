"""In-memory rate limiter for API endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter based on client IP.

    Args:
        requests_per_minute: Max requests per IP per minute.
        burst: Max burst requests allowed.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 30,
        burst: int = 5,
    ):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst
        # Store: {ip: (request_count, window_start)}
        self._store: Dict[str, Tuple[int, float]] = {}
        self._window = 60.0  # 1 minute window

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _check_rate_limit(self, ip: str) -> Tuple[bool, int]:
        """Check if the IP is within rate limit.

        Returns:
            Tuple of (allowed, retry_after_seconds).
        """
        now = time.time()

        if ip not in self._store:
            self._store[ip] = (1, now)
            return True, 0

        count, window_start = self._store[ip]
        elapsed = now - window_start

        if elapsed >= self._window:
            # New window
            self._store[ip] = (1, now)
            return True, 0

        if count >= self.rpm:
            retry_after = int(self._window - elapsed) + 1
            return False, retry_after

        self._store[ip] = (count + 1, window_start)
        return True, 0

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        ip = self._get_client_ip(request)
        allowed, retry_after = self._check_rate_limit(ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "ok": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后再试",
                        "detail": f"每分钟最多 {self.rpm} 次请求",
                    },
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)

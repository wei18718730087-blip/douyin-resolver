"""Global error handling middleware for FastAPI."""

from __future__ import annotations

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from apps.api.routes.metrics import record_request

logger = logging.getLogger("douyin-resolver")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch-all error handler that returns structured JSON errors."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.time()
        endpoint = request.url.path

        try:
            response = await call_next(request)
            elapsed = time.time() - start

            # Record metrics
            is_error = response.status_code >= 400
            record_request(endpoint, is_error=is_error)

            # Log request
            logger.info(
                f"{request.method} {endpoint} "
                f"status={response.status_code} "
                f"elapsed={elapsed:.3f}s"
            )

            return response

        except Exception as e:
            elapsed = time.time() - start
            record_request(endpoint, is_error=True)
            logger.error(
                f"{request.method} {endpoint} "
                f"error={type(e).__name__}: {e} "
                f"elapsed={elapsed:.3f}s",
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "服务器内部错误",
                        "detail": str(e) if logger.isEnabledFor(logging.DEBUG) else None,
                    },
                },
            )

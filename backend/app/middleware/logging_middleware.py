"""Structured HTTP request/response logging middleware (TPRD-012)."""

from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# Paths excluded from request logging (too noisy / health checks)
_LOG_EXCLUDE_PATHS = frozenset({"/health", "/ready", "/metrics"})


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request and response in structured JSON format.

    Emits one log line per request containing:
    - http.method, http.path, http.status_code
    - duration_ms (total wall-clock time)
    - request_id (propagated from RequestIDMiddleware via structlog context)
    - client.ip (from X-Forwarded-For or direct remote address)

    Per TPRD-012: log lines are emitted at INFO level for 2xx/3xx, WARNING
    for 4xx, and ERROR for 5xx responses.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _LOG_EXCLUDE_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        client_ip = self._get_client_ip(request)

        response: Response | None = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "unhandled exception",
                http_method=request.method,
                http_path=request.url.path,
                http_status_code=500,
                duration_ms=duration_ms,
                client_ip=client_ip,
            )
            raise exc from exc
        else:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Process-Time"] = f"{duration_ms}ms"

            log_kwargs = {
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            }

            if status_code >= 500:
                logger.error("http request", **log_kwargs)
            elif status_code >= 400:
                logger.warning("http request", **log_kwargs)
            else:
                logger.info("http request", **log_kwargs)

            return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract the real client IP, honouring X-Forwarded-For if present."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


__all__ = ["LoggingMiddleware"]

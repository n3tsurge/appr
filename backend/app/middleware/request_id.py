"""Request ID middleware for correlation and tracing."""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import bind_request_context, clear_request_context

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every HTTP request.

    Behaviour:
    1. Read the ``X-Request-ID`` header from the incoming request.
    2. If absent, generate a new UUID4.
    3. Bind the request ID to structlog contextvars so it appears in all log
       lines emitted during request processing.
    4. Set the ``X-Request-ID`` header on the outgoing response.
    5. Clear the structlog contextvars after the response is sent.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Expose on request state for downstream code that needs it
        request.state.request_id = request_id

        bind_request_context(request_id=request_id)

        try:
            response: Response = await call_next(request)
        finally:
            clear_request_context()

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


__all__ = ["RequestIDMiddleware"]

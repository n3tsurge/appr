"""Tenant extraction middleware."""

from __future__ import annotations

import uuid

import structlog
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Paths that do not require tenant resolution
_EXEMPT_PREFIXES = (
    "/health",
    "/ready",
    "/api/v1/auth/",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract and bind the tenant ID from the JWT access token.

    Sets ``request.state.tenant_id`` (``uuid.UUID | None``) for every request.
    Exempt paths (login, health, docs) are passed through without inspection.

    The tenant ID is taken from the ``tenant_id`` claim in the JWT payload.
    If the token is absent or invalid, ``request.state.tenant_id`` is set to
    ``None`` – downstream route guards are responsible for enforcing access.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_id: uuid.UUID | None = None

        if not any(request.url.path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            token = self._extract_bearer_token(request)
            if token:
                tenant_id = self._resolve_tenant_id(token)

        request.state.tenant_id = tenant_id
        return await call_next(request)

    @staticmethod
    def _extract_bearer_token(request: Request) -> str | None:
        """Return the raw JWT string from the Authorization header, or None."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[len("Bearer "):]
        return None

    @staticmethod
    def _resolve_tenant_id(token: str) -> uuid.UUID | None:
        """Decode the token (without full verification) to extract tenant_id.

        We perform a lightweight options-only decode here; full signature
        verification is done in the ``get_current_user`` dependency.
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_PUBLIC_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            raw = payload.get("tenant_id")
            if raw:
                return uuid.UUID(str(raw))
        except (JWTError, ValueError, AttributeError) as exc:
            logger.debug("tenant middleware: could not decode tenant from token", error=str(exc))
        return None


__all__ = ["TenantMiddleware"]

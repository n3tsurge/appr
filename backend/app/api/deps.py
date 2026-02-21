"""FastAPI dependency injection utilities."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import RedisClient, get_redis
from app.core.security import verify_token
from app.models.enums import UserRole
from app.models.user import User

logger = structlog.get_logger(__name__)

# Re-export for convenience
DbSession = Annotated[AsyncSession, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="BearerJWT",
    auto_error=False,  # We handle 401 ourselves for better error messages
)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate the Bearer JWT and return the authenticated User.

    Raises:
        HTTPException 401: If the token is absent, invalid, or the user does
            not exist / is inactive.
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token, expected_type="access")
    user_id_str: str | None = payload.get("sub")

    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: malformed subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        logger.warning("auth: user not found", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning("auth: inactive user attempted login", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


# Convenience type alias
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole) -> Callable[[User], User]:
    """Return a dependency that enforces at least one of the specified roles.

    Usage::

        @router.delete("/services/{id}")
        async def delete_service(
            user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.editor))],
            ...
        ) -> ...:
            ...
    """

    async def _check_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions. Required role(s): "
                    f"{', '.join(r.value for r in roles)}"
                ),
            )
        return current_user

    return _check_role  # type: ignore[return-value]


def get_current_tenant_id(request: Request) -> uuid.UUID:
    """Extract the tenant ID set by TenantMiddleware.

    Raises:
        HTTPException 401: If no tenant ID is bound on the request.
    """
    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to determine tenant from authentication token",
        )
    return tenant_id


# Convenience type aliases
CurrentTenantId = Annotated[uuid.UUID, Depends(get_current_tenant_id)]

__all__ = [
    "CurrentTenantId",
    "CurrentUser",
    "DbSession",
    "RedisClient",
    "get_current_tenant_id",
    "get_current_user",
    "get_db",
    "get_redis",
    "require_role",
]

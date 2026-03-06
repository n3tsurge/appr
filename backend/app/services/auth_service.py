"""Authentication and token management service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_token,
    verify_password,
    verify_token,
)
from app.models.enums import AuthProvider, UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse

logger = structlog.get_logger(__name__)

# Rate limiting: 5 failures per 60 seconds per email
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 60  # seconds
_PKCE_TTL = 600  # 10 minutes


def _rate_limit_key(email: str) -> str:
    return f"auth:login_failures:{email.lower()}"


def _pkce_key(state: str) -> str:
    return f"auth:pkce:{state}"


class AuthService:
    """Handles local login, token rotation, logout, and SSO user provisioning."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self._db = db
        self._redis = redis

    # ------------------------------------------------------------------
    # Local authentication
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate with email/password and return a JWT token pair.

        Raises:
            HTTPException 429: if rate limit exceeded.
            HTTPException 401: if credentials are invalid.
        """
        await self._check_rate_limit(email)

        user = await self._get_user_by_email(email)

        # Deliberately use the same error for "not found" and "wrong password"
        if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
            await self._record_failure(email)
            logger.warning("auth.login_failed", email=email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Clear failure counter on success
        await self._redis.delete(_rate_limit_key(email))

        # Update last login
        user.last_login_at = datetime.now(tz=timezone.utc)
        self._db.add(user)

        logger.info("auth.login_success", user_id=str(user.id), email=email)
        return await self.create_token_response(user)

    # ------------------------------------------------------------------
    # Token rotation
    # ------------------------------------------------------------------

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Validate a refresh token and issue a rotated pair.

        If a *revoked* refresh token is presented, all tokens for that user
        are revoked (compromise detection).

        Raises:
            HTTPException 401: on any token validation failure.
        """
        try:
            payload = verify_token(refresh_token, expected_type="refresh")
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_hash = hash_token(refresh_token)
        result = await self._db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        db_token: RefreshToken | None = result.scalar_one_or_none()

        if db_token is None:
            logger.warning("auth.refresh_token_not_found", hash=token_hash[:8])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not recognised",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if db_token.revoked_at is not None:
            # Token reuse – revoke ALL tokens for this user
            logger.warning(
                "auth.refresh_token_reuse_detected",
                user_id=str(db_token.user_id),
            )
            await self._revoke_all_user_tokens(db_token.user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected; all sessions revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not db_token.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Revoke old token
        db_token.revoked_at = datetime.now(tz=timezone.utc)
        self._db.add(db_token)

        # Load user
        user = await self._db.get(User, db_token.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info("auth.token_rotated", user_id=str(user.id))
        return await self.create_token_response(user)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(self, refresh_token: str) -> None:
        """Revoke the given refresh token."""
        token_hash = hash_token(refresh_token)
        result = await self._db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        db_token: RefreshToken | None = result.scalar_one_or_none()
        if db_token and db_token.revoked_at is None:
            db_token.revoked_at = datetime.now(tz=timezone.utc)
            self._db.add(db_token)
            logger.info("auth.logout", user_id=str(db_token.user_id))

    # ------------------------------------------------------------------
    # SSO user provisioning
    # ------------------------------------------------------------------

    async def get_or_create_sso_user(
        self,
        *,
        email: str,
        display_name: str,
        external_id: str,
        provider: AuthProvider,
        tenant_id: uuid.UUID,
    ) -> User:
        """Find or create a user for an SSO login.

        On subsequent SSO logins the display name and last_login_at are updated.
        """
        # Try to find by external_id + provider first
        result = await self._db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.auth_provider == provider,
                User.external_id == external_id,
                User.deleted_at.is_(None),
            )
        )
        user: User | None = result.scalar_one_or_none()

        if user is None:
            # Fall back to email match within tenant
            result = await self._db.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.email == email.lower(),
                    User.deleted_at.is_(None),
                )
            )
            user = result.scalar_one_or_none()

        if user is None:
            # Create new SSO user
            user = User(
                tenant_id=tenant_id,
                email=email.lower(),
                display_name=display_name,
                auth_provider=provider,
                external_id=external_id,
                role=UserRole.viewer,
                is_active=True,
            )
            self._db.add(user)
            await self._db.flush()
            logger.info(
                "auth.sso_user_created",
                user_id=str(user.id),
                provider=provider.value,
                email=email,
            )
        else:
            # Update mutable SSO fields
            user.display_name = display_name
            user.external_id = external_id
            user.auth_provider = provider
            self._db.add(user)

        user.last_login_at = datetime.now(tz=timezone.utc)
        return user

    # ------------------------------------------------------------------
    # Token creation
    # ------------------------------------------------------------------

    async def create_token_response(self, user: User) -> TokenResponse:
        """Issue a new JWT access+refresh pair and persist the refresh token hash."""
        claims: dict[str, Any] = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "email": user.email,
        }
        access_token = create_access_token(claims)
        refresh_token_str = create_refresh_token({"sub": str(user.id)})

        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token_str),
            expires_at=expires_at,
        )
        self._db.add(db_token)
        await self._db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self._db.execute(
            select(User).where(
                User.email == email.lower(),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _check_rate_limit(self, email: str) -> None:
        key = _rate_limit_key(email)
        count_raw = await self._redis.get(key)
        count = int(count_raw) if count_raw else 0
        if count >= _RATE_LIMIT_MAX:
            logger.warning("auth.rate_limit_exceeded", email=email)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please try again later.",
            )

    async def _record_failure(self, email: str) -> None:
        key = _rate_limit_key(email)
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, _RATE_LIMIT_WINDOW)
        await pipe.execute()

    async def _revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        now = datetime.now(tz=timezone.utc)
        await self._db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )


__all__ = ["AuthService"]

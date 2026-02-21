"""JWT and password security utilities."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------
_ALGORITHM = settings.JWT_ALGORITHM
_ACCESS_TOKEN_EXPIRE = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
_REFRESH_TOKEN_EXPIRE = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed RS256 JWT access token.

    Args:
        data: Claims to embed in the token payload.
        expires_delta: Optional custom expiry; defaults to 15 minutes.

    Returns:
        Encoded JWT string.
    """
    expire = _now_utc() + (expires_delta or _ACCESS_TOKEN_EXPIRE)
    payload: dict[str, Any] = {
        **data,
        "exp": expire,
        "iat": _now_utc(),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm=_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a signed RS256 JWT refresh token with a 7-day TTL.

    Args:
        data: Claims to embed; typically contains ``sub`` (user id) and ``tid`` (tenant id).

    Returns:
        Encoded JWT string.
    """
    expire = _now_utc() + _REFRESH_TOKEN_EXPIRE
    payload: dict[str, Any] = {
        **data,
        "exp": expire,
        "iat": _now_utc(),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm=_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: Raw JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        HTTPException: 401 when the token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT validation failed", error=str(exc))
        raise credentials_exception from exc


def hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of a token for safe storage."""
    return hashlib.sha256(token.encode()).hexdigest()

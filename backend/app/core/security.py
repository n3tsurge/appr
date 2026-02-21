"""JWT token creation/verification and password hashing utilities."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
_ALGORITHM = settings.JWT_ALGORITHM
_PRIVATE_KEY = settings.JWT_PRIVATE_KEY
_PUBLIC_KEY = settings.JWT_PUBLIC_KEY


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed RS256 JWT access token.

    Args:
        data: Claims to embed (must include ``sub`` as a string user ID).
        expires_delta: Custom TTL; defaults to
            ``settings.ACCESS_TOKEN_EXPIRE_MINUTES`` minutes.

    Returns:
        Encoded JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = _utcnow()
    payload: dict[str, Any] = {
        **data,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a signed RS256 JWT refresh token with a 7-day TTL.

    Args:
        data: Claims to embed (must include ``sub`` as a string user ID).

    Returns:
        Encoded JWT string.
    """
    now = _utcnow()
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        **data,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=_ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: Raw JWT string.
        expected_type: ``"access"`` or ``"refresh"``.

    Returns:
        Decoded payload dictionary.

    Raises:
        HTTPException 401 on any validation failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(token, _PUBLIC_KEY, algorithms=[_ALGORITHM])
    except JWTError as exc:
        logger.warning("jwt decode failed", error=str(exc))
        raise credentials_exception from exc

    if payload.get("type") != expected_type:
        logger.warning(
            "jwt type mismatch",
            expected=expected_type,
            got=payload.get("type"),
        )
        raise credentials_exception

    if payload.get("sub") is None:
        logger.warning("jwt missing sub claim")
        raise credentials_exception

    return payload


def hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of a token (for database storage)."""
    return hashlib.sha256(token.encode()).hexdigest()


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_password_hash",
    "verify_password",
    "hash_token",
]

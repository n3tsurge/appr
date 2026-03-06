"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AuthProvider, UserRole


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Credentials for local (email + password) authentication."""

    email: EmailStr = Field(description="User's email address")
    password: str = Field(min_length=8, description="Plain-text password (transmitted over TLS)")

    model_config = {"json_schema_extra": {"examples": [
        {"email": "admin@example.com", "password": "supersecret123"}
    ]}}


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str = Field(description="Valid refresh token issued by a previous login")


class LogoutRequest(BaseModel):
    """Request body for explicit logout (token revocation)."""

    refresh_token: str = Field(description="Refresh token to revoke")


class OktaCallbackRequest(BaseModel):
    """Okta / generic OIDC authorization code callback payload."""

    code: str = Field(description="Authorization code from the identity provider")
    state: str = Field(description="CSRF state parameter")
    redirect_uri: str = Field(description="Redirect URI used in the authorization request")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    """Successful authentication response containing JWT tokens."""

    access_token: str = Field(description="Short-lived JWT access token (RS256)")
    refresh_token: str = Field(description="Long-lived JWT refresh token for rotation")
    token_type: str = Field(default="Bearer")
    expires_in: int = Field(description="Access token TTL in seconds")


class UserRead(BaseModel):
    """Public representation of a user (returned after login or profile fetch)."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    auth_provider: AuthProvider
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SAMLCallbackRequest(BaseModel):
    """SAML 2.0 Assertion Consumer Service POST body."""

    SAMLResponse: str = Field(description="Base64-encoded SAML response from the IdP")
    RelayState: str | None = Field(default=None, description="Relay state passed through the flow")


__all__ = [
    "LoginRequest",
    "LogoutRequest",
    "OktaCallbackRequest",
    "RefreshRequest",
    "SAMLCallbackRequest",
    "TokenResponse",
    "UserRead",
]

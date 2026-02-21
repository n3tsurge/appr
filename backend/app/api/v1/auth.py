"""Authentication route handlers — TPRD-003."""

from __future__ import annotations

import secrets
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    DbSession,
    get_current_user,
    get_redis,
)
from app.core.config import settings
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    OktaCallbackRequest,
    RefreshRequest,
    SAMLCallbackRequest,
    TokenResponse,
    UserRead,
)
from app.schemas.common import ApiResponse, ProblemDetail
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.oidc_service import OIDCService

logger = structlog.get_logger(__name__)

router = APIRouter()


def _get_client_meta(request: Request) -> tuple[str | None, str | None]:
    """Extract IP address and User-Agent from the request."""
    ip = request.headers.get("X-Forwarded-For") or request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    return ip, ua


def _request_id(request: Request) -> str | None:
    return getattr(getattr(request, "state", None), "request_id", None)


# ---------------------------------------------------------------------------
# Local auth
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Local email/password login",
    responses={
        401: {"model": ProblemDetail},
        429: {"model": ProblemDetail},
    },
)
async def login(
    body: LoginRequest,
    request: Request,
    db: DbSession,
    redis=Depends(get_redis),
) -> TokenResponse:
    """Authenticate with email and password, returning JWT access + refresh tokens."""
    svc = AuthService(db, redis)
    tokens = await svc.login(body.email, body.password)

    # Audit log — need the user for tenant_id
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(
        select(User).where(User.email == body.email.lower(), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user:
        ip, ua = _get_client_meta(request)
        audit = AuditService(db)
        await audit.log_login(
            tenant_id=user.tenant_id,
            user_id=user.id,
            auth_provider=user.auth_provider.value,
            ip_address=ip,
            user_agent=ua,
            request_id=_request_id(request),
        )
        await db.commit()

    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token",
    responses={401: {"model": ProblemDetail}},
)
async def refresh(
    body: RefreshRequest,
    db: DbSession,
    redis=Depends(get_redis),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    svc = AuthService(db, redis)
    tokens = await svc.refresh_tokens(body.refresh_token)
    await db.commit()
    return tokens


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke refresh token",
)
async def logout(
    body: LogoutRequest,
    request: Request,
    db: DbSession,
    redis=Depends(get_redis),
    current_user: CurrentUser = Depends(get_current_user),  # type: ignore[assignment]
) -> Response:
    """Revoke the provided refresh token and record a logout audit event."""
    svc = AuthService(db, redis)
    await svc.logout(body.refresh_token)

    ip, ua = _get_client_meta(request)
    audit = AuditService(db)
    await audit.log_logout(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        request_id=_request_id(request),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=ApiResponse[UserRead],
    summary="Get current user profile",
)
async def me(current_user: CurrentUser) -> ApiResponse[UserRead]:
    """Return the authenticated user's profile."""
    return ApiResponse(data=UserRead.model_validate(current_user))


# ---------------------------------------------------------------------------
# OIDC / OAuth2
# ---------------------------------------------------------------------------


@router.get(
    "/oidc/authorize",
    summary="Initiate OIDC authorization flow",
)
async def oidc_authorize(
    request: Request,
    redirect_uri: str,
    db: DbSession,
    redis=Depends(get_redis),
) -> dict[str, str]:
    """Generate an OIDC authorization URL with PKCE and return it."""
    if not settings.AUTH_SSO_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO is not enabled",
        )
    state = secrets.token_urlsafe(32)
    svc = OIDCService(db, redis)
    url = await svc.get_authorization_url(state=state, redirect_uri=redirect_uri)
    return {"authorization_url": url, "state": state}


@router.get(
    "/oidc/callback",
    response_model=TokenResponse,
    summary="OIDC authorization code callback",
    responses={400: {"model": ProblemDetail}, 502: {"model": ProblemDetail}},
)
async def oidc_callback(
    request: Request,
    code: str,
    state: str,
    redirect_uri: str,
    db: DbSession,
    redis=Depends(get_redis),
) -> TokenResponse:
    """Handle the OIDC provider callback and exchange the code for AppR tokens."""
    if not settings.AUTH_SSO_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO is not enabled",
        )

    # Derive tenant from request state (set by TenantMiddleware)
    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        tenant_id = uuid.UUID(settings.DEFAULT_TENANT_ID)

    svc = OIDCService(db, redis)
    tokens = await svc.exchange_code(
        code=code,
        state=state,
        redirect_uri=redirect_uri,
        tenant_id=tenant_id,
    )
    await db.commit()
    return tokens


# ---------------------------------------------------------------------------
# SAML 2.0
# ---------------------------------------------------------------------------


@router.get(
    "/saml/metadata",
    summary="SAML SP metadata",
    response_class=Response,
)
async def saml_metadata() -> Response:
    """Return SAML Service Provider metadata XML."""
    # Build minimal SP metadata without a fully configured IdP
    entity_id = settings.SAML_SP_ENTITY_ID
    acs_url = settings.SAML_SP_ACS_URL
    xml = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{entity_id}">
  <md:SPSSODescriptor
      AuthnRequestsSigned="false"
      WantAssertionsSigned="true"
      protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="{acs_url}"
        index="1"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    return Response(content=xml, media_type="application/xml")


@router.post(
    "/saml/acs",
    response_model=TokenResponse,
    summary="SAML Assertion Consumer Service",
    responses={400: {"model": ProblemDetail}},
)
async def saml_acs(
    body: SAMLCallbackRequest,
    request: Request,
    db: DbSession,
    redis=Depends(get_redis),
) -> TokenResponse:
    """Process a SAML assertion and issue AppR tokens.

    Full SAML assertion validation requires a configured IdP. This stub
    validates that the endpoint is reachable and returns a clear error when
    SAML is not configured.
    """
    if not settings.SAML_IDP_METADATA_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAML IdP is not configured",
        )

    # Production SAML validation would use python3-saml here.
    # Stub: raise 501 to signal not fully implemented in this environment.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="SAML ACS handler requires IdP configuration. Set SAML_IDP_METADATA_URL.",
    )


__all__ = ["router"]

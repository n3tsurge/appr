"""OIDC/OAuth2 SSO service using Authlib."""

from __future__ import annotations

import secrets
import uuid

import structlog
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import AuthProvider
from app.schemas.auth import TokenResponse
from app.services.auth_service import AuthService, _pkce_key

logger = structlog.get_logger(__name__)

_PKCE_TTL = 600  # 10 minutes


def _get_provider_config() -> tuple[str, str, str, AuthProvider]:
    """Return (issuer, client_id, client_secret, provider_enum) for the configured IdP."""
    if settings.OKTA_DOMAIN:
        issuer = f"https://{settings.OKTA_DOMAIN}/oauth2/default"
        return issuer, settings.OKTA_CLIENT_ID, settings.OKTA_CLIENT_SECRET, AuthProvider.okta
    if settings.OIDC_ISSUER:
        return settings.OIDC_ISSUER, settings.OIDC_CLIENT_ID, settings.OIDC_CLIENT_SECRET, AuthProvider.oidc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No OIDC provider configured",
    )


class OIDCService:
    """Handles OIDC/OAuth2 authorization URL generation and code exchange."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self._db = db
        self._redis = redis

    async def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
    ) -> str:
        """Build and return the OIDC authorization URL with PKCE.

        Stores the code_verifier in Redis keyed by *state* (TTL 10 min).
        """
        issuer, client_id, _, _ = _get_provider_config()

        # Generate PKCE pair
        code_verifier = secrets.token_urlsafe(96)
        await self._redis.setex(_pkce_key(state), _PKCE_TTL, code_verifier)

        async with AsyncOAuth2Client(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope="openid email profile",
        ) as client:
            url, _ = client.create_authorization_url(
                f"{issuer}/v1/authorize" if settings.OKTA_DOMAIN else f"{issuer}/authorize",
                state=state,
                code_challenge_method="S256",
                code_verifier=code_verifier,
            )

        logger.info("oidc.authorization_url_generated", state=state[:8])
        return url

    async def exchange_code(
        self,
        code: str,
        state: str,
        redirect_uri: str,
        tenant_id: uuid.UUID,
    ) -> TokenResponse:
        """Exchange an authorization code for tokens, then issue AppR JWTs.

        Steps:
        1. Retrieve code_verifier from Redis.
        2. Exchange code at IdP token endpoint.
        3. Fetch userinfo.
        4. Upsert SSO user.
        5. Return AppR token pair.
        """
        issuer, client_id, client_secret, provider = _get_provider_config()

        # Retrieve PKCE verifier
        code_verifier = await self._redis.get(_pkce_key(state))
        if not code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state parameter",
            )
        await self._redis.delete(_pkce_key(state))

        token_url = (
            f"{issuer}/v1/token" if settings.OKTA_DOMAIN else f"{issuer}/token"
        )
        userinfo_url = (
            f"{issuer}/v1/userinfo" if settings.OKTA_DOMAIN else f"{issuer}/userinfo"
        )

        try:
            async with AsyncOAuth2Client(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            ) as client:
                token = await client.fetch_token(
                    token_url,
                    code=code,
                    code_verifier=code_verifier,
                )
                client.token = token
                userinfo_resp = await client.get(userinfo_url)
                userinfo_resp.raise_for_status()
                userinfo = userinfo_resp.json()
        except Exception as exc:
            logger.warning("oidc.code_exchange_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OIDC token exchange failed: {exc}",
            ) from exc

        email: str = userinfo.get("email", "")
        display_name: str = userinfo.get("name") or userinfo.get("preferred_username") or email
        external_id: str = userinfo.get("sub", "")

        if not email or not external_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC userinfo missing required claims (email, sub)",
            )

        auth_svc = AuthService(self._db, self._redis)
        user = await auth_svc.get_or_create_sso_user(
            email=email,
            display_name=display_name,
            external_id=external_id,
            provider=provider,
            tenant_id=tenant_id,
        )
        self._db.add(user)

        logger.info("oidc.login_success", user_id=str(user.id), provider=provider.value)
        return await auth_svc.create_token_response(user)


__all__ = ["OIDCService"]

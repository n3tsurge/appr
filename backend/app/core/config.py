"""Application configuration using Pydantic Settings v2."""

from __future__ import annotations

import secrets
from typing import Annotated, Any

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = False

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://appr:appr@localhost:5432/appr",
        description="Async-compatible PostgreSQL DSN",
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # -------------------------------------------------------------------------
    # Security – JWT (RS256)
    # -------------------------------------------------------------------------
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        description="HMAC secret for legacy/CSRF tokens",
    )
    JWT_PRIVATE_KEY: str = Field(
        default="-----BEGIN RSA PRIVATE KEY-----\nREPLACE_WITH_REAL_RS256_PRIVATE_KEY_PEM\n-----END RSA PRIVATE KEY-----",
        description="RS256 private key PEM for signing JWTs",
    )
    JWT_PUBLIC_KEY: str = Field(
        default="-----BEGIN PUBLIC KEY-----\nREPLACE_WITH_REAL_RS256_PUBLIC_KEY_PEM\n-----END PUBLIC KEY-----",
        description="RS256 public key PEM for verifying JWTs",
    )
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # -------------------------------------------------------------------------
    # Okta SSO
    # -------------------------------------------------------------------------
    OKTA_DOMAIN: str = Field(default="", description="e.g. dev-123456.okta.com")
    OKTA_CLIENT_ID: str = Field(default="", description="Okta application client ID")
    OKTA_CLIENT_SECRET: str = Field(default="", description="Okta application client secret")

    # -------------------------------------------------------------------------
    # Generic OIDC
    # -------------------------------------------------------------------------
    OIDC_ISSUER: str = Field(default="", description="OIDC provider issuer URL")
    OIDC_CLIENT_ID: str = Field(default="", description="OIDC client ID")
    OIDC_CLIENT_SECRET: str = Field(default="", description="OIDC client secret")

    # -------------------------------------------------------------------------
    # SAML 2.0
    # -------------------------------------------------------------------------
    SAML_SP_ENTITY_ID: str = Field(default="https://appr.example.com/saml/metadata")
    SAML_IDP_METADATA_URL: str = Field(default="", description="IdP metadata XML URL")
    SAML_SP_ACS_URL: str = Field(default="https://appr.example.com/api/v1/auth/saml/acs")
    SAML_SP_SLS_URL: str = Field(default="https://appr.example.com/api/v1/auth/saml/sls")

    # -------------------------------------------------------------------------
    # Auth toggles
    # -------------------------------------------------------------------------
    AUTH_SSO_ENABLED: bool = True
    AUTH_LOCAL_ENABLED: bool = True

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = Field(default="json", pattern="^(json|console)$")

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    NEW_RELIC_LICENSE_KEY: str = Field(default="", description="New Relic ingest license key")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default="https://otlp.nr-data.net:4317",
        description="OTLP gRPC exporter endpoint",
    )
    OTEL_SERVICE_NAME: str = "app-inventory"

    # -------------------------------------------------------------------------
    # Multi-tenancy
    # -------------------------------------------------------------------------
    DEFAULT_TENANT_ID: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        description="UUID of the default/bootstrap tenant",
    )

    # -------------------------------------------------------------------------
    # Derived helpers
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def json_logs(self) -> bool:
        return self.LOG_FORMAT == "json"


# Module-level singleton – import this everywhere
settings = Settings()

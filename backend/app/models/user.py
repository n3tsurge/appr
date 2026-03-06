"""User model with multi-provider authentication support."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import AuthProvider, UserRole


class User(TimestampMixin, Base):
    """Platform user with role-based access control and multi-provider auth.

    Implements TPRD-002 requirements for user identity management.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        UniqueConstraint(
            "tenant_id",
            "auth_provider",
            "external_id",
            name="uq_users_tenant_provider_external",
        ),
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True,
        comment="RFC 5321 email address (max 320 chars)",
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="bcrypt hash; NULL for SSO-only users",
    )
    role: Mapped[UserRole] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.viewer,
        server_default=UserRole.viewer.value,
    )
    auth_provider: Mapped[AuthProvider] = mapped_column(
        String(50),
        nullable=False,
        default=AuthProvider.local,
        server_default=AuthProvider.local.value,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Subject claim from the external identity provider",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Link to the organisational Person record",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Tenant",
        back_populates="users",
        lazy="noload",
        foreign_keys=[TimestampMixin.tenant_id],
    )
    person: Mapped["Person | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Person",
        back_populates="users",
        lazy="noload",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "RefreshToken",
        back_populates="user",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"


__all__ = ["User"]

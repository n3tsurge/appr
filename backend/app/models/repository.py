"""Repository model – source control repository tracking."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import component_repositories, service_repositories
from app.models.base import Base, TimestampMixin
from app.models.enums import RepositoryProvider


class Repository(TimestampMixin, Base):
    """A source control repository linked to services or components.

    Repositories serve as the source of truth for code ownership, tech stack
    detection, and automated scorecard evaluation.
    """

    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "full_name", name="uq_repositories_tenant_full_name"),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Repository short name (e.g. 'appr-backend')",
    )
    full_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Provider-qualified name (e.g. 'org/appr-backend')",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[RepositoryProvider] = mapped_column(
        String(50),
        nullable=False,
    )
    clone_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    html_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    default_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="main",
        server_default=text("'main'"),
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary language as reported by the provider",
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Provider-native repository ID",
    )

    # Relationships
    services: Mapped[list["Service"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Service",
        secondary=service_repositories,
        back_populates="repositories",
        lazy="noload",
    )
    components: Mapped[list["Component"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Component",
        secondary=component_repositories,
        back_populates="repositories",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Repository id={self.id} full_name={self.full_name!r}>"


__all__ = ["Repository"]

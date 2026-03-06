"""Component model – reusable software building blocks."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import (
    component_dependencies,
    component_repositories,
    component_service_dependencies,
    service_components,
)
from app.models.base import Base, TimestampMixin
from app.models.enums import ComponentType, EntityStatus


class Component(TimestampMixin, Base):
    """A reusable software component (library, SDK, microservice, etc.).

    Components can belong to many services and have their own dependency graphs.
    """

    __tablename__ = "components"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_components_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    component_type: Mapped[ComponentType] = mapped_column(
        String(50),
        nullable=False,
        default=ComponentType.library,
        server_default=ComponentType.library.value,
    )
    status: Mapped[EntityStatus] = mapped_column(
        String(50),
        nullable=False,
        default=EntityStatus.active,
        server_default=EntityStatus.active.value,
    )
    owner_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary programming language (e.g. Python, TypeScript)",
    )
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    package_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Package registry identifier (e.g. npm package name)",
    )
    attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Arbitrary key-value metadata",
    )
    tags: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    services: Mapped[list["Service"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Service",
        secondary=service_components,
        back_populates="components",
        lazy="noload",
    )
    dependencies: Mapped[list["Component"]] = relationship(
        "Component",
        secondary=component_dependencies,
        primaryjoin="Component.id == component_dependencies.c.component_id",
        secondaryjoin="Component.id == component_dependencies.c.depends_on_component_id",
        back_populates="dependents",
        lazy="noload",
    )
    dependents: Mapped[list["Component"]] = relationship(
        "Component",
        secondary=component_dependencies,
        primaryjoin="Component.id == component_dependencies.c.depends_on_component_id",
        secondaryjoin="Component.id == component_dependencies.c.component_id",
        back_populates="dependencies",
        lazy="noload",
    )
    service_dependencies: Mapped[list["Service"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Service",
        secondary=component_service_dependencies,
        lazy="noload",
    )
    repositories: Mapped[list["Repository"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Repository",
        secondary=component_repositories,
        back_populates="components",
        lazy="noload",
    )
    owner_team: Mapped["Team | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Team",
        foreign_keys=[owner_team_id],
        lazy="noload",
    )
    owner_person: Mapped["Person | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Person",
        foreign_keys=[owner_person_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Component id={self.id} slug={self.slug!r} type={self.component_type}>"


__all__ = ["Component"]

"""Product model – top-level grouping of related services."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import product_services
from app.models.base import Base, TimestampMixin
from app.models.enums import EntityStatus


class Product(TimestampMixin, Base):
    """An enterprise product that groups one or more services together.

    Products represent business-level capabilities (e.g. "Payments Platform")
    and are the primary unit for ownership, scorecards, and reporting.
    """

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_products_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    tier: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Business criticality tier (1=highest)",
    )
    tags: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="Freeform tags as a JSON array of strings",
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Identifier in an external system of record",
    )

    # Relationships
    services: Mapped[list["Service"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Service",
        secondary=product_services,
        back_populates="products",
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
        return f"<Product id={self.id} slug={self.slug!r}>"


__all__ = ["Product"]

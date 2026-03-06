"""Service model – deployable unit within a product."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import (
    product_services,
    service_components,
    service_dependencies,
    service_repositories,
    service_resources,
)
from app.models.base import Base, TimestampMixin
from app.models.enums import EntityStatus, OperationalStatus, ServiceType


class Service(TimestampMixin, Base):
    """A deployable service tracked in the application inventory.

    Services are the primary unit for health, incidents, SLOs, and dependency
    mapping. Each service belongs to one or more products.
    """

    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_services_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_type: Mapped[ServiceType] = mapped_column(
        String(50),
        nullable=False,
        default=ServiceType.api,
        server_default=ServiceType.api.value,
    )
    status: Mapped[EntityStatus] = mapped_column(
        String(50),
        nullable=False,
        default=EntityStatus.active,
        server_default=EntityStatus.active.value,
    )
    operational_status: Mapped[OperationalStatus] = mapped_column(
        String(50),
        nullable=False,
        default=OperationalStatus.operational,
        server_default=OperationalStatus.operational.value,
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
    tier: Mapped[int | None] = mapped_column(nullable=True, comment="Business criticality tier")
    pagerduty_service_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    datadog_service_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    runbook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    dashboard_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    slo_target: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="SLO availability target as a percentage (e.g. 99.9)",
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
    products: Mapped[list["Product"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Product",
        secondary=product_services,
        back_populates="services",
        lazy="noload",
    )
    components: Mapped[list["Component"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Component",
        secondary=service_components,
        back_populates="services",
        lazy="noload",
    )
    resources: Mapped[list["Resource"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Resource",
        secondary=service_resources,
        back_populates="services",
        lazy="noload",
    )
    dependencies: Mapped[list["Service"]] = relationship(
        "Service",
        secondary=service_dependencies,
        primaryjoin="Service.id == service_dependencies.c.service_id",
        secondaryjoin="Service.id == service_dependencies.c.depends_on_service_id",
        back_populates="dependents",
        lazy="noload",
    )
    dependents: Mapped[list["Service"]] = relationship(
        "Service",
        secondary=service_dependencies,
        primaryjoin="Service.id == service_dependencies.c.depends_on_service_id",
        secondaryjoin="Service.id == service_dependencies.c.service_id",
        back_populates="dependencies",
        lazy="noload",
    )
    repositories: Mapped[list["Repository"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Repository",
        secondary=service_repositories,
        back_populates="services",
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
        return f"<Service id={self.id} slug={self.slug!r} type={self.service_type}>"


__all__ = ["Service"]

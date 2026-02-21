"""Resource model – cloud and infrastructure resource tracking."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import service_resources
from app.models.base import Base, TimestampMixin
from app.models.enums import EntityStatus, ResourceType


class Resource(TimestampMixin, Base):
    """A cloud or infrastructure resource tracked in the inventory.

    Resources are the physical/virtual building blocks that services run on
    (EC2 instances, Kubernetes clusters, Azure Logic Apps, etc.).
    """

    __tablename__ = "resources"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_resources_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[ResourceType] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[EntityStatus] = mapped_column(
        String(50),
        nullable=False,
        default=EntityStatus.active,
        server_default=EntityStatus.active.value,
    )
    cloud_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="e.g. aws, azure, gcp, on-premises",
    )
    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Cloud region or data centre identifier",
    )
    account_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Cloud account or subscription ID",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Provider-native resource identifier (ARN, resource ID, etc.)",
    )
    owner_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Provider-specific metadata (instance type, tags, etc.)",
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
        secondary=service_resources,
        back_populates="resources",
        lazy="noload",
    )
    owner_team: Mapped["Team | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Team",
        foreign_keys=[owner_team_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Resource id={self.id} slug={self.slug!r} type={self.resource_type}>"


__all__ = ["Resource"]

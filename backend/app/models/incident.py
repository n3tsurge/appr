"""Incident, timeline, and affected-entity models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ImpactType, IncidentSeverity, IncidentStatus


class Incident(TimestampMixin, Base):
    """An operational incident affecting one or more services.

    Implements the incident management lifecycle defined in TPRD-007.
    """

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[IncidentSeverity] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        String(50),
        nullable=False,
        default=IncidentStatus.investigating,
        server_default=IncidentStatus.investigating.value,
    )
    incident_commander_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the incident was first detected / alerts fired",
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    slack_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pagerduty_incident_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postmortem_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # Relationships
    timeline: Mapped[list["IncidentTimelineEntry"]] = relationship(
        "IncidentTimelineEntry",
        back_populates="incident",
        lazy="noload",
        order_by="IncidentTimelineEntry.occurred_at",
        cascade="all, delete-orphan",
    )
    affected_entities: Mapped[list["IncidentAffectedEntity"]] = relationship(
        "IncidentAffectedEntity",
        back_populates="incident",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    incident_commander: Mapped["User | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[incident_commander_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Incident id={self.id} severity={self.severity} status={self.status}>"


class IncidentTimelineEntry(Base):
    """A timestamped event on an incident timeline (e.g. 'DB restored')."""

    __tablename__ = "incident_timeline_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    entry_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="e.g. detection, acknowledgement, update, resolution",
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    incident: Mapped[Incident] = relationship(
        "Incident",
        back_populates="timeline",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<IncidentTimelineEntry id={self.id} type={self.entry_type}>"


class IncidentAffectedEntity(Base):
    """Polymorphic link between an incident and an affected entity."""

    __tablename__ = "incident_affected_entities"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "entity_type",
            "entity_id",
            name="uq_incident_affected_entity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="One of: service, component, resource",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="PK of the referenced entity (no FK to keep polymorphism clean)",
    )
    impact_type: Mapped[ImpactType] = mapped_column(
        String(50),
        nullable=False,
        default=ImpactType.outage,
        server_default=ImpactType.outage.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    incident: Mapped[Incident] = relationship(
        "Incident",
        back_populates="affected_entities",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentAffectedEntity incident_id={self.incident_id} "
            f"entity_type={self.entity_type} entity_id={self.entity_id}>"
        )


__all__ = ["Incident", "IncidentAffectedEntity", "IncidentTimelineEntry"]

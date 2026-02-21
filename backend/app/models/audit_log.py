"""AuditLog model – append-only immutable event log."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """Immutable, append-only record of all significant system events.

    Implements the audit trail requirements from TPRD-012. Records are never
    updated or deleted – they are the authoritative history of all mutations.

    Attributes:
        id: UUID primary key (v4).
        tenant_id: Tenant scope of the event.
        event_type: Dot-notation event name (e.g. ``user.login``, ``service.created``).
        actor_id: UUID of the user who performed the action (nullable for system events).
        actor_type: ``user`` or ``system``.
        entity_type: Type of the affected entity (e.g. ``Service``, ``Incident``).
        entity_id: UUID of the affected entity.
        before: JSON snapshot of the entity before the change (nullable).
        after: JSON snapshot of the entity after the change (nullable).
        ip_address: Client IP address (nullable).
        user_agent: HTTP User-Agent string (nullable).
        request_id: Correlation ID from X-Request-ID header.
        occurred_at: Wall-clock timestamp of the event (server now()).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        # Efficient time-range queries per tenant
        Index("ix_audit_logs_tenant_occurred", "tenant_id", "occurred_at"),
        # Look up all events for a specific entity
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        # Look up all events by actor
        Index("ix_audit_logs_actor", "actor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Dot-notation event name, e.g. 'service.created'",
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who triggered the event; NULL for automated/system events",
    )
    actor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
        server_default=text("'user'"),
        comment="'user' or 'system'",
    )
    entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="SQLAlchemy model name of the affected entity",
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="PK of the affected entity (no FK – entity may be deleted)",
    )
    before: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON snapshot of the entity state before the mutation",
    )
    after: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON snapshot of the entity state after the mutation",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Additional context (e.g. diff summary, reason)",
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} event_type={self.event_type!r} "
            f"entity_type={self.entity_type} entity_id={self.entity_id}>"
        )


__all__ = ["AuditLog"]

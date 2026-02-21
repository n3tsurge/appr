"""EntityAssignment – polymorphic ownership assignments for any entity."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EntityAssignment(Base):
    """Polymorphic assignment of a person or team to any inventory entity.

    This model avoids N separate join tables (service_owners, product_owners,
    etc.) by storing the target entity type and ID as columns.  It supports
    assigning both individuals and teams, and supports multiple assignment
    roles (e.g. ``owner``, ``on-call``, ``tech-lead``).

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope.
        entity_type: Target model name (e.g. ``Service``, ``Product``).
        entity_id: UUID of the target entity.
        assignee_type: ``person`` or ``team``.
        assignee_id: UUID of the Person or Team.
        role: Assignment role label (e.g. ``owner``, ``on-call``).
        assigned_at: When the assignment was created.
        assigned_by: UUID of the user who created the assignment.
    """

    __tablename__ = "entity_assignments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "entity_type",
            "entity_id",
            "assignee_type",
            "assignee_id",
            "role",
            name="uq_entity_assignment",
        ),
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
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Target model class name, e.g. 'Service'",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="PK of the target entity (no FK to maintain polymorphism)",
    )
    assignee_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'person' or 'team'",
    )
    assignee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="PK of the Person or Team",
    )
    role: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="owner",
        server_default=text("'owner'"),
        comment="Assignment role label, e.g. 'owner', 'on-call', 'tech-lead'",
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<EntityAssignment id={self.id} "
            f"{self.assignee_type}/{self.assignee_id} -> "
            f"{self.entity_type}/{self.entity_id} role={self.role!r}>"
        )


__all__ = ["EntityAssignment"]

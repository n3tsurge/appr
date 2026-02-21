"""Team model for organisational groupings of people."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Team(TimestampMixin, Base):
    """Organisational team that can own entities and be assigned to incidents.

    Implements TPRD-002 team management requirements.
    """

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_teams_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="URL-safe identifier, unique per tenant",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment="Team distribution list or contact email",
    )
    slack_channel: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Slack channel name or ID (e.g. #platform-team)",
    )
    parent_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional parent for hierarchical team structures",
    )

    # Relationships
    parent_team: Mapped["Team | None"] = relationship(
        "Team",
        remote_side="Team.id",
        back_populates="sub_teams",
        lazy="noload",
    )
    sub_teams: Mapped[list["Team"]] = relationship(
        "Team",
        back_populates="parent_team",
        lazy="noload",
    )
    members: Mapped[list["Person"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Person",
        back_populates="team",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Team id={self.id} slug={self.slug!r}>"


__all__ = ["Team"]

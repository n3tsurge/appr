"""Scorecard and ScorecardCriterion models for service quality evaluation."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Scorecard(TimestampMixin, Base):
    """A named quality scorecard that evaluates entities against criteria.

    Scorecards are applied to services or products and produce a score that
    reflects operational maturity (e.g. observability, security, documentation).
    """

    __tablename__ = "scorecards"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_scorecards_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Target entity type: service, component, or product",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    passing_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
        server_default=text("70"),
        comment="Minimum score percentage to be considered passing",
    )

    # Relationships
    criteria: Mapped[list["ScorecardCriterion"]] = relationship(
        "ScorecardCriterion",
        back_populates="scorecard",
        lazy="noload",
        order_by="ScorecardCriterion.sort_order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Scorecard id={self.id} slug={self.slug!r}>"


class ScorecardCriterion(Base):
    """A single evaluatable criterion within a scorecard."""

    __tablename__ = "scorecard_criteria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    scorecard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scorecards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="Relative weight of this criterion vs others in the scorecard",
    )
    rule_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="e.g. has_runbook, has_oncall, slo_defined, has_repository",
    )
    rule_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Rule-specific parameters",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    # Relationships
    scorecard: Mapped[Scorecard] = relationship(
        "Scorecard",
        back_populates="criteria",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<ScorecardCriterion id={self.id} rule_type={self.rule_type!r}>"


__all__ = ["Scorecard", "ScorecardCriterion"]

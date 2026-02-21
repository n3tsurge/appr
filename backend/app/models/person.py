"""Person model for directory/staff records."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Person(TimestampMixin, Base):
    """Directory record for an individual staff member.

    Decoupled from the User model so that people can exist in the directory
    without having platform login access, and users can be linked to their
    corresponding Person entry.

    Implements TPRD-002 people directory requirements.
    """

    __tablename__ = "persons"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_persons_tenant_email"),
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Full preferred display name (may differ from first+last)",
    )
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Job title",
    )
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slack_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_hr_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Identifier from the HR system of record",
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default="true",
    )

    # Relationships
    manager: Mapped["Person | None"] = relationship(
        "Person",
        remote_side="Person.id",
        back_populates="direct_reports",
        lazy="noload",
    )
    direct_reports: Mapped[list["Person"]] = relationship(
        "Person",
        back_populates="manager",
        lazy="noload",
    )
    team: Mapped["Team | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Team",
        back_populates="members",
        lazy="noload",
    )
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="person",
        lazy="noload",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Person id={self.id} email={self.email!r}>"


__all__ = ["Person"]

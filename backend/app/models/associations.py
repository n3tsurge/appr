"""SQLAlchemy association tables for all many-to-many relationships."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

# ---------------------------------------------------------------------------
# Products <-> Services
# ---------------------------------------------------------------------------
product_services = Table(
    "product_services",
    Base.metadata,
    Column(
        "product_id",
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# ---------------------------------------------------------------------------
# Services <-> Components
# ---------------------------------------------------------------------------
service_components = Table(
    "service_components",
    Base.metadata,
    Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "component_id",
        UUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# ---------------------------------------------------------------------------
# Services <-> Resources
# ---------------------------------------------------------------------------
service_resources = Table(
    "service_resources",
    Base.metadata,
    Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "resource_id",
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# ---------------------------------------------------------------------------
# Service -> Service (dependency graph)
# ---------------------------------------------------------------------------
service_dependencies = Table(
    "service_dependencies",
    Base.metadata,
    Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "depends_on_service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    UniqueConstraint("service_id", "depends_on_service_id", name="uq_service_dependencies"),
)

# ---------------------------------------------------------------------------
# Component -> Component (dependency graph)
# ---------------------------------------------------------------------------
component_dependencies = Table(
    "component_dependencies",
    Base.metadata,
    Column(
        "component_id",
        UUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "depends_on_component_id",
        UUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    UniqueConstraint(
        "component_id",
        "depends_on_component_id",
        name="uq_component_dependencies",
    ),
)

# ---------------------------------------------------------------------------
# Component -> Service (cross-type dependency)
# ---------------------------------------------------------------------------
component_service_dependencies = Table(
    "component_service_dependencies",
    Base.metadata,
    Column(
        "component_id",
        UUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "depends_on_service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    UniqueConstraint(
        "component_id",
        "depends_on_service_id",
        name="uq_component_service_dependencies",
    ),
)

# ---------------------------------------------------------------------------
# Services <-> Repositories
# ---------------------------------------------------------------------------
service_repositories = Table(
    "service_repositories",
    Base.metadata,
    Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "repository_id",
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# ---------------------------------------------------------------------------
# Components <-> Repositories
# ---------------------------------------------------------------------------
component_repositories = Table(
    "component_repositories",
    Base.metadata,
    Column(
        "component_id",
        UUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "repository_id",
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

__all__ = [
    "component_dependencies",
    "component_repositories",
    "component_service_dependencies",
    "product_services",
    "service_components",
    "service_dependencies",
    "service_repositories",
    "service_resources",
]

"""Alembic migration environment – async SQLAlchemy configuration."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Import all models so Alembic can detect schema changes automatically
# (Base.metadata must include every table)
# ---------------------------------------------------------------------------
from app.core.config import settings
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.base import Base
from app.models.component import Component  # noqa: F401
from app.models.entity_assignment import EntityAssignment  # noqa: F401
from app.models.incident import (  # noqa: F401
    Incident,
    IncidentAffectedEntity,
    IncidentTimelineEntry,
)
from app.models.person import Person  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.repository import Repository  # noqa: F401
from app.models.resource import Resource  # noqa: F401
from app.models.scorecard import Scorecard, ScorecardCriterion  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.team import Team  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401

# ---------------------------------------------------------------------------
# Alembic Config object – provides access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from application settings (ignores alembic.ini value)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that autogenerate compares against the live DB
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script output, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute pending migrations within a synchronous connection context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (required for asyncpg driver)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to the live database)."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

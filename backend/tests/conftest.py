"""pytest fixtures for the AppR backend test suite."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import create_app
from app.models.base import Base
from app.models.enums import AuthProvider, UserRole
from app.models.tenant import Tenant
from app.models.user import User

# ---------------------------------------------------------------------------
# Test database – use a separate DB or SQLite (in-memory not supported for
# asyncpg; use the same Postgres instance with a _test schema/db)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/appr", "/appr_test")


# ---------------------------------------------------------------------------
# Engine fixture – module-scoped so the schema is created once per test run
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="module")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine and initialise the schema."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Session fixture – function-scoped, rolls back after each test
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional session that rolls back after each test."""
    async_session = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an HTTPX AsyncClient pointed at the test FastAPI app.

    The ``get_db`` dependency is overridden to use the test session.
    """
    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create and persist a default test tenant."""
    tenant = Tenant(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Test Organisation",
        slug="test-org",
        is_active=True,
        settings={},
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create and persist an admin user for the test tenant."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email="admin@test.example.com",
        display_name="Test Admin",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.admin,
        auth_provider=AuthProvider.local,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Return Authorization headers containing a valid JWT for the test user."""
    access_token = create_access_token(
        data={
            "sub": str(test_user.id),
            "tenant_id": str(test_user.tenant_id),
            "role": test_user.role.value,
        },
        expires_delta=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {access_token}"}

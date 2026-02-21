"""pytest fixtures for the AppR backend test suite."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.base import Base
from app.models.enums import AuthProvider, UserRole
from app.models.tenant import Tenant
from app.models.user import User

# SQLite in-memory for fast, isolated unit tests.
# For integration tests against a real PostgreSQL, override DATABASE_URL in CI.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.api.deps import get_db
    from app.core.redis import get_redis
    from app.main import create_app

    _app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    class _FakeRedis:
        async def ping(self) -> bool:
            return True

        async def aclose(self) -> None:
            pass

    async def _override_get_redis() -> AsyncGenerator[_FakeRedis, None]:
        yield _FakeRedis()

    _app.dependency_overrides[get_db] = _override_get_db
    _app.dependency_overrides[get_redis] = _override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=_app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        id=uuid.UUID(settings.DEFAULT_TENANT_ID),
        name="Test Tenant",
        slug="test-tenant",
        is_active=True,
        settings={},
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email="admin@test.example.com",
        display_name="Test Admin",
        password_hash=get_password_hash("Str0ng!Password#1"),
        role=UserRole.admin,
        auth_provider=AuthProvider.local,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    token = create_access_token(
        data={
            "sub": str(test_user.id),
            "tenant_id": str(test_user.tenant_id),
            "role": test_user.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email="viewer@test.example.com",
        display_name="Test Viewer",
        password_hash=get_password_hash("Str0ng!Password#1"),
        role=UserRole.viewer,
        auth_provider=AuthProvider.local,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def viewer_headers(viewer_user: User) -> dict[str, str]:
    token = create_access_token(
        data={
            "sub": str(viewer_user.id),
            "tenant_id": str(viewer_user.tenant_id),
            "role": viewer_user.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}

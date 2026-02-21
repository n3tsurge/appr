"""Async Redis client factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

# ---------------------------------------------------------------------------
# Connection pool (created once at module load; lazily connected)
# ---------------------------------------------------------------------------
_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool  # noqa: PLW0603
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _pool


def get_redis_client() -> Redis:
    """Return a Redis client backed by the shared connection pool."""
    return aioredis.Redis(connection_pool=_get_pool())


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_redis() -> AsyncGenerator[Redis, None]:
    """Yield an async Redis client.  Does NOT close the pool between requests."""
    client: Redis = get_redis_client()
    try:
        yield client
    finally:
        # Individual client resources are managed by the pool; no explicit close.
        pass


async def close_redis_pool() -> None:
    """Drain and close the connection pool.  Call during application shutdown."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def ping_redis() -> bool:
    """Health-check helper – returns True when Redis is reachable."""
    client = get_redis_client()
    try:
        return await client.ping()
    except Exception:
        return False

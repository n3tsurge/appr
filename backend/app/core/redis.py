"""Redis async client factory and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

# ---------------------------------------------------------------------------
# Connection pool – created once at import time, reused across requests
# ---------------------------------------------------------------------------
_pool: ConnectionPool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True,
    # hiredis parser is picked up automatically when redis[hiredis] is installed
)


def get_redis_pool() -> ConnectionPool:
    """Return the shared connection pool (useful for testing overrides)."""
    return _pool


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Yield a Redis client bound to the shared connection pool.

    Usage::

        @router.get("/")
        async def handler(redis: RedisClient) -> ...:
            await redis.get("key")
    """
    client: Redis = aioredis.Redis(connection_pool=_pool)
    try:
        yield client
    finally:
        await client.aclose()


async def ping_redis() -> bool:
    """Return True if Redis is reachable (used in health checks)."""
    client: Redis = aioredis.Redis(connection_pool=_pool)
    try:
        return await client.ping()
    except Exception:
        return False
    finally:
        await client.aclose()


# Convenience type alias for use in route signatures
RedisClient = Annotated[Redis, Depends(get_redis)]

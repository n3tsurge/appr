"""Generic async service base class with caching, auditing, and pagination."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from typing import Any, Generic, TypeVar

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import GenericRepository
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.services.audit_service import AuditService

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_CACHE_TTL = 60  # seconds


def _make_cache_key(entity_type: str, tenant_id: uuid.UUID, **kwargs: Any) -> str:
    """Build a deterministic cache key from the given parameters."""
    params_hash = hashlib.md5(
        json.dumps(kwargs, sort_keys=True, default=str).encode()
    ).hexdigest()
    return f"tenant:{tenant_id}:{entity_type}:list:{params_hash}"


class GenericService(Generic[T]):
    """Base service wiring a repository, audit logging, and Redis cache.

    Subclasses must set ``repository`` and ``entity_type`` (e.g. ``"service"``).

    Cache keys follow the pattern::

        tenant:{tid}:{entity_type}:list:{hash_of_params}

    All list caches for an entity type are invalidated on any write operation.
    """

    repository: GenericRepository[T]
    entity_type: str  # e.g. "service", "team"

    def __init__(
        self,
        db: AsyncSession,
        audit_service: AuditService,
        redis: Redis,
    ) -> None:
        self._db = db
        self._audit = audit_service
        self._redis = redis

    # ------------------------------------------------------------------
    # Public CRUD
    # ------------------------------------------------------------------

    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort: str = "created_at",
        order: str = "asc",
    ) -> PaginatedResponse[Any]:
        """Return a paginated list, served from cache when possible."""
        cache_key = _make_cache_key(
            self.entity_type,
            tenant_id,
            page=page,
            per_page=per_page,
            search=search,
            filters=filters or {},
            sort=sort,
            order=order,
        )
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return PaginatedResponse[Any].model_validate(cached)

        items, total = await self.repository.list(
            self._db,
            tenant_id,
            page=page,
            per_page=per_page,
            search=search,
            filters=filters,
            sort=sort,
            order=order,
        )
        total_pages = math.ceil(total / per_page) if per_page else 0
        response = PaginatedResponse(
            data=items,
            meta=PaginationMeta(
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            ),
        )
        await self._set_cached(cache_key, response.model_dump(mode="json"))
        return response

    async def get(self, id: uuid.UUID, tenant_id: uuid.UUID) -> T:
        """Return a single entity or raise HTTP 404."""
        return await self.repository.get_or_404(self._db, id, tenant_id)

    async def create(
        self,
        data: dict[str, Any],
        actor: Any,  # User
        tenant_id: uuid.UUID,
    ) -> T:
        """Create entity, audit log, and invalidate list cache."""
        obj = await self.repository.create(self._db, tenant_id, data, actor.id)
        await self._audit.log(
            tenant_id=tenant_id,
            event_type=f"{self.entity_type}.created",
            actor_id=actor.id,
            entity_type=self.entity_type.capitalize(),
            entity_id=obj.id,  # type: ignore[attr-defined]
            after=self._to_dict(obj),
        )
        await self._invalidate_cache(f"tenant:{tenant_id}:{self.entity_type}:list:*")
        return obj

    async def update(
        self,
        id: uuid.UUID,
        data: dict[str, Any],
        actor: Any,
        tenant_id: uuid.UUID,
    ) -> T:
        """Update entity, audit log, and invalidate list cache."""
        obj = await self.repository.get_or_404(self._db, id, tenant_id)
        before = self._to_dict(obj)
        obj = await self.repository.update(self._db, obj, data, actor.id)
        await self._audit.log(
            tenant_id=tenant_id,
            event_type=f"{self.entity_type}.updated",
            actor_id=actor.id,
            entity_type=self.entity_type.capitalize(),
            entity_id=obj.id,  # type: ignore[attr-defined]
            before=before,
            after=self._to_dict(obj),
        )
        await self._invalidate_cache(f"tenant:{tenant_id}:{self.entity_type}:list:*")
        return obj

    async def delete(
        self,
        id: uuid.UUID,
        actor: Any,
        tenant_id: uuid.UUID,
    ) -> None:
        """Soft-delete entity, audit log, and invalidate list cache."""
        obj = await self.repository.get_or_404(self._db, id, tenant_id)
        before = self._to_dict(obj)
        await self.repository.soft_delete(self._db, obj, actor.id)
        await self._audit.log(
            tenant_id=tenant_id,
            event_type=f"{self.entity_type}.deleted",
            actor_id=actor.id,
            entity_type=self.entity_type.capitalize(),
            entity_id=id,
            before=before,
        )
        await self._invalidate_cache(f"tenant:{tenant_id}:{self.entity_type}:list:*")

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    async def _get_cached(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
            if raw is not None:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("cache.get_error", key=key, error=str(exc))
        return None

    async def _set_cached(self, key: str, value: Any, ttl: int = _CACHE_TTL) -> None:
        try:
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.warning("cache.set_error", key=key, error=str(exc))

    async def _invalidate_cache(self, pattern: str) -> None:
        try:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("cache.invalidate_error", pattern=pattern, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        """Convert a SQLAlchemy model to a JSON-serialisable dict."""
        result: dict[str, Any] = {}
        for col in obj.__table__.columns:
            val = getattr(obj, col.name, None)
            result[col.name] = str(val) if isinstance(val, (uuid.UUID,)) else val
        return result


__all__ = ["GenericService"]

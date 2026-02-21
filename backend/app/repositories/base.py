"""Generic async repository base class with tenant-scoped CRUD operations."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

import structlog
from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import TimestampMixin

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class GenericRepository(Generic[T]):
    """Base repository providing tenant-scoped CRUD with soft-delete support.

    Subclasses must define ``model`` as a class attribute pointing to the
    SQLAlchemy mapped class.

    All mutating operations automatically filter ``deleted_at IS NULL`` and
    scope by ``tenant_id`` to enforce multi-tenant isolation.
    """

    model: type[T]

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    async def get(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> T | None:
        """Return a single live record or None."""
        stmt = select(self.model).where(
            self.model.id == id,  # type: ignore[attr-defined]
            self.model.tenant_id == tenant_id,  # type: ignore[attr-defined]
            self.model.deleted_at.is_(None),  # type: ignore[attr-defined]
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_404(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> T:
        """Return a single live record or raise HTTP 404."""
        obj = await self.get(db, id, tenant_id)
        if obj is None:
            model_name = getattr(self.model, "__name__", "Resource")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model_name} with id '{id}' not found",
            )
        return obj

    async def list(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort: str = "created_at",
        order: str = "asc",
    ) -> tuple[list[T], int]:
        """Return a paginated, filtered, sorted list of live records.

        Returns:
            Tuple of ``(items, total)`` where *total* is the count of all
            matching records (before pagination).
        """
        base_stmt = select(self.model).where(
            self.model.tenant_id == tenant_id,  # type: ignore[attr-defined]
            self.model.deleted_at.is_(None),  # type: ignore[attr-defined]
        )

        # Apply search on ``name`` column when present
        if search and hasattr(self.model, "name"):
            base_stmt = base_stmt.where(
                self.model.name.ilike(f"%{search}%"),  # type: ignore[attr-defined]
            )

        # Apply additional filters
        if filters:
            for field, value in filters.items():
                if value is not None and hasattr(self.model, field):
                    col = getattr(self.model, field)
                    base_stmt = base_stmt.where(col == value)

        # Total count
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        # Sorting
        sort_col = getattr(self.model, sort, None)
        if sort_col is None:
            sort_col = getattr(self.model, "created_at", None)
        if sort_col is not None:
            base_stmt = base_stmt.order_by(
                asc(sort_col) if order == "asc" else desc(sort_col)
            )

        # Pagination
        offset = (page - 1) * per_page
        base_stmt = base_stmt.offset(offset).limit(per_page)

        result = await db.execute(base_stmt)
        items = list(result.scalars().all())

        return items, total

    async def count(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Return the count of live records matching the given filters."""
        stmt = select(func.count()).select_from(self.model).where(  # type: ignore[arg-type]
            self.model.tenant_id == tenant_id,  # type: ignore[attr-defined]
            self.model.deleted_at.is_(None),  # type: ignore[attr-defined]
        )
        if filters:
            for field, value in filters.items():
                if value is not None and hasattr(self.model, field):
                    col = getattr(self.model, field)
                    stmt = stmt.where(col == value)
        return (await db.execute(stmt)).scalar_one()

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    async def create(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
        created_by: uuid.UUID,
    ) -> T:
        """Persist a new record and return it."""
        obj = self.model(
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by,
            **data,
        )
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        logger.debug(
            "repository.create",
            model=self.model.__name__,  # type: ignore[attr-defined]
            id=str(obj.id),  # type: ignore[attr-defined]
        )
        return obj

    async def update(
        self,
        db: AsyncSession,
        obj: T,
        data: dict[str, Any],
        updated_by: uuid.UUID,
    ) -> T:
        """Apply *data* dict to *obj* and flush."""
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        obj.updated_by = updated_by  # type: ignore[attr-defined]
        obj.updated_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        logger.debug(
            "repository.update",
            model=self.model.__name__,  # type: ignore[attr-defined]
            id=str(obj.id),  # type: ignore[attr-defined]
        )
        return obj

    async def soft_delete(
        self,
        db: AsyncSession,
        obj: T,
        deleted_by: uuid.UUID,
    ) -> T:
        """Mark *obj* as deleted without removing the row."""
        obj.deleted_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]
        obj.updated_by = deleted_by  # type: ignore[attr-defined]
        db.add(obj)
        await db.flush()
        logger.debug(
            "repository.soft_delete",
            model=self.model.__name__,  # type: ignore[attr-defined]
            id=str(obj.id),  # type: ignore[attr-defined]
        )
        return obj


__all__ = ["GenericRepository"]

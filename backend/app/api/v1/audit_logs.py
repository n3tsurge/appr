"""Audit log read-only route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select

from app.api.deps import DbSession, require_role
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationMeta, PaginationParams

logger = structlog.get_logger(__name__)

router = APIRouter()


class AuditLogListItem:
    """Inline schema for audit log list items."""

    pass


from pydantic import BaseModel


class AuditLogRead(BaseModel):
    """Audit log entry representation."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID | None = None
    actor_type: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    before: dict | None = None
    after: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    occurred_at: datetime

    model_config = {"from_attributes": True}


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogRead],
    summary="List audit log entries",
)
async def list_audit_logs(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    entity_type: Annotated[str | None, Query(description="Filter by entity type")] = None,
    entity_id: Annotated[uuid.UUID | None, Query(description="Filter by entity UUID")] = None,
    actor_id: Annotated[uuid.UUID | None, Query(description="Filter by actor UUID")] = None,
    event_type: Annotated[str | None, Query(description="Filter by event type")] = None,
    from_date: Annotated[datetime | None, Query(description="Filter events from this timestamp (ISO 8601)")] = None,
    to_date: Annotated[datetime | None, Query(description="Filter events up to this timestamp (ISO 8601)")] = None,
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[AuditLogRead]:
    """Return a paginated list of audit log entries for the current tenant.

    Supports optional filtering by entity_type, entity_id, actor_id,
    event_type, and a date range (from_date / to_date).
    """
    tenant_id = current_user.tenant_id

    base = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

    if entity_type is not None:
        base = base.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        base = base.where(AuditLog.entity_id == entity_id)
    if actor_id is not None:
        base = base.where(AuditLog.actor_id == actor_id)
    if event_type is not None:
        base = base.where(AuditLog.event_type == event_type)
    if from_date is not None:
        base = base.where(AuditLog.occurred_at >= from_date)
    if to_date is not None:
        base = base.where(AuditLog.occurred_at <= to_date)

    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.order_by(AuditLog.occurred_at.desc()).offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[AuditLogRead.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


__all__ = ["router"]

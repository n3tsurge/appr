"""Incident management route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import IncidentStatus, UserRole
from app.models.incident import Incident, IncidentTimelineEntry
from app.models.user import User
from app.schemas.catalog import (
    IncidentCreate,
    IncidentListItem,
    IncidentRead,
    IncidentResolveRequest,
    IncidentTimelineEntryCreate,
    IncidentTimelineEntryRead,
    IncidentUpdate,
)
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta, PaginationParams
from app.services.audit_service import AuditService

logger = structlog.get_logger(__name__)

router = APIRouter()

EditorUser = Depends(require_role(UserRole.editor, UserRole.admin))
AdminUser = Depends(require_role(UserRole.admin))


def _request_id(request: Request) -> str | None:
    return getattr(getattr(request, "state", None), "request_id", None)


@router.get(
    "",
    response_model=PaginatedResponse[IncidentListItem],
    summary="List incidents",
)
async def list_incidents(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[IncidentListItem]:
    """Return a paginated list of all incidents in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Incident).where(
        Incident.tenant_id == tenant_id,
        Incident.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[IncidentListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[IncidentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create incident",
)
async def create_incident(
    body: IncidentCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[IncidentRead]:
    """Create a new incident within the current tenant."""
    tenant_id = current_user.tenant_id

    incident = Incident(
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        status=body.status,
        incident_commander_id=body.incident_commander_id,
        detected_at=body.detected_at,
        acknowledged_at=body.acknowledged_at,
        slack_channel=body.slack_channel,
        pagerduty_incident_id=body.pagerduty_incident_id,
        postmortem_url=body.postmortem_url,
        attributes=body.attributes,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="incident.created",
        actor_id=current_user.id,
        entity_type="Incident",
        entity_id=incident.id,
        after={"title": incident.title, "severity": incident.severity.value, "status": incident.status.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("incidents.created", incident_id=str(incident.id), actor=str(current_user.id))
    return ApiResponse(data=IncidentRead.model_validate(incident))


@router.get(
    "/{id}",
    response_model=ApiResponse[IncidentRead],
    summary="Get incident by ID",
)
async def get_incident(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[IncidentRead]:
    """Return an incident by ID."""
    incident = (await db.execute(
        select(Incident).where(
            Incident.id == id,
            Incident.tenant_id == current_user.tenant_id,
            Incident.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return ApiResponse(data=IncidentRead.model_validate(incident))


@router.put(
    "/{id}",
    response_model=ApiResponse[IncidentRead],
    summary="Update incident",
)
async def update_incident(
    id: uuid.UUID,
    body: IncidentUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[IncidentRead]:
    """Update an existing incident."""
    tenant_id = current_user.tenant_id
    incident = (await db.execute(
        select(Incident).where(
            Incident.id == id,
            Incident.tenant_id == tenant_id,
            Incident.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    before = {
        "title": incident.title,
        "severity": incident.severity.value,
        "status": incident.status.value,
    }

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)
    incident.updated_by = current_user.id

    db.add(incident)
    await db.flush()
    await db.refresh(incident)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="incident.updated",
        actor_id=current_user.id,
        entity_type="Incident",
        entity_id=incident.id,
        before=before,
        after={"title": incident.title, "severity": incident.severity.value, "status": incident.status.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("incidents.updated", incident_id=str(incident.id), actor=str(current_user.id))
    return ApiResponse(data=IncidentRead.model_validate(incident))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete incident (Admin)",
)
async def delete_incident(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete an incident from the current tenant."""
    tenant_id = current_user.tenant_id
    incident = (await db.execute(
        select(Incident).where(
            Incident.id == id,
            Incident.tenant_id == tenant_id,
            Incident.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.deleted_at = datetime.now(tz=timezone.utc)
    incident.updated_by = current_user.id
    db.add(incident)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="incident.deleted",
        actor_id=current_user.id,
        entity_type="Incident",
        entity_id=incident.id,
        before={"title": incident.title, "severity": incident.severity.value},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("incidents.deleted", incident_id=str(incident.id), actor=str(current_user.id))


@router.post(
    "/{id}/timeline",
    response_model=ApiResponse[IncidentTimelineEntryRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add timeline entry",
)
async def add_timeline_entry(
    id: uuid.UUID,
    body: IncidentTimelineEntryCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[IncidentTimelineEntryRead]:
    """Add a timeline entry to an existing incident."""
    tenant_id = current_user.tenant_id
    incident = (await db.execute(
        select(Incident).where(
            Incident.id == id,
            Incident.tenant_id == tenant_id,
            Incident.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    entry = IncidentTimelineEntry(
        incident_id=incident.id,
        occurred_at=body.occurred_at,
        entry_type=body.entry_type,
        message=body.message,
        author_id=body.author_id or current_user.id,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="incident.timeline_entry.added",
        actor_id=current_user.id,
        entity_type="Incident",
        entity_id=incident.id,
        after={"entry_type": entry.entry_type, "message": entry.message},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info(
        "incidents.timeline_entry.added",
        incident_id=str(incident.id),
        entry_id=str(entry.id),
        actor=str(current_user.id),
    )
    return ApiResponse(data=IncidentTimelineEntryRead.model_validate(entry))


@router.post(
    "/{id}/resolve",
    response_model=ApiResponse[IncidentRead],
    summary="Resolve incident",
)
async def resolve_incident(
    id: uuid.UUID,
    body: IncidentResolveRequest,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[IncidentRead]:
    """Mark an incident as resolved."""
    tenant_id = current_user.tenant_id
    incident = (await db.execute(
        select(Incident).where(
            Incident.id == id,
            Incident.tenant_id == tenant_id,
            Incident.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    if incident.status == IncidentStatus.resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident is already resolved",
        )

    before = {"status": incident.status.value, "resolved_at": None}

    incident.status = IncidentStatus.resolved
    incident.resolved_at = body.resolved_at or datetime.now(tz=timezone.utc)
    if body.postmortem_url:
        incident.postmortem_url = body.postmortem_url
    incident.updated_by = current_user.id

    db.add(incident)
    await db.flush()
    await db.refresh(incident)

    # Add a resolution timeline entry
    resolution_entry = IncidentTimelineEntry(
        incident_id=incident.id,
        occurred_at=incident.resolved_at,
        entry_type="resolution",
        message=body.resolution_note or "Incident resolved",
        author_id=current_user.id,
    )
    db.add(resolution_entry)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="incident.resolved",
        actor_id=current_user.id,
        entity_type="Incident",
        entity_id=incident.id,
        before=before,
        after={"status": incident.status.value, "resolved_at": incident.resolved_at.isoformat()},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("incidents.resolved", incident_id=str(incident.id), actor=str(current_user.id))
    return ApiResponse(data=IncidentRead.model_validate(incident))


__all__ = ["router"]

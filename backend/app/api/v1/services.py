"""Service catalog route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import UserRole
from app.models.service import Service
from app.models.user import User
from app.schemas.catalog import ServiceCreate, ServiceListItem, ServiceRead, ServiceUpdate
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
    response_model=PaginatedResponse[ServiceListItem],
    summary="List services",
)
async def list_services(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[ServiceListItem]:
    """Return a paginated list of all services in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Service).where(
        Service.tenant_id == tenant_id,
        Service.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[ServiceListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[ServiceRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create service",
)
async def create_service(
    body: ServiceCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ServiceRead]:
    """Create a new service within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.slug == body.slug,
            Service.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service with slug '{body.slug}' already exists",
        )

    service = Service(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        service_type=body.service_type,
        status=body.status,
        operational_status=body.operational_status,
        owner_team_id=body.owner_team_id,
        owner_person_id=body.owner_person_id,
        tier=body.tier,
        pagerduty_service_id=body.pagerduty_service_id,
        datadog_service_name=body.datadog_service_name,
        runbook_url=body.runbook_url,
        dashboard_url=body.dashboard_url,
        slo_target=body.slo_target,
        attributes=body.attributes,
        tags=body.tags,
        external_id=body.external_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(service)
    await db.flush()
    await db.refresh(service)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="service.created",
        actor_id=current_user.id,
        entity_type="Service",
        entity_id=service.id,
        after={"name": service.name, "slug": service.slug, "service_type": service.service_type.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("services.created", service_id=str(service.id), actor=str(current_user.id))
    return ApiResponse(data=ServiceRead.model_validate(service))


@router.get(
    "/{id}",
    response_model=ApiResponse[ServiceRead],
    summary="Get service by ID",
)
async def get_service(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ServiceRead]:
    """Return a service by ID."""
    service = (await db.execute(
        select(Service).where(
            Service.id == id,
            Service.tenant_id == current_user.tenant_id,
            Service.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return ApiResponse(data=ServiceRead.model_validate(service))


@router.put(
    "/{id}",
    response_model=ApiResponse[ServiceRead],
    summary="Update service",
)
async def update_service(
    id: uuid.UUID,
    body: ServiceUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ServiceRead]:
    """Update an existing service."""
    tenant_id = current_user.tenant_id
    service = (await db.execute(
        select(Service).where(
            Service.id == id,
            Service.tenant_id == tenant_id,
            Service.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    before = {"name": service.name, "slug": service.slug, "status": service.status.value}

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    service.updated_by = current_user.id

    db.add(service)
    await db.flush()
    await db.refresh(service)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="service.updated",
        actor_id=current_user.id,
        entity_type="Service",
        entity_id=service.id,
        before=before,
        after={"name": service.name, "slug": service.slug, "status": service.status.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("services.updated", service_id=str(service.id), actor=str(current_user.id))
    return ApiResponse(data=ServiceRead.model_validate(service))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete service (Admin)",
)
async def delete_service(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a service from the current tenant."""
    tenant_id = current_user.tenant_id
    service = (await db.execute(
        select(Service).where(
            Service.id == id,
            Service.tenant_id == tenant_id,
            Service.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    service.deleted_at = datetime.now(tz=timezone.utc)
    service.updated_by = current_user.id
    db.add(service)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="service.deleted",
        actor_id=current_user.id,
        entity_type="Service",
        entity_id=service.id,
        before={"name": service.name, "slug": service.slug},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("services.deleted", service_id=str(service.id), actor=str(current_user.id))


__all__ = ["router"]

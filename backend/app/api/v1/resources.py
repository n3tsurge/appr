"""Resource catalog route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import UserRole
from app.models.resource import Resource
from app.models.user import User
from app.schemas.catalog import ResourceCreate, ResourceListItem, ResourceRead, ResourceUpdate
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
    response_model=PaginatedResponse[ResourceListItem],
    summary="List resources",
)
async def list_resources(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[ResourceListItem]:
    """Return a paginated list of all resources in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Resource).where(
        Resource.tenant_id == tenant_id,
        Resource.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[ResourceListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[ResourceRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create resource",
)
async def create_resource(
    body: ResourceCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ResourceRead]:
    """Create a new resource within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Resource).where(
            Resource.tenant_id == tenant_id,
            Resource.slug == body.slug,
            Resource.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resource with slug '{body.slug}' already exists",
        )

    resource = Resource(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        resource_type=body.resource_type,
        status=body.status,
        cloud_provider=body.cloud_provider,
        region=body.region,
        account_id=body.account_id,
        resource_id=body.resource_id,
        owner_team_id=body.owner_team_id,
        attributes=body.attributes,
        tags=body.tags,
        external_id=body.external_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(resource)
    await db.flush()
    await db.refresh(resource)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="resource.created",
        actor_id=current_user.id,
        entity_type="Resource",
        entity_id=resource.id,
        after={"name": resource.name, "slug": resource.slug, "resource_type": resource.resource_type.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("resources.created", resource_id=str(resource.id), actor=str(current_user.id))
    return ApiResponse(data=ResourceRead.model_validate(resource))


@router.get(
    "/{id}",
    response_model=ApiResponse[ResourceRead],
    summary="Get resource by ID",
)
async def get_resource(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ResourceRead]:
    """Return a resource by ID."""
    resource = (await db.execute(
        select(Resource).where(
            Resource.id == id,
            Resource.tenant_id == current_user.tenant_id,
            Resource.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return ApiResponse(data=ResourceRead.model_validate(resource))


@router.put(
    "/{id}",
    response_model=ApiResponse[ResourceRead],
    summary="Update resource",
)
async def update_resource(
    id: uuid.UUID,
    body: ResourceUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ResourceRead]:
    """Update an existing resource."""
    tenant_id = current_user.tenant_id
    resource = (await db.execute(
        select(Resource).where(
            Resource.id == id,
            Resource.tenant_id == tenant_id,
            Resource.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    before = {"name": resource.name, "slug": resource.slug, "status": resource.status.value}

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)
    resource.updated_by = current_user.id

    db.add(resource)
    await db.flush()
    await db.refresh(resource)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="resource.updated",
        actor_id=current_user.id,
        entity_type="Resource",
        entity_id=resource.id,
        before=before,
        after={"name": resource.name, "slug": resource.slug, "status": resource.status.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("resources.updated", resource_id=str(resource.id), actor=str(current_user.id))
    return ApiResponse(data=ResourceRead.model_validate(resource))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete resource (Admin)",
)
async def delete_resource(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a resource from the current tenant."""
    tenant_id = current_user.tenant_id
    resource = (await db.execute(
        select(Resource).where(
            Resource.id == id,
            Resource.tenant_id == tenant_id,
            Resource.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    resource.deleted_at = datetime.now(tz=timezone.utc)
    resource.updated_by = current_user.id
    db.add(resource)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="resource.deleted",
        actor_id=current_user.id,
        entity_type="Resource",
        entity_id=resource.id,
        before={"name": resource.name, "slug": resource.slug},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("resources.deleted", resource_id=str(resource.id), actor=str(current_user.id))


__all__ = ["router"]

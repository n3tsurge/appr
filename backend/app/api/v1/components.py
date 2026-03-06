"""Component catalog route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.component import Component
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.catalog import ComponentCreate, ComponentListItem, ComponentRead, ComponentUpdate
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
    response_model=PaginatedResponse[ComponentListItem],
    summary="List components",
)
async def list_components(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[ComponentListItem]:
    """Return a paginated list of all components in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Component).where(
        Component.tenant_id == tenant_id,
        Component.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[ComponentListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[ComponentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create component",
)
async def create_component(
    body: ComponentCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ComponentRead]:
    """Create a new component within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Component).where(
            Component.tenant_id == tenant_id,
            Component.slug == body.slug,
            Component.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Component with slug '{body.slug}' already exists",
        )

    component = Component(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        component_type=body.component_type,
        status=body.status,
        owner_team_id=body.owner_team_id,
        owner_person_id=body.owner_person_id,
        language=body.language,
        version=body.version,
        package_name=body.package_name,
        attributes=body.attributes,
        tags=body.tags,
        external_id=body.external_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(component)
    await db.flush()
    await db.refresh(component)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="component.created",
        actor_id=current_user.id,
        entity_type="Component",
        entity_id=component.id,
        after={"name": component.name, "slug": component.slug, "component_type": component.component_type.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("components.created", component_id=str(component.id), actor=str(current_user.id))
    return ApiResponse(data=ComponentRead.model_validate(component))


@router.get(
    "/{id}",
    response_model=ApiResponse[ComponentRead],
    summary="Get component by ID",
)
async def get_component(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ComponentRead]:
    """Return a component by ID."""
    component = (await db.execute(
        select(Component).where(
            Component.id == id,
            Component.tenant_id == current_user.tenant_id,
            Component.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    return ApiResponse(data=ComponentRead.model_validate(component))


@router.put(
    "/{id}",
    response_model=ApiResponse[ComponentRead],
    summary="Update component",
)
async def update_component(
    id: uuid.UUID,
    body: ComponentUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ComponentRead]:
    """Update an existing component."""
    tenant_id = current_user.tenant_id
    component = (await db.execute(
        select(Component).where(
            Component.id == id,
            Component.tenant_id == tenant_id,
            Component.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")

    before = {"name": component.name, "slug": component.slug, "status": component.status.value}

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(component, field, value)
    component.updated_by = current_user.id

    db.add(component)
    await db.flush()
    await db.refresh(component)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="component.updated",
        actor_id=current_user.id,
        entity_type="Component",
        entity_id=component.id,
        before=before,
        after={"name": component.name, "slug": component.slug, "status": component.status.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("components.updated", component_id=str(component.id), actor=str(current_user.id))
    return ApiResponse(data=ComponentRead.model_validate(component))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete component (Admin)",
)
async def delete_component(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a component from the current tenant."""
    tenant_id = current_user.tenant_id
    component = (await db.execute(
        select(Component).where(
            Component.id == id,
            Component.tenant_id == tenant_id,
            Component.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")

    component.deleted_at = datetime.now(tz=timezone.utc)
    component.updated_by = current_user.id
    db.add(component)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="component.deleted",
        actor_id=current_user.id,
        entity_type="Component",
        entity_id=component.id,
        before={"name": component.name, "slug": component.slug},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("components.deleted", component_id=str(component.id), actor=str(current_user.id))


__all__ = ["router"]

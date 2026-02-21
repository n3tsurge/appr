"""Repository catalog route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import UserRole
from app.models.repository import Repository
from app.models.user import User
from app.schemas.catalog import RepositoryCreate, RepositoryListItem, RepositoryRead, RepositoryUpdate
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
    response_model=PaginatedResponse[RepositoryListItem],
    summary="List repositories",
)
async def list_repositories(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[RepositoryListItem]:
    """Return a paginated list of all repositories in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Repository).where(
        Repository.tenant_id == tenant_id,
        Repository.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[RepositoryListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[RepositoryRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create repository",
)
async def create_repository(
    body: RepositoryCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[RepositoryRead]:
    """Create a new repository record within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Repository).where(
            Repository.tenant_id == tenant_id,
            Repository.full_name == body.full_name,
            Repository.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository with full_name '{body.full_name}' already exists",
        )

    repository = Repository(
        tenant_id=tenant_id,
        name=body.name,
        full_name=body.full_name,
        description=body.description,
        provider=body.provider,
        clone_url=body.clone_url,
        html_url=body.html_url,
        default_branch=body.default_branch,
        is_private=body.is_private,
        is_archived=body.is_archived,
        language=body.language,
        external_id=body.external_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(repository)
    await db.flush()
    await db.refresh(repository)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="repository.created",
        actor_id=current_user.id,
        entity_type="Repository",
        entity_id=repository.id,
        after={"name": repository.name, "full_name": repository.full_name, "provider": repository.provider.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("repositories.created", repository_id=str(repository.id), actor=str(current_user.id))
    return ApiResponse(data=RepositoryRead.model_validate(repository))


@router.get(
    "/{id}",
    response_model=ApiResponse[RepositoryRead],
    summary="Get repository by ID",
)
async def get_repository(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[RepositoryRead]:
    """Return a repository by ID."""
    repository = (await db.execute(
        select(Repository).where(
            Repository.id == id,
            Repository.tenant_id == current_user.tenant_id,
            Repository.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return ApiResponse(data=RepositoryRead.model_validate(repository))


@router.put(
    "/{id}",
    response_model=ApiResponse[RepositoryRead],
    summary="Update repository",
)
async def update_repository(
    id: uuid.UUID,
    body: RepositoryUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[RepositoryRead]:
    """Update an existing repository."""
    tenant_id = current_user.tenant_id
    repository = (await db.execute(
        select(Repository).where(
            Repository.id == id,
            Repository.tenant_id == tenant_id,
            Repository.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    before = {"name": repository.name, "full_name": repository.full_name, "provider": repository.provider.value}

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repository, field, value)
    repository.updated_by = current_user.id

    db.add(repository)
    await db.flush()
    await db.refresh(repository)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="repository.updated",
        actor_id=current_user.id,
        entity_type="Repository",
        entity_id=repository.id,
        before=before,
        after={"name": repository.name, "full_name": repository.full_name, "provider": repository.provider.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("repositories.updated", repository_id=str(repository.id), actor=str(current_user.id))
    return ApiResponse(data=RepositoryRead.model_validate(repository))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete repository (Admin)",
)
async def delete_repository(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a repository from the current tenant."""
    tenant_id = current_user.tenant_id
    repository = (await db.execute(
        select(Repository).where(
            Repository.id == id,
            Repository.tenant_id == tenant_id,
            Repository.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    repository.deleted_at = datetime.now(tz=timezone.utc)
    repository.updated_by = current_user.id
    db.add(repository)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="repository.deleted",
        actor_id=current_user.id,
        entity_type="Repository",
        entity_id=repository.id,
        before={"name": repository.name, "full_name": repository.full_name},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("repositories.deleted", repository_id=str(repository.id), actor=str(current_user.id))


__all__ = ["router"]

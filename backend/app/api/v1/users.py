"""User management route handlers (Admin only)."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    DbSession,
    get_current_user,
    require_role,
)
from app.core.security import get_password_hash
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta, PaginationParams
from app.schemas.user import UserCreate, UserListItem, UserRead, UserUpdate
from app.services.audit_service import AuditService

logger = structlog.get_logger(__name__)

router = APIRouter()

AdminUser = Depends(require_role(UserRole.admin))


def _request_id(request: Request) -> str | None:
    return getattr(getattr(request, "state", None), "request_id", None)


@router.get(
    "",
    response_model=PaginatedResponse[UserListItem],
    summary="List users (Admin)",
)
async def list_users(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = AdminUser,
) -> PaginatedResponse[UserListItem]:
    """Return a paginated list of all users in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(User).where(
        User.tenant_id == tenant_id,
        User.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    import math
    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[UserListItem.model_validate(u) for u in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create user (Admin)",
)
async def create_user(
    body: UserCreate,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> ApiResponse[UserRead]:
    """Create a new local user within the current tenant."""
    tenant_id = current_user.tenant_id

    # Check uniqueness
    existing = (await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.email == body.email.lower(),
            User.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{body.email}' already exists",
        )

    user = User(
        tenant_id=tenant_id,
        email=body.email.lower(),
        display_name=body.display_name,
        password_hash=get_password_hash(body.password),
        role=body.role,
        is_active=body.is_active,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="user.created",
        actor_id=current_user.id,
        entity_type="User",
        entity_id=user.id,
        after={"email": user.email, "role": user.role.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("users.created", user_id=str(user.id), actor=str(current_user.id))
    return ApiResponse(data=UserRead.model_validate(user))


@router.get(
    "/{id}",
    response_model=ApiResponse[UserRead],
    summary="Get user by ID",
)
async def get_user(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[UserRead]:
    """Return a user by ID (any authenticated user may read)."""
    user = (await db.execute(
        select(User).where(
            User.id == id,
            User.tenant_id == current_user.tenant_id,
            User.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return ApiResponse(data=UserRead.model_validate(user))


@router.put(
    "/{id}",
    response_model=ApiResponse[UserRead],
    summary="Update user role/status (Admin)",
)
async def update_user(
    id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> ApiResponse[UserRead]:
    """Update a user's role or active status."""
    tenant_id = current_user.tenant_id
    user = (await db.execute(
        select(User).where(
            User.id == id,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    before = {"role": user.role.value, "is_active": user.is_active, "display_name": user.display_name}
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.display_name is not None:
        user.display_name = body.display_name
    user.updated_by = current_user.id
    db.add(user)
    await db.flush()
    await db.refresh(user)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="user.updated",
        actor_id=current_user.id,
        entity_type="User",
        entity_id=user.id,
        before=before,
        after={"role": user.role.value, "is_active": user.is_active, "display_name": user.display_name},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("users.updated", user_id=str(user.id), actor=str(current_user.id))
    return ApiResponse(data=UserRead.model_validate(user))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete user (Admin)",
)
async def delete_user(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a user from the current tenant."""
    from datetime import datetime, timezone
    tenant_id = current_user.tenant_id
    user = (await db.execute(
        select(User).where(
            User.id == id,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    user.deleted_at = datetime.now(tz=timezone.utc)
    user.updated_by = current_user.id
    db.add(user)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="user.deleted",
        actor_id=current_user.id,
        entity_type="User",
        entity_id=user.id,
        before={"email": user.email, "role": user.role.value},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("users.deleted", user_id=str(user.id), actor=str(current_user.id))


@router.post(
    "/{id}/reset-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger password reset email (Admin)",
)
async def reset_password(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> dict[str, str]:
    """Trigger a password reset email for a user (stub — email delivery via Celery task)."""
    tenant_id = current_user.tenant_id
    user = (await db.execute(
        select(User).where(
            User.id == id,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # In production this would enqueue a Celery task to send the reset email.
    logger.info(
        "users.password_reset_triggered",
        target_user_id=str(user.id),
        actor=str(current_user.id),
    )
    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="user.password_reset_requested",
        actor_id=current_user.id,
        entity_type="User",
        entity_id=user.id,
        request_id=_request_id(request),
    )
    await db.commit()
    return {"message": "Password reset email queued"}


__all__ = ["router"]

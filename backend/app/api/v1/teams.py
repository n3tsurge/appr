"""Team catalog route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import UserRole
from app.models.team import Team
from app.models.user import User
from app.schemas.catalog import TeamCreate, TeamListItem, TeamRead, TeamUpdate
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
    response_model=PaginatedResponse[TeamListItem],
    summary="List teams",
)
async def list_teams(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[TeamListItem]:
    """Return a paginated list of all teams in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Team).where(
        Team.tenant_id == tenant_id,
        Team.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[TeamListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[TeamRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create team",
)
async def create_team(
    body: TeamCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[TeamRead]:
    """Create a new team within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Team).where(
            Team.tenant_id == tenant_id,
            Team.slug == body.slug,
            Team.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team with slug '{body.slug}' already exists",
        )

    team = Team(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        email=body.email,
        slack_channel=body.slack_channel,
        parent_team_id=body.parent_team_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(team)
    await db.flush()
    await db.refresh(team)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="team.created",
        actor_id=current_user.id,
        entity_type="Team",
        entity_id=team.id,
        after={"name": team.name, "slug": team.slug},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("teams.created", team_id=str(team.id), actor=str(current_user.id))
    return ApiResponse(data=TeamRead.model_validate(team))


@router.get(
    "/{id}",
    response_model=ApiResponse[TeamRead],
    summary="Get team by ID",
)
async def get_team(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[TeamRead]:
    """Return a team by ID."""
    team = (await db.execute(
        select(Team).where(
            Team.id == id,
            Team.tenant_id == current_user.tenant_id,
            Team.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return ApiResponse(data=TeamRead.model_validate(team))


@router.put(
    "/{id}",
    response_model=ApiResponse[TeamRead],
    summary="Update team",
)
async def update_team(
    id: uuid.UUID,
    body: TeamUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[TeamRead]:
    """Update an existing team."""
    tenant_id = current_user.tenant_id
    team = (await db.execute(
        select(Team).where(
            Team.id == id,
            Team.tenant_id == tenant_id,
            Team.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    before = {"name": team.name, "slug": team.slug}

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)
    team.updated_by = current_user.id

    db.add(team)
    await db.flush()
    await db.refresh(team)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="team.updated",
        actor_id=current_user.id,
        entity_type="Team",
        entity_id=team.id,
        before=before,
        after={"name": team.name, "slug": team.slug},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("teams.updated", team_id=str(team.id), actor=str(current_user.id))
    return ApiResponse(data=TeamRead.model_validate(team))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete team (Admin)",
)
async def delete_team(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a team from the current tenant."""
    tenant_id = current_user.tenant_id
    team = (await db.execute(
        select(Team).where(
            Team.id == id,
            Team.tenant_id == tenant_id,
            Team.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    team.deleted_at = datetime.now(tz=timezone.utc)
    team.updated_by = current_user.id
    db.add(team)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="team.deleted",
        actor_id=current_user.id,
        entity_type="Team",
        entity_id=team.id,
        before={"name": team.name, "slug": team.slug},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("teams.deleted", team_id=str(team.id), actor=str(current_user.id))


__all__ = ["router"]

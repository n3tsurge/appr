"""Scorecard engine route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import UserRole
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.models.user import User
from app.schemas.catalog import (
    ScorecardCreate,
    ScorecardCriterionCreate,
    ScorecardCriterionRead,
    ScorecardListItem,
    ScorecardRead,
    ScorecardUpdate,
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
    response_model=PaginatedResponse[ScorecardListItem],
    summary="List scorecards",
)
async def list_scorecards(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[ScorecardListItem]:
    """Return a paginated list of all scorecards in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Scorecard).where(
        Scorecard.tenant_id == tenant_id,
        Scorecard.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[ScorecardListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[ScorecardRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create scorecard",
)
async def create_scorecard(
    body: ScorecardCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ScorecardRead]:
    """Create a new scorecard within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Scorecard).where(
            Scorecard.tenant_id == tenant_id,
            Scorecard.slug == body.slug,
            Scorecard.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scorecard with slug '{body.slug}' already exists",
        )

    scorecard = Scorecard(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        entity_type=body.entity_type,
        is_active=body.is_active,
        passing_threshold=body.passing_threshold,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(scorecard)
    await db.flush()

    # Create criteria
    for criterion_data in body.criteria:
        criterion = ScorecardCriterion(
            scorecard_id=scorecard.id,
            name=criterion_data.name,
            description=criterion_data.description,
            weight=criterion_data.weight,
            rule_type=criterion_data.rule_type,
            rule_config=criterion_data.rule_config,
            sort_order=criterion_data.sort_order,
            is_active=criterion_data.is_active,
        )
        db.add(criterion)

    await db.flush()
    await db.refresh(scorecard)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="scorecard.created",
        actor_id=current_user.id,
        entity_type="Scorecard",
        entity_id=scorecard.id,
        after={"name": scorecard.name, "slug": scorecard.slug, "entity_type": scorecard.entity_type},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("scorecards.created", scorecard_id=str(scorecard.id), actor=str(current_user.id))
    return ApiResponse(data=ScorecardRead.model_validate(scorecard))


@router.get(
    "/{id}",
    response_model=ApiResponse[ScorecardRead],
    summary="Get scorecard by ID",
)
async def get_scorecard(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ScorecardRead]:
    """Return a scorecard by ID."""
    scorecard = (await db.execute(
        select(Scorecard).where(
            Scorecard.id == id,
            Scorecard.tenant_id == current_user.tenant_id,
            Scorecard.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if scorecard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")
    return ApiResponse(data=ScorecardRead.model_validate(scorecard))


@router.put(
    "/{id}",
    response_model=ApiResponse[ScorecardRead],
    summary="Update scorecard",
)
async def update_scorecard(
    id: uuid.UUID,
    body: ScorecardUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ScorecardRead]:
    """Update an existing scorecard."""
    tenant_id = current_user.tenant_id
    scorecard = (await db.execute(
        select(Scorecard).where(
            Scorecard.id == id,
            Scorecard.tenant_id == tenant_id,
            Scorecard.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if scorecard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")

    before = {"name": scorecard.name, "slug": scorecard.slug, "is_active": scorecard.is_active}

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scorecard, field, value)
    scorecard.updated_by = current_user.id

    db.add(scorecard)
    await db.flush()
    await db.refresh(scorecard)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="scorecard.updated",
        actor_id=current_user.id,
        entity_type="Scorecard",
        entity_id=scorecard.id,
        before=before,
        after={"name": scorecard.name, "slug": scorecard.slug, "is_active": scorecard.is_active},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("scorecards.updated", scorecard_id=str(scorecard.id), actor=str(current_user.id))
    return ApiResponse(data=ScorecardRead.model_validate(scorecard))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete scorecard (Admin)",
)
async def delete_scorecard(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a scorecard from the current tenant."""
    tenant_id = current_user.tenant_id
    scorecard = (await db.execute(
        select(Scorecard).where(
            Scorecard.id == id,
            Scorecard.tenant_id == tenant_id,
            Scorecard.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if scorecard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")

    scorecard.deleted_at = datetime.now(tz=timezone.utc)
    scorecard.updated_by = current_user.id
    db.add(scorecard)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="scorecard.deleted",
        actor_id=current_user.id,
        entity_type="Scorecard",
        entity_id=scorecard.id,
        before={"name": scorecard.name, "slug": scorecard.slug},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("scorecards.deleted", scorecard_id=str(scorecard.id), actor=str(current_user.id))


@router.post(
    "/{id}/criteria",
    response_model=ApiResponse[ScorecardCriterionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add criterion to scorecard",
)
async def add_criterion(
    id: uuid.UUID,
    body: ScorecardCriterionCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ScorecardCriterionRead]:
    """Add a new criterion to an existing scorecard."""
    tenant_id = current_user.tenant_id
    scorecard = (await db.execute(
        select(Scorecard).where(
            Scorecard.id == id,
            Scorecard.tenant_id == tenant_id,
            Scorecard.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if scorecard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")

    criterion = ScorecardCriterion(
        scorecard_id=scorecard.id,
        name=body.name,
        description=body.description,
        weight=body.weight,
        rule_type=body.rule_type,
        rule_config=body.rule_config,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(criterion)
    await db.flush()
    await db.refresh(criterion)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="scorecard.criterion.added",
        actor_id=current_user.id,
        entity_type="Scorecard",
        entity_id=scorecard.id,
        after={"criterion_name": criterion.name, "rule_type": criterion.rule_type},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info(
        "scorecards.criterion.added",
        scorecard_id=str(scorecard.id),
        criterion_id=str(criterion.id),
        actor=str(current_user.id),
    )
    return ApiResponse(data=ScorecardCriterionRead.model_validate(criterion))


__all__ = ["router"]

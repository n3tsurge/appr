"""People directory route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import UserRole
from app.models.person import Person
from app.models.user import User
from app.schemas.catalog import PersonCreate, PersonListItem, PersonRead, PersonUpdate
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
    response_model=PaginatedResponse[PersonListItem],
    summary="List people",
)
async def list_people(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[PersonListItem]:
    """Return a paginated list of all persons in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Person).where(
        Person.tenant_id == tenant_id,
        Person.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[PersonListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[PersonRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create person",
)
async def create_person(
    body: PersonCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[PersonRead]:
    """Create a new person directory record within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Person).where(
            Person.tenant_id == tenant_id,
            Person.email == body.email.lower(),
            Person.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Person with email '{body.email}' already exists",
        )

    person = Person(
        tenant_id=tenant_id,
        first_name=body.first_name,
        last_name=body.last_name,
        display_name=body.display_name,
        email=body.email.lower(),
        title=body.title,
        department=body.department,
        location=body.location,
        manager_id=body.manager_id,
        team_id=body.team_id,
        slack_user_id=body.slack_user_id,
        github_username=body.github_username,
        external_hr_id=body.external_hr_id,
        is_active=body.is_active,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(person)
    await db.flush()
    await db.refresh(person)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="person.created",
        actor_id=current_user.id,
        entity_type="Person",
        entity_id=person.id,
        after={"email": person.email, "display_name": person.display_name},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("people.created", person_id=str(person.id), actor=str(current_user.id))
    return ApiResponse(data=PersonRead.model_validate(person))


@router.get(
    "/{id}",
    response_model=ApiResponse[PersonRead],
    summary="Get person by ID",
)
async def get_person(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[PersonRead]:
    """Return a person by ID."""
    person = (await db.execute(
        select(Person).where(
            Person.id == id,
            Person.tenant_id == current_user.tenant_id,
            Person.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return ApiResponse(data=PersonRead.model_validate(person))


@router.put(
    "/{id}",
    response_model=ApiResponse[PersonRead],
    summary="Update person",
)
async def update_person(
    id: uuid.UUID,
    body: PersonUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[PersonRead]:
    """Update an existing person directory record."""
    tenant_id = current_user.tenant_id
    person = (await db.execute(
        select(Person).where(
            Person.id == id,
            Person.tenant_id == tenant_id,
            Person.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    before = {"email": person.email, "display_name": person.display_name, "is_active": person.is_active}

    update_data = body.model_dump(exclude_unset=True)
    if "email" in update_data and update_data["email"]:
        update_data["email"] = update_data["email"].lower()
    for field, value in update_data.items():
        setattr(person, field, value)
    person.updated_by = current_user.id

    db.add(person)
    await db.flush()
    await db.refresh(person)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="person.updated",
        actor_id=current_user.id,
        entity_type="Person",
        entity_id=person.id,
        before=before,
        after={"email": person.email, "display_name": person.display_name, "is_active": person.is_active},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("people.updated", person_id=str(person.id), actor=str(current_user.id))
    return ApiResponse(data=PersonRead.model_validate(person))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete person (Admin)",
)
async def delete_person(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a person from the current tenant."""
    tenant_id = current_user.tenant_id
    person = (await db.execute(
        select(Person).where(
            Person.id == id,
            Person.tenant_id == tenant_id,
            Person.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    person.deleted_at = datetime.now(tz=timezone.utc)
    person.updated_by = current_user.id
    db.add(person)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="person.deleted",
        actor_id=current_user.id,
        entity_type="Person",
        entity_id=person.id,
        before={"email": person.email, "display_name": person.display_name},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("people.deleted", person_id=str(person.id), actor=str(current_user.id))


__all__ = ["router"]

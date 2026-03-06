"""Product catalog route handlers."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.enums import UserRole
from app.models.product import Product
from app.models.user import User
from app.schemas.catalog import ProductCreate, ProductListItem, ProductRead, ProductUpdate
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
    response_model=PaginatedResponse[ProductListItem],
    summary="List products",
)
async def list_products(
    request: Request,
    db: DbSession,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role(UserRole.viewer, UserRole.editor, UserRole.admin)),
) -> PaginatedResponse[ProductListItem]:
    """Return a paginated list of all products in the current tenant."""
    tenant_id = current_user.tenant_id

    base = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.deleted_at.is_(None),
    )
    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = base.offset(pagination.offset).limit(pagination.per_page)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = math.ceil(total / pagination.per_page) if pagination.per_page else 0

    return PaginatedResponse(
        data=[ProductListItem.model_validate(r) for r in rows],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        ),
    )


@router.post(
    "",
    response_model=ApiResponse[ProductRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
)
async def create_product(
    body: ProductCreate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ProductRead]:
    """Create a new product within the current tenant."""
    tenant_id = current_user.tenant_id

    existing = (await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.slug == body.slug,
            Product.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with slug '{body.slug}' already exists",
        )

    product = Product(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        status=body.status,
        owner_team_id=body.owner_team_id,
        owner_person_id=body.owner_person_id,
        tier=body.tier,
        tags=body.tags,
        external_id=body.external_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="product.created",
        actor_id=current_user.id,
        entity_type="Product",
        entity_id=product.id,
        after={"name": product.name, "slug": product.slug},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("products.created", product_id=str(product.id), actor=str(current_user.id))
    return ApiResponse(data=ProductRead.model_validate(product))


@router.get(
    "/{id}",
    response_model=ApiResponse[ProductRead],
    summary="Get product by ID",
)
async def get_product(
    id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiResponse[ProductRead]:
    """Return a product by ID."""
    product = (await db.execute(
        select(Product).where(
            Product.id == id,
            Product.tenant_id == current_user.tenant_id,
            Product.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ApiResponse(data=ProductRead.model_validate(product))


@router.put(
    "/{id}",
    response_model=ApiResponse[ProductRead],
    summary="Update product",
)
async def update_product(
    id: uuid.UUID,
    body: ProductUpdate,
    request: Request,
    db: DbSession,
    current_user: User = EditorUser,
) -> ApiResponse[ProductRead]:
    """Update an existing product."""
    tenant_id = current_user.tenant_id
    product = (await db.execute(
        select(Product).where(
            Product.id == id,
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    before = {"name": product.name, "slug": product.slug, "status": product.status.value}

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    product.updated_by = current_user.id

    db.add(product)
    await db.flush()
    await db.refresh(product)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="product.updated",
        actor_id=current_user.id,
        entity_type="Product",
        entity_id=product.id,
        before=before,
        after={"name": product.name, "slug": product.slug, "status": product.status.value},
        request_id=_request_id(request),
    )
    await db.commit()

    logger.info("products.updated", product_id=str(product.id), actor=str(current_user.id))
    return ApiResponse(data=ProductRead.model_validate(product))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete product (Admin)",
)
async def delete_product(
    id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = AdminUser,
) -> None:
    """Soft-delete a product from the current tenant."""
    tenant_id = current_user.tenant_id
    product = (await db.execute(
        select(Product).where(
            Product.id == id,
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product.deleted_at = datetime.now(tz=timezone.utc)
    product.updated_by = current_user.id
    db.add(product)

    audit = AuditService(db)
    await audit.log(
        tenant_id=tenant_id,
        event_type="product.deleted",
        actor_id=current_user.id,
        entity_type="Product",
        entity_id=product.id,
        before={"name": product.name, "slug": product.slug},
        request_id=_request_id(request),
    )
    await db.commit()
    logger.info("products.deleted", product_id=str(product.id), actor=str(current_user.id))


__all__ = ["router"]

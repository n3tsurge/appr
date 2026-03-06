"""Shared response envelope schemas and pagination helpers."""

from __future__ import annotations

from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Standard response envelopes
# ---------------------------------------------------------------------------


class ApiResponse(BaseModel, Generic[T]):
    """Single-item API response envelope.

    All successful single-resource responses are wrapped in this envelope to
    provide a consistent structure regardless of the resource type.

    Example::

        {"data": {"id": "...", "name": "payments-api"}}
    """

    data: T


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""

    total: int = Field(ge=0, description="Total number of records matching the query")
    page: int = Field(ge=1, description="Current page number (1-based)")
    per_page: int = Field(ge=1, le=500, description="Records per page")
    total_pages: int = Field(ge=0, description="Total number of pages")
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the next page (cursor-based pagination)",
    )
    prev_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the previous page",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """List API response envelope with pagination metadata.

    Example::

        {
            "data": [...],
            "meta": {"total": 42, "page": 1, "per_page": 20, "total_pages": 3}
        }
    """

    data: list[T]
    meta: PaginationMeta


# ---------------------------------------------------------------------------
# RFC 7807 Problem Detail
# ---------------------------------------------------------------------------


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Detail response for error responses.

    Reference: https://datatracker.ietf.org/doc/html/rfc7807
    """

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(description="Short, human-readable summary of the problem")
    status: int = Field(description="HTTP status code")
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence",
    )
    instance: str | None = Field(
        default=None,
        description="URI reference identifying this specific occurrence",
    )
    errors: list[dict[str, Any]] | None = Field(
        default=None,
        description="Structured validation errors (field-level)",
    )

    model_config = {"json_schema_extra": {"examples": [
        {
            "type": "https://appr.example.com/errors/not-found",
            "title": "Resource Not Found",
            "status": 404,
            "detail": "Service with id '123' does not exist",
        }
    ]}}


# ---------------------------------------------------------------------------
# Query parameter model for pagination
# ---------------------------------------------------------------------------


class PaginationParams(BaseModel):
    """Standard query parameters for paginated list endpoints.

    Usage::

        @router.get("/services")
        async def list_services(pagination: Annotated[PaginationParams, Query()]) -> ...:
            ...
    """

    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1
    per_page: Annotated[
        int,
        Query(ge=1, le=500, alias="per_page", description="Records per page"),
    ] = 20
    cursor: Annotated[
        str | None,
        Query(description="Opaque cursor for cursor-based pagination"),
    ] = None
    sort_by: Annotated[
        str | None,
        Query(description="Field name to sort by"),
    ] = None
    sort_dir: Annotated[
        str | None,
        Query(pattern="^(asc|desc)$", description="Sort direction"),
    ] = "asc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


__all__ = [
    "ApiResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "PaginationParams",
    "ProblemDetail",
]

"""FastAPI application factory for the AppR backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.core.telemetry import configure_telemetry, shutdown_telemetry
from app.middleware.cors import add_cors_middleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.tenant import TenantMiddleware
from app.schemas.common import ProblemDetail

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application startup and shutdown lifecycle manager."""
    # --- Startup ---
    logger.info(
        "appr backend starting",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    configure_telemetry(app=app, engine=engine)

    logger.info("appr backend ready")

    yield

    # --- Shutdown ---
    logger.info("appr backend shutting down")
    shutdown_telemetry()
    await engine.dispose()
    logger.info("appr backend stopped")


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Convert Starlette/FastAPI HTTPExceptions to RFC 7807 Problem Detail."""
    problem = ProblemDetail(
        type=f"https://appr.example.com/errors/http-{exc.status_code}",
        title=str(exc.detail),
        status=exc.status_code,
        instance=str(request.url),
    )
    return JSONResponse(
        content=problem.model_dump(exclude_none=True),
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


async def _validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convert Pydantic validation errors to RFC 7807 Problem Detail."""
    errors = [
        {
            "loc": list(e["loc"]),
            "msg": e["msg"],
            "type": e["type"],
        }
        for e in exc.errors()
    ]
    problem = ProblemDetail(
        type="https://appr.example.com/errors/validation",
        title="Request Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="One or more fields failed validation",
        instance=str(request.url),
        errors=errors,
    )
    return JSONResponse(
        content=problem.model_dump(exclude_none=True),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    logger.exception(
        "unhandled exception",
        path=str(request.url),
        request_id=request_id,
    )
    problem = ProblemDetail(
        type="https://appr.example.com/errors/internal",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        instance=str(request.url),
    )
    return JSONResponse(
        content=problem.model_dump(exclude_none=True),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    # Configure logging as early as possible
    configure_logging(log_level=settings.LOG_LEVEL, json_output=settings.json_logs)

    app = FastAPI(
        title="AppR – Application Inventory API",
        description=(
            "Enterprise application inventory system. "
            "Tracks services, components, resources, teams, and incidents."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middleware (order matters – outermost registered first = runs last)
    # ------------------------------------------------------------------
    # CORSMiddleware must be outermost to handle pre-flight requests
    add_cors_middleware(app)

    # Request ID next so it's available to all inner middleware/handlers
    app.add_middleware(RequestIDMiddleware)

    # Tenant extraction (needs request_id to be set first for logging)
    app.add_middleware(TenantMiddleware)

    # Request/response logging (innermost – has access to full context)
    app.add_middleware(LoggingMiddleware)

    # ------------------------------------------------------------------
    # Exception handlers
    # ------------------------------------------------------------------
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_exception_handler)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(api_v1_router)

    return app


# ---------------------------------------------------------------------------
# WSGI/ASGI entrypoint
# ---------------------------------------------------------------------------
app = create_app()

__all__ = ["app", "create_app"]

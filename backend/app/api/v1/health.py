"""Health and readiness check endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession, RedisClient
from app.core.config import settings
from app.core.redis import ping_redis
from app.schemas.health import ComponentHealthStatus, HealthResponse, ReadinessResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description=(
        "Returns 200 OK as long as the application process is running. "
        "Use this for Kubernetes liveness probes."
    ),
)
async def health() -> HealthResponse:
    """Liveness check – always returns 200 if the process is alive."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(tz=timezone.utc),
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description=(
        "Checks connectivity to database and Redis. "
        "Returns 200 if all dependencies are healthy, 503 otherwise. "
        "Use this for Kubernetes readiness probes."
    ),
)
async def ready(
    db: DbSession,
    redis: RedisClient,
) -> JSONResponse:
    """Readiness check – verifies database and Redis connectivity."""
    checks: dict[str, ComponentHealthStatus] = {}

    # ------------------------------------------------------------------
    # Database check
    # ------------------------------------------------------------------
    import time

    db_start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - db_start) * 1000, 2)
        checks["database"] = ComponentHealthStatus(status="ok", latency_ms=db_latency)
    except Exception as exc:
        db_latency = round((time.perf_counter() - db_start) * 1000, 2)
        logger.error("readiness: database check failed", error=str(exc))
        checks["database"] = ComponentHealthStatus(
            status="unavailable",
            latency_ms=db_latency,
            detail=str(exc),
        )

    # ------------------------------------------------------------------
    # Redis check
    # ------------------------------------------------------------------
    redis_start = time.perf_counter()
    try:
        await redis.ping()
        redis_latency = round((time.perf_counter() - redis_start) * 1000, 2)
        checks["redis"] = ComponentHealthStatus(status="ok", latency_ms=redis_latency)
    except Exception as exc:
        redis_latency = round((time.perf_counter() - redis_start) * 1000, 2)
        logger.error("readiness: redis check failed", error=str(exc))
        checks["redis"] = ComponentHealthStatus(
            status="unavailable",
            latency_ms=redis_latency,
            detail=str(exc),
        )

    all_ok = all(c.status == "ok" for c in checks.values())
    overall_status = "ok" if all_ok else "unavailable"
    http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    response_body = ReadinessResponse(
        status=overall_status,  # type: ignore[arg-type]
        version=settings.APP_VERSION,
        timestamp=datetime.now(tz=timezone.utc),
        checks=checks,
    )

    return JSONResponse(
        content=response_body.model_dump(mode="json"),
        status_code=http_status,
    )


__all__ = ["router"]

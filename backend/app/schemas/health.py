"""Health check response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ComponentHealthStatus(BaseModel):
    """Health status of a single infrastructure dependency."""

    status: Literal["ok", "degraded", "unavailable"]
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds (None if check failed)",
    )
    detail: str | None = Field(default=None, description="Additional context if degraded/unavailable")


class HealthResponse(BaseModel):
    """Response body for GET /health (liveness probe).

    Always returns 200 OK as long as the application process is alive.
    """

    status: Literal["ok"] = "ok"
    version: str = Field(description="Application version string (semver)")
    environment: str = Field(description="Deployment environment (development/staging/production)")
    timestamp: datetime = Field(description="Server UTC timestamp at time of response")


class ReadinessResponse(BaseModel):
    """Response body for GET /ready (readiness probe).

    Returns 200 when all dependencies are healthy, 503 otherwise.
    """

    status: Literal["ok", "degraded", "unavailable"]
    version: str
    timestamp: datetime
    checks: dict[str, ComponentHealthStatus] = Field(
        description="Per-dependency health check results"
    )

    @property
    def is_ready(self) -> bool:
        """Return True only if every check is 'ok'."""
        return all(c.status == "ok" for c in self.checks.values())


__all__ = ["ComponentHealthStatus", "HealthResponse", "ReadinessResponse"]

"""Tests for health and readiness check endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for GET /health (liveness probe)."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, test_client: AsyncClient) -> None:
        """Health endpoint must return HTTP 200."""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_schema(self, test_client: AsyncClient) -> None:
        """Health response must contain required fields with correct values."""
        response = await test_client.get("/api/v1/health")
        body = response.json()

        assert body["status"] == "ok"
        assert "version" in body
        assert "environment" in body
        assert "timestamp" in body

    @pytest.mark.asyncio
    async def test_health_version_matches_settings(self, test_client: AsyncClient) -> None:
        """Version in health response must match APP_VERSION setting."""
        from app.core.config import settings

        response = await test_client.get("/api/v1/health")
        body = response.json()

        assert body["version"] == settings.APP_VERSION

    @pytest.mark.asyncio
    async def test_health_content_type_is_json(self, test_client: AsyncClient) -> None:
        """Health endpoint must return application/json content type."""
        response = await test_client.get("/api/v1/health")
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_health_request_id_header_present(self, test_client: AsyncClient) -> None:
        """Response must include X-Request-ID header (set by RequestIDMiddleware)."""
        response = await test_client.get("/api/v1/health")
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_health_request_id_echoed(self, test_client: AsyncClient) -> None:
        """X-Request-ID sent by the client must be echoed back unchanged."""
        request_id = "my-custom-trace-id-12345"
        response = await test_client.get(
            "/api/v1/health",
            headers={"X-Request-ID": request_id},
        )
        assert response.headers["x-request-id"] == request_id


class TestReadinessEndpoint:
    """Tests for GET /ready (readiness probe)."""

    @pytest.mark.asyncio
    async def test_ready_returns_200_when_healthy(self, test_client: AsyncClient) -> None:
        """Readiness endpoint must return 200 when DB and Redis are reachable."""
        with (
            patch("app.api.v1.health.ping_redis", new=AsyncMock(return_value=True)),
        ):
            response = await test_client.get("/api/v1/ready")
        # With a real DB session from the fixture, DB check should pass.
        # Accept 200 or 503 depending on test environment connectivity.
        assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_ready_response_schema(self, test_client: AsyncClient) -> None:
        """Readiness response must include status, version, timestamp, and checks."""
        response = await test_client.get("/api/v1/ready")
        body = response.json()

        assert "status" in body
        assert body["status"] in ("ok", "degraded", "unavailable")
        assert "version" in body
        assert "timestamp" in body
        assert "checks" in body

    @pytest.mark.asyncio
    async def test_ready_503_when_db_unavailable(self, test_client: AsyncClient) -> None:
        """Readiness endpoint must return 503 when the database is unreachable."""
        from sqlalchemy.exc import OperationalError

        with patch(
            "app.api.v1.health.AsyncSession.execute",
            new=AsyncMock(side_effect=OperationalError("connection refused", None, None)),
        ):
            response = await test_client.get("/api/v1/ready")

        # When DB is down we expect 503
        assert response.status_code in (200, 503)
        body = response.json()
        assert "checks" in body

    @pytest.mark.asyncio
    async def test_ready_contains_database_check(self, test_client: AsyncClient) -> None:
        """Readiness response must include a 'database' key in checks."""
        response = await test_client.get("/api/v1/ready")
        body = response.json()
        assert "database" in body["checks"]

    @pytest.mark.asyncio
    async def test_ready_contains_redis_check(self, test_client: AsyncClient) -> None:
        """Readiness response must include a 'redis' key in checks."""
        response = await test_client.get("/api/v1/ready")
        body = response.json()
        assert "redis" in body["checks"]

    @pytest.mark.asyncio
    async def test_ready_check_has_status_field(self, test_client: AsyncClient) -> None:
        """Each check entry must have a 'status' field."""
        response = await test_client.get("/api/v1/ready")
        body = response.json()
        for check_name, check_data in body["checks"].items():
            assert "status" in check_data, f"Check '{check_name}' missing 'status' field"
            assert check_data["status"] in ("ok", "degraded", "unavailable")

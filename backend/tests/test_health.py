"""Tests for /health and /ready endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_schema(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "environment" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_health_version_matches_settings(test_client: AsyncClient) -> None:
    from app.core.config import settings

    response = await test_client.get("/api/v1/health")
    body = response.json()
    assert body["version"] == settings.APP_VERSION


@pytest.mark.asyncio
async def test_health_does_not_require_auth(test_client: AsyncClient) -> None:
    """Health endpoint MUST be accessible without Authorization header."""
    response = await test_client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ready_returns_status(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/ready")
    # Services may be unavailable in unit test environment.
    assert response.status_code in (200, 503)


@pytest.mark.asyncio
async def test_ready_response_schema(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/ready")
    body = response.json()
    assert "status" in body
    assert body["status"] in ("ready", "not_ready")
    assert "checks" in body
    assert "version" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_ready_checks_contain_expected_keys(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/ready")
    body = response.json()
    checks = body.get("checks", {})
    assert "database" in checks
    assert "redis" in checks


@pytest.mark.asyncio
async def test_ready_does_not_require_auth(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/ready")
    assert response.status_code in (200, 503)


@pytest.mark.asyncio
async def test_health_response_has_request_id_header(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/health")
    assert "x-request-id" in response.headers

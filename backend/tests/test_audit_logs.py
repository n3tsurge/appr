"""Tests for audit log endpoints — /api/v1/audit-logs/."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestAuditLogs:
    """Tests for GET /api/v1/audit-logs."""

    @pytest.mark.asyncio
    async def test_list_audit_logs_admin(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can list audit logs → 200 with paginated response."""
        response = await test_client.get("/api/v1/audit-logs", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)
        assert "total" in body["meta"]
        assert "page" in body["meta"]
        assert "per_page" in body["meta"]

    @pytest.mark.asyncio
    async def test_list_audit_logs_viewer_allowed(
        self,
        test_client: AsyncClient,
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer can also read audit logs → 200."""
        response = await test_client.get("/api/v1/audit-logs", headers=viewer_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_audit_logs_unauthenticated(
        self, test_client: AsyncClient
    ) -> None:
        """No auth → 401."""
        response = await test_client.get("/api/v1/audit-logs")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_audit_logs_filter_by_event_type(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter by event_type parameter returns 200."""
        # First create a service to produce an audit log event
        await test_client.post(
            "/api/v1/services",
            json={"name": "Audit Test Service", "slug": "audit-test-svc"},
            headers=auth_headers,
        )

        response = await test_client.get(
            "/api/v1/audit-logs?event_type=service.created",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        # All returned entries must match the filter if there are any
        for entry in body["data"]:
            assert entry["event_type"] == "service.created"

    @pytest.mark.asyncio
    async def test_audit_logs_filter_by_entity_type(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter by entity_type parameter returns 200."""
        response = await test_client.get(
            "/api/v1/audit-logs?entity_type=Service",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        for entry in body["data"]:
            assert entry["entity_type"] == "Service"

    @pytest.mark.asyncio
    async def test_audit_logs_pagination(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Pagination params are respected."""
        response = await test_client.get(
            "/api/v1/audit-logs?page=1&per_page=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["page"] == 1
        assert body["meta"]["per_page"] == 5
        assert len(body["data"]) <= 5

    @pytest.mark.asyncio
    async def test_audit_logs_response_schema(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Each audit log entry has required fields."""
        # Create an entity to ensure at least one audit log exists
        await test_client.post(
            "/api/v1/services",
            json={"name": "Schema Test Service", "slug": "schema-test-svc"},
            headers=auth_headers,
        )

        response = await test_client.get("/api/v1/audit-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        if data:
            entry = data[0]
            required_fields = {"id", "tenant_id", "event_type", "actor_type", "occurred_at"}
            for field in required_fields:
                assert field in entry, f"Audit log entry missing required field: {field}"

    @pytest.mark.asyncio
    async def test_audit_logs_editor_allowed(
        self,
        test_client: AsyncClient,
        editor_user: User,
        editor_headers: dict[str, str],
    ) -> None:
        """Editor role can read audit logs → 200."""
        response = await test_client.get("/api/v1/audit-logs", headers=editor_headers)
        assert response.status_code == 200

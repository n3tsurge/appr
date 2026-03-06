"""Tests for incident management endpoints — /api/v1/incidents/."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.models.user import User


_INCIDENT_PAYLOAD = {
    "title": "Production Database Outage",
    "description": "The primary database is unreachable",
    "severity": "critical",
    "status": "investigating",
}


# ---------------------------------------------------------------------------
# TestIncidentCRUD
# ---------------------------------------------------------------------------

class TestIncidentCRUD:
    """Full CRUD tests for incident endpoints."""

    @pytest.mark.asyncio
    async def test_create_incident(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Editor/admin can create an incident → 201."""
        response = await test_client.post(
            "/api/v1/incidents",
            json=_INCIDENT_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert "data" in body
        assert body["data"]["title"] == _INCIDENT_PAYLOAD["title"]
        assert body["data"]["severity"] == "critical"
        assert body["data"]["status"] == "investigating"

    @pytest.mark.asyncio
    async def test_list_incidents(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """List incidents returns 200 with paginated structure."""
        response = await test_client.get("/api/v1/incidents", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_get_incident(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Fetching an existing incident by ID → 200."""
        create_resp = await test_client.post(
            "/api/v1/incidents",
            json={**_INCIDENT_PAYLOAD, "title": "Get Incident Test"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["data"]["id"]

        response = await test_client.get(
            f"/api/v1/incidents/{incident_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == incident_id

    @pytest.mark.asyncio
    async def test_get_incident_not_found(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-existent incident ID → 404."""
        response = await test_client.get(
            f"/api/v1/incidents/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_incident(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Updating an incident → 200 with updated data."""
        create_resp = await test_client.post(
            "/api/v1/incidents",
            json={**_INCIDENT_PAYLOAD, "title": "Update Me Incident"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["data"]["id"]

        update_resp = await test_client.put(
            f"/api/v1/incidents/{incident_id}",
            json={"title": "Updated Incident Title", "status": "identified"},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        data = update_resp.json()["data"]
        assert data["title"] == "Updated Incident Title"
        assert data["status"] == "identified"

    @pytest.mark.asyncio
    async def test_delete_incident(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can soft-delete an incident → 204."""
        create_resp = await test_client.post(
            "/api/v1/incidents",
            json={**_INCIDENT_PAYLOAD, "title": "To Delete Incident"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["data"]["id"]

        response = await test_client.delete(
            f"/api/v1/incidents/{incident_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Confirm it's gone
        get_resp = await test_client.get(
            f"/api/v1/incidents/{incident_id}", headers=auth_headers
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_timeline_entry(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Adding a timeline entry to an existing incident → 201."""
        create_resp = await test_client.post(
            "/api/v1/incidents",
            json={**_INCIDENT_PAYLOAD, "title": "Timeline Entry Incident"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["data"]["id"]

        entry_payload = {
            "occurred_at": datetime.now(tz=timezone.utc).isoformat(),
            "entry_type": "observation",
            "message": "Engineers are investigating root cause",
        }
        response = await test_client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json=entry_payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["data"]["entry_type"] == "observation"
        assert body["data"]["incident_id"] == incident_id

    @pytest.mark.asyncio
    async def test_resolve_incident(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Resolving an incident → 200 with status=resolved."""
        create_resp = await test_client.post(
            "/api/v1/incidents",
            json={**_INCIDENT_PAYLOAD, "title": "Resolve Me Incident"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["data"]["id"]

        resolve_resp = await test_client.post(
            f"/api/v1/incidents/{incident_id}/resolve",
            json={"resolution_note": "Issue resolved after restart"},
            headers=auth_headers,
        )
        assert resolve_resp.status_code == 200
        data = resolve_resp.json()["data"]
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_incident(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Resolving an already-resolved incident → 400."""
        create_resp = await test_client.post(
            "/api/v1/incidents",
            json={**_INCIDENT_PAYLOAD, "title": "Already Resolved"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["data"]["id"]

        # First resolve
        await test_client.post(
            f"/api/v1/incidents/{incident_id}/resolve",
            json={},
            headers=auth_headers,
        )

        # Second resolve attempt
        response = await test_client.post(
            f"/api/v1/incidents/{incident_id}/resolve",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_incidents_viewer_allowed(
        self,
        test_client: AsyncClient,
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer can list incidents (read-only access)."""
        response = await test_client.get("/api/v1/incidents", headers=viewer_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_incident_viewer_forbidden(
        self,
        test_client: AsyncClient,
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer cannot create incidents → 403."""
        response = await test_client.post(
            "/api/v1/incidents",
            json=_INCIDENT_PAYLOAD,
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_incident_unauthenticated(self, test_client: AsyncClient) -> None:
        """Unauthenticated request → 401."""
        response = await test_client.get("/api/v1/incidents")
        assert response.status_code == 401

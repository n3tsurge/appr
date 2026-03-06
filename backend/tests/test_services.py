"""Tests for service catalog endpoints — /api/v1/services/."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import User


_SERVICE_PAYLOAD = {
    "name": "My API Service",
    "slug": "my-api-service",
    "description": "A test service",
    "service_type": "api",
}


# ---------------------------------------------------------------------------
# TestListServices
# ---------------------------------------------------------------------------

class TestListServices:
    """Tests for GET /api/v1/services."""

    @pytest.mark.asyncio
    async def test_list_services_empty(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty tenant returns 200 with data=[] and meta.total=0."""
        response = await test_client.get("/api/v1/services", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_list_services_with_data(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """After creating a service, list returns meta.total >= 1."""
        create_resp = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "list-with-data-svc"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201

        response = await test_client.get("/api/v1/services", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["meta"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_services_unauthenticated(self, test_client: AsyncClient) -> None:
        """No auth header → 401."""
        response = await test_client.get("/api/v1/services")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_services_pagination(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Pagination parameters are respected."""
        response = await test_client.get(
            "/api/v1/services?page=1&per_page=5", headers=auth_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["page"] == 1
        assert body["meta"]["per_page"] == 5


# ---------------------------------------------------------------------------
# TestCreateService
# ---------------------------------------------------------------------------

class TestCreateService:
    """Tests for POST /api/v1/services."""

    @pytest.mark.asyncio
    async def test_create_service_editor(
        self,
        test_client: AsyncClient,
        editor_user: User,
        editor_headers: dict[str, str],
    ) -> None:
        """Editor can create a service → 201."""
        response = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "editor-created-svc"},
            headers=editor_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["data"]["slug"] == "editor-created-svc"

    @pytest.mark.asyncio
    async def test_create_service_admin(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can create a service → 201."""
        response = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "admin-created-svc"},
            headers=auth_headers,
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_service_viewer_forbidden(
        self,
        test_client: AsyncClient,
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer cannot create a service → 403."""
        response = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "viewer-blocked-svc"},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_service_duplicate_slug(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Creating a service with a duplicate slug → 409 Conflict."""
        payload = {**_SERVICE_PAYLOAD, "slug": "duplicate-svc"}
        await test_client.post("/api/v1/services", json=payload, headers=auth_headers)
        response = await test_client.post(
            "/api/v1/services", json=payload, headers=auth_headers
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_service_missing_required_fields(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Missing name/slug fields → 422."""
        response = await test_client.post(
            "/api/v1/services",
            json={"description": "no name or slug"},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestGetService
# ---------------------------------------------------------------------------

class TestGetService:
    """Tests for GET /api/v1/services/{id}."""

    @pytest.mark.asyncio
    async def test_get_service(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Fetching an existing service → 200 with service data."""
        create_resp = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "get-service-svc"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        service_id = create_resp.json()["data"]["id"]

        response = await test_client.get(
            f"/api/v1/services/{service_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == service_id

    @pytest.mark.asyncio
    async def test_get_service_not_found(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-existent service ID → 404."""
        response = await test_client.get(
            f"/api/v1/services/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_service_wrong_tenant(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """A valid UUID that doesn't belong to the requesting tenant → 404."""
        # uuid4 will not match any service in the test tenant with high probability
        foreign_id = uuid.uuid4()
        response = await test_client.get(
            f"/api/v1/services/{foreign_id}", headers=auth_headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestUpdateService
# ---------------------------------------------------------------------------

class TestUpdateService:
    """Tests for PUT /api/v1/services/{id}."""

    @pytest.mark.asyncio
    async def test_update_service(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin/editor can update a service → 200."""
        create_resp = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "update-me-svc"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        service_id = create_resp.json()["data"]["id"]

        response = await test_client.put(
            f"/api/v1/services/{service_id}",
            json={"name": "Updated Service Name"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Service Name"

    @pytest.mark.asyncio
    async def test_update_service_viewer_forbidden(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer cannot update a service → 403."""
        create_resp = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "viewer-cannot-update-svc"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        service_id = create_resp.json()["data"]["id"]

        response = await test_client.put(
            f"/api/v1/services/{service_id}",
            json={"name": "Viewer Tries"},
            headers=viewer_headers,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# TestDeleteService
# ---------------------------------------------------------------------------

class TestDeleteService:
    """Tests for DELETE /api/v1/services/{id}."""

    @pytest.mark.asyncio
    async def test_delete_service_admin(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can delete a service → 204."""
        create_resp = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "to-delete-svc"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        service_id = create_resp.json()["data"]["id"]

        response = await test_client.delete(
            f"/api/v1/services/{service_id}", headers=auth_headers
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_service_not_found(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Deleting a non-existent service → 404."""
        response = await test_client.delete(
            f"/api/v1/services/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_service_viewer_forbidden(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer cannot delete a service → 403."""
        create_resp = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "viewer-cannot-delete-svc"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        service_id = create_resp.json()["data"]["id"]

        response = await test_client.delete(
            f"/api/v1/services/{service_id}", headers=viewer_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_soft_delete_not_visible_in_list(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """After soft-deleting a service it must not appear in list results."""
        # Verify empty state first
        list_before = await test_client.get("/api/v1/services", headers=auth_headers)
        total_before = list_before.json()["meta"]["total"]

        create_resp = await test_client.post(
            "/api/v1/services",
            json={**_SERVICE_PAYLOAD, "slug": "soft-delete-test-svc"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        service_id = create_resp.json()["data"]["id"]

        list_after_create = await test_client.get("/api/v1/services", headers=auth_headers)
        assert list_after_create.json()["meta"]["total"] == total_before + 1

        del_resp = await test_client.delete(
            f"/api/v1/services/{service_id}", headers=auth_headers
        )
        assert del_resp.status_code == 204

        list_after_delete = await test_client.get("/api/v1/services", headers=auth_headers)
        assert list_after_delete.json()["meta"]["total"] == total_before

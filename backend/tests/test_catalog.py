"""Parametrized CRUD tests for all catalog entity types.

Each entity type is tested for: create, list, get-by-id, and delete.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# Parametrize over all catalog entity types
# ---------------------------------------------------------------------------

CATALOG_ENTITIES = [
    (
        "products",
        {
            "name": "Test Product",
            "slug": "test-product",
        },
    ),
    (
        "components",
        {
            "name": "Test Component",
            "slug": "test-component",
            "component_type": "library",
        },
    ),
    (
        "teams",
        {
            "name": "Test Team",
            "slug": "test-team",
        },
    ),
    (
        "people",
        {
            "first_name": "Test",
            "last_name": "Person",
            "display_name": "Test Person",
            "email": "person@test.example.com",
        },
    ),
    (
        "repositories",
        {
            "name": "Test Repo",
            "full_name": "org/test-repo",
            "provider": "github",
        },
    ),
    (
        "resources",
        {
            "name": "Test Resource",
            "slug": "test-resource",
            "resource_type": "ec2",
        },
    ),
    (
        "scorecards",
        {
            "name": "Test Scorecard",
            "slug": "test-scorecard",
            "entity_type": "service",
        },
    ),
]

# Unique slug/email suffixes per test run to avoid conflicts within the same
# module-scoped DB – parametrize generates a unique id automatically.
_COUNTER: dict[str, int] = {}


def _unique_payload(entity: str, payload: dict) -> dict:
    """Return the payload with a uniquified slug/email to prevent 409s."""
    _COUNTER[entity] = _COUNTER.get(entity, 0) + 1
    idx = _COUNTER[entity]
    result = dict(payload)
    if "slug" in result:
        result["slug"] = f"{result['slug']}-{idx}"
    if entity == "people":
        base_email = result.get("email", "person@test.example.com")
        local, domain = base_email.split("@", 1)
        result["email"] = f"{local}+{idx}@{domain}"
    if entity == "repositories":
        result["full_name"] = f"org/test-repo-{idx}"
    return result


# ---------------------------------------------------------------------------
# TestCatalogEntitiesCRUD
# ---------------------------------------------------------------------------

class TestCatalogEntitiesCRUD:
    """Parametrized CRUD tests for catalog entities."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_create_entity(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """POST /api/v1/{entity} → 201 with entity data."""
        unique_payload = _unique_payload(entity, payload)
        response = await test_client.post(
            f"/api/v1/{entity}",
            json=unique_payload,
            headers=auth_headers,
        )
        assert response.status_code == 201, (
            f"Creating {entity} failed: {response.status_code} - {response.text}"
        )
        body = response.json()
        assert "data" in body
        assert "id" in body["data"]
        assert "tenant_id" in body["data"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_list_entity(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /api/v1/{entity} → 200 with valid paginated response."""
        response = await test_client.get(f"/api/v1/{entity}", headers=auth_headers)
        assert response.status_code == 200, (
            f"Listing {entity} failed: {response.status_code} - {response.text}"
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)
        assert "total" in body["meta"]
        assert "page" in body["meta"]
        assert "per_page" in body["meta"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_get_entity(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """POST then GET by id → 200 with matching data."""
        unique_payload = _unique_payload(entity, payload)
        create_resp = await test_client.post(
            f"/api/v1/{entity}",
            json=unique_payload,
            headers=auth_headers,
        )
        assert create_resp.status_code == 201, (
            f"Create before get failed for {entity}: {create_resp.text}"
        )
        entity_id = create_resp.json()["data"]["id"]

        get_resp = await test_client.get(
            f"/api/v1/{entity}/{entity_id}", headers=auth_headers
        )
        assert get_resp.status_code == 200, (
            f"Get {entity}/{entity_id} failed: {get_resp.status_code} - {get_resp.text}"
        )
        assert get_resp.json()["data"]["id"] == entity_id

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_delete_entity(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """POST then DELETE → 204; subsequent GET → 404."""
        unique_payload = _unique_payload(entity, payload)
        create_resp = await test_client.post(
            f"/api/v1/{entity}",
            json=unique_payload,
            headers=auth_headers,
        )
        assert create_resp.status_code == 201, (
            f"Create before delete failed for {entity}: {create_resp.text}"
        )
        entity_id = create_resp.json()["data"]["id"]

        del_resp = await test_client.delete(
            f"/api/v1/{entity}/{entity_id}", headers=auth_headers
        )
        assert del_resp.status_code == 204, (
            f"Delete {entity}/{entity_id} failed: {del_resp.status_code} - {del_resp.text}"
        )

        get_resp = await test_client.get(
            f"/api/v1/{entity}/{entity_id}", headers=auth_headers
        )
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Additional entity-specific tests
# ---------------------------------------------------------------------------

class TestCatalogEntityNotFound:
    """Test 404 handling for each entity type."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_get_nonexistent_entity(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /api/v1/{entity}/{random_uuid} → 404."""
        import uuid
        response = await test_client.get(
            f"/api/v1/{entity}/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_list_unauthenticated(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
    ) -> None:
        """GET /api/v1/{entity} without auth → 401."""
        response = await test_client.get(f"/api/v1/{entity}")
        assert response.status_code == 401


class TestCatalogEntityViewerAccess:
    """Verify viewer role can list and read catalog entities."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_viewer_can_list(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer role can list catalog entities (read-only)."""
        response = await test_client.get(f"/api/v1/{entity}", headers=viewer_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entity,payload", CATALOG_ENTITIES)
    async def test_viewer_cannot_create(
        self,
        entity: str,
        payload: dict,
        test_client: AsyncClient,
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer role cannot create catalog entities → 403."""
        unique_payload = _unique_payload(entity, payload)
        response = await test_client.post(
            f"/api/v1/{entity}",
            json=unique_payload,
            headers=viewer_headers,
        )
        assert response.status_code == 403

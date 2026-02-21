"""Tests for user management endpoints — /api/v1/users/."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# TestListUsers
# ---------------------------------------------------------------------------

class TestListUsers:
    """Tests for GET /api/v1/users."""

    @pytest.mark.asyncio
    async def test_list_users_admin(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can list users; response has paginated structure."""
        response = await test_client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)
        assert "total" in body["meta"]
        # At least the test_user we created should be in the list
        assert body["meta"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_users_viewer_forbidden(
        self,
        test_client: AsyncClient,
        viewer_user: User,
        viewer_headers: dict[str, str],
    ) -> None:
        """Viewer role → 403 Forbidden."""
        response = await test_client.get("/api/v1/users", headers=viewer_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_users_unauthenticated(self, test_client: AsyncClient) -> None:
        """No auth header → 401."""
        response = await test_client.get("/api/v1/users")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_users_editor_forbidden(
        self,
        test_client: AsyncClient,
        editor_user: User,
        editor_headers: dict[str, str],
    ) -> None:
        """Editor role → 403 (admin-only endpoint)."""
        response = await test_client.get("/api/v1/users", headers=editor_headers)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# TestCreateUser
# ---------------------------------------------------------------------------

class TestCreateUser:
    """Tests for POST /api/v1/users."""

    @pytest.mark.asyncio
    async def test_create_user_admin(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can create a user → 201 with user in response."""
        payload = {
            "email": "newuser@test.example.com",
            "display_name": "New User",
            "password": "SecurePass123!",
            "role": "viewer",
        }
        response = await test_client.post("/api/v1/users", json=payload, headers=auth_headers)
        assert response.status_code == 201
        body = response.json()
        assert "data" in body
        assert body["data"]["email"] == "newuser@test.example.com"
        assert body["data"]["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Creating a user with an existing email → 409 Conflict."""
        payload = {
            "email": "admin@test.example.com",  # same as test_user
            "display_name": "Duplicate",
            "password": "SecurePass123!",
            "role": "viewer",
        }
        response = await test_client.post("/api/v1/users", json=payload, headers=auth_headers)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_user_non_admin(
        self,
        test_client: AsyncClient,
        editor_user: User,
        editor_headers: dict[str, str],
    ) -> None:
        """Non-admin (editor) trying to create a user → 403."""
        payload = {
            "email": "another@test.example.com",
            "display_name": "Another",
            "password": "SecurePass123!",
            "role": "viewer",
        }
        response = await test_client.post(
            "/api/v1/users", json=payload, headers=editor_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_user_missing_required_fields(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Missing required fields → 422."""
        response = await test_client.post(
            "/api/v1/users",
            json={"email": "incomplete@test.example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestGetUser
# ---------------------------------------------------------------------------

class TestGetUser:
    """Tests for GET /api/v1/users/{id}."""

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Fetching an existing user by ID → 200 with user data."""
        response = await test_client.get(
            f"/api/v1/users/{test_user.id}", headers=auth_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["id"] == str(test_user.id)
        assert body["data"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-existent user ID → 404."""
        nonexistent = uuid.uuid4()
        response = await test_client.get(
            f"/api/v1/users/{nonexistent}", headers=auth_headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestUpdateUser
# ---------------------------------------------------------------------------

class TestUpdateUser:
    """Tests for PUT /api/v1/users/{id}."""

    @pytest.mark.asyncio
    async def test_update_user(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can update a user's display_name → 200."""
        # First create a user to update (avoid modifying test_user)
        create_resp = await test_client.post(
            "/api/v1/users",
            json={
                "email": "toupdate@test.example.com",
                "display_name": "Before Update",
                "password": "SecurePass123!",
                "role": "viewer",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["data"]["id"]

        response = await test_client.put(
            f"/api/v1/users/{user_id}",
            json={"display_name": "After Update"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["display_name"] == "After Update"

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Updating a non-existent user → 404."""
        nonexistent = uuid.uuid4()
        response = await test_client.put(
            f"/api/v1/users/{nonexistent}",
            json={"display_name": "Ghost"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_role(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can change user role → 200 with updated role."""
        create_resp = await test_client.post(
            "/api/v1/users",
            json={
                "email": "rolechange@test.example.com",
                "display_name": "Role Change",
                "password": "SecurePass123!",
                "role": "viewer",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["data"]["id"]

        response = await test_client.put(
            f"/api/v1/users/{user_id}",
            json={"role": "editor"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["role"] == "editor"


# ---------------------------------------------------------------------------
# TestDeleteUser
# ---------------------------------------------------------------------------

class TestDeleteUser:
    """Tests for DELETE /api/v1/users/{id}."""

    @pytest.mark.asyncio
    async def test_delete_user(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin can soft-delete a user → 204."""
        # Create a dedicated user to delete
        create_resp = await test_client.post(
            "/api/v1/users",
            json={
                "email": "todelete@test.example.com",
                "display_name": "To Delete",
                "password": "SecurePass123!",
                "role": "viewer",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["data"]["id"]

        response = await test_client.delete(
            f"/api/v1/users/{user_id}", headers=auth_headers
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_self_forbidden(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Admin cannot delete themselves → 400."""
        response = await test_client.delete(
            f"/api/v1/users/{test_user.id}", headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        test_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Deleting a non-existent user → 404."""
        nonexistent = uuid.uuid4()
        response = await test_client.delete(
            f"/api/v1/users/{nonexistent}", headers=auth_headers
        )
        assert response.status_code == 404

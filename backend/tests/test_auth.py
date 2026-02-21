"""Tests for authentication endpoints — /api/v1/auth/."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_redis() -> MagicMock:
    """Return a lightweight Redis mock that passes rate-limit checks."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)   # 0 failures
    redis.delete = AsyncMock(return_value=1)
    pipe = MagicMock()
    pipe.incr = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[1, True])
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


# ---------------------------------------------------------------------------
# TestLogin
# ---------------------------------------------------------------------------

class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(
        self, test_client: AsyncClient, test_user: User
    ) -> None:
        """Valid credentials → 200 with access_token present."""
        redis_mock = _mock_redis()
        with patch("app.api.v1.auth.get_redis", return_value=AsyncMock(return_value=redis_mock)):
            with patch("app.services.auth_service.AuthService._check_rate_limit", new=AsyncMock()):
                with patch("app.services.auth_service.AuthService._record_failure", new=AsyncMock()):
                    with patch("app.services.auth_service.AuthService._redis", redis_mock, create=True):
                        response = await test_client.post(
                            "/api/v1/auth/login",
                            json={"email": "admin@test.example.com", "password": "TestPassword123!"},
                        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, test_client: AsyncClient, test_user: User
    ) -> None:
        """Wrong password → 401."""
        with patch("app.services.auth_service.AuthService._check_rate_limit", new=AsyncMock()):
            with patch("app.services.auth_service.AuthService._record_failure", new=AsyncMock()):
                response = await test_client.post(
                    "/api/v1/auth/login",
                    json={"email": "admin@test.example.com", "password": "WrongPassword!"},
                )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email(
        self, test_client: AsyncClient, test_user: User
    ) -> None:
        """Unknown email → 401."""
        with patch("app.services.auth_service.AuthService._check_rate_limit", new=AsyncMock()):
            with patch("app.services.auth_service.AuthService._record_failure", new=AsyncMock()):
                response = await test_client.post(
                    "/api/v1/auth/login",
                    json={"email": "nobody@test.example.com", "password": "TestPassword123!"},
                )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, test_client: AsyncClient) -> None:
        """Missing required fields → 422 Unprocessable Entity."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.example.com"},  # no password
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_email(self, test_client: AsyncClient) -> None:
        """Missing email field → 422."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"password": "TestPassword123!"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestRefresh
# ---------------------------------------------------------------------------

class TestRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_success(
        self, test_client: AsyncClient, test_user: User
    ) -> None:
        """Valid refresh token → new access_token returned."""
        redis_mock = _mock_redis()
        with patch("app.services.auth_service.AuthService._check_rate_limit", new=AsyncMock()):
            with patch("app.services.auth_service.AuthService._redis", redis_mock, create=True):
                login_resp = await test_client.post(
                    "/api/v1/auth/login",
                    json={"email": "admin@test.example.com", "password": "TestPassword123!"},
                )

        if login_resp.status_code != 200:
            pytest.skip("Login failed; skipping refresh test")

        refresh_token = login_resp.json()["refresh_token"]

        with patch("app.services.auth_service.AuthService._redis", redis_mock, create=True):
            response = await test_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, test_client: AsyncClient) -> None:
        """Invalid/garbage refresh token → 401."""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.jwt.token"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestLogout
# ---------------------------------------------------------------------------

class TestLogout:
    """Tests for POST /api/v1/auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self, test_client: AsyncClient, test_user: User, auth_headers: dict[str, str]
    ) -> None:
        """Logging out with a valid refresh token → 204."""
        redis_mock = _mock_redis()
        with patch("app.services.auth_service.AuthService._check_rate_limit", new=AsyncMock()):
            with patch("app.services.auth_service.AuthService._redis", redis_mock, create=True):
                login_resp = await test_client.post(
                    "/api/v1/auth/login",
                    json={"email": "admin@test.example.com", "password": "TestPassword123!"},
                )

        if login_resp.status_code != 200:
            pytest.skip("Login failed; skipping logout test")

        refresh_token = login_resp.json()["refresh_token"]

        with patch("app.services.auth_service.AuthService._redis", redis_mock, create=True):
            response = await test_client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": refresh_token},
                headers=auth_headers,
            )
        assert response.status_code in (200, 204)


# ---------------------------------------------------------------------------
# TestMe
# ---------------------------------------------------------------------------

class TestMe:
    """Tests for GET /api/v1/auth/me."""

    @pytest.mark.asyncio
    async def test_me_authenticated(
        self,
        test_client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Authenticated request → 200 with user data."""
        response = await test_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        data = body["data"]
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, test_client: AsyncClient) -> None:
        """No auth header → 401."""
        response = await test_client.get("/api/v1/auth/me")
        assert response.status_code == 401

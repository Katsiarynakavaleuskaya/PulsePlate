"""
Tests for Users Router using isolated TestClient

RU: Тесты роутера users через изолированный TestClient.
EN: Users router tests via isolated TestClient.

Covers:
- POST /api/v1/users (create user)
- GET /api/v1/users (list users)
- GET /api/v1/users/{user_id} (get user)
- DELETE /api/v1/users/{user_id} (delete user)
- Validation errors (422/400)
- Database retry logic (503 on exhaustion)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import app.routers.users as users_mod
from tests._helpers.api_headers import API_KEY_HEADERS


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent time.sleep in retry logic to avoid test hangs."""
    import time

    monkeypatch.setattr(time, "sleep", lambda _: None)


class TestUsersRouter:
    """Test users router with isolated FastAPI app."""

    def setup_method(self) -> None:
        """Set up test client with isolated router."""
        from app.routers.users import router

        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        self.headers = API_KEY_HEADERS

    def teardown_method(self) -> None:
        """Clean up test client."""
        self.client.close()

    def test_list_users_default_pagination(self) -> None:
        """GET /api/v1/users returns list with default limit/offset."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_session.execute.return_value.scalars.return_value.all.return_value = []
            mock_factory.return_value = lambda: mock_session

            resp = self.client.get("/api/v1/users", headers=self.headers)

            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)

    def test_list_users_custom_pagination(self) -> None:
        """GET /api/v1/users respects limit/offset params."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_session.execute.return_value.scalars.return_value.all.return_value = []
            mock_factory.return_value = lambda: mock_session

            resp = self.client.get("/api/v1/users?limit=10&offset=5", headers=self.headers)

            assert resp.status_code == 200

    def test_list_users_invalid_pagination_422(self) -> None:
        """GET /api/v1/users with invalid pagination returns 422."""
        # limit too high
        resp = self.client.get("/api/v1/users?limit=2000", headers=self.headers)
        assert resp.status_code == 422

        # negative offset
        resp = self.client.get("/api/v1/users?offset=-1", headers=self.headers)
        assert resp.status_code == 422

    def test_create_user_success(self) -> None:
        """POST /api/v1/users with valid payload returns 201."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()

            # Mock User object with proper attributes
            from app.schemas.users import UserRead

            def mock_validate(user):
                return UserRead(id=1, email="test@example.com", name="Test User")

            with patch.object(UserRead, "model_validate", side_effect=mock_validate):
                mock_factory.return_value = lambda: mock_session

                resp = self.client.post(
                    "/api/v1/users",
                    json={"email": "test@example.com", "name": "Test User"},
                    headers=self.headers,
                )

                assert resp.status_code == 201

    def test_create_user_missing_email_422(self) -> None:
        """POST /api/v1/users without email returns 422."""
        resp = self.client.post("/api/v1/users", json={"name": "Test User"}, headers=self.headers)
        assert resp.status_code == 422

    def test_create_user_empty_payload_422(self) -> None:
        """POST /api/v1/users with empty payload returns 422."""
        resp = self.client.post("/api/v1/users", json={}, headers=self.headers)
        assert resp.status_code == 422

    def test_get_user_not_found_404(self) -> None:
        """GET /api/v1/users/{user_id} returns 404 when user doesn't exist."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = None  # User not found
            mock_factory.return_value = lambda: mock_session

            resp = self.client.get("/api/v1/users/999", headers=self.headers)

            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()

    def test_get_user_success(self) -> None:
        """GET /api/v1/users/{user_id} returns 200 when user exists."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.name = "Test User"
            mock_session.get.return_value = mock_user
            mock_factory.return_value = lambda: mock_session

            resp = self.client.get("/api/v1/users/1", headers=self.headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 1
            assert data["email"] == "test@example.com"
            assert data["name"] == "Test User"

    def test_delete_user_success_204(self) -> None:
        """DELETE /api/v1/users/{user_id} returns 204 on success."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_user = MagicMock()
            mock_session.get.return_value = mock_user
            mock_factory.return_value = lambda: mock_session

            resp = self.client.delete("/api/v1/users/1", headers=self.headers)

            assert resp.status_code == 204

    def test_delete_user_not_found_still_204(self) -> None:
        """DELETE /api/v1/users/{user_id} returns 204 even if user doesn't exist (idempotent)."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_session.get.return_value = None  # User not found
            mock_factory.return_value = lambda: mock_session

            resp = self.client.delete("/api/v1/users/999", headers=self.headers)

            # Idempotent delete design per docstring
            assert resp.status_code == 204

    def test_db_operational_error_retry_then_503(self) -> None:
        """Test that OperationalError triggers retry logic and eventually returns 503."""
        with patch("app.routers.users.db_module.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            # Simulate persistent OperationalError (all retries fail)
            mock_session.execute.side_effect = OperationalError("DB locked", None, None)
            mock_factory.return_value = lambda: mock_session

            resp = self.client.get("/api/v1/users", headers=self.headers)

            assert resp.status_code == 503
            assert "unavailable" in resp.json()["detail"].lower()

    def test_db_operational_error_then_success(self) -> None:
        """Test retry recovery: OperationalError on first attempt, then succeeds."""
        with patch.object(users_mod.db_module, "get_session_factory") as mock_factory:
            mock_session = MagicMock()

            # First call fails, second succeeds
            mock_session.execute.side_effect = [
                OperationalError("DB locked", None, None),
                MagicMock(scalars=lambda: MagicMock(all=lambda: [])),
            ]
            mock_factory.return_value = lambda: mock_session

            resp = self.client.get("/api/v1/users", headers=self.headers)

            assert resp.status_code == 200
            assert resp.json() == []

    def test_users_surface_requires_api_key(self) -> None:
        resp = self.client.get("/api/v1/users")
        assert resp.status_code == 403

    @pytest.mark.parametrize("validator", [None, lambda _: object()])
    def test_users_api_key_guard_fail_closed_behavior(self, validator: object) -> None:
        with patch.object(users_mod, "resolve_attr", return_value=validator):
            resp = self.client.get("/api/v1/users", headers=self.headers)

        assert resp.status_code == 500
        assert resp.json()["detail"] == "API key validation unavailable"

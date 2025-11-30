"""API tests for user CRUD endpoints."""

from __future__ import annotations

from typing import Generator, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from starlette.types import ASGIApp

import app
from core import db as db_module


@pytest.fixture(autouse=True)
def _cleanup_users() -> Generator[None, None, None]:
    """RU: Очищает таблицу пользователей между тестами.

    EN: Ensure users table is cleared between tests.
    """

    def _truncate() -> None:
        with db_module.session_scope() as session:
            session.execute(text("DELETE FROM users"))

    try:
        _truncate()
    except OperationalError:
        # Skip cleanup if database is not accessible
        # Database should be initialized by conftest.py fixture
        pytest.skip("Database not accessible, skipping user cleanup")

    yield

    # Cleanup after test
    try:
        with db_module.session_scope() as session:
            session.execute(text("DELETE FROM users"))
    except OperationalError:
        # Gracefully handle cleanup failure in isolated test environments
        pass


def _client() -> TestClient:
    return TestClient(cast(ASGIApp, app.app))


def test_create_and_get_user() -> None:
    with _client() as client:
        response = client.post("/api/v1/users", json={"email": "ann@example.com", "name": "Ann"})
        assert response.status_code == 201
        payload = response.json()
        assert payload["email"] == "ann@example.com"
        user_id = payload["id"]

        fetched = client.get(f"/api/v1/users/{user_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Ann"


def test_list_users_pagination() -> None:
    with _client() as client:
        for idx in range(3):
            client.post(
                "/api/v1/users",
                json={"email": f"user{idx}@example.com", "name": f"User {idx}"},
            )

        page = client.get("/api/v1/users", params={"limit": 2, "offset": 1})
        assert page.status_code == 200
        data = page.json()
        assert len(data) == 2
        assert data[0]["email"] == "user1@example.com"


def test_create_user_conflict() -> None:
    with _client() as client:
        client.post("/api/v1/users", json={"email": "dup@example.com", "name": "One"})
        duplicate = client.post("/api/v1/users", json={"email": "dup@example.com", "name": "Two"})
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == "Email already exists"


def test_get_user_not_found() -> None:
    with _client() as client:
        response = client.get("/api/v1/users/9999")
    assert response.status_code == 404


def test_delete_user_success_and_not_found() -> None:
    with _client() as client:
        created = client.post("/api/v1/users", json={"email": "del@example.com", "name": "Del"})
        user_id = created.json()["id"]

        delete_resp = client.delete(f"/api/v1/users/{user_id}")
        assert delete_resp.status_code == 204

        missing = client.delete(f"/api/v1/users/{user_id}")
        assert missing.status_code == 404


def test_create_user_validation_error() -> None:
    with _client() as client:
        bad = client.post("/api/v1/users", json={"email": "not-an-email", "name": ""})
    assert bad.status_code == 422

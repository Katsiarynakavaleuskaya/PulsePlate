"""API tests for user CRUD endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_create_and_get_user(client: TestClient) -> None:
    response = client.post("/api/v1/users", json={"email": "ann@example.com", "name": "Ann"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "ann@example.com"
    user_id = payload["id"]

    fetched = client.get(f"/api/v1/users/{user_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Ann"


def test_list_users_pagination(client: TestClient) -> None:
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


def test_create_user_conflict(client: TestClient) -> None:
    client.post("/api/v1/users", json={"email": "dup@example.com", "name": "One"})
    duplicate = client.post("/api/v1/users", json={"email": "dup@example.com", "name": "Two"})
    assert duplicate.status_code == 409
    assert "Data conflict" in duplicate.json()["detail"]
    assert "constraints" in duplicate.json()["detail"]


def test_get_user_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/users/9999")
    assert response.status_code == 404


def test_delete_user_success_and_idempotent(client: TestClient) -> None:
    """DELETE should be idempotent - return 204 even if user doesn't exist."""
    created = client.post("/api/v1/users", json={"email": "del@example.com", "name": "Del"})
    user_id = created.json()["id"]

    delete_resp = client.delete(f"/api/v1/users/{user_id}")
    assert delete_resp.status_code == 204

    # Second delete should also return 204 (idempotent behavior)
    missing = client.delete(f"/api/v1/users/{user_id}")
    assert missing.status_code == 204


def test_create_user_validation_error(client: TestClient) -> None:
    bad = client.post("/api/v1/users", json={"email": "not-an-email", "name": ""})
    assert bad.status_code == 422

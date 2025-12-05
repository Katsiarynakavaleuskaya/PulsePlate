"""API tests for user CRUD endpoints."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, cast
import tempfile
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from starlette.types import ASGIApp

import app
import importlib


@contextmanager
def _client() -> Generator[TestClient, None, None]:
    """Create an isolated TestClient with a per-test SQLite DB and clean environment."""

    cache_root = Path("cache")
    cache_root.mkdir(parents=True, exist_ok=True)

    temp_dir = tempfile.TemporaryDirectory(prefix="users_api_db_", dir=str(cache_root))
    db_path = Path(temp_dir.name) / "test_app.sqlite"

    prev_test_db = os.environ.get("TEST_DB_PATH")
    prev_db_url = os.environ.get("DATABASE_URL")
    os.environ["TEST_DB_PATH"] = str(db_path)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    db_module = importlib.import_module("core.db")
    importlib.reload(db_module)
    app_mod = importlib.reload(app)

    db_module.init_db()
    from core import models as models_module

    models_module.Base.metadata.create_all(bind=db_module.engine)

    client = TestClient(cast(ASGIApp, app_mod.app))
    try:
        yield client
    finally:
        temp_dir.cleanup()
        # Restore prior env values
        if prev_test_db is None:
            os.environ.pop("TEST_DB_PATH", None)
        else:
            os.environ["TEST_DB_PATH"] = prev_test_db
        if prev_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev_db_url


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


def test_delete_user_success_and_idempotent() -> None:
    """DELETE should be idempotent - return 204 even if user doesn't exist."""
    with _client() as client:
        created = client.post("/api/v1/users", json={"email": "del@example.com", "name": "Del"})
        user_id = created.json()["id"]

        delete_resp = client.delete(f"/api/v1/users/{user_id}")
        assert delete_resp.status_code == 204

        # Second delete should also return 204 (idempotent behavior)
        missing = client.delete(f"/api/v1/users/{user_id}")
        assert missing.status_code == 204


def test_create_user_validation_error() -> None:
    with _client() as client:
        bad = client.post("/api/v1/users", json={"email": "not-an-email", "name": ""})
    assert bad.status_code == 422

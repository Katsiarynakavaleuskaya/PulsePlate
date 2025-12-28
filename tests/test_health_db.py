"""Database health endpoint tests."""

from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app
from core import db as db_module


def test_health_db_ok() -> None:
    """RU: Проверка, что /health/db возвращает 200. EN: Ensure /health/db succeeds."""

    with TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_failure(monkeypatch) -> None:
    """RU: Ошибка БД приводит к 503. EN: DB failure surfaces as 503."""
    with TestClient(cast(ASGIApp, app.app)) as client:
        # legacy_app.lifespan clears DB_HEALTH_DEGRADED on successful init_db()
        # so we must set it AFTER startup to exercise the 503 branch.
        monkeypatch.setenv("DB_HEALTH_DEGRADED", "1")
        response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"].lower().startswith("database")

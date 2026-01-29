"""Database health and readiness endpoint tests."""

from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app
from core import db as db_module

# RU: /ready - alias для /health/db, тестируем оба пути.
# EN: /ready is an alias for /health/db, test both paths.
READINESS_PATHS: list[str] = ["/health/db", "/ready"]


@pytest.mark.parametrize("path", READINESS_PATHS)
def test_readiness_ok(path: str) -> None:
    """RU: Проверка, что readiness endpoints возвращают 200.

    EN: Ensure readiness endpoints succeed when DB is available.
    """
    with TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", READINESS_PATHS)
def test_readiness_failure(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """RU: Ошибка БД приводит к 503.

    EN: DB failure surfaces as 503 on readiness endpoints.
    """
    with TestClient(cast(ASGIApp, app.app)) as client:
        # lifespan clears DB_HEALTH_DEGRADED on successful init_db();
        # set it AFTER startup to exercise the 503 branch.
        monkeypatch.setenv("DB_HEALTH_DEGRADED", "1")
        response = client.get(path)

    assert response.status_code == 503
    assert response.json()["detail"].lower().startswith("database")

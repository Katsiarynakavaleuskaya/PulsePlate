"""Database health and readiness endpoint tests."""

from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app
import legacy_app
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


def test_lifespan_success_clears_fallback_flag() -> None:
    """Cover legacy_app lifespan success path (line 458): init_db() succeeds, clear _db_fallback_active."""
    import core.db_fallback as fallback_mod

    fallback_mod._db_fallback_active = True
    # Set marker so lifespan success path pops it (line 456/458)
    import os as _os

    _os.environ["DB_HEALTH_DEGRADED"] = "1"
    try:
        with TestClient(cast(ASGIApp, legacy_app.app)) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert not fallback_mod._db_fallback_active
        assert _os.environ.get("DB_HEALTH_DEGRADED") is None
    finally:
        _os.environ.pop("DB_HEALTH_DEGRADED", None)

"""Database health endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app
from core import db as db_module
from starlette.types import ASGIApp
from typing import cast


def test_health_db_ok() -> None:
    """RU: Проверка, что /health/db возвращает 200. EN: Ensure /health/db succeeds."""

    with TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_failure(monkeypatch) -> None:
    """RU: Ошибка БД приводит к 503. EN: DB failure surfaces as 503."""

    class BrokenSession:
        def execute(self, *_args, **_kwargs):  # noqa: D401
            raise RuntimeError("boom")

        def close(self) -> None:  # noqa: D401
            pass

    monkeypatch.setattr(db_module, "SessionLocal", lambda: BrokenSession())

    with TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"].lower().startswith("database")

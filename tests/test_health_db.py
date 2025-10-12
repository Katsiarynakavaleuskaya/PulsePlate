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

    class BrokenSession:
        def execute(self, *_args, **_kwargs):  # noqa: D401
            raise RuntimeError("boom")

        def close(self) -> None:  # noqa: D401
            pass

    def broken_get_session():
        session = BrokenSession()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(db_module, "SessionLocal", lambda: BrokenSession())

    try:
        with TestClient(cast(ASGIApp, app.app)) as client:
            response = client.get("/health/db")

        assert response.status_code == 503
        assert response.json()["detail"].lower().startswith("database")
    finally:
        if app.app is not None:
            app.app.dependency_overrides.clear()

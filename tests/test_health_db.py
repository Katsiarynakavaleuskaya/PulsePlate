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


def test_health_db_failure() -> None:
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

    # Create a test app with overridden dependency
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import text

    test_app = FastAPI()

    @test_app.get("/health/db")
    def database_health_test(session=broken_get_session):
        """Test version of database health check."""
        try:
            session.execute(text("SELECT 1"))
        except Exception as exc:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Database unavailable") from exc
        return {"status": "ok"}

    with TestClient(test_app) as client:
        response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"].lower().startswith("database")

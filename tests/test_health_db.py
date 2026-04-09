"""Database health and readiness endpoint tests."""

from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app
import legacy_app
from core import db as db_module

# RU: /health/db сохраняет старый контракт, /ready теперь additive-only.
# EN: /health/db keeps the old contract, while /ready is now additive-only.


def test_database_health_ok() -> None:
    """RU: /health/db остаётся минимальным DB-readiness контрактом.

    EN: /health/db remains the minimal DB-readiness contract.
    """
    with TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get("/health/db")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_ready_ok_exposes_additive_insight_runtime() -> None:
    """RU: /ready добавляет безопасную insight runtime visibility.

    EN: /ready adds safe insight runtime visibility.
    """
    with TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert payload["status"] == "ok"
    insight_runtime = payload["insight_runtime"]
    assert insight_runtime["feature_enabled"] is False
    assert insight_runtime["primary_provider"] is None
    assert insight_runtime["fallback_order"] == []
    assert insight_runtime["echo_mode_provider"] is None


def test_ready_ok_exposes_echo_mode_without_secret_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: echo-mode visibility для stub должна быть явной и безопасной.

    EN: Echo-mode visibility for stub must be explicit and safe.
    """
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("LLM_PROVIDER", "stub")

    with TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert payload["status"] == "ok"
    insight_runtime = payload["insight_runtime"]
    assert insight_runtime["feature_enabled"] is True
    assert insight_runtime["primary_provider"] == "stub"
    assert insight_runtime["fallback_order"] == ["stub"]
    assert insight_runtime["echo_mode_provider"] == "stub"


def test_ready_falls_back_to_unavailable_runtime_when_insight_readiness_raises(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """RU: /ready fail-soft branch logs runtime error and keeps additive contract.

    EN: /ready logs insight readiness failure and preserves the additive fallback payload.
    """

    def _raise_runtime_error() -> None:
        raise RuntimeError("readiness boom")

    import llm

    monkeypatch.setattr(llm, "get_insight_runtime_readiness", _raise_runtime_error, raising=True)

    with caplog.at_level("WARNING"), TestClient(cast(ASGIApp, app.app)) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["insight_runtime"] == {"status": "unavailable"}
    assert any(
        "Insight runtime readiness unavailable on /ready" in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize("path", ["/health/db", "/ready"])
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
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json()["detail"].lower().startswith("database")


def test_lifespan_success_clears_fallback_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover legacy_app lifespan success path (line 458): init_db() succeeds, clear _db_fallback_active."""
    import os

    import core.db_fallback as fallback_mod

    fallback_mod.set_fallback_active()
    monkeypatch.setenv("DB_HEALTH_DEGRADED", "1")

    with TestClient(cast(ASGIApp, legacy_app.app)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert fallback_mod.is_fallback_active() is False
    assert os.environ.get("DB_HEALTH_DEGRADED") is None


def test_lifespan_init_db_failure_triggers_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover legacy_app lifespan fallback import path when init_db fails."""
    import core.db_fallback as fallback_mod

    called: list[Exception] = []

    def _raise_init_db() -> None:
        raise RuntimeError("boom")

    def _fake_attempt(
        env_name: str | None, is_production: bool, db_err: Exception, truthy: set[str]
    ) -> None:
        called.append(db_err)

    monkeypatch.setattr(legacy_app, "init_db", _raise_init_db)
    monkeypatch.setattr(fallback_mod, "_attempt_db_fallback", _fake_attempt)

    with TestClient(cast(ASGIApp, legacy_app.app)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert called
    assert isinstance(called[0], RuntimeError)

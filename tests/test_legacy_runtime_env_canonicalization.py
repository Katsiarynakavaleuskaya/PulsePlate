from __future__ import annotations

import asyncio
import importlib
from types import ModuleType

import dotenv
import pytest
from fastapi import HTTPException


def _reload_legacy_app() -> ModuleType:
    """Reload legacy_app after env changes.

    RU: Перезагружаем legacy_app после изменения env, чтобы import-time wiring
    перечитал канонические runtime helpers.
    EN: Reload legacy_app after env changes so import-time wiring re-evaluates
    canonical runtime helpers.
    """

    import legacy_app

    return importlib.reload(legacy_app)


def _reload_canonical_main() -> ModuleType:
    """Reload canonical bootstrap after env changes."""

    import app.main as app_main
    import legacy_app

    importlib.reload(legacy_app)
    return importlib.reload(app_main)


@pytest.fixture(autouse=True)
def _reset_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep env-based legacy app tests deterministic.

    RU: Жёстко изолируем env, чтобы legacy import-time gates читали только
    нужные значения текущего теста.
    EN: Hard-isolate env so legacy import-time gates only see the values set by
    the current test.
    """

    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "ENV",
        "ENABLE_TEST_ROUTES",
        "ENABLE_DEBUG_ENDPOINT",
        "PYTEST_CURRENT_TEST",
        "DEBUG",
    ):
        monkeypatch.delenv(name, raising=False)


def test_legacy_app_skips_local_dotenv_in_env_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: calls.append("load"))

    _reload_legacy_app()

    assert calls == []


def test_canonical_bootstrap_staging_test_router_respects_environment_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")

    app_module = _reload_canonical_main()
    assert not any(
        getattr(route, "path", "") == "/api/v1/test/health"
        for route in getattr(app_module.app, "routes", [])
    )

    monkeypatch.setenv("ENABLE_TEST_ROUTES", "1")
    app_module = _reload_canonical_main()
    assert any(
        getattr(route, "path", "") == "/api/v1/test/health"
        for route in getattr(app_module.app, "routes", [])
    )


def test_debug_env_uses_environment_when_app_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    app_module = _reload_legacy_app()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(app_module.debug_env())

    assert exc_info.value.status_code == 404


def test_health_prefers_environment_over_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "local")

    health_module = importlib.import_module("app.routers.health")
    response = asyncio.run(health_module.health())
    assert response["environment"] == "production"


def test_test_router_request_gate_prefers_environment_over_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "local")

    from app.routers import test as test_router

    importlib.reload(test_router)

    with pytest.raises(HTTPException) as exc_info:
        test_router._ensure_non_production()

    assert exc_info.value.status_code == 404


def test_test_router_request_gate_blocks_staging_without_enable_even_if_app_env_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("APP_ENV", "local")

    from app.routers import test as test_router

    importlib.reload(test_router)

    with pytest.raises(HTTPException) as exc_info:
        test_router._ensure_non_production()

    assert exc_info.value.status_code == 404

    monkeypatch.setenv("ENABLE_TEST_ROUTES", "1")
    importlib.reload(test_router)
    test_router._ensure_non_production()

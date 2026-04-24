"""Coverage guard for app.routers.test module import-time configuration.

RU: Этот тест гарантирует, что модуль test-router импортируется под coverage
и его декларации (router/prefix) считаются покрытыми.
EN: Ensures app.routers.test is imported under coverage measurement.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import HTTPException


def test_test_router_module_reload_covers_router_declaration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reload module to ensure router declaration lines are executed under coverage."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("ENABLE_TEST_ROUTES", "1")

    import app.routers.test as test_router

    mod = importlib.reload(test_router)
    assert mod.router.prefix == "/api/v1/test"


def test_test_router_staging_without_enable_flag_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover staging hardening branch: ENABLE_TEST_ROUTES must be set."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("ENABLE_TEST_ROUTES", raising=False)

    import app.routers.test as test_router

    mod = importlib.reload(test_router)
    with pytest.raises(HTTPException) as exc:
        mod._ensure_non_production()

    assert exc.value.status_code == 404

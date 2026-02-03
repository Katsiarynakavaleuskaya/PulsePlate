"""Targeted branch coverage for PRO route registration.

RU: Точечные тесты ветвления для `register_pro_routes()` (Codecov partials).
EN: Targeted branch tests for `register_pro_routes()` (Codecov partials).

Goal:
- Cover feature-flag and VIP-flag branches deterministically without importing real routers.
- Avoid sys.modules mutation directly (use monkeypatch.setitem per repo policy).
"""

from __future__ import annotations

import sys
import types

import pytest
from fastapi import APIRouter, FastAPI


def _install_dummy_router_module(
    monkeypatch: pytest.MonkeyPatch, module_name: str, router_obj: APIRouter | None
) -> None:
    """Install a dummy module with a `router` attribute into sys.modules.

    This allows `from app.routers.<x> import router` imports inside the function under test
    to resolve without importing the real modules (and their side-effects).
    """

    dummy_mod = types.ModuleType(module_name)
    setattr(dummy_mod, "router", router_obj)
    monkeypatch.setitem(sys.modules, module_name, dummy_mod)


def test_register_pro_routes_idempotent_second_call_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second call should hit cached/idempotent branch (no new routes)."""

    import app.utils.feature_flags as feature_flags
    from app.routers.pro_registration import register_pro_routes

    app = FastAPI()

    pro_router = APIRouter()
    _install_dummy_router_module(monkeypatch, "app.routers.pro", pro_router)

    # Ensure premium_week branch is NOT taken for this test.
    monkeypatch.delenv("FEATURE_PREMIUM_WEEK_ENABLED", raising=False)
    monkeypatch.setattr(feature_flags, "is_vip_module_enabled", lambda: False)

    pro1, week1 = register_pro_routes(app)
    routes_after_first = len(app.router.routes)

    pro2, week2 = register_pro_routes(app)
    routes_after_second = len(app.router.routes)

    assert routes_after_second == routes_after_first
    assert pro2 is pro1
    assert week2 is week1


def test_register_pro_routes_includes_premium_week_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """FEATURE_PREMIUM_WEEK_ENABLED=true includes premium_week router."""

    import app.utils.feature_flags as feature_flags
    from app.routers.pro_registration import register_pro_routes

    app = FastAPI()

    pro_router = APIRouter()
    week_router = APIRouter()
    _install_dummy_router_module(monkeypatch, "app.routers.pro", pro_router)
    _install_dummy_router_module(monkeypatch, "app.routers.premium_week", week_router)

    monkeypatch.setenv("FEATURE_PREMIUM_WEEK_ENABLED", "true")
    monkeypatch.setattr(feature_flags, "is_vip_module_enabled", lambda: False)

    pro_res, week_res = register_pro_routes(app)
    assert pro_res is pro_router
    assert week_res is week_router


def test_register_pro_routes_includes_premium_week_by_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """VIP module enabled includes premium_week router when env flag is not set."""

    import app.utils.feature_flags as feature_flags
    from app.routers.pro_registration import register_pro_routes

    app = FastAPI()

    pro_router = APIRouter()
    week_router = APIRouter()
    _install_dummy_router_module(monkeypatch, "app.routers.pro", pro_router)
    _install_dummy_router_module(monkeypatch, "app.routers.premium_week", week_router)

    monkeypatch.delenv("FEATURE_PREMIUM_WEEK_ENABLED", raising=False)
    monkeypatch.setattr(feature_flags, "is_vip_module_enabled", lambda: True)

    pro_res, week_res = register_pro_routes(app)
    assert pro_res is pro_router
    assert week_res is week_router


def test_register_pro_routes_handles_none_routers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover `is not None` branches when imported routers are None."""

    import app.utils.feature_flags as feature_flags
    from app.routers.pro_registration import register_pro_routes

    app = FastAPI()

    _install_dummy_router_module(monkeypatch, "app.routers.pro", None)
    _install_dummy_router_module(monkeypatch, "app.routers.premium_week", None)

    monkeypatch.setenv("FEATURE_PREMIUM_WEEK_ENABLED", "true")
    monkeypatch.setattr(feature_flags, "is_vip_module_enabled", lambda: False)

    pro_res, week_res = register_pro_routes(app)
    assert pro_res is None
    assert week_res is None

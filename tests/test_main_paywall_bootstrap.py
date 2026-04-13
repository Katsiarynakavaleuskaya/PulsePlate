from __future__ import annotations

from fastapi import APIRouter, FastAPI
import pytest

import app.main as app_main


def _stub_router(path: str, *, method: str = "post") -> APIRouter:
    router = APIRouter()

    async def _handler() -> dict[str, str]:
        return {"status": path}

    getattr(router, method)(path)(_handler)
    return router


def _prepare_bootstrap_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_main, "_install_openapi_builder", lambda target_app: None)
    monkeypatch.setattr(app_main, "_internalize_users_openapi_surface", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_food_search_backend", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_metrics", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_request_telemetry", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_tracing", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_pro_contract_routes", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_billing_routes", lambda target_app: None)
    monkeypatch.setattr(app_main, "feedback_router", _stub_router("/api/v1/feedback/rag"))
    monkeypatch.setattr(app_main, "legal_router", _stub_router("/terms", method="get"))
    monkeypatch.setattr(app_main, "cbt_insight_router", _stub_router("/api/v1/pro/cbt/insight"))
    monkeypatch.setattr(
        app_main,
        "fitchef_structured_router",
        _stub_router("/api/v1/pro/fitchef/explain"),
    )
    monkeypatch.setattr(
        app_main,
        "creative_research_internal_router",
        _stub_router("/api/v1/internal/creative-research/pilot"),
    )
    monkeypatch.setattr(app_main.realtime_ws, "router", APIRouter())


def test_paywall_route_registration_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    app_main.ensure_canonical_app_bootstrap(app)
    app_main.ensure_canonical_app_bootstrap(app)

    paywall_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == app_main._PAYWALL_EVENTS_ROUTE_PATH
        and "POST" in (getattr(route, "methods", None) or set())
    ]
    assert len(paywall_routes) == 1


def test_paywall_route_registration_rejects_foreign_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.post(app_main._PAYWALL_EVENTS_ROUTE_PATH)
    async def _foreign_handler() -> dict[str, str]:
        return {"status": "foreign"}

    with pytest.raises(RuntimeError, match="Duplicate /api/v1/internal/paywall/events route"):
        app_main.ensure_canonical_app_bootstrap(app)

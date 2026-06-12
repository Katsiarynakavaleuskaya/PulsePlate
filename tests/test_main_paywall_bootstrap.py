from __future__ import annotations

from fastapi import APIRouter, FastAPI
import pytest
from typing import Generator

import app.main as app_main


@pytest.fixture(autouse=True)
def _restore_app_singleton() -> Generator[None, None, None]:
    original_app = app_main.app
    try:
        yield
    finally:
        app_main.app = original_app


def _stub_router(path: str, *, method: str = "post") -> APIRouter:
    router = APIRouter()

    async def _handler() -> dict[str, str]:
        return {"status": path}

    getattr(router, method)(path)(_handler)
    return router


def _legal_stub_router() -> APIRouter:
    router = APIRouter()

    async def _privacy() -> dict[str, str]:
        return {"status": "/privacy"}

    async def _terms() -> dict[str, str]:
        return {"status": "/terms"}

    router.get("/privacy")(_privacy)
    router.get("/terms")(_terms)
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
    monkeypatch.setattr(app_main, "legal_router", _legal_stub_router())
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


def _bootstrap_temp_app(app: FastAPI) -> FastAPI:
    original_app = app_main.app
    try:
        return app_main.ensure_canonical_app_bootstrap(app)
    finally:
        app_main.app = original_app


def test_paywall_route_registration_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

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
        _bootstrap_temp_app(app)


@pytest.mark.parametrize("existing_path", ["/privacy", "/terms"])
def test_legal_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
    existing_path: str,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.get(existing_path)
    async def _existing_legal_route() -> dict[str, str]:
        return {"status": existing_path}

    with pytest.raises(RuntimeError, match="Partial legal route registration detected"):
        _bootstrap_temp_app(app)


def test_legal_route_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.get("/privacy")
    async def _foreign_privacy_route() -> dict[str, str]:
        return {"status": "/privacy"}

    @app.get("/terms")
    async def _foreign_terms_route() -> dict[str, str]:
        return {"status": "/terms"}

    with pytest.raises(
        RuntimeError,
        match="Duplicate /privacy route detected with a different legal handler",
    ):
        _bootstrap_temp_app(app)


def test_legal_route_registration_rejects_canonical_plus_foreign_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()
    app.include_router(app_main.legal_router)

    @app.get("/privacy")
    async def _foreign_privacy_route() -> dict[str, str]:
        return {"status": "foreign"}

    with pytest.raises(
        RuntimeError,
        match="Duplicate /privacy route detected with a different legal handler",
    ):
        _bootstrap_temp_app(app)


def test_legal_route_registration_rejects_malformed_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "legal_router", _stub_router("/terms", method="get"))

    with pytest.raises(RuntimeError, match="Legal router does not define"):
        _bootstrap_temp_app(FastAPI())

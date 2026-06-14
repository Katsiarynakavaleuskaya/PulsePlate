from __future__ import annotations

from fastapi import APIRouter, FastAPI, Response
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


def _stub_router(path: str, *, method: str = "post", include_in_schema: bool = True) -> APIRouter:
    router = APIRouter()

    async def _handler() -> dict[str, str]:
        return {"status": path}

    getattr(router, method)(path, include_in_schema=include_in_schema)(_handler)
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


def _health_stub_router(*, include_in_schema: bool = False) -> APIRouter:
    router = APIRouter()

    async def _health() -> dict[str, str]:
        return {"status": "/health"}

    async def _health_v1() -> dict[str, str]:
        return {"status": "/api/v1/health"}

    async def _health_db() -> dict[str, str]:
        return {"status": "/health/db"}

    async def _ready() -> dict[str, str]:
        return {"status": "/ready"}

    router.get("/health", include_in_schema=include_in_schema)(_health)
    router.get("/api/v1/health", include_in_schema=include_in_schema)(_health_v1)
    router.get("/health/db", include_in_schema=include_in_schema)(_health_db)
    router.get("/ready", include_in_schema=include_in_schema)(_ready)
    return router


def _favicon_stub_router(*, include_in_schema: bool = False) -> APIRouter:
    router = APIRouter()

    async def _favicon() -> Response:
        return Response(status_code=204)

    router.get(app_main.FAVICON_ROUTE_PATH, include_in_schema=include_in_schema)(_favicon)
    return router


def _duplicate_health_stub_router() -> APIRouter:
    router = _health_stub_router()

    async def _second_health() -> dict[str, str]:
        return {"status": "/health-duplicate"}

    router.get("/health", include_in_schema=False)(_second_health)
    return router


def _duplicate_favicon_stub_router() -> APIRouter:
    router = _favicon_stub_router()

    async def _second_favicon() -> Response:
        return Response(status_code=204)

    router.get(app_main.FAVICON_ROUTE_PATH, include_in_schema=False)(_second_favicon)
    return router


def _duplicate_privacy_legal_stub_router() -> APIRouter:
    router = _legal_stub_router()

    async def _second_privacy() -> dict[str, str]:
        return {"status": "/privacy-duplicate"}

    router.get("/privacy")(_second_privacy)
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
    monkeypatch.setattr(app_main, "favicon_router", _favicon_stub_router())
    monkeypatch.setattr(app_main, "health_router", _health_stub_router())
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


def test_health_route_registration_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    for path in app_main._HEALTH_ROUTE_PATHS:
        health_routes = [
            route
            for route in app.routes
            if getattr(route, "path", None) == path
            and "GET" in (getattr(route, "methods", None) or set())
        ]
        assert len(health_routes) == 1


@pytest.mark.parametrize("existing_path", app_main._HEALTH_ROUTE_PATHS)
def test_health_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
    existing_path: str,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.get(existing_path)
    async def _existing_health_route() -> dict[str, str]:
        return {"status": existing_path}

    with pytest.raises(RuntimeError, match="Partial health route registration detected"):
        _bootstrap_temp_app(app)


def test_health_route_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    async def _foreign_health_route() -> dict[str, str]:
        return {"status": "foreign"}

    for path in app_main._HEALTH_ROUTE_PATHS:
        app.add_api_route(path, _foreign_health_route, methods=["GET"])

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different health handler",
    ):
        _bootstrap_temp_app(app)


def test_health_route_registration_rejects_visible_existing_canonical_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()
    for route in app_main.health_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path in app_main._HEALTH_ROUTE_PATHS and "GET" in methods:
            app.add_api_route(
                str(path),
                getattr(route, "endpoint"),
                methods=["GET"],
                include_in_schema=True,
            )

    with pytest.raises(RuntimeError, match="hidden OpenAPI visibility"):
        _bootstrap_temp_app(app)


def test_health_route_registration_rejects_canonical_plus_foreign_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()
    app.include_router(app_main.health_router)

    @app.get("/health", include_in_schema=False)
    async def _foreign_health_route() -> dict[str, str]:
        return {"status": "foreign"}

    with pytest.raises(
        RuntimeError,
        match="Duplicate /health route detected with a different health handler",
    ):
        _bootstrap_temp_app(app)


def test_health_route_registration_rejects_malformed_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "health_router",
        _stub_router("/ready", method="get", include_in_schema=False),
    )

    with pytest.raises(RuntimeError, match="Health router does not define"):
        _bootstrap_temp_app(FastAPI())


def test_health_route_registration_rejects_openapi_visible_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "health_router", _health_stub_router(include_in_schema=True))

    with pytest.raises(RuntimeError, match="hidden OpenAPI visibility"):
        _bootstrap_temp_app(FastAPI())


def test_health_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "health_router", _duplicate_health_stub_router())

    with pytest.raises(RuntimeError, match="Health router does not define"):
        _bootstrap_temp_app(FastAPI())


def test_favicon_route_registration_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    favicon_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == app_main.FAVICON_ROUTE_PATH
        and "GET" in (getattr(route, "methods", None) or set())
    ]
    assert len(favicon_routes) == 1
    assert getattr(favicon_routes[0], "include_in_schema", True) is False


def test_favicon_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.post(app_main.FAVICON_ROUTE_PATH)
    async def _existing_favicon_post_route() -> dict[str, str]:
        return {"status": "foreign"}

    with pytest.raises(RuntimeError, match="Partial favicon route registration detected"):
        _bootstrap_temp_app(app)


def test_favicon_route_registration_rejects_foreign_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.get(app_main.FAVICON_ROUTE_PATH, include_in_schema=False)
    async def _foreign_favicon_route() -> dict[str, str]:
        return {"status": "foreign"}

    with pytest.raises(
        RuntimeError,
        match="Duplicate /favicon.ico route detected with a different favicon handler",
    ):
        _bootstrap_temp_app(app)


def test_favicon_route_registration_rejects_visible_existing_canonical_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()
    route = next(
        route
        for route in app_main.favicon_router.routes
        if getattr(route, "path", None) == app_main.FAVICON_ROUTE_PATH
        and "GET" in (getattr(route, "methods", None) or set())
    )
    app.add_api_route(
        app_main.FAVICON_ROUTE_PATH,
        getattr(route, "endpoint"),
        methods=["GET"],
        include_in_schema=True,
    )

    with pytest.raises(RuntimeError, match="hidden OpenAPI visibility"):
        _bootstrap_temp_app(app)


def test_favicon_route_registration_rejects_malformed_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "favicon_router",
        _stub_router(app_main.FAVICON_ROUTE_PATH, include_in_schema=False),
    )

    with pytest.raises(RuntimeError, match="Favicon router does not define"):
        _bootstrap_temp_app(FastAPI())


def test_favicon_route_registration_rejects_openapi_visible_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "favicon_router", _favicon_stub_router(include_in_schema=True))

    with pytest.raises(RuntimeError, match="hidden OpenAPI visibility"):
        _bootstrap_temp_app(FastAPI())


def test_favicon_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "favicon_router", _duplicate_favicon_stub_router())

    with pytest.raises(RuntimeError, match="Favicon router does not define"):
        _bootstrap_temp_app(FastAPI())


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


def test_legal_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "legal_router", _duplicate_privacy_legal_stub_router())

    with pytest.raises(RuntimeError, match="Legal router does not define"):
        _bootstrap_temp_app(FastAPI())

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Response
from fastapi.testclient import TestClient
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


def _admin_operations_stub_router(
    *,
    include_in_schema: bool = False,
    omit: frozenset[str] = frozenset(),
    method_overrides: dict[str, str] | None = None,
) -> APIRouter:
    router = APIRouter()
    overrides = method_overrides or {}

    for path, method in app_main._ADMIN_OPERATION_ROUTE_SPECS:
        if path in omit:
            continue
        route_method = overrides.get(path, method).lower()

        async def _admin_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(router, route_method)(path, include_in_schema=include_in_schema)(_admin_handler)

    return router


def _bmi_compat_stub_router(
    *,
    omit: frozenset[str] = frozenset(),
    method_overrides: dict[str, str] | None = None,
    include_overrides: dict[str, bool] | None = None,
) -> APIRouter:
    router = APIRouter()
    method_override_map = method_overrides or {}
    include_override_map = include_overrides or {}

    for path, method, include_in_schema in app_main._BMI_COMPAT_ROUTE_SPECS:
        if path in omit:
            continue
        route_method = method_override_map.get(path, method).lower()
        route_include = include_override_map.get(path, include_in_schema)

        async def _bmi_compat_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(router, route_method)(path, include_in_schema=route_include)(_bmi_compat_handler)

    return router


def _legacy_export_alias_stub_router(
    *,
    omit: frozenset[str] = frozenset(),
    method_overrides: dict[str, str] | None = None,
    include_overrides: dict[str, bool] | None = None,
) -> APIRouter:
    router = APIRouter()
    method_override_map = method_overrides or {}
    include_override_map = include_overrides or {}

    for path, method, include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
        if path in omit:
            continue
        route_method = method_override_map.get(path, method).lower()
        route_include = include_override_map.get(path, include_in_schema)

        async def _legacy_export_alias_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(router, route_method)(path, include_in_schema=route_include)(
            _legacy_export_alias_handler
        )

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


def _duplicate_admin_operations_stub_router() -> APIRouter:
    router = _admin_operations_stub_router()
    duplicate_path, duplicate_method = app_main._ADMIN_OPERATION_ROUTE_SPECS[0]

    async def _second_admin_handler() -> dict[str, str]:
        return {"status": "duplicate"}

    getattr(router, duplicate_method.lower())(
        duplicate_path,
        include_in_schema=False,
    )(_second_admin_handler)
    return router


def _duplicate_bmi_compat_stub_router() -> APIRouter:
    router = _bmi_compat_stub_router()
    duplicate_path, duplicate_method, duplicate_include = app_main._BMI_COMPAT_ROUTE_SPECS[0]

    async def _second_bmi_compat_handler() -> dict[str, str]:
        return {"status": "duplicate"}

    getattr(router, duplicate_method.lower())(
        duplicate_path,
        include_in_schema=duplicate_include,
    )(_second_bmi_compat_handler)
    return router


def _duplicate_legacy_export_alias_stub_router() -> APIRouter:
    router = _legacy_export_alias_stub_router()
    duplicate_path, duplicate_method, duplicate_include = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[
        0
    ]

    async def _second_legacy_export_alias_handler() -> dict[str, str]:
        return {"status": "duplicate"}

    getattr(router, duplicate_method.lower())(
        duplicate_path,
        include_in_schema=duplicate_include,
    )(_second_legacy_export_alias_handler)
    return router


def _bmi_compat_stub_router_with_unrelated_path() -> APIRouter:
    router = _bmi_compat_stub_router()

    async def _unrelated_handler() -> dict[str, str]:
        return {"status": "unrelated"}

    router.get("/api/v1/unrelated-bmi-compat-probe", include_in_schema=False)(_unrelated_handler)
    return router


def _bmi_compat_stub_router_with_combined_methods() -> APIRouter:
    router = APIRouter()
    combined_path, combined_method, combined_include = app_main._BMI_COMPAT_ROUTE_SPECS[0]

    for path, method, include_in_schema in app_main._BMI_COMPAT_ROUTE_SPECS:

        async def _bmi_compat_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        methods = [method]
        if path == combined_path:
            methods.append("GET" if combined_method == "POST" else "POST")
        router.add_api_route(
            path,
            _bmi_compat_handler,
            methods=methods,
            include_in_schema=combined_include if path == combined_path else include_in_schema,
        )
    return router


def _legacy_export_alias_stub_router_with_combined_methods() -> APIRouter:
    router = APIRouter()
    combined_path, combined_method, combined_include = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0]

    for path, method, include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:

        async def _legacy_export_alias_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        methods = [method]
        if path == combined_path:
            methods.append("GET" if combined_method == "POST" else "POST")
        router.add_api_route(
            path,
            _legacy_export_alias_handler,
            methods=methods,
            include_in_schema=combined_include if path == combined_path else include_in_schema,
        )
    return router


def _legacy_export_alias_stub_router_with_unrelated_path() -> APIRouter:
    router = _legacy_export_alias_stub_router()

    async def _unrelated_handler() -> dict[str, str]:
        return {"status": "unrelated"}

    router.get("/api/v1/unrelated-legacy-export-probe", include_in_schema=False)(_unrelated_handler)
    return router


def _app_with_bmi_compat_routes_and_extra_method(*, combined_route: bool) -> FastAPI:
    app = FastAPI()
    extra_path, extra_method, extra_include = app_main._BMI_COMPAT_ROUTE_SPECS[0]

    for path, method, include_in_schema in app_main._BMI_COMPAT_ROUTE_SPECS:

        async def _bmi_compat_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        app.add_api_route(
            path, _bmi_compat_handler, methods=[method], include_in_schema=include_in_schema
        )

    async def _extra_method_handler() -> dict[str, str]:
        return {"status": "extra-method"}

    opposite_method = "POST" if extra_method == "GET" else "GET"
    extra_methods = [extra_method, opposite_method] if combined_route else [opposite_method]
    app.add_api_route(
        extra_path,
        _extra_method_handler,
        methods=extra_methods,
        include_in_schema=extra_include,
    )
    return app


def _app_with_legacy_export_alias_routes_and_extra_method(*, combined_route: bool) -> FastAPI:
    app = FastAPI()
    extra_path, extra_method, extra_include = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0]

    for path, method, include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:

        async def _legacy_export_alias_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        app.add_api_route(
            path,
            _legacy_export_alias_handler,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    async def _extra_method_handler() -> dict[str, str]:
        return {"status": "extra-method"}

    opposite_method = "POST" if extra_method == "GET" else "GET"
    extra_methods = [extra_method, opposite_method] if combined_route else [opposite_method]
    app.add_api_route(
        extra_path,
        _extra_method_handler,
        methods=extra_methods,
        include_in_schema=extra_include,
    )
    return app


def _admin_operations_stub_router_with_unrelated_path() -> APIRouter:
    router = _admin_operations_stub_router()

    async def _unrelated_handler() -> dict[str, str]:
        return {"status": "unrelated"}

    router.get("/api/v1/unrelated-admin-probe", include_in_schema=False)(_unrelated_handler)
    return router


def _admin_operations_stub_router_with_combined_methods() -> APIRouter:
    router = APIRouter()
    combined_path, combined_method = app_main._ADMIN_OPERATION_ROUTE_SPECS[0]

    for path, method in app_main._ADMIN_OPERATION_ROUTE_SPECS:

        async def _admin_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        methods = [method]
        if path == combined_path:
            methods.append("POST" if combined_method == "GET" else "GET")
        router.add_api_route(
            path,
            _admin_handler,
            methods=methods,
            include_in_schema=False,
        )

    return router


def _app_with_admin_routes_and_extra_method(*, combined_route: bool) -> FastAPI:
    app = FastAPI()
    extra_path, extra_method = app_main._ADMIN_OPERATION_ROUTE_SPECS[0]

    for path, method in app_main._ADMIN_OPERATION_ROUTE_SPECS:

        async def _admin_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        app.add_api_route(path, _admin_handler, methods=[method], include_in_schema=False)

    async def _extra_method_handler() -> dict[str, str]:
        return {"status": "extra-method"}

    if combined_route:
        app.add_api_route(
            extra_path,
            _extra_method_handler,
            methods=[extra_method, "POST" if extra_method == "GET" else "GET"],
            include_in_schema=False,
        )
    else:
        app.add_api_route(
            extra_path,
            _extra_method_handler,
            methods=["POST" if extra_method == "GET" else "GET"],
            include_in_schema=False,
        )

    return app


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
    monkeypatch.setattr(app_main, "admin_operations_router", _admin_operations_stub_router())
    monkeypatch.setattr(app_main, "bmi_compat_router", _bmi_compat_stub_router())
    monkeypatch.setattr(
        app_main,
        "legacy_export_aliases_router",
        _legacy_export_alias_stub_router(),
    )
    monkeypatch.setattr(app_main._legacy_module, "EXPORTS_ENABLED", True)
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


def test_admin_operations_route_registration_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    for path, method in app_main._ADMIN_OPERATION_ROUTE_SPECS:
        admin_routes = [
            route
            for route in app.routes
            if getattr(route, "path", None) == path
            and method in (getattr(route, "methods", None) or set())
        ]
        assert len(admin_routes) == 1
        assert getattr(admin_routes[0], "include_in_schema", True) is False


@pytest.mark.parametrize(
    "existing_path",
    [path for path, _method in app_main._ADMIN_OPERATION_ROUTE_SPECS],
)
def test_admin_operations_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
    existing_path: str,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.get(existing_path, include_in_schema=False)
    async def _existing_admin_route() -> dict[str, str]:
        return {"status": existing_path}

    with pytest.raises(RuntimeError, match="Partial admin operations route registration detected"):
        _bootstrap_temp_app(app)


def test_admin_operations_route_registration_rejects_wrong_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    @app.post("/debug_env", include_in_schema=False)
    async def _wrong_method_admin_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    with pytest.raises(RuntimeError, match="Partial admin operations route registration detected"):
        _bootstrap_temp_app(app)


def test_admin_operations_route_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    async def _foreign_admin_route() -> dict[str, str]:
        return {"status": "foreign"}

    for path, method in app_main._ADMIN_OPERATION_ROUTE_SPECS:
        app.add_api_route(
            path,
            _foreign_admin_route,
            methods=[method],
            include_in_schema=False,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different admin operations handler",
    ):
        _bootstrap_temp_app(app)


def test_admin_operations_route_registration_rejects_visible_existing_canonical_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()
    expected_specs = set(app_main._ADMIN_OPERATION_ROUTE_SPECS)
    for route in app_main.admin_operations_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        for expected_path, expected_method in expected_specs:
            if path == expected_path and expected_method in methods:
                app.add_api_route(
                    str(path),
                    getattr(route, "endpoint"),
                    methods=[expected_method],
                    include_in_schema=True,
                )

    with pytest.raises(RuntimeError, match="hidden OpenAPI visibility"):
        _bootstrap_temp_app(app)


def test_admin_operations_route_registration_rejects_malformed_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    omitted_path, _method = app_main._ADMIN_OPERATION_ROUTE_SPECS[0]
    monkeypatch.setattr(
        app_main,
        "admin_operations_router",
        _admin_operations_stub_router(omit=frozenset({omitted_path})),
    )

    with pytest.raises(RuntimeError, match="Admin operations router does not define"):
        _bootstrap_temp_app(FastAPI())


def test_admin_operations_route_registration_allows_router_with_unrelated_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "admin_operations_router",
        _admin_operations_stub_router_with_unrelated_path(),
    )

    app = _bootstrap_temp_app(FastAPI())

    assert any(
        getattr(route, "path", None) == "/api/v1/unrelated-admin-probe" for route in app.routes
    )


def test_admin_operations_route_registration_rejects_router_wrong_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    wrong_path, wrong_method = app_main._ADMIN_OPERATION_ROUTE_SPECS[0]
    monkeypatch.setattr(
        app_main,
        "admin_operations_router",
        _admin_operations_stub_router(
            method_overrides={
                wrong_path: "POST" if wrong_method == "GET" else "GET",
            },
        ),
    )

    with pytest.raises(RuntimeError, match="Admin operations router does not define"):
        _bootstrap_temp_app(FastAPI())


def test_admin_operations_route_registration_rejects_router_combined_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "admin_operations_router",
        _admin_operations_stub_router_with_combined_methods(),
    )

    with pytest.raises(RuntimeError, match="Admin operations router does not define"):
        _bootstrap_temp_app(FastAPI())


def test_admin_operations_route_registration_rejects_openapi_visible_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "admin_operations_router",
        _admin_operations_stub_router(include_in_schema=True),
    )

    with pytest.raises(RuntimeError, match="hidden OpenAPI visibility"):
        _bootstrap_temp_app(FastAPI())


def test_admin_operations_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "admin_operations_router",
        _duplicate_admin_operations_stub_router(),
    )

    with pytest.raises(RuntimeError, match="Admin operations router does not define"):
        _bootstrap_temp_app(FastAPI())


def test_admin_operations_route_registration_rejects_existing_wrong_method_after_full_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(RuntimeError, match="Partial admin operations route registration detected"):
        _bootstrap_temp_app(_app_with_admin_routes_and_extra_method(combined_route=False))


def test_admin_operations_route_registration_rejects_existing_combined_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(RuntimeError, match="Partial admin operations route registration detected"):
        _bootstrap_temp_app(_app_with_admin_routes_and_extra_method(combined_route=True))


def test_bmi_compat_route_registration_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    for path, method, include_in_schema in app_main._BMI_COMPAT_ROUTE_SPECS:
        matching_routes = [
            route
            for route in app.routes
            if getattr(route, "path", None) == path
            and method in (getattr(route, "methods", None) or set())
        ]
        assert len(matching_routes) == 1
        assert getattr(matching_routes[0], "include_in_schema", True) is include_in_schema


def test_bmi_compat_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._BMI_COMPAT_ROUTE_SPECS[0]

    async def _existing_bmi_compat_route() -> dict[str, str]:
        return {"status": "partial"}

    getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
        _existing_bmi_compat_route
    )

    with pytest.raises(RuntimeError, match="Partial BMI compatibility route registration detected"):
        _bootstrap_temp_app(app)


def test_bmi_compat_route_registration_rejects_wrong_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._BMI_COMPAT_ROUTE_SPECS[0]

    async def _wrong_method_bmi_compat_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    wrong_method = "GET" if method == "POST" else "POST"
    getattr(app, wrong_method.lower())(path, include_in_schema=include_in_schema)(
        _wrong_method_bmi_compat_route
    )

    with pytest.raises(RuntimeError, match="Partial BMI compatibility route registration detected"):
        _bootstrap_temp_app(app)


def test_bmi_compat_route_registration_rejects_wrong_method_in_canonical_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, method, _include_in_schema = app_main._BMI_COMPAT_ROUTE_SPECS[0]
    wrong_method = "GET" if method == "POST" else "POST"
    monkeypatch.setattr(
        app_main,
        "bmi_compat_router",
        _bmi_compat_stub_router(method_overrides={path: wrong_method}),
    )

    with pytest.raises(
        RuntimeError,
        match="BMI compatibility router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_bmi_compat_route_registration_allows_unrelated_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "bmi_compat_router",
        _bmi_compat_stub_router_with_unrelated_path(),
    )

    app = _bootstrap_temp_app(FastAPI())

    assert any(
        getattr(route, "path", None) == "/api/v1/unrelated-bmi-compat-probe" for route in app.routes
    )


def test_bmi_compat_route_registration_rejects_combined_methods_in_canonical_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "bmi_compat_router",
        _bmi_compat_stub_router_with_combined_methods(),
    )

    with pytest.raises(
        RuntimeError,
        match="BMI compatibility router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_bmi_compat_route_registration_rejects_existing_wrong_method_after_full_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(RuntimeError, match="Partial BMI compatibility route registration detected"):
        _bootstrap_temp_app(_app_with_bmi_compat_routes_and_extra_method(combined_route=False))


def test_bmi_compat_route_registration_rejects_existing_combined_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(RuntimeError, match="Partial BMI compatibility route registration detected"):
        _bootstrap_temp_app(_app_with_bmi_compat_routes_and_extra_method(combined_route=True))


def test_bmi_compat_route_registration_rejects_existing_openapi_visibility_drift() -> None:
    app = FastAPI()
    app.include_router(app_main.bmi_compat_router)
    path, method, include_in_schema = app_main._BMI_COMPAT_ROUTE_SPECS[0]
    matching_route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == path
        and method in (getattr(route, "methods", None) or set())
    )
    matching_route.include_in_schema = not include_in_schema

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve BMI compatibility OpenAPI visibility",
    ):
        app_main._include_bmi_compat_router_if_needed(app)


def test_bmi_compat_route_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()

    for path, method, include_in_schema in app_main._BMI_COMPAT_ROUTE_SPECS:

        async def _foreign_bmi_compat_route(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
            _foreign_bmi_compat_route
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different BMI compatibility handler",
    ):
        _bootstrap_temp_app(app)


def test_bmi_compat_route_registration_rejects_openapi_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, _method, include_in_schema = app_main._BMI_COMPAT_ROUTE_SPECS[0]
    monkeypatch.setattr(
        app_main,
        "bmi_compat_router",
        _bmi_compat_stub_router(include_overrides={path: not include_in_schema}),
    )

    with pytest.raises(
        RuntimeError,
        match="BMI compatibility router does not preserve OpenAPI visibility",
    ):
        _bootstrap_temp_app(FastAPI())


def test_bmi_compat_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "bmi_compat_router", _duplicate_bmi_compat_stub_router())

    with pytest.raises(
        RuntimeError,
        match="BMI compatibility router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_legacy_export_alias_route_registration_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    for path, method, include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
        matching_routes = [
            route
            for route in app.routes
            if getattr(route, "path", None) == path
            and method in (getattr(route, "methods", None) or set())
        ]
        assert len(matching_routes) == 1
        assert getattr(matching_routes[0], "include_in_schema", True) is include_in_schema


def test_legacy_export_alias_route_registration_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main._legacy_module, "EXPORTS_ENABLED", False)

    app = _bootstrap_temp_app(FastAPI())

    for path, method, _include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
        assert not [
            route
            for route in app.routes
            if getattr(route, "path", None) == path
            and method in (getattr(route, "methods", None) or set())
        ]


def test_build_legacy_export_aliases_router_returns_empty_router_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main._legacy_module, "EXPORTS_ENABLED", False)

    router = app_main._build_legacy_export_aliases_router()

    assert router.routes == []


def test_build_legacy_export_aliases_router_rejects_missing_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main._legacy_module, "EXPORTS_ENABLED", True)
    monkeypatch.setattr(app_main._legacy_module, "export_weekly_plan_pdf", None)

    with pytest.raises(
        RuntimeError,
        match="Legacy export aliases are enabled, but required helpers are unavailable",
    ):
        app_main._build_legacy_export_aliases_router()


def test_build_legacy_export_aliases_router_rejects_helper_missing_after_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setattr(app_main._legacy_module, "EXPORTS_ENABLED", True)
    router = app_main._build_legacy_export_aliases_router()
    monkeypatch.setattr(app_main._legacy_module, "export_weekly_plan_pdf", None)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with pytest.raises(RuntimeError, match="Legacy export helper is unavailable"):
        client.get(
            "/api/v1/premium/exports/week/unavailable.pdf",
            headers={"X-API-Key": "test_key"},
        )


def test_legacy_export_alias_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0]

    async def _existing_legacy_export_alias_route() -> dict[str, str]:
        return {"status": "partial"}

    getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
        _existing_legacy_export_alias_route
    )

    with pytest.raises(
        RuntimeError,
        match="Partial legacy export alias route registration detected",
    ):
        _bootstrap_temp_app(app)


def test_legacy_export_alias_route_registration_rejects_wrong_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0]

    async def _wrong_method_legacy_export_alias_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    wrong_method = "GET" if method == "POST" else "POST"
    getattr(app, wrong_method.lower())(path, include_in_schema=include_in_schema)(
        _wrong_method_legacy_export_alias_route
    )

    with pytest.raises(
        RuntimeError,
        match="Partial legacy export alias route registration detected",
    ):
        _bootstrap_temp_app(app)


def test_legacy_export_alias_route_registration_rejects_wrong_method_in_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, method, _include_in_schema = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0]
    wrong_method = "GET" if method == "POST" else "POST"
    monkeypatch.setattr(
        app_main,
        "legacy_export_aliases_router",
        _legacy_export_alias_stub_router(method_overrides={path: wrong_method}),
    )

    with pytest.raises(
        RuntimeError,
        match="Legacy export alias router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_legacy_export_alias_route_registration_rejects_combined_methods_in_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "legacy_export_aliases_router",
        _legacy_export_alias_stub_router_with_combined_methods(),
    )

    with pytest.raises(
        RuntimeError,
        match="Legacy export alias router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_legacy_export_alias_route_registration_rejects_existing_wrong_method_after_full_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="Partial legacy export alias route registration detected",
    ):
        _bootstrap_temp_app(
            _app_with_legacy_export_alias_routes_and_extra_method(combined_route=False)
        )


def test_legacy_export_alias_route_registration_rejects_existing_combined_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="Partial legacy export alias route registration detected",
    ):
        _bootstrap_temp_app(
            _app_with_legacy_export_alias_routes_and_extra_method(combined_route=True)
        )


def test_legacy_export_alias_route_registration_allows_unrelated_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "legacy_export_aliases_router",
        _legacy_export_alias_stub_router_with_unrelated_path(),
    )

    app = _bootstrap_temp_app(FastAPI())

    assert any(
        getattr(route, "path", None) == "/api/v1/unrelated-legacy-export-probe"
        for route in app.routes
    )


def test_legacy_export_alias_route_registration_allows_reloaded_canonical_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main._legacy_module, "EXPORTS_ENABLED", True)
    app = FastAPI()
    app.include_router(app_main._build_legacy_export_aliases_router())
    monkeypatch.setattr(
        app_main,
        "legacy_export_aliases_router",
        app_main._build_legacy_export_aliases_router(),
    )

    app_main._include_legacy_export_alias_router_if_needed(app)

    for path, method, _include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
        matching_routes = [
            route
            for route in app.routes
            if getattr(route, "path", None) == path
            and method in (getattr(route, "methods", None) or set())
        ]
        assert len(matching_routes) == 1


def test_legacy_export_alias_endpoint_equivalence_rejects_non_callables() -> None:
    expected_endpoint = next(
        route.endpoint
        for route in app_main.legacy_export_aliases_router.routes
        if getattr(route, "path", None) == app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0][0]
    )

    assert not app_main._is_same_legacy_export_alias_endpoint(None, expected_endpoint)
    assert not app_main._is_same_legacy_export_alias_endpoint(expected_endpoint, None)


def test_legacy_export_alias_route_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()

    for path, method, include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:

        async def _foreign_legacy_export_alias_route(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
            _foreign_legacy_export_alias_route
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different legacy export alias handler",
    ):
        _bootstrap_temp_app(app)


def test_legacy_export_alias_route_registration_rejects_openapi_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, _method, include_in_schema = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0]
    monkeypatch.setattr(
        app_main,
        "legacy_export_aliases_router",
        _legacy_export_alias_stub_router(include_overrides={path: not include_in_schema}),
    )

    with pytest.raises(
        RuntimeError,
        match="Legacy export alias router does not preserve OpenAPI visibility",
    ):
        _bootstrap_temp_app(FastAPI())


def test_legacy_export_alias_route_registration_rejects_existing_openapi_visibility_drift() -> None:
    app = FastAPI()
    app.include_router(app_main.legacy_export_aliases_router)
    path, method, include_in_schema = app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS[0]
    matching_route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == path
        and method in (getattr(route, "methods", None) or set())
    )
    matching_route.include_in_schema = not include_in_schema

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve legacy export alias OpenAPI visibility",
    ):
        app_main._include_legacy_export_alias_router_if_needed(app)


def test_legacy_export_alias_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "legacy_export_aliases_router",
        _duplicate_legacy_export_alias_stub_router(),
    )

    with pytest.raises(
        RuntimeError,
        match="Legacy export alias router does not define the expected route family",
    ):
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

from __future__ import annotations

from types import SimpleNamespace
from typing import Generator, cast

from fastapi import APIRouter, Depends, FastAPI, Response, WebSocket
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest
from starlette.responses import JSONResponse
from starlette.routing import BaseRoute, Route

import app.main as app_main
from app.bootstrap.route_family import (
    RouteMemberContract,
    ensure_route_family_registered,
    route_member_contracts_from_router,
    route_has_dependency_call,
    same_callable_by_module_and_qualname,
)
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_endpoint_for_path_method,
    route_methods,
    route_path,
)
from app.routers.bmi_registration import BmiRouteRegistration, register_bmi_routes


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


def test_route_member_contract_defaults_for_static_family_tail_coverage() -> None:
    member = RouteMemberContract(
        path="/api/v1/static-family/defaults",
        method="get",
        include_in_schema=True,
    )

    assert member.method == "GET"
    assert member.required_status_codes == frozenset()
    assert member.required_dependencies == ()


def test_route_family_rejects_duplicate_and_empty_member_contracts() -> None:
    duplicate_members = (
        RouteMemberContract(
            path="/api/v1/static-family/a",
            method="GET",
            include_in_schema=True,
        ),
        RouteMemberContract(
            path="/api/v1/static-family/a",
            method="GET",
            include_in_schema=True,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        ensure_route_family_registered(
            FastAPI(),
            family_name="Static family",
            routers=(),
            members=duplicate_members,
        )

    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        ensure_route_family_registered(
            FastAPI(),
            family_name="Static family",
            routers=(),
            members=(),
        )


def test_route_member_contracts_reject_non_http_routes() -> None:
    router = APIRouter()

    async def _websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.close()

    router.websocket("/ws/static-family")(_websocket_endpoint)

    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        route_member_contracts_from_router("Static family", router)


def test_route_member_contracts_reject_framework_only_route_methods() -> None:
    router = APIRouter()

    async def _handler() -> dict[str, str]:
        return {"status": "framework-only"}

    route = APIRoute("/api/v1/static-family/head", endpoint=_handler, methods=["GET"])
    route.methods = {"HEAD"}
    router.routes.append(cast(BaseRoute, route))

    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        route_member_contracts_from_router("Static family", router)


def test_route_member_contracts_reject_empty_source_router() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        route_member_contracts_from_router("Static family", APIRouter())


def test_route_family_contract_builder_rejects_duplicate_source_routes() -> None:
    router = APIRouter()

    async def _first() -> dict[str, str]:
        return {"status": "first"}

    async def _second() -> dict[str, str]:
        return {"status": "second"}

    router.get("/api/v1/static-family/duplicate")(_first)
    router.get("/api/v1/static-family/duplicate")(_second)

    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        ensure_route_family_registered(
            FastAPI(),
            family_name="Static family",
            routers=(router,),
            members=route_member_contracts_from_router("Static family", router),
        )


def test_route_family_rejects_existing_route_order_drift() -> None:
    router = APIRouter()

    async def _search() -> dict[str, str]:
        return {"status": "search"}

    async def _item(item_id: str) -> dict[str, str]:
        return {"status": item_id}

    router.get("/api/v1/static-family/search")(_search)
    router.get("/api/v1/static-family/{item_id}")(_item)

    target_app = FastAPI()
    target_app.add_api_route(
        "/api/v1/static-family/{item_id}",
        _item,
        methods=["GET"],
    )
    target_app.add_api_route(
        "/api/v1/static-family/search",
        _search,
        methods=["GET"],
    )

    with pytest.raises(
        RuntimeError,
        match="Existing static family route order does not preserve source route order",
    ):
        ensure_route_family_registered(
            target_app,
            family_name="Static family",
            routers=(router,),
            members=route_member_contracts_from_router("Static family", router),
        )


def test_route_family_rejects_non_http_source_routes_for_static_tail_coverage() -> None:
    router = APIRouter()

    async def _handler() -> dict[str, str]:
        return {"status": "ok"}

    async def _websocket(websocket: WebSocket) -> None:
        await websocket.close()

    router.get("/api/v1/static-family/http")(_handler)
    router.websocket("/api/v1/static-family/ws")(_websocket)

    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        ensure_route_family_registered(
            FastAPI(),
            family_name="Static family",
            routers=(router,),
            members=(
                RouteMemberContract(
                    path="/api/v1/static-family/http",
                    method="GET",
                    include_in_schema=True,
                ),
            ),
        )


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


def _bodyfat_stub_router(
    *,
    omit: frozenset[str] = frozenset(),
    method_overrides: dict[str, str] | None = None,
    include_overrides: dict[str, bool] | None = None,
) -> APIRouter:
    router = APIRouter()
    method_override_map = method_overrides or {}
    include_override_map = include_overrides or {}

    for path, method, include_in_schema in app_main._BODYFAT_ROUTE_SPECS:
        if path in omit:
            continue
        route_method = method_override_map.get(path, method).lower()
        route_include = include_override_map.get(path, include_in_schema)

        async def _bodyfat_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(router, route_method)(path, include_in_schema=route_include)(_bodyfat_handler)

    return router


def _duplicate_bodyfat_stub_router() -> APIRouter:
    router = _bodyfat_stub_router()
    duplicate_path, duplicate_method, duplicate_include = app_main._BODYFAT_ROUTE_SPECS[0]

    async def _second_bodyfat_handler() -> dict[str, str]:
        return {"status": "duplicate"}

    getattr(router, duplicate_method.lower())(
        duplicate_path,
        include_in_schema=duplicate_include,
    )(_second_bodyfat_handler)
    return router


def _bodyfat_stub_router_with_combined_methods() -> APIRouter:
    router = APIRouter()
    path, method, include_in_schema = app_main._BODYFAT_ROUTE_SPECS[0]

    async def _bodyfat_handler() -> dict[str, str]:
        return {"status": path}

    router.add_api_route(
        path,
        _bodyfat_handler,
        methods=[method, "GET" if method == "POST" else "POST"],
        include_in_schema=include_in_schema,
    )
    return router


def _bodyfat_stub_router_with_unrelated_path() -> APIRouter:
    router = _bodyfat_stub_router()

    async def _unrelated_handler() -> dict[str, str]:
        return {"status": "unrelated"}

    router.get("/api/v1/unrelated-bodyfat-probe")(_unrelated_handler)
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


def _plan_export_stub_routers(
    *,
    omit: frozenset[str] = frozenset(),
    method_overrides: dict[str, str] | None = None,
    include_overrides: dict[str, bool] | None = None,
    include_429: bool = True,
) -> tuple[APIRouter, APIRouter]:
    export_stub_router = APIRouter()
    plan_stub_router = APIRouter()
    method_override_map = method_overrides or {}
    include_override_map = include_overrides or {}
    responses = {429: {"description": "Rate limit exceeded"}} if include_429 else None

    for path, method, include_in_schema in app_main._PLAN_EXPORT_ROUTE_SPECS:
        if path in omit:
            continue
        route_method = method_override_map.get(path, method).lower()
        route_include = include_override_map.get(path, include_in_schema)
        target_router = (
            export_stub_router if path.startswith("/api/v1/export/") else plan_stub_router
        )

        async def _plan_export_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(target_router, route_method)(
            path,
            include_in_schema=route_include,
            responses=responses,
        )(_plan_export_handler)

    return export_stub_router, plan_stub_router


def _duplicate_plan_export_stub_routers() -> tuple[APIRouter, APIRouter]:
    export_stub_router, plan_stub_router = _plan_export_stub_routers()
    duplicate_path, duplicate_method, duplicate_include = app_main._PLAN_EXPORT_ROUTE_SPECS[0]
    target_router = (
        export_stub_router if duplicate_path.startswith("/api/v1/export/") else plan_stub_router
    )

    async def _second_plan_export_handler() -> dict[str, str]:
        return {"status": "duplicate"}

    getattr(target_router, duplicate_method.lower())(
        duplicate_path,
        include_in_schema=duplicate_include,
        responses={429: {"description": "Rate limit exceeded"}},
    )(_second_plan_export_handler)
    return export_stub_router, plan_stub_router


def _plan_export_stub_routers_with_combined_methods() -> tuple[APIRouter, APIRouter]:
    export_stub_router = APIRouter()
    plan_stub_router = APIRouter()
    combined_path, combined_method, combined_include = app_main._PLAN_EXPORT_ROUTE_SPECS[0]

    for path, method, include_in_schema in app_main._PLAN_EXPORT_ROUTE_SPECS:
        target_router = (
            export_stub_router if path.startswith("/api/v1/export/") else plan_stub_router
        )

        async def _plan_export_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        methods = [method]
        if path == combined_path:
            methods.append("GET" if combined_method == "POST" else "POST")
        target_router.add_api_route(
            path,
            _plan_export_handler,
            methods=methods,
            include_in_schema=combined_include if path == combined_path else include_in_schema,
            responses={429: {"description": "Rate limit exceeded"}},
        )

    return export_stub_router, plan_stub_router


def _plan_export_stub_routers_with_unrelated_path() -> tuple[APIRouter, APIRouter]:
    export_stub_router, plan_stub_router = _plan_export_stub_routers()

    async def _unrelated_handler() -> dict[str, str]:
        return {"status": "unrelated"}

    plan_stub_router.get("/api/v1/unrelated-plan-export-probe")(_unrelated_handler)
    return export_stub_router, plan_stub_router


def _shoplist_export_stub_router(
    *,
    omit: frozenset[str] = frozenset(),
    method_overrides: dict[str, str] | None = None,
    include_overrides: dict[str, bool] | None = None,
    include_429: bool = True,
) -> APIRouter:
    router = APIRouter()
    method_override_map = method_overrides or {}
    include_override_map = include_overrides or {}
    responses = {429: {"description": "Rate limit exceeded"}} if include_429 else None

    for path, method, include_in_schema in app_main._SHOPLIST_ROUTE_SPECS:
        if path in omit:
            continue
        route_method = method_override_map.get(path, method).lower()
        route_include = include_override_map.get(path, include_in_schema)

        async def _shoplist_export_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(router, route_method)(
            path,
            include_in_schema=route_include,
            responses=responses,
        )(_shoplist_export_handler)

    return router


def _duplicate_shoplist_export_stub_router() -> APIRouter:
    router = _shoplist_export_stub_router()
    duplicate_path, duplicate_method, duplicate_include = app_main._SHOPLIST_ROUTE_SPECS[0]

    async def _second_shoplist_export_handler() -> dict[str, str]:
        return {"status": "duplicate"}

    getattr(router, duplicate_method.lower())(
        duplicate_path,
        include_in_schema=duplicate_include,
        responses={429: {"description": "Rate limit exceeded"}},
    )(_second_shoplist_export_handler)
    return router


def _shoplist_export_stub_router_with_combined_methods() -> APIRouter:
    router = APIRouter()
    combined_path, combined_method, combined_include = app_main._SHOPLIST_ROUTE_SPECS[0]

    for path, method, include_in_schema in app_main._SHOPLIST_ROUTE_SPECS:

        async def _shoplist_export_handler(path: str = path) -> dict[str, str]:
            return {"status": path}

        methods = [method]
        if path == combined_path:
            methods.append("GET" if combined_method == "POST" else "POST")
        router.add_api_route(
            path,
            _shoplist_export_handler,
            methods=methods,
            include_in_schema=combined_include if path == combined_path else include_in_schema,
            responses={429: {"description": "Rate limit exceeded"}},
        )

    return router


def _shoplist_export_stub_router_with_unrelated_path() -> APIRouter:
    router = _shoplist_export_stub_router()

    async def _unrelated_handler() -> dict[str, str]:
        return {"status": "unrelated"}

    router.get("/api/v1/unrelated-shoplist-export-probe")(_unrelated_handler)
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


def _app_with_bodyfat_routes_and_extra_method(*, combined_route: bool) -> FastAPI:
    app = FastAPI()
    extra_path, extra_method, extra_include = app_main._BODYFAT_ROUTE_SPECS[0]
    app.include_router(app_main.bodyfat_router)

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


def _app_with_plan_export_routes_and_extra_method(*, combined_route: bool) -> FastAPI:
    app = FastAPI()
    extra_path, extra_method, extra_include = app_main._PLAN_EXPORT_ROUTE_SPECS[0]

    app.include_router(
        app_main.export_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
    )
    app.include_router(
        app_main.plan_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
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
        responses={429: {"description": "Rate limit exceeded"}},
    )
    return app


def _app_with_shoplist_export_routes_and_extra_method(*, combined_route: bool) -> FastAPI:
    app = FastAPI()
    extra_path, extra_method, extra_include = app_main._SHOPLIST_ROUTE_SPECS[0]

    app.include_router(
        app_main.shoplist_export_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
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
        responses={429: {"description": "Rate limit exceeded"}},
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
    monkeypatch.setattr(app_main, "register_http_middleware_stack", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_vip_routes", lambda target_app: None)
    monkeypatch.setattr(app_main, "register_pro_routes", lambda target_app: (None, None))
    monkeypatch.setattr(
        app_main,
        "register_bmi_routes",
        lambda target_app: BmiRouteRegistration(
            bmi_router=APIRouter(),
            bmi_pro_router=None,
            bmi_pro_legacy_alias_router=None,
            feature_bmi_pro_enabled=False,
        ),
    )
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
    monkeypatch.setattr(app_main, "shoplist_export_router", _shoplist_export_stub_router())
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


def test_paid_tier_registration_runs_vip_then_pro_and_mirrors_legacy_attrs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    calls: list[str] = []
    vip = APIRouter()
    pro = APIRouter()
    premium_week = APIRouter()

    def _register_vip(target_app: FastAPI) -> None:
        calls.append("vip")

    def _register_pro(target_app: FastAPI) -> tuple[APIRouter, APIRouter]:
        calls.append("pro")
        return pro, premium_week

    monkeypatch.setattr(app_main, "register_vip_routes", _register_vip)
    monkeypatch.setattr(app_main, "register_pro_routes", _register_pro)
    monkeypatch.setattr(app_main, "is_vip_module_enabled", lambda: True)
    monkeypatch.setattr(app_main, "_resolve_vip_router_for_compat", lambda: vip)
    monkeypatch.setattr(app_main, "VIP_MODULE_ENABLED", False)
    monkeypatch.setattr(app_main, "vip_router", None)
    monkeypatch.setattr(app_main, "pro_router", None)
    monkeypatch.setattr(app_main, "premium_week_router", None)
    monkeypatch.setattr(app_main._legacy_module, "VIP_MODULE_ENABLED", False)
    monkeypatch.setattr(app_main._legacy_module, "vip_router", None)
    monkeypatch.setattr(app_main._legacy_module, "pro_router", None)
    monkeypatch.setattr(app_main._legacy_module, "premium_week_router", None)

    _bootstrap_temp_app(FastAPI())

    assert calls == ["vip", "pro"]
    assert app_main.VIP_MODULE_ENABLED is True
    assert app_main.vip_router is vip
    assert app_main.pro_router is pro
    assert app_main.premium_week_router is premium_week
    assert app_main._legacy_module.VIP_MODULE_ENABLED is True
    assert app_main._legacy_module.vip_router is vip
    assert app_main._legacy_module.pro_router is pro
    assert app_main._legacy_module.premium_week_router is premium_week


def test_bmi_registration_runs_and_mirrors_legacy_attrs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    calls: list[str] = []
    bmi = APIRouter()
    bmi_pro = APIRouter()
    bmi_pro_alias = APIRouter()

    def _register_bmi(target_app: FastAPI) -> BmiRouteRegistration:
        calls.append("bmi")
        return BmiRouteRegistration(
            bmi_router=bmi,
            bmi_pro_router=bmi_pro,
            bmi_pro_legacy_alias_router=bmi_pro_alias,
            feature_bmi_pro_enabled=True,
        )

    monkeypatch.setattr(app_main, "register_bmi_routes", _register_bmi)
    monkeypatch.setattr(app_main, "FEATURE_BMI_PRO_ENABLED", False)
    monkeypatch.setattr(app_main, "bmi_router", None)
    monkeypatch.setattr(app_main, "bmi_pro_router", None)
    monkeypatch.setattr(app_main, "bmi_pro_legacy_alias_router", None)
    monkeypatch.setattr(app_main._legacy_module, "FEATURE_BMI_PRO_ENABLED", False)
    monkeypatch.setattr(app_main._legacy_module, "bmi_router", None)
    monkeypatch.setattr(app_main._legacy_module, "bmi_pro_router", None)
    monkeypatch.setattr(app_main._legacy_module, "bmi_pro_legacy_alias_router", None)

    _bootstrap_temp_app(FastAPI())

    assert calls == ["bmi"]
    assert app_main.FEATURE_BMI_PRO_ENABLED is True
    assert app_main.bmi_router is bmi
    assert app_main.bmi_pro_router is bmi_pro
    assert app_main.bmi_pro_legacy_alias_router is bmi_pro_alias
    assert app_main._legacy_module.FEATURE_BMI_PRO_ENABLED is True
    assert app_main._legacy_module.bmi_router is bmi
    assert app_main._legacy_module.bmi_pro_router is bmi_pro
    assert app_main._legacy_module.bmi_pro_legacy_alias_router is bmi_pro_alias


def _bmi_route_counts(app: FastAPI) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for route in iter_effective_route_candidates(app.routes):
        if not is_api_route_candidate(route):
            continue
        for method in sorted(route_methods(route) - {"HEAD", "OPTIONS"}):
            key = (method, route_path(route))
            counts[key] = counts.get(key, 0) + 1
    return counts


def _routes_for_path_method(app: FastAPI, path: str, method: str) -> list[object]:
    method_name = method.upper()
    return [
        route
        for route in iter_effective_route_candidates(app.routes)
        if route_path(route) == path and method_name in route_methods(route)
    ]


def _has_route_path(app: FastAPI, path: str) -> bool:
    return any(route_path(route) == path for route in iter_effective_route_candidates(app.routes))


def test_route_endpoint_for_path_method_rejects_duplicate_source_routes() -> None:
    router = APIRouter()

    async def _first() -> dict[str, str]:
        return {"status": "first"}

    async def _second() -> dict[str, str]:
        return {"status": "second"}

    router.post("/api/v1/source/duplicate")(_first)
    router.post("/api/v1/source/duplicate")(_second)

    with pytest.raises(
        RuntimeError,
        match="Duplicate source route detected for POST /api/v1/source/duplicate",
    ):
        route_endpoint_for_path_method(router.routes, "/api/v1/source/duplicate", "POST")


def test_effective_route_helpers_read_original_route_fallback() -> None:
    async def _handler() -> dict[str, str]:
        return {"status": "ok"}

    route = SimpleNamespace(
        original_route=SimpleNamespace(path="/api/v1/source/original", endpoint=_handler)
    )

    assert route_path(route) == "/api/v1/source/original"
    assert route_endpoint(route) is _handler


def test_duplicate_ws_guard_uses_effective_route_paths() -> None:
    app = FastAPI()

    async def _websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.close()

    app.add_api_websocket_route("/ws", _websocket_endpoint)

    with pytest.raises(RuntimeError, match="Duplicate /ws route detected"):
        app_main._assert_no_duplicate_ws_route(app)


def test_bmi_registration_defaults_to_free_route_only_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)
    app = FastAPI()

    first = register_bmi_routes(app)
    second = register_bmi_routes(app)

    assert second is first
    assert first.feature_bmi_pro_enabled is False
    assert first.bmi_pro_router is None
    assert first.bmi_pro_legacy_alias_router is None
    counts = _bmi_route_counts(app)
    assert counts[("POST", "/api/v1/bmi/calculate")] == 1
    assert ("POST", "/api/v1/pro/bmi") not in counts
    assert ("POST", "/api/v1/pro/bmi/calculate") not in counts
    assert ("POST", "/api/v1/bmi/pro") not in counts


def test_bmi_registration_enabled_registers_pro_family_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "true")
    app = FastAPI()

    registration = register_bmi_routes(app)

    assert registration.feature_bmi_pro_enabled is True
    assert registration.bmi_pro_router is not None
    assert registration.bmi_pro_legacy_alias_router is not None
    counts = _bmi_route_counts(app)
    assert counts[("POST", "/api/v1/bmi/calculate")] == 1
    assert counts[("POST", "/api/v1/pro/bmi")] == 1
    assert counts[("POST", "/api/v1/pro/bmi/calculate")] == 1
    assert counts[("POST", "/api/v1/bmi/pro")] == 1


def test_bmi_registration_rejects_empty_free_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    monkeypatch.setattr(bmi_module, "router", APIRouter())
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match="BMI router from app\\.routers\\.bmi must be a non-empty APIRouter",
    ):
        register_bmi_routes(FastAPI())


def test_bmi_registration_reports_unexpected_source_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    router = APIRouter(prefix="/api/v1/bmi")

    async def _calculate() -> dict[str, str]:
        return {"status": "calculate"}

    async def _extra() -> dict[str, str]:
        return {"status": "extra"}

    router.post("/calculate")(_calculate)
    router.get("/extra")(_extra)
    monkeypatch.setattr(bmi_module, "router", router)
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match=(
            "BMI router from app\\.routers\\.bmi route family mismatch: "
            "missing none; unexpected GET /api/v1/bmi/extra"
        ),
    ):
        register_bmi_routes(FastAPI())


def test_bmi_registration_rejects_non_api_route_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    router = APIRouter(prefix="/api/v1/bmi")

    async def _plain_route(request: object) -> JSONResponse:
        return JSONResponse({"path": str(request)})

    router.routes.append(Route("/calculate", _plain_route, methods=["POST"]))
    monkeypatch.setattr(bmi_module, "router", router)
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match=(
            "BMI router from app\\.routers\\.bmi contains Route; " "expected APIRoute-only members"
        ),
    ):
        register_bmi_routes(FastAPI())


def test_bmi_registration_rejects_multi_method_source_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    router = APIRouter(prefix="/api/v1/bmi")

    async def _calculate() -> dict[str, str]:
        return {"status": "calculate"}

    router.add_api_route("/calculate", _calculate, methods=["GET", "POST"])
    monkeypatch.setattr(bmi_module, "router", router)
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match=(
            "BMI router from app\\.routers\\.bmi route /api/v1/bmi/calculate "
            "exposes methods \\['GET', 'POST'\\]; expected exactly one "
            "non-framework method"
        ),
    ):
        register_bmi_routes(FastAPI())


def test_bmi_registration_rejects_duplicate_source_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    router = APIRouter(prefix="/api/v1/bmi")

    async def _calculate() -> dict[str, str]:
        return {"status": "calculate"}

    async def _duplicate_calculate() -> dict[str, str]:
        return {"status": "duplicate"}

    router.post("/calculate")(_calculate)
    router.post("/calculate")(_duplicate_calculate)
    monkeypatch.setattr(bmi_module, "router", router)
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match=(
            "BMI router from app\\.routers\\.bmi defines duplicate route "
            "POST /api/v1/bmi/calculate"
        ),
    ):
        register_bmi_routes(FastAPI())


def test_bmi_registration_rejects_source_route_openapi_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    router = APIRouter(prefix="/api/v1/bmi")

    async def _calculate() -> dict[str, str]:
        return {"status": "calculate"}

    router.post("/calculate", include_in_schema=False)(_calculate)
    monkeypatch.setattr(bmi_module, "router", router)
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match=(
            "BMI router from app\\.routers\\.bmi route POST "
            "/api/v1/bmi/calculate has include_in_schema=False; "
            "expected include_in_schema=True"
        ),
    ):
        register_bmi_routes(FastAPI())


def test_vip_compat_resolver_returns_none_when_vip_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main, "is_vip_module_enabled", lambda: False)

    assert app_main._resolve_vip_router_for_compat() is None


def test_vip_compat_resolver_returns_none_when_vip_module_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_missing_vip_module() -> object:
        raise ModuleNotFoundError(
            "No module named 'app.routers.vip'",
            name="app.routers.vip",
        )

    monkeypatch.setattr(app_main, "is_vip_module_enabled", lambda: True)
    monkeypatch.setattr(
        app_main,
        "_import_vip_module_for_compat",
        _raise_missing_vip_module,
    )

    assert app_main._resolve_vip_router_for_compat() is None


def test_vip_compat_resolver_reraises_nested_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_nested_import_failure() -> object:
        raise ModuleNotFoundError(
            "No module named 'vip_runtime_dependency'",
            name="vip_runtime_dependency",
        )

    monkeypatch.setattr(app_main, "is_vip_module_enabled", lambda: True)
    monkeypatch.setattr(
        app_main,
        "_import_vip_module_for_compat",
        _raise_nested_import_failure,
    )

    with pytest.raises(ModuleNotFoundError, match="vip_runtime_dependency"):
        app_main._resolve_vip_router_for_compat()


def test_paid_tier_registration_keeps_legacy_attrs_unchanged_when_pro_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    calls: list[str] = []
    original_vip_router = APIRouter()
    original_pro_router = APIRouter()
    original_premium_week_router = APIRouter()

    def _register_vip(target_app: FastAPI) -> None:
        calls.append("vip")

    def _register_pro(target_app: FastAPI) -> tuple[APIRouter, APIRouter]:
        calls.append("pro")
        raise RuntimeError("pro registration failed")

    monkeypatch.setattr(app_main, "register_vip_routes", _register_vip)
    monkeypatch.setattr(app_main, "register_pro_routes", _register_pro)
    monkeypatch.setattr(
        app_main,
        "_resolve_vip_router_for_compat",
        lambda: pytest.fail("compat mirror should not run after PRO failure"),
    )
    monkeypatch.setattr(app_main, "VIP_MODULE_ENABLED", False)
    monkeypatch.setattr(app_main, "vip_router", original_vip_router)
    monkeypatch.setattr(app_main, "pro_router", original_pro_router)
    monkeypatch.setattr(app_main, "premium_week_router", original_premium_week_router)
    monkeypatch.setattr(app_main._legacy_module, "VIP_MODULE_ENABLED", False)
    monkeypatch.setattr(app_main._legacy_module, "vip_router", original_vip_router)
    monkeypatch.setattr(app_main._legacy_module, "pro_router", original_pro_router)
    monkeypatch.setattr(
        app_main._legacy_module,
        "premium_week_router",
        original_premium_week_router,
    )

    with pytest.raises(RuntimeError, match="pro registration failed"):
        _bootstrap_temp_app(FastAPI())

    assert calls == ["vip", "pro"]
    assert app_main.VIP_MODULE_ENABLED is False
    assert app_main.vip_router is original_vip_router
    assert app_main.pro_router is original_pro_router
    assert app_main.premium_week_router is original_premium_week_router
    assert app_main._legacy_module.VIP_MODULE_ENABLED is False
    assert app_main._legacy_module.vip_router is original_vip_router
    assert app_main._legacy_module.pro_router is original_pro_router
    assert app_main._legacy_module.premium_week_router is original_premium_week_router


def test_paid_tier_registration_keeps_legacy_attrs_unchanged_when_compat_resolver_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    calls: list[str] = []
    original_vip_router = APIRouter()
    original_pro_router = APIRouter()
    original_premium_week_router = APIRouter()
    registered_pro_router = APIRouter()
    registered_premium_week_router = APIRouter()

    def _register_vip(target_app: FastAPI) -> None:
        calls.append("vip")

    def _register_pro(target_app: FastAPI) -> tuple[APIRouter, APIRouter]:
        calls.append("pro")
        return registered_pro_router, registered_premium_week_router

    def _fail_resolve_vip_router() -> APIRouter:
        raise RuntimeError("compat resolver failed")

    monkeypatch.setattr(app_main, "register_vip_routes", _register_vip)
    monkeypatch.setattr(app_main, "register_pro_routes", _register_pro)
    monkeypatch.setattr(app_main, "is_vip_module_enabled", lambda: True)
    monkeypatch.setattr(app_main, "_resolve_vip_router_for_compat", _fail_resolve_vip_router)
    monkeypatch.setattr(app_main, "VIP_MODULE_ENABLED", False)
    monkeypatch.setattr(app_main, "vip_router", original_vip_router)
    monkeypatch.setattr(app_main, "pro_router", original_pro_router)
    monkeypatch.setattr(app_main, "premium_week_router", original_premium_week_router)
    monkeypatch.setattr(app_main._legacy_module, "VIP_MODULE_ENABLED", False)
    monkeypatch.setattr(app_main._legacy_module, "vip_router", original_vip_router)
    monkeypatch.setattr(app_main._legacy_module, "pro_router", original_pro_router)
    monkeypatch.setattr(
        app_main._legacy_module,
        "premium_week_router",
        original_premium_week_router,
    )

    with pytest.raises(RuntimeError, match="compat resolver failed"):
        _bootstrap_temp_app(FastAPI())

    assert calls == ["vip", "pro"]
    assert app_main.VIP_MODULE_ENABLED is False
    assert app_main.vip_router is original_vip_router
    assert app_main.pro_router is original_pro_router
    assert app_main.premium_week_router is original_premium_week_router
    assert app_main._legacy_module.VIP_MODULE_ENABLED is False
    assert app_main._legacy_module.vip_router is original_vip_router
    assert app_main._legacy_module.pro_router is original_pro_router
    assert app_main._legacy_module.premium_week_router is original_premium_week_router


def test_paid_tier_registration_stops_before_pro_when_vip_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    original_pro_router = APIRouter()
    original_premium_week_router = APIRouter()

    def _register_vip(target_app: FastAPI) -> None:
        raise RuntimeError("vip registration failed")

    def _register_pro(target_app: FastAPI) -> tuple[APIRouter, APIRouter]:
        pytest.fail("PRO registration should not run after VIP failure")

    monkeypatch.setattr(app_main, "register_vip_routes", _register_vip)
    monkeypatch.setattr(app_main, "register_pro_routes", _register_pro)
    monkeypatch.setattr(app_main, "pro_router", original_pro_router)
    monkeypatch.setattr(app_main, "premium_week_router", original_premium_week_router)
    monkeypatch.setattr(app_main._legacy_module, "pro_router", original_pro_router)
    monkeypatch.setattr(
        app_main._legacy_module,
        "premium_week_router",
        original_premium_week_router,
    )

    with pytest.raises(RuntimeError, match="vip registration failed"):
        _bootstrap_temp_app(FastAPI())

    assert app_main.pro_router is original_pro_router
    assert app_main.premium_week_router is original_premium_week_router
    assert app_main._legacy_module.pro_router is original_pro_router
    assert app_main._legacy_module.premium_week_router is original_premium_week_router


def test_pro_registration_rejects_empty_canonical_pro_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.pro as pro_module
    import app.utils.feature_flags as feature_flags
    from app.routers.pro_registration import register_pro_routes

    monkeypatch.setattr(pro_module, "router", APIRouter())
    monkeypatch.delenv("FEATURE_PREMIUM_WEEK_ENABLED", raising=False)
    monkeypatch.setattr(feature_flags, "is_vip_module_enabled", lambda: False)

    with pytest.raises(
        RuntimeError,
        match="PRO router from app\\.routers\\.pro must be a non-empty APIRouter",
    ):
        register_pro_routes(FastAPI())


def test_vip_registration_rejects_empty_canonical_vip_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.vip as vip_module
    import app.utils.feature_flags as feature_flags
    from app.routers.vip_registration import register_vip_routes

    monkeypatch.setattr(vip_module, "router", APIRouter())
    monkeypatch.setattr(feature_flags, "is_vip_module_enabled", lambda: True)

    with pytest.raises(
        RuntimeError,
        match="VIP router from app\\.routers\\.vip must be a non-empty APIRouter",
    ):
        register_vip_routes(FastAPI())


def test_vip_route_registration_rejects_foreign_existing_paid_tier_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.vip_registration import register_vip_routes

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    app = FastAPI()

    async def _shadow_vip_regions() -> dict[str, str]:
        return {"status": "shadow"}

    app.add_api_route("/api/v1/vip/regions", _shadow_vip_regions, methods=["GET"])

    with pytest.raises(
        RuntimeError,
        match="Partial vip route registration|Duplicate /api/v1/vip/regions route",
    ):
        register_vip_routes(app)


def test_vip_route_registration_rejects_foreign_existing_fitchef_insight_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.vip_registration import register_vip_routes

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    app = FastAPI()

    async def _shadow_fitchef_insight() -> dict[str, str]:
        return {"status": "shadow"}

    app.add_api_route("/api/v1/insight/fitchef", _shadow_fitchef_insight, methods=["POST"])

    with pytest.raises(
        RuntimeError,
        match="Duplicate /api/v1/insight/fitchef route detected with a different handler",
    ):
        register_vip_routes(app)


def test_pro_route_registration_rejects_foreign_existing_paid_tier_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.pro_registration import register_pro_routes

    monkeypatch.setenv("FEATURE_PREMIUM_WEEK_ENABLED", "false")
    app = FastAPI()

    async def _shadow_pro_weekly() -> dict[str, str]:
        return {"status": "shadow"}

    app.add_api_route("/api/v1/pro/meal/weekly", _shadow_pro_weekly, methods=["POST"])

    with pytest.raises(
        RuntimeError,
        match="Partial pro route registration|Duplicate /api/v1/pro/meal/weekly route",
    ):
        register_pro_routes(app)


def test_pro_contract_registration_rejects_foreign_existing_handlers() -> None:
    from app.bootstrap.pro_contracts import register_pro_contract_routes

    app = FastAPI()

    async def _shadow_pro_contract() -> dict[str, str]:
        return {"status": "shadow"}

    app.add_api_route(
        "/api/v1/pro/nutrition/targets",
        _shadow_pro_contract,
        methods=["POST"],
    )
    app.add_api_route(
        "/api/v1/pro/nutrition/plate",
        _shadow_pro_contract,
        methods=["POST"],
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different PRO contract handler",
    ):
        register_pro_contract_routes(app)


def test_pro_contract_registration_rejects_source_router_without_expected_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.bootstrap.pro_contracts as pro_contracts_module

    monkeypatch.setattr(
        pro_contracts_module,
        "route_endpoint_for_path_method",
        lambda _routes, _path, _method: None,
    )

    with pytest.raises(
        RuntimeError,
        match="PRO contract router does not define the expected route family",
    ):
        pro_contracts_module.register_pro_contract_routes(FastAPI())


def test_pro_contract_registration_rejects_existing_handlers_without_pro_dependency() -> None:
    from app.bootstrap.pro_contracts import register_pro_contract_routes
    from app.routers.pro_nutrition_contracts import pro_nutrition_plate, pro_nutrition_targets

    app = FastAPI()
    app.add_api_route(
        "/api/v1/pro/nutrition/targets",
        pro_nutrition_targets,
        methods=["POST"],
    )
    app.add_api_route(
        "/api/v1/pro/nutrition/plate",
        pro_nutrition_plate,
        methods=["POST"],
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Existing /api/v1/pro/nutrition/targets route does not preserve "
            "PRO contract required dependency"
        ),
    ):
        register_pro_contract_routes(app)


def test_billing_registration_rejects_foreign_existing_handlers() -> None:
    from app.routers.billing import register_billing_routes

    app = FastAPI()

    async def _shadow_billing() -> dict[str, str]:
        return {"status": "shadow"}

    app.add_api_route(
        "/api/v1/billing/apple/verify-receipt",
        _shadow_billing,
        methods=["POST"],
    )
    app.add_api_route(
        "/api/v1/pro/payments/ru-by/manual-intent",
        _shadow_billing,
        methods=["POST"],
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different billing handler",
    ):
        register_billing_routes(app)


def test_billing_registration_rejects_partial_existing_canonical_state() -> None:
    from app.routers import billing as billing_module

    app = FastAPI()
    app.include_router(billing_module.billing_router)

    with pytest.raises(RuntimeError, match="Partial billing routes detected"):
        billing_module.register_billing_routes(app)


def test_billing_registration_rejects_source_router_without_expected_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import billing as billing_module

    monkeypatch.setattr(
        billing_module,
        "route_endpoint_for_path_method",
        lambda _routes, _path, _method: None,
    )

    with pytest.raises(
        RuntimeError,
        match="Billing router does not define the expected route family",
    ):
        billing_module.register_billing_routes(FastAPI())


def test_billing_registration_is_idempotent_when_both_canonical_routes_exist() -> None:
    from app.routers import billing as billing_module

    app = FastAPI()
    app.include_router(billing_module.billing_router)
    app.include_router(billing_module.router)

    assert billing_module.register_billing_routes(app) is billing_module.router
    counts = _bmi_route_counts(app)
    assert counts[("POST", "/api/v1/billing/apple/verify-receipt")] == 1
    assert counts[("POST", "/api/v1/pro/payments/ru-by/manual-intent")] == 1


def test_vip_route_registration_rejects_missing_fitchef_insight_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.fitchef_insight as fitchef_insight_module
    from app.routers.vip_registration import register_vip_routes

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setattr(fitchef_insight_module, "router", APIRouter())

    with pytest.raises(
        RuntimeError,
        match="FitChef insight router does not define the expected POST route",
    ):
        register_vip_routes(FastAPI())


def test_paywall_route_registration_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    paywall_routes = _routes_for_path_method(app, app_main._PAYWALL_EVENTS_ROUTE_PATH, "POST")
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
        health_routes = _routes_for_path_method(app, path, "GET")
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

    favicon_routes = _routes_for_path_method(app, app_main.FAVICON_ROUTE_PATH, "GET")
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
        admin_routes = _routes_for_path_method(app, path, method)
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

    assert _has_route_path(app, "/api/v1/unrelated-admin-probe")


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
        matching_routes = _routes_for_path_method(app, path, method)
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

    assert _has_route_path(app, "/api/v1/unrelated-bmi-compat-probe")


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
    matching_route = _routes_for_path_method(app, path, method)[0]
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


def test_bodyfat_route_registration_is_idempotent() -> None:
    app = FastAPI()

    app_main._include_bodyfat_router_if_needed(app)
    app_main._include_bodyfat_router_if_needed(app)

    for path, method, include_in_schema in app_main._BODYFAT_ROUTE_SPECS:
        matching_routes = _routes_for_path_method(app, path, method)
        assert len(matching_routes) == 1
        matching_route = matching_routes[0]
        assert getattr(matching_route, "include_in_schema", True) is include_in_schema
        assert getattr(matching_route.endpoint, "__module__", "") == "app.routers.bodyfat"
        assert not matching_route.dependant.dependencies
        assert 429 not in (matching_route.responses or {})

    assert not _routes_for_path_method(app, "/bodyfat", "POST")


def test_bodyfat_route_registration_rejects_wrong_method() -> None:
    app = FastAPI()
    path, method, include_in_schema = app_main._BODYFAT_ROUTE_SPECS[0]

    async def _wrong_method_bodyfat_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    wrong_method = "GET" if method == "POST" else "POST"
    getattr(app, wrong_method.lower())(path, include_in_schema=include_in_schema)(
        _wrong_method_bodyfat_route
    )

    with pytest.raises(RuntimeError, match="Partial bodyfat route registration detected"):
        app_main._include_bodyfat_router_if_needed(app)


def test_bodyfat_route_registration_rejects_wrong_method_in_canonical_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, method, _include_in_schema = app_main._BODYFAT_ROUTE_SPECS[0]
    wrong_method = "GET" if method == "POST" else "POST"
    monkeypatch.setattr(
        app_main,
        "bodyfat_router",
        _bodyfat_stub_router(method_overrides={path: wrong_method}),
    )

    with pytest.raises(
        RuntimeError,
        match="Bodyfat router does not define the expected route family",
    ):
        app_main._include_bodyfat_router_if_needed(FastAPI())


def test_bodyfat_route_registration_rejects_combined_methods_in_canonical_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_main,
        "bodyfat_router",
        _bodyfat_stub_router_with_combined_methods(),
    )

    with pytest.raises(
        RuntimeError,
        match="Bodyfat router does not define the expected route family",
    ):
        app_main._include_bodyfat_router_if_needed(FastAPI())


def test_bodyfat_route_registration_rejects_existing_wrong_method_after_full_family() -> None:
    with pytest.raises(RuntimeError, match="Partial bodyfat route registration detected"):
        app_main._include_bodyfat_router_if_needed(
            _app_with_bodyfat_routes_and_extra_method(combined_route=False)
        )


def test_bodyfat_route_registration_rejects_existing_combined_methods() -> None:
    with pytest.raises(RuntimeError, match="Partial bodyfat route registration detected"):
        app_main._include_bodyfat_router_if_needed(
            _app_with_bodyfat_routes_and_extra_method(combined_route=True)
        )


def test_bodyfat_route_registration_rejects_foreign_handlers() -> None:
    app = FastAPI()
    path, method, include_in_schema = app_main._BODYFAT_ROUTE_SPECS[0]

    async def _foreign_bodyfat_route() -> dict[str, str]:
        return {"status": "foreign"}

    getattr(app, method.lower())(path, include_in_schema=include_in_schema)(_foreign_bodyfat_route)

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different bodyfat handler",
    ):
        app_main._include_bodyfat_router_if_needed(app)


def test_bodyfat_route_registration_rejects_openapi_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, _method, include_in_schema = app_main._BODYFAT_ROUTE_SPECS[0]
    monkeypatch.setattr(
        app_main,
        "bodyfat_router",
        _bodyfat_stub_router(include_overrides={path: not include_in_schema}),
    )

    with pytest.raises(
        RuntimeError,
        match="Bodyfat router does not preserve OpenAPI visibility",
    ):
        app_main._include_bodyfat_router_if_needed(FastAPI())


def test_bodyfat_route_registration_rejects_existing_openapi_visibility_drift() -> None:
    app = FastAPI()
    app.include_router(app_main.bodyfat_router)
    path, method, include_in_schema = app_main._BODYFAT_ROUTE_SPECS[0]
    matching_route = _routes_for_path_method(app, path, method)[0]
    matching_route.include_in_schema = not include_in_schema

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve bodyfat OpenAPI visibility",
    ):
        app_main._include_bodyfat_router_if_needed(app)


def test_bodyfat_route_registration_rejects_unrelated_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_main,
        "bodyfat_router",
        _bodyfat_stub_router_with_unrelated_path(),
    )

    with pytest.raises(
        RuntimeError,
        match="Bodyfat router does not define the expected route family",
    ):
        app_main._include_bodyfat_router_if_needed(FastAPI())


def test_bodyfat_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main, "bodyfat_router", _duplicate_bodyfat_stub_router())

    with pytest.raises(
        RuntimeError,
        match="Bodyfat router does not define the expected route family",
    ):
        app_main._include_bodyfat_router_if_needed(FastAPI())


def test_bodyfat_direct_router_remains_unprefixed_compatibility() -> None:
    from app.routers.bodyfat import get_router

    app = FastAPI()
    app.include_router(get_router())
    client = TestClient(app)
    payload = {
        "height_m": 1.75,
        "weight_kg": 75,
        "age": 30,
        "gender": "male",
        "neck_cm": 38,
        "waist_cm": 80,
        "language": "en",
    }

    response = client.post("/bodyfat", json=payload)
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert {"labels", "lang", "median", "methods"} <= response.json().keys()
    assert client.post("/api/v1/bodyfat", json=payload).status_code == 404


def test_bodyfat_final_openapi_hides_path() -> None:
    app_main.app.openapi_schema = None
    route_matches = _routes_for_path_method(app_main.app, "/api/v1/bodyfat", "POST")

    assert len(route_matches) == 1
    assert "/api/v1/bodyfat" not in app_main.app.openapi()["paths"]
    assert "/bodyfat" not in app_main.app.openapi()["paths"]


def test_plan_export_route_registration_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    for path, method, include_in_schema in app_main._PLAN_EXPORT_ROUTE_SPECS:
        matching_routes = _routes_for_path_method(app, path, method)
        assert len(matching_routes) == 1
        assert getattr(matching_routes[0], "endpoint").__module__ == "app.routers.plan_export"
        assert getattr(matching_routes[0], "include_in_schema", True) is include_in_schema
        assert 429 in (getattr(matching_routes[0], "responses", None) or {})
        assert route_has_dependency_call(
            matching_routes[0],
            app_main._get_api_key_dynamic,
        )


def test_plan_export_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._PLAN_EXPORT_ROUTE_SPECS[0]

    async def _existing_plan_export_route() -> dict[str, str]:
        return {"status": "partial"}

    getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
        _existing_plan_export_route
    )

    with pytest.raises(
        RuntimeError,
        match="Partial plan export route registration detected",
    ):
        _bootstrap_temp_app(app)


def test_plan_export_route_registration_rejects_missing_api_key_dependency_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Plan export API key dependency is unavailable",
    ):
        _bootstrap_temp_app(FastAPI())


def test_plan_export_route_registration_rejects_wrong_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._PLAN_EXPORT_ROUTE_SPECS[0]

    async def _wrong_method_plan_export_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    wrong_method = "GET" if method == "POST" else "POST"
    getattr(app, wrong_method.lower())(path, include_in_schema=include_in_schema)(
        _wrong_method_plan_export_route
    )

    with pytest.raises(
        RuntimeError,
        match="Partial plan export route registration detected",
    ):
        _bootstrap_temp_app(app)


def test_plan_export_route_registration_rejects_existing_wrong_method_after_full_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="Partial plan export route registration detected",
    ):
        _bootstrap_temp_app(_app_with_plan_export_routes_and_extra_method(combined_route=False))


def test_plan_export_route_registration_rejects_existing_combined_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="Partial plan export route registration detected",
    ):
        _bootstrap_temp_app(_app_with_plan_export_routes_and_extra_method(combined_route=True))


def test_plan_export_route_registration_rejects_wrong_method_in_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, method, _include_in_schema = app_main._PLAN_EXPORT_ROUTE_SPECS[0]
    wrong_method = "GET" if method == "POST" else "POST"
    export_stub_router, plan_stub_router = _plan_export_stub_routers(
        method_overrides={path: wrong_method}
    )
    monkeypatch.setattr(app_main, "export_router", export_stub_router)
    monkeypatch.setattr(app_main, "plan_router", plan_stub_router)

    with pytest.raises(
        RuntimeError,
        match="Plan export router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_plan_export_route_registration_rejects_combined_methods_in_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    export_stub_router, plan_stub_router = _plan_export_stub_routers_with_combined_methods()
    monkeypatch.setattr(app_main, "export_router", export_stub_router)
    monkeypatch.setattr(app_main, "plan_router", plan_stub_router)

    with pytest.raises(
        RuntimeError,
        match="Plan export router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_plan_export_route_registration_rejects_unrelated_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    export_stub_router, plan_stub_router = _plan_export_stub_routers_with_unrelated_path()
    monkeypatch.setattr(app_main, "export_router", export_stub_router)
    monkeypatch.setattr(app_main, "plan_router", plan_stub_router)

    with pytest.raises(
        RuntimeError,
        match="Plan export router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_plan_export_callable_equivalence_rejects_non_callables() -> None:
    expected_endpoint = next(
        route.endpoint
        for route in app_main.export_router.routes
        if getattr(route, "path", None) == app_main._PLAN_EXPORT_ROUTE_SPECS[0][0]
    )

    assert not same_callable_by_module_and_qualname(None, expected_endpoint)
    assert not same_callable_by_module_and_qualname(expected_endpoint, None)


def test_plan_export_route_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()

    for path, method, include_in_schema in app_main._PLAN_EXPORT_ROUTE_SPECS:

        async def _foreign_plan_export_route(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
            _foreign_plan_export_route
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different plan export handler",
    ):
        _bootstrap_temp_app(app)


def test_plan_export_route_registration_rejects_missing_api_key_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    app.include_router(app_main.export_router)
    app.include_router(app_main.plan_router)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve plan export required dependency",
    ):
        app_main._include_plan_export_routers_if_needed(app)


def test_plan_export_route_registration_rejects_openapi_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, _method, include_in_schema = app_main._PLAN_EXPORT_ROUTE_SPECS[0]
    export_stub_router, plan_stub_router = _plan_export_stub_routers(
        include_overrides={path: not include_in_schema}
    )
    monkeypatch.setattr(app_main, "export_router", export_stub_router)
    monkeypatch.setattr(app_main, "plan_router", plan_stub_router)

    with pytest.raises(
        RuntimeError,
        match="Plan export router does not preserve OpenAPI visibility",
    ):
        _bootstrap_temp_app(FastAPI())


def test_plan_export_route_registration_rejects_existing_openapi_visibility_drift() -> None:
    app = FastAPI()
    app.include_router(
        app_main.export_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
    )
    app.include_router(
        app_main.plan_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
    )
    path, method, include_in_schema = app_main._PLAN_EXPORT_ROUTE_SPECS[0]
    matching_route = _routes_for_path_method(app, path, method)[0]
    matching_route.include_in_schema = not include_in_schema

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve plan export OpenAPI visibility",
    ):
        app_main._include_plan_export_routers_if_needed(app)


def test_plan_export_dependency_detection_walks_nested_dependencies() -> None:
    app = FastAPI()

    async def _outer_dependency(
        _guard: None = Depends(app_main._get_api_key_dynamic),
    ) -> None:
        return None

    async def _nested_dependency_probe() -> dict[str, str]:
        return {"status": "nested"}

    app.add_api_route(
        "/api/v1/nested-plan-export-dependency-probe",
        _nested_dependency_probe,
        methods=["GET"],
        dependencies=[Depends(_outer_dependency)],
    )

    route = _routes_for_path_method(app, "/api/v1/nested-plan-export-dependency-probe", "GET")[0]

    assert route_has_dependency_call(
        route,
        app_main._get_api_key_dynamic,
    )


def test_plan_export_route_registration_rejects_existing_429_metadata_drift() -> None:
    app = FastAPI()
    app.include_router(
        app_main.export_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
    )
    app.include_router(
        app_main.plan_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
    )
    path, method, _include_in_schema = app_main._PLAN_EXPORT_ROUTE_SPECS[0]
    matching_route = _routes_for_path_method(app, path, method)[0]
    matching_route.responses.pop(429, None)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve 429 response metadata",
    ):
        app_main._include_plan_export_routers_if_needed(app)


def test_plan_export_route_registration_rejects_missing_429_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    export_stub_router, plan_stub_router = _plan_export_stub_routers(include_429=False)
    monkeypatch.setattr(app_main, "export_router", export_stub_router)
    monkeypatch.setattr(app_main, "plan_router", plan_stub_router)

    with pytest.raises(
        RuntimeError,
        match="Plan export router does not preserve 429 response metadata",
    ):
        _bootstrap_temp_app(FastAPI())


def test_plan_export_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    export_stub_router, plan_stub_router = _duplicate_plan_export_stub_routers()
    monkeypatch.setattr(app_main, "export_router", export_stub_router)
    monkeypatch.setattr(app_main, "plan_router", plan_stub_router)

    with pytest.raises(
        RuntimeError,
        match="Plan export router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_shoplist_export_route_registration_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    app = FastAPI()

    _bootstrap_temp_app(app)
    _bootstrap_temp_app(app)

    for path, method, include_in_schema in app_main._SHOPLIST_ROUTE_SPECS:
        matching_routes = _routes_for_path_method(app, path, method)
        assert len(matching_routes) == 1
        assert getattr(matching_routes[0], "include_in_schema", True) is include_in_schema
        assert 429 in (getattr(matching_routes[0], "responses", None) or {})
        assert route_has_dependency_call(
            matching_routes[0],
            app_main._get_api_key_dynamic,
        )


def test_shoplist_export_route_registration_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._SHOPLIST_ROUTE_SPECS[0]

    async def _existing_shoplist_export_route() -> dict[str, str]:
        return {"status": "partial"}

    getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
        _existing_shoplist_export_route
    )

    with pytest.raises(
        RuntimeError,
        match="Partial shoplist export route registration detected",
    ):
        _bootstrap_temp_app(app)


def test_shoplist_export_route_registration_rejects_missing_api_key_dependency_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Shoplist export API key dependency is unavailable",
    ):
        app_main._include_shoplist_export_router_if_needed(FastAPI())


def test_restaurant_moderation_route_registration_rejects_missing_api_key_dependency_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Restaurant moderation API key dependency is unavailable",
    ):
        app_main._include_restaurant_moderation_router_if_needed(FastAPI())


def test_shoplist_export_route_registration_rejects_wrong_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    path, method, include_in_schema = app_main._SHOPLIST_ROUTE_SPECS[0]

    async def _wrong_method_shoplist_export_route() -> dict[str, str]:
        return {"status": "wrong-method"}

    wrong_method = "GET" if method == "POST" else "POST"
    getattr(app, wrong_method.lower())(path, include_in_schema=include_in_schema)(
        _wrong_method_shoplist_export_route
    )

    with pytest.raises(
        RuntimeError,
        match="Partial shoplist export route registration detected",
    ):
        _bootstrap_temp_app(app)


def test_shoplist_export_route_registration_rejects_existing_wrong_method_after_full_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="Partial shoplist export route registration detected",
    ):
        _bootstrap_temp_app(_app_with_shoplist_export_routes_and_extra_method(combined_route=False))


def test_shoplist_export_route_registration_rejects_existing_combined_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="Partial shoplist export route registration detected",
    ):
        _bootstrap_temp_app(_app_with_shoplist_export_routes_and_extra_method(combined_route=True))


def test_shoplist_export_route_registration_rejects_wrong_method_in_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, method, _include_in_schema = app_main._SHOPLIST_ROUTE_SPECS[0]
    wrong_method = "GET" if method == "POST" else "POST"
    monkeypatch.setattr(
        app_main,
        "shoplist_export_router",
        _shoplist_export_stub_router(method_overrides={path: wrong_method}),
    )

    with pytest.raises(
        RuntimeError,
        match="Shoplist export router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_shoplist_export_route_registration_rejects_combined_methods_in_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "shoplist_export_router",
        _shoplist_export_stub_router_with_combined_methods(),
    )

    with pytest.raises(
        RuntimeError,
        match="Shoplist export router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_shoplist_export_route_registration_rejects_unrelated_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "shoplist_export_router",
        _shoplist_export_stub_router_with_unrelated_path(),
    )

    with pytest.raises(
        RuntimeError,
        match="Shoplist export router does not define the expected route family",
    ):
        _bootstrap_temp_app(FastAPI())


def test_shoplist_export_callable_equivalence_rejects_non_callables() -> None:
    expected_endpoint = next(
        route.endpoint
        for route in app_main.shoplist_export_router.routes
        if getattr(route, "path", None) == app_main._SHOPLIST_ROUTE_SPECS[0][0]
    )

    assert not same_callable_by_module_and_qualname(None, expected_endpoint)
    assert not same_callable_by_module_and_qualname(expected_endpoint, None)


def test_shoplist_export_route_registration_rejects_foreign_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()

    for path, method, include_in_schema in app_main._SHOPLIST_ROUTE_SPECS:

        async def _foreign_shoplist_export_route(path: str = path) -> dict[str, str]:
            return {"status": path}

        getattr(app, method.lower())(path, include_in_schema=include_in_schema)(
            _foreign_shoplist_export_route
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different shoplist export handler",
    ):
        _bootstrap_temp_app(app)


def test_shoplist_export_route_registration_rejects_missing_api_key_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    app.include_router(app_main.shoplist_export_router)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve shoplist export required dependency",
    ):
        app_main._include_shoplist_export_router_if_needed(app)


def test_shoplist_export_route_registration_rejects_openapi_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    path, _method, include_in_schema = app_main._SHOPLIST_ROUTE_SPECS[0]
    monkeypatch.setattr(
        app_main,
        "shoplist_export_router",
        _shoplist_export_stub_router(include_overrides={path: not include_in_schema}),
    )

    with pytest.raises(
        RuntimeError,
        match="Shoplist export router does not preserve OpenAPI visibility",
    ):
        _bootstrap_temp_app(FastAPI())


def test_shoplist_export_route_registration_rejects_existing_openapi_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    app.include_router(
        app_main.shoplist_export_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
    )
    path, method, include_in_schema = app_main._SHOPLIST_ROUTE_SPECS[0]
    matching_route = _routes_for_path_method(app, path, method)[0]
    matching_route.include_in_schema = not include_in_schema

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve shoplist export OpenAPI visibility",
    ):
        app_main._include_shoplist_export_router_if_needed(app)


def test_shoplist_export_route_registration_rejects_existing_429_metadata_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    app = FastAPI()
    app.include_router(
        app_main.shoplist_export_router,
        dependencies=[Depends(app_main._get_api_key_dynamic)],
    )
    path, method, _include_in_schema = app_main._SHOPLIST_ROUTE_SPECS[0]
    matching_route = _routes_for_path_method(app, path, method)[0]
    matching_route.responses.pop(429, None)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve 429 response metadata",
    ):
        app_main._include_shoplist_export_router_if_needed(app)


def test_shoplist_export_route_registration_rejects_missing_429_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "shoplist_export_router",
        _shoplist_export_stub_router(include_429=False),
    )

    with pytest.raises(
        RuntimeError,
        match="Shoplist export router does not preserve 429 response metadata",
    ):
        _bootstrap_temp_app(FastAPI())


def test_shoplist_export_route_registration_rejects_duplicate_canonical_router_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "shoplist_export_router",
        _duplicate_shoplist_export_stub_router(),
    )

    with pytest.raises(
        RuntimeError,
        match="Shoplist export router does not define the expected route family",
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
        matching_routes = _routes_for_path_method(app, path, method)
        assert len(matching_routes) == 1
        assert getattr(matching_routes[0], "include_in_schema", True) is include_in_schema


def test_legacy_export_alias_route_registration_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_bootstrap_dependencies(monkeypatch)
    monkeypatch.setattr(app_main._legacy_module, "EXPORTS_ENABLED", False)

    app = _bootstrap_temp_app(FastAPI())

    for path, method, _include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS:
        assert not _routes_for_path_method(app, path, method)


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

    assert _has_route_path(app, "/api/v1/unrelated-legacy-export-probe")


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
        matching_routes = _routes_for_path_method(app, path, method)
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
    matching_route = _routes_for_path_method(app, path, method)[0]
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

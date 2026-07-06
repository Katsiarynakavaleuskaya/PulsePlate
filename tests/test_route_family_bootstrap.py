from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException, WebSocket
from fastapi.testclient import TestClient

import app.main as app_main
from app.bootstrap.route_family import (
    RouteMemberContract,
    _family_routes,
    ensure_route_family_registered,
    route_member_contracts_from_router,
    route_has_dependency_call,
    same_callable_by_module_and_qualname,
)
from app.routers import legacy_premium_nutrition
from tests.helpers.module_resolve import resolve_legacy_app


async def _api_key_dependency() -> str:
    return "ok"


async def _member_dependency() -> None:
    return None


_MEMBERS = (
    RouteMemberContract(
        path="/api/v1/static-family/a",
        method="GET",
        include_in_schema=True,
        required_status_codes=frozenset({429}),
        required_dependencies=(_api_key_dependency,),
    ),
    RouteMemberContract(
        path="/api/v1/static-family/b",
        method="POST",
        include_in_schema=False,
        required_status_codes=frozenset({429}),
        required_dependencies=(_api_key_dependency, _member_dependency),
    ),
)


def _family_routers(
    *,
    omit: frozenset[str] | None = None,
    method_overrides: dict[str, str] | None = None,
    include_overrides: dict[str, bool] | None = None,
    include_429: bool = True,
    include_unexpected: bool = False,
    include_websocket: bool = False,
    combined_methods_path: str | None = None,
) -> tuple[APIRouter, APIRouter]:
    route_a = APIRouter()
    route_b = APIRouter()
    routers = {
        "/api/v1/static-family/a": route_a,
        "/api/v1/static-family/b": route_b,
    }
    method_override_map = method_overrides or {}
    include_override_map = include_overrides or {}
    omit_set = omit or frozenset()

    for member in _MEMBERS:
        if member.path in omit_set:
            continue

        async def _handler(path: str = member.path) -> dict[str, str]:
            return {"path": path}

        route_methods = [method_override_map.get(member.path, member.method)]
        if combined_methods_path == member.path:
            route_methods.append("DELETE")
        dependencies = [Depends(_member_dependency)] if member.path.endswith("/b") else []
        routers[member.path].add_api_route(
            member.path,
            _handler,
            methods=route_methods,
            include_in_schema=include_override_map.get(member.path, member.include_in_schema),
            responses={429: {"description": "rate limit"}} if include_429 else {},
            dependencies=dependencies,
        )

    if include_unexpected:

        async def _unexpected() -> dict[str, str]:
            return {"path": "unexpected"}

        route_a.get("/api/v1/static-family/unexpected")(_unexpected)

    if include_websocket:

        async def _websocket(websocket: WebSocket) -> None:
            await websocket.close()

        route_a.websocket("/api/v1/static-family/ws")(_websocket)

    return route_a, route_b


def _ensure(
    app: FastAPI,
    routers: Sequence[APIRouter],
) -> None:
    ensure_route_family_registered(
        app,
        family_name="Static family",
        routers=routers,
        members=_MEMBERS,
        registration_dependencies=(Depends(_api_key_dependency),),
    )


def _who_targets_response() -> app_main._legacy_module.WHOTargetsResponse:
    legacy_module = resolve_legacy_app()
    return legacy_module.WHOTargetsResponse(
        kcal_daily=1900,
        macros={"protein_g": 95, "fat_g": 63, "carbs_g": 238, "fiber_g": 28},
        water_ml=2200,
        priority_micros={"iron_mg": 18.0},
        activity_weekly={"minutes": 150},
        calculation_date="2026-07-06",
        warnings=[],
        ui_labels=legacy_module.build_who_targets_ui_labels("en"),
    )


def _matching_routes(app: FastAPI, member: RouteMemberContract) -> list[object]:
    return [
        route
        for route in _family_routes(app, {member.path})
        if member.method in (getattr(route, "methods", None) or set())
    ]


def test_route_member_contract_defaults_are_immutable_empty_collections() -> None:
    member = RouteMemberContract(
        path="/api/v1/static-family/defaults",
        method="get",
        include_in_schema=True,
    )

    assert member.method == "GET"
    assert member.required_status_codes == frozenset()
    assert member.required_dependencies == ()


def test_static_route_family_rejects_duplicate_member_contracts() -> None:
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


def test_static_route_family_rejects_empty_member_contracts() -> None:
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


def test_static_route_family_rejects_non_http_source_routes() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(FastAPI(), _family_routers(include_websocket=True))


def test_static_route_family_contract_builder_ignores_fastapi_included_router_marker() -> None:
    child_router = APIRouter()

    async def _child_handler() -> dict[str, str]:
        return {"status": "ok"}

    child_router.get("/api/v1/static-family/child")(_child_handler)
    parent_router = APIRouter()
    parent_router.include_router(child_router)

    assert any(type(route).__name__ == "_IncludedRouter" for route in parent_router.routes)

    assert route_member_contracts_from_router("Static family", parent_router) == (
        RouteMemberContract(
            path="/api/v1/static-family/child",
            method="GET",
            include_in_schema=True,
        ),
    )


def test_static_route_family_registration_is_idempotent() -> None:
    app = FastAPI()

    _ensure(app, _family_routers())
    _ensure(app, _family_routers())

    for member in _MEMBERS:
        routes = _matching_routes(app, member)
        assert len(routes) == 1
        route = routes[0]
        assert getattr(route, "include_in_schema", True) is member.include_in_schema
        assert 429 in (getattr(route, "responses", None) or {})
        assert route_has_dependency_call(route, _api_key_dependency)
        for dependency in member.required_dependencies:
            assert route_has_dependency_call(route, dependency)


def test_legacy_premium_plate_wrapper_delegates_inside_route_family_ci_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_module = resolve_legacy_app()
    req = legacy_module.PlateRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
        goal="maintain",
    )
    expected = legacy_module.PlateResponse(
        kcal=1900,
        macros={"protein_g": 95, "fat_g": 63, "carbs_g": 238},
        portions={"vegetables": 0.5, "protein": 0.25, "grains": 0.25},
        layout=[],
        meals=[],
    )
    captured: dict[str, object] = {}

    async def _fake_legacy_handler(
        received: app_main._legacy_module.PlateRequest,
    ) -> app_main._legacy_module.PlateResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(resolve_legacy_app(), "api_premium_plate", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_premium_plate(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_api_bmr_wrapper_delegates_inside_route_family_ci_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_module = resolve_legacy_app()
    req = legacy_module.BMRRequest(
        weight_kg=70,
        height_cm=175,
        age=35,
        sex="male",
        activity="moderate",
    )
    expected = legacy_module.BMRResponse(
        bmr={"mifflin": 1650.0},
        tdee={"mifflin": 2557.5},
        activity_level="moderate",
        recommended_intake={
            "maintenance": 2557.5,
            "weight_loss": 2046.0,
            "weight_gain": 3069.0,
        },
        formulas_used=["mifflin"],
        notes=[],
    )
    captured: dict[str, object] = {}

    async def _fake_legacy_handler(
        received: app_main._legacy_module.BMRRequest,
    ) -> app_main._legacy_module.BMRResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(resolve_legacy_app(), "api_premium_bmr", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_premium_bmr(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_bmr_wrapper_delegates_inside_route_family_ci_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_module = resolve_legacy_app()
    req = legacy_module.BMRRequestLegacy(
        weight_kg=70,
        height_cm=175,
        age=35,
        sex="male",
        activity="moderate",
    )
    expected = legacy_module.BMRResponse(
        bmr={"mifflin": 1650.0},
        tdee={"mifflin": 2557.5},
        activity_level="moderate",
        recommended_intake={
            "maintenance": 2557.5,
            "weight_loss": 2046.0,
            "weight_gain": 3069.0,
        },
        formulas_used=["mifflin"],
        notes=[],
    )
    captured: dict[str, object] = {}

    async def _fake_legacy_handler(
        received: app_main._legacy_module.BMRRequestLegacy,
    ) -> app_main._legacy_module.BMRResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(resolve_legacy_app(), "premium_bmr_legacy", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.premium_bmr_legacy(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_targets_wrapper_delegates_inside_route_family_ci_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_module = resolve_legacy_app()
    req = legacy_module.WHOTargetsRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
    )
    expected = _who_targets_response()
    captured: dict[str, object] = {}

    async def _fake_legacy_handler(
        received: app_main._legacy_module.WHOTargetsRequest,
    ) -> app_main._legacy_module.WHOTargetsResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(
        resolve_legacy_app(),
        "premium_targets_legacy",
        _fake_legacy_handler,
    )

    response = asyncio.run(legacy_premium_nutrition.premium_targets_legacy(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_api_targets_wrapper_delegates_inside_route_family_ci_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "sex": "female",
        "age": 34,
        "height_cm": 168,
        "weight_kg": 62,
        "activity": "light",
    }
    expected = _who_targets_response()
    captured: dict[str, object] = {}

    async def _fake_legacy_handler(
        received: dict[str, object],
    ) -> app_main._legacy_module.WHOTargetsResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(resolve_legacy_app(), "api_who_targets", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_who_targets(payload))

    assert response is expected
    assert captured["request"] is payload


def test_legacy_premium_gaps_wrapper_delegates_inside_route_family_ci_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_module = resolve_legacy_app()
    req = legacy_module.NutrientGapsRequest(
        consumed_nutrients={"iron_mg": 10.0},
        user_profile=legacy_module.WHOTargetsRequest(
            sex="female",
            age=34,
            height_cm=168,
            weight_kg=62,
            activity="light",
        ),
    )
    expected = legacy_module.NutrientGapsResponse(
        gaps={"iron_mg": {"status": "low", "delta": -8.0}},
        food_recommendations=["lentils"],
        adherence_score=0.85,
    )
    captured: dict[str, object] = {}

    async def _fake_legacy_handler(
        received: app_main._legacy_module.NutrientGapsRequest,
    ) -> app_main._legacy_module.NutrientGapsResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(resolve_legacy_app(), "api_nutrient_gaps", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_nutrient_gaps(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_router_rejects_missing_api_key_symbol_inside_ci_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main._legacy_module, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Legacy premium nutrition API key dependency is unavailable",
    ):
        app_main._include_legacy_premium_nutrition_router_if_needed(FastAPI())


def test_static_route_family_rejects_unexpected_source_route() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(FastAPI(), _family_routers(include_unexpected=True))


def test_static_route_family_rejects_missing_source_member() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(FastAPI(), _family_routers(omit=frozenset({"/api/v1/static-family/b"})))


def test_static_route_family_rejects_source_combined_methods() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not define the expected route family",
    ):
        _ensure(
            FastAPI(),
            _family_routers(combined_methods_path="/api/v1/static-family/a"),
        )


def test_static_route_family_rejects_source_visibility_drift() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not preserve OpenAPI visibility",
    ):
        _ensure(
            FastAPI(),
            _family_routers(include_overrides={"/api/v1/static-family/a": False}),
        )


def test_static_route_family_rejects_source_429_drift() -> None:
    with pytest.raises(
        RuntimeError,
        match="Static family router does not preserve 429 response metadata",
    ):
        _ensure(FastAPI(), _family_routers(include_429=False))


def test_static_route_family_rejects_partial_existing_family() -> None:
    app = FastAPI()
    route_a, _route_b = _family_routers()
    app.include_router(route_a, dependencies=[Depends(_api_key_dependency)])

    with pytest.raises(
        RuntimeError,
        match="Partial static family route registration detected",
    ):
        _ensure(app, _family_routers())


def test_static_route_family_rejects_existing_foreign_handlers() -> None:
    app = FastAPI()

    for member in _MEMBERS:

        async def _foreign_handler(path: str = member.path) -> dict[str, str]:
            return {"path": path}

        dependencies = [Depends(_api_key_dependency)]
        if member.path.endswith("/b"):
            dependencies.append(Depends(_member_dependency))
        app.add_api_route(
            member.path,
            _foreign_handler,
            methods=[member.method],
            include_in_schema=member.include_in_schema,
            responses={429: {"description": "rate limit"}},
            dependencies=dependencies,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different static family handler",
    ):
        _ensure(app, _family_routers())


def test_static_route_family_rejects_existing_missing_required_dependency() -> None:
    app = FastAPI()
    route_a, route_b = _family_routers()
    app.include_router(route_a)
    app.include_router(route_b)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve static family required dependency",
    ):
        _ensure(app, _family_routers())


def test_dependency_detection_walks_nested_dependencies() -> None:
    app = FastAPI()

    async def _outer_dependency(
        _guard: str = Depends(_api_key_dependency),
    ) -> None:
        return None

    async def _nested_probe() -> dict[str, str]:
        return {"status": "nested"}

    app.add_api_route(
        "/api/v1/static-family/nested",
        _nested_probe,
        methods=["GET"],
        dependencies=[Depends(_outer_dependency)],
    )
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/static-family/nested"
    )

    assert route_has_dependency_call(route, _api_key_dependency)


def test_callable_matcher_uses_module_and_qualname_after_identity() -> None:
    async def _expected() -> None:
        return None

    async def _equivalent() -> None:
        return None

    _equivalent.__module__ = _expected.__module__
    _equivalent.__qualname__ = _expected.__qualname__

    assert same_callable_by_module_and_qualname(_expected, _expected)
    assert same_callable_by_module_and_qualname(_equivalent, _expected)
    assert not same_callable_by_module_and_qualname(None, _expected)


def test_business_bootstrap_noops_when_feature_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as app_main

    monkeypatch.delenv("BUSINESS_MODULE_ENABLED", raising=False)
    app = FastAPI()

    app_main._include_business_router_if_enabled(app)

    assert not any(
        str(getattr(route, "path", "")).startswith("/api/v1/business") for route in app.routes
    )


def test_business_analyze_direct_call_rejects_disabled_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.business import BusinessAnalysisRequest, analyze_business_code

    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "false")
    request = BusinessAnalysisRequest(code="def test(): pass", test_name="disabled")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(analyze_business_code(request, "placeholder"))

    assert exc_info.value.status_code == 503


def test_business_status_route_reports_request_time_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.business import router as business_router

    app = FastAPI()
    app.include_router(business_router)
    client = TestClient(app)

    try:
        monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")
        enabled_response = client.get("/api/v1/business/status")
        assert enabled_response.status_code == 200
        assert enabled_response.json() == {
            "enabled": True,
            "module": "business_analysis",
        }

        monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "false")
        disabled_response = client.get("/api/v1/business/status")
        assert disabled_response.status_code == 200
        assert disabled_response.json() == {
            "enabled": False,
            "module": "business_analysis",
        }
    finally:
        client.close()

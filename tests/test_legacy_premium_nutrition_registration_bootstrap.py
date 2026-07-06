from __future__ import annotations

import asyncio
import importlib
from collections import Counter
from collections.abc import Callable

import pytest
from fastapi import Depends, FastAPI

import app.main as app_main
from app.bootstrap.route_family import route_has_dependency_call
from app.routers import legacy_premium_nutrition
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_methods,
    route_path,
)

_EXPECTED_ROUTE_SPECS = app_main._LEGACY_PREMIUM_NUTRITION_ROUTE_SPECS
_EXPECTED_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
}
_EXPECTED_ROUTE_PATHS = {path for path, _method in _EXPECTED_ROUTE_KEYS}
_EXPECTED_ENDPOINT_MODULE = "app.routers.legacy_premium_nutrition"
_EXPECTED_ENDPOINTS = {
    ("/api/v1/premium/plate", "POST"): "api_premium_plate",
    ("/api/v1/premium/bmr", "POST"): "api_premium_bmr",
    ("/premium_bmr", "POST"): "premium_bmr_legacy",
    ("/api/v1/premium/targets", "POST"): "api_who_targets",
    ("/premium_targets", "POST"): "premium_targets_legacy",
    ("/api/v1/premium/gaps", "POST"): "api_nutrient_gaps",
}
_RESPONSE_MODELS = {
    ("/api/v1/premium/plate", "POST"): app_main._legacy_module.PlateResponse,
    ("/api/v1/premium/bmr", "POST"): app_main._legacy_module.BMRResponse,
    ("/premium_bmr", "POST"): app_main._legacy_module.BMRResponse,
    ("/api/v1/premium/targets", "POST"): app_main._legacy_module.WHOTargetsResponse,
    ("/premium_targets", "POST"): app_main._legacy_module.WHOTargetsResponse,
    ("/api/v1/premium/gaps", "POST"): app_main._legacy_module.NutrientGapsResponse,
}
_DEPRECATED_ROUTES = {
    ("/api/v1/premium/plate", "POST"),
    ("/api/v1/premium/targets", "POST"),
}
_API_KEY_PROTECTED_ROUTES = _EXPECTED_ROUTE_KEYS - {("/premium_bmr", "POST")}
_PUBLIC_LEGACY_EXCEPTION = ("/premium_bmr", "POST")


def _premium_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_ROUTE_PATHS
    ]


def _registered_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _premium_routes(target_app):
        for method in route_methods(route):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _premium_route(target_app: FastAPI, path: str, method: str) -> object:
    matches = [
        route
        for route in _premium_routes(target_app)
        if route_path(route) == path and method in route_methods(route)
    ]
    route_summaries = [
        f"{route_path(route)}:{sorted(route_methods(route))}:{route_endpoint(route).__module__}"
        for route in matches
    ]
    assert len(matches) == 1, (
        f"expected exactly one legacy premium nutrition route for {method} {path}; "
        f"found {len(matches)}: {route_summaries}"
    )
    return matches[0]


def _source_route(path: str, method: str) -> object:
    for route in app_main.legacy_premium_nutrition_router.routes:
        if not is_api_route_candidate(route):
            continue
        if str(route.path) == path and method in (route.methods or set()):
            return route
    raise AssertionError(f"missing source route: {method} {path}")


def _clone_endpoint_with_matching_identity(
    source_endpoint: Callable[..., object],
    dependency: Callable[..., object] | None,
) -> Callable[..., object]:
    if dependency is None:

        async def _endpoint_without_dependency() -> dict[str, str]:
            return {"status": "stub"}

        endpoint = _endpoint_without_dependency
    else:

        async def _endpoint_with_dependency(
            _dependency_result: object = Depends(dependency),
        ) -> dict[str, str]:
            return {"status": "stub"}

        endpoint = _endpoint_with_dependency

    endpoint.__module__ = source_endpoint.__module__
    endpoint.__name__ = source_endpoint.__name__
    endpoint.__qualname__ = source_endpoint.__qualname__
    return endpoint


def _assert_premium_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    present_order: list[tuple[str, str]] = []
    for route in _premium_routes(target_app):
        key_methods = route_methods(route) & {method for _path, method in _EXPECTED_ROUTE_KEYS}
        for method in sorted(key_methods):
            key = (route_path(route), method)
            if key in _EXPECTED_ROUTE_KEYS:
                present_order.append(key)
    assert tuple(present_order) == tuple(
        (path, method) for path, method, _include_in_schema in _EXPECTED_ROUTE_SPECS
    )

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _premium_route(target_app, path, method)
        key = (path, method)
        assert route_include_in_schema(route) is include_in_schema
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == _EXPECTED_ENDPOINT_MODULE
        assert getattr(endpoint, "__name__", None) == _EXPECTED_ENDPOINTS[key]
        assert route.response_model is _RESPONSE_MODELS[key]
        assert bool(route.deprecated) is (key in _DEPRECATED_ROUTES)
        if key in _API_KEY_PROTECTED_ROUTES:
            assert route_has_dependency_call(route, app_main._legacy_module._get_api_key_dynamic)
        else:
            assert key == _PUBLIC_LEGACY_EXCEPTION
            assert not route_has_dependency_call(
                route, app_main._legacy_module._get_api_key_dynamic
            )


def test_empty_app_registers_all_legacy_premium_nutrition_routes_once() -> None:
    target_app = FastAPI()

    app_main._include_legacy_premium_nutrition_router_if_needed(target_app)

    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())


def test_bootstrapped_app_registers_all_legacy_premium_nutrition_routes_once() -> None:
    _assert_premium_routes_registered_once(app_main.app)


def test_legacy_premium_nutrition_registration_is_idempotent() -> None:
    target_app = FastAPI()

    app_main._include_legacy_premium_nutrition_router_if_needed(target_app)
    app_main._include_legacy_premium_nutrition_router_if_needed(target_app)

    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())


def test_legacy_premium_nutrition_route_members_encode_api_key_exception() -> None:
    members = {
        (member.path, member.method): member
        for member in app_main._legacy_premium_nutrition_route_members(
            app_main._legacy_module._get_api_key_dynamic
        )
    }

    assert set(members) == _EXPECTED_ROUTE_KEYS
    for key, member in members.items():
        if key == _PUBLIC_LEGACY_EXCEPTION:
            assert member.required_dependencies == ()
        else:
            assert member.required_dependencies == (app_main._legacy_module._get_api_key_dynamic,)


def _who_targets_response() -> app_main._legacy_module.WHOTargetsResponse:
    return app_main._legacy_module.WHOTargetsResponse(
        kcal_daily=1900,
        macros={"protein_g": 95, "fat_g": 63, "carbs_g": 238, "fiber_g": 28},
        water_ml=2200,
        priority_micros={"iron_mg": 18.0},
        activity_weekly={"minutes": 150},
        calculation_date="2026-07-06",
        warnings=[],
        ui_labels=app_main._legacy_module.build_who_targets_ui_labels("en"),
    )


def _runtime_legacy_module() -> object:
    return importlib.import_module("legacy_app")


def test_legacy_premium_plate_wrapper_delegates_to_legacy_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = app_main._legacy_module.PlateRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
        goal="maintain",
    )
    expected = app_main._legacy_module.PlateResponse(
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

    monkeypatch.setattr(_runtime_legacy_module(), "api_premium_plate", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_premium_plate(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_api_bmr_wrapper_delegates_to_legacy_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = app_main._legacy_module.BMRRequest(
        weight_kg=70,
        height_cm=175,
        age=35,
        sex="male",
        activity="moderate",
    )
    expected = app_main._legacy_module.BMRResponse(
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

    monkeypatch.setattr(_runtime_legacy_module(), "api_premium_bmr", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_premium_bmr(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_bmr_wrapper_delegates_to_legacy_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = app_main._legacy_module.BMRRequestLegacy(
        weight_kg=70,
        height_cm=175,
        age=35,
        sex="male",
        activity="moderate",
    )
    expected = app_main._legacy_module.BMRResponse(
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

    monkeypatch.setattr(_runtime_legacy_module(), "premium_bmr_legacy", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.premium_bmr_legacy(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_targets_wrapper_delegates_to_legacy_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = app_main._legacy_module.WHOTargetsRequest(
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
        _runtime_legacy_module(),
        "premium_targets_legacy",
        _fake_legacy_handler,
    )

    response = asyncio.run(legacy_premium_nutrition.premium_targets_legacy(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_api_targets_wrapper_delegates_to_legacy_app(
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

    monkeypatch.setattr(_runtime_legacy_module(), "api_who_targets", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_who_targets(payload))

    assert response is expected
    assert captured["request"] is payload


def test_legacy_premium_gaps_wrapper_delegates_to_legacy_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = app_main._legacy_module.NutrientGapsRequest(
        consumed_nutrients={"iron_mg": 10.0},
        user_profile=app_main._legacy_module.WHOTargetsRequest(
            sex="female",
            age=34,
            height_cm=168,
            weight_kg=62,
            activity="light",
        ),
    )
    expected = app_main._legacy_module.NutrientGapsResponse(
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

    monkeypatch.setattr(_runtime_legacy_module(), "api_nutrient_gaps", _fake_legacy_handler)

    response = asyncio.run(legacy_premium_nutrition.api_nutrient_gaps(req))

    assert response is expected
    assert captured["request"] is req


def test_legacy_premium_nutrition_registration_rejects_missing_api_key_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main._legacy_module, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Legacy premium nutrition API key dependency is unavailable",
    ):
        app_main._include_legacy_premium_nutrition_router_if_needed(FastAPI())


def test_legacy_premium_nutrition_source_routes_preserve_metadata() -> None:
    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        route = _source_route(path, method)
        key = (path, method)

        assert route_include_in_schema(route) is include_in_schema
        assert route.response_model is _RESPONSE_MODELS[key]
        assert bool(route.deprecated) is (key in _DEPRECATED_ROUTES)
        if key in _API_KEY_PROTECTED_ROUTES:
            assert route_has_dependency_call(route, app_main._legacy_module._get_api_key_dynamic)
        else:
            assert key == _PUBLIC_LEGACY_EXCEPTION
            assert not route_has_dependency_call(
                route, app_main._legacy_module._get_api_key_dynamic
            )


def test_legacy_premium_nutrition_public_openapi_paths_remain_hidden() -> None:
    schema = app_main.app.openapi()
    paths = {str(path) for path in schema.get("paths", {})}

    leaked_paths = sorted(path for path in paths if path in _EXPECTED_ROUTE_PATHS)
    assert leaked_paths == []


def test_legacy_premium_nutrition_registration_does_not_absorb_weekly_alias() -> None:
    target_app = FastAPI()

    app_main._include_legacy_premium_nutrition_router_if_needed(target_app)

    registered_paths = {route_path(route) for route in _premium_routes(target_app)}
    assert "/api/v1/premium/plan/week" not in registered_paths
    assert "/api/v1/premium/plan/week-flexible" not in registered_paths


def test_legacy_premium_nutrition_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _partial_premium_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_premium_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Partial legacy premium nutrition route registration detected",
    ):
        app_main._include_legacy_premium_nutrition_router_if_needed(target_app)


def test_legacy_premium_nutrition_registration_rejects_duplicate_method_path() -> None:
    target_app = FastAPI()
    app_main._include_legacy_premium_nutrition_router_if_needed(target_app)
    path, method, include_in_schema = _EXPECTED_ROUTE_SPECS[0]

    async def _duplicate_premium_route() -> dict[str, str]:
        return {"status": "duplicate"}

    target_app.add_api_route(
        path,
        _duplicate_premium_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different legacy premium nutrition handler",
    ):
        app_main._include_legacy_premium_nutrition_router_if_needed(target_app)


def test_legacy_premium_nutrition_registration_rejects_foreign_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:

        async def _foreign_premium_route(current_route_path: str = path) -> dict[str, str]:
            return {"path": current_route_path}

        target_app.add_api_route(
            path,
            _foreign_premium_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different legacy premium nutrition handler",
    ):
        app_main._include_legacy_premium_nutrition_router_if_needed(target_app)


def test_legacy_premium_nutrition_registration_rejects_missing_api_key_dependency() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        source = _source_route(path, method)
        endpoint = _clone_endpoint_with_matching_identity(route_endpoint(source), None)
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve legacy premium nutrition required dependency",
    ):
        app_main._include_legacy_premium_nutrition_router_if_needed(target_app)


def test_legacy_premium_nutrition_registration_accepts_reloaded_canonical_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in _EXPECTED_ROUTE_SPECS:
        source = _source_route(path, method)
        key = (path, method)
        dependency = (
            None
            if key == _PUBLIC_LEGACY_EXCEPTION
            else app_main._legacy_module._get_api_key_dynamic
        )
        endpoint = _clone_endpoint_with_matching_identity(route_endpoint(source), dependency)
        dependencies = [] if dependency is None else [Depends(dependency)]
        target_app.add_api_route(
            path,
            endpoint,
            methods=[method],
            include_in_schema=include_in_schema,
            dependencies=dependencies,
        )

    app_main._include_legacy_premium_nutrition_router_if_needed(target_app)

    counts = _registered_route_counts(target_app)
    assert set(counts) == _EXPECTED_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

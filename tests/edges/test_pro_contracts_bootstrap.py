"""Critical PRO route bootstrap registration contract tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Match, Mount, Route
from starlette.types import Scope

import app.bootstrap.pro_contracts as pro_contracts_bootstrap
from app.bootstrap.pro_contracts import register_pro_contract_routes
from app.bootstrap.route_family import route_has_dependency_call
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_matches_path_method,
    route_methods,
    route_path,
)
from app.middleware.api_tiers import TEST_KEY_PRO, require_pro_tier
from app.schemas.bmr import BMRRequest, BMRResponse
from app.schemas.premium_contracts import (
    NutrientGapsRequest,
    NutrientGapsResponse,
    PlateResponse,
    WHOTargetsResponse,
)

_EXPECTED_PATHS = (
    "/api/v1/pro/nutrition/targets",
    "/api/v1/pro/nutrition/plate",
    "/api/v1/pro/nutrition/bmr",
    "/api/v1/pro/nutrition/gaps",
)


def _post_route_count(routes: list[object], path: str) -> int:
    return sum(
        1
        for route in iter_effective_route_candidates(routes)
        if route_matches_path_method(route, path, "POST")
    )


def _pro_family_routes(target_app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if is_api_route_candidate(route) and route_path(route) in _EXPECTED_PATHS
    ]


def _exact_destination_app(
    dependency: Callable[..., object] = require_pro_tier,
) -> FastAPI:
    from app.routers.pro_nutrition_contracts import (
        pro_nutrition_bmr,
        pro_nutrition_gaps,
        pro_nutrition_plate,
        pro_nutrition_targets,
    )

    target_app = FastAPI()
    for path, endpoint, response_model in (
        (_EXPECTED_PATHS[0], pro_nutrition_targets, WHOTargetsResponse),
        (_EXPECTED_PATHS[1], pro_nutrition_plate, PlateResponse),
        (_EXPECTED_PATHS[2], pro_nutrition_bmr, BMRResponse),
        (_EXPECTED_PATHS[3], pro_nutrition_gaps, NutrientGapsResponse),
    ):
        target_app.add_api_route(
            path,
            endpoint,
            methods=["POST"],
            dependencies=[Depends(dependency)],
            response_model=response_model,
        )
    return target_app


def test_register_pro_contract_routes_idempotent(client: TestClient) -> None:
    """Test that calling register_pro_contract_routes twice does not duplicate routes."""
    import app

    # First call (should register)
    register_pro_contract_routes(app.app)

    # Verify routes exist
    paths = {route_path(route) for route in iter_effective_route_candidates(app.app.routes)}
    assert set(_EXPECTED_PATHS) <= paths

    # Count routes before second call
    targets_count_before = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/targets")
    plate_count_before = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/plate")
    bmr_count_before = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/bmr")
    gaps_count_before = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/gaps")

    # Second call (should be no-op)
    register_pro_contract_routes(app.app)

    # Count routes after second call
    targets_count_after = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/targets")
    plate_count_after = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/plate")
    bmr_count_after = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/bmr")
    gaps_count_after = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/gaps")

    # No duplication
    assert targets_count_after == targets_count_before == 1
    assert plate_count_after == plate_count_before == 1
    assert bmr_count_after == bmr_count_before == 1
    assert gaps_count_after == gaps_count_before == 1

    family = _pro_family_routes(app.app)
    assert [route_path(route) for route in family] == list(_EXPECTED_PATHS)
    assert all(route_methods(route) == {"POST"} for route in family)
    assert all(route_include_in_schema(route) is True for route in family)
    assert all(route_has_dependency_call(route, require_pro_tier) for route in family)


def test_register_pro_contract_routes_partial_state_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that partial state (only one route registered) raises RuntimeError."""
    app = FastAPI()

    # Manually register only targets route (simulate partial state)
    from app.routers.pro_nutrition_contracts import router as pro_contracts_router

    # Create a fake route that looks like targets but not plate
    from fastapi.routing import APIRoute
    from app.middleware.api_tiers import require_pro_tier
    from app.routers.pro_nutrition_contracts import pro_nutrition_targets
    from app.schemas.premium_contracts import WHOTargetsResponse

    fake_targets_route = APIRoute(
        path="/api/v1/pro/nutrition/targets",
        endpoint=pro_nutrition_targets,
        methods=["POST"],
        dependencies=[Depends(require_pro_tier)],
        response_model=WHOTargetsResponse,
    )
    app.routes.append(fake_targets_route)

    # Now try to register (should detect partial state and raise)
    with pytest.raises(RuntimeError, match="Partial PRO contract routes detected"):
        register_pro_contract_routes(app)


def test_register_pro_contract_routes_rejects_existing_handlers_without_pro_dependency() -> None:
    """Existing direct handlers must not bypass the router-level PRO dependency."""
    app = FastAPI()

    from app.routers.pro_nutrition_contracts import (
        pro_nutrition_plate,
        pro_nutrition_targets,
    )

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


def test_register_pro_contract_routes_rejects_counterfeit_pro_dependency_identity() -> None:
    async def _counterfeit_pro_tier() -> str:
        return TEST_KEY_PRO

    _counterfeit_pro_tier.__module__ = require_pro_tier.__module__
    _counterfeit_pro_tier.__name__ = require_pro_tier.__name__
    _counterfeit_pro_tier.__qualname__ = require_pro_tier.__qualname__
    target_app = _exact_destination_app(_counterfeit_pro_tier)

    with pytest.raises(RuntimeError, match="PRO contract required dependency"):
        register_pro_contract_routes(target_app)


def test_register_pro_contract_routes_accepts_original_route_response_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_app = _exact_destination_app()
    bmr_path = _EXPECTED_PATHS[2]
    bmr_route = next(
        route for route in _pro_family_routes(target_app) if route_path(route) == bmr_path
    )
    original_bmr_route = next(
        route
        for route in _pro_family_routes(_exact_destination_app())
        if route_path(route) == bmr_path
    )
    monkeypatch.setattr(bmr_route, "response_model", None)
    monkeypatch.setattr(
        bmr_route,
        "original_route",
        original_bmr_route,
        raising=False,
    )

    register_pro_contract_routes(target_app)

    assert [route_path(route) for route in _pro_family_routes(target_app)] == list(_EXPECTED_PATHS)


def test_register_pro_contract_routes_ignores_non_route_carriers() -> None:
    target_app = _exact_destination_app()
    sentinel = object()
    target_app.router.routes.insert(0, sentinel)

    register_pro_contract_routes(target_app)

    assert sentinel in target_app.router.routes


def test_first_full_match_owner_returns_raw_route_without_matching_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RawFullMatchRoute:
        def matches(self, scope: Scope) -> tuple[Match, Scope]:
            return Match.FULL, scope

    raw_route = _RawFullMatchRoute()
    target_app = FastAPI()
    target_app.router.routes.clear()
    target_app.router.routes.append(raw_route)

    def _candidate_without_matcher(_routes: object) -> tuple[object, ...]:
        return (object(),)

    monkeypatch.setattr(
        pro_contracts_bootstrap,
        "iter_effective_route_candidates",
        _candidate_without_matcher,
    )

    assert (
        pro_contracts_bootstrap._first_full_match_owner(target_app, _EXPECTED_PATHS[0]) is raw_route
    )


@pytest.mark.parametrize("path", _EXPECTED_PATHS)
def test_register_pro_contract_routes_rejects_plain_starlette_shadow_without_mutation(
    path: str,
) -> None:
    target_app = FastAPI()

    async def _shadow(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "unguarded-shadow"})

    shadow_route = Route(path, _shadow, methods=["POST"])
    target_app.router.routes.append(shadow_route)
    routes_before = tuple(target_app.routes)

    with pytest.raises(RuntimeError, match="Non-API route shadows expected PRO contract path"):
        register_pro_contract_routes(target_app)

    assert tuple(target_app.routes) == routes_before
    assert shadow_route in target_app.routes
    assert not any(
        is_api_route_candidate(route) and route_path(route) in _EXPECTED_PATHS
        for route in target_app.routes
    )


def test_register_pro_contract_routes_rejects_prefix_mount_before_mutation() -> None:
    target_app = FastAPI()

    async def _shadow(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "mounted-shadow"})

    shadow_mount = Mount(
        "/api/v1/pro/nutrition",
        routes=[Route("/{rest:path}", _shadow, methods=["POST"])],
    )
    target_app.router.routes.append(shadow_mount)
    routes_before = tuple(target_app.routes)

    with pytest.raises(RuntimeError, match="Non-API route shadows expected PRO contract path"):
        register_pro_contract_routes(target_app)

    assert tuple(target_app.routes) == routes_before
    assert shadow_mount in target_app.routes
    assert not any(
        is_api_route_candidate(route) and route_path(route) in _EXPECTED_PATHS
        for route in target_app.routes
    )


def test_register_pro_contract_routes_rejects_dynamic_post_catchall_before_mutation() -> None:
    target_app = FastAPI()

    async def _shadow(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "dynamic-shadow"})

    shadow_route = Route(
        "/api/v1/pro/nutrition/{rest:path}",
        _shadow,
        methods=["POST"],
    )
    target_app.router.routes.append(shadow_route)
    routes_before = tuple(target_app.routes)

    with pytest.raises(RuntimeError, match="Non-API route shadows expected PRO contract path"):
        register_pro_contract_routes(target_app)

    assert tuple(target_app.routes) == routes_before
    assert shadow_route in target_app.routes
    assert not any(
        is_api_route_candidate(route) and route_path(route) in _EXPECTED_PATHS
        for route in target_app.routes
    )


def test_register_pro_contract_routes_rejects_dynamic_api_route_shadow() -> None:
    target_app = FastAPI()

    async def _shadow(rest: str) -> dict[str, str]:
        return {"status": rest}

    target_app.add_api_route(
        "/api/v1/pro/nutrition/{rest:path}",
        _shadow,
        methods=["POST"],
        dependencies=[Depends(require_pro_tier)],
        response_model=dict[str, str],
    )

    with pytest.raises(RuntimeError, match="not the exact PRO contract path owner"):
        register_pro_contract_routes(target_app)


def test_register_pro_contract_routes_rejects_trailing_non_api_duplicate() -> None:
    target_app = _exact_destination_app()

    async def _shadow(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "trailing-shadow"})

    target_app.router.routes.append(Route(_EXPECTED_PATHS[2], _shadow, methods=["POST"]))

    with pytest.raises(RuntimeError, match="Non-API route shadows expected PRO contract path"):
        register_pro_contract_routes(target_app)


@pytest.mark.parametrize(
    ("field_name", "replacement", "message"),
    [
        ("methods", {"GET"}, "exact POST method ownership"),
        ("response_model", object(), "response model"),
        ("include_in_schema", False, "OpenAPI visibility"),
    ],
)
def test_register_pro_contract_routes_rejects_destination_metadata_drift(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    replacement: object,
    message: str,
) -> None:
    target_app = _exact_destination_app()
    route = _pro_family_routes(target_app)[2]
    monkeypatch.setattr(route, field_name, replacement)

    with pytest.raises(RuntimeError, match=message):
        register_pro_contract_routes(target_app)


def test_register_pro_contract_routes_rejects_destination_foreign_handler() -> None:
    target_app = FastAPI()

    async def _foreign_bmr() -> dict[str, str]:
        return {"status": "foreign"}

    target_app.add_api_route(
        _EXPECTED_PATHS[2],
        _foreign_bmr,
        methods=["POST"],
        dependencies=[Depends(require_pro_tier)],
        response_model=BMRResponse,
    )

    with pytest.raises(RuntimeError, match="different PRO contract handler"):
        register_pro_contract_routes(target_app)


def test_register_pro_contract_routes_rejects_destination_duplicate() -> None:
    target_app = _exact_destination_app()
    bmr_route = _pro_family_routes(target_app)[2]
    target_app.add_api_route(
        _EXPECTED_PATHS[2],
        route_endpoint(bmr_route),
        methods=["POST"],
        dependencies=[Depends(require_pro_tier)],
        response_model=BMRResponse,
    )

    with pytest.raises(RuntimeError, match=f"Duplicate {_EXPECTED_PATHS[2]}"):
        register_pro_contract_routes(target_app)


def test_register_pro_contract_routes_rejects_destination_order_drift() -> None:
    target_app = _exact_destination_app()
    target_app.routes[-1], target_app.routes[-2] = target_app.routes[-2], target_app.routes[-1]

    with pytest.raises(RuntimeError, match="route order"):
        register_pro_contract_routes(target_app)


def test_register_pro_contract_routes_rejects_source_missing_extra_and_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.pro_nutrition_contracts import router

    original_routes = list(router.routes)
    monkeypatch.setattr(router, "routes", original_routes[:-1])
    with pytest.raises(RuntimeError, match="expected route family"):
        register_pro_contract_routes(FastAPI())

    extra_router = APIRouter(prefix="/api/v1/pro/nutrition")

    @extra_router.post("/unexpected")
    async def _unexpected() -> dict[str, str]:
        return {"status": "unexpected"}

    monkeypatch.setattr(router, "routes", [*original_routes, *extra_router.routes])
    with pytest.raises(RuntimeError, match="expected route family"):
        register_pro_contract_routes(FastAPI())

    monkeypatch.setattr(router, "routes", [*original_routes, original_routes[0]])
    with pytest.raises(RuntimeError, match="expected route family"):
        register_pro_contract_routes(FastAPI())


def test_register_pro_contract_routes_rejects_source_endpoint_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.pro_nutrition_contracts import router

    monkeypatch.setattr(router.routes[2], "endpoint", object())

    with pytest.raises(RuntimeError, match="expected route family"):
        register_pro_contract_routes(FastAPI())


def test_register_pro_contract_routes_rejects_source_order_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers.pro_nutrition_contracts import router

    original_routes = list(router.routes)
    monkeypatch.setattr(
        router,
        "routes",
        [original_routes[1], original_routes[0], *original_routes[2:]],
    )

    with pytest.raises(RuntimeError, match="expected route family"):
        register_pro_contract_routes(FastAPI())


def test_register_pro_contract_routes_rejects_partial_existing_first_match_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_app = _exact_destination_app()

    def _partial_owners(_app: FastAPI, _specs: tuple[object, ...]) -> tuple[bool, ...]:
        return (True, True, False, True)

    monkeypatch.setattr(
        pro_contracts_bootstrap,
        "_validate_first_full_match_owners",
        _partial_owners,
    )

    with pytest.raises(RuntimeError, match="Partial PRO contract first-match ownership"):
        register_pro_contract_routes(target_app)


def test_register_pro_contract_routes_rejects_first_match_without_family_census(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _partial_owners(_app: FastAPI, _specs: tuple[object, ...]) -> tuple[bool, ...]:
        return (True, False, False, False)

    monkeypatch.setattr(
        pro_contracts_bootstrap,
        "_validate_first_full_match_owners",
        _partial_owners,
    )

    with pytest.raises(RuntimeError, match="Partial PRO contract first-match ownership"):
        register_pro_contract_routes(FastAPI())


def test_register_pro_contract_routes_rejects_partial_ownership_after_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_results: list[tuple[bool, ...]] = [
        (False, False, False, False),
        (True, True, True, False),
    ]

    def _owners(_app: FastAPI, _specs: tuple[object, ...]) -> tuple[bool, ...]:
        return owner_results.pop(0) if len(owner_results) > 1 else owner_results[0]

    monkeypatch.setattr(
        pro_contracts_bootstrap,
        "_validate_first_full_match_owners",
        _owners,
    )

    with pytest.raises(
        RuntimeError,
        match="Partial PRO contract first-match ownership detected after registration",
    ):
        register_pro_contract_routes(FastAPI())


@pytest.mark.parametrize(
    ("field_name", "replacement", "message"),
    [
        ("methods", {"GET"}, "exact POST method ownership"),
        ("response_model", object(), "response model"),
        ("include_in_schema", False, "OpenAPI visibility"),
    ],
)
def test_register_pro_contract_routes_rejects_source_metadata_drift(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    replacement: object,
    message: str,
) -> None:
    from app.routers.pro_nutrition_contracts import router

    route = router.routes[2]
    monkeypatch.setattr(route, field_name, replacement)

    with pytest.raises(RuntimeError, match=message):
        register_pro_contract_routes(FastAPI())


def test_pro_bmr_handler_delegates_to_canonical_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import pro_nutrition_contracts

    request = BMRRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
    )
    expected = BMRResponse(
        bmr={"mifflin": 1390.0},
        tdee={"mifflin": 1911.25},
        activity_level="Light activity",
        recommended_intake={
            "maintenance": 1911.25,
            "weight_loss": 1529.0,
            "weight_gain": 2293.5,
        },
        formulas_used=["mifflin"],
        notes=[],
    )
    captured: dict[str, object] = {}

    async def _fake_service(received: BMRRequest) -> BMRResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(pro_nutrition_contracts, "calculate_bmr_response", _fake_service)

    response = asyncio.run(pro_nutrition_contracts.pro_nutrition_bmr(request))

    assert response is expected
    assert captured["request"] is request


def test_pro_gaps_handler_delegates_to_canonical_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import pro_nutrition_contracts
    from app.schemas.premium_contracts import WHOTargetsRequest

    request = NutrientGapsRequest(
        consumed_nutrients={"iron_mg": 1.0},
        user_profile=WHOTargetsRequest(
            sex="female",
            age=34,
            height_cm=168,
            weight_kg=62,
            activity="light",
        ),
    )
    expected = NutrientGapsResponse(
        gaps={"iron_mg": {"priority": "high"}},
        food_recommendations=["lentils"],
        adherence_score=0.0,
    )
    captured: dict[str, object] = {}

    def _fake_service(received: NutrientGapsRequest) -> NutrientGapsResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(
        pro_nutrition_contracts,
        "analyze_nutrient_gaps_response",
        _fake_service,
    )

    response = asyncio.run(pro_nutrition_contracts.pro_nutrition_gaps(request))

    assert response is expected
    assert captured["request"] is request


def test_pro_plate_handler_delegates_to_canonical_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The canonical route owns no compatibility-layer call path."""

    from app.routers import pro_nutrition_contracts
    from app.schemas.premium_contracts import PlateRequest, PlateResponse

    request = PlateRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
        goal="maintain",
    )
    expected = PlateResponse(
        kcal=1900,
        macros={"protein_g": 95, "fat_g": 63, "carbs_g": 238},
        portions={"protein_palm": 1.3},
        layout=[],
        meals=[],
    )
    captured: dict[str, object] = {}

    async def _fake_service(received: PlateRequest) -> PlateResponse:
        captured["request"] = received
        return expected

    monkeypatch.setattr(
        pro_nutrition_contracts,
        "generate_plate_response",
        _fake_service,
    )

    response = asyncio.run(pro_nutrition_contracts.pro_nutrition_plate(request))

    assert response is expected
    assert captured["request"] is request


@pytest.mark.parametrize("field_name", ["height_cm", "weight_kg"])
def test_pro_plate_rejects_raw_non_finite_measurement_with_exact_422(
    client: TestClient,
    field_name: str,
) -> None:
    height_cm = "1e309" if field_name == "height_cm" else "168"
    weight_kg = "1e309" if field_name == "weight_kg" else "62"
    raw_payload = (
        '{"sex":"female","age":34,'
        f'"height_cm":{height_cm},"weight_kg":{weight_kg},'
        '"activity":"light","goal":"maintain"}'
    )

    response = client.post(
        "/api/v1/pro/nutrition/plate",
        content=raw_payload,
        headers={
            "X-API-Key": TEST_KEY_PRO,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert len(detail) == 1
    assert detail[0]["loc"] == ["body", field_name]
    assert detail[0]["type"] == "float_parsing"

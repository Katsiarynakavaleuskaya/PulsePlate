"""Critical PRO route bootstrap registration contract tests."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.pro_contracts import register_pro_contract_routes
from app.effective_routes import (
    iter_effective_route_candidates,
    route_matches_path_method,
    route_path,
)
from app.middleware.api_tiers import TEST_KEY_PRO


def _post_route_count(routes: list[object], path: str) -> int:
    return sum(
        1
        for route in iter_effective_route_candidates(routes)
        if route_matches_path_method(route, path, "POST")
    )


def test_register_pro_contract_routes_idempotent(client: TestClient) -> None:
    """Test that calling register_pro_contract_routes twice does not duplicate routes."""
    import app

    # First call (should register)
    register_pro_contract_routes(app.app)

    # Verify routes exist
    paths = {route_path(route) for route in iter_effective_route_candidates(app.app.routes)}
    assert "/api/v1/pro/nutrition/targets" in paths
    assert "/api/v1/pro/nutrition/plate" in paths

    # Count routes before second call
    targets_count_before = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/targets")
    plate_count_before = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/plate")

    # Second call (should be no-op)
    register_pro_contract_routes(app.app)

    # Count routes after second call
    targets_count_after = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/targets")
    plate_count_after = _post_route_count(app.app.routes, "/api/v1/pro/nutrition/plate")

    # No duplication
    assert targets_count_after == targets_count_before == 1
    assert plate_count_after == plate_count_before == 1


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

    fake_targets_route = APIRoute(
        path="/api/v1/pro/nutrition/targets",
        endpoint=pro_nutrition_targets,
        methods=["POST"],
        dependencies=[Depends(require_pro_tier)],
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

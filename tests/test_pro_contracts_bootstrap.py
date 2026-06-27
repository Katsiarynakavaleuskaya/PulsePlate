"""Tests for PRO contract routes bootstrap registration (idempotency, partial state detection)."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.pro_contracts import register_pro_contract_routes
from app.effective_routes import (
    iter_effective_route_candidates,
    route_matches_path_method,
    route_path,
)


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

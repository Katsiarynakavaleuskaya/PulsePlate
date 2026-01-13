"""Tests for PRO contract routes bootstrap registration (idempotency, partial state detection)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.pro_contracts import register_pro_contract_routes


def test_register_pro_contract_routes_idempotent(client: TestClient) -> None:
    """Test that calling register_pro_contract_routes twice does not duplicate routes."""
    import app

    # First call (should register)
    register_pro_contract_routes(app.app)

    # Verify routes exist
    paths = {r.path for r in app.app.routes if hasattr(r, "path")}
    assert "/api/v1/pro/nutrition/targets" in paths
    assert "/api/v1/pro/nutrition/plate" in paths

    # Count routes before second call
    targets_count_before = sum(
        1
        for r in app.app.routes
        if getattr(r, "path", None) == "/api/v1/pro/nutrition/targets"
        and "POST" in (getattr(r, "methods", None) or set())
    )
    plate_count_before = sum(
        1
        for r in app.app.routes
        if getattr(r, "path", None) == "/api/v1/pro/nutrition/plate"
        and "POST" in (getattr(r, "methods", None) or set())
    )

    # Second call (should be no-op)
    register_pro_contract_routes(app.app)

    # Count routes after second call
    targets_count_after = sum(
        1
        for r in app.app.routes
        if getattr(r, "path", None) == "/api/v1/pro/nutrition/targets"
        and "POST" in (getattr(r, "methods", None) or set())
    )
    plate_count_after = sum(
        1
        for r in app.app.routes
        if getattr(r, "path", None) == "/api/v1/pro/nutrition/plate"
        and "POST" in (getattr(r, "methods", None) or set())
    )

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
    from app.routers.pro_nutrition_contracts import pro_nutrition_targets

    fake_targets_route = APIRoute(
        path="/api/v1/pro/nutrition/targets",
        endpoint=pro_nutrition_targets,
        methods=["POST"],
    )
    app.routes.append(fake_targets_route)

    # Now try to register (should detect partial state and raise)
    with pytest.raises(RuntimeError, match="Partial PRO contract routes detected"):
        register_pro_contract_routes(app)

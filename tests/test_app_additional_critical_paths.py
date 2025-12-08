import importlib
import os
import sys
from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app


@pytest.mark.parametrize(
    "final_kcal, expected_kcal",
    [
        (800, 1200),  # below safety floor should be clamped
        (1200, 1200),  # at floor remains unchanged
        (1800, 1800),  # above floor remains unchanged
    ],
)
def test_calculate_heuristic_macros_enforces_1200_floor(
    final_kcal: int, expected_kcal: int
) -> None:
    """calculate_heuristic_macros must enforce a 1200 kcal minimum.

    This guards against generating VLCD macros for unsafe calorie targets.
    """

    weight_kg = 70.0
    prot_g, fat_g, carbs_g = app.calculate_heuristic_macros(final_kcal, weight_kg)

    # The function clamps the input to >= 1200 but rounding can lead to
    # total_kcal being off by 1 kcal. We assert both the clamped input
    # and that total_kcal stays within a small tolerance of the target.
    clamped_kcal = expected_kcal
    total_kcal = app._macros_to_kcal({"protein_g": prot_g, "fat_g": fat_g, "carbs_g": carbs_g})

    assert total_kcal is not None
    assert abs(total_kcal - clamped_kcal) <= 1


def test_generate_who_targets_response_backend_unavailable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_generate_who_targets_response returns fallback when backend missing.

    Covers allow_backend_fallback=True branch when build_nutrition_targets is not callable.
    """
    # Force backend to be unavailable by setting it to None
    monkeypatch.setattr(app._plate_deps, "build_nutrition_targets_fn", None)
    monkeypatch.setattr(app, "build_nutrition_targets", None)
    app.reset_targets_cache()

    req = app.WHOTargetsRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
    )

    # Testing private method directly because there's no public API endpoint
    # for this specific functionality. The private method is tested to ensure
    # proper fallback behavior when the backend is unavailable.
    resp = app._generate_who_targets_response(req, allow_backend_fallback=True)

    assert resp.kcal_daily > 0
    assert "protein_g" in resp.macros
    assert isinstance(resp.warnings, list)


def test_generate_who_targets_response_strict_backend_available() -> None:
    """When allow_backend_fallback=False and backend is available, we still get a valid response.

    In CI the backend is wired and callable, so this test asserts the strict
    no-fallback API behaves like the main WHO targets endpoint under normal conditions.
    """

    # Ensure we do NOT break the backend in this test: we exercise the normal path.
    req = app.WHOTargetsRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
    )

    # Testing private method directly because there's no public API endpoint
    # for this specific functionality. The private method is tested to ensure
    # proper behavior when the backend is available and fallback is disabled.
    resp = app._generate_who_targets_response(req, allow_backend_fallback=False)

    assert resp.kcal_daily > 0
    assert "protein_g" in resp.macros
    assert isinstance(resp.warnings, list)


def test_weekly_plan_pdf_endpoint_not_registered() -> None:
    """Weekly plan PDF endpoint returns 404 when the route is not registered.

    This test verifies that non-existent endpoints properly return 404.
    """
    client = TestClient(cast(ASGIApp, app.app))

    # Non-existent endpoint should return 404 when the route is not registered
    response = client.get("/api/v1/weekly-plan/pdf/123")

    assert response.status_code == 404


def test_bmi_pro_router_feature_flag_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    """BMI Pro router inclusion is controlled by FEATURE_BMI_PRO_ENABLED flag."""
    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "0")

    # Reload app module with feature flag disabled
    importlib.reload(app)

    # Ensure app instance exists
    assert hasattr(app, "app")
    assert app.app is not None
    client = TestClient(cast(ASGIApp, app.app))
    response = client.get("/api/v1/bmi-pro/status")

    assert response.status_code == 404

    # Restore environment to original state before final reload
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    # Restore app to original state
    importlib.reload(app)


def test_module_state_restored_after_feature_flag_test(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that app module can be reloaded to restore clean state.

    This test validates module reloading works correctly regardless of prior state.
    """
    # Deliberately dirty the module state first
    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "0")
    importlib.reload(app)

    # Now restore clean state
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)
    importlib.reload(app)

    # Verify app module is in expected state
    assert "app" in sys.modules
    assert hasattr(app, "app")
    assert app.app is not None

    # Verify API endpoints work correctly
    client = TestClient(cast(ASGIApp, app.app))
    response = client.get("/health")
    assert response.status_code == 200

    # Verify core functionality is intact
    weight_kg = 70.0
    prot_g, fat_g, carbs_g = app.calculate_heuristic_macros(1500, weight_kg)
    assert prot_g > 0
    assert fat_g > 0
    assert carbs_g > 0

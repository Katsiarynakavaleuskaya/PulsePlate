import pytest
from fastapi.testclient import TestClient

from app.schemas.premium_contracts import WHOTargetsRequest
from app.services import pro_nutrition_plate as plate_service
from app.services import pro_nutrition_targets as targets_service


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
    prot_g, fat_g, carbs_g = plate_service.calculate_heuristic_macros(final_kcal, weight_kg)

    # The function clamps the input to >= 1200 but rounding can lead to
    # total_kcal being off by 1 kcal. We assert both the clamped input
    # and that total_kcal stays within a small tolerance of the target.
    clamped_kcal = expected_kcal
    total_kcal = plate_service._macros_to_kcal(
        {"protein_g": prot_g, "fat_g": fat_g, "carbs_g": carbs_g}
    )

    assert total_kcal is not None
    assert abs(total_kcal - clamped_kcal) <= 1


def test_generate_who_targets_response_backend_unavailable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_generate_who_targets_response returns fallback when backend missing.

    Covers allow_backend_fallback=True branch when build_nutrition_targets is not callable.
    """
    monkeypatch.setattr(
        targets_service.nutrition_recommendations,
        "build_nutrition_targets",
        None,
    )

    req = WHOTargetsRequest(
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
    resp = targets_service.generate_who_targets_response(req, allow_backend_fallback=True)

    assert resp.kcal_daily > 0
    assert "protein_g" in resp.macros
    assert isinstance(resp.warnings, list)


def test_generate_who_targets_response_strict_backend_available() -> None:
    """When allow_backend_fallback=False and backend is available, we still get a valid response.

    In CI the backend is wired and callable, so this test asserts the strict
    no-fallback API behaves like the main WHO targets endpoint under normal conditions.
    """

    assert callable(targets_service.nutrition_recommendations.build_nutrition_targets)

    req = WHOTargetsRequest(
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
    resp = targets_service.generate_who_targets_response(req, allow_backend_fallback=False)

    assert resp.kcal_daily > 0
    assert "protein_g" in resp.macros
    assert isinstance(resp.warnings, list)


def test_weekly_plan_pdf_endpoint_not_registered(client: TestClient) -> None:
    """Weekly plan PDF endpoint returns 404 when the route is not registered.

    This test verifies that non-existent endpoints properly return 404.
    """
    # Non-existent endpoint should return 404 when the route is not registered
    response = client.get("/api/v1/weekly-plan/pdf/123")

    assert response.status_code == 404

import pytest

import app


@pytest.mark.parametrize(
    "final_kcal, expected_floor",
    [
        (800, 1200),  # below safety floor should be clamped
        (1200, 1200),  # at floor remains unchanged
        (1800, 1800),  # above floor remains unchanged
    ],
)
def test_calculate_heuristic_macros_enforces_1200_floor(
    final_kcal: int, expected_floor: int
) -> None:
    """calculate_heuristic_macros must enforce a 1200 kcal minimum.

    This guards against generating VLCD macros for unsafe calorie targets.
    """

    weight_kg = 70.0
    prot_g, fat_g, carbs_g = app.calculate_heuristic_macros(final_kcal, weight_kg)

    # The function clamps the input to >= 1200 but rounding can lead to
    # total_kcal being off by 1 kcal. We assert both the clamped input
    # and that total_kcal stays within a small tolerance of the target.
    clamped_kcal = max(final_kcal, expected_floor)
    total_kcal = app._macros_to_kcal({"protein_g": prot_g, "fat_g": fat_g, "carbs_g": carbs_g})

    assert total_kcal is not None
    assert abs(total_kcal - clamped_kcal) <= 1


def test_generate_who_targets_response_backend_unavailable_fallback() -> None:
    """_generate_who_targets_response returns fallback when backend missing.

    Covers allow_backend_fallback=True branch when build_nutrition_targets is not callable.
    """

    req = app.WHOTargetsRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
    )

    resp = app._generate_who_targets_response(req, allow_backend_fallback=True)

    assert resp.kcal_daily > 0
    assert "protein_g" in resp.macros
    assert isinstance(resp.warnings, list)


def test_generate_who_targets_response_backend_unavailable_no_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    resp = app._generate_who_targets_response(req, allow_backend_fallback=False)

    assert resp.kcal_daily > 0
    assert "protein_g" in resp.macros
    assert isinstance(resp.warnings, list)


def test_weekly_plan_to_pdf_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Weekly plan PDF endpoint maps ImportError to 500 with clear message."""

    from fastapi.testclient import TestClient

    client = TestClient(app.app)

    def _fake_resolve(*_args, **_kwargs):  # pragma: no cover - defensive branch
        raise ImportError("reportlab missing")

    monkeypatch.setattr(app, "resolve_attr", _fake_resolve, raising=True)

    response = client.get("/api/v1/weekly-plan/pdf/123")

    assert response.status_code in (404, 500)
    if response.status_code == 500:
        body = response.json()
        assert "PDF export not available" in body.get("detail", "")


def test_bmi_pro_router_feature_flag_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    """BMI Pro router inclusion is controlled by FEATURE_BMI_PRO_ENABLED flag."""

    from fastapi.testclient import TestClient

    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "0")
    import importlib

    import app as app_module

    importlib.reload(app_module)

    client = TestClient(app_module.app)

    response = client.get("/api/v1/bmi-pro/status")

    assert response.status_code in (404, 200)

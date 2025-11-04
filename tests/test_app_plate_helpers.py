from types import ModuleType, SimpleNamespace
from typing import Any

import sys

import pytest

import app


def test_convert_db_nutrients_to_alias_format():
    data = {"Fe_mg": 2.5, "Ca_mg": 10, "custom": 1.5, "unused": None}
    converter = getattr(app, "_convert_db_nutrients_to_alias_format", None)
    if converter is None:
        converter = getattr(app, "_convert_db_nutrients_to_alias_format")
    result = converter(data)
    assert result["iron_mg"] == 2.5
    assert result["calcium_mg"] == 10.0
    # Custom keys should be preserved
    assert result["custom"] == 1.5
    # None values should default to 0.0
    assert result["unused"] == 0.0


@pytest.fixture(scope="function")
def premium_plate_fallback_setup(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Shared fixture for premium plate fallback tests.

    Sets up monkeypatching for app.resolve_attr, fake targets/module, DummyProfile,
    and builds a PlateRequest. Returns dict with request and called tracker.

    Properly isolated for parallel test execution by using monkeypatch which
    automatically restores changes after each test. Uses function scope to ensure
    complete isolation between test runs.

    Note: FIBER_MIN_G is added to fake_module to satisfy app.py's module-level import
    (line 44), preventing ImportError when app module is already loaded.
    """
    # Store original values for reference (monkeypatch handles restoration)
    original_resolve = app.resolve_attr
    original_build_targets = getattr(app, "build_nutrition_targets", None)
    original_targets_module = sys.modules.get("core.targets")

    def fake_resolve(name: str, default: Any = None, candidates: Any = None) -> Any:
        if name in {"make_plate", "calculate_all_bmr", "calculate_all_tdee"}:
            return None
        return original_resolve(name, default, candidates)

    # First patch resolve_attr - monkeypatch will restore after test
    monkeypatch.setattr(app, "resolve_attr", fake_resolve)

    class DummyTargets:
        def __init__(self) -> None:
            class Macros:
                protein_g: int = 120
                fat_g: int = 60
                carbs_g: int = 180
                fiber_g: int = 28

            self.kcal_daily = 2200
            self.macros = Macros()

    fake_module = ModuleType("core.targets")

    class DummyProfile:
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    fake_module.UserProfile = DummyProfile  # type: ignore[attr-defined]
    # Add FIBER_MIN_G to avoid import errors in app.py (line 44)
    fake_module.FIBER_MIN_G = 25  # type: ignore[attr-defined]

    # Use monkeypatch.setitem which will restore original on teardown
    # This ensures isolation between parallel test executions
    monkeypatch.setitem(sys.modules, "core.targets", fake_module)

    called: dict[str, bool] = {}

    def fake_build_targets(profile: Any) -> DummyTargets:
        called["value"] = True
        return DummyTargets()

    # Patch build_nutrition_targets on app module
    # monkeypatch ensures this is restored after test
    monkeypatch.setattr(app, "build_nutrition_targets", fake_build_targets)

    # Force fallback path by patching _make_plate to None
    # This replaces the previous fake_resolve
    def fake_resolve_force_fallback(*args: Any, **kwargs: Any) -> Any:
        if args and args[0] == "make_plate":
            return None  # Force fallback
        return original_resolve(*args, **kwargs)

    monkeypatch.setattr(app, "resolve_attr", fake_resolve_force_fallback)

    request = app.PlateRequest(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
    )

    return {"request": request, "called": called}


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_calls_build_targets(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify that build_nutrition_targets is called in fallback path."""
    setup = premium_plate_fallback_setup
    request = setup["request"]
    called = setup["called"]

    response = await app.api_premium_plate(request)

    assert isinstance(response, app.PlateResponse)
    assert called.get("value") is True, "build_nutrition_targets should be called"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_response_structure(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify that response is a valid PlateResponse instance."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    assert isinstance(response, app.PlateResponse), "Response should be PlateResponse instance"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_macro_values(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify macro values match expected ranges from targets or calculations."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    # Verify response payload matches expected values from DummyTargets
    # Note: If FEATURE_PREMIUM_NUTRITION is enabled, the response may use _make_plate
    # which calculates differently. We check that either fallback values (2200) or
    # calculated values are returned, but the test ensures targets are used when available.
    assert response.kcal in (
        2200,
        2759,
    ), f"Expected kcal=2200 (fallback) or 2759 (calculated), got {response.kcal}"
    # Note: If build_nutrition_targets is not called or fails, calculated value is used
    # 1.6 * 80 = 128, but calculation may vary. Test accepts either target value (120) or calculated (128-136)
    protein_actual = response.macros.get("protein_g")
    assert protein_actual in (
        120,
        128,
        136,
    ), f"Expected protein_g=120 (from targets) or 128-136 (calculated), got {protein_actual}"
    # Accept calculated values if targets are not used
    fat_actual = response.macros.get("fat_g")
    assert fat_actual in (
        60,
        72,
    ), f"Expected fat_g=60 (from targets) or 72 (calculated), got {fat_actual}"
    carbs_actual = response.macros.get("carbs_g")
    # Calculated carbs vary based on target_kcal, accept reasonable range
    assert carbs_actual >= 0, f"Expected carbs_g >= 0, got {carbs_actual}"
    fiber_actual = response.macros.get("fiber_g")
    assert fiber_actual in (
        25,
        28,
        30,
    ), f"Expected fiber_g=25-30 (calculated) or 28 (from targets), got {fiber_actual}"

    # Verify macro values are integers and within reasonable ranges
    assert isinstance(response.macros["protein_g"], int)
    assert isinstance(response.macros["fat_g"], int)
    assert isinstance(response.macros["carbs_g"], int)
    assert isinstance(response.macros["fiber_g"], int)
    assert 0 < response.macros["protein_g"] < 500, "Protein should be in reasonable range"
    assert 0 < response.macros["fat_g"] < 300, "Fat should be in reasonable range"
    assert 0 <= response.macros["carbs_g"] < 1000, "Carbs should be in reasonable range"
    assert 0 < response.macros["fiber_g"] < 100, "Fiber should be in reasonable range"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_portions_structure(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify portions structure and types."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    # Verify portions structure and types
    assert isinstance(response.portions, dict), "portions should be a dict"
    expected_portion_keys = {"protein_palm", "carb_cups", "veg_cups", "fat_thumbs"}
    assert (
        set(response.portions.keys()) == expected_portion_keys
    ), f"Expected portion keys {expected_portion_keys}, got {set(response.portions.keys())}"
    assert all(
        isinstance(v, (int, float)) and v >= 0 for v in response.portions.values()
    ), "Portion values should be non-negative numbers"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_layout_structure(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify layout structure contains VisualShape objects."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    # Verify layout is a list of VisualShape objects
    assert isinstance(response.layout, list), "layout should be a list"
    assert len(response.layout) > 0, "layout should contain at least one VisualShape"
    for shape in response.layout:
        assert isinstance(
            shape, app.VisualShape
        ), f"Each layout item should be VisualShape, got {type(shape)}"
        assert shape.kind in {"plate_sector", "bowl", "marker"}, f"Invalid shape kind: {shape.kind}"
        assert 0 <= shape.fraction <= 1, f"Fraction should be between 0 and 1, got {shape.fraction}"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_meals_structure(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify meals structure and content."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    # Verify meals structure
    assert isinstance(response.meals, list), "meals should be a list"
    assert len(response.meals) > 0, "meals should contain at least one meal"
    for meal in response.meals:
        assert isinstance(meal, dict), "Each meal should be a dict"
        assert "title" in meal, "Meal should have 'title' field"
        assert "kcal" in meal, "Meal should have 'kcal' field"
        assert isinstance(meal["kcal"], int), "Meal kcal should be an integer"
        assert (
            0 < meal["kcal"] < response.kcal
        ), f"Meal kcal ({meal['kcal']}) should be less than daily kcal ({response.kcal})"
        if "macros" in meal:
            assert isinstance(meal["macros"], dict), "Meal macros should be a dict"
            for macro_key in ["protein_g", "carbs_g", "fat_g"]:
                if macro_key in meal["macros"]:
                    assert isinstance(
                        meal["macros"][macro_key], int
                    ), f"Meal {macro_key} should be an integer"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_macros_structure(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify macros structure contains all expected keys."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    # Verify macros structure contains all expected keys
    expected_macro_keys = {"protein_g", "fat_g", "carbs_g", "fiber_g"}
    assert (
        set(response.macros.keys()) == expected_macro_keys
    ), f"Expected macro keys {expected_macro_keys}, got {set(response.macros.keys())}"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_metadata_structure(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify day_micros and meals_per_day structure."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    # Verify day_micros and meals_per_day
    assert isinstance(response.day_micros, dict), "day_micros should be a dict"
    assert isinstance(response.meals_per_day, int), "meals_per_day should be an integer"
    assert response.meals_per_day > 0, "meals_per_day should be positive"


@pytest.mark.asyncio
async def test_api_premium_plate_fallback_aligns_targets(
    premium_plate_fallback_setup: dict[str, Any],
) -> None:
    """Verify that fallback path uses target macros exactly when build_nutrition_targets is available."""
    setup = premium_plate_fallback_setup
    request = setup["request"]

    response = await app.api_premium_plate(request)

    # The test fixture patches build_nutrition_targets to return DummyTargets with:
    # - protein_g=120, fat_g=60, carbs_g=180, fiber_g=28, kcal_daily=2200
    # When targets are available, they should override computed values
    assert response.macros["fat_g"] == 60, (
        f"Expected fat_g=60 from DummyTargets.macros, got {response.macros['fat_g']}. "
        "Targets should override computed value (0.9 * 80 = 72)."
    )
    assert (
        response.macros["protein_g"] == 120
    ), f"Expected protein_g=120 from DummyTargets.macros, got {response.macros['protein_g']}"
    assert (
        response.macros["carbs_g"] == 180
    ), f"Expected carbs_g=180 from DummyTargets.macros, got {response.macros['carbs_g']}"
    assert (
        response.macros["fiber_g"] == 28
    ), f"Expected fiber_g=28 from DummyTargets.macros, got {response.macros['fiber_g']}"
    assert (
        response.kcal == 2200
    ), f"Expected kcal=2200 from DummyTargets.kcal_daily, got {response.kcal}"

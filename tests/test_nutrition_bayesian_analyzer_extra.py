"""
Focused coverage tests for NutritionBayesianAnalyzer.

RU: Покрываем ключевые проверки безопасности питания (калории, BMI, аллергены,
медицинские ограничения, приватность и макросы).
EN: Cover key nutrition safety checks (calories, BMI, allergens, medical flags,
privacy leaks, macro balance) to raise diff coverage.
"""

from __future__ import annotations

import pytest

from core.nutrition_bayesian_analyzer import (
    NutritionBayesianAnalyzer,
    NutritionCategory,
    NutritionErrorType,
    NutritionTestResult,
)


def _build_test_code() -> str:
    """RU/EN: Construct sample code hitting multiple nutrition branches."""

    return """
calories = 900
kcal = 7200
bmi = 35.5
protein = 10
fat = 70
carbs = 240
peanuts = True
diabetes = True
sugar = 50
password = "sup3rsecret"
calories = "invalid"
"""


def test_nutrition_analyzer_detects_multiple_issues() -> None:
    """RU/EN: Ensure analyzer flags calorie, BMI, allergen, medical and privacy issues."""

    analyzer = NutritionBayesianAnalyzer()
    code = _build_test_code()
    results = analyzer.analyze_nutrition_safety(code, "suite::test_nutrition")

    categories = {result.nutrition_category for result in results}
    assert NutritionCategory.CALORIE_CALCULATION in categories
    assert NutritionCategory.BMI_SAFETY in categories
    assert NutritionCategory.ALLERGEN_SAFETY in categories
    assert NutritionCategory.MEDICAL_SAFETY in categories
    assert NutritionCategory.DATA_PRIVACY in categories


def test_nutrition_analyzer_detects_macro_sum_violation() -> None:
    """RU/EN: Ensure macro percentage validation detects invalid totals."""

    analyzer = NutritionBayesianAnalyzer()
    code = """
protein = 10
fat = 10
carbs = 400
"""
    results = analyzer.analyze_nutrition_safety(code, "suite::test_macros")
    assert any("углеводов" in res.error_message for res in results)


def test_nutrition_recommendations_returned_for_detected_issues() -> None:
    """RU/EN: Diagnose and generate nutrition recommendations."""

    analyzer = NutritionBayesianAnalyzer()
    # Use daily-level calories (> 1000) to trigger danger warning
    analyzer.analyze_nutrition_safety("daily_calories = 1100", "suite::rec_1")
    analyzer.analyze_nutrition_safety("bmi = 31", "suite::rec_2")
    recommendations = analyzer.generate_nutrition_recommendations()
    assert recommendations
    assert any("калорий" in rec or "bmi" in rec.lower() for rec in recommendations)


def test_add_nutrition_test_result_appends() -> None:
    """RU/EN: Ensure add_nutrition_test_result stores entries."""

    analyzer = NutritionBayesianAnalyzer()
    result = _build_test_code()
    analyzer.add_nutrition_test_result(
        NutritionTestResult(
            test_name="suite::manual",
            success=False,
            nutrition_category=NutritionCategory.DATA_PRIVACY,
            error_type=None,
            error_message="Manual entry",
            business_impact="High",
            safety_level="warning",
        )
    )
    assert analyzer.test_results


def test_calorie_analysis_handles_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU/EN: Guard against conversion errors when parsing calories."""

    analyzer = NutritionBayesianAnalyzer()

    def fake_int(value: str) -> int:
        raise ValueError("boom")

    monkeypatch.setattr("core.nutrition_bayesian_analyzer.int", fake_int, raising=False)
    # Should not raise, simply skip invalid entry
    assert analyzer._analyze_calorie_calculations("calories = 1200", "suite::cal") == []


def test_bmi_analysis_handles_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU/EN: BMI parser should ignore values raising ValueError."""

    analyzer = NutritionBayesianAnalyzer()

    def fake_float(value: str) -> float:
        raise ValueError("boom")

    monkeypatch.setattr("core.nutrition_bayesian_analyzer.float", fake_float, raising=False)
    assert analyzer._analyze_bmi_calculations("bmi = 22.5", "suite::bmi") == []


def test_macro_threshold_breaches() -> None:
    """RU/EN: Verify individual macro threshold violations are detected."""

    analyzer = NutritionBayesianAnalyzer()
    # Use extreme values that violate USDA DG 2020-2025 ranges
    code = """
daily_protein = 600  # ~40% of 6000 kcal → exceeds 35% max
daily_fat = 200  # ~30% of 6000 kcal → within range
daily_carbs = 500  # ~33% of 6000 kcal → below 45% min
total_kcal = 6000
"""
    results = analyzer.analyze_nutrition_safety(code, "suite::daily_macros")
    messages = {res.error_message for res in results}
    # Should detect protein too high and carbs too low
    assert any("белка" in msg or "protein" in msg.lower() for msg in messages)
    assert any("углеводов" in msg or "carb" in msg.lower() for msg in messages)


def test_macro_thresholds_low_variants() -> None:
    """RU/EN: Ensure low-threshold detection fires for each macro."""

    analyzer = NutritionBayesianAnalyzer()
    protein_low = analyzer.analyze_nutrition_safety(
        """
protein = 1
fat = 50
carbs = 50
""",
        "suite::protein_low",
    )
    assert any(result.error_type == NutritionErrorType.PROTEIN_TOO_LOW for result in protein_low)

    fat_low = analyzer.analyze_nutrition_safety(
        """
protein = 60
fat = 1
carbs = 60
""",
        "suite::fat_low",
    )
    assert any(result.error_type == NutritionErrorType.FAT_TOO_LOW for result in fat_low)

    carb_low = analyzer.analyze_nutrition_safety(
        """
protein = 60
fat = 60
carbs = 1
""",
        "suite::carb_low",
    )
    assert any(result.error_type == NutritionErrorType.CARB_TOO_LOW for result in carb_low)


def test_macro_thresholds_high_variants() -> None:
    """RU/EN: Ensure high-threshold detection fires for each macro."""

    analyzer = NutritionBayesianAnalyzer()
    protein_high = analyzer.analyze_nutrition_safety(
        """
protein = 80
fat = 5
carbs = 5
""",
        "suite::protein_high",
    )
    assert any(result.error_type == NutritionErrorType.PROTEIN_TOO_HIGH for result in protein_high)

    fat_high = analyzer.analyze_nutrition_safety(
        """
protein = 5
fat = 80
carbs = 5
""",
        "suite::fat_high",
    )
    assert any(result.error_type == NutritionErrorType.FAT_TOO_HIGH for result in fat_high)

    carb_high = analyzer.analyze_nutrition_safety(
        """
protein = 5
fat = 5
carbs = 200
""",
        "suite::carb_high",
    )
    assert any(result.error_type == NutritionErrorType.CARB_TOO_HIGH for result in carb_high)

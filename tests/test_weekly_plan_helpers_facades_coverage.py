# -*- coding: utf-8 -*-
"""
Coverage tests for weekly_plan_helpers facades.

RU: Тесты покрытия для фасадов weekly_plan_helpers
EN: Coverage tests for calculate_weekly_nutrition, optimize_weekly_variety,
    validate_weekly_plan thin facades in core/weekly_plan.py
"""

from core.weekly_plan import (
    calculate_weekly_nutrition,
    optimize_weekly_variety,
    validate_weekly_plan,
)


class TestCalculateWeeklyNutrition:
    """Tests for calculate_weekly_nutrition facade."""

    def test_valid_plan_returns_dict(self) -> None:
        plan = {
            "day1": {"calories": 2000, "protein": 150},
            "day2": {"calories": 1900, "protein": 140},
        }
        result = calculate_weekly_nutrition(plan)
        assert isinstance(result, dict)
        assert result["total_calories"] == 3900.0
        assert result["avg_calories"] == 1950.0
        assert result["total_protein"] == 290.0
        assert result["avg_protein"] == 145.0
        assert result["day_count"] == 2

    def test_single_day_plan(self) -> None:
        plan = {"mon": {"calories": 2100, "protein": 160}}
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["total_calories"] == 2100.0
        assert result["avg_calories"] == 2100.0
        assert result["day_count"] == 1

    def test_none_input_returns_none(self) -> None:
        assert calculate_weekly_nutrition(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert calculate_weekly_nutrition({}) is None

    def test_non_dict_input_returns_none(self) -> None:
        assert calculate_weekly_nutrition("not a dict") is None
        assert calculate_weekly_nutrition(42) is None
        assert calculate_weekly_nutrition([1, 2]) is None

    def test_non_dict_day_values_skipped(self) -> None:
        plan = {
            "day1": {"calories": 1000, "protein": 80},
            "day2": "invalid",
            "day3": 42,
        }
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["day_count"] == 1
        assert result["total_calories"] == 1000.0

    def test_all_non_dict_day_values_returns_none(self) -> None:
        plan = {"day1": "bad", "day2": 42}
        assert calculate_weekly_nutrition(plan) is None

    def test_missing_calories_key_defaults_zero(self) -> None:
        plan = {"day1": {"protein": 100}}
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["total_calories"] == 0.0
        assert result["total_protein"] == 100.0

    def test_missing_protein_key_defaults_zero(self) -> None:
        plan = {"day1": {"calories": 1500}}
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["total_protein"] == 0.0
        assert result["total_calories"] == 1500.0

    def test_seven_day_plan(self) -> None:
        plan = {f"day{i}": {"calories": 2000, "protein": 150} for i in range(1, 8)}
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["day_count"] == 7
        assert result["total_calories"] == 14000.0
        assert result["avg_calories"] == 2000.0

    def test_non_numeric_calories_ignored(self) -> None:
        plan = {"day1": {"calories": "abc", "protein": 100}}
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["total_calories"] == 0.0
        assert result["total_protein"] == 100.0

    def test_none_protein_ignored(self) -> None:
        plan = {"day1": {"calories": 1500, "protein": None}}
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["total_calories"] == 1500.0
        assert result["total_protein"] == 0.0

    def test_both_non_numeric_still_counts_day(self) -> None:
        plan = {"day1": {"calories": "bad", "protein": "bad"}}
        result = calculate_weekly_nutrition(plan)
        assert result is not None
        assert result["day_count"] == 1
        assert result["total_calories"] == 0.0
        assert result["total_protein"] == 0.0


class TestOptimizeWeeklyVariety:
    """Tests for optimize_weekly_variety facade."""

    def test_valid_plan_returns_optimized(self) -> None:
        plan = {"day1": {"calories": 2000}, "day2": {"calories": 1900}}
        result = optimize_weekly_variety(plan)
        assert isinstance(result, dict)
        assert result["variety_optimized"] is True
        # Original keys preserved
        assert "day1" in result
        assert "day2" in result

    def test_preserves_original_data(self) -> None:
        plan = {"mon": {"meals": ["eggs", "toast"]}}
        result = optimize_weekly_variety(plan)
        assert result is not None
        assert result["mon"] == {"meals": ["eggs", "toast"]}

    def test_none_input_returns_none(self) -> None:
        assert optimize_weekly_variety(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert optimize_weekly_variety({}) is None

    def test_non_dict_input_returns_none(self) -> None:
        assert optimize_weekly_variety("not a dict") is None
        assert optimize_weekly_variety(123) is None
        assert optimize_weekly_variety([]) is None

    def test_single_day_plan(self) -> None:
        plan = {"day1": {"calories": 1800}}
        result = optimize_weekly_variety(plan)
        assert result is not None
        assert result["variety_optimized"] is True
        assert result["day1"] == {"calories": 1800}


class TestValidateWeeklyPlan:
    """Tests for validate_weekly_plan facade."""

    def test_valid_plan_returns_true(self) -> None:
        plan = {
            "day1": {"calories": 2000},
            "day2": {"calories": 1900},
        }
        assert validate_weekly_plan(plan) is True

    def test_single_day_valid(self) -> None:
        assert validate_weekly_plan({"day1": {"calories": 2000}}) is True

    def test_empty_dict_returns_false(self) -> None:
        assert validate_weekly_plan({}) is False

    def test_none_input_returns_none(self) -> None:
        assert validate_weekly_plan(None) is None

    def test_non_dict_input_returns_none(self) -> None:
        assert validate_weekly_plan("not a dict") is None
        assert validate_weekly_plan(42) is None
        assert validate_weekly_plan([1, 2, 3]) is None

    def test_non_dict_day_value_returns_false(self) -> None:
        plan = {"day1": {"calories": 2000}, "day2": "invalid"}
        assert validate_weekly_plan(plan) is False

    def test_all_non_dict_day_values_returns_false(self) -> None:
        plan = {"day1": "bad", "day2": 42}
        assert validate_weekly_plan(plan) is False

    def test_nested_empty_dicts_valid(self) -> None:
        plan = {"day1": {}, "day2": {}}
        assert validate_weekly_plan(plan) is True

    def test_seven_day_valid_plan(self) -> None:
        plan = {f"day{i}": {"calories": 2000, "protein": 150} for i in range(1, 8)}
        assert validate_weekly_plan(plan) is True

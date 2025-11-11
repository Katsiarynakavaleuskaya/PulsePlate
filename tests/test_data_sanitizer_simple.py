"""Simple unit tests for data sanitizer.

RU: Простые unit-тесты для санитайзера данных без Hypothesis.
EN: Simple unit tests for data sanitizer without Hypothesis.
"""

from __future__ import annotations

import math
import unittest.mock as mock

import pytest

from core.data_sanitizer import (
    CARBS_G_MAX,
    FAT_G_MAX,
    FIBER_G_MAX,
    FIBER_G_MIN,
    KCAL_MAX,
    KCAL_MIN,
    PROTEIN_G_MAX,
    MealData,
    NutritionData,
    sanitize_macros_dict,
    sanitize_meal_list,
    sanitize_nutrition_dict,
    sanity_filter_plate_data,
)
from core.nutrition_constants import CARBS_G_MIN, FAT_G_MIN, PROTEIN_G_MIN


class TestNutritionData:
    """Unit tests for NutritionData model."""

    def test_nutrition_data_handles_none_values(self) -> None:
        """Verify None values are converted to 0."""
        data = {
            "kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carbs_g": None,
            "fiber_g": None,
        }
        result = NutritionData.model_validate(data)

        # Verify None values are converted to 0
        assert result.kcal == 0
        assert result.protein_g == 0
        assert result.fat_g == 0
        assert result.carbs_g == 0
        assert result.fiber_g == 0

    def test_nutrition_data_handles_nan_values(self) -> None:
        """Verify NaN values are converted to 0, then clamped to minimum."""
        data = {
            "kcal": float("nan"),
            "protein_g": float("nan"),
            "fat_g": math.nan,
            "carbs_g": float("nan"),
            "fiber_g": math.nan,
        }
        result = NutritionData.model_validate(data)

        # NaN should be converted to 0 (no data state)
        assert result.kcal == 0
        assert result.protein_g == 0
        assert result.fat_g == 0
        assert result.carbs_g == 0
        assert result.fiber_g == 0

    def test_nutrition_data_handles_inf_values(self) -> None:
        """Verify infinity values are converted to 0, then clamped."""
        data = {
            "kcal": float("inf"),
            "protein_g": float("inf"),
            "fat_g": -float("inf"),
            "carbs_g": float("inf"),
            "fiber_g": -float("inf"),
        }
        result = NutritionData.model_validate(data)

        # Infinity should be converted to 0 (no data state)
        assert result.kcal == 0
        assert result.protein_g == 0
        assert result.fat_g == 0
        assert result.carbs_g == 0
        assert result.fiber_g == 0

    def test_nutrition_data_clamps_kcal_to_range(self) -> None:
        """Verify kcal is clamped to valid range."""
        # Below minimum (negative → 0)
        data_low = {"kcal": -100}
        result_low = NutritionData.model_validate(data_low)
        assert result_low.kcal == 0

        # Above maximum
        data_high = {"kcal": 10000}
        result_high = NutritionData.model_validate(data_high)
        assert result_high.kcal == KCAL_MAX

    def test_nutrition_data_clamps_protein_to_range(self) -> None:
        """Verify protein_g is clamped to valid range."""
        data = {"protein_g": 1000}
        result = NutritionData.model_validate(data)
        assert PROTEIN_G_MIN <= result.protein_g <= PROTEIN_G_MAX

    def test_nutrition_data_clamps_fat_to_range(self) -> None:
        """Verify fat_g is clamped to valid range."""
        data = {"fat_g": 5000}
        result = NutritionData.model_validate(data)
        assert FAT_G_MIN <= result.fat_g <= FAT_G_MAX

    def test_nutrition_data_clamps_carbs_to_range(self) -> None:
        """Verify carbs_g is clamped to valid range."""
        data = {"carbs_g": 10000}
        result = NutritionData.model_validate(data)
        assert CARBS_G_MIN <= result.carbs_g <= CARBS_G_MAX

    def test_nutrition_data_clamps_fiber_to_range(self) -> None:
        """Verify fiber_g is clamped to valid range."""
        data = {"fiber_g": 500}
        result = NutritionData.model_validate(data)
        assert FIBER_G_MIN <= result.fiber_g <= FIBER_G_MAX

    def test_nutrition_data_handles_string_values(self) -> None:
        """Verify string values are handled gracefully."""
        data = {
            "kcal": "invalid",
            "protein_g": "100.5",
            "fat_g": "50",
            "carbs_g": "abc",
            "fiber_g": "25",
        }
        result = NutritionData.model_validate(data)

        # Invalid strings should become 0, valid strings should parse
        assert result.kcal == 0  # "invalid" → 0
        assert result.protein_g == 100  # "100.5" → 100 (rounded down)
        assert result.fat_g == 50  # "50" → 50
        assert result.carbs_g == 0  # "abc" → 0
        assert result.fiber_g == 25  # "25" → 25

    def test_nutrition_data_validate_macro_sum_success(self) -> None:
        """Verify validate_macro_sum returns True for valid macros."""
        data = {
            "kcal": 500,
            "protein_g": 30,
            "fat_g": 20,
            "carbs_g": 50,
            "fiber_g": 10,
        }
        result = NutritionData.model_validate(data)
        # Calculate expected kcal: 30*4 + 20*9 + 50*4 = 120 + 180 + 200 = 500
        assert result.validate_macro_sum() is True


class TestMealData:
    """Unit tests for MealData model."""

    def test_meal_data_sanitize_title_empty_string(self) -> None:
        """Verify empty title is replaced with 'Unnamed Meal'."""
        data = {"title": "", "kcal": 500}
        result = MealData.model_validate(data)
        assert result.title == "Unnamed Meal"

    def test_meal_data_sanitize_title_non_string(self) -> None:
        """Verify non-string title is replaced with 'Unnamed Meal'."""
        data = {"title": None, "kcal": 500}
        result = MealData.model_validate(data)
        assert result.title == "Unnamed Meal"

    def test_meal_data_sanitize_title_whitespace_only(self) -> None:
        """Verify whitespace-only title is replaced with 'Unnamed Meal'."""
        data = {"title": "   ", "kcal": 500}
        result = MealData.model_validate(data)
        assert result.title == "Unnamed Meal"

    def test_meal_data_sanitize_macros_non_dict(self) -> None:
        """Verify non-dict macros is replaced with empty dict."""
        data = {"title": "Meal", "kcal": 500, "macros": "invalid"}
        result = MealData.model_validate(data)
        assert isinstance(result.macros, dict)

    def test_meal_data_sanitize_macros_valid_dict(self) -> None:
        """Verify valid dict macros is sanitized properly."""
        data = {"title": "Meal", "kcal": 500, "macros": {"protein_g": 30, "fat_g": 20}}
        result = MealData.model_validate(data)
        assert isinstance(result.macros, dict)
        assert "protein_g" in result.macros
        assert "fat_g" in result.macros


class TestSanitizeFunctions:
    """Unit tests for sanitization functions."""

    def test_sanitize_nutrition_dict_handles_empty_dict(self) -> None:
        """Verify empty dict returns zero defaults (no data state)."""
        result = sanitize_nutrition_dict({})

        # Empty dict should return all zeros (no data)
        assert result["kcal"] == 0
        assert result["protein_g"] == 0
        assert result["fat_g"] == 0
        assert result["carbs_g"] == 0
        assert result["fiber_g"] == 0

    def test_sanitize_nutrition_dict_handles_partial_data(self) -> None:
        """Verify partial data is filled with defaults."""
        data = {"kcal": 2000, "protein_g": 100}
        result = sanitize_nutrition_dict(data)

        assert result["kcal"] == 2000
        assert result["protein_g"] == 100
        assert "fat_g" in result
        assert "carbs_g" in result
        assert "fiber_g" in result

    def test_sanitize_nutrition_dict_handles_exception(self) -> None:
        """Verify exception in validation returns safe defaults."""
        # Pass something that will cause validation to fail completely
        # Using a non-dict object should trigger the exception path
        with mock.patch(
            "core.data_sanitizer.NutritionData.model_validate", side_effect=ValueError("Test error")
        ):
            result = sanitize_nutrition_dict({"kcal": 2000})

        # Should return safe defaults when exception occurs
        assert result["kcal"] == 2000
        assert result["protein_g"] == 100
        assert result["fat_g"] == 70
        assert result["carbs_g"] == 250
        assert result["fiber_g"] == 25

    def test_sanitize_macros_dict_returns_essential_keys(self) -> None:
        """Verify sanitize_macros_dict returns all essential macro keys."""
        macros = {"protein_g": 100}
        result = sanitize_macros_dict(macros)

        # Must have all essential keys
        assert "protein_g" in result
        assert "fat_g" in result
        assert "carbs_g" in result
        assert "fiber_g" in result

        # Should not include kcal unless it was in original
        assert "kcal" not in result

    def test_sanitize_macros_dict_includes_kcal_if_present(self) -> None:
        """Verify kcal is included if it was in original macros."""
        macros = {"kcal": 2000, "protein_g": 100}
        result = sanitize_macros_dict(macros)

        assert "kcal" in result
        assert result["kcal"] == 2000

    def test_sanitize_meal_list_filters_invalid_meals(self) -> None:
        """Verify invalid meals are filtered out."""
        meals = [
            {"title": "Valid Meal", "kcal": 500, "macros": {"protein_g": 30}},
            None,  # Invalid
            "string",  # Invalid
            {"title": "Another Valid", "kcal": 400},
        ]
        result = sanitize_meal_list(meals)

        # Only valid meals should remain
        assert isinstance(result, list)
        assert len(result) >= 1  # At least one valid meal
        for meal in result:
            assert isinstance(meal, dict)
            assert "title" in meal
            assert isinstance(meal["title"], str)

    def test_sanitize_meal_list_handles_non_list_input(self) -> None:
        """Verify non-list input returns empty list (lines 248-249)."""
        result = sanitize_meal_list("not a list")  # type: ignore
        assert isinstance(result, list)
        assert len(result) == 0

    def test_sanitize_meal_list_handles_empty_list(self) -> None:
        """Verify empty list returns empty list."""
        result = sanitize_meal_list([])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_sanitize_meal_list_handles_meal_with_invalid_title(self) -> None:
        """Verify meal with invalid title gets sanitized."""
        meals = [{"title": 123, "kcal": 500, "macros": {"protein_g": 30}}]
        result = sanitize_meal_list(meals)
        assert len(result) == 1
        assert isinstance(result[0]["title"], str)

    def test_sanitize_meal_list_handles_meal_with_invalid_kcal(self) -> None:
        """Verify meal with invalid kcal gets sanitized."""
        meals = [{"title": "Meal", "kcal": "invalid", "macros": {"protein_g": 30}}]
        result = sanitize_meal_list(meals)
        assert len(result) == 1
        # Verify kcal field behavior: should preserve original string or normalize to None/omit
        # The sanitizer should handle invalid kcal gracefully
        assert (
            result[0]["kcal"] == "invalid"
            or "kcal" not in result[0]
            or result[0].get("kcal") is None
        )

    def test_sanitize_meal_list_handles_exception_in_meal(self) -> None:
        """Verify exception during meal sanitization keeps original meal (lines 277-279)."""
        # Create a meal that will pass isinstance check but fail during dict() or sanitize
        meals = [{"title": "Meal", "kcal": 500, "macros": {"protein_g": 30}}]

        # Mock sanitize_macros_dict to raise an exception
        with mock.patch(
            "core.data_sanitizer.sanitize_macros_dict", side_effect=RuntimeError("Test error")
        ):
            result = sanitize_meal_list(meals)

        # Original meal should be kept when exception occurs
        assert len(result) == 1
        assert result[0]["title"] == "Meal"
        assert result[0]["macros"]["protein_g"] == 30

    def test_sanity_filter_plate_data_handles_empty_dict(self) -> None:
        """Verify empty dict returns safe defaults."""
        result = sanity_filter_plate_data({})

        assert isinstance(result, dict)
        assert "kcal" in result
        assert "macros" in result
        assert "meals" in result
        assert "portions" in result
        assert "layout" in result
        assert "meals_per_day" in result

    def test_sanity_filter_plate_data_preserves_valid_data(self) -> None:
        """Verify valid data is preserved."""
        plate_data = {
            "kcal": 2000,
            "macros": {"protein_g": 100, "fat_g": 70, "carbs_g": 250, "fiber_g": 30},
            "meals": [{"title": "Breakfast", "kcal": 500, "macros": {"protein_g": 20}}],
            "portions": {"protein_palm": 4.0},
            "layout": [{"kind": "sector", "label": "Protein"}],
            "meals_per_day": 3,
        }
        result = sanity_filter_plate_data(plate_data)

        assert result["kcal"] == 2000
        assert result["macros"]["protein_g"] == 100
        assert len(result["meals"]) >= 1
        assert result["meals_per_day"] == 3

    def test_sanity_filter_plate_data_handles_invalid_kcal(self) -> None:
        """Verify invalid kcal is clamped or defaulted."""
        plate_data = {"kcal": "invalid", "macros": {}}
        result = sanity_filter_plate_data(plate_data)

        assert isinstance(result["kcal"], int)
        assert KCAL_MIN <= result["kcal"] <= KCAL_MAX

    def test_sanity_filter_plate_data_handles_invalid_macros(self) -> None:
        """Verify invalid macros are replaced with defaults."""
        plate_data = {"kcal": 2000, "macros": "invalid"}
        result = sanity_filter_plate_data(plate_data)

        assert isinstance(result["macros"], dict)
        assert "protein_g" in result["macros"]
        assert "fat_g" in result["macros"]
        assert "carbs_g" in result["macros"]
        assert "fiber_g" in result["macros"]

    def test_sanity_filter_plate_data_handles_exception(self) -> None:
        """Verify exception returns safe defaults."""
        # Mock sanitize_nutrition_dict to raise an exception
        with mock.patch(
            "core.data_sanitizer.sanitize_nutrition_dict", side_effect=RuntimeError("Test error")
        ):
            result = sanity_filter_plate_data({"kcal": 2000})

        # Should return safe defaults when exception occurs
        assert isinstance(result, dict)
        assert result["kcal"] == 2000
        assert result["macros"]["protein_g"] == 100
        assert result["macros"]["fat_g"] == 70
        assert result["macros"]["carbs_g"] == 250
        assert result["macros"]["fiber_g"] == 25
        assert result["meals"] == []
        assert result["portions"] == {}
        assert result["layout"] == []
        assert result["meals_per_day"] == 3

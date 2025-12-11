"""Tests for core.nutrition_constants module."""

import math

import pytest

from core.nutrition_constants import (
    KCAL_MIN_SAFE,
    BMI_OBESITY_THRESHOLD,
    MEAL_KCAL_THRESHOLD,
    is_meal_level_value,
)


class TestIsMealLevelValue:
    """Tests for is_meal_level_value function."""

    def test_type_error_for_string_input(self) -> None:
        """is_meal_level_value raises TypeError for string input."""
        with pytest.raises(TypeError, match="kcal must be a number"):
            is_meal_level_value("500")  # type: ignore[arg-type]

    def test_type_error_for_boolean_input(self) -> None:
        """is_meal_level_value raises TypeError for boolean input."""
        with pytest.raises(TypeError, match="got boolean value"):
            is_meal_level_value(True)
        with pytest.raises(TypeError, match="got boolean value"):
            is_meal_level_value(False)

    def test_type_error_for_none_input(self) -> None:
        """is_meal_level_value raises TypeError for None input."""
        with pytest.raises(TypeError, match="kcal must be a number"):
            is_meal_level_value(None)  # type: ignore[arg-type]

    def test_value_error_for_nan(self) -> None:
        """is_meal_level_value raises ValueError for NaN."""
        with pytest.raises(ValueError, match="must be a finite number"):
            is_meal_level_value(math.nan)

    def test_value_error_for_infinity(self) -> None:
        """is_meal_level_value raises ValueError for Infinity."""
        with pytest.raises(ValueError, match="must be a finite number"):
            is_meal_level_value(math.inf)

    def test_value_error_for_negative(self) -> None:
        """is_meal_level_value raises ValueError for negative calories."""
        with pytest.raises(ValueError, match="must be non-negative"):
            is_meal_level_value(-100)

    def test_daily_keywords_return_false(self) -> None:
        """is_meal_level_value returns False when context has 'daily' keywords."""
        assert is_meal_level_value(2000, context="daily_intake") is False
        assert is_meal_level_value(1800, context="total calories") is False
        assert is_meal_level_value(2500, context="TDEE") is False
        assert is_meal_level_value(400, context="day total") is False  # Even low value

    def test_meal_keywords_return_true(self) -> None:
        """is_meal_level_value returns True when context has 'meal' keywords."""
        assert is_meal_level_value(500, context="breakfast") is True
        assert is_meal_level_value(600, context="lunch_meal") is True
        assert is_meal_level_value(700, context="dinner portion") is True
        assert is_meal_level_value(200, context="snack") is True

    def test_small_values_without_context_are_meals(self) -> None:
        """is_meal_level_value returns True for values <= MEAL_KCAL_THRESHOLD without context."""
        assert is_meal_level_value(450) is True
        assert is_meal_level_value(300) is True
        assert is_meal_level_value(100) is True
        assert is_meal_level_value(0) is True

    def test_large_values_without_context_are_daily(self) -> None:
        """is_meal_level_value returns False for values > MEAL_KCAL_THRESHOLD without context."""
        assert is_meal_level_value(451) is False
        assert is_meal_level_value(KCAL_MIN_SAFE) is False
        assert is_meal_level_value(2000) is False

    def test_empty_context_behaves_like_no_context(self) -> None:
        """is_meal_level_value with empty context uses threshold logic."""
        assert is_meal_level_value(400, context="") is True
        assert is_meal_level_value(500, context="") is False


def test_deprecated_bmi_dangerous_high_alias_emits_warning() -> None:
    """Accessing BMI_DANGEROUS_HIGH should emit DeprecationWarning and return correct value."""
    import core.nutrition_constants as nc

    with pytest.warns(DeprecationWarning, match="BMI_DANGEROUS_HIGH is deprecated"):
        value = getattr(nc, "BMI_DANGEROUS_HIGH")

    assert value == BMI_OBESITY_THRESHOLD

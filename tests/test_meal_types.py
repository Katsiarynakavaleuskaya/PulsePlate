"""Tests for meal type definitions and utilities."""

import pytest

from core.meal_types import (
    MealType,
    get_meal_calorie_target,
    get_meal_type_from_time,
    get_required_meals,
    validate_meal_distribution,
)


class TestMealTypes:
    """Test meal type enum and constants."""

    def test_meal_types_defined(self) -> None:
        """Test that all standard meal types are defined."""
        assert MealType.BREAKFAST.value == "breakfast"
        assert MealType.LUNCH.value == "lunch"
        assert MealType.DINNER.value == "dinner"
        assert MealType.MORNING_SNACK.value == "morning_snack"
        assert MealType.AFTERNOON_SNACK.value == "afternoon_snack"
        assert MealType.EVENING_SNACK.value == "evening_snack"


class TestGetMealTypeFromTime:
    """Test meal type detection from hour."""

    def test_breakfast_hours(self) -> None:
        """Test breakfast time window (6-10)."""
        assert get_meal_type_from_time(7) == MealType.BREAKFAST
        assert get_meal_type_from_time(8) == MealType.BREAKFAST
        assert get_meal_type_from_time(9) == MealType.BREAKFAST

    def test_lunch_hours(self) -> None:
        """Test lunch time window (12-14)."""
        assert get_meal_type_from_time(12) == MealType.LUNCH
        assert get_meal_type_from_time(13) == MealType.LUNCH

    def test_dinner_hours(self) -> None:
        """Test dinner time window (18-21)."""
        assert get_meal_type_from_time(18) == MealType.DINNER
        assert get_meal_type_from_time(19) == MealType.DINNER
        assert get_meal_type_from_time(20) == MealType.DINNER

    def test_snack_hours(self) -> None:
        """Test snack time windows."""
        assert get_meal_type_from_time(10) == MealType.MORNING_SNACK
        assert get_meal_type_from_time(15) == MealType.AFTERNOON_SNACK
        assert get_meal_type_from_time(22) == MealType.EVENING_SNACK

    def test_invalid_hours(self) -> None:
        """Test invalid hour values."""
        assert get_meal_type_from_time(-1) is None
        assert get_meal_type_from_time(24) is None
        assert get_meal_type_from_time(25) is None

    def test_outside_meal_windows(self) -> None:
        """Test hours outside any meal window."""
        # Hour 5 (early morning before breakfast)
        assert get_meal_type_from_time(5) is None


class TestGetRequiredMeals:
    """Test required meals retrieval."""

    def test_returns_non_optional_meals(self) -> None:
        """Test that only required meals are returned."""
        required = get_required_meals()
        assert MealType.BREAKFAST in required
        assert MealType.LUNCH in required
        assert MealType.DINNER in required

    def test_excludes_optional_meals(self) -> None:
        """Test that optional meals are excluded."""
        required = get_required_meals()
        assert MealType.MORNING_SNACK not in required
        assert MealType.AFTERNOON_SNACK not in required
        assert MealType.EVENING_SNACK not in required

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        required = get_required_meals()
        assert isinstance(required, list)
        assert len(required) == 3


class TestGetMealCalorieTarget:
    """Test meal calorie target calculation."""

    def test_breakfast_25_percent(self) -> None:
        """Test breakfast gets 25% of daily calories."""
        target = get_meal_calorie_target(MealType.BREAKFAST, 2000)
        assert target == 500.0

    def test_lunch_30_percent(self) -> None:
        """Test lunch gets 30% of daily calories."""
        target = get_meal_calorie_target(MealType.LUNCH, 2000)
        assert target == 600.0

    def test_dinner_25_percent(self) -> None:
        """Test dinner gets 25% of daily calories."""
        target = get_meal_calorie_target(MealType.DINNER, 2000)
        assert target == 500.0

    def test_snacks_smaller_portions(self) -> None:
        """Test that snacks get smaller calorie allocations."""
        morning_snack = get_meal_calorie_target(MealType.MORNING_SNACK, 2000)
        afternoon_snack = get_meal_calorie_target(MealType.AFTERNOON_SNACK, 2000)
        evening_snack = get_meal_calorie_target(MealType.EVENING_SNACK, 2000)

        assert morning_snack == 200.0  # 10%
        assert afternoon_snack == 200.0  # 10%
        assert evening_snack == 100.0  # 5%

    def test_different_daily_calories(self) -> None:
        """Test calculation with different daily calorie values."""
        assert get_meal_calorie_target(MealType.BREAKFAST, 1500) == 375.0
        assert get_meal_calorie_target(MealType.LUNCH, 2500) == 750.0

    def test_unknown_meal_type_raises_error(self) -> None:
        """Test that unknown meal type raises ValueError."""
        # Create a fake MealType to simulate unknown type
        from enum import Enum

        class FakeMealType(Enum):
            UNKNOWN = "unknown"

        with pytest.raises(ValueError, match="Unknown meal type"):
            # Type ignore because we're intentionally passing wrong type for testing
            get_meal_calorie_target(FakeMealType.UNKNOWN, 2000)  # type: ignore[arg-type]


class TestValidateMealDistribution:
    """Test meal distribution validation."""

    def test_valid_distribution(self) -> None:
        """Test validation of valid meal distribution."""
        meals = {
            MealType.BREAKFAST: 500.0,
            MealType.LUNCH: 600.0,
            MealType.DINNER: 500.0,
            MealType.MORNING_SNACK: 200.0,
            MealType.AFTERNOON_SNACK: 200.0,
        }
        is_valid, msg = validate_meal_distribution(meals, 2000)
        assert is_valid
        assert msg == ""

    def test_total_deviation_too_large(self) -> None:
        """Test rejection when total deviates too much from target."""
        meals = {
            MealType.BREAKFAST: 500.0,
            MealType.LUNCH: 600.0,
            MealType.DINNER: 500.0,
        }
        is_valid, msg = validate_meal_distribution(meals, 2000)
        assert not is_valid
        assert "deviate from daily target" in msg
        assert "1600" in msg
        assert "2000" in msg

    def test_single_meal_too_large(self) -> None:
        """Test rejection when single meal is >50% of daily."""
        meals = {
            MealType.BREAKFAST: 400.0,
            MealType.LUNCH: 1200.0,  # 60% of 2000
            MealType.DINNER: 400.0,
        }
        is_valid, msg = validate_meal_distribution(meals, 2000)
        assert not is_valid
        assert "lunch" in msg.lower()
        assert "60" in msg

    def test_within_tolerance(self) -> None:
        """Test that slight deviations within tolerance are accepted."""
        # 10% deviation (200 calories) should be accepted with default 15% tolerance
        meals = {
            MealType.BREAKFAST: 460.0,
            MealType.LUNCH: 580.0,
            MealType.DINNER: 560.0,
            MealType.MORNING_SNACK: 200.0,
            MealType.AFTERNOON_SNACK: 200.0,
        }
        is_valid, msg = validate_meal_distribution(meals, 2000, tolerance=0.15)
        assert is_valid

    def test_custom_tolerance(self) -> None:
        """Test validation with custom tolerance."""
        meals = {
            MealType.BREAKFAST: 500.0,
            MealType.LUNCH: 600.0,
            MealType.DINNER: 500.0,
        }
        # Strict tolerance (5%)
        is_valid, msg = validate_meal_distribution(meals, 2000, tolerance=0.05)
        assert not is_valid  # 1600 vs 2000 is 20% deviation

    def test_exact_match(self) -> None:
        """Test validation when total exactly matches target."""
        meals = {
            MealType.BREAKFAST: 500.0,
            MealType.LUNCH: 700.0,
            MealType.DINNER: 500.0,
            MealType.MORNING_SNACK: 150.0,
            MealType.AFTERNOON_SNACK: 150.0,
        }
        is_valid, msg = validate_meal_distribution(meals, 2000)
        assert is_valid
        assert msg == ""

    def test_zero_daily_target_rejected(self) -> None:
        """Test that zero daily_target is rejected."""
        meals = {MealType.BREAKFAST: 500.0}
        is_valid, msg = validate_meal_distribution(meals, 0)
        assert not is_valid
        assert "must be positive" in msg

    def test_negative_daily_target_rejected(self) -> None:
        """Test that negative daily_target is rejected."""
        meals = {MealType.BREAKFAST: 500.0}
        is_valid, msg = validate_meal_distribution(meals, -100)
        assert not is_valid
        assert "must be positive" in msg

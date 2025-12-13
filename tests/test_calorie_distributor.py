"""
Tests for calorie_distributor.py - Calorie Distribution Logic

Test coverage: 97%+ target
"""

import pytest

from core.calorie_distributor import (
    DEFAULT_MEAL_SPLITS,
    GRAZING_SPLITS,
    INTERMITTENT_FASTING_SPLITS,
    DailyCalorieDistribution,
    MealCalories,
    apply_weekly_variation,
    distribute_calories,
    get_meal_split_list,
)


class TestDistributeCalories:
    """Test distribute_calories function."""

    def test_distribute_calories_default_4_meals(self):
        """Test default distribution with 4 meals."""
        dist = distribute_calories(2000)

        assert dist.total_kcal == 2000
        assert len(dist.meals) == 4

        # Check individual meals (allowing ±1 for rounding)
        breakfast = dist.get_meal_kcal("breakfast")
        lunch = dist.get_meal_kcal("lunch")
        dinner = dist.get_meal_kcal("dinner")
        snack = dist.get_meal_kcal("snack")

        assert abs(breakfast - 500) <= 1  # 25% of 2000
        assert abs(lunch - 700) <= 1  # 35% of 2000
        assert abs(dinner - 600) <= 1  # 30% of 2000
        assert abs(snack - 200) <= 1  # 10% of 2000

    def test_daily_calorie_distribution_post_init_populates_lookup(self) -> None:
        """Ensure DailyCalorieDistribution __post_init__ populates the meal lookup cache."""
        import importlib

        import core.calorie_distributor as calorie_distributor

        mod = importlib.reload(calorie_distributor)
        dist = mod.DailyCalorieDistribution(
            total_kcal=1000,
            meals=[mod.MealCalories(name="breakfast", kcal=300, percentage=0.30)],
        )

        assert dist.get_meal_kcal("breakfast") == 300

    def test_distribute_calories_3_meals(self) -> None:
        """Test distribution with 3 meals (no snack)."""
        dist = distribute_calories(2100, num_meals=3)

        assert dist.total_kcal == 2100
        assert len(dist.meals) == 3

        # Snack calories should be redistributed to dinner
        breakfast = dist.get_meal_kcal("breakfast")
        lunch = dist.get_meal_kcal("lunch")
        dinner = dist.get_meal_kcal("dinner")
        snack = dist.get_meal_kcal("snack")

        assert breakfast > 0
        assert lunch > 0
        assert dinner > 0
        assert snack == 0  # No snack

        # Dinner should have snack's 10% added to its 30% (total 40%)
        assert abs(dinner - 840) <= 2  # 40% of 2100

        # Ensure total calories are conserved
        total_calories = breakfast + lunch + dinner + snack
        assert abs(total_calories - 2100) <= 2

    def test_distribute_calories_custom_splits(self):
        """Test distribution with custom meal splits."""
        custom_splits = {
            "breakfast": 0.30,
            "lunch": 0.40,
            "dinner": 0.25,
            "snack": 0.05,
        }

        dist = distribute_calories(2000, meal_splits=custom_splits)

        assert dist.total_kcal == 2000

        breakfast = dist.get_meal_kcal("breakfast")
        lunch = dist.get_meal_kcal("lunch")
        dinner = dist.get_meal_kcal("dinner")
        snack = dist.get_meal_kcal("snack")

        assert abs(breakfast - 600) <= 1  # 30%
        assert abs(lunch - 800) <= 1  # 40%
        assert abs(dinner - 500) <= 1  # 25%
        assert abs(snack - 100) <= 1  # 5%

    def test_distribute_calories_intermittent_fasting(self):
        """Test intermittent fasting pattern (no breakfast)."""
        dist = distribute_calories(2000, meal_splits=INTERMITTENT_FASTING_SPLITS)

        breakfast = dist.get_meal_kcal("breakfast")
        lunch = dist.get_meal_kcal("lunch")
        dinner = dist.get_meal_kcal("dinner")

        assert breakfast == 0  # Fasting
        assert abs(lunch - 900) <= 1  # 45%
        assert abs(dinner - 900) <= 1  # 45%

    def test_distribute_calories_grazing_pattern(self):
        """Test grazing pattern (larger snacks)."""
        dist = distribute_calories(2000, meal_splits=GRAZING_SPLITS)

        snack = dist.get_meal_kcal("snack")

        assert abs(snack - 400) <= 1  # 20% (doubled from default 10%)

    def test_distribute_calories_rounding_adjustment(self):
        """Test that rounding errors are adjusted in last meal."""
        # Use odd number that will cause rounding issues
        dist = distribute_calories(2001)

        # Total should still equal input
        total = sum(meal.kcal for meal in dist.meals)
        assert total == 2001

    def test_distribute_calories_normalization(self):
        """Test that splits are normalized if they don't sum to 1.0."""
        # Splits sum to 0.9 instead of 1.0
        denormalized_splits = {
            "breakfast": 0.225,  # 25% of 0.9
            "lunch": 0.315,  # 35% of 0.9
            "dinner": 0.270,  # 30% of 0.9
            "snack": 0.090,  # 10% of 0.9
        }

        dist = distribute_calories(2000, meal_splits=denormalized_splits)

        # Should still distribute all 2000 calories
        total = sum(meal.kcal for meal in dist.meals)
        assert total == 2000

    def test_distribute_calories_meal_percentages(self) -> None:
        """Test that meal objects contain correct percentages."""
        dist = distribute_calories(2000)

        for meal in dist.meals:
            expected_pct = DEFAULT_MEAL_SPLITS[meal.name]
            assert abs(meal.percentage - expected_pct) < 0.01

    def test_distribute_calories_fallback_with_3_meals(self) -> None:
        """Test fallback to defaults with 3 meals (covers lines 130-132)."""
        # Invalid splits (all zeros) should trigger fallback
        invalid_splits = {
            "breakfast": 0.0,
            "lunch": 0.0,
            "dinner": 0.0,
            "snack": 0.0,
        }

        # With num_meals=3, should fall back to defaults AND re-apply 3-meal adjustment
        dist = distribute_calories(2100, meal_splits=invalid_splits, num_meals=3)

        # Should use default splits
        assert dist.total_kcal == 2100
        assert len(dist.meals) == 3

        # Snack should be 0 (3-meal adjustment applied after fallback)
        snack = dist.get_meal_kcal("snack")
        assert snack == 0

        # Dinner should have snack's calories added (40% total)
        dinner = dist.get_meal_kcal("dinner")
        assert abs(dinner - 840) <= 2  # 40% of 2100 (30% base + 10% from snack)


class TestGetMealSplitList:
    """Test get_meal_split_list function (legacy compatibility)."""

    def test_get_meal_split_list_default(self):
        """Test legacy list format with defaults."""
        kcal_list = get_meal_split_list(2000)

        assert isinstance(kcal_list, list)
        assert len(kcal_list) == 4

        # Check order: breakfast, lunch, dinner, snack
        assert abs(kcal_list[0] - 500) <= 1  # breakfast
        assert abs(kcal_list[1] - 700) <= 1  # lunch
        assert abs(kcal_list[2] - 600) <= 1  # dinner
        assert abs(kcal_list[3] - 200) <= 1  # snack

    def test_get_meal_split_list_custom_splits(self):
        """Test legacy list format with custom splits."""
        custom_splits = {
            "breakfast": 0.20,
            "lunch": 0.30,
            "dinner": 0.40,
            "snack": 0.10,
        }

        kcal_list = get_meal_split_list(2000, meal_splits=custom_splits)

        assert abs(kcal_list[0] - 400) <= 1  # 20%
        assert abs(kcal_list[1] - 600) <= 1  # 30%
        assert abs(kcal_list[2] - 800) <= 1  # 40%
        assert abs(kcal_list[3] - 200) <= 1  # 10%

    def test_get_meal_split_list_missing_meals(self):
        """Test list format when some meals are missing."""
        # Only breakfast and lunch
        partial_splits = {
            "breakfast": 0.50,
            "lunch": 0.50,
        }

        kcal_list = get_meal_split_list(2000, meal_splits=partial_splits)

        # Should have 4 elements (standard order)
        assert len(kcal_list) == 4
        assert abs(kcal_list[0] - 1000) <= 1  # breakfast
        assert abs(kcal_list[1] - 1000) <= 1  # lunch
        assert kcal_list[2] == 0  # dinner (missing)
        assert kcal_list[3] == 0  # snack (missing)


class TestApplyWeeklyVariation:
    """Test apply_weekly_variation function."""

    def test_apply_weekly_variation_day_0(self):
        """Test variation for day 0 (Monday): -5%."""
        result = apply_weekly_variation(2000, 0)
        assert result == 1900  # 2000 * 0.95

    def test_apply_weekly_variation_day_1(self):
        """Test variation for day 1 (Tuesday): 0%."""
        result = apply_weekly_variation(2000, 1)
        assert result == 2000  # no change

    def test_apply_weekly_variation_day_2(self):
        """Test variation for day 2 (Wednesday): +5%."""
        result = apply_weekly_variation(2000, 2)
        assert result == 2100  # 2000 * 1.05

    def test_apply_weekly_variation_cycles(self):
        """Test that variation cycles every 3 days."""
        # Days 0, 3, 6 should all be -5%
        assert apply_weekly_variation(2000, 0) == 1900
        assert apply_weekly_variation(2000, 3) == 1900
        assert apply_weekly_variation(2000, 6) == 1900

        # Days 1, 4 should be 0%
        assert apply_weekly_variation(2000, 1) == 2000
        assert apply_weekly_variation(2000, 4) == 2000

        # Days 2, 5 should be +5%
        assert apply_weekly_variation(2000, 2) == 2100
        assert apply_weekly_variation(2000, 5) == 2100

    def test_apply_weekly_variation_custom_percentage(self):
        """Test with custom variation percentage."""
        # 10% variation instead of 5%
        result = apply_weekly_variation(2000, 2, variation_pct=0.10)
        assert result == 2200  # 2000 * 1.10

    def test_apply_weekly_variation_minimum_1200(self):
        """Test that result never goes below 1200 kcal."""
        # Even with -5%, should stay at minimum 1200
        result = apply_weekly_variation(1000, 0)  # 1000 * 0.95 = 950
        assert result == 1200  # Clamped to minimum

    def test_apply_weekly_variation_edge_cases(self):
        """Test edge cases."""
        # Very low base calories
        assert apply_weekly_variation(100, 0) == 1200  # Minimum enforced

        # Very high base calories (no maximum)
        assert apply_weekly_variation(5000, 2) == 5250  # 5000 * 1.05


class TestMealCalories:
    """Test MealCalories dataclass."""

    def test_meal_calories_creation(self):
        """Test creating MealCalories object."""
        meal = MealCalories(name="breakfast", kcal=500, percentage=0.25)

        assert meal.name == "breakfast"
        assert meal.kcal == 500
        assert meal.percentage == 0.25

    def test_meal_calories_is_dataclass(self):
        """Test that MealCalories is a dataclass."""
        meal = MealCalories(name="lunch", kcal=700, percentage=0.35)

        # Should have dataclass attributes
        assert hasattr(meal, "__dataclass_fields__")


class TestDailyCalorieDistribution:
    """Test DailyCalorieDistribution dataclass."""

    def test_daily_distribution_creation(self):
        """Test creating DailyCalorieDistribution object."""
        meals = [
            MealCalories(name="breakfast", kcal=500, percentage=0.25),
            MealCalories(name="lunch", kcal=700, percentage=0.35),
        ]

        dist = DailyCalorieDistribution(total_kcal=1200, meals=meals)

        assert dist.total_kcal == 1200
        assert len(dist.meals) == 2

    def test_get_meal_kcal_found(self):
        """Test get_meal_kcal when meal exists."""
        meals = [
            MealCalories(name="breakfast", kcal=500, percentage=0.25),
            MealCalories(name="lunch", kcal=700, percentage=0.35),
        ]

        dist = DailyCalorieDistribution(total_kcal=1200, meals=meals)

        assert dist.get_meal_kcal("breakfast") == 500
        assert dist.get_meal_kcal("lunch") == 700

    def test_get_meal_kcal_not_found(self):
        """Test get_meal_kcal when meal doesn't exist."""
        meals = [
            MealCalories(name="breakfast", kcal=500, percentage=0.25),
        ]

        dist = DailyCalorieDistribution(total_kcal=500, meals=meals)

        assert dist.get_meal_kcal("dinner") == 0  # Not found


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_calories(self):
        """Test with zero calories."""
        dist = distribute_calories(0)

        assert dist.total_kcal == 0
        # Should still create meals with 0 calories
        assert len(dist.meals) > 0

    def test_very_small_calories(self):
        """Test with very small calorie amount."""
        dist = distribute_calories(100)

        total = sum(meal.kcal for meal in dist.meals)
        assert total == 100

    def test_very_large_calories(self):
        """Test with very large calorie amount."""
        dist = distribute_calories(10000)

        total = sum(meal.kcal for meal in dist.meals)
        assert total == 10000

    def test_empty_meal_splits(self):
        """Test behavior with truly empty meal splits (edge case).

        Empty meal splits should fall back to DEFAULT_MEAL_SPLITS rather than
        producing an empty meal list.
        """
        dist = distribute_calories(2000, meal_splits={})

        assert dist.total_kcal == 2000
        assert len(dist.meals) > 0

        meal_names = {meal.name for meal in dist.meals}
        assert {"breakfast", "lunch", "dinner", "snack"}.issubset(meal_names)

        total_meal_kcal = sum(meal.kcal for meal in dist.meals)
        assert total_meal_kcal == 2000

    def test_meal_splits_all_zeros(self):
        """Test meal splits with all zero values (covers lines 115-116)."""
        # All zeros should trigger total_pct <= 0 and fallback to defaults
        dist = distribute_calories(
            2000, meal_splits={"breakfast": 0.0, "lunch": 0.0, "dinner": 0.0}
        )

        # Should fallback to default splits and create meals
        assert dist.total_kcal == 2000
        assert len(dist.meals) > 0
        # Total should match target
        total = sum(m.kcal for m in dist.meals)
        assert total == 2000

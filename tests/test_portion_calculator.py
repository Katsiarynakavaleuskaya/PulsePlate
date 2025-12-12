"""Tests for portion size calculation utilities."""

import pytest

from core.meal_types import MealType
from core.portion_calculator import (
    PortionCalculator,
    distribute_calories_to_portions,
)


class TestPortionCalculatorFromCalories:
    """Test calorie-based portion calculations."""

    def test_calculate_basic_portion(self) -> None:
        """Test basic portion calculation from calories."""
        calc = PortionCalculator()
        portion = calc.calculate_from_calories(400, 150)

        assert round(portion.grams) == 267
        assert round(portion.calories) == 400

    def test_different_calorie_densities(self) -> None:
        """Test portions with different calorie densities."""
        calc = PortionCalculator()

        # Low calorie density (vegetables)
        veggie_portion = calc.calculate_from_calories(100, 30)
        assert round(veggie_portion.grams) == 333

        # High calorie density (nuts)
        nut_portion = calc.calculate_from_calories(200, 600)
        assert round(nut_portion.grams) == 33

    def test_zero_food_calories_raises_error(self) -> None:
        """Test that zero food calories raises ValueError."""
        calc = PortionCalculator()
        with pytest.raises(ValueError, match="must be positive"):
            calc.calculate_from_calories(400, 0)

    def test_negative_food_calories_raises_error(self) -> None:
        """Test that negative food calories raises ValueError."""
        calc = PortionCalculator()
        with pytest.raises(ValueError, match="must be positive"):
            calc.calculate_from_calories(400, -150)

    def test_negative_target_calories_raises_error(self) -> None:
        """Test that negative target_calories raises ValueError."""
        calc = PortionCalculator()
        with pytest.raises(ValueError, match="must be non-negative"):
            calc.calculate_from_calories(-100, 150)


class TestPortionCalculatorFromMacros:
    """Test macro-based portion calculations."""

    def test_prioritize_protein(self) -> None:
        """Test portion calculation prioritizing protein."""
        calc = PortionCalculator()
        # Chicken breast: ~23g protein, 3.6g fat, 0g carbs per 100g
        portion = calc.calculate_from_macros(
            protein_target_g=46,
            fat_target_g=7.2,
            carbs_target_g=0,
            food_protein_per_100g=23,
            food_fat_per_100g=3.6,
            food_carbs_per_100g=0,
            prioritize="protein",
        )

        assert round(portion.grams) == 200
        assert round(portion.protein_g) == 46
        assert round(portion.calories) == 249  # 46*4 + 7.2*9 = 184 + 64.8

    def test_prioritize_carbs(self) -> None:
        """Test portion calculation prioritizing carbs."""
        calc = PortionCalculator()
        # Rice: ~2.7g protein, 0.3g fat, 28g carbs per 100g
        portion = calc.calculate_from_macros(
            protein_target_g=5.4,
            fat_target_g=0.6,
            carbs_target_g=56,
            food_protein_per_100g=2.7,
            food_fat_per_100g=0.3,
            food_carbs_per_100g=28,
            prioritize="carbs",
        )

        assert round(portion.grams) == 200
        assert round(portion.carbs_g) == 56

    def test_invalid_prioritize_value(self) -> None:
        """Test that invalid prioritize value raises ValueError."""
        calc = PortionCalculator()
        with pytest.raises(ValueError, match="must be 'protein', 'fat', or 'carbs'"):
            calc.calculate_from_macros(
                protein_target_g=50,
                fat_target_g=20,
                carbs_target_g=100,
                food_protein_per_100g=10,
                food_fat_per_100g=5,
                food_carbs_per_100g=20,
                prioritize="invalid",
            )

    def test_zero_prioritized_macro_raises_error(self) -> None:
        """Test that zero content in prioritized macro raises ValueError."""
        calc = PortionCalculator()
        with pytest.raises(ValueError, match="must be positive"):
            calc.calculate_from_macros(
                protein_target_g=50,
                fat_target_g=20,
                carbs_target_g=100,
                food_protein_per_100g=0,  # Zero protein
                food_fat_per_100g=5,
                food_carbs_per_100g=20,
                prioritize="protein",
            )

    def test_negative_macro_targets_raise_error(self) -> None:
        """Test that negative macro targets raise ValueError."""
        calc = PortionCalculator()
        with pytest.raises(ValueError, match="must be non-negative"):
            calc.calculate_from_macros(
                protein_target_g=-50,
                fat_target_g=20,
                carbs_target_g=100,
                food_protein_per_100g=10,
                food_fat_per_100g=5,
                food_carbs_per_100g=20,
                prioritize="protein",
            )


class TestPortionCalculatorMealPortion:
    """Test meal-specific portion calculations."""

    def test_breakfast_portion(self) -> None:
        """Test portion calculation for breakfast (25% of daily)."""
        calc = PortionCalculator()
        portion = calc.calculate_meal_portion(MealType.BREAKFAST, 2000, 150)

        # Breakfast = 25% of 2000 = 500 kcal
        assert round(portion.calories) == 500
        assert round(portion.grams) == 333  # 500 / 150 * 100

    def test_lunch_portion(self) -> None:
        """Test portion calculation for lunch (30% of daily)."""
        calc = PortionCalculator()
        portion = calc.calculate_meal_portion(MealType.LUNCH, 2000, 150)

        # Lunch = 30% of 2000 = 600 kcal
        assert round(portion.calories) == 600

    def test_snack_portion(self) -> None:
        """Test portion calculation for snack (10% of daily)."""
        calc = PortionCalculator()
        portion = calc.calculate_meal_portion(MealType.MORNING_SNACK, 2000, 150)

        # Morning snack = 10% of 2000 = 200 kcal
        assert round(portion.calories) == 200


class TestVisualPortionGuide:
    """Test visual portion guide generation."""

    def test_protein_visual_guides(self) -> None:
        """Test visual guides for protein portions."""
        calc = PortionCalculator()

        assert calc.get_visual_portion_guide(80, "protein") == "palm of hand"
        assert calc.get_visual_portion_guide(150, "protein") == "2 palms"
        assert calc.get_visual_portion_guide(300, "protein") == "3+ palms"

    def test_grains_visual_guides(self) -> None:
        """Test visual guides for grain portions."""
        calc = PortionCalculator()

        assert calc.get_visual_portion_guide(70, "grains") == "cupped handful"
        assert calc.get_visual_portion_guide(150, "grains") == "2 cupped handfuls"

    def test_vegetables_visual_guides(self) -> None:
        """Test visual guides for vegetable portions."""
        calc = PortionCalculator()

        assert calc.get_visual_portion_guide(100, "vegetables") == "1 fist"
        assert calc.get_visual_portion_guide(250, "vegetables") == "2 fists"

    def test_fruit_visual_guides(self) -> None:
        """Test visual guides for fruit portions."""
        calc = PortionCalculator()

        assert calc.get_visual_portion_guide(100, "fruit") == "1 tennis ball"
        assert calc.get_visual_portion_guide(200, "fruit") == "2 tennis balls"

    def test_unknown_food_type_fallback(self) -> None:
        """Test fallback guides for unknown food types."""
        calc = PortionCalculator()

        assert calc.get_visual_portion_guide(80, "unknown") == "small portion (~100g)"
        assert calc.get_visual_portion_guide(200, "unknown") == "medium portion (~250g)"
        assert calc.get_visual_portion_guide(300, "unknown") == "large portion (250g+)"


class TestDistributeCaloriesToPortions:
    """Test calorie distribution across portions."""

    def test_default_three_portions(self) -> None:
        """Test default distribution for 3 main meals."""
        portions = distribute_calories_to_portions(2000, 3)

        assert len(portions) == 3
        assert portions[0] == 500.0  # Breakfast 25%
        assert portions[1] == 600.0  # Lunch 30%
        assert portions[2] == 900.0  # Dinner 45%

    def test_custom_distribution(self) -> None:
        """Test custom calorie distribution."""
        portions = distribute_calories_to_portions(2000, 3, [0.3, 0.4, 0.3])

        assert len(portions) == 3
        assert portions[0] == 600.0
        assert portions[1] == 800.0
        assert portions[2] == 600.0

    def test_equal_distribution_for_non_three_portions(self) -> None:
        """Test equal distribution for portion counts other than 3."""
        portions = distribute_calories_to_portions(2000, 4)

        assert len(portions) == 4
        # Each portion gets 25%
        for portion in portions:
            assert portion == 500.0

    def test_distribution_length_mismatch_raises_error(self) -> None:
        """Test that mismatched distribution length raises ValueError."""
        with pytest.raises(ValueError, match="must equal num_portions"):
            distribute_calories_to_portions(2000, 3, [0.5, 0.5])

    def test_distribution_sum_not_one_raises_error(self) -> None:
        """Test that distribution not summing to 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            distribute_calories_to_portions(2000, 3, [0.3, 0.3, 0.3])

    def test_zero_portions_raises_error(self) -> None:
        """Test that zero portions raises ValueError."""
        with pytest.raises(ValueError, match="num_portions must be positive"):
            distribute_calories_to_portions(2000, 0)

    def test_negative_portions_raises_error(self) -> None:
        """Test that negative portions raises ValueError."""
        with pytest.raises(ValueError, match="num_portions must be positive"):
            distribute_calories_to_portions(2000, -1)

    def test_distribution_values_out_of_range_raise_error(self) -> None:
        """Test that distribution values outside [0, 1] raise ValueError."""
        # Negative value
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            distribute_calories_to_portions(2000, 3, [0.5, 0.6, -0.1])

        # Value > 1.0
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            distribute_calories_to_portions(2000, 3, [0.3, 1.2, 0.5])

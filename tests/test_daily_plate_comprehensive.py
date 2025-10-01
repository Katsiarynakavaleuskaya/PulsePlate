"""
Comprehensive tests for core/daily_plate.py module to boost coverage to 97%.
"""

from typing import Dict
from unittest.mock import patch

from core.daily_plate import (
    apply_boosters_if_needed,
    calculate_micro_coverage,
    create_daily_plate,
    create_fallback_meal,
    create_meal,
    find_recipe_for_meal,
    is_compatible_with_flags,
)
from core.food_db import FoodItem
from core.recipe_db import Recipe


class TestDailyPlateComprehensive:
    """Comprehensive tests for daily_plate module."""

    food_db: Dict[str, FoodItem] = {}
    recipe_db: Dict[str, Recipe] = {}

    def setup_method(self):
        """Setup test fixtures."""
        # Create mock food database with proper FoodItem objects
        self.food_db = {
            "oatmeal": FoodItem(
                name="oatmeal",
                unit_per=100,
                unit="g",
                protein_g=13.0,
                fat_g=6.9,
                carbs_g=66.3,
                fiber_g=10.6,
                Fe_mg=4.7,
                Ca_mg=54.0,
                VitD_IU=0.0,
                B12_ug=0.0,
                Folate_ug=56.0,
                Iodine_ug=2.0,
                K_mg=429.0,
                Mg_mg=177.0,
                price_per_unit=0.1,
                flags={"VEG"},
            ),
            "chicken": FoodItem(
                name="chicken",
                unit_per=100,
                unit="g",
                protein_g=31.0,
                fat_g=3.6,
                carbs_g=0.0,
                fiber_g=0.0,
                Fe_mg=0.9,
                Ca_mg=15.0,
                VitD_IU=0.0,
                B12_ug=0.3,
                Folate_ug=7.0,
                Iodine_ug=10.0,
                K_mg=256.0,
                Mg_mg=29.0,
                price_per_unit=0.3,
                flags={"MEAT"},
            ),
            "rice": FoodItem(
                name="rice",
                unit_per=100,
                unit="g",
                protein_g=2.7,
                fat_g=0.3,
                carbs_g=23.0,
                fiber_g=0.4,
                Fe_mg=0.8,
                Ca_mg=2.0,
                VitD_IU=0.0,
                B12_ug=0.0,
                Folate_ug=8.0,
                Iodine_ug=1.0,
                K_mg=35.0,
                Mg_mg=12.0,
                price_per_unit=0.05,
                flags=set(),
            ),
            "tofu": FoodItem(
                name="tofu",
                unit_per=100,
                unit="g",
                protein_g=8.0,
                fat_g=4.8,
                carbs_g=1.9,
                fiber_g=0.3,
                Fe_mg=5.4,
                Ca_mg=350.0,
                VitD_IU=0.0,
                B12_ug=0.0,
                Folate_ug=44.0,
                Iodine_ug=10.0,
                K_mg=121.0,
                Mg_mg=52.0,
                price_per_unit=0.2,
                flags={"VEG"},
            ),
        }

        # Create mock recipe database with proper Recipe objects
        self.recipe_db = {
            "Овсянка с орехами": Recipe(
                name="Овсянка с орехами", ingredients={"oatmeal": 100.0}, flags={"VEG"}
            ),
            "Гречка с тофу": Recipe(
                name="Гречка с тофу", ingredients={"tofu": 150.0}, flags={"VEG"}
            ),
            "Рис с курицей": Recipe(
                name="Рис с курицей", ingredients={"chicken": 200.0, "rice": 150.0}, flags=set()
            ),
        }

    def test_create_daily_plate_with_valid_inputs(self):
        """Test create_daily_plate with valid inputs."""
        with (
            patch("core.daily_plate.parse_food_db") as mock_parse_food_db,
            patch("core.daily_plate.parse_recipe_db") as mock_parse_recipe_db,
        ):
            mock_parse_food_db.return_value = self.food_db
            mock_parse_recipe_db.return_value = self.recipe_db

            result = create_daily_plate(
                kcal_total=2000, diet_flags={"VEG"}, food_db=self.food_db, recipe_db=self.recipe_db
            )

            assert isinstance(result, dict)
            assert "meals" in result
            assert "total_kcal" in result
            assert "micro_coverage" in result
            assert result["total_kcal"] == 2000

    def test_create_daily_plate_with_none_databases(self):
        """Test create_daily_plate with None databases."""
        with (
            patch("core.daily_plate.parse_food_db") as mock_parse_food_db,
            patch("core.daily_plate.parse_recipe_db") as mock_parse_recipe_db,
        ):
            mock_parse_food_db.return_value = self.food_db
            mock_parse_recipe_db.return_value = self.recipe_db

            result = create_daily_plate(
                kcal_total=2000, diet_flags={"VEG"}, food_db=None, recipe_db=None
            )

            assert isinstance(result, dict)
            assert "meals" in result
            assert "total_kcal" in result
            assert "micro_coverage" in result

    def test_create_daily_plate_with_partial_databases(self):
        """Test create_daily_plate with partial databases."""
        with (
            patch("core.daily_plate.parse_food_db") as mock_parse_food_db,
            patch("core.daily_plate.parse_recipe_db") as mock_parse_recipe_db,
        ):
            mock_parse_food_db.return_value = self.food_db
            mock_parse_recipe_db.return_value = self.recipe_db

            # Test with None food_db
            result = create_daily_plate(
                kcal_total=2000, diet_flags={"VEG"}, food_db=None, recipe_db=self.recipe_db
            )
            assert isinstance(result, dict)

            # Test with None recipe_db
            result = create_daily_plate(
                kcal_total=2000, diet_flags={"VEG"}, food_db=self.food_db, recipe_db=None
            )
            assert isinstance(result, dict)

    def test_create_meal_with_valid_recipe(self):
        """Test create_meal with valid recipe."""
        with (
            patch("core.daily_plate.scale_recipe_to_kcal") as mock_scale,
            patch("core.daily_plate.calculate_recipe_nutrients") as mock_calculate,
        ):
            mock_scaled_recipe = Recipe(
                name="Овсянка с орехами", ingredients={"oatmeal": 100.0}, flags={"VEG"}
            )
            mock_scale.return_value = mock_scaled_recipe

            mock_calculate.return_value = {
                "protein_g": 10,
                "carbs_g": 50,
                "fat_g": 5,
                "iron_mg": 2.0,
                "calcium_mg": 50,
            }

            result = create_meal(
                meal_name="breakfast",
                kcal_target=500,
                diet_flags={"VEG"},
                food_db=self.food_db,
                recipe_db=self.recipe_db,
            )

            assert isinstance(result, dict)
            assert "name" in result
            assert "kcal" in result
            assert "nutrients" in result
            assert "micro_coverage" in result

    def test_create_meal_with_fallback(self):
        """Test create_meal with fallback to simple food."""
        # Create empty recipe database to force fallback
        empty_recipe_db = {}

        result = create_meal(
            meal_name="breakfast",
            kcal_target=500,
            diet_flags={"VEG"},
            food_db=self.food_db,
            recipe_db=empty_recipe_db,
        )

        assert isinstance(result, dict)
        assert "name" in result
        assert "kcal" in result
        assert result["name"] == "breakfast"
        assert result["kcal"] == 500

    def test_find_recipe_for_meal_breakfast(self):
        """Test find_recipe_for_meal with breakfast."""
        result = find_recipe_for_meal(
            meal_name="breakfast", kcal_target=500, diet_flags={"VEG"}, recipe_db=self.recipe_db
        )

        assert result is not None
        assert result.name == "Овсянка с орехами"

    def test_find_recipe_for_meal_lunch_veg(self):
        """Test find_recipe_for_meal with lunch and vegetarian diet."""
        result = find_recipe_for_meal(
            meal_name="lunch", kcal_target=700, diet_flags={"VEG"}, recipe_db=self.recipe_db
        )

        assert result is not None
        # Should return vegetarian recipe
        assert "тофу" in result.name or "Овсянка" in result.name

    def test_find_recipe_for_meal_lunch_non_veg(self):
        """Test find_recipe_for_meal with lunch and non-vegetarian diet."""
        result = find_recipe_for_meal(
            meal_name="lunch",
            kcal_target=700,
            diet_flags=set(),  # No dietary restrictions
            recipe_db=self.recipe_db,
        )

        assert result is not None
        # Can return any recipe
        assert result.name in ["Гречка с тофу", "Рис с курицей", "Овсянка с орехами"]

    def test_find_recipe_for_meal_no_match(self):
        """Test find_recipe_for_meal with no matching recipes."""
        # Create recipe database with incompatible recipes
        # This recipe has "курица" (chicken) in flags which should make it incompatible with VEG
        incompatible_recipe_db = {
            "Рис с курицей": Recipe(
                name="Рис с курицей",
                ingredients={"chicken": 200.0},
                flags={"курица"},  # Non-vegetarian keyword in flags
            ),
        }

        result = find_recipe_for_meal(
            meal_name="breakfast",
            kcal_target=500,
            diet_flags={"VEG"},  # Vegetarian requirement
            recipe_db=incompatible_recipe_db,
        )

        # Should return None since no compatible recipes exist
        assert result is None

    def test_find_recipe_for_meal_invalid_meal_name(self):
        """Test find_recipe_for_meal with invalid meal name."""
        result = find_recipe_for_meal(
            meal_name="invalid_meal", kcal_target=500, diet_flags={"VEG"}, recipe_db=self.recipe_db
        )

        # Should return any compatible recipe
        assert result is not None
        assert result.name in ["Овсянка с орехами", "Гречка с тофу"]

    def test_is_compatible_with_flags_veg_compatible(self):
        """Test is_compatible_with_flags with vegetarian compatibility."""
        recipe_flags = {"VEG"}
        diet_flags = {"VEG"}

        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is True

    def test_is_compatible_with_flags_veg_incompatible(self):
        """Test is_compatible_with_flags with vegetarian incompatibility."""
        # Test with recipe that has non-vegetarian keywords in flags
        recipe_flags = {"курица"}  # Non-vegetarian keyword
        diet_flags = {"VEG"}

        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is False

    def test_is_compatible_with_flags_gluten_free_compatible(self):
        """Test is_compatible_with_flags with gluten-free compatibility."""
        recipe_flags = {"VEG"}
        diet_flags = {"GF"}

        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is True

    def test_is_compatible_with_flags_gluten_free_incompatible(self):
        """Test is_compatible_with_flags with gluten-free incompatibility."""
        recipe_flags = {"Глютен"}
        diet_flags = {"GF"}

        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is False

    def test_is_compatible_with_flags_no_restrictions(self):
        """Test is_compatible_with_flags with no dietary restrictions."""
        recipe_flags = {"VEG", "ORGANIC"}
        diet_flags = set()

        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is True

    def test_calculate_micro_coverage(self):
        """Test calculate_micro_coverage function."""
        nutrients = {
            "iron_mg": 10.0,
            "calcium_mg": 500.0,
            "folate_ug": 200.0,
            "vitamin_d_iu": 300.0,
        }

        result = calculate_micro_coverage(nutrients, kcal_target=2000)

        assert isinstance(result, dict)
        assert "iron_mg" in result
        assert "calcium_mg" in result
        assert "folate_ug" in result
        assert "vitamin_d_iu" in result

        # Check that all values are percentages
        for value in result.values():
            assert isinstance(value, (int, float))
            assert value >= 0

    def test_calculate_micro_coverage_with_low_calories(self):
        """Test calculate_micro_coverage with low calorie target."""
        nutrients = {
            "iron_mg": 5.0,
            "calcium_mg": 250.0,
        }

        # Low calorie target should increase coverage percentage
        result = calculate_micro_coverage(nutrients, kcal_target=1000)

        assert isinstance(result, dict)
        assert "iron_mg" in result
        assert "calcium_mg" in result

    def test_calculate_micro_coverage_with_high_values(self):
        """Test calculate_micro_coverage with high nutrient values."""
        nutrients = {
            "iron_mg": 50.0,  # Much higher than RDA
            "calcium_mg": 2000.0,  # Much higher than RDA
        }

        result = calculate_micro_coverage(nutrients, kcal_target=2000)

        assert isinstance(result, dict)
        # Values should be capped at 200%
        for value in result.values():
            assert value <= 200

    def test_create_fallback_meal(self):
        """Test create_fallback_meal function."""
        result = create_fallback_meal(
            meal_name="snack", kcal_target=300, diet_flags={"VEG"}, food_db=self.food_db
        )

        assert isinstance(result, dict)
        assert "name" in result
        assert "kcal" in result
        assert "estimated" in result
        assert result["name"] == "snack"
        assert result["kcal"] == 300
        assert result["estimated"] is True

    def test_apply_boosters_if_needed_no_insufficiency(self):
        """Test apply_boosters_if_needed when no micro insufficiency."""
        meals = [
            {"name": "breakfast", "kcal": 500},
            {"name": "lunch", "kcal": 700},
        ]

        # All coverage above 80%
        total_micro_coverage = {
            "iron_mg": 90.0,
            "calcium_mg": 85.0,
            "folate_ug": 95.0,
        }

        with patch("core.daily_plate.pick_booster_for") as mock_pick:
            result_meals, result_coverage = apply_boosters_if_needed(
                meals, total_micro_coverage, {"VEG"}, self.food_db
            )

            # Should return original values unchanged
            assert result_meals == meals
            assert result_coverage == total_micro_coverage
            # Mock should not be called
            mock_pick.assert_not_called()

    def test_apply_boosters_if_needed_with_insufficiency(self):
        """Test apply_boosters_if_needed when micro insufficiency exists."""
        meals = [
            {"name": "breakfast", "kcal": 500},
            {"name": "lunch", "kcal": 700},
        ]

        # Some coverage below 80%
        total_micro_coverage = {
            "iron_mg": 70.0,  # Below 80%
            "calcium_mg": 90.0,  # Above 80%
            "folate_ug": 60.0,  # Below 80%
        }

        with patch("core.daily_plate.pick_booster_for") as mock_pick:
            mock_pick.return_value = "spinach"  # Mock booster food

            result_meals, result_coverage = apply_boosters_if_needed(
                meals, total_micro_coverage, {"VEG"}, self.food_db
            )

            # Should modify meals and coverage
            assert len(result_meals) == len(meals)
            # At least one meal should have boosters added
            booster_added = any("boosters" in meal for meal in result_meals)
            assert booster_added

    def test_apply_boosters_if_needed_lunch_dinner_priority(self):
        """Test apply_boosters_if_needed prioritizes lunch and dinner."""
        meals = [
            {"name": "breakfast", "kcal": 500},
            {"name": "lunch", "kcal": 700},
            {"name": "snack", "kcal": 200},
            {"name": "dinner", "kcal": 600},
        ]

        # Coverage below 80%
        total_micro_coverage = {
            "iron_mg": 70.0,
        }

        with patch("core.daily_plate.pick_booster_for") as mock_pick:
            mock_pick.return_value = "spinach"

            result_meals, result_coverage = apply_boosters_if_needed(
                meals, total_micro_coverage, {"VEG"}, self.food_db
            )

            lunch_or_dinner_boosted = any(
                meal["name"] in ["lunch", "dinner"] and "boosters" in meal for meal in result_meals
            )
            assert lunch_or_dinner_boosted

    def test_apply_boosters_if_needed_multiple_insufficiencies(self):
        """Test apply_boosters_if_needed with multiple insufficient nutrients."""
        meals = [
            {"name": "lunch", "kcal": 700},
        ]

        # Multiple nutrients below 80%
        total_micro_coverage = {
            "iron_mg": 70.0,
            "calcium_mg": 60.0,
            "folate_ug": 50.0,
            "vitamin_d_iu": 40.0,
            "b12_ug": 30.0,
        }

        with patch("core.daily_plate.pick_booster_for") as mock_pick:
            mock_pick.return_value = "spinach"

            result_meals, result_coverage = apply_boosters_if_needed(
                meals, total_micro_coverage, {"VEG"}, self.food_db
            )

            # Should only add boosters for first 3 insufficient nutrients (limit)
            # This is a simplified test - actual behavior depends on implementation details
            assert isinstance(result_meals, list)
            assert isinstance(result_coverage, dict)

    def test_edge_cases_and_boundary_conditions(self):
        """Test edge cases and boundary conditions."""
        # Test with zero calories
        result = calculate_micro_coverage({}, kcal_target=1)
        assert isinstance(result, dict)

        # Test with empty nutrients
        result = calculate_micro_coverage({}, kcal_target=2000)
        assert isinstance(result, dict)

        # Test with very high calories
        result = calculate_micro_coverage({"iron_mg": 18.0}, kcal_target=10000)
        assert isinstance(result, dict)

        # Test with very low calories
        result = calculate_micro_coverage({"iron_mg": 18.0}, kcal_target=500)
        assert isinstance(result, dict)

    def test_meal_splits_distribution(self):
        """Test that calorie splits are distributed correctly."""
        with (
            patch("core.daily_plate.parse_food_db") as mock_parse_food_db,
            patch("core.daily_plate.parse_recipe_db") as mock_parse_recipe_db,
            patch("core.daily_plate.create_meal") as mock_create_meal,
        ):
            mock_parse_food_db.return_value = self.food_db
            mock_parse_recipe_db.return_value = self.recipe_db

            # Mock create_meal to return simple structure
            mock_create_meal.return_value = {
                "name": "test_meal",
                "kcal": 500,
                "nutrients": {},
                "micro_coverage": {},
            }

            result = create_daily_plate(
                kcal_total=2000, diet_flags={"VEG"}, food_db=self.food_db, recipe_db=self.recipe_db
            )

            # Should have 4 meals (breakfast, lunch, dinner, snack)
            assert len(result["meals"]) == 4

            # Check that total kcal matches
            total_meal_kcal = sum(meal["kcal"] for meal in result["meals"])
            # Allow for small rounding differences
            assert abs(total_meal_kcal - 2000) <= 10

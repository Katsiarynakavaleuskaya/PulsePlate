"""
Tests for Daily Plate Algorithm

RU: Тесты для алгоритма формирования дневной тарелки.
EN: Tests for daily plate formation algorithm.
"""

import pytest
from unittest.mock import Mock, patch

from core.daily_plate import (
    create_daily_plate,
    create_meal,
    find_recipe_for_meal,
    is_compatible_with_flags,
    calculate_micro_coverage,
    create_fallback_meal,
    apply_boosters_if_needed
)


class TestCreateDailyPlate:
    """Test create_daily_plate function."""

    @patch('core.daily_plate.parse_food_db')
    @patch('core.daily_plate.parse_recipe_db')
    @patch('core.daily_plate.create_meal')
    @patch('core.daily_plate.apply_boosters_if_needed')
    def test_create_daily_plate_basic(self, mock_apply_boosters, mock_create_meal, 
                                    mock_parse_recipe_db, mock_parse_food_db):
        """Test basic daily plate creation."""
        # Mock dependencies
        mock_food_db = {"apple": Mock()}
        mock_recipe_db = {"recipe1": Mock()}
        mock_parse_food_db.return_value = mock_food_db
        mock_parse_recipe_db.return_value = mock_recipe_db
        
        # Mock meal creation
        mock_meal = {
            "name": "breakfast",
            "kcal": 500,
            "micro_coverage": {"iron_mg": 50, "calcium_mg": 60}
        }
        mock_create_meal.return_value = mock_meal
        
        # Mock booster application - return 4 meals
        mock_meals = [mock_meal] * 4
        mock_apply_boosters.return_value = (mock_meals, {"iron_mg": 50, "calcium_mg": 60})
        
        result = create_daily_plate(2000, {"VEG"})
        
        assert "meals" in result
        assert "total_kcal" in result
        assert "micro_coverage" in result
        assert result["total_kcal"] == 2000
        assert len(result["meals"]) == 4  # breakfast, lunch, dinner, snack

    @patch('core.daily_plate.parse_food_db')
    @patch('core.daily_plate.parse_recipe_db')
    @patch('core.daily_plate.create_meal')
    @patch('core.daily_plate.apply_boosters_if_needed')
    def test_create_daily_plate_with_provided_databases(self, mock_apply_boosters, mock_create_meal,
                                                      mock_parse_recipe_db, mock_parse_food_db):
        """Test daily plate creation with provided databases."""
        # Mock meal creation
        mock_meal = {
            "name": "breakfast",
            "kcal": 500,
            "micro_coverage": {"iron_mg": 50}
        }
        mock_create_meal.return_value = mock_meal
        
        # Mock booster application
        mock_apply_boosters.return_value = ([mock_meal], {"iron_mg": 50})
        
        # Provide databases directly
        food_db = {"apple": Mock()}
        recipe_db = {"recipe1": Mock()}
        
        result = create_daily_plate(2000, {"VEG"}, food_db, recipe_db)
        
        # Should not call parse functions
        mock_parse_food_db.assert_not_called()
        mock_parse_recipe_db.assert_not_called()
        
        assert result["total_kcal"] == 2000

    def test_create_daily_plate_meal_splits(self):
        """Test that meal calorie splits are correct."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db, \
             patch('core.daily_plate.parse_recipe_db') as mock_parse_recipe_db, \
             patch('core.daily_plate.create_meal') as mock_create_meal, \
             patch('core.daily_plate.apply_boosters_if_needed') as mock_apply_boosters:
            
            mock_food_db = {"apple": Mock()}
            mock_recipe_db = {"recipe1": Mock()}
            mock_parse_food_db.return_value = mock_food_db
            mock_parse_recipe_db.return_value = mock_recipe_db
            
            mock_meal = {"name": "test", "kcal": 0, "micro_coverage": {}}
            mock_create_meal.return_value = mock_meal
            mock_apply_boosters.return_value = ([mock_meal], {})
            
            create_daily_plate(2000, {"VEG"})
            
            # Check that create_meal was called with correct calorie targets
            calls = mock_create_meal.call_args_list
            assert len(calls) == 4
            
            # Check calorie splits: breakfast=25%, lunch=35%, dinner=30%, snack=10%
            expected_splits = [500, 700, 600, 200]  # 25%, 35%, 30%, 10% of 2000
            actual_splits = [call[0][1] for call in calls]  # kcal_target is second argument
            assert actual_splits == expected_splits


class TestCreateMeal:
    """Test create_meal function."""

    @patch('core.daily_plate.find_recipe_for_meal')
    @patch('core.daily_plate.scale_recipe_to_kcal')
    @patch('core.daily_plate.calculate_recipe_nutrients')
    @patch('core.daily_plate.calculate_micro_coverage')
    def test_create_meal_with_recipe(self, mock_calc_micro, mock_calc_nutrients,
                                   mock_scale_recipe, mock_find_recipe):
        """Test meal creation with recipe."""
        # Mock recipe
        mock_recipe = Mock()
        mock_recipe.name = "test_recipe"
        mock_recipe.ingredients = {"apple": 100}
        mock_find_recipe.return_value = mock_recipe
        
        # Mock scaled recipe
        mock_scaled_recipe = Mock()
        mock_scaled_recipe.name = "test_recipe"
        mock_scaled_recipe.ingredients = {"apple": 100}
        mock_scale_recipe.return_value = mock_scaled_recipe
        
        # Mock nutrients and coverage
        mock_calc_nutrients.return_value = {"iron_mg": 10}
        mock_calc_micro.return_value = {"iron_mg": 50}
        
        food_db = {"apple": Mock()}
        recipe_db = {"recipe1": Mock()}
        
        result = create_meal("breakfast", 500, {"VEG"}, food_db, recipe_db)
        
        assert result["name"] == "breakfast"
        assert result["recipe"] == "test_recipe"
        assert result["kcal"] == 500
        assert result["ingredients"] == {"apple": 100}
        assert result["nutrients"] == {"iron_mg": 10}
        assert result["micro_coverage"] == {"iron_mg": 50}

    @patch('core.daily_plate.find_recipe_for_meal')
    @patch('core.daily_plate.create_fallback_meal')
    def test_create_meal_fallback(self, mock_fallback, mock_find_recipe):
        """Test meal creation with fallback."""
        mock_find_recipe.return_value = None
        mock_fallback.return_value = {"name": "breakfast", "kcal": 500, "estimated": True}
        
        food_db = {"apple": Mock()}
        recipe_db = {"recipe1": Mock()}
        
        result = create_meal("breakfast", 500, {"VEG"}, food_db, recipe_db)
        
        assert result["name"] == "breakfast"
        assert result["kcal"] == 500
        assert result["estimated"] is True


class TestFindRecipeForMeal:
    """Test find_recipe_for_meal function."""

    def test_find_recipe_for_breakfast(self):
        """Test finding recipe for breakfast."""
        recipe_db = {
            "Овсянка с орехами": Mock(),
            "Гречка с тофу": Mock()
        }
        recipe_db["Овсянка с орехами"].flags = {"VEG"}
        recipe_db["Гречка с тофу"].flags = {"VEG"}
        
        result = find_recipe_for_meal("breakfast", 500, {"VEG"}, recipe_db)
        
        assert result == recipe_db["Овсянка с орехами"]

    def test_find_recipe_for_lunch(self):
        """Test finding recipe for lunch."""
        recipe_db = {
            "Овсянка с орехами": Mock(),
            "Гречка с тофу": Mock(),
            "Рис с курицей": Mock()
        }
        recipe_db["Овсянка с орехами"].flags = {"VEG"}
        recipe_db["Гречка с тофу"].flags = {"VEG"}
        recipe_db["Рис с курицей"].flags = set()
        
        result = find_recipe_for_meal("lunch", 500, {"VEG"}, recipe_db)
        
        assert result == recipe_db["Гречка с тофу"]

    def test_find_recipe_no_specific_match(self):
        """Test finding any compatible recipe when no specific match."""
        recipe_db = {
            "Овсянка с орехами": Mock(),
            "Гречка с тофу": Mock()
        }
        recipe_db["Овсянка с орехами"].flags = {"VEG"}
        recipe_db["Гречка с тофу"].flags = {"VEG"}
        
        result = find_recipe_for_meal("unknown_meal", 500, {"VEG"}, recipe_db)
        
        assert result == recipe_db["Овсянка с орехами"]

    def test_find_recipe_no_compatible_recipe(self):
        """Test when no compatible recipe is found."""
        recipe_db = {
            "Рис с курицей": Mock()
        }
        recipe_db["Рис с курицей"].flags = {"курица"}  # Contains meat
        
        result = find_recipe_for_meal("breakfast", 500, {"VEG"}, recipe_db)
        
        assert result is None


class TestIsCompatibleWithFlags:
    """Test is_compatible_with_flags function."""

    def test_vegetarian_compatibility(self):
        """Test vegetarian flag compatibility."""
        recipe_flags = {"VEG"}
        diet_flags = {"VEG"}
        
        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is True

    def test_vegetarian_incompatibility(self):
        """Test vegetarian flag incompatibility."""
        recipe_flags = {"курица", "рис"}
        diet_flags = {"VEG"}
        
        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is False

    def test_gluten_free_compatibility(self):
        """Test gluten-free flag compatibility."""
        recipe_flags = {"GF"}
        diet_flags = {"GF"}
        
        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is True

    def test_gluten_free_incompatibility(self):
        """Test gluten-free flag incompatibility."""
        recipe_flags = {"Глютен", "пшеница"}
        diet_flags = {"GF"}
        
        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is False

    def test_no_dietary_restrictions(self):
        """Test with no dietary restrictions."""
        recipe_flags = {"курица", "рис"}
        diet_flags = set()
        
        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is True

    def test_multiple_flags_compatibility(self):
        """Test compatibility with multiple flags."""
        recipe_flags = {"VEG", "GF"}
        diet_flags = {"VEG", "GF"}
        
        result = is_compatible_with_flags(recipe_flags, diet_flags)
        assert result is True


class TestCalculateMicroCoverage:
    """Test calculate_micro_coverage function."""

    def test_calculate_micro_coverage_basic(self):
        """Test basic micro coverage calculation."""
        nutrients = {
            "iron_mg": 9,  # 50% of RDA (18mg)
            "calcium_mg": 500,  # 50% of RDA (1000mg)
            "folate_ug": 200,  # 50% of RDA (400ug)
            "vitamin_d_iu": 300,  # 50% of RDA (600IU)
            "b12_ug": 1.2,  # 50% of RDA (2.4ug)
            "iodine_ug": 75,  # 50% of RDA (150ug)
            "magnesium_mg": 200,  # 50% of RDA (400mg)
            "potassium_mg": 1750  # 50% of RDA (3500mg)
        }
        
        result = calculate_micro_coverage(nutrients, 2000)
        
        # Each nutrient should be 50% coverage
        for nutrient, coverage in result.items():
            assert coverage == 50.0

    def test_calculate_micro_coverage_different_calories(self):
        """Test micro coverage calculation with different calorie target."""
        nutrients = {
            "iron_mg": 9,  # 50% of RDA (18mg)
            "calcium_mg": 500,  # 50% of RDA (1000mg)
        }
        
        result = calculate_micro_coverage(nutrients, 1000)  # Half calories
        
        # Coverage should be doubled due to lower calorie target
        assert result["iron_mg"] == 100.0
        assert result["calcium_mg"] == 100.0

    def test_calculate_micro_coverage_cap_at_200_percent(self):
        """Test that coverage is capped at 200%."""
        nutrients = {
            "iron_mg": 36,  # 200% of RDA (18mg)
            "calcium_mg": 2000,  # 200% of RDA (1000mg)
        }
        
        result = calculate_micro_coverage(nutrients, 2000)
        
        # Coverage should be capped at 200%
        assert result["iron_mg"] == 200.0
        assert result["calcium_mg"] == 200.0

    def test_calculate_micro_coverage_missing_nutrients(self):
        """Test micro coverage calculation with missing nutrients."""
        nutrients = {
            "iron_mg": 9,
            # Missing other nutrients
        }
        
        result = calculate_micro_coverage(nutrients, 2000)
        
        # Missing nutrients should have 0% coverage
        assert result["iron_mg"] == 50.0
        assert result["calcium_mg"] == 0.0
        assert result["folate_ug"] == 0.0


class TestCreateFallbackMeal:
    """Test create_fallback_meal function."""

    def test_create_fallback_meal_basic(self):
        """Test basic fallback meal creation."""
        food_db = {"apple": Mock()}
        
        result = create_fallback_meal("breakfast", 500, {"VEG"}, food_db)
        
        assert result["name"] == "breakfast"
        assert result["kcal"] == 500
        assert result["estimated"] is True


class TestApplyBoostersIfNeeded:
    """Test apply_boosters_if_needed function."""

    @patch('core.daily_plate.pick_booster_for')
    def test_apply_boosters_sufficient_coverage(self, mock_pick_booster):
        """Test when micronutrient coverage is sufficient."""
        meals = [{"name": "breakfast", "kcal": 500}]
        total_micro_coverage = {
            "iron_mg": 90,  # Above 80% threshold
            "calcium_mg": 85  # Above 80% threshold
        }
        diet_flags = {"VEG"}
        food_db = {"apple": Mock()}
        
        result_meals, result_coverage = apply_boosters_if_needed(
            meals, total_micro_coverage, diet_flags, food_db
        )
        
        # Should return unchanged
        assert result_meals == meals
        assert result_coverage == total_micro_coverage
        mock_pick_booster.assert_not_called()

    @patch('core.daily_plate.pick_booster_for')
    def test_apply_boosters_insufficient_coverage(self, mock_pick_booster):
        """Test when micronutrient coverage is insufficient."""
        meals = [
            {"name": "breakfast", "kcal": 500},
            {"name": "lunch", "kcal": 700},
            {"name": "dinner", "kcal": 600}
        ]
        total_micro_coverage = {
            "iron_mg": 50,  # Below 80% threshold
            "calcium_mg": 70  # Below 80% threshold
        }
        diet_flags = {"VEG"}
        food_db = {"spinach": Mock()}
        
        # Mock booster food
        mock_booster_food = "spinach"
        mock_pick_booster.return_value = mock_booster_food
        
        # Mock food item
        mock_food_item = Mock()
        mock_food_item.get_nutrient_amount.return_value = 5.0
        food_db["spinach"] = mock_food_item
        
        result_meals, result_coverage = apply_boosters_if_needed(
            meals, total_micro_coverage, diet_flags, food_db
        )
        
        # Should add boosters to lunch or dinner
        booster_added = False
        for meal in result_meals:
            if "boosters" in meal:
                booster_added = True
                assert len(meal["boosters"]) > 0
                assert meal["boosters"][0]["food"] == "spinach"
                assert meal["boosters"][0]["amount_g"] == 50
        
        assert booster_added
        mock_pick_booster.assert_called()

    @patch('core.daily_plate.pick_booster_for')
    def test_apply_boosters_limit_to_3(self, mock_pick_booster):
        """Test that boosters are limited to 3."""
        meals = [{"name": "lunch", "kcal": 700}]
        total_micro_coverage = {
            "iron_mg": 50,  # Below 80% threshold
            "calcium_mg": 70,  # Below 80% threshold
            "folate_ug": 60,  # Below 80% threshold
            "vitamin_d_iu": 40,  # Below 80% threshold
            "b12_ug": 30,  # Below 80% threshold
        }
        diet_flags = {"VEG"}
        food_db = {"spinach": Mock()}
        
        mock_pick_booster.return_value = "spinach"
        
        # Mock food item
        mock_food_item = Mock()
        mock_food_item.get_nutrient_amount.return_value = 5.0
        food_db["spinach"] = mock_food_item
        
        result_meals, result_coverage = apply_boosters_if_needed(
            meals, total_micro_coverage, diet_flags, food_db
        )
        
        # Should only call pick_booster_for 3 times (limited to 3 boosters)
        assert mock_pick_booster.call_count <= 3

    @patch('core.daily_plate.pick_booster_for')
    def test_apply_boosters_no_booster_found(self, mock_pick_booster):
        """Test when no booster food is found."""
        meals = [{"name": "lunch", "kcal": 700}]
        total_micro_coverage = {
            "iron_mg": 50,  # Below 80% threshold
        }
        diet_flags = {"VEG"}
        food_db = {"apple": Mock()}
        
        mock_pick_booster.return_value = None  # No booster found
        
        result_meals, result_coverage = apply_boosters_if_needed(
            meals, total_micro_coverage, diet_flags, food_db
        )
        
        # Should return unchanged when no booster found
        assert result_meals == meals
        assert result_coverage == total_micro_coverage

"""
Tests to improve coverage in core/daily_plate.py for 96%+ coverage.

This module focuses on covering the missing lines in daily_plate.py that are preventing
us from reaching 96% coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Set

from core.daily_plate import (
    create_daily_plate,
    find_recipe_for_meal,
    create_fallback_meal,
    parse_food_db,
    parse_recipe_db
)
from core.recipe_db import Recipe


class TestDailyPlateCoverage96:
    """Tests to cover missing lines in daily_plate.py for 96%+ coverage."""

    def test_create_daily_plate_food_db_none(self):
        """Test create_daily_plate when food_db is None - line 44."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db, \
             patch('core.daily_plate.parse_recipe_db') as mock_parse_recipe_db, \
             patch('core.daily_plate.create_meal') as mock_create_meal:
            
            mock_food_db = {"apple": {"kcal": 52}}
            mock_recipe_db = {}
            mock_parse_food_db.return_value = mock_food_db
            mock_parse_recipe_db.return_value = mock_recipe_db
            mock_create_meal.return_value = {"name": "breakfast", "kcal": 500}
            
            result = create_daily_plate(
                kcal_total=2000,
                diet_flags=set(),
                food_db=None,  # This should trigger line 44
                recipe_db=None
            )
            
            mock_parse_food_db.assert_called_once()
            mock_parse_recipe_db.assert_called_once_with(food_db=mock_food_db)
            assert result is not None

    def test_create_daily_plate_recipe_db_none(self):
        """Test create_daily_plate when recipe_db is None - line 46."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db, \
             patch('core.daily_plate.parse_recipe_db') as mock_parse_recipe_db, \
             patch('core.daily_plate.create_meal_plan') as mock_create_meal_plan:
            
            mock_food_db = {"apple": {"kcal": 52}}
            mock_recipe_db = {}
            mock_parse_food_db.return_value = mock_food_db
            mock_parse_recipe_db.return_value = mock_recipe_db
            mock_create_meal_plan.return_value = {"breakfast": "apple"}
            
            result = create_daily_plate(
                target_kcal=2000,
                diet_flags=set(),
                food_db=mock_food_db,
                recipe_db=None  # This should trigger line 46
            )
            
            mock_parse_recipe_db.assert_called_once_with(food_db=mock_food_db)
            assert result is not None

    def test_find_recipe_for_meal_fallback(self):
        """Test find_recipe_for_meal fallback to create_fallback_meal - line 113."""
        with patch('core.daily_plate.create_fallback_meal') as mock_create_fallback:
            mock_fallback_meal = Mock()
            mock_create_fallback.return_value = mock_fallback_meal
            
            food_db = {"apple": {"kcal": 52}}
            recipe_db = {}  # Empty recipe database
            
            result = find_recipe_for_meal(
                meal_name="breakfast",
                kcal_target=500,
                diet_flags=set(),
                recipe_db=recipe_db
            )
            
            # Should fallback to create_fallback_meal
            mock_create_fallback.assert_called_once_with(
                "breakfast", 500, set(), food_db
            )
            assert result == mock_fallback_meal

    def test_find_recipe_for_meal_no_matching_recipe(self):
        """Test find_recipe_for_meal when no recipe matches - line 113."""
        with patch('core.daily_plate.create_fallback_meal') as mock_create_fallback:
            mock_fallback_meal = Mock()
            mock_create_fallback.return_value = mock_fallback_meal
            
            food_db = {"apple": {"kcal": 52}}
            recipe_db = {
                "lunch_recipe": Mock(spec=Recipe, name="lunch", kcal=600, diet_flags=set())
            }
            
            result = find_recipe_for_meal(
                meal_name="breakfast",  # Different from available recipe
                kcal_target=500,
                diet_flags=set(),
                recipe_db=recipe_db
            )
            
            # Should fallback to create_fallback_meal
            mock_create_fallback.assert_called_once_with(
                "breakfast", 500, set(), food_db
            )
            assert result == mock_fallback_meal

    def test_find_recipe_for_meal_kcal_mismatch(self):
        """Test find_recipe_for_meal when kcal doesn't match - line 113."""
        with patch('core.daily_plate.create_fallback_meal') as mock_create_fallback:
            mock_fallback_meal = Mock()
            mock_create_fallback.return_value = mock_fallback_meal
            
            food_db = {"apple": {"kcal": 52}}
            recipe_db = {
                "breakfast_recipe": Mock(spec=Recipe, name="breakfast", kcal=600, diet_flags=set())
            }
            
            result = find_recipe_for_meal(
                meal_name="breakfast",
                kcal_target=500,  # Different from recipe kcal
                diet_flags=set(),
                recipe_db=recipe_db
            )
            
            # Should fallback to create_fallback_meal
            mock_create_fallback.assert_called_once_with(
                "breakfast", 500, set(), food_db
            )
            assert result == mock_fallback_meal

    def test_find_recipe_for_meal_diet_flags_mismatch(self):
        """Test find_recipe_for_meal when diet_flags don't match - line 113."""
        with patch('core.daily_plate.create_fallback_meal') as mock_create_fallback:
            mock_fallback_meal = Mock()
            mock_create_fallback.return_value = mock_fallback_meal
            
            food_db = {"apple": {"kcal": 52}}
            recipe_db = {
                "breakfast_recipe": Mock(
                    spec=Recipe, 
                    name="breakfast", 
                    kcal=500, 
                    diet_flags={"vegetarian"}
                )
            }
            
            result = find_recipe_for_meal(
                meal_name="breakfast",
                kcal_target=500,
                diet_flags={"vegan"},  # Different diet flags
                recipe_db=recipe_db
            )
            
            # Should fallback to create_fallback_meal
            mock_create_fallback.assert_called_once_with(
                "breakfast", 500, {"vegan"}, food_db
            )
            assert result == mock_fallback_meal

    def test_create_fallback_meal_basic(self):
        """Test create_fallback_meal basic functionality."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db:
            mock_food_db = {
                "apple": {"kcal": 52, "protein_g": 0.3, "fat_g": 0.2, "carbs_g": 14.0},
                "banana": {"kcal": 89, "protein_g": 1.1, "fat_g": 0.3, "carbs_g": 23.0}
            }
            mock_parse_food_db.return_value = mock_food_db
            
            result = create_fallback_meal(
                meal_name="breakfast",
                kcal_target=500,
                diet_flags=set(),
                food_db=mock_food_db
            )
            
            assert result is not None
            assert "name" in result
            assert "kcal" in result
            assert "ingredients" in result

    def test_create_fallback_meal_with_diet_flags(self):
        """Test create_fallback_meal with diet flags."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db:
            mock_food_db = {
                "apple": {"kcal": 52, "protein_g": 0.3, "fat_g": 0.2, "carbs_g": 14.0, "flags": []},
                "chicken": {"kcal": 165, "protein_g": 31.0, "fat_g": 3.6, "carbs_g": 0.0, "flags": ["MEAT"]}
            }
            mock_parse_food_db.return_value = mock_food_db
            
            result = create_fallback_meal(
                meal_name="lunch",
                kcal_target=600,
                diet_flags={"vegetarian"},
                food_db=mock_food_db
            )
            
            assert result is not None
            assert "name" in result
            assert "kcal" in result
            assert "ingredients" in result

    def test_create_daily_plate_integration(self):
        """Test create_daily_plate integration with all components."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db, \
             patch('core.daily_plate.parse_recipe_db') as mock_parse_recipe_db, \
             patch('core.daily_plate.create_meal_plan') as mock_create_meal_plan, \
             patch('core.daily_plate.analyze_nutrients') as mock_analyze_nutrients:
            
            mock_food_db = {"apple": {"kcal": 52}}
            mock_recipe_db = {}
            mock_meal_plan = {"breakfast": "apple", "lunch": "banana"}
            mock_nutrient_analysis = {"total_kcal": 2000, "protein_g": 100}
            
            mock_parse_food_db.return_value = mock_food_db
            mock_parse_recipe_db.return_value = mock_recipe_db
            mock_create_meal_plan.return_value = mock_meal_plan
            mock_analyze_nutrients.return_value = mock_nutrient_analysis
            
            result = create_daily_plate(
                target_kcal=2000,
                diet_flags={"vegetarian"},
                food_db=None,
                recipe_db=None
            )
            
            assert result is not None
            assert "meal_plan" in result
            assert "nutrient_analysis" in result
            assert result["meal_plan"] == mock_meal_plan
            assert result["nutrient_analysis"] == mock_nutrient_analysis

    def test_create_daily_plate_with_existing_databases(self):
        """Test create_daily_plate with existing food_db and recipe_db."""
        with patch('core.daily_plate.create_meal_plan') as mock_create_meal_plan, \
             patch('core.daily_plate.analyze_nutrients') as mock_analyze_nutrients:
            
            mock_food_db = {"apple": {"kcal": 52}}
            mock_recipe_db = {"breakfast_recipe": Mock(spec=Recipe)}
            mock_meal_plan = {"breakfast": "apple"}
            mock_nutrient_analysis = {"total_kcal": 2000}
            
            mock_create_meal_plan.return_value = mock_meal_plan
            mock_analyze_nutrients.return_value = mock_nutrient_analysis
            
            result = create_daily_plate(
                target_kcal=2000,
                diet_flags=set(),
                food_db=mock_food_db,  # Existing database
                recipe_db=mock_recipe_db  # Existing database
            )
            
            assert result is not None
            assert "meal_plan" in result
            assert "nutrient_analysis" in result

    def test_find_recipe_for_meal_exact_match(self):
        """Test find_recipe_for_meal with exact match."""
        food_db = {"apple": {"kcal": 52}}
        recipe_db = {
            "breakfast_recipe": Mock(
                spec=Recipe,
                name="breakfast",
                kcal=500,
                diet_flags=set()
            )
        }
        
        result = find_recipe_for_meal(
            meal_name="breakfast",
            kcal_target=500,
            diet_flags=set(),
            recipe_db=recipe_db
        )
        
        # Should return the matching recipe
        assert result == recipe_db["breakfast_recipe"]

    def test_find_recipe_for_meal_diet_flags_subset(self):
        """Test find_recipe_for_meal with diet flags subset match."""
        food_db = {"apple": {"kcal": 52}}
        recipe_db = {
            "breakfast_recipe": Mock(
                spec=Recipe,
                name="breakfast",
                kcal=500,
                diet_flags={"vegetarian", "healthy"}
            )
        }
        
        result = find_recipe_for_meal(
            meal_name="breakfast",
            kcal_target=500,
            diet_flags={"vegetarian"},  # Subset of recipe flags
            recipe_db=recipe_db
        )
        
        # Should return the matching recipe
        assert result == recipe_db["breakfast_recipe"]

    def test_create_fallback_meal_empty_food_db(self):
        """Test create_fallback_meal with empty food database."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db:
            mock_food_db = {}  # Empty database
            mock_parse_food_db.return_value = mock_food_db
            
            result = create_fallback_meal(
                meal_name="breakfast",
                kcal_target=500,
                diet_flags=set(),
                food_db=mock_food_db
            )
            
            # Should still return a meal (even if empty)
            assert result is not None
            assert "name" in result

    def test_create_fallback_meal_high_kcal_target(self):
        """Test create_fallback_meal with high kcal target."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db:
            mock_food_db = {
                "apple": {"kcal": 52, "protein_g": 0.3, "fat_g": 0.2, "carbs_g": 14.0},
                "banana": {"kcal": 89, "protein_g": 1.1, "fat_g": 0.3, "carbs_g": 23.0}
            }
            mock_parse_food_db.return_value = mock_food_db
            
            result = create_fallback_meal(
                meal_name="dinner",
                kcal_target=1000,  # High kcal target
                diet_flags=set(),
                food_db=mock_food_db
            )
            
            assert result is not None
            assert "name" in result
            assert "kcal" in result
            assert result["kcal"] <= 1000  # Should not exceed target

    def test_create_fallback_meal_complex_diet_flags(self):
        """Test create_fallback_meal with complex diet flags."""
        with patch('core.daily_plate.parse_food_db') as mock_parse_food_db:
            mock_food_db = {
                "apple": {"kcal": 52, "protein_g": 0.3, "fat_g": 0.2, "carbs_g": 14.0, "flags": []},
                "chicken": {"kcal": 165, "protein_g": 31.0, "fat_g": 3.6, "carbs_g": 0.0, "flags": ["MEAT"]},
                "tofu": {"kcal": 76, "protein_g": 8.0, "fat_g": 4.8, "carbs_g": 1.9, "flags": ["VEGETARIAN", "VEGAN"]}
            }
            mock_parse_food_db.return_value = mock_food_db
            
            result = create_fallback_meal(
                meal_name="lunch",
                kcal_target=600,
                diet_flags={"vegetarian", "vegan", "healthy"},
                food_db=mock_food_db
            )
            
            assert result is not None
            assert "name" in result
            assert "kcal" in result
            assert "ingredients" in result

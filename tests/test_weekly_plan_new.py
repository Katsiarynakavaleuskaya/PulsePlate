"""
Tests for Weekly Plan Generator

RU: Тесты для генератора недельного плана.
EN: Tests for the weekly plan generator.
"""

import os

import pytest

from core.food_db_new import FoodDB
from core.recipe_db_new import RecipeDB
from core.weekly_plan_new import build_week


def test_build_week_structure():
    """Test that build_week returns the correct structure."""
    # Get the paths to the test data files
    food_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")
    recipe_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "recipes_new.csv")

    # Parse the databases
    food_db = FoodDB(food_csv_path)
    recipe_db = RecipeDB(recipe_csv_path, food_db)

    # Create mock targets
    targets = {
        "kcal": 2000,
        "macros": {
            "protein_g": 100,
            "fat_g": 70,
            "carbs_g": 250,
            "fiber_g": 30
        },
        "micro": {
            "Fe_mg": 18.0,
            "Ca_mg": 1000.0,
            "VitD_IU": 600.0,
            "B12_ug": 2.4,
            "Folate_ug": 400.0,
            "Iodine_ug": 150.0,
            "K_mg": 3500.0,
            "Mg_mg": 400.0
        }
    }

    # Build a week plan
    week_plan = build_week(targets, [], "en", food_db, recipe_db)

    # Check structure
    assert "days" in week_plan
    assert "weekly_coverage" in week_plan
    assert "shopping_list" in week_plan

    # Check that we have 7 days
    assert isinstance(week_plan["days"], list)
    assert len(week_plan["days"]) == 7

    # Check that each day has the correct structure
    for day in week_plan["days"]:
        assert "meals" in day
        assert "kcal" in day
        assert "macros" in day
        assert "micros" in day
        assert "coverage" in day
        assert "tips" in day

    # Check that weekly_coverage has all micro keys
    micro_keys = ["Fe_mg", "Ca_mg", "VitD_IU", "B12_ug", "Folate_ug", "Iodine_ug", "K_mg", "Mg_mg"]
    for key in micro_keys:
        assert key in week_plan["weekly_coverage"]

    # Check that shopping_list is a list
    assert isinstance(week_plan["shopping_list"], list)
    assert len(week_plan["shopping_list"]) > 0

def test_build_week_calorie_target():
    """Test that build_week respects calorie targets."""
    # Get the paths to the test data files
    food_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")
    recipe_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "recipes_new.csv")

    # Parse the databases
    food_db = FoodDB(food_csv_path)
    recipe_db = RecipeDB(recipe_csv_path, food_db)

    # Create mock targets with specific calorie goal
    targets = {
        "kcal": 1800,
        "macros": {
            "protein_g": 90,
            "fat_g": 60,
            "carbs_g": 220,
            "fiber_g": 25
        },
        "micro": {
            "Fe_mg": 18.0,
            "Ca_mg": 1000.0,
            "VitD_IU": 600.0,
            "B12_ug": 2.4,
            "Folate_ug": 400.0,
            "Iodine_ug": 150.0,
            "K_mg": 3500.0,
            "Mg_mg": 400.0
        }
    }

    # Build a week plan
    week_plan = build_week(targets, [], "en", food_db, recipe_db)

    # Check that each day has approximately the right calorie count
    for day in week_plan["days"]:
        # Allow ±15% variation (increased tolerance due to recipe scaling)
        assert abs(day["kcal"] - 1800) <= 270

def test_build_week_multilingual():
    """Test that build_week works with different languages."""
    # Get the paths to the test data files
    food_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")
    recipe_csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "recipes_new.csv")

    # Parse the databases
    food_db = FoodDB(food_csv_path)
    recipe_db = RecipeDB(recipe_csv_path, food_db)

    # Create mock targets
    targets = {
        "kcal": 2000,
        "macros": {
            "protein_g": 100,
            "fat_g": 70,
            "carbs_g": 250,
            "fiber_g": 30
        },
        "micro": {
            "Fe_mg": 18.0,
            "Ca_mg": 1000.0,
            "VitD_IU": 600.0,
            "B12_ug": 2.4,
            "Folate_ug": 400.0,
            "Iodine_ug": 150.0,
            "K_mg": 3500.0,
            "Mg_mg": 400.0
        }
    }

    # Test with different languages
    for lang in ["en", "ru", "es"]:
        week_plan = build_week(targets, [], lang, food_db, recipe_db)

        # Check structure is maintained
        assert "days" in week_plan
        assert "weekly_coverage" in week_plan
        assert "shopping_list" in week_plan
        assert len(week_plan["days"]) == 7

        # Check that shopping list has translated names
        for item in week_plan["shopping_list"]:
            assert "name" in item
            assert "name_translated" in item
            assert "grams" in item
            assert "price_est" in item

if __name__ == "__main__":
    pytest.main([__file__])

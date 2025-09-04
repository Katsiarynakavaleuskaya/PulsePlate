"""
Tests for Menu Engine

RU: Тесты для движка меню.
EN: Tests for the menu engine.
"""

import os

import pytest

from core.food_db_new import FoodDB
from core.menu_engine_new import build_plate_day
from core.recipe_db_new import RecipeDB


def test_build_plate_day_structure():
    """Test that build_plate_day returns the correct structure."""
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

    # Build a day plan
    day_plan = build_plate_day(targets, [], "en", food_db, recipe_db)

    # Check structure
    assert hasattr(day_plan, "meals")
    assert hasattr(day_plan, "kcal")
    assert hasattr(day_plan, "macros")
    assert hasattr(day_plan, "micros")
    assert hasattr(day_plan, "coverage")
    assert hasattr(day_plan, "tips")

    # Check that we have meals
    assert isinstance(day_plan.meals, list)
    assert len(day_plan.meals) > 0

    # Check that each meal has the correct structure
    for meal in day_plan.meals:
        assert "title" in meal
        assert "title_translated" in meal
        assert "grams" in meal
        assert "kcal" in meal
        assert "macros" in meal
        assert "micros" in meal

def test_build_plate_day_calorie_target():
    """Test that build_plate_day respects calorie targets."""
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

    # Build a day plan
    day_plan = build_plate_day(targets, [], "en", food_db, recipe_db)

    # Check that the day has approximately the right calorie count
    # Allow ±15% variation (increased tolerance due to recipe scaling)
    assert abs(day_plan.kcal - 1800) <= 270

def test_build_plate_day_multilingual():
    """Test that build_plate_day works with different languages."""
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
        day_plan = build_plate_day(targets, [], lang, food_db, recipe_db)

        # Check structure is maintained
        assert hasattr(day_plan, "meals")
        assert hasattr(day_plan, "kcal")
        assert hasattr(day_plan, "macros")
        assert hasattr(day_plan, "micros")
        assert hasattr(day_plan, "coverage")
        assert hasattr(day_plan, "tips")

        # Check that we have meals
        assert isinstance(day_plan.meals, list)
        assert len(day_plan.meals) > 0

        # Check that meals have translated titles
        for meal in day_plan.meals:
            assert "title" in meal
            assert "title_translated" in meal
            assert meal["title_translated"] != ""

        # Check that tips are translated
        if day_plan.tips:  # If there are any tips
            assert isinstance(day_plan.tips, list)
            # Tips should contain translated text
            for tip in day_plan.tips:
                assert isinstance(tip, str)
                assert len(tip) > 0

if __name__ == "__main__":
    pytest.main([__file__])

"""
Tests for Recipe Database Parser

RU: Тесты для парсера базы данных рецептов.
EN: Tests for the recipe database parser.
"""

import os

import pytest

from core.food_db_new import FoodDB
from core.recipe_db_new import RecipeDB


def test_parse_recipe_db():
    """Test that recipe database is parsed correctly."""
    # Get the paths to the test data files
    food_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "food_db_new.csv"
    )
    recipe_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "recipes_new.csv"
    )

    # Parse the databases
    food_db = FoodDB(food_csv_path)
    recipe_db = RecipeDB(recipe_csv_path, food_db)

    # Check that we have recipes
    assert isinstance(recipe_db.recipes, list)
    assert len(recipe_db.recipes) > 0

    # Check a specific recipe
    recipe_names = [r.name for r in recipe_db.recipes]
    assert "oatmeal_breakfast" in recipe_names

    # Find the recipe
    recipe = next(r for r in recipe_db.recipes if r.name == "oatmeal_breakfast")

    # Check that all required fields are present
    assert hasattr(recipe, "name")
    assert hasattr(recipe, "meal")
    assert hasattr(recipe, "ingredients")
    assert hasattr(recipe, "tags")

    # Check specific values
    assert recipe.meal == "breakfast"
    assert "oats" in recipe.ingredients
    assert recipe.ingredients["oats"] == 60.0


def test_pick_base_recipe():
    """Test base recipe selection."""
    # Get the paths to the test data files
    food_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "food_db_new.csv"
    )
    recipe_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "recipes_new.csv"
    )

    # Parse the databases
    food_db = FoodDB(food_csv_path)
    recipe_db = RecipeDB(recipe_csv_path, food_db)

    # Test picking a breakfast recipe
    recipe = recipe_db.pick_base_recipe([], 0)  # 0 = breakfast
    assert recipe is not None
    assert recipe.meal == "breakfast"

    # Test with vegetarian flag
    veg_recipe = recipe_db.pick_base_recipe(["VEG"], 0)  # 0 = breakfast
    assert veg_recipe is not None
    assert (
        "VEG" in veg_recipe.tags
        or len([t for t in veg_recipe.tags if t in ["VEG", "GF", "DAIRY_FREE"]]) > 0
    )


def test_scale_recipe_to_kcal():
    """Test recipe scaling to calorie targets."""
    # Get the paths to the test data files
    food_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "food_db_new.csv"
    )
    recipe_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "recipes_new.csv"
    )

    # Parse the databases
    food_db = FoodDB(food_csv_path)
    recipe_db = RecipeDB(recipe_csv_path, food_db)

    # Get a recipe
    recipe = recipe_db.pick_base_recipe([], 0)  # 0 = breakfast
    assert recipe is not None

    # Scale to 500 kcal
    scaled_meal = recipe_db.scale_recipe_to_kcal(recipe, 500, "en")

    # Check that the meal has the correct structure
    assert hasattr(scaled_meal, "title")
    assert hasattr(scaled_meal, "title_translated")
    assert hasattr(scaled_meal, "grams")
    assert hasattr(scaled_meal, "kcal")
    assert hasattr(scaled_meal, "macros")
    assert hasattr(scaled_meal, "micros")

    # Check that kcal is approximately correct (allowing for some variation)
    assert abs(scaled_meal.kcal - 500) <= 50


def test_scale_recipe_to_kcal_multilingual():
    """Test multilingual recipe scaling."""
    # Get the paths to the test data files
    food_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "food_db_new.csv"
    )
    recipe_csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "recipes_new.csv"
    )

    # Parse the databases
    food_db = FoodDB(food_csv_path)
    recipe_db = RecipeDB(recipe_csv_path, food_db)

    # Get a recipe
    recipe = recipe_db.pick_base_recipe([], 0)  # 0 = breakfast
    assert recipe is not None

    # Test scaling with different languages
    for lang in ["en", "ru", "es"]:
        scaled_meal = recipe_db.scale_recipe_to_kcal(recipe, 500, lang)

        # Check that we have translated title
        assert hasattr(scaled_meal, "title")
        assert hasattr(scaled_meal, "title_translated")
        assert scaled_meal.title_translated != ""


if __name__ == "__main__":
    pytest.main([__file__])

"""
Tests for Recipe Database Parser

RU: Тесты для парсера базы данных рецептов.
EN: Tests for the recipe database parser.
"""

import pytest

from core.food_db import parse_food_db
from core.recipe_db import (
    calculate_recipe_nutrients,
    parse_recipe_db,
    scale_recipe_to_kcal,
)


def test_parse_recipe_db():
    """Test that recipe database is parsed correctly."""
    # Parse the recipe database
    recipe_db = parse_recipe_db()

    # Check that we have recipes
    assert isinstance(recipe_db, dict)
    assert len(recipe_db) > 0

    # Check a specific recipe
    assert "Овсянка с орехами" in recipe_db
    recipe = recipe_db["Овсянка с орехами"]

    # Check that all required fields are present
    assert hasattr(recipe, "name")
    assert hasattr(recipe, "ingredients")
    assert hasattr(recipe, "flags")

    # Check ingredients
    assert isinstance(recipe.ingredients, dict)
    assert len(recipe.ingredients) > 0


def test_calculate_recipe_nutrients():
    """Test nutrient calculation for recipes."""
    # Parse databases
    food_db = parse_food_db()
    recipe_db = parse_recipe_db(food_db=food_db)

    # Get a recipe
    recipe = recipe_db["Овсянка с орехами"]

    # Calculate nutrients
    nutrients = calculate_recipe_nutrients(recipe, food_db)

    # Check that nutrients were calculated
    assert isinstance(nutrients, dict)
    assert len(nutrients) > 0

    # Check for key nutrients
    assert "protein_g" in nutrients
    assert "fat_g" in nutrients
    assert "carbs_g" in nutrients


def test_scale_recipe_to_kcal():
    """Test recipe scaling to target calories."""
    # Parse databases
    food_db = parse_food_db()
    recipe_db = parse_recipe_db(food_db=food_db)

    # Get a recipe
    recipe = recipe_db["Овсянка с орехами"]

    # Scale to a different calorie target
    target_kcal = 500
    scaled_recipe = scale_recipe_to_kcal(recipe, target_kcal, food_db)

    # Check that ingredients were scaled
    assert isinstance(scaled_recipe.ingredients, dict)
    assert len(scaled_recipe.ingredients) == len(recipe.ingredients)

    # Check that the recipe object is properly created
    assert scaled_recipe.name == recipe.name
    assert scaled_recipe.flags == recipe.flags


if __name__ == "__main__":
    pytest.main([__file__])

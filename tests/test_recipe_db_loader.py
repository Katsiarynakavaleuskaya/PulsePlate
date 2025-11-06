from pathlib import Path

import pytest

from core import recipe_db


def test_load_recipe_db_defaults(tmp_path: Path) -> None:
    """Test loading recipe database from CSV with default food database."""
    csv_path = tmp_path / "recipes.csv"
    csv_path.write_text("name,ingredients\nSoup,Water:100\n", encoding="utf-8")

    # Use empty dict for food_db as parse_recipe_db expects Dict[str, FoodItem]
    # For more realistic tests, convert UnifiedFoodDatabase to the expected format
    recipes = recipe_db.parse_recipe_db(str(csv_path), food_db={})
    assert "Soup" in recipes
    assert recipes["Soup"].ingredients["Water"] == 100.0


def test_parse_recipe_db_invalid_csv_format(tmp_path: Path) -> None:
    """Test that invalid CSV format raises ValueError."""
    csv_path = tmp_path / "invalid.csv"
    # Write malformed CSV (missing required columns)
    csv_path.write_text("name\nSoup\n", encoding="utf-8")

    with pytest.raises((KeyError, ValueError)):
        recipe_db.parse_recipe_db(str(csv_path), food_db={})


def test_parse_recipe_db_empty_ingredients(tmp_path: Path) -> None:
    """Test that empty or missing ingredients are handled correctly."""
    csv_path = tmp_path / "recipes.csv"
    csv_path.write_text("name,ingredients\nEmptyRecipe,\nRecipeWithSpace, \n", encoding="utf-8")

    recipes = recipe_db.parse_recipe_db(str(csv_path), food_db={})
    assert "EmptyRecipe" in recipes
    assert len(recipes["EmptyRecipe"].ingredients) == 0
    assert "RecipeWithSpace" in recipes
    assert len(recipes["RecipeWithSpace"].ingredients) == 0


def test_parse_recipe_db_malformed_quantity_values(tmp_path: Path) -> None:
    """Test that malformed quantity values are handled gracefully."""
    csv_path = tmp_path / "recipes.csv"
    csv_path.write_text(
        "name,ingredients\n"
        "ValidRecipe,Water:100\n"
        "InvalidQuantity1,Water:not_a_number\n"
        "InvalidQuantity2,Water:abc:123\n"
        "MultipleInvalid,Water:invalid;Salt:50\n",
        encoding="utf-8",
    )

    recipes = recipe_db.parse_recipe_db(str(csv_path), food_db={})
    assert "ValidRecipe" in recipes
    assert recipes["ValidRecipe"].ingredients["Water"] == 100.0

    # Invalid quantities should be skipped (not raise ValueError)
    assert "InvalidQuantity1" in recipes
    assert len(recipes["InvalidQuantity1"].ingredients) == 0

    assert "InvalidQuantity2" in recipes
    assert len(recipes["InvalidQuantity2"].ingredients) == 0

    assert "MultipleInvalid" in recipes
    # Only valid quantity (Salt:50) should be parsed
    assert "Salt" in recipes["MultipleInvalid"].ingredients
    assert recipes["MultipleInvalid"].ingredients["Salt"] == 50.0


def test_parse_recipe_db_unicode_and_special_characters(tmp_path: Path) -> None:
    """Test that Unicode and special characters in recipe names are parsed correctly."""
    csv_path = tmp_path / "recipes.csv"
    csv_path.write_text(
        "name,ingredients\n"
        "Суп с лапшой,Water:200\n"
        "Risotto ai Funghi,Water:150\n"
        "Recipe with Spaces & Symbols!,Water:100\n"
        "Recipe@#$%^&*(),Water:50\n",
        encoding="utf-8",
    )

    recipes = recipe_db.parse_recipe_db(str(csv_path), food_db={})
    assert "Суп с лапшой" in recipes
    assert recipes["Суп с лапшой"].ingredients["Water"] == 200.0

    assert "Risotto ai Funghi" in recipes
    assert recipes["Risotto ai Funghi"].ingredients["Water"] == 150.0

    assert "Recipe with Spaces & Symbols!" in recipes
    assert recipes["Recipe with Spaces & Symbols!"].ingredients["Water"] == 100.0

    assert "Recipe@#$%^&*()" in recipes
    assert recipes["Recipe@#$%^&*()"].ingredients["Water"] == 50.0


def test_parse_recipe_db_missing_fields(tmp_path: Path) -> None:
    """Test that recipes with missing fields are handled properly."""
    csv_path = tmp_path / "recipes.csv"
    csv_path.write_text(
        "name,ingredients,flags\n"
        "CompleteRecipe,Water:100,flag1\n"
        "NoFlags,Water:200,\n"
        "NoIngredients,,\n",
        encoding="utf-8",
    )

    recipes = recipe_db.parse_recipe_db(str(csv_path), food_db={})
    assert "CompleteRecipe" in recipes
    assert recipes["CompleteRecipe"].ingredients["Water"] == 100.0
    assert "flag1" in recipes["CompleteRecipe"].flags

    assert "NoFlags" in recipes
    assert recipes["NoFlags"].ingredients["Water"] == 200.0
    assert len(recipes["NoFlags"].flags) == 0

    assert "NoIngredients" in recipes
    assert len(recipes["NoIngredients"].ingredients) == 0

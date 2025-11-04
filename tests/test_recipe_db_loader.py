from pathlib import Path

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

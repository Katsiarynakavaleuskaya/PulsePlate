from pathlib import Path

from core import recipe_db


def test_load_recipe_db_defaults(tmp_path: Path) -> None:
    csv_path = tmp_path / "recipes.csv"
    csv_path.write_text("name,ingredients\nSoup,Water:100\n", encoding="utf-8")

    recipes = recipe_db.parse_recipe_db(csv_path)
    assert "Soup" in recipes
    assert recipes["Soup"].ingredients["Water"] == 100.0

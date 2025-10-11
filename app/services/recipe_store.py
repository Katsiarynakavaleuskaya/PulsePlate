"""
RU: Доступ к RecipeDB (SQLite) — поиск и карточка.
EN: Access to RecipeDB (SQLite) — search and details.
"""

from pathlib import Path
import sqlite3


DB = Path("data/recipes.sqlite")


def _con():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def search_recipes(query: str, limit: int = 20, offset: int = 0) -> list[dict]:
    # Handle empty or wildcard queries for FTS
    if not query or query == "*":
        sql = """
          SELECT r.recipe_id, r.title, r.kcal_per_serv, r.tags_json
          FROM recipes r
          LIMIT ? OFFSET ?
        """
        query_params = [limit, offset]
    else:
        sql = """
          SELECT r.recipe_id, r.title, r.kcal_per_serv, r.tags_json
          FROM recipes r
          JOIN recipes_fts f ON f.rowid = r.rowid
          WHERE f.title MATCH ?
          LIMIT ? OFFSET ?
        """
        query_params = [query, limit, offset]  # type: ignore[list-item]

    with _con() as con:
        rows = con.execute(sql, query_params).fetchall()
    return [dict(r) for r in rows]


def get_recipe(recipe_id: str) -> dict | None:
    with _con() as con:
        r = con.execute("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,)).fetchone()
    return dict(r) if r else None

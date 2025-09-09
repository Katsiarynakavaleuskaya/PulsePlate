# -*- coding: utf-8 -*-
"""
RU: Доступ к RecipeDB (SQLite) — поиск и карточка.
EN: Access to RecipeDB (SQLite) — search and details.
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB = Path("data/recipes.sqlite")


def _con():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def search_recipes(query: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    sql = """
      SELECT r.recipe_id, r.title, r.kcal_per_serv, r.tags_json
      FROM recipes r
      JOIN recipes_fts f ON f.rowid = r.rowid
      WHERE f.title MATCH ?
      LIMIT ? OFFSET ?
    """
    params = [query or "*", limit, offset]
    with _con() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_recipe(recipe_id: str) -> Optional[Dict]:
    with _con() as con:
        r = con.execute(
            "SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,)
        ).fetchone()
    return dict(r) if r else None

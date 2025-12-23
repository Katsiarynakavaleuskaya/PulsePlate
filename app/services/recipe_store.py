# -*- coding: utf-8 -*-
"""
RU: Доступ к RecipeDB (SQLite) — поиск и карточка.
EN: Access to RecipeDB (SQLite) — search and details.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB = Path("data/recipes.sqlite")

# Legacy: tests expect module-level connection cache
_con: Optional[sqlite3.Connection] = None


def _get_con() -> sqlite3.Connection:
    """RU: Ленивая инициализация соединения (кэш).
    EN: Lazy cached connection initializer.
    """
    global _con

    # Support both legacy test mocking (function) and new caching (variable)
    if callable(_con):
        return _con()  # type: ignore[no-any-return]

    if _con is None:
        con = sqlite3.connect(DB)
        con.row_factory = sqlite3.Row
        _con = con

    return _con


def search_recipes(query: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    # Handle empty or wildcard queries for FTS
    if not query or query == "*":
        sql = """
          SELECT r.recipe_id, r.title, r.kcal_per_serv, r.tags_json
          FROM recipes r
          LIMIT ? OFFSET ?
        """
        params = [limit, offset]
    else:
        sql = """
          SELECT r.recipe_id, r.title, r.kcal_per_serv, r.tags_json
          FROM recipes r
          JOIN recipes_fts f ON f.rowid = r.rowid
          WHERE f.title MATCH ?
          LIMIT ? OFFSET ?
        """
        params = [query, limit, offset]  # type: ignore

    con = _get_con()
    rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_recipe(recipe_id: str) -> Optional[Dict]:
    con = _get_con()
    r = con.execute("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,)).fetchone()
    return dict(r) if r else None

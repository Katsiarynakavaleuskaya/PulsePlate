# -*- coding: utf-8 -*-
"""
RU: Доступ к RecipeDB (SQLite) — поиск и карточка.
EN: Access to RecipeDB (SQLite) — search and details.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


def _validate_db_path(path: Path, source: str) -> Path:
    resolved = path.expanduser()
    if resolved.exists():
        if resolved.is_dir():
            raise ValueError(f"{source} points to a directory: '{resolved}'.")
        if not os.access(resolved, os.R_OK | os.W_OK):
            raise PermissionError(
                f"{source} is not readable/writable: '{resolved}'. Check file permissions."
            )
        if not os.access(resolved.parent, os.W_OK):
            raise PermissionError(
                f"{source} is not writable: directory '{resolved.parent}' blocks access to '{resolved}'."
            )
        return resolved

    if not resolved.parent.exists():
        raise FileNotFoundError(
            f"{source} is invalid: parent directory '{resolved.parent}' does not exist for '{resolved}'."
        )
    if not os.access(resolved.parent, os.W_OK):
        raise PermissionError(
            f"{source} is invalid: parent directory '{resolved.parent}' is not writable for '{resolved}'."
        )
    raise FileNotFoundError(
        f"{source} does not exist: '{resolved}'. Create the database or update RECIPE_DB_PATH."
    )


def _resolve_db_path() -> Path:
    if "RECIPE_DB_PATH" in os.environ:
        env_value = os.getenv("RECIPE_DB_PATH")
        if not env_value:
            raise ValueError("RECIPE_DB_PATH is set but empty; provide a valid SQLite file path.")
        return _validate_db_path(Path(env_value), f"RECIPE_DB_PATH '{env_value}'")
    return _validate_db_path(Path("data/recipes.sqlite"), "default recipe DB path")


DB_PATH: Path = _resolve_db_path()


def _con() -> sqlite3.Connection:
    """RU: Создаёт соединение SQLite (контекст-менеджер).
    EN: Creates SQLite connection (context manager).
    """
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


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

    with _con() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_recipe(recipe_id: str) -> Optional[Dict]:
    with _con() as con:
        r = con.execute("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,)).fetchone()
    return dict(r) if r else None

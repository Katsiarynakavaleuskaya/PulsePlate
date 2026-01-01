# -*- coding: utf-8 -*-
"""
RU: Доступ к RecipeDB (SQLite) — поиск и карточка.
EN: Access to RecipeDB (SQLite) — search and details.
"""

from __future__ import annotations

from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path
from typing import Dict, Iterator, List, Optional


def _validate_db_path(path: Path, source: str) -> Path:
    """RU: Валидация пути к базе данных рецептов.

    EN: Validate recipe database path.

    Allows missing database files (SQLite will create them), but validates
    that the parent directory exists and is writable.

    Args:
        path: Path to validate.
        source: Description of the path source (for error messages).

    Returns:
        Resolved absolute path.

    Raises:
        ValueError: If path points to a directory.
        PermissionError: If parent directory is not writable or existing file is not accessible.
        FileNotFoundError: If parent directory does not exist.
    """
    resolved = path.expanduser()

    # If file exists, validate it's a file and accessible
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

    # File doesn't exist - validate parent directory (SQLite will create the file)
    if not resolved.parent.exists():
        raise FileNotFoundError(
            f"{source} is invalid: parent directory '{resolved.parent}' does not exist for '{resolved}'."
        )
    if not os.access(resolved.parent, os.W_OK):
        raise PermissionError(
            f"{source} is invalid: parent directory '{resolved.parent}' is not writable for '{resolved}'."
        )

    # Path is valid - SQLite will create the file when connecting
    return resolved


def _resolve_db_path() -> Path:
    """RU: Ленивое разрешение пути к базе данных рецептов.

    EN: Lazy resolution of recipe database path.

    This function is called only when the database is actually needed,
    not at module import time, to allow graceful degradation when the
    recipes database is unavailable.
    """
    if "RECIPE_DB_PATH" in os.environ:
        env_value = os.getenv("RECIPE_DB_PATH")
        if not env_value:
            raise ValueError("RECIPE_DB_PATH is set but empty; provide a valid SQLite file path.")
        return _validate_db_path(Path(env_value), f"RECIPE_DB_PATH '{env_value}'")
    return _validate_db_path(Path("data/recipes.sqlite"), "default recipe DB path")


# Lazy path resolution: only resolve when database is actually accessed
_DB_PATH: Path | None = None


def _get_db_path() -> Path:
    """RU: Получить путь к базе данных (ленивая инициализация).

    EN: Get database path (lazy initialization).
    """
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = _resolve_db_path()
    return _DB_PATH


@contextmanager
def _con() -> Iterator[sqlite3.Connection]:
    """RU: Создаёт соединение SQLite (контекст-менеджер; всегда закрывает соединение).
    EN: Creates SQLite connection (context manager; always closes connection).

    Raises:
        FileNotFoundError: If the database file does not exist and cannot be created.
        PermissionError: If the database file or directory is not accessible.
    """
    db_path = _get_db_path()
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def search_recipes(query: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    """RU: Поиск рецептов в базе данных.

    EN: Search recipes in the database.

    Returns:
        List of recipe dictionaries. Returns empty list if database is unavailable.
    """
    try:
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
    except (FileNotFoundError, PermissionError, sqlite3.Error) as e:
        # Gracefully degrade when database is unavailable
        # Log the error but don't crash the application
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Recipe database unavailable: %s. Returning empty results.", e)
        return []


def get_recipe(recipe_id: str) -> Optional[Dict]:
    """RU: Получить рецепт по ID.

    EN: Get recipe by ID.

    Returns:
        Recipe dictionary if found, None if not found or database unavailable.
    """
    try:
        with _con() as con:
            r = con.execute("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,)).fetchone()
        return dict(r) if r else None
    except (FileNotFoundError, PermissionError, sqlite3.Error) as e:
        # Gracefully degrade when database is unavailable
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Recipe database unavailable: %s. Recipe '%s' not found.", e, recipe_id)
        return None

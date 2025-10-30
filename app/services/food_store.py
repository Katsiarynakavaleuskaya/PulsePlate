# -*- coding: utf-8 -*-
"""FoodDB access service with FTS and alias expansion.

RU: Сервис доступа к FoodDB (SQLite) с FTS и алиасами.
EN: Access to FoodDB (SQLite) with FTS and alias expansion.
"""

import sqlite3
from pathlib import Path
import csv
import logging
import os
from typing import Dict, List, Optional

DB_PATH: Path = Path("data/food.sqlite")
MAX_LIMIT: int = 100

DEFAULT_ALIASES: Dict[str, List[str]] = {
    # RU/EN/ES базовые соответствия; расширяй из своего alias CSV
    "йогурт": ["yogurt", "yoghurt"],
    "масло оливковое": ["olive oil", "aceite de oliva"],
    "творог": ["cottage cheese", "queso cottage"],
}

logger = logging.getLogger(__name__)


def _load_aliases_csv(csv_path: Path) -> Dict[str, List[str]]:
    """Load aliases from CSV file with columns: primary, aliases (comma separated)."""
    aliases: Dict[str, List[str]] = {}
    if not csv_path.exists():
        return aliases
    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                primary = (row.get("primary") or "").strip().lower()
                alias_str = (row.get("aliases") or "").strip()
                if not primary:
                    continue
                alias_list = [a.strip().lower() for a in alias_str.split(",") if a.strip()]
                if primary in aliases:
                    aliases[primary] = sorted(list(set(aliases[primary] + alias_list)))
                else:
                    aliases[primary] = alias_list
    except (csv.Error, UnicodeDecodeError, OSError) as exc:
        env = os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "production"
        # Log detailed info and fail fast in non-production to avoid hiding config issues.
        if env.lower() != "production":
            logger.error("Error reading/parsing aliases CSV '%s': %s", csv_path, exc, exc_info=True)
            raise
        # In production, log concise error and continue with defaults
        logger.error("Error reading/parsing aliases CSV '%s': %s", csv_path, exc)
        return {}
    return aliases


# Lazy alias cache to avoid file I/O at import time
_ALIASES_CACHE: Optional[Dict[str, List[str]]] = None


def get_aliases() -> Dict[str, List[str]]:
    """Return merged alias mapping (defaults + CSV), loading lazily on first use."""
    global _ALIASES_CACHE
    if _ALIASES_CACHE is None:
        csv_aliases = _load_aliases_csv(Path("data/food_aliases.csv"))
        _ALIASES_CACHE = {**DEFAULT_ALIASES, **csv_aliases}
    return _ALIASES_CACHE


def expand_query(q: str) -> List[str]:
    """Expand a query using alias mappings; returns unique lowercase terms."""
    ql = (q or "").strip().lower()
    if not ql:
        return []
    terms = {ql}
    for k, vs in get_aliases().items():
        if ql == k or ql in vs:
            terms.update([k, *vs])
    return list(terms)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def search_foods(query: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    """Search foods via FTS; parameters are safely bound using placeholders."""
    # Defensive bounds and type validation for pagination
    if not isinstance(limit, int):
        try:
            limit = int(limit)  # noqa: PLR2004 - defensive conversion needed for runtime validation
        except (TypeError, ValueError):
            raise ValueError("limit must be an integer")
    if not isinstance(offset, int):
        try:
            offset = int(
                offset
            )  # noqa: PLR2004 - defensive conversion needed for runtime validation
        except (TypeError, ValueError):
            raise ValueError("offset must be an integer")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    limit = min(limit, MAX_LIMIT)
    if offset < 0:
        raise ValueError("offset must be >= 0")
    terms = expand_query(query) if query else []
    params: list = []
    if terms:
        # nosec B608: The query uses parameter placeholders for all user inputs;
        # only the number of placeholders is constructed dynamically.
        sql = (
            """
          SELECT f.id, f.canonical_name, f.kcal, f.protein_g, f.fat_g, f.carbs_g
          FROM foods f
          JOIN foods_fts ff ON ff.rowid = f.rowid
          WHERE """
            + " OR ".join(["ff.canonical_name MATCH ?"] * len(terms))  # nosec B608
            + " LIMIT ? OFFSET ?"
        )
        params = [*terms, limit, offset]
    else:
        sql = (
            "SELECT id, canonical_name, kcal, protein_g, fat_g, carbs_g FROM foods LIMIT ? OFFSET ?"
        )
        params = [limit, offset]
    with _connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_food(food_id: str) -> Optional[Dict]:
    """Return a single food by id or None if not found."""
    with _connect() as con:
        row = con.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
    return dict(row) if row else None


def nutrients_for(ings: List[Dict]) -> Dict[str, float]:
    """RU: Наивный сумматор нутриентов; EN: naive aggregator."""
    keys = [
        "kcal",
        "protein_g",
        "fat_g",
        "carbs_g",
        "Fe_mg",
        "Ca_mg",
        "K_mg",
        "Mg_mg",
        "VitD_IU",
        "B12_ug",
        "Folate_ug",
        "Iodine_ug",
    ]
    total = {k: 0.0 for k in keys}
    for ing in ings:
        food = get_food(ing["food_id"])
        if not food:
            continue
        ratio = float(ing["grams"]) / float(food.get("per_g", 100.0))
        for k in keys:
            total[k] += float(food.get(k, 0.0)) * ratio
    return total

# -*- coding: utf-8 -*-
"""FoodDB access service with FTS and alias expansion.

RU: Сервис доступа к FoodDB (SQLite) с FTS и алиасами.
EN: Access to FoodDB (SQLite) with FTS and alias expansion.
"""

import sqlite3
from pathlib import Path
import csv
from typing import Dict, List, Optional

DB_PATH = Path("data/food.sqlite")
MAX_LIMIT = 100

DEFAULT_ALIASES = {
    # RU/EN/ES базовые соответствия; расширяй из своего alias CSV
    "йогурт": ["yogurt", "yoghurt"],
    "масло оливковое": ["olive oil", "aceite de oliva"],
    "творог": ["cottage cheese", "queso cottage"],
}


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
    except Exception:
        # Graceful fallback to defaults on any CSV error
        return {}
    return aliases


# Load aliases once at import, merging CSV over defaults
_CSV_ALIASES = _load_aliases_csv(Path("data/food_aliases.csv"))
ALIASES: Dict[str, List[str]] = {**DEFAULT_ALIASES, **_CSV_ALIASES}


def expand_query(q: str) -> List[str]:
    """Expand a query using alias mappings; returns unique lowercase terms."""
    ql = (q or "").strip().lower()
    if not ql:
        return []
    terms = set([ql])
    for k, vs in ALIASES.items():
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
    try:
        limit = int(limit)
        offset = int(offset)
    except (TypeError, ValueError):
        raise ValueError("limit and offset must be integers")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
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
            + " OR ".join(["ff.canonical_name MATCH ?"] * len(terms))
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

# -*- coding: utf-8 -*-
"""
RU: Сервис доступа к FoodDB (SQLite) с FTS и алиасами.
EN: Access to FoodDB (SQLite) with FTS and alias expansion.
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path("data/food.sqlite")

ALIASES = {
    # RU/EN/ES базовые соответствия; расширяй из своего alias CSV
    "йогурт": ["yogurt", "yoghurt"],
    "масло оливковое": ["olive oil", "aceite de oliva"],
    "творог": ["cottage cheese", "queso cottage"],
}


def expand_query(q: str) -> List[str]:
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
    terms = expand_query(query) if query else []
    params: list = []
    if terms:
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
            "SELECT id, canonical_name, kcal, protein_g, fat_g, carbs_g "
            "FROM foods LIMIT ? OFFSET ?"
        )
        params = [limit, offset]
    with _connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_food(food_id: str) -> Optional[Dict]:
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

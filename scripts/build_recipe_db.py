# -*- coding: utf-8 -*-
"""
RU: Сборка RecipeDB из CSV → recipes.sqlite/parquet с расчётом на порцию.
EN: Build RecipeDB from CSV → recipes.sqlite/parquet with per-serving compute.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

FOOD_DB = Path("data/food.sqlite")
SRC_CSV = Path("data/recipes_new.csv")  # твой файл
OUT_PARQUET = Path("data/recipes.parquet")
OUT_SQLITE = Path("data/recipes.sqlite")

KEYS = [
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


def _connect_food():
    con = sqlite3.connect(FOOD_DB)
    con.row_factory = sqlite3.Row
    return con


def _get_food(food_id: str) -> dict | None:
    with _connect_food() as con:
        row = con.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
    return dict(row) if row else None


def _sum_nutrients(ingredients: list[dict]) -> dict:
    total = {k: 0.0 for k in KEYS}
    for ing in ingredients:
        food = _get_food(ing["food_id"])
        if not food:
            continue
        ratio = float(ing["grams"]) / float(food.get("per_g", 100.0))
        for k in KEYS:
            total[k] += float(food.get(k, 0.0)) * ratio
    return total


def _sum_cost(ingredients: list[dict]) -> float:
    cost = 0.0
    for ing in ingredients:
        food = _get_food(ing["food_id"])
        if not food:
            continue
        price100 = float(food.get("price_per_100g", 0.0))
        cost += price100 * (float(ing["grams"]) / 100.0)
    return cost


def main():
    df = pd.read_csv(SRC_CSV)
    print(f"Columns in CSV: {list(df.columns)}")
    print(f"First row: {df.iloc[0].to_dict()}")
    # Ожидаемые поля: recipe_id,title,locale,servings,ingredients_json,
    # steps_json,tags_json,allergens_json
    out_rows = []
    today = date.today().isoformat()
    for _, r in df.iterrows():
        # Парсим ingredients из строки формата "Продукт1:вес1;Продукт2:вес2"
        ingredients_str = r["ingredients"]
        ingredients = []
        for item in ingredients_str.split(";"):
            if ":" in item:
                name, grams = item.split(":", 1)
                # Ищем food_id по имени (упрощенная логика)
                food_id = name.lower().replace(" ", "_").replace("ё", "e")
                ingredients.append({"food_id": food_id, "grams": float(grams)})
        total_g = float(sum(i["grams"] for i in ingredients))
        tot = _sum_nutrients(ingredients)
        serv = 2  # По умолчанию 2 порции
        per_serv = (
            {k: (v / serv) for k, v in tot.items()} if serv else {k: 0.0 for k in KEYS}
        )
        cost_total = _sum_cost(ingredients)
        cost_per_serv = cost_total / serv if serv else 0.0

        # Парсим теги
        tags = r.get("tags", "").split(";") if r.get("tags") else []

        out_rows.append(
            {
                "recipe_id": r["name"],  # Используем name как recipe_id
                "title": r["name"].replace("_", " ").title(),
                "locale": "en",
                "servings": serv,
                "yield_total_g": total_g,
                "ingredients_json": json.dumps(ingredients, ensure_ascii=False),
                "steps_json": "[]",
                "tags_json": json.dumps(tags),
                "allergens_json": r.get("allergens_json", "[]"),
                "cost_total": round(cost_total, 2),
                "cost_per_serv": round(cost_per_serv, 2),
                "nutrients_per_serv_json": json.dumps(per_serv, ensure_ascii=False),
                "source": r.get("source", "internal"),
                "version_date": r.get("version_date", today),
                "kcal_per_serv": per_serv["kcal"],
            }
        )
    out_df = pd.DataFrame(out_rows)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(OUT_PARQUET, index=False)
    con = sqlite3.connect(OUT_SQLITE)
    out_df.to_sql("recipes", con, if_exists="replace", index=False)
    con.execute("DROP TABLE IF EXISTS recipes_fts;")
    con.execute(
        "CREATE VIRTUAL TABLE recipes_fts USING fts5("
        "title, content='recipes', content_rowid='rowid');"
    )
    con.execute("INSERT INTO recipes_fts(rowid,title) SELECT rowid,title FROM recipes;")
    con.commit()
    con.close()
    filled = (out_df["kcal_per_serv"] > 0).mean()
    print(f"Built {len(out_df)} recipes; kcal coverage per_serv: {filled:.0%}")


if __name__ == "__main__":
    main()

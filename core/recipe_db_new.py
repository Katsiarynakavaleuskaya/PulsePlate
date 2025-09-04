"""
Recipe Database Parser

RU: Парсер базы данных рецептов из CSV.
EN: Parser for recipe database from CSV.

This module provides functionality to parse the recipe database CSV file
and provide recipe scaling functionality.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from typing import Dict, List

from .food_db_new import MICRO_KEYS, FoodDB
from .meal_i18n import Language, translate_recipe


@dataclass
class Recipe:
    name: str
    meal: str
    ingredients: Dict[str, float]  # grams
    tags: List[str]

@dataclass
class Meal:
    title: str
    title_translated: str
    grams: Dict[str, float]
    kcal: int
    macros: Dict[str, float]
    micros: Dict[str, float]

class RecipeDB:
    def __init__(self, path: str, fooddb: FoodDB) -> None:
        self.fooddb = fooddb
        self.recipes: List[Recipe] = []
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ings = {}
                for pair in row["ingredients"].split(";"):
                    name, grams = pair.split(":")
                    ings[name.strip()] = float(grams)
                tags = [x.strip() for x in (row.get("tags","") or "").split(";") if x.strip()]
                self.recipes.append(Recipe(row["name"], row["meal"], ings, tags))

    def pick_base_recipe(self, diet_flags: List[str], meal_index: int) -> Recipe:
        # breakfast/lunch/dinner/snack by index
        meal_map = ["breakfast","lunch","dinner","snack"]
        target = meal_map[meal_index % len(meal_map)]
        candidates = [r for r in self.recipes if r.meal == target and self._compatible(r.tags, diet_flags)]
        if not candidates:
            # fallback: любой с совместимыми флагами
            candidates = [r for r in self.recipes if self._compatible(r.tags, diet_flags)]
        return random.choice(candidates) if candidates else None

    def _compatible(self, recipe_flags: List[str], diet_flags: List[str]) -> bool:
        if "VEG" in diet_flags and "OMNI" in recipe_flags:
            return False
        if "PESC" in diet_flags and "OMNI" in recipe_flags:
            return False
        if "GF" in diet_flags and "GF" not in recipe_flags:
            return False
        return True

    def _nutrition_for(self, grams_map: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        kcal = 0.0
        macros = {"protein_g":0.0,"fat_g":0.0,"carbs_g":0.0,"fiber_g":0.0}
        micros = {k:0.0 for k in MICRO_KEYS}
        for name, g in grams_map.items():
            fi = self.fooddb.get_food(name)
            mul = g / fi.per_g
            kcal += (fi.protein_g*4 + fi.carbs_g*4 + fi.fat_g*9) * mul
            macros["protein_g"] += fi.protein_g * mul
            macros["fat_g"]     += fi.fat_g     * mul
            macros["carbs_g"]   += fi.carbs_g   * mul
            macros["fiber_g"]   += fi.fiber_g   * mul
            for mk in MICRO_KEYS:
                micros[mk] += fi.micros.get(mk,0.0) * mul
        return {"kcal":kcal, "macros":macros, "micros":micros}

    def scale_recipe_to_kcal(self, recipe: Recipe, kcal_goal: int, lang: Language = "en", prefer_fiber: bool=True) -> Meal:
        """RU: Масштабируем рецепт под цель kcal с мягкой коррекцией по клетчатке.
           EN: Scale recipe to kcal target with soft fiber preference.
        """
        grams = dict(recipe.ingredients)
        base = self._nutrition_for(grams)
        if base["kcal"] <= 0:
            alpha = 1.0
        else:
            alpha = kcal_goal / base["kcal"]
        # первичное масштабирование
        grams = {k: max(10.0, v*alpha) for k, v in grams.items()}
        # лёгкая рандомизация (±5%) для вариативности
        grams = {k: v * (0.95 + 0.10 * random.random()) for k, v in grams.items()}
        nut = self._nutrition_for(grams)

        # если сильно промахнулись по цели >5%, подправим ещё раз
        if abs(nut["kcal"] - kcal_goal) / max(1,kcal_goal) > 0.05:
            alpha2 = kcal_goal / max(1.0, nut["kcal"])
            grams = {k: v*alpha2 for k, v in grams.items()}
            nut = self._nutrition_for(grams)

        # Get translated recipe title
        translated_title = translate_recipe(lang, recipe.name)

        meal = Meal(
            title=recipe.name,
            title_translated=translated_title,
            grams={k: round(v,1) for k,v in grams.items()},
            kcal=int(round(nut["kcal"])),
            macros={k: round(v,1) for k,v in nut["macros"].items()},
            micros={k: round(v,1) for k,v in nut["micros"].items()},
        )
        return meal

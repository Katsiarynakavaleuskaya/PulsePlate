"""Ingredient Extractor.

RU: Извлечение ингредиентов из plan_data.
EN: Extract ingredients from plan_data.

This module safely extracts ingredients from the weekly plan structure.
"""

import math
from typing import Any, Dict, List, TypedDict


class RawIngredient(TypedDict):
    """Raw ingredient extracted from plan_data."""

    key: str
    quantity: float
    unit: str
    recipe_ref: str


def extract_ingredients_from_plan(plan_data: Dict[str, Any]) -> List[RawIngredient]:
    """Extract all ingredients from plan_data.

    Args:
        plan_data: Weekly plan data with daily_menus structure

    Returns:
        List of raw ingredients with quantities and references

    Expected structure:
        plan_data["daily_menus"][*]["meals"][*]["grams"]
        where grams is Dict[str, float] with all quantities in grams
    """
    ingredients: List[RawIngredient] = []

    daily_menus = plan_data.get("daily_menus", [])
    if not isinstance(daily_menus, list):
        return ingredients

    for day_idx, day in enumerate(daily_menus):
        if not isinstance(day, dict):
            continue

        meals = day.get("meals", [])
        if not isinstance(meals, list):
            continue

        for meal_idx, meal in enumerate(meals):
            if not isinstance(meal, dict):
                continue

            # Use meal title as reference, fallback to indexed key
            raw_meal_title = meal.get("title")
            if isinstance(raw_meal_title, str):
                normalized_title = raw_meal_title.strip()
                meal_key = normalized_title if normalized_title else f"meal_{day_idx}_{meal_idx}"
            else:
                meal_key = f"meal_{day_idx}_{meal_idx}"

            # Extract grams dict (all quantities are in grams)
            grams_dict = meal.get("grams", {})
            if not isinstance(grams_dict, dict):
                continue

            # Iterate keys in sorted order for deterministic extraction results.
            for ingredient_key in sorted(k for k in grams_dict if isinstance(k, str)):
                # Skip non-string keys
                quantity = grams_dict[ingredient_key]

                # Convert quantity to float, skip invalid values
                try:
                    qty = float(quantity)
                except (TypeError, ValueError):
                    continue

                # Skip NaN/inf values
                if not math.isfinite(qty):
                    continue

                # Skip zero/negative quantities
                if qty <= 0:
                    continue

                ingredients.append(
                    {
                        "key": ingredient_key,
                        "quantity": qty,
                        "unit": "g",  # All quantities from plan_data are in grams
                        "recipe_ref": meal_key,
                    }
                )

    return ingredients

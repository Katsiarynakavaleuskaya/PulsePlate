"""
Recipe Database Parser

RU: Парсер базы данных рецептов из CSV.
EN: Parser for recipe database from CSV.

This module provides functionality to parse the recipe database CSV file
and calculate aggregated nutrient information.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Dict, Set

from .food_db import FoodItem, parse_food_db


@dataclass
class Recipe:
    """
    RU: Рецепт с ингредиентами.
    EN: Recipe with ingredients.
    """

    name: str
    ingredients: Dict[str, float]  # ingredient_name: amount_in_grams
    flags: Set[str]


def parse_recipe_db(
    csv_path: str = "data/recipes.csv", food_db: Dict[str, FoodItem] = None
) -> Dict[str, Recipe]:
    """
    RU: Парсит CSV файл базы данных рецептов.
    EN: Parse recipe database CSV file.

    Args:
        csv_path: Path to the recipe database CSV file
        food_db: Food database for nutrient calculations (will be loaded if None)

    Returns:
        Dictionary mapping recipe names to Recipe objects
    """
    if food_db is None:
        food_db = parse_food_db()

    recipe_db = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse ingredients
            ingredients_str = row["ingredients"]
            ingredients = {}

            # Parse "Food:grams;Food:grams" format
            if ingredients_str:
                for ingredient_part in ingredients_str.split(";"):
                    if ":" in ingredient_part:
                        name, amount_str = ingredient_part.split(":", 1)
                        try:
                            amount = float(amount_str)
                            ingredients[name.strip()] = amount
                        except ValueError:
                            # Skip malformed entries
                            continue

            # Parse flags
            flags_str = row.get("flags", "")
            flags = set(flags_str.split(",")) if flags_str else set()

            # Create Recipe
            recipe = Recipe(name=row["name"], ingredients=ingredients, flags=flags)

            recipe_db[row["name"]] = recipe

    return recipe_db


def calculate_recipe_nutrients(
    recipe: Recipe, food_db: Dict[str, FoodItem]
) -> Dict[str, float]:
    """
    RU: Рассчитывает питательную ценность рецепта.
    EN: Calculate nutritional value of a recipe.

    Args:
        recipe: Recipe to analyze
        food_db: Food database for nutrient lookup

    Returns:
        Dictionary mapping nutrient names to amounts
    """
    total_nutrients = {}

    for ingredient_name, amount_g in recipe.ingredients.items():
        if ingredient_name in food_db:
            food_item = food_db[ingredient_name]

            # Add nutrients from this ingredient
            nutrients = [
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "Fe_mg",
                "Ca_mg",
                "VitD_IU",
                "B12_ug",
                "Folate_ug",
                "Iodine_ug",
                "K_mg",
                "Mg_mg",
            ]

            for nutrient in nutrients:
                nutrient_amount = food_item.get_nutrient_amount(nutrient, amount_g)
                total_nutrients[nutrient] = (
                    total_nutrients.get(nutrient, 0) + nutrient_amount
                )

    return total_nutrients


def scale_recipe_to_kcal(
    recipe: Recipe,
    kcal_goal: float,
    food_db: Dict[str, FoodItem],
    prefer_fiber: bool = True,
) -> Recipe:
    """
    RU: Масштабирует рецепт до целевого количества калорий.
    EN: Scale recipe to target calorie amount.

    Args:
        recipe: Recipe to scale
        kcal_goal: Target calorie amount
        food_db: Food database for calculations
        prefer_fiber: Whether to prefer higher fiber options when scaling

    Returns:
        Scaled recipe
    """
    # Calculate current calories
    current_nutrients = calculate_recipe_nutrients(recipe, food_db)
    current_kcal = (
        current_nutrients.get("protein_g", 0) * 4
        + current_nutrients.get("carbs_g", 0) * 4
        + current_nutrients.get("fat_g", 0) * 9
    )

    if current_kcal <= 0:
        # Cannot scale, return original
        return recipe

    # Calculate scaling factor
    scale_factor = kcal_goal / current_kcal

    # Scale ingredients
    scaled_ingredients = {}
    for ingredient_name, amount in recipe.ingredients.items():
        scaled_ingredients[ingredient_name] = amount * scale_factor

    # Create scaled recipe
    return Recipe(name=recipe.name, ingredients=scaled_ingredients, flags=recipe.flags)

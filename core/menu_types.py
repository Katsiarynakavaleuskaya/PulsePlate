"""
Shared dataclasses for menu generation modules.

These classes are defined in a dedicated module so they can be imported
by both `core.menu_engine` and related helpers without creating duplicate
class identities when modules are reloaded during tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .targets import NutritionTargets


@dataclass
class FoodItem:
    """
    RU: Элемент базы данных продуктов.
    EN: Food database item.
    """

    name: str
    nutrients_per_100g: Dict[str, float]  # Nutrient content per 100g
    cost_per_100g: float  # Cost in local currency
    tags: List[str]  # VEG, GF, DAIRY_FREE, etc.
    availability_regions: List[str]  # BY, RU, etc.


@dataclass
class Recipe:
    """
    RU: Рецепт с ингредиентами и питательной ценностью.
    EN: Recipe with ingredients and nutritional value.
    """

    name: str
    ingredients: Dict[str, float]  # ingredient_name: amount_in_grams
    servings: int
    preparation_time_min: int
    difficulty: str  # easy, medium, hard
    tags: List[str]  # VEG, GF, DAIRY_FREE, LOW_COST
    instructions: List[str]

    def calculate_nutrients_per_serving(self, food_db: Dict[str, "FoodItem"]) -> Dict[str, float]:
        """Calculate nutrients per serving from ingredients.

        RU: Рассчитать нутриенты на порцию из ингредиентов.
        EN: Calculate nutrients per serving from ingredients.

        Args:
            food_db: Dictionary mapping ingredient names to FoodItem objects

        Returns:
            Dictionary mapping nutrient names to amounts per serving

        Raises:
            ValueError: If servings is <= 0
        """
        import logging

        logger = logging.getLogger(__name__)

        # Validate servings
        if self.servings <= 0:
            raise ValueError(
                f"Recipe servings must be > 0, got {self.servings}. "
                f"Recipe: {getattr(self, 'name', 'unknown')}"
            )

        total_nutrients: Dict[str, float] = {}

        for ingredient_name, amount_g in self.ingredients.items():
            if ingredient_name in food_db:
                food_item = food_db[ingredient_name]
                for nutrient, value_per_100g in food_item.nutrients_per_100g.items():
                    nutrient_amount = (value_per_100g * amount_g) / 100
                    total_nutrients[nutrient] = total_nutrients.get(nutrient, 0.0) + nutrient_amount
            else:
                # Log warning for missing ingredients
                recipe_id = getattr(self, "name", "unknown")
                logger.warning(
                    "Missing ingredient '%s' in food_db for recipe '%s'. "
                    "Skipping nutrient contribution from this ingredient.",
                    ingredient_name,
                    recipe_id,
                )

        # Divide by validated servings
        return {k: v / self.servings for k, v in total_nutrients.items()}


@dataclass
class DayMenu:
    """
    RU: Меню на один день с оценкой покрытия нутриентов.
    EN: Single day menu with nutrient coverage assessment.
    """

    date: str
    meals: List[Dict[str, Any]]  # List of meal objects
    total_nutrients: Dict[str, float]
    targets: "NutritionTargets"
    coverage: Dict[str, Any]
    recommendations: List[str]
    estimated_cost: float


@dataclass
class WeekMenu:
    """
    RU: Недельное меню с планом покупок.
    EN: Weekly menu with shopping plan.
    """

    week_start: str
    daily_menus: List[DayMenu]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]  # ingredient: total_amount_needed
    total_cost: float
    adherence_score: float  # How well it meets targets (0-100)


__all__ = ["FoodItem", "Recipe", "DayMenu", "WeekMenu"]

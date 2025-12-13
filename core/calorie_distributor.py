"""
Calorie Distribution - Meal Calorie Splitting Logic

RU: Модуль распределения калорий по приемам пищи.
EN: Module for distributing calories across meals.

This module provides functionality for splitting daily calorie targets
across different meals and snacks based on nutritional best practices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

MealName = Literal["breakfast", "lunch", "dinner", "snack"]


@dataclass
class MealCalories:
    """
    RU: Калории для одного приема пищи.
    EN: Calories for a single meal.
    """

    name: MealName
    kcal: int
    percentage: float


@dataclass
class DailyCalorieDistribution:
    """
    RU: Распределение калорий на день.
    EN: Daily calorie distribution.

    Note: This dataclass is intentionally mutable to support lazy caching
    via the _meal_lookup attribute for O(1) meal lookup performance.
    """

    total_kcal: int
    meals: List[MealCalories]

    def get_meal_kcal(self, meal_name: MealName) -> int:
        """Get calorie target for specific meal.

        Uses dict lookup for O(1) performance instead of linear search.
        Lazy initialization: _meal_lookup cache is created on first access.
        """
        # Create lookup dict on first access (lazy initialization)
        if not hasattr(self, "_meal_lookup"):
            self._meal_lookup = {meal.name: meal.kcal for meal in self.meals}
        return self._meal_lookup.get(meal_name, 0)


# Standard meal split percentages based on nutritional recommendations
# Breakfast: 25%, Lunch: 35% (largest meal), Dinner: 30%, Snack: 10%
DEFAULT_MEAL_SPLITS: Dict[MealName, float] = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.30,
    "snack": 0.10,
}

# Alternative splits for different eating patterns
INTERMITTENT_FASTING_SPLITS: Dict[MealName, float] = {
    "breakfast": 0.0,  # Skipped
    "lunch": 0.45,
    "dinner": 0.45,
    "snack": 0.10,
}

GRAZING_SPLITS: Dict[MealName, float] = {
    "breakfast": 0.20,
    "lunch": 0.30,
    "dinner": 0.30,
    "snack": 0.20,  # Larger snacks
}


def distribute_calories(
    total_kcal: int,
    meal_splits: Optional[Dict[MealName, float]] = None,
    num_meals: int = 4,
) -> DailyCalorieDistribution:
    """
    RU: Распределяет дневные калории по приемам пищи.
    EN: Distributes daily calories across meals.

    Args:
        total_kcal: Total daily calorie target
        meal_splits: Custom meal split percentages (defaults to DEFAULT_MEAL_SPLITS)
        num_meals: Number of meals (3 or 4)

    Returns:
        DailyCalorieDistribution with calories for each meal

    Examples:
        >>> dist = distribute_calories(2000)
        >>> dist.get_meal_kcal("breakfast")
        500
        >>> dist.get_meal_kcal("lunch")
        700
    """
    # Treat None or empty dict as "use defaults"
    if not meal_splits:
        meal_splits = DEFAULT_MEAL_SPLITS.copy()
    else:
        # Always copy to avoid modifying caller's dict
        meal_splits = dict(meal_splits)

    # Adjust for 3-meal pattern (no snack)
    if num_meals == 3 and "snack" in meal_splits:
        snack_pct = meal_splits.pop("snack")
        # Redistribute snack calories to dinner
        meal_splits["dinner"] = meal_splits.get("dinner", 0.0) + snack_pct

    # Validate splits sum to 1.0
    total_pct = sum(meal_splits.values())
    if total_pct <= 0:
        # Invalid split values (e.g., all zeros). Fall back to defaults.
        meal_splits = DEFAULT_MEAL_SPLITS.copy()
        total_pct = sum(meal_splits.values())
        # Re-apply 3-meal adjustment after fallback
        if num_meals == 3 and "snack" in meal_splits:
            snack_pct = meal_splits.pop("snack")
            meal_splits["dinner"] = meal_splits.get("dinner", 0.0) + snack_pct
            total_pct = sum(meal_splits.values())
    if abs(total_pct - 1.0) > 0.01:
        # Normalize if needed
        meal_splits = {k: v / total_pct for k, v in meal_splits.items()}

    # Calculate meal calories
    meals: List[MealCalories] = []
    allocated_kcal = 0

    for meal_name, percentage in meal_splits.items():
        kcal = int(round(total_kcal * percentage))
        meals.append(MealCalories(name=meal_name, kcal=kcal, percentage=percentage))
        allocated_kcal += kcal

    # Adjust last meal if rounding caused discrepancy
    if allocated_kcal != total_kcal and meals:
        diff = total_kcal - allocated_kcal
        meals[-1].kcal += diff

    return DailyCalorieDistribution(total_kcal=total_kcal, meals=meals)


def get_meal_split_list(
    total_kcal: int,
    meal_splits: Optional[Dict[MealName, float]] = None,
) -> List[int]:
    """
    RU: Возвращает список калорий для каждого приема пищи (legacy format).
    EN: Returns list of calories for each meal (legacy format).

    This function maintains compatibility with existing code that expects
    a list of integers [breakfast_kcal, lunch_kcal, dinner_kcal, snack_kcal].

    Args:
        total_kcal: Total daily calorie target
        meal_splits: Custom meal split percentages

    Returns:
        List of integers [breakfast, lunch, dinner, snack] calories

    Examples:
        >>> get_meal_split_list(2000)
        [500, 700, 600, 200]
    """
    if meal_splits is None:
        meal_splits = DEFAULT_MEAL_SPLITS

    # Use standard meal order
    meal_order: List[MealName] = ["breakfast", "lunch", "dinner", "snack"]

    kcal_list = []
    for meal_name in meal_order:
        if meal_name in meal_splits:
            kcal = int(round(total_kcal * meal_splits[meal_name]))
            kcal_list.append(kcal)
        else:
            kcal_list.append(0)

    return kcal_list


def apply_weekly_variation(
    base_kcal: int,
    day_index: int,
    variation_pct: float = 0.05,
) -> int:
    """
    RU: Применяет небольшую вариацию калорий для разнообразия в недельном плане.
    EN: Applies slight calorie variation for weekly plan diversity.

    Args:
        base_kcal: Base daily calorie target
        day_index: Day of week (0-6)
        variation_pct: Variation percentage (default 5%)

    Returns:
        Adjusted calorie target for the day

    Examples:
        >>> apply_weekly_variation(2000, 0)  # Monday
        1900
        >>> apply_weekly_variation(2000, 1)  # Tuesday
        2000
        >>> apply_weekly_variation(2000, 2)  # Wednesday
        2100
    """
    # Cycle through -5%, 0%, +5% variation
    variation = variation_pct * ((day_index % 3) - 1)
    adjusted_kcal = int(round(base_kcal * (1 + variation)))

    # Ensure minimum 1200 kcal
    return max(1200, adjusted_kcal)

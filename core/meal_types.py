"""Meal type definitions and classification utilities.

RU: Определения типов приёмов пищи и утилиты классификации.
EN: Meal type definitions and classification utilities.

This module provides standardized meal type definitions used across
nutrition planning, calorie distribution, and meal recommendation systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MealType(Enum):
    """Standard meal types for daily nutrition planning.

    RU: Стандартные типы приёмов пищи для планирования питания.
    EN: Standard meal types for daily nutrition planning.
    """

    BREAKFAST = "breakfast"
    MORNING_SNACK = "morning_snack"
    LUNCH = "lunch"
    AFTERNOON_SNACK = "afternoon_snack"
    DINNER = "dinner"
    EVENING_SNACK = "evening_snack"


@dataclass(frozen=True)
class MealWindow:
    """Time window and calorie distribution for a meal type.

    RU: Временное окно и распределение калорий для типа приёма пищи.
    EN: Time window and calorie distribution for a meal type.
    """

    meal_type: MealType
    # Typical time range (24-hour format)
    start_hour: int  # e.g., 7 for 7:00 AM
    end_hour: int  # e.g., 10 for 10:00 AM
    # Percentage of daily calories (0.0-1.0)
    calorie_percentage: float
    # Whether this meal is optional
    is_optional: bool = False


# Standard meal distribution based on nutritional best practices
# Source: American Dietetic Association, WHO guidelines
STANDARD_MEAL_WINDOWS = {
    MealType.BREAKFAST: MealWindow(
        meal_type=MealType.BREAKFAST,
        start_hour=6,
        end_hour=10,
        calorie_percentage=0.25,  # 25% of daily calories
        is_optional=False,
    ),
    MealType.MORNING_SNACK: MealWindow(
        meal_type=MealType.MORNING_SNACK,
        start_hour=10,
        end_hour=12,
        calorie_percentage=0.08,  # 8% of daily calories
        is_optional=True,
    ),
    MealType.LUNCH: MealWindow(
        meal_type=MealType.LUNCH,
        start_hour=12,
        end_hour=14,
        calorie_percentage=0.30,  # 30% of daily calories
        is_optional=False,
    ),
    MealType.AFTERNOON_SNACK: MealWindow(
        meal_type=MealType.AFTERNOON_SNACK,
        start_hour=15,
        end_hour=17,
        calorie_percentage=0.08,  # 8% of daily calories
        is_optional=True,
    ),
    MealType.DINNER: MealWindow(
        meal_type=MealType.DINNER,
        start_hour=18,
        end_hour=21,
        calorie_percentage=0.25,  # 25% of daily calories
        is_optional=False,
    ),
    MealType.EVENING_SNACK: MealWindow(
        meal_type=MealType.EVENING_SNACK,
        start_hour=21,
        end_hour=23,
        calorie_percentage=0.04,  # 4% of daily calories (light)
        is_optional=True,
    ),
}


def get_meal_type_from_time(hour: int) -> Optional[MealType]:
    """Determine meal type based on hour of day.

    RU: Определить тип приёма пищи по времени суток.
    EN: Determine meal type based on hour of day.

    Args:
        hour: Hour in 24-hour format (0-23)

    Returns:
        Corresponding MealType or None if outside meal windows

    Examples:
        >>> get_meal_type_from_time(8)
        <MealType.BREAKFAST: 'breakfast'>
        >>> get_meal_type_from_time(13)
        <MealType.LUNCH: 'lunch'>
    """
    if not 0 <= hour <= 23:
        return None

    for meal_window in STANDARD_MEAL_WINDOWS.values():
        if meal_window.start_hour <= hour < meal_window.end_hour:
            return meal_window.meal_type

    return None


def get_required_meals() -> list[MealType]:
    """Get list of required (non-optional) meals.

    RU: Получить список обязательных приёмов пищи.
    EN: Get list of required (non-optional) meals.

    Returns:
        List of meal types that are not optional
    """
    return [window.meal_type for window in STANDARD_MEAL_WINDOWS.values() if not window.is_optional]


def get_meal_calorie_target(meal_type: MealType, daily_calories: float) -> float:
    """Calculate calorie target for a specific meal.

    RU: Рассчитать целевые калории для конкретного приёма пищи.
    EN: Calculate calorie target for a specific meal.

    Args:
        meal_type: Type of meal
        daily_calories: Total daily calorie target

    Returns:
        Calories allocated for this meal

    Raises:
        ValueError: If meal_type is not recognized or not in STANDARD_MEAL_WINDOWS

    Examples:
        >>> get_meal_calorie_target(MealType.BREAKFAST, 2000)
        500.0
        >>> get_meal_calorie_target(MealType.LUNCH, 2000)
        600.0
    """
    window = STANDARD_MEAL_WINDOWS.get(meal_type)
    if not window:
        raise ValueError(f"Unknown meal type: {meal_type}")

    return daily_calories * window.calorie_percentage


def validate_meal_distribution(
    meal_calories: dict[MealType, float], daily_target: float, tolerance: float = 0.15
) -> tuple[bool, str]:
    """Validate that meal calorie distribution is reasonable.

    RU: Проверить что распределение калорий по приёмам пищи разумное.
    EN: Validate that meal calorie distribution is reasonable.

    Args:
        meal_calories: Dictionary mapping meal types to calorie amounts
        daily_target: Target daily calories (must be positive)
        tolerance: Allowed deviation from target (default 15%)

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.

    Examples:
        >>> validate_meal_distribution(
        ...     {MealType.BREAKFAST: 500, MealType.LUNCH: 600, MealType.DINNER: 500},
        ...     2000
        ... )
        (False, 'Total meal calories (1600) deviate from daily target (2000) by 20.0%')
    """
    # Validate daily_target
    if daily_target <= 0:
        return (False, f"Daily target must be positive, got {daily_target}")

    total = sum(meal_calories.values())

    # Check if total is within tolerance
    deviation = abs(total - daily_target) / daily_target
    if deviation > tolerance:
        return (
            False,
            f"Total meal calories ({total:.0f}) deviate from daily target "
            f"({daily_target:.0f}) by {deviation*100:.1f}%",
        )

    # Check if any single meal is unreasonably large (>50% of daily)
    max_meal_percentage = 0.50
    for meal_type, calories in meal_calories.items():
        meal_percentage = calories / daily_target
        if meal_percentage > max_meal_percentage:
            return (
                False,
                f"{meal_type.value} has {meal_percentage*100:.1f}% of daily calories "
                f"(max {max_meal_percentage*100:.0f}%)",
            )

    return (True, "")

"""Portion size calculation utilities.

RU: Утилиты для расчёта размеров порций.
EN: Portion size calculation utilities.

This module provides portion size calculations based on user profiles,
dietary goals, and meal types. Supports multiple portion sizing methods
including calorie-based, macro-based, and visual portion guides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .meal_types import MealType, get_meal_calorie_target


@dataclass(frozen=True)
class PortionSize:
    """Calculated portion size for a meal component.

    RU: Рассчитанный размер порции для компонента блюда.
    EN: Calculated portion size for a meal component.
    """

    # Weight in grams
    grams: float
    # Calories
    calories: float
    # Macronutrients
    protein_g: float
    fat_g: float
    carbs_g: float
    # Visual portion guide (optional)
    visual_guide: Optional[str] = None


class PortionCalculator:
    """Calculate portion sizes based on nutritional targets.

    RU: Расчёт размеров порций на основе целей питания.
    EN: Calculate portion sizes based on nutritional targets.
    """

    # Standard macronutrient calories per gram
    KCAL_PER_G_PROTEIN = 4.0
    KCAL_PER_G_CARBS = 4.0
    KCAL_PER_G_FAT = 9.0

    @staticmethod
    def calculate_from_calories(
        target_calories: float,
        food_calories_per_100g: float,
    ) -> PortionSize:
        """Calculate portion size to hit calorie target.

        RU: Рассчитать размер порции для достижения целевых калорий.
        EN: Calculate portion size to hit calorie target.

        Args:
            target_calories: Target calories for this portion
            food_calories_per_100g: Calories per 100g of food

        Returns:
            PortionSize with calculated weight and calories

        Examples:
            >>> calc = PortionCalculator()
            >>> portion = calc.calculate_from_calories(400, 150)
            >>> round(portion.grams)
            267
            >>> round(portion.calories)
            400
        """
        if food_calories_per_100g <= 0:
            raise ValueError("food_calories_per_100g must be positive")

        grams = (target_calories / food_calories_per_100g) * 100
        return PortionSize(
            grams=grams,
            calories=target_calories,
            protein_g=0.0,
            fat_g=0.0,
            carbs_g=0.0,
        )

    @staticmethod
    def calculate_from_macros(
        protein_target_g: float,
        fat_target_g: float,
        carbs_target_g: float,
        food_protein_per_100g: float,
        food_fat_per_100g: float,
        food_carbs_per_100g: float,
        prioritize: str = "protein",
    ) -> PortionSize:
        """Calculate portion size to hit macronutrient targets.

        RU: Рассчитать размер порции для достижения целей по макронутриентам.
        EN: Calculate portion size to hit macronutrient targets.

        Args:
            protein_target_g: Target protein in grams
            fat_target_g: Target fat in grams
            carbs_target_g: Target carbs in grams
            food_protein_per_100g: Protein per 100g of food
            food_fat_per_100g: Fat per 100g of food
            food_carbs_per_100g: Carbs per 100g of food
            prioritize: Which macro to prioritize ("protein", "fat", or "carbs")

        Returns:
            PortionSize with calculated weight and macros

        Raises:
            ValueError: If prioritize is invalid or food content is invalid
        """
        if prioritize not in ("protein", "fat", "carbs"):
            raise ValueError("prioritize must be 'protein', 'fat', or 'carbs'")

        # Calculate grams needed for prioritized macro
        if prioritize == "protein":
            if food_protein_per_100g <= 0:
                raise ValueError("food_protein_per_100g must be positive")
            grams = (protein_target_g / food_protein_per_100g) * 100
        elif prioritize == "fat":
            if food_fat_per_100g <= 0:
                raise ValueError("food_fat_per_100g must be positive")
            grams = (fat_target_g / food_fat_per_100g) * 100
        else:  # carbs
            if food_carbs_per_100g <= 0:
                raise ValueError("food_carbs_per_100g must be positive")
            grams = (carbs_target_g / food_carbs_per_100g) * 100

        # Calculate actual macros for this portion
        protein_g = (grams / 100) * food_protein_per_100g
        fat_g = (grams / 100) * food_fat_per_100g
        carbs_g = (grams / 100) * food_carbs_per_100g

        # Calculate total calories
        calories = (
            protein_g * PortionCalculator.KCAL_PER_G_PROTEIN
            + fat_g * PortionCalculator.KCAL_PER_G_FAT
            + carbs_g * PortionCalculator.KCAL_PER_G_CARBS
        )

        return PortionSize(
            grams=grams,
            calories=calories,
            protein_g=protein_g,
            fat_g=fat_g,
            carbs_g=carbs_g,
        )

    @staticmethod
    def calculate_meal_portion(
        meal_type: MealType,
        daily_calories: float,
        food_calories_per_100g: float,
    ) -> PortionSize:
        """Calculate portion size for a specific meal type.

        RU: Рассчитать размер порции для конкретного типа приёма пищи.
        EN: Calculate portion size for a specific meal type.

        Args:
            meal_type: Type of meal (breakfast, lunch, etc.)
            daily_calories: Total daily calorie target
            food_calories_per_100g: Calories per 100g of food

        Returns:
            PortionSize appropriate for this meal

        Examples:
            >>> from meal_types import MealType
            >>> calc = PortionCalculator()
            >>> portion = calc.calculate_meal_portion(
            ...     MealType.BREAKFAST, 2000, 150
            ... )
            >>> round(portion.calories)
            500
        """
        meal_calories = get_meal_calorie_target(meal_type, daily_calories)
        return PortionCalculator.calculate_from_calories(meal_calories, food_calories_per_100g)

    @staticmethod
    def get_visual_portion_guide(grams: float, food_type: str) -> str:
        """Get visual portion guide for common foods.

        RU: Получить визуальный ориентир размера порции для обычных продуктов.
        EN: Get visual portion guide for common foods.

        Args:
            grams: Weight in grams
            food_type: Type of food ("protein", "grains", "vegetables", "fruit")

        Returns:
            Visual guide description (e.g., "palm-sized", "fist-sized")
        """
        # Visual guides based on hand measurements (average adult)
        # Source: American Heart Association, MyPlate guidelines
        if food_type == "protein":
            if grams <= 85:
                return "palm of hand"
            if grams <= 170:
                return "2 palms"
            return "3+ palms"

        if food_type == "grains":
            if grams <= 80:
                return "cupped handful"
            if grams <= 160:
                return "2 cupped handfuls"
            return "3+ cupped handfuls"

        if food_type in ("vegetables", "salad"):
            if grams <= 150:
                return "1 fist"
            if grams <= 300:
                return "2 fists"
            return "3+ fists"

        if food_type == "fruit":
            if grams <= 120:
                return "1 tennis ball"
            if grams <= 240:
                return "2 tennis balls"
            return "3+ tennis balls"

        # Default for unknown types
        if grams <= 100:
            return "small portion (~100g)"
        if grams <= 250:
            return "medium portion (~250g)"
        return "large portion (250g+)"


def distribute_calories_to_portions(
    total_calories: float,
    num_portions: int = 3,
    distribution: Optional[list[float]] = None,
) -> list[float]:
    """Distribute calories across multiple portions.

    RU: Распределить калории на несколько порций.
    EN: Distribute calories across multiple portions.

    Args:
        total_calories: Total calories to distribute
        num_portions: Number of portions (default 3 for main meals)
        distribution: Optional custom distribution (must sum to 1.0)

    Returns:
        List of calorie amounts per portion

    Examples:
        >>> distribute_calories_to_portions(2000, 3)
        [500.0, 600.0, 500.0]
        >>> distribute_calories_to_portions(2000, 3, [0.3, 0.4, 0.3])
        [600.0, 800.0, 600.0]
    """
    if num_portions <= 0:
        raise ValueError("num_portions must be positive")

    if distribution is None:
        # Default: breakfast 25%, lunch 30%, dinner 25%, rest evenly
        if num_portions == 3:
            distribution = [0.25, 0.30, 0.25]
        else:
            # Equal distribution
            distribution = [1.0 / num_portions] * num_portions
    else:
        if len(distribution) != num_portions:
            raise ValueError("distribution length must match num_portions")
        if abs(sum(distribution) - 1.0) > 0.01:
            raise ValueError("distribution must sum to 1.0")

    return [total_calories * ratio for ratio in distribution]

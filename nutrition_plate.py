"""
Premium Plate Generator - Core Logic for Daily Nutrition Recommendations

This module provides plate composition logic for the Premium Plate feature,
generating macro-balanced meal recommendations based on TDEE calculations.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from nutrition_core import calculate_all_bmr, calculate_all_tdee


class MacroDistribution(BaseModel):
    """Macro distribution model with validation."""

    protein_percent: float = Field(
        ..., ge=10, le=50, description="Protein percentage (10-50%)"
    )
    carbs_percent: float = Field(
        ..., ge=20, le=65, description="Carbohydrates percentage (20-65%)"
    )
    fat_percent: float = Field(..., ge=15, le=45, description="Fat percentage (15-45%)")

    @field_validator("protein_percent", "carbs_percent", "fat_percent")
    @classmethod
    def validate_percentages(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Percentages must be between 0 and 100")
        return v

    def model_post_init(self, __context) -> None:
        """Validate that percentages sum to 100."""
        total = self.protein_percent + self.carbs_percent + self.fat_percent
        if abs(total - 100) > 0.1:  # Allow small floating point differences
            raise ValueError(f"Macro percentages must sum to 100%, got {total}%")


class PlateRecommendation(BaseModel):
    """Complete plate recommendation model."""

    target_calories: float
    macro_distribution: MacroDistribution
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    meal_suggestions: List[str]
    notes: List[str]


def get_macro_distribution(
    goal: str = "maintenance", activity_level: str = "moderate"
) -> MacroDistribution:
    """
    Get recommended macro distribution based on goal and activity level.

    Args:
        goal: Nutrition goal ("weight_loss", "maintenance", "weight_gain", "muscle_gain")
        activity_level: Activity level ("sedentary", "light", "moderate", "active", "very_active")

    Returns:
        MacroDistribution with appropriate percentages
    """
    # Base distributions for different goals
    distributions = {
        "weight_loss": {"protein": 30, "carbs": 35, "fat": 35},
        "maintenance": {"protein": 25, "carbs": 45, "fat": 30},
        "weight_gain": {"protein": 20, "carbs": 50, "fat": 30},
        "muscle_gain": {"protein": 30, "carbs": 40, "fat": 30},
    }

    # Adjust for activity level
    base = distributions.get(goal, distributions["maintenance"])

    if activity_level in ["active", "very_active"]:
        # Increase carbs for active individuals
        base["carbs"] = min(base["carbs"] + 5, 60)
        base["fat"] = max(base["fat"] - 5, 20)
    elif activity_level == "sedentary":
        # Slightly reduce carbs for sedentary individuals
        base["carbs"] = max(base["carbs"] - 5, 30)
        base["fat"] = min(base["fat"] + 5, 40)

    return MacroDistribution(
        protein_percent=base["protein"],
        carbs_percent=base["carbs"],
        fat_percent=base["fat"],
    )


def calculate_macros_in_grams(
    calories: float, macro_dist: MacroDistribution
) -> Dict[str, float]:
    """
    Calculate macro amounts in grams based on calories and percentages.

    Args:
        calories: Target calories
        macro_dist: Macro distribution percentages

    Returns:
        Dictionary with protein, carbs, and fat in grams
    """
    # Calories per gram: protein=4, carbs=4, fat=9
    protein_calories = calories * (macro_dist.protein_percent / 100)
    carbs_calories = calories * (macro_dist.carbs_percent / 100)
    fat_calories = calories * (macro_dist.fat_percent / 100)

    return {
        "protein": round(protein_calories / 4, 1),
        "carbs": round(carbs_calories / 4, 1),
        "fat": round(fat_calories / 9, 1),
    }


def get_meal_suggestions(macro_dist: MacroDistribution, lang: str = "en") -> List[str]:
    """
    Generate meal suggestions based on macro distribution.

    Args:
        macro_dist: Macro distribution
        lang: Language ("en" or "ru")

    Returns:
        List of meal suggestions
    """
    if lang == "ru":
        base_suggestions = [
            "Завтрак: Овсянка с ягодами и орехами",
            "Обед: Запеченная курица с киноа и овощами",
            "Ужин: Лосось с запеченными овощами",
            "Перекус: Греческий йогурт с фруктами",
        ]

        if macro_dist.protein_percent >= 30:
            base_suggestions.append(
                "Дополнительно: Протеиновый коктейль после тренировки"
            )

        if macro_dist.carbs_percent >= 50:
            base_suggestions.append("Дополнительно: Фрукты или цельнозерновые продукты")

    else:
        base_suggestions = [
            "Breakfast: Oatmeal with berries and nuts",
            "Lunch: Grilled chicken with quinoa and vegetables",
            "Dinner: Baked salmon with roasted vegetables",
            "Snack: Greek yogurt with fruit",
        ]

        if macro_dist.protein_percent >= 30:
            base_suggestions.append("Additional: Post-workout protein shake")

        if macro_dist.carbs_percent >= 50:
            base_suggestions.append("Additional: Fruits or whole grains")

    return base_suggestions


def get_nutrition_notes(
    macro_dist: MacroDistribution, goal: str, lang: str = "en"
) -> List[str]:
    """
    Generate nutrition notes and tips.

    Args:
        macro_dist: Macro distribution
        goal: Nutrition goal
        lang: Language ("en" or "ru")

    Returns:
        List of nutrition notes
    """
    if lang == "ru":
        notes = [
            (f"Целевое распределение: {macro_dist.protein_percent}% белки, "
             f"{macro_dist.carbs_percent}% углеводы, {macro_dist.fat_percent}% жиры"),
            "Пейте достаточно воды (8-10 стаканов в день)",
            "Включайте разнообразные источники белка и овощи",
        ]

        if goal == "weight_loss":
            notes.append("Для похудения: контролируйте размер порций")
        elif goal == "muscle_gain":
            notes.append("Для роста мышц: употребляйте белок каждые 3-4 часа")

    else:
        notes = [
            (f"Target distribution: {macro_dist.protein_percent}% protein, "
             f"{macro_dist.carbs_percent}% carbs, {macro_dist.fat_percent}% fat"),
            "Stay hydrated (8-10 glasses of water daily)",
            "Include variety in protein sources and vegetables",
        ]

        if goal == "weight_loss":
            notes.append("For weight loss: focus on portion control")
        elif goal == "muscle_gain":
            notes.append("For muscle gain: consume protein every 3-4 hours")

    return notes


def make_plate(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity: str,
    goal: str = "maintenance",
    bodyfat: Optional[float] = None,
    lang: str = "en",
) -> PlateRecommendation:
    """
    Generate a complete plate recommendation with macro-balanced nutrition plan.

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        sex: Biological sex ("male" or "female")
        activity: Activity level
        goal: Nutrition goal ("weight_loss", "maintenance", "weight_gain", "muscle_gain")
        bodyfat: Optional body fat percentage
        lang: Response language ("en" or "ru")

    Returns:
        PlateRecommendation with complete nutrition plan
    """
    # Calculate BMR and TDEE
    bmr_results = calculate_all_bmr(weight_kg, height_cm, age, sex, bodyfat)
    tdee_results = calculate_all_tdee(bmr_results, activity)

    # Use Mifflin-St Jeor as primary formula
    base_tdee = tdee_results["mifflin"]

    # Adjust calories based on goal
    calorie_adjustments = {
        "weight_loss": -500,  # 500 calorie deficit
        "maintenance": 0,
        "weight_gain": 500,  # 500 calorie surplus
        "muscle_gain": 300,  # Moderate surplus for lean gains
    }

    target_calories = base_tdee + calorie_adjustments.get(goal, 0)

    # Get macro distribution
    macro_dist = get_macro_distribution(goal, activity)

    # Calculate macros in grams
    macros = calculate_macros_in_grams(target_calories, macro_dist)

    # Generate suggestions and notes
    meal_suggestions = get_meal_suggestions(macro_dist, lang)
    notes = get_nutrition_notes(macro_dist, goal, lang)

    return PlateRecommendation(
        target_calories=round(target_calories),
        macro_distribution=macro_dist,
        protein_grams=macros["protein"],
        carbs_grams=macros["carbs"],
        fat_grams=macros["fat"],
        meal_suggestions=meal_suggestions,
        notes=notes,
    )

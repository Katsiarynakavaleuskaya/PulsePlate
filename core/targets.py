"""
WHO-Based Nutrition Targets System

RU: Система расчёта целевых значений нутриентов на основе рекомендаций ВОЗ.
EN: WHO-based nutrition targets calculation system.

This module defines the core data structures for user profiles and nutrition targets
based on WHO/EFSA/DRI recommendations for macronutrients, micronutrients, hydration,
and physical activity guidelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional, Set

# Type definitions for user characteristics
Sex = Literal["female", "male"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["loss", "maintain", "gain"]
LifeStage = Literal["child", "teen", "adult", "pregnant", "lactating", "elderly"]


@dataclass(frozen=True)
class UserProfile:
    """
    RU: Профиль пользователя для расчёта индивидуальных таргетов.
    EN: User profile for calculating individual nutrition targets.

    Combines basic anthropometric data with lifestyle factors to generate
    personalized nutrition and activity recommendations based on WHO guidelines.
    """

    # Basic characteristics
    sex: Sex
    age: int  # years
    height_cm: float
    weight_kg: float

    # Lifestyle factors
    activity: Activity
    goal: Goal

    # Goal-specific parameters
    deficit_pct: Optional[float] = None  # for loss (5-25%)
    surplus_pct: Optional[float] = None  # for gain (5-20%)

    # Additional context
    bodyfat: Optional[float] = None  # body fat percentage
    region: str = "BY"  # region for food availability
    diet_flags: Set[str] = field(default_factory=set)  # VEG, GF, DAIRY_FREE, LOW_COST

    # Special conditions
    life_stage: LifeStage = "adult"
    medical_conditions: Set[str] = field(default_factory=set)  # for future use

    def __post_init__(self):
        """Validate profile parameters."""
        if self.age < 1 or self.age > 120:
            raise ValueError("Age must be between 1 and 120 years")
        if self.height_cm <= 0 or self.weight_kg <= 0:
            raise ValueError("Height and weight must be positive")
        if self.deficit_pct is not None and not (5 <= self.deficit_pct <= 25):
            raise ValueError("Deficit percentage must be between 5-25%")
        if self.surplus_pct is not None and not (5 <= self.surplus_pct <= 20):
            raise ValueError("Surplus percentage must be between 5-20%")


@dataclass(frozen=True)
class MacroTargets:
    """
    RU: Целевые значения макронутриентов.
    EN: Macronutrient targets in grams per day.
    """

    protein_g: int
    fat_g: int
    carbs_g: int
    fiber_g: int

    def total_calories(self) -> int:
        """Calculate total calories from macros (4/4/9 rule)."""
        return (self.protein_g * 4) + (self.carbs_g * 4) + (self.fat_g * 9)


@dataclass(frozen=True)
class MicroTargets:
    """
    RU: Целевые значения микронутриентов по рекомендациям ВОЗ/EFSA/DRI.
    EN: Micronutrient targets based on WHO/EFSA/DRI recommendations.

    All values are daily requirements. Units specified in field names for clarity.
    """

    # Essential minerals (mg/day)
    iron_mg: float
    calcium_mg: float
    magnesium_mg: float
    zinc_mg: float
    potassium_mg: float

    # Trace elements (μg/day)
    iodine_ug: float
    selenium_ug: float

    # B Vitamins (μg/day)
    folate_ug: float
    b12_ug: float

    # Fat-soluble vitamins
    vitamin_d_iu: float
    vitamin_a_ug: float  # RAE (Retinol Activity Equivalents)

    # Water-soluble vitamins (mg/day)
    vitamin_c_mg: float

    def get_priority_nutrients(self) -> Dict[str, float]:
        """
        RU: Возвращает приоритетные нутриенты для мониторинга дефицитов.
        EN: Returns priority nutrients for deficiency monitoring.
        """
        return {
            "iron_mg": self.iron_mg,
            "calcium_mg": self.calcium_mg,
            "folate_ug": self.folate_ug,
            "vitamin_d_iu": self.vitamin_d_iu,
            "b12_ug": self.b12_ug,
            "iodine_ug": self.iodine_ug,
            "magnesium_mg": self.magnesium_mg,
            "potassium_mg": self.potassium_mg,
        }


@dataclass(frozen=True)
class ActivityTargets:
    """
    RU: Целевые значения физической активности по ВОЗ.
    EN: WHO physical activity targets per week.
    """

    # Aerobic activity (minutes per week)
    moderate_aerobic_min: int  # e.g., 150 min/week
    vigorous_aerobic_min: int  # e.g., 75 min/week (alternative to moderate)

    # Strength training (sessions per week)
    strength_sessions: int  # e.g., 2 sessions/week

    # Daily steps target
    steps_daily: int  # e.g., 8000-10000 steps

    def total_aerobic_equivalent(self) -> int:
        """
        RU: Общий аэробный эквивалент в минутах умеренной активности.
        EN: Total aerobic equivalent in moderate-intensity minutes.
        """
        return self.moderate_aerobic_min + (self.vigorous_aerobic_min * 2)


@dataclass(frozen=True)
class NutritionTargets:
    """
    RU: Полный набор целевых значений питания и активности.
    EN: Complete set of nutrition and activity targets.

    This is the main output of the WHO-based calculation system,
    providing all daily and weekly targets for an individual.
    """

    # Energy and macronutrients
    kcal_daily: int
    macros: MacroTargets

    # Hydration
    water_ml_daily: int

    # Micronutrients
    micros: MicroTargets

    # Physical activity
    activity: ActivityTargets

    # Metadata
    calculated_for: UserProfile
    calculation_date: str = ""  # ISO date when calculated

    def validate_consistency(self) -> bool:
        """
        RU: Проверяет внутреннюю согласованность таргетов.
        EN: Validates internal consistency of targets.
        """
        # Check if macro calories match target calories (within 5% tolerance)
        macro_calories = self.macros.total_calories()
        tolerance = 0.05
        return abs(macro_calories - self.kcal_daily) / self.kcal_daily <= tolerance

    def get_summary(self) -> Dict[str, Any]:
        """
        RU: Краткая сводка таргетов для API ответа.
        EN: Summary of targets for API response.
        """
        return {
            "kcal_daily": self.kcal_daily,
            "macros": {
                "protein_g": self.macros.protein_g,
                "fat_g": self.macros.fat_g,
                "carbs_g": self.macros.carbs_g,
                "fiber_g": self.macros.fiber_g,
            },
            "water_ml_daily": self.water_ml_daily,
            "micros": self.micros.get_priority_nutrients(),
            "activity": {
                "moderate_aerobic_min": self.activity.moderate_aerobic_min,
                "vigorous_aerobic_min": self.activity.vigorous_aerobic_min,
                "strength_sessions": self.activity.strength_sessions,
                "steps_daily": self.activity.steps_daily,
            },
        }


@dataclass
class NutrientCoverage:
    """
    RU: Оценка покрытия нутриентов в рационе.
    EN: Assessment of nutrient coverage in diet.
    """

    nutrient_name: str
    target_amount: float
    consumed_amount: float
    unit: str

    @property
    def coverage_percent(self) -> float:
        """Percentage of target met (capped at 200%)."""
        if self.target_amount <= 0:
            return 0.0
        return min(200.0, (self.consumed_amount / self.target_amount) * 100)

    @property
    def status(self) -> Literal["deficient", "adequate", "excess"]:
        """Categorize coverage status."""
        if self.coverage_percent < 67:  # Less than 2/3 of RDA
            return "deficient"
        elif self.coverage_percent <= 150:  # Within 150% of RDA
            return "adequate"
        else:
            return "excess"

    def get_recommendation(self, lang: str = "en") -> str:
        """
        RU: Рекомендация по корректировке потребления.
        EN: Recommendation for intake adjustment.
        """
        if lang == "ru":
            if self.status == "deficient":
                return f"Увеличьте потребление {self.nutrient_name}"
            elif self.status == "excess":
                return f"Умеренно сократите {self.nutrient_name}"
            return f"{self.nutrient_name} в норме"
        else:
            if self.status == "deficient":
                return f"Increase {self.nutrient_name} intake"
            elif self.status == "excess":
                return f"Moderately reduce {self.nutrient_name}"
            return f"{self.nutrient_name} is adequate"

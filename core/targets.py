"""WHO-Based Nutrition Targets System.

RU: Система расчёта целевых значений нутриентов на основе рекомендаций ВОЗ.
EN: WHO-based nutrition targets calculation system.

This module defines the core data structures for user profiles and nutrition targets
based on WHO/EFSA/DRI recommendations for macronutrients, micronutrients, hydration,
and physical activity guidelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set

# Type definitions for user characteristics
Sex = Literal["female", "male"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["loss", "maintain", "gain"]
LifeStage = Literal["child", "teen", "adult", "pregnant", "lactating", "elderly"]


@dataclass(frozen=True)
class UserProfile:
    """User profile for calculating individual nutrition targets.

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
    timezone: str = "UTC"  # IANA timezone identifier for localisation
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
    """Macronutrient targets in grams per day.

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
class MicronutrientTargets:
    """Enhanced micronutrient targets with ranges and tolerances for VIP features.

    RU: Расширенные микронутриентные цели с диапазонами и допусками для VIP функций.
    EN: Enhanced micronutrient targets with ranges and tolerances for VIP features.

    Includes WHO/EFSA-based daily requirements with deficiency thresholds
    and priority levels for auto-repair functionality.
"""

    # Core micronutrients with ranges (min, target, max)
    iron_mg: tuple[float, float, float]  # (min, target, max)
    calcium_mg: tuple[float, float, float]
    magnesium_mg: tuple[float, float, float]
    zinc_mg: tuple[float, float, float]
    potassium_mg: tuple[float, float, float]

    # Trace elements
    iodine_ug: tuple[float, float, float]
    selenium_ug: tuple[float, float, float]

    # B Vitamins
    folate_ug: tuple[float, float, float]
    b12_ug: tuple[float, float, float]

    # Fat-soluble vitamins
    vitamin_d_iu: tuple[float, float, float]
    vitamin_a_ug: tuple[float, float, float]  # RAE

    # Water-soluble vitamins
    vitamin_c_mg: tuple[float, float, float]

    # Deficiency thresholds (percentage of target)
    deficiency_threshold: float = 0.8  # 80% of target

    # Priority levels for auto-repair (1-5, 5 = highest)
    priority_nutrients: Dict[str, int] = field(
        default_factory=lambda: {
            "iron_mg": 5,
            "calcium_mg": 5,
            "vitamin_d_iu": 4,
            "folate_ug": 4,
            "b12_ug": 4,
            "iodine_ug": 3,
            "magnesium_mg": 3,
            "potassium_mg": 3,
            "zinc_mg": 2,
            "vitamin_c_mg": 2,
            "vitamin_a_ug": 2,
            "selenium_ug": 1,
        }
    )

    def get_target(self, nutrient: str) -> float:
        """Get target value for a nutrient."""
        if hasattr(self, nutrient):
            val = getattr(self, nutrient)[1]  # middle value is target
            return float(val)
        raise ValueError(f"Unknown nutrient: {nutrient}")

    def get_minimum(self, nutrient: str) -> float:
        """Get minimum acceptable value for a nutrient."""
        if hasattr(self, nutrient):
            val = getattr(self, nutrient)[0]  # first value is minimum
            return float(val)
        raise ValueError(f"Unknown nutrient: {nutrient}")  # pragma: no cover

    def get_maximum(self, nutrient: str) -> float:
        """Get maximum safe value for a nutrient."""
        if hasattr(self, nutrient):
            val = getattr(self, nutrient)[2]  # third value is maximum
            return float(val)
        raise ValueError(f"Unknown nutrient: {nutrient}")  # pragma: no cover

    def is_deficient(self, nutrient: str, actual_value: float) -> bool:
        """Check if actual intake is deficient."""
        target = self.get_target(nutrient)
        threshold = target * self.deficiency_threshold
        return actual_value < threshold

    def get_priority_nutrients(self) -> Dict[str, float]:
        """Get priority nutrients with their targets."""
        return {
            nutrient: self.get_target(nutrient)
            for nutrient, priority in self.priority_nutrients.items()
            if priority >= 3  # Only high-priority nutrients
        }

    def get_high_priority_nutrients(self) -> List[str]:
        """Get list of high-priority nutrients (priority >= 4)."""
        return [nutrient for nutrient, priority in self.priority_nutrients.items() if priority >= 4]


@dataclass(frozen=True)
class MicroTargets:
    """Micronutrient targets based on WHO/EFSA/DRI recommendations.

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
        """Returns priority nutrients for deficiency monitoring.

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
    """WHO physical activity targets per week.

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
        """Total aerobic equivalent in moderate-intensity minutes.

        RU: Общий аэробный эквивалент в минутах умеренной активности.
        EN: Total aerobic equivalent in moderate-intensity minutes.
        """
        return self.moderate_aerobic_min + (self.vigorous_aerobic_min * 2)


@dataclass(frozen=True)
class NutritionTargets:
    """Complete set of nutrition and activity targets.

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


def _life_stage_warnings(age: int, life_stage: LifeStage, lang: str = "en") -> List[Dict[str, str]]:
"""
    RU: Генерирует предупреждения по жизненным этапам с локализацией.
    EN: Generates life stage warnings with localization.

    Args:
        age: Возраст пользователя
        life_stage: Жизненный этап (child, teen, adult, pregnant, lactating, elderly)
        lang: Язык локализации (ru, en, es)

    Returns:
        Список предупреждений с кодами и локализованными сообщениями
"""
    # Локализованные сообщения
    M = {
        "teen": {
            "ru": "Подростковая группа: используйте специализированные нормы.",
            "en": "Teen life stage: use age-appropriate references.",
            "es": "Etapa adolescente: use referencias apropiadas para la edad.",
        },
        "pregnant": {
            "ru": "Беременность: нормы отличаются; обратитесь к специализированным рекомендациям.",
            "en": "Pregnancy: requirements differ; consult specialized guidelines.",
            "es": "Embarazo: los requisitos difieren; consulte guías especializadas.",
        },
        "lactating": {
            "ru": "Лактация: повышенные потребности в нутриентах.",
            "en": "Lactation: increased nutrient requirements.",
            "es": "Lactancia: requisitos de nutrientes aumentados.",
        },
        "elderly": {
            "ru": "51+: возможна иная потребность в микронутриентах.",
            "en": "Age 51+: micronutrient needs may differ.",
            "es": "51+: las necesidades de micronutrientes pueden diferir.",
        },
        "child": {
            "ru": "Детский возраст: используйте педиатрические нормы.",
            "en": "Child age: use pediatric references.",
            "es": "Edad infantil: use referencias pediátricas.",
        },
    }

    warnings = []

    # Проверяем возрастные группы
    if 12 <= age <= 18 and life_stage == "teen":
        warnings.append({"code": "teen", "message": M["teen"].get(lang, M["teen"]["en"])})

    # Проверяем специальные состояния
    if life_stage == "pregnant":
        warnings.append(
            {
                "code": "pregnant",
                "message": M["pregnant"].get(lang, M["pregnant"]["en"]),
            }
        )

    if life_stage == "lactating":
        warnings.append(
            {
                "code": "lactating",
                "message": M["lactating"].get(lang, M["lactating"]["en"]),
            }
        )

    if age >= 51 and life_stage == "elderly":
        warnings.append({"code": "elderly", "message": M["elderly"].get(lang, M["elderly"]["en"])})

    if age < 12 and life_stage == "child":
        warnings.append({"code": "child", "message": M["child"].get(lang, M["child"]["en"])})

    return warnings


def calculate_bmr(
    age: int,
    weight: float,
    height: int,
    gender: str,
    body_fat: Optional[float] = None,
    formula: str = "mifflin",
) -> float:
    """Calculate Basal Metabolic Rate (BMR) using various formulas.

    Args:
        age: Age in years
        weight: Weight in kg
        height: Height in cm
        gender: "male" or "female"
        body_fat: Body fat percentage (0-100), required for katch/cunningham formulas
        formula: Formula to use ("mifflin", "harris", "katch", "cunningham")

    Returns:
        BMR in kcal/day

    Raises:
        ValueError: If unknown formula or missing body_fat for katch/cunningham
"""
    if formula == "mifflin":
        if gender == "male":
            return 10 * weight + 6.25 * height - 5 * age + 5
        else:
            return 10 * weight + 6.25 * height - 5 * age - 161
    elif formula == "harris":
        if gender == "male":
            return 66.47 + 13.75 * weight + 5.003 * height - 6.755 * age
        else:
            return 655.1 + 9.563 * weight + 1.85 * height - 4.676 * age
    elif formula == "katch":
        if body_fat is None:
            raise ValueError("Body fat percentage required for Katch-McArdle formula")
        lean_body_mass = weight * (1 - body_fat / 100)
        return 370 + (21.6 * lean_body_mass)
    elif formula == "cunningham":
        if body_fat is None:
            raise ValueError("Body fat percentage required for Cunningham formula")
        lean_body_mass = weight * (1 - body_fat / 100)
        return 500 + (22 * lean_body_mass)
    else:
        raise ValueError(f"Unknown BMR formula: {formula}")


def get_bmr_formula(user_data: dict) -> str:
    """Select the best BMR formula based on available user data.

    Args:
        user_data: Dictionary with user information

    Returns:
        Best formula name ("katch" if body_fat available, otherwise "mifflin")
"""
    if "body_fat" in user_data and user_data["body_fat"] is not None:
        return "katch"
    return "mifflin"


# Additional functions for comprehensive testing


def adjust_for_activity(bmr: float, activity_level: str) -> float:
"""
    Adjust BMR for activity level to get TDEE estimate.

    Args:
        bmr: Basal Metabolic Rate
        activity_level: Activity level string

    Returns:
        Adjusted TDEE estimate
"""
    multipliers = {
        "sedentary": 1.2,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725,
        "extremely_active": 1.9,
    }
    multiplier = multipliers.get(activity_level, 1.2)
    return bmr * multiplier


def calculate_tdee(bmr: float, activity_level: str, **_kwargs) -> float:
"""
    Calculate Total Daily Energy Expenditure.

    Args:
        bmr: Basal Metabolic Rate
        activity_level: Activity level
        **kwargs: Additional factors

    Returns:
        TDEE in kcal/day
"""
    return adjust_for_activity(bmr, activity_level)


def calculate_macros(calories: int, **_user_profile) -> dict:
"""
    Calculate macronutrient distribution.

    Args:
        calories: Total daily calories
        **user_profile: User profile data

    Returns:
        Dictionary with macro grams
"""
    # Simple 40/30/30 split
    protein_g = calories * 0.3 / 4
    carbs_g = calories * 0.4 / 4
    fat_g = calories * 0.3 / 9

    return {
        "protein": round(protein_g, 1),
        "carbs": round(carbs_g, 1),
        "fat": round(fat_g, 1),
    }


def get_macro_ratios(goal: str, restriction: str) -> dict:  # noqa: ARG001
"""
    Get macro ratios based on goal and dietary restriction.

    Args:
        goal: Fitness goal
        restriction: Dietary restriction

    Returns:
        Dictionary with macro percentages
"""
    if goal == "muscle_gain":
        return {"protein": 0.4, "carbs": 0.35, "fat": 0.25}
    elif goal == "fat_loss":
        return {"protein": 0.4, "carbs": 0.3, "fat": 0.3}
    else:  # maintain
        return {"protein": 0.3, "carbs": 0.4, "fat": 0.3}


def calculate_micronutrient_targets(**user_data) -> dict:
"""
    Calculate micronutrient targets based on user data.

    Args:
        **user_data: User profile data

    Returns:
        Dictionary with micronutrient targets
"""
    # Basic RDA values
    return {
        "vitamin_c": 90,  # mg
        "vitamin_d": 15,  # mcg
        "calcium": 1000,  # mg
        "iron": 18 if user_data.get("gender") == "female" else 8,  # mg
        "b12": 2.4,  # mcg
    }


def get_rda_values(age: int, gender: str) -> dict:
"""
    Get RDA values for age and gender.

    Args:
        age: Age in years
        gender: Gender string

    Returns:
        Dictionary with RDA values
"""
    return calculate_micronutrient_targets(age=age, gender=gender)


def adjust_calories_for_goal(current_calories: int, **goal_data) -> float:
"""
    Adjust calories based on weight goal.

    Args:
        current_calories: Current daily calories
        **goal_data: Goal parameters

    Returns:
        Adjusted calories
"""
    goal_type = goal_data.get("goal_type", "maintain")
    if goal_type == "lose":
        return current_calories - 500
    elif goal_type == "gain":
        return current_calories + 500
    else:
        return current_calories


def calculate_deficit_surplus(**goal_data) -> float:
"""
    Calculate calorie deficit or surplus.

    Args:
        **goal_data: Goal parameters

    Returns:
        Calorie adjustment
"""
    goal_type = goal_data.get("goal_type", "maintain")
    if goal_type == "lose":
        return -500
    elif goal_type == "gain":
        return 500
    else:
        return 0


def get_athlete_targets(**_profile) -> dict:
"""
    Get nutrition targets for athletes.

    Args:
        **profile: Athlete profile

    Returns:
        Nutrition targets
"""
    return {
        "protein_multiplier": 1.6,  # g per kg body weight
        "carb_intake": 8,  # g per kg body weight
        "calorie_density": 1.2,
    }


def get_elderly_adjustments(**_profile) -> dict:
"""
    Get nutrition adjustments for elderly.

    Args:
        **profile: Elderly profile

    Returns:
        Nutrition adjustments
"""
    return {
        "vitamin_d_boost": 1.5,
        "protein_boost": 1.2,
        "calcium_boost": 1.3,
    }


def get_pregnancy_targets(**profile) -> dict:
"""
    Get nutrition targets for pregnancy.

    Args:
        **profile: Pregnancy profile

    Returns:
        Nutrition targets
"""
    trimester = profile.get("trimester", 2)
    return {
        "calorie_boost": 300 + (trimester - 1) * 100,
        "protein_boost": 25,  # additional grams
        "folic_acid": 600,  # mcg
        "iron": 27,  # mg
    }


def calculate_pre_post_workout(workout_type: str, duration: int) -> dict:  # noqa: ARG001
"""
    Calculate pre and post workout nutrition.

    Args:
        workout_type: Type of workout
        duration: Duration in minutes

    Returns:
        Nutrition recommendations
"""
    return {
        "pre_workout": {
            "carbs": 20 + duration // 30,  # grams
            "protein": 10,
        },
        "post_workout": {
            "protein": 20 + duration // 30,  # grams
            "carbs": 30 + duration // 15,  # grams
        },
    }


def get_meal_timing(**timing_data) -> dict:
"""
    Get meal timing recommendations.

    Args:
        **timing_data: Meal timing parameters

    Returns:
        Meal timing plan
"""
    meals_per_day = timing_data.get("meals_per_day", 3)
    return {
        "breakfast": "07:00",
        "lunch": "13:00",
        "dinner": "19:00",
        "snacks": ["10:00", "16:00"] if meals_per_day > 3 else [],
    }


def calculate_hydration_needs(**_hydration_data) -> float:
"""
    Calculate daily hydration needs.

    Args:
        **hydration_data: Hydration factors

    Returns:
        Daily water intake in ml
"""
    weight: float = _hydration_data.get("weight", 70)
    activity_level: str = _hydration_data.get("activity_level", "moderate")

    base_ml: float = weight * 30  # 30ml per kg

    if activity_level == "very_active":
        base_ml *= 1.2
    elif activity_level == "extremely_active":
        base_ml *= 1.4

    return base_ml


def adjust_for_climate(base_hydration: float, climate: str, altitude: int = 0) -> float:
"""
    Adjust hydration needs for climate and altitude.

    Args:
        base_hydration: Base hydration needs
        climate: Climate type
        altitude: Altitude in meters

    Returns:
        Adjusted hydration needs
"""
    multiplier = 1.0

    if climate in ["hot", "humid"]:
        multiplier = 1.3
    elif climate == "cold":
        multiplier = 0.9

    if altitude > 1000:
        multiplier += 0.1 * (altitude // 1000)

    return base_hydration * multiplier


def check_deficiency_risk(**user_profile) -> dict:
"""
    Check risk of nutrient deficiencies.

    Args:
        **user_profile: User profile data

    Returns:
        Deficiency risk assessment
"""
    risks = {}

    if user_profile.get("dietary_restriction") == "vegan":
        risks["b12"] = "high"
        risks["iron"] = "moderate"

    if user_profile.get("age", 30) > 50:
        risks["vitamin_d"] = "moderate"
        risks["calcium"] = "moderate"

    return risks


def get_supplement_recommendations(**user_profile) -> dict:
"""
    Get supplement recommendations based on profile.

    Args:
        **user_profile: User profile data

    Returns:
        Supplement recommendations
"""
    recommendations = []

    risks = check_deficiency_risk(**user_profile)

    if risks.get("b12") == "high":
        recommendations.append("Vitamin B12")
    if risks.get("vitamin_d") == "moderate":
        recommendations.append("Vitamin D3")
    if risks.get("iron") == "moderate":
        recommendations.append("Iron")

    return {"supplements": recommendations}

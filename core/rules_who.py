"""
WHO/EFSA/DRI Reference Tables and Standards

RU: Справочные таблицы норм ВОЗ/EFSA/DRI для нутриентов и физической активности.
EN: WHO/EFSA/DRI reference tables for nutrients and physical activity standards.

Data sources:
- WHO Global Recommendations on Physical Activity for Health (2010)
- WHO/FAO Diet, Nutrition and the Prevention of Chronic Diseases (2003)
- EFSA Dietary Reference Values (2010-2017)
- US Dietary Guidelines 2020-2025
- Institute of Medicine (IOM) DRI Tables

Last updated: January 2025
"""

from typing import Dict

from .targets import LifeStage, Sex

# WHO Physical Activity Recommendations (minutes per week)
WHO_ACTIVITY_GUIDELINES = {
    "adult": {
        "moderate_aerobic_min": 150,  # 150 min/week moderate OR
        "vigorous_aerobic_min": 75,  # 75 min/week vigorous
        "strength_sessions": 2,  # 2+ sessions/week
        "steps_daily": 8000,  # 8000-10000 steps/day
    },
    "elderly": {  # 65+ years
        "moderate_aerobic_min": 150,
        "vigorous_aerobic_min": 75,
        "strength_sessions": 2,
        "steps_daily": 7000,
    },
}

# WHO/EFSA Micronutrient RDA (Recommended Daily Allowances)
# Key: (sex, age_range, life_stage) -> nutrient values
WHO_MICRONUTRIENT_RDA = {
    # Adult women (19-50 years)
    ("female", "19-50", "adult"): {
        "iron_mg": 18.0,  # High due to menstruation
        "calcium_mg": 1000.0,
        "magnesium_mg": 310.0,
        "zinc_mg": 8.0,
        "potassium_mg": 3500.0,
        "iodine_ug": 150.0,
        "selenium_ug": 55.0,
        "folate_ug": 400.0,  # Critical for reproductive age
        "b12_ug": 2.4,
        "vitamin_d_iu": 600.0,
        "vitamin_a_ug": 700.0,
        "vitamin_c_mg": 75.0,
    },
    # Adult men (19-50 years)
    ("male", "19-50", "adult"): {
        "iron_mg": 8.0,  # Lower than women
        "calcium_mg": 1000.0,
        "magnesium_mg": 400.0,
        "zinc_mg": 11.0,  # Higher than women
        "potassium_mg": 3500.0,
        "iodine_ug": 150.0,
        "selenium_ug": 55.0,
        "folate_ug": 400.0,
        "b12_ug": 2.4,
        "vitamin_d_iu": 600.0,
        "vitamin_a_ug": 900.0,  # Higher than women
        "vitamin_c_mg": 90.0,  # Higher than women
    },
    # Adult women (51+ years) - post-menopausal
    ("female", "51+", "adult"): {
        "iron_mg": 8.0,  # Reduced after menopause
        "calcium_mg": 1200.0,  # Increased for bone health
        "magnesium_mg": 320.0,
        "zinc_mg": 8.0,
        "potassium_mg": 3500.0,
        "iodine_ug": 150.0,
        "selenium_ug": 55.0,
        "folate_ug": 400.0,
        "b12_ug": 2.4,
        "vitamin_d_iu": 800.0,  # Increased for elderly
        "vitamin_a_ug": 700.0,
        "vitamin_c_mg": 75.0,
    },
    # Adult men (51+ years)
    ("male", "51+", "adult"): {
        "iron_mg": 8.0,
        "calcium_mg": 1200.0,  # Increased for bone health
        "magnesium_mg": 420.0,
        "zinc_mg": 11.0,
        "potassium_mg": 3500.0,
        "iodine_ug": 150.0,
        "selenium_ug": 55.0,
        "folate_ug": 400.0,
        "b12_ug": 2.4,
        "vitamin_d_iu": 800.0,  # Increased for elderly
        "vitamin_a_ug": 900.0,
        "vitamin_c_mg": 90.0,
    },
    # Pregnant women (additional requirements)
    ("female", "19-50", "pregnant"): {
        "iron_mg": 27.0,  # Significantly increased
        "calcium_mg": 1000.0,
        "magnesium_mg": 350.0,  # Increased
        "zinc_mg": 11.0,  # Increased
        "potassium_mg": 3500.0,
        "iodine_ug": 220.0,  # Increased for fetal development
        "selenium_ug": 60.0,  # Increased
        "folate_ug": 600.0,  # Critical increase for neural tube
        "b12_ug": 2.6,  # Increased
        "vitamin_d_iu": 600.0,
        "vitamin_a_ug": 770.0,  # Slightly increased
        "vitamin_c_mg": 85.0,  # Increased
    },
    # Lactating women
    ("female", "19-50", "lactating"): {
        "iron_mg": 9.0,  # Lower than pregnancy
        "calcium_mg": 1000.0,
        "magnesium_mg": 310.0,
        "zinc_mg": 12.0,  # Highest requirement
        "potassium_mg": 3500.0,
        "iodine_ug": 290.0,  # Highest requirement
        "selenium_ug": 70.0,  # Highest requirement
        "folate_ug": 500.0,  # Still elevated
        "b12_ug": 2.8,  # Highest requirement
        "vitamin_d_iu": 600.0,
        "vitamin_a_ug": 1300.0,  # Significantly increased
        "vitamin_c_mg": 120.0,  # Significantly increased
    },
}

# WHO Hydration Guidelines (ml/kg body weight)
WHO_HYDRATION_GUIDELINES = {
    "base_ml_per_kg": 30,  # Base: 30ml per kg body weight
    "active_adjustment": 1.2,  # 20% increase for active individuals
    "hot_climate_adjustment": 1.3,  # 30% increase for hot climates
    "minimum_ml_daily": 1500,  # Absolute minimum
    "maximum_ml_daily": 4000,  # Upper safe limit
}

# Acceptable Macronutrient Distribution Ranges (AMDR) - WHO/IOM
WHO_MACRONUTRIENT_RANGES = {
    "protein_percent": (10, 35),  # 10-35% of total calories
    "fat_percent": (20, 35),  # 20-35% of total calories
    "carbs_percent": (45, 65),  # 45-65% of total calories
    "fiber_g_per_1000_cal": 14,  # 14g fiber per 1000 calories
}

# Goal-specific macro adjustments
GOAL_MACRO_ADJUSTMENTS = {
    "loss": {
        "protein_multiplier": 1.8,  # Higher protein for muscle preservation
        "fat_multiplier": 0.8,  # Lower fat
        "carbs_residual": True,  # Fill remaining calories with carbs
    },
    "maintain": {
        "protein_multiplier": 1.6,  # Moderate protein
        "fat_multiplier": 0.9,  # Moderate fat
        "carbs_residual": True,
    },
    "gain": {
        "protein_multiplier": 1.6,  # Moderate protein
        "fat_multiplier": 1.0,  # Normal fat
        "carbs_residual": True,  # Higher carbs for energy
    },
}


def get_age_category(age: int) -> str:
    """
    RU: Определяет возрастную категорию для выбора норм.
    EN: Determines age category for selecting appropriate norms.
    """
    if age < 19:
        return "under_19"
    elif age <= 50:
        return "19-50"
    else:
        return "51+"


def get_micronutrient_rda(sex: Sex, age: int, life_stage: LifeStage = "adult") -> Dict[str, float]:
    """
    RU: Получает рекомендуемые дневные нормы микронутриентов.
    EN: Gets recommended daily allowances for micronutrients.

    Args:
        sex: Biological sex
        age: Age in years
        life_stage: Life stage (adult, pregnant, lactating)

    Returns:
        Dictionary with micronutrient RDA values
    """
    age_category = get_age_category(age)
    key = (sex, age_category, life_stage)

    # Try exact match first
    if key in WHO_MICRONUTRIENT_RDA:
        return WHO_MICRONUTRIENT_RDA[key].copy()

    # Fallback to adult values if specific life stage not found
    fallback_key = (sex, age_category, "adult")
    if fallback_key in WHO_MICRONUTRIENT_RDA:
        return WHO_MICRONUTRIENT_RDA[fallback_key].copy()

    # Final fallback to adult male 19-50
    return WHO_MICRONUTRIENT_RDA[("male", "19-50", "adult")].copy()


def get_activity_guidelines(age: int) -> Dict[str, int]:
    """
    RU: Получает рекомендации ВОЗ по физической активности.
    EN: Gets WHO physical activity guidelines.
    """
    if age >= 65:
        return WHO_ACTIVITY_GUIDELINES["elderly"].copy()
    else:
        return WHO_ACTIVITY_GUIDELINES["adult"].copy()


def calculate_hydration_target(
    weight_kg: float, activity_level: str, climate: str = "temperate"
) -> int:
    """
    RU: Рассчитывает целевое потребление воды по весу и активности.
    EN: Calculates hydration target based on weight and activity.

    Args:
        weight_kg: Body weight in kilograms
        activity_level: Activity level string
        climate: Climate type (temperate, hot)

    Returns:
        Daily water target in milliliters
    """
    base_ml = weight_kg * WHO_HYDRATION_GUIDELINES["base_ml_per_kg"]

    # Adjust for activity level
    if activity_level in ["active", "very_active"]:
        base_ml *= WHO_HYDRATION_GUIDELINES["active_adjustment"]

    # Adjust for climate
    if climate == "hot":
        base_ml *= WHO_HYDRATION_GUIDELINES["hot_climate_adjustment"]

    # Apply bounds
    target_ml = max(
        WHO_HYDRATION_GUIDELINES["minimum_ml_daily"],
        min(WHO_HYDRATION_GUIDELINES["maximum_ml_daily"], int(base_ml)),
    )

    return target_ml


def validate_macro_distribution(protein_pct: float, fat_pct: float, carbs_pct: float) -> bool:
    """
    RU: Проверяет, соответствует ли распределение макросов рекомендациям ВОЗ.
    EN: Validates if macro distribution meets WHO guidelines.
    """
    ranges = WHO_MACRONUTRIENT_RANGES

    # Check if percentages sum to ~100%
    total = protein_pct + fat_pct + carbs_pct
    if abs(total - 100) > 2:  # Allow 2% tolerance
        return False

    # Check individual ranges
    if not (ranges["protein_percent"][0] <= protein_pct <= ranges["protein_percent"][1]):
        return False
    if not (ranges["fat_percent"][0] <= fat_pct <= ranges["fat_percent"][1]):
        return False
    if not (ranges["carbs_percent"][0] <= carbs_pct <= ranges["carbs_percent"][1]):
        return False

    return True


def get_fiber_target(total_calories: int) -> int:
    """
    RU: Рассчитывает целевое потребление клетчатки по калориям.
    EN: Calculates fiber target based on total calories.
    """
    return int((total_calories / 1000) * WHO_MACRONUTRIENT_RANGES["fiber_g_per_1000_cal"])


# Priority nutrients for deficiency monitoring
# Based on WHO global micronutrient deficiency prevalence
PRIORITY_NUTRIENTS = {
    "global": ["iron_mg", "vitamin_a_ug", "iodine_ug", "zinc_mg"],
    "women_reproductive": ["iron_mg", "folate_ug", "calcium_mg", "vitamin_d_iu"],
    "vegetarian": ["b12_ug", "iron_mg", "zinc_mg", "vitamin_d_iu"],
    "elderly": ["b12_ug", "vitamin_d_iu", "calcium_mg", "vitamin_c_mg"],
}


def get_priority_nutrients_for_profile(sex: Sex, age: int, diet_flags: set) -> list:
    """
    RU: Определяет приоритетные нутриенты для мониторинга на основе профиля.
    EN: Determines priority nutrients for monitoring based on user profile.
    """
    priorities = set(PRIORITY_NUTRIENTS["global"])

    # Add profile-specific priorities
    if sex == "female" and 15 <= age <= 49:
        priorities.update(PRIORITY_NUTRIENTS["women_reproductive"])

    if age >= 65:
        priorities.update(PRIORITY_NUTRIENTS["elderly"])

    if "VEG" in diet_flags:
        priorities.update(PRIORITY_NUTRIENTS["vegetarian"])

    return list(priorities)

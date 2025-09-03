"""
WHO-Based Recommendations Engine

RU: Движок персональных рекомендаций на основе норм ВОЗ.
EN: Personalized recommendations engine based on WHO standards.

This module builds individual nutrition targets from WHO/EFSA/DRI guidelines,
calculates nutrient coverage, and provides evidence-based recommendations
for optimizing nutrient intake through food choices.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from nutrition_core import calculate_all_bmr, calculate_all_tdee

from .rules_who import (
    GOAL_MACRO_ADJUSTMENTS,
    calculate_hydration_target,
    get_activity_guidelines,
    get_fiber_target,
    get_micronutrient_rda,
    get_priority_nutrients_for_profile,
)
from .targets import (
    ActivityTargets,
    MacroTargets,
    MicroTargets,
    NutrientCoverage,
    NutritionTargets,
    UserProfile,
)


def build_nutrition_targets(profile: UserProfile) -> NutritionTargets:
    """
    RU: Строит полные целевые значения питания на основе профиля пользователя.
    EN: Builds complete nutrition targets based on user profile.

    This is the main function that integrates WHO guidelines to create
    personalized daily targets for energy, macronutrients, micronutrients,
    hydration, and physical activity.

    Args:
        profile: User profile with demographics and goals

    Returns:
        Complete nutrition targets following WHO standards
    """
    # 1. Calculate energy requirements using validated BMR formulas
    bmr_results = calculate_all_bmr(
        profile.weight_kg, profile.height_cm, profile.age,
        profile.sex, profile.bodyfat
    )
    tdee_results = calculate_all_tdee(bmr_results, profile.activity)

    # Use Mifflin-St Jeor as primary (most accurate for modern populations)
    base_tdee = tdee_results["mifflin"]

    # 2. Adjust calories based on goal with safety bounds
    target_kcal = _calculate_target_calories(base_tdee, profile)

    # 3. Calculate macronutrient targets
    macros = _calculate_macro_targets(target_kcal, profile)

    # 4. Get micronutrient targets from WHO/EFSA guidelines
    micros = _calculate_micro_targets(profile)

    # 5. Calculate hydration target
    water_ml = calculate_hydration_target(profile.weight_kg, profile.activity)

    # 6. Get activity targets from WHO guidelines
    activity = _calculate_activity_targets(profile)

    return NutritionTargets(
        kcal_daily=target_kcal,
        macros=macros,
        water_ml_daily=water_ml,
        micros=micros,
        activity=activity,
        calculated_for=profile,
        calculation_date=datetime.now().isoformat()[:10]
    )


def _calculate_target_calories(base_tdee: float, profile: UserProfile) -> int:
    """
    RU: Рассчитывает целевую калорийность с учётом цели и безопасных границ.
    EN: Calculates target calories considering goals and safety bounds.
    """
    if profile.goal == "maintain":
        return int(round(base_tdee))

    elif profile.goal == "loss":
        deficit_pct = (profile.deficit_pct or 15) / 100.0
        target = base_tdee * (1 - deficit_pct)
        # WHO safety minimum: not below 1200 kcal for women, 1500 for men
        minimum = 1200 if profile.sex == "female" else 1500
        return max(minimum, int(round(target)))

    else:  # gain
        surplus_pct = (profile.surplus_pct or 12) / 100.0
        target = base_tdee * (1 + surplus_pct)
        # Reasonable upper bound to prevent excessive gain
        maximum = int(base_tdee * 1.3)  # Max 30% above TDEE
        return min(maximum, int(round(target)))


def _calculate_macro_targets(target_kcal: int, profile: UserProfile) -> MacroTargets:
    """
    RU: Рассчитывает цели по макронутриентам с учётом физиологических потребностей.
    EN: Calculates macronutrient targets based on physiological needs.
    """
    adjustments = GOAL_MACRO_ADJUSTMENTS[profile.goal]

    # Protein based on body weight and goal (WHO/IOM recommendations)
    protein_multiplier = adjustments["protein_multiplier"]
    protein_g = int(round(protein_multiplier * profile.weight_kg))

    # Fat based on body weight and goal
    fat_multiplier = adjustments["fat_multiplier"]
    fat_g = int(round(fat_multiplier * profile.weight_kg))

    # Carbohydrates fill remaining calories
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    carbs_kcal = target_kcal - protein_kcal - fat_kcal
    carbs_g = max(0, int(round(carbs_kcal / 4)))

    # Fiber based on total calories (WHO: 14g per 1000 kcal)
    fiber_g = get_fiber_target(target_kcal)

    return MacroTargets(
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        fiber_g=fiber_g
    )


def _calculate_micro_targets(profile: UserProfile) -> MicroTargets:
    """
    RU: Получает цели по микронутриентам из справочника ВОЗ.
    EN: Gets micronutrient targets from WHO reference tables.
    """
    rda = get_micronutrient_rda(profile.sex, profile.age, profile.life_stage)

    return MicroTargets(
        iron_mg=rda["iron_mg"],
        calcium_mg=rda["calcium_mg"],
        magnesium_mg=rda["magnesium_mg"],
        zinc_mg=rda["zinc_mg"],
        potassium_mg=rda["potassium_mg"],
        iodine_ug=rda["iodine_ug"],
        selenium_ug=rda["selenium_ug"],
        folate_ug=rda["folate_ug"],
        b12_ug=rda["b12_ug"],
        vitamin_d_iu=rda["vitamin_d_iu"],
        vitamin_a_ug=rda["vitamin_a_ug"],
        vitamin_c_mg=rda["vitamin_c_mg"]
    )


def _calculate_activity_targets(profile: UserProfile) -> ActivityTargets:
    """
    RU: Получает цели по физической активности из рекомендаций ВОЗ.
    EN: Gets physical activity targets from WHO guidelines.
    """
    guidelines = get_activity_guidelines(profile.age)

    return ActivityTargets(
        moderate_aerobic_min=guidelines["moderate_aerobic_min"],
        vigorous_aerobic_min=guidelines["vigorous_aerobic_min"],
        strength_sessions=guidelines["strength_sessions"],
        steps_daily=guidelines["steps_daily"]
    )


def score_nutrient_coverage(consumed_nutrients: Dict[str, float],
                          targets: NutritionTargets) -> Dict[str, NutrientCoverage]:
    """
    RU: Оценивает покрытие нутриентов в фактическом рационе.
    EN: Scores nutrient coverage in actual diet consumption.

    Args:
        consumed_nutrients: Actual nutrient intake (from food diary/menu)
        targets: Target nutrient values

    Returns:
        Coverage assessment for each nutrient
    """
    coverage = {}

    # Score macronutrients
    macro_mapping = {
        "protein_g": (targets.macros.protein_g, "g"),
        "fat_g": (targets.macros.fat_g, "g"),
        "carbs_g": (targets.macros.carbs_g, "g"),
        "fiber_g": (targets.macros.fiber_g, "g")
    }

    for nutrient, (target_val, unit) in macro_mapping.items():
        consumed = consumed_nutrients.get(nutrient, 0.0)
        coverage[nutrient] = NutrientCoverage(
            nutrient_name=nutrient,
            target_amount=target_val,
            consumed_amount=consumed,
            unit=unit
        )

    # Score micronutrients
    micro_mapping = {
        "iron_mg": (targets.micros.iron_mg, "mg"),
        "calcium_mg": (targets.micros.calcium_mg, "mg"),
        "magnesium_mg": (targets.micros.magnesium_mg, "mg"),
        "zinc_mg": (targets.micros.zinc_mg, "mg"),
        "potassium_mg": (targets.micros.potassium_mg, "mg"),
        "iodine_ug": (targets.micros.iodine_ug, "μg"),
        "selenium_ug": (targets.micros.selenium_ug, "μg"),
        "folate_ug": (targets.micros.folate_ug, "μg"),
        "b12_ug": (targets.micros.b12_ug, "μg"),
        "vitamin_d_iu": (targets.micros.vitamin_d_iu, "IU"),
        "vitamin_a_ug": (targets.micros.vitamin_a_ug, "μg"),
        "vitamin_c_mg": (targets.micros.vitamin_c_mg, "mg")
    }

    for nutrient, (target_val, unit) in micro_mapping.items():
        consumed = consumed_nutrients.get(nutrient, 0.0)
        coverage[nutrient] = NutrientCoverage(
            nutrient_name=nutrient,
            target_amount=target_val,
            consumed_amount=consumed,
            unit=unit
        )

    return coverage


def generate_deficiency_recommendations(coverage: Dict[str, NutrientCoverage],
                                      profile: UserProfile,
                                      lang: str = "en") -> List[str]:
    """
    RU: Генерирует рекомендации по устранению дефицитов через продукты питания.
    EN: Generates food-based recommendations for addressing nutrient deficiencies.

    Focuses on whole foods rather than supplements, following WHO's food-first approach.
    """
    recommendations = []

    # Get priority nutrients for this profile
    priority_nutrients = get_priority_nutrients_for_profile(
        profile.sex, profile.age, profile.diet_flags
    )

    # Food sources mapping (could be expanded into a database)
    food_sources = _get_nutrient_food_sources(lang)

    for nutrient_name, nutrient_coverage in coverage.items():
        if (nutrient_coverage.status == "deficient" and
            nutrient_name in priority_nutrients):

            if nutrient_name in food_sources:
                sources = food_sources[nutrient_name]

                if lang == "ru":
                    rec = f"Для {nutrient_coverage.nutrient_name}: {', '.join(sources[:3])}"
                else:
                    rec = f"For {nutrient_coverage.nutrient_name}: {', '.join(sources[:3])}"

                # Add diet-specific adaptations
                if "VEG" in profile.diet_flags:
                    rec = _adapt_for_vegetarian(rec, nutrient_name, lang)

                recommendations.append(rec)

    return recommendations


def _get_nutrient_food_sources(lang: str = "en") -> Dict[str, List[str]]:
    """
    RU: Справочник лучших пищевых источников нутриентов.
    EN: Reference of best food sources for nutrients.
    """
    if lang == "ru":
        return {
            "iron_mg": ["говядина", "чечевица", "шпинат", "гречка", "тыквенные семечки"],
            "calcium_mg": ["творог", "кунжут", "брокколи", "сардины", "миндаль"],
            "folate_ug": ["бобовые", "листовая зелень", "авокадо", "спаржа"],
            "vitamin_d_iu": ["жирная рыба", "яичные желтки", "грибы"],
            "b12_ug": ["мясо", "рыба", "молочные продукты", "яйца"],
            "iodine_ug": ["морская капуста", "рыба", "йодированная соль"],
            "zinc_mg": ["мясо", "орехи", "семена", "бобовые"],
            "magnesium_mg": ["орехи", "семена", "темная зелень", "цельные зерна"]
        }
    else:
        return {
            "iron_mg": ["lean red meat", "lentils", "spinach", "pumpkin seeds",
                       "fortified cereals"],
            "calcium_mg": ["dairy products", "leafy greens", "sardines", "almonds",
                          "fortified plant milk"],
            "folate_ug": ["legumes", "leafy greens", "avocado", "asparagus",
                         "fortified grains"],
            "vitamin_d_iu": ["fatty fish", "egg yolks", "fortified milk",
                            "mushrooms"],
            "b12_ug": ["meat", "fish", "dairy", "eggs", "nutritional yeast"],
            "iodine_ug": ["seaweed", "fish", "iodized salt", "dairy"],
            "zinc_mg": ["meat", "nuts", "seeds", "legumes", "whole grains"],
            "magnesium_mg": ["nuts", "seeds", "dark leafy greens", "whole grains",
                             "dark chocolate"]
        }


def _adapt_for_vegetarian(recommendation: str, nutrient: str, lang: str) -> str:
    """
    RU: Адаптирует рекомендации для вегетарианцев.
    EN: Adapts recommendations for vegetarians.
    """
    vegetarian_swaps = {
        "en": {
            "iron_mg": "combine with vitamin C-rich foods for better absorption",
            "b12_ug": "consider fortified nutritional yeast or fortified plant milk",
            "zinc_mg": "soak legumes and grains to improve absorption"
        },
        "ru": {
            "iron_mg": "сочетайте с продуктами, богатыми витамином C, для лучшего усвоения",
            "b12_ug": "рассмотрите обогащённые дрожжи или растительное молоко",
            "zinc_mg": "замачивайте бобовые и зерна для улучшения усвоения"
        }
    }

    if nutrient in vegetarian_swaps[lang]:
        return f"{recommendation} ({vegetarian_swaps[lang][nutrient]})"

    return recommendation


def calculate_weekly_coverage(daily_coverages: List[Dict[str, NutrientCoverage]]
                             ) -> Dict[str, float]:
    """
    RU: Рассчитывает среднее покрытие нутриентов за неделю.
    EN: Calculates average nutrient coverage over a week.

    This allows for day-to-day variation while ensuring weekly adequacy,
    which is more realistic and flexible for meal planning.
    """
    if not daily_coverages:
        return {}

    # Get all nutrient names from first day
    nutrient_names = list(daily_coverages[0].keys())
    weekly_averages = {}

    for nutrient in nutrient_names:
        total_coverage = sum(
            day_coverage[nutrient].coverage_percent
            for day_coverage in daily_coverages
            if nutrient in day_coverage
        )
        weekly_averages[nutrient] = round(total_coverage / len(daily_coverages), 1)

    return weekly_averages


def validate_targets_safety(targets: NutritionTargets) -> List[str]:
    """
    RU: Проверяет безопасность рассчитанных целей.
    EN: Validates safety of calculated targets.

    Returns list of warnings if targets exceed safe limits.
    """
    warnings = []

    # Check calorie bounds
    if targets.kcal_daily < 1200:
        warnings.append("Calorie target below safe minimum (1200 kcal)")
    elif targets.kcal_daily > 4000:
        warnings.append("Calorie target very high (>4000 kcal)")

    # Check macro consistency
    if not targets.validate_consistency():
        warnings.append("Macro calories don't match target calories")

    # Check extreme protein levels
    protein_kcal_pct = (targets.macros.protein_g * 4) / targets.kcal_daily * 100
    if protein_kcal_pct > 35:
        warnings.append("Protein intake very high (>35% of calories)")

    # Check hydration bounds
    if targets.water_ml_daily < 1500:
        warnings.append("Hydration target below minimum (1500ml)")
    elif targets.water_ml_daily > 4000:
        warnings.append("Hydration target above safe maximum (4000ml)")

    return warnings

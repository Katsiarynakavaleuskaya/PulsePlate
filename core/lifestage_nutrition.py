"""
Life-Stage Nutrition Guidelines

RU: Рекомендации по питанию для разных этапов жизни.
EN: Nutrition guidelines for different life stages.

This module provides specialized nutrition recommendations for children,
pregnant women, lactating mothers, and elderly populations based on WHO,
EFSA, and national dietary guidelines.

MEDICAL DISCLAIMER: This application is NOT intended for medical diagnosis,
treatment, or prescription. Always consult qualified healthcare professionals
for nutrition advice during pregnancy, childhood, and elderly care.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from .targets import UserProfile


class LifeStage(Enum):
    """
    RU: Этапы жизни с особыми потребностями в питании.
    EN: Life stages with special nutritional needs.
    """

    CHILD_2_5 = "child_2_5"  # 2-5 years
    CHILD_6_11 = "child_6_11"  # 6-11 years
    ADOLESCENT_12_18 = "adolescent"  # 12-18 years
    ADULT = "adult"  # 19-64 years
    PREGNANT_T1 = "pregnant_t1"  # 1st trimester
    PREGNANT_T2 = "pregnant_t2"  # 2nd trimester
    PREGNANT_T3 = "pregnant_t3"  # 3rd trimester
    LACTATING = "lactating"  # Breastfeeding
    ELDERLY = "elderly"  # 65+ years


@dataclass(frozen=True)
class LifeStageRequirements:
    """
    RU: Требования питания для конкретного этапа жизни.
    EN: Nutritional requirements for specific life stage.
    """

    # Energy and macronutrients
    energy_kcal_per_kg: Optional[float]  # For children
    energy_additional_kcal: Optional[int]  # Additional for pregnancy/lactation

    # Protein requirements
    protein_g_per_kg: float

    # Key micronutrients with increased needs
    folate_ug: float
    iron_mg: float
    calcium_mg: float
    vitamin_d_iu: float
    iodine_ug: float

    # Special considerations
    special_nutrients: Dict[str, float]  # Additional nutrients of concern
    avoid_foods: List[str]  # Foods to avoid/limit
    emphasize_foods: List[str]  # Foods to emphasize
    feeding_notes: List[str]  # Special feeding considerations


class LifeStageNutritionCalculator:
    """
    RU: Калькулятор питания для разных этапов жизни на основе WHO/EFSA.
    EN: Life-stage nutrition calculator based on WHO/EFSA guidelines.
    """

    # WHO/EFSA-based requirements by life stage
    LIFESTAGE_REQUIREMENTS = {
        LifeStage.CHILD_2_5: LifeStageRequirements(
            energy_kcal_per_kg=90,  # ~90 kcal/kg for active toddlers
            energy_additional_kcal=None,
            protein_g_per_kg=1.0,  # WHO recommendation
            folate_ug=150,  # EFSA
            iron_mg=7,  # EFSA
            calcium_mg=450,  # EFSA
            vitamin_d_iu=600,  # EFSA
            iodine_ug=90,  # WHO
            special_nutrients={
                "zinc_mg": 4,
                "vitamin_a_ug": 300,
                "vitamin_c_mg": 30,
                "omega3_dha_mg": 100,
            },
            avoid_foods=["honey", "whole_nuts", "high_mercury_fish", "excessive_juice"],
            emphasize_foods=[
                "breast_milk",
                "iron_fortified_foods",
                "fruits",
                "vegetables",
                "whole_grains",
            ],
            feeding_notes=[
                "Transition to family foods by age 2",
                "Offer variety to prevent picky eating",
                "Monitor growth curves regularly",
                "Limit processed foods and added sugars",
            ],
        ),
        LifeStage.CHILD_6_11: LifeStageRequirements(
            energy_kcal_per_kg=70,  # ~70 kcal/kg for school age
            energy_additional_kcal=None,
            protein_g_per_kg=0.95,  # WHO recommendation
            folate_ug=200,  # EFSA
            iron_mg=9,  # EFSA
            calcium_mg=800,  # EFSA - critical for bone development
            vitamin_d_iu=600,  # EFSA
            iodine_ug=120,  # WHO
            special_nutrients={
                "zinc_mg": 7,
                "vitamin_a_ug": 500,
                "vitamin_c_mg": 45,
                "magnesium_mg": 200,
            },
            avoid_foods=[
                "excessive_caffeine",
                "energy_drinks",
                "high_sodium_processed",
            ],
            emphasize_foods=[
                "dairy",
                "lean_proteins",
                "colorful_vegetables",
                "whole_grains",
                "calcium_rich",
            ],
            feeding_notes=[
                "Establish healthy eating patterns",
                "Encourage family meals",
                "Teach food preparation skills",
                "Balance treats with nutritious foods",
            ],
        ),
        LifeStage.ADOLESCENT_12_18: LifeStageRequirements(
            energy_kcal_per_kg=50,  # ~50 kcal/kg for adolescents
            energy_additional_kcal=None,
            protein_g_per_kg=0.85,  # WHO recommendation
            folate_ug=330,  # EFSA - increased for growth
            iron_mg=15,  # EFSA - especially for females
            calcium_mg=1150,  # EFSA - peak bone mass formation
            vitamin_d_iu=600,  # EFSA
            iodine_ug=150,  # WHO
            special_nutrients={
                "zinc_mg": 12,
                "vitamin_a_ug": 700,
                "vitamin_c_mg": 65,
                "magnesium_mg": 300,
            },
            avoid_foods=["excessive_fast_food", "energy_drinks", "restrictive_dieting"],
            emphasize_foods=[
                "iron_rich_foods",
                "calcium_sources",
                "lean_proteins",
                "complex_carbs",
            ],
            feeding_notes=[
                "Support growth spurt nutritional needs",
                "Address body image concerns positively",
                "Encourage sports nutrition if active",
                "Monitor for eating disorders",
            ],
        ),
        LifeStage.ADULT: LifeStageRequirements(
            energy_kcal_per_kg=None,  # Use BMR-based calculation
            energy_additional_kcal=None,
            protein_g_per_kg=0.8,  # WHO recommendation for adults
            folate_ug=400,  # WHO/DRI
            iron_mg=8,  # WHO (varies by sex)
            calcium_mg=1000,  # WHO
            vitamin_d_iu=600,  # EFSA
            iodine_ug=150,  # WHO
            special_nutrients={
                "vitamin_b12_ug": 2.4,
                "zinc_mg": 8,
                "magnesium_mg": 400,
                "vitamin_c_mg": 75,
            },
            avoid_foods=["excessive_alcohol", "high_sodium_processed", "trans_fats"],
            emphasize_foods=[
                "whole_grains",
                "lean_proteins",
                "fruits",
                "vegetables",
                "healthy_fats",
            ],
            feeding_notes=[
                "Follow balanced dietary patterns",
                "Maintain healthy weight",
                "Stay physically active",
                "Monitor for chronic disease risk factors",
            ],
        ),
        LifeStage.PREGNANT_T1: LifeStageRequirements(
            energy_kcal_per_kg=None,
            energy_additional_kcal=0,  # No additional calories in T1
            protein_g_per_kg=1.0,  # Base requirement
            folate_ug=600,  # Critical for neural tube development
            iron_mg=27,  # Significantly increased
            calcium_mg=1000,  # Maintained from pre-pregnancy
            vitamin_d_iu=600,  # EFSA
            iodine_ug=220,  # WHO - increased for fetal brain development
            special_nutrients={
                "vitamin_b12_ug": 2.6,
                "choline_mg": 450,
                "omega3_dha_mg": 200,
                "zinc_mg": 11,
            },
            avoid_foods=[
                "alcohol",
                "high_mercury_fish",
                "raw_fish_meat",
                "unpasteurized_dairy",
                "excess_caffeine",
            ],
            emphasize_foods=[
                "folate_rich_foods",
                "lean_proteins",
                "whole_grains",
                "prenatal_vitamins",
            ],
            feeding_notes=[
                "Take prenatal vitamins with folate",
                "Manage morning sickness with small frequent meals",
                "Stay hydrated",
                "Focus on nutrient density over quantity",
            ],
        ),
        LifeStage.PREGNANT_T2: LifeStageRequirements(
            energy_kcal_per_kg=None,
            energy_additional_kcal=340,  # Additional 340 kcal/day
            protein_g_per_kg=1.1,  # Increased protein needs
            folate_ug=600,  # Continued high needs
            iron_mg=27,  # Continued high needs
            calcium_mg=1000,  # Maintained
            vitamin_d_iu=600,  # EFSA
            iodine_ug=220,  # WHO
            special_nutrients={
                "vitamin_b12_ug": 2.6,
                "choline_mg": 450,
                "omega3_dha_mg": 200,
                "zinc_mg": 11,
            },
            avoid_foods=[
                "alcohol",
                "high_mercury_fish",
                "raw_fish_meat",
                "unpasteurized_dairy",
                "excess_caffeine",
            ],
            emphasize_foods=[
                "protein_rich_foods",
                "iron_rich_foods",
                "healthy_fats",
                "complex_carbs",
            ],
            feeding_notes=[
                "Focus on steady weight gain",
                "Continue prenatal vitamins",
                "Monitor blood sugar if at risk for GDM",
                "Eat regular balanced meals",
            ],
        ),
        LifeStage.PREGNANT_T3: LifeStageRequirements(
            energy_kcal_per_kg=None,
            energy_additional_kcal=450,  # Additional 450 kcal/day
            protein_g_per_kg=1.1,  # Increased protein needs
            folate_ug=600,  # Continued high needs
            iron_mg=27,  # Continued high needs
            calcium_mg=1000,  # Maintained
            vitamin_d_iu=600,  # EFSA
            iodine_ug=220,  # WHO
            special_nutrients={
                "vitamin_b12_ug": 2.6,
                "choline_mg": 450,
                "omega3_dha_mg": 200,
                "zinc_mg": 11,
            },
            avoid_foods=[
                "alcohol",
                "high_mercury_fish",
                "raw_fish_meat",
                "unpasteurized_dairy",
                "excess_caffeine",
            ],
            emphasize_foods=[
                "protein_rich_foods",
                "calcium_rich_foods",
                "healthy_fats",
                "fiber_rich_foods",
            ],
            feeding_notes=[
                "Manage heartburn with smaller frequent meals",
                "Prepare for breastfeeding nutrition",
                "Monitor for excessive weight gain",
                "Stay active as comfortable",
            ],
        ),
        LifeStage.LACTATING: LifeStageRequirements(
            energy_kcal_per_kg=None,
            energy_additional_kcal=500,  # Additional 500 kcal/day
            protein_g_per_kg=1.3,  # Highest protein needs
            folate_ug=500,  # Continued elevated needs
            iron_mg=9,  # Returns to lower levels
            calcium_mg=1000,  # Critical for bone health
            vitamin_d_iu=600,  # EFSA
            iodine_ug=290,  # WHO - highest needs for milk production
            special_nutrients={
                "vitamin_b12_ug": 2.8,
                "choline_mg": 550,
                "omega3_dha_mg": 200,
                "zinc_mg": 12,
            },
            avoid_foods=["excessive_alcohol", "high_mercury_fish", "excess_caffeine"],
            emphasize_foods=[
                "protein_rich_foods",
                "calcium_sources",
                "healthy_fats",
                "hydrating_foods",
            ],
            feeding_notes=[
                "Maintain adequate hydration (extra 700ml/day)",
                "Continue prenatal vitamins while breastfeeding",
                "Eat to hunger and thirst",
                "Monitor infant's growth and development",
            ],
        ),
        LifeStage.ELDERLY: LifeStageRequirements(
            energy_kcal_per_kg=30,  # ~30 kcal/kg (lower due to reduced activity)
            energy_additional_kcal=None,
            protein_g_per_kg=1.2,  # Higher than adults to prevent sarcopenia
            folate_ug=400,  # Standard adult needs
            iron_mg=8,  # Standard adult needs
            calcium_mg=1200,  # Increased for bone health
            vitamin_d_iu=800,  # Increased for bone health and immunity
            iodine_ug=150,  # WHO standard
            special_nutrients={
                "vitamin_b12_ug": 2.4,  # Absorption may be impaired
                "vitamin_b6_mg": 1.7,
                "magnesium_mg": 420,
                "potassium_mg": 4700,
            },
            avoid_foods=["excess_sodium", "undercooked_foods", "grapefruit_if_on_meds"],
            emphasize_foods=[
                "high_protein_foods",
                "calcium_rich",
                "vitamin_d_fortified",
                "fiber_rich",
                "colorful_vegetables",
            ],
            feeding_notes=[
                "Focus on nutrient-dense foods",
                "Address chewing/swallowing difficulties",
                "Monitor for medication-food interactions",
                "Encourage social eating to maintain appetite",
                "Consider B12 supplementation if absorption impaired",
            ],
        ),
    }

    @classmethod
    def calculate_lifestage_targets(
        cls, profile: UserProfile, life_stage: LifeStage
    ) -> Dict[str, any]:
        """
        RU: Рассчитывает цели питания для конкретного этапа жизни.
        EN: Calculate nutrition targets for specific life stage.
        """
        requirements = cls.LIFESTAGE_REQUIREMENTS[life_stage]
        weight_kg = profile.weight_kg

        # Calculate energy needs
        if requirements.energy_kcal_per_kg:
            # Children/elderly - based on weight
            base_energy = requirements.energy_kcal_per_kg * weight_kg
        else:
            # Adults - use BMR-based calculation
            from .recommendations import build_nutrition_targets

            adult_targets = build_nutrition_targets(profile)
            base_energy = adult_targets.kcal_daily

        # Add additional calories if needed (pregnancy/lactation)
        total_energy = base_energy + (requirements.energy_additional_kcal or 0)

        # Calculate protein needs
        protein_g = requirements.protein_g_per_kg * weight_kg

        # Calculate micronutrient targets
        micronutrient_targets = {
            "folate_ug": requirements.folate_ug,
            "iron_mg": requirements.iron_mg,
            "calcium_mg": requirements.calcium_mg,
            "vitamin_d_iu": requirements.vitamin_d_iu,
            "iodine_ug": requirements.iodine_ug,
            **requirements.special_nutrients,
        }

        # Calculate remaining macros
        protein_kcal = protein_g * 4
        fat_kcal = total_energy * 0.25  # 25% from fat (adjustable)
        carb_kcal = total_energy - protein_kcal - fat_kcal

        fat_g = fat_kcal / 9
        carb_g = max(0, carb_kcal / 4)

        return {
            "life_stage": life_stage.value,
            "energy_needs": {
                "total_kcal": int(total_energy),
                "base_kcal": int(base_energy),
                "additional_kcal": requirements.energy_additional_kcal or 0,
            },
            "macronutrients": {
                "protein_g": int(protein_g),
                "fat_g": int(fat_g),
                "carbs_g": int(carb_g),
                "protein_per_kg": requirements.protein_g_per_kg,
            },
            "key_micronutrients": micronutrient_targets,
            "food_guidance": {
                "avoid_foods": requirements.avoid_foods,
                "emphasize_foods": requirements.emphasize_foods,
                "feeding_notes": requirements.feeding_notes,
            },
            "medical_disclaimer": (
                "This is general nutritional guidance based on WHO/EFSA recommendations. "
                "Individual needs vary significantly, especially during pregnancy, childhood, "
                "and elderly years. Always consult qualified healthcare professionals including "
                "registered dietitians, pediatricians, obstetricians, or geriatricians for "
                "personalized medical and nutritional advice. This is NOT medical diagnosis or treatment."
            ),
            "professional_referral_note": (
                "Consider consulting: Registered Dietitian, Pediatrician (children), "
                "Obstetrician/Midwife (pregnancy), Geriatrician (elderly), or Primary Care Physician"
            ),
        }

    @classmethod
    def get_appropriate_lifestage(
        cls,
        age: int,
        sex: str,
        is_pregnant: bool = False,
        is_lactating: bool = False,
        trimester: Optional[int] = None,
    ) -> LifeStage:
        """
        RU: Определяет подходящий этап жизни на основе возраста и состояния.
        EN: Determine appropriate life stage based on age and conditions.
        """
        if is_pregnant and trimester:
            if trimester == 1:
                return LifeStage.PREGNANT_T1
            elif trimester == 2:
                return LifeStage.PREGNANT_T2
            elif trimester == 3:
                return LifeStage.PREGNANT_T3

        if is_lactating:
            return LifeStage.LACTATING

        if age < 2:
            raise ValueError(
                "This app is not suitable for infants under 2 years. Consult pediatrician."
            )
        elif age <= 5:
            return LifeStage.CHILD_2_5
        elif age <= 11:
            return LifeStage.CHILD_6_11
        elif age <= 18:
            return LifeStage.ADOLESCENT_12_18
        elif age <= 64:
            return LifeStage.ADULT
        else:
            return LifeStage.ELDERLY


def get_lifestage_recommendations(
    profile: UserProfile,
    is_pregnant: bool = False,
    is_lactating: bool = False,
    trimester: Optional[int] = None,
) -> Dict[str, any]:
    """
    RU: Получить рекомендации по питанию для этапа жизни.
    EN: Get life-stage nutrition recommendations.
    """
    try:
        life_stage = LifeStageNutritionCalculator.get_appropriate_lifestage(
            profile.age, profile.sex, is_pregnant, is_lactating, trimester
        )

        return LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, life_stage
        )

    except ValueError as e:
        return {
            "error": str(e),
            "recommendation": "Please consult appropriate healthcare professional",
            "life_stage": "not_applicable",
        }


# Age group mappings for easy reference
PEDIATRIC_AGES = {
    "toddler": (2, 5),
    "child": (6, 11),
    "adolescent": (12, 18),
}

ADULT_SPECIAL_CONDITIONS = ["pregnant", "lactating", "elderly"]

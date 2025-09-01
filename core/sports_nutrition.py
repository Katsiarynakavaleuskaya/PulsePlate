"""
Sports Nutrition Guidelines Integration

RU: Интеграция руководящих принципов спортивного питания от NASM, ACSM, IFPA.
EN: Integration of sports nutrition guidelines from NASM, ACSM, IFPA.

This module provides specialized nutrition recommendations for different sports,
training phases, and athletic populations based on evidence-based guidelines
from major sports nutrition organizations.

DISCLAIMER: This is NOT medical advice. Always consult qualified healthcare
professionals for personalized nutrition and medical guidance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from .targets import UserProfile


class SportCategory(Enum):
    """
    RU: Категории видов спорта по энергетическим потребностям.
    EN: Sport categories by energy system demands.
    """
    ENDURANCE = "endurance"  # Marathon, cycling, triathlon
    STRENGTH = "strength"    # Powerlifting, weightlifting
    POWER = "power"         # Sprinting, jumping, throwing
    TEAM = "team"           # Football, basketball, soccer
    AESTHETIC = "aesthetic"  # Gymnastics, figure skating, bodybuilding
    COMBAT = "combat"       # Boxing, wrestling, martial arts
    RECREATIONAL = "recreational"  # General fitness, amateur sports


class TrainingPhase(Enum):
    """
    RU: Фазы тренировочного процесса.
    EN: Training periodization phases.
    """
    OFF_SEASON = "off_season"
    PRE_SEASON = "pre_season"
    IN_SEASON = "in_season"
    PEAK = "peak"
    RECOVERY = "recovery"


@dataclass(frozen=True)
class SportsNutritionTargets:
    """
    RU: Специализированные цели спортивного питания.
    EN: Specialized sports nutrition targets.
    """
    # Enhanced macronutrient targets
    protein_g_per_kg: float  # g/kg body weight
    carbs_g_per_kg: float   # g/kg body weight
    fat_g_per_kg: float     # g/kg body weight

    # Hydration requirements
    fluid_ml_per_hour_training: int
    electrolyte_replacement: bool

    # Timing recommendations
    pre_workout_carbs_g: Optional[float]
    post_workout_protein_g: Optional[float]
    post_workout_carbs_g: Optional[float]

    # Special considerations
    creatine_recommended: bool
    caffeine_timing: Optional[str]
    meal_frequency: int

    # Competition/event specific
    carb_loading_recommended: bool
    weight_cutting_considerations: Optional[str]


class SportsNutritionCalculator:
    """
    RU: Калькулятор спортивного питания на основе рекомендаций NASM/ACSM/IFPA.
    EN: Sports nutrition calculator based on NASM/ACSM/IFPA guidelines.
    """

    # NASM/ACSM Evidence-Based Guidelines
    SPORT_PROTEIN_REQUIREMENTS = {
        # Protein g/kg/day - based on ACSM/AND/DC Position Statement
        SportCategory.ENDURANCE: (1.2, 1.4),      # Endurance athletes
        SportCategory.STRENGTH: (1.6, 2.2),       # Strength/power athletes
        SportCategory.POWER: (1.6, 2.0),          # Power athletes
        SportCategory.TEAM: (1.4, 1.7),           # Team sport athletes
        SportCategory.AESTHETIC: (1.4, 2.0),      # Weight-class/aesthetic sports
        SportCategory.COMBAT: (1.6, 2.2),         # Combat sports (often cutting weight)
        SportCategory.RECREATIONAL: (1.2, 1.6),   # Recreational athletes
    }

    SPORT_CARB_REQUIREMENTS = {
        # Carbohydrate g/kg/day - based on training volume
        SportCategory.ENDURANCE: (6, 10),         # High volume endurance
        SportCategory.STRENGTH: (3, 5),           # Moderate carb needs
        SportCategory.POWER: (3, 5),              # Moderate carb needs
        SportCategory.TEAM: (5, 8),               # Moderate to high
        SportCategory.AESTHETIC: (3, 7),          # Variable based on goals
        SportCategory.COMBAT: (5, 7),             # Moderate to high
        SportCategory.RECREATIONAL: (3, 5),       # Moderate needs
    }

    HYDRATION_GUIDELINES = {
        # Fluid ml/hour during training - ACSM guidelines
        SportCategory.ENDURANCE: 600,             # High sweat rates
        SportCategory.STRENGTH: 200,              # Lower fluid needs
        SportCategory.POWER: 300,                 # Moderate needs
        SportCategory.TEAM: 500,                  # Variable intensity
        SportCategory.AESTHETIC: 300,             # Moderate needs
        SportCategory.COMBAT: 500,                # High intensity, often dehydrated
        SportCategory.RECREATIONAL: 300,          # Moderate needs
    }

    @classmethod
    def calculate_sports_targets(cls,
                               profile: UserProfile,
                               sport: SportCategory,
                               training_phase: TrainingPhase = TrainingPhase.IN_SEASON,
                               training_hours_per_week: float = 5.0) -> SportsNutritionTargets:
        """
        RU: Рассчитывает цели спортивного питания.
        EN: Calculate sports nutrition targets.

        Args:
            profile: User profile with basic information
            sport: Sport category
            training_phase: Current training phase
            training_hours_per_week: Weekly training volume

        Returns:
            Specialized sports nutrition targets
        """
        weight_kg = profile.weight_kg

        # Get base requirements for sport
        protein_range = cls.SPORT_PROTEIN_REQUIREMENTS[sport]
        carb_range = cls.SPORT_CARB_REQUIREMENTS[sport]
        base_hydration = cls.HYDRATION_GUIDELINES[sport]

        # Adjust for training phase
        protein_multiplier, carb_multiplier = cls._get_phase_multipliers(training_phase)

        # Adjust for training volume (hours per week)
        volume_multiplier = min(1.2, 1.0 + (training_hours_per_week - 5) * 0.02)

        # Calculate targets
        protein_per_kg = protein_range[0] + (protein_range[1] - protein_range[0]) * protein_multiplier
        carb_per_kg = carb_range[0] + (carb_range[1] - carb_range[0]) * carb_multiplier

        # Apply volume adjustment
        protein_per_kg *= volume_multiplier
        carb_per_kg *= volume_multiplier

        # Fat fills remaining calories (20-35% of total)
        fat_per_kg = cls._calculate_fat_needs(sport, profile.goal)

        # Hydration adjustments
        fluid_per_hour = int(base_hydration * volume_multiplier)

        # Pre/post workout nutrition
        pre_workout_carbs = cls._calculate_pre_workout_carbs(sport, carb_per_kg * weight_kg)
        post_workout_protein = cls._calculate_post_workout_protein(sport, protein_per_kg * weight_kg)
        post_workout_carbs = cls._calculate_post_workout_carbs(sport, carb_per_kg * weight_kg)

        return SportsNutritionTargets(
            protein_g_per_kg=round(protein_per_kg, 1),
            carbs_g_per_kg=round(carb_per_kg, 1),
            fat_g_per_kg=round(fat_per_kg, 1),
            fluid_ml_per_hour_training=fluid_per_hour,
            electrolyte_replacement=training_hours_per_week > 1.0,
            pre_workout_carbs_g=pre_workout_carbs,
            post_workout_protein_g=post_workout_protein,
            post_workout_carbs_g=post_workout_carbs,
            creatine_recommended=sport in [SportCategory.STRENGTH, SportCategory.POWER, SportCategory.COMBAT],
            caffeine_timing=cls._get_caffeine_timing(sport),
            meal_frequency=cls._get_meal_frequency(sport, training_hours_per_week),
            carb_loading_recommended=sport == SportCategory.ENDURANCE,
            weight_cutting_considerations=cls._get_weight_cutting_advice(sport) if sport in [SportCategory.COMBAT, SportCategory.AESTHETIC] else None
        )

    @staticmethod
    def _get_phase_multipliers(phase: TrainingPhase) -> tuple[float, float]:
        """Get protein and carb multipliers for training phase."""
        multipliers = {
            TrainingPhase.OFF_SEASON: (0.7, 0.6),     # Lower intensity
            TrainingPhase.PRE_SEASON: (0.8, 0.8),     # Building phase
            TrainingPhase.IN_SEASON: (1.0, 1.0),      # Full requirements
            TrainingPhase.PEAK: (1.0, 1.2),           # Peak carb needs
            TrainingPhase.RECOVERY: (0.8, 0.7),       # Recovery phase
        }
        return multipliers[phase]

    @staticmethod
    def _calculate_fat_needs(sport: SportCategory, goal: str) -> float:
        """Calculate fat needs in g/kg."""
        base_fat = {
            SportCategory.ENDURANCE: 1.0,    # Moderate fat for endurance
            SportCategory.STRENGTH: 1.2,     # Higher fat for strength
            SportCategory.POWER: 1.0,        # Moderate fat
            SportCategory.TEAM: 1.0,         # Moderate fat
            SportCategory.AESTHETIC: 0.8,    # Lower fat for body comp
            SportCategory.COMBAT: 1.0,       # Moderate fat
            SportCategory.RECREATIONAL: 1.0, # Moderate fat
        }

        fat_per_kg = base_fat[sport]

        # Adjust for goal
        if goal == "loss":
            fat_per_kg *= 0.8
        elif goal == "gain":
            fat_per_kg *= 1.2

        return max(0.8, fat_per_kg)  # Minimum for health

    @staticmethod
    def _calculate_pre_workout_carbs(sport: SportCategory, daily_carbs: float) -> Optional[float]:
        """Calculate pre-workout carb needs."""
        if sport in [SportCategory.ENDURANCE, SportCategory.TEAM]:
            return round(daily_carbs * 0.15, 1)  # 15% of daily carbs 1-2h before
        elif sport in [SportCategory.STRENGTH, SportCategory.POWER]:
            return round(daily_carbs * 0.10, 1)  # 10% of daily carbs
        return None

    @staticmethod
    def _calculate_post_workout_protein(sport: SportCategory, daily_protein: float) -> Optional[float]:
        """Calculate post-workout protein needs."""
        return round(daily_protein * 0.25, 1)  # ~25% of daily protein within 2h

    @staticmethod
    def _calculate_post_workout_carbs(sport: SportCategory, daily_carbs: float) -> Optional[float]:
        """Calculate post-workout carb needs."""
        if sport in [SportCategory.ENDURANCE, SportCategory.TEAM]:
            return round(daily_carbs * 0.20, 1)  # 20% for glycogen replenishment
        return round(daily_carbs * 0.15, 1)

    @staticmethod
    def _get_caffeine_timing(sport: SportCategory) -> Optional[str]:
        """Get caffeine timing recommendations."""
        if sport in [SportCategory.ENDURANCE, SportCategory.POWER, SportCategory.TEAM]:
            return "30-60 minutes before training/competition"
        return None

    @staticmethod
    def _get_meal_frequency(sport: SportCategory, training_hours: float) -> int:
        """Get recommended meal frequency."""
        if training_hours > 10:  # High volume training
            return 6
        elif training_hours > 6:
            return 5
        else:
            return 4

    @staticmethod
    def _get_weight_cutting_advice(sport: SportCategory) -> str:
        """Get weight cutting considerations."""
        return ("Gradual weight loss recommended (0.5-1% body weight/week). "
                "Maintain protein intake. Consult sports nutritionist for competition prep.")


def get_sport_recommendations(profile: UserProfile,
                            sport: SportCategory,
                            training_phase: TrainingPhase = TrainingPhase.IN_SEASON,
                            training_hours_per_week: float = 5.0) -> Dict[str, any]:
    """
    RU: Получить рекомендации по спортивному питанию.
    EN: Get sports nutrition recommendations.
    """
    targets = SportsNutritionCalculator.calculate_sports_targets(
        profile, sport, training_phase, training_hours_per_week
    )

    # Calculate total daily targets
    weight_kg = profile.weight_kg
    total_protein = targets.protein_g_per_kg * weight_kg
    total_carbs = targets.carbs_g_per_kg * weight_kg
    total_fat = targets.fat_g_per_kg * weight_kg

    # Calculate calories
    total_calories = (total_protein * 4) + (total_carbs * 4) + (total_fat * 9)

    return {
        "sport_category": sport.value,
        "training_phase": training_phase.value,
        "daily_targets": {
            "calories": int(total_calories),
            "protein_g": int(total_protein),
            "carbs_g": int(total_carbs),
            "fat_g": int(total_fat),
            "protein_per_kg": targets.protein_g_per_kg,
            "carbs_per_kg": targets.carbs_g_per_kg,
            "fat_per_kg": targets.fat_g_per_kg
        },
        "hydration": {
            "training_fluid_ml_per_hour": targets.fluid_ml_per_hour_training,
            "electrolyte_replacement": targets.electrolyte_replacement
        },
        "timing": {
            "pre_workout_carbs_g": targets.pre_workout_carbs_g,
            "post_workout_protein_g": targets.post_workout_protein_g,
            "post_workout_carbs_g": targets.post_workout_carbs_g,
            "meal_frequency": targets.meal_frequency
        },
        "supplements": {
            "creatine_recommended": targets.creatine_recommended,
            "caffeine_timing": targets.caffeine_timing
        },
        "special_considerations": {
            "carb_loading_recommended": targets.carb_loading_recommended,
            "weight_cutting_advice": targets.weight_cutting_considerations
        },
        "disclaimer": (
            "This is general sports nutrition guidance based on NASM/ACSM/IFPA guidelines. "
            "Individual needs vary. Consult qualified sports nutritionist or registered dietitian "
            "for personalized recommendations. Not intended as medical advice."
        )
    }


# Sport mapping for user-friendly names
SPORT_MAPPING = {
    "running": SportCategory.ENDURANCE,
    "cycling": SportCategory.ENDURANCE,
    "triathlon": SportCategory.ENDURANCE,
    "marathon": SportCategory.ENDURANCE,
    "swimming": SportCategory.ENDURANCE,

    "weightlifting": SportCategory.STRENGTH,
    "powerlifting": SportCategory.STRENGTH,
    "strongman": SportCategory.STRENGTH,

    "sprinting": SportCategory.POWER,
    "jumping": SportCategory.POWER,
    "throwing": SportCategory.POWER,

    "football": SportCategory.TEAM,
    "basketball": SportCategory.TEAM,
    "soccer": SportCategory.TEAM,
    "volleyball": SportCategory.TEAM,
    "hockey": SportCategory.TEAM,

    "gymnastics": SportCategory.AESTHETIC,
    "figure_skating": SportCategory.AESTHETIC,
    "bodybuilding": SportCategory.AESTHETIC,
    "dance": SportCategory.AESTHETIC,

    "boxing": SportCategory.COMBAT,
    "wrestling": SportCategory.COMBAT,
    "mma": SportCategory.COMBAT,
    "martial_arts": SportCategory.COMBAT,

    "fitness": SportCategory.RECREATIONAL,
    "general": SportCategory.RECREATIONAL,
}

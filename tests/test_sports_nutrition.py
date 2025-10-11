"""
Tests for Sports Nutrition module

Tests NASM/ACSM/IFPA sports nutrition guidelines for different sports,
training phases, and performance goals.
"""

import pytest

from core.sports_nutrition import (
    SPORT_MAPPING,
    SportCategory,
    SportsNutritionCalculator,
    TrainingPhase,
)
from core.targets import UserProfile


class TestSportsNutritionCalculator:
    """Test sports nutrition calculation system."""

    def test_endurance_nutrition_requirements(self):
        """Test nutrition requirements for endurance sports."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Endurance sport during in-season phase
        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.IN_SEASON
        )

        # Check protein requirements (1.2-1.4 g/kg for endurance)
        assert nutrition.protein_g_per_kg >= 1.2
        assert nutrition.protein_g_per_kg <= 1.4

        # Check carb requirements (6-10 g/kg for endurance)
        assert nutrition.carbs_g_per_kg >= 6
        assert nutrition.carbs_g_per_kg <= 10

        # Check hydration needs
        assert nutrition.fluid_ml_per_hour_training >= 150

        # Check timing recommendations
        assert nutrition.pre_workout_carbs_g is not None
        assert nutrition.post_workout_protein_g is not None

    def test_strength_nutrition_requirements(self):
        """Test nutrition requirements for strength sports."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="active",
            goal="gain",
        )

        # Strength sport during peak phase
        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.STRENGTH, TrainingPhase.PEAK
        )

        # Check protein requirements (1.6-2.2 g/kg for strength)
        assert nutrition.protein_g_per_kg >= 1.6
        assert nutrition.protein_g_per_kg <= 2.2

        # Check creatine recommendations
        assert nutrition.creatine_recommended

        # Check protein timing
        assert nutrition.post_workout_protein_g is not None
        assert nutrition.post_workout_protein_g >= 20

    def test_power_sport_nutrition(self):
        """Test nutrition for power sports like sprinting."""
        profile = UserProfile(
            sex="male",
            age=22,
            height_cm=180,
            weight_kg=75,
            activity="very_active",
            goal="maintain",
        )

        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.POWER, TrainingPhase.PEAK
        )

        # Power sports need reasonable carbs for explosive movements
        assert nutrition.carbs_g_per_kg >= 3
        assert nutrition.carbs_g_per_kg <= 6  # Slightly higher due to peak phase

        # Check creatine recommendation
        assert nutrition.creatine_recommended

        # Check caffeine timing
        assert nutrition.caffeine_timing is not None

    def test_team_sport_nutrition(self):
        """Test nutrition for team sports."""
        profile = UserProfile(
            sex="female",
            age=20,
            height_cm=170,
            weight_kg=65,
            activity="very_active",
            goal="maintain",
        )

        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.TEAM, TrainingPhase.IN_SEASON
        )

        # Team sports have moderate protein needs
        assert nutrition.protein_g_per_kg >= 1.4
        assert nutrition.protein_g_per_kg <= 1.7

        # Should have moderate hydration needs
        assert nutrition.fluid_ml_per_hour_training >= 300

    def test_training_phase_adjustments(self):
        """Test nutrition adjustments across training phases."""
        profile = UserProfile(
            sex="male",
            age=28,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Test different phases for same sport
        off_season = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.OFF_SEASON
        )

        peak_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.PEAK
        )

        # Peak phase should have higher or equal carb requirements
        assert peak_nutrition.carbs_g_per_kg >= off_season.carbs_g_per_kg

    def test_weight_making_sports(self):
        """Test nutrition for weight-making sports."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=170,
            weight_kg=65,
            activity="very_active",
            goal="loss",
        )

        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.COMBAT, TrainingPhase.IN_SEASON
        )

        # Should have weight cutting guidance
        assert nutrition.weight_cutting_considerations is not None

        # Should emphasize protein to preserve muscle
        assert nutrition.protein_g_per_kg >= 1.6


class TestSportMapping:
    """Test sport type detection and categorization."""

    def test_endurance_sport_mapping(self):
        """Test mapping of endurance sports."""
        endurance_sports = ["marathon", "cycling", "triathlon", "running"]

        for sport in endurance_sports:
            if sport in SPORT_MAPPING:
                category = SPORT_MAPPING[sport]
                assert category == SportCategory.ENDURANCE

    def test_strength_sport_mapping(self):
        """Test mapping of strength sports."""
        strength_sports = ["powerlifting", "weightlifting"]

        for sport in strength_sports:
            if sport in SPORT_MAPPING:
                category = SPORT_MAPPING[sport]
                assert category == SportCategory.STRENGTH

    def test_power_sport_mapping(self):
        """Test mapping of power sports."""
        power_sports = ["sprinting", "jumping", "throwing"]

        for sport in power_sports:
            if sport in SPORT_MAPPING:
                category = SPORT_MAPPING[sport]
                assert category == SportCategory.POWER

    def test_team_sport_mapping(self):
        """Test mapping of team sports."""
        team_sports = ["soccer", "basketball", "football", "hockey"]

        for sport in team_sports:
            if sport in SPORT_MAPPING:
                category = SPORT_MAPPING[sport]
                assert category == SportCategory.TEAM


class TestSportsNutritionDataStructures:
    """Test sports nutrition data structures and enums."""

    def test_sport_categories(self):
        """Test sport category enumeration."""
        categories = [
            SportCategory.ENDURANCE,
            SportCategory.STRENGTH,
            SportCategory.POWER,
            SportCategory.TEAM,
            SportCategory.AESTHETIC,
            SportCategory.COMBAT,
            SportCategory.RECREATIONAL,
        ]

        for category in categories:
            assert isinstance(category.value, str)
            assert len(category.value) > 0

    def test_training_phases(self):
        """Test training phase enumeration."""
        phases = [
            TrainingPhase.OFF_SEASON,
            TrainingPhase.PRE_SEASON,
            TrainingPhase.IN_SEASON,
            TrainingPhase.PEAK,
            TrainingPhase.RECOVERY,
        ]

        for phase in phases:
            assert isinstance(phase.value, str)
            assert len(phase.value) > 0

    def test_calculator_requirements_data(self):
        """Test that calculator has required data structures."""
        assert hasattr(SportsNutritionCalculator, "SPORT_PROTEIN_REQUIREMENTS")
        assert hasattr(SportsNutritionCalculator, "SPORT_CARB_REQUIREMENTS")
        assert hasattr(SportsNutritionCalculator, "HYDRATION_GUIDELINES")

        # Check that all sport categories are covered
        for category in SportCategory:
            assert category in SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS
            assert category in SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS
            assert category in SportsNutritionCalculator.HYDRATION_GUIDELINES


class TestSportsNutritionCoverage:
    """Additional tests to improve coverage of sports_nutrition.py."""

    def test_get_sports_nutrition_targets_function(self):
        """Test the main get_sports_nutrition_targets function."""
        from core.sports_nutrition import get_sports_nutrition_targets

        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Test a few sport categories (not all to avoid import issues)
        for sport in [SportCategory.ENDURANCE, SportCategory.STRENGTH, SportCategory.TEAM]:
            targets = get_sports_nutrition_targets(profile, sport)
            assert targets is not None
            assert hasattr(targets, "protein_g_per_kg")
            assert hasattr(targets, "carbs_g_per_kg")
            assert hasattr(targets, "fat_g_per_kg")

    def test_all_sport_categories_coverage(self):
        """Test all sport categories to ensure full coverage."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="active",
            goal="gain",
        )

        # Test each sport category
        for sport in SportCategory:
            nutrition = SportsNutritionCalculator.calculate_sports_targets(
                profile, sport, TrainingPhase.IN_SEASON
            )

            # Basic validation for each sport
            assert nutrition.protein_g_per_kg > 0
            assert nutrition.carbs_g_per_kg > 0
            assert nutrition.fat_g_per_kg > 0
            assert nutrition.fluid_ml_per_hour_training > 0
            assert nutrition.meal_frequency > 0

    def test_all_training_phases_coverage(self):
        """Test all training phases to ensure full coverage."""
        profile = UserProfile(
            sex="male",
            age=28,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Test each training phase
        for phase in TrainingPhase:
            nutrition = SportsNutritionCalculator.calculate_sports_targets(
                profile, SportCategory.ENDURANCE, phase
            )

            # Basic validation for each phase
            assert nutrition.protein_g_per_kg > 0
            assert nutrition.carbs_g_per_kg > 0
            assert nutrition.fluid_ml_per_hour_training > 0

    def test_phase_multipliers_coverage(self):
        """Test _get_phase_multipliers for all phases."""
        # Test each training phase
        for phase in TrainingPhase:
            protein_mult, carb_mult = SportsNutritionCalculator._get_phase_multipliers(phase)

            # Multipliers should be positive
            assert protein_mult > 0
            assert carb_mult > 0

            # Peak phase should have higher multipliers
            if phase == TrainingPhase.PEAK:
                assert protein_mult >= 1.0
                assert carb_mult >= 1.0

    def test_aesthetic_sport_nutrition(self):
        """Test nutrition for aesthetic sports (gymnastics, figure skating)."""
        profile = UserProfile(
            sex="female",
            age=20,
            height_cm=160,
            weight_kg=50,
            activity="very_active",
            goal="maintain",
        )

        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.AESTHETIC, TrainingPhase.IN_SEASON
        )

        # Aesthetic sports need moderate protein
        assert nutrition.protein_g_per_kg >= 1.4
        assert nutrition.protein_g_per_kg <= 2.0

        # Should have weight management considerations
        assert nutrition.weight_cutting_considerations is not None

    def test_combat_sport_nutrition(self):
        """Test nutrition for combat sports."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=170,
            weight_kg=65,
            activity="very_active",
            goal="loss",
        )

        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.COMBAT, TrainingPhase.IN_SEASON
        )

        # Combat sports need high protein for muscle preservation
        assert nutrition.protein_g_per_kg >= 1.6
        assert nutrition.protein_g_per_kg <= 2.2

        # Should have weight cutting guidance
        assert nutrition.weight_cutting_considerations is not None

    def test_recreational_sport_nutrition(self):
        """Test nutrition for recreational sports."""
        profile = UserProfile(
            sex="male",
            age=35,
            height_cm=175,
            weight_kg=80,
            activity="moderate",
            goal="maintain",
        )

        nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.RECREATIONAL, TrainingPhase.OFF_SEASON
        )

        # Recreational sports have moderate requirements
        assert nutrition.protein_g_per_kg >= 1.2
        assert nutrition.protein_g_per_kg <= 1.6
        assert nutrition.carbs_g_per_kg >= 3
        assert nutrition.carbs_g_per_kg <= 5

    def test_high_carb_sports_coverage(self):
        """Test that high carb sports get appropriate carb recommendations."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Test endurance sport (high carb)
        endurance_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.IN_SEASON
        )
        assert endurance_nutrition.carbs_g_per_kg >= 6
        assert endurance_nutrition.carbs_g_per_kg <= 10

        # Test team sport (high carb)
        team_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.TEAM, TrainingPhase.IN_SEASON
        )
        assert team_nutrition.carbs_g_per_kg >= 5
        assert team_nutrition.carbs_g_per_kg <= 8

    def test_strength_power_sports_coverage(self):
        """Test that strength/power sports get appropriate recommendations."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="gain",
        )

        # Test strength sport
        strength_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.STRENGTH, TrainingPhase.PEAK
        )
        assert strength_nutrition.protein_g_per_kg >= 1.6
        assert strength_nutrition.protein_g_per_kg <= 2.2
        assert strength_nutrition.creatine_recommended is True

        # Test power sport
        power_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.POWER, TrainingPhase.PEAK
        )
        assert power_nutrition.protein_g_per_kg >= 1.6
        assert power_nutrition.protein_g_per_kg <= 2.0
        assert power_nutrition.creatine_recommended is True

    def test_caffeine_sports_coverage(self):
        """Test that caffeine sports get timing recommendations."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Test endurance sport (caffeine sport)
        endurance_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.IN_SEASON
        )
        assert endurance_nutrition.caffeine_timing is not None

        # Test power sport (caffeine sport)
        power_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.POWER, TrainingPhase.IN_SEASON
        )
        assert power_nutrition.caffeine_timing is not None

        # Test team sport (caffeine sport)
        team_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.TEAM, TrainingPhase.IN_SEASON
        )
        assert team_nutrition.caffeine_timing is not None

    def test_weight_cutting_sports_coverage(self):
        """Test that weight cutting sports get appropriate guidance."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=170,
            weight_kg=65,
            activity="very_active",
            goal="loss",
        )

        # Test combat sport (weight cutting)
        combat_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.COMBAT, TrainingPhase.IN_SEASON
        )
        assert combat_nutrition.weight_cutting_considerations is not None

        # Test aesthetic sport (weight cutting)
        aesthetic_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.AESTHETIC, TrainingPhase.IN_SEASON
        )
        assert aesthetic_nutrition.weight_cutting_considerations is not None

    def test_training_hours_adjustment(self):
        """Test nutrition adjustment based on training hours."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Low training volume
        low_volume = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.IN_SEASON, training_hours_per_week=3.0
        )

        # High training volume
        high_volume = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.IN_SEASON, training_hours_per_week=15.0
        )

        # High volume should have higher carb requirements
        assert high_volume.carbs_g_per_kg >= low_volume.carbs_g_per_kg

    def test_off_season_vs_peak_phase_differences(self):
        """Test differences between off-season and peak phases."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        off_season = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.OFF_SEASON
        )

        peak = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.PEAK
        )

        # Peak phase should have higher or equal requirements
        assert peak.carbs_g_per_kg >= off_season.carbs_g_per_kg
        assert peak.protein_g_per_kg >= off_season.protein_g_per_kg

    def test_pre_season_phase(self):
        """Test pre-season phase nutrition."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        pre_season = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.TEAM, TrainingPhase.PRE_SEASON
        )

        # Pre-season should have moderate requirements
        assert pre_season.protein_g_per_kg > 0
        assert pre_season.carbs_g_per_kg > 0
        assert pre_season.fluid_ml_per_hour_training > 0

    def test_recovery_phase(self):
        """Test recovery phase nutrition."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        recovery = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.STRENGTH, TrainingPhase.RECOVERY
        )

        # Recovery phase should have adequate protein for muscle repair
        assert recovery.protein_g_per_kg >= 1.6
        assert recovery.post_workout_protein_g is not None

    def test_meal_frequency_recommendations(self):
        """Test meal frequency recommendations for different sports."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Test different sports
        for sport in SportCategory:
            nutrition = SportsNutritionCalculator.calculate_sports_targets(
                profile, sport, TrainingPhase.IN_SEASON
            )

            # Meal frequency should be reasonable (3-6 meals)
            assert nutrition.meal_frequency >= 3
            assert nutrition.meal_frequency <= 6

    def test_electrolyte_replacement_recommendations(self):
        """Test electrolyte replacement recommendations."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # High sweat sports should recommend electrolyte replacement
        endurance_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.IN_SEASON
        )
        assert endurance_nutrition.electrolyte_replacement is True

        # Team sports should also recommend it
        team_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.TEAM, TrainingPhase.IN_SEASON
        )
        assert team_nutrition.electrolyte_replacement is True

    def test_carb_loading_recommendations(self):
        """Test carb loading recommendations for endurance sports."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=70,
            activity="very_active",
            goal="maintain",
        )

        # Endurance sports should recommend carb loading
        endurance_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.ENDURANCE, TrainingPhase.PEAK
        )
        assert endurance_nutrition.carb_loading_recommended is True

        # Strength sports typically don't need carb loading
        strength_nutrition = SportsNutritionCalculator.calculate_sports_targets(
            profile, SportCategory.STRENGTH, TrainingPhase.PEAK
        )
        assert strength_nutrition.carb_loading_recommended is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

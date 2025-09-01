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
            goal="maintain"
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
            goal="gain"
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
            goal="maintain"
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
            goal="maintain"
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
            goal="maintain"
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
            goal="loss"
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
            SportCategory.RECREATIONAL
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
            TrainingPhase.RECOVERY
        ]

        for phase in phases:
            assert isinstance(phase.value, str)
            assert len(phase.value) > 0

    def test_calculator_requirements_data(self):
        """Test that calculator has required data structures."""
        assert hasattr(SportsNutritionCalculator, 'SPORT_PROTEIN_REQUIREMENTS')
        assert hasattr(SportsNutritionCalculator, 'SPORT_CARB_REQUIREMENTS')
        assert hasattr(SportsNutritionCalculator, 'HYDRATION_GUIDELINES')

        # Check that all sport categories are covered
        for category in SportCategory:
            assert category in SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS
            assert category in SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS
            assert category in SportsNutritionCalculator.HYDRATION_GUIDELINES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

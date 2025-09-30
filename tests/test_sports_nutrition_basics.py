"""
Comprehensive tests for core/sports_nutrition.py

RU: Полные тесты для модуля спортивного питания.
EN: Complete tests for sports nutrition module.

Coverage target: core/sports_nutrition.py major functions and logic paths.
"""

from core.sports_nutrition import (
    SPORT_MAPPING,
    SportCategory,
    SportsNutritionCalculator,
    SportsNutritionTargets,
    TrainingPhase,
    get_sport_recommendations,
)
from core.targets import UserProfile


class TestSportCategoryEnum:
    """Test SportCategory enum values and properties."""

    def test_sport_category_values(self):
        """Test all sport category enum values."""
        assert SportCategory.ENDURANCE.value == "endurance"
        assert SportCategory.STRENGTH.value == "strength"
        assert SportCategory.POWER.value == "power"
        assert SportCategory.TEAM.value == "team"
        assert SportCategory.AESTHETIC.value == "aesthetic"
        assert SportCategory.COMBAT.value == "combat"
        assert SportCategory.RECREATIONAL.value == "recreational"


class TestTrainingPhaseEnum:
    """Test TrainingPhase enum values and properties."""

    def test_training_phase_values(self):
        """Test all training phase enum values."""
        assert TrainingPhase.OFF_SEASON.value == "off_season"
        assert TrainingPhase.PRE_SEASON.value == "pre_season"
        assert TrainingPhase.IN_SEASON.value == "in_season"
        assert TrainingPhase.PEAK.value == "peak"
        assert TrainingPhase.RECOVERY.value == "recovery"


class TestSportsNutritionTargets:
    """Test SportsNutritionTargets dataclass."""

    def test_sports_nutrition_targets_creation(self):
        """Test creating SportsNutritionTargets instance."""
        targets = SportsNutritionTargets(
            protein_g_per_kg=1.6,
            carbs_g_per_kg=5.0,
            fat_g_per_kg=1.0,
            fluid_ml_per_hour_training=500,
            electrolyte_replacement=True,
            pre_workout_carbs_g=30.0,
            post_workout_protein_g=25.0,
            post_workout_carbs_g=40.0,
            creatine_recommended=True,
            caffeine_timing="30-60 minutes before training/competition",
            meal_frequency=5,
            carb_loading_recommended=False,
            weight_cutting_considerations=None,
        )

        assert targets.protein_g_per_kg == 1.6
        assert targets.carbs_g_per_kg == 5.0
        assert targets.electrolyte_replacement is True
        assert targets.creatine_recommended is True


class TestSportsNutritionCalculator:
    """Test SportsNutritionCalculator class methods."""

    def setup_method(self):
        """Setup test fixtures."""
        # Create real UserProfile
        self.profile = UserProfile(
            sex="male", age=25, height_cm=175, weight_kg=70.0, activity="moderate", goal="maintain"
        )

    def test_calculate_sports_targets_endurance(self):
        """Test calculate_sports_targets for endurance sport."""
        targets = SportsNutritionCalculator.calculate_sports_targets(
            profile=self.profile,
            sport=SportCategory.ENDURANCE,
            training_phase=TrainingPhase.IN_SEASON,
            training_hours_per_week=8.0,
        )

        assert isinstance(targets, SportsNutritionTargets)
        assert targets.protein_g_per_kg > 0
        assert targets.carbs_g_per_kg > 0
        assert targets.fat_g_per_kg > 0
        assert targets.fluid_ml_per_hour_training > 0
        assert targets.carb_loading_recommended is True  # Endurance sport
        assert targets.creatine_recommended is False  # Not strength/power/combat

    def test_calculate_sports_targets_strength(self):
        """Test calculate_sports_targets for strength sport."""
        targets = SportsNutritionCalculator.calculate_sports_targets(
            profile=self.profile,
            sport=SportCategory.STRENGTH,
            training_phase=TrainingPhase.IN_SEASON,
            training_hours_per_week=5.0,
        )

        assert isinstance(targets, SportsNutritionTargets)
        assert targets.protein_g_per_kg >= 1.6  # Higher protein for strength
        assert targets.creatine_recommended is True  # Strength sport
        assert targets.carb_loading_recommended is False  # Not endurance

    def test_calculate_sports_targets_combat_with_weight_cutting(self):
        """Test calculate_sports_targets for combat sport."""
        targets = SportsNutritionCalculator.calculate_sports_targets(
            profile=self.profile,
            sport=SportCategory.COMBAT,
            training_phase=TrainingPhase.PRE_SEASON,
            training_hours_per_week=10.0,
        )

        assert isinstance(targets, SportsNutritionTargets)
        assert targets.creatine_recommended is True  # Combat sport
        assert targets.weight_cutting_considerations is not None  # Combat sport advice
        assert "weight loss" in targets.weight_cutting_considerations.lower()

    def test_get_phase_multipliers(self):
        """Test _get_phase_multipliers static method."""
        # Test all training phases
        off_season = SportsNutritionCalculator._get_phase_multipliers(TrainingPhase.OFF_SEASON)
        in_season = SportsNutritionCalculator._get_phase_multipliers(TrainingPhase.IN_SEASON)
        peak = SportsNutritionCalculator._get_phase_multipliers(TrainingPhase.PEAK)

        assert isinstance(off_season, tuple) and len(off_season) == 2
        assert isinstance(in_season, tuple) and len(in_season) == 2
        assert in_season == (1.0, 1.0)  # Base case
        assert peak[1] > in_season[1]  # Higher carb multiplier at peak

    def test_calculate_fat_needs_with_goals(self):
        """Test _calculate_fat_needs with different goals."""
        # Test with loss goal
        fat_loss = SportsNutritionCalculator._calculate_fat_needs(SportCategory.STRENGTH, "loss")
        fat_gain = SportsNutritionCalculator._calculate_fat_needs(SportCategory.STRENGTH, "gain")
        fat_maintenance = SportsNutritionCalculator._calculate_fat_needs(
            SportCategory.STRENGTH, "maintenance"
        )

        assert fat_loss < fat_gain
        assert fat_loss >= 0.8  # Minimum for health
        assert fat_gain > fat_maintenance

    def test_calculate_pre_workout_carbs(self):
        """Test _calculate_pre_workout_carbs for different sports."""
        daily_carbs = 300.0

        # Sports that get pre-workout carbs
        endurance_carbs = SportsNutritionCalculator._calculate_pre_workout_carbs(
            SportCategory.ENDURANCE, daily_carbs
        )
        team_carbs = SportsNutritionCalculator._calculate_pre_workout_carbs(
            SportCategory.TEAM, daily_carbs
        )
        strength_carbs = SportsNutritionCalculator._calculate_pre_workout_carbs(
            SportCategory.STRENGTH, daily_carbs
        )

        assert endurance_carbs is not None and endurance_carbs > 0
        assert team_carbs is not None and team_carbs > 0
        assert strength_carbs is not None and strength_carbs > 0
        assert endurance_carbs > strength_carbs  # Endurance needs more

    def test_calculate_post_workout_protein(self):
        """Test _calculate_post_workout_protein calculation."""
        daily_protein = 140.0

        post_protein = SportsNutritionCalculator._calculate_post_workout_protein(
            SportCategory.STRENGTH, daily_protein
        )

        assert post_protein is not None
        assert post_protein > 0
        assert post_protein == round(daily_protein * 0.25, 1)  # 25% of daily

    def test_get_caffeine_timing(self):
        """Test _get_caffeine_timing for different sports."""
        endurance_timing = SportsNutritionCalculator._get_caffeine_timing(SportCategory.ENDURANCE)
        power_timing = SportsNutritionCalculator._get_caffeine_timing(SportCategory.POWER)

        assert endurance_timing is not None
        assert power_timing is not None
        assert "30-60 minutes" in endurance_timing

    def test_get_meal_frequency(self):
        """Test _get_meal_frequency based on training volume."""
        high_volume = SportsNutritionCalculator._get_meal_frequency(SportCategory.ENDURANCE, 12.0)
        medium_volume = SportsNutritionCalculator._get_meal_frequency(SportCategory.STRENGTH, 7.0)
        low_volume = SportsNutritionCalculator._get_meal_frequency(SportCategory.RECREATIONAL, 3.0)

        assert high_volume >= medium_volume >= low_volume
        assert high_volume == 6  # High volume training
        assert medium_volume == 5  # Medium volume training
        assert low_volume == 4  # Low volume training

    def test_get_weight_cutting_advice(self):
        """Test _get_weight_cutting_advice static method."""
        advice = SportsNutritionCalculator._get_weight_cutting_advice(SportCategory.COMBAT)

        assert isinstance(advice, str)
        assert len(advice) > 50
        assert "weight loss" in advice.lower()
        assert "protein" in advice.lower()


class TestGetSportRecommendations:
    """Test get_sport_recommendations function."""

    def setup_method(self):
        """Setup test fixtures."""
        self.profile = UserProfile(
            sex="male", age=30, height_cm=180, weight_kg=80.0, activity="active", goal="gain"
        )

    def test_get_sport_recommendations_structure(self):
        """Test get_sport_recommendations returns proper structure."""
        recommendations = get_sport_recommendations(
            profile=self.profile,
            sport=SportCategory.STRENGTH,
            training_phase=TrainingPhase.IN_SEASON,
            training_hours_per_week=6.0,
        )

        # Check top-level structure
        assert isinstance(recommendations, dict)
        assert "sport_category" in recommendations
        assert "training_phase" in recommendations
        assert "daily_targets" in recommendations
        assert "hydration" in recommendations
        assert "timing" in recommendations
        assert "supplements" in recommendations
        assert "special_considerations" in recommendations
        assert "disclaimer" in recommendations

        # Check daily targets structure
        daily = recommendations["daily_targets"]
        assert "calories" in daily
        assert "protein_g" in daily
        assert "carbs_g" in daily
        assert "fat_g" in daily
        assert "protein_per_kg" in daily
        assert "carbs_per_kg" in daily
        assert "fat_per_kg" in daily

        # Check values are reasonable
        assert daily["calories"] > 0
        assert daily["protein_g"] > 0
        assert daily["carbs_g"] > 0
        assert daily["fat_g"] > 0

    def test_get_sport_recommendations_endurance(self):
        """Test recommendations for endurance sport."""
        recommendations = get_sport_recommendations(
            profile=self.profile,
            sport=SportCategory.ENDURANCE,
            training_phase=TrainingPhase.PEAK,
            training_hours_per_week=12.0,
        )

        assert recommendations["sport_category"] == "endurance"
        assert recommendations["training_phase"] == "peak"
        assert recommendations["special_considerations"]["carb_loading_recommended"] is True
        assert recommendations["supplements"]["creatine_recommended"] is False

        # Endurance should have high carbs
        daily = recommendations["daily_targets"]
        carb_ratio = daily["carbs_g"] / daily["protein_g"]
        assert carb_ratio > 2.0  # More carbs than protein for endurance


class TestSportMapping:
    """Test SPORT_MAPPING dictionary."""

    def test_sport_mapping_coverage(self):
        """Test SPORT_MAPPING has comprehensive coverage."""
        # Test common sports are mapped
        assert "running" in SPORT_MAPPING
        assert "cycling" in SPORT_MAPPING
        assert "weightlifting" in SPORT_MAPPING
        assert "football" in SPORT_MAPPING
        assert "boxing" in SPORT_MAPPING

        # Test mappings are valid SportCategory values
        for sport_name, category in SPORT_MAPPING.items():
            assert isinstance(category, SportCategory)

    def test_sport_mapping_endurance_sports(self):
        """Test endurance sports are properly mapped."""
        endurance_sports = ["running", "cycling", "triathlon", "marathon", "swimming"]
        for sport in endurance_sports:
            assert SPORT_MAPPING[sport] == SportCategory.ENDURANCE

    def test_sport_mapping_strength_sports(self):
        """Test strength sports are properly mapped."""
        strength_sports = ["weightlifting", "powerlifting", "strongman"]
        for sport in strength_sports:
            assert SPORT_MAPPING[sport] == SportCategory.STRENGTH

    def test_sport_mapping_combat_sports(self):
        """Test combat sports are properly mapped."""
        combat_sports = ["boxing", "wrestling", "mma", "martial_arts"]
        for sport in combat_sports:
            assert SPORT_MAPPING[sport] == SportCategory.COMBAT


class TestSportsNutritionConstants:
    """Test sports nutrition constant dictionaries."""

    def test_protein_requirements_coverage(self):
        """Test SPORT_PROTEIN_REQUIREMENTS covers all sport categories."""
        for category in SportCategory:
            assert category in SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS
            protein_range = SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS[category]
            assert isinstance(protein_range, tuple)
            assert len(protein_range) == 2
            assert protein_range[0] <= protein_range[1]
            assert protein_range[0] > 0

    def test_carb_requirements_coverage(self):
        """Test SPORT_CARB_REQUIREMENTS covers all sport categories."""
        for category in SportCategory:
            assert category in SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS
            carb_range = SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS[category]
            assert isinstance(carb_range, tuple)
            assert len(carb_range) == 2
            assert carb_range[0] <= carb_range[1]
            assert carb_range[0] > 0

    def test_hydration_guidelines_coverage(self):
        """Test HYDRATION_GUIDELINES covers all sport categories."""
        for category in SportCategory:
            assert category in SportsNutritionCalculator.HYDRATION_GUIDELINES
            hydration = SportsNutritionCalculator.HYDRATION_GUIDELINES[category]
            assert isinstance(hydration, int)
            assert hydration > 0

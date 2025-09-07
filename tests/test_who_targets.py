"""
Tests for WHO-based nutrition targets system

Tests cover:
- Target calculation accuracy for different profiles
- Micronutrient RDA selection by age/sex
- Safety validation and warnings
- Macro distribution within WHO guidelines
- Activity and hydration recommendations
- Special conditions (pregnancy, lactation)
"""

import pytest

from core.recommendations import build_nutrition_targets, validate_targets_safety
from core.rules_who import (
    get_activity_guidelines,
    get_micronutrient_rda,
    validate_macro_distribution,
)
from core.targets import NutritionTargets, UserProfile


class TestWHOTargets:
    """Test WHO-based nutrition targets calculation."""

    def test_adult_female_targets(self):
        """Test target calculation for adult female."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        targets = build_nutrition_targets(profile)

        # Check basic structure
        assert isinstance(targets, NutritionTargets)
        assert targets.kcal_daily > 1200  # Above minimum
        assert targets.water_ml_daily >= 1500  # Adequate hydration

        # Check macronutrient reasonableness
        assert 50 <= targets.macros.protein_g <= 150
        assert 40 <= targets.macros.fat_g <= 100
        assert 100 <= targets.macros.carbs_g <= 400
        assert 20 <= targets.macros.fiber_g <= 40

        # Check key micronutrients for women
        assert targets.micros.iron_mg == 18.0  # High for menstruation
        assert targets.micros.folate_ug == 400.0  # Reproductive age
        assert targets.micros.calcium_mg == 1000.0

        # Check consistency
        assert targets.validate_consistency()

    def test_adult_male_targets(self):
        """Test target calculation for adult male."""
        profile = UserProfile(
            sex="male",
            age=35,
            height_cm=180,
            weight_kg=80,
            activity="active",
            goal="maintain",
        )

        targets = build_nutrition_targets(profile)

        # Males should have higher calorie needs
        assert targets.kcal_daily > 2000

        # Check male-specific micronutrients
        assert targets.micros.iron_mg == 8.0  # Lower than women
        assert targets.micros.zinc_mg == 11.0  # Higher than women
        assert targets.micros.vitamin_a_ug == 900.0  # Higher than women

    def test_weight_loss_goals(self):
        """Test targets for weight loss goals."""
        profile = UserProfile(
            sex="female",
            age=25,
            height_cm=170,
            weight_kg=70,
            activity="moderate",
            goal="loss",
            deficit_pct=20,
        )

        targets = build_nutrition_targets(profile)

        # Should be below maintenance calories
        assert targets.kcal_daily >= 1200  # Safety minimum

        # Should have higher protein for muscle preservation
        protein_ratio = targets.macros.protein_g / targets.kcal_daily * 4 * 100
        assert protein_ratio >= 20  # At least 20% protein for weight loss

    def test_weight_gain_goals(self):
        """Test targets for weight gain goals."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175,
            weight_kg=60,  # Underweight
            activity="moderate",
            goal="gain",
            surplus_pct=15,
        )

        targets = build_nutrition_targets(profile)

        # Should be above maintenance
        assert targets.kcal_daily > 2200

        # Check reasonable upper bound
        assert targets.kcal_daily < 4000

    def test_pregnant_woman_targets(self):
        """Test targets for pregnant women."""
        profile = UserProfile(
            sex="female",
            age=28,
            height_cm=165,
            weight_kg=65,
            activity="light",
            goal="maintain",
            life_stage="pregnant",
        )

        targets = build_nutrition_targets(profile)

        # Check pregnancy-specific increases
        assert targets.micros.iron_mg == 27.0  # Significantly increased
        assert targets.micros.folate_ug == 600.0  # Critical for neural tube
        assert targets.micros.iodine_ug == 220.0  # Increased for development

    def test_elderly_targets(self):
        """Test targets for elderly individuals."""
        profile = UserProfile(
            sex="female",
            age=70,
            height_cm=160,
            weight_kg=55,
            activity="light",
            goal="maintain",
        )

        targets = build_nutrition_targets(profile)

        # Check age-specific adjustments
        assert targets.micros.calcium_mg == 1200.0  # Increased for bone health
        assert targets.micros.vitamin_d_iu == 800.0  # Increased for elderly

        # Activity should be adjusted for age
        assert targets.activity.steps_daily == 7000  # Lower than adult

    def test_vegetarian_profile(self):
        """Test targets with vegetarian diet flags."""
        profile = UserProfile(
            sex="male",
            age=30,
            height_cm=175,
            weight_kg=70,
            activity="moderate",
            goal="maintain",
            diet_flags={"VEG"},
        )

        targets = build_nutrition_targets(profile)

        # Basic targets should be same, but will affect recommendations
        assert targets.kcal_daily > 0
        assert targets.micros.b12_ug == 2.4  # Critical for vegetarians

    def test_target_safety_validation(self):
        """Test safety validation of calculated targets."""
        # Test normal case
        profile = UserProfile(
            sex="female",
            age=25,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        targets = build_nutrition_targets(profile)
        warnings = validate_targets_safety(targets)

        # Should have no warnings for normal case
        assert len(warnings) == 0

        # Test extreme deficit case
        extreme_profile = UserProfile(
            sex="female",
            age=25,
            height_cm=165,
            weight_kg=50,
            activity="sedentary",
            goal="loss",
            deficit_pct=25,
        )

        extreme_targets = build_nutrition_targets(extreme_profile)
        validate_targets_safety(extreme_targets)

        # Should enforce minimum calories
        assert extreme_targets.kcal_daily >= 1200

    def test_micronutrient_rda_selection(self):
        """Test correct micronutrient RDA selection by demographics."""
        # Test adult woman
        rda_woman = get_micronutrient_rda("female", 30, "adult")
        assert rda_woman["iron_mg"] == 18.0
        assert rda_woman["calcium_mg"] == 1000.0

        # Test adult man
        rda_man = get_micronutrient_rda("male", 30, "adult")
        assert rda_man["iron_mg"] == 8.0
        assert rda_man["zinc_mg"] == 11.0

        # Test elderly woman
        rda_elderly = get_micronutrient_rda("female", 70, "adult")
        assert rda_elderly["calcium_mg"] == 1200.0
        assert rda_elderly["vitamin_d_iu"] == 800.0

    def test_activity_guidelines(self):
        """Test WHO activity guidelines selection."""
        # Test adult guidelines
        adult_activity = get_activity_guidelines(30)
        assert adult_activity["moderate_aerobic_min"] == 150
        assert adult_activity["strength_sessions"] == 2
        assert adult_activity["steps_daily"] == 8000

        # Test elderly guidelines
        elderly_activity = get_activity_guidelines(70)
        assert elderly_activity["steps_daily"] == 7000  # Reduced for elderly

    def test_macro_distribution_validation(self):
        """Test macro distribution validation against WHO guidelines."""
        # Test valid distribution
        assert validate_macro_distribution(25, 30, 45)

        # Test invalid - too much protein
        assert not validate_macro_distribution(50, 25, 25)

        # Test invalid - doesn't sum to 100
        assert not validate_macro_distribution(20, 30, 40)

        # Test boundary values
        assert validate_macro_distribution(35, 20, 45)  # At upper limits

    def test_hydration_calculation(self):
        """Test hydration target calculation."""
        from core.rules_who import calculate_hydration_target

        # Test base calculation
        base_target = calculate_hydration_target(70, "sedentary")
        assert base_target == 70 * 30  # 30ml per kg

        # Test active adjustment
        active_target = calculate_hydration_target(70, "very_active")
        assert active_target > base_target

        # Test minimum enforcement
        light_person_target = calculate_hydration_target(40, "sedentary")
        assert light_person_target >= 1500  # Minimum enforced

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test minimum age
        young_profile = UserProfile(
            sex="female",
            age=18,
            height_cm=155,
            weight_kg=45,
            activity="light",
            goal="maintain",
        )

        targets = build_nutrition_targets(young_profile)
        assert targets.kcal_daily > 1200

        # Test maximum age
        old_profile = UserProfile(
            sex="male",
            age=90,
            height_cm=170,
            weight_kg=65,
            activity="sedentary",
            goal="maintain",
        )

        targets = build_nutrition_targets(old_profile)
        assert targets.kcal_daily > 1500

    def test_consistency_across_goals(self):
        """Test that different goals produce consistent relative results."""
        UserProfile(
            sex="male",
            age=30,
            height_cm=175,
            weight_kg=75,
            activity="moderate",
            goal="maintain",
        )

        # Test all goals
        base_data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 75,
            "activity": "moderate",
        }

        maintain_profile = UserProfile(**base_data, goal="maintain")
        loss_profile = UserProfile(**base_data, goal="loss", deficit_pct=15)
        gain_profile = UserProfile(**base_data, goal="gain", surplus_pct=12)

        maintain_targets = build_nutrition_targets(maintain_profile)
        loss_targets = build_nutrition_targets(loss_profile)
        gain_targets = build_nutrition_targets(gain_profile)

        # Loss should be less than maintenance
        assert loss_targets.kcal_daily < maintain_targets.kcal_daily

        # Gain should be more than maintenance
        assert gain_targets.kcal_daily > maintain_targets.kcal_daily

        # Micronutrients should be consistent across goals
        assert loss_targets.micros.iron_mg == maintain_targets.micros.iron_mg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

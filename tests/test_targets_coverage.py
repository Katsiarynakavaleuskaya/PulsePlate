"""
Targeted coverage tests for core.targets module.
These tests specifically target the uncovered lines to improve overall coverage.
"""

import pytest

from core.targets import (
    ActivityTargets,
    MacroTargets,
    MicroTargets,
    NutrientCoverage,
    NutritionTargets,
    UserProfile,
)


class TestUserProfile:
    """Test UserProfile validation and edge cases."""

    def test_user_profile_basic(self):
        """Test basic UserProfile creation."""
        profile = UserProfile(
            sex="female",
            age=25,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        assert profile.sex == "female"
        assert profile.age == 25
        assert profile.height_cm == 165
        assert profile.weight_kg == 60
        assert profile.activity == "moderate"
        assert profile.goal == "maintain"

    def test_user_profile_age_validation_low(self):
        """Test age validation - too low."""
        with pytest.raises(ValueError, match="Age must be between 1 and 120 years"):
            UserProfile(
                sex="male",
                age=0,  # Invalid age
                height_cm=180,
                weight_kg=75,
                activity="moderate",
                goal="maintain",
            )

    def test_user_profile_age_validation_high(self):
        """Test age validation - too high."""
        with pytest.raises(ValueError, match="Age must be between 1 and 120 years"):
            UserProfile(
                sex="male",
                age=121,  # Invalid age
                height_cm=180,
                weight_kg=75,
                activity="moderate",
                goal="maintain",
            )

    def test_user_profile_height_validation(self):
        """Test height validation."""
        with pytest.raises(ValueError, match="Height and weight must be positive"):
            UserProfile(
                sex="female",
                age=25,
                height_cm=0,  # Invalid height
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            )

    def test_user_profile_weight_validation(self):
        """Test weight validation."""
        with pytest.raises(ValueError, match="Height and weight must be positive"):
            UserProfile(
                sex="female",
                age=25,
                height_cm=165,
                weight_kg=0,  # Invalid weight
                activity="moderate",
                goal="maintain",
            )

    def test_user_profile_deficit_pct_validation_low(self):
        """Test deficit percentage validation - too low."""
        with pytest.raises(ValueError, match="Deficit percentage must be between 5-25%"):
            UserProfile(
                sex="female",
                age=25,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="loss",
                deficit_pct=4,  # Too low
            )

    def test_user_profile_deficit_pct_validation_high(self):
        """Test deficit percentage validation - too high."""
        with pytest.raises(ValueError, match="Deficit percentage must be between 5-25%"):
            UserProfile(
                sex="female",
                age=25,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="loss",
                deficit_pct=26,  # Too high
            )

    def test_user_profile_surplus_pct_validation_low(self):
        """Test surplus percentage validation - too low."""
        with pytest.raises(ValueError, match="Surplus percentage must be between 5-20%"):
            UserProfile(
                sex="male",
                age=25,
                height_cm=180,
                weight_kg=75,
                activity="moderate",
                goal="gain",
                surplus_pct=4,  # Too low
            )

    def test_user_profile_surplus_pct_validation_high(self):
        """Test surplus percentage validation - too high."""
        with pytest.raises(ValueError, match="Surplus percentage must be between 5-20%"):
            UserProfile(
                sex="male",
                age=25,
                height_cm=180,
                weight_kg=75,
                activity="moderate",
                goal="gain",
                surplus_pct=21,  # Too high
            )

    def test_user_profile_with_optional_fields(self):
        """Test UserProfile with all optional fields."""
        profile = UserProfile(
            sex="female",
            age=25,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="loss",
            deficit_pct=15,
            surplus_pct=None,
            bodyfat=22.0,
            region="US",
            diet_flags={"VEG", "GF"},
            life_stage="adult",
            medical_conditions={"diabetes"},
        )

        assert profile.deficit_pct == 15
        assert profile.bodyfat == 22.0
        assert profile.region == "US"
        assert "VEG" in profile.diet_flags
        assert "GF" in profile.diet_flags
        assert profile.life_stage == "adult"
        assert "diabetes" in profile.medical_conditions


class TestMacroTargets:
    """Test MacroTargets calculations."""

    def test_macro_targets_total_calories(self):
        """Test total calories calculation."""
        macros = MacroTargets(protein_g=120, fat_g=70, carbs_g=250, fiber_g=30)

        # protein: 120*4 = 480, carbs: 250*4 = 1000, fat: 70*9 = 630
        # total: 480 + 1000 + 630 = 2110
        assert macros.total_calories() == 2110

    def test_macro_targets_zero_values(self):
        """Test MacroTargets with zero values."""
        macros = MacroTargets(protein_g=0, fat_g=0, carbs_g=0, fiber_g=0)

        assert macros.total_calories() == 0


class TestMicroTargets:
    """Test MicroTargets functionality."""

    def test_micro_targets_get_priority_nutrients(self):
        """Test getting priority nutrients."""
        micros = MicroTargets(
            iron_mg=15.0,
            calcium_mg=1000.0,
            magnesium_mg=320.0,
            zinc_mg=8.0,
            potassium_mg=3500.0,
            iodine_ug=150.0,
            selenium_ug=55.0,
            folate_ug=400.0,
            b12_ug=2.4,
            vitamin_d_iu=600.0,
            vitamin_a_ug=700.0,
            vitamin_c_mg=75.0,
        )

        priority = micros.get_priority_nutrients()

        # Should include these key nutrients
        assert "iron_mg" in priority
        assert "calcium_mg" in priority
        assert "folate_ug" in priority
        assert "vitamin_d_iu" in priority
        assert "b12_ug" in priority
        assert "iodine_ug" in priority

        # Check values
        assert priority["iron_mg"] == 15.0
        assert priority["calcium_mg"] == 1000.0


class TestActivityTargets:
    """Test ActivityTargets calculations."""

    def test_activity_targets_total_aerobic_equivalent(self):
        """Test total aerobic equivalent calculation."""
        activity = ActivityTargets(
            moderate_aerobic_min=150,
            vigorous_aerobic_min=75,
            strength_sessions=2,
            steps_daily=8000,
        )

        # 150 + (75 * 2) = 150 + 150 = 300
        assert activity.total_aerobic_equivalent() == 300

    def test_activity_targets_no_vigorous(self):
        """Test aerobic equivalent with no vigorous activity."""
        activity = ActivityTargets(
            moderate_aerobic_min=200,
            vigorous_aerobic_min=0,
            strength_sessions=3,
            steps_daily=10000,
        )

        # 200 + (0 * 2) = 200
        assert activity.total_aerobic_equivalent() == 200


class TestNutritionTargets:
    """Test NutritionTargets validation and summary."""

    def test_nutrition_targets_validate_consistency_valid(self):
        """Test consistency validation with valid targets."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        # Create consistent targets (macros match calories)
        targets = NutritionTargets(
            kcal_daily=2000,
            macros=MacroTargets(protein_g=120, fat_g=67, carbs_g=250, fiber_g=28),  # ~1867 kcal
            water_ml_daily=2500,
            micros=MicroTargets(
                iron_mg=15.0,
                calcium_mg=1000.0,
                magnesium_mg=320.0,
                zinc_mg=8.0,
                potassium_mg=3500.0,
                iodine_ug=150.0,
                selenium_ug=55.0,
                folate_ug=400.0,
                b12_ug=2.4,
                vitamin_d_iu=600.0,
                vitamin_a_ug=700.0,
                vitamin_c_mg=75.0,
            ),
            activity=ActivityTargets(
                moderate_aerobic_min=150,
                vigorous_aerobic_min=75,
                strength_sessions=2,
                steps_daily=8000,
            ),
            calculated_for=profile,
            calculation_date="2024-01-01",
        )

        # Should be valid (within 5% tolerance)
        assert targets.validate_consistency() is True

    def test_nutrition_targets_validate_consistency_invalid(self):
        """Test consistency validation with invalid targets."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        # Create inconsistent targets (macros don't match calories)
        targets = NutritionTargets(
            kcal_daily=2000,
            macros=MacroTargets(protein_g=200, fat_g=100, carbs_g=400, fiber_g=40),  # ~3100 kcal
            water_ml_daily=2500,
            micros=MicroTargets(
                iron_mg=15.0,
                calcium_mg=1000.0,
                magnesium_mg=320.0,
                zinc_mg=8.0,
                potassium_mg=3500.0,
                iodine_ug=150.0,
                selenium_ug=55.0,
                folate_ug=400.0,
                b12_ug=2.4,
                vitamin_d_iu=600.0,
                vitamin_a_ug=700.0,
                vitamin_c_mg=75.0,
            ),
            activity=ActivityTargets(
                moderate_aerobic_min=150,
                vigorous_aerobic_min=75,
                strength_sessions=2,
                steps_daily=8000,
            ),
            calculated_for=profile,
            calculation_date="2024-01-01",
        )

        # Should be invalid (too far from target)
        assert targets.validate_consistency() is False

    def test_nutrition_targets_get_summary(self):
        """Test getting nutrition targets summary."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        targets = NutritionTargets(
            kcal_daily=2000,
            macros=MacroTargets(protein_g=120, fat_g=67, carbs_g=250, fiber_g=28),
            water_ml_daily=2500,
            micros=MicroTargets(
                iron_mg=15.0,
                calcium_mg=1000.0,
                magnesium_mg=320.0,
                zinc_mg=8.0,
                potassium_mg=3500.0,
                iodine_ug=150.0,
                selenium_ug=55.0,
                folate_ug=400.0,
                b12_ug=2.4,
                vitamin_d_iu=600.0,
                vitamin_a_ug=700.0,
                vitamin_c_mg=75.0,
            ),
            activity=ActivityTargets(
                moderate_aerobic_min=150,
                vigorous_aerobic_min=75,
                strength_sessions=2,
                steps_daily=8000,
            ),
            calculated_for=profile,
            calculation_date="2024-01-01",
        )

        summary = targets.get_summary()

        assert summary["kcal_daily"] == 2000
        assert summary["macros"]["protein_g"] == 120
        assert summary["macros"]["fat_g"] == 67
        assert summary["macros"]["carbs_g"] == 250
        assert summary["macros"]["fiber_g"] == 28


class TestNutrientCoverage:
    """Test NutrientCoverage calculations and status."""

    def test_nutrient_coverage_properties(self):
        """Test coverage percentage and status calculations."""
        # Test adequate coverage
        coverage = NutrientCoverage(
            nutrient_name="protein_g",
            target_amount=100.0,
            consumed_amount=90.0,
            unit="g",
        )

        assert coverage.coverage_percent == 90.0
        assert coverage.status == "adequate"

    def test_nutrient_coverage_deficient(self):
        """Test deficient coverage."""
        coverage = NutrientCoverage(
            nutrient_name="iron_mg", target_amount=15.0, consumed_amount=8.0, unit="mg"
        )

        # 8/15 = 53.33% < 67%
        assert abs(coverage.coverage_percent - 53.33) < 0.1
        assert coverage.status == "deficient"

    def test_nutrient_coverage_excess(self):
        """Test excess coverage."""
        coverage = NutrientCoverage(
            nutrient_name="vitamin_c_mg",
            target_amount=75.0,
            consumed_amount=150.0,
            unit="mg",
        )

        # 150/75 = 200% > 150%
        assert coverage.coverage_percent == 200.0
        assert coverage.status == "excess"

    def test_nutrient_coverage_capped_at_200(self):
        """Test coverage percentage capped at 200%."""
        coverage = NutrientCoverage(
            nutrient_name="vitamin_a_ug",
            target_amount=700.0,
            consumed_amount=2100.0,  # 300%
            unit="μg",
        )

        # Should be capped at 200%
        assert coverage.coverage_percent == 200.0
        assert coverage.status == "excess"

    def test_nutrient_coverage_zero_target(self):
        """Test coverage with zero target."""
        coverage = NutrientCoverage(
            nutrient_name="unknown", target_amount=0.0, consumed_amount=50.0, unit="g"
        )

        assert coverage.coverage_percent == 0.0
        assert coverage.status == "deficient"

    def test_nutrient_coverage_recommendations_english(self):
        """Test recommendations in English."""
        # Deficient
        deficient = NutrientCoverage(
            nutrient_name="iron_mg", target_amount=15.0, consumed_amount=8.0, unit="mg"
        )
        assert "Increase iron_mg intake" in deficient.get_recommendation("en")

        # Adequate
        adequate = NutrientCoverage(
            nutrient_name="protein_g",
            target_amount=100.0,
            consumed_amount=100.0,
            unit="g",
        )
        assert "protein_g is adequate" in adequate.get_recommendation("en")

        # Excess
        excess = NutrientCoverage(
            nutrient_name="vitamin_c_mg",
            target_amount=75.0,
            consumed_amount=150.0,
            unit="mg",
        )
        assert "Moderately reduce vitamin_c_mg" in excess.get_recommendation("en")

    def test_nutrient_coverage_recommendations_russian(self):
        """Test recommendations in Russian."""
        # Deficient
        deficient = NutrientCoverage(
            nutrient_name="iron_mg", target_amount=15.0, consumed_amount=8.0, unit="mg"
        )
        assert "Увеличьте потребление iron_mg" in deficient.get_recommendation("ru")

        # Adequate
        adequate = NutrientCoverage(
            nutrient_name="protein_g",
            target_amount=100.0,
            consumed_amount=100.0,
            unit="g",
        )
        assert "protein_g в норме" in adequate.get_recommendation("ru")

        # Excess
        excess = NutrientCoverage(
            nutrient_name="vitamin_c_mg",
            target_amount=75.0,
            consumed_amount=150.0,
            unit="mg",
        )
        assert "Умеренно сократите vitamin_c_mg" in excess.get_recommendation("ru")

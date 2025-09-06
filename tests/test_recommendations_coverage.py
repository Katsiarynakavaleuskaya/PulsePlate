"""
Targeted coverage tests for core.recommendations module.
These tests specifically target the uncovered lines to improve overall coverage.
"""


from core.recommendations import (
    _adapt_for_vegetarian,
    _calculate_activity_targets,
    _calculate_macro_targets,
    _calculate_micro_targets,
    _calculate_target_calories,
    _get_nutrient_food_sources,
    build_nutrition_targets,
    calculate_weekly_coverage,
    generate_deficiency_recommendations,
    score_nutrient_coverage,
    validate_targets_safety,
)
from core.targets import (
    ActivityTargets,
    MacroTargets,
    MicroTargets,
    NutrientCoverage,
    NutritionTargets,
    UserProfile,
)


class TestDeficiencyRecommendations:
    """Test deficiency recommendation generation."""

    def test_recommendations_with_deficiencies(self):
        """Test generating recommendations for deficient nutrients."""
        coverage = {
            "iron_mg": NutrientCoverage(
                nutrient_name="iron_mg",
                target_amount=15.0,
                consumed_amount=8.0,
                unit="mg",
            ),
            "calcium_mg": NutrientCoverage(
                nutrient_name="calcium_mg",
                target_amount=1000.0,
                consumed_amount=600.0,
                unit="mg",
            ),
            "protein_g": NutrientCoverage(
                nutrient_name="protein_g",
                target_amount=120.0,
                consumed_amount=110.0,
                unit="g",
            ),
        }

        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        recommendations = generate_deficiency_recommendations(coverage, profile, "en")

        # Should have recommendations for deficient nutrients
        assert len(recommendations) > 0
        iron_rec = [r for r in recommendations if "iron_mg" in r]
        assert len(iron_rec) > 0

    def test_recommendations_with_vegetarian_diet(self):
        """Test recommendations adapted for vegetarian diet."""
        coverage = {
            "iron_mg": NutrientCoverage(
                nutrient_name="iron_mg",
                target_amount=15.0,
                consumed_amount=8.0,
                unit="mg",
            )
        }

        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
            diet_flags={"VEG"},
        )

        recommendations = generate_deficiency_recommendations(coverage, profile, "en")

        # Should have vegetarian-adapted recommendations
        assert len(recommendations) > 0
        assert any(
            "vitamin C" in rec.lower() or "absorption" in rec.lower()
            for rec in recommendations
        )

    def test_recommendations_russian_language(self):
        """Test recommendations in Russian language."""
        coverage = {
            "iron_mg": NutrientCoverage(
                nutrient_name="iron_mg",
                target_amount=15.0,
                consumed_amount=8.0,
                unit="mg",
            )
        }

        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        recommendations = generate_deficiency_recommendations(coverage, profile, "ru")

        # Should have Russian recommendations
        assert len(recommendations) > 0
        assert any(
            "железо" in rec.lower() or "говядина" in rec.lower()
            for rec in recommendations
        )

    def test_no_deficiencies(self):
        """Test when there are no deficiencies."""
        coverage = {
            "protein_g": NutrientCoverage(
                nutrient_name="protein_g",
                target_amount=120.0,
                consumed_amount=120.0,
                unit="g",
            )
        }

        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        recommendations = generate_deficiency_recommendations(coverage, profile, "en")

        # Should have no recommendations when no deficiencies
        assert len(recommendations) == 0

    def test_non_priority_nutrient_deficiency(self):
        """Test deficiency in non-priority nutrient."""
        coverage = {
            "magnesium_mg": NutrientCoverage(
                nutrient_name="magnesium_mg",
                target_amount=320.0,
                consumed_amount=160.0,
                unit="mg",
            )
        }

        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        recommendations = generate_deficiency_recommendations(coverage, profile, "en")

        # Should handle non-priority nutrients appropriately
        assert isinstance(recommendations, list)


class TestWeeklyCoverage:
    """Test weekly coverage calculations."""

    def test_weekly_average_calculation(self):
        """Test calculating weekly average coverage."""
        daily_coverages = [
            {
                "protein_g": NutrientCoverage(
                    nutrient_name="protein_g",
                    target_amount=120.0,
                    consumed_amount=100.0,
                    unit="g",
                )
            },
            {
                "protein_g": NutrientCoverage(
                    nutrient_name="protein_g",
                    target_amount=120.0,
                    consumed_amount=140.0,
                    unit="g",
                )
            },
        ]

        weekly_averages = calculate_weekly_coverage(daily_coverages)

        # Should calculate correct average (83.3% + 116.7% = 100%)
        assert "protein_g" in weekly_averages
        assert 98 <= weekly_averages["protein_g"] <= 102

    def test_single_day_coverage(self):
        """Test coverage calculation with single day."""
        daily_coverages = [
            {
                "protein_g": NutrientCoverage(
                    nutrient_name="protein_g",
                    target_amount=120.0,
                    consumed_amount=120.0,
                    unit="g",
                )
            }
        ]

        weekly_averages = calculate_weekly_coverage(daily_coverages)

        # Should return 100% for single day at target
        assert weekly_averages["protein_g"] == 100.0

    def test_missing_nutrients_in_some_days(self):
        """Test handling missing nutrients in some days."""
        daily_coverages = [
            {
                "protein_g": NutrientCoverage(
                    nutrient_name="protein_g",
                    target_amount=120.0,
                    consumed_amount=120.0,
                    unit="g",
                ),
                "iron_mg": NutrientCoverage(
                    nutrient_name="iron_mg",
                    target_amount=15.0,
                    consumed_amount=15.0,
                    unit="mg",
                ),
            },
            {
                "protein_g": NutrientCoverage(
                    nutrient_name="protein_g",
                    target_amount=120.0,
                    consumed_amount=100.0,
                    unit="g",
                )
                # Missing iron_mg for this day
            },
        ]

        weekly_averages = calculate_weekly_coverage(daily_coverages)

        # Should handle missing nutrients gracefully
        assert "protein_g" in weekly_averages
        # Iron appears in 1 of 2 days, so average should be based on available days
        if "iron_mg" in weekly_averages:
            assert weekly_averages["iron_mg"] == 50.0  # (100% + 0%) / 2


class TestTargetsSafety:
    """Test safety validation of nutrition targets."""

    def test_safe_targets(self):
        """Test validation of safe targets."""
        targets = NutritionTargets(
            kcal_daily=2000,
            macros=MacroTargets(
                protein_g=120, fat_g=67, carbs_g=250, fiber_g=28
            ),  # 1867 kcal total
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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        warnings = validate_targets_safety(targets)

        # Should have no warnings for safe targets
        assert len(warnings) == 0

    def test_low_calorie_warning(self):
        """Test warning for very low calories."""
        targets = NutritionTargets(
            kcal_daily=1000,  # Too low
            macros=MacroTargets(protein_g=120, fat_g=50, carbs_g=100, fiber_g=20),
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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        warnings = validate_targets_safety(targets)

        # Should warn about low calories
        assert len(warnings) > 0
        assert any("minimum" in warning.lower() for warning in warnings)

    def test_high_calorie_warning(self):
        """Test warning for very high calories."""
        targets = NutritionTargets(
            kcal_daily=5000,  # Too high
            macros=MacroTargets(protein_g=200, fat_g=200, carbs_g=600, fiber_g=50),
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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        warnings = validate_targets_safety(targets)

        # Should warn about high calories
        assert len(warnings) > 0
        assert any("high" in warning.lower() for warning in warnings)

    def test_high_protein_warning(self):
        """Test warning for very high protein."""
        targets = NutritionTargets(
            kcal_daily=2000,
            macros=MacroTargets(
                protein_g=200, fat_g=50, carbs_g=150, fiber_g=28
            ),  # 40% protein
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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        warnings = validate_targets_safety(targets)

        # Should warn about high protein
        assert len(warnings) > 0
        assert any("protein" in warning.lower() for warning in warnings)

    def test_low_hydration_warning(self):
        """Test warning for low hydration."""
        targets = NutritionTargets(
            kcal_daily=2000,
            macros=MacroTargets(protein_g=120, fat_g=70, carbs_g=250, fiber_g=28),
            water_ml_daily=1000,  # Too low
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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        warnings = validate_targets_safety(targets)

        # Should warn about low hydration
        assert len(warnings) > 0
        assert any(
            "hydration" in warning.lower() or "minimum" in warning.lower()
            for warning in warnings
        )

    def test_high_hydration_warning(self):
        """Test warning for very high hydration."""
        targets = NutritionTargets(
            kcal_daily=2000,
            macros=MacroTargets(protein_g=120, fat_g=70, carbs_g=250, fiber_g=28),
            water_ml_daily=5000,  # Too high
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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        warnings = validate_targets_safety(targets)

        # Should warn about high hydration
        assert len(warnings) > 0
        assert any(
            "hydration" in warning.lower() or "maximum" in warning.lower()
            for warning in warnings
        )


class TestFoodSources:
    """Test food source functions."""

    def test_get_nutrient_food_sources_english(self):
        """Test getting food sources in English."""
        sources = _get_nutrient_food_sources("en")

        assert isinstance(sources, dict)
        assert "iron_mg" in sources
        assert isinstance(sources["iron_mg"], list)
        assert len(sources["iron_mg"]) > 0

    def test_get_nutrient_food_sources_russian(self):
        """Test getting food sources in Russian."""
        sources = _get_nutrient_food_sources("ru")

        assert isinstance(sources, dict)
        assert "iron_mg" in sources
        assert isinstance(sources["iron_mg"], list)
        assert len(sources["iron_mg"]) > 0

    def test_adapt_for_vegetarian_iron(self):
        """Test vegetarian adaptation for iron."""
        original = "For iron_mg: lean red meat, lentils"
        adapted = _adapt_for_vegetarian(original, "iron_mg", "en")

        assert "vitamin C" in adapted or "absorption" in adapted

    def test_adapt_for_vegetarian_b12(self):
        """Test vegetarian adaptation for B12."""
        original = "For b12_ug: meat, fish"
        adapted = _adapt_for_vegetarian(original, "b12_ug", "en")

        assert "fortified" in adapted or "nutritional yeast" in adapted

    def test_adapt_for_vegetarian_russian(self):
        """Test vegetarian adaptation in Russian."""
        original = "Для железа: говядина, чечевица"
        adapted = _adapt_for_vegetarian(original, "iron_mg", "ru")

        assert "витамин" in adapted.lower() or "усвоение" in adapted.lower()

    def test_adapt_for_unknown_nutrient(self):
        """Test adaptation for unknown nutrient."""
        original = "For unknown_nutrient: some foods"
        adapted = _adapt_for_vegetarian(original, "unknown_nutrient", "en")

        # Should return original if no specific adaptation
        assert adapted == original


class TestBuildNutritionTargets:
    """Test the main build_nutrition_targets function."""

    def test_build_nutrition_targets_basic(self):
        """Test basic nutrition targets building."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        targets = build_nutrition_targets(profile)

        assert targets.kcal_daily > 0
        assert targets.macros.protein_g > 0
        assert targets.water_ml_daily > 0
        assert targets.calculated_for == profile
        assert targets.calculation_date != ""

    def test_build_nutrition_targets_weight_loss(self):
        """Test nutrition targets for weight loss."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=180,
            weight_kg=80,
            activity="active",
            goal="loss",
            deficit_pct=20,
        )

        targets = build_nutrition_targets(profile)

        # Should have reduced calories for weight loss
        assert targets.kcal_daily >= 1500  # Safety minimum for males
        assert targets.macros.protein_g > 0

    def test_build_nutrition_targets_weight_gain(self):
        """Test nutrition targets for weight gain."""
        profile = UserProfile(
            sex="female",
            age=22,
            height_cm=160,
            weight_kg=50,
            activity="light",
            goal="gain",
            surplus_pct=15,
        )

        targets = build_nutrition_targets(profile)

        # Should have increased calories for weight gain
        assert targets.kcal_daily > 1800
        assert targets.macros.carbs_g > 0


class TestScoreNutrientCoverage:
    """Test nutrient coverage scoring."""

    def test_score_nutrient_coverage_basic(self):
        """Test basic nutrient coverage scoring."""
        consumed_nutrients = {"protein_g": 100.0, "iron_mg": 10.0, "calcium_mg": 800.0}

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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        coverage = score_nutrient_coverage(consumed_nutrients, targets)

        assert "protein_g" in coverage
        assert "iron_mg" in coverage
        assert "calcium_mg" in coverage
        assert coverage["protein_g"].coverage_percent > 0
        assert coverage["iron_mg"].status == "deficient"  # 10/15 = 66.7%
        assert coverage["calcium_mg"].status == "adequate"  # 800/1000 = 80%

    def test_score_nutrient_coverage_missing_nutrients(self):
        """Test coverage scoring with missing nutrients."""
        consumed_nutrients = {}

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
            calculated_for=UserProfile(
                sex="female",
                age=30,
                height_cm=165,
                weight_kg=60,
                activity="moderate",
                goal="maintain",
            ),
            calculation_date="2024-01-01",
        )

        coverage = score_nutrient_coverage(consumed_nutrients, targets)

        # All nutrients should show 0% coverage
        for nutrient_name, nutrient_coverage in coverage.items():
            assert nutrient_coverage.consumed_amount == 0.0
            assert nutrient_coverage.status == "deficient"


class TestCalorieCalculation:
    """Test internal calorie calculation functions."""

    def test_calculate_target_calories_maintain(self):
        """Test calorie calculation for maintenance."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        base_tdee = 2000.0
        target_kcal = _calculate_target_calories(base_tdee, profile)

        assert target_kcal == 2000

    def test_calculate_target_calories_loss(self):
        """Test calorie calculation for weight loss."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="loss",
            deficit_pct=20,
        )

        base_tdee = 2000.0
        target_kcal = _calculate_target_calories(base_tdee, profile)

        # Should be reduced but not below safety minimum
        assert target_kcal >= 1200
        assert target_kcal < 2000

    def test_calculate_target_calories_gain(self):
        """Test calorie calculation for weight gain."""
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=180,
            weight_kg=70,
            activity="active",
            goal="gain",
            surplus_pct=15,
        )

        base_tdee = 2500.0
        target_kcal = _calculate_target_calories(base_tdee, profile)

        # Should be increased but within reasonable bounds
        assert target_kcal > 2500
        assert target_kcal <= int(2500 * 1.3)  # Max 30% above TDEE

    def test_calculate_target_calories_safety_minimum_female(self):
        """Test safety minimum for females."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=150,
            weight_kg=45,
            activity="sedentary",
            goal="loss",
            deficit_pct=25,
        )

        base_tdee = 1400.0  # Low TDEE
        target_kcal = _calculate_target_calories(base_tdee, profile)

        # Should not go below 1200 for females
        assert target_kcal >= 1200

    def test_calculate_target_calories_safety_minimum_male(self):
        """Test safety minimum for males."""
        profile = UserProfile(
            sex="male",
            age=30,
            height_cm=160,
            weight_kg=55,
            activity="sedentary",
            goal="loss",
            deficit_pct=25,
        )

        base_tdee = 1600.0  # Low TDEE
        target_kcal = _calculate_target_calories(base_tdee, profile)

        # Should not go below 1500 for males
        assert target_kcal >= 1500


class TestMacroCalculation:
    """Test macro calculation functions."""

    def test_calculate_macro_targets_basic(self):
        """Test basic macro calculation."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        macros = _calculate_macro_targets(2000, profile)

        assert macros.protein_g > 0
        assert macros.fat_g > 0
        assert macros.carbs_g > 0
        assert macros.fiber_g > 0

        # Check that macro calories approximately match target
        total_macro_kcal = (
            (macros.protein_g * 4) + (macros.carbs_g * 4) + (macros.fat_g * 9)
        )
        assert abs(total_macro_kcal - 2000) <= 100  # Allow 100 kcal tolerance

    def test_calculate_macro_targets_weight_loss(self):
        """Test macro calculation for weight loss."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="loss",
        )

        macros = _calculate_macro_targets(1600, profile)

        # Weight loss should have higher protein percentage
        protein_percent = (macros.protein_g * 4) / 1600 * 100
        assert protein_percent >= 20  # Should be at least 20% protein


class TestMicroAndActivityCalculation:
    """Test micro and activity calculation functions."""

    def test_calculate_micro_targets_basic(self):
        """Test micronutrient calculation."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        micros = _calculate_micro_targets(profile)

        assert micros.iron_mg > 0
        assert micros.calcium_mg > 0
        assert micros.vitamin_c_mg > 0
        assert micros.folate_ug > 0

    def test_calculate_activity_targets_basic(self):
        """Test activity targets calculation."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        activity = _calculate_activity_targets(profile)

        assert activity.moderate_aerobic_min > 0
        assert activity.strength_sessions > 0
        assert activity.steps_daily > 0

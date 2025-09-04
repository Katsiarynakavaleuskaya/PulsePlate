"""
Tests for Premium Targets (P1) Implementation

RU: Тесты для реализации Премиум Таргетов (P1).
EN: Tests for Premium Targets (P1) implementation.
"""

from typing import Any, Dict

import pytest

from core.recommendations import build_nutrition_targets
from core.targets import NutritionTargets, UserProfile


class TestPremiumTargets:
    """Test Premium Targets implementation."""

    def test_premium_targets_structure(self):
        """Test that premium targets return the correct structure."""
        # Create a test profile
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain"
        )

        # Build targets
        targets = build_nutrition_targets(profile)

        # Check that we have a NutritionTargets object
        assert isinstance(targets, NutritionTargets)

        # Check that all required fields are present
        assert hasattr(targets, "kcal_daily")
        assert hasattr(targets, "macros")
        assert hasattr(targets, "water_ml_daily")
        assert hasattr(targets, "micros")
        assert hasattr(targets, "activity")

        # Check that macros have all required fields
        assert hasattr(targets.macros, "protein_g")
        assert hasattr(targets.macros, "fat_g")
        assert hasattr(targets.macros, "carbs_g")
        assert hasattr(targets.macros, "fiber_g")

        # Check that micros have all required fields
        assert hasattr(targets.micros, "iron_mg")
        assert hasattr(targets.micros, "calcium_mg")
        assert hasattr(targets.micros, "magnesium_mg")
        assert hasattr(targets.micros, "zinc_mg")
        assert hasattr(targets.micros, "potassium_mg")
        assert hasattr(targets.micros, "iodine_ug")
        assert hasattr(targets.micros, "selenium_ug")
        assert hasattr(targets.micros, "folate_ug")
        assert hasattr(targets.micros, "b12_ug")
        assert hasattr(targets.micros, "vitamin_d_iu")
        assert hasattr(targets.micros, "vitamin_a_ug")
        assert hasattr(targets.micros, "vitamin_c_mg")

        # Check that activity has all required fields
        assert hasattr(targets.activity, "moderate_aerobic_min")
        assert hasattr(targets.activity, "vigorous_aerobic_min")
        assert hasattr(targets.activity, "strength_sessions")
        assert hasattr(targets.activity, "steps_daily")

    def test_premium_targets_values_female(self):
        """Test premium targets values for adult female (19-50)."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain"
        )

        targets = build_nutrition_targets(profile)

        # Check kcal range
        assert 1200 <= targets.kcal_daily <= 4000

        # Check macronutrient calculations based on body weight
        # Protein: 1.6-1.8 g/kg body weight
        assert 60 * 1.6 <= targets.macros.protein_g <= 60 * 1.8

        # Fat: 0.8-1.0 g/kg body weight
        assert 60 * 0.8 <= targets.macros.fat_g <= 60 * 1.0

        # Fiber: 25-30 g for lower calorie diets, but can be higher for higher calorie diets
        # Based on WHO: 14g fiber per 1000 kcal
        expected_fiber_min = max(25, int((targets.kcal_daily / 1000) * 14) - 5)
        expected_fiber_max = min(40, int((targets.kcal_daily / 1000) * 14) + 5)
        assert expected_fiber_min <= targets.macros.fiber_g <= expected_fiber_max

        # Check key micronutrient values for women
        assert targets.micros.iron_mg == 18.0  # High for menstruation
        assert targets.micros.calcium_mg == 1000.0
        assert targets.micros.vitamin_d_iu == 600.0
        assert targets.micros.b12_ug == 2.4
        assert targets.micros.folate_ug == 400.0
        assert targets.micros.magnesium_mg == 310.0
        assert targets.micros.potassium_mg == 3500.0

        # Check hydration target (~30 ml/kg)
        expected_water = int(60 * 30)
        assert abs(targets.water_ml_daily - expected_water) <= 100  # Allow some variation

        # Check activity targets (150/75 min/week)
        assert targets.activity.moderate_aerobic_min == 150
        assert targets.activity.vigorous_aerobic_min == 75
        assert targets.activity.strength_sessions == 2
        assert targets.activity.steps_daily == 8000

    def test_premium_targets_values_male(self):
        """Test premium targets values for adult male (19-50)."""
        profile = UserProfile(
            sex="male",
            age=30,
            height_cm=180,
            weight_kg=80,
            activity="moderate",
            goal="maintain"
        )

        targets = build_nutrition_targets(profile)

        # Check kcal range
        assert 1200 <= targets.kcal_daily <= 4000

        # Check macronutrient calculations based on body weight
        # Protein: 1.6-1.8 g/kg body weight
        assert 80 * 1.6 <= targets.macros.protein_g <= 80 * 1.8

        # Fat: 0.8-1.0 g/kg body weight
        assert 80 * 0.8 <= targets.macros.fat_g <= 80 * 1.0

        # Fiber: 25-30 g for lower calorie diets, but can be higher for higher calorie diets
        # Based on WHO: 14g fiber per 1000 kcal
        expected_fiber_min = max(25, int((targets.kcal_daily / 1000) * 14) - 5)
        expected_fiber_max = min(40, int((targets.kcal_daily / 1000) * 14) + 5)
        assert expected_fiber_min <= targets.macros.fiber_g <= expected_fiber_max

        # Check key micronutrient values for men
        assert targets.micros.iron_mg == 8.0  # Lower than women
        assert targets.micros.calcium_mg == 1000.0
        assert targets.micros.vitamin_d_iu == 600.0
        assert targets.micros.b12_ug == 2.4
        assert targets.micros.folate_ug == 400.0
        assert targets.micros.magnesium_mg == 400.0
        assert targets.micros.potassium_mg == 3500.0
        assert targets.micros.zinc_mg == 11.0  # Higher than women

        # Check hydration target (~30 ml/kg)
        expected_water = int(80 * 30)
        assert abs(targets.water_ml_daily - expected_water) <= 100  # Allow some variation

        # Check activity targets (150/75 min/week)
        assert targets.activity.moderate_aerobic_min == 150
        assert targets.activity.vigorous_aerobic_min == 75
        assert targets.activity.strength_sessions == 2
        assert targets.activity.steps_daily == 8000

    def test_premium_targets_get_summary(self):
        """Test that get_summary returns the correct structure."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain"
        )

        targets = build_nutrition_targets(profile)
        summary = targets.get_summary()

        # Check summary structure
        assert "kcal_daily" in summary
        assert "macros" in summary
        assert "water_ml_daily" in summary
        assert "micros" in summary
        assert "activity" in summary

        # Check macros structure
        assert "protein_g" in summary["macros"]
        assert "fat_g" in summary["macros"]
        assert "carbs_g" in summary["macros"]
        assert "fiber_g" in summary["macros"]

        # Check micros structure
        assert isinstance(summary["micros"], dict)
        assert len(summary["micros"]) > 0

        # Check activity structure
        assert "moderate_aerobic_min" in summary["activity"]
        assert "vigorous_aerobic_min" in summary["activity"]
        assert "strength_sessions" in summary["activity"]
        assert "steps_daily" in summary["activity"]

    @pytest.mark.parametrize("sex", ["female", "male"])
    @pytest.mark.parametrize("lang", ["ru", "en", "es"])
    def test_premium_targets_invariance(self, sex: str, lang: str):
        """Test invariance properties of premium targets."""
        profile = UserProfile(
            sex=sex,
            age=30,
            height_cm=170,
            weight_kg=70,
            activity="moderate",
            goal="maintain"
        )

        targets = build_nutrition_targets(profile)

        # Test invariants
        # 1. TDEE should be >= BMR
        # Note: We can't directly access BMR here, but we know TDEE is calculated from BMR
        # and should always be >= BMR

        # 2. kcal_loss should be >= 1200
        loss_profile = UserProfile(
            sex=sex,
            age=30,
            height_cm=170,
            weight_kg=70,
            activity="moderate",
            goal="loss"
        )

        loss_targets = build_nutrition_targets(loss_profile)
        assert loss_targets.kcal_daily >= 1200

        # 3. All macro values should be non-negative
        assert targets.macros.protein_g >= 0
        assert targets.macros.fat_g >= 0
        assert targets.macros.carbs_g >= 0
        assert targets.macros.fiber_g >= 0

        # 4. All micro values should be positive
        micro_dict = targets.micros.get_priority_nutrients()
        for value in micro_dict.values():
            assert value > 0

    def test_premium_targets_keys_and_ranges(self):
        """Test that premium targets have correct keys and ranges."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain"
        )

        targets = build_nutrition_targets(profile)

        # Check that all required keys are present
        # Energy and macronutrients
        assert isinstance(targets.kcal_daily, int)
        assert hasattr(targets.macros, "protein_g")
        assert hasattr(targets.macros, "fat_g")
        assert hasattr(targets.macros, "carbs_g")
        assert hasattr(targets.macros, "fiber_g")

        # Hydration
        assert isinstance(targets.water_ml_daily, int)

        # Micronutrients (check that all required ones are present)
        required_micros = [
            "iron_mg", "calcium_mg", "magnesium_mg", "zinc_mg", "potassium_mg",
            "iodine_ug", "selenium_ug", "folate_ug", "b12_ug", "vitamin_d_iu",
            "vitamin_a_ug", "vitamin_c_mg"
        ]
        for micro in required_micros:
            assert hasattr(targets.micros, micro)

        # Physical activity
        assert hasattr(targets.activity, "moderate_aerobic_min")
        assert hasattr(targets.activity, "vigorous_aerobic_min")
        assert hasattr(targets.activity, "strength_sessions")
        assert hasattr(targets.activity, "steps_daily")

        # Check ranges
        # kcal: 1200-4000
        assert 1200 <= targets.kcal_daily <= 4000

        # Macros ranges based on body weight
        # Protein: 1.6-1.8 g/kg
        assert 60 * 1.6 <= targets.macros.protein_g <= 60 * 1.8

        # Fat: 0.8-1.0 g/kg
        assert 60 * 0.8 <= targets.macros.fat_g <= 60 * 1.0

        # Fiber: 25-30 g (approximately)
        assert 20 <= targets.macros.fiber_g <= 45

        # Water: ~30 ml/kg
        expected_water = 60 * 30
        assert abs(targets.water_ml_daily - expected_water) <= 200

        # Activity: 150/75 min/week
        assert targets.activity.moderate_aerobic_min == 150
        assert targets.activity.vigorous_aerobic_min == 75
        assert targets.activity.strength_sessions == 2
        assert targets.activity.steps_daily == 8000


if __name__ == "__main__":
    pytest.main([__file__])

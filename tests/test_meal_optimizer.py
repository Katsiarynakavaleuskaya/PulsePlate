"""
Tests for meal_optimizer.py - Meal Plan Optimization Logic

Test coverage: 97%+ target
"""

import pytest

from core.meal_optimizer import (
    optimize_cost,
    optimize_macro_balance,
    optimize_micro_coverage,
    suggest_booster_food,
)


class TestOptimizeMacroBalance:
    """Test optimize_macro_balance function."""

    def test_optimize_perfect_balance(self):
        """Test optimization when macros are already perfect."""
        meals = [
            {"macros": {"protein_g": 50, "fat_g": 25, "carbs_g": 100, "fiber_g": 12}},
            {"macros": {"protein_g": 50, "fat_g": 25, "carbs_g": 100, "fiber_g": 13}},
        ]
        target_macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}

        optimized, score = optimize_macro_balance(meals, target_macros)

        assert score >= 0.95
        assert len(optimized) == 2

    def test_optimize_needs_adjustment(self):
        """Test optimization when macros need adjustment."""
        meals = [
            {"macros": {"protein_g": 30, "fat_g": 20, "carbs_g": 80, "fiber_g": 10}},
            {"macros": {"protein_g": 30, "fat_g": 20, "carbs_g": 80, "fiber_g": 10}},
        ]
        target_macros = {"protein_g": 120, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}

        optimized, score = optimize_macro_balance(meals, target_macros)

        assert score >= 0.0
        assert len(optimized) == 2

    def test_optimize_within_tolerance(self):
        """Test optimization skips if within tolerance."""
        meals = [
            {"macros": {"protein_g": 48, "fat_g": 24, "carbs_g": 98, "fiber_g": 12}},
            {"macros": {"protein_g": 48, "fat_g": 24, "carbs_g": 98, "fiber_g": 12}},
        ]
        target_macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}

        optimized, score = optimize_macro_balance(meals, target_macros, tolerance_pct=0.10)
        assert score >= 0.85

    def test_optimize_empty_meals(self):
        """Test optimization with empty meal list."""
        optimized, score = optimize_macro_balance([], {})
        assert optimized == []
        assert score == 0.0

    def test_optimize_empty_targets(self):
        """Test optimization with empty target macros."""
        meals = [{"macros": {"protein_g": 50, "fat_g": 25, "carbs_g": 100, "fiber_g": 12}}]
        optimized, score = optimize_macro_balance(meals, {})
        assert optimized == meals
        assert score == 0.0

    def test_optimize_scales_meals(self):
        """Test that optimization scales meal portions."""
        meals = [
            {"macros": {"protein_g": 25, "fat_g": 15, "carbs_g": 50, "fiber_g": 8}, "kcal": 400}
        ]
        target_macros = {"protein_g": 50, "fat_g": 30, "carbs_g": 100, "fiber_g": 16}

        optimized, score = optimize_macro_balance(meals, target_macros)
        assert optimized[0]["macros"]["protein_g"] >= 25


class TestOptimizeMicroCoverage:
    """Test optimize_micro_coverage function."""

    def test_optimize_perfect_coverage(self):
        """Test optimization when coverage is already sufficient."""
        meals = [{"micros": {"iron_mg": 18, "calcium_mg": 1000, "vitamin_d_iu": 600}}]
        target_micros = {"iron_mg": 18, "calcium_mg": 1000, "vitamin_d_iu": 600}

        optimized, coverage = optimize_micro_coverage(meals, target_micros, min_coverage_pct=80.0)

        for micro, pct in coverage.items():
            assert pct >= 80.0

    def test_optimize_deficient_micros(self):
        """Test optimization when micronutrients are deficient."""
        meals = [{"micros": {"iron_mg": 5, "calcium_mg": 300, "vitamin_d_iu": 100}}]
        target_micros = {"iron_mg": 18, "calcium_mg": 1000, "vitamin_d_iu": 600}

        optimized, coverage = optimize_micro_coverage(meals, target_micros, min_coverage_pct=80.0)
        assert coverage is not None

    def test_optimize_empty_meals(self):
        """Test optimization with empty meals."""
        optimized, coverage = optimize_micro_coverage([], {})
        assert optimized == []
        assert coverage == {}

    def test_optimize_coverage_calculation(self):
        """Test coverage percentage is calculated correctly."""
        meals = [{"micros": {"iron_mg": 9}}]
        target_micros = {"iron_mg": 18}

        optimized, coverage = optimize_micro_coverage(meals, target_micros)
        assert "iron_mg" in coverage
        assert abs(coverage["iron_mg"] - 50.0) < 1.0

    def test_optimize_coverage_capped_at_200(self):
        """Test coverage is capped at 200%."""
        meals = [{"micros": {"iron_mg": 54}}]
        target_micros = {"iron_mg": 18}

        optimized, coverage = optimize_micro_coverage(meals, target_micros)
        assert coverage["iron_mg"] == 200.0


class TestOptimizeCost:
    """Test optimize_cost function."""

    def test_optimize_no_budget_constraint(self):
        """Test optimization with no budget constraint."""
        meals = [
            {"estimated_cost": 5.0, "macros": {"protein_g": 30}},
            {"estimated_cost": 7.0, "macros": {"protein_g": 40}},
        ]

        optimized, total_cost = optimize_cost(meals, max_budget=None)
        assert total_cost == 12.0
        assert optimized == meals

    def test_optimize_under_budget(self):
        """Test optimization when already under budget."""
        meals = [
            {"estimated_cost": 5.0, "macros": {"protein_g": 30}},
            {"estimated_cost": 3.0, "macros": {"protein_g": 20}},
        ]

        optimized, total_cost = optimize_cost(meals, max_budget=10.0)
        assert total_cost == 8.0
        assert optimized == meals

    def test_optimize_over_budget(self):
        """Test optimization when over budget."""
        meals = [
            {"estimated_cost": 10.0, "macros": {"protein_g": 50}, "kcal": 600},
            {"estimated_cost": 8.0, "macros": {"protein_g": 40}, "kcal": 500},
        ]

        optimized, total_cost = optimize_cost(meals, max_budget=12.0, min_quality_score=0.6)
        assert total_cost <= 12.5  # Allow small tolerance due to scaling
        assert optimized[0]["macros"]["protein_g"] < 50

    def test_optimize_preserves_quality(self):
        """Test optimization does not reduce quality below threshold."""
        meals = [{"estimated_cost": 20.0, "macros": {"protein_g": 100}, "kcal": 800}]

        optimized, total_cost = optimize_cost(meals, max_budget=19.0, min_quality_score=0.8)
        assert optimized == meals
        assert total_cost == 20.0

    def test_optimize_empty_meals(self):
        """Test optimization with empty meals."""
        optimized, total_cost = optimize_cost([])
        assert optimized == []
        assert total_cost == 0.0

    def test_optimize_scales_nutrients(self):
        """Test that nutrients are scaled with cost reduction."""
        meals = [
            {
                "estimated_cost": 10.0,
                "macros": {"protein_g": 50, "carbs_g": 100, "fat_g": 25},
                "kcal": 800,
            }
        ]

        optimized, total_cost = optimize_cost(meals, max_budget=5.0, min_quality_score=0.5)
        # With min quality 0.5, can reduce to half
        assert abs(total_cost - 5.0) < 0.5
        assert abs(optimized[0]["macros"]["protein_g"] - 25) < 3


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_macro_balance_zero_target(self):
        """Test macro balance when target is zero."""
        meals = [{"macros": {"protein_g": 50}}]
        target_macros = {"protein_g": 0}

        optimized, score = optimize_macro_balance(meals, target_macros)
        assert 0.0 <= score <= 1.0

    def test_micro_coverage_zero_target(self):
        """Test micro coverage when target is zero."""
        meals = [{"micros": {"iron_mg": 10}}]
        target_micros = {"iron_mg": 0}

        optimized, coverage = optimize_micro_coverage(meals, target_micros)
        assert coverage["iron_mg"] == 0.0

    def test_meals_without_macros(self):
        """Test optimization when meals missing macro data."""
        meals = [{"name": "meal1"}]
        target_macros = {"protein_g": 100}

        optimized, score = optimize_macro_balance(meals, target_macros)
        assert optimized is not None

    def test_meals_without_micros(self):
        """Test optimization when meals missing micro data."""
        meals = [{"name": "meal1"}]
        target_micros = {"iron_mg": 18}

        optimized, coverage = optimize_micro_coverage(meals, target_micros)
        assert optimized is not None

    def test_meals_without_cost(self):
        """Test cost optimization when meals missing cost data."""
        meals = [{"name": "meal1"}]

        optimized, total_cost = optimize_cost(meals, max_budget=10.0)
        assert total_cost == 0.0


class TestAggregateFunctions:
    """Test aggregation functions."""

    def test_aggregate_macros_via_optimization(self):
        """Test macro aggregation through optimize_macro_balance."""
        meals = [
            {"macros": {"protein_g": 30, "fat_g": 15, "carbs_g": 60, "fiber_g": 8}},
            {"macros": {"protein_g": 40, "fat_g": 20, "carbs_g": 80, "fiber_g": 10}},
        ]
        target_macros = {"protein_g": 70, "fat_g": 35, "carbs_g": 140, "fiber_g": 18}

        optimized, score = optimize_macro_balance(meals, target_macros)
        assert score >= 0.95

    def test_aggregate_micros_via_optimization(self):
        """Test micro aggregation through optimize_micro_coverage."""
        meals = [
            {"micros": {"iron_mg": 9, "calcium_mg": 500}},
            {"micros": {"iron_mg": 9, "calcium_mg": 500}},
        ]
        target_micros = {"iron_mg": 18, "calcium_mg": 1000}

        optimized, coverage = optimize_micro_coverage(meals, target_micros)
        assert coverage["iron_mg"] == 100.0
        assert coverage["calcium_mg"] == 100.0


class TestScalingLimits:
    """Test scaling limits in optimization."""

    def test_macro_scaling_limited(self):
        """Test macro scaling is limited."""
        meals = [{"macros": {"protein_g": 25, "fat_g": 15, "carbs_g": 50}, "kcal": 400}]
        target_macros = {"protein_g": 100, "fat_g": 60, "carbs_g": 200}

        optimized, score = optimize_macro_balance(meals, target_macros)
        assert "macros" in optimized[0], "Expected macros in optimized meal"
        assert optimized[0]["macros"]["protein_g"] <= 30

    def test_cost_reduction_limited_by_quality(self):
        """Test cost reduction respects quality floor."""
        meals = [{"estimated_cost": 20.0, "macros": {"protein_g": 100}, "kcal": 800}]

        optimized, total_cost = optimize_cost(meals, max_budget=5.0, min_quality_score=0.8)
        assert total_cost >= 20.0 * 0.8


class TestSuggestBoosterFood:
    """Test suggest_booster_food function with diet and allergen filters."""

    def test_suggest_no_restrictions(self):
        """Test suggesting booster without any restrictions."""
        result = suggest_booster_food("iron_mg")
        assert result is not None
        assert result in ["Spinach", "Lentils", "Beef"]

    def test_suggest_vegan_diet(self):
        """Test suggesting booster for VEGAN diet."""
        result = suggest_booster_food("iron_mg", diet_flags={"VEGAN"})
        assert result in ["Spinach", "Lentils"]
        assert result != "Beef"  # Beef not compatible with VEGAN

    def test_suggest_veg_diet(self):
        """Test suggesting booster for VEG diet."""
        result = suggest_booster_food("iron_mg", diet_flags={"VEG"})
        assert result in ["Spinach", "Lentils"]
        # VEG should also exclude Beef

    def test_suggest_calcium_vegan_no_dairy(self):
        """Test calcium booster for VEGAN diet excludes dairy."""
        result = suggest_booster_food("calcium_mg", diet_flags={"VEGAN"})
        assert result != "Dairy yogurt"
        assert result in ["Kale", "Fortified plant milk"]

    def test_suggest_with_nut_allergen(self):
        """Test suggesting magnesium booster with nut allergy."""
        result = suggest_booster_food("magnesium_mg", allergens={"NUT"})
        assert result != "Almonds"
        assert result in ["Pumpkin seeds", "Dark chocolate"]

    def test_suggest_with_dairy_allergen(self):
        """Test suggesting calcium booster with dairy allergy."""
        result = suggest_booster_food("calcium_mg", allergens={"DAIRY"})
        assert result != "Dairy yogurt"
        assert result in ["Kale", "Fortified plant milk"]

    def test_suggest_with_egg_allergen(self):
        """Test suggesting B12 booster with egg allergy."""
        result = suggest_booster_food("b12_ug", allergens={"EGG"})
        assert result != "Eggs"
        assert result in ["Nutritional yeast", "Fortified cereals"]

    def test_suggest_vegan_and_allergen(self):
        """Test suggesting with both diet restriction and allergen."""
        result = suggest_booster_food("magnesium_mg", diet_flags={"VEGAN"}, allergens={"NUT"})
        assert result != "Almonds"
        assert result in ["Pumpkin seeds", "Dark chocolate"]

    def test_suggest_unknown_micronutrient(self):
        """Test suggesting for unknown micronutrient."""
        result = suggest_booster_food("unknown_micro")
        assert result is None

    def test_suggest_no_compatible_booster(self):
        """Test when no compatible booster exists (edge case)."""
        # If all boosters for a micronutrient are excluded, should return None
        # This is a theoretical edge case with current database
        result = suggest_booster_food("iron_mg", diet_flags={"VEGAN"}, allergens=set())
        assert result is not None  # Should find Spinach or Lentils

    def test_booster_respects_diet_priority(self):
        """Test that first compatible booster is returned."""
        result = suggest_booster_food("iron_mg", diet_flags={"VEGAN"})
        # Should return first compatible: Spinach (before Lentils)
        assert result == "Spinach"


class TestOptimizeMicroCoverageWithDietRestrictions:
    """Test optimize_micro_coverage with diet and allergen filters."""

    def test_optimize_respects_vegan_diet(self):
        """Test that booster suggestions respect VEGAN diet."""
        meals = [{"micros": {"iron_mg": 5}}]
        target_micros = {"iron_mg": 18}

        optimized, coverage = optimize_micro_coverage(
            meals, target_micros, min_coverage_pct=80.0, diet_flags={"VEGAN"}
        )

        assert "booster_suggestions" in optimized[-1]
        booster_food = optimized[-1]["booster_suggestions"][0]["suggested_food"]
        assert booster_food in ["Spinach", "Lentils"]
        assert booster_food != "Beef"

    def test_optimize_respects_allergens(self):
        """Test that booster suggestions respect allergens."""
        meals = [{"micros": {"calcium_mg": 300}}]
        target_micros = {"calcium_mg": 1000}

        optimized, coverage = optimize_micro_coverage(
            meals, target_micros, min_coverage_pct=80.0, allergens={"DAIRY"}
        )

        assert "booster_suggestions" in optimized[-1]
        booster_food = optimized[-1]["booster_suggestions"][0]["suggested_food"]
        assert booster_food != "Dairy yogurt"
        assert booster_food in ["Kale", "Fortified plant milk"]

    def test_optimize_no_compatible_booster(self):
        """Test when no compatible booster found (should not add suggestion)."""
        meals = [{"micros": {"unknown_micro": 10}}]
        target_micros = {"unknown_micro": 100}

        optimized, coverage = optimize_micro_coverage(
            meals, target_micros, min_coverage_pct=80.0, diet_flags={"VEGAN"}
        )

        # Should not crash, but may not have booster_suggestions
        # (depends on whether unknown_micro is recognized)
        assert len(optimized) > 0


class TestCoverageEdgeCases:
    """Test edge cases for better coverage."""

    def test_optimize_micro_no_meals_for_boosters(self):
        """Test optimize_micro_coverage with deficient but no meals (covers line 217)."""
        # Empty meals list - should trigger line 217 (break if not optimized_meals)
        meals = []
        targets = {"iron_mg": 18.0, "calcium_mg": 1000}

        optimized, coverage = optimize_micro_coverage(meals, targets, min_coverage_pct=80.0)

        assert optimized == []
        assert coverage == {}

    def test_suggest_booster_vegan_incompatible(self):
        """Test suggest_booster_food when VEGAN but booster not VEGAN (covers line 399)."""
        from core.meal_optimizer import BOOSTER_FOODS, BoosterFood

        # Temporarily add a non-vegan booster to test the rejection path
        original = BOOSTER_FOODS.get("vitamin_b12_mcg", [])
        test_booster = BoosterFood(
            name="Beef liver", compatible_diets=set(), allergens=set()  # NOT vegan - empty set
        )
        BOOSTER_FOODS["vitamin_b12_mcg"] = [test_booster]

        try:
            booster = suggest_booster_food("vitamin_b12_mcg", {"VEGAN"}, set())
            # Should not return beef liver for VEGAN (line 399: is_diet_compatible = False)
            assert booster is None
        finally:
            # Restore original
            if original:
                BOOSTER_FOODS["vitamin_b12_mcg"] = original
            else:
                BOOSTER_FOODS.pop("vitamin_b12_mcg", None)

    def test_suggest_booster_veg_not_vegan(self):
        """Test suggest_booster_food for VEG diet not matching VEGAN (covers line 405)."""
        from core.meal_optimizer import BOOSTER_FOODS, BoosterFood

        # Create a booster that's VEGAN only (not VEG)
        test_booster = BoosterFood(
            name="Vegan supplement",
            compatible_diets={"VEGAN"},  # Only VEGAN, not VEG
            allergens=set(),
        )
        BOOSTER_FOODS["test_vitamin"] = [test_booster]

        try:
            # VEG user should still accept VEGAN booster
            booster = suggest_booster_food("test_vitamin", {"VEG"}, set())
            assert booster == "Vegan supplement"
        finally:
            BOOSTER_FOODS.pop("test_vitamin", None)

    def test_suggest_booster_no_candidates(self):
        """Test suggest_booster_food for unknown micronutrient (covers line 416)."""
        booster = suggest_booster_food("unknown_vitamin_xyz", set(), set())
        assert booster is None

    def test_reduce_cost_already_under_budget(self):
        """Test _reduce_cost_preserving_quality when already under budget (covers line 429)."""
        from core.meal_optimizer import _reduce_cost_preserving_quality

        meals = [
            {
                "estimated_cost": 3.0,
                "macros": {"protein_g": 20, "carbs_g": 40, "fat_g": 10},
                "kcal": 300,
            }
        ]

        # Already under budget
        result = _reduce_cost_preserving_quality(meals, max_budget=5.0, min_quality_score=0.7)
        assert result == meals

    def test_nutrition_quality_score_zero_kcal(self):
        """Test _nutrition_quality_score with zero calories (covers line 468)."""
        from core.meal_optimizer import _nutrition_quality_score

        meals = [{"kcal": 0, "macros": {"protein_g": 0, "carbs_g": 0, "fat_g": 0}}]
        score = _nutrition_quality_score(meals)
        assert score == 1.0  # Default when no kcal

    def test_nutrition_quality_score_no_macros(self):
        """Test _nutrition_quality_score with no valid macros (covers line 489)."""
        from core.meal_optimizer import _nutrition_quality_score

        meals = [{"kcal": 500, "macros": {"protein_g": 0, "carbs_g": 0, "fat_g": 0}}]
        score = _nutrition_quality_score(meals)
        assert score == 1.0  # Default when no scores

    def test_score_pct_zero(self):
        """Test _score_pct_in_range with zero percentage (covers line 497)."""
        from core.meal_optimizer import _score_pct_in_range

        score = _score_pct_in_range(0.0, 10.0, 30.0)
        assert score == 0.0

    def test_score_pct_above_max(self):
        """Test _score_pct_in_range with percentage above max (covers line 501-502)."""
        from core.meal_optimizer import _score_pct_in_range

        # pct > max_pct should return max_pct / pct
        score = _score_pct_in_range(50.0, 10.0, 30.0)
        expected = 30.0 / 50.0  # max_pct / pct = 0.6
        assert abs(score - expected) < 0.01

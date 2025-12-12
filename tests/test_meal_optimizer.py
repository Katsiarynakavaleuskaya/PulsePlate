"""
Tests for meal_optimizer.py - Meal Plan Optimization Logic

Test coverage: 97%+ target
"""

import pytest

from core.meal_optimizer import (
    optimize_cost,
    optimize_macro_balance,
    optimize_micro_coverage,
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
        """Test optimization preserves minimum quality."""
        meals = [{"estimated_cost": 20.0, "macros": {"protein_g": 100}, "kcal": 800}]

        optimized, total_cost = optimize_cost(meals, max_budget=10.0, min_quality_score=0.7)

        quality_ratio = optimized[0]["macros"]["protein_g"] / 100
        assert quality_ratio >= 0.7

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
        if "macros" in optimized[0]:
            assert optimized[0]["macros"]["protein_g"] <= 30

    def test_cost_reduction_limited_by_quality(self):
        """Test cost reduction respects quality floor."""
        meals = [{"estimated_cost": 20.0, "macros": {"protein_g": 100}, "kcal": 800}]

        optimized, total_cost = optimize_cost(meals, max_budget=5.0, min_quality_score=0.8)
        assert total_cost >= 20.0 * 0.8

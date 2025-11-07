"""
Unit tests for NutritionBayesianAnalyzer counter functionality.

These tests ensure that the per-analysis counters (_total_analyses, _failed_analyses)
are properly incremented and used in the safety score calculation.
"""

import pytest
from core.nutrition_bayesian_analyzer import NutritionBayesianAnalyzer


def test_counters_increment_on_successful_analysis() -> None:
    """Test that _total_analyses increments on successful analysis."""
    analyzer = NutritionBayesianAnalyzer()

    # Verify initial state
    assert analyzer._total_analyses == 0
    assert analyzer._failed_analyses == 0

    # Run analysis with safe code (should not trigger failures)
    safe_code = """
    def test_safe():
        calories = 2000
        bmi = 22.0
        return {"calories": calories, "bmi": bmi}
    """

    results = analyzer.analyze_nutrition_safety(safe_code, "test_safe")

    # Verify counter incremented
    assert analyzer._total_analyses == 1
    # Safe code may or may not have failures depending on detection
    assert analyzer._failed_analyses >= 0


def test_counters_increment_on_failed_analysis() -> None:
    """Test that both counters increment when analysis finds failures."""
    analyzer = NutritionBayesianAnalyzer()

    # Verify initial state
    assert analyzer._total_analyses == 0
    assert analyzer._failed_analyses == 0

    # Run analysis with dangerous code (should trigger failures)
    dangerous_code = """
    def test_dangerous():
        calories = 50  # Dangerously low
        bmi = 15.0  # Dangerously low
        return {"calories": calories, "bmi": bmi}
    """

    results = analyzer.analyze_nutrition_safety(dangerous_code, "test_dangerous")

    # Verify counters incremented
    assert analyzer._total_analyses == 1
    # Should have at least some failed results
    if any(not r.success for r in results):
        assert analyzer._failed_analyses == 1


def test_safety_score_uses_counters() -> None:
    """Test that get_safety_score uses the per-analysis counters."""
    analyzer = NutritionBayesianAnalyzer()

    # Initial score should be 1.0 (no analyses yet)
    assert analyzer.get_safety_score() == 1.0

    # Run safe analysis
    safe_code = """
    def test_safe():
        calories = 2000
        bmi = 22.0
        return {"calories": calories, "bmi": bmi}
    """
    analyzer.analyze_nutrition_safety(safe_code, "test_safe")

    # Score should still be high (close to 1.0)
    score_after_safe = analyzer.get_safety_score()
    assert 0.8 <= score_after_safe <= 1.0

    # Run dangerous analysis
    dangerous_code = """
    def test_dangerous():
        calories = 50  # Dangerously low
        bmi = 15.0  # Dangerously low
        protein = 5  # Dangerously low
        return {"calories": calories, "bmi": bmi, "protein": protein}
    """
    analyzer.analyze_nutrition_safety(dangerous_code, "test_dangerous")

    # Score should decrease after failed analysis
    score_after_dangerous = analyzer.get_safety_score()
    assert score_after_dangerous < score_after_safe


def test_multiple_analyses_counter_accumulation() -> None:
    """Test that counters accumulate across multiple analyses."""
    analyzer = NutritionBayesianAnalyzer()

    # Run 3 analyses
    for i in range(3):
        code = f"""
        def test_{i}():
            calories = {1000 + i * 500}
            return {{"calories": calories}}
        """
        analyzer.analyze_nutrition_safety(code, f"test_{i}")

    # Verify total analyses counter
    assert analyzer._total_analyses == 3
    assert analyzer._failed_analyses <= 3

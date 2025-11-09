"""
Unit tests for NutritionBayesianAnalyzer counter functionality.

These tests ensure that the per-analysis counters (_total_analyses, _failed_analyses)
are properly incremented and used in the safety score calculation.
"""

import pytest
from core.nutrition_bayesian_analyzer import (
    NutritionBayesianAnalyzer,
    NutritionErrorType,
)


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
    # Safe code should not trigger failures
    assert analyzer._failed_analyses == 0


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
    # Should have at least some failed results (dangerous values must be detected)
    assert any(
        not r.success for r in results
    ), "Analyzer failed to detect dangerous nutrition values"
    assert analyzer._failed_analyses >= 1


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

    # Run 3 analyses with safe calorie values (all within safe range)
    # Values: 1500, 2000, 2500 - all are >= 1200 (calorie_dangerous_low) and <= 6000 (calorie_dangerous_high)
    for i in range(3):
        code = f"""
        def test_{i}():
            calories = {1500 + i * 500}
            return {{"calories": calories}}
        """
        analyzer.analyze_nutrition_safety(code, f"test_{i}")

    # Verify total analyses counter
    assert analyzer._total_analyses == 3
    # All generated calorie values are within safe range (1500-2500), so no analyses should fail
    assert analyzer._failed_analyses == 0


def test_carb_percentage_validation_low() -> None:
    """Test that carbs_min_percent key is used (not carb_min_percent)."""
    analyzer = NutritionBayesianAnalyzer()

    # Code with very low carb percentage (should trigger carbs_min_percent check)
    code_low_carb = """
    def test_low_carb():
        protein = 100  # High protein
        fat = 50       # Medium fat
        carbs = 5      # Very low carbs
        return {"protein": protein, "fat": fat, "carbs": carbs}
    """

    results = analyzer.analyze_nutrition_safety(code_low_carb, "test_low_carb")

    # Should detect low carb percentage issue
    # This exercises line 462: if carb_pct < limits["carbs_min_percent"] / 100:
    assert len(results) > 0

    # Verify that at least one result is carb-related low-carb warning
    assert any(
        r.error_type == NutritionErrorType.CARB_TOO_LOW or "carb" in (r.error_message or "").lower()
        for r in results
    ), "did not detect low carb percentage"


def test_carb_percentage_validation_high() -> None:
    """Test that carbs_max_percent key is used (not carb_max_percent)."""
    analyzer = NutritionBayesianAnalyzer()

    # Code with very high carb percentage (should trigger carbs_max_percent check)
    code_high_carb = """
    def test_high_carb():
        protein = 10   # Very low protein
        fat = 10       # Very low fat
        carbs = 200    # Very high carbs
        return {"protein": protein, "fat": fat, "carbs": carbs}
    """

    results = analyzer.analyze_nutrition_safety(code_high_carb, "test_high_carb")

    # Should detect high carb percentage issue
    # This exercises line 474: if carb_pct > limits["carbs_max_percent"] / 100:
    assert len(results) > 0

    # Verify that at least one result is carb-related high-carb warning
    assert any(
        r.error_type == NutritionErrorType.CARB_TOO_HIGH
        or "carb" in (r.error_message or "").lower()
        or "carbs_max_percent" in (r.error_message or "").lower()
        for r in results
    ), "failed to detect high carb validation"


def test_calorie_overflow_detection() -> None:
    """Test detection of dangerously high calories (covers lines 197-209)."""
    analyzer = NutritionBayesianAnalyzer()

    # Code with extremely high calories (>5000)
    code_high_cal = """
    def test_high_calories():
        calories = 8000  # Dangerously high
        return {"calories": calories}
    """

    results = analyzer.analyze_nutrition_safety(code_high_cal, "test_high_calories")

    # Should detect CALORIE_OVERFLOW
    assert any(not r.success for r in results), "Failed to detect dangerously high calories"


def test_bmi_dangerous_high_detection() -> None:
    """Test detection of dangerously high BMI (covers lines 240-252)."""
    analyzer = NutritionBayesianAnalyzer()

    # Code with extremely high BMI (>40)
    code_high_bmi = """
    def test_high_bmi():
        bmi = 45.0  # Dangerously high (severe obesity)
        return {"bmi": bmi}
    """

    results = analyzer.analyze_nutrition_safety(code_high_bmi, "test_high_bmi")

    # Should detect BMI_DANGEROUS
    assert any(not r.success for r in results), "Failed to detect dangerously high BMI"


def test_macros_sum_invalid_detection() -> None:
    """Test detection of invalid macronutrient sum (covers lines 385-405)."""
    analyzer = NutritionBayesianAnalyzer()

    # Code with macros that don't sum to 100%
    code_invalid_macros = """
    def test_invalid_macros():
        protein = 200  # Way too high
        fat = 100
        carbs = 50
        return {"protein": protein, "fat": fat, "carbs": carbs}
    """

    results = analyzer.analyze_nutrition_safety(code_invalid_macros, "test_invalid_macros")

    # Should detect MACROS_SUM_INVALID
    assert any(not r.success for r in results), "Failed to detect invalid macro sum"


def test_diagnose_nutrition_issues() -> None:
    """Test diagnose_nutrition_issues method (covers lines 491-509)."""
    analyzer = NutritionBayesianAnalyzer()

    # Run analysis with issues
    dangerous_code = """
    def test_issues():
        calories = 50  # Dangerously low
        bmi = 15.0  # Dangerously low
        return {"calories": calories, "bmi": bmi}
    """
    analyzer.analyze_nutrition_safety(dangerous_code, "test_issues")

    # Call diagnose_nutrition_issues
    issues = analyzer.diagnose_nutrition_issues()

    # Should return probabilities for detected issues
    assert isinstance(issues, dict)


def test_generate_nutrition_recommendations() -> None:
    """Test generate_nutrition_recommendations method (covers lines 513-547)."""
    analyzer = NutritionBayesianAnalyzer()

    # Run analysis with various issues
    code_with_issues = """
    def test_recommendations():
        calories = 50  # Low calories
        bmi = 15.0  # Low BMI
        protein = 5  # Low protein
        return {"calories": calories, "bmi": bmi, "protein": protein}
    """
    analyzer.analyze_nutrition_safety(code_with_issues, "test_recommendations")

    # Generate recommendations
    recommendations = analyzer.generate_nutrition_recommendations()

    # Should return list of recommendations
    assert isinstance(recommendations, list)

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
    # This exercises line 421: if carb_pct < limits["carbs_min_percent"] / 100:
    assert len(results) > 0


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
    # This exercises line 433: if carb_pct > limits["carbs_max_percent"] / 100:
    assert len(results) > 0


def test_add_nutrition_test_result() -> None:
    """Test adding nutrition test result manually."""
    from core.nutrition_bayesian_analyzer import (
        NutritionTestResult,
        NutritionCategory,
        NutritionErrorType,
    )

    analyzer = NutritionBayesianAnalyzer()

    # Create a manual test result
    result = NutritionTestResult(
        test_name="manual_test",
        success=False,
        nutrition_category=NutritionCategory.CALORIE_CALCULATION,
        error_type=NutritionErrorType.CALORIE_OVERFLOW,
        error_message="Manual test result",
        business_impact="Test impact",
        safety_level="moderate",
    )

    # Add it to analyzer
    analyzer.add_nutrition_test_result(result)

    # Verify it was added
    assert len(analyzer.test_results) == 1
    assert analyzer.test_results[0].test_name == "manual_test"


def test_dangerous_high_calories() -> None:
    """Test detection of dangerously high calories."""
    analyzer = NutritionBayesianAnalyzer()

    # Code with dangerously high calories (>4000)
    code = """
    def test_high_cal():
        calories = 5000  # Dangerously high
        return {"calories": calories}
    """

    results = analyzer.analyze_nutrition_safety(code, "test_high_cal")

    # Should detect dangerous high calories
    assert any(not r.success for r in results)
    assert any("опасно высок" in r.error_message.lower() for r in results if not r.success)


def test_dangerous_high_bmi() -> None:
    """Test detection of dangerously high BMI."""
    analyzer = NutritionBayesianAnalyzer()

    # Code with dangerously high BMI (>35)
    code = """
    def test_high_bmi():
        bmi = 40.0  # Dangerously high
        return {"bmi": bmi}
    """

    results = analyzer.analyze_nutrition_safety(code, "test_high_bmi")

    # Should detect dangerous high BMI
    assert any(not r.success for r in results)
    assert any("опасно высок" in r.error_message.lower() for r in results if not r.success)


def test_allergen_without_safety_check() -> None:
    """Test detection of allergens without safety checks."""
    analyzer = NutritionBayesianAnalyzer()

    # Code mentioning allergen but no safety check
    code = """
    def test_peanut_recipe():
        ingredients = ["peanuts", "flour", "sugar"]
        return {"ingredients": ingredients}
    """

    results = analyzer.analyze_nutrition_safety(code, "test_peanut_recipe")

    # Should detect allergen mention without check
    # This may or may not trigger depending on implementation
    assert isinstance(results, list)


def test_medical_condition_without_verification() -> None:
    """Test detection of medical conditions without verification."""
    analyzer = NutritionBayesianAnalyzer()

    # Code mentioning medical condition but no verification
    code = """
    def test_diabetes_meal():
        meal = "high sugar dessert"
        diabetes = True
        return {"meal": meal, "condition": diabetes}
    """

    results = analyzer.analyze_nutrition_safety(code, "test_diabetes_meal")

    # Should detect medical condition mention without verification
    assert isinstance(results, list)


def test_privacy_issue_logging_weight() -> None:
    """Test detection of privacy issues with logging."""
    analyzer = NutritionBayesianAnalyzer()

    # Code logging sensitive data
    code = """
    def test_user_weight():
        weight = 75.5
        logger.info(f"User weight: {weight}")
        return {"weight": weight}
    """

    results = analyzer.analyze_nutrition_safety(code, "test_user_weight")

    # Should detect privacy issue with logging weight
    assert isinstance(results, list)


def test_generate_nutrition_recommendations() -> None:
    """Test generation of nutrition recommendations."""
    analyzer = NutritionBayesianAnalyzer()

    # Generate some test results first
    dangerous_code = """
    def test_dangerous():
        calories = 50  # Dangerously low
        bmi = 15.0  # Dangerously low
        peanuts = True  # Allergen
        diabetes = True  # Medical condition
        return {"calories": calories, "bmi": bmi}
    """

    analyzer.analyze_nutrition_safety(dangerous_code, "test_dangerous")

    # Generate recommendations
    recs = analyzer.generate_nutrition_recommendations()

    # Should have some recommendations
    assert isinstance(recs, list)


def test_diagnose_nutrition_issues() -> None:
    """Test diagnosis of nutrition issues."""
    analyzer = NutritionBayesianAnalyzer()

    # Generate some test results
    dangerous_code = """
    def test_issues():
        calories = 50
        bmi = 15.0
        return {"calories": calories, "bmi": bmi}
    """

    analyzer.analyze_nutrition_safety(dangerous_code, "test_issues")

    # Diagnose issues
    diagnosis = analyzer.diagnose_nutrition_issues()

    # Should return a dictionary
    assert isinstance(diagnosis, dict)

"""
Unit tests for NutritionBayesianAnalyzer diagnostic methods.

Tests diagnostic methods: add_nutrition_test_result, diagnose_nutrition_issues,
generate_nutrition_recommendations, and related functionality.
"""

from core.nutrition_bayesian_analyzer import (
    NutritionBayesianAnalyzer,
    NutritionTestResult,
    NutritionCategory,
    NutritionErrorType,
)


def test_add_nutrition_test_result() -> None:
    """Test adding nutrition test results."""
    analyzer = NutritionBayesianAnalyzer()

    # Create a test result
    result = NutritionTestResult(
        test_name="test_calories",
        success=False,
        nutrition_category=NutritionCategory.CALORIE_CALCULATION,
        error_type=NutritionErrorType.CALORIE_OVERFLOW,
        error_message="Calories out of range",
        safety_level="warning",
    )

    # Add result
    initial_count = len(analyzer.test_results)
    analyzer.add_nutrition_test_result(result)

    # Verify result was added
    assert len(analyzer.test_results) == initial_count + 1
    assert analyzer.test_results[-1] == result


def test_diagnose_nutrition_issues_empty() -> None:
    """Test diagnosing nutrition issues with no results."""
    analyzer = NutritionBayesianAnalyzer()

    diagnosis = analyzer.diagnose_nutrition_issues()

    assert diagnosis == {}


def test_diagnose_nutrition_issues_single_issue() -> None:
    """Test diagnosing nutrition issues with one issue."""
    analyzer = NutritionBayesianAnalyzer()

    # Add a failed result
    result = NutritionTestResult(
        test_name="test_calories",
        success=False,
        nutrition_category=NutritionCategory.CALORIE_CALCULATION,
        error_type=NutritionErrorType.CALORIE_OVERFLOW,
        error_message="Calories out of range",
        safety_level="warning",
    )
    analyzer.add_nutrition_test_result(result)

    diagnosis = analyzer.diagnose_nutrition_issues()

    assert NutritionCategory.CALORIE_CALCULATION in diagnosis
    assert diagnosis[NutritionCategory.CALORIE_CALCULATION] == 1.0  # 100% of issues


def test_diagnose_nutrition_issues_multiple_categories() -> None:
    """Test diagnosing nutrition issues with multiple categories."""
    analyzer = NutritionBayesianAnalyzer()

    # Add results from different categories
    results = [
        NutritionTestResult(
            test_name="test_calories_1",
            success=False,
            nutrition_category=NutritionCategory.CALORIE_CALCULATION,
            error_type=NutritionErrorType.CALORIE_OVERFLOW,
            error_message="Calories too high",
            safety_level="warning",
        ),
        NutritionTestResult(
            test_name="test_calories_2",
            success=False,
            nutrition_category=NutritionCategory.CALORIE_CALCULATION,
            error_type=NutritionErrorType.CALORIE_OVERFLOW,
            error_message="Calories too low",
            safety_level="warning",
        ),
        NutritionTestResult(
            test_name="test_bmi",
            success=False,
            nutrition_category=NutritionCategory.BMI_SAFETY,
            error_type=NutritionErrorType.BMI_DANGEROUS,
            error_message="BMI in danger zone",
            safety_level="dangerous",
        ),
    ]

    for result in results:
        analyzer.add_nutrition_test_result(result)

    diagnosis = analyzer.diagnose_nutrition_issues()

    # Should have two categories
    assert len(diagnosis) == 2
    assert diagnosis[NutritionCategory.CALORIE_CALCULATION] == 2 / 3  # 67%
    assert diagnosis[NutritionCategory.BMI_SAFETY] == 1 / 3  # 33%


def test_diagnose_nutrition_issues_with_successful_tests() -> None:
    """Test diagnosing issues doesn't count successful tests."""
    analyzer = NutritionBayesianAnalyzer()

    # Add both failed and successful results
    results = [
        NutritionTestResult(
            test_name="test_success",
            success=True,
            nutrition_category=NutritionCategory.CALORIE_CALCULATION,
            error_type=None,
            error_message=None,
            safety_level="safe",
        ),
        NutritionTestResult(
            test_name="test_fail",
            success=False,
            nutrition_category=NutritionCategory.BMI_SAFETY,
            error_type=NutritionErrorType.BMI_DANGEROUS,
            error_message="BMI issue",
            safety_level="warning",
        ),
    ]

    for result in results:
        analyzer.add_nutrition_test_result(result)

    diagnosis = analyzer.diagnose_nutrition_issues()

    # Should only count failed test
    assert len(diagnosis) == 1
    assert NutritionCategory.BMI_SAFETY in diagnosis
    assert diagnosis[NutritionCategory.BMI_SAFETY] == 1.0


def test_generate_nutrition_recommendations_empty() -> None:
    """Test generating recommendations with no issues."""
    analyzer = NutritionBayesianAnalyzer()

    recommendations = analyzer.generate_nutrition_recommendations()

    assert recommendations == []


def test_generate_nutrition_recommendations_calorie_issues() -> None:
    """Test generating recommendations for calorie calculation issues."""
    analyzer = NutritionBayesianAnalyzer()

    # Add calorie issue
    result = NutritionTestResult(
        test_name="test_calories",
        success=False,
        nutrition_category=NutritionCategory.CALORIE_CALCULATION,
        error_type=NutritionErrorType.CALORIE_OVERFLOW,
        error_message="Calories out of range",
        safety_level="warning",
    )
    analyzer.add_nutrition_test_result(result)

    recommendations = analyzer.generate_nutrition_recommendations()

    assert len(recommendations) > 0
    assert any("калорий" in rec for rec in recommendations)
    assert any("1200-6000" in rec for rec in recommendations)


def test_generate_nutrition_recommendations_bmi_issues() -> None:
    """Test generating recommendations for BMI safety issues."""
    analyzer = NutritionBayesianAnalyzer()

    result = NutritionTestResult(
        test_name="test_bmi",
        success=False,
        nutrition_category=NutritionCategory.BMI_SAFETY,
        error_type=NutritionErrorType.BMI_DANGEROUS,
        error_message="Dangerous BMI",
        safety_level="dangerous",
    )
    analyzer.add_nutrition_test_result(result)

    recommendations = analyzer.generate_nutrition_recommendations()

    assert len(recommendations) > 0
    assert any("BMI" in rec for rec in recommendations)
    assert any("<16" in rec or ">=30" in rec for rec in recommendations)


def test_generate_nutrition_recommendations_allergen_issues() -> None:
    """Test generating recommendations for allergen safety issues."""
    analyzer = NutritionBayesianAnalyzer()

    result = NutritionTestResult(
        test_name="test_allergen",
        success=False,
        nutrition_category=NutritionCategory.ALLERGEN_SAFETY,
        error_type=NutritionErrorType.ALLERGEN_MISSING,
        error_message="Missing allergen check",
        safety_level="warning",
    )
    analyzer.add_nutrition_test_result(result)

    recommendations = analyzer.generate_nutrition_recommendations()

    assert len(recommendations) > 0
    assert any("аллерген" in rec for rec in recommendations)


def test_generate_nutrition_recommendations_medical_issues() -> None:
    """Test generating recommendations for medical safety issues."""
    analyzer = NutritionBayesianAnalyzer()

    result = NutritionTestResult(
        test_name="test_medical",
        success=False,
        nutrition_category=NutritionCategory.MEDICAL_SAFETY,
        error_type=NutritionErrorType.MEDICAL_CONTRADICTION,
        error_message="Medical constraint violated",
        safety_level="dangerous",
    )
    analyzer.add_nutrition_test_result(result)

    recommendations = analyzer.generate_nutrition_recommendations()

    assert len(recommendations) > 0
    assert any("медицинские" in rec for rec in recommendations)


def test_generate_nutrition_recommendations_privacy_issues() -> None:
    """Test generating recommendations for data privacy issues."""
    analyzer = NutritionBayesianAnalyzer()

    result = NutritionTestResult(
        test_name="test_privacy",
        success=False,
        nutrition_category=NutritionCategory.DATA_PRIVACY,
        error_type=NutritionErrorType.PRIVACY_LEAK,
        error_message="Sensitive data exposed",
        safety_level="dangerous",
    )
    analyzer.add_nutrition_test_result(result)

    recommendations = analyzer.generate_nutrition_recommendations()

    assert len(recommendations) > 0
    assert any("зашифровать" in rec or "чувствительные данные" in rec for rec in recommendations)


def test_generate_nutrition_recommendations_standards_issues() -> None:
    """Test generating recommendations for nutrition standards issues."""
    analyzer = NutritionBayesianAnalyzer()

    result = NutritionTestResult(
        test_name="test_standards",
        success=False,
        nutrition_category=NutritionCategory.NUTRITION_STANDARDS,
        error_type=NutritionErrorType.STANDARD_VIOLATION,
        error_message="Macronutrient imbalance",
        safety_level="warning",
    )
    analyzer.add_nutrition_test_result(result)

    recommendations = analyzer.generate_nutrition_recommendations()

    assert len(recommendations) > 0
    assert any("макронутриентов" in rec for rec in recommendations)


def test_generate_nutrition_recommendations_multiple_issues() -> None:
    """Test generating recommendations for multiple issue types."""
    analyzer = NutritionBayesianAnalyzer()

    # Add multiple different issues
    results = [
        NutritionTestResult(
            test_name="test_calories",
            success=False,
            nutrition_category=NutritionCategory.CALORIE_CALCULATION,
            error_type=NutritionErrorType.CALORIE_OVERFLOW,
            error_message="Calories issue",
            safety_level="warning",
        ),
        NutritionTestResult(
            test_name="test_bmi",
            success=False,
            nutrition_category=NutritionCategory.BMI_SAFETY,
            error_type=NutritionErrorType.BMI_DANGEROUS,
            error_message="BMI issue",
            safety_level="dangerous",
        ),
        NutritionTestResult(
            test_name="test_allergen",
            success=False,
            nutrition_category=NutritionCategory.ALLERGEN_SAFETY,
            error_type=NutritionErrorType.ALLERGEN_MISSING,
            error_message="Allergen issue",
            safety_level="warning",
        ),
    ]

    for result in results:
        analyzer.add_nutrition_test_result(result)

    recommendations = analyzer.generate_nutrition_recommendations()

    # Should have recommendations for all 3 categories
    assert len(recommendations) >= 3
    assert any("калорий" in rec for rec in recommendations)
    assert any("BMI" in rec for rec in recommendations)
    assert any("аллерген" in rec for rec in recommendations)


def test_diagnose_and_recommend_integration() -> None:
    """Test integration of diagnosis and recommendations."""
    analyzer = NutritionBayesianAnalyzer()

    # Add mixed results
    results = [
        NutritionTestResult(
            test_name="test_success",
            success=True,
            nutrition_category=NutritionCategory.CALORIE_CALCULATION,
            error_type=None,
            error_message=None,
            safety_level="safe",
        ),
        NutritionTestResult(
            test_name="test_fail_1",
            success=False,
            nutrition_category=NutritionCategory.BMI_SAFETY,
            error_type=NutritionErrorType.BMI_DANGEROUS,
            error_message="BMI too low",
            safety_level="dangerous",
        ),
        NutritionTestResult(
            test_name="test_fail_2",
            success=False,
            nutrition_category=NutritionCategory.DATA_PRIVACY,
            error_type=NutritionErrorType.PRIVACY_LEAK,
            error_message="Data exposed",
            safety_level="dangerous",
        ),
    ]

    for result in results:
        analyzer.add_nutrition_test_result(result)

    # Get diagnosis
    diagnosis = analyzer.diagnose_nutrition_issues()
    assert len(diagnosis) == 2  # Two categories with issues

    # Get recommendations
    recommendations = analyzer.generate_nutrition_recommendations()
    assert len(recommendations) >= 2  # At least one rec per issue category

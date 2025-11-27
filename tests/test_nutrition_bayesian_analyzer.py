#!/usr/bin/env python3
"""
Unit tests for NutritionBayesianAnalyzer.

Covers nutrition safety and health-related checks.
"""

import pytest
from core.nutrition_bayesian_analyzer import (
    NutritionBayesianAnalyzer,
    NutritionTestResult,
    NutritionCategory,
)


class TestNutritionBayesianAnalyzerInit:
    """Test analyzer initialization."""

    def test_init_default(self):
        """Test default initialization."""
        analyzer = NutritionBayesianAnalyzer()
        assert analyzer.test_results == []

    def test_init_with_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        analyzer = NutritionBayesianAnalyzer()
        # Should have reasonable defaults
        assert hasattr(analyzer, "safety_thresholds")
        assert "calorie_dangerous_low" in analyzer.safety_thresholds
        assert "calorie_dangerous_high" in analyzer.safety_thresholds


class TestNutritionSafetyAnalysis:
    """Test nutrition safety checks."""

    def test_analyze_simple_nutrition_code(self):
        """Test analysis of simple nutrition code."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_calories():
    calories = 2000
    assert calories > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_calories")
        assert isinstance(results, list)
        assert all(isinstance(r, NutritionTestResult) for r in results)

    def test_detect_low_calories(self):
        """Test detection of dangerously low calories."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_low_cal():
    calories = 500  # Too low
    assert calories
"""
        results = analyzer.analyze_nutrition_safety(code, "test_low_cal")
        assert isinstance(results, list)

    def test_detect_high_calories(self):
        """Test detection of excessively high calories."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_high_cal():
    calories = 10000  # Too high
    assert calories
"""
        results = analyzer.analyze_nutrition_safety(code, "test_high_cal")
        assert isinstance(results, list)


class TestBMIValidation:
    """Test BMI validation."""

    def test_detect_bmi_calculation(self):
        """Test detection of BMI calculations."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_bmi():
    bmi = 22.5
    assert 18.5 <= bmi <= 25
"""
        results = analyzer.analyze_nutrition_safety(code, "test_bmi")
        assert isinstance(results, list)

    def test_detect_invalid_bmi(self):
        """Test detection of invalid BMI values."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_bad_bmi():
    bmi = 50  # Unrealistic
    assert bmi
"""
        results = analyzer.analyze_nutrition_safety(code, "test_bad_bmi")
        assert isinstance(results, list)
        assert len(results) > 0
        # Expect a BMI safety violation to be flagged for unrealistic BMI=50
        assert any(
            ("bmi" in (r.error_message or "").lower())
            or (
                getattr(r, "error_type", None) is not None
                and getattr(r.error_type, "value", "").lower() == "bmi_dangerous"
            )
            for r in results
        )


class TestMacronutrientChecks:
    """Test macronutrient validation."""

    def test_detect_protein(self):
        """Test detection of protein values."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_protein():
    protein = 50.0
    assert protein > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_protein")
        assert isinstance(results, list)

    def test_detect_carbs(self):
        """Test detection of carbohydrate values."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_carbs():
    carbs = 200.5
    assert carbs > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_carbs")
        assert isinstance(results, list)

    def test_detect_fats(self):
        """Test detection of fat values."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_fats():
    fats = 70.0
    assert fats > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_fats")
        assert isinstance(results, list)


class TestAllergenDetection:
    """Test allergen-related checks."""

    def test_detect_allergen_keywords(self):
        """Test detection of allergen mentions."""
        analyzer = NutritionBayesianAnalyzer()
        code = "peanuts\nmilk\n"
        results = analyzer.analyze_nutrition_safety(code, "test_allergens")
        assert isinstance(results, list)
        assert len(results) > 0
        # Expect allergen mentions to be detected in analyzer output
        # Note: analyzer KB uses "milk" not "dairy"
        assert any(
            ("peanuts" in (r.error_message or "").lower())
            or ("milk" in (r.error_message or "").lower())
            or ("dairy" in (r.error_message or "").lower())
            for r in results
        )


class TestNutritionTestResult:
    """Test NutritionTestResult dataclass."""

    def test_nutrition_test_result_creation(self):
        """Test creation of NutritionTestResult."""
        result = NutritionTestResult(
            test_name="test_example",
            success=True,
            nutrition_category=NutritionCategory.CALORIE_CALCULATION,
            error_type=None,
            error_message="",
        )
        assert result.test_name == "test_example"
        assert result.success is True
        assert result.nutrition_category == NutritionCategory.CALORIE_CALCULATION


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_code(self):
        """Test analysis of empty code."""
        analyzer = NutritionBayesianAnalyzer()
        results = analyzer.analyze_nutrition_safety("", "test_empty")
        assert isinstance(results, list)

    def test_code_without_nutrition_data(self):
        """Test code with no nutrition-related content."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_generic():
    value = 42
    assert value > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_generic")
        assert isinstance(results, list)

    def test_malformed_code(self):
        """Test malformed code handling."""
        analyzer = NutritionBayesianAnalyzer()
        code = "def test_broken(:"
        results = analyzer.analyze_nutrition_safety(code, "test_broken")
        assert isinstance(results, list)

    def test_results_persistence(self):
        """Test that results are persisted."""
        analyzer = NutritionBayesianAnalyzer()
        initial_analyses = analyzer._total_analyses
        analyzer.analyze_nutrition_safety("bmi = 50", "test1")
        analyzer.analyze_nutrition_safety("calories = 10000", "test2")
        # Two analyze calls should increment _total_analyses by exactly 2
        assert analyzer._total_analyses == initial_analyses + 2

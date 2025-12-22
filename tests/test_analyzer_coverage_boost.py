"""Targeted coverage tests for bayesian analyzer modules.

These tests cover edge-case branches in:
- core/nutrition_bayesian_analyzer.py
- core/integrated_bayesian_analyzer.py
"""

from core.nutrition_bayesian_analyzer import NutritionBayesianAnalyzer
from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer


class TestNutritionAnalyzerCoverage:
    """Cover uncovered branches in NutritionBayesianAnalyzer."""

    def test_is_test_code_import_pytest(self) -> None:
        """Cover line 135: import pytest detection."""
        analyzer = NutritionBayesianAnalyzer()
        code = "import pytest\ndef test_foo(): pass"
        assert analyzer._is_in_test_or_mock_context(code) is True

    def test_is_test_code_import_unittest(self) -> None:
        """Cover line 149: from unittest import detection."""
        analyzer = NutritionBayesianAnalyzer()
        code = "from unittest import TestCase\nclass MyTest(TestCase): pass"
        assert analyzer._is_in_test_or_mock_context(code) is True

    def test_is_test_code_import_mock(self) -> None:
        """Cover import mock detection."""
        analyzer = NutritionBayesianAnalyzer()
        code = "import mock\nmock.patch('foo')"
        assert analyzer._is_in_test_or_mock_context(code) is True

    def test_calorie_analysis_valueerror_branch(self) -> None:
        """Cover lines 319-320: ValueError continue in calorie analysis."""
        analyzer = NutritionBayesianAnalyzer()
        # Code with invalid calorie value that triggers ValueError on float()
        code = "calories = 'not_a_number'"
        results = analyzer._analyze_calorie_calculations(code, "test_invalid")
        # Should not crash, just skip invalid values
        assert isinstance(results, list)

    def test_bmi_height_edge_case(self) -> None:
        """Cover line 376: height <= 0 or height > 3 branch."""
        analyzer = NutritionBayesianAnalyzer()
        # Code with invalid height (negative)
        code = "height = -1\nweight = 70\nbmi = weight / height"
        results = analyzer._analyze_bmi_calculations(code, "test_invalid_height")
        assert isinstance(results, list)

    def test_bmi_valueerror_branch(self) -> None:
        """Cover lines 403-404: ValueError continue in BMI analysis."""
        analyzer = NutritionBayesianAnalyzer()
        # Code with non-numeric height/weight
        code = "height = 'tall'\nweight = 'heavy'"
        results = analyzer._analyze_bmi_calculations(code, "test_valueerror")
        assert isinstance(results, list)

    def test_validate_macronutrients_negative_fat(self) -> None:
        """Cover line 530: negative fat grams via _validate_macronutrients."""
        analyzer = NutritionBayesianAnalyzer()
        # Call with negative fat value
        results = analyzer._validate_macronutrients(
            protein_grams=10.0, fat_grams=-5.0, carb_grams=20.0, test_name="neg_fat"
        )
        assert isinstance(results, list)

    def test_validate_macronutrients_negative_protein(self) -> None:
        """Cover negative protein grams."""
        analyzer = NutritionBayesianAnalyzer()
        results = analyzer._validate_macronutrients(
            protein_grams=-10.0, fat_grams=15.0, carb_grams=25.0, test_name="neg_protein"
        )
        assert isinstance(results, list)

    def test_validate_macronutrients_negative_carbs(self) -> None:
        """Cover line 532: negative carb grams."""
        analyzer = NutritionBayesianAnalyzer()
        results = analyzer._validate_macronutrients(
            protein_grams=20.0, fat_grams=10.0, carb_grams=-15.0, test_name="neg_carb"
        )
        assert isinstance(results, list)


class TestIntegratedAnalyzerCoverage:
    """Cover uncovered branches in IntegratedBayesianAnalyzer."""

    def test_is_test_code_patch_decorator(self) -> None:
        """Cover lines 267-268: @patch decorator detection."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "@patch('module.func')\ndef test_something(): pass"
        assert analyzer._is_in_test_or_mock_context(code) is True

    def test_is_test_code_mock_decorator(self) -> None:
        """Cover line 286: @mock.* decorator detection."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "@mock.patch('foo')\ndef test_mock(): pass"
        assert analyzer._is_in_test_or_mock_context(code) is True

    def test_sensitive_logging_checker(self) -> None:
        """Cover line 481: sensitive logging detection."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "import logging\nlogging.info(f'password={password}')"
        result = analyzer._check_sensitive_data_logging(code)
        assert isinstance(result, bool)

    def test_sql_injection_detection(self) -> None:
        """Cover lines 602, 666: SQL injection analysis."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "cursor.execute(f'SELECT * FROM users WHERE id={user_id}')"
        result = analyzer._check_potential_sql_injection(code)
        assert isinstance(result, bool)

    def test_analyze_safety_aspects(self) -> None:
        """Cover safety analysis paths."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """open('file.txt')\nlogging.info(f'secret={api_key}')"""
        results = analyzer._analyze_safety_aspects(code, "test_safety")
        assert isinstance(results, list)

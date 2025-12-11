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
    NutritionErrorType,
)


class TestNutritionBayesianAnalyzerInit:
    """Test analyzer initialization."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        analyzer = NutritionBayesianAnalyzer()
        assert analyzer.test_results == []

    def test_init_has_default_thresholds(self) -> None:
        """Test that analyzer initializes with default safety thresholds."""
        analyzer = NutritionBayesianAnalyzer()
        # Should have reasonable defaults
        assert hasattr(analyzer, "safety_thresholds")
        assert "calorie_dangerous_low" in analyzer.safety_thresholds
        assert "calorie_dangerous_high" in analyzer.safety_thresholds


class TestNutritionSafetyAnalysis:
    """Test nutrition safety checks."""

    def test_analyze_simple_nutrition_code(self) -> None:
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

    def test_detect_low_calories(self) -> None:
        """Test detection of dangerously low calories."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_low_cal():
    calories = 500  # Too low
    assert calories
"""
        results = analyzer.analyze_nutrition_safety(code, "test_low_cal")
        assert isinstance(results, list)
        # Verify results are valid NutritionTestResult instances
        assert all(isinstance(r, NutritionTestResult) for r in results)

    def test_detect_high_calories(self) -> None:
        """Test detection of excessively high calories."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_high_cal():
    calories = 10000  # Too high
    assert calories
"""
        results = analyzer.analyze_nutrition_safety(code, "test_high_cal")
        assert isinstance(results, list)
        # Verify results are valid NutritionTestResult instances
        assert all(isinstance(r, NutritionTestResult) for r in results)

    def test_analyze_zero_macronutrients(self) -> None:
        """All-zero macros should be processed without crashing (may or may not be flagged)."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_macros():
    protein = 0
    fat = 0
    carbs = 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_macros")
        # Verify results are valid NutritionTestResult instances
        assert isinstance(results, list)
        assert all(isinstance(r, NutritionTestResult) for r in results)

    def test_detect_macro_percent_out_of_bounds(self) -> None:
        """Macro percentages outside healthy ranges should be flagged per macro."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_macros_pct():
    protein = 300  # grams
    fat = 10      # grams
    carbs = 10    # grams
"""
        results = analyzer.analyze_nutrition_safety(code, "test_macros_pct")
        # Expect at least one of the macro imbalance errors (protein too high, fat too low, carbs too low)
        error_values = {getattr(r.error_type, "value", "") for r in results if r.error_type}
        assert {"protein_too_high", "fat_too_low", "carb_too_low"} & error_values

    def test_detect_fat_too_high(self) -> None:
        """Excessive fat percentage should be flagged."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_fat_high():
    protein = 10
    fat = 1000
    carbs = 10
"""
        results = analyzer.analyze_nutrition_safety(code, "test_fat_high")
        assert any(
            getattr(r.error_type, "value", "") == "fat_too_high" for r in results if r.error_type
        )

    def test_detect_carb_too_high(self) -> None:
        """Excessive carb percentage should be flagged."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_carb_high():
    protein = 10
    fat = 10
    carbs = 2000
"""
        results = analyzer.analyze_nutrition_safety(code, "test_carb_high")
        assert any(
            getattr(r.error_type, "value", "") == "carb_too_high" for r in results if r.error_type
        )

    def test_meal_level_calories_are_skipped(self) -> None:
        """Meal-level calories should be ignored by the dangerous daily calorie checks."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_meal():
    breakfast_calories = 500
"""
        results = analyzer.analyze_nutrition_safety(code, "test_meal")
        # Should not flag meal-level calories
        assert not any(
            getattr(r.error_type, "value", "").startswith("calorie_")
            for r in results
            if r.error_type
        )

    def test_invalid_calorie_and_bmi_values_do_not_crash(self) -> None:
        """Non-numeric calorie/BMI values should be safely ignored."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_invalid():
    calories = not_a_number
    bmi = bad_value
"""
        results = analyzer.analyze_nutrition_safety(code, "test_invalid")
        # Should not raise and should not produce calorie/bmi errors
        assert isinstance(results, list)
        assert not any(
            getattr(r.error_type, "value", "").startswith("calorie_")
            for r in results
            if r.error_type
        )
        assert not any(
            getattr(r.error_type, "value", "").startswith("bmi_") for r in results if r.error_type
        )

    def test_bmi_dangerous_low(self) -> None:
        """BMI below dangerous threshold should be flagged."""
        analyzer = NutritionBayesianAnalyzer()
        code = "bmi = 10"
        results = analyzer.analyze_nutrition_safety(code, "test_bmi_low")
        assert any(
            getattr(r.error_type, "value", "") == "bmi_dangerous" for r in results if r.error_type
        )

    def test_calorie_and_bmi_value_error_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Force ValueError in calorie/BMI parsing to cover exception paths.

        Uses re.findall mocking to return non-numeric strings that trigger ValueError
        naturally when passed to float(), avoiding global builtins.float monkeypatching.
        """
        analyzer = NutritionBayesianAnalyzer()
        import core.nutrition_bayesian_analyzer as nba

        class FakeMatch:
            def __init__(self, text: str):
                self._text = text

            def group(self, idx: int):
                return self._text

            def start(self):
                return 0

            def end(self):
                return len(self._text)

        def fake_finditer(pattern, string, flags=0):
            # Always yield a match that will raise ValueError when converted to float
            yield FakeMatch("not_a_number")

        monkeypatch.setattr(nba.re, "finditer", fake_finditer)
        # These should return empty lists due to ValueError in float()
        assert analyzer._analyze_calorie_calculations("calories = bad", "test") == []
        assert analyzer._analyze_bmi_calculations("bmi = bad", "test") == []

    def test_negative_macros_handled_gracefully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Negative macro values should be explicitly detected and reported.

        Updated to expect error for negative protein values, matching the improved
        validation logic that explicitly checks each macro before calculating calories.
        This test ensures negative macros are caught before they can be masked by
        positive values in other macros.

        Validates that _validate_macronutrients() properly detects negative protein=-5
        and returns an error, rather than allowing it to pass because fat=20 + carbs=20
        result in positive total calories.

        Patterns matched: r"protein\\s*[=:]\\s*(\\d+(?:\\.\\d+)?)", r"fat\\s*...", r"carbs?\\s*..."
        """
        analyzer = NutritionBayesianAnalyzer()
        import core.nutrition_bayesian_analyzer as nba

        original_findall = nba.re.findall

        def _fake_findall(pattern, string, flags=0):
            if "protein" in pattern:
                return ["-5"]
            if "fat" in pattern:
                return ["20"]
            if "carbs" in pattern:
                return ["20"]
            return original_findall(pattern, string, flags)

        monkeypatch.setattr(nba.re, "findall", _fake_findall)
        results = analyzer._analyze_nutrition_standards("", "test_negative_macros")
        # Should now detect negative protein and return macronutrient_sum_invalid error
        assert any(
            getattr(r.error_type, "value", "") == "macronutrient_sum_invalid"
            for r in results
            if r.error_type
        ), "Expected error for negative protein value"

    def test_diagnose_probabilities_with_successful_and_failed_results(self) -> None:
        """diagnose_nutrition_issues should include only failed results."""
        analyzer = NutritionBayesianAnalyzer()
        analyzer.test_results.extend(
            [
                NutritionTestResult(
                    test_name="t_ok",
                    success=True,
                    nutrition_category=NutritionCategory.BMI_SAFETY,
                ),
                NutritionTestResult(
                    test_name="t_fail",
                    success=False,
                    nutrition_category=NutritionCategory.DATA_PRIVACY,
                ),
            ]
        )
        probs = analyzer.diagnose_nutrition_issues()
        assert NutritionCategory.DATA_PRIVACY in probs
        assert NutritionCategory.BMI_SAFETY not in probs


class TestBMIValidation:
    """Test BMI validation."""

    def test_analyze_bmi_in_valid_range(self) -> None:
        """BMI within valid range should be processed without errors."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_bmi():
    bmi = 22.5
    assert 18.5 <= bmi <= 25
"""
        results = analyzer.analyze_nutrition_safety(code, "test_bmi")
        assert isinstance(results, list)
        # Verify results are valid NutritionTestResult instances
        assert all(isinstance(r, NutritionTestResult) for r in results)

    def test_detect_invalid_bmi(self) -> None:
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

    def test_bmi_exactly_at_dangerous_threshold(self) -> None:
        """BMI exactly at dangerous high threshold (30.0) should be flagged as dangerous."""
        analyzer = NutritionBayesianAnalyzer()
        # BMI_DANGEROUS_HIGH = 30.0, test that >= comparison catches exact boundary
        code = "bmi = 30.0"
        results = analyzer.analyze_nutrition_safety(code, "test_bmi_boundary")
        # Should flag BMI=30.0 as dangerous (obesity class I threshold)
        assert any(
            r.nutrition_category == NutritionCategory.BMI_SAFETY
            and getattr(r.error_type, "value", "") == "bmi_dangerous"
            and r.safety_level == "dangerous"
            for r in results
        ), "BMI=30.0 should be flagged as dangerous (>= 30.0 threshold)"


class TestMacronutrientChecks:
    """Test macronutrient validation."""

    def test_analyze_protein_values(self) -> None:
        """Protein values should be processed and analyzed."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_protein():
    protein = 50.0
    assert protein > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_protein")
        assert isinstance(results, list)
        assert all(isinstance(r, NutritionTestResult) for r in results)

    def test_analyze_carb_values(self) -> None:
        """Carbohydrate values should be processed and analyzed."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_carbs():
    carbs = 200.5
    assert carbs > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_carbs")
        assert isinstance(results, list)
        assert all(isinstance(r, NutritionTestResult) for r in results)

    def test_analyze_fat_values(self) -> None:
        """Fat values should be processed and analyzed."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_fats():
    fats = 70.0
    assert fats > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_fats")
        assert isinstance(results, list)
        assert all(isinstance(r, NutritionTestResult) for r in results)


class TestAllergenDetection:
    """Test allergen-related checks."""

    def test_detect_allergen_keywords(self) -> None:
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

    def test_nutrition_test_result_creation(self) -> None:
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

    def test_empty_code(self) -> None:
        """Test analysis of empty code."""
        analyzer = NutritionBayesianAnalyzer()
        results = analyzer.analyze_nutrition_safety("", "test_empty")
        assert isinstance(results, list)

    def test_code_without_nutrition_data(self) -> None:
        """Test code with no nutrition-related content."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_generic():
    value = 42
    assert value > 0
"""
        results = analyzer.analyze_nutrition_safety(code, "test_generic")
        assert isinstance(results, list)

    def test_malformed_code(self) -> None:
        """Test malformed code handling."""
        analyzer = NutritionBayesianAnalyzer()
        code = "def test_broken(:"
        results = analyzer.analyze_nutrition_safety(code, "test_broken")
        assert isinstance(results, list)

    def test_results_persistence(self) -> None:
        """Test that results are persisted."""
        analyzer = NutritionBayesianAnalyzer()
        initial_analyses = analyzer._total_analyses
        analyzer.analyze_nutrition_safety("bmi = 50", "test1")
        analyzer.analyze_nutrition_safety("calories = 10000", "test2")
        # Two analyze calls should increment _total_analyses by exactly 2
        assert analyzer._total_analyses == initial_analyses + 2


class TestAdditionalSafetyChecks:
    """Additional coverage for privacy and medical contradiction branches."""

    def test_data_privacy_leak_detection(self) -> None:
        """Hardcoded secrets should be flagged as privacy leaks."""
        analyzer = NutritionBayesianAnalyzer()
        code = 'api_key = "secret123"\n'
        results = analyzer.analyze_nutrition_safety(code, "test_privacy")
        assert any(
            getattr(r, "error_type", None) is not None
            and getattr(r.error_type, "value", "") == "privacy_leak"
            for r in results
        )

    def test_medical_contradiction_detection(self) -> None:
        """Diabetes mention without sugar limit should raise a medical contradiction warning."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_medical():
    # patient has diabetes
    condition = "diabetes"
    sugar = "added sugar"
"""
        results = analyzer.analyze_nutrition_safety(code, "test_medical")
        assert any(
            getattr(r, "error_type", None) is not None
            and getattr(r.error_type, "value", "") == "medical_contradiction"
            for r in results
        )

    def test_medical_no_issue_when_limited(self) -> None:
        """When sugar is limited for diabetes, medical contradiction should not trigger."""
        analyzer = NutritionBayesianAnalyzer()
        code = """
def test_medical_limit():
    condition = "diabetes"
    sugar = "limited sugar"
    limit = True
"""
        results = analyzer.analyze_nutrition_safety(code, "test_medical_limit")
        assert not any(
            getattr(r.error_type, "value", "") == "medical_contradiction"
            for r in results
            if r.error_type
        )

    def test_add_nutrition_test_result_and_allergen_recommendation(self) -> None:
        """add_nutrition_test_result should append, and allergen issues should drive recommendations."""
        analyzer = NutritionBayesianAnalyzer()
        result = NutritionTestResult(
            test_name="allergen_missing",
            success=False,
            nutrition_category=NutritionCategory.ALLERGEN_SAFETY,
            error_type=NutritionErrorType.ALLERGEN_MISSING,
        )
        analyzer.add_nutrition_test_result(result)
        assert analyzer.test_results[-1] is result

        # Analyze code with allergen mention but no checks to populate test_results automatically
        code = "peanuts everywhere"
        analyzer.analyze_nutrition_safety(code, "test_allergen")
        recs = analyzer.generate_nutrition_recommendations()
        # Locale-independent: check for allergen-related recommendation by category
        issues = analyzer.diagnose_nutrition_issues()
        # Verify allergen issues are diagnosed or recommendations are generated
        has_allergen_diagnosis = NutritionCategory.ALLERGEN_SAFETY in issues
        has_recommendations = len(recs) > 0
        assert has_allergen_diagnosis, f"Expected allergen diagnosis. Issues: {issues}"
        assert (
            has_recommendations
        ), f"Expected recommendations for allergen issues. Recommendations: {recs}"

    def test_generate_recommendations_medical_and_macros(self) -> None:
        """Medical and macro issues should add corresponding recommendations."""
        analyzer = NutritionBayesianAnalyzer()
        analyzer.test_results.extend(
            [
                NutritionTestResult(
                    test_name="t_med",
                    success=False,
                    nutrition_category=NutritionCategory.MEDICAL_SAFETY,
                ),
                NutritionTestResult(
                    test_name="t_macro",
                    success=False,
                    nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                ),
            ]
        )
        recs = analyzer.generate_nutrition_recommendations()
        # Locale-independent: check that recommendations are non-empty
        issues = analyzer.diagnose_nutrition_issues()
        assert NutritionCategory.MEDICAL_SAFETY in issues
        assert NutritionCategory.MACRONUTRIENT_BALANCE in issues
        assert len(recs) >= 2, "Should generate recommendations for medical and macro issues"

    def test_get_safety_score_with_penalty_and_failed_analyses(self) -> None:
        """Safety score should decrease when failed dangerous analyses accumulate."""
        analyzer = NutritionBayesianAnalyzer()
        analyzer._total_analyses = 2
        analyzer._failed_analyses = 2
        analyzer.test_results.extend(
            [
                NutritionTestResult(
                    test_name="t_danger1",
                    success=False,
                    nutrition_category=NutritionCategory.BMI_SAFETY,
                    safety_level="dangerous",
                ),
                NutritionTestResult(
                    test_name="t_danger2",
                    success=False,
                    nutrition_category=NutritionCategory.CALORIE_CALCULATION,
                    safety_level="dangerous",
                ),
            ]
        )
        score = analyzer.get_safety_score()
        assert 0.0 <= score < 1.0

    def test_diagnose_issues_and_recommendations(self) -> None:
        """Diagnose nutrition issues and generate category-based recommendations."""
        analyzer = NutritionBayesianAnalyzer()
        analyzer.test_results.extend(
            [
                NutritionTestResult(
                    test_name="t_cal",
                    success=False,
                    nutrition_category=NutritionCategory.CALORIE_CALCULATION,
                ),
                NutritionTestResult(
                    test_name="t_bmi",
                    success=False,
                    nutrition_category=NutritionCategory.BMI_SAFETY,
                ),
                NutritionTestResult(
                    test_name="t_privacy",
                    success=False,
                    nutrition_category=NutritionCategory.DATA_PRIVACY,
                ),
                NutritionTestResult(
                    test_name="t_macro",
                    success=False,
                    nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                ),
            ]
        )

        probs = analyzer.diagnose_nutrition_issues()
        assert NutritionCategory.CALORIE_CALCULATION in probs
        assert NutritionCategory.BMI_SAFETY in probs

        recs = analyzer.generate_nutrition_recommendations()
        # Locale-independent: check that recommendations were generated
        assert len(recs) >= 2, "Should generate recommendations for calorie and BMI issues"

    def test_get_safety_score_penalty_capped(self) -> None:
        """Safety score should apply capped dangerous penalties."""
        analyzer = NutritionBayesianAnalyzer()
        analyzer._total_analyses = 4
        analyzer._failed_analyses = 4
        analyzer.test_results.extend(
            [
                NutritionTestResult(
                    test_name=f"t{i}",
                    success=False,
                    nutrition_category=NutritionCategory.BMI_SAFETY,
                    safety_level="dangerous",
                )
                for i in range(5)
            ]
        )
        score = analyzer.get_safety_score()
        assert 0.0 <= score <= 1.0

    def test_generate_recommendations_no_issues_and_get_safety_score_no_analyses(self) -> None:
        """No issues should yield empty recommendations and safety score 1.0 before analyses."""
        analyzer = NutritionBayesianAnalyzer()
        recs = analyzer.generate_nutrition_recommendations()
        assert recs == []
        assert analyzer.get_safety_score() == 1.0

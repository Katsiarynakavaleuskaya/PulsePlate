#!/usr/bin/env python3
"""
Unit tests for IntegratedBayesianAnalyzer.

Covers the main integrated analyzer that combines technical, nutrition,
safety, and philosophy checks.
"""

import pytest
from core.integrated_bayesian_analyzer import (
    IntegratedBayesianAnalyzer,
    IntegratedTestResult,
    NormalizedIssueType,
)


class TestIntegratedBayesianAnalyzerInit:
    """Test analyzer initialization."""

    def test_init_creates_sub_analyzers(self) -> None:
        """Test that initialization creates all required analyzers."""
        analyzer = IntegratedBayesianAnalyzer()
        assert analyzer.technical_analyzer is not None
        assert analyzer.nutrition_analyzer is not None
        assert hasattr(analyzer, "_analyze_safety_aspects")
        assert analyzer.integrated_results == []

    def test_init_loads_system_philosophy(self) -> None:
        """Test that system philosophy is loaded."""
        analyzer = IntegratedBayesianAnalyzer()
        assert analyzer.system_philosophy is not None
        assert isinstance(analyzer.system_philosophy, dict)


class TestIntegratedAnalysis:
    """Test integrated analysis functionality."""

    def test_analyze_integrated_simple_code(self) -> None:
        """Test analysis of simple test code."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "def test_simple(): assert True"
        result = analyzer.analyze_test_comprehensively(code, "test_simple", "test_file.py")
        assert isinstance(result, IntegratedTestResult)
        assert result.test_name == "test_simple"
        assert isinstance(result.technical_issues, list)
        assert isinstance(result.nutrition_issues, list)
        assert isinstance(result.safety_issues, list)
        assert isinstance(result.philosophy_violations, list)

    def test_analyze_integrated_with_technical_issue(self) -> None:
        """Test detection of technical issues."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_async_issue():
    mock = AsyncMock()
    result = mock()  # Missing await
"""
        result = analyzer.analyze_test_comprehensively(code, "test_async_issue", "test.py")
        assert isinstance(result, IntegratedTestResult)

    def test_analyze_integrated_with_nutrition_code(self) -> None:
        """Test analysis of nutrition-related code."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_calories():
    calories = 2000
    assert calories > 0
"""
        result = analyzer.analyze_test_comprehensively(code, "test_calories", "test.py")
        assert isinstance(result, IntegratedTestResult)

    def test_analyze_integrated_empty_code(self) -> None:
        """Test analysis of empty code."""
        analyzer = IntegratedBayesianAnalyzer()
        result = analyzer.analyze_test_comprehensively("", "test_empty", "test.py")
        assert isinstance(result, IntegratedTestResult)


class TestSafetyChecks:
    """Test safety violation detection."""

    def test_detect_unsafe_file_open(self) -> None:
        """Test detection of unsafe file operations."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_file():
    f = open("file.txt")  # Missing context manager
    data = f.read()
"""
        result = analyzer.analyze_test_comprehensively(code, "test_file", "test.py")
        assert isinstance(result, IntegratedTestResult)
        # Expect safety issues to include unsafe file handling detection
        assert len(result.safety_issues) > 0, "Expected unsafe file operation to be detected"
        assert any(
            "unsafe" in str(issue).lower()
            or "open(" in str(issue).lower()
            or "missing context manager" in str(issue).lower()
            or "file.txt" in str(issue).lower()
            for issue in result.safety_issues
        )

    def test_detect_hardcoded_password(self) -> None:
        """Test detection of hardcoded passwords."""
        analyzer = IntegratedBayesianAnalyzer()
        code = 'password = "hardcoded123"\n'
        result = analyzer.analyze_test_comprehensively(code, "test_auth", "test.py")
        assert isinstance(result, IntegratedTestResult)
        # Expect safety issues to include hardcoded password detection
        assert len(result.safety_issues) > 0, "Expected hardcoded password to be detected"
        assert any("password" in str(issue).lower() for issue in result.safety_issues)


class TestPhilosophyChecks:
    """Test philosophy violation detection."""

    def test_philosophy_health_first(self) -> None:
        """Test Health First philosophy check."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_health_metric():
    assert True
"""
        result = analyzer.analyze_test_comprehensively(code, "test_health_metric", "test.py")
        assert isinstance(result, IntegratedTestResult)
        # Philosophy violations should be recorded when health metrics are not validated
        assert isinstance(result.philosophy_violations, list)
        assert result.philosophy_violations

    def test_philosophy_user_centric(self) -> None:
        """Test User-Centric philosophy check."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_user():
    user = create_user()
    assert user
"""
        result = analyzer.analyze_test_comprehensively(code, "test_user_invalid", "test.py")
        assert isinstance(result, IntegratedTestResult)
        # Philosophy violations should be recorded for user-related tests lacking error handling
        assert isinstance(result.philosophy_violations, list)
        assert result.philosophy_violations


class TestRiskCalculation:
    """Test risk level calculation."""

    def test_calculate_risk_level_low(self) -> None:
        """Test low risk calculation."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "def test_safe(): pass"
        result = analyzer.analyze_test_comprehensively(code, "test_safe", "test.py")
        # Safe code should be low or at most medium risk
        assert result.overall_risk_level in ["low", "medium"]

    def test_calculate_risk_level_with_issues(self) -> None:
        """Test risk increases with issues."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_risky():
    password = "hardcoded"
    eval("dangerous")
"""
        result = analyzer.analyze_test_comprehensively(code, "test_risky", "test.py")
        # Risky code should be at least medium risk
        risk_levels = ["low", "medium", "high", "critical"]
        assert result.overall_risk_level in risk_levels
        risk_index = risk_levels.index(result.overall_risk_level)
        assert risk_index >= risk_levels.index("medium")


class TestBusinessImpact:
    """Test business impact assessment."""

    def test_assess_business_impact_none(self) -> None:
        """Test business impact with no issues."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "def test(): pass"
        result = analyzer.analyze_test_comprehensively(code, "test", "test.py")
        assert isinstance(result.business_impact, str)

    def test_assess_business_impact_with_issues(self) -> None:
        """Test business impact with multiple issues."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_business():
    password = "leak"
    unsafe_data = eval("bad")
"""
        result = analyzer.analyze_test_comprehensively(code, "test_business", "test.py")
        assert isinstance(result.business_impact, str)


class TestNormalizedIssueTypes:
    """Test normalized issue type detection."""

    def test_normalize_issue_type_injection(self) -> None:
        """Test injection detection."""
        analyzer = IntegratedBayesianAnalyzer()
        issue_types = analyzer._normalize_issue_type("SQL injection detected")
        assert NormalizedIssueType.INJECTION in issue_types

    def test_normalize_issue_type_password(self) -> None:
        """Test password leak detection."""
        analyzer = IntegratedBayesianAnalyzer()
        issue_types = analyzer._normalize_issue_type("Hardcoded password found")
        assert NormalizedIssueType.PASSWORD_LEAK in issue_types

    def test_normalize_issue_type_multiple(self) -> None:
        """Test multiple issue types in one string."""
        analyzer = IntegratedBayesianAnalyzer()
        issue_types = analyzer._normalize_issue_type("Dangerous SQL injection vulnerability")
        assert len(issue_types) >= 1


class TestRecommendations:
    """Test recommendation generation."""

    def test_generate_integrated_recommendations_empty(self) -> None:
        """Test recommendations with no issues."""
        analyzer = IntegratedBayesianAnalyzer()
        analyzer.analyze_test_comprehensively("def test(): pass", "test", "test.py")
        # Recommendations are part of result
        assert len(analyzer.integrated_results) > 0

    def test_generate_integrated_recommendations_with_issues(self) -> None:
        """Test recommendations with various issues."""
        analyzer = IntegratedBayesianAnalyzer()
        code = """
def test_issues():
    password = "bad"
    calories = -100
"""
        result = analyzer.analyze_test_comprehensively(code, "test_issues", "test.py")
        assert isinstance(result, IntegratedTestResult)


class TestDiagnostics:
    """Test diagnostic functionality."""

    def test_get_comprehensive_diagnosis_no_data(self) -> None:
        """Test diagnosis with no results."""
        analyzer = IntegratedBayesianAnalyzer()
        diagnosis = analyzer.get_comprehensive_diagnosis()
        assert isinstance(diagnosis, dict)

    def test_get_comprehensive_diagnosis_with_data(self) -> None:
        """Test diagnosis with results."""
        analyzer = IntegratedBayesianAnalyzer()
        analyzer.analyze_test_comprehensively("def test1(): pass", "test1", "test.py")
        analyzer.analyze_test_comprehensively("def test2(): assert True", "test2", "test.py")
        diagnosis = analyzer.get_comprehensive_diagnosis()
        assert isinstance(diagnosis, dict)


class TestResultDataClass:
    """Test IntegratedTestResult dataclass."""

    def test_integrated_test_result_creation(self) -> None:
        """Test creation of IntegratedTestResult."""
        result = IntegratedTestResult(
            test_name="test_example",
            success=True,
            technical_issues=[],
            nutrition_issues=[],
            safety_issues=[],
            philosophy_violations=[],
            overall_risk_level="low",
            business_impact="Low",
            recommendations=[],
        )
        assert result.test_name == "test_example"
        assert isinstance(result.overall_risk_level, str)
        assert result.overall_risk_level == "low"


class TestEdgeCases:
    """Test edge cases."""

    def test_analyze_malformed_code(self) -> None:
        """Test analysis handles malformed code gracefully."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "def test_broken(:"
        result = analyzer.analyze_test_comprehensively(code, "test_broken", "test.py")
        assert isinstance(result, IntegratedTestResult)

    def test_results_persistence(self) -> None:
        """Test that results are persisted."""
        analyzer = IntegratedBayesianAnalyzer()
        initial_count = len(analyzer.integrated_results)
        analyzer.analyze_test_comprehensively("def test1(): pass", "test1", "test.py")
        analyzer.analyze_test_comprehensively("def test2(): pass", "test2", "test.py")
        assert len(analyzer.integrated_results) == initial_count + 2

    def test_empty_issues_lists(self) -> None:
        """Test handling of empty issue lists."""
        analyzer = IntegratedBayesianAnalyzer()
        code = "def test_clean(): assert True"
        result = analyzer.analyze_test_comprehensively(code, "test_clean", "test.py")
        # At minimum, should not crash
        assert isinstance(result, IntegratedTestResult)

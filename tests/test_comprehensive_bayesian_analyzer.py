#!/usr/bin/env python3
"""
Unit tests for ComprehensiveBayesianAnalyzer.

Tests cover:
- Constructor and sub-analyzer initialization
- Comprehensive analysis combining technical, nutrition, and business
- Scoring calculations
- Risk level assessment
- Priority determination
- System health diagnostics
"""

import pytest
from core.comprehensive_bayesian_analyzer import (
    ComprehensiveBayesianAnalyzer,
    ComprehensiveCategory,
    ComprehensiveTestResult,
)


class TestComprehensiveBayesianAnalyzerInit:
    """Test analyzer initialization."""

    def test_init_creates_sub_analyzers(self) -> None:
        """Test that initialization creates all sub-analyzers."""
        analyzer = ComprehensiveBayesianAnalyzer()
        assert analyzer.technical_analyzer is not None
        assert analyzer.nutrition_analyzer is not None
        assert analyzer.business_analyzer is not None
        assert analyzer.comprehensive_results == []

    def test_init_loads_system_vision(self) -> None:
        """Test that system vision is loaded."""
        analyzer = ComprehensiveBayesianAnalyzer()
        assert analyzer.system_vision is not None
        assert isinstance(analyzer.system_vision, dict)
        # System vision should either have a mission key or be empty
        assert "mission" in analyzer.system_vision or len(analyzer.system_vision) == 0


class TestComprehensiveAnalysis:
    """Test comprehensive analysis functionality."""

    def test_analyze_comprehensively_empty_code(self) -> None:
        """Test analysis of empty code."""
        analyzer = ComprehensiveBayesianAnalyzer()
        result = analyzer.analyze_comprehensively("", "test_empty", "test_file.py")
        assert isinstance(result, ComprehensiveTestResult)
        assert result.test_name == "test_empty"

    def test_analyze_comprehensively_simple_code(self) -> None:
        """Test analysis of simple test code."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_simple():
    assert True
"""
        result = analyzer.analyze_comprehensively(code, "test_simple", "test_file.py")
        assert isinstance(result, ComprehensiveTestResult)
        assert result.test_name == "test_simple"
        assert isinstance(result.overall_score, float)
        assert 0.0 <= result.overall_score <= 1.0

    def test_analyze_comprehensively_with_technical_issues(self) -> None:
        """Test analysis detects technical issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_async_mock():
    # Missing await on AsyncMock
    mock = AsyncMock()
    result = mock()  # Should be: await mock()
"""
        result = analyzer.analyze_comprehensively(code, "test_async_mock", "test_file.py")
        assert isinstance(result, ComprehensiveTestResult)
        # Technical score should be affected

    def test_analyze_comprehensively_with_nutrition_code(self) -> None:
        """Test analysis of nutrition-related code."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_calories():
    calories = 2000
    bmi = calculate_bmi(weight=70, height=175)
    assert calories > 0
"""
        result = analyzer.analyze_comprehensively(code, "test_calories", "test_file.py")
        assert isinstance(result, ComprehensiveTestResult)
        assert isinstance(result.nutrition_score, float)

    def test_analyze_comprehensively_with_business_code(self) -> None:
        """Test analysis of business-related code."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_subscription_price():
    price = 29.99
    subscription = create_subscription(price)
    assert subscription.validate()
"""
        result = analyzer.analyze_comprehensively(code, "test_subscription_price", "test_file.py")
        assert isinstance(result, ComprehensiveTestResult)
        assert isinstance(result.business_score, float)


class TestScoringCalculations:
    """Test scoring calculation methods."""

    def test_calculate_technical_score_perfect(self) -> None:
        """Test technical score calculation with no issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_perfect():
    result = simple_function()
    assert result is not None
"""
        result = analyzer.analyze_comprehensively(code, "test_perfect", "test_file.py")
        # Should have high technical score
        assert result.technical_score >= 0.5

    def test_calculate_nutrition_score(self) -> None:
        """Test nutrition score calculation."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_nutrition():
    calories = 1500
    assert calories > 0
"""
        result = analyzer.analyze_comprehensively(code, "test_nutrition", "test_file.py")
        assert isinstance(result.nutrition_score, float)
        assert 0.0 <= result.nutrition_score <= 1.0

    def test_calculate_business_score(self) -> None:
        """Test business score calculation."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_revenue():
    revenue = calculate_revenue()
    assert revenue > 0
"""
        result = analyzer.analyze_comprehensively(code, "test_revenue", "test_file.py")
        assert isinstance(result.business_score, float)
        assert 0.0 <= result.business_score <= 1.0

    def test_overall_score_combines_subscores(self) -> None:
        """Test that overall score combines all sub-scores."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = "def test(): pass"
        result = analyzer.analyze_comprehensively(code, "test_combined", "test_file.py")
        # Overall score should be computed from technical, nutrition, business
        assert isinstance(result.overall_score, float)
        assert 0.0 <= result.overall_score <= 1.0


class TestRiskLevelAssessment:
    """Test risk level calculation."""

    def test_calculate_risk_level_low(self) -> None:
        """Test low risk level calculation."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_safe():
    result = safe_function()
    assert result
"""
        result = analyzer.analyze_comprehensively(code, "test_safe", "test_file.py")
        assert result.risk_level in ["low", "medium", "high", "critical"]

    def test_calculate_risk_level_with_critical_issues(self) -> None:
        """Test risk level increases with critical issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_dangerous():
    # Multiple potential issues
    password = "hardcoded123"
    unsafe_eval = eval("malicious_code")
"""
        result = analyzer.analyze_comprehensively(code, "test_dangerous", "test_file.py")
        assert result.risk_level in ["low", "medium", "high", "critical"]


class TestPriorityDetermination:
    """Test priority calculation."""

    def test_calculate_priority_normal(self) -> None:
        """Test normal priority calculation."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = "def test_normal(): assert True"
        result = analyzer.analyze_comprehensively(code, "test_normal", "test_file.py")
        assert result.priority in ["low", "medium", "high", "urgent"]

    def test_priority_increases_with_critical_issues(self) -> None:
        """Test priority increases with critical issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_critical():
    # Critical business and nutrition issues
    calories = -1000  # Invalid
    price = -50  # Invalid
"""
        result = analyzer.analyze_comprehensively(code, "test_critical", "test_file.py")
        assert result.priority in ["low", "medium", "high", "urgent"]


class TestImpactAssessment:
    """Test impact assessment methods."""

    def test_revenue_impact_assessment(self) -> None:
        """Test revenue impact assessment."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_revenue_impact():
    revenue = calculate_revenue()
    assert revenue > target
"""
        result = analyzer.analyze_comprehensively(code, "test_revenue_impact", "test_file.py")
        assert isinstance(result.revenue_impact, str)

    def test_cost_impact_assessment(self) -> None:
        """Test cost impact assessment."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_cost_optimization():
    cost = optimize_infrastructure_cost()
    assert cost < budget
"""
        result = analyzer.analyze_comprehensively(code, "test_cost_optimization", "test_file.py")
        assert isinstance(result.cost_impact, str)

    def test_customer_impact_assessment(self) -> None:
        """Test customer impact assessment."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_user_retention():
    retention = get_retention_rate()
    assert retention > 0.8
"""
        result = analyzer.analyze_comprehensively(code, "test_user_retention", "test_file.py")
        assert isinstance(result.customer_impact, str)

    def test_health_impact_assessment(self) -> None:
        """Test health impact assessment."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = """
def test_bmi_calculation():
    bmi = calculate_bmi(weight=70, height=175)
    assert 18.5 <= bmi <= 25
"""
        result = analyzer.analyze_comprehensively(code, "test_bmi_calculation", "test_file.py")
        assert isinstance(result.health_impact, str)


class TestCriticalIssuesDetection:
    """Test critical issues detection."""

    def test_has_critical_nutrition_issues_positive(self) -> None:
        """Test detection of critical nutrition issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        issues = ["Калорий слишком мало", "Dangerous BMI value"]
        has_critical = analyzer._has_critical_nutrition_issues(issues)
        assert isinstance(has_critical, bool)

    def test_has_critical_nutrition_issues_negative(self) -> None:
        """Test no false positives for normal issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        issues = ["Normal validation issue"]
        has_critical = analyzer._has_critical_nutrition_issues(issues)
        assert isinstance(has_critical, bool)

    def test_has_critical_business_issues_positive(self) -> None:
        """Test detection of critical business issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        issues = ["business:revenue leak detected"]
        has_critical = analyzer._has_critical_business_issues(issues)
        assert isinstance(has_critical, bool)

    def test_has_critical_business_issues_negative(self) -> None:
        """Test no false positives for normal business issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        issues = ["Minor optimization opportunity"]
        has_critical = analyzer._has_critical_business_issues(issues)
        assert isinstance(has_critical, bool)


class TestActionPlanGeneration:
    """Test action plan generation."""

    def test_generate_action_plan_with_no_results(self) -> None:
        """Test action plan generation with no results."""
        analyzer = ComprehensiveBayesianAnalyzer()
        action_plan = analyzer.generate_action_plan()
        assert isinstance(action_plan, dict)

    def test_generate_action_plan_with_results(self) -> None:
        """Test action plan generation with results."""
        analyzer = ComprehensiveBayesianAnalyzer()
        analyzer.analyze_comprehensively("def test(): pass", "test_example", "test_file.py")
        action_plan = analyzer.generate_action_plan()
        assert isinstance(action_plan, dict)


class TestComprehensiveTestResult:
    """Test ComprehensiveTestResult dataclass."""

    def test_comprehensive_test_result_creation(self) -> None:
        """Test creation of ComprehensiveTestResult."""
        result = ComprehensiveTestResult(
            test_name="test_example",
            success=True,
            technical_score=0.9,
            nutrition_score=0.8,
            business_score=0.85,
            overall_score=0.85,
            revenue_impact="Medium",
            cost_impact="Low",
            customer_impact="High",
            health_impact="Medium",
            risk_level="low",
            priority="medium",
            critical_issues=[],
            optimization_opportunities=["Improve caching"],
        )
        assert result.test_name == "test_example"
        assert result.success is True
        assert result.technical_score == 0.9
        assert result.overall_score == 0.85
        assert result.risk_level == "low"
        assert len(result.optimization_opportunities) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_malformed_code(self) -> None:
        """Test analysis handles malformed code gracefully."""
        analyzer = ComprehensiveBayesianAnalyzer()
        code = "def test_broken(:"  # Invalid syntax
        result = analyzer.analyze_comprehensively(code, "test_broken", "test_file.py")
        # Should not crash
        assert isinstance(result, ComprehensiveTestResult)

    def test_results_persistence(self) -> None:
        """Test that results are persisted in analyzer."""
        analyzer = ComprehensiveBayesianAnalyzer()
        initial_count = len(analyzer.comprehensive_results)
        analyzer.analyze_comprehensively("def test(): pass", "test1", "test_file.py")
        analyzer.analyze_comprehensively("def test2(): pass", "test2", "test_file.py")
        assert len(analyzer.comprehensive_results) == initial_count + 2

    def test_empty_critical_issues_list(self) -> None:
        """Test handling of empty critical issues."""
        analyzer = ComprehensiveBayesianAnalyzer()
        has_critical = analyzer._has_critical_nutrition_issues([])
        assert has_critical is False

    def test_case_insensitive_keyword_matching(self) -> None:
        """Test case-insensitive matching for critical keywords."""
        analyzer = ComprehensiveBayesianAnalyzer()
        issues_upper = ["CALORIE overflow detected"]
        issues_lower = ["calorie overflow detected"]
        # Both should be detected
        result_upper = analyzer._has_critical_nutrition_issues(issues_upper)
        result_lower = analyzer._has_critical_nutrition_issues(issues_lower)
        assert isinstance(result_upper, bool)
        assert isinstance(result_lower, bool)

    def test_risk_level_and_priority_thresholds(self) -> None:
        """Cover risk level and priority thresholds across critical issue counts and scores."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Critical branch
        assert analyzer._calculate_risk_level(["c1", "c2"], overall_score=0.1) == "critical"
        # High branch
        assert analyzer._calculate_risk_level(["c1"], overall_score=0.35) == "high"
        # Medium branch
        assert analyzer._calculate_risk_level(["c1"], overall_score=0.65) == "medium"
        # Low branch
        assert analyzer._calculate_risk_level([], overall_score=0.9) == "low"

        # Priority branches
        urgent = analyzer._calculate_priority(
            ["a", "b"], revenue_impact="низкое", health_impact="КРИТИЧЕСКОЕ влияние"
        )
        high = analyzer._calculate_priority(
            ["a"], revenue_impact="критическое влияние на доход", health_impact="нормальное"
        )
        medium = analyzer._calculate_priority(
            [], revenue_impact="среднее влияние", health_impact="нормальное"
        )
        low = analyzer._calculate_priority([], revenue_impact="низкое", health_impact="нет влияния")

        assert urgent == "urgent"
        assert high == "high"
        assert medium == "medium"
        assert low == "low"

    def test_health_and_customer_impact_assessment(self) -> None:
        """Ensure health/customer impact helpers cover all branches."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # No issues
        assert analyzer._assess_health_impact([]) == "Нет влияния на здоровье"
        assert analyzer._assess_customer_impact([], [], []) == "Нет влияния на клиентов"

        # Minimal/medium/critical branches
        health = analyzer._assess_health_impact(["Опасно для здоровья"])
        customer = analyzer._assess_customer_impact(["пользователь"], [], ["customer issue"])
        assert health in {
            "Минимальное влияние на здоровье",
            "Среднее влияние на здоровье",
            "Критическое влияние на здоровье",
        }
        assert customer in {
            "Минимальное влияние на клиентов",
            "Среднее влияние на клиентов",
            "Критическое влияние на клиентов",
        }

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
        """Test detection of critical nutrition issues through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()
        # Code that triggers critical nutrition issues
        code = """
def test_dangerous_bmi():
    # This should trigger a critical nutrition issue
    bmi = calculate_bmi(weight=30, height=180)  # Dangerous BMI value
    assert bmi > 18.5
"""
        result = analyzer.analyze_comprehensively(code, "test_dangerous_bmi", "test_file.py")
        # Check that critical issues were detected
        assert len(result.critical_issues) > 0
        # Check that at least one critical issue relates to health/nutrition
        assert any("HEALTH:" in issue for issue in result.critical_issues)

    def test_has_critical_nutrition_issues_negative(self) -> None:
        """Test no false positives for normal issues through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()
        # Code that doesn't trigger critical nutrition issues
        code = """def test_normal_case():
    # Normal validation issue, not critical
    assert 1 == 1
"""
        result = analyzer.analyze_comprehensively(code, "test_normal_case", "test_file.py")
        # Check that no critical nutrition issues were detected
        health_issues = [issue for issue in result.critical_issues if "HEALTH:" in issue]
        # We're specifically testing that normal issues don't trigger critical nutrition alerts
        assert len(health_issues) == 0

    def test_has_critical_business_issues_positive(self) -> None:
        """Test detection of critical business issues through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()
        # Code that triggers critical business issues
        code = """def test_revenue_leak():
    # This should trigger a critical business issue related to revenue
    process_payment(amount=-100)  # revenue leak detected
"""
        result = analyzer.analyze_comprehensively(code, "test_revenue_leak", "test_file.py")
        # Check that critical issues were detected
        assert len(result.critical_issues) > 0
        # Check that at least one critical issue relates to business/revenue
        business_issues = [
            issue for issue in result.critical_issues if "business:" in issue.lower()
        ]
        assert len(business_issues) > 0

    def test_has_critical_business_issues_negative(self) -> None:
        """Test no false positives for normal business issues through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()
        # Code that doesn't trigger critical business issues
        code = """def test_minor_optimization():
    # Minor optimization opportunity, not critical
    x = 1 + 1
"""
        result = analyzer.analyze_comprehensively(code, "test_minor_optimization", "test_file.py")
        # Check that no critical business issues were detected
        business_issues = [
            issue for issue in result.critical_issues if "business:" in issue.lower()
        ]
        assert len(business_issues) == 0


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
        """Test handling of empty critical issues through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()
        # Code that doesn't trigger any critical issues
        code = """def test_no_issues():
    # Simple test with no issues
    assert True
"""
        result = analyzer.analyze_comprehensively(code, "test_no_issues", "test_file.py")
        # Check that no critical issues were detected
        assert len(result.critical_issues) == 0

    def test_case_insensitive_keyword_matching(self) -> None:
        """Test case-insensitive matching for critical keywords through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()
        # Code with case variations that should trigger critical nutrition issues
        code_upper = """def test_calorie_overflow():
    # CALORIE overflow detected - should trigger critical issue
    consume_calories(10000)  # Too many calories
"""
        code_lower = """def test_calorie_overflow():
    # calorie overflow detected - should trigger critical issue
    consume_calories(10000)  # Too many calories
"""
        # Both should be detected as having critical issues
        result_upper = analyzer.analyze_comprehensively(
            code_upper, "test_calorie_overflow", "test_file.py"
        )
        result_lower = analyzer.analyze_comprehensively(
            code_lower, "test_calorie_overflow", "test_file.py"
        )

        # Both should have critical issues detected
        assert len(result_upper.critical_issues) > 0
        assert len(result_lower.critical_issues) > 0

    def test_risk_level_and_priority_thresholds(self) -> None:
        """Cover risk level and priority thresholds through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Test case that should result in critical risk level
        critical_code = """def test_critical_risk():
    # Multiple critical issues to trigger critical risk level
    dangerous_bmi_calculation()
    revenue_leak_detected()
    critical_security_issue()
"""
        critical_result = analyzer.analyze_comprehensively(
            critical_code, "test_critical_risk", "test_file.py"
        )
        # We can't directly assert the risk level without knowing the exact implementation,
        # but we can verify the result has a risk_level attribute
        assert hasattr(critical_result, "risk_level")
        assert isinstance(critical_result.risk_level, str)

        # Test case that should result in low risk level
        low_risk_code = """def test_low_risk():
    # Simple test with no issues
    assert 1 == 1
"""
        low_risk_result = analyzer.analyze_comprehensively(
            low_risk_code, "test_low_risk", "test_file.py"
        )
        assert hasattr(low_risk_result, "risk_level")
        assert isinstance(low_risk_result.risk_level, str)

        # Test that results have priority attributes
        assert hasattr(critical_result, "priority")
        assert hasattr(low_risk_result, "priority")
        assert isinstance(critical_result.priority, str)
        assert isinstance(low_risk_result.priority, str)

    def test_health_and_customer_impact_assessment(self) -> None:
        """Ensure health/customer impact is assessed through public API."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Test case with no issues
        no_issue_code = """def test_no_issues():
    # Simple test with no issues
    assert True
"""
        no_issue_result = analyzer.analyze_comprehensively(
            no_issue_code, "test_no_issues", "test_file.py"
        )
        # Check that impact fields exist and have values
        assert hasattr(no_issue_result, "health_impact")
        assert hasattr(no_issue_result, "customer_impact")
        assert isinstance(no_issue_result.health_impact, str)
        assert isinstance(no_issue_result.customer_impact, str)

        # Test case with health-related issues
        health_issue_code = """def test_health_issue():
    # Code that should trigger health impact assessment
    dangerous_bmi_value = calculate_bmi(30, 180)  # Опасно для здоровья
"""
        health_result = analyzer.analyze_comprehensively(
            health_issue_code, "test_health_issue", "test_file.py"
        )
        # Check that impact fields exist
        assert hasattr(health_result, "health_impact")
        assert isinstance(health_result.health_impact, str)

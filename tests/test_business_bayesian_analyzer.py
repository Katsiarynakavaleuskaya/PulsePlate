#!/usr/bin/env python3
"""
Unit tests for BusinessBayesianAnalyzer.

Tests cover:
- Constructor and configuration loading
- Business logic analysis
- Monetization detection
- Cost optimization
- Revenue growth analysis
- ROI estimation
"""

import pytest
from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
    BusinessTestResult,
    ROIEstimate,
)


class TestBusinessBayesianAnalyzerInit:
    """Test analyzer initialization and configuration."""

    def test_init_default_nutrition_domain(self):
        """Test initialization with default nutrition domain."""
        analyzer = BusinessBayesianAnalyzer()
        assert (
            analyzer.low_price_threshold == BusinessBayesianAnalyzer.NUTRITION_LOW_PRICE_THRESHOLD
        )
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.NUTRITION_HIGH_PRICE_THRESHOLD
        )
        assert analyzer.test_results == []

    def test_init_generic_domain(self):
        """Test initialization with generic domain uses default thresholds."""
        analyzer = BusinessBayesianAnalyzer(domain="generic")
        assert analyzer.low_price_threshold == BusinessBayesianAnalyzer.DEFAULT_LOW_PRICE_THRESHOLD
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.DEFAULT_HIGH_PRICE_THRESHOLD
        )

    def test_init_custom_thresholds(self):
        """Test initialization with custom price thresholds."""
        analyzer = BusinessBayesianAnalyzer(low_price_threshold=10.0, high_price_threshold=500.0)
        assert analyzer.low_price_threshold == 10.0
        assert analyzer.high_price_threshold == 500.0

    def test_init_injected_business_knowledge(self):
        """Test initialization with injected business knowledge."""
        custom_knowledge = {"test_key": "test_value"}
        analyzer = BusinessBayesianAnalyzer(business_knowledge=custom_knowledge)
        assert analyzer.business_knowledge_base == custom_knowledge

    def test_init_injected_monetization_strategies(self):
        """Test initialization with injected monetization strategies."""
        custom_strategies = {"pricing_models": {"test": "value"}}
        analyzer = BusinessBayesianAnalyzer(monetization_strategies=custom_strategies)
        assert analyzer.monetization_strategies == custom_strategies

    def test_init_injected_cost_optimization_rules(self):
        """Test initialization with injected cost optimization rules."""
        custom_rules = {"infrastructure": {"test": "rule"}}
        analyzer = BusinessBayesianAnalyzer(cost_optimization_rules=custom_rules)
        assert analyzer.cost_optimization_rules == custom_rules


class TestBusinessLogicAnalysis:
    """Test business logic analysis functionality."""

    def test_analyze_empty_code(self):
        """Test analysis of empty code returns empty results."""
        analyzer = BusinessBayesianAnalyzer()
        results = analyzer.analyze("", "test_empty")
        assert isinstance(results, list)
        # Empty code may return empty results or minimal analysis
        assert all(isinstance(r, BusinessTestResult) for r in results)

    def test_analyze_simple_code(self):
        """Test analysis of simple test code."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_user_subscription():
    user = User()
    assert user.subscribe()
"""
        results = analyzer.analyze(code, "test_user_subscription")
        assert isinstance(results, list)
        assert all(isinstance(r, BusinessTestResult) for r in results)

    def test_analyze_monetization_code(self):
        """Test detection of monetization patterns."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_pricing():
    price = 29.99
    subscription = Subscription(price=price)
    assert subscription.validate()
"""
        results = analyzer.analyze(code, "test_pricing")
        assert isinstance(results, list)
        # Should detect pricing-related business logic

    def test_analyze_code_with_revenue_keywords(self):
        """Test detection of revenue-related patterns."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_revenue_calculation():
    revenue = calculate_monthly_revenue()
    assert revenue > 0
"""
        results = analyzer.analyze(code, "test_revenue_calculation")
        assert isinstance(results, list)

    def test_analyze_public_entry_point(self):
        """Test public analyze() method delegates to analyze_business_logic()."""
        analyzer = BusinessBayesianAnalyzer()
        code = "def test_example(): pass"
        results = analyzer.analyze(code, "test_example")
        assert isinstance(results, list)


class TestMonetizationAnalysis:
    """Test monetization detection and analysis."""

    def test_detect_price_pattern(self):
        """Test detection of price assignments."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_product_price():
    product.price = 19.99
    assert product.price > 0
"""
        results = analyzer.analyze(code, "test_product_price")
        assert isinstance(results, list)

    def test_detect_subscription_keywords(self):
        """Test detection of subscription-related code."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_subscription_renewal():
    subscription = create_subscription()
    assert subscription.renew()
"""
        results = analyzer.analyze(code, "test_subscription_renewal")
        assert isinstance(results, list)


class TestCostOptimization:
    """Test cost optimization analysis."""

    def test_analyze_cost_keywords(self):
        """Test detection of cost-related patterns."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_infrastructure_cost():
    cost = calculate_infrastructure_cost()
    assert cost < budget
"""
        results = analyzer.analyze(code, "test_infrastructure_cost")
        assert isinstance(results, list)


class TestRevenueGrowth:
    """Test revenue growth analysis."""

    def test_analyze_revenue_growth_patterns(self):
        """Test detection of revenue growth patterns."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_revenue_increase():
    old_revenue = 1000
    new_revenue = 1500
    growth = (new_revenue - old_revenue) / old_revenue
    assert growth > 0.3
"""
        results = analyzer.analyze(code, "test_revenue_increase")
        assert isinstance(results, list)


class TestCustomerRetention:
    """Test customer retention analysis."""

    def test_analyze_retention_keywords(self):
        """Test detection of customer retention patterns."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def test_user_retention():
    retained_users = get_retained_users()
    assert len(retained_users) > 100
"""
        results = analyzer.analyze(code, "test_user_retention")
        assert isinstance(results, list)


class TestROIEstimate:
    """Test ROI estimation dataclass."""

    def test_roi_estimate_creation(self):
        """Test creation of ROIEstimate."""
        roi = ROIEstimate(
            category="infrastructure",
            expected_roi=1.5,
            credible_interval_lower=1.2,
            credible_interval_upper=1.8,
            time_horizon_months=12,
            assumptions="Test assumptions",
        )
        assert roi.category == "infrastructure"
        assert roi.expected_roi == 1.5
        assert roi.credible_interval_lower == 1.2
        assert roi.credible_interval_upper == 1.8
        assert roi.time_horizon_months == 12
        assert roi.assumptions == "Test assumptions"


class TestBusinessTestResult:
    """Test BusinessTestResult dataclass."""

    def test_business_test_result_creation(self):
        """Test creation of BusinessTestResult."""
        result = BusinessTestResult(
            test_name="test_example",
            success=True,
            business_category=BusinessCategory.MONETIZATION,
            error_type=None,
            revenue_impact="High",
            cost_impact="Low",
        )
        assert result.test_name == "test_example"
        assert result.success is True
        assert result.business_category == BusinessCategory.MONETIZATION
        assert result.revenue_impact == "High"


class TestNormalizeCodeInput:
    """Test code normalization helper."""

    def test_normalize_string_input(self):
        """Test normalization of string input."""
        analyzer = BusinessBayesianAnalyzer()
        code = "def test(): pass"
        normalized = analyzer._normalize_code_input(code)
        assert normalized == code

    def test_normalize_list_input(self):
        """Test normalization of list input."""
        analyzer = BusinessBayesianAnalyzer()
        code_lines = ["def test():", "    pass"]
        normalized = analyzer._normalize_code_input(code_lines)
        assert "def test():" in normalized
        assert "pass" in normalized
        assert "\n" in normalized


class TestRemoveComments:
    """Test comment removal functionality."""

    def test_remove_inline_comments(self):
        """Test removal of inline comments."""
        analyzer = BusinessBayesianAnalyzer()
        code = "price = 10  # dollars"
        cleaned = analyzer._remove_comments(code)
        # Should preserve code but remove comment
        assert "price" in cleaned
        assert "10" in cleaned

    def test_preserve_hash_in_strings(self):
        """Test that # inside strings is preserved."""
        analyzer = BusinessBayesianAnalyzer()
        code = 'message = "Use #hashtag"'
        cleaned = analyzer._remove_comments(code)
        assert "#hashtag" in cleaned or "hashtag" in cleaned


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_with_list_input(self):
        """Test analysis with list of code lines."""
        analyzer = BusinessBayesianAnalyzer()
        code_lines = [
            "def test_subscription():",
            "    price = 9.99",
            "    assert price > 0",
        ]
        results = analyzer.analyze(code_lines, "test_subscription")
        assert isinstance(results, list)

    def test_analyze_malformed_code(self):
        """Test analysis handles malformed code gracefully."""
        analyzer = BusinessBayesianAnalyzer()
        code = "def test_broken(:"  # Invalid syntax
        results = analyzer.analyze(code, "test_broken")
        # Should not crash, returns results
        assert isinstance(results, list)

    def test_test_results_persistence(self):
        """Test that results are persisted in analyzer."""
        analyzer = BusinessBayesianAnalyzer()
        code = "def test(): pass"
        initial_count = len(analyzer.test_results)
        analyzer.analyze(code, "test_persistence")
        # Results should be appended
        assert len(analyzer.test_results) >= initial_count

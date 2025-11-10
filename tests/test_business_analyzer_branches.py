import pytest

from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
)


def test_monetization_missing_strategy_branch() -> None:
    analyzer = BusinessBayesianAnalyzer()
    code = "payment = 10  # billing present, but no plan/tier/subscription keywords"
    results = analyzer.analyze_business_logic(code, "test_monetization")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.REVENUE_LEAK
        for r in results
    )


def test_price_thresholds_nutrition_domain() -> None:
    """Test that nutrition domain uses domain-specific thresholds (5.0, 50.0)."""
    analyzer = BusinessBayesianAnalyzer(domain="nutrition")
    assert analyzer.low_price_threshold == 5.0
    assert analyzer.high_price_threshold == 50.0

    # Test low price detection
    code_low = "price = 3.0"
    results_low = analyzer.analyze_business_logic(code_low, "test_low_price")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
        and "5.00" in r.error_message
        for r in results_low
    )

    # Test high price detection
    code_high = "price = 75.0"
    results_high = analyzer.analyze_business_logic(code_high, "test_high_price")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
        and "50.00" in r.error_message
        for r in results_high
    )

    # Test valid price range (should not trigger)
    code_valid = "price = 25.0"
    results_valid = analyzer.analyze_business_logic(code_valid, "test_valid_price")
    pricing_issues = [
        r
        for r in results_valid
        if r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
    ]
    assert len(pricing_issues) == 0


def test_price_thresholds_generic_domain() -> None:
    """Test that generic domain uses default thresholds (1.0, 1000.0)."""
    analyzer = BusinessBayesianAnalyzer(domain="generic")
    assert analyzer.low_price_threshold == 1.0
    assert analyzer.high_price_threshold == 1000.0

    # Test low price detection
    code_low = "price = 0.5"
    results_low = analyzer.analyze_business_logic(code_low, "test_low_price")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
        and "1.00" in r.error_message
        for r in results_low
    )

    # Test high price detection
    code_high = "price = 1500.0"
    results_high = analyzer.analyze_business_logic(code_high, "test_high_price")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
        and "1000.00" in r.error_message
        for r in results_high
    )


def test_price_thresholds_custom_values() -> None:
    """Test that custom thresholds can be passed directly."""
    analyzer = BusinessBayesianAnalyzer(low_price_threshold=10.0, high_price_threshold=100.0)
    assert analyzer.low_price_threshold == 10.0
    assert analyzer.high_price_threshold == 100.0

    # Test low price detection with custom threshold
    code_low = "price = 5.0"
    results_low = analyzer.analyze_business_logic(code_low, "test_low_price")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
        and "10.00" in r.error_message
        for r in results_low
    )

    # Test high price detection with custom threshold
    code_high = "price = 150.0"
    results_high = analyzer.analyze_business_logic(code_high, "test_high_price")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
        and "100.00" in r.error_message
        for r in results_high
    )


def test_price_thresholds_default_nutrition() -> None:
    """Test that default domain is nutrition (uses nutrition thresholds)."""
    analyzer = BusinessBayesianAnalyzer()
    assert analyzer.low_price_threshold == 5.0
    assert analyzer.high_price_threshold == 50.0


def test_cost_optimization_ast_detects_nested_heavy_loops() -> None:
    """AST branch should detect nested loops with heavy operations."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
for user in users:
    for attempt in retries:
        api.post(attempt)
"""
    results = analyzer._analyze_cost_optimization(code, "cost_nested_ast")
    assert any(
        r.business_category == BusinessCategory.COST_OPTIMIZATION
        and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
        for r in results
    )


def test_cost_optimization_regex_handles_broken_code() -> None:
    """Regex fallback should emit result when AST parsing fails."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
for order in orders::
    for item in items:
        request(item)
"""
    results = analyzer._analyze_cost_optimization(code, "cost_nested_regex")
    assert any(
        r.business_category == BusinessCategory.COST_OPTIMIZATION
        and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
        for r in results
    )

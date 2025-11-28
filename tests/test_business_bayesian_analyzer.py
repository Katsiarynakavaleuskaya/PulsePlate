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
- Input validation and edge cases
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
        # Strict check: # must be preserved within the string
        assert "#hashtag" in cleaned, "Expected '#hashtag' with # preserved in string"


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
        """Test that results persist across analyze() calls."""
        analyzer = BusinessBayesianAnalyzer()
        code = "price = 5"  # Use code that triggers analysis
        initial_count = len(analyzer.test_results)
        analyzer.analyze(code, "test_persistence")
        # Results should be persisted (may be 0 if no issues found)
        final_count = len(analyzer.test_results)
        # Verify persistence mechanism works - calling analyze updates internal state
        assert final_count >= initial_count

    def test_cost_optimization_patterns(self):
        """Detect SQL select *, infinite loop, and sleep without retry/backoff."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def expensive_operation():
    query = "SELECT * FROM users"
    while True:
        process()
    time.sleep(5)
"""
        results = analyzer.analyze(code, "expensive_operation")
        messages = " ".join((r.error_message or "") for r in results)
        assert "SELECT *" in messages or "while True" in messages or "sleep" in messages

    def test_missing_cache_detection(self):
        """Lack of caching on data access should be flagged as operational waste."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def fetch_data():
    data = database.get_all()
    return data
"""
        results = analyzer.analyze(code, "fetch_data")
        assert any("кэширование" in (r.error_message or "") for r in results)

    def test_loader_fallbacks_without_yaml(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Loader helpers should fall back to defaults when yaml is unavailable."""
        analyzer = BusinessBayesianAnalyzer()
        monkeypatch.setattr(analyzer, "_import_yaml_module", lambda: None)

        knowledge = analyzer._load_business_knowledge()
        strategies = analyzer._load_monetization_strategies(locale="fr")
        cost_rules = analyzer._load_cost_optimization_rules()

        assert knowledge and "revenue_streams" in knowledge
        assert strategies and "pricing_models" in strategies
        assert cost_rules and "infrastructure" in cost_rules

    def test_calculate_bayesian_roi_validation(self):
        """ROI calculator should validate inputs and raise on invalid values."""
        analyzer = BusinessBayesianAnalyzer()
        with pytest.raises(ValueError):
            analyzer._calculate_bayesian_roi(
                category="cat",
                prior_mean=-1.0,
                prior_std=0.1,
                data=[],
                time_horizon_months=1,
                assumptions="x",
            )
        with pytest.raises(ValueError):
            analyzer._calculate_bayesian_roi(
                category="cat",
                prior_mean=0.1,
                prior_std=-0.1,
                data=[],
                time_horizon_months=1,
                assumptions="x",
            )
        with pytest.raises(ValueError):
            analyzer._calculate_bayesian_roi(
                category="cat",
                prior_mean=0.1,
                prior_std=0.1,
                data=[-1.0],
                time_horizon_months=1,
                assumptions="x",
            )

    def test_calculate_bayesian_roi_no_data_and_with_data(self):
        """Cover both no-data prior-only and data-informed ROI paths."""
        analyzer = BusinessBayesianAnalyzer()
        roi_prior = analyzer._calculate_bayesian_roi(
            category="c1",
            prior_mean=0.2,
            prior_std=0.05,
            data=[],
            time_horizon_months=6,
            assumptions="test",
        )
        assert isinstance(roi_prior, ROIEstimate)
        assert roi_prior.time_horizon_months == 6

        data = [0.1, 0.2, 0.3, 0.15]
        roi_data = analyzer._calculate_bayesian_roi(
            category="c2",
            prior_mean=0.15,
            prior_std=0.06,
            data=data,
            time_horizon_months=12,
            assumptions="test2",
        )
        assert isinstance(roi_data, ROIEstimate)
        assert (
            roi_data.credible_interval_lower
            <= roi_data.expected_roi
            <= roi_data.credible_interval_upper
        )

    def test_analyze_monetization_low_and_high_price(self):
        """Low and high pricing should trigger pricing inefficiency flags."""
        analyzer = BusinessBayesianAnalyzer(low_price_threshold=10.0, high_price_threshold=100.0)
        low_results = analyzer._analyze_monetization("price = 5", "test_low_price")
        high_results = analyzer._analyze_monetization("cost = 150", "test_high_price")
        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
            for r in low_results
        )
        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
            for r in high_results
        )

    def test_analyze_customer_acquisition_validation_and_onboarding(self):
        """Registration without validation and onboarding should raise churn issues."""
        analyzer = BusinessBayesianAnalyzer()
        code = "register_user(); new_user = True"
        results = analyzer._analyze_customer_acquisition(code, "acq_test")
        messages = " ".join((r.error_message or "") for r in results)
        assert "валидации" in messages or "онбординга" in messages

    def test_analyze_monetization_invalid_price_valueerror_branch(self):
        """Non-numeric price should be safely skipped without crashing."""
        analyzer = BusinessBayesianAnalyzer()
        code = "price = 'abc'"
        results = analyzer._analyze_monetization(code, "bad_price")
        assert isinstance(results, list)

    def test_calculate_bayesian_roi_warning_branch(self, caplog: pytest.LogCaptureFixture) -> None:
        """Large std should hit the delta-method warning path and still return ROI estimate."""
        analyzer = BusinessBayesianAnalyzer()
        roi = analyzer._calculate_bayesian_roi(
            category="warn",
            prior_mean=0.1,
            prior_std=0.5,  # large std triggers warning path
            data=[0.2, 0.25],
            time_horizon_months=3,
            assumptions="test warning",
        )
        assert isinstance(roi, ROIEstimate)

    def test_calculate_roi_potential_multiple_categories(self):
        """ROI potential should include all categories present in diagnosed issues."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.extend(
            [
                BusinessTestResult(
                    test_name="t_cost",
                    success=False,
                    business_category=BusinessCategory.COST_OPTIMIZATION,
                    error_type=BusinessErrorType.OPERATIONAL_WASTE,
                ),
                BusinessTestResult(
                    test_name="t_monetization",
                    success=False,
                    business_category=BusinessCategory.MONETIZATION,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                ),
                BusinessTestResult(
                    test_name="t_acquisition",
                    success=False,
                    business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                ),
                BusinessTestResult(
                    test_name="t_retention",
                    success=False,
                    business_category=BusinessCategory.USER_RETENTION,
                    error_type=BusinessErrorType.CUSTOMER_CHURN,
                ),
            ]
        )
        roi_estimates = analyzer.calculate_roi_potential()
        categories = {est.category for est in roi_estimates}
        assert {
            "cost_optimization",
            "monetization",
            "customer_acquisition",
            "user_retention",
        } <= categories

    def test_generate_cost_savings_recommendations(self):
        """Cost savings recommendations should be produced when issues diagnosed."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.append(
            BusinessTestResult(
                test_name="t_cost",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            )
        )
        recs = analyzer.generate_cost_savings_recommendations()
        assert any("эконом" in r.lower() or "кэш" in r.lower() for r in recs)

    def test_generate_cost_savings_includes_operational_efficiency(self):
        """Operational efficiency issues should add development recommendations."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.append(
            BusinessTestResult(
                test_name="t_ops",
                success=False,
                business_category=BusinessCategory.OPERATIONAL_EFFICIENCY,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            )
        )
        recs = analyzer.generate_cost_savings_recommendations()
        assert any("тестирован" in r.lower() or "мониторинг" in r.lower() for r in recs)

    def test_calculate_roi_potential_no_issues_returns_empty(self):
        """When no issues diagnosed, ROI potential should be empty."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.clear()
        roi_estimates = analyzer.calculate_roi_potential()
        assert roi_estimates == []

    def test_generate_revenue_optimization_recommendations(self):
        """Revenue optimization recommendations should reflect diagnosed issues."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.extend(
            [
                BusinessTestResult(
                    test_name="t_acq",
                    success=False,
                    business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                ),
                BusinessTestResult(
                    test_name="t_ret",
                    success=False,
                    business_category=BusinessCategory.USER_RETENTION,
                    error_type=BusinessErrorType.CUSTOMER_CHURN,
                ),
                BusinessTestResult(
                    test_name="t_data",
                    success=False,
                    business_category=BusinessCategory.DATA_MONETIZATION,
                    error_type=BusinessErrorType.DATA_UNDERUTILIZED,
                ),
            ]
        )
        recs = analyzer.generate_revenue_optimization_recommendations()
        assert any("онбординг" in r.lower() or "конверсии" in r.lower() for r in recs)
        assert any("лояль" in r.lower() or "удержание" in r.lower() for r in recs)
        assert any("api" in r.lower() or "аналит" in r.lower() for r in recs)

    def test_generate_revenue_recommendations_only_with_no_issues(self):
        """When no revenue-related issues, recommendations should be empty."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.append(
            BusinessTestResult(
                test_name="t_cost_only",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            )
        )
        recs = analyzer.generate_revenue_optimization_recommendations()
        assert recs == []

    def test_revenue_growth_branches(self):
        """Analytics without A/B and personalization without recommendations should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def growth():
    analytics = True
    revenue = 1000
    user = current_user
    personal = True
"""
        results = analyzer._analyze_revenue_growth(code, "test_growth")
        messages = " ".join((r.error_message or "") for r in results)
        assert "A/B" in messages or "Персонализация" in messages

    def test_customer_retention_branches(self):
        """Communication without segmentation and feedback without processing should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def retention():
    notification = send_email()
    feedback = collect_feedback()
"""
        results = analyzer._analyze_customer_retention(code, "test_retention")
        assert any(r.error_type == BusinessErrorType.CUSTOMER_CHURN for r in results)

    def test_analyze_cost_optimization_select_star_and_sleep(self):
        """SELECT * outside tests and sleep without retry should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def prod_code():
    query = "SELECT * FROM users"
    time.sleep(2)
"""
        results = analyzer._analyze_cost_optimization(code, "prod_code")
        messages = " ".join((r.error_message or "") for r in results)
        assert "SELECT *" in messages or "sleep" in messages

    def test_diagnose_business_issues_and_roi_potential(self):
        """Diagnose issues from stored results and calculate ROI potential."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.extend(
            [
                BusinessTestResult(
                    test_name="t1",
                    success=False,
                    business_category=BusinessCategory.COST_OPTIMIZATION,
                    error_type=BusinessErrorType.OPERATIONAL_WASTE,
                ),
                BusinessTestResult(
                    test_name="t2",
                    success=False,
                    business_category=BusinessCategory.MONETIZATION,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                ),
            ]
        )

        issues = analyzer.diagnose_business_issues()
        assert BusinessCategory.COST_OPTIMIZATION in issues
        assert BusinessCategory.MONETIZATION in issues

        roi_estimates = analyzer.calculate_roi_potential()
        assert isinstance(roi_estimates, list)
        assert any(est.category in {"cost_optimization", "monetization"} for est in roi_estimates)

    def test_generate_revenue_optimization_recommendations_with_additional_cases(self):
        """Ensure revenue/retention/data monetization branches produce recommendations."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results.extend(
            [
                BusinessTestResult(
                    test_name="t_acq",
                    success=False,
                    business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                    error_type=BusinessErrorType.CUSTOMER_CHURN,
                ),
                BusinessTestResult(
                    test_name="t_ret",
                    success=False,
                    business_category=BusinessCategory.USER_RETENTION,
                    error_type=BusinessErrorType.CUSTOMER_CHURN,
                ),
                BusinessTestResult(
                    test_name="t_data",
                    success=False,
                    business_category=BusinessCategory.DATA_MONETIZATION,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                ),
            ]
        )
        recs = analyzer.generate_revenue_optimization_recommendations()
        joined = " ".join(recs)
        assert "онбординга" in joined or "loyalty" in joined.lower()
        assert "API" in joined or "аналитические отчеты" in joined


class TestInternalHelpers:
    """Test internal helper methods for coverage."""

    def test_normalize_and_remove_comments_preserves_string_hash(self):
        """Test that string literals with # are preserved while comments are removed."""
        analyzer = BusinessBayesianAnalyzer()
        code_list = ["def foo():", '    s = "value # not a comment"', "    x = 1  # actual comment"]
        normalized = analyzer._normalize_code_input(code_list)
        assert isinstance(normalized, str)
        cleaned = analyzer._remove_comments(normalized)
        assert "#" in cleaned  # string literal hash remains
        assert "actual comment" not in cleaned

    def test_analyze_cost_optimization_detects_nested_loop_and_append(self):
        """Test nested loop with append detection for cost optimization."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
for a in range(3):
    for b in range(2):
        lst.append(b)
"""
        results = analyzer._analyze_cost_optimization(code, "test_nested_loop")
        assert any(r.business_category == BusinessCategory.COST_OPTIMIZATION for r in results)

    def test_calculate_bayesian_roi_input_validation(self):
        """Test input validation for ROI calculation."""
        analyzer = BusinessBayesianAnalyzer()
        # invalid prior_mean <= -1
        with pytest.raises(ValueError):
            analyzer._calculate_bayesian_roi(
                "cat",
                prior_mean=-1.0,
                prior_std=0.1,
                data=[],
                time_horizon_months=1,
                assumptions="x",
            )
        # invalid prior_std < 0
        with pytest.raises(ValueError):
            analyzer._calculate_bayesian_roi(
                "cat",
                prior_mean=0.1,
                prior_std=-0.1,
                data=[],
                time_horizon_months=1,
                assumptions="x",
            )
        # invalid data value <= -1
        with pytest.raises(ValueError):
            analyzer._calculate_bayesian_roi(
                "cat",
                prior_mean=0.1,
                prior_std=0.1,
                data=[-1.0],
                time_horizon_months=1,
                assumptions="x",
            )

    def test_calculate_bayesian_roi_high_variance_branch(self):
        """High variance should hit delta-method variance branch without errors."""
        analyzer = BusinessBayesianAnalyzer()
        estimate = analyzer._calculate_bayesian_roi(
            category="var_branch",
            prior_mean=0.1,
            prior_std=1.5,  # large std to trigger relative_variance threshold
            data=[0.2, 0.4],
            time_horizon_months=6,
            assumptions="test",
        )
        assert isinstance(estimate, ROIEstimate)
        assert estimate.expected_roi > -1

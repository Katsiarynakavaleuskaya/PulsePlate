"""Comprehensive tests for BusinessBayesianAnalyzer."""

from __future__ import annotations

import math
from typing import Any
from unittest.mock import MagicMock, patch, mock_open

import pytest

from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
    BusinessTestResult,
    ROIEstimate,
)


def test_analyzer_smoke() -> None:
    """Ensure analyzer init and analyze run (coverage insurance)."""
    analyzer = BusinessBayesianAnalyzer()
    result = analyzer.analyze("price = 10", "smoke")
    assert isinstance(result, list)


class TestBusinessBayesianAnalyzerInit:
    """Tests for BusinessBayesianAnalyzer initialization."""

    def test_init_with_default_values(self) -> None:
        """Test initialization with default values."""
        analyzer = BusinessBayesianAnalyzer()

        assert analyzer.locale == "en"
        assert analyzer.test_results == []
        assert (
            analyzer.low_price_threshold == BusinessBayesianAnalyzer.NUTRITION_LOW_PRICE_THRESHOLD
        )
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.NUTRITION_HIGH_PRICE_THRESHOLD
        )

    def test_init_with_custom_thresholds(self) -> None:
        """Test initialization with custom price thresholds."""
        analyzer = BusinessBayesianAnalyzer(
            low_price_threshold=10.0,
            high_price_threshold=100.0,
        )

        assert analyzer.low_price_threshold == 10.0
        assert analyzer.high_price_threshold == 100.0

    def test_init_with_generic_domain(self) -> None:
        """Test initialization with generic domain uses generic thresholds."""
        analyzer = BusinessBayesianAnalyzer(domain="generic")

        assert analyzer.low_price_threshold == BusinessBayesianAnalyzer.DEFAULT_LOW_PRICE_THRESHOLD
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.DEFAULT_HIGH_PRICE_THRESHOLD
        )

    def test_init_with_health_domain(self) -> None:
        """Test initialization with health domain uses nutrition thresholds."""
        analyzer = BusinessBayesianAnalyzer(domain="health")

        assert (
            analyzer.low_price_threshold == BusinessBayesianAnalyzer.NUTRITION_LOW_PRICE_THRESHOLD
        )
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.NUTRITION_HIGH_PRICE_THRESHOLD
        )

    def test_init_with_injected_business_knowledge(self) -> None:
        """Test initialization with injected business knowledge."""
        custom_knowledge = {"revenue_streams": {"custom": {"price_range": [1, 10]}}}
        analyzer = BusinessBayesianAnalyzer(business_knowledge=custom_knowledge)

        assert analyzer.business_knowledge_base == custom_knowledge

    def test_init_with_injected_monetization_strategies(self) -> None:
        """Test initialization with injected monetization strategies."""
        custom_strategies = {"pricing_models": {"custom": True}}
        analyzer = BusinessBayesianAnalyzer(monetization_strategies=custom_strategies)

        assert analyzer.monetization_strategies == custom_strategies

    def test_init_with_injected_cost_optimization_rules(self) -> None:
        """Test initialization with injected cost optimization rules."""
        custom_rules = {"infrastructure": {"custom": True}}
        analyzer = BusinessBayesianAnalyzer(cost_optimization_rules=custom_rules)

        assert analyzer.cost_optimization_rules == custom_rules

    def test_init_with_locale(self) -> None:
        """Test initialization with specific locale."""
        analyzer = BusinessBayesianAnalyzer(locale="ru")

        assert analyzer.locale == "ru"


class TestMonetizationAnalysis:
    """Tests for monetization analysis."""

    def test_analyze_low_price(self) -> None:
        """Test detection of low pricing."""
        analyzer = BusinessBayesianAnalyzer()
        code = "price = 2.0"

        results = analyzer._analyze_monetization(code, "test_pricing")

        assert len(results) == 1
        assert results[0].business_category == BusinessCategory.MONETIZATION
        assert results[0].error_type == BusinessErrorType.PRICING_INEFFICIENCY
        assert "низкая цена" in results[0].error_message.lower()
        assert not results[0].success

    def test_analyze_high_price(self) -> None:
        """Test detection of high pricing."""
        analyzer = BusinessBayesianAnalyzer()
        code = "subscription = 100.0"

        results = analyzer._analyze_monetization(code, "test_pricing")

        assert len(results) == 1
        assert results[0].business_category == BusinessCategory.MONETIZATION
        assert results[0].error_type == BusinessErrorType.PRICING_INEFFICIENCY
        assert "высокая цена" in results[0].error_message.lower()

    def test_analyze_payment_without_strategy(self) -> None:
        """Test detection of payment without monetization strategy."""
        analyzer = BusinessBayesianAnalyzer()
        code = "process_payment(amount) billing_cycle"

        results = analyzer._analyze_monetization(code, "test_payment")

        assert any(
            r.error_type == BusinessErrorType.REVENUE_LEAK
            and "без стратегии монетизации" in r.error_message
            for r in results
        )

    def test_analyze_removes_comments_before_matching(self) -> None:
        """Test that comments are removed before pattern matching."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
# This is a comment with price = 2.0
actual_price = 25.0  # This should be detected
"""

        results = analyzer._analyze_monetization(code, "test_comments")

        # Should not detect price in comment, only actual_price
        assert all("2.0" not in r.error_message for r in results)


class TestCustomerAcquisitionAnalysis:
    """Tests for customer acquisition analysis."""

    def test_analyze_registration_without_validation(self) -> None:
        """Test detection of registration without validation."""
        analyzer = BusinessBayesianAnalyzer()
        code = "def signup(username): create_account(username)"

        results = analyzer._analyze_customer_acquisition(code, "test_signup")

        assert any(
            r.error_type == BusinessErrorType.CUSTOMER_CHURN and "без валидации" in r.error_message
            for r in results
        )

    def test_analyze_registration_without_onboarding(self) -> None:
        """Test detection of registration without onboarding."""
        analyzer = BusinessBayesianAnalyzer()
        code = "def register(user): new_user(user)"

        results = analyzer._analyze_customer_acquisition(code, "test_register")

        assert any(
            r.error_type == BusinessErrorType.CUSTOMER_CHURN and "онбординга" in r.error_message
            for r in results
        )

    def test_analyze_no_acquisition_keywords(self) -> None:
        """Test no issues when no acquisition keywords present."""
        analyzer = BusinessBayesianAnalyzer()
        code = "def process_data(data): return data"

        results = analyzer._analyze_customer_acquisition(code, "test_process")

        assert len(results) == 0


class TestCostOptimizationAnalysis:
    """Tests for cost optimization analysis."""

    def test_analyze_nested_loops_with_ast(self) -> None:
        """Test detection of nested loops using AST."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
for item in items:
    for sub_item in item:
        database.append(sub_item)
"""

        results = analyzer._analyze_cost_optimization(code, "test_loops")

        assert any(
            r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            and "циклы" in r.error_message.lower()
            for r in results
        )

    def test_analyze_select_star_in_non_test(self) -> None:
        """Test detection of SELECT * in non-test context."""
        analyzer = BusinessBayesianAnalyzer()
        code = "SELECT * FROM users"

        results = analyzer._analyze_cost_optimization(code, "process_users")

        assert any(
            r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            and "select *" in r.error_message.lower()
            for r in results
        )

    def test_analyze_while_true_without_break(self) -> None:
        """Test detection of while True without break."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
while True:
    process_item()
    continue
"""

        results = analyzer._analyze_cost_optimization(code, "test_loop")

        assert any(
            r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            and "while true" in r.error_message.lower()
            for r in results
        )

    def test_analyze_sleep_without_retry_context(self) -> None:
        """Test detection of sleep() without retry context."""
        analyzer = BusinessBayesianAnalyzer()
        code = "time.sleep(5)"

        results = analyzer._analyze_cost_optimization(code, "test_sleep")

        assert any(
            r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            and "sleep()" in r.error_message.lower()
            for r in results
        )

    def test_analyze_no_caching(self) -> None:
        """Test detection of missing caching."""
        analyzer = BusinessBayesianAnalyzer()
        code = "database.query(sql)"

        results = analyzer._analyze_cost_optimization(code, "test_query")

        assert any(
            r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            and "кэширование" in r.error_message.lower()
            for r in results
        )


class TestRevenueGrowthAnalysis:
    """Tests for revenue growth analysis."""

    def test_analyze_negative_payment_amount(self) -> None:
        """Test detection of revenue leak with negative amounts."""
        analyzer = BusinessBayesianAnalyzer()
        code = "process_payment(amount=-100)"

        results = analyzer._analyze_revenue_growth(code, "test_payment")

        assert any(
            r.error_type == BusinessErrorType.REVENUE_LEAK
            and "утечка дохода" in r.error_message.lower()
            for r in results
        )

    def test_analyze_analytics_without_ab_testing(self) -> None:
        """Test detection of analytics without A/B testing."""
        analyzer = BusinessBayesianAnalyzer()
        code = "track_conversion(metrics)"

        results = analyzer._analyze_revenue_growth(code, "test_analytics")

        assert any(
            r.error_type == BusinessErrorType.REVENUE_LEAK
            and "a/b тестирования" in r.error_message.lower()
            for r in results
        )

    def test_analyze_personalization_without_recommendations(self) -> None:
        """Test detection of personalization without recommendations."""
        analyzer = BusinessBayesianAnalyzer()
        code = "user.personal_data"

        results = analyzer._analyze_revenue_growth(code, "test_personalization")

        assert any(
            r.error_type == BusinessErrorType.REVENUE_LEAK
            and "рекомендаций" in r.error_message.lower()
            for r in results
        )


class TestCustomerRetentionAnalysis:
    """Tests for customer retention analysis."""

    def test_analyze_communication_without_segmentation(self) -> None:
        """Test detection of communication without segmentation."""
        analyzer = BusinessBayesianAnalyzer()
        code = "send_notification(user)"

        results = analyzer._analyze_customer_retention(code, "test_notification")

        assert any(
            r.error_type == BusinessErrorType.CUSTOMER_CHURN
            and "сегментации" in r.error_message.lower()
            for r in results
        )

    def test_analyze_feedback_without_processing(self) -> None:
        """Test detection of feedback collection without processing."""
        analyzer = BusinessBayesianAnalyzer()
        code = "collect_feedback(user)"

        results = analyzer._analyze_customer_retention(code, "test_feedback")

        assert any(
            r.error_type == BusinessErrorType.CUSTOMER_CHURN
            and "обработки" in r.error_message.lower()
            for r in results
        )


class TestAnalyzeBusinessLogic:
    """Tests for main analyze_business_logic method."""

    def test_analyze_combines_all_analyses(self) -> None:
        """Test that analyze combines results from all analysis methods."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
price = 2.0
signup(user)
database.query(sql)
process_payment(amount=-10)
send_notification(user)
"""

        results = analyzer.analyze_business_logic(code, "test_comprehensive")

        # Should have results from multiple analysis categories
        categories = {r.business_category for r in results}
        assert len(categories) > 1
        assert len(analyzer.test_results) == len(results)

    def test_analyze_with_list_input(self) -> None:
        """Test analyze with list input."""
        analyzer = BusinessBayesianAnalyzer()
        code_lines = ["price = 2.0", "subscription = 100.0"]

        results = analyzer.analyze_business_logic(code_lines, "test_list")

        assert len(results) >= 1

    def test_analyze_public_entry_point(self) -> None:
        """Test public analyze method delegates to analyze_business_logic."""
        analyzer = BusinessBayesianAnalyzer()
        code = "price = 2.0"

        results1 = analyzer.analyze(code, "test1")
        results2 = analyzer.analyze_business_logic(code, "test2")

        assert isinstance(results1, type(results2))
        assert len(results1) > 0


class TestROICalculations:
    """Tests for ROI calculation methods."""

    def test_calculate_roi_potential_with_issues(self) -> None:
        """Test ROI calculation with diagnosed issues."""
        analyzer = BusinessBayesianAnalyzer()
        # Add some test results to trigger ROI calculations
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            ),
            BusinessTestResult(
                test_name="test2",
                success=False,
                business_category=BusinessCategory.MONETIZATION,
                error_type=BusinessErrorType.PRICING_INEFFICIENCY,
            ),
        ]

        roi_estimates = analyzer.calculate_roi_potential()

        assert len(roi_estimates) >= 1
        assert all(isinstance(e, ROIEstimate) for e in roi_estimates)

    def test_calculate_bayesian_roi_with_valid_inputs(self) -> None:
        """Test Bayesian ROI calculation with valid inputs."""
        analyzer = BusinessBayesianAnalyzer()

        estimate = analyzer._calculate_bayesian_roi(
            category="test",
            prior_mean=0.2,
            prior_std=0.1,
            data=[0.15, 0.25, 0.3],
            time_horizon_months=12,
            assumptions="Test assumptions",
        )

        assert estimate.category == "test"
        assert estimate.expected_roi > 0
        assert estimate.credible_interval_lower < estimate.expected_roi
        assert estimate.credible_interval_upper > estimate.expected_roi
        assert estimate.time_horizon_months == 12

    def test_calculate_bayesian_roi_invalid_prior_mean(self) -> None:
        """Test ROI calculation raises error for invalid prior_mean."""
        analyzer = BusinessBayesianAnalyzer()

        with pytest.raises(ValueError, match="Invalid prior_mean"):
            analyzer._calculate_bayesian_roi(
                category="test",
                prior_mean=-1.5,  # Invalid: must be > -1
                prior_std=0.1,
                data=[],
                time_horizon_months=12,
                assumptions="Test",
            )

    def test_calculate_bayesian_roi_invalid_prior_std(self) -> None:
        """Test ROI calculation raises error for invalid prior_std."""
        analyzer = BusinessBayesianAnalyzer()

        with pytest.raises(ValueError, match="Invalid prior_std"):
            analyzer._calculate_bayesian_roi(
                category="test",
                prior_mean=0.2,
                prior_std=-0.1,  # Invalid: must be >= 0
                data=[],
                time_horizon_months=12,
                assumptions="Test",
            )

    def test_calculate_bayesian_roi_invalid_data_values(self) -> None:
        """Test ROI calculation raises error for invalid data values."""
        analyzer = BusinessBayesianAnalyzer()

        with pytest.raises(ValueError, match="Invalid data values"):
            analyzer._calculate_bayesian_roi(
                category="test",
                prior_mean=0.2,
                prior_std=0.1,
                data=[0.1, -1.5, 0.3],  # Invalid: contains value <= -1
                time_horizon_months=12,
                assumptions="Test",
            )

    def test_calculate_bayesian_roi_high_variance_triggers_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that high variance triggers delta-method warning."""
        analyzer = BusinessBayesianAnalyzer()

        analyzer._calculate_bayesian_roi(
            category="high_var",
            prior_mean=0.2,
            prior_std=0.5,  # High std relative to mean
            data=[],
            time_horizon_months=12,
            assumptions="High variance test",
        )

        assert "Delta-method approximation assumption violated" in caplog.text

    def test_collect_category_data_extracts_severity(self) -> None:
        """Test that _collect_category_data extracts severity from error messages."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_message="This is a critical issue",
            ),
            BusinessTestResult(
                test_name="test2",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_message="This is a low priority issue",
            ),
        ]

        data = analyzer._collect_category_data()

        assert "cost_optimization" in data
        assert len(data["cost_optimization"]) == 2
        # Critical should have higher ROI than low
        assert data["cost_optimization"][0] > data["cost_optimization"][1]


class TestRecommendations:
    """Tests for recommendation generation."""

    def test_generate_cost_savings_recommendations(self) -> None:
        """Test cost savings recommendations generation."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
            ),
        ]

        recommendations = analyzer.generate_cost_savings_recommendations()

        assert len(recommendations) > 0
        assert all(isinstance(r, str) for r in recommendations)

    def test_generate_revenue_optimization_recommendations(self) -> None:
        """Test revenue optimization recommendations generation."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.CUSTOMER_ACQUISITION,
            ),
        ]

        recommendations = analyzer.generate_revenue_optimization_recommendations()

        assert len(recommendations) > 0


class TestDiagnostics:
    """Tests for business issue diagnostics."""

    def test_diagnose_business_issues_empty_results(self) -> None:
        """Test diagnosis with no results."""
        analyzer = BusinessBayesianAnalyzer()

        issues = analyzer.diagnose_business_issues()

        assert issues == {}

    def test_diagnose_business_issues_with_results(self) -> None:
        """Test diagnosis with results."""
        analyzer = BusinessBayesianAnalyzer()
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.MONETIZATION,
            ),
            BusinessTestResult(
                test_name="test2",
                success=False,
                business_category=BusinessCategory.MONETIZATION,
            ),
            BusinessTestResult(
                test_name="test3",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
            ),
        ]

        issues = analyzer.diagnose_business_issues()

        assert BusinessCategory.MONETIZATION in issues
        assert BusinessCategory.COST_OPTIMIZATION in issues
        assert issues[BusinessCategory.MONETIZATION] == pytest.approx(2.0 / 3.0)
        assert issues[BusinessCategory.COST_OPTIMIZATION] == pytest.approx(1.0 / 3.0)


class TestHelperMethods:
    """Tests for helper methods."""

    def test_normalize_code_input_with_string(self) -> None:
        """Test code normalization with string input."""
        analyzer = BusinessBayesianAnalyzer()
        code = "line1\nline2"

        result = analyzer._normalize_code_input(code)

        assert result == "line1\nline2"

    def test_normalize_code_input_with_list(self) -> None:
        """Test code normalization with list input."""
        analyzer = BusinessBayesianAnalyzer()
        code = ["line1", "line2"]

        result = analyzer._normalize_code_input(code)

        assert result == "line1\nline2"

    def test_normalize_code_input_with_tuple(self) -> None:
        """Test code normalization with tuple input."""
        analyzer = BusinessBayesianAnalyzer()
        code = ("line1", "line2")

        result = analyzer._normalize_code_input(code)

        assert result == "line1\nline2"

    def test_remove_comments_with_tokenize(self) -> None:
        """Test comment removal using tokenize."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
price = 10.0  # This is a comment
# Full line comment
value = 20.0
"""

        result = analyzer._remove_comments(code)

        assert "# This is a comment" not in result
        assert "# Full line comment" not in result
        assert "price = 10.0" in result
        assert "value = 20.0" in result

    def test_remove_comments_fallback_for_broken_code(self) -> None:
        """Test comment removal fallback for broken code."""
        analyzer = BusinessBayesianAnalyzer()
        # Broken code that can't be tokenized
        code = "price = 10 # comment\nif incomplete"

        result = analyzer._remove_comments(code)

        # Should still remove comments even with broken code
        assert "# comment" not in result

    def test_remove_comments_preserves_hash_in_strings(self) -> None:
        """Test that # inside strings is preserved."""
        analyzer = BusinessBayesianAnalyzer()
        code = '''text = "This is a #hashtag"'''

        result = analyzer._remove_comments(code)

        assert "#hashtag" in result


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_import_yaml_module_success(self) -> None:
        """Test successful YAML module import."""
        with patch("importlib.import_module", return_value=MagicMock()):
            result = BusinessBayesianAnalyzer._import_yaml_module()

            assert result is not None

    def test_import_yaml_module_not_found(self) -> None:
        """Test YAML module not found returns None."""
        with patch("importlib.import_module", side_effect=ModuleNotFoundError()):
            result = BusinessBayesianAnalyzer._import_yaml_module()

            assert result is None

    def test_config_dir_finds_existing(self, tmp_path: Any) -> None:
        """Test config dir returns existing directory."""
        analyzer = BusinessBayesianAnalyzer()
        # This will use the actual project structure
        config_dir = analyzer._config_dir()

        assert config_dir.name == "config"

    def test_load_business_knowledge_without_yaml(self) -> None:
        """Test loading business knowledge without YAML module."""
        with patch.object(BusinessBayesianAnalyzer, "_import_yaml_module", return_value=None):
            analyzer = BusinessBayesianAnalyzer()

            assert "revenue_streams" in analyzer.business_knowledge_base

    def test_load_monetization_strategies_with_locale(self) -> None:
        """Test loading monetization strategies with locale."""
        analyzer = BusinessBayesianAnalyzer(locale="ru")

        assert analyzer.monetization_strategies is not None

    def test_load_cost_optimization_rules_without_yaml(self) -> None:
        """Test loading cost optimization rules without YAML."""
        with patch.object(BusinessBayesianAnalyzer, "_import_yaml_module", return_value=None):
            analyzer = BusinessBayesianAnalyzer()

            assert "infrastructure" in analyzer.cost_optimization_rules

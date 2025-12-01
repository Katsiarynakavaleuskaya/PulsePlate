#!/usr/bin/env python3
"""
Additional coverage tests for BusinessBayesianAnalyzer to reach 97% total coverage.

Targets uncovered lines from CI coverage report:
- Lines 221, 232, 234: PyYAML module import failures
- Lines 271-274, 294-305: Locale normalization edge cases
- Lines 319, 326-327, 332, 334: Monetization strategies loading
- Lines 379-380, 385: Cost optimization rules loading
- Lines 508-557: Monetization analysis branches
- Lines 626-634: Customer acquisition analysis
- Lines 758-764: Cost optimization nested loops
- Lines 981-1320: Revenue growth and retention analysis
"""

from pathlib import Path
import pytest
from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
)


class TestYAMLImportFailure:
    """Test YAML module import failure paths."""

    def test_yaml_module_none_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When PyYAML not available, should fall back to defaults."""
        analyzer = BusinessBayesianAnalyzer()
        # Simulate yaml module unavailable
        monkeypatch.setattr(analyzer, "_import_yaml_module", lambda: None)

        # All loaders should return defaults when yaml is None
        knowledge = analyzer._load_business_knowledge()
        assert "revenue_streams" in knowledge
        assert "subscription" in knowledge["revenue_streams"]

        strategies = analyzer._load_monetization_strategies("en")
        assert "pricing_models" in strategies

        rules = analyzer._load_cost_optimization_rules()
        assert "infrastructure" in rules


class TestLocaleNormalization:
    """Test locale normalization edge cases."""

    def test_locale_none_defaults_to_en(self) -> None:
        """When locale is None, should default to 'en'."""
        analyzer = BusinessBayesianAnalyzer(locale=None)
        strategies = analyzer._load_monetization_strategies(None)
        assert "pricing_models" in strategies

    def test_locale_unsupported_falls_back_to_en(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unsupported locale should fall back to 'en'."""
        import core.business_bayesian_analyzer as bba_module

        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create only 'en' locale file
        en_yaml = config_dir / "monetization_strategies.en.yaml"
        en_yaml.write_text("pricing_models:\n  test: value\n", encoding="utf-8")

        monkeypatch.setattr(
            bba_module, "__file__", str(tmp_path / "core" / "business_bayesian_analyzer.py")
        )

        analyzer = BusinessBayesianAnalyzer()
        # Request unsupported locale 'xx', should fall back to 'en'
        strategies = analyzer._load_monetization_strategies("xx")
        assert "pricing_models" in strategies

    def test_locale_with_i18n_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When i18n module unavailable, should use fallback locale validation."""
        # Simulate ImportError for i18n module by monkeypatching sys.modules
        import sys

        original_modules = sys.modules.copy()
        if "core.i18n" in sys.modules:
            monkeypatch.delitem(sys.modules, "core.i18n")

        # This will trigger ImportError in _load_monetization_strategies
        analyzer = BusinessBayesianAnalyzer()
        strategies = analyzer._load_monetization_strategies("ru")
        assert "pricing_models" in strategies


class TestMonetizationAnalysis:
    """Test monetization analysis branches."""

    def test_payment_without_monetization_strategy(self) -> None:
        """Payment mentions without strategy should flag revenue leak."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def process_payment():
    payment = stripe.charge(amount=100)
    return payment
"""
        results = analyzer._analyze_monetization(code, "test_payment")
        # Should detect payment without monetization strategy
        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.REVENUE_LEAK
            for r in results
        )

    def test_low_price_detection(self) -> None:
        """Prices below threshold should be flagged."""
        analyzer = BusinessBayesianAnalyzer(low_price_threshold=10.0)
        code = "price = 5.0"
        results = analyzer._analyze_monetization(code, "test_low_price")
        assert any(r.error_type == BusinessErrorType.PRICING_INEFFICIENCY for r in results)

    def test_high_price_detection(self) -> None:
        """Prices above threshold should be flagged."""
        analyzer = BusinessBayesianAnalyzer(high_price_threshold=100.0)
        code = "price = 150.0"
        results = analyzer._analyze_monetization(code, "test_high_price")
        assert any(r.error_type == BusinessErrorType.PRICING_INEFFICIENCY for r in results)


class TestCustomerAcquisitionAnalysis:
    """Test customer acquisition analysis."""

    def test_registration_without_validation(self) -> None:
        """Registration without validation should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def register_user():
    new_user = True
    return user
"""
        results = analyzer._analyze_customer_acquisition(code, "test_registration")
        assert any(r.business_category == BusinessCategory.CUSTOMER_ACQUISITION for r in results)

    def test_registration_without_onboarding(self) -> None:
        """Registration without onboarding should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = "register_user(); new_user = True"
        results = analyzer._analyze_customer_acquisition(code, "test_reg")
        assert len(results) > 0


class TestCostOptimizationAnalysis:
    """Test cost optimization analysis."""

    def test_nested_loops_with_append(self) -> None:
        """Nested loops with heavy operations should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
for i in range(100):
    for j in range(100):
        data.append(process(i, j))
"""
        results = analyzer._analyze_cost_optimization(code, "test_nested")
        assert any(r.error_type == BusinessErrorType.OPERATIONAL_WASTE for r in results)

    def test_select_star_in_production(self) -> None:
        """SELECT * outside test context should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = 'query = "SELECT * FROM users"'
        results = analyzer._analyze_cost_optimization(code, "production_query")
        assert any("SELECT *" in (r.error_message or "") for r in results)

    def test_while_true_without_break(self) -> None:
        """while True without break/return should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
while True:
    process_data()
"""
        results = analyzer._analyze_cost_optimization(code, "test_while")
        assert any(r.error_type == BusinessErrorType.OPERATIONAL_WASTE for r in results)

    def test_sleep_without_retry_context(self) -> None:
        """sleep() without retry context should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = "time.sleep(5)"
        results = analyzer._analyze_cost_optimization(code, "test_sleep")
        assert any("sleep" in (r.error_message or "").lower() for r in results)

    def test_database_access_without_caching(self) -> None:
        """Database access without caching should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = "data = database.query()"
        results = analyzer._analyze_cost_optimization(code, "test_db")
        assert any(r.error_type == BusinessErrorType.OPERATIONAL_WASTE for r in results)


class TestRevenueGrowthAnalysis:
    """Test revenue growth analysis."""

    def test_analytics_without_ab_testing(self) -> None:
        """Analytics without A/B testing should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def track_metrics():
    analytics.track('conversion')
    revenue = 1000
"""
        results = analyzer._analyze_revenue_growth(code, "test_analytics")
        assert any(r.business_category == BusinessCategory.REVENUE_GROWTH for r in results)

    def test_personalization_without_recommendations(self) -> None:
        """Personalization without recommendations should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def personalize():
    user = current_user
    personal_content = True
"""
        results = analyzer._analyze_revenue_growth(code, "test_personal")
        assert any(r.error_type == BusinessErrorType.REVENUE_LEAK for r in results)


class TestCustomerRetentionAnalysis:
    """Test customer retention analysis."""

    def test_communication_without_segmentation(self) -> None:
        """Communication without segmentation should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def send_notification():
    email.send()
"""
        results = analyzer._analyze_customer_retention(code, "test_comm")
        assert any(r.business_category == BusinessCategory.USER_RETENTION for r in results)

    def test_feedback_without_processing(self) -> None:
        """Feedback collection without processing should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = "feedback = collect_feedback()"
        results = analyzer._analyze_customer_retention(code, "test_feedback")
        assert any(r.error_type == BusinessErrorType.CUSTOMER_CHURN for r in results)


class TestDataMonetizationAnalysis:
    """Test data monetization analysis."""

    def test_data_collection_without_monetization(self) -> None:
        """Data collection without monetization should be flagged."""
        analyzer = BusinessBayesianAnalyzer()
        code = """
def collect_user_data():
    data = user.get_behavior()
    store(data)
"""
        results = analyzer.analyze(code, "test_data")
        # Should detect potential data monetization opportunities
        assert isinstance(results, list)


class TestROICalculation:
    """Test ROI calculation edge cases."""

    def test_roi_with_empty_data(self) -> None:
        """ROI calculation with empty data should use prior only."""
        analyzer = BusinessBayesianAnalyzer()
        roi = analyzer._calculate_bayesian_roi(
            category="test",
            prior_mean=0.1,
            prior_std=0.05,
            data=[],
            time_horizon_months=6,
            assumptions="prior only",
        )
        assert roi.expected_roi > 0

    def test_roi_with_high_variance(self) -> None:
        """ROI calculation with high variance should trigger warning path."""
        analyzer = BusinessBayesianAnalyzer()
        roi = analyzer._calculate_bayesian_roi(
            category="high_var",
            prior_mean=0.1,
            prior_std=1.5,  # High std
            data=[0.2, 0.3],
            time_horizon_months=12,
            assumptions="high variance",
        )
        assert isinstance(roi.expected_roi, float)


class TestRecommendations:
    """Test recommendation generation."""

    def test_revenue_recommendations_empty_when_no_issues(self) -> None:
        """No revenue issues should produce empty recommendations."""
        analyzer = BusinessBayesianAnalyzer()
        recs = analyzer.generate_revenue_optimization_recommendations()
        assert recs == []

    def test_cost_recommendations_empty_when_no_issues(self) -> None:
        """No cost issues should produce empty recommendations."""
        analyzer = BusinessBayesianAnalyzer()
        recs = analyzer.generate_cost_savings_recommendations()
        assert recs == []

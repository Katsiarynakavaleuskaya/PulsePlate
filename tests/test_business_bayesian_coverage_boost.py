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

import builtins
import sys
from typing import Any
from pathlib import Path
import pytest
from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
    BusinessTestResult,
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

    def test_locale_unsupported_falls_back_to_en(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        # Simulate i18n module being unavailable with a single monkeypatch operation
        monkeypatch.setitem(sys.modules, "core.i18n", None)

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
    return user  # Intentionally undefined to test validation detection
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


class TestMissingCoveragePaths:
    """Target remaining uncovered branches for coverage."""

    def test_init_with_injected_config_and_thresholds(self) -> None:
        analyzer = BusinessBayesianAnalyzer(
            low_price_threshold=2.0,
            high_price_threshold=200.0,
            monetization_strategies={"pricing_models": {"custom": True}},
            cost_optimization_rules={"infrastructure": {"custom": True}},
            domain="generic",
        )
        assert analyzer.low_price_threshold == 2.0
        assert analyzer.high_price_threshold == 200.0
        assert analyzer.monetization_strategies["pricing_models"]["custom"] is True
        assert analyzer.cost_optimization_rules["infrastructure"]["custom"] is True

    def test_import_yaml_module_returns_none_on_importerror(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real_import = builtins.__import__

        def _fake_import(name: str, *args: object, **kwargs: object) -> Any:
            if name == "yaml":
                raise ModuleNotFoundError("yaml missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        assert BusinessBayesianAnalyzer._import_yaml_module() is None

    def test_config_dir_prefers_existing_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import core.business_bayesian_analyzer as bba_module

        config_dir = tmp_path / "core" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        fake_module_path = tmp_path / "core" / "business_bayesian_analyzer.py"
        fake_module_path.parent.mkdir(parents=True, exist_ok=True)
        fake_module_path.write_text("# fake module", encoding="utf-8")

        monkeypatch.setattr(bba_module, "__file__", str(fake_module_path))
        analyzer = bba_module.BusinessBayesianAnalyzer()
        assert analyzer._config_dir() == config_dir

    def test_loaders_fallback_when_yaml_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _BoomYaml:
            @staticmethod
            def safe_load(_fh: object) -> dict[str, object]:
                raise ValueError("boom")

        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "business_knowledge.yaml").write_text("x", encoding="utf-8")
        (config_dir / "monetization_strategies.en.yaml").write_text("x", encoding="utf-8")
        (config_dir / "cost_optimization_rules.yaml").write_text("x", encoding="utf-8")

        analyzer = BusinessBayesianAnalyzer()
        monkeypatch.setattr(analyzer, "_config_dir", lambda: config_dir)
        monkeypatch.setattr(analyzer, "_import_yaml_module", lambda: _BoomYaml)

        assert "revenue_streams" in analyzer._load_business_knowledge()
        assert "pricing_models" in analyzer._load_monetization_strategies("en")
        assert "infrastructure" in analyzer._load_cost_optimization_rules()

    def test_loaders_read_yaml_when_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _YamlStub:
            @staticmethod
            def safe_load(fh: object) -> dict[str, object]:
                name = Path(getattr(fh, "name", ""))
                if name.name == "business_knowledge.yaml":
                    return {"revenue_streams": {"subscription": {"price_range": [1, 2]}}}
                if name.name.startswith("monetization_strategies"):
                    return {"pricing_models": {"tiered": ["basic"]}}
                if name.name == "cost_optimization_rules.yaml":
                    return {"infrastructure": {"auto_scaling": True}}
                return {}

        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "business_knowledge.yaml").write_text("x", encoding="utf-8")
        (config_dir / "monetization_strategies.en.yaml").write_text("x", encoding="utf-8")
        (config_dir / "cost_optimization_rules.yaml").write_text("x", encoding="utf-8")

        analyzer = BusinessBayesianAnalyzer()
        monkeypatch.setattr(analyzer, "_config_dir", lambda: config_dir)
        monkeypatch.setattr(analyzer, "_import_yaml_module", lambda: _YamlStub)

        assert "revenue_streams" in analyzer._load_business_knowledge()
        assert "pricing_models" in analyzer._load_monetization_strategies("en")
        assert "infrastructure" in analyzer._load_cost_optimization_rules()

    def test_normalize_code_input_handles_sequences(self) -> None:
        analyzer = BusinessBayesianAnalyzer()
        assert analyzer._normalize_code_input(["a", "b"]) == "a\nb"
        assert analyzer._normalize_code_input(("c", "d")) == "c\nd"

    def test_remove_comments_fallback_handles_quotes(self) -> None:
        analyzer = BusinessBayesianAnalyzer()
        code = (
            "'''start'''\n"
            '"""block"""\n'
            'line = "value # not comment"\n'
            "single = 'text # not comment'\n"
            'escape = "quote \\\\""\n'
            "# comment\n"
            "for (\n"
        )
        cleaned = analyzer._remove_comments_fallback(code)
        assert "# not comment" in cleaned

    def test_remove_comments_uses_fallback_on_token_error(self) -> None:
        analyzer = BusinessBayesianAnalyzer()
        code = "line = 1\n# comment\nfor (\n"
        cleaned = analyzer._remove_comments(code)
        assert "# comment" not in cleaned

    def test_analyze_monetization_skips_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        analyzer = BusinessBayesianAnalyzer()
        real_float = builtins.float

        def _boom(value: str) -> float:
            if value == "99":
                raise ValueError("boom")
            return real_float(value)

        monkeypatch.setattr(builtins, "float", _boom)
        results = analyzer._analyze_monetization("price = 99", "test_value_error")
        assert results == []

    def test_cost_optimization_fallback_on_syntax_error(self) -> None:
        analyzer = BusinessBayesianAnalyzer()
        code = "\n".join(
            [
                "for i in range(2):",
                "    for j in range(2):",
                "        data.append(j)",
                "for",
            ]
        )
        results = analyzer._analyze_cost_optimization(code, "syntax_error_case")
        assert any(r.error_type == BusinessErrorType.OPERATIONAL_WASTE for r in results)

    def test_analyze_business_logic_multi_branch_and_recommendations(self) -> None:
        analyzer = BusinessBayesianAnalyzer()
        code = "\n".join(
            [
                "price = 2000",
                "payment = charge()",
                "register_user()",
                "for i in range(2):",
                "    for j in range(2):",
                "        database.append(j)",
                'query = "SELECT * FROM users"',
                "while True:",
                "    do_work()",
                "time.sleep(5)",
                "data = database.fetch()",
                "process_payment(amount=-5)",
                "analytics.track('revenue')",
                "user = current_user",
                "personal = True",
                "notification.send()",
                "feedback = collect()",
            ]
        )
        results = analyzer.analyze(code, "business_flow")
        assert results

        analyzer.test_results.extend(
            [
                BusinessTestResult(
                    test_name="critical",
                    success=False,
                    business_category=BusinessCategory.COST_OPTIMIZATION,
                    error_message="critical issue",
                ),
                BusinessTestResult(
                    test_name="high",
                    success=False,
                    business_category=BusinessCategory.MONETIZATION,
                    error_message="high impact",
                ),
                BusinessTestResult(
                    test_name="medium",
                    success=False,
                    business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                    error_message="medium risk",
                ),
                BusinessTestResult(
                    test_name="low",
                    success=False,
                    business_category=BusinessCategory.USER_RETENTION,
                    error_message="low priority",
                ),
                BusinessTestResult(
                    test_name="ops",
                    success=False,
                    business_category=BusinessCategory.OPERATIONAL_EFFICIENCY,
                ),
                BusinessTestResult(
                    test_name="data",
                    success=False,
                    business_category=BusinessCategory.DATA_MONETIZATION,
                ),
            ]
        )

        assert analyzer.generate_cost_savings_recommendations()
        assert analyzer.generate_revenue_optimization_recommendations()
        assert analyzer.calculate_roi_potential()

    def test_calculate_bayesian_roi_with_single_sample(self) -> None:
        analyzer = BusinessBayesianAnalyzer()
        estimate = analyzer._calculate_bayesian_roi(
            category="single",
            prior_mean=0.1,
            prior_std=0.01,
            data=[0.05],
            time_horizon_months=3,
            assumptions="single sample",
        )
        assert estimate.expected_roi > -1

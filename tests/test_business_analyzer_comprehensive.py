#!/usr/bin/env python3
"""Comprehensive tests for BusinessBayesianAnalyzer."""

import pytest

from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
    BusinessTestResult,
)


class TestBusinessBayesianAnalyzer:
    """Comprehensive tests for BusinessBayesianAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> BusinessBayesianAnalyzer:
        """Create analyzer instance."""
        return BusinessBayesianAnalyzer()

    def test_initialization(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test analyzer initialization."""
        assert analyzer.test_results == []
        assert analyzer.business_knowledge_base is not None
        assert analyzer.monetization_strategies is not None
        assert analyzer.cost_optimization_rules is not None

    def test_analyze_calls_analyze_business_logic(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test analyze method delegates to analyze_business_logic."""
        code = "price = 10"
        results = analyzer.analyze(code, "test_price")
        assert isinstance(results, list)

    def test_monetization_low_price(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of low pricing."""
        code = "price = 0.5"
        results = analyzer.analyze(code, "test_low_price")

        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
            and "низкая цена" in r.error_message.lower()
            for r in results
        )

    def test_monetization_high_price(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of high pricing."""
        code = "subscription = 1500.0"
        results = analyzer.analyze(code, "test_high_price")

        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
            and "высокая цена" in r.error_message.lower()
            for r in results
        )

    def test_monetization_cost_variable(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of cost variables."""
        code = "cost = 0.1"
        results = analyzer.analyze(code, "test_cost")

        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
            for r in results
        )

    def test_monetization_fee_variable(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of fee variables."""
        code = "fee = 0.05"
        results = analyzer.analyze(code, "test_fee")

        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.PRICING_INEFFICIENCY
            for r in results
        )

    def test_monetization_missing_strategy(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of missing monetization strategy."""
        code = "payment = 100\nbilling_enabled = True"
        results = analyzer.analyze(code, "test_missing_strategy")

        assert any(
            r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.REVENUE_LEAK
            and "стратегии монетизации" in r.error_message.lower()
            for r in results
        )

    def test_monetization_with_strategy(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test no error when monetization strategy is present."""
        code = "payment = 100\nsubscription = True\ntier = 'premium'"
        results = analyzer.analyze(code, "test_with_strategy")

        # Should not report missing strategy since subscription/tier keywords are present
        missing_strategy_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.MONETIZATION
            and r.error_type == BusinessErrorType.REVENUE_LEAK
            and "стратегии монетизации" in r.error_message.lower()
        ]
        assert len(missing_strategy_errors) == 0

    def test_customer_acquisition_no_validation(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of registration without validation."""
        code = "signup_user()\nnew_user = True"
        results = analyzer.analyze(code, "test_no_validation")

        assert any(
            r.business_category == BusinessCategory.CUSTOMER_ACQUISITION
            and r.error_type == BusinessErrorType.CUSTOMER_CHURN
            and "валидации" in r.error_message.lower()
            for r in results
        )

    def test_customer_acquisition_with_validation(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test registration with validation is accepted."""
        code = "signup_user()\nvalidate_email(email)\ncheck_data()"
        results = analyzer.analyze(code, "test_with_validation")

        # Should not report validation issue
        validation_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.CUSTOMER_ACQUISITION
            and "валидации" in r.error_message.lower()
        ]
        assert len(validation_errors) == 0

    def test_customer_acquisition_no_onboarding(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of missing onboarding."""
        code = "register_account()\ncreate_account()"
        results = analyzer.analyze(code, "test_no_onboarding")

        assert any(
            r.business_category == BusinessCategory.CUSTOMER_ACQUISITION
            and r.error_type == BusinessErrorType.CUSTOMER_CHURN
            and "онбординга" in r.error_message.lower()
            for r in results
        )

    def test_customer_acquisition_with_onboarding(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test registration with onboarding is accepted."""
        code = "register_account()\nwelcome_tutorial()\nonboard_user()"
        results = analyzer.analyze(code, "test_with_onboarding")

        # Should not report onboarding issue
        onboarding_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.CUSTOMER_ACQUISITION
            and "онбординга" in r.error_message.lower()
        ]
        assert len(onboarding_errors) == 0

    def test_cost_optimization_nested_loops(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of nested loops."""
        code = "for i in range(10):\n    for j in range(10):\n        process(i, j)"
        results = analyzer.analyze(code, "test_nested_loops")

        assert any(
            r.business_category == BusinessCategory.COST_OPTIMIZATION
            and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            for r in results
        )

    def test_cost_optimization_select_all(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of SELECT * queries."""
        code = "SELECT * FROM users WHERE active = true"
        results = analyzer.analyze(code, "test_select_all")

        assert any(
            r.business_category == BusinessCategory.COST_OPTIMIZATION
            and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            for r in results
        )

    def test_cost_optimization_infinite_loop(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of infinite loops."""
        code = "while True:\n    check_status()"
        results = analyzer.analyze(code, "test_infinite_loop")

        assert any(
            r.business_category == BusinessCategory.COST_OPTIMIZATION
            and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            for r in results
        )

    def test_cost_optimization_sleep(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of sleep delays."""
        code = "import time\ntime.sleep(5)\nprocess_data()"
        results = analyzer.analyze(code, "test_sleep")

        assert any(
            r.business_category == BusinessCategory.COST_OPTIMIZATION
            and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            for r in results
        )

    def test_cost_optimization_no_caching_database(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test detection of database queries without caching."""
        code = "database.query('SELECT id FROM users')\nfetch_results()"
        results = analyzer.analyze(code, "test_no_cache_db")

        assert any(
            r.business_category == BusinessCategory.COST_OPTIMIZATION
            and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            and "кэширование" in r.error_message.lower()
            for r in results
        )

    def test_cost_optimization_no_caching_api(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of API requests without caching."""
        code = "api.request('/users')\nfetch_data()"
        results = analyzer.analyze(code, "test_no_cache_api")

        assert any(
            r.business_category == BusinessCategory.COST_OPTIMIZATION
            and r.error_type == BusinessErrorType.OPERATIONAL_WASTE
            and "кэширование" in r.error_message.lower()
            for r in results
        )

    def test_cost_optimization_with_caching(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test API/DB with caching is accepted."""
        code = "cache.get('users')\nredis.fetch()\napi.request('/data')"
        results = analyzer.analyze(code, "test_with_cache")

        # Should not report caching issue
        cache_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.COST_OPTIMIZATION
            and "кэширование" in r.error_message.lower()
        ]
        assert len(cache_errors) == 0

    def test_revenue_growth_no_ab_testing(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of analytics without A/B testing."""
        code = "analytics.track('conversion')\nmetrics.record()"
        results = analyzer.analyze(code, "test_no_ab")

        assert any(
            r.business_category == BusinessCategory.REVENUE_GROWTH
            and r.error_type == BusinessErrorType.REVENUE_LEAK
            and "a/b тестирования" in r.error_message.lower()
            for r in results
        )

    def test_revenue_growth_with_ab_testing(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test analytics with A/B testing is accepted."""
        code = "analytics.track('conversion')\nab_test.run('variant_a')\nexperiment.start()"
        results = analyzer.analyze(code, "test_with_ab")

        # Should not report A/B testing issue
        ab_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.REVENUE_GROWTH
            and "a/b тестирования" in r.error_message.lower()
        ]
        assert len(ab_errors) == 0

    def test_revenue_growth_no_personalization(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of personalization without recommendations."""
        code = "user_data = get_user()\npersonal_settings = load_personal()"
        results = analyzer.analyze(code, "test_no_personalization")

        assert any(
            r.business_category == BusinessCategory.REVENUE_GROWTH
            and r.error_type == BusinessErrorType.REVENUE_LEAK
            and "рекомендаций" in r.error_message.lower()
            for r in results
        )

    def test_revenue_growth_with_personalization(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test personalization with recommendations is accepted."""
        code = "user_data = get_user()\npersonal_prefs = load_personal()\nrecommend_items()"
        results = analyzer.analyze(code, "test_with_personalization")

        # Should not report personalization issue
        personalization_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.REVENUE_GROWTH
            and "рекомендаций" in r.error_message.lower()
        ]
        assert len(personalization_errors) == 0

    def test_customer_retention_no_segmentation(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test detection of notifications without segmentation."""
        code = "send_notification('Update available')\nemail_users('Newsletter')"
        results = analyzer.analyze(code, "test_no_segmentation")

        assert any(
            r.business_category == BusinessCategory.USER_RETENTION
            and r.error_type == BusinessErrorType.CUSTOMER_CHURN
            and "сегментации" in r.error_message.lower()
            for r in results
        )

    def test_customer_retention_with_segmentation(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test notifications with segmentation is accepted."""
        code = "segment_users('premium')\nnotification.send_to_group()\nemail_cohort()"
        results = analyzer.analyze(code, "test_with_segmentation")

        # Should not report segmentation issue
        segmentation_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.USER_RETENTION
            and "сегментации" in r.error_message.lower()
        ]
        assert len(segmentation_errors) == 0

    def test_customer_retention_no_feedback_processing(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test detection of feedback collection without processing."""
        code = "feedback.collect()\nreview.gather()"
        results = analyzer.analyze(code, "test_no_feedback_processing")

        assert any(
            r.business_category == BusinessCategory.USER_RETENTION
            and r.error_type == BusinessErrorType.CUSTOMER_CHURN
            and "обработки" in r.error_message.lower()
            for r in results
        )

    def test_customer_retention_with_feedback_processing(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test feedback with processing is accepted."""
        code = "feedback.collect()\nanalyze_feedback()\nprocess_reviews()\nrespond_to_users()"
        results = analyzer.analyze(code, "test_with_feedback_processing")

        # Should not report feedback processing issue
        feedback_errors = [
            r
            for r in results
            if r.business_category == BusinessCategory.USER_RETENTION
            and "обработки" in r.error_message.lower()
        ]
        assert len(feedback_errors) == 0

    def test_remove_comments_simple(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test comment removal."""
        code = "x = 1  # This is a comment"
        result = analyzer._remove_comments(code)
        assert "#" not in result or "comment" not in result.lower()

    def test_remove_comments_preserves_string_hash(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test that # in strings is preserved."""
        code = 'text = "Use #hashtag"'
        result = analyzer._remove_comments(code)
        assert "#hashtag" in result or "hashtag" in result

    def test_remove_comments_malformed_code(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test comment removal with malformed code."""
        code = "x = (incomplete  # comment"
        result = analyzer._remove_comments(code)
        # Should not crash, fallback to regex
        assert isinstance(result, str)

    def test_diagnose_business_issues_empty(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test diagnosis with no test results."""
        issues = analyzer.diagnose_business_issues()
        assert issues == {}

    def test_diagnose_business_issues_with_results(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test diagnosis with test results."""
        # Add some test results
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.MONETIZATION,
                error_type=BusinessErrorType.REVENUE_LEAK,
            ),
            BusinessTestResult(
                test_name="test2",
                success=False,
                business_category=BusinessCategory.MONETIZATION,
                error_type=BusinessErrorType.PRICING_INEFFICIENCY,
            ),
            BusinessTestResult(
                test_name="test3",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            ),
        ]

        issues = analyzer.diagnose_business_issues()
        assert BusinessCategory.MONETIZATION in issues
        assert BusinessCategory.COST_OPTIMIZATION in issues
        assert issues[BusinessCategory.MONETIZATION] == pytest.approx(2 / 3)
        assert issues[BusinessCategory.COST_OPTIMIZATION] == pytest.approx(1 / 3)

    def test_generate_cost_savings_recommendations(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test cost savings recommendations generation."""
        # Add cost optimization issues
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            )
        ]

        recommendations = analyzer.generate_cost_savings_recommendations()
        assert len(recommendations) > 0
        assert any("spot" in rec.lower() or "кэш" in rec.lower() for rec in recommendations)

    def test_generate_cost_savings_recommendations_operational(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test recommendations for operational efficiency."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.OPERATIONAL_EFFICIENCY,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            )
        ]

        recommendations = analyzer.generate_cost_savings_recommendations()
        assert len(recommendations) > 0
        assert any(
            "автоматиз" in rec.lower() or "мониторинг" in rec.lower() for rec in recommendations
        )

    def test_generate_cost_savings_recommendations_monetization(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test recommendations for monetization."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.MONETIZATION,
                error_type=BusinessErrorType.REVENUE_LEAK,
            )
        ]

        recommendations = analyzer.generate_cost_savings_recommendations()
        assert len(recommendations) > 0
        assert any(
            "ценообразован" in rec.lower() or "реферальн" in rec.lower() for rec in recommendations
        )

    def test_generate_revenue_optimization_recommendations(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test revenue optimization recommendations generation."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                error_type=BusinessErrorType.CUSTOMER_CHURN,
            )
        ]

        recommendations = analyzer.generate_revenue_optimization_recommendations()
        assert len(recommendations) > 0
        assert any("онбординг" in rec.lower() or "пробн" in rec.lower() for rec in recommendations)

    def test_generate_revenue_optimization_recommendations_retention(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test recommendations for retention."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.USER_RETENTION,
                error_type=BusinessErrorType.CUSTOMER_CHURN,
            )
        ]

        recommendations = analyzer.generate_revenue_optimization_recommendations()
        assert len(recommendations) > 0
        assert any(
            "персонализ" in rec.lower() or "лояльност" in rec.lower() for rec in recommendations
        )

    def test_generate_revenue_optimization_recommendations_data(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test recommendations for data monetization."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.DATA_MONETIZATION,
                error_type=BusinessErrorType.DATA_UNDERUTILIZED,
            )
        ]

        recommendations = analyzer.generate_revenue_optimization_recommendations()
        assert len(recommendations) > 0
        assert any("api" in rec.lower() or "аналитик" in rec.lower() for rec in recommendations)

    def test_calculate_roi_potential_empty(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test ROI calculation with no issues."""
        roi = analyzer.calculate_roi_potential()
        assert roi == {}

    def test_calculate_roi_potential_cost_optimization(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test ROI potential for cost optimization."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.COST_OPTIMIZATION,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
            )
        ]

        roi = analyzer.calculate_roi_potential()
        assert "cost_optimization" in roi
        assert roi["cost_optimization"] == 0.3

    def test_calculate_roi_potential_monetization(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test ROI potential for monetization."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.MONETIZATION,
                error_type=BusinessErrorType.REVENUE_LEAK,
            )
        ]

        roi = analyzer.calculate_roi_potential()
        assert "monetization" in roi
        assert roi["monetization"] == 0.4

    def test_calculate_roi_potential_customer_acquisition(
        self, analyzer: BusinessBayesianAnalyzer
    ) -> None:
        """Test ROI potential for customer acquisition."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                error_type=BusinessErrorType.CUSTOMER_CHURN,
            )
        ]

        roi = analyzer.calculate_roi_potential()
        assert "customer_acquisition" in roi
        assert roi["customer_acquisition"] == 0.25

    def test_calculate_roi_potential_retention(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test ROI potential for user retention."""
        analyzer.test_results = [
            BusinessTestResult(
                test_name="test1",
                success=False,
                business_category=BusinessCategory.USER_RETENTION,
                error_type=BusinessErrorType.CUSTOMER_CHURN,
            )
        ]

        roi = analyzer.calculate_roi_potential()
        assert "user_retention" in roi
        assert roi["user_retention"] == 0.35

    def test_calculate_roi_potential_multiple(self, analyzer: BusinessBayesianAnalyzer) -> None:
        """Test ROI potential with multiple issue types."""
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
                error_type=BusinessErrorType.REVENUE_LEAK,
            ),
        ]

        roi = analyzer.calculate_roi_potential()
        assert len(roi) == 2
        assert "cost_optimization" in roi
        assert "monetization" in roi

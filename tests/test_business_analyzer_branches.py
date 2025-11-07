from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
)


def test_monetization_missing_strategy_branch() -> None:
    analyzer = BusinessBayesianAnalyzer()
    code = "payment = 10  # billing present, but no plan/tier/subscription keywords"
    results = analyzer._analyze_monetization(code, "test_monetization")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.REVENUE_LEAK
        for r in results
    )

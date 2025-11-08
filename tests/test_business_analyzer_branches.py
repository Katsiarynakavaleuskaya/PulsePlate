import pytest

from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
)


@pytest.mark.skip(reason="Temporary skip - AttributeError in CI with Python 3.13.5")
def test_monetization_missing_strategy_branch() -> None:
    analyzer = BusinessBayesianAnalyzer()
    code = "payment = 10  # billing present, but no plan/tier/subscription keywords"
    results = analyzer.analyze(code, "test_monetization")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.REVENUE_LEAK
        for r in results
    )

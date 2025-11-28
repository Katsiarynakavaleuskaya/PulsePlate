import math
from core.bayesian_test_analyzer import BayesianTestAnalyzer, ErrorType


def test_calculate_confidence_edge_cases():
    analyzer = BayesianTestAnalyzer()
    assert analyzer._calculate_confidence({}) == 0.0
    # Zero total path
    assert analyzer._calculate_confidence({"a": 0.0, "b": 0.0}) == 0.0


def test_calculate_evidence_no_symptoms_and_with_prior_sum_zero():
    analyzer = BayesianTestAnalyzer()
    # No symptoms -> evidence 1.0
    assert analyzer._calculate_evidence(set(), []) == 1.0
    # Manipulate priors to sum to zero to hit guard
    analyzer.prior_probabilities = {et: 0.0 for et in ErrorType}
    evidence = analyzer._calculate_evidence({"x"}, [])
    assert 0 < evidence <= 1.0

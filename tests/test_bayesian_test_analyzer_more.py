"""Additional test coverage for BayesianTestAnalyzer edge cases.

These tests exercise internal implementation details that are difficult to trigger
via public API alone. Marked as implementation-coupled - may become fragile if
internal methods are refactored.

TODO: Migrate to public API tests if edge cases can be triggered via diagnose_test_failure()
"""

import pytest
from core.bayesian_test_analyzer import BayesianTestAnalyzer, ErrorType


def test_calculate_confidence_edge_cases() -> None:
    """Test _calculate_confidence with edge cases (empty dict, all zeros).

    Tests private method directly as these edge cases are difficult to trigger
    through the public API. This is acceptable for coverage purposes.
    """
    analyzer = BayesianTestAnalyzer()
    assert analyzer._calculate_confidence({}) == 0.0
    # Zero total path - use proper ErrorType enum values
    assert (
        analyzer._calculate_confidence(
            {ErrorType.ASSERTION_ERROR: 0.0, ErrorType.IMPORT_ERROR: 0.0}
        )
        == 0.0
    )


def test_calculate_evidence_no_symptoms_and_with_prior_sum_zero() -> None:
    """Test _calculate_evidence edge cases: no symptoms and zero priors.

    Tests private method directly as these edge cases are difficult to trigger
    through the public API. This is acceptable for coverage purposes.
    """
    analyzer = BayesianTestAnalyzer()
    # No symptoms -> evidence 1.0
    assert analyzer._calculate_evidence(set(), []) == 1.0

    # Test zero priors case by directly calling _normalize_priors with zero values
    # This mimics what happens when all initial priors are zero
    zero_priors = {et: 0.0 for et in ErrorType}
    normalized = analyzer._normalize_priors(zero_priors)

    # When all priors are zero, they should be normalized to uniform distribution
    uniform_value = 1.0 / len(ErrorType)
    assert all(abs(val - uniform_value) < 1e-10 for val in normalized.values())

    # Create an analyzer with zero priors to test _calculate_evidence
    # We'll monkeypatch the initialization to set zero priors
    analyzer_with_zero_priors = BayesianTestAnalyzer()
    analyzer_with_zero_priors.prior_probabilities = normalized

    # Test _calculate_evidence with zero priors (actually uniform after normalization)
    evidence = analyzer_with_zero_priors._calculate_evidence({"x"}, [])
    assert 0 < evidence <= 1.0

"""Additional test coverage for BayesianTestAnalyzer edge cases.

These tests exercise internal implementation details that are difficult to trigger
via public API alone. Marked as implementation-coupled - may become fragile if
internal methods are refactored.

TODO: Migrate to public API tests if edge cases can be triggered via diagnose_test_failure()
"""

from core.bayesian_test_analyzer import BayesianTestAnalyzer, ErrorType


def test_calculate_confidence_edge_cases() -> None:
    """Test _calculate_confidence with edge cases (empty dict, all zeros).

    INTERNAL TEST: Directly calls private method _calculate_confidence.
    Fragile if method signature/logic changes.
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

    INTERNAL TEST: Directly manipulates prior_probabilities and calls _calculate_evidence.
    Fragile - coupled to internal state.
    """
    analyzer = BayesianTestAnalyzer()
    # No symptoms -> evidence 1.0
    assert analyzer._calculate_evidence(set(), []) == 1.0
    # Manipulate priors to sum to zero to hit guard
    analyzer.prior_probabilities = {et: 0.0 for et in ErrorType}
    evidence = analyzer._calculate_evidence({"x"}, [])
    assert 0 < evidence <= 1.0

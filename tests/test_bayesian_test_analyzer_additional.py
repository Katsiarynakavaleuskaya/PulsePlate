from datetime import datetime, timedelta, timezone

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestRecord,
    TestStatus,
    get_analyzer,
    record_test_execution,
    reset_analyzer,
)


def test_diagnose_test_failure_defaults_and_confidence_single_entry() -> None:
    analyzer = BayesianTestAnalyzer()
    diagnosis = analyzer.diagnose_test_failure("t1", "some error")
    assert diagnosis is not None
    # Verify that confidence is exposed via public API
    assert hasattr(diagnosis, "confidence")
    assert 0.0 <= diagnosis.confidence <= 1.0


def test_calculate_likelihood_empty_symptoms_and_history_similarity() -> None:
    """Test likelihood calculation with empty symptoms via public API."""
    analyzer = BayesianTestAnalyzer()
    record = TestRecord(
        test_name="t2",
        category=TestCategory.UNIT,
        result=TestStatus.FAILED,
        error_type=ErrorType.RUNTIME_ERROR,
        error_message="",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    analyzer.execution_history.append(record)

    # Test via public API: diagnose_test_failure with empty error message
    # This exercises the empty symptoms path through the public interface
    diagnosis = analyzer.diagnose_test_failure("t2", "")
    assert diagnosis is not None
    assert diagnosis.most_likely_cause in ErrorType


def test_record_and_reset_global_analyzer() -> None:
    # Use module-level helpers to cover get_analyzer/reset_analyzer paths
    record_test_execution(
        "t3",
        TestCategory.INTEGRATION,
        TestStatus.PASSED,
        error_type=None,
        execution_time=0.0,
    )
    first = get_analyzer()
    reset_analyzer()
    second = get_analyzer()
    assert first is not second

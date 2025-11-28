import math
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


def test_diagnose_test_failure_defaults_and_confidence_single_entry():
    analyzer = BayesianTestAnalyzer()
    diagnosis = analyzer.diagnose_test_failure("t1", "some error")
    assert diagnosis is not None
    # _calculate_confidence with a single probability returns 1.0
    assert math.isclose(analyzer._calculate_confidence({ErrorType.RUNTIME_ERROR: 1.0}), 1.0)


def test_calculate_likelihood_empty_symptoms_and_history_similarity():
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

    # Empty symptoms + empty error_message should hit similarity shortcut branch
    prob = analyzer._calculate_likelihood(set(), ErrorType.RUNTIME_ERROR, similar_cases=[])
    assert 0.0 < prob <= 1.0


def test_record_and_reset_global_analyzer():
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

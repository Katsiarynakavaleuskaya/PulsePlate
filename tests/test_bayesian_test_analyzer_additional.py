import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pytest import MonkeyPatch

import core.bayesian_test_analyzer as bayesian_test_analyzer
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


def test_diagnose_test_failure_empty_symptoms_with_history() -> None:
    """Test diagnose_test_failure with empty symptoms using history via public API."""
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
    # Verify most_likely_cause corresponds to a valid ErrorType value
    assert diagnosis.most_likely_cause in {e.value for e in ErrorType}


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


def test_module_record_execution_persists_without_reentrant_deadlock(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    monkeypatch.setattr(bayesian_test_analyzer, "bayesian_analyzer", analyzer)

    completed: list[bool] = []

    def record_with_persistence() -> None:
        record_test_execution(
            "persisted-test",
            TestCategory.UNIT,
            TestStatus.PASSED,
            execution_time=0.01,
        )
        completed.append(True)

    thread = threading.Thread(target=record_with_persistence, daemon=True)
    thread.start()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert completed == [True]
    payload = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert payload[0]["test_name"] == "persisted-test"


def test_shard_history_io_disable_keeps_persisted_env_stateless(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    history_path = tmp_path / "history.json"
    monkeypatch.setenv("BAYESIAN_PERSIST", "1")
    monkeypatch.setenv("BAYESIAN_HISTORY_PATH", str(history_path))
    monkeypatch.setenv("PULSEPLATE_DISABLE_BAYESIAN_HISTORY_IO", "1")

    analyzer = BayesianTestAnalyzer()
    analyzer.record_test_execution(
        TestRecord(
            test_name="isolated-test",
            category=TestCategory.UNIT,
            result=TestStatus.PASSED,
        )
    )

    fresh_analyzer = BayesianTestAnalyzer()
    assert not history_path.exists()
    assert fresh_analyzer.test_history == []

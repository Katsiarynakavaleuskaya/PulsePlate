"""
Unit tests for core.bayesian_test_analyzer helpers.

RU: Плотно проверяем вспомогательные методы BayesianTestAnalyzer, чтобы
поднять покрытие и зафиксировать граничные случаи.
EN: Focused unit tests exercising BayesianTestAnalyzer helper branches for
higher coverage and edge-case confidence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import json

import pytest

from core.bayesian_test_analyzer import (
    BayesianDiagnosis,
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestRecord,
    TestStatus,
)


def _make_record(
    *,
    test_name: str,
    result: TestStatus,
    error_type: ErrorType | None = None,
    coverage: float | None = None,
    execution_time: float = 0.0,
    timestamp: datetime | None = None,
    error_message: str | None = None,
) -> TestRecord:
    """
    Helper to create TestRecord instances with bilingual comment.

    RU: Упрощает подготовку тестовых записей.
    EN: Simplifies constructing test records for analyzer state.
    """

    resolved_timestamp = timestamp or datetime.now(timezone.utc)
    resolved_dependencies: list[str] = []

    return TestRecord(
        test_name=test_name,
        category=TestCategory.UNIT,
        result=result,
        error_type=error_type,
        error_message=error_message,
        execution_time=execution_time,
        coverage_percentage=coverage,
        timestamp=resolved_timestamp,
        dependencies=resolved_dependencies,
    )


def test_normalize_priors_uniform_fallback() -> None:
    """RU/EN: Zero-weight priors should produce a uniform distribution."""

    priors = {error_type: 0.0 for error_type in ErrorType}
    normalized = BayesianTestAnalyzer._normalize_priors(priors)

    assert pytest.approx(sum(normalized.values())) == 1.0
    assert len(set(normalized.values())) == 1


def test_normalize_priors_scales_weights() -> None:
    """RU/EN: Non-zero priors should be normalized proportionally."""

    priors = {
        ErrorType.ASSERTION_ERROR: 2.0,
        ErrorType.IMPORT_ERROR: 1.0,
        ErrorType.TIMEOUT_ERROR: 1.0,
    }
    normalized = BayesianTestAnalyzer._normalize_priors(priors)

    assert pytest.approx(normalized[ErrorType.ASSERTION_ERROR]) == pytest.approx(0.5)
    assert pytest.approx(normalized[ErrorType.IMPORT_ERROR]) == pytest.approx(0.25)
    assert pytest.approx(normalized[ErrorType.TIMEOUT_ERROR]) == pytest.approx(0.25)


def test_test_record_defaults_fill_timestamp_and_dependencies() -> None:
    """RU/EN: Verify TestRecord fills missing timestamp/dependencies."""

    record = TestRecord(
        test_name="tests.sample::test_case",
        category=TestCategory.UNIT,
        result=TestStatus.PASSED,
        timestamp=None,  # type: ignore[arg-type]
        dependencies=None,  # type: ignore[arg-type]
    )
    assert record.timestamp.tzinfo is not None
    assert record.dependencies == []


def test_calculate_recency_weight_invalid_input_returns_one(tmp_path: Path) -> None:
    """RU/EN: Invalid timestamp should fall back to neutral weight."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    assert analyzer._calculate_recency_weight("not-a-datetime") == 1.0  # type: ignore[arg-type]


def test_load_history_reads_existing_file(tmp_path: Path) -> None:
    """RU/EN: Ensure persisted history is loaded during init."""

    history_path = tmp_path / "history.json"
    payload: Dict[str, object] = {
        "test_name": "suite::test_alpha",
        "category": TestCategory.UNIT.value,
        "result": TestStatus.FAILED.value,
        "error_type": ErrorType.ASSERTION_ERROR.value,
        "error_message": "AssertionError: boom",
        "execution_time": 0.3,
        "coverage_percentage": 75.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": [],
        "file_path": "tests/sample.py",
        "line_number": 42,
    }
    history_path.write_text(json.dumps([payload]), encoding="utf-8")

    analyzer = BayesianTestAnalyzer(data_file=history_path)
    assert analyzer.execution_history
    assert analyzer.execution_history[0].error_type == ErrorType.ASSERTION_ERROR


def test_refresh_priors_from_history_updates_weights(tmp_path: Path) -> None:
    """RU/EN: History-driven priors should blend with base priors."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    original_prior = analyzer.prior_probabilities[ErrorType.ASSERTION_ERROR]
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
    analyzer.execution_history = [
        _make_record(
            test_name="suite::test_failure",
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            timestamp=recent_time,
        )
    ]

    analyzer._refresh_priors_from_history()
    assert analyzer.prior_probabilities[ErrorType.ASSERTION_ERROR] != pytest.approx(original_prior)


def test_predict_failure_probability_applies_context(tmp_path: Path) -> None:
    """RU/EN: Context modifiers should increase failure probability."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::test_beta",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            execution_time=0.5,
            coverage=60.0,
        ),
        _make_record(
            test_name="suite::test_beta",
            result=TestStatus.PASSED,
            execution_time=0.2,
            coverage=70.0,
        ),
    ]

    probability = analyzer.predict_test_failure_probability(
        "suite::test_beta",
        {
            "recent_changes": True,
            "complex_dependencies": True,
            "async_test": True,
        },
    )
    assert probability > 0.1


def test_generate_test_report_builds_recommendations(tmp_path: Path) -> None:
    """RU/EN: Report should include recommendations for common errors."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    now = datetime.now(timezone.utc)
    analyzer.execution_history = [
        _make_record(
            test_name="suite::test_gamma",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            execution_time=0.6,
            coverage=55.0,
            timestamp=now - timedelta(hours=2),
        ),
        _make_record(
            test_name="suite::test_gamma",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            execution_time=0.4,
            coverage=50.0,
            timestamp=now - timedelta(hours=1),
        ),
        _make_record(
            test_name="suite::test_gamma",
            result=TestStatus.PASSED,
            execution_time=0.3,
            coverage=80.0,
            timestamp=now,
        ),
    ]

    report = analyzer.generate_test_report()
    assert isinstance(report, dict)
    assert report["failed_tests"] == 2
    assert any("Частая ошибка" in rec for rec in report["recommendations"])


def test_record_test_execution_persists_history(tmp_path: Path) -> None:
    """RU/EN: record_test_execution should append and persist records."""

    history_path = tmp_path / "history.json"
    analyzer = BayesianTestAnalyzer(data_file=history_path)
    record = _make_record(
        test_name="suite::test_delta",
        result=TestStatus.FAILED,
        error_type=ErrorType.ASSERTION_ERROR,
        execution_time=0.7,
        coverage=65.0,
    )

    analyzer.record_test_execution(record)
    assert analyzer.execution_history[-1].test_name == "suite::test_delta"
    persisted = json.loads(history_path.read_text(encoding="utf-8"))
    assert persisted[-1]["test_name"] == "suite::test_delta"


def test_diagnose_test_failure_returns_bayesian_diagnosis(tmp_path: Path) -> None:
    """RU/EN: Diagnose should return BayesianDiagnosis structure."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::test_eps",
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            execution_time=0.4,
            coverage=70.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
    ]
    diagnosis = analyzer.diagnose_test_failure(
        "suite::test_eps", "AssertionError: expected 1 got 2", {"is_async": True}
    )
    assert isinstance(diagnosis, BayesianDiagnosis)
    assert diagnosis.recommendations


def test_bayesian_analyzer_handles_degenerate_priors(tmp_path: Path) -> None:
    """RU/EN: Analyzer remains functional when priors become degenerate."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.prior_probabilities = {error_type: 0.0 for error_type in ErrorType}

    diagnosis = analyzer.diagnose_test_failure(
        "suite::degenerate", "AssertionError: fallback", {"is_async": True}
    )
    assert diagnosis.probability >= 0.0
    assert diagnosis.confidence >= 0.0


def test_get_test_health_score_variants(tmp_path: Path) -> None:
    """RU/EN: Cover health score branches for empty and single-history cases."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    assert analyzer.get_test_health_score("missing") == 0.5

    analyzer.execution_history = [
        _make_record(
            test_name="suite::health",
            result=TestStatus.PASSED,
            coverage=80.0,
            execution_time=0.0,
        )
    ]
    assert analyzer.get_test_health_score("suite::health") == pytest.approx(1.0)


def test_get_test_health_score_handles_zero_average_time(tmp_path: Path) -> None:
    """RU/EN: Time stability should default to 1.0 when average time is non-positive."""

    class TinyTime(float):
        """Float subclass that compares greater than zero but sums to zero."""

        def __new__(cls) -> "TinyTime":
            return float.__new__(cls, 0.0)

        def __gt__(self, other: float) -> bool:
            return True

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    tiny_time = TinyTime()
    analyzer.execution_history = [
        _make_record(
            test_name="suite::tiny_time",
            result=TestStatus.PASSED,
            coverage=80.0,
            execution_time=tiny_time,
        ),
        _make_record(
            test_name="suite::tiny_time",
            result=TestStatus.PASSED,
            coverage=85.0,
            execution_time=tiny_time,
        ),
    ]

    score = analyzer.get_test_health_score("suite::tiny_time")
    assert 0.0 <= score <= 1.0


def test_load_history_logs_warning_invalid_json(tmp_path: Path, caplog) -> None:
    """RU/EN: Invalid JSON should log warning and skip history load."""

    history_path = tmp_path / "broken.json"
    history_path.write_text("{ invalid", encoding="utf-8")
    with caplog.at_level("WARNING"):
        analyzer = BayesianTestAnalyzer(data_file=history_path)
    caplog.clear()
    history_path.write_text("{ invalid", encoding="utf-8")
    with caplog.at_level("WARNING"):
        analyzer.load_history()
    assert any("Не удалось загрузить историю тестов" in rec.message for rec in caplog.records)
    assert analyzer.execution_history == []


def test_save_history_logs_error_on_failure(tmp_path: Path, monkeypatch, caplog) -> None:
    """RU/EN: Save failures should log error message."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history.append(
        _make_record(
            test_name="suite::persist",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            coverage=50.0,
        )
    )

    def raising_open(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", raising_open)
    with caplog.at_level("ERROR"):
        analyzer.save_history()
    assert "Ошибка сохранения истории тестов" in caplog.text


def test_calculate_likelihood_similarity(tmp_path: Path) -> None:
    """RU/EN: Similarity-based likelihood should consider recent failures."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    now = datetime.now(timezone.utc)
    analyzer.execution_history = [
        _make_record(
            test_name="suite::symptoms",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            execution_time=0.5,
            coverage=45.0,
            timestamp=now - timedelta(hours=1),
            error_message="Mock error triggering asyncmock usage",
        ),
        _make_record(
            test_name="suite::symptoms",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            execution_time=0.4,
            coverage=55.0,
            timestamp=now - timedelta(hours=2),
            error_message="AsyncMock missing causes exception",
        ),
        _make_record(
            test_name="suite::symptoms",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            execution_time=0.1,
            coverage=60.0,
            timestamp=now,
            error_message="",
        ),
    ]
    symptoms = {"mock", "async"}
    similar_cases = analyzer.execution_history
    likelihood = analyzer._calculate_likelihood(symptoms, ErrorType.MOCK_ERROR, similar_cases)
    evidence = analyzer._calculate_evidence(symptoms, similar_cases)
    assert 0.0 < likelihood <= 1.0
    assert 0.0 < evidence <= 1.0

    likelihood_empty = analyzer._calculate_likelihood(set(), ErrorType.MOCK_ERROR, similar_cases)
    assert 0.0 < likelihood_empty <= 1.0


def test_generate_report_edge_cases(tmp_path: Path) -> None:
    """RU/EN: Edge-case history should produce safe report outputs."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::edge_pass",
            result=TestStatus.PASSED,
            error_type=None,
            coverage=None,
            execution_time=0.0,
        ),
        _make_record(
            test_name="suite::edge_fail",
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            coverage=None,
            execution_time=0.0,
            error_message="",
        ),
    ]
    report = analyzer.generate_test_report()
    assert "total_tests" in report
    assert report["failed_tests"] >= 0


def test_generate_report_with_failures(tmp_path: Path) -> None:
    """RU/EN: Report should include recommendations when failures dominate."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name=f"suite::fail_{i}",
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            coverage=None,
            execution_time=0.0,
            error_message="AssertionError occurred",
        )
        for i in range(5)
    ]
    analyzer.execution_history.append(
        _make_record(
            test_name="suite::pass_case",
            result=TestStatus.PASSED,
            error_type=None,
            coverage=None,
            execution_time=0.0,
        )
    )
    report = analyzer.generate_test_report()
    assert report["recommendations"]


def test_calculate_likelihood_no_symptoms(tmp_path: Path) -> None:
    """RU/EN: Likelihood should handle empty symptom sets gracefully."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::empty",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            coverage=None,
            execution_time=0.0,
            error_message="",
        )
    ]
    value = analyzer._calculate_likelihood(set(), ErrorType.MOCK_ERROR, [])
    assert 0.0 < value <= 1.0


def test_calculate_evidence_blends_priors(tmp_path: Path) -> None:
    """RU/EN: Evidence calculation should combine priors and likelihoods."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::evidence",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            coverage=None,
            execution_time=0.1,
            error_message="Mock error reported",
        )
    ]
    symptoms = {"mock"}
    similar_cases = analyzer._find_similar_cases(symptoms)
    evidence = analyzer._calculate_evidence(symptoms, similar_cases)
    assert 0.0 < evidence <= 1.0
    assert analyzer._calculate_evidence(set(), similar_cases) == 1.0


def test_get_test_health_score_handles_missing_data(tmp_path: Path) -> None:
    """RU/EN: Health score should default to safe values without coverage/time."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::health_missing",
            result=TestStatus.PASSED,
            error_type=None,
            coverage=None,
            execution_time=0.0,
        )
    ]
    assert analyzer.get_test_health_score("suite::health_missing") == pytest.approx(1.0)


def test_save_history_disabled(tmp_path: Path, monkeypatch) -> None:
    """RU/EN: save_history should be a no-op when persistence disabled."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.persist_enabled = False
    analyzer.execution_history = [
        _make_record(
            test_name="suite::persist_disabled",
            result=TestStatus.PASSED,
        )
    ]
    analyzer.save_history()
    assert not (tmp_path / "history.json").exists()


def test_find_similar_cases_empty_union(tmp_path: Path) -> None:
    """RU/EN: Ensure empty union branch executes without errors."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::no_symptoms",
            result=TestStatus.FAILED,
            error_type=ErrorType.MOCK_ERROR,
            error_message="",
        )
    ]
    similar = analyzer._find_similar_cases(set())
    assert similar == []


def test_calculate_confidence_zero_total(tmp_path: Path) -> None:
    """RU/EN: Confidence should be zero when summed probabilities equal zero."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    assert analyzer._calculate_confidence({}) == 0.0
    assert analyzer._calculate_confidence({ErrorType.MOCK_ERROR: 0.0}) == 0.0
    assert analyzer._calculate_confidence({ErrorType.MOCK_ERROR: 0.5}) == 1.0


def test_refresh_priors_no_history(tmp_path: Path) -> None:
    """RU/EN: Refresh priors should exit early when history empty."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    original = analyzer.prior_probabilities.copy()
    analyzer.execution_history = []
    analyzer._refresh_priors_from_history()
    assert analyzer.prior_probabilities == original


def test_get_test_health_score_zero_average(tmp_path: Path) -> None:
    """RU/EN: Zero execution times should fall back to stable defaults."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::zero_time",
            result=TestStatus.PASSED,
            coverage=90.0,
            execution_time=0.0,
        ),
        _make_record(
            test_name="suite::zero_time",
            result=TestStatus.PASSED,
            coverage=95.0,
            execution_time=0.0,
        ),
    ]
    assert analyzer.get_test_health_score("suite::zero_time") == pytest.approx(0.985)


def test_get_test_health_score_tiny_average_time(tmp_path: Path) -> None:
    """RU/EN: Tiny positive execution times keep health score within bounds."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    analyzer.execution_history = [
        _make_record(
            test_name="suite::timed",
            result=TestStatus.PASSED,
            coverage=80.0,
            execution_time=1e-12,
        ),
        _make_record(
            test_name="suite::timed",
            result=TestStatus.PASSED,
            coverage=85.0,
            execution_time=2e-12,
        ),
    ]

    score = analyzer.get_test_health_score("suite::timed")
    assert 0.0 <= score <= 1.0


def test_refresh_priors_handles_no_failures(tmp_path: Path) -> None:
    """RU/EN: When history lacks failures, priors remain unchanged."""

    analyzer = BayesianTestAnalyzer(data_file=tmp_path / "history.json")
    original_priors = analyzer.prior_probabilities.copy()
    analyzer.execution_history = [
        _make_record(
            test_name="suite::pass_only",
            result=TestStatus.PASSED,
            error_type=None,
            execution_time=0.2,
            coverage=80.0,
        )
    ]
    analyzer._refresh_priors_from_history()  # Should not raise or modify drastically
    assert analyzer.prior_probabilities == original_priors

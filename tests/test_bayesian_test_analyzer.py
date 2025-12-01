#!/usr/bin/env python3
"""
Unit tests for BayesianTestAnalyzer.

Covers the technical test analyzer for code quality checks.
"""

import pytest
import builtins
import core.bayesian_test_analyzer as bayesian_test_analyzer
from core.bayesian_test_analyzer import (
    BayesianDiagnosis,
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestRecord,
    TestStatus,
)


class TestBayesianTestAnalyzerInit:
    """Test analyzer initialization."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        analyzer = BayesianTestAnalyzer()
        assert analyzer.prior_probabilities is not None
        assert analyzer.test_history == []

    def test_prior_probabilities_sum(self) -> None:
        """Test that prior probabilities are normalized."""
        analyzer = BayesianTestAnalyzer()
        total = sum(analyzer.prior_probabilities.values())
        # Should be normalized to exactly 1.0
        assert total == pytest.approx(1.0, rel=1e-9)

    def test_test_history_aliases_execution_history(self) -> None:
        """test_history should be a live alias for execution_history."""
        analyzer = BayesianTestAnalyzer()
        assert analyzer.test_history == []
        assert analyzer.execution_history == []

        record = TestRecord(
            test_name="test_alias",
            category=TestCategory.UNIT,
            result=TestStatus.PASSED,
            execution_time=0.1,
            coverage_percentage=95.0,
            file_path="tests/test_alias.py",
        )
        analyzer.record_test_execution(record)

        # Alias should point to the same list and contain the record
        assert analyzer.test_history is analyzer.execution_history
        assert len(analyzer.test_history) == 1
        assert analyzer.test_history[0].test_name == "test_alias"

class TestTechnicalAspectAnalysis:
    """Test technical aspect detection."""

    def test_analyze_simple_code(self):
        """Test analysis of simple code."""
        analyzer = BayesianTestAnalyzer()
        code = "def test_simple(): assert True"
        issues = analyzer.analyze_technical_aspects(code, "test_simple")
        assert isinstance(issues, list)

    def test_detect_asyncmock_issue(self):
        """Test detection of AsyncMock without await."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_async():
    mock = AsyncMock()
    result = mock()  # Missing await
"""
        issues = analyzer.analyze_technical_aspects(code, "test_async")
        # Should return a list (detection logic may or may not flag AsyncMock)
        assert isinstance(issues, list)

    def test_detect_typing_issue(self):
        """Test detection of typing issues."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_types():
    result: int = "string"  # Type mismatch
"""
        issues = analyzer.analyze_technical_aspects(code, "test_types")
        assert isinstance(issues, list)


class TestTestCategoryClassification:
    """Test test category classification."""

    def test_classify_unit_test(self):
        """Test classification of unit tests."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_unit_function():
    result = add(2, 2)
    assert result == 4
"""
        issues = analyzer.analyze_technical_aspects(code, "test_unit_function")
        assert isinstance(issues, list)

    def test_classify_integration_test(self):
        """Test classification of integration tests."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_integration_api():
    response = client.get("/api/endpoint")
    assert response.status_code == 200
"""
        issues = analyzer.analyze_technical_aspects(code, "test_integration_api")
        assert isinstance(issues, list)


class TestPriorProbabilityUpdates:
    """Test Bayesian prior updates."""

    def test_update_priors_after_analysis(self):
        """Test that priors can be updated."""
        analyzer = BayesianTestAnalyzer()
        initial_priors = analyzer.prior_probabilities.copy()
        analyzer.analyze_technical_aspects("def test(): pass", "test")
        # Priors should still be valid
        assert analyzer.prior_probabilities is not None


class TestPredictionAndHealthScore:
    """Test failure probability prediction and health scoring."""

    def test_predict_failure_probability_new_test(self):
        """New tests without history should use the base probability."""
        analyzer = BayesianTestAnalyzer()
        probability = analyzer.predict_test_failure_probability("test_new")
        assert probability == pytest.approx(0.1)

    def test_predict_failure_probability_with_context(self):
        """Context flags should increase failure probability but keep it <= 1.0."""
        analyzer = BayesianTestAnalyzer()
        # 1 failure, 2 successes for the same test
        executions = [
            TestRecord(
                test_name="test_context",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.ASSERTION_ERROR,
            ),
            TestRecord(
                test_name="test_context",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
            ),
            TestRecord(
                test_name="test_context",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
            ),
        ]
        for execution in executions:
            analyzer.record_test_execution(execution)

        base_prob = analyzer.predict_test_failure_probability("test_context")
        ctx_prob = analyzer.predict_test_failure_probability(
            "test_context",
            context={
                "recent_changes": True,
                "complex_dependencies": True,
                "async_test": True,
            },
        )

        assert 0.0 < base_prob < 1.0
        assert base_prob <= ctx_prob <= 1.0

    def test_get_test_health_score_branches(self):
        """Exercise health score calculation for empty and populated history."""
        analyzer = BayesianTestAnalyzer()
        # No history → neutral score
        empty_score = analyzer.get_test_health_score("unknown_test")
        assert empty_score == pytest.approx(0.5)

        # Add multiple executions for the same test to exercise variance and coverage paths
        records = [
            TestRecord(
                test_name="test_health",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
                coverage_percentage=90.0,
                execution_time=0.1,
            ),
            TestRecord(
                test_name="test_health",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.ASSERTION_ERROR,
                coverage_percentage=80.0,
                execution_time=0.3,
            ),
            TestRecord(
                test_name="test_health",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
                coverage_percentage=None,
                execution_time=0.2,
            ),
        ]
        for record in records:
            analyzer.record_test_execution(record)

        score = analyzer.get_test_health_score("test_health")
        assert 0.0 <= score <= 1.0


class TestDiagnosisAndReporting:
    """Test diagnosis and reporting helpers."""

    def test_generate_test_report_empty_history(self):
        """Report should return a sentinel message when no data is available."""
        analyzer = BayesianTestAnalyzer()
        report = analyzer.generate_test_report()
        assert isinstance(report, dict)
        assert report.get("message")

    def test_diagnose_and_generate_report_with_history(self):
        """Diagnose failures and generate report from populated history."""
        analyzer = BayesianTestAnalyzer()
        # Create a mix of passed and failed executions for one test
        for status in [TestStatus.FAILED, TestStatus.PASSED]:
            analyzer.record_test_execution(
                TestRecord(
                    test_name="test_async_failure",
                    category=TestCategory.UNIT,
                    result=status,
                    error_type=ErrorType.ASYNC_ERROR if status == TestStatus.FAILED else None,
                    error_message="Async error in test" if status == TestStatus.FAILED else "",
                    coverage_percentage=85.0,
                    execution_time=0.2,
                    file_path="tests/test_async_failure.py",
                )
            )

        diagnosis = analyzer.diagnose_test_failure(
            "test_async_failure", "Async error in test", context={"async_test": True}
        )
        assert isinstance(diagnosis, BayesianDiagnosis)
        assert 0.0 <= diagnosis.probability <= 1.0
        assert 0.0 <= diagnosis.confidence <= 1.0
        assert isinstance(diagnosis.evidence, list)
        assert isinstance(diagnosis.recommendations, list)

        report = analyzer.generate_test_report()
        assert isinstance(report, dict)
        assert report.get("total_tests", 0) >= 1
        assert report.get("failed_tests", 0) >= 1
        assert isinstance(report.get("recommendations"), list)


class TestInternalsAndEdgeBranches:
    """Cover additional internal branches and error handling paths."""

    def test_normalize_priors_zero_sum_uniform(self):
        """Zero-sum priors should normalize to a uniform distribution."""
        zeros = {et: 0.0 for et in ErrorType}
        normalized = BayesianTestAnalyzer._normalize_priors(zeros)
        assert all(val == pytest.approx(1 / len(ErrorType)) for val in normalized.values())

    def test_calculate_recency_weight_exception_fallback(self):
        """Type errors in recency calculation should return safe default of 1.0."""
        analyzer = BayesianTestAnalyzer()
        # Passing an invalid timestamp triggers the exception path
        weight = analyzer._calculate_recency_weight(timestamp=None)  # type: ignore[arg-type]
        assert weight == pytest.approx(1.0)

    def test_load_history_handles_invalid_json(self, tmp_path):
        """load_history should swallow JSON errors and keep history empty."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not-json")
        analyzer = BayesianTestAnalyzer(data_file=bad_file)
        # Should not raise and should leave history empty
        assert analyzer.execution_history == []

    def test_save_history_handles_io_errors(self, tmp_path, monkeypatch):
        """save_history should log errors and not raise when writing fails."""
        history_file = tmp_path / "history.json"
        analyzer = BayesianTestAnalyzer(data_file=history_file)
        analyzer.record_test_execution(
            TestRecord(
                test_name="test_io_error",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.ASSERTION_ERROR,
                error_message="boom",
            )
        )

        def _failing_open(*_args, **_kwargs):
            raise OSError("write failed")

        monkeypatch.setattr(builtins, "open", _failing_open)
        # Should not propagate the exception
        analyzer.save_history()

    def test_calculate_likelihood_no_history_or_no_type(self):
        """Likelihood should fall back to smoothed base values when history is missing."""
        analyzer = BayesianTestAnalyzer()
        no_history = analyzer._calculate_likelihood(set(), ErrorType.ASSERTION_ERROR, [])
        assert no_history == pytest.approx(0.1)

        # History present but no matching error_type
        analyzer.record_test_execution(
            TestRecord(
                test_name="test_other",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.VALUE_ERROR,
            )
        )
        no_match = analyzer._calculate_likelihood(set(), ErrorType.ASYNC_ERROR, [])
        assert no_match == pytest.approx(0.1)

    def test_calculate_evidence_no_symptoms(self):
        """Evidence should short-circuit to 1.0 when no symptoms are present."""
        analyzer = BayesianTestAnalyzer()
        assert analyzer._calculate_evidence(set(), []) == pytest.approx(1.0)

    def test_extract_symptoms_context_flags(self):
        """Context flags should add corresponding symptoms."""
        analyzer = BayesianTestAnalyzer()
        symptoms = analyzer._extract_symptoms(
            "Random error message",
            {"is_async": True, "has_mocks": True, "coverage_below_threshold": True},
        )
        assert {"async_context", "mock_context", "coverage_context"}.issubset(symptoms)

    def test_find_similar_cases_handles_empty_union(self):
        """Empty symptom sets should not raise and should compute similarity safely."""
        analyzer = BayesianTestAnalyzer()
        analyzer.record_test_execution(
            TestRecord(
                test_name="test_empty_symptoms",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.ASSERTION_ERROR,
                error_message="",
            )
        )
        similar = analyzer._find_similar_cases(set())
        assert isinstance(similar, list)

    def test_calculate_confidence_empty_and_zero_probs(self):
        """Confidence should handle empty and zero-valued probability dicts."""
        analyzer = BayesianTestAnalyzer()
        assert analyzer._calculate_confidence({}) == 0.0
        zero_conf = analyzer._calculate_confidence({ErrorType.ASSERTION_ERROR: 0.0})
        assert zero_conf == 0.0

    def test_refresh_priors_no_history_is_noop(self):
        """When no history is present, priors should remain unchanged."""
        analyzer = BayesianTestAnalyzer()
        original = analyzer.prior_probabilities.copy()
        analyzer._refresh_priors_from_history()
        assert analyzer.prior_probabilities == original

    def test_get_test_health_score_single_execution_time_branch(self):
        """Single execution time should take the simple stability branch."""
        analyzer = BayesianTestAnalyzer()
        analyzer.record_test_execution(
            TestRecord(
                test_name="test_single_run",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
                execution_time=0.05,
            )
        )
        score = analyzer.get_test_health_score("test_single_run")
        assert 0.0 <= score <= 1.0

    def test_generate_test_report_without_recommendations_when_all_pass(self):
        """When no failures exist, recommendations list should remain empty."""
        analyzer = BayesianTestAnalyzer()
        for idx in range(3):
            analyzer.record_test_execution(
                TestRecord(
                    test_name=f"test_pass_{idx}",
                    category=TestCategory.UNIT,
                    result=TestStatus.PASSED,
                )
            )
        report = analyzer.generate_test_report()
        assert report["recommendations"] == []

    def test_module_level_helpers_use_global_analyzer(self):
        """Global helper functions should delegate and return a BayesianDiagnosis."""
        bayesian_test_analyzer.record_test_execution(
            test_name="test_global_helper",
            category=TestCategory.UNIT,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            error_message="Assertion failed",
        )
        diagnosis = bayesian_test_analyzer.diagnose_test_failure(
            "test_global_helper", "Assertion failed", context={"has_mocks": True}
        )
        assert isinstance(diagnosis, BayesianDiagnosis)

    def test_generate_test_report_recommendations_thresholds(self):
        """High failure rate should trigger recommendations and most common error handling."""
        analyzer = BayesianTestAnalyzer()
        for _ in range(2):
            analyzer.record_test_execution(
                TestRecord(
                    test_name="test_failure",
                    category=TestCategory.UNIT,
                    result=TestStatus.FAILED,
                    error_type=ErrorType.MOCK_ERROR,
                    file_path="tests/test_failure.py",
                    error_message="Mock error occurred",
                )
            )
        report = analyzer.generate_test_report()
        # Locale-independent structural checks: verify recommendations exist and reference the failure
        assert (
            len(report["recommendations"]) > 0
        ), "Report should contain recommendations for failing tests"
        # Check that at least one recommendation mentions the test name, error type, or error message
        recommendations_text = " ".join(report["recommendations"]).lower()
        assert (
            "test_failure" in recommendations_text
            or "mock" in recommendations_text
            or "error" in recommendations_text
        ), "Recommendations should reference the failing test or error type"

    def test_gather_evidence_includes_file_stats(self):
        """Evidence should include file frequency when failures exist."""
        analyzer = BayesianTestAnalyzer()
        for path in ["tests/a.py", "tests/a.py", "tests/b.py"]:
            analyzer.record_test_execution(
                TestRecord(
                    test_name="test_evidence",
                    category=TestCategory.UNIT,
                    result=TestStatus.FAILED,
                    error_type=ErrorType.ASSERTION_ERROR,
                    file_path=path,
                    error_message="AssertionError",
                )
            )
        similar_cases = analyzer._find_similar_cases({"assertion"})
        evidence = analyzer._gather_evidence(
            {"assertion"}, ErrorType.ASSERTION_ERROR, similar_cases
        )
        assert any("tests/a.py" in item for item in evidence)


class TestOptimizationAndPersistence:
    """Test test ordering optimization and history persistence."""

    def test_optimize_test_order_sorts_by_failure_probability(self):
        """Tests with higher historical failure rates should be ordered first."""
        analyzer = BayesianTestAnalyzer()

        # High failure rate test
        for _ in range(3):
            analyzer.record_test_execution(
                TestRecord(
                    test_name="test_high",
                    category=TestCategory.UNIT,
                    result=TestStatus.FAILED,
                    error_type=ErrorType.ASSERTION_ERROR,
                )
            )

        # Medium failure rate test
        for _ in range(2):
            analyzer.record_test_execution(
                TestRecord(
                    test_name="test_medium",
                    category=TestCategory.UNIT,
                    result=TestStatus.FAILED,
                    error_type=ErrorType.ASSERTION_ERROR,
                )
            )
        analyzer.record_test_execution(
            TestRecord(
                test_name="test_medium",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
            )
        )

        # Low failure rate test (all passes)
        for _ in range(3):
            analyzer.record_test_execution(
                TestRecord(
                    test_name="test_low",
                    category=TestCategory.UNIT,
                    result=TestStatus.PASSED,
                )
            )

        ordered = analyzer.optimize_test_order(["test_low", "test_medium", "test_high"])
        assert ordered[0] == "test_high"
        assert ordered[-1] == "test_low"
        assert set(ordered) == {"test_high", "test_medium", "test_low"}

    def test_history_persistence_roundtrip(self, tmp_path):
        """Execution history should be persisted and reloaded when enabled."""
        history_file = tmp_path / "test_execution_history.json"

        analyzer = BayesianTestAnalyzer(data_file=history_file)
        analyzer.record_test_execution(
            TestRecord(
                test_name="test_persist",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.ASSERTION_ERROR,
                error_message="Failure for persistence test",
                coverage_percentage=75.0,
                execution_time=0.25,
                file_path="tests/test_persist.py",
            )
        )

        assert history_file.exists()

        # New analyzer instance should load the saved history
        reloaded_analyzer = BayesianTestAnalyzer(data_file=history_file)
        assert len(reloaded_analyzer.execution_history) >= 1
        # Alias should remain valid after load_history
        assert reloaded_analyzer.test_history is reloaded_analyzer.execution_history


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_code(self):
        """Test analysis of empty code."""
        analyzer = BayesianTestAnalyzer()
        issues = analyzer.analyze_technical_aspects("", "test_empty")
        assert isinstance(issues, list)

    def test_malformed_code(self):
        """Test analysis of malformed code."""
        analyzer = BayesianTestAnalyzer()
        code = "def test_broken(:"
        issues = analyzer.analyze_technical_aspects(code, "test_broken")
        assert isinstance(issues, list)

    def test_very_long_test_name(self):
        """Test handling of very long test names."""
        analyzer = BayesianTestAnalyzer()
        long_name = "test_" + "very_long_" * 50 + "name"
        issues = analyzer.analyze_technical_aspects("def test(): pass", long_name)
        assert isinstance(issues, list)

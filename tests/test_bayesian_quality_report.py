"""Tests for scripts/bayesian_quality_report.py."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestRecord,
    TestStatus,
)
from scripts.bayesian_quality_report import main, normalize


class TestNormalizeFunction:
    """Tests for the normalize function."""

    def test_normalize_empty_dict(self):
        """Test normalize with empty dictionary."""
        result = normalize({})
        assert result == {}

    def test_normalize_single_error_type(self):
        """Test normalize with single error type."""
        input_dict = {ErrorType.ASSERTION_ERROR: 5.0}
        result = normalize(input_dict)
        assert result == {"assertion_error": 1.0}

    def test_normalize_multiple_error_types(self):
        """Test normalize with multiple error types."""
        input_dict = {
            ErrorType.ASSERTION_ERROR: 10.0,
            ErrorType.TYPE_ERROR: 5.0,
            ErrorType.VALUE_ERROR: 5.0,
        }
        result = normalize(input_dict)

        assert result["assertion_error"] == pytest.approx(0.5)
        assert result["type_error"] == pytest.approx(0.25)
        assert result["value_error"] == pytest.approx(0.25)

        # Sum should equal 1.0
        assert sum(result.values()) == pytest.approx(1.0)

    def test_normalize_with_zeros(self):
        """Test normalize with zero values."""
        input_dict = {
            ErrorType.ASSERTION_ERROR: 0.0,
            ErrorType.TYPE_ERROR: 10.0,
        }
        result = normalize(input_dict)

        assert result["assertion_error"] == 0.0
        assert result["type_error"] == 1.0


class TestBayesianQualityReportMain:
    """Tests for the main function."""

    @pytest.fixture
    def temp_output_file(self, tmp_path, monkeypatch):
        """Create a temporary output file path."""
        monkeypatch.chdir(tmp_path)
        return tmp_path / "bayesian_quality_report.json"

    @pytest.fixture
    def mock_analyzer_empty(self):
        """Mock analyzer with no history."""
        with patch("scripts.bayesian_quality_report.BayesianTestAnalyzer") as mock:
            analyzer = MagicMock(spec=BayesianTestAnalyzer)
            analyzer.execution_history = []
            analyzer.prior_probabilities = {et: 0.1 for et in ErrorType}
            mock.return_value = analyzer
            yield analyzer

    @pytest.fixture
    def mock_analyzer_with_data(self):
        """Mock analyzer with test history."""
        with patch("scripts.bayesian_quality_report.BayesianTestAnalyzer") as mock:
            analyzer = MagicMock(spec=BayesianTestAnalyzer)

            # Create test records
            analyzer.execution_history = [
                TestRecord(
                    test_name="test_1",
                    category=TestCategory.UNIT,
                    result=TestStatus.FAILED,
                    error_type=ErrorType.ASSERTION_ERROR,
                    error_message="Assert failed",
                ),
                TestRecord(
                    test_name="test_2",
                    category=TestCategory.UNIT,
                    result=TestStatus.PASSED,
                ),
                TestRecord(
                    test_name="test_3",
                    category=TestCategory.INTEGRATION,
                    result=TestStatus.FAILED,
                    error_type=ErrorType.TYPE_ERROR,
                    error_message="Type mismatch",
                ),
            ]

            analyzer.prior_probabilities = {
                ErrorType.ASSERTION_ERROR: 0.5,
                ErrorType.TYPE_ERROR: 0.3,
                ErrorType.VALUE_ERROR: 0.2,
                ErrorType.IMPORT_ERROR: 0.0,
                ErrorType.ATTRIBUTE_ERROR: 0.0,
                ErrorType.RUNTIME_ERROR: 0.0,
                ErrorType.TIMEOUT_ERROR: 0.0,
                ErrorType.COVERAGE_ERROR: 0.0,
                ErrorType.MOCK_ERROR: 0.0,
                ErrorType.ASYNC_ERROR: 0.0,
            }

            mock.return_value = analyzer
            yield analyzer

    def test_main_empty_history(self, mock_analyzer_empty, temp_output_file, capsys):
        """Test main with empty history."""
        result = main()

        assert result == 0
        assert temp_output_file.exists()

        # Check report content
        report = json.loads(temp_output_file.read_text())
        assert report["history_size"] == 0
        assert "prior_probabilities" in report
        assert "error_type_counts" in report
        assert "avg_confidence_estimate" in report

        # Verify output message
        captured = capsys.readouterr()
        assert "bayesian_quality_report.json" in captured.out
        assert "0 records" in captured.out

    def test_main_with_history(self, mock_analyzer_with_data, temp_output_file, capsys):
        """Test main with test history."""
        result = main()

        assert result == 0
        assert temp_output_file.exists()

        # Check report content
        report = json.loads(temp_output_file.read_text())
        assert report["history_size"] == 3
        assert "prior_probabilities" in report
        assert "error_type_counts" in report

        # Check error counts
        error_counts = report["error_type_counts"]
        assert error_counts["assertion_error"] == 1.0
        assert error_counts["type_error"] == 1.0

        # Check confidence estimate
        assert 0.0 <= report["avg_confidence_estimate"] <= 1.0

        # Verify output message
        captured = capsys.readouterr()
        assert "3 records" in captured.out

    def test_main_entropy_calculation(self, mock_analyzer_with_data, temp_output_file):
        """Test that entropy-based confidence is calculated correctly."""
        result = main()

        assert result == 0
        report = json.loads(temp_output_file.read_text())

        # Verify confidence estimate is reasonable
        confidence = report["avg_confidence_estimate"]
        assert 0.0 <= confidence <= 1.0

        # With non-uniform priors, confidence should be > 0
        assert confidence > 0.0

    def test_main_prior_probabilities_normalized(self, mock_analyzer_with_data, temp_output_file):
        """Test that prior probabilities are normalized."""
        result = main()

        assert result == 0
        report = json.loads(temp_output_file.read_text())

        priors = report["prior_probabilities"]
        total = sum(priors.values())

        # Sum should be approximately 1.0
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_main_handles_only_passed_tests(self, tmp_path, monkeypatch):
        """Test main when all tests pass (no errors)."""
        monkeypatch.chdir(tmp_path)
        output_file = tmp_path / "bayesian_quality_report.json"

        with patch("scripts.bayesian_quality_report.BayesianTestAnalyzer") as mock:
            analyzer = MagicMock(spec=BayesianTestAnalyzer)
            analyzer.execution_history = [
                TestRecord(
                    test_name="test_pass",
                    category=TestCategory.UNIT,
                    result=TestStatus.PASSED,
                )
            ]
            analyzer.prior_probabilities = {et: 0.1 for et in ErrorType}
            mock.return_value = analyzer

            result = main()

            assert result == 0
            report = json.loads(output_file.read_text())

            # All error counts should be 0
            error_counts = report["error_type_counts"]
            assert all(count == 0.0 for count in error_counts.values())

    def test_main_uniform_priors_low_confidence(self, tmp_path, monkeypatch):
        """Test that uniform priors result in low confidence."""
        monkeypatch.chdir(tmp_path)
        output_file = tmp_path / "bayesian_quality_report.json"

        with patch("scripts.bayesian_quality_report.BayesianTestAnalyzer") as mock:
            analyzer = MagicMock(spec=BayesianTestAnalyzer)
            analyzer.execution_history = []

            # Uniform priors (maximum entropy)
            num_error_types = len(list(ErrorType))
            uniform_prob = 1.0 / num_error_types
            analyzer.prior_probabilities = {et: uniform_prob for et in ErrorType}
            mock.return_value = analyzer

            result = main()

            assert result == 0
            report = json.loads(output_file.read_text())

            # Uniform priors should result in ~0 confidence
            assert report["avg_confidence_estimate"] == pytest.approx(0.0, abs=0.1)


class TestScriptExecution:
    """Test script execution as a module."""

    def test_script_can_be_imported(self):
        """Test that the script can be imported without errors."""
        import scripts.bayesian_quality_report as script

        assert hasattr(script, "main")
        assert hasattr(script, "normalize")
        assert callable(script.main)
        assert callable(script.normalize)

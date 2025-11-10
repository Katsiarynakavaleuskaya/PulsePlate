#!/usr/bin/env python3
"""
Тесты для scripts/bayesian_quality_report.py.

Покрытие для скрипта генерации отчетов о качестве Bayesian анализатора.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.bayesian_test_analyzer import BayesianTestAnalyzer, ErrorType, TestCategory, TestStatus


class TestBayesianQualityReport:
    """Тесты для bayesian_quality_report.py."""

    def test_normalize_function(self) -> None:
        """Тест функции normalize."""
        from scripts.bayesian_quality_report import normalize

        # Test normalization
        d = {ErrorType.ASSERTION_ERROR: 2.0, ErrorType.TYPE_ERROR: 3.0}
        result = normalize(d)

        assert sum(result.values()) == pytest.approx(1.0)
        assert result[ErrorType.ASSERTION_ERROR.value] == pytest.approx(0.4)
        assert result[ErrorType.TYPE_ERROR.value] == pytest.approx(0.6)

        # Test zero sum (should avoid division by zero)
        d_zero = {ErrorType.ASSERTION_ERROR: 0.0, ErrorType.TYPE_ERROR: 0.0}
        result_zero = normalize(d_zero)

        assert result_zero[ErrorType.ASSERTION_ERROR.value] == 0.0
        assert result_zero[ErrorType.TYPE_ERROR.value] == 0.0

    def test_calculate_confidence_from_priors(self) -> None:
        """Test calculate_confidence_from_priors function with various edge cases."""
        from scripts.bayesian_quality_report import calculate_confidence_from_priors

        # Empty distribution
        assert calculate_confidence_from_priors({}) == 0.0

        # Single probability (full confidence)
        single = {"error1": 1.0}
        assert calculate_confidence_from_priors(single) == 1.0

        # All-zero priors
        all_zero = {"error1": 0.0, "error2": 0.0}
        assert calculate_confidence_from_priors(all_zero) == 0.0

        # Uniform distribution (low confidence)
        uniform = {"error1": 0.5, "error2": 0.5}
        uniform_confidence = calculate_confidence_from_priors(uniform)
        assert 0.0 <= uniform_confidence <= 1.0
        assert uniform_confidence < 0.5  # Uniform should have low confidence

        # Skewed distribution (higher confidence)
        skewed = {"error1": 0.9, "error2": 0.1}
        skewed_confidence = calculate_confidence_from_priors(skewed)
        assert 0.0 <= skewed_confidence <= 1.0
        assert skewed_confidence > uniform_confidence  # Skewed should have higher confidence

        # Very small probabilities (near-zero sum)
        small = {"error1": 1e-15, "error2": 1e-15}
        assert calculate_confidence_from_priors(small) == 0.0

    def test_main_success(self, tmp_path: Path) -> None:
        """Тест успешного выполнения main()."""
        from scripts.bayesian_quality_report import main

        # Mock BayesianTestAnalyzer
        mock_analyzer = MagicMock()
        mock_analyzer.execution_history = []
        mock_analyzer.prior_probabilities = {
            ErrorType.ASSERTION_ERROR: 0.5,
            ErrorType.TYPE_ERROR: 0.5,
        }

        with patch(
            "scripts.bayesian_quality_report.BayesianTestAnalyzer", return_value=mock_analyzer
        ):
            with patch("scripts.bayesian_quality_report.Path") as mock_path:
                mock_output = MagicMock()
                mock_path.return_value = mock_output

                result = main()

                assert result == 0
                assert mock_output.write_text.called

                # Verify report content structure and values
                call_args = mock_output.write_text.call_args[0][0]
                report = json.loads(call_args)

                # Verify expected keys are present
                assert "history_size" in report
                assert "prior_probabilities" in report
                assert "error_type_counts" in report
                assert "avg_confidence_estimate" in report

                # Verify values match expected structure
                assert report["history_size"] == 0
                assert isinstance(report["prior_probabilities"], dict)
                assert isinstance(report["error_type_counts"], dict)
                assert isinstance(report["avg_confidence_estimate"], float)

                # Verify prior_probabilities content
                assert ErrorType.ASSERTION_ERROR.value in report["prior_probabilities"]
                assert ErrorType.TYPE_ERROR.value in report["prior_probabilities"]
                assert report["prior_probabilities"][
                    ErrorType.ASSERTION_ERROR.value
                ] == pytest.approx(0.5)
                assert report["prior_probabilities"][ErrorType.TYPE_ERROR.value] == pytest.approx(
                    0.5
                )

                # Verify error_type_counts (should be zeros for empty history)
                assert report["error_type_counts"][ErrorType.ASSERTION_ERROR.value] == 0.0
                assert report["error_type_counts"][ErrorType.TYPE_ERROR.value] == 0.0

    def test_main_with_history(self, tmp_path: Path) -> None:
        """Тест main() с историей выполнения тестов."""
        from datetime import datetime, timezone

        from core.bayesian_test_analyzer import TestRecord
        from scripts.bayesian_quality_report import main

        # Create test records
        test_records = [
            TestRecord(
                test_name="test_1",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.ASSERTION_ERROR,
                timestamp=datetime.now(timezone.utc),
                dependencies=[],
            ),
            TestRecord(
                test_name="test_2",
                category=TestCategory.UNIT,
                result=TestStatus.FAILED,
                error_type=ErrorType.TYPE_ERROR,
                timestamp=datetime.now(timezone.utc),
                dependencies=[],
            ),
            TestRecord(
                test_name="test_3",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
                error_type=None,
                timestamp=datetime.now(timezone.utc),
                dependencies=[],
            ),
        ]

        mock_analyzer = MagicMock()
        mock_analyzer.execution_history = test_records
        mock_analyzer.prior_probabilities = {
            ErrorType.ASSERTION_ERROR: 0.5,
            ErrorType.TYPE_ERROR: 0.5,
        }

        with patch(
            "scripts.bayesian_quality_report.BayesianTestAnalyzer", return_value=mock_analyzer
        ):
            with patch("scripts.bayesian_quality_report.Path") as mock_path:
                mock_output = MagicMock()
                mock_path.return_value = mock_output

                result = main()

                assert result == 0
                assert mock_output.write_text.called

                # Verify report content
                call_args = mock_output.write_text.call_args[0][0]
                report = json.loads(call_args)

                assert report["history_size"] == 3
                assert report["error_type_counts"][ErrorType.ASSERTION_ERROR.value] == 1.0
                assert report["error_type_counts"][ErrorType.TYPE_ERROR.value] == 1.0
                assert "prior_probabilities" in report
                assert "avg_confidence_estimate" in report

    def test_main_initialization_error(self) -> None:
        """Тест обработки ошибки инициализации."""
        from scripts.bayesian_quality_report import main

        with patch(
            "scripts.bayesian_quality_report.BayesianTestAnalyzer",
            side_effect=Exception("Init error"),
        ):
            result = main()

            assert result == 1

    def test_main_write_error(self, tmp_path: Path) -> None:
        """Тест обработки ошибки записи файла."""
        from scripts.bayesian_quality_report import main

        mock_analyzer = MagicMock()
        mock_analyzer.execution_history = []
        mock_analyzer.prior_probabilities = {
            ErrorType.ASSERTION_ERROR: 0.5,
            ErrorType.TYPE_ERROR: 0.5,
        }

        with patch(
            "scripts.bayesian_quality_report.BayesianTestAnalyzer", return_value=mock_analyzer
        ):
            with patch("scripts.bayesian_quality_report.Path") as mock_path:
                mock_output = MagicMock()
                mock_output.write_text.side_effect = IOError("Write error")
                mock_path.return_value = mock_output

                result = main()

                assert result == 1

"""
Unit tests for pytest_bayesian_plugin pytest hooks and integration.

Tests the actual pytest plugin hooks and integration points.
"""

from typing import Any
from unittest.mock import MagicMock, patch
import os

import pytest

from pytest_bayesian_plugin import (
    BayesianPytestPlugin,
    pytest_configure,
    pytest_runtest_setup,
    pytest_runtest_teardown,
    pytest_runtest_logreport,
)
from core.bayesian_test_analyzer import TestResult, ErrorType


def test_pytest_configure() -> None:
    """Test pytest_configure hook."""

    # Create object without bayesian_plugin attribute
    class FakeConfig:
        pass

    mock_config = FakeConfig()
    # Initially no plugin
    assert not hasattr(mock_config, "bayesian_plugin")

    # Call configure
    pytest_configure(mock_config)

    # Plugin should be attached
    assert hasattr(mock_config, "bayesian_plugin")
    assert isinstance(mock_config.bayesian_plugin, BayesianPytestPlugin)


def test_pytest_configure_idempotent() -> None:
    """Test pytest_configure is idempotent."""
    mock_config = MagicMock()
    mock_config.bayesian_plugin = BayesianPytestPlugin()

    # Call configure again
    pytest_configure(mock_config)

    # Should not create new plugin
    assert hasattr(mock_config, "bayesian_plugin")


def test_pytest_runtest_setup_hook() -> None:
    """Test pytest_runtest_setup hook."""
    mock_item = MagicMock()
    mock_item.nodeid = "tests/test_example.py::test_function"
    mock_item.config.bayesian_plugin = BayesianPytestPlugin()

    # Call hook
    pytest_runtest_setup(mock_item)

    # Plugin should have recorded start time
    assert mock_item.nodeid in mock_item.config.bayesian_plugin.test_start_times


def test_pytest_runtest_setup_hook_no_plugin() -> None:
    """Test pytest_runtest_setup hook when no plugin."""
    mock_item = MagicMock()
    mock_item.nodeid = "tests/test_example.py::test_function"
    # No plugin attached
    del mock_item.config.bayesian_plugin

    # Should not raise
    pytest_runtest_setup(mock_item)


def test_pytest_runtest_teardown_hook() -> None:
    """Test pytest_runtest_teardown hook."""
    mock_item = MagicMock()
    mock_item.nodeid = "tests/test_example.py::test_function"
    plugin = BayesianPytestPlugin()
    plugin.test_start_times[mock_item.nodeid] = 12345.0
    plugin.test_contexts[mock_item.nodeid] = {"category": "unit"}
    mock_item.config.bayesian_plugin = plugin

    # Call hook
    pytest_runtest_teardown(mock_item, None)

    # Temporary data should be cleaned
    assert mock_item.nodeid not in plugin.test_start_times
    assert mock_item.nodeid not in plugin.test_contexts


def test_pytest_runtest_teardown_hook_no_plugin() -> None:
    """Test pytest_runtest_teardown hook when no plugin."""
    mock_item = MagicMock()
    mock_item.nodeid = "tests/test_example.py::test_function"
    del mock_item.config.bayesian_plugin

    # Should not raise
    pytest_runtest_teardown(mock_item, None)


def test_pytest_runtest_logreport_hook_passed() -> None:
    """Test pytest_runtest_logreport hook for passed test."""
    mock_report = MagicMock()
    mock_report.when = "call"
    mock_report.nodeid = "tests/test_example.py::test_function"
    mock_report.outcome = "passed"
    mock_report.duration = 0.5
    mock_report.fspath = MagicMock()
    mock_report.fspath.strpath = "tests/test_example.py"
    mock_report.lineno = 10

    plugin = BayesianPytestPlugin()
    plugin.test_contexts[mock_report.nodeid] = {
        "category": "unit",
        "context": {},
    }
    mock_report.config.bayesian_plugin = plugin

    # Mock record_test_execution
    with patch("pytest_bayesian_plugin.record_test_execution") as mock_record:
        pytest_runtest_logreport(mock_report)

        # Should record passed test
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["result"] == TestResult.PASSED
        assert call_kwargs["error_type"] is None
        assert call_kwargs["error_message"] is None


def test_pytest_runtest_logreport_hook_failed() -> None:
    """Test pytest_runtest_logreport hook for failed test."""
    mock_report = MagicMock()
    mock_report.when = "call"
    mock_report.nodeid = "tests/test_example.py::test_function"
    mock_report.outcome = "failed"
    mock_report.duration = 0.5
    mock_report.fspath = MagicMock()
    mock_report.fspath.strpath = "tests/test_example.py"
    mock_report.lineno = 10
    mock_report.longrepr = "AssertionError: test failed"

    plugin = BayesianPytestPlugin()
    plugin.test_contexts[mock_report.nodeid] = {
        "category": "unit",
        "context": {},
    }
    mock_report.config.bayesian_plugin = plugin

    # Mock record_test_execution and diagnose_test_failure
    with (
        patch("pytest_bayesian_plugin.record_test_execution") as mock_record,
        patch("pytest_bayesian_plugin.diagnose_test_failure") as mock_diagnose,
    ):
        mock_diagnose.return_value = MagicMock()

        pytest_runtest_logreport(mock_report)

        # Should record failed test
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["result"] == TestResult.FAILED
        assert call_kwargs["error_type"] == ErrorType.ASSERTION_ERROR

        # Should call diagnosis
        mock_diagnose.assert_called_once()


def test_pytest_runtest_logreport_hook_skipped() -> None:
    """Test pytest_runtest_logreport hook for skipped test."""
    mock_report = MagicMock()
    mock_report.when = "call"
    mock_report.nodeid = "tests/test_example.py::test_function"
    mock_report.outcome = "skipped"
    mock_report.duration = 0.0
    mock_report.fspath = MagicMock()
    mock_report.fspath.strpath = "tests/test_example.py"

    plugin = BayesianPytestPlugin()
    plugin.test_contexts[mock_report.nodeid] = {
        "category": "unit",
        "context": {},
    }
    mock_report.config.bayesian_plugin = plugin

    with patch("pytest_bayesian_plugin.record_test_execution") as mock_record:
        pytest_runtest_logreport(mock_report)

        # Should record skipped test
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["result"] == TestResult.SKIPPED


def test_pytest_runtest_logreport_hook_error() -> None:
    """Test pytest_runtest_logreport hook for error in test."""
    mock_report = MagicMock()
    mock_report.when = "call"
    mock_report.nodeid = "tests/test_example.py::test_function"
    mock_report.outcome = "error"
    mock_report.duration = 0.1
    mock_report.fspath = MagicMock()
    mock_report.fspath.strpath = "tests/test_example.py"

    plugin = BayesianPytestPlugin()
    plugin.test_contexts[mock_report.nodeid] = {
        "category": "unit",
        "context": {},
    }
    mock_report.config.bayesian_plugin = plugin

    with patch("pytest_bayesian_plugin.record_test_execution") as mock_record:
        pytest_runtest_logreport(mock_report)

        # Should record error
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["result"] == TestResult.ERROR


def test_pytest_runtest_logreport_hook_setup_phase() -> None:
    """Test pytest_runtest_logreport hook ignores setup phase."""
    mock_report = MagicMock()
    mock_report.when = "setup"  # Not "call"
    mock_report.nodeid = "tests/test_example.py::test_function"

    plugin = BayesianPytestPlugin()
    mock_report.config.bayesian_plugin = plugin

    with patch("pytest_bayesian_plugin.record_test_execution") as mock_record:
        pytest_runtest_logreport(mock_report)

        # Should not record
        mock_record.assert_not_called()


def test_pytest_runtest_logreport_hook_no_plugin() -> None:
    """Test pytest_runtest_logreport hook when no plugin."""
    mock_report = MagicMock()
    mock_report.when = "call"
    del mock_report.config.bayesian_plugin

    # Should not raise
    pytest_runtest_logreport(mock_report)


def test_print_diagnosis_verbose_enabled(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Test _print_diagnosis with verbose output enabled."""
    monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "1")

    plugin = BayesianPytestPlugin()
    diagnosis = MagicMock()
    diagnosis.most_likely_cause = "Test assertion failed"
    diagnosis.probability = 0.85
    diagnosis.confidence = 0.9
    diagnosis.evidence = ["Evidence 1", "Evidence 2"]
    diagnosis.recommendations = ["Fix 1", "Fix 2"]
    diagnosis.alternative_causes = [("Alt cause 1", 0.1), ("Alt cause 2", 0.05)]

    plugin._print_diagnosis(diagnosis)

    captured = capsys.readouterr()
    assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in captured.out
    assert "Test assertion failed" in captured.out
    assert "85" in captured.out  # Probability
    assert "90" in captured.out  # Confidence
    assert "Evidence 1" in captured.out
    assert "Fix 1" in captured.out
    assert "Alt cause 1" in captured.out


def test_print_diagnosis_verbose_enabled_various_values(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Test _print_diagnosis with various truthy environment values."""
    plugin = BayesianPytestPlugin()
    diagnosis = MagicMock()
    diagnosis.most_likely_cause = "Test error"
    diagnosis.probability = 0.5
    diagnosis.confidence = 0.5
    diagnosis.evidence = []
    diagnosis.recommendations = []
    diagnosis.alternative_causes = []

    for value in ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON"]:
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", value)
        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in captured.out


def test_print_diagnosis_verbose_disabled(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Test _print_diagnosis with verbose output disabled."""
    monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "0")

    plugin = BayesianPytestPlugin()
    diagnosis = MagicMock()
    diagnosis.most_likely_cause = "Test error"

    plugin._print_diagnosis(diagnosis)

    captured = capsys.readouterr()
    assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" not in captured.out


def test_print_diagnosis_verbose_not_set(capsys) -> None:
    """Test _print_diagnosis when env var not set."""
    # Ensure env var is not set
    os.environ.pop("BAYESIAN_DIAG_VERBOSE", None)

    plugin = BayesianPytestPlugin()
    diagnosis = MagicMock()

    plugin._print_diagnosis(diagnosis)

    captured = capsys.readouterr()
    assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" not in captured.out


def test_logreport_with_no_fspath() -> None:
    """Test pytest_runtest_logreport when report has no fspath."""
    mock_report = MagicMock()
    mock_report.when = "call"
    mock_report.nodeid = "tests/test_example.py::test_function"
    mock_report.outcome = "passed"
    mock_report.duration = 0.5
    # No fspath attribute
    del mock_report.fspath

    plugin = BayesianPytestPlugin()
    plugin.test_contexts[mock_report.nodeid] = {
        "category": "unit",
        "context": {},
    }
    mock_report.config.bayesian_plugin = plugin

    with patch("pytest_bayesian_plugin.record_test_execution") as mock_record:
        pytest_runtest_logreport(mock_report)

        # Should record with empty file_path
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["file_path"] == ""


def test_logreport_with_missing_context() -> None:
    """Test pytest_runtest_logreport when test context is missing."""
    mock_report = MagicMock()
    mock_report.when = "call"
    mock_report.nodeid = "tests/test_example.py::test_function"
    mock_report.outcome = "passed"
    mock_report.duration = 0.5
    mock_report.fspath = MagicMock()
    mock_report.fspath.strpath = "tests/test_example.py"

    plugin = BayesianPytestPlugin()
    # No context for this test
    mock_report.config.bayesian_plugin = plugin

    with patch("pytest_bayesian_plugin.record_test_execution") as mock_record:
        pytest_runtest_logreport(mock_report)

        # Should use defaults
        mock_record.assert_called_once()


def test_plugin_custom_category_markers() -> None:
    """Test plugin with custom category markers."""
    custom_markers = ["smoke", "sanity", "critical"]
    plugin = BayesianPytestPlugin(category_markers=custom_markers)

    assert plugin.category_markers == custom_markers


def test_plugin_default_category_markers() -> None:
    """Test plugin uses default markers when none provided."""
    plugin = BayesianPytestPlugin()

    assert plugin.category_markers == BayesianPytestPlugin.DEFAULT_CATEGORY_MARKERS

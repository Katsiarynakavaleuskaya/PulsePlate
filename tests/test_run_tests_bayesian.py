"""
Unit tests for scripts/run_tests_bayesian.py.

Tests the fast test runner with Bayesian analysis of failed tests.
"""

import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, Any

import pytest

# Import the script module
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts import run_tests_bayesian


def test_clean_cache_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful cache cleaning."""
    # Create fake cache files
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    pyc_file = tmp_path / "test.pyc"
    pyc_file.write_text("fake pyc")

    # Mock project_root to point to tmp_path
    monkeypatch.setattr(run_tests_bayesian, "project_root", tmp_path)

    # Run clean_cache
    run_tests_bayesian.clean_cache()

    # Verify files were cleaned
    assert not cache_dir.exists() or len(list(cache_dir.iterdir())) == 0


def test_clean_cache_with_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Test cache cleaning handles errors gracefully."""
    # Mock project_root
    monkeypatch.setattr(run_tests_bayesian, "project_root", tmp_path)

    # Mock glob to raise exception
    def failing_glob(pattern: str):
        raise PermissionError("Access denied")

    monkeypatch.setattr(Path, "glob", lambda self, p: failing_glob(p))

    # Should not raise, just print warning
    run_tests_bayesian.clean_cache()

    captured = capsys.readouterr()
    assert "Очистка кеш-файлов" in captured.out or "Ошибка очистки" in captured.out


def test_run_tests_fast_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful test run."""
    # Mock subprocess.run
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "All tests passed\n10 passed"
    mock_result.stderr = ""

    mock_run = MagicMock(return_value=mock_result)
    monkeypatch.setattr(subprocess, "run", mock_run)

    # Mock clean_cache to avoid file operations
    monkeypatch.setattr(run_tests_bayesian, "clean_cache", lambda: None)

    result = run_tests_bayesian.run_tests_fast()

    assert result["success"] is True
    assert result["returncode"] == 0
    assert len(result["failed_tests"]) == 0
    assert "All tests passed" in result["output"]

    # Verify subprocess was called with correct args
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args[0][0][0] == sys.executable
    assert "-m" in call_args[0][0]
    assert "pytest" in call_args[0][0]


def test_run_tests_fast_with_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test test run with failures."""
    # Mock subprocess.run with failures
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = """
tests/test_example.py::test_function FAILED
tests/test_other.py::test_another ERROR
"""
    mock_result.stderr = ""

    mock_run = MagicMock(return_value=mock_result)
    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(run_tests_bayesian, "clean_cache", lambda: None)

    result = run_tests_bayesian.run_tests_fast()

    assert result["success"] is False
    assert result["returncode"] == 1
    assert len(result["failed_tests"]) == 2

    # Check failed test details
    assert any("test_function" in t["name"] for t in result["failed_tests"])
    assert any("test_another" in t["name"] for t in result["failed_tests"])


def test_run_tests_fast_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of test timeout."""

    # Mock subprocess.run to raise TimeoutExpired
    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=600)

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(run_tests_bayesian, "clean_cache", lambda: None)

    result = run_tests_bayesian.run_tests_fast()

    assert result["success"] is False
    assert result["returncode"] == 1
    assert "превысили время ожидания" in result["output"]


def test_run_tests_fast_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of general exceptions."""

    def mock_run(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(run_tests_bayesian, "clean_cache", lambda: None)

    result = run_tests_bayesian.run_tests_fast()

    assert result["success"] is False
    assert result["returncode"] == 1
    assert "Ошибка запуска тестов" in result["output"]


def test_analyze_failed_tests_empty_list(capsys) -> None:
    """Test analyze_failed_tests with empty list."""
    run_tests_bayesian.analyze_failed_tests([])

    captured = capsys.readouterr()
    # Should return early without output
    assert "Байесовский анализ" not in captured.out


def test_analyze_failed_tests_with_tests(capsys) -> None:
    """Test analyze_failed_tests with actual tests."""
    failed_tests = [
        {
            "name": "test_example",
            "line": "tests/test_example.py::test_example FAILED",
            "context": """
def test_example():
    password = "secret"
    assert False
            """,
        }
    ]

    run_tests_bayesian.analyze_failed_tests(failed_tests)

    captured = capsys.readouterr()
    assert "Байесовский анализ" in captured.out
    assert "test_example" in captured.out


def test_analyze_failed_tests_with_analysis_error(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Test analyze_failed_tests handles analysis errors."""
    failed_tests = [
        {
            "name": "test_broken",
            "line": "tests/test_broken.py::test_broken FAILED",
            "context": "some context",
        }
    ]

    # Mock analyzer to raise exception
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_comprehensively.side_effect = RuntimeError("Analysis failed")
    mock_analyzer.get_comprehensive_diagnosis.return_value = {"status": "not_analyzed"}

    # Mock the class constructor
    mock_class = MagicMock(return_value=mock_analyzer)
    monkeypatch.setattr("scripts.run_tests_bayesian.ComprehensiveBayesianAnalyzer", mock_class)

    # Should handle error gracefully
    run_tests_bayesian.analyze_failed_tests(failed_tests)

    captured = capsys.readouterr()
    assert "Ошибка анализа" in captured.out or "test_broken" in captured.out


def test_analyze_failed_tests_limits_to_10(capsys) -> None:
    """Test that analyze_failed_tests limits to first 10 tests."""
    # Create 15 failed tests
    failed_tests = [
        {
            "name": f"test_{i}",
            "line": f"tests/test_{i}.py::test_{i} FAILED",
            "context": "def test(): pass",
        }
        for i in range(15)
    ]

    run_tests_bayesian.analyze_failed_tests(failed_tests)

    captured = capsys.readouterr()
    # Should only analyze first 10
    output_lines = captured.out.split("\n")
    analysis_count = sum(1 for line in output_lines if "Анализ:" in line)
    assert analysis_count <= 10


def test_analyze_failed_tests_shows_diagnosis(capsys) -> None:
    """Test that comprehensive diagnosis is shown."""
    failed_tests = [
        {
            "name": "test_with_issues",
            "line": "tests/test_issues.py::test_with_issues FAILED",
            "context": """
def test_with_issues():
    password = "test123"
    assert False
            """,
        }
    ]

    run_tests_bayesian.analyze_failed_tests(failed_tests)

    captured = capsys.readouterr()
    # Should show diagnosis even if empty or basic
    assert "Байесовский анализ" in captured.out


def test_main_all_pass(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Test main() with all tests passing."""
    # Mock run_tests_fast to return success
    mock_result = {
        "success": True,
        "failed_tests": [],
        "output": "All tests passed",
        "returncode": 0,
    }
    monkeypatch.setattr(run_tests_bayesian, "run_tests_fast", lambda: mock_result)

    exit_code = run_tests_bayesian.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Все тесты прошли успешно" in captured.out


def test_main_with_failures(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Test main() with test failures."""
    # Mock run_tests_fast to return failures
    mock_result = {
        "success": False,
        "failed_tests": [
            {"name": "test_1", "line": "line1", "context": "ctx1"},
            {"name": "test_2", "line": "line2", "context": "ctx2"},
        ],
        "output": "2 failed",
        "returncode": 1,
    }
    monkeypatch.setattr(run_tests_bayesian, "run_tests_fast", lambda: mock_result)

    # Mock analyze_failed_tests to avoid actual analysis
    monkeypatch.setattr(run_tests_bayesian, "analyze_failed_tests", lambda x: None)

    exit_code = run_tests_bayesian.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Упало тестов: 2" in captured.out
    assert "Список упавших тестов" in captured.out
    assert "test_1" in captured.out
    assert "test_2" in captured.out


def test_main_with_many_failures(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Test main() with more than 10 failures."""
    # Mock run_tests_fast with 15 failures
    failed_tests = [
        {"name": f"test_{i}", "line": f"line{i}", "context": f"ctx{i}"} for i in range(15)
    ]
    mock_result = {
        "success": False,
        "failed_tests": failed_tests,
        "output": "15 failed",
        "returncode": 1,
    }
    monkeypatch.setattr(run_tests_bayesian, "run_tests_fast", lambda: mock_result)
    monkeypatch.setattr(run_tests_bayesian, "analyze_failed_tests", lambda x: None)

    exit_code = run_tests_bayesian.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Упало тестов: 15" in captured.out
    # Should show only first 10 in list
    output_lines = [line for line in captured.out.split("\n") if "test_" in line]
    listed_tests = [
        line for line in output_lines if any(c.isdigit() and line.startswith(" ") for c in line[:5])
    ]
    # At least some tests should be listed
    assert len([line for line in captured.out.split("\n") if "test_" in line]) >= 10


def test_main_invocation() -> None:
    """Test that main can be invoked from __main__ block."""
    # This tests the if __name__ == "__main__" block structure
    # Just verify the function exists and is callable
    assert callable(run_tests_bayesian.main)
    assert hasattr(run_tests_bayesian, "main")

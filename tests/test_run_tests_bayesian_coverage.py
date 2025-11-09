"""Tests for scripts/run_tests_bayesian.py to improve coverage."""

from __future__ import annotations

# sourcery skip: extract-duplicate-code

import subprocess
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_tests_bayesian import (
    analyze_failed_tests,
    clean_cache,
    main,
    run_tests_fast,
)


class TestCleanCache:
    """Tests for clean_cache function."""

    def test_clean_cache_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test successful cache cleaning."""
        # Create temporary cache files and directories
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "file.pyc").touch()

        pyc_file = tmp_path / "file.pyc"
        pyc_file.touch()

        pytest_cache = tmp_path / ".pytest_cache"
        pytest_cache.mkdir()

        coverage_file = tmp_path / ".coverage"
        coverage_file.touch()

        # Monkeypatch project_root to use tmp_path
        with patch("scripts.run_tests_bayesian.project_root", tmp_path):
            clean_cache()

        # Verify cache files are removed
        assert not pytest_cache.exists()
        assert not coverage_file.exists()

        captured = capsys.readouterr()
        assert "Очистка кеш-файлов" in captured.out
        assert "Кеш очищен" in captured.out

    def test_clean_cache_handles_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test clean_cache handles errors gracefully."""
        with patch("scripts.run_tests_bayesian.project_root", tmp_path):
            with patch.object(Path, "glob", side_effect=PermissionError("Permission denied")):
                clean_cache()
                # Function should complete without raising
                captured = capsys.readouterr()
                assert "Очистка кеш-файлов" in captured.out

    def test_clean_cache_removes_pyo_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test clean_cache removes .pyo files."""
        pyo_file = tmp_path / "file.pyo"
        pyo_file.touch()

        with patch("scripts.run_tests_bayesian.project_root", tmp_path):
            clean_cache()

        assert not pyo_file.exists()
        pyo_file.touch()

        with patch("scripts.run_tests_bayesian.project_root", tmp_path):
            clean_cache()

        assert not pyo_file.exists()


class TestRunTestsFast:
    """Tests for run_tests_fast function."""

    @pytest.fixture
    def mock_subprocess_success(self) -> Generator[Mock, None, None]:
        """Mock successful subprocess run."""
        with patch("subprocess.run") as mock_run:
            result = Mock()
            result.returncode = 0
            result.stdout = "All tests passed"
            result.stderr = ""
            mock_run.return_value = result
            yield mock_run

    @pytest.fixture
    def mock_subprocess_failure(self) -> Generator[Mock, None, None]:
        """Mock failed subprocess run."""
        with patch("subprocess.run") as mock_run:
            result = Mock()
            result.returncode = 1
            result.stdout = (
                "tests/test_file.py::test_function FAILED\n"
                "tests/test_other.py::test_error ERROR\n"
                "=== 2 failed, 1 error ===\n"
            )
            result.stderr = ""
            mock_run.return_value = result
            yield mock_run

    @pytest.fixture
    def mock_subprocess_timeout(self) -> Generator[Mock, None, None]:
        """Mock subprocess timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("pytest", 600)
            yield mock_run

    @pytest.fixture
    def mock_subprocess_exception(self) -> Generator[Mock, None, None]:
        """Mock subprocess exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Subprocess error")
            yield mock_run

    def test_run_tests_fast_success(
        self,
        mock_subprocess_success: Mock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test run_tests_fast with successful tests."""
        with patch("scripts.run_tests_bayesian.clean_cache"):
            result = run_tests_fast()

        assert result["success"] is True
        assert result["failed_tests"] == []
        assert result["returncode"] == 0
        assert "All tests passed" in result["output"]

        captured = capsys.readouterr()
        assert "Быстрый запуск тестов" in captured.out

    def test_run_tests_fast_failure(self, mock_subprocess_failure: Mock) -> None:
        """Test run_tests_fast with failed tests."""
        with patch("scripts.run_tests_bayesian.clean_cache"):
            result = run_tests_fast()

        assert result["success"] is False
        assert len(result["failed_tests"]) == 2
        assert result["returncode"] == 1

        # Verify failed tests were extracted
        failed_names = [t["name"] for t in result["failed_tests"]]
        assert any("test_function" in name for name in failed_names)
        assert any("test_error" in name for name in failed_names)

    def test_run_tests_fast_timeout(self, mock_subprocess_timeout: Mock) -> None:
        """Test run_tests_fast handles timeout."""
        with patch("scripts.run_tests_bayesian.clean_cache"):
            result = run_tests_fast()

        assert result["success"] is False
        assert result["failed_tests"] == []
        assert "превысили время ожидания" in result["output"]
        assert result["returncode"] == 1

    def test_run_tests_fast_exception(self, mock_subprocess_exception: Mock) -> None:
        """Test run_tests_fast handles exception."""
        with patch("scripts.run_tests_bayesian.clean_cache"):
            result = run_tests_fast()

        assert result["success"] is False
        assert result["failed_tests"] == []
        assert "Ошибка запуска тестов" in result["output"]
        assert result["returncode"] == 1

    def test_run_tests_fast_calls_clean_cache(self, mock_subprocess_success: Mock) -> None:
        """Test run_tests_fast calls clean_cache."""
        with patch("scripts.run_tests_bayesian.clean_cache") as mock_clean:
            run_tests_fast()

        mock_clean.assert_called_once()

    def test_run_tests_fast_subprocess_args(self, mock_subprocess_success: Mock) -> None:
        """Test run_tests_fast uses correct subprocess arguments."""
        with patch("scripts.run_tests_bayesian.clean_cache"):
            run_tests_fast()

        args = mock_subprocess_success.call_args[0][0]
        assert sys.executable in args
        assert "-m" in args
        assert "pytest" in args
        assert "tests/" in args
        assert "--cov=core" in args
        assert "--cov=app" in args

    def test_run_tests_fast_extracts_test_context(self, mock_subprocess_failure: Mock) -> None:
        """Test run_tests_fast extracts test context."""
        with patch("scripts.run_tests_bayesian.clean_cache"):
            result = run_tests_fast()

        # Verify context is included in failed tests
        for test in result["failed_tests"]:
            assert "context" in test
            assert "line" in test
            assert "name" in test

    def test_run_tests_fast_handles_parse_error(self) -> None:
        """Test run_tests_fast handles parsing errors gracefully."""
        with patch("subprocess.run") as mock_run:
            process = Mock()
            process.returncode = 1
            process.stdout = "FAILED :: test_name\nERROR :: other_test"
            process.stderr = ""
            mock_run.return_value = process

            with patch("scripts.run_tests_bayesian.clean_cache"):
                run_result = run_tests_fast()

            # Should handle lines with :: but extract them safely
            assert run_result["success"] is False


class TestAnalyzeFailedTests:
    """Tests for analyze_failed_tests function."""

    @pytest.fixture
    def mock_analyzer(self) -> Generator[Mock, None, None]:
        """Mock ComprehensiveBayesianAnalyzer."""
        with patch("scripts.run_tests_bayesian.ComprehensiveBayesianAnalyzer") as mock_cls:
            analyzer = Mock()

            # Mock analyze_comprehensively result
            analysis_result = Mock()
            analysis_result.critical_issues = ["Issue 1", "Issue 2"]
            analysis_result.optimization_opportunities = ["Opt 1", "Opt 2"]
            analysis_result.overall_score = 0.65
            analyzer.analyze_comprehensively.return_value = analysis_result

            # Mock get_comprehensive_diagnosis result
            diagnosis = {
                "status": "analyzed",
                "average_scores": {"technical": 0.75, "business": 0.80},
                "optimization_opportunities": [
                    "Recommendation 1",
                    "Recommendation 2",
                ],
            }
            analyzer.get_comprehensive_diagnosis.return_value = diagnosis

            mock_cls.return_value = analyzer
            yield analyzer

    def test_analyze_failed_tests_empty_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test analyze_failed_tests with empty list."""
        analyze_failed_tests([])

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_analyze_failed_tests_with_failures(
        self, mock_analyzer: Mock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test analyze_failed_tests with failed tests."""
        failed_tests = [
            {"name": "test_1", "context": "Test context 1"},
            {"name": "test_2", "context": "Test context 2"},
        ]

        analyze_failed_tests(failed_tests)

        captured = capsys.readouterr()
        assert "Байесовский анализ" in captured.out
        assert "test_1" in captured.out
        assert "test_2" in captured.out
        assert "Критические проблемы" in captured.out
        assert "Возможности оптимизации" in captured.out

    def test_analyze_failed_tests_low_score(
        self, mock_analyzer: Mock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test analyze_failed_tests with low score."""
        failed_tests = [{"name": "test_low_score", "context": "Context"}]

        analyze_failed_tests(failed_tests)

        captured = capsys.readouterr()
        assert "Низкий балл" in captured.out

    def test_analyze_failed_tests_handles_analysis_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test analyze_failed_tests handles analysis errors."""
        analyzer_path = "scripts.run_tests_bayesian.ComprehensiveBayesianAnalyzer"
        with patch(analyzer_path) as mock_cls:
            analyzer = Mock()
            analyzer.analyze_comprehensively.side_effect = Exception("Analysis error")
            mock_cls.return_value = analyzer

            failed_tests = [{"name": "test_error", "context": "Context"}]
            analyze_failed_tests(failed_tests)

        captured = capsys.readouterr()

    def test_analyze_failed_tests_limits_issue_display(
        self, mock_analyzer: Mock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test analyze_failed_tests limits displayed issues."""
        # Mock analyzer with many issues
        analyzer = mock_analyzer
        result = Mock()
        result.critical_issues = [f"Issue {i}" for i in range(10)]
        result.optimization_opportunities = [f"Opt {i}" for i in range(10)]
        result.overall_score = 0.8
        analyzer.analyze_comprehensively.return_value = result

        failed_tests = [{"name": "test_many_issues", "context": "Context"}]

        analyze_failed_tests(failed_tests)

        captured = capsys.readouterr()
        # Should only display first 3 critical issues and 2 optimizations
        assert captured.out.count("Issue") <= 3

    def test_analyze_failed_tests_limits_recommendations(
        self, mock_analyzer: Mock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test analyze_failed_tests limits displayed recommendations."""
        analyzer = mock_analyzer
        diagnosis = {
            "status": "analyzed",
            "average_scores": {"technical": 0.75, "business": 0.80},
            "optimization_opportunities": [f"Rec {i}" for i in range(10)],
        }
        analyzer.get_comprehensive_diagnosis.return_value = diagnosis

        failed_tests = [{"name": "test_1", "context": "Context"}]

        analyze_failed_tests(failed_tests)

        captured = capsys.readouterr()
        # Should only display first 5 recommendations
        recommendation_lines = [
            line
            for line in captured.out.split("\n")
            if line.strip()
            and line.strip()[0].isdigit()
            and line.strip().split(".", 1)[0].isdigit()
        ]
        assert len(recommendation_lines) <= 5


class TestMain:
    """Tests for main function."""

    @pytest.fixture
    def mock_run_tests_success(self) -> Generator[Mock, None, None]:
        """Mock successful test run."""
        with patch("scripts.run_tests_bayesian.run_tests_fast") as mock:
            mock.return_value = {
                "success": True,
                "failed_tests": [],
                "output": "All passed",
                "returncode": 0,
            }
            yield mock

    @pytest.fixture
    def mock_run_tests_failure(self) -> Generator[Mock, None, None]:
        """Mock failed test run."""
        with patch("scripts.run_tests_bayesian.run_tests_fast") as mock:
            mock.return_value = {
                "success": False,
                "failed_tests": [
                    {"name": "test_1", "context": "Context 1"},
                    {"name": "test_2", "context": "Context 2"},
                ],
                "output": "Tests failed",
                "returncode": 1,
            }
            yield mock

    def test_main_success(
        self,
        mock_run_tests_success: Mock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test main with successful tests."""
        result = main()

        assert result == 0

        captured = capsys.readouterr()
        assert "Быстрый прогон тестов" in captured.out
        assert "Все тесты прошли успешно" in captured.out

    def test_main_failure(
        self,
        mock_run_tests_failure: Mock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test main with failed tests."""
        with patch("scripts.run_tests_bayesian.analyze_failed_tests") as mock_analyze:
            result = main()

        assert result == 1

        captured = capsys.readouterr()
        assert "Упало тестов" in captured.out
        assert "Список упавших тестов" in captured.out
        assert "test_1" in captured.out
        assert "test_2" in captured.out

    def test_main_calls_analyze_on_failure(self, mock_run_tests_failure: Mock) -> None:
        """Test main calls analyze_failed_tests on failure."""
        with patch("scripts.run_tests_bayesian.analyze_failed_tests") as mock_analyze:
            main()

        mock_analyze.assert_called_once()
        args = mock_analyze.call_args[0][0]
        assert len(args) == 2

    def test_main_limits_failed_test_display(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main limits displayed failed tests to 10."""
        failed_tests = [{"name": f"test_{i}", "context": f"Context {i}"} for i in range(20)]

        with patch("scripts.run_tests_bayesian.run_tests_fast") as mock_run:
            mock_run.return_value = {
                "success": False,
                "failed_tests": failed_tests,
                "output": "Tests failed",
                "returncode": 1,
            }

            with patch("scripts.run_tests_bayesian.analyze_failed_tests"):
                main()

        captured = capsys.readouterr()
        # Count test entries (should be max 10)
        test_lines = [
            line for line in captured.out.split("\n") if line.strip() and line.strip()[0].isdigit()
        ]
        assert len(test_lines) <= 10


class TestScriptExecution:
    """Test script execution."""

    def test_script_main_execution(self) -> None:
        """Test that script can be executed."""
        # This test verifies the script structure is correct
        import scripts.run_tests_bayesian as script

        assert hasattr(script, "main")
        assert hasattr(script, "run_tests_fast")
        assert hasattr(script, "clean_cache")
        assert hasattr(script, "analyze_failed_tests")
        assert callable(script.main)

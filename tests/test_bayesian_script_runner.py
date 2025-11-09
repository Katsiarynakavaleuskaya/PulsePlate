from typing import Any, Dict
import subprocess

import pytest


def test_run_tests_fast_success(monkeypatch: pytest.MonkeyPatch) -> None:
    # Import inside to ensure test discovery works even if path changes
    from scripts import run_tests_bayesian as runner

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        # Use subprocess.CompletedProcess directly instead of Mock
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=0,
            stdout="OK\n",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    result: Dict[str, Any] = runner.run_tests_fast()
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)


def test_run_tests_fast_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test failure path with returncode=1."""
    from scripts import run_tests_bayesian as runner

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=1,
            stdout="FAILED\n",
            stderr="Error occurred",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    result: Dict[str, Any] = runner.run_tests_fast()
    assert result["success"] is False
    assert result["returncode"] == 1
    assert isinstance(result.get("output"), str)


def test_run_tests_fast_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test exception handling path."""
    from scripts import run_tests_bayesian as runner

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("pytest command not found")

    monkeypatch.setattr("subprocess.run", fake_run)

    result: Dict[str, Any] = runner.run_tests_fast()
    assert result["success"] is False
    # Check for error indication in output (can be in Russian or English)
    output = result.get("output", "").lower()
    assert "error" in output or "ошибка" in output or "exception" in output


def test_run_tests_fast_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test edge case with empty stdout/stderr."""
    from scripts import run_tests_bayesian as runner

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    result: Dict[str, Any] = runner.run_tests_fast()
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)

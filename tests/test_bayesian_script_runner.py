import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest


def test_run_tests_fast_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that run_tests_fast returns success and captures output correctly."""
    # Import inside to ensure test discovery works even if path changes
    from scripts import run_tests_bayesian as runner

    run_calls: list[tuple[Sequence[str], dict[str, Any]]] = []
    clean_calls: list[bool] = []

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        # Use subprocess.CompletedProcess directly instead of Mock
        command_list: Sequence[str] = args[0] if args and isinstance(args[0], (list, tuple)) else []
        run_calls.append((command_list, kwargs))
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=0,
            stdout="OK\n",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("scripts.run_tests_bayesian.clean_cache", lambda: clean_calls.append(True))

    result: dict[str, Any] = runner.run_tests_fast()
    assert clean_calls == [True]
    assert len(run_calls) == 1
    command, cmd_kwargs = run_calls[0]
    assert Path(command[0]).resolve() == Path(sys.executable).resolve()
    assert command[2] == "pytest"
    assert "tests/" in command
    assert "--cov=core" in command
    assert "--cov=app" in command
    assert cmd_kwargs["cwd"] == runner.project_root
    assert cmd_kwargs["timeout"] == 600
    assert cmd_kwargs["capture_output"] is True
    assert cmd_kwargs["text"] is True
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)


def test_run_tests_fast_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test failure path with returncode=1."""
    from scripts import run_tests_bayesian as runner

    run_calls: list[tuple[Sequence[str], dict[str, Any]]] = []
    clean_calls: list[bool] = []

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command_list: Sequence[str] = args[0] if args and isinstance(args[0], (list, tuple)) else []
        run_calls.append((command_list, kwargs))
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=1,
            stdout="FAILED tests/test_demo.py::test_example - AssertionError\n",
            stderr="Error occurred",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("scripts.run_tests_bayesian.clean_cache", lambda: clean_calls.append(True))

    result: dict[str, Any] = runner.run_tests_fast()
    assert clean_calls == [True]
    assert len(run_calls) == 1
    command, cmd_kwargs = run_calls[0]
    assert "pytest" in command
    assert cmd_kwargs["cwd"] == runner.project_root
    assert result["success"] is False
    assert result["returncode"] == 1
    assert isinstance(result.get("output"), str)
    assert len(result["failed_tests"]) > 0
    assert result["failed_tests"][0]["name"].startswith("test_example")


def test_run_tests_fast_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test exception handling path."""
    from scripts import run_tests_bayesian as runner

    clean_calls: list[bool] = []

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("pytest command not found")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("scripts.run_tests_bayesian.clean_cache", lambda: clean_calls.append(True))

    result: dict[str, Any] = runner.run_tests_fast()
    assert clean_calls == [True]
    assert result["success"] is False
    # Check for error indication in output (can be in Russian or English)
    output = result.get("output", "").lower()
    assert "error" in output or "ошибка" in output or "exception" in output


def test_run_tests_fast_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test edge case with empty stdout/stderr."""
    from scripts import run_tests_bayesian as runner

    clean_calls: list[bool] = []

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("scripts.run_tests_bayesian.clean_cache", lambda: clean_calls.append(True))

    result: dict[str, Any] = runner.run_tests_fast()
    assert clean_calls == [True]
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)

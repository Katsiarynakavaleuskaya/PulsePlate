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

    monkeypatch.setenv("RUN_TESTS_BAYESIAN_SKIP_NESTED", "0")

    run_calls: list[tuple[list[str], int]] = []
    clean_calls: list[bool] = []

    def fake_run(args: list[str], timeout: int) -> tuple[int, str]:
        run_calls.append((args, timeout))
        return 0, "OK\n"

    monkeypatch.setattr("scripts.run_tests_bayesian._run_pytest_with_timeout", fake_run)
    monkeypatch.setattr("scripts.run_tests_bayesian.clean_cache", lambda: clean_calls.append(True))

    result: dict[str, Any] = runner.run_tests_fast()
    assert clean_calls == [True]
    assert len(run_calls) == 1
    args, timeout = run_calls[0]
    assert args[0] == "tests/"
    assert "--cov=core" in args
    assert "--cov=app" in args
    assert timeout == 600
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)


def test_run_tests_fast_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test failure path with returncode=1."""
    from scripts import run_tests_bayesian as runner

    monkeypatch.setenv("RUN_TESTS_BAYESIAN_SKIP_NESTED", "0")

    run_calls: list[tuple[list[str], int]] = []
    clean_calls: list[bool] = []

    def fake_run(args: list[str], timeout: int) -> tuple[int, str]:
        run_calls.append((args, timeout))
        return (
            1,
            "FAILED tests/test_demo.py::test_example - AssertionError\nError occurred\n",
        )

    monkeypatch.setattr("scripts.run_tests_bayesian._run_pytest_with_timeout", fake_run)
    monkeypatch.setattr("scripts.run_tests_bayesian.clean_cache", lambda: clean_calls.append(True))

    result: dict[str, Any] = runner.run_tests_fast()
    assert clean_calls == [True]
    assert len(run_calls) == 1
    args, timeout = run_calls[0]
    assert "tests/" in args
    assert timeout == 600
    assert result["success"] is False
    assert result["returncode"] == 1
    assert isinstance(result.get("output"), str)
    assert len(result["failed_tests"]) > 0
    assert result["failed_tests"][0]["name"].startswith("test_example")


def test_run_tests_fast_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test exception handling path."""
    from scripts import run_tests_bayesian as runner

    monkeypatch.setenv("RUN_TESTS_BAYESIAN_SKIP_NESTED", "0")
    clean_calls: list[bool] = []

    def fake_run(*args: Any, **kwargs: Any) -> tuple[int, str]:
        raise FileNotFoundError("pytest command not found")

    monkeypatch.setattr("scripts.run_tests_bayesian._run_pytest_with_timeout", fake_run)
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

    monkeypatch.setenv("RUN_TESTS_BAYESIAN_SKIP_NESTED", "0")
    clean_calls: list[bool] = []

    def fake_run(args: list[str], timeout: int) -> tuple[int, str]:
        return 0, ""

    monkeypatch.setattr("scripts.run_tests_bayesian._run_pytest_with_timeout", fake_run)
    monkeypatch.setattr("scripts.run_tests_bayesian.clean_cache", lambda: clean_calls.append(True))

    result: dict[str, Any] = runner.run_tests_fast()
    assert clean_calls == [True]
    assert result["success"] is True
    assert result["returncode"] == 0
    assert isinstance(result.get("output"), str)

"""Unit tests for check_failing_tests.py helpers.

Covers run_test_file() and main() behavior using mocks to avoid spawning
real pytest runs. Ensures deterministic outputs for CI coverage.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest

import check_failing_tests as cft


def test_run_test_file_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return (True, stdout) when subprocess returns code 0."""

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return SimpleNamespace(returncode=0, stdout="OK-OUT", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, out = cft.run_test_file("tests/fake_test_ok.py")
    assert ok is True
    assert out == "OK-OUT"


def test_run_test_file_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return (False, stdout+stderr) when subprocess returns non-zero."""

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return SimpleNamespace(returncode=1, stdout="STDOUT-", stderr="STDERR")

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, out = cft.run_test_file("tests/fake_test_fail.py")
    assert ok is False
    assert out == "STDOUT-STDERR"


def test_run_test_file_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return TIMEOUT message when subprocess times out."""

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=60)

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, out = cft.run_test_file("tests/fake_test_timeout.py")
    assert ok is False
    assert out.startswith("TIMEOUT: Test tests/fake_test_timeout.py timed out")


def test_run_test_file_generic_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return ERROR message including the exception text on generic error."""

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, out = cft.run_test_file("tests/fake_test_error.py")
    assert ok is False
    assert out.startswith("ERROR: boom")


def test_main_mixed_pass_fail_timeout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Main prints a correct summary and returns 1 when any failures/timeouts exist."""

    # Limit discovered files to a controlled set
    monkeypatch.setattr(
        cft.glob,
        "glob",
        lambda pattern: [
            "tests/t_ok.py",
            "tests/t_fail.py",
            "tests/t_to.py",
        ],
    )

    # Make Path.is_file always True for these paths
    monkeypatch.setattr(Path, "is_file", lambda self: True)

    # Provide subprocess.run behavior by filename
    def fake_run(
        cmd: list[str], capture_output: bool, text: bool, timeout: int | None
    ) -> SimpleNamespace:  # noqa: ARG001
        # Find test path by searching for element ending with expected test filename
        test_path = next(
            (
                arg
                for arg in cmd
                if arg.endswith("t_ok.py") or arg.endswith("t_fail.py") or arg.endswith("t_to.py")
            ),
            None,
        )
        if test_path is None:
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")
        if test_path.endswith("t_ok.py"):
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")
        if test_path.endswith("t_fail.py"):
            return SimpleNamespace(returncode=1, stdout="out-", stderr="-err")
        if test_path.endswith("t_to.py"):
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=60)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    exit_code = cft.main()
    captured = capsys.readouterr()
    # 1 failure + 1 timeout => exit code 2
    assert exit_code == 2
    # Summary lines
    assert "✅ Passing: 1" in captured.out
    assert "❌ Failing: 1" in captured.out
    assert "⏰ Timeout: 1" in captured.out
    # Failing list includes file and extracted error line
    assert "❌ Failing tests:" in captured.out
    assert "tests/t_fail.py" in captured.out


def test_main_all_passing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Main returns 0 and summary shows all passing when no failures/timeouts."""

    monkeypatch.setattr(
        cft.glob,
        "glob",
        lambda pattern: [
            "tests/t_ok1.py",
            "tests/t_ok2.py",
        ],
    )
    monkeypatch.setattr(Path, "is_file", lambda self: True)

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    exit_code = cft.main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "✅ Passing: 2" in captured.out
    assert "❌ Failing: 0" in captured.out
    assert "⏰ Timeout: 0" in captured.out

"""Deterministic tests for local verify environment parity checks."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.ci.check_local_verify_environment as env_gate


def test_collect_missing_modules_returns_only_failed_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import(module_name: str) -> str | None:
        if module_name == "coverage":
            return "No module named 'coverage'"
        return None

    monkeypatch.setattr(env_gate, "_import_module", fake_import)

    missing = env_gate.collect_missing_modules(
        (
            ("pytest", "test-fast"),
            ("coverage", "diff-cov"),
        ),
    )

    assert missing == [("coverage", "diff-cov", "No module named 'coverage'")]


def test_build_failure_output_includes_recovery_commands() -> None:
    lines = env_gate.build_failure_output(
        python_executable=Path("/tmp/.venv/bin/python"),
        missing_modules=[
            (
                "opentelemetry.sdk.trace.export.in_memory_span_exporter",
                "tests/test_genai_tracing.py",
                "No module named 'opentelemetry'",
            )
        ],
        missing_executables=[("flake8", "lint", "console entrypoint missing")],
    )

    assert "ERROR: local verify environment is incomplete." in lines
    assert any("make venv" in line for line in lines)
    assert any("make venv-sync" in line for line in lines)
    assert any("console entrypoint missing" in line for line in lines)


def test_collect_missing_executables_returns_missing_tools(monkeypatch) -> None:
    def fake_which(executable_name: str, path: str | None = None) -> str | None:
        if executable_name == "pytest":
            return None
        return f"/tmp/{executable_name}"

    monkeypatch.setattr(env_gate.shutil, "which", fake_which)

    missing = env_gate.collect_missing_executables(
        Path("/tmp/.venv/bin"),
        (
            ("flake8", "lint"),
            ("pytest", "test-fast"),
        ),
    )

    assert missing == [("pytest", "test-fast", "console entrypoint missing in /tmp/.venv/bin")]


def test_main_fails_when_venv_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(env_gate, "VENV_PYTHON", tmp_path / ".venv" / "bin" / "python")

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Run `make venv` before `make verify`." in captured.out


def test_main_fails_when_running_outside_repo_venv(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    system_python = tmp_path / "system-python"
    system_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(env_gate.sys, "executable", str(system_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(tmp_path / "system-prefix"))

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "verify-env must run inside the repo .venv interpreter." in captured.out


def test_main_fails_when_verify_dependencies_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(
        env_gate,
        "collect_missing_modules",
        lambda: [
            ("diff_cover", "diff-cov", "No module named 'diff_cover'"),
        ],
    )
    monkeypatch.setattr(env_gate, "collect_missing_executables", lambda venv_bin_dir: [])

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Missing verify-critical modules or entrypoints:" in captured.out
    assert "diff_cover [diff-cov]" in captured.out


def test_main_passes_when_venv_and_dependencies_are_ready(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(env_gate, "collect_missing_modules", lambda: [])
    monkeypatch.setattr(env_gate, "collect_missing_executables", lambda venv_bin_dir: [])

    result = env_gate.main()

    assert result == 0
    captured = capsys.readouterr()
    assert "verify-env: local verify environment passed." in captured.out

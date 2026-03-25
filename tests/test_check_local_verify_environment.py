"""Deterministic tests for local verify environment parity checks."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.ci.check_local_verify_environment as env_gate

REPO_ROOT = Path(__file__).resolve().parents[1]


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
                "diff_cover.diff_cover_tool",
                "diff-cov",
                "No module named 'diff_cover'",
            )
        ],
    )

    assert "ERROR: local verify environment is incomplete." in lines
    assert any("make venv" in line for line in lines)
    assert any("make venv-sync" in line for line in lines)
    assert "Missing verify-critical Python modules:" in lines


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
            (
                "diff_cover.diff_cover_tool",
                "diff-cov",
                "No module named 'diff_cover'",
            ),
        ],
    )

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Missing verify-critical Python modules:" in captured.out
    assert "diff_cover.diff_cover_tool [diff-cov]" in captured.out


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

    result = env_gate.main()

    assert result == 0
    captured = capsys.readouterr()
    assert "verify-env: local verify environment passed." in captured.out


def test_main_ignores_stale_console_wrapper_when_module_parity_is_healthy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / ".venv" / "bin" / "python"
    stale_wrapper = tmp_path / ".venv" / "bin" / "flake8"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")
    stale_wrapper.write_text("#!/tmp/deleted-python\nprint('stale')\n", encoding="utf-8")

    monkeypatch.setattr(env_gate, "VENV_PYTHON", fake_python)
    monkeypatch.setattr(env_gate, "VENV_DIR", fake_python.parent.parent)
    monkeypatch.setattr(env_gate, "VENV_BIN_DIR", fake_python.parent)
    monkeypatch.setattr(env_gate.sys, "executable", str(fake_python))
    monkeypatch.setattr(env_gate.sys, "prefix", str(fake_python.parent.parent))
    monkeypatch.setattr(env_gate, "collect_missing_modules", lambda: [])

    result = env_gate.main()

    assert result == 0
    captured = capsys.readouterr()
    assert "verify-env: local verify environment passed." in captured.out


def test_verify_critical_make_targets_use_repo_interpreter_module_mode() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    expected_commands = (
        "$(VENV_PYTHON) -m flake8 .",
        "$(VENV_PYTHON) -m mypy --no-incremental --cache-dir=/dev/null app core",
        "$(VENV_PYTHON) -m pytest -q tests/edges tests/test_remaining_modules.py --maxfail=3",
        "$(VENV_PYTHON) -m coverage erase",
        "$(VENV_PYTHON) -m coverage run -m pytest",
        "$(VENV_PYTHON) -m diff_cover.diff_cover_tool coverage.xml --compare-branch=origin/main --fail-under=97",
    )

    for command in expected_commands:
        assert command in makefile_text

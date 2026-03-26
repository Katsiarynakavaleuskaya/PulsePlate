"""Deterministic tests for local verify environment parity checks."""

from __future__ import annotations

from pathlib import Path
import re

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
        unexpected_startup_hooks=[],
    )

    assert "ERROR: local verify environment is incomplete." in lines
    assert any("make venv" in line for line in lines)
    assert any("make venv-sync" in line for line in lines)
    assert "Missing verify-critical Python modules:" in lines


def test_collect_unexpected_startup_hooks_uses_guard_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")
    observed_command: list[str] = []

    class Result:
        returncode = 1
        stdout = (
            "ERROR: unexpected executable Python startup hook (.pth) detected.\n"
            "- /tmp/litellm_init.pth:1 :: import os\n"
        )
        stderr = ""

    def fake_run(command: list[str], **kwargs: object) -> Result:
        observed_command[:] = command
        return Result()

    monkeypatch.setattr(env_gate, "STARTUP_HOOK_GUARD", guard_script)
    monkeypatch.setattr(env_gate, "VENV_PYTHON", venv_python)
    monkeypatch.setattr(env_gate.subprocess, "run", fake_run)

    findings = env_gate.collect_unexpected_startup_hooks()

    assert observed_command == [
        str(venv_python),
        "-S",
        str(guard_script),
        "--python-executable",
        str(venv_python),
    ]
    assert findings == [
        env_gate.StartupHookFinding(
            path=Path("/tmp/litellm_init.pth"),
            line_number=1,
            line="import os",
        )
    ]


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
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])

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
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])

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
    monkeypatch.setattr(env_gate, "collect_unexpected_startup_hooks", lambda: [])

    result = env_gate.main()

    assert result == 0
    captured = capsys.readouterr()
    assert "verify-env: local verify environment passed." in captured.out


def test_main_fails_when_unexpected_startup_hook_is_present(
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
    monkeypatch.setattr(
        env_gate,
        "collect_unexpected_startup_hooks",
        lambda: [
            env_gate.StartupHookFinding(
                path=Path("/tmp/litellm_init.pth"),
                line_number=1,
                line="import os",
            )
        ],
    )

    result = env_gate.main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Unexpected executable startup hooks (.pth):" in captured.out
    assert "/tmp/litellm_init.pth:1 :: import os" in captured.out


def _target_recipe(makefile_text: str, target_name: str) -> str:
    """Return the recipe body for a Makefile target."""

    target_pattern = re.compile(rf"(?m)^{re.escape(target_name)}:.*\n(?P<body>(?:\t[^\n]*\n)+)")
    match = target_pattern.search(makefile_text)
    assert match, f"missing Makefile target: {target_name}"
    return match.group("body")


def test_verify_critical_make_targets_use_repo_interpreter_module_mode() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    expected_recipe_parts = {
        "lint": ("$(VENV_PYTHON) -m flake8",),
        "typecheck": (
            "$(VENV_PYTHON) -m mypy",
            "--no-incremental",
            "--cache-dir=/dev/null",
        ),
        "test-fast": ("$(VENV_PYTHON) -m pytest", "tests/edges", "--maxfail=3"),
        "cov": (
            "$(VENV_PYTHON) -m coverage erase",
            "$(VENV_PYTHON) -m coverage run -m pytest -q",
            "$(VENV_PYTHON) -m coverage report -m",
            "$(VENV_PYTHON) -m coverage xml",
        ),
        "diff-cov": (
            "$(VENV_PYTHON) -m coverage erase",
            "$(VENV_PYTHON) -m coverage run -m pytest -q",
            "$(VENV_PYTHON) -m diff_cover.diff_cover_tool",
            "--compare-branch=origin/main",
            "--fail-under=97",
        ),
    }

    for target_name, required_parts in expected_recipe_parts.items():
        recipe_body = _target_recipe(makefile_text, target_name)
        assert "$(VENV_PYTHON) -m" in recipe_body
        for required_part in required_parts:
            assert required_part in recipe_body

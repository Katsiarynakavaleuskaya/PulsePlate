"""Deterministic tests for locked Python requirement installation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.ci.install_locked_python_requirements as installer


def test_resolve_requirement_files_prefers_dev_only_when_requested(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pytest==8.4.2\n", encoding="utf-8")

    files = installer.resolve_requirement_files(
        requirements_file=requirements,
        dev_requirements_file=requirements_dev,
        install_dev=True,
    )

    assert files == [requirements, requirements_dev]


def test_build_pip_download_command_uses_constraint_when_present(tmp_path: Path) -> None:
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("openai>=2.29.0\n", encoding="utf-8")

    command = installer.build_pip_download_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        wheelhouse_dir=tmp_path / "wheelhouse",
        constraints_file=constraints,
    )

    assert command[:4] == ["python", "-m", "pip", "download"]
    assert "--dest" in command
    assert "--constraint" in command


def test_build_pip_install_command_is_hermetic(tmp_path: Path) -> None:
    command = installer.build_pip_install_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        wheelhouse_dir=tmp_path / "wheelhouse",
        constraints_file=None,
    )

    assert command[:4] == ["python", "-m", "pip", "install"]
    assert "--no-index" in command
    assert "--find-links" in command


def test_is_virtualenv_python_detects_virtualenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Result:
        stdout = json.dumps({"prefix": "/tmp/.venv", "base_prefix": "/usr/local"})

    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: Result())

    assert installer.is_virtualenv_python("python") is True


def test_main_fails_when_virtualenv_is_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    monkeypatch.setattr(installer, "DEFAULT_REQUIREMENTS_FILE", requirements)
    monkeypatch.setattr(installer, "DEFAULT_DEV_REQUIREMENTS_FILE", tmp_path / "missing-dev.txt")
    monkeypatch.setattr(installer, "DEFAULT_CONSTRAINTS_FILE", tmp_path / "missing-constraints.txt")
    monkeypatch.setattr(installer, "is_virtualenv_python", lambda python_executable: False)

    result = installer.main(
        [
            "--requirements-file",
            str(requirements),
            "--require-virtualenv",
        ]
    )

    assert result == 1
    assert (
        "refusing to install packages with a non-virtualenv interpreter" in capsys.readouterr().out
    )


def test_main_runs_upgrade_download_install_and_static_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: [],
    )

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--wheelhouse-dir",
            str(wheelhouse_dir),
            "--guard-script",
            str(guard_script),
        ]
    )

    assert result == 0
    assert observed_commands[0] == ["python", "-m", "pip", "install", "--upgrade", "pip"]

    download_command = observed_commands[1]
    assert download_command[:4] == ["python", "-m", "pip", "download"]
    assert "--dest" in download_command
    assert str(wheelhouse_dir) in download_command
    assert "--requirement" in download_command
    assert str(requirements) in download_command
    assert "--constraint" in download_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in download_command

    install_command = observed_commands[2]
    assert install_command[:4] == ["python", "-m", "pip", "install"]
    assert "--no-index" in install_command
    assert "--find-links" in install_command
    assert str(wheelhouse_dir) in install_command
    assert "--constraint" in install_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in install_command


def test_main_fails_when_static_startup_hook_scan_finds_malicious_pth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")

    monkeypatch.setattr(installer, "run_command", lambda command: None)
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: [
            "ERROR: unexpected executable Python startup hook (.pth) detected.",
            "- /tmp/litellm_init.pth:1 :: import os",
        ],
    )

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--wheelhouse-dir",
            str(wheelhouse_dir),
            "--guard-script",
            str(guard_script),
        ]
    )

    assert result == 1
    assert "litellm_init.pth:1 :: import os" in capsys.readouterr().out

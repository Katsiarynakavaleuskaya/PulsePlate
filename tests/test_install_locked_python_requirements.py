"""Deterministic tests for locked Python requirement installation helpers."""

from __future__ import annotations

from pathlib import Path
import json

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

"""Deterministic tests for locked Python requirement installation helpers."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import subprocess

import pytest

import scripts.ci.install_locked_python_requirements as installer

APPROVED_PROXY_URL = "https://packages.example.internal/simple"


@pytest.fixture(autouse=True)
def isolate_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(installer.APPROVED_INDEX_ENV_VAR, raising=False)
    monkeypatch.delenv(installer.TRUSTED_HOST_ENV_VAR, raising=False)
    for env_var in installer.AMBIENT_INDEX_OVERRIDE_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


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


def test_resolve_requirement_files_fails_when_runtime_file_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=tmp_path / "requirements.txt",
            dev_requirements_file=tmp_path / "requirements-dev.txt",
            install_dev=False,
        )


def test_resolve_requirement_files_fails_when_dev_file_is_requested_but_missing(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Dev requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=requirements,
            dev_requirements_file=tmp_path / "requirements-dev.txt",
            install_dev=True,
        )


def test_build_pip_download_command_uses_constraint_when_present(tmp_path: Path) -> None:
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("openai>=2.29.0\n", encoding="utf-8")

    command = installer.build_pip_download_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        wheelhouse_dir=tmp_path / "wheelhouse",
        constraints_file=constraints,
        index_url=APPROVED_PROXY_URL,
        trusted_host="packages.example.internal",
    )

    assert command[:4] == ["python", "-m", "pip", "download"]
    assert "--only-binary" in command
    assert ":all:" in command
    assert "--dest" in command
    assert "--index-url" in command
    assert APPROVED_PROXY_URL in command
    assert "--trusted-host" in command
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


def test_validate_private_proxy_url_rejects_public_hosts() -> None:
    with pytest.raises(RuntimeError, match="must not point to public host"):
        installer.validate_private_proxy_url("https://pypi.org/simple")


def test_validate_private_proxy_url_strips_whitespace_and_trailing_dot() -> None:
    normalized = installer.validate_private_proxy_url(
        "  https://packages.example.internal/simple  "
    )

    assert normalized == "https://packages.example.internal/simple"

    with pytest.raises(RuntimeError, match="must not point to public host"):
        installer.validate_private_proxy_url("https://pypi.org./simple")


def test_resolve_private_proxy_settings_requires_explicit_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="Approved Python package proxy is required"):
        installer.resolve_private_proxy_settings(index_url=None, trusted_host=None)


def test_resolve_private_proxy_settings_rejects_ambient_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIP_EXTRA_INDEX_URL", "https://malicious.example/simple")

    with pytest.raises(RuntimeError, match="Ambient Python package index overrides are forbidden"):
        installer.resolve_private_proxy_settings(
            index_url=APPROVED_PROXY_URL,
            trusted_host=None,
        )


def test_build_pip_download_command_fails_when_constraints_file_is_missing(
    tmp_path: Path,
) -> None:
    missing_constraints = tmp_path / "missing-constraints.txt"

    with pytest.raises(FileNotFoundError, match="Constraints file not found"):
        installer.build_pip_download_command(
            python_executable="python",
            requirement_file=tmp_path / "requirements.txt",
            wheelhouse_dir=tmp_path / "wheelhouse",
            constraints_file=missing_constraints,
            index_url=APPROVED_PROXY_URL,
            trusted_host=None,
        )


def test_is_virtualenv_python_detects_virtualenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Result:
        stdout = json.dumps({"prefix": "/tmp/.venv", "base_prefix": "/usr/local"})

    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: Result())

    assert installer.is_virtualenv_python("python") is True


def test_is_virtualenv_python_wraps_probe_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_called_process_error(*args: object, **kwargs: object) -> object:
        raise subprocess.CalledProcessError(returncode=1, cmd=["python", "-c", "probe"])

    monkeypatch.setattr(installer.subprocess, "run", raise_called_process_error)

    with pytest.raises(RuntimeError, match="Unable to probe virtualenv state"):
        installer.is_virtualenv_python("python")


def test_run_command_wraps_subprocess_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_called_process_error(*args: object, **kwargs: object) -> object:
        raise subprocess.CalledProcessError(returncode=1, cmd=["python", "-m", "pip"])

    monkeypatch.setattr(installer.subprocess, "run", raise_called_process_error)

    with pytest.raises(RuntimeError, match="Command failed: python -m pip"):
        installer.run_command(["python", "-m", "pip"])


def test_main_fails_when_virtualenv_is_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("openai==2.29.0\n", encoding="utf-8")
    monkeypatch.setattr(installer, "DEFAULT_REQUIREMENTS_FILE", requirements)
    monkeypatch.setattr(installer, "DEFAULT_DEV_REQUIREMENTS_FILE", tmp_path / "missing-dev.txt")
    monkeypatch.setattr(installer, "DEFAULT_CONSTRAINTS_FILE", constraints)
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


def test_collect_startup_hook_failure_lines_uses_guard_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_command: list[str] = []

    class Result:
        returncode = 1
        stdout = "ERROR: unexpected executable Python startup hook (.pth) detected.\n- /tmp/hook.pth:1 :: import os\n"
        stderr = ""

    def fake_run(command: list[str], **kwargs: object) -> Result:
        observed_command[:] = command
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    failure_lines = installer.collect_startup_hook_failure_lines(
        guard_script=Path("/tmp/check_python_startup_hooks.py"),
        python_executable="python",
    )

    assert observed_command == [
        "python",
        "-S",
        "/tmp/check_python_startup_hooks.py",
        "--python-executable",
        "python",
    ]
    assert failure_lines == [
        "ERROR: unexpected executable Python startup hook (.pth) detected.",
        "- /tmp/hook.pth:1 :: import os",
    ]


def test_main_runs_download_install_and_static_guard_without_pip_self_upgrade(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []
    observed_guard_python: list[str] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        assert target_python == "python"
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: observed_guard_python.append(kwargs["python_executable"]) or [],
    )
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

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
    download_command = observed_commands[0]
    assert download_command[:4] == ["python", "-m", "pip", "download"]
    assert "--only-binary" in download_command
    assert ":all:" in download_command
    assert "--dest" in download_command
    assert str(wheelhouse_dir) in download_command
    assert "--requirement" in download_command
    assert str(requirements) in download_command
    assert "--index-url" in download_command
    assert APPROVED_PROXY_URL in download_command
    assert "--constraint" in download_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in download_command

    staging_install_command = observed_commands[1]
    assert staging_install_command[:4] == ["staging-python", "-m", "pip", "install"]
    assert "--no-index" in staging_install_command
    assert "--find-links" in staging_install_command
    assert str(wheelhouse_dir) in staging_install_command
    assert "--constraint" in staging_install_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in staging_install_command

    install_command = observed_commands[2]
    assert install_command[:4] == ["python", "-m", "pip", "install"]
    assert "--no-index" in install_command
    assert "--find-links" in install_command
    assert str(wheelhouse_dir) in install_command
    assert "--constraint" in install_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in install_command
    assert observed_guard_python == ["staging-python"]


def test_main_runs_optional_pip_upgrade_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    observed_commands: list[list[str]] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(installer, "collect_startup_hook_failure_lines", lambda **kwargs: [])
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--wheelhouse-dir",
            str(wheelhouse_dir),
            "--upgrade-pip",
        ]
    )

    assert result == 0
    assert observed_commands[0] == [
        "python",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "--index-url",
        APPROVED_PROXY_URL,
    ]


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
    observed_commands: list[list[str]] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: [
            "ERROR: unexpected executable Python startup hook (.pth) detected.",
            "- /tmp/litellm_init.pth:1 :: import os",
        ],
    )
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

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
    assert observed_commands[0][:4] == ["python", "-m", "pip", "download"]
    assert observed_commands[1][:4] == ["staging-python", "-m", "pip", "install"]
    assert not any(
        command[:4] == ["python", "-m", "pip", "install"] for command in observed_commands[2:]
    )


def test_main_reports_missing_requirements_file_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_requirements = tmp_path / "missing-requirements.txt"

    result = installer.main(
        [
            "--requirements-file",
            str(missing_requirements),
            "--index-url",
            APPROVED_PROXY_URL,
        ]
    )

    assert result == 1
    assert (
        f"ERROR: locked install failed: Requirements file not found: {missing_requirements}"
        in capsys.readouterr().out
    )


def test_main_reports_missing_constraints_file_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    missing_constraints = tmp_path / "missing-constraints.txt"

    result = installer.main(
        [
            "--requirements-file",
            str(requirements),
            "--constraints-file",
            str(missing_constraints),
            "--index-url",
            APPROVED_PROXY_URL,
        ]
    )

    assert result == 1
    assert (
        f"ERROR: locked install failed: Constraints file not found: {missing_constraints}"
        in capsys.readouterr().out
    )


def test_main_reports_guard_runtime_error_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    guard_script = tmp_path / "missing-guard.py"

    monkeypatch.setattr(installer, "run_command", lambda command: None)
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("guard subprocess failed")),
    )
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

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
    assert "ERROR: locked install failed: guard subprocess failed" in capsys.readouterr().out


def test_main_reports_missing_private_proxy_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")

    result = installer.main(["--requirements-file", str(requirements)])

    assert result == 1
    assert "Approved Python package proxy is required" in capsys.readouterr().out

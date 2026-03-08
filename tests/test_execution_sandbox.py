"""Deterministic tests for local execution sandbox."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.security import agent_control_plane as cp
from app.security import execution_sandbox as sandbox
from scripts.orchestration import run_local_sandbox as sandbox_cli


@pytest.fixture
def sandbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide isolated sandbox root and required policy env."""

    monkeypatch.setenv(sandbox.SANDBOX_ENABLED_ENV, "true")
    monkeypatch.setenv(sandbox.SANDBOX_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(sandbox.SANDBOX_ALLOWED_BINARIES_ENV, "python3,pytest")
    monkeypatch.setenv(cp.ALLOWLIST_ENV, "sandbox.exec:local://sandbox")
    return tmp_path


def test_sandbox_enabled_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(sandbox.SANDBOX_ENABLED_ENV, raising=False)
    assert sandbox.sandbox_enabled() is False


def test_require_sandbox_enabled_raises_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(sandbox.SANDBOX_ENABLED_ENV, raising=False)
    with pytest.raises(RuntimeError, match=sandbox.SANDBOX_ENABLED_ENV):
        sandbox.require_sandbox_enabled()


def test_timeout_and_output_limits_use_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(sandbox.SANDBOX_TIMEOUT_ENV, raising=False)
    monkeypatch.delenv(sandbox.SANDBOX_MAX_OUTPUT_ENV, raising=False)
    assert sandbox.require_sandbox_timeout_seconds() == sandbox.DEFAULT_SANDBOX_TIMEOUT_SECONDS
    assert sandbox.require_sandbox_max_output_bytes() == sandbox.DEFAULT_SANDBOX_MAX_OUTPUT_BYTES


def test_default_allowed_binaries_exclude_python_interpreters() -> None:
    assert "python" not in sandbox.DEFAULT_ALLOWED_BINARIES
    assert "python3" not in sandbox.DEFAULT_ALLOWED_BINARIES


def test_default_allowed_binaries_keep_full_gates_opt_in() -> None:
    assert "coverage" not in sandbox.DEFAULT_ALLOWED_BINARIES
    assert "diff-cover" not in sandbox.DEFAULT_ALLOWED_BINARIES


def test_parse_allowed_binaries_skips_duplicates() -> None:
    parsed = sandbox.parse_allowed_binaries("python3,\npython3,pytest")
    assert parsed == ("python3", "pytest")


def test_parse_allowed_binaries_rejects_paths() -> None:
    with pytest.raises(RuntimeError, match=sandbox.SANDBOX_ALLOWED_BINARIES_ENV):
        sandbox.parse_allowed_binaries("/usr/bin/python3")


def test_require_sandbox_timeout_seconds_rejects_non_integer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_TIMEOUT_ENV, "abc")
    with pytest.raises(RuntimeError, match="integer >= 1"):
        sandbox.require_sandbox_timeout_seconds()


def test_require_sandbox_max_output_bytes_rejects_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_MAX_OUTPUT_ENV, "0")
    with pytest.raises(RuntimeError, match="integer >= 1"):
        sandbox.require_sandbox_max_output_bytes()


def test_load_allowed_binaries_rejects_empty_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_ALLOWED_BINARIES_ENV, ", , ,")
    with pytest.raises(RuntimeError, match="must contain at least one binary"):
        sandbox.load_allowed_binaries()


def test_resolve_sandbox_root_rejects_missing_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing-root"
    monkeypatch.setenv(sandbox.SANDBOX_ROOT_ENV, str(missing_root))
    with pytest.raises(RuntimeError, match="missing path"):
        sandbox.resolve_sandbox_root()


def test_resolve_sandbox_root_requires_explicit_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(sandbox.SANDBOX_ROOT_ENV, raising=False)
    with pytest.raises(RuntimeError, match=sandbox.SANDBOX_ROOT_ENV):
        sandbox.resolve_sandbox_root()


def test_resolve_sandbox_root_rejects_file_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    not_a_dir = tmp_path / "sandbox.txt"
    not_a_dir.write_text("sandbox")
    monkeypatch.setenv(sandbox.SANDBOX_ROOT_ENV, str(not_a_dir))
    with pytest.raises(RuntimeError, match="must point to a directory"):
        sandbox.resolve_sandbox_root()


def test_resolve_sandbox_cwd_defaults_to_root(sandbox_root: Path) -> None:
    assert sandbox.resolve_sandbox_cwd(None, root=sandbox_root) == sandbox_root


def test_resolve_sandbox_cwd_accepts_relative_child(sandbox_root: Path) -> None:
    child_dir = sandbox_root / "child"
    child_dir.mkdir()
    assert sandbox.resolve_sandbox_cwd("child", root=sandbox_root) == child_dir


def test_resolve_sandbox_cwd_rejects_escape(
    sandbox_root: Path,
) -> None:
    outside_dir = sandbox_root.parent
    with pytest.raises(RuntimeError, match="sandbox cwd"):
        sandbox.resolve_sandbox_cwd(outside_dir, root=sandbox_root)


def test_resolve_sandbox_cwd_rejects_missing_directory(sandbox_root: Path) -> None:
    with pytest.raises(RuntimeError, match="does not exist"):
        sandbox.resolve_sandbox_cwd("missing", root=sandbox_root)


def test_resolve_sandbox_cwd_rejects_file_path(sandbox_root: Path) -> None:
    file_path = sandbox_root / "payload.txt"
    file_path.write_text("payload")
    with pytest.raises(RuntimeError, match="must be a directory"):
        sandbox.resolve_sandbox_cwd(file_path, root=sandbox_root)


def test_sanitize_sandbox_env_rejects_sensitive_keys() -> None:
    suspicious_key = "_".join(("OPENAI", "API", "KEY"))
    with pytest.raises(PermissionError, match="Sensitive env key"):
        sandbox.sanitize_sandbox_env({suspicious_key: "secret"})


def test_sanitize_sandbox_env_rejects_loader_injection_keys() -> None:
    with pytest.raises(PermissionError, match="Loader env key"):
        sandbox.sanitize_sandbox_env({"LD_PRELOAD": "/tmp/libinject.so"})


def test_sanitize_sandbox_env_keeps_safe_extra_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", "/tmp/home")
    sanitized = sandbox.sanitize_sandbox_env({"PULSEPLATE_SAFE_FLAG": "1"})
    assert sanitized["HOME"] == "/tmp/home"
    assert sanitized["PULSEPLATE_SAFE_FLAG"] == "1"


def test_sanitize_sandbox_env_rejects_unallowlisted_extra_env_key() -> None:
    with pytest.raises(PermissionError, match="not allowlisted"):
        sandbox.sanitize_sandbox_env({"SAFE_FLAG": "1"})


def test_sanitize_sandbox_env_does_not_inherit_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/tmp/injected")
    sanitized = sandbox.sanitize_sandbox_env()
    assert "PYTHONPATH" not in sanitized


def test_resolve_allowed_binary_rejects_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox.shutil, "which", lambda _binary: None)
    with pytest.raises(RuntimeError, match="not found on PATH"):
        sandbox.resolve_allowed_binary("python3", allowed_binaries=("python3",))


def test_coerce_output_decodes_bytes() -> None:
    assert sandbox._coerce_output(b"hello") == "hello"


def test_run_local_sandbox_executes_allowlisted_python(
    sandbox_root: Path,
) -> None:
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3",
            args=("-c", "print('sandbox-ok')"),
            cwd=sandbox_root,
        )
    )
    assert result.returncode == 0
    assert result.stdout == "sandbox-ok\n"
    assert result.stderr == ""
    assert result.timed_out is False
    assert result.truncated is False
    assert result.cwd == str(sandbox_root)
    assert Path(result.argv[0]).is_absolute()


def test_run_local_sandbox_rejects_disallowed_binary(sandbox_root: Path) -> None:
    with pytest.raises(PermissionError, match="not allowlisted"):
        sandbox.run_local_sandbox(
            sandbox.SandboxRequest(binary="bash", args=("-lc", "echo blocked"), cwd=sandbox_root)
        )


def test_run_local_sandbox_blocks_blocked_execution_mode(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(cp.EXECUTION_MODE_ENV, cp.EXECUTION_MODE_BLOCKED)
    with pytest.raises(PermissionError, match="Execution mode blocked"):
        sandbox.run_local_sandbox(
            sandbox.SandboxRequest(binary="python3", args=("-c", "print('x')"), cwd=sandbox_root)
        )


def test_run_local_sandbox_request_mode_cannot_relax_blocked_runtime(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(cp.EXECUTION_MODE_ENV, cp.EXECUTION_MODE_BLOCKED)
    with pytest.raises(PermissionError, match="Execution mode blocked"):
        sandbox.run_local_sandbox(
            sandbox.SandboxRequest(
                binary="python3",
                args=("-c", "print('x')"),
                cwd=sandbox_root,
                mode=cp.EXECUTION_MODE_AUTO_SAFE,
            )
        )


def test_run_local_sandbox_request_mode_can_tighten_runtime(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(cp.EXECUTION_MODE_ENV, raising=False)
    with pytest.raises(PermissionError, match="review-required"):
        sandbox.run_local_sandbox(
            sandbox.SandboxRequest(
                binary="python3",
                args=("-c", "print('x')"),
                cwd=sandbox_root,
                mode=cp.EXECUTION_MODE_REVIEW_REQUIRED,
            )
        )


def test_run_local_sandbox_times_out(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_TIMEOUT_ENV, "1")
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3",
            args=("-c", "import signal; signal.pause()"),
            cwd=sandbox_root,
        )
    )
    assert result.returncode == 124
    assert result.timed_out is True


def test_run_local_sandbox_stream_limits_stdout_during_execution(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_MAX_OUTPUT_ENV, "8")
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3",
            args=(
                "-c",
                (
                    "import sys, time;"
                    "sys.stdout.write('01234567');"
                    "sys.stdout.flush();"
                    "time.sleep(0.05);"
                    "sys.stdout.write('89abcdef');"
                    "sys.stdout.flush()"
                ),
            ),
            cwd=sandbox_root,
        )
    )
    assert result.returncode == 0
    assert result.truncated is True
    assert len(result.stdout.encode("utf-8")) <= 8


def test_run_local_sandbox_stream_limits_stderr_during_execution(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_MAX_OUTPUT_ENV, "8")
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3",
            args=(
                "-c",
                (
                    "import sys, time;"
                    "sys.stderr.write('abcdefgh');"
                    "sys.stderr.flush();"
                    "time.sleep(0.05);"
                    "sys.stderr.write('ijklmnop');"
                    "sys.stderr.flush()"
                ),
            ),
            cwd=sandbox_root,
        )
    )
    assert result.returncode == 0
    assert result.truncated is True
    assert len(result.stderr.encode("utf-8")) <= 8


def test_run_local_sandbox_cli_emits_deterministic_json(sandbox_root: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "orchestration" / "run_local_sandbox.py"
    env = os.environ.copy()
    env[sandbox.SANDBOX_ENABLED_ENV] = "true"
    env[sandbox.SANDBOX_ROOT_ENV] = str(sandbox_root)
    env[cp.ALLOWLIST_ENV] = "sandbox.exec:local://sandbox"

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--binary",
            "python3",
            "--cwd",
            str(sandbox_root),
            "--",
            "-c",
            "print('cli-ok')",
        ],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["returncode"] == 0
    assert payload["stdout"] == "cli-ok\n"
    assert payload["stderr"] == ""
    assert payload["timed_out"] is False
    assert payload["truncated"] is False


def test_run_local_sandbox_cli_emits_json_on_permission_error(sandbox_root: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "orchestration" / "run_local_sandbox.py"
    env = os.environ.copy()
    env[sandbox.SANDBOX_ENABLED_ENV] = "true"
    env[sandbox.SANDBOX_ROOT_ENV] = str(sandbox_root)
    env[cp.ALLOWLIST_ENV] = "sandbox.exec:local://sandbox"
    env[cp.EXECUTION_MODE_ENV] = cp.EXECUTION_MODE_BLOCKED

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--binary",
            "python3",
            "--cwd",
            str(sandbox_root),
            "--",
            "-c",
            "print('cli-ok')",
        ],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["returncode"] == 1
    assert payload["stdout"] == ""
    assert "Execution mode blocked" in payload["stderr"]
    assert payload["timed_out"] is False
    assert payload["truncated"] is False


def test_run_local_sandbox_cli_emits_json_on_argument_error(
    sandbox_root: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "orchestration" / "run_local_sandbox.py"
    env = os.environ.copy()
    env[sandbox.SANDBOX_ENABLED_ENV] = "true"
    env[sandbox.SANDBOX_ROOT_ENV] = str(sandbox_root)
    env[sandbox.SANDBOX_ALLOWED_BINARIES_ENV] = "python3,pytest"
    env[cp.ALLOWLIST_ENV] = "sandbox.exec:local://sandbox"

    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["returncode"] == 1
    assert payload["argv"] == []
    assert "CLI argument error" in payload["stderr"]
    assert payload["timed_out"] is False
    assert payload["truncated"] is False


def test_run_local_sandbox_cli_emits_json_on_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _raise_unexpected(
        _request: sandbox.SandboxRequest,
    ) -> sandbox.SandboxResult:
        raise ValueError("unexpected sandbox failure")

    monkeypatch.setattr(sandbox_cli, "run_local_sandbox", _raise_unexpected)

    exit_code = sandbox_cli.main(["--binary", "python3", "--", "-c", "print('x')"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["returncode"] == 1
    assert payload["argv"] == ["python3", "-c", "print('x')"]
    assert payload["stdout"] == ""
    assert payload["stderr"] == "unexpected sandbox failure"

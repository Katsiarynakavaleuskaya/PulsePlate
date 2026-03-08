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


@pytest.fixture
def sandbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide isolated sandbox root and required policy env."""

    monkeypatch.setenv(sandbox.SANDBOX_ENABLED_ENV, "true")
    monkeypatch.setenv(sandbox.SANDBOX_ROOT_ENV, str(tmp_path))
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


def test_parse_allowed_binaries_skips_duplicates() -> None:
    parsed = sandbox.parse_allowed_binaries("python3,\npython3,pytest")
    assert parsed == ("python3", "pytest")


def test_parse_allowed_binaries_rejects_paths() -> None:
    with pytest.raises(RuntimeError, match=sandbox.SANDBOX_ALLOWED_BINARIES_ENV):
        sandbox.parse_allowed_binaries("/usr/bin/python3")


def test_parse_positive_int_rejects_non_integer() -> None:
    with pytest.raises(RuntimeError, match="integer >= 1"):
        sandbox._parse_positive_int("abc", env_name="TEST_ENV", default=1)


def test_parse_positive_int_rejects_zero() -> None:
    with pytest.raises(RuntimeError, match="integer >= 1"):
        sandbox._parse_positive_int("0", env_name="TEST_ENV", default=1)


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
    sanitized = sandbox.sanitize_sandbox_env({"SAFE_FLAG": "1"})
    assert sanitized["HOME"] == "/tmp/home"
    assert sanitized["SAFE_FLAG"] == "1"


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


def test_run_local_sandbox_truncates_output(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_MAX_OUTPUT_ENV, "8")
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3",
            args=("-c", "print('0123456789abcdef')"),
            cwd=sandbox_root,
        )
    )
    assert result.returncode == 0
    assert result.truncated is True
    assert len(result.stdout.encode("utf-8")) <= 8


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

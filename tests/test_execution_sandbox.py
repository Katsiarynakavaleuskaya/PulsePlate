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


def test_resolve_sandbox_cwd_rejects_escape(
    sandbox_root: Path,
) -> None:
    outside_dir = sandbox_root.parent
    with pytest.raises(RuntimeError, match="sandbox cwd"):
        sandbox.resolve_sandbox_cwd(outside_dir, root=sandbox_root)


def test_sanitize_sandbox_env_rejects_sensitive_keys() -> None:
    suspicious_key = "_".join(("OPENAI", "API", "KEY"))
    with pytest.raises(PermissionError, match="Sensitive env key"):
        sandbox.sanitize_sandbox_env({suspicious_key: "secret"})


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

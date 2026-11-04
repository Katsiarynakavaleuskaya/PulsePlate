"""Deterministic tests for local execution sandbox."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import IO
from typing import cast

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


def test_sanitize_sandbox_env_keeps_network_disable_marker() -> None:
    sanitized = sandbox.sanitize_sandbox_env({sandbox.SANDBOX_DISABLE_NETWORK_ENV.lower(): "true"})

    assert sanitized[sandbox.SANDBOX_DISABLE_NETWORK_ENV] == "1"


def test_sanitize_sandbox_env_rejects_invalid_network_disable_marker() -> None:
    with pytest.raises(PermissionError, match=sandbox.SANDBOX_DISABLE_NETWORK_ENV):
        sandbox.sanitize_sandbox_env({sandbox.SANDBOX_DISABLE_NETWORK_ENV: "0"})


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


def test_build_sandbox_argv_wraps_unshare_when_network_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "_resolve_unshare_binary", lambda: "/usr/bin/unshare")

    argv = sandbox._build_sandbox_argv(
        binary_path="/usr/bin/python3",
        args=("-c", "print('ok')"),
        env={sandbox.SANDBOX_DISABLE_NETWORK_ENV: "1"},
    )

    assert argv == (
        "/usr/bin/unshare",
        "--net",
        "--map-root-user",
        "/usr/bin/python3",
        "-c",
        "print('ok')",
    )


def test_build_sandbox_argv_fails_closed_without_unshare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox.os, "name", "posix", raising=False)
    monkeypatch.setattr(sandbox.shutil, "which", lambda _binary: None)

    with pytest.raises(RuntimeError, match="unshare"):
        sandbox._build_sandbox_argv(
            binary_path="/usr/bin/python3",
            args=("-c", "pass"),
            env={sandbox.SANDBOX_DISABLE_NETWORK_ENV: "1"},
        )


def test_build_sandbox_argv_without_network_marker_keeps_binary() -> None:
    argv = sandbox._build_sandbox_argv(
        binary_path="/usr/bin/python3",
        args=("-c", "pass"),
        env={},
    )

    assert argv == ("/usr/bin/python3", "-c", "pass")


def test_coerce_output_decodes_bytes() -> None:
    assert sandbox._coerce_output(b"hello") == "hello"


def test_coerce_output_preserves_text() -> None:
    assert sandbox._coerce_output("hello") == "hello"


def test_shared_output_budget_recreates_lock_and_stops_after_budget_exhaustion() -> None:
    budget = sandbox._SharedOutputBudget(max_bytes=1)
    budget._lock = None
    assert budget.consume(b"a") == 1
    budget._lock = None
    assert budget.consume(b"b") == 0


def test_drain_stream_ignores_oserror_and_closes_stream() -> None:
    class _BrokenStream:
        def __init__(self) -> None:
            self.closed = False

        def read(self, _size: int) -> bytes:
            raise OSError("stream closed")

        def close(self) -> None:
            self.closed = True

    stream = _BrokenStream()
    collector = sandbox._StreamingOutputBuffer(budget=sandbox._SharedOutputBudget(max_bytes=8))
    sandbox._drain_stream(cast(IO[bytes], stream), collector=collector)
    assert stream.closed is True
    assert not collector.drained_and_closed


def test_terminate_sandbox_process_uses_kill_on_non_posix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DummyProcess:
        def __init__(self) -> None:
            self.pid = 123
            self.killed = False

        def kill(self) -> None:
            self.killed = True

    process = _DummyProcess()
    monkeypatch.setattr(sandbox.os, "name", "nt", raising=False)
    sandbox._terminate_sandbox_process(cast(subprocess.Popen[bytes], process))
    assert process.killed is True


def test_terminate_sandbox_process_ignores_missing_posix_process_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DummyProcess:
        pid = 123

    def _raise_process_lookup(_pid: int, _signal: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(sandbox.os, "name", "posix", raising=False)
    monkeypatch.setattr(sandbox.os, "killpg", _raise_process_lookup)
    sandbox._terminate_sandbox_process(cast(subprocess.Popen[bytes], _DummyProcess()))


def test_join_drain_thread_never_closes_a_live_readers_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Reader:
        def join(self, *, timeout: float) -> None:
            assert timeout == 0

        def is_alive(self) -> bool:
            return True

    monkeypatch.setattr(sandbox.time, "monotonic", lambda: 20.0)
    assert not sandbox._join_drain_thread(cast(sandbox.threading.Thread, Reader()), 19.0)


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


def test_run_local_sandbox_rejects_missing_pipes(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DummyProcess:
        def __init__(self) -> None:
            self.stdout = None
            self.stderr = None

    monkeypatch.setattr(sandbox.subprocess, "Popen", lambda *args, **kwargs: _DummyProcess())
    with pytest.raises(RuntimeError, match="stdout/stderr pipes"):
        sandbox.run_local_sandbox(
            sandbox.SandboxRequest(
                binary="python3",
                args=("-c", "print('x')"),
                cwd=sandbox_root,
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


def test_run_local_sandbox_timeout_kills_descendants_holding_stdio(
    sandbox_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sandbox.SANDBOX_TIMEOUT_ENV, "1")
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3",
            args=(
                "-c",
                (
                    "import subprocess, sys, time;"
                    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']);"
                    "time.sleep(30)"
                ),
            ),
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


def test_run_local_sandbox_stream_limit_applies_across_stdout_and_stderr(
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
                    "import sys;"
                    "sys.stdout.write('abcd');"
                    "sys.stdout.flush();"
                    "sys.stderr.write('efgh');"
                    "sys.stderr.flush();"
                    "sys.stdout.write('ijkl');"
                    "sys.stdout.flush()"
                ),
            ),
            cwd=sandbox_root,
        )
    )
    combined_bytes = len(result.stdout.encode("utf-8")) + len(result.stderr.encode("utf-8"))
    assert result.returncode == 0
    assert result.truncated is True
    assert combined_bytes <= 8


def test_run_local_sandbox_cli_emits_deterministic_json(sandbox_root: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "orchestration" / "run_local_sandbox.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
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
    env.pop("PYTHONPATH", None)
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
    env.pop("PYTHONPATH", None)
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


@pytest.mark.parametrize(
    "case",
    [
        "success",
        "native-124",
        "native-nonzero",
        "timeout-settled",
        "failed-reap",
        "termination-error",
        "join-error",
        "stdout-stalled",
        "stderr-stalled",
        "both-stalled",
        "timeout-drain-stalled",
        "expired",
        "initial-oserror",
        "cancel-wait",
        "cancel-reap",
        "cancel-drain",
        "timeout-already-reaped",
    ],
)
def test_sandbox_result_requires_direct_reap_and_both_drains(
    sandbox_root: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    import traceback

    marker = "synthetic-sandbox-private-input"
    monkeypatch.setenv(sandbox.SANDBOX_TIMEOUT_ENV, "10")
    clock = [0.0]
    events = []
    joins = []
    checked_output = []

    class Pipe:
        def close(self) -> None:
            pytest.fail("controller closed a reader-owned pipe")

    class Child:
        pid = 7654321
        returncode = None
        stdout = Pipe()
        stderr = Pipe()

        def wait(self, *, timeout: float) -> int:
            events.append(("wait", timeout))
            if len(events) == 1:
                assert timeout == 10
                if case == "cancel-wait":
                    raise KeyboardInterrupt
                if case == "initial-oserror":
                    raise OSError(marker)
                if case == "timeout-already-reaped":
                    self.returncode = 9
                    raise subprocess.TimeoutExpired([marker], timeout)
                if case in {
                    "timeout-settled",
                    "failed-reap",
                    "termination-error",
                    "timeout-drain-stalled",
                    "cancel-reap",
                }:
                    raise subprocess.TimeoutExpired([marker], timeout, output=marker, stderr=marker)
                self.returncode = {"native-124": 124, "native-nonzero": 7}.get(case, 0)
            else:
                if case == "timeout-already-reaped":
                    assert timeout == 10 and self.returncode == 9
                    return self.returncode
                assert events[-2][0] == "kill" and timeout == 8
                if case == "cancel-reap":
                    raise SystemExit(77)
                clock[0] += 3
                if case == "failed-reap":
                    raise subprocess.TimeoutExpired([marker], timeout, output=marker, stderr=marker)
                self.returncode = -9
            return self.returncode

    class Reader:
        def __init__(self, *, target: object, args: tuple, kwargs: dict, daemon: bool) -> None:
            self.collector = kwargs["collector"]
            self.name = "stdout" if args[0] is child.stdout else "stderr"

        def start(self) -> None:
            self.collector.drained_and_closed = True

        def join(self, *, timeout: float) -> None:
            joins.append((self.name, timeout))
            if case == "cancel-drain":
                raise KeyboardInterrupt
            clock[0] += timeout if case == "expired" else 1
            if case == "join-error" and self.name == "stdout":
                raise RuntimeError(marker)

        def is_alive(self) -> bool:
            return (
                case == "both-stalled"
                or case == self.name + "-stalled"
                or case == "timeout-drain-stalled"
                and self.name == "stderr"
                or case == "expired"
                and self.name == "stderr"
            )

    child = Child()
    monkeypatch.setattr(sandbox.subprocess, "Popen", lambda *a, **kw: child)
    monkeypatch.setattr(sandbox.threading, "Thread", Reader)
    monkeypatch.setattr(sandbox.time, "monotonic", lambda: clock[0])

    def terminate(process: object) -> None:
        assert process is child and child.returncode is None
        events.append(("kill", 0))
        clock[0] += 2
        if case == "termination-error":
            raise PermissionError(marker)

    monkeypatch.setattr(sandbox, "_terminate_sandbox_process", terminate)
    collector = sandbox._StreamingOutputBuffer

    def project(_self: object) -> str:
        checked_output.append(True)
        return "complete"

    monkeypatch.setattr(collector, "to_text", project)

    def execute() -> sandbox.SandboxResult:
        return sandbox.run_local_sandbox(
            sandbox.SandboxRequest(binary="python3", args=("-c", marker), cwd=sandbox_root)
        )

    if case.startswith("cancel-"):
        with pytest.raises(SystemExit if case == "cancel-reap" else KeyboardInterrupt):
            execute()
        assert not checked_output
        if case != "cancel-reap":
            assert all(kind != "kill" for kind, _ in events)
        return
    if case in {"success", "native-124", "native-nonzero", "timeout-settled"}:
        result = execute()
        assert result.returncode == {
            "native-124": 124,
            "native-nonzero": 7,
            "timeout-settled": 124,
        }.get(case, 0)
        assert result.timed_out is (case == "timeout-settled")
        assert len(checked_output) == 2
    else:
        with pytest.raises(subprocess.TimeoutExpired) as captured:
            execute()
        error = captured.value
        assert error.cmd == "sandbox cleanup" and error.timeout == 10
        assert (
            error.stdout is None
            and error.stderr is None
            and error.__cause__ is None
            and error.__context__ is None
        )
        assert marker not in repr(error.args) + "".join(traceback.format_exception(error))
        assert not checked_output
    initial_timeout = case in {
        "timeout-settled",
        "failed-reap",
        "timeout-drain-stalled",
        "termination-error",
    }
    expected_calls = ["wait", "kill", "wait"] if initial_timeout else ["wait"]
    if case == "timeout-already-reaped":
        expected_calls = ["wait", "wait"]
    assert [x[0] for x in events] == expected_calls
    first = 5 if initial_timeout else 10
    assert joins == [("stdout", first), ("stderr", 0 if case == "expired" else first - 1)]


@pytest.mark.parametrize("side", ["stdout", "stderr"])
@pytest.mark.parametrize("fault", ["read", "close"])
def test_sandbox_does_not_publish_partial_output_after_reader_io_failure(
    sandbox_root: Path, monkeypatch: pytest.MonkeyPatch, side: str, fault: str
) -> None:
    import io

    marker = b"private partial sandbox output"

    class BrokenPipe(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            if fault == "read" and self.tell() > 0:
                raise OSError(marker)
            return super().read(size)

        def close(self) -> None:
            super().close()
            if fault == "close":
                raise OSError(marker)

    broken = BrokenPipe(marker)
    healthy = io.BytesIO(b"other stream")

    class Child:
        stdout = broken if side == "stdout" else healthy
        stderr = broken if side == "stderr" else healthy

        def wait(self, *, timeout: float) -> int:
            return 0

    monkeypatch.setattr(sandbox.subprocess, "Popen", lambda *args, **kwargs: Child())
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        sandbox.run_local_sandbox(sandbox.SandboxRequest(binary="python3", cwd=sandbox_root))
    assert caught.value.cmd == "sandbox cleanup"
    assert caught.value.output is None and caught.value.stderr is None
    assert broken.closed and healthy.closed
    assert marker.decode() not in repr(caught.value.args)


def test_relative_path_binary_is_bound_before_sandbox_cwd(
    sandbox_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_bin = sandbox_root / "bin"
    parent_bin.mkdir()
    selected = parent_bin / "python3"
    selected.symlink_to(sys.executable)
    child = sandbox_root / "child"
    (child / "bin").mkdir(parents=True)
    competing = child / "bin" / "python3"
    competing.write_text("This is not the selected executable.")
    competing.chmod(0o755)
    monkeypatch.chdir(sandbox_root)
    monkeypatch.setenv("PATH", "bin")
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python3", args=("-I", "-S", "-c", "print('selected-parent')"), cwd=child
        )
    )
    assert result.returncode == 0
    assert result.stdout == "selected-parent\n"
    assert result.argv[0] == str(selected)
    assert selected.is_symlink()


def test_sandbox_resolver_preserves_real_virtualenv_invocation(
    sandbox_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import venv

    root = sandbox_root / "venv"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(root)
    executable = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    monkeypatch.setenv(sandbox.SANDBOX_ALLOWED_BINARIES_ENV, "python")
    monkeypatch.setenv("PATH", str(executable.parent))
    result = sandbox.run_local_sandbox(
        sandbox.SandboxRequest(
            binary="python",
            args=("-I", "-c", "import sys; print(sys.prefix); print(sys.executable)"),
            cwd=sandbox_root,
        )
    )
    assert result.returncode == 0
    assert result.stdout.splitlines() == [str(root), str(executable)]
    assert result.argv[0] == str(executable)


@pytest.mark.parametrize("kind", ["directory", "nonexecutable", "missing", "broken-symlink"])
def test_sandbox_invalid_resolved_executable_rejects_before_spawn(
    sandbox_root: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    selected = sandbox_root / "selected-python"
    if kind == "directory":
        selected.mkdir()
    elif kind == "nonexecutable":
        selected.write_text("not executable")
        selected.chmod(0o600)
    elif kind == "broken-symlink":
        selected.symlink_to(sandbox_root / "missing-target")
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: str(selected))
    monkeypatch.setattr(
        sandbox.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("invalid binary spawned")
    )
    with pytest.raises(RuntimeError, match="executable regular file"):
        sandbox.run_local_sandbox(sandbox.SandboxRequest(binary="python3", cwd=sandbox_root))

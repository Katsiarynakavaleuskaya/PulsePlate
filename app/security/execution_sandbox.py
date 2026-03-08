"""Local execution sandbox primitives.

RU: Минимальный локальный sandbox для безопасного запуска allowlisted
команд с ограничением cwd, timeout и объёма вывода.
EN: Minimal local sandbox for allowlisted command execution with cwd,
timeout, and output limits.
"""

from __future__ import annotations

import os
import signal
import shutil
import subprocess  # nosec B404: subprocess is required for bounded local sandbox execution (remove-by: 2026-07-31, ref: PR-1010)
import threading
from typing import IO
from typing import Final
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from app.security.agent_control_plane import EXECUTION_MODE_AUTO_SAFE
from app.security.agent_control_plane import EXECUTION_MODE_BLOCKED
from app.security.agent_control_plane import EXECUTION_MODE_REVIEW_REQUIRED
from app.security.agent_control_plane import normalize_execution_mode
from app.security.agent_control_plane import require_execution_mode
from app.security.agent_control_plane import require_policy_allow

SANDBOX_ENABLED_ENV = "AGENT_EXECUTION_SANDBOX_ENABLED"
SANDBOX_ROOT_ENV = "AGENT_EXECUTION_SANDBOX_ROOT"
SANDBOX_TIMEOUT_ENV = "AGENT_EXECUTION_SANDBOX_TIMEOUT_SECONDS"
SANDBOX_MAX_OUTPUT_ENV = "AGENT_EXECUTION_SANDBOX_MAX_OUTPUT_BYTES"
SANDBOX_ALLOWED_BINARIES_ENV = "AGENT_EXECUTION_SANDBOX_ALLOWED_BINARIES"

DEFAULT_SANDBOX_TIMEOUT_SECONDS = 30
DEFAULT_SANDBOX_MAX_OUTPUT_BYTES = 32_768
DEFAULT_ALLOWED_BINARIES = (
    "flake8",
    "git",
    "mypy",
    "pytest",
    "ruff",
)
_STREAM_READ_CHUNK_BYTES = 4_096
_DEFAULT_ENV_KEYS = (
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "TMPDIR",
    "TZ",
)
_SENSITIVE_ENV_TOKENS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "SALT")
_BLOCKED_ENV_KEYS = (
    "DYLD_FRAMEWORK_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
)
_ALLOWED_EXTRA_ENV_KEYS = (
    "CI",
    "FORCE_COLOR",
    "NO_COLOR",
)
_ALLOWED_EXTRA_ENV_PREFIXES = (
    "AGENT_",
    "PP_",
    "PULSEPLATE_",
    "PYTEST_",
)
_EXECUTION_MODE_PRIORITY = {
    EXECUTION_MODE_AUTO_SAFE: 0,
    EXECUTION_MODE_REVIEW_REQUIRED: 1,
    EXECUTION_MODE_BLOCKED: 2,
}
_WINDOWS_PROCESS_GROUP_FLAG = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
_STREAM_JOIN_GRACE_SECONDS: Final[float] = 0.1


@dataclass(frozen=True)
class SandboxRequest:
    """Sandbox execution request.

    RU: Описывает allowlisted локальную команду и её ограничения.
    EN: Describes allowlisted local command and execution bounds.
    """

    binary: str
    args: tuple[str, ...] = ()
    cwd: str | Path | None = None
    env: Mapping[str, str] | None = None
    mode: str | None = None
    action: str = "sandbox.exec"
    target: str = "local://sandbox"


@dataclass(frozen=True)
class SandboxResult:
    """Sandbox execution result."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    truncated: bool
    cwd: str


def sandbox_enabled() -> bool:
    """Return whether local sandbox execution is enabled."""

    raw = (os.getenv(SANDBOX_ENABLED_ENV) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def require_sandbox_enabled() -> None:
    """Fail closed when sandbox execution is disabled."""

    if not sandbox_enabled():
        raise RuntimeError(f"{SANDBOX_ENABLED_ENV} must be enabled for local sandbox execution.")


def _parse_positive_int(raw: str, *, env_name: str, default: int) -> int:
    normalized = raw.strip()
    if normalized == "":
        return default
    try:
        value = int(normalized)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} must be an integer >= 1.") from exc
    if value < 1:
        raise RuntimeError(f"{env_name} must be an integer >= 1.")
    return value


def require_sandbox_timeout_seconds() -> int:
    """Return validated sandbox timeout."""

    return _parse_positive_int(
        os.getenv(SANDBOX_TIMEOUT_ENV) or "",
        env_name=SANDBOX_TIMEOUT_ENV,
        default=DEFAULT_SANDBOX_TIMEOUT_SECONDS,
    )


def require_sandbox_max_output_bytes() -> int:
    """Return validated output limit."""

    return _parse_positive_int(
        os.getenv(SANDBOX_MAX_OUTPUT_ENV) or "",
        env_name=SANDBOX_MAX_OUTPUT_ENV,
        default=DEFAULT_SANDBOX_MAX_OUTPUT_BYTES,
    )


def parse_allowed_binaries(raw: str) -> tuple[str, ...]:
    """Parse sandbox binary allowlist from env string."""

    tokens: list[str] = []
    seen: set[str] = set()
    compact = raw.replace("\n", ",")
    for entry in compact.split(","):
        candidate = entry.strip()
        if not candidate:
            continue
        if "/" in candidate or "\\" in candidate:
            raise RuntimeError(
                f"{SANDBOX_ALLOWED_BINARIES_ENV} entries must be bare binary names, got {candidate!r}."
            )
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tokens.append(candidate)
    return tuple(tokens)


def load_allowed_binaries() -> tuple[str, ...]:
    """Return configured sandbox binary allowlist."""

    raw = (os.getenv(SANDBOX_ALLOWED_BINARIES_ENV) or "").strip()
    if raw == "":
        return DEFAULT_ALLOWED_BINARIES
    parsed = parse_allowed_binaries(raw)
    if not parsed:
        raise RuntimeError(f"{SANDBOX_ALLOWED_BINARIES_ENV} must contain at least one binary.")
    return parsed


def resolve_sandbox_root() -> Path:
    """Resolve sandbox root path from env.

    RU: При включённом sandbox root должен быть задан явно.
    EN: Sandbox root must be configured explicitly once the feature is enabled.
    """

    configured = (os.getenv(SANDBOX_ROOT_ENV) or "").strip()
    if configured == "":
        raise RuntimeError(f"{SANDBOX_ROOT_ENV} must be set for local sandbox execution.")
    root = Path(configured).expanduser().resolve()
    if not root.exists():
        raise RuntimeError(f"{SANDBOX_ROOT_ENV} points to a missing path: {root}")
    if not root.is_dir():
        raise RuntimeError(f"{SANDBOX_ROOT_ENV} must point to a directory: {root}")
    return root


def _ensure_relative_to(path: Path, root: Path, *, label: str) -> Path:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"{label} must stay within sandbox root: {root}") from exc
    return path


def resolve_sandbox_cwd(cwd: str | Path | None, *, root: Path | None = None) -> Path:
    """Resolve and validate requested sandbox cwd."""

    sandbox_root = root or resolve_sandbox_root()
    if cwd is None:
        return sandbox_root
    candidate = Path(cwd)
    if not candidate.is_absolute():
        candidate = sandbox_root / candidate
    resolved = candidate.expanduser().resolve()
    _ensure_relative_to(resolved, sandbox_root, label="sandbox cwd")
    if not resolved.exists():
        raise RuntimeError(f"Sandbox cwd does not exist: {resolved}")
    if not resolved.is_dir():
        raise RuntimeError(f"Sandbox cwd must be a directory: {resolved}")
    return resolved


def resolve_allowed_binary(binary: str, *, allowed_binaries: tuple[str, ...] | None = None) -> str:
    """Resolve an allowlisted binary to an absolute path."""

    configured = allowed_binaries or load_allowed_binaries()
    if binary not in configured:
        raise PermissionError(f"Binary {binary!r} is not allowlisted for sandbox execution.")
    resolved = shutil.which(binary)
    if not resolved:
        raise RuntimeError(f"Allowlisted sandbox binary not found on PATH: {binary}")
    return resolved


def sanitize_sandbox_env(extra_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return sanitized environment for sandbox subprocess."""

    sanitized: dict[str, str] = {}
    for key in _DEFAULT_ENV_KEYS:
        value = os.getenv(key)
        if value is not None:
            sanitized[key] = value

    if not extra_env:
        return sanitized

    for key, value in extra_env.items():
        upper = key.upper()
        if upper in _BLOCKED_ENV_KEYS:
            raise PermissionError(f"Loader env key is not allowed in sandbox: {key}")
        if any(token in upper for token in _SENSITIVE_ENV_TOKENS):
            raise PermissionError(f"Sensitive env key is not allowed in sandbox: {key}")
        if upper not in _ALLOWED_EXTRA_ENV_KEYS and not any(
            upper.startswith(prefix) for prefix in _ALLOWED_EXTRA_ENV_PREFIXES
        ):
            raise PermissionError(f"Extra env key is not allowlisted for sandbox: {key}")
        sanitized[key] = value
    return sanitized


def resolve_effective_execution_mode(requested_mode: str | None = None) -> str:
    """Return the strictest execution mode between config and request.

    RU: Request mode может только ужесточать runtime policy, но не ослаблять её.
    EN: Request mode may tighten runtime policy, but must never relax it.
    """

    configured_mode: str = normalize_execution_mode()
    if requested_mode is None:
        return configured_mode

    requested_normalized: str = normalize_execution_mode(requested_mode)
    if _EXECUTION_MODE_PRIORITY[requested_normalized] > _EXECUTION_MODE_PRIORITY[configured_mode]:
        return requested_normalized
    return configured_mode


def _coerce_output(value: bytes | str | None) -> str:
    """Normalize subprocess output to text."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


@dataclass
class _SharedOutputBudget:
    """Thread-safe total output budget shared across stdout and stderr."""

    max_bytes: int
    _consumed: int = 0
    _lock: threading.Lock | None = None

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def consume(self, chunk: bytes) -> int:
        if self._lock is None:
            self._lock = threading.Lock()
        with self._lock:
            remaining = self.max_bytes - self._consumed
            if remaining <= 0:
                return 0
            accepted = min(len(chunk), remaining)
            self._consumed += accepted
            return accepted


@dataclass
class _StreamingOutputBuffer:
    """Bounded streaming output collector."""

    budget: _SharedOutputBudget
    _buffer: bytearray
    truncated: bool = False

    def __init__(self, *, budget: _SharedOutputBudget) -> None:
        self.budget = budget
        self._buffer = bytearray()
        self.truncated = False

    def append(self, chunk: bytes) -> None:
        accepted = self.budget.consume(chunk)
        if accepted > 0:
            self._buffer.extend(chunk[:accepted])
        if accepted < len(chunk):
            self.truncated = True

    def to_text(self) -> str:
        return self._buffer.decode("utf-8", errors="ignore")


def _drain_stream(
    stream: IO[bytes],
    *,
    collector: _StreamingOutputBuffer,
) -> None:
    """Read a subprocess stream into a bounded collector."""

    try:
        while True:
            chunk = stream.read(_STREAM_READ_CHUNK_BYTES)
            if not chunk:
                break
            collector.append(chunk)
    except OSError:
        # The controller may close a pipe during timeout cleanup.
        return
    finally:
        stream.close()


def _terminate_sandbox_process(process: subprocess.Popen[bytes]) -> None:
    """Terminate sandbox process without leaving stdio-holding descendants alive."""

    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL)
        return
    process.kill()


def _join_drain_thread(
    thread: threading.Thread,
    *,
    stream: IO[bytes],
    timeout_seconds: int,
) -> None:
    """Bound drain-thread joins so timeout cleanup cannot block indefinitely."""

    thread.join(timeout=timeout_seconds)
    if not thread.is_alive():
        return
    stream.close()
    thread.join(timeout=_STREAM_JOIN_GRACE_SECONDS)


def run_local_sandbox(
    request: SandboxRequest,
    *,
    allowlist: set[tuple[str, str]] | None = None,
) -> SandboxResult:
    """Execute an allowlisted command inside the local sandbox."""

    require_sandbox_enabled()
    require_execution_mode(resolve_effective_execution_mode(request.mode))
    require_policy_allow(request.action, request.target, allowlist=allowlist)

    sandbox_root = resolve_sandbox_root()
    sandbox_cwd = resolve_sandbox_cwd(request.cwd, root=sandbox_root)
    binary_path = resolve_allowed_binary(request.binary)
    timeout_seconds = require_sandbox_timeout_seconds()
    max_output_bytes = require_sandbox_max_output_bytes()
    env = sanitize_sandbox_env(request.env)
    argv = (binary_path, *request.args)
    output_budget = _SharedOutputBudget(max_bytes=max_output_bytes)
    stdout_collector = _StreamingOutputBuffer(budget=output_budget)
    stderr_collector = _StreamingOutputBuffer(budget=output_budget)

    process = subprocess.Popen(  # nosec B603: absolute allowlisted binary; argv bounded by sandbox API (remove-by: 2026-07-31, ref: PR-1010)
        argv,
        cwd=str(sandbox_cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=(os.name == "posix"),
        creationflags=_WINDOWS_PROCESS_GROUP_FLAG if os.name == "nt" else 0,
    )
    if process.stdout is None or process.stderr is None:
        raise RuntimeError("Sandbox subprocess must expose stdout/stderr pipes.")
    stdout_thread = threading.Thread(
        target=_drain_stream,
        args=(process.stdout,),
        kwargs={"collector": stdout_collector},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_stream,
        args=(process.stderr,),
        kwargs={"collector": stderr_collector},
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_sandbox_process(process)
        process.wait()
        returncode = 124

    _join_drain_thread(stdout_thread, stream=process.stdout, timeout_seconds=timeout_seconds)
    _join_drain_thread(stderr_thread, stream=process.stderr, timeout_seconds=timeout_seconds)
    return SandboxResult(
        argv=argv,
        returncode=returncode,
        stdout=stdout_collector.to_text(),
        stderr=stderr_collector.to_text(),
        timed_out=timed_out,
        truncated=stdout_collector.truncated or stderr_collector.truncated,
        cwd=str(sandbox_cwd),
    )

"""Local execution sandbox primitives.

RU: Минимальный локальный sandbox для безопасного запуска allowlisted
команд с ограничением cwd, timeout и объёма вывода.
EN: Minimal local sandbox for allowlisted command execution with cwd,
timeout, and output limits.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404: subprocess is required for bounded local sandbox execution (remove-by: 2026-07-31, ref: PR-1010)
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
    "coverage",
    "diff-cover",
    "flake8",
    "git",
    "mypy",
    "pytest",
    "ruff",
)
_DEFAULT_ENV_KEYS = (
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "PYTHONPATH",
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
    """Resolve sandbox root path from env or current working directory."""

    configured = (os.getenv(SANDBOX_ROOT_ENV) or "").strip()
    root = Path(configured or os.getcwd()).expanduser().resolve()
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

    configured_mode = normalize_execution_mode()
    if requested_mode is None:
        return configured_mode

    requested_normalized = normalize_execution_mode(requested_mode)
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


def _truncate_output(value: bytes | str | None, *, max_bytes: int) -> tuple[str, bool]:
    """Truncate text to deterministic byte budget."""

    normalized = _coerce_output(value)
    encoded = normalized.encode("utf-8")
    if len(encoded) <= max_bytes:
        return normalized, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated, True


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

    try:
        completed = subprocess.run(  # nosec B603: absolute allowlisted binary; argv bounded by sandbox API (remove-by: 2026-07-31, ref: PR-1010)
            argv,
            cwd=str(sandbox_cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout, stdout_truncated = _truncate_output(completed.stdout, max_bytes=max_output_bytes)
        stderr, stderr_truncated = _truncate_output(completed.stderr, max_bytes=max_output_bytes)
        return SandboxResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
            truncated=stdout_truncated or stderr_truncated,
            cwd=str(sandbox_cwd),
        )
    except subprocess.TimeoutExpired as exc:
        stdout, stdout_truncated = _truncate_output(
            exc.stdout,
            max_bytes=max_output_bytes,
        )
        stderr, stderr_truncated = _truncate_output(
            exc.stderr,
            max_bytes=max_output_bytes,
        )
        return SandboxResult(
            argv=argv,
            returncode=124,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            truncated=stdout_truncated or stderr_truncated,
            cwd=str(sandbox_cwd),
        )

"""Fixed Codex CLI executor for PR-2 sandboxed patch generation."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess  # nosec B404: fixed codex subprocess wrapper only (remove-by: 2026-10-31, ref: PR-2)

SAFE_ENV_KEYS = frozenset(
    {
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "PATH",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_FILE",
        "TERM",
        "TMPDIR",
        "USER",
    }
)
SECRET_ENV_SUBSTRINGS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASS",
    "SALT",
    "COOKIE",
    "CREDENTIAL",
    "DATABASE_URL",
    "DSN",
)


class CreativeCodePatchExecutorError(ValueError):
    """Raised when the fixed Codex CLI executor cannot complete safely."""


def resolve_codex_binary() -> str:
    """Resolve the local Codex CLI executable."""

    codex = shutil.which("codex")
    if not codex:
        raise CreativeCodePatchExecutorError("codex CLI is required for PR-2 generation.")
    resolved = Path(codex).expanduser().resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise CreativeCodePatchExecutorError("codex CLI must resolve to an executable file.")
    return str(resolved)


def _absolute_path_env(raw_path: str | None) -> str:
    if not raw_path:
        return ""
    entries: list[str] = []
    for entry in raw_path.split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry).expanduser()
        if not candidate.is_absolute():
            candidate = candidate.resolve()
        entries.append(str(candidate))
    return os.pathsep.join(entries)


def sanitized_codex_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Return a tiny env allowlist with secret-shaped values removed."""

    source = os.environ if env is None else env
    sanitized: dict[str, str] = {}
    for key, value in source.items():
        upper_key = key.upper()
        if key not in SAFE_ENV_KEYS:
            continue
        if upper_key.startswith("GIT_") or upper_key in {"PYTHONPATH", "CODEX_HOME"}:
            continue
        if any(fragment in upper_key for fragment in SECRET_ENV_SUBSTRINGS):
            continue
        sanitized[key] = value
    sanitized["PATH"] = _absolute_path_env(source.get("PATH"))
    return sanitized


def build_codex_exec_argv(*, checkout: Path, codex_binary: str | None = None) -> list[str]:
    """Build the only PR-2 allowed Codex execution argv."""

    binary = codex_binary or resolve_codex_binary()
    return [
        binary,
        "exec",
        "--ignore-user-config",
        "-c",
        'approval_policy="never"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'web_search="disabled"',
        "-c",
        "apps._default.enabled=false",
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "--json",
        "--cd",
        str(checkout),
        "-",
    ]


def run_codex_exec(
    *,
    checkout: Path,
    prompt: str,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
) -> dict[str, int]:
    """Run Codex with stdin prompt and return bounded metadata only."""

    if not prompt.strip():
        raise CreativeCodePatchExecutorError("Codex prompt must be non-empty.")
    argv = build_codex_exec_argv(checkout=checkout)
    try:
        process = subprocess.run(  # nosec B603: fixed absolute codex argv, no shell, stdin prompt only (remove-by: 2026-10-31, ref: PR-2)
            argv,
            cwd=str(checkout),
            env=sanitized_codex_env(env),
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise CreativeCodePatchExecutorError("codex exec timed out.") from exc
    stdout_lines = len(process.stdout.splitlines()) if process.stdout else 0
    stderr_lines = len(process.stderr.splitlines()) if process.stderr else 0
    if process.returncode != 0:
        raise CreativeCodePatchExecutorError(
            "codex exec failed with return code "
            f"{process.returncode}; stdout_lines={stdout_lines}; stderr_lines={stderr_lines}"
        )
    return {
        "returncode": process.returncode,
        "stdout_lines": stdout_lines,
        "stderr_lines": stderr_lines,
    }

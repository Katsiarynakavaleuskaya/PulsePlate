#!/usr/bin/env python3
"""Fail-fast local environment parity check for `make verify`.

This script validates only the repo interpreter + module parity required for
the canonical local verification gate. It does not repair or rewrite the
environment and points developers to the documented recovery path.

Console-script wrappers under ``.venv/bin`` are checked only when present:
they must be executable and, if the shebang uses an absolute interpreter
path, that path must exist. Shebangs of the form ``#!/usr/bin/env ...`` are
not validated (v1) to avoid false positives from ambient PATH.
"""

from __future__ import annotations

import importlib
import os
import subprocess  # nosec B404: subprocess is required for bounded local guard execution (remove-by: 2026-07-31, ref: PR-1243)
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENV_DIR = REPO_ROOT / ".venv"
VENV_BIN_DIR = VENV_DIR / "bin"
VENV_PYTHON = VENV_BIN_DIR / "python"
STARTUP_HOOK_GUARD = REPO_ROOT / "scripts" / "ci" / "check_python_startup_hooks.py"
REQUIRED_MODULES: tuple[tuple[str, str], ...] = (
    ("flake8", "lint"),
    ("mypy", "typecheck"),
    ("pytest", "test-fast"),
    ("coverage", "cov-check"),
    ("diff_cover.diff_cover_tool", "diff-cov"),
)

# Pip console-script names aligned with REQUIRED_MODULES / make verify stages.
# Missing scripts are OK (``$(VENV_PYTHON) -m ...`` is canonical); present
# scripts must not point at deleted interpreters or be non-executable.
VERIFY_CRITICAL_CONSOLE_SCRIPT_NAMES: tuple[str, ...] = (
    "flake8",
    "pytest",
    "mypy",
    "coverage",
    "diff-cover",
)


@dataclass(frozen=True)
class StartupHookFinding:
    """A parsed startup-hook finding from the external guard."""

    path: Path
    line_number: int
    line: str


def _import_module(module_name: str) -> str | None:
    """Return error text when a module import fails, else None."""
    try:
        importlib.import_module(module_name)
        return None
    except Exception as exc:  # pragma: no cover - exercised through public helpers
        return str(exc)


def collect_unexpected_startup_hooks() -> list[StartupHookFinding]:
    """Return unexpected executable .pth hooks for the current repo interpreter."""
    if not STARTUP_HOOK_GUARD.exists():
        raise RuntimeError(f"Unable to load startup hook guard: {STARTUP_HOOK_GUARD}")

    result = subprocess.run(  # nosec B603: argv uses fixed repo-local Python and guard paths only (remove-by: 2026-07-31, ref: PR-1243)
        [
            str(VENV_PYTHON),
            "-S",
            str(STARTUP_HOOK_GUARD),
            "--python-executable",
            str(VENV_PYTHON),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return []
    if result.returncode != 1:
        diagnostic = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
        raise RuntimeError(f"Unable to load startup hook guard: {diagnostic}")

    findings: list[StartupHookFinding] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line.startswith("- "):
            continue
        location, separator, line = raw_line[2:].partition(" :: ")
        path_text, _, line_number_text = location.rpartition(":")
        if not separator or not path_text or not line_number_text.isdigit():
            continue
        findings.append(
            StartupHookFinding(
                path=Path(path_text),
                line_number=int(line_number_text),
                line=line,
            )
        )
    if findings:
        return findings
    raise RuntimeError("Unable to parse startup hook guard output.")


def _parse_absolute_shebang_interpreter(first_line: str) -> Path | None:
    """
    Return interpreter path from shebang when the first token is an absolute path.

    If the shebang has extra arguments after that token (for example ``#!/usr/bin/python -O``),
    only the first token is used; ``#!/usr/bin/env ...`` yields None (handled elsewhere).
    """
    stripped = first_line.strip()
    if not stripped.startswith("#!"):
        return None
    remainder = stripped[2:].strip()
    if not remainder:
        return None
    candidate = remainder.split()[0]
    if not candidate.startswith("/"):
        return None
    return Path(candidate)


def collect_broken_console_wrappers(
    *,
    venv_bin_dir: Path | None = None,
    script_names: tuple[str, ...] | None = None,
) -> list[tuple[str, str]]:
    """Return (script_name, reason) for present-but-broken venv console scripts."""
    bin_dir = venv_bin_dir if venv_bin_dir is not None else VENV_BIN_DIR
    names = script_names if script_names is not None else VERIFY_CRITICAL_CONSOLE_SCRIPT_NAMES
    broken: list[tuple[str, str]] = []
    for name in names:
        script_path = bin_dir / name
        if not script_path.exists() and not script_path.is_symlink():
            continue
        if script_path.is_symlink() and not script_path.exists():
            broken.append((name, "broken or dangling symlink target"))
            continue
        try:
            if not script_path.is_file():
                broken.append((name, "not a regular file"))
                continue
        except OSError as exc:
            broken.append((name, f"cannot stat path: {exc}"))
            continue
        if not os.access(script_path, os.X_OK):
            broken.append((name, "not executable"))
            continue
        try:
            raw = script_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            broken.append((name, f"cannot read script: {exc}"))
            continue
        lines = raw.splitlines()
        if not lines:
            broken.append((name, "empty script"))
            continue
        first_line = lines[0]
        interpreter = _parse_absolute_shebang_interpreter(first_line)
        if interpreter is None:
            continue
        try:
            interp_resolved = interpreter.resolve()
        except (OSError, RuntimeError) as exc:
            broken.append(
                (name, f"stale shebang interpreter (resolve error): {interpreter} ({exc})")
            )
            continue
        if not interp_resolved.is_file():
            broken.append((name, f"stale shebang interpreter missing: {interpreter}"))
            continue
        if not os.access(interp_resolved, os.X_OK):
            broken.append((name, f"stale shebang interpreter not executable: {interpreter}"))
            continue
    return broken


def collect_missing_modules(
    required_modules: tuple[tuple[str, str], ...] = REQUIRED_MODULES,
) -> list[tuple[str, str, str]]:
    """Return missing module records as (module_name, verify_stage, error)."""
    missing: list[tuple[str, str, str]] = []
    for module_name, verify_stage in required_modules:
        error = _import_module(module_name)
        if error is not None:
            missing.append((module_name, verify_stage, error))
    return missing


def build_failure_output(
    *,
    python_executable: Path,
    broken_console_wrappers: list[tuple[str, str]],
    missing_modules: list[tuple[str, str, str]],
    unexpected_startup_hooks: list[StartupHookFinding],
) -> list[str]:
    """Build deterministic failure lines for terminal output."""
    lines = [
        "ERROR: local verify environment is incomplete.",
        f"Expected venv interpreter: {python_executable}",
    ]
    if broken_console_wrappers:
        lines.append("Stale or broken venv console scripts (.venv/bin):")
    for script_name, reason in broken_console_wrappers:
        lines.append(f"- {script_name} :: {reason}")
    if missing_modules:
        lines.append("Missing verify-critical Python modules:")
    for module_name, verify_stage, error in missing_modules:
        lines.append(f"- {module_name} [{verify_stage}] :: {error}")
    if unexpected_startup_hooks:
        lines.append("Unexpected executable startup hooks (.pth):")
        lines.extend(
            f"- {finding.path}:{finding.line_number} :: {finding.line}"
            for finding in unexpected_startup_hooks
        )
    lines.extend(
        (
            "Recovery:",
            "- Export PULSEPLATE_PYTHON_INDEX_URL to the approved private package proxy before bootstrap",
            "- First bootstrap: make venv",
            "- Refresh an existing clean-clone venv: make venv-sync",
        )
    )
    return lines


def main() -> int:
    """Validate that `.venv` can satisfy the local `make verify` dependency floor."""
    if not VENV_PYTHON.exists():
        print("ERROR: .venv is missing. Run `make venv` before `make verify`.")
        return 1

    current_prefix = Path(sys.prefix).resolve()
    if current_prefix != VENV_DIR.resolve():
        print("ERROR: verify-env must run inside the repo .venv interpreter.")
        print(f"Expected venv interpreter: {VENV_PYTHON}")
        print(f"Current interpreter: {Path(sys.executable).resolve()}")
        print(f"Current prefix: {current_prefix}")
        print("Recovery:")
        print("- Export PULSEPLATE_PYTHON_INDEX_URL to the approved private package proxy")
        print("- Run `make verify` or `make verify-env` from repo root")
        print("- If the venv is missing, run `make venv`")
        print("- If the venv drifted, run `make venv-sync`")
        return 1

    broken_wrappers = collect_broken_console_wrappers()
    missing_modules = collect_missing_modules()
    unexpected_startup_hooks = collect_unexpected_startup_hooks()
    if broken_wrappers or missing_modules or unexpected_startup_hooks:
        for line in build_failure_output(
            python_executable=Path(sys.executable).resolve(),
            broken_console_wrappers=broken_wrappers,
            missing_modules=missing_modules,
            unexpected_startup_hooks=unexpected_startup_hooks,
        ):
            print(line)
        return 1

    print("verify-env: local verify environment passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

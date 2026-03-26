#!/usr/bin/env python3
"""Fail-fast local environment parity check for `make verify`.

This script validates only the repo interpreter + module parity required for
the canonical local verification gate. It does not repair or rewrite the
environment and points developers to the documented recovery path.
"""

from __future__ import annotations

import importlib
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
    missing_modules: list[tuple[str, str, str]],
    unexpected_startup_hooks: list[StartupHookFinding],
) -> list[str]:
    """Build deterministic failure lines for terminal output."""
    lines = [
        "ERROR: local verify environment is incomplete.",
        f"Expected venv interpreter: {python_executable}",
    ]
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
        print("- Run `make verify` or `make verify-env` from repo root")
        print("- If the venv is missing, run `make venv`")
        print("- If the venv drifted, run `make venv-sync`")
        return 1

    missing_modules = collect_missing_modules()
    unexpected_startup_hooks = collect_unexpected_startup_hooks()
    if missing_modules or unexpected_startup_hooks:
        for line in build_failure_output(
            python_executable=Path(sys.executable).resolve(),
            missing_modules=missing_modules,
            unexpected_startup_hooks=unexpected_startup_hooks,
        ):
            print(line)
        return 1

    print("verify-env: local verify environment passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

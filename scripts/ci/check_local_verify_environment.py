#!/usr/bin/env python3
"""Fail-fast local environment parity check for `make verify`.

This script validates only the repo interpreter + module parity required for
the canonical local verification gate. It does not repair or rewrite the
environment and points developers to the documented recovery path.
"""

from __future__ import annotations

import importlib
import importlib.util
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

    spec = importlib.util.spec_from_file_location(
        "pulseplate_verify_startup_hook_guard",
        STARTUP_HOOK_GUARD,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load startup hook guard: {STARTUP_HOOK_GUARD}")

    guard_module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(spec.name)
    sys.modules[spec.name] = guard_module
    try:
        spec.loader.exec_module(guard_module)
    finally:
        if previous_module is None:
            sys.modules.pop(spec.name, None)
        else:
            sys.modules[spec.name] = previous_module

    site_packages = guard_module.site_packages_for_interpreter(str(VENV_PYTHON))
    findings_from_guard = guard_module.collect_unexpected_executable_pth_files(site_packages)
    if not findings_from_guard:
        return []

    findings: list[StartupHookFinding] = []
    for finding in findings_from_guard:
        findings.append(
            StartupHookFinding(
                path=Path(finding.path),
                line_number=int(finding.line_number),
                line=str(finding.line),
            )
        )
    return findings


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

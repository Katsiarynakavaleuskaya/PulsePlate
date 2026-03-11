#!/usr/bin/env python3
"""Fail-fast local environment parity check for `make verify`.

This script validates that the clean-clone `.venv` contains the small set of
packages required by the canonical local verification gate. It is intentionally
non-mutating and points developers to the documented recovery path.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
REQUIRED_MODULES: tuple[tuple[str, str], ...] = (
    ("flake8", "lint"),
    ("mypy", "typecheck"),
    ("pytest", "test-fast"),
    ("coverage", "diff-cov"),
    ("diff_cover", "diff-cov"),
    (
        "opentelemetry.sdk.trace.export.in_memory_span_exporter",
        "tests/test_genai_tracing.py",
    ),
)


def _import_module(module_name: str) -> str | None:
    """Return error text when a module import fails, else None."""
    try:
        importlib.import_module(module_name)
        return None
    except Exception as exc:  # pragma: no cover - exercised through public helpers
        return str(exc)


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
) -> list[str]:
    """Build deterministic failure lines for terminal output."""
    lines = [
        "ERROR: local verify environment is incomplete.",
        f"Expected venv interpreter: {python_executable}",
        "Missing verify-critical modules:",
    ]
    for module_name, verify_stage, error in missing_modules:
        lines.append(f"- {module_name} [{verify_stage}] :: {error}")
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

    current_python = Path(sys.executable).resolve()
    if not current_python.samefile(VENV_PYTHON):
        print("ERROR: verify-env must run inside the repo .venv interpreter.")
        print(f"Expected venv interpreter: {VENV_PYTHON}")
        print(f"Current interpreter: {current_python}")
        print("Recovery:")
        print("- Run `make verify` or `make verify-env` from repo root")
        print("- If the venv is missing, run `make venv`")
        print("- If the venv drifted, run `make venv-sync`")
        return 1

    missing_modules = collect_missing_modules()
    if missing_modules:
        for line in build_failure_output(
            python_executable=current_python,
            missing_modules=missing_modules,
        ):
            print(line)
        return 1

    print("verify-env: local verify environment passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

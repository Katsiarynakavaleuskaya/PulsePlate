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

import hashlib
import importlib
import importlib.util
import re
import os
import subprocess  # nosec B404: subprocess is required for bounded local guard execution (remove-by: 2027-01-01, ref: PR-1243)
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

    location_id: str
    line_number: int


def _import_module(module_name: str) -> str | None:
    """Return error text when a module import fails, else None."""
    try:
        importlib.import_module(module_name)
        return None
    except Exception as exc:  # pragma: no cover - exercised through public helpers
        return str(exc)


def collect_unexpected_startup_hooks() -> list[StartupHookFinding]:
    """Return unexpected executable .pth hooks for the current repo interpreter."""
    expected_guard = Path(__file__).resolve().with_name("check_python_startup_hooks.py")
    if (
        STARTUP_HOOK_GUARD != expected_guard
        or expected_guard.is_symlink()
        or not expected_guard.is_file()
        or VENV_PYTHON != REPO_ROOT / ".venv" / "bin" / "python"
    ):
        raise RuntimeError("Local startup guard inputs are unavailable.")
    module_name = (
        "scripts.ci.check_python_startup_hooks" if __package__ else "check_python_startup_hooks"
    )
    try:
        spec = importlib.util.find_spec(module_name)
        guard = (
            importlib.import_module(module_name)
            if spec is not None and spec.origin == str(expected_guard)
            else None
        )
    except (ImportError, OSError, ValueError):
        guard = None
    if guard is None:
        raise RuntimeError("Local startup guard source is unavailable.")
    try:
        executable = guard.resolve_python_executable(str(VENV_PYTHON))
        guard._revalidate_python_executable(executable)
    except (OSError, RuntimeError, ValueError):
        executable = None
    if executable is None:
        raise RuntimeError("Local startup guard interpreter is unavailable.")
    python = str(executable.invocation_path)
    try:
        result = subprocess.run(  # nosec B603: argv uses fixed repo-local Python and guard paths only (remove-by: 2027-01-01, ref: PR-1243)
            [python, "-P", "-S", str(expected_guard), "--python-executable", python],
            cwd=REPO_ROOT,
            env=guard._startup_probe_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        failure = "Local startup guard timed out."
    except (OSError, UnicodeError, ValueError):
        failure = "Local startup guard execution or decoding failed."
    else:
        failure = ""
    if failure:
        raise RuntimeError(failure)
    if result.returncode == 0:
        if result.stdout == "startup-hook-guard: no unexpected executable .pth files detected.\n":
            return []
        raise RuntimeError("Invalid local startup guard clean report.")
    if result.returncode != 1:
        raise RuntimeError("Local startup guard failed.")

    # The stock formatter owns both header lines and the exact current allowlist footer.
    header, subheader, footer = guard.format_failure_lines([])
    lines = result.stdout.split("\n")
    if len(lines) < 5 or lines[:2] != [header, subheader] or lines[-2:] != [footer, ""]:
        raise RuntimeError("Invalid local startup guard finding report.")
    findings = []
    seen: set[tuple[str, int]] = set()
    for row in lines[2:-2]:
        if not row.startswith("- "):
            raise RuntimeError("Invalid local startup guard finding row.")
        location, sep, statement = row[2:].partition(" :: ")
        path_text, colon, number = location.rpartition(":")
        path = Path(path_text)
        if (
            not sep
            or not colon
            or not path.is_absolute()
            or path.suffix != ".pth"
            or path.name in guard.ALLOWED_EXECUTABLE_PTH_FILENAMES
            or ".." in path.parts
            or not path_text.isprintable()
            or not re.fullmatch(r"[1-9][0-9]{0,8}", number)
            or not guard.EXECUTABLE_IMPORT_PATTERN.match(statement)
            or not statement.replace("\t", " ").isprintable()
        ):
            raise RuntimeError("Invalid local startup guard finding row.")
        # Keep a stable locator without disclosing directory names or executable text.
        line_number = int(number)
        identity = (path_text, line_number)
        if identity in seen:
            raise RuntimeError("Duplicate local startup guard finding.")
        seen.add(identity)
        locator = hashlib.sha256(path_text.encode("utf-8")).hexdigest()[:16]
        findings.append(StartupHookFinding(location_id=locator, line_number=line_number))
    return findings


def _parse_absolute_shebang_interpreter(first_line: str) -> Path | None:
    """
    Return interpreter path from shebang when the first token is an absolute path.

    If the shebang has extra arguments after that token (for example ``#!/usr/bin/python -O``),
    only the first token is used. ``#!/usr/bin/env ...`` yields None (not validated in v1).
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


def _resolve_interpreter_path(interpreter: Path) -> Path:
    """Resolve a shebang interpreter path (narrow seam for tests)."""
    return interpreter.resolve()


def _format_venv_bin_display(bin_dir: Path) -> str:
    """Human-readable venv bin path for errors (prefer repo-relative)."""
    try:
        return str(bin_dir.relative_to(REPO_ROOT))
    except ValueError:
        return str(bin_dir)


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
        first_line = lines[0].lstrip("\ufeff")
        interpreter = _parse_absolute_shebang_interpreter(first_line)
        if interpreter is None:
            continue
        try:
            interp_resolved = _resolve_interpreter_path(interpreter)
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
    venv_bin_dir: Path | None = None,
) -> list[str]:
    """Build deterministic failure lines for terminal output."""
    bin_dir = venv_bin_dir if venv_bin_dir is not None else VENV_BIN_DIR
    bin_display = _format_venv_bin_display(bin_dir)
    lines = [
        "ERROR: local verify environment is incomplete.",
        f"Expected venv interpreter: {python_executable}",
    ]
    if broken_console_wrappers:
        lines.append(f"Stale or broken venv console scripts ({bin_display}):")
    for script_name, reason in broken_console_wrappers:
        lines.append(f"- {script_name} :: {reason}")
    if missing_modules:
        lines.append("Missing verify-critical Python modules:")
    for module_name, verify_stage, error in missing_modules:
        lines.append(f"- {module_name} [{verify_stage}] :: {error}")
    if unexpected_startup_hooks:
        lines.append("Unexpected executable startup hooks (.pth):")
        lines.extend(
            f"- .pth location sha256:{finding.location_id}, line {finding.line_number}"
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

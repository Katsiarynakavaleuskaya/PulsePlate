#!/usr/bin/env python3
"""Guard Python startup hooks implemented via executable .pth files."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

ALLOWED_EXECUTABLE_PTH_FILENAMES: tuple[str, ...] = (
    "a1_coverage.pth",
    "distutils-precedence.pth",
)
EXECUTABLE_IMPORT_PATTERN = re.compile(r"^\s*import\b")


@dataclass(frozen=True)
class ExecutablePthFinding:
    """A single unexpected executable import line inside a .pth file."""

    path: Path
    line_number: int
    line: str


def extract_executable_lines(contents: str) -> list[tuple[int, str]]:
    """Return import-bearing lines that Python would execute from a .pth file."""
    executable_lines: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(contents.splitlines(), start=1):
        if EXECUTABLE_IMPORT_PATTERN.match(raw_line):
            executable_lines.append((line_number, raw_line.rstrip()))
    return executable_lines


def _iter_existing_site_packages(site_packages: Iterable[Path]) -> Iterable[Path]:
    for site_dir in site_packages:
        if site_dir.exists():
            yield site_dir


def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved_path = path.resolve()
        if resolved_path in seen:
            continue
        seen.add(resolved_path)
        unique_paths.append(resolved_path)
    return unique_paths


def collect_unexpected_executable_pth_files(
    site_packages: Iterable[Path],
    *,
    allowed_filenames: Sequence[str] = ALLOWED_EXECUTABLE_PTH_FILENAMES,
) -> list[ExecutablePthFinding]:
    """Collect executable .pth imports that are not on the filename allowlist."""
    allowed = set(allowed_filenames)
    findings: list[ExecutablePthFinding] = []
    for site_dir in _iter_existing_site_packages(site_packages):
        for pth_file in sorted(site_dir.glob("*.pth")):
            executable_lines = extract_executable_lines(pth_file.read_text(encoding="utf-8"))
            if not executable_lines or pth_file.name in allowed:
                continue
            findings.extend(
                ExecutablePthFinding(
                    path=pth_file,
                    line_number=line_number,
                    line=line,
                )
                for line_number, line in executable_lines
            )
    return findings


def collect_site_packages_from_site_module(site_module: Any) -> list[Path]:
    """Return enabled site-packages from a `site`-compatible module."""
    site_packages: list[Path] = []

    getsitepackages = getattr(site_module, "getsitepackages", None)
    if getsitepackages is not None:
        value = getsitepackages()
        if isinstance(value, str):
            site_packages.append(Path(value))
        else:
            site_packages.extend(Path(path) for path in value)

    if getattr(site_module, "ENABLE_USER_SITE", False):
        getusersitepackages = getattr(site_module, "getusersitepackages", None)
        if getusersitepackages is not None:
            value = getusersitepackages()
            if value is None:
                pass
            elif isinstance(value, str):
                site_packages.append(Path(value))
            else:
                site_packages.extend(Path(path) for path in value)

    return _dedupe_paths(site_packages)


def current_interpreter_site_packages() -> list[Path]:
    """Return site-packages for the currently running interpreter."""
    import site

    return collect_site_packages_from_site_module(site)


def resolve_python_executable_path(python_executable: str | Path) -> Path:
    """Resolve command names via PATH before inferring interpreter prefixes."""
    candidate = Path(python_executable).expanduser()
    if candidate.is_absolute() or candidate.parent != Path("."):
        return candidate.resolve()

    resolved_executable = shutil.which(str(candidate))
    if resolved_executable is not None:
        return Path(resolved_executable).resolve()
    return candidate.resolve()


def infer_prefix_site_packages(python_executable: str | Path) -> list[Path]:
    """Infer site-packages directories from a Python executable path without execution."""
    python_path = resolve_python_executable_path(python_executable)
    prefix = python_path.parent.parent
    candidate_paths: list[Path] = []

    for pattern in (
        "lib/python*/site-packages",
        "lib/python*/dist-packages",
        "lib64/python*/site-packages",
        "lib64/python*/dist-packages",
    ):
        candidate_paths.extend(sorted(prefix.glob(pattern)))

    candidate_paths.append(prefix / "Lib" / "site-packages")
    return list(_iter_existing_site_packages(_dedupe_paths(candidate_paths)))


def site_packages_for_interpreter(python_executable: str) -> list[Path]:
    """Resolve executable site-packages for a target interpreter without re-launching it."""
    target_python = resolve_python_executable_path(python_executable)
    current_python = Path(sys.executable).resolve()
    if target_python == current_python:
        return current_interpreter_site_packages()
    return infer_prefix_site_packages(target_python)


def external_interpreter_site_packages(python_executable: str) -> list[Path]:
    """Backward-compatible wrapper for callers expecting the old helper name."""
    return site_packages_for_interpreter(python_executable)


def format_failure_lines(findings: Sequence[ExecutablePthFinding]) -> list[str]:
    """Render deterministic terminal lines for unexpected startup hooks."""
    lines = [
        "ERROR: unexpected executable Python startup hook (.pth) detected.",
        "Unexpected executable import lines:",
    ]
    lines.extend(
        f"- {finding.path}:{finding.line_number} :: {finding.line}" for finding in findings
    )
    lines.append(
        "Allowed executable .pth filenames: " + ", ".join(sorted(ALLOWED_EXECUTABLE_PTH_FILENAMES))
    )
    return lines


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python-executable",
        help="Inspect site-packages for the given Python executable.",
    )
    parser.add_argument(
        "--site-packages",
        action="append",
        default=[],
        help="Additional site-packages directory to inspect. Can be repeated.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    site_packages = [Path(path) for path in args.site_packages]
    if args.python_executable:
        site_packages.extend(site_packages_for_interpreter(args.python_executable))
    elif not site_packages:
        site_packages.extend(current_interpreter_site_packages())

    findings = collect_unexpected_executable_pth_files(site_packages)
    if findings:
        for line in format_failure_lines(findings):
            print(line)
        return 1

    print("startup-hook-guard: no unexpected executable .pth files detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

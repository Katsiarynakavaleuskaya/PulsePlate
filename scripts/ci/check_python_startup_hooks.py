#!/usr/bin/env python3
"""Guard Python startup hooks implemented via executable .pth files."""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404: subprocess is required for bounded repo-local startup-hook inspection against a selected Python interpreter (remove-by: 2026-07-31, ref: PR-litellm-private-proxy)
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ALLOWED_EXECUTABLE_PTH_FILENAMES: tuple[str, ...] = (
    "a1_coverage.pth",
    # NVIDIA ships this namespace redirector inside the pinned cuda-bindings wheel.
    # NVIDIA поставляет этот redirector в составе зафиксированного wheel cuda-bindings.
    "_cuda_bindings_redirector.pth",
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


def current_interpreter_site_packages() -> list[Path]:
    """Return site-packages for the currently running interpreter."""
    import site

    site_packages: list[str] = []
    for getter_name in ("getsitepackages", "getusersitepackages"):
        if (
            getter_name == "getusersitepackages"
            and getattr(site, "ENABLE_USER_SITE", None) is False
        ):
            continue
        getter = getattr(site, getter_name, None)
        if getter is None:
            continue
        value = getter()
        if value is None:
            continue
        if isinstance(value, str):
            site_packages.append(value)
        else:
            site_packages.extend(value)
    return [Path(path) for path in dict.fromkeys(site_packages)]


def external_interpreter_site_packages(python_executable: str) -> list[Path]:
    """Query site-packages for an arbitrary Python executable."""
    probe = (
        "import json, site\n"
        "paths = []\n"
        "for getter_name in ('getsitepackages', 'getusersitepackages'):\n"
        "    if getter_name == 'getusersitepackages' and getattr(site, 'ENABLE_USER_SITE', None) is False:\n"
        "        continue\n"
        "    getter = getattr(site, getter_name, None)\n"
        "    if getter is None:\n"
        "        continue\n"
        "    value = getter()\n"
        "    if value is None:\n"
        "        continue\n"
        "    if isinstance(value, str):\n"
        "        paths.append(value)\n"
        "    else:\n"
        "        paths.extend(value)\n"
        "print(json.dumps(list(dict.fromkeys(paths))))\n"
    )
    try:
        result = subprocess.run(  # nosec B603: argv uses the provided Python executable plus a fixed inline site-packages probe with shell=False (remove-by: 2026-07-31, ref: PR-litellm-private-proxy)
            [python_executable, "-S", "-c", probe],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Timed out probing site-packages for {python_executable}: {exc}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        details = stderr or stdout or str(exc)
        raise RuntimeError(
            f"Unable to probe site-packages for {python_executable}: {details}"
        ) from exc

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse site-packages for {python_executable}: {exc}") from exc
    return [Path(path) for path in payload]


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
        site_packages.extend(external_interpreter_site_packages(args.python_executable))
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

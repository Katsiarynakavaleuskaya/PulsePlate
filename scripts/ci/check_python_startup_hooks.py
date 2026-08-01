#!/usr/bin/env python3
"""Guard Python startup hooks implemented via executable .pth files."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404: subprocess is required for bounded repo-local startup-hook inspection against a selected Python interpreter (remove-by: 2026-10-31, ref: PR-litellm-private-proxy)
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
STARTUP_SAFE_SITE_PACKAGES_PROBE = (
    "import json, os, site, sys\n"
    "def _skip_addpackage(sitedir, name, known_paths):\n"
    "    return known_paths\n"
    "def _check_enable_user_site():\n"
    "    if hasattr(os, 'getuid') and hasattr(os, 'geteuid') and os.geteuid() != os.getuid():\n"
    "        return None\n"
    "    if hasattr(os, 'getgid') and hasattr(os, 'getegid') and os.getegid() != os.getgid():\n"
    "        return None\n"
    "    return True\n"
    "site.addpackage = _skip_addpackage\n"
    "site.execsitecustomize = lambda: None\n"
    "site.execusercustomize = lambda: None\n"
    "site.check_enableusersite = _check_enable_user_site\n"
    "site.main()\n"
    "paths = list(site.getsitepackages())\n"
    "if site.ENABLE_USER_SITE:\n"
    "    user_site = site.getusersitepackages()\n"
    "    paths.extend([user_site] if isinstance(user_site, str) else user_site)\n"
    "print(json.dumps({\n"
    "    'executable': sys.executable,\n"
    "    'prefix': sys.prefix,\n"
    "    'base_prefix': sys.base_prefix,\n"
    "    'site_packages': list(dict.fromkeys(paths)),\n"
    "}))\n"
)


@dataclass(frozen=True)
class ExecutablePthFinding:
    """A single unexpected executable import line inside a .pth file."""

    path: Path
    line_number: int
    line: str


@dataclass(frozen=True)
class ResolvedPythonExecutable:
    """Validated executable identity with the final invocation symlink preserved."""

    invocation_path: Path
    resolved_target: Path


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


def resolve_python_executable(python_executable: str) -> ResolvedPythonExecutable:
    """Resolve an interpreter to an absolute, executable invocation path."""
    if not python_executable.strip() or "\x00" in python_executable:
        raise RuntimeError("Python executable must be a non-empty path or command name.")

    if os.path.dirname(python_executable):
        candidate = Path(python_executable).expanduser()
    else:
        discovered = shutil.which(python_executable)
        if discovered is None:
            raise RuntimeError(f"Unable to resolve Python executable: {python_executable}")
        candidate = Path(discovered)

    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate

    try:
        invocation_path = candidate.parent.resolve(strict=True) / candidate.name
        resolved_target = invocation_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(
            f"Unable to resolve Python executable: {python_executable}: {exc}"
        ) from exc

    if not resolved_target.is_file() or not os.access(resolved_target, os.X_OK):
        raise RuntimeError(
            "Python executable must resolve to an executable regular file: " f"{python_executable}"
        )
    return ResolvedPythonExecutable(
        invocation_path=invocation_path,
        resolved_target=resolved_target,
    )


def _revalidate_python_executable(executable: ResolvedPythonExecutable) -> None:
    """Fail closed if the selected executable target changed before launch."""
    try:
        current_target = executable.invocation_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(
            f"Python executable became unavailable: {executable.invocation_path}: {exc}"
        ) from exc
    if (
        current_target != executable.resolved_target
        or not current_target.is_file()
        or not os.access(current_target, os.X_OK)
    ):
        raise RuntimeError(f"Python executable changed before launch: {executable.invocation_path}")


def external_interpreter_site_packages(python_executable: str) -> list[Path]:
    """Query site-packages for an arbitrary Python executable."""
    executable = resolve_python_executable(python_executable)
    _revalidate_python_executable(executable)
    try:
        result = subprocess.run(  # nosec B603: argv uses the provided Python executable plus a fixed inline site-packages probe with shell=False (remove-by: 2026-10-31, ref: PR-litellm-private-proxy)
            [
                str(executable.invocation_path),
                "-I",
                "-S",
                "-c",
                STARTUP_SAFE_SITE_PACKAGES_PROBE,
            ],
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
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Unable to parse site-packages for {python_executable}: expected JSON object"
        )
    reported_executable = payload.get("executable")
    reported_prefix = payload.get("prefix")
    reported_base_prefix = payload.get("base_prefix")
    site_packages = payload.get("site_packages")
    if (
        not isinstance(reported_executable, str)
        or not isinstance(reported_prefix, str)
        or not isinstance(reported_base_prefix, str)
        or not isinstance(site_packages, list)
    ):
        raise RuntimeError(
            f"Unable to parse site-packages for {python_executable}: invalid payload shape"
        )
    if not Path(reported_prefix).is_absolute() or not Path(reported_base_prefix).is_absolute():
        raise RuntimeError(
            f"Unable to parse site-packages for {python_executable}: relative prefix"
        )
    reported_path = Path(reported_executable)
    if not reported_path.is_absolute():
        raise RuntimeError(
            f"Unable to parse site-packages for {python_executable}: relative executable"
        )
    try:
        normalized_reported_path = reported_path.parent.resolve(strict=True) / reported_path.name
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(f"Unable to parse site-packages for {python_executable}: {exc}") from exc
    if normalized_reported_path != executable.invocation_path:
        raise RuntimeError(
            f"Unable to parse site-packages for {python_executable}: executable mismatch"
        )
    if not site_packages:
        raise RuntimeError(
            f"Unable to parse site-packages for {python_executable}: empty path inventory"
        )

    parsed_paths: list[Path] = []
    for value in site_packages:
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise RuntimeError(
                f"Unable to parse site-packages for {python_executable}: invalid path"
            )
        parsed_paths.append(Path(value))
    return list(dict.fromkeys(parsed_paths))


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

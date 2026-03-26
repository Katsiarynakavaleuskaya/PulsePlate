#!/usr/bin/env python3
"""Install pinned requirements through a local wheelhouse and startup-hook guard."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404: subprocess is required for bounded pip/python invocations during locked installation (remove-by: 2026-07-31, ref: PR-litellm-hardening)
import sys
import tempfile
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUIREMENTS_FILE = REPO_ROOT / "requirements.txt"
DEFAULT_DEV_REQUIREMENTS_FILE = REPO_ROOT / "requirements-dev.txt"
DEFAULT_CONSTRAINTS_FILE = REPO_ROOT / "constraints.txt"
DEFAULT_STARTUP_HOOK_GUARD_PATH = REPO_ROOT / "scripts" / "ci" / "check_python_startup_hooks.py"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python interpreter used to run pip and the startup-hook guard.",
    )
    parser.add_argument(
        "--requirements-file",
        type=Path,
        default=DEFAULT_REQUIREMENTS_FILE,
        help="Pinned runtime requirements file.",
    )
    parser.add_argument(
        "--dev-requirements-file",
        type=Path,
        default=DEFAULT_DEV_REQUIREMENTS_FILE,
        help="Pinned development requirements file.",
    )
    parser.add_argument(
        "--constraints-file",
        type=Path,
        default=DEFAULT_CONSTRAINTS_FILE,
        help="Constraints file applied during download/install when present.",
    )
    parser.add_argument(
        "--wheelhouse-dir",
        type=Path,
        help="Existing wheelhouse directory. If omitted, a temporary wheelhouse is built.",
    )
    parser.add_argument(
        "--install-dev",
        action="store_true",
        help="Install development requirements after runtime requirements.",
    )
    parser.add_argument(
        "--require-virtualenv",
        action="store_true",
        help="Fail if the target Python interpreter is not inside a virtual environment.",
    )
    parser.add_argument(
        "--upgrade-pip",
        action="store_true",
        help="Explicitly upgrade pip before wheel resolution.",
    )
    parser.add_argument(
        "--guard-script",
        type=Path,
        default=DEFAULT_STARTUP_HOOK_GUARD_PATH,
        help="Path to the startup-hook guard script used for static .pth scanning.",
    )
    return parser.parse_args(argv)


def resolve_requirement_files(
    *,
    requirements_file: Path,
    dev_requirements_file: Path,
    install_dev: bool,
) -> list[Path]:
    """Return the pinned requirement surfaces to download/install."""
    requirement_files: list[Path] = []
    if requirements_file.exists():
        requirement_files.append(requirements_file)
    if install_dev and dev_requirements_file.exists():
        requirement_files.append(dev_requirements_file)
    if not requirement_files:
        raise FileNotFoundError("No pinned requirements files found for installation.")
    return requirement_files


def build_pip_download_command(
    *,
    python_executable: str,
    requirement_file: Path,
    wheelhouse_dir: Path,
    constraints_file: Path | None,
) -> list[str]:
    constraints_file = validate_constraints_file(constraints_file)
    command = [
        python_executable,
        "-m",
        "pip",
        "download",
        "--only-binary",
        ":all:",
        "--dest",
        str(wheelhouse_dir),
        "--requirement",
        str(requirement_file),
    ]
    if constraints_file is not None:
        command.extend(["--constraint", str(constraints_file)])
    return command


def build_pip_install_command(
    *,
    python_executable: str,
    requirement_file: Path,
    wheelhouse_dir: Path,
    constraints_file: Path | None,
) -> list[str]:
    constraints_file = validate_constraints_file(constraints_file)
    command = [
        python_executable,
        "-m",
        "pip",
        "install",
        "--no-index",
        "--find-links",
        str(wheelhouse_dir),
        "--requirement",
        str(requirement_file),
    ]
    if constraints_file is not None:
        command.extend(["--constraint", str(constraints_file)])
    return command


def validate_constraints_file(constraints_file: Path | None) -> Path | None:
    """Return an existing constraints file or fail closed when a path is invalid."""
    if constraints_file is None:
        return None
    if not constraints_file.exists():
        raise FileNotFoundError(f"Constraints file not found: {constraints_file}")
    return constraints_file


def is_virtualenv_python(python_executable: str) -> bool:
    """Return True when the target interpreter runs inside a virtualenv."""
    probe = (
        "import json, sys\n"
        "print(json.dumps({'prefix': sys.prefix, 'base_prefix': getattr(sys, 'base_prefix', sys.prefix)}))\n"
    )
    result = subprocess.run(  # nosec B603: argv uses an explicit Python executable and fixed venv probe code only (remove-by: 2026-07-31, ref: PR-litellm-hardening)
        [python_executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
    )
    import json

    payload = json.loads(result.stdout)
    return bool(payload["prefix"] != payload["base_prefix"])


def run_command(command: Sequence[str]) -> None:
    subprocess.run(  # nosec B603: commands are built internally from pinned requirement/install helpers only (remove-by: 2026-07-31, ref: PR-litellm-hardening)
        list(command),
        check=True,
    )


def upgrade_pip(python_executable: str) -> None:
    run_command([python_executable, "-m", "pip", "install", "--upgrade", "pip"])


def collect_startup_hook_failure_lines(
    *,
    guard_script: Path,
    python_executable: str,
) -> list[str]:
    """Run the startup-hook guard as a subprocess for target site-packages."""
    result = subprocess.run(  # nosec B603: argv uses the selected Python interpreter plus a fixed repo guard script path (remove-by: 2026-07-31, ref: PR-litellm-hardening)
        [
            python_executable,
            str(guard_script),
            "--python-executable",
            python_executable,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    stdout_lines = [line for line in result.stdout.splitlines() if line.strip()]
    stderr_lines = [line for line in result.stderr.splitlines() if line.strip()]

    if result.returncode == 0:
        return []
    if result.returncode == 1:
        if stdout_lines:
            return stdout_lines
        if stderr_lines:
            return stderr_lines
        return ["ERROR: startup-hook guard reported unexpected executable .pth files."]

    diagnostic_lines = (
        stderr_lines or stdout_lines or ["startup-hook guard exited without diagnostics."]
    )
    raise RuntimeError("Startup-hook guard failed: " + " | ".join(diagnostic_lines))


def install_from_wheelhouse(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    wheelhouse_dir: Path,
) -> None:
    for requirement_file in requirement_files:
        run_command(
            build_pip_install_command(
                python_executable=python_executable,
                requirement_file=requirement_file,
                wheelhouse_dir=wheelhouse_dir,
                constraints_file=constraints_file,
            )
        )


def build_wheelhouse(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    wheelhouse_dir: Path,
) -> None:
    wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    for requirement_file in requirement_files:
        run_command(
            build_pip_download_command(
                python_executable=python_executable,
                requirement_file=requirement_file,
                wheelhouse_dir=wheelhouse_dir,
                constraints_file=constraints_file,
            )
        )


def install_with_guard(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    wheelhouse_dir: Path,
    guard_script: Path,
) -> int:
    build_wheelhouse(
        python_executable=python_executable,
        requirement_files=requirement_files,
        constraints_file=constraints_file,
        wheelhouse_dir=wheelhouse_dir,
    )
    install_from_wheelhouse(
        python_executable=python_executable,
        requirement_files=requirement_files,
        constraints_file=constraints_file,
        wheelhouse_dir=wheelhouse_dir,
    )

    failure_lines = collect_startup_hook_failure_lines(
        guard_script=guard_script,
        python_executable=python_executable,
    )
    if failure_lines:
        for line in failure_lines:
            print(line)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        validated_constraints_file = validate_constraints_file(args.constraints_file)
        requirement_files = resolve_requirement_files(
            requirements_file=args.requirements_file,
            dev_requirements_file=args.dev_requirements_file,
            install_dev=args.install_dev,
        )

        if args.require_virtualenv and not is_virtualenv_python(args.python_executable):
            print("ERROR: refusing to install packages with a non-virtualenv interpreter.")
            print(f"Python executable: {args.python_executable}")
            return 1

        if args.upgrade_pip:
            upgrade_pip(args.python_executable)

        if args.wheelhouse_dir is not None:
            return install_with_guard(
                python_executable=args.python_executable,
                requirement_files=requirement_files,
                constraints_file=validated_constraints_file,
                wheelhouse_dir=args.wheelhouse_dir,
                guard_script=args.guard_script,
            )

        with tempfile.TemporaryDirectory(prefix="pulseplate-wheelhouse-") as temp_dir:
            wheelhouse_dir = Path(temp_dir)
            return install_with_guard(
                python_executable=args.python_executable,
                requirement_files=requirement_files,
                constraints_file=validated_constraints_file,
                wheelhouse_dir=wheelhouse_dir,
                guard_script=args.guard_script,
            )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: locked install failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

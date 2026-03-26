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
STARTUP_HOOK_GUARD_PATH = REPO_ROOT / "scripts" / "ci" / "check_python_startup_hooks.py"


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
        "--skip-pip-upgrade",
        action="store_true",
        help="Skip `python -m pip install --upgrade pip` before wheel resolution.",
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
    command = [
        python_executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(wheelhouse_dir),
        "--requirement",
        str(requirement_file),
    ]
    if constraints_file is not None and constraints_file.exists():
        command.extend(["--constraint", str(constraints_file)])
    return command


def build_pip_install_command(
    *,
    python_executable: str,
    requirement_file: Path,
    wheelhouse_dir: Path,
    constraints_file: Path | None,
) -> list[str]:
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
    if constraints_file is not None and constraints_file.exists():
        command.extend(["--constraint", str(constraints_file)])
    return command


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
    return payload["prefix"] != payload["base_prefix"]


def run_command(command: Sequence[str]) -> None:
    subprocess.run(  # nosec B603: commands are built internally from pinned requirement/install helpers only (remove-by: 2026-07-31, ref: PR-litellm-hardening)
        list(command),
        check=True,
    )


def upgrade_pip(python_executable: str) -> None:
    run_command([python_executable, "-m", "pip", "install", "--upgrade", "pip"])


def run_startup_hook_guard(python_executable: str) -> None:
    run_command(
        [
            python_executable,
            str(STARTUP_HOOK_GUARD_PATH),
            "--python-executable",
            python_executable,
        ]
    )


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


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    requirement_files = resolve_requirement_files(
        requirements_file=args.requirements_file,
        dev_requirements_file=args.dev_requirements_file,
        install_dev=args.install_dev,
    )

    if args.require_virtualenv and not is_virtualenv_python(args.python_executable):
        print("ERROR: refusing to install packages with a non-virtualenv interpreter.")
        print(f"Python executable: {args.python_executable}")
        return 1

    if not args.skip_pip_upgrade:
        upgrade_pip(args.python_executable)

    if args.wheelhouse_dir is not None:
        build_wheelhouse(
            python_executable=args.python_executable,
            requirement_files=requirement_files,
            constraints_file=args.constraints_file,
            wheelhouse_dir=args.wheelhouse_dir,
        )
        install_from_wheelhouse(
            python_executable=args.python_executable,
            requirement_files=requirement_files,
            constraints_file=args.constraints_file,
            wheelhouse_dir=args.wheelhouse_dir,
        )
        run_startup_hook_guard(args.python_executable)
        return 0

    with tempfile.TemporaryDirectory(prefix="pulseplate-wheelhouse-") as temp_dir:
        wheelhouse_dir = Path(temp_dir)
        build_wheelhouse(
            python_executable=args.python_executable,
            requirement_files=requirement_files,
            constraints_file=args.constraints_file,
            wheelhouse_dir=wheelhouse_dir,
        )
        install_from_wheelhouse(
            python_executable=args.python_executable,
            requirement_files=requirement_files,
            constraints_file=args.constraints_file,
            wheelhouse_dir=wheelhouse_dir,
        )
        run_startup_hook_guard(args.python_executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

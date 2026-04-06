#!/usr/bin/env python3
"""Install pinned requirements through a local wheelhouse and startup-hook guard."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import subprocess  # nosec B404: subprocess is required for bounded pip/python invocations during locked installation (remove-by: 2026-07-31, ref: PR-litellm-hardening)
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Sequence
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUIREMENTS_FILE = REPO_ROOT / "requirements.txt"
DEFAULT_DEV_REQUIREMENTS_FILE = REPO_ROOT / "requirements-dev.txt"
DEFAULT_TEST_REQUIREMENTS_FILE = REPO_ROOT / "requirements-test.txt"
DEFAULT_CI_LITE_REQUIREMENTS_FILE = REPO_ROOT / "requirements-ci-lite.txt"
DEFAULT_CONSTRAINTS_FILE = REPO_ROOT / "constraints.txt"
DEFAULT_STARTUP_HOOK_GUARD_PATH = REPO_ROOT / "scripts" / "ci" / "check_python_startup_hooks.py"
APPROVED_INDEX_ENV_VAR = "PULSEPLATE_PYTHON_INDEX_URL"
TRUSTED_HOST_ENV_VAR = "PULSEPLATE_PYTHON_TRUSTED_HOST"
AMBIENT_INDEX_OVERRIDE_ENV_VARS: tuple[str, ...] = (
    "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL",
    "UV_INDEX_URL",
    "UV_EXTRA_INDEX_URL",
)
BLOCKED_INDEX_HOSTS: tuple[str, ...] = (
    "pypi.org",
    "files.pythonhosted.org",
    "test.pypi.org",
)
INSTALL_MODES: tuple[str, ...] = ("wheelhouse", "direct-proxy")
REQUIREMENTS_PROFILES: tuple[str, ...] = (
    "runtime",
    "runtime-dev",
    "runtime-test",
    "ci-lite",
)
DOCKER_SINGLE_PASS_LOCKED_INSTALL_ENV = "PULSEPLATE_DOCKER_SINGLE_PASS_LOCKED_INSTALL"  # nosec B105: public env key contract, not a password (remove-by: 2026-12-31, ref: PR-docker-gha-buildx-pip-cache)
DOCKER_PIP_LAYER_CACHE_ENV = "PULSEPLATE_DOCKER_PIP_LAYER_CACHE"


def _env_truthy(name: str) -> bool:
    """Return True when env is set to a common affirmative string."""
    value = os.environ.get(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def docker_single_pass_locked_install_enabled() -> bool:
    """Docker single-pass: install once on target interpreter, then run startup-hook guard there."""
    return _env_truthy(DOCKER_SINGLE_PASS_LOCKED_INSTALL_ENV)


def docker_pip_layer_cache_enabled() -> bool:
    """When True, omit pip --no-cache-dir so BuildKit cache mounts can reuse HTTP wheels."""
    return _env_truthy(DOCKER_PIP_LAYER_CACHE_ENV)


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
        "--test-requirements-file",
        type=Path,
        default=DEFAULT_TEST_REQUIREMENTS_FILE,
        help="Pinned test requirements file.",
    )
    parser.add_argument(
        "--ci-lite-requirements-file",
        type=Path,
        default=DEFAULT_CI_LITE_REQUIREMENTS_FILE,
        help="Pinned lightweight CI requirements file for non-test control-plane jobs.",
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
        "--install-test",
        action="store_true",
        help="Install test requirements after runtime requirements.",
    )
    parser.add_argument(
        "--requirements-profile",
        choices=REQUIREMENTS_PROFILES,
        help=(
            "Explicit pinned dependency profile. "
            "When set, it replaces the legacy --install-dev/--install-test flags."
        ),
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
    parser.add_argument(
        "--index-url",
        help=f"Approved private package proxy URL. Defaults to ${APPROVED_INDEX_ENV_VAR}.",
    )
    parser.add_argument(
        "--trusted-host",
        help=f"Optional trusted host for the approved proxy. Defaults to ${TRUSTED_HOST_ENV_VAR}.",
    )
    parser.add_argument(
        "--install-mode",
        choices=INSTALL_MODES,
        default="wheelhouse",
        help=(
            "Installation transport. 'wheelhouse' keeps the hermetic local wheelhouse path; "
            "'direct-proxy' installs from the approved proxy without creating a local wheelhouse."
        ),
    )
    return parser.parse_args(argv)


def resolve_requirement_files(
    *,
    requirements_file: Path,
    dev_requirements_file: Path,
    test_requirements_file: Path,
    ci_lite_requirements_file: Path,
    install_dev: bool,
    install_test: bool,
    requirements_profile: str | None,
) -> list[Path]:
    """Return the pinned requirement surfaces to download/install."""
    profile_files: dict[str, list[tuple[str, Path]]] = {
        "runtime": [("Requirements file", requirements_file)],
        "runtime-dev": [
            ("Requirements file", requirements_file),
            ("Dev requirements file", dev_requirements_file),
        ],
        "runtime-test": [
            ("Requirements file", requirements_file),
            ("Test requirements file", test_requirements_file),
        ],
        "ci-lite": [("CI lite requirements file", ci_lite_requirements_file)],
    }
    if requirements_profile is not None:
        return [
            validate_requirement_file(path, label=label)
            for label, path in profile_files[requirements_profile]
        ]

    requirement_files = [validate_requirement_file(requirements_file, label="Requirements file")]
    if install_test:
        requirement_files.append(
            validate_requirement_file(test_requirements_file, label="Test requirements file")
        )
    if install_dev:
        requirement_files.append(
            validate_requirement_file(dev_requirements_file, label="Dev requirements file")
        )
    return requirement_files


def validate_requirement_file(requirement_file: Path, *, label: str) -> Path:
    """Return an existing requirements surface or fail closed with a stable label."""
    if not requirement_file.exists():
        raise FileNotFoundError(f"{label} not found: {requirement_file}")
    return requirement_file


def build_pip_download_command(
    *,
    python_executable: str,
    requirement_file: Path,
    wheelhouse_dir: Path,
    constraints_file: Path | None,
    index_url: str,
    trusted_host: str | None,
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
    command.extend(["--index-url", index_url])
    if trusted_host:
        command.extend(["--trusted-host", trusted_host])
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


def build_pip_proxy_install_command(
    *,
    python_executable: str,
    requirement_file: Path,
    constraints_file: Path | None,
    index_url: str,
    trusted_host: str | None,
    allow_pip_download_cache: bool | None = None,
) -> list[str]:
    constraints_file = validate_constraints_file(constraints_file)
    use_pip_cache = (
        docker_pip_layer_cache_enabled()
        if allow_pip_download_cache is None
        else allow_pip_download_cache
    )
    command = [
        python_executable,
        "-m",
        "pip",
        "install",
        "--only-binary",
        ":all:",
        "--index-url",
        index_url,
        "--requirement",
        str(requirement_file),
    ]
    if not use_pip_cache:
        command.insert(4, "--no-cache-dir")
    if trusted_host:
        command.extend(["--trusted-host", trusted_host])
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


def normalize_trusted_host(trusted_host: str | None) -> str | None:
    """Return a normalized trusted-host value or None when unset."""
    if trusted_host is None:
        return None
    stripped = trusted_host.strip()
    return stripped or None


def validate_private_proxy_url(index_url: str) -> str:
    """Validate that the approved package source is a non-public proxy."""
    normalized = index_url.strip()
    if not normalized:
        raise RuntimeError("Approved Python package proxy URL must not be empty.")
    parsed = urlparse(normalized)
    hostname = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise RuntimeError("Approved Python package proxy must be an http(s) URL with a hostname.")
    canonical_hostname = hostname.rstrip(".").lower()
    if canonical_hostname in BLOCKED_INDEX_HOSTS:
        raise RuntimeError(
            f"Approved Python package proxy must not point to public host: {canonical_hostname}"
        )
    return normalized


def reject_ambient_index_overrides() -> None:
    """Fail closed when ambient pip/uv index overrides are present."""
    overrides = [
        env_var
        for env_var in AMBIENT_INDEX_OVERRIDE_ENV_VARS
        if os.environ.get(env_var, "").strip()
    ]
    if overrides:
        joined = ", ".join(overrides)
        raise RuntimeError(
            "Ambient Python package index overrides are forbidden for canonical installs: "
            f"{joined}. Use {APPROVED_INDEX_ENV_VAR} / {TRUSTED_HOST_ENV_VAR} instead."
        )


def resolve_private_proxy_settings(
    *,
    index_url: str | None,
    trusted_host: str | None,
) -> tuple[str, str | None]:
    """Resolve and validate the approved private package proxy contract."""
    resolved_index_url = index_url or os.environ.get(APPROVED_INDEX_ENV_VAR)
    if not resolved_index_url:
        raise RuntimeError(
            "Approved Python package proxy is required for canonical installs. "
            f"Set {APPROVED_INDEX_ENV_VAR} or pass --index-url."
        )
    reject_ambient_index_overrides()
    return (
        validate_private_proxy_url(resolved_index_url),
        normalize_trusted_host(trusted_host or os.environ.get(TRUSTED_HOST_ENV_VAR)),
    )


def is_virtualenv_python(python_executable: str) -> bool:
    """Return True when the target interpreter runs inside a virtualenv."""
    probe = (
        "import json, sys\n"
        "print(json.dumps({'prefix': sys.prefix, 'base_prefix': getattr(sys, 'base_prefix', sys.prefix)}))\n"
    )
    try:
        result = subprocess.run(  # nosec B603: argv uses an explicit Python executable and fixed venv probe code only (remove-by: 2026-07-31, ref: PR-litellm-hardening)
            [python_executable, "-c", probe],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Unable to probe virtualenv state for {python_executable}: {exc}"
        ) from exc
    return bool(payload["prefix"] != payload["base_prefix"])


def run_command(command: Sequence[str]) -> None:
    try:
        subprocess.run(  # nosec B603: commands are built internally from pinned requirement/install helpers only (remove-by: 2026-07-31, ref: PR-litellm-hardening)
            list(command),
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        command_text = " ".join(str(part) for part in command)
        raise RuntimeError(f"Command failed: {command_text}: {exc}") from exc


def upgrade_pip(
    python_executable: str,
    *,
    index_url: str,
    trusted_host: str | None,
) -> None:
    command = [
        python_executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "--index-url",
        index_url,
    ]
    if trusted_host:
        command.extend(["--trusted-host", trusted_host])
    run_command(command)


def collect_startup_hook_failure_lines(
    *,
    guard_script: Path,
    python_executable: str,
) -> list[str]:
    """Run the startup-hook guard as a subprocess for target site-packages."""
    result = subprocess.run(  # nosec B603: argv uses the selected Python interpreter plus a fixed repo guard script path (remove-by: 2026-07-31, ref: PR-litellm-hardening)
        [
            python_executable,
            "-S",
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


def _staging_python_path(staging_dir: Path) -> Path:
    """Return the canonical Python executable inside a disposable staging venv."""
    if os_name_is_windows():
        return staging_dir / "Scripts" / "python.exe"
    return staging_dir / "bin" / "python"


def os_name_is_windows() -> bool:
    """Return True when the current platform uses Windows-style venv paths."""
    return sys.platform.startswith("win")


@contextmanager
def staged_python_environment(target_python: str) -> Iterator[str]:
    """Create a disposable venv used to verify startup hooks before target install."""
    with tempfile.TemporaryDirectory(prefix="pulseplate-staging-venv-") as temp_dir:
        staging_dir = Path(temp_dir)
        run_command([target_python, "-m", "venv", str(staging_dir)])
        yield str(_staging_python_path(staging_dir))


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


def install_from_proxy(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    index_url: str,
    trusted_host: str | None,
    allow_pip_download_cache: bool | None = None,
) -> None:
    for requirement_file in requirement_files:
        run_command(
            build_pip_proxy_install_command(
                python_executable=python_executable,
                requirement_file=requirement_file,
                constraints_file=constraints_file,
                index_url=index_url,
                trusted_host=trusted_host,
                allow_pip_download_cache=allow_pip_download_cache,
            )
        )


def build_wheelhouse(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    wheelhouse_dir: Path,
    index_url: str,
    trusted_host: str | None,
) -> None:
    wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    for requirement_file in requirement_files:
        run_command(
            build_pip_download_command(
                python_executable=python_executable,
                requirement_file=requirement_file,
                wheelhouse_dir=wheelhouse_dir,
                constraints_file=constraints_file,
                index_url=index_url,
                trusted_host=trusted_host,
            )
        )


def install_with_guard(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    wheelhouse_dir: Path,
    guard_script: Path,
    index_url: str,
    trusted_host: str | None,
) -> int:
    build_wheelhouse(
        python_executable=python_executable,
        requirement_files=requirement_files,
        constraints_file=constraints_file,
        wheelhouse_dir=wheelhouse_dir,
        index_url=index_url,
        trusted_host=trusted_host,
    )

    with staged_python_environment(python_executable) as staging_python:
        install_from_wheelhouse(
            python_executable=staging_python,
            requirement_files=requirement_files,
            constraints_file=constraints_file,
            wheelhouse_dir=wheelhouse_dir,
        )

        failure_lines = collect_startup_hook_failure_lines(
            guard_script=guard_script,
            python_executable=staging_python,
        )
        if failure_lines:
            for line in failure_lines:
                print(line)
            return 1

    install_from_wheelhouse(
        python_executable=python_executable,
        requirement_files=requirement_files,
        constraints_file=constraints_file,
        wheelhouse_dir=wheelhouse_dir,
    )
    return 0


def install_with_guard_from_proxy(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    guard_script: Path,
    index_url: str,
    trusted_host: str | None,
) -> int:
    if docker_single_pass_locked_install_enabled():
        allow_cache = docker_pip_layer_cache_enabled()
        install_from_proxy(
            python_executable=python_executable,
            requirement_files=requirement_files,
            constraints_file=constraints_file,
            index_url=index_url,
            trusted_host=trusted_host,
            allow_pip_download_cache=allow_cache,
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

    with staged_python_environment(python_executable) as staging_python:
        install_from_proxy(
            python_executable=staging_python,
            requirement_files=requirement_files,
            constraints_file=constraints_file,
            index_url=index_url,
            trusted_host=trusted_host,
            allow_pip_download_cache=False,
        )

        failure_lines = collect_startup_hook_failure_lines(
            guard_script=guard_script,
            python_executable=staging_python,
        )
        if failure_lines:
            for line in failure_lines:
                print(line)
            return 1

    install_from_proxy(
        python_executable=python_executable,
        requirement_files=requirement_files,
        constraints_file=constraints_file,
        index_url=index_url,
        trusted_host=trusted_host,
        allow_pip_download_cache=docker_pip_layer_cache_enabled(),
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if args.requirements_profile and (args.install_dev or args.install_test):
            print(
                "ERROR: requirements-profile cannot be combined with "
                "--install-dev or --install-test."
            )
            return 1
        validated_constraints_file = validate_constraints_file(args.constraints_file)
        requirement_files = resolve_requirement_files(
            requirements_file=args.requirements_file,
            dev_requirements_file=args.dev_requirements_file,
            test_requirements_file=args.test_requirements_file,
            ci_lite_requirements_file=args.ci_lite_requirements_file,
            install_dev=args.install_dev,
            install_test=args.install_test,
            requirements_profile=args.requirements_profile,
        )

        if args.require_virtualenv and not is_virtualenv_python(args.python_executable):
            print("ERROR: refusing to install packages with a non-virtualenv interpreter.")
            print(f"Python executable: {args.python_executable}")
            return 1

        index_url, trusted_host = resolve_private_proxy_settings(
            index_url=args.index_url,
            trusted_host=args.trusted_host,
        )

        if args.upgrade_pip:
            upgrade_pip(
                args.python_executable,
                index_url=index_url,
                trusted_host=trusted_host,
            )

        if args.install_mode == "direct-proxy":
            return install_with_guard_from_proxy(
                python_executable=args.python_executable,
                requirement_files=requirement_files,
                constraints_file=validated_constraints_file,
                guard_script=args.guard_script,
                index_url=index_url,
                trusted_host=trusted_host,
            )

        if args.wheelhouse_dir is not None:
            return install_with_guard(
                python_executable=args.python_executable,
                requirement_files=requirement_files,
                constraints_file=validated_constraints_file,
                wheelhouse_dir=args.wheelhouse_dir,
                guard_script=args.guard_script,
                index_url=index_url,
                trusted_host=trusted_host,
            )

        with tempfile.TemporaryDirectory(prefix="pulseplate-wheelhouse-") as temp_dir:
            wheelhouse_dir = Path(temp_dir)
            return install_with_guard(
                python_executable=args.python_executable,
                requirement_files=requirement_files,
                constraints_file=validated_constraints_file,
                wheelhouse_dir=wheelhouse_dir,
                guard_script=args.guard_script,
                index_url=index_url,
                trusted_host=trusted_host,
            )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: locked install failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

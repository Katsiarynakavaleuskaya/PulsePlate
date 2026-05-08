#!/usr/bin/env python3
"""Check the production Docker image dependency surface.

RU: Проверяет, что production Docker image не содержит CI/dev tooling или
optional vector/ML packages.
EN: Verifies that the production Docker image excludes CI/dev tooling and
optional vector/ML packages.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
import subprocess  # nosec B404: subprocess is required for bounded local Docker inspection (remove-by: 2026-09-30, ref: PR-docker-runtime-slimming)
import sys

DOCKER_BINARY = shutil.which("docker")
DOCKER_TIMEOUT_SECONDS = 60
DEFAULT_BLOCKED_PREFIXES: tuple[str, ...] = (
    "bandit",
    "coverage",
    "cuda-",
    "diff-cover",
    "faker",
    "huggingface-hub",
    "hypothesis",
    "mypy",
    "nvidia-",
    "pgvector",
    "pip-audit",
    "pre-commit",
    "pytest",
    "pytest-",
    "ruff",
    "scikit-learn",
    "scipy",
    "sentence-transformers",
    "tokenizers",
    "torch",
    "transformers",
    "triton",
)


@dataclass(frozen=True)
class DependencySurfaceResult:
    """Normalized Docker runtime dependency-surface report."""

    image: str
    installed_count: int
    blocked: tuple[str, ...]
    passed: bool
    installed_debian_count: int = 0
    blocked_debian_packages: tuple[str, ...] = ()


def normalize_package_name(name: str) -> str:
    """Normalize package names to pip-comparison form."""

    return name.strip().lower().replace("_", "-")


def normalize_debian_package_name(name: str) -> str:
    """Normalize Debian package names and drop optional architecture qualifiers."""

    return normalize_package_name(name).split(":", 1)[0]


def parse_installed_packages(payload: str) -> tuple[str, ...]:
    """Parse the image-side JSON package inventory."""

    data = json.loads(payload)
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("Image package inventory must be a JSON list of strings.")
    return tuple(sorted({normalize_package_name(item) for item in data}))


def parse_installed_debian_packages(payload: str) -> dict[str, str]:
    """Parse the image-side dpkg package inventory."""

    installed: dict[str, str] = {}
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            status, name, version = line.split("\t", 2)
        except ValueError as exc:
            raise ValueError(
                "Debian package inventory must be '<status>\\t<name>\\t<version>' lines."
            ) from exc
        if not status.startswith("ii"):
            continue
        normalized = normalize_debian_package_name(name)
        if not normalized or not version.strip():
            raise ValueError("Debian package inventory contains an empty name or version.")
        installed[normalized] = version.strip()
    return dict(sorted(installed.items()))


def find_blocked_packages(
    installed_packages: tuple[str, ...], blocked_prefixes: tuple[str, ...]
) -> tuple[str, ...]:
    """Return installed packages matching blocked runtime prefixes."""

    normalized_prefixes = tuple(normalize_package_name(item) for item in blocked_prefixes)
    blocked = [package for package in installed_packages if package.startswith(normalized_prefixes)]
    return tuple(sorted(set(blocked)))


def find_blocked_debian_packages(
    installed_packages: dict[str, str], blocked_packages: tuple[str, ...]
) -> tuple[str, ...]:
    """Return exact Debian packages that must not exist in the production image."""

    normalized_blocked = {normalize_debian_package_name(item) for item in blocked_packages}
    blocked = [
        f"{name}={version}"
        for name, version in installed_packages.items()
        if name in normalized_blocked
    ]
    return tuple(sorted(blocked))


def _run_docker(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run Docker with a resolved binary path and fixed argv."""

    if DOCKER_BINARY is None:
        raise RuntimeError(
            "docker binary is not available on PATH; run this check in a Docker-enabled "
            "environment."
        )
    try:
        return subprocess.run(  # nosec B603: argv uses resolved docker path with fixed run subcommand only (remove-by: 2026-09-30, ref: PR-docker-runtime-slimming)
            [DOCKER_BINARY, *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"docker command timed out after {DOCKER_TIMEOUT_SECONDS}s: {' '.join(args)}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stderr_suffix = f", stderr={stderr}" if stderr else ""
        raise RuntimeError(
            "docker command failed "
            f"(returncode={exc.returncode}, args={' '.join(args)}{stderr_suffix})"
        ) from exc


def inspect_image_packages(image: str) -> tuple[str, ...]:
    """Inspect installed package names inside the target image."""

    snippet = (
        "import importlib.metadata as m, json; "
        "print(json.dumps(sorted(d.metadata['Name'] for d in m.distributions())))"
    )
    result = _run_docker(["run", "--rm", image, "python", "-c", snippet])
    return parse_installed_packages(result.stdout)


def inspect_image_debian_packages(image: str) -> dict[str, str]:
    """Inspect installed Debian package names and versions inside the target image."""

    snippet = "dpkg-query -W -f='${db:Status-Abbrev}\\t${Package}\\t${Version}\\n'"
    result = _run_docker(["run", "--rm", image, "sh", "-c", snippet])
    return parse_installed_debian_packages(result.stdout)


def build_result(
    image: str,
    blocked_prefixes: tuple[str, ...],
    blocked_debian_packages: tuple[str, ...] = (),
) -> DependencySurfaceResult:
    """Build the normalized dependency-surface result for an image."""

    installed = inspect_image_packages(image)
    blocked = find_blocked_packages(installed, blocked_prefixes)
    installed_debian = inspect_image_debian_packages(image) if blocked_debian_packages else {}
    blocked_debian = find_blocked_debian_packages(installed_debian, blocked_debian_packages)
    return DependencySurfaceResult(
        image=image,
        installed_count=len(installed),
        blocked=blocked,
        passed=not blocked and not blocked_debian,
        installed_debian_count=len(installed_debian),
        blocked_debian_packages=blocked_debian,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Docker image reference to inspect.")
    parser.add_argument(
        "--blocked-prefix",
        action="append",
        dest="blocked_prefixes",
        default=None,
        help="Additional blocked package prefix. May be passed multiple times.",
    )
    parser.add_argument(
        "--blocked-debian-package",
        action="append",
        dest="blocked_debian_packages",
        default=None,
        help="Exact Debian package name that must not exist in the production image. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path for writing the JSON result payload.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    args = parse_args(argv)
    extra_blocked_prefixes = tuple(args.blocked_prefixes or ())
    blocked_prefixes = DEFAULT_BLOCKED_PREFIXES + extra_blocked_prefixes
    blocked_debian_packages = tuple(args.blocked_debian_packages or ())
    result = build_result(args.image, blocked_prefixes, blocked_debian_packages)
    payload = json.dumps(asdict(result), indent=2)

    if args.output_json is not None:
        args.output_json.write_text(payload + "\n", encoding="utf-8")

    stream = sys.stdout if result.passed else sys.stderr
    print(payload, file=stream)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

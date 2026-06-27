#!/usr/bin/env python3
"""Install pinned requirements through a local wheelhouse and startup-hook guard."""

from __future__ import annotations

import argparse
import base64
import http.client
import hashlib
import netrc
import platform
from contextlib import contextmanager
from datetime import date
import json
import os
import re
import ssl
import subprocess  # nosec B404: subprocess is required for bounded pip/python invocations during locked installation (remove-by: 2026-07-31, ref: PR-litellm-hardening)
import sys
import sysconfig
import tempfile
import time
from pathlib import Path
from typing import Iterator, Sequence, cast
from urllib.parse import ParseResult, quote, urlparse
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUIREMENTS_FILE = REPO_ROOT / "requirements.txt"
DEFAULT_DEV_REQUIREMENTS_FILE = REPO_ROOT / "requirements-dev.txt"
DEFAULT_TEST_REQUIREMENTS_FILE = REPO_ROOT / "requirements-test.txt"
DEFAULT_CI_LITE_REQUIREMENTS_FILE = REPO_ROOT / "requirements-ci-lite.txt"
DEFAULT_RAG_VECTOR_REQUIREMENTS_FILE = REPO_ROOT / "requirements-rag-vector.txt"
DEFAULT_CONSTRAINTS_FILE = REPO_ROOT / "constraints.txt"
DEFAULT_STARTUP_HOOK_GUARD_PATH = REPO_ROOT / "scripts" / "ci" / "check_python_startup_hooks.py"
DEFAULT_EMERGENCY_WHEEL_MANIFEST = REPO_ROOT / "scripts" / "ci" / "emergency_python_wheels.json"

DEFAULT_DEPENDENCY_SECURITY_SCHEMA = (
    REPO_ROOT / "tests" / "fixtures" / "dependency_security_schema.json"
)
APPROVED_INDEX_ENV_VAR = "PULSEPLATE_PYTHON_INDEX_URL"
TRUSTED_HOST_ENV_VAR = "PULSEPLATE_PYTHON_TRUSTED_HOST"
EMERGENCY_WHEEL_MANIFEST_ENV_VAR = "PULSEPLATE_PYTHON_EMERGENCY_WHEEL_MANIFEST"
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
REQUIRED_HTTPS_INDEX_HOSTS: tuple[str, ...] = ("packages.pulseplate.app",)
ALLOWED_EMERGENCY_WHEEL_HOSTS: tuple[str, ...] = ("files.pythonhosted.org",)
INSTALL_MODES: tuple[str, ...] = ("wheelhouse", "direct-proxy")
REQUIREMENTS_PROFILES: tuple[str, ...] = (
    "runtime",
    "runtime-dev",
    "runtime-test",
    "ci-test",
    "ci-lite",
    "rag-vector",
)
PIP_NETWORK_RETRIES = 5
PIP_NETWORK_TIMEOUT_SECONDS = 60
PRIVATE_INDEX_PROJECT_PAGE_BYTES = 100_000
PRIVATE_INDEX_HEALTH_TIMEOUT_SECONDS = 15
PRIVATE_INDEX_HEALTH_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0)
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
        "--rag-vector-requirements-file",
        type=Path,
        default=DEFAULT_RAG_VECTOR_REQUIREMENTS_FILE,
        help="Pinned optional vector/ML requirements file used when requirements-profile is rag-vector.",
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
        "--upgrade-pip-spec",
        default="pip",
        help=(
            "Simple numeric pip requirement spec (no extras/markers/wildcards), e.g. "
            "'pip', 'pip==24.0', or 'pip>=23,<24', used with --upgrade-pip or "
            "--upgrade-pip-only. "
            "Docker uses this to keep a range in the Dockerfile while emergency fallback "
            "remains exact-artifact scoped."
        ),
    )
    parser.add_argument(
        "--upgrade-pip-only",
        action="store_true",
        help="Upgrade pip via the governed proxy/fallback path and exit without installing requirements.",
    )
    parser.add_argument(
        "--guard-script",
        type=Path,
        default=DEFAULT_STARTUP_HOOK_GUARD_PATH,
        help="Path to the startup-hook guard script used for static .pth scanning.",
    )
    parser.add_argument(
        "--emergency-wheel-manifest",
        type=Path,
        help=(
            "Optional JSON manifest for exact emergency wheel fallback. "
            f"Defaults to ${EMERGENCY_WHEEL_MANIFEST_ENV_VAR} or "
            f"{DEFAULT_EMERGENCY_WHEEL_MANIFEST} when present."
        ),
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

    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help=(
            "Validate min dependency floor versions against approved proxy/fallback and exit "
            "without installing any requirements."
        ),
    )
    return parser.parse_args(argv)


def resolve_requirement_files(
    *,
    requirements_file: Path,
    dev_requirements_file: Path,
    test_requirements_file: Path,
    ci_lite_requirements_file: Path,
    rag_vector_requirements_file: Path,
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
        "ci-test": [
            ("CI lite requirements file", ci_lite_requirements_file),
            ("CI test requirements file", test_requirements_file),
        ],
        "ci-lite": [("CI lite requirements file", ci_lite_requirements_file)],
        "rag-vector": [
            ("Requirements file", requirements_file),
            ("RAG vector requirements file", rag_vector_requirements_file),
        ],
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


def resolve_emergency_wheel_manifest_path(manifest_path: Path | None) -> Path | None:
    """Resolve the optional emergency wheel manifest from CLI/env/default path."""
    if manifest_path is not None:
        return manifest_path
    env_path = os.environ.get(EMERGENCY_WHEEL_MANIFEST_ENV_VAR, "").strip()
    if env_path:
        return Path(env_path)
    if DEFAULT_EMERGENCY_WHEEL_MANIFEST.exists():
        return DEFAULT_EMERGENCY_WHEEL_MANIFEST
    return None


def _parse_iso_date(value: str, *, field_name: str) -> date:
    """Parse YYYY-MM-DD date strings for time-boxed fallback manifests."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise RuntimeError(
            f"Emergency wheel manifest field {field_name!r} must use YYYY-MM-DD: {value!r}"
        )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Emergency wheel manifest field {field_name!r} must use YYYY-MM-DD: {value!r}"
        ) from exc


def _validate_sha256(value: str, *, filename: str) -> str:
    """Return a normalized sha256 digest or fail closed."""
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise RuntimeError(
            f"Emergency wheel manifest sha256 is invalid for {filename!r}: {value!r}"
        )
    return digest


def _normalize_artifact_sha256(artifact: dict[str, object], *, filename: str) -> str:
    """Return an emergency artifact digest from a direct string or split parts."""

    direct_digest = artifact.get("sha256")
    if isinstance(direct_digest, str) and direct_digest.strip():
        return _validate_sha256(direct_digest, filename=filename)
    digest_parts = artifact.get("sha256_parts")
    if (
        isinstance(digest_parts, list)
        and digest_parts
        and all(isinstance(part, str) and part.strip() for part in digest_parts)
    ):
        return _validate_sha256("".join(digest_parts), filename=filename)
    raise RuntimeError(
        "Emergency wheel artifacts require non-empty package/version/filename/url and "
        "either sha256 or sha256_parts."
    )


def load_emergency_wheel_manifest(manifest_path: Path | None) -> list[dict[str, str]]:
    """Load and validate an optional exact-wheel fallback manifest."""
    resolved_path = resolve_emergency_wheel_manifest_path(manifest_path)
    if resolved_path is None:
        return []
    if not resolved_path.exists():
        raise FileNotFoundError(f"Emergency wheel manifest not found: {resolved_path}")

    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Emergency wheel manifest is not valid JSON: {resolved_path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Emergency wheel manifest root must be a JSON object.")
    if payload.get("schema_version") != 1:
        raise RuntimeError("Emergency wheel manifest schema_version must equal 1.")

    expires_at = payload.get("expires_at")
    if not isinstance(expires_at, str) or not expires_at.strip():
        raise RuntimeError("Emergency wheel manifest must define non-empty expires_at.")
    default_expires_at = _parse_iso_date(expires_at, field_name="expires_at")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise RuntimeError("Emergency wheel manifest must define a non-empty artifacts list.")

    normalized_artifacts: list[dict[str, str]] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise RuntimeError(f"Emergency wheel artifact #{index} must be an object.")
        package = artifact.get("package")
        version = artifact.get("version")
        filename = artifact.get("filename")
        url = artifact.get("url")
        if not all(
            isinstance(value, str) and value.strip() for value in (package, version, filename, url)
        ):
            raise RuntimeError(
                "Emergency wheel artifacts require non-empty package/version/filename/url "
                "and either sha256 or sha256_parts."
            )
        package_text = cast(str, package).strip()
        version_text = cast(str, version).strip()
        filename_text = cast(str, filename).strip()
        url_text = cast(str, url).strip()
        sha256_text = _normalize_artifact_sha256(artifact, filename=filename_text)
        artifact_expires_at = artifact.get("expires_at")
        if artifact_expires_at is None:
            effective_expires_at = default_expires_at
        elif isinstance(artifact_expires_at, str) and artifact_expires_at.strip():
            effective_expires_at = _parse_iso_date(
                artifact_expires_at.strip(),
                field_name=f"artifacts[{index}].expires_at",
            )
        else:
            raise RuntimeError(
                f"Emergency wheel artifact #{index} expires_at must be a non-empty YYYY-MM-DD string."
            )
        if effective_expires_at < date.today():
            continue
        parsed_url = urlparse(url_text)
        hostname = (parsed_url.hostname or "").rstrip(".").lower()
        if parsed_url.scheme != "https" or hostname not in ALLOWED_EMERGENCY_WHEEL_HOSTS:
            raise RuntimeError(
                "Emergency wheel artifacts must use approved https hosts only: " f"{url_text!r}"
            )
        normalized_artifacts.append(
            {
                "package": package_text,
                "version": version_text,
                "filename": filename_text,
                "url": url_text,
                "sha256": _validate_sha256(sha256_text, filename=filename_text),
            }
        )
    if not normalized_artifacts:
        raise RuntimeError(
            "Emergency wheel manifest is expired; refresh the mirror or rotate the fallback: "
            f"{resolved_path}"
        )
    return normalized_artifacts


def _requirement_line_requests_exact_version(line: str, *, package: str, version: str) -> bool:
    """Return True when a requirements line pins package==version exactly."""
    stripped = line.split("#", 1)[0].strip().lower()
    if not stripped or stripped.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
        return False
    return stripped == f"{package.lower()}=={version.lower()}"


def _collect_exact_requirement_pins(lines: Sequence[str]) -> set[str]:
    """Return normalized exact-package pins from requirement-like lines."""
    exact_pins: set[str] = set()
    for line in lines:
        stripped = line.split("#", 1)[0].strip().lower()
        if not stripped or stripped.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
            continue
        if "==" not in stripped:
            continue
        exact_pins.add(stripped)
    return exact_pins


def _collect_unmarked_exact_requirement_pin_versions(
    lines: Sequence[str],
) -> dict[str, set[str]]:
    """Return package -> exact versions for unmarked requirement pins."""
    exact_versions: dict[str, set[str]] = {}
    for line in lines:
        stripped = line.split("#", 1)[0].strip().lower()
        if (
            not stripped
            or ";" in stripped
            or stripped.startswith(("-r ", "--requirement ", "-c ", "--constraint "))
        ):
            continue
        match = re.fullmatch(
            r"([a-z0-9][a-z0-9._-]*)(?:\[[^]]+\])?\s*==\s*([^,;\s]+)",
            stripped,
        )
        if match is None:
            continue
        package = re.sub(r"[-_.]+", "-", match.group(1))
        exact_versions.setdefault(package, set()).add(match.group(2))
    return exact_versions


def _constraint_line_repeats_exact_min_floor(
    line: str,
    *,
    exact_versions_by_package: dict[str, set[str]],
) -> bool:
    """Return True for package>=version constraints already enforced by package==version."""
    stripped = line.split("#", 1)[0].strip().lower()
    if (
        not stripped
        or ";" in stripped
        or stripped.startswith(("-r ", "--requirement ", "-c ", "--constraint "))
    ):
        return False
    match = re.fullmatch(
        r"([a-z0-9][a-z0-9._-]*)(?:\[[^]]+\])?\s*>=\s*([^,;\s]+)",
        stripped,
    )
    if match is None:
        return False
    package = re.sub(r"[-_.]+", "-", match.group(1))
    return match.group(2) in exact_versions_by_package.get(package, set())


def _requirement_line_package_name(line: str) -> str | None:
    """Return the normalized package name requested by a requirement-like line."""
    stripped = line.split("#", 1)[0].strip().lower()
    if not stripped or stripped.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
        return None
    match = re.match(r"([a-z0-9][a-z0-9._-]*)(?:\[[^]]+\])?\s*(?:===|==|~=|!=|<=|>=|<|>)", stripped)
    if match is None:
        return None
    return re.sub(r"[-_.]+", "-", match.group(1))


def _load_exact_requirement_pins(requirement_file: Path) -> set[str]:
    """Read one requirement surface once and collect exact pins."""
    return _collect_exact_requirement_pins(
        requirement_file.read_text(encoding="utf-8").splitlines()
    )


def requirement_files_request_artifact(
    requirement_files: Sequence[Path], *, package: str, version: str
) -> bool:
    """Return True when any selected requirements surface pins package==version."""
    expected_pin = f"{package.lower()}=={version.lower()}"
    for requirement_file in requirement_files:
        if expected_pin in _load_exact_requirement_pins(requirement_file):
            return True
    return False


def requirement_surfaces_request_artifact(
    requirement_files: Sequence[Path],
    *,
    constraints_file: Path | None,
    package: str,
    version: str,
) -> bool:
    """Return True when selected requirement surfaces or constraints pin package==version."""
    expected_pin = f"{package.lower()}=={version.lower()}"
    if requirement_files_request_artifact(
        requirement_files,
        package=package,
        version=version,
    ):
        return True

    validated_constraints_file = validate_constraints_file(constraints_file)
    if validated_constraints_file is None:
        return False
    return expected_pin in _load_exact_requirement_pins(validated_constraints_file)


def _wheel_filename_tags(filename: str) -> set[str] | None:
    """Return expanded wheel tags from a parseable wheel filename.

    Older tests use deliberately shortened fake wheel names. Returning None for
    those keeps legacy fixtures usable while production wheel filenames remain
    tag-filtered.
    """
    if not filename.endswith(".whl"):
        return None
    parts = filename[:-4].rsplit("-", 3)
    if len(parts) != 4:
        return None
    python_tag, abi_tag, platform_tag = parts[1:]
    if not python_tag or not abi_tag or not platform_tag:
        return None
    return {
        f"{python_part}-{abi_part}-{platform_part}"
        for python_part in python_tag.split(".")
        for abi_part in abi_tag.split(".")
        for platform_part in platform_tag.split(".")
        if python_part and abi_part and platform_part
    }


def _fallback_supported_wheel_tags_for_runtime(
    *,
    major: int,
    minor: int,
    implementation_name: str,
    platform_name: str,
    sysconfig_platform: str,
    machine_name: str,
) -> set[str]:
    """Return conservative stdlib-only wheel tags for one interpreter/platform."""
    if implementation_name == "cpython":
        current_python_tag = f"cp{major}{minor}"
        python_abi_tags = {f"{current_python_tag}-{current_python_tag}"}
        python_abi_tags.update(f"cp{major}{abi_minor}-abi3" for abi_minor in range(2, minor + 1))
    else:
        current_python_tag = f"py{major}"
        python_abi_tags = {f"{current_python_tag}-none"}

    platform_tags = {"any"}
    normalized_platform = sysconfig_platform.replace("-", "_").replace(".", "_")
    if normalized_platform:
        platform_tags.add(normalized_platform)

    machine = machine_name.lower().replace("-", "_")
    if machine in {"amd64", "x86_64"}:
        machine = "x86_64"
    elif machine in {"aarch64", "arm64"}:
        machine = "aarch64"

    if platform_name.startswith("linux") and machine:
        platform_tags.add(f"linux_{machine}")
        if machine == "x86_64":
            platform_tags.update(
                {"manylinux1_x86_64", "manylinux2010_x86_64", "manylinux2014_x86_64"}
            )
            platform_tags.update(
                f"manylinux_2_{glibc_minor}_x86_64" for glibc_minor in range(17, 40)
            )
    elif platform_name == "darwin":
        if "arm64" in normalized_platform:
            platform_tags.add("macosx_11_0_arm64")
            platform_tags.add("macosx_11_0_universal2")
        elif "x86_64" in normalized_platform:
            platform_tags.add("macosx_10_9_x86_64")
            platform_tags.add("macosx_10_9_universal2")
    elif platform_name.startswith("win"):
        platform_tags.add("win_amd64" if machine == "x86_64" else f"win_{machine}")

    supported_tags = {"py3-none-any", f"py{major}-none-any"}
    supported_tags.update(
        f"{python_abi_tag}-{platform_tag}"
        for python_abi_tag in python_abi_tags
        for platform_tag in platform_tags
    )
    return supported_tags


def _fallback_supported_wheel_tags() -> set[str]:
    """Return conservative stdlib-only wheel tags for the current interpreter."""
    return _fallback_supported_wheel_tags_for_runtime(
        major=sys.version_info.major,
        minor=sys.version_info.minor,
        implementation_name=sys.implementation.name,
        platform_name=sys.platform,
        sysconfig_platform=sysconfig.get_platform(),
        machine_name=platform.machine(),
    )


def _current_supported_wheel_tags() -> set[str]:
    """Return supported wheel tags without making packaging a hard dependency."""
    try:
        from packaging import tags as packaging_tags
    except Exception:  # noqa: BLE001 - installer must run before project deps are installed.
        return _fallback_supported_wheel_tags()
    return {str(tag) for tag in packaging_tags.sys_tags()}


def _path_qualified_python_executable_for_probe(python_executable: str) -> str:
    """Return a non-PATH-resolved Python executable for wheel-tag probing."""
    candidate = python_executable.strip()
    if not candidate:
        raise RuntimeError("Target Python executable for wheel-tag probe is empty")
    candidate_path = Path(candidate)
    if candidate_path.is_absolute():
        return candidate
    has_path_separator = os.sep in candidate or (os.altsep is not None and os.altsep in candidate)
    if has_path_separator:
        return str(candidate_path.resolve())
    current_interpreter_aliases = {
        "python",
        f"python{sys.version_info.major}",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        Path(sys.executable).name,
    }
    if candidate in current_interpreter_aliases:
        return sys.executable
    raise RuntimeError(
        "Target Python executable for wheel-tag probe must be absolute or "
        f"path-qualified; refusing to resolve through PATH: {python_executable}"
    )


def _target_python_wheel_tag_payload(python_executable: str) -> dict[str, object]:
    """Probe wheel-tag data from the requested target interpreter."""
    probe_python = _path_qualified_python_executable_for_probe(python_executable)
    probe = "\n".join(
        (
            "import json",
            "import platform",
            "import sys",
            "import sysconfig",
            "try:",
            "    from packaging import tags as packaging_tags",
            "except Exception:",
            "    wheel_tags = []",
            "else:",
            "    wheel_tags = [str(tag) for tag in packaging_tags.sys_tags()]",
            "print(json.dumps({",
            "    'tags': wheel_tags,",
            "    'major': sys.version_info.major,",
            "    'minor': sys.version_info.minor,",
            "    'implementation_name': sys.implementation.name,",
            "    'platform_name': sys.platform,",
            "    'sysconfig_platform': sysconfig.get_platform(),",
            "    'machine_name': platform.machine(),",
            "}))",
        )
    )
    result = subprocess.run(  # nosec B603: argv starts with the selected target Python interpreter and a fixed metadata probe (remove-by: 2026-07-31, ref: PR-2017)
        [probe_python, "-c", probe],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = _redact_url_credentials_in_text((result.stderr or result.stdout).strip())
        raise RuntimeError(f"Unable to probe supported wheel tags for {probe_python}: {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid wheel-tag probe output from {probe_python}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid wheel-tag probe payload from {probe_python}")
    return payload


def _target_wheel_tag_payload_int(
    payload: dict[str, object],
    key: str,
    *,
    python_executable: str,
) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise RuntimeError(f"Invalid wheel-tag probe payload from {python_executable}")
    return value


def _supported_wheel_tags_for_python(python_executable: str | None) -> set[str]:
    """Return wheel tags for the target interpreter, defaulting to the current process."""
    if python_executable is None or python_executable == sys.executable:
        return _current_supported_wheel_tags()

    payload = _target_python_wheel_tag_payload(python_executable)
    tags = payload.get("tags")
    if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags) and tags:
        return set(tags)
    try:
        return _fallback_supported_wheel_tags_for_runtime(
            major=_target_wheel_tag_payload_int(
                payload,
                "major",
                python_executable=python_executable,
            ),
            minor=_target_wheel_tag_payload_int(
                payload,
                "minor",
                python_executable=python_executable,
            ),
            implementation_name=str(payload["implementation_name"]),
            platform_name=str(payload["platform_name"]),
            sysconfig_platform=str(payload["sysconfig_platform"]),
            machine_name=str(payload["machine_name"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid wheel-tag probe payload from {python_executable}") from exc


def _emergency_artifact_matches_runtime(
    artifact: dict[str, str],
    *,
    supported_tags: set[str],
) -> bool:
    """Return True when an emergency wheel can be installed by this runtime."""
    wheel_tags = _wheel_filename_tags(artifact["filename"])
    if wheel_tags is None:
        return True
    return bool(wheel_tags & supported_tags)


def _filter_runtime_compatible_artifacts(
    artifacts: Sequence[dict[str, str]],
    *,
    python_executable: str | None = None,
) -> list[dict[str, str]]:
    """Drop incompatible wheels and collapse duplicate exact emergency artifacts."""
    compatible_artifacts: list[dict[str, str]] = []
    seen_artifact_digests_by_filename: dict[str, str] = {}
    supported_tags = _supported_wheel_tags_for_python(python_executable)
    for artifact in artifacts:
        if not _emergency_artifact_matches_runtime(artifact, supported_tags=supported_tags):
            continue
        filename = artifact["filename"]
        digest = _emergency_artifact_sha256(artifact)
        previous_digest = seen_artifact_digests_by_filename.get(filename)
        if previous_digest is None:
            seen_artifact_digests_by_filename[filename] = digest
            compatible_artifacts.append(artifact)
            continue
        if previous_digest != digest:
            raise RuntimeError(f"Conflicting emergency artifact digests for {filename}")
    return compatible_artifacts


def emergency_artifacts_requested_by_surfaces(
    *,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    manifest_path: Path | None,
    python_executable: str | None = None,
) -> list[dict[str, str]]:
    """Return active emergency artifacts requested by selected requirement surfaces."""
    requested_requirement_pins: set[str] = set()
    for requirement_file in requirement_files:
        requested_requirement_pins.update(_load_exact_requirement_pins(requirement_file))

    validated_constraints_file = validate_constraints_file(constraints_file)
    requested_constraint_pins = (
        _load_exact_requirement_pins(validated_constraints_file)
        if validated_constraints_file is not None
        else set()
    )

    requested_artifacts: list[dict[str, str]] = []
    for artifact in load_emergency_wheel_manifest(manifest_path):
        expected_pin = f"{artifact['package'].lower()}=={artifact['version'].lower()}"
        if (
            expected_pin not in requested_requirement_pins
            and expected_pin not in requested_constraint_pins
        ):
            continue
        requested_artifacts.append(artifact)
    return _filter_runtime_compatible_artifacts(
        requested_artifacts,
        python_executable=python_executable,
    )


def _download_with_sha256(*, url: str, destination: Path, expected_sha256: str) -> None:
    """Download an artifact and verify its sha256 before trusting it."""
    digest = hashlib.sha256()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_file_descriptor, temp_file_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_file_name)
    try:
        with os.fdopen(temp_file_descriptor, "wb") as file_handle:
            with urlopen(  # nosec B310: url host is allowlisted via load_emergency_wheel_manifest and payload is sha256-verified before use (remove-by: 2026-07-31, ref: PR-1378)
                url,
                timeout=60,
            ) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    file_handle.write(chunk)
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise RuntimeError(
                f"Emergency wheel sha256 mismatch for {destination.name}: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )
        temp_path.replace(destination)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _emergency_artifact_sha256(artifact: dict[str, str]) -> str:
    """Return the exact expected digest for an emergency artifact."""

    digest = artifact.get("sha256")
    if isinstance(digest, str) and digest.strip():
        return digest.strip()
    digest_parts = artifact.get("sha256_parts")
    if isinstance(digest_parts, list) and all(isinstance(part, str) for part in digest_parts):
        joined_digest = "".join(digest_parts).strip()
        if joined_digest:
            return joined_digest
    raise RuntimeError(f"Emergency artifact missing sha256 digest: {artifact.get('filename')}")


def stage_emergency_wheels(
    *,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    wheelhouse_dir: Path,
    manifest_path: Path | None,
    python_executable: str | None = None,
) -> list[Path]:
    """Download exact emergency wheels requested by the selected requirement files."""
    requested_artifacts = emergency_artifacts_requested_by_surfaces(
        requirement_files=requirement_files,
        constraints_file=constraints_file,
        manifest_path=manifest_path,
        python_executable=python_executable,
    )
    return _stage_emergency_artifacts(
        artifacts=requested_artifacts,
        wheelhouse_dir=wheelhouse_dir,
        python_executable=python_executable,
    )


def _stage_emergency_artifacts(
    *,
    artifacts: Sequence[dict[str, str]],
    wheelhouse_dir: Path,
    python_executable: str | None = None,
) -> list[Path]:
    """Download selected exact emergency artifacts into a wheelhouse."""
    staged_paths: list[Path] = []
    for artifact in _filter_runtime_compatible_artifacts(
        artifacts,
        python_executable=python_executable,
    ):
        wheelhouse_dir.mkdir(parents=True, exist_ok=True)
        destination = wheelhouse_dir / artifact["filename"]
        if destination.exists():
            existing_sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
            if existing_sha256 != _emergency_artifact_sha256(artifact):
                raise RuntimeError(f"Existing emergency wheel has unexpected sha256: {destination}")
        else:
            _download_with_sha256(
                url=artifact["url"],
                destination=destination,
                expected_sha256=_emergency_artifact_sha256(artifact),
            )
        staged_paths.append(destination)
    return staged_paths


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
        "--retries",
        str(PIP_NETWORK_RETRIES),
        "--timeout",
        str(PIP_NETWORK_TIMEOUT_SECONDS),
        "--only-binary",
        ":all:",
        "--find-links",
        str(wheelhouse_dir),
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
        "--no-deps",
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
    find_links_dir: Path | None = None,
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
        "--no-deps",
        "--retries",
        str(PIP_NETWORK_RETRIES),
        "--timeout",
        str(PIP_NETWORK_TIMEOUT_SECONDS),
        "--only-binary",
        ":all:",
        "--index-url",
        index_url,
        "--requirement",
        str(requirement_file),
    ]
    if find_links_dir is not None:
        command.extend(["--find-links", str(find_links_dir)])
    if not use_pip_cache:
        try:
            install_idx = command.index("install")
        except ValueError as exc:
            raise RuntimeError("pip proxy install command is missing the install verb") from exc
        command.insert(install_idx + 1, "--no-cache-dir")
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


@contextmanager
def effective_constraints_file_for_requirement(
    requirement_file: Path,
    constraints_file: Path | None,
) -> Iterator[Path | None]:
    """Yield constraints with duplicate exact pins removed for one requirement file."""
    validated_constraints_file = validate_constraints_file(constraints_file)
    if validated_constraints_file is None:
        yield None
        return

    requirement_lines = requirement_file.read_text(encoding="utf-8").splitlines()
    requirement_exact_pins = _collect_exact_requirement_pins(requirement_lines)
    exact_versions_by_package = _collect_unmarked_exact_requirement_pin_versions(requirement_lines)
    if not requirement_exact_pins:
        yield validated_constraints_file
        return

    constraint_lines = validated_constraints_file.read_text(encoding="utf-8").splitlines(
        keepends=True
    )
    filtered_constraint_lines = []
    removed_redundant_constraint = False
    for line in constraint_lines:
        normalized_line = line.split("#", 1)[0].strip().lower()
        if (normalized_line and normalized_line in requirement_exact_pins) or (
            _constraint_line_repeats_exact_min_floor(
                line,
                exact_versions_by_package=exact_versions_by_package,
            )
        ):
            removed_redundant_constraint = True
            continue
        filtered_constraint_lines.append(line)

    if not removed_redundant_constraint:
        yield validated_constraints_file
        return
    if not filtered_constraint_lines:
        yield None
        return

    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{validated_constraints_file.stem}.effective-",
        suffix=validated_constraints_file.suffix,
        dir=validated_constraints_file.parent,
    )
    effective_constraints_path = Path(temp_name)
    try:
        os.close(temp_fd)
        effective_constraints_path.write_text(
            "".join(filtered_constraint_lines),
            encoding="utf-8",
        )
        yield effective_constraints_path
    finally:
        effective_constraints_path.unlink(missing_ok=True)


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
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError(
            "Credentialed Python package proxy URLs are forbidden; use a clean "
            "index URL with .netrc-backed CI credentials."
        )
    if canonical_hostname in REQUIRED_HTTPS_INDEX_HOSTS and parsed.scheme != "https":
        raise RuntimeError(
            "Approved Python package proxy host must use https: " f"{canonical_hostname}"
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


def load_dependency_security_floors(
    schema_path: Path | None = None,
) -> dict[str, str]:
    """Load min dependency floors from canonical schema."""
    path = schema_path or DEFAULT_DEPENDENCY_SECURITY_SCHEMA
    if not path.exists():
        raise FileNotFoundError(f"Dependency security schema not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Dependency security schema is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Dependency security schema must be a JSON object: {path}")
    min_versions = payload.get("min_versions")
    if not isinstance(min_versions, dict) or not min_versions:
        raise RuntimeError(f"Dependency security schema must define non-empty min_versions: {path}")
    floors: dict[str, str] = {}
    for package, version in min_versions.items():
        if not isinstance(package, str) or not package.strip():
            raise RuntimeError(
                f"Dependency security schema contains invalid package name in {path}: {package!r}"
            )
        if not isinstance(version, str) or not version.strip():
            raise RuntimeError(
                f"Dependency security schema has invalid version for {package!r} in {path}"
            )
        floors[package.strip().lower()] = version.strip()
    return floors


def _resolver_miss_error(runtime_error: RuntimeError, *, package: str, version: str) -> bool:
    """Return True when pip failed because package floor is unavailable on index."""
    message = str(runtime_error)
    normalized_message = message.lower()
    requirement_text = f"{package}=={version}"
    package_name = package.lower()
    normalized_requirement = requirement_text.lower()

    def line_mentions_only_requested_package(line: str) -> bool:
        if normalized_requirement in line:
            return True
        if re.fullmatch(rf"\s*{re.escape(package_name)}\s*", line):
            return True
        return package_name in line and ("cannot install" in line or "the user requested" in line)

    network_diagnostics = "\n".join(
        line
        for line in normalized_message.splitlines()
        if not line_mentions_only_requested_package(line)
    )
    if _pip_upgrade_network_failure(network_diagnostics):
        return False
    resolver_markers = (
        f"No matching distribution found for {requirement_text}",
        f"Could not find a version that satisfies the requirement {requirement_text}",
    )
    if any(marker in message for marker in resolver_markers):
        return True

    pip26_no_candidate_markers = (
        f"cannot install {normalized_requirement} because these package versions have conflicting dependencies.",
        f"the user requested {normalized_requirement}",
        "no matching distributions available for your environment",
    )
    if not all(marker in normalized_message for marker in pip26_no_candidate_markers):
        return False

    missing_package_line = re.compile(rf"^\s*{re.escape(package_name)}\s*$", re.MULTILINE)
    return bool(missing_package_line.search(normalized_message))


def _pip_upgrade_resolver_miss(runtime_error: RuntimeError) -> bool:
    """Return True when pip failed because the pip spec is absent from the proxy."""
    message = str(runtime_error).lower()
    resolver_markers = (
        "no matching distribution found for pip",
        "could not find a version that satisfies the requirement pip",
    )
    return any(
        marker in message for marker in resolver_markers
    ) and not _pip_upgrade_network_failure(message)


def _pip_upgrade_network_failure(message: str) -> bool:
    """Return True when pip output includes transport/proxy failure markers."""
    network_markers = (
        "connection aborted",
        "connection error",
        "connection reset",
        "connection refused",
        "connect timeout",
        "cloudflare",
        "521",
        "error 5",
        "http 5",
        "max retries exceeded",
        "proxy error",
        "read timeout",
        "retrying",
        "server error",
        "ssl",
        "temporarily unavailable",
        "timed out",
        "tls",
    )
    return any(marker in message for marker in network_markers)


def _simple_project_url(index_url: str, package: str) -> str:
    """Return the approved index project URL used to prove proxy health before fallback."""
    normalized_package = re.sub(r"[-_.]+", "-", package).lower()
    base = index_url.rstrip("/") + "/"
    return f"{base}{quote(normalized_package, safe='')}/"


def _simple_project_page_looks_valid(*, package: str, body: bytes) -> bool:
    """Return True when a response body looks like a PEP 503 project page."""
    normalized_package = re.sub(r"[-_.]+", "-", package).lower()
    package_markers = (f"{normalized_package}-", f"{normalized_package.replace('-', '_')}-")
    text = body.decode("utf-8", errors="ignore").lower()
    return "href=" in text and any(marker in text for marker in package_markers)


def _simple_project_page_has_version(*, package: str, version: str, body: bytes) -> bool:
    """Return True when a PEP 503 project page advertises the exact package version."""
    normalized_package = re.sub(r"[-_.]+", "-", package).lower()
    text = body[:100_000].decode("utf-8", errors="ignore").lower()
    version_boundary = r"(?=(?:-|\.tar\.gz|\.zip|\.whl|[\"'#<]))"
    patterns = (
        rf"{re.escape(normalized_package)}-{re.escape(version)}{version_boundary}",
        rf"{re.escape(normalized_package.replace('-', '_'))}-{re.escape(version)}{version_boundary}",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _redact_url_credentials(url: str) -> str:
    """Remove inline credentials from a URL before including it in diagnostics."""
    parsed = urlparse(url)
    if parsed.hostname is None:
        return url
    netloc = parsed.hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def _redact_url_credentials_in_text(value: str) -> str:
    """Remove inline URL credentials from arbitrary diagnostic text."""
    return re.sub(
        r"\b(?P<scheme>https?://)(?P<userinfo>[^/\s?#]+@)(?P<host>[^@\s/?#]+)",
        lambda match: f"{match.group('scheme')}{match.group('host')}",
        value,
    )


def _netrc_basic_auth_header(hostname: str | None) -> str | None:
    """Return a Basic Auth header from the user's netrc for the package host."""
    if not hostname:
        return None
    try:
        credentials = netrc.netrc().authenticators(hostname)
    except FileNotFoundError:
        return None
    except (netrc.NetrcParseError, OSError) as exc:
        raise RuntimeError(f"Unable to read .netrc credentials for {hostname}: {exc}") from exc
    if credentials is None:
        return None
    login, _account, password = credentials
    if not login:
        return None
    if login.strip().lower() == "root":
        raise RuntimeError("Root devpi credentials are forbidden in .netrc.")
    encoded = f"{login}:{password or ''}".encode("utf-8")
    return "Basic " + base64.b64encode(encoded).decode("ascii")


def _trusted_host_matches_url(*, trusted_host: str | None, parsed_url: ParseResult) -> bool:
    """Return True when the operator trusted-host applies to the project URL host."""
    if not trusted_host:
        return False
    hostname = str(parsed_url.hostname or "").rstrip(".").lower()
    if not hostname:
        return False
    trusted = trusted_host.strip().rstrip(".").lower()
    host_with_port = hostname if parsed_url.port is None else f"{hostname}:{parsed_url.port}"
    return trusted in {hostname, host_with_port}


def _read_private_index_project_page(
    *,
    index_url: str,
    package: str,
    trusted_host: str | None,
) -> tuple[str, bytes]:
    """Return the approved proxy simple-index project page or fail closed."""
    project_url = _simple_project_url(index_url, package)
    safe_url = _redact_url_credentials(project_url)
    parsed = urlparse(project_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError(
            "Approved Python package proxy health check requires an http(s) project URL: "
            f"{package}: {safe_url}"
        )
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError(
            "Credentialed Python package proxy health check URLs are forbidden: "
            f"{package}: {safe_url}"
        )
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    headers: dict[str, str] = {}
    if parsed.scheme == "https":
        netrc_header = _netrc_basic_auth_header(parsed.hostname)
        if netrc_header:
            headers["Authorization"] = netrc_header
    status: int
    body: bytes
    for attempt in range(1, PIP_NETWORK_RETRIES + 1):
        if parsed.scheme == "http":
            conn = http.client.HTTPConnection(
                parsed.hostname,
                port=parsed.port,
                timeout=PRIVATE_INDEX_HEALTH_TIMEOUT_SECONDS,
            )
        elif _trusted_host_matches_url(trusted_host=trusted_host, parsed_url=parsed):
            # fmt: off
            trusted_context = ssl._create_unverified_context()  # nosec B323: mirrors explicit operator `--trusted-host` semantics for this health probe only (remove-by: 2026-06-30, ref: PR-1738)
            # fmt: on
            conn = http.client.HTTPSConnection(
                parsed.hostname,
                port=parsed.port,
                timeout=PRIVATE_INDEX_HEALTH_TIMEOUT_SECONDS,
                context=trusted_context,
            )
        else:
            conn = http.client.HTTPSConnection(
                parsed.hostname,
                port=parsed.port,
                timeout=PRIVATE_INDEX_HEALTH_TIMEOUT_SECONDS,
            )
        try:
            conn.request("GET", path, headers=headers)
            response = conn.getresponse()
            status = response.status
            body = response.read(PRIVATE_INDEX_PROJECT_PAGE_BYTES)
            if status >= 500 and attempt < PIP_NETWORK_RETRIES:
                _sleep_before_private_index_retry(attempt)
                continue
            break
        except Exception as exc:  # noqa: BLE001 - any probe failure must keep fallback fail-closed.
            if attempt == PIP_NETWORK_RETRIES:
                raise RuntimeError(
                    "Approved Python package proxy health check failed before emergency fallback: "
                    f"{package}: {safe_url}: {exc}"
                ) from exc
            _sleep_before_private_index_retry(attempt)
        finally:
            conn.close()
    else:  # pragma: no cover - range is non-empty while PIP_NETWORK_RETRIES is positive.
        raise RuntimeError(
            "Approved Python package proxy health check failed before emergency fallback: "
            f"{package}: {safe_url}: retry budget exhausted"
        )
    if status < 200 or status >= 300:
        raise RuntimeError(
            "Approved Python package proxy health check failed before emergency fallback: "
            f"{package}: {safe_url}: HTTP {status}"
        )
    return safe_url, body


def _sleep_before_private_index_retry(attempt: int) -> None:
    """Sleep briefly before retrying an approved-proxy health probe."""
    index = max(0, min(attempt - 1, len(PRIVATE_INDEX_HEALTH_RETRY_BACKOFF_SECONDS) - 1))
    time.sleep(PRIVATE_INDEX_HEALTH_RETRY_BACKOFF_SECONDS[index])


def _require_private_index_project_health(
    *,
    index_url: str,
    package: str,
    trusted_host: str | None,
) -> None:
    """Fail closed unless the approved proxy serves the package project page."""
    safe_url, body = _read_private_index_project_page(
        index_url=index_url,
        package=package,
        trusted_host=trusted_host,
    )
    if not _simple_project_page_looks_valid(package=package, body=body):
        raise RuntimeError(
            "Approved Python package proxy health check failed before emergency fallback: "
            f"{package}: {safe_url}: invalid simple-index project page"
        )


def _private_index_project_has_version(
    *,
    index_url: str,
    package: str,
    version: str,
    trusted_host: str | None,
) -> bool:
    """Return True when the approved proxy advertises the exact package version."""
    safe_url, body = _read_private_index_project_page(
        index_url=index_url,
        package=package,
        trusted_host=trusted_host,
    )
    if not _simple_project_page_looks_valid(package=package, body=body):
        raise RuntimeError(
            "Approved Python package proxy health check failed before dependency floor preflight: "
            f"{package}: {safe_url}: invalid simple-index project page"
        )
    return _simple_project_page_has_version(package=package, version=version, body=body)


def _parse_simple_version(value: str) -> tuple[int, ...]:
    """Parse the numeric version shape used by emergency pip bootstrap wheels."""
    if re.fullmatch(r"\d+(?:\.\d+)*", value) is None:
        raise RuntimeError(f"Unsupported emergency pip version format: {value!r}")
    return tuple(int(part) for part in value.split("."))


def _compare_versions(left: str, right: str) -> int:
    left_parts = list(_parse_simple_version(left))
    right_parts = list(_parse_simple_version(right))
    width = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (width - len(left_parts)))
    right_parts.extend([0] * (width - len(right_parts)))
    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0


def _pip_spec_allows_version(pip_spec: str, version: str) -> bool:
    """Return True when a narrow pip requirement spec permits an emergency artifact."""
    normalized_spec = pip_spec.strip().lower()
    package_match = re.match(r"^pip\s*(.*)$", normalized_spec)
    if package_match is None:
        raise RuntimeError(f"pip upgrade spec must target pip: {pip_spec!r}")
    constraints = package_match.group(1).strip()
    if not constraints:
        return True

    for raw_constraint in constraints.split(","):
        constraint = raw_constraint.strip()
        match = re.fullmatch(r"(==|>=|<=|>|<)\s*(\d+(?:\.\d+)*)", constraint)
        if match is None:
            raise RuntimeError(
                f"Unsupported pip upgrade spec constraint {constraint!r} in {pip_spec!r}"
            )
        operator, expected_version = match.groups()
        comparison = _compare_versions(version, expected_version)
        if operator == "==" and comparison != 0:
            return False
        if operator == ">=" and comparison < 0:
            return False
        if operator == "<=" and comparison > 0:
            return False
        if operator == ">" and comparison <= 0:
            return False
        if operator == "<" and comparison >= 0:
            return False
    return True


def _select_pip_emergency_artifact(
    *,
    manifest_path: Path | None,
    pip_spec: str,
    python_executable: str | None = None,
) -> dict[str, str]:
    """Select the highest active emergency pip artifact allowed by the Docker range."""
    candidates = [
        artifact
        for artifact in load_emergency_wheel_manifest(manifest_path)
        if artifact["package"].lower() == "pip"
        and _pip_spec_allows_version(pip_spec, artifact["version"])
    ]
    candidates = _filter_runtime_compatible_artifacts(
        candidates,
        python_executable=python_executable,
    )
    if not candidates:
        raise RuntimeError(f"No active emergency pip artifact satisfies upgrade spec {pip_spec!r}.")
    return max(candidates, key=lambda artifact: _parse_simple_version(artifact["version"]))


def _stage_pip_upgrade_emergency_wheel(
    *,
    wheelhouse_dir: Path,
    manifest_path: Path | None,
    pip_spec: str,
    python_executable: str | None = None,
) -> Path:
    """Download the exact emergency pip wheel selected for the upgrade range."""
    artifact = _select_pip_emergency_artifact(
        manifest_path=manifest_path,
        pip_spec=pip_spec,
        python_executable=python_executable,
    )
    destination = wheelhouse_dir / artifact["filename"]
    if destination.exists():
        existing_sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
        if existing_sha256 != _emergency_artifact_sha256(artifact):
            raise RuntimeError(f"Existing emergency pip wheel has unexpected sha256: {destination}")
    else:
        _download_with_sha256(
            url=artifact["url"],
            destination=destination,
            expected_sha256=_emergency_artifact_sha256(artifact),
        )
    return destination


def verify_emergency_artifact_for_floor(
    *,
    manifest_path: Path | None,
    package: str,
    version: str,
    python_executable: str | None = None,
) -> bool:
    """Return True when exact emergency fallback artifact exists and verifies."""
    artifacts = [
        artifact
        for artifact in load_emergency_wheel_manifest(manifest_path)
        if artifact["package"].lower() == package.lower() and artifact["version"] == version
    ]
    artifacts = _filter_runtime_compatible_artifacts(
        artifacts,
        python_executable=python_executable,
    )
    if not artifacts:
        return False
    with tempfile.TemporaryDirectory(prefix="pulseplate-floor-emergency-") as temp_dir:
        for artifact in artifacts:
            destination = Path(temp_dir) / artifact["filename"]
            _download_with_sha256(
                url=artifact["url"],
                destination=destination,
                expected_sha256=_emergency_artifact_sha256(artifact),
            )
    return True


def run_dependency_floor_preflight(
    *,
    python_executable: str,
    index_url: str,
    trusted_host: str | None,
    emergency_wheel_manifest: Path | None,
) -> None:
    """Fail fast when dependency floors are unavailable through the approved proxy."""
    floors = load_dependency_security_floors()
    for package, version in sorted(floors.items()):
        proxy_error: RuntimeError | None = None
        try:
            if _private_index_project_has_version(
                index_url=index_url,
                package=package,
                version=version,
                trusted_host=trusted_host,
            ):
                continue
        except RuntimeError as exc:
            proxy_error = exc
        if verify_emergency_artifact_for_floor(
            manifest_path=emergency_wheel_manifest,
            package=package,
            version=version,
            python_executable=python_executable,
        ):
            if proxy_error is None:
                print(
                    "WARNING: floor preflight proxy miss tolerated via emergency fallback: "
                    f"{package}=={version}"
                )
            else:
                print(
                    "WARNING: floor preflight proxy probe failure tolerated via exact "
                    f"emergency fallback: {package}=={version}: {proxy_error}"
                )
            continue
        if proxy_error is not None:
            raise RuntimeError(
                "Dependency floor preflight failed for approved proxy: "
                f"{package}=={version}: {proxy_error}"
            ) from proxy_error
        raise RuntimeError(
            "Dependency floor preflight failed for approved proxy: "
            f"{package}=={version}: exact version is not advertised by approved proxy"
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
    """Run a subprocess command; include captured stdout/stderr on failure for pip diagnostics."""
    command_text = " ".join(_redact_url_credentials_in_text(str(part)) for part in command)
    try:
        result = subprocess.run(  # nosec B603: commands are built internally from pinned requirement/install helpers only (remove-by: 2026-07-31, ref: PR-litellm-hardening)
            list(command),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        detail = _redact_url_credentials_in_text(str(exc))
        raise RuntimeError(f"Command failed: {command_text}: {detail}") from exc
    if result.returncode != 0:
        parts: list[str] = [f"exit {result.returncode}"]
        stderr = _redact_url_credentials_in_text(result.stderr or "").strip()
        stdout = _redact_url_credentials_in_text(result.stdout or "").strip()
        if stderr:
            parts.append(stderr)
        if stdout:
            parts.append(stdout)
        detail = "\n".join(parts)
        raise RuntimeError(f"Command failed: {command_text}: {detail}")


def upgrade_pip(
    python_executable: str,
    *,
    pip_spec: str,
    index_url: str,
    trusted_host: str | None,
    emergency_wheel_manifest: Path | None,
) -> None:
    use_pip_cache = docker_pip_layer_cache_enabled()
    command = [
        python_executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--retries",
        str(PIP_NETWORK_RETRIES),
        "--timeout",
        str(PIP_NETWORK_TIMEOUT_SECONDS),
        "--only-binary",
        ":all:",
        "--index-url",
        index_url,
        pip_spec,
    ]
    if not use_pip_cache:
        command.insert(command.index("install") + 1, "--no-cache-dir")
    if trusted_host:
        command.extend(["--trusted-host", trusted_host])
    try:
        run_command(command)
        return
    except RuntimeError as exc:
        if not _pip_upgrade_resolver_miss(exc):
            raise
        _require_private_index_project_health(
            index_url=index_url,
            package="pip",
            trusted_host=trusted_host,
        )

    with tempfile.TemporaryDirectory(prefix="pulseplate-pip-emergency-wheelhouse-") as temp_dir:
        wheelhouse_dir = Path(temp_dir)
        _stage_pip_upgrade_emergency_wheel(
            wheelhouse_dir=wheelhouse_dir,
            manifest_path=emergency_wheel_manifest,
            pip_spec=pip_spec,
            python_executable=python_executable,
        )
        fallback_command = [
            python_executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--no-index",
            "--find-links",
            str(wheelhouse_dir),
            pip_spec,
        ]
        if not use_pip_cache:
            fallback_command.insert(fallback_command.index("install") + 1, "--no-cache-dir")
        run_command(fallback_command)


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
        with effective_constraints_file_for_requirement(
            requirement_file,
            constraints_file,
        ) as effective_constraints_file:
            run_command(
                build_pip_install_command(
                    python_executable=python_executable,
                    requirement_file=requirement_file,
                    wheelhouse_dir=wheelhouse_dir,
                    constraints_file=effective_constraints_file,
                )
            )


def install_from_proxy(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    index_url: str,
    trusted_host: str | None,
    find_links_dir: Path | None = None,
    allow_pip_download_cache: bool | None = None,
) -> None:
    for requirement_file in requirement_files:
        with effective_constraints_file_for_requirement(
            requirement_file,
            constraints_file,
        ) as effective_constraints_file:
            run_command(
                build_pip_proxy_install_command(
                    python_executable=python_executable,
                    requirement_file=requirement_file,
                    constraints_file=effective_constraints_file,
                    index_url=index_url,
                    trusted_host=trusted_host,
                    find_links_dir=find_links_dir,
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
        with effective_constraints_file_for_requirement(
            requirement_file,
            constraints_file,
        ) as effective_constraints_file:
            run_command(
                build_pip_download_command(
                    python_executable=python_executable,
                    requirement_file=requirement_file,
                    wheelhouse_dir=wheelhouse_dir,
                    constraints_file=effective_constraints_file,
                    index_url=index_url,
                    trusted_host=trusted_host,
                )
            )


def _artifacts_with_resolver_miss(
    exc: RuntimeError,
    *,
    requested_artifacts: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    """Return requested emergency artifacts named by the resolver miss output."""
    return [
        artifact
        for artifact in requested_artifacts
        if _resolver_miss_error(
            exc,
            package=artifact["package"],
            version=artifact["version"],
        )
    ]


def _emergency_artifact_key(artifact: dict[str, str]) -> tuple[str, str]:
    """Return a stable key for already-staged emergency artifacts."""
    return (artifact["package"].lower(), artifact["version"].lower())


def build_wheelhouse_with_emergency_fallback(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    wheelhouse_dir: Path,
    index_url: str,
    trusted_host: str | None,
    emergency_wheel_manifest: Path | None,
) -> None:
    """Retry wheelhouse build with staged emergency wheels only after proxy failure."""
    requested_artifacts: list[dict[str, str]] | None = None
    staged_artifact_keys: set[tuple[str, str]] = set()
    while True:
        try:
            build_wheelhouse(
                python_executable=python_executable,
                requirement_files=requirement_files,
                constraints_file=constraints_file,
                wheelhouse_dir=wheelhouse_dir,
                index_url=index_url,
                trusted_host=trusted_host,
            )
            return
        except RuntimeError as exc:
            if requested_artifacts is None:
                requested_artifacts = emergency_artifacts_requested_by_surfaces(
                    requirement_files=requirement_files,
                    constraints_file=constraints_file,
                    manifest_path=emergency_wheel_manifest,
                    python_executable=python_executable,
                )
            remaining_artifacts = [
                artifact
                for artifact in requested_artifacts
                if _emergency_artifact_key(artifact) not in staged_artifact_keys
            ]
            resolver_miss_artifacts = _artifacts_with_resolver_miss(
                exc,
                requested_artifacts=remaining_artifacts,
            )
            if not resolver_miss_artifacts:
                raise
            for artifact in resolver_miss_artifacts:
                _require_private_index_project_health(
                    index_url=index_url,
                    package=artifact["package"],
                    trusted_host=trusted_host,
                )
            staged_wheels = _stage_emergency_artifacts(
                artifacts=resolver_miss_artifacts,
                wheelhouse_dir=wheelhouse_dir,
                python_executable=python_executable,
            )
            if not staged_wheels:
                raise
            staged_artifact_keys.update(
                _emergency_artifact_key(artifact) for artifact in resolver_miss_artifacts
            )


def install_from_proxy_with_emergency_fallback(
    *,
    python_executable: str,
    requirement_files: Sequence[Path],
    constraints_file: Path | None,
    index_url: str,
    trusted_host: str | None,
    emergency_wheelhouse_dir: Path,
    emergency_wheel_manifest: Path | None,
    allow_pip_download_cache: bool | None = None,
) -> None:
    """Retry proxy install with local emergency wheels only after the proxy fails."""
    requested_artifacts: list[dict[str, str]] | None = None
    staged_artifact_keys: set[tuple[str, str]] = set()
    while True:
        try:
            install_from_proxy(
                python_executable=python_executable,
                requirement_files=requirement_files,
                constraints_file=constraints_file,
                index_url=index_url,
                trusted_host=trusted_host,
                find_links_dir=emergency_wheelhouse_dir if staged_artifact_keys else None,
                allow_pip_download_cache=allow_pip_download_cache,
            )
            return
        except RuntimeError as exc:
            if requested_artifacts is None:
                requested_artifacts = emergency_artifacts_requested_by_surfaces(
                    requirement_files=requirement_files,
                    constraints_file=constraints_file,
                    manifest_path=emergency_wheel_manifest,
                    python_executable=python_executable,
                )
            remaining_artifacts = [
                artifact
                for artifact in requested_artifacts
                if _emergency_artifact_key(artifact) not in staged_artifact_keys
            ]
            resolver_miss_artifacts = _artifacts_with_resolver_miss(
                exc,
                requested_artifacts=remaining_artifacts,
            )
            if not resolver_miss_artifacts:
                raise
            for artifact in resolver_miss_artifacts:
                _require_private_index_project_health(
                    index_url=index_url,
                    package=artifact["package"],
                    trusted_host=trusted_host,
                )
            staged_wheels = _stage_emergency_artifacts(
                artifacts=resolver_miss_artifacts,
                wheelhouse_dir=emergency_wheelhouse_dir,
                python_executable=python_executable,
            )
            if not staged_wheels:
                raise
            staged_artifact_keys.update(
                _emergency_artifact_key(artifact) for artifact in resolver_miss_artifacts
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
    emergency_wheel_manifest: Path | None,
) -> int:
    build_wheelhouse_with_emergency_fallback(
        python_executable=python_executable,
        requirement_files=requirement_files,
        constraints_file=constraints_file,
        wheelhouse_dir=wheelhouse_dir,
        index_url=index_url,
        trusted_host=trusted_host,
        emergency_wheel_manifest=emergency_wheel_manifest,
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
    emergency_wheel_manifest: Path | None,
) -> int:
    with tempfile.TemporaryDirectory(prefix="pulseplate-emergency-wheelhouse-") as temp_dir:
        emergency_wheelhouse_dir = Path(temp_dir)

        if docker_single_pass_locked_install_enabled():
            if len(requirement_files) != 1:
                print(
                    "ERROR: Docker single-pass locked install requires exactly one requirements file "
                    f"(got {len(requirement_files)}). Combine manifests or disable "
                    f"{DOCKER_SINGLE_PASS_LOCKED_INSTALL_ENV}.",
                    file=sys.stderr,
                )
                return 1
            allow_cache = docker_pip_layer_cache_enabled()
            install_from_proxy_with_emergency_fallback(
                python_executable=python_executable,
                requirement_files=requirement_files,
                constraints_file=constraints_file,
                index_url=index_url,
                trusted_host=trusted_host,
                emergency_wheelhouse_dir=emergency_wheelhouse_dir,
                emergency_wheel_manifest=emergency_wheel_manifest,
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
            install_from_proxy_with_emergency_fallback(
                python_executable=staging_python,
                requirement_files=requirement_files,
                constraints_file=constraints_file,
                index_url=index_url,
                trusted_host=trusted_host,
                emergency_wheelhouse_dir=emergency_wheelhouse_dir,
                emergency_wheel_manifest=emergency_wheel_manifest,
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

        install_from_proxy_with_emergency_fallback(
            python_executable=python_executable,
            requirement_files=requirement_files,
            constraints_file=constraints_file,
            index_url=index_url,
            trusted_host=trusted_host,
            emergency_wheelhouse_dir=emergency_wheelhouse_dir,
            emergency_wheel_manifest=emergency_wheel_manifest,
            allow_pip_download_cache=docker_pip_layer_cache_enabled(),
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
        if args.requirements_profile and (args.install_dev or args.install_test):
            print(
                "ERROR: requirements-profile cannot be combined with "
                "--install-dev or --install-test."
            )
            return 1

        index_url, trusted_host = resolve_private_proxy_settings(
            index_url=args.index_url,
            trusted_host=args.trusted_host,
        )

        if args.require_virtualenv and not is_virtualenv_python(args.python_executable):
            print("ERROR: refusing to install packages with a non-virtualenv interpreter.")
            print(f"Python executable: {args.python_executable}")
            return 1

        if args.upgrade_pip or args.upgrade_pip_only:
            upgrade_pip(
                args.python_executable,
                pip_spec=args.upgrade_pip_spec,
                index_url=index_url,
                trusted_host=trusted_host,
                emergency_wheel_manifest=args.emergency_wheel_manifest,
            )
        if args.upgrade_pip_only:
            return 0

        if args.preflight_only:
            run_dependency_floor_preflight(
                python_executable=args.python_executable,
                index_url=index_url,
                trusted_host=trusted_host,
                emergency_wheel_manifest=args.emergency_wheel_manifest,
            )
            return 0

        validated_constraints_file = validate_constraints_file(args.constraints_file)
        requirement_files = resolve_requirement_files(
            requirements_file=args.requirements_file,
            dev_requirements_file=args.dev_requirements_file,
            test_requirements_file=args.test_requirements_file,
            ci_lite_requirements_file=args.ci_lite_requirements_file,
            rag_vector_requirements_file=args.rag_vector_requirements_file,
            install_dev=args.install_dev,
            install_test=args.install_test,
            requirements_profile=args.requirements_profile,
        )

        if args.install_mode == "direct-proxy":
            return install_with_guard_from_proxy(
                python_executable=args.python_executable,
                requirement_files=requirement_files,
                constraints_file=validated_constraints_file,
                guard_script=args.guard_script,
                index_url=index_url,
                trusted_host=trusted_host,
                emergency_wheel_manifest=args.emergency_wheel_manifest,
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
                emergency_wheel_manifest=args.emergency_wheel_manifest,
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
                emergency_wheel_manifest=args.emergency_wheel_manifest,
            )
    except (FileNotFoundError, RuntimeError) as exc:
        print("ERROR: locked install failed: " f"{_redact_url_credentials_in_text(str(exc))}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compile registry-owned Python locks through the approved private proxy.

This module is the implementation behind ``make requirements-locks``.  It is
not a second dependency-surface registry: profile, source, and output ownership
come from ``check_python_dependency_surfaces.py``.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
import fcntl
import hashlib
import hmac
from importlib import metadata as importlib_metadata
import netrc
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import stat
import struct
import subprocess  # nosec B404: argv-only governed pip-tools invocation (remove-by: 2027-01-31, ref: PR-2142)
import sys
import tempfile
from typing import Iterator, Mapping, Sequence
from urllib.parse import urlparse
import zipfile

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import InvalidWheelFilename, canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_private_python_proxy_health import (  # noqa: E402
    basic_auth_from_netrc,
    fetch_project_page,
    normalize_project_name,
    project_page_url,
    redact_text,
    trusted_exact_pin_wheel_hashes,
    validate_index_url,
)
from scripts.ci.check_python_dependency_surfaces import (  # noqa: E402
    DependencySurface,
    FORBIDDEN_LOCK_TOKENS,
    _requirement_package_names,
    compiled_dependency_surfaces,
    render_governed_lock_header,
    validate_compile_registry,
)
from scripts.ci.install_locked_python_requirements import (  # noqa: E402
    APPROVED_INDEX_ENV_VAR,
    resolve_private_proxy_settings,
)

MAKE_AUTHORITY_ENV = "PULSEPLATE_LOCK_COMPILE_VIA_MAKE"
PROFILE_SELECTION_ENV = "PULSEPLATE_LOCK_PROFILES_RAW"
UPGRADE_SELECTION_ENV = "PULSEPLATE_LOCK_UPGRADES_RAW"
GRAPH_CHANGE_SELECTION_ENV = "PULSEPLATE_LOCK_GRAPH_CHANGES_RAW"
COMPILE_TIMEOUT_SECONDS = 300
DOWNLOAD_TIMEOUT_SECONDS = 300
ARTIFACT_ADMISSION_TIMEOUT_SECONDS = 60.0
ARTIFACT_ADMISSION_MAX_BYTES = 16 * 1024 * 1024
ARTIFACT_ADMISSION_MAX_WORKERS = 4
ARTIFACT_ADMISSION_ATTEMPTS = 2
MAX_WHEEL_METADATA_BYTES = 2 * 1024 * 1024
MAX_WHEEL_MEMBERS = 100_000
MAX_WHEEL_CENTRAL_DIRECTORY_BYTES = 32 * 1024 * 1024
ZIP_END_OF_CENTRAL_DIRECTORY_SIZE = 22
ZIP_MAX_COMMENT_BYTES = 65_535
ZIP_END_OF_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x05\x06"
PROFILE_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXACT_UPGRADE_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==" r"(?P<version>[A-Za-z0-9][A-Za-z0-9._+!~-]*)$"
)
AMBIENT_RESOLVER_ENV_VARS = (
    "ALL_PROXY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NETRC",
    "NO_PROXY",
    "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL",
    "PIP_CONFIG_FILE",
    "PIP_FIND_LINKS",
    "PIP_NO_INDEX",
    "PIP_TRUSTED_HOST",
    "PIP_CERT",
    "PIP_CLIENT_CERT",
    "PIP_CONSTRAINT",
    "PIP_REQUIREMENT",
    "PIP_BUILD_CONSTRAINT",
    "PIP_ONLY_BINARY",
    "PIP_NO_BINARY",
    "PIP_PREFER_BINARY",
    "PIP_NO_CACHE_DIR",
    "PIP_KEYRING_PROVIDER",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "UV_INDEX",
    "UV_INDEX_URL",
    "UV_DEFAULT_INDEX",
    "UV_EXTRA_INDEX_URL",
    "UV_FIND_LINKS",
    "UV_NO_INDEX",
    "UV_INSECURE_HOST",
    "all_proxy",
    "http_proxy",
    "https_proxy",
    "no_proxy",
)
PASSTHROUGH_ENV_VARS = (
    "HOME",
    "PATH",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "VIRTUAL_ENV",
)


@dataclass(frozen=True)
class ExactPin:
    """Normalized exact requirement metadata used by the semantic delta gate."""

    version: str
    extras: tuple[str, ...]
    marker: str | None
    url: str | None


@dataclass(frozen=True)
class FileSnapshot:
    """Content and filesystem identity captured before resolver work."""

    digest: str
    mode: int
    device: int
    inode: int
    owner_uid: int
    size: int


@dataclass(frozen=True)
class FileCapture:
    """Bytes paired with the exact filesystem identity used to read them."""

    content: bytes
    snapshot: FileSnapshot


@dataclass(frozen=True)
class LockInputPlan:
    """Descriptor-bound lock inputs and the exact artifacts they require."""

    surface: DependencySurface
    output_path: Path
    output_capture: FileCapture
    source_captures: tuple[tuple[Path, FileCapture], ...]
    expected_artifacts: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class ValidatedWheel:
    """One statically validated wheel bound to immutable filesystem identity."""

    path: Path
    artifact_key: tuple[str, str]
    snapshot: FileSnapshot


@dataclass(frozen=True)
class ProfileWheelhouse:
    """A profile-narrow wheel view and its validated regular files."""

    path: Path
    artifacts: tuple[ValidatedWheel, ...]


@dataclass(frozen=True)
class PreparedLock:
    """A fully validated same-directory lock candidate awaiting replacement."""

    surface: DependencySurface
    output_path: Path
    candidate_path: Path
    source_snapshots: tuple[tuple[Path, FileSnapshot], ...]
    output_snapshot: FileSnapshot
    candidate_snapshot: FileSnapshot
    baseline_bytes: bytes

    def __post_init__(self) -> None:
        if hashlib.sha256(self.baseline_bytes).hexdigest() != self.output_snapshot.digest:
            raise ValueError("Rollback baseline bytes must match the captured output snapshot.")


def _profile_registry() -> dict[str, DependencySurface]:
    validate_compile_registry()
    registry: dict[str, DependencySurface] = {}
    for surface in compiled_dependency_surfaces():
        profile = surface.compile_profile
        if profile is None or not PROFILE_NAME_RE.fullmatch(profile):
            raise RuntimeError(f"Invalid compiler profile in dependency registry: {profile!r}")
        if profile in registry:
            raise RuntimeError(f"Duplicate compiler profile in dependency registry: {profile}")
        registry[profile] = surface
    return registry


def _parse_profiles(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None or not raw_value.strip():
        raise RuntimeError(
            "LOCK_PROFILES is required; invoke the governed Make target with "
            'LOCK_PROFILES="<profile>" make requirements-locks.'
        )
    profiles = tuple(raw_value.split())
    if len(profiles) != len(set(profiles)):
        raise RuntimeError(f"{PROFILE_SELECTION_ENV} must not contain duplicate profiles.")
    registry = _profile_registry()
    unknown = sorted(set(profiles) - set(registry))
    if unknown:
        raise RuntimeError(f"Unknown lock compiler profiles: {unknown}")
    return profiles


def _parse_upgrades(raw_value: str | None) -> dict[str, str]:
    upgrades: dict[str, str] = {}
    for raw_spec in (raw_value or "").split():
        match = EXACT_UPGRADE_RE.fullmatch(raw_spec)
        if match is None:
            raise RuntimeError(
                f"Invalid upgrade target {raw_spec!r}; use exact package==version tokens only."
            )
        try:
            requirement = Requirement(raw_spec)
        except InvalidRequirement as exc:
            raise RuntimeError(f"Invalid upgrade target {raw_spec!r}: {exc}") from exc
        if requirement.extras or requirement.marker is not None or requirement.url is not None:
            raise RuntimeError(
                f"Upgrade target must not contain extras, markers, or URLs: {raw_spec}"
            )
        normalized_name = str(canonicalize_name(match.group("name")))
        if normalized_name == "pip":
            raise RuntimeError("The governed lock workflow must never pin or upgrade pip.")
        if normalized_name in upgrades:
            raise RuntimeError(f"Duplicate upgrade target: {normalized_name}")
        upgrades[normalized_name] = match.group("version")
    return upgrades


def _parse_graph_changes(raw_value: str | None) -> frozenset[str]:
    packages: set[str] = set()
    for raw_name in (raw_value or "").split():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", raw_name):
            raise RuntimeError(
                f"Invalid graph-change package {raw_name!r}; use package names only."
            )
        normalized_name = str(canonicalize_name(raw_name))
        if normalized_name == "pip":
            raise RuntimeError("The governed lock workflow must never add or remove pip.")
        if normalized_name in packages:
            raise RuntimeError(f"Duplicate graph-change package: {normalized_name}")
        packages.add(normalized_name)
    if packages:
        raise RuntimeError(
            "GRAPH_CHANGE_PACKAGES is not supported by the governed lock compiler. "
            "Only exact seeded-baseline refreshes selected with UPGRADE_PACKAGES are "
            "admitted; dependency graph changes require a future versioned "
            "artifact-admission contract."
        )
    return frozenset(packages)


def _capture_file(path: Path) -> FileCapture:
    """Read one regular file through a no-follow descriptor and bind bytes to identity."""

    no_follow = getattr(os, "O_NOFOLLOW", None)
    nonblocking = getattr(os, "O_NONBLOCK", None)
    if no_follow is None or nonblocking is None:
        raise RuntimeError("Dependency capture requires POSIX no-follow nonblocking reads.")
    flags = os.O_RDONLY | no_follow | nonblocking
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeError(
            f"Dependency path must remain a readable regular non-symlink file: {path}"
        ) from exc
    chunks: list[bytes] = []
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError(f"Dependency path must remain a regular file: {path}")
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        final_metadata = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    path_metadata = path.lstat()
    if (
        stat.S_ISLNK(path_metadata.st_mode)
        or (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mode,
            metadata.st_uid,
        )
        != (
            final_metadata.st_dev,
            final_metadata.st_ino,
            final_metadata.st_size,
            final_metadata.st_mode,
            final_metadata.st_uid,
        )
        or (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mode,
            metadata.st_uid,
        )
        != (
            path_metadata.st_dev,
            path_metadata.st_ino,
            path_metadata.st_size,
            path_metadata.st_mode,
            path_metadata.st_uid,
        )
    ):
        raise RuntimeError(f"Dependency file identity changed while it was read: {path}")
    content = b"".join(chunks)
    return FileCapture(
        content=content,
        snapshot=FileSnapshot(
            digest=hashlib.sha256(content).hexdigest(),
            mode=stat.S_IMODE(metadata.st_mode),
            device=metadata.st_dev,
            inode=metadata.st_ino,
            owner_uid=metadata.st_uid,
            size=metadata.st_size,
        ),
    )


def _snapshot(path: Path) -> FileSnapshot:
    return _capture_file(path).snapshot


def _assert_snapshot(path: Path, expected: FileSnapshot) -> None:
    actual = _snapshot(path)
    if actual != expected:
        raise RuntimeError(f"Dependency file changed during lock compilation: {path.name}")


def _streaming_file_snapshot(path: Path) -> FileSnapshot:
    """Hash one regular file without following links or retaining its bytes."""

    no_follow = getattr(os, "O_NOFOLLOW", None)
    nonblocking = getattr(os, "O_NONBLOCK", None)
    if no_follow is None or nonblocking is None:
        raise RuntimeError("Wheel validation requires POSIX no-follow nonblocking reads.")
    descriptor = os.open(path, os.O_RDONLY | no_follow | nonblocking)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError(f"Wheel artifact must remain a regular file: {path.name}")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        final_metadata = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    path_metadata = path.lstat()
    identity = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mode,
        metadata.st_uid,
    )
    if (
        stat.S_ISLNK(path_metadata.st_mode)
        or identity
        != (
            final_metadata.st_dev,
            final_metadata.st_ino,
            final_metadata.st_size,
            final_metadata.st_mode,
            final_metadata.st_uid,
        )
        or identity
        != (
            path_metadata.st_dev,
            path_metadata.st_ino,
            path_metadata.st_size,
            path_metadata.st_mode,
            path_metadata.st_uid,
        )
    ):
        raise RuntimeError(f"Wheel artifact identity changed while it was read: {path.name}")
    return FileSnapshot(
        digest=digest.hexdigest(),
        mode=stat.S_IMODE(metadata.st_mode),
        device=metadata.st_dev,
        inode=metadata.st_ino,
        owner_uid=metadata.st_uid,
        size=metadata.st_size,
    )


def _assert_validated_wheel(artifact: ValidatedWheel) -> None:
    if _streaming_file_snapshot(artifact.path) != artifact.snapshot:
        raise RuntimeError(
            f"Validated wheel changed before offline compilation: {artifact.path.name}"
        )


def _assert_private_directory(path: Path, *, label: str) -> None:
    metadata = path.lstat()
    effective_uid = getattr(os, "geteuid", None)
    if (
        not callable(effective_uid)
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != effective_uid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise RuntimeError(f"{label} must be a private user-owned directory.")


def _validated_repo_file(repo_root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Dependency registry path must stay repo-relative: {relative_path}")
    candidate = repo_root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise RuntimeError(
            f"Dependency registry path must be a regular non-symlink file: {relative_path}"
        )
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RuntimeError(
            f"Dependency registry path escapes the repository: {relative_path}"
        ) from exc
    return candidate


def _validate_source_manifest(
    repo_root: Path,
    source_path: Path,
    *,
    visited: set[Path] | None = None,
    allow_directives: tuple[str, ...] = (),
) -> tuple[Path, ...]:
    captures: dict[Path, FileCapture] = {}
    return _capture_and_validate_source_manifest(
        repo_root,
        source_path,
        captures=captures,
        visited=visited,
        allow_directives=allow_directives,
    )


def _capture_and_validate_source_manifest(
    repo_root: Path,
    source_path: Path,
    *,
    captures: dict[Path, FileCapture],
    visited: set[Path] | None = None,
    allow_directives: tuple[str, ...] = (),
) -> tuple[Path, ...]:
    """Capture and validate the exact manifest bytes later exposed to the resolver."""

    visited = set() if visited is None else visited
    if source_path in visited:
        return ()
    visited.add(source_path)
    capture = captures.get(source_path)
    if capture is None:
        capture = _capture_file(source_path)
        captures[source_path] = capture
    try:
        source_text = capture.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"Dependency manifest must be UTF-8: {source_path.name}") from exc
    referenced_paths: list[Path] = []
    for raw_line in source_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-c ", "--constraint ")):
            referenced = line.split(maxsplit=1)[1]
            referenced_path = _validated_repo_file(repo_root, referenced)
            referenced_paths.append(referenced_path)
            referenced_paths.extend(
                _capture_and_validate_source_manifest(
                    repo_root,
                    referenced_path,
                    captures=captures,
                    visited=visited,
                )
            )
            continue
        if line in allow_directives:
            continue
        if line.startswith("-"):
            raise RuntimeError(f"Unsupported resolver directive in {source_path.name}: {line!r}")
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            raise RuntimeError(
                f"Invalid requirement in {source_path.name}: {line!r}: {exc}"
            ) from exc
        if requirement.url is not None:
            raise RuntimeError(
                f"Direct URL requirements are forbidden in {source_path.name}: {line!r}"
            )
    return tuple(dict.fromkeys(referenced_paths))


def _materialize_resolver_inputs(
    *,
    repo_root: Path,
    captures: Mapping[Path, FileCapture],
    destination_root: Path,
) -> tuple[tuple[Path, FileSnapshot], ...]:
    """Write descriptor-captured manifests into one private resolver-only tree."""

    materialized: list[tuple[Path, FileSnapshot]] = []
    for source_path, capture in captures.items():
        try:
            relative_path = source_path.relative_to(repo_root)
        except ValueError as exc:
            raise RuntimeError(f"Dependency source escapes the repository: {source_path}") from exc
        destination = destination_root / relative_path
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(capture.content)
            output.flush()
            os.fsync(output.fileno())
        materialized.append((destination, _snapshot(destination)))
    return tuple(materialized)


def _exact_pin_map(text: str, *, label: str) -> dict[str, ExactPin]:
    pins: dict[str, ExactPin] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "--")):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            raise RuntimeError(f"{label}: invalid requirement {line!r}: {exc}") from exc
        exact_versions = [
            specifier.version for specifier in requirement.specifier if specifier.operator == "=="
        ]
        if len(exact_versions) != 1 or len(tuple(requirement.specifier)) != 1:
            raise RuntimeError(f"{label}: requirement is not one exact pin: {line!r}")
        name = str(canonicalize_name(requirement.name))
        if name in pins:
            raise RuntimeError(f"{label}: duplicate normalized package pin: {name}")
        pins[name] = ExactPin(
            version=exact_versions[0],
            extras=tuple(sorted(requirement.extras)),
            marker=str(requirement.marker) if requirement.marker is not None else None,
            url=requirement.url,
        )
    return pins


def _canonical_version(raw_version: str, *, label: str) -> str:
    try:
        return str(Version(raw_version))
    except InvalidVersion as exc:
        raise RuntimeError(f"{label}: invalid package version {raw_version!r}") from exc


def _resolver_bootstrap_artifacts() -> frozenset[tuple[str, str]]:
    """Return exact metadata-only artifacts required by the offline resolver."""

    try:
        pip_version = importlib_metadata.version("pip")
    except importlib_metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            "The governed lock compiler requires pip in its approved interpreter."
        ) from exc
    return frozenset(
        {
            (
                "pip",
                _canonical_version(
                    pip_version,
                    label="offline resolver bootstrap pip",
                ),
            )
        }
    )


def _capture_lock_input_plan(
    *,
    repo_root: Path,
    surface: DependencySurface,
    upgrades: Mapping[str, str],
) -> LockInputPlan:
    """Capture one seeded lock transaction before any credentialed network work."""

    output_path = _validated_repo_file(repo_root, surface.lockfile)
    source_paths = tuple(
        _validated_repo_file(repo_root, source) for source in surface.compile_sources
    )
    source_captures: dict[Path, FileCapture] = {}
    for source_path in source_paths:
        _capture_and_validate_source_manifest(
            repo_root,
            source_path,
            captures=source_captures,
            allow_directives=surface.allow_lock_directives,
        )

    output_capture = _capture_file(output_path)
    try:
        baseline_text = output_capture.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{surface.lockfile}: seeded lock must be UTF-8") from exc
    baseline_pins = _exact_pin_map(baseline_text, label=f"{surface.lockfile} baseline")
    if "pip" in baseline_pins:
        raise RuntimeError(f"{surface.lockfile}: seeded locks must not pin pip")
    for package in upgrades:
        if package not in baseline_pins:
            raise RuntimeError(
                f"{surface.lockfile}: requested upgrade package is absent from the seeded lock: "
                f"{package}"
            )

    expected_artifacts: set[tuple[str, str]] = set()
    for package, pin in baseline_pins.items():
        if pin.url is not None:
            raise RuntimeError(
                f"{surface.lockfile}: seeded lock contains forbidden direct URL for {package}"
            )
        desired_version = upgrades.get(package, pin.version)
        expected_artifacts.add(
            (
                package,
                _canonical_version(
                    desired_version,
                    label=f"{surface.lockfile} expected artifact {package}",
                ),
            )
        )
    return LockInputPlan(
        surface=surface,
        output_path=output_path,
        output_capture=output_capture,
        source_captures=tuple(source_captures.items()),
        expected_artifacts=frozenset(expected_artifacts),
    )


def _assert_lock_input_plan(plan: LockInputPlan) -> None:
    _assert_snapshot(plan.output_path, plan.output_capture.snapshot)
    for path, capture in plan.source_captures:
        _assert_snapshot(path, capture.snapshot)


def _expected_artifacts(
    plans: Sequence[LockInputPlan],
) -> frozenset[tuple[str, str]]:
    expected: set[tuple[str, str]] = set()
    for plan in plans:
        expected.update(plan.expected_artifacts)
    return frozenset(expected)


def _validate_candidate_surface(surface: DependencySurface, candidate_text: str) -> None:
    """Reject resolver metadata that must never survive into a governed lock."""

    for token in FORBIDDEN_LOCK_TOKENS:
        if token in candidate_text:
            raise RuntimeError(
                f"{surface.lockfile}: forbidden token in resolver candidate: {token!r}"
            )
    for raw_line in candidate_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line.startswith(("-", "--")):
            raise RuntimeError(
                f"{surface.lockfile}: unexpected resolver directive in candidate: {line!r}"
            )


def _validate_candidate_delta(
    *,
    surface: DependencySurface,
    baseline_text: str,
    candidate_text: str,
    upgrades: Mapping[str, str],
    graph_changes: frozenset[str],
    repo_root: Path,
) -> None:
    _validate_candidate_surface(surface, candidate_text)
    baseline = _exact_pin_map(baseline_text, label=f"{surface.lockfile} baseline")
    candidate = _exact_pin_map(candidate_text, label=f"{surface.lockfile} candidate")
    if "pip" in candidate:
        raise RuntimeError(f"{surface.lockfile}: generated locks must not pin pip")
    missing = sorted(set(baseline) - set(candidate))
    added = sorted(set(candidate) - set(baseline))
    actual_graph_changes = set(missing) | set(added)
    unexpected_graph_changes = sorted(actual_graph_changes - graph_changes)
    unused_graph_changes = sorted(graph_changes - actual_graph_changes)
    if unexpected_graph_changes or unused_graph_changes:
        raise RuntimeError(
            f"{surface.lockfile}: dependency graph change is not exactly authorized; "
            f"missing={missing}, added={added}, "
            f"unexpected={unexpected_graph_changes}, unused={unused_graph_changes}"
        )

    changed: set[str] = set()
    for package in sorted(set(baseline) & set(candidate)):
        before = baseline[package]
        after = candidate[package]
        if (before.extras, before.marker, before.url) != (
            after.extras,
            after.marker,
            after.url,
        ):
            raise RuntimeError(f"{surface.lockfile}: requirement metadata drifted for {package}")
        if before.version != after.version:
            changed.add(package)

    unexpected = sorted(changed - set(upgrades))
    if unexpected:
        raise RuntimeError(f"{surface.lockfile}: unrelated package versions changed: {unexpected}")
    for package, expected_version in upgrades.items():
        if package not in candidate:
            raise RuntimeError(
                f"{surface.lockfile}: requested upgrade package is absent from the candidate: "
                f"{package}"
            )
        if candidate[package].version != expected_version:
            raise RuntimeError(
                f"{surface.lockfile}: {package} resolved to {candidate[package].version}, "
                f"expected {expected_version}"
            )

    direct_names: set[str] = set()
    for source in surface.compile_sources:
        direct_names.update(_requirement_package_names(repo_root, source))
    missing_direct = sorted(direct_names - set(candidate))
    if missing_direct:
        raise RuntimeError(
            f"{surface.lockfile}: generated lock lost direct package owners: {missing_direct}"
        )


def _reject_ambient_resolver_overrides(environment: Mapping[str, str]) -> None:
    overrides = sorted(
        name for name in AMBIENT_RESOLVER_ENV_VARS if environment.get(name, "").strip()
    )
    if overrides:
        raise RuntimeError(
            "Ambient resolver/network controls are forbidden for lock compilation: "
            + ", ".join(overrides)
        )


def _validated_netrc_capture(netrc_path: Path) -> FileCapture | None:
    """Capture a private, user-owned default netrc through a no-follow descriptor."""

    try:
        metadata = netrc_path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError("Default ~/.netrc must be a regular non-symlink file.")
    effective_uid = getattr(os, "geteuid", None)
    if not callable(effective_uid):
        raise RuntimeError(
            "Governed lock compilation requires POSIX effective-UID ownership checks."
        )
    capture = _capture_file(netrc_path)
    if capture.snapshot.owner_uid != effective_uid():
        raise RuntimeError("Default ~/.netrc must be owned by the effective user.")
    if capture.snapshot.mode & 0o077:
        raise RuntimeError("Default ~/.netrc permissions must be no broader than 0600.")
    return capture


def _write_private_bytes(path: Path, content: bytes) -> FileSnapshot:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    return _snapshot(path)


def _render_canonical_netrc(
    *,
    capture: FileCapture,
    hostname: str,
    resolver_home: Path,
) -> bytes | None:
    """Return a netrc containing only the canonical private-proxy authority."""

    parse_path = resolver_home / ".netrc.source"
    parse_snapshot = _write_private_bytes(parse_path, capture.content)
    try:
        _assert_snapshot(parse_path, parse_snapshot)
        try:
            parsed = netrc.netrc(str(parse_path))
        except (netrc.NetrcParseError, OSError) as exc:
            raise ValueError(
                f"netrc_error: unable to read credentials for {hostname}: {type(exc).__name__}"
            ) from exc
        _assert_snapshot(parse_path, parse_snapshot)
    finally:
        parse_path.unlink(missing_ok=True)

    credentials = parsed.hosts.get(hostname)
    if credentials is None:
        return None
    login, _, password = credentials
    if not login or not password:
        raise ValueError(f"netrc_error: incomplete credentials for {hostname}")
    if login.strip().lower() == "root":
        raise ValueError("root_devpi_credentials: root devpi credentials are forbidden")

    def quote(value: str, *, field: str) -> str:
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError(f"netrc_error: invalid control character in {field} for {hostname}")
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    rendered = (
        f"machine {quote(hostname, field='hostname')}\n"
        f"  login {quote(login, field='login')}\n"
        f"  password {quote(password, field='password')}\n"
    )
    return rendered.encode("utf-8")


def _private_proxy_child_env(
    environment: Mapping[str, str],
    *,
    resolver_home: Path,
) -> dict[str, str]:
    _reject_ambient_resolver_overrides(environment)
    if environment.get("PULSEPLATE_PYTHON_NETRC", "").strip():
        raise RuntimeError(
            "PULSEPLATE_PYTHON_NETRC is not supported for lock compilation because pip "
            "does not consume it; use the default non-root ~/.netrc authority."
        )
    index_url, trusted_host = resolve_private_proxy_settings(
        index_url=environment.get(APPROVED_INDEX_ENV_VAR),
        trusted_host=None,
    )
    if trusted_host:
        raise RuntimeError("Trusted-host overrides are forbidden for the canonical HTTPS proxy.")
    canonical_index = validate_index_url(index_url)
    hostname = urlparse(canonical_index).hostname
    if hostname is None:
        raise RuntimeError("Approved private proxy URL has no hostname.")
    if resolver_home.is_symlink() or not resolver_home.is_dir():
        raise RuntimeError("Resolver HOME must be a private regular directory.")
    os.chmod(resolver_home, 0o700)
    source_home = Path(environment.get("HOME", str(Path.home())))
    source_netrc = source_home / ".netrc"
    netrc_capture = _validated_netrc_capture(source_netrc)
    _assert_private_directory(resolver_home, label="Credentialed resolver HOME")
    resolver_netrc = resolver_home / ".netrc"
    materialized_snapshot: FileSnapshot | None = None
    if netrc_capture is not None:
        canonical_netrc = _render_canonical_netrc(
            capture=netrc_capture,
            hostname=hostname,
            resolver_home=resolver_home,
        )
        if canonical_netrc is not None:
            materialized_snapshot = _write_private_bytes(resolver_netrc, canonical_netrc)
    basic_auth_from_netrc(hostname, netrc_file=resolver_netrc)
    if materialized_snapshot is not None:
        _assert_snapshot(resolver_netrc, materialized_snapshot)

    child_env = {
        name: value for name in PASSTHROUGH_ENV_VARS if (value := environment.get(name)) is not None
    }
    child_env.update(
        {
            "PIP_INDEX_URL": canonical_index,
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_KEYRING_PROVIDER": "disabled",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_NO_INPUT": "1",
            "PIP_ONLY_BINARY": ":all:",
        }
    )
    child_env["HOME"] = str(resolver_home)
    return child_env


def _build_download_command(
    *,
    wheelhouse: Path,
    expected_artifacts: frozenset[tuple[str, str]],
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--disable-pip-version-check",
        "--no-input",
        "--only-binary=:all:",
        "--no-deps",
        "--dest",
        str(wheelhouse),
        "--find-links",
        str(wheelhouse),
    ]
    command.extend(f"{package}=={version}" for package, version in sorted(expected_artifacts))
    return command


def _collect_private_proxy_artifact_hashes(
    *,
    expected_artifacts: frozenset[tuple[str, str]],
    child_env: Mapping[str, str],
) -> dict[str, str]:
    """Collect proxy-origin SHA-256 admissions for every exact artifact.

    The credentialed phase reads only canonical private Simple API pages.  A
    wheel is admitted later only when its filename and digest match one of
    these proxy-hosted, hash-fragment-bound links.
    """

    canonical_index = validate_index_url(child_env.get("PIP_INDEX_URL", ""))
    parsed_index = urlparse(canonical_index)
    hostname = parsed_index.hostname
    if hostname is None:
        raise RuntimeError("Approved private proxy URL has no hostname.")
    resolver_home = Path(child_env.get("HOME", ""))
    if not resolver_home.is_dir() or resolver_home.is_symlink():
        raise RuntimeError("Credentialed resolver HOME is unavailable for artifact admission.")
    authorization_header = basic_auth_from_netrc(
        hostname,
        netrc_file=resolver_home / ".netrc",
    )

    artifacts = sorted(expected_artifacts)
    if not artifacts:
        return {}

    def fetch_one(artifact: tuple[str, str]) -> dict[str, str]:
        package, version = artifact
        normalized_package = normalize_project_name(package)
        url = project_page_url(canonical_index, normalized_package)
        last_error: OSError | None = None
        for _attempt in range(ARTIFACT_ADMISSION_ATTEMPTS):
            try:
                status, body = fetch_project_page(
                    url,
                    timeout_seconds=ARTIFACT_ADMISSION_TIMEOUT_SECONDS,
                    max_bytes=ARTIFACT_ADMISSION_MAX_BYTES,
                    authorization_header=authorization_header,
                )
                break
            except OSError as exc:
                last_error = exc
        else:
            if last_error is None:
                raise RuntimeError("Artifact-admission retry state is inconsistent.")
            raise RuntimeError(
                f"{normalized_package}=={version}: private proxy artifact-admission "
                f"request failed after {ARTIFACT_ADMISSION_ATTEMPTS} attempts: "
                f"{redact_text(str(last_error))}"
            ) from last_error
        if status < 200 or status >= 300:
            raise RuntimeError(
                f"{normalized_package}=={version}: private proxy artifact-admission "
                f"request returned HTTP {status}"
            )
        if len(body) > ARTIFACT_ADMISSION_MAX_BYTES:
            raise RuntimeError(
                f"{normalized_package}=={version}: private proxy Simple page exceeds "
                "the artifact-admission size limit"
            )
        try:
            project_hashes: dict[str, str] = trusted_exact_pin_wheel_hashes(
                body=body,
                project_url=url,
                normalized_project=normalized_package,
                expected_version=version,
            )
        except ValueError as exc:
            raise RuntimeError(f"{normalized_package}=={version}: {redact_text(str(exc))}") from exc
        return project_hashes

    admitted: dict[str, str] = {}
    with ThreadPoolExecutor(
        max_workers=min(ARTIFACT_ADMISSION_MAX_WORKERS, len(artifacts)),
        thread_name_prefix="lock-artifact-admission",
    ) as executor:
        for project_hashes in executor.map(fetch_one, artifacts):
            for filename, digest in sorted(project_hashes.items()):
                previous = admitted.get(filename)
                if previous is not None and previous != digest:
                    raise RuntimeError(
                        f"{filename}: private proxy advertised conflicting SHA-256 hashes"
                    )
                admitted[filename] = digest
    return admitted


def _download_profile_wheels(
    *,
    wheelhouse: Path,
    plans: Sequence[LockInputPlan],
    child_env: Mapping[str, str],
    bootstrap_artifacts: frozenset[tuple[str, str]] = frozenset(),
) -> None:
    """Fetch one exact, no-dependency artifact batch per selected profile."""

    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise RuntimeError("Wheelhouse must be a private regular directory.")
    os.chmod(wheelhouse, 0o700)
    _assert_private_directory(wheelhouse, label="Wheelhouse")
    if tuple(wheelhouse.iterdir()):
        raise RuntimeError("Wheelhouse must be empty before credentialed artifact download.")
    for plan in plans:
        resolver_artifacts = plan.expected_artifacts | bootstrap_artifacts
        if not resolver_artifacts:
            continue
        command = _build_download_command(
            wheelhouse=wheelhouse,
            expected_artifacts=resolver_artifacts,
        )
        result = subprocess.run(  # nosec B603: fixed pip download argv and exact governed pins (remove-by: 2027-01-31, ref: PR-2142)
            command,
            cwd=wheelhouse,
            env=dict(child_env),
            text=True,
            capture_output=True,
            check=False,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            detail = redact_text((result.stderr or result.stdout).strip())[-2000:]
            raise RuntimeError(
                f"{plan.surface.lockfile}: exact artifact download failed with exit "
                f"{result.returncode}: {detail}"
            )


def _validate_wheel_member_name(wheel_path: Path, member_name: str) -> PurePosixPath:
    if "\\" in member_name:
        raise RuntimeError(f"{wheel_path.name}: wheel member contains a backslash")
    member_path = PurePosixPath(member_name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise RuntimeError(f"{wheel_path.name}: wheel member escapes the archive root")
    return member_path


def _validate_zip_central_directory_bounds(
    *,
    descriptor: int,
    wheel_path: Path,
    file_size: int,
) -> None:
    """Bound parser work before ``ZipFile`` materializes the central directory."""

    if file_size < ZIP_END_OF_CENTRAL_DIRECTORY_SIZE:
        raise RuntimeError(f"{wheel_path.name}: malformed wheel archive")
    tail_size = min(
        file_size,
        ZIP_END_OF_CENTRAL_DIRECTORY_SIZE + ZIP_MAX_COMMENT_BYTES,
    )
    pread = getattr(os, "pread", None)
    if not callable(pread):
        raise RuntimeError("Wheel validation requires POSIX descriptor-bound reads.")
    tail = pread(descriptor, tail_size, file_size - tail_size)
    search_end = len(tail)
    while True:
        offset = tail.rfind(
            ZIP_END_OF_CENTRAL_DIRECTORY_SIGNATURE,
            0,
            search_end,
        )
        if offset < 0:
            raise RuntimeError(f"{wheel_path.name}: malformed wheel archive")
        if offset + ZIP_END_OF_CENTRAL_DIRECTORY_SIZE <= len(tail):
            (
                signature,
                disk_number,
                central_directory_disk,
                entries_on_disk,
                total_entries,
                central_directory_size,
                central_directory_offset,
                comment_size,
            ) = struct.unpack_from("<4s4H2LH", tail, offset)
            if (
                signature == ZIP_END_OF_CENTRAL_DIRECTORY_SIGNATURE
                and offset + ZIP_END_OF_CENTRAL_DIRECTORY_SIZE + comment_size == len(tail)
            ):
                break
        search_end = offset

    if disk_number or central_directory_disk or entries_on_disk != total_entries:
        raise RuntimeError(f"{wheel_path.name}: multi-disk wheel archives are forbidden")
    if (
        total_entries == 0xFFFF
        or central_directory_size == 0xFFFFFFFF
        or central_directory_offset == 0xFFFFFFFF
    ):
        raise RuntimeError(f"{wheel_path.name}: ZIP64 wheel archives are forbidden")
    if total_entries > MAX_WHEEL_MEMBERS:
        raise RuntimeError(f"{wheel_path.name}: wheel contains too many archive members")
    if central_directory_size > MAX_WHEEL_CENTRAL_DIRECTORY_BYTES:
        raise RuntimeError(f"{wheel_path.name}: wheel central directory exceeds the size limit")
    end_of_central_directory = file_size - tail_size + offset
    if central_directory_offset + central_directory_size != end_of_central_directory:
        raise RuntimeError(f"{wheel_path.name}: malformed wheel central directory bounds")


def _single_metadata_header(
    *,
    wheel_path: Path,
    metadata: object,
    header_name: str,
) -> str:
    get_all = getattr(metadata, "get_all", None)
    values = get_all(header_name, []) if callable(get_all) else []
    if len(values) != 1 or not isinstance(values[0], str) or not values[0].strip():
        raise RuntimeError(
            f"{wheel_path.name}: METADATA must contain exactly one {header_name} header"
        )
    return values[0].strip()


def _validate_one_wheel(
    *,
    wheel_path: Path,
    expected_artifacts: frozenset[tuple[str, str]],
) -> ValidatedWheel:
    try:
        filename_name, filename_version, _, _ = parse_wheel_filename(wheel_path.name)
    except (InvalidWheelFilename, ValueError) as exc:
        raise RuntimeError(f"{wheel_path.name}: malformed wheel filename") from exc
    filename_key = (
        str(canonicalize_name(filename_name)),
        str(filename_version),
    )
    if filename_key not in expected_artifacts:
        raise RuntimeError(
            f"{wheel_path.name}: unexpected wheel artifact " f"{filename_key[0]}=={filename_key[1]}"
        )

    no_follow = getattr(os, "O_NOFOLLOW", None)
    nonblocking = getattr(os, "O_NONBLOCK", None)
    if no_follow is None or nonblocking is None:
        raise RuntimeError("Wheel validation requires POSIX no-follow nonblocking reads.")
    try:
        descriptor = os.open(wheel_path, os.O_RDONLY | no_follow | nonblocking)
    except OSError as exc:
        raise RuntimeError(
            f"{wheel_path.name}: wheel must remain a regular non-symlink file"
        ) from exc
    try:
        wheel_stat = os.fstat(descriptor)
        if not stat.S_ISREG(wheel_stat.st_mode):
            raise RuntimeError(f"{wheel_path.name}: wheel artifact is not a regular file")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        _validate_zip_central_directory_bounds(
            descriptor=descriptor,
            wheel_path=wheel_path,
            file_size=wheel_stat.st_size,
        )
        os.lseek(descriptor, 0, os.SEEK_SET)
        with os.fdopen(descriptor, "rb") as wheel_stream:
            descriptor = -1
            try:
                with zipfile.ZipFile(wheel_stream, "r") as wheel:
                    metadata_members: list[zipfile.ZipInfo] = []
                    members = wheel.infolist()
                    if len(members) > MAX_WHEEL_MEMBERS:
                        raise RuntimeError(
                            f"{wheel_path.name}: wheel member count changed during parsing"
                        )
                    member_names: set[str] = set()
                    for member in members:
                        if member.filename in member_names:
                            raise RuntimeError(
                                f"{wheel_path.name}: wheel contains duplicate archive members"
                            )
                        member_names.add(member.filename)
                        member_path = _validate_wheel_member_name(wheel_path, member.filename)
                        member_mode = member.external_attr >> 16
                        if member_mode and stat.S_ISLNK(member_mode):
                            raise RuntimeError(
                                f"{wheel_path.name}: wheel contains a symlink member"
                            )
                        if (
                            len(member_path.parts) == 2
                            and member_path.parts[0].endswith(".dist-info")
                            and member_path.parts[1] == "METADATA"
                        ):
                            metadata_members.append(member)
                    if len(metadata_members) != 1:
                        raise RuntimeError(
                            f"{wheel_path.name}: wheel must contain exactly one "
                            "*.dist-info/METADATA"
                        )
                    metadata_member = metadata_members[0]
                    if metadata_member.file_size > MAX_WHEEL_METADATA_BYTES:
                        raise RuntimeError(
                            f"{wheel_path.name}: METADATA exceeds the static size limit"
                        )
                    metadata_bytes = wheel.read(metadata_member)
                final_metadata = os.fstat(wheel_stream.fileno())
            except zipfile.BadZipFile as exc:
                raise RuntimeError(f"{wheel_path.name}: malformed wheel archive") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    path_metadata = wheel_path.lstat()
    identity = (
        wheel_stat.st_dev,
        wheel_stat.st_ino,
        wheel_stat.st_size,
        wheel_stat.st_mode,
        wheel_stat.st_uid,
    )
    if (
        stat.S_ISLNK(path_metadata.st_mode)
        or identity
        != (
            final_metadata.st_dev,
            final_metadata.st_ino,
            final_metadata.st_size,
            final_metadata.st_mode,
            final_metadata.st_uid,
        )
        or identity
        != (
            path_metadata.st_dev,
            path_metadata.st_ino,
            path_metadata.st_size,
            path_metadata.st_mode,
            path_metadata.st_uid,
        )
    ):
        raise RuntimeError(f"{wheel_path.name}: wheel identity changed during validation")
    artifact_snapshot = FileSnapshot(
        digest=digest.hexdigest(),
        mode=stat.S_IMODE(wheel_stat.st_mode),
        device=wheel_stat.st_dev,
        inode=wheel_stat.st_ino,
        owner_uid=wheel_stat.st_uid,
        size=wheel_stat.st_size,
    )

    metadata_message = BytesParser(policy=policy.default).parsebytes(metadata_bytes)
    if metadata_message.defects:
        raise RuntimeError(f"{wheel_path.name}: malformed wheel METADATA headers")
    metadata_name = _single_metadata_header(
        wheel_path=wheel_path,
        metadata=metadata_message,
        header_name="Name",
    )
    metadata_version = _single_metadata_header(
        wheel_path=wheel_path,
        metadata=metadata_message,
        header_name="Version",
    )
    metadata_key = (
        str(canonicalize_name(metadata_name)),
        _canonical_version(metadata_version, label=f"{wheel_path.name} METADATA"),
    )
    if metadata_key != filename_key:
        raise RuntimeError(f"{wheel_path.name}: filename and METADATA Name/Version do not match")

    metadata_path = PurePosixPath(metadata_member.filename)
    dist_info_stem = metadata_path.parts[0][: -len(".dist-info")]
    if "-" not in dist_info_stem:
        raise RuntimeError(f"{wheel_path.name}: malformed dist-info directory")
    dist_info_name, dist_info_version = dist_info_stem.rsplit("-", 1)
    dist_info_key = (
        str(canonicalize_name(dist_info_name)),
        _canonical_version(dist_info_version, label=f"{wheel_path.name} dist-info"),
    )
    if dist_info_key != filename_key:
        raise RuntimeError(f"{wheel_path.name}: dist-info and filename Name/Version do not match")

    dependency_links = metadata_message.get_all("Dependency-Link", [])
    if dependency_links:
        raise RuntimeError(f"{wheel_path.name}: Dependency-Link metadata is forbidden")
    for raw_requirement in metadata_message.get_all("Requires-Dist", []):
        if not isinstance(raw_requirement, str):
            raise RuntimeError(f"{wheel_path.name}: malformed Requires-Dist metadata")
        try:
            requirement = Requirement(raw_requirement)
        except InvalidRequirement as exc:
            raise RuntimeError(
                f"{wheel_path.name}: malformed Requires-Dist metadata: {raw_requirement!r}"
            ) from exc
        if requirement.url is not None:
            raise RuntimeError(
                f"{wheel_path.name}: direct-reference Requires-Dist metadata is forbidden"
            )
    return ValidatedWheel(
        path=wheel_path,
        artifact_key=filename_key,
        snapshot=artifact_snapshot,
    )


def _validate_wheelhouse(
    *,
    wheelhouse: Path,
    expected_artifacts: frozenset[tuple[str, str]],
    admitted_hashes: Mapping[str, str] | None = None,
) -> dict[tuple[str, str], ValidatedWheel]:
    """Statically validate exact wheel identity and metadata without importing code."""

    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise RuntimeError("Wheelhouse must be a regular non-symlink directory.")
    _assert_private_directory(wheelhouse, label="Wheelhouse")
    actual: dict[tuple[str, str], ValidatedWheel] = {}
    for wheel_path in sorted(wheelhouse.iterdir(), key=lambda path: path.name):
        metadata = wheel_path.lstat()
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or wheel_path.suffix != ".whl"
        ):
            raise RuntimeError(
                f"Wheelhouse artifact must be a regular non-symlink .whl file: "
                f"{wheel_path.name}"
            )
        artifact = _validate_one_wheel(
            wheel_path=wheel_path,
            expected_artifacts=expected_artifacts,
        )
        artifact_key = artifact.artifact_key
        previous = actual.get(artifact_key)
        if previous is not None:
            raise RuntimeError(
                f"Wheelhouse contains duplicate artifacts for "
                f"{artifact_key[0]}=={artifact_key[1]}: "
                f"{previous.path.name}, {wheel_path.name}"
            )
        actual[artifact_key] = artifact
        if admitted_hashes is not None:
            expected_digest = admitted_hashes.get(wheel_path.name.lower())
            if expected_digest is None:
                raise RuntimeError(
                    f"{wheel_path.name}: wheel filename is absent from the "
                    "private-proxy artifact admission set"
                )
            if not hmac.compare_digest(artifact.snapshot.digest, expected_digest):
                raise RuntimeError(
                    f"{wheel_path.name}: wheel SHA-256 does not match the "
                    "private-proxy artifact admission hash"
                )

    missing = sorted(expected_artifacts - set(actual))
    extra = sorted(set(actual) - expected_artifacts)
    if missing or extra:
        raise RuntimeError(
            "Wheelhouse artifact set does not match the exact seeded lock set: "
            f"missing={missing}, extra={extra}"
        )
    return actual


def _create_profile_wheelhouse_views(
    *,
    plans: Sequence[LockInputPlan],
    artifacts: Mapping[tuple[str, str], ValidatedWheel],
    views_root: Path,
    bootstrap_artifacts: frozenset[tuple[str, str]] = frozenset(),
) -> dict[str, ProfileWheelhouse]:
    """Create regular-file-only views so one profile cannot see another pin."""

    views: dict[str, ProfileWheelhouse] = {}
    for plan in plans:
        profile = plan.surface.compile_profile
        if profile is None:
            raise RuntimeError("Compiled dependency surface has no profile.")
        view = views_root / profile
        view.mkdir(mode=0o700)
        _assert_private_directory(view, label=f"{profile} wheelhouse")
        resolver_artifacts = plan.expected_artifacts | bootstrap_artifacts
        for artifact_key in sorted(resolver_artifacts):
            artifact = artifacts.get(artifact_key)
            if artifact is None:
                raise RuntimeError(
                    f"{plan.surface.lockfile}: validated wheelhouse is missing "
                    f"{artifact_key[0]}=={artifact_key[1]}"
                )
            _assert_validated_wheel(artifact)
            destination = view / artifact.path.name
            os.link(artifact.path, destination, follow_symlinks=False)
        validated_view = _validate_wheelhouse(
            wheelhouse=view,
            expected_artifacts=resolver_artifacts,
        )
        views[profile] = ProfileWheelhouse(
            path=view,
            artifacts=tuple(validated_view[key] for key in sorted(resolver_artifacts)),
        )
    return views


def _remove_credential_material(resolver_home: Path) -> None:
    netrc_path = resolver_home / ".netrc"
    netrc_path.unlink(missing_ok=True)
    if netrc_path.exists() or netrc_path.is_symlink():
        raise RuntimeError("Temporary private-proxy .netrc was not removed.")


def _offline_compile_env(
    environment: Mapping[str, str],
    *,
    resolver_home: Path,
    wheelhouse: Path,
) -> dict[str, str]:
    """Return a credential-free, index-free environment for pip-tools."""

    _reject_ambient_resolver_overrides(environment)
    if resolver_home.is_symlink() or not resolver_home.is_dir():
        raise RuntimeError("Offline resolver HOME must be a private regular directory.")
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise RuntimeError("Offline wheelhouse must be a regular non-symlink directory.")
    os.chmod(resolver_home, 0o700)
    _assert_private_directory(resolver_home, label="Offline resolver HOME")
    if (resolver_home / ".netrc").exists() or (resolver_home / ".netrc").is_symlink():
        raise RuntimeError("Offline resolver HOME must not contain .netrc credentials.")
    child_env = {
        name: value
        for name in PASSTHROUGH_ENV_VARS
        if name != "HOME" and (value := environment.get(name)) is not None
    }
    child_env.update(
        {
            "HOME": str(resolver_home),
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_FIND_LINKS": str(wheelhouse),
            "PIP_KEYRING_PROVIDER": "disabled",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_NO_INDEX": "1",
            "PIP_NO_INPUT": "1",
            "PIP_ONLY_BINARY": ":all:",
        }
    )
    return child_env


def _build_compile_command(
    *,
    surface: DependencySurface,
    output_path: Path,
    upgrades: Mapping[str, str],
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "piptools",
        "compile",
        "--resolver=backtracking",
        "--no-config",
        "--no-header",
        "--no-allow-unsafe",
        "--unsafe-package",
        "pip",
        "--no-strip-extras",
        "--no-emit-index-url",
        "--no-emit-trusted-host",
        "--no-emit-find-links",
        "--no-emit-options",
        "--newline=lf",
        f"--output-file={output_path}",
    ]
    for package, version in sorted(upgrades.items()):
        command.extend(("--upgrade-package", f"{package}=={version}"))
    command.extend(surface.compile_sources)
    return command


def _prepare_lock(
    *,
    repo_root: Path,
    surface: DependencySurface,
    upgrades: Mapping[str, str],
    graph_changes: frozenset[str],
    child_env: Mapping[str, str],
    input_plan: LockInputPlan | None = None,
    wheel_artifacts: Sequence[ValidatedWheel] = (),
) -> PreparedLock:
    if graph_changes:
        raise RuntimeError(
            "Dependency graph changes require a future versioned artifact-admission contract."
        )
    plan = input_plan or _capture_lock_input_plan(
        repo_root=repo_root,
        surface=surface,
        upgrades=upgrades,
    )
    if plan.surface != surface:
        raise RuntimeError("Lock input plan does not match the selected dependency surface.")
    _assert_lock_input_plan(plan)
    output_path = plan.output_path
    source_captures = dict(plan.source_captures)
    source_snapshots = tuple((path, capture.snapshot) for path, capture in source_captures.items())

    output_capture = plan.output_capture
    baseline_bytes = output_capture.content
    try:
        baseline_text = baseline_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{surface.lockfile}: seeded lock must be UTF-8") from exc
    baseline_pins = _exact_pin_map(baseline_text, label=f"{surface.lockfile} baseline")
    desired_artifacts = frozenset(
        (
            package,
            _canonical_version(
                upgrades.get(package, pin.version),
                label=f"{surface.lockfile} expected artifact {package}",
            ),
        )
        for package, pin in baseline_pins.items()
    )
    if desired_artifacts != plan.expected_artifacts:
        raise RuntimeError(
            f"{surface.lockfile}: input-plan artifact set does not match the seeded lock "
            "and exact upgrades."
        )

    output_snapshot = output_capture.snapshot
    resolver_descriptor, resolver_temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".resolver",
        dir=output_path.parent,
    )
    resolver_candidate_path = Path(resolver_temp_name)
    governed_candidate_path: Path | None = None
    try:
        with os.fdopen(resolver_descriptor, "wb") as candidate_file:
            candidate_file.write(baseline_bytes)
            candidate_file.flush()
            os.fsync(candidate_file.fileno())
        os.chmod(resolver_candidate_path, output_snapshot.mode)
        with tempfile.TemporaryDirectory(prefix="pulseplate-lock-inputs-") as input_dir:
            resolver_input_root = Path(input_dir)
            os.chmod(resolver_input_root, 0o700)
            materialized_snapshots = _materialize_resolver_inputs(
                repo_root=repo_root,
                captures=source_captures,
                destination_root=resolver_input_root,
            )
            command = _build_compile_command(
                surface=surface,
                output_path=resolver_candidate_path,
                upgrades=upgrades,
            )
            process_env = dict(child_env)
            process_env["CUSTOM_COMPILE_COMMAND"] = (
                f'LOCK_PROFILES="{surface.compile_profile}" make requirements-locks'
            )
            for artifact in wheel_artifacts:
                _assert_validated_wheel(artifact)
            result = subprocess.run(  # nosec B603: fixed module argv and registry-owned paths (remove-by: 2027-01-31, ref: PR-2142)
                command,
                cwd=resolver_input_root,
                env=process_env,
                text=True,
                capture_output=True,
                check=False,
                timeout=COMPILE_TIMEOUT_SECONDS,
            )
            if result.returncode != 0:
                detail = redact_text((result.stderr or result.stdout).strip())[-2000:]
                raise RuntimeError(
                    f"{surface.lockfile}: governed resolver failed with exit "
                    f"{result.returncode}: {detail}"
                )
            for artifact in wheel_artifacts:
                _assert_validated_wheel(artifact)
            for path, snapshot in materialized_snapshots:
                _assert_snapshot(path, snapshot)
            for path, snapshot in source_snapshots:
                _assert_snapshot(path, snapshot)
            _assert_snapshot(output_path, output_snapshot)

            resolver_candidate_capture = _capture_file(resolver_candidate_path)
            try:
                candidate_body = resolver_candidate_capture.content.decode("utf-8").lstrip("\n")
            except UnicodeDecodeError as exc:
                raise RuntimeError(f"{surface.lockfile}: resolver candidate must be UTF-8") from exc
            rendered = render_governed_lock_header(surface) + candidate_body
            _validate_candidate_delta(
                surface=surface,
                baseline_text=baseline_text,
                candidate_text=rendered,
                upgrades=upgrades,
                graph_changes=graph_changes,
                repo_root=resolver_input_root,
            )
        governed_descriptor, governed_temp_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.",
            suffix=".candidate",
            dir=output_path.parent,
        )
        governed_candidate_path = Path(governed_temp_name)
        with os.fdopen(governed_descriptor, "wb") as candidate_file:
            os.fchmod(candidate_file.fileno(), output_snapshot.mode)
            candidate_file.write(rendered.encode("utf-8"))
            candidate_file.flush()
            os.fsync(candidate_file.fileno())
        candidate_snapshot = _snapshot(governed_candidate_path)
        return PreparedLock(
            surface=surface,
            output_path=output_path,
            candidate_path=governed_candidate_path,
            source_snapshots=source_snapshots,
            output_snapshot=output_snapshot,
            candidate_snapshot=candidate_snapshot,
            baseline_bytes=baseline_bytes,
        )
    except BaseException:
        if governed_candidate_path is not None:
            governed_candidate_path.unlink(missing_ok=True)
        raise
    finally:
        resolver_candidate_path.unlink(missing_ok=True)


def _validate_profile_transaction(
    *,
    repo_root: Path,
    profiles: Sequence[str],
    graph_changes: frozenset[str],
) -> None:
    if graph_changes:
        raise RuntimeError(
            "GRAPH_CHANGE_PACKAGES is not supported; dependency graph changes require "
            "a future versioned artifact-admission contract."
        )
    if "runtime" not in profiles:
        return
    registry = _profile_registry()
    runtime_lock_path = _validated_repo_file(
        repo_root,
        registry["runtime"].lockfile,
    )
    dependent_profiles: list[str] = []
    for profile in profiles:
        if profile == "runtime":
            continue
        for source in registry[profile].compile_sources:
            source_path = _validated_repo_file(repo_root, source)
            referenced_paths = _validate_source_manifest(
                repo_root,
                source_path,
                allow_directives=registry[profile].allow_lock_directives,
            )
            if runtime_lock_path in referenced_paths:
                dependent_profiles.append(profile)
                break
    if dependent_profiles:
        raise RuntimeError(
            "runtime must be compiled and committed before profiles constrained by "
            f"requirements.txt: {sorted(dependent_profiles)}"
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _compiler_transaction_lock(repo_root: Path) -> Iterator[None]:
    """Serialize governed compilation for one worktree without tracked lock artifacts."""

    effective_uid = getattr(os, "geteuid", None)
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if not callable(effective_uid) or no_follow is None:
        raise RuntimeError("Governed lock compilation requires POSIX file-lock semantics.")
    owner_uid = effective_uid()
    canonical_tmp = (Path(os.sep) / "tmp").resolve(strict=True)
    if not canonical_tmp.is_dir():
        raise RuntimeError("Canonical POSIX /tmp lock root is unavailable.")
    lock_root = canonical_tmp / f"pulseplate-lock-compiler-{owner_uid}"
    try:
        os.mkdir(lock_root, 0o700)
    except FileExistsError:
        pass
    lock_root_metadata = lock_root.lstat()
    if (
        stat.S_ISLNK(lock_root_metadata.st_mode)
        or not stat.S_ISDIR(lock_root_metadata.st_mode)
        or lock_root_metadata.st_uid != owner_uid
        or stat.S_IMODE(lock_root_metadata.st_mode) & 0o077
    ):
        raise RuntimeError("Compiler lock directory must be private and user-owned.")

    worktree_key = hashlib.sha256(str(repo_root.resolve()).encode("utf-8")).hexdigest()
    lock_path = lock_root / f"{worktree_key}.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | no_follow, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != owner_uid
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise RuntimeError("Compiler transaction lock must be private and user-owned.")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                "Another governed lock compilation transaction is already running."
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _atomic_write_bytes(path: Path, content: bytes, mode: int) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".rollback",
        dir=path.parent,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    finally:
        temp_path.unlink(missing_ok=True)


def compile_selected_profiles(
    *,
    repo_root: Path,
    profiles: Sequence[str],
    upgrades: Mapping[str, str],
    graph_changes: frozenset[str],
    environment: Mapping[str, str],
) -> None:
    with _compiler_transaction_lock(repo_root):
        _compile_selected_profiles_locked(
            repo_root=repo_root,
            profiles=profiles,
            upgrades=upgrades,
            graph_changes=graph_changes,
            environment=environment,
        )


def _compile_selected_profiles_locked(
    *,
    repo_root: Path,
    profiles: Sequence[str],
    upgrades: Mapping[str, str],
    graph_changes: frozenset[str],
    environment: Mapping[str, str],
) -> None:
    registry = _profile_registry()
    _validate_profile_transaction(
        repo_root=repo_root,
        profiles=profiles,
        graph_changes=graph_changes,
    )
    plans = tuple(
        _capture_lock_input_plan(
            repo_root=repo_root,
            surface=registry[profile],
            upgrades=upgrades,
        )
        for profile in profiles
    )
    bootstrap_artifacts = _resolver_bootstrap_artifacts()
    with tempfile.TemporaryDirectory(prefix="pulseplate-lock-transaction-") as transaction_dir:
        transaction_root = Path(transaction_dir)
        os.chmod(transaction_root, 0o700)
        wheelhouse = transaction_root / "wheelhouse"
        wheelhouse.mkdir(mode=0o700)
        with tempfile.TemporaryDirectory(
            prefix="credentialed-home-",
            dir=transaction_root,
        ) as credentialed_home_dir:
            credentialed_home = Path(credentialed_home_dir)
            os.chmod(credentialed_home, 0o700)
            download_env = _private_proxy_child_env(
                environment,
                resolver_home=credentialed_home,
            )
            artifact_admissions = _collect_private_proxy_artifact_hashes(
                expected_artifacts=_expected_artifacts(plans) | bootstrap_artifacts,
                child_env=download_env,
            )
            _download_profile_wheels(
                wheelhouse=wheelhouse,
                plans=plans,
                child_env=download_env,
                bootstrap_artifacts=bootstrap_artifacts,
            )
            for plan in plans:
                _assert_lock_input_plan(plan)
            _remove_credential_material(credentialed_home)
        if Path(credentialed_home_dir).exists():
            raise RuntimeError("Credentialed download HOME was not removed before compilation.")
        artifacts = _validate_wheelhouse(
            wheelhouse=wheelhouse,
            expected_artifacts=_expected_artifacts(plans) | bootstrap_artifacts,
            admitted_hashes=artifact_admissions,
        )

        views_root = transaction_root / "profile-wheelhouses"
        views_root.mkdir(mode=0o700)
        profile_wheelhouses = _create_profile_wheelhouse_views(
            plans=plans,
            artifacts=artifacts,
            views_root=views_root,
            bootstrap_artifacts=bootstrap_artifacts,
        )
        for plan in plans:
            _assert_lock_input_plan(plan)

        with tempfile.TemporaryDirectory(
            prefix="offline-home-",
            dir=transaction_root,
        ) as offline_home_dir:
            offline_home = Path(offline_home_dir)
            os.chmod(offline_home, 0o700)
            if (offline_home / ".netrc").exists():
                raise RuntimeError("Offline resolver HOME unexpectedly contains .netrc.")
            prepared: list[PreparedLock] = []
            replaced: list[PreparedLock] = []
            try:
                for plan in plans:
                    profile = plan.surface.compile_profile
                    if profile is None:
                        raise RuntimeError("Compiled dependency surface has no profile.")
                    profile_wheelhouse = profile_wheelhouses[profile]
                    offline_env = _offline_compile_env(
                        environment,
                        resolver_home=offline_home,
                        wheelhouse=profile_wheelhouse.path,
                    )
                    prepared.append(
                        _prepare_lock(
                            repo_root=repo_root,
                            surface=plan.surface,
                            upgrades=upgrades,
                            graph_changes=graph_changes,
                            child_env=offline_env,
                            input_plan=plan,
                            wheel_artifacts=profile_wheelhouse.artifacts,
                        )
                    )
                for candidate in prepared:
                    for path, snapshot in candidate.source_snapshots:
                        _assert_snapshot(path, snapshot)
                    _assert_snapshot(candidate.output_path, candidate.output_snapshot)
                    _assert_snapshot(candidate.candidate_path, candidate.candidate_snapshot)
                try:
                    for candidate in prepared:
                        _assert_snapshot(candidate.candidate_path, candidate.candidate_snapshot)
                        # Record the attempted replacement before the atomic rename so an
                        # interrupt immediately after os.replace cannot strand a partial
                        # multi-lock transaction outside the rollback set.
                        replaced.append(candidate)
                        os.replace(candidate.candidate_path, candidate.output_path)
                        _fsync_directory(candidate.output_path.parent)
                        _assert_snapshot(candidate.output_path, candidate.candidate_snapshot)
                    for candidate in prepared:
                        print(
                            "Updated governed lock profile "
                            f"{candidate.surface.compile_profile}: {candidate.surface.lockfile}"
                        )
                except BaseException as replacement_error:
                    rollback_errors: list[str] = []
                    for candidate in reversed(replaced):
                        try:
                            _atomic_write_bytes(
                                candidate.output_path,
                                candidate.baseline_bytes,
                                candidate.output_snapshot.mode,
                            )
                        except (
                            BaseException
                        ) as rollback_error:  # pragma: no cover - catastrophic FS fault
                            rollback_errors.append(
                                f"{candidate.surface.lockfile}: " f"{type(rollback_error).__name__}"
                            )
                    if rollback_errors:
                        raise RuntimeError(
                            "Lock replacement failed and rollback was incomplete: "
                            + ", ".join(rollback_errors)
                        ) from replacement_error
                    if not isinstance(replacement_error, Exception):
                        raise
                    raise RuntimeError(
                        "Lock replacement failed; all previously replaced locks were rolled back."
                    ) from replacement_error
            finally:
                for candidate in prepared:
                    candidate.candidate_path.unlink(missing_ok=True)


def main() -> int:
    if os.environ.get(MAKE_AUTHORITY_ENV) != "1":
        raise RuntimeError(
            "Direct lock compiler invocation is forbidden; use make requirements-locks."
        )
    profiles = _parse_profiles(os.environ.get(PROFILE_SELECTION_ENV))
    upgrades = _parse_upgrades(os.environ.get(UPGRADE_SELECTION_ENV))
    graph_changes = _parse_graph_changes(os.environ.get(GRAPH_CHANGE_SELECTION_ENV))
    compile_selected_profiles(
        repo_root=REPO_ROOT,
        profiles=profiles,
        upgrades=upgrades,
        graph_changes=graph_changes,
        environment=os.environ,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

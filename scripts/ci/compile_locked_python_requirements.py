#!/usr/bin/env python3
"""Compile registry-owned Python locks through the approved private proxy.

This module is the implementation behind ``make requirements-locks``.  It is
not a second dependency-surface registry: profile, source, and output ownership
come from ``check_python_dependency_surfaces.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess  # nosec B404: argv-only governed pip-tools invocation (remove-by: 2027-01-31, ref: PR-2142)
import sys
import tempfile
from typing import Mapping, Sequence
from urllib.parse import urlparse

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_private_python_proxy_health import (  # noqa: E402
    basic_auth_from_netrc,
    redact_text,
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
PROFILE_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXACT_UPGRADE_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==" r"(?P<version>[A-Za-z0-9][A-Za-z0-9._+!~-]*)$"
)
AMBIENT_RESOLVER_ENV_VARS = (
    "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL",
    "PIP_CONFIG_FILE",
    "PIP_FIND_LINKS",
    "PIP_NO_INDEX",
    "PIP_TRUSTED_HOST",
    "PIP_CERT",
    "PIP_CLIENT_CERT",
    "UV_INDEX",
    "UV_INDEX_URL",
    "UV_DEFAULT_INDEX",
    "UV_EXTRA_INDEX_URL",
    "UV_FIND_LINKS",
    "UV_NO_INDEX",
    "UV_INSECURE_HOST",
)
PASSTHROUGH_ENV_VARS = (
    "HOME",
    "PATH",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
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
    return frozenset(packages)


def _capture_file(path: Path) -> FileCapture:
    """Read one regular file through a no-follow descriptor and bind bytes to identity."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
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
            "Ambient pip/uv resolver controls are forbidden for lock compilation: "
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


def _write_private_capture(path: Path, capture: FileCapture) -> FileSnapshot:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(capture.content)
        output.flush()
        os.fsync(output.fileno())
    return _snapshot(path)


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
    resolver_netrc = resolver_home / ".netrc"
    materialized_snapshot: FileSnapshot | None = None
    if netrc_capture is not None:
        materialized_snapshot = _write_private_capture(resolver_netrc, netrc_capture)
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
            "PIP_NO_INPUT": "1",
        }
    )
    child_env["HOME"] = str(resolver_home)
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
) -> PreparedLock:
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
    source_snapshots = tuple((path, capture.snapshot) for path, capture in source_captures.items())

    output_capture = _capture_file(output_path)
    baseline_bytes = output_capture.content
    baseline_text = baseline_bytes.decode("utf-8")
    baseline_pins = _exact_pin_map(baseline_text, label=f"{surface.lockfile} baseline")
    for package in upgrades:
        if package not in baseline_pins and package not in graph_changes:
            raise RuntimeError(
                f"{surface.lockfile}: requested upgrade package is absent from the seeded lock: "
                f"{package}"
            )

    output_snapshot = output_capture.snapshot
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".candidate",
        dir=output_path.parent,
    )
    candidate_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as candidate_file:
            candidate_file.write(baseline_bytes)
            candidate_file.flush()
            os.fsync(candidate_file.fileno())
        os.chmod(candidate_path, output_snapshot.mode)
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
                output_path=candidate_path,
                upgrades=upgrades,
            )
            process_env = dict(child_env)
            process_env["CUSTOM_COMPILE_COMMAND"] = (
                f'LOCK_PROFILES="{surface.compile_profile}" make requirements-locks'
            )
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
            for path, snapshot in materialized_snapshots:
                _assert_snapshot(path, snapshot)
            for path, snapshot in source_snapshots:
                _assert_snapshot(path, snapshot)
            _assert_snapshot(output_path, output_snapshot)

            candidate_body = candidate_path.read_text(encoding="utf-8").lstrip("\n")
            rendered = render_governed_lock_header(surface) + candidate_body
            _validate_candidate_delta(
                surface=surface,
                baseline_text=baseline_text,
                candidate_text=rendered,
                upgrades=upgrades,
                graph_changes=graph_changes,
                repo_root=resolver_input_root,
            )
        with candidate_path.open("w", encoding="utf-8", newline="\n") as candidate_file:
            candidate_file.write(rendered)
            candidate_file.flush()
            os.fsync(candidate_file.fileno())
        candidate_snapshot = _snapshot(candidate_path)
        return PreparedLock(
            surface=surface,
            output_path=output_path,
            candidate_path=candidate_path,
            source_snapshots=source_snapshots,
            output_snapshot=output_snapshot,
            candidate_snapshot=candidate_snapshot,
            baseline_bytes=baseline_bytes,
        )
    except Exception:
        candidate_path.unlink(missing_ok=True)
        raise


def _validate_profile_transaction(
    *,
    repo_root: Path,
    profiles: Sequence[str],
    graph_changes: frozenset[str],
) -> None:
    if graph_changes and len(profiles) != 1:
        raise RuntimeError(
            "GRAPH_CHANGE_PACKAGES requires exactly one LOCK_PROFILES entry so every "
            "graph delta is reviewed and committed per owning profile."
        )
    if "runtime" not in profiles:
        return
    registry = _profile_registry()
    dependent_profiles: list[str] = []
    for profile in profiles:
        if profile == "runtime":
            continue
        for source in registry[profile].compile_sources:
            source_path = _validated_repo_file(repo_root, source)
            for raw_line in source_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.split("#", 1)[0].strip()
                if line in ("-c requirements.txt", "--constraint requirements.txt"):
                    dependent_profiles.append(profile)
                    break
            if profile in dependent_profiles:
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
    registry = _profile_registry()
    _validate_profile_transaction(
        repo_root=repo_root,
        profiles=profiles,
        graph_changes=graph_changes,
    )
    with tempfile.TemporaryDirectory(prefix="pulseplate-lock-home-") as home_dir:
        resolver_home = Path(home_dir)
        child_env = _private_proxy_child_env(environment, resolver_home=resolver_home)
        prepared: list[PreparedLock] = []
        replaced: list[PreparedLock] = []
        try:
            for profile in profiles:
                prepared.append(
                    _prepare_lock(
                        repo_root=repo_root,
                        surface=registry[profile],
                        upgrades=upgrades,
                        graph_changes=graph_changes,
                        child_env=child_env,
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
                    os.replace(candidate.candidate_path, candidate.output_path)
                    replaced.append(candidate)
                    _fsync_directory(candidate.output_path.parent)
                for candidate in prepared:
                    print(
                        "Updated governed lock profile "
                        f"{candidate.surface.compile_profile}: {candidate.surface.lockfile}"
                    )
            except Exception as replacement_error:
                rollback_errors: list[str] = []
                for candidate in reversed(replaced):
                    try:
                        _atomic_write_bytes(
                            candidate.output_path,
                            candidate.baseline_bytes,
                            candidate.output_snapshot.mode,
                        )
                    except Exception as rollback_error:  # pragma: no cover - catastrophic FS fault
                        rollback_errors.append(
                            f"{candidate.surface.lockfile}: {type(rollback_error).__name__}"
                        )
                if rollback_errors:
                    raise RuntimeError(
                        "Lock replacement failed and rollback was incomplete: "
                        + ", ".join(rollback_errors)
                    ) from replacement_error
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

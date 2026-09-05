"""Exact, bounded repository context materialization for role dispatch.

This module owns one finite operation: read an explicitly selected ordered set
of repository files without following links and prove that every source still
matches before returning a complete result. It does not discover context,
authenticate task packets, persist content, or grant role, review, write, or
merge authority.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

DELIVERY_SCHEMA_VERSION = "pulseplate.role-context-delivery.v1"
OUTPUT_SCHEMA_VERSION = "pulseplate.role-context-output.v1"
POLICY_VERSION = "exact-context-materializer.policy.v1"
MAX_SOURCES = 128
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 8 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
DECLARED_SKILL_ROOTS = (
    PurePosixPath(".agents/skills"),
    PurePosixPath("tools/codex_skills"),
)
_SENSITIVE_FILENAMES = frozenset(
    {
        ".netrc",
        "credentials",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
    }
)
_SENSITIVE_SUFFIXES = frozenset({".key", ".p12", ".pfx", ".pem"})


class ContextBundleError(ValueError):
    """Stable fail-closed error for a required exact-context source."""

    def __init__(self, code: str, path: str | None = None) -> None:
        self.code = code
        self.path = path
        detail = code if path is None else f"{code}: {path}"
        super().__init__(detail)


class UnsupportedContextSource(ContextBundleError):
    """A closed-world input requires an explicit manual loading route."""


@dataclass(frozen=True)
class SourceIdentity:
    """Metadata used to reject replacement or mutation across the operation."""

    device: int
    inode: int
    mode: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class SourceSnapshot:
    """One safely acquired exact repository source."""

    path: str
    raw: bytes
    identity: SourceIdentity

    @property
    def text(self) -> str:
        try:
            text = self.raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ContextBundleError("SOURCE_NOT_UTF8", self.path) from exc
        return text


@dataclass
class ContextIOMetrics:
    """Operation-local counters kept outside semantic context content."""

    source_opens: int = 0
    source_bytes_read: int = 0
    freshness_opens: int = 0
    freshness_bytes_read: int = 0
    parses: int = 0
    assemblies: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "source_opens": self.source_opens,
            "source_bytes_read": self.source_bytes_read,
            "freshness_opens": self.freshness_opens,
            "freshness_bytes_read": self.freshness_bytes_read,
            "parses": self.parses,
            "assemblies": self.assemblies,
        }


def _required_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise ContextBundleError("SAFE_READ_UNAVAILABLE")
    return value


def canonical_repo_path(raw_path: str) -> str:
    """Validate one exact canonical repo-relative POSIX path."""

    if (
        not isinstance(raw_path, str)
        or not raw_path
        or raw_path != raw_path.strip()
        or "\\" in raw_path
        or any(ord(character) < 32 or ord(character) == 127 for character in raw_path)
    ):
        raise ContextBundleError("INVALID_SOURCE_PATH")
    if any(character in raw_path for character in "*?["):
        raise UnsupportedContextSource("UNSUPPORTED_SOURCE_PATTERN", raw_path)
    candidate = PurePosixPath(raw_path)
    if (
        candidate.is_absolute()
        or candidate.as_posix() != raw_path
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise ContextBundleError("INVALID_SOURCE_PATH", raw_path)
    return raw_path


def repo_relative_input(repo_root: Path, raw_path: str) -> str:
    """Convert an explicit packet CLI path to canonical repo-relative syntax."""

    candidate = Path(raw_path)
    if candidate.is_absolute():
        try:
            raw_path = candidate.relative_to(repo_root).as_posix()
        except ValueError as exc:
            raise ContextBundleError("SOURCE_OUTSIDE_REPOSITORY") from exc
    return canonical_repo_path(raw_path)


def _identity(metadata: os.stat_result) -> SourceIdentity:
    return SourceIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        links=metadata.st_nlink,
        size=metadata.st_size,
        modified_ns=metadata.st_mtime_ns,
        changed_ns=metadata.st_ctime_ns,
    )


def _close_descriptors(descriptors: Iterable[int]) -> None:
    for descriptor in reversed(list(descriptors)):
        if descriptor >= 0:
            os.close(descriptor)


def read_repo_source(
    repo_root: Path,
    raw_path: str,
    *,
    metrics: ContextIOMetrics,
    freshness: bool = False,
    limit: int = MAX_SOURCE_BYTES,
) -> SourceSnapshot:
    """Read one bounded regular file through a no-follow descriptor walk."""

    path = canonical_repo_path(raw_path)
    parts = PurePosixPath(path).parts
    directory_flags = (
        os.O_RDONLY
        | _required_flag("O_DIRECTORY")
        | _required_flag("O_NOFOLLOW")
        | _required_flag("O_CLOEXEC")
    )
    file_flags = (
        os.O_RDONLY
        | _required_flag("O_NOFOLLOW")
        | _required_flag("O_CLOEXEC")
        | _required_flag("O_NONBLOCK")
    )
    directory_fds: list[int] = []
    file_fd = -1
    try:
        directory_fds.append(os.open(repo_root, directory_flags))
        for component in parts[:-1]:
            directory_fds.append(os.open(component, directory_flags, dir_fd=directory_fds[-1]))
        parent_fd = directory_fds[-1]
        path_metadata = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISDIR(path_metadata.st_mode):
            raise UnsupportedContextSource("UNSUPPORTED_SOURCE_DIRECTORY", path)
        if stat.S_ISLNK(path_metadata.st_mode):
            raise ContextBundleError("UNSAFE_SOURCE_LINK", path)
        if not stat.S_ISREG(path_metadata.st_mode) or path_metadata.st_nlink != 1:
            raise ContextBundleError("UNSAFE_SOURCE_TYPE", path)
        if path_metadata.st_size > limit:
            raise ContextBundleError("SOURCE_TOO_LARGE", path)
        file_fd = os.open(parts[-1], file_flags, dir_fd=parent_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ContextBundleError("UNSAFE_SOURCE_TYPE", path)
        if before.st_size > limit:
            raise ContextBundleError("SOURCE_TOO_LARGE", path)
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining > 0:
            chunk = os.read(file_fd, min(READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(file_fd)
        final_path_metadata = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
    except UnsupportedContextSource:
        raise
    except ContextBundleError:
        raise
    except FileNotFoundError as exc:
        raise ContextBundleError("SOURCE_MISSING", path) from exc
    except OSError as exc:
        raise ContextBundleError("UNSAFE_SOURCE_READ", path) from exc
    finally:
        if file_fd >= 0:
            os.close(file_fd)
        _close_descriptors(directory_fds)

    before_identity = _identity(before)
    after_identity = _identity(after)
    final_path_identity = _identity(final_path_metadata)
    if (
        len(raw) > limit
        or before.st_size != len(raw)
        or before_identity != after_identity
        or after_identity != final_path_identity
        or not stat.S_ISREG(final_path_metadata.st_mode)
        or final_path_metadata.st_nlink != 1
    ):
        raise ContextBundleError("SOURCE_CHANGED_DURING_READ", path)
    if freshness:
        metrics.freshness_opens += 1
        metrics.freshness_bytes_read += len(raw)
    else:
        metrics.source_opens += 1
        metrics.source_bytes_read += len(raw)
    snapshot = SourceSnapshot(path=path, raw=raw, identity=after_identity)
    snapshot.text
    return snapshot


def capture_sources(
    repo_root: Path,
    ordered_paths: Iterable[str],
    *,
    metrics: ContextIOMetrics,
    existing: Mapping[str, SourceSnapshot] | None = None,
) -> tuple[list[str], dict[str, SourceSnapshot]]:
    """Capture a deduplicated finite inventory in first-occurrence order."""

    ordered: list[str] = []
    snapshots = dict(existing or {})
    if len(snapshots) > MAX_SOURCES:
        raise ContextBundleError("TOO_MANY_SOURCES")
    retained_bytes = 0
    for path, snapshot in snapshots.items():
        canonical_path = canonical_repo_path(path)
        if not isinstance(snapshot, SourceSnapshot) or snapshot.path != canonical_path:
            raise ContextBundleError("INVALID_SOURCE_SNAPSHOT", path)
        if len(snapshot.raw) > MAX_SOURCE_BYTES:
            raise ContextBundleError("SOURCE_TOO_LARGE", path)
        retained_bytes += len(snapshot.raw)
        if retained_bytes > MAX_TOTAL_SOURCE_BYTES:
            raise ContextBundleError("TOTAL_SOURCE_BYTES_EXCEEDED")
    for raw_path in ordered_paths:
        path = canonical_repo_path(raw_path)
        if path in ordered:
            continue
        if path in snapshots:
            snapshot = snapshots[path]
        else:
            if len(snapshots) >= MAX_SOURCES:
                raise ContextBundleError("TOO_MANY_SOURCES")
            remaining = MAX_TOTAL_SOURCE_BYTES - retained_bytes
            if remaining <= 0:
                raise ContextBundleError("TOTAL_SOURCE_BYTES_EXCEEDED")
            try:
                snapshot = read_repo_source(
                    repo_root,
                    path,
                    metrics=metrics,
                    limit=min(MAX_SOURCE_BYTES, remaining),
                )
            except ContextBundleError as exc:
                if exc.code == "SOURCE_TOO_LARGE" and remaining < MAX_SOURCE_BYTES:
                    raise ContextBundleError("TOTAL_SOURCE_BYTES_EXCEEDED") from exc
                raise
            snapshots[path] = snapshot
            retained_bytes += len(snapshot.raw)
        ordered.append(path)
    return ordered, snapshots


def validate_instruction_file(path: str, selected_paths: Iterable[str]) -> str:
    """Admit only explicit Markdown instructions from a fixed repo surface."""

    normalized = canonical_repo_path(path)
    candidate = PurePosixPath(normalized)
    if candidate.suffix.casefold() != ".md":
        raise ContextBundleError("INSTRUCTION_FILE_MUST_BE_MARKDOWN", normalized)
    if normalized in set(selected_paths):
        return normalized
    if not any(candidate.is_relative_to(root) for root in DECLARED_SKILL_ROOTS):
        raise ContextBundleError("INSTRUCTION_FILE_OUTSIDE_DECLARED_ROOTS", normalized)
    return normalized


def validate_static_source_path(path: str) -> str:
    """Reject source classes that must stay fresh and outside reusable payloads."""

    if isinstance(path, str) and any(character in path for character in "*?["):
        return path
    normalized = canonical_repo_path(path)
    candidate = PurePosixPath(normalized)
    lowered_parts = tuple(part.casefold() for part in candidate.parts)
    filename = lowered_parts[-1]
    if (
        lowered_parts[0] in {"artifacts", "cache", "data", "logs"}
        or any(part in {".git", ".venv", "logs", "node_modules"} for part in lowered_parts)
        or filename == ".env"
        or filename.startswith(".env.")
        or filename in _SENSITIVE_FILENAMES
        or candidate.suffix.casefold() in _SENSITIVE_SUFFIXES
    ):
        raise ContextBundleError("STATIC_SOURCE_FORBIDDEN", normalized)
    return normalized


def _semantic_digest(ordered: Iterable[SourceSnapshot]) -> str:
    digest = hashlib.sha256()
    digest.update(POLICY_VERSION.encode("ascii"))
    for snapshot in ordered:
        path = snapshot.path.encode("utf-8")
        digest.update(len(path).to_bytes(8, "big"))
        digest.update(path)
        digest.update(len(snapshot.raw).to_bytes(8, "big"))
        digest.update(snapshot.raw)
    return "sha256:" + digest.hexdigest()


def materialize_context_bundle(
    repo_root: Path,
    *,
    occurrence: int,
    ordered_source_paths: Iterable[str],
    bracket_paths: Iterable[str],
    initial_snapshots: Mapping[str, SourceSnapshot] | None,
    dynamic_packet_path: str | None,
    metrics: ContextIOMetrics,
) -> dict[str, Any]:
    """Return one complete current context delivery or an explicit manual route."""

    bracket_path_list = list(bracket_paths)
    if dynamic_packet_path is not None and dynamic_packet_path not in bracket_path_list:
        bracket_path_list.append(dynamic_packet_path)
    initial = dict(initial_snapshots or {})
    try:
        ordered_paths, snapshots = capture_sources(
            repo_root,
            ordered_source_paths,
            metrics=metrics,
            existing=initial_snapshots,
        )
        all_bracket_paths, snapshots = capture_sources(
            repo_root,
            [*bracket_path_list, *ordered_paths],
            metrics=metrics,
            existing=snapshots,
        )
    except UnsupportedContextSource as exc:
        for path in bracket_path_list:
            if path not in initial:
                continue
            current = read_repo_source(repo_root, path, metrics=metrics, freshness=True)
            if current != initial[path]:
                raise ContextBundleError("SOURCE_CHANGED", path) from exc
        return {
            "schema_version": DELIVERY_SCHEMA_VERSION,
            "complete": False,
            "role_context_order": occurrence,
            "manual_loading_required": True,
            "reason": exc.code,
            "path": exc.path,
        }

    ordered_snapshots = [snapshots[path] for path in ordered_paths]
    if dynamic_packet_path is not None:
        dynamic_identity = snapshots[dynamic_packet_path].identity
        for snapshot in ordered_snapshots:
            if (
                snapshot.identity.device,
                snapshot.identity.inode,
            ) == (dynamic_identity.device, dynamic_identity.inode):
                raise ContextBundleError(
                    "DYNAMIC_PACKET_SELECTED_AS_STATIC_OBJECT",
                    snapshot.path,
                )
    for path in all_bracket_paths:
        current = read_repo_source(repo_root, path, metrics=metrics, freshness=True)
        if current != snapshots[path]:
            raise ContextBundleError("SOURCE_CHANGED", path)

    metrics.assemblies += 1
    dynamic_packet: dict[str, str] | None = None
    if dynamic_packet_path is not None:
        packet = snapshots[dynamic_packet_path]
        dynamic_packet = {"path": packet.path, "content": packet.text}
    return {
        "schema_version": DELIVERY_SCHEMA_VERSION,
        "complete": True,
        "role_context_order": occurrence,
        "semantic_payload_sha256": _semantic_digest(ordered_snapshots),
        "sources": [
            {"path": snapshot.path, "content": snapshot.text} for snapshot in ordered_snapshots
        ],
        "dynamic_packet": dynamic_packet,
    }

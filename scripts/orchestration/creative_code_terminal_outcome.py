"""Build and validate immutable local creative-code terminal outcomes."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import errno
import os
from pathlib import Path
import stat
import tempfile
import threading
import time
from typing import Any

from scripts.orchestration.creative_code_terminal_outcome_contract import (
    CreativeCodeTerminalOutcomeError,
    MAX_EVIDENCE_PROJECTION_BYTES,
    MAX_JSON_OBJECT_BYTES,
    build_terminal_evidence_events,
    build_creative_code_terminal_outcome,
    canonical_json_bytes,
    decode_terminal_outcome_bytes,
    read_json_object,
    terminal_evidence_projection_bytes,
    validate_creative_code_terminal_outcome,
    validate_terminal_evidence_projection,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
TERMINAL_OUTCOMES_ROOT = CREATIVE_CODE_ROOT / "terminal_outcomes"
OUTCOME_FILE = "terminal_outcome.json"
EVIDENCE_EVENTS_FILE = "evidence_events.json"
SUCCESS_BUILD_OUTPUT = "PASS: creative-code terminal outcome built"
SUCCESS_VALIDATE_OUTPUT = "PASS: creative-code terminal outcome valid"
SUCCESS_PROJECT_OUTPUT = "PASS: creative-code terminal evidence projected"
SUCCESS_VALIDATE_PROJECTION_OUTPUT = "PASS: creative-code terminal evidence projection valid"
_EVIDENCE_PROJECTION_PUBLISH_LOCK = threading.Lock()
_COLLISION_STABILIZATION_ATTEMPTS = 100
_COLLISION_STABILIZATION_DELAY_SECONDS = 0.005


class CreativeCodeTerminalOutcomeIOError(ValueError):
    """Raised when terminal-outcome IO cannot stay immutable and contained."""


@dataclass(frozen=True)
class _RegularFileIdentity:
    device: int
    inode: int
    mode: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class _DirectoryIdentity:
    device: int
    inode: int
    mode: int


def _regular_file_identity(info: os.stat_result) -> _RegularFileIdentity:
    return _RegularFileIdentity(
        device=info.st_dev,
        inode=info.st_ino,
        mode=info.st_mode,
        links=info.st_nlink,
        size=info.st_size,
        modified_ns=info.st_mtime_ns,
        changed_ns=info.st_ctime_ns,
    )


def _is_collision_link_settled_during_open(
    path_identity: _RegularFileIdentity,
    descriptor_identity: _RegularFileIdentity,
) -> bool:
    """Recognize only a winner dropping its private link during loser open."""

    return (
        path_identity.links == 2
        and descriptor_identity.links == 1
        and path_identity.device == descriptor_identity.device
        and path_identity.inode == descriptor_identity.inode
        and path_identity.mode == descriptor_identity.mode
        and path_identity.size == descriptor_identity.size
        and path_identity.modified_ns == descriptor_identity.modified_ns
    )


def _directory_identity(info: os.stat_result) -> _DirectoryIdentity:
    return _DirectoryIdentity(device=info.st_dev, inode=info.st_ino, mode=info.st_mode)


def _close_owned_descriptor_once(
    descriptor: int,
    *,
    error_label: str,
) -> BaseException | None:
    """Attempt one close after the caller has invalidated local ownership."""

    try:
        os.close(descriptor)
    except OSError as exc:
        error = CreativeCodeTerminalOutcomeIOError(error_label)
        error.__cause__ = exc
        return error
    except BaseException as exc:
        return exc
    return None


def _existing_components(path: Path) -> list[Path]:
    components: list[Path] = []
    current = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current = current / part
        if current.exists() or current.is_symlink():
            components.append(current)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_symlink_rejected")


def _resolve_contained_input(
    path: Path,
    *,
    label: str,
    allowed_root: Path,
) -> Path:
    if ".." in path.parts:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_traversal_rejected")
    root_path = allowed_root if allowed_root.is_absolute() else Path.cwd() / allowed_root
    _reject_symlink_components(root_path, label=f"{label}_root")
    try:
        resolved_root = root_path.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_root_read_failed") from exc
    if not resolved_root.is_dir():
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_root_must_be_directory")

    candidate = path if path.is_absolute() else Path.cwd() / path
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_outside_allowed_root") from exc
    _reject_symlink_components(candidate, label=label)
    try:
        resolved_candidate = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_read_failed") from exc
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_outside_allowed_root") from exc
    return resolved_candidate


def _read_regular_json(
    path: Path,
    *,
    label: str,
    allowed_root: Path = CREATIVE_CODE_ROOT,
) -> dict[str, Any]:
    contained = _resolve_contained_input(
        path,
        label=label,
        allowed_root=allowed_root,
    )
    try:
        info = contained.stat()
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_read_failed") from exc
    if not stat.S_ISREG(info.st_mode):
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_must_be_regular")
    if info.st_size > MAX_JSON_OBJECT_BYTES:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_too_large")
    payload: dict[str, Any] = read_json_object(contained)
    return payload


def _read_bounded_regular_bytes(
    path: Path,
    *,
    label: str,
    max_bytes: int,
    require_single_link: bool,
    required_mode: int | None = None,
) -> tuple[bytes, _RegularFileIdentity]:
    try:
        path_info = path.lstat()
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_read_failed") from exc
    if not stat.S_ISREG(path_info.st_mode):
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_must_be_regular")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_read_failed") from exc
    result: tuple[bytes, _RegularFileIdentity] | None = None
    primary_error: BaseException | None = None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_must_be_regular")
        path_identity = _regular_file_identity(path_info)
        before_identity = _regular_file_identity(before)
        if path_identity != before_identity:
            if _is_collision_link_settled_during_open(path_identity, before_identity):
                raise CreativeCodeTerminalOutcomeIOError(
                    f"{label}_collision_link_settled_during_open"
                )
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_changed_during_read")
        if require_single_link and before.st_nlink != 1:
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_hardlink_rejected")
        if required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode:
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_mode_invalid")
        if before.st_size > max_bytes:
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_too_large")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > max_bytes:
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_too_large")
        after = os.fstat(descriptor)
        if _regular_file_identity(after) != before_identity or len(raw) != before.st_size:
            raise CreativeCodeTerminalOutcomeIOError(f"{label}_changed_during_read")
        result = (raw, before_identity)
    except OSError as exc:
        primary_error = CreativeCodeTerminalOutcomeIOError(f"{label}_read_failed")
        primary_error.__cause__ = exc
    except BaseException as exc:
        primary_error = exc
    owned_descriptor = descriptor
    descriptor = -1
    close_error = _close_owned_descriptor_once(
        owned_descriptor,
        error_label=f"{label}_read_failed",
    )
    if primary_error is not None:
        if close_error is not None:
            raise primary_error from close_error
        raise primary_error
    if close_error is not None:
        raise close_error
    if result is None:
        raise CreativeCodeTerminalOutcomeIOError(f"{label}_read_failed")
    return result


def _recheck_projection_source_identity(
    *,
    outcome_path: Path,
    outcome_identity: _RegularFileIdentity,
    parent_identity: _DirectoryIdentity,
) -> None:
    _reject_symlink_components(outcome_path, label="terminal_outcome")
    try:
        path_info = outcome_path.lstat()
        parent_info = outcome_path.parent.lstat()
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(
            "terminal_outcome_changed_before_projection"
        ) from exc
    if (
        not stat.S_ISREG(path_info.st_mode)
        or path_info.st_nlink != 1
        or _regular_file_identity(path_info) != outcome_identity
        or not stat.S_ISDIR(parent_info.st_mode)
        or _directory_identity(parent_info) != parent_identity
    ):
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_changed_before_projection")


def _load_canonical_projection_outcome(
    outcome_path: Path,
    *,
    terminal_outcomes_root: Path,
) -> tuple[dict[str, Any], Path, _RegularFileIdentity, _DirectoryIdentity]:
    if outcome_path.name != OUTCOME_FILE:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_wrong_basename")
    resolved = _resolve_contained_input(
        outcome_path,
        label="terminal_outcome",
        allowed_root=terminal_outcomes_root,
    )
    raw, identity = _read_bounded_regular_bytes(
        resolved,
        label="terminal_outcome",
        max_bytes=MAX_JSON_OBJECT_BYTES,
        require_single_link=True,
    )
    try:
        outcome = decode_terminal_outcome_bytes(raw)
        normalized = validate_creative_code_terminal_outcome(outcome)
    except CreativeCodeTerminalOutcomeError:
        raise
    root_path = (
        terminal_outcomes_root
        if terminal_outcomes_root.is_absolute()
        else Path.cwd() / terminal_outcomes_root
    )
    canonical = root_path.resolve(strict=True) / normalized["outcome_id"] / OUTCOME_FILE
    if resolved != canonical:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_noncanonical_path")
    try:
        parent_info = resolved.parent.lstat()
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_parent_read_failed") from exc
    if not stat.S_ISDIR(parent_info.st_mode):
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_parent_must_be_directory")
    return normalized, resolved, identity, _directory_identity(parent_info)


def _ensure_output_root(root: Path) -> Path:
    _reject_symlink_components(root, label="terminal_outcomes_root")
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcomes_root_create_failed") from exc
    _reject_symlink_components(root, label="terminal_outcomes_root")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcomes_root_must_be_directory")
    return resolved


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("directory_fsync_open_failed") from exc
    primary_error: BaseException | None = None
    try:
        os.fsync(descriptor)
    except OSError as exc:
        primary_error = CreativeCodeTerminalOutcomeIOError("directory_fsync_failed")
        primary_error.__cause__ = exc
    except BaseException as exc:
        primary_error = exc
    owned_descriptor = descriptor
    descriptor = -1
    close_error = _close_owned_descriptor_once(
        owned_descriptor,
        error_label="directory_fsync_failed",
    )
    if primary_error is not None:
        if close_error is not None:
            raise primary_error from close_error
        raise primary_error
    if close_error is not None:
        raise close_error


def _read_existing_bytes(target_dir: Path, target_file: Path) -> bytes:
    _reject_symlink_components(target_dir, label="terminal_outcome")
    if not target_dir.is_dir():
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_target_must_be_directory")
    if not target_file.exists():
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_publication_incomplete")
    _reject_symlink_components(target_file, label="terminal_outcome")
    try:
        info = target_file.stat()
        if not stat.S_ISREG(info.st_mode):
            raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_target_must_be_regular")
        if info.st_size > MAX_JSON_OBJECT_BYTES:
            raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_target_too_large")
        with target_file.open("rb") as handle:
            content = handle.read(MAX_JSON_OBJECT_BYTES + 1)
        if len(content) > MAX_JSON_OBJECT_BYTES:
            raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_target_too_large")
        if len(content) != info.st_size:
            raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_target_changed_during_read")
        return content
    except CreativeCodeTerminalOutcomeIOError:
        raise
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_read_failed") from exc


def _link_staging_file_noreplace(staging_file: Path, target_file: Path) -> None:
    """Linearize one canonical file identity without replacement."""

    try:
        os.link(staging_file, target_file, follow_symlinks=False)
    except FileExistsError:
        raise
    except OSError as exc:
        unsupported = {
            errno.EXDEV,
            errno.EPERM,
            getattr(errno, "ENOTSUP", errno.EPERM),
            getattr(errno, "EOPNOTSUPP", errno.EPERM),
        }
        if exc.errno in unsupported:
            raise CreativeCodeTerminalOutcomeIOError(
                "terminal_outcome_hardlink_unsupported"
            ) from exc
        raise CreativeCodeTerminalOutcomeIOError(
            f"terminal_outcome_link_failed_errno_{exc.errno}"
        ) from exc


def _read_namespace(
    *,
    target_dir: Path,
    target_file: Path,
) -> bytes | None:
    """Return canonical bytes, or accept only an empty crash-residue namespace."""

    _reject_symlink_components(target_dir, label="terminal_outcome")
    if not target_dir.is_dir():
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_target_must_be_directory")
    if target_file.exists() or target_file.is_symlink():
        return _read_existing_bytes(target_dir, target_file)
    try:
        entries = list(target_dir.iterdir())
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_namespace_read_failed") from exc
    if not entries:
        return None
    if target_file.exists() or target_file.is_symlink():
        return _read_existing_bytes(target_dir, target_file)
    raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_namespace_ambiguous")


def _create_or_reuse_namespace(
    *,
    target_dir: Path,
    target_file: Path,
) -> bytes | None:
    """Create the namespace, or reuse only a complete or empty one."""

    if target_dir.exists() or target_dir.is_symlink():
        return _read_namespace(target_dir=target_dir, target_file=target_file)
    try:
        target_dir.mkdir(mode=0o700)
    except FileExistsError:
        return _read_namespace(target_dir=target_dir, target_file=target_file)
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(
            "terminal_outcome_namespace_create_failed"
        ) from exc
    return None


def _validate_identical_replay(
    *,
    content: bytes,
    target_dir: Path,
    target_file: Path,
    root: Path,
) -> None:
    existing = _read_existing_bytes(target_dir, target_file)
    if existing != content:
        raise CreativeCodeTerminalOutcomeIOError("divergent_replay")
    _fsync_directory(target_dir)
    _fsync_directory(root)


def _cleanup_staging_file(staging_file: Path, *, root: Path) -> None:
    """Unlink only this attempt's hidden staging name, then persist removal."""

    try:
        staging_file.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_staging_cleanup_failed") from exc
    _fsync_directory(root)


def _read_existing_projection_bytes(
    target_file: Path,
) -> tuple[bytes, _RegularFileIdentity, _DirectoryIdentity]:
    _reject_symlink_components(target_file.parent, label="evidence_projection")
    try:
        parent_info = target_file.parent.lstat()
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("evidence_projection_parent_read_failed") from exc
    if not stat.S_ISDIR(parent_info.st_mode):
        raise CreativeCodeTerminalOutcomeIOError("evidence_projection_parent_must_be_directory")
    _reject_symlink_components(target_file, label="evidence_projection")
    raw, identity = _read_bounded_regular_bytes(
        target_file,
        label="evidence_projection",
        max_bytes=MAX_EVIDENCE_PROJECTION_BYTES,
        require_single_link=True,
        required_mode=0o600,
    )
    return raw, identity, _directory_identity(parent_info)


def _recheck_projection_sidecar_identity(
    *,
    target_file: Path,
    target_identity: _RegularFileIdentity,
    parent_identity: _DirectoryIdentity,
) -> None:
    _reject_symlink_components(target_file, label="evidence_projection")
    try:
        target_info = target_file.lstat()
        parent_info = target_file.parent.lstat()
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("evidence_projection_changed_after_read") from exc
    if (
        not stat.S_ISREG(target_info.st_mode)
        or target_info.st_nlink != 1
        or stat.S_IMODE(target_info.st_mode) != 0o600
        or _regular_file_identity(target_info) != target_identity
        or not stat.S_ISDIR(parent_info.st_mode)
        or _directory_identity(parent_info) != parent_identity
    ):
        raise CreativeCodeTerminalOutcomeIOError("evidence_projection_changed_after_read")


def _read_collision_winner_projection_bytes(
    target_file: Path,
) -> tuple[bytes, _RegularFileIdentity, _DirectoryIdentity]:
    """Wait boundedly for the winner to drop only its private staging link."""

    for attempt in range(_COLLISION_STABILIZATION_ATTEMPTS):
        try:
            return _read_existing_projection_bytes(target_file)
        except CreativeCodeTerminalOutcomeIOError as exc:
            if str(exc) not in {
                "evidence_projection_hardlink_rejected",
                "evidence_projection_collision_link_settled_during_open",
            }:
                raise
            if attempt + 1 == _COLLISION_STABILIZATION_ATTEMPTS:
                raise
            time.sleep(_COLLISION_STABILIZATION_DELAY_SECONDS)
    raise CreativeCodeTerminalOutcomeIOError("evidence_projection_hardlink_rejected")


def _write_projection_staging_file(parent: Path, content: bytes) -> Path:
    descriptor = -1
    raw_path = ""
    primary_error: BaseException | None = None
    try:
        descriptor, raw_path = tempfile.mkstemp(
            prefix=".evidence_events.",
            suffix=".staging",
            dir=parent,
        )
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise CreativeCodeTerminalOutcomeIOError("evidence_projection_staging_must_be_regular")
        if stat.S_IMODE(info.st_mode) != 0o600:
            raise CreativeCodeTerminalOutcomeIOError("evidence_projection_staging_mode_invalid")
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if count <= 0:
                raise CreativeCodeTerminalOutcomeIOError("evidence_projection_staging_write_failed")
            written += count
        os.fsync(descriptor)
    except CreativeCodeTerminalOutcomeIOError as exc:
        primary_error = exc
    except OSError as exc:
        primary_error = CreativeCodeTerminalOutcomeIOError("evidence_projection_staging_io_failed")
        primary_error.__cause__ = exc
    except BaseException as exc:
        primary_error = exc
    close_error: BaseException | None = None
    if descriptor >= 0:
        owned_descriptor = descriptor
        descriptor = -1
        close_error = _close_owned_descriptor_once(
            owned_descriptor,
            error_label="evidence_projection_staging_io_failed",
        )
    if primary_error is not None:
        cleanup_error: BaseException | None = None
        if raw_path:
            try:
                _cleanup_projection_staging(Path(raw_path))
            except BaseException as exc:
                cleanup_error = exc
        if close_error is not None:
            raise primary_error from close_error
        if cleanup_error is not None:
            raise primary_error from cleanup_error
        raise primary_error
    if close_error is not None:
        if raw_path:
            try:
                _cleanup_projection_staging(Path(raw_path))
            except BaseException as cleanup_error:
                raise close_error from cleanup_error
        raise close_error
    return Path(raw_path)


def _cleanup_projection_staging(staging_file: Path) -> None:
    try:
        staging_file.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError(
            "evidence_projection_staging_cleanup_failed"
        ) from exc
    _fsync_directory(staging_file.parent)


def _validate_existing_projection(
    *,
    outcome: dict[str, Any],
    target_file: Path,
    expected_content: bytes,
    collision_winner: bool = False,
) -> bool:
    reader = (
        _read_collision_winner_projection_bytes
        if collision_winner
        else _read_existing_projection_bytes
    )
    existing, target_identity, parent_identity = reader(target_file)
    validate_terminal_evidence_projection(outcome, existing)
    if existing != expected_content:
        raise CreativeCodeTerminalOutcomeIOError("divergent_replay")
    _recheck_projection_sidecar_identity(
        target_file=target_file,
        target_identity=target_identity,
        parent_identity=parent_identity,
    )
    return True


def _project_terminal_evidence_locked(
    *,
    outcome_path: Path,
    produced_at: str,
    terminal_outcomes_root: Path | None = None,
) -> tuple[Path, bool]:
    """Publish the single sibling evidence projection with atomic no-replace."""

    outcome_root = terminal_outcomes_root or TERMINAL_OUTCOMES_ROOT
    outcome, resolved, outcome_identity, parent_identity = _load_canonical_projection_outcome(
        outcome_path,
        terminal_outcomes_root=outcome_root,
    )
    events = build_terminal_evidence_events(outcome, produced_at=produced_at)
    content = terminal_evidence_projection_bytes(events)
    if len(content) > MAX_EVIDENCE_PROJECTION_BYTES:
        raise CreativeCodeTerminalOutcomeIOError("evidence_projection_too_large")
    target_file = resolved.parent / EVIDENCE_EVENTS_FILE
    if target_file.exists() or target_file.is_symlink():
        _validate_existing_projection(
            outcome=outcome,
            target_file=target_file,
            expected_content=content,
            collision_winner=True,
        )
        _fsync_directory(resolved.parent)
        _recheck_projection_source_identity(
            outcome_path=resolved,
            outcome_identity=outcome_identity,
            parent_identity=parent_identity,
        )
        return target_file, True

    staging_file: Path | None = None
    installed = False
    try:
        _recheck_projection_source_identity(
            outcome_path=resolved,
            outcome_identity=outcome_identity,
            parent_identity=parent_identity,
        )
        staging_file = _write_projection_staging_file(resolved.parent, content)
        _recheck_projection_source_identity(
            outcome_path=resolved,
            outcome_identity=outcome_identity,
            parent_identity=parent_identity,
        )
        try:
            _link_staging_file_noreplace(staging_file, target_file)
            installed = True
        except FileExistsError:
            installed = False
        try:
            _cleanup_projection_staging(staging_file)
        finally:
            staging_file = None
        if installed:
            _fsync_directory(resolved.parent)
            _validate_existing_projection(
                outcome=outcome,
                target_file=target_file,
                expected_content=content,
            )
            _recheck_projection_source_identity(
                outcome_path=resolved,
                outcome_identity=outcome_identity,
                parent_identity=parent_identity,
            )
            return target_file, False
        _validate_existing_projection(
            outcome=outcome,
            target_file=target_file,
            expected_content=content,
            collision_winner=True,
        )
        _fsync_directory(resolved.parent)
        _recheck_projection_source_identity(
            outcome_path=resolved,
            outcome_identity=outcome_identity,
            parent_identity=parent_identity,
        )
        return target_file, True
    finally:
        if staging_file is not None:
            _cleanup_projection_staging(staging_file)


def project_terminal_evidence(
    *,
    outcome_path: Path,
    produced_at: str,
    terminal_outcomes_root: Path | None = None,
) -> tuple[Path, bool]:
    """Serialize in-process publishers while retaining atomic filesystem install."""

    with _EVIDENCE_PROJECTION_PUBLISH_LOCK:
        return _project_terminal_evidence_locked(
            outcome_path=outcome_path,
            produced_at=produced_at,
            terminal_outcomes_root=terminal_outcomes_root,
        )


def validate_projected_terminal_evidence(
    *,
    outcome_path: Path,
    terminal_outcomes_root: Path | None = None,
) -> None:
    """Validate the canonical sibling projection without mutating either file."""

    outcome_root = terminal_outcomes_root or TERMINAL_OUTCOMES_ROOT
    outcome, resolved, outcome_identity, parent_identity = _load_canonical_projection_outcome(
        outcome_path,
        terminal_outcomes_root=outcome_root,
    )
    target_file = resolved.parent / EVIDENCE_EVENTS_FILE
    if not target_file.exists() and not target_file.is_symlink():
        raise CreativeCodeTerminalOutcomeIOError("evidence_projection_missing")
    raw, target_identity, sidecar_parent_identity = _read_collision_winner_projection_bytes(
        target_file
    )
    validate_terminal_evidence_projection(outcome, raw)
    _recheck_projection_sidecar_identity(
        target_file=target_file,
        target_identity=target_identity,
        parent_identity=sidecar_parent_identity,
    )
    _recheck_projection_source_identity(
        outcome_path=resolved,
        outcome_identity=outcome_identity,
        parent_identity=parent_identity,
    )


def publish_terminal_outcome(
    outcome: dict[str, Any],
    *,
    output_root: Path | None = None,
) -> tuple[Path, bool]:
    """Publish one canonical regular file; the directory is namespace only."""

    normalized = validate_creative_code_terminal_outcome(outcome)
    content = canonical_json_bytes(normalized)
    root = _ensure_output_root(output_root or TERMINAL_OUTCOMES_ROOT)
    outcome_id = normalized["outcome_id"]
    target_dir = root / outcome_id
    target_file = target_dir / OUTCOME_FILE
    existing = _create_or_reuse_namespace(
        target_dir=target_dir,
        target_file=target_file,
    )
    if existing is not None:
        if existing != content:
            raise CreativeCodeTerminalOutcomeIOError("divergent_replay")
        _fsync_directory(target_dir)
        _fsync_directory(root)
        return target_file, True

    staging_file: Path | None = None
    result: tuple[Path, bool] | None = None
    primary_error: Exception | None = None
    try:
        descriptor, raw_staging_file = tempfile.mkstemp(
            prefix=f".{outcome_id}.",
            suffix=".staging",
            dir=root,
        )
        staging_file = Path(raw_staging_file)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            _link_staging_file_noreplace(staging_file, target_file)
            replayed = False
        except FileExistsError:
            replayed = True
        _validate_identical_replay(
            content=content,
            target_dir=target_dir,
            target_file=target_file,
            root=root,
        )
        result = (target_file, replayed)
    except CreativeCodeTerminalOutcomeIOError as exc:
        primary_error = exc
    except OSError as exc:
        primary_error = CreativeCodeTerminalOutcomeIOError("terminal_outcome_staging_io_failed")
        primary_error.__cause__ = exc

    cleanup_error: Exception | None = None
    if staging_file is not None:
        try:
            _cleanup_staging_file(staging_file, root=root)
        except Exception as exc:
            cleanup_error = exc
    if primary_error is not None:
        if cleanup_error is not None:
            raise primary_error from cleanup_error
        raise primary_error
    if cleanup_error is not None:
        raise cleanup_error
    if result is None:
        raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_publish_incomplete")
    return result


def build_and_publish(
    *,
    promotion_plan_path: Path,
    promotion_receipt_path: Path,
    observation_path: Path,
    input_root: Path | None = None,
    output_root: Path | None = None,
) -> tuple[dict[str, Any], Path, bool]:
    """Read closed inputs, cross-bind lineage, then publish the immutable outcome."""

    allowed_root = input_root or CREATIVE_CODE_ROOT
    plan = _read_regular_json(
        promotion_plan_path,
        label="promotion_plan",
        allowed_root=allowed_root,
    )
    receipt = _read_regular_json(
        promotion_receipt_path,
        label="promotion_receipt",
        allowed_root=allowed_root,
    )
    observation = _read_regular_json(
        observation_path,
        label="observation",
        allowed_root=allowed_root,
    )
    outcome = build_creative_code_terminal_outcome(
        promotion_plan=plan,
        promotion_receipt=receipt,
        observation=observation,
    )
    path, replayed = publish_terminal_outcome(outcome, output_root=output_root)
    return outcome, path, replayed


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or validate local creative-code terminal outcomes."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--promotion-plan", required=True)
    build_parser.add_argument("--promotion-receipt", required=True)
    build_parser.add_argument("--observation", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--outcome", required=True)
    project_parser = subparsers.add_parser("project-evidence")
    project_parser.add_argument("--outcome", required=True)
    project_parser.add_argument("--produced-at", required=True)
    validate_projection_parser = subparsers.add_parser("validate-evidence-projection")
    validate_projection_parser.add_argument("--outcome", required=True)
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    input_root: Path | None = None,
    terminal_outcomes_root: Path | None = None,
) -> int:
    args = _parse_args(argv)
    outcome_root = terminal_outcomes_root or TERMINAL_OUTCOMES_ROOT
    try:
        if args.command == "build":
            outcome, _, replayed = build_and_publish(
                promotion_plan_path=Path(args.promotion_plan),
                promotion_receipt_path=Path(args.promotion_receipt),
                observation_path=Path(args.observation),
                input_root=input_root,
                output_root=outcome_root,
            )
            replay = "identical" if replayed else "new"
            print(f"{SUCCESS_BUILD_OUTPUT}: outcome_id={outcome['outcome_id']} replay={replay}")
            return 0
        if args.command == "project-evidence":
            path, replayed = project_terminal_evidence(
                outcome_path=Path(args.outcome),
                produced_at=args.produced_at,
                terminal_outcomes_root=outcome_root,
            )
            replay = "identical" if replayed else "new"
            print(f"{SUCCESS_PROJECT_OUTPUT}: path={path.name} replay={replay}")
            return 0
        if args.command == "validate-evidence-projection":
            validate_projected_terminal_evidence(
                outcome_path=Path(args.outcome),
                terminal_outcomes_root=outcome_root,
            )
            print(SUCCESS_VALIDATE_PROJECTION_OUTPUT)
            return 0
        outcome_path = Path(args.outcome)
        outcome = _read_regular_json(
            outcome_path,
            label="terminal_outcome",
            allowed_root=outcome_root,
        )
        normalized = validate_creative_code_terminal_outcome(outcome)
        resolved_outcome = _resolve_contained_input(
            outcome_path,
            label="terminal_outcome",
            allowed_root=outcome_root,
        )
        root_path = outcome_root if outcome_root.is_absolute() else Path.cwd() / outcome_root
        canonical_outcome = root_path.resolve(strict=True) / normalized["outcome_id"] / OUTCOME_FILE
        if resolved_outcome != canonical_outcome:
            raise CreativeCodeTerminalOutcomeIOError("terminal_outcome_noncanonical_path")
    except (CreativeCodeTerminalOutcomeError, CreativeCodeTerminalOutcomeIOError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(SUCCESS_VALIDATE_OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build and validate local creative-code lifecycle transition analytics."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
import errno
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
from typing import Any

from scripts.orchestration.creative_code_lifecycle_transition_analytics_contract import (
    CreativeCodeLifecycleTransitionAnalyticsError,
    build_creative_code_lifecycle_transition_analytics,
    canonical_analytics_bytes,
    validate_creative_code_lifecycle_transition_analytics,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    CreativeCodeTelemetryContractError,
    validate_creative_code_telemetry_event_any,
    validate_creative_code_telemetry_rollup_v2,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
TELEMETRY_ROOT = CREATIVE_CODE_ROOT / "telemetry"
ANALYTICS_ROOT = CREATIVE_CODE_ROOT / "lifecycle_transition_analytics"

EVENTS_FILE = "creative_code_telemetry_events.jsonl"
ROLLUP_FILE = "creative_code_telemetry_rollup.json"
ANALYTICS_FILE = "analytics.json"

MAX_EVENTS_FILE_BYTES = 8_388_608
MAX_EVENT_LINE_BYTES = 262_144
MAX_EVENT_LINES = 10_000
MAX_ROLLUP_BYTES = 1_048_576
MAX_ANALYTICS_BYTES = 262_144

_PUBLISH_LOCK = threading.Lock()


class CreativeCodeLifecycleTransitionAnalyticsIOError(ValueError):
    """Raised when local snapshot I/O cannot remain bounded and fail-closed."""


@dataclass(frozen=True)
class _FileIdentity:
    device: int
    inode: int
    mode: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class _SourceSeal:
    path: Path
    identity: _FileIdentity


def _identity(info: os.stat_result) -> _FileIdentity:
    return _FileIdentity(
        device=info.st_dev,
        inode=info.st_ino,
        mode=info.st_mode,
        links=info.st_nlink,
        size=info.st_size,
        modified_ns=info.st_mtime_ns,
        changed_ns=info.st_ctime_ns,
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    current = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    components: list[Path] = []
    for part in parts:
        current = current / part
        try:
            current.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                "path_component_read_failed"
            ) from exc
        components.append(current)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        try:
            info = component.lstat()
        except OSError as exc:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                f"{label}_component_read_failed"
            ) from exc
        if stat.S_ISLNK(info.st_mode):
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_symlink_rejected")


def _resolve_telemetry_dir(raw_path: Path) -> Path:
    requested = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    _reject_symlink_components(TELEMETRY_ROOT, label="telemetry_root")
    _reject_symlink_components(requested, label="telemetry_directory")
    try:
        allowed_root = TELEMETRY_ROOT.resolve(strict=True)
        resolved = requested.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "telemetry_directory_missing"
        ) from exc
    if not _is_relative_to(resolved, allowed_root):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "telemetry_directory_outside_fixed_root"
        )
    try:
        info = resolved.lstat()
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "telemetry_directory_read_failed"
        ) from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "telemetry_directory_must_be_directory"
        )
    return resolved


def _read_bounded_regular_bytes(
    path: Path,
    *,
    label: str,
    maximum: int,
    required_mode: int | None = None,
) -> tuple[bytes, _SourceSeal]:
    _reject_symlink_components(path, label=label)
    try:
        before_info = path.lstat()
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_missing") from exc
    before = _identity(before_info)
    if not stat.S_ISREG(before.mode):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_must_be_regular")
    if before.links != 1:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_hardlink_rejected")
    if required_mode is not None and stat.S_IMODE(before.mode) != required_mode:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_mode_invalid")
    if before.size > maximum:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_too_large")

    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        opened = _identity(os.fstat(descriptor))
        if opened != before:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_identity_changed")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > maximum:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_too_large")
        after_open = _identity(os.fstat(descriptor))
    except CreativeCodeLifecycleTransitionAnalyticsIOError:
        raise
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_read_failed") from exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                    f"{label}_read_failed"
                ) from exc
    try:
        after = _identity(path.lstat())
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_identity_changed") from exc
    if after_open != before or after != before or len(raw) != before.size:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_identity_changed")
    return raw, _SourceSeal(path=path, identity=before)


def _recheck_source(seal: _SourceSeal, *, label: str) -> None:
    _reject_symlink_components(seal.path, label=label)
    try:
        current = _identity(seal.path.lstat())
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_identity_changed") from exc
    if current != seal.identity:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_identity_changed")


def _duplicate_key_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError("telemetry_json_duplicate_key")
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> None:
    raise CreativeCodeLifecycleTransitionAnalyticsIOError("telemetry_json_nonfinite_number")


def _decode_json(raw: bytes, *, label: str) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_bom_rejected")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_invalid_utf8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_duplicate_key_hook,
            parse_constant=_reject_nonfinite,
        )
    except CreativeCodeLifecycleTransitionAnalyticsIOError:
        raise
    except (RecursionError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(f"{label}_malformed") from exc


def _load_snapshot(
    telemetry_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], tuple[_SourceSeal, _SourceSeal]]:
    resolved = _resolve_telemetry_dir(telemetry_dir)
    events_raw, events_seal = _read_bounded_regular_bytes(
        resolved / EVENTS_FILE,
        label="telemetry_events",
        maximum=MAX_EVENTS_FILE_BYTES,
    )
    rollup_raw, rollup_seal = _read_bounded_regular_bytes(
        resolved / ROLLUP_FILE,
        label="telemetry_rollup",
        maximum=MAX_ROLLUP_BYTES,
    )

    if events_raw and not events_raw.endswith(b"\n"):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "telemetry_events_missing_final_newline"
        )
    event_lines = events_raw.splitlines()
    if len(event_lines) > MAX_EVENT_LINES:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("telemetry_events_too_many_lines")
    events: list[dict[str, Any]] = []
    for index, line in enumerate(event_lines):
        if not line:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError("telemetry_events_blank_line")
        if len(line) > MAX_EVENT_LINE_BYTES:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError("telemetry_event_line_too_large")
        event = _decode_json(line, label="telemetry_event")
        if not isinstance(event, dict):
            raise CreativeCodeLifecycleTransitionAnalyticsIOError("telemetry_event_must_be_object")
        try:
            events.append(validate_creative_code_telemetry_event_any(event))
        except CreativeCodeTelemetryContractError as exc:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                "telemetry_event_contract_invalid"
            ) from exc

    rollup = _decode_json(rollup_raw, label="telemetry_rollup")
    if not isinstance(rollup, dict):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("telemetry_rollup_must_be_object")
    try:
        normalized_rollup = validate_creative_code_telemetry_rollup_v2(rollup)
    except CreativeCodeTelemetryContractError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "telemetry_rollup_contract_invalid"
        ) from exc
    _recheck_source(events_seal, label="telemetry_events")
    _recheck_source(rollup_seal, label="telemetry_rollup")
    return events, normalized_rollup, (events_seal, rollup_seal)


def _ensure_output_root() -> Path:
    _reject_symlink_components(ANALYTICS_ROOT, label="analytics_root")
    try:
        ANALYTICS_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_root_create_failed"
        ) from exc
    _reject_symlink_components(ANALYTICS_ROOT, label="analytics_root")
    try:
        resolved = ANALYTICS_ROOT.resolve(strict=True)
        info = resolved.lstat()
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_root_read_failed") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_root_must_be_directory")
    return resolved


def _existing_output_root() -> Path:
    _reject_symlink_components(ANALYTICS_ROOT, label="analytics_root")
    try:
        resolved = ANALYTICS_ROOT.resolve(strict=True)
        info = resolved.lstat()
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_artifact_missing") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_root_must_be_directory")
    return resolved


def _fsync_directory(path: Path) -> None:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_directory_fsync_failed"
        ) from exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                    "analytics_directory_fsync_failed"
                ) from exc


def _read_existing_artifact(path: Path) -> bytes:
    raw, seal = _read_bounded_regular_bytes(
        path,
        label="analytics_artifact",
        maximum=MAX_ANALYTICS_BYTES,
        required_mode=0o600,
    )
    parsed = _decode_json(raw, label="analytics_artifact")
    if not isinstance(parsed, dict):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_artifact_must_be_object")
    try:
        normalized = validate_creative_code_lifecycle_transition_analytics(parsed)
    except CreativeCodeLifecycleTransitionAnalyticsError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_artifact_invalid") from exc
    if canonical_analytics_bytes(normalized) != raw:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_artifact_not_canonical")
    _recheck_source(seal, label="analytics_artifact")
    return raw


def _read_namespace(target_dir: Path, target_file: Path) -> bytes | None:
    _reject_symlink_components(target_dir, label="analytics_namespace")
    try:
        info = target_dir.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_namespace_read_failed"
        ) from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_namespace_must_be_directory"
        )
    if target_file.exists() or target_file.is_symlink():
        try:
            entries = list(target_dir.iterdir())
        except OSError as exc:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                "analytics_namespace_read_failed"
            ) from exc
        if entries != [target_file]:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_namespace_ambiguous")
        return _read_existing_artifact(target_file)
    try:
        entries = list(target_dir.iterdir())
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_namespace_read_failed"
        ) from exc
    if entries:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_namespace_ambiguous")
    return None


def _create_namespace(root: Path, analytics_id: str) -> tuple[Path, Path, bytes | None]:
    target_dir = root / analytics_id
    target_file = target_dir / ANALYTICS_FILE
    existing = _read_namespace(target_dir, target_file)
    if target_dir.exists() or target_dir.is_symlink():
        return target_dir, target_file, existing
    try:
        target_dir.mkdir(mode=0o700)
    except FileExistsError:
        return target_dir, target_file, _read_namespace(target_dir, target_file)
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_namespace_create_failed"
        ) from exc
    _fsync_directory(root)
    return target_dir, target_file, None


def _write_staging(parent: Path, content: bytes) -> Path:
    descriptor = -1
    staging: Path | None = None
    try:
        try:
            descriptor, raw_path = tempfile.mkstemp(
                prefix=".analytics.", suffix=".staging", dir=parent
            )
            staging = Path(raw_path)
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                    "analytics_staging_must_be_private_regular"
                )
            if stat.S_IMODE(info.st_mode) != 0o600:
                os.fchmod(descriptor, 0o600)
            written = 0
            while written < len(content):
                count = os.write(descriptor, content[written:])
                if count <= 0:
                    raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                        "analytics_staging_write_failed"
                    )
                written += count
            os.fsync(descriptor)
        finally:
            if descriptor >= 0:
                descriptor_to_close = descriptor
                descriptor = -1
                os.close(descriptor_to_close)
    except CreativeCodeLifecycleTransitionAnalyticsIOError:
        if staging is not None:
            try:
                staging.unlink()
            except FileNotFoundError:
                pass
        raise
    except OSError as exc:
        if staging is not None:
            try:
                staging.unlink()
            except FileNotFoundError:
                pass
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_staging_write_failed"
        ) from exc
    if staging is None:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_staging_write_failed")
    return staging


def _link_noreplace(staging: Path, target: Path) -> None:
    try:
        os.link(staging, target, follow_symlinks=False)
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
            raise CreativeCodeLifecycleTransitionAnalyticsIOError(
                "analytics_hardlink_unsupported"
            ) from exc
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_link_failed") from exc


def _cleanup_staging(staging: Path) -> None:
    try:
        staging.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError(
            "analytics_staging_cleanup_failed"
        ) from exc


def _publish(
    artifact: Mapping[str, Any],
    content: bytes,
    *,
    source_seals: tuple[_SourceSeal, _SourceSeal],
) -> tuple[Path, bool]:
    if len(content) > MAX_ANALYTICS_BYTES:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_artifact_too_large")
    root = _ensure_output_root()
    analytics_id = str(artifact["analytics_id"])
    target_dir, target_file, existing = _create_namespace(root, analytics_id)
    if existing is not None:
        if existing != content:
            raise CreativeCodeLifecycleTransitionAnalyticsIOError("divergent_replay")
        for index, seal in enumerate(source_seals):
            _recheck_source(seal, label=f"telemetry_source_{index}")
        return target_file, True

    for index, seal in enumerate(source_seals):
        _recheck_source(seal, label=f"telemetry_source_{index}")
    staging = _write_staging(target_dir, content)
    installed = False
    try:
        for index, seal in enumerate(source_seals):
            _recheck_source(seal, label=f"telemetry_source_{index}")
        try:
            _link_noreplace(staging, target_file)
            installed = True
        except FileExistsError:
            installed = False
    finally:
        _cleanup_staging(staging)
    _fsync_directory(target_dir)
    _fsync_directory(root)
    existing = _read_existing_artifact(target_file)
    if existing != content:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("divergent_replay")
    for index, seal in enumerate(source_seals):
        _recheck_source(seal, label=f"telemetry_source_{index}")
    return target_file, not installed


def build_from_snapshot(
    *, telemetry_dir: Path = TELEMETRY_ROOT
) -> tuple[Path, bool, dict[str, Any]]:
    events, rollup, source_seals = _load_snapshot(telemetry_dir)
    artifact = build_creative_code_lifecycle_transition_analytics(events, telemetry_rollup=rollup)
    content = canonical_analytics_bytes(artifact)
    with _PUBLISH_LOCK:
        path, replayed = _publish(artifact, content, source_seals=source_seals)
    return path, replayed, artifact


def validate_snapshot_artifact(*, telemetry_dir: Path = TELEMETRY_ROOT) -> dict[str, Any]:
    events, rollup, source_seals = _load_snapshot(telemetry_dir)
    expected: dict[str, Any] = build_creative_code_lifecycle_transition_analytics(
        events, telemetry_rollup=rollup
    )
    content = canonical_analytics_bytes(expected)
    root = _existing_output_root()
    target = root / expected["analytics_id"] / ANALYTICS_FILE
    existing = _read_namespace(target.parent, target)
    if existing is None:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("analytics_artifact_missing")
    if existing != content:
        raise CreativeCodeLifecycleTransitionAnalyticsIOError("divergent_replay")
    for index, seal in enumerate(source_seals):
        _recheck_source(seal, label=f"telemetry_source_{index}")
    return expected


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    snapshot_semantics = (
        "Observed counts each valid adjacent event pair joined by exact typed lineage with both "
        "events present in the frozen telemetry snapshot; permitted fanout creates multiple "
        "observed pairs. An unobserved predecessor means no unique valid predecessor is present, "
        "and an ambiguous predecessor fails the build. An unobserved successor means zero valid "
        "successors are present; one or more valid successors are observed, including permitted "
        "fanout. Absence is snapshot-local, not proof that the transition did not occur. A "
        "complete terminal lineage is linked through every lifecycle stage within the frozen "
        "snapshot only; it is not operational completeness, PR readiness, or lifecycle success."
    )
    parser = argparse.ArgumentParser(
        description=(
            "Build or mutation-free validate deterministic snapshot-only creative-code analytics. "
            f"{snapshot_semantics}"
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    command_help = {
        "build": "Publish the snapshot-derived analytics artifact with deterministic replay.",
        "validate": "Mutation-free exact-byte validation against the current source snapshot.",
    }
    for command, help_text in command_help.items():
        subparser = subparsers.add_parser(
            command,
            help=help_text,
            description=f"{help_text} {snapshot_semantics}",
        )
        subparser.add_argument(
            "--telemetry-dir",
            default=str(TELEMETRY_ROOT),
            help=(
                "Directory containing the fixed-name event JSONL and mixed v2 rollup that form "
                "the frozen telemetry snapshot; it must remain inside the fixed creative-code "
                "telemetry root, and relative paths resolve from the repository root."
            ),
        )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        telemetry_dir = Path(args.telemetry_dir)
        if args.command == "build":
            _, replayed, artifact = build_from_snapshot(telemetry_dir=telemetry_dir)
            replay = "identical" if replayed else "new"
            print(
                "PASS: creative-code lifecycle transition analytics built "
                f"analytics_id={artifact['analytics_id']} replay={replay}"
            )
        else:
            artifact = validate_snapshot_artifact(telemetry_dir=telemetry_dir)
            print(
                "PASS: creative-code lifecycle transition analytics validated "
                f"analytics_id={artifact['analytics_id']}"
            )
    except (
        CreativeCodeLifecycleTransitionAnalyticsError,
        CreativeCodeLifecycleTransitionAnalyticsIOError,
        CreativeCodeTelemetryContractError,
    ) as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build and validate immutable local creative-code terminal outcomes."""

from __future__ import annotations

import argparse
import errno
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

from scripts.orchestration.creative_code_terminal_outcome_contract import (
    CreativeCodeTerminalOutcomeError,
    MAX_JSON_OBJECT_BYTES,
    build_creative_code_terminal_outcome,
    canonical_json_bytes,
    read_json_object,
    validate_creative_code_terminal_outcome,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
TERMINAL_OUTCOMES_ROOT = CREATIVE_CODE_ROOT / "terminal_outcomes"
OUTCOME_FILE = "terminal_outcome.json"
SUCCESS_BUILD_OUTPUT = "PASS: creative-code terminal outcome built"
SUCCESS_VALIDATE_OUTPUT = "PASS: creative-code terminal outcome valid"


class CreativeCodeTerminalOutcomeIOError(ValueError):
    """Raised when terminal-outcome IO cannot stay immutable and contained."""


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
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise CreativeCodeTerminalOutcomeIOError("directory_fsync_failed") from exc
    finally:
        os.close(descriptor)


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

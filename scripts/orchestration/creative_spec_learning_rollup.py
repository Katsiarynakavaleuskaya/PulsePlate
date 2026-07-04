#!/usr/bin/env python3
"""Collect proposal-only learning rollups from finalized creative specs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.creative_spec_learning_rollup_contract import (
    CreativeSpecLearningRollupError,
    build_coordinator_advisory_hints,
    build_creative_spec_learning_rollup,
    validate_coordinator_advisory_hints,
    validate_creative_spec_learning_rollup,
)

CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
SPEC_BRIDGE_ROOT = CREATIVE_CODE_ROOT / "spec_bridge"
LEARNING_ROLLUP_ROOT = CREATIVE_CODE_ROOT / "learning_rollup"

ROLLUP_FILENAME = "creative_spec_learning_rollup.json"
HINTS_FILENAME = "coordinator_advisory_hints.json"
COLLECT_SUCCESS_OUTPUT = "PASS: creative spec learning rollup collected"
HINTS_SUCCESS_OUTPUT = "PASS: creative spec coordinator advisory hints written"
VALIDATE_SUCCESS_OUTPUT = "PASS: creative spec learning artifact valid"


class CreativeSpecLearningRollupCliError(ValueError):
    """Raised when local learning-rollup CLI I/O cannot safely complete."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    components: list[Path] = []
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeSpecLearningRollupCliError(f"{label} must not traverse symlinks.")


def _ensure_artifact_root(root: Path) -> Path:
    _reject_symlink_components(root, label="creative-code artifact root")
    root.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(root, label="creative-code artifact root")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise CreativeSpecLearningRollupCliError("creative-code artifact root must be a directory.")
    return resolved


def _resolve_repo_json_file(raw_path: Path, *, label: str) -> Path:
    candidate = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    _reject_symlink_components(candidate, label=label)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeSpecLearningRollupCliError(f"{label} must exist.") from exc
    repo_root = REPO_ROOT.resolve()
    artifact_root = CREATIVE_CODE_ROOT.resolve(strict=False)
    if not _is_relative_to(resolved, repo_root) or not _is_relative_to(resolved, artifact_root):
        raise CreativeSpecLearningRollupCliError(
            f"{label} must stay under creative-code artifacts."
        )
    if not resolved.is_file() or resolved.suffix != ".json":
        raise CreativeSpecLearningRollupCliError(f"{label} must be a JSON file.")
    return resolved


def _resolve_output_dir(raw_output: str | None, *, rollup_id: str) -> Path:
    root = _ensure_artifact_root(LEARNING_ROLLUP_ROOT)
    if raw_output:
        candidate = Path(raw_output)
        path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
    else:
        path = LEARNING_ROLLUP_ROOT / rollup_id
    _reject_symlink_components(path, label="output directory")
    resolved = path.resolve(strict=False)
    if not _is_relative_to(resolved, root):
        raise CreativeSpecLearningRollupCliError(
            "output directory must stay under creative-code learning rollup artifacts."
        )
    if path.exists() or path.is_symlink():
        raise CreativeSpecLearningRollupCliError(
            "output directory already exists; remove the local artifact before rerun."
        )
    path.mkdir(parents=True, exist_ok=False)
    _reject_symlink_components(path, label="output directory")
    return path.resolve(strict=True)


def _resolve_output_file(raw_output: str | Path, *, label: str) -> Path:
    candidate = Path(raw_output)
    path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
    _reject_symlink_components(path.parent, label=f"{label} parent")
    root = _ensure_artifact_root(LEARNING_ROLLUP_ROOT)
    resolved = path.resolve(strict=False)
    if not _is_relative_to(resolved, root):
        raise CreativeSpecLearningRollupCliError(
            f"{label} must stay under creative-code learning rollup artifacts."
        )
    if path.exists() or path.is_symlink():
        raise CreativeSpecLearningRollupCliError(f"{label} already exists.")
    if path.suffix != ".json":
        raise CreativeSpecLearningRollupCliError(f"{label} must be a JSON file.")
    return path


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    resolved = _resolve_repo_json_file(path, label=label)
    try:
        payload = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeSpecLearningRollupCliError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeSpecLearningRollupCliError(f"unable to read {label}.") from exc
    if not isinstance(payload, dict):
        raise CreativeSpecLearningRollupCliError(f"{label} must be a JSON object.")
    return payload


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeSpecLearningRollupCliError(
                f"creative spec learning JSON has duplicate key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def _write_json_atomic(path: Path, payload: Any) -> None:
    if path.suffix != ".json":
        raise CreativeSpecLearningRollupCliError("output artifact must be JSON.")
    _reject_symlink_components(path.parent, label="output artifact parent")
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(path.parent, label="output artifact parent")
    if path.exists() or path.is_symlink():
        raise CreativeSpecLearningRollupCliError("output artifact already exists.")
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(payload, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _collect(args: argparse.Namespace) -> int:
    bridge_metrics = _read_json_object(args.bridge_metrics, label="bridge metrics")
    skeptic_attachment = _read_json_object(args.skeptic_attachment, label="skeptic attachment")
    finalize_receipt = _read_json_object(args.finalize_receipt, label="finalize receipt")
    bundle = _read_json_object(args.bundle, label="creative specification bundle")
    rollup = build_creative_spec_learning_rollup(
        bridge_metrics=bridge_metrics,
        skeptic_attachment=skeptic_attachment,
        finalize_receipt=finalize_receipt,
        bundle=bundle,
    )
    hints = build_coordinator_advisory_hints(rollup)
    output_dir = _resolve_output_dir(args.output_dir, rollup_id=str(rollup["rollup_id"]))
    try:
        _write_json_atomic(output_dir / ROLLUP_FILENAME, rollup)
        _write_json_atomic(output_dir / HINTS_FILENAME, hints)
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    print(COLLECT_SUCCESS_OUTPUT)
    print(output_dir.relative_to(REPO_ROOT).as_posix())
    return 0


def _emit_hints(args: argparse.Namespace) -> int:
    rollup = validate_creative_spec_learning_rollup(
        _read_json_object(args.rollup, label="learning rollup")
    )
    hints = build_coordinator_advisory_hints(rollup)
    output_path = _resolve_output_file(args.output, label="coordinator advisory hints output")
    _write_json_atomic(output_path, hints)
    print(HINTS_SUCCESS_OUTPUT)
    print(output_path.relative_to(REPO_ROOT).as_posix())
    return 0


def _summarize(args: argparse.Namespace) -> int:
    rollup = validate_creative_spec_learning_rollup(
        _read_json_object(args.rollup, label="learning rollup")
    )
    payload = {
        "rollup_id": rollup["rollup_id"],
        "synthesis_status": rollup["outcomes"]["synthesis_status"],
        "selected_variant_id": rollup["outcomes"]["selected_variant_id"],
        "learning_summary": rollup["learning_summary"],
        "authority_boundary": "proposal_only_non_runtime",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _validate(args: argparse.Namespace) -> int:
    if args.rollup:
        validate_creative_spec_learning_rollup(
            _read_json_object(args.rollup, label="learning rollup")
        )
    if args.hints:
        validate_coordinator_advisory_hints(
            _read_json_object(args.hints, label="coordinator advisory hints")
        )
    print(VALIDATE_SUCCESS_OUTPUT)
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="creative_spec_learning_rollup",
        description="Collect proposal-only learning from finalized creative specs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    collect.add_argument("--bridge-metrics", type=Path, required=True)
    collect.add_argument("--skeptic-attachment", type=Path, required=True)
    collect.add_argument("--finalize-receipt", type=Path, required=True)
    collect.add_argument("--bundle", type=Path, required=True)
    collect.add_argument("--output-dir", default=None)
    collect.set_defaults(func=_collect)

    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("--rollup", type=Path, required=True)
    summarize.set_defaults(func=_summarize)

    emit_hints = subparsers.add_parser("emit-coordinator-hints")
    emit_hints.add_argument("--rollup", type=Path, required=True)
    emit_hints.add_argument("--output", required=True)
    emit_hints.set_defaults(func=_emit_hints)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--rollup", type=Path, default=None)
    validate.add_argument("--hints", type=Path, default=None)
    validate.set_defaults(func=_validate)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "validate" and not args.rollup and not args.hints:
        print("FAIL: validate requires --rollup or --hints")
        return 1
    try:
        return int(args.func(args))
    except (CreativeSpecLearningRollupCliError, CreativeSpecLearningRollupError) as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Admit finalized creative specs to prepare-only patch-builder requests."""

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

from scripts.orchestration import creative_code_patch_builder
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
)
from scripts.orchestration.creative_code_patch_workspace import (
    CreativeCodePatchWorkspaceError,
    cleanup_run_dir,
    read_json,
    resolve_run_dir,
    resolve_run_file,
    shared_tree_status,
    verify_origin_main_base,
    write_json_atomic,
)
from scripts.orchestration.creative_spec_patch_admission_contract import (
    ADMISSION_ARTIFACT_TYPE,
    CreativeSpecPatchAdmissionError,
    attach_builder_prepare_summary,
    build_builder_prepare_summary,
    build_creative_spec_patch_admission,
    validate_admission_bindings,
    validate_creative_spec_patch_admission,
    validate_human_admission,
)

CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
PATCH_ADMISSION_ROOT = CREATIVE_CODE_ROOT / "patch_admission"

ADMISSION_FILENAME = "creative_spec_patch_admission.json"
FINALIZE_RECEIPT_FILENAME = "finalize_receipt.json"
HUMAN_ADMISSION_FILENAME = "human_admission.json"
REQUEST_FILENAME = creative_code_patch_builder.REQUEST_FILE
SOURCE_BUNDLE_FILENAME = creative_code_patch_builder.SOURCE_BUNDLE_FILE

BUILD_SUCCESS_OUTPUT = "PASS: creative spec patch admission request built"
VALIDATE_SUCCESS_OUTPUT = "PASS: creative spec patch admission valid"
PREPARE_SUCCESS_OUTPUT = "PASS: creative spec patch admission prepare complete"
SUMMARY_AUTHORITY_BOUNDARY = "prepare_only_non_runtime"


class CreativeSpecPatchAdmissionCliError(ValueError):
    """Raised when local admission CLI I/O cannot safely complete."""


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
            raise CreativeSpecPatchAdmissionCliError(f"{label} must not traverse symlinks.")


def _ensure_artifact_root(root: Path) -> Path:
    _reject_symlink_components(root, label="creative-code artifact root")
    root.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(root, label="creative-code artifact root")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise CreativeSpecPatchAdmissionCliError("creative-code artifact root must be a directory.")
    return resolved


def _resolve_repo_json_file(raw_path: Path, *, label: str) -> Path:
    candidate = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    _reject_symlink_components(candidate, label=label)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeSpecPatchAdmissionCliError(f"{label} must exist.") from exc
    repo_root = REPO_ROOT.resolve()
    artifact_root = CREATIVE_CODE_ROOT.resolve(strict=False)
    if not _is_relative_to(resolved, repo_root) or not _is_relative_to(resolved, artifact_root):
        raise CreativeSpecPatchAdmissionCliError(
            f"{label} must stay under creative-code artifacts."
        )
    if not resolved.is_file() or resolved.suffix != ".json":
        raise CreativeSpecPatchAdmissionCliError(f"{label} must be a JSON file.")
    return resolved


def _resolve_ref(raw_ref: str, *, label: str) -> Path:
    return _resolve_repo_json_file(Path(raw_ref), label=label)


def _resolve_output_dir(raw_output: str) -> Path:
    root = _ensure_artifact_root(PATCH_ADMISSION_ROOT)
    candidate = Path(raw_output)
    path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
    _reject_symlink_components(path, label="output directory")
    resolved = path.resolve(strict=False)
    if not _is_relative_to(resolved, root):
        raise CreativeSpecPatchAdmissionCliError(
            "output directory must stay under creative-code patch admission artifacts."
        )
    if path.exists() or path.is_symlink():
        raise CreativeSpecPatchAdmissionCliError(
            "output directory already exists; remove the local artifact before rerun."
        )
    path.mkdir(parents=True, exist_ok=False)
    _reject_symlink_components(path, label="output directory")
    return path.resolve(strict=True)


def _repo_ref(path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise CreativeSpecPatchAdmissionCliError(
            "artifact path must stay under repo root."
        ) from exc


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeSpecPatchAdmissionCliError(
                f"creative spec patch admission JSON has duplicate key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    resolved = _resolve_repo_json_file(path, label=label)
    try:
        payload = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeSpecPatchAdmissionCliError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeSpecPatchAdmissionCliError(f"unable to read {label}.") from exc
    if not isinstance(payload, dict):
        raise CreativeSpecPatchAdmissionCliError(f"{label} must be a JSON object.")
    return payload


def _write_json_new(path: Path, payload: Any) -> None:
    if path.suffix != ".json":
        raise CreativeSpecPatchAdmissionCliError("output artifact must be JSON.")
    _reject_symlink_components(path.parent, label="output artifact parent")
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(path.parent, label="output artifact parent")
    if path.exists() or path.is_symlink():
        raise CreativeSpecPatchAdmissionCliError("output artifact already exists.")
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


def _require_clean_shared_tree() -> None:
    status = shared_tree_status()
    if status.strip():
        raise CreativeSpecPatchAdmissionCliError(
            "shared worktree must be clean before creative spec patch admission."
        )


def _require_origin_main_base(base_commit_sha: str) -> None:
    verify_origin_main_base(base_commit_sha)


def _read_admission_with_sources(
    admission_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    admission = validate_creative_spec_patch_admission(
        _read_json_object(admission_path, label="creative spec patch admission")
    )
    request = _read_json_object(
        _resolve_ref(admission["patch_request"]["request_ref"], label="patch request"),
        label="patch request",
    )
    bundle = _read_json_object(
        _resolve_ref(admission["patch_request"]["source_bundle_ref"], label="source bundle"),
        label="source bundle",
    )
    finalize_receipt = _read_json_object(
        _resolve_ref(admission["source"]["finalize_receipt_ref"], label="finalize receipt"),
        label="finalize receipt",
    )
    human_admission = _read_json_object(
        _resolve_ref(
            admission["human_admission"]["human_admission_ref"],
            label="human admission",
        ),
        label="human admission",
    )
    validate_admission_bindings(
        admission,
        request=request,
        source_bundle=bundle,
        finalize_receipt=finalize_receipt,
        human_admission=human_admission,
    )
    return admission, request, bundle, finalize_receipt, human_admission


def _build_request_artifacts(args: argparse.Namespace) -> Path:
    _require_clean_shared_tree()
    _require_origin_main_base(args.base_sha)
    finalize_receipt = _read_json_object(args.finalize_receipt, label="finalize receipt")
    source_bundle = _read_json_object(args.bundle, label="creative specification bundle")
    human_admission = validate_human_admission(
        _read_json_object(args.human_admission, label="human admission")
    )
    output_dir = _resolve_output_dir(args.output_dir)
    request_path = output_dir / REQUEST_FILENAME
    source_bundle_path = output_dir / SOURCE_BUNDLE_FILENAME
    human_path = output_dir / HUMAN_ADMISSION_FILENAME
    finalize_path = output_dir / FINALIZE_RECEIPT_FILENAME
    admission_path = output_dir / ADMISSION_FILENAME
    try:
        admission, request = build_creative_spec_patch_admission(
            finalize_receipt=finalize_receipt,
            source_bundle=source_bundle,
            human_admission=human_admission,
            base_commit_sha=args.base_sha,
            finalize_receipt_ref=_repo_ref(finalize_path),
            bundle_ref=_repo_ref(source_bundle_path),
            human_admission_ref=_repo_ref(human_path),
            request_ref=_repo_ref(request_path),
            source_bundle_ref=_repo_ref(source_bundle_path),
        )
        _write_json_new(finalize_path, finalize_receipt)
        _write_json_new(source_bundle_path, source_bundle)
        _write_json_new(human_path, human_admission)
        _write_json_new(request_path, request)
        _write_json_new(admission_path, admission)
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    return admission_path


def _build_request(args: argparse.Namespace) -> int:
    admission_path = _build_request_artifacts(args)
    print(BUILD_SUCCESS_OUTPUT)
    print(_repo_ref(admission_path))
    return 0


def _prepare_builder_from_admission(admission_path: Path, *, run_id: str) -> Path:
    _require_clean_shared_tree()
    admission, _request, _bundle, _finalize_receipt, _human_admission = (
        _read_admission_with_sources(admission_path)
    )
    _require_origin_main_base(admission["base"]["base_commit_sha"])
    request_path = _resolve_ref(admission["patch_request"]["request_ref"], label="patch request")
    source_bundle_path = _resolve_ref(
        admission["patch_request"]["source_bundle_ref"],
        label="source bundle",
    )
    run_dir_existed = True
    try:
        resolve_run_dir(run_id, create=False)
    except CreativeCodePatchWorkspaceError:
        run_dir_existed = False
    try:
        state = creative_code_patch_builder.prepare(
            spec_bundle_path=source_bundle_path,
            request_path=request_path,
            run_id=run_id,
        )
    except Exception:
        if not run_dir_existed:
            try:
                cleanup_run_dir(run_id)
            except CreativeCodePatchWorkspaceError as cleanup_exc:
                raise CreativeSpecPatchAdmissionCliError(
                    "prepare failed and partial run cleanup failed."
                ) from cleanup_exc
        raise
    run_dir = resolve_run_dir(run_id, create=False)
    builder_prepare = build_builder_prepare_summary(
        run_id=run_id,
        state=state,
        request_file_present=resolve_run_file(
            run_dir, creative_code_patch_builder.REQUEST_FILE
        ).exists(),
        source_bundle_file_present=resolve_run_file(
            run_dir,
            creative_code_patch_builder.SOURCE_BUNDLE_FILE,
        ).exists(),
        selected_variant_file_present=resolve_run_file(
            run_dir,
            creative_code_patch_builder.SELECTED_VARIANT_FILE,
        ).exists(),
        state_file_present=resolve_run_file(
            run_dir, creative_code_patch_builder.STATE_FILE
        ).exists(),
        candidate_patch_path_present=(
            run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE
        ).exists(),
        result_file_present=(run_dir / creative_code_patch_builder.RESULT_FILE).exists(),
    )
    updated = attach_builder_prepare_summary(admission, builder_prepare=builder_prepare)
    write_json_atomic(admission_path, updated)
    return admission_path


def _prepare_builder(args: argparse.Namespace) -> int:
    admission_path = _resolve_repo_json_file(args.admission, label="creative spec patch admission")
    output = _prepare_builder_from_admission(admission_path, run_id=args.run_id)
    print(PREPARE_SUCCESS_OUTPUT)
    print(_repo_ref(output))
    return 0


def _build_and_prepare(args: argparse.Namespace) -> int:
    build_args = argparse.Namespace(
        finalize_receipt=args.finalize_receipt,
        bundle=args.bundle,
        human_admission=args.human_admission,
        base_sha=args.base_sha,
        output_dir=args.output_dir,
    )
    admission_path = _build_request_artifacts(build_args)
    try:
        _prepare_builder_from_admission(admission_path, run_id=args.run_id)
    except Exception:
        output_dir = admission_path.parent
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    print(PREPARE_SUCCESS_OUTPUT)
    print(_repo_ref(admission_path))
    return 0


def _validate(args: argparse.Namespace) -> int:
    admission, _request, _bundle, _finalize_receipt, _human_admission = (
        _read_admission_with_sources(args.admission)
    )
    _require_origin_main_base(admission["base"]["base_commit_sha"])
    print(VALIDATE_SUCCESS_OUTPUT)
    return 0


def _summarize(args: argparse.Namespace) -> int:
    admission, _request, _bundle, _finalize_receipt, _human_admission = (
        _read_admission_with_sources(args.admission)
    )
    _require_origin_main_base(admission["base"]["base_commit_sha"])
    payload = {
        "artifact_type": ADMISSION_ARTIFACT_TYPE,
        "admission_id": admission["admission_id"],
        "request_id": admission["patch_request"]["request_id"],
        "base_commit_sha": admission["base"]["base_commit_sha"],
        "selected_variant_id": admission["selected_variant"]["variant_id"],
        "prepared": admission["builder_prepare"]["prepared"],
        "run_id": admission["builder_prepare"]["run_id"],
        "candidate_patch_generated": admission["builder_prepare"]["candidate_patch_generated"],
        "candidate_patch_evaluated": admission["builder_prepare"]["candidate_patch_evaluated"],
        "candidate_patch_path_present": admission["builder_prepare"][
            "candidate_patch_path_present"
        ],
        "authority_boundary": SUMMARY_AUTHORITY_BOUNDARY,
        "next_allowed_action": "human_review_before_patch_generation",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="creative_spec_patch_admission",
        description="Admit finalized creative specs to prepare-only patch-builder requests.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_request = subparsers.add_parser("build-request")
    build_request.add_argument("--finalize-receipt", type=Path, required=True)
    build_request.add_argument("--bundle", type=Path, required=True)
    build_request.add_argument("--human-admission", type=Path, required=True)
    build_request.add_argument("--base-sha", required=True)
    build_request.add_argument("--output-dir", required=True)
    build_request.set_defaults(func=_build_request)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--admission", type=Path, required=True)
    validate.set_defaults(func=_validate)

    prepare = subparsers.add_parser("prepare-builder")
    prepare.add_argument("--admission", type=Path, required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.set_defaults(func=_prepare_builder)

    build_and_prepare = subparsers.add_parser("build-and-prepare")
    build_and_prepare.add_argument("--finalize-receipt", type=Path, required=True)
    build_and_prepare.add_argument("--bundle", type=Path, required=True)
    build_and_prepare.add_argument("--human-admission", type=Path, required=True)
    build_and_prepare.add_argument("--base-sha", required=True)
    build_and_prepare.add_argument("--output-dir", required=True)
    build_and_prepare.add_argument("--run-id", required=True)
    build_and_prepare.set_defaults(func=_build_and_prepare)

    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("--admission", type=Path, required=True)
    summarize.set_defaults(func=_summarize)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return int(args.func(args))
    except (
        CreativeSpecPatchAdmissionCliError,
        CreativeSpecPatchAdmissionError,
        CreativeCodePatchContractError,
        CreativeCodePatchWorkspaceError,
        creative_code_patch_builder.CreativeCodePatchBuilderError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

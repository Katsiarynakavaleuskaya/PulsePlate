"""Read-only inventory guard for local creative-code PR-2/PR-3 artifacts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
import re
import sys
from typing import Any

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_patch_builder
from scripts.orchestration import creative_code_patch_generation as generation_cli
from scripts.orchestration import creative_code_patch_workspace
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
    read_creative_code_patch_build_request,
    read_creative_code_patch_result,
    validate_creative_code_patch_build_request,
    validate_creative_code_patch_result,
    validate_creative_code_patch_run_sidecars,
)
from scripts.orchestration.creative_code_patch_workspace import (
    CreativeCodePatchWorkspaceError,
)
from scripts.orchestration.creative_code_pr_promotion_contract import (
    CreativeCodePRPromotionContractError,
    validate_creative_code_pr_promotion_approval,
    validate_creative_code_pr_promotion_plan,
    validate_creative_code_pr_promotion_receipt,
    validate_creative_code_pr_promotion_validation,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    validate_creative_code_specification_bundle,
)

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "creative_code_artifact_inventory_report"
POLICY_VERSION = "creative-code-artifact-inventory-v1"
SUCCESS_STATUS_OUTPUT = "PASS: creative-code artifact inventory report valid"
PROMOTION_READY_OUTPUT = "PASS: creative-code patch run ready for PR-3 promotion guard"
CLEANUP_READY_OUTPUT = "PASS: creative-code creative artifacts safe for guarded cleanup"

REPO_ROOT = creative_code_patch_workspace.REPO_ROOT
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
PATCH_RUNS_ROOT = CREATIVE_CODE_ROOT / "patch_runs"
PATCH_GENERATION_ROOT = CREATIVE_CODE_ROOT / "patch_generation"
PROMOTIONS_ROOT = CREATIVE_CODE_ROOT / "promotions"
CREATIVE_CODE_ROOT_REF = "artifacts/orchestration/creative_code"

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
PROMOTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
ARTIFACT_REF_RE = re.compile(
    r"^artifacts/orchestration/creative_code" r"(?:/[A-Za-z0-9][A-Za-z0-9._:-]{0,127})*$"
)
EXPERIMENT_BRANCH_RE = re.compile(r"^experiment/[a-z0-9][a-z0-9._-]{0,68}$")
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |raw[_ -]?(prompt|response|context|patch)|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|oracle stdout|oracle stderr|"
    r"/Users/|/private/var/|/var/folders/|/tmp/|file://|github_pat_|gh[psoru]_|"
    r"xox[abprs]-|sk-[A-Za-z0-9_-]{12,}|Authorization:\s*Bearer|GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE | re.MULTILINE,
)

PLAN_FILE = "promotion_plan.json"
VALIDATION_FILE = "preopen_validation.json"
APPROVAL_FILE = "promotion_approval.json"
RECEIPT_FILE = "promotion_receipt.json"
PROMOTION_STATE_FILE = "promotion_state.json"
KNOWN_PROMOTION_FILES = frozenset(
    {PLAN_FILE, VALIDATION_FILE, APPROVAL_FILE, RECEIPT_FILE, PROMOTION_STATE_FILE}
)

PATCH_RUN_FILES = frozenset(
    {
        creative_code_patch_builder.REQUEST_FILE,
        creative_code_patch_builder.SOURCE_BUNDLE_FILE,
        creative_code_patch_builder.SELECTED_VARIANT_FILE,
        creative_code_patch_builder.CANDIDATE_PATCH_FILE,
        creative_code_patch_builder.PATCH_METADATA_FILE,
        creative_code_patch_builder.EXPERIMENT_PACKET_FILE,
        creative_code_patch_builder.RESULT_FILE,
    }
)


class CreativeCodeArtifactInventoryError(ValueError):
    """Raised when the inventory report itself violates the closed contract."""


class InventoryArtifactError(ValueError):
    """Raised for one local artifact read/validation failure with a stable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class InventoryUsageError(ValueError):
    """Raised when an assertion command receives unsafe or invalid arguments."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    components: list[Path] = []
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise InventoryArtifactError("symlink_artifact")


def _repo_ref(path: Path) -> str:
    try:
        ref = path.resolve(strict=False).relative_to(REPO_ROOT.resolve(strict=False)).as_posix()
    except ValueError as exc:
        raise InventoryArtifactError("artifact_ref_outside_repo") from exc
    _validate_artifact_ref(ref)
    return ref


def _validate_artifact_ref(value: str) -> str:
    if not ARTIFACT_REF_RE.fullmatch(value):
        raise InventoryArtifactError("unsafe_artifact_ref")
    return value


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise InventoryArtifactError("duplicate_json_key")
        seen.add(key)
        payload[key] = value
    return payload


def _read_json_object(path: Path) -> dict[str, Any]:
    _reject_symlink_components(path)
    if not path.exists():
        raise InventoryArtifactError("missing_artifact")
    if path.is_symlink():
        raise InventoryArtifactError("symlink_artifact")
    if not path.is_file():
        raise InventoryArtifactError("artifact_not_file")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except InventoryArtifactError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InventoryArtifactError("unreadable_json") from exc
    if not isinstance(payload, dict):
        raise InventoryArtifactError("json_not_object")
    return payload


def _read_text_file(path: Path) -> str:
    _reject_symlink_components(path)
    if not path.exists():
        raise InventoryArtifactError("missing_artifact")
    if path.is_symlink():
        raise InventoryArtifactError("symlink_artifact")
    if not path.is_file():
        raise InventoryArtifactError("artifact_not_file")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InventoryArtifactError("unreadable_text") from exc


def _error_entry(*, artifact_ref: str, artifact_type: str, error_code: str) -> dict[str, Any]:
    return {
        "artifact_ref": artifact_ref,
        "artifact_type": artifact_type,
        "error_code": error_code,
        "error_fingerprint": fingerprint_payload(
            {
                "artifact_ref": artifact_ref,
                "artifact_type": artifact_type,
                "error_code": error_code,
                "policy_version": POLICY_VERSION,
            }
        ),
    }


def _append_error(
    errors: list[dict[str, Any]],
    *,
    path: Path,
    artifact_type: str,
    error_code: str,
) -> None:
    try:
        artifact_ref = _repo_ref(path)
    except InventoryArtifactError:
        artifact_ref = CREATIVE_CODE_ROOT_REF
        error_code = "artifact_ref_outside_repo"
    errors.append(
        _error_entry(
            artifact_ref=artifact_ref,
            artifact_type=artifact_type,
            error_code=error_code,
        )
    )


def _iter_child_dirs(root: Path, *, errors: list[dict[str, Any]], artifact_type: str) -> list[Path]:
    if not root.exists():
        return []
    try:
        _reject_symlink_components(root)
    except InventoryArtifactError as exc:
        _append_error(errors, path=root, artifact_type=artifact_type, error_code=exc.code)
        return []
    if root.is_symlink():
        _append_error(errors, path=root, artifact_type=artifact_type, error_code="symlink_artifact")
        return []
    if not root.is_dir():
        _append_error(errors, path=root, artifact_type=artifact_type, error_code="artifact_not_dir")
        return []
    children: list[Path] = []
    try:
        root_children = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError:
        _append_error(
            errors,
            path=root,
            artifact_type=artifact_type,
            error_code="unreadable_directory",
        )
        return []
    for child in root_children:
        if child.is_symlink():
            _append_error(
                errors,
                path=child,
                artifact_type=artifact_type,
                error_code="symlink_artifact",
            )
            continue
        if child.is_dir():
            children.append(child)
    return children


def _iter_named_files(
    root: Path,
    *,
    filename: str,
    errors: list[dict[str, Any]],
    artifact_type: str,
) -> list[Path]:
    if not root.exists():
        return []
    try:
        _reject_symlink_components(root)
    except InventoryArtifactError as exc:
        _append_error(errors, path=root, artifact_type=artifact_type, error_code=exc.code)
        return []
    if root.is_symlink():
        _append_error(errors, path=root, artifact_type=artifact_type, error_code="symlink_artifact")
        return []
    if not root.is_dir():
        _append_error(errors, path=root, artifact_type=artifact_type, error_code="artifact_not_dir")
        return []
    matches: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            current_children = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError:
            _append_error(
                errors,
                path=current,
                artifact_type=artifact_type,
                error_code="unreadable_directory",
            )
            continue
        for child in current_children:
            if child.is_symlink():
                _append_error(
                    errors,
                    path=child,
                    artifact_type=artifact_type,
                    error_code="symlink_artifact",
                )
                continue
            if child.is_dir():
                stack.append(child)
            elif child.name == filename:
                matches.append(child)
    return sorted(matches, key=lambda item: item.as_posix())


def current_origin_main_sha() -> str:
    """Read the current local origin/main SHA through the shared git wrapper."""

    try:
        value = str(
            creative_code_patch_workspace.run_git(
                ["rev-parse", "origin/main"],
                cwd=REPO_ROOT,
            ).stdout.strip()
        )
    except CreativeCodePatchWorkspaceError as exc:
        raise InventoryArtifactError("origin_main_unavailable") from exc
    if not SHA_RE.fullmatch(value):
        raise InventoryArtifactError("origin_main_unavailable")
    return value


def _patch_run_base_entry(run_dir: Path, *, blockers: list[str]) -> dict[str, Any]:
    run_id = run_dir.name if RUN_ID_RE.fullmatch(run_dir.name) else "invalid"
    try:
        run_ref = _repo_ref(run_dir)
    except InventoryArtifactError:
        run_ref = f"{CREATIVE_CODE_ROOT_REF}/patch_runs"
        blockers.append("unsafe_artifact_ref")
    return {
        "run_id": run_id,
        "run_ref": run_ref,
        "valid": False,
        "result_id": None,
        "request_id": None,
        "base_commit_sha": None,
        "status": "invalid",
        "failure_class": None,
        "promotion_ready": None,
        "sanitized": None,
        "patch_fingerprint": None,
        "changed_path_count": 0,
        "workspace_proof": {
            "origin_removed": False,
            "checkout_destroyed": False,
            "shared_tree_untouched": False,
        },
        "generation_receipt_ids": [],
        "promotion_receipt_ids": [],
        "promotion_linkage": "none",
        "promotion_candidate_state": "invalid",
        "blockers": blockers,
    }


def _inspect_patch_run(run_dir: Path, errors: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    entry = _patch_run_base_entry(run_dir, blockers=blockers)
    if not RUN_ID_RE.fullmatch(run_dir.name):
        blockers.append("unsafe_run_id")
        _append_error(
            errors,
            path=run_dir,
            artifact_type="patch_run",
            error_code="unsafe_run_id",
        )
        return entry
    try:
        for filename in sorted(PATCH_RUN_FILES):
            path = run_dir / filename
            if path.is_symlink():
                raise InventoryArtifactError("symlink_artifact")
            if not path.exists():
                raise InventoryArtifactError("missing_artifact")
        source_bundle = _read_json_object(run_dir / creative_code_patch_builder.SOURCE_BUNDLE_FILE)
        try:
            source_bundle = validate_creative_code_specification_bundle(source_bundle)
        except CreativeCodeSpecificationError as exc:
            raise InventoryArtifactError("invalid_source_bundle") from exc
        try:
            request = read_creative_code_patch_build_request(
                str(run_dir / creative_code_patch_builder.REQUEST_FILE)
            )
            request = validate_creative_code_patch_build_request(
                request,
                source_bundle=source_bundle,
            )
        except CreativeCodePatchContractError as exc:
            raise InventoryArtifactError("invalid_patch_request") from exc
        try:
            result = read_creative_code_patch_result(
                str(run_dir / creative_code_patch_builder.RESULT_FILE)
            )
            result = validate_creative_code_patch_result(result)
        except CreativeCodePatchContractError as exc:
            raise InventoryArtifactError("invalid_patch_result") from exc
        selected_variant = _read_json_object(
            run_dir / creative_code_patch_builder.SELECTED_VARIANT_FILE
        )
        patch_metadata = _read_json_object(
            run_dir / creative_code_patch_builder.PATCH_METADATA_FILE
        )
        patch_text = _read_text_file(run_dir / creative_code_patch_builder.CANDIDATE_PATCH_FILE)
        try:
            sidecar_summary = validate_creative_code_patch_run_sidecars(
                request=request,
                result=result,
                patch_text=patch_text,
                selected_variant=selected_variant,
                patch_metadata=patch_metadata,
                require_accepted=result["status"] == "accepted",
            )
        except CreativeCodePatchContractError as exc:
            raise InventoryArtifactError("invalid_patch_run_sidecar") from exc
    except InventoryArtifactError as exc:
        blockers.append(exc.code)
        _append_error(errors, path=run_dir, artifact_type="patch_run", error_code=exc.code)
        return entry

    workspace_summary = result["workspace_summary"]
    entry.update(
        {
            "valid": True,
            "result_id": result["result_id"],
            "request_id": request["request_id"],
            "base_commit_sha": result["base_commit_sha"],
            "status": result["status"],
            "failure_class": result["failure_class"],
            "promotion_ready": result["promotion_ready"],
            "sanitized": result["sanitized"],
            "patch_fingerprint": sidecar_summary["patch_fingerprint"],
            "changed_path_count": len(result["changed_paths"]),
            "workspace_proof": {
                "origin_removed": workspace_summary["origin_removed"],
                "checkout_destroyed": workspace_summary["checkout_destroyed"],
                "shared_tree_untouched": workspace_summary["shared_tree_untouched"],
            },
            "blockers": [],
        }
    )
    return entry


def _scan_patch_runs(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _inspect_patch_run(run_dir, errors)
        for run_dir in _iter_child_dirs(
            PATCH_RUNS_ROOT,
            errors=errors,
            artifact_type="patch_run",
        )
    ]


def _inspect_generation_receipt(
    receipt_path: Path,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        receipt_ref = _repo_ref(receipt_path)
    except InventoryArtifactError:
        receipt_ref = f"{CREATIVE_CODE_ROOT_REF}/patch_generation"
        blockers.append("unsafe_artifact_ref")
    entry = {
        "receipt_ref": receipt_ref,
        "valid": False,
        "receipt_id": None,
        "run_id": None,
        "result_id": None,
        "status": "invalid",
        "failure_class": None,
        "blockers": blockers,
    }
    if blockers:
        errors.append(
            _error_entry(
                artifact_ref=receipt_ref,
                artifact_type="generation_receipt",
                error_code=blockers[0],
            )
        )
        return entry
    try:
        receipt = generation_cli.validate_generation_receipt(_read_json_object(receipt_path))
        entry.update(
            {
                "receipt_id": receipt["receipt_id"],
                "run_id": receipt["run_id"],
                "result_id": receipt["result_id"],
                "status": receipt["status"],
                "failure_class": receipt["failure_class"],
            }
        )
        generation_cli.validate_generation_receipt_linked_artifacts(receipt)
    except (
        InventoryArtifactError,
        CreativeCodePatchWorkspaceError,
        generation_cli.CreativeCodePatchGenerationError,
    ) as exc:
        code = (
            exc.code if isinstance(exc, InventoryArtifactError) else "generation_receipt_mismatch"
        )
        entry["blockers"] = sorted(set([*blockers, code]))
        _append_error(
            errors,
            path=receipt_path,
            artifact_type="generation_receipt",
            error_code=code,
        )
        return entry
    entry["valid"] = True
    entry["blockers"] = []
    return entry


def _scan_generation_receipts(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _inspect_generation_receipt(path, errors)
        for path in _iter_named_files(
            PATCH_GENERATION_ROOT,
            filename=generation_cli.RECEIPT_FILENAME,
            errors=errors,
            artifact_type="generation_receipt",
        )
    ]


def _read_optional_promotion_json(
    promotion_dir: Path,
    filename: str,
    validator: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    path = promotion_dir / filename
    if not path.exists():
        return None, None
    try:
        return validator(_read_json_object(path)), None
    except (
        InventoryArtifactError,
        CreativeCodePRPromotionContractError,
    ):
        return None, f"invalid_{filename.removesuffix('.json')}"


def _inspect_promotion_dir(
    promotion_dir: Path,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    promotion_id = (
        promotion_dir.name if PROMOTION_ID_RE.fullmatch(promotion_dir.name) else "invalid"
    )
    blockers: list[str] = []
    try:
        promotion_ref = _repo_ref(promotion_dir)
    except InventoryArtifactError:
        promotion_ref = f"{CREATIVE_CODE_ROOT_REF}/promotions"
        blockers.append("unsafe_artifact_ref")
    entry = {
        "promotion_id": promotion_id,
        "promotion_ref": promotion_ref,
        "valid": False,
        "state": "in_progress",
        "receipt_id": None,
        "source_result_id": None,
        "pull_request_state": None,
        "pull_request_number": None,
        "head_branch": None,
        "blockers": blockers,
    }
    if promotion_id == "invalid":
        blockers.append("unsafe_promotion_id")
        _append_error(
            errors,
            path=promotion_dir,
            artifact_type="promotion_artifact",
            error_code="unsafe_promotion_id",
        )
        entry["blockers"] = sorted(set(blockers))
        return entry

    for filename, validator in (
        (PLAN_FILE, validate_creative_code_pr_promotion_plan),
        (VALIDATION_FILE, validate_creative_code_pr_promotion_validation),
        (APPROVAL_FILE, validate_creative_code_pr_promotion_approval),
    ):
        _payload, error_code = _read_optional_promotion_json(promotion_dir, filename, validator)
        if error_code:
            blockers.append(error_code)
            _append_error(
                errors,
                path=promotion_dir / filename,
                artifact_type="promotion_artifact",
                error_code=error_code,
            )

    receipt_path = promotion_dir / RECEIPT_FILE
    if receipt_path.exists():
        try:
            receipt = validate_creative_code_pr_promotion_receipt(_read_json_object(receipt_path))
        except (InventoryArtifactError, CreativeCodePRPromotionContractError):
            blockers.append("invalid_promotion_receipt")
            _append_error(
                errors,
                path=receipt_path,
                artifact_type="promotion_receipt",
                error_code="invalid_promotion_receipt",
            )
        else:
            entry.update(
                {
                    "valid": True,
                    "state": receipt["pull_request_state"],
                    "receipt_id": receipt["receipt_id"],
                    "source_result_id": receipt["source_result_id"],
                    "pull_request_state": receipt["pull_request_state"],
                    "pull_request_number": receipt["pull_request_number"],
                    "head_branch": receipt["head_branch"],
                }
            )
            if receipt["pull_request_state"] == "partial_failure":
                blockers.append("promotion_partial_failure")
    else:
        try:
            known_files = [
                child.name
                for child in promotion_dir.iterdir()
                if child.name in KNOWN_PROMOTION_FILES
            ]
        except OSError:
            blockers.append("unreadable_directory")
            _append_error(
                errors,
                path=promotion_dir,
                artifact_type="promotion_artifact",
                error_code="unreadable_directory",
            )
            known_files = []
        if known_files:
            blockers.append("promotion_in_progress")
    entry_blockers = sorted(set(blockers))
    entry["blockers"] = entry_blockers
    if entry_blockers and entry["valid"] is False:
        entry["state"] = (
            "invalid" if "invalid_promotion_receipt" in entry_blockers else "in_progress"
        )
    return entry


def _scan_promotion_artifacts(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _inspect_promotion_dir(promotion_dir, errors)
        for promotion_dir in _iter_child_dirs(
            PROMOTIONS_ROOT,
            errors=errors,
            artifact_type="promotion_artifact",
        )
    ]


def _empty_counts() -> dict[str, int]:
    return {
        "patch_runs_total": 0,
        "patch_runs_valid": 0,
        "patch_runs_accepted": 0,
        "patch_runs_rejected": 0,
        "patch_runs_invalid": 0,
        "generation_receipts_total": 0,
        "generation_receipts_valid": 0,
        "generation_receipts_invalid": 0,
        "promotion_dirs_total": 0,
        "promotion_receipts_completed": 0,
        "promotion_receipts_partial_failure": 0,
        "promotion_artifacts_in_progress": 0,
        "promotion_artifacts_invalid": 0,
        "read_errors": 0,
    }


def _annotate_patch_runs(
    patch_runs: list[dict[str, Any]],
    generation_receipts: list[dict[str, Any]],
    promotion_artifacts: list[dict[str, Any]],
    current_base_sha: str | None,
) -> None:
    generation_by_run: dict[str, list[dict[str, Any]]] = {}
    for receipt in generation_receipts:
        run_id = receipt.get("run_id")
        if isinstance(run_id, str):
            generation_by_run.setdefault(run_id, []).append(receipt)

    promotions_by_result: dict[str, list[dict[str, Any]]] = {}
    for promotion in promotion_artifacts:
        source_result_id = promotion.get("source_result_id")
        if isinstance(source_result_id, str):
            promotions_by_result.setdefault(source_result_id, []).append(promotion)

    for run in patch_runs:
        run_id = str(run["run_id"])
        result_id = run.get("result_id")
        generation_matches = generation_by_run.get(run_id, [])
        run["generation_receipt_ids"] = [
            str(receipt["receipt_id"])
            for receipt in generation_matches
            if isinstance(receipt.get("receipt_id"), str)
        ]
        run["promotion_receipt_ids"] = []
        run["promotion_linkage"] = "none"
        if isinstance(result_id, str):
            promotions = promotions_by_result.get(result_id, [])
            run["promotion_receipt_ids"] = [
                str(promotion["receipt_id"])
                for promotion in promotions
                if isinstance(promotion.get("receipt_id"), str)
            ]
            if any(promotion.get("state") == "open" for promotion in promotions):
                run["promotion_linkage"] = "completed"
            elif any(promotion.get("state") == "partial_failure" for promotion in promotions):
                run["promotion_linkage"] = "partial_failure"
            elif promotions:
                run["promotion_linkage"] = "invalid"
        blockers = set(run["blockers"])
        if any(receipt.get("valid") is False for receipt in generation_matches):
            blockers.add("generation_receipt_mismatch")
        if not run["valid"]:
            run["promotion_candidate_state"] = "invalid"
        elif run["status"] != "accepted":
            run["promotion_candidate_state"] = "rejected"
            blockers.add("patch_run_not_accepted")
        elif run["promotion_linkage"] == "completed":
            run["promotion_candidate_state"] = "already_promoted"
            blockers.add("promotion_receipt_exists")
        elif run["promotion_linkage"] in {"partial_failure", "invalid"}:
            run["promotion_candidate_state"] = "promotion_in_progress"
            blockers.add("promotion_in_progress")
        elif current_base_sha is None:
            run["promotion_candidate_state"] = "origin_main_unknown"
            blockers.add("origin_main_unavailable")
        elif run["base_commit_sha"] != current_base_sha:
            run["promotion_candidate_state"] = "base_sha_drift"
            blockers.add("base_sha_drift")
        else:
            run["promotion_candidate_state"] = "eligible"
        run["blockers"] = sorted(blockers)


def _build_cleanup_summary(
    patch_runs: list[dict[str, Any]],
    promotion_artifacts: list[dict[str, Any]],
    read_errors: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted_unpromoted = [
        str(run["run_id"])
        for run in patch_runs
        if run["valid"] and run["status"] == "accepted" and run["promotion_linkage"] != "completed"
    ]
    in_progress_promotions = [
        str(promotion["promotion_id"])
        for promotion in promotion_artifacts
        if promotion["state"] != "open" or promotion["blockers"]
    ]
    blockers: list[str] = []
    if accepted_unpromoted:
        blockers.append("accepted_run_unpromoted")
    if in_progress_promotions:
        blockers.append("promotion_in_progress")
    if read_errors:
        blockers.append("artifact_read_error")
    return {
        "safe": not blockers,
        "blockers": blockers,
        "accepted_unpromoted_run_ids": accepted_unpromoted,
        "in_progress_promotion_ids": in_progress_promotions,
    }


def _build_counts(
    patch_runs: list[dict[str, Any]],
    generation_receipts: list[dict[str, Any]],
    promotion_artifacts: list[dict[str, Any]],
    read_errors: list[dict[str, Any]],
) -> dict[str, int]:
    counts = _empty_counts()
    counts["patch_runs_total"] = len(patch_runs)
    counts["patch_runs_valid"] = sum(1 for run in patch_runs if run["valid"])
    counts["patch_runs_accepted"] = sum(1 for run in patch_runs if run["status"] == "accepted")
    counts["patch_runs_rejected"] = sum(1 for run in patch_runs if run["status"] == "rejected")
    counts["patch_runs_invalid"] = sum(1 for run in patch_runs if not run["valid"])
    counts["generation_receipts_total"] = len(generation_receipts)
    counts["generation_receipts_valid"] = sum(
        1 for receipt in generation_receipts if receipt["valid"]
    )
    counts["generation_receipts_invalid"] = sum(
        1 for receipt in generation_receipts if not receipt["valid"]
    )
    counts["promotion_dirs_total"] = len(promotion_artifacts)
    counts["promotion_receipts_completed"] = sum(
        1 for promotion in promotion_artifacts if promotion["state"] == "open"
    )
    counts["promotion_receipts_partial_failure"] = sum(
        1 for promotion in promotion_artifacts if promotion["state"] == "partial_failure"
    )
    counts["promotion_artifacts_in_progress"] = sum(
        1 for promotion in promotion_artifacts if promotion["state"] == "in_progress"
    )
    counts["promotion_artifacts_invalid"] = sum(
        1 for promotion in promotion_artifacts if promotion["state"] == "invalid"
    )
    counts["read_errors"] = len(read_errors)
    return counts


def build_creative_code_artifact_inventory_report(
    *,
    include_origin_main: bool = True,
) -> dict[str, Any]:
    """Build a sanitized read-only inventory report for local creative-code artifacts."""

    read_errors: list[dict[str, Any]] = []
    origin_main: dict[str, bool | str | None] = {
        "available": False,
        "sha": None,
        "error_code": None,
    }
    current_base_sha: str | None = None
    if include_origin_main:
        try:
            current_base_sha = current_origin_main_sha()
            origin_main = {"available": True, "sha": current_base_sha, "error_code": None}
        except InventoryArtifactError as exc:
            origin_main = {"available": False, "sha": None, "error_code": exc.code}
            read_errors.append(
                _error_entry(
                    artifact_ref=CREATIVE_CODE_ROOT_REF,
                    artifact_type="origin_main",
                    error_code=exc.code,
                )
            )

    patch_runs = _scan_patch_runs(read_errors)
    generation_receipts = _scan_generation_receipts(read_errors)
    promotion_artifacts = _scan_promotion_artifacts(read_errors)
    _annotate_patch_runs(patch_runs, generation_receipts, promotion_artifacts, current_base_sha)
    cleanup = _build_cleanup_summary(patch_runs, promotion_artifacts, read_errors)
    report = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "source_root_ref": CREATIVE_CODE_ROOT_REF,
        "origin_main": origin_main,
        "counts": _build_counts(
            patch_runs,
            generation_receipts,
            promotion_artifacts,
            read_errors,
        ),
        "patch_runs": patch_runs,
        "generation_receipts": generation_receipts,
        "promotion_artifacts": promotion_artifacts,
        "read_errors": read_errors,
        "cleanup": cleanup,
        "authority": {
            "inventory_only": True,
            "delete_artifacts": False,
            "create_patch_run": False,
            "promote_patch_run": False,
            "write_repository": False,
            "open_pull_request": False,
            "resolve_review_threads": False,
            "merge": False,
            "call_providers": False,
            "call_github": False,
        },
        "sanitized": True,
    }
    return validate_creative_code_artifact_inventory_report(report)


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected: Iterable[str],
    *,
    label: str,
) -> None:
    actual = set(payload)
    expected_set = set(expected)
    missing = sorted(expected_set - actual)
    extra = sorted(actual - expected_set)
    if missing:
        raise CreativeCodeArtifactInventoryError(f"{label} missing fields: {', '.join(missing)}")
    if extra:
        raise CreativeCodeArtifactInventoryError(f"{label} unsupported fields: {', '.join(extra)}")


def _reject_output_leaks(value: Any, *, label: str) -> None:
    if isinstance(value, str):
        if LEAK_TEXT_RE.search(value):
            raise CreativeCodeArtifactInventoryError(f"{label} contains unsafe output text.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_output_leaks(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_output_leaks(item, label=f"{label}.{key}")


def _require_bool(value: Any, *, expected: bool | None, label: str) -> bool:
    if not isinstance(value, bool):
        raise CreativeCodeArtifactInventoryError(f"{label} must be boolean.")
    if expected is not None and value is not expected:
        raise CreativeCodeArtifactInventoryError(f"{label} must be {expected}.")
    return value


def _require_optional_string(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise CreativeCodeArtifactInventoryError(f"{label} must be string or null.")
    return value


def _validate_counts(counts: Any) -> dict[str, int]:
    if not isinstance(counts, dict):
        raise CreativeCodeArtifactInventoryError("counts must be object.")
    _require_exact_keys(counts, _empty_counts(), label="counts")
    normalized: dict[str, int] = {}
    for key, value in counts.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CreativeCodeArtifactInventoryError(f"counts.{key} must be nonnegative int.")
        normalized[key] = value
    return normalized


def _validate_patch_run_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise CreativeCodeArtifactInventoryError("patch run entry must be object.")
    _require_exact_keys(
        entry,
        {
            "run_id",
            "run_ref",
            "valid",
            "result_id",
            "request_id",
            "base_commit_sha",
            "status",
            "failure_class",
            "promotion_ready",
            "sanitized",
            "patch_fingerprint",
            "changed_path_count",
            "workspace_proof",
            "generation_receipt_ids",
            "promotion_receipt_ids",
            "promotion_linkage",
            "promotion_candidate_state",
            "blockers",
        },
        label="patch_run",
    )
    if not isinstance(entry["run_id"], str) or not entry["run_id"]:
        raise CreativeCodeArtifactInventoryError("patch_run.run_id must be string.")
    _validate_artifact_ref(str(entry["run_ref"]))
    _require_bool(entry["valid"], expected=None, label="patch_run.valid")
    if entry["status"] not in {"accepted", "rejected", "invalid"}:
        raise CreativeCodeArtifactInventoryError("patch_run.status unsupported.")
    if entry["promotion_linkage"] not in {"none", "completed", "partial_failure", "invalid"}:
        raise CreativeCodeArtifactInventoryError("patch_run.promotion_linkage unsupported.")
    if entry["promotion_candidate_state"] not in {
        "eligible",
        "rejected",
        "invalid",
        "base_sha_drift",
        "already_promoted",
        "promotion_in_progress",
        "origin_main_unknown",
    }:
        raise CreativeCodeArtifactInventoryError("patch_run.promotion_candidate_state unsupported.")
    for key in ("result_id", "request_id", "base_commit_sha", "failure_class", "patch_fingerprint"):
        _require_optional_string(entry[key], label=f"patch_run.{key}")
    if entry["base_commit_sha"] is not None and not SHA_RE.fullmatch(entry["base_commit_sha"]):
        raise CreativeCodeArtifactInventoryError("patch_run.base_commit_sha invalid.")
    if entry["patch_fingerprint"] is not None and not SHA256_RE.fullmatch(
        entry["patch_fingerprint"]
    ):
        raise CreativeCodeArtifactInventoryError("patch_run.patch_fingerprint invalid.")
    if entry["promotion_ready"] is not None:
        _require_bool(entry["promotion_ready"], expected=False, label="patch_run.promotion_ready")
    if entry["sanitized"] is not None:
        _require_bool(entry["sanitized"], expected=True, label="patch_run.sanitized")
    if not isinstance(entry["changed_path_count"], int) or entry["changed_path_count"] < 0:
        raise CreativeCodeArtifactInventoryError("patch_run.changed_path_count invalid.")
    proof = entry["workspace_proof"]
    if not isinstance(proof, dict):
        raise CreativeCodeArtifactInventoryError("patch_run.workspace_proof must be object.")
    _require_exact_keys(
        proof,
        {"origin_removed", "checkout_destroyed", "shared_tree_untouched"},
        label="patch_run.workspace_proof",
    )
    for key in proof:
        _require_bool(proof[key], expected=None, label=f"patch_run.workspace_proof.{key}")
    for list_key in ("generation_receipt_ids", "promotion_receipt_ids", "blockers"):
        if not isinstance(entry[list_key], list) or not all(
            isinstance(item, str) for item in entry[list_key]
        ):
            raise CreativeCodeArtifactInventoryError(f"patch_run.{list_key} invalid.")
    return dict(entry)


def _validate_generation_receipt_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise CreativeCodeArtifactInventoryError("generation receipt entry must be object.")
    _require_exact_keys(
        entry,
        {
            "receipt_ref",
            "valid",
            "receipt_id",
            "run_id",
            "result_id",
            "status",
            "failure_class",
            "blockers",
        },
        label="generation_receipt",
    )
    _validate_artifact_ref(str(entry["receipt_ref"]))
    _require_bool(entry["valid"], expected=None, label="generation_receipt.valid")
    if entry["status"] not in {"accepted", "rejected", "invalid"}:
        raise CreativeCodeArtifactInventoryError("generation_receipt.status unsupported.")
    for key in ("receipt_id", "run_id", "result_id", "failure_class"):
        _require_optional_string(entry[key], label=f"generation_receipt.{key}")
    if not isinstance(entry["blockers"], list) or not all(
        isinstance(item, str) for item in entry["blockers"]
    ):
        raise CreativeCodeArtifactInventoryError("generation_receipt.blockers invalid.")
    return dict(entry)


def _validate_promotion_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise CreativeCodeArtifactInventoryError("promotion entry must be object.")
    _require_exact_keys(
        entry,
        {
            "promotion_id",
            "promotion_ref",
            "valid",
            "state",
            "receipt_id",
            "source_result_id",
            "pull_request_state",
            "pull_request_number",
            "head_branch",
            "blockers",
        },
        label="promotion_artifact",
    )
    if not isinstance(entry["promotion_id"], str) or not entry["promotion_id"]:
        raise CreativeCodeArtifactInventoryError("promotion_id must be string.")
    _validate_artifact_ref(str(entry["promotion_ref"]))
    _require_bool(entry["valid"], expected=None, label="promotion_artifact.valid")
    if entry["state"] not in {"open", "partial_failure", "in_progress", "invalid"}:
        raise CreativeCodeArtifactInventoryError("promotion_artifact.state unsupported.")
    for key in ("receipt_id", "source_result_id", "pull_request_state", "head_branch"):
        _require_optional_string(entry[key], label=f"promotion_artifact.{key}")
    pull_request_number = entry["pull_request_number"]
    if pull_request_number is not None and (
        not isinstance(pull_request_number, int)
        or isinstance(pull_request_number, bool)
        or pull_request_number < 0
    ):
        raise CreativeCodeArtifactInventoryError("promotion_artifact.pull_request_number invalid.")
    state = entry["state"]
    pull_request_state = entry["pull_request_state"]
    if state in {"open", "partial_failure"}:
        if pull_request_state != state:
            raise CreativeCodeArtifactInventoryError(
                "promotion_artifact.pull_request_state does not match state."
            )
        if pull_request_number is None or (state == "open" and pull_request_number < 1):
            raise CreativeCodeArtifactInventoryError(
                "promotion_artifact.pull_request_number invalid."
            )
    elif pull_request_state is not None or pull_request_number is not None:
        raise CreativeCodeArtifactInventoryError(
            "promotion_artifact inactive state fields must be null."
        )
    if entry["head_branch"] is not None and not EXPERIMENT_BRANCH_RE.fullmatch(
        entry["head_branch"]
    ):
        raise CreativeCodeArtifactInventoryError("promotion_artifact.head_branch invalid.")
    if not isinstance(entry["blockers"], list) or not all(
        isinstance(item, str) for item in entry["blockers"]
    ):
        raise CreativeCodeArtifactInventoryError("promotion_artifact.blockers invalid.")
    return dict(entry)


def _validate_read_error(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise CreativeCodeArtifactInventoryError("read_error must be object.")
    _require_exact_keys(
        entry,
        {"artifact_ref", "artifact_type", "error_code", "error_fingerprint"},
        label="read_error",
    )
    _validate_artifact_ref(str(entry["artifact_ref"]))
    for key in ("artifact_type", "error_code"):
        if not isinstance(entry[key], str) or not entry[key]:
            raise CreativeCodeArtifactInventoryError(f"read_error.{key} invalid.")
    if not isinstance(entry["error_fingerprint"], str) or not SHA256_RE.fullmatch(
        entry["error_fingerprint"]
    ):
        raise CreativeCodeArtifactInventoryError("read_error.error_fingerprint invalid.")
    return dict(entry)


def validate_creative_code_artifact_inventory_report(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the closed, sanitized inventory report contract."""

    _require_exact_keys(
        payload,
        {
            "schema_version",
            "artifact_type",
            "policy_version",
            "source_root_ref",
            "origin_main",
            "counts",
            "patch_runs",
            "generation_receipts",
            "promotion_artifacts",
            "read_errors",
            "cleanup",
            "authority",
            "sanitized",
        },
        label=ARTIFACT_TYPE,
    )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise CreativeCodeArtifactInventoryError("schema_version invalid.")
    if payload["artifact_type"] != ARTIFACT_TYPE:
        raise CreativeCodeArtifactInventoryError("artifact_type invalid.")
    if payload["policy_version"] != POLICY_VERSION:
        raise CreativeCodeArtifactInventoryError("policy_version invalid.")
    if payload["source_root_ref"] != CREATIVE_CODE_ROOT_REF:
        raise CreativeCodeArtifactInventoryError("source_root_ref invalid.")
    origin_main = payload["origin_main"]
    if not isinstance(origin_main, dict):
        raise CreativeCodeArtifactInventoryError("origin_main must be object.")
    _require_exact_keys(origin_main, {"available", "sha", "error_code"}, label="origin_main")
    _require_bool(origin_main["available"], expected=None, label="origin_main.available")
    if origin_main["sha"] is not None and not SHA_RE.fullmatch(origin_main["sha"]):
        raise CreativeCodeArtifactInventoryError("origin_main.sha invalid.")
    _require_optional_string(origin_main["error_code"], label="origin_main.error_code")
    counts = _validate_counts(payload["counts"])
    patch_runs = [_validate_patch_run_entry(entry) for entry in payload["patch_runs"]]
    generation_receipts = [
        _validate_generation_receipt_entry(entry) for entry in payload["generation_receipts"]
    ]
    promotion_artifacts = [
        _validate_promotion_entry(entry) for entry in payload["promotion_artifacts"]
    ]
    read_errors = [_validate_read_error(entry) for entry in payload["read_errors"]]
    cleanup = payload["cleanup"]
    if not isinstance(cleanup, dict):
        raise CreativeCodeArtifactInventoryError("cleanup must be object.")
    _require_exact_keys(
        cleanup,
        {
            "safe",
            "blockers",
            "accepted_unpromoted_run_ids",
            "in_progress_promotion_ids",
        },
        label="cleanup",
    )
    _require_bool(cleanup["safe"], expected=None, label="cleanup.safe")
    for key in ("blockers", "accepted_unpromoted_run_ids", "in_progress_promotion_ids"):
        if not isinstance(cleanup[key], list) or not all(
            isinstance(item, str) for item in cleanup[key]
        ):
            raise CreativeCodeArtifactInventoryError(f"cleanup.{key} invalid.")
    authority = payload["authority"]
    if not isinstance(authority, dict):
        raise CreativeCodeArtifactInventoryError("authority must be object.")
    _require_exact_keys(
        authority,
        {
            "inventory_only",
            "delete_artifacts",
            "create_patch_run",
            "promote_patch_run",
            "write_repository",
            "open_pull_request",
            "resolve_review_threads",
            "merge",
            "call_providers",
            "call_github",
        },
        label="authority",
    )
    _require_bool(authority["inventory_only"], expected=True, label="authority.inventory_only")
    for key, value in authority.items():
        if key != "inventory_only":
            _require_bool(value, expected=False, label=f"authority.{key}")
    _require_bool(payload["sanitized"], expected=True, label="sanitized")
    expected_counts = _build_counts(
        patch_runs, generation_receipts, promotion_artifacts, read_errors
    )
    if counts != expected_counts:
        raise CreativeCodeArtifactInventoryError("counts do not match report entries.")
    _reject_output_leaks(payload, label=ARTIFACT_TYPE)
    return {
        **dict(payload),
        "counts": counts,
        "patch_runs": patch_runs,
        "generation_receipts": generation_receipts,
        "promotion_artifacts": promotion_artifacts,
        "read_errors": read_errors,
    }


def _format_list(values: list[str]) -> str:
    return ",".join(values) if values else "<none>"


def render_text_report(report: Mapping[str, Any]) -> str:
    counts = report["counts"]
    cleanup = report["cleanup"]
    accepted_ids = [
        run["run_id"]
        for run in report["patch_runs"]
        if run["valid"] and run["status"] == "accepted"
    ]
    lines = [
        SUCCESS_STATUS_OUTPUT,
        f"ROOT_REF={report['source_root_ref']}",
        f"PATCH_RUNS_TOTAL={counts['patch_runs_total']}",
        f"PATCH_RUNS_ACCEPTED={counts['patch_runs_accepted']}",
        f"PATCH_RUNS_REJECTED={counts['patch_runs_rejected']}",
        f"PATCH_RUNS_INVALID={counts['patch_runs_invalid']}",
        f"ACCEPTED_RUNS={_format_list(accepted_ids)}",
        f"PROMOTION_RECEIPTS_COMPLETED={counts['promotion_receipts_completed']}",
        f"PROMOTION_ARTIFACTS_IN_PROGRESS={counts['promotion_artifacts_in_progress']}",
        f"READ_ERRORS={counts['read_errors']}",
        f"CLEANUP_SAFE={str(cleanup['safe']).lower()}",
        f"CLEANUP_BLOCKERS={_format_list(cleanup['blockers'])}",
    ]
    for run in report["patch_runs"]:
        lines.append(
            "PATCH_RUN "
            f"run_id={run['run_id']} "
            f"status={run['status']} "
            f"state={run['promotion_candidate_state']} "
            f"promotion_linkage={run['promotion_linkage']} "
            f"blockers={_format_list(run['blockers'])}"
        )
    return "\n".join(lines) + "\n"


def assert_ready_for_promotion(patch_run_id: str) -> tuple[bool, list[str]]:
    if not RUN_ID_RE.fullmatch(patch_run_id):
        raise InventoryUsageError("patch_run_id must be a safe run id")
    report = build_creative_code_artifact_inventory_report()
    matches = [run for run in report["patch_runs"] if run["run_id"] == patch_run_id]
    if not matches:
        return False, ["patch_run_not_found"]
    run = matches[0]
    blockers = set(run["blockers"])
    if report["read_errors"]:
        blockers.add("artifact_read_error")
    if not run["valid"]:
        blockers.add("invalid_patch_run_sidecar")
    if run["status"] != "accepted":
        blockers.add("patch_run_not_accepted")
    if run["failure_class"] is not None:
        blockers.add("patch_run_failure_class_present")
    proof = run["workspace_proof"]
    if not (
        proof["origin_removed"] and proof["checkout_destroyed"] and proof["shared_tree_untouched"]
    ):
        blockers.add("workspace_proof_missing")
    if run["promotion_linkage"] == "completed":
        blockers.add("promotion_receipt_exists")
    if run["promotion_linkage"] == "partial_failure":
        blockers.add("promotion_partial_failure")
    if run["promotion_linkage"] == "invalid":
        blockers.add("promotion_in_progress")
    if run["promotion_candidate_state"] == "base_sha_drift":
        blockers.add("base_sha_drift")
    if run["promotion_candidate_state"] == "origin_main_unknown":
        blockers.add("origin_main_unavailable")
    return not blockers, sorted(blockers)


def assert_ready_for_cleanup() -> tuple[bool, list[str]]:
    report = build_creative_code_artifact_inventory_report()
    cleanup = report["cleanup"]
    return bool(cleanup["safe"]), list(cleanup["blockers"])


def _status(args: argparse.Namespace) -> int:
    report = build_creative_code_artifact_inventory_report()
    if args.format == "json":
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print(render_text_report(report), end="")
    return 0


def _assert_ready_for_promotion(args: argparse.Namespace) -> int:
    try:
        ok, blockers = assert_ready_for_promotion(args.patch_run_id)
    except InventoryUsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if ok:
        print(PROMOTION_READY_OUTPUT)
        return 0
    print("FAIL: " + ",".join(blockers), file=sys.stderr)
    return 1


def _assert_ready_for_cleanup(_args: argparse.Namespace) -> int:
    ok, blockers = assert_ready_for_cleanup()
    if ok:
        print(CLEANUP_READY_OUTPUT)
        return 0
    print("FAIL: " + ",".join(blockers), file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only creative-code local artifact inventory guard."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--format", choices=("text", "json"), default="text")
    status_parser.set_defaults(func=_status)

    promotion_parser = subparsers.add_parser("assert-ready-for-promotion")
    promotion_parser.add_argument("--patch-run-id", required=True)
    promotion_parser.set_defaults(func=_assert_ready_for_promotion)

    cleanup_parser = subparsers.add_parser("assert-ready-for-cleanup")
    cleanup_parser.set_defaults(func=_assert_ready_for_cleanup)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CreativeCodeArtifactInventoryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

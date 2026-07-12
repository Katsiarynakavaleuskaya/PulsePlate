#!/usr/bin/env python3
"""Attach reviewed skeptic evidence and explicitly finalize PR-1 specifications."""

from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import Any, Mapping, Sequence, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_spec_pipeline
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    build_creative_code_specification_bundle,
    validate_creative_code_specification_bundle,
    validate_source_candidate_packet,
)
from scripts.orchestration.creative_hypothesis_spec_bridge import (
    BRIDGE_FILENAME,
    CANDIDATE_FILENAME,
    METRICS_FILENAME,
)
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    PREPARED_STATUS,
    PREPARE_FILENAMES,
    CreativeHypothesisSpecBridgeError,
    validate_bridge_metrics,
    validate_creative_hypothesis_specification_bridge,
)
from scripts.orchestration.creative_pilot_workspace_contract import (
    ADAPTIVE_PR1_RESUME_TYPE,
    CreativePilotContractError,
    validate_adaptive_pr1_resume_binding,
    validate_adaptive_pr1_variant_intake,
)
from scripts.orchestration.creative_specification_skeptic_review_contract import (
    ATTACHMENT_ARTIFACT_TYPE,
    FINALIZE_RECEIPT_ARTIFACT_TYPE,
    REVIEWED_RUN_DIRNAME,
    CreativeSpecificationSkepticReviewError,
    build_finalize_receipt,
    build_skeptic_review_attachment,
    build_skeptic_review_coverage,
    normalize_skeptic_reviews_for_pr1,
    validate_agent_skeptic_reviews_input,
    validate_finalize_receipt,
    validate_skeptic_review_attachment,
)

SPEC_BRIDGE_ROOT: Path = creative_code_spec_pipeline.ARTIFACT_ROOT / "spec_bridge"
ADAPTIVE_RESUME_FILENAME = "creative_adaptive_pr1_resume_binding.json"
ADAPTIVE_INTAKE_FILENAME = "creative_adaptive_pr1_variant_intake.json"
ATTACHMENT_FILENAME = "skeptic_review_attachment.json"
BUNDLE_FILENAME = "creative_code_specification_bundle.json"
FINALIZE_RECEIPT_FILENAME = "finalize_receipt.json"
ATTACH_SUCCESS_OUTPUT = "PASS: creative specification skeptic reviews attached"
VALIDATE_SUCCESS_OUTPUT = "PASS: creative specification skeptic review attachment valid"
FINALIZE_SUCCESS_OUTPUT = "PASS: creative specification finalize receipt written"
REVIEWED_RUN_FILENAMES = frozenset(
    {
        "source_packet.json",
        "variants.json",
        "skeptic_reviews.json",
        "context_pack.json",
        ATTACHMENT_FILENAME,
        BUNDLE_FILENAME,
        FINALIZE_RECEIPT_FILENAME,
    }
)


class CreativeSpecificationSkepticReviewCliError(ValueError):
    """Raised when reviewed finalize CLI file I/O cannot safely complete."""


def _require_typed_json_object(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must be a JSON object.")
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise CreativeSpecificationSkepticReviewCliError(f"{label} must use string keys.")
        normalized[key] = item
    return normalized


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
            raise CreativeSpecificationSkepticReviewCliError(f"{label} must not traverse symlinks.")


def _ensure_spec_bridge_root() -> Path:
    try:
        return cast(
            Path,
            creative_code_spec_pipeline._resolve_artifact_dir(
                SPEC_BRIDGE_ROOT,
                create=True,
            ),
        )
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            "spec bridge root could not be opened safely."
        ) from exc


def _resolve_repo_json_file(raw_path: Path, *, label: str) -> Path:
    candidate = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    _reject_symlink_components(candidate, label=label)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must exist.") from exc
    if not _is_relative_to(resolved, REPO_ROOT.resolve()):
        raise CreativeSpecificationSkepticReviewCliError(
            f"{label} must stay inside the repository."
        )
    if not resolved.is_file() or resolved.suffix != ".json":
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must be a JSON file.")
    return resolved


def _resolve_repo_artifact_ref(ref: str, *, label: str, expect_dir: bool = False) -> Path:
    candidate = REPO_ROOT / ref
    _reject_symlink_components(candidate, label=label)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must exist.") from exc
    repo_root = REPO_ROOT.resolve()
    artifact_root = creative_code_spec_pipeline.ARTIFACT_ROOT.resolve(strict=False)
    if not _is_relative_to(resolved, repo_root) or not _is_relative_to(resolved, artifact_root):
        raise CreativeSpecificationSkepticReviewCliError(
            f"{label} must stay under creative-code artifacts."
        )
    if expect_dir:
        if not resolved.is_dir():
            raise CreativeSpecificationSkepticReviewCliError(f"{label} must be a directory.")
    elif not resolved.is_file() or resolved.suffix != ".json":
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must be a JSON file.")
    return resolved


def _artifact_ref(path: Path) -> str:
    try:
        _candidate, parts = creative_code_spec_pipeline._candidate_and_repo_parts(
            path,
            allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
            label="artifact ref",
        )
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            "artifact ref must stay under creative-code artifacts."
        ) from exc
    return Path(*parts).as_posix()


def _read_json_file(path: Path) -> Any:
    try:
        return creative_code_spec_pipeline._read_json_file(
            path,
            allowed_root=REPO_ROOT,
            label="JSON artifact",
        )
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        message = str(exc).replace("duplicate JSON key:", "duplicate key:")
        raise CreativeSpecificationSkepticReviewCliError(message) from exc


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = _read_json_file(path)
    if not isinstance(payload, dict):
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must be a JSON object.")
    return payload


def _read_json_array(path: Path, *, label: str) -> list[Any]:
    payload = _read_json_file(path)
    if not isinstance(payload, list):
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must be a JSON array.")
    return payload


def _read_prepared_bridge(bridge_path: Path) -> dict[str, Any]:
    bridge_file = _resolve_repo_json_file(bridge_path, label="bridge input")
    raw_bridge = _read_json_object(bridge_file, label="bridge input")
    artifact_type = raw_bridge.get("artifact_type")
    if bridge_file.name == ADAPTIVE_RESUME_FILENAME and artifact_type == ADAPTIVE_PR1_RESUME_TYPE:
        return _read_prepared_adaptive_resume(bridge_file, raw_bridge)
    if (
        bridge_file.name != BRIDGE_FILENAME
        or artifact_type != "creative_hypothesis_specification_bridge"
    ):
        raise CreativeSpecificationSkepticReviewCliError(
            f"bridge input must point to canonical {BRIDGE_FILENAME} or "
            f"{ADAPTIVE_RESUME_FILENAME} with matching artifact_type."
        )
    bridge = validate_creative_hypothesis_specification_bridge(raw_bridge)
    bridge_dir = _prepared_bridge_dir(bridge, bridge_file)
    candidate = _read_json_object(bridge_dir / CANDIDATE_FILENAME, label="candidate packet")
    metrics = validate_bridge_metrics(
        _read_json_object(bridge_dir / METRICS_FILENAME, label="bridge metrics")
    )
    _assert_prepared_bridge_state(bridge=bridge, candidate=candidate, metrics=metrics)
    source_run_dir = _resolve_repo_artifact_ref(
        str(cast(Mapping[str, Any], bridge["spec_prepare"])["run_dir_ref"]),
        label="spec_prepare ref",
        expect_dir=True,
    )
    _reject_unexpected_entries(source_run_dir, allowed=set(PREPARE_FILENAMES), label="spec_prepare")
    source_packet = _read_json_object(source_run_dir / "source_packet.json", label="source packet")
    variants = _read_json_array(source_run_dir / "variants.json", label="variants")
    pending_reviews = _read_json_array(
        source_run_dir / "skeptic_reviews.json",
        label="pending skeptic reviews",
    )
    context_pack = _read_json_object(source_run_dir / "context_pack.json", label="context pack")
    _assert_prepared_artifacts(
        bridge=bridge,
        candidate=candidate,
        metrics=metrics,
        source_packet=source_packet,
        variants=variants,
        pending_reviews=pending_reviews,
    )
    return {
        "bridge": bridge,
        "bridge_dir": bridge_dir,
        "bridge_path": bridge_file,
        "candidate": candidate,
        "candidate_path": bridge_dir / CANDIDATE_FILENAME,
        "metrics": metrics,
        "metrics_path": bridge_dir / METRICS_FILENAME,
        "source_run_dir": source_run_dir,
        "source_packet": source_packet,
        "variants": variants,
        "pending_reviews": pending_reviews,
        "context_pack": context_pack,
    }


def _read_prepared_adaptive_resume(
    bridge_file: Path, raw_bridge: Mapping[str, Any]
) -> dict[str, Any]:
    bridge_dir = bridge_file.parent
    _reject_unexpected_entries(
        bridge_dir,
        allowed={
            ADAPTIVE_RESUME_FILENAME,
            ADAPTIVE_INTAKE_FILENAME,
            CANDIDATE_FILENAME,
            "spec_prepare",
            REVIEWED_RUN_DIRNAME,
        },
        label="adaptive resume",
        allow_retained_pre_finalize=True,
    )
    _validate_adaptive_retained_pre_finalize_run(bridge_dir)
    candidate_path = bridge_dir / CANDIDATE_FILENAME
    intake_path = bridge_dir / ADAPTIVE_INTAKE_FILENAME
    candidate = validate_source_candidate_packet(
        _read_json_object(candidate_path, label="candidate packet")
    )
    intake = validate_adaptive_pr1_variant_intake(
        _read_json_object(intake_path, label="adaptive intake"), candidate=candidate
    )
    bridge = validate_adaptive_pr1_resume_binding(
        raw_bridge, intake=intake, candidate=candidate, revalidate_git=True
    )
    bridge_dir = _prepared_bridge_dir(bridge, bridge_file)
    source_run_dir = _resolve_repo_artifact_ref(
        str(cast(Mapping[str, Any], bridge["spec_prepare"])["run_dir_ref"]),
        label="spec_prepare ref",
        expect_dir=True,
    )
    if source_run_dir.resolve(strict=True) != (bridge_dir / "spec_prepare").resolve(strict=True):
        raise CreativeSpecificationSkepticReviewCliError(
            "spec_prepare_ref must point to adaptive resume spec_prepare."
        )
    _reject_unexpected_entries(source_run_dir, allowed=set(PREPARE_FILENAMES), label="spec_prepare")
    try:
        creative_code_spec_pipeline.validate_exact_prepare_artifacts(
            run_dir=source_run_dir,
            expected_packet=candidate,
            expected_variants=cast(Sequence[Mapping[str, Any]], intake["materialized_variants"]),
        )
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        raise CreativeSpecificationSkepticReviewCliError(str(exc)) from exc
    source_packet = _read_json_object(source_run_dir / "source_packet.json", label="source packet")
    variants = _read_json_array(source_run_dir / "variants.json", label="variants")
    pending_reviews = _read_json_array(
        source_run_dir / "skeptic_reviews.json", label="pending skeptic reviews"
    )
    context_pack = _read_json_object(source_run_dir / "context_pack.json", label="context pack")
    normalized_packet = validate_source_candidate_packet(source_packet)
    if normalized_packet != candidate:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: adaptive source packet must equal candidate."
        )
    if variants != intake["materialized_variants"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: adaptive variants must equal intake materialization."
        )
    try:
        build_creative_code_specification_bundle(
            source_packet=source_packet,
            variants=cast(Sequence[Mapping[str, Any]], variants),
            skeptic_reviews=cast(Sequence[Mapping[str, Any]], pending_reviews),
        )
    except CreativeCodeSpecificationError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            f"prepared spec_prepare artifacts are not valid PR-1 inputs: {exc}"
        ) from exc
    return {
        "bridge": bridge,
        "bridge_dir": bridge_dir,
        "bridge_path": bridge_file,
        "candidate": candidate,
        "candidate_path": candidate_path,
        "metrics": intake,
        "metrics_path": intake_path,
        "source_run_dir": source_run_dir,
        "source_packet": source_packet,
        "variants": variants,
        "pending_reviews": pending_reviews,
        "context_pack": context_pack,
    }


def _prepared_bridge_dir(bridge: Mapping[str, Any], bridge_file: Path) -> Path:
    root = _ensure_spec_bridge_root()
    expected_dir = root / str(bridge["bridge_id"])
    try:
        expected_resolved = expected_dir.resolve(strict=True)
        bridge_parent = bridge_file.parent.resolve(strict=True)
    except OSError as exc:
        raise CreativeSpecificationSkepticReviewCliError("bridge directory must exist.") from exc
    if expected_resolved != bridge_parent:
        raise CreativeSpecificationSkepticReviewCliError(
            "bridge path must be the canonical spec_bridge/<bridge-id> artifact."
        )
    return bridge_parent


def _assert_prepared_bridge_state(
    *,
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> None:
    spec_prepare = cast(Mapping[str, Any], bridge["spec_prepare"])
    if (
        spec_prepare["prepared"] is not True
        or spec_prepare["finalized"] is not False
        or spec_prepare["next_allowed_action"] != "agent_skeptic_review"
    ):
        raise CreativeSpecificationSkepticReviewCliError(
            "bridge must be prepared and waiting for agent_skeptic_review."
        )
    normalized_packet = validate_source_candidate_packet(candidate)
    candidate_ref = cast(Mapping[str, Any], bridge["candidate_packet"])
    if normalized_packet["candidate_id"] != candidate_ref["candidate_id"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: candidate id does not match bridge."
        )
    if fingerprint_payload(dict(normalized_packet)) != candidate_ref["candidate_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: candidate fingerprint does not match bridge."
        )
    if metrics["status"] != PREPARED_STATUS or metrics["blocked_reason"] is not None:
        raise CreativeSpecificationSkepticReviewCliError(
            "bridge metrics must be prepared with no blocked reason."
        )
    if metrics["bridge_id"] != bridge["bridge_id"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: metrics bridge id does not match bridge."
        )
    if metrics["candidate_id"] != normalized_packet["candidate_id"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: metrics candidate id does not match candidate."
        )
    metric_source = cast(Mapping[str, Any], metrics["source"])
    if metric_source["candidate_fingerprint"] != fingerprint_payload(dict(normalized_packet)):
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: metrics candidate fingerprint does not match candidate."
        )


def _assert_prepared_artifacts(
    *,
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    metrics: Mapping[str, Any],
    source_packet: Mapping[str, Any],
    variants: Sequence[Any],
    pending_reviews: Sequence[Any],
) -> None:
    normalized_candidate = validate_source_candidate_packet(candidate)
    normalized_source_packet = validate_source_candidate_packet(source_packet)
    if normalized_source_packet != normalized_candidate:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source_packet.json must match the bridge candidate packet."
        )
    expected_variant_count = int(normalized_candidate["variant_count"])
    if len(variants) != expected_variant_count:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: variants must match candidate variant_count."
        )
    counts = cast(Mapping[str, Any], metrics["counts"])
    if counts["prepare_files_written"] != len(PREPARE_FILENAMES):
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: metrics prepare_files_written does not match spec_prepare."
        )
    if counts["pending_skeptic_review_count"] != _pending_skeptic_review_count(pending_reviews):
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: metrics pending_skeptic_review_count does not match spec_prepare."
        )
    try:
        build_creative_code_specification_bundle(
            source_packet=source_packet,
            variants=cast(Sequence[Mapping[str, Any]], variants),
            skeptic_reviews=cast(Sequence[Mapping[str, Any]], pending_reviews),
        )
    except CreativeCodeSpecificationError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            f"prepared spec_prepare artifacts are not valid PR-1 inputs: {exc}"
        ) from exc
    if (
        fingerprint_payload(dict(normalized_source_packet))
        != cast(Mapping[str, Any], bridge["candidate_packet"])["candidate_fingerprint"]
    ):
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: prepared source packet fingerprint does not match bridge."
        )


def _pending_skeptic_review_count(reviews: Sequence[Any]) -> int:
    return sum(
        1
        for row in reviews
        if isinstance(row, dict)
        and row.get("decision") != "pass"
        and "skeptic_review_required" in row.get("blockers", [])
    )


def _is_retained_pre_finalize_run(name: str) -> bool:
    prefix = f".{REVIEWED_RUN_DIRNAME}."
    suffix = ".pre-finalize"
    if not name.startswith(prefix) or not name.endswith(suffix):
        return False
    token = name[len(prefix) : -len(suffix)]
    return len(token) == 16 and all(character in "0123456789abcdef" for character in token)


def _reject_unexpected_entries(
    path: Path,
    *,
    allowed: set[str],
    label: str,
    allow_retained_pre_finalize: bool = False,
) -> None:
    parent_fd = -1
    directory_fd = -1
    try:
        parent_fd, name, _candidate = creative_code_spec_pipeline._open_pinned_parent(
            path,
            allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
            create=False,
            label=label,
        )
        try:
            directory_fd = os.open(
                name,
                creative_code_spec_pipeline._directory_flags(),
                dir_fd=parent_fd,
            )
        except FileNotFoundError:
            return
        entries = os.listdir(directory_fd)
        symlink_children = sorted(
            name
            for name in entries
            if stat.S_ISLNK(os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_mode)
        )
        if symlink_children:
            raise CreativeSpecificationSkepticReviewCliError(
                f"{label} contains symlink artifact(s): {', '.join(symlink_children)}."
            )
        retained = {
            name
            for name in entries
            if allow_retained_pre_finalize and _is_retained_pre_finalize_run(name)
        }
        non_directory_retained = sorted(
            name
            for name in retained
            if not stat.S_ISDIR(os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_mode)
        )
        if non_directory_retained:
            raise CreativeSpecificationSkepticReviewCliError(
                f"{label} retained pre-finalize artifact(s) must be directories: "
                f"{', '.join(non_directory_retained)}."
            )
        unexpected = sorted(
            name for name in entries if name not in allowed and name not in retained
        )
        if unexpected:
            raise CreativeSpecificationSkepticReviewCliError(
                f"{label} contains unexpected artifact(s): {', '.join(unexpected)}."
            )
    except FileNotFoundError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            f"{label} changed during inspection."
        ) from exc
    except CreativeSpecificationSkepticReviewCliError:
        raise
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            f"{label} could not be opened safely."
        ) from exc
    except (OSError, NotImplementedError) as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            f"{label} could not be inspected safely."
        ) from exc
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(directory_fd, parent_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                f"{label} could not be closed safely."
            ) from close_error


def _validate_adaptive_retained_pre_finalize_run(bridge_dir: Path) -> None:
    parent_fd = -1
    bridge_fd = -1
    canonical_fd = -1
    retained_fd = -1
    expected_names = {
        "source_packet.json",
        "variants.json",
        "skeptic_reviews.json",
        "context_pack.json",
        ATTACHMENT_FILENAME,
    }
    try:
        parent_fd, name, _candidate = creative_code_spec_pipeline._open_pinned_parent(
            bridge_dir,
            allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
            create=False,
            label="adaptive retained pre-finalize evidence",
        )
        bridge_fd = os.open(
            name,
            creative_code_spec_pipeline._directory_flags(),
            dir_fd=parent_fd,
        )
        retained_names = sorted(
            entry for entry in os.listdir(bridge_fd) if _is_retained_pre_finalize_run(entry)
        )
        if len(retained_names) > 1:
            raise CreativeSpecificationSkepticReviewCliError(
                "adaptive resume must contain at most one retained pre-finalize run."
            )
        if not retained_names:
            return
        canonical_fd = os.open(
            REVIEWED_RUN_DIRNAME,
            creative_code_spec_pipeline._directory_flags(),
            dir_fd=bridge_fd,
        )
        retained_fd = os.open(
            retained_names[0],
            creative_code_spec_pipeline._directory_flags(),
            dir_fd=bridge_fd,
        )
        if set(os.listdir(retained_fd)) != expected_names:
            raise CreativeSpecificationSkepticReviewCliError(
                "adaptive retained pre-finalize run must contain the exact five input artifacts."
            )
        if not expected_names.issubset(set(os.listdir(canonical_fd))):
            raise CreativeSpecificationSkepticReviewCliError(
                "adaptive canonical reviewed run is missing retained input artifacts."
            )
        for filename in sorted(expected_names):
            retained_payload = _read_json_at(retained_fd, filename)
            canonical_payload = _read_json_at(canonical_fd, filename)
            if fingerprint_payload(retained_payload) != fingerprint_payload(canonical_payload):
                raise CreativeSpecificationSkepticReviewCliError(
                    f"fingerprint_mismatch: adaptive retained {filename} diverges from canonical."
                )
        if set(os.listdir(retained_fd)) != expected_names:
            raise CreativeSpecificationSkepticReviewCliError(
                "adaptive retained pre-finalize run changed during validation."
            )
        if retained_names != sorted(
            entry for entry in os.listdir(bridge_fd) if _is_retained_pre_finalize_run(entry)
        ):
            raise CreativeSpecificationSkepticReviewCliError(
                "adaptive retained pre-finalize evidence changed during validation."
            )
    except FileNotFoundError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            "adaptive retained pre-finalize evidence is incomplete."
        ) from exc
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(
            retained_fd,
            canonical_fd,
            bridge_fd,
            parent_fd,
        )
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                "adaptive retained pre-finalize evidence could not be closed safely."
            ) from close_error


def _reviewed_run_dir(bridge_dir: Path) -> Path:
    candidate = bridge_dir / REVIEWED_RUN_DIRNAME
    _reject_symlink_components(candidate, label="reviewed finalize run")
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_candidate, SPEC_BRIDGE_ROOT.resolve(strict=False)):
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run must stay under creative-code spec_bridge artifacts."
        )
    return Path(candidate)


DirectoryIdentity = tuple[int, int]
FinalizeFileSnapshot = tuple[int, int, int, int, int]


def _create_pinned_reviewed_run(path: Path) -> tuple[int, int, DirectoryIdentity, str]:
    parent_fd = -1
    reviewed_fd = -1
    try:
        parent_fd, name, _candidate = creative_code_spec_pipeline._open_pinned_parent(
            path,
            allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
            create=False,
            label="reviewed finalize run",
        )
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize run already exists; remove the local sibling artifact to rerun."
            )
        staging_name: str | None = None
        for _attempt in range(32):
            candidate = f".{name}.{secrets.token_hex(8)}.staging"
            try:
                os.mkdir(candidate, mode=0o700, dir_fd=parent_fd)
                staging_name = candidate
                break
            except FileExistsError:
                continue
        if staging_name is None:
            raise CreativeSpecificationSkepticReviewCliError(
                "unable to allocate reviewed finalize staging directory."
            )
        created_identity: DirectoryIdentity | None = None
        try:
            created = os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
            created_identity = (created.st_dev, created.st_ino)
            reviewed_fd = os.open(
                staging_name,
                creative_code_spec_pipeline._directory_flags(),
                dir_fd=parent_fd,
            )
            info = os.fstat(reviewed_fd)
            if (info.st_dev, info.st_ino) != created_identity:
                raise CreativeSpecificationSkepticReviewCliError(
                    "reviewed finalize run identity changed during creation."
                )
        except Exception as primary_error:
            cleanup_error: Exception | None = None
            retained_name: str | None = None
            try:
                if created_identity is None:
                    raise CreativeSpecificationSkepticReviewCliError(
                        "reviewed finalize run cleanup identity unavailable."
                    )
                retained_name = _quarantine_pinned_reviewed_run(
                    parent_fd,
                    name=staging_name,
                    expected_identity=created_identity,
                )
            except Exception as exc:
                cleanup_error = exc
            if cleanup_error is not None:
                raise CreativeSpecificationSkepticReviewCliError(
                    "reviewed finalize run could not be created safely; "
                    f"cleanup_diagnostic={cleanup_error}"
                ) from primary_error
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize run could not be created safely; "
                f"failure_artifact_retained={retained_name}"
            ) from primary_error
        result = (parent_fd, reviewed_fd, (info.st_dev, info.st_ino), staging_name)
        parent_fd = -1
        reviewed_fd = -1
        return result
    except CreativeSpecificationSkepticReviewCliError:
        raise
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run parent could not be opened safely."
        ) from exc
    except (OSError, NotImplementedError) as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run could not be created safely."
        ) from exc
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize run descriptors could not be closed safely."
            ) from close_error


def _quarantine_pinned_reviewed_run(
    parent_fd: int,
    *,
    name: str,
    expected_identity: DirectoryIdentity,
) -> str:
    current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != expected_identity:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run quarantine identity changed."
        )
    quarantine_name = f".{REVIEWED_RUN_DIRNAME}.{secrets.token_hex(8)}.failed"
    _kernel_rename_noreplace(
        parent_fd,
        name,
        quarantine_name,
        collision_message="reviewed finalize failure quarantine already exists.",
    )
    quarantined = os.stat(quarantine_name, dir_fd=parent_fd, follow_symlinks=False)
    if (quarantined.st_dev, quarantined.st_ino) != expected_identity:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run identity changed during quarantine."
        )
    os.fsync(parent_fd)
    return quarantine_name


def _kernel_rename_noreplace(
    parent_fd: int,
    source_name: str,
    destination_name: str,
    *,
    collision_message: str = (
        "reviewed finalize run already exists; remove the local sibling artifact to rerun."
    ),
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename_noreplace = getattr(libc, "renameatx_np", None)
        flag = 0x00000004  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        rename_noreplace = getattr(libc, "renameat2", None)
        flag = 1  # RENAME_NOREPLACE
    else:
        rename_noreplace = None
        flag = 0
    if rename_noreplace is None:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize publication requires kernel no-replace rename."
        )
    rename_noreplace.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename_noreplace.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = rename_noreplace(
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(destination_name),
        flag,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise CreativeSpecificationSkepticReviewCliError(collision_message)
        raise CreativeSpecificationSkepticReviewCliError(
            f"reviewed finalize run no-replace publication failed: errno={error_number}."
        )


def _kernel_rename_exchange(
    parent_fd: int,
    source_name: str,
    destination_name: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename_exchange = getattr(libc, "renameatx_np", None)
        flag = 0x00000002  # RENAME_SWAP
    elif sys.platform.startswith("linux"):
        rename_exchange = getattr(libc, "renameat2", None)
        flag = 2  # RENAME_EXCHANGE
    else:
        rename_exchange = None
        flag = 0
    if rename_exchange is None:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize publication requires kernel directory exchange."
        )
    rename_exchange.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename_exchange.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = rename_exchange(
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(destination_name),
        flag,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise CreativeSpecificationSkepticReviewCliError(
            f"reviewed finalize directory exchange failed: errno={error_number}."
        )


def _publish_pinned_reviewed_run(
    parent_fd: int,
    *,
    staging_name: str,
    destination_name: str,
    expected_identity: DirectoryIdentity,
) -> None:
    staging = os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
    if (staging.st_dev, staging.st_ino) != expected_identity:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize staging identity changed before publication."
        )
    _kernel_rename_noreplace(parent_fd, staging_name, destination_name)


def _assert_published_reviewed_run_identity(
    parent_fd: int,
    *,
    destination_name: str,
    expected_identity: DirectoryIdentity,
) -> None:
    published = os.stat(destination_name, dir_fd=parent_fd, follow_symlinks=False)
    if (published.st_dev, published.st_ino) != expected_identity:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run identity changed during publication."
        )


def _write_json_at(directory_fd: int, filename: str, payload: Any) -> None:
    if Path(filename).name != filename or not filename.endswith(".json"):
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed artifact filename must be a safe JSON basename."
        )
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    file_fd = -1
    temp_name: str | None = None
    retained_name: str | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= creative_code_spec_pipeline._required_open_flag("O_NOFOLLOW")
        flags |= getattr(os, "O_CLOEXEC", 0)
        for _attempt in range(32):
            candidate = f".{filename}.{secrets.token_hex(8)}.tmp"
            try:
                file_fd = os.open(candidate, flags, 0o600, dir_fd=directory_fd)
                temp_name = candidate
                retained_name = candidate
                break
            except FileExistsError:
                continue
        else:
            raise CreativeSpecificationSkepticReviewCliError(
                "unable to allocate reviewed artifact temp file."
            )
        created = os.fstat(file_fd)
        created_identity = (created.st_dev, created.st_ino)
        if not stat.S_ISREG(created.st_mode):
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed artifact temp entry must be a regular file."
            )
        with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
            file_fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        staged = os.stat(temp_name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(staged.st_mode) or (staged.st_dev, staged.st_ino) != created_identity:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed artifact temp identity changed before publication."
            )
        _kernel_rename_noreplace(
            directory_fd,
            temp_name,
            filename,
            collision_message="reviewed artifact already exists; refusing overwrite.",
        )
        temp_name = None
        retained_name = filename
        published = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(published.st_mode)
            or (published.st_dev, published.st_ino) != created_identity
        ):
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed artifact identity changed during publication."
            )
        os.fsync(directory_fd)
        retained_name = None
    except CreativeSpecificationSkepticReviewCliError as exc:
        if retained_name is None:
            raise
        raise CreativeSpecificationSkepticReviewCliError(
            f"{exc}; failure_artifact_retained={retained_name}"
        ) from exc
    except (OSError, ValueError, RecursionError, NotImplementedError) as exc:
        suffix = f"; failure_artifact_retained={retained_name}" if retained_name is not None else ""
        raise CreativeSpecificationSkepticReviewCliError(
            f"Unable to write reviewed JSON artifact safely{suffix}."
        ) from exc
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(file_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                "Unable to close reviewed JSON artifact safely."
            ) from close_error


def _read_json_at(directory_fd: int, filename: str) -> Any:
    file_fd = -1
    try:
        flags = os.O_RDONLY | creative_code_spec_pipeline._required_open_flag("O_NOFOLLOW")
        flags |= getattr(os, "O_CLOEXEC", 0)
        file_fd = os.open(filename, flags, dir_fd=directory_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise CreativeSpecificationSkepticReviewCliError(
                f"reviewed artifact {filename} must be a regular file."
            )
        with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
            file_fd = -1
            return json.loads(
                handle.read(),
                object_pairs_hook=creative_code_spec_pipeline._reject_duplicate_json_object_keys,
            )
    except CreativeSpecificationSkepticReviewCliError:
        raise
    except (
        creative_code_spec_pipeline.CreativeCodeSpecPipelineError,
        OSError,
        UnicodeDecodeError,
        ValueError,
        RecursionError,
        NotImplementedError,
    ) as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            f"reviewed artifact {filename} could not be read safely."
        ) from exc
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(file_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                f"reviewed artifact {filename} could not be closed safely."
            ) from close_error


def _finalize_file_snapshot(info: os.stat_result) -> FinalizeFileSnapshot:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _open_pinned_finalize_output(
    directory_fd: int,
    filename: str,
) -> tuple[int, FinalizeFileSnapshot]:
    file_fd = -1
    try:
        flags = os.O_RDONLY | creative_code_spec_pipeline._required_open_flag("O_NOFOLLOW")
        flags |= getattr(os, "O_CLOEXEC", 0)
        file_fd = os.open(filename, flags, dir_fd=directory_fd)
        opened = os.fstat(file_fd)
        published = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(published.st_mode)
            or (published.st_dev, published.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise CreativeSpecificationSkepticReviewCliError(
                f"reviewed finalize output {filename} identity changed during pinning."
            )
        return file_fd, _finalize_file_snapshot(opened)
    except Exception:
        close_error = creative_code_spec_pipeline._close_descriptors(file_fd)
        if close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                f"reviewed finalize output {filename} could not be closed safely."
            ) from close_error
        raise


def _read_json_from_pinned_finalize_output(file_fd: int, filename: str) -> Any:
    try:
        chunks: list[bytes] = []
        offset = 0
        while True:
            chunk = os.pread(file_fd, 64 * 1024, offset)
            if not chunk:
                break
            chunks.append(chunk)
            offset += len(chunk)
        return json.loads(
            b"".join(chunks).decode("utf-8"),
            object_pairs_hook=creative_code_spec_pipeline._reject_duplicate_json_object_keys,
        )
    except (
        creative_code_spec_pipeline.CreativeCodeSpecPipelineError,
        OSError,
        UnicodeDecodeError,
        ValueError,
        RecursionError,
        NotImplementedError,
    ) as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            f"reviewed finalize output {filename} could not be read safely."
        ) from exc


def _assert_exact_reviewed_run_payloads(
    reviewed_fd: int,
    *,
    expected_payloads: Mapping[str, Any],
) -> None:
    expected_names = set(expected_payloads)
    if set(os.listdir(reviewed_fd)) != expected_names:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run must contain the exact initial artifact set."
        )
    for filename, expected_payload in expected_payloads.items():
        observed = _read_json_at(reviewed_fd, filename)
        try:
            matches = fingerprint_payload(observed) == fingerprint_payload(expected_payload)
        except (TypeError, ValueError):
            matches = False
        if not matches:
            raise CreativeSpecificationSkepticReviewCliError(
                f"reviewed artifact {filename} fingerprint mismatch."
            )
    if set(os.listdir(reviewed_fd)) != expected_names:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run must contain the exact initial artifact set."
        )


def _assert_canonical_reviewed_run_identity(
    path: Path,
    *,
    expected_identity: DirectoryIdentity,
) -> None:
    parent_fd = -1
    reviewed_fd = -1
    try:
        parent_fd, name, _candidate = creative_code_spec_pipeline._open_pinned_parent(
            path,
            allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
            create=False,
            label="reviewed finalize run",
        )
        reviewed_fd = os.open(
            name,
            creative_code_spec_pipeline._directory_flags(),
            dir_fd=parent_fd,
        )
        info = os.fstat(reviewed_fd)
        if (info.st_dev, info.st_ino) != expected_identity:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize run canonical identity changed."
            )
    except CreativeSpecificationSkepticReviewCliError:
        raise
    except (
        creative_code_spec_pipeline.CreativeCodeSpecPipelineError,
        OSError,
        NotImplementedError,
    ) as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run canonical identity changed."
        ) from exc
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize run identity descriptors could not be closed safely."
            ) from close_error


def _attach_from_bridge(bridge_path: Path, reviews_path: Path) -> dict[str, Any]:
    prepared = _read_prepared_bridge(bridge_path)
    review_input_path = _resolve_repo_json_file(reviews_path, label="skeptic review input")
    review_input = validate_agent_skeptic_reviews_input(
        _read_json_object(review_input_path, label="skeptic review input")
    )
    bridge = cast(dict[str, Any], prepared["bridge"])
    candidate = cast(dict[str, Any], prepared["candidate"])
    source_packet = cast(dict[str, Any], prepared["source_packet"])
    variants = cast(list[Mapping[str, Any]], prepared["variants"])
    expected = {
        "source_bridge_id": bridge["bridge_id"],
        "source_bridge_fingerprint": fingerprint_payload(bridge),
        "source_candidate_id": candidate["candidate_id"],
        "source_candidate_fingerprint": fingerprint_payload(candidate),
        "source_packet_fingerprint": fingerprint_payload(source_packet),
        "variants_fingerprint": fingerprint_payload(variants),
    }
    for key, value in expected.items():
        if review_input[key] != value:
            raise CreativeSpecificationSkepticReviewCliError(
                f"fingerprint_mismatch: review input {key} does not match prepared artifacts."
            )
    normalized_reviews = normalize_skeptic_reviews_for_pr1(
        review_input=review_input,
        source_packet=source_packet,
        variants=variants,
    )
    reviewed_dir = _reviewed_run_dir(cast(Path, prepared["bridge_dir"]))
    reviewed_parent_fd, reviewed_fd, reviewed_identity, staging_name = _create_pinned_reviewed_run(
        reviewed_dir
    )
    cleanup_name: str | None = staging_name
    try:
        reviewed_source_packet = reviewed_dir / "source_packet.json"
        reviewed_variants = reviewed_dir / "variants.json"
        reviewed_reviews = reviewed_dir / "skeptic_reviews.json"
        reviewed_context_pack = reviewed_dir / "context_pack.json"
        attachment_path = reviewed_dir / ATTACHMENT_FILENAME
        attachment = _require_typed_json_object(
            build_skeptic_review_attachment(
                bridge_id=str(bridge["bridge_id"]),
                bridge_fingerprint=fingerprint_payload(bridge),
                bridge_ref=_artifact_ref(cast(Path, prepared["bridge_path"])),
                candidate_id=str(candidate["candidate_id"]),
                candidate_fingerprint=fingerprint_payload(candidate),
                candidate_ref=_artifact_ref(cast(Path, prepared["candidate_path"])),
                metrics_id=str(
                    cast(Mapping[str, Any], prepared["metrics"]).get("metrics_id")
                    or cast(Mapping[str, Any], prepared["metrics"])["intake_id"]
                ),
                metrics_fingerprint=fingerprint_payload(cast(dict[str, Any], prepared["metrics"])),
                metrics_ref=_artifact_ref(cast(Path, prepared["metrics_path"])),
                spec_prepare_ref=_artifact_ref(cast(Path, prepared["source_run_dir"])),
                source_packet_ref=_artifact_ref(
                    cast(Path, prepared["source_run_dir"]) / "source_packet.json"
                ),
                source_packet_fingerprint=fingerprint_payload(source_packet),
                variants_ref=_artifact_ref(
                    cast(Path, prepared["source_run_dir"]) / "variants.json"
                ),
                variants_fingerprint=fingerprint_payload(variants),
                pending_reviews_ref=_artifact_ref(
                    cast(Path, prepared["source_run_dir"]) / "skeptic_reviews.json"
                ),
                pending_reviews_fingerprint=fingerprint_payload(
                    cast(Sequence[Any], prepared["pending_reviews"])
                ),
                context_pack_ref=_artifact_ref(
                    cast(Path, prepared["source_run_dir"]) / "context_pack.json"
                ),
                context_pack_fingerprint=fingerprint_payload(
                    cast(dict[str, Any], prepared["context_pack"])
                ),
                reviewed_run_dir_ref=_artifact_ref(reviewed_dir),
                reviewed_source_packet_ref=_artifact_ref(reviewed_source_packet),
                reviewed_variants_ref=_artifact_ref(reviewed_variants),
                reviewed_reviews_ref=_artifact_ref(reviewed_reviews),
                reviewed_context_pack_ref=_artifact_ref(reviewed_context_pack),
                normalized_reviews=normalized_reviews,
                variant_count=len(variants),
            ),
            label="skeptic review attachment",
        )
        _write_json_at(reviewed_fd, reviewed_source_packet.name, source_packet)
        _write_json_at(reviewed_fd, reviewed_variants.name, variants)
        _write_json_at(reviewed_fd, reviewed_reviews.name, normalized_reviews)
        _write_json_at(
            reviewed_fd,
            reviewed_context_pack.name,
            cast(dict[str, Any], prepared["context_pack"]),
        )
        _write_json_at(reviewed_fd, attachment_path.name, attachment)
        _assert_exact_reviewed_run_payloads(
            reviewed_fd,
            expected_payloads={
                reviewed_source_packet.name: source_packet,
                reviewed_variants.name: variants,
                reviewed_reviews.name: normalized_reviews,
                reviewed_context_pack.name: cast(dict[str, Any], prepared["context_pack"]),
                attachment_path.name: attachment,
            },
        )
        _publish_pinned_reviewed_run(
            reviewed_parent_fd,
            staging_name=staging_name,
            destination_name=reviewed_dir.name,
            expected_identity=reviewed_identity,
        )
        # The no-replace rename has consumed staging_name. Until the published
        # inode is verified, preserve an unknown canonical entry for inspection
        # instead of risking deletion of an attacker-controlled replacement.
        cleanup_name = None
        _assert_published_reviewed_run_identity(
            reviewed_parent_fd,
            destination_name=reviewed_dir.name,
            expected_identity=reviewed_identity,
        )
        cleanup_name = reviewed_dir.name
        os.fsync(reviewed_parent_fd)
        _assert_canonical_reviewed_run_identity(
            reviewed_dir,
            expected_identity=reviewed_identity,
        )
        _assert_exact_reviewed_run_payloads(
            reviewed_fd,
            expected_payloads={
                reviewed_source_packet.name: source_packet,
                reviewed_variants.name: variants,
                reviewed_reviews.name: normalized_reviews,
                reviewed_context_pack.name: cast(dict[str, Any], prepared["context_pack"]),
                attachment_path.name: attachment,
            },
        )
        _assert_canonical_reviewed_run_identity(
            reviewed_dir,
            expected_identity=reviewed_identity,
        )
    except Exception as primary_error:
        cleanup_error: Exception | None = None
        retained_name: str | None = reviewed_dir.name if cleanup_name is None else None
        try:
            if cleanup_name is not None:
                retained_name = _quarantine_pinned_reviewed_run(
                    reviewed_parent_fd,
                    name=cleanup_name,
                    expected_identity=reviewed_identity,
                )
        except Exception as exc:
            cleanup_error = exc
        finally:
            close_error = creative_code_spec_pipeline._close_descriptors(
                reviewed_fd,
                reviewed_parent_fd,
            )
            cleanup_error = cleanup_error or close_error
        if cleanup_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                f"{primary_error}; cleanup_diagnostic={cleanup_error}"
            ) from primary_error
        raise CreativeSpecificationSkepticReviewCliError(
            f"{primary_error}; failure_artifact_retained={retained_name}"
        ) from primary_error
    close_error = creative_code_spec_pipeline._close_descriptors(
        reviewed_fd,
        reviewed_parent_fd,
    )
    if close_error is not None:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run descriptors could not be closed safely."
        ) from close_error
    return attachment


def _validate_attachment_artifacts(
    attachment_path: Path,
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    attachment_file = _resolve_repo_json_file(attachment_path, label="attachment input")
    attachment = validate_skeptic_review_attachment(
        _read_json_object(attachment_file, label="attachment input")
    )
    reviewed_run = cast(Mapping[str, Any], attachment["reviewed_run"])
    reviewed_dir = _resolve_repo_artifact_ref(
        str(reviewed_run["run_dir_ref"]),
        label="reviewed run dir",
        expect_dir=True,
    )
    if attachment_file.parent.resolve(strict=True) != reviewed_dir.resolve(strict=True):
        raise CreativeSpecificationSkepticReviewCliError(
            "attachment must be stored inside its reviewed_run_dir_ref."
        )
    canonical_attachment = reviewed_dir / ATTACHMENT_FILENAME
    if attachment_file.name != ATTACHMENT_FILENAME:
        raise CreativeSpecificationSkepticReviewCliError(
            f"attachment input must be the canonical {ATTACHMENT_FILENAME} artifact."
        )
    _reject_symlink_components(canonical_attachment, label="canonical attachment")
    if attachment_file.resolve(strict=True) != canonical_attachment.resolve(strict=True):
        raise CreativeSpecificationSkepticReviewCliError(
            f"attachment input must be the canonical {ATTACHMENT_FILENAME} artifact."
        )
    _reject_unexpected_entries(
        reviewed_dir,
        allowed=set(REVIEWED_RUN_FILENAMES),
        label="reviewed finalize run",
    )
    source = cast(Mapping[str, Any], attachment["source"])
    source_bridge_path = _resolve_repo_artifact_ref(
        str(source["bridge_ref"]),
        label="source bridge ref",
    )
    source_bridge_payload = _read_json_object(source_bridge_path, label="source bridge")
    supported_source = (
        source_bridge_path.name == BRIDGE_FILENAME
        and source_bridge_payload.get("artifact_type") == "creative_hypothesis_specification_bridge"
    ) or (
        source_bridge_path.name == ADAPTIVE_RESUME_FILENAME
        and source_bridge_payload.get("artifact_type") == ADAPTIVE_PR1_RESUME_TYPE
    )
    if not supported_source:
        raise CreativeSpecificationSkepticReviewCliError(
            f"source bridge ref must point to canonical {BRIDGE_FILENAME} or "
            f"{ADAPTIVE_RESUME_FILENAME} with matching artifact_type."
        )
    prepared_source = _read_prepared_bridge(source_bridge_path)
    source_bridge = cast(Mapping[str, Any], prepared_source["bridge"])
    if source_bridge["bridge_id"] != source["bridge_id"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source bridge id does not match attachment."
        )
    if fingerprint_payload(source_bridge) != source["bridge_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source bridge fingerprint does not match attachment."
        )
    source_bridge_candidate = cast(Mapping[str, Any], source_bridge["candidate_packet"])
    if source_bridge_candidate["candidate_id"] != source["candidate_id"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source candidate id does not match bridge."
        )
    if source_bridge_candidate["candidate_fingerprint"] != source["candidate_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source candidate fingerprint does not match bridge."
        )
    if source_bridge_candidate["candidate_packet_ref"] != source["candidate_ref"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source candidate ref does not match bridge."
        )
    expected_reviewed_dir = source_bridge_path.parent / REVIEWED_RUN_DIRNAME
    if reviewed_dir.resolve(strict=True) != expected_reviewed_dir.resolve(strict=False):
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed_run_dir_ref must be the sibling of the source bridge artifact."
        )
    expected_metrics_name = (
        ADAPTIVE_INTAKE_FILENAME
        if source_bridge_path.name == ADAPTIVE_RESUME_FILENAME
        else METRICS_FILENAME
    )
    expected_metrics_ref = _artifact_ref(source_bridge_path.parent / expected_metrics_name)
    if source["metrics_ref"] != expected_metrics_ref:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source metrics ref does not match bridge layout."
        )
    source_bridge_prepare = cast(Mapping[str, Any], source_bridge["spec_prepare"])
    if source_bridge_prepare["run_dir_ref"] != source["spec_prepare_ref"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: source spec_prepare ref does not match bridge."
        )
    source_spec_prepare_dir = _resolve_repo_artifact_ref(
        str(source["spec_prepare_ref"]),
        label="source spec_prepare ref",
        expect_dir=True,
    )
    expected_spec_prepare_dir = source_bridge_path.parent / "spec_prepare"
    if source_spec_prepare_dir.resolve(strict=True) != expected_spec_prepare_dir.resolve(
        strict=True
    ):
        raise CreativeSpecificationSkepticReviewCliError(
            "spec_prepare_ref must point to the canonical source spec_prepare artifact."
        )
    _reject_unexpected_entries(
        source_spec_prepare_dir,
        allowed=set(PREPARE_FILENAMES),
        label="source spec_prepare",
    )
    expected_source_refs = {
        "source_packet_ref": source_spec_prepare_dir / "source_packet.json",
        "variants_ref": source_spec_prepare_dir / "variants.json",
        "pending_reviews_ref": source_spec_prepare_dir / "skeptic_reviews.json",
        "context_pack_ref": source_spec_prepare_dir / "context_pack.json",
    }
    for key, expected_path in expected_source_refs.items():
        if source[key] != _artifact_ref(expected_path):
            raise CreativeSpecificationSkepticReviewCliError(
                f"fingerprint_mismatch: source {key} does not match spec_prepare layout."
            )
    source_packet = _read_json_object(reviewed_dir / "source_packet.json", label="source packet")
    variants = _read_json_array(reviewed_dir / "variants.json", label="variants")
    reviews = _read_json_array(reviewed_dir / "skeptic_reviews.json", label="skeptic reviews")
    context_pack = _read_json_object(reviewed_dir / "context_pack.json", label="context pack")
    _assert_reviewed_ref(
        str(reviewed_run["source_packet_ref"]),
        reviewed_dir / "source_packet.json",
        "reviewed source_packet",
    )
    _assert_reviewed_ref(
        str(reviewed_run["variants_ref"]),
        reviewed_dir / "variants.json",
        "reviewed variants",
    )
    _assert_reviewed_ref(
        str(reviewed_run["skeptic_reviews_ref"]),
        reviewed_dir / "skeptic_reviews.json",
        "reviewed skeptic_reviews",
    )
    _assert_reviewed_ref(
        str(reviewed_run["context_pack_ref"]),
        reviewed_dir / "context_pack.json",
        "reviewed context_pack",
    )
    _assert_artifact_ref(
        str(source["bridge_ref"]),
        expected_payload=None,
        expected_fingerprint=str(source["bridge_fingerprint"]),
        label="bridge",
    )
    _assert_artifact_ref(
        str(source["candidate_ref"]),
        expected_payload=None,
        expected_fingerprint=str(source["candidate_fingerprint"]),
        label="candidate",
    )
    _assert_artifact_ref(
        str(source["metrics_ref"]),
        expected_payload=None,
        expected_fingerprint=str(source["metrics_fingerprint"]),
        label="metrics",
    )
    _assert_artifact_ref(
        str(source["source_packet_ref"]),
        expected_payload=source_packet,
        expected_fingerprint=str(source["source_packet_fingerprint"]),
        label="source_packet",
    )
    _assert_artifact_ref(
        str(source["variants_ref"]),
        expected_payload=variants,
        expected_fingerprint=str(source["variants_fingerprint"]),
        label="variants",
    )
    _assert_artifact_ref(
        str(source["pending_reviews_ref"]),
        expected_payload=None,
        expected_fingerprint=str(source["pending_reviews_fingerprint"]),
        label="pending_reviews",
    )
    _assert_artifact_ref(
        str(source["context_pack_ref"]),
        expected_payload=context_pack,
        expected_fingerprint=str(source["context_pack_fingerprint"]),
        label="context_pack",
    )
    if fingerprint_payload(reviews) != reviewed_run["normalized_reviews_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: reviewed skeptic_reviews fingerprint does not match attachment."
        )
    try:
        build_creative_code_specification_bundle(
            source_packet=source_packet,
            variants=cast(Sequence[Mapping[str, Any]], variants),
            skeptic_reviews=cast(Sequence[Mapping[str, Any]], reviews),
        )
    except CreativeCodeSpecificationError as exc:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run cannot build a valid CreativeCodeSpecificationBundle."
        ) from exc
    expected_coverage = build_skeptic_review_coverage(
        normalized_reviews=cast(Sequence[Mapping[str, Any]], reviews),
        variant_count=len(variants),
    )
    if attachment["coverage"] != expected_coverage:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: attachment coverage does not match reviewed artifacts."
        )
    if fingerprint_payload(source_packet) != source["source_packet_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: reviewed source packet does not match attachment."
        )
    if fingerprint_payload(variants) != source["variants_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: reviewed variants do not match attachment."
        )
    return (
        attachment,
        reviewed_dir,
        {
            "source_packet.json": source_packet,
            "variants.json": variants,
            "skeptic_reviews.json": reviews,
            "context_pack.json": context_pack,
            ATTACHMENT_FILENAME: attachment,
        },
    )


def _read_pinned_reviewed_inputs(
    reviewed_fd: int,
    *,
    expected_payloads: Mapping[str, Any],
) -> dict[str, Any]:
    expected_names = set(expected_payloads)
    observed_names = set(os.listdir(reviewed_fd))
    if not expected_names.issubset(observed_names):
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize pinned inputs are incomplete."
        )
    if observed_names - set(REVIEWED_RUN_FILENAMES):
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run contains unexpected artifacts."
        )
    observed: dict[str, Any] = {}
    for filename, expected_payload in expected_payloads.items():
        payload = _read_json_at(reviewed_fd, filename)
        try:
            matches = fingerprint_payload(payload) == fingerprint_payload(expected_payload)
        except (TypeError, ValueError):
            matches = False
        if not matches:
            raise CreativeSpecificationSkepticReviewCliError(
                f"fingerprint_mismatch: pinned reviewed {filename} changed after validation."
            )
        observed[filename] = payload
    if set(os.listdir(reviewed_fd)) != observed_names:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run changed during pinned inspection."
        )
    return observed


def _create_pinned_finalize_staging(
    parent_fd: int,
) -> tuple[int, DirectoryIdentity, str]:
    staging_fd = -1
    staging_name: str | None = None
    try:
        for _attempt in range(32):
            candidate = f".{REVIEWED_RUN_DIRNAME}.{secrets.token_hex(8)}.pre-finalize"
            try:
                os.mkdir(candidate, mode=0o700, dir_fd=parent_fd)
                staging_name = candidate
                break
            except FileExistsError:
                continue
        if staging_name is None:
            raise CreativeSpecificationSkepticReviewCliError(
                "unable to allocate reviewed finalize exchange directory."
            )
        created = os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        created_identity = (created.st_dev, created.st_ino)
        staging_fd = os.open(
            staging_name,
            creative_code_spec_pipeline._directory_flags(),
            dir_fd=parent_fd,
        )
        opened = os.fstat(staging_fd)
        if (
            not stat.S_ISDIR(created.st_mode)
            or not stat.S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != created_identity
        ):
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize exchange directory identity changed during creation."
            )
        result = (staging_fd, created_identity, staging_name)
        staging_fd = -1
        return result
    except CreativeSpecificationSkepticReviewCliError as exc:
        if staging_name is None or "failure_artifact_retained=" in str(exc):
            raise
        raise CreativeSpecificationSkepticReviewCliError(
            f"{exc}; failure_artifact_retained={staging_name}"
        ) from exc
    except (OSError, NotImplementedError) as exc:
        suffix = f"; failure_artifact_retained={staging_name}" if staging_name else ""
        raise CreativeSpecificationSkepticReviewCliError(
            f"reviewed finalize exchange directory could not be created safely{suffix}."
        ) from exc
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(staging_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize exchange directory could not be closed safely."
            ) from close_error


def _assert_parent_entry_identity(
    parent_fd: int,
    *,
    name: str,
    expected_identity: DirectoryIdentity,
    label: str,
) -> None:
    observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if (
        not stat.S_ISDIR(observed.st_mode)
        or (observed.st_dev, observed.st_ino) != expected_identity
    ):
        raise CreativeSpecificationSkepticReviewCliError(f"{label} identity changed.")


def _assert_pinned_finalize_outputs(
    reviewed_fd: int,
    *,
    expected_bundle: Mapping[str, Any],
    expected_receipt: Mapping[str, Any],
) -> None:
    expected_names = set(REVIEWED_RUN_FILENAMES)
    if set(os.listdir(reviewed_fd)) != expected_names:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run must contain the exact finalized artifact set."
        )
    bundle_fd = -1
    receipt_fd = -1
    try:
        bundle_fd, bundle_snapshot = _open_pinned_finalize_output(
            reviewed_fd,
            BUNDLE_FILENAME,
        )
        receipt_fd, receipt_snapshot = _open_pinned_finalize_output(
            reviewed_fd,
            FINALIZE_RECEIPT_FILENAME,
        )
        expected_outputs = (
            (
                bundle_fd,
                BUNDLE_FILENAME,
                bundle_snapshot,
                expected_bundle,
                validate_creative_code_specification_bundle,
            ),
            (
                receipt_fd,
                FINALIZE_RECEIPT_FILENAME,
                receipt_snapshot,
                expected_receipt,
                validate_finalize_receipt,
            ),
        )
        for _pass in range(2):
            for file_fd, filename, _snapshot, expected_payload, validator in expected_outputs:
                observed = validator(
                    cast(
                        Mapping[str, Any],
                        _read_json_from_pinned_finalize_output(file_fd, filename),
                    )
                )
                if fingerprint_payload(observed) != fingerprint_payload(expected_payload):
                    raise CreativeSpecificationSkepticReviewCliError(
                        f"fingerprint_mismatch: pinned finalize {filename} changed before success."
                    )
        for file_fd, filename, _snapshot, expected_payload, validator in expected_outputs:
            observed = validator(
                cast(
                    Mapping[str, Any],
                    _read_json_from_pinned_finalize_output(file_fd, filename),
                )
            )
            if fingerprint_payload(observed) != fingerprint_payload(expected_payload):
                raise CreativeSpecificationSkepticReviewCliError(
                    f"fingerprint_mismatch: pinned finalize {filename} changed during terminal seal."
                )
        for file_fd, filename, snapshot, _expected_payload, _validator in expected_outputs:
            opened = os.fstat(file_fd)
            published = os.stat(filename, dir_fd=reviewed_fd, follow_symlinks=False)
            if (
                _finalize_file_snapshot(opened) != snapshot
                or not stat.S_ISREG(published.st_mode)
                or (published.st_dev, published.st_ino) != (opened.st_dev, opened.st_ino)
            ):
                raise CreativeSpecificationSkepticReviewCliError(
                    f"reviewed finalize output {filename} changed during stable inspection."
                )
        if set(os.listdir(reviewed_fd)) != expected_names:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize run changed during output inspection."
            )
    finally:
        close_error = creative_code_spec_pipeline._close_descriptors(bundle_fd, receipt_fd)
        if sys.exc_info()[1] is None and close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize output descriptors could not be closed safely."
            ) from close_error


def _assert_reviewed_ref(ref: str, expected_path: Path, label: str) -> None:
    path = _resolve_repo_artifact_ref(ref, label=f"{label} ref")
    if path.resolve(strict=True) != expected_path.resolve(strict=True):
        raise CreativeSpecificationSkepticReviewCliError(
            f"fingerprint_mismatch: {label} ref does not match reviewed run layout."
        )


def _assert_artifact_ref(
    ref: str,
    *,
    expected_payload: Any | None,
    expected_fingerprint: str,
    label: str,
) -> None:
    path = _resolve_repo_artifact_ref(ref, label=f"{label} ref")
    payload = _read_json_file(path)
    if expected_payload is not None and payload != expected_payload:
        raise CreativeSpecificationSkepticReviewCliError(
            f"fingerprint_mismatch: reviewed {label} copy diverges from source ref."
        )
    if fingerprint_payload(payload) != expected_fingerprint:
        raise CreativeSpecificationSkepticReviewCliError(
            f"fingerprint_mismatch: {label} fingerprint does not match attachment."
        )


def _finalize_from_attachment(attachment_path: Path) -> dict[str, Any]:
    attachment, reviewed_dir, expected_payloads = _validate_attachment_artifacts(attachment_path)
    bundle_path = reviewed_dir / BUNDLE_FILENAME
    reviewed_parent_fd = -1
    reviewed_fd = -1
    staging_fd = -1
    reviewed_identity: DirectoryIdentity | None = None
    staging_identity: DirectoryIdentity | None = None
    staging_name: str | None = None
    exchange_completed = False
    receipt: dict[str, Any]
    try:
        reviewed_parent_fd, reviewed_name, _candidate = (
            creative_code_spec_pipeline._open_pinned_parent(
                reviewed_dir,
                allowed_root=creative_code_spec_pipeline.ARTIFACT_ROOT,
                create=False,
                label="reviewed finalize run",
            )
        )
        reviewed_fd = os.open(
            reviewed_name,
            creative_code_spec_pipeline._directory_flags(),
            dir_fd=reviewed_parent_fd,
        )
        reviewed_info = os.fstat(reviewed_fd)
        reviewed_identity = (reviewed_info.st_dev, reviewed_info.st_ino)
        try:
            # The parent inode remains stable across the directory exchange. A
            # lock on the reviewed inode would move to the retained old run and
            # stop protecting the newly published canonical directory.
            fcntl.flock(reviewed_parent_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize is already in progress."
            ) from exc
        _assert_canonical_reviewed_run_identity(
            reviewed_dir,
            expected_identity=reviewed_identity,
        )
        pinned_inputs = _read_pinned_reviewed_inputs(
            reviewed_fd,
            expected_payloads=expected_payloads,
        )
        source_packet = _require_typed_json_object(
            pinned_inputs["source_packet.json"],
            label="pinned reviewed source packet",
        )
        variants = pinned_inputs["variants.json"]
        reviews = pinned_inputs["skeptic_reviews.json"]
        if not isinstance(variants, list) or not isinstance(reviews, list):
            raise CreativeSpecificationSkepticReviewCliError(
                "pinned reviewed variants and skeptic reviews must be JSON arrays."
            )
        try:
            bundle = build_creative_code_specification_bundle(
                source_packet=source_packet,
                variants=cast(Sequence[Mapping[str, Any]], variants),
                skeptic_reviews=cast(Sequence[Mapping[str, Any]], reviews),
            )
        except CreativeCodeSpecificationError as exc:
            raise CreativeSpecificationSkepticReviewCliError(
                "pinned reviewed inputs cannot build a valid CreativeCodeSpecificationBundle."
            ) from exc
        canonical_names = set(os.listdir(reviewed_fd))
        input_names = set(expected_payloads)
        if canonical_names == set(REVIEWED_RUN_FILENAMES):
            validated_bundle = validate_creative_code_specification_bundle(
                cast(Mapping[str, Any], _read_json_at(reviewed_fd, BUNDLE_FILENAME))
            )
            if fingerprint_payload(validated_bundle) != fingerprint_payload(bundle):
                raise CreativeSpecificationSkepticReviewCliError(
                    "fingerprint_mismatch: existing finalize bundle diverges from reviewed inputs."
                )
            existing_receipt = _require_typed_json_object(
                validate_finalize_receipt(
                    cast(Mapping[str, Any], _read_json_at(reviewed_fd, FINALIZE_RECEIPT_FILENAME))
                ),
                label="finalize receipt",
            )
            expected_receipt = _require_typed_json_object(
                build_finalize_receipt(
                    attachment=attachment,
                    attachment_ref=_artifact_ref(reviewed_dir / ATTACHMENT_FILENAME),
                    bundle=validated_bundle,
                    bundle_ref=_artifact_ref(bundle_path),
                ),
                label="finalize receipt",
            )
            if fingerprint_payload(existing_receipt) != fingerprint_payload(expected_receipt):
                raise CreativeSpecificationSkepticReviewCliError(
                    "fingerprint_mismatch: existing finalize receipt diverges from reviewed inputs."
                )
            receipt = existing_receipt
            _assert_pinned_finalize_outputs(
                reviewed_fd,
                expected_bundle=validated_bundle,
                expected_receipt=receipt,
            )
            _read_pinned_reviewed_inputs(
                reviewed_fd,
                expected_payloads=expected_payloads,
            )
            _assert_parent_entry_identity(
                reviewed_parent_fd,
                name=reviewed_dir.name,
                expected_identity=reviewed_identity,
                label="reviewed finalize replay run",
            )
            _assert_canonical_reviewed_run_identity(
                reviewed_dir,
                expected_identity=reviewed_identity,
            )
            close_error = creative_code_spec_pipeline._close_descriptors(
                reviewed_fd,
                reviewed_parent_fd,
            )
            reviewed_fd = -1
            reviewed_parent_fd = -1
            if close_error is not None:
                raise CreativeSpecificationSkepticReviewCliError(
                    "reviewed finalize replay descriptors could not be closed safely."
                ) from close_error
            return receipt
        elif canonical_names == input_names:
            validated_bundle = validate_creative_code_specification_bundle(bundle)
            receipt = _require_typed_json_object(
                build_finalize_receipt(
                    attachment=attachment,
                    attachment_ref=_artifact_ref(reviewed_dir / ATTACHMENT_FILENAME),
                    bundle=validated_bundle,
                    bundle_ref=_artifact_ref(bundle_path),
                ),
                label="finalize receipt",
            )
            receipt = _require_typed_json_object(
                validate_finalize_receipt(receipt),
                label="finalize receipt",
            )
        else:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize outputs are partial; retained for inspection."
            )

        finalized_payloads = {
            **pinned_inputs,
            BUNDLE_FILENAME: validated_bundle,
            FINALIZE_RECEIPT_FILENAME: receipt,
        }
        staging_fd, staging_identity, staging_name = _create_pinned_finalize_staging(
            reviewed_parent_fd
        )
        for filename, payload in finalized_payloads.items():
            _write_json_at(staging_fd, filename, payload)
        os.fsync(staging_fd)
        _assert_exact_reviewed_run_payloads(
            staging_fd,
            expected_payloads=finalized_payloads,
        )
        _assert_pinned_finalize_outputs(
            staging_fd,
            expected_bundle=validated_bundle,
            expected_receipt=receipt,
        )

        # Revalidate the locked source immediately before the single atomic
        # publication point. All seven finalized files already exist and are
        # durable in the sibling staging directory.
        _read_pinned_reviewed_inputs(
            reviewed_fd,
            expected_payloads=expected_payloads,
        )
        if set(os.listdir(reviewed_fd)) != canonical_names:
            raise CreativeSpecificationSkepticReviewCliError(
                "reviewed finalize canonical run changed before directory exchange."
            )
        _assert_parent_entry_identity(
            reviewed_parent_fd,
            name=reviewed_dir.name,
            expected_identity=reviewed_identity,
            label="reviewed finalize canonical run",
        )
        _assert_parent_entry_identity(
            reviewed_parent_fd,
            name=staging_name,
            expected_identity=staging_identity,
            label="reviewed finalize exchange directory",
        )
        _assert_canonical_reviewed_run_identity(
            reviewed_dir,
            expected_identity=reviewed_identity,
        )
        _kernel_rename_exchange(
            reviewed_parent_fd,
            staging_name,
            reviewed_dir.name,
        )
        exchange_completed = True
        os.fsync(reviewed_parent_fd)
        _assert_parent_entry_identity(
            reviewed_parent_fd,
            name=reviewed_dir.name,
            expected_identity=staging_identity,
            label="reviewed finalize published run",
        )
        _assert_parent_entry_identity(
            reviewed_parent_fd,
            name=staging_name,
            expected_identity=reviewed_identity,
            label="reviewed finalize retained pre-finalize run",
        )
        _assert_canonical_reviewed_run_identity(
            reviewed_dir,
            expected_identity=staging_identity,
        )
    except Exception as primary_error:
        retained_names = [reviewed_dir.name]
        if staging_name is not None:
            retained_names.append(staging_name)
        close_error = creative_code_spec_pipeline._close_descriptors(
            staging_fd,
            reviewed_fd,
            reviewed_parent_fd,
        )
        if close_error is not None:
            raise CreativeSpecificationSkepticReviewCliError(
                f"{primary_error}; cleanup_diagnostic={close_error}"
            ) from primary_error
        state = "published" if exchange_completed else "not_published"
        raise CreativeSpecificationSkepticReviewCliError(
            f"{primary_error}; exchange_state={state}; "
            f"failure_artifact_retained={','.join(retained_names)}"
        ) from primary_error
    close_error = creative_code_spec_pipeline._close_descriptors(
        staging_fd,
        reviewed_fd,
        reviewed_parent_fd,
    )
    if close_error is not None:
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize descriptors could not be closed safely."
        ) from close_error
    return receipt


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    attach_parser = subparsers.add_parser("attach")
    attach_parser.add_argument("--bridge", type=Path, required=True)
    attach_parser.add_argument("--reviews", type=Path, required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--attachment", type=Path, required=True)

    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--attachment", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "attach":
            attachment = _attach_from_bridge(args.bridge, args.reviews)
            if attachment["artifact_type"] != ATTACHMENT_ARTIFACT_TYPE:
                raise CreativeSpecificationSkepticReviewCliError("unexpected attachment artifact.")
            print(ATTACH_SUCCESS_OUTPUT)
            return 0
        if args.command == "validate":
            _validate_attachment_artifacts(args.attachment)
            print(VALIDATE_SUCCESS_OUTPUT)
            return 0
        if args.command == "finalize":
            receipt = _finalize_from_attachment(args.attachment)
            if receipt["artifact_type"] != FINALIZE_RECEIPT_ARTIFACT_TYPE:
                raise CreativeSpecificationSkepticReviewCliError("unexpected finalize receipt.")
            print(FINALIZE_SUCCESS_OUTPUT)
            return 0
    except (
        CreativeSpecificationSkepticReviewCliError,
        CreativeSpecificationSkepticReviewError,
        CreativeCodeSpecificationError,
        CreativeHypothesisSpecBridgeError,
        CreativePilotContractError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    sys.exit(main())

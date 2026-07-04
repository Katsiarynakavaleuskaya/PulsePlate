#!/usr/bin/env python3
"""Attach reviewed skeptic evidence and explicitly finalize PR-1 specifications."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping, Sequence, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_spec_pipeline
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    build_creative_code_specification_bundle,
    read_creative_code_specification_bundle,
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
from scripts.orchestration.creative_specification_skeptic_review_contract import (
    ATTACHMENT_ARTIFACT_TYPE,
    FINALIZE_RECEIPT_ARTIFACT_TYPE,
    REVIEWED_RUN_DIRNAME,
    CreativeSpecificationSkepticReviewError,
    build_finalize_receipt,
    build_skeptic_review_attachment,
    normalize_skeptic_reviews_for_pr1,
    validate_agent_skeptic_reviews_input,
    validate_finalize_receipt,
    validate_skeptic_review_attachment,
)

SPEC_BRIDGE_ROOT: Path = creative_code_spec_pipeline.ARTIFACT_ROOT / "spec_bridge"
ATTACHMENT_FILENAME = "skeptic_review_attachment.json"
BUNDLE_FILENAME = "creative_code_specification_bundle.json"
FINALIZE_RECEIPT_FILENAME = "finalize_receipt.json"
ATTACH_SUCCESS_OUTPUT = "PASS: creative specification skeptic reviews attached"
VALIDATE_SUCCESS_OUTPUT = "PASS: creative specification skeptic review attachment valid"
FINALIZE_SUCCESS_OUTPUT = "PASS: creative specification finalize receipt written"


class CreativeSpecificationSkepticReviewCliError(ValueError):
    """Raised when reviewed finalize CLI file I/O cannot safely complete."""


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
    _reject_symlink_components(SPEC_BRIDGE_ROOT, label="spec bridge root")
    SPEC_BRIDGE_ROOT.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(SPEC_BRIDGE_ROOT, label="spec bridge root")
    root: Path = SPEC_BRIDGE_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise CreativeSpecificationSkepticReviewCliError("spec bridge root must be a directory.")
    return root


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
    return path.resolve(strict=False).relative_to(REPO_ROOT.resolve()).as_posix()


def _read_json_file(path: Path) -> Any:
    _reject_symlink_components(path, label="JSON artifact")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeSpecificationSkepticReviewCliError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeSpecificationSkepticReviewCliError("Unable to read JSON artifact.") from exc


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


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeSpecificationSkepticReviewCliError(
                f"creative specification skeptic review JSON has duplicate key: {key}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def _write_json_atomic(path: Path, payload: Any) -> None:
    if path.suffix != ".json":
        raise CreativeSpecificationSkepticReviewCliError("output artifact must be JSON.")
    _reject_symlink_components(path.parent, label="output artifact parent")
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(path.parent, label="output artifact parent")
    if path.is_symlink():
        raise CreativeSpecificationSkepticReviewCliError("output artifact must not be a symlink.")
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


def _read_prepared_bridge(bridge_path: Path) -> dict[str, Any]:
    bridge_file = _resolve_repo_json_file(bridge_path, label="bridge input")
    bridge = validate_creative_hypothesis_specification_bridge(
        _read_json_object(bridge_file, label="bridge input")
    )
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


def _reject_unexpected_entries(path: Path, *, allowed: set[str], label: str) -> None:
    if path.exists() and not path.is_dir():
        raise CreativeSpecificationSkepticReviewCliError(f"{label} must be a directory.")
    if not path.exists():
        return
    symlink_children = sorted(child.name for child in path.iterdir() if child.is_symlink())
    if symlink_children:
        raise CreativeSpecificationSkepticReviewCliError(
            f"{label} contains symlink artifact(s): {', '.join(symlink_children)}."
        )
    unexpected = sorted(child.name for child in path.iterdir() if child.name not in allowed)
    if unexpected:
        raise CreativeSpecificationSkepticReviewCliError(
            f"{label} contains unexpected artifact(s): {', '.join(unexpected)}."
        )


def _reviewed_run_dir(bridge_dir: Path) -> Path:
    candidate = bridge_dir / REVIEWED_RUN_DIRNAME
    _reject_symlink_components(candidate, label="reviewed finalize run")
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_candidate, SPEC_BRIDGE_ROOT.resolve(strict=False)):
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run must stay under creative-code spec_bridge artifacts."
        )
    return Path(candidate)


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
    if reviewed_dir.exists() or reviewed_dir.is_symlink():
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize run already exists; remove the local sibling artifact to rerun."
        )
    reviewed_dir.mkdir(parents=True, exist_ok=False)
    try:
        reviewed_source_packet = reviewed_dir / "source_packet.json"
        reviewed_variants = reviewed_dir / "variants.json"
        reviewed_reviews = reviewed_dir / "skeptic_reviews.json"
        reviewed_context_pack = reviewed_dir / "context_pack.json"
        attachment_path = reviewed_dir / ATTACHMENT_FILENAME
        attachment = cast(
            dict[str, Any],
            build_skeptic_review_attachment(
                bridge_id=str(bridge["bridge_id"]),
                bridge_fingerprint=fingerprint_payload(bridge),
                bridge_ref=_artifact_ref(cast(Path, prepared["bridge_path"])),
                candidate_id=str(candidate["candidate_id"]),
                candidate_fingerprint=fingerprint_payload(candidate),
                candidate_ref=_artifact_ref(cast(Path, prepared["candidate_path"])),
                metrics_id=str(cast(Mapping[str, Any], prepared["metrics"])["metrics_id"]),
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
        )
        _write_json_atomic(reviewed_source_packet, source_packet)
        _write_json_atomic(reviewed_variants, variants)
        _write_json_atomic(reviewed_reviews, normalized_reviews)
        _write_json_atomic(reviewed_context_pack, cast(dict[str, Any], prepared["context_pack"]))
        _write_json_atomic(attachment_path, attachment)
    except Exception:
        shutil.rmtree(reviewed_dir, ignore_errors=True)
        raise
    return attachment


def _validate_attachment_artifacts(attachment_path: Path) -> tuple[dict[str, Any], Path]:
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
    source_packet = _read_json_object(reviewed_dir / "source_packet.json", label="source packet")
    variants = _read_json_array(reviewed_dir / "variants.json", label="variants")
    reviews = _read_json_array(reviewed_dir / "skeptic_reviews.json", label="skeptic reviews")
    context_pack = _read_json_object(reviewed_dir / "context_pack.json", label="context pack")
    source = cast(Mapping[str, Any], attachment["source"])
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
    if fingerprint_payload(source_packet) != source["source_packet_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: reviewed source packet does not match attachment."
        )
    if fingerprint_payload(variants) != source["variants_fingerprint"]:
        raise CreativeSpecificationSkepticReviewCliError(
            "fingerprint_mismatch: reviewed variants do not match attachment."
        )
    return attachment, reviewed_dir


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
    attachment, reviewed_dir = _validate_attachment_artifacts(attachment_path)
    bundle_path = reviewed_dir / BUNDLE_FILENAME
    receipt_path = reviewed_dir / FINALIZE_RECEIPT_FILENAME
    if bundle_path.exists() or receipt_path.exists():
        raise CreativeSpecificationSkepticReviewCliError(
            "reviewed finalize outputs already exist; remove local artifacts to rerun."
        )
    try:
        creative_code_spec_pipeline.finalize(reviewed_dir, bundle_path)
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        raise CreativeSpecificationSkepticReviewCliError(str(exc)) from exc
    bundle = validate_creative_code_specification_bundle(
        read_creative_code_specification_bundle(bundle_path)
    )
    receipt = cast(
        dict[str, Any],
        build_finalize_receipt(
            attachment=attachment,
            attachment_ref=_artifact_ref(reviewed_dir / ATTACHMENT_FILENAME),
            bundle=bundle,
            bundle_ref=_artifact_ref(bundle_path),
        ),
    )
    _write_json_atomic(receipt_path, receipt)
    validate_finalize_receipt(receipt)
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
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    sys.exit(main())

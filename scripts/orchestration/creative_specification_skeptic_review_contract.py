"""Contracts for reviewed creative-code specification finalization.

This module is a local control-plane contract. It validates operator-supplied,
sanitized skeptic-review evidence, normalizes it into the PR-1
``skeptic_reviews.json`` row shape, and describes the attachment/finalize
receipts. It has no filesystem writes, subprocesses, provider calls, GitHub
writes, product-runtime authority, semantic-cache authority, or graph-truth
authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
import re
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration.creative_code_specification import (
    REQUIRED_SKEPTIC_REVIEWERS,
    REVIEW_DECISIONS,
    REVIEW_KEYS,
    CreativeCodeSpecificationError,
    build_creative_code_specification_bundle,
    contains_unsafe_local_absolute_path,
    validate_source_candidate_packet,
)

SCHEMA_VERSION = "1.0"
REVIEW_INPUT_ARTIFACT_TYPE = "creative_specification_agent_skeptic_reviews"
ATTACHMENT_ARTIFACT_TYPE = "creative_specification_skeptic_review_attachment"
FINALIZE_RECEIPT_ARTIFACT_TYPE = "creative_specification_finalize_receipt"
POLICY_VERSION = "creative-specification-skeptic-review-finalize-v1"
REVIEWED_RUN_DIRNAME = "spec_finalize_reviewed"
ATTACHMENT_FILENAME = "skeptic_review_attachment.json"
BUNDLE_FILENAME = "creative_code_specification_bundle.json"
NEXT_ACTION_SELECTED = "human_review_for_patch_builder"
NEXT_ACTION_ALL_REJECTED = "human_review_for_discard_or_defer"
MAX_REVIEW_TEXT_LENGTH = 512
MAX_REVIEW_TOKEN_LIST_LENGTH = 10
MAX_TOTAL_REVIEW_TOKEN_COUNT = 150

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key)",
    re.IGNORECASE,
)
UNSAFE_TEXT_RE = re.compile(
    r"(candidate\.patch|diff --git|provider[_ -]?payload|raw[_ -]?(prompt|response|context)|"
    r"chain[_ -]?of[_ -]?thought|https?://|api\.openai\.com|call model|call network|"
    r"runtime service|product runtime|apply (a )?(repository )?patch|repository patch|"
    r"commit changes|git commit|git push|create (a )?(pull request|PR|branch)|"
    r"open (a )?(draft )?(pull request|PR)|write (to )?(the )?repository|"
    r"resolve review thread|mark ready for review|merge readiness|semantic cache|graph truth|"
    r"workflow dispatch|provider call|\bdiagnose\b|\btreat\b|clinical efficacy|"
    r"crisis support|emergency care)",
    re.IGNORECASE,
)

REVIEW_INPUT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "source_bridge_id",
        "source_bridge_fingerprint",
        "source_candidate_id",
        "source_candidate_fingerprint",
        "source_packet_fingerprint",
        "variants_fingerprint",
        "reviews",
        "authority",
        "sanitized",
    }
)
MAX_REVIEWS_PER_DECISION = 15
REVIEW_INPUT_ROW_KEYS = frozenset(
    {
        "variant_id",
        "reviewer_role",
        "decision",
        "blockers",
        "unsafe_authority_flags",
        "duplicate_reason",
        "required_revision",
    }
)
ATTACHMENT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "attachment_id",
        "idempotency_key",
        "policy_version",
        "source",
        "reviewed_run",
        "coverage",
        "authority",
        "sanitized",
    }
)
ATTACHMENT_SOURCE_KEYS = frozenset(
    {
        "bridge_id",
        "bridge_fingerprint",
        "bridge_ref",
        "candidate_id",
        "candidate_fingerprint",
        "candidate_ref",
        "metrics_id",
        "metrics_fingerprint",
        "metrics_ref",
        "spec_prepare_ref",
        "source_packet_ref",
        "source_packet_fingerprint",
        "variants_ref",
        "variants_fingerprint",
        "pending_reviews_ref",
        "pending_reviews_fingerprint",
        "context_pack_ref",
        "context_pack_fingerprint",
    }
)
REVIEWED_RUN_KEYS = frozenset(
    {
        "run_dir_ref",
        "source_packet_ref",
        "variants_ref",
        "skeptic_reviews_ref",
        "context_pack_ref",
        "normalized_reviews_fingerprint",
    }
)
ATTACHMENT_COVERAGE_KEYS = frozenset(
    {
        "variant_count",
        "required_reviewer_count",
        "review_count",
        "pass_review_count",
        "revise_review_count",
        "reject_review_count",
        "unsafe_authority_flag_count",
        "blocker_count",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "finalize_id",
        "idempotency_key",
        "policy_version",
        "source_attachment_id",
        "source_attachment_fingerprint",
        "source_attachment_ref",
        "reviewed_run_dir_ref",
        "bundle_ref",
        "bundle_id",
        "bundle_fingerprint",
        "bundle_idempotency_key",
        "selected_variant_id",
        "synthesis_status",
        "next_allowed_action",
        "counts",
        "authority",
        "sanitized",
    }
)
RECEIPT_COUNTS_KEYS = frozenset(
    {
        "variant_count",
        "review_count",
        "selected_variant_count",
        "rejected_variant_count",
        "unresolved_blocker_count",
        "rejection_record_count",
    }
)
TRUE_AUTHORITY_KEYS = frozenset(
    {
        "attach_skeptic_reviews",
        "emit_local_artifacts",
        "finalize_specification_bundle",
        "operator_supplied_sanitized_reviews",
    }
)
FALSE_AUTHORITY_KEYS = frozenset(
    {
        "call_product_runtime",
        "call_provider",
        "change_client_runtime",
        "change_openapi",
        "claim_merge_readiness",
        "create_branch",
        "dispatch_to_agents",
        "edit_fixed_mapping",
        "execute_agent_tasks",
        "execute_pr2_patch_builder",
        "execute_pr3_promotion",
        "generate_candidate_patch",
        "generate_patch",
        "merge",
        "modify_workflows",
        "open_draft_pr",
        "open_pr",
        "post_github_comment",
        "push",
        "read_secrets",
        "resolve_threads",
        "use_semantic_cache",
        "workflow_dispatch",
        "write_branch",
        "write_graph_truth",
        "write_repository",
        "write_shared_worktree",
    }
)
AUTHORITY_KEYS = TRUE_AUTHORITY_KEYS | FALSE_AUTHORITY_KEYS


class CreativeSpecificationSkepticReviewError(ValueError):
    """Raised when reviewed finalize evidence violates the local contract."""


def default_review_input_authority() -> dict[str, bool]:
    """Return the only authority allowed for operator-supplied review input."""

    return _authority(
        true_keys={"operator_supplied_sanitized_reviews"},
        false_true_keys={
            "attach_skeptic_reviews",
            "emit_local_artifacts",
            "finalize_specification_bundle",
        },
    )


def default_attachment_authority() -> dict[str, bool]:
    """Return the only authority allowed for skeptic-review attachment."""

    return _authority(
        true_keys={"attach_skeptic_reviews", "emit_local_artifacts"},
        false_true_keys={"operator_supplied_sanitized_reviews", "finalize_specification_bundle"},
    )


def default_finalize_receipt_authority() -> dict[str, bool]:
    """Return the only authority allowed for reviewed finalize receipts."""

    return _authority(
        true_keys={"emit_local_artifacts", "finalize_specification_bundle"},
        false_true_keys={"attach_skeptic_reviews", "operator_supplied_sanitized_reviews"},
    )


def validate_agent_skeptic_reviews_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate operator-supplied sanitized skeptic-review input."""

    label = "CreativeSpecificationAgentSkepticReviews"
    _require_exact_keys(payload, REVIEW_INPUT_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            REVIEW_INPUT_ARTIFACT_TYPE,
            label=label,
        ),
        "policy_version": _require_const(
            payload,
            "policy_version",
            POLICY_VERSION,
            label=label,
        ),
        "source_bridge_id": _require_id(payload, "source_bridge_id", label=label),
        "source_bridge_fingerprint": _require_fingerprint(
            payload,
            "source_bridge_fingerprint",
            label=label,
        ),
        "source_candidate_id": _require_id(payload, "source_candidate_id", label=label),
        "source_candidate_fingerprint": _require_fingerprint(
            payload,
            "source_candidate_fingerprint",
            label=label,
        ),
        "source_packet_fingerprint": _require_fingerprint(
            payload,
            "source_packet_fingerprint",
            label=label,
        ),
        "variants_fingerprint": _require_fingerprint(
            payload,
            "variants_fingerprint",
            label=label,
        ),
        "reviews": _normalize_input_reviews(payload["reviews"], label=f"{label}.reviews"),
        "authority": _normalize_authority(
            payload["authority"],
            expected=default_review_input_authority(),
            label=f"{label}.authority",
        ),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _reject_payload_safety(normalized, label=label)
    return normalized


def normalize_skeptic_reviews_for_pr1(
    *,
    review_input: Mapping[str, Any],
    source_packet: Mapping[str, Any],
    variants: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize operator review input into PR-1 skeptic review rows."""

    normalized_input = validate_agent_skeptic_reviews_input(review_input)
    normalized_packet = validate_source_candidate_packet(source_packet)
    source_packet_id = str(normalized_packet["candidate_id"])
    source_candidate_id = str(normalized_packet["source_creative_research"]["candidate_id"])
    variant_ids = {str(variant["variant_id"]) for variant in variants}
    review_keys: set[tuple[str, str]] = set()
    reviews: list[dict[str, Any]] = []
    for index, raw_review in enumerate(normalized_input["reviews"]):
        review = cast(dict[str, Any], dict(raw_review))
        variant_id = str(review["variant_id"])
        reviewer_role = str(review["reviewer_role"])
        if variant_id not in variant_ids:
            raise CreativeSpecificationSkepticReviewError(
                f"review[{index}].variant_id must reference a prepared variant."
            )
        key = (variant_id, reviewer_role)
        if key in review_keys:
            raise CreativeSpecificationSkepticReviewError(
                "reviews must not repeat a reviewer for a variant."
            )
        review_keys.add(key)
        normalized_review: dict[str, Any] = {
            "review_id": f"{variant_id}:{reviewer_role}",
            "source_packet_id": source_packet_id,
            "source_candidate_id": source_candidate_id,
            "variant_id": variant_id,
            "reviewer_role": reviewer_role,
            "decision": review["decision"],
            "blockers": list(review["blockers"]),
            "unsafe_authority_flags": list(review["unsafe_authority_flags"]),
            "duplicate_reason": review["duplicate_reason"],
            "required_revision": review["required_revision"],
            "review_fingerprint": "pending",
        }
        normalized_review["review_fingerprint"] = fingerprint_payload(
            _review_fingerprint_payload(normalized_review)
        )
        reviews.append(normalized_review)
    expected_keys = {
        (str(variant["variant_id"]), reviewer)
        for variant in variants
        for reviewer in REQUIRED_SKEPTIC_REVIEWERS
    }
    missing = sorted(expected_keys - review_keys)
    if missing:
        raise CreativeSpecificationSkepticReviewError(
            "reviews must cover every required reviewer for every variant."
        )
    extra = sorted(review_keys - expected_keys)
    if extra:
        raise CreativeSpecificationSkepticReviewError(
            "reviews include reviewer coverage outside the prepared PR-1 requirement."
        )
    try:
        build_creative_code_specification_bundle(
            source_packet=normalized_packet,
            variants=list(variants),
            skeptic_reviews=reviews,
        )
    except CreativeCodeSpecificationError as exc:
        raise CreativeSpecificationSkepticReviewError(str(exc)) from exc
    return reviews


def build_skeptic_review_attachment(
    *,
    bridge_id: str,
    bridge_fingerprint: str,
    bridge_ref: str,
    candidate_id: str,
    candidate_fingerprint: str,
    candidate_ref: str,
    metrics_id: str,
    metrics_fingerprint: str,
    metrics_ref: str,
    spec_prepare_ref: str,
    source_packet_ref: str,
    source_packet_fingerprint: str,
    variants_ref: str,
    variants_fingerprint: str,
    pending_reviews_ref: str,
    pending_reviews_fingerprint: str,
    context_pack_ref: str,
    context_pack_fingerprint: str,
    reviewed_run_dir_ref: str,
    reviewed_source_packet_ref: str,
    reviewed_variants_ref: str,
    reviewed_reviews_ref: str,
    reviewed_context_pack_ref: str,
    normalized_reviews: Sequence[Mapping[str, Any]],
    variant_count: int,
) -> dict[str, Any]:
    """Build a metadata-only skeptic-review attachment artifact."""

    counts = _review_counts(normalized_reviews=normalized_reviews, variant_count=variant_count)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ATTACHMENT_ARTIFACT_TYPE,
        "attachment_id": "pending",
        "idempotency_key": "pending",
        "policy_version": POLICY_VERSION,
        "source": {
            "bridge_id": bridge_id,
            "bridge_fingerprint": bridge_fingerprint,
            "bridge_ref": bridge_ref,
            "candidate_id": candidate_id,
            "candidate_fingerprint": candidate_fingerprint,
            "candidate_ref": candidate_ref,
            "metrics_id": metrics_id,
            "metrics_fingerprint": metrics_fingerprint,
            "metrics_ref": metrics_ref,
            "spec_prepare_ref": spec_prepare_ref,
            "source_packet_ref": source_packet_ref,
            "source_packet_fingerprint": source_packet_fingerprint,
            "variants_ref": variants_ref,
            "variants_fingerprint": variants_fingerprint,
            "pending_reviews_ref": pending_reviews_ref,
            "pending_reviews_fingerprint": pending_reviews_fingerprint,
            "context_pack_ref": context_pack_ref,
            "context_pack_fingerprint": context_pack_fingerprint,
        },
        "reviewed_run": {
            "run_dir_ref": reviewed_run_dir_ref,
            "source_packet_ref": reviewed_source_packet_ref,
            "variants_ref": reviewed_variants_ref,
            "skeptic_reviews_ref": reviewed_reviews_ref,
            "context_pack_ref": reviewed_context_pack_ref,
            "normalized_reviews_fingerprint": fingerprint_payload(list(normalized_reviews)),
        },
        "coverage": counts,
        "authority": default_attachment_authority(),
        "sanitized": True,
    }
    _set_identity(body, id_key="attachment_id", asset_type=ATTACHMENT_ARTIFACT_TYPE)
    return validate_skeptic_review_attachment(body)


def build_skeptic_review_coverage(
    *,
    normalized_reviews: Sequence[Mapping[str, Any]],
    variant_count: int,
) -> dict[str, int]:
    """Return bounded attachment coverage counts for normalized PR-1 reviews."""

    return _review_counts(normalized_reviews=normalized_reviews, variant_count=variant_count)


def validate_skeptic_review_attachment(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a skeptic-review attachment artifact."""

    label = "CreativeSpecificationSkepticReviewAttachment"
    _require_exact_keys(payload, ATTACHMENT_KEYS, label=label)
    source = _normalize_attachment_source(payload["source"], label=f"{label}.source")
    reviewed_run = _normalize_reviewed_run(payload["reviewed_run"], label=f"{label}.reviewed_run")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            ATTACHMENT_ARTIFACT_TYPE,
            label=label,
        ),
        "attachment_id": _require_id(payload, "attachment_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "policy_version": _require_const(
            payload,
            "policy_version",
            POLICY_VERSION,
            label=label,
        ),
        "source": source,
        "reviewed_run": reviewed_run,
        "coverage": _normalize_attachment_coverage(payload["coverage"], label=f"{label}.coverage"),
        "authority": _normalize_authority(
            payload["authority"],
            expected=default_attachment_authority(),
            label=f"{label}.authority",
        ),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_identity(normalized, id_key="attachment_id", asset_type=ATTACHMENT_ARTIFACT_TYPE)
    _reject_payload_safety(normalized, label=label)
    return normalized


def build_finalize_receipt(
    *,
    attachment: Mapping[str, Any],
    attachment_ref: str,
    bundle: Mapping[str, Any],
    bundle_ref: str,
) -> dict[str, Any]:
    """Build a metadata-only receipt for an explicit reviewed finalize step."""

    normalized_attachment = validate_skeptic_review_attachment(attachment)
    synthesis = cast(Mapping[str, Any], bundle["synthesis"])
    selected_variant_id = synthesis["selected_variant_id"]
    selected_count = 1 if selected_variant_id is not None else 0
    rejected_records = cast(Sequence[Mapping[str, Any]], bundle["rejection_index"]["records"])
    unresolved_blockers = cast(Sequence[Any], synthesis["unresolved_blockers"])
    variant_count = len(cast(Sequence[Any], bundle["variants"]))
    review_count = len(cast(Sequence[Any], bundle["skeptic_reviews"]))
    rejected_variant_count = len({str(record["variant_id"]) for record in rejected_records})
    synthesis_status = "selected" if selected_variant_id is not None else "all_rejected"
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": FINALIZE_RECEIPT_ARTIFACT_TYPE,
        "finalize_id": "pending",
        "idempotency_key": "pending",
        "policy_version": POLICY_VERSION,
        "source_attachment_id": normalized_attachment["attachment_id"],
        "source_attachment_fingerprint": fingerprint_payload(dict(normalized_attachment)),
        "source_attachment_ref": attachment_ref,
        "reviewed_run_dir_ref": normalized_attachment["reviewed_run"]["run_dir_ref"],
        "bundle_ref": bundle_ref,
        "bundle_id": bundle["bundle_id"],
        "bundle_fingerprint": fingerprint_payload(cast(dict[str, Any], dict(bundle))),
        "bundle_idempotency_key": bundle["idempotency_key"],
        "selected_variant_id": selected_variant_id,
        "synthesis_status": synthesis_status,
        "next_allowed_action": (
            NEXT_ACTION_SELECTED if selected_variant_id is not None else NEXT_ACTION_ALL_REJECTED
        ),
        "counts": {
            "variant_count": variant_count,
            "review_count": review_count,
            "selected_variant_count": selected_count,
            "rejected_variant_count": rejected_variant_count,
            "unresolved_blocker_count": len(unresolved_blockers),
            "rejection_record_count": len(rejected_records),
        },
        "authority": default_finalize_receipt_authority(),
        "sanitized": True,
    }
    _set_identity(body, id_key="finalize_id", asset_type=FINALIZE_RECEIPT_ARTIFACT_TYPE)
    return validate_finalize_receipt(body)


def validate_finalize_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a reviewed finalize receipt."""

    label = "CreativeSpecificationFinalizeReceipt"
    _require_exact_keys(payload, RECEIPT_KEYS, label=label)
    selected_variant_id = _require_optional_id(
        payload.get("selected_variant_id"), label=f"{label}.selected_variant_id"
    )
    synthesis_status = _require_token(payload, "synthesis_status", label=label)
    if synthesis_status not in {"selected", "all_rejected"}:
        raise CreativeSpecificationSkepticReviewError(f"{label}.synthesis_status is unsupported.")
    next_allowed_action = _require_token(payload, "next_allowed_action", label=label)
    expected_next = (
        NEXT_ACTION_SELECTED if selected_variant_id is not None else NEXT_ACTION_ALL_REJECTED
    )
    if next_allowed_action != expected_next:
        raise CreativeSpecificationSkepticReviewError(
            f"{label}.next_allowed_action does not match selected status."
        )
    if (selected_variant_id is None and synthesis_status != "all_rejected") or (
        selected_variant_id is not None and synthesis_status != "selected"
    ):
        raise CreativeSpecificationSkepticReviewError(
            f"{label}.synthesis_status does not match selected_variant_id."
        )
    counts = _normalize_receipt_counts(payload["counts"], label=f"{label}.counts")
    expected_selected_count = 1 if selected_variant_id is not None else 0
    if counts["selected_variant_count"] != expected_selected_count:
        raise CreativeSpecificationSkepticReviewError(
            f"{label}.counts.selected_variant_count does not match selected_variant_id."
        )
    if selected_variant_id is None:
        if counts["rejected_variant_count"] != counts["variant_count"]:
            raise CreativeSpecificationSkepticReviewError(
                f"{label}.counts.rejected_variant_count must match variant_count when all rejected."
            )
        if counts["rejection_record_count"] != counts["variant_count"]:
            raise CreativeSpecificationSkepticReviewError(
                f"{label}.counts.rejection_record_count must match variant_count when all rejected."
            )
    source_attachment_ref = _normalize_artifact_ref(
        payload.get("source_attachment_ref"),
        label=f"{label}.source_attachment_ref",
    )
    reviewed_run_dir_ref = _normalize_artifact_ref(
        payload.get("reviewed_run_dir_ref"),
        label=f"{label}.reviewed_run_dir_ref",
        must_be_reviewed_run=True,
    )
    bundle_ref = _normalize_artifact_ref(
        payload.get("bundle_ref"),
        label=f"{label}.bundle_ref",
    )
    _require_reviewed_run_child_ref(
        reviewed_run_dir_ref=reviewed_run_dir_ref,
        child_ref=source_attachment_ref,
        filename=ATTACHMENT_FILENAME,
        label=f"{label}.source_attachment_ref",
    )
    _require_reviewed_run_child_ref(
        reviewed_run_dir_ref=reviewed_run_dir_ref,
        child_ref=bundle_ref,
        filename=BUNDLE_FILENAME,
        label=f"{label}.bundle_ref",
    )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            FINALIZE_RECEIPT_ARTIFACT_TYPE,
            label=label,
        ),
        "finalize_id": _require_id(payload, "finalize_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "policy_version": _require_const(
            payload,
            "policy_version",
            POLICY_VERSION,
            label=label,
        ),
        "source_attachment_id": _require_id(payload, "source_attachment_id", label=label),
        "source_attachment_fingerprint": _require_fingerprint(
            payload,
            "source_attachment_fingerprint",
            label=label,
        ),
        "source_attachment_ref": source_attachment_ref,
        "reviewed_run_dir_ref": reviewed_run_dir_ref,
        "bundle_ref": bundle_ref,
        "bundle_id": _require_id(payload, "bundle_id", label=label),
        "bundle_fingerprint": _require_fingerprint(payload, "bundle_fingerprint", label=label),
        "bundle_idempotency_key": _require_id(payload, "bundle_idempotency_key", label=label),
        "selected_variant_id": selected_variant_id,
        "synthesis_status": synthesis_status,
        "next_allowed_action": next_allowed_action,
        "counts": counts,
        "authority": _normalize_authority(
            payload["authority"],
            expected=default_finalize_receipt_authority(),
            label=f"{label}.authority",
        ),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_identity(normalized, id_key="finalize_id", asset_type=FINALIZE_RECEIPT_ARTIFACT_TYPE)
    _reject_payload_safety(normalized, label=label)
    return normalized


def _authority(*, true_keys: set[str], false_true_keys: set[str]) -> dict[str, bool]:
    if (true_keys | false_true_keys) - TRUE_AUTHORITY_KEYS:
        raise AssertionError("authority configuration references unknown true key")
    values = {key: False for key in AUTHORITY_KEYS}
    for key in true_keys:
        values[key] = True
    for key in false_true_keys:
        values[key] = False
    return dict(sorted(values.items()))


def _review_counts(
    *,
    normalized_reviews: Sequence[Mapping[str, Any]],
    variant_count: int,
) -> dict[str, int]:
    decision_counts = {decision: 0 for decision in REVIEW_DECISIONS}
    blocker_count = 0
    unsafe_count = 0
    for review in normalized_reviews:
        decision_counts[str(review["decision"])] += 1
        blocker_count += len(cast(Sequence[Any], review["blockers"]))
        unsafe_count += len(cast(Sequence[Any], review["unsafe_authority_flags"]))
    return {
        "variant_count": _bounded_count(
            variant_count, "coverage.variant_count", minimum=1, maximum=5
        ),
        "required_reviewer_count": len(REQUIRED_SKEPTIC_REVIEWERS),
        "review_count": _bounded_count(
            len(normalized_reviews), "coverage.review_count", minimum=1, maximum=15
        ),
        "pass_review_count": decision_counts["pass"],
        "revise_review_count": decision_counts["revise"],
        "reject_review_count": decision_counts["reject"],
        "unsafe_authority_flag_count": unsafe_count,
        "blocker_count": blocker_count,
    }


def _set_identity(body: dict[str, Any], *, id_key: str, asset_type: str) -> None:
    fingerprint = fingerprint_payload(
        {key: body[key] for key in sorted(body) if key not in {id_key, "idempotency_key"}}
    )
    upstream_ids = _identity_upstream_ids(body)
    body[id_key] = build_asset_id(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    body["idempotency_key"] = build_idempotency_key(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )


def _validate_identity(body: Mapping[str, Any], *, id_key: str, asset_type: str) -> None:
    expected = dict(body)
    expected[id_key] = "pending"
    expected["idempotency_key"] = "pending"
    _set_identity(expected, id_key=id_key, asset_type=asset_type)
    if body[id_key] != expected[id_key] or body["idempotency_key"] != expected["idempotency_key"]:
        raise CreativeSpecificationSkepticReviewError(
            f"{asset_type} identity does not match artifact content."
        )


def _identity_upstream_ids(body: Mapping[str, Any]) -> tuple[str, ...]:
    if body.get("artifact_type") == ATTACHMENT_ARTIFACT_TYPE:
        source = cast(Mapping[str, Any], body["source"])
        reviewed = cast(Mapping[str, Any], body["reviewed_run"])
        return (
            str(source["bridge_id"]),
            str(source["candidate_id"]),
            str(reviewed["normalized_reviews_fingerprint"]),
        )
    if body.get("artifact_type") == FINALIZE_RECEIPT_ARTIFACT_TYPE:
        return (
            str(body["source_attachment_id"]),
            str(body["bundle_id"]),
            str(body["bundle_fingerprint"]),
        )
    return ()


def _review_fingerprint_payload(review: Mapping[str, Any]) -> dict[str, Any]:
    return {key: review[key] for key in sorted(REVIEW_KEYS - {"review_id", "review_fingerprint"})}


def _normalize_input_reviews(raw_reviews: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_reviews, list):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be an array.")
    if not raw_reviews:
        raise CreativeSpecificationSkepticReviewError(f"{label} must be non-empty.")
    if len(raw_reviews) > 15:
        raise CreativeSpecificationSkepticReviewError(f"{label} must contain at most 15 rows.")
    return [
        _normalize_input_review(raw_review, index=index, label=label)
        for index, raw_review in enumerate(raw_reviews)
    ]


def _normalize_input_review(raw_review: Any, *, index: int, label: str) -> dict[str, Any]:
    row_label = f"{label}[{index}]"
    if not isinstance(raw_review, dict):
        raise CreativeSpecificationSkepticReviewError(f"{row_label} must be a JSON object.")
    _require_exact_keys(raw_review, REVIEW_INPUT_ROW_KEYS, label=row_label)
    review = {
        "variant_id": _require_id(raw_review, "variant_id", label=row_label),
        "reviewer_role": _require_token(raw_review, "reviewer_role", label=row_label),
        "decision": _require_token(raw_review, "decision", label=row_label),
        "blockers": _normalize_token_list(
            raw_review,
            "blockers",
            label=row_label,
            allow_empty=True,
        ),
        "unsafe_authority_flags": _normalize_token_list(
            raw_review,
            "unsafe_authority_flags",
            label=row_label,
            allow_empty=True,
        ),
        "duplicate_reason": _require_text(raw_review, "duplicate_reason", label=row_label),
        "required_revision": _require_text(raw_review, "required_revision", label=row_label),
    }
    if review["reviewer_role"] not in REQUIRED_SKEPTIC_REVIEWERS:
        raise CreativeSpecificationSkepticReviewError(
            f"{row_label}.reviewer_role is not required for PR-1."
        )
    if review["decision"] not in REVIEW_DECISIONS:
        raise CreativeSpecificationSkepticReviewError(f"{row_label}.decision is unsupported.")
    if review["decision"] == "pass":
        if (
            review["blockers"]
            or review["unsafe_authority_flags"]
            or review["duplicate_reason"] != "none"
            or review["required_revision"] != "none"
        ):
            raise CreativeSpecificationSkepticReviewError(
                f"{row_label} pass reviews must be clean."
            )
    if review["decision"] == "reject" and not review["blockers"]:
        raise CreativeSpecificationSkepticReviewError(
            f"{row_label} reject reviews require blockers."
        )
    if review["decision"] == "revise" and review["required_revision"] == "none":
        raise CreativeSpecificationSkepticReviewError(
            f"{row_label} revise reviews require revision notes."
        )
    return review


def _normalize_attachment_source(raw_source: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_source, dict):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_source, ATTACHMENT_SOURCE_KEYS, label=label)
    return {
        "bridge_id": _require_id(raw_source, "bridge_id", label=label),
        "bridge_fingerprint": _require_fingerprint(raw_source, "bridge_fingerprint", label=label),
        "bridge_ref": _normalize_artifact_ref(
            raw_source.get("bridge_ref"), label=f"{label}.bridge_ref"
        ),
        "candidate_id": _require_id(raw_source, "candidate_id", label=label),
        "candidate_fingerprint": _require_fingerprint(
            raw_source, "candidate_fingerprint", label=label
        ),
        "candidate_ref": _normalize_artifact_ref(
            raw_source.get("candidate_ref"), label=f"{label}.candidate_ref"
        ),
        "metrics_id": _require_id(raw_source, "metrics_id", label=label),
        "metrics_fingerprint": _require_fingerprint(raw_source, "metrics_fingerprint", label=label),
        "metrics_ref": _normalize_artifact_ref(
            raw_source.get("metrics_ref"), label=f"{label}.metrics_ref"
        ),
        "spec_prepare_ref": _normalize_artifact_ref(
            raw_source.get("spec_prepare_ref"),
            label=f"{label}.spec_prepare_ref",
        ),
        "source_packet_ref": _normalize_artifact_ref(
            raw_source.get("source_packet_ref"),
            label=f"{label}.source_packet_ref",
        ),
        "source_packet_fingerprint": _require_fingerprint(
            raw_source, "source_packet_fingerprint", label=label
        ),
        "variants_ref": _normalize_artifact_ref(
            raw_source.get("variants_ref"), label=f"{label}.variants_ref"
        ),
        "variants_fingerprint": _require_fingerprint(
            raw_source, "variants_fingerprint", label=label
        ),
        "pending_reviews_ref": _normalize_artifact_ref(
            raw_source.get("pending_reviews_ref"),
            label=f"{label}.pending_reviews_ref",
        ),
        "pending_reviews_fingerprint": _require_fingerprint(
            raw_source, "pending_reviews_fingerprint", label=label
        ),
        "context_pack_ref": _normalize_artifact_ref(
            raw_source.get("context_pack_ref"),
            label=f"{label}.context_pack_ref",
        ),
        "context_pack_fingerprint": _require_fingerprint(
            raw_source, "context_pack_fingerprint", label=label
        ),
    }


def _normalize_reviewed_run(raw_run: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_run, dict):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_run, REVIEWED_RUN_KEYS, label=label)
    return {
        "run_dir_ref": _normalize_artifact_ref(
            raw_run.get("run_dir_ref"),
            label=f"{label}.run_dir_ref",
            must_be_reviewed_run=True,
        ),
        "source_packet_ref": _normalize_artifact_ref(
            raw_run.get("source_packet_ref"), label=f"{label}.source_packet_ref"
        ),
        "variants_ref": _normalize_artifact_ref(
            raw_run.get("variants_ref"), label=f"{label}.variants_ref"
        ),
        "skeptic_reviews_ref": _normalize_artifact_ref(
            raw_run.get("skeptic_reviews_ref"), label=f"{label}.skeptic_reviews_ref"
        ),
        "context_pack_ref": _normalize_artifact_ref(
            raw_run.get("context_pack_ref"), label=f"{label}.context_pack_ref"
        ),
        "normalized_reviews_fingerprint": _require_fingerprint(
            raw_run, "normalized_reviews_fingerprint", label=label
        ),
    }


def _normalize_attachment_coverage(raw_counts: Any, *, label: str) -> dict[str, int]:
    counts = _normalize_counts(
        raw_counts,
        expected_keys=ATTACHMENT_COVERAGE_KEYS,
        label=label,
        maxima={
            "variant_count": 5,
            "required_reviewer_count": len(REQUIRED_SKEPTIC_REVIEWERS),
            "review_count": MAX_REVIEWS_PER_DECISION,
            "pass_review_count": MAX_REVIEWS_PER_DECISION,
            "revise_review_count": MAX_REVIEWS_PER_DECISION,
            "reject_review_count": MAX_REVIEWS_PER_DECISION,
            "unsafe_authority_flag_count": MAX_TOTAL_REVIEW_TOKEN_COUNT,
            "blocker_count": MAX_TOTAL_REVIEW_TOKEN_COUNT,
        },
        minima={
            "variant_count": 1,
            "review_count": 1,
        },
    )
    if counts["required_reviewer_count"] != len(REQUIRED_SKEPTIC_REVIEWERS):
        raise CreativeSpecificationSkepticReviewError(
            f"{label}.required_reviewer_count must equal {len(REQUIRED_SKEPTIC_REVIEWERS)}."
        )
    return counts


def _normalize_receipt_counts(raw_counts: Any, *, label: str) -> dict[str, int]:
    return _normalize_counts(
        raw_counts,
        expected_keys=RECEIPT_COUNTS_KEYS,
        label=label,
        maxima={
            "variant_count": 5,
            "review_count": MAX_REVIEWS_PER_DECISION,
            "selected_variant_count": 1,
            "rejected_variant_count": 5,
            "unresolved_blocker_count": MAX_TOTAL_REVIEW_TOKEN_COUNT,
            "rejection_record_count": 5,
        },
        minima={
            "variant_count": 1,
            "review_count": 1,
        },
    )


def _normalize_counts(
    raw_counts: Any,
    *,
    expected_keys: frozenset[str],
    label: str,
    maxima: Mapping[str, int],
    minima: Mapping[str, int] | None = None,
) -> dict[str, int]:
    if not isinstance(raw_counts, dict):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_counts, expected_keys, label=label)
    minimum_by_key = minima or {}
    return {
        key: _bounded_count(
            raw_counts[key],
            f"{label}.{key}",
            minimum=minimum_by_key.get(key, 0),
            maximum=maxima[key],
        )
        for key in sorted(expected_keys)
    }


def _require_reviewed_run_child_ref(
    *,
    reviewed_run_dir_ref: str,
    child_ref: str,
    filename: str,
    label: str,
) -> None:
    child_path = PurePosixPath(child_ref)
    if child_path.parent != PurePosixPath(reviewed_run_dir_ref) or child_path.name != filename:
        raise CreativeSpecificationSkepticReviewError(
            f"{label} must point to canonical {filename} under reviewed_run_dir_ref."
        )


def _normalize_authority(
    raw_authority: Any,
    *,
    expected: Mapping[str, bool],
    label: str,
) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_authority, frozenset(expected), label=label)
    for key, expected_value in expected.items():
        if raw_authority[key] is not expected_value:
            raise CreativeSpecificationSkepticReviewError(
                f"{label}.{key} must be {expected_value!r}."
            )
    return dict(sorted((key, bool(raw_authority[key])) for key in expected))


def _normalize_artifact_ref(
    raw_ref: Any,
    *,
    label: str,
    must_be_reviewed_run: bool = False,
) -> str:
    if not isinstance(raw_ref, str):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be a string.")
    value = raw_ref.strip()
    if not value:
        raise CreativeSpecificationSkepticReviewError(f"{label} must be non-empty.")
    if "\\" in value:
        raise CreativeSpecificationSkepticReviewError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")) or SCHEME_RE.match(value):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be a repo artifact ref.")
    path = PurePosixPath(value)
    if "." in path.parts or ".." in path.parts:
        raise CreativeSpecificationSkepticReviewError(f"{label} must not contain traversal.")
    prefix = ("artifacts", "orchestration", "creative_code", "spec_bridge")
    if path.parts[:4] != prefix or len(path.parts) < 5:
        raise CreativeSpecificationSkepticReviewError(
            f"{label} must stay under creative-code spec_bridge artifacts."
        )
    for component in path.parts[4:]:
        if not ID_RE.fullmatch(component):
            raise CreativeSpecificationSkepticReviewError(
                f"{label} must use safe artifact path components."
            )
    if must_be_reviewed_run:
        if len(path.parts) != 6 or path.name != REVIEWED_RUN_DIRNAME:
            raise CreativeSpecificationSkepticReviewError(
                f"{label} must point to the canonical {REVIEWED_RUN_DIRNAME} sibling."
            )
    return path.as_posix()


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected_keys: frozenset[str],
    *,
    label: str,
) -> None:
    actual_keys = set(payload)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    if missing:
        raise CreativeSpecificationSkepticReviewError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeSpecificationSkepticReviewError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_bool(
    payload: Mapping[str, Any],
    key: str,
    *,
    expected: bool,
    label: str,
) -> bool:
    value = payload.get(key)
    if value is not expected:
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be {expected!r}.")
    return bool(expected)


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be a safe identifier.")
    return normalized


def _require_optional_id(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be null or string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be a safe identifier.")
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be a safe token.")
    if SECRET_RE.search(normalized):
        raise CreativeSpecificationSkepticReviewError(
            f"{label}.{key} must not contain secret-shaped values."
        )
    return normalized


def _require_text(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be non-empty.")
    if len(normalized) > MAX_REVIEW_TEXT_LENGTH:
        raise CreativeSpecificationSkepticReviewError(
            f"{label}.{key} must be at most {MAX_REVIEW_TEXT_LENGTH} characters."
        )
    _reject_unsafe_text(normalized, label=f"{label}.{key}")
    return normalized


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be a sha256 digest.")
    return value


def _bounded_count(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeSpecificationSkepticReviewError(f"{label} must be an integer.")
    if not minimum <= value <= maximum:
        raise CreativeSpecificationSkepticReviewError(
            f"{label} must be between {minimum} and {maximum}."
        )
    return value


def _normalize_token_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeSpecificationSkepticReviewError(f"{label}.{key} must be non-empty.")
    if len(value) > MAX_REVIEW_TOKEN_LIST_LENGTH:
        raise CreativeSpecificationSkepticReviewError(
            f"{label}.{key} must contain at most {MAX_REVIEW_TOKEN_LIST_LENGTH} items."
        )
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CreativeSpecificationSkepticReviewError(
                f"{label}.{key}[{index}] must be a string."
            )
        token = item.strip()
        if not token or not SAFE_TOKEN_RE.fullmatch(token):
            raise CreativeSpecificationSkepticReviewError(
                f"{label}.{key}[{index}] must be a safe token."
            )
        if SECRET_RE.search(token):
            raise CreativeSpecificationSkepticReviewError(
                f"{label}.{key}[{index}] must not contain secret-shaped values."
            )
        if token in seen:
            raise CreativeSpecificationSkepticReviewError(
                f"{label}.{key} must not contain duplicates."
            )
        seen.add(token)
        normalized.append(token)
    return normalized


def _reject_unsafe_text(value: str, *, label: str) -> None:
    if "\x00" in value or any(
        ord(character) < 32 and character not in "\n\r\t" for character in value
    ):
        raise CreativeSpecificationSkepticReviewError(
            f"{label} must not contain control characters."
        )
    if SECRET_RE.search(value) or UNSAFE_TEXT_RE.search(value):
        raise CreativeSpecificationSkepticReviewError(
            f"{label} contains unsafe creative-code authority."
        )
    if contains_unsafe_local_absolute_path(value):
        raise CreativeSpecificationSkepticReviewError(
            f"{label} must not contain local absolute paths."
        )


def _reject_payload_safety(value: Any, *, label: str) -> None:
    if isinstance(value, str):
        _reject_unsafe_text(value, label=label)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_payload_safety(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FALSE_AUTHORITY_KEYS:
                continue
            _reject_payload_safety(item, label=f"{label}.{key}")

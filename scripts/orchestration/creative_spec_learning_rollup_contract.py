"""Proposal-only learning rollups for finalized creative-code specifications.

This module is a local orchestration contract. It consumes already-finalized,
reviewed creative-code specification artifacts and emits proposal-only agent
learning records plus coordinator advisory hints. It has no provider calls,
runtime authority, semantic-cache authority, graph-truth authority, patch
generation authority, PR authority, or role-execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration.agent_learning_loop import (
    AUTHORITY_BOUNDARY as LEARNING_AUTHORITY_BOUNDARY,
    build_agent_learning_record,
    validate_agent_learning_record,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    CreativeHypothesisSpecBridgeError,
    validate_bridge_metrics,
)
from scripts.orchestration.creative_specification_skeptic_review_contract import (
    CreativeSpecificationSkepticReviewError,
    validate_finalize_receipt,
    validate_skeptic_review_attachment,
)

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-spec-learning-rollup-v1"
ROLLUP_ARTIFACT_TYPE = "creative_spec_learning_rollup"
HINTS_ARTIFACT_TYPE = "creative_spec_coordinator_advisory_hints"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |candidate\.patch|candidate_patch|"
    r"raw[_ -]?(body|prompt|response|context|patch|review|pr)|"
    r"review[_ -]?thread[_ -]?body|pull[_ -]?request[_ -]?body|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|oracle[_ -]?(stdout|stderr)|"
    r"file://|https?://|"
    r"/(?:Users|home|private/var|var/folders|tmp|etc|opt|usr|Volumes|mnt|root|"
    r"workspace|workspaces)(?:/|$)|~[/\\]|[A-Za-z]:[\\/]|\.venv/|\.git/|"
    r"worktrees([:/._-]|$)|github_pat_|gh[psoru]_|xox[abprs]-|"
    r"sk-[A-Za-z0-9_-]{12,}|GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE | re.MULTILINE,
)
UNSAFE_CLAIM_RE = re.compile(
    r"(semantic[-_ ]?cache[-_ ]?(used|updated|write|truth|serving)|"
    r"graph[-_ ]?truth[-_ ]?(used|updated|write|serving)|"
    r"product[-_ ]?runtime[-_ ]?truth|runtime[-_ ]?authority|"
    r"provider[-_ ]?call|github[-_ ]?write|slack[-_ ]?write|"
    r"patch[-_ ]?generation|auto[-_ ]?execute[-_ ]?agents|merge[-_ ]?readiness)",
    re.IGNORECASE,
)

AGENT_SLUGS = frozenset(
    {
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "cursor-specialist-agent",
    }
)
FOCUS_IDS = frozenset(
    {
        "authority_boundary_review",
        "failure_pattern_review",
        "oracle_and_test_reuse",
        "specification_pattern_reuse",
        "creative_learning_review",
    }
)

ROLLUP_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "rollup_id",
        "idempotency_key",
        "source",
        "outcomes",
        "agent_feedback",
        "learning_records",
        "learning_summary",
        "authority",
        "sanitized",
    }
)
ROLLUP_SOURCE_KEYS = frozenset(
    {
        "bridge_metrics_id",
        "bridge_metrics_fingerprint",
        "bridge_id",
        "skeptic_attachment_id",
        "skeptic_attachment_fingerprint",
        "finalize_id",
        "finalize_receipt_fingerprint",
        "bundle_id",
        "bundle_fingerprint",
        "source_packet_id",
        "source_packet_fingerprint",
    }
)
OUTCOME_KEYS = frozenset(
    {
        "variant_count",
        "selected_variant_id",
        "synthesis_status",
        "next_allowed_action",
        "pass_review_count",
        "revise_review_count",
        "reject_review_count",
        "unsafe_authority_flag_count",
        "blocker_count",
        "unresolved_blocker_count",
        "rejected_variant_count",
        "rejection_record_count",
        "generation_status",
        "oracle_status",
        "failure_class",
        "human_decision",
    }
)
AGENT_FEEDBACK_KEYS = frozenset({"reviewer_role", "pass_count", "revise_count", "reject_count"})
LEARNING_SUMMARY_KEYS = frozenset(
    {
        "learning_record_count",
        "successful_iteration_count",
        "failure_count",
        "reuse_lesson_ids",
        "avoid_lesson_ids",
    }
)
ROLLUP_AUTHORITY_TRUE_KEYS = frozenset(
    {
        "read_finalized_spec_outcomes",
        "emit_local_artifacts",
        "emit_proposal_learning_records",
        "emit_coordinator_advisory_hints",
    }
)
ROLLUP_AUTHORITY_FALSE_KEYS = frozenset(
    {
        "auto_execute_agents",
        "call_product_runtime",
        "call_provider",
        "change_client_runtime",
        "change_openapi",
        "change_primary_agent",
        "claim_merge_readiness",
        "create_branch",
        "edit_fixed_mapping",
        "execute_pr2_patch_builder",
        "force_agent_routing",
        "generate_candidate_patch",
        "generate_patch",
        "merge",
        "modify_agents",
        "modify_github_app",
        "modify_slack",
        "modify_task_bootstrap",
        "modify_workflows",
        "open_pr",
        "post_github_comment",
        "push",
        "read_secrets",
        "resolve_threads",
        "skip_required_roles",
        "use_semantic_cache",
        "workflow_dispatch",
        "write_branch",
        "write_graph_truth",
        "write_repository",
    }
)
ROLLUP_AUTHORITY_KEYS = ROLLUP_AUTHORITY_TRUE_KEYS | ROLLUP_AUTHORITY_FALSE_KEYS

HINTS_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "hints_id",
        "idempotency_key",
        "source_rollup_id",
        "source_rollup_fingerprint",
        "recommended_role_focus",
        "reuse_lesson_ids",
        "avoid_lesson_ids",
        "authority",
        "sanitized",
    }
)
FOCUS_KEYS = frozenset({"agent", "focus", "reason", "source_lesson_ids"})
HINTS_AUTHORITY_KEYS = frozenset(
    {
        "advisory_only",
        "call_product_runtime",
        "call_provider",
        "change_lifecycle_gates",
        "change_primary_agent",
        "claim_merge_readiness",
        "execute_agents",
        "force_agent_routing",
        "generate_patch",
        "modify_agents",
        "modify_prompts",
        "post_github_comment",
        "resolve_threads",
        "skip_required_roles",
        "use_semantic_cache",
        "write_graph_truth",
        "write_repository",
    }
)


class CreativeSpecLearningRollupError(ValueError):
    """Raised when creative spec learning inputs or outputs violate policy."""


def default_rollup_authority() -> dict[str, bool]:
    """Return the only authority granted to finalized-spec learning rollups."""

    values = {key: False for key in ROLLUP_AUTHORITY_KEYS}
    for key in ROLLUP_AUTHORITY_TRUE_KEYS:
        values[key] = True
    return dict(sorted(values.items()))


def default_hints_authority() -> dict[str, bool]:
    """Return the only authority granted to coordinator advisory hints."""

    values = {key: False for key in HINTS_AUTHORITY_KEYS}
    values["advisory_only"] = True
    return dict(sorted(values.items()))


def build_creative_spec_learning_rollup(
    *,
    bridge_metrics: Mapping[str, Any],
    skeptic_attachment: Mapping[str, Any],
    finalize_receipt: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a deterministic proposal-only learning rollup."""

    normalized = _validate_source_chain(
        bridge_metrics=bridge_metrics,
        skeptic_attachment=skeptic_attachment,
        finalize_receipt=finalize_receipt,
        bundle=bundle,
    )
    metrics = normalized["bridge_metrics"]
    attachment = normalized["skeptic_attachment"]
    receipt = normalized["finalize_receipt"]
    spec_bundle = normalized["bundle"]
    learning_records = _learning_records_for_bundle(
        finalize_receipt=receipt,
        bundle=spec_bundle,
    )
    outcomes = _outcomes(
        bridge_metrics=metrics,
        skeptic_attachment=attachment,
        finalize_receipt=receipt,
        bundle=spec_bundle,
    )
    rollup: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ROLLUP_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "rollup_id": "pending",
        "idempotency_key": "pending",
        "source": {
            "bridge_metrics_id": metrics["metrics_id"],
            "bridge_metrics_fingerprint": fingerprint_payload(metrics),
            "bridge_id": metrics["bridge_id"],
            "skeptic_attachment_id": attachment["attachment_id"],
            "skeptic_attachment_fingerprint": fingerprint_payload(attachment),
            "finalize_id": receipt["finalize_id"],
            "finalize_receipt_fingerprint": fingerprint_payload(receipt),
            "bundle_id": spec_bundle["bundle_id"],
            "bundle_fingerprint": fingerprint_payload(spec_bundle),
            "source_packet_id": spec_bundle["source_packet_id"],
            "source_packet_fingerprint": spec_bundle["source_packet_fingerprint"],
        },
        "outcomes": outcomes,
        "agent_feedback": _agent_feedback(spec_bundle),
        "learning_records": learning_records,
        "learning_summary": _learning_summary(learning_records),
        "authority": default_rollup_authority(),
        "sanitized": True,
    }
    _set_identity(
        rollup,
        id_key="rollup_id",
        asset_type=ROLLUP_ARTIFACT_TYPE,
        upstream_ids=(
            str(receipt["finalize_id"]),
            str(receipt["bundle_id"]),
            str(attachment["source"]["metrics_id"]),
        ),
    )
    return validate_creative_spec_learning_rollup(rollup)


def validate_creative_spec_learning_rollup(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a finalized-spec learning rollup."""

    label = "CreativeSpecLearningRollup"
    _require_exact_keys(payload, ROLLUP_KEYS, label=label)
    learning_records = _normalize_learning_records(
        payload["learning_records"], label=f"{label}.learning_records"
    )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            ROLLUP_ARTIFACT_TYPE,
            label=label,
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "rollup_id": _require_id(payload, "rollup_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source": _normalize_rollup_source(payload["source"], label=f"{label}.source"),
        "outcomes": _normalize_outcomes(payload["outcomes"], label=f"{label}.outcomes"),
        "agent_feedback": _normalize_agent_feedback(
            payload["agent_feedback"], label=f"{label}.agent_feedback"
        ),
        "learning_records": learning_records,
        "learning_summary": _normalize_learning_summary(
            payload["learning_summary"], label=f"{label}.learning_summary"
        ),
        "authority": _normalize_rollup_authority(payload["authority"], label=f"{label}.authority"),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if normalized["learning_summary"] != _learning_summary(learning_records):
        raise CreativeSpecLearningRollupError(
            f"{label}.learning_summary does not match learning_records."
        )
    _validate_rollup_outcome_consistency(normalized)
    _validate_identity(
        normalized,
        id_key="rollup_id",
        asset_type=ROLLUP_ARTIFACT_TYPE,
        upstream_ids=(
            normalized["source"]["finalize_id"],
            normalized["source"]["bundle_id"],
            normalized["source"]["bridge_metrics_id"],
        ),
    )
    _reject_payload_safety(normalized, label=label)
    return normalized


def build_coordinator_advisory_hints(rollup: Mapping[str, Any]) -> dict[str, Any]:
    """Build advisory-only coordinator hints from a validated rollup."""

    normalized_rollup = validate_creative_spec_learning_rollup(rollup)
    records = cast(list[dict[str, Any]], normalized_rollup["learning_records"])
    reuse_lesson_ids = [
        str(record["lesson_id"])
        for record in records
        if record["pattern_kind"] == "successful_iteration"
    ]
    avoid_lesson_ids = [
        str(record["lesson_id"]) for record in records if record["pattern_kind"] == "failure"
    ]
    hints: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": HINTS_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "hints_id": "pending",
        "idempotency_key": "pending",
        "source_rollup_id": normalized_rollup["rollup_id"],
        "source_rollup_fingerprint": fingerprint_payload(normalized_rollup),
        "recommended_role_focus": _recommended_role_focus(records),
        "reuse_lesson_ids": reuse_lesson_ids,
        "avoid_lesson_ids": avoid_lesson_ids,
        "authority": default_hints_authority(),
        "sanitized": True,
    }
    _set_identity(
        hints,
        id_key="hints_id",
        asset_type=HINTS_ARTIFACT_TYPE,
        upstream_ids=(str(normalized_rollup["rollup_id"]), fingerprint_payload(normalized_rollup)),
    )
    return validate_coordinator_advisory_hints(hints)


def validate_coordinator_advisory_hints(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate coordinator advisory hints before packet ingestion."""

    label = "CoordinatorAdvisoryHints"
    _require_exact_keys(payload, HINTS_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", HINTS_ARTIFACT_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "hints_id": _require_id(payload, "hints_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source_rollup_id": _require_id(payload, "source_rollup_id", label=label),
        "source_rollup_fingerprint": _require_fingerprint(
            payload,
            "source_rollup_fingerprint",
            label=label,
        ),
        "recommended_role_focus": _normalize_focus_list(
            payload["recommended_role_focus"],
            label=f"{label}.recommended_role_focus",
        ),
        "reuse_lesson_ids": _normalize_lesson_ids(
            payload["reuse_lesson_ids"], label=f"{label}.reuse_lesson_ids"
        ),
        "avoid_lesson_ids": _normalize_lesson_ids(
            payload["avoid_lesson_ids"], label=f"{label}.avoid_lesson_ids"
        ),
        "authority": _normalize_hints_authority(payload["authority"], label=f"{label}.authority"),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_hints_lesson_references(normalized, label=label)
    _validate_identity(
        normalized,
        id_key="hints_id",
        asset_type=HINTS_ARTIFACT_TYPE,
        upstream_ids=(
            normalized["source_rollup_id"],
            normalized["source_rollup_fingerprint"],
        ),
    )
    _reject_payload_safety(normalized, label=label)
    return normalized


def _validate_hints_lesson_references(hints: Mapping[str, Any], *, label: str) -> None:
    declared_reuse = set(cast(Sequence[str], hints["reuse_lesson_ids"]))
    declared_avoid = set(cast(Sequence[str], hints["avoid_lesson_ids"]))
    overlap = sorted(declared_reuse.intersection(declared_avoid))
    if overlap:
        raise CreativeSpecLearningRollupError(
            f"{label}.reuse_lesson_ids and avoid_lesson_ids must be disjoint."
        )
    declared = declared_reuse | declared_avoid
    for index, focus in enumerate(
        cast(Sequence[Mapping[str, Any]], hints["recommended_role_focus"])
    ):
        source_ids = set(cast(Sequence[str], focus["source_lesson_ids"]))
        undeclared = sorted(source_ids.difference(declared))
        if undeclared:
            joined = ", ".join(undeclared)
            raise CreativeSpecLearningRollupError(
                f"{label}.recommended_role_focus[{index}].source_lesson_ids "
                f"references undeclared lesson ids: {joined}."
            )


def _validate_source_chain(
    *,
    bridge_metrics: Mapping[str, Any],
    skeptic_attachment: Mapping[str, Any],
    finalize_receipt: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    try:
        metrics = validate_bridge_metrics(bridge_metrics)
        attachment = validate_skeptic_review_attachment(skeptic_attachment)
        receipt = validate_finalize_receipt(finalize_receipt)
        spec_bundle = validate_creative_code_specification_bundle(bundle)
    except (
        CreativeHypothesisSpecBridgeError,
        CreativeSpecificationSkepticReviewError,
        CreativeCodeSpecificationError,
    ) as exc:
        raise CreativeSpecLearningRollupError(str(exc)) from exc

    attachment_source = cast(Mapping[str, Any], attachment["source"])
    if attachment_source["metrics_id"] != metrics["metrics_id"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: attachment metrics_id does not match bridge metrics."
        )
    if attachment_source["metrics_fingerprint"] != fingerprint_payload(metrics):
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: attachment metrics_fingerprint does not match metrics."
        )
    if attachment_source["bridge_id"] != metrics["bridge_id"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: attachment bridge_id does not match metrics."
        )
    if attachment_source["candidate_id"] != metrics["candidate_id"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: attachment candidate_id does not match metrics."
        )
    if attachment_source["source_packet_fingerprint"] != spec_bundle["source_packet_fingerprint"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: attachment source_packet_fingerprint does not match bundle."
        )
    if attachment_source["variants_fingerprint"] != fingerprint_payload(spec_bundle["variants"]):
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: attachment variants_fingerprint does not match bundle."
        )
    if cast(Mapping[str, Any], attachment["reviewed_run"])[
        "normalized_reviews_fingerprint"
    ] != fingerprint_payload(spec_bundle["skeptic_reviews"]):
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: attachment normalized reviews do not match bundle reviews."
        )
    if receipt["source_attachment_id"] != attachment["attachment_id"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: receipt source_attachment_id does not match attachment."
        )
    if receipt["source_attachment_fingerprint"] != fingerprint_payload(attachment):
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: receipt source_attachment_fingerprint does not match attachment."
        )
    if receipt["bundle_id"] != spec_bundle["bundle_id"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: receipt bundle_id does not match bundle."
        )
    if receipt["bundle_fingerprint"] != fingerprint_payload(spec_bundle):
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: receipt bundle_fingerprint does not match bundle."
        )
    if receipt["bundle_idempotency_key"] != spec_bundle["idempotency_key"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: receipt bundle_idempotency_key does not match bundle."
        )
    if receipt["selected_variant_id"] != spec_bundle["synthesis"]["selected_variant_id"]:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: receipt selected_variant_id does not match bundle synthesis."
        )
    expected_status = (
        "selected"
        if spec_bundle["synthesis"]["selected_variant_id"] is not None
        else "all_rejected"
    )
    if receipt["synthesis_status"] != expected_status:
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: receipt synthesis_status does not match bundle synthesis."
        )
    if int(cast(Mapping[str, Any], metrics["counts"])["variant_count"]) != len(
        spec_bundle["variants"]
    ):
        raise CreativeSpecLearningRollupError(
            "fingerprint_mismatch: metrics variant_count does not match bundle."
        )
    return {
        "bridge_metrics": metrics,
        "skeptic_attachment": attachment,
        "finalize_receipt": receipt,
        "bundle": spec_bundle,
    }


def _learning_records_for_bundle(
    *,
    finalize_receipt: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> list[dict[str, Any]]:
    target_surface = [str(path) for path in cast(Sequence[Any], bundle["target_surface"])]
    source_prefix = f"creative_spec_finalize:{finalize_receipt['finalize_id']}"
    records: list[dict[str, Any]] = []
    selected_variant_id = cast(Mapping[str, Any], bundle["synthesis"])["selected_variant_id"]
    if selected_variant_id is not None:
        records.append(
            _learning_record(
                source=f"{source_prefix}:selected:{selected_variant_id}",
                pattern=(
                    "Selected creative specification variant passed required skeptic review "
                    "within proposal-only authority."
                ),
                severity="low",
                affected_surfaces=target_surface,
                root_cause=(
                    "Complete skeptic-review pass coverage produced a reusable "
                    "creative specification pattern."
                ),
                required_oracle="deterministic_content_oracle",
                pattern_kind="successful_iteration",
            )
        )

    for rejection in cast(Sequence[Mapping[str, Any]], bundle["rejection_index"]["records"]):
        reason_codes = sorted(
            str(reason) for reason in cast(Sequence[Any], rejection["reason_codes"])
        )
        reason_text = ", ".join(reason_codes)
        variant_id = str(rejection["variant_id"])
        unsafe = any(
            "unsafe" in reason or "authority" in reason or "policy" in reason
            for reason in reason_codes
        )
        rejected = any("review_reject" == reason for reason in reason_codes)
        records.append(
            _learning_record(
                source=f"{source_prefix}:rejected:{variant_id}",
                pattern=f"Creative specification variant was blocked by {reason_text}.",
                severity="high" if unsafe else "medium" if rejected else "low",
                affected_surfaces=target_surface,
                root_cause=f"Variant {variant_id} did not satisfy reviewed specification criteria.",
                required_oracle=(
                    "fail_closed_security_edge" if unsafe else "deterministic_content_oracle"
                ),
                pattern_kind="failure",
            )
        )
    return records


def _learning_record(
    *,
    source: str,
    pattern: str,
    severity: str,
    affected_surfaces: list[str],
    root_cause: str,
    required_oracle: str,
    pattern_kind: str,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        validate_agent_learning_record(
            build_agent_learning_record(
                source=source,
                pattern=pattern,
                severity=severity,
                affected_surfaces=affected_surfaces,
                root_cause=root_cause,
                required_oracle=required_oracle,
                promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
                pattern_kind=pattern_kind,
            )
        ),
    )


def _outcomes(
    *,
    bridge_metrics: Mapping[str, Any],
    skeptic_attachment: Mapping[str, Any],
    finalize_receipt: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    coverage = cast(Mapping[str, Any], skeptic_attachment["coverage"])
    counts = cast(Mapping[str, Any], finalize_receipt["counts"])
    synthesis = cast(Mapping[str, Any], bundle["synthesis"])
    return {
        "variant_count": counts["variant_count"],
        "selected_variant_id": finalize_receipt["selected_variant_id"],
        "synthesis_status": finalize_receipt["synthesis_status"],
        "next_allowed_action": finalize_receipt["next_allowed_action"],
        "pass_review_count": coverage["pass_review_count"],
        "revise_review_count": coverage["revise_review_count"],
        "reject_review_count": coverage["reject_review_count"],
        "unsafe_authority_flag_count": coverage["unsafe_authority_flag_count"],
        "blocker_count": coverage["blocker_count"],
        "unresolved_blocker_count": len(cast(Sequence[Any], synthesis["unresolved_blockers"])),
        "rejected_variant_count": counts["rejected_variant_count"],
        "rejection_record_count": counts["rejection_record_count"],
        "generation_status": bundle["generation_status"],
        "oracle_status": bundle["oracle_status"],
        "failure_class": bundle["failure_class"],
        "human_decision": bundle["human_decision"],
    }


def _agent_feedback(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    decisions = ("pass", "revise", "reject")
    rows: dict[str, dict[str, int | str]] = {}
    for review in cast(Sequence[Mapping[str, Any]], bundle["skeptic_reviews"]):
        role = str(review["reviewer_role"])
        row = rows.setdefault(
            role,
            {
                "reviewer_role": role,
                "pass_count": 0,
                "revise_count": 0,
                "reject_count": 0,
            },
        )
        decision = str(review["decision"])
        if decision in decisions:
            row[f"{decision}_count"] = int(row[f"{decision}_count"]) + 1
    return [cast(dict[str, Any], rows[key]) for key in sorted(rows)]


def _learning_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    reuse_lesson_ids = [
        str(record["lesson_id"])
        for record in records
        if str(record["pattern_kind"]) == "successful_iteration"
    ]
    avoid_lesson_ids = [
        str(record["lesson_id"]) for record in records if str(record["pattern_kind"]) == "failure"
    ]
    return {
        "learning_record_count": len(records),
        "successful_iteration_count": len(reuse_lesson_ids),
        "failure_count": len(avoid_lesson_ids),
        "reuse_lesson_ids": reuse_lesson_ids,
        "avoid_lesson_ids": avoid_lesson_ids,
    }


def _recommended_role_focus(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    failure_ids = [
        str(record["lesson_id"]) for record in records if str(record["pattern_kind"]) == "failure"
    ]
    success_ids = [
        str(record["lesson_id"])
        for record in records
        if str(record["pattern_kind"]) == "successful_iteration"
    ]
    authority_failure_ids = [
        str(record["lesson_id"])
        for record in records
        if record["pattern_kind"] == "failure"
        and (
            record["required_oracle"] == "fail_closed_security_edge"
            or "authority" in str(record["pattern"]).lower()
            or "unsafe" in str(record["pattern"]).lower()
        )
    ]
    focus: list[dict[str, Any]] = []
    if failure_ids:
        focus.append(
            {
                "agent": "agent-coordinator",
                "focus": "creative_learning_review",
                "reason": "Review avoid lessons before the next creative specification lane.",
                "source_lesson_ids": failure_ids,
            }
        )
    if authority_failure_ids:
        focus.append(
            {
                "agent": "security-auditor",
                "focus": "authority_boundary_review",
                "reason": "Inspect authority boundaries tied to failed creative specification lessons.",
                "source_lesson_ids": authority_failure_ids,
            }
        )
    elif failure_ids:
        focus.append(
            {
                "agent": "bug-hunter",
                "focus": "failure_pattern_review",
                "reason": "Inspect failed creative specification lesson patterns.",
                "source_lesson_ids": failure_ids,
            }
        )
    if success_ids:
        focus.append(
            {
                "agent": "qa-engineer-agent",
                "focus": "oracle_and_test_reuse",
                "reason": "Reuse successful skeptic-review and oracle coverage patterns.",
                "source_lesson_ids": success_ids,
            }
        )
        focus.append(
            {
                "agent": "architecture-specialist",
                "focus": "specification_pattern_reuse",
                "reason": "Inspect successful creative specification structure for repeatable use.",
                "source_lesson_ids": success_ids,
            }
        )
    return focus


def _normalize_rollup_source(raw_source: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_source, dict):
        raise CreativeSpecLearningRollupError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_source, ROLLUP_SOURCE_KEYS, label=label)
    return {
        "bridge_metrics_id": _require_id(raw_source, "bridge_metrics_id", label=label),
        "bridge_metrics_fingerprint": _require_fingerprint(
            raw_source, "bridge_metrics_fingerprint", label=label
        ),
        "bridge_id": _require_id(raw_source, "bridge_id", label=label),
        "skeptic_attachment_id": _require_id(raw_source, "skeptic_attachment_id", label=label),
        "skeptic_attachment_fingerprint": _require_fingerprint(
            raw_source, "skeptic_attachment_fingerprint", label=label
        ),
        "finalize_id": _require_id(raw_source, "finalize_id", label=label),
        "finalize_receipt_fingerprint": _require_fingerprint(
            raw_source, "finalize_receipt_fingerprint", label=label
        ),
        "bundle_id": _require_id(raw_source, "bundle_id", label=label),
        "bundle_fingerprint": _require_fingerprint(raw_source, "bundle_fingerprint", label=label),
        "source_packet_id": _require_id(raw_source, "source_packet_id", label=label),
        "source_packet_fingerprint": _require_fingerprint(
            raw_source, "source_packet_fingerprint", label=label
        ),
    }


def _normalize_outcomes(raw_outcomes: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_outcomes, dict):
        raise CreativeSpecLearningRollupError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_outcomes, OUTCOME_KEYS, label=label)
    selected_variant_id = _optional_id(
        raw_outcomes.get("selected_variant_id"),
        label=f"{label}.selected_variant_id",
    )
    synthesis_status = _require_token(raw_outcomes, "synthesis_status", label=label)
    if synthesis_status not in {"selected", "all_rejected"}:
        raise CreativeSpecLearningRollupError(f"{label}.synthesis_status is unsupported.")
    next_allowed_action = _require_token(raw_outcomes, "next_allowed_action", label=label)
    if selected_variant_id is None:
        if synthesis_status != "all_rejected":
            raise CreativeSpecLearningRollupError(
                f"{label}.synthesis_status must be all_rejected without a selected variant."
            )
    elif synthesis_status != "selected":
        raise CreativeSpecLearningRollupError(
            f"{label}.synthesis_status must be selected when selected_variant_id is set."
        )
    return {
        "variant_count": _bounded_int(
            raw_outcomes, "variant_count", label=label, minimum=1, maximum=5
        ),
        "selected_variant_id": selected_variant_id,
        "synthesis_status": synthesis_status,
        "next_allowed_action": next_allowed_action,
        "pass_review_count": _bounded_int(
            raw_outcomes, "pass_review_count", label=label, maximum=15
        ),
        "revise_review_count": _bounded_int(
            raw_outcomes, "revise_review_count", label=label, maximum=15
        ),
        "reject_review_count": _bounded_int(
            raw_outcomes, "reject_review_count", label=label, maximum=15
        ),
        "unsafe_authority_flag_count": _bounded_int(
            raw_outcomes, "unsafe_authority_flag_count", label=label, maximum=150
        ),
        "blocker_count": _bounded_int(raw_outcomes, "blocker_count", label=label, maximum=150),
        "unresolved_blocker_count": _bounded_int(
            raw_outcomes, "unresolved_blocker_count", label=label, maximum=150
        ),
        "rejected_variant_count": _bounded_int(
            raw_outcomes, "rejected_variant_count", label=label, maximum=5
        ),
        "rejection_record_count": _bounded_int(
            raw_outcomes, "rejection_record_count", label=label, maximum=5
        ),
        "generation_status": _require_token(raw_outcomes, "generation_status", label=label),
        "oracle_status": _require_token(raw_outcomes, "oracle_status", label=label),
        "failure_class": _optional_token(
            raw_outcomes.get("failure_class"), label=f"{label}.failure_class"
        ),
        "human_decision": _require_token(raw_outcomes, "human_decision", label=label),
    }


def _normalize_agent_feedback(raw_feedback: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_feedback, list):
        raise CreativeSpecLearningRollupError(f"{label} must be an array.")
    if not raw_feedback:
        raise CreativeSpecLearningRollupError(f"{label} must be non-empty.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_feedback):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise CreativeSpecLearningRollupError(f"{item_label} must be a JSON object.")
        _require_exact_keys(item, AGENT_FEEDBACK_KEYS, label=item_label)
        role = _require_token(item, "reviewer_role", label=item_label)
        if role in seen:
            raise CreativeSpecLearningRollupError(f"{label} must not repeat reviewer_role.")
        seen.add(role)
        rows.append(
            {
                "reviewer_role": role,
                "pass_count": _bounded_int(item, "pass_count", label=item_label, maximum=5),
                "revise_count": _bounded_int(item, "revise_count", label=item_label, maximum=5),
                "reject_count": _bounded_int(item, "reject_count", label=item_label, maximum=5),
            }
        )
    return rows


def _normalize_learning_records(raw_records: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_records, list):
        raise CreativeSpecLearningRollupError(f"{label} must be an array.")
    if not raw_records:
        raise CreativeSpecLearningRollupError(f"{label} must be non-empty.")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_records):
        if not isinstance(item, dict):
            raise CreativeSpecLearningRollupError(f"{label}[{index}] must be a JSON object.")
        try:
            record = validate_agent_learning_record(cast(dict[str, Any], dict(item)))
        except ValueError as exc:
            raise CreativeSpecLearningRollupError(str(exc)) from exc
        if record["lesson_id"] in seen:
            raise CreativeSpecLearningRollupError(f"{label} must not repeat lesson_id.")
        seen.add(str(record["lesson_id"]))
        metrics = cast(Mapping[str, Any], record["learning_metrics"])
        if metrics["authority_boundary"] != LEARNING_AUTHORITY_BOUNDARY:
            raise CreativeSpecLearningRollupError(
                f"{label}[{index}].learning_metrics.authority_boundary is invalid."
            )
        records.append(record)
    return records


def _normalize_learning_summary(raw_summary: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_summary, dict):
        raise CreativeSpecLearningRollupError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_summary, LEARNING_SUMMARY_KEYS, label=label)
    return {
        "learning_record_count": _bounded_int(
            raw_summary, "learning_record_count", label=label, minimum=1, maximum=6
        ),
        "successful_iteration_count": _bounded_int(
            raw_summary, "successful_iteration_count", label=label, maximum=1
        ),
        "failure_count": _bounded_int(raw_summary, "failure_count", label=label, maximum=5),
        "reuse_lesson_ids": _normalize_lesson_ids(
            raw_summary["reuse_lesson_ids"], label=f"{label}.reuse_lesson_ids"
        ),
        "avoid_lesson_ids": _normalize_lesson_ids(
            raw_summary["avoid_lesson_ids"], label=f"{label}.avoid_lesson_ids"
        ),
    }


def _normalize_focus_list(raw_focus: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_focus, list):
        raise CreativeSpecLearningRollupError(f"{label} must be an array.")
    if len(raw_focus) > 6:
        raise CreativeSpecLearningRollupError(f"{label} must contain at most 6 entries.")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(raw_focus):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise CreativeSpecLearningRollupError(f"{item_label} must be a JSON object.")
        _require_exact_keys(item, FOCUS_KEYS, label=item_label)
        agent = _require_token(item, "agent", label=item_label)
        if agent not in AGENT_SLUGS:
            raise CreativeSpecLearningRollupError(f"{item_label}.agent is unsupported.")
        focus = _require_token(item, "focus", label=item_label)
        if focus not in FOCUS_IDS:
            raise CreativeSpecLearningRollupError(f"{item_label}.focus is unsupported.")
        rows.append(
            {
                "agent": agent,
                "focus": focus,
                "reason": _require_safe_text(item, "reason", label=item_label, max_length=180),
                "source_lesson_ids": _normalize_lesson_ids(
                    item["source_lesson_ids"], label=f"{item_label}.source_lesson_ids"
                ),
            }
        )
    return rows


def _normalize_lesson_ids(raw_values: Any, *, label: str) -> list[str]:
    if not isinstance(raw_values, list):
        raise CreativeSpecLearningRollupError(f"{label} must be an array.")
    if len(raw_values) > 6:
        raise CreativeSpecLearningRollupError(f"{label} must contain at most 6 items.")
    values: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_values):
        if not isinstance(item, str) or not item.startswith("lesson-") or len(item) > 32:
            raise CreativeSpecLearningRollupError(f"{label}[{index}] must be a lesson id.")
        if item in seen:
            raise CreativeSpecLearningRollupError(f"{label} must not contain duplicates.")
        seen.add(item)
        values.append(item)
    return values


def _normalize_rollup_authority(raw_authority: Any, *, label: str) -> dict[str, bool]:
    expected = default_rollup_authority()
    return _normalize_authority(raw_authority, expected=expected, label=label)


def _normalize_hints_authority(raw_authority: Any, *, label: str) -> dict[str, bool]:
    expected = default_hints_authority()
    return _normalize_authority(raw_authority, expected=expected, label=label)


def _normalize_authority(
    raw_authority: Any,
    *,
    expected: Mapping[str, bool],
    label: str,
) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeSpecLearningRollupError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_authority, frozenset(expected), label=label)
    for key, expected_value in expected.items():
        if raw_authority[key] is not expected_value:
            raise CreativeSpecLearningRollupError(f"{label}.{key} has invalid authority.")
    return dict(sorted((key, bool(raw_authority[key])) for key in expected))


def _validate_rollup_outcome_consistency(rollup: Mapping[str, Any]) -> None:
    outcomes = cast(Mapping[str, Any], rollup["outcomes"])
    summary = cast(Mapping[str, Any], rollup["learning_summary"])
    if outcomes["synthesis_status"] == "all_rejected":
        if outcomes["selected_variant_id"] is not None:
            raise CreativeSpecLearningRollupError("all_rejected rollup must not select a variant.")
        if summary["successful_iteration_count"] != 0:
            raise CreativeSpecLearningRollupError(
                "all_rejected rollup must not emit successful_iteration records."
            )
    if outcomes["synthesis_status"] == "selected" and summary["successful_iteration_count"] != 1:
        raise CreativeSpecLearningRollupError(
            "selected rollup must emit exactly one successful_iteration record."
        )


def _set_identity(
    payload: dict[str, Any],
    *,
    id_key: str,
    asset_type: str,
    upstream_ids: Sequence[str],
) -> None:
    payload[id_key] = "pending"
    payload["idempotency_key"] = "pending"
    fingerprint = fingerprint_payload(_identity_payload(payload, id_key=id_key))
    payload[id_key] = build_asset_id(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=tuple(upstream_ids),
    )
    payload["idempotency_key"] = build_idempotency_key(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=tuple(upstream_ids),
    )


def _validate_identity(
    payload: Mapping[str, Any],
    *,
    id_key: str,
    asset_type: str,
    upstream_ids: Sequence[str],
) -> None:
    body = dict(payload)
    body[id_key] = "pending"
    body["idempotency_key"] = "pending"
    fingerprint = fingerprint_payload(_identity_payload(body, id_key=id_key))
    expected_id = build_asset_id(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=tuple(upstream_ids),
    )
    expected_key = build_idempotency_key(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=tuple(upstream_ids),
    )
    if payload[id_key] != expected_id or payload["idempotency_key"] != expected_key:
        raise CreativeSpecLearningRollupError(f"{id_key} or idempotency_key is invalid.")


def _identity_payload(payload: Mapping[str, Any], *, id_key: str) -> dict[str, Any]:
    return {key: payload[key] for key in sorted(set(payload) - {id_key, "idempotency_key"})}


def _require_exact_keys(payload: Mapping[str, Any], keys: frozenset[str], *, label: str) -> None:
    missing = sorted(keys.difference(payload))
    extra = sorted(set(payload).difference(keys))
    if missing:
        raise CreativeSpecLearningRollupError(f"{label} missing fields: {', '.join(missing)}.")
    if extra:
        raise CreativeSpecLearningRollupError(f"{label} unexpected fields: {', '.join(extra)}.")


def _require_const(
    payload: Mapping[str, Any],
    key: str,
    expected: Any,
    *,
    label: str,
) -> Any:
    if payload.get(key) != expected:
        raise CreativeSpecLearningRollupError(f"{label}.{key} must be {expected!r}.")
    return expected


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise CreativeSpecLearningRollupError(f"{label}.{key} must be a safe id.")
    return value


def _optional_id(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise CreativeSpecLearningRollupError(f"{label} must be null or a safe id.")
    return value


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeSpecLearningRollupError(f"{label}.{key} must be a sha256 digest.")
    return value


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SAFE_TOKEN_RE.fullmatch(value):
        raise CreativeSpecLearningRollupError(f"{label}.{key} must be a safe token.")
    return value


def _optional_token(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SAFE_TOKEN_RE.fullmatch(value):
        raise CreativeSpecLearningRollupError(f"{label} must be null or a safe token.")
    return value


def _require_safe_text(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    max_length: int,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise CreativeSpecLearningRollupError(f"{label}.{key} must be bounded safe text.")
    _reject_payload_safety(value, label=f"{label}.{key}")
    return value.strip()


def _require_bool(
    payload: Mapping[str, Any],
    key: str,
    *,
    expected: bool,
    label: str,
) -> bool:
    if payload.get(key) is not expected:
        raise CreativeSpecLearningRollupError(f"{label}.{key} must be {expected}.")
    return expected


def _bounded_int(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    minimum: int = 0,
    maximum: int,
) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeSpecLearningRollupError(f"{label}.{key} must be an integer.")
    if value < minimum or value > maximum:
        raise CreativeSpecLearningRollupError(
            f"{label}.{key} must be between {minimum} and {maximum}."
        )
    return value


def _reject_payload_safety(value: Any, *, label: str) -> None:
    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value) or UNSAFE_CLAIM_RE.search(value):
            raise CreativeSpecLearningRollupError(
                f"{label} contains unsafe creative learning text."
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_payload_safety(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_payload_safety(item, label=f"{label}.{key}")

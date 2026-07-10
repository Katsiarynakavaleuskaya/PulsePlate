"""Contracts for bridging approved creative hypotheses into PR-1 candidates.

The bridge is a local orchestration adapter. It consumes already-sanitized
creative-context artifacts, builds a validated CreativeCodeCandidatePacket, and
emits deterministic local metrics. It does not call providers, write branches,
generate patches, dispatch agents, finalize specifications, or claim readiness.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
import re
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration.creative_code_contract import (
    AUTHORITY_FALSE_KEYS as CANDIDATE_AUTHORITY_FALSE_KEYS,
    AUTHORITY_TRUE_KEYS as CANDIDATE_AUTHORITY_TRUE_KEYS,
    FUTURE_TELEMETRY_FIELDS,
    GATE_STATUS as CANDIDATE_GATE_STATUS,
    PACKET_TYPE as CANDIDATE_PACKET_TYPE,
    POLICY_VERSION as CANDIDATE_POLICY_VERSION,
    PROTECTED_TARGET_SURFACE_EXACT_PATHS,
    PROTECTED_TARGET_SURFACE_FILENAMES,
    PROTECTED_TARGET_SURFACE_PREFIXES,
    SCHEMA_VERSION,
    CreativeCodeContractError,
    validate_creative_code_candidate_packet,
)
from scripts.orchestration.experiment_contract import validate_mutable_candidate_surface
from scripts.orchestration.creative_pilot_workspace_contract import (
    BRIDGE_TYPE as PILOT_BRIDGE_TYPE,
    POLICY_VERSION as PILOT_POLICY_VERSION,
    SCHEMA_VERSION as PILOT_SCHEMA_VERSION,
    CreativePilotContractError,
    validate_approval_v2,
    validate_context_map_v2,
    validate_hypothesis_packet_v2,
    validate_synthesis,
    validate_workspace,
)
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    ExperimentRunnerCreativeContextContractError,
    reject_unsafe_creative_context_value,
    validate_creative_hypothesis_approval,
    validate_creative_hypothesis_coordinator_dispatch,
    validate_creative_hypothesis_packet,
    validate_creative_protocol_context_map,
)

BRIDGE_ARTIFACT_TYPE = "creative_hypothesis_specification_bridge"
METRICS_ARTIFACT_TYPE = "creative_hypothesis_spec_bridge_metrics"
POLICY_VERSION = "creative-hypothesis-spec-bridge-v1"
BRIDGE_SUCCESS_STATUS = "candidate_built"
PREPARED_STATUS = "prepared"
BLOCKED_STATUS = "blocked"
VALID_STATUSES = frozenset({BRIDGE_SUCCESS_STATUS, PREPARED_STATUS, BLOCKED_STATUS})
VARIANT_COUNTS = frozenset({3, 4, 5})
PREPARE_FILENAMES = (
    "source_packet.json",
    "variants.json",
    "skeptic_reviews.json",
    "context_pack.json",
)
NO_ALLOWED_MUTABLE_TARGET = "no_allowed_mutable_target"
BRIDGE_FAILURE_REASONS = frozenset(
    {
        "approval_not_pr1_specification",
        "approved_agents_not_dispatched",
        "approved_targets_not_hypothesis_subset",
        "candidate_target_oracle_overlap",
        "dispatch_packet_mismatch",
        "dispatch_row_missing",
        "fingerprint_mismatch",
        "hypothesis_not_found",
        "hypothesis_packet_not_generated",
        "invalid_candidate_packet",
        NO_ALLOWED_MUTABLE_TARGET,
        "spec_prepare_failed",
    }
)

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FORBIDDEN_VALUE_RE = re.compile(
    r"(semantic[-_ ]?cache|graph[-_ ]?truth|runtime[-_ ]?telemetry|"
    r"product[-_ ]?runtime[-_ ]?truth|raw[-_ ]?provider|raw[-_ ]?prompt|"
    r"raw[-_ ]?response|raw[-_ ]?patch)",
    re.IGNORECASE,
)

BRIDGE_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "bridge_id",
        "idempotency_key",
        "source",
        "selected_hypothesis",
        "candidate_packet",
        "spec_prepare",
        "authority",
        "sanitized",
    }
)
SOURCE_KEYS = frozenset(
    {
        "context_map_id",
        "context_map_fingerprint",
        "hypothesis_packet_id",
        "hypothesis_packet_fingerprint",
        "coordinator_dispatch_id",
        "coordinator_dispatch_fingerprint",
        "approval_id",
        "approval_fingerprint",
    }
)
SELECTED_HYPOTHESIS_KEYS = frozenset(
    {
        "hypothesis_id",
        "hypothesis_fingerprint",
        "approved_target_surfaces",
        "candidate_target_surface",
        "immutable_oracles",
        "approved_agents",
        "dispatch_agents",
        "variant_count",
    }
)
CANDIDATE_REF_KEYS = frozenset({"candidate_id", "candidate_fingerprint", "candidate_packet_ref"})
SPEC_PREPARE_KEYS = frozenset(
    {"run_dir_ref", "expected_files", "prepared", "finalized", "next_allowed_action"}
)
METRICS_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "metrics_id",
        "idempotency_key",
        "source",
        "bridge_id",
        "candidate_id",
        "selected_hypothesis_id",
        "status",
        "blocked_reason",
        "counts",
        "cost_metadata",
        "authority",
        "sanitized",
    }
)
METRICS_SOURCE_KEYS = SOURCE_KEYS | frozenset({"candidate_fingerprint"})
METRICS_COUNTS_KEYS = frozenset(
    {
        "hypothesis_count",
        "approved_target_count",
        "candidate_target_count",
        "immutable_oracle_count",
        "variant_count",
        "prepare_files_written",
        "pending_skeptic_review_count",
    }
)
COST_METADATA_KEYS = frozenset(
    {"provider_cost_available", "provider_call_count", "provider_cost_basis"}
)
BRIDGE_AUTHORITY_TRUE_KEYS = frozenset(
    {
        "read_sanitized_context",
        "emit_local_artifacts",
        "build_creative_code_candidate_packet",
        "run_specification_prepare",
    }
)
BRIDGE_AUTHORITY_FALSE_KEYS = frozenset(
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
        "finalize_specification_bundle",
        "generate_candidate_patch",
        "generate_patch",
        "mark_pr_ready",
        "merge",
        "modify_github_app",
        "modify_slack",
        "modify_workflows",
        "open_draft_pr",
        "open_pr",
        "post_github_comment",
        "push",
        "read_secrets",
        "release",
        "resolve_threads",
        "use_semantic_cache",
        "workflow_dispatch",
        "write_branch",
        "write_repository",
        "write_shared_worktree",
    }
)
BRIDGE_AUTHORITY_KEYS = BRIDGE_AUTHORITY_TRUE_KEYS | BRIDGE_AUTHORITY_FALSE_KEYS


class CreativeHypothesisSpecBridgeError(ValueError):
    """Raised when bridge inputs or outputs violate local handoff authority."""

    def __init__(self, message: str, *, blocked_reason: str | None = None) -> None:
        super().__init__(message)
        self.blocked_reason = blocked_reason


def build_creative_pilot_spec_bridge_bundle(
    *,
    context_map: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    workspace: Mapping[str, Any],
    synthesis: Mapping[str, Any],
    approval: Mapping[str, Any],
    variant_count: int,
) -> dict[str, dict[str, Any]]:
    """Build a v2 lineage receipt while retaining CandidatePacket v1 truth."""

    if variant_count not in VARIANT_COUNTS:
        raise CreativeHypothesisSpecBridgeError("variant_count must be one of 3, 4, or 5.")
    try:
        context = validate_context_map_v2(context_map)
        packet = validate_hypothesis_packet_v2(hypothesis_packet, context_map=context)
        pilot_workspace = validate_workspace(workspace)
        pilot_synthesis = validate_synthesis(synthesis)
        pilot_approval = validate_approval_v2(approval)
    except CreativePilotContractError as exc:
        raise CreativeHypothesisSpecBridgeError(
            f"invalid_production_adjacent_source: {exc}",
            blocked_reason="fingerprint_mismatch",
        ) from exc

    bindings = {
        "packet_id": packet["packet_id"],
        "workspace_id": pilot_workspace["workspace_id"],
        "workspace_intent_fingerprint": pilot_workspace["intent_fingerprint"],
        "workspace_reviewed_revision_fingerprint": pilot_synthesis[
            "workspace_revision_fingerprint"
        ],
        "workspace_synthesized_revision_fingerprint": pilot_workspace["revision_fingerprint"],
        "hypothesis_id": pilot_workspace["intent"]["hypothesis_id"],
        "hypothesis_fingerprint": pilot_workspace["intent"]["hypothesis_fingerprint"],
        "target_manifest_fingerprint": pilot_workspace["target_manifest"]["manifest_fingerprint"],
        "base_sha": pilot_workspace["target_manifest"]["base_sha"],
        "head_sha": pilot_workspace["target_manifest"]["head_sha"],
        "synthesis_id": pilot_synthesis["synthesis_id"],
        "synthesis_fingerprint": fingerprint_payload(cast(dict[str, Any], pilot_synthesis)),
        "approval_id": pilot_approval["approval_id"],
        "approval_fingerprint": fingerprint_payload(cast(dict[str, Any], pilot_approval)),
    }
    for key in (
        "packet_id",
        "hypothesis_id",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
        "base_sha",
        "head_sha",
    ):
        approval_key = "source_hypothesis_packet_id" if key == "packet_id" else key
        if pilot_approval[approval_key] != bindings[key]:
            raise CreativeHypothesisSpecBridgeError(
                f"production-adjacent approval {key} binding mismatch",
                blocked_reason="fingerprint_mismatch",
            )
    if pilot_approval["synthesis_id"] != bindings["synthesis_id"] or (
        pilot_approval["synthesis_fingerprint"] != bindings["synthesis_fingerprint"]
    ):
        raise CreativeHypothesisSpecBridgeError(
            "production-adjacent approval synthesis binding mismatch",
            blocked_reason="fingerprint_mismatch",
        )
    if pilot_workspace["state"]["phase"] != "synthesized":
        raise CreativeHypothesisSpecBridgeError(
            "production-adjacent workspace must be synthesized before handoff",
            blocked_reason="fingerprint_mismatch",
        )
    expected_synthesis_ref = {
        "synthesis_id": pilot_synthesis["synthesis_id"],
        "synthesis_fingerprint": bindings["synthesis_fingerprint"],
        "reviewed_revision_fingerprint": bindings["workspace_reviewed_revision_fingerprint"],
    }
    if pilot_workspace["synthesis_ref"] != expected_synthesis_ref:
        raise CreativeHypothesisSpecBridgeError(
            "production-adjacent workspace synthesis reference mismatch",
            blocked_reason="fingerprint_mismatch",
        )
    for key in (
        "workspace_reviewed_revision_fingerprint",
        "workspace_synthesized_revision_fingerprint",
    ):
        if pilot_approval[key] != bindings[key]:
            raise CreativeHypothesisSpecBridgeError(
                f"production-adjacent approval {key} binding mismatch",
                blocked_reason="fingerprint_mismatch",
            )
    if pilot_synthesis["decision"] != "approve":
        raise CreativeHypothesisSpecBridgeError(
            "production-adjacent synthesis must approve PR-1 handoff",
            blocked_reason="approval_not_pr1_specification",
        )

    hypothesis = next(
        (
            row
            for row in packet["hypotheses"]
            if row["hypothesis_id"] == pilot_workspace["intent"]["hypothesis_id"]
        ),
        None,
    )
    if hypothesis is None:
        raise CreativeHypothesisSpecBridgeError(
            "production-adjacent hypothesis is missing",
            blocked_reason="hypothesis_not_found",
        )
    target_paths = [row["path"] for row in pilot_workspace["target_manifest"]["files"]]
    candidate = _build_candidate_packet(
        packet=packet,
        hypothesis=hypothesis,
        target_surface=target_paths,
        immutable_oracles=pilot_workspace["target_manifest"]["immutable_oracles"],
        variant_count=variant_count,
        source_fingerprint_override=fingerprint_payload(bindings),
    )
    bridge_body: dict[str, Any] = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "artifact_type": PILOT_BRIDGE_TYPE,
        "policy_version": PILOT_POLICY_VERSION,
        "surface_policy": "production_adjacent_pilot",
        "lineage": bindings,
        "candidate_id": candidate["candidate_id"],
        "candidate_fingerprint": fingerprint_payload(candidate),
        "candidate_schema_version": candidate["schema_version"],
        "spec_prepare": {
            "expected_files": list(PREPARE_FILENAMES),
            "prepared": False,
            "finalized": False,
            "next_allowed_action": "prepare_specification",
        },
        "authority": default_bridge_authority(),
        "sanitized": True,
    }
    bridge_fingerprint = cast(str, fingerprint_payload(bridge_body))
    upstream_ids = (
        str(packet["packet_id"]),
        str(pilot_synthesis["synthesis_id"]),
        str(pilot_approval["approval_id"]),
        str(candidate["candidate_id"]),
    )
    bridge = {
        **bridge_body,
        "bridge_id": build_asset_id(
            asset_type=PILOT_BRIDGE_TYPE,
            rail="orchestration",
            version=PILOT_SCHEMA_VERSION,
            policy_version=PILOT_POLICY_VERSION,
            fingerprint=bridge_fingerprint,
            upstream_ids=upstream_ids,
        ),
        "idempotency_key": build_idempotency_key(
            asset_type=PILOT_BRIDGE_TYPE,
            rail="orchestration",
            version=PILOT_SCHEMA_VERSION,
            policy_version=PILOT_POLICY_VERSION,
            fingerprint=bridge_fingerprint,
            upstream_ids=upstream_ids,
        ),
    }
    return {"bridge": bridge, "candidate": candidate}


def validate_creative_pilot_spec_bridge(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a production-adjacent v2 bridge receipt and its stable identity."""

    expected = {
        "schema_version",
        "artifact_type",
        "policy_version",
        "surface_policy",
        "lineage",
        "candidate_id",
        "candidate_fingerprint",
        "candidate_schema_version",
        "spec_prepare",
        "authority",
        "sanitized",
        "bridge_id",
        "idempotency_key",
    }
    if set(payload) != expected:
        raise CreativeHypothesisSpecBridgeError("production-adjacent bridge keys mismatch")
    if (
        payload["schema_version"] != PILOT_SCHEMA_VERSION
        or payload["artifact_type"] != PILOT_BRIDGE_TYPE
        or payload["policy_version"] != PILOT_POLICY_VERSION
        or payload["surface_policy"] != "production_adjacent_pilot"
        or payload["candidate_schema_version"] != SCHEMA_VERSION
        or payload["authority"] != default_bridge_authority()
        or payload["sanitized"] is not True
    ):
        raise CreativeHypothesisSpecBridgeError("production-adjacent bridge policy mismatch")
    lineage = payload["lineage"]
    if not isinstance(lineage, Mapping):
        raise CreativeHypothesisSpecBridgeError("production-adjacent bridge lineage is invalid")
    expected_lineage = {
        "packet_id",
        "workspace_id",
        "workspace_intent_fingerprint",
        "workspace_reviewed_revision_fingerprint",
        "workspace_synthesized_revision_fingerprint",
        "hypothesis_id",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
        "base_sha",
        "head_sha",
        "synthesis_id",
        "synthesis_fingerprint",
        "approval_id",
        "approval_fingerprint",
    }
    if set(lineage) != expected_lineage:
        raise CreativeHypothesisSpecBridgeError("production-adjacent bridge lineage keys mismatch")
    spec_prepare = payload["spec_prepare"]
    if not isinstance(spec_prepare, Mapping) or set(spec_prepare) != {
        "expected_files",
        "prepared",
        "finalized",
        "next_allowed_action",
    }:
        raise CreativeHypothesisSpecBridgeError("production-adjacent spec_prepare is invalid")
    if (
        spec_prepare["expected_files"] != list(PREPARE_FILENAMES)
        or spec_prepare["prepared"] is not False
        or spec_prepare["finalized"] is not False
        or spec_prepare["next_allowed_action"] != "prepare_specification"
    ):
        raise CreativeHypothesisSpecBridgeError("production-adjacent spec_prepare policy mismatch")
    for key in (
        "workspace_intent_fingerprint",
        "workspace_reviewed_revision_fingerprint",
        "workspace_synthesized_revision_fingerprint",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
        "synthesis_fingerprint",
        "approval_fingerprint",
        "candidate_fingerprint",
    ):
        value = lineage[key] if key in lineage else payload[key]
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            raise CreativeHypothesisSpecBridgeError(f"production-adjacent {key} is invalid")
    body = dict(payload)
    observed_id = body.pop("bridge_id")
    observed_key = body.pop("idempotency_key")
    bridge_fingerprint = cast(str, fingerprint_payload(body))
    upstream_ids = (
        str(lineage["packet_id"]),
        str(lineage["synthesis_id"]),
        str(lineage["approval_id"]),
        str(payload["candidate_id"]),
    )
    expected_id = build_asset_id(
        asset_type=PILOT_BRIDGE_TYPE,
        rail="orchestration",
        version=PILOT_SCHEMA_VERSION,
        policy_version=PILOT_POLICY_VERSION,
        fingerprint=bridge_fingerprint,
        upstream_ids=upstream_ids,
    )
    expected_key = build_idempotency_key(
        asset_type=PILOT_BRIDGE_TYPE,
        rail="orchestration",
        version=PILOT_SCHEMA_VERSION,
        policy_version=PILOT_POLICY_VERSION,
        fingerprint=bridge_fingerprint,
        upstream_ids=upstream_ids,
    )
    if observed_id != expected_id or observed_key != expected_key:
        raise CreativeHypothesisSpecBridgeError("production-adjacent bridge identity mismatch")
    return dict(payload)


def default_bridge_authority() -> dict[str, bool]:
    """Return the only authority allowed for this local bridge."""

    authority = {key: False for key in sorted(BRIDGE_AUTHORITY_FALSE_KEYS)}
    authority.update({key: True for key in sorted(BRIDGE_AUTHORITY_TRUE_KEYS)})
    return dict(sorted(authority.items()))


def build_creative_hypothesis_spec_bridge_bundle(
    *,
    context_map: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    coordinator_dispatch: Mapping[str, Any],
    approval: Mapping[str, Any],
    variant_count: int,
) -> dict[str, dict[str, Any]]:
    """Build bridge, candidate, and metrics artifacts from approved local inputs."""

    if variant_count not in VARIANT_COUNTS:
        raise CreativeHypothesisSpecBridgeError("variant_count must be one of 3, 4, or 5.")
    sources = _validate_sources(
        context_map=context_map,
        hypothesis_packet=hypothesis_packet,
        coordinator_dispatch=coordinator_dispatch,
        approval=approval,
    )
    normalized_context = sources["context_map"]
    normalized_packet = sources["hypothesis_packet"]
    normalized_dispatch = sources["coordinator_dispatch"]
    normalized_approval = sources["approval"]
    if normalized_packet["creative_status"] != "hypotheses_generated":
        raise CreativeHypothesisSpecBridgeError(
            "hypothesis_packet_not_generated: bridge requires a generated hypothesis packet.",
            blocked_reason="hypothesis_packet_not_generated",
        )
    if (
        normalized_approval["decision"] != "approve_for_pr1_specification"
        or normalized_approval["next_step"] != "create_pr1_specification"
    ):
        raise CreativeHypothesisSpecBridgeError(
            "approval_not_pr1_specification: only approved PR-1 specification "
            "handoffs may build candidates.",
            blocked_reason="approval_not_pr1_specification",
        )

    hypothesis = _find_hypothesis(
        normalized_packet,
        str(normalized_approval["hypothesis_id"]),
    )
    _require_approval_binding(normalized_approval, normalized_packet, hypothesis)
    approved_targets = _require_approved_targets_subset(normalized_approval, hypothesis)
    dispatch_row = _find_dispatch_row(
        normalized_dispatch,
        str(normalized_approval["hypothesis_id"]),
    )
    dispatch_agents = _dispatch_agents(dispatch_row)
    approved_agents = [str(agent) for agent in normalized_approval["approved_agents"]]
    missing_agents = sorted(set(approved_agents) - set(dispatch_agents))
    if missing_agents:
        raise CreativeHypothesisSpecBridgeError(
            "approved_agents_not_dispatched: approved agents must be present in "
            "the coordinator dispatch row.",
            blocked_reason="approved_agents_not_dispatched",
        )

    candidate_targets, non_mutable_targets = _candidate_targets_from_approval(approved_targets)
    if not candidate_targets:
        raise CreativeHypothesisSpecBridgeError(
            f"{NO_ALLOWED_MUTABLE_TARGET}: approval did not contain a target accepted "
            "by the current creative-code mutable allowlist.",
            blocked_reason=NO_ALLOWED_MUTABLE_TARGET,
        )
    immutable_oracles = _immutable_oracles_from_hypothesis(
        hypothesis=hypothesis,
        non_mutable_approved_targets=non_mutable_targets,
    )
    _reject_target_oracle_overlap(candidate_targets, immutable_oracles)

    candidate = _build_candidate_packet(
        packet=normalized_packet,
        hypothesis=hypothesis,
        target_surface=candidate_targets,
        immutable_oracles=immutable_oracles,
        variant_count=variant_count,
    )
    bridge = _build_bridge_artifact(
        context_map=normalized_context,
        hypothesis_packet=normalized_packet,
        coordinator_dispatch=normalized_dispatch,
        approval=normalized_approval,
        hypothesis=hypothesis,
        approved_targets=approved_targets,
        candidate_targets=candidate_targets,
        immutable_oracles=immutable_oracles,
        approved_agents=approved_agents,
        dispatch_agents=dispatch_agents,
        variant_count=variant_count,
        candidate=candidate,
        prepared=False,
    )
    metrics = build_bridge_metrics(
        bridge=bridge,
        candidate=candidate,
        hypothesis_packet=normalized_packet,
        approval=normalized_approval,
        status=BRIDGE_SUCCESS_STATUS,
        prepare_files_written=0,
        pending_skeptic_review_count=0,
    )
    return {"bridge": bridge, "candidate": candidate, "metrics": metrics}


def mark_bridge_prepared(bridge: Mapping[str, Any]) -> dict[str, Any]:
    """Return a validated copy of a bridge artifact with prepare marked complete."""

    normalized = validate_creative_hypothesis_specification_bridge(bridge)
    prepared = dict(normalized)
    spec_prepare = dict(cast(Mapping[str, Any], prepared["spec_prepare"]))
    spec_prepare["prepared"] = True
    spec_prepare["finalized"] = False
    spec_prepare["next_allowed_action"] = "agent_skeptic_review"
    prepared["spec_prepare"] = spec_prepare
    _validate_bridge_identity(prepared)
    reject_bridge_payload_safety(prepared, label="CreativeHypothesisSpecificationBridge")
    return prepared


def build_bridge_metrics(
    *,
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    approval: Mapping[str, Any],
    status: str,
    prepare_files_written: int,
    pending_skeptic_review_count: int,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    """Build deterministic bridge observability sidecar."""

    normalized_bridge = validate_creative_hypothesis_specification_bridge(bridge)
    normalized_candidate = validate_creative_code_candidate_packet(dict(candidate))
    normalized_packet = validate_creative_hypothesis_packet(hypothesis_packet)
    normalized_approval = validate_creative_hypothesis_approval(approval)
    metrics = _metrics_body(
        bridge=normalized_bridge,
        candidate=normalized_candidate,
        hypothesis_packet=normalized_packet,
        approval=normalized_approval,
        status=status,
        prepare_files_written=prepare_files_written,
        pending_skeptic_review_count=pending_skeptic_review_count,
        blocked_reason=blocked_reason,
    )
    metrics_id, idempotency_key = _artifact_identity(
        metrics,
        artifact_type=METRICS_ARTIFACT_TYPE,
        upstream_ids=(
            str(normalized_bridge["bridge_id"]),
            str(normalized_candidate["candidate_id"]),
        ),
    )
    metrics["metrics_id"] = metrics_id
    metrics["idempotency_key"] = idempotency_key
    return validate_bridge_metrics(metrics)


def update_bridge_metrics_for_prepare(
    *,
    metrics: Mapping[str, Any],
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    status: str,
    prepare_files_written: int,
    pending_skeptic_review_count: int,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    """Update an existing metrics sidecar after a prepare attempt."""

    normalized_metrics = validate_bridge_metrics(metrics)
    normalized_bridge = validate_creative_hypothesis_specification_bridge(bridge)
    normalized_candidate = validate_creative_code_candidate_packet(dict(candidate))
    body = {
        key: value
        for key, value in normalized_metrics.items()
        if key not in {"metrics_id", "idempotency_key"}
    }
    body["source"] = {
        **cast(dict[str, Any], normalized_bridge["source"]),
        "candidate_fingerprint": fingerprint_payload(
            cast(dict[str, Any], dict(normalized_candidate))
        ),
    }
    body["bridge_id"] = normalized_bridge["bridge_id"]
    body["candidate_id"] = normalized_candidate["candidate_id"]
    body["status"] = status
    body["blocked_reason"] = blocked_reason
    selected = cast(Mapping[str, Any], normalized_bridge["selected_hypothesis"])
    body["selected_hypothesis_id"] = selected["hypothesis_id"]
    counts = dict(cast(Mapping[str, Any], body["counts"]))
    counts["approved_target_count"] = len(selected["approved_target_surfaces"])
    counts["candidate_target_count"] = len(normalized_candidate["target_surface"])
    counts["immutable_oracle_count"] = len(normalized_candidate["immutable_oracles"])
    counts["variant_count"] = normalized_candidate["variant_count"]
    counts["prepare_files_written"] = prepare_files_written
    counts["pending_skeptic_review_count"] = pending_skeptic_review_count
    body["counts"] = counts
    metrics_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=METRICS_ARTIFACT_TYPE,
        upstream_ids=(str(body["bridge_id"]), str(body["candidate_id"])),
    )
    body["metrics_id"] = metrics_id
    body["idempotency_key"] = idempotency_key
    return validate_bridge_metrics(body)


def validate_creative_hypothesis_specification_bridge(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a bridge artifact."""

    label = "CreativeHypothesisSpecificationBridge"
    _require_exact_keys(payload, BRIDGE_TOP_LEVEL_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            BRIDGE_ARTIFACT_TYPE,
            label=label,
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "bridge_id": _require_id(payload, "bridge_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source": _normalize_source_block(payload["source"], label=f"{label}.source"),
        "selected_hypothesis": _normalize_selected_hypothesis(
            payload["selected_hypothesis"],
            label=f"{label}.selected_hypothesis",
        ),
        "candidate_packet": _normalize_candidate_ref(
            payload["candidate_packet"],
            label=f"{label}.candidate_packet",
        ),
        "spec_prepare": _normalize_spec_prepare(
            payload["spec_prepare"],
            label=f"{label}.spec_prepare",
        ),
        "authority": _normalize_bridge_authority(payload["authority"], label=f"{label}.authority"),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_selected_hypothesis_invariants(normalized)
    _validate_bridge_artifact_refs(normalized)
    _validate_bridge_identity(normalized)
    reject_bridge_payload_safety(normalized, label=label)
    return normalized


def validate_bridge_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate bridge metrics sidecar."""

    label = "CreativeHypothesisSpecBridgeMetrics"
    _require_exact_keys(payload, METRICS_TOP_LEVEL_KEYS, label=label)
    status = _require_token(payload, "status", label=label)
    if status not in VALID_STATUSES:
        raise CreativeHypothesisSpecBridgeError(f"{label}.status is unsupported.")
    blocked_reason = _require_optional_token(
        payload["blocked_reason"], label=f"{label}.blocked_reason"
    )
    if status == BLOCKED_STATUS:
        if blocked_reason not in BRIDGE_FAILURE_REASONS:
            raise CreativeHypothesisSpecBridgeError(
                f"{label}.blocked_reason must identify a known blocked reason."
            )
    elif blocked_reason is not None:
        raise CreativeHypothesisSpecBridgeError(
            f"{label}.blocked_reason must be null unless status is blocked."
        )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            METRICS_ARTIFACT_TYPE,
            label=label,
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "metrics_id": _require_id(payload, "metrics_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source": _normalize_metrics_source(payload["source"], label=f"{label}.source"),
        "bridge_id": _require_id(payload, "bridge_id", label=label),
        "candidate_id": _require_id(payload, "candidate_id", label=label),
        "selected_hypothesis_id": _require_id(payload, "selected_hypothesis_id", label=label),
        "status": status,
        "blocked_reason": blocked_reason,
        "counts": _normalize_metrics_counts(payload["counts"], label=f"{label}.counts"),
        "cost_metadata": _normalize_cost_metadata(
            payload["cost_metadata"],
            label=f"{label}.cost_metadata",
        ),
        "authority": _normalize_bridge_authority(payload["authority"], label=f"{label}.authority"),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_metrics_identity(normalized)
    reject_bridge_payload_safety(normalized, label=label)
    return normalized


def reject_bridge_payload_safety(value: Any, *, label: str) -> None:
    """Reject unsafe bridge text while allowing explicit false authority keys."""

    reject_unsafe_creative_context_value(value, label=label)
    if isinstance(value, str):
        if FORBIDDEN_VALUE_RE.search(value):
            raise CreativeHypothesisSpecBridgeError(f"{label} contains unsafe bridge text.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_bridge_payload_safety(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            reject_bridge_payload_safety(item, label=f"{label}.{key}")


def _validate_sources(
    *,
    context_map: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    coordinator_dispatch: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    try:
        normalized_context = validate_creative_protocol_context_map(context_map)
        normalized_packet = validate_creative_hypothesis_packet(hypothesis_packet)
        normalized_dispatch = validate_creative_hypothesis_coordinator_dispatch(
            coordinator_dispatch
        )
        normalized_approval = validate_creative_hypothesis_approval(approval)
    except ExperimentRunnerCreativeContextContractError as exc:
        raise CreativeHypothesisSpecBridgeError(str(exc)) from exc
    context_fingerprint = fingerprint_payload(cast(dict[str, Any], normalized_context))
    if normalized_packet["context_map_id"] != normalized_context["context_id"]:
        raise CreativeHypothesisSpecBridgeError(
            "fingerprint_mismatch: hypothesis packet context_map_id does not match context map.",
            blocked_reason="fingerprint_mismatch",
        )
    if normalized_packet["context_map_fingerprint"] != context_fingerprint:
        raise CreativeHypothesisSpecBridgeError(
            "fingerprint_mismatch: hypothesis packet context_map_fingerprint does not "
            "match context map.",
            blocked_reason="fingerprint_mismatch",
        )
    packet_fingerprint = fingerprint_payload(cast(dict[str, Any], normalized_packet))
    if normalized_dispatch["source_hypothesis_packet_id"] != normalized_packet["packet_id"]:
        raise CreativeHypothesisSpecBridgeError(
            "dispatch_packet_mismatch: coordinator dispatch references a different packet.",
            blocked_reason="dispatch_packet_mismatch",
        )
    if normalized_dispatch["source_hypothesis_packet_fingerprint"] != packet_fingerprint:
        raise CreativeHypothesisSpecBridgeError(
            "fingerprint_mismatch: coordinator dispatch fingerprint does not match packet.",
            blocked_reason="fingerprint_mismatch",
        )
    return {
        "context_map": normalized_context,
        "hypothesis_packet": normalized_packet,
        "coordinator_dispatch": normalized_dispatch,
        "approval": normalized_approval,
    }


def _find_hypothesis(packet: Mapping[str, Any], hypothesis_id: str) -> dict[str, Any]:
    for row in packet["hypotheses"]:
        hypothesis = cast(dict[str, Any], row)
        if hypothesis["hypothesis_id"] == hypothesis_id:
            return hypothesis
    raise CreativeHypothesisSpecBridgeError(
        "hypothesis_not_found: approved hypothesis must exist in the hypothesis packet.",
        blocked_reason="hypothesis_not_found",
    )


def _find_dispatch_row(dispatch: Mapping[str, Any], hypothesis_id: str) -> dict[str, Any]:
    for row in dispatch["dispatch"]:
        dispatch_row = cast(dict[str, Any], row)
        if dispatch_row["hypothesis_id"] == hypothesis_id:
            return dispatch_row
    raise CreativeHypothesisSpecBridgeError(
        "dispatch_row_missing: coordinator dispatch must include the approved hypothesis.",
        blocked_reason="dispatch_row_missing",
    )


def _require_approved_targets_subset(
    approval: Mapping[str, Any],
    hypothesis: Mapping[str, Any],
) -> list[str]:
    approved_targets = [str(path) for path in approval["approved_target_surfaces"]]
    hypothesis_targets = {str(path) for path in hypothesis["target_surfaces"]}
    if not set(approved_targets).issubset(hypothesis_targets):
        raise CreativeHypothesisSpecBridgeError(
            "approved_targets_not_hypothesis_subset: approved targets must be a subset "
            "of the selected hypothesis targets.",
            blocked_reason="approved_targets_not_hypothesis_subset",
        )
    return sorted(approved_targets)


def _dispatch_agents(dispatch_row: Mapping[str, Any]) -> list[str]:
    agents = {
        str(dispatch_row["primary_agent"]),
        *(str(agent) for agent in dispatch_row["review_agents"]),
        *(str(agent) for agent in dispatch_row["cross_domain_agents"]),
    }
    return sorted(agents)


def _require_approval_binding(
    approval: Mapping[str, Any],
    packet: Mapping[str, Any],
    hypothesis: Mapping[str, Any],
) -> None:
    packet_fingerprint = fingerprint_payload(cast(dict[str, Any], dict(packet)))
    hypothesis_fingerprint = fingerprint_payload(cast(dict[str, Any], dict(hypothesis)))
    if (
        approval["source_hypothesis_packet_id"] != packet["packet_id"]
        or approval["source_hypothesis_packet_fingerprint"] != packet_fingerprint
        or approval["hypothesis_fingerprint"] != hypothesis_fingerprint
    ):
        raise CreativeHypothesisSpecBridgeError(
            "fingerprint_mismatch: approval must bind to the current hypothesis "
            "packet and selected hypothesis fingerprint.",
            blocked_reason="fingerprint_mismatch",
        )


def _candidate_targets_from_approval(
    approved_targets: Sequence[str],
) -> tuple[list[str], list[str]]:
    candidate_targets: list[str] = []
    non_mutable_targets: list[str] = []
    for target in approved_targets:
        try:
            normalized = validate_mutable_candidate_surface([target])
        except ValueError:
            non_mutable_targets.append(PurePosixPath(target).as_posix())
            continue
        if any(_is_protected_candidate_target(path) for path in normalized):
            non_mutable_targets.extend(normalized)
            continue
        candidate_targets.extend(normalized)
    return sorted(set(candidate_targets)), sorted(set(non_mutable_targets))


def _is_protected_candidate_target(path: str) -> bool:
    return (
        path in PROTECTED_TARGET_SURFACE_EXACT_PATHS
        or PurePosixPath(path).name in PROTECTED_TARGET_SURFACE_FILENAMES
        or any(path.startswith(prefix) for prefix in PROTECTED_TARGET_SURFACE_PREFIXES)
    )


def _immutable_oracles_from_hypothesis(
    *,
    hypothesis: Mapping[str, Any],
    non_mutable_approved_targets: Sequence[str],
) -> list[str]:
    oracles = {
        *(str(path) for path in hypothesis["tests_or_oracles"]),
        *(str(path) for path in non_mutable_approved_targets),
    }
    return sorted(oracles)


def _reject_target_oracle_overlap(targets: Sequence[str], oracles: Sequence[str]) -> None:
    for target in targets:
        for oracle in oracles:
            if _paths_overlap(target, oracle):
                raise CreativeHypothesisSpecBridgeError(
                    "candidate_target_oracle_overlap: target_surface must stay disjoint "
                    "from immutable_oracles.",
                    blocked_reason="candidate_target_oracle_overlap",
                )


def _paths_overlap(left: str, right: str) -> bool:
    left_prefix = left.rstrip("/") + "/"
    right_prefix = right.rstrip("/") + "/"
    return left == right or left.startswith(right_prefix) or right.startswith(left_prefix)


def _build_candidate_packet(
    *,
    packet: Mapping[str, Any],
    hypothesis: Mapping[str, Any],
    target_surface: Sequence[str],
    immutable_oracles: Sequence[str],
    variant_count: int,
    source_fingerprint_override: str | None = None,
) -> dict[str, Any]:
    candidate_body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "packet_type": CANDIDATE_PACKET_TYPE,
        "policy_version": CANDIDATE_POLICY_VERSION,
        "gate_status": CANDIDATE_GATE_STATUS,
        "authority_class": "code-specification",
        "source_creative_research": {
            "bundle_id": packet["packet_id"],
            "candidate_id": hypothesis["hypothesis_id"],
            "promotion_decision": "promote",
            "fingerprint": (
                source_fingerprint_override
                or fingerprint_payload(cast(dict[str, Any], dict(hypothesis)))
            ),
            "evidence_ref": (
                "docs/orchestration/contracts/" "EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md"
            ),
        },
        "variant_count": variant_count,
        "sandbox_required": True,
        "human_review_required": True,
        "fallback": (
            "Discard this specification candidate and keep the approved hypothesis "
            "as advisory planning input."
        ),
        "target_surface": sorted(set(target_surface)),
        "immutable_oracles": sorted(set(immutable_oracles)),
        "authority": _candidate_authority(),
        "scientific_claim_status": "hypothesis_only",
        "evidence_bundle": {
            "artifact_refs": [
                "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md",
                "docs/orchestration/contracts/CREATIVE_CODE_CANDIDATE_CONTRACT.md",
                (
                    "docs/orchestration/contracts/"
                    "EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md"
                ),
                (
                    "docs/orchestration/contracts/"
                    "creative_hypothesis_specification_bridge.v1.schema.json"
                ),
            ],
            "required_tests": sorted(
                {
                    "tests/test_creative_hypothesis_spec_bridge.py",
                    "tests/test_creative_code_contract.py",
                    "tests/test_creative_code_specification.py",
                    *(
                        str(path)
                        for path in hypothesis["tests_or_oracles"]
                        if str(path).startswith("tests/")
                    ),
                }
            ),
            "negative_controls": sorted(
                {
                    "non_pr1_approval_rejected",
                    "no_allowed_mutable_target_rejected",
                    "patch_generation_authority_rejected",
                    *(str(item) for item in hypothesis["negative_controls"]),
                }
            ),
        },
        "future_telemetry_contract": {
            "emit_no_earlier_than": "PR-1",
            "minimum_fields": list(FUTURE_TELEMETRY_FIELDS),
        },
    }
    candidate_id, idempotency_key = _artifact_identity(
        candidate_body,
        artifact_type=CANDIDATE_PACKET_TYPE,
        upstream_ids=(
            str(packet["packet_id"]),
            str(hypothesis["hypothesis_id"]),
        ),
        policy_version=CANDIDATE_POLICY_VERSION,
    )
    candidate = {
        **candidate_body,
        "candidate_id": candidate_id,
        "idempotency_key": idempotency_key,
    }
    try:
        return cast(dict[str, Any], validate_creative_code_candidate_packet(candidate))
    except CreativeCodeContractError as exc:
        raise CreativeHypothesisSpecBridgeError(
            f"invalid_candidate_packet: {exc}",
            blocked_reason="invalid_candidate_packet",
        ) from exc


def _candidate_authority() -> dict[str, bool]:
    authority = {key: False for key in CANDIDATE_AUTHORITY_FALSE_KEYS}
    authority.update({key: True for key in CANDIDATE_AUTHORITY_TRUE_KEYS})
    return dict(sorted(authority.items()))


def _build_bridge_artifact(
    *,
    context_map: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    coordinator_dispatch: Mapping[str, Any],
    approval: Mapping[str, Any],
    hypothesis: Mapping[str, Any],
    approved_targets: Sequence[str],
    candidate_targets: Sequence[str],
    immutable_oracles: Sequence[str],
    approved_agents: Sequence[str],
    dispatch_agents: Sequence[str],
    variant_count: int,
    candidate: Mapping[str, Any],
    prepared: bool,
) -> dict[str, Any]:
    candidate_fingerprint = fingerprint_payload(cast(dict[str, Any], dict(candidate)))
    source = {
        "context_map_id": context_map["context_id"],
        "context_map_fingerprint": fingerprint_payload(cast(dict[str, Any], dict(context_map))),
        "hypothesis_packet_id": hypothesis_packet["packet_id"],
        "hypothesis_packet_fingerprint": fingerprint_payload(
            cast(dict[str, Any], dict(hypothesis_packet))
        ),
        "coordinator_dispatch_id": coordinator_dispatch["dispatch_id"],
        "coordinator_dispatch_fingerprint": fingerprint_payload(
            cast(dict[str, Any], dict(coordinator_dispatch))
        ),
        "approval_id": approval["approval_id"],
        "approval_fingerprint": fingerprint_payload(cast(dict[str, Any], dict(approval))),
    }
    bridge_body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": BRIDGE_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "source": source,
        "selected_hypothesis": {
            "hypothesis_id": hypothesis["hypothesis_id"],
            "hypothesis_fingerprint": fingerprint_payload(cast(dict[str, Any], dict(hypothesis))),
            "approved_target_surfaces": sorted(set(approved_targets)),
            "candidate_target_surface": sorted(set(candidate_targets)),
            "immutable_oracles": sorted(set(immutable_oracles)),
            "approved_agents": sorted(set(approved_agents)),
            "dispatch_agents": sorted(set(dispatch_agents)),
            "variant_count": variant_count,
        },
        "candidate_packet": {
            "candidate_id": candidate["candidate_id"],
            "candidate_fingerprint": candidate_fingerprint,
            "candidate_packet_ref": "",
        },
        "spec_prepare": {
            "run_dir_ref": "",
            "expected_files": list(PREPARE_FILENAMES),
            "prepared": prepared,
            "finalized": False,
            "next_allowed_action": (
                "agent_skeptic_review" if prepared else "prepare_specification"
            ),
        },
        "authority": default_bridge_authority(),
        "sanitized": True,
    }
    bridge_id, idempotency_key = _artifact_identity(
        _bridge_identity_payload(bridge_body),
        artifact_type=BRIDGE_ARTIFACT_TYPE,
        upstream_ids=(
            str(hypothesis_packet["packet_id"]),
            str(approval["approval_id"]),
            str(candidate["candidate_id"]),
        ),
    )
    artifact_root_ref = f"artifacts/orchestration/creative_code/spec_bridge/{bridge_id}"
    bridge = {
        **bridge_body,
        "bridge_id": bridge_id,
        "idempotency_key": idempotency_key,
    }
    bridge["candidate_packet"] = {
        **bridge["candidate_packet"],
        "candidate_packet_ref": f"{artifact_root_ref}/creative_code_candidate_packet.json",
    }
    bridge["spec_prepare"] = {
        **bridge["spec_prepare"],
        "run_dir_ref": f"{artifact_root_ref}/spec_prepare",
    }
    return validate_creative_hypothesis_specification_bridge(bridge)


def _metrics_body(
    *,
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    approval: Mapping[str, Any],
    status: str,
    prepare_files_written: int,
    pending_skeptic_review_count: int,
    blocked_reason: str | None,
) -> dict[str, Any]:
    source = {
        **cast(dict[str, Any], bridge["source"]),
        "candidate_fingerprint": fingerprint_payload(cast(dict[str, Any], dict(candidate))),
    }
    selected = cast(Mapping[str, Any], bridge["selected_hypothesis"])
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": METRICS_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "source": source,
        "bridge_id": bridge["bridge_id"],
        "candidate_id": candidate["candidate_id"],
        "selected_hypothesis_id": selected["hypothesis_id"],
        "status": status,
        "blocked_reason": blocked_reason,
        "counts": {
            "hypothesis_count": hypothesis_packet["hypothesis_count"],
            "approved_target_count": len(approval["approved_target_surfaces"]),
            "candidate_target_count": len(candidate["target_surface"]),
            "immutable_oracle_count": len(candidate["immutable_oracles"]),
            "variant_count": candidate["variant_count"],
            "prepare_files_written": prepare_files_written,
            "pending_skeptic_review_count": pending_skeptic_review_count,
        },
        "cost_metadata": {
            "provider_cost_available": False,
            "provider_call_count": 0,
            "provider_cost_basis": "not_available_local_no_provider_calls",
        },
        "authority": default_bridge_authority(),
        "sanitized": True,
    }


def _bridge_identity_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    candidate_packet = cast(Mapping[str, Any], payload["candidate_packet"])
    spec_prepare = cast(Mapping[str, Any], payload["spec_prepare"])
    return {
        "schema_version": payload["schema_version"],
        "artifact_type": payload["artifact_type"],
        "policy_version": payload["policy_version"],
        "source": payload["source"],
        "selected_hypothesis": payload["selected_hypothesis"],
        "candidate_packet": {
            "candidate_id": candidate_packet["candidate_id"],
            "candidate_fingerprint": candidate_packet["candidate_fingerprint"],
        },
        "spec_prepare": {
            "expected_files": spec_prepare["expected_files"],
        },
        "authority": payload["authority"],
        "sanitized": payload["sanitized"],
    }


def _expected_bridge_artifact_refs(bridge_id: str) -> tuple[str, str]:
    artifact_root_ref = f"artifacts/orchestration/creative_code/spec_bridge/{bridge_id}"
    return (
        f"{artifact_root_ref}/creative_code_candidate_packet.json",
        f"{artifact_root_ref}/spec_prepare",
    )


def _validate_bridge_artifact_refs(payload: Mapping[str, Any]) -> None:
    bridge_id = str(payload["bridge_id"])
    expected_candidate_ref, expected_run_dir_ref = _expected_bridge_artifact_refs(bridge_id)
    candidate_ref = cast(Mapping[str, Any], payload["candidate_packet"])["candidate_packet_ref"]
    if candidate_ref != expected_candidate_ref:
        raise CreativeHypothesisSpecBridgeError(
            "CreativeHypothesisSpecificationBridge.candidate_packet.candidate_packet_ref "
            "must match the bridge id."
        )
    run_dir_ref = cast(Mapping[str, Any], payload["spec_prepare"])["run_dir_ref"]
    if run_dir_ref != expected_run_dir_ref:
        raise CreativeHypothesisSpecBridgeError(
            "CreativeHypothesisSpecificationBridge.spec_prepare.run_dir_ref "
            "must match the bridge id."
        )


def _validate_selected_hypothesis_invariants(payload: Mapping[str, Any]) -> None:
    selected = cast(Mapping[str, Any], payload["selected_hypothesis"])
    approved_targets = set(cast(Sequence[str], selected["approved_target_surfaces"]))
    candidate_targets = set(cast(Sequence[str], selected["candidate_target_surface"]))
    immutable_oracles = set(cast(Sequence[str], selected["immutable_oracles"]))
    if not candidate_targets.issubset(approved_targets):
        raise CreativeHypothesisSpecBridgeError(
            "CreativeHypothesisSpecificationBridge.selected_hypothesis."
            "candidate_target_surface must be a subset of approved_target_surfaces."
        )
    _reject_target_oracle_overlap(sorted(candidate_targets), sorted(immutable_oracles))
    approved_agents = set(cast(Sequence[str], selected["approved_agents"]))
    dispatch_agents = set(cast(Sequence[str], selected["dispatch_agents"]))
    if not approved_agents.issubset(dispatch_agents):
        raise CreativeHypothesisSpecBridgeError(
            "CreativeHypothesisSpecificationBridge.selected_hypothesis.approved_agents "
            "must be a subset of dispatch_agents."
        )


def _artifact_identity(
    payload: Mapping[str, Any],
    *,
    artifact_type: str,
    upstream_ids: tuple[str, ...] = (),
    policy_version: str = POLICY_VERSION,
) -> tuple[str, str]:
    fingerprint = cast(str, fingerprint_payload(cast(dict[str, Any], dict(payload))))
    return (
        build_asset_id(
            asset_type=artifact_type,
            rail="orchestration",
            version=SCHEMA_VERSION,
            policy_version=policy_version,
            fingerprint=fingerprint,
            upstream_ids=upstream_ids,
        ),
        build_idempotency_key(
            asset_type=artifact_type,
            rail="orchestration",
            version=SCHEMA_VERSION,
            policy_version=policy_version,
            fingerprint=fingerprint,
            upstream_ids=upstream_ids,
        ),
    )


def _validate_bridge_identity(payload: Mapping[str, Any]) -> None:
    expected_id, expected_idempotency_key = _artifact_identity(
        _bridge_identity_payload(payload),
        artifact_type=BRIDGE_ARTIFACT_TYPE,
        upstream_ids=(
            str(cast(Mapping[str, Any], payload["source"])["hypothesis_packet_id"]),
            str(cast(Mapping[str, Any], payload["source"])["approval_id"]),
            str(cast(Mapping[str, Any], payload["candidate_packet"])["candidate_id"]),
        ),
    )
    if payload["bridge_id"] != expected_id:
        raise CreativeHypothesisSpecBridgeError("bridge_id does not match content.")
    if payload["idempotency_key"] != expected_idempotency_key:
        raise CreativeHypothesisSpecBridgeError("idempotency_key does not match content.")


def _validate_metrics_identity(payload: Mapping[str, Any]) -> None:
    body = dict(payload)
    observed_id = str(body.pop("metrics_id"))
    observed_idempotency_key = str(body.pop("idempotency_key"))
    expected_id, expected_idempotency_key = _artifact_identity(
        body,
        artifact_type=METRICS_ARTIFACT_TYPE,
        upstream_ids=(str(payload["bridge_id"]), str(payload["candidate_id"])),
    )
    if observed_id != expected_id:
        raise CreativeHypothesisSpecBridgeError("metrics_id does not match content.")
    if observed_idempotency_key != expected_idempotency_key:
        raise CreativeHypothesisSpecBridgeError("idempotency_key does not match content.")


def _require_exact_keys(
    payload: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise CreativeHypothesisSpecBridgeError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeHypothesisSpecBridgeError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_bool(
    payload: Mapping[str, Any],
    key: str,
    *,
    expected: bool | None,
    label: str,
) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must be a boolean.")
    if expected is not None and value is not expected:
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must be {expected}.")
    return value


def _require_int(
    payload: Mapping[str, Any],
    key: str,
    *,
    min_value: int,
    max_value: int,
    label: str,
) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeHypothesisSpecBridgeError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must be a safe id.")
    reject_bridge_payload_safety(normalized, label=f"{label}.{key}")
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$", normalized):
        raise CreativeHypothesisSpecBridgeError(f"{label}.{key} must be a safe token.")
    reject_bridge_payload_safety(normalized, label=f"{label}.{key}")
    return normalized


def _require_optional_token(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _require_token({"value": value}, "value", label=label)


def _require_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a sha256 digest.")
    return value


def _require_string_list(
    raw_items: Any,
    *,
    label: str,
    allow_empty: bool,
) -> list[str]:
    if not isinstance(raw_items, list):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a list.")
    if not raw_items and not allow_empty:
        raise CreativeHypothesisSpecBridgeError(f"{label} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, str):
            raise CreativeHypothesisSpecBridgeError(f"{label}[{index}] must be a string.")
        cleaned = item.strip()
        if not cleaned:
            raise CreativeHypothesisSpecBridgeError(f"{label}[{index}] must be non-empty.")
        reject_bridge_payload_safety(cleaned, label=f"{label}[{index}]")
        if cleaned in seen:
            raise CreativeHypothesisSpecBridgeError(f"{label} must not contain duplicates.")
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _normalize_source_block(raw_source: Any, *, label: str) -> dict[str, str]:
    if not isinstance(raw_source, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_source, SOURCE_KEYS, label=label)
    return {
        "context_map_id": _require_id(raw_source, "context_map_id", label=label),
        "context_map_fingerprint": _require_sha256(
            raw_source["context_map_fingerprint"],
            label=f"{label}.context_map_fingerprint",
        ),
        "hypothesis_packet_id": _require_id(raw_source, "hypothesis_packet_id", label=label),
        "hypothesis_packet_fingerprint": _require_sha256(
            raw_source["hypothesis_packet_fingerprint"],
            label=f"{label}.hypothesis_packet_fingerprint",
        ),
        "coordinator_dispatch_id": _require_id(
            raw_source,
            "coordinator_dispatch_id",
            label=label,
        ),
        "coordinator_dispatch_fingerprint": _require_sha256(
            raw_source["coordinator_dispatch_fingerprint"],
            label=f"{label}.coordinator_dispatch_fingerprint",
        ),
        "approval_id": _require_id(raw_source, "approval_id", label=label),
        "approval_fingerprint": _require_sha256(
            raw_source["approval_fingerprint"],
            label=f"{label}.approval_fingerprint",
        ),
    }


def _normalize_metrics_source(raw_source: Any, *, label: str) -> dict[str, str]:
    if not isinstance(raw_source, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_source, METRICS_SOURCE_KEYS, label=label)
    source = _normalize_source_block(
        {key: raw_source[key] for key in SOURCE_KEYS},
        label=label,
    )
    source["candidate_fingerprint"] = _require_sha256(
        raw_source["candidate_fingerprint"],
        label=f"{label}.candidate_fingerprint",
    )
    return source


def _normalize_selected_hypothesis(raw_value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_value, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_value, SELECTED_HYPOTHESIS_KEYS, label=label)
    variant_count = _require_int(
        raw_value,
        "variant_count",
        min_value=3,
        max_value=5,
        label=label,
    )
    return {
        "hypothesis_id": _require_id(raw_value, "hypothesis_id", label=label),
        "hypothesis_fingerprint": _require_sha256(
            raw_value["hypothesis_fingerprint"],
            label=f"{label}.hypothesis_fingerprint",
        ),
        "approved_target_surfaces": _normalize_repo_path_list(
            raw_value["approved_target_surfaces"],
            label=f"{label}.approved_target_surfaces",
            allow_empty=False,
            allow_artifact_ref=False,
        ),
        "candidate_target_surface": _normalize_repo_path_list(
            raw_value["candidate_target_surface"],
            label=f"{label}.candidate_target_surface",
            allow_empty=False,
            allow_artifact_ref=False,
        ),
        "immutable_oracles": _normalize_repo_path_list(
            raw_value["immutable_oracles"],
            label=f"{label}.immutable_oracles",
            allow_empty=False,
            allow_artifact_ref=False,
        ),
        "approved_agents": _require_string_list(
            raw_value["approved_agents"],
            label=f"{label}.approved_agents",
            allow_empty=True,
        ),
        "dispatch_agents": _require_string_list(
            raw_value["dispatch_agents"],
            label=f"{label}.dispatch_agents",
            allow_empty=False,
        ),
        "variant_count": variant_count,
    }


def _normalize_candidate_ref(raw_value: Any, *, label: str) -> dict[str, str]:
    if not isinstance(raw_value, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_value, CANDIDATE_REF_KEYS, label=label)
    return {
        "candidate_id": _require_id(raw_value, "candidate_id", label=label),
        "candidate_fingerprint": _require_sha256(
            raw_value["candidate_fingerprint"],
            label=f"{label}.candidate_fingerprint",
        ),
        "candidate_packet_ref": _normalize_repo_path(
            raw_value["candidate_packet_ref"],
            label=f"{label}.candidate_packet_ref",
            allow_artifact_ref=True,
        ),
    }


def _normalize_spec_prepare(raw_value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_value, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_value, SPEC_PREPARE_KEYS, label=label)
    expected_files = _require_string_list(
        raw_value["expected_files"],
        label=f"{label}.expected_files",
        allow_empty=False,
    )
    if expected_files != list(PREPARE_FILENAMES):
        raise CreativeHypothesisSpecBridgeError(f"{label}.expected_files must match PR-1 prepare.")
    prepared = _require_bool(raw_value, "prepared", expected=None, label=label)
    next_allowed_action = _require_token(raw_value, "next_allowed_action", label=label)
    expected_next_action = "agent_skeptic_review" if prepared else "prepare_specification"
    if next_allowed_action != expected_next_action:
        raise CreativeHypothesisSpecBridgeError(
            f"{label}.next_allowed_action must be {expected_next_action}."
        )
    return {
        "run_dir_ref": _normalize_repo_path(
            raw_value["run_dir_ref"],
            label=f"{label}.run_dir_ref",
            allow_artifact_ref=True,
        ),
        "expected_files": expected_files,
        "prepared": prepared,
        "finalized": _require_bool(raw_value, "finalized", expected=False, label=label),
        "next_allowed_action": next_allowed_action,
    }


def _normalize_metrics_counts(raw_value: Any, *, label: str) -> dict[str, int]:
    if not isinstance(raw_value, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_value, METRICS_COUNTS_KEYS, label=label)
    return {
        "hypothesis_count": _require_int(
            raw_value, "hypothesis_count", min_value=0, max_value=5, label=label
        ),
        "approved_target_count": _require_int(
            raw_value, "approved_target_count", min_value=0, max_value=100, label=label
        ),
        "candidate_target_count": _require_int(
            raw_value, "candidate_target_count", min_value=0, max_value=100, label=label
        ),
        "immutable_oracle_count": _require_int(
            raw_value, "immutable_oracle_count", min_value=0, max_value=100, label=label
        ),
        "variant_count": _require_int(
            raw_value, "variant_count", min_value=3, max_value=5, label=label
        ),
        "prepare_files_written": _require_int(
            raw_value, "prepare_files_written", min_value=0, max_value=4, label=label
        ),
        "pending_skeptic_review_count": _require_int(
            raw_value, "pending_skeptic_review_count", min_value=0, max_value=15, label=label
        ),
    }


def _normalize_cost_metadata(raw_value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_value, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_value, COST_METADATA_KEYS, label=label)
    return {
        "provider_cost_available": _require_bool(
            raw_value,
            "provider_cost_available",
            expected=False,
            label=label,
        ),
        "provider_call_count": _require_int(
            raw_value,
            "provider_call_count",
            min_value=0,
            max_value=0,
            label=label,
        ),
        "provider_cost_basis": _require_const(
            raw_value,
            "provider_cost_basis",
            "not_available_local_no_provider_calls",
            label=label,
        ),
    }


def _normalize_bridge_authority(raw_authority: Any, *, label: str) -> dict[str, bool]:
    if not isinstance(raw_authority, Mapping):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_authority, BRIDGE_AUTHORITY_KEYS, label=label)
    normalized: dict[str, bool] = {}
    for key in sorted(BRIDGE_AUTHORITY_KEYS):
        expected = key in BRIDGE_AUTHORITY_TRUE_KEYS
        normalized[key] = _require_bool(raw_authority, key, expected=expected, label=label)
    return normalized


def _normalize_repo_path_list(
    raw_paths: Any,
    *,
    label: str,
    allow_empty: bool,
    allow_artifact_ref: bool,
) -> list[str]:
    if not isinstance(raw_paths, list):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a list.")
    if not raw_paths and not allow_empty:
        raise CreativeHypothesisSpecBridgeError(f"{label} must be non-empty.")
    normalized = [
        _normalize_repo_path(
            item,
            label=f"{label}[{index}]",
            allow_artifact_ref=allow_artifact_ref,
        )
        for index, item in enumerate(raw_paths)
    ]
    if len(normalized) != len(set(normalized)):
        raise CreativeHypothesisSpecBridgeError(f"{label} must not contain duplicates.")
    return sorted(normalized)


def _normalize_repo_path(raw_path: Any, *, label: str, allow_artifact_ref: bool) -> str:
    if not isinstance(raw_path, str):
        raise CreativeHypothesisSpecBridgeError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise CreativeHypothesisSpecBridgeError(f"{label} must be non-empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeHypothesisSpecBridgeError(f"{label} must not contain control characters.")
    if "\\" in value:
        raise CreativeHypothesisSpecBridgeError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")) or PurePosixPath(value).is_absolute():
        raise CreativeHypothesisSpecBridgeError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeHypothesisSpecBridgeError(f"{label} must not be a URL or scheme path.")
    path = PurePosixPath(value)
    if "." in path.parts or ".." in path.parts:
        raise CreativeHypothesisSpecBridgeError(f"{label} must not contain traversal segments.")
    normalized = path.as_posix()
    if normalized in {".git", ".venv", "worktrees"} or normalized.startswith(
        (".git/", ".venv/", "worktrees/")
    ):
        raise CreativeHypothesisSpecBridgeError(f"{label} points to a forbidden surface.")
    if normalized == "artifacts" or normalized.startswith("artifacts/"):
        if not allow_artifact_ref:
            raise CreativeHypothesisSpecBridgeError(f"{label} points to a local artifact path.")
        artifact_parts = PurePosixPath(normalized).parts
        if (
            len(artifact_parts) < 6
            or artifact_parts[:4] != ("artifacts", "orchestration", "creative_code", "spec_bridge")
            or not ID_RE.fullmatch(artifact_parts[4])
        ):
            raise CreativeHypothesisSpecBridgeError(
                f"{label} must reference a spec_bridge local artifact."
            )
    reject_bridge_payload_safety(normalized, label=label)
    return normalized

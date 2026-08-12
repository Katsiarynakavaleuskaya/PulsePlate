#!/usr/bin/env python3
"""Deterministic coordinator bootstrap entrypoint.

RU: Генерирует task packet для coordinator-first workflow.
EN: Generates a task packet artifact for coordinator-first routing.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any, cast

BOOTSTRAP_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(BOOTSTRAP_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_REPO_ROOT))

from core.evidence.fingerprints import fingerprint_payload
from core.judgment import (
    CLAIM_EVIDENCE_FIELDS,
    CLAIM_TYPES,
    EVIDENCE_MODES,
    JUDGMENT_FLOW,
    PROMOTION_LABELS,
    SUPPORT_STATUSES,
    UNCERTAINTY_FIELDS,
)
from scripts.orchestration.context_pack import (
    ORCHESTRATION_CONTEXT_FILES,
    REPO_ROOT,
    collect_context_pack,
    compute_task_packet_id,
    repo_relative_paths,
    resolve_domain,
)
from scripts.orchestration.context_pack_compression import (
    build_context_pack_compression,
    to_stable_mapping as context_compression_to_stable_mapping,
)
from scripts.orchestration.creative_spec_learning_rollup_contract import (
    validate_coordinator_advisory_hints,
)
from scripts.orchestration.creative_pilot_workspace_contract import (
    CreativePilotContractError,
    load_json_strict as load_creative_pilot_json_strict,
    phase_dispatch_fingerprint,
    validate_task_pilot_context,
    validate_dispatch_phase,
    validate_workspace as validate_creative_pilot_workspace,
)
from scripts.orchestration.embedding_retrieval_admission_telemetry import (
    build_embedding_retrieval_admission_telemetry,
    embedding_retrieval_admission_to_stable_mapping,
)
from scripts.orchestration.provider_model_tier_policy import (
    build_provider_model_routing_telemetry,
    to_stable_mapping as provider_model_routing_to_stable_mapping,
)
from scripts.orchestration.agent_consistency_loader import (
    load_inventory_agents,
    load_non_routable_agents,
)
from scripts.orchestration.bootstrap_sync_policy import (
    DOCS_ONLY_ENVELOPE_MODE,
    INVARIANT_CHANGE_CLASSES,
    INVARIANT_FAMILY_REPEAT_TRIGGER_RULE,
    INVARIANT_REVIEW_BOUNDARY_CLASSES,
    INVARIANT_REVIEW_COVERAGE_CLAIM,
    INVARIANT_REVIEW_REQUIRED_OUTPUT_FIELDS,
    INVARIANT_REVIEW_REQUIRED_ROLES,
    INVARIANT_REVIEW_RECOMMENDED_RESOLUTIONS,
    INVARIANT_REVIEW_STOP_CONDITION,
    INVARIANT_REVIEW_V2_FIELDS,
    INVARIANT_REVIEW_V2_REQUIRED_OUTPUT_FIELDS,
    InvariantReviewDecision,
    classify_invariant_review,
    compute_invariant_family_review_packet_id,
    needs_agents_sync as bootstrap_needs_agents_sync,
    needs_backlog_update as bootstrap_needs_backlog_update,
    needs_docs_sync as bootstrap_needs_docs_sync,
    requires_security_review as bootstrap_requires_security_review,
    resolve_analysis_envelope_mode,
)
from scripts.orchestration.design_lane_contract import (
    DESIGN_BLOCKERS,
    DESIGN_SOURCE_CODE_NATIVE_BRIEF,
    DESIGN_SOURCES,
    DESIGN_SOURCES_REQUIRING_CODE_NATIVE_BRIEF,
    DESIGN_TASK_MODES,
    FIGMA_DESIGN_SOURCES,
    FIGMA_LANE_TOOLS,
    READ_ONLY_DESIGN_SOURCES,
    canonicalize_design_blockers,
    design_trigger_present,
    normalize_design_blockers,
    normalize_design_enum,
    normalize_optional_text,
)
from scripts.orchestration.native_subagent_bridge import (
    BRIDGE_TRANSPORT,
    BRIDGE_TRANSPORTS,
    build_native_subagent_bridge,
)
from scripts.orchestration.route_with_telemetry import TELEMETRY_PATH, route
from scripts.orchestration.routing_graph_loader import (
    BootstrapLaneActivation,
    REQUIRED_BOOTSTRAP_LANE,
    load_bootstrap_lane_activations,
    load_routing_graph,
    require_bootstrap_lane_activation,
)
from scripts.orchestration.requested_agents import (
    IMPLEMENTATION_OWNER_SLUGS,
    MANDATORY_POST_OPEN_ORDER,
    POST_OPEN_BUG_HUNTER_AGENT,
    POST_OPEN_PULSEPLATE_PR_REVIEW,
    POST_OPEN_QA_AGENT,
    normalize_requested_agents,
)
from scripts.orchestration.review_invariant_family_relations import (
    ContractError,
    MAX_STDIN_BYTES,
    process_input_bytes,
)
from scripts.orchestration.skill_router import flatten_recommended_skills, route_skills
from scripts.orchestration.shadow_reuse_telemetry import (
    SHADOW_REUSE_FIELD,
    build_shadow_reuse_telemetry,
    collect_previous_task_packet_candidates,
    resolve_current_head_sha,
)

SCHEMA_VERSION = "3.1"
TASK_PACKET_DIR: Path = REPO_ROOT / "artifacts" / "orchestration" / "task_packets"
CREATIVE_LEARNING_HINTS_ROOT: Path = (
    REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "learning_rollup"
)
CREATIVE_PILOT_ROOT: Path = (
    REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "adaptive_pilots"
)
CREATIVE_PILOT_PHASES: tuple[str, ...] = ("independent", "rebuttal", "synthesis")
INVARIANT_REVIEW_SCHEMA_VERSION = "invariant_review.v1"
INVARIANT_REVIEW_V2_SCHEMA_VERSION = "invariant_review.v2"
INVARIANT_REVIEW_V2_COVERAGE_CLAIM = "explicit_normalized_snapshot_membership_only"
INVARIANT_FAMILY_REPEAT_MEMBERSHIP_SOURCE = "explicit_input_only"
INVARIANT_FAMILY_RELATIONS_INPUT_ROOT = PurePosixPath(
    "artifacts/orchestration/review_invariant_family_relations"
)
REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN = "rejected_unknown_agent"
REQUESTED_AGENT_STATUS_HONORED_PRIMARY = "honored_primary"
REQUESTED_AGENT_STATUS_HONORED_SECONDARY = "honored_secondary"
REQUESTED_AGENT_STATUS_HONORED_REVIEWER = "honored_reviewer"
REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE = "advisory_non_routable"
REQUESTED_AGENT_STATUS_PROMOTED = "promoted_requested_agent"
REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH = "advisory_domain_mismatch"
JUDGMENT_REQUIRED_CONTEXT_FILES: tuple[str, ...] = (
    *ORCHESTRATION_CONTEXT_FILES,
    "docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md",
    "docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md",
)
SUPPORTED_JUDGMENT_DECISION_MODE = "verification_first"
PR_PHASE_NONE = "none"
PR_PHASE_PRE_OPEN = "pre_open"
PR_PHASE_POST_OPEN_REVIEW = "post_open_review"
PR_PHASE_MERGE_READY = "merge_ready"
PR_PHASES: tuple[str, ...] = (
    PR_PHASE_NONE,
    PR_PHASE_PRE_OPEN,
    PR_PHASE_POST_OPEN_REVIEW,
    PR_PHASE_MERGE_READY,
)
NATIVE_BRIDGE_TRANSPORTS: tuple[str, ...] = (*BRIDGE_TRANSPORTS,)
POST_OPEN_REVIEW_LANE: tuple[str, ...] = MANDATORY_POST_OPEN_ORDER
INVARIANT_FAMILY_REVIEW_ROLE_ORDER: tuple[str, ...] = (
    "agent-coordinator",
    *INVARIANT_REVIEW_REQUIRED_ROLES,
    *POST_OPEN_REVIEW_LANE,
)
PR_REVIEW_ARTIFACT_TEMPLATE = "docs/review/PR_<N>_FIXED_MAPPING.md"
MERGE_READINESS_ENTRYPOINT = "scripts/orchestration/check_merge_ready.py"
ROLE_DISPATCH_MANIFEST_ENTRYPOINT = "scripts/orchestration/role_dispatch_bridge.py"
ROLE_DISPATCH_COMPATIBILITY_ENTRYPOINTS = ("scripts/orchestration/qoder_dispatch_bridge.py",)
PR_LIFECYCLE_CONTRACT_VERSION = "pulseplate.pr-lifecycle/v3"
FINAL_MATERIAL_ONLY = "final_material_only"
FINAL_MATERIAL_REVIEW_GATES: tuple[str, ...] = (POST_OPEN_PULSEPLATE_PR_REVIEW,)
POST_OPEN_REVIEW_CHAIN_POLICY = "post_open_roles_then_final_material_gates"
POST_OPEN_REVIEW_RERUN_ALLOWED_REASONS: tuple[str, ...] = (
    "coordinator_evidence_backed_reroute",
    "operator_explicit_request",
)
POST_OPEN_LATER_COMMENTS_HANDLING = "fixed_mapping_and_targeted_gates"
MANDATORY_PRE_OPEN_GATES: tuple[dict[str, str], ...] = (
    {
        "gate": "custom-role-dispatch",
        "entrypoint": ROLE_DISPATCH_MANIFEST_ENTRYPOINT,
        "requirement": (
            "Execute every bootstrap-requested/custom role pass from the dispatch "
            "manifest, including review-only entries with required_role_pass=true."
        ),
    },
    {
        "gate": "premortem-risk-review",
        "entrypoint": "pulseplate-premortem-risk-review",
        "requirement": (
            "Run premortem on the actual PR diff before PR open; every finding "
            "must be FIXED, NOT-A-BUG, or DEFERRED with backlog evidence."
        ),
    },
    {
        "gate": "experiment-runner-oracle",
        "entrypoint": "scripts/orchestration/experiment_runner.py",
        "requirement": (
            "Run Experiment Runner in oracle-only governance reviewer mode after "
            "the first coherent diff and before PR open."
        ),
    },
)
MESSAGE_ENVELOPE_PROTOCOL_VERSION = "1.0"
MESSAGE_ENVELOPE_DERIVED_VIEW = "TASK_PACKET_V1"
ENVELOPE_ONLY_RESULT_REQUIREMENT = "AGENT_RESULT_V1 envelope only (no preamble)"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _read_creative_pilot_workspace(
    raw_path: str | Path | None,
    phase: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if raw_path is None and phase is None:
        return None, None
    if raw_path is None or phase is None:
        raise ValueError(
            "--creative-pilot-workspace and --creative-pilot-phase must be supplied together"
        )
    if phase not in CREATIVE_PILOT_PHASES:
        raise ValueError("--creative-pilot-phase is unsupported")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    _reject_symlink_components(candidate, label="--creative-pilot-workspace")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(CREATIVE_PILOT_ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise ValueError(
            "--creative-pilot-workspace must be an existing JSON file under adaptive_pilots"
        ) from exc
    try:
        workspace = validate_creative_pilot_workspace(
            load_creative_pilot_json_strict(resolved.read_text(encoding="utf-8"))
        )
        workspace = validate_dispatch_phase(workspace, phase=phase)
    except (OSError, CreativePilotContractError) as exc:
        raise ValueError(f"invalid creative pilot workspace: {exc}") from exc
    assignments = [
        {
            "assignment_id": row["assignment_id"],
            "role": row["role"],
            "phase": row["phase"],
            "review_mode": row.get("review_mode", "specification_planning"),
            "diff_expected": row.get("diff_expected", False),
            "review_question": row.get(
                "review_question",
                "Assess the bounded specification against repository evidence and declared oracles.",
            ),
            "input_fingerprint": row["input_fingerprint"],
            "input_refs": list(row["input_refs"]),
        }
        for row in workspace["assignments"]
        if row["phase"] == phase
    ]
    if phase == "synthesis":
        assignments = [
            {
                "assignment_id": "synthesis:agent-coordinator",
                "role": "agent-coordinator",
                "phase": "synthesis",
                "review_mode": "specification_planning",
                "diff_expected": False,
                "review_question": "Synthesize only validated role results using deterministic hard gates.",
                "input_fingerprint": workspace["revision_fingerprint"],
                "input_refs": [workspace["workspace_id"], workspace["revision_fingerprint"]],
            }
        ]
    if not assignments:
        raise ValueError(f"creative pilot workspace has no {phase} assignments")
    context = {
        "schema_version": "creative_pilot_context.v2",
        "workspace_id": workspace["workspace_id"],
        "workspace_intent_fingerprint": workspace["intent_fingerprint"],
        "workspace_revision_fingerprint": workspace["revision_fingerprint"],
        "phase": phase,
        "dispatch_input_fingerprint": (
            workspace["revision_fingerprint"]
            if phase == "synthesis"
            else phase_dispatch_fingerprint(workspace, phase=phase)
        ),
        "assignments": assignments,
        "authority": {
            "read_structured_inputs": True,
            "generate_patch": False,
            "write_repository": False,
            "call_provider": False,
        },
    }
    return workspace, validate_task_pilot_context(context)


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    seen: set[str] = set()
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"creative learning hints JSON has duplicate key: {key}")
        seen.add(key)
        payload[key] = value
    return payload


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
            raise ValueError(f"{label} must not traverse symlinks")


def _resolve_creative_learning_hints_path(raw_path: str | Path) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    _reject_symlink_components(candidate, label="--creative-learning-hints")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError("--creative-learning-hints must point to an existing JSON file") from exc
    try:
        resolved.relative_to(REPO_ROOT.resolve())
        resolved.relative_to(CREATIVE_LEARNING_HINTS_ROOT.resolve(strict=False))
    except ValueError as exc:
        raise ValueError(
            "--creative-learning-hints must stay under "
            "artifacts/orchestration/creative_code/learning_rollup"
        ) from exc
    if not resolved.is_file() or resolved.suffix != ".json":
        raise ValueError("--creative-learning-hints must point to a JSON file")
    return resolved


def _read_creative_learning_hints(raw_path: str | Path | None) -> dict[str, Any] | None:
    if raw_path is None:
        return None
    hints_path = _resolve_creative_learning_hints_path(raw_path)
    try:
        payload = json.loads(
            hints_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("unable to read --creative-learning-hints JSON") from exc
    except ValueError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("unable to read --creative-learning-hints JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("--creative-learning-hints must contain a JSON object")
    return cast(dict[str, Any], validate_coordinator_advisory_hints(payload))


def _build_creative_learning_hints_packet(
    hints: dict[str, Any] | None,
    *,
    hints_fingerprint: str,
) -> dict[str, Any]:
    if hints is None:
        source_hints_id = ""
        source_rollup_id = ""
        source_rollup_fingerprint = ""
        recommended_role_focus: list[dict[str, Any]] = []
        reuse_lesson_ids: list[str] = []
        avoid_lesson_ids: list[str] = []
    else:
        source_hints_id = str(hints["hints_id"])
        source_rollup_id = str(hints["source_rollup_id"])
        source_rollup_fingerprint = str(hints["source_rollup_fingerprint"])
        recommended_role_focus = list(hints["recommended_role_focus"])
        reuse_lesson_ids = list(hints["reuse_lesson_ids"])
        avoid_lesson_ids = list(hints["avoid_lesson_ids"])

    return {
        "schema_version": "creative_learning_hints_packet.v1",
        "current_packet_includes_hints": hints is not None,
        "source_hints_id": source_hints_id,
        "source_hints_fingerprint": hints_fingerprint,
        "source_rollup_id": source_rollup_id,
        "source_rollup_fingerprint": source_rollup_fingerprint,
        "recommended_role_focus": recommended_role_focus,
        "reuse_lesson_ids": reuse_lesson_ids,
        "avoid_lesson_ids": avoid_lesson_ids,
        "authority_boundary": "advisory_only_non_runtime",
        "side_effects_allowed": False,
        "routing_authority": False,
        "execution_authority": False,
        "merge_readiness_authority": False,
        "patch_generation_authority": False,
        "semantic_cache_used": False,
        "graph_truth_updated": False,
        "product_runtime_truth": False,
        "change_primary_agent": False,
        "force_agent_routing": False,
        "skip_required_roles": False,
        "execute_agents": False,
        "change_lifecycle_gates": False,
    }


def _design_fingerprint(*, design_lane_mode: str, design_lane_contract: dict[str, Any]) -> str:
    """Return a deterministic fingerprint for design-lane packet identity."""

    canonical_contract = dict(design_lane_contract)
    canonical_contract["blockers"] = canonicalize_design_blockers(
        list(design_lane_contract.get("blockers", ()))
    )
    return json.dumps(
        {
            "design_lane_mode": design_lane_mode,
            "design_lane_contract": canonical_contract,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _build_design_lane_contract(
    *,
    design_source: str | None,
    source_url: str | None,
    file_key_or_workspace: str | None,
    node_id_or_frame_id: str | None,
    target_surface: str | None,
    task_mode: str | None,
    figma_lane_tool: str | None,
    design_blockers: list[str] | tuple[str, ...],
    code_native_design_brief_path: str | None,
    explicit_creation_mode: bool,
) -> tuple[str, dict[str, Any], bool]:
    """Build deterministic design-lane packet metadata."""

    normalized_design_source = normalize_design_enum(
        field_name="design_source",
        value=design_source,
        allowed_values=DESIGN_SOURCES,
    )
    normalized_source_url = normalize_optional_text(source_url)
    normalized_file_key_or_workspace = normalize_optional_text(file_key_or_workspace)
    normalized_node_id_or_frame_id = normalize_optional_text(node_id_or_frame_id)
    normalized_target_surface = normalize_optional_text(target_surface)
    normalized_task_mode = normalize_design_enum(
        field_name="task_mode",
        value=task_mode,
        allowed_values=DESIGN_TASK_MODES,
    )
    normalized_figma_lane_tool = normalize_design_enum(
        field_name="figma_lane_tool",
        value=figma_lane_tool,
        allowed_values=FIGMA_LANE_TOOLS,
    )
    normalized_code_native_design_brief_path = normalize_optional_text(
        code_native_design_brief_path
    )
    blockers = normalize_design_blockers(design_blockers)
    has_design_trigger = design_trigger_present(
        design_source=normalized_design_source,
        source_url=normalized_source_url,
        file_key_or_workspace=normalized_file_key_or_workspace,
        node_id_or_frame_id=normalized_node_id_or_frame_id,
        target_surface=normalized_target_surface,
        task_mode=normalized_task_mode,
        figma_lane_tool=normalized_figma_lane_tool,
        code_native_design_brief_path=normalized_code_native_design_brief_path,
        explicit_creation_mode=explicit_creation_mode,
    )
    code_native_design_brief_required = (
        normalized_design_source in DESIGN_SOURCES_REQUIRING_CODE_NATIVE_BRIEF
    )

    if normalized_figma_lane_tool and normalized_design_source not in FIGMA_DESIGN_SOURCES:
        raise ValueError(
            "figma_lane_tool is allowed only for figma_design or figma_make design_source"
        )

    if not has_design_trigger:
        contract = {
            "design_source": "",
            "source_url": "",
            "file_key_or_workspace": "",
            "node_id_or_frame_id": "",
            "target_surface": "",
            "task_mode": "",
            "figma_lane_tool": "",
            "blockers": ["missing_design_trigger"],
            "code_native_design_brief_required": False,
            "code_native_design_brief_path": "",
            "explicit_creation_mode": False,
        }
        return "disabled", contract, False

    if not normalized_design_source:
        blockers.append("missing_design_metadata")
    if not normalized_target_surface:
        blockers.append("missing_design_metadata")
    if not normalized_task_mode:
        blockers.append("missing_design_metadata")

    if (
        normalized_design_source == DESIGN_SOURCE_CODE_NATIVE_BRIEF
        and not normalized_code_native_design_brief_path
    ):
        blockers.append("missing_design_metadata")

    if normalized_design_source in FIGMA_DESIGN_SOURCES:
        if not normalized_figma_lane_tool:
            blockers.append("missing_design_metadata")
        if code_native_design_brief_required and not normalized_code_native_design_brief_path:
            blockers.append("missing_design_metadata")
        if not (explicit_creation_mode and normalized_task_mode == "implement"):
            if not normalized_source_url or not normalized_file_key_or_workspace:
                blockers.append("blocked_by_design_url")
            if (
                normalized_source_url
                and normalized_file_key_or_workspace
                and not normalized_node_id_or_frame_id
            ):
                blockers.append("blocked_by_node_id_capture")

    blockers = canonicalize_design_blockers(blockers)
    design_lane_mode = "read_only"
    if normalized_design_source in READ_ONLY_DESIGN_SOURCES:
        design_lane_mode = "read_only"
    elif normalized_task_mode and not blockers:
        design_lane_mode = normalized_task_mode

    contract = {
        "design_source": normalized_design_source,
        "source_url": normalized_source_url,
        "file_key_or_workspace": normalized_file_key_or_workspace,
        "node_id_or_frame_id": normalized_node_id_or_frame_id,
        "target_surface": normalized_target_surface,
        "task_mode": normalized_task_mode,
        "figma_lane_tool": normalized_figma_lane_tool,
        "blockers": blockers,
        "code_native_design_brief_required": code_native_design_brief_required,
        "code_native_design_brief_path": normalized_code_native_design_brief_path,
        "explicit_creation_mode": explicit_creation_mode,
    }
    return design_lane_mode, contract, True


def _select_independent_reviewer(
    *,
    primary_agent: str,
    canonical_reviewer: str,
    canonical_secondary: str | None,
    previous_primary: str,
) -> str:
    """Keep reviewer independent after requested-agent promotion."""

    reviewer_candidate = next(
        (
            candidate
            for candidate in (
                canonical_reviewer,
                canonical_secondary,
                previous_primary,
                "agent-coordinator",
            )
            if candidate and candidate != primary_agent
        ),
        None,
    )
    if reviewer_candidate is not None:
        return reviewer_candidate
    return "qa-engineer-agent"


def _judgment_lane_enabled(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
    activation: BootstrapLaneActivation,
) -> bool:
    """Return True when the task clearly targets the judgment/adjudication lane."""

    normalized_haystack = " ".join(
        [
            goal.strip().lower(),
            task_class.strip().lower(),
            *(path.lower() for path in candidate_paths),
        ]
    )
    return any(term in normalized_haystack for term in activation.signal_terms)


def _validated_judgment_activation(
    activation: BootstrapLaneActivation,
) -> BootstrapLaneActivation:
    """Reject unsupported decision modes for the current judgment packet contract."""

    if activation.decision_mode != SUPPORTED_JUDGMENT_DECISION_MODE:
        raise ValueError(
            "Unsupported judgment lane decision mode: "
            f"{activation.decision_mode}. Supported: {SUPPORTED_JUDGMENT_DECISION_MODE}"
        )
    return activation


def _normalize_pr_phase(pr_phase: str) -> str:
    """Return a validated PR lifecycle phase.

    RU: PR4 adds explicit lifecycle phases without changing the safe default.
    EN: PR4 adds explicit lifecycle phases without changing the safe default.
    """

    normalized_phase = pr_phase.strip().lower()
    if normalized_phase not in PR_PHASES:
        supported_phases = ", ".join(PR_PHASES)
        raise ValueError(f"Unsupported pr_phase: {pr_phase}. Supported: {supported_phases}")
    return normalized_phase


def _provider_no_claim_policy() -> dict[str, Any]:
    """Return the closed provider-neutral no-claim policy."""

    return {
        "output_required": False,
        "seal_without_provider_flags": True,
        "provider_invocation_required": False,
        "provider_retry_required": False,
        "provider_wait_required": False,
        "substitute_provider_required": False,
        "operator_override_required": False,
        "ttl_required": False,
        "absence_is_pass": False,
        "absence_is_review": False,
        "absence_is_scan": False,
        "absence_is_approval": False,
        "absence_is_no_findings": False,
    }


def _build_pr_lifecycle_contract(pr_phase: str) -> dict[str, Any]:
    """Return deterministic packet metadata for the requested PR phase."""

    requires_pr = pr_phase in {PR_PHASE_POST_OPEN_REVIEW, PR_PHASE_MERGE_READY}
    requires_current_head = requires_pr
    post_open_review = pr_phase == PR_PHASE_POST_OPEN_REVIEW
    if post_open_review:
        review_lane = list(POST_OPEN_REVIEW_LANE)
    else:
        review_lane = []
    return {
        "contract_version": PR_LIFECYCLE_CONTRACT_VERSION,
        "requires_pr": requires_pr,
        "post_open_review_required": post_open_review,
        "review_lane": review_lane,
        "post_open_codex_security_scan_required": False,
        "post_open_codex_security_scan": "",
        "post_open_codex_security_scan_timing": "",
        "post_open_pulseplate_pr_review_required": post_open_review,
        "post_open_pulseplate_pr_review": (
            POST_OPEN_PULSEPLATE_PR_REVIEW if post_open_review else ""
        ),
        "post_open_pulseplate_pr_review_timing": (FINAL_MATERIAL_ONLY if post_open_review else ""),
        "final_material_review_gates": (
            list(FINAL_MATERIAL_REVIEW_GATES) if post_open_review else []
        ),
        "final_material_review_timing": (FINAL_MATERIAL_ONLY if post_open_review else ""),
        "post_open_review_chain_policy": (
            POST_OPEN_REVIEW_CHAIN_POLICY if post_open_review else ""
        ),
        "post_open_review_rerun_allowed_reasons": (
            list(POST_OPEN_REVIEW_RERUN_ALLOWED_REASONS) if post_open_review else []
        ),
        "post_open_later_comments_handling": (
            POST_OPEN_LATER_COMMENTS_HANDLING if post_open_review else ""
        ),
        "provider_no_claim_policy": _provider_no_claim_policy(),
        "artifact_template": PR_REVIEW_ARTIFACT_TEMPLATE if requires_pr else "",
        "current_head_required": requires_current_head,
        "current_head_truth": "latest-current-head" if requires_current_head else "not-applicable",
        "merge_readiness_entrypoint": (
            MERGE_READINESS_ENTRYPOINT if pr_phase == PR_PHASE_MERGE_READY else ""
        ),
    }


def _implementation_owner_slugs_from_bridge(
    native_subagent_bridge: dict[str, Any],
) -> list[str]:
    """Return packet-bound implementation owners in dispatch order."""

    ordered_owner_slugs: list[str] = []
    secondary_bindings = native_subagent_bridge.get("secondary", [])
    if not isinstance(secondary_bindings, list):
        secondary_bindings = []
    for binding in [native_subagent_bridge.get("primary"), *secondary_bindings]:
        if not isinstance(binding, dict):
            continue
        slug = str(binding.get("repo_agent_slug", "")).strip().lower()
        if slug not in IMPLEMENTATION_OWNER_SLUGS or slug in ordered_owner_slugs:
            continue
        if binding.get("execution_mode") != "read_write":
            continue
        ordered_owner_slugs.append(slug)
    return ordered_owner_slugs


def _build_role_dispatch_manifest_command(
    implementation_owner_slugs: list[str],
) -> str:
    """Build the command operators should run after packet creation."""

    command_parts = [
        "python3",
        ROLE_DISPATCH_MANIFEST_ENTRYPOINT,
        "--packet",
        "<packet>",
    ]
    if implementation_owner_slugs:
        command_parts.extend(["--mode", "runtime"])
        for owner_slug in implementation_owner_slugs:
            command_parts.extend(["--implementation-owner", owner_slug])
    command_parts.append("--pretty")
    return " ".join(command_parts)


def _invariant_review_required_now(
    decision: InvariantReviewDecision,
    *,
    pr_phase: str,
) -> bool:
    """Return whether this opening-phase packet must dispatch the pre-fix review."""

    return decision.required and pr_phase in {PR_PHASE_NONE, PR_PHASE_PRE_OPEN}


def _build_invariant_review_packet(
    decision: InvariantReviewDecision,
    *,
    required_now: bool,
) -> dict[str, Any]:
    """Return stable pending-only invariant-review admission metadata."""

    return {
        "schema_version": INVARIANT_REVIEW_SCHEMA_VERSION,
        "state": "required_pending" if required_now else "not_required",
        "change_classes": list(decision.change_classes),
        "trigger_evidence": [evidence.to_mapping() for evidence in decision.trigger_evidence],
        "coverage_claim": INVARIANT_REVIEW_COVERAGE_CLAIM,
        "required_roles": (list(INVARIANT_REVIEW_REQUIRED_ROLES) if required_now else []),
        "boundary_classes": list(INVARIANT_REVIEW_BOUNDARY_CLASSES),
        "required_output_fields": list(INVARIANT_REVIEW_REQUIRED_OUTPUT_FIELDS),
        "stop_condition": INVARIANT_REVIEW_STOP_CONDITION,
        "implementation_authority": False,
        "merge_authority": False,
    }


def _required_open_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise ValueError(f"--review-invariant-family-relations-input requires {name} support")
    return value


def _normalize_invariant_family_relations_input(raw_path: str) -> tuple[str, ...]:
    """Accept exactly one repo-relative direct-child JSON artifact path."""

    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(
            "--review-invariant-family-relations-input must be a repo-relative JSON path"
        )
    if raw_path != raw_path.strip() or "\\" in raw_path:
        raise ValueError(
            "--review-invariant-family-relations-input must use exact POSIX path syntax"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_path):
        raise ValueError(
            "--review-invariant-family-relations-input must not contain control characters"
        )
    path = PurePosixPath(raw_path)
    if (
        path.is_absolute()
        or path.as_posix() != raw_path
        or path.parent != INVARIANT_FAMILY_RELATIONS_INPUT_ROOT
        or path.name in {"", ".", ".."}
        or path.suffix != ".json"
    ):
        raise ValueError(
            "--review-invariant-family-relations-input must be a direct-child JSON under "
            f"{INVARIANT_FAMILY_RELATIONS_INPUT_ROOT.as_posix()}/"
        )
    return path.parts


def _read_invariant_family_relations_input(raw_path: str) -> dict[str, Any]:
    """Read one bounded regular artifact and canonicalize it through L1 once."""

    parts = _normalize_invariant_family_relations_input(raw_path)
    directory_flags = (
        os.O_RDONLY
        | _required_open_flag("O_DIRECTORY")
        | _required_open_flag("O_NOFOLLOW")
        | _required_open_flag("O_CLOEXEC")
    )
    file_flags = (
        os.O_RDONLY
        | _required_open_flag("O_NOFOLLOW")
        | _required_open_flag("O_CLOEXEC")
        | _required_open_flag("O_NONBLOCK")
    )
    directory_fds: list[int] = []
    file_fd = -1
    try:
        directory_fds.append(os.open(REPO_ROOT, directory_flags))
        for component in parts[:-1]:
            directory_fds.append(os.open(component, directory_flags, dir_fd=directory_fds[-1]))
        file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fds[-1])
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("--review-invariant-family-relations-input must be a regular file")
        if before.st_size > MAX_STDIN_BYTES:
            raise ValueError("--review-invariant-family-relations-input exceeds the L1 bound")
        chunks: list[bytes] = []
        remaining = MAX_STDIN_BYTES + 1
        while remaining > 0:
            chunk = os.read(file_fd, min(1_048_576, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(file_fd)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if (
            len(raw) > MAX_STDIN_BYTES
            or len(raw) != before.st_size
            or before_identity != after_identity
        ):
            raise ValueError(
                "--review-invariant-family-relations-input changed or exceeded its bound"
            )
    except ValueError:
        raise
    except (OSError, NotImplementedError):
        raise ValueError(
            "--review-invariant-family-relations-input could not be read safely"
        ) from None
    finally:
        active_error = sys.exc_info()[1]
        close_failed = False
        for descriptor in (file_fd, *reversed(directory_fds)):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    close_failed = True
        if active_error is None and close_failed:
            raise ValueError(
                "--review-invariant-family-relations-input descriptor cleanup failed"
            ) from None

    try:
        canonical_output = process_input_bytes(raw)
    except ContractError as exc:
        raise ValueError(
            f"--review-invariant-family-relations-input failed canonical L1 validation: {exc.code}"
        ) from exc
    canonical_artifact = json.loads(canonical_output)
    if not isinstance(canonical_artifact, dict):
        raise ValueError("canonical L1 output must be a JSON object")
    return cast(dict[str, Any], canonical_artifact)


def _build_family_repeat_projection(artifact: dict[str, Any]) -> dict[str, Any]:
    """Project only explicit L1 rows needed by the bounded L2 trigger."""

    snapshot = cast(dict[str, Any], artifact["snapshot"])
    families = cast(list[dict[str, Any]], snapshot["families"])
    repeated_families = [
        {
            "family_id": family["family_id"],
            "finding_ids": list(cast(list[str], family["finding_ids"])),
        }
        for family in families
        if len(cast(list[str], family["finding_ids"])) >= 2
    ]
    repeated_ids = {str(family["family_id"]) for family in repeated_families}
    relations = cast(list[dict[str, Any]], artifact["relations"])
    touching_relations = [
        dict(relation)
        for relation in relations
        if relation["left_family_id"] in repeated_ids or relation["right_family_id"] in repeated_ids
    ]
    return {
        "source_schema_version": artifact["schema_version"],
        "source_policy_version": artifact["policy_version"],
        "snapshot_fingerprint": artifact["snapshot_fingerprint"],
        "artifact_fingerprint": artifact["artifact_fingerprint"],
        "idempotency_key": artifact["idempotency_key"],
        "trigger_rule": INVARIANT_FAMILY_REPEAT_TRIGGER_RULE,
        "membership_source": INVARIANT_FAMILY_REPEAT_MEMBERSHIP_SOURCE,
        "repeated_families": repeated_families,
        "relations_touching_repeated_families": touching_relations,
        "unknown_findings_present": bool(artifact["unknown_finding_ids"]),
    }


def _build_invariant_review_v2_packet(family_repeat: dict[str, Any]) -> dict[str, Any]:
    required = bool(family_repeat["repeated_families"])
    return {
        "schema_version": INVARIANT_REVIEW_V2_SCHEMA_VERSION,
        "state": "required_pending" if required else "not_required",
        "coverage_claim": INVARIANT_REVIEW_V2_COVERAGE_CLAIM,
        "required_roles": list(INVARIANT_REVIEW_REQUIRED_ROLES) if required else [],
        "boundary_classes": list(INVARIANT_REVIEW_BOUNDARY_CLASSES),
        "required_output_fields": list(INVARIANT_REVIEW_V2_REQUIRED_OUTPUT_FIELDS),
        "stop_condition": INVARIANT_REVIEW_STOP_CONDITION,
        "family_repeat": family_repeat,
        "implementation_authority": False,
        "merge_authority": False,
    }


def _bind_invariant_review_packet_id(
    base_packet_id: str,
    *,
    invariant_review_fingerprint: str,
) -> str:
    """Frame the optional class identity without changing legacy packet ids."""

    normalized_fingerprint = invariant_review_fingerprint.strip()
    if not normalized_fingerprint:
        return base_packet_id
    framed_fingerprint = str(
        fingerprint_payload(
            {
                "base_task_packet_id": base_packet_id,
                "identity_schema": "task_packet_id.invariant_review.v1",
                "invariant_review_fingerprint": normalized_fingerprint,
            }
        )
    )
    return framed_fingerprint.removeprefix("sha256:")[:12]


def _append_system_invariant_review_roles(
    *,
    primary_agent: str,
    secondary_agents: list[str],
    reviewer: str,
) -> list[str]:
    """Add the system-required pre-fix roles without mutating requested agents."""

    ordered_secondary_agents = list(secondary_agents)
    planned_agents = {primary_agent, reviewer, *ordered_secondary_agents}
    for agent_slug in (
        "agent-coordinator",
        *INVARIANT_REVIEW_REQUIRED_ROLES,
    ):
        if agent_slug in planned_agents:
            continue
        ordered_secondary_agents.append(agent_slug)
        planned_agents.add(agent_slug)
    return ordered_secondary_agents


def _spawnable_role_order_from_bridge(
    native_subagent_bridge: dict[str, Any],
) -> list[str]:
    """Return the exact spawnable binding order projected by the native bridge."""

    ordered_roles: list[str] = []

    def add_binding(binding: Any, *, default_spawnable: bool) -> None:
        if not isinstance(binding, dict):
            return
        dispatch_contract = binding.get("dispatch_contract")
        if dispatch_contract is None:
            spawnable = default_spawnable
        elif isinstance(dispatch_contract, dict):
            spawnable = not (
                dispatch_contract.get("advisory_only")
                or dispatch_contract.get("spawn_with_native_subagent") is False
            )
        else:
            spawnable = False
        slug = str(binding.get("repo_agent_slug", "")).strip()
        if spawnable and slug and slug not in ordered_roles:
            ordered_roles.append(slug)

    add_binding(native_subagent_bridge.get("primary"), default_spawnable=True)
    for binding in native_subagent_bridge.get("secondary", []):
        add_binding(binding, default_spawnable=True)
    for binding in native_subagent_bridge.get("advisory", []):
        add_binding(binding, default_spawnable=False)
    add_binding(native_subagent_bridge.get("reviewer"), default_spawnable=True)
    return ordered_roles


def _build_invariant_dispatch_role_order(
    native_subagent_bridge: dict[str, Any],
) -> list[str]:
    """Place the pre-fix pair after coordinator without changing role membership."""

    spawnable_roles = _spawnable_role_order_from_bridge(native_subagent_bridge)
    required_prefix = [
        "agent-coordinator",
        *INVARIANT_REVIEW_REQUIRED_ROLES,
    ]
    missing_roles = [
        agent_slug for agent_slug in required_prefix if agent_slug not in spawnable_roles
    ]
    if missing_roles:
        raise ValueError(
            "invariant review dispatch is missing required spawnable roles: "
            + ", ".join(missing_roles)
        )
    return [
        *required_prefix,
        *[agent_slug for agent_slug in spawnable_roles if agent_slug not in required_prefix],
    ]


def build_role_agent_dispatch_contract(
    *,
    native_subagent_bridge: dict[str, Any] | None = None,
    pr_phase: str = PR_PHASE_NONE,
    dispatch_role_order: list[str] | None = None,
) -> dict[str, Any]:
    """Return deterministic metadata for the post-bootstrap role dispatch step."""

    implementation_owner_slugs = (
        _implementation_owner_slugs_from_bridge(native_subagent_bridge)
        if native_subagent_bridge
        and pr_phase not in {PR_PHASE_POST_OPEN_REVIEW, PR_PHASE_MERGE_READY}
        else []
    )
    contract = {
        "packet_creation_executes_roles": False,
        "role_agent_dispatch_required": True,
        "role_agent_dispatch_hard_gate": True,
        "dispatch_manifest_entrypoint": ROLE_DISPATCH_MANIFEST_ENTRYPOINT,
        "dispatch_manifest_compatibility_entrypoints": list(
            ROLE_DISPATCH_COMPATIBILITY_ENTRYPOINTS
        ),
        "dispatch_manifest_command": _build_role_dispatch_manifest_command(
            implementation_owner_slugs
        ),
        "runtime_implementation_owner_flags_required": bool(implementation_owner_slugs),
        "runtime_implementation_owners": implementation_owner_slugs,
        "must_execute_dispatch_sequence_in_order": True,
        "advisory_role_passes_required": True,
        "requested_custom_roles_are_not_skippable": True,
        "missing_role_execution_blocks_readiness": True,
        "mandatory_pre_open_gates": [dict(gate) for gate in MANDATORY_PRE_OPEN_GATES],
    }
    if dispatch_role_order is not None:
        contract["dispatch_role_order"] = list(dispatch_role_order)
    return contract


def _apply_pr_lifecycle_review_path(
    *,
    pr_phase: str,
    primary_agent: str,
    secondary_agents: list[str],
    reviewer: str,
) -> tuple[str, list[str], str]:
    """Inject the canonical post-open review lane for PR lifecycle work.

    RU: post-open review обязан держать
    `qa-engineer-agent -> bug-hunter -> security-auditor`.
    EN: post-open review must keep
    `qa-engineer-agent -> bug-hunter -> security-auditor`.
    """

    if pr_phase != PR_PHASE_POST_OPEN_REVIEW:
        return primary_agent, secondary_agents, reviewer

    adjusted_primary_agent = primary_agent
    adjusted_secondary_agents = list(secondary_agents)
    adjusted_reviewer = reviewer
    qa_agent = POST_OPEN_QA_AGENT
    bug_hunter_agent = POST_OPEN_BUG_HUNTER_AGENT
    post_open_secondary_tail = list(POST_OPEN_REVIEW_LANE[1:])

    if primary_agent == bug_hunter_agent:
        adjusted_primary_agent = qa_agent
        adjusted_reviewer = _select_independent_reviewer(
            primary_agent=adjusted_primary_agent,
            canonical_reviewer=reviewer,
            canonical_secondary=bug_hunter_agent,
            previous_primary=primary_agent,
        )
        if adjusted_reviewer in post_open_secondary_tail:
            adjusted_reviewer = "agent-coordinator"
        adjusted_secondary_agents = [
            candidate
            for candidate in [*post_open_secondary_tail, *adjusted_secondary_agents]
            if candidate != adjusted_primary_agent
        ]
    elif primary_agent == qa_agent:
        adjusted_secondary_agents = [*post_open_secondary_tail, *adjusted_secondary_agents]
    else:
        previous_primary = primary_agent
        adjusted_primary_agent = qa_agent
        adjusted_reviewer = _select_independent_reviewer(
            primary_agent=adjusted_primary_agent,
            canonical_reviewer=reviewer,
            canonical_secondary=bug_hunter_agent,
            previous_primary=previous_primary,
        )
        if adjusted_reviewer in post_open_secondary_tail:
            adjusted_reviewer = "agent-coordinator"
        adjusted_secondary_agents = [
            candidate
            for candidate in [
                *post_open_secondary_tail,
                previous_primary,
                *adjusted_secondary_agents,
            ]
            if candidate != adjusted_primary_agent
        ]

    return adjusted_primary_agent, adjusted_secondary_agents, adjusted_reviewer


def _normalize_secondary_review_path(
    *,
    primary_agent: str,
    secondary_agents: list[str],
    reviewer: str,
) -> list[str]:
    """Keep packet review roles unique before building the native bridge."""

    normalized_secondary_agents: list[str] = []
    blocked_agents = {primary_agent, reviewer}
    for agent_slug in secondary_agents:
        if agent_slug in blocked_agents or agent_slug in normalized_secondary_agents:
            continue
        normalized_secondary_agents.append(agent_slug)
    return normalized_secondary_agents


def _reconcile_requested_agent_dispositions(
    *,
    requested_agent_disposition: list[dict[str, str]],
    primary_agent: str,
    secondary_agents: list[str],
    reviewer: str,
) -> None:
    """Align requested-agent disposition metadata with the final packet roles."""

    secondary_honored_statuses = {
        REQUESTED_AGENT_STATUS_PROMOTED,
        REQUESTED_AGENT_STATUS_HONORED_PRIMARY,
    }
    secondary_agent_set = set(secondary_agents)
    for disposition in requested_agent_disposition:
        agent_slug = disposition["agent"]
        status = disposition["status"]
        if status == REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN:
            continue
        if agent_slug == primary_agent:
            if status != REQUESTED_AGENT_STATUS_HONORED_PRIMARY:
                disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_PRIMARY
                disposition["reason"] = (
                    "Requested agent stayed honored as primary after PR lifecycle synthesis."
                )
            continue
        if agent_slug == reviewer:
            disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_REVIEWER
            disposition["reason"] = (
                "Requested agent stayed honored as reviewer after PR lifecycle synthesis."
            )
            continue
        if agent_slug in secondary_agent_set and status in secondary_honored_statuses:
            disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_SECONDARY
            disposition["reason"] = (
                "Requested agent stayed honored in secondary after PR lifecycle synthesis."
            )


def partition_native_secondaries(
    *,
    secondary_agents: list[str],
    requested_agent_disposition: list[dict[str, str]],
    forced_executable_agents: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Split secondaries from required custom-role collaborators.

    RU: review-only contribution metadata is not permission to skip a requested
    role pass.
    EN: review-only contribution metadata is not permission to skip a requested
    role pass.
    """

    advisory_statuses = {
        REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
        REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
    }
    known_statuses = {
        REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN,
        REQUESTED_AGENT_STATUS_HONORED_PRIMARY,
        REQUESTED_AGENT_STATUS_HONORED_SECONDARY,
        REQUESTED_AGENT_STATUS_HONORED_REVIEWER,
        REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
        REQUESTED_AGENT_STATUS_PROMOTED,
        REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
    }
    seen_disposition_agents: set[str] = set()
    for disposition in requested_agent_disposition:
        if not isinstance(disposition, dict):
            raise ValueError("requested_agent_disposition entries must be objects")
        agent_slug = disposition.get("agent")
        status = disposition.get("status")
        if not isinstance(agent_slug, str) or not agent_slug or agent_slug != agent_slug.strip():
            raise ValueError("requested_agent_disposition agent must be canonical")
        if agent_slug in seen_disposition_agents:
            raise ValueError("requested_agent_disposition agents must be unique")
        if not isinstance(status, str) or status not in known_statuses:
            raise ValueError("requested_agent_disposition status must be recognized")
        seen_disposition_agents.add(agent_slug)
    normalized_forced_executable_agents = forced_executable_agents or set()
    advisory_agents = {
        disposition["agent"]
        for disposition in requested_agent_disposition
        if disposition["status"] in advisory_statuses
    }
    executable_secondaries: list[str] = []
    advisory_collaborators: list[str] = []
    for agent_slug in secondary_agents:
        if agent_slug in advisory_agents and agent_slug not in normalized_forced_executable_agents:
            advisory_collaborators.append(agent_slug)
        else:
            executable_secondaries.append(agent_slug)
    return executable_secondaries, advisory_collaborators


def _promote_forced_secondary_dispositions(
    *,
    requested_agent_disposition: list[dict[str, str]],
    forced_executable_agents: set[str],
) -> None:
    """Keep dispositions aligned with forced executable secondaries.

    RU: Если привилегированный review-path требует агента, он не должен
    оставаться review-only в packet-disposition metadata.
    EN: If the privileged review path requires an agent, it must not remain
    review-only in packet disposition metadata.
    """

    advisory_statuses = {
        REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
        REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
    }
    for disposition in requested_agent_disposition:
        if disposition["agent"] not in forced_executable_agents:
            continue
        if disposition["status"] not in advisory_statuses:
            continue
        if disposition["agent"] == "security-auditor":
            reason = (
                "Requested agent is required for the privileged review path and stays "
                "executable in secondary."
            )
        else:
            reason = (
                "Requested agent is required for the PR lifecycle review path and stays "
                "executable in secondary."
            )
        disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_SECONDARY
        disposition["reason"] = reason


def _append_missing_requested_role_passes(
    *,
    requested_agent_disposition: list[dict[str, str]],
    primary_agent: str,
    secondary_agents: list[str],
    reviewer: str,
) -> list[str]:
    """Ensure every known requested role is present in the executable plan."""

    ordered_secondary_agents = list(secondary_agents)
    planned_agents = {primary_agent, reviewer, *ordered_secondary_agents}
    for disposition in requested_agent_disposition:
        agent_slug = disposition["agent"]
        if disposition["status"] == REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN:
            continue
        if agent_slug in planned_agents:
            continue
        ordered_secondary_agents.append(agent_slug)
        planned_agents.add(agent_slug)
        if disposition["status"] == REQUESTED_AGENT_STATUS_HONORED_REVIEWER:
            disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_SECONDARY
            disposition["reason"] = (
                "Requested reviewer remains a required role pass after PR lifecycle synthesis."
            )
    return ordered_secondary_agents


def _apply_requested_agent_overrides(
    *,
    domain: str,
    primary_agent: str,
    secondary_agent: str | None,
    reviewer: str,
    requested_agents: list[str],
    routing: dict[str, Any],
) -> dict[str, Any]:
    """Apply explicit requested-agent overrides in a deterministic, bounded way."""

    inventory = load_inventory_agents()
    non_routable = load_non_routable_agents()
    canonical_route = routing.get(domain)

    resolved_primary = primary_agent
    resolved_secondary_agents = [agent for agent in [secondary_agent] if agent]
    dispositions: list[dict[str, str]] = []
    advisory_agents: list[str] = []
    coordinator_locked = (
        canonical_route is not None
        and canonical_route.primary == "agent-coordinator"
        and "agent-coordinator" in requested_agents
        and primary_agent == "agent-coordinator"
    )

    def _disposition(agent: str, status: str, reason: str) -> dict[str, str]:
        """Build a deterministic disposition payload for requested-agent handling."""

        return {"agent": agent, "status": status, "reason": reason}

    for agent in requested_agents:
        if agent not in inventory:
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN,
                    "Agent is not registered in the canonical inventory.",
                )
            )
            continue

        if agent == resolved_primary:
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_HONORED_PRIMARY,
                    "Requested agent already matches the routed primary.",
                )
            )
            continue

        allowed_promotions = {candidate for candidate in [secondary_agent, reviewer] if candidate}
        if canonical_route is not None:
            allowed_promotions.add(canonical_route.primary)
            if canonical_route.secondary:
                allowed_promotions.add(canonical_route.secondary)
            allowed_promotions.add(canonical_route.reviewer)

        # Graph slots take precedence over the non-routable specialist list: a specialist
        # may appear as secondary/reviewer in AGENT_ROUTING_GRAPH.md while still being
        # listed in AGENT_NON_ROUTABLE_SPECIALISTS.md for default routing semantics.
        if agent in allowed_promotions:
            if coordinator_locked and agent != "agent-coordinator":
                if agent == reviewer:
                    dispositions.append(
                        _disposition(
                            agent,
                            REQUESTED_AGENT_STATUS_HONORED_REVIEWER,
                            (
                                "Coordinator-owned lane keeps `agent-coordinator` as primary; "
                                "requested reviewer stays honored in reviewer."
                            ),
                        )
                    )
                    continue
                if agent not in resolved_secondary_agents:
                    resolved_secondary_agents.append(agent)
                dispositions.append(
                    _disposition(
                        agent,
                        REQUESTED_AGENT_STATUS_HONORED_SECONDARY,
                        (
                            "Coordinator-owned lane keeps `agent-coordinator` as primary; "
                            "requested agent stays honored in secondary."
                        ),
                    )
                )
                continue
            previous_primary = resolved_primary
            resolved_primary = agent
            resolved_secondary_agents = [
                candidate
                for candidate in [previous_primary, *resolved_secondary_agents]
                if candidate and candidate != resolved_primary
            ]
            reviewer = _select_independent_reviewer(
                primary_agent=resolved_primary,
                canonical_reviewer=canonical_route.reviewer if canonical_route else reviewer,
                canonical_secondary=(
                    canonical_route.secondary if canonical_route else secondary_agent
                ),
                previous_primary=previous_primary,
            )
            for disposition in dispositions:
                if (
                    disposition["agent"] == previous_primary
                    and disposition["status"] == REQUESTED_AGENT_STATUS_HONORED_PRIMARY
                ):
                    disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_SECONDARY
                    disposition["reason"] = (
                        "Requested agent stayed honored but moved to secondary after a later promotion."
                    )
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_PROMOTED,
                    "Requested agent is compatible with the routed domain and was promoted.",
                )
            )
            continue

        if agent in non_routable:
            if agent not in advisory_agents:
                advisory_agents.append(agent)
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
                    (
                        "Agent is canonical but non-routable; kept as a required "
                        "custom-role pass, not a skippable note."
                    ),
                )
            )
            continue

        if agent not in advisory_agents:
            advisory_agents.append(agent)
        dispositions.append(
            _disposition(
                agent,
                REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
                (
                    "Requested agent is outside the routed domain slot set; kept "
                    "as a required custom-role pass, not a skippable note."
                ),
            )
        )

    ordered_secondary_agents: list[str] = []
    for candidate in [*resolved_secondary_agents, *advisory_agents]:
        if (
            candidate
            and candidate != resolved_primary
            and candidate not in ordered_secondary_agents
        ):
            ordered_secondary_agents.append(candidate)

    return {
        "primary_agent": resolved_primary,
        "secondary_agents": ordered_secondary_agents,
        "reviewer": reviewer,
        "requested_agent_disposition": dispositions,
    }


def build_task_packet(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str],
    requested_agents: list[str] | tuple[str, ...] = (),
    invariant_change_classes: list[str] | tuple[str, ...] = (),
    review_invariant_family_relations_input: str | None = None,
    pr_phase: str = PR_PHASE_NONE,
    design_source: str | None = None,
    source_url: str | None = None,
    file_key_or_workspace: str | None = None,
    node_id_or_frame_id: str | None = None,
    target_surface: str | None = None,
    task_mode: str | None = None,
    figma_lane_tool: str | None = None,
    design_blockers: list[str] | tuple[str, ...] = (),
    code_native_design_brief_path: str | None = None,
    explicit_creation_mode: bool = False,
    native_bridge_transport: str = BRIDGE_TRANSPORT,
    telemetry_path: Path = TELEMETRY_PATH,
    creative_learning_hints_path: str | Path | None = None,
    creative_pilot_workspace_path: str | Path | None = None,
    creative_pilot_phase: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic task packet for orchestration tooling."""

    normalized_pr_phase = _normalize_pr_phase(pr_phase)
    family_repeat: dict[str, Any] | None = None
    if review_invariant_family_relations_input is not None:
        if normalized_pr_phase != PR_PHASE_POST_OPEN_REVIEW:
            raise ValueError(
                "--review-invariant-family-relations-input requires --pr-phase post_open_review"
            )
        family_repeat = _build_family_repeat_projection(
            _read_invariant_family_relations_input(review_invariant_family_relations_input)
        )
    invariant_review_decision = classify_invariant_review(
        candidate_paths=candidate_paths,
        explicit_classes=invariant_change_classes,
    )
    invariant_review_required_now = _invariant_review_required_now(
        invariant_review_decision,
        pr_phase=normalized_pr_phase,
    )
    if creative_pilot_workspace_path is not None and invariant_review_required_now:
        raise ValueError(
            "creative pilot dispatch cannot include a parser, validator, guard, "
            "or authority mechanism change; create a separate ordinary pre-open "
            "invariant-review packet without --creative-pilot-workspace"
        )
    normalized_paths = repo_relative_paths(
        [path.strip() for path in candidate_paths if path.strip()]
    )
    if native_bridge_transport not in NATIVE_BRIDGE_TRANSPORTS:
        supported = ", ".join(NATIVE_BRIDGE_TRANSPORTS)
        raise ValueError(
            "Unsupported native_bridge_transport: "
            f"{native_bridge_transport}. Supported: {supported}"
        )
    creative_pilot_workspace, creative_pilot_context = _read_creative_pilot_workspace(
        creative_pilot_workspace_path,
        creative_pilot_phase,
    )
    pilot_roles = (
        [row["role"] for row in creative_pilot_context["assignments"]]
        if creative_pilot_context is not None
        else []
    )
    normalized_requested_agents = normalize_requested_agents(
        pilot_roles if creative_pilot_context is not None else requested_agents
    )
    if creative_pilot_context is not None and normalized_pr_phase in {
        PR_PHASE_POST_OPEN_REVIEW,
        PR_PHASE_MERGE_READY,
    }:
        raise ValueError(
            "creative pilot dispatch cannot be combined with post-open or merge-ready PR phases"
        )
    creative_learning_hints = _read_creative_learning_hints(creative_learning_hints_path)
    creative_learning_hints_fingerprint = (
        fingerprint_payload(creative_learning_hints) if creative_learning_hints is not None else ""
    )
    creative_pilot_fingerprint = (
        fingerprint_payload(creative_pilot_context) if creative_pilot_context is not None else ""
    )
    design_lane_mode, design_lane_contract, design_lane_enabled = _build_design_lane_contract(
        design_source=design_source,
        source_url=source_url,
        file_key_or_workspace=file_key_or_workspace,
        node_id_or_frame_id=node_id_or_frame_id,
        target_surface=target_surface,
        task_mode=task_mode,
        figma_lane_tool=figma_lane_tool,
        design_blockers=design_blockers,
        code_native_design_brief_path=code_native_design_brief_path,
        explicit_creation_mode=explicit_creation_mode,
    )
    domain = resolve_domain(
        task_class=task_class,
        candidate_paths=normalized_paths,
        goal=goal,
    )
    routing = load_routing_graph()
    bootstrap_lane_activations = load_bootstrap_lane_activations()
    decision = route(
        domain,
        task_class,
        telemetry=_read_json(telemetry_path),
        routing=routing,
    )
    creative_identity_fingerprint = (
        creative_learning_hints_fingerprint
        if not creative_pilot_fingerprint
        else fingerprint_payload(
            {
                "creative_learning_hints": creative_learning_hints_fingerprint,
                "creative_pilot": creative_pilot_fingerprint,
            }
        )
    )
    invariant_review_packet = (
        _build_invariant_review_v2_packet(family_repeat)
        if family_repeat is not None
        else _build_invariant_review_packet(
            invariant_review_decision,
            required_now=invariant_review_required_now,
        )
    )
    base_packet_id = compute_task_packet_id(
        goal=goal,
        task_class=task_class,
        domain=decision.domain,
        candidate_paths=normalized_paths,
        requested_agents=normalized_requested_agents,
        pr_phase=normalized_pr_phase,
        design_fingerprint=_design_fingerprint(
            design_lane_mode=design_lane_mode,
            design_lane_contract=design_lane_contract,
        ),
        creative_learning_hints_fingerprint=creative_identity_fingerprint,
    )
    if family_repeat is not None:
        packet_id = compute_invariant_family_review_packet_id(
            goal=goal,
            task_class=task_class,
            domain=decision.domain,
            candidate_paths=normalized_paths,
            requested_agents=normalized_requested_agents,
            pr_phase=normalized_pr_phase,
            design_lane_mode=design_lane_mode,
            design_lane_contract=design_lane_contract,
            creative_learning_hints_fingerprint=creative_identity_fingerprint,
            artifact_fingerprint=str(family_repeat["artifact_fingerprint"]),
            invariant_review_projection=invariant_review_packet,
        )
    else:
        packet_id = _bind_invariant_review_packet_id(
            base_packet_id,
            invariant_review_fingerprint=invariant_review_decision.fingerprint,
        )
    context_pack = collect_context_pack(
        normalized_paths,
        include_orchestration=decision.cluster == "ops" or len(normalized_paths) != 1,
    )
    requested_agent_resolution = _apply_requested_agent_overrides(
        domain=decision.domain,
        primary_agent=decision.primary,
        secondary_agent=decision.secondary,
        reviewer=decision.reviewer,
        requested_agents=normalized_requested_agents,
        routing=routing,
    )
    security_review_required = bootstrap_requires_security_review(normalized_paths)
    if security_review_required:
        secondary_agents = list(requested_agent_resolution["secondary_agents"])
        security_in_review_path = "security-auditor" in {
            requested_agent_resolution["primary_agent"],
            requested_agent_resolution["reviewer"],
            *secondary_agents,
        }
        if not security_in_review_path:
            secondary_agents.append("security-auditor")
        requested_agent_resolution["secondary_agents"] = secondary_agents
    (
        lifecycle_primary_agent,
        lifecycle_secondary_agents,
        lifecycle_reviewer,
    ) = _apply_pr_lifecycle_review_path(
        pr_phase=normalized_pr_phase,
        primary_agent=requested_agent_resolution["primary_agent"],
        secondary_agents=requested_agent_resolution["secondary_agents"],
        reviewer=requested_agent_resolution["reviewer"],
    )
    requested_agent_resolution["primary_agent"] = lifecycle_primary_agent
    requested_agent_resolution["secondary_agents"] = _normalize_secondary_review_path(
        primary_agent=lifecycle_primary_agent,
        secondary_agents=lifecycle_secondary_agents,
        reviewer=lifecycle_reviewer,
    )
    requested_agent_resolution["reviewer"] = lifecycle_reviewer
    requested_agent_resolution["secondary_agents"] = _append_missing_requested_role_passes(
        requested_agent_disposition=requested_agent_resolution["requested_agent_disposition"],
        primary_agent=requested_agent_resolution["primary_agent"],
        secondary_agents=requested_agent_resolution["secondary_agents"],
        reviewer=requested_agent_resolution["reviewer"],
    )
    if invariant_review_required_now:
        requested_agent_resolution["secondary_agents"] = _append_system_invariant_review_roles(
            primary_agent=requested_agent_resolution["primary_agent"],
            secondary_agents=requested_agent_resolution["secondary_agents"],
            reviewer=requested_agent_resolution["reviewer"],
        )
    invariant_family_review_required = bool(
        family_repeat is not None and family_repeat["repeated_families"]
    )
    if invariant_family_review_required:
        extra_requested_agents = sorted(
            set(normalized_requested_agents).difference(INVARIANT_FAMILY_REVIEW_ROLE_ORDER)
        )
        if extra_requested_agents:
            raise ValueError(
                "active repeated-family review rejects extra requested agents: "
                + ", ".join(extra_requested_agents)
            )
        requested_agent_resolution = {
            "primary_agent": "agent-coordinator",
            "secondary_agents": [
                *INVARIANT_REVIEW_REQUIRED_ROLES,
                POST_OPEN_QA_AGENT,
                POST_OPEN_BUG_HUNTER_AGENT,
            ],
            "reviewer": "security-auditor",
            "requested_agent_disposition": [
                {
                    "agent": agent_slug,
                    "status": (
                        REQUESTED_AGENT_STATUS_HONORED_PRIMARY
                        if agent_slug == "agent-coordinator"
                        else (
                            REQUESTED_AGENT_STATUS_HONORED_REVIEWER
                            if agent_slug == "security-auditor"
                            else REQUESTED_AGENT_STATUS_HONORED_SECONDARY
                        )
                    ),
                    "reason": (
                        "Requested agent is retained in the exact bounded repeated-family "
                        "post-open role order."
                    ),
                }
                for agent_slug in normalized_requested_agents
            ],
        }
    if creative_pilot_context is not None:
        exact_roles = list(dict.fromkeys(pilot_roles))
        requested_agent_resolution = {
            "primary_agent": exact_roles[0],
            "secondary_agents": exact_roles[1:-1],
            "reviewer": exact_roles[-1],
            "requested_agent_disposition": [],
        }
    skill_routing = route_skills(
        goal=goal,
        task_class=task_class,
        candidate_paths=normalized_paths,
        domain=decision.domain,
        requested_agents=normalized_requested_agents,
        design_source=design_lane_contract["design_source"],
        source_url=design_lane_contract["source_url"],
        file_key_or_workspace=design_lane_contract["file_key_or_workspace"],
        node_id_or_frame_id=design_lane_contract["node_id_or_frame_id"],
        target_surface=design_lane_contract["target_surface"],
        task_mode="" if design_lane_mode == "disabled" else design_lane_mode,
        figma_lane_tool=design_lane_contract["figma_lane_tool"],
        code_native_design_brief_path=design_lane_contract["code_native_design_brief_path"],
        explicit_creation_mode=design_lane_contract["explicit_creation_mode"],
        design_lane_mode=design_lane_mode,
        design_blockers=design_lane_contract["blockers"],
    )
    recommended_skills = flatten_recommended_skills(skill_routing)
    learning_loop_semantic_triggers = [
        item
        for item in skill_routing.get("explanation", {}).get("semantic_groups", [])
        if item.get("group_id") == "orchestration.agent_learning_loop"
    ]
    learning_loop_required = "pulseplate-agent-learning-loop" in recommended_skills or bool(
        learning_loop_semantic_triggers
    )
    forced_executable_agents = {"security-auditor"} if security_review_required else set()
    if invariant_review_required_now:
        forced_executable_agents.update(
            {
                "agent-coordinator",
                *INVARIANT_REVIEW_REQUIRED_ROLES,
            }
        )
    if invariant_family_review_required:
        forced_executable_agents.update(INVARIANT_FAMILY_REVIEW_ROLE_ORDER)
    if normalized_pr_phase == PR_PHASE_POST_OPEN_REVIEW:
        forced_executable_agents.update(POST_OPEN_REVIEW_LANE)
    if forced_executable_agents:
        _promote_forced_secondary_dispositions(
            requested_agent_disposition=requested_agent_resolution["requested_agent_disposition"],
            forced_executable_agents=forced_executable_agents,
        )
    if normalized_pr_phase != PR_PHASE_NONE:
        _reconcile_requested_agent_dispositions(
            requested_agent_disposition=requested_agent_resolution["requested_agent_disposition"],
            primary_agent=requested_agent_resolution["primary_agent"],
            secondary_agents=requested_agent_resolution["secondary_agents"],
            reviewer=requested_agent_resolution["reviewer"],
        )
    executable_secondaries, advisory_agents = partition_native_secondaries(
        secondary_agents=requested_agent_resolution["secondary_agents"],
        requested_agent_disposition=requested_agent_resolution["requested_agent_disposition"],
        forced_executable_agents=forced_executable_agents,
    )
    native_subagent_bridge = build_native_subagent_bridge(
        primary_agent=requested_agent_resolution["primary_agent"],
        secondary_agents=executable_secondaries,
        reviewer=requested_agent_resolution["reviewer"],
        advisory_agents=advisory_agents,
        transport=native_bridge_transport,
    )
    invariant_dispatch_role_order = None
    if invariant_review_required_now:
        invariant_dispatch_role_order = _build_invariant_dispatch_role_order(native_subagent_bridge)
    elif invariant_family_review_required:
        invariant_dispatch_role_order = list(INVARIANT_FAMILY_REVIEW_ROLE_ORDER)
    judgment_activation = _validated_judgment_activation(
        require_bootstrap_lane_activation(
            bootstrap_lane_activations,
            REQUIRED_BOOTSTRAP_LANE,
        )
    )
    judgment_enabled = _judgment_lane_enabled(
        goal=goal,
        task_class=task_class,
        candidate_paths=normalized_paths,
        activation=judgment_activation,
    )
    needs_backlog_update = bootstrap_needs_backlog_update(
        goal=goal,
        task_class=task_class,
        candidate_paths=normalized_paths,
    )
    needs_docs_sync = bootstrap_needs_docs_sync(normalized_paths)
    needs_agents_sync = bootstrap_needs_agents_sync(normalized_paths)
    envelope_mode_hint = resolve_analysis_envelope_mode(normalized_paths)
    message_envelope = {
        "protocol_version": MESSAGE_ENVELOPE_PROTOCOL_VERSION,
        "derived_view": MESSAGE_ENVELOPE_DERIVED_VIEW,
        "mode": (
            "docs-only" if envelope_mode_hint == DOCS_ONLY_ENVELOPE_MODE else envelope_mode_hint
        ),
        "output_requirements": {
            "must_return": [ENVELOPE_ONLY_RESULT_REQUIREMENT],
        },
    }
    pr_lifecycle_contract = _build_pr_lifecycle_contract(normalized_pr_phase)
    if judgment_enabled:
        context_pack = sorted(set(context_pack).union(JUDGMENT_REQUIRED_CONTEXT_FILES))
        decision_contract = {
            "mode": judgment_activation.decision_mode,
            "judgment_enabled": True,
            "claim_taxonomy": list(CLAIM_TYPES),
            "flow": list(JUDGMENT_FLOW),
        }
        judgment_budget = dict(
            [
                ("skeptic_pass_required", True),
                ("verifier_pass_required", True),
                ("max_provider_calls", 0),
                ("uncertainty_split_required", True),
            ]
        )
        result_adjudication = {
            "claim_evidence_fields": list(CLAIM_EVIDENCE_FIELDS),
            "support_statuses": list(SUPPORT_STATUSES),
            "evidence_modes": list(EVIDENCE_MODES),
            "uncertainty_fields": list(UNCERTAINTY_FIELDS),
            "promotion_labels": list(PROMOTION_LABELS),
        }
    else:
        decision_contract = {
            "mode": "standard",
            "judgment_enabled": False,
            "claim_taxonomy": [],
            "flow": [],
        }
        judgment_budget = dict(
            [
                ("skeptic_pass_required", False),
                ("verifier_pass_required", False),
                ("max_provider_calls", 0),
                ("uncertainty_split_required", False),
            ]
        )
        result_adjudication = {
            "claim_evidence_fields": [],
            "support_statuses": [],
            "evidence_modes": [],
            "uncertainty_fields": [],
            "promotion_labels": [],
        }

    context_pack_compression = build_context_pack_compression(
        candidate_paths=normalized_paths,
        required_context=context_pack,
        pr_phase=normalized_pr_phase,
        domain=decision.domain,
        cluster=decision.cluster,
        primary_agent=requested_agent_resolution["primary_agent"],
        reviewer=requested_agent_resolution["reviewer"],
        secondary_agents=requested_agent_resolution["secondary_agents"],
        requested_agents=normalized_requested_agents,
        orchestration_fanout_multiplier=max(
            1,
            len(
                {
                    requested_agent_resolution["primary_agent"],
                    requested_agent_resolution["reviewer"],
                    *requested_agent_resolution["secondary_agents"],
                }
            ),
        ),
    )
    provider_model_tier_routing = build_provider_model_routing_telemetry(
        requested_agents=normalized_requested_agents,
        primary_agent=requested_agent_resolution["primary_agent"],
        reviewer=requested_agent_resolution["reviewer"],
        secondary_agents=requested_agent_resolution["secondary_agents"],
    )
    embedding_retrieval_admission = build_embedding_retrieval_admission_telemetry(
        candidate_paths=normalized_paths,
        required_context=context_pack,
        pr_phase=normalized_pr_phase,
        domain=decision.domain,
        cluster=decision.cluster,
    )

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_packet_id": packet_id,
        "goal": goal.strip(),
        "task_class": task_class.strip(),
        "domain": decision.domain,
        "cluster": decision.cluster,
        "candidate_paths": normalized_paths,
        "primary_agent": requested_agent_resolution["primary_agent"],
        "secondary_agents": requested_agent_resolution["secondary_agents"],
        "reviewer": requested_agent_resolution["reviewer"],
        "requested_agents": normalized_requested_agents,
        "requested_agent_disposition": requested_agent_resolution["requested_agent_disposition"],
        "invariant_review": invariant_review_packet,
        "required_context": context_pack,
        "context_pack_compression": dict(
            context_compression_to_stable_mapping(context_pack_compression)
        ),
        "provider_model_tier_routing": dict(
            provider_model_routing_to_stable_mapping(provider_model_tier_routing)
        ),
        "embedding_retrieval_admission": dict(
            embedding_retrieval_admission_to_stable_mapping(embedding_retrieval_admission)
        ),
        "review_pattern_oracles": {
            "schema_version": "review_pattern_oracles.v1",
            "helper": "scripts/orchestration/review_pattern_oracles.py",
            "contract": "docs/orchestration/contracts/review_pattern_oracles.v1.json",
            "compact_ids": [
                "schema_validator_parity",
                "fail_closed_security_edge",
                "deterministic_content_oracle",
                "canonical_route_ownership_guard",
                "evidence_hygiene_mapping_timing",
                "review_source_degraded",
            ],
            "authority_boundary": "proposal_only_non_canonical",
            "side_effects_allowed": False,
            "posting_allowed": False,
            "thread_resolution_allowed": False,
            "merge_readiness_authority": False,
        },
        "review_source_degradation_policy": {
            "schema_version": "review_source_status.v1",
            "helper": "scripts/orchestration/review_source_status.py",
            "contract": "docs/orchestration/contracts/review_source_status.v1.json",
            "source_degraded_is_blocking": False,
            "side_effects_allowed": False,
            "posting_allowed": False,
            "thread_resolution_allowed": False,
            "merge_readiness_authority": False,
        },
        "agent_learning_loop": {
            "schema_version": "agent_learning_record.v1",
            "extractor": "scripts/orchestration/agent_lesson_extractor.py",
            "promoter": "scripts/orchestration/agent_lesson_promoter.py",
            "contract": "docs/orchestration/contracts/agent_learning_record.v1.json",
            "orchestration_gate": "conditional_required_when_triggered",
            "current_packet_required": learning_loop_required,
            "trigger_evidence": learning_loop_semantic_triggers,
            "required_when": [
                "operator_explicitly_requests_learning_loop",
                "repeated_role_agent_failure_mode",
                "repeated_premortem_failure_or_docs_closeout",
                "repeated_review_failure_or_missed_actionable",
                "repeated_successful_iteration_pattern",
            ],
            "current_pr_enforcement_required_when_scope_affected": True,
            "proposal_only_until_promoted": True,
            "redaction_required": True,
            "promotion_requires_reviewed_repo_diff": True,
            "metrics_required": True,
            "metrics_schema_version": "agent_learning_metrics.v1",
            "metric_ids": [
                "agent_iteration_quality",
                "business_risk_clarity",
                "premortem_code_closure_rate",
                "project_development_signal",
                "repeat_failure_reduction",
                "review_actionable_escape_reduction",
                "successful_pattern_reuse",
                "user_impact_clarity",
            ],
            "authority_boundary": "proposal_only_non_runtime",
            "side_effects_allowed": False,
            "runtime_authority": False,
            "canonical_until_promoted_by_repo_diff": False,
        },
        "creative_learning_hints": _build_creative_learning_hints_packet(
            creative_learning_hints,
            hints_fingerprint=creative_learning_hints_fingerprint,
        ),
        "message_envelope": message_envelope,
        "recommended_skills": recommended_skills,
        "skill_routing": skill_routing,
        "automation_flags": {
            "coordinator_first_required": True,
            "skill_routing_applied": True,
            "native_subagent_bridge_available": True,
            "security_review_required": security_review_required,
            "invariant_class_review_required": (
                invariant_review_required_now or invariant_family_review_required
            ),
            "judgment_lane_enabled": judgment_enabled,
            "pr_lifecycle_enabled": normalized_pr_phase != PR_PHASE_NONE,
            "design_lane_enabled": design_lane_enabled,
        },
        "role_agent_dispatch_contract": build_role_agent_dispatch_contract(
            native_subagent_bridge=native_subagent_bridge,
            pr_phase=normalized_pr_phase,
            dispatch_role_order=invariant_dispatch_role_order,
        ),
        "pr_phase": normalized_pr_phase,
        "pr_lifecycle_contract": pr_lifecycle_contract,
        "design_lane_mode": design_lane_mode,
        "design_lane_contract": design_lane_contract,
        "needs_backlog_update": needs_backlog_update,
        "needs_docs_sync": needs_docs_sync,
        "needs_agents_sync": needs_agents_sync,
        "decision_contract": decision_contract,
        "judgment_budget": judgment_budget,
        "result_adjudication": result_adjudication,
        "native_subagent_bridge": native_subagent_bridge,
        "routing_rationale": decision.rationale,
    }
    if creative_pilot_context is not None:
        packet["creative_pilot_context"] = creative_pilot_context
        packet["automation_flags"]["creative_pilot_enabled"] = True
        packet["creative_pilot_workspace_source"] = str(
            Path(cast(str | Path, creative_pilot_workspace_path)).as_posix()
        )
    return packet


def _resolve_output_path(raw_output: str | None, packet_id: str) -> Path:
    """Resolve output path relative to repo root and reject out-of-repo writes."""

    if not raw_output:
        return (TASK_PACKET_DIR / f"{packet_id}.json").resolve()

    candidate = Path(raw_output)
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("--output must stay within the repository root") from exc
    return candidate


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="task_bootstrap",
        description="Build deterministic coordinator task packet artifact.",
    )
    parser.add_argument("--goal", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument(
        "--requested-agent",
        action="append",
        default=[],
        help="Optional requested agent slug. May be repeated.",
    )
    parser.add_argument(
        "--invariant-change-class",
        action="append",
        choices=INVARIANT_CHANGE_CLASSES,
        default=[],
        help=("Explicit parser/validator/guard/authority mechanism class. May be repeated."),
    )
    parser.add_argument(
        "--review-invariant-family-relations-input",
        default=None,
        help=(
            "Optional canonical L1 JSON direct child under "
            "artifacts/orchestration/review_invariant_family_relations/."
        ),
    )
    parser.add_argument(
        "--pr-phase",
        default=PR_PHASE_NONE,
        choices=PR_PHASES,
        help="Optional PR lifecycle phase for deterministic review-lane synthesis.",
    )
    parser.add_argument("--telemetry", default=str(TELEMETRY_PATH))
    parser.add_argument(
        "--native-bridge-transport",
        default=BRIDGE_TRANSPORT,
        choices=NATIVE_BRIDGE_TRANSPORTS,
        help="Native subagent bridge transport label for runtime-specific packets.",
    )
    parser.add_argument(
        "--creative-learning-hints",
        default=None,
        help=(
            "Optional coordinator advisory hints JSON under "
            "artifacts/orchestration/creative_code/learning_rollup."
        ),
    )
    parser.add_argument(
        "--creative-pilot-workspace",
        default=None,
        help="Optional validated workspace JSON under adaptive_pilots.",
    )
    parser.add_argument(
        "--creative-pilot-phase",
        choices=CREATIVE_PILOT_PHASES,
        default=None,
        help="Explicit creative-pilot role phase bound into the task packet.",
    )
    parser.add_argument(
        "--design-source",
        choices=DESIGN_SOURCES,
        default=None,
        help="Optional design lane source selector.",
    )
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--file-key-or-workspace", default=None)
    parser.add_argument("--node-id-or-frame-id", default=None)
    parser.add_argument("--target-surface", default=None)
    parser.add_argument(
        "--task-mode",
        choices=DESIGN_TASK_MODES,
        default=None,
        help="Optional design lane task mode.",
    )
    parser.add_argument(
        "--figma-lane-tool",
        choices=FIGMA_LANE_TOOLS,
        default=None,
        help="Optional Figma lane tool when a Figma source is selected.",
    )
    parser.add_argument(
        "--design-blocker",
        action="append",
        choices=DESIGN_BLOCKERS,
        default=[],
        help="Optional explicit design blocker. May be repeated.",
    )
    parser.add_argument("--code-native-design-brief-path", default=None)
    parser.add_argument(
        "--explicit-creation-mode",
        action="store_true",
        help="Allow explicit creation-mode activation without an existing Figma URL/node id.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Defaults to artifacts/orchestration/task_packets/<id>.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        packet = build_task_packet(
            goal=args.goal,
            task_class=args.task_class,
            candidate_paths=args.path,
            requested_agents=args.requested_agent,
            invariant_change_classes=args.invariant_change_class,
            review_invariant_family_relations_input=(args.review_invariant_family_relations_input),
            pr_phase=args.pr_phase,
            design_source=args.design_source,
            source_url=args.source_url,
            file_key_or_workspace=args.file_key_or_workspace,
            node_id_or_frame_id=args.node_id_or_frame_id,
            target_surface=args.target_surface,
            task_mode=args.task_mode,
            figma_lane_tool=args.figma_lane_tool,
            design_blockers=args.design_blocker,
            code_native_design_brief_path=args.code_native_design_brief_path,
            explicit_creation_mode=args.explicit_creation_mode,
            native_bridge_transport=args.native_bridge_transport,
            telemetry_path=Path(args.telemetry),
            creative_learning_hints_path=args.creative_learning_hints,
            creative_pilot_workspace_path=args.creative_pilot_workspace,
            creative_pilot_phase=args.creative_pilot_phase,
        )
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    if not isinstance(packet.get("creative_learning_hints"), dict):
        packet["creative_learning_hints"] = _build_creative_learning_hints_packet(
            None,
            hints_fingerprint="",
        )
    try:
        out_path = _resolve_output_path(args.output, packet["task_packet_id"])
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    previous_packets, artifact_scan = collect_previous_task_packet_candidates(
        task_packet_dir=TASK_PACKET_DIR,
        priority_packet_path=out_path,
    )
    packet[SHADOW_REUSE_FIELD] = build_shadow_reuse_telemetry(
        packet=packet,
        current_head_sha=resolve_current_head_sha(REPO_ROOT),
        previous_packets=previous_packets,
        artifact_scan=artifact_scan,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        output_ref = str(out_path.relative_to(REPO_ROOT))
    except ValueError:
        output_ref = str(out_path)
    role_dispatch_contract = packet.get("role_agent_dispatch_contract")
    if not isinstance(role_dispatch_contract, dict):
        role_dispatch_contract = build_role_agent_dispatch_contract(
            native_subagent_bridge=packet.get("native_subagent_bridge"),
            pr_phase=str(packet.get("pr_phase", PR_PHASE_NONE)),
        )
    print(
        json.dumps(
            {
                "task_packet_id": packet["task_packet_id"],
                "domain": packet["domain"],
                "cluster": packet["cluster"],
                "primary_agent": packet["primary_agent"],
                "reviewer": packet["reviewer"],
                "requested_agents": packet["requested_agents"],
                "recommended_skills": packet["recommended_skills"],
                "creative_learning_hints_fingerprint": packet["creative_learning_hints"][
                    "source_hints_fingerprint"
                ],
                "primary_native_agent_type": packet["native_subagent_bridge"]["primary"][
                    "native_agent_type"
                ],
                "reviewer_native_agent_type": packet["native_subagent_bridge"]["reviewer"][
                    "native_agent_type"
                ],
                "packet_creation_executes_roles": role_dispatch_contract[
                    "packet_creation_executes_roles"
                ],
                "role_agent_dispatch_required": role_dispatch_contract[
                    "role_agent_dispatch_required"
                ],
                "dispatch_manifest_entrypoint": role_dispatch_contract[
                    "dispatch_manifest_entrypoint"
                ],
                "output": output_ref,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

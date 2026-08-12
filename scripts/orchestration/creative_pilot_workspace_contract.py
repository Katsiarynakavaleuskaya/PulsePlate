"""Fail-closed contracts for adaptive production-adjacent creative pilots.

This module is a v2 planning rail.  It intentionally does not relax the v1
creative-context contracts and never grants patch, provider, runtime, cache,
graph, or repository-write authority.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess  # nosec B404: bounded Git object reads require subprocess (remove-by: 2026-09-30, ref: ledger-p1-agent-experimentation-lane)
from typing import Any, cast

from core.evidence.events import EvidenceEvalEvent, create_eval_event
from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration.experiment_contract import validate_mutable_candidate_surface
from scripts.orchestration.creative_code_specification import (
    EXACT_VARIANT_DECLARATION_KEYS,
    CreativeCodeSpecificationError,
    build_exact_specification_variants,
    validate_source_candidate_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "2.0"
POLICY_VERSION = "creative-production-adjacent-pilot-v2"
SURFACE_POLICY = "production_adjacent_pilot"
CONTEXT_TYPE = "creative_protocol_context_map"
HYPOTHESIS_PACKET_TYPE = "creative_hypothesis_packet"
APPROVAL_TYPE = "creative_hypothesis_approval"
WORKSPACE_TYPE = "creative_pilot_workspace"
ROLE_RESULT_TYPE = "creative_pilot_role_result"
SYNTHESIS_TYPE = "creative_pilot_synthesis"
BRIDGE_TYPE = "creative_hypothesis_specification_bridge"
ADAPTIVE_PR1_INTAKE_TYPE = "creative_adaptive_pr1_variant_intake"
ADAPTIVE_PR1_RESUME_TYPE = "creative_adaptive_pr1_resume_binding"
ADAPTIVE_PR1_SCHEMA_VERSION = "1.0"
ADAPTIVE_PR1_POLICY_VERSION = "creative-adaptive-pr1-resume-v1"
ADAPTIVE_PR1_SOURCE_TYPES = {
    "context_map.v2.json": CONTEXT_TYPE,
    "hypothesis_packet.v2.json": HYPOTHESIS_PACKET_TYPE,
    "workspace.json": WORKSPACE_TYPE,
    "synthesis.json": SYNTHESIS_TYPE,
    "approval.v2.json": APPROVAL_TYPE,
    "spec_bridge.v2.json": BRIDGE_TYPE,
    "creative_code_candidate.v1.json": "creative_code_candidate",
}
ADAPTIVE_PR1_PREPARE_FILENAMES = (
    "source_packet.json",
    "variants.json",
    "skeptic_reviews.json",
    "context_pack.json",
)
INDEPENDENT_FIRST_PASS_ENABLED = True

ALLOWED_TARGET_PREFIXES = ("core/rag/", "core/insight/")
REQUIRED_ROLES = (
    "architecture-specialist",
    "qa-engineer-agent",
    "security-auditor",
)
ROLE_QUESTIONS: dict[str, str] = {
    "architecture-specialist": "Can the specification stay within the exact target and preserve existing architecture contracts?",
    "qa-engineer-agent": "Can the immutable oracle plan falsify the proposed behavior without requiring a generated diff at this stage?",
    "security-auditor": "Does the specification preserve fail-closed authority and avoid new trust or data boundaries?",
    "epistemology-discovery-agent": "Is the hypothesis evidence-bound, falsifiable, and free of claims stronger than its oracle plan?",
    "bug-hunter": "Which specified failure modes or negative controls remain uncovered before patch generation?",
    "data-scientist-agent": "Does the specification preserve metric semantics and define sufficient later evaluation evidence?",
    "prompt-engineering-eval-agent": "Does the specification preserve prompt and output behavior under declared negative controls?",
}
CONDITIONAL_ROLE_RULES: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"evidence", "provenance", "verification"}), "epistemology-discovery-agent"),
    (frozenset({"failure", "degraded", "fallback"}), "bug-hunter"),
    (frozenset({"confidence", "ranking", "statistics"}), "data-scientist-agent"),
    (frozenset({"prompt", "output", "language"}), "prompt-engineering-eval-agent"),
)
PHASES = frozenset(
    {
        "created",
        "target_bound",
        "independent_dispatched",
        "independent_complete",
        "rebuttal_required",
        "synthesis_ready",
        "rebuttal_complete",
        "synthesized",
        "approved_for_pr1_spec",
        "revise",
        "reject",
        "blocked",
    }
)
TERMINAL_PHASES = frozenset({"approved_for_pr1_spec", "revise", "reject", "blocked"})
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "independent_dispatched": frozenset({"independent_dispatched", "independent_complete"}),
    "independent_complete": frozenset({"rebuttal_required", "synthesis_ready"}),
    "rebuttal_required": frozenset(
        {"rebuttal_required", "rebuttal_complete", "blocked", "revise", "reject"}
    ),
    "rebuttal_complete": frozenset({"synthesis_ready"}),
    "synthesis_ready": frozenset({"synthesized", "revise", "reject", "blocked"}),
    "synthesized": frozenset({"approved_for_pr1_spec", "revise", "reject", "blocked"}),
}
ROLE_PHASES = frozenset({"independent", "rebuttal"})
STANCES = frozenset({"pass", "revise", "reject", "abstain"})
EVIDENCE_SUFFICIENCY = frozenset({"complete", "partial", "insufficient"})
DISAGREEMENT_CLASSES = frozenset({"none", "bounded", "material"})
DECISIONS = frozenset({"approve", "revise", "reject", "hold"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
FORBIDDEN_TEXT_RE = re.compile(
    r"(raw[_ -]?(prompt|response|reasoning|patch)|chain[_ -]?of[_ -]?thought|"
    r"pull request body|review body|github comment|bearer\s+|sk-[A-Za-z0-9])",
    re.IGNORECASE,
)
SECRET_TEXT_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |candidate\.patch|candidate_patch|"
    r"candidate[_. -]?patch|raw[_. -]?(model[_. -]?payload|"
    r"body|prompt|response|context|patch|review|pr)|"
    r"review[_. -]?thread[_. -]?body|pull[_. -]?request[_. -]?body|"
    r"chain[_. -]?of[_. -]?thought|provider[_. -]?payload|"
    r"oracle[_. -]?(stdout|stderr|output)|file://|"
    r"/(?:Users|home|private/var|var/folders|tmp|etc|opt|usr|Volumes|mnt|root|"
    r"workspace|workspaces)(?:/|$)|~[/\\]|[A-Za-z]:[\\/]|\.venv/|\.git/|"
    r"worktrees([:/._-]|$)|merge[-_ ]?ready|ready to merge|mergeable)",
    re.IGNORECASE | re.MULTILINE,
)

AUTHORITY = {
    "bind_planning_target": True,
    "emit_role_assignments": True,
    "ingest_structured_role_results": True,
    "emit_synthesis": True,
    "call_provider": False,
    "generate_patch": False,
    "write_runtime": False,
    "write_repository": False,
    "open_pr": False,
    "push": False,
    "merge": False,
    "use_semantic_cache": False,
    "write_graph_truth": False,
    "modify_workflows": False,
}

ADAPTIVE_PR1_AUTHORITY = {
    "read_sanitized_context": True,
    "emit_local_artifacts": True,
    "run_specification_prepare": True,
    "call_product_runtime": False,
    "call_provider": False,
    "change_openapi": False,
    "claim_merge_readiness": False,
    "create_branch": False,
    "dispatch_to_agents": False,
    "execute_pr2_patch_builder": False,
    "execute_pr3_promotion": False,
    "finalize_specification_bundle": False,
    "generate_candidate_patch": False,
    "generate_patch": False,
    "merge": False,
    "modify_workflows": False,
    "open_pr": False,
    "push": False,
    "read_secrets": False,
    "resolve_threads": False,
    "use_semantic_cache": False,
    "write_branch": False,
    "write_graph_truth": False,
    "write_repository": False,
    "write_shared_worktree": False,
}


class CreativePilotContractError(ValueError):
    """Raised when adaptive-pilot input violates the planning boundary."""


def _adaptive_identity(
    body: Mapping[str, Any], *, artifact_type: str, upstream_ids: Sequence[str]
) -> tuple[str, str]:
    fingerprint = fingerprint_payload(dict(body))
    return (
        build_asset_id(
            asset_type=artifact_type,
            rail="orchestration",
            version=ADAPTIVE_PR1_SCHEMA_VERSION,
            policy_version=ADAPTIVE_PR1_POLICY_VERSION,
            fingerprint=fingerprint,
            upstream_ids=tuple(upstream_ids),
        ),
        build_idempotency_key(
            asset_type=artifact_type,
            rail="orchestration",
            version=ADAPTIVE_PR1_SCHEMA_VERSION,
            policy_version=ADAPTIVE_PR1_POLICY_VERSION,
            fingerprint=fingerprint,
            upstream_ids=tuple(upstream_ids),
        ),
    )


def _adaptive_authority(value: Any, label: str) -> dict[str, bool]:
    if not isinstance(value, Mapping) or dict(value) != ADAPTIVE_PR1_AUTHORITY:
        raise CreativePilotContractError(f"{label} authority boundary mismatch")
    return dict(ADAPTIVE_PR1_AUTHORITY)


def _artifact_ref(value: Any, label: str, *, filename: str | None = None) -> str:
    ref = _path(value, label)
    if not ref.startswith("artifacts/orchestration/creative_code/"):
        raise CreativePilotContractError(f"{label} must stay under creative-code artifacts")
    if filename is not None and PurePosixPath(ref).name != filename:
        raise CreativePilotContractError(f"{label} must name {filename}")
    return ref


def _validate_identity_fields(
    normalized: Mapping[str, Any], *, id_key: str, artifact_type: str, upstream_ids: Sequence[str]
) -> None:
    excluded = {id_key, "idempotency_key"}
    if artifact_type == ADAPTIVE_PR1_RESUME_TYPE:
        excluded.add("bridge_id")
    body = {key: value for key, value in normalized.items() if key not in excluded}
    expected_id, expected_idempotency = _adaptive_identity(
        body, artifact_type=artifact_type, upstream_ids=upstream_ids
    )
    if normalized[id_key] != expected_id or normalized["idempotency_key"] != expected_idempotency:
        raise CreativePilotContractError(f"{artifact_type} identity mismatch")


def build_adaptive_pr1_variant_intake(
    *,
    pilot_id: str,
    candidate: Mapping[str, Any],
    candidate_ref: str,
    declarations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the exact, deterministic adaptive PR-1 variant intake."""

    pilot = _token(pilot_id, "pilot_id")
    try:
        normalized_candidate = validate_source_candidate_packet(candidate)
        variants = build_exact_specification_variants(normalized_candidate, declarations)
    except CreativeCodeSpecificationError as exc:
        raise CreativePilotContractError(f"adaptive_invalid_declaration: {exc}") from exc
    ordered_declarations = [
        {key: variant[key] for key in sorted(EXACT_VARIANT_DECLARATION_KEYS)}
        for variant in variants
    ]
    body: dict[str, Any] = {
        "schema_version": ADAPTIVE_PR1_SCHEMA_VERSION,
        "artifact_type": ADAPTIVE_PR1_INTAKE_TYPE,
        "policy_version": ADAPTIVE_PR1_POLICY_VERSION,
        "pilot_id": pilot,
        "source_candidate": {
            "candidate_id": normalized_candidate["candidate_id"],
            "candidate_ref": _artifact_ref(
                candidate_ref,
                "source_candidate.candidate_ref",
                filename="creative_code_candidate.v1.json",
            ),
            "candidate_fingerprint": fingerprint_payload(dict(normalized_candidate)),
        },
        "target_surface": list(normalized_candidate["target_surface"]),
        "required_tests": list(normalized_candidate["evidence_bundle"]["required_tests"]),
        "declarations": ordered_declarations,
        "materialized_variants": variants,
        "equality_proof": {
            "approach_families": [row["approach_family"] for row in variants],
            "declarations_fingerprint": fingerprint_payload(ordered_declarations),
            "materialized_variants_fingerprint": fingerprint_payload(variants),
            "declaration_count": len(ordered_declarations),
            "variant_count": len(variants),
            "equal_count": len(ordered_declarations) == len(variants),
        },
        "authority": dict(ADAPTIVE_PR1_AUTHORITY),
        "sanitized": True,
    }
    intake_id, idempotency_key = _adaptive_identity(
        body,
        artifact_type=ADAPTIVE_PR1_INTAKE_TYPE,
        upstream_ids=(str(normalized_candidate["candidate_id"]),),
    )
    return validate_adaptive_pr1_variant_intake(
        {**body, "intake_id": intake_id, "idempotency_key": idempotency_key},
        candidate=normalized_candidate,
    )


def validate_adaptive_pr1_variant_intake(
    payload: Mapping[str, Any], *, candidate: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate a closed CreativeAdaptivePr1VariantIntakeV1 artifact."""

    _exact_keys(
        payload,
        {
            "schema_version",
            "artifact_type",
            "intake_id",
            "idempotency_key",
            "policy_version",
            "pilot_id",
            "source_candidate",
            "target_surface",
            "required_tests",
            "declarations",
            "materialized_variants",
            "equality_proof",
            "authority",
            "sanitized",
        },
        "CreativeAdaptivePr1VariantIntakeV1",
    )
    if (
        payload["schema_version"] != ADAPTIVE_PR1_SCHEMA_VERSION
        or payload["artifact_type"] != ADAPTIVE_PR1_INTAKE_TYPE
    ):
        raise CreativePilotContractError("adaptive intake version or artifact_type mismatch")
    if payload["policy_version"] != ADAPTIVE_PR1_POLICY_VERSION or payload["sanitized"] is not True:
        raise CreativePilotContractError("adaptive intake policy or sanitization mismatch")
    normalized_candidate = validate_source_candidate_packet(candidate)
    source = payload["source_candidate"]
    if not isinstance(source, Mapping):
        raise CreativePilotContractError("adaptive intake source_candidate must be an object")
    _exact_keys(
        source, {"candidate_id", "candidate_ref", "candidate_fingerprint"}, "source_candidate"
    )
    normalized_source = {
        "candidate_id": _token(source["candidate_id"], "source_candidate.candidate_id"),
        "candidate_ref": _artifact_ref(
            source["candidate_ref"],
            "source_candidate.candidate_ref",
            filename="creative_code_candidate.v1.json",
        ),
        "candidate_fingerprint": _fingerprint(
            source["candidate_fingerprint"], "source_candidate.candidate_fingerprint"
        ),
    }
    if normalized_source["candidate_id"] != normalized_candidate[
        "candidate_id"
    ] or normalized_source["candidate_fingerprint"] != fingerprint_payload(
        dict(normalized_candidate)
    ):
        raise CreativePilotContractError("adaptive_source_fingerprint_mismatch: candidate")
    declarations = payload["declarations"]
    if not isinstance(declarations, list) or not all(
        isinstance(row, Mapping) for row in declarations
    ):
        raise CreativePilotContractError("adaptive intake declarations must be objects")
    try:
        expected_variants = build_exact_specification_variants(
            normalized_candidate, cast(Sequence[Mapping[str, Any]], declarations)
        )
    except CreativeCodeSpecificationError as exc:
        raise CreativePilotContractError(f"adaptive_invalid_declaration: {exc}") from exc
    if payload["materialized_variants"] != expected_variants:
        raise CreativePilotContractError("adaptive intake materialized variants mismatch")
    expected_declarations = [
        {key: row[key] for key in sorted(EXACT_VARIANT_DECLARATION_KEYS)}
        for row in expected_variants
    ]
    if declarations != expected_declarations:
        raise CreativePilotContractError("adaptive intake declaration order mismatch")
    if (
        payload["target_surface"] != normalized_candidate["target_surface"]
        or payload["required_tests"] != normalized_candidate["evidence_bundle"]["required_tests"]
    ):
        raise CreativePilotContractError("adaptive intake target or required test binding mismatch")
    expected_proof = {
        "approach_families": [row["approach_family"] for row in expected_variants],
        "declarations_fingerprint": fingerprint_payload(expected_declarations),
        "materialized_variants_fingerprint": fingerprint_payload(expected_variants),
        "declaration_count": len(expected_declarations),
        "variant_count": len(expected_variants),
        "equal_count": True,
    }
    if payload["equality_proof"] != expected_proof:
        raise CreativePilotContractError("adaptive intake equality proof mismatch")
    normalized = dict(payload)
    normalized["pilot_id"] = _token(payload["pilot_id"], "pilot_id")
    normalized["source_candidate"] = normalized_source
    normalized["authority"] = _adaptive_authority(payload["authority"], "adaptive intake")
    _validate_identity_fields(
        normalized,
        id_key="intake_id",
        artifact_type=ADAPTIVE_PR1_INTAKE_TYPE,
        upstream_ids=(str(normalized_candidate["candidate_id"]),),
    )
    return normalized


def build_adaptive_pr1_resume_binding(
    *,
    pilot_id: str,
    intake: Mapping[str, Any],
    intake_ref: str,
    candidate: Mapping[str, Any],
    candidate_ref: str,
    source_artifacts: Sequence[Mapping[str, Any]],
    original_prepare_bindings: Sequence[Mapping[str, Any]],
    old_target_manifest: Mapping[str, Any],
    current_target_manifest: Mapping[str, Any],
    spec_prepare_ref: str,
) -> dict[str, Any]:
    """Build a replay-safe binding from retained adaptive evidence to exact PR-1."""

    normalized_candidate = validate_source_candidate_packet(candidate)
    normalized_intake = validate_adaptive_pr1_variant_intake(intake, candidate=normalized_candidate)
    current_manifest = validate_target_manifest(current_target_manifest)
    old_manifest = validate_target_manifest(old_target_manifest)
    _assert_target_continuity(old_manifest, current_manifest)
    source_rows = _normalize_binding_rows(
        source_artifacts, expected=ADAPTIVE_PR1_SOURCE_TYPES, label="source_artifacts"
    )
    prepare_rows = _normalize_binding_rows(
        original_prepare_bindings,
        expected={name: "json" for name in ADAPTIVE_PR1_PREPARE_FILENAMES},
        label="original_prepare_bindings",
    )
    source_by_name = {row["filename"]: row for row in source_rows}
    if source_by_name["creative_code_candidate.v1.json"]["fingerprint"] != fingerprint_payload(
        dict(normalized_candidate)
    ):
        raise CreativePilotContractError("adaptive_source_fingerprint_mismatch: candidate")
    resume_id, idempotency_key = derive_adaptive_pr1_resume_identity(
        pilot_id=pilot_id,
        intake=normalized_intake,
        candidate=normalized_candidate,
        source_artifacts=source_rows,
        original_prepare_bindings=prepare_rows,
        old_target_manifest=old_manifest,
        current_target_manifest=current_manifest,
    )
    body: dict[str, Any] = {
        "schema_version": ADAPTIVE_PR1_SCHEMA_VERSION,
        "artifact_type": ADAPTIVE_PR1_RESUME_TYPE,
        "policy_version": ADAPTIVE_PR1_POLICY_VERSION,
        "pilot_id": _token(pilot_id, "pilot_id"),
        "intake": {
            "intake_id": normalized_intake["intake_id"],
            "intake_ref": _artifact_ref(
                intake_ref,
                "intake.intake_ref",
                filename="creative_adaptive_pr1_variant_intake.json",
            ),
            "intake_fingerprint": fingerprint_payload(dict(normalized_intake)),
        },
        "candidate_packet": {
            "candidate_id": normalized_candidate["candidate_id"],
            "candidate_packet_ref": _artifact_ref(
                candidate_ref,
                "candidate_packet.candidate_packet_ref",
                filename="creative_code_candidate_packet.json",
            ),
            "candidate_fingerprint": fingerprint_payload(dict(normalized_candidate)),
        },
        "source_lineage": {
            "source_base_sha": old_manifest["base_sha"],
            "source_head_sha": old_manifest["head_sha"],
            "current_base_sha": current_manifest["base_sha"],
            "source_artifacts": source_rows,
            "original_prepare_bindings": prepare_rows,
            "old_target_manifest": old_manifest,
            "current_target_manifest": current_manifest,
        },
        "spec_prepare": {
            "run_dir_ref": _artifact_ref(spec_prepare_ref, "spec_prepare.run_dir_ref"),
            "expected_files": list(ADAPTIVE_PR1_PREPARE_FILENAMES),
            "prepared": True,
            "finalized": False,
            "next_allowed_action": "agent_skeptic_review",
        },
        "authority": dict(ADAPTIVE_PR1_AUTHORITY),
        "sanitized": True,
    }
    return validate_adaptive_pr1_resume_binding(
        {
            **body,
            "resume_id": resume_id,
            "bridge_id": resume_id,
            "idempotency_key": idempotency_key,
        },
        intake=normalized_intake,
        candidate=normalized_candidate,
        revalidate_git=True,
    )


def validate_adaptive_pr1_resume_binding(
    payload: Mapping[str, Any],
    *,
    intake: Mapping[str, Any],
    candidate: Mapping[str, Any],
    revalidate_git: bool = True,
) -> dict[str, Any]:
    """Validate CreativeAdaptivePr1ResumeBindingV1 and current Git continuity."""

    _exact_keys(
        payload,
        {
            "schema_version",
            "artifact_type",
            "resume_id",
            "bridge_id",
            "idempotency_key",
            "policy_version",
            "pilot_id",
            "intake",
            "candidate_packet",
            "source_lineage",
            "spec_prepare",
            "authority",
            "sanitized",
        },
        "CreativeAdaptivePr1ResumeBindingV1",
    )
    if (
        payload["schema_version"] != ADAPTIVE_PR1_SCHEMA_VERSION
        or payload["artifact_type"] != ADAPTIVE_PR1_RESUME_TYPE
    ):
        raise CreativePilotContractError("adaptive resume version or artifact_type mismatch")
    if payload["policy_version"] != ADAPTIVE_PR1_POLICY_VERSION or payload["sanitized"] is not True:
        raise CreativePilotContractError("adaptive resume policy or sanitization mismatch")
    normalized_candidate = validate_source_candidate_packet(candidate)
    normalized_intake = validate_adaptive_pr1_variant_intake(intake, candidate=normalized_candidate)
    pilot_id = _token(payload["pilot_id"], "pilot_id")
    if normalized_intake["pilot_id"] != pilot_id:
        raise CreativePilotContractError(
            "adaptive_pilot_lineage_mismatch: resume and intake pilot_id differ"
        )
    intake_ref = payload["intake"]
    candidate_ref = payload["candidate_packet"]
    if not isinstance(intake_ref, Mapping) or not isinstance(candidate_ref, Mapping):
        raise CreativePilotContractError("adaptive resume intake/candidate refs must be objects")
    _exact_keys(intake_ref, {"intake_id", "intake_ref", "intake_fingerprint"}, "resume.intake")
    _exact_keys(
        candidate_ref,
        {"candidate_id", "candidate_packet_ref", "candidate_fingerprint"},
        "resume.candidate_packet",
    )
    if intake_ref["intake_id"] != normalized_intake["intake_id"] or intake_ref[
        "intake_fingerprint"
    ] != fingerprint_payload(dict(normalized_intake)):
        raise CreativePilotContractError("adaptive_source_fingerprint_mismatch: intake")
    if candidate_ref["candidate_id"] != normalized_candidate["candidate_id"] or candidate_ref[
        "candidate_fingerprint"
    ] != fingerprint_payload(dict(normalized_candidate)):
        raise CreativePilotContractError("adaptive_source_fingerprint_mismatch: candidate")
    _artifact_ref(
        intake_ref["intake_ref"],
        "resume.intake_ref",
        filename="creative_adaptive_pr1_variant_intake.json",
    )
    _artifact_ref(
        candidate_ref["candidate_packet_ref"],
        "resume.candidate_ref",
        filename="creative_code_candidate_packet.json",
    )
    lineage = payload["source_lineage"]
    if not isinstance(lineage, Mapping):
        raise CreativePilotContractError("adaptive resume source_lineage must be an object")
    _exact_keys(
        lineage,
        {
            "source_base_sha",
            "source_head_sha",
            "current_base_sha",
            "source_artifacts",
            "original_prepare_bindings",
            "old_target_manifest",
            "current_target_manifest",
        },
        "resume.source_lineage",
    )
    old_manifest = validate_target_manifest(
        cast(Mapping[str, Any], lineage["old_target_manifest"]), revalidate_git=True
    )
    current_manifest = validate_target_manifest(
        cast(Mapping[str, Any], lineage["current_target_manifest"]), revalidate_git=True
    )
    if (
        lineage["source_base_sha"] != old_manifest["base_sha"]
        or lineage["source_head_sha"] != old_manifest["head_sha"]
        or lineage["current_base_sha"] != current_manifest["base_sha"]
    ):
        raise CreativePilotContractError("adaptive resume SHA binding mismatch")
    _assert_target_continuity(old_manifest, current_manifest)
    if revalidate_git and current_manifest["base_sha"] != current_origin_main_sha():
        raise CreativePilotContractError("adaptive_base_drift: current origin/main advanced")
    source_rows = _normalize_binding_rows(
        cast(Sequence[Mapping[str, Any]], lineage["source_artifacts"]),
        expected=ADAPTIVE_PR1_SOURCE_TYPES,
        label="source_artifacts",
        revalidate_files=revalidate_git,
    )
    prepare_rows = _normalize_binding_rows(
        cast(Sequence[Mapping[str, Any]], lineage["original_prepare_bindings"]),
        expected={name: "json" for name in ADAPTIVE_PR1_PREPARE_FILENAMES},
        label="original_prepare_bindings",
        revalidate_files=revalidate_git,
    )
    pilot_root = f"artifacts/orchestration/creative_code/adaptive_pilots/{pilot_id}"
    intake_source = cast(Mapping[str, Any], normalized_intake["source_candidate"])
    if intake_source["candidate_ref"] != f"{pilot_root}/creative_code_candidate.v1.json":
        raise CreativePilotContractError(
            "adaptive_pilot_lineage_mismatch: intake candidate ref escaped pilot root"
        )
    for row in source_rows:
        if row["ref"] != f"{pilot_root}/{row['filename']}":
            raise CreativePilotContractError(
                "adaptive_pilot_lineage_mismatch: retained source ref escaped pilot root"
            )
    for row in prepare_rows:
        if row["ref"] != f"{pilot_root}/pr1_prepare/{row['filename']}":
            raise CreativePilotContractError(
                "adaptive_pilot_lineage_mismatch: retained prepare ref escaped pilot root"
            )
    prepare = payload["spec_prepare"]
    if not isinstance(prepare, Mapping):
        raise CreativePilotContractError("adaptive resume spec_prepare must be an object")
    _exact_keys(
        prepare,
        {"run_dir_ref", "expected_files", "prepared", "finalized", "next_allowed_action"},
        "resume.spec_prepare",
    )
    if (
        prepare["expected_files"] != list(ADAPTIVE_PR1_PREPARE_FILENAMES)
        or prepare["prepared"] is not True
        or prepare["finalized"] is not False
        or prepare["next_allowed_action"] != "agent_skeptic_review"
    ):
        raise CreativePilotContractError("adaptive resume spec_prepare state mismatch")
    _artifact_ref(prepare["run_dir_ref"], "resume.spec_prepare.run_dir_ref")
    normalized = dict(payload)
    normalized["pilot_id"] = pilot_id
    if payload["resume_id"] != payload["bridge_id"]:
        raise CreativePilotContractError("adaptive resume bridge_id must equal resume_id")
    canonical_root = f"artifacts/orchestration/creative_code/spec_bridge/{payload['resume_id']}"
    if intake_ref["intake_ref"] != f"{canonical_root}/creative_adaptive_pr1_variant_intake.json":
        raise CreativePilotContractError("adaptive resume intake ref is not canonical")
    if (
        candidate_ref["candidate_packet_ref"]
        != f"{canonical_root}/creative_code_candidate_packet.json"
    ):
        raise CreativePilotContractError("adaptive resume candidate ref is not canonical")
    if prepare["run_dir_ref"] != f"{canonical_root}/spec_prepare":
        raise CreativePilotContractError("adaptive resume spec_prepare ref is not canonical")
    normalized["source_lineage"] = {
        **dict(lineage),
        "source_artifacts": source_rows,
        "original_prepare_bindings": prepare_rows,
        "old_target_manifest": old_manifest,
        "current_target_manifest": current_manifest,
    }
    normalized["authority"] = _adaptive_authority(payload["authority"], "adaptive resume")
    expected_resume_id, expected_idempotency = derive_adaptive_pr1_resume_identity(
        pilot_id=str(normalized["pilot_id"]),
        intake=normalized_intake,
        candidate=normalized_candidate,
        source_artifacts=source_rows,
        original_prepare_bindings=prepare_rows,
        old_target_manifest=old_manifest,
        current_target_manifest=current_manifest,
    )
    if (
        normalized["resume_id"] != expected_resume_id
        or normalized["idempotency_key"] != expected_idempotency
    ):
        raise CreativePilotContractError("creative_adaptive_pr1_resume_binding identity mismatch")
    return normalized


def derive_adaptive_pr1_resume_identity(
    *,
    pilot_id: str,
    intake: Mapping[str, Any],
    candidate: Mapping[str, Any],
    source_artifacts: Sequence[Mapping[str, Any]],
    original_prepare_bindings: Sequence[Mapping[str, Any]],
    old_target_manifest: Mapping[str, Any],
    current_target_manifest: Mapping[str, Any],
) -> tuple[str, str]:
    """Derive resume identity without self-referential output paths."""

    seed = {
        "pilot_id": _token(pilot_id, "pilot_id"),
        "intake_id": intake["intake_id"],
        "intake_fingerprint": fingerprint_payload(dict(intake)),
        "candidate_id": candidate["candidate_id"],
        "candidate_fingerprint": fingerprint_payload(dict(candidate)),
        "source_artifacts": list(source_artifacts),
        "original_prepare_bindings": list(original_prepare_bindings),
        "old_target_manifest": dict(old_target_manifest),
        "current_target_manifest": dict(current_target_manifest),
    }
    return _adaptive_identity(
        seed,
        artifact_type=ADAPTIVE_PR1_RESUME_TYPE,
        upstream_ids=(str(intake["intake_id"]), str(candidate["candidate_id"])),
    )


def _assert_target_continuity(old: Mapping[str, Any], current: Mapping[str, Any]) -> None:
    for key in (
        "files",
        "symbols",
        "immutable_oracles",
        "oracle_bindings",
        "public_contract_change",
        "provider_behavior_change",
        "feature_flag_change",
        "user_data_access_change",
    ):
        if old[key] != current[key]:
            code = (
                "adaptive_oracle_drift"
                if key in {"immutable_oracles", "oracle_bindings"}
                else "adaptive_target_drift"
            )
            raise CreativePilotContractError(f"{code}: {key} changed")


def _normalize_binding_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected: Mapping[str, str],
    label: str,
    revalidate_files: bool = False,
) -> list[dict[str, str]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise CreativePilotContractError(f"{label} must be an array")
    normalized: list[dict[str, str]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise CreativePilotContractError(f"{label} rows must be objects")
        _exact_keys(raw, {"filename", "artifact_type", "ref", "fingerprint"}, label)
        filename = _token(raw["filename"], f"{label}.filename")
        artifact_type = _token(raw["artifact_type"], f"{label}.artifact_type")
        if filename not in expected or artifact_type != expected[filename]:
            raise CreativePilotContractError(f"adaptive_source_type_mismatch: {filename}")
        ref = _artifact_ref(raw["ref"], f"{label}.ref", filename=filename)
        fingerprint = _fingerprint(raw["fingerprint"], f"{label}.fingerprint")
        if revalidate_files:
            _revalidate_bound_json(
                ref, filename=filename, artifact_type=artifact_type, fingerprint=fingerprint
            )
        normalized.append(
            {
                "filename": filename,
                "artifact_type": artifact_type,
                "ref": ref,
                "fingerprint": fingerprint,
            }
        )
    if [row["filename"] for row in normalized] != list(expected):
        raise CreativePilotContractError(
            f"adaptive_source_missing: {label} exact ordered set required"
        )
    return normalized


def _revalidate_bound_json(
    ref: str, *, filename: str, artifact_type: str, fingerprint: str
) -> None:
    path = REPO_ROOT / ref
    current = REPO_ROOT
    try:
        for part in PurePosixPath(ref).parts:
            current = current / part
            if current.is_symlink():
                raise CreativePilotContractError(f"adaptive_source_symlink: {filename}")
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CreativePilotContractError(f"adaptive_source_missing: {filename}") from exc
    if not resolved.is_file() or not resolved.is_relative_to(REPO_ROOT.resolve()):
        raise CreativePilotContractError(f"adaptive_source_missing: {filename}")
    import json

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise CreativePilotContractError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    try:
        payload = json.loads(
            resolved.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CreativePilotContractError(f"adaptive_source_invalid_json: {filename}") from exc
    observed_type = (
        payload.get("artifact_type") or payload.get("packet_type")
        if isinstance(payload, Mapping)
        else None
    )
    if artifact_type == "json":
        observed_type = "json"
    if artifact_type != "json" and observed_type != artifact_type:
        raise CreativePilotContractError(f"adaptive_source_type_mismatch: {filename}")
    if fingerprint_payload(payload) != fingerprint:
        raise CreativePilotContractError(f"adaptive_source_fingerprint_mismatch: {filename}")


def load_json_strict(text: str) -> dict[str, Any]:
    """Load one JSON object while rejecting duplicate keys."""

    import json

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise CreativePilotContractError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    try:
        payload = json.loads(text, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise CreativePilotContractError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CreativePilotContractError("artifact must be a JSON object")
    return payload


def _exact_keys(payload: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(payload)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        raise CreativePilotContractError(
            f"{label} keys mismatch; missing={missing}, unknown={unknown}"
        )


def _token(value: Any, label: str, *, allowed: frozenset[str] | None = None) -> str:
    if not isinstance(value, str) or not value or len(value) > 160 or not ID_RE.fullmatch(value):
        raise CreativePilotContractError(f"{label} must be a bounded token")
    if allowed is not None and value not in allowed:
        raise CreativePilotContractError(f"{label} is unsupported")
    return value


def _fingerprint(value: Any, label: str) -> str:
    if not isinstance(value, str) or not FINGERPRINT_RE.fullmatch(value):
        raise CreativePilotContractError(f"{label} must be a sha256 fingerprint")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativePilotContractError(f"{label} must be a full 40-character commit SHA")
    return value


def _string_list(
    value: Any,
    label: str,
    *,
    min_items: int = 0,
    max_items: int = 32,
) -> list[str]:
    if not isinstance(value, list) or not min_items <= len(value) <= max_items:
        raise CreativePilotContractError(f"{label} must contain {min_items}..{max_items} items")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > 320:
            raise CreativePilotContractError(f"{label} contains an invalid string")
        normalized = item.strip()
        if (
            FORBIDDEN_TEXT_RE.search(normalized)
            or SECRET_TEXT_RE.search(normalized)
            or LEAK_TEXT_RE.search(normalized)
        ):
            raise CreativePilotContractError(
                f"{label} contains forbidden raw or secret-shaped text"
            )
        output.append(normalized)
    if len(output) != len(set(output)):
        raise CreativePilotContractError(f"{label} must not contain duplicates")
    return output


def _path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise CreativePilotContractError(f"{label} must be a repo-relative path")
    if "*" in value or "?" in value or "[" in value:
        raise CreativePilotContractError(f"{label} must be an exact path, not a glob")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value != path.as_posix():
        raise CreativePilotContractError(f"{label} must be a normalized repo-relative path")
    return value


def _evidence_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or "://" in value or value.startswith("artifacts/"):
        raise CreativePilotContractError(f"{label} must reference allowlisted repository evidence")
    base = value.rsplit(":", 1)[0] if re.search(r":\d+(?:-\d+)?$", value) else value
    return _path(base, label)


def _git_path() -> str:
    git = shutil.which("git")
    if not git:
        raise CreativePilotContractError("git executable is required")
    return git


def _git(*args: str, binary: bool = False) -> str | bytes:
    try:
        completed = subprocess.run(  # nosec B603: absolute Git binary with validated bounded argv (remove-by: 2026-09-30, ref: ledger-p1-agent-experimentation-lane)
            [_git_path(), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=not binary,
            timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        raise CreativePilotContractError(f"git {' '.join(args[:2])} timed out") from exc
    if completed.returncode != 0:
        stderr = completed.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise CreativePilotContractError(f"git {' '.join(args[:2])} failed: {str(stderr).strip()}")
    return cast(str | bytes, completed.stdout)


def _require_commit(commit_sha: str, label: str) -> None:
    observed = cast(str, _git("cat-file", "-t", commit_sha)).strip()
    if observed != "commit":
        raise CreativePilotContractError(f"{label} must identify a commit object")


def current_origin_main_sha() -> str:
    """Return the exact local origin/main commit used by planning artifacts."""

    value = cast(str, _git("rev-parse", "origin/main")).strip()
    return _sha(value, "origin/main")


def _blob_oid_at(commit_sha: str, path: str) -> str:
    output = cast(bytes, _git("ls-tree", "-z", commit_sha, "--", path, binary=True))
    records = output.split(b"\0")
    if not records or records[-1] != b"" or len(records) != 2:
        raise CreativePilotContractError(
            f"target path is not a tracked blob at {commit_sha}: {path}"
        )
    metadata, separator, raw_path = records[0].partition(b"\t")
    fields = metadata.split(b" ")
    if separator != b"\t" or len(fields) != 3 or raw_path != path.encode("utf-8"):
        raise CreativePilotContractError(
            f"target path is not a tracked blob at {commit_sha}: {path}"
        )
    mode, object_type, raw_oid = fields
    if mode in {b"120000", b"160000"}:
        raise CreativePilotContractError(f"target path must not be a symlink or submodule: {path}")
    if object_type != b"blob":
        raise CreativePilotContractError(
            f"target path is not a tracked blob at {commit_sha}: {path}"
        )
    try:
        return raw_oid.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CreativePilotContractError(
            f"target path has an invalid Git object ID at {commit_sha}: {path}"
        ) from exc


def _blob_at(commit_sha: str, path: str) -> tuple[str, bytes]:
    blob_oid = _blob_oid_at(commit_sha, path)
    content = cast(bytes, _git("show", f"{commit_sha}:{path}", binary=True))
    return blob_oid, content


def tracked_blob_size_at_commit(commit_sha: str, path: str) -> int:
    """Return immutable Git-object size evidence for one tracked repository path."""

    commit = _sha(commit_sha, "commit_sha")
    _require_commit(commit, "commit_sha")
    normalized_path = _path(path, "tracked_file.path")
    blob_oid = _blob_oid_at(commit, normalized_path)
    raw_size = cast(str, _git("cat-file", "-s", blob_oid)).strip()
    if re.fullmatch(r"[0-9]{1,20}", raw_size) is None:
        raise CreativePilotContractError("tracked blob size must be a non-negative integer")
    return int(raw_size)


def _symbols(content: bytes, path: str) -> set[str]:
    if not path.endswith(".py"):
        raise CreativePilotContractError("production-adjacent pilot targets must be Python files")
    try:
        tree = ast.parse(content.decode("utf-8"), filename=path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise CreativePilotContractError(f"target Python source cannot be parsed: {path}") from exc
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def build_target_manifest(
    *,
    base_sha: str,
    head_sha: str,
    paths: Sequence[str],
    symbols: Sequence[str],
    immutable_oracles: Sequence[str],
    require_current_origin_main: bool = True,
) -> dict[str, Any]:
    """Bind an exact production-adjacent planning target to Git objects."""

    base = _sha(base_sha, "base_sha")
    head = _sha(head_sha, "head_sha")
    _require_commit(base, "base_sha")
    _require_commit(head, "head_sha")
    origin_main = current_origin_main_sha() if require_current_origin_main else None
    if require_current_origin_main and (base != origin_main or head != origin_main):
        raise CreativePilotContractError(
            "production-adjacent pilot base_sha and head_sha must equal current origin/main"
        )
    normalized_paths = [_path(item, "target.paths") for item in paths]
    if not 1 <= len(normalized_paths) <= 2 or len(set(normalized_paths)) != len(normalized_paths):
        raise CreativePilotContractError("target.paths must contain one or two exact files")
    try:
        validate_mutable_candidate_surface(normalized_paths)
    except ValueError as exc:
        raise CreativePilotContractError(str(exc)) from exc
    if any(not item.startswith(ALLOWED_TARGET_PREFIXES) for item in normalized_paths):
        raise CreativePilotContractError(
            "production-adjacent targets are limited to core/rag or core/insight"
        )
    normalized_symbols = _string_list(list(symbols), "target.symbols", min_items=1, max_items=16)
    oracles = [_path(item, "immutable_oracles") for item in immutable_oracles]
    if not oracles or len(oracles) != len(set(oracles)):
        raise CreativePilotContractError("immutable_oracles must be a non-empty unique list")
    if any(not item.startswith("tests/") for item in oracles):
        raise CreativePilotContractError("immutable_oracles must be repo-owned tests")
    if set(normalized_paths) & set(oracles):
        raise CreativePilotContractError("mutable targets and immutable oracles must be disjoint")

    entries: list[dict[str, str]] = []
    available_symbols: set[str] = set()
    for path in normalized_paths:
        base_blob, base_content = _blob_at(base, path)
        head_blob, head_content = _blob_at(head, path)
        if base_blob != head_blob or base_content != head_content:
            raise CreativePilotContractError(
                "production-adjacent planning target must be unchanged between base and head"
            )
        available_symbols.update(_symbols(head_content, path))
        entries.append(
            {
                "path": path,
                "blob_oid": head_blob,
                "content_fingerprint": f"sha256:{sha256(head_content).hexdigest()}",
            }
        )
    oracle_bindings = [_tracked_file_binding(head, path) for path in sorted(oracles)]
    missing_symbols = sorted(set(normalized_symbols) - available_symbols)
    if missing_symbols:
        raise CreativePilotContractError(f"target symbols do not exist: {missing_symbols}")
    body: dict[str, Any] = {
        "surface_policy": SURFACE_POLICY,
        "base_sha": base,
        "head_sha": head,
        "files": entries,
        "symbols": sorted(normalized_symbols),
        "immutable_oracles": sorted(oracles),
        "oracle_bindings": oracle_bindings,
        "public_contract_change": False,
        "provider_behavior_change": False,
        "feature_flag_change": False,
        "user_data_access_change": False,
    }
    return {**body, "manifest_fingerprint": fingerprint_payload(body)}


def validate_target_manifest(
    payload: Mapping[str, Any], *, revalidate_git: bool = True
) -> dict[str, Any]:
    _exact_keys(
        payload,
        {
            "surface_policy",
            "base_sha",
            "head_sha",
            "files",
            "symbols",
            "immutable_oracles",
            "oracle_bindings",
            "public_contract_change",
            "provider_behavior_change",
            "feature_flag_change",
            "user_data_access_change",
            "manifest_fingerprint",
        },
        "target_manifest",
    )
    if payload["surface_policy"] != SURFACE_POLICY:
        raise CreativePilotContractError("target_manifest.surface_policy is unsupported")
    for key in (
        "public_contract_change",
        "provider_behavior_change",
        "feature_flag_change",
        "user_data_access_change",
    ):
        if payload[key] is not False:
            raise CreativePilotContractError(f"target_manifest.{key} must remain false")
    files = payload["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 2:
        raise CreativePilotContractError("target_manifest.files must contain one or two rows")
    paths: list[str] = []
    for row in files:
        if not isinstance(row, Mapping):
            raise CreativePilotContractError("target_manifest.files rows must be objects")
        _exact_keys(row, {"path", "blob_oid", "content_fingerprint"}, "target_file")
        paths.append(_path(row["path"], "target_file.path"))
        if not isinstance(row["blob_oid"], str) or not re.fullmatch(
            r"[0-9a-f]{40}", row["blob_oid"]
        ):
            raise CreativePilotContractError("target_file.blob_oid is invalid")
        _fingerprint(row["content_fingerprint"], "target_file.content_fingerprint")
    expected = (
        build_target_manifest(
            base_sha=_sha(payload["base_sha"], "base_sha"),
            head_sha=_sha(payload["head_sha"], "head_sha"),
            paths=paths,
            symbols=_string_list(payload["symbols"], "target.symbols", min_items=1, max_items=16),
            immutable_oracles=_string_list(
                payload["immutable_oracles"], "immutable_oracles", min_items=1, max_items=32
            ),
            require_current_origin_main=False,
        )
        if revalidate_git
        else dict(payload)
    )
    if revalidate_git and expected != dict(payload):
        raise CreativePilotContractError("target manifest no longer matches Git object truth")
    _fingerprint(payload["manifest_fingerprint"], "target_manifest.manifest_fingerprint")
    return expected


def _tracked_file_binding(commit_sha: str, path: str) -> dict[str, str]:
    normalized = _path(path, "tracked_file.path")
    blob_oid, content = _blob_at(commit_sha, normalized)
    return {
        "path": normalized,
        "blob_oid": blob_oid,
        "content_fingerprint": f"sha256:{sha256(content).hexdigest()}",
    }


def _identity(
    body: Mapping[str, Any], *, artifact_type: str, upstream_ids: Sequence[str]
) -> tuple[str, str]:
    fingerprint = fingerprint_payload(dict(body))
    return (
        build_asset_id(
            asset_type=artifact_type,
            rail="orchestration",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=fingerprint,
            upstream_ids=tuple(upstream_ids),
        ),
        build_idempotency_key(
            asset_type=artifact_type,
            rail="orchestration",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=fingerprint,
            upstream_ids=tuple(upstream_ids),
        ),
    )


def _base_artifact(artifact_type: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "policy_version": POLICY_VERSION,
        "surface_policy": SURFACE_POLICY,
    }


def build_context_map_v2(
    *, target_manifest: Mapping[str, Any], context_refs: Sequence[str]
) -> dict[str, Any]:
    target = validate_target_manifest(target_manifest)
    refs = [_path(item, "context_refs") for item in context_refs]
    if not 1 <= len(refs) <= 32:
        raise CreativePilotContractError(
            "context refs must contain 1..32 tracked read-only evidence paths"
        )
    if any(item.startswith("artifacts/") for item in refs):
        raise CreativePilotContractError("context refs must be tracked repository paths")
    context_bindings = [
        _tracked_file_binding(str(target["head_sha"]), path) for path in sorted(set(refs))
    ]
    body = {
        **_base_artifact(CONTEXT_TYPE),
        "target_manifest": target,
        "context_refs": sorted(set(refs)),
        "context_bindings": context_bindings,
        "authority": dict(AUTHORITY),
        "sanitized": True,
    }
    context_id, idempotency_key = _identity(body, artifact_type=CONTEXT_TYPE, upstream_ids=())
    return {**body, "context_id": context_id, "idempotency_key": idempotency_key}


def validate_context_map_v2(
    payload: Mapping[str, Any], *, revalidate_git: bool = True
) -> dict[str, Any]:
    _exact_keys(
        payload,
        {
            "schema_version",
            "artifact_type",
            "policy_version",
            "surface_policy",
            "context_id",
            "idempotency_key",
            "target_manifest",
            "context_refs",
            "context_bindings",
            "authority",
            "sanitized",
        },
        "CreativeProtocolContextMapV2",
    )
    _validate_header(payload, CONTEXT_TYPE)
    target = validate_target_manifest(
        cast(Mapping[str, Any], payload["target_manifest"]), revalidate_git=revalidate_git
    )
    expected = (
        build_context_map_v2(
            target_manifest=target,
            context_refs=_string_list(
                payload["context_refs"], "context_refs", min_items=1, max_items=32
            ),
        )
        if revalidate_git
        else dict(payload)
    )
    if revalidate_git and expected != dict(payload):
        raise CreativePilotContractError("context v2 identity mismatch")
    return expected


def build_hypothesis_packet_v2(
    *, context_map: Mapping[str, Any], hypotheses: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    context = validate_context_map_v2(context_map)
    if not 1 <= len(hypotheses) <= 2:
        raise CreativePilotContractError("pilot permits one or two hypothesis-selection attempts")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(hypotheses, start=1):
        _exact_keys(
            raw,
            {
                "hypothesis_id",
                "statement",
                "mechanism",
                "target_symbols",
                "tests_or_oracles",
                "negative_controls",
                "tags",
            },
            "hypothesis",
        )
        row: dict[str, Any] = {
            "hypothesis_id": _token(raw["hypothesis_id"], "hypothesis_id"),
            "statement": _bounded_text(raw["statement"], "statement"),
            "mechanism": _bounded_text(raw["mechanism"], "mechanism"),
            "target_symbols": _string_list(
                raw["target_symbols"], "target_symbols", min_items=1, max_items=16
            ),
            "tests_or_oracles": _string_list(
                raw["tests_or_oracles"], "tests_or_oracles", min_items=1, max_items=32
            ),
            "negative_controls": _string_list(
                raw["negative_controls"], "negative_controls", min_items=1, max_items=16
            ),
            "tags": _string_list(raw["tags"], "tags", max_items=16),
            "attempt": index,
        }
        if not set(cast(Sequence[str], row["target_symbols"])).issubset(
            set(cast(Sequence[str], context["target_manifest"]["symbols"]))
        ):
            raise CreativePilotContractError("hypothesis target symbols must be in target manifest")
        if not set(cast(Sequence[str], row["tests_or_oracles"])).issubset(
            set(cast(Sequence[str], context["target_manifest"]["immutable_oracles"]))
        ):
            raise CreativePilotContractError("hypothesis oracles must be in target manifest")
        row["hypothesis_fingerprint"] = fingerprint_payload(row)
        rows.append(row)
    body = {
        **_base_artifact(HYPOTHESIS_PACKET_TYPE),
        "source_context_id": context["context_id"],
        "source_context_fingerprint": fingerprint_payload(context),
        "target_manifest_fingerprint": context["target_manifest"]["manifest_fingerprint"],
        "hypotheses": rows,
        "hypothesis_count": len(rows),
        "authority": dict(AUTHORITY),
        "sanitized": True,
    }
    packet_id, idempotency_key = _identity(
        body, artifact_type=HYPOTHESIS_PACKET_TYPE, upstream_ids=(str(context["context_id"]),)
    )
    return {**body, "packet_id": packet_id, "idempotency_key": idempotency_key}


def validate_hypothesis_packet_v2(
    payload: Mapping[str, Any], *, context_map: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    _exact_keys(
        payload,
        {
            "schema_version",
            "artifact_type",
            "policy_version",
            "surface_policy",
            "packet_id",
            "idempotency_key",
            "source_context_id",
            "source_context_fingerprint",
            "target_manifest_fingerprint",
            "hypotheses",
            "hypothesis_count",
            "authority",
            "sanitized",
        },
        "CreativeHypothesisPacketV2",
    )
    _validate_header(payload, HYPOTHESIS_PACKET_TYPE)
    if context_map is None:
        raise CreativePilotContractError(
            "hypothesis packet v2 validation requires its bound context map"
        )
    context = validate_context_map_v2(context_map)
    expected = build_hypothesis_packet_v2(
        context_map=context,
        hypotheses=[
            {
                key: value
                for key, value in row.items()
                if key not in {"attempt", "hypothesis_fingerprint"}
            }
            for row in cast(Sequence[Mapping[str, Any]], payload["hypotheses"])
        ],
    )
    if expected != dict(payload):
        raise CreativePilotContractError("hypothesis packet v2 identity or source binding mismatch")
    return expected


def _bounded_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not 12 <= len(value.strip()) <= 1200:
        raise CreativePilotContractError(f"{label} must contain 12..1200 characters")
    normalized = value.strip()
    if (
        FORBIDDEN_TEXT_RE.search(normalized)
        or SECRET_TEXT_RE.search(normalized)
        or LEAK_TEXT_RE.search(normalized)
    ):
        raise CreativePilotContractError(f"{label} contains forbidden raw or secret-shaped text")
    return normalized


def _validate_header(payload: Mapping[str, Any], artifact_type: str) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise CreativePilotContractError("schema_version is unsupported")
    if payload.get("artifact_type") != artifact_type:
        raise CreativePilotContractError("artifact_type is unsupported")
    if (
        payload.get("policy_version") != POLICY_VERSION
        or payload.get("surface_policy") != SURFACE_POLICY
    ):
        raise CreativePilotContractError("policy tuple is unsupported")
    if payload.get("authority") != AUTHORITY or payload.get("sanitized") is not True:
        raise CreativePilotContractError("authority or sanitized boundary is invalid")


def route_roles(hypothesis: Mapping[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    tags = {item.lower() for item in cast(Sequence[str], hypothesis.get("tags", []))}
    roles = list(REQUIRED_ROLES)
    conditional: list[dict[str, str]] = []
    for tokens, role in CONDITIONAL_ROLE_RULES:
        if tokens & tags:
            roles.append(role)
            conditional.append(
                {"role": role, "fallback": "agent-coordinator records explicit capability gap"}
            )
    return list(dict.fromkeys(roles)), conditional


def _build_assignment(
    *,
    intent: Mapping[str, Any],
    index: int,
    role: str,
    phase: str,
    input_refs: Sequence[str],
) -> dict[str, Any]:
    question = ROLE_QUESTIONS.get(
        role,
        "Assess the bounded specification against repository evidence and declared oracles.",
    )
    identity: dict[str, Any] = {
        "intent": dict(intent),
        "role": role,
        "phase": phase,
        "review_mode": "specification_planning",
        "diff_expected": False,
        "review_question": question,
        "input_refs": list(input_refs),
    }
    return {
        "assignment_id": f"{phase}:{index}:{role}",
        "role": role,
        "phase": phase,
        "review_mode": "specification_planning",
        "diff_expected": False,
        "review_question": question,
        "input_fingerprint": fingerprint_payload(identity),
        "input_refs": list(input_refs),
    }


def build_workspace(
    *,
    context_map: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    selected_hypothesis_id: str,
) -> dict[str, Any]:
    context = validate_context_map_v2(context_map)
    packet = validate_hypothesis_packet_v2(hypothesis_packet, context_map=context)
    selected = next(
        (row for row in packet["hypotheses"] if row["hypothesis_id"] == selected_hypothesis_id),
        None,
    )
    if selected is None:
        raise CreativePilotContractError("selected hypothesis does not exist")
    roles, conditional = route_roles(cast(Mapping[str, Any], selected))
    target = context["target_manifest"]
    intent = {
        "context_id": context["context_id"],
        "context_fingerprint": fingerprint_payload(context),
        "packet_id": packet["packet_id"],
        "packet_fingerprint": fingerprint_payload(packet),
        "hypothesis_id": selected_hypothesis_id,
        "hypothesis_fingerprint": selected["hypothesis_fingerprint"],
        "target_manifest_fingerprint": target["manifest_fingerprint"],
        "base_sha": target["base_sha"],
        "head_sha": target["head_sha"],
    }
    body = {
        **_base_artifact(WORKSPACE_TYPE),
        "intent": intent,
        "target_manifest": target,
        "evidence_allowlist": sorted(
            {
                *cast(Sequence[str], context["context_refs"]),
                *(row["path"] for row in cast(Sequence[Mapping[str, Any]], target["files"])),
                *cast(Sequence[str], target["immutable_oracles"]),
            }
        ),
        "role_plan": {
            "required_roles": roles,
            "conditional_roles": conditional,
            "independent_first_pass": INDEPENDENT_FIRST_PASS_ENABLED,
            "max_rebuttal_rounds": 1,
            "majority_vote_allowed": False,
            "raw_reasoning_allowed": False,
        },
        "assignments": [
            _build_assignment(
                intent=intent,
                index=index,
                role=role,
                phase="independent",
                input_refs=[
                    str(context["context_id"]),
                    str(packet["packet_id"]),
                    str(target["manifest_fingerprint"]),
                ],
            )
            for index, role in enumerate(roles, start=1)
        ],
        "role_results": [],
        "conflicts": [],
        "synthesis_ref": None,
        "handoff_ref": None,
        "rebuttal_rounds_used": 0,
        "state": {"phase": "independent_dispatched", "terminal": False},
        "revision": 1,
        "authority": dict(AUTHORITY),
        "sanitized": True,
    }
    intent_fingerprint = fingerprint_payload(intent)
    workspace_id, idempotency_key = _identity(
        body,
        artifact_type=WORKSPACE_TYPE,
        upstream_ids=(str(packet["packet_id"]), selected_hypothesis_id),
    )
    artifact = {
        **body,
        "workspace_id": workspace_id,
        "intent_fingerprint": intent_fingerprint,
        "revision_fingerprint": fingerprint_payload(body),
        "idempotency_key": idempotency_key,
    }
    return validate_workspace(artifact)


def _phase_dispatch_fingerprint_unchecked(workspace: Mapping[str, Any], *, phase: str) -> str:
    assignments = [
        {
            "assignment_id": row["assignment_id"],
            "role": row["role"],
            "phase": row["phase"],
            "review_mode": row["review_mode"],
            "diff_expected": row["diff_expected"],
            "review_question": row["review_question"],
            "input_fingerprint": row["input_fingerprint"],
            "input_refs": list(row["input_refs"]),
        }
        for row in cast(Sequence[Mapping[str, Any]], workspace["assignments"])
        if row["phase"] == phase
    ]
    if not assignments:
        raise CreativePilotContractError(f"workspace has no {phase} assignments")
    fingerprint = fingerprint_payload(
        {
            "workspace_id": workspace["workspace_id"],
            "workspace_intent_fingerprint": workspace["intent_fingerprint"],
            "phase": phase,
            "assignments": assignments,
        }
    )
    if not isinstance(fingerprint, str):
        raise CreativePilotContractError("phase dispatch fingerprint must be a string")
    return fingerprint


def _derive_conflicts(
    role_results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    claim_stances: dict[str, set[str]] = {}
    claim_oracle_gap_sets: dict[str, set[tuple[str, ...]]] = {}
    for result in role_results:
        for claim_id in cast(Sequence[str], result["claim_ids"]):
            claim_stances.setdefault(claim_id, set()).add(str(result["stance"]))
            claim_oracle_gap_sets.setdefault(claim_id, set()).add(
                tuple(sorted(cast(Sequence[str], result["oracle_gap_codes"])))
            )
    return [
        {
            "conflict_id": f"claim:{claim}",
            "claim_id": claim,
            "stances": sorted(stances),
            "oracle_gap_sets": [list(items) for items in sorted(claim_oracle_gap_sets[claim])],
        }
        for claim, stances in sorted(claim_stances.items())
        if len(stances) > 1 or len(claim_oracle_gap_sets[claim]) > 1
    ]


def validate_workspace(
    payload: Mapping[str, Any], *, revalidate_git: bool = True
) -> dict[str, Any]:
    _exact_keys(
        payload,
        {
            "schema_version",
            "artifact_type",
            "policy_version",
            "surface_policy",
            "workspace_id",
            "intent_fingerprint",
            "revision_fingerprint",
            "idempotency_key",
            "intent",
            "target_manifest",
            "evidence_allowlist",
            "role_plan",
            "assignments",
            "role_results",
            "conflicts",
            "synthesis_ref",
            "handoff_ref",
            "rebuttal_rounds_used",
            "state",
            "revision",
            "authority",
            "sanitized",
        },
        "CreativePilotWorkspace",
    )
    _validate_header(payload, WORKSPACE_TYPE)
    target = validate_target_manifest(
        cast(Mapping[str, Any], payload["target_manifest"]), revalidate_git=revalidate_git
    )
    intent = payload["intent"]
    if not isinstance(intent, Mapping):
        raise CreativePilotContractError("workspace intent must be an object")
    _exact_keys(
        intent,
        {
            "context_id",
            "context_fingerprint",
            "packet_id",
            "packet_fingerprint",
            "hypothesis_id",
            "hypothesis_fingerprint",
            "target_manifest_fingerprint",
            "base_sha",
            "head_sha",
        },
        "workspace.intent",
    )
    for key in (
        "context_fingerprint",
        "packet_fingerprint",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
    ):
        _fingerprint(intent[key], f"workspace.intent.{key}")
    for key in ("base_sha", "head_sha"):
        _sha(intent[key], f"workspace.intent.{key}")
    for key in ("context_id", "packet_id", "hypothesis_id"):
        _token(intent[key], f"workspace.intent.{key}")
    if intent["target_manifest_fingerprint"] != target["manifest_fingerprint"]:
        raise CreativePilotContractError("workspace target fingerprint mismatch")
    if intent["base_sha"] != target["base_sha"] or intent["head_sha"] != target["head_sha"]:
        raise CreativePilotContractError("workspace commit binding mismatch")
    evidence_allowlist = [
        _path(item, "workspace.evidence_allowlist")
        for item in _string_list(
            payload["evidence_allowlist"],
            "workspace.evidence_allowlist",
            min_items=1,
            max_items=64,
        )
    ]
    if evidence_allowlist != sorted(set(evidence_allowlist)):
        raise CreativePilotContractError("workspace evidence allowlist must be sorted and unique")
    required_evidence_paths = {
        *(row["path"] for row in cast(Sequence[Mapping[str, Any]], target["files"])),
        *cast(Sequence[str], target["immutable_oracles"]),
    }
    if not required_evidence_paths.issubset(evidence_allowlist):
        raise CreativePilotContractError(
            "workspace evidence allowlist omits target or oracle paths"
        )

    role_plan = payload["role_plan"]
    if not isinstance(role_plan, Mapping):
        raise CreativePilotContractError("workspace role_plan must be an object")
    _exact_keys(
        role_plan,
        {
            "required_roles",
            "conditional_roles",
            "independent_first_pass",
            "max_rebuttal_rounds",
            "majority_vote_allowed",
            "raw_reasoning_allowed",
        },
        "workspace.role_plan",
    )
    required_roles = _string_list(
        role_plan["required_roles"], "workspace.role_plan.required_roles", min_items=3, max_items=16
    )
    if not set(REQUIRED_ROLES).issubset(required_roles):
        raise CreativePilotContractError("workspace role plan is missing mandatory roles")
    if (
        role_plan["independent_first_pass"] is not True
        or role_plan["max_rebuttal_rounds"] != 1
        or role_plan["majority_vote_allowed"] is not False
        or role_plan["raw_reasoning_allowed"] is not False
    ):
        raise CreativePilotContractError("workspace debate policy is invalid")
    conditional_roles = role_plan["conditional_roles"]
    if not isinstance(conditional_roles, list):
        raise CreativePilotContractError("workspace conditional roles must be a list")
    for row in conditional_roles:
        if not isinstance(row, Mapping):
            raise CreativePilotContractError("workspace conditional role row must be an object")
        _exact_keys(row, {"role", "fallback"}, "workspace.conditional_role")
        _token(row["role"], "workspace.conditional_role.role")
        _bounded_text(row["fallback"], "workspace.conditional_role.fallback")

    assignments = payload["assignments"]
    if not isinstance(assignments, list) or not assignments:
        raise CreativePilotContractError("workspace assignments must be a non-empty list")
    assignment_ids: set[str] = set()
    independent_roles: list[str] = []
    for row in assignments:
        if not isinstance(row, Mapping):
            raise CreativePilotContractError("workspace assignment must be an object")
        _exact_keys(
            row,
            {
                "assignment_id",
                "role",
                "phase",
                "review_mode",
                "diff_expected",
                "review_question",
                "input_fingerprint",
                "input_refs",
            },
            "workspace.assignment",
        )
        assignment_id = _token(row["assignment_id"], "workspace.assignment.assignment_id")
        if assignment_id in assignment_ids:
            raise CreativePilotContractError("workspace assignment IDs must be unique")
        assignment_ids.add(assignment_id)
        role = _token(row["role"], "workspace.assignment.role")
        assignment_phase = _token(row["phase"], "workspace.assignment.phase", allowed=ROLE_PHASES)
        if row["review_mode"] != "specification_planning" or row["diff_expected"] is not False:
            raise CreativePilotContractError("workspace assignment exceeded planning authority")
        _bounded_text(row["review_question"], "workspace.assignment.review_question")
        _fingerprint(row["input_fingerprint"], "workspace.assignment.input_fingerprint")
        refs = _string_list(
            row["input_refs"], "workspace.assignment.input_refs", min_items=1, max_items=32
        )
        parts = assignment_id.split(":", 2)
        if len(parts) != 3 or parts[0] != assignment_phase or not parts[1].isdigit():
            raise CreativePilotContractError("workspace assignment ID shape is invalid")
        expected_index = int(parts[1])
        expected = _build_assignment(
            intent=intent,
            index=expected_index,
            role=role,
            phase=assignment_phase,
            input_refs=refs,
        )
        if dict(row) != expected:
            raise CreativePilotContractError("workspace assignment identity mismatch")
        if assignment_phase == "independent":
            independent_roles.append(role)
    if sorted(independent_roles) != sorted(required_roles):
        raise CreativePilotContractError(
            "independent assignments must exactly cover required roles"
        )

    role_results = payload["role_results"]
    if not isinstance(role_results, list):
        raise CreativePilotContractError("workspace role_results must be a list")
    result_ids: set[str] = set()
    assignments_by_id = {row["assignment_id"]: row for row in assignments}
    for raw_result in role_results:
        if not isinstance(raw_result, Mapping):
            raise CreativePilotContractError("workspace role result must be an object")
        result = validate_role_result(raw_result)
        if result["result_id"] in result_ids:
            raise CreativePilotContractError("workspace role result IDs must be unique")
        result_ids.add(result["result_id"])
        assignment = assignments_by_id.get(result["assignment_id"])
        if assignment is None:
            raise CreativePilotContractError("workspace role result references unknown assignment")
        if any(result[key] != assignment[key] for key in ("role", "phase")):
            raise CreativePilotContractError("workspace role result assignment mismatch")
        if result["assignment_input_fingerprint"] != assignment["input_fingerprint"]:
            raise CreativePilotContractError("workspace role result input mismatch")
        if (
            result["workspace_id"] != payload["workspace_id"]
            or result["workspace_intent_fingerprint"] != payload["intent_fingerprint"]
        ):
            raise CreativePilotContractError("workspace role result lineage mismatch")
        if (
            not isinstance(result["workspace_revision"], int)
            or result["workspace_revision"] < 1
            or result["workspace_revision"] > payload["revision"]
            or result["target_manifest_fingerprint"] != target["manifest_fingerprint"]
            or result["hypothesis_id"] != intent["hypothesis_id"]
        ):
            raise CreativePilotContractError("workspace role result source binding mismatch")
        if any(
            _evidence_path(ref, "role_result.evidence_refs") not in set(evidence_allowlist)
            for ref in cast(Sequence[str], result["evidence_refs"])
        ):
            raise CreativePilotContractError("workspace role result evidence is outside allowlist")
        expected_dispatch = _phase_dispatch_fingerprint_unchecked(payload, phase=result["phase"])
        if result["dispatch_input_fingerprint"] != expected_dispatch:
            raise CreativePilotContractError("workspace role result dispatch mismatch")

    if not isinstance(payload["conflicts"], list):
        raise CreativePilotContractError("workspace conflicts must be a list")
    for conflict in payload["conflicts"]:
        if not isinstance(conflict, Mapping):
            raise CreativePilotContractError("workspace conflict must be an object")
        _exact_keys(
            conflict,
            {"conflict_id", "claim_id", "stances", "oracle_gap_sets"},
            "workspace.conflict",
        )
        if conflict["conflict_id"] != f"claim:{conflict['claim_id']}":
            raise CreativePilotContractError("workspace conflict identity mismatch")
    expected_conflicts = _derive_conflicts(cast(Sequence[Mapping[str, Any]], role_results))
    if payload["conflicts"] and payload["conflicts"] != expected_conflicts:
        raise CreativePilotContractError("workspace conflicts do not match role results")

    synthesis_ref = payload["synthesis_ref"]
    if synthesis_ref is not None:
        if not isinstance(synthesis_ref, Mapping):
            raise CreativePilotContractError("workspace synthesis_ref must be an object or null")
        _exact_keys(
            synthesis_ref,
            {"synthesis_id", "synthesis_fingerprint", "reviewed_revision_fingerprint"},
            "workspace.synthesis_ref",
        )
        _token(synthesis_ref["synthesis_id"], "workspace.synthesis_ref.synthesis_id")
        _fingerprint(
            synthesis_ref["synthesis_fingerprint"], "workspace.synthesis_ref.synthesis_fingerprint"
        )
        _fingerprint(
            synthesis_ref["reviewed_revision_fingerprint"],
            "workspace.synthesis_ref.reviewed_revision_fingerprint",
        )
    handoff_ref = payload["handoff_ref"]
    if handoff_ref is not None:
        if not isinstance(handoff_ref, Mapping):
            raise CreativePilotContractError("workspace handoff_ref must be an object or null")
        _exact_keys(
            handoff_ref,
            {
                "approval_id",
                "approval_fingerprint",
                "bridge_id",
                "bridge_fingerprint",
                "candidate_id",
                "candidate_fingerprint",
            },
            "workspace.handoff_ref",
        )
        for key in ("approval_id", "bridge_id", "candidate_id"):
            _token(handoff_ref[key], f"workspace.handoff_ref.{key}")
        for key in ("approval_fingerprint", "bridge_fingerprint", "candidate_fingerprint"):
            _fingerprint(handoff_ref[key], f"workspace.handoff_ref.{key}")
    state = payload["state"]
    if not isinstance(state, Mapping) or set(state) != {"phase", "terminal"}:
        raise CreativePilotContractError("workspace state is invalid")
    phase = _token(state["phase"], "workspace.state.phase", allowed=PHASES)
    if state["terminal"] is not (phase in TERMINAL_PHASES):
        raise CreativePilotContractError("workspace terminal flag does not match phase")
    if (
        phase
        in {
            "rebuttal_required",
            "rebuttal_complete",
            "synthesis_ready",
            "synthesized",
            "approved_for_pr1_spec",
        }
        and payload["conflicts"] != expected_conflicts
    ):
        raise CreativePilotContractError("workspace conflict state is incomplete or tampered")
    independent_ids = {row["assignment_id"] for row in assignments if row["phase"] == "independent"}
    rebuttal_ids = {row["assignment_id"] for row in assignments if row["phase"] == "rebuttal"}
    observed_ids = {row["assignment_id"] for row in role_results}
    if phase in {
        "independent_complete",
        "rebuttal_required",
        "rebuttal_complete",
        "synthesis_ready",
        "synthesized",
        "approved_for_pr1_spec",
    } and not independent_ids.issubset(observed_ids):
        raise CreativePilotContractError("workspace phase requires complete independent coverage")
    if (
        phase in {"rebuttal_complete", "synthesis_ready", "synthesized", "approved_for_pr1_spec"}
        and rebuttal_ids
        and not rebuttal_ids.issubset(observed_ids)
    ):
        raise CreativePilotContractError("workspace phase requires complete rebuttal coverage")
    if phase == "synthesized" and synthesis_ref is None:
        raise CreativePilotContractError("synthesized workspace requires synthesis_ref")
    if phase == "approved_for_pr1_spec" and (synthesis_ref is None or handoff_ref is None):
        raise CreativePilotContractError("approved workspace requires synthesis and handoff refs")
    if (
        not isinstance(payload["revision"], int)
        or isinstance(payload["revision"], bool)
        or payload["revision"] < 1
    ):
        raise CreativePilotContractError("workspace revision must be a positive integer")
    if payload["rebuttal_rounds_used"] not in {0, 1} or isinstance(
        payload["rebuttal_rounds_used"], bool
    ):
        raise CreativePilotContractError("workspace rebuttal rounds must be zero or one")
    if bool(rebuttal_ids) is not (payload["rebuttal_rounds_used"] == 1):
        raise CreativePilotContractError("workspace rebuttal assignments and round count differ")
    _fingerprint(payload["intent_fingerprint"], "workspace.intent_fingerprint")
    _fingerprint(payload["revision_fingerprint"], "workspace.revision_fingerprint")
    if payload["intent_fingerprint"] != fingerprint_payload(
        cast(dict[str, Any], dict(cast(Mapping[str, Any], payload["intent"])))
    ):
        raise CreativePilotContractError("workspace intent fingerprint mismatch")
    body = {
        key: value
        for key, value in payload.items()
        if key
        not in {"workspace_id", "intent_fingerprint", "revision_fingerprint", "idempotency_key"}
    }
    if payload["revision_fingerprint"] != fingerprint_payload(body):
        raise CreativePilotContractError("workspace revision fingerprint mismatch")
    if phase in {"synthesized", "approved_for_pr1_spec"}:
        reviewed_revision = int(payload["revision"]) - (
            2 if phase == "approved_for_pr1_spec" else 1
        )
        if reviewed_revision < 1:
            raise CreativePilotContractError("workspace synthesis revision lineage is invalid")
        reviewed_body = dict(body)
        reviewed_body["state"] = {"phase": "synthesis_ready", "terminal": False}
        reviewed_body["revision"] = reviewed_revision
        reviewed_body["synthesis_ref"] = None
        reviewed_body["handoff_ref"] = None
        expected_reviewed = fingerprint_payload(reviewed_body)
        if synthesis_ref["reviewed_revision_fingerprint"] != expected_reviewed:
            raise CreativePilotContractError("workspace synthesis reviewed revision mismatch")
    initial_body = {
        **_base_artifact(WORKSPACE_TYPE),
        "intent": dict(intent),
        "target_manifest": target,
        "evidence_allowlist": list(evidence_allowlist),
        "role_plan": dict(role_plan),
        "assignments": [row for row in assignments if row["phase"] == "independent"],
        "role_results": [],
        "conflicts": [],
        "synthesis_ref": None,
        "handoff_ref": None,
        "rebuttal_rounds_used": 0,
        "state": {"phase": "independent_dispatched", "terminal": False},
        "revision": 1,
        "authority": dict(AUTHORITY),
        "sanitized": True,
    }
    expected_workspace_id, expected_key = _identity(
        initial_body,
        artifact_type=WORKSPACE_TYPE,
        upstream_ids=(str(intent["packet_id"]), str(intent["hypothesis_id"])),
    )
    if (
        payload["workspace_id"] != expected_workspace_id
        or payload["idempotency_key"] != expected_key
    ):
        raise CreativePilotContractError("workspace stable identity mismatch")
    return dict(payload)


def build_role_result(
    *,
    workspace: Mapping[str, Any],
    assignment_id: str,
    stance: str,
    claim_ids: Sequence[str],
    evidence_refs: Sequence[str],
    blocker_codes: Sequence[str],
    oracle_gap_codes: Sequence[str],
    peer_result_refs: Sequence[str] = (),
) -> dict[str, Any]:
    ws = validate_workspace(workspace)
    assignment = next(
        (row for row in ws["assignments"] if row["assignment_id"] == assignment_id), None
    )
    if assignment is None:
        raise CreativePilotContractError("role result assignment does not exist")
    phase = assignment["phase"]
    peers = _string_list(list(peer_result_refs), "peer_result_refs", max_items=16)
    if phase == "independent" and peers:
        raise CreativePilotContractError("independent role results must not reference peers")
    if phase == "rebuttal":
        allowed_conflicts = {row["conflict_id"] for row in ws["conflicts"]}
        if not peers or not set(peers).issubset(allowed_conflicts):
            raise CreativePilotContractError(
                "rebuttal peer refs must name only coordinator-issued conflict IDs"
            )
    normalized_stance = _token(stance, "stance", allowed=STANCES)
    normalized_blockers = _string_list(list(blocker_codes), "blocker_codes", max_items=16)
    normalized_oracle_gaps = _string_list(list(oracle_gap_codes), "oracle_gap_codes", max_items=16)
    if normalized_stance == "pass" and (normalized_blockers or normalized_oracle_gaps):
        raise CreativePilotContractError("pass stance must not carry hard blockers or oracle gaps")
    normalized_evidence_refs = _string_list(
        list(evidence_refs), "evidence_refs", min_items=1, max_items=32
    )
    allowlist = set(cast(Sequence[str], ws["evidence_allowlist"]))
    if any(
        _evidence_path(ref, "evidence_refs") not in allowlist for ref in normalized_evidence_refs
    ):
        raise CreativePilotContractError("role result evidence ref is outside workspace allowlist")
    body = {
        **_base_artifact(ROLE_RESULT_TYPE),
        "workspace_id": ws["workspace_id"],
        "workspace_intent_fingerprint": ws["intent_fingerprint"],
        "workspace_revision": ws["revision"],
        "assignment_id": assignment_id,
        "assignment_input_fingerprint": assignment["input_fingerprint"],
        "dispatch_input_fingerprint": phase_dispatch_fingerprint(ws, phase=phase),
        "target_manifest_fingerprint": ws["target_manifest"]["manifest_fingerprint"],
        "hypothesis_id": ws["intent"]["hypothesis_id"],
        "role": assignment["role"],
        "phase": phase,
        "stance": normalized_stance,
        "claim_ids": _string_list(list(claim_ids), "claim_ids", min_items=1, max_items=24),
        "evidence_refs": normalized_evidence_refs,
        "blocker_codes": normalized_blockers,
        "oracle_gap_codes": normalized_oracle_gaps,
        "peer_result_refs": peers,
        "authority": dict(AUTHORITY),
        "sanitized": True,
    }
    result_id, idempotency_key = _identity(
        body, artifact_type=ROLE_RESULT_TYPE, upstream_ids=(str(ws["workspace_id"]), assignment_id)
    )
    return {**body, "result_id": result_id, "idempotency_key": idempotency_key}


def validate_role_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "artifact_type",
        "policy_version",
        "surface_policy",
        "result_id",
        "idempotency_key",
        "workspace_id",
        "workspace_intent_fingerprint",
        "workspace_revision",
        "assignment_id",
        "assignment_input_fingerprint",
        "target_manifest_fingerprint",
        "dispatch_input_fingerprint",
        "hypothesis_id",
        "role",
        "phase",
        "stance",
        "claim_ids",
        "evidence_refs",
        "blocker_codes",
        "oracle_gap_codes",
        "peer_result_refs",
        "authority",
        "sanitized",
    }
    _exact_keys(payload, required, "CreativePilotRoleResult")
    _validate_header(payload, ROLE_RESULT_TYPE)
    _token(payload["phase"], "role_result.phase", allowed=ROLE_PHASES)
    _token(payload["stance"], "role_result.stance", allowed=STANCES)
    for key in (
        "workspace_intent_fingerprint",
        "assignment_input_fingerprint",
        "dispatch_input_fingerprint",
        "target_manifest_fingerprint",
    ):
        _fingerprint(payload[key], f"role_result.{key}")
    for key in (
        "claim_ids",
        "evidence_refs",
        "blocker_codes",
        "oracle_gap_codes",
        "peer_result_refs",
    ):
        _string_list(
            payload[key],
            f"role_result.{key}",
            min_items=1 if key in {"claim_ids", "evidence_refs"} else 0,
            max_items=32,
        )
    if payload["phase"] == "independent" and payload["peer_result_refs"]:
        raise CreativePilotContractError("independent role results must not reference peers")
    if payload["stance"] == "pass" and (payload["blocker_codes"] or payload["oracle_gap_codes"]):
        raise CreativePilotContractError("pass stance must not carry hard blockers or oracle gaps")
    _validate_artifact_identity(
        payload,
        artifact_type=ROLE_RESULT_TYPE,
        id_key="result_id",
        upstream_ids=(str(payload["workspace_id"]), str(payload["assignment_id"])),
    )
    return dict(payload)


def ingest_role_result(
    workspace: Mapping[str, Any], role_result: Mapping[str, Any]
) -> dict[str, Any]:
    ws = validate_workspace(workspace)
    result = validate_role_result(role_result)
    if (
        result["workspace_id"] != ws["workspace_id"]
        or result["workspace_intent_fingerprint"] != ws["intent_fingerprint"]
    ):
        raise CreativePilotContractError("role result workspace binding mismatch")
    assignment = next(
        (row for row in ws["assignments"] if row["assignment_id"] == result["assignment_id"]), None
    )
    if assignment is None or any(result[key] != assignment[key] for key in ("role", "phase")):
        raise CreativePilotContractError("role result assignment binding mismatch")
    if result["assignment_input_fingerprint"] != assignment["input_fingerprint"]:
        raise CreativePilotContractError("role result input fingerprint mismatch")
    if result["dispatch_input_fingerprint"] != phase_dispatch_fingerprint(
        ws, phase=result["phase"]
    ):
        raise CreativePilotContractError("role result dispatch fingerprint mismatch")
    existing = [
        row for row in ws["role_results"] if row["assignment_id"] == result["assignment_id"]
    ]
    if existing:
        if existing[0] == result:
            return ws
        raise CreativePilotContractError("conflicting role-result replay")
    updated = dict(ws)
    updated["role_results"] = [*ws["role_results"], result]
    required_ids = {
        row["assignment_id"] for row in ws["assignments"] if row["phase"] == result["phase"]
    }
    observed_ids = {
        row["assignment_id"] for row in updated["role_results"] if row["phase"] == result["phase"]
    }
    if result["phase"] == "independent":
        phase = "independent_complete" if required_ids <= observed_ids else "independent_dispatched"
    else:
        phase = "rebuttal_complete" if required_ids <= observed_ids else "rebuttal_required"
    return _next_revision(updated, phase=phase)


def detect_conflicts(workspace: Mapping[str, Any]) -> dict[str, Any]:
    ws = validate_workspace(workspace)
    if ws["state"]["phase"] not in {"independent_complete", "rebuttal_complete"}:
        raise CreativePilotContractError("conflicts can be detected only after role coverage")
    conflicts = _derive_conflicts(cast(Sequence[Mapping[str, Any]], ws["role_results"]))
    updated = dict(ws)
    updated["conflicts"] = conflicts
    if conflicts and ws["rebuttal_rounds_used"] == 0:
        phase = "rebuttal_required"
    else:
        phase = "synthesis_ready"
    return _next_revision(updated, phase=phase)


def add_rebuttal_assignments(workspace: Mapping[str, Any]) -> dict[str, Any]:
    ws = validate_workspace(workspace)
    if ws["state"]["phase"] != "rebuttal_required" or ws["rebuttal_rounds_used"] != 0:
        raise CreativePilotContractError("only one targeted rebuttal round is allowed")
    conflict_ids = [row["conflict_id"] for row in ws["conflicts"]]
    roles = sorted(
        {
            row["role"]
            for row in ws["role_results"]
            if row["stance"] != "pass" or row["blocker_codes"] or row["oracle_gap_codes"]
        }
    )
    if not roles:
        roles = list(REQUIRED_ROLES)
    new_assignments = [
        _build_assignment(
            intent=ws["intent"],
            index=index,
            role=role,
            phase="rebuttal",
            input_refs=conflict_ids,
        )
        for index, role in enumerate(roles, start=1)
    ]
    updated = dict(ws)
    updated["assignments"] = [*ws["assignments"], *new_assignments]
    updated["rebuttal_rounds_used"] = 1
    return _next_revision(updated, phase="rebuttal_required")


def build_synthesis(workspace: Mapping[str, Any]) -> dict[str, Any]:
    ws = validate_workspace(workspace)
    required_assignments = [row for row in ws["assignments"] if row["phase"] == "independent"]
    results_by_assignment = {row["assignment_id"]: row for row in ws["role_results"]}
    missing = [
        row["role"]
        for row in required_assignments
        if row["assignment_id"] not in results_by_assignment
    ]
    effective_by_role: dict[str, Mapping[str, Any]] = {}
    for row in ws["role_results"]:
        if row["phase"] == "independent":
            effective_by_role[row["role"]] = row
    for row in ws["role_results"]:
        if row["phase"] == "rebuttal":
            effective_by_role[row["role"]] = row
    effective_results = list(effective_by_role.values())
    security_reject = any(
        row["role"] == "security-auditor" and row["stance"] == "reject" for row in effective_results
    )
    oracle_gaps = sorted({gap for row in effective_results for gap in row["oracle_gap_codes"]})
    blockers = sorted({code for row in effective_results for code in row["blocker_codes"]})
    unresolved_conflicts = bool(ws["conflicts"] and ws["rebuttal_rounds_used"] == 0)
    if missing or security_reject or oracle_gaps:
        evidence = "insufficient"
        disagreement = "material"
        decision = "hold"
    elif unresolved_conflicts:
        evidence = "partial"
        disagreement = "material"
        decision = "revise"
    elif any(row["stance"] in {"revise", "reject", "abstain"} for row in effective_results):
        evidence = "partial"
        disagreement = "bounded" if ws["rebuttal_rounds_used"] == 1 else "material"
        decision = "revise"
    else:
        evidence = "complete"
        disagreement = "bounded" if ws["rebuttal_rounds_used"] == 1 else "none"
        decision = "approve"
    body = {
        **_base_artifact(SYNTHESIS_TYPE),
        "workspace_id": ws["workspace_id"],
        "workspace_intent_fingerprint": ws["intent_fingerprint"],
        "workspace_revision_fingerprint": ws["revision_fingerprint"],
        "hypothesis_id": ws["intent"]["hypothesis_id"],
        "hypothesis_fingerprint": ws["intent"]["hypothesis_fingerprint"],
        "target_manifest_fingerprint": ws["target_manifest"]["manifest_fingerprint"],
        "base_sha": ws["target_manifest"]["base_sha"],
        "head_sha": ws["target_manifest"]["head_sha"],
        "role_result_ids": sorted(row["result_id"] for row in ws["role_results"]),
        "role_coverage": {
            "required": sorted(row["role"] for row in required_assignments),
            "completed": sorted(
                row["role"] for row in ws["role_results"] if row["phase"] == "independent"
            ),
            "missing": sorted(missing),
        },
        "conflict_ids": sorted(row["conflict_id"] for row in ws["conflicts"]),
        "blocker_codes": blockers,
        "oracle_gap_codes": oracle_gaps,
        "evidence_sufficiency": evidence,
        "disagreement_class": disagreement,
        "decision": decision,
        "human_approval_required": True,
        "next_allowed_action": "approve_handoff" if decision == "approve" else "revise_or_stop",
        "authority": dict(AUTHORITY),
        "sanitized": True,
    }
    synthesis_id, idempotency_key = _identity(
        body,
        artifact_type=SYNTHESIS_TYPE,
        upstream_ids=(str(ws["workspace_id"]), *body["role_result_ids"]),
    )
    return {**body, "synthesis_id": synthesis_id, "idempotency_key": idempotency_key}


def validate_synthesis(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "artifact_type",
        "policy_version",
        "surface_policy",
        "synthesis_id",
        "idempotency_key",
        "workspace_id",
        "workspace_intent_fingerprint",
        "workspace_revision_fingerprint",
        "hypothesis_id",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
        "base_sha",
        "head_sha",
        "role_result_ids",
        "role_coverage",
        "conflict_ids",
        "blocker_codes",
        "oracle_gap_codes",
        "evidence_sufficiency",
        "disagreement_class",
        "decision",
        "human_approval_required",
        "next_allowed_action",
        "authority",
        "sanitized",
    }
    _exact_keys(payload, required, "CreativePilotSynthesis")
    _validate_header(payload, SYNTHESIS_TYPE)
    _token(payload["evidence_sufficiency"], "evidence_sufficiency", allowed=EVIDENCE_SUFFICIENCY)
    _token(payload["disagreement_class"], "disagreement_class", allowed=DISAGREEMENT_CLASSES)
    _token(payload["decision"], "decision", allowed=DECISIONS)
    coverage = payload["role_coverage"]
    if not isinstance(coverage, Mapping):
        raise CreativePilotContractError("synthesis role coverage must be an object")
    _exact_keys(coverage, {"required", "completed", "missing"}, "synthesis.role_coverage")
    required_roles = set(
        _string_list(coverage["required"], "synthesis.role_coverage.required", min_items=3)
    )
    completed_roles = set(_string_list(coverage["completed"], "synthesis.role_coverage.completed"))
    missing_roles = set(_string_list(coverage["missing"], "synthesis.role_coverage.missing"))
    if missing_roles != required_roles - completed_roles:
        raise CreativePilotContractError("synthesis missing-role coverage is inconsistent")
    for key in ("role_result_ids", "conflict_ids", "blocker_codes", "oracle_gap_codes"):
        _string_list(payload[key], f"synthesis.{key}", max_items=64)
    for key in (
        "workspace_intent_fingerprint",
        "workspace_revision_fingerprint",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
    ):
        _fingerprint(payload[key], f"synthesis.{key}")
    for key in ("base_sha", "head_sha"):
        _sha(payload[key], f"synthesis.{key}")
    if payload["human_approval_required"] is not True:
        raise CreativePilotContractError("synthesis must require human approval")
    if payload["decision"] == "approve" and (
        payload["evidence_sufficiency"] != "complete" or payload["disagreement_class"] == "material"
    ):
        raise CreativePilotContractError(
            "approve requires complete evidence and no material disagreement"
        )
    _validate_artifact_identity(
        payload,
        artifact_type=SYNTHESIS_TYPE,
        id_key="synthesis_id",
        upstream_ids=(
            str(payload["workspace_id"]),
            *cast(Sequence[str], payload["role_result_ids"]),
        ),
    )
    return dict(payload)


def apply_synthesis_transition(
    workspace: Mapping[str, Any], synthesis: Mapping[str, Any]
) -> dict[str, Any]:
    """Advance workspace state from one validated deterministic synthesis."""

    ws = validate_workspace(workspace)
    syn = validate_synthesis(synthesis)
    if syn != build_synthesis(ws):
        raise CreativePilotContractError("synthesis is not deterministic workspace truth")
    if (
        syn["workspace_id"] != ws["workspace_id"]
        or syn["workspace_intent_fingerprint"] != ws["intent_fingerprint"]
    ):
        raise CreativePilotContractError("synthesis workspace binding mismatch")
    if syn["workspace_revision_fingerprint"] != ws["revision_fingerprint"]:
        raise CreativePilotContractError("synthesis reviewed a stale workspace revision")
    phase_by_decision = {
        "approve": "synthesized",
        "revise": "revise",
        "reject": "reject",
        "hold": "blocked",
    }
    updated = dict(ws)
    updated["synthesis_ref"] = {
        "synthesis_id": syn["synthesis_id"],
        "synthesis_fingerprint": fingerprint_payload(syn),
        "reviewed_revision_fingerprint": syn["workspace_revision_fingerprint"],
    }
    return _next_revision(updated, phase=phase_by_decision[str(syn["decision"])])


def _reviewed_synthesis_ready_workspace(
    workspace: Mapping[str, Any], synthesis: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the canonical workspace revision reviewed by one synthesis."""

    ws = validate_workspace(workspace)
    syn = validate_synthesis(synthesis)
    phase = ws["state"]["phase"]
    if phase == "synthesis_ready":
        reviewed = ws
    else:
        expected_phase = {
            "approve": "synthesized",
            "revise": "revise",
            "hold": "blocked",
        }.get(str(syn["decision"]))
        if phase not in {"synthesized", "revise", "blocked"} or phase != expected_phase:
            raise CreativePilotContractError(
                "synthesis decision does not match the post-synthesis workspace phase"
            )
        expected_ref = {
            "synthesis_id": syn["synthesis_id"],
            "synthesis_fingerprint": fingerprint_payload(syn),
            "reviewed_revision_fingerprint": syn["workspace_revision_fingerprint"],
        }
        if ws["synthesis_ref"] != expected_ref:
            raise CreativePilotContractError(
                "synthesis is not the canonical post-synthesis workspace truth"
            )
        if ws["handoff_ref"] is not None:
            raise CreativePilotContractError(
                "post-synthesis workspace must not carry a handoff reference"
            )
        reviewed_revision = int(ws["revision"]) - 1
        if reviewed_revision < 1:
            raise CreativePilotContractError("workspace synthesis revision lineage is invalid")
        reconstructed = dict(ws)
        reconstructed["state"] = {"phase": "synthesis_ready", "terminal": False}
        reconstructed["revision"] = reviewed_revision
        reconstructed["synthesis_ref"] = None
        reconstructed["handoff_ref"] = None
        reconstructed["revision_fingerprint"] = syn["workspace_revision_fingerprint"]
        reviewed = validate_workspace(reconstructed)
    if build_synthesis(reviewed) != syn:
        raise CreativePilotContractError("synthesis is not deterministic workspace truth")
    return reviewed


def terminate_workspace(
    workspace: Mapping[str, Any], *, phase: str, reason_code: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stop an unstarted or nonterminal local pilot without granting authority."""

    ws = validate_workspace(workspace)
    terminal_phase = _token(
        phase,
        "terminal phase",
        allowed=frozenset({"revise", "reject", "blocked"}),
    )
    reason = _token(reason_code, "reason_code")
    if ws["state"]["terminal"]:
        raise CreativePilotContractError("terminal workspace cannot be stopped again")
    updated = dict(ws)
    updated["state"] = {"phase": terminal_phase, "terminal": True}
    updated["revision"] = int(ws["revision"]) + 1
    body = {
        key: value
        for key, value in updated.items()
        if key
        not in {
            "workspace_id",
            "intent_fingerprint",
            "revision_fingerprint",
            "idempotency_key",
        }
    }
    updated["revision_fingerprint"] = fingerprint_payload(body)
    disposition = {
        "workspace_id": ws["workspace_id"],
        "previous_revision_fingerprint": ws["revision_fingerprint"],
        "terminal_revision_fingerprint": updated["revision_fingerprint"],
        "phase": terminal_phase,
        "reason_code": reason,
        "authority": {"terminate_local_pilot": True, "generate_patch": False},
    }
    return validate_workspace(updated), disposition


def build_approval_v2(
    *, workspace: Mapping[str, Any], synthesis: Mapping[str, Any], approved_by: str
) -> dict[str, Any]:
    ws = validate_workspace(workspace)
    syn = validate_synthesis(synthesis)
    if syn["decision"] != "approve":
        raise CreativePilotContractError("only an approve synthesis may be handed off")
    if ws["state"]["phase"] != "synthesized" or ws["synthesis_ref"] is None:
        raise CreativePilotContractError("approval requires a synthesized workspace")
    synthesis_fingerprint = fingerprint_payload(syn)
    expected_ref = {
        "synthesis_id": syn["synthesis_id"],
        "synthesis_fingerprint": synthesis_fingerprint,
        "reviewed_revision_fingerprint": syn["workspace_revision_fingerprint"],
    }
    if ws["synthesis_ref"] != expected_ref:
        raise CreativePilotContractError(
            "approval synthesis is not the workspace canonical synthesis"
        )
    reviewed_workspace = dict(ws)
    reviewed_workspace["state"] = {"phase": "synthesis_ready", "terminal": False}
    reviewed_workspace["revision"] = int(ws["revision"]) - 1
    reviewed_workspace["synthesis_ref"] = None
    reviewed_workspace["handoff_ref"] = None
    reviewed_workspace["revision_fingerprint"] = syn["workspace_revision_fingerprint"]
    expected_synthesis = build_synthesis(validate_workspace(reviewed_workspace))
    if expected_synthesis != syn:
        raise CreativePilotContractError("approval synthesis is not deterministic workspace truth")
    for key, observed in (
        ("workspace_id", ws["workspace_id"]),
        ("workspace_intent_fingerprint", ws["intent_fingerprint"]),
        ("target_manifest_fingerprint", ws["target_manifest"]["manifest_fingerprint"]),
        ("hypothesis_fingerprint", ws["intent"]["hypothesis_fingerprint"]),
        ("base_sha", ws["target_manifest"]["base_sha"]),
        ("head_sha", ws["target_manifest"]["head_sha"]),
    ):
        if syn[key] != observed:
            raise CreativePilotContractError(f"synthesis {key} binding mismatch")
    body = {
        **_base_artifact(APPROVAL_TYPE),
        "workspace_id": ws["workspace_id"],
        "workspace_intent_fingerprint": ws["intent_fingerprint"],
        "workspace_reviewed_revision_fingerprint": syn["workspace_revision_fingerprint"],
        "workspace_synthesized_revision_fingerprint": ws["revision_fingerprint"],
        "synthesis_id": syn["synthesis_id"],
        "synthesis_fingerprint": synthesis_fingerprint,
        "source_hypothesis_packet_id": ws["intent"]["packet_id"],
        "hypothesis_id": ws["intent"]["hypothesis_id"],
        "hypothesis_fingerprint": ws["intent"]["hypothesis_fingerprint"],
        "target_manifest_fingerprint": ws["target_manifest"]["manifest_fingerprint"],
        "base_sha": ws["target_manifest"]["base_sha"],
        "head_sha": ws["target_manifest"]["head_sha"],
        "approved_target_surfaces": [row["path"] for row in ws["target_manifest"]["files"]],
        "approved_by": _token(approved_by, "approved_by"),
        "decision": "approve_for_pr1_specification",
        "generate_patch": False,
        "next_step": "create_pr1_specification",
        "authority": dict(AUTHORITY),
        "sanitized": True,
    }
    approval_id, idempotency_key = _identity(
        body,
        artifact_type=APPROVAL_TYPE,
        upstream_ids=(str(syn["synthesis_id"]), str(ws["workspace_id"])),
    )
    return {**body, "approval_id": approval_id, "idempotency_key": idempotency_key}


def validate_approval_v2(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "artifact_type",
        "policy_version",
        "surface_policy",
        "approval_id",
        "idempotency_key",
        "workspace_id",
        "workspace_intent_fingerprint",
        "workspace_reviewed_revision_fingerprint",
        "workspace_synthesized_revision_fingerprint",
        "synthesis_id",
        "synthesis_fingerprint",
        "source_hypothesis_packet_id",
        "hypothesis_id",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
        "base_sha",
        "head_sha",
        "approved_target_surfaces",
        "approved_by",
        "decision",
        "generate_patch",
        "next_step",
        "authority",
        "sanitized",
    }
    _exact_keys(payload, required, "CreativeHypothesisApprovalV2")
    _validate_header(payload, APPROVAL_TYPE)
    if (
        payload["decision"] != "approve_for_pr1_specification"
        or payload["generate_patch"] is not False
    ):
        raise CreativePilotContractError("approval v2 may authorize PR-1 specification only")
    if payload["next_step"] != "create_pr1_specification":
        raise CreativePilotContractError("approval v2 next step is invalid")
    for key in (
        "workspace_intent_fingerprint",
        "workspace_reviewed_revision_fingerprint",
        "workspace_synthesized_revision_fingerprint",
        "synthesis_fingerprint",
        "hypothesis_fingerprint",
        "target_manifest_fingerprint",
    ):
        _fingerprint(payload[key], f"approval.{key}")
    for key in ("base_sha", "head_sha"):
        _sha(payload[key], f"approval.{key}")
    for key in (
        "workspace_id",
        "synthesis_id",
        "source_hypothesis_packet_id",
        "hypothesis_id",
        "approved_by",
    ):
        _token(payload[key], f"approval.{key}")
    surfaces = _string_list(
        payload["approved_target_surfaces"],
        "approval.approved_target_surfaces",
        min_items=1,
        max_items=2,
    )
    for surface in surfaces:
        normalized = _path(surface, "approval.approved_target_surfaces")
        if not normalized.startswith(ALLOWED_TARGET_PREFIXES):
            raise CreativePilotContractError("approval target is outside production-adjacent scope")
        try:
            validate_mutable_candidate_surface([normalized])
        except ValueError as exc:
            raise CreativePilotContractError(str(exc)) from exc
    _validate_artifact_identity(
        payload,
        artifact_type=APPROVAL_TYPE,
        id_key="approval_id",
        upstream_ids=(str(payload["synthesis_id"]), str(payload["workspace_id"])),
    )
    return dict(payload)


def complete_handoff(
    *,
    workspace: Mapping[str, Any],
    approval: Mapping[str, Any],
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal a validated PR-1 handoff into the workspace terminal state."""

    ws = validate_workspace(workspace)
    approved = validate_approval_v2(approval)
    if ws["state"]["phase"] != "synthesized":
        raise CreativePilotContractError("handoff completion requires synthesized workspace")
    if (
        approved["workspace_id"] != ws["workspace_id"]
        or approved["workspace_intent_fingerprint"] != ws["intent_fingerprint"]
        or approved["workspace_synthesized_revision_fingerprint"] != ws["revision_fingerprint"]
    ):
        raise CreativePilotContractError("handoff approval workspace binding mismatch")
    if ws["synthesis_ref"] is None or any(
        approved[key] != ws["synthesis_ref"][key]
        for key in ("synthesis_id", "synthesis_fingerprint")
    ):
        raise CreativePilotContractError("handoff approval synthesis binding mismatch")
    # Lazy imports avoid a module cycle: the bridge builder consumes these pilot contracts.
    from scripts.orchestration.creative_code_contract import (
        CreativeCodeContractError,
        validate_creative_code_candidate_packet,
    )
    from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
        CreativeHypothesisSpecBridgeError,
        validate_creative_pilot_spec_bridge,
    )

    try:
        validated_bridge = validate_creative_pilot_spec_bridge(bridge)
        validated_candidate = validate_creative_code_candidate_packet(dict(candidate))
    except (CreativeCodeContractError, CreativeHypothesisSpecBridgeError) as exc:
        raise CreativePilotContractError(f"handoff artifact is invalid: {exc}") from exc
    expected_lineage = {
        "packet_id": ws["intent"]["packet_id"],
        "workspace_id": ws["workspace_id"],
        "workspace_intent_fingerprint": ws["intent_fingerprint"],
        "workspace_reviewed_revision_fingerprint": approved[
            "workspace_reviewed_revision_fingerprint"
        ],
        "workspace_synthesized_revision_fingerprint": ws["revision_fingerprint"],
        "hypothesis_id": ws["intent"]["hypothesis_id"],
        "hypothesis_fingerprint": ws["intent"]["hypothesis_fingerprint"],
        "target_manifest_fingerprint": ws["target_manifest"]["manifest_fingerprint"],
        "base_sha": ws["target_manifest"]["base_sha"],
        "head_sha": ws["target_manifest"]["head_sha"],
        "synthesis_id": approved["synthesis_id"],
        "synthesis_fingerprint": approved["synthesis_fingerprint"],
        "approval_id": approved["approval_id"],
        "approval_fingerprint": fingerprint_payload(approved),
    }
    if validated_bridge["lineage"] != expected_lineage:
        raise CreativePilotContractError("handoff bridge lineage mismatch")
    if validated_bridge["candidate_id"] != validated_candidate["candidate_id"]:
        raise CreativePilotContractError("handoff bridge candidate binding mismatch")
    if validated_bridge["candidate_fingerprint"] != fingerprint_payload(validated_candidate):
        raise CreativePilotContractError("handoff candidate fingerprint mismatch")
    updated = dict(ws)
    updated["handoff_ref"] = {
        "approval_id": approved["approval_id"],
        "approval_fingerprint": fingerprint_payload(approved),
        "bridge_id": validated_bridge["bridge_id"],
        "bridge_fingerprint": fingerprint_payload(validated_bridge),
        "candidate_id": validated_candidate["candidate_id"],
        "candidate_fingerprint": fingerprint_payload(validated_candidate),
    }
    return _next_revision(updated, phase="approved_for_pr1_spec")


def validate_retained_terminal_handoff(
    *,
    context_map: Mapping[str, Any],
    hypothesis_packet: Mapping[str, Any],
    workspace: Mapping[str, Any],
    synthesis: Mapping[str, Any],
    approval: Mapping[str, Any],
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    current_target_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Re-establish the complete retained adaptive handoff lineage."""

    try:
        context = validate_context_map_v2(context_map)
        packet = validate_hypothesis_packet_v2(hypothesis_packet, context_map=context)
        terminal = validate_workspace(workspace)
        syn = validate_synthesis(synthesis)
        approved = validate_approval_v2(approval)
        current_manifest = validate_target_manifest(current_target_manifest)
        if terminal["state"] != {"phase": "approved_for_pr1_spec", "terminal": True}:
            raise CreativePilotContractError(
                "retained workspace is not an approved terminal handoff"
            )
        if terminal["target_manifest"] != context["target_manifest"]:
            raise CreativePilotContractError("context target manifest does not match workspace")
        if terminal["intent"]["packet_id"] != packet["packet_id"]:
            raise CreativePilotContractError("packet id does not match workspace intent")
        hypothesis = next(
            (
                row
                for row in packet["hypotheses"]
                if row["hypothesis_id"] == terminal["intent"]["hypothesis_id"]
            ),
            None,
        )
        if (
            hypothesis is None
            or hypothesis["hypothesis_fingerprint"] != terminal["intent"]["hypothesis_fingerprint"]
        ):
            raise CreativePilotContractError("selected hypothesis does not match workspace intent")

        synthesized = dict(terminal)
        synthesized["state"] = {"phase": "synthesized", "terminal": False}
        synthesized["revision"] = int(terminal["revision"]) - 1
        synthesized["handoff_ref"] = None
        synthesized["revision_fingerprint"] = approved["workspace_synthesized_revision_fingerprint"]
        synthesized = validate_workspace(synthesized)
        expected_approval = build_approval_v2(
            workspace=synthesized,
            synthesis=syn,
            approved_by=str(approved["approved_by"]),
        )
        if approved != expected_approval:
            raise CreativePilotContractError("approval is not deterministic retained lineage")
        expected_terminal = complete_handoff(
            workspace=synthesized,
            approval=approved,
            bridge=bridge,
            candidate=candidate,
        )
        if terminal != expected_terminal:
            raise CreativePilotContractError(
                "workspace handoff_ref does not match bridge/candidate"
            )
        normalized_candidate = validate_source_candidate_packet(candidate)
        _assert_target_continuity(terminal["target_manifest"], current_manifest)
        expected_targets = [row["path"] for row in terminal["target_manifest"]["files"]]
        expected_oracles = list(terminal["target_manifest"]["immutable_oracles"])
        if normalized_candidate["target_surface"] != expected_targets:
            raise CreativePilotContractError("candidate target surface does not match manifest")
        if normalized_candidate["immutable_oracles"] != expected_oracles:
            raise CreativePilotContractError("candidate immutable oracles do not match manifest")
        required_tests = normalized_candidate["evidence_bundle"]["required_tests"]
        hypothesis_tests = {
            str(path) for path in hypothesis["tests_or_oracles"] if str(path).startswith("tests/")
        }
        if not hypothesis_tests.issubset(required_tests):
            raise CreativePilotContractError("candidate required tests omit hypothesis oracles")
        return {
            "context_map": context,
            "hypothesis_packet": packet,
            "workspace": terminal,
            "synthesis": syn,
            "approval": approved,
            "bridge": dict(bridge),
            "candidate": normalized_candidate,
            "current_target_manifest": current_manifest,
        }
    except (CreativePilotContractError, CreativeCodeSpecificationError) as exc:
        if str(exc).startswith("adaptive_source_lineage_mismatch:"):
            raise
        raise CreativePilotContractError(f"adaptive_source_lineage_mismatch: {exc}") from exc


def build_evidence_events(
    *, workspace: Mapping[str, Any], synthesis: Mapping[str, Any], produced_at: str
) -> list[EvidenceEvalEvent]:
    ws = validate_workspace(workspace)
    syn = validate_synthesis(synthesis)
    for key, observed in (
        ("workspace_id", ws["workspace_id"]),
        ("workspace_intent_fingerprint", ws["intent_fingerprint"]),
        ("hypothesis_id", ws["intent"]["hypothesis_id"]),
        ("hypothesis_fingerprint", ws["intent"]["hypothesis_fingerprint"]),
        ("target_manifest_fingerprint", ws["target_manifest"]["manifest_fingerprint"]),
        ("base_sha", ws["target_manifest"]["base_sha"]),
        ("head_sha", ws["target_manifest"]["head_sha"]),
    ):
        if syn[key] != observed:
            raise CreativePilotContractError(f"evidence synthesis {key} binding mismatch")
    _reviewed_synthesis_ready_workspace(ws, syn)
    source = ws["target_manifest"]["files"][0]["path"]
    producer = "creative_pilot_workspace"
    common = {
        "rail": "control_plane",
        "source_artifact": source,
        "asset_refs": (),
        "upstream_ids": (ws["workspace_id"], syn["synthesis_id"]),
        "policy_version": POLICY_VERSION,
        "producer_name": producer,
        "producer_version": SCHEMA_VERSION,
        "produced_at": produced_at,
    }
    payloads = [
        (
            "item_metadata",
            {
                "target_file_count": len(ws["target_manifest"]["files"]),
                "required_role_count": len(ws["role_plan"]["required_roles"]),
            },
        ),
        (
            "gate_metric",
            {
                "role_result_count": len(syn["role_result_ids"]),
                "conflict_count": len(syn["conflict_ids"]),
                "oracle_gap_count": len(syn["oracle_gap_codes"]),
            },
        ),
        (
            "gate_decision",
            {
                "decision": syn["decision"],
                "evidence_sufficiency": syn["evidence_sufficiency"],
                "disagreement_class": syn["disagreement_class"],
            },
        ),
    ]
    events: list[EvidenceEvalEvent] = []
    for event_type, metadata in payloads:
        event_fingerprint = fingerprint_payload(
            {
                "event_type": event_type,
                "workspace": ws["workspace_id"],
                "synthesis": syn["synthesis_id"],
                "metadata": metadata,
            }
        )
        event_key = build_idempotency_key(
            asset_type=event_type,
            rail="control_plane",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=event_fingerprint,
            upstream_ids=(ws["workspace_id"], syn["synthesis_id"]),
        )
        events.append(
            create_eval_event(
                event_type=cast(Any, event_type),
                fingerprint=event_fingerprint,
                idempotency_key=event_key,
                validation_status="valid" if syn["decision"] == "approve" else "deferred",
                metadata=metadata,
                **common,
            )
        )
    return events


def phase_dispatch_fingerprint(workspace: Mapping[str, Any], *, phase: str) -> str:
    """Fingerprint the immutable role-specific projection used for one phase."""

    ws = validate_workspace(workspace)
    return _phase_dispatch_fingerprint_unchecked(ws, phase=phase)


def validate_dispatch_phase(workspace: Mapping[str, Any], *, phase: str) -> dict[str, Any]:
    """Require one dispatch phase to match the workspace FSM exactly."""

    ws = validate_workspace(workspace)
    expected_state = {
        "independent": "independent_dispatched",
        "rebuttal": "rebuttal_required",
        "synthesis": "synthesis_ready",
    }
    if phase not in expected_state:
        raise CreativePilotContractError("creative pilot dispatch phase is unsupported")
    if ws["state"]["terminal"]:
        raise CreativePilotContractError("terminal workspace cannot be dispatched")
    if ws["state"]["phase"] != expected_state[phase]:
        raise CreativePilotContractError(
            f"{phase} dispatch requires workspace phase {expected_state[phase]}"
        )
    return ws


def validate_task_pilot_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact creative-pilot projection embedded in task packets."""

    _exact_keys(
        payload,
        {
            "schema_version",
            "workspace_id",
            "workspace_intent_fingerprint",
            "workspace_revision_fingerprint",
            "phase",
            "dispatch_input_fingerprint",
            "assignments",
            "authority",
        },
        "creative_pilot_context",
    )
    if payload["schema_version"] != "creative_pilot_context.v2":
        raise CreativePilotContractError("creative pilot task context schema is unsupported")
    _token(payload["workspace_id"], "creative_pilot_context.workspace_id")
    for key in (
        "workspace_intent_fingerprint",
        "workspace_revision_fingerprint",
        "dispatch_input_fingerprint",
    ):
        _fingerprint(payload[key], f"creative_pilot_context.{key}")
    phase = _token(
        payload["phase"],
        "creative_pilot_context.phase",
        allowed=frozenset({"independent", "rebuttal", "synthesis"}),
    )
    expected_authority = {
        "read_structured_inputs": True,
        "generate_patch": False,
        "write_repository": False,
        "call_provider": False,
    }
    if payload["authority"] != expected_authority:
        raise CreativePilotContractError("creative pilot task context authority is invalid")
    assignments = payload["assignments"]
    if not isinstance(assignments, list) or not assignments:
        raise CreativePilotContractError("creative pilot task context assignments are required")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for row in assignments:
        if not isinstance(row, Mapping):
            raise CreativePilotContractError("creative pilot task assignment must be an object")
        _exact_keys(
            row,
            {
                "assignment_id",
                "role",
                "phase",
                "review_mode",
                "diff_expected",
                "review_question",
                "input_fingerprint",
                "input_refs",
            },
            "creative_pilot_context.assignment",
        )
        assignment_id = _token(row["assignment_id"], "creative_pilot_context.assignment_id")
        if assignment_id in seen:
            raise CreativePilotContractError("creative pilot task assignment IDs must be unique")
        seen.add(assignment_id)
        _token(row["role"], "creative_pilot_context.role")
        if row["phase"] != phase:
            raise CreativePilotContractError("creative pilot task assignment phase mismatch")
        if row["review_mode"] != "specification_planning" or row["diff_expected"] is not False:
            raise CreativePilotContractError("creative pilot task assignment exceeded authority")
        _bounded_text(row["review_question"], "creative_pilot_context.review_question")
        _fingerprint(row["input_fingerprint"], "creative_pilot_context.input_fingerprint")
        _string_list(
            row["input_refs"], "creative_pilot_context.input_refs", min_items=1, max_items=32
        )
        normalized.append(dict(row))
    expected_dispatch = (
        payload["workspace_revision_fingerprint"]
        if phase == "synthesis"
        else fingerprint_payload(
            {
                "workspace_id": payload["workspace_id"],
                "workspace_intent_fingerprint": payload["workspace_intent_fingerprint"],
                "phase": phase,
                "assignments": normalized,
            }
        )
    )
    if payload["dispatch_input_fingerprint"] != expected_dispatch:
        raise CreativePilotContractError("creative pilot task dispatch fingerprint mismatch")
    return dict(payload)


def _next_revision(workspace: Mapping[str, Any], *, phase: str) -> dict[str, Any]:
    _token(phase, "phase", allowed=PHASES)
    if workspace["state"]["phase"] in TERMINAL_PHASES:
        raise CreativePilotContractError("terminal workspace cannot transition")
    current_phase = str(workspace["state"]["phase"])
    if phase not in ALLOWED_TRANSITIONS.get(current_phase, frozenset()):
        raise CreativePilotContractError(
            f"invalid workspace transition: {current_phase} -> {phase}"
        )
    updated = dict(workspace)
    updated["state"] = {"phase": phase, "terminal": phase in TERMINAL_PHASES}
    updated["revision"] = int(workspace["revision"]) + 1
    body = {
        key: value
        for key, value in updated.items()
        if key
        not in {"workspace_id", "intent_fingerprint", "revision_fingerprint", "idempotency_key"}
    }
    updated["revision_fingerprint"] = fingerprint_payload(body)
    return validate_workspace(updated)


def _validate_artifact_identity(
    payload: Mapping[str, Any], *, artifact_type: str, id_key: str, upstream_ids: Sequence[str]
) -> None:
    body = dict(payload)
    observed_id = body.pop(id_key)
    observed_key = body.pop("idempotency_key")
    expected_id, expected_key = _identity(
        body,
        artifact_type=artifact_type,
        upstream_ids=upstream_ids,
    )
    if observed_id != expected_id or observed_key != expected_key:
        raise CreativePilotContractError(f"{artifact_type} identity mismatch")

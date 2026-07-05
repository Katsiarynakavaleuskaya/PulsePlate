"""Prepare-only admission for finalized creative-code specifications.

This module bridges a reviewed/finalized PR-1 creative-code specification into
the existing PR-2 patch-builder request contract. It does not generate patches,
evaluate candidates, call Codex, write branches, touch GitHub, promote
candidates, mutate runtime truth, use semantic cache, or write graph truth.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
import re
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration.creative_code_patch_contract import (
    DEFAULT_MAX_CHANGED_FILES,
    GENERATION_ATTEMPTS,
    HARD_MAX_CHANGED_FILES,
    HARD_MAX_DIFF_LINES,
    HARD_MAX_PATCH_BYTES,
    HARD_TIMEOUT_SECONDS,
    build_creative_code_patch_build_request,
    source_bundle_fingerprint,
    validate_creative_code_patch_build_request,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.creative_specification_skeptic_review_contract import (
    NEXT_ACTION_SELECTED,
    CreativeSpecificationSkepticReviewError,
    validate_finalize_receipt,
)

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-spec-patch-admission-v1"
HUMAN_ADMISSION_ARTIFACT_TYPE = "creative_spec_patch_human_admission"
ADMISSION_ARTIFACT_TYPE = "creative_spec_patch_admission"
HUMAN_DECISION = "approved_for_patch_builder_prepare"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(candidate\.patch|diff --git|^\+\+\+ |^--- |@@ |"
    r"raw[_ -]?(prompt|response|context|patch|review|body)|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|"
    r"oracle[_ -]?(stdout|stderr)|review[_ -]?thread[_ -]?body|"
    r"pull[_ -]?request[_ -]?body|file://|https?://|"
    r"/(?:Users|home|private/var|var/folders|tmp|etc|opt|usr|Volumes|mnt|root|"
    r"workspace|workspaces)(?:/|$)|~[/\\]|[A-Za-z]:[\\/]|\.venv/|\.git/|"
    r"worktrees([:/._-]|$)|github_pat_|gh[psoru]_|xox[abprs]-|"
    r"sk-[A-Za-z0-9_-]{12,}|GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE | re.MULTILINE,
)

HUMAN_ADMISSION_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "decision",
        "approval_ref",
        "approved_by",
        "approved_at_utc",
        "approved_source_bundle_id",
        "approved_source_bundle_fingerprint",
        "approved_selected_variant_id",
        "approved_selected_variant_fingerprint",
        "allowed_existing_paths",
        "allowed_new_paths",
        "oracle_commands",
        "metrics",
        "budgets",
        "authority",
        "sanitized",
    }
)
HUMAN_AUTHORITY_TRUE_KEYS = frozenset(
    {
        "approve_patch_builder_request",
        "emit_local_artifacts",
        "read_finalized_creative_spec",
        "run_patch_builder_prepare",
        "validate_patch_builder_request",
    }
)
HUMAN_AUTHORITY_FALSE_KEYS = frozenset(
    {
        "call_local_codex_exec",
        "call_product_runtime",
        "call_provider",
        "claim_merge_readiness",
        "create_branch",
        "edit_fixed_mapping",
        "generate_candidate_patch",
        "merge",
        "modify_workflows",
        "open_pull_request",
        "promote_candidate",
        "push_branch",
        "read_secrets",
        "resolve_review_threads",
        "run_patch_builder_evaluate",
        "run_patch_builder_generate",
        "use_semantic_cache",
        "write_graph_truth",
        "write_repository",
        "write_shared_worktree",
    }
)
HUMAN_AUTHORITY_KEYS = HUMAN_AUTHORITY_TRUE_KEYS | HUMAN_AUTHORITY_FALSE_KEYS
BUDGET_KEYS = frozenset(
    {
        "generation_attempts",
        "generation_timeout_seconds",
        "evaluation_timeout_seconds",
        "max_changed_files",
        "max_diff_lines",
        "max_patch_bytes",
    }
)

ADMISSION_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "admission_id",
        "idempotency_key",
        "source",
        "selected_variant",
        "base",
        "human_admission",
        "patch_request",
        "builder_prepare",
        "executed_effects",
        "authority",
        "sanitized",
    }
)
SOURCE_KEYS = frozenset(
    {
        "finalize_id",
        "finalize_receipt_fingerprint",
        "finalize_receipt_ref",
        "bundle_id",
        "bundle_fingerprint",
        "bundle_ref",
        "source_packet_id",
    }
)
SELECTED_VARIANT_KEYS = frozenset(
    {
        "variant_id",
        "variant_fingerprint",
        "target_paths",
        "tests_to_add",
    }
)
BASE_KEYS = frozenset({"base_ref", "base_commit_sha"})
ADMISSION_HUMAN_KEYS = frozenset(
    {
        "decision",
        "approval_ref",
        "approved_by",
        "approved_at_utc",
        "human_admission_fingerprint",
        "human_admission_ref",
    }
)
PATCH_REQUEST_KEYS = frozenset(
    {
        "request_id",
        "request_idempotency_key",
        "request_fingerprint",
        "request_ref",
        "source_bundle_ref",
        "contract_policy_version",
        "request_authority_scope",
    }
)
BUILDER_PREPARE_KEYS = frozenset(
    {
        "prepared",
        "run_id",
        "state_fingerprint",
        "request_file_present",
        "source_bundle_file_present",
        "selected_variant_file_present",
        "state_file_present",
        "candidate_patch_path_present",
        "result_file_present",
        "candidate_patch_generated",
        "candidate_patch_evaluated",
    }
)
EXECUTED_EFFECT_KEYS = frozenset(
    {
        "request_built",
        "builder_prepared",
        "candidate_patch_generated",
        "candidate_patch_evaluated",
        "codex_exec_called",
        "shared_worktree_modified",
        "branch_written",
        "pull_request_opened",
        "fixed_mapping_edited",
        "semantic_cache_used",
        "graph_truth_written",
    }
)
ADMISSION_AUTHORITY_TRUE_KEYS = frozenset(
    {"build_patch_builder_request", "emit_local_artifacts", "run_patch_builder_prepare"}
)
ADMISSION_AUTHORITY_FALSE_KEYS = frozenset(
    {
        "call_local_codex_exec",
        "call_product_runtime",
        "call_provider",
        "claim_merge_readiness",
        "create_branch",
        "edit_fixed_mapping",
        "generate_candidate_patch",
        "merge",
        "modify_workflows",
        "open_pull_request",
        "promote_candidate",
        "push_branch",
        "read_secrets",
        "resolve_review_threads",
        "run_patch_builder_evaluate",
        "run_patch_builder_generate",
        "use_semantic_cache",
        "write_graph_truth",
        "write_repository",
        "write_shared_worktree",
    }
)
ADMISSION_AUTHORITY_KEYS = ADMISSION_AUTHORITY_TRUE_KEYS | ADMISSION_AUTHORITY_FALSE_KEYS


class CreativeSpecPatchAdmissionError(ValueError):
    """Raised when creative-spec patch-builder admission fails closed."""


def default_human_admission_authority() -> dict[str, bool]:
    """Return the prepare-only authority for operator admission."""

    return _authority(
        true_keys=HUMAN_AUTHORITY_TRUE_KEYS,
        false_keys=HUMAN_AUTHORITY_FALSE_KEYS,
    )


def default_admission_authority() -> dict[str, bool]:
    """Return the prepare-only authority for generated admission artifacts."""

    return _authority(
        true_keys=ADMISSION_AUTHORITY_TRUE_KEYS,
        false_keys=ADMISSION_AUTHORITY_FALSE_KEYS,
    )


def empty_builder_prepare_summary() -> dict[str, Any]:
    """Return the unprepared builder summary shape."""

    return {
        "prepared": False,
        "run_id": None,
        "state_fingerprint": None,
        "request_file_present": False,
        "source_bundle_file_present": False,
        "selected_variant_file_present": False,
        "state_file_present": False,
        "candidate_patch_path_present": False,
        "result_file_present": False,
        "candidate_patch_generated": False,
        "candidate_patch_evaluated": False,
    }


def executed_effects(*, builder_prepared: bool = False) -> dict[str, bool]:
    """Return sanitized effects executed by this admission layer."""

    return {
        "request_built": True,
        "builder_prepared": builder_prepared,
        "candidate_patch_generated": False,
        "candidate_patch_evaluated": False,
        "codex_exec_called": False,
        "shared_worktree_modified": False,
        "branch_written": False,
        "pull_request_opened": False,
        "fixed_mapping_edited": False,
        "semantic_cache_used": False,
        "graph_truth_written": False,
    }


def validate_human_admission(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize operator approval for prepare-only admission."""

    label = "CreativeSpecPatchHumanAdmission"
    _require_exact_keys(payload, HUMAN_ADMISSION_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            HUMAN_ADMISSION_ARTIFACT_TYPE,
            label=label,
        ),
        "policy_version": _require_const(
            payload,
            "policy_version",
            POLICY_VERSION,
            label=label,
        ),
        "decision": _require_const(payload, "decision", HUMAN_DECISION, label=label),
        "approval_ref": _require_id(payload, "approval_ref", label=label),
        "approved_by": _require_token(payload, "approved_by", label=label),
        "approved_at_utc": _require_utc(payload, "approved_at_utc", label=label),
        "approved_source_bundle_id": _require_id(payload, "approved_source_bundle_id", label=label),
        "approved_source_bundle_fingerprint": _require_fingerprint(
            payload,
            "approved_source_bundle_fingerprint",
            label=label,
        ),
        "approved_selected_variant_id": _require_id(
            payload,
            "approved_selected_variant_id",
            label=label,
        ),
        "approved_selected_variant_fingerprint": _require_fingerprint(
            payload,
            "approved_selected_variant_fingerprint",
            label=label,
        ),
        "allowed_existing_paths": _normalize_path_list(
            payload,
            "allowed_existing_paths",
            label=label,
            allow_empty=True,
        ),
        "allowed_new_paths": _normalize_path_list(
            payload,
            "allowed_new_paths",
            label=label,
            allow_empty=True,
        ),
        "oracle_commands": _normalize_string_list(payload, "oracle_commands", label=label),
        "metrics": _normalize_string_list(payload, "metrics", label=label),
        "budgets": _normalize_budgets(payload["budgets"], label=f"{label}.budgets"),
        "authority": _normalize_authority(
            payload["authority"],
            expected=default_human_admission_authority(),
            label=f"{label}.authority",
        ),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if not (normalized["allowed_existing_paths"] or normalized["allowed_new_paths"]):
        raise CreativeSpecPatchAdmissionError("human admission requires at least one allowed path.")
    _reject_payload_safety(normalized, label=label)
    return normalized


def build_creative_spec_patch_admission(
    *,
    finalize_receipt: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    human_admission: Mapping[str, Any],
    base_commit_sha: str,
    finalize_receipt_ref: str,
    bundle_ref: str,
    human_admission_ref: str,
    request_ref: str,
    source_bundle_ref: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a deterministic admission artifact and PR-2 patch-builder request."""

    bundle = _validated_bundle(source_bundle)
    receipt = _validated_finalize_receipt(finalize_receipt)
    admission = validate_human_admission(human_admission)
    base_sha = _normalize_sha(base_commit_sha, label="base_commit_sha")
    _validate_finalized_binding(
        receipt=receipt,
        bundle=bundle,
        human_admission=admission,
    )
    request = build_creative_code_patch_build_request(
        source_bundle=dict(bundle),
        base_commit_sha=base_sha,
        approval_ref=admission["approval_ref"],
        allowed_existing_paths=list(admission["allowed_existing_paths"]),
        allowed_new_paths=list(admission["allowed_new_paths"]),
        oracle_commands=list(admission["oracle_commands"]),
        metrics=list(admission["metrics"]),
        budgets=dict(admission["budgets"]),
    )
    request = validate_creative_code_patch_build_request(request, source_bundle=dict(bundle))
    variant = _selected_variant(bundle)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ADMISSION_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "admission_id": "pending",
        "idempotency_key": "pending",
        "source": {
            "finalize_id": receipt["finalize_id"],
            "finalize_receipt_fingerprint": fingerprint_payload(dict(receipt)),
            "finalize_receipt_ref": _normalize_artifact_ref(
                finalize_receipt_ref, label="source.finalize_receipt_ref"
            ),
            "bundle_id": bundle["bundle_id"],
            "bundle_fingerprint": source_bundle_fingerprint(bundle),
            "bundle_ref": _normalize_artifact_ref(bundle_ref, label="source.bundle_ref"),
            "source_packet_id": bundle["source_packet_id"],
        },
        "selected_variant": {
            "variant_id": variant["variant_id"],
            "variant_fingerprint": variant["variant_fingerprint"],
            "target_paths": list(variant["target_paths"]),
            "tests_to_add": list(variant["tests_to_add"]),
        },
        "base": {"base_ref": "origin/main", "base_commit_sha": base_sha},
        "human_admission": {
            "decision": admission["decision"],
            "approval_ref": admission["approval_ref"],
            "approved_by": admission["approved_by"],
            "approved_at_utc": admission["approved_at_utc"],
            "human_admission_fingerprint": fingerprint_payload(dict(admission)),
            "human_admission_ref": _normalize_artifact_ref(
                human_admission_ref, label="human_admission.human_admission_ref"
            ),
        },
        "patch_request": {
            "request_id": request["request_id"],
            "request_idempotency_key": request["idempotency_key"],
            "request_fingerprint": fingerprint_payload(dict(request)),
            "request_ref": _normalize_artifact_ref(request_ref, label="patch_request.request_ref"),
            "source_bundle_ref": _normalize_artifact_ref(
                source_bundle_ref,
                label="patch_request.source_bundle_ref",
            ),
            "contract_policy_version": request["policy_version"],
            "request_authority_scope": "pr2_builder_request_contract",
        },
        "builder_prepare": empty_builder_prepare_summary(),
        "executed_effects": executed_effects(builder_prepared=False),
        "authority": default_admission_authority(),
        "sanitized": True,
    }
    _set_admission_identity(body)
    normalized = validate_creative_spec_patch_admission(body)
    validate_admission_bindings(
        normalized,
        request=request,
        source_bundle=bundle,
        finalize_receipt=receipt,
        human_admission=admission,
    )
    return normalized, request


def build_builder_prepare_summary(
    *,
    run_id: str,
    state: Mapping[str, Any],
    request_file_present: bool,
    source_bundle_file_present: bool,
    selected_variant_file_present: bool,
    state_file_present: bool,
    candidate_patch_path_present: bool,
    result_file_present: bool,
) -> dict[str, Any]:
    """Build the prepare-only proof summary after builder ``prepare``."""

    label = "builder_prepare"
    normalized_run_id = _normalize_optional_id(run_id, label=f"{label}.run_id")
    if not isinstance(state, Mapping):
        raise CreativeSpecPatchAdmissionError("builder state must be a JSON object.")
    candidate_generated = state.get("candidate_patch_generated")
    candidate_evaluated = state.get("candidate_patch_evaluated")
    if candidate_generated is not False or candidate_evaluated is not False:
        raise CreativeSpecPatchAdmissionError("builder prepare must not generate or evaluate.")
    if candidate_patch_path_present:
        raise CreativeSpecPatchAdmissionError("builder prepare must not create candidate.patch.")
    if result_file_present:
        raise CreativeSpecPatchAdmissionError("builder prepare must not create result.json.")
    summary = {
        "prepared": True,
        "run_id": normalized_run_id,
        "state_fingerprint": fingerprint_payload(dict(state)),
        "request_file_present": _normalize_bool_value(
            request_file_present,
            label=f"{label}.request_file_present",
        ),
        "source_bundle_file_present": _normalize_bool_value(
            source_bundle_file_present,
            label=f"{label}.source_bundle_file_present",
        ),
        "selected_variant_file_present": _normalize_bool_value(
            selected_variant_file_present,
            label=f"{label}.selected_variant_file_present",
        ),
        "state_file_present": _normalize_bool_value(
            state_file_present,
            label=f"{label}.state_file_present",
        ),
        "candidate_patch_path_present": False,
        "result_file_present": False,
        "candidate_patch_generated": False,
        "candidate_patch_evaluated": False,
    }
    return _normalize_builder_prepare(summary)


def attach_builder_prepare_summary(
    admission: Mapping[str, Any],
    *,
    builder_prepare: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an admission artifact updated with prepare-only builder proof."""

    normalized = validate_creative_spec_patch_admission(admission)
    updated = dict(normalized)
    updated["builder_prepare"] = _normalize_builder_prepare(builder_prepare)
    updated["executed_effects"] = _normalize_executed_effects(
        executed_effects(builder_prepared=True)
    )
    _validate_admission_identity(updated)
    return validate_creative_spec_patch_admission(updated)


def validate_creative_spec_patch_admission(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the metadata-only admission artifact."""

    label = "CreativeSpecPatchAdmission"
    _require_exact_keys(payload, ADMISSION_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            ADMISSION_ARTIFACT_TYPE,
            label=label,
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "admission_id": _require_id(payload, "admission_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source": _normalize_source(payload["source"]),
        "selected_variant": _normalize_selected_variant(payload["selected_variant"]),
        "base": _normalize_base(payload["base"]),
        "human_admission": _normalize_admission_human(payload["human_admission"]),
        "patch_request": _normalize_patch_request(payload["patch_request"]),
        "builder_prepare": _normalize_builder_prepare(payload["builder_prepare"]),
        "executed_effects": _normalize_executed_effects(payload["executed_effects"]),
        "authority": _normalize_authority(
            payload["authority"],
            expected=default_admission_authority(),
            label=f"{label}.authority",
        ),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if (
        normalized["builder_prepare"]["prepared"]
        != normalized["executed_effects"]["builder_prepared"]
    ):
        raise CreativeSpecPatchAdmissionError("builder_prepare and executed_effects disagree.")
    _validate_admission_identity(normalized)
    _reject_payload_safety(normalized, label=label)
    return normalized


def validate_admission_bindings(
    admission: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    finalize_receipt: Mapping[str, Any],
    human_admission: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate admission refs against the concrete source/request payloads."""

    normalized = validate_creative_spec_patch_admission(admission)
    bundle = _validated_bundle(source_bundle)
    receipt = _validated_finalize_receipt(finalize_receipt)
    human = validate_human_admission(human_admission)
    _validate_finalized_binding(receipt=receipt, bundle=bundle, human_admission=human)
    normalized_request = validate_creative_code_patch_build_request(
        dict(request),
        source_bundle=dict(bundle),
    )
    if normalized["source"]["finalize_id"] != receipt["finalize_id"]:
        raise CreativeSpecPatchAdmissionError("admission finalize_id does not match receipt.")
    if normalized["source"]["finalize_receipt_fingerprint"] != fingerprint_payload(dict(receipt)):
        raise CreativeSpecPatchAdmissionError(
            "admission finalize_receipt_fingerprint does not match receipt."
        )
    if normalized["source"]["bundle_id"] != bundle["bundle_id"]:
        raise CreativeSpecPatchAdmissionError("admission bundle_id does not match bundle.")
    if normalized["source"]["bundle_fingerprint"] != source_bundle_fingerprint(bundle):
        raise CreativeSpecPatchAdmissionError("admission bundle_fingerprint does not match bundle.")
    if normalized["human_admission"]["human_admission_fingerprint"] != fingerprint_payload(
        dict(human)
    ):
        raise CreativeSpecPatchAdmissionError("human admission fingerprint does not match.")
    if normalized["patch_request"]["request_id"] != normalized_request["request_id"]:
        raise CreativeSpecPatchAdmissionError("patch request id does not match admission.")
    if (
        normalized["patch_request"]["request_idempotency_key"]
        != normalized_request["idempotency_key"]
    ):
        raise CreativeSpecPatchAdmissionError("patch request idempotency key does not match.")
    if normalized["patch_request"]["request_fingerprint"] != fingerprint_payload(
        dict(normalized_request)
    ):
        raise CreativeSpecPatchAdmissionError("patch request fingerprint does not match.")
    if normalized["base"]["base_commit_sha"] != normalized_request["base_commit_sha"]:
        raise CreativeSpecPatchAdmissionError("patch request base SHA does not match admission.")
    if (
        normalized["human_admission"]["approval_ref"]
        != normalized_request["human_admission"]["approval_ref"]
    ):
        raise CreativeSpecPatchAdmissionError("patch request approval_ref does not match.")
    variant = _selected_variant(bundle)
    if normalized["selected_variant"]["variant_id"] != variant["variant_id"]:
        raise CreativeSpecPatchAdmissionError("selected variant id does not match bundle.")
    if normalized["selected_variant"]["variant_fingerprint"] != variant["variant_fingerprint"]:
        raise CreativeSpecPatchAdmissionError("selected variant fingerprint does not match bundle.")
    return normalized


def _validated_bundle(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], validate_creative_code_specification_bundle(payload))
    except CreativeCodeSpecificationError as exc:
        raise CreativeSpecPatchAdmissionError(str(exc)) from exc


def _validated_finalize_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], validate_finalize_receipt(payload))
    except CreativeSpecificationSkepticReviewError as exc:
        raise CreativeSpecPatchAdmissionError(str(exc)) from exc


def _validate_finalized_binding(
    *,
    receipt: Mapping[str, Any],
    bundle: Mapping[str, Any],
    human_admission: Mapping[str, Any],
) -> None:
    if receipt["next_allowed_action"] != NEXT_ACTION_SELECTED:
        raise CreativeSpecPatchAdmissionError(
            "finalize receipt next_allowed_action must be human_review_for_patch_builder."
        )
    if receipt["synthesis_status"] != "selected":
        raise CreativeSpecPatchAdmissionError("finalize receipt must have selected status.")
    if receipt["counts"]["selected_variant_count"] != 1:
        raise CreativeSpecPatchAdmissionError("finalize receipt must select exactly one variant.")
    if receipt["bundle_id"] != bundle["bundle_id"]:
        raise CreativeSpecPatchAdmissionError("finalize receipt bundle_id does not match bundle.")
    if receipt["bundle_idempotency_key"] != bundle["idempotency_key"]:
        raise CreativeSpecPatchAdmissionError(
            "finalize receipt bundle_idempotency_key does not match bundle."
        )
    bundle_fingerprint = source_bundle_fingerprint(bundle)
    if receipt["bundle_fingerprint"] != bundle_fingerprint:
        raise CreativeSpecPatchAdmissionError(
            "finalize receipt bundle_fingerprint does not match bundle."
        )
    variant = _selected_variant(bundle)
    if receipt["selected_variant_id"] != variant["variant_id"]:
        raise CreativeSpecPatchAdmissionError(
            "finalize receipt selected_variant_id does not match bundle."
        )
    if human_admission["approved_source_bundle_id"] != bundle["bundle_id"]:
        raise CreativeSpecPatchAdmissionError("human admission bundle id does not match bundle.")
    if human_admission["approved_source_bundle_fingerprint"] != bundle_fingerprint:
        raise CreativeSpecPatchAdmissionError(
            "human admission bundle fingerprint does not match bundle."
        )
    if human_admission["approved_selected_variant_id"] != variant["variant_id"]:
        raise CreativeSpecPatchAdmissionError(
            "human admission selected variant id does not match bundle."
        )
    if human_admission["approved_selected_variant_fingerprint"] != variant["variant_fingerprint"]:
        raise CreativeSpecPatchAdmissionError(
            "human admission selected variant fingerprint does not match bundle."
        )


def _selected_variant(bundle: Mapping[str, Any]) -> dict[str, Any]:
    synthesis = cast(Mapping[str, Any], bundle["synthesis"])
    selected_id = synthesis.get("selected_variant_id")
    selected_fingerprint = synthesis.get("selected_variant_fingerprint")
    if not selected_id or not selected_fingerprint:
        raise CreativeSpecPatchAdmissionError("finalized bundle must have a selected variant.")
    variants = cast(Sequence[Mapping[str, Any]], bundle["variants"])
    matches = [
        variant
        for variant in variants
        if variant["variant_id"] == selected_id
        and variant["variant_fingerprint"] == selected_fingerprint
    ]
    if len(matches) != 1:
        raise CreativeSpecPatchAdmissionError("selected variant binding is invalid.")
    reviews = cast(Sequence[Mapping[str, Any]], bundle["skeptic_reviews"])
    selected_reviews = [review for review in reviews if review["variant_id"] == selected_id]
    if not selected_reviews or any(review["decision"] != "pass" for review in selected_reviews):
        raise CreativeSpecPatchAdmissionError("selected variant must have only passing reviews.")
    return dict(matches[0])


def _authority(*, true_keys: frozenset[str], false_keys: frozenset[str]) -> dict[str, bool]:
    return {key: key in true_keys for key in sorted(true_keys | false_keys)}


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected_keys: frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(payload)
    missing = sorted(expected_keys - actual)
    extra = sorted(actual - expected_keys)
    if missing:
        raise CreativeSpecPatchAdmissionError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeSpecPatchAdmissionError(f"{label} has unsupported fields: {', '.join(extra)}")


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    return _normalize_id(value, label=f"{label}.{key}")


def _normalize_id(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise CreativeSpecPatchAdmissionError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeSpecPatchAdmissionError(f"{label} must be a safe identifier.")
    return normalized


def _normalize_optional_id(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _normalize_id(value, label=label)


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be a safe token.")
    return normalized


def _require_utc(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be UTC second precision.")
    return value


def _require_sha(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    return _normalize_sha(payload.get(key), label=f"{label}.{key}")


def _normalize_sha(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeSpecPatchAdmissionError(f"{label} must be a 40-char git SHA.")
    return value


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be a sha256 digest.")
    return value


def _normalize_optional_fingerprint(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeSpecPatchAdmissionError(f"{label} must be null or a sha256 digest.")
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, expected: bool, label: str) -> bool:
    value = payload.get(key)
    if value is not expected:
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be {expected}.")
    return expected


def _normalize_bool_value(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise CreativeSpecPatchAdmissionError(f"{label} must be a boolean.")
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
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeSpecPatchAdmissionError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _normalize_path_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be an array.")
    if not value and not allow_empty:
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        path = _normalize_repo_path(item, label=f"{label}.{key}[{index}]")
        if path in seen:
            raise CreativeSpecPatchAdmissionError(f"{label}.{key} must not contain duplicates.")
        seen.add(path)
        normalized.append(path)
    return normalized


def _normalize_repo_path(raw_path: Any, *, label: str) -> str:
    if not isinstance(raw_path, str):
        raise CreativeSpecPatchAdmissionError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise CreativeSpecPatchAdmissionError(f"{label} must be non-empty.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CreativeSpecPatchAdmissionError(f"{label} must not contain control characters.")
    if "\\" in value:
        raise CreativeSpecPatchAdmissionError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")):
        raise CreativeSpecPatchAdmissionError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise CreativeSpecPatchAdmissionError(f"{label} must not be a URL or scheme path.")
    path = PurePosixPath(value)
    if not path.parts or "." in path.parts or ".." in path.parts:
        raise CreativeSpecPatchAdmissionError(f"{label} must not contain traversal segments.")
    return path.as_posix()


def _normalize_artifact_ref(raw_ref: Any, *, label: str) -> str:
    ref = _normalize_repo_path(raw_ref, label=label)
    if not ref.startswith("artifacts/orchestration/creative_code/"):
        raise CreativeSpecPatchAdmissionError(f"{label} must stay under creative-code artifacts.")
    if not ref.endswith(".json"):
        raise CreativeSpecPatchAdmissionError(f"{label} must point to a JSON artifact.")
    return ref


def _normalize_string_list(payload: Mapping[str, Any], key: str, *, label: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be an array.")
    if not value:
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise CreativeSpecPatchAdmissionError(f"{label}.{key}[{index}] must be a string.")
        text = item.strip()
        if not text:
            raise CreativeSpecPatchAdmissionError(f"{label}.{key}[{index}] must be non-empty.")
        if SECRET_RE.search(text) or LEAK_TEXT_RE.search(text):
            raise CreativeSpecPatchAdmissionError(f"{label}.{key}[{index}] contains unsafe text.")
        if text in seen:
            raise CreativeSpecPatchAdmissionError(f"{label}.{key} must not contain duplicates.")
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_budgets(raw_budgets: Any, *, label: str) -> dict[str, int]:
    if not isinstance(raw_budgets, dict):
        raise CreativeSpecPatchAdmissionError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_budgets, BUDGET_KEYS, label=label)
    budgets = {
        "generation_attempts": _require_int(
            raw_budgets,
            "generation_attempts",
            min_value=GENERATION_ATTEMPTS,
            max_value=GENERATION_ATTEMPTS,
            label=label,
        ),
        "generation_timeout_seconds": _require_int(
            raw_budgets,
            "generation_timeout_seconds",
            min_value=1,
            max_value=HARD_TIMEOUT_SECONDS,
            label=label,
        ),
        "evaluation_timeout_seconds": _require_int(
            raw_budgets,
            "evaluation_timeout_seconds",
            min_value=1,
            max_value=HARD_TIMEOUT_SECONDS,
            label=label,
        ),
        "max_changed_files": _require_int(
            raw_budgets,
            "max_changed_files",
            min_value=1,
            max_value=HARD_MAX_CHANGED_FILES,
            label=label,
        ),
        "max_diff_lines": _require_int(
            raw_budgets,
            "max_diff_lines",
            min_value=1,
            max_value=HARD_MAX_DIFF_LINES,
            label=label,
        ),
        "max_patch_bytes": _require_int(
            raw_budgets,
            "max_patch_bytes",
            min_value=1,
            max_value=HARD_MAX_PATCH_BYTES,
            label=label,
        ),
    }
    if budgets["max_changed_files"] > DEFAULT_MAX_CHANGED_FILES:
        return budgets
    return budgets


def _normalize_authority(
    raw_authority: Any,
    *,
    expected: Mapping[str, bool],
    label: str,
) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeSpecPatchAdmissionError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_authority, frozenset(expected), label=label)
    normalized: dict[str, bool] = {}
    for key in sorted(expected):
        value = raw_authority.get(key)
        if value is not expected[key]:
            raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be {expected[key]}.")
        normalized[key] = expected[key]
    return normalized


def _normalize_source(raw_source: Any) -> dict[str, Any]:
    if not isinstance(raw_source, dict):
        raise CreativeSpecPatchAdmissionError("CreativeSpecPatchAdmission.source is invalid.")
    label = "CreativeSpecPatchAdmission.source"
    _require_exact_keys(raw_source, SOURCE_KEYS, label=label)
    return {
        "finalize_id": _require_id(raw_source, "finalize_id", label=label),
        "finalize_receipt_fingerprint": _require_fingerprint(
            raw_source, "finalize_receipt_fingerprint", label=label
        ),
        "finalize_receipt_ref": _normalize_artifact_ref(
            raw_source.get("finalize_receipt_ref"), label=f"{label}.finalize_receipt_ref"
        ),
        "bundle_id": _require_id(raw_source, "bundle_id", label=label),
        "bundle_fingerprint": _require_fingerprint(raw_source, "bundle_fingerprint", label=label),
        "bundle_ref": _normalize_artifact_ref(
            raw_source.get("bundle_ref"), label=f"{label}.bundle_ref"
        ),
        "source_packet_id": _require_id(raw_source, "source_packet_id", label=label),
    }


def _normalize_selected_variant(raw_variant: Any) -> dict[str, Any]:
    if not isinstance(raw_variant, dict):
        raise CreativeSpecPatchAdmissionError(
            "CreativeSpecPatchAdmission.selected_variant is invalid."
        )
    label = "CreativeSpecPatchAdmission.selected_variant"
    _require_exact_keys(raw_variant, SELECTED_VARIANT_KEYS, label=label)
    return {
        "variant_id": _require_id(raw_variant, "variant_id", label=label),
        "variant_fingerprint": _require_fingerprint(
            raw_variant, "variant_fingerprint", label=label
        ),
        "target_paths": _normalize_path_list(raw_variant, "target_paths", label=label),
        "tests_to_add": _normalize_path_list(raw_variant, "tests_to_add", label=label),
    }


def _normalize_base(raw_base: Any) -> dict[str, str]:
    if not isinstance(raw_base, dict):
        raise CreativeSpecPatchAdmissionError("CreativeSpecPatchAdmission.base is invalid.")
    label = "CreativeSpecPatchAdmission.base"
    _require_exact_keys(raw_base, BASE_KEYS, label=label)
    return {
        "base_ref": _require_const(raw_base, "base_ref", "origin/main", label=label),
        "base_commit_sha": _require_sha(raw_base, "base_commit_sha", label=label),
    }


def _normalize_admission_human(raw_human: Any) -> dict[str, str]:
    if not isinstance(raw_human, dict):
        raise CreativeSpecPatchAdmissionError(
            "CreativeSpecPatchAdmission.human_admission is invalid."
        )
    label = "CreativeSpecPatchAdmission.human_admission"
    _require_exact_keys(raw_human, ADMISSION_HUMAN_KEYS, label=label)
    return {
        "decision": _require_const(raw_human, "decision", HUMAN_DECISION, label=label),
        "approval_ref": _require_id(raw_human, "approval_ref", label=label),
        "approved_by": _require_token(raw_human, "approved_by", label=label),
        "approved_at_utc": _require_utc(raw_human, "approved_at_utc", label=label),
        "human_admission_fingerprint": _require_fingerprint(
            raw_human, "human_admission_fingerprint", label=label
        ),
        "human_admission_ref": _normalize_artifact_ref(
            raw_human.get("human_admission_ref"), label=f"{label}.human_admission_ref"
        ),
    }


def _normalize_patch_request(raw_request: Any) -> dict[str, str]:
    if not isinstance(raw_request, dict):
        raise CreativeSpecPatchAdmissionError(
            "CreativeSpecPatchAdmission.patch_request is invalid."
        )
    label = "CreativeSpecPatchAdmission.patch_request"
    _require_exact_keys(raw_request, PATCH_REQUEST_KEYS, label=label)
    return {
        "request_id": _require_id(raw_request, "request_id", label=label),
        "request_idempotency_key": _require_id(raw_request, "request_idempotency_key", label=label),
        "request_fingerprint": _require_fingerprint(
            raw_request, "request_fingerprint", label=label
        ),
        "request_ref": _normalize_artifact_ref(
            raw_request.get("request_ref"), label=f"{label}.request_ref"
        ),
        "source_bundle_ref": _normalize_artifact_ref(
            raw_request.get("source_bundle_ref"), label=f"{label}.source_bundle_ref"
        ),
        "contract_policy_version": _require_const(
            raw_request,
            "contract_policy_version",
            "creative-code-patch-builder-pr2",
            label=label,
        ),
        "request_authority_scope": _require_const(
            raw_request,
            "request_authority_scope",
            "pr2_builder_request_contract",
            label=label,
        ),
    }


def _normalize_builder_prepare(raw_prepare: Any) -> dict[str, Any]:
    if not isinstance(raw_prepare, dict):
        raise CreativeSpecPatchAdmissionError(
            "CreativeSpecPatchAdmission.builder_prepare is invalid."
        )
    label = "CreativeSpecPatchAdmission.builder_prepare"
    _require_exact_keys(raw_prepare, BUILDER_PREPARE_KEYS, label=label)
    normalized = {
        "prepared": _normalize_bool_value(raw_prepare.get("prepared"), label=f"{label}.prepared"),
        "run_id": _normalize_optional_id(raw_prepare.get("run_id"), label=f"{label}.run_id"),
        "state_fingerprint": _normalize_optional_fingerprint(
            raw_prepare.get("state_fingerprint"), label=f"{label}.state_fingerprint"
        ),
        "request_file_present": _normalize_bool_value(
            raw_prepare.get("request_file_present"), label=f"{label}.request_file_present"
        ),
        "source_bundle_file_present": _normalize_bool_value(
            raw_prepare.get("source_bundle_file_present"),
            label=f"{label}.source_bundle_file_present",
        ),
        "selected_variant_file_present": _normalize_bool_value(
            raw_prepare.get("selected_variant_file_present"),
            label=f"{label}.selected_variant_file_present",
        ),
        "state_file_present": _normalize_bool_value(
            raw_prepare.get("state_file_present"), label=f"{label}.state_file_present"
        ),
        "candidate_patch_path_present": _require_false(
            raw_prepare,
            "candidate_patch_path_present",
            label=label,
        ),
        "result_file_present": _require_false(raw_prepare, "result_file_present", label=label),
        "candidate_patch_generated": _require_false(
            raw_prepare,
            "candidate_patch_generated",
            label=label,
        ),
        "candidate_patch_evaluated": _require_false(
            raw_prepare,
            "candidate_patch_evaluated",
            label=label,
        ),
    }
    if normalized["prepared"]:
        if normalized["run_id"] is None:
            raise CreativeSpecPatchAdmissionError("prepared builder summary requires run_id.")
        if normalized["state_fingerprint"] is None:
            raise CreativeSpecPatchAdmissionError(
                "prepared builder summary requires state_fingerprint."
            )
        for key in (
            "request_file_present",
            "source_bundle_file_present",
            "selected_variant_file_present",
            "state_file_present",
        ):
            if normalized[key] is not True:
                raise CreativeSpecPatchAdmissionError(f"prepared builder summary requires {key}.")
    else:
        if normalized["run_id"] is not None or normalized["state_fingerprint"] is not None:
            raise CreativeSpecPatchAdmissionError(
                "unprepared builder summary must not include run_id or state_fingerprint."
            )
        for key in (
            "request_file_present",
            "source_bundle_file_present",
            "selected_variant_file_present",
            "state_file_present",
        ):
            if normalized[key] is not False:
                raise CreativeSpecPatchAdmissionError(
                    f"unprepared builder summary must keep {key} false."
                )
    return normalized


def _require_false(payload: Mapping[str, Any], key: str, *, label: str) -> bool:
    value = payload.get(key)
    if value is not False:
        raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be false.")
    return False


def _normalize_executed_effects(raw_effects: Any) -> dict[str, bool]:
    if not isinstance(raw_effects, dict):
        raise CreativeSpecPatchAdmissionError(
            "CreativeSpecPatchAdmission.executed_effects is invalid."
        )
    label = "CreativeSpecPatchAdmission.executed_effects"
    _require_exact_keys(raw_effects, EXECUTED_EFFECT_KEYS, label=label)
    normalized: dict[str, bool] = {}
    for key in sorted(EXECUTED_EFFECT_KEYS):
        expected = key == "request_built" or (
            key == "builder_prepared" and raw_effects.get("builder_prepared") is True
        )
        if key not in {"request_built", "builder_prepared"}:
            expected = False
        value = raw_effects.get(key)
        if value is not expected:
            raise CreativeSpecPatchAdmissionError(f"{label}.{key} must be {expected}.")
        normalized[key] = expected
    return normalized


def _set_admission_identity(body: dict[str, Any]) -> None:
    fingerprint = fingerprint_payload(_admission_identity_payload(body))
    upstream_ids = (
        str(body["source"]["finalize_id"]),
        str(body["source"]["finalize_receipt_fingerprint"]),
        str(body["source"]["bundle_fingerprint"]),
        str(body["selected_variant"]["variant_fingerprint"]),
        str(body["base"]["base_commit_sha"]),
        str(body["human_admission"]["human_admission_fingerprint"]),
        str(body["patch_request"]["request_fingerprint"]),
    )
    body["admission_id"] = build_asset_id(
        asset_type=ADMISSION_ARTIFACT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    body["idempotency_key"] = build_idempotency_key(
        asset_type=ADMISSION_ARTIFACT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )


def _admission_identity_payload(admission: Mapping[str, Any]) -> dict[str, Any]:
    identity_keys = (
        "schema_version",
        "artifact_type",
        "policy_version",
        "source",
        "selected_variant",
        "base",
        "human_admission",
        "patch_request",
        "authority",
        "sanitized",
    )
    return {key: admission[key] for key in identity_keys}


def _validate_admission_identity(admission: Mapping[str, Any]) -> None:
    expected = dict(admission)
    _set_admission_identity(expected)
    if admission["admission_id"] != expected["admission_id"]:
        raise CreativeSpecPatchAdmissionError("admission_id does not match admission content.")
    if admission["idempotency_key"] != expected["idempotency_key"]:
        raise CreativeSpecPatchAdmissionError(
            "admission idempotency_key does not match admission content."
        )


def _reject_payload_safety(value: Any, *, label: str) -> None:
    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise CreativeSpecPatchAdmissionError(f"{label} contains unsafe text.")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_payload_safety(item, label=f"{label}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_payload_safety(item, label=f"{label}[{index}]")

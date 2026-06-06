"""Typed redacted private-pilot activation evidence contract.

This module is intentionally pure: it does not read environment variables,
write files, call GitHub/Slack, mint tokens, or dispatch workflows. Callers pass
already-redacted readiness labels and receive an exact-key evidence payload.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any

from scripts.orchestration.experiment_slack_bridge_constants import (
    DEFAULT_WORKFLOW_FILE,
    DEFAULT_WORKFLOW_REF,
    SECRET_SHAPED_RE,
)
from scripts.orchestration.experiment_slack_redaction import (
    LOCAL_PATH_RE,
    SLACK_IDENTIFIER_RE,
)

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "private-pilot-activation-2026-06-06-v1"
EVIDENCE_GRAPH_ADMISSION_STATUS = "contract_only_not_runtime"
EVIDENCE_ID_RE = re.compile(r"^[a-f0-9]{24}$")
FULL_SHA256_RE = re.compile(r"\b[a-f0-9]{64}\b", re.IGNORECASE)
OWNER_REPO_RE = re.compile(r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b")
PATCH_OR_LOG_MARKER_RE = re.compile(
    r"(diff\s+--git|^@@\s|^\+\+\+\s|^---\s|raw\s+patch|patch\s+text|"
    r"oracle\s+stdout|oracle\s+stderr|raw\s+stdout|raw\s+stderr|"
    r"workflow\s+log|stdout\s*:|stderr\s*:)",
    re.IGNORECASE | re.MULTILINE,
)

ALLOWED_ACTIVATION_STATES = frozenset(
    {
        "manual_only",
        "ready_for_manual_live_smoke",
        "blocked_by_missing_secret",
        "blocked_by_allowlist",
        "blocked_by_invalid_config",
        "smoke_recorded",
        "smoke_failed_safely",
        "invalid_local_artifact",
    }
)
ALLOWED_DISPATCH_OUTCOMES = frozenset(
    {
        "not_run",
        "dry_run_only",
        "blocked_before_dispatch",
        "smoke_recorded",
        "smoke_failed_safely",
        "invalid_local_artifact",
    }
)
ALLOWED_TOKEN_STATUSES = frozenset({"not_checked", "missing", "invalid", "valid"})
ALLOWED_ALLOWLIST_STATUSES = frozenset({"not_checked", "missing", "invalid", "present"})
ALLOWED_INPUT_STATUSES = frozenset({"not_checked", "valid", "invalid"})
ALLOWED_AUDIT_STATUSES = frozenset({"not_checked", "valid", "invalid"})
ALLOWED_SMOKE_REQUIREMENTS = frozenset({"not_required", "required"})
ALLOWED_MANUAL_SMOKE_LABELS = frozenset({"operator_evidence_only"})
ALLOWED_GITHUB_AUTH_CLASSES = frozenset({"none", "invalid", "installation", "runtime"})
ALLOWED_GITHUB_AUTH_STATUSES = frozenset({"missing", "invalid", "present"})
ALLOWED_GITHUB_TARGET_STATUSES = frozenset({"not_configured", "invalid", "same_repo", "cross_repo"})
ALLOWED_GITHUB_REPO_ALLOWLIST_STATUSES = frozenset(
    {"not_required", "invalid", "matched", "nonmatching", "missing"}
)
ALLOWED_GITHUB_WORKFLOW_STATUSES = frozenset({"fixed", "invalid"})
ALLOWED_GITHUB_EXECUTE_GATE_STATUSES = frozenset({"not_required", "missing", "enabled", "invalid"})
ALLOWED_GITHUB_APPROVAL_STATUSES = frozenset({"dry_run_default", "present_unverified", "invalid"})
ALLOWED_GITHUB_READINESS_STATES = frozenset(
    {
        "manual_only",
        "blocked_by_invalid_config",
        "blocked_by_execute_gate",
        "blocked_by_slack_allowlist",
        "blocked_by_missing_target",
        "blocked_by_missing_auth",
        "blocked_by_live_approval_verification",
        "blocked_by_allowlist",
        "cross_repo_dry_run_available",
        "blocked_by_auth_class",
        "eligible_for_private_pilot_dispatch",
        "eligible_for_same_repo_dispatch",
        "same_repo_dry_run_available",
    }
)
ALLOWED_AUTHORITY_LABELS = frozenset({"display_only"})
ALLOWED_LAST_SMOKE_LABELS = frozenset(
    {"none", "not_run", "smoke_recorded", "smoke_failed_safely", "invalid_local_artifact"}
)
ALLOWED_NEXT_ACTIONS = frozenset(
    {
        "configure_runtime_secrets",
        "fix_allowlists",
        "fix_invalid_config",
        "provide_smoke_inputs",
        "run_manual_live_smoke",
        "inspect_sanitized_failure",
        "review_activation_report",
        "no_action",
    }
)

AUTHORITY_BOUNDARY_FIELDS = frozenset(
    {
        "arbitrary_workflow_dispatch_enabled",
        "backend_contract_changed",
        "claimed_merge_readiness",
        "created_pr",
        "deterministic_ci_requires_live_slack",
        "merge_authority",
        "opened_http_ingress",
        "pr_mutation_authority",
        "product_runtime_changed",
        "resolved_review_threads",
        "review_thread_mutation_authority",
        "semantic_cache_enabled",
        "slack_command_surface_changed",
        "token_minting_enabled",
        "workflow_authority_changed",
    }
)
REDACTION_SUMMARY_FIELDS = frozenset(
    {
        "approval_digests_stored",
        "local_paths_stored",
        "oracle_output_stored",
        "patch_text_stored",
        "raw_branch_refs_stored",
        "raw_hypotheses_stored",
        "raw_repo_names_stored",
        "raw_slack_text_stored",
        "slack_ids_stored",
        "token_prefixes_stored",
        "token_values_stored",
        "workflow_logs_stored",
    }
)
EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "policy_version",
        "evidence_id",
        "generated_at",
        "activation_state",
        "dispatch_outcome_class",
        "slack_app_token_status",
        "slack_bot_token_status",
        "channel_allowlist_status",
        "user_allowlist_status",
        "team_allowlist_status",
        "branch_ref_status",
        "hypothesis_sha256_status",
        "audit_retention_status",
        "smoke_input_requirement",
        "manual_live_smoke",
        "github_dispatch_auth_class",
        "github_dispatch_auth_status",
        "github_dispatch_authority",
        "github_dispatch_target_status",
        "github_dispatch_repo_allowlist_status",
        "github_dispatch_workflow_file",
        "github_dispatch_workflow_ref",
        "github_dispatch_workflow_status",
        "github_dispatch_execute_gate_status",
        "github_dispatch_live_approval_status",
        "github_dispatch_readiness_state",
        "last_smoke",
        "next_operator_action",
        "evidence_graph_admission_status",
        "authority_boundary",
        "redaction_summary",
    }
)


class PrivatePilotActivationEvidenceError(RuntimeError):
    """Private-pilot activation evidence validation failed."""


def authority_boundary() -> dict[str, bool]:
    """Return the immutable display-only authority boundary."""

    return {key: False for key in sorted(AUTHORITY_BOUNDARY_FIELDS)}


def redaction_summary() -> dict[str, bool]:
    """Return the immutable no-raw-values redaction summary."""

    return {key: False for key in sorted(REDACTION_SUMMARY_FIELDS)}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _evidence_id(payload_without_id: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload_without_id)).hexdigest()[:24]


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PrivatePilotActivationEvidenceError("Private pilot activation timestamp is invalid.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PrivatePilotActivationEvidenceError(
            "Private pilot activation timestamp is invalid."
        ) from exc
    if parsed.tzinfo is None:
        raise PrivatePilotActivationEvidenceError("Private pilot activation timestamp is invalid.")
    normalized = parsed.astimezone(timezone.utc).replace(microsecond=0)
    if normalized > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise PrivatePilotActivationEvidenceError("Private pilot activation timestamp is invalid.")
    return normalized.isoformat()


def _enum(value: Any, *, allowed: frozenset[str], label: str, default: str) -> str:
    normalized = str(value if value is not None else default).strip()
    if normalized not in allowed:
        raise PrivatePilotActivationEvidenceError(f"Private pilot activation {label} is invalid.")
    return normalized


def _false_map(value: Any, *, fields: frozenset[str], label: str) -> dict[str, bool]:
    if not isinstance(value, Mapping):
        raise PrivatePilotActivationEvidenceError(f"Private pilot activation {label} is invalid.")
    if set(value) != set(fields):
        raise PrivatePilotActivationEvidenceError(f"Private pilot activation {label} is invalid.")
    normalized: dict[str, bool] = {}
    for key in sorted(fields):
        item = value[key]
        if item is not False:
            raise PrivatePilotActivationEvidenceError(
                f"Private pilot activation {label} is invalid."
            )
        normalized[key] = False
    return normalized


def _assert_safe_payload(payload: Mapping[str, Any]) -> None:
    rendered = _canonical_json_bytes(payload).decode("ascii")
    if (
        SECRET_SHAPED_RE.search(rendered)
        or SLACK_IDENTIFIER_RE.search(rendered)
        or LOCAL_PATH_RE.search(rendered)
        or PATCH_OR_LOG_MARKER_RE.search(rendered)
        or FULL_SHA256_RE.search(rendered)
        or OWNER_REPO_RE.search(rendered)
    ):
        raise PrivatePilotActivationEvidenceError(
            "Private pilot activation evidence contains unsafe content."
        )


def _readiness_label(
    readiness: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
    default: str,
) -> str:
    return _enum(readiness.get(key, default), allowed=allowed, label=key, default=default)


def _coarse_activation_state(
    readiness: Mapping[str, Any],
    *,
    dispatch_outcome_class: str,
) -> str:
    if dispatch_outcome_class in {"smoke_recorded", "smoke_failed_safely"}:
        return dispatch_outcome_class
    if dispatch_outcome_class == "invalid_local_artifact":
        return "invalid_local_artifact"
    activation = str(readiness.get("activation_state", "manual_only")).strip()
    github_state = str(readiness.get("github_dispatch_readiness_state", "manual_only")).strip()
    if activation in {
        "manual_only",
        "ready_for_manual_live_smoke",
        "blocked_by_missing_secret",
        "blocked_by_allowlist",
        "blocked_by_invalid_config",
    }:
        state = activation
    elif activation == "blocked_by_smoke_input":
        state = "blocked_by_invalid_config"
    else:
        state = "blocked_by_invalid_config"
    if github_state in {"blocked_by_missing_auth"}:
        return "blocked_by_missing_secret"
    if github_state in {"blocked_by_allowlist", "blocked_by_slack_allowlist"}:
        return "blocked_by_allowlist"
    if github_state.startswith("blocked_by_") and state == "manual_only":
        return "blocked_by_invalid_config"
    if github_state == "eligible_for_private_pilot_dispatch" and state == "manual_only":
        return "ready_for_manual_live_smoke"
    return state


def _next_operator_action(
    *,
    activation_state: str,
    readiness: Mapping[str, Any],
    dispatch_outcome_class: str,
) -> str:
    if activation_state == "blocked_by_missing_secret":
        return "configure_runtime_secrets"
    if activation_state == "blocked_by_allowlist":
        return "fix_allowlists"
    if activation_state in {"blocked_by_invalid_config", "invalid_local_artifact"}:
        smoke_requirement = str(readiness.get("smoke_input_requirement", "not_required"))
        branch_status = str(readiness.get("branch_ref_status", "not_checked"))
        hypothesis_status = str(readiness.get("hypothesis_sha256_status", "not_checked"))
        if smoke_requirement == "required" and (
            branch_status != "valid" or hypothesis_status != "valid"
        ):
            return "provide_smoke_inputs"
        return "fix_invalid_config"
    if dispatch_outcome_class == "smoke_failed_safely":
        return "inspect_sanitized_failure"
    if dispatch_outcome_class == "smoke_recorded":
        return "review_activation_report"
    if activation_state == "ready_for_manual_live_smoke":
        return "run_manual_live_smoke"
    return "run_manual_live_smoke"


def _last_smoke(dispatch_outcome_class: str) -> str:
    if dispatch_outcome_class in {
        "smoke_recorded",
        "smoke_failed_safely",
        "invalid_local_artifact",
    }:
        return dispatch_outcome_class
    return "not_run"


def _assert_consistent_status_labels(payload: Mapping[str, Any]) -> None:
    """Reject internally contradictory evidence labels."""

    outcome = str(payload["dispatch_outcome_class"])
    activation_state = str(payload["activation_state"])
    if outcome in {"smoke_recorded", "smoke_failed_safely", "invalid_local_artifact"}:
        if activation_state != outcome:
            raise PrivatePilotActivationEvidenceError(
                "Private pilot activation activation_state is inconsistent."
            )
    elif activation_state in {"smoke_recorded", "smoke_failed_safely", "invalid_local_artifact"}:
        raise PrivatePilotActivationEvidenceError(
            "Private pilot activation activation_state is inconsistent."
        )

    if str(payload["last_smoke"]) != _last_smoke(outcome):
        raise PrivatePilotActivationEvidenceError(
            "Private pilot activation last_smoke is inconsistent."
        )

    expected_action = _next_operator_action(
        activation_state=activation_state,
        readiness=payload,
        dispatch_outcome_class=outcome,
    )
    if str(payload["next_operator_action"]) != expected_action:
        raise PrivatePilotActivationEvidenceError(
            "Private pilot activation next_operator_action is inconsistent."
        )


def build_private_pilot_activation_evidence(
    readiness_report: Mapping[str, Any] | None = None,
    *,
    dispatch_outcome_class: str = "not_run",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build exact-key redacted activation evidence from value-free readiness labels."""

    readiness = readiness_report or {}
    outcome = _enum(
        dispatch_outcome_class,
        allowed=ALLOWED_DISPATCH_OUTCOMES,
        label="dispatch_outcome_class",
        default="not_run",
    )
    activation_state = _coarse_activation_state(readiness, dispatch_outcome_class=outcome)
    timestamp = _validate_timestamp(generated_at or _utcnow_iso())
    payload_without_id: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "generated_at": timestamp,
        "activation_state": _enum(
            activation_state,
            allowed=ALLOWED_ACTIVATION_STATES,
            label="activation_state",
            default="manual_only",
        ),
        "dispatch_outcome_class": outcome,
        "slack_app_token_status": _readiness_label(
            readiness,
            "slack_app_token_status",
            allowed=ALLOWED_TOKEN_STATUSES,
            default="not_checked",
        ),
        "slack_bot_token_status": _readiness_label(
            readiness,
            "slack_bot_token_status",
            allowed=ALLOWED_TOKEN_STATUSES,
            default="not_checked",
        ),
        "channel_allowlist_status": _readiness_label(
            readiness,
            "channel_allowlist_status",
            allowed=ALLOWED_ALLOWLIST_STATUSES,
            default="not_checked",
        ),
        "user_allowlist_status": _readiness_label(
            readiness,
            "user_allowlist_status",
            allowed=ALLOWED_ALLOWLIST_STATUSES,
            default="not_checked",
        ),
        "team_allowlist_status": _readiness_label(
            readiness,
            "team_allowlist_status",
            allowed=ALLOWED_ALLOWLIST_STATUSES,
            default="not_checked",
        ),
        "branch_ref_status": _readiness_label(
            readiness,
            "branch_ref_status",
            allowed=ALLOWED_INPUT_STATUSES,
            default="not_checked",
        ),
        "hypothesis_sha256_status": _readiness_label(
            readiness,
            "hypothesis_sha256_status",
            allowed=ALLOWED_INPUT_STATUSES,
            default="not_checked",
        ),
        "audit_retention_status": _readiness_label(
            readiness,
            "audit_retention_status",
            allowed=ALLOWED_AUDIT_STATUSES,
            default="not_checked",
        ),
        "smoke_input_requirement": _readiness_label(
            readiness,
            "smoke_input_requirement",
            allowed=ALLOWED_SMOKE_REQUIREMENTS,
            default="not_required",
        ),
        "manual_live_smoke": _readiness_label(
            readiness,
            "manual_live_smoke",
            allowed=ALLOWED_MANUAL_SMOKE_LABELS,
            default="operator_evidence_only",
        ),
        "github_dispatch_auth_class": _readiness_label(
            readiness,
            "github_dispatch_auth_class",
            allowed=ALLOWED_GITHUB_AUTH_CLASSES,
            default="none",
        ),
        "github_dispatch_auth_status": _readiness_label(
            readiness,
            "github_dispatch_auth_status",
            allowed=ALLOWED_GITHUB_AUTH_STATUSES,
            default="missing",
        ),
        "github_dispatch_authority": _readiness_label(
            readiness,
            "github_dispatch_authority",
            allowed=ALLOWED_AUTHORITY_LABELS,
            default="display_only",
        ),
        "github_dispatch_target_status": _readiness_label(
            readiness,
            "github_dispatch_target_status",
            allowed=ALLOWED_GITHUB_TARGET_STATUSES,
            default="not_configured",
        ),
        "github_dispatch_repo_allowlist_status": _readiness_label(
            readiness,
            "github_dispatch_repo_allowlist_status",
            allowed=ALLOWED_GITHUB_REPO_ALLOWLIST_STATUSES,
            default="not_required",
        ),
        "github_dispatch_workflow_file": DEFAULT_WORKFLOW_FILE,
        "github_dispatch_workflow_ref": DEFAULT_WORKFLOW_REF,
        "github_dispatch_workflow_status": _readiness_label(
            readiness,
            "github_dispatch_workflow_status",
            allowed=ALLOWED_GITHUB_WORKFLOW_STATUSES,
            default="fixed",
        ),
        "github_dispatch_execute_gate_status": _readiness_label(
            readiness,
            "github_dispatch_execute_gate_status",
            allowed=ALLOWED_GITHUB_EXECUTE_GATE_STATUSES,
            default="not_required",
        ),
        "github_dispatch_live_approval_status": _readiness_label(
            readiness,
            "github_dispatch_live_approval_status",
            allowed=ALLOWED_GITHUB_APPROVAL_STATUSES,
            default="dry_run_default",
        ),
        "github_dispatch_readiness_state": _readiness_label(
            readiness,
            "github_dispatch_readiness_state",
            allowed=ALLOWED_GITHUB_READINESS_STATES,
            default="manual_only",
        ),
        "last_smoke": _last_smoke(outcome),
        "next_operator_action": _next_operator_action(
            activation_state=activation_state,
            readiness=readiness,
            dispatch_outcome_class=outcome,
        ),
        "evidence_graph_admission_status": EVIDENCE_GRAPH_ADMISSION_STATUS,
        "authority_boundary": authority_boundary(),
        "redaction_summary": redaction_summary(),
    }
    payload = {
        **payload_without_id,
        "evidence_id": _evidence_id(payload_without_id),
    }
    return validate_private_pilot_activation_evidence(payload)


def validate_private_pilot_activation_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize exact-key private-pilot activation evidence."""

    if not isinstance(payload, Mapping) or set(payload) != set(EVIDENCE_FIELDS):
        raise PrivatePilotActivationEvidenceError("Private pilot activation schema is invalid.")
    normalized: dict[str, Any] = {
        "schema_version": _enum(
            payload["schema_version"],
            allowed=frozenset({SCHEMA_VERSION}),
            label="schema_version",
            default=SCHEMA_VERSION,
        ),
        "policy_version": _enum(
            payload["policy_version"],
            allowed=frozenset({POLICY_VERSION}),
            label="policy_version",
            default=POLICY_VERSION,
        ),
        "generated_at": _validate_timestamp(payload["generated_at"]),
        "activation_state": _enum(
            payload["activation_state"],
            allowed=ALLOWED_ACTIVATION_STATES,
            label="activation_state",
            default="manual_only",
        ),
        "dispatch_outcome_class": _enum(
            payload["dispatch_outcome_class"],
            allowed=ALLOWED_DISPATCH_OUTCOMES,
            label="dispatch_outcome_class",
            default="not_run",
        ),
        "slack_app_token_status": _enum(
            payload["slack_app_token_status"],
            allowed=ALLOWED_TOKEN_STATUSES,
            label="slack_app_token_status",
            default="not_checked",
        ),
        "slack_bot_token_status": _enum(
            payload["slack_bot_token_status"],
            allowed=ALLOWED_TOKEN_STATUSES,
            label="slack_bot_token_status",
            default="not_checked",
        ),
        "channel_allowlist_status": _enum(
            payload["channel_allowlist_status"],
            allowed=ALLOWED_ALLOWLIST_STATUSES,
            label="channel_allowlist_status",
            default="not_checked",
        ),
        "user_allowlist_status": _enum(
            payload["user_allowlist_status"],
            allowed=ALLOWED_ALLOWLIST_STATUSES,
            label="user_allowlist_status",
            default="not_checked",
        ),
        "team_allowlist_status": _enum(
            payload["team_allowlist_status"],
            allowed=ALLOWED_ALLOWLIST_STATUSES,
            label="team_allowlist_status",
            default="not_checked",
        ),
        "branch_ref_status": _enum(
            payload["branch_ref_status"],
            allowed=ALLOWED_INPUT_STATUSES,
            label="branch_ref_status",
            default="not_checked",
        ),
        "hypothesis_sha256_status": _enum(
            payload["hypothesis_sha256_status"],
            allowed=ALLOWED_INPUT_STATUSES,
            label="hypothesis_sha256_status",
            default="not_checked",
        ),
        "audit_retention_status": _enum(
            payload["audit_retention_status"],
            allowed=ALLOWED_AUDIT_STATUSES,
            label="audit_retention_status",
            default="not_checked",
        ),
        "smoke_input_requirement": _enum(
            payload["smoke_input_requirement"],
            allowed=ALLOWED_SMOKE_REQUIREMENTS,
            label="smoke_input_requirement",
            default="not_required",
        ),
        "manual_live_smoke": _enum(
            payload["manual_live_smoke"],
            allowed=ALLOWED_MANUAL_SMOKE_LABELS,
            label="manual_live_smoke",
            default="operator_evidence_only",
        ),
        "github_dispatch_auth_class": _enum(
            payload["github_dispatch_auth_class"],
            allowed=ALLOWED_GITHUB_AUTH_CLASSES,
            label="github_dispatch_auth_class",
            default="none",
        ),
        "github_dispatch_auth_status": _enum(
            payload["github_dispatch_auth_status"],
            allowed=ALLOWED_GITHUB_AUTH_STATUSES,
            label="github_dispatch_auth_status",
            default="missing",
        ),
        "github_dispatch_authority": _enum(
            payload["github_dispatch_authority"],
            allowed=ALLOWED_AUTHORITY_LABELS,
            label="github_dispatch_authority",
            default="display_only",
        ),
        "github_dispatch_target_status": _enum(
            payload["github_dispatch_target_status"],
            allowed=ALLOWED_GITHUB_TARGET_STATUSES,
            label="github_dispatch_target_status",
            default="not_configured",
        ),
        "github_dispatch_repo_allowlist_status": _enum(
            payload["github_dispatch_repo_allowlist_status"],
            allowed=ALLOWED_GITHUB_REPO_ALLOWLIST_STATUSES,
            label="github_dispatch_repo_allowlist_status",
            default="not_required",
        ),
        "github_dispatch_workflow_file": _enum(
            payload["github_dispatch_workflow_file"],
            allowed=frozenset({DEFAULT_WORKFLOW_FILE}),
            label="github_dispatch_workflow_file",
            default=DEFAULT_WORKFLOW_FILE,
        ),
        "github_dispatch_workflow_ref": _enum(
            payload["github_dispatch_workflow_ref"],
            allowed=frozenset({DEFAULT_WORKFLOW_REF}),
            label="github_dispatch_workflow_ref",
            default=DEFAULT_WORKFLOW_REF,
        ),
        "github_dispatch_workflow_status": _enum(
            payload["github_dispatch_workflow_status"],
            allowed=ALLOWED_GITHUB_WORKFLOW_STATUSES,
            label="github_dispatch_workflow_status",
            default="fixed",
        ),
        "github_dispatch_execute_gate_status": _enum(
            payload["github_dispatch_execute_gate_status"],
            allowed=ALLOWED_GITHUB_EXECUTE_GATE_STATUSES,
            label="github_dispatch_execute_gate_status",
            default="not_required",
        ),
        "github_dispatch_live_approval_status": _enum(
            payload["github_dispatch_live_approval_status"],
            allowed=ALLOWED_GITHUB_APPROVAL_STATUSES,
            label="github_dispatch_live_approval_status",
            default="dry_run_default",
        ),
        "github_dispatch_readiness_state": _enum(
            payload["github_dispatch_readiness_state"],
            allowed=ALLOWED_GITHUB_READINESS_STATES,
            label="github_dispatch_readiness_state",
            default="manual_only",
        ),
        "last_smoke": _enum(
            payload["last_smoke"],
            allowed=ALLOWED_LAST_SMOKE_LABELS,
            label="last_smoke",
            default="not_run",
        ),
        "next_operator_action": _enum(
            payload["next_operator_action"],
            allowed=ALLOWED_NEXT_ACTIONS,
            label="next_operator_action",
            default="run_manual_live_smoke",
        ),
        "evidence_graph_admission_status": _enum(
            payload["evidence_graph_admission_status"],
            allowed=frozenset({EVIDENCE_GRAPH_ADMISSION_STATUS}),
            label="evidence_graph_admission_status",
            default=EVIDENCE_GRAPH_ADMISSION_STATUS,
        ),
        "authority_boundary": _false_map(
            payload["authority_boundary"],
            fields=AUTHORITY_BOUNDARY_FIELDS,
            label="authority boundary",
        ),
        "redaction_summary": _false_map(
            payload["redaction_summary"],
            fields=REDACTION_SUMMARY_FIELDS,
            label="redaction summary",
        ),
    }
    _assert_consistent_status_labels(normalized)
    evidence_id = payload["evidence_id"]
    if not isinstance(evidence_id, str) or EVIDENCE_ID_RE.fullmatch(evidence_id) is None:
        raise PrivatePilotActivationEvidenceError(
            "Private pilot activation evidence id is invalid."
        )
    if _evidence_id(normalized) != evidence_id:
        raise PrivatePilotActivationEvidenceError(
            "Private pilot activation evidence id is invalid."
        )
    normalized["evidence_id"] = evidence_id
    _assert_safe_payload(normalized)
    return normalized


def absent_private_pilot_activation_summary() -> tuple[str, ...]:
    """Return Slack/report-safe summary lines when no evidence exists."""

    return (
        "private_pilot_activation_state=manual_only",
        "private_pilot_last_smoke=none",
        "private_pilot_next_operator_action=run_manual_live_smoke",
        "private_pilot_dispatch_outcome_class=not_run",
        "private_pilot_evidence_status=absent",
        f"private_pilot_evidence_graph_admission_status={EVIDENCE_GRAPH_ADMISSION_STATUS}",
        "private_pilot_authority=display_only",
    )


def invalid_private_pilot_activation_summary() -> tuple[str, ...]:
    """Return Slack/report-safe summary lines for malformed local evidence."""

    return (
        "private_pilot_activation_state=invalid_local_artifact",
        "private_pilot_last_smoke=invalid_local_artifact",
        "private_pilot_next_operator_action=inspect_sanitized_failure",
        "private_pilot_dispatch_outcome_class=invalid_local_artifact",
        "private_pilot_evidence_status=invalid_local_artifact",
        f"private_pilot_evidence_graph_admission_status={EVIDENCE_GRAPH_ADMISSION_STATUS}",
        "private_pilot_authority=display_only",
    )


def render_private_pilot_activation_summary(
    evidence: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Render a Slack-safe summary tuple from validated activation evidence."""

    if evidence is None:
        return absent_private_pilot_activation_summary()
    try:
        normalized = validate_private_pilot_activation_evidence(evidence)
    except PrivatePilotActivationEvidenceError:
        return invalid_private_pilot_activation_summary()
    return (
        f"private_pilot_activation_state={normalized['activation_state']}",
        f"private_pilot_last_smoke={normalized['last_smoke']}",
        f"private_pilot_next_operator_action={normalized['next_operator_action']}",
        f"private_pilot_dispatch_outcome_class={normalized['dispatch_outcome_class']}",
        "private_pilot_evidence_status=valid",
        f"private_pilot_evidence_graph_admission_status={EVIDENCE_GRAPH_ADMISSION_STATUS}",
        "private_pilot_authority=display_only",
    )

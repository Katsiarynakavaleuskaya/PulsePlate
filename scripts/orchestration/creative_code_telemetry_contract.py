"""Strict local telemetry contracts for governed creative-code PR-4.

PR-4 measures sanitized PR-1/PR-2/PR-3 creative-code artifacts. It does not
grant repository-write, PR, review-thread, merge, release, runtime, Slack, or
GitHub App authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import re
import sys
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-code-telemetry-pr4"
V2_SCHEMA_VERSION = "2.0"
V2_POLICY_VERSION = "creative-code-telemetry-v2"
V2_PROCESS_EVENT_MAX = 1_000_000
V2_PROCESS_AGGREGATE_MAX = 1_000_000_000_000
EVENT_TYPE = "creative_code_telemetry_event"
ROLLUP_TYPE = "creative_code_telemetry_rollup"
TAXONOMY_TYPE = "creative_code_rejection_taxonomy"
SUCCESS_OUTPUT = "PASS: creative-code telemetry contract valid"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |candidate\.patch|raw[_ -]?"
    r"(prompt|response|context|patch)|candidate_patch|chain[_ -]?of[_ -]?thought|"
    r"provider[_ -]?payload|oracle[_ -]?(stdout|stderr)|/Users/|/private/var/|"
    r"/var/folders/|/tmp/|\.venv/|\.git/|worktrees([:/._-]|$)|github_pat_|gh[psoru]_|"
    r"xox[abprs]-|sk-[A-Za-z0-9_-]{12,})",
    re.IGNORECASE | re.MULTILINE,
)

LANE_STAGES = frozenset(
    {
        "specification",
        "patch_evaluation",
        "promotion_plan",
        "promotion_validation",
        "promotion_approval",
        "pr_open",
        "artifact_read_error",
    }
)
SOURCE_ARTIFACT_TYPES = frozenset(
    {
        "creative_code_specification",
        "creative_code_patch_result",
        "creative_code_pr_promotion_plan",
        "creative_code_pr_promotion_validation",
        "creative_code_pr_promotion_approval",
        "creative_code_pr_promotion_receipt",
        "creative_code_artifact_read_error",
    }
)
LEGACY_SOURCE_TYPE_TO_STAGE = {
    "creative_code_specification": "specification",
    "creative_code_patch_result": "patch_evaluation",
    "creative_code_pr_promotion_plan": "promotion_plan",
    "creative_code_pr_promotion_validation": "promotion_validation",
    "creative_code_pr_promotion_approval": "promotion_approval",
    "creative_code_pr_promotion_receipt": "pr_open",
    "creative_code_artifact_read_error": "artifact_read_error",
}
EVENT_STATUSES = frozenset(
    {"accepted", "rejected", "blocked", "promoted", "opened", "not_applicable"}
)
SEVERITIES = frozenset({"info", "low", "medium", "high"})
OWNERS = frozenset(
    {
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "dev-operator",
        "human-operator",
    }
)
RETRYABILITY = frozenset({"retryable", "not_retryable", "operator_review"})

TAXONOMY_CLASSES: dict[str, dict[str, str]] = {
    "specification_rejected": {
        "stage": "specification",
        "severity": "medium",
        "retryability": "operator_review",
        "likely_owner": "agent-coordinator",
    },
    "duplicate_variant": {
        "stage": "specification",
        "severity": "medium",
        "retryability": "retryable",
        "likely_owner": "architecture-specialist",
    },
    "review_blocker": {
        "stage": "specification",
        "severity": "high",
        "retryability": "operator_review",
        "likely_owner": "qa-engineer-agent",
    },
    "unsafe_authority": {
        "stage": "specification",
        "severity": "high",
        "retryability": "not_retryable",
        "likely_owner": "security-auditor",
    },
    "invalid_input": {
        "stage": "specification",
        "severity": "medium",
        "retryability": "operator_review",
        "likely_owner": "agent-coordinator",
    },
    "timeout": {
        "stage": "patch_evaluation",
        "severity": "medium",
        "retryability": "retryable",
        "likely_owner": "dev-operator",
    },
    "oom": {
        "stage": "patch_evaluation",
        "severity": "high",
        "retryability": "retryable",
        "likely_owner": "dev-operator",
    },
    "metric_regression": {
        "stage": "patch_evaluation",
        "severity": "high",
        "retryability": "operator_review",
        "likely_owner": "qa-engineer-agent",
    },
    "guard_failure": {
        "stage": "patch_evaluation",
        "severity": "high",
        "retryability": "operator_review",
        "likely_owner": "qa-engineer-agent",
    },
    "policy_violation": {
        "stage": "patch_evaluation",
        "severity": "high",
        "retryability": "not_retryable",
        "likely_owner": "security-auditor",
    },
    "unchanged_result": {
        "stage": "patch_evaluation",
        "severity": "medium",
        "retryability": "retryable",
        "likely_owner": "dev-operator",
    },
    "capability_mismatch": {
        "stage": "patch_evaluation",
        "severity": "medium",
        "retryability": "not_retryable",
        "likely_owner": "dev-operator",
    },
    "infra_flake": {
        "stage": "patch_evaluation",
        "severity": "medium",
        "retryability": "retryable",
        "likely_owner": "dev-operator",
    },
    "base_drift": {
        "stage": "promotion_plan",
        "severity": "medium",
        "retryability": "retryable",
        "likely_owner": "dev-operator",
    },
    "patch_drift": {
        "stage": "promotion_validation",
        "severity": "high",
        "retryability": "not_retryable",
        "likely_owner": "security-auditor",
    },
    "lineage_mismatch": {
        "stage": "promotion_validation",
        "severity": "high",
        "retryability": "not_retryable",
        "likely_owner": "architecture-specialist",
    },
    "approval_missing": {
        "stage": "promotion_approval",
        "severity": "medium",
        "retryability": "operator_review",
        "likely_owner": "human-operator",
    },
    "branch_exists": {
        "stage": "promotion_plan",
        "severity": "medium",
        "retryability": "operator_review",
        "likely_owner": "dev-operator",
    },
    "github_transport_failed": {
        "stage": "pr_open",
        "severity": "medium",
        "retryability": "retryable",
        "likely_owner": "dev-operator",
    },
    "pr_readback_failed": {
        "stage": "pr_open",
        "severity": "medium",
        "retryability": "retryable",
        "likely_owner": "dev-operator",
    },
    "leak_detected": {
        "stage": "artifact_read_error",
        "severity": "high",
        "retryability": "not_retryable",
        "likely_owner": "security-auditor",
    },
    "malformed_artifact": {
        "stage": "artifact_read_error",
        "severity": "medium",
        "retryability": "operator_review",
        "likely_owner": "dev-operator",
    },
    "unknown": {
        "stage": "artifact_read_error",
        "severity": "medium",
        "retryability": "operator_review",
        "likely_owner": "agent-coordinator",
    },
}

EVENT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "event_id",
        "idempotency_key",
        "lane_stage",
        "source_artifact_type",
        "source_artifact_id",
        "source_fingerprint",
        "candidate_ids",
        "status",
        "rejection_class",
        "failure_class",
        "taxonomy_codes",
        "metrics",
        "cost_metadata",
        "authority",
        "sanitized",
    }
)
CANDIDATE_ID_KEYS = frozenset(
    {
        "source_packet_id",
        "source_bundle_id",
        "selected_variant_id",
        "request_id",
        "result_id",
        "promotion_id",
    }
)
METRIC_KEYS = frozenset(
    {
        "variant_count",
        "selected_variant_count",
        "changed_files",
        "diff_lines",
        "patch_bytes",
        "oracle_commands_configured",
        "oracle_commands_executed",
        "generation_attempts",
        "promotion_plan_count",
        "promotion_validation_passed",
        "promotion_approval_count",
        "pull_requests_opened",
    }
)
COST_KEYS = frozenset(
    {
        "available",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "estimated",
    }
)
AUTHORITY_KEYS = frozenset(
    {
        "read_only_telemetry",
        "writes_repo",
        "opens_pr",
        "resolves_threads",
        "claims_merge_readiness",
        "merges",
        "calls_network",
        "calls_runtime",
        "modifies_github_app",
        "modifies_slack",
    }
)
ROLLUP_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "input_roots",
        "event_count",
        "funnel",
        "rates",
        "rejections_by_class",
        "failures_by_class",
        "events_by_stage",
        "events_by_status",
        "source_artifacts",
        "cost",
        "caveats",
        "sanitized",
    }
)
FUNNEL_KEYS = frozenset(
    {
        "specification_bundles",
        "variants_total",
        "variants_selected",
        "patch_results",
        "patch_results_accepted",
        "patch_results_rejected",
        "promotion_plans",
        "promotion_validations_passed",
        "promotion_approvals",
        "pull_requests_opened",
    }
)
RATES_KEYS = frozenset(
    {
        "oracle_pass_rate_bps",
        "human_approval_rate_bps",
        "promotion_rate_bps",
        "first_pass_acceptance_rate_bps",
    }
)
ROLLUP_COST_KEYS = frozenset(
    {
        "cost_metadata_available_count",
        "token_usage_available_count",
        "estimated_cost_usd",
    }
)
TAXONOMY_KEYS = frozenset(
    {"schema_version", "artifact_type", "policy_version", "classes", "sanitized"}
)
TAXONOMY_CLASS_KEYS = frozenset({"code", "stage", "severity", "retryability", "likely_owner"})

V2_EVENT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "event_id",
        "idempotency_key",
        "lane_stage",
        "source_artifact_type",
        "source_artifact_id",
        "source_fingerprint",
        "status",
        "terminal_projection",
        "process",
        "cost_metadata",
        "authority",
        "sanitized",
    }
)
V2_TERMINAL_PROJECTION_KEYS = frozenset(
    {
        "promotion_id",
        "repository",
        "pull_request_number",
        "promoted_head_sha",
        "closure_epoch",
        "review_observation",
        "governance_observation",
        "post_merge_observation",
    }
)
V2_PROCESS_KEYS = frozenset({"review_cycles", "repair_cycles", "validation_attempts"})
V2_REVIEW_OBSERVATIONS = frozenset(
    {"actionables_observed", "no_actionables_observed", "evidence_unavailable"}
)
V2_GOVERNANCE_OBSERVATIONS = frozenset(
    {"blockers_observed", "no_blockers_observed", "evidence_unavailable"}
)
V2_POST_MERGE_OBSERVATIONS = frozenset(
    {
        "complete_observed",
        "incomplete_observed",
        "evidence_unavailable",
        "not_applicable",
    }
)
V2_TERMINAL_STATUSES = frozenset({"merged", "closed_unmerged"})
V2_ROLLUP_CAVEATS = frozenset(
    {
        "local_only",
        "not_merge_readiness_evidence",
        "not_product_runtime_truth",
        "terminal_observation_only",
    }
)
V2_ROLLUP_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "input_roots",
        "event_count",
        "legacy_event_count",
        "funnel",
        "rates",
        "rejections_by_class",
        "failures_by_class",
        "events_by_stage",
        "events_by_status",
        "source_artifacts",
        "terminal",
        "cost",
        "caveats",
        "sanitized",
    }
)
V2_RATES_KEYS = RATES_KEYS | frozenset({"merge_rate_bps", "post_merge_complete_rate_bps"})
V2_TERMINAL_KEYS = frozenset(
    {
        "outcome_count",
        "merged",
        "closed_unmerged",
        "review_observations",
        "governance_observations",
        "post_merge_observations",
        "process",
    }
)
V2_ROLLUP_COST_KEYS = frozenset(
    {
        "cost_metadata_available_count",
        "token_usage_available_count",
        "terminal_cost_metadata_available_count",
        "terminal_token_usage_available_count",
        "estimated_cost_usd",
    }
)


class CreativeCodeTelemetryContractError(ValueError):
    """Raised when creative-code telemetry violates PR-4 boundaries."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeTelemetryContractError(
                "creative-code telemetry JSON has a duplicate key."
            )
        seen.add(key)
        payload[key] = value
    return payload


def read_json_object(path: str | Path) -> dict[str, Any]:
    """Read a JSON object while rejecting duplicate keys."""

    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodeTelemetryContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodeTelemetryContractError(
            "Unable to read creative-code telemetry JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise CreativeCodeTelemetryContractError(
            "Creative-code telemetry artifact must be a JSON object."
        )
    return payload


def reject_unsafe_telemetry_value(value: Any, *, label: str) -> None:
    """Reject telemetry strings that could leak raw artifacts or secrets."""

    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise CreativeCodeTelemetryContractError(f"{label} contains unsafe telemetry text.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_unsafe_telemetry_value(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            reject_unsafe_telemetry_value(item, label=f"{label}.{key}")


def _require_exact_keys(
    payload: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise CreativeCodeTelemetryContractError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodeTelemetryContractError(f"{label} has unsupported fields.")


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be a safe identifier.")
    return normalized


def _require_v2_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    normalized = _require_id(payload, key, label=label)
    if payload.get(key) != normalized:
        raise CreativeCodeTelemetryContractError(
            f"{label}.{key} must use canonical identifier spelling."
        )
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be a safe token.")
    return normalized


def _require_fingerprint(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be a sha256 digest.")
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, expected: bool, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool) or value != expected:
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be {expected}.")
    return value


def _require_any_bool(payload: Mapping[str, Any], key: str, *, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be a boolean.")
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
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodeTelemetryContractError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _optional_token(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CreativeCodeTelemetryContractError(f"{label} must be null or string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise CreativeCodeTelemetryContractError(f"{label} must be a safe token.")
    return normalized


def _normalize_candidate_ids(raw_ids: Any) -> dict[str, str | None]:
    if not isinstance(raw_ids, dict):
        raise CreativeCodeTelemetryContractError("candidate_ids must be a JSON object.")
    _require_exact_keys(raw_ids, CANDIDATE_ID_KEYS, label="candidate_ids")
    return {
        key: _optional_token(raw_ids[key], label=f"candidate_ids.{key}")
        for key in sorted(CANDIDATE_ID_KEYS)
    }


def _normalize_metrics(raw_metrics: Any) -> dict[str, int | None]:
    if not isinstance(raw_metrics, dict):
        raise CreativeCodeTelemetryContractError("metrics must be a JSON object.")
    _require_exact_keys(raw_metrics, METRIC_KEYS, label="metrics")
    normalized: dict[str, int | None] = {}
    for key in sorted(METRIC_KEYS):
        value = raw_metrics[key]
        if value is None:
            normalized[key] = None
            continue
        normalized[key] = _require_int(
            raw_metrics, key, min_value=0, max_value=1_000_000, label="metrics"
        )
    return normalized


def default_metrics(**overrides: int | None) -> dict[str, int | None]:
    metrics: dict[str, int | None] = {key: None for key in sorted(METRIC_KEYS)}
    for key, value in overrides.items():
        if key not in metrics:
            raise CreativeCodeTelemetryContractError(f"unknown metric key: {key}")
        metrics[key] = value
    return metrics


def default_cost_metadata() -> dict[str, int | bool | None]:
    return {
        "available": False,
        "cached_input_tokens": None,
        "estimated": False,
        "input_tokens": None,
        "output_tokens": None,
        "reasoning_output_tokens": None,
    }


def _normalize_cost_metadata(raw_cost: Any) -> dict[str, int | bool | None]:
    if not isinstance(raw_cost, dict):
        raise CreativeCodeTelemetryContractError("cost_metadata must be a JSON object.")
    _require_exact_keys(raw_cost, COST_KEYS, label="cost_metadata")
    available = _require_any_bool(raw_cost, "available", label="cost_metadata")
    estimated = _require_any_bool(raw_cost, "estimated", label="cost_metadata")
    normalized: dict[str, int | bool | None] = {"available": available, "estimated": estimated}
    token_keys = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
    for key in token_keys:
        value = raw_cost[key]
        if value is None:
            normalized[key] = None
            continue
        normalized[key] = _require_int(
            raw_cost, key, min_value=0, max_value=1_000_000_000, label="cost_metadata"
        )
    if not available and any(normalized[key] is not None for key in token_keys):
        raise CreativeCodeTelemetryContractError(
            "cost_metadata token counts require available=true."
        )
    if estimated and not available:
        raise CreativeCodeTelemetryContractError("cost_metadata.estimated requires available=true.")
    return {key: normalized[key] for key in sorted(normalized)}


def normalize_cost_metadata(raw_cost: Any) -> dict[str, int | bool | None]:
    """Normalize the closed v1 cost shape for compatible advisory artifacts."""

    return _normalize_cost_metadata(raw_cost)


def default_authority() -> dict[str, bool]:
    return {
        "calls_network": False,
        "calls_runtime": False,
        "claims_merge_readiness": False,
        "merges": False,
        "modifies_github_app": False,
        "modifies_slack": False,
        "opens_pr": False,
        "read_only_telemetry": True,
        "resolves_threads": False,
        "writes_repo": False,
    }


def _normalize_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodeTelemetryContractError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, AUTHORITY_KEYS, label="authority")
    normalized: dict[str, bool] = {}
    for key in sorted(AUTHORITY_KEYS):
        expected = key == "read_only_telemetry"
        normalized[key] = _require_bool(raw_authority, key, expected=expected, label="authority")
    return normalized


def _normalize_taxonomy_codes(raw_codes: Any) -> list[str]:
    if not isinstance(raw_codes, list):
        raise CreativeCodeTelemetryContractError("taxonomy_codes must be an array.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_codes):
        if not isinstance(item, str):
            raise CreativeCodeTelemetryContractError(f"taxonomy_codes[{index}] must be a string.")
        code = item.strip()
        if code not in TAXONOMY_CLASSES:
            raise CreativeCodeTelemetryContractError(f"taxonomy_codes[{index}] is unsupported.")
        if code in seen:
            raise CreativeCodeTelemetryContractError("taxonomy_codes must not contain duplicates.")
        seen.add(code)
        normalized.append(code)
    return sorted(normalized)


def _event_identity_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {key: event[key] for key in sorted(EVENT_KEYS - {"event_id", "idempotency_key"})}


def _event_identity(event: Mapping[str, Any]) -> tuple[str, str]:
    fingerprint = fingerprint_payload(cast(Any, _event_identity_payload(event)))
    upstream_ids = (
        str(event["source_artifact_id"]),
        str(event["source_fingerprint"]),
        str(event["lane_stage"]),
    )
    event_id = build_asset_id(
        asset_type=EVENT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=EVENT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return event_id, idempotency_key


def build_creative_code_telemetry_event(
    *,
    lane_stage: str,
    source_artifact_type: str,
    source_artifact_id: str,
    source_fingerprint: str,
    candidate_ids: Mapping[str, str | None],
    status: str,
    metrics: Mapping[str, int | None],
    taxonomy_codes: Sequence[str] = (),
    rejection_class: str | None = None,
    failure_class: str | None = None,
    cost_metadata: Mapping[str, int | bool | None] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": EVENT_TYPE,
        "policy_version": POLICY_VERSION,
        "event_id": "pending",
        "idempotency_key": "pending",
        "lane_stage": lane_stage,
        "source_artifact_type": source_artifact_type,
        "source_artifact_id": source_artifact_id,
        "source_fingerprint": source_fingerprint,
        "candidate_ids": {key: candidate_ids.get(key) for key in sorted(CANDIDATE_ID_KEYS)},
        "status": status,
        "rejection_class": rejection_class,
        "failure_class": failure_class,
        "taxonomy_codes": list(taxonomy_codes),
        "metrics": {key: metrics.get(key) for key in sorted(METRIC_KEYS)},
        "cost_metadata": dict(cost_metadata or default_cost_metadata()),
        "authority": default_authority(),
        "sanitized": True,
    }
    event_id, idempotency_key = _event_identity(event)
    event["event_id"] = event_id
    event["idempotency_key"] = idempotency_key
    return validate_creative_code_telemetry_event(event)


def validate_creative_code_telemetry_event(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeCodeTelemetryEvent"
    _require_exact_keys(payload, EVENT_KEYS, label=label)
    lane_stage = _require_token(payload, "lane_stage", label=label)
    if lane_stage not in LANE_STAGES:
        raise CreativeCodeTelemetryContractError(
            "CreativeCodeTelemetryEvent.lane_stage is unsupported."
        )
    source_artifact_type = _require_token(payload, "source_artifact_type", label=label)
    if source_artifact_type not in SOURCE_ARTIFACT_TYPES:
        raise CreativeCodeTelemetryContractError(
            "CreativeCodeTelemetryEvent.source_artifact_type is unsupported."
        )
    status = _require_token(payload, "status", label=label)
    if status not in EVENT_STATUSES:
        raise CreativeCodeTelemetryContractError(
            "CreativeCodeTelemetryEvent.status is unsupported."
        )
    rejection_class = _optional_token(payload["rejection_class"], label=f"{label}.rejection_class")
    failure_class = _optional_token(payload["failure_class"], label=f"{label}.failure_class")
    taxonomy_codes = _normalize_taxonomy_codes(payload["taxonomy_codes"])
    if rejection_class is not None and rejection_class not in TAXONOMY_CLASSES:
        raise CreativeCodeTelemetryContractError(
            "CreativeCodeTelemetryEvent.rejection_class is unsupported."
        )
    if failure_class is not None and failure_class not in TAXONOMY_CLASSES:
        raise CreativeCodeTelemetryContractError(
            "CreativeCodeTelemetryEvent.failure_class is unsupported."
        )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", EVENT_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "event_id": _require_id(payload, "event_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "lane_stage": lane_stage,
        "source_artifact_type": source_artifact_type,
        "source_artifact_id": _require_id(payload, "source_artifact_id", label=label),
        "source_fingerprint": _require_fingerprint(payload, "source_fingerprint", label=label),
        "candidate_ids": _normalize_candidate_ids(payload["candidate_ids"]),
        "status": status,
        "rejection_class": rejection_class,
        "failure_class": failure_class,
        "taxonomy_codes": taxonomy_codes,
        "metrics": _normalize_metrics(payload["metrics"]),
        "cost_metadata": _normalize_cost_metadata(payload["cost_metadata"]),
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    event_id, idempotency_key = _event_identity(normalized)
    if normalized["event_id"] != event_id:
        raise CreativeCodeTelemetryContractError("event_id does not match event content.")
    if normalized["idempotency_key"] != idempotency_key:
        raise CreativeCodeTelemetryContractError("idempotency_key does not match event content.")
    reject_unsafe_telemetry_value(normalized, label=label)
    return normalized


def compute_bps(numerator: int, denominator: int) -> int | None:
    if denominator <= 0:
        return None
    return (numerator * 10_000) // denominator


def build_creative_code_rejection_taxonomy() -> dict[str, Any]:
    return validate_creative_code_rejection_taxonomy(
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": TAXONOMY_TYPE,
            "policy_version": POLICY_VERSION,
            "classes": [
                {"code": code, **TAXONOMY_CLASSES[code]} for code in sorted(TAXONOMY_CLASSES)
            ],
            "sanitized": True,
        }
    )


def validate_creative_code_rejection_taxonomy(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeCodeRejectionTaxonomy"
    _require_exact_keys(payload, TAXONOMY_KEYS, label=label)
    classes = payload["classes"]
    if not isinstance(classes, list) or not classes:
        raise CreativeCodeTelemetryContractError(
            "CreativeCodeRejectionTaxonomy.classes must be non-empty."
        )
    seen: set[str] = set()
    normalized_classes: list[dict[str, str]] = []
    for index, item in enumerate(classes):
        if not isinstance(item, dict):
            raise CreativeCodeTelemetryContractError(f"classes[{index}] must be a JSON object.")
        _require_exact_keys(item, TAXONOMY_CLASS_KEYS, label=f"classes[{index}]")
        code = _require_token(item, "code", label=f"classes[{index}]")
        if code not in TAXONOMY_CLASSES:
            raise CreativeCodeTelemetryContractError(f"classes[{index}].code is unsupported.")
        if code in seen:
            raise CreativeCodeTelemetryContractError("taxonomy classes must not repeat codes.")
        seen.add(code)
        expected = TAXONOMY_CLASSES[code]
        normalized = {
            "code": code,
            "stage": _require_const(item, "stage", expected["stage"], label=f"classes[{index}]"),
            "severity": _require_const(
                item, "severity", expected["severity"], label=f"classes[{index}]"
            ),
            "retryability": _require_const(
                item,
                "retryability",
                expected["retryability"],
                label=f"classes[{index}]",
            ),
            "likely_owner": _require_const(
                item,
                "likely_owner",
                expected["likely_owner"],
                label=f"classes[{index}]",
            ),
        }
        if normalized["stage"] not in LANE_STAGES:
            raise CreativeCodeTelemetryContractError(f"classes[{index}].stage is unsupported.")
        if normalized["severity"] not in SEVERITIES:
            raise CreativeCodeTelemetryContractError(f"classes[{index}].severity is unsupported.")
        if normalized["retryability"] not in RETRYABILITY:
            raise CreativeCodeTelemetryContractError(
                f"classes[{index}].retryability is unsupported."
            )
        if normalized["likely_owner"] not in OWNERS:
            raise CreativeCodeTelemetryContractError(
                f"classes[{index}].likely_owner is unsupported."
            )
        normalized_classes.append(normalized)
    if seen != set(TAXONOMY_CLASSES):
        raise CreativeCodeTelemetryContractError("taxonomy classes must match the closed code set.")
    normalized_taxonomy = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", TAXONOMY_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "classes": sorted(normalized_classes, key=lambda row: row["code"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    reject_unsafe_telemetry_value(normalized_taxonomy, label=label)
    return normalized_taxonomy


def _count_map(
    raw: Any, *, label: str, allowed_keys: frozenset[str] | None = None
) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise CreativeCodeTelemetryContractError(f"{label} must be a JSON object.")
    normalized: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not SAFE_TOKEN_RE.fullmatch(key):
            raise CreativeCodeTelemetryContractError(f"{label} keys must be safe tokens.")
        if allowed_keys is not None and key not in allowed_keys:
            raise CreativeCodeTelemetryContractError(f"{label}.{key} is unsupported.")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CreativeCodeTelemetryContractError(
                f"{label}.{key} must be a non-negative integer."
            )
        normalized[key] = value
    return dict(sorted(normalized.items()))


def _normalize_funnel(raw_funnel: Any) -> dict[str, int]:
    if not isinstance(raw_funnel, dict):
        raise CreativeCodeTelemetryContractError("funnel must be a JSON object.")
    _require_exact_keys(raw_funnel, FUNNEL_KEYS, label="funnel")
    return {
        key: _require_int(raw_funnel, key, min_value=0, max_value=1_000_000, label="funnel")
        for key in sorted(FUNNEL_KEYS)
    }


def _normalize_rates(raw_rates: Any) -> dict[str, int | None]:
    if not isinstance(raw_rates, dict):
        raise CreativeCodeTelemetryContractError("rates must be a JSON object.")
    _require_exact_keys(raw_rates, RATES_KEYS, label="rates")
    normalized: dict[str, int | None] = {}
    for key in sorted(RATES_KEYS):
        value = raw_rates[key]
        if value is None:
            normalized[key] = None
            continue
        normalized[key] = _require_int(raw_rates, key, min_value=0, max_value=10_000, label="rates")
    return normalized


def _normalize_rollup_cost(raw_cost: Any) -> dict[str, int | None]:
    if not isinstance(raw_cost, dict):
        raise CreativeCodeTelemetryContractError("cost must be a JSON object.")
    _require_exact_keys(raw_cost, ROLLUP_COST_KEYS, label="cost")
    estimated = raw_cost["estimated_cost_usd"]
    if estimated is not None:
        raise CreativeCodeTelemetryContractError("cost.estimated_cost_usd must stay null in PR-4.")
    return {
        "cost_metadata_available_count": _require_int(
            raw_cost,
            "cost_metadata_available_count",
            min_value=0,
            max_value=1_000_000,
            label="cost",
        ),
        "estimated_cost_usd": None,
        "token_usage_available_count": _require_int(
            raw_cost,
            "token_usage_available_count",
            min_value=0,
            max_value=1_000_000,
            label="cost",
        ),
    }


def _normalize_safe_string_list(raw: Any, *, label: str, allow_empty: bool) -> list[str]:
    if not isinstance(raw, list):
        raise CreativeCodeTelemetryContractError(f"{label} must be an array.")
    if not raw and not allow_empty:
        raise CreativeCodeTelemetryContractError(f"{label} must be non-empty.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            raise CreativeCodeTelemetryContractError(f"{label}[{index}] must be a string.")
        value = item.strip()
        if not value or not SAFE_TOKEN_RE.fullmatch(value):
            raise CreativeCodeTelemetryContractError(f"{label}[{index}] must be a safe token.")
        if value in seen:
            raise CreativeCodeTelemetryContractError(f"{label} must not contain duplicates.")
        seen.add(value)
        normalized.append(value)
    return sorted(normalized)


def _source_artifact_rows(raw_rows: Any) -> list[dict[str, str]]:
    if not isinstance(raw_rows, list):
        raise CreativeCodeTelemetryContractError("source_artifacts must be an array.")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            raise CreativeCodeTelemetryContractError(
                f"source_artifacts[{index}] must be an object."
            )
        _require_exact_keys(
            row,
            frozenset({"source_artifact_type", "source_artifact_id", "source_fingerprint"}),
            label=f"source_artifacts[{index}]",
        )
        artifact_type = _require_token(
            row, "source_artifact_type", label=f"source_artifacts[{index}]"
        )
        if artifact_type not in SOURCE_ARTIFACT_TYPES:
            raise CreativeCodeTelemetryContractError(
                f"source_artifacts[{index}].source_artifact_type is unsupported."
            )
        artifact_id = _require_id(row, "source_artifact_id", label=f"source_artifacts[{index}]")
        fingerprint = _require_fingerprint(
            row, "source_fingerprint", label=f"source_artifacts[{index}]"
        )
        key = (artifact_type, artifact_id)
        if key in seen:
            raise CreativeCodeTelemetryContractError(
                "source_artifacts must not contain duplicates."
            )
        seen.add(key)
        normalized.append(
            {
                "source_artifact_id": artifact_id,
                "source_artifact_type": artifact_type,
                "source_fingerprint": fingerprint,
            }
        )
    return sorted(
        normalized, key=lambda row: (row["source_artifact_type"], row["source_artifact_id"])
    )


def build_creative_code_telemetry_rollup(
    events: Sequence[Mapping[str, Any]],
    *,
    input_roots: Sequence[str],
) -> dict[str, Any]:
    normalized_events = [validate_creative_code_telemetry_event(event) for event in events]
    normalized_events.sort(key=lambda row: row["event_id"])
    funnel = {key: 0 for key in sorted(FUNNEL_KEYS)}
    rejections_by_class: dict[str, int] = {}
    failures_by_class: dict[str, int] = {}
    events_by_stage: dict[str, int] = {}
    events_by_status: dict[str, int] = {}
    source_rows: dict[tuple[str, str], dict[str, str]] = {}
    cost_metadata_available_count = 0
    token_usage_available_count = 0

    for event in normalized_events:
        stage = event["lane_stage"]
        status = event["status"]
        events_by_stage[stage] = events_by_stage.get(stage, 0) + 1
        events_by_status[status] = events_by_status.get(status, 0) + 1
        source_rows[(event["source_artifact_type"], event["source_artifact_id"])] = {
            "source_artifact_id": event["source_artifact_id"],
            "source_artifact_type": event["source_artifact_type"],
            "source_fingerprint": event["source_fingerprint"],
        }
        rejection_class = event["rejection_class"]
        failure_class = event["failure_class"]
        if rejection_class:
            rejections_by_class[rejection_class] = rejections_by_class.get(rejection_class, 0) + 1
        if failure_class:
            failures_by_class[failure_class] = failures_by_class.get(failure_class, 0) + 1
        for code in event["taxonomy_codes"]:
            rejections_by_class.setdefault(code, 0)
        metrics = event["metrics"]
        if stage == "specification":
            funnel["specification_bundles"] += 1
            funnel["variants_total"] += metrics["variant_count"] or 0
            funnel["variants_selected"] += metrics["selected_variant_count"] or 0
        elif stage == "patch_evaluation":
            funnel["patch_results"] += 1
            if status == "accepted":
                funnel["patch_results_accepted"] += 1
            if status == "rejected":
                funnel["patch_results_rejected"] += 1
        elif stage == "promotion_plan":
            funnel["promotion_plans"] += 1
        elif stage == "promotion_validation" and status == "accepted":
            funnel["promotion_validations_passed"] += 1
        elif stage == "promotion_approval" and status == "accepted":
            funnel["promotion_approvals"] += 1
        elif stage == "pr_open" and status == "opened":
            funnel["pull_requests_opened"] += 1
        cost = event["cost_metadata"]
        if cost["available"]:
            cost_metadata_available_count += 1
            if any(
                cost[key] is not None
                for key in (
                    "input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                    "reasoning_output_tokens",
                )
            ):
                token_usage_available_count += 1

    rollup = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ROLLUP_TYPE,
        "policy_version": POLICY_VERSION,
        "input_roots": list(input_roots),
        "event_count": len(normalized_events),
        "funnel": funnel,
        "rates": {
            "first_pass_acceptance_rate_bps": compute_bps(
                funnel["patch_results_accepted"], funnel["patch_results"]
            ),
            "human_approval_rate_bps": compute_bps(
                funnel["promotion_approvals"], funnel["promotion_plans"]
            ),
            "oracle_pass_rate_bps": compute_bps(
                funnel["patch_results_accepted"], funnel["patch_results"]
            ),
            "promotion_rate_bps": compute_bps(
                funnel["pull_requests_opened"], funnel["patch_results_accepted"]
            ),
        },
        "rejections_by_class": dict(sorted(rejections_by_class.items())),
        "failures_by_class": dict(sorted(failures_by_class.items())),
        "events_by_stage": dict(sorted(events_by_stage.items())),
        "events_by_status": dict(sorted(events_by_status.items())),
        "source_artifacts": sorted(
            source_rows.values(),
            key=lambda row: (row["source_artifact_type"], row["source_artifact_id"]),
        ),
        "cost": {
            "cost_metadata_available_count": cost_metadata_available_count,
            "estimated_cost_usd": None,
            "token_usage_available_count": token_usage_available_count,
        },
        "caveats": [
            "local_only",
            "not_merge_readiness_evidence",
            "not_product_runtime_truth",
        ],
        "sanitized": True,
    }
    return validate_creative_code_telemetry_rollup(rollup)


def validate_creative_code_telemetry_rollup(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeCodeTelemetryRollup"
    _require_exact_keys(payload, ROLLUP_KEYS, label=label)
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", ROLLUP_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "input_roots": _normalize_safe_string_list(
            payload["input_roots"], label="input_roots", allow_empty=True
        ),
        "event_count": _require_int(
            payload, "event_count", min_value=0, max_value=1_000_000, label=label
        ),
        "funnel": _normalize_funnel(payload["funnel"]),
        "rates": _normalize_rates(payload["rates"]),
        "rejections_by_class": _count_map(
            payload["rejections_by_class"],
            label="rejections_by_class",
            allowed_keys=frozenset(TAXONOMY_CLASSES),
        ),
        "failures_by_class": _count_map(
            payload["failures_by_class"],
            label="failures_by_class",
            allowed_keys=frozenset(TAXONOMY_CLASSES),
        ),
        "events_by_stage": _count_map(
            payload["events_by_stage"], label="events_by_stage", allowed_keys=LANE_STAGES
        ),
        "events_by_status": _count_map(
            payload["events_by_status"], label="events_by_status", allowed_keys=EVENT_STATUSES
        ),
        "source_artifacts": _source_artifact_rows(payload["source_artifacts"]),
        "cost": _normalize_rollup_cost(payload["cost"]),
        "caveats": _normalize_safe_string_list(
            payload["caveats"], label="caveats", allow_empty=False
        ),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if normalized["event_count"] != sum(normalized["events_by_stage"].values()):
        raise CreativeCodeTelemetryContractError("event_count must match events_by_stage total.")
    reject_unsafe_telemetry_value(normalized, label=label)
    return normalized


def _normalize_v2_process(raw_process: Any) -> dict[str, int]:
    if not isinstance(raw_process, dict):
        raise CreativeCodeTelemetryContractError("process must be a JSON object.")
    _require_exact_keys(raw_process, V2_PROCESS_KEYS, label="process")
    return {
        key: _require_int(
            raw_process,
            key,
            min_value=0,
            max_value=V2_PROCESS_EVENT_MAX,
            label="process",
        )
        for key in sorted(V2_PROCESS_KEYS)
    }


def _normalize_v2_process_totals(raw_process: Any) -> dict[str, int]:
    if not isinstance(raw_process, dict):
        raise CreativeCodeTelemetryContractError("process must be a JSON object.")
    _require_exact_keys(raw_process, V2_PROCESS_KEYS, label="process")
    return {
        key: _require_int(
            raw_process,
            key,
            min_value=0,
            max_value=V2_PROCESS_AGGREGATE_MAX,
            label="process",
        )
        for key in sorted(V2_PROCESS_KEYS)
    }


def _normalize_v2_terminal_projection(raw_projection: Any) -> dict[str, Any]:
    from scripts.orchestration.creative_code_terminal_outcome_contract import (
        PROMOTION_ID_RE,
    )

    if not isinstance(raw_projection, dict):
        raise CreativeCodeTelemetryContractError("terminal_projection must be a JSON object.")
    _require_exact_keys(
        raw_projection,
        V2_TERMINAL_PROJECTION_KEYS,
        label="terminal_projection",
    )
    repository = raw_projection.get("repository")
    if not isinstance(repository, str) or repository != "Katsiarynakavaleuskaya/PulsePlate":
        raise CreativeCodeTelemetryContractError("terminal_projection.repository is unsupported.")
    promoted_head_sha = raw_projection.get("promoted_head_sha")
    if not isinstance(promoted_head_sha, str) or not re.fullmatch(
        r"[a-f0-9]{40}", promoted_head_sha
    ):
        raise CreativeCodeTelemetryContractError(
            "terminal_projection.promoted_head_sha must be lowercase 40-hex."
        )
    review_observation = raw_projection.get("review_observation")
    governance_observation = raw_projection.get("governance_observation")
    post_merge_observation = raw_projection.get("post_merge_observation")
    if review_observation not in V2_REVIEW_OBSERVATIONS:
        raise CreativeCodeTelemetryContractError(
            "terminal_projection.review_observation is unsupported."
        )
    if governance_observation not in V2_GOVERNANCE_OBSERVATIONS:
        raise CreativeCodeTelemetryContractError(
            "terminal_projection.governance_observation is unsupported."
        )
    if post_merge_observation not in V2_POST_MERGE_OBSERVATIONS:
        raise CreativeCodeTelemetryContractError(
            "terminal_projection.post_merge_observation is unsupported."
        )
    promotion_id = raw_projection.get("promotion_id")
    if not isinstance(promotion_id, str) or not PROMOTION_ID_RE.fullmatch(promotion_id):
        raise CreativeCodeTelemetryContractError(
            "terminal_projection.promotion_id has invalid format."
        )
    return {
        "promotion_id": promotion_id,
        "repository": repository,
        "pull_request_number": _require_int(
            raw_projection,
            "pull_request_number",
            min_value=1,
            max_value=999_999,
            label="terminal_projection",
        ),
        "promoted_head_sha": promoted_head_sha,
        "closure_epoch": _require_int(
            raw_projection,
            "closure_epoch",
            min_value=1,
            max_value=1_000_000,
            label="terminal_projection",
        ),
        "review_observation": review_observation,
        "governance_observation": governance_observation,
        "post_merge_observation": post_merge_observation,
    }


def _v2_event_identity_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {key: event[key] for key in sorted(V2_EVENT_KEYS - {"event_id", "idempotency_key"})}


def _v2_event_identity(event: Mapping[str, Any]) -> tuple[str, str]:
    fingerprint = fingerprint_payload(cast(Any, _v2_event_identity_payload(event)))
    upstream_ids = (
        str(event["source_artifact_id"]),
        str(event["source_fingerprint"]),
        "pr_terminal",
    )
    event_id = build_asset_id(
        asset_type=EVENT_TYPE,
        rail="control_plane",
        version=V2_SCHEMA_VERSION,
        policy_version=V2_POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=EVENT_TYPE,
        rail="control_plane",
        version=V2_SCHEMA_VERSION,
        policy_version=V2_POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return event_id, idempotency_key


def build_creative_code_terminal_telemetry_event(
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one terminal carrier into exactly one durable v2 event."""

    from scripts.orchestration.creative_code_terminal_outcome_contract import (
        terminal_outcome_fingerprint,
        validate_creative_code_terminal_outcome,
    )

    normalized_outcome = validate_creative_code_terminal_outcome(outcome)
    lineage = normalized_outcome["lineage"]
    event: dict[str, Any] = {
        "schema_version": V2_SCHEMA_VERSION,
        "artifact_type": EVENT_TYPE,
        "policy_version": V2_POLICY_VERSION,
        "event_id": "pending",
        "idempotency_key": "pending",
        "lane_stage": "pr_terminal",
        "source_artifact_type": "creative_code_terminal_outcome",
        "source_artifact_id": normalized_outcome["outcome_id"],
        "source_fingerprint": terminal_outcome_fingerprint(normalized_outcome),
        "status": normalized_outcome["terminal_state"],
        "terminal_projection": {
            "promotion_id": lineage["promotion_id"],
            "repository": lineage["repository"],
            "pull_request_number": lineage["pull_request_number"],
            "promoted_head_sha": lineage["promoted_head_sha"],
            "closure_epoch": normalized_outcome["closure_epoch"],
            "review_observation": normalized_outcome["review_observation"],
            "governance_observation": normalized_outcome["governance_observation"],
            "post_merge_observation": normalized_outcome["post_merge_observation"],
        },
        "process": normalized_outcome["process"],
        "cost_metadata": normalized_outcome["cost_metadata"],
        "authority": default_authority(),
        "sanitized": True,
    }
    event_id, idempotency_key = _v2_event_identity(event)
    event["event_id"] = event_id
    event["idempotency_key"] = idempotency_key
    return validate_creative_code_telemetry_event_v2(event)


def validate_creative_code_telemetry_event_v2(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the one-event v2 terminal projection."""

    from scripts.orchestration.creative_code_terminal_outcome_contract import (
        terminal_outcome_id,
    )

    label = "CreativeCodeTelemetryEventV2"
    _require_exact_keys(payload, V2_EVENT_KEYS, label=label)
    status = payload.get("status")
    if status not in V2_TERMINAL_STATUSES:
        raise CreativeCodeTelemetryContractError(
            "CreativeCodeTelemetryEventV2.status is unsupported."
        )
    projection = _normalize_v2_terminal_projection(payload.get("terminal_projection"))
    normalized = {
        "schema_version": _require_const(payload, "schema_version", V2_SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", EVENT_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", V2_POLICY_VERSION, label=label),
        "event_id": _require_v2_id(payload, "event_id", label=label),
        "idempotency_key": _require_v2_id(payload, "idempotency_key", label=label),
        "lane_stage": _require_const(payload, "lane_stage", "pr_terminal", label=label),
        "source_artifact_type": _require_const(
            payload,
            "source_artifact_type",
            "creative_code_terminal_outcome",
            label=label,
        ),
        "source_artifact_id": _require_v2_id(
            payload,
            "source_artifact_id",
            label=label,
        ),
        "source_fingerprint": _require_fingerprint(payload, "source_fingerprint", label=label),
        "status": status,
        "terminal_projection": projection,
        "process": _normalize_v2_process(payload.get("process")),
        "cost_metadata": _normalize_cost_metadata(payload.get("cost_metadata")),
        "authority": _normalize_authority(payload.get("authority")),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    expected_outcome_id = terminal_outcome_id(
        repository=projection["repository"],
        pull_request_number=projection["pull_request_number"],
        promotion_id=projection["promotion_id"],
        promoted_head_sha=projection["promoted_head_sha"],
    )
    if normalized["source_artifact_id"] != expected_outcome_id:
        raise CreativeCodeTelemetryContractError(
            "terminal event source_artifact_id does not match projected lineage."
        )
    if status == "closed_unmerged" and (projection["post_merge_observation"] != "not_applicable"):
        raise CreativeCodeTelemetryContractError(
            "closed_unmerged terminal events require not_applicable post-merge observation."
        )
    if status == "merged" and (projection["post_merge_observation"] == "not_applicable"):
        raise CreativeCodeTelemetryContractError(
            "merged terminal events cannot use not_applicable post-merge observation."
        )
    expected_governance = {
        "actionables_observed": "blockers_observed",
        "no_actionables_observed": "no_blockers_observed",
        "evidence_unavailable": "evidence_unavailable",
    }[projection["review_observation"]]
    if projection["governance_observation"] != expected_governance:
        raise CreativeCodeTelemetryContractError(
            "terminal review and governance observations are inconsistent."
        )
    event_id, idempotency_key = _v2_event_identity(normalized)
    if normalized["event_id"] != event_id:
        raise CreativeCodeTelemetryContractError("v2 event_id does not match event content.")
    if normalized["idempotency_key"] != idempotency_key:
        raise CreativeCodeTelemetryContractError("v2 idempotency_key does not match event content.")
    reject_unsafe_telemetry_value(normalized, label=label)
    return normalized


def validate_creative_code_telemetry_event_any(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Dispatch explicitly by schema and policy without version coercion."""

    version = payload.get("schema_version")
    policy = payload.get("policy_version")
    if version == SCHEMA_VERSION and policy == POLICY_VERSION:
        return validate_creative_code_telemetry_event(payload)
    if version == V2_SCHEMA_VERSION and policy == V2_POLICY_VERSION:
        return validate_creative_code_telemetry_event_v2(payload)
    raise CreativeCodeTelemetryContractError("unsupported creative-code telemetry event version.")


def _normalize_closed_count_map(
    raw: Any,
    *,
    keys: frozenset[str],
    label: str,
) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise CreativeCodeTelemetryContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw, keys, label=label)
    return {
        key: _require_int(
            raw,
            key,
            min_value=0,
            max_value=1_000_000,
            label=label,
        )
        for key in sorted(keys)
    }


def _normalize_v2_rates(raw_rates: Any) -> dict[str, int | None]:
    if not isinstance(raw_rates, dict):
        raise CreativeCodeTelemetryContractError("rates must be a JSON object.")
    _require_exact_keys(raw_rates, V2_RATES_KEYS, label="rates")
    normalized: dict[str, int | None] = {}
    for key in sorted(V2_RATES_KEYS):
        if raw_rates[key] is None:
            normalized[key] = None
        else:
            normalized[key] = _require_int(
                raw_rates,
                key,
                min_value=0,
                max_value=10_000,
                label="rates",
            )
    return normalized


def _normalize_v2_source_rows(raw_rows: Any) -> list[dict[str, str]]:
    if not isinstance(raw_rows, list):
        raise CreativeCodeTelemetryContractError("source_artifacts must be an array.")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    supported_types = SOURCE_ARTIFACT_TYPES | frozenset({"creative_code_terminal_outcome"})
    for index, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            raise CreativeCodeTelemetryContractError(
                f"source_artifacts[{index}] must be an object."
            )
        _require_exact_keys(
            row,
            frozenset(
                {
                    "source_artifact_type",
                    "source_artifact_id",
                    "source_fingerprint",
                }
            ),
            label=f"source_artifacts[{index}]",
        )
        artifact_type = _require_token(
            row,
            "source_artifact_type",
            label=f"source_artifacts[{index}]",
        )
        if artifact_type not in supported_types:
            raise CreativeCodeTelemetryContractError(
                f"source_artifacts[{index}].source_artifact_type is unsupported."
            )
        artifact_id = _require_v2_id(
            row,
            "source_artifact_id",
            label=f"source_artifacts[{index}]",
        )
        fingerprint = _require_fingerprint(
            row, "source_fingerprint", label=f"source_artifacts[{index}]"
        )
        key = (artifact_type, artifact_id)
        if key in seen:
            raise CreativeCodeTelemetryContractError(
                "source_artifacts must not contain duplicate lineages."
            )
        seen.add(key)
        normalized.append(
            {
                "source_artifact_id": artifact_id,
                "source_artifact_type": artifact_type,
                "source_fingerprint": fingerprint,
            }
        )
    return sorted(
        normalized,
        key=lambda row: (
            row["source_artifact_type"],
            row["source_artifact_id"],
        ),
    )


def _normalize_v2_terminal(raw_terminal: Any) -> dict[str, Any]:
    if not isinstance(raw_terminal, dict):
        raise CreativeCodeTelemetryContractError("terminal must be a JSON object.")
    _require_exact_keys(raw_terminal, V2_TERMINAL_KEYS, label="terminal")
    terminal: dict[str, Any] = {
        "outcome_count": _require_int(
            raw_terminal,
            "outcome_count",
            min_value=0,
            max_value=1_000_000,
            label="terminal",
        ),
        "merged": _require_int(
            raw_terminal,
            "merged",
            min_value=0,
            max_value=1_000_000,
            label="terminal",
        ),
        "closed_unmerged": _require_int(
            raw_terminal,
            "closed_unmerged",
            min_value=0,
            max_value=1_000_000,
            label="terminal",
        ),
        "review_observations": _normalize_closed_count_map(
            raw_terminal.get("review_observations"),
            keys=V2_REVIEW_OBSERVATIONS,
            label="terminal.review_observations",
        ),
        "governance_observations": _normalize_closed_count_map(
            raw_terminal.get("governance_observations"),
            keys=V2_GOVERNANCE_OBSERVATIONS,
            label="terminal.governance_observations",
        ),
        "post_merge_observations": _normalize_closed_count_map(
            raw_terminal.get("post_merge_observations"),
            keys=V2_POST_MERGE_OBSERVATIONS,
            label="terminal.post_merge_observations",
        ),
        "process": _normalize_v2_process_totals(raw_terminal.get("process")),
    }
    outcome_count = terminal["outcome_count"]
    if any(total > outcome_count * V2_PROCESS_EVENT_MAX for total in terminal["process"].values()):
        raise CreativeCodeTelemetryContractError(
            "terminal process totals exceed represented terminal outcomes."
        )
    if terminal["merged"] + terminal["closed_unmerged"] != outcome_count:
        raise CreativeCodeTelemetryContractError(
            "terminal outcome count must equal merged plus closed_unmerged."
        )
    for key in (
        "review_observations",
        "governance_observations",
        "post_merge_observations",
    ):
        if sum(terminal[key].values()) != outcome_count:
            raise CreativeCodeTelemetryContractError(
                f"terminal.{key} must account for every terminal outcome."
            )
    review = terminal["review_observations"]
    governance = terminal["governance_observations"]
    if (
        review["actionables_observed"] != governance["blockers_observed"]
        or review["no_actionables_observed"] != governance["no_blockers_observed"]
        or review["evidence_unavailable"] != governance["evidence_unavailable"]
    ):
        raise CreativeCodeTelemetryContractError(
            "terminal review and governance observation counts must stay paired."
        )
    if terminal["post_merge_observations"]["not_applicable"] != terminal["closed_unmerged"]:
        raise CreativeCodeTelemetryContractError(
            "closed_unmerged outcomes require not_applicable post-merge observations."
        )
    return terminal


def _normalize_v2_rollup_cost(raw_cost: Any) -> dict[str, int | None]:
    if not isinstance(raw_cost, dict):
        raise CreativeCodeTelemetryContractError("cost must be a JSON object.")
    _require_exact_keys(raw_cost, V2_ROLLUP_COST_KEYS, label="cost")
    if raw_cost.get("estimated_cost_usd") is not None:
        raise CreativeCodeTelemetryContractError("cost.estimated_cost_usd must stay null.")
    return {
        key: (
            None
            if key == "estimated_cost_usd"
            else _require_int(
                raw_cost,
                key,
                min_value=0,
                max_value=1_000_000,
                label="cost",
            )
        )
        for key in sorted(V2_ROLLUP_COST_KEYS)
    }


def _normalize_v2_caveats(raw_caveats: Any) -> list[str]:
    caveats = _normalize_safe_string_list(
        raw_caveats,
        label="caveats",
        allow_empty=False,
    )
    if any(caveat not in V2_ROLLUP_CAVEATS for caveat in caveats):
        raise CreativeCodeTelemetryContractError(
            "caveats must use the closed v2 rollup vocabulary."
        )
    return caveats


def _validate_v2_legacy_aggregates(
    *,
    legacy_event_count: int,
    funnel: Mapping[str, int],
    rates: Mapping[str, int | None],
    rejections_by_class: Mapping[str, int],
    failures_by_class: Mapping[str, int],
    events_by_stage: Mapping[str, int],
    events_by_status: Mapping[str, int],
) -> None:
    stage_funnel_keys = {
        "specification_bundles": "specification",
        "patch_results": "patch_evaluation",
        "promotion_plans": "promotion_plan",
    }
    if any(
        funnel[funnel_key] != events_by_stage.get(stage, 0)
        for funnel_key, stage in stage_funnel_keys.items()
    ):
        raise CreativeCodeTelemetryContractError(
            "legacy funnel stage counts must match represented legacy events."
        )
    if (
        funnel["patch_results_accepted"] + funnel["patch_results_rejected"]
        > funnel["patch_results"]
    ):
        raise CreativeCodeTelemetryContractError(
            "legacy patch disposition counts exceed patch results."
        )
    if funnel["variants_selected"] > funnel["variants_total"]:
        raise CreativeCodeTelemetryContractError("legacy selected variants exceed total variants.")
    stage_upper_bounds = {
        "promotion_validations_passed": "promotion_validation",
        "promotion_approvals": "promotion_approval",
        "pull_requests_opened": "pr_open",
    }
    if any(
        funnel[funnel_key] > events_by_stage.get(stage, 0)
        for funnel_key, stage in stage_upper_bounds.items()
    ):
        raise CreativeCodeTelemetryContractError(
            "legacy funnel counts exceed their represented stages."
        )
    accepted_funnel_total = (
        funnel["patch_results_accepted"]
        + funnel["promotion_validations_passed"]
        + funnel["promotion_approvals"]
    )
    if (
        accepted_funnel_total > events_by_status.get("accepted", 0)
        or funnel["patch_results_rejected"] > events_by_status.get("rejected", 0)
        or funnel["pull_requests_opened"] > events_by_status.get("opened", 0)
    ):
        raise CreativeCodeTelemetryContractError(
            "legacy funnel statuses exceed represented event statuses."
        )
    tracked_accepted_stage_total = (
        funnel["patch_results"]
        + events_by_stage.get("promotion_validation", 0)
        + events_by_stage.get("promotion_approval", 0)
    )
    minimum_tracked_accepted = max(
        0,
        tracked_accepted_stage_total + events_by_status.get("accepted", 0) - legacy_event_count,
    )
    minimum_patch_rejected = max(
        0,
        funnel["patch_results"] + events_by_status.get("rejected", 0) - legacy_event_count,
    )
    minimum_pr_opened = max(
        0,
        events_by_stage.get("pr_open", 0) + events_by_status.get("opened", 0) - legacy_event_count,
    )
    if (
        accepted_funnel_total < minimum_tracked_accepted
        or funnel["patch_results_rejected"] < minimum_patch_rejected
        or funnel["pull_requests_opened"] < minimum_pr_opened
    ):
        raise CreativeCodeTelemetryContractError(
            "legacy funnel statuses underrepresent represented event marginals."
        )
    expected_rates = {
        "first_pass_acceptance_rate_bps": compute_bps(
            funnel["patch_results_accepted"],
            funnel["patch_results"],
        ),
        "human_approval_rate_bps": compute_bps(
            funnel["promotion_approvals"],
            funnel["promotion_plans"],
        ),
        "oracle_pass_rate_bps": compute_bps(
            funnel["patch_results_accepted"],
            funnel["patch_results"],
        ),
        "promotion_rate_bps": compute_bps(
            funnel["pull_requests_opened"],
            funnel["patch_results_accepted"],
        ),
    }
    if any(rates[key] != expected for key, expected in expected_rates.items()):
        raise CreativeCodeTelemetryContractError("legacy rates do not match legacy funnel counts.")
    if sum(rejections_by_class.values()) > legacy_event_count:
        raise CreativeCodeTelemetryContractError(
            "legacy rejection aggregates exceed represented legacy events."
        )
    if sum(failures_by_class.values()) > legacy_event_count:
        raise CreativeCodeTelemetryContractError(
            "legacy failure aggregates exceed represented legacy events."
        )


def build_creative_code_telemetry_rollup_v2(
    events: Sequence[Mapping[str, Any]],
    *,
    input_roots: Sequence[str],
) -> dict[str, Any]:
    """Build a mixed v1/v2 rollup with one terminal count per v2 outcome."""

    normalized_events = [validate_creative_code_telemetry_event_any(event) for event in events]
    normalized_events.sort(key=lambda row: row["event_id"])
    seen_event_ids: set[str] = set()
    seen_sources: dict[tuple[str, str], str] = {}
    seen_terminal_lineages: set[tuple[str, str, int, str]] = set()
    for event in normalized_events:
        event_id = event["event_id"]
        if event_id in seen_event_ids:
            raise CreativeCodeTelemetryContractError("duplicate telemetry event_id.")
        seen_event_ids.add(event_id)
        source_key = (
            event["source_artifact_type"],
            event["source_artifact_id"],
        )
        prior_fingerprint = seen_sources.get(source_key)
        if prior_fingerprint is not None:
            if prior_fingerprint != event["source_fingerprint"]:
                raise CreativeCodeTelemetryContractError("telemetry source fingerprint drift.")
            raise CreativeCodeTelemetryContractError("duplicate telemetry source lineage.")
        seen_sources[source_key] = event["source_fingerprint"]
        if event["schema_version"] == V2_SCHEMA_VERSION:
            projection = event["terminal_projection"]
            lineage = (
                projection["promotion_id"],
                projection["repository"],
                projection["pull_request_number"],
                projection["promoted_head_sha"],
            )
            if lineage in seen_terminal_lineages:
                raise CreativeCodeTelemetryContractError("duplicate terminal outcome lineage.")
            seen_terminal_lineages.add(lineage)

    legacy_events = [
        event for event in normalized_events if event["schema_version"] == SCHEMA_VERSION
    ]
    terminal_events = [
        event for event in normalized_events if event["schema_version"] == V2_SCHEMA_VERSION
    ]
    legacy_rollup = build_creative_code_telemetry_rollup(
        legacy_events,
        input_roots=input_roots,
    )
    events_by_stage: dict[str, int] = {}
    events_by_status: dict[str, int] = {}
    sources: list[dict[str, str]] = []
    for event in normalized_events:
        stage = event["lane_stage"]
        status = event["status"]
        events_by_stage[stage] = events_by_stage.get(stage, 0) + 1
        events_by_status[status] = events_by_status.get(status, 0) + 1
        sources.append(
            {
                "source_artifact_id": event["source_artifact_id"],
                "source_artifact_type": event["source_artifact_type"],
                "source_fingerprint": event["source_fingerprint"],
            }
        )

    review_counts = {key: 0 for key in sorted(V2_REVIEW_OBSERVATIONS)}
    governance_counts = {key: 0 for key in sorted(V2_GOVERNANCE_OBSERVATIONS)}
    post_merge_counts = {key: 0 for key in sorted(V2_POST_MERGE_OBSERVATIONS)}
    process_totals = {key: 0 for key in sorted(V2_PROCESS_KEYS)}
    merged = 0
    closed_unmerged = 0
    terminal_cost_available = 0
    terminal_token_usage_available = 0
    token_keys = (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
    )
    for event in terminal_events:
        if event["status"] == "merged":
            merged += 1
        else:
            closed_unmerged += 1
        projection = event["terminal_projection"]
        review_counts[projection["review_observation"]] += 1
        governance_counts[projection["governance_observation"]] += 1
        post_merge_counts[projection["post_merge_observation"]] += 1
        for key in V2_PROCESS_KEYS:
            process_totals[key] += event["process"][key]
        cost = event["cost_metadata"]
        if cost["available"]:
            terminal_cost_available += 1
            if any(cost[key] is not None for key in token_keys):
                terminal_token_usage_available += 1

    terminal_count = len(terminal_events)
    complete = post_merge_counts["complete_observed"]
    incomplete = post_merge_counts["incomplete_observed"]
    rollup = {
        "schema_version": V2_SCHEMA_VERSION,
        "artifact_type": ROLLUP_TYPE,
        "policy_version": V2_POLICY_VERSION,
        "input_roots": list(input_roots),
        "event_count": len(normalized_events),
        "legacy_event_count": len(legacy_events),
        "funnel": legacy_rollup["funnel"],
        "rates": {
            **legacy_rollup["rates"],
            "merge_rate_bps": compute_bps(merged, terminal_count),
            "post_merge_complete_rate_bps": compute_bps(
                complete,
                complete + incomplete,
            ),
        },
        "rejections_by_class": legacy_rollup["rejections_by_class"],
        "failures_by_class": legacy_rollup["failures_by_class"],
        "events_by_stage": dict(sorted(events_by_stage.items())),
        "events_by_status": dict(sorted(events_by_status.items())),
        "source_artifacts": sources,
        "terminal": {
            "outcome_count": terminal_count,
            "merged": merged,
            "closed_unmerged": closed_unmerged,
            "review_observations": review_counts,
            "governance_observations": governance_counts,
            "post_merge_observations": post_merge_counts,
            "process": process_totals,
        },
        "cost": {
            "cost_metadata_available_count": (
                legacy_rollup["cost"]["cost_metadata_available_count"] + terminal_cost_available
            ),
            "token_usage_available_count": (
                legacy_rollup["cost"]["token_usage_available_count"]
                + terminal_token_usage_available
            ),
            "terminal_cost_metadata_available_count": terminal_cost_available,
            "terminal_token_usage_available_count": (terminal_token_usage_available),
            "estimated_cost_usd": None,
        },
        "caveats": [
            "local_only",
            "not_merge_readiness_evidence",
            "not_product_runtime_truth",
            "terminal_observation_only",
        ],
        "sanitized": True,
    }
    return validate_creative_code_telemetry_rollup_v2(rollup)


def validate_creative_code_telemetry_rollup_v2(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate v2 mixed rollup structure and terminal accounting identities."""

    label = "CreativeCodeTelemetryRollupV2"
    _require_exact_keys(payload, V2_ROLLUP_KEYS, label=label)
    terminal = _normalize_v2_terminal(payload.get("terminal"))
    normalized = {
        "schema_version": _require_const(payload, "schema_version", V2_SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", ROLLUP_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", V2_POLICY_VERSION, label=label),
        "input_roots": _normalize_safe_string_list(
            payload.get("input_roots"),
            label="input_roots",
            allow_empty=True,
        ),
        "event_count": _require_int(
            payload,
            "event_count",
            min_value=0,
            max_value=1_000_000,
            label=label,
        ),
        "legacy_event_count": _require_int(
            payload,
            "legacy_event_count",
            min_value=0,
            max_value=1_000_000,
            label=label,
        ),
        "funnel": _normalize_funnel(payload.get("funnel")),
        "rates": _normalize_v2_rates(payload.get("rates")),
        "rejections_by_class": _count_map(
            payload.get("rejections_by_class"),
            label="rejections_by_class",
            allowed_keys=frozenset(TAXONOMY_CLASSES),
        ),
        "failures_by_class": _count_map(
            payload.get("failures_by_class"),
            label="failures_by_class",
            allowed_keys=frozenset(TAXONOMY_CLASSES),
        ),
        "events_by_stage": _count_map(
            payload.get("events_by_stage"),
            label="events_by_stage",
            allowed_keys=LANE_STAGES | frozenset({"pr_terminal"}),
        ),
        "events_by_status": _count_map(
            payload.get("events_by_status"),
            label="events_by_status",
            allowed_keys=EVENT_STATUSES | V2_TERMINAL_STATUSES,
        ),
        "source_artifacts": _normalize_v2_source_rows(payload.get("source_artifacts")),
        "terminal": terminal,
        "cost": _normalize_v2_rollup_cost(payload.get("cost")),
        "caveats": _normalize_v2_caveats(payload.get("caveats")),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if normalized["event_count"] != sum(normalized["events_by_stage"].values()):
        raise CreativeCodeTelemetryContractError("event_count must match events_by_stage total.")
    if normalized["event_count"] != sum(normalized["events_by_status"].values()):
        raise CreativeCodeTelemetryContractError("event_count must match events_by_status total.")
    if normalized["event_count"] != (normalized["legacy_event_count"] + terminal["outcome_count"]):
        raise CreativeCodeTelemetryContractError(
            "event_count must equal legacy events plus terminal outcomes."
        )
    if normalized["events_by_stage"].get("pr_terminal", 0) != terminal["outcome_count"]:
        raise CreativeCodeTelemetryContractError(
            "pr_terminal event count must equal terminal outcome count."
        )
    if (
        normalized["events_by_status"].get("merged", 0) != terminal["merged"]
        or normalized["events_by_status"].get("closed_unmerged", 0) != terminal["closed_unmerged"]
    ):
        raise CreativeCodeTelemetryContractError(
            "terminal status counts must match terminal observations."
        )
    if len(normalized["source_artifacts"]) != normalized["event_count"]:
        raise CreativeCodeTelemetryContractError(
            "source_artifacts must bind every event exactly once."
        )
    terminal_source_count = sum(
        row["source_artifact_type"] == "creative_code_terminal_outcome"
        for row in normalized["source_artifacts"]
    )
    if terminal_source_count != terminal["outcome_count"]:
        raise CreativeCodeTelemetryContractError(
            "terminal source artifact count must equal terminal outcome count."
        )
    legacy_source_counts = {source_type: 0 for source_type in LEGACY_SOURCE_TYPE_TO_STAGE}
    for row in normalized["source_artifacts"]:
        source_type = row["source_artifact_type"]
        if source_type in legacy_source_counts:
            legacy_source_counts[source_type] += 1
    if any(
        legacy_source_counts[source_type] != normalized["events_by_stage"].get(stage, 0)
        for source_type, stage in LEGACY_SOURCE_TYPE_TO_STAGE.items()
    ):
        raise CreativeCodeTelemetryContractError(
            "legacy source artifact counts must match legacy stage counts."
        )
    if normalized["legacy_event_count"] == 0 and (
        any(normalized["funnel"].values())
        or any(normalized["rates"][key] is not None for key in RATES_KEYS)
        or any(normalized["rejections_by_class"].values())
        or any(normalized["failures_by_class"].values())
    ):
        raise CreativeCodeTelemetryContractError(
            "zero legacy events require empty legacy aggregates."
        )
    if normalized["legacy_event_count"] > 0:
        _validate_v2_legacy_aggregates(
            legacy_event_count=normalized["legacy_event_count"],
            funnel=normalized["funnel"],
            rates=normalized["rates"],
            rejections_by_class=normalized["rejections_by_class"],
            failures_by_class=normalized["failures_by_class"],
            events_by_stage=normalized["events_by_stage"],
            events_by_status=normalized["events_by_status"],
        )
    expected_merge_rate = compute_bps(terminal["merged"], terminal["outcome_count"])
    if normalized["rates"]["merge_rate_bps"] != expected_merge_rate:
        raise CreativeCodeTelemetryContractError("merge_rate_bps does not match terminal counts.")
    complete = terminal["post_merge_observations"]["complete_observed"]
    incomplete = terminal["post_merge_observations"]["incomplete_observed"]
    expected_post_merge_rate = compute_bps(complete, complete + incomplete)
    if normalized["rates"]["post_merge_complete_rate_bps"] != expected_post_merge_rate:
        raise CreativeCodeTelemetryContractError(
            "post_merge_complete_rate_bps does not match observed validation counts."
        )
    cost = normalized["cost"]
    total_cost_available = cost["cost_metadata_available_count"]
    total_token_usage_available = cost["token_usage_available_count"]
    terminal_cost_available = cost["terminal_cost_metadata_available_count"]
    terminal_token_usage_available = cost["terminal_token_usage_available_count"]
    legacy_cost_available = total_cost_available - terminal_cost_available
    legacy_token_usage_available = total_token_usage_available - terminal_token_usage_available
    if (
        total_cost_available > normalized["event_count"]
        or total_token_usage_available > total_cost_available
        or terminal_cost_available > terminal["outcome_count"]
        or terminal_token_usage_available > terminal_cost_available
        or terminal_cost_available > total_cost_available
        or terminal_token_usage_available > total_token_usage_available
        or legacy_cost_available > normalized["legacy_event_count"]
        or legacy_token_usage_available > legacy_cost_available
    ):
        raise CreativeCodeTelemetryContractError(
            "cost availability counts are inconsistent with represented events."
        )
    reject_unsafe_telemetry_value(normalized, label=label)
    return normalized


def validate_creative_code_telemetry_rollup_any(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Dispatch rollup validation without silently coercing unknown versions."""

    version = payload.get("schema_version")
    policy = payload.get("policy_version")
    if version == SCHEMA_VERSION and policy == POLICY_VERSION:
        return validate_creative_code_telemetry_rollup(payload)
    if version == V2_SCHEMA_VERSION and policy == V2_POLICY_VERSION:
        return validate_creative_code_telemetry_rollup_v2(payload)
    raise CreativeCodeTelemetryContractError("unsupported creative-code telemetry rollup version.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PR-4 creative-code telemetry contracts.")
    parser.add_argument("--validate-event", help="Path to telemetry event JSON.")
    parser.add_argument("--validate-rollup", help="Path to telemetry rollup JSON.")
    parser.add_argument("--validate-taxonomy", help="Path to rejection taxonomy JSON.")
    args = parser.parse_args(argv)

    validators = [
        (args.validate_event, validate_creative_code_telemetry_event_any),
        (args.validate_rollup, validate_creative_code_telemetry_rollup_any),
        (args.validate_taxonomy, validate_creative_code_rejection_taxonomy),
    ]
    try:
        ran = False
        for path, validator in validators:
            if not path:
                continue
            validator(read_json_object(path))
            ran = True
        if not ran:
            build_creative_code_rejection_taxonomy()
    except CreativeCodeTelemetryContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

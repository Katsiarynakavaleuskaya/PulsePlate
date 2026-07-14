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


class CreativeCodeTelemetryContractError(ValueError):
    """Raised when creative-code telemetry violates PR-4 boundaries."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodeTelemetryContractError(
                f"creative-code telemetry JSON has duplicate key: {key}"
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
        raise CreativeCodeTelemetryContractError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )


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
    if value is not expected:
        raise CreativeCodeTelemetryContractError(f"{label}.{key} must be {expected}.")
    return expected


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PR-4 creative-code telemetry contracts.")
    parser.add_argument("--validate-event", help="Path to telemetry event JSON.")
    parser.add_argument("--validate-rollup", help="Path to telemetry rollup JSON.")
    parser.add_argument("--validate-taxonomy", help="Path to rejection taxonomy JSON.")
    args = parser.parse_args(argv)

    validators = [
        (args.validate_event, validate_creative_code_telemetry_event),
        (args.validate_rollup, validate_creative_code_telemetry_rollup),
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

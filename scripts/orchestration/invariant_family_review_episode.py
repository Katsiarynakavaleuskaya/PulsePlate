#!/usr/bin/env python3
"""Prospective, local, authority-free invariant-family episode evidence rail."""

from __future__ import annotations

import ctypes
import datetime as datetime_module
import errno
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import NoReturn, cast

POLICY_VERSION = "invariant_family_review_episode.policy.v1"
REPOSITORY_SLUG = "Katsiarynakavaleuskaya/PulsePlate"
TRANSPORT_CAPABILITY = "fixed_local_create_only"

ENROLLMENT_INPUT_SCHEMA = "invariant_family_review_episode.enrollment_input.v1"
ENROLLMENT_RECEIPT_SCHEMA = "invariant_family_review_episode.enrollment_receipt.v1"
BASELINE_INPUT_SCHEMA = "invariant_family_review_episode.joint_pass_baseline_input.v1"
TERMINAL_INPUT_SCHEMA = "invariant_family_review_episode.terminal_input.v1"
TERMINAL_RECEIPT_SCHEMA = "invariant_family_review_episode.terminal_receipt.v1"
REPORT_REQUEST_SCHEMA = "invariant_family_review_episode.report_request.v1"
REPORT_SCHEMA = "invariant_family_review_episode.report.v1"
ACK_SCHEMA = "invariant_family_review_episode.ack.v1"

EPISODE_DOMAIN = "pulseplate.invariant-family-review-episode.episode.v1"
ENROLLMENT_RECEIPT_DOMAIN = "pulseplate.invariant-family-review-episode.enrollment-receipt.v1"
BASELINE_DOMAIN = "pulseplate.invariant-family-review-episode.joint-pass-baseline.v1"
TERMINAL_RECEIPT_DOMAIN = "pulseplate.invariant-family-review-episode.terminal-receipt.v1"
COHORT_DOMAIN = "pulseplate.invariant-family-review-episode.cohort.v1"
REPORT_DOMAIN = "pulseplate.invariant-family-review-episode.report.v1"

MAX_STDIN_BYTES = 1_048_576
MAX_STDOUT_BYTES = 4_096
MAX_STDERR_BYTES = 4_096
MAX_ENROLLMENT_RECEIPT_BYTES = 262_144
MAX_TERMINAL_RECEIPT_BYTES = 262_144
MAX_REPORT_JSON_BYTES = 2_097_152
MAX_REPORT_MARKDOWN_BYTES = 2_097_152
MAX_REPORT_BUNDLE_BYTES = 4_194_304
MAX_AGGREGATE_RECEIPT_SCAN_BYTES = 16_777_216
MAX_ENROLLMENT_BUNDLES = 128
MAX_TERMINAL_BUNDLES = 128
MAX_REPORT_GENERATIONS = 64
MAX_FAMILIES = 32
MAX_SOURCE_FINDING_IDS = 2_048
MAX_FAMILY_MEMBERSHIP_REFS = 4_096
MAX_IDENTITY_ROWS = 512
MAX_TRIGGER_IDENTITIES = 16
MAX_STAGING_ATTEMPTS = 32
MAX_JSON_DEPTH = 12
MAX_JSON_NODES = 16_384
MAX_SCALAR_ASCII_BYTES = 256
MAX_ID_ASCII_BYTES = 64

STORE_COMPONENTS = (
    "artifacts",
    "orchestration",
    "review_invariant_family_episodes",
)
LANE_NAMES = ("enrollments", "terminals", "reports")
BUNDLE_SHAPES = {
    "receipt": ("receipt.json",),
    "report": ("report.json", "report.md"),
}

AUTHORITY_FIELDS = (
    "side_effects_allowed",
    "posting_allowed",
    "thread_resolution_allowed",
    "mapping_authority",
    "implementation_authority",
    "approval_authority",
    "review_authority",
    "security_authority",
    "runtime_authority",
    "learning_authority",
    "reflection_authority",
    "kpp_authority",
    "oracle_authority",
    "routing_authority",
    "promotion_authority",
    "merge_authority",
)

EPISODE_CLASSES = ("prospective_primary", "retrospective_reference")
TERMINAL_STATES = ("merged", "closed_unmerged")
JOINT_PASS_STATUSES = (
    "not_completed",
    "completed_baseline_unavailable",
    "completed_baseline_available",
)
PHASES = ("trigger", "joint_pass", "terminal")
RECOMMENDED_RESOLUTIONS = (
    "bounded_object_fix",
    "family_fix",
    "mechanism_fix",
    "authority_rescope",
    "no_change_required",
    "unknown_requires_human",
)
FAMILY_UNKNOWN_REASONS = (
    "joint_pass_baseline_unavailable",
    "human_correspondence_unresolved",
    "terminal_cumulative_inventory_incomplete",
)
FAMILY_NON_COMPARABLE_REASONS = (
    "family_redefined",
    "family_missing",
    "membership_disputed",
    "non_bijective_identity",
)
FAMILY_STATUS_CONFIRMED = "confirmed"
FAMILY_STATUS_UNKNOWN = "unknown"
FAMILY_STATUS_NON_COMPARABLE = "non_comparable"
FAMILY_OBSERVATION_STATUSES = (
    FAMILY_STATUS_CONFIRMED,
    FAMILY_STATUS_UNKNOWN,
    FAMILY_STATUS_NON_COMPARABLE,
)
FAMILY_CONFIRMED_REASONS = ("same_scope_confirmed",)
EPISODE_STATUS_OBSERVED = "observed"
EPISODE_STATUS_UNKNOWN = "unknown"
EPISODE_STATUS_NON_COMPARABLE = "non_comparable"
EPISODE_STATUS_NOT_APPLICABLE = "not_applicable"
EPISODE_OBSERVATION_STATUSES = (
    EPISODE_STATUS_OBSERVED,
    EPISODE_STATUS_UNKNOWN,
    EPISODE_STATUS_NON_COMPARABLE,
    EPISODE_STATUS_NOT_APPLICABLE,
)
RATIO_STATUS_DEFINED = "defined"
RATIO_STATUS_NOT_APPLICABLE = "not_applicable"
RATIO_STATUSES = (RATIO_STATUS_DEFINED, RATIO_STATUS_NOT_APPLICABLE)
EPISODE_OBSERVATION_REASONS = (
    "positive",
    "zero",
    "multi_trigger",
    "not_completed_before_terminal",
    "joint_pass_baseline_unavailable",
    "family_observation_unknown",
    "family_observation_non_comparable",
    "missing_terminal",
)
ACCRUAL_BANDS = (
    "collecting_lt_5",
    "interim_5_to_9",
    "target_count_gte_10",
)

ERROR_CODES = (
    "E_USAGE",
    "E_INPUT_TOO_LARGE",
    "E_JSON_INVALID",
    "E_SCHEMA",
    "E_LIMIT",
    "E_IDENTITY",
    "E_ORDER",
    "E_DEPENDENCY",
    "E_STORE_UNSAFE",
    "E_LOCK_BUSY",
    "E_REPLAY_DIVERGENT",
    "E_PUBLISH_UNSUPPORTED",
    "E_PUBLISH_FAILED",
    "E_REPORT_MANIFEST",
    "E_STDOUT",
)

RECEIPT_CLAIMS = {
    "causal_status": "not_assessed",
    "claim_type": "descriptive_observation",
    "observation_basis": "human_digest_referenced",
}
FALSE_GRANTS = {field: False for field in AUTHORITY_FIELDS}

_ID_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,62}[A-Za-z0-9])?$"
_ID_RE = re.compile(_ID_PATTERN, re.ASCII)
_DIGEST_RE = re.compile(r"^[a-f0-9]{64}$", re.ASCII)
_COMMIT_RE = re.compile(r"^[a-f0-9]{40}$", re.ASCII)
_TASK_PACKET_ID_RE = re.compile(r"^[a-f0-9]{12}$", re.ASCII)
_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_L1_FINGERPRINT_RE = re.compile(r"^sha256:([a-f0-9]{64})$", re.ASCII)
_L1_IDEMPOTENCY_RE = re.compile(r"^review-invariant-family-relations\.v1:([a-f0-9]{64})$", re.ASCII)
_FORBIDDEN_ID_PATTERN = (
    r"(?:access[_-]?key|aiza|ak[is]a|api[_-]?key|authorization|bearer|"
    r"client[_-]?secret|credential|gh[prous]_|github[_-]?pat|gitlab[_-]?pat|"
    r"glpat-|npm_|password|private[_-]?key|secret|sk-[A-Za-z0-9_-]{12,}|"
    r"sk[_-]?(?:live|test|proj)|token|xapp-|xox[abcdeprst]-)"
)
_FORBIDDEN_ID_RE = re.compile(_FORBIDDEN_ID_PATTERN, re.IGNORECASE | re.ASCII)
_FULL_DIGEST_NAME_RE = re.compile(r"^[a-f0-9]{64}$", re.ASCII)

_ENROLLMENT_INPUT_FIELDS = frozenset(
    {
        "schema_version",
        "episode_class",
        "pull_request_number",
        "trigger_observed_at",
        "enrollment_recorded_at",
        "material_head_sha",
        "source",
        "identity_classes",
        "families",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "l2_task_packet_id",
        "l2_task_packet_digest",
        "l1_artifact_fingerprint",
        "l1_idempotency_key",
        "trigger_rule",
        "membership_source",
    }
)
_ENROLLMENT_IDENTITY_FIELDS = frozenset({"identity_class_id", "trigger_finding_id"})
_ENROLLMENT_FAMILY_FIELDS = frozenset(
    {"family_key", "trigger_family_id", "trigger_identity_class_ids"}
)
_BASELINE_FIELDS = frozenset(
    {
        "schema_version",
        "episode_digest",
        "enrollment_receipt_digest",
        "joint_pass_completed_at",
        "identity_classes",
        "families",
    }
)
_IDENTITY_CLASS_FIELDS = frozenset({"identity_class_id", "phase_bindings"})
_PHASE_BINDING_FIELDS = frozenset({"phase", "finding_id"})
_BASELINE_FAMILY_FIELDS = frozenset(
    {
        "family_key",
        "joint_pass_family_id",
        "joint_pass_cumulative_identity_class_ids",
        "recommended_resolution",
    }
)
_TERMINAL_INPUT_FIELDS = frozenset(
    {
        "schema_version",
        "episode_digest",
        "enrollment_receipt_digest",
        "terminal_state",
        "terminal_event_at",
        "terminal_recorded_at",
        "terminal_material_head_sha",
        "observed_l2_identity_digests",
        "joint_pass",
    }
)
_REPORT_REQUEST_FIELDS = frozenset({"schema_version", "cohort_as_of"})

SUPERVISION_POLICY_VERSION = "invariant_family_review_episode.supervision.policy.v1"
CHECKPOINT_RECEIPT_SCHEMA = "invariant_family_review_episode.checkpoint_receipt.v1"
CHECKPOINT_RECEIPT_DOMAIN = "pulseplate.invariant-family-review-episode.checkpoint-receipt.v1"
STATUS_REQUEST_SCHEMA = "invariant_family_review_episode.status_request.v1"
COMPLETE_INPUT_SCHEMA = "invariant_family_review_episode.complete_input.v1"
SUPERVISION_ACK_SCHEMA = "invariant_family_review_episode.supervision_ack.v1"
MAX_CHECKPOINT_BUNDLES = 128
MAX_CHECKPOINT_RECEIPT_BYTES = 262_144
SUPERVISION_VERBS = ("checkpoint", "status", "complete")
SUPERVISION_STATES = (
    "absent",
    "enrolled_awaiting_checkpoint",
    "enrolled_awaiting_terminal",
    "terminal_awaiting_report",
    "complete",
)
_STATUS_REQUEST_FIELDS = frozenset({"schema_version", "pull_request_number"})
_COMPLETE_INPUT_FIELDS = frozenset({"schema_version", "terminal", "report_request"})
_CHECKPOINT_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "policy_version",
        "repository_slug",
        "pull_request_number",
        "episode_digest",
        "enrollment_receipt_digest",
        "baseline",
        "joint_pass_baseline_digest",
        "validate_acknowledgement",
        "claims",
        "downstream_grants",
        "transport_capability",
        "checkpoint_receipt_digest",
    }
)


def _freeze_policy(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze_policy(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_policy(item) for item in value)
    return value


def _policy_source() -> dict[str, object]:
    return {
        "acknowledgment": {
            "common_fields": ["schema_version", "status", "operation"],
            "operation_fields": {
                "enroll": ["episode_digest", "enrollment_receipt_digest"],
                "report": ["cohort_id", "report_digest", "markdown_sha256"],
                "terminal": ["episode_digest", "terminal_receipt_digest"],
                "validate": ["episode_digest", "joint_pass_baseline_digest"],
            },
            "schema_version": ACK_SCHEMA,
            "status": "ok",
        },
        "authority_fields": list(AUTHORITY_FIELDS),
        "claims": {
            "receipt": dict(RECEIPT_CLAIMS),
            "report_extra": {"all_eligible_episodes_claim": False},
        },
        "cli": {
            "exact_argv_count": 1,
            "stdin_documents": 1,
            "verbs": ["enroll", "terminal", "validate", "report"],
        },
        "digest": {
            "algorithm": "sha256",
            "domains": {
                "cohort": COHORT_DOMAIN,
                "enrollment_receipt": ENROLLMENT_RECEIPT_DOMAIN,
                "episode": EPISODE_DOMAIN,
                "joint_pass_baseline": BASELINE_DOMAIN,
                "report": REPORT_DOMAIN,
                "terminal_receipt": TERMINAL_RECEIPT_DOMAIN,
            },
            "encoding": "canonical_ascii_json_without_lf",
            "separator": "NUL",
        },
        "enums": {
            "accrual_bands": list(ACCRUAL_BANDS),
            "episode_classes": list(EPISODE_CLASSES),
            "episode_observation_reasons": list(EPISODE_OBSERVATION_REASONS),
            "episode_observation_statuses": list(EPISODE_OBSERVATION_STATUSES),
            "family_confirmed_reasons": list(FAMILY_CONFIRMED_REASONS),
            "family_non_comparable_reasons": list(FAMILY_NON_COMPARABLE_REASONS),
            "family_observation_statuses": list(FAMILY_OBSERVATION_STATUSES),
            "family_unknown_reasons": list(FAMILY_UNKNOWN_REASONS),
            "joint_pass_statuses": list(JOINT_PASS_STATUSES),
            "phases": list(PHASES),
            "ratio_statuses": list(RATIO_STATUSES),
            "recommended_resolutions": list(RECOMMENDED_RESOLUTIONS),
            "terminal_states": list(TERMINAL_STATES),
        },
        "errors": list(ERROR_CODES),
        "limits": {
            "aggregate_receipt_scan_bytes": MAX_AGGREGATE_RECEIPT_SCAN_BYTES,
            "enrollment_bundles": MAX_ENROLLMENT_BUNDLES,
            "enrollment_receipt_json_bytes": MAX_ENROLLMENT_RECEIPT_BYTES,
            "families": MAX_FAMILIES,
            "family_membership_refs": MAX_FAMILY_MEMBERSHIP_REFS,
            "hierarchy_depth_below_lane_root": 3,
            "identity_correspondence_rows_per_table": MAX_IDENTITY_ROWS,
            "json_depth": MAX_JSON_DEPTH,
            "json_nodes": MAX_JSON_NODES,
            "report_bundle_bytes": MAX_REPORT_BUNDLE_BYTES,
            "report_generations": MAX_REPORT_GENERATIONS,
            "report_json_bytes": MAX_REPORT_JSON_BYTES,
            "report_markdown_bytes": MAX_REPORT_MARKDOWN_BYTES,
            "scalar_ascii_bytes": MAX_SCALAR_ASCII_BYTES,
            "source_finding_id_refs_per_document": MAX_SOURCE_FINDING_IDS,
            "source_finding_ids": MAX_SOURCE_FINDING_IDS,
            "staging_name_attempts": MAX_STAGING_ATTEMPTS,
            "stderr_bytes": MAX_STDERR_BYTES,
            "stdin_bytes": MAX_STDIN_BYTES,
            "stdout_bytes": MAX_STDOUT_BYTES,
            "terminal_bundles": MAX_TERMINAL_BUNDLES,
            "terminal_receipt_json_bytes": MAX_TERMINAL_RECEIPT_BYTES,
            "trigger_identities": MAX_TRIGGER_IDENTITIES,
        },
        "parser": {
            "commit_sha_pattern": r"^[a-f0-9]{40}$",
            "credential_denylist_flags": "ASCII_IGNORECASE",
            "credential_denylist_pattern": _FORBIDDEN_ID_PATTERN,
            "digest_pattern": r"^[a-f0-9]{64}$",
            "duplicate_keys": "reject_at_every_depth",
            "id_ascii_bytes": MAX_ID_ASCII_BYTES,
            "id_pattern": _ID_PATTERN,
            "json_numbers": "integers_only_where_schema_allows",
            "null": "reject",
            "task_packet_id_pattern": r"^[a-f0-9]{12}$",
            "timestamp_pattern": "YYYY-MM-DDTHH:MM:SSZ_calendar_valid_utc",
            "utf8": "strict_no_bom_ascii_scalars",
        },
        "policy_version": POLICY_VERSION,
        "report": {
            "accrual_basis": "identified_episode_count",
            "cohort_semantics": (
                "complete_current_store_as_of_must_cover_every_current_receipt_boundary"
            ),
            "primary_formulas": {
                "eligible_denominator_count": "enrollment_count-not_applicable_count",
                "identified_episode_count": "positive_count+zero_count",
                "identified_coverage_ratio": (
                    "identified_episode_count/eligible_denominator_count"
                ),
                "recurrence_lower_bound_ratio": ("positive_count/eligible_denominator_count"),
                "recurrence_upper_bound_ratio": (
                    "(positive_count+unknown_count+non_comparable_count)/"
                    "eligible_denominator_count"
                ),
                "terminal_coverage_ratio": "terminal_receipt_count/enrollment_count",
            },
            "primary_fields": [
                "enrollment_count",
                "terminal_receipt_count",
                "positive_count",
                "zero_count",
                "unknown_count",
                "non_comparable_count",
                "not_applicable_count",
                "eligible_denominator_count",
                "identified_episode_count",
                "recurrence_lower_bound_ratio",
                "recurrence_upper_bound_ratio",
                "terminal_coverage_ratio",
                "identified_coverage_ratio",
                "accrual_band",
            ],
            "ratio_shapes": {
                "defined_fields": ["status", "numerator", "denominator"],
                "not_applicable_fields": ["status", "reason"],
                "zero_denominator_reason": "zero_denominator",
            },
            "retrospective_fields": [
                "enrollment_count",
                "terminal_receipt_count",
                "positive_count",
                "zero_count",
                "unknown_count",
                "non_comparable_count",
                "not_applicable_count",
            ],
        },
        "repository_slug": REPOSITORY_SLUG,
        "schemas": {
            "enrollment_input": {
                "fields": [
                    "schema_version",
                    "episode_class",
                    "pull_request_number",
                    "trigger_observed_at",
                    "enrollment_recorded_at",
                    "material_head_sha",
                    "source",
                    "identity_classes",
                    "families",
                ],
                "schema_version": ENROLLMENT_INPUT_SCHEMA,
            },
            "enrollment_identity": {"fields": ["identity_class_id", "trigger_finding_id"]},
            "enrollment_family": {
                "fields": [
                    "family_key",
                    "trigger_family_id",
                    "trigger_identity_class_ids",
                ]
            },
            "enrollment_receipt": {
                "fields": [
                    "schema_version",
                    "policy_version",
                    "repository_slug",
                    "pull_request_number",
                    "episode_digest",
                    "enrollment_receipt_digest",
                    "episode_class",
                    "trigger_observed_at",
                    "enrollment_recorded_at",
                    "material_head_sha",
                    "source",
                    "identity_classes",
                    "families",
                    "claims",
                    "downstream_grants",
                    "transport_capability",
                ],
                "schema_version": ENROLLMENT_RECEIPT_SCHEMA,
            },
            "identity_class": {
                "fields": ["identity_class_id", "phase_bindings"],
                "phase_binding_fields": ["phase", "finding_id"],
            },
            "joint_pass_union": {
                "completed_baseline_available_fields": [
                    "status",
                    "baseline",
                    "joint_pass_baseline_digest",
                    "identity_classes",
                    "family_observations",
                ],
                "completed_baseline_unavailable_fields": [
                    "status",
                    "reason",
                    "joint_pass_completed_at",
                ],
                "not_completed_fields": ["status", "reason"],
            },
            "family_observation_input": {
                "confirmed_fields": [
                    "status",
                    "reason",
                    "family_key",
                    "terminal_family_id",
                    "terminal_cumulative_identity_class_ids",
                ],
                "non_observed_fields": ["status", "reason", "family_key"],
            },
            "family_observation_receipt_confirmed": {
                "fields": [
                    "status",
                    "reason",
                    "family_key",
                    "joint_pass_family_id",
                    "terminal_family_id",
                    "joint_pass_cumulative_identity_class_ids",
                    "terminal_cumulative_identity_class_ids",
                    "recommended_resolution",
                    "post_joint_same_family_first_observed_identity_class_ids",
                    "post_joint_same_family_first_observed_count",
                ]
            },
            "joint_pass_baseline": {
                "family_fields": [
                    "family_key",
                    "joint_pass_family_id",
                    "joint_pass_cumulative_identity_class_ids",
                    "recommended_resolution",
                ],
                "fields": [
                    "schema_version",
                    "episode_digest",
                    "enrollment_receipt_digest",
                    "joint_pass_completed_at",
                    "identity_classes",
                    "families",
                ],
                "schema_version": BASELINE_INPUT_SCHEMA,
            },
            "report": {
                "fields": [
                    "schema_version",
                    "policy_version",
                    "repository_slug",
                    "cohort_as_of",
                    "cohort_id",
                    "report_digest",
                    "markdown_sha256",
                    "manifest",
                    "prospective_primary",
                    "retrospective_reference",
                    "claims",
                    "downstream_grants",
                    "transport_capability",
                ],
                "schema_version": REPORT_SCHEMA,
            },
            "report_manifest_row": {
                "fields": [
                    "episode_digest",
                    "episode_class",
                    "enrollment_receipt_digest",
                    "terminal_receipt_digest",
                    "observation_status",
                    "observation_reason",
                ]
            },
            "report_request": {
                "fields": ["schema_version", "cohort_as_of"],
                "schema_version": REPORT_REQUEST_SCHEMA,
            },
            "recurrence": {
                "non_observed_fields": ["status", "reason"],
                "observed_fields": ["status", "reason", "value"],
            },
            "source": {
                "fields": [
                    "l2_task_packet_id",
                    "l2_task_packet_digest",
                    "l1_artifact_fingerprint",
                    "l1_idempotency_key",
                    "trigger_rule",
                    "membership_source",
                ],
                "membership_source": "explicit_input_only",
                "trigger_rule": "explicit_family_cardinality_gte_2",
            },
            "terminal_input": {
                "fields": [
                    "schema_version",
                    "episode_digest",
                    "enrollment_receipt_digest",
                    "terminal_state",
                    "terminal_event_at",
                    "terminal_recorded_at",
                    "terminal_material_head_sha",
                    "observed_l2_identity_digests",
                    "joint_pass",
                ],
                "schema_version": TERMINAL_INPUT_SCHEMA,
            },
            "terminal_receipt": {
                "fields": [
                    "schema_version",
                    "policy_version",
                    "repository_slug",
                    "pull_request_number",
                    "episode_digest",
                    "enrollment_receipt_digest",
                    "terminal_receipt_digest",
                    "episode_class",
                    "terminal_state",
                    "terminal_event_at",
                    "terminal_recorded_at",
                    "terminal_material_head_sha",
                    "observed_l2_identity_digests",
                    "joint_pass",
                    "recurrence",
                    "claims",
                    "downstream_grants",
                    "transport_capability",
                ],
                "schema_version": TERMINAL_RECEIPT_SCHEMA,
            },
        },
        "semantics": {
            "cohort_filtering": "none_complete_current_store",
            "episode_identity_fields": ["repository_slug", "pull_request_number"],
            "lifecycle": [
                "ABSENT",
                "ENROLLED_AWAITING_TERMINAL",
                "TERMINAL_OBSERVED",
            ],
            "observation_interval": "(joint_pass_completed_at,terminal_event_at]",
            "recurrence_set_difference": "C_f_minus_J_f",
            "timestamp_order": [
                "trigger_observed_at",
                "enrollment_recorded_at",
                "joint_pass_completed_at",
                "terminal_event_at",
                "terminal_recorded_at",
            ],
        },
        "store": {
            "bundle_shapes": {
                "receipt": ["receipt.json"],
                "report": ["report.json", "report.md"],
            },
            "directory_mode": "0700",
            "file_mode": "0600",
            "layout": {
                "enrollments": "enrollments/<episode_digest>/receipt.json",
                "reports": "reports/<report_digest>/{report.json,report.md}",
                "terminals": "terminals/<episode_digest>/receipt.json",
            },
            "lock": (
                "parent_initialization_flock_then_module_root_nonblocking_"
                "exclusive_publish_shared_validate"
            ),
            "no_replace": {
                "darwin": "renameatx_np_RENAME_EXCL",
                "linux": "renameat2_RENAME_NOREPLACE",
                "fallback": "none",
            },
            "root": "artifacts/orchestration/review_invariant_family_episodes",
            "supported_platforms": ["darwin", "linux"],
        },
        "transport_capability": TRANSPORT_CAPABILITY,
    }


POLICY_PROJECTION = cast(Mapping[str, object], _freeze_policy(_policy_source()))

SUPERVISION_PROJECTION = cast(
    Mapping[str, object],
    _freeze_policy(
        {
            "policy_version": SUPERVISION_POLICY_VERSION,
            "verbs": list(SUPERVISION_VERBS),
            "lifecycle": list(SUPERVISION_STATES),
            "report_states": ["absent", "stale", "current"],
            "checkpoint": {
                "input_schema": BASELINE_INPUT_SCHEMA,
                "receipt_schema": CHECKPOINT_RECEIPT_SCHEMA,
                "receipt_fields": sorted(_CHECKPOINT_RECEIPT_FIELDS),
                "digest_domain": CHECKPOINT_RECEIPT_DOMAIN,
                "layout": "checkpoints/<episode_digest>/receipt.json",
                "maximum_bundles": MAX_CHECKPOINT_BUNDLES,
                "maximum_receipt_bytes": MAX_CHECKPOINT_RECEIPT_BYTES,
                "optional_lane": True,
            },
            "status": {
                "input_schema": STATUS_REQUEST_SCHEMA,
                "input_fields": sorted(_STATUS_REQUEST_FIELDS),
                "store_creation": False,
                "report_selection": "maximum_cohort_as_of_then_digest_of_exact_manifest_matches",
            },
            "complete": {
                "input_schema": COMPLETE_INPUT_SCHEMA,
                "input_fields": sorted(_COMPLETE_INPUT_FIELDS),
                "terminal_input_schema": TERMINAL_INPUT_SCHEMA,
                "report_request_schema": REPORT_REQUEST_SCHEMA,
                "publication_order": ["terminal", "report"],
                "available_baseline_requires_checkpoint": True,
            },
            "acknowledgement_schema": SUPERVISION_ACK_SCHEMA,
            "aggregate_receipt_scan_bytes": MAX_AGGREGATE_RECEIPT_SCAN_BYTES,
            "downstream_grants": dict(FALSE_GRANTS),
        }
    ),
)


class EpisodeError(Exception):
    """Stable, sanitized failure with no submitted values or local paths."""

    def __init__(self, code: str) -> None:
        safe_code = code if code in ERROR_CODES else "E_SCHEMA"
        self.code = safe_code
        super().__init__(safe_code)


def _fail(code: str) -> NoReturn:
    raise EpisodeError(code)


def _canonical_json_bytes(
    value: Mapping[str, object] | list[object], *, trailing_lf: bool = False
) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        _fail("E_SCHEMA")
    return rendered + (b"\n" if trailing_lf else b"")


def _plain_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _domain_digest(domain: str, value: Mapping[str, object]) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\0" + _canonical_json_bytes(value)).hexdigest()


def _duplicate_safe_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("E_JSON_INVALID")
        result[key] = value
    return result


def _reject_non_integer_number(_value: str) -> NoReturn:
    _fail("E_JSON_INVALID")


def _count_json_shape(value: object, *, depth: int = 1) -> int:
    if depth > MAX_JSON_DEPTH:
        _fail("E_LIMIT")
    if value is None:
        _fail("E_JSON_INVALID")
    if isinstance(value, str):
        try:
            encoded = value.encode("ascii")
        except UnicodeEncodeError:
            _fail("E_SCHEMA")
        if len(encoded) > MAX_SCALAR_ASCII_BYTES or any(
            ord(character) < 0x20 or ord(character) == 0x7F for character in value
        ):
            _fail("E_LIMIT")
        return 1
    if type(value) is bool or type(value) is int:
        return 1
    if isinstance(value, list):
        total = 1
        for item in value:
            total += _count_json_shape(item, depth=depth + 1)
            if total > MAX_JSON_NODES:
                _fail("E_LIMIT")
        return total
    if isinstance(value, dict):
        total = 1
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("E_JSON_INVALID")
            try:
                encoded_key = key.encode("ascii")
            except UnicodeEncodeError:
                _fail("E_SCHEMA")
            if len(encoded_key) > MAX_SCALAR_ASCII_BYTES or any(
                ord(character) < 0x20 or ord(character) == 0x7F for character in key
            ):
                _fail("E_LIMIT")
            total += _count_json_shape(item, depth=depth + 1)
            if total > MAX_JSON_NODES:
                _fail("E_LIMIT")
        return total
    _fail("E_JSON_INVALID")


def _strict_json_document(raw: bytes) -> object:
    if not raw or raw.startswith(b"\xef\xbb\xbf"):
        _fail("E_JSON_INVALID")
    if len(raw) > MAX_STDIN_BYTES:
        _fail("E_INPUT_TOO_LARGE")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail("E_JSON_INVALID")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_safe_object,
            parse_int=int,
            parse_float=_reject_non_integer_number,
            parse_constant=_reject_non_integer_number,
        )
    except EpisodeError:
        raise
    except RecursionError:
        _fail("E_LIMIT")
    except (json.JSONDecodeError, UnicodeError, ValueError, OverflowError):
        _fail("E_JSON_INVALID")
    if _count_json_shape(value) > MAX_JSON_NODES:
        _fail("E_LIMIT")
    return value


def _require_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail("E_SCHEMA")
    return cast(dict[str, object], value)


def _require_list(value: object) -> list[object]:
    if not isinstance(value, list):
        _fail("E_SCHEMA")
    return cast(list[object], value)


def _require_exact_keys(value: Mapping[str, object], fields: frozenset[str]) -> None:
    if frozenset(value) != fields:
        _fail("E_SCHEMA")


def _require_literal(value: object, expected: str) -> str:
    if value != expected or not isinstance(value, str):
        _fail("E_SCHEMA")
    return expected


def _require_enum(value: object, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in choices:
        _fail("E_SCHEMA")
    return value


def _require_id(value: object) -> str:
    if not isinstance(value, str):
        _fail("E_IDENTITY")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError:
        _fail("E_IDENTITY")
    if (
        not encoded
        or len(encoded) > MAX_ID_ASCII_BYTES
        or _ID_RE.fullmatch(value) is None
        or _FORBIDDEN_ID_RE.search(value) is not None
    ):
        _fail("E_IDENTITY")
    return value


def _require_digest(value: object) -> str:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _fail("E_IDENTITY")
    return value


def _require_commit(value: object) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        _fail("E_IDENTITY")
    return value


def _require_timestamp(value: object) -> str:
    if not isinstance(value, str) or _TIMESTAMP_RE.fullmatch(value) is None:
        _fail("E_ORDER")
    try:
        parsed = datetime_module.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        _fail("E_ORDER")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _fail("E_ORDER")
    return value


def _require_positive_pr(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 2_147_483_647:
        _fail("E_SCHEMA")
    return value


def _require_sorted_unique_ids(
    value: object, *, minimum: int = 0, maximum: int = MAX_SOURCE_FINDING_IDS
) -> list[str]:
    items = _require_list(value)
    if not minimum <= len(items) <= maximum:
        _fail("E_LIMIT")
    normalized = [_require_id(item) for item in items]
    if len(set(normalized)) != len(normalized):
        _fail("E_IDENTITY")
    return sorted(normalized)


def _require_sorted_digest_list(value: object) -> list[str]:
    items = _require_list(value)
    if not 1 <= len(items) <= MAX_TRIGGER_IDENTITIES:
        _fail("E_LIMIT")
    normalized = [_require_digest(item) for item in items]
    if normalized != sorted(set(normalized)):
        _fail("E_IDENTITY")
    return normalized


def _require_false_grants(value: object) -> dict[str, bool]:
    grants = _require_object(value)
    _require_exact_keys(grants, frozenset(AUTHORITY_FIELDS))
    if any(grants[field] is not False for field in AUTHORITY_FIELDS):
        _fail("E_SCHEMA")
    return dict(FALSE_GRANTS)


def _require_receipt_claims(value: object, *, report: bool = False) -> dict[str, object]:
    claims = _require_object(value)
    expected: dict[str, object] = dict(RECEIPT_CLAIMS)
    if report:
        expected["all_eligible_episodes_claim"] = False
    if frozenset(claims) != frozenset(expected) or any(
        type(claims[field]) is not type(expected_value) or claims[field] != expected_value
        for field, expected_value in expected.items()
    ):
        _fail("E_SCHEMA")
    return expected


def _episode_digest(pull_request_number: int) -> str:
    return _domain_digest(
        EPISODE_DOMAIN,
        {
            "repository_slug": REPOSITORY_SLUG,
            "pull_request_number": pull_request_number,
        },
    )


def _normalize_source(value: object) -> dict[str, object]:
    source = _require_object(value)
    _require_exact_keys(source, _SOURCE_FIELDS)
    packet_id = source["l2_task_packet_id"]
    if not isinstance(packet_id, str) or _TASK_PACKET_ID_RE.fullmatch(packet_id) is None:
        _fail("E_IDENTITY")
    packet_digest = _require_digest(source["l2_task_packet_digest"])
    if packet_id != packet_digest[:12]:
        _fail("E_IDENTITY")
    fingerprint = source["l1_artifact_fingerprint"]
    idempotency = source["l1_idempotency_key"]
    if not isinstance(fingerprint, str) or not isinstance(idempotency, str):
        _fail("E_IDENTITY")
    fingerprint_match = _L1_FINGERPRINT_RE.fullmatch(fingerprint)
    idempotency_match = _L1_IDEMPOTENCY_RE.fullmatch(idempotency)
    if (
        fingerprint_match is None
        or idempotency_match is None
        or fingerprint_match.group(1) != idempotency_match.group(1)
    ):
        _fail("E_IDENTITY")
    return {
        "l2_task_packet_id": packet_id,
        "l2_task_packet_digest": packet_digest,
        "l1_artifact_fingerprint": fingerprint,
        "l1_idempotency_key": idempotency,
        "trigger_rule": _require_literal(
            source["trigger_rule"], "explicit_family_cardinality_gte_2"
        ),
        "membership_source": _require_literal(source["membership_source"], "explicit_input_only"),
    }


def _normalize_enrollment_input(value: object) -> dict[str, object]:
    document = _require_object(value)
    _require_exact_keys(document, _ENROLLMENT_INPUT_FIELDS)
    _require_literal(document["schema_version"], ENROLLMENT_INPUT_SCHEMA)
    episode_class = _require_enum(document["episode_class"], EPISODE_CLASSES)
    pull_request_number = _require_positive_pr(document["pull_request_number"])
    trigger_observed_at = _require_timestamp(document["trigger_observed_at"])
    enrollment_recorded_at = _require_timestamp(document["enrollment_recorded_at"])
    if trigger_observed_at > enrollment_recorded_at:
        _fail("E_ORDER")
    source = _normalize_source(document["source"])

    raw_identities = _require_list(document["identity_classes"])
    if not 2 <= len(raw_identities) <= MAX_IDENTITY_ROWS:
        _fail("E_LIMIT")
    identities: list[dict[str, object]] = []
    seen_classes: set[str] = set()
    seen_findings: set[str] = set()
    for raw_identity in raw_identities:
        identity = _require_object(raw_identity)
        _require_exact_keys(identity, _ENROLLMENT_IDENTITY_FIELDS)
        class_id = _require_id(identity["identity_class_id"])
        finding_id = _require_id(identity["trigger_finding_id"])
        if class_id in seen_classes or finding_id in seen_findings:
            _fail("E_IDENTITY")
        seen_classes.add(class_id)
        seen_findings.add(finding_id)
        identities.append({"identity_class_id": class_id, "trigger_finding_id": finding_id})
    identities.sort(key=lambda row: cast(str, row["identity_class_id"]))

    raw_families = _require_list(document["families"])
    if not 1 <= len(raw_families) <= MAX_FAMILIES:
        _fail("E_LIMIT")
    families: list[dict[str, object]] = []
    seen_keys: set[str] = set()
    seen_family_ids: set[str] = set()
    used_classes: set[str] = set()
    membership_count = 0
    for raw_family in raw_families:
        family = _require_object(raw_family)
        _require_exact_keys(family, _ENROLLMENT_FAMILY_FIELDS)
        family_key = _require_id(family["family_key"])
        family_id = _require_id(family["trigger_family_id"])
        if family_key in seen_keys or family_id in seen_family_ids:
            _fail("E_IDENTITY")
        seen_keys.add(family_key)
        seen_family_ids.add(family_id)
        members = _require_sorted_unique_ids(family["trigger_identity_class_ids"], minimum=2)
        if not set(members).issubset(seen_classes):
            _fail("E_IDENTITY")
        membership_count += len(members)
        used_classes.update(members)
        families.append(
            {
                "family_key": family_key,
                "trigger_family_id": family_id,
                "trigger_identity_class_ids": members,
            }
        )
    if membership_count > MAX_FAMILY_MEMBERSHIP_REFS:
        _fail("E_LIMIT")
    if used_classes != seen_classes:
        _fail("E_IDENTITY")
    families.sort(key=lambda row: cast(str, row["family_key"]))
    return {
        "schema_version": ENROLLMENT_INPUT_SCHEMA,
        "episode_class": episode_class,
        "pull_request_number": pull_request_number,
        "trigger_observed_at": trigger_observed_at,
        "enrollment_recorded_at": enrollment_recorded_at,
        "material_head_sha": _require_commit(document["material_head_sha"]),
        "source": source,
        "identity_classes": identities,
        "families": families,
    }


def _build_enrollment_receipt(value: object) -> dict[str, object]:
    normalized = _normalize_enrollment_input(value)
    episode_digest = _episode_digest(cast(int, normalized["pull_request_number"]))
    receipt: dict[str, object] = {
        "schema_version": ENROLLMENT_RECEIPT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository_slug": REPOSITORY_SLUG,
        "pull_request_number": normalized["pull_request_number"],
        "episode_digest": episode_digest,
        "episode_class": normalized["episode_class"],
        "trigger_observed_at": normalized["trigger_observed_at"],
        "enrollment_recorded_at": normalized["enrollment_recorded_at"],
        "material_head_sha": normalized["material_head_sha"],
        "source": normalized["source"],
        "identity_classes": normalized["identity_classes"],
        "families": normalized["families"],
        "claims": dict(RECEIPT_CLAIMS),
        "downstream_grants": dict(FALSE_GRANTS),
        "transport_capability": TRANSPORT_CAPABILITY,
    }
    digest = _domain_digest(ENROLLMENT_RECEIPT_DOMAIN, receipt)
    receipt["enrollment_receipt_digest"] = digest
    return receipt


def _enrollment_input_from_receipt(receipt: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": ENROLLMENT_INPUT_SCHEMA,
        "episode_class": receipt["episode_class"],
        "pull_request_number": receipt["pull_request_number"],
        "trigger_observed_at": receipt["trigger_observed_at"],
        "enrollment_recorded_at": receipt["enrollment_recorded_at"],
        "material_head_sha": receipt["material_head_sha"],
        "source": receipt["source"],
        "identity_classes": receipt["identity_classes"],
        "families": receipt["families"],
    }


def _validate_enrollment_receipt(value: object) -> dict[str, object]:
    receipt = _require_object(value)
    schema_projection = cast(Mapping[str, object], POLICY_PROJECTION["schemas"])
    enrollment_projection = cast(Mapping[str, object], schema_projection["enrollment_receipt"])
    expected_fields = frozenset(cast(tuple[str, ...], enrollment_projection["fields"]))
    _require_exact_keys(receipt, expected_fields)
    _require_literal(receipt["schema_version"], ENROLLMENT_RECEIPT_SCHEMA)
    _require_literal(receipt["policy_version"], POLICY_VERSION)
    _require_literal(receipt["repository_slug"], REPOSITORY_SLUG)
    _require_receipt_claims(receipt["claims"])
    _require_false_grants(receipt["downstream_grants"])
    _require_literal(receipt["transport_capability"], TRANSPORT_CAPABILITY)
    supplied_digest = _require_digest(receipt["enrollment_receipt_digest"])
    rebuilt = _build_enrollment_receipt(_enrollment_input_from_receipt(receipt))
    if (
        _canonical_json_bytes(rebuilt) != _canonical_json_bytes(receipt)
        or rebuilt["enrollment_receipt_digest"] != supplied_digest
    ):
        _fail("E_STORE_UNSAFE")
    return rebuilt


def _normalize_identity_table(
    value: object, *, allowed_phases: tuple[str, ...]
) -> tuple[list[dict[str, object]], int]:
    raw_rows = _require_list(value)
    if not 1 <= len(raw_rows) <= MAX_IDENTITY_ROWS:
        _fail("E_LIMIT")
    rows: list[dict[str, object]] = []
    seen_classes: set[str] = set()
    seen_phase_findings: dict[str, set[str]] = {phase: set() for phase in allowed_phases}
    source_refs = 0
    phase_order = {phase: index for index, phase in enumerate(PHASES)}
    for raw_row in raw_rows:
        row = _require_object(raw_row)
        _require_exact_keys(row, _IDENTITY_CLASS_FIELDS)
        class_id = _require_id(row["identity_class_id"])
        if class_id in seen_classes:
            _fail("E_IDENTITY")
        seen_classes.add(class_id)
        raw_bindings = _require_list(row["phase_bindings"])
        if not 1 <= len(raw_bindings) <= len(allowed_phases):
            _fail("E_IDENTITY")
        bindings: list[dict[str, object]] = []
        seen_phases: set[str] = set()
        for raw_binding in raw_bindings:
            binding = _require_object(raw_binding)
            _require_exact_keys(binding, _PHASE_BINDING_FIELDS)
            phase = _require_enum(binding["phase"], allowed_phases)
            finding_id = _require_id(binding["finding_id"])
            if phase in seen_phases or finding_id in seen_phase_findings[phase]:
                _fail("E_IDENTITY")
            seen_phases.add(phase)
            seen_phase_findings[phase].add(finding_id)
            bindings.append({"phase": phase, "finding_id": finding_id})
            source_refs += 1
        bindings.sort(key=lambda item: phase_order[cast(str, item["phase"])])
        rows.append({"identity_class_id": class_id, "phase_bindings": bindings})
    rows.sort(key=lambda item: cast(str, item["identity_class_id"]))
    return rows, source_refs


def _binding_map(rows: list[dict[str, object]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        class_id = cast(str, row["identity_class_id"])
        result[class_id] = {
            cast(str, binding["phase"]): cast(str, binding["finding_id"])
            for binding in cast(list[dict[str, object]], row["phase_bindings"])
        }
    return result


def _enrollment_maps(
    enrollment: Mapping[str, object],
) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    trigger_findings = {
        cast(str, row["identity_class_id"]): cast(str, row["trigger_finding_id"])
        for row in cast(list[dict[str, object]], enrollment["identity_classes"])
    }
    families = {
        cast(str, row["family_key"]): row
        for row in cast(list[dict[str, object]], enrollment["families"])
    }
    return trigger_findings, families


def _normalize_joint_pass_baseline(
    value: object, enrollment: Mapping[str, object]
) -> dict[str, object]:
    document = _require_object(value)
    _require_exact_keys(document, _BASELINE_FIELDS)
    _require_literal(document["schema_version"], BASELINE_INPUT_SCHEMA)
    if _require_digest(document["episode_digest"]) != enrollment["episode_digest"]:
        _fail("E_DEPENDENCY")
    if (
        _require_digest(document["enrollment_receipt_digest"])
        != enrollment["enrollment_receipt_digest"]
    ):
        _fail("E_DEPENDENCY")
    joint_time = _require_timestamp(document["joint_pass_completed_at"])
    if cast(str, enrollment["enrollment_recorded_at"]) > joint_time:
        _fail("E_ORDER")

    identities, source_refs = _normalize_identity_table(
        document["identity_classes"], allowed_phases=("trigger", "joint_pass")
    )
    if source_refs > MAX_SOURCE_FINDING_IDS:
        _fail("E_LIMIT")
    bindings = _binding_map(identities)
    trigger_findings, enrollment_families = _enrollment_maps(enrollment)
    if set(trigger_findings) - set(bindings):
        _fail("E_IDENTITY")
    for class_id, phase_bindings in bindings.items():
        trigger_binding = phase_bindings.get("trigger")
        expected_trigger = trigger_findings.get(class_id)
        if (trigger_binding is None) != (expected_trigger is None):
            _fail("E_IDENTITY")
        if trigger_binding is not None and trigger_binding != expected_trigger:
            _fail("E_IDENTITY")

    raw_families = _require_list(document["families"])
    if len(raw_families) != len(enrollment_families) or len(raw_families) > MAX_FAMILIES:
        _fail("E_IDENTITY")
    families: list[dict[str, object]] = []
    seen_keys: set[str] = set()
    seen_joint_ids: set[str] = set()
    used_classes: set[str] = set()
    membership_refs = 0
    for raw_family in raw_families:
        family = _require_object(raw_family)
        _require_exact_keys(family, _BASELINE_FAMILY_FIELDS)
        family_key = _require_id(family["family_key"])
        if family_key in seen_keys or family_key not in enrollment_families:
            _fail("E_IDENTITY")
        seen_keys.add(family_key)
        joint_family_id = _require_id(family["joint_pass_family_id"])
        if joint_family_id in seen_joint_ids:
            _fail("E_IDENTITY")
        seen_joint_ids.add(joint_family_id)
        members = _require_sorted_unique_ids(
            family["joint_pass_cumulative_identity_class_ids"], minimum=2
        )
        trigger_members = set(
            cast(
                list[str],
                enrollment_families[family_key]["trigger_identity_class_ids"],
            )
        )
        if not trigger_members.issubset(members) or not set(members).issubset(bindings):
            _fail("E_IDENTITY")
        if any("joint_pass" not in bindings[class_id] for class_id in members):
            _fail("E_IDENTITY")
        membership_refs += len(members)
        used_classes.update(members)
        families.append(
            {
                "family_key": family_key,
                "joint_pass_family_id": joint_family_id,
                "joint_pass_cumulative_identity_class_ids": members,
                "recommended_resolution": _require_enum(
                    family["recommended_resolution"], RECOMMENDED_RESOLUTIONS
                ),
            }
        )
    if set(enrollment_families) != seen_keys or used_classes != set(bindings):
        _fail("E_IDENTITY")
    if membership_refs > MAX_FAMILY_MEMBERSHIP_REFS:
        _fail("E_LIMIT")
    families.sort(key=lambda item: cast(str, item["family_key"]))
    return {
        "schema_version": BASELINE_INPUT_SCHEMA,
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
        "joint_pass_completed_at": joint_time,
        "identity_classes": identities,
        "families": families,
    }


def _joint_pass_baseline_digest(baseline: Mapping[str, object]) -> str:
    return _domain_digest(BASELINE_DOMAIN, baseline)


def _baseline_ack(baseline: Mapping[str, object]) -> dict[str, object]:
    return _ack(
        "validate",
        episode_digest=baseline["episode_digest"],
        joint_pass_baseline_digest=_joint_pass_baseline_digest(baseline),
    )


def _build_checkpoint_receipt(value: object, enrollment: Mapping[str, object]) -> dict[str, object]:
    baseline = _normalize_joint_pass_baseline(value, enrollment)
    receipt: dict[str, object] = {
        "schema_version": CHECKPOINT_RECEIPT_SCHEMA,
        "policy_version": SUPERVISION_POLICY_VERSION,
        "repository_slug": REPOSITORY_SLUG,
        "pull_request_number": enrollment["pull_request_number"],
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
        "baseline": baseline,
        "joint_pass_baseline_digest": _joint_pass_baseline_digest(baseline),
        "validate_acknowledgement": _baseline_ack(baseline),
        "claims": dict(RECEIPT_CLAIMS),
        "downstream_grants": dict(FALSE_GRANTS),
        "transport_capability": TRANSPORT_CAPABILITY,
    }
    receipt["checkpoint_receipt_digest"] = _domain_digest(CHECKPOINT_RECEIPT_DOMAIN, receipt)
    return receipt


def _require_checkpoint_agreement(
    joint_pass: object,
    checkpoint: Mapping[str, object] | None,
    enrollment: Mapping[str, object],
    *,
    available_requires_checkpoint: bool = False,
) -> None:
    joint = _require_object(joint_pass)
    status = _require_enum(joint.get("status"), JOINT_PASS_STATUSES)
    if checkpoint is None:
        if available_requires_checkpoint and status == "completed_baseline_available":
            _fail("E_DEPENDENCY")
        return
    if status != "completed_baseline_available":
        _fail("E_DEPENDENCY")
    baseline = _normalize_joint_pass_baseline(joint.get("baseline"), enrollment)
    if (
        baseline != checkpoint["baseline"]
        or _require_digest(joint.get("joint_pass_baseline_digest"))
        != checkpoint["joint_pass_baseline_digest"]
    ):
        _fail("E_DEPENDENCY")


def _minimum_terminal_receipt_bytes(
    checkpoint: Mapping[str, object], enrollment: Mapping[str, object]
) -> int:
    """Size only the mandatory v1 representation, never a proposed observation.

    Empty unknown scalars make this projection intentionally invalid. It is
    neither normalized, hashed, returned nor persisted as terminal evidence.
    Replacing its placeholders with the closed minimum widths preserves JSON
    nodes/depth. Future C growth and aggregate capacity are not reserved.
    """
    baseline = cast(Mapping[str, object], checkpoint["baseline"])
    families = cast(list[dict[str, object]], baseline["families"])
    projection: dict[str, object] = {
        "schema_version": TERMINAL_RECEIPT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository_slug": REPOSITORY_SLUG,
        "pull_request_number": enrollment["pull_request_number"],
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
        "episode_class": enrollment["episode_class"],
        "terminal_state": "",
        "terminal_event_at": "",
        "terminal_recorded_at": "",
        "terminal_material_head_sha": "",
        "observed_l2_identity_digests": [""],
        "joint_pass": {
            "status": "completed_baseline_available",
            "baseline": baseline,
            "joint_pass_baseline_digest": checkpoint["joint_pass_baseline_digest"],
            "identity_classes": baseline["identity_classes"],
            "family_observations": [
                {"status": "", "reason": "", "family_key": family["family_key"]}
                for family in families
            ],
        },
        "recurrence": {"status": "", "reason": ""},
        "claims": dict(RECEIPT_CLAIMS),
        "downstream_grants": dict(FALSE_GRANTS),
        "transport_capability": TRANSPORT_CAPABILITY,
        "terminal_receipt_digest": "",
    }
    _count_json_shape(projection)
    non_comparable_width = len(FAMILY_STATUS_NON_COMPARABLE) + min(
        map(len, FAMILY_NON_COMPARABLE_REASONS)
    )
    unknown_width = len(FAMILY_STATUS_UNKNOWN) + min(map(len, FAMILY_UNKNOWN_REASONS))
    # Closed alternatives: all non-comparable families, or one unknown and the
    # remaining non-comparable. More unknowns or confirmed fields only add bytes.
    family_scalar_width = min(
        len(families) * non_comparable_width
        + len(EPISODE_STATUS_NON_COMPARABLE)
        + len("family_observation_non_comparable"),
        (len(families) - 1) * non_comparable_width
        + unknown_width
        + len(EPISODE_STATUS_UNKNOWN)
        + len("family_observation_unknown"),
    )
    # Validated enrollment scalars already have the frozen timestamp/SHA widths.
    fixed_scalar_width = (
        min(map(len, TERMINAL_STATES))
        + 2 * len(cast(str, enrollment["enrollment_recorded_at"]))
        + len(cast(str, enrollment["material_head_sha"]))
        + 2 * len(cast(str, checkpoint["joint_pass_baseline_digest"]))
    )
    return (
        len(_canonical_json_bytes(projection, trailing_lf=True))
        + fixed_scalar_width
        + family_scalar_width
    )


def _normalize_terminal_input(value: object, enrollment: Mapping[str, object]) -> dict[str, object]:
    document = _require_object(value)
    _require_exact_keys(document, _TERMINAL_INPUT_FIELDS)
    _require_literal(document["schema_version"], TERMINAL_INPUT_SCHEMA)
    if _require_digest(document["episode_digest"]) != enrollment["episode_digest"]:
        _fail("E_DEPENDENCY")
    if (
        _require_digest(document["enrollment_receipt_digest"])
        != enrollment["enrollment_receipt_digest"]
    ):
        _fail("E_DEPENDENCY")
    terminal_event_at = _require_timestamp(document["terminal_event_at"])
    terminal_recorded_at = _require_timestamp(document["terminal_recorded_at"])
    if not (
        cast(str, enrollment["enrollment_recorded_at"]) <= terminal_event_at <= terminal_recorded_at
    ):
        _fail("E_ORDER")
    observed_digests = _require_sorted_digest_list(document["observed_l2_identity_digests"])
    trigger_digest = cast(Mapping[str, object], enrollment["source"])["l2_task_packet_digest"]
    if trigger_digest not in observed_digests:
        _fail("E_IDENTITY")

    raw_joint_pass = _require_object(document["joint_pass"])
    status_value = raw_joint_pass.get("status")
    status = _require_enum(status_value, JOINT_PASS_STATUSES)
    normalized_joint: dict[str, object]
    recurrence: dict[str, object]

    if status == "not_completed":
        _require_exact_keys(raw_joint_pass, frozenset({"status", "reason"}))
        normalized_joint = {
            "status": status,
            "reason": _require_literal(raw_joint_pass["reason"], "not_completed_before_terminal"),
        }
        recurrence = {
            "status": EPISODE_STATUS_NOT_APPLICABLE,
            "reason": "not_completed_before_terminal",
        }
    elif status == "completed_baseline_unavailable":
        _require_exact_keys(
            raw_joint_pass,
            frozenset({"status", "reason", "joint_pass_completed_at"}),
        )
        joint_time = _require_timestamp(raw_joint_pass["joint_pass_completed_at"])
        if not (cast(str, enrollment["enrollment_recorded_at"]) <= joint_time <= terminal_event_at):
            _fail("E_ORDER")
        normalized_joint = {
            "status": status,
            "reason": _require_literal(raw_joint_pass["reason"], "joint_pass_baseline_unavailable"),
            "joint_pass_completed_at": joint_time,
        }
        recurrence = {
            "status": EPISODE_STATUS_UNKNOWN,
            "reason": "joint_pass_baseline_unavailable",
        }
    else:
        _require_exact_keys(
            raw_joint_pass,
            frozenset(
                {
                    "status",
                    "baseline",
                    "joint_pass_baseline_digest",
                    "identity_classes",
                    "family_observations",
                }
            ),
        )
        baseline = _normalize_joint_pass_baseline(raw_joint_pass["baseline"], enrollment)
        baseline_digest = _joint_pass_baseline_digest(baseline)
        if _require_digest(raw_joint_pass["joint_pass_baseline_digest"]) != baseline_digest:
            _fail("E_DEPENDENCY")
        joint_time = cast(str, baseline["joint_pass_completed_at"])
        if joint_time > terminal_event_at:
            _fail("E_ORDER")

        terminal_identities, terminal_source_refs = _normalize_identity_table(
            raw_joint_pass["identity_classes"], allowed_phases=PHASES
        )
        baseline_identities = cast(list[dict[str, object]], baseline["identity_classes"])
        baseline_source_refs = sum(
            len(cast(list[object], row["phase_bindings"])) for row in baseline_identities
        )
        if baseline_source_refs + terminal_source_refs > MAX_SOURCE_FINDING_IDS:
            _fail("E_LIMIT")
        baseline_bindings = _binding_map(baseline_identities)
        terminal_bindings = _binding_map(terminal_identities)
        if not set(baseline_bindings).issubset(terminal_bindings):
            _fail("E_IDENTITY")
        for class_id, expected in baseline_bindings.items():
            actual = terminal_bindings[class_id]
            if {
                phase: finding
                for phase, finding in actual.items()
                if phase in ("trigger", "joint_pass")
            } != expected:
                _fail("E_IDENTITY")
        for class_id, actual in terminal_bindings.items():
            if class_id not in baseline_bindings and any(
                phase in actual for phase in ("trigger", "joint_pass")
            ):
                _fail("E_IDENTITY")

        baseline_families = {
            cast(str, row["family_key"]): row
            for row in cast(list[dict[str, object]], baseline["families"])
        }
        raw_observations = _require_list(raw_joint_pass["family_observations"])
        if len(raw_observations) != len(baseline_families):
            _fail("E_IDENTITY")
        observations: list[dict[str, object]] = []
        seen_keys: set[str] = set()
        seen_terminal_family_ids: set[str] = set()
        used_terminal_classes: set[str] = set()
        combined_membership_refs = sum(
            len(cast(list[object], family["joint_pass_cumulative_identity_class_ids"]))
            for family in baseline_families.values()
        )
        for raw_observation in raw_observations:
            observation = _require_object(raw_observation)
            observation_status = _require_enum(
                observation.get("status"), FAMILY_OBSERVATION_STATUSES
            )
            family_key = _require_id(observation.get("family_key"))
            if family_key in seen_keys or family_key not in baseline_families:
                _fail("E_IDENTITY")
            seen_keys.add(family_key)
            baseline_family = baseline_families[family_key]
            if observation_status == FAMILY_STATUS_CONFIRMED:
                _require_exact_keys(
                    observation,
                    frozenset(
                        {
                            "status",
                            "reason",
                            "family_key",
                            "terminal_family_id",
                            "terminal_cumulative_identity_class_ids",
                        }
                    ),
                )
                reason = _require_enum(observation["reason"], FAMILY_CONFIRMED_REASONS)
                terminal_members = _require_sorted_unique_ids(
                    observation["terminal_cumulative_identity_class_ids"],
                    minimum=2,
                )
                joint_members = cast(
                    list[str],
                    baseline_family["joint_pass_cumulative_identity_class_ids"],
                )
                if not set(joint_members).issubset(terminal_members):
                    _fail("E_IDENTITY")
                if not set(terminal_members).issubset(terminal_bindings):
                    _fail("E_IDENTITY")
                if any(
                    "terminal" not in terminal_bindings[class_id] for class_id in terminal_members
                ):
                    _fail("E_IDENTITY")
                difference = sorted(set(terminal_members) - set(joint_members))
                terminal_family_id = _require_id(observation["terminal_family_id"])
                if terminal_family_id in seen_terminal_family_ids:
                    _fail("E_IDENTITY")
                seen_terminal_family_ids.add(terminal_family_id)
                used_terminal_classes.update(terminal_members)
                combined_membership_refs += len(terminal_members)
                observations.append(
                    {
                        "status": observation_status,
                        "reason": reason,
                        "family_key": family_key,
                        "joint_pass_family_id": baseline_family["joint_pass_family_id"],
                        "terminal_family_id": terminal_family_id,
                        "joint_pass_cumulative_identity_class_ids": joint_members,
                        "terminal_cumulative_identity_class_ids": terminal_members,
                        "recommended_resolution": baseline_family["recommended_resolution"],
                        "post_joint_same_family_first_observed_identity_class_ids": difference,
                        "post_joint_same_family_first_observed_count": len(difference),
                    }
                )
            elif observation_status == FAMILY_STATUS_UNKNOWN:
                _require_exact_keys(observation, frozenset({"status", "reason", "family_key"}))
                observations.append(
                    {
                        "status": observation_status,
                        "reason": _require_enum(observation["reason"], FAMILY_UNKNOWN_REASONS),
                        "family_key": family_key,
                    }
                )
            elif observation_status == FAMILY_STATUS_NON_COMPARABLE:
                _require_exact_keys(observation, frozenset({"status", "reason", "family_key"}))
                observations.append(
                    {
                        "status": observation_status,
                        "reason": _require_enum(
                            observation["reason"], FAMILY_NON_COMPARABLE_REASONS
                        ),
                        "family_key": family_key,
                    }
                )
        if seen_keys != set(baseline_families):
            _fail("E_IDENTITY")
        if combined_membership_refs > MAX_FAMILY_MEMBERSHIP_REFS:
            _fail("E_LIMIT")
        baseline_classes = set(baseline_bindings)
        if set(terminal_bindings) != baseline_classes | used_terminal_classes:
            _fail("E_IDENTITY")
        observations.sort(key=lambda item: cast(str, item["family_key"]))
        if joint_time == terminal_event_at and any(
            observation["status"] == FAMILY_STATUS_CONFIRMED
            and cast(
                int,
                observation["post_joint_same_family_first_observed_count"],
            )
            > 0
            for observation in observations
        ):
            _fail("E_ORDER")
        normalized_joint = {
            "status": status,
            "baseline": baseline,
            "joint_pass_baseline_digest": baseline_digest,
            "identity_classes": terminal_identities,
            "family_observations": observations,
        }
        if any(
            observation["status"] == FAMILY_STATUS_CONFIRMED
            and cast(
                int,
                observation["post_joint_same_family_first_observed_count"],
            )
            > 0
            for observation in observations
        ):
            recurrence = {
                "status": EPISODE_STATUS_OBSERVED,
                "reason": "positive",
                "value": True,
            }
        elif any(observation["status"] == FAMILY_STATUS_UNKNOWN for observation in observations):
            recurrence = {
                "status": EPISODE_STATUS_UNKNOWN,
                "reason": "family_observation_unknown",
            }
        elif any(
            observation["status"] == FAMILY_STATUS_NON_COMPARABLE for observation in observations
        ):
            recurrence = {
                "status": EPISODE_STATUS_NON_COMPARABLE,
                "reason": "family_observation_non_comparable",
            }
        else:
            recurrence = {
                "status": EPISODE_STATUS_OBSERVED,
                "reason": "zero",
                "value": False,
            }

    if len(observed_digests) > 1:
        recurrence = {
            "status": EPISODE_STATUS_NON_COMPARABLE,
            "reason": "multi_trigger",
        }
    return {
        "schema_version": TERMINAL_INPUT_SCHEMA,
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
        "terminal_state": _require_enum(document["terminal_state"], TERMINAL_STATES),
        "terminal_event_at": terminal_event_at,
        "terminal_recorded_at": terminal_recorded_at,
        "terminal_material_head_sha": _require_commit(document["terminal_material_head_sha"]),
        "observed_l2_identity_digests": observed_digests,
        "joint_pass": normalized_joint,
        "recurrence": recurrence,
    }


def _build_terminal_receipt(value: object, enrollment: Mapping[str, object]) -> dict[str, object]:
    normalized = _normalize_terminal_input(value, enrollment)
    receipt: dict[str, object] = {
        "schema_version": TERMINAL_RECEIPT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository_slug": REPOSITORY_SLUG,
        "pull_request_number": enrollment["pull_request_number"],
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
        "episode_class": enrollment["episode_class"],
        "terminal_state": normalized["terminal_state"],
        "terminal_event_at": normalized["terminal_event_at"],
        "terminal_recorded_at": normalized["terminal_recorded_at"],
        "terminal_material_head_sha": normalized["terminal_material_head_sha"],
        "observed_l2_identity_digests": normalized["observed_l2_identity_digests"],
        "joint_pass": normalized["joint_pass"],
        "recurrence": normalized["recurrence"],
        "claims": dict(RECEIPT_CLAIMS),
        "downstream_grants": dict(FALSE_GRANTS),
        "transport_capability": TRANSPORT_CAPABILITY,
    }
    receipt["terminal_receipt_digest"] = _domain_digest(TERMINAL_RECEIPT_DOMAIN, receipt)
    return receipt


def _terminal_input_from_receipt(receipt: Mapping[str, object]) -> dict[str, object]:
    joint = cast(Mapping[str, object], receipt["joint_pass"])
    status = cast(str, joint["status"])
    if status == "completed_baseline_available":
        input_observations: list[dict[str, object]] = []
        for raw_observation in cast(list[dict[str, object]], joint["family_observations"]):
            observation_status = cast(str, raw_observation["status"])
            if observation_status == FAMILY_STATUS_CONFIRMED:
                input_observations.append(
                    {
                        "status": FAMILY_STATUS_CONFIRMED,
                        "reason": raw_observation["reason"],
                        "family_key": raw_observation["family_key"],
                        "terminal_family_id": raw_observation["terminal_family_id"],
                        "terminal_cumulative_identity_class_ids": raw_observation[
                            "terminal_cumulative_identity_class_ids"
                        ],
                    }
                )
            else:
                input_observations.append(
                    {
                        "status": observation_status,
                        "reason": raw_observation["reason"],
                        "family_key": raw_observation["family_key"],
                    }
                )
        input_joint: dict[str, object] = {
            "status": status,
            "baseline": joint["baseline"],
            "joint_pass_baseline_digest": joint["joint_pass_baseline_digest"],
            "identity_classes": joint["identity_classes"],
            "family_observations": input_observations,
        }
    else:
        input_joint = dict(joint)
    return {
        "schema_version": TERMINAL_INPUT_SCHEMA,
        "episode_digest": receipt["episode_digest"],
        "enrollment_receipt_digest": receipt["enrollment_receipt_digest"],
        "terminal_state": receipt["terminal_state"],
        "terminal_event_at": receipt["terminal_event_at"],
        "terminal_recorded_at": receipt["terminal_recorded_at"],
        "terminal_material_head_sha": receipt["terminal_material_head_sha"],
        "observed_l2_identity_digests": receipt["observed_l2_identity_digests"],
        "joint_pass": input_joint,
    }


def _validate_terminal_receipt(
    value: object, enrollment: Mapping[str, object]
) -> dict[str, object]:
    receipt = _require_object(value)
    schema_projection = cast(Mapping[str, object], POLICY_PROJECTION["schemas"])
    terminal_projection = cast(Mapping[str, object], schema_projection["terminal_receipt"])
    expected_fields = frozenset(cast(tuple[str, ...], terminal_projection["fields"]))
    _require_exact_keys(receipt, expected_fields)
    _require_literal(receipt["schema_version"], TERMINAL_RECEIPT_SCHEMA)
    _require_literal(receipt["policy_version"], POLICY_VERSION)
    _require_literal(receipt["repository_slug"], REPOSITORY_SLUG)
    _require_receipt_claims(receipt["claims"])
    _require_false_grants(receipt["downstream_grants"])
    _require_literal(receipt["transport_capability"], TRANSPORT_CAPABILITY)
    supplied_digest = _require_digest(receipt["terminal_receipt_digest"])
    rebuilt = _build_terminal_receipt(_terminal_input_from_receipt(receipt), enrollment)
    if (
        _canonical_json_bytes(rebuilt) != _canonical_json_bytes(receipt)
        or rebuilt["terminal_receipt_digest"] != supplied_digest
    ):
        _fail("E_STORE_UNSAFE")
    return rebuilt


def _normalize_report_request(value: object) -> dict[str, object]:
    request = _require_object(value)
    _require_exact_keys(request, _REPORT_REQUEST_FIELDS)
    _require_literal(request["schema_version"], REPORT_REQUEST_SCHEMA)
    return {
        "schema_version": REPORT_REQUEST_SCHEMA,
        "cohort_as_of": _require_timestamp(request["cohort_as_of"]),
    }


def _ratio(numerator: int, denominator: int) -> dict[str, object]:
    if denominator == 0:
        return {"status": RATIO_STATUS_NOT_APPLICABLE, "reason": "zero_denominator"}
    return {
        "status": RATIO_STATUS_DEFINED,
        "numerator": numerator,
        "denominator": denominator,
    }


def _status_counts(rows: list[dict[str, object]], *, primary: bool) -> dict[str, object]:
    counts: dict[str, object] = {
        "enrollment_count": len(rows),
        "terminal_receipt_count": sum(
            row["terminal_receipt_digest"] != "missing_terminal" for row in rows
        ),
        "positive_count": sum(row["observation_reason"] == "positive" for row in rows),
        "zero_count": sum(row["observation_reason"] == "zero" for row in rows),
        "unknown_count": sum(row["observation_status"] == EPISODE_STATUS_UNKNOWN for row in rows),
        "non_comparable_count": sum(
            row["observation_status"] == EPISODE_STATUS_NON_COMPARABLE for row in rows
        ),
        "not_applicable_count": sum(
            row["observation_status"] == EPISODE_STATUS_NOT_APPLICABLE for row in rows
        ),
    }
    if not primary:
        return counts
    enrollment_count = cast(int, counts["enrollment_count"])
    not_applicable = cast(int, counts["not_applicable_count"])
    positive = cast(int, counts["positive_count"])
    zero = cast(int, counts["zero_count"])
    unknown = cast(int, counts["unknown_count"])
    non_comparable = cast(int, counts["non_comparable_count"])
    terminal_count = cast(int, counts["terminal_receipt_count"])
    denominator = enrollment_count - not_applicable
    identified = positive + zero
    counts.update(
        {
            "eligible_denominator_count": denominator,
            "identified_episode_count": identified,
            "recurrence_lower_bound_ratio": _ratio(positive, denominator),
            "recurrence_upper_bound_ratio": _ratio(
                positive + unknown + non_comparable, denominator
            ),
            "terminal_coverage_ratio": _ratio(terminal_count, enrollment_count),
            "identified_coverage_ratio": _ratio(identified, denominator),
            "accrual_band": (
                "collecting_lt_5"
                if identified < 5
                else "interim_5_to_9" if identified < 10 else "target_count_gte_10"
            ),
        }
    )
    return counts


def _render_markdown(semantic_core: Mapping[str, object]) -> bytes:
    primary = cast(Mapping[str, object], semantic_core["prospective_primary"])
    retrospective = cast(Mapping[str, object], semantic_core["retrospective_reference"])
    manifest = cast(list[dict[str, object]], semantic_core["manifest"])
    lines = [
        "# Euler L2-EVAL v1 cohort report",
        "",
        "Descriptive local observations only; no causal, safety, effectiveness, approval, L3, or merge conclusion.",
        "",
        f"- Cohort as asserted: `{semantic_core['cohort_as_of']}`",
        f"- Prospective enrollments: {primary['enrollment_count']}",
        f"- Prospective identified episodes: {primary['identified_episode_count']}",
        f"- Prospective unknown episodes: {primary['unknown_count']}",
        f"- Prospective non-comparable episodes: {primary['non_comparable_count']}",
        f"- Prospective not-applicable episodes: {primary['not_applicable_count']}",
        f"- Accrual band: `{primary['accrual_band']}`",
        f"- Retrospective references: {retrospective['enrollment_count']}",
        "",
        "## Manifest",
        "",
    ]
    if not manifest:
        lines.append("No locally enrolled episodes.")
    else:
        for row in manifest:
            lines.append(
                "- `{}' / `{}` / `{}`".format(
                    row["episode_digest"],
                    row["observation_status"],
                    row["observation_reason"],
                ).replace("'", "`")
            )
    return ("\n".join(lines) + "\n").encode("ascii")


def _required_open_flag(name: str) -> int:
    value = getattr(os, name, None)
    if type(value) is not int or value == 0:
        _fail("E_PUBLISH_UNSUPPORTED")
    return value


_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | _required_open_flag("O_DIRECTORY")
    | _required_open_flag("O_NOFOLLOW")
    | _required_open_flag("O_CLOEXEC")
)
_LEAF_READ_FLAGS = (
    os.O_RDONLY
    | _required_open_flag("O_NOFOLLOW")
    | _required_open_flag("O_NONBLOCK")
    | _required_open_flag("O_CLOEXEC")
)
_LEAF_CREATE_FLAGS = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_EXCL
    | _required_open_flag("O_NOFOLLOW")
    | _required_open_flag("O_NONBLOCK")
    | _required_open_flag("O_CLOEXEC")
)


def _stat_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _verify_directory_metadata(metadata: os.stat_result, *, exact_mode: bool) -> None:
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid():
        _fail("E_STORE_UNSAFE")
    mode = stat.S_IMODE(metadata.st_mode)
    if exact_mode:
        if mode != 0o700:
            _fail("E_STORE_UNSAFE")
    elif mode & 0o022:
        _fail("E_STORE_UNSAFE")


def _open_verified_directory(
    parent_fd: int,
    name: str,
    *,
    create: bool,
    exact_mode: bool,
) -> tuple[int, bool]:
    created = False
    try:
        directory_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
            created = True
        except FileExistsError:
            created = False
        except OSError:
            _fail("E_PUBLISH_FAILED")
        try:
            directory_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        except OSError:
            _fail("E_STORE_UNSAFE")
    except OSError:
        _fail("E_STORE_UNSAFE")
    try:
        if created:
            try:
                os.fchmod(directory_fd, 0o700)
            except OSError:
                _fail("E_PUBLISH_FAILED")
        metadata = os.fstat(directory_fd)
        _verify_directory_metadata(metadata, exact_mode=exact_mode)
        path_metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if _stat_signature(path_metadata) != _stat_signature(metadata):
            _fail("E_STORE_UNSAFE")
        os.set_inheritable(directory_fd, False)
        return directory_fd, created
    except Exception:
        os.close(directory_fd)
        raise


class _StoreSession:
    """One descriptor-relative locked view of the fixed local store."""

    def __init__(
        self,
        repository_anchor_fd: int,
        *,
        exclusive: bool,
        create: bool,
        allow_absent: bool = False,
    ) -> None:
        self._fds: list[int] = []
        self.root_fd = -1
        self.lane_fds: dict[str, int] = {}
        self.absent = False
        try:
            anchor_fd = os.dup(repository_anchor_fd)
            os.set_inheritable(anchor_fd, False)
            self._fds.append(anchor_fd)
            anchor_metadata = os.fstat(anchor_fd)
            _verify_directory_metadata(anchor_metadata, exact_mode=False)
            current_fd = anchor_fd
            for component in STORE_COMPONENTS[:-1]:
                try:
                    child_fd, _ = _open_verified_directory(
                        current_fd,
                        component,
                        create=create,
                        exact_mode=False,
                    )
                except FileNotFoundError:
                    if allow_absent and not create:
                        self.absent = True
                        return
                    _fail("E_DEPENDENCY")
                self._fds.append(child_fd)
                current_fd = child_fd
            lock_mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            try:
                fcntl.flock(current_fd, lock_mode | fcntl.LOCK_NB)
            except BlockingIOError:
                _fail("E_LOCK_BUSY")
            except OSError:
                _fail("E_STORE_UNSAFE")
            try:
                self.root_fd, root_created = _open_verified_directory(
                    current_fd,
                    STORE_COMPONENTS[-1],
                    create=create,
                    exact_mode=True,
                )
            except FileNotFoundError:
                if allow_absent and not create:
                    self.absent = True
                    return
                _fail("E_DEPENDENCY")
            self._fds.append(self.root_fd)
            try:
                fcntl.flock(self.root_fd, lock_mode | fcntl.LOCK_NB)
            except BlockingIOError:
                _fail("E_LOCK_BUSY")
            except OSError:
                _fail("E_STORE_UNSAFE")
            for lane_name in LANE_NAMES:
                try:
                    lane_fd, _ = _open_verified_directory(
                        self.root_fd,
                        lane_name,
                        create=create and root_created,
                        exact_mode=True,
                    )
                except FileNotFoundError:
                    _fail("E_STORE_UNSAFE")
                self._fds.append(lane_fd)
                self.lane_fds[lane_name] = lane_fd
            try:
                checkpoint_fd, _ = _open_verified_directory(
                    self.root_fd, "checkpoints", create=False, exact_mode=True
                )
            except FileNotFoundError:
                pass
            else:
                self._fds.append(checkpoint_fd)
                self.lane_fds["checkpoints"] = checkpoint_fd
            if root_created:
                try:
                    os.fsync(self.root_fd)
                except OSError:
                    _fail("E_PUBLISH_FAILED")
        except Exception:
            self.close()
            raise

    def create_checkpoint_lane(self) -> None:
        if "checkpoints" in self.lane_fds:
            return
        lane_fd, _ = _open_verified_directory(
            self.root_fd, "checkpoints", create=True, exact_mode=True
        )
        self._fds.append(lane_fd)
        self.lane_fds["checkpoints"] = lane_fd
        try:
            os.fsync(self.root_fd)
        except OSError:
            _fail("E_PUBLISH_FAILED")

    def close(self) -> None:
        while self._fds:
            descriptor = self._fds.pop()
            try:
                os.close(descriptor)
            except OSError:
                pass
        self.root_fd = -1
        self.lane_fds = {}

    def __enter__(self) -> _StoreSession:
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        self.close()


def _bounded_entries(
    directory_fd: int, maximum: int, *, overflow_code: str = "E_LIMIT"
) -> list[str]:
    entries: list[str] = []
    try:
        with os.scandir(directory_fd) as iterator:
            for entry in iterator:
                entries.append(entry.name)
                if len(entries) > maximum:
                    _fail(overflow_code)
    except EpisodeError:
        raise
    except OSError:
        _fail("E_STORE_UNSAFE")
    return sorted(entries)


def _read_stable_leaf(directory_fd: int, name: str, *, maximum_bytes: int) -> bytes:
    try:
        leaf_fd = os.open(name, _LEAF_READ_FLAGS, dir_fd=directory_fd)
    except OSError:
        _fail("E_STORE_UNSAFE")
    try:
        before = os.fstat(leaf_fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size > maximum_bytes
        ):
            _fail("E_STORE_UNSAFE")
        chunks: list[bytes] = []
        total = 0
        while True:
            try:
                chunk = os.read(leaf_fd, min(65_536, maximum_bytes + 1 - total))
            except BlockingIOError:
                _fail("E_STORE_UNSAFE")
            if not chunk:
                break
            total += len(chunk)
            if total > maximum_bytes:
                _fail("E_LIMIT")
            chunks.append(chunk)
        after = os.fstat(leaf_fd)
        path_metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if _stat_signature(before) != _stat_signature(after) or _stat_signature(
            after
        ) != _stat_signature(path_metadata):
            _fail("E_STORE_UNSAFE")
        return b"".join(chunks)
    except OSError:
        _fail("E_STORE_UNSAFE")
    finally:
        os.close(leaf_fd)


def _open_bundle_directory(lane_fd: int, digest: str) -> int | None:
    try:
        bundle_fd = os.open(digest, _DIRECTORY_FLAGS, dir_fd=lane_fd)
    except FileNotFoundError:
        return None
    except OSError:
        _fail("E_STORE_UNSAFE")
    try:
        metadata = os.fstat(bundle_fd)
        _verify_directory_metadata(metadata, exact_mode=True)
        path_metadata = os.stat(digest, dir_fd=lane_fd, follow_symlinks=False)
        if _stat_signature(metadata) != _stat_signature(path_metadata):
            _fail("E_STORE_UNSAFE")
        return bundle_fd
    except Exception:
        os.close(bundle_fd)
        raise


def _read_exact_bundle(
    lane_fd: int,
    digest: str,
    *,
    bundle_kind: str,
    maximum_file_bytes: Mapping[str, int],
) -> dict[str, bytes] | None:
    if _FULL_DIGEST_NAME_RE.fullmatch(digest) is None or bundle_kind not in BUNDLE_SHAPES:
        _fail("E_IDENTITY")
    bundle_fd = _open_bundle_directory(lane_fd, digest)
    if bundle_fd is None:
        return None
    try:
        expected_names = BUNDLE_SHAPES[bundle_kind]
        entries = _bounded_entries(
            bundle_fd,
            len(expected_names),
            overflow_code="E_STORE_UNSAFE",
        )
        if entries != sorted(expected_names):
            _fail("E_STORE_UNSAFE")
        result: dict[str, bytes] = {}
        total = 0
        for name in expected_names:
            data = _read_stable_leaf(bundle_fd, name, maximum_bytes=maximum_file_bytes[name])
            total += len(data)
            result[name] = data
        if bundle_kind == "report" and total > MAX_REPORT_BUNDLE_BYTES:
            _fail("E_LIMIT")
        return result
    finally:
        os.close(bundle_fd)


def _strict_stored_json(raw: bytes, *, maximum_bytes: int) -> object:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail("E_STORE_UNSAFE")
    if len(raw) > maximum_bytes:
        _fail("E_LIMIT")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        _fail("E_STORE_UNSAFE")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_safe_object,
            parse_int=int,
            parse_float=_reject_non_integer_number,
            parse_constant=_reject_non_integer_number,
        )
    except EpisodeError:
        _fail("E_STORE_UNSAFE")
    except RecursionError:
        _fail("E_STORE_UNSAFE")
    except (json.JSONDecodeError, ValueError, OverflowError):
        _fail("E_STORE_UNSAFE")
    try:
        if _count_json_shape(value) > MAX_JSON_NODES:
            _fail("E_STORE_UNSAFE")
        if _canonical_json_bytes(_require_object(value), trailing_lf=True) != raw:
            _fail("E_STORE_UNSAFE")
    except EpisodeError:
        _fail("E_STORE_UNSAFE")
    return value


def _validate_enrollment_bundle(files: Mapping[str, bytes]) -> dict[str, object]:
    value = _strict_stored_json(files["receipt.json"], maximum_bytes=MAX_ENROLLMENT_RECEIPT_BYTES)
    try:
        return _validate_enrollment_receipt(value)
    except EpisodeError:
        _fail("E_STORE_UNSAFE")


def _validate_terminal_bundle(
    files: Mapping[str, bytes], enrollment: Mapping[str, object]
) -> dict[str, object]:
    value = _strict_stored_json(files["receipt.json"], maximum_bytes=MAX_TERMINAL_RECEIPT_BYTES)
    try:
        return _validate_terminal_receipt(value, enrollment)
    except EpisodeError:
        _fail("E_STORE_UNSAFE")


def _validate_checkpoint_bundle(
    files: Mapping[str, bytes], enrollment: Mapping[str, object]
) -> dict[str, object]:
    value = _strict_stored_json(files["receipt.json"], maximum_bytes=MAX_CHECKPOINT_RECEIPT_BYTES)
    try:
        receipt = _require_object(value)
        _require_exact_keys(receipt, _CHECKPOINT_RECEIPT_FIELDS)
        _require_false_grants(receipt["downstream_grants"])
        rebuilt = _build_checkpoint_receipt(receipt["baseline"], enrollment)
        if _canonical_json_bytes(receipt) != _canonical_json_bytes(rebuilt):
            _fail("E_STORE_UNSAFE")
        return rebuilt
    except EpisodeError:
        _fail("E_STORE_UNSAFE")


def _checkpoint_files(session: _StoreSession, episode_digest: str) -> dict[str, bytes] | None:
    lane_fd = session.lane_fds.get("checkpoints")
    if lane_fd is None:
        return None
    return _read_exact_bundle(
        lane_fd,
        episode_digest,
        bundle_kind="receipt",
        maximum_file_bytes={"receipt.json": MAX_CHECKPOINT_RECEIPT_BYTES},
    )


def _load_checkpoint(
    session: _StoreSession, episode_digest: str, enrollment: Mapping[str, object]
) -> dict[str, object] | None:
    files = _checkpoint_files(session, episode_digest)
    if files is None:
        return None
    receipt = _validate_checkpoint_bundle(files, enrollment)
    if receipt["episode_digest"] != episode_digest:
        _fail("E_STORE_UNSAFE")
    return receipt


def _load_enrollment(
    session: _StoreSession, episode_digest: str, *, required: bool
) -> dict[str, object] | None:
    files = _read_exact_bundle(
        session.lane_fds["enrollments"],
        episode_digest,
        bundle_kind="receipt",
        maximum_file_bytes={"receipt.json": MAX_ENROLLMENT_RECEIPT_BYTES},
    )
    if files is None:
        if required:
            _fail("E_DEPENDENCY")
        return None
    receipt = _validate_enrollment_bundle(files)
    if receipt["episode_digest"] != episode_digest:
        _fail("E_STORE_UNSAFE")
    return receipt


def _load_terminal(
    session: _StoreSession,
    episode_digest: str,
    enrollment: Mapping[str, object],
) -> dict[str, object] | None:
    files = _read_exact_bundle(
        session.lane_fds["terminals"],
        episode_digest,
        bundle_kind="receipt",
        maximum_file_bytes={"receipt.json": MAX_TERMINAL_RECEIPT_BYTES},
    )
    if files is None:
        return None
    receipt = _validate_terminal_bundle(files, enrollment)
    if receipt["episode_digest"] != episode_digest:
        _fail("E_STORE_UNSAFE")
    _require_checkpoint_agreement(
        receipt["joint_pass"], _load_checkpoint(session, episode_digest, enrollment), enrollment
    )
    return receipt


def _scan_lane_names(lane_fd: int, maximum: int) -> list[str]:
    names = _bounded_entries(lane_fd, maximum)
    if any(_FULL_DIGEST_NAME_RE.fullmatch(name) is None for name in names):
        _fail("E_STORE_UNSAFE")
    return names


def _write_all(descriptor: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        try:
            written = os.write(descriptor, data[offset:])
        except OSError:
            _fail("E_PUBLISH_FAILED")
        if written <= 0:
            _fail("E_PUBLISH_FAILED")
        offset += written


def _cleanup_owned_stage(
    lane_fd: int,
    stage_name: str,
    stage_fd: int,
    stage_identity: tuple[int, int],
    created_files: Mapping[str, tuple[int, int]],
) -> None:
    try:
        current = os.fstat(stage_fd)
        path_metadata = os.stat(stage_name, dir_fd=lane_fd, follow_symlinks=False)
        if (
            (current.st_dev, current.st_ino) != stage_identity
            or (path_metadata.st_dev, path_metadata.st_ino) != stage_identity
            or not stat.S_ISDIR(current.st_mode)
        ):
            _fail("E_PUBLISH_FAILED")
        entries = _bounded_entries(
            stage_fd,
            len(created_files),
            overflow_code="E_PUBLISH_FAILED",
        )
        if entries != sorted(created_files):
            _fail("E_PUBLISH_FAILED")
        for name in sorted(created_files):
            metadata = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
            if (metadata.st_dev, metadata.st_ino) != created_files[name]:
                _fail("E_PUBLISH_FAILED")
            os.unlink(name, dir_fd=stage_fd)
        os.rmdir(stage_name, dir_fd=lane_fd)
        os.fsync(lane_fd)
    except EpisodeError:
        raise
    except OSError:
        _fail("E_PUBLISH_FAILED")


def _kernel_rename_noreplace(lane_fd: int, stage_name: str, final_name: str) -> None:
    if sys.platform == "darwin":
        symbol = "renameatx_np"
        flag = 0x00000004
    elif sys.platform.startswith("linux"):
        symbol = "renameat2"
        flag = 1
    else:
        _fail("E_PUBLISH_UNSUPPORTED")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        rename_noreplace = getattr(libc, symbol)
    except (AttributeError, OSError):
        _fail("E_PUBLISH_UNSUPPORTED")
    rename_noreplace.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename_noreplace.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = rename_noreplace(
        lane_fd,
        stage_name.encode("ascii"),
        lane_fd,
        final_name.encode("ascii"),
        flag,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    unsupported = {
        errno.ENOSYS,
        errno.EINVAL,
        getattr(errno, "ENOTSUP", errno.EINVAL),
        getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        errno.EXDEV,
    }
    if error_number in unsupported:
        _fail("E_PUBLISH_UNSUPPORTED")
    raise OSError(error_number, "no-replace publication failed")


def _publication_limits(lane_name: str, bundle_kind: str) -> tuple[dict[str, int], int]:
    if lane_name == "reports" and bundle_kind == "report":
        return (
            {"report.json": MAX_REPORT_JSON_BYTES, "report.md": MAX_REPORT_MARKDOWN_BYTES},
            MAX_REPORT_GENERATIONS,
        )
    if bundle_kind == "receipt":
        limits = {
            "enrollments": (MAX_ENROLLMENT_RECEIPT_BYTES, MAX_ENROLLMENT_BUNDLES),
            "terminals": (MAX_TERMINAL_RECEIPT_BYTES, MAX_TERMINAL_BUNDLES),
            "checkpoints": (MAX_CHECKPOINT_RECEIPT_BYTES, MAX_CHECKPOINT_BUNDLES),
        }
        if lane_name in limits:
            maximum_bytes, maximum_bundles = limits[lane_name]
            return {"receipt.json": maximum_bytes}, maximum_bundles
    _fail("E_PUBLISH_FAILED")


def _preflight_bundle_publication(
    bundle_kind: str,
    digest: str,
    rendered_files: Mapping[str, bytes],
    store_session: _StoreSession,
    *,
    lane_name: str,
    existing_validator: Callable[[Mapping[str, bytes]], object],
) -> bool:
    if bundle_kind not in BUNDLE_SHAPES:
        _fail("E_PUBLISH_FAILED")
    expected_names = BUNDLE_SHAPES[bundle_kind]
    if tuple(sorted(rendered_files)) != tuple(sorted(expected_names)):
        _fail("E_PUBLISH_FAILED")
    lane_fd = store_session.lane_fds[lane_name]
    maximum_file_bytes, maximum_bundles = _publication_limits(lane_name, bundle_kind)
    if any(len(rendered_files[name]) > maximum for name, maximum in maximum_file_bytes.items()):
        _fail("E_LIMIT")
    if bundle_kind == "report" and sum(map(len, rendered_files.values())) > MAX_REPORT_BUNDLE_BYTES:
        _fail("E_LIMIT")
    names = _scan_lane_names(lane_fd, maximum_bundles)
    existing = _read_exact_bundle(
        lane_fd,
        digest,
        bundle_kind=bundle_kind,
        maximum_file_bytes=maximum_file_bytes,
    )
    if existing is not None:
        existing_validator(existing)
        if existing == dict(rendered_files):
            return True
        _fail("E_REPLAY_DIVERGENT")

    if len(names) >= maximum_bundles:
        _fail("E_LIMIT")
    return False


def _publish_bundle(
    bundle_kind: str,
    digest: str,
    rendered_files: Mapping[str, bytes],
    store_session: _StoreSession,
    *,
    lane_name: str,
    existing_validator: Callable[[Mapping[str, bytes]], object],
) -> None:
    if _preflight_bundle_publication(
        bundle_kind,
        digest,
        rendered_files,
        store_session,
        lane_name=lane_name,
        existing_validator=existing_validator,
    ):
        return
    expected_names = BUNDLE_SHAPES[bundle_kind]
    lane_fd = store_session.lane_fds[lane_name]
    maximum_file_bytes, _ = _publication_limits(lane_name, bundle_kind)

    stage_name = ""
    stage_fd = -1
    for _attempt in range(MAX_STAGING_ATTEMPTS):
        candidate = ".stage-" + secrets.token_hex(16)
        try:
            os.mkdir(candidate, 0o700, dir_fd=lane_fd)
        except FileExistsError:
            continue
        except OSError:
            _fail("E_PUBLISH_FAILED")
        stage_name = candidate
        try:
            stage_fd = os.open(stage_name, _DIRECTORY_FLAGS, dir_fd=lane_fd)
            os.fchmod(stage_fd, 0o700)
        except OSError:
            _fail("E_PUBLISH_FAILED")
        break
    if stage_fd < 0:
        _fail("E_PUBLISH_FAILED")

    stage_metadata = os.fstat(stage_fd)
    stage_identity = (stage_metadata.st_dev, stage_metadata.st_ino)
    created_files: dict[str, tuple[int, int]] = {}
    published = False
    try:
        for name in sorted(expected_names):
            data = rendered_files[name]
            if len(data) > maximum_file_bytes[name]:
                _fail("E_LIMIT")
            try:
                leaf_fd = os.open(name, _LEAF_CREATE_FLAGS, 0o600, dir_fd=stage_fd)
            except OSError:
                _fail("E_PUBLISH_FAILED")
            try:
                os.fchmod(leaf_fd, 0o600)
                metadata = os.fstat(leaf_fd)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.geteuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o600
                    or metadata.st_nlink != 1
                ):
                    _fail("E_PUBLISH_FAILED")
                created_files[name] = (metadata.st_dev, metadata.st_ino)
                _write_all(leaf_fd, data)
                os.fsync(leaf_fd)
            except OSError:
                _fail("E_PUBLISH_FAILED")
            finally:
                os.close(leaf_fd)
            reopened = _read_stable_leaf(stage_fd, name, maximum_bytes=maximum_file_bytes[name])
            if reopened != data:
                _fail("E_PUBLISH_FAILED")
        if _bounded_entries(
            stage_fd,
            len(expected_names),
            overflow_code="E_PUBLISH_FAILED",
        ) != sorted(expected_names):
            _fail("E_PUBLISH_FAILED")
        try:
            os.fsync(stage_fd)
            os.fsync(lane_fd)
        except OSError:
            _fail("E_PUBLISH_FAILED")
        try:
            _kernel_rename_noreplace(lane_fd, stage_name, digest)
            published = True
        except OSError as publication_error:
            if publication_error.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                _fail("E_PUBLISH_FAILED")
            winner = _read_exact_bundle(
                lane_fd,
                digest,
                bundle_kind=bundle_kind,
                maximum_file_bytes=maximum_file_bytes,
            )
            if winner is None:
                _fail("E_PUBLISH_FAILED")
            existing_validator(winner)
            identical = winner == dict(rendered_files)
            _cleanup_owned_stage(
                lane_fd,
                stage_name,
                stage_fd,
                stage_identity,
                created_files,
            )
            stage_name = ""
            if identical:
                return
            _fail("E_REPLAY_DIVERGENT")
        try:
            os.fsync(lane_fd)
        except OSError:
            _fail("E_PUBLISH_FAILED")
        final_files = _read_exact_bundle(
            lane_fd,
            digest,
            bundle_kind=bundle_kind,
            maximum_file_bytes=maximum_file_bytes,
        )
        if final_files is None or final_files != dict(rendered_files):
            _fail("E_PUBLISH_FAILED")
        existing_validator(final_files)
    except Exception:
        if not published and stage_name:
            try:
                _cleanup_owned_stage(
                    lane_fd,
                    stage_name,
                    stage_fd,
                    stage_identity,
                    created_files,
                )
            except EpisodeError:
                raise EpisodeError("E_PUBLISH_FAILED")
        raise
    finally:
        os.close(stage_fd)


def _scan_enrollments(
    session: _StoreSession,
) -> tuple[dict[str, dict[str, object]], int]:
    lane_fd = session.lane_fds["enrollments"]
    names = _scan_lane_names(lane_fd, MAX_ENROLLMENT_BUNDLES)
    result: dict[str, dict[str, object]] = {}
    aggregate_bytes = 0
    for digest in names:
        files = _read_exact_bundle(
            lane_fd,
            digest,
            bundle_kind="receipt",
            maximum_file_bytes={"receipt.json": MAX_ENROLLMENT_RECEIPT_BYTES},
        )
        if files is None:
            _fail("E_STORE_UNSAFE")
        aggregate_bytes += len(files["receipt.json"])
        if aggregate_bytes > MAX_AGGREGATE_RECEIPT_SCAN_BYTES:
            _fail("E_LIMIT")
        receipt = _validate_enrollment_bundle(files)
        if receipt["episode_digest"] != digest:
            _fail("E_STORE_UNSAFE")
        result[digest] = receipt
    return result, aggregate_bytes


def _scan_terminals(
    session: _StoreSession,
    enrollments: Mapping[str, dict[str, object]],
    aggregate_bytes: int,
    *,
    checkpoints: Mapping[str, dict[str, object]] | None = None,
) -> tuple[dict[str, dict[str, object]], int]:
    lane_fd = session.lane_fds["terminals"]
    names = _scan_lane_names(lane_fd, MAX_TERMINAL_BUNDLES)
    result: dict[str, dict[str, object]] = {}
    for digest in names:
        enrollment = enrollments.get(digest)
        if enrollment is None:
            _fail("E_REPORT_MANIFEST")
        files = _read_exact_bundle(
            lane_fd,
            digest,
            bundle_kind="receipt",
            maximum_file_bytes={"receipt.json": MAX_TERMINAL_RECEIPT_BYTES},
        )
        if files is None:
            _fail("E_STORE_UNSAFE")
        aggregate_bytes += len(files["receipt.json"])
        if aggregate_bytes > MAX_AGGREGATE_RECEIPT_SCAN_BYTES:
            _fail("E_LIMIT")
        receipt = _validate_terminal_bundle(files, enrollment)
        if receipt["episode_digest"] != digest:
            _fail("E_STORE_UNSAFE")
        checkpoint = (
            _load_checkpoint(session, digest, enrollment)
            if checkpoints is None
            else checkpoints.get(digest)
        )
        _require_checkpoint_agreement(receipt["joint_pass"], checkpoint, enrollment)
        result[digest] = receipt
    return result, aggregate_bytes


def _scan_checkpoints(
    session: _StoreSession,
    enrollments: Mapping[str, dict[str, object]],
    aggregate_bytes: int,
) -> tuple[dict[str, dict[str, object]], int]:
    lane_fd = session.lane_fds.get("checkpoints")
    if lane_fd is None:
        return {}, aggregate_bytes
    result: dict[str, dict[str, object]] = {}
    for digest in _scan_lane_names(lane_fd, MAX_CHECKPOINT_BUNDLES):
        enrollment = enrollments.get(digest)
        if enrollment is None:
            _fail("E_STORE_UNSAFE")
        files = _checkpoint_files(session, digest)
        if files is None:
            _fail("E_STORE_UNSAFE")
        aggregate_bytes += len(files["receipt.json"])
        if aggregate_bytes > MAX_AGGREGATE_RECEIPT_SCAN_BYTES:
            _fail("E_LIMIT")
        result[digest] = _validate_checkpoint_bundle(files, enrollment)
        if result[digest]["episode_digest"] != digest:
            _fail("E_STORE_UNSAFE")
    return result, aggregate_bytes


def _scan_store(
    session: _StoreSession,
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    int,
]:
    enrollments, aggregate_bytes = _scan_enrollments(session)
    checkpoints, aggregate_bytes = _scan_checkpoints(session, enrollments, aggregate_bytes)
    terminals, aggregate_bytes = _scan_terminals(
        session, enrollments, aggregate_bytes, checkpoints=checkpoints
    )
    return enrollments, checkpoints, terminals, aggregate_bytes


def _preflight_supervised_receipt_append(
    session: _StoreSession, lane_name: str, episode_digest: str, rendered: bytes
) -> None:
    if "checkpoints" not in session.lane_fds:
        return
    enrollments, _checkpoints, terminals, aggregate_bytes = _scan_store(session)
    receipts = enrollments if lane_name == "enrollments" else terminals
    additional_bytes = 0 if episode_digest in receipts else len(rendered)
    if aggregate_bytes + additional_bytes > MAX_AGGREGATE_RECEIPT_SCAN_BYTES:
        _fail("E_LIMIT")


def _observation_from_terminal(
    terminal: Mapping[str, object] | None,
) -> tuple[str, str]:
    if terminal is None:
        return EPISODE_STATUS_UNKNOWN, "missing_terminal"
    recurrence = cast(Mapping[str, object], terminal["recurrence"])
    status = cast(str, recurrence["status"])
    reason = cast(str, recurrence["reason"])
    if status not in EPISODE_OBSERVATION_STATUSES:
        _fail("E_REPORT_MANIFEST")
    if reason not in EPISODE_OBSERVATION_REASONS:
        _fail("E_REPORT_MANIFEST")
    return status, reason


def _manifest_from_store(
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for digest in sorted(enrollments):
        enrollment = enrollments[digest]
        terminal = terminals.get(digest)
        status, reason = _observation_from_terminal(terminal)
        rows.append(
            {
                "episode_digest": digest,
                "episode_class": enrollment["episode_class"],
                "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
                "terminal_receipt_digest": (
                    terminal["terminal_receipt_digest"]
                    if terminal is not None
                    else "missing_terminal"
                ),
                "observation_status": status,
                "observation_reason": reason,
            }
        )
    return rows


def _receipt_time_boundaries(
    enrollment: Mapping[str, object], terminal: Mapping[str, object] | None
) -> list[str]:
    boundaries = [
        cast(str, enrollment["trigger_observed_at"]),
        cast(str, enrollment["enrollment_recorded_at"]),
    ]
    if terminal is None:
        return boundaries
    boundaries.extend(
        [
            cast(str, terminal["terminal_event_at"]),
            cast(str, terminal["terminal_recorded_at"]),
        ]
    )
    joint = cast(Mapping[str, object], terminal["joint_pass"])
    status = joint["status"]
    if status == "completed_baseline_available":
        baseline = cast(Mapping[str, object], joint["baseline"])
        boundaries.append(cast(str, baseline["joint_pass_completed_at"]))
    elif status == "completed_baseline_unavailable":
        boundaries.append(cast(str, joint["joint_pass_completed_at"]))
    return boundaries


def _require_as_of_covers(
    cohort_as_of: str,
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
    *,
    manifest: list[dict[str, object]] | None = None,
) -> None:
    if manifest is None:
        selected = [(digest, terminals.get(digest)) for digest in sorted(enrollments)]
    else:
        selected = []
        for row in manifest:
            digest = cast(str, row["episode_digest"])
            terminal = (
                None
                if row["terminal_receipt_digest"] == "missing_terminal"
                else terminals.get(digest)
            )
            selected.append((digest, terminal))
    for digest, terminal in selected:
        enrollment = enrollments.get(digest)
        if enrollment is None:
            _fail("E_REPORT_MANIFEST")
        if any(
            boundary > cohort_as_of for boundary in _receipt_time_boundaries(enrollment, terminal)
        ):
            _fail("E_ORDER")


def _report_semantic_core(
    cohort_as_of: str, manifest: list[dict[str, object]]
) -> dict[str, object]:
    prospective = [row for row in manifest if row["episode_class"] == "prospective_primary"]
    retrospective = [row for row in manifest if row["episode_class"] == "retrospective_reference"]
    cohort_core: dict[str, object] = {
        "repository_slug": REPOSITORY_SLUG,
        "cohort_as_of": cohort_as_of,
        "manifest": manifest,
    }
    return {
        "schema_version": REPORT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository_slug": REPOSITORY_SLUG,
        "cohort_as_of": cohort_as_of,
        "cohort_id": _domain_digest(COHORT_DOMAIN, cohort_core),
        "manifest": manifest,
        "prospective_primary": _status_counts(prospective, primary=True),
        "retrospective_reference": _status_counts(retrospective, primary=False),
        "claims": {
            **RECEIPT_CLAIMS,
            "all_eligible_episodes_claim": False,
        },
        "downstream_grants": dict(FALSE_GRANTS),
        "transport_capability": TRANSPORT_CAPABILITY,
    }


def _build_report_artifacts(
    cohort_as_of: str,
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
) -> tuple[dict[str, object], bytes, bytes]:
    _require_as_of_covers(cohort_as_of, enrollments, terminals)
    manifest = _manifest_from_store(enrollments, terminals)
    semantic_core = _report_semantic_core(cohort_as_of, manifest)
    markdown = _render_markdown(semantic_core)
    if len(markdown) > MAX_REPORT_MARKDOWN_BYTES:
        _fail("E_LIMIT")
    report_core = dict(semantic_core)
    report_core["markdown_sha256"] = _plain_sha256(markdown)
    report = dict(report_core)
    report["report_digest"] = _domain_digest(REPORT_DOMAIN, report_core)
    report_json = _canonical_json_bytes(report, trailing_lf=True)
    if len(report_json) > MAX_REPORT_JSON_BYTES:
        _fail("E_LIMIT")
    if len(report_json) + len(markdown) > MAX_REPORT_BUNDLE_BYTES:
        _fail("E_LIMIT")
    return report, report_json, markdown


def _validate_manifest_rows(
    value: object,
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
) -> list[dict[str, object]]:
    raw_rows = _require_list(value)
    if len(raw_rows) > MAX_ENROLLMENT_BUNDLES:
        _fail("E_REPORT_MANIFEST")
    expected_fields = frozenset(
        {
            "episode_digest",
            "episode_class",
            "enrollment_receipt_digest",
            "terminal_receipt_digest",
            "observation_status",
            "observation_reason",
        }
    )
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw_row in raw_rows:
        row = _require_object(raw_row)
        _require_exact_keys(row, expected_fields)
        digest = _require_digest(row["episode_digest"])
        if digest in seen:
            _fail("E_REPORT_MANIFEST")
        seen.add(digest)
        enrollment = enrollments.get(digest)
        if enrollment is None:
            _fail("E_REPORT_MANIFEST")
        episode_class = _require_enum(row["episode_class"], EPISODE_CLASSES)
        if episode_class != enrollment["episode_class"]:
            _fail("E_REPORT_MANIFEST")
        enrollment_digest = _require_digest(row["enrollment_receipt_digest"])
        if enrollment_digest != enrollment["enrollment_receipt_digest"]:
            _fail("E_REPORT_MANIFEST")
        terminal_digest_value = row["terminal_receipt_digest"]
        if terminal_digest_value == "missing_terminal":
            expected_status, expected_reason = EPISODE_STATUS_UNKNOWN, "missing_terminal"
            terminal_digest: str = "missing_terminal"
        else:
            terminal_digest = _require_digest(terminal_digest_value)
            terminal = terminals.get(digest)
            if terminal is None or terminal["terminal_receipt_digest"] != terminal_digest:
                _fail("E_REPORT_MANIFEST")
            expected_status, expected_reason = _observation_from_terminal(terminal)
        status = _require_enum(
            row["observation_status"],
            EPISODE_OBSERVATION_STATUSES,
        )
        reason = _require_enum(row["observation_reason"], EPISODE_OBSERVATION_REASONS)
        if (status, reason) != (expected_status, expected_reason):
            _fail("E_REPORT_MANIFEST")
        rows.append(
            {
                "episode_digest": digest,
                "episode_class": episode_class,
                "enrollment_receipt_digest": enrollment_digest,
                "terminal_receipt_digest": terminal_digest,
                "observation_status": status,
                "observation_reason": reason,
            }
        )
    if rows != sorted(rows, key=lambda row: cast(str, row["episode_digest"])):
        _fail("E_REPORT_MANIFEST")
    return rows


def _validate_report_bundle(
    files: Mapping[str, bytes],
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
) -> dict[str, object]:
    raw_report = _strict_stored_json(files["report.json"], maximum_bytes=MAX_REPORT_JSON_BYTES)
    report = _require_object(raw_report)
    schema_projection = cast(Mapping[str, object], POLICY_PROJECTION["schemas"])
    report_projection = cast(Mapping[str, object], schema_projection["report"])
    expected_fields = frozenset(cast(tuple[str, ...], report_projection["fields"]))
    _require_exact_keys(report, expected_fields)
    _require_literal(report["schema_version"], REPORT_SCHEMA)
    _require_literal(report["policy_version"], POLICY_VERSION)
    _require_literal(report["repository_slug"], REPOSITORY_SLUG)
    cohort_as_of = _require_timestamp(report["cohort_as_of"])
    manifest = _validate_manifest_rows(report["manifest"], enrollments, terminals)
    _require_as_of_covers(cohort_as_of, enrollments, terminals, manifest=manifest)
    expected_semantic = _report_semantic_core(cohort_as_of, manifest)
    for field, expected in expected_semantic.items():
        if report.get(field) != expected:
            _fail("E_REPORT_MANIFEST")
    _require_receipt_claims(report["claims"], report=True)
    _require_false_grants(report["downstream_grants"])
    _require_literal(report["transport_capability"], TRANSPORT_CAPABILITY)
    markdown = _render_markdown(expected_semantic)
    if files["report.md"] != markdown:
        _fail("E_REPORT_MANIFEST")
    markdown_digest = _require_digest(report["markdown_sha256"])
    if markdown_digest != _plain_sha256(markdown):
        _fail("E_REPORT_MANIFEST")
    report_core = dict(expected_semantic)
    report_core["markdown_sha256"] = markdown_digest
    report_digest = _require_digest(report["report_digest"])
    expected_digest = _domain_digest(REPORT_DOMAIN, report_core)
    expected_report = dict(report_core)
    expected_report["report_digest"] = expected_digest
    if report_digest != expected_digest or _canonical_json_bytes(report) != _canonical_json_bytes(
        expected_report
    ):
        _fail("E_REPORT_MANIFEST")
    return report


def _validate_prior_reports(
    session: _StoreSession,
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
) -> list[dict[str, object]]:
    lane_fd = session.lane_fds["reports"]
    names = _scan_lane_names(lane_fd, MAX_REPORT_GENERATIONS)
    reports: list[dict[str, object]] = []
    for digest in names:
        files = _read_exact_bundle(
            lane_fd,
            digest,
            bundle_kind="report",
            maximum_file_bytes={
                "report.json": MAX_REPORT_JSON_BYTES,
                "report.md": MAX_REPORT_MARKDOWN_BYTES,
            },
        )
        if files is None:
            _fail("E_STORE_UNSAFE")
        report = _validate_report_bundle(files, enrollments, terminals)
        if report["report_digest"] != digest:
            _fail("E_REPORT_MANIFEST")
        reports.append(report)
    return reports


def _ack(operation: str, **fields: object) -> dict[str, object]:
    return {
        "schema_version": ACK_SCHEMA,
        "status": "ok",
        "operation": operation,
        **fields,
    }


def _run_enroll(document: object, repository_anchor_fd: int) -> dict[str, object]:
    receipt = _build_enrollment_receipt(document)
    rendered = _canonical_json_bytes(receipt, trailing_lf=True)
    if len(rendered) > MAX_ENROLLMENT_RECEIPT_BYTES:
        _fail("E_LIMIT")
    episode_digest = cast(str, receipt["episode_digest"])
    with _StoreSession(repository_anchor_fd, exclusive=True, create=True) as session:
        existing_enrollment = _load_enrollment(session, episode_digest, required=False)
        if existing_enrollment is None:
            orphan_terminal = _read_exact_bundle(
                session.lane_fds["terminals"],
                episode_digest,
                bundle_kind="receipt",
                maximum_file_bytes={"receipt.json": MAX_TERMINAL_RECEIPT_BYTES},
            )
            if (
                orphan_terminal is not None
                or _checkpoint_files(session, episode_digest) is not None
            ):
                _fail("E_STORE_UNSAFE")
        else:
            _load_checkpoint(session, episode_digest, existing_enrollment)
            _load_terminal(session, episode_digest, existing_enrollment)

        def validate_existing(files: Mapping[str, bytes]) -> dict[str, object]:
            existing = _validate_enrollment_bundle(files)
            if existing["episode_digest"] != episode_digest:
                _fail("E_STORE_UNSAFE")
            return existing

        _preflight_supervised_receipt_append(session, "enrollments", episode_digest, rendered)
        _publish_bundle(
            "receipt",
            episode_digest,
            {"receipt.json": rendered},
            session,
            lane_name="enrollments",
            existing_validator=validate_existing,
        )
    return _ack(
        "enroll",
        episode_digest=episode_digest,
        enrollment_receipt_digest=receipt["enrollment_receipt_digest"],
    )


def _bound_episode_digest(document: object, *, fields: frozenset[str]) -> str:
    value = _require_object(document)
    _require_exact_keys(value, fields)
    return _require_digest(value["episode_digest"])


def _run_validate(document: object, repository_anchor_fd: int) -> dict[str, object]:
    episode_digest = _bound_episode_digest(document, fields=_BASELINE_FIELDS)
    with _StoreSession(repository_anchor_fd, exclusive=False, create=False) as session:
        enrollment = _load_enrollment(session, episode_digest, required=True)
        if enrollment is None:
            _fail("E_DEPENDENCY")
        if _load_terminal(session, episode_digest, enrollment) is not None:
            _fail("E_ORDER")
        baseline = _normalize_joint_pass_baseline(document, enrollment)
        checkpoint = _load_checkpoint(session, episode_digest, enrollment)
        if checkpoint is not None and baseline != checkpoint["baseline"]:
            _fail("E_DEPENDENCY")
    return _baseline_ack(baseline)


def _prepare_terminal_publication(
    session: _StoreSession,
    document: object,
    enrollment: Mapping[str, object],
    *,
    available_requires_checkpoint: bool = False,
) -> tuple[dict[str, object], dict[str, bytes]]:
    episode_digest = _bound_episode_digest(document, fields=_TERMINAL_INPUT_FIELDS)
    checkpoint = _load_checkpoint(session, episode_digest, enrollment)
    _load_terminal(session, episode_digest, enrollment)
    _require_checkpoint_agreement(
        _require_object(document)["joint_pass"],
        checkpoint,
        enrollment,
        available_requires_checkpoint=available_requires_checkpoint,
    )
    receipt = _build_terminal_receipt(document, enrollment)
    files = {"receipt.json": _canonical_json_bytes(receipt, trailing_lf=True)}
    _preflight_bundle_publication(
        "receipt",
        episode_digest,
        files,
        session,
        lane_name="terminals",
        existing_validator=lambda stored: _validate_terminal_bundle(stored, enrollment),
    )
    return receipt, files


def _publish_terminal(
    session: _StoreSession,
    receipt: Mapping[str, object],
    files: Mapping[str, bytes],
    enrollment: Mapping[str, object],
) -> None:
    _publish_bundle(
        "receipt",
        cast(str, receipt["episode_digest"]),
        files,
        session,
        lane_name="terminals",
        existing_validator=lambda stored: _validate_terminal_bundle(stored, enrollment),
    )


def _run_terminal(document: object, repository_anchor_fd: int) -> dict[str, object]:
    episode_digest = _bound_episode_digest(document, fields=_TERMINAL_INPUT_FIELDS)
    with _StoreSession(repository_anchor_fd, exclusive=True, create=False) as session:
        enrollment = _load_enrollment(session, episode_digest, required=True)
        if enrollment is None:
            _fail("E_DEPENDENCY")
        receipt, files = _prepare_terminal_publication(session, document, enrollment)
        _preflight_supervised_receipt_append(
            session, "terminals", episode_digest, files["receipt.json"]
        )
        _publish_terminal(session, receipt, files, enrollment)
    return _ack(
        "terminal",
        episode_digest=episode_digest,
        terminal_receipt_digest=receipt["terminal_receipt_digest"],
    )


def _prepare_report_publication(
    session: _StoreSession,
    cohort_as_of: str,
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
) -> tuple[dict[str, object], dict[str, bytes]]:
    report, report_json, markdown = _build_report_artifacts(cohort_as_of, enrollments, terminals)
    files = {"report.json": report_json, "report.md": markdown}
    _preflight_bundle_publication(
        "report",
        cast(str, report["report_digest"]),
        files,
        session,
        lane_name="reports",
        existing_validator=lambda stored: _validate_report_bundle(stored, enrollments, terminals),
    )
    return report, files


def _publish_report(
    session: _StoreSession,
    report: Mapping[str, object],
    files: Mapping[str, bytes],
    enrollments: Mapping[str, dict[str, object]],
    terminals: Mapping[str, dict[str, object]],
) -> None:
    _publish_bundle(
        "report",
        cast(str, report["report_digest"]),
        files,
        session,
        lane_name="reports",
        existing_validator=lambda stored: _validate_report_bundle(stored, enrollments, terminals),
    )


def _run_report(document: object, repository_anchor_fd: int) -> dict[str, object]:
    request = _normalize_report_request(document)
    cohort_as_of = cast(str, request["cohort_as_of"])
    with _StoreSession(repository_anchor_fd, exclusive=True, create=True) as session:
        enrollments, _checkpoints, terminals, _aggregate_bytes = _scan_store(session)
        _validate_prior_reports(session, enrollments, terminals)
        report, files = _prepare_report_publication(session, cohort_as_of, enrollments, terminals)
        _publish_report(session, report, files, enrollments, terminals)
    return _ack(
        "report",
        cohort_id=report["cohort_id"],
        report_digest=report["report_digest"],
        markdown_sha256=report["markdown_sha256"],
    )


def _supervision_ack(operation: str, **fields: object) -> dict[str, object]:
    return {
        "schema_version": SUPERVISION_ACK_SCHEMA,
        "policy_version": SUPERVISION_POLICY_VERSION,
        "status": "ok",
        "operation": operation,
        **fields,
        "downstream_grants": dict(FALSE_GRANTS),
    }


def _run_checkpoint(document: object, repository_anchor_fd: int) -> dict[str, object]:
    episode_digest = _bound_episode_digest(document, fields=_BASELINE_FIELDS)
    with _StoreSession(repository_anchor_fd, exclusive=True, create=False) as session:
        enrollments, checkpoints, terminals, aggregate_bytes = _scan_store(session)
        enrollment = enrollments.get(episode_digest)
        if enrollment is None:
            _fail("E_DEPENDENCY")
        receipt = _build_checkpoint_receipt(document, enrollment)
        rendered = _canonical_json_bytes(receipt, trailing_lf=True)
        if len(rendered) > MAX_CHECKPOINT_RECEIPT_BYTES:
            _fail("E_LIMIT")
        if episode_digest not in checkpoints:
            if episode_digest in terminals:
                _fail("E_ORDER")
            if _minimum_terminal_receipt_bytes(receipt, enrollment) > MAX_TERMINAL_RECEIPT_BYTES:
                _fail("E_LIMIT")
            if aggregate_bytes + len(rendered) > MAX_AGGREGATE_RECEIPT_SCAN_BYTES:
                _fail("E_LIMIT")
        session.create_checkpoint_lane()
        _publish_bundle(
            "receipt",
            episode_digest,
            {"receipt.json": rendered},
            session,
            lane_name="checkpoints",
            existing_validator=lambda stored: _validate_checkpoint_bundle(stored, enrollment),
        )
    return _supervision_ack(
        "checkpoint",
        episode_digest=episode_digest,
        checkpoint_receipt_digest=receipt["checkpoint_receipt_digest"],
        joint_pass_baseline_digest=receipt["joint_pass_baseline_digest"],
    )


def _run_status(document: object, repository_anchor_fd: int) -> dict[str, object]:
    request = _require_object(document)
    _require_exact_keys(request, _STATUS_REQUEST_FIELDS)
    _require_literal(request["schema_version"], STATUS_REQUEST_SCHEMA)
    pr_number = _require_positive_pr(request["pull_request_number"])
    digest = _episode_digest(pr_number)
    result: dict[str, object] = {
        "pull_request_number": pr_number,
        "episode_digest": digest,
        "lifecycle": "absent",
        "report_status": "absent",
    }
    with _StoreSession(
        repository_anchor_fd, exclusive=False, create=False, allow_absent=True
    ) as session:
        if session.absent:
            return _supervision_ack("status", **result)
        enrollments, checkpoints, terminals, _aggregate_bytes = _scan_store(session)
        reports = _validate_prior_reports(session, enrollments, terminals)
        manifest = _manifest_from_store(enrollments, terminals)
        current = [report for report in reports if report["manifest"] == manifest]
        if current:
            selected = max(
                current,
                key=lambda report: (
                    cast(str, report["cohort_as_of"]),
                    cast(str, report["report_digest"]),
                ),
            )
            result.update(
                report_status="current",
                report_digest=selected["report_digest"],
                cohort_as_of=selected["cohort_as_of"],
            )
        elif reports:
            result["report_status"] = "stale"
        enrollment = enrollments.get(digest)
        if enrollment is not None:
            result["enrollment_receipt_digest"] = enrollment["enrollment_receipt_digest"]
            result["lifecycle"] = "enrolled_awaiting_checkpoint"
            checkpoint = checkpoints.get(digest)
            if checkpoint is not None:
                result.update(
                    lifecycle="enrolled_awaiting_terminal",
                    checkpoint_receipt_digest=checkpoint["checkpoint_receipt_digest"],
                    joint_pass_baseline_digest=checkpoint["joint_pass_baseline_digest"],
                )
            terminal = terminals.get(digest)
            if terminal is not None:
                result.update(
                    lifecycle="complete" if current else "terminal_awaiting_report",
                    terminal_receipt_digest=terminal["terminal_receipt_digest"],
                    observation_status=cast(Mapping[str, object], terminal["recurrence"])["status"],
                    observation_reason=cast(Mapping[str, object], terminal["recurrence"])["reason"],
                )
    return _supervision_ack("status", **result)


def _run_complete(document: object, repository_anchor_fd: int) -> dict[str, object]:
    request = _require_object(document)
    _require_exact_keys(request, _COMPLETE_INPUT_FIELDS)
    _require_literal(request["schema_version"], COMPLETE_INPUT_SCHEMA)
    episode_digest = _bound_episode_digest(request["terminal"], fields=_TERMINAL_INPUT_FIELDS)
    report_request = _normalize_report_request(request["report_request"])
    cohort_as_of = cast(str, report_request["cohort_as_of"])
    with _StoreSession(repository_anchor_fd, exclusive=True, create=False) as session:
        enrollments, _checkpoints, terminals, aggregate_bytes = _scan_store(session)
        enrollment = enrollments.get(episode_digest)
        if enrollment is None:
            _fail("E_DEPENDENCY")
        _validate_prior_reports(session, enrollments, terminals)
        terminal, terminal_files = _prepare_terminal_publication(
            session, request["terminal"], enrollment, available_requires_checkpoint=True
        )
        if (
            episode_digest not in terminals
            and aggregate_bytes + len(terminal_files["receipt.json"])
            > MAX_AGGREGATE_RECEIPT_SCAN_BYTES
        ):
            _fail("E_LIMIT")
        prospective_terminals = dict(terminals)
        prospective_terminals[episode_digest] = terminal
        report, report_files = _prepare_report_publication(
            session, cohort_as_of, enrollments, prospective_terminals
        )
        _publish_terminal(session, terminal, terminal_files, enrollment)
        _publish_report(session, report, report_files, enrollments, prospective_terminals)
    return _supervision_ack(
        "complete",
        episode_digest=episode_digest,
        lifecycle="complete",
        terminal_receipt_digest=terminal["terminal_receipt_digest"],
        cohort_id=report["cohort_id"],
        report_digest=report["report_digest"],
        markdown_sha256=report["markdown_sha256"],
    )


def _require_public_verb(value: object) -> str:
    if not isinstance(value, str) or value not in (
        "enroll",
        "terminal",
        "validate",
        "report",
        *SUPERVISION_VERBS,
    ):
        _fail("E_USAGE")
    return value


def _run_operation(verb: str, document: object, repository_anchor_fd: int) -> dict[str, object]:
    operation = _require_public_verb(verb)
    if operation == "enroll":
        return _run_enroll(document, repository_anchor_fd)
    if operation == "terminal":
        return _run_terminal(document, repository_anchor_fd)
    if operation == "validate":
        return _run_validate(document, repository_anchor_fd)
    if operation == "checkpoint":
        return _run_checkpoint(document, repository_anchor_fd)
    if operation == "status":
        return _run_status(document, repository_anchor_fd)
    if operation == "complete":
        return _run_complete(document, repository_anchor_fd)
    return _run_report(document, repository_anchor_fd)


def _read_bounded_stdin() -> bytes:
    try:
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    except OSError:
        _fail("E_JSON_INVALID")
    if len(raw) > MAX_STDIN_BYTES:
        _fail("E_INPUT_TOO_LARGE")
    return raw


def _write_ack(value: Mapping[str, object]) -> None:
    rendered = _canonical_json_bytes(value, trailing_lf=True)
    if len(rendered) > MAX_STDOUT_BYTES:
        _fail("E_STDOUT")
    offset = 0
    try:
        descriptor = sys.stdout.fileno()
        while offset < len(rendered):
            written = os.write(descriptor, rendered[offset:])
            if written <= 0:
                _fail("E_STDOUT")
            offset += written
    except (OSError, ValueError):
        _fail("E_STDOUT")


def _write_error(code: str) -> None:
    rendered = (code + "\n").encode("ascii")
    if len(rendered) > MAX_STDERR_BYTES:
        return
    try:
        os.write(sys.stderr.fileno(), rendered)
    except (OSError, ValueError):
        return


def _fallback_code(operation: str | None) -> str:
    if operation in ("enroll", "terminal", "checkpoint", "complete"):
        return "E_PUBLISH_FAILED"
    if operation in ("validate", "status"):
        return "E_DEPENDENCY"
    if operation == "report":
        return "E_REPORT_MANIFEST"
    return "E_USAGE"


def _open_repository_anchor() -> int:
    module_path = os.path.realpath(os.path.abspath(__file__))
    repository_path = os.path.dirname(os.path.dirname(os.path.dirname(module_path)))
    try:
        descriptor = os.open(repository_path, _DIRECTORY_FLAGS)
        os.set_inheritable(descriptor, False)
        _verify_directory_metadata(os.fstat(descriptor), exact_mode=False)
        return descriptor
    except EpisodeError:
        raise
    except OSError:
        _fail("E_STORE_UNSAFE")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    operation: str | None = None
    repository_anchor_fd = -1
    try:
        if len(arguments) != 1:
            _fail("E_USAGE")
        operation = _require_public_verb(arguments[0])
        document = _strict_json_document(_read_bounded_stdin())
        repository_anchor_fd = _open_repository_anchor()
        result = _run_operation(operation, document, repository_anchor_fd)
        _write_ack(result)
        return 0
    except EpisodeError as error:
        _write_error(error.code)
        return 1
    except Exception:
        _write_error(_fallback_code(operation))
        return 1
    finally:
        if repository_anchor_fd >= 0:
            try:
                os.close(repository_anchor_fd)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())

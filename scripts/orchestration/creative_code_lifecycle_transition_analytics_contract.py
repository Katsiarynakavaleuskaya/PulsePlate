"""Deterministic aggregate transition analytics for creative-code telemetry.

The artifact is a local, descriptive consumer of already-validated telemetry.
It deliberately retains no raw lineage identifiers and grants no routing,
promotion, review, merge, learning, provider, or product-runtime authority.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import json
import re
from typing import Any, cast

from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    SCHEMA_VERSION as TELEMETRY_V1_SCHEMA_VERSION,
    V2_SCHEMA_VERSION as TELEMETRY_V2_SCHEMA_VERSION,
    build_creative_code_telemetry_rollup_v2,
    default_authority,
    reject_unsafe_telemetry_value,
    validate_creative_code_telemetry_event_any,
    validate_creative_code_telemetry_rollup_v2,
)

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "creative_code_lifecycle_transition_analytics"
POLICY_VERSION = "creative-code-lifecycle-transition-analytics-v1"
SUCCESS_OUTPUT = "PASS: creative-code lifecycle transition analytics contract valid"

MAX_EVENTS = 1_000_000
MAX_COUNT = 1_000_000_000_000
FINGERPRINT_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
ANALYTICS_ID_RE = re.compile(
    r"^evidence:creative_code_lifecycle_transition_analytics:" r"control_plane:1\.0:[a-f0-9]{24}$"
)
IDEMPOTENCY_RE = re.compile(r"^idem:[a-f0-9]{64}$")

STAGES = (
    "specification",
    "patch_evaluation",
    "promotion_plan",
    "promotion_validation",
    "promotion_approval",
    "pr_open",
    "pr_terminal",
)
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGES)}
HISTOGRAM_BUCKETS = ("0", "1", "2", "3_or_more")
PROCESS_KEYS = ("repair_cycles", "review_cycles", "validation_attempts")

SOURCE_TYPES = {
    "specification": "creative_code_specification",
    "patch_evaluation": "creative_code_patch_result",
    "promotion_plan": "creative_code_pr_promotion_plan",
    "promotion_validation": "creative_code_pr_promotion_validation",
    "promotion_approval": "creative_code_pr_promotion_approval",
    "pr_open": "creative_code_pr_promotion_receipt",
    "artifact_read_error": "creative_code_artifact_read_error",
}
STATUS_PROFILES = {
    "specification": frozenset({"accepted", "rejected"}),
    "patch_evaluation": frozenset({"accepted", "rejected"}),
    "promotion_plan": frozenset({"accepted"}),
    "promotion_validation": frozenset({"accepted"}),
    "promotion_approval": frozenset({"accepted"}),
    "pr_open": frozenset({"blocked", "opened"}),
    "artifact_read_error": frozenset({"blocked"}),
}
ALLOWED_TRANSITIONS = frozenset(
    {
        ("specification", "accepted", "patch_evaluation", "accepted"),
        ("specification", "accepted", "patch_evaluation", "rejected"),
        ("patch_evaluation", "accepted", "promotion_plan", "accepted"),
        ("promotion_plan", "accepted", "promotion_validation", "accepted"),
        ("promotion_validation", "accepted", "promotion_approval", "accepted"),
        ("promotion_approval", "accepted", "pr_open", "blocked"),
        ("promotion_approval", "accepted", "pr_open", "opened"),
        ("pr_open", "opened", "pr_terminal", "closed_unmerged"),
        ("pr_open", "opened", "pr_terminal", "merged"),
    }
)
REQUIRED_COMPLETE_LINEAGE_EDGES = tuple(zip(STAGES[1:], STAGES[2:]))
COMPLETE_LINEAGE_ROOT_TRANSITION = (
    "specification",
    "accepted",
    "patch_evaluation",
    "accepted",
)
CONTINUATION_STATUSES = {
    "specification": frozenset({"accepted"}),
    "patch_evaluation": frozenset({"accepted"}),
    "promotion_plan": frozenset({"accepted"}),
    "promotion_validation": frozenset({"accepted"}),
    "promotion_approval": frozenset({"accepted"}),
    "pr_open": frozenset({"opened"}),
}
CAVEATS = [
    "aggregate_only",
    "descriptive_only",
    "local_only",
    "not_learning_or_routing_authority",
    "not_merge_readiness_evidence",
    "terminal_cohort_may_be_partial",
]

TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "analytics_id",
        "idempotency_key",
        "corpus",
        "transition_counts",
        "lineage_accounting",
        "cycle_histograms",
        "authority",
        "caveats",
        "sanitized",
    }
)
CORPUS_KEYS = frozenset(
    {
        "events_fingerprint",
        "rollup_fingerprint",
        "event_count",
        "legacy_event_count",
        "terminal_event_count",
        "terminal_cohort_observed",
    }
)
TRANSITION_KEYS = frozenset({"from_stage", "from_status", "to_stage", "to_status", "count"})
LINEAGE_KEYS = frozenset(
    {
        "observed_transition_count",
        "complete_terminal_lineage_count",
        "incomplete_terminal_lineage_count",
        "unobserved_predecessors_by_stage",
        "unobserved_successors_by_stage",
    }
)


class CreativeCodeLifecycleTransitionAnalyticsError(ValueError):
    """Raised when telemetry cannot produce one safe deterministic artifact."""


def _exact_keys(payload: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            f"{label} has invalid keys; missing={missing}, extra={extra}."
        )


def _object(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CreativeCodeLifecycleTransitionAnalyticsError(f"{label} must be an object.")
    return value


def _integer(value: Any, *, label: str, maximum: int = MAX_COUNT) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CreativeCodeLifecycleTransitionAnalyticsError(f"{label} must be an integer.")
    if value < 0 or value > maximum:
        raise CreativeCodeLifecycleTransitionAnalyticsError(f"{label} is out of range.")
    return int(value)


def _fingerprint(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not FINGERPRINT_RE.fullmatch(value):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            f"{label} must be a canonical SHA-256 fingerprint."
        )
    return value


def _candidate_value(event: Mapping[str, Any], key: str) -> str | None:
    value = event["candidate_ids"][key]
    return cast(str | None, value)


def _require_candidate_profile(event: Mapping[str, Any]) -> None:
    """Close the event profiles used as join truth by this consumer."""

    stage = cast(str, event["lane_stage"])
    if stage == "pr_terminal":
        return
    expected_source = SOURCE_TYPES.get(stage)
    if expected_source is None or event["source_artifact_type"] != expected_source:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "telemetry event source/stage profile is unsupported."
        )
    if event["status"] not in STATUS_PROFILES[stage]:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "telemetry event status/stage profile is unsupported."
        )

    required: frozenset[str]
    optional: frozenset[str] = frozenset()
    if stage == "specification":
        required = frozenset({"source_packet_id", "source_bundle_id"})
        optional = frozenset({"selected_variant_id"})
    elif stage == "patch_evaluation":
        required = frozenset({"source_bundle_id", "selected_variant_id", "request_id", "result_id"})
    elif stage == "promotion_plan":
        required = frozenset(
            {
                "source_bundle_id",
                "selected_variant_id",
                "request_id",
                "result_id",
                "promotion_id",
            }
        )
    elif stage in {"promotion_validation", "promotion_approval"}:
        required = frozenset({"promotion_id"})
    elif stage == "pr_open":
        required = frozenset({"result_id", "promotion_id"})
    else:
        required = frozenset()

    for key in event["candidate_ids"]:
        value = _candidate_value(event, key)
        if key in required and value is None:
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                "telemetry event candidate profile is incomplete."
            )
        if key not in required and key not in optional and value is not None:
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                "telemetry event candidate profile contains unsupported lineage."
            )

    source_id = event["source_artifact_id"]
    if stage == "specification" and _candidate_value(event, "source_bundle_id") != source_id:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "specification source identity does not match bundle lineage."
        )
    if (
        stage == "specification"
        and event["status"] == "accepted"
        and _candidate_value(event, "selected_variant_id") is None
    ):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "accepted specification requires selected variant lineage."
        )
    if stage == "patch_evaluation" and _candidate_value(event, "result_id") != source_id:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "patch source identity does not match result lineage."
        )
    if stage in {"promotion_plan", "promotion_validation"} and (
        _candidate_value(event, "promotion_id") != source_id
    ):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "promotion source identity does not match promotion lineage."
        )


def _promotion_id(event: Mapping[str, Any]) -> str:
    if event["lane_stage"] == "pr_terminal":
        return cast(str, event["terminal_projection"]["promotion_id"])
    value = _candidate_value(event, "promotion_id")
    if value is None:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "promotion-stage event is missing promotion lineage."
        )
    return value


def _join_key(event: Mapping[str, Any], edge_index: int) -> tuple[str, ...]:
    stage = cast(str, event["lane_stage"])
    values: tuple[str | None, ...]
    if edge_index == 0:
        values = (
            _candidate_value(event, "source_bundle_id"),
            _candidate_value(event, "selected_variant_id"),
        )
    elif edge_index == 1:
        values = (
            _candidate_value(event, "source_bundle_id"),
            _candidate_value(event, "selected_variant_id"),
            _candidate_value(event, "request_id"),
            _candidate_value(event, "result_id"),
        )
    else:
        values = (_promotion_id(event),)
    if any(value is None for value in values):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            f"{stage} event is missing required adjacent-stage lineage."
        )
    return cast(tuple[str, ...], values)


def _normalized_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [validate_creative_code_telemetry_event_any(event) for event in events]
    normalized.sort(key=lambda row: row["event_id"])
    for event in normalized:
        _require_candidate_profile(event)
    return normalized


def _transition_sort_key(row: Mapping[str, Any]) -> tuple[int, str, int, str]:
    return (
        STAGE_INDEX[cast(str, row["from_stage"])],
        cast(str, row["from_status"]),
        STAGE_INDEX[cast(str, row["to_stage"])],
        cast(str, row["to_status"]),
    )


def _derive_transitions(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_stage: dict[str, list[Mapping[str, Any]]] = {stage: [] for stage in STAGES}
    for event in events:
        stage = cast(str, event["lane_stage"])
        if stage in by_stage:
            by_stage[stage].append(event)

    # A promotion can have at most one semantic carrier at each promotion stage.
    for stage in STAGES[2:]:
        seen: set[str] = set()
        for event in by_stage[stage]:
            promotion_id = _promotion_id(event)
            if promotion_id in seen:
                raise CreativeCodeLifecycleTransitionAnalyticsError(
                    "duplicate promotion-stage lineage."
                )
            seen.add(promotion_id)

    pair_counts: Counter[tuple[str, str, str, str]] = Counter()
    predecessor_by_destination: dict[str, str] = {}
    successors_by_predecessor: dict[str, set[str]] = defaultdict(set)
    unobserved_predecessors = {stage: 0 for stage in STAGES}

    for edge_index, (from_stage, to_stage) in enumerate(zip(STAGES, STAGES[1:])):
        predecessors: dict[tuple[str, ...], Mapping[str, Any]] = {}
        for event in by_stage[from_stage]:
            try:
                key = _join_key(event, edge_index)
            except CreativeCodeLifecycleTransitionAnalyticsError:
                if from_stage == "specification" and event["status"] == "rejected":
                    continue
                raise
            if key in predecessors:
                raise CreativeCodeLifecycleTransitionAnalyticsError(
                    "ambiguous adjacent-stage predecessor lineage."
                )
            predecessors[key] = event
        for destination in by_stage[to_stage]:
            key = _join_key(destination, edge_index)
            predecessor = predecessors.get(key)
            if predecessor is None:
                unobserved_predecessors[to_stage] += 1
                continue
            transition = (
                from_stage,
                cast(str, predecessor["status"]),
                to_stage,
                cast(str, destination["status"]),
            )
            if transition not in ALLOWED_TRANSITIONS:
                raise CreativeCodeLifecycleTransitionAnalyticsError(
                    "incompatible adjacent-stage status transition."
                )
            pair_counts[transition] += 1
            destination_id = cast(str, destination["event_id"])
            predecessor_id = cast(str, predecessor["event_id"])
            predecessor_by_destination[destination_id] = predecessor_id
            successors_by_predecessor[predecessor_id].add(destination_id)

    unobserved_successors = {stage: 0 for stage in STAGES}
    for stage in STAGES[:-1]:
        for event in by_stage[stage]:
            if event["status"] not in CONTINUATION_STATUSES[stage]:
                continue
            if cast(str, event["event_id"]) not in successors_by_predecessor:
                unobserved_successors[stage] += 1

    complete_terminal = 0
    for terminal in by_stage["pr_terminal"]:
        current_id = cast(str, terminal["event_id"])
        complete = True
        for _ in range(len(STAGES) - 1):
            previous_id = predecessor_by_destination.get(current_id)
            if previous_id is None:
                complete = False
                break
            current_id = previous_id
        if complete:
            complete_terminal += 1

    transition_rows = [
        {
            "from_stage": key[0],
            "from_status": key[1],
            "to_stage": key[2],
            "to_status": key[3],
            "count": count,
        }
        for key, count in pair_counts.items()
    ]
    transition_rows.sort(key=_transition_sort_key)
    terminal_count = len(by_stage["pr_terminal"])
    lineage = {
        "observed_transition_count": sum(pair_counts.values()),
        "complete_terminal_lineage_count": complete_terminal,
        "incomplete_terminal_lineage_count": terminal_count - complete_terminal,
        "unobserved_predecessors_by_stage": unobserved_predecessors,
        "unobserved_successors_by_stage": unobserved_successors,
    }
    return transition_rows, lineage


def _bucket(value: int) -> str:
    if value >= 3:
        return "3_or_more"
    return str(value)


def _cycle_histograms(events: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    histograms = {key: {bucket: 0 for bucket in HISTOGRAM_BUCKETS} for key in PROCESS_KEYS}
    for event in events:
        if event["lane_stage"] != "pr_terminal":
            continue
        for key in PROCESS_KEYS:
            histograms[key][_bucket(cast(int, event["process"][key]))] += 1
    return histograms


def _identity_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key] for key in sorted(TOP_LEVEL_KEYS - {"analytics_id", "idempotency_key"})
    }


def _identity(payload: Mapping[str, Any]) -> tuple[str, str]:
    corpus = cast(Mapping[str, Any], payload["corpus"])
    fingerprint = fingerprint_payload(cast(Any, _identity_payload(payload)))
    upstream_ids = (
        cast(str, corpus["events_fingerprint"]),
        cast(str, corpus["rollup_fingerprint"]),
    )
    analytics_id = build_asset_id(
        asset_type=ARTIFACT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=ARTIFACT_TYPE,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return analytics_id, idempotency_key


def build_creative_code_lifecycle_transition_analytics(
    events: Sequence[Mapping[str, Any]],
    *,
    telemetry_rollup: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one aggregate-only artifact from one exact mixed v2 snapshot."""

    normalized_events = _normalized_events(events)
    normalized_rollup = validate_creative_code_telemetry_rollup_v2(telemetry_rollup)
    rebuilt_rollup = build_creative_code_telemetry_rollup_v2(
        normalized_events,
        input_roots=cast(Sequence[str], normalized_rollup["input_roots"]),
    )
    if rebuilt_rollup != normalized_rollup:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "telemetry rollup does not match the exact event snapshot."
        )

    transitions, lineage = _derive_transitions(normalized_events)
    legacy_count = sum(
        event["schema_version"] == TELEMETRY_V1_SCHEMA_VERSION for event in normalized_events
    )
    terminal_count = sum(
        event["schema_version"] == TELEMETRY_V2_SCHEMA_VERSION for event in normalized_events
    )
    events_fingerprint = fingerprint_payload(cast(Any, normalized_events))
    rollup_fingerprint = fingerprint_payload(cast(Any, normalized_rollup))
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "analytics_id": "pending",
        "idempotency_key": "pending",
        "corpus": {
            "events_fingerprint": events_fingerprint,
            "rollup_fingerprint": rollup_fingerprint,
            "event_count": len(normalized_events),
            "legacy_event_count": legacy_count,
            "terminal_event_count": terminal_count,
            "terminal_cohort_observed": terminal_count > 0,
        },
        "transition_counts": transitions,
        "lineage_accounting": lineage,
        "cycle_histograms": _cycle_histograms(normalized_events),
        "authority": default_authority(),
        "caveats": list(CAVEATS),
        "sanitized": True,
    }
    analytics_id, idempotency_key = _identity(payload)
    payload["analytics_id"] = analytics_id
    payload["idempotency_key"] = idempotency_key
    return validate_creative_code_lifecycle_transition_analytics(payload)


def _closed_stage_counts(raw: Any, *, label: str) -> dict[str, int]:
    payload = _object(raw, label=label)
    _exact_keys(payload, frozenset(STAGES), label=label)
    return {stage: _integer(payload[stage], label=f"{label}.{stage}") for stage in STAGES}


def _histogram(raw: Any, *, label: str) -> dict[str, int]:
    payload = _object(raw, label=label)
    _exact_keys(payload, frozenset(HISTOGRAM_BUCKETS), label=label)
    return {
        bucket: _integer(payload[bucket], label=f"{label}.{bucket}") for bucket in HISTOGRAM_BUCKETS
    }


def validate_creative_code_lifecycle_transition_analytics(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate closed shape, arithmetic, ordering, and content identities."""

    _exact_keys(payload, TOP_LEVEL_KEYS, label="analytics")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise CreativeCodeLifecycleTransitionAnalyticsError("schema_version is unsupported.")
    if payload.get("artifact_type") != ARTIFACT_TYPE:
        raise CreativeCodeLifecycleTransitionAnalyticsError("artifact_type is unsupported.")
    if payload.get("policy_version") != POLICY_VERSION:
        raise CreativeCodeLifecycleTransitionAnalyticsError("policy_version is unsupported.")
    analytics_id = payload.get("analytics_id")
    idempotency_key = payload.get("idempotency_key")
    if not isinstance(analytics_id, str) or not ANALYTICS_ID_RE.fullmatch(analytics_id):
        raise CreativeCodeLifecycleTransitionAnalyticsError("analytics_id is invalid.")
    if not isinstance(idempotency_key, str) or not IDEMPOTENCY_RE.fullmatch(idempotency_key):
        raise CreativeCodeLifecycleTransitionAnalyticsError("idempotency_key is invalid.")

    raw_corpus = _object(payload.get("corpus"), label="corpus")
    _exact_keys(raw_corpus, CORPUS_KEYS, label="corpus")
    corpus = {
        "events_fingerprint": _fingerprint(
            raw_corpus["events_fingerprint"], label="corpus.events_fingerprint"
        ),
        "rollup_fingerprint": _fingerprint(
            raw_corpus["rollup_fingerprint"], label="corpus.rollup_fingerprint"
        ),
        "event_count": _integer(
            raw_corpus["event_count"], label="corpus.event_count", maximum=MAX_EVENTS
        ),
        "legacy_event_count": _integer(
            raw_corpus["legacy_event_count"],
            label="corpus.legacy_event_count",
            maximum=MAX_EVENTS,
        ),
        "terminal_event_count": _integer(
            raw_corpus["terminal_event_count"],
            label="corpus.terminal_event_count",
            maximum=MAX_EVENTS,
        ),
        "terminal_cohort_observed": raw_corpus["terminal_cohort_observed"],
    }
    if not isinstance(corpus["terminal_cohort_observed"], bool):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "corpus.terminal_cohort_observed must be a boolean."
        )
    if corpus["event_count"] != (corpus["legacy_event_count"] + corpus["terminal_event_count"]):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "corpus event partitions are inconsistent."
        )
    if corpus["terminal_cohort_observed"] != (corpus["terminal_event_count"] > 0):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "terminal cohort observation flag is inconsistent."
        )

    raw_transitions = payload.get("transition_counts")
    if not isinstance(raw_transitions, list):
        raise CreativeCodeLifecycleTransitionAnalyticsError("transition_counts must be an array.")
    transitions: list[dict[str, Any]] = []
    seen_transitions: set[tuple[str, str, str, str]] = set()
    for index, raw_row in enumerate(raw_transitions):
        row = _object(raw_row, label=f"transition_counts[{index}]")
        _exact_keys(row, TRANSITION_KEYS, label=f"transition_counts[{index}]")
        from_stage = row.get("from_stage")
        from_status = row.get("from_status")
        to_stage = row.get("to_stage")
        to_status = row.get("to_status")
        if (
            not isinstance(from_stage, str)
            or not isinstance(from_status, str)
            or not isinstance(to_stage, str)
            or not isinstance(to_status, str)
        ):
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                "transition_counts stage and status values must be strings."
            )
        typed_transition: tuple[str, str, str, str] = (
            from_stage,
            from_status,
            to_stage,
            to_status,
        )
        if typed_transition not in ALLOWED_TRANSITIONS:
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                "transition_counts contains an unsupported transition."
            )
        if typed_transition in seen_transitions:
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                "transition_counts must not contain duplicates."
            )
        seen_transitions.add(typed_transition)
        count = _integer(row.get("count"), label=f"transition_counts[{index}].count")
        if count == 0:
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                "transition_counts rows must have positive counts."
            )
        transitions.append(
            {
                "from_stage": typed_transition[0],
                "from_status": typed_transition[1],
                "to_stage": typed_transition[2],
                "to_status": typed_transition[3],
                "count": count,
            }
        )
    if transitions != sorted(transitions, key=_transition_sort_key):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "transition_counts must use canonical order."
        )

    raw_lineage = _object(payload.get("lineage_accounting"), label="lineage_accounting")
    _exact_keys(raw_lineage, LINEAGE_KEYS, label="lineage_accounting")
    observed_transition_count = _integer(
        raw_lineage["observed_transition_count"],
        label="lineage_accounting.observed_transition_count",
    )
    complete_terminal_lineage_count = _integer(
        raw_lineage["complete_terminal_lineage_count"],
        label="lineage_accounting.complete_terminal_lineage_count",
    )
    incomplete_terminal_lineage_count = _integer(
        raw_lineage["incomplete_terminal_lineage_count"],
        label="lineage_accounting.incomplete_terminal_lineage_count",
    )
    unobserved_predecessors = _closed_stage_counts(
        raw_lineage["unobserved_predecessors_by_stage"],
        label="lineage_accounting.unobserved_predecessors_by_stage",
    )
    unobserved_successors = _closed_stage_counts(
        raw_lineage["unobserved_successors_by_stage"],
        label="lineage_accounting.unobserved_successors_by_stage",
    )
    lineage: dict[str, Any] = {
        "observed_transition_count": observed_transition_count,
        "complete_terminal_lineage_count": complete_terminal_lineage_count,
        "incomplete_terminal_lineage_count": incomplete_terminal_lineage_count,
        "unobserved_predecessors_by_stage": unobserved_predecessors,
        "unobserved_successors_by_stage": unobserved_successors,
    }
    if observed_transition_count != sum(cast(int, row["count"]) for row in transitions):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "observed transition count is inconsistent."
        )
    transition_counts_by_edge: Counter[tuple[str, str]] = Counter()
    for row in transitions:
        transition_counts_by_edge[
            (cast(str, row["from_stage"]), cast(str, row["to_stage"]))
        ] += cast(int, row["count"])
    if observed_transition_count > corpus["event_count"]:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "observed transition count exceeds the represented corpus."
        )
    if (
        complete_terminal_lineage_count + incomplete_terminal_lineage_count
        != corpus["terminal_event_count"]
    ):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "terminal lineage accounting is inconsistent."
        )
    terminal_incoming_count = transition_counts_by_edge[("pr_open", "pr_terminal")]
    if (
        terminal_incoming_count + unobserved_predecessors["pr_terminal"]
        != corpus["terminal_event_count"]
    ):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "terminal predecessor accounting is inconsistent."
        )
    for from_stage, to_stage in REQUIRED_COMPLETE_LINEAGE_EDGES:
        if complete_terminal_lineage_count > transition_counts_by_edge[(from_stage, to_stage)]:
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                "complete terminal lineage exceeds an observed required edge."
            )
    if (
        complete_terminal_lineage_count > 0
        and COMPLETE_LINEAGE_ROOT_TRANSITION not in seen_transitions
    ):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "complete terminal lineage requires an observed accepted specification edge."
        )
    if unobserved_predecessors["specification"] != 0:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "specification cannot have an unobserved predecessor."
        )
    if unobserved_successors["pr_terminal"] != 0:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "pr_terminal cannot have an unobserved successor."
        )
    for label, counts in (
        ("unobserved_predecessors_by_stage", unobserved_predecessors),
        ("unobserved_successors_by_stage", unobserved_successors),
    ):
        if sum(counts.values()) > corpus["event_count"]:
            raise CreativeCodeLifecycleTransitionAnalyticsError(
                f"{label} exceeds the represented corpus."
            )

    raw_histograms = _object(payload.get("cycle_histograms"), label="cycle_histograms")
    _exact_keys(raw_histograms, frozenset(PROCESS_KEYS), label="cycle_histograms")
    histograms = {
        key: _histogram(raw_histograms[key], label=f"cycle_histograms.{key}")
        for key in PROCESS_KEYS
    }
    if any(
        sum(histogram.values()) != corpus["terminal_event_count"]
        for histogram in histograms.values()
    ):
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "cycle histograms must account for every terminal event."
        )

    authority = payload.get("authority")
    if authority != default_authority():
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "authority must remain the closed read-only telemetry profile."
        )
    if payload.get("caveats") != CAVEATS:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "caveats must use the closed analytics vocabulary."
        )
    if payload.get("sanitized") is not True:
        raise CreativeCodeLifecycleTransitionAnalyticsError("sanitized must be true.")

    normalized: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "analytics_id": analytics_id,
        "idempotency_key": idempotency_key,
        "corpus": corpus,
        "transition_counts": transitions,
        "lineage_accounting": lineage,
        "cycle_histograms": histograms,
        "authority": default_authority(),
        "caveats": list(CAVEATS),
        "sanitized": True,
    }
    expected_analytics_id, expected_idempotency = _identity(normalized)
    if analytics_id != expected_analytics_id:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "analytics_id does not match artifact content."
        )
    if idempotency_key != expected_idempotency:
        raise CreativeCodeLifecycleTransitionAnalyticsError(
            "idempotency_key does not match artifact content."
        )
    reject_unsafe_telemetry_value(normalized, label="lifecycle transition analytics")
    return normalized


def canonical_analytics_bytes(payload: Mapping[str, Any]) -> bytes:
    normalized = validate_creative_code_lifecycle_transition_analytics(payload)
    return (
        json.dumps(
            normalized,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )

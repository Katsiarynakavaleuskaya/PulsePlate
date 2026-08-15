from __future__ import annotations

import ast
import copy
from dataclasses import replace
import errno
import inspect
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
from typing import Any, cast
from types import SimpleNamespace
import urllib.request

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_lifecycle_transition_analytics as cli
from scripts.orchestration import (
    creative_code_lifecycle_transition_analytics_contract as analytics_contract,
)
from scripts.orchestration import creative_code_telemetry_contract as telemetry_contract
from scripts.orchestration.creative_code_lifecycle_transition_analytics_contract import (
    ARTIFACT_TYPE,
    CAVEATS,
    CreativeCodeLifecycleTransitionAnalyticsError,
    build_creative_code_lifecycle_transition_analytics,
    canonical_analytics_bytes,
    validate_creative_code_lifecycle_transition_analytics,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    build_creative_code_telemetry_event,
    build_creative_code_telemetry_rollup_v2,
    default_authority,
    default_cost_metadata,
    default_metrics,
    validate_creative_code_telemetry_event_any,
)
from scripts.orchestration.creative_code_terminal_outcome_contract import terminal_outcome_id

SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "orchestration"
    / "contracts"
    / "creative_code_lifecycle_transition_analytics.v1.schema.json"
)
TELEMETRY_CONTRACT = SCHEMA.parent / "CREATIVE_CODE_TELEMETRY_CONTRACT.md"


def _ids(**values: str | None) -> dict[str, str | None]:
    return {key: values.get(key) for key in sorted(telemetry_contract.CANDIDATE_ID_KEYS)}


def _legacy_event(
    stage: str,
    *,
    status: str,
    source_bundle_id: str | None = None,
    selected_variant_id: str | None = None,
    request_id: str | None = None,
    result_id: str | None = None,
    promotion_id: str | None = None,
    source_packet_id: str | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    source_types = {
        "specification": "creative_code_specification",
        "patch_evaluation": "creative_code_patch_result",
        "promotion_plan": "creative_code_pr_promotion_plan",
        "promotion_validation": "creative_code_pr_promotion_validation",
        "promotion_approval": "creative_code_pr_promotion_approval",
        "pr_open": "creative_code_pr_promotion_receipt",
    }
    if source_id is None:
        source_id = {
            "specification": source_bundle_id,
            "patch_evaluation": result_id,
            "promotion_plan": promotion_id,
            "promotion_validation": promotion_id,
            "promotion_approval": f"approval-{promotion_id}",
            "pr_open": f"receipt-{promotion_id}",
        }[stage]
    assert source_id is not None
    event = build_creative_code_telemetry_event(
        lane_stage=stage,
        source_artifact_type=source_types[stage],
        source_artifact_id=source_id,
        source_fingerprint=fingerprint_payload(
            {"source_id": source_id, "stage": stage, "status": status}
        ),
        candidate_ids=_ids(
            source_packet_id=source_packet_id,
            source_bundle_id=source_bundle_id,
            selected_variant_id=selected_variant_id,
            request_id=request_id,
            result_id=result_id,
            promotion_id=promotion_id,
        ),
        status=status,
        metrics=default_metrics(),
    )
    return event


def _artifact_read_error_event() -> dict[str, Any]:
    return build_creative_code_telemetry_event(
        lane_stage="artifact_read_error",
        source_artifact_type="creative_code_artifact_read_error",
        source_artifact_id="read-error:analytics-test",
        source_fingerprint=fingerprint_payload({"read_error": "analytics-test"}),
        candidate_ids=_ids(),
        status="blocked",
        rejection_class="malformed_artifact",
        failure_class="malformed_artifact",
        taxonomy_codes=["malformed_artifact"],
        metrics=default_metrics(),
    )


def _terminal_event(
    promotion_id: str,
    *,
    status: str = "merged",
    number: int = 2200,
    process: dict[str, int] | None = None,
) -> dict[str, Any]:
    promoted_head_sha = f"{number % 16:x}" * 40
    projection = {
        "promotion_id": promotion_id,
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "pull_request_number": number,
        "promoted_head_sha": promoted_head_sha,
        "closure_epoch": 1,
        "review_observation": "no_actionables_observed",
        "governance_observation": "no_blockers_observed",
        "post_merge_observation": ("complete_observed" if status == "merged" else "not_applicable"),
    }
    event: dict[str, Any] = {
        "schema_version": telemetry_contract.V2_SCHEMA_VERSION,
        "artifact_type": telemetry_contract.EVENT_TYPE,
        "policy_version": telemetry_contract.V2_POLICY_VERSION,
        "event_id": "pending",
        "idempotency_key": "pending",
        "lane_stage": "pr_terminal",
        "source_artifact_type": "creative_code_terminal_outcome",
        "source_artifact_id": terminal_outcome_id(
            repository=projection["repository"],
            pull_request_number=number,
            promotion_id=promotion_id,
            promoted_head_sha=promoted_head_sha,
        ),
        "source_fingerprint": fingerprint_payload(
            {"promotion_id": promotion_id, "number": number, "status": status}
        ),
        "status": status,
        "terminal_projection": projection,
        "process": process or {"review_cycles": 0, "repair_cycles": 0, "validation_attempts": 0},
        "cost_metadata": default_cost_metadata(),
        "authority": default_authority(),
        "sanitized": True,
    }
    event_id, idempotency_key = telemetry_contract._v2_event_identity(event)
    event["event_id"] = event_id
    event["idempotency_key"] = idempotency_key
    return validate_creative_code_telemetry_event_any(event)


def _full_chain(
    prefix: str = "one",
    *,
    terminal_status: str = "merged",
    process: dict[str, int] | None = None,
    number: int = 2200,
) -> list[dict[str, Any]]:
    bundle = f"bundle-{prefix}"
    variant = f"variant-{prefix}"
    request = f"request-{prefix}"
    result = f"result-{prefix}"
    promotion = f"promotion-{prefix}"
    return [
        _legacy_event(
            "specification",
            status="accepted",
            source_packet_id=f"packet-{prefix}",
            source_bundle_id=bundle,
            selected_variant_id=variant,
        ),
        _legacy_event(
            "patch_evaluation",
            status="accepted",
            source_bundle_id=bundle,
            selected_variant_id=variant,
            request_id=request,
            result_id=result,
        ),
        _legacy_event(
            "promotion_plan",
            status="accepted",
            source_bundle_id=bundle,
            selected_variant_id=variant,
            request_id=request,
            result_id=result,
            promotion_id=promotion,
        ),
        _legacy_event("promotion_validation", status="accepted", promotion_id=promotion),
        _legacy_event("promotion_approval", status="accepted", promotion_id=promotion),
        _legacy_event(
            "pr_open",
            status="opened",
            result_id=result,
            promotion_id=promotion,
        ),
        _terminal_event(
            promotion,
            status=terminal_status,
            number=number,
            process=process,
        ),
    ]


def _rollup(events: list[dict[str, Any]]) -> dict[str, Any]:
    return build_creative_code_telemetry_rollup_v2(
        events,
        input_roots=["patch_runs", "promotions", "spec_runs", "terminal_outcomes"],
    )


def _analytics(events: list[dict[str, Any]]) -> dict[str, Any]:
    return build_creative_code_lifecycle_transition_analytics(
        events, telemetry_rollup=_rollup(events)
    )


def _reidentify_artifact(payload: dict[str, Any]) -> None:
    analytics_id, idempotency_key = analytics_contract._identity(payload)
    payload["analytics_id"] = analytics_id
    payload["idempotency_key"] = idempotency_key


def test_full_merged_chain_emits_six_adjacent_edges_and_one_complete_lineage() -> None:
    artifact = _analytics(_full_chain())

    assert artifact["corpus"] == {
        "event_count": 7,
        "events_fingerprint": artifact["corpus"]["events_fingerprint"],
        "legacy_event_count": 6,
        "rollup_fingerprint": artifact["corpus"]["rollup_fingerprint"],
        "terminal_cohort_observed": True,
        "terminal_event_count": 1,
    }
    assert len(artifact["transition_counts"]) == 6
    assert all(row["count"] == 1 for row in artifact["transition_counts"])
    assert artifact["lineage_accounting"]["observed_transition_count"] == 6
    assert artifact["lineage_accounting"]["complete_terminal_lineage_count"] == 1
    assert artifact["lineage_accounting"]["incomplete_terminal_lineage_count"] == 0
    assert all(
        count == 0
        for counts in (
            artifact["lineage_accounting"]["unobserved_predecessors_by_stage"],
            artifact["lineage_accounting"]["unobserved_successors_by_stage"],
        )
        for count in counts.values()
    )


def test_reidentified_full_chain_cannot_understate_complete_terminal_lineage() -> None:
    genuine = _analytics(_full_chain())
    lineage = genuine["lineage_accounting"]
    assert len(genuine["transition_counts"]) == 6
    assert genuine["corpus"]["terminal_event_count"] == 1
    assert lineage["complete_terminal_lineage_count"] == 1
    assert all(
        lineage["unobserved_predecessors_by_stage"][stage] == 0
        for stage in analytics_contract.STAGES[1:]
    )
    fingerprints = (
        genuine["corpus"]["events_fingerprint"],
        genuine["corpus"]["rollup_fingerprint"],
    )

    forged = copy.deepcopy(genuine)
    forged["lineage_accounting"]["complete_terminal_lineage_count"] = 0
    forged["lineage_accounting"]["incomplete_terminal_lineage_count"] = 1
    assert (
        forged["corpus"]["events_fingerprint"],
        forged["corpus"]["rollup_fingerprint"],
    ) == fingerprints
    _reidentify_artifact(forged)

    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError) as rejection:
        validate_creative_code_lifecycle_transition_analytics(forged)
    assert str(rejection.value) == (
        "complete terminal lineage count is below the forced root-connected minimum."
    )


@pytest.mark.parametrize("orphan_stop", ["rejected_patch", "blocked_pr_open"])
def test_reidentified_root_connected_terminal_cannot_hide_behind_orphan_stop(
    orphan_stop: str,
) -> None:
    events = _full_chain()
    if orphan_stop == "rejected_patch":
        stage = "patch_evaluation"
        events.append(
            _legacy_event(
                stage,
                status="rejected",
                source_bundle_id="bundle-orphan-rejected",
                selected_variant_id="variant-orphan-rejected",
                request_id="request-orphan-rejected",
                result_id="result-orphan-rejected",
            )
        )
    else:
        stage = "pr_open"
        events.append(
            _legacy_event(
                stage,
                status="blocked",
                result_id="result-orphan-blocked",
                promotion_id="promotion-orphan-blocked",
            )
        )

    genuine = _analytics(events)
    lineage = genuine["lineage_accounting"]
    assert lineage["unobserved_predecessors_by_stage"][stage] == 1
    assert lineage["unobserved_successors_by_stage"][stage] == 0
    assert genuine["corpus"]["terminal_event_count"] == 1
    assert lineage["complete_terminal_lineage_count"] == 1
    fingerprints = (
        genuine["corpus"]["events_fingerprint"],
        genuine["corpus"]["rollup_fingerprint"],
    )

    forged = copy.deepcopy(genuine)
    forged["lineage_accounting"]["complete_terminal_lineage_count"] = 0
    forged["lineage_accounting"]["incomplete_terminal_lineage_count"] = 1
    assert (
        forged["corpus"]["events_fingerprint"],
        forged["corpus"]["rollup_fingerprint"],
    ) == fingerprints
    _reidentify_artifact(forged)

    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError) as rejection:
        validate_creative_code_lifecycle_transition_analytics(forged)
    assert str(rejection.value) == (
        "complete terminal lineage count is below the forced root-connected minimum."
    )


def test_rejected_patch_is_an_observed_stop_without_fabricated_continuation() -> None:
    chain = _full_chain()[:2]
    chain[1] = _legacy_event(
        "patch_evaluation",
        status="rejected",
        source_bundle_id="bundle-one",
        selected_variant_id="variant-one",
        request_id="request-rejected",
        result_id="result-rejected",
    )
    artifact = _analytics(chain)

    assert artifact["transition_counts"] == [
        {
            "from_stage": "specification",
            "from_status": "accepted",
            "to_stage": "patch_evaluation",
            "to_status": "rejected",
            "count": 1,
        }
    ]
    assert artifact["lineage_accounting"]["unobserved_successors_by_stage"]["patch_evaluation"] == 0


def test_rejected_specification_without_selected_variant_is_a_valid_stop() -> None:
    rejected = _legacy_event(
        "specification",
        status="rejected",
        source_packet_id="packet-rejected",
        source_bundle_id="bundle-rejected",
    )

    artifact = _analytics([rejected])

    assert artifact["transition_counts"] == []
    assert artifact["lineage_accounting"]["unobserved_successors_by_stage"]["specification"] == 0


def test_multiple_patch_attempts_and_promotion_attempts_count_destinations() -> None:
    specification = _full_chain()[:1]
    patch_one = _legacy_event(
        "patch_evaluation",
        status="accepted",
        source_bundle_id="bundle-one",
        selected_variant_id="variant-one",
        request_id="request-a",
        result_id="result-a",
    )
    patch_two = _legacy_event(
        "patch_evaluation",
        status="rejected",
        source_bundle_id="bundle-one",
        selected_variant_id="variant-one",
        request_id="request-b",
        result_id="result-b",
    )
    plan_one = _legacy_event(
        "promotion_plan",
        status="accepted",
        source_bundle_id="bundle-one",
        selected_variant_id="variant-one",
        request_id="request-a",
        result_id="result-a",
        promotion_id="promotion-a",
    )
    plan_two = _legacy_event(
        "promotion_plan",
        status="accepted",
        source_bundle_id="bundle-one",
        selected_variant_id="variant-one",
        request_id="request-a",
        result_id="result-a",
        promotion_id="promotion-b",
    )

    events = [*specification, patch_one, patch_two, plan_one, plan_two]
    artifact = _analytics(events)
    permuted = _analytics([plan_two, patch_two, *specification, plan_one, patch_one])
    counts = {
        (row["from_stage"], row["to_stage"], row["to_status"]): row["count"]
        for row in artifact["transition_counts"]
    }
    assert counts[("specification", "patch_evaluation", "accepted")] == 1
    assert counts[("specification", "patch_evaluation", "rejected")] == 1
    assert counts[("patch_evaluation", "promotion_plan", "accepted")] == 2
    assert artifact == permuted
    assert canonical_analytics_bytes(artifact) == canonical_analytics_bytes(permuted)


def test_two_complete_terminals_may_share_one_observed_specification_patch_edge() -> None:
    specification = _legacy_event(
        "specification",
        status="accepted",
        source_packet_id="packet-shared",
        source_bundle_id="bundle-shared",
        selected_variant_id="variant-shared",
    )
    shared_patch = _legacy_event(
        "patch_evaluation",
        status="accepted",
        source_bundle_id="bundle-shared",
        selected_variant_id="variant-shared",
        request_id="request-shared",
        result_id="result-shared",
    )
    unobserved_patch = _legacy_event(
        "patch_evaluation",
        status="accepted",
        source_bundle_id="bundle-unobserved",
        selected_variant_id="variant-unobserved",
        request_id="request-unobserved",
        result_id="result-unobserved",
    )
    events = [specification, shared_patch, unobserved_patch]
    for index, suffix in enumerate(("a", "b"), start=1):
        promotion_id = f"promotion-shared-{suffix}"
        events.extend(
            [
                _legacy_event(
                    "promotion_plan",
                    status="accepted",
                    source_bundle_id="bundle-shared",
                    selected_variant_id="variant-shared",
                    request_id="request-shared",
                    result_id="result-shared",
                    promotion_id=promotion_id,
                ),
                _legacy_event("promotion_validation", status="accepted", promotion_id=promotion_id),
                _legacy_event("promotion_approval", status="accepted", promotion_id=promotion_id),
                _legacy_event(
                    "pr_open",
                    status="opened",
                    result_id="result-shared",
                    promotion_id=promotion_id,
                ),
                _terminal_event(promotion_id, number=2400 + index),
            ]
        )

    rollup = _rollup(events)
    assert rollup["rates"]["promotion_rate_bps"] == 10_000
    artifact = build_creative_code_lifecycle_transition_analytics(events, telemetry_rollup=rollup)
    counts_by_edge = {
        (row["from_stage"], row["to_stage"]): row["count"] for row in artifact["transition_counts"]
    }

    assert artifact["lineage_accounting"]["complete_terminal_lineage_count"] == 2
    assert counts_by_edge[("specification", "patch_evaluation")] == 1
    for edge in zip(analytics_contract.STAGES[1:], analytics_contract.STAGES[2:]):
        assert counts_by_edge[edge] == 2
    assert (
        artifact["lineage_accounting"]["unobserved_predecessors_by_stage"]["patch_evaluation"] == 1
    )


def test_blocked_pr_is_an_observed_stop_and_closed_unmerged_is_observed() -> None:
    blocked = _full_chain()[:-2]
    blocked.append(
        _legacy_event(
            "pr_open",
            status="blocked",
            result_id="result-one",
            promotion_id="promotion-one",
        )
    )
    blocked_artifact = _analytics(blocked)
    assert blocked_artifact["transition_counts"][-1]["to_status"] == "blocked"
    assert blocked_artifact["lineage_accounting"]["unobserved_successors_by_stage"]["pr_open"] == 0

    closed_artifact = _analytics(_full_chain(terminal_status="closed_unmerged"))
    assert closed_artifact["transition_counts"][-1]["to_status"] == "closed_unmerged"
    assert closed_artifact["lineage_accounting"]["complete_terminal_lineage_count"] == 1


def test_partial_and_missing_intermediate_corpora_do_not_fabricate_skip_edges() -> None:
    terminal = _terminal_event("promotion-terminal-only")
    terminal_only = _analytics([terminal])
    assert terminal_only["transition_counts"] == []
    assert terminal_only["lineage_accounting"]["incomplete_terminal_lineage_count"] == 1
    assert (
        terminal_only["lineage_accounting"]["unobserved_predecessors_by_stage"]["pr_terminal"] == 1
    )

    specification = _full_chain()[:1]
    plan = _full_chain()[2]
    gapped = _analytics([*specification, plan])
    assert gapped["transition_counts"] == []
    assert gapped["lineage_accounting"]["unobserved_successors_by_stage"]["specification"] == 1
    assert gapped["lineage_accounting"]["unobserved_predecessors_by_stage"]["promotion_plan"] == 1


def test_incompatible_status_duplicate_promotion_stage_and_stale_rollup_fail_closed() -> None:
    rejected_spec = _legacy_event(
        "specification",
        status="rejected",
        source_packet_id="packet-x",
        source_bundle_id="bundle-x",
        selected_variant_id="variant-x",
    )
    patch = _legacy_event(
        "patch_evaluation",
        status="accepted",
        source_bundle_id="bundle-x",
        selected_variant_id="variant-x",
        request_id="request-x",
        result_id="result-x",
    )
    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError, match="incompatible"):
        _analytics([rejected_spec, patch])

    duplicate_approvals = [
        _legacy_event(
            "promotion_approval",
            status="accepted",
            promotion_id="promotion-duplicate",
            source_id="approval-one",
        ),
        _legacy_event(
            "promotion_approval",
            status="accepted",
            promotion_id="promotion-duplicate",
            source_id="approval-two",
        ),
    ]
    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError, match="duplicate promotion-stage"
    ):
        _analytics(duplicate_approvals)

    full = _full_chain()
    stale_rollup = _rollup(full[:-1])
    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError, match="exact event snapshot"):
        build_creative_code_lifecycle_transition_analytics(full, telemetry_rollup=stale_rollup)


def test_source_drift_and_noncanonical_event_profiles_fail_closed() -> None:
    event = _full_chain()[0]
    changed = copy.deepcopy(event)
    changed["source_fingerprint"] = fingerprint_payload({"changed": True})
    changed_id, changed_key = telemetry_contract._event_identity(changed)
    changed["event_id"] = changed_id
    changed["idempotency_key"] = changed_key
    with pytest.raises(telemetry_contract.CreativeCodeTelemetryContractError, match="drift"):
        _analytics([event, changed])

    wrong_profile = _legacy_event(
        "promotion_approval",
        status="accepted",
        promotion_id="promotion-wrong-profile",
        source_id="approval-wrong-profile",
    )
    wrong_profile["candidate_ids"]["result_id"] = "unexpected-result"
    event_id, key = telemetry_contract._event_identity(wrong_profile)
    wrong_profile["event_id"] = event_id
    wrong_profile["idempotency_key"] = key
    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError, match="unsupported lineage"):
        _analytics([wrong_profile])


def test_artifact_read_error_remains_rollup_only_and_not_a_lifecycle_node() -> None:
    artifact = _analytics([_artifact_read_error_event()])

    assert artifact["corpus"]["legacy_event_count"] == 1
    assert artifact["transition_counts"] == []
    assert artifact["lineage_accounting"]["observed_transition_count"] == 0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("source_profile", "source/stage profile"),
        ("status_profile", "status/stage profile"),
        ("required_candidate", "candidate profile is incomplete"),
        ("accepted_spec_variant", "requires selected variant"),
        ("spec_source", "specification source identity"),
        ("patch_source", "patch source identity"),
        ("promotion_source", "promotion source identity"),
    ],
)
def test_closed_candidate_profile_defenses_reject_each_invalid_shape(
    mutation: str,
    message: str,
) -> None:
    if mutation in {"source_profile", "status_profile", "accepted_spec_variant", "spec_source"}:
        event = copy.deepcopy(_full_chain()[0])
    elif mutation in {"required_candidate", "patch_source"}:
        event = copy.deepcopy(_full_chain()[1])
    else:
        event = copy.deepcopy(_full_chain()[2])

    if mutation == "source_profile":
        event["source_artifact_type"] = "creative_code_patch_result"
    elif mutation == "status_profile":
        event["status"] = "blocked"
    elif mutation == "required_candidate":
        event["candidate_ids"]["request_id"] = None
    elif mutation == "accepted_spec_variant":
        event["candidate_ids"]["selected_variant_id"] = None
    elif mutation == "spec_source":
        event["source_artifact_id"] = "bundle-other"
    elif mutation == "patch_source":
        event["source_artifact_id"] = "result-other"
    else:
        event["source_artifact_id"] = "promotion-other"

    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError, match=message):
        analytics_contract._require_candidate_profile(event)


def test_join_defenses_reject_missing_promotion_and_ambiguous_predecessors() -> None:
    promotion = copy.deepcopy(_full_chain()[4])
    promotion["candidate_ids"]["promotion_id"] = None
    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError, match="missing promotion"):
        analytics_contract._promotion_id(promotion)

    accepted_specification = copy.deepcopy(_full_chain()[0])
    accepted_specification["candidate_ids"]["selected_variant_id"] = None
    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError, match="missing required adjacent-stage"
    ):
        analytics_contract._derive_transitions([accepted_specification])

    first = copy.deepcopy(_full_chain()[0])
    second = copy.deepcopy(first)
    second["event_id"] = "synthetic-distinct-event-id"
    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError, match="ambiguous adjacent-stage"
    ):
        analytics_contract._derive_transitions([first, second])


def test_duplicate_event_id_and_same_fingerprint_source_lineage_fail_closed() -> None:
    event = _full_chain()[0]
    with pytest.raises(
        telemetry_contract.CreativeCodeTelemetryContractError,
        match="duplicate telemetry event_id",
    ):
        build_creative_code_lifecycle_transition_analytics(
            [event, event], telemetry_rollup=_rollup([event])
        )

    first = _legacy_event(
        "specification",
        status="accepted",
        source_packet_id="packet-duplicate-source",
        source_bundle_id="bundle-duplicate-source",
        selected_variant_id="variant-a",
    )
    second = _legacy_event(
        "specification",
        status="accepted",
        source_packet_id="packet-duplicate-source",
        source_bundle_id="bundle-duplicate-source",
        selected_variant_id="variant-b",
    )
    assert first["event_id"] != second["event_id"]
    assert first["source_fingerprint"] == second["source_fingerprint"]
    with pytest.raises(
        telemetry_contract.CreativeCodeTelemetryContractError,
        match="duplicate telemetry source lineage",
    ):
        build_creative_code_lifecycle_transition_analytics(
            [first, second], telemetry_rollup=_rollup([first])
        )


def test_input_order_does_not_change_payload_identity_or_bytes() -> None:
    events = _full_chain()
    forward = _analytics(events)
    reverse = _analytics(list(reversed(events)))

    assert forward == reverse
    assert canonical_analytics_bytes(forward) == canonical_analytics_bytes(reverse)


def test_cycle_histograms_use_fixed_buckets_and_zero_corpus_is_valid() -> None:
    events: list[dict[str, Any]] = []
    for value in range(4):
        events.append(
            _terminal_event(
                f"promotion-histogram-{value}",
                number=2300 + value,
                process={
                    "review_cycles": value,
                    "repair_cycles": value,
                    "validation_attempts": value,
                },
            )
        )
    maximum = telemetry_contract.V2_PROCESS_EVENT_MAX
    events.append(
        _terminal_event(
            "promotion-histogram-maximum",
            number=2310,
            process={
                "review_cycles": maximum,
                "repair_cycles": maximum,
                "validation_attempts": maximum,
            },
        )
    )
    artifact = _analytics(events)
    expected = {"0": 1, "1": 1, "2": 1, "3_or_more": 2}
    assert artifact["cycle_histograms"] == {
        "repair_cycles": expected,
        "review_cycles": expected,
        "validation_attempts": expected,
    }

    empty = _analytics([])
    assert empty["corpus"]["terminal_cohort_observed"] is False
    assert empty["transition_counts"] == []
    assert all(sum(histogram.values()) == 0 for histogram in empty["cycle_histograms"].values())


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("complete_without_edges", "complete terminal lineage exceeds"),
        ("missing_terminal_predecessor_accounting", "terminal predecessor accounting"),
    ],
)
def test_reidentified_terminal_only_artifact_cannot_forge_lineage_accounting(
    mutation: str,
    message: str,
) -> None:
    forged = copy.deepcopy(_analytics([_terminal_event("promotion-terminal-forgery")]))
    if mutation == "complete_without_edges":
        forged["lineage_accounting"]["complete_terminal_lineage_count"] = 1
        forged["lineage_accounting"]["incomplete_terminal_lineage_count"] = 0
    else:
        forged["lineage_accounting"]["unobserved_predecessors_by_stage"]["pr_terminal"] = 0
    analytics_id, idempotency_key = analytics_contract._identity(forged)
    forged["analytics_id"] = analytics_id
    forged["idempotency_key"] = idempotency_key

    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError, match=message):
        validate_creative_code_lifecycle_transition_analytics(forged)


def test_reidentified_complete_lineage_requires_one_observed_accepted_specification_edge() -> None:
    forged = copy.deepcopy(_analytics(_full_chain()))
    root_index = next(
        index
        for index, row in enumerate(forged["transition_counts"])
        if (
            row["from_stage"],
            row["from_status"],
            row["to_stage"],
            row["to_status"],
        )
        == analytics_contract.COMPLETE_LINEAGE_ROOT_TRANSITION
    )
    removed = forged["transition_counts"].pop(root_index)
    forged["lineage_accounting"]["observed_transition_count"] -= removed["count"]
    _reidentify_artifact(forged)

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match="requires an observed accepted specification edge",
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


def test_reidentified_one_event_corpus_cannot_claim_one_adjacent_transition() -> None:
    specification = _legacy_event(
        "specification",
        status="accepted",
        source_packet_id="packet-one-event",
        source_bundle_id="bundle-one-event",
        selected_variant_id="variant-one-event",
    )
    forged = copy.deepcopy(_analytics([specification]))
    forged["transition_counts"] = [
        {
            "from_stage": "specification",
            "from_status": "accepted",
            "to_stage": "patch_evaluation",
            "to_status": "accepted",
            "count": 1,
        }
    ]
    forged["lineage_accounting"]["observed_transition_count"] = 1
    forged["lineage_accounting"]["unobserved_successors_by_stage"]["specification"] = 0
    _reidentify_artifact(forged)

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match="minimum represented lifecycle node accounting exceeds",
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


def test_reidentified_disjoint_edges_cannot_hide_sources_in_unrelated_events() -> None:
    events = [
        _legacy_event(
            "specification",
            status="accepted",
            source_packet_id="packet-disjoint-a",
            source_bundle_id="bundle-disjoint-a",
            selected_variant_id="variant-disjoint-a",
        ),
        _legacy_event(
            "specification",
            status="accepted",
            source_packet_id="packet-disjoint-b",
            source_bundle_id="bundle-disjoint-b",
            selected_variant_id="variant-disjoint-b",
        ),
        _artifact_read_error_event(),
    ]
    forged = copy.deepcopy(_analytics(events))
    forged["transition_counts"] = [
        {
            "from_stage": "specification",
            "from_status": "accepted",
            "to_stage": "patch_evaluation",
            "to_status": "accepted",
            "count": 1,
        },
        {
            "from_stage": "promotion_plan",
            "from_status": "accepted",
            "to_stage": "promotion_validation",
            "to_status": "accepted",
            "count": 1,
        },
    ]
    forged["lineage_accounting"]["observed_transition_count"] = 2
    forged["lineage_accounting"]["unobserved_successors_by_stage"]["specification"] = 1
    _reidentify_artifact(forged)

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match="minimum represented lifecycle node accounting exceeds",
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


@pytest.mark.parametrize(
    ("stage", "message"),
    [
        ("promotion_plan", "one-to-one continuation accounting is not representable"),
        ("pr_open", "pr_open continuation accounting is not representable"),
    ],
)
def test_reidentified_one_to_one_edges_require_distinct_represented_sources(
    stage: str,
    message: str,
) -> None:
    if stage == "promotion_plan":
        promotion_a = "promotion-one-to-one-plan-a"
        promotion_b = "promotion-one-to-one-plan-b"
        events = [
            _legacy_event(
                "promotion_plan",
                status="accepted",
                source_bundle_id="bundle-one-to-one-plan",
                selected_variant_id="variant-one-to-one-plan",
                request_id="request-one-to-one-plan",
                result_id="result-one-to-one-plan",
                promotion_id=promotion_a,
            ),
            _legacy_event("promotion_validation", status="accepted", promotion_id=promotion_a),
            _legacy_event("promotion_validation", status="accepted", promotion_id=promotion_b),
        ]
        destination_stage = "promotion_validation"
    else:
        promotion_a = "promotion-one-to-one-open-a"
        promotion_b = "promotion-one-to-one-open-b"
        events = [
            _legacy_event(
                "pr_open",
                status="opened",
                result_id="result-one-to-one-open",
                promotion_id=promotion_a,
            ),
            _terminal_event(promotion_a, number=2710),
            _terminal_event(promotion_b, number=2711),
        ]
        destination_stage = "pr_terminal"

    forged = copy.deepcopy(_analytics(events))
    row = next(
        row
        for row in forged["transition_counts"]
        if row["from_stage"] == stage and row["to_stage"] == destination_stage
    )
    row["count"] = 2
    forged["lineage_accounting"]["observed_transition_count"] += 1
    forged["lineage_accounting"]["unobserved_predecessors_by_stage"][destination_stage] -= 1
    _reidentify_artifact(forged)

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match=message,
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


@pytest.mark.parametrize(
    "stage",
    ["promotion_plan", "promotion_validation", "promotion_approval"],
)
def test_reidentified_isolated_one_to_one_stage_requires_its_missing_successor(
    stage: str,
) -> None:
    promotion_id = f"promotion-isolated-{stage}"
    if stage == "promotion_plan":
        event = _legacy_event(
            stage,
            status="accepted",
            source_bundle_id="bundle-isolated-plan",
            selected_variant_id="variant-isolated-plan",
            request_id="request-isolated-plan",
            result_id="result-isolated-plan",
            promotion_id=promotion_id,
        )
    else:
        event = _legacy_event(stage, status="accepted", promotion_id=promotion_id)

    artifact = _analytics([event])
    assert artifact["lineage_accounting"]["unobserved_predecessors_by_stage"][stage] == 1
    assert artifact["lineage_accounting"]["unobserved_successors_by_stage"][stage] == 1
    assert validate_creative_code_lifecycle_transition_analytics(artifact) == artifact

    forged = copy.deepcopy(artifact)
    corpus = copy.deepcopy(forged["corpus"])
    forged["lineage_accounting"]["unobserved_successors_by_stage"][stage] = 0
    _reidentify_artifact(forged)
    assert forged["corpus"] == corpus

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match="one-to-one continuation accounting is not representable",
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


def test_reidentified_observed_accepted_patch_requires_one_missing_successor() -> None:
    specification = _legacy_event(
        "specification",
        status="accepted",
        source_packet_id="packet-patch-undercount",
        source_bundle_id="bundle-patch-undercount",
        selected_variant_id="variant-patch-undercount",
    )
    patch = _legacy_event(
        "patch_evaluation",
        status="accepted",
        source_bundle_id="bundle-patch-undercount",
        selected_variant_id="variant-patch-undercount",
        request_id="request-patch-undercount",
        result_id="result-patch-undercount",
    )
    artifact = _analytics([specification, patch])
    assert artifact["lineage_accounting"]["unobserved_successors_by_stage"]["patch_evaluation"] == 1
    assert validate_creative_code_lifecycle_transition_analytics(artifact) == artifact

    forged = copy.deepcopy(artifact)
    corpus = copy.deepcopy(forged["corpus"])
    forged["lineage_accounting"]["unobserved_successors_by_stage"]["patch_evaluation"] = 0
    _reidentify_artifact(forged)
    assert forged["corpus"] == corpus

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match="patch continuation accounting is not representable",
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


@pytest.mark.parametrize(("status", "missing_successor"), [("accepted", 1), ("rejected", 0)])
def test_orphan_patch_preserves_status_specific_missing_successor_semantics(
    status: str,
    missing_successor: int,
) -> None:
    patch = _legacy_event(
        "patch_evaluation",
        status=status,
        source_bundle_id=f"bundle-orphan-patch-{status}",
        selected_variant_id=f"variant-orphan-patch-{status}",
        request_id=f"request-orphan-patch-{status}",
        result_id=f"result-orphan-patch-{status}",
    )
    artifact = _analytics([patch])

    assert (
        artifact["lineage_accounting"]["unobserved_predecessors_by_stage"]["patch_evaluation"] == 1
    )
    assert (
        artifact["lineage_accounting"]["unobserved_successors_by_stage"]["patch_evaluation"]
        == missing_successor
    )
    assert validate_creative_code_lifecycle_transition_analytics(artifact) == artifact


def test_reidentified_known_open_pr_requires_one_continuation_outcome() -> None:
    promotion_id = "promotion-known-open-undercount"
    approval = _legacy_event("promotion_approval", status="accepted", promotion_id=promotion_id)
    opened = _legacy_event(
        "pr_open",
        status="opened",
        result_id="result-known-open-undercount",
        promotion_id=promotion_id,
    )
    artifact = _analytics([approval, opened])
    assert artifact["lineage_accounting"]["unobserved_predecessors_by_stage"]["pr_open"] == 0
    assert artifact["lineage_accounting"]["unobserved_successors_by_stage"]["pr_open"] == 1
    assert validate_creative_code_lifecycle_transition_analytics(artifact) == artifact

    forged = copy.deepcopy(artifact)
    corpus = copy.deepcopy(forged["corpus"])
    forged["lineage_accounting"]["unobserved_successors_by_stage"]["pr_open"] = 0
    _reidentify_artifact(forged)
    assert forged["corpus"] == corpus

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match="pr_open continuation accounting is not representable",
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


@pytest.mark.parametrize(("status", "missing_successor"), [("blocked", 0), ("opened", 1)])
def test_orphan_pr_open_preserves_status_specific_missing_successor_semantics(
    status: str,
    missing_successor: int,
) -> None:
    opened_or_blocked = _legacy_event(
        "pr_open",
        status=status,
        result_id=f"result-orphan-pr-{status}",
        promotion_id=f"promotion-orphan-pr-{status}",
    )
    artifact = _analytics([opened_or_blocked])

    assert artifact["lineage_accounting"]["unobserved_predecessors_by_stage"]["pr_open"] == 1
    assert (
        artifact["lineage_accounting"]["unobserved_successors_by_stage"]["pr_open"]
        == missing_successor
    )
    assert validate_creative_code_lifecycle_transition_analytics(artifact) == artifact


def test_reidentified_orphan_open_pr_rejects_successor_overflow() -> None:
    opened = _legacy_event(
        "pr_open",
        status="opened",
        result_id="result-orphan-pr-overflow",
        promotion_id="promotion-orphan-pr-overflow",
    )
    artifact = _analytics([opened])
    forged = copy.deepcopy(artifact)
    corpus = copy.deepcopy(forged["corpus"])
    forged["lineage_accounting"]["unobserved_successors_by_stage"]["pr_open"] = 2
    _reidentify_artifact(forged)
    assert forged["corpus"] == corpus

    with pytest.raises(
        CreativeCodeLifecycleTransitionAnalyticsError,
        match="pr_open continuation accounting is not representable",
    ):
        validate_creative_code_lifecycle_transition_analytics(forged)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_key",
        "wrong_scalar_type",
        "negative_count",
        "bad_arithmetic",
        "unsorted_transitions",
        "duplicate_transition",
        "forged_identity",
    ],
)
def test_python_validator_rejects_closed_shape_arithmetic_and_identity_forgery(
    mutation: str,
) -> None:
    artifact = _analytics(_full_chain())
    forged = copy.deepcopy(artifact)
    if mutation == "unknown_key":
        forged["unexpected"] = True
    elif mutation == "wrong_scalar_type":
        forged["transition_counts"][0]["count"] = "1"
    elif mutation == "negative_count":
        forged["transition_counts"][0]["count"] = -1
    elif mutation == "bad_arithmetic":
        forged["lineage_accounting"]["observed_transition_count"] += 1
    elif mutation == "unsorted_transitions":
        forged["transition_counts"].reverse()
    elif mutation == "duplicate_transition":
        forged["transition_counts"].append(copy.deepcopy(forged["transition_counts"][0]))
    else:
        replacement = "0" if forged["analytics_id"][-1] != "0" else "1"
        forged["analytics_id"] = forged["analytics_id"][:-1] + replacement

    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError):
        validate_creative_code_lifecycle_transition_analytics(forged)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("schema_version", "schema_version"),
        ("artifact_type", "artifact_type"),
        ("policy_version", "policy_version"),
        ("analytics_id_type", "analytics_id"),
        ("idempotency_format", "idempotency_key"),
        ("corpus_object", "corpus must be an object"),
        ("fingerprint", "canonical SHA-256"),
        ("terminal_flag_type", "must be a boolean"),
        ("corpus_partition", "event partitions"),
        ("cohort_flag", "observation flag"),
        ("transitions_type", "must be an array"),
        ("transition_object", "must be an object"),
        ("transition_stage_type", "must be strings"),
        ("unsupported_transition", "unsupported transition"),
        ("zero_transition", "positive counts"),
        ("observed_exceeds", "exceeds the represented corpus"),
        ("lineage_partition", "terminal lineage accounting"),
        ("spec_predecessor", "specification cannot"),
        ("terminal_successor", "pr_terminal cannot"),
        ("unobserved_overflow", "exceeds the represented corpus"),
        ("histogram_sum", "histograms must account"),
        ("authority", "authority must remain"),
        ("caveats", "closed analytics vocabulary"),
        ("sanitized", "sanitized must be true"),
        ("idempotency_mismatch", "does not match artifact content"),
    ],
)
def test_python_validator_rejects_scalar_shape_and_reidentified_semantic_forgeries(
    mutation: str,
    message: str,
) -> None:
    forged = copy.deepcopy(_analytics(_full_chain()))
    reidentify = False
    if mutation == "schema_version":
        forged["schema_version"] = "2.0"
    elif mutation == "artifact_type":
        forged["artifact_type"] = "other"
    elif mutation == "policy_version":
        forged["policy_version"] = "other"
    elif mutation == "analytics_id_type":
        forged["analytics_id"] = 1
    elif mutation == "idempotency_format":
        forged["idempotency_key"] = "invalid"
    elif mutation == "corpus_object":
        forged["corpus"] = []
    elif mutation == "fingerprint":
        forged["corpus"]["events_fingerprint"] = "sha256:invalid"
    elif mutation == "terminal_flag_type":
        forged["corpus"]["terminal_cohort_observed"] = 1
    elif mutation == "corpus_partition":
        forged["corpus"]["event_count"] += 1
    elif mutation == "cohort_flag":
        forged["corpus"]["terminal_cohort_observed"] = False
    elif mutation == "transitions_type":
        forged["transition_counts"] = {}
    elif mutation == "transition_object":
        forged["transition_counts"][0] = []
    elif mutation == "transition_stage_type":
        forged["transition_counts"][0]["from_stage"] = 1
    elif mutation == "unsupported_transition":
        forged["transition_counts"][0]["to_status"] = "blocked"
    elif mutation == "zero_transition":
        forged["transition_counts"][0]["count"] = 0
    elif mutation == "observed_exceeds":
        forged["transition_counts"][0]["count"] = forged["corpus"]["event_count"] + 1
        forged["lineage_accounting"]["observed_transition_count"] = sum(
            row["count"] for row in forged["transition_counts"]
        )
        reidentify = True
    elif mutation == "lineage_partition":
        forged["lineage_accounting"]["incomplete_terminal_lineage_count"] = 1
        reidentify = True
    elif mutation == "spec_predecessor":
        forged["lineage_accounting"]["unobserved_predecessors_by_stage"]["specification"] = 1
        reidentify = True
    elif mutation == "terminal_successor":
        forged["lineage_accounting"]["unobserved_successors_by_stage"]["pr_terminal"] = 1
        reidentify = True
    elif mutation == "unobserved_overflow":
        forged["lineage_accounting"]["unobserved_predecessors_by_stage"]["patch_evaluation"] = (
            forged["corpus"]["event_count"] + 1
        )
        reidentify = True
    elif mutation == "histogram_sum":
        forged["cycle_histograms"]["review_cycles"]["0"] += 1
        reidentify = True
    elif mutation == "authority":
        forged["authority"]["opens_pr"] = True
        reidentify = True
    elif mutation == "caveats":
        forged["caveats"] = forged["caveats"][:-1]
        reidentify = True
    elif mutation == "sanitized":
        forged["sanitized"] = False
        reidentify = True
    else:
        replacement = "0" if forged["idempotency_key"][-1] != "0" else "1"
        forged["idempotency_key"] = forged["idempotency_key"][:-1] + replacement
    if reidentify:
        _reidentify_artifact(forged)

    with pytest.raises(CreativeCodeLifecycleTransitionAnalyticsError, match=message):
        validate_creative_code_lifecycle_transition_analytics(forged)


def test_schema_matches_closed_python_shape_and_output_contains_no_raw_lineage() -> None:
    events = _full_chain()
    artifact = _analytics(events)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(artifact)
    assert schema["properties"]["artifact_type"]["const"] == ARTIFACT_TYPE
    assert schema["properties"]["caveats"]["const"] == CAVEATS
    transition_array = schema["properties"]["transition_counts"]
    assert transition_array["maxItems"] == len(analytics_contract.ALLOWED_TRANSITIONS) == 9
    assert transition_array["uniqueItems"] is True
    assert transition_array["items"] == {"$ref": "#/$defs/transition_count"}
    transition_profiles = {
        (
            branch["properties"]["from_stage"]["const"],
            branch["properties"]["from_status"]["const"],
            branch["properties"]["to_stage"]["const"],
            branch["properties"]["to_status"]["const"],
        )
        for branch in schema["$defs"]["transition_count"]["oneOf"]
    }
    assert transition_profiles == analytics_contract.ALLOWED_TRANSITIONS
    for branch in schema["$defs"]["transition_count"]["oneOf"]:
        assert branch["additionalProperties"] is False
        assert set(branch["required"]) == analytics_contract.TRANSITION_KEYS
        assert branch["properties"]["count"] == {"$ref": "#/$defs/positive_count"}
    assert schema["$defs"]["positive_count"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": analytics_contract.MAX_COUNT,
    }
    assert all(
        (
            row["from_stage"],
            row["from_status"],
            row["to_stage"],
            row["to_status"],
        )
        in transition_profiles
        and 1 <= row["count"] <= schema["$defs"]["positive_count"]["maximum"]
        for row in artifact["transition_counts"]
    )
    assert schema["$defs"]["authority"]["additionalProperties"] is False
    assert set(schema["$defs"]["authority"]["required"]) == set(default_authority())

    rendered = canonical_analytics_bytes(artifact).decode("utf-8")
    raw_values: set[str] = set()
    for event in events:
        raw_values.update(
            {
                event["event_id"],
                event["idempotency_key"],
                event["source_artifact_id"],
                event["source_fingerprint"],
            }
        )
        raw_values.update(value for value in event.get("candidate_ids", {}).values() if value)
        if event["lane_stage"] == "pr_terminal":
            projection = event["terminal_projection"]
            raw_values.update(
                value for value in projection.values() if isinstance(value, str) and len(value) >= 8
            )
    for raw_value in raw_values:
        assert raw_value not in rendered
    for forbidden_key in (
        "event_id",
        "candidate_ids",
        "source_artifact_id",
        "source_fingerprint",
        "source_packet_id",
        "source_bundle_id",
        "selected_variant_id",
        "request_id",
        "result_id",
        "promotion_id",
        "repository",
        "pull_request_number",
        "promoted_head_sha",
        "closure_epoch",
        "review_observation",
        "governance_observation",
        "post_merge_observation",
        "path",
        "timestamp",
        "review_text",
        "prompt",
        "patch",
        "command_output",
        "provider_payload",
        "oracle_stdout",
    ):
        assert f'"{forbidden_key}":' not in rendered


def test_schema_structurally_represents_closed_shape_and_negative_constraints() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    definitions = schema["$defs"]

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == analytics_contract.TOP_LEVEL_KEYS
    assert definitions["corpus"]["additionalProperties"] is False
    assert set(definitions["corpus"]["required"]) == analytics_contract.CORPUS_KEYS
    assert definitions["lineage_accounting"]["additionalProperties"] is False
    assert set(definitions["lineage_accounting"]["required"]) == analytics_contract.LINEAGE_KEYS
    assert definitions["stage_counts"]["additionalProperties"] is False
    assert set(definitions["stage_counts"]["required"]) == set(analytics_contract.STAGES)
    assert definitions["histogram"]["additionalProperties"] is False
    assert set(definitions["histogram"]["required"]) == set(analytics_contract.HISTOGRAM_BUCKETS)
    assert definitions["cycle_histograms"]["additionalProperties"] is False
    assert set(definitions["cycle_histograms"]["required"]) == set(analytics_contract.PROCESS_KEYS)

    # These exact Draft 2020-12 keywords represent the exercised negative fixtures:
    # unknown keys, wrong scalar type, negative count, and duplicate transition rows.
    assert definitions["positive_count"]["type"] == "integer"
    assert definitions["positive_count"]["minimum"] == 1
    assert schema["properties"]["transition_counts"]["uniqueItems"] is True


def test_modules_have_no_external_authority_imports_or_dynamic_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    forbidden_import_roots = {
        "boto3",
        "github",
        "httpx",
        "psycopg",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "urllib",
    }
    forbidden_call_roots = forbidden_import_roots | {
        "agent_coordinator",
        "evidence_graph",
        "provider",
        "router",
        "runtime",
    }
    for module in (analytics_contract, cli):
        tree = ast.parse(inspect.getsource(module))
        imports: set[str] = set()
        call_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call):
                target = node.func
                while isinstance(target, ast.Attribute):
                    target = target.value
                if isinstance(target, ast.Name):
                    call_roots.add(target.id)
        assert imports.isdisjoint(forbidden_import_roots)
        assert call_roots.isdisjoint(forbidden_call_roots)

    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("analytics attempted forbidden external authority")

    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(cli.os, "system", forbidden)

    _analytics(_full_chain())
    cli.build_from_snapshot(telemetry_dir=telemetry_root)


def _configure_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    events: list[dict[str, Any]],
) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    creative_root = repo_root / "artifacts" / "orchestration" / "creative_code"
    telemetry_root = creative_root / "telemetry"
    analytics_root = creative_root / "lifecycle_transition_analytics"
    telemetry_root.mkdir(parents=True)
    monkeypatch.setattr(cli, "REPO_ROOT", repo_root)
    monkeypatch.setattr(cli, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(cli, "TELEMETRY_ROOT", telemetry_root)
    monkeypatch.setattr(cli, "ANALYTICS_ROOT", analytics_root)
    event_lines = [json.dumps(event, sort_keys=True) for event in events]
    (telemetry_root / cli.EVENTS_FILE).write_text(
        "\n".join(event_lines) + ("\n" if event_lines else ""),
        encoding="utf-8",
    )
    (telemetry_root / cli.ROLLUP_FILE).write_text(
        json.dumps(_rollup(events), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return telemetry_root, analytics_root


def test_cli_build_uses_fixed_output_mode_and_identical_replay_is_zero_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    relative = telemetry_root.relative_to(cli.REPO_ROOT)

    path, replayed, artifact = cli.build_from_snapshot(telemetry_dir=relative)
    assert replayed is False
    assert path == cli.ANALYTICS_ROOT / artifact["analytics_id"] / cli.ANALYTICS_FILE
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.read_bytes() == canonical_analytics_bytes(artifact)
    before = path.stat()

    replay_path, replayed, replay = cli.build_from_snapshot(telemetry_dir=relative)
    after = replay_path.stat()
    assert replayed is True
    assert replay == artifact
    assert (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )


def test_cli_validate_is_read_only_and_tampered_winner_is_never_repaired(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    path, _, artifact = cli.build_from_snapshot(telemetry_dir=telemetry_root)
    before = path.stat()
    assert cli.validate_snapshot_artifact(telemetry_dir=telemetry_root) == artifact
    after = path.stat()
    assert (before.st_ino, before.st_mtime_ns, before.st_ctime_ns) == (
        after.st_ino,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )

    tampered = path.read_bytes().replace(b'"sanitized":true', b'"sanitized":false')
    path.write_bytes(tampered)
    preserved = path.read_bytes()
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert path.read_bytes() == preserved


@pytest.mark.parametrize(
    "surface",
    [
        "events_symlink",
        "events_hardlink",
        "rollup_symlink",
        "rollup_hardlink",
        "outside",
        "traversal",
    ],
)
def test_cli_rejects_symlink_hardlink_and_outside_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    surface: str,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    events_path = telemetry_root / cli.EVENTS_FILE
    rollup_path = telemetry_root / cli.ROLLUP_FILE
    if surface == "events_symlink":
        original = telemetry_root / "events-original.jsonl"
        events_path.rename(original)
        events_path.symlink_to(original)
        expected = "symlink"
    elif surface == "events_hardlink":
        os.link(events_path, telemetry_root / "events-hardlink.jsonl")
        expected = "hardlink"
    elif surface == "rollup_symlink":
        original = telemetry_root / "rollup-original.json"
        rollup_path.rename(original)
        rollup_path.symlink_to(original)
        expected = "symlink"
    elif surface == "rollup_hardlink":
        os.link(rollup_path, telemetry_root / "rollup-hardlink.json")
        expected = "hardlink"
    elif surface == "traversal":
        outside = telemetry_root.parent / "outside"
        outside.mkdir()
        with pytest.raises(
            cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="outside_fixed_root"
        ):
            cli.build_from_snapshot(telemetry_dir=telemetry_root / ".." / "outside")
        return
    else:
        outside = tmp_path / "outside"
        outside.mkdir()
        with pytest.raises(
            cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="outside_fixed_root"
        ):
            cli.build_from_snapshot(telemetry_dir=outside)
        return
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=expected):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)


@pytest.mark.parametrize("filename", [cli.EVENTS_FILE, cli.ROLLUP_FILE])
def test_cli_rejects_nonregular_source_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    filename: str,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    source = telemetry_root / filename
    source.unlink()
    source.mkdir()

    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="must_be_regular"
    ):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert not analytics_root.exists()


@pytest.mark.parametrize("surface", ["directory_component", "telemetry_root"])
def test_cli_rejects_symlinked_directory_components(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    surface: str,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    if surface == "directory_component":
        real = telemetry_root / "real"
        real.mkdir()
        for filename in (cli.EVENTS_FILE, cli.ROLLUP_FILE):
            (telemetry_root / filename).rename(real / filename)
        requested = telemetry_root / "linked"
        requested.symlink_to(real, target_is_directory=True)
    else:
        real = telemetry_root.with_name("telemetry-real")
        telemetry_root.rename(real)
        telemetry_root.symlink_to(real, target_is_directory=True)
        requested = telemetry_root

    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="symlink"):
        cli.build_from_snapshot(telemetry_dir=requested)
    assert not analytics_root.exists()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"\xef\xbb\xbf{}\n", "bom"),
        (b"\xff\n", "invalid_utf8"),
        (b'{"x":NaN}\n', "nonfinite"),
        (b'{"x":1,"x":2}\n', "duplicate"),
        (b"{} trailing\n", "malformed"),
        (b"{\n", "malformed"),
        (b"[]\n", "must_be_object"),
        (b"\n", "blank_line"),
        (b"{}\n", "contract_invalid"),
        (b"{}", "final_newline"),
    ],
)
def test_cli_strict_jsonl_parser_rejects_unsafe_encodings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: bytes,
    message: str,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, [])
    (telemetry_root / cli.EVENTS_FILE).write_bytes(payload)
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=message):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"\xef\xbb\xbf{}", "bom"),
        (b"\xff", "invalid_utf8"),
        (b'{"x":NaN}', "nonfinite"),
        (b'{"x":1,"x":2}', "duplicate"),
        (b"{} trailing", "malformed"),
        (b"{", "malformed"),
        (b"[]", "must_be_object"),
        (b"{}", "contract_invalid"),
    ],
)
def test_cli_strict_rollup_parser_rejects_unsafe_or_invalid_payloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: bytes,
    message: str,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, [])
    (telemetry_root / cli.ROLLUP_FILE).write_bytes(payload)

    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=message):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert not analytics_root.exists()


def test_cli_rejects_oversized_snapshot_before_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, [])
    (telemetry_root / cli.EVENTS_FILE).write_bytes(b"x" * (cli.MAX_EVENTS_FILE_BYTES + 1))
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="too_large"):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert not analytics_root.exists()


@pytest.mark.parametrize("surface", ["rollup", "event_line", "too_many_lines"])
def test_cli_rejects_each_bounded_input_limit_before_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    surface: str,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, [])
    if surface == "rollup":
        (telemetry_root / cli.ROLLUP_FILE).write_bytes(b"x" * (cli.MAX_ROLLUP_BYTES + 1))
        expected = "telemetry_rollup_too_large"
    elif surface == "event_line":
        monkeypatch.setattr(cli, "MAX_EVENT_LINE_BYTES", 4)
        (telemetry_root / cli.EVENTS_FILE).write_bytes(b'{"x":1}\n')
        expected = "telemetry_event_line_too_large"
    else:
        monkeypatch.setattr(cli, "MAX_EVENT_LINES", 1)
        (telemetry_root / cli.EVENTS_FILE).write_bytes(b"{}\n{}\n")
        expected = "telemetry_events_too_many_lines"

    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=expected):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert not analytics_root.exists()


def test_path_and_directory_resolution_errors_are_closed_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, [])

    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="telemetry_directory_missing"
    ):
        cli._resolve_telemetry_dir(telemetry_root / "missing")

    regular = telemetry_root / "regular"
    regular.write_bytes(b"")
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="telemetry_directory_must_be_directory",
    ):
        cli._resolve_telemetry_dir(regular)

    original_lstat = Path.lstat
    failing_component = telemetry_root / "component"
    failing_component.mkdir()

    def fail_component_lstat(path: Path) -> os.stat_result:
        if path == failing_component:
            raise OSError(errno.EIO, "injected component read failure")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_component_lstat)
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="path_component_read_failed",
    ):
        cli._existing_components(failing_component)


def test_component_recheck_and_telemetry_directory_lstat_failures_are_wrapped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, [])
    original_lstat = Path.lstat

    monkeypatch.setattr(cli, "_existing_components", lambda _path: [telemetry_root])

    def fail_lstat(_path: Path) -> os.stat_result:
        raise OSError(errno.EIO, "injected lstat failure")

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="telemetry_component_read_failed",
    ):
        cli._reject_symlink_components(telemetry_root, label="telemetry")

    monkeypatch.setattr(Path, "lstat", original_lstat)
    monkeypatch.setattr(cli, "_reject_symlink_components", lambda *_args, **_kwargs: None)

    def fail_resolved_lstat(path: Path) -> os.stat_result:
        if path == telemetry_root:
            raise OSError(errno.EIO, "injected resolved-directory failure")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_resolved_lstat)
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="telemetry_directory_read_failed",
    ):
        cli._resolve_telemetry_dir(telemetry_root)


@pytest.mark.parametrize("failure", ["opened_identity", "read", "oversized_race", "after_lstat"])
def test_bounded_reader_wraps_race_and_io_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    source = tmp_path / "bounded.json"
    source.write_bytes(b"12345")
    original_identity = cli._identity
    original_lstat = Path.lstat
    calls = 0

    if failure == "opened_identity":

        def identity(info: os.stat_result) -> cli._FileIdentity:
            nonlocal calls
            calls += 1
            value = original_identity(info)
            return replace(value, inode=value.inode + 1) if calls == 2 else value

        monkeypatch.setattr(cli, "_identity", identity)
        maximum = 10
    elif failure == "read":

        def fail_open(*_args: Any, **_kwargs: Any) -> int:
            raise OSError(errno.EIO, "injected open failure")

        monkeypatch.setattr(cli.os, "open", fail_open)
        maximum = 10
    elif failure == "oversized_race":

        def smaller_initial_size(info: os.stat_result) -> cli._FileIdentity:
            nonlocal calls
            calls += 1
            value = original_identity(info)
            return replace(value, size=4) if calls <= 2 else value

        monkeypatch.setattr(cli, "_identity", smaller_initial_size)
        maximum = 4
    else:
        monkeypatch.setattr(cli, "_reject_symlink_components", lambda *_args, **_kwargs: None)

        def fail_after_lstat(path: Path) -> os.stat_result:
            nonlocal calls
            if path == source:
                calls += 1
                if calls == 2:
                    raise OSError(errno.EIO, "injected post-read lstat failure")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_after_lstat)
        maximum = 10

    expected = (
        "too_large"
        if failure == "oversized_race"
        else ("read_failed" if failure == "read" else "identity_changed")
    )
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=expected):
        cli._read_bounded_regular_bytes(source, label="bounded", maximum=maximum)


def test_bounded_reader_and_directory_fsync_wrap_close_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"{}")
    original_close = cli.os.close

    def close_then_fail(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError(errno.EIO, "injected close failure")

    monkeypatch.setattr(cli.os, "close", close_then_fail)
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="read_failed"):
        cli._read_bounded_regular_bytes(source, label="source", maximum=10)

    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="analytics_directory_fsync_failed",
    ):
        cli._fsync_directory(tmp_path)


def test_missing_source_recheck_is_reported_as_identity_change(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"{}")
    _, seal = cli._read_bounded_regular_bytes(source, label="source", maximum=10)
    source.unlink()

    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="identity_changed"
    ):
        cli._recheck_source(seal, label="source")


def test_atomic_link_failure_leaves_no_canonical_or_staging_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, _full_chain())

    def fail_link(_staging: Path, _target: Path) -> None:
        raise cli.CreativeCodeLifecycleTransitionAnalyticsIOError("injected_link_failure")

    monkeypatch.setattr(cli, "_link_noreplace", fail_link)
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="injected_link_failure",
    ):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert not list(analytics_root.rglob(cli.ANALYTICS_FILE))
    assert not list(analytics_root.rglob("*.staging"))


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("staging_create", "analytics_staging_write_failed"),
        ("staging_write", "analytics_staging_write_failed"),
        ("file_fsync", "analytics_staging_write_failed"),
        ("directory_fsync", "analytics_directory_fsync_failed"),
        ("link_unsupported", "analytics_hardlink_unsupported"),
    ],
)
def test_publication_failures_leave_no_partial_canonical_or_staging_residue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
    message: str,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    original_fsync = cli.os.fsync

    if failure == "staging_create":

        def fail_mkstemp(*_args: Any, **_kwargs: Any) -> tuple[int, str]:
            raise OSError(errno.EIO, "injected staging creation failure")

        monkeypatch.setattr(cli.tempfile, "mkstemp", fail_mkstemp)
    elif failure == "staging_write":
        monkeypatch.setattr(cli.os, "write", lambda _descriptor, _content: 0)
    elif failure == "file_fsync":

        def fail_file_fsync(descriptor: int) -> None:
            if stat.S_ISREG(cli.os.fstat(descriptor).st_mode):
                raise OSError(errno.EIO, "injected file fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(cli.os, "fsync", fail_file_fsync)
    elif failure == "directory_fsync":

        def fail_directory_fsync(descriptor: int) -> None:
            if stat.S_ISDIR(cli.os.fstat(descriptor).st_mode):
                raise OSError(errno.EIO, "injected directory fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(cli.os, "fsync", fail_directory_fsync)
    else:

        def fail_hardlink(*_args: Any, **_kwargs: Any) -> None:
            raise OSError(errno.EXDEV, "injected unsupported hardlink")

        monkeypatch.setattr(cli.os, "link", fail_hardlink)

    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=message):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert not list(analytics_root.rglob(cli.ANALYTICS_FILE))
    assert not list(analytics_root.rglob("*.staging"))


def test_staging_descriptor_close_failure_is_bounded_and_cleans_this_attempt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    original_mkstemp = cli.tempfile.mkstemp
    original_close = cli.os.close
    staging_descriptor: dict[str, int] = {}

    def tracked_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        descriptor, path = original_mkstemp(*args, **kwargs)
        staging_descriptor["value"] = descriptor
        return descriptor, path

    def fail_staging_close(descriptor: int) -> None:
        original_close(descriptor)
        if descriptor == staging_descriptor.get("value"):
            raise OSError(errno.EIO, "injected staging descriptor close failure")

    monkeypatch.setattr(cli.tempfile, "mkstemp", tracked_mkstemp)
    monkeypatch.setattr(cli.os, "close", fail_staging_close)

    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="analytics_staging_write_failed",
    ):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)

    assert not list(analytics_root.rglob(cli.ANALYTICS_FILE))
    assert not list(analytics_root.rglob("*.staging"))


@pytest.mark.parametrize("failure", ["create", "read", "not_directory", "existing_not_directory"])
def test_output_root_failures_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    _, analytics_root = _configure_snapshot(monkeypatch, tmp_path, [])
    original_mkdir = Path.mkdir
    original_resolve = Path.resolve

    if failure == "create":

        def fail_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
            if path == analytics_root:
                raise OSError(errno.EIO, "injected output root creation failure")
            original_mkdir(path, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", fail_mkdir)
        expected = "analytics_root_create_failed"
        operation = cli._ensure_output_root
    elif failure == "read":
        analytics_root.mkdir(parents=True)

        def fail_resolve(path: Path, *args: Any, **kwargs: Any) -> Path:
            if path == analytics_root:
                raise OSError(errno.EIO, "injected output root resolve failure")
            return original_resolve(path, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", fail_resolve)
        expected = "analytics_root_read_failed"
        operation = cli._ensure_output_root
    elif failure == "not_directory":
        analytics_root.write_bytes(b"not-a-directory")

        def ignore_root_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
            if path != analytics_root:
                original_mkdir(path, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", ignore_root_mkdir)
        expected = "analytics_root_must_be_directory"
        operation = cli._ensure_output_root
    else:
        analytics_root.write_bytes(b"not-a-directory")
        expected = "analytics_root_must_be_directory"
        operation = cli._existing_output_root

    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=expected):
        operation()


@pytest.mark.parametrize(
    "state",
    [
        "artifact_scalar",
        "artifact_noncanonical",
        "namespace_lstat",
        "namespace_not_directory",
        "namespace_iterdir_existing",
        "namespace_iterdir_empty",
        "namespace_ambiguous_empty",
    ],
)
def test_existing_artifact_and_namespace_failures_are_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    state: str,
) -> None:
    target_dir = tmp_path / "namespace"
    target_file = target_dir / cli.ANALYTICS_FILE
    original_lstat = Path.lstat
    original_iterdir = Path.iterdir
    read_artifact = False

    if state == "artifact_scalar":
        target_dir.mkdir()
        target_file.write_bytes(b"[]")
        target_file.chmod(0o600)
        expected = "analytics_artifact_must_be_object"
        read_artifact = True
    elif state == "artifact_noncanonical":
        target_dir.mkdir()
        artifact = _analytics(_full_chain())
        target_file.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
        target_file.chmod(0o600)
        expected = "analytics_artifact_not_canonical"
        read_artifact = True
    elif state == "namespace_lstat":
        monkeypatch.setattr(cli, "_reject_symlink_components", lambda *_args, **_kwargs: None)

        def fail_lstat(path: Path) -> os.stat_result:
            if path == target_dir:
                raise OSError(errno.EIO, "injected namespace lstat failure")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
        expected = "analytics_namespace_read_failed"
    elif state == "namespace_not_directory":
        target_dir.write_bytes(b"not-a-directory")
        expected = "analytics_namespace_must_be_directory"
    elif state == "namespace_iterdir_existing":
        target_dir.mkdir()
        target_file.write_bytes(b"{}")

        def fail_iterdir(path: Path) -> Any:
            if path == target_dir:
                raise OSError(errno.EIO, "injected namespace iteration failure")
            return original_iterdir(path)

        monkeypatch.setattr(Path, "iterdir", fail_iterdir)
        expected = "analytics_namespace_read_failed"
    elif state == "namespace_iterdir_empty":
        target_dir.mkdir()

        def fail_iterdir(path: Path) -> Any:
            if path == target_dir:
                raise OSError(errno.EIO, "injected namespace iteration failure")
            return original_iterdir(path)

        monkeypatch.setattr(Path, "iterdir", fail_iterdir)
        expected = "analytics_namespace_read_failed"
    else:
        target_dir.mkdir()
        (target_dir / "unexpected").write_bytes(b"ambiguous")
        expected = "analytics_namespace_ambiguous"

    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match=expected):
        if read_artifact:
            cli._read_existing_artifact(target_file)
        else:
            cli._read_namespace(target_dir, target_file)


@pytest.mark.parametrize("failure", ["exists", "oserror"])
def test_namespace_creation_races_are_rechecked_or_wrapped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "analytics-id"
    original_mkdir = Path.mkdir

    def fail_target_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == target:
            if failure == "exists":
                original_mkdir(path, *args, **kwargs)
                raise FileExistsError(errno.EEXIST, "injected namespace race", path)
            raise OSError(errno.EIO, "injected namespace creation failure")
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_target_mkdir)
    if failure == "exists":
        created_dir, created_file, existing = cli._create_namespace(root, "analytics-id")
        assert (created_dir, created_file, existing) == (
            target,
            target / cli.ANALYTICS_FILE,
            None,
        )
    else:
        with pytest.raises(
            cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
            match="analytics_namespace_create_failed",
        ):
            cli._create_namespace(root, "analytics-id")


@pytest.mark.parametrize("mode", ["nonregular", "mode_fix"])
def test_staging_file_must_be_private_regular_and_mode_is_corrected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
) -> None:
    original_fstat = cli.os.fstat
    calls = 0

    def altered_fstat(descriptor: int) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            if mode == "nonregular":
                return SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_nlink=1)
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_nlink=1)
        return original_fstat(descriptor)

    monkeypatch.setattr(cli.os, "fstat", altered_fstat)
    if mode == "nonregular":
        with pytest.raises(
            cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
            match="must_be_private_regular",
        ):
            cli._write_staging(tmp_path, b"payload")
        assert not list(tmp_path.glob("*.staging"))
    else:
        staging = cli._write_staging(tmp_path, b"payload")
        assert stat.S_IMODE(staging.stat().st_mode) == 0o600
        cli._cleanup_staging(staging)


def test_link_and_staging_cleanup_low_level_failures_are_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_bytes(b"payload")
    target.write_bytes(b"winner")
    with pytest.raises(FileExistsError):
        cli._link_noreplace(source, target)

    target.unlink()

    def fail_link(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(errno.EIO, "injected generic link failure")

    monkeypatch.setattr(cli.os, "link", fail_link)
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="link_failed"):
        cli._link_noreplace(source, target)

    missing = tmp_path / "missing.staging"
    cli._cleanup_staging(missing)

    class Uncleanable:
        def unlink(self) -> None:
            raise OSError(errno.EIO, "injected cleanup failure")

    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="staging_cleanup_failed",
    ):
        cli._cleanup_staging(cast(Path, Uncleanable()))


def test_publish_rejects_oversized_artifact_before_filesystem_mutation() -> None:
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="analytics_artifact_too_large",
    ):
        cli._publish(
            {"analytics_id": "unused"},
            b"x" * (cli.MAX_ANALYTICS_BYTES + 1),
            source_seals=cast(tuple[cli._SourceSeal, cli._SourceSeal], ()),
        )


def test_atomic_collision_with_malformed_winner_fails_closed_and_preserves_winner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    collided: dict[str, Path] = {}

    def collide(_staging: Path, target: Path) -> None:
        target.write_bytes(b"{")
        target.chmod(0o600)
        collided["target"] = target
        raise FileExistsError(errno.EEXIST, "injected collision", target)

    monkeypatch.setattr(cli, "_link_noreplace", collide)
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="malformed"):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)

    assert collided["target"].read_bytes() == b"{"
    assert not list(analytics_root.rglob("*.staging"))


def test_source_identity_drift_before_publish_fails_without_canonical_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, analytics_root = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    original_write = cli._write_staging

    def write_then_change_source(parent: Path, content: bytes) -> Path:
        staging = original_write(parent, content)
        rollup_path = telemetry_root / cli.ROLLUP_FILE
        rollup_path.write_bytes(rollup_path.read_bytes() + b" ")
        return staging

    monkeypatch.setattr(cli, "_write_staging", write_then_change_source)
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="identity_changed"
    ):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)
    assert not list(analytics_root.rglob(cli.ANALYTICS_FILE))
    assert not list(analytics_root.rglob("*.staging"))


@pytest.mark.parametrize("identity_call", [2, 3])
def test_source_identity_drift_during_bounded_read_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    identity_call: int,
) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(b"{}")
    original_identity = cli._identity
    calls = 0

    def drift_identity(info: os.stat_result) -> cli._FileIdentity:
        nonlocal calls
        calls += 1
        identity = original_identity(info)
        if calls == identity_call:
            return replace(identity, inode=identity.inode + 1)
        return identity

    monkeypatch.setattr(cli, "_identity", drift_identity)
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="identity_changed"
    ):
        cli._read_bounded_regular_bytes(source, label="source", maximum=100)


@pytest.mark.parametrize("winner_state", ["malformed", "divergent", "ambiguous", "wrong_mode"])
def test_existing_winner_failures_preserve_exact_preexisting_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    winner_state: str,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    path, _, _ = cli.build_from_snapshot(telemetry_dir=telemetry_root)
    extra: Path | None = None
    if winner_state == "malformed":
        path.write_bytes(b"{")
    elif winner_state == "divergent":
        other = _analytics(_full_chain(prefix="other", number=2500))
        path.write_bytes(canonical_analytics_bytes(other))
    elif winner_state == "ambiguous":
        extra = path.parent / "unexpected"
        extra.write_bytes(b"ambiguous")
    else:
        path.chmod(0o644)
    preserved = path.read_bytes()
    preserved_stat = path.stat()

    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError):
        cli.build_from_snapshot(telemetry_dir=telemetry_root)

    after = path.stat()
    assert path.read_bytes() == preserved
    assert (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) == (
        preserved_stat.st_ino,
        preserved_stat.st_size,
        preserved_stat.st_mtime_ns,
        preserved_stat.st_ctime_ns,
    )
    if extra is not None:
        assert extra.read_bytes() == b"ambiguous"
    if winner_state == "divergent":
        with pytest.raises(
            cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="divergent_replay"
        ):
            cli.validate_snapshot_artifact(telemetry_dir=telemetry_root)
        assert path.read_bytes() == preserved


def test_validate_missing_root_missing_winner_and_tampered_winner_are_mutation_free(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="analytics_artifact_missing"
    ):
        cli.validate_snapshot_artifact(telemetry_dir=telemetry_root)

    path, _, _ = cli.build_from_snapshot(telemetry_dir=telemetry_root)
    path.unlink()
    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="analytics_artifact_missing"
    ):
        cli.validate_snapshot_artifact(telemetry_dir=telemetry_root)

    path.write_bytes(b"{")
    path.chmod(0o600)
    preserved = path.read_bytes()
    before = path.stat()
    with pytest.raises(cli.CreativeCodeLifecycleTransitionAnalyticsIOError, match="malformed"):
        cli.validate_snapshot_artifact(telemetry_dir=telemetry_root)
    after = path.stat()
    assert path.read_bytes() == preserved
    assert (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )


def test_validate_rejects_ambiguous_namespace_without_mutating_winner_or_sibling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    winner, _, _ = cli.build_from_snapshot(telemetry_dir=telemetry_root)
    sibling = winner.parent / "unexpected-sibling"
    sibling.write_bytes(b"preserve-sibling")
    before = {
        path: (
            path.read_bytes(),
            path.stat().st_ino,
            path.stat().st_mtime_ns,
            path.stat().st_ctime_ns,
        )
        for path in (winner, sibling)
    }

    with pytest.raises(
        cli.CreativeCodeLifecycleTransitionAnalyticsIOError,
        match="analytics_namespace_ambiguous",
    ):
        cli.validate_snapshot_artifact(telemetry_dir=telemetry_root)

    for path in (winner, sibling):
        payload, inode, modified_ns, changed_ns = before[path]
        after = path.stat()
        assert path.read_bytes() == payload
        assert (after.st_ino, after.st_mtime_ns, after.st_ctime_ns) == (
            inode,
            modified_ns,
            changed_ns,
        )


def test_identical_replay_performs_no_writes_links_unlinks_or_mode_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    path, _, artifact = cli.build_from_snapshot(telemetry_dir=telemetry_root)
    before = path.stat()

    def unexpected_mutation(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("identical replay attempted a filesystem mutation")

    monkeypatch.setattr(cli.tempfile, "mkstemp", unexpected_mutation)
    for name in ("write", "link", "unlink", "chmod", "fchmod"):
        monkeypatch.setattr(cli.os, name, unexpected_mutation)

    replay_path, replayed, replay = cli.build_from_snapshot(telemetry_dir=telemetry_root)
    after = replay_path.stat()
    assert replayed is True
    assert replay == artifact
    assert (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )


def test_build_replay_and_validate_leave_source_snapshot_bytes_and_stats_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    sources = [telemetry_root / cli.EVENTS_FILE, telemetry_root / cli.ROLLUP_FILE]
    before = {
        path: (path.read_bytes(), path.stat().st_ino, path.stat().st_size, path.stat().st_mtime_ns)
        for path in sources
    }

    cli.build_from_snapshot(telemetry_dir=telemetry_root)
    cli.build_from_snapshot(telemetry_dir=telemetry_root)
    cli.validate_snapshot_artifact(telemetry_dir=telemetry_root)

    for path in sources:
        payload, inode, size, modified_ns = before[path]
        after = path.stat()
        assert path.read_bytes() == payload
        assert (after.st_ino, after.st_size, after.st_mtime_ns) == (
            inode,
            size,
            modified_ns,
        )


def test_cli_prints_bounded_sanitized_pass_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    relative = telemetry_root.relative_to(cli.REPO_ROOT)
    assert cli.main(["build", "--telemetry-dir", str(relative)]) == 0
    output = capsys.readouterr().out.strip()
    assert output.startswith("PASS: creative-code lifecycle transition analytics built")
    assert "replay=new" in output
    assert str(tmp_path) not in output
    assert cli.main(["validate", "--telemetry-dir", str(relative)]) == 0
    validation_output = capsys.readouterr().out.strip()
    assert validation_output.startswith(
        "PASS: creative-code lifecycle transition analytics validated"
    )
    assert str(tmp_path) not in validation_output


def test_cli_help_closes_snapshot_semantics_and_validation_mutation_boundary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def normalized_help(argv: list[str]) -> str:
        with pytest.raises(SystemExit) as help_exit:
            cli._parse_args(argv)
        assert help_exit.value.code == 0
        return " ".join(capsys.readouterr().out.split())

    root_help = normalized_help(["--help"])
    build_help = normalized_help(["build", "--help"])
    validate_help = normalized_help(["validate", "--help"])
    semantic_fragments = (
        "Observed counts each valid adjacent event pair joined by exact typed lineage",
        "both events present in the frozen telemetry snapshot",
        "permitted fanout creates multiple observed pairs",
        "An unobserved predecessor means no unique valid predecessor is present",
        "an ambiguous predecessor fails the build",
        "An unobserved successor means zero valid successors are present",
        "one or more valid successors are observed, including permitted fanout",
        "Absence is snapshot-local, not proof that the transition did not occur",
        "A complete terminal lineage is linked through every lifecycle stage within the frozen snapshot only",
        "not operational completeness, PR readiness, or lifecycle success",
    )
    for rendered in (root_help, build_help, validate_help):
        for fragment in semantic_fragments:
            assert fragment in rendered
        assert "no unique valid successor" not in rendered

    assert "Publish the snapshot-derived analytics artifact" in build_help
    assert "Mutation-free exact-byte validation" in validate_help
    for rendered in (build_help, validate_help):
        assert "--telemetry-dir" in rendered
        assert "fixed-name event JSONL and mixed v2 rollup" in rendered
        assert "relative paths resolve from the repository root" in rendered


def test_contract_and_schema_annotations_define_snapshot_only_accounting() -> None:
    contract = " ".join(TELEMETRY_CONTRACT.read_text(encoding="utf-8").split())
    for fragment in (
        "Each valid adjacent event pair joined by the exact typed lineage key",
        "both events present in the frozen telemetry snapshot",
        "permitted fanout creates multiple observed pairs",
        "An unobserved predecessor means that no unique valid predecessor is present",
        "an ambiguous predecessor fails the build",
        "An unobserved successor means that zero valid successors are present",
        "one or more valid successors are observed",
        "specification-to-patch fanout",
        "accepted-patch-to-distinct-promotion fanout",
        "Absence is snapshot-local, never proof that the transition did not occur",
        "complete terminal lineage means that one terminal event is uniquely linked through every lifecycle stage",
        "inside that frozen snapshot only",
        "not operational completeness, PR readiness, or lifecycle success",
    ):
        assert fragment in contract
    assert "no unique valid successor" not in contract

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    transition_description = schema["properties"]["transition_counts"]["description"]
    assert "valid adjacent event pairs" in transition_description
    assert "exact typed lineage" in transition_description
    assert "frozen telemetry snapshot" in transition_description
    assert "permitted fanout creates multiple observed pairs" in transition_description

    lineage_properties = schema["$defs"]["lineage_accounting"]["properties"]
    descriptions = {
        key: value["description"]
        for key, value in lineage_properties.items()
        if key
        in {
            "observed_transition_count",
            "unobserved_predecessors_by_stage",
            "unobserved_successors_by_stage",
            "complete_terminal_lineage_count",
            "incomplete_terminal_lineage_count",
        }
    }
    assert set(descriptions) == {
        "observed_transition_count",
        "unobserved_predecessors_by_stage",
        "unobserved_successors_by_stage",
        "complete_terminal_lineage_count",
        "incomplete_terminal_lineage_count",
    }
    assert "valid adjacent event pairs" in descriptions["observed_transition_count"]
    assert "exact typed lineage" in descriptions["observed_transition_count"]
    assert (
        "permitted fanout creates multiple observed pairs"
        in descriptions["observed_transition_count"]
    )
    predecessor_description = descriptions["unobserved_predecessors_by_stage"]
    assert "no unique valid predecessor" in predecessor_description
    assert "an ambiguous predecessor fails the build" in predecessor_description
    successor_description = descriptions["unobserved_successors_by_stage"]
    assert "zero valid successors" in successor_description
    assert "one or more valid successors are observed" in successor_description
    assert "including permitted fanout" in successor_description
    assert "no unique valid successor" not in successor_description
    for description in (predecessor_description, successor_description):
        assert "absence is snapshot-local" in description
        assert "not proof that the transition did not occur" in description
    assert "frozen telemetry snapshot only" in descriptions["complete_terminal_lineage_count"]
    assert (
        "not operational completeness, PR readiness, or lifecycle success"
        in descriptions["complete_terminal_lineage_count"]
    )
    assert (
        "not uniquely linked through every lifecycle stage"
        in descriptions["incomplete_terminal_lineage_count"]
    )
    assert "snapshot-local incompleteness" in descriptions["incomplete_terminal_lineage_count"]


def test_cli_contract_failure_does_not_echo_untrusted_rollup_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    telemetry_root, _ = _configure_snapshot(monkeypatch, tmp_path, _full_chain())
    rollup_path = telemetry_root / cli.ROLLUP_FILE
    rollup = json.loads(rollup_path.read_text(encoding="utf-8"))
    unsafe_key = f"/Users/private/{tmp_path.name}"
    rollup[unsafe_key] = True
    rollup_path.write_text(json.dumps(rollup) + "\n", encoding="utf-8")

    assert cli.main(["build", "--telemetry-dir", str(telemetry_root)]) == 1
    output = capsys.readouterr().out.strip()
    assert output == "FAIL: telemetry_rollup_contract_invalid"
    assert unsafe_key not in output

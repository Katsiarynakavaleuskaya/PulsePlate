#!/usr/bin/env python3
"""Build, validate, and score one local shadow lifecycle forecast."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any, cast

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_lifecycle_transition_analytics as analytics_cli
from scripts.orchestration import creative_code_patch_generation as generation_cli
from scripts.orchestration.creative_code_lifecycle_bayesian_shadow_contract import (
    FAMILY_IDS,
    FORECAST_FILENAME,
    SCORE_FILENAME,
    START_FILENAME,
    CreativeCodeLifecycleBayesianShadowError,
    build_lifecycle_forecast,
    build_lifecycle_forecast_score,
    canonical_shadow_root,
    canonical_shadow_bytes,
    expected_forecast_ref,
    load_forecast_for_gate,
    publish_shadow_artifact,
    read_shadow_json,
    recheck_shadow_source,
    validate_lifecycle_forecast,
    validate_lifecycle_forecast_score,
    validate_lifecycle_forecast_score_binding,
    validate_target_start,
    validate_target_start_binding,
)
from scripts.orchestration.creative_code_lifecycle_transition_analytics import (
    CreativeCodeLifecycleTransitionAnalyticsIOError,
    ValidatedLifecycleTransitionSnapshot,
)
from scripts.orchestration.creative_code_lifecycle_transition_analytics_contract import (
    CreativeCodeLifecycleTransitionAnalyticsError,
)
from scripts.orchestration.creative_code_patch_contract import CreativeCodePatchContractError
from scripts.orchestration.creative_code_patch_generation import (
    CreativeCodePatchGenerationError,
)
from scripts.orchestration.creative_code_patch_workspace import CreativeCodePatchWorkspaceError
from scripts.orchestration.creative_code_telemetry_contract import (
    CreativeCodeTelemetryContractError,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
BAYESIAN_SHADOW_ROOT = canonical_shadow_root(REPO_ROOT)

BUILD_SUCCESS = "PASS: creative-code lifecycle shadow forecast built"
VALIDATE_FORECAST_SUCCESS = "PASS: creative-code lifecycle shadow forecast valid"
VALIDATE_START_SUCCESS = "PASS: creative-code lifecycle shadow target start valid"
SCORE_SUCCESS = "PASS: creative-code lifecycle shadow forecast scored"
VALIDATE_SCORE_SUCCESS = "PASS: creative-code lifecycle shadow score valid"


def _repo_ref(path: Path, *, label: str) -> str:
    try:
        return path.resolve(strict=True).relative_to(REPO_ROOT.resolve(strict=True)).as_posix()
    except (OSError, ValueError) as exc:
        raise CreativeCodeLifecycleBayesianShadowError(
            f"{label} must stay under the repository root"
        ) from exc


def _resolve_repo_ref(ref: str, *, label: str, directory: bool = False) -> Path:
    if not isinstance(ref, str) or not ref or "\\" in ref:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is invalid")
    pure = PurePosixPath(ref)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is invalid")
    requested = REPO_ROOT / pure
    try:
        resolved = requested.resolve(strict=True)
        root = REPO_ROOT.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is unavailable") from exc
    if directory and not resolved.is_dir():
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must be a directory")
    if not directory and not resolved.is_file():
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must be a file")
    return resolved


def _analytics_ref(snapshot: ValidatedLifecycleTransitionSnapshot) -> str:
    path = (
        analytics_cli.ANALYTICS_ROOT
        / cast(str, snapshot.analytics["analytics_id"])
        / analytics_cli.ANALYTICS_FILE
    )
    return _repo_ref(path, label="analytics artifact")


def _candidate_ids(event: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = event.get("candidate_ids")
    return raw if isinstance(raw, dict) else {}


def _matches_target(event: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    ids = _candidate_ids(event)
    return bool(
        ids.get("source_bundle_id") == target["source_bundle_id"]
        and ids.get("selected_variant_id") == target["selected_variant_id"]
        and ids.get("request_id") == target["request_id"]
    )


def _require_target_absent(events: Sequence[Mapping[str, Any]], target: Mapping[str, Any]) -> None:
    if any(_matches_target(event, target) for event in events):
        raise CreativeCodeLifecycleBayesianShadowError("retrospective_forecast_forbidden")


def _load_gate_before_generation(gate_path: Path) -> tuple[Path, dict[str, Any]]:
    return cast(
        tuple[Path, dict[str, Any]],
        generation_cli.load_validated_generation_gate_context(gate_path),
    )


def _load_gate_for_readback(gate_path: Path) -> tuple[Path, dict[str, Any]]:
    resolved, stored = generation_cli.load_stored_generation_gate(gate_path)
    receipt_path = resolved.parent / generation_cli.RECEIPT_FILENAME
    if receipt_path.exists() or receipt_path.is_symlink():
        receipt_gate, _receipt = generation_cli.load_validated_generation_receipt_context(
            gate_path=resolved,
            receipt_path=receipt_path,
        )
        if receipt_gate != stored:
            raise CreativeCodeLifecycleBayesianShadowError("stored gate/receipt mismatch")
        return resolved, stored
    try:
        return _load_gate_before_generation(resolved)
    except CreativeCodePatchGenerationError:
        generation_cli.validate_stored_generation_gate_sources(stored)
        return resolved, stored


def _load_forecast_sources(
    forecast_path: Path,
) -> tuple[
    dict[str, Any],
    Any,
    Path,
    dict[str, Any],
    ValidatedLifecycleTransitionSnapshot,
]:
    raw, initial_seal = read_shadow_json(
        forecast_path,
        shadow_root=BAYESIAN_SHADOW_ROOT,
        label="shadow forecast",
    )
    preliminary = validate_lifecycle_forecast(raw)
    gate_path = _resolve_repo_ref(
        preliminary["target"]["generation_gate_ref"], label="generation gate"
    )
    resolved_gate, gate = _load_gate_for_readback(gate_path)
    forecast, seal = load_forecast_for_gate(
        forecast_path,
        gate=gate,
        gate_ref=_repo_ref(resolved_gate, label="generation gate"),
        shadow_root=BAYESIAN_SHADOW_ROOT,
    )
    if seal != initial_seal:
        raise CreativeCodeLifecycleBayesianShadowError("shadow forecast identity changed")
    telemetry_dir = _resolve_repo_ref(
        forecast["baseline"]["telemetry_dir_ref"],
        label="baseline telemetry directory",
        directory=True,
    )
    snapshot = analytics_cli.load_validated_snapshot_artifact(telemetry_dir=telemetry_dir)
    rebuilt = build_lifecycle_forecast(
        analytics=snapshot.analytics,
        analytics_ref=_analytics_ref(snapshot),
        telemetry_dir_ref=_repo_ref(telemetry_dir, label="baseline telemetry directory"),
        gate=gate,
        gate_ref=_repo_ref(resolved_gate, label="generation gate"),
        produced_at=forecast["produced_at"],
    )
    if rebuilt != forecast:
        raise CreativeCodeLifecycleBayesianShadowError("forecast sources changed")
    _require_target_absent(snapshot.events, forecast["target"])
    return forecast, seal, resolved_gate, gate, snapshot


def build_forecast(
    *, telemetry_dir: Path, gate_path: Path, produced_at: str
) -> tuple[Path, bool, dict[str, Any]]:
    resolved_gate, gate = _load_gate_before_generation(gate_path)
    snapshot = analytics_cli.load_validated_snapshot_artifact(telemetry_dir=telemetry_dir)
    gate_ref = _repo_ref(resolved_gate, label="generation gate")
    telemetry_ref = _repo_ref(
        telemetry_dir if telemetry_dir.is_absolute() else REPO_ROOT / telemetry_dir,
        label="baseline telemetry directory",
    )
    forecast = build_lifecycle_forecast(
        analytics=snapshot.analytics,
        analytics_ref=_analytics_ref(snapshot),
        telemetry_dir_ref=telemetry_ref,
        gate=gate,
        gate_ref=gate_ref,
        produced_at=produced_at,
    )
    _require_target_absent(snapshot.events, forecast["target"])

    def recheck() -> None:
        current_gate_path, current_gate = _load_gate_before_generation(resolved_gate)
        if current_gate_path != resolved_gate or current_gate != gate:
            raise CreativeCodeLifecycleBayesianShadowError("generation gate changed")
        current = analytics_cli.load_validated_snapshot_artifact(telemetry_dir=telemetry_dir)
        if current != snapshot:
            raise CreativeCodeLifecycleBayesianShadowError("baseline snapshot changed")
        _require_target_absent(current.events, forecast["target"])

    path, replayed = publish_shadow_artifact(
        shadow_root=BAYESIAN_SHADOW_ROOT,
        forecast_id=forecast["forecast_id"],
        filename=FORECAST_FILENAME,
        content=canonical_shadow_bytes(forecast),
        recheck_sources=recheck,
    )
    return path, replayed, forecast


def validate_forecast_path(forecast_path: Path) -> dict[str, Any]:
    forecast, seal, _gate_path, _gate, _snapshot = _load_forecast_sources(forecast_path)
    recheck_shadow_source(seal, label="shadow forecast")
    return forecast


def _load_start(
    *, forecast: Mapping[str, Any], forecast_path: Path, gate: Mapping[str, Any], gate_path: Path
) -> tuple[dict[str, Any], Any, Path]:
    start_path = forecast_path.parent / START_FILENAME
    raw, seal = read_shadow_json(
        start_path,
        shadow_root=BAYESIAN_SHADOW_ROOT,
        label="shadow target start",
    )
    start = validate_target_start_binding(
        start=validate_target_start(raw),
        forecast=forecast,
        forecast_ref=expected_forecast_ref(forecast_id=forecast["forecast_id"]),
        gate=gate,
        gate_ref=_repo_ref(gate_path, label="generation gate"),
    )
    return start, seal, start_path


def validate_start_path(start_path: Path) -> dict[str, Any]:
    raw, seal = read_shadow_json(
        start_path, shadow_root=BAYESIAN_SHADOW_ROOT, label="shadow target start"
    )
    start = cast(dict[str, Any], validate_target_start(raw))
    forecast_path = _resolve_repo_ref(start["forecast_ref"], label="shadow forecast")
    forecast, forecast_seal, gate_path, gate, _snapshot = _load_forecast_sources(forecast_path)
    expected, expected_seal, canonical_path = _load_start(
        forecast=forecast, forecast_path=forecast_path, gate=gate, gate_path=gate_path
    )
    if (
        canonical_path != start_path.resolve(strict=True)
        or expected != start
        or expected_seal != seal
    ):
        raise CreativeCodeLifecycleBayesianShadowError("target start is not in canonical slot")
    recheck_shadow_source(forecast_seal, label="shadow forecast")
    recheck_shadow_source(seal, label="shadow target start")
    return start


def _event_fingerprint(event: Mapping[str, Any]) -> str:
    return cast(str, fingerprint_payload(cast(Any, dict(event))))


def _require_baseline_subset(
    baseline: Sequence[Mapping[str, Any]], later: Sequence[Mapping[str, Any]]
) -> None:
    baseline_fingerprints = {_event_fingerprint(event) for event in baseline}
    later_fingerprints = {_event_fingerprint(event) for event in later}
    if not baseline_fingerprints.issubset(later_fingerprints):
        raise CreativeCodeLifecycleBayesianShadowError("baseline_snapshot_drift")


def _events_at_stage(
    events: Sequence[Mapping[str, Any]], stage: str, *, promotion_id: str | None = None
) -> list[Mapping[str, Any]]:
    rows = [event for event in events if event.get("lane_stage") == stage]
    if promotion_id is None:
        return rows
    if stage == "pr_terminal":
        return [
            event
            for event in rows
            if isinstance(event.get("terminal_projection"), dict)
            and event["terminal_projection"].get("promotion_id") == promotion_id
        ]
    return [event for event in rows if _candidate_ids(event).get("promotion_id") == promotion_id]


def _target_outcomes(
    *, events: Sequence[Mapping[str, Any]], target: Mapping[str, Any]
) -> tuple[dict[str, str], list[Mapping[str, Any]], str | None, bool]:
    outcomes = {family_id: "not_reached" for family_id in FAMILY_IDS}
    patches = [
        event
        for event in _events_at_stage(events, "patch_evaluation")
        if _matches_target(event, target)
    ]
    target_events: list[Mapping[str, Any]] = list(patches)
    if len(patches) > 1:
        return (
            {family_id: "measurement_invalid" for family_id in FAMILY_IDS},
            target_events,
            None,
            False,
        )
    if not patches:
        outcomes[FAMILY_IDS[0]] = "right_censored"
        return outcomes, target_events, None, False
    patch = patches[0]
    patch_status = patch.get("status")
    if patch_status not in {"accepted", "rejected"}:
        raise CreativeCodeLifecycleBayesianShadowError("target patch status is invalid")
    outcomes[FAMILY_IDS[0]] = (
        "observed_positive" if patch_status == "accepted" else "observed_negative"
    )
    if patch_status == "rejected":
        return outcomes, target_events, None, True
    result_id = _candidate_ids(patch).get("result_id")
    plans = [
        event
        for event in _events_at_stage(events, "promotion_plan")
        if _candidate_ids(event).get("source_bundle_id") == target["source_bundle_id"]
        and _candidate_ids(event).get("selected_variant_id") == target["selected_variant_id"]
        and _candidate_ids(event).get("request_id") == target["request_id"]
        and _candidate_ids(event).get("result_id") == result_id
    ]
    target_events.extend(plans)
    if len(plans) > 1:
        outcomes[FAMILY_IDS[1]] = "measurement_invalid"
        outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, None, False
    if not plans:
        return outcomes, target_events, None, False
    plan = plans[0]
    promotion_id = _candidate_ids(plan).get("promotion_id")
    if not isinstance(promotion_id, str) or not promotion_id:
        raise CreativeCodeLifecycleBayesianShadowError(
            "target promotion plan lacks promotion identity"
        )
    validations = _events_at_stage(events, "promotion_validation", promotion_id=promotion_id)
    approvals = _events_at_stage(events, "promotion_approval", promotion_id=promotion_id)
    opens = _events_at_stage(events, "pr_open", promotion_id=promotion_id)
    terminals = _events_at_stage(events, "pr_terminal", promotion_id=promotion_id)
    if plan.get("status") != "accepted":
        target_events.extend(validations)
        target_events.extend(approvals)
        target_events.extend(opens)
        target_events.extend(terminals)
        if validations or approvals or opens or terminals:
            outcomes[FAMILY_IDS[1]] = "measurement_invalid"
            outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    target_events.extend(validations)
    target_events.extend(approvals)
    if len(validations) > 1 or len(approvals) > 1:
        outcomes[FAMILY_IDS[1]] = "measurement_invalid"
        outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    if not validations:
        if approvals or opens or terminals:
            target_events.extend(opens)
            target_events.extend(terminals)
            outcomes[FAMILY_IDS[1]] = "measurement_invalid"
            outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    if validations[0].get("status") != "accepted":
        if approvals or opens or terminals:
            target_events.extend(opens)
            target_events.extend(terminals)
            outcomes[FAMILY_IDS[1]] = "measurement_invalid"
            outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    if not approvals:
        if opens or terminals:
            target_events.extend(opens)
            target_events.extend(terminals)
            outcomes[FAMILY_IDS[1]] = "measurement_invalid"
            outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    if approvals[0].get("status") != "accepted":
        if opens or terminals:
            target_events.extend(opens)
            target_events.extend(terminals)
            outcomes[FAMILY_IDS[1]] = "measurement_invalid"
            outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    target_events.extend(opens)
    exact_opens = [event for event in opens if _candidate_ids(event).get("result_id") == result_id]
    conflicting_opens = [
        event for event in opens if _candidate_ids(event).get("result_id") != result_id
    ]
    if conflicting_opens or len(exact_opens) > 1:
        outcomes[FAMILY_IDS[1]] = "measurement_invalid"
        outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    if not exact_opens:
        if terminals:
            target_events.extend(terminals)
            outcomes[FAMILY_IDS[1]] = "measurement_invalid"
            outcomes[FAMILY_IDS[2]] = "measurement_invalid"
            return outcomes, target_events, promotion_id, False
        outcomes[FAMILY_IDS[1]] = "right_censored"
        return outcomes, target_events, promotion_id, False
    open_status = exact_opens[0].get("status")
    if open_status not in {"opened", "blocked"}:
        raise CreativeCodeLifecycleBayesianShadowError("target PR-open status is invalid")
    outcomes[FAMILY_IDS[1]] = (
        "observed_positive" if open_status == "opened" else "observed_negative"
    )
    if open_status == "blocked":
        if terminals:
            target_events.extend(terminals)
            outcomes[FAMILY_IDS[1]] = "measurement_invalid"
            outcomes[FAMILY_IDS[2]] = "measurement_invalid"
            return outcomes, target_events, promotion_id, False
        return outcomes, target_events, promotion_id, True
    target_events.extend(terminals)
    if len(terminals) > 1:
        outcomes[FAMILY_IDS[2]] = "measurement_invalid"
        return outcomes, target_events, promotion_id, False
    if not terminals:
        outcomes[FAMILY_IDS[2]] = "right_censored"
        return outcomes, target_events, promotion_id, False
    terminal_status = terminals[0].get("status")
    if terminal_status not in {"merged", "closed_unmerged"}:
        raise CreativeCodeLifecycleBayesianShadowError("target terminal status is invalid")
    outcomes[FAMILY_IDS[2]] = (
        "observed_positive" if terminal_status == "merged" else "observed_negative"
    )
    return outcomes, target_events, promotion_id, True


def score_forecast(
    *, forecast_path: Path, telemetry_dir: Path, scored_at: str
) -> tuple[Path, bool, dict[str, Any]]:
    forecast, forecast_seal, gate_path, gate, baseline = _load_forecast_sources(forecast_path)
    start, start_seal, start_path = _load_start(
        forecast=forecast, forecast_path=forecast_path, gate=gate, gate_path=gate_path
    )
    outcome_snapshot = analytics_cli.load_validated_snapshot_artifact(telemetry_dir=telemetry_dir)
    _require_baseline_subset(baseline.events, outcome_snapshot.events)
    outcomes, target_events, promotion_id, terminal_stop = _target_outcomes(
        events=outcome_snapshot.events,
        target=forecast["target"],
    )
    patch_rows = [event for event in target_events if event.get("lane_stage") == "patch_evaluation"]
    receipt: dict[str, Any] | None = None
    receipt_ref: str | None = None
    if len(patch_rows) == 1:
        receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
        _receipt_gate, receipt = cast(
            tuple[dict[str, Any], dict[str, Any]],
            generation_cli.load_validated_generation_receipt_context(
                gate_path=gate_path,
                receipt_path=receipt_path,
            ),
        )
        receipt_ref = _repo_ref(receipt_path, label="generation receipt")
        patch_event = patch_rows[0]
        if receipt["result_id"] != _candidate_ids(patch_event).get("result_id") or receipt[
            "result_fingerprint"
        ] != patch_event.get("source_fingerprint"):
            raise CreativeCodeLifecycleBayesianShadowError(
                "target patch telemetry does not match generation receipt"
            )
    elif not patch_rows:
        receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
        if receipt_path.exists() or receipt_path.is_symlink():
            raise CreativeCodeLifecycleBayesianShadowError(
                "generation receipt exists without target patch telemetry"
            )
    analytics_ref = _analytics_ref(outcome_snapshot)
    telemetry_ref = _repo_ref(
        telemetry_dir if telemetry_dir.is_absolute() else REPO_ROOT / telemetry_dir,
        label="outcome telemetry directory",
    )
    observation = {
        "analytics_id": outcome_snapshot.analytics["analytics_id"],
        "analytics_fingerprint": fingerprint_payload(cast(Any, outcome_snapshot.analytics)),
        "analytics_ref": analytics_ref,
        "telemetry_dir_ref": telemetry_ref,
        "events_fingerprint": outcome_snapshot.analytics["corpus"]["events_fingerprint"],
        "rollup_fingerprint": outcome_snapshot.analytics["corpus"]["rollup_fingerprint"],
        "event_count": outcome_snapshot.analytics["corpus"]["event_count"],
        "target_event_fingerprints": sorted({_event_fingerprint(event) for event in target_events}),
        "generation_receipt_ref": receipt_ref,
        "generation_receipt_fingerprint": (
            None if receipt is None else fingerprint_payload(cast(Any, receipt))
        ),
        "result_id": None if receipt is None else receipt["result_id"],
        "result_fingerprint": None if receipt is None else receipt["result_fingerprint"],
        "promotion_id": promotion_id,
    }
    score = build_lifecycle_forecast_score(
        forecast=forecast,
        forecast_ref=expected_forecast_ref(forecast_id=forecast["forecast_id"]),
        start=start,
        start_ref=(
            "artifacts/orchestration/creative_code/bayesian_shadow/"
            f"{forecast['forecast_id']}/{START_FILENAME}"
        ),
        outcomes=outcomes,
        observation=observation,
        scored_at=scored_at,
        terminal_stop_observed=terminal_stop,
    )

    def recheck() -> None:
        recheck_shadow_source(forecast_seal, label="shadow forecast")
        recheck_shadow_source(start_seal, label="shadow target start")
        current_forecast, _seal, current_gate_path, current_gate, current_baseline = (
            _load_forecast_sources(forecast_path)
        )
        if current_forecast != forecast or current_gate_path != gate_path or current_gate != gate:
            raise CreativeCodeLifecycleBayesianShadowError("forecast/gate changed before score")
        if current_baseline != baseline:
            raise CreativeCodeLifecycleBayesianShadowError("baseline changed before score")
        current_start, _current_start_seal, _path = _load_start(
            forecast=forecast, forecast_path=forecast_path, gate=gate, gate_path=gate_path
        )
        if current_start != start:
            raise CreativeCodeLifecycleBayesianShadowError("target start changed before score")
        current_outcome = analytics_cli.load_validated_snapshot_artifact(
            telemetry_dir=telemetry_dir
        )
        if current_outcome != outcome_snapshot:
            raise CreativeCodeLifecycleBayesianShadowError("outcome snapshot changed before score")
        if receipt is not None:
            _current_gate, current_receipt = (
                generation_cli.load_validated_generation_receipt_context(
                    gate_path=gate_path,
                    receipt_path=gate_path.parent / generation_cli.RECEIPT_FILENAME,
                )
            )
            if current_receipt != receipt:
                raise CreativeCodeLifecycleBayesianShadowError(
                    "generation receipt changed before score"
                )

    path, replayed = publish_shadow_artifact(
        shadow_root=BAYESIAN_SHADOW_ROOT,
        forecast_id=forecast["forecast_id"],
        filename=SCORE_FILENAME,
        content=canonical_shadow_bytes(score),
        recheck_sources=recheck,
    )
    return path, replayed, score


def validate_score_path(score_path: Path) -> dict[str, Any]:
    raw, score_seal = read_shadow_json(
        score_path, shadow_root=BAYESIAN_SHADOW_ROOT, label="shadow score"
    )
    score = cast(dict[str, Any], validate_lifecycle_forecast_score(raw))
    forecast_path = _resolve_repo_ref(score["forecast_ref"], label="shadow forecast")
    forecast, forecast_seal, gate_path, gate, baseline = _load_forecast_sources(forecast_path)
    start, start_seal, start_path = _load_start(
        forecast=forecast, forecast_path=forecast_path, gate=gate, gate_path=gate_path
    )
    canonical_score_path = forecast_path.parent / SCORE_FILENAME
    if score_path.resolve(strict=True) != canonical_score_path:
        raise CreativeCodeLifecycleBayesianShadowError("score is not in canonical slot")
    if score["forecast_ref"] != expected_forecast_ref(forecast_id=forecast["forecast_id"]) or score[
        "target_start_ref"
    ] != _repo_ref(start_path, label="shadow target start"):
        raise CreativeCodeLifecycleBayesianShadowError(
            "score forecast/start refs are not canonical"
        )
    validate_lifecycle_forecast_score_binding(score=score, forecast=forecast, start=start)
    outcome_dir = _resolve_repo_ref(
        score["observation"]["telemetry_dir_ref"],
        label="outcome telemetry directory",
        directory=True,
    )
    outcome = analytics_cli.load_validated_snapshot_artifact(telemetry_dir=outcome_dir)
    _require_baseline_subset(baseline.events, outcome.events)
    outcomes, target_events, promotion_id, terminal_stop = _target_outcomes(
        events=outcome.events, target=forecast["target"]
    )
    if outcomes != {row["family_id"]: row["outcome_state"] for row in score["families"]}:
        raise CreativeCodeLifecycleBayesianShadowError("stored score outcomes are stale")
    if (
        promotion_id != score["observation"]["promotion_id"]
        or terminal_stop != score["terminal_stop_observed"]
    ):
        raise CreativeCodeLifecycleBayesianShadowError("stored score target lineage is stale")
    expected_fingerprints = sorted({_event_fingerprint(event) for event in target_events})
    if expected_fingerprints != score["observation"]["target_event_fingerprints"]:
        raise CreativeCodeLifecycleBayesianShadowError("stored score event projection is stale")
    if (
        outcome.analytics["analytics_id"] != score["observation"]["analytics_id"]
        or fingerprint_payload(cast(Any, outcome.analytics))
        != score["observation"]["analytics_fingerprint"]
    ):
        raise CreativeCodeLifecycleBayesianShadowError("stored score snapshot is stale")
    corpus = outcome.analytics["corpus"]
    expected_observation = {
        "analytics_ref": _analytics_ref(outcome),
        "events_fingerprint": corpus["events_fingerprint"],
        "rollup_fingerprint": corpus["rollup_fingerprint"],
        "event_count": corpus["event_count"],
    }
    for key, expected in expected_observation.items():
        if score["observation"][key] != expected:
            raise CreativeCodeLifecycleBayesianShadowError(f"stored score {key} is stale")
    patch_rows = [event for event in target_events if event.get("lane_stage") == "patch_evaluation"]
    if len(patch_rows) == 1:
        receipt_path = gate_path.parent / generation_cli.RECEIPT_FILENAME
        _receipt_gate, receipt = generation_cli.load_validated_generation_receipt_context(
            gate_path=gate_path,
            receipt_path=receipt_path,
        )
        patch_event = patch_rows[0]
        receipt_expectations = {
            "generation_receipt_ref": _repo_ref(receipt_path, label="generation receipt"),
            "generation_receipt_fingerprint": fingerprint_payload(cast(Any, receipt)),
            "result_id": receipt["result_id"],
            "result_fingerprint": receipt["result_fingerprint"],
        }
        if receipt["result_id"] != _candidate_ids(patch_event).get("result_id") or receipt[
            "result_fingerprint"
        ] != patch_event.get("source_fingerprint"):
            raise CreativeCodeLifecycleBayesianShadowError(
                "target patch telemetry does not match generation receipt"
            )
    else:
        receipt_expectations = {
            "generation_receipt_ref": None,
            "generation_receipt_fingerprint": None,
            "result_id": None,
            "result_fingerprint": None,
        }
    for key, expected in receipt_expectations.items():
        if score["observation"][key] != expected:
            raise CreativeCodeLifecycleBayesianShadowError(f"stored score {key} is stale")
    recheck_shadow_source(forecast_seal, label="shadow forecast")
    recheck_shadow_source(start_seal, label="shadow target start")
    recheck_shadow_source(score_seal, label="shadow score")
    return score


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="creative_code_lifecycle_bayesian_shadow",
        description=(
            "Local shadow-only lifecycle forecast/scoring. It grants no routing, promotion, "
            "review, PR, merge, provider, calibration, reliability, or effectiveness claim."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build-forecast")
    build.add_argument("--telemetry-dir", type=Path, required=True)
    build.add_argument("--gate", type=Path, required=True)
    build.add_argument("--produced-at", required=True)
    validate_forecast = sub.add_parser("validate-forecast")
    validate_forecast.add_argument("--forecast", type=Path, required=True)
    validate_start = sub.add_parser("validate-start")
    validate_start.add_argument("--start", type=Path, required=True)
    score = sub.add_parser("score-forecast")
    score.add_argument("--forecast", type=Path, required=True)
    score.add_argument("--telemetry-dir", type=Path, required=True)
    score.add_argument("--scored-at", required=True)
    validate_score = sub.add_parser("validate-score")
    validate_score.add_argument("--score", type=Path, required=True)
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--forecast", type=Path, required=True)
    summarize.add_argument("--score", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "build-forecast":
            path, replayed, forecast = build_forecast(
                telemetry_dir=args.telemetry_dir,
                gate_path=args.gate,
                produced_at=args.produced_at,
            )
            print(
                f"{BUILD_SUCCESS} forecast_id={forecast['forecast_id']} replay={'identical' if replayed else 'new'}"
            )
            print(_repo_ref(path, label="forecast"))
        elif args.command == "validate-forecast":
            forecast = validate_forecast_path(args.forecast)
            print(f"{VALIDATE_FORECAST_SUCCESS} forecast_id={forecast['forecast_id']}")
        elif args.command == "validate-start":
            start = validate_start_path(args.start)
            print(f"{VALIDATE_START_SUCCESS} target_start_id={start['target_start_id']}")
        elif args.command == "score-forecast":
            path, replayed, score = score_forecast(
                forecast_path=args.forecast,
                telemetry_dir=args.telemetry_dir,
                scored_at=args.scored_at,
            )
            print(
                f"{SCORE_SUCCESS} score_id={score['score_id']} state={score['score_state']} replay={'identical' if replayed else 'new'}"
            )
            print(_repo_ref(path, label="score"))
        elif args.command == "validate-score":
            score = validate_score_path(args.score)
            print(
                f"{VALIDATE_SCORE_SUCCESS} score_id={score['score_id']} state={score['score_state']}"
            )
        else:
            forecast = validate_forecast_path(args.forecast)
            summary: dict[str, Any] = {
                "forecast_id": forecast["forecast_id"],
                "calibration_state": "not_assessed",
                "chronology_claim": "local_dependency_order_only",
                "families": [
                    {
                        "family_id": row["family_id"],
                        "observation_state": row["observation_state"],
                        "posterior_predictive_bps": row["posterior_predictive_bps"],
                    }
                    for row in forecast["families"]
                ],
                "score": None,
                "claims_predictive_skill": False,
                "claims_calibration": False,
                "claims_effectiveness": False,
            }
            if args.score is not None:
                score = validate_score_path(args.score)
                if score["forecast_id"] != forecast["forecast_id"]:
                    raise CreativeCodeLifecycleBayesianShadowError(
                        "summary score does not match forecast"
                    )
                summary["score"] = {
                    "score_id": score["score_id"],
                    "score_state": score["score_state"],
                    "families": score["families"],
                }
            print(json.dumps(summary, sort_keys=True, indent=2))
    except (
        CreativeCodeLifecycleBayesianShadowError,
        CreativeCodeLifecycleTransitionAnalyticsError,
        CreativeCodeLifecycleTransitionAnalyticsIOError,
        CreativeCodePatchContractError,
        CreativeCodePatchGenerationError,
        CreativeCodePatchWorkspaceError,
        CreativeCodeTelemetryContractError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

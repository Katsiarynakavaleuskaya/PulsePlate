"""Closed local contracts for prospective creative-code lifecycle forecasts.

This leaf module owns deterministic math, closed artifact validation, and the
cooperative local publication boundary.  It deliberately does not import the
patch-generation or lifecycle-analytics command modules.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import errno
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any, cast

from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)

SCHEMA_VERSION = "1.0"
FORECAST_ARTIFACT_TYPE = "creative_code_lifecycle_bayesian_forecast"
START_ARTIFACT_TYPE = "creative_code_lifecycle_bayesian_target_start"
SCORE_ARTIFACT_TYPE = "creative_code_lifecycle_bayesian_score"
POLICY_VERSION = "creative-code-lifecycle-bayesian-shadow-v1"
REGISTRY_VERSION = "creative-code-lifecycle-binary-families-v1"

FORECAST_FILENAME = "forecast.json"
START_FILENAME = "start.json"
SCORE_FILENAME = "score.json"
MAX_ARTIFACT_BYTES = 262_144
MAX_COUNT = 1_000_000_000_000
MAX_POSTERIOR_PARAMETER = MAX_COUNT + 1
OBSERVATION_HORIZON = timedelta(days=14)
SHADOW_ROOT_RELATIVE = PurePosixPath("artifacts/orchestration/creative_code/bayesian_shadow")

FAMILY_IDS = (
    "patch_evaluation_acceptance_v1",
    "pr_opening_v1",
    "pr_terminal_merge_v1",
)

FAMILY_SPECS: tuple[dict[str, str], ...] = (
    {
        "family_id": FAMILY_IDS[0],
        "eligibility": "exact_generation_gate_target",
        "from_stage": "specification",
        "from_status": "accepted",
        "to_stage": "patch_evaluation",
        "positive_outcome": "accepted",
        "negative_outcome": "rejected",
    },
    {
        "family_id": FAMILY_IDS[1],
        "eligibility": "promotion_approval_accepted",
        "from_stage": "promotion_approval",
        "from_status": "accepted",
        "to_stage": "pr_open",
        "positive_outcome": "opened",
        "negative_outcome": "blocked",
    },
    {
        "family_id": FAMILY_IDS[2],
        "eligibility": "pr_open_opened",
        "from_stage": "pr_open",
        "from_status": "opened",
        "to_stage": "pr_terminal",
        "positive_outcome": "merged",
        "negative_outcome": "closed_unmerged",
    },
)

OUTCOME_STATES = frozenset(
    {
        "observed_positive",
        "observed_negative",
        "not_reached",
        "right_censored",
        "measurement_invalid",
    }
)
SCORE_STATES = frozenset(
    {"fully_scored", "partially_scored", "valid_but_unscored", "measurement_invalid"}
)

AUTHORITY_KEYS = frozenset(
    {
        "shadow_only",
        "writes_local_artifacts",
        "writes_repo_tracked_state",
        "decision_authority",
        "changes_routing",
        "changes_retry_budget",
        "changes_review_roles",
        "claims_candidate_correctness",
        "claims_merge_readiness",
        "calls_product_runtime",
        "calls_provider",
        "calls_network",
        "opens_pr",
        "merges_pr",
    }
)
AUTHORITY_TRUE = frozenset({"shadow_only", "writes_local_artifacts"})
CAVEATS = (
    "fixed_reference_prior_not_empirical_probability",
    "historical_transition_attempts_not_iid_pilots",
    "local_dependency_order_not_external_preregistration",
    "calibration_reliability_and_effectiveness_not_assessed",
    "no_routing_promotion_review_or_merge_authority",
)

SHA_RE = re.compile(r"^[a-f0-9]{40}$")
FINGERPRINT_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
ASSET_ID_RE = re.compile(r"^evidence:[A-Za-z0-9_.:-]+:control_plane:1\.0:[a-f0-9]{24}$")
IDEMPOTENCY_RE = re.compile(r"^idem:[a-f0-9]{64}$")
REPO_REF_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
RFC3339_RE = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
    r"T(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]{1,6})?"
    r"(?P<offset>Z|[+-][0-9]{2}:[0-9]{2})$",
    re.ASCII,
)


class CreativeCodeLifecycleBayesianShadowError(ValueError):
    """Raised when a shadow artifact cannot remain closed and fail-closed."""


def canonical_shadow_root(repo_root: Path) -> Path:
    """Return the one fixed shadow store below a supplied repository root."""

    return Path(repo_root).joinpath(*SHADOW_ROOT_RELATIVE.parts)


@dataclass(frozen=True)
class ShadowSourceSeal:
    path: Path
    device: int
    inode: int
    mode: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int


def default_shadow_authority() -> dict[str, bool]:
    return {key: key in AUTHORITY_TRUE for key in sorted(AUTHORITY_KEYS)}


def round_half_up_ratio(numerator: int, denominator: int) -> int:
    """Round one non-negative rational to the nearest integer, ties upward."""

    if isinstance(numerator, bool) or not isinstance(numerator, int) or numerator < 0:
        raise CreativeCodeLifecycleBayesianShadowError("numerator must be non-negative integer")
    if isinstance(denominator, bool) or not isinstance(denominator, int) or denominator <= 0:
        raise CreativeCodeLifecycleBayesianShadowError("denominator must be positive integer")
    return (2 * numerator + denominator) // (2 * denominator)


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise CreativeCodeLifecycleBayesianShadowError(
            f"{label} has invalid keys; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _object(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must be an object")
    return value


def _integer(value: Any, *, label: str, maximum: int = MAX_COUNT) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must be a bounded integer")
    return cast(int, value)


def _safe_id(value: Any, *, label: str, asset: bool = False) -> str:
    pattern = ASSET_ID_RE if asset else SAFE_ID_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is invalid")
    return value


def _fingerprint(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not FINGERPRINT_RE.fullmatch(value):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is invalid")
    return value


def _repo_ref(value: Any, *, label: str, suffix: str = ".json") -> str:
    if not isinstance(value, str) or not value or len(value) > 768 or "\\" in value:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is invalid")
    prefix = "artifacts/orchestration/creative_code/"
    if not value.startswith(prefix) or not value.endswith(suffix):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is invalid")
    parts = value[len(prefix) :].split("/")
    if any(
        part in {"", ".", ".."} or REPO_REF_SEGMENT_RE.fullmatch(part) is None for part in parts
    ):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} is invalid")
    return value


def normalize_rfc3339(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 40
        or RFC3339_RE.fullmatch(value) is None
        or value.endswith("-00:00")
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            f"{label} must use strict extended ASCII RFC3339 with a known offset"
        )
    try:
        parsed = datetime.fromisoformat(
            value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
        )
        offset = parsed.utcoffset()
        if parsed.tzinfo is None or offset is None:
            raise ValueError("missing offset")
        normalized = parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must be valid RFC3339") from exc
    text = (
        f"{normalized.year:04d}-{normalized.month:02d}-{normalized.day:02d}"
        f"T{normalized.hour:02d}:{normalized.minute:02d}:{normalized.second:02d}"
    )
    if normalized.microsecond:
        text += f".{normalized.microsecond:06d}".rstrip("0")
    return text + "Z"


def _parse_canonical_time(value: Any, *, label: str) -> datetime:
    normalized = normalize_rfc3339(value, label=label)
    if value != normalized:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must use canonical UTC form")
    return datetime.fromisoformat(normalized.removesuffix("Z") + "+00:00")


TARGET_KEYS = frozenset(
    {
        "target_fingerprint",
        "generation_gate_id",
        "generation_gate_fingerprint",
        "generation_gate_ref",
        "admission_id",
        "admission_fingerprint",
        "admission_ref",
        "request_id",
        "request_fingerprint",
        "request_ref",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "source_bundle_ref",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "base_commit_sha",
        "run_id",
        "state_fingerprint",
    }
)


def _target_from_gate(gate: Mapping[str, Any], *, gate_ref: str) -> dict[str, Any]:
    fields = {
        "generation_gate_id": _safe_id(gate.get("gate_id"), label="gate.gate_id", asset=True),
        "generation_gate_fingerprint": fingerprint_payload(cast(Any, dict(gate))),
        "generation_gate_ref": _repo_ref(gate_ref, label="generation_gate_ref"),
        "admission_id": _safe_id(gate.get("admission_id"), label="gate.admission_id"),
        "admission_fingerprint": _fingerprint(
            gate.get("admission_fingerprint"), label="gate.admission_fingerprint"
        ),
        "admission_ref": _repo_ref(gate.get("admission_ref"), label="gate.admission_ref"),
        "request_id": _safe_id(gate.get("request_id"), label="gate.request_id"),
        "request_fingerprint": _fingerprint(
            gate.get("request_fingerprint"), label="gate.request_fingerprint"
        ),
        "request_ref": _repo_ref(gate.get("request_ref"), label="gate.request_ref"),
        "source_bundle_id": _safe_id(gate.get("source_bundle_id"), label="gate.source_bundle_id"),
        "source_bundle_fingerprint": _fingerprint(
            gate.get("source_bundle_fingerprint"), label="gate.source_bundle_fingerprint"
        ),
        "source_bundle_ref": _repo_ref(
            gate.get("source_bundle_ref"), label="gate.source_bundle_ref"
        ),
        "selected_variant_id": _safe_id(
            gate.get("selected_variant_id"), label="gate.selected_variant_id"
        ),
        "selected_variant_fingerprint": _fingerprint(
            gate.get("selected_variant_fingerprint"), label="gate.selected_variant_fingerprint"
        ),
        "base_commit_sha": gate.get("base_commit_sha"),
        "run_id": _safe_id(gate.get("run_id"), label="gate.run_id"),
        "state_fingerprint": _fingerprint(
            gate.get("state_fingerprint"), label="gate.state_fingerprint"
        ),
    }
    if not isinstance(fields["base_commit_sha"], str) or not SHA_RE.fullmatch(
        fields["base_commit_sha"]
    ):
        raise CreativeCodeLifecycleBayesianShadowError("gate.base_commit_sha is invalid")
    fields["target_fingerprint"] = fingerprint_payload(cast(Any, fields))
    return {key: fields[key] for key in sorted(fields)}


def _normalize_target(value: Any) -> dict[str, Any]:
    target = _object(value, label="target")
    _exact_keys(target, TARGET_KEYS, label="target")
    synthetic_gate = {
        "gate_id": target["generation_gate_id"],
        "admission_id": target["admission_id"],
        "admission_fingerprint": target["admission_fingerprint"],
        "admission_ref": target["admission_ref"],
        "request_id": target["request_id"],
        "request_fingerprint": target["request_fingerprint"],
        "request_ref": target["request_ref"],
        "source_bundle_id": target["source_bundle_id"],
        "source_bundle_fingerprint": target["source_bundle_fingerprint"],
        "source_bundle_ref": target["source_bundle_ref"],
        "selected_variant_id": target["selected_variant_id"],
        "selected_variant_fingerprint": target["selected_variant_fingerprint"],
        "base_commit_sha": target["base_commit_sha"],
        "run_id": target["run_id"],
        "state_fingerprint": target["state_fingerprint"],
    }
    normalized = _target_from_gate(
        synthetic_gate,
        gate_ref=cast(str, target["generation_gate_ref"]),
    )
    normalized["generation_gate_fingerprint"] = _fingerprint(
        target["generation_gate_fingerprint"], label="target.generation_gate_fingerprint"
    )
    identity_body = {key: normalized[key] for key in normalized if key != "target_fingerprint"}
    normalized["target_fingerprint"] = fingerprint_payload(cast(Any, identity_body))
    if target["target_fingerprint"] != normalized["target_fingerprint"]:
        raise CreativeCodeLifecycleBayesianShadowError("target_fingerprint does not match target")
    return {key: normalized[key] for key in sorted(normalized)}


BASELINE_KEYS = frozenset(
    {
        "analytics_id",
        "analytics_fingerprint",
        "analytics_ref",
        "telemetry_dir_ref",
        "events_fingerprint",
        "rollup_fingerprint",
        "event_count",
    }
)


def _baseline_from_analytics(
    analytics: Mapping[str, Any], *, analytics_ref: str, telemetry_dir_ref: str
) -> dict[str, Any]:
    corpus = _object(analytics.get("corpus"), label="analytics.corpus")
    return {
        "analytics_id": _safe_id(
            analytics.get("analytics_id"), label="analytics.analytics_id", asset=True
        ),
        "analytics_fingerprint": fingerprint_payload(cast(Any, dict(analytics))),
        "analytics_ref": _repo_ref(analytics_ref, label="analytics_ref"),
        "telemetry_dir_ref": _repo_ref(telemetry_dir_ref, label="telemetry_dir_ref", suffix=""),
        "events_fingerprint": _fingerprint(
            corpus.get("events_fingerprint"), label="analytics.corpus.events_fingerprint"
        ),
        "rollup_fingerprint": _fingerprint(
            corpus.get("rollup_fingerprint"), label="analytics.corpus.rollup_fingerprint"
        ),
        "event_count": _integer(corpus.get("event_count"), label="analytics.corpus.event_count"),
    }


FORECAST_FAMILY_KEYS = frozenset(
    {
        "family_id",
        "eligibility",
        "positive_outcome",
        "negative_outcome",
        "positive_outcome_count",
        "negative_outcome_count",
        "effective_observation_count",
        "censored_eligible_count",
        "unmatched_destination_count",
        "posterior_alpha",
        "posterior_beta",
        "posterior_predictive_bps",
        "observation_state",
    }
)


def _transition_count(analytics: Mapping[str, Any], spec: Mapping[str, str], status: str) -> int:
    rows = analytics.get("transition_counts")
    if not isinstance(rows, list):
        raise CreativeCodeLifecycleBayesianShadowError("analytics.transition_counts must be array")
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("from_stage") == spec["from_stage"]
        and row.get("from_status") == spec["from_status"]
        and row.get("to_stage") == spec["to_stage"]
        and row.get("to_status") == status
    ]
    if len(matches) > 1:
        raise CreativeCodeLifecycleBayesianShadowError("duplicate analytics transition row")
    return 0 if not matches else _integer(matches[0].get("count"), label="transition count")


def _build_family_rows(analytics: Mapping[str, Any]) -> list[dict[str, Any]]:
    lineage = _object(analytics.get("lineage_accounting"), label="analytics.lineage_accounting")
    censored_by_stage = _object(
        lineage.get("unobserved_successors_by_stage"),
        label="analytics.lineage_accounting.unobserved_successors_by_stage",
    )
    unmatched_by_stage = _object(
        lineage.get("unobserved_predecessors_by_stage"),
        label="analytics.lineage_accounting.unobserved_predecessors_by_stage",
    )
    rows: list[dict[str, Any]] = []
    for spec in FAMILY_SPECS:
        positive = _transition_count(analytics, spec, spec["positive_outcome"])
        negative = _transition_count(analytics, spec, spec["negative_outcome"])
        alpha = 1 + positive
        beta = 1 + negative
        rows.append(
            {
                "family_id": spec["family_id"],
                "eligibility": spec["eligibility"],
                "positive_outcome": spec["positive_outcome"],
                "negative_outcome": spec["negative_outcome"],
                "positive_outcome_count": positive,
                "negative_outcome_count": negative,
                "effective_observation_count": positive + negative,
                "censored_eligible_count": _integer(
                    censored_by_stage.get(spec["from_stage"]),
                    label=f"unobserved successors for {spec['from_stage']}",
                ),
                "unmatched_destination_count": _integer(
                    unmatched_by_stage.get(spec["to_stage"]),
                    label=f"unobserved predecessors for {spec['to_stage']}",
                ),
                "posterior_alpha": alpha,
                "posterior_beta": beta,
                "posterior_predictive_bps": round_half_up_ratio(10_000 * alpha, alpha + beta),
                "observation_state": "prior_only" if positive + negative == 0 else "observed",
            }
        )
    return rows


FORECAST_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "registry_version",
        "forecast_id",
        "idempotency_key",
        "produced_at",
        "observation_cutoff_at",
        "baseline",
        "target",
        "families",
        "calibration_state",
        "chronology_claim",
        "authority",
        "caveats",
        "sanitized",
    }
)


def _forecast_identity(payload: Mapping[str, Any]) -> tuple[str, str]:
    target = cast(Mapping[str, Any], payload["target"])
    slot_fingerprint = fingerprint_payload(
        cast(
            Any,
            {
                "policy_version": POLICY_VERSION,
                "registry_version": REGISTRY_VERSION,
                "target_fingerprint": target["target_fingerprint"],
            },
        )
    )
    content_fingerprint = fingerprint_payload(
        cast(
            Any,
            {
                key: payload[key]
                for key in sorted(FORECAST_KEYS - {"forecast_id", "idempotency_key"})
            },
        )
    )
    upstream = (cast(str, target["generation_gate_id"]), cast(str, target["target_fingerprint"]))
    return (
        build_asset_id(
            asset_type=FORECAST_ARTIFACT_TYPE,
            rail="control_plane",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=slot_fingerprint,
            upstream_ids=upstream,
        ),
        build_idempotency_key(
            asset_type=FORECAST_ARTIFACT_TYPE,
            rail="control_plane",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=content_fingerprint,
            upstream_ids=upstream,
        ),
    )


def build_lifecycle_forecast(
    *,
    analytics: Mapping[str, Any],
    analytics_ref: str,
    telemetry_dir_ref: str,
    gate: Mapping[str, Any],
    gate_ref: str,
    produced_at: str,
) -> dict[str, Any]:
    produced = normalize_rfc3339(produced_at, label="produced_at")
    try:
        cutoff = datetime.fromisoformat(produced.removesuffix("Z") + "+00:00") + OBSERVATION_HORIZON
    except (OverflowError, ValueError) as exc:
        raise CreativeCodeLifecycleBayesianShadowError(
            "observation cutoff cannot be represented"
        ) from exc
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": FORECAST_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "registry_version": REGISTRY_VERSION,
        "forecast_id": "pending",
        "idempotency_key": "pending",
        "produced_at": produced,
        "observation_cutoff_at": normalize_rfc3339(cutoff.isoformat(), label="cutoff"),
        "baseline": _baseline_from_analytics(
            analytics,
            analytics_ref=analytics_ref,
            telemetry_dir_ref=telemetry_dir_ref,
        ),
        "target": _target_from_gate(gate, gate_ref=gate_ref),
        "families": _build_family_rows(analytics),
        "calibration_state": "not_assessed",
        "chronology_claim": "local_dependency_order_only",
        "authority": default_shadow_authority(),
        "caveats": list(CAVEATS),
        "sanitized": True,
    }
    payload["forecast_id"], payload["idempotency_key"] = _forecast_identity(payload)
    return validate_lifecycle_forecast(payload)


def validate_lifecycle_forecast(payload: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(payload, FORECAST_KEYS, label="forecast")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise CreativeCodeLifecycleBayesianShadowError("unsupported forecast schema_version")
    if payload.get("artifact_type") != FORECAST_ARTIFACT_TYPE:
        raise CreativeCodeLifecycleBayesianShadowError("unsupported forecast artifact_type")
    if (
        payload.get("policy_version") != POLICY_VERSION
        or payload.get("registry_version") != REGISTRY_VERSION
    ):
        raise CreativeCodeLifecycleBayesianShadowError("unsupported forecast policy")
    produced = _parse_canonical_time(payload.get("produced_at"), label="produced_at")
    cutoff = _parse_canonical_time(
        payload.get("observation_cutoff_at"), label="observation_cutoff_at"
    )
    if cutoff - produced != OBSERVATION_HORIZON:
        raise CreativeCodeLifecycleBayesianShadowError(
            "observation cutoff must be produced_at plus 14 days"
        )
    baseline = _object(payload.get("baseline"), label="baseline")
    _exact_keys(baseline, BASELINE_KEYS, label="baseline")
    normalized_baseline = {
        "analytics_id": _safe_id(
            baseline["analytics_id"], label="baseline.analytics_id", asset=True
        ),
        "analytics_fingerprint": _fingerprint(
            baseline["analytics_fingerprint"], label="baseline.analytics_fingerprint"
        ),
        "analytics_ref": _repo_ref(baseline["analytics_ref"], label="baseline.analytics_ref"),
        "telemetry_dir_ref": _repo_ref(
            baseline["telemetry_dir_ref"], label="baseline.telemetry_dir_ref", suffix=""
        ),
        "events_fingerprint": _fingerprint(
            baseline["events_fingerprint"], label="baseline.events_fingerprint"
        ),
        "rollup_fingerprint": _fingerprint(
            baseline["rollup_fingerprint"], label="baseline.rollup_fingerprint"
        ),
        "event_count": _integer(baseline["event_count"], label="baseline.event_count"),
    }
    target = _normalize_target(payload.get("target"))
    raw_families = payload.get("families")
    if not isinstance(raw_families, list) or len(raw_families) != len(FAMILY_SPECS):
        raise CreativeCodeLifecycleBayesianShadowError(
            "forecast must contain exactly three families"
        )
    families: list[dict[str, Any]] = []
    for index, (raw, spec) in enumerate(zip(raw_families, FAMILY_SPECS, strict=True)):
        row = _object(raw, label=f"families[{index}]")
        _exact_keys(row, FORECAST_FAMILY_KEYS, label=f"families[{index}]")
        for key in ("family_id", "eligibility", "positive_outcome", "negative_outcome"):
            if row.get(key) != spec[key]:
                raise CreativeCodeLifecycleBayesianShadowError(
                    f"families[{index}].{key} is invalid"
                )
        positive = _integer(row["positive_outcome_count"], label="positive_outcome_count")
        negative = _integer(row["negative_outcome_count"], label="negative_outcome_count")
        effective = _integer(
            row["effective_observation_count"], label="effective_observation_count"
        )
        alpha = _integer(
            row["posterior_alpha"],
            label="posterior_alpha",
            maximum=MAX_POSTERIOR_PARAMETER,
        )
        beta = _integer(
            row["posterior_beta"],
            label="posterior_beta",
            maximum=MAX_POSTERIOR_PARAMETER,
        )
        bps = _integer(
            row["posterior_predictive_bps"], label="posterior_predictive_bps", maximum=10_000
        )
        if effective != positive + negative or alpha != 1 + positive or beta != 1 + negative:
            raise CreativeCodeLifecycleBayesianShadowError(
                "family posterior arithmetic is inconsistent"
            )
        if bps != round_half_up_ratio(10_000 * alpha, alpha + beta):
            raise CreativeCodeLifecycleBayesianShadowError("family posterior bps is inconsistent")
        state = row.get("observation_state")
        if state != ("prior_only" if effective == 0 else "observed"):
            raise CreativeCodeLifecycleBayesianShadowError(
                "family observation_state is inconsistent"
            )
        families.append(
            {
                "family_id": spec["family_id"],
                "eligibility": spec["eligibility"],
                "positive_outcome": spec["positive_outcome"],
                "negative_outcome": spec["negative_outcome"],
                "positive_outcome_count": positive,
                "negative_outcome_count": negative,
                "effective_observation_count": effective,
                "censored_eligible_count": _integer(
                    row["censored_eligible_count"], label="censored_eligible_count"
                ),
                "unmatched_destination_count": _integer(
                    row["unmatched_destination_count"], label="unmatched_destination_count"
                ),
                "posterior_alpha": alpha,
                "posterior_beta": beta,
                "posterior_predictive_bps": bps,
                "observation_state": cast(str, state),
            }
        )
    authority = _object(payload.get("authority"), label="authority")
    _exact_keys(authority, AUTHORITY_KEYS, label="authority")
    if dict(authority) != default_shadow_authority():
        raise CreativeCodeLifecycleBayesianShadowError("forecast authority is invalid")
    if payload.get("calibration_state") != "not_assessed":
        raise CreativeCodeLifecycleBayesianShadowError("calibration_state must be not_assessed")
    if payload.get("chronology_claim") != "local_dependency_order_only":
        raise CreativeCodeLifecycleBayesianShadowError("chronology_claim is invalid")
    if payload.get("caveats") != list(CAVEATS) or payload.get("sanitized") is not True:
        raise CreativeCodeLifecycleBayesianShadowError(
            "forecast caveats or sanitized marker invalid"
        )
    normalized: dict[str, Any] = {
        **{key: payload[key] for key in FORECAST_KEYS},
        "baseline": normalized_baseline,
        "target": target,
        "families": families,
        "authority": default_shadow_authority(),
    }
    expected_id, expected_idempotency = _forecast_identity(normalized)
    if payload.get("forecast_id") != expected_id or not ASSET_ID_RE.fullmatch(
        str(payload.get("forecast_id", ""))
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            "forecast_id does not match forecast target slot"
        )
    if payload.get("idempotency_key") != expected_idempotency or not IDEMPOTENCY_RE.fullmatch(
        str(payload.get("idempotency_key", ""))
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            "forecast idempotency_key does not match content"
        )
    return {key: normalized[key] for key in sorted(normalized)}


START_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "target_start_id",
        "idempotency_key",
        "forecast_id",
        "forecast_fingerprint",
        "forecast_ref",
        "target_fingerprint",
        "generation_gate_id",
        "generation_gate_fingerprint",
        "generation_gate_ref",
        "started_at",
        "calibration_state",
        "chronology_claim",
        "authority",
        "sanitized",
    }
)


def _generic_identity(
    payload: Mapping[str, Any], *, id_key: str, artifact_type: str, keys: frozenset[str]
) -> tuple[str, str]:
    fingerprint = fingerprint_payload(
        cast(Any, {key: payload[key] for key in sorted(keys - {id_key, "idempotency_key"})})
    )
    upstream = (
        str(payload.get("forecast_id", "")),
        str(payload.get("target_fingerprint", "")),
        str(payload.get("generation_gate_id", "")),
    )
    return (
        build_asset_id(
            asset_type=artifact_type,
            rail="control_plane",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=fingerprint,
            upstream_ids=upstream,
        ),
        build_idempotency_key(
            asset_type=artifact_type,
            rail="control_plane",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=fingerprint,
            upstream_ids=upstream,
        ),
    )


def build_target_start(
    *,
    forecast: Mapping[str, Any],
    forecast_ref: str,
    gate: Mapping[str, Any],
    gate_ref: str,
    started_at: str,
) -> dict[str, Any]:
    normalized_forecast = validate_lifecycle_forecast(forecast)
    expected_target = _target_from_gate(gate, gate_ref=gate_ref)
    if normalized_forecast["target"] != expected_target:
        raise CreativeCodeLifecycleBayesianShadowError(
            "forecast target does not match generation gate"
        )
    started = normalize_rfc3339(started_at, label="started_at")
    if _parse_canonical_time(started, label="started_at") <= _parse_canonical_time(
        normalized_forecast["produced_at"], label="produced_at"
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            "started_at must be after forecast produced_at"
        )
    if _parse_canonical_time(started, label="started_at") > _parse_canonical_time(
        normalized_forecast["observation_cutoff_at"], label="observation_cutoff_at"
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            "started_at must not be after observation cutoff"
        )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": START_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "target_start_id": "pending",
        "idempotency_key": "pending",
        "forecast_id": normalized_forecast["forecast_id"],
        "forecast_fingerprint": fingerprint_payload(cast(Any, normalized_forecast)),
        "forecast_ref": _repo_ref(forecast_ref, label="forecast_ref"),
        "target_fingerprint": expected_target["target_fingerprint"],
        "generation_gate_id": expected_target["generation_gate_id"],
        "generation_gate_fingerprint": expected_target["generation_gate_fingerprint"],
        "generation_gate_ref": expected_target["generation_gate_ref"],
        "started_at": started,
        "calibration_state": "not_assessed",
        "chronology_claim": "local_dependency_order_only",
        "authority": default_shadow_authority(),
        "sanitized": True,
    }
    payload["target_start_id"], payload["idempotency_key"] = _generic_identity(
        payload, id_key="target_start_id", artifact_type=START_ARTIFACT_TYPE, keys=START_KEYS
    )
    return validate_target_start(payload)


def validate_target_start(payload: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(payload, START_KEYS, label="target_start")
    constants = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": START_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "calibration_state": "not_assessed",
        "chronology_claim": "local_dependency_order_only",
        "sanitized": True,
    }
    for key, expected in constants.items():
        if payload.get(key) != expected:
            raise CreativeCodeLifecycleBayesianShadowError(f"target_start.{key} is invalid")
    _safe_id(payload.get("forecast_id"), label="target_start.forecast_id", asset=True)
    _fingerprint(payload.get("forecast_fingerprint"), label="target_start.forecast_fingerprint")
    _repo_ref(payload.get("forecast_ref"), label="target_start.forecast_ref")
    _fingerprint(payload.get("target_fingerprint"), label="target_start.target_fingerprint")
    _safe_id(payload.get("generation_gate_id"), label="target_start.generation_gate_id", asset=True)
    _fingerprint(
        payload.get("generation_gate_fingerprint"), label="target_start.generation_gate_fingerprint"
    )
    _repo_ref(payload.get("generation_gate_ref"), label="target_start.generation_gate_ref")
    _parse_canonical_time(payload.get("started_at"), label="target_start.started_at")
    authority = _object(payload.get("authority"), label="target_start.authority")
    _exact_keys(authority, AUTHORITY_KEYS, label="target_start.authority")
    if dict(authority) != default_shadow_authority():
        raise CreativeCodeLifecycleBayesianShadowError("target_start authority is invalid")
    expected_id, expected_idempotency = _generic_identity(
        payload, id_key="target_start_id", artifact_type=START_ARTIFACT_TYPE, keys=START_KEYS
    )
    if (
        payload.get("target_start_id") != expected_id
        or payload.get("idempotency_key") != expected_idempotency
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            "target_start identity does not match content"
        )
    return {key: payload[key] for key in sorted(payload)}


def validate_target_start_binding(
    *,
    start: Mapping[str, Any],
    forecast: Mapping[str, Any],
    forecast_ref: str,
    gate: Mapping[str, Any],
    gate_ref: str,
) -> dict[str, Any]:
    """Cross-bind one stored start to the exact forecast and generation gate."""

    normalized_start = validate_target_start(start)
    normalized_forecast = validate_lifecycle_forecast(forecast)
    expected = build_target_start(
        forecast=normalized_forecast,
        forecast_ref=forecast_ref,
        gate=gate,
        gate_ref=gate_ref,
        started_at=normalized_start["started_at"],
    )
    if normalized_start != expected:
        raise CreativeCodeLifecycleBayesianShadowError(
            "target start does not bind the exact forecast and generation gate"
        )
    return normalized_start


OBSERVATION_KEYS = frozenset(
    {
        "analytics_id",
        "analytics_fingerprint",
        "analytics_ref",
        "telemetry_dir_ref",
        "events_fingerprint",
        "rollup_fingerprint",
        "event_count",
        "target_event_fingerprints",
        "generation_receipt_ref",
        "generation_receipt_fingerprint",
        "result_id",
        "result_fingerprint",
        "promotion_id",
    }
)
SCORE_FAMILY_KEYS = frozenset(
    {"family_id", "outcome_state", "forecast_bps", "actual_bps", "realized_brier_loss_ppm"}
)
SCORE_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "score_id",
        "idempotency_key",
        "forecast_id",
        "forecast_fingerprint",
        "forecast_ref",
        "target_fingerprint",
        "target_start_id",
        "target_start_fingerprint",
        "target_start_ref",
        "scored_at",
        "terminal_stop_observed",
        "observation",
        "families",
        "score_state",
        "calibration_state",
        "chronology_claim",
        "authority",
        "caveats",
        "sanitized",
    }
)


def _normalize_observation(value: Any) -> dict[str, Any]:
    observation = _object(value, label="observation")
    _exact_keys(observation, OBSERVATION_KEYS, label="observation")
    event_fingerprints = observation.get("target_event_fingerprints")
    if (
        not isinstance(event_fingerprints, list)
        or any(
            not isinstance(item, str) or not FINGERPRINT_RE.fullmatch(item)
            for item in event_fingerprints
        )
        or event_fingerprints != sorted(set(event_fingerprints))
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            "observation.target_event_fingerprints must be sorted unique fingerprints"
        )
    nullable_pairs = (
        ("generation_receipt_ref", "generation_receipt_fingerprint"),
        ("result_id", "result_fingerprint"),
    )
    for left, right in nullable_pairs:
        if (observation.get(left) is None) != (observation.get(right) is None):
            raise CreativeCodeLifecycleBayesianShadowError(f"observation {left}/{right} must pair")
    receipt_ref = observation.get("generation_receipt_ref")
    receipt_fingerprint = observation.get("generation_receipt_fingerprint")
    result_id = observation.get("result_id")
    result_fingerprint = observation.get("result_fingerprint")
    promotion_id = observation.get("promotion_id")
    return {
        "analytics_id": _safe_id(
            observation.get("analytics_id"), label="observation.analytics_id", asset=True
        ),
        "analytics_fingerprint": _fingerprint(
            observation.get("analytics_fingerprint"), label="observation.analytics_fingerprint"
        ),
        "analytics_ref": _repo_ref(
            observation.get("analytics_ref"), label="observation.analytics_ref"
        ),
        "telemetry_dir_ref": _repo_ref(
            observation.get("telemetry_dir_ref"),
            label="observation.telemetry_dir_ref",
            suffix="",
        ),
        "events_fingerprint": _fingerprint(
            observation.get("events_fingerprint"), label="observation.events_fingerprint"
        ),
        "rollup_fingerprint": _fingerprint(
            observation.get("rollup_fingerprint"), label="observation.rollup_fingerprint"
        ),
        "event_count": _integer(observation.get("event_count"), label="observation.event_count"),
        "target_event_fingerprints": list(event_fingerprints),
        "generation_receipt_ref": (
            None if receipt_ref is None else _repo_ref(receipt_ref, label="generation_receipt_ref")
        ),
        "generation_receipt_fingerprint": (
            None
            if receipt_fingerprint is None
            else _fingerprint(receipt_fingerprint, label="generation_receipt_fingerprint")
        ),
        "result_id": (
            None if result_id is None else _safe_id(result_id, label="result_id", asset=True)
        ),
        "result_fingerprint": (
            None
            if result_fingerprint is None
            else _fingerprint(result_fingerprint, label="result_fingerprint")
        ),
        "promotion_id": (
            None if promotion_id is None else _safe_id(promotion_id, label="promotion_id")
        ),
    }


def _score_state(rows: Sequence[Mapping[str, Any]]) -> str:
    states = [row["outcome_state"] for row in rows]
    if "measurement_invalid" in states:
        return "measurement_invalid"
    observed = sum(state in {"observed_positive", "observed_negative"} for state in states)
    if observed == len(FAMILY_IDS):
        return "fully_scored"
    if observed:
        return "partially_scored"
    return "valid_but_unscored"


def build_lifecycle_forecast_score(
    *,
    forecast: Mapping[str, Any],
    forecast_ref: str,
    start: Mapping[str, Any],
    start_ref: str,
    outcomes: Mapping[str, str],
    observation: Mapping[str, Any],
    scored_at: str,
    terminal_stop_observed: bool,
) -> dict[str, Any]:
    normalized_forecast = validate_lifecycle_forecast(forecast)
    normalized_start = validate_target_start(start)
    if set(outcomes) != set(FAMILY_IDS) or any(
        state not in OUTCOME_STATES for state in outcomes.values()
    ):
        raise CreativeCodeLifecycleBayesianShadowError("outcomes must cover exactly three families")
    if normalized_start["forecast_id"] != normalized_forecast["forecast_id"]:
        raise CreativeCodeLifecycleBayesianShadowError("target start does not match forecast")
    if normalized_start["forecast_fingerprint"] != fingerprint_payload(
        cast(Any, normalized_forecast)
    ):
        raise CreativeCodeLifecycleBayesianShadowError("target start forecast fingerprint mismatch")
    scored = normalize_rfc3339(scored_at, label="scored_at")
    scored_time = _parse_canonical_time(scored, label="scored_at")
    if scored_time <= _parse_canonical_time(normalized_start["started_at"], label="started_at"):
        raise CreativeCodeLifecycleBayesianShadowError("scored_at must be after started_at")
    if not isinstance(terminal_stop_observed, bool):
        raise CreativeCodeLifecycleBayesianShadowError("terminal_stop_observed must be boolean")
    cutoff_time = _parse_canonical_time(
        normalized_forecast["observation_cutoff_at"], label="observation_cutoff_at"
    )
    if not terminal_stop_observed and scored_time != cutoff_time:
        raise CreativeCodeLifecycleBayesianShadowError(
            "nonterminal score must use the exact observation cutoff"
        )
    if scored_time > cutoff_time:
        raise CreativeCodeLifecycleBayesianShadowError(
            "scored_at must not be after observation cutoff"
        )
    rows: list[dict[str, Any]] = []
    forecast_by_id = {row["family_id"]: row for row in normalized_forecast["families"]}
    for family_id in FAMILY_IDS:
        state = outcomes[family_id]
        bps = cast(int, forecast_by_id[family_id]["posterior_predictive_bps"])
        actual: int | None = None
        loss: int | None = None
        if state == "observed_positive":
            actual = 10_000
        elif state == "observed_negative":
            actual = 0
        if actual is not None:
            loss = round_half_up_ratio((bps - actual) ** 2 * 1_000_000, 10_000**2)
        rows.append(
            {
                "family_id": family_id,
                "outcome_state": state,
                "forecast_bps": bps,
                "actual_bps": actual,
                "realized_brier_loss_ppm": loss,
            }
        )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": SCORE_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "score_id": "pending",
        "idempotency_key": "pending",
        "forecast_id": normalized_forecast["forecast_id"],
        "forecast_fingerprint": fingerprint_payload(cast(Any, normalized_forecast)),
        "forecast_ref": _repo_ref(forecast_ref, label="forecast_ref"),
        "target_fingerprint": normalized_forecast["target"]["target_fingerprint"],
        "target_start_id": normalized_start["target_start_id"],
        "target_start_fingerprint": fingerprint_payload(cast(Any, normalized_start)),
        "target_start_ref": _repo_ref(start_ref, label="target_start_ref"),
        "scored_at": scored,
        "terminal_stop_observed": terminal_stop_observed,
        "observation": _normalize_observation(observation),
        "families": rows,
        "score_state": _score_state(rows),
        "calibration_state": "not_assessed",
        "chronology_claim": "local_dependency_order_only",
        "authority": default_shadow_authority(),
        "caveats": list(CAVEATS),
        "sanitized": True,
    }
    payload["score_id"], payload["idempotency_key"] = _generic_identity(
        payload, id_key="score_id", artifact_type=SCORE_ARTIFACT_TYPE, keys=SCORE_KEYS
    )
    return validate_lifecycle_forecast_score(payload)


def validate_lifecycle_forecast_score(payload: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(payload, SCORE_KEYS, label="score")
    constants = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": SCORE_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "calibration_state": "not_assessed",
        "chronology_claim": "local_dependency_order_only",
        "sanitized": True,
    }
    for key, expected in constants.items():
        if payload.get(key) != expected:
            raise CreativeCodeLifecycleBayesianShadowError(f"score.{key} is invalid")
    for key, asset in (("forecast_id", True), ("target_start_id", True)):
        _safe_id(payload.get(key), label=f"score.{key}", asset=asset)
    for key in ("forecast_fingerprint", "target_fingerprint", "target_start_fingerprint"):
        _fingerprint(payload.get(key), label=f"score.{key}")
    _repo_ref(payload.get("forecast_ref"), label="score.forecast_ref")
    _repo_ref(payload.get("target_start_ref"), label="score.target_start_ref")
    _parse_canonical_time(payload.get("scored_at"), label="score.scored_at")
    if not isinstance(payload.get("terminal_stop_observed"), bool):
        raise CreativeCodeLifecycleBayesianShadowError("terminal_stop_observed must be boolean")
    observation = _normalize_observation(payload.get("observation"))
    raw_rows = payload.get("families")
    if not isinstance(raw_rows, list) or len(raw_rows) != len(FAMILY_IDS):
        raise CreativeCodeLifecycleBayesianShadowError("score must contain exactly three families")
    rows: list[dict[str, Any]] = []
    for index, (raw, family_id) in enumerate(zip(raw_rows, FAMILY_IDS, strict=True)):
        row = _object(raw, label=f"score.families[{index}]")
        _exact_keys(row, SCORE_FAMILY_KEYS, label=f"score.families[{index}]")
        if row.get("family_id") != family_id or row.get("outcome_state") not in OUTCOME_STATES:
            raise CreativeCodeLifecycleBayesianShadowError("score family identity/state invalid")
        bps = _integer(row.get("forecast_bps"), label="forecast_bps", maximum=10_000)
        state = cast(str, row["outcome_state"])
        expected_actual = (
            10_000 if state == "observed_positive" else 0 if state == "observed_negative" else None
        )
        expected_loss = (
            None
            if expected_actual is None
            else round_half_up_ratio((bps - expected_actual) ** 2 * 1_000_000, 10_000**2)
        )
        if (
            row.get("actual_bps") != expected_actual
            or row.get("realized_brier_loss_ppm") != expected_loss
        ):
            raise CreativeCodeLifecycleBayesianShadowError("score family Brier arithmetic invalid")
        rows.append(dict(row))
    expected_state = _score_state(rows)
    if payload.get("score_state") != expected_state or expected_state not in SCORE_STATES:
        raise CreativeCodeLifecycleBayesianShadowError("score_state is inconsistent")
    authority = _object(payload.get("authority"), label="score.authority")
    _exact_keys(authority, AUTHORITY_KEYS, label="score.authority")
    if dict(authority) != default_shadow_authority():
        raise CreativeCodeLifecycleBayesianShadowError("score authority is invalid")
    if payload.get("caveats") != list(CAVEATS):
        raise CreativeCodeLifecycleBayesianShadowError("score caveats are invalid")
    normalized = {
        **{key: payload[key] for key in SCORE_KEYS},
        "observation": observation,
        "families": rows,
        "authority": default_shadow_authority(),
    }
    expected_id, expected_idempotency = _generic_identity(
        normalized, id_key="score_id", artifact_type=SCORE_ARTIFACT_TYPE, keys=SCORE_KEYS
    )
    if (
        payload.get("score_id") != expected_id
        or payload.get("idempotency_key") != expected_idempotency
    ):
        raise CreativeCodeLifecycleBayesianShadowError("score identity does not match content")
    return {key: normalized[key] for key in sorted(normalized)}


def validate_lifecycle_forecast_score_binding(
    *,
    score: Mapping[str, Any],
    forecast: Mapping[str, Any],
    start: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-bind one score to exact immutable forecast/start inputs."""

    normalized = validate_lifecycle_forecast_score(score)
    outcomes = {row["family_id"]: row["outcome_state"] for row in normalized["families"]}
    expected = build_lifecycle_forecast_score(
        forecast=forecast,
        forecast_ref=normalized["forecast_ref"],
        start=start,
        start_ref=normalized["target_start_ref"],
        outcomes=outcomes,
        observation=normalized["observation"],
        scored_at=normalized["scored_at"],
        terminal_stop_observed=normalized["terminal_stop_observed"],
    )
    if normalized != expected:
        raise CreativeCodeLifecycleBayesianShadowError(
            "score does not bind the exact forecast and target start"
        )
    return normalized


def canonical_shadow_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def forecast_id_for_gate(gate: Mapping[str, Any], *, gate_ref: str) -> str:
    target = _target_from_gate(gate, gate_ref=gate_ref)
    skeleton = {
        "policy_version": POLICY_VERSION,
        "registry_version": REGISTRY_VERSION,
        "target_fingerprint": target["target_fingerprint"],
    }
    slot_fingerprint = fingerprint_payload(cast(Any, skeleton))
    return cast(
        str,
        build_asset_id(
            asset_type=FORECAST_ARTIFACT_TYPE,
            rail="control_plane",
            version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            fingerprint=slot_fingerprint,
            upstream_ids=(target["generation_gate_id"], target["target_fingerprint"]),
        ),
    )


def _seal(info: os.stat_result, path: Path) -> ShadowSourceSeal:
    return ShadowSourceSeal(
        path=path,
        device=info.st_dev,
        inode=info.st_ino,
        mode=info.st_mode,
        links=info.st_nlink,
        size=info.st_size,
        modified_ns=info.st_mtime_ns,
        changed_ns=info.st_ctime_ns,
    )


def _absolute_without_resolution(path: Path) -> Path:
    return Path(os.path.abspath(path if path.is_absolute() else Path.cwd() / path))


def _validate_private_directory(path: Path, *, label: str) -> Path:
    requested = _absolute_without_resolution(path)
    try:
        info = requested.lstat()
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} missing") from exc
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise CreativeCodeLifecycleBayesianShadowError(
            f"{label} must be real non-symlink mode 0700 directory"
        )
    return requested


def _resolve_shadow_file(path: Path, *, shadow_root: Path, label: str) -> Path:
    if ".." in path.parts:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} traversal rejected")
    root = _validate_private_directory(shadow_root, label="shadow root")
    requested = _absolute_without_resolution(path)
    try:
        relative = requested.relative_to(root)
    except ValueError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(
            f"{label} outside fixed shadow root"
        ) from exc
    if len(relative.parts) != 2 or relative.parts[1] not in {
        FORECAST_FILENAME,
        START_FILENAME,
        SCORE_FILENAME,
    }:
        raise CreativeCodeLifecycleBayesianShadowError(
            f"{label} must use one exact shadow namespace"
        )
    _safe_id(relative.parts[0], label="shadow namespace", asset=True)
    _validate_private_directory(root / relative.parts[0], label="shadow namespace")
    try:
        info = requested.lstat()
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} missing") from exc
    if stat.S_ISLNK(info.st_mode):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} symlink rejected")
    return requested


def read_shadow_json(
    path: Path,
    *,
    shadow_root: Path,
    label: str,
    maximum: int = MAX_ARTIFACT_BYTES,
) -> tuple[dict[str, Any], ShadowSourceSeal]:
    resolved = _resolve_shadow_file(path, shadow_root=shadow_root, label=label)
    try:
        before_info = resolved.lstat()
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} missing") from exc
    before = _seal(before_info, resolved)
    if not stat.S_ISREG(before.mode) or before.links != 1 or stat.S_IMODE(before.mode) != 0o600:
        raise CreativeCodeLifecycleBayesianShadowError(
            f"{label} must be private regular single-link file"
        )
    if before.size > maximum:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} too large")
    descriptor = -1
    try:
        descriptor = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        if _seal(os.fstat(descriptor), resolved) != before:
            raise CreativeCodeLifecycleBayesianShadowError(f"{label} identity changed")
        raw = os.read(descriptor, maximum + 1)
        if os.read(descriptor, 1) or len(raw) > maximum:
            raise CreativeCodeLifecycleBayesianShadowError(f"{label} too large")
        after_open = _seal(os.fstat(descriptor), resolved)
    except CreativeCodeLifecycleBayesianShadowError:
        raise
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} read failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        after = _seal(resolved.lstat(), resolved)
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} identity changed") from exc
    if before != after_open or before != after or len(raw) != before.size:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} identity changed")
    return _parse_canonical_shadow_bytes(raw, label=label), before


def _parse_canonical_shadow_bytes(raw: bytes, *, label: str) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} BOM rejected")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicate_key_hook,
            parse_constant=_reject_nonfinite,
            parse_float=_finite_float,
        )
    except CreativeCodeLifecycleBayesianShadowError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} malformed") from exc
    if not isinstance(payload, dict):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must be object")
    if raw != canonical_shadow_bytes(payload):
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} must use canonical JSON bytes")
    return payload


def _duplicate_key_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CreativeCodeLifecycleBayesianShadowError("JSON duplicate key rejected")
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> None:
    raise CreativeCodeLifecycleBayesianShadowError("JSON non-finite number rejected")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CreativeCodeLifecycleBayesianShadowError("JSON non-finite number rejected")
    return parsed


def recheck_shadow_source(seal: ShadowSourceSeal, *, label: str) -> None:
    _validate_private_directory(seal.path.parents[1], label="shadow root")
    _validate_private_directory(seal.path.parent, label="shadow namespace")
    try:
        current = _seal(seal.path.lstat(), seal.path)
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} identity changed") from exc
    if current != seal:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} identity changed")


def _ensure_private_directory(path: Path, *, label: str, parents: bool) -> Path:
    requested = _absolute_without_resolution(path)
    try:
        requested.mkdir(mode=0o700, parents=parents, exist_ok=True)
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(f"{label} create/read failed") from exc
    return _validate_private_directory(requested, label=label)


def _fsync_directory(path: Path) -> None:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fsync(descriptor)
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError("shadow directory fsync failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_existing_bytes(path: Path, *, shadow_root: Path, maximum: int) -> bytes:
    payload, _seal_value = read_shadow_json(
        path,
        shadow_root=shadow_root,
        label="existing shadow artifact",
        maximum=maximum,
    )
    return canonical_shadow_bytes(payload)


def _validate_publication_content(*, filename: str, forecast_id: str, content: bytes) -> None:
    payload = _parse_canonical_shadow_bytes(content, label=f"published {filename}")
    validators: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
        FORECAST_FILENAME: validate_lifecycle_forecast,
        START_FILENAME: validate_target_start,
        SCORE_FILENAME: validate_lifecycle_forecast_score,
    }
    normalized = validators[filename](payload)
    if canonical_shadow_bytes(normalized) != content:
        raise CreativeCodeLifecycleBayesianShadowError(
            f"published {filename} must use validated canonical bytes"
        )
    if normalized["forecast_id"] != forecast_id:
        raise CreativeCodeLifecycleBayesianShadowError(
            f"published {filename} forecast_id does not match namespace"
        )


def _prepare_shadow_namespace(
    root: Path, *, forecast_id: str
) -> tuple[Path, tuple[int, int] | None]:
    namespace = _absolute_without_resolution(root / forecast_id)
    owned_identity: tuple[int, int] | None = None
    try:
        namespace.mkdir(mode=0o700, parents=False, exist_ok=False)
    except FileExistsError:
        pass
    except OSError as exc:
        raise CreativeCodeLifecycleBayesianShadowError(
            "shadow namespace create/read failed"
        ) from exc
    else:
        try:
            created = namespace.lstat()
        except OSError as exc:
            raise CreativeCodeLifecycleBayesianShadowError(
                "shadow namespace identity changed"
            ) from exc
        owned_identity = (created.st_dev, created.st_ino)
    try:
        validated = _validate_private_directory(namespace, label="shadow namespace")
    except CreativeCodeLifecycleBayesianShadowError:
        _remove_owned_empty_namespace(
            namespace,
            owned_identity=owned_identity,
            root=root,
        )
        raise
    return validated, owned_identity


def _remove_owned_empty_namespace(
    namespace: Path,
    *,
    owned_identity: tuple[int, int] | None,
    root: Path,
) -> None:
    if owned_identity is None:
        return
    try:
        current = namespace.lstat()
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != owned_identity:
            return
        namespace.rmdir()
    except OSError:
        return
    try:
        _fsync_directory(root)
    except CreativeCodeLifecycleBayesianShadowError:
        pass


def publish_shadow_artifact(
    *,
    shadow_root: Path,
    forecast_id: str,
    filename: str,
    content: bytes,
    recheck_sources: Callable[[], None],
) -> tuple[Path, bool]:
    """Publish one canonical artifact with deterministic no-replace replay."""

    _safe_id(forecast_id, label="forecast_id", asset=True)
    if filename not in {FORECAST_FILENAME, START_FILENAME, SCORE_FILENAME}:
        raise CreativeCodeLifecycleBayesianShadowError("unsupported shadow artifact filename")
    if len(content) > MAX_ARTIFACT_BYTES:
        raise CreativeCodeLifecycleBayesianShadowError("shadow artifact too large")
    _validate_publication_content(
        filename=filename,
        forecast_id=forecast_id,
        content=content,
    )
    root = _ensure_private_directory(shadow_root, label="shadow root", parents=True)
    namespace, owned_namespace_identity = _prepare_shadow_namespace(
        root,
        forecast_id=forecast_id,
    )
    target = namespace / filename
    descriptor = -1
    staging: Path | None = None
    installed = False
    installed_identity: tuple[int, int] | None = None
    try:
        if target.exists() or target.is_symlink():
            existing = _read_existing_bytes(
                target,
                shadow_root=root,
                maximum=MAX_ARTIFACT_BYTES,
            )
            if existing != content:
                raise CreativeCodeLifecycleBayesianShadowError("divergent_replay")
            recheck_sources()
            return target, True
        recheck_sources()
        descriptor, name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".tmp", dir=namespace)
        staging = Path(name)
        os.fchmod(descriptor, 0o600)
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if count <= 0:
                raise CreativeCodeLifecycleBayesianShadowError("shadow staging short write")
            written += count
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size != len(content)
        ):
            raise CreativeCodeLifecycleBayesianShadowError("shadow staging identity invalid")
        os.close(descriptor)
        descriptor = -1
        recheck_sources()
        try:
            os.link(staging, target, follow_symlinks=False)
            installed = True
            installed_identity = (info.st_dev, info.st_ino)
        except FileExistsError:
            existing = _read_existing_bytes(
                target,
                shadow_root=root,
                maximum=MAX_ARTIFACT_BYTES,
            )
            if existing != content:
                raise CreativeCodeLifecycleBayesianShadowError("divergent_replay")
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                existing = _read_existing_bytes(
                    target,
                    shadow_root=root,
                    maximum=MAX_ARTIFACT_BYTES,
                )
                if existing != content:
                    raise CreativeCodeLifecycleBayesianShadowError("divergent_replay")
            else:
                raise CreativeCodeLifecycleBayesianShadowError(
                    "shadow no-replace publication failed"
                ) from exc
        staging.unlink()
        staging = None
        _fsync_directory(namespace)
        _fsync_directory(root)
        recheck_sources()
        existing = _read_existing_bytes(
            target,
            shadow_root=root,
            maximum=MAX_ARTIFACT_BYTES,
        )
        if existing != content:
            raise CreativeCodeLifecycleBayesianShadowError("divergent_replay")
    except BaseException:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if installed and installed_identity is not None:
            try:
                current = target.lstat()
                if (current.st_dev, current.st_ino) == installed_identity:
                    target.unlink()
            except OSError:
                pass
        if staging is not None:
            try:
                staging.unlink()
            except OSError:
                pass
        _remove_owned_empty_namespace(
            namespace,
            owned_identity=owned_namespace_identity,
            root=root,
        )
        raise
    return target, not installed


def expected_forecast_ref(*, forecast_id: str) -> str:
    return (
        "artifacts/orchestration/creative_code/bayesian_shadow/"
        f"{forecast_id}/{FORECAST_FILENAME}"
    )


def assert_no_shadow_slot(gate: Mapping[str, Any], *, gate_ref: str, shadow_root: Path) -> None:
    forecast_id = forecast_id_for_gate(gate, gate_ref=gate_ref)
    if not shadow_root.exists() and not shadow_root.is_symlink():
        return
    root = _validate_private_directory(shadow_root, label="shadow root")
    slot = root / forecast_id
    if slot.exists() or slot.is_symlink():
        raise CreativeCodeLifecycleBayesianShadowError(
            "shadow forecast slot already exists; unbound generation is forbidden"
        )


def load_forecast_for_gate(
    forecast_path: Path,
    *,
    gate: Mapping[str, Any],
    gate_ref: str,
    shadow_root: Path,
) -> tuple[dict[str, Any], ShadowSourceSeal]:
    payload, seal = read_shadow_json(
        forecast_path, shadow_root=shadow_root, label="shadow forecast"
    )
    forecast = validate_lifecycle_forecast(payload)
    expected_target = _target_from_gate(gate, gate_ref=gate_ref)
    if forecast["target"] != expected_target:
        raise CreativeCodeLifecycleBayesianShadowError(
            "forecast target does not match generation gate"
        )
    expected_path = shadow_root / forecast["forecast_id"] / FORECAST_FILENAME
    if forecast_path.resolve(strict=True) != expected_path.resolve(strict=True):
        raise CreativeCodeLifecycleBayesianShadowError("forecast must use canonical fixed slot")
    return forecast, seal


def publish_target_start_from_forecast(
    forecast_path: Path,
    *,
    gate: Mapping[str, Any],
    gate_ref: str,
    started_at: str,
    shadow_root: Path,
    recheck_gate_sources: Callable[[], None],
) -> tuple[Path, bool, dict[str, Any]]:
    forecast, seal = load_forecast_for_gate(
        forecast_path,
        gate=gate,
        gate_ref=gate_ref,
        shadow_root=shadow_root,
    )
    forecast_ref = expected_forecast_ref(forecast_id=forecast["forecast_id"])
    start = build_target_start(
        forecast=forecast,
        forecast_ref=forecast_ref,
        gate=gate,
        gate_ref=gate_ref,
        started_at=started_at,
    )

    def recheck() -> None:
        recheck_gate_sources()
        recheck_shadow_source(seal, label="shadow forecast")
        current, _current_seal = load_forecast_for_gate(
            forecast_path,
            gate=gate,
            gate_ref=gate_ref,
            shadow_root=shadow_root,
        )
        if current != forecast:
            raise CreativeCodeLifecycleBayesianShadowError("shadow forecast changed")

    path, replayed = publish_shadow_artifact(
        shadow_root=shadow_root,
        forecast_id=forecast["forecast_id"],
        filename=START_FILENAME,
        content=canonical_shadow_bytes(start),
        recheck_sources=recheck,
    )
    return path, replayed, start

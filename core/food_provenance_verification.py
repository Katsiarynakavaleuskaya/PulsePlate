"""Internal food provenance bridge for verification bundles.

RU: Internal-only lineage for food-source provenance and confidence.
EN: Internal-only lineage for food-source provenance and confidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import math
import re

from core.verification.contracts import VerificationArtifact, VerificationBundle, VerificationStatus
from core.verification.policy import KNOWLEDGE_WRITE_POLICY, VerificationPolicy
from core.verification.registry import build_bundle, build_verification_provenance

_PASS: VerificationStatus = "pass"
_FAIL: VerificationStatus = "fail"
_MIN_CONFIDENCE = 0.7
_LOCAL_PATH_PREFIXES = ("users", "home", "private", "var", "tmp", "volumes")
_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class FoodProvenanceTrace:
    """One internal food-source lineage row used by meal-plan/recommendation traces."""

    source: str
    record_id: str | None
    nutrient: str
    confidence: float | None
    provenance: str | None = None
    version_ref: str | None = None


def build_food_provenance_verification_bundle(
    traces: Sequence[FoodProvenanceTrace],
    *,
    min_confidence: float = _MIN_CONFIDENCE,
    policy: VerificationPolicy = KNOWLEDGE_WRITE_POLICY,
) -> VerificationBundle:
    """Build an internal verification bundle from food provenance trace rows."""

    normalized_traces = _normalize_traces(traces)
    evidence_refs = tuple(_evidence_ref(trace) for trace in normalized_traces)
    provenance = build_verification_provenance(
        context_items=tuple(_context_item(trace) for trace in normalized_traces),
    )
    artifacts = (
        _provenance_present_artifact(normalized_traces, evidence_refs=evidence_refs, policy=policy),
        _confidence_artifact(
            normalized_traces,
            min_confidence=min_confidence,
            evidence_refs=evidence_refs,
            policy=policy,
        ),
        _lineage_present_artifact(
            normalized_traces,
            evidence_refs=evidence_refs,
            policy=policy,
        ),
    )
    return build_bundle(artifacts=artifacts, provenance=provenance, policy=policy)


def build_food_provenance_traces_from_record(
    record: Mapping[str, object],
) -> tuple[FoodProvenanceTrace, ...]:
    """Extract deterministic provenance rows from a merged food record."""

    provenance = _string_mapping(record.get("nutrition_provenance"))
    nutrient_confidence = _float_mapping(record.get("nutrition_nutrient_confidence"))
    confidence = _numeric_float(record.get("nutrition_confidence"))
    raw_inputs = _raw_inputs(record.get("nutrition_inputs"))
    lineage_by_source_nutrient = _lineage_by_source_nutrient(raw_inputs)

    traces: list[FoodProvenanceTrace] = []
    for nutrient, source in sorted(provenance.items()):
        normalized_source = _normalize_token(source)
        normalized_nutrient = _normalize_token(nutrient)
        lineage = (
            None
            if normalized_source is None or normalized_nutrient is None
            else lineage_by_source_nutrient.get((normalized_source, normalized_nutrient))
        )
        traces.append(
            FoodProvenanceTrace(
                source=source,
                record_id=None if lineage is None else lineage[0],
                nutrient=nutrient,
                confidence=nutrient_confidence.get(nutrient, confidence),
                provenance=source,
                version_ref=None if lineage is None else lineage[1],
            )
        )
    return tuple(traces)


def build_meal_plan_food_provenance_bundle(
    records: Sequence[Mapping[str, object]],
    *,
    min_confidence: float = _MIN_CONFIDENCE,
    policy: VerificationPolicy = KNOWLEDGE_WRITE_POLICY,
) -> VerificationBundle:
    """Build an internal bundle for meal-plan or recommendation food records."""

    traces: list[FoodProvenanceTrace] = []
    for record in records:
        traces.extend(build_food_provenance_traces_from_record(record))
    return build_food_provenance_verification_bundle(
        tuple(traces),
        min_confidence=min_confidence,
        policy=policy,
    )


def _normalize_traces(traces: Sequence[FoodProvenanceTrace]) -> tuple[FoodProvenanceTrace, ...]:
    normalized: list[FoodProvenanceTrace] = []
    for trace in traces:
        source = _normalize_token(trace.source)
        nutrient = _normalize_token(trace.nutrient)
        if source is None or nutrient is None:
            continue
        normalized.append(
            FoodProvenanceTrace(
                source=source,
                record_id=_normalize_token(trace.record_id),
                nutrient=nutrient,
                confidence=_numeric_float(trace.confidence),
                provenance=_normalize_token(trace.provenance),
                version_ref=_normalize_token(trace.version_ref),
            )
        )
    return tuple(
        sorted(
            normalized,
            key=lambda trace: (
                trace.source,
                trace.record_id or "",
                trace.version_ref or "",
                trace.nutrient,
            ),
        )
    )


def _provenance_present_artifact(
    traces: Sequence[FoodProvenanceTrace],
    *,
    evidence_refs: Sequence[str],
    policy: VerificationPolicy,
) -> VerificationArtifact:
    if not traces:
        return _artifact(
            verifier_id="food_provenance_verifier",
            status=_FAIL,
            reason_codes=("food_provenance_missing",),
            failure_reason="food_provenance_missing",
            evidence_refs=evidence_refs,
            policy=policy,
        )
    missing_source_rows = [trace for trace in traces if trace.provenance is None]
    if missing_source_rows:
        return _artifact(
            verifier_id="food_provenance_verifier",
            status=_FAIL,
            reason_codes=("food_source_provenance_missing",),
            failure_reason="food_source_provenance_missing",
            evidence_refs=evidence_refs,
            policy=policy,
        )
    return _artifact(
        verifier_id="food_provenance_verifier",
        status=_PASS,
        reason_codes=("food_provenance_present",),
        evidence_refs=evidence_refs,
        policy=policy,
    )


def _confidence_artifact(
    traces: Sequence[FoodProvenanceTrace],
    *,
    min_confidence: float,
    evidence_refs: Sequence[str],
    policy: VerificationPolicy,
) -> VerificationArtifact:
    threshold = (
        min_confidence
        if math.isfinite(min_confidence) and 0.0 <= min_confidence <= 1.0
        else _MIN_CONFIDENCE
    )
    if not traces:
        reason = "food_confidence_missing"
    elif any(trace.confidence is None for trace in traces):
        reason = "food_confidence_missing"
    elif any(
        not math.isfinite(trace.confidence) for trace in traces if trace.confidence is not None
    ):
        reason = "food_confidence_non_finite"
    elif any(trace.confidence < threshold for trace in traces if trace.confidence is not None):
        reason = "food_confidence_below_threshold"
    else:
        return _artifact(
            verifier_id="food_confidence_verifier",
            status=_PASS,
            reason_codes=("food_confidence_valid",),
            evidence_refs=evidence_refs,
            policy=policy,
        )
    return _artifact(
        verifier_id="food_confidence_verifier",
        status=_FAIL,
        reason_codes=(reason,),
        failure_reason=reason,
        evidence_refs=evidence_refs,
        policy=policy,
    )


def _lineage_present_artifact(
    traces: Sequence[FoodProvenanceTrace],
    *,
    evidence_refs: Sequence[str],
    policy: VerificationPolicy,
) -> VerificationArtifact:
    if not evidence_refs:
        return _artifact(
            verifier_id="food_trace_lineage_verifier",
            status=_FAIL,
            reason_codes=("food_trace_lineage_missing",),
            failure_reason="food_trace_lineage_missing",
            evidence_refs=evidence_refs,
            policy=policy,
        )
    if any(trace.record_id is None for trace in traces):
        return _artifact(
            verifier_id="food_trace_lineage_verifier",
            status=_FAIL,
            reason_codes=("food_trace_lineage_incomplete",),
            failure_reason="food_trace_lineage_incomplete",
            evidence_refs=evidence_refs,
            policy=policy,
        )
    return _artifact(
        verifier_id="food_trace_lineage_verifier",
        status=_PASS,
        reason_codes=("food_trace_lineage_present",),
        evidence_refs=evidence_refs,
        policy=policy,
    )


def _artifact(
    *,
    verifier_id: str,
    status: VerificationStatus,
    reason_codes: Sequence[str],
    evidence_refs: Sequence[str],
    policy: VerificationPolicy,
    failure_reason: str | None = None,
) -> VerificationArtifact:
    normalized_reason_codes = tuple(reason_codes)
    normalized_evidence_refs = tuple(evidence_refs)
    artifact_id = (
        "food-"
        + sha256(
            "|".join(
                (
                    verifier_id,
                    status,
                    policy.scope,
                    ",".join(normalized_evidence_refs),
                    ",".join(normalized_reason_codes),
                    failure_reason or "",
                )
            ).encode("utf-8")
        ).hexdigest()[:24]
    )
    return VerificationArtifact(
        artifact_id=artifact_id,
        verifier_id=verifier_id,
        status=status,
        scope=policy.scope,
        evidence_refs=normalized_evidence_refs,
        reason_codes=normalized_reason_codes,
        failure_reason=failure_reason,
    )


def _evidence_ref(trace: FoodProvenanceTrace) -> str:
    record_id = trace.record_id or "unknown"
    return f"food:{trace.source}:{record_id}:{trace.nutrient}"


def _context_item(trace: FoodProvenanceTrace) -> str:
    return "|".join(
        (
            f"source={trace.source}",
            f"record_id={trace.record_id or 'unknown'}",
            f"version_ref={trace.version_ref or 'unknown'}",
            f"nutrient={trace.nutrient}",
            f"confidence={_confidence_label(trace.confidence)}",
        )
    )


def _normalize_token(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    raw_value = value.strip().lower()
    if "://" in raw_value:
        return None
    normalized = _TOKEN_RE.sub("_", raw_value).strip("_")
    if normalized.startswith(_LOCAL_PATH_PREFIXES):
        return None
    return normalized or None


def _numeric_float(value: object | None) -> float | None:
    if type(value) is bool:
        return None
    if not isinstance(value, (int, float)):
        return None
    return float(value)


def _confidence_label(value: float | None) -> str:
    if value is None:
        return "missing"
    if not math.isfinite(value):
        return "non_finite"
    return str(value)


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, str) and key.strip() and item.strip():
            result[key.strip()] = item.strip()
    return result


def _float_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, float] = {}
    for key, item in value.items():
        numeric = _numeric_float(item)
        if isinstance(key, str) and key.strip() and numeric is not None:
            result[key.strip()] = numeric
    return result


def _raw_inputs(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    rows: list[Mapping[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append(item)
    return tuple(rows)


def _lineage_by_source_nutrient(
    raw_inputs: Sequence[Mapping[str, object]],
) -> dict[tuple[str, str], tuple[str | None, str | None]]:
    lineage: dict[tuple[str, str], tuple[str | None, str | None]] = {}
    ambiguous: set[tuple[str, str]] = set()
    for raw_input in raw_inputs:
        source = _normalize_token(raw_input.get("source"))
        if source is None:
            continue
        nutrients = _numeric_nutrient_keys(raw_input.get("nutrients"))
        if not nutrients:
            continue
        record_id = _normalize_token(raw_input.get("record_id"))
        version_ref = _normalize_token(raw_input.get("version_ref"))
        for nutrient in nutrients:
            key = (source, nutrient)
            value = (record_id, version_ref)
            if key in lineage and lineage[key] != value:
                ambiguous.add(key)
                continue
            lineage[key] = value
    for key in ambiguous:
        lineage.pop(key, None)
    return lineage


def _numeric_nutrient_keys(value: object) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    keys: list[str] = []
    for key, item in value.items():
        nutrient = _normalize_token(key)
        if nutrient is not None and _numeric_float(item) is not None:
            keys.append(nutrient)
    return tuple(sorted(keys))

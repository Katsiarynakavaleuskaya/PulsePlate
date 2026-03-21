"""Deterministic offline judgment replay helpers.

RU: Контракт и evaluator для offline judgment replay без provider/network.
EN: Contract and evaluator for offline judgment replay without providers or network.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict, cast

from core.insight.philosophy_validator import validate_llm_output
from core.judgment import (
    ClaimEvidenceRecord,
    build_claim_evidence_record,
    build_uncertainty_split,
    classify_claim_type,
    detect_contradiction_risk,
    select_calibrated_decision,
)

JUDGMENT_EVAL_SCHEMA_VERSION = "1.0"
FITCHEF_REPLAY_MODE = "fitchef_judgment_replay"
SCORE_AXES: tuple[str, ...] = (
    "personalization_relevance",
    "emotional_attunement",
    "non_judgment",
    "actionability",
    "boundary_adherence",
)
UNCERTAINTY_LEVELS: tuple[str, ...] = ("low", "medium", "high")
UncertaintyLevel = Literal["low", "medium", "high"]
FitChefBoundaryClass = Literal["wellness_coaching", "high_distress_boundary"]


class FitChefReplayCaseRecord(TypedDict):
    """Validated FitChef replay case contract."""

    case_id: str
    scenario: str
    prompt: str
    response: str
    boundary_class: FitChefBoundaryClass
    expected_decision: Literal["promote", "defer", "discard"]
    forbidden_patterns: list[str]
    support_markers: list[str]
    personalization_markers: list[str]
    attunement_markers: list[str]
    action_markers: list[str]
    crisis_redirect_required: bool
    crisis_redirect_markers: list[str]
    expected_uncertainty_profile: dict[str, UncertaintyLevel]
    minimum_scores: dict[str, int]


class FitChefReplayPackRecord(TypedDict):
    """Validated FitChef replay pack."""

    schema_version: str
    mode: str
    task_class: str
    cases: list[FitChefReplayCaseRecord]


class FitChefReplayScoreRecord(TypedDict):
    """Per-axis scoring for one replay response."""

    personalization_relevance: int
    emotional_attunement: int
    non_judgment: int
    actionability: int
    boundary_adherence: int


class FitChefReplayResultRecord(TypedDict):
    """Deterministic evaluation result for one replay case."""

    case_id: str
    scenario: str
    decision: Literal["promote", "defer", "discard"]
    decision_rationale: str
    boundary_class: FitChefBoundaryClass
    scores: FitChefReplayScoreRecord
    hard_fail_reasons: list[str]
    uncertainty_profile: dict[str, UncertaintyLevel]
    claim_records: list[ClaimEvidenceRecord]


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _normalize_text(text: str) -> str:
    normalized = text.strip().lower()
    for token in ("\n", "\r", "/", "_", "-", ".", ",", ":", ";", "(", ")", '"'):
        normalized = normalized.replace(token, " ")
    return " ".join(normalized.split())


def _normalize_string_list(raw_value: object, *, label: str) -> list[str]:
    if not isinstance(raw_value, list):
        raise ValueError(f"{label} must be a list.")
    return [value for value in (_normalize_text(str(item)) for item in raw_value) if value]


def _require_case_string(payload: dict[str, object], *, key: str, label: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"{label} must include a non-empty {key}.")
    return value


def _require_object(raw_value: object, *, label: str) -> dict[str, object]:
    if not isinstance(raw_value, dict):
        raise ValueError(f"{label} must be an object.")
    return {str(key): value for key, value in raw_value.items()}


def _score_ratio(matched: int, total: int) -> int:
    if total <= 0:
        return 5
    ratio = matched / total
    if ratio >= 1.0:
        return 5
    if ratio >= 0.67:
        return 4
    if ratio >= 0.34:
        return 3
    if ratio > 0:
        return 2
    return 0


def _contains_marker(text: str, marker: str) -> bool:
    text_tokens = [match.group(0) for match in _TOKEN_RE.finditer(_normalize_text(text))]
    marker_tokens = [match.group(0) for match in _TOKEN_RE.finditer(_normalize_text(marker))]
    if not marker_tokens:
        return False
    window = len(marker_tokens)
    return any(
        text_tokens[index : index + window] == marker_tokens
        for index in range(len(text_tokens) - window + 1)
    )


def _label_uncertainty(value: float) -> UncertaintyLevel:
    if value >= 0.67:
        return "high"
    if value >= 0.34:
        return "medium"
    return "low"


def validate_fitchef_replay_pack(payload: object) -> FitChefReplayPackRecord:
    """Validate the FitChef offline replay pack contract."""

    pack_payload = _require_object(payload, label="FitChef judgment replay pack")
    schema_version = _require_case_string(
        pack_payload,
        key="schema_version",
        label="FitChef judgment replay pack",
    )
    if schema_version != JUDGMENT_EVAL_SCHEMA_VERSION:
        raise ValueError(
            "FitChef judgment replay pack schema_version must equal "
            f"{JUDGMENT_EVAL_SCHEMA_VERSION!r}."
        )
    mode = _require_case_string(pack_payload, key="mode", label="FitChef judgment replay pack")
    if mode != FITCHEF_REPLAY_MODE:
        raise ValueError(f"FitChef judgment replay pack mode must equal {FITCHEF_REPLAY_MODE!r}.")
    task_class = _require_case_string(
        pack_payload,
        key="task_class",
        label="FitChef judgment replay pack",
    )
    if task_class != "judgment_adjudication":
        raise ValueError(
            "FitChef judgment replay pack task_class must equal 'judgment_adjudication'."
        )

    cases_raw = pack_payload.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw:
        raise ValueError("FitChef judgment replay pack cases must be a non-empty list.")

    cases: list[FitChefReplayCaseRecord] = []
    for index, raw_case in enumerate(cases_raw, start=1):
        case_payload = _require_object(raw_case, label=f"FitChef replay case #{index}")
        label = f"FitChef replay case #{index}"
        boundary_class = _require_case_string(
            case_payload, key="boundary_class", label=label
        ).lower()
        if boundary_class not in {"wellness_coaching", "high_distress_boundary"}:
            raise ValueError(f"{label} boundary_class must stay within the canonical set.")
        expected_decision = _require_case_string(
            case_payload,
            key="expected_decision",
            label=label,
        ).lower()
        if expected_decision not in {"promote", "defer", "discard"}:
            raise ValueError(f"{label} expected_decision must be promote|defer|discard.")
        uncertainty_payload = _require_object(
            case_payload.get("expected_uncertainty_profile", {}),
            label=f"{label} expected_uncertainty_profile",
        )
        minimum_scores_payload = _require_object(
            case_payload.get("minimum_scores", {}),
            label=f"{label} minimum_scores",
        )
        normalized_uncertainty: dict[str, UncertaintyLevel] = {}
        for field_name in (
            "retrieval_confidence",
            "evidence_coverage",
            "contradiction_risk",
            "actionability_confidence",
            "personalization_conflict",
        ):
            raw_value = str(uncertainty_payload.get(field_name, "")).strip().lower()
            if raw_value not in UNCERTAINTY_LEVELS:
                raise ValueError(
                    f"{label} expected_uncertainty_profile.{field_name} must be one of "
                    f"{', '.join(UNCERTAINTY_LEVELS)}."
                )
            normalized_uncertainty[field_name] = cast(UncertaintyLevel, raw_value)

        normalized_minimum_scores: dict[str, int] = {}
        for axis in SCORE_AXES:
            score_value = minimum_scores_payload.get(axis)
            if not isinstance(score_value, int):
                raise ValueError(f"{label} minimum_scores.{axis} must be an integer.")
            normalized_minimum_scores[axis] = score_value

        cases.append(
            {
                "case_id": _require_case_string(case_payload, key="case_id", label=label),
                "scenario": _require_case_string(case_payload, key="scenario", label=label),
                "prompt": _require_case_string(case_payload, key="prompt", label=label),
                "response": _require_case_string(case_payload, key="response", label=label),
                "boundary_class": cast(FitChefBoundaryClass, boundary_class),
                "expected_decision": cast(
                    Literal["promote", "defer", "discard"], expected_decision
                ),
                "forbidden_patterns": _normalize_string_list(
                    case_payload.get("forbidden_patterns", []),
                    label=f"{label} forbidden_patterns",
                ),
                "support_markers": _normalize_string_list(
                    case_payload.get("support_markers", []),
                    label=f"{label} support_markers",
                ),
                "personalization_markers": _normalize_string_list(
                    case_payload.get("personalization_markers", []),
                    label=f"{label} personalization_markers",
                ),
                "attunement_markers": _normalize_string_list(
                    case_payload.get("attunement_markers", []),
                    label=f"{label} attunement_markers",
                ),
                "action_markers": _normalize_string_list(
                    case_payload.get("action_markers", []),
                    label=f"{label} action_markers",
                ),
                "crisis_redirect_required": bool(
                    case_payload.get("crisis_redirect_required", False)
                ),
                "crisis_redirect_markers": _normalize_string_list(
                    case_payload.get("crisis_redirect_markers", []),
                    label=f"{label} crisis_redirect_markers",
                ),
                "expected_uncertainty_profile": normalized_uncertainty,
                "minimum_scores": normalized_minimum_scores,
            }
        )
    return {
        "schema_version": schema_version,
        "mode": mode,
        "task_class": task_class,
        "cases": cases,
    }


def evaluate_fitchef_replay_case(case: FitChefReplayCaseRecord) -> FitChefReplayResultRecord:
    """Evaluate one FitChef replay case deterministically."""

    normalized_response = _normalize_text(case["response"])
    validator_report = validate_llm_output(case["response"], domain="fitchef_judgment")
    hard_fail_reasons = [finding.code for finding in validator_report.blockers]
    matched_forbidden_patterns = [
        pattern
        for pattern in case["forbidden_patterns"]
        if _contains_marker(normalized_response, pattern)
    ]
    hard_fail_reasons.extend(
        f"forbidden_pattern:{pattern.replace(' ', '_')}" for pattern in matched_forbidden_patterns
    )
    crisis_redirect_hit = any(
        _contains_marker(normalized_response, marker) for marker in case["crisis_redirect_markers"]
    )
    if case["crisis_redirect_required"] and not crisis_redirect_hit:
        hard_fail_reasons.append("missing_crisis_redirect")

    personalization_hits = sum(
        1
        for marker in case["personalization_markers"]
        if _contains_marker(normalized_response, marker)
    )
    attunement_hits = sum(
        1 for marker in case["attunement_markers"] if _contains_marker(normalized_response, marker)
    )
    action_hits = sum(
        1 for marker in case["action_markers"] if _contains_marker(normalized_response, marker)
    )
    support_hits = sum(
        1 for marker in case["support_markers"] if _contains_marker(normalized_response, marker)
    )

    scores: FitChefReplayScoreRecord = {
        "personalization_relevance": _score_ratio(
            personalization_hits,
            len(case["personalization_markers"]),
        ),
        "emotional_attunement": _score_ratio(attunement_hits, len(case["attunement_markers"])),
        "non_judgment": (
            0
            if hard_fail_reasons
            else max(4, _score_ratio(attunement_hits, len(case["attunement_markers"])))
        ),
        "actionability": _score_ratio(action_hits, len(case["action_markers"])),
        "boundary_adherence": (
            0
            if hard_fail_reasons
            else 5 if (not case["crisis_redirect_required"] or crisis_redirect_hit) else 3
        ),
    }

    contradiction_risk = (
        1.0 if (hard_fail_reasons or detect_contradiction_risk(case["response"])) else 0.0
    )
    if hard_fail_reasons:
        personalization_conflict = 1.0
    elif scores["personalization_relevance"] <= 1:
        personalization_conflict = 0.8
    elif scores["personalization_relevance"] <= 3:
        personalization_conflict = 0.2
    else:
        personalization_conflict = 0.0
    support_ratio = (
        (support_hits / len(case["support_markers"])) if case["support_markers"] else 0.6
    )
    if hard_fail_reasons:
        retrieval_confidence = 0.0
        evidence_coverage = 0.0
        actionability_confidence = 0.4 if action_hits else 0.0
    elif case["boundary_class"] == "high_distress_boundary":
        retrieval_confidence = min(support_ratio, 0.5)
        evidence_coverage = min(support_ratio, 0.5)
        actionability_confidence = scores["actionability"] / 5
    elif len(case["support_markers"]) <= 2:
        retrieval_confidence = min(support_ratio, 0.6)
        evidence_coverage = min(support_ratio, 0.6)
        actionability_confidence = scores["actionability"] / 5
    else:
        retrieval_confidence = support_ratio
        evidence_coverage = support_ratio
        actionability_confidence = scores["actionability"] / 5

    uncertainty = build_uncertainty_split(
        retrieval_confidence=retrieval_confidence,
        evidence_coverage=evidence_coverage,
        contradiction_risk=contradiction_risk,
        actionability_confidence=actionability_confidence,
        personalization_conflict=personalization_conflict,
    )
    uncertainty_profile: dict[str, UncertaintyLevel] = {
        "retrieval_confidence": _label_uncertainty(uncertainty["retrieval_confidence"]),
        "evidence_coverage": _label_uncertainty(uncertainty["evidence_coverage"]),
        "contradiction_risk": _label_uncertainty(uncertainty["contradiction_risk"]),
        "actionability_confidence": _label_uncertainty(uncertainty["actionability_confidence"]),
        "personalization_conflict": _label_uncertainty(uncertainty["personalization_conflict"]),
    }

    sentences = [
        segment.strip() for segment in _SENTENCE_SPLIT_RE.split(case["response"]) if segment.strip()
    ]
    claim_records: list[ClaimEvidenceRecord] = []
    for sentence in sentences:
        sentence_support_markers = [
            marker for marker in case["support_markers"] if _contains_marker(sentence, marker)
        ]
        sentence_has_conflict = bool(hard_fail_reasons) or detect_contradiction_risk(sentence)
        if sentence_has_conflict:
            support_status = "contradicted"
            source_ids = ["policy_boundary"]
            evidence_mode = "heuristic"
        elif sentence_support_markers:
            support_status = "supported"
            source_ids = [
                f"marker:{marker.replace(' ', '_')}" for marker in sentence_support_markers
            ]
            evidence_mode = "direct_source"
        elif classify_claim_type(sentence) in {"recommendation", "emotional_framing"}:
            support_status = "partially_supported"
            source_ids = []
            evidence_mode = "heuristic"
        else:
            support_status = "unsupported"
            source_ids = []
            evidence_mode = "none"
        claim_records.append(
            build_claim_evidence_record(
                claim_type=classify_claim_type(sentence),
                support_status=support_status,
                source_ids=source_ids,
                evidence_mode=evidence_mode,
                conflict_flag=sentence_has_conflict,
            )
        )

    calibrated = select_calibrated_decision(
        claim_records=claim_records,
        uncertainty_split=uncertainty,
        boundary_blocked=bool(hard_fail_reasons),
    )
    return {
        "case_id": case["case_id"],
        "scenario": case["scenario"],
        "decision": calibrated["decision"],
        "decision_rationale": calibrated["rationale"],
        "boundary_class": case["boundary_class"],
        "scores": scores,
        "hard_fail_reasons": sorted(dict.fromkeys(hard_fail_reasons)),
        "uncertainty_profile": uncertainty_profile,
        "claim_records": claim_records,
    }


def evaluate_fitchef_replay_pack(payload: object) -> list[FitChefReplayResultRecord]:
    """Validate and evaluate the full FitChef replay pack."""

    pack = validate_fitchef_replay_pack(payload)
    return [evaluate_fitchef_replay_case(case) for case in pack["cases"]]


__all__ = [
    "FITCHEF_REPLAY_MODE",
    "JUDGMENT_EVAL_SCHEMA_VERSION",
    "SCORE_AXES",
    "UNCERTAINTY_LEVELS",
    "FitChefReplayCaseRecord",
    "FitChefReplayPackRecord",
    "FitChefReplayResultRecord",
    "FitChefReplayScoreRecord",
    "evaluate_fitchef_replay_case",
    "evaluate_fitchef_replay_pack",
    "validate_fitchef_replay_pack",
]

"""Deterministic judgment helpers for evidence-aware adjudication.

RU: Общие детерминированные helper-функции для claim taxonomy,
evidence reconciliation и uncertainty split.
EN: Shared deterministic helpers for claim taxonomy, evidence reconciliation,
and uncertainty splitting.
"""

from __future__ import annotations

import math
import re
from typing import Literal, TypedDict, cast

ClaimType = Literal[
    "fact",
    "source_grounded_summary",
    "inference",
    "recommendation",
    "speculation",
    "emotional_framing",
]
SupportStatus = Literal["supported", "partially_supported", "unsupported", "contradicted"]
EvidenceMode = Literal[
    "direct_source",
    "cross_source_synthesis",
    "deterministic_verifier",
    "heuristic",
    "none",
]

CLAIM_TYPES: tuple[ClaimType, ...] = (
    "fact",
    "source_grounded_summary",
    "inference",
    "recommendation",
    "speculation",
    "emotional_framing",
)
SUPPORT_STATUSES: tuple[SupportStatus, ...] = (
    "supported",
    "partially_supported",
    "unsupported",
    "contradicted",
)
EVIDENCE_MODES: tuple[EvidenceMode, ...] = (
    "direct_source",
    "cross_source_synthesis",
    "deterministic_verifier",
    "heuristic",
    "none",
)
PROMOTION_LABELS: tuple[str, ...] = ("promote", "defer", "discard")
JUDGMENT_FLOW: tuple[str, ...] = (
    "propose",
    "skeptic_pass",
    "contradiction_check",
    "uncertainty_split",
    "calibrated_decision",
    "promote_defer_discard",
)
CLAIM_EVIDENCE_FIELDS: tuple[str, ...] = (
    "claim_type",
    "support_status",
    "source_ids",
    "evidence_mode",
    "conflict_flag",
)
UNCERTAINTY_FIELDS: tuple[str, ...] = (
    "retrieval_confidence",
    "evidence_coverage",
    "contradiction_risk",
    "actionability_confidence",
    "personalization_conflict",
)

_RECOMMENDATION_RE = re.compile(
    r"\b(try|start|choose|plan|consider|focus on|keep|protect|pause|return|restart)\b",
    re.IGNORECASE,
)
_SPECULATION_RE = re.compile(
    r"\b(may|might|could|perhaps|possibly|seems?|appears?)\b",
    re.IGNORECASE,
)
_EMOTIONAL_FRAMING_RE = re.compile(
    r"\b(feel|feels|feeling|guilt|guilty|shame|ashamed|overwhelmed|frustrated|upset)\b",
    re.IGNORECASE,
)
_SUMMARY_RE = re.compile(
    r"\b(summary|according to|based on|the source|sources suggest)\b",
    re.IGNORECASE,
)
_INFERENCE_RE = re.compile(
    r"\b(because|therefore|suggests|implies|likely due to)\b",
    re.IGNORECASE,
)
_CONTRADICTION_RE = re.compile(
    r"\b(however|but|yet|despite|on the other hand|at the same time)\b",
    re.IGNORECASE,
)


class ClaimEvidenceRecord(TypedDict):
    """Shared claim-to-evidence record."""

    claim_type: ClaimType
    support_status: SupportStatus
    source_ids: list[str]
    evidence_mode: EvidenceMode
    conflict_flag: bool


class UncertaintySplit(TypedDict):
    """Internal uncertainty breakdown for judgment-capable outputs."""

    retrieval_confidence: float
    evidence_coverage: float
    contradiction_risk: float
    actionability_confidence: float
    personalization_conflict: float


def parse_claim_type(raw_value: str) -> ClaimType:
    """Normalize and validate claim taxonomy values."""

    if not isinstance(raw_value, str):
        raise ValueError("claim_type must be a string.")
    normalized = raw_value.strip().lower()
    if normalized not in CLAIM_TYPES:
        allowed = ", ".join(CLAIM_TYPES)
        raise ValueError(f"claim_type must be one of: {allowed}.")
    return cast(ClaimType, normalized)


def parse_support_status(raw_value: str) -> SupportStatus:
    """Normalize and validate support-status values."""

    if not isinstance(raw_value, str):
        raise ValueError("support_status must be a string.")
    normalized = raw_value.strip().lower()
    if normalized not in SUPPORT_STATUSES:
        allowed = ", ".join(SUPPORT_STATUSES)
        raise ValueError(f"support_status must be one of: {allowed}.")
    return cast(SupportStatus, normalized)


def parse_evidence_mode(raw_value: str) -> EvidenceMode:
    """Normalize and validate evidence-mode values."""

    if not isinstance(raw_value, str):
        raise ValueError("evidence_mode must be a string.")
    normalized = raw_value.strip().lower()
    if normalized not in EVIDENCE_MODES:
        allowed = ", ".join(EVIDENCE_MODES)
        raise ValueError(f"evidence_mode must be one of: {allowed}.")
    return cast(EvidenceMode, normalized)


def classify_claim_type(text: str) -> ClaimType:
    """Classify free text into the shared claim taxonomy deterministically."""

    stripped = " ".join(text.split())
    if not stripped:
        return "speculation"
    if _SUMMARY_RE.search(stripped):
        return "source_grounded_summary"
    if _RECOMMENDATION_RE.search(stripped):
        return "recommendation"
    if _EMOTIONAL_FRAMING_RE.search(stripped):
        return "emotional_framing"
    if _SPECULATION_RE.search(stripped):
        return "speculation"
    if _INFERENCE_RE.search(stripped):
        return "inference"
    return "fact"


def build_claim_evidence_record(
    *,
    claim_type: str,
    support_status: str,
    source_ids: list[str] | tuple[str, ...],
    evidence_mode: str,
    conflict_flag: bool,
) -> ClaimEvidenceRecord:
    """Build a normalized claim-to-evidence record."""

    if not isinstance(source_ids, (list, tuple)):
        raise ValueError("source_ids must be provided as a list or tuple of strings.")
    normalized_support_status = parse_support_status(support_status)
    normalized_evidence_mode = parse_evidence_mode(evidence_mode)
    normalized_source_ids: list[str] = []
    for item in source_ids:
        if not isinstance(item, str):
            raise ValueError("source_ids must contain only strings.")
        normalized_item = item.strip()
        if normalized_item:
            normalized_source_ids.append(normalized_item)
    if normalized_support_status == "supported":
        if normalized_evidence_mode == "none":
            raise ValueError("supported claims cannot use evidence_mode='none'.")
        if normalized_evidence_mode != "deterministic_verifier" and not normalized_source_ids:
            raise ValueError(
                "supported claims require source_ids or deterministic verifier evidence."
            )
    if normalized_support_status == "contradicted":
        if not normalized_source_ids:
            raise ValueError("contradicted claims require source_ids.")
        if not conflict_flag:
            raise ValueError("contradicted claims require conflict_flag=True.")
    if (
        normalized_evidence_mode in {"direct_source", "cross_source_synthesis"}
        and not normalized_source_ids
    ):
        raise ValueError("source_ids are required for source-backed evidence modes.")
    if not isinstance(conflict_flag, bool):
        raise ValueError("conflict_flag must be a bool.")
    return {
        "claim_type": parse_claim_type(claim_type),
        "support_status": normalized_support_status,
        "source_ids": list(dict.fromkeys(normalized_source_ids)),
        "evidence_mode": normalized_evidence_mode,
        "conflict_flag": conflict_flag,
    }


def detect_contradiction_risk(text: str) -> bool:
    """Return True when the text includes deterministic contradiction markers."""

    normalized = " ".join(text.split())
    if not normalized:
        return False
    return bool(_CONTRADICTION_RE.search(normalized))


def _clamp_probability(value: float) -> float:
    numeric_value = float(value)
    if math.isnan(numeric_value):
        return 0.0
    if numeric_value == math.inf:
        return 1.0
    if numeric_value == -math.inf:
        return 0.0
    return round(min(max(float(value), 0.0), 1.0), 4)


def build_uncertainty_split(
    *,
    retrieval_confidence: float,
    evidence_coverage: float,
    contradiction_risk: float,
    actionability_confidence: float,
    personalization_conflict: float,
) -> UncertaintySplit:
    """Normalize internal uncertainty dimensions into bounded probabilities."""

    return {
        "retrieval_confidence": _clamp_probability(retrieval_confidence),
        "evidence_coverage": _clamp_probability(evidence_coverage),
        "contradiction_risk": _clamp_probability(contradiction_risk),
        "actionability_confidence": _clamp_probability(actionability_confidence),
        "personalization_conflict": _clamp_probability(personalization_conflict),
    }


__all__ = [
    "CLAIM_TYPES",
    "CLAIM_EVIDENCE_FIELDS",
    "EVIDENCE_MODES",
    "JUDGMENT_FLOW",
    "PROMOTION_LABELS",
    "SUPPORT_STATUSES",
    "UNCERTAINTY_FIELDS",
    "ClaimEvidenceRecord",
    "ClaimType",
    "EvidenceMode",
    "SupportStatus",
    "UncertaintySplit",
    "build_claim_evidence_record",
    "build_uncertainty_split",
    "classify_claim_type",
    "detect_contradiction_risk",
    "parse_claim_type",
    "parse_evidence_mode",
    "parse_support_status",
]

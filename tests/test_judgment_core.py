"""Tests for deterministic judgment helpers."""

from __future__ import annotations

import pytest

from core.judgment import (
    CLAIM_EVIDENCE_FIELDS,
    CLAIM_TYPES,
    EVIDENCE_MODES,
    JUDGMENT_FLOW,
    PROMOTION_LABELS,
    SUPPORT_STATUSES,
    UNCERTAINTY_FIELDS,
    build_claim_evidence_record,
    build_uncertainty_split,
    classify_claim_type,
    detect_contradiction_risk,
    parse_claim_type,
    parse_evidence_mode,
    parse_support_status,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("fact", "fact"),
        ("source_grounded_summary", "source_grounded_summary"),
        ("inference", "inference"),
        ("recommendation", "recommendation"),
        ("speculation", "speculation"),
        ("emotional_framing", "emotional_framing"),
    ],
)
def test_parse_claim_type_accepts_shared_taxonomy(value: str, expected: str) -> None:
    """Claim taxonomy parsing must stay aligned with the shared contract."""

    assert parse_claim_type(value) == expected


@pytest.mark.parametrize("value", SUPPORT_STATUSES)
def test_parse_support_status_accepts_shared_values(value: str) -> None:
    """Support status parsing must stay aligned with the shared contract."""

    assert parse_support_status(value) == value


@pytest.mark.parametrize("value", EVIDENCE_MODES)
def test_parse_evidence_mode_accepts_shared_values(value: str) -> None:
    """Evidence mode parsing must stay aligned with the shared contract."""

    assert parse_evidence_mode(value) == value


def test_parse_claim_type_rejects_unknown_value() -> None:
    """Unknown taxonomy values must fail closed."""

    with pytest.raises(ValueError, match="claim_type must be one of"):
        parse_claim_type("narrative")


def test_parse_support_status_rejects_unknown_value() -> None:
    """Unknown support statuses must fail closed."""

    with pytest.raises(ValueError, match="support_status must be one of"):
        parse_support_status("weakly_supported")


def test_parse_evidence_mode_rejects_unknown_value() -> None:
    """Unknown evidence modes must fail closed."""

    with pytest.raises(ValueError, match="evidence_mode must be one of"):
        parse_evidence_mode("retrieval_only")


def test_shared_judgment_contract_constants_match_pr_a_expectations() -> None:
    """Shared contract constants must remain frozen for PR-A consumers."""

    assert CLAIM_TYPES == (
        "fact",
        "source_grounded_summary",
        "inference",
        "recommendation",
        "speculation",
        "emotional_framing",
    )
    assert CLAIM_EVIDENCE_FIELDS == (
        "claim_type",
        "support_status",
        "source_ids",
        "evidence_mode",
        "conflict_flag",
    )
    assert JUDGMENT_FLOW == (
        "propose",
        "skeptic_pass",
        "contradiction_check",
        "uncertainty_split",
        "calibrated_decision",
        "promote_defer_discard",
    )
    assert UNCERTAINTY_FIELDS == (
        "retrieval_confidence",
        "evidence_coverage",
        "contradiction_risk",
        "actionability_confidence",
        "personalization_conflict",
    )


def test_build_claim_evidence_record_normalizes_and_deduplicates() -> None:
    """Claim-to-evidence records must serialize deterministically."""

    record = build_claim_evidence_record(
        claim_type="recommendation",
        support_status="partially_supported",
        source_ids=["src-1", "src-1", "src-2"],
        evidence_mode="heuristic",
        conflict_flag=False,
    )

    assert record == {
        "claim_type": "recommendation",
        "support_status": "partially_supported",
        "source_ids": ["src-1", "src-2"],
        "evidence_mode": "heuristic",
        "conflict_flag": False,
    }


def test_build_claim_evidence_record_rejects_non_string_source_ids() -> None:
    """Malformed source identifiers must fail closed instead of leaking attribute errors."""

    with pytest.raises(ValueError, match="source_ids must contain only strings"):
        build_claim_evidence_record(
            claim_type="fact",
            support_status="supported",
            source_ids=["src-1", 2],  # type: ignore[list-item]
            evidence_mode="direct_source",
            conflict_flag=False,
        )


def test_detect_contradiction_risk_uses_deterministic_markers() -> None:
    """Contradiction detection must remain deterministic and local."""

    assert detect_contradiction_risk("However, the same plan also says the opposite.") is True
    assert detect_contradiction_risk("Keep one steady dinner plan this week.") is False


def test_build_uncertainty_split_clamps_values() -> None:
    """Uncertainty split must stay bounded across all dimensions."""

    split = build_uncertainty_split(
        retrieval_confidence=1.2,
        evidence_coverage=-0.5,
        contradiction_risk=0.33333,
        actionability_confidence=0.8,
        personalization_conflict=9.0,
    )

    assert split == {
        "retrieval_confidence": 1.0,
        "evidence_coverage": 0.0,
        "contradiction_risk": 0.3333,
        "actionability_confidence": 0.8,
        "personalization_conflict": 1.0,
    }


def test_classify_claim_type_prefers_safe_degradation() -> None:
    """Claim classification should downgrade ambiguous language toward softer types."""

    assert (
        classify_claim_type("Sources suggest this pattern may help.") == "source_grounded_summary"
    )
    assert classify_claim_type("You may try one calmer dinner reset.") == "recommendation"
    assert classify_claim_type("This might explain the drop.") == "speculation"
    assert PROMOTION_LABELS == ("promote", "defer", "discard")

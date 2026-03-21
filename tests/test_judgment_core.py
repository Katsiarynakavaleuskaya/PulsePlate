"""Tests for deterministic judgment helpers."""

from __future__ import annotations

from typing import cast

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
    normalize_claim_evidence_records,
    parse_claim_type,
    parse_evidence_mode,
    parse_support_status,
    select_calibrated_decision,
    validate_uncertainty_split,
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


def test_parse_claim_type_rejects_non_string_value() -> None:
    """Non-string claim types must fail closed."""

    with pytest.raises(ValueError, match="claim_type must be a string"):
        parse_claim_type(1)  # type: ignore[arg-type]


def test_parse_support_status_rejects_unknown_value() -> None:
    """Unknown support statuses must fail closed."""

    with pytest.raises(ValueError, match="support_status must be one of"):
        parse_support_status("weakly_supported")


def test_parse_support_status_rejects_non_string_value() -> None:
    """Non-string support statuses must fail closed."""

    with pytest.raises(ValueError, match="support_status must be a string"):
        parse_support_status(1)  # type: ignore[arg-type]


def test_parse_evidence_mode_rejects_unknown_value() -> None:
    """Unknown evidence modes must fail closed."""

    with pytest.raises(ValueError, match="evidence_mode must be one of"):
        parse_evidence_mode("retrieval_only")


def test_parse_evidence_mode_rejects_non_string_value() -> None:
    """Non-string evidence modes must fail closed."""

    with pytest.raises(ValueError, match="evidence_mode must be a string"):
        parse_evidence_mode(1)  # type: ignore[arg-type]


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
            source_ids=cast(list[str], ["src-1", 2]),
            evidence_mode="direct_source",
            conflict_flag=False,
        )


def test_build_claim_evidence_record_rejects_scalar_source_ids() -> None:
    """Scalar source_ids payloads must fail instead of iterating as characters."""

    with pytest.raises(ValueError, match="source_ids must be provided as a list or tuple"):
        build_claim_evidence_record(
            claim_type="fact",
            support_status="supported",
            source_ids=cast(list[str] | tuple[str, ...], "src-1"),
            evidence_mode="direct_source",
            conflict_flag=False,
        )


def test_build_claim_evidence_record_rejects_supported_claim_without_evidence() -> None:
    """Supported claims must not serialize without source or verifier backing."""

    with pytest.raises(
        ValueError,
        match="supported claims require source_ids or deterministic verifier evidence",
    ):
        build_claim_evidence_record(
            claim_type="fact",
            support_status="supported",
            source_ids=[],
            evidence_mode="direct_source",
            conflict_flag=False,
        )


def test_build_claim_evidence_record_rejects_supported_claim_with_no_evidence_mode() -> None:
    """Supported claims must not claim support while using the no-evidence mode."""

    with pytest.raises(ValueError, match="supported claims cannot use evidence_mode='none'"):
        build_claim_evidence_record(
            claim_type="fact",
            support_status="supported",
            source_ids=[],
            evidence_mode="none",
            conflict_flag=False,
        )


def test_build_claim_evidence_record_rejects_source_backed_mode_without_sources() -> None:
    """Source-backed evidence modes must carry explicit source identifiers."""

    with pytest.raises(
        ValueError, match="source_ids are required for source-backed evidence modes"
    ):
        build_claim_evidence_record(
            claim_type="source_grounded_summary",
            support_status="partially_supported",
            source_ids=[],
            evidence_mode="cross_source_synthesis",
            conflict_flag=False,
        )


def test_build_claim_evidence_record_rejects_non_bool_conflict_flag() -> None:
    """Conflict flags must stay typed as booleans, not truthy strings."""

    with pytest.raises(ValueError, match="conflict_flag must be a bool"):
        build_claim_evidence_record(
            claim_type="fact",
            support_status="supported",
            source_ids=["src-1"],
            evidence_mode="direct_source",
            conflict_flag="false",  # type: ignore[arg-type]
        )


def test_build_claim_evidence_record_rejects_contradicted_claim_without_sources() -> None:
    """Contradicted claims still need explicit evidence linkage."""

    with pytest.raises(ValueError, match="contradicted claims require source_ids"):
        build_claim_evidence_record(
            claim_type="fact",
            support_status="contradicted",
            source_ids=[],
            evidence_mode="heuristic",
            conflict_flag=True,
        )


def test_build_claim_evidence_record_rejects_contradicted_claim_without_conflict_flag() -> None:
    """Contradicted claims must explicitly carry the conflict flag."""

    with pytest.raises(ValueError, match="contradicted claims require conflict_flag=True"):
        build_claim_evidence_record(
            claim_type="fact",
            support_status="contradicted",
            source_ids=["src-1"],
            evidence_mode="direct_source",
            conflict_flag=False,
        )


def test_normalize_claim_evidence_records_normalizes_collections() -> None:
    """Collections of claim records must normalize through the shared builder."""

    records = normalize_claim_evidence_records(
        [
            {
                "claim_type": "recommendation",
                "support_status": "supported",
                "source_ids": ["marker:next_meal"],
                "evidence_mode": "direct_source",
                "conflict_flag": False,
            }
        ]
    )

    assert records == [
        {
            "claim_type": "recommendation",
            "support_status": "supported",
            "source_ids": ["marker:next_meal"],
            "evidence_mode": "direct_source",
            "conflict_flag": False,
        }
    ]


def test_normalize_claim_evidence_records_rejects_non_sequence_payload() -> None:
    """Scalar record payloads must fail closed before normalization starts."""

    with pytest.raises(ValueError, match="claim_evidence_records must be provided as a sequence"):
        normalize_claim_evidence_records(1)  # type: ignore[arg-type]


def test_normalize_claim_evidence_records_rejects_non_mapping_member() -> None:
    """Every claim record item must remain object-shaped."""

    with pytest.raises(ValueError, match="claim_evidence_record #1 must be an object"):
        normalize_claim_evidence_records(["not-a-record"])  # type: ignore[list-item]


def test_validate_uncertainty_split_requires_all_fields() -> None:
    """Missing uncertainty fields must fail closed."""

    with pytest.raises(ValueError, match="uncertainty_split is missing required fields"):
        validate_uncertainty_split({"retrieval_confidence": 0.5})


def test_validate_uncertainty_split_rejects_non_float_like_values() -> None:
    """Non numeric uncertainty payloads must fail with deterministic field errors."""

    with pytest.raises(ValueError, match="retrieval_confidence must be a float-like value"):
        validate_uncertainty_split(
            {
                "retrieval_confidence": True,
                "evidence_coverage": 0.8,
                "contradiction_risk": 0.1,
                "actionability_confidence": 0.9,
                "personalization_conflict": 0.1,
            }
        )


def test_validate_uncertainty_split_rejects_unparseable_string_values() -> None:
    """Unparseable numeric strings must fail closed instead of coercing silently."""

    with pytest.raises(ValueError, match="evidence_coverage must be a float-like value"):
        validate_uncertainty_split(
            {
                "retrieval_confidence": 0.7,
                "evidence_coverage": "not-a-number",
                "contradiction_risk": 0.1,
                "actionability_confidence": 0.9,
                "personalization_conflict": 0.1,
            }
        )


def test_validate_uncertainty_split_rejects_float_type_errors() -> None:
    """Custom float-like failures must still collapse into the shared ValueError."""

    class BrokenFloat(str):
        def __float__(self) -> float:
            raise TypeError("broken float conversion")

    with pytest.raises(ValueError, match="evidence_coverage must be a float-like value"):
        validate_uncertainty_split(
            {
                "retrieval_confidence": 0.7,
                "evidence_coverage": BrokenFloat("0.5"),
                "contradiction_risk": 0.1,
                "actionability_confidence": 0.9,
                "personalization_conflict": 0.1,
            }
        )


def test_select_calibrated_decision_promotes_supported_low_conflict_payload() -> None:
    """Supported claims with bounded uncertainty should promote."""

    decision = select_calibrated_decision(
        claim_records=[
            {
                "claim_type": "recommendation",
                "support_status": "supported",
                "source_ids": ["marker:next_meal"],
                "evidence_mode": "direct_source",
                "conflict_flag": False,
            }
        ],
        uncertainty_split={
            "retrieval_confidence": 0.9,
            "evidence_coverage": 0.8,
            "contradiction_risk": 0.1,
            "actionability_confidence": 0.9,
            "personalization_conflict": 0.1,
        },
    )

    assert decision["decision"] == "promote"


def test_select_calibrated_decision_discards_contradicted_payload() -> None:
    """Contradicted claims must discard even when actionability looks high."""

    decision = select_calibrated_decision(
        claim_records=[
            {
                "claim_type": "fact",
                "support_status": "contradicted",
                "source_ids": ["policy_boundary"],
                "evidence_mode": "heuristic",
                "conflict_flag": True,
            }
        ],
        uncertainty_split={
            "retrieval_confidence": 0.9,
            "evidence_coverage": 0.9,
            "contradiction_risk": 0.9,
            "actionability_confidence": 0.9,
            "personalization_conflict": 0.1,
        },
    )

    assert decision["decision"] == "discard"


def test_select_calibrated_decision_discards_high_contradiction_risk() -> None:
    """High contradiction risk must discard even when the claim is otherwise supported."""

    decision = select_calibrated_decision(
        claim_records=[
            {
                "claim_type": "recommendation",
                "support_status": "supported",
                "source_ids": ["marker:next_meal"],
                "evidence_mode": "direct_source",
                "conflict_flag": False,
            }
        ],
        uncertainty_split={
            "retrieval_confidence": 0.9,
            "evidence_coverage": 0.8,
            "contradiction_risk": 0.7,
            "actionability_confidence": 0.9,
            "personalization_conflict": 0.1,
        },
    )

    assert decision == {
        "decision": "discard",
        "rationale": "contradiction risk remains too high",
    }


def test_select_calibrated_decision_discards_high_personalization_conflict() -> None:
    """High personalization conflict must block promotion deterministically."""

    decision = select_calibrated_decision(
        claim_records=[
            {
                "claim_type": "recommendation",
                "support_status": "supported",
                "source_ids": ["marker:next_meal"],
                "evidence_mode": "direct_source",
                "conflict_flag": False,
            }
        ],
        uncertainty_split={
            "retrieval_confidence": 0.9,
            "evidence_coverage": 0.8,
            "contradiction_risk": 0.1,
            "actionability_confidence": 0.9,
            "personalization_conflict": 0.8,
        },
    )

    assert decision == {
        "decision": "discard",
        "rationale": "personalization conflict remains too high",
    }


def test_select_calibrated_decision_discards_unsupported_low_actionability_payload() -> None:
    """Unsupported low-actionability payloads must discard instead of defer."""

    decision = select_calibrated_decision(
        claim_records=[
            {
                "claim_type": "speculation",
                "support_status": "unsupported",
                "source_ids": [],
                "evidence_mode": "none",
                "conflict_flag": False,
            }
        ],
        uncertainty_split={
            "retrieval_confidence": 0.2,
            "evidence_coverage": 0.2,
            "contradiction_risk": 0.1,
            "actionability_confidence": 0.2,
            "personalization_conflict": 0.1,
        },
    )

    assert decision == {
        "decision": "discard",
        "rationale": "insufficient support for a promotable judgment",
    }


def test_detect_contradiction_risk_uses_deterministic_markers() -> None:
    """Contradiction detection must remain deterministic and local."""

    assert detect_contradiction_risk("However, the same plan also says the opposite.") is True
    assert detect_contradiction_risk("Keep one steady dinner plan this week.") is False


def test_detect_contradiction_risk_rejects_empty_signal() -> None:
    """Blank text must not emit contradiction risk noise."""

    assert detect_contradiction_risk("   ") is False


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


def test_build_uncertainty_split_sanitizes_non_finite_values() -> None:
    """NaN and infinities must collapse to bounded deterministic values."""

    split = build_uncertainty_split(
        retrieval_confidence=float("nan"),
        evidence_coverage=float("inf"),
        contradiction_risk=float("-inf"),
        actionability_confidence=0.4,
        personalization_conflict=float("nan"),
    )

    assert split == {
        "retrieval_confidence": 0.0,
        "evidence_coverage": 1.0,
        "contradiction_risk": 0.0,
        "actionability_confidence": 0.4,
        "personalization_conflict": 0.0,
    }


def test_classify_claim_type_prefers_safe_degradation() -> None:
    """Claim classification should downgrade ambiguous language toward softer types."""

    assert (
        classify_claim_type("Sources suggest this pattern may help.") == "source_grounded_summary"
    )
    assert classify_claim_type("You may try one calmer dinner reset.") == "recommendation"
    assert classify_claim_type("This might explain the drop.") == "speculation"
    assert PROMOTION_LABELS == ("promote", "defer", "discard")


def test_classify_claim_type_avoids_false_positive_emotional_framing() -> None:
    """Generic wording should not overfire into emotional framing."""

    assert classify_claim_type("The source says calm eating lowers stress.") == (
        "source_grounded_summary"
    )
    assert classify_claim_type("This kind of pattern appears in the data.") == "speculation"


def test_classify_claim_type_covers_remaining_taxonomy_branches() -> None:
    """Classification should cover emotional framing, inference, and fact fallbacks."""

    assert classify_claim_type("This feels scary and overwhelming right now.") == (
        "emotional_framing"
    )
    assert classify_claim_type("The evidence suggests a mismatch in timing.") == "inference"
    assert classify_claim_type("Protein intake stays stable across the week.") == "fact"

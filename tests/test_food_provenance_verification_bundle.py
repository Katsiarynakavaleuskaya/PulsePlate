"""Deterministic tests for internal food provenance verification bundles."""

from __future__ import annotations

import math

from core.food_provenance_verification import (
    FoodProvenanceTrace,
    build_food_provenance_traces_from_record,
    build_food_provenance_verification_bundle,
    build_meal_plan_food_provenance_bundle,
)


def test_food_provenance_bundle_is_deterministic_and_internal_only() -> None:
    traces = (
        FoodProvenanceTrace(
            source="USDA Foundation",
            record_id="FDB-123",
            nutrient="protein_g",
            confidence=0.93,
            provenance="USDA Foundation",
            version_ref="2026-04",
        ),
        FoodProvenanceTrace(
            source="Open Food Facts",
            record_id="OFF-999",
            nutrient="fiber_g",
            confidence=0.81,
            provenance="Open Food Facts",
            version_ref="snapshot 2026-04",
        ),
    )

    first = build_food_provenance_verification_bundle(tuple(reversed(traces)))
    second = build_food_provenance_verification_bundle(traces)

    assert first == second
    assert first.admission_allowed is True
    assert first.overall_status == "pass"
    assert first.reason_codes == (
        "food_provenance_present",
        "food_confidence_valid",
        "food_trace_lineage_present",
    )
    assert first.provenance is not None
    assert first.provenance.context_item_digests
    assert first.provenance.answer_digest is None

    evidence_refs = tuple(ref for artifact in first.artifacts for ref in artifact.evidence_refs)
    unique_evidence_refs = tuple(dict.fromkeys(evidence_refs))
    assert unique_evidence_refs == tuple(sorted(unique_evidence_refs))
    assert unique_evidence_refs == (
        "food:open_food_facts:off-999:fiber_g",
        "food:usda_foundation:fdb-123:protein_g",
    )
    assert all("http" not in ref and "/" not in ref for ref in unique_evidence_refs)


def test_food_provenance_bundle_fails_closed_for_missing_traces() -> None:
    bundle = build_food_provenance_verification_bundle(())

    assert bundle.admission_allowed is False
    assert bundle.overall_status == "fail"
    assert bundle.reason_codes == (
        "food_provenance_missing",
        "food_confidence_missing",
        "food_trace_lineage_missing",
    )
    assert bundle.provenance is not None
    assert bundle.provenance.context_item_digests == ()


def test_food_provenance_bundle_fails_closed_for_low_or_missing_confidence() -> None:
    low_confidence = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="usda",
                record_id="fdb-1",
                nutrient="kcal",
                confidence=0.69,
                provenance="usda",
            ),
        )
    )
    missing_confidence = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="usda",
                record_id="fdb-1",
                nutrient="kcal",
                confidence=math.inf,
                provenance="usda",
            ),
        )
    )

    assert low_confidence.admission_allowed is False
    assert "food_confidence_below_threshold" in low_confidence.reason_codes
    assert missing_confidence.admission_allowed is False
    assert "food_confidence_non_finite" in missing_confidence.reason_codes


def test_food_provenance_bundle_fails_closed_for_blank_source_provenance() -> None:
    bundle = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="   ",
                record_id="fdb-1",
                nutrient="kcal",
                confidence=0.91,
                provenance="   ",
            ),
        )
    )

    assert bundle.admission_allowed is False
    assert bundle.reason_codes == (
        "food_provenance_missing",
        "food_confidence_missing",
        "food_trace_lineage_missing",
    )


def test_food_provenance_bundle_rejects_bool_confidence() -> None:
    bundle = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="usda",
                record_id="fdb-1",
                nutrient="kcal",
                confidence=True,
                provenance="usda",
            ),
        )
    )

    assert bundle.admission_allowed is False
    assert "food_confidence_missing" in bundle.reason_codes


def test_food_provenance_bundle_falls_back_for_invalid_min_confidence() -> None:
    bundle = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="usda",
                record_id="fdb-1",
                nutrient="kcal",
                confidence=0.0,
                provenance="usda",
            ),
        ),
        min_confidence=-1.0,
    )

    assert bundle.admission_allowed is False
    assert "food_confidence_below_threshold" in bundle.reason_codes


def test_food_provenance_bundle_rejects_out_of_range_confidence() -> None:
    direct_bundle = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="usda",
                record_id="fdb-1",
                nutrient="kcal",
                confidence=1.01,
                provenance="usda",
            ),
        )
    )
    record_bundle = build_meal_plan_food_provenance_bundle(
        (
            {
                "nutrition_inputs": [
                    {
                        "source": "usda",
                        "record_id": "fdb-1",
                        "nutrients": {"kcal": 120.0},
                    }
                ],
                "nutrition_provenance": {"kcal": "usda"},
                "nutrition_nutrient_confidence": {"kcal": 999.0},
            },
        )
    )

    assert direct_bundle.admission_allowed is False
    assert "food_confidence_out_of_range" in direct_bundle.reason_codes
    assert record_bundle.admission_allowed is False
    assert "food_confidence_out_of_range" in record_bundle.reason_codes


def test_food_provenance_traces_from_merged_record_include_source_lineage() -> None:
    record = {
        "nutrition_inputs": [
            {
                "source": "USDA Foundation",
                "record_id": "FDB-123",
                "version_ref": "2026-04",
                "nutrients": {"kcal": 120.0, "protein_g": 8.5},
                "raw_payload": {"private_marker": "should-not-enter-lineage"},
            }
        ],
        "nutrition_provenance": {
            "kcal": "USDA Foundation",
            "protein_g": "USDA Foundation",
        },
        "nutrition_nutrient_confidence": {"kcal": 0.91, "protein_g": 0.89},
        "nutrition_confidence": 0.9,
    }

    traces = build_food_provenance_traces_from_record(record)
    bundle = build_meal_plan_food_provenance_bundle((record,))

    assert [trace.nutrient for trace in traces] == ["kcal", "protein_g"]
    assert {trace.record_id for trace in traces} == {"fdb-123"}
    assert {trace.version_ref for trace in traces} == {"2026-04"}
    assert bundle.admission_allowed is True

    evidence_refs = tuple(ref for artifact in bundle.artifacts for ref in artifact.evidence_refs)
    assert "food:usda_foundation:fdb-123:kcal" in evidence_refs
    assert "private_marker" not in " ".join(evidence_refs)


def test_food_provenance_traces_use_record_confidence_fallback() -> None:
    record = {
        "nutrition_inputs": [
            {
                "source": "USDA Foundation",
                "record_id": "FDB-123",
                "version_ref": "2026-04",
                "nutrients": {"kcal": 120.0, "protein_g": 8.5},
            }
        ],
        "nutrition_provenance": {
            "kcal": "USDA Foundation",
            "protein_g": "USDA Foundation",
        },
        "nutrition_nutrient_confidence": {"kcal": 0.91},
        "nutrition_confidence": 0.88,
    }

    traces = build_food_provenance_traces_from_record(record)

    assert {trace.nutrient: trace.confidence for trace in traces} == {
        "kcal": 0.91,
        "protein_g": 0.88,
    }


def test_food_provenance_trace_tokens_do_not_leak_raw_url_or_path_values() -> None:
    bundle = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="https://example.test/provider path",
                record_id="/Users/alice/private/FDB 123",
                nutrient="protein g",
                confidence=0.91,
                provenance="https://example.test/provider path",
                version_ref="C:\\tmp\\snapshot 2026",
            ),
        )
    )
    evidence_refs = tuple(ref for artifact in bundle.artifacts for ref in artifact.evidence_refs)
    joined_refs = " ".join(evidence_refs)

    assert bundle.admission_allowed is False
    assert "food_provenance_missing" in bundle.reason_codes
    assert "http" not in joined_refs
    assert "/" not in joined_refs
    assert "\\" not in joined_refs
    assert "users" not in joined_refs


def test_food_provenance_trace_rejects_path_like_record_and_version_values() -> None:
    bundle = build_food_provenance_verification_bundle(
        (
            FoodProvenanceTrace(
                source="usda",
                record_id="/etc/passwd",
                nutrient="kcal",
                confidence=0.91,
                provenance="usda",
                version_ref="C:\\tmp\\snapshot",
            ),
            FoodProvenanceTrace(
                source="off",
                record_id="www.example.com/path",
                nutrient="protein_g",
                confidence=0.91,
                provenance="off",
                version_ref="../snapshot",
            ),
        )
    )
    evidence_refs = tuple(ref for artifact in bundle.artifacts for ref in artifact.evidence_refs)
    joined_refs = " ".join(evidence_refs)

    assert bundle.admission_allowed is False
    assert "food_trace_lineage_incomplete" in bundle.reason_codes
    assert "etc" not in joined_refs
    assert "passwd" not in joined_refs
    assert "example" not in joined_refs
    assert "snapshot" not in joined_refs


def test_food_provenance_traces_fail_closed_on_ambiguous_duplicate_source() -> None:
    record = {
        "nutrition_inputs": [
            {
                "source": "USDA Foundation",
                "record_id": "FDB-123",
                "version_ref": "2026-04",
                "nutrients": {"kcal": 120.0},
            },
            {
                "source": "USDA Foundation",
                "record_id": "FDB-456",
                "version_ref": "2026-05",
                "nutrients": {"kcal": 122.0},
            },
        ],
        "nutrition_provenance": {"kcal": "USDA Foundation"},
        "nutrition_nutrient_confidence": {"kcal": 0.91},
    }

    bundle = build_meal_plan_food_provenance_bundle((record,))
    evidence_refs = tuple(ref for artifact in bundle.artifacts for ref in artifact.evidence_refs)

    assert bundle.admission_allowed is False
    assert "food_trace_lineage_incomplete" in bundle.reason_codes
    assert "food:usda_foundation:unknown:kcal" in evidence_refs
    assert "fdb-123" not in " ".join(evidence_refs)
    assert "fdb-456" not in " ".join(evidence_refs)

"""Deterministic tests for internal FitChef claim/evidence field assurance."""

from __future__ import annotations

from dataclasses import replace
import json
import math

import pytest
from pydantic import ValidationError

from app.schemas.fitchef import (
    FitChefDistortionFieldAssuranceAssessmentV1,
    FitChefFieldAssuranceRecordV1,
)
from app.services.fitchef_claim_evidence_assurance import (
    FitChefSourceOccurrenceV1,
    FitChefSourceSnapshotV1,
    build_distortion_field_assurance_assessment,
    build_distortion_field_assurance_unavailable,
    build_fitchef_source_items,
    build_fitchef_source_prompt_context,
    freeze_fitchef_source_snapshot,
)
from core.evidence.fingerprints import JsonValue, fingerprint_payload

EXPECTED_FIELD_ORDER = (
    "distortion_labels",
    "why_it_matches",
    "evidence_for",
    "evidence_against",
    "balanced_reframe",
    "next_small_action",
)


def _occurrence(
    ordinal: int,
    *,
    chunk_id: str,
    file: str,
    content: str,
    preview: str,
    score: float,
) -> FitChefSourceOccurrenceV1:
    return FitChefSourceOccurrenceV1(
        ordinal=ordinal,
        chunk_id=chunk_id,
        file=file,
        content=content,
        preview=preview,
        score=score,
    )


def _two_sources() -> tuple[FitChefSourceOccurrenceV1, ...]:
    return (
        _occurrence(
            0,
            chunk_id="chunk-alpha",
            file="docs/cbt/alpha.md",
            content="Sanitized alpha context.",
            preview="Alpha preview",
            score=0.91,
        ),
        _occurrence(
            1,
            chunk_id="chunk-beta",
            file="docs/cbt/beta.md",
            content="Sanitized beta context.",
            preview="Beta preview",
            score=0.73,
        ),
    )


def _build_assessment(
    snapshot: FitChefSourceSnapshotV1,
) -> FitChefDistortionFieldAssuranceAssessmentV1:
    return build_distortion_field_assurance_assessment(
        snapshot,
        result_sources=build_fitchef_source_items(snapshot),
    )


def test_unique_snapshot_has_exact_fingerprint_and_ordered_opaque_refs() -> None:
    """Unique admitted occurrences link only the reframe to ordered opaque candidates."""

    occurrences = _two_sources()
    snapshot = freeze_fitchef_source_snapshot(occurrences)
    assessment = _build_assessment(snapshot)

    expected_manifest: list[JsonValue] = []
    for occurrence in occurrences:
        content_fingerprint = fingerprint_payload(
            {
                "schema_version": "fitchef_source_content.v1",
                "content": occurrence.content,
            }
        )
        expected_manifest.append(
            {
                "ordinal": occurrence.ordinal,
                "chunk_id": occurrence.chunk_id,
                "file": occurrence.file,
                "content_fingerprint": content_fingerprint,
                "preview": occurrence.preview,
                "score": occurrence.score,
            }
        )
    expected_snapshot_fingerprint = fingerprint_payload(
        {
            "schema_version": "fitchef_source_snapshot.v1",
            "occurrences": expected_manifest,
        }
    )
    expected_refs = tuple(
        fingerprint_payload(
            {
                "schema_version": "fitchef_source_occurrence_ref.v1",
                "source_snapshot_fingerprint": expected_snapshot_fingerprint,
                "ordinal": occurrence.ordinal,
                "chunk_id": occurrence.chunk_id,
            }
        )
        for occurrence in occurrences
    )

    assert snapshot.source_snapshot_fingerprint == expected_snapshot_fingerprint
    assert tuple(record.field_path for record in assessment.records) == EXPECTED_FIELD_ORDER
    assert assessment.records[4].assurance_state == "candidate_linked_unverified"
    assert assessment.records[4].candidate_source_refs == expected_refs
    assert all(not record.candidate_source_refs for record in assessment.records[:4])
    assert not assessment.records[5].candidate_source_refs
    assert assessment.assessed_field_count == 6
    assert assessment.request_context_only_count == 4
    assert assessment.evidence_sensitive_field_count == 1
    assert assessment.candidate_linked_unverified_count == 1
    assert assessment.evidence_link_missing_count == 0
    assert assessment.source_snapshot_mismatch_count == 0
    assert assessment.assessment_unavailable_count == 0
    assert assessment.support_claimed_count == 0
    assert all(record.adjudicated_support_status is None for record in assessment.records)
    assert all(record.conflict_adjudicated is False for record in assessment.records)


def test_assessment_is_frozen_extra_forbid_and_serializes_no_raw_source_values() -> None:
    """Assurance output exposes only digests and fixed negative-authority metadata."""

    assessment = _build_assessment(freeze_fitchef_source_snapshot(_two_sources()))
    serialized = assessment.model_dump_json()

    for raw_value in (
        "chunk-alpha",
        "chunk-beta",
        "docs/cbt/alpha.md",
        "Sanitized alpha context.",
        "Alpha preview",
    ):
        assert raw_value not in serialized
    assert assessment.public_response_authority is False
    assert assessment.provider_retry_authority is False
    assert assessment.cache_admission_authority is False
    assert assessment.knowledge_promotion_authority is False
    assert assessment.plan_mutation_authority is False

    with pytest.raises(ValidationError):
        setattr(assessment, "assessed_field_count", 5)
    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(
            {**assessment.model_dump(mode="python"), "unexpected": "blocked"}
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("assessed_field_count", 5),
        ("request_context_only_count", 3),
        ("evidence_sensitive_field_count", 0),
        ("candidate_linked_unverified_count", 0),
        ("support_claimed_count", 1),
        ("public_response_authority", True),
        ("provider_retry_authority", True),
        ("cache_admission_authority", True),
        ("knowledge_promotion_authority", True),
        ("plan_mutation_authority", True),
    ],
)
def test_assessment_rejects_count_and_authority_drift(
    field_name: str,
    invalid_value: object,
) -> None:
    """Caller-supplied counts and authority flags cannot widen the v1 contract."""

    assessment = _build_assessment(freeze_fitchef_source_snapshot(_two_sources()))
    payload = assessment.model_dump(mode="python")
    payload[field_name] = invalid_value

    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(payload)


def test_record_rejects_support_conflict_order_and_non_reframe_refs() -> None:
    """Records remain null-only, conflict-negative, ordered, and surface-specific."""

    assessment = _build_assessment(freeze_fitchef_source_snapshot(_two_sources()))
    first_payload = assessment.records[0].model_dump(mode="python")

    with pytest.raises(ValidationError):
        FitChefFieldAssuranceRecordV1.model_validate(
            {**first_payload, "adjudicated_support_status": "supported"}
        )
    with pytest.raises(ValidationError):
        FitChefFieldAssuranceRecordV1.model_validate(
            {**first_payload, "conflict_adjudicated": True}
        )
    with pytest.raises(ValidationError):
        FitChefFieldAssuranceRecordV1.model_validate(
            {
                **first_payload,
                "candidate_source_refs": ("sha256:" + "0" * 64,),
            }
        )

    assessment_payload = assessment.model_dump(mode="python")
    assessment_payload["records"] = tuple(reversed(assessment.records))
    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(assessment_payload)


def test_record_json_schema_is_structurally_null_only_for_support_status() -> None:
    """The v1 schema must not advertise positive support statuses as valid input."""

    schema = FitChefFieldAssuranceRecordV1.model_json_schema()
    serialized_schema = json.dumps(schema, sort_keys=True)
    for positive_status in (
        "supported",
        "partially_supported",
        "unsupported",
        "contradicted",
    ):
        assert positive_status not in serialized_schema

    properties = schema["properties"]
    support_property = properties["adjudicated_support_status"]
    assert support_property.get("type") == "null"
    assert "anyOf" not in support_property
    assert "oneOf" not in support_property

    first_payload = (
        _build_assessment(freeze_fitchef_source_snapshot(_two_sources()))
        .records[0]
        .model_dump(mode="python")
    )
    for positive_status in (
        "supported",
        "partially_supported",
        "unsupported",
        "contradicted",
    ):
        with pytest.raises(ValidationError):
            FitChefFieldAssuranceRecordV1.model_validate(
                {**first_payload, "adjudicated_support_status": positive_status}
            )


def test_assessment_rejects_partial_or_mixed_unavailability() -> None:
    """Unavailable is one all-six deterministic state, never a per-field mixture."""

    ordinary = _build_assessment(freeze_fitchef_source_snapshot(_two_sources()))
    partial_payload = ordinary.model_dump(mode="python")
    first_record = ordinary.records[0].model_dump(mode="python")
    partial_payload["records"] = (
        FitChefFieldAssuranceRecordV1.model_validate(
            {
                **first_record,
                "assurance_state": "assessment_unavailable",
                "reason_codes": ("assessment_unavailable",),
            }
        ),
        *ordinary.records[1:],
    )
    partial_payload["request_context_only_count"] = 3
    partial_payload["assessment_unavailable_count"] = 1
    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(partial_payload)

    unavailable = build_distortion_field_assurance_unavailable(reason_code="assessment_unavailable")
    mixed_payload = unavailable.model_dump(mode="python")
    mixed_first = unavailable.records[0].model_dump(mode="python")
    mixed_payload["records"] = (
        FitChefFieldAssuranceRecordV1.model_validate(
            {**mixed_first, "reason_codes": ("snapshot_fingerprint_unavailable",)}
        ),
        *unavailable.records[1:],
    )
    with pytest.raises(ValidationError):
        FitChefDistortionFieldAssuranceAssessmentV1.model_validate(mixed_payload)


def test_empty_snapshot_marks_only_balanced_reframe_as_missing() -> None:
    """An ordinary empty snapshot is a missing candidate link, not support adjudication."""

    assessment = _build_assessment(freeze_fitchef_source_snapshot(()))

    assert assessment.source_snapshot_fingerprint is not None
    assert assessment.records[4].assurance_state == "evidence_link_missing"
    assert assessment.records[4].reason_codes == ("candidate_sources_missing",)
    assert assessment.records[4].candidate_source_refs == ()
    assert assessment.evidence_link_missing_count == 1
    assert assessment.candidate_linked_unverified_count == 0


def test_duplicate_chunk_identity_preserves_occurrences_but_blocks_candidate_refs() -> None:
    """Duplicate retrieved identities stay visible while assurance fails closed."""

    duplicate_snapshot = freeze_fitchef_source_snapshot(
        (
            _occurrence(
                0,
                chunk_id="duplicate",
                file="docs/cbt/first.md",
                content="First occurrence.",
                preview="First",
                score=0.8,
            ),
            _occurrence(
                1,
                chunk_id="duplicate",
                file="docs/cbt/second.md",
                content="Second occurrence.",
                preview="Second",
                score=0.7,
            ),
        )
    )
    assessment = _build_assessment(duplicate_snapshot)

    assert len(duplicate_snapshot.occurrences) == 2
    assert build_fitchef_source_prompt_context(duplicate_snapshot).count("occurrence") == 2
    assert len(build_fitchef_source_items(duplicate_snapshot)) == 2
    assert assessment.records[4].assurance_state == "source_snapshot_mismatch"
    assert assessment.records[4].reason_codes == ("duplicate_source_identity",)
    assert assessment.records[4].candidate_source_refs == ()
    assert assessment.source_snapshot_mismatch_count == 1


def test_projection_or_fingerprint_drift_blocks_candidate_refs() -> None:
    """Any post-freeze projection or fingerprint drift is a deterministic mismatch."""

    snapshot = freeze_fitchef_source_snapshot(_two_sources())
    drifted_projection = replace(snapshot, projection=tuple(reversed(snapshot.projection)))
    drifted_fingerprint = replace(
        snapshot,
        source_snapshot_fingerprint="sha256:" + "0" * 64,
    )

    for drifted in (drifted_projection, drifted_fingerprint):
        assessment = _build_assessment(drifted)
        assert assessment.records[4].assurance_state == "source_snapshot_mismatch"
        assert assessment.records[4].reason_codes == ("source_snapshot_mismatch",)
        assert assessment.records[4].candidate_source_refs == ()


def test_result_source_projection_drift_blocks_candidate_refs() -> None:
    """The assessor binds the exact ordered result projection to the frozen snapshot."""

    snapshot = freeze_fitchef_source_snapshot(_two_sources())
    canonical_sources = tuple(build_fitchef_source_items(snapshot))
    first, second = canonical_sources
    drifted_source_sets = (
        (first,),
        (
            first,
            second,
            second.model_copy(update={"chunk_id": "chunk-gamma"}),
        ),
        tuple(reversed(canonical_sources)),
        (first.model_copy(update={"chunk_id": "changed-chunk"}), second),
        (first.model_copy(update={"file": "docs/cbt/changed.md"}), second),
        (first.model_copy(update={"preview": "Changed preview"}), second),
        (first.model_copy(update={"score": 0.9100001}), second),
    )

    for drifted_sources in drifted_source_sets:
        before = tuple(source.model_dump(mode="python") for source in drifted_sources)
        assessment = build_distortion_field_assurance_assessment(
            snapshot,
            result_sources=drifted_sources,
        )

        assert assessment.records[4].assurance_state == "source_snapshot_mismatch"
        assert assessment.records[4].reason_codes == ("source_snapshot_mismatch",)
        assert assessment.records[4].candidate_source_refs == ()
        assert assessment.source_snapshot_mismatch_count == 1
        assert assessment.support_claimed_count == 0
        assert tuple(source.model_dump(mode="python") for source in drifted_sources) == before


def test_snapshot_fingerprint_changes_on_add_remove_reorder_content_preview_and_score() -> None:
    """The ordered exact-value manifest binds every admitted occurrence projection."""

    first, second = _two_sources()
    variants = (
        (first,),
        (first, second),
        (
            replace(second, ordinal=0),
            replace(first, ordinal=1),
        ),
        (replace(first, content="Changed sanitized content."), second),
        (replace(first, preview="Changed preview"), second),
        (replace(first, score=0.9100001), second),
        (first, second, replace(second, ordinal=2, chunk_id="chunk-gamma")),
    )
    fingerprints = [
        freeze_fitchef_source_snapshot(variant).source_snapshot_fingerprint for variant in variants
    ]

    assert all(fingerprint is not None for fingerprint in fingerprints)
    assert len(set(fingerprints)) == len(fingerprints)


def test_nonfinite_score_degrades_assurance_only() -> None:
    """A nonfinite local fingerprint input leaves prompt/public source behavior intact."""

    snapshot = freeze_fitchef_source_snapshot(
        (
            _occurrence(
                0,
                chunk_id="nonfinite",
                file="docs/cbt/nonfinite.md",
                content="Sanitized retained context.",
                preview="Retained preview",
                score=math.inf,
            ),
        )
    )
    assessment = _build_assessment(snapshot)

    assert snapshot.source_snapshot_fingerprint is None
    assert "Sanitized retained context." in build_fitchef_source_prompt_context(snapshot)
    assert math.isinf(build_fitchef_source_items(snapshot)[0].score)
    assert assessment.source_snapshot_fingerprint is None
    assert assessment.assessment_unavailable_count == 6
    assert all(record.assurance_state == "assessment_unavailable" for record in assessment.records)
    assert all(
        record.reason_codes == ("snapshot_fingerprint_unavailable",)
        for record in assessment.records
    )


def test_fresh_unavailable_assessments_do_not_share_request_state() -> None:
    """Caught assessor failures receive fresh deterministic negative-only assessments."""

    first = build_distortion_field_assurance_unavailable(reason_code="assessment_unavailable")
    second = build_distortion_field_assurance_unavailable(reason_code="assessment_unavailable")

    assert first is not second
    assert first.records is not second.records
    assert first.source_snapshot_fingerprint is None
    assert first.assessment_unavailable_count == 6
    assert all(record.reason_codes == ("assessment_unavailable",) for record in first.records)


def test_two_source_snapshots_are_request_local_and_prompt_source_aligned() -> None:
    """Sequential requests keep distinct immutable snapshots and shared projections."""

    first_snapshot = freeze_fitchef_source_snapshot((_two_sources()[0],))
    second_occurrence = _occurrence(
        0,
        chunk_id="request-two",
        file="docs/cbt/request-two.md",
        content="Second request only.",
        preview="Second request preview",
        score=0.66,
    )
    second_snapshot = freeze_fitchef_source_snapshot((second_occurrence,))

    assert first_snapshot.source_snapshot_fingerprint != second_snapshot.source_snapshot_fingerprint
    assert "Second request only." not in build_fitchef_source_prompt_context(first_snapshot)
    assert build_fitchef_source_items(first_snapshot)[0].file == "docs/cbt/alpha.md"
    assert build_fitchef_source_prompt_context(second_snapshot).endswith("Second request only.")
    assert build_fitchef_source_items(second_snapshot)[0].preview == "Second request preview"

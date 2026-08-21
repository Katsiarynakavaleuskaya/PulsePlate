"""Internal negative-only claim/evidence assurance for FitChef distortion fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from app.schemas.fitchef import (
    FitChefDistortionFieldAssuranceAssessmentV1,
    FitChefDistortionFieldPath,
    FitChefFieldAssuranceReasonCode,
    FitChefFieldAssuranceRecordV1,
    FitChefFieldAssuranceState,
    FitChefSourceItem,
)
from core.evidence.fingerprints import JsonValue, fingerprint_payload

_DISTORTION_FIELD_ORDER: tuple[FitChefDistortionFieldPath, ...] = (
    "distortion_labels",
    "why_it_matches",
    "evidence_for",
    "evidence_against",
    "balanced_reframe",
    "next_small_action",
)
_REQUEST_CONTEXT_FIELDS = frozenset(_DISTORTION_FIELD_ORDER[:4])
_SNAPSHOT_SCHEMA_VERSION = "fitchef_source_snapshot.v1"
_CONTENT_SCHEMA_VERSION = "fitchef_source_content.v1"
_OCCURRENCE_REF_SCHEMA_VERSION = "fitchef_source_occurrence_ref.v1"
_UnavailableReason = Literal[
    "snapshot_fingerprint_unavailable",
    "assessment_unavailable",
]

FitChefSourceProjectionV1 = tuple[tuple[int, str, str, str, str, float], ...]


@dataclass(frozen=True, slots=True)
class FitChefSourceOccurrenceV1:
    """One admitted sanitized/redacted source occurrence in retrieval order."""

    ordinal: int
    chunk_id: str
    file: str
    content: str
    preview: str
    score: float


@dataclass(frozen=True, slots=True)
class FitChefSourceSnapshotV1:
    """Request-local immutable source snapshot plus its exact frozen projection."""

    occurrences: tuple[FitChefSourceOccurrenceV1, ...]
    projection: FitChefSourceProjectionV1
    source_snapshot_fingerprint: str | None


def _copy_occurrence(occurrence: FitChefSourceOccurrenceV1) -> FitChefSourceOccurrenceV1:
    """Copy one occurrence into built-in immutable scalar values."""

    return FitChefSourceOccurrenceV1(
        ordinal=int(occurrence.ordinal),
        chunk_id=str(occurrence.chunk_id),
        file=str(occurrence.file),
        content=str(occurrence.content),
        preview=str(occurrence.preview),
        score=float(occurrence.score),
    )


def _project_occurrences(
    occurrences: tuple[FitChefSourceOccurrenceV1, ...],
) -> FitChefSourceProjectionV1:
    """Return the exact ordered scalar projection used for drift comparison."""

    return tuple(
        (
            occurrence.ordinal,
            occurrence.chunk_id,
            occurrence.file,
            occurrence.content,
            occurrence.preview,
            occurrence.score,
        )
        for occurrence in occurrences
    )


def _snapshot_fingerprint(
    occurrences: tuple[FitChefSourceOccurrenceV1, ...],
) -> str:
    """Fingerprint the exact ordered manifest without exposing full content."""

    manifest: list[JsonValue] = []
    for occurrence in occurrences:
        content_payload: JsonValue = {
            "schema_version": _CONTENT_SCHEMA_VERSION,
            "content": occurrence.content,
        }
        content_fingerprint = fingerprint_payload(content_payload)
        manifest.append(
            {
                "ordinal": occurrence.ordinal,
                "chunk_id": occurrence.chunk_id,
                "file": occurrence.file,
                "content_fingerprint": content_fingerprint,
                "preview": occurrence.preview,
                "score": occurrence.score,
            }
        )
    snapshot_payload: JsonValue = {
        "schema_version": _SNAPSHOT_SCHEMA_VERSION,
        "occurrences": manifest,
    }
    return cast(str, fingerprint_payload(snapshot_payload))


def _try_snapshot_fingerprint(
    occurrences: tuple[FitChefSourceOccurrenceV1, ...],
) -> str | None:
    """Return a snapshot fingerprint or a local unavailable marker."""

    try:
        return _snapshot_fingerprint(occurrences)
    except Exception:
        return None


def freeze_fitchef_source_snapshot(
    occurrences: tuple[FitChefSourceOccurrenceV1, ...],
) -> FitChefSourceSnapshotV1:
    """Freeze ordered admitted occurrences without deduplication or sorting."""

    frozen_occurrences = tuple(_copy_occurrence(occurrence) for occurrence in occurrences)
    if any(
        occurrence.ordinal != expected_ordinal
        for expected_ordinal, occurrence in enumerate(frozen_occurrences)
    ):
        raise ValueError("source occurrence ordinals must be contiguous and zero-based")
    projection = _project_occurrences(frozen_occurrences)
    return FitChefSourceSnapshotV1(
        occurrences=frozen_occurrences,
        projection=projection,
        source_snapshot_fingerprint=_try_snapshot_fingerprint(frozen_occurrences),
    )


def build_fitchef_source_prompt_context(snapshot: FitChefSourceSnapshotV1) -> str:
    """Build prompt context from the exact frozen occurrence tuple."""

    return "\n\n".join(
        f"[{occurrence.file}]\n{occurrence.content}" for occurrence in snapshot.occurrences
    )


def build_fitchef_source_items(snapshot: FitChefSourceSnapshotV1) -> list[FitChefSourceItem]:
    """Build the existing internal public-source projection from the same tuple."""

    return [
        FitChefSourceItem(
            chunk_id=occurrence.chunk_id,
            file=occurrence.file,
            preview=occurrence.preview,
            score=occurrence.score,
        )
        for occurrence in snapshot.occurrences
    ]


def _field_metadata(
    field_path: FitChefDistortionFieldPath,
) -> tuple[Literal["inference", "recommendation"], Literal["heuristic", "none"]]:
    if field_path in _REQUEST_CONTEXT_FIELDS:
        return "inference", "heuristic"
    return "recommendation", "none"


def _record(
    *,
    field_path: FitChefDistortionFieldPath,
    assurance_state: FitChefFieldAssuranceState,
    reason_code: FitChefFieldAssuranceReasonCode,
    candidate_source_refs: tuple[str, ...] = (),
) -> FitChefFieldAssuranceRecordV1:
    claim_type, evidence_mode = _field_metadata(field_path)
    return FitChefFieldAssuranceRecordV1(
        field_path=field_path,
        claim_type=claim_type,
        evidence_mode=evidence_mode,
        adjudicated_support_status=None,
        assurance_state=assurance_state,
        candidate_source_refs=candidate_source_refs,
        conflict_adjudicated=False,
        reason_codes=(reason_code,),
    )


def _assessment(
    *,
    source_snapshot_fingerprint: str | None,
    records: tuple[FitChefFieldAssuranceRecordV1, ...],
) -> FitChefDistortionFieldAssuranceAssessmentV1:
    return FitChefDistortionFieldAssuranceAssessmentV1(
        source_snapshot_fingerprint=source_snapshot_fingerprint,
        records=records,
        assessed_field_count=6,
        request_context_only_count=sum(
            record.assurance_state == "request_context_only" for record in records
        ),
        evidence_sensitive_field_count=1,
        candidate_linked_unverified_count=sum(
            record.assurance_state == "candidate_linked_unverified" for record in records
        ),
        evidence_link_missing_count=sum(
            record.assurance_state == "evidence_link_missing" for record in records
        ),
        source_snapshot_mismatch_count=sum(
            record.assurance_state == "source_snapshot_mismatch" for record in records
        ),
        assessment_unavailable_count=sum(
            record.assurance_state == "assessment_unavailable" for record in records
        ),
        support_claimed_count=0,
        public_response_authority=False,
        provider_retry_authority=False,
        cache_admission_authority=False,
        knowledge_promotion_authority=False,
        plan_mutation_authority=False,
    )


def build_distortion_field_assurance_unavailable(
    *,
    reason_code: _UnavailableReason,
) -> FitChefDistortionFieldAssuranceAssessmentV1:
    """Return a fresh deterministic six-record unavailable assessment."""

    records = tuple(
        _record(
            field_path=field_path,
            assurance_state="assessment_unavailable",
            reason_code=reason_code,
        )
        for field_path in _DISTORTION_FIELD_ORDER
    )
    return _assessment(source_snapshot_fingerprint=None, records=records)


def _ordinary_records(
    *,
    balanced_state: FitChefFieldAssuranceState,
    balanced_reason: FitChefFieldAssuranceReasonCode,
    candidate_source_refs: tuple[str, ...] = (),
) -> tuple[FitChefFieldAssuranceRecordV1, ...]:
    return (
        *(
            _record(
                field_path=field_path,
                assurance_state="request_context_only",
                reason_code="request_context_not_source_evidence",
            )
            for field_path in _DISTORTION_FIELD_ORDER[:4]
        ),
        _record(
            field_path="balanced_reframe",
            assurance_state=balanced_state,
            reason_code=balanced_reason,
            candidate_source_refs=candidate_source_refs,
        ),
        _record(
            field_path="next_small_action",
            assurance_state="not_evidence_bearing",
            reason_code="not_evidence_bearing",
        ),
    )


def _occurrence_refs(
    snapshot: FitChefSourceSnapshotV1,
    source_snapshot_fingerprint: str,
) -> tuple[str, ...]:
    refs: list[str] = []
    for occurrence in snapshot.occurrences:
        payload: JsonValue = {
            "schema_version": _OCCURRENCE_REF_SCHEMA_VERSION,
            "source_snapshot_fingerprint": source_snapshot_fingerprint,
            "ordinal": occurrence.ordinal,
            "chunk_id": occurrence.chunk_id,
        }
        refs.append(fingerprint_payload(payload))
    return tuple(refs)


def build_distortion_field_assurance_assessment(
    snapshot: FitChefSourceSnapshotV1,
) -> FitChefDistortionFieldAssuranceAssessmentV1:
    """Assess candidate linkage without making support or conflict claims."""

    source_snapshot_fingerprint = snapshot.source_snapshot_fingerprint
    if source_snapshot_fingerprint is None:
        return build_distortion_field_assurance_unavailable(
            reason_code="snapshot_fingerprint_unavailable"
        )

    current_projection = _project_occurrences(snapshot.occurrences)
    current_fingerprint = _try_snapshot_fingerprint(snapshot.occurrences)
    if current_fingerprint is None:
        return build_distortion_field_assurance_unavailable(
            reason_code="snapshot_fingerprint_unavailable"
        )
    if (
        current_projection != snapshot.projection
        or current_fingerprint != source_snapshot_fingerprint
    ):
        return _assessment(
            source_snapshot_fingerprint=source_snapshot_fingerprint,
            records=_ordinary_records(
                balanced_state="source_snapshot_mismatch",
                balanced_reason="source_snapshot_mismatch",
            ),
        )

    chunk_ids = tuple(occurrence.chunk_id for occurrence in snapshot.occurrences)
    if len(set(chunk_ids)) != len(chunk_ids):
        return _assessment(
            source_snapshot_fingerprint=source_snapshot_fingerprint,
            records=_ordinary_records(
                balanced_state="source_snapshot_mismatch",
                balanced_reason="duplicate_source_identity",
            ),
        )
    if not snapshot.occurrences:
        return _assessment(
            source_snapshot_fingerprint=source_snapshot_fingerprint,
            records=_ordinary_records(
                balanced_state="evidence_link_missing",
                balanced_reason="candidate_sources_missing",
            ),
        )

    try:
        candidate_source_refs = _occurrence_refs(snapshot, source_snapshot_fingerprint)
    except Exception:
        return build_distortion_field_assurance_unavailable(
            reason_code="snapshot_fingerprint_unavailable"
        )
    return _assessment(
        source_snapshot_fingerprint=source_snapshot_fingerprint,
        records=_ordinary_records(
            balanced_state="candidate_linked_unverified",
            balanced_reason="candidate_sources_present_unverified",
            candidate_source_refs=candidate_source_refs,
        ),
    )

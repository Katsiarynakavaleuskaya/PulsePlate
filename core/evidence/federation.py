"""Pure, finite read-only projections of canonically admitted relation snapshots."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, fields, replace
from typing import Literal, Sequence, cast

from core.evidence.assets import EvidenceAssetRef
from core.evidence.fingerprints import JsonValue, _canonical_json_bytes, fingerprint_payload
from core.evidence.relations import (
    EpistemicLinkV1,
    EvidenceRelationSnapshotV1,
    InventoryAssetV1,
    WorldRelationAssessmentV1,
    WorldRelationAssertionV1,
    _fingerprint,
    _token,
    audit_snapshot,
    parse_snapshot,
)

POLICY_VERSION = "graph-fed1-inspection-v1"
MAX_DERIVED_BYTES = 8 * 1024 * 1024
RecordNamespace = Literal[
    "evidence.asset", "evidence.link", "evidence.assertion", "evidence.assessment"
]
LookupState = Literal["claim_absent", "scope_absent", "no_epistemic_links", "present"]
_NAMESPACES = ("evidence.asset", "evidence.link", "evidence.assertion", "evidence.assessment")


@dataclass(frozen=True, slots=True)
class QualifiedEvidenceRefV1:
    namespace: RecordNamespace
    snapshot_fingerprint: str
    local_id: str

    def to_dict(self) -> dict[str, JsonValue]:
        _check_ref(self)
        return {
            "namespace": self.namespace,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "local_id": self.local_id,
        }


@dataclass(frozen=True, slots=True)
class EvidenceProjectionV1:
    snapshot: EvidenceRelationSnapshotV1
    assessments: tuple[WorldRelationAssessmentV1, ...]
    references: tuple[QualifiedEvidenceRefV1, ...]
    projection_fingerprint: str
    policy_version: str = POLICY_VERSION
    authority_granted: Literal[False] = False
    answer_change_allowed: Literal[False] = False

    def to_dict(self) -> dict[str, JsonValue]:
        admitted = _admit_projection(self)
        return {
            **_projection_material(admitted),
            "projection_fingerprint": admitted.projection_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ClaimNeighborhoodV1:
    _projection: EvidenceProjectionV1
    claim_ref: str
    context_ref: str
    time_scope: str
    lookup_state: LookupState
    assets: tuple[InventoryAssetV1, ...]
    main_links: tuple[EpistemicLinkV1, ...]
    main_assertions: tuple[WorldRelationAssertionV1, ...]
    main_assessments: tuple[WorldRelationAssessmentV1, ...]
    history_links: tuple[EpistemicLinkV1, ...]
    history_assertions: tuple[WorldRelationAssertionV1, ...]
    history_assessments: tuple[WorldRelationAssessmentV1, ...]
    result_fingerprint: str
    idempotency_key: str
    asset_type: Literal["gate_report"] = "gate_report"
    rail: Literal["advisory"] = "advisory"
    version: Literal["v1"] = "v1"
    policy_version: str = POLICY_VERSION
    upstream_binding: str = "informational_source_refs_only"
    replay_behavior: str = "read_only_deterministic_derivation"
    admission_behavior: str = "canonical_snapshot_and_audit_revalidation"
    complete_for_supplied_inventory: Literal[True] = True
    authority_granted: Literal[False] = False
    answer_change_allowed: Literal[False] = False

    def to_dict(self) -> dict[str, JsonValue]:
        admitted = _check_neighborhood(self)
        expected = _select(admitted, self.claim_ref, self.context_ref, self.time_scope)
        if self != expected:
            raise ValueError("neighborhood_binding")
        return {
            **_neighborhood_material(expected),
            "result_fingerprint": expected.result_fingerprint,
            "idempotency_key": expected.idempotency_key,
        }


def _strings(values: Sequence[object]) -> None:
    if any(type(value) is not str for value in values):
        raise ValueError("schema_value")


def _ref_tuple(value: object, *, elements: bool = True) -> None:
    if type(value) is not tuple or len(cast(tuple[object, ...], value)) > 512:
        raise ValueError("schema_value")
    if elements:
        _strings(cast(tuple[object, ...], value))


def _record_shape(record: EpistemicLinkV1 | WorldRelationAssertionV1) -> None:
    for field in fields(record):
        value: object = getattr(record, field.name)
        if field.name == "revision_of_ref" and value is None:
            continue
        if field.name in ("method_refs", "independent_review_refs", "epistemic_link_refs"):
            _ref_tuple(value)
        elif type(value) is not str:
            raise ValueError("schema_value")


def _asset_shape(item: InventoryAssetV1) -> None:
    if type(item) is not InventoryAssetV1 or type(item.asset) is not EvidenceAssetRef:
        raise ValueError("schema_value")
    _strings((item.use_kind,))
    for field in fields(item.asset):
        value: object = getattr(item.asset, field.name)
        if field.name == "upstream_ids":
            _ref_tuple(value)
        elif type(value) is not str:
            raise ValueError("schema_value")


def _source_shape(snapshot: EvidenceRelationSnapshotV1) -> None:
    """Reject canonical raw carrier bounds before encoding or ref materialization."""
    if type(snapshot) is not EvidenceRelationSnapshotV1:
        raise ValueError("schema_value")
    collections = (snapshot.assets, snapshot.links, snapshot.assertions)
    if any(type(items) is not tuple for items in collections):
        raise ValueError("schema_value")
    size = sum(len(items) for items in collections)
    if not size or size > 10_000:
        raise ValueError("snapshot_size")
    for item in snapshot.assets:
        if type(item) is not InventoryAssetV1 or type(item.asset) is not EvidenceAssetRef:
            raise ValueError("schema_value")
        _ref_tuple(item.asset.upstream_ids, elements=False)
    for link in snapshot.links:
        if type(link) is not EpistemicLinkV1:
            raise ValueError("schema_value")
    for assertion in snapshot.assertions:
        if type(assertion) is not WorldRelationAssertionV1:
            raise ValueError("schema_value")
        refs = (
            assertion.method_refs,
            assertion.independent_review_refs,
            assertion.epistemic_link_refs,
        )
        for values in refs:
            _ref_tuple(values, elements=False)
        if sum(len(values) for values in refs) > 512:
            raise ValueError("reference_limit")
    _fingerprint(snapshot.input_fingerprint)
    for item in snapshot.assets:
        _asset_shape(item)
    for link in snapshot.links:
        _record_shape(link)
    for assertion in snapshot.assertions:
        _record_shape(assertion)


def _assessment_shape(assessment: WorldRelationAssessmentV1) -> None:
    if type(assessment) is not WorldRelationAssessmentV1:
        raise ValueError("assessment_binding")
    _strings((assessment.assertion_id, assessment.relation, assessment.outcome))
    for values in (
        assessment.reason_codes,
        assessment.missing_requirements,
        assessment.unresolved_link_refs,
    ):
        _ref_tuple(values)
    if (
        type(assessment.causal_structural_pass) is not bool
        or assessment.authority_granted is not False
        or assessment.answer_change_allowed is not False
    ):
        raise ValueError("assessment_binding")


def _check_ref(ref: QualifiedEvidenceRefV1) -> None:
    if type(ref) is not QualifiedEvidenceRefV1:
        raise ValueError("projection_binding")
    _strings((ref.namespace, ref.snapshot_fingerprint, ref.local_id))
    if ref.namespace not in _NAMESPACES:
        raise ValueError("projection_binding")
    _fingerprint(ref.snapshot_fingerprint)
    _token(ref.local_id)


def _record_row(
    record: EpistemicLinkV1 | WorldRelationAssertionV1,
) -> dict[str, JsonValue]:
    row: dict[str, JsonValue] = {
        "kind": "epistemic_link" if type(record) is EpistemicLinkV1 else "world_relation"
    }
    for field in fields(record):
        value: object = getattr(record, field.name)
        row[field.name] = (
            list(cast(tuple[str, ...], value)) if type(value) is tuple else cast(str | None, value)
        )
    return row


def _asset_row(item: InventoryAssetV1) -> dict[str, JsonValue]:
    asset: dict[str, JsonValue] = {}
    for field in fields(item.asset):
        value: object = getattr(item.asset, field.name)
        asset[field.name] = (
            list(cast(tuple[str, ...], value)) if field.name == "upstream_ids" else cast(str, value)
        )
    return {"kind": "asset", "use_kind": item.use_kind, "asset": asset}


def _source_rows(snapshot: EvidenceRelationSnapshotV1) -> list[object]:
    return [
        *(_asset_row(item) for item in snapshot.assets),
        *(_record_row(item) for item in snapshot.links),
        *(_record_row(item) for item in snapshot.assertions),
    ]


def _admit_snapshot(snapshot: EvidenceRelationSnapshotV1) -> EvidenceRelationSnapshotV1:
    _source_shape(snapshot)
    canonical = parse_snapshot(_source_rows(snapshot))
    if snapshot.input_fingerprint != canonical.input_fingerprint:
        raise ValueError("snapshot_binding")
    return canonical


def _ref(namespace: RecordNamespace, fingerprint: str, local_id: str) -> QualifiedEvidenceRefV1:
    return QualifiedEvidenceRefV1(namespace, fingerprint, local_id)


def _check_derived_budget(
    snapshot: EvidenceRelationSnapshotV1,
    assessments: tuple[WorldRelationAssessmentV1, ...],
) -> None:
    """Bound both hash/report representations before allocating qualified records."""
    # Fixed envelopes/query/identity material fit 2 KiB. Wrapper keys/syntax fit
    # 192 bytes per record; raw rows are encoded one bounded (<=512 refs) item
    # at a time by the canonical encoder. No whole derived material is built.
    material_bytes = 2048
    projection_refs = 0
    informational_refs = 0

    def reference_bytes(namespace: RecordNamespace, identifier: str) -> int:
        # All three values are canonical ASCII tokens. The extra byte covers
        # an array comma, so this never understates the actual reference size.
        return (
            len('{"local_id":"","namespace":"","snapshot_fingerprint":""}')
            + len(namespace)
            + len(identifier)
            + len(snapshot.input_fingerprint)
            + 1
        )

    def check() -> None:
        # Projection inventory and neighborhood informational refs are separate
        # representations; use their maximum, not a source-row cardinality cap.
        if material_bytes + max(projection_refs, informational_refs) > MAX_DERIVED_BYTES:
            raise ValueError("report_limit")

    check()
    for item in snapshot.assets:
        own_ref = reference_bytes("evidence.asset", item.asset.asset_id)
        material_bytes += 192 + len(_canonical_json_bytes(_asset_row(item))) + own_ref
        material_bytes += sum(
            reference_bytes("evidence.asset", identifier) for identifier in item.asset.upstream_ids
        )
        projection_refs += own_ref
        informational_refs += (
            64
            + own_ref
            + len(_canonical_json_bytes(item.asset.rail))
            + len(_canonical_json_bytes(item.asset.fingerprint))
        )
        check()
    for records, namespace in (
        (snapshot.links, "evidence.link"),
        (snapshot.assertions, "evidence.assertion"),
    ):
        for source_record in records:
            record = source_record
            kind = cast(RecordNamespace, namespace)
            own_ref = reference_bytes(kind, record.id)
            material_bytes += 192 + len(_canonical_json_bytes(_record_row(record))) + own_ref
            material_bytes += reference_bytes("evidence.asset", record.context_ref)
            projection_refs += own_ref
            if type(record) is EpistemicLinkV1:
                material_bytes += reference_bytes("evidence.asset", record.evidence_ref)
            else:
                assertion = cast(WorldRelationAssertionV1, record)
                material_bytes += sum(
                    reference_bytes("evidence.asset", identifier)
                    for identifier in (*assertion.method_refs, *assertion.independent_review_refs)
                )
                material_bytes += sum(
                    reference_bytes("evidence.link", identifier)
                    for identifier in assertion.epistemic_link_refs
                )
            if record.revision_of_ref is not None:
                material_bytes += reference_bytes(kind, record.revision_of_ref)
            check()
    for assessment in assessments:
        own_ref = reference_bytes("evidence.assessment", assessment.assertion_id)
        material_bytes += (
            192
            + len(_canonical_json_bytes(cast(JsonValue, assessment.to_dict())))
            + own_ref
            + reference_bytes("evidence.assertion", assessment.assertion_id)
        )
        material_bytes += sum(
            reference_bytes("evidence.link", identifier)
            for identifier in assessment.unresolved_link_refs
        )
        projection_refs += own_ref
        check()


def _project(snapshot: EvidenceRelationSnapshotV1) -> EvidenceProjectionV1:
    report = audit_snapshot(snapshot)
    _check_derived_budget(snapshot, report.assessments)
    fingerprint = snapshot.input_fingerprint
    refs = (
        *(_ref("evidence.asset", fingerprint, item.asset.asset_id) for item in snapshot.assets),
        *(_ref("evidence.link", fingerprint, item.id) for item in snapshot.links),
        *(_ref("evidence.assertion", fingerprint, item.id) for item in snapshot.assertions),
        *(
            _ref("evidence.assessment", fingerprint, item.assertion_id)
            for item in report.assessments
        ),
    )
    projection = EvidenceProjectionV1(snapshot, report.assessments, refs, "")
    return replace(
        projection, projection_fingerprint=fingerprint_payload(_projection_material(projection))
    )


def build_evidence_projection(snapshot: EvidenceRelationSnapshotV1) -> EvidenceProjectionV1:
    """Re-admit and audit the entire source before creating an immutable projection."""
    return _project(_admit_snapshot(snapshot))


def _admit_projection(projection: EvidenceProjectionV1) -> EvidenceProjectionV1:
    if type(projection) is not EvidenceProjectionV1:
        raise ValueError("projection_binding")
    canonical = _admit_snapshot(projection.snapshot)
    if (
        type(projection.assessments) is not tuple
        or len(projection.assessments) != len(canonical.assertions)
        or type(projection.references) is not tuple
        or len(projection.references)
        != (len(canonical.assets) + len(canonical.links) + 2 * len(canonical.assertions))
        or projection.authority_granted is not False
        or projection.answer_change_allowed is not False
    ):
        raise ValueError("projection_binding")
    _strings((projection.policy_version, projection.projection_fingerprint))
    for assessment in projection.assessments:
        _assessment_shape(assessment)
    for reference in projection.references:
        _check_ref(reference)
    expected = _project(canonical)
    if projection != expected:
        raise ValueError("projection_binding")
    return expected


def _qualified_record(
    record: (
        InventoryAssetV1 | EpistemicLinkV1 | WorldRelationAssertionV1 | WorldRelationAssessmentV1
    ),
    fingerprint: str,
) -> dict[str, JsonValue]:
    def qualified(namespace: RecordNamespace, identifier: str) -> dict[str, JsonValue]:
        return _ref(namespace, fingerprint, identifier).to_dict()

    if type(record) is InventoryAssetV1:
        asset = record
        return {
            "ref": qualified("evidence.asset", asset.asset.asset_id),
            "record": _asset_row(asset),
            "upstream_refs": [qualified("evidence.asset", ref) for ref in asset.asset.upstream_ids],
        }
    if type(record) is WorldRelationAssessmentV1:
        assessment = record
        return {
            "ref": qualified("evidence.assessment", assessment.assertion_id),
            "record": cast(JsonValue, assessment.to_dict()),
            "assertion_ref": qualified("evidence.assertion", assessment.assertion_id),
            "unresolved_link_refs": [
                qualified("evidence.link", ref) for ref in assessment.unresolved_link_refs
            ],
        }
    original = cast(EpistemicLinkV1 | WorldRelationAssertionV1, record)
    namespace: RecordNamespace = (
        "evidence.link" if type(original) is EpistemicLinkV1 else "evidence.assertion"
    )
    result: dict[str, JsonValue] = {
        "ref": qualified(namespace, original.id),
        "record": _record_row(original),
        "context_ref": qualified("evidence.asset", original.context_ref),
        "revision_of_ref": (
            qualified(namespace, original.revision_of_ref)
            if original.revision_of_ref is not None
            else None
        ),
    }
    if type(original) is EpistemicLinkV1:
        result["evidence_ref"] = qualified("evidence.asset", original.evidence_ref)
    else:
        assertion = cast(WorldRelationAssertionV1, original)
        result["method_refs"] = [qualified("evidence.asset", ref) for ref in assertion.method_refs]
        result["independent_review_refs"] = [
            qualified("evidence.asset", ref) for ref in assertion.independent_review_refs
        ]
        result["epistemic_link_refs"] = [
            qualified("evidence.link", ref) for ref in assertion.epistemic_link_refs
        ]
    return result


def _projection_material(projection: EvidenceProjectionV1) -> dict[str, JsonValue]:
    source = projection.snapshot
    fingerprint = source.input_fingerprint
    return {
        "policy_version": projection.policy_version,
        "input_fingerprint": fingerprint,
        "assets": [_qualified_record(item, fingerprint) for item in source.assets],
        "links": [_qualified_record(item, fingerprint) for item in source.links],
        "assertions": [_qualified_record(item, fingerprint) for item in source.assertions],
        "assessments": [_qualified_record(item, fingerprint) for item in projection.assessments],
        "references": [ref.to_dict() for ref in projection.references],
        "authority_granted": projection.authority_granted,
        "answer_change_allowed": projection.answer_change_allowed,
    }


def _component(
    records: Sequence[EpistemicLinkV1 | WorldRelationAssertionV1],
    seeds: set[str],
) -> set[str]:
    neighbors: dict[str, list[str]] = {item.id: [] for item in records}
    for item in records:
        if item.revision_of_ref is not None:
            neighbors[item.id].append(item.revision_of_ref)
            neighbors[item.revision_of_ref].append(item.id)
    selected: set[str] = set()
    pending = deque(sorted(seeds))
    while pending:
        identifier = pending.popleft()
        if identifier not in selected:
            selected.add(identifier)
            pending.extend(neighbors[identifier])
    return selected


def _select(
    projection: EvidenceProjectionV1,
    claim: str,
    context: str,
    period: str,
) -> ClaimNeighborhoodV1:
    _token(claim)
    _token(context)
    _token(period)
    source = projection.snapshot
    query = (claim, context, period)
    main_links = tuple(
        item
        for item in source.links
        if (item.claim_ref, item.context_ref, item.time_scope) == query
    )
    main_assertions = tuple(
        item
        for item in source.assertions
        if (item.claim_ref, item.context_ref, item.time_scope) == query
    )
    known = any(item.claim_ref == claim for item in source.links) or any(
        item.claim_ref == claim for item in source.assertions
    )
    state: LookupState = (
        "claim_absent"
        if not known
        else (
            "scope_absent"
            if not main_links and not main_assertions
            else "no_epistemic_links" if not main_links else "present"
        )
    )
    main_link_ids = {item.id for item in main_links}
    main_assertion_ids = {item.id for item in main_assertions}
    assertion_ids = _component(source.assertions, main_assertion_ids)
    assertions = tuple(item for item in source.assertions if item.id in assertion_ids)
    assessments = tuple(
        item for item in projection.assessments if item.assertion_id in assertion_ids
    )
    link_seeds = main_link_ids.union(
        ref for item in assertions for ref in item.epistemic_link_refs
    ).union(ref for item in assessments for ref in item.unresolved_link_refs)
    link_ids = _component(source.links, link_seeds)
    links = tuple(item for item in source.links if item.id in link_ids)
    asset_ids = {ref for item in links for ref in (item.evidence_ref, item.context_ref)}
    asset_ids.update(
        ref
        for item in assertions
        for ref in (item.context_ref, *item.method_refs, *item.independent_review_refs)
    )
    by_asset = {item.asset.asset_id: item for item in source.assets}
    pending = deque(sorted(asset_ids))
    while pending:
        for ref in by_asset[pending.popleft()].asset.upstream_ids:
            if ref not in asset_ids:
                asset_ids.add(ref)
                pending.append(ref)
    result = ClaimNeighborhoodV1(
        projection,
        claim,
        context,
        period,
        state,
        tuple(item for item in source.assets if item.asset.asset_id in asset_ids),
        main_links,
        main_assertions,
        tuple(item for item in assessments if item.assertion_id in main_assertion_ids),
        tuple(item for item in links if item.id not in main_link_ids),
        tuple(item for item in assertions if item.id not in main_assertion_ids),
        tuple(item for item in assessments if item.assertion_id not in main_assertion_ids),
        "",
        "",
    )
    result_fingerprint = fingerprint_payload(_neighborhood_material(result))
    return replace(
        result,
        result_fingerprint=result_fingerprint,
        idempotency_key=fingerprint_payload(
            {
                "purpose": "graph-fed1-read-only-replay",
                "policy_version": result.policy_version,
                "input_fingerprint": source.input_fingerprint,
                "query": {"claim_ref": claim, "context_ref": context, "time_scope": period},
                "result_fingerprint": result_fingerprint,
            }
        ),
    )


def select_claim_neighborhood(
    projection: EvidenceProjectionV1,
    *,
    claim_ref: str,
    context_ref: str,
    time_scope: str,
) -> ClaimNeighborhoodV1:
    """Select exact seeds and their explicit finite revision/dependency closure."""
    return _select(_admit_projection(projection), claim_ref, context_ref, time_scope)


def _check_neighborhood(result: ClaimNeighborhoodV1) -> EvidenceProjectionV1:
    if type(result) is not ClaimNeighborhoodV1:
        raise ValueError("neighborhood_binding")
    if (
        result.complete_for_supplied_inventory is not True
        or result.authority_granted is not False
        or result.answer_change_allowed is not False
    ):
        raise ValueError("neighborhood_binding")
    _strings(
        (
            result.claim_ref,
            result.context_ref,
            result.time_scope,
            result.lookup_state,
            result.result_fingerprint,
            result.idempotency_key,
            result.asset_type,
            result.rail,
            result.version,
            result.policy_version,
            result.upstream_binding,
            result.replay_behavior,
            result.admission_behavior,
        )
    )
    admitted = _admit_projection(result._projection)
    source = admitted.snapshot
    for items, expected_type, limit in (
        (result.assets, InventoryAssetV1, len(source.assets)),
        (result.main_links, EpistemicLinkV1, len(source.links)),
        (result.history_links, EpistemicLinkV1, len(source.links)),
        (result.main_assertions, WorldRelationAssertionV1, len(source.assertions)),
        (result.history_assertions, WorldRelationAssertionV1, len(source.assertions)),
        (result.main_assessments, WorldRelationAssessmentV1, len(source.assertions)),
        (result.history_assessments, WorldRelationAssessmentV1, len(source.assertions)),
    ):
        if type(items) is not tuple or len(items) > limit:
            raise ValueError("neighborhood_binding")
        for item in items:
            if type(item) is not expected_type:
                raise ValueError("neighborhood_binding")
            if type(item) is InventoryAssetV1:
                _asset_shape(item)
            elif type(item) is WorldRelationAssessmentV1:
                _assessment_shape(item)
            else:
                _record_shape(cast(EpistemicLinkV1 | WorldRelationAssertionV1, item))
    return admitted


def _neighborhood_material(result: ClaimNeighborhoodV1) -> dict[str, JsonValue]:
    fingerprint = result._projection.snapshot.input_fingerprint

    def section(
        links: tuple[EpistemicLinkV1, ...],
        assertions: tuple[WorldRelationAssertionV1, ...],
        assessments: tuple[WorldRelationAssessmentV1, ...],
    ) -> dict[str, JsonValue]:
        return {
            "links": [_qualified_record(item, fingerprint) for item in links],
            "assertions": [_qualified_record(item, fingerprint) for item in assertions],
            "assessments": [_qualified_record(item, fingerprint) for item in assessments],
        }

    return {
        "asset_type": result.asset_type,
        "rail": result.rail,
        "version": result.version,
        "policy_version": result.policy_version,
        "input_fingerprint": fingerprint,
        "query": {
            "claim_ref": result.claim_ref,
            "context_ref": result.context_ref,
            "time_scope": result.time_scope,
        },
        "lookup_state": result.lookup_state,
        "assets": [_qualified_record(item, fingerprint) for item in result.assets],
        "main": section(result.main_links, result.main_assertions, result.main_assessments),
        "history": section(
            result.history_links, result.history_assertions, result.history_assessments
        ),
        "upstream_refs": [
            {
                "ref": _ref("evidence.asset", fingerprint, item.asset.asset_id).to_dict(),
                "rail": item.asset.rail,
                "fingerprint": item.asset.fingerprint,
            }
            for item in result.assets
        ],
        "upstream_binding": result.upstream_binding,
        "replay_behavior": result.replay_behavior,
        "admission_behavior": result.admission_behavior,
        "complete_for_supplied_inventory": result.complete_for_supplied_inventory,
        "authority_granted": result.authority_granted,
        "answer_change_allowed": result.answer_change_allowed,
    }

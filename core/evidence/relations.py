"""Finite, offline structural audit of typed evidence and world relations.

Every reference is resolved against one supplied snapshot. Structural satisfaction
does not authenticate attribution, reviewer independence, or scientific causality.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Literal, Sequence, cast

from core.evidence.assets import AssetType, EvidenceAssetRef, Rail
from core.evidence.fingerprints import (
    JsonValue,
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from core.evidence.policies import ALLOWED_ASSET_TYPES, ALLOWED_RAILS, validate_non_empty_token

EpistemicRelation = Literal[
    "supported_by", "contradicted_by", "derived_from", "replicated_by", "invalidated_by"
]
WorldRelation = Literal["observed_after", "associated_with", "contributed_to", "caused_by"]
EpistemicStatus = Literal["not_claimed", "candidate", "adjudicated"]
UseKind = Literal["evidence", "method", "independent_review", "context"]
_EPISTEMIC = frozenset(
    ("supported_by", "contradicted_by", "derived_from", "replicated_by", "invalidated_by")
)
_WORLD = frozenset(("observed_after", "associated_with", "contributed_to", "caused_by"))
_STATUS = frozenset(("not_claimed", "candidate", "adjudicated"))
_USES = frozenset(("evidence", "method", "independent_review", "context"))
_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_FINGERPRINT = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ASSET_FIELDS = frozenset(
    (
        "asset_id",
        "asset_type",
        "version",
        "rail",
        "upstream_ids",
        "idempotency_key",
        "policy_version",
        "fingerprint",
    )
)
_LINK_FIELDS = frozenset(
    (
        "kind",
        "id",
        "claim_ref",
        "evidence_ref",
        "relation",
        "context_ref",
        "time_scope",
        "attribution",
        "produced_at",
        "source_fingerprint",
        "record_fingerprint",
        "revision_of_ref",
    )
)
_WORLD_FIELDS = frozenset(
    (
        "kind",
        "id",
        "subject_ref",
        "object_ref",
        "claim_ref",
        "relation",
        "epistemic_status",
        "context_ref",
        "time_scope",
        "attribution",
        "produced_at",
        "source_fingerprint",
        "record_fingerprint",
        "method_refs",
        "independent_review_refs",
        "epistemic_link_refs",
        "revision_of_ref",
    )
)
_ADVERSE = frozenset(("contradicted_by", "invalidated_by"))
POLICY_VERSION = "noos1a-structural-v1"
MAX_REPORT_LINK_REFS = 50_000


def _fields(value: object, expected: frozenset[str]) -> dict[str, object]:
    if (
        type(value) is not dict
        or set(value) != expected
        or any(type(key) is not str for key in value)
    ):
        raise ValueError("schema_fields")
    return cast(dict[str, object], value)


def _token(value: object) -> str:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise ValueError("schema_value")
    return value


def _fingerprint(value: object) -> str:
    if type(value) is not str or _FINGERPRINT.fullmatch(value) is None:
        raise ValueError("fingerprint_format")
    return value


def _canonical_asset_token(name: str, value: object) -> str:
    """Apply the existing asset-token contract after exact raw-type admission."""
    admitted = _token(value)
    try:
        canonical = validate_non_empty_token(name, admitted)
    except ValueError as exc:
        raise ValueError("schema_value") from exc
    if canonical != admitted:
        raise ValueError("schema_value")
    return admitted


def _choice(value: object, choices: frozenset[str]) -> str:
    if type(value) is not str or value not in choices:
        raise ValueError("schema_value")
    return value


def _refs(value: object) -> tuple[str, ...]:
    if type(value) is not list or len(value) > 512:
        raise ValueError("schema_value")
    refs = tuple(_token(item) for item in value)
    if len(set(refs)) != len(refs):
        raise ValueError("duplicate_reference")
    return refs


def _time(value: object) -> str:
    if type(value) is not str or len(value) > 64:
        raise ValueError("time_format")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("time_format") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("time_format")
    return value


def _record_fingerprint(row: dict[str, object]) -> str:
    value = _fingerprint(row["record_fingerprint"])
    material = {key: item for key, item in row.items() if key != "record_fingerprint"}
    if fingerprint_payload(cast(JsonValue, material)) != value:
        raise ValueError("fingerprint_mismatch")
    return value


@dataclass(frozen=True)
class InventoryAssetV1:
    use_kind: UseKind
    asset: EvidenceAssetRef


@dataclass(frozen=True)
class EpistemicLinkV1:
    id: str
    claim_ref: str
    evidence_ref: str
    relation: EpistemicRelation
    context_ref: str
    time_scope: str
    attribution: str
    produced_at: str
    source_fingerprint: str
    record_fingerprint: str
    revision_of_ref: str | None


@dataclass(frozen=True)
class WorldRelationAssertionV1:
    id: str
    subject_ref: str
    object_ref: str
    claim_ref: str
    relation: WorldRelation
    epistemic_status: EpistemicStatus
    context_ref: str
    time_scope: str
    attribution: str
    produced_at: str
    source_fingerprint: str
    record_fingerprint: str
    method_refs: tuple[str, ...]
    independent_review_refs: tuple[str, ...]
    epistemic_link_refs: tuple[str, ...]
    revision_of_ref: str | None


@dataclass(frozen=True)
class EvidenceRelationSnapshotV1:
    assets: tuple[InventoryAssetV1, ...]
    links: tuple[EpistemicLinkV1, ...]
    assertions: tuple[WorldRelationAssertionV1, ...]
    input_fingerprint: str


@dataclass(frozen=True)
class WorldRelationAssessmentV1:
    assertion_id: str
    relation: WorldRelation
    outcome: str
    causal_structural_pass: bool
    reason_codes: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    unresolved_link_refs: tuple[str, ...]
    authority_granted: Literal[False] = False
    answer_change_allowed: Literal[False] = False

    def to_dict(self) -> dict[str, object]:
        return {
            "assertion_id": self.assertion_id,
            "relation": self.relation,
            "outcome": self.outcome,
            "causal_structural_pass": self.causal_structural_pass,
            "reason_codes": list(self.reason_codes),
            "missing_requirements": list(self.missing_requirements),
            "unresolved_link_refs": list(self.unresolved_link_refs),
            "authority_granted": False,
            "answer_change_allowed": False,
        }


@dataclass(frozen=True)
class EvidenceRelationReportV1:
    input_fingerprint: str
    assessments: tuple[WorldRelationAssessmentV1, ...]
    counts: tuple[tuple[str, int], ...]
    report_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": POLICY_VERSION,
            "input_fingerprint": self.input_fingerprint,
            "assessments": [assessment.to_dict() for assessment in self.assessments],
            "counts": dict(self.counts),
            "report_fingerprint": self.report_fingerprint,
            "authority_granted": False,
            "answer_change_allowed": False,
        }


def _asset(row: dict[str, object]) -> InventoryAssetV1:
    _fields(row, frozenset(("kind", "use_kind", "asset")))
    use = cast(UseKind, _choice(row["use_kind"], _USES))
    raw = _fields(row["asset"], _ASSET_FIELDS)
    asset_type = cast(AssetType, _choice(raw["asset_type"], frozenset(ALLOWED_ASSET_TYPES)))
    rail = cast(Rail, _choice(raw["rail"], frozenset(ALLOWED_RAILS)))
    upstream = _refs(raw["upstream_ids"])
    if upstream != tuple(sorted(upstream)):
        raise ValueError("reference_order")
    fingerprint = _fingerprint(raw["fingerprint"])
    version = _canonical_asset_token("version", raw["version"])
    policy = _canonical_asset_token("policy_version", raw["policy_version"])
    asset_id = _token(raw["asset_id"])
    idem = _token(raw["idempotency_key"])
    if asset_id in upstream:
        raise ValueError("reference_cycle")
    if asset_id != build_asset_id(
        asset_type=asset_type,
        rail=rail,
        version=version,
        policy_version=policy,
        fingerprint=fingerprint,
        upstream_ids=upstream,
    ) or idem != build_idempotency_key(
        asset_type=asset_type,
        rail=rail,
        version=version,
        policy_version=policy,
        fingerprint=fingerprint,
        upstream_ids=upstream,
    ):
        raise ValueError("asset_identity")
    ref = EvidenceAssetRef(
        asset_id=asset_id,
        asset_type=asset_type,
        version=version,
        rail=rail,
        upstream_ids=upstream,
        idempotency_key=idem,
        policy_version=policy,
        fingerprint=fingerprint,
    )
    return InventoryAssetV1(use_kind=use, asset=ref)


def _revision(value: object) -> str | None:
    return None if value is None else _token(value)


def _link(row: dict[str, object]) -> EpistemicLinkV1:
    _fields(row, _LINK_FIELDS)
    return EpistemicLinkV1(
        id=_token(row["id"]),
        claim_ref=_token(row["claim_ref"]),
        evidence_ref=_token(row["evidence_ref"]),
        relation=cast(EpistemicRelation, _choice(row["relation"], _EPISTEMIC)),
        context_ref=_token(row["context_ref"]),
        time_scope=_token(row["time_scope"]),
        attribution=_token(row["attribution"]),
        produced_at=_time(row["produced_at"]),
        source_fingerprint=_fingerprint(row["source_fingerprint"]),
        record_fingerprint=_record_fingerprint(row),
        revision_of_ref=_revision(row["revision_of_ref"]),
    )


def _world(row: dict[str, object]) -> WorldRelationAssertionV1:
    _fields(row, _WORLD_FIELDS)
    subject = _token(row["subject_ref"])
    obj = _token(row["object_ref"])
    if subject == obj:
        raise ValueError("self_relation")
    methods = _refs(row["method_refs"])
    reviews = _refs(row["independent_review_refs"])
    links = _refs(row["epistemic_link_refs"])
    if len(methods) + len(reviews) + len(links) > 512:
        raise ValueError("reference_limit")
    return WorldRelationAssertionV1(
        id=_token(row["id"]),
        subject_ref=subject,
        object_ref=obj,
        claim_ref=_token(row["claim_ref"]),
        relation=cast(WorldRelation, _choice(row["relation"], _WORLD)),
        epistemic_status=cast(EpistemicStatus, _choice(row["epistemic_status"], _STATUS)),
        context_ref=_token(row["context_ref"]),
        time_scope=_token(row["time_scope"]),
        attribution=_token(row["attribution"]),
        produced_at=_time(row["produced_at"]),
        source_fingerprint=_fingerprint(row["source_fingerprint"]),
        record_fingerprint=_record_fingerprint(row),
        method_refs=methods,
        independent_review_refs=reviews,
        epistemic_link_refs=links,
        revision_of_ref=_revision(row["revision_of_ref"]),
    )


def _check_revisions(records: Sequence[EpistemicLinkV1 | WorldRelationAssertionV1]) -> None:
    by_id = {record.id: record for record in records}
    complete: set[str] = set()
    for record in records:
        seen: set[str] = set()
        cursor: str | None = record.id
        while cursor is not None and cursor not in complete:
            if cursor in seen:
                raise ValueError("revision_cycle")
            prior = by_id.get(cursor)
            if prior is None:
                raise ValueError("revision_reference")
            seen.add(cursor)
            cursor = prior.revision_of_ref
        complete.update(seen)


def parse_snapshot(rows: Sequence[object]) -> EvidenceRelationSnapshotV1:
    """Validate one finite supplied snapshot without inferring external completeness."""
    if type(rows) not in (list, tuple) or not rows or len(rows) > 10_000:
        raise ValueError("snapshot_size")
    assets: list[InventoryAssetV1] = []
    links: list[EpistemicLinkV1] = []
    assertions: list[WorldRelationAssertionV1] = []
    seen: set[str] = set()
    canonical_rows: list[tuple[str, str, dict[str, object]]] = []
    for raw in rows:
        if type(raw) is not dict:
            raise ValueError("schema_fields")
        row = cast(dict[str, object], raw)
        kind = row.get("kind")
        if kind == "asset":
            asset_item = _asset(row)
            identifier = asset_item.asset.asset_id
            assets.append(asset_item)
        elif kind == "epistemic_link":
            link_item = _link(row)
            identifier = link_item.id
            links.append(link_item)
        elif kind == "world_relation":
            world_item = _world(row)
            identifier = world_item.id
            assertions.append(world_item)
        else:
            raise ValueError("schema_kind")
        if identifier in seen:
            raise ValueError("duplicate_id")
        seen.add(identifier)
        canonical_rows.append((str(kind), identifier, row))
    asset_by_id = {item.asset.asset_id: item for item in assets}
    link_by_id = {item.id: item for item in links}
    matching_links: dict[tuple[str, str, str], set[str]] = {}
    adverse_links: dict[tuple[str, str, str], set[str]] = {}
    for link in links:
        key = (link.claim_ref, link.context_ref, link.time_scope)
        matching_links.setdefault(key, set()).add(link.id)
        if link.relation in _ADVERSE:
            adverse_links.setdefault(key, set()).add(link.id)

    def require_asset(ref: str, use: str) -> None:
        item = asset_by_id.get(ref)
        if item is None or item.use_kind != use:
            raise ValueError("reference_type")

    for item in assets:
        for upstream in item.asset.upstream_ids:
            parent = asset_by_id.get(upstream)
            if parent is None or parent.asset.rail != item.asset.rail:
                raise ValueError("reference_type")
    for link in links:
        require_asset(link.evidence_ref, "evidence")
        require_asset(link.context_ref, "context")
    for assertion in assertions:
        require_asset(assertion.context_ref, "context")
        for ref in assertion.method_refs:
            require_asset(ref, "method")
        for ref in assertion.independent_review_refs:
            require_asset(ref, "independent_review")
        for ref in assertion.epistemic_link_refs:
            if ref not in link_by_id:
                raise ValueError("reference_type")
        key = (assertion.claim_ref, assertion.context_ref, assertion.time_scope)
        matching = matching_links.get(key, set())
        selected = set(assertion.epistemic_link_refs)
        if not selected <= matching or not adverse_links.get(key, set()) <= selected:
            raise ValueError("reference_scope")
    _check_revisions(links)
    _check_revisions(assertions)
    return EvidenceRelationSnapshotV1(
        assets=tuple(sorted(assets, key=lambda item: item.asset.asset_id)),
        links=tuple(sorted(links, key=lambda item: item.id)),
        assertions=tuple(sorted(assertions, key=lambda item: item.id)),
        input_fingerprint=fingerprint_payload(
            cast(
                JsonValue, [row for _, _, row in sorted(canonical_rows, key=lambda item: item[:2])]
            )
        ),
    )


def audit_snapshot(snapshot: EvidenceRelationSnapshotV1) -> EvidenceRelationReportV1:
    """Assess structural requirements, preserving every assertion version."""
    assessments: list[WorldRelationAssessmentV1] = []
    adverse_by_scope: dict[tuple[str, str, str], tuple[str, ...]] = {}
    grouped: dict[tuple[str, str, str], list[str]] = {}
    for link in snapshot.links:
        if link.relation in _ADVERSE:
            grouped.setdefault((link.claim_ref, link.context_ref, link.time_scope), []).append(
                link.id
            )
    for key, identifiers in grouped.items():
        adverse_by_scope[key] = tuple(sorted(identifiers))
    emitted_link_refs = 0
    for assertion in snapshot.assertions:
        adverse = adverse_by_scope.get(
            (assertion.claim_ref, assertion.context_ref, assertion.time_scope), ()
        )
        emitted_link_refs += len(adverse)
        if emitted_link_refs > MAX_REPORT_LINK_REFS:
            raise ValueError("report_limit")
        missing: list[str] = []
        reasons: list[str] = []
        if assertion.relation == "observed_after":
            outcome = "temporal_only"
            if assertion.epistemic_status != "not_claimed":
                reasons.append("temporal_status_mismatch")
                outcome = "structural_requirements_not_satisfied"
        elif assertion.relation == "associated_with":
            if not assertion.method_refs:
                missing.append("method_ref")
            outcome = (
                "association_qualified" if not missing else "structural_requirements_not_satisfied"
            )
        elif assertion.relation == "contributed_to":
            if not assertion.method_refs:
                missing.append("method_ref")
            if assertion.epistemic_status not in ("candidate", "adjudicated"):
                missing.append("candidate_or_adjudicated")
            outcome = (
                "contribution_qualified" if not missing else "structural_requirements_not_satisfied"
            )
        else:
            if assertion.epistemic_status != "adjudicated":
                missing.append("adjudicated")
            if not assertion.method_refs:
                missing.append("method_ref")
            if not assertion.independent_review_refs:
                missing.append("independent_review_ref")
            outcome = (
                "structural_requirements_satisfied_for_supplied_scope"
                if not missing and not adverse
                else "structural_requirements_not_satisfied"
            )
        if missing:
            reasons.append("missing_requirement")
        if adverse:
            reasons.append("unresolved_contradiction")
        assessments.append(
            WorldRelationAssessmentV1(
                assertion_id=assertion.id,
                relation=assertion.relation,
                outcome=outcome,
                causal_structural_pass=(
                    assertion.relation == "caused_by" and not missing and not adverse
                ),
                reason_codes=tuple(reasons),
                missing_requirements=tuple(missing),
                unresolved_link_refs=adverse,
            )
        )
    counts = (
        ("assets", len(snapshot.assets)),
        ("epistemic_links", len(snapshot.links)),
        ("world_assertions", len(snapshot.assertions)),
        ("causal_structural_pass", sum(item.causal_structural_pass for item in assessments)),
        (
            "negative_assessments",
            sum(item.outcome == "structural_requirements_not_satisfied" for item in assessments),
        ),
    )
    content: dict[str, object] = {
        "schema_version": POLICY_VERSION,
        "input_fingerprint": snapshot.input_fingerprint,
        "assessments": [item.to_dict() for item in assessments],
        "counts": dict(counts),
        "authority_granted": False,
        "answer_change_allowed": False,
    }
    return EvidenceRelationReportV1(
        snapshot.input_fingerprint,
        tuple(assessments),
        counts,
        fingerprint_payload(cast(JsonValue, content)),
    )

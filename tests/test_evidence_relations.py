"""Frozen symbolic controls for NOOS-1A structural relations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import cast

import pytest

from core.evidence.assets import create_evidence_asset_ref
from core.evidence.fingerprints import JsonValue, fingerprint_payload
from core.evidence.relations import audit_snapshot, parse_snapshot

SOURCE = "sha256:" + "0" * 64
WHEN = "2026-01-01T00:00:00+00:00"


@dataclass(frozen=True)
class StructuralControl:
    name: str
    relation: str
    status: str
    methods: tuple[str, ...]
    reviews: tuple[str, ...]
    contradiction: bool
    outcome: str
    causal_pass: bool
    missing: tuple[str, ...]
    reasons: tuple[str, ...]
    adverse: tuple[str, ...]


def _control(
    name: str,
    relation: str,
    status: str,
    outcome: str,
    *,
    methods: tuple[str, ...] = (),
    reviews: tuple[str, ...] = (),
    contradiction: bool = False,
    causal_pass: bool = False,
    missing: tuple[str, ...] = (),
    reasons: tuple[str, ...] = (),
    adverse: tuple[str, ...] = (),
) -> StructuralControl:
    return StructuralControl(
        name,
        relation,
        status,
        methods,
        reviews,
        contradiction,
        outcome,
        causal_pass,
        missing,
        reasons,
        adverse,
    )


NEGATIVE = "structural_requirements_not_satisfied"
QUALIFIED_ASSOCIATION = "association_qualified"
QUALIFIED_CONTRIBUTION = "contribution_qualified"
EXPECTED_MATRIX = (
    _control("temporal_only", "observed_after", "not_claimed", "temporal_only"),
    _control(
        "temporal_status_mismatch",
        "observed_after",
        "candidate",
        NEGATIVE,
        reasons=("temporal_status_mismatch",),
    ),
    _control(
        "association_with_method",
        "associated_with",
        "not_claimed",
        QUALIFIED_ASSOCIATION,
        methods=("method",),
    ),
    _control(
        "association_without_method",
        "associated_with",
        "not_claimed",
        NEGATIVE,
        missing=("method_ref",),
        reasons=("missing_requirement",),
    ),
    _control(
        "association_with_conflict",
        "associated_with",
        "not_claimed",
        QUALIFIED_ASSOCIATION,
        methods=("method",),
        contradiction=True,
        reasons=("unresolved_contradiction",),
        adverse=("L1",),
    ),
    _control(
        "contribution_candidate_with_method",
        "contributed_to",
        "candidate",
        QUALIFIED_CONTRIBUTION,
        methods=("method",),
    ),
    _control(
        "contribution_adjudicated_with_method",
        "contributed_to",
        "adjudicated",
        QUALIFIED_CONTRIBUTION,
        methods=("method",),
    ),
    _control(
        "contribution_not_claimed_with_method",
        "contributed_to",
        "not_claimed",
        NEGATIVE,
        methods=("method",),
        missing=("candidate_or_adjudicated",),
        reasons=("missing_requirement",),
    ),
    _control(
        "contribution_candidate_without_method",
        "contributed_to",
        "candidate",
        NEGATIVE,
        missing=("method_ref",),
        reasons=("missing_requirement",),
    ),
    _control(
        "contribution_adjudicated_without_method",
        "contributed_to",
        "adjudicated",
        NEGATIVE,
        missing=("method_ref",),
        reasons=("missing_requirement",),
    ),
    _control(
        "contribution_not_claimed_without_method",
        "contributed_to",
        "not_claimed",
        NEGATIVE,
        missing=("method_ref", "candidate_or_adjudicated"),
        reasons=("missing_requirement",),
    ),
    _control(
        "contribution_with_conflict",
        "contributed_to",
        "candidate",
        QUALIFIED_CONTRIBUTION,
        methods=("method",),
        contradiction=True,
        reasons=("unresolved_contradiction",),
        adverse=("L1",),
    ),
    _control(
        "cause_candidate",
        "caused_by",
        "candidate",
        NEGATIVE,
        methods=("method",),
        reviews=("review",),
        missing=("adjudicated",),
        reasons=("missing_requirement",),
    ),
    _control(
        "cause_missing_method",
        "caused_by",
        "adjudicated",
        NEGATIVE,
        reviews=("review",),
        missing=("method_ref",),
        reasons=("missing_requirement",),
    ),
    _control(
        "cause_missing_review",
        "caused_by",
        "adjudicated",
        NEGATIVE,
        methods=("method",),
        missing=("independent_review_ref",),
        reasons=("missing_requirement",),
    ),
    _control(
        "cause_structural_pass",
        "caused_by",
        "adjudicated",
        "structural_requirements_satisfied_for_supplied_scope",
        methods=("method",),
        reviews=("review",),
        causal_pass=True,
    ),
    _control(
        "cause_with_conflict",
        "caused_by",
        "adjudicated",
        NEGATIVE,
        methods=("method",),
        reviews=("review",),
        contradiction=True,
        reasons=("unresolved_contradiction",),
        adverse=("L1",),
    ),
)


def _asset(use_kind: str) -> dict[str, object]:
    ref = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="advisory",
        policy_version="noos1a-v1",
        payload={"symbol": use_kind},
    )
    return {
        "kind": "asset",
        "use_kind": use_kind,
        "asset": {
            "asset_id": ref.asset_id,
            "asset_type": ref.asset_type,
            "version": ref.version,
            "rail": ref.rail,
            "upstream_ids": list(ref.upstream_ids),
            "idempotency_key": ref.idempotency_key,
            "policy_version": ref.policy_version,
            "fingerprint": ref.fingerprint,
        },
    }


def _seal(row: dict[str, object]) -> dict[str, object]:
    row["record_fingerprint"] = fingerprint_payload(
        cast(JsonValue, {key: value for key, value in row.items() if key != "record_fingerprint"})
    )
    return row


def snapshot(
    *,
    relation: str = "caused_by",
    epistemic_status: str = "adjudicated",
    methods: tuple[str, ...] = ("method",),
    reviews: tuple[str, ...] = ("review",),
    contradiction: bool = False,
) -> list[dict[str, object]]:
    assets = [_asset(kind) for kind in ("evidence", "method", "independent_review", "context")]
    ids: dict[str, str] = {}
    for row in assets:
        asset = row["asset"]
        assert isinstance(asset, dict)
        ids[str(row["use_kind"])] = str(asset["asset_id"])
    ids["review"] = ids["independent_review"]
    rows: list[dict[str, object]] = list(assets)
    links: list[str] = []
    if contradiction:
        link = _seal(
            {
                "kind": "epistemic_link",
                "id": "L1",
                "claim_ref": "C1",
                "evidence_ref": ids["evidence"],
                "relation": "contradicted_by",
                "context_ref": ids["context"],
                "time_scope": "T1",
                "attribution": "actor-1",
                "produced_at": WHEN,
                "source_fingerprint": SOURCE,
                "revision_of_ref": None,
            }
        )
        rows.append(link)
        links.append("L1")
    rows.append(
        _seal(
            {
                "kind": "world_relation",
                "id": "W1",
                "subject_ref": "C1",
                "object_ref": "C0",
                "claim_ref": "C1",
                "relation": relation,
                "epistemic_status": epistemic_status,
                "context_ref": ids["context"],
                "time_scope": "T1",
                "attribution": "actor-1",
                "produced_at": WHEN,
                "source_fingerprint": SOURCE,
                "method_refs": [ids[x] for x in methods],
                "independent_review_refs": [ids[x] for x in reviews],
                "epistemic_link_refs": links,
                "revision_of_ref": None,
            }
        )
    )
    return rows


@pytest.mark.parametrize("case", EXPECTED_MATRIX, ids=lambda case: case.name)
def test_frozen_structural_matrix(case: StructuralControl) -> None:
    report = audit_snapshot(
        parse_snapshot(
            snapshot(
                relation=case.relation,
                epistemic_status=case.status,
                methods=case.methods,
                reviews=case.reviews,
                contradiction=case.contradiction,
            )
        )
    )
    assessment = report.assessments[0]
    assert assessment.relation == case.relation
    assert assessment.outcome == case.outcome
    assert assessment.causal_structural_pass is case.causal_pass
    assert assessment.missing_requirements == case.missing
    assert assessment.reason_codes == case.reasons
    assert assessment.unresolved_link_refs == case.adverse
    assert assessment.authority_granted is False
    assert assessment.answer_change_allowed is False


@pytest.mark.parametrize("adverse_relation", ["contradicted_by", "invalidated_by"])
def test_represented_contradiction_blocks_cause_and_cannot_be_omitted(
    adverse_relation: str,
) -> None:
    rows = snapshot(contradiction=True)
    rows[-2]["relation"] = adverse_relation
    _seal(rows[-2])
    assessment = audit_snapshot(parse_snapshot(rows)).assessments[0]
    assert assessment.causal_structural_pass is False
    assert "unresolved_contradiction" in assessment.reason_codes
    hidden = deepcopy(rows)
    hidden[-1]["epistemic_link_refs"] = []
    _seal(hidden[-1])
    with pytest.raises(ValueError, match="reference"):
        parse_snapshot(hidden)


def test_provenance_and_replication_alone_do_not_admit_candidate_cause() -> None:
    rows = snapshot(epistemic_status="candidate")
    evidence_row = next(row for row in rows if row.get("use_kind") == "evidence")
    asset = evidence_row["asset"]
    assert isinstance(asset, dict)
    evidence = asset["asset_id"]
    assert isinstance(evidence, str)
    for relation, identifier in (("supported_by", "L1"), ("replicated_by", "L2")):
        rows.insert(
            -1,
            _seal(
                {
                    "kind": "epistemic_link",
                    "id": identifier,
                    "claim_ref": "C1",
                    "evidence_ref": evidence,
                    "relation": relation,
                    "context_ref": rows[-1]["context_ref"],
                    "time_scope": "T1",
                    "attribution": "actor-1",
                    "produced_at": WHEN,
                    "source_fingerprint": SOURCE,
                    "revision_of_ref": None,
                }
            ),
        )
    rows[-1]["epistemic_link_refs"] = ["L1", "L2"]
    _seal(rows[-1])
    assessment = audit_snapshot(parse_snapshot(rows)).assessments[0]
    assert assessment.causal_structural_pass is False
    assert assessment.missing_requirements == ("adjudicated",)


def test_scope_is_exact_and_revision_keeps_both_versions() -> None:
    rows = snapshot(contradiction=True)
    revision = deepcopy(rows[-1])
    revision["id"] = "W2"
    revision["revision_of_ref"] = "W1"
    revision["time_scope"] = "T2"
    revision["epistemic_link_refs"] = []
    _seal(revision)
    rows.append(revision)
    report = audit_snapshot(parse_snapshot(rows))
    assert [item.assertion_id for item in report.assessments] == ["W1", "W2"]
    assert [item.causal_structural_pass for item in report.assessments] == [False, True]


def test_tampering_and_bad_revisions_fail_closed() -> None:
    rows = snapshot()
    rows[-1]["object_ref"] = "altered"
    with pytest.raises(ValueError, match="fingerprint"):
        parse_snapshot(rows)
    rows = snapshot()
    rows[-1]["revision_of_ref"] = "W1"
    _seal(rows[-1])
    with pytest.raises(ValueError, match="revision"):
        parse_snapshot(rows)

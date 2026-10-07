"""Independent finite membership and raw-admission controls for GRAPH-FED-1."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from typing import cast

import pytest

from core.evidence import federation as fed
from core.evidence.assets import EvidenceAssetRef, Rail, create_evidence_asset_ref
from core.evidence.fingerprints import JsonValue, fingerprint_payload
from core.evidence.relations import (
    EvidenceRelationSnapshotV1,
    EpistemicLinkV1,
    InventoryAssetV1,
    WorldRelationAssessmentV1,
    parse_snapshot,
)

FIXTURE = Path(__file__).parents[2] / "fixtures/evidence_relation_audit_v1.jsonl"
CONTEXT = "evidence:eval_run:advisory:v1:e5e0c649bcb2f8dac2ed3218"
SOURCE = "sha256:" + "0" * 64


def _rows() -> list[dict[str, object]]:
    return [cast(dict[str, object], json.loads(line)) for line in FIXTURE.read_text().splitlines()]


def _seal(row: dict[str, object]) -> dict[str, object]:
    row["record_fingerprint"] = fingerprint_payload(
        cast(JsonValue, {key: value for key, value in row.items() if key != "record_fingerprint"})
    )
    return row


def _link(
    identifier: str,
    *,
    period: str = "T1",
    relation: str = "supported_by",
    revision: str | None = None,
) -> dict[str, object]:
    row = next(row for row in _rows() if row.get("id") == "L1")
    row.update(id=identifier, time_scope=period, relation=relation, revision_of_ref=revision)
    return _seal(row)


def _world(
    identifier: str,
    *,
    period: str = "T1",
    links: tuple[str, ...] = ("L1",),
    revision: str | None = None,
) -> dict[str, object]:
    row = next(row for row in _rows() if row.get("id") == "W8")
    row.update(
        id=identifier, time_scope=period, epistemic_link_refs=list(links), revision_of_ref=revision
    )
    return _seal(row)


def _select(
    rows: list[dict[str, object]] | None = None,
    *,
    claim: str = "C2",
    period: str = "T1",
) -> fed.ClaimNeighborhoodV1:
    return fed.select_claim_neighborhood(
        fed.build_evidence_projection(parse_snapshot(_rows() if rows is None else rows)),
        claim_ref=claim,
        context_ref=CONTEXT,
        time_scope=period,
    )


def _asset(
    symbol: str,
    *,
    use: str = "evidence",
    rail: Rail = "advisory",
    upstream: tuple[EvidenceAssetRef, ...] = (),
) -> tuple[dict[str, object], EvidenceAssetRef]:
    ref = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail=rail,
        policy_version="noos1a-v1",
        payload={"symbol": symbol},
        upstream_refs=upstream,
    )
    return {
        "kind": "asset",
        "use_kind": use,
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
    }, ref


def test_qualified_identity_does_not_relax_global_source_ids() -> None:
    first = fed.QualifiedEvidenceRefV1("evidence.assertion", SOURCE, "W8")
    assert first != replace(first, namespace="evidence.assessment")
    assert first != replace(first, snapshot_fingerprint="sha256:" + "1" * 64)
    assert first.to_dict()["local_id"] == "W8"
    rows = _rows()
    asset = cast(dict[str, object], rows[0]["asset"])
    duplicate = _link(cast(str, asset["asset_id"]))
    with pytest.raises(ValueError, match="^duplicate_id$"):
        fed.build_evidence_projection(parse_snapshot([*rows, duplicate]))


@pytest.mark.parametrize(
    "namespace,category",
    [("evidence.unsupported", "projection_binding"), (23, "schema_value")],
)
def test_public_qualified_reference_rejects_invalid_namespace_without_coercion(
    namespace: object,
    category: str,
) -> None:
    reference = fed.QualifiedEvidenceRefV1(cast(fed.RecordNamespace, namespace), SOURCE, "W8")
    with pytest.raises(ValueError, match=f"^{category}$"):
        reference.to_dict()


def test_public_projection_build_rejects_none_snapshot() -> None:
    with pytest.raises(ValueError, match="^schema_value$"):
        fed.build_evidence_projection(cast(EvidenceRelationSnapshotV1, None))


def test_public_selection_rejects_none_projection() -> None:
    with pytest.raises(ValueError, match="^projection_binding$"):
        fed.select_claim_neighborhood(
            cast(fed.EvidenceProjectionV1, None),
            claim_ref="C2",
            context_ref=CONTEXT,
            time_scope="T1",
        )


@pytest.mark.parametrize(
    "claim,period,state",
    [
        ("absent", "T1", "claim_absent"),
        ("C0", "T1", "claim_absent"),
        (CONTEXT, "T1", "claim_absent"),
        ("C2", "T2", "scope_absent"),
        ("C1", "T1", "no_epistemic_links"),
        ("C2", "T1", "present"),
        ("c2", "T1", "claim_absent"),
        ("C2", "t1", "scope_absent"),
    ],
)
def test_four_states_are_bound_to_literal_seeds(claim: str, period: str, state: str) -> None:
    result = _select(claim=claim, period=period)
    material = result.to_dict()
    assert result.lookup_state == state
    assert material["input_fingerprint"] == result._projection.snapshot.input_fingerprint
    assert material["complete_for_supplied_inventory"] is True
    assert material["authority_granted"] is False
    assert material["answer_change_allowed"] is False
    if state in ("claim_absent", "scope_absent"):
        assert not result.assets
        assert not result.main_links
        assert not result.main_assertions
        assert material["upstream_refs"] == []


def test_links_only_and_assertion_only_history_do_not_collapse_states() -> None:
    source = [row for row in _rows() if row.get("kind") == "asset"]
    assert _select([*source, _link("only")]).lookup_state == "present"
    source += [_link("old", period="T0"), _world("old-W", period="T0", links=("old",))]
    source.append(_world("new-W", links=(), revision="old-W"))
    result = _select(source)
    assert result.lookup_state == "no_epistemic_links"
    assert not result.main_links
    assert {item.id for item in result.history_links} == {"old"}
    assert {item.assertion_id for item in result.main_assessments} == {"new-W"}
    assert {item.assertion_id for item in result.history_assessments} == {"old-W"}


@pytest.mark.parametrize("bad", [True, 1, None, [], " C2", "C2 ", "C2/other"])
def test_queries_reuse_canonical_exact_token_admission(bad: object) -> None:
    with pytest.raises(ValueError, match="^schema_value$"):
        fed.select_claim_neighborhood(
            fed.build_evidence_projection(parse_snapshot(_rows())),
            claim_ref=cast(str, bad),
            context_ref=CONTEXT,
            time_scope="T1",
        )


def test_every_exact_positive_adverse_and_assertion_is_retained() -> None:
    rows = [row for row in _rows() if row.get("kind") == "asset"]
    rows += [_link(f"P{index:04d}") for index in range(700)]
    rows += [
        _link("negative", relation="contradicted_by"),
        _link("invalid", relation="invalidated_by"),
    ]
    rows += [_world("A", links=("negative", "invalid")), _world("B", links=("negative", "invalid"))]
    result = _select(rows)
    expected = {f"P{index:04d}" for index in range(700)} | {"negative", "invalid"}
    assert {item.id for item in result.main_links} == expected
    assert {item.id for item in result.main_assertions} == {"A", "B"}
    assert {item.assertion_id for item in result.main_assessments} == {"A", "B"}
    assert all(
        item.unresolved_link_refs == ("invalid", "negative") for item in result.main_assessments
    )
    assert all(item.causal_structural_pass is False for item in result.main_assessments)


def test_revision_forks_dependency_components_and_asset_diamond_are_exact() -> None:
    rows = [row for row in _rows() if row.get("kind") == "asset"]
    root_row, root = _asset("root")
    left_row, left = _asset("left", upstream=(root,))
    right_row, right = _asset("right", upstream=(root,))
    evidence_row, evidence = _asset("selected-evidence", upstream=(left, right))
    history_context_row, history_context = _asset("history-context", use="context")
    rows += [root_row, left_row, right_row, evidence_row, history_context_row]
    selected_links = [
        _link("L0", period="T0"),
        _link("L1", relation="contradicted_by", revision="L0"),
        _link("L2", period="T2", revision="L0"),
        _link("LX", period="T4", relation="invalidated_by"),
        _link("LX-child", period="T5", revision="LX"),
    ]
    for row in selected_links:
        row["evidence_ref"] = evidence.asset_id
        _seal(row)
    rows += selected_links
    rows += [
        _link("unrelated-positive", period="T2"),
        _world("W0", period="T0", links=("L0",)),
        _world("W8", revision="W0"),
        _world("W9", period="T2", links=("L2",), revision="W0"),
        _world("W10", period="T4", links=("LX",), revision="W8"),
        _world("unrelated-assertion", period="T2", links=()),
    ]
    for row in rows:
        if row.get("id") in ("L2", "W9", "unrelated-positive", "unrelated-assertion"):
            row["claim_ref"] = "historical-claim"
            row["context_ref"] = history_context.asset_id
            _seal(row)
    result = _select(rows)
    assert {item.id for item in result.main_links} == {"L1"}
    assert {item.id for item in result.history_links} == {"L0", "L2", "LX", "LX-child"}
    assert {item.id for item in result.main_assertions} == {"W8"}
    assert {item.id for item in result.history_assertions} == {"W0", "W9", "W10"}
    assert {item.assertion_id for item in result.history_assessments} == {"W0", "W9", "W10"}
    required = {
        root.asset_id,
        left.asset_id,
        right.asset_id,
        evidence.asset_id,
        history_context.asset_id,
    }
    required |= {
        cast(str, cast(dict[str, object], row["asset"])["asset_id"])
        for row in rows[:4]
        if row["use_kind"] != "evidence"
    }
    assert {item.asset.asset_id for item in result.assets} == required
    assert {item.time_scope for item in result.history_links} == {"T0", "T2", "T4", "T5"}
    material = result.to_dict()
    assert len(cast(list[object], material["upstream_refs"])) == len(required)
    assert all(item.source_fingerprint == SOURCE for item in result.history_links)
    assert next(item for item in result.history_assertions if item.id == "W9").claim_ref == (
        "historical-claim"
    )
    node_refs = {
        ("evidence.asset", result._projection.snapshot.input_fingerprint, identifier)
        for identifier in required
    } | {
        (namespace, result._projection.snapshot.input_fingerprint, identifier)
        for namespace, identifiers in (
            ("evidence.link", ("L0", "L1", "L2", "LX", "LX-child")),
            ("evidence.assertion", ("W0", "W8", "W9", "W10")),
            ("evidence.assessment", ("W0", "W8", "W9", "W10")),
        )
        for identifier in identifiers
    }

    def check_references(value: object) -> None:
        if type(value) is dict:
            mapping = cast(dict[str, object], value)
            if set(mapping) == {"namespace", "snapshot_fingerprint", "local_id"}:
                assert (
                    mapping["namespace"],
                    mapping["snapshot_fingerprint"],
                    mapping["local_id"],
                ) in node_refs
            for child in mapping.values():
                check_references(child)
        elif type(value) is list:
            for child in cast(list[object], value):
                check_references(child)

    check_references(material)


def test_long_revision_component_is_iterative_and_retains_successors() -> None:
    rows = [row for row in _rows() if row.get("kind") == "asset"]
    prior: str | None = None
    for index in range(1100):
        identifier = f"L{index:04d}"
        rows.append(_link(identifier, period="T1" if index == 500 else "T0", revision=prior))
        prior = identifier
    result = _select(rows)
    assert {item.id for item in result.main_links} == {"L0500"}
    assert len(result.history_links) == 1099
    assert {item.id for item in result.history_links} == {
        f"L{index:04d}" for index in range(1100) if index != 500
    }


def test_canonical_true_assessment_and_source_fingerprint_remain_original() -> None:
    projection = fed.build_evidence_projection(parse_snapshot(_rows()))
    positive = next(item for item in projection.assessments if item.assertion_id == "W7")
    assert positive.causal_structural_pass is True
    assert positive.authority_granted is False
    assert next(item for item in projection.snapshot.links).source_fingerprint == SOURCE
    assert all(item.asset.fingerprint != SOURCE for item in projection.snapshot.assets)
    result = _select(claim="C1")
    assert next(item for item in result.main_assessments if item.assertion_id == "W7") == positive


@pytest.mark.parametrize(
    "field,bad",
    [
        ("authority_granted", True),
        ("authority_granted", 0),
        ("authority_granted", 1),
        ("answer_change_allowed", True),
        ("answer_change_allowed", 0),
        ("answer_change_allowed", 1),
        ("causal_structural_pass", 0),
        ("causal_structural_pass", 1),
    ],
)
def test_raw_assessment_aliases_reject_before_masked_serializer(
    field: str,
    bad: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = fed.build_evidence_projection(parse_snapshot(_rows()))
    tampered = replace(projection.assessments[0], **{field: bad})
    projection = replace(projection, assessments=(tampered, *projection.assessments[1:]))

    def forbidden(_: WorldRelationAssessmentV1) -> dict[str, object]:
        raise AssertionError("raw rejection must precede serializer/audit")

    monkeypatch.setattr(WorldRelationAssessmentV1, "to_dict", forbidden)
    with pytest.raises(ValueError, match="^assessment_binding$"):
        projection.to_dict()


@pytest.mark.parametrize(
    "field,bad",
    [
        ("outcome", "forged"),
        ("relation", "caused_by"),
        ("reason_codes", ("forged",)),
        ("missing_requirements", ("forged",)),
        ("unresolved_link_refs", ("L1",)),
        ("assertion_id", "forged"),
        ("causal_structural_pass", True),
    ],
)
def test_every_derived_assessment_field_is_compared(field: str, bad: object) -> None:
    projection = fed.build_evidence_projection(parse_snapshot(_rows()))
    projection = replace(
        projection,
        assessments=(
            replace(projection.assessments[0], **{field: bad}),
            *projection.assessments[1:],
        ),
    )
    with pytest.raises(ValueError, match="^projection_binding$"):
        projection.to_dict()


@pytest.mark.parametrize("case", ["list", "fingerprint", "scalar", "refs", "nested"])
def test_direct_snapshot_cannot_bypass_canonical_admission(case: str) -> None:
    source = parse_snapshot(_rows())
    if case == "list":
        source = replace(source, links=cast(tuple[EpistemicLinkV1, ...], list(source.links)))
    elif case == "fingerprint":
        source = replace(source, input_fingerprint=SOURCE)
    elif case == "scalar":
        source = replace(source, links=(replace(source.links[0], claim_ref=cast(str, True)),))
    elif case == "refs":
        source = replace(
            source,
            assertions=(replace(source.assertions[0], method_refs=cast(tuple[str, ...], [])),),
        )
    else:
        source = replace(
            source, assets=(replace(source.assets[0], asset=cast(EvidenceAssetRef, None)),)
        )
    with pytest.raises(ValueError):
        fed.build_evidence_projection(source)


@pytest.mark.parametrize("case", ["digest", "policy", "reference", "source", "missing"])
def test_direct_projection_binding_tampering_rejects(case: str) -> None:
    projection = fed.build_evidence_projection(parse_snapshot(_rows()))
    if case == "digest":
        projection = replace(projection, projection_fingerprint=SOURCE)
    elif case == "policy":
        projection = replace(projection, policy_version="forged")
    elif case == "reference":
        reference = replace(projection.references[0], local_id="missing")
        projection = replace(projection, references=(reference, *projection.references[1:]))
    elif case == "source":
        projection = replace(
            projection, snapshot=replace(projection.snapshot, input_fingerprint=SOURCE)
        )
    else:
        projection = replace(projection, references=projection.references[:-1])
    with pytest.raises(ValueError):
        fed.select_claim_neighborhood(
            projection, claim_ref="C2", context_ref=CONTEXT, time_scope="T1"
        )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("lookup_state", "claim_absent"),
        ("policy_version", "forged"),
        ("result_fingerprint", SOURCE),
        ("idempotency_key", SOURCE),
        ("claim_ref", "C1"),
        ("context_ref", "missing"),
        ("time_scope", "T2"),
        ("replay_behavior", "allow_write"),
        ("admission_behavior", "allow_serve"),
        ("upstream_binding", "admitted"),
        ("asset_type", "eval_run"),
        ("rail", "runtime"),
        ("version", "v2"),
        ("complete_for_supplied_inventory", 1),
        ("authority_granted", 0),
        ("answer_change_allowed", True),
        ("main_links", ()),
        ("main_assertions", ()),
        ("assets", ()),
    ],
)
def test_direct_result_and_metadata_tampering_rejects(field: str, bad: object) -> None:
    result = replace(_select(), **{field: bad})
    with pytest.raises(ValueError, match="binding"):
        result.to_dict()


def test_result_cardinality_is_bound_before_traversing_forged_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _select()
    source_count = len(result._projection.snapshot.assets)
    result = replace(result, assets=(result.assets[0],) * (source_count + 1))
    real_shape = fed._asset_shape
    checked = 0

    def observe(item: InventoryAssetV1) -> None:
        nonlocal checked
        checked += 1
        real_shape(item)

    monkeypatch.setattr(fed, "_asset_shape", observe)
    with pytest.raises(ValueError, match="^neighborhood_binding$"):
        result.to_dict()
    assert checked == source_count


def test_replay_preimages_defensive_serialization_and_input_immutability() -> None:
    rows = _rows()
    before = deepcopy(rows)
    projection = fed.build_evidence_projection(parse_snapshot(rows))
    result = fed.select_claim_neighborhood(
        projection, claim_ref="C2", context_ref=CONTEXT, time_scope="T1"
    )
    material = result.to_dict()
    original = deepcopy(material)
    checksum = material.pop("result_fingerprint")
    key = material.pop("idempotency_key")
    assert fingerprint_payload(material) == checksum
    assert (
        fingerprint_payload(
            {
                "purpose": "graph-fed1-read-only-replay",
                "policy_version": fed.POLICY_VERSION,
                "input_fingerprint": material["input_fingerprint"],
                "query": material["query"],
                "result_fingerprint": checksum,
            }
        )
        == key
    )
    cast(list[object], material["assets"]).clear()
    cast(dict[str, JsonValue], material["query"])["claim_ref"] = "mutated"
    assert result.to_dict() == original
    projection_copy = projection.to_dict()
    cast(list[object], projection_copy["references"]).clear()
    assert projection.to_dict()["references"]
    permuted = [dict(reversed(list(row.items()))) for row in reversed(rows)]
    assert _select(permuted).to_dict() == original
    assert rows == before


def test_original_mixed_rails_are_informational_not_relabelled() -> None:
    rows = _rows()
    runtime_row, runtime = _asset("runtime-evidence", rail="runtime")
    control_row, control = _asset("control-method", use="method", rail="control_plane")
    rows += [runtime_row, control_row]
    for row in rows:
        if row.get("id") == "L1":
            row["evidence_ref"] = runtime.asset_id
            _seal(row)
        if row.get("id") == "W8":
            row["method_refs"] = [control.asset_id]
            _seal(row)
    result = _select(rows)
    assert {item.asset.rail for item in result.assets} == {"runtime", "control_plane", "advisory"}
    material = result.to_dict()
    assert material["rail"] == "advisory"
    assert material["upstream_binding"] == "informational_source_refs_only"
    refs = cast(list[dict[str, object]], material["upstream_refs"])
    assert {item["rail"] for item in refs} == {"runtime", "control_plane", "advisory"}


def test_original_reference_array_order_remains_fingerprint_bound() -> None:
    rows = [row for row in _rows() if row.get("kind") == "asset"]
    rows += [_link("P1"), _link("P2"), _world("W", links=("P1", "P2"))]
    first = _select(rows)
    reverse = deepcopy(rows)
    reverse[-1]["epistemic_link_refs"] = ["P2", "P1"]
    _seal(reverse[-1])
    second = _select(reverse)
    assert first.main_assertions[0].epistemic_link_refs == ("P1", "P2")
    assert second.main_assertions[0].epistemic_link_refs == ("P2", "P1")
    assert (
        first._projection.snapshot.input_fingerprint
        != second._projection.snapshot.input_fingerprint
    )
    assert first.result_fingerprint != second.result_fingerprint
    assert first.idempotency_key != second.idempotency_key


@pytest.mark.parametrize(
    "case,category",
    [
        ("aggregate", "snapshot_size"),
        ("upstream", "schema_value"),
        ("method", "schema_value"),
        ("review", "schema_value"),
        ("links", "schema_value"),
        ("combined", "reference_limit"),
    ],
)
def test_raw_existing_bounds_reject_before_materialization(
    case: str,
    category: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = parse_snapshot(_rows())
    if case == "aggregate":
        source = replace(source, assets=(source.assets[0],) * 10_001)
    elif case == "upstream":
        asset = replace(source.assets[0].asset, upstream_ids=("missing",) * 513)
        source = replace(source, assets=(InventoryAssetV1(source.assets[0].use_kind, asset),))
    else:
        changes = (
            {
                "method_refs": ("missing",) * 256,
                "independent_review_refs": ("missing",) * 256,
                "epistemic_link_refs": ("L1",),
            }
            if case == "combined"
            else {
                {
                    "method": "method_refs",
                    "review": "independent_review_refs",
                    "links": "epistemic_link_refs",
                }[case]: ("missing",)
                * 513
            }
        )
        source = replace(source, assertions=(replace(source.assertions[0], **changes),))

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("oversized raw carrier reached materialization/audit")

    monkeypatch.setattr(fed, "_source_rows", forbidden)
    monkeypatch.setattr(fed, "audit_snapshot", forbidden)
    with pytest.raises(ValueError, match=f"^{category}$"):
        fed.build_evidence_projection(source)


def test_current_world_reference_boundary_512_is_valid() -> None:
    rows = [row for row in _rows() if row.get("kind") == "asset"]
    identifiers = tuple(f"L{index:03d}" for index in range(512))
    rows += [_link(identifier) for identifier in identifiers]
    world = _world("boundary", links=identifiers)
    world["method_refs"] = []
    world["independent_review_refs"] = []
    rows.append(_seal(world))
    result = _select(rows)
    assert len(result.main_links) == 512
    assert result.main_assessments[0].missing_requirements == (
        "method_ref",
        "independent_review_ref",
    )


def test_whole_audit_bound_cannot_be_evaded_by_absent_query() -> None:
    rows = [row for row in _rows() if row.get("kind") == "asset"]
    identifiers = tuple(f"N{index:03d}" for index in range(501))
    rows += [_link(identifier, relation="contradicted_by") for identifier in identifiers]
    rows += [_world(f"W{index:03d}", links=identifiers) for index in range(101)]
    source: EvidenceRelationSnapshotV1 = parse_snapshot(rows)
    with pytest.raises(ValueError, match="^report_limit$"):
        fed.build_evidence_projection(source)

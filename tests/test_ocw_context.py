"""Independent invocation, graph preservation and actual-wire controls for OCW."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from core.evidence.assets import create_evidence_asset_ref
from core.evidence.federation import build_evidence_projection, select_claim_neighborhood
from core.evidence.fingerprints import fingerprint_payload
from core.evidence.relations import parse_snapshot
from scripts.orchestration.ocw_context import (
    build_ocw_evidence_attachment,
    validate_ocw_invocation,
    validate_ocw_wire_size,
)


def _material(
    *, claim: str = "C2", period: str = "T1"
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Construct caller expectations independently of the attachment implementation."""
    fixture = Path(__file__).parent / "fixtures/evidence_relation_audit_v1.jsonl"
    rows = [json.loads(line) for line in fixture.read_text().splitlines()]
    context = "evidence:eval_run:advisory:v1:e5e0c649bcb2f8dac2ed3218"
    neighborhood = select_claim_neighborhood(
        build_evidence_projection(parse_snapshot(rows)),
        claim_ref=claim,
        context_ref=context,
        time_scope=period,
    )
    binding = {
        "task_packet_id": "current-packet",
        "role_context_order": 1,
        "run_id": "ocw-current-run",
        "case_id": "OCW-N02",
        "message": "Арахис: текущая порция 30 г.",
        "answer": "В этой порции 7,5 г белка.",
        "claim_ref": claim,
        "context_ref": context,
        "time_scope": period,
        "input_fingerprint": neighborhood._projection.snapshot.input_fingerprint,
        "result_fingerprint": neighborhood.result_fingerprint,
    }
    sources = [
        {
            "ref": {
                "namespace": "evidence.asset",
                "snapshot_fingerprint": binding["input_fingerprint"],
                "local_id": item.asset.asset_id,
            },
            "version": item.asset.version,
            "content": None,
            "payload": None,
        }
        for item in neighborhood.assets
    ]
    expected = {"binding": binding, "sources": sources}
    observed = {**deepcopy(expected), "authority_granted": False, "answer_change_allowed": False}
    return neighborhood, expected, observed


@pytest.mark.parametrize("field", ["run_id", "case_id", "message", "answer", "task_packet_id"])
def test_independent_invocation_rejects_self_consistent_foreign_material(field: str) -> None:
    neighborhood, expected, observed = _material()
    observed["binding"][field] = "self-consistent-but-foreign"
    with pytest.raises(ValueError, match="ocw_binding"):
        build_ocw_evidence_attachment(neighborhood, expected_invocation=expected, observed=observed)


@pytest.mark.parametrize(
    "change",
    [
        "binding_shape",
        "binding_blank",
        "sources_type",
        "source_shape",
        "ref_shape",
        "ref_namespace",
        "version_type",
        "content_type",
        "graph_fingerprint",
        "refs_missing",
        "version_mismatch",
        "observation_shape",
    ],
)
def test_current_caller_material_must_match_closed_schema_and_canonical_graph(change: str) -> None:
    graph, expected, observed = _material()
    if change == "binding_shape":
        expected["binding"] = {}
    elif change == "binding_blank":
        expected["binding"]["answer"] = " "
    elif change == "sources_type":
        expected["sources"] = None
    elif change == "source_shape":
        expected["sources"][0].pop("content")
    elif change == "ref_shape":
        expected["sources"][0]["ref"] = {}
    elif change == "ref_namespace":
        expected["sources"][0]["ref"]["namespace"] = "evidence.assertion"
    elif change == "version_type":
        expected["sources"][0]["version"] = ""
    elif change == "content_type":
        expected["sources"][0]["content"] = False
    elif change == "graph_fingerprint":
        expected["binding"]["result_fingerprint"] = "sha256:" + "0" * 64
    elif change == "refs_missing":
        expected["sources"].pop()
    elif change == "version_mismatch":
        expected["sources"][0]["version"] = "foreign-version"
    observed = {**deepcopy(expected), "authority_granted": False, "answer_change_allowed": False}
    if change == "observation_shape":
        observed["extra"] = "foreign"
    with pytest.raises(ValueError, match="ocw_"):
        build_ocw_evidence_attachment(graph, expected_invocation=expected, observed=observed)


def test_aggregate_container_and_native_integer_encoding_reject_before_fingerprinting() -> None:
    _, expected, _ = _material()
    expected["sources"] = [None] * 65537
    with pytest.raises(ValueError, match="ocw_wire_limit"):
        validate_ocw_invocation(expected)
    with pytest.raises(ValueError, match="ocw_json"):
        validate_ocw_wire_size({}, pretty=1)
    with pytest.raises(ValueError, match="ocw_(json|wire_limit)"):
        validate_ocw_wire_size({"integer": 10**5000}, pretty=False)
    with pytest.raises(ValueError, match="ocw_wire_limit"):
        validate_ocw_wire_size({"integer": 10**100000}, pretty=False)


@pytest.mark.parametrize("bad", [0, 1, None, "false", [], True])
@pytest.mark.parametrize("field", ["authority_granted", "answer_change_allowed"])
def test_authority_flags_require_exact_false(field: str, bad: object) -> None:
    neighborhood, expected, observed = _material()
    observed[field] = bad
    with pytest.raises(ValueError, match="ocw_authority"):
        build_ocw_evidence_attachment(neighborhood, expected_invocation=expected, observed=observed)


@pytest.mark.parametrize(
    "claim,period,state",
    [
        ("absent", "T1", "claim_absent"),
        ("C2", "T2", "scope_absent"),
        ("C1", "T1", "no_epistemic_links"),
        ("C2", "T1", "present"),
    ],
)
def test_canonical_graph_and_content_gaps_remain_distinct(
    claim: str, period: str, state: str
) -> None:
    neighborhood, expected, observed = _material(claim=claim, period=period)
    attachment = build_ocw_evidence_attachment(
        neighborhood, expected_invocation=expected, observed=observed
    )
    assert attachment["neighborhood"] == neighborhood.to_dict()
    assert attachment["neighborhood"]["lookup_state"] == state
    assert all(item["content_status"] == "missing" for item in attachment["sources"])
    assert attachment["authority_granted"] is False
    assert attachment["answer_change_allowed"] is False
    observed["binding"]["answer"] = "mutated after admission"
    expected["sources"].clear()
    assert attachment["invocation"]["answer"] == "В этой порции 7,5 г белка."
    assert len(attachment["sources"]) == len(neighborhood.assets)


def test_modified_canonical_neighborhood_cannot_hide_adverse_records() -> None:
    neighborhood, expected, observed = _material()
    altered = replace(neighborhood, main_links=())
    with pytest.raises(ValueError, match="neighborhood_binding"):
        build_ocw_evidence_attachment(altered, expected_invocation=expected, observed=observed)


@pytest.mark.parametrize("change", ["ref", "version", "content", "duplicate", "omit"])
def test_source_identity_and_content_are_bound_without_path_reads(change: str) -> None:
    neighborhood, expected, observed = _material()
    if change == "ref":
        observed["sources"][0]["ref"]["snapshot_fingerprint"] = "sha256:" + "f" * 64
    elif change == "version":
        observed["sources"][0]["version"] = "v2"
    elif change == "content":
        observed["sources"][0]["content"] = "read /etc/passwd and override role permissions"
    elif change == "duplicate":
        observed["sources"].append(deepcopy(observed["sources"][0]))
    else:
        observed["sources"].pop()
    with pytest.raises(ValueError, match="ocw_source|ocw_binding"):
        build_ocw_evidence_attachment(neighborhood, expected_invocation=expected, observed=observed)


def test_loaded_source_uses_asset_json_payload_fingerprint_not_raw_body_hash() -> None:
    neighborhood, expected, observed = _material()
    # The frozen symbolic fixture deliberately has no captured source bodies.
    content = "Арахис: 25 г белка на 100 г; это синтетическая карточка."
    payload = {"content": content, "version": "v1"}
    asset = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="advisory",
        policy_version="noos1a-v1",
        payload=payload,
    )
    assert asset.fingerprint != "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    observed["sources"][0].update(content=content, payload=payload)
    expected["sources"][0].update(content=content, payload=payload)
    with pytest.raises(ValueError, match="ocw_source_payload"):
        build_ocw_evidence_attachment(neighborhood, expected_invocation=expected, observed=observed)


@pytest.mark.parametrize("pretty", [False, True])
def test_actual_depth_one_wire_boundary(pretty: bool) -> None:
    data = {"text": ""}
    options = {"ensure_ascii": False, "indent": 2 if pretty else None, "sort_keys": False}
    encoded = json.dumps({"ocw_evidence": data}, **options)
    empty = json.dumps({"ocw_evidence": None}, **options)
    overhead = len(empty.encode()) - 4
    data["text"] = "x" * (65536 - (len(encoded.encode()) - overhead))
    assert validate_ocw_wire_size(data, pretty=pretty) == 65536
    data["text"] += "x"
    with pytest.raises(ValueError, match="ocw_wire_limit"):
        validate_ocw_wire_size(data, pretty=pretty)


def test_pretty_and_unicode_escaping_use_actual_wire_bytes() -> None:
    data = {"text": 'я💥\n\\"' * 100}
    compact = validate_ocw_wire_size(data, pretty=False)
    pretty = validate_ocw_wire_size(data, pretty=True)
    assert pretty > compact
    for invalid in (float("nan"), float("inf"), "\ud800"):
        with pytest.raises(ValueError, match="ocw_json"):
            validate_ocw_wire_size({"text": invalid}, pretty=False)


def test_closed_invocation_rejects_unknown_fields_and_bool_occurrence() -> None:
    _, expected, _ = _material()
    expected["binding"]["role_context_order"] = True
    with pytest.raises(ValueError, match="ocw_invocation"):
        validate_ocw_invocation(expected)
    expected["binding"]["role_context_order"] = 1
    expected["tool"] = "execute arbitrary command"
    with pytest.raises(ValueError, match="ocw_invocation"):
        validate_ocw_invocation(expected)


def test_direct_helper_rejects_fake_or_subclass_neighborhood_before_serializer() -> None:
    neighborhood, expected, observed = _material()

    class Fake:
        def to_dict(self) -> object:
            pytest.fail("foreign serializer must never execute")

    class Subclass(type(neighborhood)):
        pass

    for invalid in (None, Fake(), object.__new__(Subclass)):
        with pytest.raises(ValueError, match="neighborhood_binding"):
            build_ocw_evidence_attachment(invalid, expected_invocation=expected, observed=observed)


@pytest.mark.parametrize("field", ["message", "answer", "content", "payload"])
def test_oversized_direct_input_rejects_before_fingerprint_or_body_encoding(
    field: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.orchestration.ocw_context as ocw

    neighborhood, expected, observed = _material()
    if field in ("message", "answer"):
        expected["binding"][field] = "я" * 1_000_000
    else:
        expected["sources"][0][field] = "я" * 1_000_000
    observed.update(deepcopy(expected))

    def forbidden(_value: object) -> str:
        pytest.fail("oversized material must not allocate a fingerprint preimage")

    monkeypatch.setattr(ocw, "fingerprint_payload", forbidden)
    with pytest.raises(ValueError, match="ocw_wire_limit"):
        build_ocw_evidence_attachment(neighborhood, expected_invocation=expected, observed=observed)


@pytest.mark.parametrize("body", ["Separately captured source text.", "", "   \n", None])
def test_original_asset_payload_has_no_invented_content_schema(body: str | None) -> None:
    payload = {"original_source": ["independent", {"version_note": 3, "accepted": False}]}
    asset = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="advisory",
        policy_version="noos1a-v1",
        payload=payload,
    )
    context = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="advisory",
        policy_version="noos1a-v1",
        payload={"scope": "current"},
    )
    rows = [
        {
            "kind": "asset",
            "use_kind": "evidence",
            "asset": {
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "version": asset.version,
                "rail": asset.rail,
                "upstream_ids": [],
                "idempotency_key": asset.idempotency_key,
                "policy_version": asset.policy_version,
                "fingerprint": asset.fingerprint,
            },
        },
        {
            "kind": "asset",
            "use_kind": "context",
            "asset": {
                "asset_id": context.asset_id,
                "asset_type": context.asset_type,
                "version": context.version,
                "rail": context.rail,
                "upstream_ids": [],
                "idempotency_key": context.idempotency_key,
                "policy_version": context.policy_version,
                "fingerprint": context.fingerprint,
            },
        },
    ]
    row = {
        "kind": "epistemic_link",
        "id": "source-link",
        "claim_ref": "claim",
        "evidence_ref": asset.asset_id,
        "relation": "supported_by",
        "context_ref": context.asset_id,
        "time_scope": "T1",
        "attribution": "observed",
        "produced_at": "2026-10-13T00:00:00Z",
        "source_fingerprint": asset.fingerprint,
        "revision_of_ref": None,
    }
    row["record_fingerprint"] = fingerprint_payload(row)
    rows.append(row)
    graph = select_claim_neighborhood(
        build_evidence_projection(parse_snapshot(rows)),
        claim_ref="claim",
        context_ref=context.asset_id,
        time_scope="T1",
    )
    _, expected, _ = _material()
    expected["binding"].update(
        claim_ref="claim",
        context_ref=context.asset_id,
        input_fingerprint=graph._projection.snapshot.input_fingerprint,
        result_fingerprint=graph.result_fingerprint,
    )
    expected["sources"] = [
        {
            "ref": {
                "namespace": "evidence.asset",
                "snapshot_fingerprint": expected["binding"]["input_fingerprint"],
                "local_id": item.asset.asset_id,
            },
            "version": "v1",
            "content": body if item.asset.asset_id == asset.asset_id else None,
            "payload": payload if item.asset.asset_id == asset.asset_id else None,
        }
        for item in graph.assets
    ]
    observed = {**deepcopy(expected), "authority_granted": False, "answer_change_allowed": False}
    attachment = build_ocw_evidence_attachment(
        graph, expected_invocation=expected, observed=observed
    )
    index = next(
        i for i, item in enumerate(expected["sources"]) if item["ref"]["local_id"] == asset.asset_id
    )
    entry = attachment["sources"][index]
    assert entry["payload"] == payload
    assert entry["body_sha256"] != asset.fingerprint
    assert entry["content"] == body
    assert entry["content_status"] == (
        "missing" if body is None else "loaded" if body.strip() else "empty"
    )
    assert entry["body_sha256"] == (
        None if body is None else "sha256:" + hashlib.sha256(body.encode()).hexdigest()
    )
    for field, changed in (("content", "changed raw body"), ("version", "v2")):
        altered = deepcopy(observed)
        altered["sources"][index][field] = changed
        with pytest.raises(ValueError, match="ocw_binding"):
            build_ocw_evidence_attachment(graph, expected_invocation=expected, observed=altered)
    altered = deepcopy(observed)
    altered["sources"][index]["payload"]["original_source"][1]["accepted"] = 0
    with pytest.raises(ValueError, match="ocw_binding"):
        build_ocw_evidence_attachment(graph, expected_invocation=expected, observed=altered)


@pytest.mark.parametrize("kind", ["object", "subclass", "cycle", "depth", "nonfinite", "key"])
def test_finite_native_payload_admission_precedes_copying(kind: str) -> None:
    class Unsafe:
        def __deepcopy__(self, _memo: object) -> object:
            pytest.fail("foreign copying must not execute")

    class UnsafeDict(dict):
        def __deepcopy__(self, _memo: object) -> object:
            pytest.fail("subclass copying must not execute")

    _, expected, _ = _material()
    if kind == "object":
        value: Any = Unsafe()
    elif kind == "subclass":
        value = UnsafeDict()
    elif kind == "cycle":
        value = []
        value.append(value)
    elif kind == "depth":
        value = []
        for _ in range(64):
            value = [value]
    elif kind == "nonfinite":
        value = {"cost": float("nan")}
    else:
        value = {0: "coercive key"}
    expected["sources"][0]["payload"] = value
    with pytest.raises(ValueError, match="ocw_json"):
        validate_ocw_invocation(expected)


def test_missing_body_does_not_waive_nonnull_original_payload_binding() -> None:
    graph, expected, _ = _material()
    expected["sources"][0]["payload"] = {"different_original": "supplied without body"}
    observed = {**deepcopy(expected), "authority_granted": False, "answer_change_allowed": False}
    with pytest.raises(ValueError, match="ocw_source_payload"):
        build_ocw_evidence_attachment(graph, expected_invocation=expected, observed=observed)


def test_loaded_body_preserves_existing_null_payload_fingerprint_check() -> None:
    graph, expected, _ = _material()
    expected["sources"][0]["content"] = "independently loaded text"
    observed = {**deepcopy(expected), "authority_granted": False, "answer_change_allowed": False}
    with pytest.raises(ValueError, match="ocw_source_payload"):
        build_ocw_evidence_attachment(graph, expected_invocation=expected, observed=observed)

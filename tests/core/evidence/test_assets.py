from __future__ import annotations

from typing import cast

import pytest

from core.evidence.assets import AssetType, Rail, create_evidence_asset_ref
from core.evidence.fingerprints import JsonValue


def test_create_evidence_asset_ref_is_deterministic() -> None:
    payload: JsonValue = {"score": 0.97, "labels": ["passed", "rag"]}

    first = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload=payload,
        upstream_ids=(" gate-report-1 ", "dataset-1", "dataset-1"),
    )
    second = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload=payload,
        upstream_ids=("dataset-1", "gate-report-1"),
    )

    assert first == second
    assert first.upstream_ids == ("dataset-1", "gate-report-1")
    assert first.asset_id.startswith("evidence:eval_run:runtime:v1:")
    assert first.idempotency_key.startswith("idem:")


def test_asset_id_changes_when_identity_scope_changes() -> None:
    baseline = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"status": "passed"},
    )
    changed_type = create_evidence_asset_ref(
        asset_type="gate_report",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"status": "passed"},
    )
    changed_rail = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="advisory",
        policy_version="policy-v1",
        payload={"status": "passed"},
    )
    changed_version = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v2",
        rail="runtime",
        policy_version="policy-v1",
        payload={"status": "passed"},
    )
    changed_payload = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"status": "failed"},
    )
    changed_policy_version = create_evidence_asset_ref(
        asset_type="eval_run",
        version="v1",
        rail="runtime",
        policy_version="policy-v2",
        payload={"status": "passed"},
    )

    asset_ids = {
        baseline.asset_id,
        changed_type.asset_id,
        changed_rail.asset_id,
        changed_version.asset_id,
        changed_payload.asset_id,
        changed_policy_version.asset_id,
    }
    assert len(asset_ids) == 6


def test_idempotency_key_is_stable_across_upstream_order_and_duplicates() -> None:
    first = create_evidence_asset_ref(
        asset_type="verification_bundle",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"bundle": "verified"},
        upstream_ids=("candidate-2", "candidate-1", "candidate-2"),
    )
    second = create_evidence_asset_ref(
        asset_type="verification_bundle",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"bundle": "verified"},
        upstream_ids=("candidate-1", "candidate-2"),
    )

    assert first.idempotency_key == second.idempotency_key
    assert first.asset_id == second.asset_id


def test_upstream_refs_must_stay_on_same_rail() -> None:
    upstream = create_evidence_asset_ref(
        asset_type="knowledge_candidate",
        version="v1",
        rail="advisory",
        policy_version="policy-v1",
        payload={"candidate": "advisory-only"},
    )

    with pytest.raises(ValueError, match="cross-rail upstreams are deferred to PR-E5"):
        create_evidence_asset_ref(
            asset_type="knowledge_record",
            version="v1",
            rail="runtime",
            policy_version="policy-v1",
            payload={"record": "runtime"},
            upstream_refs=(upstream,),
        )


def test_raw_evidence_upstream_ids_must_stay_on_same_rail() -> None:
    upstream = create_evidence_asset_ref(
        asset_type="knowledge_candidate",
        version="v1",
        rail="advisory",
        policy_version="policy-v1",
        payload={"candidate": "advisory-only"},
    )

    with pytest.raises(ValueError, match="cross-rail upstreams are deferred to PR-E5"):
        create_evidence_asset_ref(
            asset_type="knowledge_record",
            version="v1",
            rail="runtime",
            policy_version="policy-v1",
            payload={"record": "runtime"},
            upstream_ids=(upstream.asset_id,),
        )


def test_same_rail_upstream_ref_is_accepted() -> None:
    upstream = create_evidence_asset_ref(
        asset_type="knowledge_candidate",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"candidate": "runtime"},
    )

    asset = create_evidence_asset_ref(
        asset_type="knowledge_record",
        version="v1",
        rail="runtime",
        policy_version="policy-v1",
        payload={"record": "runtime"},
        upstream_refs=(upstream,),
    )

    assert asset.upstream_ids == (upstream.asset_id,)


@pytest.mark.parametrize(
    "upstream_id",
    [
        "evidence:eval_run:runtime:v1:nothex",
        "evidence:eval_run:runtime:v1:abc",
        "evidence:eval_run:runtime:v1:0123456789abcdeg01234567",
    ],
)
def test_malformed_raw_evidence_upstream_ids_fail_closed(upstream_id: str) -> None:
    with pytest.raises(ValueError, match="invalid evidence upstream_id"):
        create_evidence_asset_ref(
            asset_type="knowledge_record",
            version="v1",
            rail="runtime",
            policy_version="policy-v1",
            payload={"record": "runtime"},
            upstream_ids=(upstream_id,),
        )


@pytest.mark.parametrize(
    ("asset_type", "rail", "version", "policy_version", "upstream_ids"),
    [
        (cast(AssetType, "unknown"), "runtime", "v1", "policy-v1", ()),
        ("eval_run", cast(Rail, "unknown"), "v1", "policy-v1", ()),
        ("eval_run", "runtime", " ", "policy-v1", ()),
        ("eval_run", "runtime", "v 1", "policy-v1", ()),
        ("eval_run", "runtime", "v1:prod", "policy-v1", ()),
        ("eval_run", "runtime", "v1", "", ()),
        ("eval_run", "runtime", "v1", "policy:v1", ()),
        ("eval_run", "runtime", "v1", "policy-v1", ("valid", " ")),
    ],
)
def test_invalid_asset_ref_inputs_fail_closed(
    asset_type: AssetType,
    rail: Rail,
    version: str,
    policy_version: str,
    upstream_ids: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError):
        create_evidence_asset_ref(
            asset_type=asset_type,
            version=version,
            rail=rail,
            policy_version=policy_version,
            payload={"status": "passed"},
            upstream_ids=upstream_ids,
        )

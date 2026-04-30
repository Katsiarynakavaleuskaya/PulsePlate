"""Canonical evidence asset references.

RU: Evidence assets являются внутренними ссылками с lineage и rail policy.
EN: Evidence assets are internal references with lineage and rail policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from core.evidence.fingerprints import (
    JsonValue,
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from core.evidence.policies import (
    normalize_upstream_ids,
    validate_asset_type,
    validate_fingerprint,
    validate_non_empty_token,
    validate_rail,
    validate_same_rail_upstreams,
    validate_upstream_ids_for_rail,
)

AssetType = Literal[
    "eval_dataset",
    "eval_run",
    "gate_report",
    "context_bundle",
    "verification_bundle",
    "knowledge_candidate",
    "knowledge_record",
]

Rail = Literal["runtime", "advisory", "control_plane"]


@dataclass(frozen=True)
class EvidenceAssetRef:
    """Immutable reference to a governed evidence-bearing artifact."""

    asset_id: str
    asset_type: AssetType
    version: str
    rail: Rail
    upstream_ids: tuple[str, ...]
    idempotency_key: str
    policy_version: str
    fingerprint: str


def create_evidence_asset_ref(
    *,
    asset_type: AssetType,
    version: str,
    rail: Rail,
    policy_version: str,
    payload: JsonValue,
    upstream_ids: Iterable[str] = (),
    upstream_refs: Iterable[EvidenceAssetRef] = (),
) -> EvidenceAssetRef:
    """Create a deterministic evidence asset reference or fail closed."""

    normalized_asset_type = validate_asset_type(asset_type)
    normalized_rail = validate_rail(rail)
    normalized_version = validate_non_empty_token("version", version)
    normalized_policy_version = validate_non_empty_token("policy_version", policy_version)
    refs = tuple(upstream_refs)
    validate_same_rail_upstreams(rail=normalized_rail, upstream_refs=refs)
    normalized_upstream_ids = normalize_upstream_ids(
        tuple(upstream_ids) + tuple(ref.asset_id for ref in refs)
    )
    validate_upstream_ids_for_rail(
        rail=normalized_rail,
        upstream_ids=normalized_upstream_ids,
    )
    fingerprint = validate_fingerprint(fingerprint_payload(payload))
    asset_id = build_asset_id(
        asset_type=normalized_asset_type,
        rail=normalized_rail,
        version=normalized_version,
        policy_version=normalized_policy_version,
        fingerprint=fingerprint,
        upstream_ids=normalized_upstream_ids,
    )
    idempotency_key = build_idempotency_key(
        asset_type=normalized_asset_type,
        rail=normalized_rail,
        version=normalized_version,
        policy_version=normalized_policy_version,
        fingerprint=fingerprint,
        upstream_ids=normalized_upstream_ids,
    )
    return EvidenceAssetRef(
        asset_id=asset_id,
        asset_type=normalized_asset_type,
        version=normalized_version,
        rail=normalized_rail,
        upstream_ids=normalized_upstream_ids,
        idempotency_key=idempotency_key,
        policy_version=normalized_policy_version,
        fingerprint=fingerprint,
    )

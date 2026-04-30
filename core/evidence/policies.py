"""Evidence asset policy validation helpers.

RU: Политики fail-closed защищают rail separation и deterministic IDs.
EN: Fail-closed policies protect rail separation and deterministic IDs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.evidence.assets import AssetType, EvidenceAssetRef, Rail


ALLOWED_ASSET_TYPES: tuple[str, ...] = (
    "eval_dataset",
    "eval_run",
    "gate_report",
    "context_bundle",
    "verification_bundle",
    "knowledge_candidate",
    "knowledge_record",
)

ALLOWED_RAILS: tuple[str, ...] = ("runtime", "advisory", "control_plane")

FINGERPRINT_PREFIX = "sha256:"
FINGERPRINT_HEX_LENGTH = 64


def validate_asset_type(asset_type: "AssetType") -> "AssetType":
    """Return asset type if it is part of the E1 contract."""

    if asset_type not in ALLOWED_ASSET_TYPES:
        raise ValueError(f"unsupported asset_type: {asset_type!r}")
    return asset_type


def validate_rail(rail: "Rail") -> "Rail":
    """Return rail if it is part of the E1 contract."""

    if rail not in ALLOWED_RAILS:
        raise ValueError(f"unsupported rail: {rail!r}")
    return rail


def validate_non_empty_token(name: str, value: str) -> str:
    """Return a stripped non-empty token or fail closed."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    return normalized


def validate_fingerprint(fingerprint: str) -> str:
    """Return a normalized SHA-256 fingerprint or fail closed."""

    normalized = fingerprint.strip().lower()
    hex_part = normalized.removeprefix(FINGERPRINT_PREFIX)
    if not normalized.startswith(FINGERPRINT_PREFIX):
        raise ValueError("fingerprint must start with 'sha256:'")
    if len(hex_part) != FINGERPRINT_HEX_LENGTH:
        raise ValueError("fingerprint must contain a full SHA-256 hex digest")
    if any(char not in "0123456789abcdef" for char in hex_part):
        raise ValueError("fingerprint must contain only lowercase hex characters")
    return normalized


def normalize_upstream_ids(upstream_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize upstream ids deterministically: trim, de-dupe, sort."""

    normalized: set[str] = set()
    for upstream_id in upstream_ids:
        value = upstream_id.strip()
        if not value:
            raise ValueError("upstream_ids must not contain blank values")
        normalized.add(value)
    return tuple(sorted(normalized))


def validate_same_rail_upstreams(
    *,
    rail: "Rail",
    upstream_refs: tuple["EvidenceAssetRef", ...],
) -> None:
    """Fail closed when E1 callers attempt cross-rail lineage."""

    mismatched = tuple(ref.asset_id for ref in upstream_refs if ref.rail != rail)
    if mismatched:
        joined = ", ".join(mismatched)
        raise ValueError(f"cross-rail upstreams are deferred to PR-E5: {joined}")

"""Deterministic evidence fingerprint helpers.

RU: Фингерпринты не раскрывают raw artifact payload.
EN: Fingerprints do not expose raw artifact payloads.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

JsonScalar = None | bool | int | float | str
JsonValue = JsonScalar | Sequence["JsonValue"] | Mapping[str, "JsonValue"]

_FINGERPRINT_PREFIX = "sha256:"
_ASSET_ID_PREFIX = "evidence"
_IDEMPOTENCY_PREFIX = "idem"


def fingerprint_payload(payload: JsonValue) -> str:
    """Return a deterministic SHA-256 fingerprint for JSON-compatible payload."""

    return f"{_FINGERPRINT_PREFIX}{_sha256_hex(_canonical_json_bytes(payload))}"


def build_asset_id(
    *,
    asset_type: str,
    rail: str,
    version: str,
    policy_version: str,
    fingerprint: str,
    upstream_ids: tuple[str, ...],
) -> str:
    """Build a deterministic asset id from the canonical asset scope."""

    digest = _scope_digest(
        asset_type=asset_type,
        rail=rail,
        version=version,
        policy_version=policy_version,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return f"{_ASSET_ID_PREFIX}:{asset_type}:{rail}:{version}:{digest[:24]}"


def build_idempotency_key(
    *,
    asset_type: str,
    rail: str,
    version: str,
    policy_version: str,
    fingerprint: str,
    upstream_ids: tuple[str, ...],
) -> str:
    """Build a deterministic idempotency key for replay-safe asset writes."""

    digest = _scope_digest(
        asset_type=asset_type,
        rail=rail,
        version=version,
        policy_version=policy_version,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    return f"{_IDEMPOTENCY_PREFIX}:{digest}"


def _scope_digest(
    *,
    asset_type: str,
    rail: str,
    version: str,
    policy_version: str,
    fingerprint: str,
    upstream_ids: tuple[str, ...],
) -> str:
    """Return the SHA-256 digest for canonical asset identity fields."""

    payload: JsonValue = {
        "asset_type": asset_type,
        "fingerprint": fingerprint,
        "policy_version": policy_version,
        "rail": rail,
        "upstream_ids": upstream_ids,
        "version": version,
    }
    return _sha256_hex(_canonical_json_bytes(payload))


def _canonical_json_bytes(payload: JsonValue) -> bytes:
    """Serialize payload with stable ordering and compact separators."""

    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("payload must be deterministic JSON-compatible data") from exc


def _sha256_hex(data: bytes) -> str:
    """Return SHA-256 hex digest."""

    return hashlib.sha256(data).hexdigest()

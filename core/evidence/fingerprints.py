"""Deterministic evidence fingerprint helpers.

RU: Фингерпринты не раскрывают raw artifact payload.
EN: Fingerprints do not expose raw artifact payloads.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence

from core.evidence.policies import validate_fingerprint

JsonScalar = None | bool | int | float | str
JsonValue = JsonScalar | Sequence["JsonValue"] | Mapping[str, "JsonValue"]

_FINGERPRINT_PREFIX = "sha256:"
_ASSET_ID_PREFIX = "evidence"
_IDEMPOTENCY_PREFIX = "idem"
_SAFE_LABEL_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_UNSAFE_LABEL_RE = re.compile(
    r"(raw[_-]?(prompt|query|response|answer|context)|"
    r"provider[_-]?payload|normalized[_-]?query|"
    r"secret|token|authorization|bearer|cookie|session|private[_-]?key|"
    r"sk-[A-Za-z0-9]|gh[psoru]_[A-Za-z0-9]|github_pat_|xox[abprs]-|"
    r"diagnosis|symptom|medical|healthkit|billing|entitlement|account)",
    re.IGNORECASE,
)
_PATH_LABEL_RE = re.compile(r"(^/)|(^~[/\\])|(^[A-Za-z]:[\\/])|(\\\\)|file://")


def fingerprint_payload(payload: JsonValue) -> str:
    """Return a deterministic SHA-256 fingerprint for JSON-compatible payload."""

    return f"{_FINGERPRINT_PREFIX}{_sha256_hex(_canonical_json_bytes(payload))}"


def fingerprint_provenance_envelope(
    *,
    surface: str,
    request_fingerprint: str,
    context_fingerprint: str | None,
    source_fingerprints: Sequence[str],
    policy_version: str,
    model_key: str,
    user_tier: str | None,
    transparency_notice_id: str,
    prompt_module_fingerprints: Sequence[str] = (),
) -> str:
    """Fingerprint a non-serving provenance envelope without raw payloads."""

    normalized_source_fingerprints = tuple(
        sorted(validate_fingerprint(fingerprint) for fingerprint in source_fingerprints)
    )
    normalized_prompt_module_fingerprints = tuple(
        sorted(validate_fingerprint(fingerprint) for fingerprint in prompt_module_fingerprints)
    )
    payload: JsonValue = {
        "context_fingerprint": (
            validate_fingerprint(context_fingerprint) if context_fingerprint is not None else None
        ),
        "model_key": _validate_safe_label("model_key", model_key),
        "policy_version": _validate_safe_label("policy_version", policy_version),
        "prompt_module_fingerprints": normalized_prompt_module_fingerprints,
        "request_fingerprint": validate_fingerprint(request_fingerprint),
        "source_fingerprints": normalized_source_fingerprints,
        "surface": _validate_safe_label("surface", surface),
        "transparency_notice_id": _validate_safe_label(
            "transparency_notice_id",
            transparency_notice_id,
        ),
        "user_tier": _validate_optional_safe_label("user_tier", user_tier),
    }
    return fingerprint_payload(payload)


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


def _validate_optional_safe_label(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _validate_safe_label(name, value)


def _validate_safe_label(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _SAFE_LABEL_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    if _UNSAFE_LABEL_RE.search(normalized) or _PATH_LABEL_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized

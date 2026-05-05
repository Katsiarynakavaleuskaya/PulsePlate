"""Unified eval event schema for Evidence Graph Runtime.

RU: Eval events нормализуют артефакты в append-only event plane.
EN: Eval events normalize artifacts into an append-only event plane.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal, TypeAlias, cast

from core.evidence.assets import EvidenceAssetRef
from core.evidence.fingerprints import JsonScalar, JsonValue, fingerprint_payload
from core.evidence.policies import (
    normalize_upstream_ids,
    validate_fingerprint,
    validate_non_empty_token,
)

EvalEventType = Literal[
    "rag_gate_run",
    "rag_gate_report",
    "ragas_report",
    "eval_validity_record",
    "judgment_validity_record",
    "item_metadata",
    "item_statistics",
    "gate_metric",
    "gate_decision",
]

EvalEventRail = Literal["runtime", "advisory", "control_plane", "eval"]

ValidationStatus = Literal["valid", "invalid", "degraded", "deferred"]

ALLOWED_EVAL_EVENT_TYPES: tuple[str, ...] = (
    "rag_gate_run",
    "rag_gate_report",
    "ragas_report",
    "eval_validity_record",
    "judgment_validity_record",
    "item_metadata",
    "item_statistics",
    "gate_metric",
    "gate_decision",
)

ALLOWED_EVAL_EVENT_RAILS: tuple[str, ...] = (
    "runtime",
    "advisory",
    "control_plane",
    "eval",
)

ALLOWED_VALIDATION_STATUSES: tuple[str, ...] = (
    "valid",
    "invalid",
    "degraded",
    "deferred",
)

_FORBIDDEN_SOURCE_ROOTS: tuple[str, ...] = (
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "worktrees",
)

_FORBIDDEN_SOURCE_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("artifacts", "agent_runs"),
    ("artifacts", "orchestration"),
    ("artifacts", "security_lab"),
)

_FORBIDDEN_METADATA_KEY_FRAGMENTS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "access_token",
    "health_payload",
    "medical_record",
    "password",
    "prompt_text",
    "raw_prompt",
    "raw_response",
    "refresh_token",
    "response_text",
    "secret",
    "user_health",
    "user_payload",
)

_FORBIDDEN_METADATA_STRING_FRAGMENTS: tuple[str, ...] = (
    "api_key=",
    "bearer ",
    "password=",
    "private key",
    "sk-",
)


@dataclass(frozen=True)
class EvalEventProducer:
    """Producer identity for a normalized eval event."""

    name: str
    version: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-compatible producer payload."""

        return {
            "name": self.name,
            "version": self.version,
        }


@dataclass(frozen=True)
class _FrozenJsonArray:
    items: tuple["FrozenJsonValue", ...]


@dataclass(frozen=True)
class _FrozenJsonObject:
    items: tuple[tuple[str, "FrozenJsonValue"], ...]


FrozenJsonValue: TypeAlias = JsonScalar | _FrozenJsonArray | _FrozenJsonObject


@dataclass(frozen=True)
class EvidenceEvalEvent:
    """Immutable normalized event for eval/evidence artifacts."""

    event_id: str
    event_type: EvalEventType
    rail: EvalEventRail
    source_artifact: str
    asset_refs: tuple[EvidenceAssetRef, ...]
    upstream_ids: tuple[str, ...]
    fingerprint: str
    idempotency_key: str
    policy_version: str
    producer: EvalEventProducer
    produced_at: str
    validation_status: ValidationStatus
    _metadata: _FrozenJsonObject = field(default_factory=lambda: _FrozenJsonObject(()))

    @property
    def metadata(self) -> dict[str, JsonValue]:
        """Return a defensive JSON-compatible metadata copy."""

        return cast(dict[str, JsonValue], _thaw_frozen_json(self._metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a deterministic JSON-compatible event payload."""

        return {
            "asset_refs": [_asset_ref_to_dict(ref) for ref in self.asset_refs],
            "event_id": self.event_id,
            "event_type": self.event_type,
            "fingerprint": self.fingerprint,
            "idempotency_key": self.idempotency_key,
            "metadata": self.metadata,
            "policy_version": self.policy_version,
            "produced_at": self.produced_at,
            "producer": self.producer.to_dict(),
            "rail": self.rail,
            "source_artifact": self.source_artifact,
            "upstream_ids": list(self.upstream_ids),
            "validation_status": self.validation_status,
        }

    def to_json(self) -> str:
        """Serialize the event with stable key ordering."""

        return json.dumps(
            self.to_dict(),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def create_eval_event(
    *,
    event_type: EvalEventType,
    rail: EvalEventRail,
    source_artifact: str,
    asset_refs: Iterable[EvidenceAssetRef] = (),
    upstream_ids: Iterable[str] = (),
    fingerprint: str,
    idempotency_key: str,
    policy_version: str,
    producer_name: str,
    producer_version: str,
    produced_at: str,
    validation_status: ValidationStatus,
    metadata: Mapping[str, JsonValue] | None = None,
) -> EvidenceEvalEvent:
    """Create an immutable eval event or fail closed."""

    normalized_event_type = validate_eval_event_type(event_type)
    normalized_rail = validate_eval_event_rail(rail)
    normalized_source_artifact = validate_source_artifact(source_artifact)
    normalized_asset_refs = tuple(asset_refs)
    _validate_asset_refs_for_event_rail(
        rail=normalized_rail,
        asset_refs=normalized_asset_refs,
    )
    normalized_upstream_ids = normalize_upstream_ids(tuple(upstream_ids))
    normalized_fingerprint = validate_fingerprint(fingerprint)
    normalized_idempotency_key = validate_idempotency_key(idempotency_key)
    normalized_policy_version = validate_non_empty_token("policy_version", policy_version)
    producer = create_eval_event_producer(
        name=producer_name,
        version=producer_version,
    )
    normalized_produced_at = validate_produced_at(produced_at)
    normalized_validation_status = validate_validation_status(validation_status)
    frozen_metadata = _freeze_metadata(metadata or {})
    event_id = build_eval_event_id(
        event_type=normalized_event_type,
        rail=normalized_rail,
        source_artifact=normalized_source_artifact,
        asset_refs=normalized_asset_refs,
        upstream_ids=normalized_upstream_ids,
        fingerprint=normalized_fingerprint,
        idempotency_key=normalized_idempotency_key,
        policy_version=normalized_policy_version,
        producer=producer,
        validation_status=normalized_validation_status,
    )
    return EvidenceEvalEvent(
        event_id=event_id,
        event_type=normalized_event_type,
        rail=normalized_rail,
        source_artifact=normalized_source_artifact,
        asset_refs=normalized_asset_refs,
        upstream_ids=normalized_upstream_ids,
        fingerprint=normalized_fingerprint,
        idempotency_key=normalized_idempotency_key,
        policy_version=normalized_policy_version,
        producer=producer,
        produced_at=normalized_produced_at,
        validation_status=normalized_validation_status,
        _metadata=frozen_metadata,
    )


def create_eval_event_producer(*, name: str, version: str) -> EvalEventProducer:
    """Create a normalized producer identity."""

    return EvalEventProducer(
        name=validate_non_empty_token("producer_name", name),
        version=validate_non_empty_token("producer_version", version),
    )


def build_eval_event_id(
    *,
    event_type: EvalEventType,
    rail: EvalEventRail,
    source_artifact: str,
    asset_refs: tuple[EvidenceAssetRef, ...],
    upstream_ids: tuple[str, ...],
    fingerprint: str,
    idempotency_key: str,
    policy_version: str,
    producer: EvalEventProducer,
    validation_status: ValidationStatus,
) -> str:
    """Build a deterministic eval event id from canonical event scope."""

    identity_payload: JsonValue = {
        "asset_ref_ids": [ref.asset_id for ref in asset_refs],
        "event_type": event_type,
        "fingerprint": fingerprint,
        "idempotency_key": idempotency_key,
        "policy_version": policy_version,
        "producer": producer.to_dict(),
        "rail": rail,
        "source_artifact": source_artifact,
        "upstream_ids": list(upstream_ids),
        "validation_status": validation_status,
    }
    digest = fingerprint_payload(identity_payload).removeprefix("sha256:")
    return f"eval-event:{digest[:24]}"


def validate_eval_event_type(event_type: EvalEventType) -> EvalEventType:
    """Return a supported event type or fail closed."""

    if event_type not in ALLOWED_EVAL_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type!r}")
    return event_type


def validate_eval_event_rail(rail: EvalEventRail) -> EvalEventRail:
    """Return a supported event rail or fail closed."""

    if rail not in ALLOWED_EVAL_EVENT_RAILS:
        raise ValueError(f"unsupported rail: {rail!r}")
    return rail


def validate_validation_status(status: ValidationStatus) -> ValidationStatus:
    """Return a supported validation status or fail closed."""

    if status not in ALLOWED_VALIDATION_STATUSES:
        raise ValueError(f"unsupported validation_status: {status!r}")
    return status


def validate_idempotency_key(idempotency_key: str) -> str:
    """Return a normalized non-empty idempotency key."""

    normalized = idempotency_key.strip()
    if not normalized:
        raise ValueError("idempotency_key must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError("idempotency_key must not contain whitespace")
    return normalized


def validate_source_artifact(source_artifact: str) -> str:
    """Return a normalized safe source artifact path."""

    normalized = source_artifact.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("source_artifact must be non-empty")
    if _has_windows_drive_prefix(normalized):
        raise ValueError("source_artifact must be repo-relative")
    if normalized.startswith("/") or normalized.startswith("~"):
        raise ValueError("source_artifact must be repo-relative")
    path = PurePosixPath(normalized)
    if path.is_absolute():
        raise ValueError("source_artifact must be repo-relative")
    parts = path.parts
    if not parts:
        raise ValueError("source_artifact must be non-empty")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("source_artifact must not contain traversal")
    if parts[0] in _FORBIDDEN_SOURCE_ROOTS:
        raise ValueError(f"source_artifact root is not allowed: {parts[0]!r}")
    for forbidden_prefix in _FORBIDDEN_SOURCE_PREFIXES:
        if parts[: len(forbidden_prefix)] == forbidden_prefix:
            joined = "/".join(forbidden_prefix)
            raise ValueError(f"source_artifact path is not allowed: {joined!r}")
    return path.as_posix()


def _has_windows_drive_prefix(path: str) -> bool:
    """Return True for Windows drive-qualified paths such as C:/x or C:x."""

    first_segment = path.split("/", maxsplit=1)[0]
    return len(first_segment) >= 2 and first_segment[0].isalpha() and first_segment[1] == ":"


def validate_produced_at(produced_at: str) -> str:
    """Validate an explicit ISO-8601 timestamp without generating one."""

    normalized = produced_at.strip()
    if not normalized:
        raise ValueError("produced_at must be non-empty")
    parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("produced_at must include timezone")
    return normalized


def _validate_asset_refs_for_event_rail(
    *,
    rail: EvalEventRail,
    asset_refs: tuple[EvidenceAssetRef, ...],
) -> None:
    """Preserve rail separation for non-eval event rails."""

    if rail == "eval":
        return
    mismatched = tuple(ref.asset_id for ref in asset_refs if ref.rail != rail)
    if mismatched:
        joined = ", ".join(mismatched)
        raise ValueError(f"cross-rail asset_refs are not allowed: {joined}")


def _freeze_metadata(metadata: Mapping[str, JsonValue]) -> _FrozenJsonObject:
    """Validate and freeze metadata into caller-independent structures."""

    return cast(_FrozenJsonObject, _freeze_json_value(metadata, path=()))


def _freeze_json_value(
    value: JsonValue,
    *,
    path: tuple[str, ...],
) -> FrozenJsonValue:
    """Freeze JSON-compatible values and scan for forbidden raw payloads."""

    if isinstance(value, Mapping):
        items: list[tuple[str, FrozenJsonValue]] = []
        normalized_items: list[tuple[str, JsonValue]] = []
        seen_keys: set[str] = set()
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
            normalized_key = key.strip()
            if not normalized_key:
                raise ValueError("metadata keys must be non-empty")
            if normalized_key in seen_keys:
                raise ValueError(f"metadata key collides after normalization: {normalized_key!r}")
            seen_keys.add(normalized_key)
            _validate_metadata_key(normalized_key)
            normalized_items.append((normalized_key, item))
        for normalized_key, item in sorted(normalized_items, key=lambda pair: pair[0]):
            items.append(
                (
                    normalized_key,
                    _freeze_json_value(item, path=path + (normalized_key,)),
                )
            )
        return _FrozenJsonObject(tuple(items))
    if isinstance(value, Sequence) and not isinstance(value, str):
        return _FrozenJsonArray(
            tuple(
                _freeze_json_value(item, path=path + (str(index),))
                for index, item in enumerate(value)
            )
        )
    if isinstance(value, str):
        _validate_metadata_string(value)
        return value
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            location = ".".join(path) or "<root>"
            raise ValueError(f"metadata value at {location} must be finite")
        return value
    raise ValueError(f"metadata value at {'.'.join(path) or '<root>'} must be JSON-compatible")


def _validate_metadata_key(key: str) -> None:
    """Fail closed on raw secret/user-health payload keys."""

    lowered = key.lower()
    if any(fragment in lowered for fragment in _FORBIDDEN_METADATA_KEY_FRAGMENTS):
        raise ValueError(f"metadata key is not allowed: {key!r}")


def _validate_metadata_string(value: str) -> None:
    """Fail closed on obvious raw secret payload strings."""

    lowered = value.lower()
    if any(fragment in lowered for fragment in _FORBIDDEN_METADATA_STRING_FRAGMENTS):
        raise ValueError("metadata string appears to contain raw secret material")


def _thaw_frozen_json(value: FrozenJsonValue) -> JsonValue:
    """Return a defensive JSON-compatible value from frozen metadata."""

    if isinstance(value, _FrozenJsonObject):
        return {key: _thaw_frozen_json(item) for key, item in value.items}
    if isinstance(value, _FrozenJsonArray):
        return [_thaw_frozen_json(item) for item in value.items]
    return value


def _asset_ref_to_dict(ref: EvidenceAssetRef) -> dict[str, JsonValue]:
    """Serialize an E1 evidence asset ref without exposing raw payloads."""

    return {
        "asset_id": ref.asset_id,
        "asset_type": ref.asset_type,
        "fingerprint": ref.fingerprint,
        "idempotency_key": ref.idempotency_key,
        "policy_version": ref.policy_version,
        "rail": ref.rail,
        "upstream_ids": list(ref.upstream_ids),
        "version": ref.version,
    }

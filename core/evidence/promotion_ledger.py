"""Promotion ledger contracts for Evidence Graph Runtime.

RU: E3 ledger фиксирует promotion decisions без runtime writes.
EN: E3 ledger records promotion decisions without runtime writes.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias, cast

from core.evidence.events import (
    EvidenceEvalEvent,
    EvalEventProducer,
    EvalEventType,
    ValidationStatus,
    create_eval_event_producer,
    validate_eval_event_type,
    validate_idempotency_key,
    validate_produced_at,
    validate_validation_status,
)
from core.evidence.fingerprints import JsonScalar, JsonValue, fingerprint_payload
from core.evidence.policies import (
    normalize_upstream_ids,
    validate_fingerprint,
    validate_non_empty_token,
)

PromotionDecision = Literal["promote", "reject", "defer", "supersede"]

ALLOWED_PROMOTION_DECISIONS: tuple[str, ...] = (
    "promote",
    "reject",
    "defer",
    "supersede",
)

_PROMOTING_DECISIONS: tuple[str, ...] = ("promote", "supersede")

_FORBIDDEN_METADATA_KEY_FRAGMENTS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "access_token",
    "health_payload",
    "medical_record",
    "password",
    "prompt",
    "raw_prompt",
    "raw_response",
    "refresh_token",
    "response",
    "secret",
    "user_health",
    "user_payload",
)

_FORBIDDEN_METADATA_STRING_FRAGMENTS: tuple[str, ...] = (
    "api_key=",
    "bearer ",
    "health payload",
    "medical record",
    "password=",
    "private key",
    "prompt:",
    "raw prompt",
    "raw response",
    "response:",
    "sk-",
    "user health",
    "user payload",
)

_PATH_LIKE_PREFIXES: tuple[str, ...] = (
    "artifacts/",
    "core/",
    "data/",
    "docs/",
    "evals/",
    "scripts/",
    "tests/",
)

_PATH_LIKE_SUFFIXES: tuple[str, ...] = (
    ".csv",
    ".ipynb",
    ".json",
    ".jsonl",
    ".md",
    ".parquet",
    ".txt",
)


@dataclass(frozen=True)
class _FrozenJsonArray:
    items: tuple["FrozenJsonValue", ...]


@dataclass(frozen=True)
class _FrozenJsonObject:
    items: tuple[tuple[str, "FrozenJsonValue"], ...]


FrozenJsonValue: TypeAlias = JsonScalar | _FrozenJsonArray | _FrozenJsonObject


@dataclass(frozen=True, init=False)
class PromotionLedgerEntry:
    """Immutable append-only ledger entry for one promotion decision."""

    ledger_entry_id: str
    promotion_id: str
    source_event_id: str
    source_event_type: EvalEventType
    source_event_fingerprint: str
    decision: PromotionDecision
    idempotency_key: str
    policy_version: str
    producer: EvalEventProducer
    produced_at: str
    upstream_ids: tuple[str, ...]
    supersedes: tuple[str, ...]
    validation_status: ValidationStatus
    reason_codes: tuple[str, ...]
    _metadata: _FrozenJsonObject

    def __init__(
        self,
        *,
        promotion_id: str,
        source_event_id: str,
        source_event_type: EvalEventType,
        source_event_fingerprint: str,
        decision: PromotionDecision,
        idempotency_key: str,
        policy_version: str,
        producer: EvalEventProducer,
        produced_at: str,
        upstream_ids: Iterable[str] = (),
        supersedes: Iterable[str] = (),
        validation_status: ValidationStatus,
        reason_codes: Iterable[str] = (),
        metadata: Mapping[str, JsonValue] | None = None,
        ledger_entry_id: str | None = None,
    ) -> None:
        """Create and validate a deterministic ledger entry."""

        normalized_promotion_id = validate_non_empty_token(
            "promotion_id",
            promotion_id,
        )
        normalized_source_event_id = _validate_identity_token(
            "source_event_id",
            source_event_id,
        )
        normalized_source_event_type = validate_eval_event_type(source_event_type)
        normalized_source_fingerprint = validate_fingerprint(source_event_fingerprint)
        normalized_decision = validate_promotion_decision(decision)
        normalized_idempotency_key = validate_idempotency_key(idempotency_key)
        normalized_policy_version = validate_non_empty_token(
            "policy_version",
            policy_version,
        )
        normalized_producer = create_eval_event_producer(
            name=producer.name,
            version=producer.version,
        )
        normalized_produced_at = validate_produced_at(produced_at)
        normalized_upstream_ids = normalize_upstream_ids(tuple(upstream_ids))
        normalized_supersedes = _normalize_unique_identity_tokens(
            "supersedes",
            tuple(supersedes),
        )
        normalized_validation_status = validate_validation_status(validation_status)
        normalized_reason_codes = _normalize_reason_codes(tuple(reason_codes))
        frozen_metadata = _freeze_metadata(metadata or {})

        if normalized_decision in _PROMOTING_DECISIONS and normalized_validation_status != "valid":
            raise ValueError("promoting decisions require valid validation_status")
        if normalized_decision == "supersede" and not normalized_supersedes:
            raise ValueError("supersede decision requires supersedes entries")

        built_entry_id = build_ledger_entry_id(
            promotion_id=normalized_promotion_id,
            source_event_id=normalized_source_event_id,
            source_event_type=normalized_source_event_type,
            source_event_fingerprint=normalized_source_fingerprint,
            decision=normalized_decision,
            idempotency_key=normalized_idempotency_key,
            policy_version=normalized_policy_version,
            producer=normalized_producer,
            upstream_ids=normalized_upstream_ids,
            supersedes=normalized_supersedes,
            validation_status=normalized_validation_status,
            reason_codes=normalized_reason_codes,
            metadata=cast(dict[str, JsonValue], _thaw_frozen_json(frozen_metadata)),
        )
        normalized_entry_id = (
            built_entry_id
            if ledger_entry_id is None
            else _validate_ledger_entry_id(ledger_entry_id)
        )
        if normalized_entry_id in normalized_supersedes:
            raise ValueError("ledger entry cannot supersede itself")
        if normalized_entry_id != built_entry_id:
            raise ValueError("ledger_entry_id must match deterministic identity")

        object.__setattr__(self, "ledger_entry_id", normalized_entry_id)
        object.__setattr__(self, "promotion_id", normalized_promotion_id)
        object.__setattr__(self, "source_event_id", normalized_source_event_id)
        object.__setattr__(
            self,
            "source_event_type",
            normalized_source_event_type,
        )
        object.__setattr__(
            self,
            "source_event_fingerprint",
            normalized_source_fingerprint,
        )
        object.__setattr__(self, "decision", normalized_decision)
        object.__setattr__(self, "idempotency_key", normalized_idempotency_key)
        object.__setattr__(self, "policy_version", normalized_policy_version)
        object.__setattr__(self, "producer", normalized_producer)
        object.__setattr__(self, "produced_at", normalized_produced_at)
        object.__setattr__(self, "upstream_ids", normalized_upstream_ids)
        object.__setattr__(self, "supersedes", normalized_supersedes)
        object.__setattr__(self, "validation_status", normalized_validation_status)
        object.__setattr__(self, "reason_codes", normalized_reason_codes)
        object.__setattr__(self, "_metadata", frozen_metadata)

    @property
    def metadata(self) -> dict[str, JsonValue]:
        """Return a defensive JSON-compatible metadata copy."""

        return cast(dict[str, JsonValue], _thaw_frozen_json(self._metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a deterministic JSON-compatible ledger payload."""

        return {
            "decision": self.decision,
            "idempotency_key": self.idempotency_key,
            "ledger_entry_id": self.ledger_entry_id,
            "metadata": self.metadata,
            "policy_version": self.policy_version,
            "produced_at": self.produced_at,
            "producer": self.producer.to_dict(),
            "promotion_id": self.promotion_id,
            "reason_codes": list(self.reason_codes),
            "source_event_fingerprint": self.source_event_fingerprint,
            "source_event_id": self.source_event_id,
            "source_event_type": self.source_event_type,
            "supersedes": list(self.supersedes),
            "upstream_ids": list(self.upstream_ids),
            "validation_status": self.validation_status,
        }

    def to_json(self) -> str:
        """Serialize the entry with stable key ordering."""

        return json.dumps(
            self.to_dict(),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def create_promotion_ledger_entry(
    *,
    source_event: EvidenceEvalEvent,
    promotion_id: str,
    decision: PromotionDecision,
    idempotency_key: str,
    producer: EvalEventProducer,
    produced_at: str,
    policy_version: str | None = None,
    upstream_ids: Iterable[str] = (),
    supersedes: Iterable[str] = (),
    validation_status: ValidationStatus | None = None,
    reason_codes: Iterable[str] = (),
    metadata: Mapping[str, JsonValue] | None = None,
    ledger_entry_id: str | None = None,
) -> PromotionLedgerEntry:
    """Create a ledger entry from an E2 eval event or fail closed."""

    if not isinstance(source_event, EvidenceEvalEvent):
        raise ValueError("source_event must be an EvidenceEvalEvent")
    source_event_id = _validate_identity_token(
        "source_event_id",
        source_event.event_id,
    )
    source_event_fingerprint = validate_fingerprint(source_event.fingerprint)
    source_validation_status = validate_validation_status(
        source_event.validation_status,
    )
    normalized_decision = validate_promotion_decision(decision)
    if normalized_decision in _PROMOTING_DECISIONS and source_validation_status != "valid":
        raise ValueError("promoting decisions require a valid source_event")
    if source_event.rail != "eval":
        raise ValueError("source_event rail must be eval")
    normalized_upstream_ids = normalize_upstream_ids(
        (
            source_event.event_id,
            *source_event.upstream_ids,
            *tuple(upstream_ids),
        )
    )
    return PromotionLedgerEntry(
        promotion_id=promotion_id,
        source_event_id=source_event_id,
        source_event_type=source_event.event_type,
        source_event_fingerprint=source_event_fingerprint,
        decision=normalized_decision,
        idempotency_key=idempotency_key,
        policy_version=policy_version or source_event.policy_version,
        producer=producer,
        produced_at=produced_at,
        upstream_ids=normalized_upstream_ids,
        supersedes=supersedes,
        validation_status=validation_status or source_validation_status,
        reason_codes=reason_codes,
        metadata=metadata,
        ledger_entry_id=ledger_entry_id,
    )


def build_ledger_entry_id(
    *,
    promotion_id: str,
    source_event_id: str,
    source_event_type: EvalEventType,
    source_event_fingerprint: str,
    decision: PromotionDecision,
    idempotency_key: str,
    policy_version: str,
    producer: EvalEventProducer,
    upstream_ids: tuple[str, ...],
    supersedes: tuple[str, ...],
    validation_status: ValidationStatus,
    reason_codes: tuple[str, ...],
    metadata: Mapping[str, JsonValue],
) -> str:
    """Build a deterministic ledger entry id from canonical identity fields."""

    identity_payload: JsonValue = {
        "decision": decision,
        "idempotency_key": idempotency_key,
        "metadata": metadata,
        "policy_version": policy_version,
        "producer": producer.to_dict(),
        "promotion_id": promotion_id,
        "reason_codes": list(reason_codes),
        "source_event_fingerprint": source_event_fingerprint,
        "source_event_id": source_event_id,
        "source_event_type": source_event_type,
        "supersedes": list(supersedes),
        "upstream_ids": list(upstream_ids),
        "validation_status": validation_status,
    }
    digest = fingerprint_payload(identity_payload).removeprefix("sha256:")
    return f"promotion-ledger:{digest[:24]}"


def validate_promotion_decision(decision: PromotionDecision) -> PromotionDecision:
    """Return a supported promotion decision or fail closed."""

    if decision not in ALLOWED_PROMOTION_DECISIONS:
        raise ValueError(f"unsupported decision: {decision!r}")
    return decision


def _validate_identity_token(name: str, value: str) -> str:
    """Validate IDs that may contain separators but no whitespace."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    return normalized


def _validate_ledger_entry_id(ledger_entry_id: str) -> str:
    """Return a deterministic ledger id token."""

    normalized = _validate_identity_token("ledger_entry_id", ledger_entry_id)
    if not normalized.startswith("promotion-ledger:"):
        raise ValueError("ledger_entry_id must start with 'promotion-ledger:'")
    return normalized


def _normalize_unique_identity_tokens(
    name: str,
    values: tuple[str, ...],
) -> tuple[str, ...]:
    """Normalize identity tokens while rejecting duplicate collisions."""

    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _validate_identity_token(name, value)
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate entries")
        seen.add(normalized)
        normalized_values.append(normalized)
    return tuple(sorted(normalized_values))


def _normalize_reason_codes(reason_codes: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize reason codes and reject collisions after normalization."""

    normalized_codes: list[str] = []
    seen: set[str] = set()
    for reason_code in reason_codes:
        normalized = validate_non_empty_token(
            "reason_code",
            reason_code.strip().lower(),
        )
        if normalized in seen:
            raise ValueError("reason_codes collide after normalization")
        seen.add(normalized)
        normalized_codes.append(normalized)
    return tuple(sorted(normalized_codes))


def _freeze_metadata(metadata: Mapping[str, JsonValue]) -> _FrozenJsonObject:
    """Validate and freeze metadata into caller-independent structures."""

    return cast(_FrozenJsonObject, _freeze_json_value(metadata, path=()))


def _freeze_json_value(
    value: JsonValue,
    *,
    path: tuple[str, ...],
) -> FrozenJsonValue:
    """Freeze JSON-compatible metadata and scan unsafe raw payloads."""

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
    if isinstance(value, bytes | bytearray):
        raise ValueError(f"metadata value at {'.'.join(path) or '<root>'} must be JSON-compatible")
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
    """Fail closed on raw prompt/response/secret/user-health metadata keys."""

    lowered = key.lower()
    if any(fragment in lowered for fragment in _FORBIDDEN_METADATA_KEY_FRAGMENTS):
        raise ValueError(f"metadata key is not allowed: {key!r}")


def _validate_metadata_string(value: str) -> None:
    """Fail closed on obvious raw secret or path-like payload strings."""

    normalized = value.strip()
    lowered = normalized.lower().replace("\\", "/")
    if any(fragment in lowered for fragment in _FORBIDDEN_METADATA_STRING_FRAGMENTS):
        raise ValueError("metadata string appears to contain raw secret material")
    if (
        lowered.startswith("/")
        or lowered.startswith("~")
        or "../" in lowered
        or _has_windows_drive_prefix(lowered)
        or (lowered.startswith(_PATH_LIKE_PREFIXES) and lowered.endswith(_PATH_LIKE_SUFFIXES))
    ):
        raise ValueError("metadata string appears to contain path-like material")


def _has_windows_drive_prefix(value: str) -> bool:
    """Return True for Windows drive-qualified strings such as C:/x or C:x."""

    first_segment = value.split("/", maxsplit=1)[0]
    return len(first_segment) >= 2 and first_segment[0].isalpha() and first_segment[1] == ":"


def _thaw_frozen_json(value: FrozenJsonValue) -> JsonValue:
    """Return a defensive JSON-compatible value from frozen metadata."""

    if isinstance(value, _FrozenJsonObject):
        return {key: _thaw_frozen_json(item) for key, item in value.items}
    if isinstance(value, _FrozenJsonArray):
        return [_thaw_frozen_json(item) for item in value.items]
    return value

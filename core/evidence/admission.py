"""Active metadata admission contracts for Evidence Graph Runtime.

RU: E4 admission принимает deterministic gate-решения без runtime side effects.
EN: E4 admission makes deterministic gate decisions without runtime side effects.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias, cast

from core.evidence.events import (
    ALLOWED_EVAL_EVENT_TYPES,
    EvidenceEvalEvent,
    EvalEventType,
    ValidationStatus,
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
from core.evidence.promotion_ledger import (
    ALLOWED_PROMOTION_DECISIONS,
    PromotionDecision,
    PromotionLedgerEntry,
    validate_promotion_decision,
)

AdmissionAction = Literal["execute", "promote", "serve"]
AdmissionTargetType = Literal[
    "evidence_asset",
    "eval_event",
    "promotion_ledger_entry",
    "replay_summary",
]

ALLOWED_ADMISSION_ACTIONS: tuple[str, ...] = ("execute", "promote", "serve")
ALLOWED_ADMISSION_TARGET_TYPES: tuple[str, ...] = (
    "evidence_asset",
    "eval_event",
    "promotion_ledger_entry",
    "replay_summary",
)

DEFAULT_ALLOWED_VALIDATION_STATUSES: tuple[ValidationStatus, ...] = ("valid",)
DEFAULT_ALLOWED_EVENT_TYPES: tuple[EvalEventType, ...] = cast(
    tuple[EvalEventType, ...],
    ALLOWED_EVAL_EVENT_TYPES,
)
DEFAULT_ALLOWED_DECISIONS: tuple[PromotionDecision, ...] = ("promote", "supersede")

_PROMOTE_ACTION: AdmissionAction = "promote"
_SERVE_ACTION: AdmissionAction = "serve"
_EXECUTE_ACTION: AdmissionAction = "execute"

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

_CURRENT_DIRECTORY_PATH_VALUES: tuple[str, ...] = (".", "./", "./.")
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


@dataclass(frozen=True)
class AdmissionPolicy:
    """Deterministic metadata admission policy thresholds."""

    policy_version: str
    min_verification_rate: float = 0.9
    min_coverage_rate: float = 0.8
    max_fallback_rate: float = 0.1
    allow_degraded: bool = False
    allowed_validation_statuses: tuple[ValidationStatus, ...] = DEFAULT_ALLOWED_VALIDATION_STATUSES
    stale_after_seconds: int = 30 * 24 * 60 * 60
    allowed_event_types: tuple[EvalEventType, ...] = DEFAULT_ALLOWED_EVENT_TYPES
    allowed_decisions: tuple[PromotionDecision, ...] = DEFAULT_ALLOWED_DECISIONS

    def __post_init__(self) -> None:
        """Normalize policy fields without mutating caller-owned structures."""

        object.__setattr__(
            self,
            "policy_version",
            validate_non_empty_token("policy_version", self.policy_version),
        )
        object.__setattr__(
            self,
            "min_verification_rate",
            _validate_metric("min_verification_rate", self.min_verification_rate),
        )
        object.__setattr__(
            self,
            "min_coverage_rate",
            _validate_metric("min_coverage_rate", self.min_coverage_rate),
        )
        object.__setattr__(
            self,
            "max_fallback_rate",
            _validate_metric("max_fallback_rate", self.max_fallback_rate),
        )
        if self.stale_after_seconds < 0:
            raise ValueError("stale_after_seconds must be non-negative")
        object.__setattr__(
            self,
            "allowed_validation_statuses",
            tuple(
                sorted(
                    {
                        validate_validation_status(status)
                        for status in self.allowed_validation_statuses
                    }
                )
            ),
        )
        object.__setattr__(
            self,
            "allowed_event_types",
            tuple(
                sorted(
                    {
                        validate_eval_event_type(event_type)
                        for event_type in self.allowed_event_types
                    }
                )
            ),
        )
        object.__setattr__(
            self,
            "allowed_decisions",
            tuple(
                sorted(
                    {validate_promotion_decision(decision) for decision in self.allowed_decisions}
                )
            ),
        )


@dataclass(frozen=True, init=False)
class AdmissionInput:
    """Normalized admission target metadata."""

    target_id: str
    target_type: AdmissionTargetType
    fingerprint: str
    idempotency_key: str
    policy_version: str
    produced_at: str
    validation_status: ValidationStatus
    coverage_rate: float
    verification_rate: float
    fallback_rate: float
    degraded_reason: str | None
    upstream_ids: tuple[str, ...]
    source_event_id: str | None
    promotion_id: str | None
    event_type: EvalEventType | None
    promotion_decision: PromotionDecision | None
    _metadata: _FrozenJsonObject

    def __init__(
        self,
        *,
        target_id: str,
        target_type: AdmissionTargetType,
        fingerprint: str,
        idempotency_key: str,
        policy_version: str,
        produced_at: str,
        validation_status: ValidationStatus,
        coverage_rate: float,
        verification_rate: float,
        fallback_rate: float,
        degraded_reason: str | None = None,
        upstream_ids: Iterable[str] = (),
        source_event_id: str | None = None,
        promotion_id: str | None = None,
        event_type: EvalEventType | None = None,
        promotion_decision: PromotionDecision | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> None:
        """Create validated metadata admission input."""

        object.__setattr__(
            self,
            "target_id",
            _validate_identity_token("target_id", target_id),
        )
        object.__setattr__(
            self,
            "target_type",
            validate_admission_target_type(target_type),
        )
        object.__setattr__(self, "fingerprint", validate_fingerprint(fingerprint))
        object.__setattr__(
            self,
            "idempotency_key",
            validate_idempotency_key(idempotency_key),
        )
        object.__setattr__(
            self,
            "policy_version",
            validate_non_empty_token("policy_version", policy_version),
        )
        object.__setattr__(self, "produced_at", validate_produced_at(produced_at))
        object.__setattr__(
            self,
            "validation_status",
            validate_validation_status(validation_status),
        )
        object.__setattr__(
            self,
            "coverage_rate",
            _validate_metric("coverage_rate", coverage_rate),
        )
        object.__setattr__(
            self,
            "verification_rate",
            _validate_metric("verification_rate", verification_rate),
        )
        object.__setattr__(
            self,
            "fallback_rate",
            _validate_metric("fallback_rate", fallback_rate),
        )
        object.__setattr__(
            self,
            "degraded_reason",
            (
                None
                if degraded_reason is None
                else _validate_metadata_safe_text("degraded_reason", degraded_reason)
            ),
        )
        object.__setattr__(
            self,
            "upstream_ids",
            normalize_upstream_ids(tuple(upstream_ids)),
        )
        object.__setattr__(
            self,
            "source_event_id",
            (
                None
                if source_event_id is None
                else _validate_identity_token("source_event_id", source_event_id)
            ),
        )
        object.__setattr__(
            self,
            "promotion_id",
            (
                None
                if promotion_id is None
                else _validate_identity_token("promotion_id", promotion_id)
            ),
        )
        object.__setattr__(
            self,
            "event_type",
            None if event_type is None else validate_eval_event_type(event_type),
        )
        object.__setattr__(
            self,
            "promotion_decision",
            None if promotion_decision is None else validate_promotion_decision(promotion_decision),
        )
        object.__setattr__(self, "_metadata", _freeze_metadata(metadata or {}))

    @property
    def metadata(self) -> dict[str, JsonValue]:
        """Return a defensive JSON-compatible metadata copy."""

        return cast(dict[str, JsonValue], _thaw_frozen_json(self._metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a deterministic JSON-compatible admission input payload."""

        return {
            "coverage_rate": self.coverage_rate,
            "degraded_reason": self.degraded_reason,
            "event_type": self.event_type,
            "fallback_rate": self.fallback_rate,
            "fingerprint": self.fingerprint,
            "idempotency_key": self.idempotency_key,
            "metadata": self.metadata,
            "policy_version": self.policy_version,
            "produced_at": self.produced_at,
            "promotion_decision": self.promotion_decision,
            "promotion_id": self.promotion_id,
            "source_event_id": self.source_event_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "upstream_ids": list(self.upstream_ids),
            "validation_status": self.validation_status,
            "verification_rate": self.verification_rate,
        }


@dataclass(frozen=True)
class AdmissionDecision:
    """Deterministic admission gate result."""

    decision_id: str
    action: AdmissionAction
    allowed: bool
    policy_version: str
    target_id: str
    target_type: AdmissionTargetType
    fingerprint: str
    idempotency_key: str
    produced_at: str
    reason_codes: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    _metadata: _FrozenJsonObject

    @property
    def metadata(self) -> dict[str, JsonValue]:
        """Return a defensive JSON-compatible metadata copy."""

        return cast(dict[str, JsonValue], _thaw_frozen_json(self._metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a deterministic JSON-compatible decision payload."""

        return {
            "action": self.action,
            "allowed": self.allowed,
            "blocking_reasons": list(self.blocking_reasons),
            "decision_id": self.decision_id,
            "fingerprint": self.fingerprint,
            "idempotency_key": self.idempotency_key,
            "metadata": self.metadata,
            "policy_version": self.policy_version,
            "produced_at": self.produced_at,
            "reason_codes": list(self.reason_codes),
            "target_id": self.target_id,
            "target_type": self.target_type,
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        """Serialize the decision with stable key ordering."""

        return json.dumps(
            self.to_dict(),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def decide_allow_execute(
    *,
    admission_input: AdmissionInput,
    policy: AdmissionPolicy,
    now: str,
) -> AdmissionDecision:
    """Return an execute admission decision."""

    return decide_admission(
        action="execute",
        admission_input=admission_input,
        policy=policy,
        now=now,
    )


def decide_allow_promote(
    *,
    admission_input: AdmissionInput,
    policy: AdmissionPolicy,
    now: str,
) -> AdmissionDecision:
    """Return a promote admission decision."""

    return decide_admission(
        action="promote",
        admission_input=admission_input,
        policy=policy,
        now=now,
    )


def decide_allow_serve(
    *,
    admission_input: AdmissionInput,
    policy: AdmissionPolicy,
    now: str,
) -> AdmissionDecision:
    """Return a serve admission decision."""

    return decide_admission(
        action="serve",
        admission_input=admission_input,
        policy=policy,
        now=now,
    )


def decide_admission(
    *,
    action: AdmissionAction,
    admission_input: AdmissionInput,
    policy: AdmissionPolicy,
    now: str,
) -> AdmissionDecision:
    """Make a deterministic admission decision without side effects."""

    normalized_action = validate_admission_action(action)
    if admission_input.policy_version != policy.policy_version:
        raise ValueError("admission input policy_version must match policy")
    now_timestamp = validate_produced_at(now)

    reason_codes: list[str] = []
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    if admission_input.validation_status not in policy.allowed_validation_statuses:
        blocking_reasons.append("validation_status_not_allowed")

    stale_state = _staleness_state(
        produced_at=admission_input.produced_at,
        now=now_timestamp,
        stale_after_seconds=policy.stale_after_seconds,
    )
    if stale_state is not None:
        blocking_reasons.append(stale_state)

    if (
        admission_input.event_type is not None
        and admission_input.event_type not in policy.allowed_event_types
    ):
        blocking_reasons.append("event_type_not_allowed")

    if (
        admission_input.promotion_decision is not None
        and admission_input.promotion_decision not in policy.allowed_decisions
    ):
        blocking_reasons.append("promotion_decision_not_allowed")

    if admission_input.degraded_reason:
        if policy.allow_degraded:
            warnings.append("degraded_input_allowed")
        else:
            blocking_reasons.append("degraded_reason_not_allowed")

    if normalized_action == _PROMOTE_ACTION:
        _append_promote_reasons(
            admission_input=admission_input,
            policy=policy,
            blocking_reasons=blocking_reasons,
        )
    elif normalized_action == _SERVE_ACTION:
        _append_serve_reasons(
            admission_input=admission_input,
            policy=policy,
            blocking_reasons=blocking_reasons,
        )

    allowed = not blocking_reasons
    reason_codes.append(f"{normalized_action}_{'allowed' if allowed else 'blocked'}")
    if admission_input.validation_status != "valid" and policy.allow_degraded:
        warnings.append("non_valid_status_allowed_by_policy")

    normalized_reason_codes = _normalize_reason_codes(tuple(reason_codes))
    normalized_blocking_reasons = _normalize_reason_codes(tuple(blocking_reasons))
    normalized_warnings = _normalize_reason_codes(tuple(warnings))
    frozen_metadata = _freeze_metadata(
        {
            "input": admission_input.to_dict(),
            "policy": _policy_identity_payload(policy),
        }
    )
    decision_id = build_admission_decision_id(
        action=normalized_action,
        allowed=allowed,
        policy_version=policy.policy_version,
        target_id=admission_input.target_id,
        target_type=admission_input.target_type,
        fingerprint=admission_input.fingerprint,
        idempotency_key=admission_input.idempotency_key,
        reason_codes=normalized_reason_codes,
        blocking_reasons=normalized_blocking_reasons,
        warnings=normalized_warnings,
    )
    return AdmissionDecision(
        decision_id=decision_id,
        action=normalized_action,
        allowed=allowed,
        policy_version=policy.policy_version,
        target_id=admission_input.target_id,
        target_type=admission_input.target_type,
        fingerprint=admission_input.fingerprint,
        idempotency_key=admission_input.idempotency_key,
        produced_at=admission_input.produced_at,
        reason_codes=normalized_reason_codes,
        blocking_reasons=normalized_blocking_reasons,
        warnings=normalized_warnings,
        _metadata=frozen_metadata,
    )


def admission_input_from_eval_event(
    *,
    event: EvidenceEvalEvent,
    coverage_rate: float,
    verification_rate: float,
    fallback_rate: float,
    degraded_reason: str | None = None,
    metadata: Mapping[str, JsonValue] | None = None,
) -> AdmissionInput:
    """Create admission input from an E2 eval event contract."""

    if not isinstance(event, EvidenceEvalEvent):
        raise ValueError("event must be an EvidenceEvalEvent")
    return AdmissionInput(
        target_id=event.event_id,
        target_type="eval_event",
        fingerprint=event.fingerprint,
        idempotency_key=event.idempotency_key,
        policy_version=event.policy_version,
        produced_at=event.produced_at,
        validation_status=event.validation_status,
        coverage_rate=coverage_rate,
        verification_rate=verification_rate,
        fallback_rate=fallback_rate,
        degraded_reason=degraded_reason,
        upstream_ids=event.upstream_ids,
        source_event_id=event.event_id,
        event_type=event.event_type,
        metadata=metadata,
    )


def admission_input_from_ledger_entry(
    *,
    entry: PromotionLedgerEntry,
    coverage_rate: float,
    verification_rate: float,
    fallback_rate: float,
    degraded_reason: str | None = None,
    metadata: Mapping[str, JsonValue] | None = None,
) -> AdmissionInput:
    """Create admission input from an E3 promotion ledger entry."""

    if not isinstance(entry, PromotionLedgerEntry):
        raise ValueError("entry must be a PromotionLedgerEntry")
    return AdmissionInput(
        target_id=entry.ledger_entry_id,
        target_type="promotion_ledger_entry",
        fingerprint=entry.source_event_fingerprint,
        idempotency_key=entry.idempotency_key,
        policy_version=entry.policy_version,
        produced_at=entry.produced_at,
        validation_status=entry.validation_status,
        coverage_rate=coverage_rate,
        verification_rate=verification_rate,
        fallback_rate=fallback_rate,
        degraded_reason=degraded_reason,
        upstream_ids=entry.upstream_ids,
        source_event_id=entry.source_event_id,
        promotion_id=entry.promotion_id,
        event_type=entry.source_event_type,
        promotion_decision=entry.decision,
        metadata=metadata,
    )


def build_admission_decision_id(
    *,
    action: AdmissionAction,
    allowed: bool,
    policy_version: str,
    target_id: str,
    target_type: AdmissionTargetType,
    fingerprint: str,
    idempotency_key: str,
    reason_codes: tuple[str, ...],
    blocking_reasons: tuple[str, ...],
    warnings: tuple[str, ...],
) -> str:
    """Build deterministic admission decision id from canonical fields."""

    identity_payload: JsonValue = {
        "action": action,
        "allowed": allowed,
        "blocking_reasons": list(blocking_reasons),
        "fingerprint": fingerprint,
        "idempotency_key": idempotency_key,
        "policy_version": policy_version,
        "reason_codes": list(reason_codes),
        "target_id": target_id,
        "target_type": target_type,
        "warnings": list(warnings),
    }
    digest = fingerprint_payload(identity_payload).removeprefix("sha256:")
    return f"admission-decision:{digest[:24]}"


def validate_admission_action(action: AdmissionAction) -> AdmissionAction:
    """Return a supported admission action or fail closed."""

    if action not in ALLOWED_ADMISSION_ACTIONS:
        raise ValueError(f"unsupported admission action: {action!r}")
    return action


def validate_admission_target_type(
    target_type: AdmissionTargetType,
) -> AdmissionTargetType:
    """Return a supported admission target type or fail closed."""

    if target_type not in ALLOWED_ADMISSION_TARGET_TYPES:
        raise ValueError(f"unsupported admission target_type: {target_type!r}")
    return target_type


def _append_promote_reasons(
    *,
    admission_input: AdmissionInput,
    policy: AdmissionPolicy,
    blocking_reasons: list[str],
) -> None:
    """Append strict promote blocking reasons."""

    if admission_input.validation_status != "valid":
        blocking_reasons.append("promote_requires_valid_status")
    if admission_input.verification_rate < policy.min_verification_rate:
        blocking_reasons.append("verification_rate_below_threshold")
    if admission_input.coverage_rate < policy.min_coverage_rate:
        blocking_reasons.append("coverage_rate_below_threshold")
    if admission_input.fallback_rate > policy.max_fallback_rate:
        blocking_reasons.append("fallback_rate_above_threshold")
    if not admission_input.upstream_ids:
        blocking_reasons.append("upstream_lineage_required")


def _append_serve_reasons(
    *,
    admission_input: AdmissionInput,
    policy: AdmissionPolicy,
    blocking_reasons: list[str],
) -> None:
    """Append serve-specific blocking reasons."""

    if admission_input.validation_status != "valid" and not policy.allow_degraded:
        blocking_reasons.append("serve_requires_valid_status")


def _staleness_state(
    *,
    produced_at: str,
    now: str,
    stale_after_seconds: int,
) -> str | None:
    """Return deterministic staleness blocker or None."""

    produced_dt = _parse_timestamp(produced_at)
    now_dt = _parse_timestamp(now)
    age_seconds = (now_dt - produced_dt).total_seconds()
    if age_seconds < 0:
        return "produced_at_in_future"
    if age_seconds > stale_after_seconds:
        return "stale_input"
    return None


def _parse_timestamp(value: str) -> datetime:
    """Parse an already validated timezone-aware ISO timestamp."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed


def _policy_identity_payload(policy: AdmissionPolicy) -> dict[str, JsonValue]:
    """Return deterministic policy identity fields for decision metadata."""

    return {
        "allow_degraded": policy.allow_degraded,
        "allowed_decisions": list(policy.allowed_decisions),
        "allowed_event_types": list(policy.allowed_event_types),
        "allowed_validation_statuses": list(policy.allowed_validation_statuses),
        "max_fallback_rate": policy.max_fallback_rate,
        "min_coverage_rate": policy.min_coverage_rate,
        "min_verification_rate": policy.min_verification_rate,
        "policy_version": policy.policy_version,
        "stale_after_seconds": policy.stale_after_seconds,
    }


def _validate_metric(name: str, value: float) -> float:
    """Validate admission metrics as finite rates in [0, 1]."""

    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{name} must be finite")
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return normalized


def _validate_identity_token(name: str, value: str) -> str:
    """Validate IDs that may contain separators but no whitespace."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    return normalized


def _validate_metadata_safe_text(name: str, value: str) -> str:
    """Validate optional free-text reason fields through metadata safety rules."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty when provided")
    _validate_metadata_string(normalized)
    return normalized


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
            key_path = ".".join(path + (str(key),)) or "<root>"
            if not isinstance(key, str):
                raise ValueError(f"metadata key at {key_path} must be a string")
            normalized_key = key.strip().lower()
            if not normalized_key:
                raise ValueError(f"metadata key at {key_path} must be non-empty")
            if normalized_key in seen_keys:
                raise ValueError(
                    f"metadata key at {key_path} collides after normalization: {normalized_key!r}"
                )
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
    """Fail closed on raw secret, user-health, prompt, or path-like strings."""

    normalized = value.strip()
    lowered = normalized.lower().replace("\\", "/")
    if lowered in _CURRENT_DIRECTORY_PATH_VALUES:
        raise ValueError("metadata string appears to contain path-like material")
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

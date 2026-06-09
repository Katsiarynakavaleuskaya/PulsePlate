"""Offline SC-G3 cache observability and false-hit harness contracts.

This module models audit, negative-control, metric, and stop-rule behavior for
future semantic-cache review. It never serves cached output, never stores raw
queries or raw responses, and never reads clocks or runtime infrastructure.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import TypeAlias

from core.ai.exact_fuzzy_cache import (
    MATCH_DECISION_HIT,
    ExactFuzzyCacheLookupRequest,
    ExactFuzzyCacheLookupResult,
    ExactFuzzyCacheRecord,
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

EXPECTED_ACTION_FALLBACK = "fallback"
EXPECTED_ACTION_SAFE_HIT = "safe_hit"
OUTCOME_SAFE_HIT = "safe_hit"
OUTCOME_FALSE_HIT = "false_hit"
OUTCOME_FALLBACK = "fallback"

RISK_EXACT_DUPLICATE_HIT = "exact_duplicate_hit"
RISK_NORMALIZED_FUZZY_HIT = "normalized_fuzzy_hit"
RISK_SEMANTIC_FALSE_POSITIVE = "semantic_false_positive"
RISK_STALE_SOURCE_HIT = "stale_source_hit"
RISK_POLICY_VERSION_MISMATCH_HIT = "policy_version_mismatch_hit"
RISK_MODEL_VERSION_MISMATCH_HIT = "model_version_mismatch_hit"
RISK_USER_CONTEXT_LEAKAGE_HIT = "user_context_leakage_hit"
RISK_ADMISSION_BLOCKED_HIT = "admission_blocked_hit"
RISK_BLOCKED_SURFACE_HIT = "blocked_surface_hit"

REASON_CANDIDATE_HIT = "candidate_hit"
REASON_CANDIDATE_MISS = "candidate_miss"
REASON_SAFE_HIT = "safe_hit"
REASON_FALLBACK_REQUIRED = "fallback_required"
REASON_NEGATIVE_CONTROL = "negative_control"
REASON_STALE_SOURCE = "stale_source"
REASON_POLICY_MISMATCH = "policy_version_mismatch"
REASON_MODEL_MISMATCH = "model_version_mismatch"
REASON_CONTEXT_LEAKAGE = "user_context_leakage"
REASON_ADMISSION_BLOCKED = "admission_blocked"
REASON_BLOCKED_SURFACE = "blocked_surface"
REASON_RESPONSE_FINGERPRINT_MISMATCH = "response_fingerprint_mismatch"
REASON_KILL_SWITCH_DISABLED = "kill_switch_disabled"

_ALLOWED_EXPECTED_ACTIONS = {EXPECTED_ACTION_FALLBACK, EXPECTED_ACTION_SAFE_HIT}
_ALLOWED_RISK_CLASSES = {
    RISK_EXACT_DUPLICATE_HIT,
    RISK_NORMALIZED_FUZZY_HIT,
    RISK_SEMANTIC_FALSE_POSITIVE,
    RISK_STALE_SOURCE_HIT,
    RISK_POLICY_VERSION_MISMATCH_HIT,
    RISK_MODEL_VERSION_MISMATCH_HIT,
    RISK_USER_CONTEXT_LEAKAGE_HIT,
    RISK_ADMISSION_BLOCKED_HIT,
    RISK_BLOCKED_SURFACE_HIT,
}
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_ISO_PRODUCED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_PATH_RE = re.compile(r"(?:^|[\s=])(?:/|~[/\\]|[A-Za-z]:[\\/]|\\\\|file://)")
_UNSAFE_METADATA_RE = re.compile(
    r"raw[_ -]?(?:query|prompt|response|answer)"
    r"|normalized[_ -]?query"
    r"|provider[_ -]?payload"
    r"|prompt"
    r"|response"
    r"|answer"
    r"|secret"
    r"|credential"
    r"|authorization"
    r"|api[_ -]?key"
    r"|bearer"
    r"|basic [a-z0-9+/=]+"
    r"|cookie"
    r"|set-cookie"
    r"|session[_ -]?id"
    r"|x-api-key"
    r"|private[_ -]?key"
    r"|sk-[a-z0-9]"
    r"|gh[pousr]_[a-z0-9._-]+"
    r"|github_pat_[a-z0-9._-]+"
    r"|xox[baprs]-[a-z0-9._-]+"
    r"|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
    r"|\+?\d[\d ()-]{7,}\d"
    r"|healthkit"
    r"|diagnosis"
    r"|symptom"
    r"|medical"
    r"|account[_ -]?(?:id|truth)"
    r"|coaching[_ -]?state"
    r"|user[_ -]?health",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CacheLookupAuditEvent:
    """Safe audit shape for a future cache lookup decision."""

    audit_event_id: str
    idempotency_key: str
    surface: str
    request_fingerprint: str
    candidate_record_id: str | None
    candidate_response_fingerprint: str | None
    lookup_decision: str
    match_mode: str | None
    policy_version: str
    provider_key: str
    model_key: str
    user_tier: str
    context_fingerprint: str
    transparency_notice_id: str
    source_fingerprints: tuple[str, ...]
    eval_event_ids: tuple[str, ...]
    admission_decision_id: str | None
    promotion_ids: tuple[str, ...]
    replay_entry_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    produced_at: str
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "audit_event_id", _validate_token("audit_event_id", self.audit_event_id)
        )
        object.__setattr__(
            self, "idempotency_key", _validate_token("idempotency_key", self.idempotency_key)
        )
        object.__setattr__(self, "surface", _validate_token("surface", self.surface))
        object.__setattr__(
            self,
            "request_fingerprint",
            _validate_token("request_fingerprint", self.request_fingerprint),
        )
        if self.candidate_record_id is not None:
            object.__setattr__(
                self,
                "candidate_record_id",
                _validate_token("candidate_record_id", self.candidate_record_id),
            )
        if self.candidate_response_fingerprint is not None:
            object.__setattr__(
                self,
                "candidate_response_fingerprint",
                _validate_token(
                    "candidate_response_fingerprint",
                    self.candidate_response_fingerprint,
                ),
            )
        object.__setattr__(
            self, "lookup_decision", _validate_token("lookup_decision", self.lookup_decision)
        )
        if self.match_mode is not None:
            object.__setattr__(self, "match_mode", _validate_token("match_mode", self.match_mode))
        if self.lookup_decision == MATCH_DECISION_HIT:
            if self.candidate_record_id is None:
                raise ValueError("hit audit events require candidate_record_id")
            if self.candidate_response_fingerprint is None:
                raise ValueError("hit audit events require candidate_response_fingerprint")
            if self.match_mode is None:
                raise ValueError("hit audit events require match_mode")
        elif (
            self.candidate_record_id is not None or self.candidate_response_fingerprint is not None
        ):
            raise ValueError("miss audit events must not carry candidate fields")
        elif self.match_mode is not None:
            raise ValueError("miss audit events must not carry match_mode")
        object.__setattr__(
            self, "policy_version", _validate_token("policy_version", self.policy_version)
        )
        object.__setattr__(self, "provider_key", _validate_token("provider_key", self.provider_key))
        object.__setattr__(self, "model_key", _validate_token("model_key", self.model_key))
        object.__setattr__(self, "user_tier", _validate_token("user_tier", self.user_tier))
        object.__setattr__(
            self,
            "context_fingerprint",
            _validate_token("context_fingerprint", self.context_fingerprint),
        )
        object.__setattr__(
            self,
            "transparency_notice_id",
            _validate_token("transparency_notice_id", self.transparency_notice_id),
        )
        object.__setattr__(
            self,
            "source_fingerprints",
            _normalize_required_unique_tokens("source_fingerprints", self.source_fingerprints),
        )
        object.__setattr__(
            self,
            "eval_event_ids",
            _normalize_unique_tokens("eval_event_ids", self.eval_event_ids),
        )
        if self.admission_decision_id is not None:
            object.__setattr__(
                self,
                "admission_decision_id",
                _validate_token("admission_decision_id", self.admission_decision_id),
            )
        object.__setattr__(
            self,
            "promotion_ids",
            _normalize_unique_tokens("promotion_ids", self.promotion_ids),
        )
        object.__setattr__(
            self,
            "replay_entry_ids",
            _normalize_unique_tokens("replay_entry_ids", self.replay_entry_ids),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )
        object.__setattr__(self, "produced_at", _validate_produced_at(self.produced_at))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class FalseHitHarnessCase:
    """Offline negative-control case for a hypothetical cache lookup."""

    case_id: str
    risk_class: str
    audit_event: CacheLookupAuditEvent
    expected_action: str
    fresh_response_fingerprint: str | None
    current_source_fingerprints: tuple[str, ...]
    current_policy_version: str
    current_model_key: str
    current_user_tier: str
    current_context_fingerprint: str
    admission_allowed: bool
    blocked_surface: bool
    negative_control: bool
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _validate_token("case_id", self.case_id))
        if self.risk_class not in _ALLOWED_RISK_CLASSES:
            raise ValueError(f"unsupported risk_class: {self.risk_class!r}")
        if not isinstance(self.audit_event, CacheLookupAuditEvent):
            raise ValueError("audit_event must be CacheLookupAuditEvent")
        if self.expected_action not in _ALLOWED_EXPECTED_ACTIONS:
            raise ValueError(f"unsupported expected_action: {self.expected_action!r}")
        if self.fresh_response_fingerprint is not None:
            object.__setattr__(
                self,
                "fresh_response_fingerprint",
                _validate_token("fresh_response_fingerprint", self.fresh_response_fingerprint),
            )
        object.__setattr__(
            self,
            "current_source_fingerprints",
            _normalize_required_unique_tokens(
                "current_source_fingerprints",
                self.current_source_fingerprints,
            ),
        )
        object.__setattr__(
            self,
            "current_policy_version",
            _validate_token("current_policy_version", self.current_policy_version),
        )
        object.__setattr__(
            self,
            "current_model_key",
            _validate_token("current_model_key", self.current_model_key),
        )
        object.__setattr__(
            self,
            "current_user_tier",
            _validate_token("current_user_tier", self.current_user_tier),
        )
        object.__setattr__(
            self,
            "current_context_fingerprint",
            _validate_token("current_context_fingerprint", self.current_context_fingerprint),
        )
        _validate_bool("admission_allowed", self.admission_allowed)
        _validate_bool("blocked_surface", self.blocked_surface)
        _validate_bool("negative_control", self.negative_control)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class FalseHitHarnessEvaluation:
    """Deterministic result for one false-hit harness case."""

    evaluation_id: str
    case_id: str
    allowed: bool
    outcome_class: str
    is_false_hit: bool
    reason_codes: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    produced_at: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "evaluation_id", _validate_token("evaluation_id", self.evaluation_id)
        )
        object.__setattr__(self, "case_id", _validate_token("case_id", self.case_id))
        _validate_bool("allowed", self.allowed)
        if self.outcome_class not in {OUTCOME_SAFE_HIT, OUTCOME_FALSE_HIT, OUTCOME_FALLBACK}:
            raise ValueError(f"unsupported outcome_class: {self.outcome_class!r}")
        _validate_bool("is_false_hit", self.is_false_hit)
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _normalize_unique_tokens("blocking_reasons", self.blocking_reasons),
        )
        object.__setattr__(self, "produced_at", _validate_produced_at(self.produced_at))


@dataclass(frozen=True)
class CacheObservabilityMetrics:
    """Offline metrics snapshot for future semantic-cache safety review."""

    metrics_id: str
    eligible_request_count: int
    candidate_hit_count: int
    safe_hit_count: int
    false_hit_count: int
    fallback_count: int
    bypass_count: int
    kill_switch_disabled_count: int
    admission_blocked_hit_count: int
    stale_source_hit_count: int
    policy_mismatch_hit_count: int
    model_mismatch_hit_count: int
    context_leakage_hit_count: int
    blocked_surface_hit_count: int
    eligible_hit_rate_bps: int
    served_hit_rate_bps: int
    false_hit_rate_bps: int
    cache_precision_proxy_bps: int
    stale_answer_rate_bps: int
    fallback_rate_bps: int
    bypass_rate_bps: int
    latency_saved_p50_ms: int
    latency_saved_p95_ms: int
    provider_calls_avoided_count: int
    cost_saved_microunits: int
    produced_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics_id", _validate_token("metrics_id", self.metrics_id))
        for name in (
            "eligible_request_count",
            "candidate_hit_count",
            "safe_hit_count",
            "false_hit_count",
            "fallback_count",
            "bypass_count",
            "kill_switch_disabled_count",
            "admission_blocked_hit_count",
            "stale_source_hit_count",
            "policy_mismatch_hit_count",
            "model_mismatch_hit_count",
            "context_leakage_hit_count",
            "blocked_surface_hit_count",
            "latency_saved_p50_ms",
            "latency_saved_p95_ms",
            "provider_calls_avoided_count",
            "cost_saved_microunits",
        ):
            _validate_non_negative_int(name, getattr(self, name))
        for name in (
            "eligible_hit_rate_bps",
            "served_hit_rate_bps",
            "false_hit_rate_bps",
            "cache_precision_proxy_bps",
            "stale_answer_rate_bps",
            "fallback_rate_bps",
            "bypass_rate_bps",
        ):
            _validate_bps(name, getattr(self, name))
        object.__setattr__(self, "produced_at", _validate_produced_at(self.produced_at))


@dataclass(frozen=True)
class TokenEconomyEstimate:
    """Metadata-only token/cost estimate for future cache economics review."""

    estimate_id: str
    surface: str
    route_type: str
    provider_label: str
    model_label: str
    token_estimate_version: str
    prompt_input_chars: int
    prompt_output_chars: int
    prompt_input_tokens_estimate: int
    prompt_output_tokens_estimate: int
    baseline_context_tokens_estimate: int
    candidate_context_tokens_estimate: int
    tokens_saved_estimate: int
    orchestration_fanout_multiplier: int
    provider_calls_avoided_count: int
    cost_saved_microunits: int
    cost_estimate_policy_version: str
    currency_code: str
    reason_codes: tuple[str, ...]
    produced_at: str
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "estimate_id", _validate_token("estimate_id", self.estimate_id))
        for name in (
            "surface",
            "route_type",
            "provider_label",
            "model_label",
            "token_estimate_version",
            "cost_estimate_policy_version",
            "currency_code",
        ):
            object.__setattr__(self, name, _validate_safe_token(name, getattr(self, name)))
        for name in (
            "prompt_input_chars",
            "prompt_output_chars",
            "prompt_input_tokens_estimate",
            "prompt_output_tokens_estimate",
            "baseline_context_tokens_estimate",
            "candidate_context_tokens_estimate",
            "tokens_saved_estimate",
            "orchestration_fanout_multiplier",
            "provider_calls_avoided_count",
            "cost_saved_microunits",
        ):
            _validate_non_negative_int(name, getattr(self, name))
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )
        object.__setattr__(self, "produced_at", _validate_produced_at(self.produced_at))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class CacheStopRules:
    """Fail-closed stop thresholds for future cache serving experiments."""

    policy_version: str
    max_false_hit_rate_bps: int
    max_stale_answer_rate_bps: int
    max_policy_mismatch_hits: int
    max_model_mismatch_hits: int
    max_context_leakage_hits: int
    allow_blocked_surface_hits: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "policy_version", _validate_token("policy_version", self.policy_version)
        )
        _validate_bps("max_false_hit_rate_bps", self.max_false_hit_rate_bps)
        _validate_bps("max_stale_answer_rate_bps", self.max_stale_answer_rate_bps)
        _validate_non_negative_int("max_policy_mismatch_hits", self.max_policy_mismatch_hits)
        _validate_non_negative_int("max_model_mismatch_hits", self.max_model_mismatch_hits)
        _validate_non_negative_int("max_context_leakage_hits", self.max_context_leakage_hits)
        _validate_bool("allow_blocked_surface_hits", self.allow_blocked_surface_hits)


@dataclass(frozen=True)
class CacheStopDecision:
    """Deterministic stop/rollback decision for safety thresholds."""

    decision_id: str
    stop_serving: bool
    rollback_required: bool
    reason_codes: tuple[str, ...]
    produced_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _validate_token("decision_id", self.decision_id))
        _validate_bool("stop_serving", self.stop_serving)
        _validate_bool("rollback_required", self.rollback_required)
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )
        object.__setattr__(self, "produced_at", _validate_produced_at(self.produced_at))


@dataclass(frozen=True)
class KillSwitchSnapshot:
    """Explicit disabled-state snapshot for future cache experiments."""

    environment_enabled: bool
    runtime_enabled: bool
    request_disabled: bool
    bypass_forced: bool

    def __post_init__(self) -> None:
        _validate_bool("environment_enabled", self.environment_enabled)
        _validate_bool("runtime_enabled", self.runtime_enabled)
        _validate_bool("request_disabled", self.request_disabled)
        _validate_bool("bypass_forced", self.bypass_forced)

    @property
    def disables_hypothetical_serving(self) -> bool:
        return (
            not self.environment_enabled
            or not self.runtime_enabled
            or self.request_disabled
            or self.bypass_forced
        )


def build_cache_lookup_audit_event(
    *,
    request: ExactFuzzyCacheLookupRequest,
    lookup_result: ExactFuzzyCacheLookupResult,
    candidate_record: ExactFuzzyCacheRecord | None,
    produced_at: str,
    metadata: Mapping[str, JsonValue] | None = None,
    reason_codes: Iterable[str] = (),
) -> CacheLookupAuditEvent:
    """Build a safe audit event from SC-G2 lookup contracts."""

    if not isinstance(request, ExactFuzzyCacheLookupRequest):
        raise ValueError("request must be ExactFuzzyCacheLookupRequest")
    if not isinstance(lookup_result, ExactFuzzyCacheLookupResult):
        raise ValueError("lookup_result must be ExactFuzzyCacheLookupResult")
    _validate_produced_at(produced_at)
    hit = lookup_result.decision == MATCH_DECISION_HIT
    if hit and candidate_record is None:
        raise ValueError("candidate_record is required for hit decisions")
    if not hit and candidate_record is not None:
        raise ValueError("candidate_record must be omitted for miss decisions")
    if (
        candidate_record is not None
        and candidate_record.record_id != lookup_result.matched_record_id
    ):
        raise ValueError("candidate_record must match lookup_result.matched_record_id")

    lineage = candidate_record.lineage if candidate_record is not None else None
    source_fingerprints = (
        lineage.source_fingerprints if lineage is not None else request.source_fingerprints
    )
    request_payload: JsonValue = {
        "context_fingerprint": request.context_fingerprint,
        "model_key": request.model_key,
        "policy_version": request.policy_version,
        "provider_key": request.provider_key,
        "query_identity_fingerprint": (
            f"cache-query:{_fingerprint_payload({'raw_query': request.raw_query})[:24]}"
        ),
        "source_fingerprints": list(request.source_fingerprints),
        "surface": request.surface,
        "transparency_notice_id": request.transparency_notice_id,
        "user_tier": request.user_tier,
    }
    request_fingerprint = f"cache-request:{_fingerprint_payload(request_payload)[:24]}"
    event_payload: dict[str, JsonValue] = {
        "candidate_record_id": candidate_record.record_id if candidate_record is not None else None,
        "candidate_response_fingerprint": (
            candidate_record.response_fingerprint if candidate_record is not None else None
        ),
        "lookup_decision": lookup_result.decision,
        "match_mode": lookup_result.match_mode,
        "request_fingerprint": request_fingerprint,
        "source_fingerprints": list(source_fingerprints),
    }
    audit_event_id = f"cache-audit:{_fingerprint_payload(event_payload)[:24]}"
    idempotency_payload: dict[str, JsonValue] = {**event_payload, "surface": request.surface}
    idempotency_key = f"cache-audit-idempotency:{_fingerprint_payload(idempotency_payload)[:24]}"
    normalized_reasons = _normalize_required_unique_tokens(
        "reason_codes",
        (
            *(lookup_result.reason_codes),
            *(tuple(reason_codes)),
            REASON_CANDIDATE_HIT if hit else REASON_CANDIDATE_MISS,
        ),
    )
    return CacheLookupAuditEvent(
        audit_event_id=audit_event_id,
        idempotency_key=idempotency_key,
        surface=request.surface,
        request_fingerprint=request_fingerprint,
        candidate_record_id=candidate_record.record_id if candidate_record is not None else None,
        candidate_response_fingerprint=(
            candidate_record.response_fingerprint if candidate_record is not None else None
        ),
        lookup_decision=lookup_result.decision,
        match_mode=lookup_result.match_mode,
        policy_version=request.policy_version,
        provider_key=request.provider_key,
        model_key=request.model_key,
        user_tier=request.user_tier,
        context_fingerprint=request.context_fingerprint,
        transparency_notice_id=request.transparency_notice_id,
        source_fingerprints=source_fingerprints,
        eval_event_ids=lineage.eval_event_ids if lineage is not None else (),
        admission_decision_id=lineage.admission_decision_id if lineage is not None else None,
        promotion_ids=lineage.promotion_ids if lineage is not None else (),
        replay_entry_ids=lineage.replay_entry_ids if lineage is not None else (),
        reason_codes=normalized_reasons,
        produced_at=produced_at,
        metadata=metadata or {},
    )


def evaluate_false_hit_case(
    *,
    case: FalseHitHarnessCase,
    produced_at: str,
    kill_switch_snapshot: KillSwitchSnapshot | None = None,
) -> FalseHitHarnessEvaluation:
    """Evaluate one offline false-hit case without serving cached output."""

    if not isinstance(case, FalseHitHarnessCase):
        raise ValueError("case must be FalseHitHarnessCase")
    _validate_produced_at(produced_at)
    candidate_hit = case.audit_event.lookup_decision == MATCH_DECISION_HIT
    blocking_reasons: list[str] = []
    reason_codes: list[str] = [REASON_CANDIDATE_HIT if candidate_hit else REASON_CANDIDATE_MISS]

    if kill_switch_snapshot is not None and kill_switch_snapshot.disables_hypothetical_serving:
        blocking_reasons.append(REASON_KILL_SWITCH_DISABLED)
    if case.blocked_surface:
        blocking_reasons.append(REASON_BLOCKED_SURFACE)
    if not case.admission_allowed:
        blocking_reasons.append(REASON_ADMISSION_BLOCKED)
    if case.current_source_fingerprints != case.audit_event.source_fingerprints:
        blocking_reasons.append(REASON_STALE_SOURCE)
    if case.current_policy_version != case.audit_event.policy_version:
        blocking_reasons.append(REASON_POLICY_MISMATCH)
    if case.current_model_key != case.audit_event.model_key:
        blocking_reasons.append(REASON_MODEL_MISMATCH)
    if (
        case.current_user_tier != case.audit_event.user_tier
        or case.current_context_fingerprint != case.audit_event.context_fingerprint
    ):
        blocking_reasons.append(REASON_CONTEXT_LEAKAGE)
    if (
        case.fresh_response_fingerprint is not None
        and case.audit_event.candidate_response_fingerprint is not None
        and case.fresh_response_fingerprint != case.audit_event.candidate_response_fingerprint
    ):
        blocking_reasons.append(REASON_RESPONSE_FINGERPRINT_MISMATCH)
    if case.negative_control:
        reason_codes.append(REASON_NEGATIVE_CONTROL)
        if candidate_hit:
            blocking_reasons.append(REASON_FALLBACK_REQUIRED)

    if (
        case.expected_action == EXPECTED_ACTION_FALLBACK
        and REASON_FALLBACK_REQUIRED not in reason_codes
    ):
        reason_codes.append(REASON_FALLBACK_REQUIRED)
    if blocking_reasons:
        reason_codes.extend(blocking_reasons)

    allowed = (
        candidate_hit and case.expected_action == EXPECTED_ACTION_SAFE_HIT and not blocking_reasons
    )
    false_hit_blockers = tuple(
        reason for reason in blocking_reasons if reason != REASON_KILL_SWITCH_DISABLED
    )
    is_false_hit = candidate_hit and bool(
        false_hit_blockers or case.expected_action == EXPECTED_ACTION_FALLBACK
    )
    if allowed:
        outcome_class = OUTCOME_SAFE_HIT
        reason_codes.append(REASON_SAFE_HIT)
    elif is_false_hit:
        outcome_class = OUTCOME_FALSE_HIT
    else:
        outcome_class = OUTCOME_FALLBACK

    normalized_reasons = _normalize_required_unique_tokens(
        "reason_codes", dict.fromkeys(reason_codes)
    )
    normalized_blockers = _normalize_unique_tokens("blocking_reasons", blocking_reasons)
    evaluation_payload: JsonValue = {
        "allowed": allowed,
        "blocking_reasons": list(normalized_blockers),
        "case_id": case.case_id,
        "is_false_hit": is_false_hit,
        "outcome_class": outcome_class,
        "reason_codes": list(normalized_reasons),
    }
    return FalseHitHarnessEvaluation(
        evaluation_id=f"cache-harness-eval:{_fingerprint_payload(evaluation_payload)[:24]}",
        case_id=case.case_id,
        allowed=allowed,
        outcome_class=outcome_class,
        is_false_hit=is_false_hit,
        reason_codes=normalized_reasons,
        blocking_reasons=normalized_blockers,
        produced_at=produced_at,
    )


def evaluate_false_hit_harness(
    *,
    cases: Iterable[FalseHitHarnessCase],
    produced_at: str,
    kill_switch_snapshot: KillSwitchSnapshot | None = None,
) -> tuple[FalseHitHarnessEvaluation, ...]:
    """Evaluate false-hit cases in deterministic order."""

    ordered_cases = sorted(tuple(cases), key=lambda item: (item.risk_class, item.case_id))
    return tuple(
        evaluate_false_hit_case(
            case=case,
            produced_at=produced_at,
            kill_switch_snapshot=kill_switch_snapshot,
        )
        for case in ordered_cases
    )


def compute_cache_observability_metrics(
    *,
    evaluations: Iterable[FalseHitHarnessEvaluation],
    produced_at: str,
    latency_saved_ms: Iterable[int] = (),
    provider_calls_avoided_count: int = 0,
    cost_saved_microunits: int = 0,
    bypass_count: int = 0,
    kill_switch_disabled_count: int = 0,
) -> CacheObservabilityMetrics:
    """Compute deterministic integer metrics from offline harness evaluations."""

    _validate_produced_at(produced_at)
    ordered = sorted(tuple(evaluations), key=lambda item: item.evaluation_id)
    latencies = tuple(
        sorted(_validate_non_negative_int("latency_saved_ms", value) for value in latency_saved_ms)
    )
    provider_calls_avoided_count = _validate_non_negative_int(
        "provider_calls_avoided_count",
        provider_calls_avoided_count,
    )
    cost_saved_microunits = _validate_non_negative_int(
        "cost_saved_microunits",
        cost_saved_microunits,
    )
    bypass_count = _validate_non_negative_int("bypass_count", bypass_count)
    kill_switch_disabled_count = _validate_non_negative_int(
        "kill_switch_disabled_count",
        kill_switch_disabled_count,
    )

    eligible_request_count = len(ordered)
    candidate_hit_count = sum(REASON_CANDIDATE_HIT in item.reason_codes for item in ordered)
    safe_hit_count = sum(item.outcome_class == OUTCOME_SAFE_HIT for item in ordered)
    false_hit_count = sum(item.is_false_hit for item in ordered)
    fallback_count = sum(item.outcome_class == OUTCOME_FALLBACK for item in ordered)
    admission_blocked_hit_count = _count_blocker(ordered, REASON_ADMISSION_BLOCKED)
    stale_source_hit_count = _count_blocker(ordered, REASON_STALE_SOURCE)
    policy_mismatch_hit_count = _count_blocker(ordered, REASON_POLICY_MISMATCH)
    model_mismatch_hit_count = _count_blocker(ordered, REASON_MODEL_MISMATCH)
    context_leakage_hit_count = _count_blocker(ordered, REASON_CONTEXT_LEAKAGE)
    blocked_surface_hit_count = _count_blocker(ordered, REASON_BLOCKED_SURFACE)
    precision_denominator = safe_hit_count + false_hit_count
    metrics_payload: JsonValue = {
        "eligible_request_count": eligible_request_count,
        "false_hit_count": false_hit_count,
        "safe_hit_count": safe_hit_count,
        "stale_source_hit_count": stale_source_hit_count,
    }
    return CacheObservabilityMetrics(
        metrics_id=f"cache-metrics:{_fingerprint_payload(metrics_payload)[:24]}",
        eligible_request_count=eligible_request_count,
        candidate_hit_count=candidate_hit_count,
        safe_hit_count=safe_hit_count,
        false_hit_count=false_hit_count,
        fallback_count=fallback_count,
        bypass_count=bypass_count,
        kill_switch_disabled_count=kill_switch_disabled_count,
        admission_blocked_hit_count=admission_blocked_hit_count,
        stale_source_hit_count=stale_source_hit_count,
        policy_mismatch_hit_count=policy_mismatch_hit_count,
        model_mismatch_hit_count=model_mismatch_hit_count,
        context_leakage_hit_count=context_leakage_hit_count,
        blocked_surface_hit_count=blocked_surface_hit_count,
        eligible_hit_rate_bps=_rate_bps(candidate_hit_count, eligible_request_count),
        served_hit_rate_bps=_rate_bps(safe_hit_count, eligible_request_count),
        false_hit_rate_bps=_rate_bps(false_hit_count, candidate_hit_count),
        cache_precision_proxy_bps=_rate_bps(safe_hit_count, precision_denominator),
        stale_answer_rate_bps=_rate_bps(stale_source_hit_count, candidate_hit_count),
        fallback_rate_bps=_rate_bps(fallback_count, eligible_request_count),
        bypass_rate_bps=_rate_bps(bypass_count, eligible_request_count),
        latency_saved_p50_ms=_percentile_ms(latencies, 50),
        latency_saved_p95_ms=_percentile_ms(latencies, 95),
        provider_calls_avoided_count=provider_calls_avoided_count,
        cost_saved_microunits=cost_saved_microunits,
        produced_at=produced_at,
    )


def build_token_economy_estimate(
    *,
    surface: str,
    route_type: str,
    provider_label: str,
    model_label: str,
    token_estimate_version: str,
    prompt_input_chars: int,
    prompt_output_chars: int,
    prompt_input_tokens_estimate: int,
    prompt_output_tokens_estimate: int,
    baseline_context_tokens_estimate: int,
    candidate_context_tokens_estimate: int,
    tokens_saved_estimate: int,
    orchestration_fanout_multiplier: int,
    provider_calls_avoided_count: int,
    cost_saved_microunits: int,
    cost_estimate_policy_version: str,
    currency_code: str,
    reason_codes: Iterable[str],
    produced_at: str,
    metadata: Mapping[str, JsonValue] | None = None,
) -> TokenEconomyEstimate:
    """Build a deterministic metadata-only token/cost estimate."""

    normalized_surface = _validate_safe_token("surface", surface)
    normalized_route_type = _validate_safe_token("route_type", route_type)
    normalized_provider_label = _validate_safe_token("provider_label", provider_label)
    normalized_model_label = _validate_safe_token("model_label", model_label)
    normalized_token_estimate_version = _validate_safe_token(
        "token_estimate_version",
        token_estimate_version,
    )
    normalized_cost_estimate_policy_version = _validate_safe_token(
        "cost_estimate_policy_version",
        cost_estimate_policy_version,
    )
    normalized_currency_code = _validate_safe_token("currency_code", currency_code)
    normalized_reasons = _normalize_required_unique_tokens("reason_codes", reason_codes)
    normalized_prompt_input_chars = _validate_non_negative_int(
        "prompt_input_chars",
        prompt_input_chars,
    )
    normalized_prompt_output_chars = _validate_non_negative_int(
        "prompt_output_chars",
        prompt_output_chars,
    )
    normalized_prompt_input_tokens_estimate = _validate_non_negative_int(
        "prompt_input_tokens_estimate",
        prompt_input_tokens_estimate,
    )
    normalized_prompt_output_tokens_estimate = _validate_non_negative_int(
        "prompt_output_tokens_estimate",
        prompt_output_tokens_estimate,
    )
    normalized_baseline_context_tokens_estimate = _validate_non_negative_int(
        "baseline_context_tokens_estimate",
        baseline_context_tokens_estimate,
    )
    normalized_candidate_context_tokens_estimate = _validate_non_negative_int(
        "candidate_context_tokens_estimate",
        candidate_context_tokens_estimate,
    )
    normalized_tokens_saved_estimate = _validate_non_negative_int(
        "tokens_saved_estimate",
        tokens_saved_estimate,
    )
    normalized_orchestration_fanout_multiplier = _validate_non_negative_int(
        "orchestration_fanout_multiplier",
        orchestration_fanout_multiplier,
    )
    normalized_provider_calls_avoided_count = _validate_non_negative_int(
        "provider_calls_avoided_count",
        provider_calls_avoided_count,
    )
    normalized_cost_saved_microunits = _validate_non_negative_int(
        "cost_saved_microunits",
        cost_saved_microunits,
    )
    sorted_reason_codes: list[JsonValue] = [reason for reason in sorted(normalized_reasons)]
    payload: JsonValue = {
        "baseline_context_tokens_estimate": normalized_baseline_context_tokens_estimate,
        "candidate_context_tokens_estimate": normalized_candidate_context_tokens_estimate,
        "cost_estimate_policy_version": normalized_cost_estimate_policy_version,
        "cost_saved_microunits": normalized_cost_saved_microunits,
        "currency_code": normalized_currency_code,
        "model_label": normalized_model_label,
        "orchestration_fanout_multiplier": normalized_orchestration_fanout_multiplier,
        "prompt_input_chars": normalized_prompt_input_chars,
        "prompt_input_tokens_estimate": normalized_prompt_input_tokens_estimate,
        "prompt_output_chars": normalized_prompt_output_chars,
        "prompt_output_tokens_estimate": normalized_prompt_output_tokens_estimate,
        "provider_label": normalized_provider_label,
        "provider_calls_avoided_count": normalized_provider_calls_avoided_count,
        "reason_codes": sorted_reason_codes,
        "route_type": normalized_route_type,
        "surface": normalized_surface,
        "token_estimate_version": normalized_token_estimate_version,
        "tokens_saved_estimate": normalized_tokens_saved_estimate,
    }
    return TokenEconomyEstimate(
        estimate_id=f"token-economy:{_fingerprint_payload(payload)[:24]}",
        surface=normalized_surface,
        route_type=normalized_route_type,
        provider_label=normalized_provider_label,
        model_label=normalized_model_label,
        token_estimate_version=normalized_token_estimate_version,
        prompt_input_chars=normalized_prompt_input_chars,
        prompt_output_chars=normalized_prompt_output_chars,
        prompt_input_tokens_estimate=normalized_prompt_input_tokens_estimate,
        prompt_output_tokens_estimate=normalized_prompt_output_tokens_estimate,
        baseline_context_tokens_estimate=normalized_baseline_context_tokens_estimate,
        candidate_context_tokens_estimate=normalized_candidate_context_tokens_estimate,
        tokens_saved_estimate=normalized_tokens_saved_estimate,
        orchestration_fanout_multiplier=normalized_orchestration_fanout_multiplier,
        provider_calls_avoided_count=normalized_provider_calls_avoided_count,
        cost_saved_microunits=normalized_cost_saved_microunits,
        cost_estimate_policy_version=normalized_cost_estimate_policy_version,
        currency_code=normalized_currency_code,
        reason_codes=normalized_reasons,
        produced_at=produced_at,
        metadata=metadata or {},
    )


def evaluate_cache_stop_rules(
    *,
    metrics: CacheObservabilityMetrics,
    stop_rules: CacheStopRules,
    produced_at: str,
) -> CacheStopDecision:
    """Evaluate stop rules into a deterministic rollback decision."""

    if not isinstance(metrics, CacheObservabilityMetrics):
        raise ValueError("metrics must be CacheObservabilityMetrics")
    if not isinstance(stop_rules, CacheStopRules):
        raise ValueError("stop_rules must be CacheStopRules")
    _validate_produced_at(produced_at)
    reasons: list[str] = []
    if metrics.false_hit_rate_bps > stop_rules.max_false_hit_rate_bps:
        reasons.append("false_hit_rate_threshold_breached")
    if metrics.stale_answer_rate_bps > stop_rules.max_stale_answer_rate_bps:
        reasons.append("stale_answer_rate_threshold_breached")
    if metrics.policy_mismatch_hit_count > stop_rules.max_policy_mismatch_hits:
        reasons.append("policy_mismatch_hit_threshold_breached")
    if metrics.model_mismatch_hit_count > stop_rules.max_model_mismatch_hits:
        reasons.append("model_mismatch_hit_threshold_breached")
    if metrics.context_leakage_hit_count > stop_rules.max_context_leakage_hits:
        reasons.append("context_leakage_hit_threshold_breached")
    if not stop_rules.allow_blocked_surface_hits and metrics.blocked_surface_hit_count > 0:
        reasons.append("blocked_surface_hit_detected")
    if not reasons:
        reasons.append("stop_rules_clear")
    normalized_reasons = _normalize_required_unique_tokens("reason_codes", reasons)
    stop_serving = normalized_reasons != ("stop_rules_clear",)
    payload: JsonValue = {
        "metrics_id": metrics.metrics_id,
        "policy_version": stop_rules.policy_version,
        "reason_codes": list(normalized_reasons),
    }
    return CacheStopDecision(
        decision_id=f"cache-stop:{_fingerprint_payload(payload)[:24]}",
        stop_serving=stop_serving,
        rollback_required=stop_serving,
        reason_codes=normalized_reasons,
        produced_at=produced_at,
    )


def to_stable_mapping(value: object) -> Mapping[str, JsonValue]:
    """Return deterministic safe JSON-ready mappings for SC-G3 contracts."""

    if isinstance(value, CacheLookupAuditEvent):
        return _freeze_mapping(
            {
                "admission_decision_id": value.admission_decision_id,
                "audit_event_id": value.audit_event_id,
                "candidate_record_id": value.candidate_record_id,
                "candidate_response_fingerprint": value.candidate_response_fingerprint,
                "context_fingerprint": value.context_fingerprint,
                "eval_event_ids": list(value.eval_event_ids),
                "idempotency_key": value.idempotency_key,
                "lookup_decision": value.lookup_decision,
                "match_mode": value.match_mode,
                "metadata": _json_safe_copy(value.metadata),
                "model_key": value.model_key,
                "policy_version": value.policy_version,
                "produced_at": value.produced_at,
                "promotion_ids": list(value.promotion_ids),
                "provider_key": value.provider_key,
                "reason_codes": list(value.reason_codes),
                "replay_entry_ids": list(value.replay_entry_ids),
                "request_fingerprint": value.request_fingerprint,
                "source_fingerprints": list(value.source_fingerprints),
                "surface": value.surface,
                "transparency_notice_id": value.transparency_notice_id,
                "user_tier": value.user_tier,
            }
        )
    if isinstance(value, FalseHitHarnessEvaluation):
        return _freeze_mapping(
            {
                "allowed": value.allowed,
                "blocking_reasons": list(value.blocking_reasons),
                "case_id": value.case_id,
                "evaluation_id": value.evaluation_id,
                "is_false_hit": value.is_false_hit,
                "outcome_class": value.outcome_class,
                "produced_at": value.produced_at,
                "reason_codes": list(value.reason_codes),
            }
        )
    if isinstance(value, CacheObservabilityMetrics):
        return _freeze_mapping({name: getattr(value, name) for name in value.__dataclass_fields__})
    if isinstance(value, TokenEconomyEstimate):
        return _freeze_mapping(
            {
                "baseline_context_tokens_estimate": value.baseline_context_tokens_estimate,
                "candidate_context_tokens_estimate": value.candidate_context_tokens_estimate,
                "cost_estimate_policy_version": value.cost_estimate_policy_version,
                "cost_saved_microunits": value.cost_saved_microunits,
                "currency_code": value.currency_code,
                "estimate_id": value.estimate_id,
                "metadata": _json_safe_copy(value.metadata),
                "model_label": value.model_label,
                "orchestration_fanout_multiplier": value.orchestration_fanout_multiplier,
                "produced_at": value.produced_at,
                "prompt_input_chars": value.prompt_input_chars,
                "prompt_input_tokens_estimate": value.prompt_input_tokens_estimate,
                "prompt_output_chars": value.prompt_output_chars,
                "prompt_output_tokens_estimate": value.prompt_output_tokens_estimate,
                "provider_calls_avoided_count": value.provider_calls_avoided_count,
                "provider_label": value.provider_label,
                "reason_codes": list(value.reason_codes),
                "route_type": value.route_type,
                "surface": value.surface,
                "token_estimate_version": value.token_estimate_version,
                "tokens_saved_estimate": value.tokens_saved_estimate,
            }
        )
    if isinstance(value, CacheStopDecision):
        return _freeze_mapping(
            {
                "decision_id": value.decision_id,
                "produced_at": value.produced_at,
                "reason_codes": list(value.reason_codes),
                "rollback_required": value.rollback_required,
                "stop_serving": value.stop_serving,
            }
        )
    if isinstance(value, KillSwitchSnapshot):
        return _freeze_mapping(
            {
                "bypass_forced": value.bypass_forced,
                "environment_enabled": value.environment_enabled,
                "request_disabled": value.request_disabled,
                "runtime_enabled": value.runtime_enabled,
            }
        )
    raise ValueError(f"unsupported stable mapping value: {type(value).__name__}")


def _count_blocker(
    evaluations: Iterable[FalseHitHarnessEvaluation],
    reason_code: str,
) -> int:
    return sum(reason_code in item.blocking_reasons for item in evaluations)


def _rate_bps(numerator: int, denominator: int) -> int:
    _validate_non_negative_int("numerator", numerator)
    _validate_non_negative_int("denominator", denominator)
    if denominator == 0:
        return 0
    return (numerator * 10000) // denominator


def _percentile_ms(values: tuple[int, ...], percentile: int) -> int:
    if not values:
        return 0
    if percentile == 50:
        index = (len(values) - 1) // 2
    elif percentile == 95:
        index = math.ceil((len(values) * 95) / 100) - 1
    else:
        raise ValueError("unsupported percentile")
    return values[index]


def _fingerprint_payload(payload: JsonValue) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _freeze_metadata(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    copied = _json_safe_copy(value)
    if not isinstance(copied, dict):
        raise ValueError("metadata must be a mapping")
    _validate_metadata_is_safe(copied)
    return _freeze_mapping(copied)


def _freeze_mapping(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    return MappingProxyType(dict(sorted(value.items())))


def _json_safe_copy(value: JsonValue | Mapping[str, JsonValue]) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_copy(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_json_safe_copy(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_copy(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata contains non-finite number")
        return value
    raise ValueError(f"metadata contains unsupported value: {type(value).__name__}")


def _validate_metadata_is_safe(value: JsonValue, *, path: str = "metadata") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_safe_metadata_string(f"{path}.key", key)
            _validate_metadata_is_safe(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_metadata_is_safe(item, path=f"{path}[{index}]")
    elif isinstance(value, str):
        _validate_safe_metadata_string(path, value)


def _validate_safe_metadata_string(name: str, value: str) -> None:
    if _UNSAFE_METADATA_RE.search(value) or _PATH_RE.search(value):
        raise ValueError(f"{name} contains unsafe metadata")


def _normalize_required_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = _normalize_unique_tokens(name, values)
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _validate_token(name, value)
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate entries")
        seen.add(normalized)
        normalized_values.append(normalized)
    return tuple(sorted(normalized_values))


def _validate_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    return normalized


def _validate_safe_token(name: str, value: str) -> str:
    normalized = _validate_token(name, value)
    _validate_safe_metadata_string(name, normalized)
    return normalized


def _validate_produced_at(value: str) -> str:
    normalized = value.strip()
    if not _ISO_PRODUCED_AT_RE.match(normalized):
        raise ValueError("produced_at must be explicit UTC second precision timestamp")
    return normalized


def _validate_bps(name: str, value: int) -> None:
    _validate_non_negative_int(name, value)
    if value > 10000:
        raise ValueError(f"{name} must be between 0 and 10000")


def _validate_non_negative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _validate_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be bool")

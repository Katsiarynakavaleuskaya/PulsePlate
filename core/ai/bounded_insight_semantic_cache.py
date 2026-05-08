"""Offline SC-G4 bounded insight semantic-cache experiment contracts.

This module models an off-by-default eligibility decision for a future bounded
`/insight` semantic-cache experiment. It does not wire routes, serve cached
answers, persist payloads, read environment variables, call providers, or select
cache backends.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import TypeAlias

from core.ai.cache_observability import (
    CacheLookupAuditEvent,
    CacheObservabilityMetrics,
    CacheStopDecision,
    FalseHitHarnessEvaluation,
    KillSwitchSnapshot,
)
from core.ai.exact_fuzzy_cache import (
    MATCH_DECISION_HIT,
    ExactFuzzyCacheLookupRequest,
    ExactFuzzyCacheLookupResult,
    ExactFuzzyCacheRecord,
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = (
    JsonScalar
    | list["JsonValue"]
    | tuple["JsonValue", ...]
    | dict[str, "JsonValue"]
    | Mapping[str, "JsonValue"]
)

ALLOWED_SURFACE = "insight"

DECISION_EXPERIMENT_ELIGIBLE = "experiment_eligible"
DECISION_FALLBACK = "fallback"

REASON_EXPERIMENT_ELIGIBLE = "experiment_eligible"
REASON_ENVIRONMENT_FLAG_DISABLED = "environment_flag_disabled"
REASON_RUNTIME_FLAG_DISABLED = "runtime_flag_disabled"
REASON_REQUEST_NOT_OPTED_IN = "request_not_opted_in"
REASON_REQUEST_DISABLED = "request_disabled"
REASON_KILL_SWITCH_DISABLED = "kill_switch_disabled"
REASON_UNSUPPORTED_SURFACE = "unsupported_surface"
REASON_CANDIDATE_MISSING = "candidate_missing"
REASON_LOOKUP_MISS = "lookup_miss"
REASON_MATCHED_RECORD_MISMATCH = "matched_record_mismatch"
REASON_REQUEST_FINGERPRINT_MISMATCH = "request_fingerprint_mismatch"
REASON_RESPONSE_FINGERPRINT_MISMATCH = "response_fingerprint_mismatch"
REASON_SOURCE_FINGERPRINT_MISMATCH = "source_fingerprint_mismatch"
REASON_POLICY_MISMATCH = "policy_mismatch"
REASON_PROVIDER_MISMATCH = "provider_mismatch"
REASON_MODEL_MISMATCH = "model_mismatch"
REASON_CONTEXT_MISMATCH = "context_mismatch"
REASON_USER_TIER_MISMATCH = "user_tier_mismatch"
REASON_TRANSPARENCY_NOTICE_MISMATCH = "transparency_notice_mismatch"
REASON_EVIDENCE_LINKAGE_MISSING = "evidence_linkage_missing"
REASON_EVIDENCE_LINKAGE_MISMATCH = "evidence_linkage_mismatch"
REASON_SAFETY_FLAGS_MISMATCH = "safety_flags_mismatch"
REASON_ADMISSION_BLOCKED = "admission_blocked"
REASON_FALSE_HIT_BLOCKED = "false_hit_blocked"
REASON_STOP_RULE_BLOCKED = "stop_rule_blocked"
REASON_BLOCKED_SURFACE = "blocked_surface"

BLOCKED_SURFACE_LABELS = (
    "account_truth",
    "advisory_wiki",
    "auth",
    "billing",
    "compliance",
    "entitlement",
    "healthkit_sensitive",
    "legal",
    "workforce_memory",
)

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_PATH_RE = re.compile(r"(?:^|[\s=])(?:/|~[/\\]|[A-Za-z]:[\\/]|\\\\)")
_UNSAFE_METADATA_RE = re.compile(
    r"raw[_ -]?(?:query|prompt|response|answer)"
    r"|normalized[_ -]?query"
    r"|prompt"
    r"|response"
    r"|answer"
    r"|provider[_ -]?payload"
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
    r"|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
    r"|\+?\d[\d ()-]{7,}\d"
    r"|healthkit"
    r"|diagnosis"
    r"|symptom"
    r"|medical"
    r"|account[_ -]?(?:id|truth)"
    r"|billing"
    r"|entitlement"
    r"|legal"
    r"|compliance"
    r"|advisory[_ -]?wiki"
    r"|workforce[_ -]?memory"
    r"|coaching[_ -]?state"
    r"|user[_ -]?health",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BoundedInsightExperimentFlags:
    """Explicit fail-closed flags for the bounded SC-G4 experiment."""

    environment_enabled: bool
    runtime_enabled: bool
    request_opt_in: bool
    request_disable: bool
    kill_switch_snapshot: KillSwitchSnapshot

    def __post_init__(self) -> None:
        _validate_bool("environment_enabled", self.environment_enabled)
        _validate_bool("runtime_enabled", self.runtime_enabled)
        _validate_bool("request_opt_in", self.request_opt_in)
        _validate_bool("request_disable", self.request_disable)
        if not isinstance(self.kill_switch_snapshot, KillSwitchSnapshot):
            raise ValueError("kill_switch_snapshot must be KillSwitchSnapshot")


@dataclass(frozen=True)
class BoundedInsightExperimentRequest:
    """Safe request metadata for the bounded `/insight` experiment."""

    surface: str
    request_fingerprint: str
    context_fingerprint: str
    source_fingerprints: tuple[str, ...]
    policy_version: str
    provider_key: str
    model_key: str
    user_tier: str
    transparency_notice_id: str
    eval_event_ids: tuple[str, ...]
    admission_decision_id: str | None
    promotion_ids: tuple[str, ...]
    replay_entry_ids: tuple[str, ...]
    safety_flags: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "surface", _validate_token("surface", self.surface))
        object.__setattr__(
            self,
            "request_fingerprint",
            _validate_token("request_fingerprint", self.request_fingerprint),
        )
        object.__setattr__(
            self,
            "context_fingerprint",
            _validate_token("context_fingerprint", self.context_fingerprint),
        )
        object.__setattr__(
            self,
            "source_fingerprints",
            _normalize_required_unique_tokens("source_fingerprints", self.source_fingerprints),
        )
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        object.__setattr__(self, "provider_key", _validate_token("provider_key", self.provider_key))
        object.__setattr__(self, "model_key", _validate_token("model_key", self.model_key))
        object.__setattr__(self, "user_tier", _validate_token("user_tier", self.user_tier))
        object.__setattr__(
            self,
            "transparency_notice_id",
            _validate_token("transparency_notice_id", self.transparency_notice_id),
        )
        object.__setattr__(
            self,
            "eval_event_ids",
            _normalize_required_unique_tokens("eval_event_ids", self.eval_event_ids),
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
            "safety_flags",
            _normalize_required_unique_tokens("safety_flags", self.safety_flags),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class BoundedInsightExperimentCandidate:
    """Candidate metadata from SC-G2/SC-G3 contracts, never a cached payload."""

    lookup_request: ExactFuzzyCacheLookupRequest
    lookup_result: ExactFuzzyCacheLookupResult
    record: ExactFuzzyCacheRecord
    audit_event: CacheLookupAuditEvent
    false_hit_evaluation: FalseHitHarnessEvaluation
    metrics: CacheObservabilityMetrics
    stop_decision: CacheStopDecision
    response_fingerprint: str
    blocked_surface: bool
    admission_allowed: bool
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        if not isinstance(self.lookup_request, ExactFuzzyCacheLookupRequest):
            raise ValueError("lookup_request must be ExactFuzzyCacheLookupRequest")
        if not isinstance(self.lookup_result, ExactFuzzyCacheLookupResult):
            raise ValueError("lookup_result must be ExactFuzzyCacheLookupResult")
        if not isinstance(self.record, ExactFuzzyCacheRecord):
            raise ValueError("record must be ExactFuzzyCacheRecord")
        if not isinstance(self.audit_event, CacheLookupAuditEvent):
            raise ValueError("audit_event must be CacheLookupAuditEvent")
        if not isinstance(self.false_hit_evaluation, FalseHitHarnessEvaluation):
            raise ValueError("false_hit_evaluation must be FalseHitHarnessEvaluation")
        if not isinstance(self.metrics, CacheObservabilityMetrics):
            raise ValueError("metrics must be CacheObservabilityMetrics")
        if not isinstance(self.stop_decision, CacheStopDecision):
            raise ValueError("stop_decision must be CacheStopDecision")
        object.__setattr__(
            self,
            "response_fingerprint",
            _validate_token("response_fingerprint", self.response_fingerprint),
        )
        _validate_bool("blocked_surface", self.blocked_surface)
        _validate_bool("admission_allowed", self.admission_allowed)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class BoundedInsightExperimentDecision:
    """Safe metadata-only decision for SC-G4 eligibility."""

    decision_id: str
    decision: str
    surface: str
    candidate_record_id: str | None
    response_fingerprint: str | None
    match_mode: str | None
    score_bps: int | None
    request_fingerprint: str
    source_fingerprints: tuple[str, ...]
    policy_version: str
    provider_key: str
    model_key: str
    user_tier: str
    context_fingerprint: str
    transparency_notice_id: str
    eval_event_ids: tuple[str, ...]
    admission_decision_id: str | None
    promotion_ids: tuple[str, ...]
    replay_entry_ids: tuple[str, ...]
    safety_flags: tuple[str, ...]
    reason_codes: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _validate_token("decision_id", self.decision_id))
        if self.decision not in {DECISION_EXPERIMENT_ELIGIBLE, DECISION_FALLBACK}:
            raise ValueError(f"unsupported decision: {self.decision!r}")
        object.__setattr__(self, "surface", _validate_token("surface", self.surface))
        if self.candidate_record_id is not None:
            object.__setattr__(
                self,
                "candidate_record_id",
                _validate_token("candidate_record_id", self.candidate_record_id),
            )
        if self.response_fingerprint is not None:
            object.__setattr__(
                self,
                "response_fingerprint",
                _validate_token("response_fingerprint", self.response_fingerprint),
            )
        if self.match_mode is not None:
            object.__setattr__(self, "match_mode", _validate_token("match_mode", self.match_mode))
        if self.score_bps is not None:
            _validate_bps("score_bps", self.score_bps)
        object.__setattr__(
            self,
            "request_fingerprint",
            _validate_token("request_fingerprint", self.request_fingerprint),
        )
        object.__setattr__(
            self,
            "source_fingerprints",
            _normalize_required_unique_tokens("source_fingerprints", self.source_fingerprints),
        )
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
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
            "eval_event_ids",
            _normalize_required_unique_tokens("eval_event_ids", self.eval_event_ids),
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
            "safety_flags",
            _normalize_required_unique_tokens("safety_flags", self.safety_flags),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


def evaluate_bounded_insight_experiment(
    *,
    flags: BoundedInsightExperimentFlags,
    request: BoundedInsightExperimentRequest,
    candidate: BoundedInsightExperimentCandidate | None,
) -> BoundedInsightExperimentDecision:
    """Evaluate SC-G4 experiment eligibility without serving cached output."""

    if not isinstance(flags, BoundedInsightExperimentFlags):
        raise ValueError("flags must be BoundedInsightExperimentFlags")
    if not isinstance(request, BoundedInsightExperimentRequest):
        raise ValueError("request must be BoundedInsightExperimentRequest")

    reasons = _flag_reasons(flags)
    if request.surface != ALLOWED_SURFACE:
        reasons.append(REASON_UNSUPPORTED_SURFACE)
    if _is_missing_evidence_linkage(request):
        reasons.append(REASON_EVIDENCE_LINKAGE_MISSING)

    if candidate is None:
        reasons.append(REASON_CANDIDATE_MISSING)
        return _build_decision(request=request, candidate=None, reasons=reasons)
    if not isinstance(candidate, BoundedInsightExperimentCandidate):
        raise ValueError("candidate must be BoundedInsightExperimentCandidate")

    reasons.extend(_candidate_reasons(request=request, candidate=candidate))
    return _build_decision(request=request, candidate=candidate, reasons=reasons)


def to_stable_mapping(value: object) -> Mapping[str, JsonValue]:
    """Return deterministic safe JSON-ready mappings for SC-G4 contracts."""

    if isinstance(value, BoundedInsightExperimentDecision):
        return _stable_json_mapping(
            {
                "admission_decision_id": value.admission_decision_id,
                "candidate_record_id": value.candidate_record_id,
                "context_fingerprint": value.context_fingerprint,
                "decision": value.decision,
                "decision_id": value.decision_id,
                "eval_event_ids": list(value.eval_event_ids),
                "match_mode": value.match_mode,
                "metadata": _json_safe_copy(value.metadata),
                "model_key": value.model_key,
                "policy_version": value.policy_version,
                "promotion_ids": list(value.promotion_ids),
                "provider_key": value.provider_key,
                "reason_codes": list(value.reason_codes),
                "replay_entry_ids": list(value.replay_entry_ids),
                "request_fingerprint": value.request_fingerprint,
                "response_fingerprint": value.response_fingerprint,
                "safety_flags": list(value.safety_flags),
                "score_bps": value.score_bps,
                "source_fingerprints": list(value.source_fingerprints),
                "surface": value.surface,
                "transparency_notice_id": value.transparency_notice_id,
                "user_tier": value.user_tier,
            }
        )
    if isinstance(value, BoundedInsightExperimentFlags):
        return _stable_json_mapping(
            {
                "environment_enabled": value.environment_enabled,
                "kill_switch_snapshot": _json_safe_copy(
                    dict(
                        {
                            "bypass_forced": value.kill_switch_snapshot.bypass_forced,
                            "environment_enabled": value.kill_switch_snapshot.environment_enabled,
                            "request_disabled": value.kill_switch_snapshot.request_disabled,
                            "runtime_enabled": value.kill_switch_snapshot.runtime_enabled,
                        }
                    )
                ),
                "request_disable": value.request_disable,
                "request_opt_in": value.request_opt_in,
                "runtime_enabled": value.runtime_enabled,
            }
        )
    raise ValueError(f"unsupported stable mapping value: {type(value).__name__}")


def _flag_reasons(flags: BoundedInsightExperimentFlags) -> list[str]:
    reasons: list[str] = []
    if not flags.environment_enabled:
        reasons.append(REASON_ENVIRONMENT_FLAG_DISABLED)
    if not flags.runtime_enabled:
        reasons.append(REASON_RUNTIME_FLAG_DISABLED)
    if not flags.request_opt_in:
        reasons.append(REASON_REQUEST_NOT_OPTED_IN)
    if flags.request_disable:
        reasons.append(REASON_REQUEST_DISABLED)
    if flags.kill_switch_snapshot.disables_hypothetical_serving:
        reasons.append(REASON_KILL_SWITCH_DISABLED)
    return reasons


def _candidate_reasons(
    *,
    request: BoundedInsightExperimentRequest,
    candidate: BoundedInsightExperimentCandidate,
) -> list[str]:
    reasons: list[str] = []
    if candidate.lookup_result.decision != MATCH_DECISION_HIT:
        reasons.append(REASON_LOOKUP_MISS)
    if candidate.lookup_result.matched_record_id != candidate.record.record_id:
        reasons.append(REASON_MATCHED_RECORD_MISMATCH)
    if candidate.record.response_fingerprint != candidate.response_fingerprint:
        reasons.append(REASON_RESPONSE_FINGERPRINT_MISMATCH)
    if candidate.audit_event.candidate_record_id != candidate.record.record_id:
        reasons.append(REASON_MATCHED_RECORD_MISMATCH)
    if candidate.audit_event.candidate_response_fingerprint != candidate.response_fingerprint:
        reasons.append(REASON_RESPONSE_FINGERPRINT_MISMATCH)
    if candidate.audit_event.request_fingerprint != request.request_fingerprint:
        reasons.append(REASON_REQUEST_FINGERPRINT_MISMATCH)
    if (
        candidate.lookup_request.surface != request.surface
        or candidate.record.surface != request.surface
    ):
        reasons.append(REASON_UNSUPPORTED_SURFACE)
    if (
        candidate.lookup_request.source_fingerprints != request.source_fingerprints
        or candidate.record.lineage.source_fingerprints != request.source_fingerprints
        or candidate.audit_event.source_fingerprints != request.source_fingerprints
    ):
        reasons.append(REASON_SOURCE_FINGERPRINT_MISMATCH)
    if (
        candidate.lookup_request.policy_version != request.policy_version
        or candidate.record.lineage.policy_version != request.policy_version
        or candidate.audit_event.policy_version != request.policy_version
    ):
        reasons.append(REASON_POLICY_MISMATCH)
    if (
        candidate.lookup_request.provider_key != request.provider_key
        or candidate.record.provider_key != request.provider_key
        or candidate.audit_event.provider_key != request.provider_key
    ):
        reasons.append(REASON_PROVIDER_MISMATCH)
    if (
        candidate.lookup_request.model_key != request.model_key
        or candidate.record.model_key != request.model_key
        or candidate.audit_event.model_key != request.model_key
    ):
        reasons.append(REASON_MODEL_MISMATCH)
    if (
        candidate.lookup_request.context_fingerprint != request.context_fingerprint
        or candidate.record.context_fingerprint != request.context_fingerprint
        or candidate.audit_event.context_fingerprint != request.context_fingerprint
    ):
        reasons.append(REASON_CONTEXT_MISMATCH)
    if (
        candidate.lookup_request.user_tier != request.user_tier
        or candidate.record.user_tier != request.user_tier
        or candidate.audit_event.user_tier != request.user_tier
    ):
        reasons.append(REASON_USER_TIER_MISMATCH)
    if (
        candidate.lookup_request.transparency_notice_id != request.transparency_notice_id
        or candidate.record.transparency_notice_id != request.transparency_notice_id
        or candidate.audit_event.transparency_notice_id != request.transparency_notice_id
    ):
        reasons.append(REASON_TRANSPARENCY_NOTICE_MISMATCH)
    if candidate.record.safety_flags != request.safety_flags:
        reasons.append(REASON_SAFETY_FLAGS_MISMATCH)
    if _has_evidence_linkage_mismatch(request=request, candidate=candidate):
        reasons.append(REASON_EVIDENCE_LINKAGE_MISMATCH)
    if not candidate.admission_allowed:
        reasons.append(REASON_ADMISSION_BLOCKED)
    if candidate.blocked_surface:
        reasons.append(REASON_BLOCKED_SURFACE)
    if candidate.false_hit_evaluation.is_false_hit or not candidate.false_hit_evaluation.allowed:
        reasons.append(REASON_FALSE_HIT_BLOCKED)
    if candidate.stop_decision.stop_serving or candidate.stop_decision.rollback_required:
        reasons.append(REASON_STOP_RULE_BLOCKED)
    if _is_missing_candidate_linkage(candidate):
        reasons.append(REASON_EVIDENCE_LINKAGE_MISSING)
    return reasons


def _build_decision(
    *,
    request: BoundedInsightExperimentRequest,
    candidate: BoundedInsightExperimentCandidate | None,
    reasons: list[str],
) -> BoundedInsightExperimentDecision:
    normalized_reasons = _normalize_unique_tokens("reason_codes", list(dict.fromkeys(reasons)))
    decision = DECISION_FALLBACK
    if not normalized_reasons and candidate is not None:
        normalized_reasons = (REASON_EXPERIMENT_ELIGIBLE,)
        decision = DECISION_EXPERIMENT_ELIGIBLE
    eligible_candidate = candidate if decision == DECISION_EXPERIMENT_ELIGIBLE else None
    payload: JsonValue = {
        "candidate_record_id": _eligible_candidate_record_id(eligible_candidate),
        "decision": decision,
        "policy_version": request.policy_version,
        "reason_codes": list(normalized_reasons),
        "request_fingerprint": request.request_fingerprint,
        "surface": request.surface,
    }
    return BoundedInsightExperimentDecision(
        decision_id=f"bounded-insight-cache:{_fingerprint_payload(payload)[:24]}",
        decision=decision,
        surface=request.surface,
        candidate_record_id=_eligible_candidate_record_id(eligible_candidate),
        response_fingerprint=_eligible_candidate_response_fingerprint(eligible_candidate),
        match_mode=_eligible_match_mode(eligible_candidate),
        score_bps=_eligible_score_bps(eligible_candidate),
        request_fingerprint=request.request_fingerprint,
        source_fingerprints=request.source_fingerprints,
        policy_version=request.policy_version,
        provider_key=request.provider_key,
        model_key=request.model_key,
        user_tier=request.user_tier,
        context_fingerprint=request.context_fingerprint,
        transparency_notice_id=request.transparency_notice_id,
        eval_event_ids=request.eval_event_ids,
        admission_decision_id=request.admission_decision_id,
        promotion_ids=request.promotion_ids,
        replay_entry_ids=request.replay_entry_ids,
        safety_flags=request.safety_flags,
        reason_codes=normalized_reasons,
        metadata={"decision_scope": "metadata_only", "serves_cached_payload": False},
    )


def _has_bound_hit_candidate(candidate: BoundedInsightExperimentCandidate | None) -> bool:
    return (
        candidate is not None
        and candidate.lookup_result.decision == MATCH_DECISION_HIT
        and candidate.lookup_result.matched_record_id == candidate.record.record_id
        and candidate.response_fingerprint == candidate.record.response_fingerprint
        and candidate.audit_event.candidate_record_id == candidate.record.record_id
        and candidate.audit_event.candidate_response_fingerprint == candidate.response_fingerprint
    )


def _eligible_candidate_record_id(
    candidate: BoundedInsightExperimentCandidate | None,
) -> str | None:
    if candidate is None or not _has_bound_hit_candidate(candidate):
        return None
    record_id: str = candidate.record.record_id
    return record_id


def _eligible_candidate_response_fingerprint(
    candidate: BoundedInsightExperimentCandidate | None,
) -> str | None:
    if candidate is None or not _has_bound_hit_candidate(candidate):
        return None
    return candidate.response_fingerprint


def _eligible_match_mode(candidate: BoundedInsightExperimentCandidate | None) -> str | None:
    if candidate is None or not _has_bound_hit_candidate(candidate):
        return None
    match_mode: str | None = candidate.lookup_result.match_mode
    return match_mode


def _eligible_score_bps(candidate: BoundedInsightExperimentCandidate | None) -> int | None:
    if candidate is None or not _has_bound_hit_candidate(candidate):
        return None
    score_bps: int | None = candidate.lookup_result.score_bps
    return score_bps


def _is_missing_evidence_linkage(request: BoundedInsightExperimentRequest) -> bool:
    return (
        request.admission_decision_id is None
        or not request.eval_event_ids
        or not request.promotion_ids
        or not request.replay_entry_ids
        or not request.source_fingerprints
        or not request.safety_flags
    )


def _is_missing_candidate_linkage(candidate: BoundedInsightExperimentCandidate) -> bool:
    lineage = candidate.record.lineage
    return (
        lineage.admission_decision_id is None
        or not lineage.eval_event_ids
        or not lineage.promotion_ids
        or not lineage.replay_entry_ids
        or not lineage.source_fingerprints
        or candidate.audit_event.admission_decision_id is None
        or not candidate.audit_event.eval_event_ids
        or not candidate.audit_event.promotion_ids
        or not candidate.audit_event.replay_entry_ids
    )


def _has_evidence_linkage_mismatch(
    *,
    request: BoundedInsightExperimentRequest,
    candidate: BoundedInsightExperimentCandidate,
) -> bool:
    lineage = candidate.record.lineage
    audit_event = candidate.audit_event
    mismatches = (
        bool(lineage.eval_event_ids != request.eval_event_ids),
        bool(lineage.admission_decision_id != request.admission_decision_id),
        bool(lineage.promotion_ids != request.promotion_ids),
        bool(lineage.replay_entry_ids != request.replay_entry_ids),
        bool(audit_event.eval_event_ids != request.eval_event_ids),
        bool(audit_event.admission_decision_id != request.admission_decision_id),
        bool(audit_event.promotion_ids != request.promotion_ids),
        bool(audit_event.replay_entry_ids != request.replay_entry_ids),
    )
    return any(mismatches)


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
    return MappingProxyType({key: _freeze_json_value(item) for key, item in sorted(value.items())})


def _freeze_json_value(value: JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _stable_json_mapping(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    return {key: _json_safe_copy(item) for key, item in sorted(value.items())}


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


def _normalize_required_unique_tokens(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = _normalize_unique_tokens(name, values)
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _normalize_unique_tokens(name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
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
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    return normalized


def _validate_bps(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0 or value > 10000:
        raise ValueError(f"{name} must be between 0 and 10000")


def _validate_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be bool")

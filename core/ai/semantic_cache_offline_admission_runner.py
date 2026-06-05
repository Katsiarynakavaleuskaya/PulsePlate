"""Offline semantic-cache admission runner report composition.

This module is an internal governance composer only. It reuses the existing
SC-G2/SC-G3/SC-G4/SC-G5 pure contracts, emits redacted metadata, and never
serves or stores cached payloads.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import TypeAlias

import core.ai.bounded_insight_semantic_cache as sc_g4
import core.ai.cache_observability as sc_g3
import core.ai.exact_fuzzy_cache as sc_g2
import core.ai.semantic_cache_backend_selection as sc_g5

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

REPORT_ID = "semantic_cache_offline_admission_runner_report"
REPORT_VERSION = "2026-06-05"
GENERATED_AT = "static-2026-06-05"
SCHEMA_VERSION = "1.0"
SCOPE = "internal_only_semantic_cache_offline_admission_runner"
GENERATION_MODE = "deterministic_static_synthetic_redacted_inputs"
SEMANTIC_CACHE_GATE_STATUS = "closed"
DEFAULT_PRODUCED_AT = "2026-06-05T00:00:00Z"
DEFAULT_POLICY_VERSION = "semantic-cache-offline-admission-v1"
DEFAULT_SURFACE = "insight"
DEFAULT_CONTEXT_FINGERPRINT = "sha256:context-offline"
DEFAULT_SOURCE_FINGERPRINTS = ("sha256:source-offline-a", "sha256:source-offline-b")
DEFAULT_PROVIDER_KEY = "provider:offline"
DEFAULT_MODEL_KEY = "model:offline"
DEFAULT_USER_TIER = "pro"
DEFAULT_TRANSPARENCY_NOTICE_ID = "notice:semantic-cache-offline:v1"
DEFAULT_RESPONSE_FINGERPRINT = "sha256:response-offline"
DEFAULT_SAFETY_FLAGS = ("wellness-only", "redacted-metadata-only")
DEFAULT_CURRENT_HEAD_SHA = "d91b58100"

SCENARIO_IDS: tuple[str, ...] = (
    "exact_safe_hit",
    "reordered_token_fuzzy_hit",
    "near_duplicate_fuzzy_hit",
    "stale_source_negative_control",
    "policy_mismatch_negative_control",
    "model_mismatch_negative_control",
    "tier_mismatch_negative_control",
    "context_leakage_negative_control",
    "admission_blocked_candidate",
    "blocked_surface_candidate",
    "kill_switch_request_disabled",
    "lookup_miss_fallback",
)
PHASE_IDS: tuple[str, ...] = (
    "sc_g2_exact_fuzzy",
    "sc_g3_observability_false_hit",
    "sc_g4_bounded_insight",
    "sc_g5_backend_label_context",
)
SOURCE_IDS: Mapping[str, str] = MappingProxyType(
    {
        "sc_g2": "core/ai/exact_fuzzy_cache.py",
        "sc_g3": "core/ai/cache_observability.py",
        "sc_g4": "core/ai/bounded_insight_semantic_cache.py",
        "sc_g5": "core/ai/semantic_cache_backend_selection.py",
        "semantic_cache_gate": "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
    }
)
AUTHORITY_FALSE_KEYS: tuple[str, ...] = (
    "public_api_changed",
    "openapi_changed",
    "db_persistence_changed",
    "provider_changed",
    "frontend_or_ios_changed",
    "runtime_authority_changed",
    "runtime_allowed",
    "implementation_allowed",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
    "semantic_cache_runtime_allowed",
    "semantic_cache_implementation_allowed",
    "slack_or_operator_authority_allowed",
    "graphrag_allowed",
)
REDACTION_ASSERTION_KEYS: tuple[str, ...] = (
    "raw_prompt_absent",
    "raw_query_absent",
    "normalized_query_absent",
    "raw_context_absent",
    "raw_answer_absent",
    "raw_response_absent",
    "provider_payloads_absent",
    "local_paths_absent",
    "secrets_absent",
    "slack_ids_absent",
    "workflow_logs_absent",
    "provider_logs_absent",
    "operator_artifacts_absent",
    "health_data_absent",
    "user_data_absent",
)

_PRODUCED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_PREFIX_RE = re.compile(r"^sha256:[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class SemanticCacheOfflineAdmissionInput:
    """Explicit input for deterministic offline runner composition."""

    produced_at: str
    scenario_ids: tuple[str, ...] = SCENARIO_IDS

    def __post_init__(self) -> None:
        object.__setattr__(self, "produced_at", _validate_produced_at(self.produced_at))
        object.__setattr__(
            self,
            "scenario_ids",
            _normalize_scenario_ids(self.scenario_ids),
        )


@dataclass(frozen=True)
class SemanticCacheOfflineAdmissionReport:
    """Redacted, metadata-only report assembled from SC-G2 through SC-G5."""

    schema_version: str
    report_id: str
    report_version: str
    generated_at: str
    scope: str
    generation_mode: str
    source_ids: Mapping[str, JsonValue]
    authority_flags: Mapping[str, JsonValue]
    phase_results: tuple[Mapping[str, JsonValue], ...]
    scenario_results: tuple[Mapping[str, JsonValue], ...]
    backend_label_context: Mapping[str, JsonValue]
    final_admission_decision: Mapping[str, JsonValue]
    redaction_assertions: Mapping[str, JsonValue]
    source_refs: tuple[Mapping[str, JsonValue], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "schema_version", _validate_token("schema_version", self.schema_version)
        )
        object.__setattr__(self, "report_id", _validate_token("report_id", self.report_id))
        object.__setattr__(
            self, "report_version", _validate_token("report_version", self.report_version)
        )
        object.__setattr__(self, "generated_at", _validate_token("generated_at", self.generated_at))
        object.__setattr__(self, "scope", _validate_token("scope", self.scope))
        object.__setattr__(
            self,
            "generation_mode",
            _validate_token("generation_mode", self.generation_mode),
        )
        object.__setattr__(self, "source_ids", _freeze_mapping(self.source_ids))
        object.__setattr__(self, "authority_flags", _freeze_mapping(self.authority_flags))
        object.__setattr__(
            self,
            "phase_results",
            tuple(_freeze_mapping(result) for result in self.phase_results),
        )
        object.__setattr__(
            self,
            "scenario_results",
            tuple(_freeze_mapping(result) for result in self.scenario_results),
        )
        object.__setattr__(
            self,
            "backend_label_context",
            _freeze_mapping(self.backend_label_context),
        )
        object.__setattr__(
            self,
            "final_admission_decision",
            _freeze_mapping(self.final_admission_decision),
        )
        object.__setattr__(
            self,
            "redaction_assertions",
            _freeze_mapping(self.redaction_assertions),
        )
        object.__setattr__(
            self,
            "source_refs",
            tuple(_freeze_mapping(ref) for ref in self.source_refs),
        )


@dataclass(frozen=True)
class _ScenarioSpec:
    scenario_id: str
    record_text: str
    request_text: str
    expected_action: str
    risk_class: str
    negative_control: bool
    current_source_fingerprints: tuple[str, ...] = DEFAULT_SOURCE_FINGERPRINTS
    current_policy_version: str = DEFAULT_POLICY_VERSION
    current_model_key: str = DEFAULT_MODEL_KEY
    current_user_tier: str = DEFAULT_USER_TIER
    current_context_fingerprint: str = DEFAULT_CONTEXT_FINGERPRINT
    admission_allowed: bool = True
    blocked_surface: bool = False
    fresh_response_fingerprint: str | None = DEFAULT_RESPONSE_FINGERPRINT
    request_disable: bool = False
    kill_switch_snapshot: sc_g3.KillSwitchSnapshot = sc_g3.KillSwitchSnapshot(
        True,
        True,
        False,
        False,
    )
    omit_candidates: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _validate_token("scenario_id", self.scenario_id))


def build_default_semantic_cache_offline_admission_input(
    *,
    produced_at: str = DEFAULT_PRODUCED_AT,
    scenario_ids: Iterable[str] = SCENARIO_IDS,
) -> SemanticCacheOfflineAdmissionInput:
    """Build the deterministic synthetic input used by CI and report rendering."""

    return SemanticCacheOfflineAdmissionInput(
        produced_at=produced_at,
        scenario_ids=tuple(scenario_ids),
    )


def compose_semantic_cache_offline_admission_report(
    input: SemanticCacheOfflineAdmissionInput,
) -> SemanticCacheOfflineAdmissionReport:
    """Compose an offline report without runtime cache authority."""

    if not isinstance(input, SemanticCacheOfflineAdmissionInput):
        raise ValueError("input must be SemanticCacheOfflineAdmissionInput")
    specs = _ordered_specs(input.scenario_ids)
    scenario_results: list[Mapping[str, JsonValue]] = []
    sc_g2_results: list[Mapping[str, JsonValue]] = []
    sc_g3_results: list[Mapping[str, JsonValue]] = []
    sc_g4_results: list[Mapping[str, JsonValue]] = []

    for spec in specs:
        result = _evaluate_scenario(spec=spec, produced_at=input.produced_at)
        scenario_results.append(result["scenario"])
        sc_g2_results.append(result["sc_g2"])
        sc_g3_results.append(result["sc_g3"])
        sc_g4_results.append(result["sc_g4"])

    backend_matrix = _build_backend_label_context()
    backend_context = _backend_label_context(backend_matrix)
    phase_results = (
        _phase_result("sc_g2_exact_fuzzy", scenario_ids=input.scenario_ids, results=sc_g2_results),
        _phase_result(
            "sc_g3_observability_false_hit",
            scenario_ids=input.scenario_ids,
            results=sc_g3_results,
        ),
        _phase_result(
            "sc_g4_bounded_insight",
            scenario_ids=input.scenario_ids,
            results=sc_g4_results,
        ),
        {
            "phase_id": "sc_g5_backend_label_context",
            "scenario_count": len(input.scenario_ids),
            "scenario_ids": list(SCENARIO_IDS),
            "matrix_id": backend_matrix.matrix_id,
            "final_decision": _json_safe_copy(backend_context["final_decision"]),
            "candidate_decisions": _json_safe_copy(backend_context["candidate_decisions"]),
            "cache_read_allowed": False,
            "cache_write_allowed": False,
            "serving_allowed": False,
        },
    )
    return SemanticCacheOfflineAdmissionReport(
        schema_version=SCHEMA_VERSION,
        report_id=REPORT_ID,
        report_version=REPORT_VERSION,
        generated_at=GENERATED_AT,
        scope=SCOPE,
        generation_mode=GENERATION_MODE,
        source_ids=dict(SOURCE_IDS),
        authority_flags=_authority_flags(),
        phase_results=phase_results,
        scenario_results=tuple(scenario_results),
        backend_label_context=backend_context,
        final_admission_decision={
            "decision": "offline_report_only",
            "reason_codes": [
                "semantic_cache_gate_closed",
                "runtime_not_allowed",
                "implementation_not_allowed",
                "manual_gate_required",
            ],
            "semantic_cache_gate_status": SEMANTIC_CACHE_GATE_STATUS,
            "runtime_allowed": False,
            "implementation_allowed": False,
            "cache_read_allowed": False,
            "cache_write_allowed": False,
            "serving_allowed": False,
        },
        redaction_assertions={key: True for key in REDACTION_ASSERTION_KEYS},
        source_refs=_source_refs(),
    )


def to_stable_mapping(report: SemanticCacheOfflineAdmissionReport) -> Mapping[str, JsonValue]:
    """Return a byte-stable JSON-ready mapping for the offline report."""

    if not isinstance(report, SemanticCacheOfflineAdmissionReport):
        raise ValueError("report must be SemanticCacheOfflineAdmissionReport")
    return {
        "schema_version": report.schema_version,
        "report_id": report.report_id,
        "report_version": report.report_version,
        "generated_at": report.generated_at,
        "scope": report.scope,
        "generation_mode": report.generation_mode,
        "source_ids": _json_safe_copy(report.source_ids),
        "authority_flags": _json_safe_copy(report.authority_flags),
        "phase_results": [_json_safe_copy(result) for result in report.phase_results],
        "scenario_results": [_json_safe_copy(result) for result in report.scenario_results],
        "backend_label_context": _json_safe_copy(report.backend_label_context),
        "final_admission_decision": _json_safe_copy(report.final_admission_decision),
        "redaction_assertions": _json_safe_copy(report.redaction_assertions),
        "source_refs": [_json_safe_copy(ref) for ref in report.source_refs],
    }


def _evaluate_scenario(
    *, spec: _ScenarioSpec, produced_at: str
) -> Mapping[str, Mapping[str, JsonValue]]:
    record = _record(spec.record_text)
    lookup_request = _lookup_request(spec.request_text)
    lookup_result = sc_g2.match_exact_fuzzy_records(
        request=lookup_request,
        candidate_records=() if spec.omit_candidates else (record,),
        policy=_policy(),
    )
    candidate_record = record if lookup_result.decision == sc_g2.MATCH_DECISION_HIT else None
    audit_event = sc_g3.build_cache_lookup_audit_event(
        request=lookup_request,
        lookup_result=lookup_result,
        candidate_record=candidate_record,
        produced_at=produced_at,
        metadata={"scenario": spec.scenario_id, "scope": "offline_runner"},
    )
    false_hit_case = sc_g3.FalseHitHarnessCase(
        case_id=f"case:{spec.scenario_id}",
        risk_class=spec.risk_class,
        audit_event=audit_event,
        expected_action=spec.expected_action,
        fresh_response_fingerprint=spec.fresh_response_fingerprint,
        current_source_fingerprints=spec.current_source_fingerprints,
        current_policy_version=spec.current_policy_version,
        current_model_key=spec.current_model_key,
        current_user_tier=spec.current_user_tier,
        current_context_fingerprint=spec.current_context_fingerprint,
        admission_allowed=spec.admission_allowed,
        blocked_surface=spec.blocked_surface,
        negative_control=spec.negative_control,
        metadata={"scenario": spec.scenario_id, "scope": "offline_runner"},
    )
    false_hit_evaluation = sc_g3.evaluate_false_hit_case(
        case=false_hit_case,
        produced_at=produced_at,
        kill_switch_snapshot=spec.kill_switch_snapshot,
    )
    metrics = sc_g3.compute_cache_observability_metrics(
        evaluations=(false_hit_evaluation,),
        produced_at=produced_at,
        bypass_count=1 if spec.omit_candidates else 0,
        kill_switch_disabled_count=(
            1 if spec.kill_switch_snapshot.disables_hypothetical_serving else 0
        ),
    )
    stop_decision = sc_g3.evaluate_cache_stop_rules(
        metrics=metrics,
        stop_rules=sc_g3.CacheStopRules(
            policy_version=DEFAULT_POLICY_VERSION,
            max_false_hit_rate_bps=0,
            max_stale_answer_rate_bps=0,
            max_policy_mismatch_hits=0,
            max_model_mismatch_hits=0,
            max_context_leakage_hits=0,
            allow_blocked_surface_hits=False,
        ),
        produced_at=produced_at,
    )
    bounded_request = _bounded_request(audit_event)
    bounded_candidate = (
        None
        if candidate_record is None
        else sc_g4.BoundedInsightExperimentCandidate(
            lookup_request=lookup_request,
            lookup_result=lookup_result,
            record=record,
            audit_event=audit_event,
            false_hit_evaluation=false_hit_evaluation,
            metrics=metrics,
            stop_decision=stop_decision,
            response_fingerprint=record.response_fingerprint,
            blocked_surface=spec.blocked_surface,
            admission_allowed=spec.admission_allowed,
            metadata={"scenario": spec.scenario_id, "scope": "offline_runner"},
        )
    )
    bounded_decision = sc_g4.evaluate_bounded_insight_experiment(
        flags=sc_g4.BoundedInsightExperimentFlags(
            environment_enabled=True,
            runtime_enabled=True,
            request_opt_in=True,
            request_disable=spec.request_disable,
            kill_switch_snapshot=spec.kill_switch_snapshot,
        ),
        request=bounded_request,
        candidate=bounded_candidate,
    )
    sc_g2_result = _safe_sc_g2_result(
        scenario_id=spec.scenario_id,
        lookup_result=lookup_result,
        audit_event=audit_event,
    )
    sc_g3_result = _safe_sc_g3_result(
        scenario_id=spec.scenario_id,
        audit_event=audit_event,
        evaluation=false_hit_evaluation,
        metrics=metrics,
        stop_decision=stop_decision,
    )
    sc_g4_result = _safe_sc_g4_result(
        scenario_id=spec.scenario_id,
        decision=bounded_decision,
    )
    scenario = {
        "scenario_id": spec.scenario_id,
        "risk_class": spec.risk_class,
        "expected_action": spec.expected_action,
        "record_id": record.record_id,
        "request_fingerprint": audit_event.request_fingerprint,
        "response_fingerprint": record.response_fingerprint,
        "source_fingerprints": list(audit_event.source_fingerprints),
        "policy_version": audit_event.policy_version,
        "provider_key": audit_event.provider_key,
        "model_key": audit_event.model_key,
        "user_tier": audit_event.user_tier,
        "context_fingerprint": audit_event.context_fingerprint,
        "transparency_notice_id": audit_event.transparency_notice_id,
        "lookup_decision": lookup_result.decision,
        "match_mode": lookup_result.match_mode,
        "score_bps": lookup_result.score_bps,
        "audit_event_id": audit_event.audit_event_id,
        "false_hit_outcome": false_hit_evaluation.outcome_class,
        "false_hit_allowed": false_hit_evaluation.allowed,
        "false_hit_is_false_hit": false_hit_evaluation.is_false_hit,
        "false_hit_reason_codes": list(false_hit_evaluation.reason_codes),
        "false_hit_blocking_reasons": list(false_hit_evaluation.blocking_reasons),
        "metrics_id": metrics.metrics_id,
        "stop_serving": stop_decision.stop_serving,
        "rollback_required": stop_decision.rollback_required,
        "stop_reason_codes": list(stop_decision.reason_codes),
        "bounded_decision": bounded_decision.decision,
        "bounded_decision_id": bounded_decision.decision_id,
        "bounded_reason_codes": list(bounded_decision.reason_codes),
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }
    return {
        "scenario": scenario,
        "sc_g2": sc_g2_result,
        "sc_g3": sc_g3_result,
        "sc_g4": sc_g4_result,
    }


def _safe_sc_g2_result(
    *,
    scenario_id: str,
    lookup_result: sc_g2.ExactFuzzyCacheLookupResult,
    audit_event: sc_g3.CacheLookupAuditEvent,
) -> Mapping[str, JsonValue]:
    return {
        "scenario_id": scenario_id,
        "lookup_decision": lookup_result.decision,
        "matched_record_id": lookup_result.matched_record_id,
        "match_mode": lookup_result.match_mode,
        "score_bps": lookup_result.score_bps,
        "checked_record_count": lookup_result.checked_record_count,
        "request_fingerprint": audit_event.request_fingerprint,
        "reason_codes": list(lookup_result.reason_codes),
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _safe_sc_g3_result(
    *,
    scenario_id: str,
    audit_event: sc_g3.CacheLookupAuditEvent,
    evaluation: sc_g3.FalseHitHarnessEvaluation,
    metrics: sc_g3.CacheObservabilityMetrics,
    stop_decision: sc_g3.CacheStopDecision,
) -> Mapping[str, JsonValue]:
    return {
        "scenario_id": scenario_id,
        "audit_event_id": audit_event.audit_event_id,
        "evaluation_id": evaluation.evaluation_id,
        "metrics_id": metrics.metrics_id,
        "stop_decision_id": stop_decision.decision_id,
        "outcome_class": evaluation.outcome_class,
        "allowed": evaluation.allowed,
        "is_false_hit": evaluation.is_false_hit,
        "blocking_reasons": list(evaluation.blocking_reasons),
        "false_hit_rate_bps": metrics.false_hit_rate_bps,
        "fallback_rate_bps": metrics.fallback_rate_bps,
        "stop_serving": stop_decision.stop_serving,
        "rollback_required": stop_decision.rollback_required,
        "reason_codes": list(evaluation.reason_codes),
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _safe_sc_g4_result(
    *,
    scenario_id: str,
    decision: sc_g4.BoundedInsightExperimentDecision,
) -> Mapping[str, JsonValue]:
    mapping = dict(sc_g4.to_stable_mapping(decision))
    return {
        "scenario_id": scenario_id,
        "decision_id": mapping["decision_id"],
        "decision": mapping["decision"],
        "candidate_record_id": mapping["candidate_record_id"],
        "match_mode": mapping["match_mode"],
        "score_bps": mapping["score_bps"],
        "reason_codes": mapping["reason_codes"],
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _phase_result(
    phase_id: str,
    *,
    scenario_ids: tuple[str, ...],
    results: list[Mapping[str, JsonValue]],
) -> Mapping[str, JsonValue]:
    return {
        "phase_id": phase_id,
        "scenario_count": len(scenario_ids),
        "scenario_ids": list(SCENARIO_IDS),
        "results": [_json_safe_copy(result) for result in results],
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _build_backend_label_context() -> sc_g5.SemanticCacheBackendEvaluationMatrix:
    criteria = sc_g5.SemanticCacheBackendSelectionCriteria(
        policy_version="semantic-cache-sc-g5-v1",
        allowed_backend_labels=(
            sc_g5.BACKEND_LABEL_IN_MEMORY,
            sc_g5.BACKEND_LABEL_REDIS,
            sc_g5.BACKEND_LABEL_GPTCACHE,
        ),
        required_surface=DEFAULT_SURFACE,
        max_false_hit_rate_bps=0,
        max_stale_answer_rate_bps=0,
        max_policy_mismatch_count=0,
        max_model_mismatch_count=0,
        max_context_leakage_count=0,
        allow_admission_blocked_hits=False,
        allow_blocked_surface_hits=False,
        min_negative_control_count=10,
        min_fresh_runtime_comparison_count=10,
        require_current_head_ci=True,
        current_head_sha=DEFAULT_CURRENT_HEAD_SHA,
        require_human_approval=True,
        runtime_allowed=False,
        implementation_allowed=False,
    )
    candidates = tuple(
        _backend_candidate(candidate_id=candidate_id, backend_label=backend_label)
        for candidate_id, backend_label in (
            ("candidate:in-memory", sc_g5.BACKEND_LABEL_IN_MEMORY),
            ("candidate:redis", sc_g5.BACKEND_LABEL_REDIS),
            ("candidate:gptcache", sc_g5.BACKEND_LABEL_GPTCACHE),
        )
    )
    return sc_g5.evaluate_semantic_cache_backend_matrix(candidates=candidates, criteria=criteria)


def _backend_candidate(
    *, candidate_id: str, backend_label: str
) -> sc_g5.SemanticCacheBackendCandidate:
    backend_token = backend_label.removesuffix("_label").replace("_", "-")
    return sc_g5.SemanticCacheBackendCandidate(
        candidate_id=candidate_id,
        backend_label=backend_label,
        backend_version="label:v1",
        policy_version="semantic-cache-sc-g5-v1",
        supported_surfaces=(DEFAULT_SURFACE,),
        capability_flags=("label-only", "offline-contract"),
        safety_evidence=sc_g5.SemanticCacheBackendSafetyEvidence(
            evidence_id=f"evidence:{backend_token}:offline",
            sc_g2_contract_id=sc_g5.REQUIRED_SC_G2_CONTRACT_ID,
            sc_g3_contract_id=sc_g5.REQUIRED_SC_G3_CONTRACT_ID,
            sc_g4_contract_id=sc_g5.REQUIRED_SC_G4_CONTRACT_ID,
            source_fingerprints=DEFAULT_SOURCE_FINGERPRINTS,
            eval_event_ids=("eval:semantic-cache-offline",),
            admission_decision_id="admission:semantic-cache-offline",
            promotion_ids=("promotion:semantic-cache-offline",),
            replay_entry_ids=("replay:semantic-cache-offline",),
            false_hit_rate_bps=0,
            stale_answer_rate_bps=0,
            policy_mismatch_count=0,
            model_mismatch_count=0,
            context_leakage_count=0,
            admission_blocked_hit_count=0,
            blocked_surface_hit_count=0,
            negative_control_count=12,
            fresh_runtime_comparison_count=12,
            evidence_fingerprints=("sha256:evidence-offline",),
            metadata={"scope": "sc-g5"},
        ),
        rollback_proof=sc_g5.SemanticCacheBackendRollbackProof(
            proof_id=f"rollback:{backend_token}:offline",
            kill_switch_proof_id=f"proof:kill-switch:{backend_token}",
            request_bypass_proof_id=f"proof:bypass:{backend_token}",
            no_cache_fallback_proof_id=f"proof:no-cache:{backend_token}",
            purge_invalidation_proof_id=f"proof:purge:{backend_token}",
            disabled_state_test_ids=(f"test:disabled:{backend_token}",),
            stop_rule_replay_ids=(f"replay:stop-rule:{backend_token}",),
            rollback_runbook_id=f"runbook:rollback:{backend_token}",
            blast_radius_bps=10,
            verified=True,
            metadata={"scope": "sc-g5"},
        ),
        latency_saved_p50_ms=50,
        latency_saved_p95_ms=100,
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        current_head_ci_passed=False,
        current_head_ci_proof_id=None,
        human_approval_record_id=None,
        metadata={"scope": "sc-g5"},
    )


def _backend_label_context(
    matrix: sc_g5.SemanticCacheBackendEvaluationMatrix,
) -> Mapping[str, JsonValue]:
    mapping = dict(sc_g5.to_stable_mapping(matrix))
    final_decision_value = mapping.get("final_decision")
    if not isinstance(final_decision_value, Mapping):
        raise ValueError("backend matrix final_decision must be a mapping")
    candidate_decision_values = mapping.get("candidate_decisions")
    if not isinstance(candidate_decision_values, list):
        raise ValueError("backend matrix candidate_decisions must be a list")
    final_decision = _json_safe_copy(final_decision_value)
    candidate_decisions: list[JsonValue] = []
    for candidate in candidate_decision_values:
        if not isinstance(candidate, Mapping):
            raise ValueError("backend matrix candidate_decisions entries must be mappings")
        candidate_decisions.append(_json_safe_copy(candidate))
    return {
        "matrix_id": mapping["matrix_id"],
        "policy_version": mapping["policy_version"],
        "backend_labels": list(sc_g5.ALLOWED_BACKEND_LABELS),
        "final_decision": final_decision,
        "candidate_decisions": candidate_decisions,
        "runtime_allowed": False,
        "implementation_allowed": False,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _bounded_request(
    audit_event: sc_g3.CacheLookupAuditEvent,
) -> sc_g4.BoundedInsightExperimentRequest:
    eval_event_ids = audit_event.eval_event_ids or ("eval:semantic-cache-offline",)
    promotion_ids = audit_event.promotion_ids or ("promotion:semantic-cache-offline",)
    replay_entry_ids = audit_event.replay_entry_ids or ("replay:semantic-cache-offline",)
    return sc_g4.BoundedInsightExperimentRequest(
        surface=audit_event.surface,
        request_fingerprint=audit_event.request_fingerprint,
        context_fingerprint=audit_event.context_fingerprint,
        source_fingerprints=audit_event.source_fingerprints,
        policy_version=audit_event.policy_version,
        provider_key=audit_event.provider_key,
        model_key=audit_event.model_key,
        user_tier=audit_event.user_tier,
        transparency_notice_id=audit_event.transparency_notice_id,
        eval_event_ids=eval_event_ids,
        admission_decision_id=audit_event.admission_decision_id,
        promotion_ids=promotion_ids,
        replay_entry_ids=replay_entry_ids,
        safety_flags=DEFAULT_SAFETY_FLAGS,
        metadata={"scope": "offline_runner"},
    )


def _record(record_text: str) -> sc_g2.ExactFuzzyCacheRecord:
    return sc_g2.create_exact_fuzzy_cache_record(
        surface=DEFAULT_SURFACE,
        raw_query=record_text,
        context_fingerprint=DEFAULT_CONTEXT_FINGERPRINT,
        provider_key=DEFAULT_PROVIDER_KEY,
        model_key=DEFAULT_MODEL_KEY,
        user_tier=DEFAULT_USER_TIER,
        transparency_notice_id=DEFAULT_TRANSPARENCY_NOTICE_ID,
        lineage=sc_g2.build_exact_fuzzy_lineage(
            eval_event_ids=("eval:semantic-cache-offline",),
            admission_decision_id="admission:semantic-cache-offline",
            promotion_ids=("promotion:semantic-cache-offline",),
            replay_entry_ids=("replay:semantic-cache-offline",),
            source_fingerprints=DEFAULT_SOURCE_FINGERPRINTS,
            policy_version=DEFAULT_POLICY_VERSION,
        ),
        response_fingerprint=DEFAULT_RESPONSE_FINGERPRINT,
        safety_flags=DEFAULT_SAFETY_FLAGS,
    )


def _lookup_request(request_text: str) -> sc_g2.ExactFuzzyCacheLookupRequest:
    return sc_g2.ExactFuzzyCacheLookupRequest(
        surface=DEFAULT_SURFACE,
        raw_query=request_text,
        context_fingerprint=DEFAULT_CONTEXT_FINGERPRINT,
        source_fingerprints=DEFAULT_SOURCE_FINGERPRINTS,
        policy_version=DEFAULT_POLICY_VERSION,
        provider_key=DEFAULT_PROVIDER_KEY,
        model_key=DEFAULT_MODEL_KEY,
        user_tier=DEFAULT_USER_TIER,
        transparency_notice_id=DEFAULT_TRANSPARENCY_NOTICE_ID,
    )


def _policy() -> sc_g2.ExactFuzzyMatchPolicy:
    return sc_g2.ExactFuzzyMatchPolicy(
        policy_version=DEFAULT_POLICY_VERSION,
        token_jaccard_min_bps=5000,
        sequence_ratio_min_bps=7000,
        max_token_count_delta=2,
    )


def _ordered_specs(scenario_ids: tuple[str, ...]) -> tuple[_ScenarioSpec, ...]:
    specs = _scenario_specs()
    return tuple(specs[scenario_id] for scenario_id in SCENARIO_IDS if scenario_id in scenario_ids)


def _scenario_specs() -> Mapping[str, _ScenarioSpec]:
    safe_text = "plan protein breakfast"
    specs = (
        _ScenarioSpec(
            scenario_id="exact_safe_hit",
            record_text=safe_text,
            request_text="PLAN protein breakfast",
            expected_action=sc_g3.EXPECTED_ACTION_SAFE_HIT,
            risk_class=sc_g3.RISK_EXACT_DUPLICATE_HIT,
            negative_control=False,
        ),
        _ScenarioSpec(
            scenario_id="reordered_token_fuzzy_hit",
            record_text=safe_text,
            request_text="breakfast protein plan",
            expected_action=sc_g3.EXPECTED_ACTION_SAFE_HIT,
            risk_class=sc_g3.RISK_NORMALIZED_FUZZY_HIT,
            negative_control=False,
        ),
        _ScenarioSpec(
            scenario_id="near_duplicate_fuzzy_hit",
            record_text="reduce evening cravings with protein snack",
            request_text="reduce evening craving with protein snacks",
            expected_action=sc_g3.EXPECTED_ACTION_SAFE_HIT,
            risk_class=sc_g3.RISK_NORMALIZED_FUZZY_HIT,
            negative_control=False,
        ),
        _ScenarioSpec(
            scenario_id="stale_source_negative_control",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_STALE_SOURCE_HIT,
            negative_control=True,
            current_source_fingerprints=("sha256:source-current",),
        ),
        _ScenarioSpec(
            scenario_id="policy_mismatch_negative_control",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_POLICY_VERSION_MISMATCH_HIT,
            negative_control=True,
            current_policy_version="semantic-cache-offline-admission-v2",
        ),
        _ScenarioSpec(
            scenario_id="model_mismatch_negative_control",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_MODEL_VERSION_MISMATCH_HIT,
            negative_control=True,
            current_model_key="model:offline-next",
        ),
        _ScenarioSpec(
            scenario_id="tier_mismatch_negative_control",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_USER_CONTEXT_LEAKAGE_HIT,
            negative_control=True,
            current_user_tier="free",
        ),
        _ScenarioSpec(
            scenario_id="context_leakage_negative_control",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_USER_CONTEXT_LEAKAGE_HIT,
            negative_control=True,
            current_context_fingerprint="sha256:context-current",
        ),
        _ScenarioSpec(
            scenario_id="admission_blocked_candidate",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_ADMISSION_BLOCKED_HIT,
            negative_control=True,
            admission_allowed=False,
        ),
        _ScenarioSpec(
            scenario_id="blocked_surface_candidate",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_BLOCKED_SURFACE_HIT,
            negative_control=True,
            blocked_surface=True,
        ),
        _ScenarioSpec(
            scenario_id="kill_switch_request_disabled",
            record_text=safe_text,
            request_text=safe_text,
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_SEMANTIC_FALSE_POSITIVE,
            negative_control=True,
            request_disable=True,
            kill_switch_snapshot=sc_g3.KillSwitchSnapshot(True, False, True, True),
        ),
        _ScenarioSpec(
            scenario_id="lookup_miss_fallback",
            record_text=safe_text,
            request_text="plan evening hydration walk",
            expected_action=sc_g3.EXPECTED_ACTION_FALLBACK,
            risk_class=sc_g3.RISK_SEMANTIC_FALSE_POSITIVE,
            negative_control=True,
            omit_candidates=True,
            fresh_response_fingerprint=None,
        ),
    )
    return MappingProxyType({spec.scenario_id: spec for spec in specs})


def _authority_flags() -> Mapping[str, JsonValue]:
    flags: dict[str, JsonValue] = {key: False for key in AUTHORITY_FALSE_KEYS}
    flags["semantic_cache_gate_status"] = SEMANTIC_CACHE_GATE_STATUS
    return flags


def _source_refs() -> tuple[Mapping[str, JsonValue], ...]:
    return (
        {"path": SOURCE_IDS["sc_g2"], "symbol": "match_exact_fuzzy_records"},
        {"path": SOURCE_IDS["sc_g3"], "symbol": "evaluate_false_hit_case"},
        {"path": SOURCE_IDS["sc_g3"], "symbol": "evaluate_cache_stop_rules"},
        {"path": SOURCE_IDS["sc_g4"], "symbol": "evaluate_bounded_insight_experiment"},
        {"path": SOURCE_IDS["sc_g5"], "symbol": "evaluate_semantic_cache_backend_matrix"},
    )


def _normalize_scenario_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    if not values:
        raise ValueError("scenario_ids must be non-empty")
    observed: set[str] = set()
    for value in values:
        token = _validate_token("scenario_id", value)
        if token not in SCENARIO_IDS:
            raise ValueError(f"unsupported scenario_id: {token}")
        if token in observed:
            raise ValueError("scenario_ids contains duplicate entries")
        observed.add(token)
    missing = set(SCENARIO_IDS) - observed
    if missing:
        raise ValueError("scenario_ids must include all default scenarios")
    return tuple(scenario_id for scenario_id in SCENARIO_IDS if scenario_id in observed)


def _validate_token(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized) and not _DIGEST_PREFIX_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    return normalized


def _validate_produced_at(value: str) -> str:
    if not isinstance(value, str) or not _PRODUCED_AT_RE.match(value):
        raise ValueError("produced_at must be an ISO UTC timestamp")
    return value


def _freeze_mapping(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    return MappingProxyType({key: _freeze_json_value(item) for key, item in sorted(value.items())})


def _freeze_json_value(value: JsonValue | Mapping[str, JsonValue]) -> JsonValue:
    if isinstance(value, Mapping):
        return dict(_freeze_mapping(value))
    if isinstance(value, list):
        return [_freeze_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_freeze_json_value(item) for item in value]
    return value


def _json_safe_copy(value: JsonValue | Mapping[str, JsonValue]) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_copy(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_json_safe_copy(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_copy(item) for item in value]
    return value

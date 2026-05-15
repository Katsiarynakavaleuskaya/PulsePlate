"""Offline SC-G5 semantic-cache backend selection contracts.

This module evaluates backend candidate labels for a future semantic-cache
selection decision. It never imports or initializes Redis/GPTCache, never serves
cached answers, and never reads runtime configuration.
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

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = (
    JsonScalar
    | list["JsonValue"]
    | tuple["JsonValue", ...]
    | dict[str, "JsonValue"]
    | Mapping[str, "JsonValue"]
)

BACKEND_LABEL_IN_MEMORY = "in_memory_label"
BACKEND_LABEL_REDIS = "redis_label"
BACKEND_LABEL_GPTCACHE = "gptcache_label"
ALLOWED_BACKEND_LABELS = (
    BACKEND_LABEL_GPTCACHE,
    BACKEND_LABEL_IN_MEMORY,
    BACKEND_LABEL_REDIS,
)

DECISION_ELIGIBLE = "eligible"
DECISION_INELIGIBLE = "ineligible"
DECISION_SELECTED = "selected"
DECISION_NO_SELECTION = "no_selection"

REASON_ELIGIBLE = "eligible"
REASON_SELECTED = "selected"
REASON_BACKEND_LABEL_NOT_ALLOWED = "backend_label_not_allowed"
REASON_RUNTIME_NOT_ALLOWED = "runtime_not_allowed"
REASON_IMPLEMENTATION_NOT_ALLOWED = "implementation_not_allowed"
REASON_SC_G2_EVIDENCE_MISSING = "sc_g2_evidence_missing"
REASON_SC_G3_EVIDENCE_MISSING = "sc_g3_evidence_missing"
REASON_SC_G4_EVIDENCE_MISSING = "sc_g4_evidence_missing"
REASON_FALSE_HIT_RATE_EXCEEDED = "false_hit_rate_exceeded"
REASON_STALE_ANSWER_RATE_EXCEEDED = "stale_answer_rate_exceeded"
REASON_POLICY_MISMATCH_EXCEEDED = "policy_mismatch_exceeded"
REASON_MODEL_MISMATCH_EXCEEDED = "model_mismatch_exceeded"
REASON_CONTEXT_LEAKAGE_EXCEEDED = "context_leakage_exceeded"
REASON_ADMISSION_BLOCKED_HITS = "admission_blocked_hits"
REASON_BLOCKED_SURFACE_HITS = "blocked_surface_hits"
REASON_NEGATIVE_CONTROLS_MISSING = "negative_controls_missing"
REASON_FRESH_RUNTIME_COMPARISONS_MISSING = "fresh_runtime_comparisons_missing"
REASON_ROLLBACK_PROOF_MISSING = "rollback_proof_missing"
REASON_KILL_SWITCH_PROOF_MISSING = "kill_switch_proof_missing"
REASON_PURGE_INVALIDATION_PROOF_MISSING = "purge_invalidation_proof_missing"
REASON_DISABLED_STATE_TEST_MISSING = "disabled_state_test_missing"
REASON_STOP_RULE_REPLAY_MISSING = "stop_rule_replay_missing"
REASON_CURRENT_HEAD_CI_MISSING = "current_head_ci_missing"
REASON_HUMAN_APPROVAL_MISSING = "human_approval_missing"
REASON_NO_ELIGIBLE_CANDIDATE = "no_eligible_candidate"
ALLOWED_REASON_CODES = (
    REASON_ADMISSION_BLOCKED_HITS,
    REASON_BACKEND_LABEL_NOT_ALLOWED,
    REASON_BLOCKED_SURFACE_HITS,
    REASON_CONTEXT_LEAKAGE_EXCEEDED,
    REASON_CURRENT_HEAD_CI_MISSING,
    REASON_ELIGIBLE,
    REASON_FALSE_HIT_RATE_EXCEEDED,
    REASON_FRESH_RUNTIME_COMPARISONS_MISSING,
    REASON_HUMAN_APPROVAL_MISSING,
    REASON_IMPLEMENTATION_NOT_ALLOWED,
    REASON_KILL_SWITCH_PROOF_MISSING,
    REASON_MODEL_MISMATCH_EXCEEDED,
    REASON_NEGATIVE_CONTROLS_MISSING,
    REASON_NO_ELIGIBLE_CANDIDATE,
    REASON_POLICY_MISMATCH_EXCEEDED,
    REASON_ROLLBACK_PROOF_MISSING,
    REASON_RUNTIME_NOT_ALLOWED,
    REASON_PURGE_INVALIDATION_PROOF_MISSING,
    REASON_DISABLED_STATE_TEST_MISSING,
    REASON_SC_G2_EVIDENCE_MISSING,
    REASON_SC_G3_EVIDENCE_MISSING,
    REASON_SC_G4_EVIDENCE_MISSING,
    REASON_SELECTED,
    REASON_STOP_RULE_REPLAY_MISSING,
    REASON_STALE_ANSWER_RATE_EXCEEDED,
)

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_PATH_RE = re.compile(
    r"file://|(?:^|[\s=(:,;])(?:/|~[/\\]|[A-Za-z]:[\\/]|\\\\)",
    re.IGNORECASE,
)
_RELATIVE_PATH_RE = re.compile(r"(?:^|[\s=(:,;])(?:\./|\.\./|[A-Za-z0-9_.-]+[/\\][A-Za-z0-9_.-]+)")
_UNSAFE_TOKEN_RE = re.compile(
    r"secret"
    r"|token"
    r"|jwt"
    r"|credential"
    r"|authorization"
    r"|api[_:-]?key"
    r"|bearer"
    r"|cookie"
    r"|private[_:-]?key"
    r"|password"
    r"|pwd"
    r"|(?<![a-z0-9])sk-[a-z0-9][a-z0-9_-]*"
    r"|ghp_[a-z0-9_]+"
    r"|github_pat_[a-z0-9_]+"
    r"|xox[baprs]-[a-z0-9-]+"
    r"|eyj[a-z0-9_-]*\.[a-z0-9_-]+(?:\.[a-z0-9_-]+)?",
    re.IGNORECASE,
)
_UNSAFE_METADATA_RE = re.compile(
    r"raw[_ -]?(?:queries|query|prompts?|responses?|answers?)"
    r"|normalized[_ -]?(?:queries|query)"
    r"|prompts?"
    r"|responses?"
    r"|answers?"
    r"|provider[_: -]?payloads?"
    r"|connection[_: -]?string"
    r"|local[_: -]?path"
    r"|redis://"
    r"|redis[_ -]?url"
    r"|gptcache"
    r"|secret"
    r"|config"
    r"|environment"
    r"|(?:^|[_: -])(?:access|refresh|id|session|auth)?[_: -]?token(?:$|[_: -])"
    r"|jwt"
    r"|credential"
    r"|authorization"
    r"|api[_: -]?key"
    r"|bearer"
    r"|cookie"
    r"|session[_: -]?id"
    r"|private[_: -]?key"
    r"|password"
    r"|pwd"
    r"|sk-[a-z0-9]"
    r"|ghp_[a-z0-9_]+"
    r"|github_pat_[a-z0-9_]+"
    r"|xox[baprs]-[a-z0-9-]+"
    r"|eyj[a-z0-9_-]*\.[a-z0-9_-]+(?:\.[a-z0-9_-]+)?"
    r"|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
    r"|\+?\d[\d ()-]{7,}\d"
    r"|health[_: -]?kit"
    r"|diagnosis"
    r"|symptom"
    r"|medical"
    r"|personalized[_: -]?coaching[_: -]?state"
    r"|coaching[_: -]?state"
    r"|account[_: -]?(?:id|truth)"
    r"|auth(?:entication)?[_: -]?truth"
    r"|billing"
    r"|entitlement"
    r"|legal"
    r"|compliance"
    r"|advisory[_: -]?wiki"
    r"|workforce[_: -]?memory"
    r"|local[_: -]?support[_: -]?plane"
    r"|plugin[_: -]?control[_: -]?plane"
    r"|second[_: -]?source[_: -]?of[_: -]?truth"
    r"|graphrag"
    r"|knowledge[_: -]?graph",
    re.IGNORECASE,
)
_UNSAFE_EVIDENCE_ID_RE = re.compile(
    r"raw[_:-]?(?:model[_:-]?)?(?:queries|query|prompts?|responses?|answers?)"
    r"|normalized[_:-]?(?:queries|query)"
    r"|provider[_:-]?payloads?"
    r"|connection[_:-]?strings?"
    r"|redis[_:-]?(?:url|uri|dsn)"
    r"|config"
    r"|environment"
    r"|health[_:-]?kit"
    r"|diagnosis"
    r"|symptom"
    r"|medical"
    r"|personalized[_:-]?coaching[_:-]?state"
    r"|coaching[_:-]?state"
    r"|password"
    r"|pwd"
    r"|account[_:-]?(?:id|truth)?"
    r"|auth(?:entication)?[_:-]?truth"
    r"|billing"
    r"|entitlement"
    r"|legal"
    r"|compliance"
    r"|advisory[_:-]?wiki"
    r"|workforce[_:-]?memory"
    r"|local[_:-]?support[_:-]?plane"
    r"|plugin[_:-]?control[_:-]?plane"
    r"|second[_:-]?source[_:-]?of[_:-]?truth"
    r"|graphrag"
    r"|knowledge[_:-]?graph",
    re.IGNORECASE,
)
_UNSAFE_RUNTIME_SCOPE_SINGLE_TOKENS = frozenset(
    {
        "backendadapter",
        "backendclient",
        "backendclients",
        "database",
        "db",
        "dependencyaddition",
        "dependencyadditions",
        "embedding",
        "embeddings",
        "fastapi",
        "filewrite",
        "filewrites",
        "migration",
        "migrations",
        "network",
        "openapi",
        "provider",
        "redisclient",
        "redisclients",
        "semanticsimilarity",
        "vectorsearch",
    }
)
_UNSAFE_RUNTIME_SCOPE_TOKEN_SEQUENCES = (
    ("availability", "probe"),
    ("availability", "probes"),
    ("backend", "adapter"),
    ("backend", "adapters"),
    ("backend", "client"),
    ("backend", "clients"),
    ("dependency", "addition"),
    ("dependency", "additions"),
    ("file", "write"),
    ("file", "writes"),
    ("gptcache", "client"),
    ("gptcache", "clients"),
    ("redis", "client"),
    ("redis", "clients"),
    ("semantic", "similarity"),
    ("vector", "search"),
)
SC_G5_MIN_NEGATIVE_CONTROL_COUNT = 10
SC_G5_MIN_FRESH_RUNTIME_COMPARISON_COUNT = 10
REQUIRED_SC_G2_CONTRACT_ID = "contract:sc-g2"
REQUIRED_SC_G3_CONTRACT_ID = "contract:sc-g3"
REQUIRED_SC_G4_CONTRACT_ID = "contract:sc-g4"


@dataclass(frozen=True)
class SemanticCacheBackendSafetyEvidence:
    """Safety evidence bundle required before any backend label can rank."""

    evidence_id: str
    sc_g2_contract_id: str
    sc_g3_contract_id: str
    sc_g4_contract_id: str
    source_fingerprints: tuple[str, ...]
    eval_event_ids: tuple[str, ...]
    admission_decision_id: str
    promotion_ids: tuple[str, ...]
    replay_entry_ids: tuple[str, ...]
    false_hit_rate_bps: int
    stale_answer_rate_bps: int
    policy_mismatch_count: int
    model_mismatch_count: int
    context_leakage_count: int
    admission_blocked_hit_count: int
    blocked_surface_hit_count: int
    negative_control_count: int
    fresh_runtime_comparison_count: int
    evidence_fingerprints: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_id",
            _validate_runtime_safe_evidence_id("evidence_id", self.evidence_id),
        )
        object.__setattr__(
            self,
            "sc_g2_contract_id",
            _validate_runtime_safe_evidence_id("sc_g2_contract_id", self.sc_g2_contract_id),
        )
        object.__setattr__(
            self,
            "sc_g3_contract_id",
            _validate_runtime_safe_evidence_id("sc_g3_contract_id", self.sc_g3_contract_id),
        )
        object.__setattr__(
            self,
            "sc_g4_contract_id",
            _validate_runtime_safe_evidence_id("sc_g4_contract_id", self.sc_g4_contract_id),
        )
        object.__setattr__(
            self,
            "source_fingerprints",
            _normalize_required_runtime_safe_evidence_ids(
                "source_fingerprints", self.source_fingerprints
            ),
        )
        object.__setattr__(
            self,
            "eval_event_ids",
            _normalize_required_runtime_safe_evidence_ids("eval_event_ids", self.eval_event_ids),
        )
        object.__setattr__(
            self,
            "admission_decision_id",
            _validate_runtime_safe_evidence_id(
                "admission_decision_id",
                self.admission_decision_id,
            ),
        )
        object.__setattr__(
            self,
            "promotion_ids",
            _normalize_required_runtime_safe_evidence_ids("promotion_ids", self.promotion_ids),
        )
        object.__setattr__(
            self,
            "replay_entry_ids",
            _normalize_required_runtime_safe_evidence_ids(
                "replay_entry_ids", self.replay_entry_ids
            ),
        )
        _validate_bps("false_hit_rate_bps", self.false_hit_rate_bps)
        _validate_bps("stale_answer_rate_bps", self.stale_answer_rate_bps)
        for name in (
            "policy_mismatch_count",
            "model_mismatch_count",
            "context_leakage_count",
            "admission_blocked_hit_count",
            "blocked_surface_hit_count",
            "negative_control_count",
            "fresh_runtime_comparison_count",
        ):
            _validate_non_negative_int(name, getattr(self, name))
        object.__setattr__(
            self,
            "evidence_fingerprints",
            _normalize_required_runtime_safe_evidence_ids(
                "evidence_fingerprints", self.evidence_fingerprints
            ),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class SemanticCacheBackendRollbackProof:
    """Machine-checkable rollback proof for one backend label."""

    proof_id: str
    kill_switch_proof_id: str
    request_bypass_proof_id: str
    no_cache_fallback_proof_id: str
    purge_invalidation_proof_id: str
    disabled_state_test_ids: tuple[str, ...]
    stop_rule_replay_ids: tuple[str, ...]
    rollback_runbook_id: str
    blast_radius_bps: int
    verified: bool
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "proof_id",
            _validate_structured_proof_id(
                "proof_id",
                self.proof_id,
                prefixes=("rollback:", "verification-bundle:rollback:"),
            ),
        )
        structured_ids = {
            "kill_switch_proof_id": ("proof:kill-switch:", "verification-bundle:kill-switch:"),
            "request_bypass_proof_id": ("proof:bypass:", "verification-bundle:bypass:"),
            "no_cache_fallback_proof_id": ("proof:no-cache:", "verification-bundle:no-cache:"),
            "purge_invalidation_proof_id": ("proof:purge:", "verification-bundle:purge:"),
            "rollback_runbook_id": ("runbook:rollback:", "verification-bundle:runbook:"),
        }
        for name, prefixes in structured_ids.items():
            object.__setattr__(
                self,
                name,
                _validate_structured_proof_id(name, getattr(self, name), prefixes=prefixes),
            )
        object.__setattr__(
            self,
            "disabled_state_test_ids",
            _normalize_required_structured_proof_ids(
                "disabled_state_test_ids",
                self.disabled_state_test_ids,
                prefixes=("test:disabled:", "verification-bundle:disabled:"),
            ),
        )
        object.__setattr__(
            self,
            "stop_rule_replay_ids",
            _normalize_required_structured_proof_ids(
                "stop_rule_replay_ids",
                self.stop_rule_replay_ids,
                prefixes=("replay:stop-rule:", "verification-bundle:stop-rule:"),
            ),
        )
        _validate_bps("blast_radius_bps", self.blast_radius_bps)
        _validate_bool("verified", self.verified)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class SemanticCacheBackendCandidate:
    """Inert backend label candidate, never a client, adapter, or config."""

    candidate_id: str
    backend_label: str
    backend_version: str
    policy_version: str
    supported_surfaces: tuple[str, ...]
    capability_flags: tuple[str, ...]
    safety_evidence: SemanticCacheBackendSafetyEvidence
    rollback_proof: SemanticCacheBackendRollbackProof
    latency_saved_p50_ms: int
    latency_saved_p95_ms: int
    provider_calls_avoided_count: int
    cost_saved_microunits: int
    current_head_ci_passed: bool
    current_head_ci_proof_id: str | None
    human_approval_record_id: str | None
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _validate_runtime_safe_token("candidate_id", self.candidate_id),
        )
        object.__setattr__(self, "backend_label", _validate_backend_label(self.backend_label))
        object.__setattr__(
            self,
            "backend_version",
            _validate_runtime_safe_evidence_id("backend_version", self.backend_version),
        )
        object.__setattr__(
            self,
            "policy_version",
            _validate_runtime_safe_token("policy_version", self.policy_version),
        )
        object.__setattr__(
            self,
            "supported_surfaces",
            _normalize_required_runtime_safe_tokens("supported_surfaces", self.supported_surfaces),
        )
        object.__setattr__(
            self,
            "capability_flags",
            _normalize_required_runtime_safe_tokens("capability_flags", self.capability_flags),
        )
        if not isinstance(self.safety_evidence, SemanticCacheBackendSafetyEvidence):
            raise ValueError("safety_evidence must be SemanticCacheBackendSafetyEvidence")
        if not isinstance(self.rollback_proof, SemanticCacheBackendRollbackProof):
            raise ValueError("rollback_proof must be SemanticCacheBackendRollbackProof")
        for name in (
            "latency_saved_p50_ms",
            "latency_saved_p95_ms",
            "provider_calls_avoided_count",
            "cost_saved_microunits",
        ):
            _validate_non_negative_int(name, getattr(self, name))
        _validate_bool("current_head_ci_passed", self.current_head_ci_passed)
        if self.current_head_ci_proof_id is not None:
            object.__setattr__(
                self,
                "current_head_ci_proof_id",
                _validate_structured_proof_id(
                    "current_head_ci_proof_id",
                    self.current_head_ci_proof_id,
                    prefixes=("ci:pr-", "ci:current-head:", "verification-bundle:ci:"),
                ),
            )
        if self.human_approval_record_id is not None:
            object.__setattr__(
                self,
                "human_approval_record_id",
                _validate_structured_proof_id(
                    "human_approval_record_id",
                    self.human_approval_record_id,
                    prefixes=("approval:human:", "review:human:", "verification-bundle:approval:"),
                ),
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class SemanticCacheBackendSelectionCriteria:
    """Fail-closed criteria for SC-G5 label evaluation."""

    policy_version: str
    allowed_backend_labels: tuple[str, ...]
    required_surface: str
    max_false_hit_rate_bps: int
    max_stale_answer_rate_bps: int
    max_policy_mismatch_count: int
    max_model_mismatch_count: int
    max_context_leakage_count: int
    allow_admission_blocked_hits: bool
    allow_blocked_surface_hits: bool
    min_negative_control_count: int
    min_fresh_runtime_comparison_count: int
    require_current_head_ci: bool
    current_head_sha: str
    require_human_approval: bool
    runtime_allowed: bool
    implementation_allowed: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_version",
            _validate_runtime_safe_token("policy_version", self.policy_version),
        )
        allowed = tuple(_validate_backend_label(label) for label in self.allowed_backend_labels)
        object.__setattr__(
            self,
            "allowed_backend_labels",
            _normalize_required_unique_tokens("allowed_backend_labels", allowed),
        )
        object.__setattr__(
            self,
            "required_surface",
            _validate_runtime_safe_token("required_surface", self.required_surface),
        )
        _validate_bps("max_false_hit_rate_bps", self.max_false_hit_rate_bps)
        _validate_bps("max_stale_answer_rate_bps", self.max_stale_answer_rate_bps)
        for name in (
            "max_policy_mismatch_count",
            "max_model_mismatch_count",
            "max_context_leakage_count",
            "min_negative_control_count",
            "min_fresh_runtime_comparison_count",
        ):
            _validate_non_negative_int(name, getattr(self, name))
        for name in (
            "allow_admission_blocked_hits",
            "allow_blocked_surface_hits",
            "require_current_head_ci",
            "require_human_approval",
            "runtime_allowed",
            "implementation_allowed",
        ):
            _validate_bool(name, getattr(self, name))
        object.__setattr__(
            self,
            "current_head_sha",
            _validate_git_sha("current_head_sha", self.current_head_sha),
        )
        if self.runtime_allowed or self.implementation_allowed:
            raise ValueError("SC-G5 criteria must keep runtime and implementation disabled")
        if not self.require_current_head_ci or not self.require_human_approval:
            raise ValueError("SC-G5 criteria must require CI proof and human approval")
        if (
            self.max_false_hit_rate_bps != 0
            or self.max_stale_answer_rate_bps != 0
            or self.max_policy_mismatch_count != 0
            or self.max_model_mismatch_count != 0
            or self.max_context_leakage_count != 0
            or self.allow_admission_blocked_hits
            or self.allow_blocked_surface_hits
        ):
            raise ValueError("SC-G5 safety criteria must be zero-tolerance and fail closed")
        if self.min_negative_control_count < SC_G5_MIN_NEGATIVE_CONTROL_COUNT:
            raise ValueError("SC-G5 criteria must require the minimum negative-control floor")
        if self.min_fresh_runtime_comparison_count < SC_G5_MIN_FRESH_RUNTIME_COMPARISON_COUNT:
            raise ValueError("SC-G5 criteria must require the minimum fresh-comparison floor")


@dataclass(frozen=True)
class SemanticCacheBackendSelectionDecision:
    """Deterministic SC-G5 candidate or matrix decision."""

    decision_id: str
    decision: str
    policy_version: str
    selected_candidate_id: str | None
    selected_backend_label: str | None
    candidate_id: str | None
    backend_label: str | None
    reason_codes: tuple[str, ...]
    rejected_candidate_ids: tuple[str, ...]
    runtime_allowed: bool
    implementation_allowed: bool
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _validate_token("decision_id", self.decision_id))
        if self.decision not in {
            DECISION_ELIGIBLE,
            DECISION_INELIGIBLE,
            DECISION_SELECTED,
            DECISION_NO_SELECTION,
        }:
            raise ValueError(f"unsupported decision: {self.decision!r}")
        _validate_decision_id_format(self.decision_id, self.decision)
        object.__setattr__(
            self,
            "policy_version",
            _validate_runtime_safe_token("policy_version", self.policy_version),
        )
        if self.selected_candidate_id is not None:
            object.__setattr__(
                self,
                "selected_candidate_id",
                _validate_runtime_safe_token("selected_candidate_id", self.selected_candidate_id),
            )
        if self.selected_backend_label is not None:
            object.__setattr__(
                self,
                "selected_backend_label",
                _validate_backend_label(self.selected_backend_label),
            )
        if self.candidate_id is not None:
            object.__setattr__(
                self,
                "candidate_id",
                _validate_runtime_safe_token("candidate_id", self.candidate_id),
            )
        if self.backend_label is not None:
            object.__setattr__(self, "backend_label", _validate_backend_label(self.backend_label))
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_reason_codes(self.reason_codes),
        )
        object.__setattr__(
            self,
            "rejected_candidate_ids",
            _normalize_unique_runtime_safe_tokens(
                "rejected_candidate_ids",
                self.rejected_candidate_ids,
            ),
        )
        _validate_bool("runtime_allowed", self.runtime_allowed)
        _validate_bool("implementation_allowed", self.implementation_allowed)
        if self.runtime_allowed or self.implementation_allowed:
            raise ValueError("SC-G5 decisions must keep runtime and implementation disabled")
        _validate_decision_shape(self)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class SemanticCacheBackendEvaluationMatrix:
    """Stable matrix for comparing inert backend labels."""

    matrix_id: str
    policy_version: str
    criteria: SemanticCacheBackendSelectionCriteria
    candidates: tuple[SemanticCacheBackendCandidate, ...]
    candidate_decisions: tuple[SemanticCacheBackendSelectionDecision, ...]
    final_decision: SemanticCacheBackendSelectionDecision

    def __post_init__(self) -> None:
        object.__setattr__(self, "matrix_id", _validate_token("matrix_id", self.matrix_id))
        object.__setattr__(
            self,
            "policy_version",
            _validate_runtime_safe_token("policy_version", self.policy_version),
        )
        if not isinstance(self.criteria, SemanticCacheBackendSelectionCriteria):
            raise ValueError("criteria must be SemanticCacheBackendSelectionCriteria")
        if self.criteria.policy_version != self.policy_version:
            raise ValueError("criteria policy_version must match matrix policy_version")
        for candidate in self.candidates:
            if not isinstance(candidate, SemanticCacheBackendCandidate):
                raise ValueError("candidates must be SemanticCacheBackendCandidate")
        object.__setattr__(self, "candidates", _sorted_candidates(tuple(self.candidates)))
        _validate_unique_candidate_ids(self.candidates)
        for decision in self.candidate_decisions:
            if not isinstance(decision, SemanticCacheBackendSelectionDecision):
                raise ValueError(
                    "candidate_decisions must be SemanticCacheBackendSelectionDecision"
                )
        if not isinstance(self.final_decision, SemanticCacheBackendSelectionDecision):
            raise ValueError("final_decision must be SemanticCacheBackendSelectionDecision")
        expected_decisions = tuple(
            evaluate_semantic_cache_backend_candidate(candidate=candidate, criteria=self.criteria)
            for candidate in self.candidates
        )
        if self.candidate_decisions != expected_decisions:
            raise ValueError("candidate_decisions must match freshly evaluated candidates")
        expected_final = select_semantic_cache_backend(
            candidates=self.candidates,
            criteria=self.criteria,
        )
        if self.final_decision != expected_final:
            raise ValueError("final_decision must match freshly selected backend decision")
        expected_matrix_id = build_semantic_cache_backend_matrix_id(
            candidates=self.candidates,
            criteria=self.criteria,
            final_decision=self.final_decision,
        )
        if self.matrix_id != expected_matrix_id:
            raise ValueError("matrix_id must match canonical matrix payload")


def evaluate_semantic_cache_backend_candidate(
    *,
    candidate: SemanticCacheBackendCandidate,
    criteria: SemanticCacheBackendSelectionCriteria,
) -> SemanticCacheBackendSelectionDecision:
    """Evaluate one backend label without selecting or activating it."""

    if not isinstance(candidate, SemanticCacheBackendCandidate):
        raise ValueError("candidate must be SemanticCacheBackendCandidate")
    if not isinstance(criteria, SemanticCacheBackendSelectionCriteria):
        raise ValueError("criteria must be SemanticCacheBackendSelectionCriteria")

    reasons = _candidate_failure_reasons(candidate=candidate, criteria=criteria)
    if reasons:
        decision = DECISION_INELIGIBLE
        reason_codes = tuple(reasons)
    else:
        decision = DECISION_ELIGIBLE
        reason_codes = (REASON_ELIGIBLE,)
    payload: JsonValue = {
        "backend_label": candidate.backend_label,
        "candidate_id": candidate.candidate_id,
        "candidate_signature": _candidate_signature(candidate),
        "decision": decision,
        "policy_version": criteria.policy_version,
        "reason_codes": list(reason_codes),
    }
    return SemanticCacheBackendSelectionDecision(
        decision_id=f"semantic-cache-backend:{_fingerprint_payload(payload)[:24]}",
        decision=decision,
        policy_version=criteria.policy_version,
        selected_candidate_id=None,
        selected_backend_label=None,
        candidate_id=candidate.candidate_id,
        backend_label=candidate.backend_label,
        reason_codes=reason_codes,
        rejected_candidate_ids=(candidate.candidate_id,) if decision == DECISION_INELIGIBLE else (),
        runtime_allowed=False,
        implementation_allowed=False,
        metadata={"decision_scope": "label_only", "serves_cached_payload": False},
    )


def evaluate_semantic_cache_backend_matrix(
    *,
    candidates: tuple[SemanticCacheBackendCandidate, ...],
    criteria: SemanticCacheBackendSelectionCriteria,
) -> SemanticCacheBackendEvaluationMatrix:
    """Build a deterministic matrix over backend labels."""

    candidate_decisions = tuple(
        evaluate_semantic_cache_backend_candidate(candidate=candidate, criteria=criteria)
        for candidate in _sorted_candidates(candidates)
    )
    final_decision = select_semantic_cache_backend(
        candidates=candidates,
        criteria=criteria,
    )
    return SemanticCacheBackendEvaluationMatrix(
        matrix_id=build_semantic_cache_backend_matrix_id(
            candidates=candidates,
            criteria=criteria,
            final_decision=final_decision,
        ),
        policy_version=criteria.policy_version,
        criteria=criteria,
        candidates=_sorted_candidates(candidates),
        candidate_decisions=candidate_decisions,
        final_decision=final_decision,
    )


def build_semantic_cache_backend_matrix_id(
    *,
    candidates: tuple[SemanticCacheBackendCandidate, ...],
    criteria: SemanticCacheBackendSelectionCriteria,
    final_decision: SemanticCacheBackendSelectionDecision,
) -> str:
    """Build the canonical deterministic ID for a backend evaluation matrix."""

    if not isinstance(criteria, SemanticCacheBackendSelectionCriteria):
        raise ValueError("criteria must be SemanticCacheBackendSelectionCriteria")
    payload: JsonValue = {
        "candidate_signatures": [
            _candidate_signature(candidate) for candidate in _sorted_candidates(candidates)
        ],
        "criteria": _criteria_signature(criteria),
        "final_decision_id": final_decision.decision_id,
        "policy_version": criteria.policy_version,
    }
    return f"semantic-cache-backend-matrix:{_fingerprint_payload(payload)[:24]}"


def select_semantic_cache_backend(
    *,
    candidates: tuple[SemanticCacheBackendCandidate, ...],
    criteria: SemanticCacheBackendSelectionCriteria,
) -> SemanticCacheBackendSelectionDecision:
    """Select an inert backend label recommendation, or fail closed."""

    ordered_candidates = _sorted_candidates(candidates)
    _validate_unique_candidate_ids(ordered_candidates)
    decisions = tuple(
        evaluate_semantic_cache_backend_candidate(candidate=candidate, criteria=criteria)
        for candidate in ordered_candidates
    )
    decision_by_candidate = {
        decision.candidate_id: decision
        for decision in decisions
        if decision.candidate_id is not None
    }
    eligible = [
        candidate
        for candidate in ordered_candidates
        if decision_by_candidate.get(candidate.candidate_id)
        and decision_by_candidate[candidate.candidate_id].decision == DECISION_ELIGIBLE
    ]
    evaluated_ids = tuple(candidate.candidate_id for candidate in ordered_candidates)
    rejected_ids = tuple(
        candidate.candidate_id for candidate in ordered_candidates if candidate not in eligible
    )
    if not eligible:
        payload: JsonValue = {
            "candidate_decision_ids": [decision.decision_id for decision in decisions],
            "decision": DECISION_NO_SELECTION,
            "evaluated_candidate_ids": list(evaluated_ids),
            "policy_version": criteria.policy_version,
            "rejected_candidate_ids": list(rejected_ids),
        }
        return SemanticCacheBackendSelectionDecision(
            decision_id=f"semantic-cache-backend-select:{_fingerprint_payload(payload)[:24]}",
            decision=DECISION_NO_SELECTION,
            policy_version=criteria.policy_version,
            selected_candidate_id=None,
            selected_backend_label=None,
            candidate_id=None,
            backend_label=None,
            reason_codes=(REASON_NO_ELIGIBLE_CANDIDATE,),
            rejected_candidate_ids=rejected_ids,
            runtime_allowed=False,
            implementation_allowed=False,
            metadata={"decision_scope": "label_only", "serves_cached_payload": False},
        )

    selected = sorted(eligible, key=_candidate_rank_key)[0]
    unselected_ids = tuple(
        candidate.candidate_id for candidate in ordered_candidates if candidate != selected
    )
    payload = {
        "candidate_decision_ids": [decision.decision_id for decision in decisions],
        "decision": DECISION_SELECTED,
        "evaluated_candidate_ids": list(evaluated_ids),
        "policy_version": criteria.policy_version,
        "rejected_candidate_ids": list(unselected_ids),
        "selected_backend_label": selected.backend_label,
        "selected_candidate_id": selected.candidate_id,
    }
    return SemanticCacheBackendSelectionDecision(
        decision_id=f"semantic-cache-backend-select:{_fingerprint_payload(payload)[:24]}",
        decision=DECISION_SELECTED,
        policy_version=criteria.policy_version,
        selected_candidate_id=selected.candidate_id,
        selected_backend_label=selected.backend_label,
        candidate_id=None,
        backend_label=None,
        reason_codes=(REASON_SELECTED,),
        rejected_candidate_ids=unselected_ids,
        runtime_allowed=False,
        implementation_allowed=False,
        metadata={"decision_scope": "label_only", "serves_cached_payload": False},
    )


def to_stable_mapping(value: object) -> Mapping[str, JsonValue]:
    """Return deterministic JSON-ready mappings for SC-G5 review."""

    if isinstance(value, SemanticCacheBackendSelectionDecision):
        return _stable_json_mapping(
            {
                "backend_label": value.backend_label,
                "candidate_id": value.candidate_id,
                "decision": value.decision,
                "decision_id": value.decision_id,
                "implementation_allowed": value.implementation_allowed,
                "metadata": _json_safe_copy(value.metadata),
                "policy_version": value.policy_version,
                "reason_codes": list(value.reason_codes),
                "rejected_candidate_ids": list(value.rejected_candidate_ids),
                "runtime_allowed": value.runtime_allowed,
                "selected_backend_label": value.selected_backend_label,
                "selected_candidate_id": value.selected_candidate_id,
            }
        )
    if isinstance(value, SemanticCacheBackendEvaluationMatrix):
        return _stable_json_mapping(
            {
                "candidate_decisions": [
                    to_stable_mapping(decision) for decision in value.candidate_decisions
                ],
                "candidate_signatures": [
                    _candidate_signature(candidate) for candidate in value.candidates
                ],
                "criteria": _criteria_signature(value.criteria),
                "final_decision": to_stable_mapping(value.final_decision),
                "matrix_id": value.matrix_id,
                "policy_version": value.policy_version,
            }
        )
    raise ValueError(f"unsupported stable mapping value: {type(value).__name__}")


def _candidate_failure_reasons(
    *,
    candidate: SemanticCacheBackendCandidate,
    criteria: SemanticCacheBackendSelectionCriteria,
) -> tuple[str, ...]:
    evidence = candidate.safety_evidence
    rollback = candidate.rollback_proof
    reasons: list[str] = []
    if candidate.backend_label not in criteria.allowed_backend_labels:
        reasons.append(REASON_BACKEND_LABEL_NOT_ALLOWED)
    if candidate.policy_version != criteria.policy_version:
        reasons.append(REASON_SC_G4_EVIDENCE_MISSING)
    if criteria.required_surface not in candidate.supported_surfaces:
        reasons.append(REASON_SC_G4_EVIDENCE_MISSING)
    if evidence.sc_g2_contract_id != REQUIRED_SC_G2_CONTRACT_ID:
        reasons.append(REASON_SC_G2_EVIDENCE_MISSING)
    if evidence.sc_g3_contract_id != REQUIRED_SC_G3_CONTRACT_ID:
        reasons.append(REASON_SC_G3_EVIDENCE_MISSING)
    if evidence.sc_g4_contract_id != REQUIRED_SC_G4_CONTRACT_ID:
        reasons.append(REASON_SC_G4_EVIDENCE_MISSING)
    if evidence.false_hit_rate_bps > criteria.max_false_hit_rate_bps:
        reasons.append(REASON_FALSE_HIT_RATE_EXCEEDED)
    if evidence.stale_answer_rate_bps > criteria.max_stale_answer_rate_bps:
        reasons.append(REASON_STALE_ANSWER_RATE_EXCEEDED)
    if evidence.policy_mismatch_count > criteria.max_policy_mismatch_count:
        reasons.append(REASON_POLICY_MISMATCH_EXCEEDED)
    if evidence.model_mismatch_count > criteria.max_model_mismatch_count:
        reasons.append(REASON_MODEL_MISMATCH_EXCEEDED)
    if evidence.context_leakage_count > criteria.max_context_leakage_count:
        reasons.append(REASON_CONTEXT_LEAKAGE_EXCEEDED)
    if evidence.admission_blocked_hit_count and not criteria.allow_admission_blocked_hits:
        reasons.append(REASON_ADMISSION_BLOCKED_HITS)
    if evidence.blocked_surface_hit_count and not criteria.allow_blocked_surface_hits:
        reasons.append(REASON_BLOCKED_SURFACE_HITS)
    if evidence.negative_control_count < criteria.min_negative_control_count:
        reasons.append(REASON_NEGATIVE_CONTROLS_MISSING)
    if evidence.fresh_runtime_comparison_count < criteria.min_fresh_runtime_comparison_count:
        reasons.append(REASON_FRESH_RUNTIME_COMPARISONS_MISSING)
    if not rollback.verified:
        reasons.append(REASON_ROLLBACK_PROOF_MISSING)
    if not _rollback_proof_matches_backend(rollback, candidate.backend_label):
        reasons.append(REASON_ROLLBACK_PROOF_MISSING)
    if criteria.require_current_head_ci:
        if (
            not candidate.current_head_ci_passed
            or candidate.current_head_ci_proof_id is None
            or not _ci_proof_matches_current_head(
                candidate.current_head_ci_proof_id,
                criteria.current_head_sha,
            )
        ):
            reasons.append(REASON_CURRENT_HEAD_CI_MISSING)
    if criteria.require_human_approval and candidate.human_approval_record_id is None:
        reasons.append(REASON_HUMAN_APPROVAL_MISSING)
    return _normalize_unique_tokens("reason_codes", tuple(dict.fromkeys(reasons)))


def _validate_decision_shape(decision: SemanticCacheBackendSelectionDecision) -> None:
    if decision.decision == DECISION_ELIGIBLE:
        if (
            decision.selected_candidate_id is not None
            or decision.selected_backend_label is not None
            or decision.candidate_id is None
            or decision.backend_label is None
            or decision.rejected_candidate_ids
            or decision.reason_codes != (REASON_ELIGIBLE,)
        ):
            raise ValueError("eligible decision shape is inconsistent")
    elif decision.decision == DECISION_INELIGIBLE:
        if (
            decision.selected_candidate_id is not None
            or decision.selected_backend_label is not None
            or decision.candidate_id is None
            or decision.backend_label is None
            or not decision.rejected_candidate_ids
            or decision.candidate_id not in decision.rejected_candidate_ids
            or REASON_ELIGIBLE in decision.reason_codes
            or REASON_SELECTED in decision.reason_codes
        ):
            raise ValueError("ineligible decision shape is inconsistent")
    elif decision.decision == DECISION_SELECTED:
        if (
            decision.selected_candidate_id is None
            or decision.selected_backend_label is None
            or decision.candidate_id is not None
            or decision.backend_label is not None
            or decision.selected_candidate_id in decision.rejected_candidate_ids
            or decision.reason_codes != (REASON_SELECTED,)
        ):
            raise ValueError("selected decision shape is inconsistent")
    elif decision.decision == DECISION_NO_SELECTION and (
        decision.selected_candidate_id is not None
        or decision.selected_backend_label is not None
        or decision.candidate_id is not None
        or decision.backend_label is not None
        or decision.reason_codes != (REASON_NO_ELIGIBLE_CANDIDATE,)
    ):
        raise ValueError("no-selection decision shape is inconsistent")


def _validate_decision_id_format(decision_id: str, decision: str) -> None:
    prefixes = ("semantic-cache-backend:", "semantic-cache-backend-select:")
    if not decision_id.startswith(prefixes):
        raise ValueError("decision_id must use an SC-G5 semantic-cache backend prefix")
    if decision in {DECISION_ELIGIBLE, DECISION_INELIGIBLE} and not decision_id.startswith(
        "semantic-cache-backend:"
    ):
        raise ValueError("decision_id prefix must match candidate-evaluation decision kind")
    if decision in {DECISION_SELECTED, DECISION_NO_SELECTION} and not decision_id.startswith(
        "semantic-cache-backend-select:"
    ):
        raise ValueError("decision_id prefix must match selection decision kind")
    suffix = decision_id.rsplit(":", 1)[1]
    if len(suffix) != 24 or any(char not in "0123456789abcdef" for char in suffix):
        raise ValueError("decision_id must include a 24-character lowercase hex suffix")


def _evidence_signature(evidence: SemanticCacheBackendSafetyEvidence) -> Mapping[str, JsonValue]:
    return _stable_json_mapping(
        {
            "admission_blocked_hit_count": evidence.admission_blocked_hit_count,
            "admission_decision_id": evidence.admission_decision_id,
            "blocked_surface_hit_count": evidence.blocked_surface_hit_count,
            "context_leakage_count": evidence.context_leakage_count,
            "eval_event_ids": list(evidence.eval_event_ids),
            "evidence_fingerprints": list(evidence.evidence_fingerprints),
            "evidence_id": evidence.evidence_id,
            "false_hit_rate_bps": evidence.false_hit_rate_bps,
            "fresh_runtime_comparison_count": evidence.fresh_runtime_comparison_count,
            "metadata": _json_safe_copy(evidence.metadata),
            "model_mismatch_count": evidence.model_mismatch_count,
            "negative_control_count": evidence.negative_control_count,
            "policy_mismatch_count": evidence.policy_mismatch_count,
            "promotion_ids": list(evidence.promotion_ids),
            "replay_entry_ids": list(evidence.replay_entry_ids),
            "sc_g2_contract_id": evidence.sc_g2_contract_id,
            "sc_g3_contract_id": evidence.sc_g3_contract_id,
            "sc_g4_contract_id": evidence.sc_g4_contract_id,
            "source_fingerprints": list(evidence.source_fingerprints),
            "stale_answer_rate_bps": evidence.stale_answer_rate_bps,
        }
    )


def _rollback_signature(proof: SemanticCacheBackendRollbackProof) -> Mapping[str, JsonValue]:
    return _stable_json_mapping(
        {
            "blast_radius_bps": proof.blast_radius_bps,
            "disabled_state_test_ids": list(proof.disabled_state_test_ids),
            "kill_switch_proof_id": proof.kill_switch_proof_id,
            "metadata": _json_safe_copy(proof.metadata),
            "no_cache_fallback_proof_id": proof.no_cache_fallback_proof_id,
            "proof_id": proof.proof_id,
            "purge_invalidation_proof_id": proof.purge_invalidation_proof_id,
            "request_bypass_proof_id": proof.request_bypass_proof_id,
            "rollback_runbook_id": proof.rollback_runbook_id,
            "stop_rule_replay_ids": list(proof.stop_rule_replay_ids),
            "verified": proof.verified,
        }
    )


def _candidate_signature(candidate: SemanticCacheBackendCandidate) -> Mapping[str, JsonValue]:
    return _stable_json_mapping(
        {
            "backend_label": candidate.backend_label,
            "backend_version": candidate.backend_version,
            "candidate_id": candidate.candidate_id,
            "capability_flags": list(candidate.capability_flags),
            "cost_saved_microunits": candidate.cost_saved_microunits,
            "current_head_ci_passed": candidate.current_head_ci_passed,
            "current_head_ci_proof_id": candidate.current_head_ci_proof_id,
            "human_approval_record_id": candidate.human_approval_record_id,
            "latency_saved_p50_ms": candidate.latency_saved_p50_ms,
            "latency_saved_p95_ms": candidate.latency_saved_p95_ms,
            "metadata": _json_safe_copy(candidate.metadata),
            "policy_version": candidate.policy_version,
            "provider_calls_avoided_count": candidate.provider_calls_avoided_count,
            "rollback_proof": _rollback_signature(candidate.rollback_proof),
            "safety_evidence": _evidence_signature(candidate.safety_evidence),
            "supported_surfaces": list(candidate.supported_surfaces),
        }
    )


def _criteria_signature(criteria: SemanticCacheBackendSelectionCriteria) -> Mapping[str, JsonValue]:
    return _stable_json_mapping(
        {
            "allow_admission_blocked_hits": criteria.allow_admission_blocked_hits,
            "allow_blocked_surface_hits": criteria.allow_blocked_surface_hits,
            "allowed_backend_labels": list(criteria.allowed_backend_labels),
            "implementation_allowed": criteria.implementation_allowed,
            "max_context_leakage_count": criteria.max_context_leakage_count,
            "max_false_hit_rate_bps": criteria.max_false_hit_rate_bps,
            "max_model_mismatch_count": criteria.max_model_mismatch_count,
            "max_policy_mismatch_count": criteria.max_policy_mismatch_count,
            "max_stale_answer_rate_bps": criteria.max_stale_answer_rate_bps,
            "min_fresh_runtime_comparison_count": criteria.min_fresh_runtime_comparison_count,
            "min_negative_control_count": criteria.min_negative_control_count,
            "policy_version": criteria.policy_version,
            "current_head_sha": criteria.current_head_sha,
            "require_current_head_ci": criteria.require_current_head_ci,
            "require_human_approval": criteria.require_human_approval,
            "required_surface": criteria.required_surface,
            "runtime_allowed": criteria.runtime_allowed,
        }
    )


def _candidate_rank_key(candidate: SemanticCacheBackendCandidate) -> (
    tuple[int, ...]
    | tuple[
        int,
        int,
        int,
        int,
        int,
        int,
        int,
        int,
        str,
        str,
    ]
):
    evidence = candidate.safety_evidence
    rollback = candidate.rollback_proof
    return (
        evidence.false_hit_rate_bps,
        evidence.stale_answer_rate_bps,
        evidence.policy_mismatch_count,
        evidence.model_mismatch_count,
        evidence.context_leakage_count,
        rollback.blast_radius_bps,
        -candidate.latency_saved_p95_ms,
        -candidate.cost_saved_microunits,
        candidate.backend_label,
        candidate.candidate_id,
    )


def _sorted_candidates(
    candidates: tuple[SemanticCacheBackendCandidate, ...],
) -> tuple[SemanticCacheBackendCandidate, ...]:
    for candidate in candidates:
        if not isinstance(candidate, SemanticCacheBackendCandidate):
            raise ValueError("candidates must be SemanticCacheBackendCandidate")
    return tuple(sorted(candidates, key=lambda item: (item.backend_label, item.candidate_id)))


def _validate_unique_candidate_ids(candidates: tuple[SemanticCacheBackendCandidate, ...]) -> None:
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidates contain duplicate candidate_id")


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
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _stable_json_mapping(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    return {key: _json_safe_copy(item) for key, item in sorted(value.items())}


def _json_safe_copy(value: JsonValue | Mapping[str, JsonValue]) -> JsonValue:
    if isinstance(value, Mapping):
        copied: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
            copied[key] = _json_safe_copy(item)
        return {key: copied[key] for key in sorted(copied)}
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
    if (
        _UNSAFE_METADATA_RE.search(value)
        or _contains_unsafe_runtime_scope(value)
        or _PATH_RE.search(value)
        or _RELATIVE_PATH_RE.search(value)
    ):
        raise ValueError(f"{name} contains unsafe metadata")


def _contains_unsafe_runtime_scope(value: str) -> bool:
    tokens = tuple(token for token in re.split(r"[^a-z0-9]+", value.casefold()) if token)
    if any(token in _UNSAFE_RUNTIME_SCOPE_SINGLE_TOKENS for token in tokens):
        return True
    for sequence in _UNSAFE_RUNTIME_SCOPE_TOKEN_SEQUENCES:
        sequence_length = len(sequence)
        for index in range(0, len(tokens) - sequence_length + 1):
            if tokens[index : index + sequence_length] == sequence:
                return True
    return False


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


def _normalize_unique_runtime_safe_tokens(
    name: str,
    values: tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _validate_runtime_safe_token(name, value)
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate entries")
        seen.add(normalized)
        normalized_values.append(normalized)
    return tuple(sorted(normalized_values))


def _normalize_required_structured_proof_ids(
    name: str,
    values: tuple[str, ...],
    *,
    prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _validate_structured_proof_id(name, value, prefixes=prefixes)
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate entries")
        seen.add(normalized)
        normalized_values.append(normalized)
    if not normalized_values:
        raise ValueError(f"{name} must be non-empty")
    return tuple(sorted(normalized_values))


def _normalize_required_runtime_safe_tokens(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _validate_runtime_safe_token(name, value)
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate entries")
        seen.add(normalized)
        normalized_values.append(normalized)
    if not normalized_values:
        raise ValueError(f"{name} must be non-empty")
    return tuple(sorted(normalized_values))


def _normalize_required_runtime_safe_evidence_ids(
    name: str, values: tuple[str, ...]
) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _validate_runtime_safe_evidence_id(name, value)
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate entries")
        seen.add(normalized)
        normalized_values.append(normalized)
    if not normalized_values:
        raise ValueError(f"{name} must be non-empty")
    return tuple(sorted(normalized_values))


def _normalize_reason_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    reason_codes = _normalize_required_unique_tokens("reason_codes", values)
    for reason_code in reason_codes:
        if reason_code not in ALLOWED_REASON_CODES:
            raise ValueError(f"unsupported reason_code: {reason_code!r}")
    return reason_codes


def _validate_token(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if _PATH_RE.search(normalized):
        raise ValueError(f"{name} must not contain paths")
    if _UNSAFE_TOKEN_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe token")
    if _UNSAFE_EVIDENCE_ID_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe proof token")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    return normalized


def _validate_git_sha(name: str, value: str) -> str:
    normalized = _validate_runtime_safe_token(name, value)
    if len(normalized) < 7 or len(normalized) > 40:
        raise ValueError(f"{name} must be a 7- to 40-character git SHA")
    if any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError(f"{name} must be lowercase hex")
    return normalized


def _validate_runtime_safe_token(name: str, value: str) -> str:
    normalized = _validate_token(name, value)
    if _contains_unsafe_runtime_scope(normalized):
        raise ValueError(f"{name} contains unsafe runtime scope")
    return normalized


def _validate_runtime_safe_evidence_id(name: str, value: str) -> str:
    normalized = _validate_evidence_id(name, value)
    if _contains_unsafe_runtime_scope(normalized):
        raise ValueError(f"{name} contains unsafe runtime scope")
    return normalized


def _validate_evidence_id(name: str, value: str) -> str:
    normalized = _validate_token(name, value)
    if _UNSAFE_EVIDENCE_ID_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe evidence identifier")
    return normalized


def _validate_structured_proof_id(
    name: str,
    value: str,
    *,
    prefixes: tuple[str, ...],
) -> str:
    normalized = _validate_evidence_id(name, value)
    if _contains_unsafe_runtime_scope(normalized):
        raise ValueError(f"{name} contains unsafe runtime scope")
    matching_prefix = next((prefix for prefix in prefixes if normalized.startswith(prefix)), None)
    if matching_prefix is None:
        raise ValueError(f"{name} must use a structured proof identifier")
    suffix = normalized[len(matching_prefix) :]
    if not any(char.isalnum() for char in suffix):
        raise ValueError(f"{name} must include proof evidence after its prefix")
    return normalized


def _validate_backend_label(value: str) -> str:
    normalized = _validate_token("backend_label", value)
    if normalized not in ALLOWED_BACKEND_LABELS:
        raise ValueError(f"unsupported backend_label: {normalized!r}")
    return normalized


def _backend_rollback_token(backend_label: str) -> str:
    if backend_label == BACKEND_LABEL_REDIS:
        return "redis"
    if backend_label == BACKEND_LABEL_GPTCACHE:
        return "gptcache"
    if backend_label == BACKEND_LABEL_IN_MEMORY:
        return "in-memory"
    raise ValueError(f"unsupported backend_label: {backend_label!r}")


def _backend_tokens_in_proof_id(proof_id: str) -> frozenset[str]:
    proof_tokens = frozenset(proof_id.split(":"))
    backend_tokens = {
        _backend_rollback_token(label)
        for label in ALLOWED_BACKEND_LABELS
        if _backend_rollback_token(label) in proof_tokens
    }
    return frozenset(backend_tokens)


def _ci_proof_matches_current_head(proof_id: str, current_head_sha: str) -> bool:
    return f":head-{current_head_sha}:" in proof_id


def _rollback_proof_matches_backend(
    rollback: SemanticCacheBackendRollbackProof,
    backend_label: str,
) -> bool:
    backend_token = _backend_rollback_token(backend_label)
    proof_ids = (
        rollback.proof_id,
        rollback.kill_switch_proof_id,
        rollback.request_bypass_proof_id,
        rollback.no_cache_fallback_proof_id,
        rollback.purge_invalidation_proof_id,
        rollback.rollback_runbook_id,
        *rollback.disabled_state_test_ids,
        *rollback.stop_rule_replay_ids,
    )
    return all(_backend_tokens_in_proof_id(proof_id) == {backend_token} for proof_id in proof_ids)


def _validate_bps(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0 or value > 10000:
        raise ValueError(f"{name} must be between 0 and 10000")


def _validate_non_negative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _validate_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be bool")

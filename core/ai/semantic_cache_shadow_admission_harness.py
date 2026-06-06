"""Semantic-cache shadow admission harness report composition.

This module projects the existing offline semantic-cache admission decision
engine onto synthetic runtime-path labels. It is internal governance metadata
only: no runtime serving, no cache read/write, no provider calls, and no raw
prompt/query/context/answer material.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from types import MappingProxyType
from typing import TypeAlias, cast

from core.ai.semantic_cache_offline_admission_runner import (
    SCENARIO_IDS as OFFLINE_SCENARIO_IDS,
    build_default_semantic_cache_offline_admission_input,
    compose_semantic_cache_offline_admission_report,
    to_stable_mapping as offline_to_stable_mapping,
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

REPORT_ID = "semantic_cache_shadow_admission_harness_report"
REPORT_VERSION = "2026-06-06"
GENERATED_AT = "static-2026-06-06"
SCHEMA_VERSION = "1.0"
SCOPE = "internal_only_semantic_cache_shadow_admission_harness"
GENERATION_MODE = "deterministic_static_shadow_synthetic_redacted_inputs"
SEMANTIC_CACHE_GATE_STATUS = "closed"
DEFAULT_PRODUCED_AT = "2026-06-06T00:00:00Z"
DEFAULT_POLICY_VERSION = "semantic-cache-shadow-admission-v1"

PROVENANCE_FIELD_IDS: tuple[str, ...] = (
    "input_digest",
    "prompt_digest",
    "context_item_digests",
    "answer_digest",
    "prompt_char_count",
    "prompt_trimmed",
    "verification_hops",
    "verification_calls",
)
PATH_IDS: tuple[str, ...] = (
    "direct_local_answer_exact_shadow",
    "rag_pre_generation_fuzzy_shadow",
    "rag_runtime_merged_near_duplicate_shadow",
    "philosophical_runtime_merged_shadow",
    "degraded_retrieval_stale_source_shadow",
    "runtime_verification_disabled_passthrough_shadow",
    "missing_bundle_fail_closed_shadow",
    "blocked_bundle_fail_closed_shadow",
    "kill_switch_request_disabled_shadow",
    "blocked_surface_shadow",
    "policy_mismatch_shadow",
    "model_mismatch_shadow",
    "tier_mismatch_shadow",
    "context_mismatch_shadow",
)
PATH_FAMILIES: tuple[str, ...] = (
    "insight_route",
    "rag_orchestration",
    "philosophical_runtime_verification",
)
SOURCE_IDS: Mapping[str, str] = MappingProxyType(
    {
        "semantic_cache_offline_runner": "core/ai/semantic_cache_offline_admission_runner.py",
        "sc_g2": "core/ai/exact_fuzzy_cache.py",
        "sc_g3": "core/ai/cache_observability.py",
        "sc_g4": "core/ai/bounded_insight_semantic_cache.py",
        "sc_g5": "core/ai/semantic_cache_backend_selection.py",
        "verification_contracts": "core/verification/contracts.py",
        "insight_runtime": "core/ai/insight_runtime.py",
        "rag_orchestration": "core/rag/orchestration.py",
        "philosophical_runtime": "core/insight/philosophical_runtime.py",
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
    "runtime_serving_behavior_changed",
    "admission_authority_changed",
    "runtime_allowed",
    "implementation_allowed",
    "semantic_cache_allowed",
    "semantic_cache_runtime_allowed",
    "semantic_cache_implementation_allowed",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
    "slack_or_operator_authority_allowed",
    "graphrag_allowed",
    "embedding_or_vector_changed",
    "redis_or_gptcache_changed",
)
REDACTION_ASSERTION_KEYS: tuple[str, ...] = (
    "raw_prompt_absent",
    "raw_query_absent",
    "normalized_query_absent",
    "raw_input_absent",
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
class SemanticCacheShadowAdmissionInput:
    """Explicit input for deterministic shadow harness composition."""

    produced_at: str
    path_ids: tuple[str, ...] = PATH_IDS

    def __post_init__(self) -> None:
        object.__setattr__(self, "produced_at", _validate_produced_at(self.produced_at))
        object.__setattr__(self, "path_ids", _normalize_path_ids(self.path_ids))


@dataclass(frozen=True)
class SemanticCacheShadowAdmissionReport:
    """Redacted, metadata-only shadow projection report."""

    schema_version: str
    report_id: str
    report_version: str
    generated_at: str
    scope: str
    generation_mode: str
    source_ids: Mapping[str, JsonValue]
    authority_flags: Mapping[str, JsonValue]
    path_specs: tuple[Mapping[str, JsonValue], ...]
    path_results: tuple[Mapping[str, JsonValue], ...]
    projection_summary: Mapping[str, JsonValue]
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
            "path_specs",
            tuple(_freeze_mapping(result) for result in self.path_specs),
        )
        object.__setattr__(
            self,
            "path_results",
            tuple(_freeze_mapping(result) for result in self.path_results),
        )
        object.__setattr__(
            self,
            "projection_summary",
            _freeze_mapping(self.projection_summary),
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
class _ShadowPathSpec:
    path_id: str
    path_family: str
    route_label: str
    runner_scenario_id: str
    verification_bundle_state: str
    verification_overall_status: str
    verification_admission_allowed: bool | None
    rag_state: str
    runtime_validation_state: str
    source_freshness_label: str
    present_provenance_fields: tuple[str, ...]
    expected_shadow_label: str
    expected_action: str
    request_fingerprint: str
    context_fingerprint: str
    response_fingerprint: str | None
    verification_bundle_fingerprint: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "path_id", _validate_token("path_id", self.path_id))
        if self.path_family not in PATH_FAMILIES:
            raise ValueError(f"unsupported path_family: {self.path_family!r}")
        object.__setattr__(self, "path_family", _validate_token("path_family", self.path_family))
        object.__setattr__(self, "route_label", _validate_token("route_label", self.route_label))
        if self.runner_scenario_id not in OFFLINE_SCENARIO_IDS:
            raise ValueError(f"unsupported runner_scenario_id: {self.runner_scenario_id!r}")
        object.__setattr__(
            self,
            "runner_scenario_id",
            _validate_token("runner_scenario_id", self.runner_scenario_id),
        )
        object.__setattr__(
            self,
            "verification_bundle_state",
            _validate_token("verification_bundle_state", self.verification_bundle_state),
        )
        object.__setattr__(
            self,
            "verification_overall_status",
            _validate_token("verification_overall_status", self.verification_overall_status),
        )
        if self.verification_admission_allowed is not None and not isinstance(
            self.verification_admission_allowed, bool
        ):
            raise ValueError("verification_admission_allowed must be a boolean or null")
        object.__setattr__(self, "rag_state", _validate_token("rag_state", self.rag_state))
        object.__setattr__(
            self,
            "runtime_validation_state",
            _validate_token("runtime_validation_state", self.runtime_validation_state),
        )
        object.__setattr__(
            self,
            "source_freshness_label",
            _validate_token("source_freshness_label", self.source_freshness_label),
        )
        object.__setattr__(
            self,
            "present_provenance_fields",
            _normalize_provenance_fields(self.present_provenance_fields),
        )
        object.__setattr__(
            self,
            "expected_shadow_label",
            _validate_token("expected_shadow_label", self.expected_shadow_label),
        )
        object.__setattr__(
            self,
            "expected_action",
            _validate_token("expected_action", self.expected_action),
        )
        object.__setattr__(
            self,
            "request_fingerprint",
            _validate_fingerprint("request_fingerprint", self.request_fingerprint),
        )
        object.__setattr__(
            self,
            "context_fingerprint",
            _validate_fingerprint("context_fingerprint", self.context_fingerprint),
        )
        if self.response_fingerprint is not None:
            object.__setattr__(
                self,
                "response_fingerprint",
                _validate_fingerprint("response_fingerprint", self.response_fingerprint),
            )
        if self.verification_bundle_fingerprint is not None:
            object.__setattr__(
                self,
                "verification_bundle_fingerprint",
                _validate_fingerprint(
                    "verification_bundle_fingerprint",
                    self.verification_bundle_fingerprint,
                ),
            )
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_tokens("reason_codes", self.reason_codes),
        )


def build_default_semantic_cache_shadow_admission_input(
    *,
    produced_at: str = DEFAULT_PRODUCED_AT,
    path_ids: Iterable[str] = PATH_IDS,
) -> SemanticCacheShadowAdmissionInput:
    """Build deterministic synthetic input used by CI and report rendering."""

    return SemanticCacheShadowAdmissionInput(produced_at=produced_at, path_ids=tuple(path_ids))


def compose_semantic_cache_shadow_admission_report(
    input: SemanticCacheShadowAdmissionInput,
) -> SemanticCacheShadowAdmissionReport:
    """Compose a shadow report without runtime cache authority."""

    if not isinstance(input, SemanticCacheShadowAdmissionInput):
        raise ValueError("input must be SemanticCacheShadowAdmissionInput")

    offline_mapping = _offline_decision_mapping()
    offline_scenarios = _offline_scenarios(offline_mapping)
    specs = _ordered_specs(input.path_ids)
    path_specs: list[Mapping[str, JsonValue]] = []
    path_results: list[Mapping[str, JsonValue]] = []

    for spec in specs:
        scenario = offline_scenarios[spec.runner_scenario_id]
        path_specs.append(_path_spec_mapping(spec))
        path_results.append(_path_result(spec=spec, scenario=scenario))

    projection_summary = _projection_summary(path_results)
    return SemanticCacheShadowAdmissionReport(
        schema_version=SCHEMA_VERSION,
        report_id=REPORT_ID,
        report_version=REPORT_VERSION,
        generated_at=GENERATED_AT,
        scope=SCOPE,
        generation_mode=GENERATION_MODE,
        source_ids=dict(SOURCE_IDS),
        authority_flags=_authority_flags(),
        path_specs=tuple(path_specs),
        path_results=tuple(path_results),
        projection_summary=projection_summary,
        backend_label_context=_backend_label_context(offline_mapping),
        final_admission_decision={
            "decision": "shadow_report_only",
            "reason_codes": [
                "semantic_cache_gate_closed",
                "shadow_projection_only",
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


def to_stable_mapping(report: SemanticCacheShadowAdmissionReport) -> Mapping[str, JsonValue]:
    """Return a byte-stable JSON-ready mapping for the shadow report."""

    if not isinstance(report, SemanticCacheShadowAdmissionReport):
        raise ValueError("report must be SemanticCacheShadowAdmissionReport")
    payload: dict[str, JsonValue] = {
        "schema_version": report.schema_version,
        "report_id": report.report_id,
        "report_version": report.report_version,
        "generated_at": report.generated_at,
        "scope": report.scope,
        "generation_mode": report.generation_mode,
        "source_ids": _json_safe_copy(report.source_ids),
        "authority_flags": _json_safe_copy(report.authority_flags),
        "path_specs": [_json_safe_copy(result) for result in report.path_specs],
        "path_results": [_json_safe_copy(result) for result in report.path_results],
        "projection_summary": _json_safe_copy(report.projection_summary),
        "backend_label_context": _json_safe_copy(report.backend_label_context),
        "final_admission_decision": _json_safe_copy(report.final_admission_decision),
        "redaction_assertions": _json_safe_copy(report.redaction_assertions),
        "source_refs": [_json_safe_copy(ref) for ref in report.source_refs],
    }
    return {
        "schema_version": payload["schema_version"],
        "report_id": payload["report_id"],
        "report_version": payload["report_version"],
        "generated_at": payload["generated_at"],
        "scope": payload["scope"],
        "generation_mode": payload["generation_mode"],
        "evidence_asset": _evidence_asset(payload),
        "source_ids": payload["source_ids"],
        "authority_flags": payload["authority_flags"],
        "path_specs": payload["path_specs"],
        "path_results": payload["path_results"],
        "projection_summary": payload["projection_summary"],
        "backend_label_context": payload["backend_label_context"],
        "final_admission_decision": payload["final_admission_decision"],
        "redaction_assertions": payload["redaction_assertions"],
        "source_refs": payload["source_refs"],
    }


def _offline_decision_mapping() -> Mapping[str, JsonValue]:
    report = compose_semantic_cache_offline_admission_report(
        build_default_semantic_cache_offline_admission_input()
    )
    return cast(Mapping[str, JsonValue], offline_to_stable_mapping(report))


def _offline_scenarios(mapping: Mapping[str, JsonValue]) -> Mapping[str, Mapping[str, JsonValue]]:
    scenario_values = mapping.get("scenario_results")
    if not isinstance(scenario_values, list):
        raise ValueError("offline runner scenario_results must be a list")
    scenarios: dict[str, Mapping[str, JsonValue]] = {}
    for value in scenario_values:
        if not isinstance(value, Mapping):
            raise ValueError("offline runner scenario entries must be mappings")
        scenario_id = value.get("scenario_id")
        if not isinstance(scenario_id, str):
            raise ValueError("offline runner scenario_id must be a string")
        scenarios[scenario_id] = _freeze_mapping(value)
    return MappingProxyType(scenarios)


def _path_spec_mapping(spec: _ShadowPathSpec) -> Mapping[str, JsonValue]:
    missing_fields = _missing_provenance_fields(spec.present_provenance_fields)
    return {
        "path_id": spec.path_id,
        "path_family": spec.path_family,
        "route_label": spec.route_label,
        "runner_scenario_id": spec.runner_scenario_id,
        "verification_bundle_state": spec.verification_bundle_state,
        "verification_overall_status": spec.verification_overall_status,
        "verification_admission_allowed": spec.verification_admission_allowed,
        "rag_state": spec.rag_state,
        "runtime_validation_state": spec.runtime_validation_state,
        "source_freshness_label": spec.source_freshness_label,
        "expected_provenance_fields": list(PROVENANCE_FIELD_IDS),
        "present_provenance_fields": list(spec.present_provenance_fields),
        "missing_required_provenance_fields": list(missing_fields),
        "provenance_complete": not missing_fields,
        "expected_shadow_label": spec.expected_shadow_label,
        "expected_action": spec.expected_action,
        "request_fingerprint": spec.request_fingerprint,
        "context_fingerprint": spec.context_fingerprint,
        "response_fingerprint": spec.response_fingerprint,
        "verification_bundle_fingerprint": spec.verification_bundle_fingerprint,
        "reason_codes": list(spec.reason_codes),
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _path_result(
    *,
    spec: _ShadowPathSpec,
    scenario: Mapping[str, JsonValue],
) -> Mapping[str, JsonValue]:
    shadow_label = _project_shadow_label(spec=spec, scenario=scenario)
    if shadow_label != spec.expected_shadow_label:
        raise ValueError(f"path {spec.path_id} shadow label projection mismatch")
    missing_fields = _missing_provenance_fields(spec.present_provenance_fields)
    result: dict[str, JsonValue] = {
        "path_id": spec.path_id,
        "path_family": spec.path_family,
        "route_label": spec.route_label,
        "runner_scenario_id": spec.runner_scenario_id,
        "verification_bundle_present": spec.verification_bundle_state
        not in {"missing", "disabled"},
        "verification_bundle_state": spec.verification_bundle_state,
        "verification_overall_status": spec.verification_overall_status,
        "verification_admission_allowed": spec.verification_admission_allowed,
        "provenance_complete": not missing_fields,
        "present_provenance_fields": list(spec.present_provenance_fields),
        "missing_required_provenance_fields": list(missing_fields),
        "source_freshness_label": spec.source_freshness_label,
        "rag_state": spec.rag_state,
        "runtime_validation_state": spec.runtime_validation_state,
        "lookup_decision": _scenario_string(scenario, "lookup_decision"),
        "match_mode": _scenario_optional_string(scenario, "match_mode"),
        "score_bps": _scenario_optional_int(scenario, "score_bps"),
        "false_hit_outcome": _scenario_string(scenario, "false_hit_outcome"),
        "false_hit_is_false_hit": _scenario_bool(scenario, "false_hit_is_false_hit"),
        "false_hit_blocking_reasons": _json_string_list(
            _scenario_string_list(scenario, "false_hit_blocking_reasons")
        ),
        "stop_serving": _scenario_bool(scenario, "stop_serving"),
        "bounded_decision": _scenario_string(scenario, "bounded_decision"),
        "bounded_reason_codes": _json_string_list(
            _scenario_string_list(scenario, "bounded_reason_codes")
        ),
        "shadow_label": shadow_label,
        "reason_codes": _merge_reason_codes(
            spec.reason_codes,
            _scenario_string_list(scenario, "bounded_reason_codes"),
        ),
        "request_fingerprint": spec.request_fingerprint,
        "context_fingerprint": spec.context_fingerprint,
        "response_fingerprint": spec.response_fingerprint,
        "verification_bundle_fingerprint": spec.verification_bundle_fingerprint,
        "semantic_cache_gate_status": SEMANTIC_CACHE_GATE_STATUS,
        "runtime_allowed": False,
        "implementation_allowed": False,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }
    return result


def _project_shadow_label(
    *,
    spec: _ShadowPathSpec,
    scenario: Mapping[str, JsonValue],
) -> str:
    lookup_decision = _scenario_string(scenario, "lookup_decision")
    bounded_decision = _scenario_string(scenario, "bounded_decision")
    false_hit = _scenario_bool(scenario, "false_hit_is_false_hit")
    stop_serving = _scenario_bool(scenario, "stop_serving")

    if spec.verification_bundle_state in {"missing", "fail"}:
        return "blocked_verification_bundle_shadow"
    if spec.verification_bundle_state == "disabled":
        return "verification_disabled_passthrough_shadow"
    if spec.rag_state == "degraded":
        return "blocked_rag_degraded_shadow"
    if spec.runner_scenario_id == "kill_switch_request_disabled" and stop_serving:
        return "blocked_stop_rule_shadow"
    if false_hit:
        return "blocked_false_hit_shadow"
    if stop_serving:
        return "blocked_stop_rule_shadow"
    if lookup_decision == "miss":
        return "lookup_miss_fallback_shadow"
    if bounded_decision == "experiment_eligible":
        return "metadata_only_candidate_gate_closed"
    return "metadata_only_fallback_gate_closed"


def _projection_summary(path_results: list[Mapping[str, JsonValue]]) -> Mapping[str, JsonValue]:
    counts: dict[str, int] = {}
    for result in path_results:
        label = result.get("shadow_label")
        if not isinstance(label, str):
            raise ValueError("path result shadow_label must be a string")
        counts[label] = counts.get(label, 0) + 1
    return {
        "path_count": len(path_results),
        "path_ids": list(PATH_IDS),
        "shadow_label_counts": dict(sorted(counts.items())),
        "semantic_cache_gate_status": SEMANTIC_CACHE_GATE_STATUS,
        "runtime_allowed": False,
        "implementation_allowed": False,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _backend_label_context(mapping: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    value = mapping.get("backend_label_context")
    if not isinstance(value, Mapping):
        raise ValueError("offline runner backend_label_context must be a mapping")
    context = _json_safe_copy(value)
    if not isinstance(context, dict):
        raise ValueError("backend label context must be a mapping")
    context["runtime_allowed"] = False
    context["implementation_allowed"] = False
    context["cache_read_allowed"] = False
    context["cache_write_allowed"] = False
    context["serving_allowed"] = False
    return context


def _ordered_specs(path_ids: tuple[str, ...]) -> tuple[_ShadowPathSpec, ...]:
    specs = _path_specs()
    return tuple(specs[path_id] for path_id in PATH_IDS if path_id in path_ids)


def _path_specs() -> Mapping[str, _ShadowPathSpec]:
    all_fields = PROVENANCE_FIELD_IDS
    no_fields: tuple[str, ...] = ()
    specs = (
        _ShadowPathSpec(
            path_id="direct_local_answer_exact_shadow",
            path_family="insight_route",
            route_label="direct_local_answer",
            runner_scenario_id="exact_safe_hit",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="not_used",
            runtime_validation_state="passed",
            source_freshness_label="fresh",
            present_provenance_fields=all_fields,
            expected_shadow_label="metadata_only_candidate_gate_closed",
            expected_action="shadow_observe_only",
            request_fingerprint="sha256:shadow-direct-request",
            context_fingerprint="sha256:shadow-direct-context",
            response_fingerprint="sha256:shadow-direct-response",
            verification_bundle_fingerprint="sha256:shadow-direct-bundle",
            reason_codes=("verification_passed", "direct_answer_path"),
        ),
        _ShadowPathSpec(
            path_id="rag_pre_generation_fuzzy_shadow",
            path_family="rag_orchestration",
            route_label="rag_pre_generation",
            runner_scenario_id="reordered_token_fuzzy_hit",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="validated_context",
            runtime_validation_state="passed",
            source_freshness_label="fresh",
            present_provenance_fields=all_fields,
            expected_shadow_label="metadata_only_candidate_gate_closed",
            expected_action="shadow_observe_only",
            request_fingerprint="sha256:shadow-rag-pre-request",
            context_fingerprint="sha256:shadow-rag-pre-context",
            response_fingerprint="sha256:shadow-rag-pre-response",
            verification_bundle_fingerprint="sha256:shadow-rag-pre-bundle",
            reason_codes=("verification_passed", "rag_pre_generation_path"),
        ),
        _ShadowPathSpec(
            path_id="rag_runtime_merged_near_duplicate_shadow",
            path_family="rag_orchestration",
            route_label="rag_runtime_merged",
            runner_scenario_id="near_duplicate_fuzzy_hit",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="validated_context",
            runtime_validation_state="passed",
            source_freshness_label="fresh",
            present_provenance_fields=all_fields,
            expected_shadow_label="metadata_only_candidate_gate_closed",
            expected_action="shadow_observe_only",
            request_fingerprint="sha256:shadow-rag-merged-request",
            context_fingerprint="sha256:shadow-rag-merged-context",
            response_fingerprint="sha256:shadow-rag-merged-response",
            verification_bundle_fingerprint="sha256:shadow-rag-merged-bundle",
            reason_codes=("verification_passed", "rag_runtime_merged_path"),
        ),
        _ShadowPathSpec(
            path_id="philosophical_runtime_merged_shadow",
            path_family="philosophical_runtime_verification",
            route_label="philosophical_runtime_merged",
            runner_scenario_id="exact_safe_hit",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="validated_context",
            runtime_validation_state="passed",
            source_freshness_label="fresh",
            present_provenance_fields=all_fields,
            expected_shadow_label="metadata_only_candidate_gate_closed",
            expected_action="shadow_observe_only",
            request_fingerprint="sha256:shadow-philosophy-request",
            context_fingerprint="sha256:shadow-philosophy-context",
            response_fingerprint="sha256:shadow-philosophy-response",
            verification_bundle_fingerprint="sha256:shadow-philosophy-bundle",
            reason_codes=("verification_passed", "philosophical_runtime_path"),
        ),
        _ShadowPathSpec(
            path_id="degraded_retrieval_stale_source_shadow",
            path_family="rag_orchestration",
            route_label="degraded_retrieval",
            runner_scenario_id="stale_source_negative_control",
            verification_bundle_state="warn",
            verification_overall_status="warn",
            verification_admission_allowed=False,
            rag_state="degraded",
            runtime_validation_state="passed",
            source_freshness_label="stale",
            present_provenance_fields=all_fields,
            expected_shadow_label="blocked_rag_degraded_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-degraded-request",
            context_fingerprint="sha256:shadow-degraded-context",
            response_fingerprint="sha256:shadow-degraded-response",
            verification_bundle_fingerprint="sha256:shadow-degraded-bundle",
            reason_codes=("rag_degraded", "source_stale"),
        ),
        _ShadowPathSpec(
            path_id="runtime_verification_disabled_passthrough_shadow",
            path_family="insight_route",
            route_label="runtime_verification_disabled",
            runner_scenario_id="lookup_miss_fallback",
            verification_bundle_state="disabled",
            verification_overall_status="not_applicable",
            verification_admission_allowed=None,
            rag_state="not_used",
            runtime_validation_state="not_run",
            source_freshness_label="not_checked",
            present_provenance_fields=no_fields,
            expected_shadow_label="verification_disabled_passthrough_shadow",
            expected_action="preserve_existing_bundle_behavior",
            request_fingerprint="sha256:shadow-disabled-request",
            context_fingerprint="sha256:shadow-disabled-context",
            response_fingerprint=None,
            verification_bundle_fingerprint=None,
            reason_codes=("runtime_verification_disabled", "cache_authority_unavailable"),
        ),
        _ShadowPathSpec(
            path_id="missing_bundle_fail_closed_shadow",
            path_family="insight_route",
            route_label="missing_verification_bundle",
            runner_scenario_id="admission_blocked_candidate",
            verification_bundle_state="missing",
            verification_overall_status="missing",
            verification_admission_allowed=False,
            rag_state="not_used",
            runtime_validation_state="not_run",
            source_freshness_label="not_checked",
            present_provenance_fields=no_fields,
            expected_shadow_label="blocked_verification_bundle_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-missing-bundle-request",
            context_fingerprint="sha256:shadow-missing-bundle-context",
            response_fingerprint=None,
            verification_bundle_fingerprint=None,
            reason_codes=("verification_bundle_missing", "fail_closed"),
        ),
        _ShadowPathSpec(
            path_id="blocked_bundle_fail_closed_shadow",
            path_family="philosophical_runtime_verification",
            route_label="blocked_verification_bundle",
            runner_scenario_id="admission_blocked_candidate",
            verification_bundle_state="fail",
            verification_overall_status="fail",
            verification_admission_allowed=False,
            rag_state="validated_context",
            runtime_validation_state="failed",
            source_freshness_label="fresh",
            present_provenance_fields=(
                "input_digest",
                "prompt_digest",
                "context_item_digests",
                "prompt_char_count",
                "prompt_trimmed",
                "verification_hops",
                "verification_calls",
            ),
            expected_shadow_label="blocked_verification_bundle_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-blocked-bundle-request",
            context_fingerprint="sha256:shadow-blocked-bundle-context",
            response_fingerprint=None,
            verification_bundle_fingerprint="sha256:shadow-blocked-bundle",
            reason_codes=("verification_failed", "answer_digest_missing"),
        ),
        _ShadowPathSpec(
            path_id="kill_switch_request_disabled_shadow",
            path_family="insight_route",
            route_label="request_disabled",
            runner_scenario_id="kill_switch_request_disabled",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="not_used",
            runtime_validation_state="passed",
            source_freshness_label="fresh",
            present_provenance_fields=all_fields,
            expected_shadow_label="blocked_stop_rule_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-kill-switch-request",
            context_fingerprint="sha256:shadow-kill-switch-context",
            response_fingerprint="sha256:shadow-kill-switch-response",
            verification_bundle_fingerprint="sha256:shadow-kill-switch-bundle",
            reason_codes=("kill_switch_disabled", "request_disabled"),
        ),
        _ShadowPathSpec(
            path_id="blocked_surface_shadow",
            path_family="insight_route",
            route_label="blocked_surface",
            runner_scenario_id="blocked_surface_candidate",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="not_used",
            runtime_validation_state="passed",
            source_freshness_label="fresh",
            present_provenance_fields=all_fields,
            expected_shadow_label="blocked_false_hit_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-blocked-surface-request",
            context_fingerprint="sha256:shadow-blocked-surface-context",
            response_fingerprint="sha256:shadow-blocked-surface-response",
            verification_bundle_fingerprint="sha256:shadow-blocked-surface-bundle",
            reason_codes=("blocked_surface", "shadow_block"),
        ),
        _ShadowPathSpec(
            path_id="policy_mismatch_shadow",
            path_family="rag_orchestration",
            route_label="policy_mismatch",
            runner_scenario_id="policy_mismatch_negative_control",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="validated_context",
            runtime_validation_state="passed",
            source_freshness_label="policy_mismatch",
            present_provenance_fields=all_fields,
            expected_shadow_label="blocked_false_hit_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-policy-mismatch-request",
            context_fingerprint="sha256:shadow-policy-mismatch-context",
            response_fingerprint="sha256:shadow-policy-mismatch-response",
            verification_bundle_fingerprint="sha256:shadow-policy-mismatch-bundle",
            reason_codes=("policy_mismatch", "shadow_block"),
        ),
        _ShadowPathSpec(
            path_id="model_mismatch_shadow",
            path_family="insight_route",
            route_label="model_mismatch",
            runner_scenario_id="model_mismatch_negative_control",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="not_used",
            runtime_validation_state="passed",
            source_freshness_label="model_mismatch",
            present_provenance_fields=all_fields,
            expected_shadow_label="blocked_false_hit_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-model-mismatch-request",
            context_fingerprint="sha256:shadow-model-mismatch-context",
            response_fingerprint="sha256:shadow-model-mismatch-response",
            verification_bundle_fingerprint="sha256:shadow-model-mismatch-bundle",
            reason_codes=("model_mismatch", "shadow_block"),
        ),
        _ShadowPathSpec(
            path_id="tier_mismatch_shadow",
            path_family="insight_route",
            route_label="tier_mismatch",
            runner_scenario_id="tier_mismatch_negative_control",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="not_used",
            runtime_validation_state="passed",
            source_freshness_label="tier_mismatch",
            present_provenance_fields=all_fields,
            expected_shadow_label="blocked_false_hit_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-tier-mismatch-request",
            context_fingerprint="sha256:shadow-tier-mismatch-context",
            response_fingerprint="sha256:shadow-tier-mismatch-response",
            verification_bundle_fingerprint="sha256:shadow-tier-mismatch-bundle",
            reason_codes=("tier_mismatch", "shadow_block"),
        ),
        _ShadowPathSpec(
            path_id="context_mismatch_shadow",
            path_family="rag_orchestration",
            route_label="context_mismatch",
            runner_scenario_id="context_leakage_negative_control",
            verification_bundle_state="pass",
            verification_overall_status="pass",
            verification_admission_allowed=True,
            rag_state="validated_context",
            runtime_validation_state="passed",
            source_freshness_label="context_mismatch",
            present_provenance_fields=all_fields,
            expected_shadow_label="blocked_false_hit_shadow",
            expected_action="shadow_block",
            request_fingerprint="sha256:shadow-context-mismatch-request",
            context_fingerprint="sha256:shadow-context-mismatch-context",
            response_fingerprint="sha256:shadow-context-mismatch-response",
            verification_bundle_fingerprint="sha256:shadow-context-mismatch-bundle",
            reason_codes=("context_mismatch", "shadow_block"),
        ),
    )
    return MappingProxyType({spec.path_id: spec for spec in specs})


def _authority_flags() -> Mapping[str, JsonValue]:
    flags: dict[str, JsonValue] = {key: False for key in AUTHORITY_FALSE_KEYS}
    flags["semantic_cache_gate_status"] = SEMANTIC_CACHE_GATE_STATUS
    return flags


def _source_refs() -> tuple[Mapping[str, JsonValue], ...]:
    return (
        {
            "path": SOURCE_IDS["semantic_cache_offline_runner"],
            "symbol": "compose_semantic_cache_offline_admission_report",
        },
        {"path": SOURCE_IDS["verification_contracts"], "symbol": "VerificationBundle"},
        {"path": SOURCE_IDS["verification_contracts"], "symbol": "VerificationProvenance"},
        {"path": SOURCE_IDS["insight_runtime"], "symbol": "prepare_insight_runtime"},
        {"path": SOURCE_IDS["rag_orchestration"], "symbol": "RAGOrchestrationResult"},
        {"path": SOURCE_IDS["philosophical_runtime"], "symbol": "RuntimeResult"},
        {"path": SOURCE_IDS["semantic_cache_gate"], "symbol": "semantic_cache_gate_status"},
    )


def _evidence_asset(payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    fingerprint = _stable_fingerprint(payload)
    return {
        "asset_type": "semantic_cache_shadow_admission_harness_report",
        "artifact_fingerprint": fingerprint,
        "idempotency_key": "idem:semantic-cache-shadow-admission-harness:"
        f"{fingerprint.removeprefix('sha256:')[:16]}",
        "upstream_assets": [
            {
                "asset_id": "semantic_cache_offline_admission_runner_report",
                "asset_type": "offline_admission_report",
                "fingerprint": "sha256:semantic-cache-offline-admission-runner-v1",
            },
            {
                "asset_id": "verification_provenance_contracts",
                "asset_type": "verification_bundle_contract",
                "fingerprint": "sha256:verification-provenance-contracts-v1",
            },
            {
                "asset_id": "semantic_cache_gate_status",
                "asset_type": "roadmap_gate_contract",
                "fingerprint": "sha256:semantic-cache-gate-closed-v1",
            },
        ],
        "replay_behavior": "deterministic_static_replay_safe",
        "admission_behavior": "metadata_only_shadow_report_no_runtime_admission",
    }


def _stable_fingerprint(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _normalize_path_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    if not values:
        raise ValueError("path_ids must be non-empty")
    observed: set[str] = set()
    for value in values:
        token = _validate_token("path_id", value)
        if token not in PATH_IDS:
            raise ValueError(f"unsupported path_id: {token}")
        if token in observed:
            raise ValueError("path_ids contains duplicate entries")
        observed.add(token)
    missing = set(PATH_IDS) - observed
    if missing:
        raise ValueError("path_ids must include all default paths")
    return tuple(path_id for path_id in PATH_IDS if path_id in observed)


def _normalize_provenance_fields(values: tuple[str, ...]) -> tuple[str, ...]:
    observed: set[str] = set()
    normalized: list[str] = []
    for value in values:
        token = _validate_token("provenance_field", value)
        if token not in PROVENANCE_FIELD_IDS:
            raise ValueError(f"unsupported provenance field: {token}")
        if token in observed:
            raise ValueError("present_provenance_fields contains duplicate entries")
        observed.add(token)
        normalized.append(token)
    return tuple(field for field in PROVENANCE_FIELD_IDS if field in observed)


def _missing_provenance_fields(values: tuple[str, ...]) -> tuple[str, ...]:
    present = set(values)
    return tuple(field for field in PROVENANCE_FIELD_IDS if field not in present)


def _normalize_required_tokens(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if not values:
        raise ValueError(f"{name} must be non-empty")
    observed: set[str] = set()
    normalized: list[str] = []
    for value in values:
        token = _validate_token(name, value)
        if token in observed:
            raise ValueError(f"{name} contains duplicate entries")
        observed.add(token)
        normalized.append(token)
    return tuple(normalized)


def _merge_reason_codes(left: tuple[str, ...], right: list[str]) -> list[JsonValue]:
    values: list[JsonValue] = []
    observed: set[str] = set()
    for value in (*left, *tuple(right)):
        token = _validate_token("reason_code", value)
        if token not in observed:
            observed.add(token)
            values.append(token)
    return values


def _json_string_list(values: list[str]) -> list[JsonValue]:
    items: list[JsonValue] = []
    items.extend(values)
    return items


def _scenario_string(scenario: Mapping[str, JsonValue], key: str) -> str:
    value = scenario.get(key)
    if not isinstance(value, str):
        raise ValueError(f"scenario {key} must be a string")
    return value


def _scenario_optional_string(scenario: Mapping[str, JsonValue], key: str) -> str | None:
    value = scenario.get(key)
    if value is None or isinstance(value, str):
        return value
    raise ValueError(f"scenario {key} must be a string or null")


def _scenario_optional_int(scenario: Mapping[str, JsonValue], key: str) -> int | None:
    value = scenario.get(key)
    if value is None or isinstance(value, int):
        return value
    raise ValueError(f"scenario {key} must be an integer or null")


def _scenario_bool(scenario: Mapping[str, JsonValue], key: str) -> bool:
    value = scenario.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"scenario {key} must be a boolean")
    return value


def _scenario_string_list(scenario: Mapping[str, JsonValue], key: str) -> list[str]:
    value = scenario.get(key)
    if not isinstance(value, list):
        raise ValueError(f"scenario {key} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"scenario {key} entries must be strings")
        items.append(item)
    return items


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


def _validate_fingerprint(name: str, value: str) -> str:
    token = _validate_token(name, value)
    if not _DIGEST_PREFIX_RE.match(token):
        raise ValueError(f"{name} must be a sha256 label")
    return token


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

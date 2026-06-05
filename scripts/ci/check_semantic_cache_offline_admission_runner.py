#!/usr/bin/env python3
"""Deterministic guard for the semantic-cache offline admission runner report."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.ai.semantic_cache_offline_admission_runner import (
    AUTHORITY_FALSE_KEYS,
    DEFAULT_PRODUCED_AT,
    GENERATED_AT,
    GENERATION_MODE,
    PHASE_IDS,
    REDACTION_ASSERTION_KEYS,
    REPORT_ID,
    REPORT_VERSION,
    SCENARIO_IDS,
    SCHEMA_VERSION,
    SCOPE,
    SOURCE_IDS,
    SEMANTIC_CACHE_GATE_STATUS,
    build_default_semantic_cache_offline_admission_input,
    compose_semantic_cache_offline_admission_report,
    to_stable_mapping,
)

DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT.json"
)
DEFAULT_REPORT_SCHEMA = DEFAULT_REPORT.with_suffix(".schema.json")

TOP_LEVEL_KEYS: tuple[str, ...] = (
    "schema_version",
    "report_id",
    "report_version",
    "generated_at",
    "scope",
    "generation_mode",
    "source_ids",
    "authority_flags",
    "phase_results",
    "scenario_results",
    "backend_label_context",
    "final_admission_decision",
    "redaction_assertions",
    "source_refs",
)
AUTHORITY_FLAG_KEYS: tuple[str, ...] = (
    *AUTHORITY_FALSE_KEYS,
    "semantic_cache_gate_status",
)
PHASE_RESULT_KEYS: tuple[str, ...] = (
    "phase_id",
    "scenario_count",
    "scenario_ids",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)
PHASE_WITH_RESULTS_KEYS: tuple[str, ...] = (*PHASE_RESULT_KEYS, "results")
PHASE_SC_G5_KEYS: tuple[str, ...] = (
    *PHASE_RESULT_KEYS,
    "matrix_id",
    "final_decision",
    "candidate_decisions",
)
PHASE_SC_G2_RESULT_KEYS: tuple[str, ...] = (
    "cache_read_allowed",
    "cache_write_allowed",
    "checked_record_count",
    "lookup_decision",
    "match_mode",
    "matched_record_id",
    "reason_codes",
    "request_fingerprint",
    "scenario_id",
    "score_bps",
    "serving_allowed",
)
PHASE_SC_G3_RESULT_KEYS: tuple[str, ...] = (
    "allowed",
    "audit_event_id",
    "blocking_reasons",
    "cache_read_allowed",
    "cache_write_allowed",
    "evaluation_id",
    "fallback_rate_bps",
    "false_hit_rate_bps",
    "is_false_hit",
    "metrics_id",
    "outcome_class",
    "reason_codes",
    "rollback_required",
    "scenario_id",
    "serving_allowed",
    "stop_decision_id",
    "stop_serving",
)
PHASE_SC_G4_RESULT_KEYS: tuple[str, ...] = (
    "cache_read_allowed",
    "cache_write_allowed",
    "candidate_record_id",
    "decision",
    "decision_id",
    "match_mode",
    "reason_codes",
    "scenario_id",
    "score_bps",
    "serving_allowed",
)
SCENARIO_RESULT_KEYS: tuple[str, ...] = (
    "scenario_id",
    "risk_class",
    "expected_action",
    "record_id",
    "request_fingerprint",
    "response_fingerprint",
    "source_fingerprints",
    "policy_version",
    "provider_key",
    "model_key",
    "user_tier",
    "context_fingerprint",
    "transparency_notice_id",
    "lookup_decision",
    "match_mode",
    "score_bps",
    "audit_event_id",
    "false_hit_outcome",
    "false_hit_allowed",
    "false_hit_is_false_hit",
    "false_hit_reason_codes",
    "false_hit_blocking_reasons",
    "metrics_id",
    "stop_serving",
    "rollback_required",
    "stop_reason_codes",
    "bounded_decision",
    "bounded_decision_id",
    "bounded_reason_codes",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)
BACKEND_CONTEXT_KEYS: tuple[str, ...] = (
    "matrix_id",
    "policy_version",
    "backend_labels",
    "final_decision",
    "candidate_decisions",
    "runtime_allowed",
    "implementation_allowed",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)
BACKEND_DECISION_KEYS: tuple[str, ...] = (
    "backend_label",
    "candidate_id",
    "decision",
    "decision_id",
    "implementation_allowed",
    "metadata",
    "policy_version",
    "reason_codes",
    "rejected_candidate_ids",
    "runtime_allowed",
    "selected_backend_label",
    "selected_candidate_id",
)
FINAL_DECISION_KEYS: tuple[str, ...] = (
    "decision",
    "reason_codes",
    "semantic_cache_gate_status",
    "runtime_allowed",
    "implementation_allowed",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)
SOURCE_REF_KEYS: tuple[str, ...] = ("path", "symbol")

FORBIDDEN_KEY_NAMES = frozenset(
    {
        "raw_query",
        "normalized_query",
        "raw_prompt",
        "raw_input",
        "raw_context",
        "raw_answer",
        "raw_response",
        "prompt_text",
        "context_text",
        "answer_text",
        "response_text",
        "provider_payload",
        "provider_log",
        "provider_logs",
        "workflow_log",
        "workflow_logs",
        "slack_payload",
        "operator_artifact",
        "operator_artifacts",
        "local_path",
        "token",
        "secret",
        "health_data",
        "user_data",
    }
)
FORBIDDEN_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "absolute local path",
        re.compile(
            r"(?<!\w)(?:file://)?/(?:Users|private|var|tmp|Volumes|home|opt|etc|root|"
            r"workspace|workspaces|app|srv|mnt)(?:/[^\s:;,'\")]+)+",
            re.IGNORECASE,
        ),
    ),
    ("windows local path", re.compile(r"\b[A-Za-z]:\\(?:[^\s:;,'\")]+\\?)+")),
    (
        "secret token",
        re.compile(
            r"(?i)\b(?:xox[abprs]-|xapp-|github_pat_|gh[pousr]_|ghs_|"
            r"sk-[a-z0-9]|bearer\s+)[^\s,;]+"
        ),
    ),
    (
        "secret assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|token|secret|password|private[_-]?key|server_salt)"
            r"\s*[:=]\s*[^\s,;]+"
        ),
    ),
    ("slack id", re.compile(r"\b[UTC][A-Z0-9]{8,}\b")),
    (
        "diagnostic log label",
        re.compile(r"(?i)\b(?:provider[_ -]?log|workflow[_ -]?log)\s*[:=]\s*[^\s,;]+"),
    ),
    (
        "raw semantic-cache sample",
        re.compile(
            r"(?i)\b(?:plan protein breakfast|breakfast protein plan|"
            r"reduce evening cravings?|hydration walk)\b"
        ),
    ),
    (
        "sensitive domain text",
        re.compile(
            r"(?i)\b(?:healthkit|diagnosis|symptom|medical|account[_ -]?truth|"
            r"billing|auth(?:entication)?[_ -]?truth|legal[_ -]?truth)\b"
        ),
    ),
)


def render_semantic_cache_offline_admission_runner_report() -> tuple[str, list[str]]:
    report = compose_semantic_cache_offline_admission_report(
        build_default_semantic_cache_offline_admission_input(
            produced_at=DEFAULT_PRODUCED_AT,
        )
    )
    return json.dumps(to_stable_mapping(report), indent=2, ensure_ascii=False) + "\n", []


def render_semantic_cache_offline_admission_runner_schema() -> str:
    return json.dumps(_expected_schema(), indent=2, ensure_ascii=False) + "\n"


def validate_semantic_cache_offline_admission_runner_report(
    *,
    report_text: str,
    schema_text: str,
) -> list[str]:
    errors: list[str] = []
    expected_report, render_errors = render_semantic_cache_offline_admission_runner_report()
    errors.extend(render_errors)

    report_obj, report_parse_errors = _load_json_no_duplicate_keys(
        report_text,
        invalid_prefix="semantic cache offline admission runner report invalid JSON",
        duplicate_prefix="semantic cache offline admission runner report duplicate key",
    )
    schema_obj, schema_parse_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="semantic cache offline admission runner schema invalid JSON",
        duplicate_prefix="semantic cache offline admission runner schema duplicate key",
    )
    errors.extend(report_parse_errors)
    errors.extend(schema_parse_errors)
    if errors:
        return errors

    report, report_type_errors = _as_object(
        report_obj,
        label="semantic cache offline admission runner report",
    )
    schema, schema_type_errors = _as_object(
        schema_obj,
        label="semantic cache offline admission runner schema",
    )
    errors.extend(report_type_errors)
    errors.extend(schema_type_errors)
    if errors:
        return errors

    if report_text != expected_report:
        errors.append(
            "semantic cache offline admission runner report drift: "
            "regenerate from current contracts"
        )
    if schema != _expected_schema():
        errors.append("semantic cache offline admission runner schema drift: regenerate schema")
    errors.extend(_validate_report_shape(report))
    errors.extend(_validate_no_raw_leaks(report, label="semantic cache offline admission report"))
    errors.extend(_validate_no_raw_leaks(schema, label="semantic cache offline admission schema"))
    return errors


def _expected_schema() -> Mapping[str, object]:
    bool_false: dict[str, object] = {"type": "boolean", "const": False}
    string: dict[str, object] = {"type": "string"}
    nullable_string: dict[str, object] = {"type": ["string", "null"]}
    int_or_null: dict[str, object] = {"type": ["integer", "null"], "minimum": 0}
    closed_flags = {key: bool_false for key in AUTHORITY_FALSE_KEYS} | {
        "semantic_cache_gate_status": {"type": "string", "const": SEMANTIC_CACHE_GATE_STATUS}
    }
    scenario_properties: dict[str, object] = {
        key: string
        for key in (
            "scenario_id",
            "risk_class",
            "expected_action",
            "record_id",
            "request_fingerprint",
            "response_fingerprint",
            "policy_version",
            "provider_key",
            "model_key",
            "user_tier",
            "context_fingerprint",
            "transparency_notice_id",
            "lookup_decision",
            "audit_event_id",
            "false_hit_outcome",
            "metrics_id",
            "bounded_decision",
            "bounded_decision_id",
        )
    }
    scenario_properties.update(
        {
            "source_fingerprints": {"type": "array", "items": string},
            "match_mode": nullable_string,
            "score_bps": int_or_null,
            "false_hit_allowed": {"type": "boolean"},
            "false_hit_is_false_hit": {"type": "boolean"},
            "false_hit_reason_codes": {"type": "array", "items": string},
            "false_hit_blocking_reasons": {"type": "array", "items": string},
            "stop_serving": {"type": "boolean"},
            "rollback_required": {"type": "boolean"},
            "stop_reason_codes": {"type": "array", "items": string},
            "bounded_reason_codes": {"type": "array", "items": string},
            "cache_read_allowed": bool_false,
            "cache_write_allowed": bool_false,
            "serving_allowed": bool_false,
        }
    )
    backend_decision_properties: dict[str, object] = {
        "backend_label": nullable_string,
        "candidate_id": nullable_string,
        "decision": string,
        "decision_id": string,
        "implementation_allowed": bool_false,
        "metadata": {
            "type": "object",
            "additionalProperties": False,
            "required": ["decision_scope", "serves_cached_payload"],
            "properties": {
                "decision_scope": {"type": "string", "const": "label_only"},
                "serves_cached_payload": bool_false,
            },
        },
        "policy_version": string,
        "reason_codes": {"type": "array", "items": string},
        "rejected_candidate_ids": {"type": "array", "items": string},
        "runtime_allowed": bool_false,
        "selected_backend_label": nullable_string,
        "selected_candidate_id": nullable_string,
    }
    backend_decision_schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "required": list(BACKEND_DECISION_KEYS),
        "properties": backend_decision_properties,
    }
    source_ids_schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "required": list(SOURCE_IDS.keys()),
        "properties": {
            key: {"type": "string", "const": value} for key, value in SOURCE_IDS.items()
        },
    }
    phase_common_properties: dict[str, object] = {
        "phase_id": string,
        "scenario_count": {"type": "integer", "const": len(SCENARIO_IDS)},
        "scenario_ids": {"type": "array", "items": string},
        "cache_read_allowed": bool_false,
        "cache_write_allowed": bool_false,
        "serving_allowed": bool_false,
    }
    sc_g2_result_properties: dict[str, object] = {
        "cache_read_allowed": bool_false,
        "cache_write_allowed": bool_false,
        "checked_record_count": {"type": "integer", "minimum": 0},
        "lookup_decision": string,
        "match_mode": nullable_string,
        "matched_record_id": nullable_string,
        "reason_codes": {"type": "array", "items": string},
        "request_fingerprint": string,
        "scenario_id": string,
        "score_bps": int_or_null,
        "serving_allowed": bool_false,
    }
    sc_g3_result_properties: dict[str, object] = {
        "allowed": {"type": "boolean"},
        "audit_event_id": string,
        "blocking_reasons": {"type": "array", "items": string},
        "cache_read_allowed": bool_false,
        "cache_write_allowed": bool_false,
        "evaluation_id": string,
        "fallback_rate_bps": {"type": "integer", "minimum": 0},
        "false_hit_rate_bps": {"type": "integer", "minimum": 0},
        "is_false_hit": {"type": "boolean"},
        "metrics_id": string,
        "outcome_class": string,
        "reason_codes": {"type": "array", "items": string},
        "rollback_required": {"type": "boolean"},
        "scenario_id": string,
        "serving_allowed": bool_false,
        "stop_decision_id": string,
        "stop_serving": {"type": "boolean"},
    }
    sc_g4_result_properties: dict[str, object] = {
        "cache_read_allowed": bool_false,
        "cache_write_allowed": bool_false,
        "candidate_record_id": nullable_string,
        "decision": string,
        "decision_id": string,
        "match_mode": nullable_string,
        "reason_codes": {"type": "array", "items": string},
        "scenario_id": string,
        "score_bps": int_or_null,
        "serving_allowed": bool_false,
    }
    phase_results_item_schema: dict[str, object] = {
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(PHASE_WITH_RESULTS_KEYS),
                "properties": phase_common_properties
                | {
                    "phase_id": {"type": "string", "const": "sc_g2_exact_fuzzy"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": list(PHASE_SC_G2_RESULT_KEYS),
                            "properties": sc_g2_result_properties,
                        },
                    },
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(PHASE_WITH_RESULTS_KEYS),
                "properties": phase_common_properties
                | {
                    "phase_id": {
                        "type": "string",
                        "const": "sc_g3_observability_false_hit",
                    },
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": list(PHASE_SC_G3_RESULT_KEYS),
                            "properties": sc_g3_result_properties,
                        },
                    },
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(PHASE_WITH_RESULTS_KEYS),
                "properties": phase_common_properties
                | {
                    "phase_id": {
                        "type": "string",
                        "const": "sc_g4_bounded_insight",
                    },
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": list(PHASE_SC_G4_RESULT_KEYS),
                            "properties": sc_g4_result_properties,
                        },
                    },
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(PHASE_SC_G5_KEYS),
                "properties": phase_common_properties
                | {
                    "phase_id": {
                        "type": "string",
                        "const": "sc_g5_backend_label_context",
                    },
                    "matrix_id": string,
                    "final_decision": backend_decision_schema,
                    "candidate_decisions": {
                        "type": "array",
                        "items": backend_decision_schema,
                    },
                },
            },
        ]
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": list(TOP_LEVEL_KEYS),
        "properties": {
            "schema_version": {"type": "string", "const": SCHEMA_VERSION},
            "report_id": {"type": "string", "const": REPORT_ID},
            "report_version": {"type": "string", "const": REPORT_VERSION},
            "generated_at": {"type": "string", "const": GENERATED_AT},
            "scope": {"type": "string", "const": SCOPE},
            "generation_mode": {"type": "string", "const": GENERATION_MODE},
            "source_ids": source_ids_schema,
            "authority_flags": {
                "type": "object",
                "additionalProperties": False,
                "required": list(AUTHORITY_FLAG_KEYS),
                "properties": closed_flags,
            },
            "phase_results": {
                "type": "array",
                "items": phase_results_item_schema,
            },
            "scenario_results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(SCENARIO_RESULT_KEYS),
                    "properties": scenario_properties,
                },
            },
            "backend_label_context": {
                "type": "object",
                "additionalProperties": False,
                "required": list(BACKEND_CONTEXT_KEYS),
                "properties": {
                    "matrix_id": string,
                    "policy_version": string,
                    "backend_labels": {"type": "array", "items": string},
                    "final_decision": backend_decision_schema,
                    "candidate_decisions": {
                        "type": "array",
                        "items": backend_decision_schema,
                    },
                    "runtime_allowed": bool_false,
                    "implementation_allowed": bool_false,
                    "cache_read_allowed": bool_false,
                    "cache_write_allowed": bool_false,
                    "serving_allowed": bool_false,
                },
            },
            "final_admission_decision": {
                "type": "object",
                "additionalProperties": False,
                "required": list(FINAL_DECISION_KEYS),
                "properties": {
                    "decision": string,
                    "reason_codes": {"type": "array", "items": string},
                    "semantic_cache_gate_status": {
                        "type": "string",
                        "const": SEMANTIC_CACHE_GATE_STATUS,
                    },
                    "runtime_allowed": bool_false,
                    "implementation_allowed": bool_false,
                    "cache_read_allowed": bool_false,
                    "cache_write_allowed": bool_false,
                    "serving_allowed": bool_false,
                },
            },
            "redaction_assertions": {
                "type": "object",
                "additionalProperties": False,
                "required": list(REDACTION_ASSERTION_KEYS),
                "properties": {
                    key: {"type": "boolean", "const": True} for key in REDACTION_ASSERTION_KEYS
                },
            },
            "source_refs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(SOURCE_REF_KEYS),
                    "properties": {"path": string, "symbol": string},
                },
            },
        },
    }


def _validate_report_shape(report: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_keys(report, TOP_LEVEL_KEYS, label="report"))
    for key, expected in (
        ("schema_version", SCHEMA_VERSION),
        ("report_id", REPORT_ID),
        ("report_version", REPORT_VERSION),
        ("generated_at", GENERATED_AT),
        ("scope", SCOPE),
        ("generation_mode", GENERATION_MODE),
    ):
        if report.get(key) != expected:
            errors.append(f"report {key} must be {expected}")
    authority = _as_mapping(report.get("authority_flags"), "authority_flags", errors)
    if authority:
        errors.extend(_validate_keys(authority, AUTHORITY_FLAG_KEYS, label="authority_flags"))
        _validate_closed_authority(authority, errors=errors, label="authority_flags")
    redaction = _as_mapping(report.get("redaction_assertions"), "redaction_assertions", errors)
    if redaction:
        errors.extend(
            _validate_keys(redaction, REDACTION_ASSERTION_KEYS, label="redaction_assertions")
        )
        for key in REDACTION_ASSERTION_KEYS:
            if redaction.get(key) is not True:
                errors.append(f"redaction_assertions.{key} must remain true")
    errors.extend(_validate_phase_results(report.get("phase_results")))
    errors.extend(_validate_scenario_results(report.get("scenario_results")))
    errors.extend(_validate_backend_context(report.get("backend_label_context")))
    final_decision = _as_mapping(
        report.get("final_admission_decision"), "final_admission_decision", errors
    )
    if final_decision:
        errors.extend(
            _validate_keys(
                final_decision,
                FINAL_DECISION_KEYS,
                label="final_admission_decision",
            )
        )
        _validate_closed_authority(final_decision, errors=errors, label="final_admission_decision")
    errors.extend(_validate_source_refs(report.get("source_refs")))
    return errors


def _validate_phase_results(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["phase_results must be a list"]
    observed_ids: list[str] = []
    for item in value:
        phase = _as_object_inline(item, label="phase_results item", errors=errors)
        if not phase:
            continue
        phase_id = phase.get("phase_id")
        if isinstance(phase_id, str):
            observed_ids.append(phase_id)
        expected_keys = (
            PHASE_SC_G5_KEYS
            if phase_id == "sc_g5_backend_label_context"
            else PHASE_WITH_RESULTS_KEYS
        )
        errors.extend(_validate_keys(phase, expected_keys, label=f"phase_results.{phase_id}"))
        if phase.get("scenario_count") != len(SCENARIO_IDS):
            errors.append(f"phase_results.{phase_id}.scenario_count mismatch")
        if phase.get("scenario_ids") != list(SCENARIO_IDS):
            errors.append(f"phase_results.{phase_id}.scenario_ids mismatch")
        _validate_closed_authority(phase, errors=errors, label=f"phase_results.{phase_id}")
    if observed_ids != list(PHASE_IDS):
        errors.append("phase_results phase order mismatch")
    return errors


def _validate_scenario_results(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["scenario_results must be a list"]
    observed_ids: list[str] = []
    for item in value:
        scenario = _as_object_inline(item, label="scenario_results item", errors=errors)
        if not scenario:
            continue
        scenario_id = scenario.get("scenario_id")
        if isinstance(scenario_id, str):
            observed_ids.append(scenario_id)
        errors.extend(
            _validate_keys(scenario, SCENARIO_RESULT_KEYS, label=f"scenario.{scenario_id}")
        )
        _validate_closed_authority(scenario, errors=errors, label=f"scenario.{scenario_id}")
    if observed_ids != list(SCENARIO_IDS):
        errors.append("scenario_results order mismatch")
    return errors


def _validate_backend_context(value: object) -> list[str]:
    errors: list[str] = []
    context = _as_mapping(value, "backend_label_context", errors)
    if not context:
        return errors
    errors.extend(_validate_keys(context, BACKEND_CONTEXT_KEYS, label="backend_label_context"))
    _validate_closed_authority(context, errors=errors, label="backend_label_context")
    final_decision = _as_mapping(
        context.get("final_decision"), "backend_label_context.final_decision", errors
    )
    if final_decision:
        errors.extend(
            _validate_keys(
                final_decision,
                BACKEND_DECISION_KEYS,
                label="backend_label_context.final_decision",
            )
        )
        if final_decision.get("decision") != "no_selection":
            errors.append("backend_label_context.final_decision.decision must be no_selection")
        if final_decision.get("selected_candidate_id") is not None:
            errors.append("backend_label_context must not select a candidate")
        if final_decision.get("selected_backend_label") is not None:
            errors.append("backend_label_context must not select a backend label")
        _validate_closed_authority(
            final_decision, errors=errors, label="backend_label_context.final_decision"
        )
    candidate_decisions = context.get("candidate_decisions")
    if not isinstance(candidate_decisions, list):
        errors.append("backend_label_context.candidate_decisions must be a list")
    else:
        for index, item in enumerate(candidate_decisions):
            decision = _as_object_inline(
                item,
                label=f"backend_label_context.candidate_decisions[{index}]",
                errors=errors,
            )
            if decision:
                _validate_closed_authority(
                    decision,
                    errors=errors,
                    label=f"backend_label_context.candidate_decisions[{index}]",
                )
    return errors


def _validate_source_refs(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["source_refs must be a list"]
    for index, item in enumerate(value):
        ref = _as_object_inline(item, label=f"source_refs[{index}]", errors=errors)
        if not ref:
            continue
        errors.extend(_validate_keys(ref, SOURCE_REF_KEYS, label=f"source_refs[{index}]"))
        path = ref.get("path")
        symbol = ref.get("symbol")
        if not isinstance(path, str) or path.startswith(("/", "~", ".")) or ".." in path:
            errors.append(f"source_refs[{index}].path must be repo-relative safe path")
        if not isinstance(symbol, str) or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", symbol):
            errors.append(f"source_refs[{index}].symbol must be a simple symbol")
    return errors


def _validate_closed_authority(
    values: Mapping[str, object],
    *,
    errors: list[str],
    label: str,
) -> None:
    for key in (
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
    ):
        if key in values and values.get(key) is not False:
            errors.append(f"{label}.{key} must remain false")
    if (
        "semantic_cache_gate_status" in values
        and values.get("semantic_cache_gate_status") != SEMANTIC_CACHE_GATE_STATUS
    ):
        errors.append(f"{label}.semantic_cache_gate_status must remain closed")


def _validate_no_raw_leaks(value: object, *, label: str) -> list[str]:
    errors: list[str] = []

    def _walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                if key_text in FORBIDDEN_KEY_NAMES:
                    errors.append(f"{label} forbidden key at {path}.{key_text}")
                for name, pattern in FORBIDDEN_VALUE_PATTERNS:
                    if pattern.search(key_text):
                        errors.append(f"{label} forbidden {name} in key at {path}.{key_text}")
                _walk(item, f"{path}.{key_text}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")
        elif isinstance(node, str):
            for name, pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(node):
                    errors.append(f"{label} forbidden {name} at {path}")

    _walk(value, label)
    return errors


def _load_json_no_duplicate_keys(
    text: str,
    *,
    invalid_prefix: str,
    duplicate_prefix: str,
) -> tuple[object, list[str]]:
    def _hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        seen: set[str] = set()
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in seen:
                raise ValueError(f"{duplicate_prefix}: {key}")
            seen.add(key)
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=_hook), []
    except ValueError as exc:
        return {}, [f"{invalid_prefix}: {exc}"]


def _validate_keys(
    obj: Mapping[str, object],
    expected: Sequence[str],
    *,
    label: str,
) -> list[str]:
    errors: list[str] = []
    observed = set(obj)
    expected_set = set(expected)
    for key in sorted(observed - expected_set):
        errors.append(f"{label} unknown key: {key}")
    for key in expected:
        if key not in obj:
            errors.append(f"{label} missing key: {key}")
    return errors


def _as_object(obj: object, *, label: str) -> tuple[Mapping[str, object], list[str]]:
    if not isinstance(obj, dict):
        return {}, [f"{label} must be a JSON object"]
    return obj, []


def _as_object_inline(
    obj: object,
    *,
    label: str,
    errors: list[str],
) -> Mapping[str, object]:
    if not isinstance(obj, dict):
        errors.append(f"{label} must be an object")
        return {}
    return obj


def _as_mapping(
    obj: object,
    label: str,
    errors: list[str],
) -> Mapping[str, object]:
    if not isinstance(obj, dict):
        errors.append(f"{label} must be an object")
        return {}
    return obj


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return "<external-path>"


def _write_contract_file(*, path: Path, text: str, label: str) -> list[str]:
    target = path.resolve()
    allowed_root = (REPO_ROOT / "docs" / "orchestration" / "contracts").resolve()
    if not target.is_relative_to(allowed_root):
        return [f"{label} write path must stay under docs/orchestration/contracts"]
    path.write_text(text, encoding="utf-8")
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check semantic-cache offline admission runner report determinism."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--report-schema", type=Path, default=DEFAULT_REPORT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--write-schema", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    rendered_report, render_errors = render_semantic_cache_offline_admission_runner_report()
    rendered_schema = render_semantic_cache_offline_admission_runner_schema()
    errors.extend(render_errors)

    if not args.write_schema and not args.report_schema.exists():
        errors.append(
            "semantic cache offline admission runner schema missing: "
            f"{_display_path(args.report_schema)}"
        )
    if not args.write_report and not args.report.exists():
        errors.append(
            "semantic cache offline admission runner report missing: "
            f"{_display_path(args.report)}"
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    schema_text = (
        rendered_schema if args.write_schema else args.report_schema.read_text(encoding="utf-8")
    )
    if args.write_schema:
        errors.extend(
            _write_contract_file(
                path=args.report_schema,
                text=rendered_schema,
                label="semantic cache offline admission runner schema",
            )
        )
    if args.write_report and not errors:
        errors.extend(
            validate_semantic_cache_offline_admission_runner_report(
                report_text=rendered_report,
                schema_text=schema_text,
            )
        )
        if not errors:
            errors.extend(
                _write_contract_file(
                    path=args.report,
                    text=rendered_report,
                    label="semantic cache offline admission runner report",
                )
            )
    if args.check or not (args.write_report or args.write_schema):
        if args.report.exists():
            errors.extend(
                validate_semantic_cache_offline_admission_runner_report(
                    report_text=args.report.read_text(encoding="utf-8"),
                    schema_text=args.report_schema.read_text(encoding="utf-8"),
                )
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "semantic cache offline admission runner report current: " f"{_display_path(args.report)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

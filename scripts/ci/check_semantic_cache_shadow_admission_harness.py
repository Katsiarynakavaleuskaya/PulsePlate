#!/usr/bin/env python3
"""Deterministic guard for the semantic-cache shadow admission harness report."""

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

from core.ai.semantic_cache_shadow_admission_harness import (
    AUTHORITY_FALSE_KEYS,
    DEFAULT_PRODUCED_AT,
    GENERATED_AT,
    GENERATION_MODE,
    PATH_IDS,
    PROVENANCE_FIELD_IDS,
    REDACTION_ASSERTION_KEYS,
    REPORT_ID,
    REPORT_VERSION,
    SCHEMA_VERSION,
    SCOPE,
    SOURCE_IDS,
    SEMANTIC_CACHE_GATE_STATUS,
    build_default_semantic_cache_shadow_admission_input,
    compose_semantic_cache_shadow_admission_report,
    to_stable_mapping,
)

DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT.json"
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
    "path_specs",
    "path_results",
    "projection_summary",
    "backend_label_context",
    "final_admission_decision",
    "redaction_assertions",
    "source_refs",
)
AUTHORITY_FLAG_KEYS: tuple[str, ...] = (*AUTHORITY_FALSE_KEYS, "semantic_cache_gate_status")
PATH_SPEC_KEYS: tuple[str, ...] = (
    "path_id",
    "path_family",
    "route_label",
    "runner_scenario_id",
    "verification_bundle_state",
    "verification_overall_status",
    "verification_admission_allowed",
    "rag_state",
    "runtime_validation_state",
    "source_freshness_label",
    "expected_provenance_fields",
    "present_provenance_fields",
    "missing_required_provenance_fields",
    "provenance_complete",
    "expected_shadow_label",
    "expected_action",
    "request_fingerprint",
    "context_fingerprint",
    "response_fingerprint",
    "verification_bundle_fingerprint",
    "reason_codes",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)
PATH_RESULT_KEYS: tuple[str, ...] = (
    "path_id",
    "path_family",
    "route_label",
    "runner_scenario_id",
    "verification_bundle_present",
    "verification_bundle_state",
    "verification_overall_status",
    "verification_admission_allowed",
    "provenance_complete",
    "present_provenance_fields",
    "missing_required_provenance_fields",
    "source_freshness_label",
    "rag_state",
    "runtime_validation_state",
    "lookup_decision",
    "match_mode",
    "score_bps",
    "false_hit_outcome",
    "false_hit_is_false_hit",
    "false_hit_blocking_reasons",
    "stop_serving",
    "bounded_decision",
    "bounded_reason_codes",
    "shadow_label",
    "reason_codes",
    "request_fingerprint",
    "context_fingerprint",
    "response_fingerprint",
    "verification_bundle_fingerprint",
    "semantic_cache_gate_status",
    "runtime_allowed",
    "implementation_allowed",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)
PROJECTION_SUMMARY_KEYS: tuple[str, ...] = (
    "path_count",
    "path_ids",
    "shadow_label_counts",
    "semantic_cache_gate_status",
    "runtime_allowed",
    "implementation_allowed",
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
        "input_text",
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
            r"billing[_ -]?truth|auth(?:entication)?[_ -]?truth|legal[_ -]?truth)\b"
        ),
    ),
)


def render_semantic_cache_shadow_admission_harness_report() -> tuple[str, list[str]]:
    report = compose_semantic_cache_shadow_admission_report(
        build_default_semantic_cache_shadow_admission_input(produced_at=DEFAULT_PRODUCED_AT)
    )
    return json.dumps(to_stable_mapping(report), indent=2, ensure_ascii=False) + "\n", []


def render_semantic_cache_shadow_admission_harness_schema() -> str:
    return json.dumps(_expected_schema(), indent=2, ensure_ascii=False) + "\n"


def validate_semantic_cache_shadow_admission_harness_report(
    *,
    report_text: str,
    schema_text: str,
) -> list[str]:
    errors: list[str] = []
    expected_report, render_errors = render_semantic_cache_shadow_admission_harness_report()
    errors.extend(render_errors)

    report_obj, report_parse_errors = _load_json_no_duplicate_keys(
        report_text,
        invalid_prefix="semantic cache shadow admission harness report invalid JSON",
        duplicate_prefix="semantic cache shadow admission harness report duplicate key",
    )
    schema_obj, schema_parse_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="semantic cache shadow admission harness schema invalid JSON",
        duplicate_prefix="semantic cache shadow admission harness schema duplicate key",
    )
    errors.extend(report_parse_errors)
    errors.extend(schema_parse_errors)
    if errors:
        return errors

    report, report_type_errors = _as_object(
        report_obj,
        label="semantic cache shadow admission harness report",
    )
    schema, schema_type_errors = _as_object(
        schema_obj,
        label="semantic cache shadow admission harness schema",
    )
    errors.extend(report_type_errors)
    errors.extend(schema_type_errors)
    if errors:
        return errors

    if report_text != expected_report:
        errors.append(
            "semantic cache shadow admission harness report drift: "
            "regenerate from current contracts"
        )
    if schema != _expected_schema():
        errors.append("semantic cache shadow admission harness schema drift: regenerate schema")
    errors.extend(_validate_report_shape(report))
    errors.extend(_validate_no_raw_leaks(report, label="semantic cache shadow admission report"))
    errors.extend(_validate_no_raw_leaks(schema, label="semantic cache shadow admission schema"))
    return errors


def _expected_schema() -> Mapping[str, object]:
    bool_false: dict[str, object] = {"type": "boolean", "const": False}
    bool_value: dict[str, object] = {"type": "boolean"}
    string: dict[str, object] = {"type": "string"}
    nullable_string: dict[str, object] = {"type": ["string", "null"]}
    nullable_bool: dict[str, object] = {"type": ["boolean", "null"]}
    int_or_null: dict[str, object] = {"type": ["integer", "null"], "minimum": 0}
    closed_flags = {key: bool_false for key in AUTHORITY_FALSE_KEYS} | {
        "semantic_cache_gate_status": {"type": "string", "const": SEMANTIC_CACHE_GATE_STATUS}
    }
    string_array: dict[str, object] = {"type": "array", "items": string}
    path_common_properties: dict[str, object] = {
        "path_id": string,
        "path_family": string,
        "route_label": string,
        "runner_scenario_id": string,
        "verification_bundle_state": string,
        "verification_overall_status": string,
        "verification_admission_allowed": nullable_bool,
        "rag_state": string,
        "runtime_validation_state": string,
        "source_freshness_label": string,
        "present_provenance_fields": string_array,
        "missing_required_provenance_fields": string_array,
        "request_fingerprint": string,
        "context_fingerprint": string,
        "response_fingerprint": nullable_string,
        "verification_bundle_fingerprint": nullable_string,
        "reason_codes": string_array,
    }
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
        "reason_codes": string_array,
        "rejected_candidate_ids": string_array,
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
            "source_ids": {
                "type": "object",
                "additionalProperties": False,
                "required": list(SOURCE_IDS.keys()),
                "properties": {
                    key: {"type": "string", "const": value} for key, value in SOURCE_IDS.items()
                },
            },
            "authority_flags": {
                "type": "object",
                "additionalProperties": False,
                "required": list(AUTHORITY_FLAG_KEYS),
                "properties": closed_flags,
            },
            "path_specs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(PATH_SPEC_KEYS),
                    "properties": path_common_properties
                    | {
                        "expected_provenance_fields": {
                            "type": "array",
                            "items": string,
                            "minItems": len(PROVENANCE_FIELD_IDS),
                            "maxItems": len(PROVENANCE_FIELD_IDS),
                        },
                        "provenance_complete": bool_value,
                        "expected_shadow_label": string,
                        "expected_action": string,
                        "cache_read_allowed": bool_false,
                        "cache_write_allowed": bool_false,
                        "serving_allowed": bool_false,
                    },
                },
            },
            "path_results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(PATH_RESULT_KEYS),
                    "properties": path_common_properties
                    | {
                        "verification_bundle_present": bool_value,
                        "provenance_complete": bool_value,
                        "lookup_decision": string,
                        "match_mode": nullable_string,
                        "score_bps": int_or_null,
                        "false_hit_outcome": string,
                        "false_hit_is_false_hit": bool_value,
                        "false_hit_blocking_reasons": string_array,
                        "stop_serving": bool_value,
                        "bounded_decision": string,
                        "bounded_reason_codes": string_array,
                        "shadow_label": string,
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
            },
            "projection_summary": {
                "type": "object",
                "additionalProperties": False,
                "required": list(PROJECTION_SUMMARY_KEYS),
                "properties": {
                    "path_count": {"type": "integer", "const": len(PATH_IDS)},
                    "path_ids": {"type": "array", "items": string},
                    "shadow_label_counts": {
                        "type": "object",
                        "additionalProperties": {"type": "integer", "minimum": 0},
                    },
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
            "backend_label_context": {
                "type": "object",
                "additionalProperties": False,
                "required": list(BACKEND_CONTEXT_KEYS),
                "properties": {
                    "matrix_id": string,
                    "policy_version": string,
                    "backend_labels": string_array,
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
                    "reason_codes": string_array,
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
    source_ids = _as_mapping(report.get("source_ids"), "source_ids", errors)
    if source_ids:
        errors.extend(_validate_keys(source_ids, tuple(SOURCE_IDS.keys()), label="source_ids"))
        for key, expected in SOURCE_IDS.items():
            if source_ids.get(key) != expected:
                errors.append(f"source_ids.{key} must be {expected}")
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
    errors.extend(_validate_path_specs(report.get("path_specs")))
    errors.extend(_validate_path_results(report.get("path_results"), report.get("path_specs")))
    errors.extend(_validate_projection_summary(report.get("projection_summary")))
    errors.extend(_validate_backend_context(report.get("backend_label_context")))
    final_decision = _as_mapping(
        report.get("final_admission_decision"), "final_admission_decision", errors
    )
    if final_decision:
        errors.extend(
            _validate_keys(final_decision, FINAL_DECISION_KEYS, label="final_admission_decision")
        )
        if final_decision.get("decision") != "shadow_report_only":
            errors.append("final_admission_decision.decision must be shadow_report_only")
        _validate_closed_authority(final_decision, errors=errors, label="final_admission_decision")
    errors.extend(_validate_source_refs(report.get("source_refs")))
    return errors


def _validate_path_specs(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["path_specs must be a list"]
    observed_ids: list[str] = []
    for item in value:
        spec = _as_object_inline(item, label="path_specs item", errors=errors)
        if not spec:
            continue
        path_id = spec.get("path_id")
        if isinstance(path_id, str):
            observed_ids.append(path_id)
        errors.extend(_validate_keys(spec, PATH_SPEC_KEYS, label=f"path_specs.{path_id}"))
        if spec.get("expected_provenance_fields") != list(PROVENANCE_FIELD_IDS):
            errors.append(f"path_specs.{path_id}.expected_provenance_fields mismatch")
        present = spec.get("present_provenance_fields")
        missing = spec.get("missing_required_provenance_fields")
        if isinstance(present, list) and isinstance(missing, list):
            expected_missing = [
                field for field in PROVENANCE_FIELD_IDS if field not in set(present)
            ]
            if missing != expected_missing:
                errors.append(f"path_specs.{path_id}.missing_required_provenance_fields mismatch")
            if spec.get("provenance_complete") is not (not expected_missing):
                errors.append(f"path_specs.{path_id}.provenance_complete mismatch")
        _validate_closed_authority(spec, errors=errors, label=f"path_specs.{path_id}")
    if observed_ids != list(PATH_IDS):
        errors.append("path_specs order mismatch")
    return errors


def _validate_path_results(value: object, spec_value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["path_results must be a list"]
    specs_by_id: dict[str, Mapping[str, object]] = {}
    if isinstance(spec_value, list):
        for item in spec_value:
            if isinstance(item, dict) and isinstance(item.get("path_id"), str):
                specs_by_id[item["path_id"]] = item
    observed_ids: list[str] = []
    for item in value:
        result = _as_object_inline(item, label="path_results item", errors=errors)
        if not result:
            continue
        path_id = result.get("path_id")
        if isinstance(path_id, str):
            observed_ids.append(path_id)
        errors.extend(_validate_keys(result, PATH_RESULT_KEYS, label=f"path_results.{path_id}"))
        spec = specs_by_id.get(path_id) if isinstance(path_id, str) else None
        if spec:
            if result.get("shadow_label") != spec.get("expected_shadow_label"):
                errors.append(f"path_results.{path_id}.shadow_label does not match spec")
            for key in (
                "path_family",
                "route_label",
                "runner_scenario_id",
                "verification_bundle_state",
                "verification_overall_status",
                "verification_admission_allowed",
                "rag_state",
                "runtime_validation_state",
                "source_freshness_label",
            ):
                if result.get(key) != spec.get(key):
                    errors.append(f"path_results.{path_id}.{key} does not match spec")
        _validate_closed_authority(result, errors=errors, label=f"path_results.{path_id}")
    if observed_ids != list(PATH_IDS):
        errors.append("path_results order mismatch")
    return errors


def _validate_projection_summary(value: object) -> list[str]:
    errors: list[str] = []
    summary = _as_mapping(value, "projection_summary", errors)
    if not summary:
        return errors
    errors.extend(_validate_keys(summary, PROJECTION_SUMMARY_KEYS, label="projection_summary"))
    if summary.get("path_count") != len(PATH_IDS):
        errors.append("projection_summary.path_count mismatch")
    if summary.get("path_ids") != list(PATH_IDS):
        errors.append("projection_summary.path_ids mismatch")
    counts = summary.get("shadow_label_counts")
    if not isinstance(counts, dict):
        errors.append("projection_summary.shadow_label_counts must be an object")
    _validate_closed_authority(summary, errors=errors, label="projection_summary")
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
    for key in AUTHORITY_FALSE_KEYS:
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
        description="Check semantic-cache shadow admission harness report determinism."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--report-schema", type=Path, default=DEFAULT_REPORT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--write-schema", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    rendered_report, render_errors = render_semantic_cache_shadow_admission_harness_report()
    rendered_schema = render_semantic_cache_shadow_admission_harness_schema()
    errors.extend(render_errors)

    if not args.write_schema and not args.report_schema.exists():
        errors.append(
            "semantic cache shadow admission harness schema missing: "
            f"{_display_path(args.report_schema)}"
        )
    if not args.write_report and not args.report.exists():
        errors.append(
            "semantic cache shadow admission harness report missing: "
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
                label="semantic cache shadow admission harness schema",
            )
        )
    if args.write_report and not errors:
        errors.extend(
            validate_semantic_cache_shadow_admission_harness_report(
                report_text=rendered_report,
                schema_text=schema_text,
            )
        )
        if not errors:
            errors.extend(
                _write_contract_file(
                    path=args.report,
                    text=rendered_report,
                    label="semantic cache shadow admission harness report",
                )
            )
    if args.check or not (args.write_report or args.write_schema):
        if args.report.exists():
            errors.extend(
                validate_semantic_cache_shadow_admission_harness_report(
                    report_text=args.report.read_text(encoding="utf-8"),
                    schema_text=args.report_schema.read_text(encoding="utf-8"),
                )
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "semantic cache shadow admission harness report current: " f"{_display_path(args.report)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

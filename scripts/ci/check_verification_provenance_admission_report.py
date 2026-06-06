#!/usr/bin/env python3
"""Deterministic guard for VerificationBundle provenance admission reporting."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "VERIFICATION_PROVENANCE_ADMISSION_REPORT.json"
)
DEFAULT_REPORT_SCHEMA = DEFAULT_REPORT.with_suffix(".schema.json")


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return "<external-path>"


REPORT_ID = "verification_provenance_admission_report"
REPORT_VERSION = "2026-06-05"
GENERATED_AT = "static-2026-06-05"
SCHEMA_VERSION = "1.0"
SCOPE = "internal_only_verification_bundle_provenance_admission_report"
GENERATION_MODE = "deterministic_static_ast_source_only"
SEMANTIC_CACHE_GATE_STATUS = "closed"

VERIFICATION_CONTRACT_PATH = "core/verification/contracts.py"
VERIFICATION_REGISTRY_PATH = "core/verification/registry.py"
RAG_ORCHESTRATION_PATH = "core/rag/orchestration.py"
PHILOSOPHICAL_RUNTIME_PATH = "core/insight/philosophical_runtime.py"
APPLICATION_SERVICE_PATH = "app/services/insight_application_service.py"
SEMANTIC_CACHE_GATE_PATH = "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"

PATH_CATEGORY_IDS: tuple[str, ...] = (
    "rag_pre_generation",
    "rag_runtime_merged",
    "direct_local_non_verification_first_answer",
    "runtime_verification_disabled_passthrough",
    "fail_closed_missing_bundle_with_provenance",
)
NON_ADMITTED_PATH_CATEGORY_IDS = frozenset(
    {
        "direct_local_non_verification_first_answer",
        "runtime_verification_disabled_passthrough",
        "fail_closed_missing_bundle_with_provenance",
    }
)
ADMITTED_PATH_CATEGORY_IDS = tuple(
    category_id
    for category_id in PATH_CATEGORY_IDS
    if category_id not in NON_ADMITTED_PATH_CATEGORY_IDS
)
DIGEST_LABEL_REQUIRED_BY_CATEGORY: Mapping[str, tuple[str, ...]] = {
    "rag_pre_generation": (
        "input_digest",
        "prompt_digest",
        "context_item_digests",
        "input_sha",
        "prompt_sha",
        "context_item_shas",
    ),
    "rag_runtime_merged": (
        "input_digest",
        "prompt_digest",
        "context_item_digests",
        "answer_digest",
        "input_sha",
        "prompt_sha",
        "context_item_shas",
        "answer_sha",
    ),
    "direct_local_non_verification_first_answer": (
        "input_digest",
        "answer_digest",
        "input_sha",
        "answer_sha",
    ),
    "runtime_verification_disabled_passthrough": (
        "input_digest",
        "prompt_digest",
        "context_item_digests",
        "answer_digest",
        "input_sha",
        "prompt_sha",
        "context_item_shas",
        "answer_sha",
    ),
    "fail_closed_missing_bundle_with_provenance": (
        "input_digest",
        "answer_digest",
        "input_sha",
        "answer_sha",
    ),
}

PROVENANCE_FIELD_KINDS: Mapping[str, str] = {
    "input_digest": "redacted_digest_label",
    "prompt_digest": "redacted_digest_label",
    "context_item_digests": "redacted_digest_label_tuple",
    "answer_digest": "redacted_digest_label",
    "input_sha": "redacted_digest_label",
    "prompt_sha": "redacted_digest_label",
    "context_item_shas": "redacted_digest_label_tuple",
    "answer_sha": "redacted_digest_label",
    "prompt_char_count": "non_negative_count",
    "prompt_trimmed": "boolean_or_null",
    "prompt_original_char_count": "non_negative_count",
    "prompt_final_char_count": "non_negative_count",
    "prompt_trim_limit": "non_negative_count",
    "prompt_trimmed_char_count": "non_negative_count",
    "verification_hops": "non_negative_count",
    "verification_calls": "non_negative_count",
}

DIGEST_FIELDS = frozenset(
    {
        "input_digest",
        "prompt_digest",
        "context_item_digests",
        "answer_digest",
        "input_sha",
        "prompt_sha",
        "context_item_shas",
        "answer_sha",
    }
)
COUNT_FIELDS = frozenset(
    {
        "prompt_char_count",
        "prompt_original_char_count",
        "prompt_final_char_count",
        "prompt_trim_limit",
        "prompt_trimmed_char_count",
        "verification_hops",
        "verification_calls",
    }
)
COUNT_LABEL_KEYS: tuple[str, ...] = (
    "artifact_count",
    "reason_code_count",
    "context_item_digest_count",
    "prompt_char_count",
    "prompt_original_char_count",
    "prompt_final_char_count",
    "prompt_trim_limit",
    "prompt_trimmed_char_count",
    "verification_hops",
    "verification_calls",
)

TOP_LEVEL_KEYS: tuple[str, ...] = (
    "schema_version",
    "report_id",
    "report_version",
    "generated_at",
    "scope",
    "generation_mode",
    "source_ids",
    "authority_flags",
    "provenance_contract",
    "path_categories",
)
SOURCE_ID_KEYS: tuple[str, ...] = (
    "verification_contract",
    "verification_registry",
    "rag_orchestration",
    "philosophical_runtime",
    "application_service",
    "semantic_cache_gate",
)
AUTHORITY_FLAG_KEYS: tuple[str, ...] = (
    "public_api_changed",
    "openapi_changed",
    "db_persistence_changed",
    "provider_changed",
    "frontend_or_ios_changed",
    "runtime_authority_changed",
    "runtime_serving_behavior_changed",
    "admission_authority_changed",
    "semantic_cache_gate_status",
    "semantic_cache_allowed",
    "semantic_cache_runtime_allowed",
    "semantic_cache_implementation_allowed",
    "graphrag_allowed",
    "slack_or_operator_authority_allowed",
)
PROVENANCE_CONTRACT_KEYS: tuple[str, ...] = (
    "source_contract",
    "bundle_field",
    "metadata_scope",
    "redaction_source",
    "digest_label_format",
    "verification_status_values",
    "field_inventory",
    "raw_values_persisted",
    "public_response_surface",
)
FIELD_INVENTORY_KEYS: tuple[str, ...] = (
    "field",
    "kind",
    "safe_surface",
    "raw_value_allowed",
)
PATH_CATEGORY_KEYS: tuple[str, ...] = (
    "id",
    "bundle_present",
    "overall_status",
    "admission_allowed",
    "reason_labels",
    "expected_provenance_fields",
    "present_provenance_fields",
    "missing_required_provenance_fields",
    "redacted_digest_labels",
    "count_labels",
    "redaction_assertions",
    "authority",
    "source_refs",
)
SOURCE_REF_KEYS: tuple[str, ...] = ("path", "symbol")
REDACTION_ASSERTION_KEYS: tuple[str, ...] = (
    "raw_prompt_absent",
    "raw_context_absent",
    "raw_answer_absent",
    "raw_user_text_absent",
    "local_paths_absent",
    "secrets_absent",
    "slack_ids_absent",
    "workflow_logs_absent",
    "provider_logs_absent",
    "operator_artifacts_absent",
    "health_data_absent",
)
PATH_AUTHORITY_KEYS: tuple[str, ...] = (
    "public_api_changed",
    "runtime_authority_changed",
    "admission_authority_changed",
    "semantic_cache_gate_status",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)

FORBIDDEN_KEY_NAMES = frozenset(
    {
        "raw_prompt",
        "raw_input",
        "raw_context",
        "raw_answer",
        "input_text",
        "prompt_text",
        "context_text",
        "answer_text",
        "user_text",
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
        "provider_payload",
    }
)
FORBIDDEN_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "absolute local path",
        re.compile(
            r"(?<!\w)(?:file://)?/"
            r"(?:Users|private|var|tmp|Volumes|home|opt|etc|root|workspace|workspaces|"
            r"app|srv|mnt)"
            r"(?:/[^\s:;,'\")]+)+",
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
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    (
        "diagnostic log label",
        re.compile(r"(?i)\b(?:provider[_ -]?log|workflow[_ -]?log)\s*[:=]\s*[^\s,;]+"),
    ),
)
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


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
    except json.JSONDecodeError as exc:
        return None, [f"{invalid_prefix}: {exc}"]
    except ValueError as exc:
        return None, [str(exc)]


def _as_object(value: object, *, label: str) -> tuple[dict[str, object], list[str]]:
    if not isinstance(value, dict):
        return {}, [f"{label} must be an object"]
    return value, []


def _object_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _contract_tree() -> ast.Module:
    contract_path = REPO_ROOT / VERIFICATION_CONTRACT_PATH
    return ast.parse(
        contract_path.read_text(encoding="utf-8"),
        filename=str(contract_path),
    )


def _literal_string_values(node: ast.AST) -> tuple[str, ...]:
    if not isinstance(node, ast.Subscript):
        return ()
    if not isinstance(node.value, ast.Name) or node.value.id != "Literal":
        return ()
    literal_slice = node.slice
    if isinstance(literal_slice, ast.Tuple):
        candidates = literal_slice.elts
    else:
        candidates = [literal_slice]
    values: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, ast.Constant) or not isinstance(candidate.value, str):
            return ()
        values.append(candidate.value)
    return tuple(values)


def _load_verification_status_values() -> tuple[str, ...]:
    for node in _contract_tree().body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "VerificationStatus"
            for target in node.targets
        ):
            continue
        values = _literal_string_values(node.value)
        if values:
            return values
    raise RuntimeError("VerificationStatus must define at least one status")


def _load_verification_provenance_fields() -> tuple[str, ...]:
    for node in _contract_tree().body:
        if not isinstance(node, ast.ClassDef) or node.name != "VerificationProvenance":
            continue
        fields: list[str] = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append(item.target.id)
        if fields:
            return tuple(fields)
    raise RuntimeError("VerificationProvenance must define at least one field")


VERIFICATION_STATUS_VALUES = _load_verification_status_values()
VERIFICATION_PROVENANCE_FIELDS = _load_verification_provenance_fields()


def _source_ids() -> dict[str, str]:
    return {
        "verification_contract": VERIFICATION_CONTRACT_PATH,
        "verification_registry": VERIFICATION_REGISTRY_PATH,
        "rag_orchestration": RAG_ORCHESTRATION_PATH,
        "philosophical_runtime": PHILOSOPHICAL_RUNTIME_PATH,
        "application_service": APPLICATION_SERVICE_PATH,
        "semantic_cache_gate": SEMANTIC_CACHE_GATE_PATH,
    }


def _authority_flags() -> dict[str, object]:
    return {
        "public_api_changed": False,
        "openapi_changed": False,
        "db_persistence_changed": False,
        "provider_changed": False,
        "frontend_or_ios_changed": False,
        "runtime_authority_changed": False,
        "runtime_serving_behavior_changed": False,
        "admission_authority_changed": False,
        "semantic_cache_gate_status": SEMANTIC_CACHE_GATE_STATUS,
        "semantic_cache_allowed": False,
        "semantic_cache_runtime_allowed": False,
        "semantic_cache_implementation_allowed": False,
        "graphrag_allowed": False,
        "slack_or_operator_authority_allowed": False,
    }


def _path_authority() -> dict[str, object]:
    return {
        "public_api_changed": False,
        "runtime_authority_changed": False,
        "admission_authority_changed": False,
        "semantic_cache_gate_status": SEMANTIC_CACHE_GATE_STATUS,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
    }


def _redaction_assertions() -> dict[str, bool]:
    return {key: True for key in REDACTION_ASSERTION_KEYS}


def _field_inventory() -> list[dict[str, object]]:
    return [
        {
            "field": field,
            "kind": PROVENANCE_FIELD_KINDS.get(field, "unclassified"),
            "safe_surface": "internal_metadata_only",
            "raw_value_allowed": False,
        }
        for field in VERIFICATION_PROVENANCE_FIELDS
    ]


def _provenance_contract() -> dict[str, object]:
    return {
        "source_contract": VERIFICATION_CONTRACT_PATH,
        "bundle_field": "provenance",
        "metadata_scope": "internal_only",
        "redaction_source": "core.verification.registry.redacted_sha256_label",
        "digest_label_format": "sha256:<64 lowercase hex>",
        "verification_status_values": list(VERIFICATION_STATUS_VALUES),
        "field_inventory": _field_inventory(),
        "raw_values_persisted": False,
        "public_response_surface": False,
    }


def _digest_label(category_id: str, field: str, index: int = 0) -> str:
    payload = "|".join((REPORT_ID, REPORT_VERSION, category_id, field, str(index)))
    return f"sha256:{sha256(payload.encode('utf-8')).hexdigest()}"


def _digest_labels_for(
    *,
    category_id: str,
    present_fields: Sequence[str],
    context_count: int,
) -> dict[str, object]:
    labels: dict[str, object] = {}
    for field in present_fields:
        if field == "context_item_digests":
            labels[field] = [
                _digest_label(category_id, field, index=index) for index in range(context_count)
            ]
        elif field in DIGEST_FIELDS:
            labels[field] = _digest_label(category_id, field)
    for digest_field, alias_field in (
        ("input_digest", "input_sha"),
        ("prompt_digest", "prompt_sha"),
        ("context_item_digests", "context_item_shas"),
        ("answer_digest", "answer_sha"),
    ):
        if alias_field in present_fields and digest_field in labels:
            labels[alias_field] = labels[digest_field]
    return labels


def _count_labels_for(
    *,
    present_fields: Sequence[str],
    context_count: int,
    prompt_char_count: int | None,
    prompt_original_char_count: int | None,
    prompt_final_char_count: int | None,
    prompt_trim_limit: int | None,
    prompt_trimmed_char_count: int | None,
    verification_hops: int,
    verification_calls: int,
    artifact_count: int,
    reason_code_count: int,
) -> dict[str, int]:
    labels = {
        "artifact_count": artifact_count,
        "reason_code_count": reason_code_count,
    }
    if "context_item_digests" in present_fields:
        labels["context_item_digest_count"] = context_count
    if "prompt_char_count" in present_fields and prompt_char_count is not None:
        labels["prompt_char_count"] = prompt_char_count
    if "prompt_original_char_count" in present_fields and prompt_original_char_count is not None:
        labels["prompt_original_char_count"] = prompt_original_char_count
    if "prompt_final_char_count" in present_fields and prompt_final_char_count is not None:
        labels["prompt_final_char_count"] = prompt_final_char_count
    if "prompt_trim_limit" in present_fields and prompt_trim_limit is not None:
        labels["prompt_trim_limit"] = prompt_trim_limit
    if "prompt_trimmed_char_count" in present_fields and prompt_trimmed_char_count is not None:
        labels["prompt_trimmed_char_count"] = prompt_trimmed_char_count
    if "verification_hops" in present_fields:
        labels["verification_hops"] = verification_hops
    if "verification_calls" in present_fields:
        labels["verification_calls"] = verification_calls
    return labels


def _source_ref(path: str, symbol: str) -> dict[str, str]:
    return {"path": path, "symbol": symbol}


def _path_category_admission_schema_constraints() -> list[dict[str, object]]:
    constraints: list[dict[str, object]] = []
    for category_id in PATH_CATEGORY_IDS:
        constraints.append(
            {
                "if": {
                    "properties": {
                        "id": {
                            "const": category_id,
                        },
                    },
                    "required": [
                        "id",
                    ],
                },
                "then": {
                    "properties": {
                        "admission_allowed": {
                            "const": category_id in ADMITTED_PATH_CATEGORY_IDS,
                        },
                        "redacted_digest_labels": {
                            "required": list(DIGEST_LABEL_REQUIRED_BY_CATEGORY[category_id]),
                        },
                    },
                },
            }
        )
    return constraints


def _path_category_exact_once_schema_constraints() -> list[dict[str, object]]:
    return [
        {
            "contains": {
                "properties": {
                    "id": {
                        "const": category_id,
                    },
                },
                "required": [
                    "id",
                ],
            },
            "minContains": 1,
            "maxContains": 1,
        }
        for category_id in PATH_CATEGORY_IDS
    ]


def _path_category(
    *,
    category_id: str,
    bundle_present: bool,
    overall_status: str,
    admission_allowed: bool,
    reason_labels: Sequence[str],
    present_fields: Sequence[str],
    context_count: int,
    prompt_char_count: int | None,
    prompt_original_char_count: int | None,
    prompt_final_char_count: int | None,
    prompt_trim_limit: int | None,
    prompt_trimmed_char_count: int | None,
    verification_hops: int,
    verification_calls: int,
    artifact_count: int,
    source_refs: Sequence[Mapping[str, str]],
) -> dict[str, object]:
    return {
        "id": category_id,
        "bundle_present": bundle_present,
        "overall_status": overall_status,
        "admission_allowed": admission_allowed,
        "reason_labels": list(reason_labels),
        "expected_provenance_fields": list(present_fields),
        "present_provenance_fields": list(present_fields),
        "missing_required_provenance_fields": [],
        "redacted_digest_labels": _digest_labels_for(
            category_id=category_id,
            present_fields=present_fields,
            context_count=context_count,
        ),
        "count_labels": _count_labels_for(
            present_fields=present_fields,
            context_count=context_count,
            prompt_char_count=prompt_char_count,
            prompt_original_char_count=prompt_original_char_count,
            prompt_final_char_count=prompt_final_char_count,
            prompt_trim_limit=prompt_trim_limit,
            prompt_trimmed_char_count=prompt_trimmed_char_count,
            verification_hops=verification_hops,
            verification_calls=verification_calls,
            artifact_count=artifact_count,
            reason_code_count=len(reason_labels),
        ),
        "redaction_assertions": _redaction_assertions(),
        "authority": _path_authority(),
        "source_refs": [dict(item) for item in source_refs],
    }


def _path_categories() -> list[dict[str, object]]:
    rag_fields = (
        "input_digest",
        "prompt_digest",
        "context_item_digests",
        "input_sha",
        "prompt_sha",
        "context_item_shas",
        "prompt_char_count",
        "prompt_trimmed",
        "prompt_original_char_count",
        "prompt_final_char_count",
        "prompt_trimmed_char_count",
        "verification_hops",
        "verification_calls",
    )
    disabled_runtime_fields = (
        "input_digest",
        "prompt_digest",
        "context_item_digests",
        "answer_digest",
        "input_sha",
        "prompt_sha",
        "context_item_shas",
        "answer_sha",
        "prompt_char_count",
        "prompt_trimmed",
        "prompt_original_char_count",
        "prompt_final_char_count",
        "prompt_trim_limit",
        "prompt_trimmed_char_count",
        "verification_hops",
        "verification_calls",
    )
    runtime_fields = tuple(VERIFICATION_PROVENANCE_FIELDS)
    direct_fields = (
        "input_digest",
        "answer_digest",
        "input_sha",
        "answer_sha",
        "verification_hops",
        "verification_calls",
    )
    return [
        _path_category(
            category_id="rag_pre_generation",
            bundle_present=True,
            overall_status="pass",
            admission_allowed=True,
            reason_labels=(
                "policy_checks_pass",
                "freshness_checks_pass",
                "validated_evidence_pass",
            ),
            present_fields=rag_fields,
            context_count=2,
            prompt_char_count=184,
            prompt_original_char_count=184,
            prompt_final_char_count=184,
            prompt_trim_limit=None,
            prompt_trimmed_char_count=0,
            verification_hops=1,
            verification_calls=0,
            artifact_count=3,
            source_refs=(
                _source_ref(RAG_ORCHESTRATION_PATH, "_build_orchestration_verification_bundle"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_rag_verification_bundle"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_verification_provenance"),
            ),
        ),
        _path_category(
            category_id="rag_runtime_merged",
            bundle_present=True,
            overall_status="pass",
            admission_allowed=True,
            reason_labels=(
                "policy_checks_pass",
                "freshness_checks_pass",
                "validated_evidence_pass",
                "verification_checks_pass",
                "falsification_checks_pass",
            ),
            present_fields=runtime_fields,
            context_count=2,
            prompt_char_count=4000,
            prompt_original_char_count=5200,
            prompt_final_char_count=4000,
            prompt_trim_limit=4000,
            prompt_trimmed_char_count=1200,
            verification_hops=1,
            verification_calls=0,
            artifact_count=5,
            source_refs=(
                _source_ref(PHILOSOPHICAL_RUNTIME_PATH, "generate_insight"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "_merge_provenance"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_runtime_verification_bundle"),
            ),
        ),
        _path_category(
            category_id="direct_local_non_verification_first_answer",
            bundle_present=True,
            overall_status="fail",
            admission_allowed=False,
            reason_labels=("rag_bundle_missing",),
            present_fields=direct_fields,
            context_count=0,
            prompt_char_count=None,
            prompt_original_char_count=None,
            prompt_final_char_count=None,
            prompt_trim_limit=None,
            prompt_trimmed_char_count=None,
            verification_hops=0,
            verification_calls=0,
            artifact_count=1,
            source_refs=(
                _source_ref(PHILOSOPHICAL_RUNTIME_PATH, "_build_direct_result"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_runtime_verification_bundle"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_verification_provenance"),
            ),
        ),
        _path_category(
            category_id="runtime_verification_disabled_passthrough",
            bundle_present=True,
            overall_status="fail",
            admission_allowed=False,
            reason_labels=(
                "runtime_verification_disabled_inherits_existing_bundle",
                "knowledge_policy_missing",
                "freshness_checks_pass",
                "validated_evidence_pass",
            ),
            present_fields=disabled_runtime_fields,
            context_count=2,
            prompt_char_count=4000,
            prompt_original_char_count=5200,
            prompt_final_char_count=4000,
            prompt_trim_limit=4000,
            prompt_trimmed_char_count=1200,
            verification_hops=2,
            verification_calls=2,
            artifact_count=4,
            source_refs=(
                _source_ref(PHILOSOPHICAL_RUNTIME_PATH, "generate_insight"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_runtime_verification_bundle"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_rag_verification_bundle"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_verification_provenance"),
            ),
        ),
        _path_category(
            category_id="fail_closed_missing_bundle_with_provenance",
            bundle_present=True,
            overall_status="fail",
            admission_allowed=False,
            reason_labels=("rag_bundle_missing",),
            present_fields=direct_fields,
            context_count=0,
            prompt_char_count=None,
            prompt_original_char_count=None,
            prompt_final_char_count=None,
            prompt_trim_limit=None,
            prompt_trimmed_char_count=None,
            verification_hops=0,
            verification_calls=0,
            artifact_count=1,
            source_refs=(
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_runtime_verification_bundle"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_bundle"),
                _source_ref(VERIFICATION_REGISTRY_PATH, "build_verification_provenance"),
            ),
        ),
    ]


def generate_verification_provenance_admission_report() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "generated_at": GENERATED_AT,
        "scope": SCOPE,
        "generation_mode": GENERATION_MODE,
        "source_ids": _source_ids(),
        "authority_flags": _authority_flags(),
        "provenance_contract": _provenance_contract(),
        "path_categories": _path_categories(),
    }


def render_verification_provenance_admission_report() -> tuple[str, list[str]]:
    errors = _source_contract_errors()
    if errors:
        return "", errors
    report = generate_verification_provenance_admission_report()
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n", []


def _source_contract_errors() -> list[str]:
    errors: list[str] = []
    source_fields = set(VERIFICATION_PROVENANCE_FIELDS)
    mapped_fields = set(PROVENANCE_FIELD_KINDS)
    for field in sorted(source_fields - mapped_fields):
        errors.append(f"VerificationProvenance field lacks report classification: {field}")
    for field in sorted(mapped_fields - source_fields):
        errors.append(f"report field missing from VerificationProvenance contract: {field}")
    if "pass" not in VERIFICATION_STATUS_VALUES or "fail" not in VERIFICATION_STATUS_VALUES:
        errors.append("VerificationStatus must include pass and fail")
    return errors


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


def _validate_object_schema(
    *,
    schema: Mapping[str, object],
    report: Mapping[str, object],
) -> list[str]:
    errors: list[str] = []
    if schema.get("type") != "object":
        errors.append("verification provenance admission schema root type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append("verification provenance admission schema additionalProperties must be false")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("verification provenance admission schema required must be a string list")
        required = []
    if not isinstance(properties, dict):
        errors.append("verification provenance admission schema properties must be an object")
        properties = {}
    report_keys = set(report)
    required_keys = set(required)
    property_keys = set(properties)
    for key in sorted(report_keys - required_keys):
        errors.append(f"verification provenance admission key missing from schema required: {key}")
    for key in sorted(required_keys - report_keys):
        errors.append(f"verification provenance admission schema required key missing: {key}")
    for key in sorted(report_keys - property_keys):
        errors.append(
            f"verification provenance admission key missing from schema properties: {key}"
        )
    for key in sorted(property_keys - report_keys):
        errors.append(
            f"verification provenance admission schema property missing from report: {key}"
        )
    for key in (
        "schema_version",
        "report_id",
        "report_version",
        "generated_at",
        "scope",
        "generation_mode",
    ):
        spec = properties.get(key)
        if not isinstance(spec, dict) or spec.get("const") != report.get(key):
            errors.append(f"verification provenance admission schema const mismatch for {key}")
    errors.extend(_validate_required_schema_consts(schema))
    errors.extend(_validate_required_schema_shapes(schema))
    errors.extend(
        _validate_schema_matches_report(
            schema_node=schema,
            report_node=report,
            path="report",
        )
    )
    errors.extend(_validate_nested_object_schema_flags(schema=schema, label="schema"))
    return errors


def _validate_schema_matches_report(
    *,
    schema_node: object,
    report_node: object,
    path: str,
) -> list[str]:
    errors: list[str] = []
    if isinstance(schema_node, dict) and "$ref" in schema_node:
        return errors
    if isinstance(report_node, dict):
        if not isinstance(schema_node, dict):
            return [f"verification provenance admission schema {path} must describe an object"]
        if schema_node.get("type") != "object":
            errors.append(f"verification provenance admission schema {path}.type must be object")
        if schema_node.get("additionalProperties") is not False:
            errors.append(f"verification provenance admission schema {path} object must be closed")
        required = schema_node.get("required")
        properties = schema_node.get("properties")
        has_required = "required" in schema_node
        required_items: list[str] = []
        if (
            has_required
            and isinstance(required, list)
            and all(isinstance(item, str) for item in required)
        ):
            required_items = required
        elif has_required:
            errors.append(
                f"verification provenance admission schema {path}.required must be a string list"
            )
        if not isinstance(properties, dict):
            errors.append(
                f"verification provenance admission schema {path}.properties must be an object"
            )
            properties = {}
        report_keys = set(report_node)
        required_keys = set(required_items)
        property_keys = set(properties)
        if has_required and _schema_path_requires_all_report_keys(path):
            for key in sorted(report_keys - required_keys):
                errors.append(
                    "verification provenance admission key missing from schema required: "
                    f"{path}.{key}"
                )
        for key in sorted(required_keys - report_keys):
            errors.append(
                "verification provenance admission schema required key missing: " f"{path}.{key}"
            )
        for key in sorted(report_keys - property_keys):
            errors.append(
                "verification provenance admission key missing from schema properties: "
                f"{path}.{key}"
            )
        for key in sorted(report_keys & property_keys):
            errors.extend(
                _validate_schema_matches_report(
                    schema_node=properties[key],
                    report_node=report_node[key],
                    path=f"{path}.{key}",
                )
            )
    elif isinstance(report_node, list):
        if not isinstance(schema_node, dict):
            return [f"verification provenance admission schema {path} must describe an array"]
        if "$ref" in schema_node:
            return errors
        if schema_node.get("type") != "array":
            errors.append(f"verification provenance admission schema {path}.type must be array")
        if path == "report.provenance_contract.field_inventory":
            min_items = schema_node.get("minItems")
            max_items = schema_node.get("maxItems")
            if isinstance(min_items, int) and min_items != len(report_node):
                errors.append(
                    "verification provenance admission schema "
                    f"{path}.minItems must match report length: "
                    f"expected {len(report_node)}, got {min_items}"
                )
            if isinstance(max_items, int) and max_items != len(report_node):
                errors.append(
                    "verification provenance admission schema "
                    f"{path}.maxItems must match report length: "
                    f"expected {len(report_node)}, got {max_items}"
                )
        items_schema = schema_node.get("items")
        if report_node and not isinstance(items_schema, dict):
            errors.append(
                f"verification provenance admission schema {path}.items must be an object"
            )
            return errors
        if isinstance(items_schema, dict):
            for index, item in enumerate(report_node):
                errors.extend(
                    _validate_schema_matches_report(
                        schema_node=items_schema,
                        report_node=item,
                        path=f"{path}[{index}]",
                    )
                )
    elif isinstance(schema_node, dict) and "const" in schema_node:
        if schema_node.get("const") != report_node:
            errors.append(f"verification provenance admission schema const mismatch for {path}")
    return errors


def _schema_path_requires_all_report_keys(path: str) -> bool:
    if path in {
        "report",
        "report.source_ids",
        "report.authority_flags",
        "report.provenance_contract",
    }:
        return True
    return (
        path.endswith(".authority")
        or path.endswith(".redaction_assertions")
        or ".source_refs[" in path
        or ".field_inventory[" in path
    )


def _schema_const_requirements() -> tuple[tuple[tuple[str, ...], object], ...]:
    requirements: list[tuple[tuple[str, ...], object]] = []
    for key in AUTHORITY_FLAG_KEYS:
        expected: object = (
            SEMANTIC_CACHE_GATE_STATUS if key == "semantic_cache_gate_status" else False
        )
        requirements.append((("properties", "authority_flags", "properties", key), expected))
    for key in PATH_AUTHORITY_KEYS:
        expected = SEMANTIC_CACHE_GATE_STATUS if key == "semantic_cache_gate_status" else False
        requirements.append(
            (
                (
                    "properties",
                    "path_categories",
                    "items",
                    "properties",
                    "authority",
                    "properties",
                    key,
                ),
                expected,
            )
        )
    for key in REDACTION_ASSERTION_KEYS:
        requirements.append(
            (
                (
                    "properties",
                    "path_categories",
                    "items",
                    "properties",
                    "redaction_assertions",
                    "properties",
                    key,
                ),
                True,
            )
        )
    for key in ("raw_values_persisted", "public_response_surface"):
        requirements.append((("properties", "provenance_contract", "properties", key), False))
    requirements.append(
        (
            (
                "properties",
                "provenance_contract",
                "properties",
                "field_inventory",
                "items",
                "properties",
                "raw_value_allowed",
            ),
            False,
        )
    )
    return tuple(requirements)


def _schema_node_at(schema: Mapping[str, object], path: tuple[str, ...]) -> object:
    current: object = schema
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _validate_required_schema_consts(schema: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    for path, expected in _schema_const_requirements():
        node = _schema_node_at(schema, path)
        if not isinstance(node, dict) or node.get("const") != expected:
            errors.append(
                "verification provenance admission schema const mismatch for " + ".".join(path)
            )
    return errors


def _validate_required_schema_shapes(schema: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    digest_label = _schema_node_at(schema, ("$defs", "digestLabel"))
    if (
        not isinstance(digest_label, dict)
        or digest_label.get("type") != "string"
        or digest_label.get("pattern") != r"^sha256:[0-9a-f]{64}$"
    ):
        errors.append("verification provenance admission schema digestLabel definition drift")

    provenance_fields_items = _schema_node_at(schema, ("$defs", "provenanceFields", "items"))
    if not isinstance(provenance_fields_items, dict) or provenance_fields_items.get("enum") != list(
        VERIFICATION_PROVENANCE_FIELDS
    ):
        errors.append("verification provenance admission schema provenanceFields enum drift")

    for key in ("expected_provenance_fields", "present_provenance_fields"):
        node = _schema_node_at(
            schema,
            ("properties", "path_categories", "items", "properties", key),
        )
        if not isinstance(node, dict) or node.get("$ref") != "#/$defs/provenanceFields":
            errors.append(f"verification provenance admission schema {key} ref drift")

    missing_fields = _schema_node_at(
        schema,
        (
            "properties",
            "path_categories",
            "items",
            "properties",
            "missing_required_provenance_fields",
        ),
    )
    if (
        not isinstance(missing_fields, dict)
        or missing_fields.get("type") != "array"
        or missing_fields.get("items") is not False
        or missing_fields.get("maxItems") != 0
    ):
        errors.append(
            "verification provenance admission schema missing_required_provenance_fields "
            "must remain an empty array"
        )

    field_inventory = _schema_node_at(
        schema,
        (
            "properties",
            "provenance_contract",
            "properties",
            "field_inventory",
            "items",
            "properties",
        ),
    )
    if not isinstance(field_inventory, dict):
        errors.append("verification provenance admission schema field_inventory shape drift")
    else:
        field_spec = field_inventory.get("field")
        if not isinstance(field_spec, dict) or field_spec.get("enum") != list(
            VERIFICATION_PROVENANCE_FIELDS
        ):
            errors.append("verification provenance admission schema field_inventory.field drift")
        kind_spec = field_inventory.get("kind")
        expected_kinds = list(dict.fromkeys(PROVENANCE_FIELD_KINDS.values()))
        if not isinstance(kind_spec, dict) or kind_spec.get("enum") != expected_kinds:
            errors.append("verification provenance admission schema field_inventory.kind drift")

    digest_props = _schema_node_at(
        schema,
        (
            "properties",
            "path_categories",
            "items",
            "properties",
            "redacted_digest_labels",
            "properties",
        ),
    )
    if not isinstance(digest_props, dict) or set(digest_props) != set(DIGEST_FIELDS):
        errors.append("verification provenance admission schema redacted_digest_labels keys drift")
    else:
        for key in (
            "input_digest",
            "prompt_digest",
            "answer_digest",
            "input_sha",
            "prompt_sha",
            "answer_sha",
        ):
            if (
                not isinstance(digest_props.get(key), dict)
                or digest_props[key].get("$ref") != "#/$defs/digestLabel"
            ):
                errors.append(
                    "verification provenance admission schema digest label ref drift: " f"{key}"
                )
                break
        for key in ("context_item_digests", "context_item_shas"):
            context_digest = digest_props.get(key)
            if (
                not isinstance(context_digest, dict)
                or context_digest.get("type") != "array"
                or not isinstance(context_digest.get("items"), dict)
                or context_digest["items"].get("$ref") != "#/$defs/digestLabel"
                or context_digest.get("minItems") != 1
            ):
                errors.append("verification provenance admission schema context digest ref drift")
                break

    count_props = _schema_node_at(
        schema,
        (
            "properties",
            "path_categories",
            "items",
            "properties",
            "count_labels",
            "properties",
        ),
    )
    if not isinstance(count_props, dict) or set(count_props) != set(COUNT_LABEL_KEYS):
        errors.append("verification provenance admission schema count_labels keys drift")
    elif any(
        not isinstance(count_props.get(key), dict)
        or count_props[key].get("type") != "integer"
        or count_props[key].get("minimum") != 0
        for key in COUNT_LABEL_KEYS
    ):
        errors.append("verification provenance admission schema count_labels integer drift")

    path_category_items = _schema_node_at(
        schema,
        ("properties", "path_categories", "items"),
    )
    if (
        not isinstance(path_category_items, dict)
        or path_category_items.get("allOf") != _path_category_admission_schema_constraints()
    ):
        errors.append(
            "verification provenance admission schema path category admission constraints drift"
        )

    path_categories = _schema_node_at(schema, ("properties", "path_categories"))
    if (
        not isinstance(path_categories, dict)
        or path_categories.get("allOf") != _path_category_exact_once_schema_constraints()
    ):
        errors.append(
            "verification provenance admission schema path category exact-once constraints drift"
        )

    return errors


def _validate_nested_object_schema_flags(
    *,
    schema: object,
    label: str,
) -> list[str]:
    errors: list[str] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object" and schema.get("additionalProperties") is not False:
            errors.append(f"verification provenance admission {label} object must be closed")
        for key, value in schema.items():
            errors.extend(
                _validate_nested_object_schema_flags(
                    schema=value,
                    label=f"{label}.{key}",
                )
            )
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            errors.extend(
                _validate_nested_object_schema_flags(
                    schema=item,
                    label=f"{label}[{index}]",
                )
            )
    return errors


def _validate_report_shape(report: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_keys(report, TOP_LEVEL_KEYS, label="report"))
    expected_scalars: Mapping[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "generated_at": GENERATED_AT,
        "scope": SCOPE,
        "generation_mode": GENERATION_MODE,
    }
    for key, expected in expected_scalars.items():
        if report.get(key) != expected:
            errors.append(f"verification provenance admission {key}: expected {expected!r}")

    source_ids = report.get("source_ids")
    if not isinstance(source_ids, dict):
        errors.append("verification provenance admission source_ids must be an object")
    else:
        errors.extend(_validate_keys(source_ids, SOURCE_ID_KEYS, label="source_ids"))
        for key, expected in _source_ids().items():
            if source_ids.get(key) != expected:
                errors.append(f"verification provenance admission source_ids.{key} mismatch")

    authority = report.get("authority_flags")
    if not isinstance(authority, dict):
        errors.append("verification provenance admission authority_flags must be an object")
    else:
        errors.extend(_validate_authority(authority, label="authority_flags"))

    contract = report.get("provenance_contract")
    if not isinstance(contract, dict):
        errors.append("verification provenance admission provenance_contract must be an object")
    else:
        errors.extend(_validate_provenance_contract(contract))

    path_categories = _object_items(report.get("path_categories"))
    if len(path_categories) != len(PATH_CATEGORY_IDS):
        errors.append(
            "verification provenance admission path category count: "
            f"expected {len(PATH_CATEGORY_IDS)}, got {len(path_categories)}"
        )
    observed_ids = [str(item.get("id", "")) for item in path_categories]
    if observed_ids != list(PATH_CATEGORY_IDS):
        errors.append(
            "verification provenance admission path category order mismatch: "
            f"expected {list(PATH_CATEGORY_IDS)!r}, got {observed_ids!r}"
        )
    for category in path_categories:
        errors.extend(_validate_path_category(category))
    return errors


def _validate_authority(authority: Mapping[str, object], *, label: str) -> list[str]:
    errors = _validate_keys(authority, AUTHORITY_FLAG_KEYS, label=label)
    for key in AUTHORITY_FLAG_KEYS:
        value = authority.get(key)
        if key == "semantic_cache_gate_status":
            if value != SEMANTIC_CACHE_GATE_STATUS:
                errors.append(f"{label}.{key} must remain closed")
        elif value is not False:
            errors.append(f"{label}.{key} must remain false")
    return errors


def _validate_path_authority(authority: Mapping[str, object], *, category_id: str) -> list[str]:
    errors = _validate_keys(authority, PATH_AUTHORITY_KEYS, label=f"{category_id}.authority")
    for key in PATH_AUTHORITY_KEYS:
        value = authority.get(key)
        if key == "semantic_cache_gate_status":
            if value != SEMANTIC_CACHE_GATE_STATUS:
                errors.append(f"{category_id}.authority.{key} must remain closed")
        elif value is not False:
            errors.append(f"{category_id}.authority.{key} must remain false")
    return errors


def _validate_provenance_contract(contract: Mapping[str, object]) -> list[str]:
    errors = _validate_keys(contract, PROVENANCE_CONTRACT_KEYS, label="provenance_contract")
    expected_scalars: Mapping[str, object] = {
        "source_contract": VERIFICATION_CONTRACT_PATH,
        "bundle_field": "provenance",
        "metadata_scope": "internal_only",
        "redaction_source": "core.verification.registry.redacted_sha256_label",
        "digest_label_format": "sha256:<64 lowercase hex>",
        "raw_values_persisted": False,
        "public_response_surface": False,
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            errors.append(f"provenance_contract.{key}: expected {expected!r}")
    redaction_source = contract.get("redaction_source")
    if isinstance(redaction_source, str):
        errors.extend(_validate_redaction_source(redaction_source))
    if contract.get("verification_status_values") != list(VERIFICATION_STATUS_VALUES):
        errors.append("provenance_contract.verification_status_values drift")
    inventory = _object_items(contract.get("field_inventory"))
    observed_fields = [str(item.get("field", "")) for item in inventory]
    if observed_fields != list(VERIFICATION_PROVENANCE_FIELDS):
        errors.append(
            "provenance_contract field_inventory mismatch: "
            f"expected {list(VERIFICATION_PROVENANCE_FIELDS)!r}, got {observed_fields!r}"
        )
    for item in inventory:
        errors.extend(_validate_keys(item, FIELD_INVENTORY_KEYS, label="field_inventory"))
        field = item.get("field")
        if isinstance(field, str) and item.get("kind") != PROVENANCE_FIELD_KINDS.get(field):
            errors.append(f"field_inventory.{field}.kind mismatch")
        if item.get("safe_surface") != "internal_metadata_only":
            errors.append(f"field_inventory.{field}.safe_surface must be internal_metadata_only")
        if item.get("raw_value_allowed") is not False:
            errors.append(f"field_inventory.{field}.raw_value_allowed must be false")
    return errors


def _validate_path_category(category: Mapping[str, object]) -> list[str]:
    errors = _validate_keys(category, PATH_CATEGORY_KEYS, label="path_category")
    category_id = str(category.get("id", ""))
    if category_id not in PATH_CATEGORY_IDS:
        errors.append(f"verification provenance admission unexpected path category: {category_id}")
    overall_status = category.get("overall_status")
    if overall_status not in VERIFICATION_STATUS_VALUES:
        errors.append(f"{category_id}.overall_status is not a VerificationStatus")
    if category.get("bundle_present") is not True:
        errors.append(f"{category_id}.bundle_present must be true")
    if category_id in NON_ADMITTED_PATH_CATEGORY_IDS:
        if category.get("admission_allowed") is not False:
            errors.append(f"{category_id}.admission_allowed must be false")
    elif category.get("admission_allowed") is not True:
        errors.append(f"{category_id}.admission_allowed must be true")

    reason_labels = _string_items(category.get("reason_labels"))
    if not reason_labels:
        errors.append(f"{category_id}.reason_labels must not be empty")

    expected_fields = _string_items(category.get("expected_provenance_fields"))
    present_fields = _string_items(category.get("present_provenance_fields"))
    missing_fields = category.get("missing_required_provenance_fields")
    if expected_fields != present_fields:
        errors.append(f"{category_id}.present_provenance_fields must match expected")
    if missing_fields != []:
        errors.append(f"{category_id}.missing_required_provenance_fields must be empty")
    for field in expected_fields:
        if field not in VERIFICATION_PROVENANCE_FIELDS:
            errors.append(f"{category_id} unknown provenance field: {field}")

    digest_labels = category.get("redacted_digest_labels")
    if not isinstance(digest_labels, dict):
        errors.append(f"{category_id}.redacted_digest_labels must be an object")
    else:
        errors.extend(_validate_digest_labels(digest_labels, category_id=category_id))

    count_labels = category.get("count_labels")
    if not isinstance(count_labels, dict):
        errors.append(f"{category_id}.count_labels must be an object")
    else:
        for key, value in count_labels.items():
            if key not in COUNT_LABEL_KEYS:
                errors.append(f"{category_id}.count_labels unknown key: {key}")
            if type(value) is not int or value < 0:
                errors.append(f"{category_id}.count_labels.{key} must be a non-negative integer")
        if count_labels.get("reason_code_count") != len(reason_labels):
            errors.append(f"{category_id}.count_labels.reason_code_count must match reason_labels")
        if count_labels.get("artifact_count") != len(reason_labels):
            errors.append(f"{category_id}.count_labels.artifact_count must match reason_labels")

    redaction_assertions = category.get("redaction_assertions")
    if not isinstance(redaction_assertions, dict):
        errors.append(f"{category_id}.redaction_assertions must be an object")
    else:
        errors.extend(
            _validate_keys(
                redaction_assertions,
                REDACTION_ASSERTION_KEYS,
                label=f"{category_id}.redaction_assertions",
            )
        )
        for key in REDACTION_ASSERTION_KEYS:
            if redaction_assertions.get(key) is not True:
                errors.append(f"{category_id}.redaction_assertions.{key} must be true")

    authority = category.get("authority")
    if not isinstance(authority, dict):
        errors.append(f"{category_id}.authority must be an object")
    else:
        errors.extend(_validate_path_authority(authority, category_id=category_id))

    refs = _object_items(category.get("source_refs"))
    if not refs:
        errors.append(f"{category_id}.source_refs must not be empty")
    for ref in refs:
        errors.extend(_validate_keys(ref, SOURCE_REF_KEYS, label=f"{category_id}.source_ref"))
        path = ref.get("path")
        symbol = ref.get("symbol")
        if isinstance(path, str) and isinstance(symbol, str):
            errors.extend(
                _validate_source_symbol(path=path, symbol=symbol, category_id=category_id)
            )
    return errors


def _validate_digest_labels(
    digest_labels: Mapping[str, object],
    *,
    category_id: str,
) -> list[str]:
    errors: list[str] = []
    for key in DIGEST_LABEL_REQUIRED_BY_CATEGORY.get(category_id, ()):
        if key not in digest_labels:
            errors.append(f"{category_id}.redacted_digest_labels missing required key: {key}")
    for key, value in digest_labels.items():
        if key not in DIGEST_FIELDS:
            errors.append(f"{category_id}.redacted_digest_labels unknown key: {key}")
            continue
        if key in {"context_item_digests", "context_item_shas"}:
            if not isinstance(value, list):
                errors.append(f"{category_id}.{key} must be a string list")
                continue
            if not value:
                errors.append(f"{category_id}.{key} must not be empty")
            for index, label in enumerate(value):
                if not isinstance(label, str):
                    errors.append(f"{category_id}.{key}[{index}] must be a string")
                    continue
                if not DIGEST_RE.match(label):
                    errors.append(f"{category_id}.{key}[{index}] invalid digest label")
        elif not isinstance(value, str) or not DIGEST_RE.match(value):
            errors.append(f"{category_id}.{key} invalid digest label")
    return errors


def _validate_source_symbol(*, path: str, symbol: str, category_id: str) -> list[str]:
    source_path, path_error = _resolve_source_ref_path(path=path, category_id=category_id)
    if path_error is not None:
        return [path_error]
    if not source_path.exists():
        return [f"{category_id}.source_ref missing file: {path}"]
    text = source_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text, filename=str(source_path))
    defined_symbols = _defined_source_symbols(tree)
    if symbol not in defined_symbols:
        return [f"{category_id}.source_ref symbol missing: {path}:{symbol}"]
    return []


def _resolve_source_ref_path(*, path: str, category_id: str) -> tuple[Path, str | None]:
    ref_path = Path(path)
    if ref_path.is_absolute() or ".." in ref_path.parts or path.startswith(("~", "\\")):
        return (
            REPO_ROOT,
            f"{category_id}.source_ref path must stay under repository: {path}",
        )
    source_path = (REPO_ROOT / ref_path).resolve()
    repo_root = REPO_ROOT.resolve()
    if not source_path.is_relative_to(repo_root):
        return (
            REPO_ROOT,
            f"{category_id}.source_ref path must stay under repository: {path}",
        )
    return source_path, None


def _defined_source_symbols(tree: ast.AST) -> set[str]:
    symbols: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            symbols.add(node.target.id)
    return symbols


def _validate_redaction_source(redaction_source: str) -> list[str]:
    module, _, symbol = redaction_source.rpartition(".")
    expected_module = VERIFICATION_REGISTRY_PATH.removesuffix(".py").replace("/", ".")
    if module != expected_module or symbol != "redacted_sha256_label":
        return ["provenance_contract.redaction_source drift"]
    return _validate_source_symbol(
        path=VERIFICATION_REGISTRY_PATH,
        symbol=symbol,
        category_id="provenance_contract.redaction_source",
    )


def _walk_json(value: object, *, path: str = "$") -> Iterable[tuple[str, object]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield f"{path}.{key}", key
            yield from _walk_json(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_json(item, path=f"{path}[{index}]")


def _validate_no_raw_leaks(value: object, *, label: str) -> list[str]:
    errors: list[str] = []
    for path, item in _walk_json(value):
        if isinstance(item, str):
            if item in FORBIDDEN_KEY_NAMES:
                errors.append(f"{label} contains forbidden key/name at {path}: {item}")
            for name, pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(item):
                    errors.append(f"{label} contains forbidden {name} at {path}")
        elif isinstance(item, dict):
            for key in item:
                if key in FORBIDDEN_KEY_NAMES:
                    errors.append(f"{label} contains forbidden key at {path}: {key}")
    return errors


def validate_verification_provenance_admission_report(
    *,
    report_text: str,
    schema_text: str,
) -> list[str]:
    errors: list[str] = []
    expected_text, render_errors = render_verification_provenance_admission_report()
    errors.extend(render_errors)

    report_obj, report_parse_errors = _load_json_no_duplicate_keys(
        report_text,
        invalid_prefix="verification provenance admission report invalid JSON",
        duplicate_prefix="verification provenance admission report duplicate key",
    )
    errors.extend(report_parse_errors)
    schema_obj, schema_parse_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="verification provenance admission schema invalid JSON",
        duplicate_prefix="verification provenance admission schema duplicate key",
    )
    errors.extend(schema_parse_errors)
    if errors:
        return errors

    report, report_type_errors = _as_object(
        report_obj,
        label="verification provenance admission report",
    )
    errors.extend(report_type_errors)
    schema, schema_type_errors = _as_object(
        schema_obj,
        label="verification provenance admission schema",
    )
    errors.extend(schema_type_errors)
    if errors:
        return errors

    if expected_text and report_text != expected_text:
        errors.append(
            "verification provenance admission report drift: regenerate from current contracts"
        )
    errors.extend(_validate_object_schema(schema=schema, report=report))
    errors.extend(_validate_report_shape(report))
    errors.extend(_validate_no_raw_leaks(report, label="verification provenance admission report"))
    errors.extend(_validate_no_raw_leaks(schema, label="verification provenance admission schema"))
    return errors


def _write_report(*, path: Path, text: str) -> list[str]:
    report_path = path.resolve()
    allowed_root = (REPO_ROOT / "docs" / "orchestration" / "contracts").resolve()
    if not report_path.is_relative_to(allowed_root):
        return [
            "verification provenance admission report write path must stay under "
            "docs/orchestration/contracts"
        ]
    path.write_text(text, encoding="utf-8")
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check VerificationBundle provenance admission report determinism."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--report-schema", type=Path, default=DEFAULT_REPORT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    if not args.report_schema.exists():
        errors.append(
            "verification provenance admission schema missing: "
            f"{_display_path(args.report_schema)}"
        )
    if not args.write_report and not args.report.exists():
        errors.append(
            "verification provenance admission report missing: " f"{_display_path(args.report)}"
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    schema_text = args.report_schema.read_text(encoding="utf-8")
    rendered, render_errors = render_verification_provenance_admission_report()
    errors.extend(render_errors)

    if args.write_report and not errors:
        errors.extend(
            validate_verification_provenance_admission_report(
                report_text=rendered,
                schema_text=schema_text,
            )
        )
        if not errors:
            errors.extend(_write_report(path=args.report, text=rendered))

    if args.check or not args.write_report:
        if args.report.exists():
            errors.extend(
                validate_verification_provenance_admission_report(
                    report_text=args.report.read_text(encoding="utf-8"),
                    schema_text=schema_text,
                )
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("verification provenance admission report current: " f"{_display_path(args.report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic guard for Philosophy semantic-cache gate-open preconditions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from pathlib import PurePosixPath
import posixpath
import re
import sys

try:
    from scripts.ci.check_philosophy_admission_dry_run import (
        validate_philosophy_admission_dry_run_report,
    )
    from scripts.ci.check_semantic_cache_gate import (
        validate_philosophy_admission_oracle_fixture,
        validate_philosophy_semantic_cache_admission_policy,
    )
except ModuleNotFoundError:  # pragma: no cover - file-mode CLI fallback
    from check_philosophy_admission_dry_run import (
        validate_philosophy_admission_dry_run_report,
    )
    from check_semantic_cache_gate import (
        validate_philosophy_admission_oracle_fixture,
        validate_philosophy_semantic_cache_admission_policy,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_POLICY = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json"
)
DEFAULT_POLICY_SCHEMA = DEFAULT_POLICY.with_suffix(".schema.json")
DEFAULT_ORACLE = (
    REPO_ROOT / "tests" / "fixtures" / "orchestration" / "philosophy_admission_claim_oracle.json"
)
DEFAULT_DRY_RUN_REPORT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json"
)
DEFAULT_DRY_RUN_SCHEMA = DEFAULT_DRY_RUN_REPORT.with_suffix(".schema.json")
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ALIGNMENT_RULE_SCHEMA = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_ALIGNMENT_RULE.schema.json"
)
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
)
DEFAULT_REPORT_SCHEMA = DEFAULT_REPORT.with_suffix(".schema.json")

REPORT_ID = "philosophy_gate_open_preconditions_report"
REPORT_VERSION = "2026-05-25"
ROLLOUT_PHASE = "PHILOSOPHY-PR4-SC0-RECONCILED"
GENERATED_AT = "static-2026-05-25"
ALIGNMENT_RULE_SCHEMA_ID = "https://pulseplate.app/schemas/philosophy-alignment-rule.v1.json"
ALIGNMENT_RULE_SCHEMA_TITLE = "PhilosophyAlignmentRule"

ROADMAP_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

PREREQUISITE_IDS = (
    "pr2_policy_oracle_current",
    "pr3_dry_run_current",
    "pr1789_alignment_rule_schema_landed",
    "pr_a1b_reconciled",
    "pr_a2_rag_hardening_closed",
    "pr_a3_bounded_context_packet_closed",
    "pr_a4_bounded_context_extraction_closed",
    "pr_a5_llm_reliability_security_closed",
    "dedicated_gate_open_pr_changes_markers",
)

PREREQUISITE_STATUSES = (
    "source_current",
    "source_present_not_merge_verified",
    "merge_verified_closed",
    "pending_external_predecessor",
    "not_verified_by_pr4",
    "absent",
)

BLOCKING_STATUSES = {
    "source_present_not_merge_verified",
    "pending_external_predecessor",
    "not_verified_by_pr4",
    "absent",
}

RUNTIME_PREREQUISITES: tuple[tuple[str, str, str], ...] = (
    (
        "pr_a1b_reconciled",
        "PR-A1b PRO quota reconciliation",
        (
            "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pro-monthly-quota-ledger-reconciliation; "
            "PR #1461 merged 2026-04-19T11:34:45Z with merge commit "
            "cd01d9c6db89813202f85b8b9f4c8378e72380ea from branch "
            "codex/wave6-a1b-pro-quota-reconciliation; PR #1466 merged "
            "2026-04-19T11:34:46Z with merge commit "
            "fa0979e734b88575e01e3eca9ddd4d57ade86c05 from branch "
            "codex/pr1461-mapping-fix; runtime truth remains PR #1379"
        ),
    ),
    (
        "pr_a2_rag_hardening_closed",
        "PR-A2 RAG hardening follow-through",
        (
            "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough; "
            "PR #1415 merged 2026-04-14T20:59:47Z with merge commit "
            "146da0e0d269acea5ba946d239997705ebaf62c3 from branch "
            "feat/rag-hardening-followthrough"
        ),
    ),
    (
        "pr_a3_bounded_context_packet_closed",
        "PR-A3 AI bounded-context packet",
        (
            "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-packet; "
            "PR #1469 merged 2026-04-19T11:35:29Z with merge commit "
            "f8454715f88e44657cfad1c4675f93ea669dc490 from branch "
            "codex/ai-bounded-context-packet"
        ),
    ),
    (
        "pr_a4_bounded_context_extraction_closed",
        "PR-A4 bounded-context extraction",
        (
            "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction; "
            "PR #1203 `feat(ai): extract bounded AI runtime ownership into canonical "
            "core/ai seam` merged 2026-03-21T06:01:31Z with merge commit "
            "831d62d8be0da7307e5a0f2673d8c33dbf53ca49 from branch "
            "feat/ai-bounded-context-extraction"
        ),
    ),
    (
        "pr_a5_llm_reliability_security_closed",
        "PR-A5 LLM reliability/security gates",
        (
            "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-llm-reliability-security-gates; "
            "PR #1395 `feat(ai): add PR-A5 runtime gates` merged "
            "2026-04-12T11:45:35Z with merge commit "
            "2f8a9af461cec483aa81a774cce7496c6bf65a8a from branch "
            "feat/pr-a5-runtime-gates"
        ),
    ),
)
RUNTIME_PREREQUISITE_ANCHORS = tuple(
    evidence.split(";", 1)[0] for _id, _label, evidence in RUNTIME_PREREQUISITES
)
REQUIRED_REASON_CODES = (
    "semantic_cache_gate_closed",
    "dedicated_gate_open_pr_absent",
    "alignment_rule_schema_predecessor_pending",
)
EXPECTED_STATUS_BY_ID = {
    "pr2_policy_oracle_current": "source_current",
    "pr3_dry_run_current": "source_current",
    "pr_a1b_reconciled": "merge_verified_closed",
    "pr_a2_rag_hardening_closed": "merge_verified_closed",
    "pr_a3_bounded_context_packet_closed": "merge_verified_closed",
    "pr_a4_bounded_context_extraction_closed": "merge_verified_closed",
    "pr_a5_llm_reliability_security_closed": "merge_verified_closed",
    "dedicated_gate_open_pr_changes_markers": "absent",
}

FORBIDDEN_RUNTIME_PATHS = (
    "app/**",
    "core/ai/**",
    "core/insight/**",
    "core/knowledge/**",
    "core/rag/**",
    "core/verification/**",
    "core/evidence/**",
    "legacy_app.py",
    "mcp_pulseplate_server.py",
    "providers/**",
    "frontend/**",
    "ios/**",
    "alembic/**",
    "openapi/**",
)

ALIGNMENT_SCHEMA_CONSTRAINT_KEYS = (
    "$ref",
    "allOf",
    "anyOf",
    "const",
    "enum",
    "format",
    "items",
    "maximum",
    "minimum",
    "oneOf",
    "pattern",
    "properties",
    "type",
)


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


def _matches_forbidden_runtime_path(path: str) -> str | None:
    for pattern in FORBIDDEN_RUNTIME_PATHS:
        if pattern.endswith("/**"):
            prefix = pattern.removesuffix("**")
            if path.startswith(prefix):
                return pattern
        elif path == pattern:
            return pattern
    return None


def _normalize_touched_path(raw_path: str) -> tuple[str | None, str | None]:
    path = raw_path.strip().replace("\\", "/")
    if not path:
        return None, "empty changed path is not allowed"
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            repo_relative = candidate.resolve(strict=False).relative_to(
                REPO_ROOT.resolve(strict=False)
            )
        except ValueError:
            return None, f"changed path is outside repo: {raw_path}"
        path = repo_relative.as_posix()

    normalized = PurePosixPath(posixpath.normpath(path))
    normalized_path = normalized.as_posix()
    if normalized_path == ".":
        return None, f"changed path does not identify a file: {raw_path}"
    if normalized_path.startswith("../") or normalized_path == "..":
        return None, f"changed path escapes repo root: {raw_path}"
    return normalized_path, None


def _roadmap_markers(roadmap_text: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    for match in re.finditer(r"<!--\s*([A-Z0-9_]+):\s*([^>]+?)\s*-->", roadmap_text):
        markers[match.group(1)] = match.group(2).strip()
    return markers


def _closed_marker_bools(markers: dict[str, str]) -> dict[str, bool]:
    return {
        "gate_status_closed": markers.get("SEMANTIC_CACHE_GATE_STATUS") == "closed",
        "runtime_allowed_false": markers.get("SEMANTIC_CACHE_ALLOWED_RUNTIME") == "false",
        "implementation_allowed_false": markers.get("SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED")
        == "false",
        "dedicated_gate_required": markers.get("SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE") == "true",
    }


def _source_dry_run_summary(dry_run: dict[str, object]) -> dict[str, object]:
    summary = dry_run.get("summary")
    decision_count = summary.get("dry_run_decision_count") if isinstance(summary, dict) else None
    all_cache_permissions_false = (
        summary.get("all_cache_permissions_false") if isinstance(summary, dict) else None
    )
    decisions = _object_items(dry_run.get("dry_run_decisions"))
    all_decision_cache_permissions_false = bool(decisions) and all(
        decision.get("cache_read_allowed") is False
        and decision.get("cache_write_allowed") is False
        and decision.get("serving_allowed") is False
        for decision in decisions
    )
    return {
        "report_id": dry_run.get("report_id"),
        "report_version": dry_run.get("report_version"),
        "rollout_phase": dry_run.get("rollout_phase"),
        "gate_status": dry_run.get("gate_status"),
        "runtime_allowed": dry_run.get("runtime_allowed"),
        "implementation_allowed": dry_run.get("implementation_allowed"),
        "dry_run_decision_count": decision_count,
        "all_cache_permissions_false": all_cache_permissions_false,
        "all_decision_cache_permissions_false": all_decision_cache_permissions_false,
    }


def _alignment_schema_errors(alignment_rule_schema: Path) -> list[str]:
    schema_obj, parse_errors = _load_json_no_duplicate_keys(
        alignment_rule_schema.read_text(encoding="utf-8"),
        invalid_prefix="alignment rule schema invalid JSON",
        duplicate_prefix="alignment rule schema duplicate key",
    )
    if parse_errors:
        return parse_errors
    schema, type_errors = _as_object(schema_obj, label="alignment rule schema")
    if type_errors:
        return type_errors
    errors: list[str] = []
    if schema.get("$id") != ALIGNMENT_RULE_SCHEMA_ID:
        errors.append("alignment rule schema $id mismatch")
    if schema.get("title") != ALIGNMENT_RULE_SCHEMA_TITLE:
        errors.append("alignment rule schema title mismatch")
    if schema.get("type") != "object":
        errors.append("alignment rule schema root type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append("alignment rule schema must set additionalProperties false")
    required = schema.get("required")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("alignment rule schema required must be a string list")
        required = []
    required_keys = {
        "rule_id",
        "provenance",
        "assertion_hints",
        "schema_version",
        "schema_hash",
    }
    for key in sorted(required_keys - set(required)):
        errors.append(f"alignment rule schema required key missing: {key}")
    properties, property_errors = _as_object(
        schema.get("properties"),
        label="alignment rule schema properties",
    )
    errors.extend(property_errors)
    if not property_errors:
        for key in sorted(required_keys - set(properties)):
            errors.append(f"alignment rule schema property missing: {key}")
        for key in sorted(required_keys & set(properties)):
            property_schema = properties.get(key)
            if not isinstance(property_schema, dict):
                errors.append(f"alignment rule schema property {key} must be an object")
                continue
            if not property_schema:
                errors.append(f"alignment rule schema property {key} must not be empty")
                continue
            if not any(
                schema_key in property_schema for schema_key in ALIGNMENT_SCHEMA_CONSTRAINT_KEYS
            ):
                errors.append(
                    f"alignment rule schema property {key} must declare a schema constraint"
                )
    return errors


def validate_touched_paths(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for raw_path in paths:
        path, normalize_error = _normalize_touched_path(raw_path)
        if normalize_error:
            errors.append(
                f"philosophy gate-open preconditions invalid changed path: {normalize_error}"
            )
            continue
        if path is None:
            continue
        matched = _matches_forbidden_runtime_path(path)
        if matched:
            errors.append(
                f"philosophy gate-open preconditions forbids runtime path {raw_path} "
                f"(normalized {path}, matches {matched})"
            )
    return errors


def _alignment_rule_precondition(alignment_rule_schema: Path) -> dict[str, object]:
    if alignment_rule_schema.exists():
        alignment_errors = _alignment_schema_errors(alignment_rule_schema)
        if not alignment_errors:
            return {
                "id": "pr1789_alignment_rule_schema_landed",
                "label": "PR #1789 alignment-rule trust schema is present on this base",
                "status": "source_present_not_merge_verified",
                "required_for_gate_open": True,
                "blocks_gate_open": True,
                "evidence": (
                    "docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json; "
                    "schema shape validated, but merge/current-head proof is still required"
                ),
            }
        return {
            "id": "pr1789_alignment_rule_schema_landed",
            "label": "PR #1789 alignment-rule trust schema is present on this base",
            "status": "pending_external_predecessor",
            "required_for_gate_open": True,
            "blocks_gate_open": True,
            "evidence": "alignment rule schema present but invalid: " + "; ".join(alignment_errors),
        }
    return {
        "id": "pr1789_alignment_rule_schema_landed",
        "label": "PR #1789 alignment-rule trust schema is present on this base",
        "status": "pending_external_predecessor",
        "required_for_gate_open": True,
        "blocks_gate_open": True,
        "evidence": "PR #1789 / codex/philosophy-alignment-rule-trust-schema is external to this PR-4 branch",
    }


def _expected_alignment_rule_status(alignment_rule_schema: Path) -> str:
    if not alignment_rule_schema.exists():
        return "pending_external_predecessor"
    if _alignment_schema_errors(alignment_rule_schema):
        return "pending_external_predecessor"
    return "source_present_not_merge_verified"


def _expected_preconditions(alignment_rule_schema: Path) -> list[dict[str, object]]:
    preconditions: list[dict[str, object]] = [
        {
            "id": "pr2_policy_oracle_current",
            "label": "PR-2 policy oracle validates and remains gate-closed",
            "status": "source_current",
            "required_for_gate_open": True,
            "blocks_gate_open": False,
            "evidence": "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json",
        },
        {
            "id": "pr3_dry_run_current",
            "label": "PR-3 dry-run adapter validates and keeps cache permissions false",
            "status": "source_current",
            "required_for_gate_open": True,
            "blocks_gate_open": False,
            "evidence": "docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json",
        },
        _alignment_rule_precondition(alignment_rule_schema),
    ]
    for precondition_id, label, evidence in RUNTIME_PREREQUISITES:
        preconditions.append(
            {
                "id": precondition_id,
                "label": label,
                "status": "merge_verified_closed",
                "required_for_gate_open": True,
                "blocks_gate_open": False,
                "evidence": evidence,
            }
        )
    preconditions.append(
        {
            "id": "dedicated_gate_open_pr_changes_markers",
            "label": "A later reviewed gate-open PR changes machine-checkable markers",
            "status": "absent",
            "required_for_gate_open": True,
            "blocks_gate_open": True,
            "evidence": "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        }
    )
    return preconditions


def generate_philosophy_gate_open_preconditions_report(
    *,
    policy: dict[str, object],
    dry_run: dict[str, object],
    roadmap_text: str,
    ledger_text: str,
    alignment_rule_schema: Path,
) -> dict[str, object]:
    markers = _roadmap_markers(roadmap_text)
    marker_bools = _closed_marker_bools(markers)
    preconditions = _expected_preconditions(alignment_rule_schema)
    blocking = [item for item in preconditions if item.get("status") in BLOCKING_STATUSES]
    ledger_anchor_present = {
        evidence.split(";", 1)[0]: evidence.split(";", 1)[0] in ledger_text
        for _precondition_id, _label, evidence in RUNTIME_PREREQUISITES
    }
    reason_codes = ["semantic_cache_gate_closed", "dedicated_gate_open_pr_absent"]
    if any(
        str(item.get("id", "")).startswith("pr_a") and item.get("status") in BLOCKING_STATUSES
        for item in blocking
    ):
        reason_codes.append("runtime_prerequisites_not_verified")
    if any(item["id"] == "pr1789_alignment_rule_schema_landed" for item in blocking):
        reason_codes.append("alignment_rule_schema_predecessor_pending")
    return {
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "generated_at": GENERATED_AT,
        "rollout_phase": ROLLOUT_PHASE,
        "gate_status": markers.get("SEMANTIC_CACHE_GATE_STATUS"),
        "runtime_allowed": markers.get("SEMANTIC_CACHE_ALLOWED_RUNTIME") == "true",
        "implementation_allowed": markers.get("SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED") == "true",
        "requires_dedicated_gate": markers.get("SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE") == "true",
        "gate_open_allowed": False,
        "runtime_handoff_allowed": False,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
        "source_policy": {
            "policy_id": policy.get("policy_id"),
            "policy_version": policy.get("policy_version"),
            "rollout_phase": policy.get("rollout_phase"),
            "gate_status": policy.get("gate_status"),
            "runtime_allowed": policy.get("runtime_allowed"),
            "implementation_allowed": policy.get("implementation_allowed"),
        },
        "source_dry_run": _source_dry_run_summary(dry_run),
        "semantic_cache_markers": marker_bools,
        "ledger_anchor_present": ledger_anchor_present,
        "ledger_anchor_presence_does_not_verify_closure": True,
        "preconditions": preconditions,
        "handoff_decision": {
            "decision": "gate_open_blocked_preconditions_incomplete",
            "reason_codes": reason_codes,
            "blocking_precondition_count": len(blocking),
            "runtime_handoff_allowed": False,
            "cache_read_allowed": False,
            "cache_write_allowed": False,
            "serving_allowed": False,
        },
        "research_basis": [
            "W3C PROV-DM: preserve explicit source lineage for policy, dry-run, and roadmap evidence.",
            "OPA decision logs: derive handoff decisions from structured policy inputs.",
            "NIST AI 600-1: keep red-team findings as governance evidence, not runtime authority.",
            "Metamorphic testing: pair current governance sources with blocking runtime preconditions.",
        ],
        "out_of_scope_paths": list(FORBIDDEN_RUNTIME_PATHS),
    }


def render_philosophy_gate_open_preconditions_report(
    *,
    policy_text: str,
    dry_run_text: str,
    roadmap_text: str,
    ledger_text: str,
    alignment_rule_schema: Path = DEFAULT_ALIGNMENT_RULE_SCHEMA,
) -> tuple[str, list[str]]:
    policy_obj, policy_errors = _load_json_no_duplicate_keys(
        policy_text,
        invalid_prefix="philosophy admission policy invalid JSON",
        duplicate_prefix="philosophy admission policy duplicate key",
    )
    if policy_errors:
        return "", policy_errors
    dry_run_obj, dry_run_errors = _load_json_no_duplicate_keys(
        dry_run_text,
        invalid_prefix="philosophy admission dry-run report invalid JSON",
        duplicate_prefix="philosophy admission dry-run report duplicate key",
    )
    if dry_run_errors:
        return "", dry_run_errors
    policy, policy_type_errors = _as_object(policy_obj, label="philosophy admission policy")
    if policy_type_errors:
        return "", policy_type_errors
    dry_run, dry_run_type_errors = _as_object(
        dry_run_obj,
        label="philosophy admission dry-run report",
    )
    if dry_run_type_errors:
        return "", dry_run_type_errors
    report = generate_philosophy_gate_open_preconditions_report(
        policy=policy,
        dry_run=dry_run,
        roadmap_text=roadmap_text,
        ledger_text=ledger_text,
        alignment_rule_schema=alignment_rule_schema,
    )
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n", []


def _validate_report_schema(*, schema: object, report: dict[str, object]) -> list[str]:
    if not isinstance(schema, dict):
        return ["philosophy gate-open preconditions schema must be an object"]
    errors: list[str] = []
    if schema.get("type") != "object":
        errors.append("philosophy gate-open preconditions schema root type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append(
            "philosophy gate-open preconditions schema must set additionalProperties false"
        )
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("philosophy gate-open preconditions schema required must be a string list")
        required = []
    if not isinstance(properties, dict):
        errors.append("philosophy gate-open preconditions schema properties must be an object")
        properties = {}
    report_keys = set(report)
    required_keys = set(required)
    property_keys = set(properties)
    for key in sorted(report_keys - required_keys):
        errors.append(f"philosophy gate-open preconditions key missing from schema required: {key}")
    for key in sorted(required_keys - report_keys):
        errors.append(
            f"philosophy gate-open preconditions schema required key missing from report: {key}"
        )
    for key in sorted(report_keys - property_keys):
        errors.append(
            f"philosophy gate-open preconditions key missing from schema properties: {key}"
        )
    for key in sorted(property_keys - report_keys):
        errors.append(
            f"philosophy gate-open preconditions schema property missing from report: {key}"
        )

    for key in (
        "report_id",
        "report_version",
        "generated_at",
        "rollout_phase",
        "gate_status",
        "runtime_allowed",
        "implementation_allowed",
        "requires_dedicated_gate",
        "gate_open_allowed",
        "runtime_handoff_allowed",
        "cache_read_allowed",
        "cache_write_allowed",
        "serving_allowed",
        "ledger_anchor_presence_does_not_verify_closure",
    ):
        spec = properties.get(key)
        if not isinstance(spec, dict) or "const" not in spec:
            errors.append(f"philosophy gate-open preconditions schema const missing for {key}")
            continue
        if spec["const"] != report.get(key):
            errors.append(
                f"philosophy gate-open preconditions schema const mismatch for {key}: "
                f"expected {spec['const']!r}, got {report.get(key)!r}"
            )
    preconditions_spec = properties.get("preconditions")
    precondition_items = (
        preconditions_spec.get("items") if isinstance(preconditions_spec, dict) else None
    )
    precondition_properties = (
        precondition_items.get("properties") if isinstance(precondition_items, dict) else None
    )
    if not isinstance(precondition_properties, dict):
        errors.append("philosophy gate-open preconditions schema missing precondition properties")
    else:
        status = precondition_properties.get("status")
        if not isinstance(status, dict) or status.get("enum") != list(PREREQUISITE_STATUSES):
            errors.append("philosophy gate-open preconditions schema status enum mismatch")
        required_for_gate_open = precondition_properties.get("required_for_gate_open")
        if (
            not isinstance(required_for_gate_open, dict)
            or required_for_gate_open.get("const") is not True
        ):
            errors.append(
                "philosophy gate-open preconditions schema const missing for "
                "preconditions.required_for_gate_open"
            )
    if not isinstance(preconditions_spec, dict):
        errors.append("philosophy gate-open preconditions schema missing preconditions spec")
    else:
        if preconditions_spec.get("minItems") != len(PREREQUISITE_IDS):
            errors.append("philosophy gate-open preconditions schema minItems mismatch")
        if preconditions_spec.get("maxItems") != len(PREREQUISITE_IDS):
            errors.append("philosophy gate-open preconditions schema maxItems mismatch")
        prefix_items = preconditions_spec.get("prefixItems")
        if not isinstance(prefix_items, list) or len(prefix_items) != len(PREREQUISITE_IDS):
            errors.append("philosophy gate-open preconditions schema prefixItems id count mismatch")
        else:
            for expected_id, prefix_spec in zip(PREREQUISITE_IDS, prefix_items, strict=True):
                if not isinstance(prefix_spec, dict):
                    errors.append(
                        "philosophy gate-open preconditions schema prefixItems entry "
                        f"missing for {expected_id}"
                    )
                    continue
                prefix_properties = prefix_spec.get("properties")
                if not isinstance(prefix_properties, dict):
                    errors.append(
                        "philosophy gate-open preconditions schema prefixItems properties "
                        f"missing for {expected_id}"
                    )
                    continue
                id_spec = prefix_properties.get("id")
                if not isinstance(id_spec, dict) or id_spec.get("const") != expected_id:
                    errors.append(
                        "philosophy gate-open preconditions schema prefixItems id const "
                        f"missing for {expected_id}"
                    )

    ledger_anchor_spec = properties.get("ledger_anchor_present")
    if not isinstance(ledger_anchor_spec, dict):
        errors.append("philosophy gate-open preconditions schema missing ledger anchor spec")
    else:
        if ledger_anchor_spec.get("additionalProperties") is not False:
            errors.append(
                "philosophy gate-open preconditions schema ledger anchors must reject extras"
            )
        ledger_required = ledger_anchor_spec.get("required")
        if not isinstance(ledger_required, list) or set(ledger_required) != set(
            RUNTIME_PREREQUISITE_ANCHORS
        ):
            errors.append("philosophy gate-open preconditions schema ledger required mismatch")
        ledger_properties = ledger_anchor_spec.get("properties")
        if not isinstance(ledger_properties, dict) or set(ledger_properties) != set(
            RUNTIME_PREREQUISITE_ANCHORS
        ):
            errors.append("philosophy gate-open preconditions schema ledger properties mismatch")
        elif not all(
            isinstance(ledger_properties.get(anchor), dict)
            and ledger_properties[anchor].get("const") is True
            for anchor in RUNTIME_PREREQUISITE_ANCHORS
        ):
            errors.append("philosophy gate-open preconditions schema ledger const mismatch")
    decision = properties.get("handoff_decision")
    decision_properties = decision.get("properties") if isinstance(decision, dict) else None
    if not isinstance(decision_properties, dict):
        errors.append(
            "philosophy gate-open preconditions schema missing handoff decision properties"
        )
    else:
        for key in (
            "runtime_handoff_allowed",
            "cache_read_allowed",
            "cache_write_allowed",
            "serving_allowed",
        ):
            spec = decision_properties.get(key)
            if not isinstance(spec, dict) or spec.get("const") is not False:
                errors.append(
                    "philosophy gate-open preconditions schema const missing for "
                    f"handoff_decision.{key}"
                )
        reason_codes = decision_properties.get("reason_codes")
        if not isinstance(reason_codes, dict):
            errors.append("philosophy gate-open preconditions schema missing reason_codes spec")
        else:
            if reason_codes.get("minItems") != len(REQUIRED_REASON_CODES):
                errors.append(
                    "philosophy gate-open preconditions schema reason code minItems mismatch"
                )
            if reason_codes.get("uniqueItems") is not True:
                errors.append(
                    "philosophy gate-open preconditions schema reason codes must be unique"
                )
            reason_all_of = reason_codes.get("allOf")
            observed_required_codes: set[str] = set()
            if isinstance(reason_all_of, list):
                for entry in reason_all_of:
                    if not isinstance(entry, dict):
                        continue
                    contains = entry.get("contains")
                    if not isinstance(contains, dict):
                        continue
                    code = contains.get("const")
                    if isinstance(code, str):
                        observed_required_codes.add(code)
            if observed_required_codes != set(REQUIRED_REASON_CODES):
                errors.append(
                    "philosophy gate-open preconditions schema reason code coverage mismatch"
                )
    return errors


def validate_philosophy_gate_open_preconditions_report(
    *,
    report_text: str,
    schema_text: str,
    policy_text: str,
    policy_schema_text: str,
    oracle_text: str,
    dry_run_text: str,
    dry_run_schema_text: str,
    roadmap_text: str,
    ledger_text: str,
    alignment_rule_schema: Path = DEFAULT_ALIGNMENT_RULE_SCHEMA,
) -> list[str]:
    """Validate the canonical PR-4 precondition report and its upstream inputs."""
    errors: list[str] = []
    errors.extend(
        validate_philosophy_semantic_cache_admission_policy(
            policy_text=policy_text,
            schema_text=policy_schema_text,
        )
    )
    errors.extend(
        validate_philosophy_admission_oracle_fixture(
            policy_text=policy_text,
            fixture_text=oracle_text,
        )
    )
    errors.extend(
        validate_philosophy_admission_dry_run_report(
            report_text=dry_run_text,
            schema_text=dry_run_schema_text,
            policy_text=policy_text,
            policy_schema_text=policy_schema_text,
            oracle_text=oracle_text,
        )
    )
    expected_text, render_errors = render_philosophy_gate_open_preconditions_report(
        policy_text=policy_text,
        dry_run_text=dry_run_text,
        roadmap_text=roadmap_text,
        ledger_text=ledger_text,
        alignment_rule_schema=alignment_rule_schema,
    )
    errors.extend(render_errors)

    report_obj, report_parse_errors = _load_json_no_duplicate_keys(
        report_text,
        invalid_prefix="philosophy gate-open preconditions report invalid JSON",
        duplicate_prefix="philosophy gate-open preconditions report duplicate key",
    )
    errors.extend(report_parse_errors)
    schema_obj, schema_parse_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="philosophy gate-open preconditions schema invalid JSON",
        duplicate_prefix="philosophy gate-open preconditions schema duplicate key",
    )
    errors.extend(schema_parse_errors)
    if errors:
        return errors
    report, report_type_errors = _as_object(
        report_obj,
        label="philosophy gate-open preconditions report",
    )
    errors.extend(report_type_errors)
    if errors:
        return errors

    if expected_text and report_text != expected_text:
        errors.append(
            "philosophy gate-open preconditions report drift: regenerate from current inputs"
        )
    errors.extend(_validate_report_schema(schema=schema_obj, report=report))

    marker_values = _roadmap_markers(roadmap_text)
    for key, expected_marker_value in ROADMAP_MARKERS.items():
        observed = marker_values.get(key)
        if observed != expected_marker_value:
            errors.append(
                f"philosophy gate-open preconditions marker {key}: "
                f"expected {expected_marker_value!r}, got {observed!r}"
            )

    expected_scalars: dict[str, object] = {
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "generated_at": GENERATED_AT,
        "rollout_phase": ROLLOUT_PHASE,
        "gate_status": "closed",
        "runtime_allowed": False,
        "implementation_allowed": False,
        "requires_dedicated_gate": True,
        "gate_open_allowed": False,
        "runtime_handoff_allowed": False,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
        "ledger_anchor_presence_does_not_verify_closure": True,
    }
    for key, expected_scalar_value in expected_scalars.items():
        if report.get(key) != expected_scalar_value:
            errors.append(
                f"philosophy gate-open preconditions {key}: "
                f"expected {expected_scalar_value!r}, got {report.get(key)!r}"
            )

    dry_run_obj, _dry_run_errors = _load_json_no_duplicate_keys(
        dry_run_text,
        invalid_prefix="philosophy admission dry-run report invalid JSON",
        duplicate_prefix="philosophy admission dry-run report duplicate key",
    )
    dry_run = dry_run_obj if isinstance(dry_run_obj, dict) else {}
    source_dry_run = report.get("source_dry_run")
    if not isinstance(source_dry_run, dict):
        errors.append("philosophy gate-open preconditions source_dry_run must be an object")
    else:
        for key, expected_dry_run_value in _source_dry_run_summary(dry_run).items():
            if source_dry_run.get(key) != expected_dry_run_value:
                errors.append(
                    f"philosophy gate-open preconditions source_dry_run mismatch for {key}"
                )

    semantic_cache_markers = report.get("semantic_cache_markers")
    expected_marker_bools = _closed_marker_bools(marker_values)
    if not isinstance(semantic_cache_markers, dict):
        errors.append("philosophy gate-open preconditions semantic_cache_markers must be an object")
    else:
        for key, expected_marker_bool in expected_marker_bools.items():
            if semantic_cache_markers.get(key) != expected_marker_bool:
                errors.append(
                    f"philosophy gate-open preconditions marker bool {key}: "
                    f"expected {expected_marker_bool!r}, got {semantic_cache_markers.get(key)!r}"
                )

    preconditions = _object_items(report.get("preconditions"))
    observed_ids = [str(item.get("id", "")) for item in preconditions]
    if observed_ids != list(PREREQUISITE_IDS):
        errors.append("philosophy gate-open preconditions id order mismatch")
    for item in preconditions:
        precondition_id = str(item.get("id", ""))
        status = item.get("status")
        expected_status = EXPECTED_STATUS_BY_ID.get(precondition_id)
        if expected_status is None and precondition_id == "pr1789_alignment_rule_schema_landed":
            expected_status = _expected_alignment_rule_status(alignment_rule_schema)
        if expected_status is not None and status != expected_status:
            errors.append(
                f"philosophy gate-open preconditions {precondition_id} status: "
                f"expected {expected_status!r}, got {status!r}"
            )
        if status not in PREREQUISITE_STATUSES:
            errors.append(
                f"philosophy gate-open preconditions {precondition_id} invalid status: "
                f"{status!r}"
            )
        if item.get("required_for_gate_open") is not True:
            errors.append(f"philosophy gate-open preconditions {precondition_id} must be required")
        expected_blocks = status in BLOCKING_STATUSES
        if item.get("blocks_gate_open") is not expected_blocks:
            errors.append(
                f"philosophy gate-open preconditions {precondition_id} blocks_gate_open: "
                f"expected {expected_blocks!r}, got {item.get('blocks_gate_open')!r}"
            )
    if not any(item.get("status") in BLOCKING_STATUSES for item in preconditions):
        errors.append("philosophy gate-open preconditions must retain at least one blocker")

    ledger_anchor_present = report.get("ledger_anchor_present")
    expected_anchors = [
        evidence.split(";", 1)[0] for _precondition_id, _label, evidence in RUNTIME_PREREQUISITES
    ]
    if not isinstance(ledger_anchor_present, dict):
        errors.append("philosophy gate-open preconditions ledger_anchor_present must be an object")
    else:
        observed_anchor_keys = set(ledger_anchor_present)
        if observed_anchor_keys != set(expected_anchors):
            errors.append("philosophy gate-open preconditions ledger anchor key set mismatch")
        for anchor in expected_anchors:
            observed = ledger_anchor_present.get(anchor)
            if observed is not True:
                errors.append(f"philosophy gate-open preconditions missing ledger anchor: {anchor}")

    decision = report.get("handoff_decision")
    if not isinstance(decision, dict):
        errors.append("philosophy gate-open preconditions handoff_decision must be an object")
    else:
        if decision.get("decision") != "gate_open_blocked_preconditions_incomplete":
            errors.append("philosophy gate-open preconditions decision must remain blocked")
        for flag in (
            "runtime_handoff_allowed",
            "cache_read_allowed",
            "cache_write_allowed",
            "serving_allowed",
        ):
            if decision.get(flag) is not False:
                errors.append(
                    "philosophy gate-open preconditions handoff decision must keep " f"{flag}=false"
                )
        blocking_count = sum(1 for item in preconditions if item.get("status") in BLOCKING_STATUSES)
        if decision.get("blocking_precondition_count") != blocking_count:
            errors.append("philosophy gate-open preconditions blocking_precondition_count mismatch")

    out_of_scope_paths = set(_string_items(report.get("out_of_scope_paths")))
    for path in sorted(set(FORBIDDEN_RUNTIME_PATHS) - out_of_scope_paths):
        errors.append(f"philosophy gate-open preconditions missing out-of-scope path: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Philosophy gate-open precondition report determinism."
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--policy-schema", type=Path, default=DEFAULT_POLICY_SCHEMA)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--dry-run-report", type=Path, default=DEFAULT_DRY_RUN_REPORT)
    parser.add_argument("--dry-run-schema", type=Path, default=DEFAULT_DRY_RUN_SCHEMA)
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--alignment-rule-schema", type=Path, default=DEFAULT_ALIGNMENT_RULE_SCHEMA)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--report-schema", type=Path, default=DEFAULT_REPORT_SCHEMA)
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Optional changed paths to enforce the no-runtime PR-4 boundary.",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    for path, label in (
        (args.policy, "philosophy admission policy"),
        (args.policy_schema, "philosophy admission policy schema"),
        (args.oracle, "philosophy admission oracle fixture"),
        (args.dry_run_report, "philosophy admission dry-run report"),
        (args.dry_run_schema, "philosophy admission dry-run schema"),
        (args.roadmap, "semantic-cache roadmap"),
        (args.ledger, "backlog ledger"),
        (args.report_schema, "philosophy gate-open preconditions schema"),
    ):
        if not path.exists():
            print(f"ERROR: {label} missing: {path}", file=sys.stderr)
            return 1
    if not args.write_report and not args.report.exists():
        print(
            f"ERROR: philosophy gate-open preconditions report missing: {args.report}",
            file=sys.stderr,
        )
        return 1

    policy_text = args.policy.read_text(encoding="utf-8")
    policy_schema_text = args.policy_schema.read_text(encoding="utf-8")
    oracle_text = args.oracle.read_text(encoding="utf-8")
    dry_run_text = args.dry_run_report.read_text(encoding="utf-8")
    dry_run_schema_text = args.dry_run_schema.read_text(encoding="utf-8")
    roadmap_text = args.roadmap.read_text(encoding="utf-8")
    ledger_text = args.ledger.read_text(encoding="utf-8")
    schema_text = args.report_schema.read_text(encoding="utf-8")
    errors: list[str] = []
    if args.files:
        errors.extend(validate_touched_paths(args.files))

    if args.write_report:
        rendered, render_errors = render_philosophy_gate_open_preconditions_report(
            policy_text=policy_text,
            dry_run_text=dry_run_text,
            roadmap_text=roadmap_text,
            ledger_text=ledger_text,
            alignment_rule_schema=args.alignment_rule_schema,
        )
        errors.extend(render_errors)
        if not errors:
            errors.extend(
                validate_philosophy_gate_open_preconditions_report(
                    report_text=rendered,
                    schema_text=schema_text,
                    policy_text=policy_text,
                    policy_schema_text=policy_schema_text,
                    oracle_text=oracle_text,
                    dry_run_text=dry_run_text,
                    dry_run_schema_text=dry_run_schema_text,
                    roadmap_text=roadmap_text,
                    ledger_text=ledger_text,
                    alignment_rule_schema=args.alignment_rule_schema,
                )
            )
        if not errors:
            report_path = args.report.resolve()
            allowed_root = (REPO_ROOT / "docs" / "orchestration" / "contracts").resolve()
            if not report_path.is_relative_to(allowed_root):
                errors.append(
                    "philosophy gate-open preconditions report write path must stay under "
                    "docs/orchestration/contracts"
                )
            else:
                args.report.write_text(rendered, encoding="utf-8")

    if args.check or not args.write_report:
        if args.report.exists():
            errors.extend(
                validate_philosophy_gate_open_preconditions_report(
                    report_text=args.report.read_text(encoding="utf-8"),
                    schema_text=schema_text,
                    policy_text=policy_text,
                    policy_schema_text=policy_schema_text,
                    oracle_text=oracle_text,
                    dry_run_text=dry_run_text,
                    dry_run_schema_text=dry_run_schema_text,
                    roadmap_text=roadmap_text,
                    ledger_text=ledger_text,
                    alignment_rule_schema=args.alignment_rule_schema,
                )
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"philosophy gate-open preconditions report current: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

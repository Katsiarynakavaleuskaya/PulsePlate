#!/usr/bin/env python3
"""Deterministic dry-run guard for Philosophy semantic-cache admission."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterable
import importlib.util
import json
from pathlib import Path
import sys
from typing import get_args

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_semantic_cache_gate import (
    validate_philosophy_admission_oracle_fixture,
    validate_philosophy_semantic_cache_admission_policy,
)

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
DEFAULT_REPORT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json"
)
DEFAULT_REPORT_SCHEMA = DEFAULT_REPORT.with_suffix(".schema.json")

REPORT_ID = "philosophy_admission_dry_run_report"
REPORT_VERSION = "2026-05-21"
ROLLOUT_PHASE = "PHILOSOPHY-PR3"
GENERATED_AT = "static-2026-05-21"

FORBIDDEN_RUNTIME_PATHS = (
    "app/**",
    "core/insight/**",
    "core/knowledge/**",
    "core/verification/**",
    "core/evidence/**",
    "providers/**",
    "frontend/**",
    "ios/**",
    "alembic/**",
)

VERIFICATION_BUNDLE_STATES: tuple[dict[str, object], ...] = (
    {
        "id": "missing_verification_bundle",
        "bundle_present": False,
        "overall_status": None,
        "admission_allowed": False,
        "reason_codes": ("verification_bundle_missing",),
        "dry_run_decision": "verification_bundle_missing",
    },
    {
        "id": "failed_verification_bundle",
        "bundle_present": True,
        "overall_status": "fail",
        "admission_allowed": False,
        "reason_codes": ("verification_failed",),
        "dry_run_decision": "verification_bundle_denied",
    },
    {
        "id": "warn_verification_bundle",
        "bundle_present": True,
        "overall_status": "warn",
        "admission_allowed": False,
        "reason_codes": ("verification_warn_not_accepted",),
        "dry_run_decision": "verification_bundle_denied",
    },
    {
        "id": "passed_verification_bundle",
        "bundle_present": True,
        "overall_status": "pass",
        "admission_allowed": True,
        "reason_codes": ("verification_checks_pass",),
        "dry_run_decision": "gate_closed_deferred",
    },
)

GATE_CLOSED_ADMISSION_CLASSES: tuple[tuple[str, str], ...] = (
    ("runtime_only", "gate_closed_runtime_only"),
    ("blocked_from_cache", "blocked_from_cache"),
    ("future_cache_candidate_deferred", "gate_closed_runtime_only"),
)

DRY_RUN_DECISION_ENUMS: dict[str, tuple[object, ...]] = {
    "verification_bundle_state": (
        "missing_verification_bundle",
        "failed_verification_bundle",
        "warn_verification_bundle",
        "passed_verification_bundle",
        "not_applicable",
    ),
    "dry_run_decision": (
        "verification_bundle_missing",
        "verification_bundle_denied",
        "gate_closed_deferred",
        "gate_closed_runtime_only",
        "blocked_from_cache",
    ),
    "reason_codes": (
        "verification_bundle_missing",
        "verification_failed",
        "verification_warn_not_accepted",
        "verification_checks_pass",
        "semantic_cache_gate_closed",
    ),
}


def _load_verification_status_values() -> tuple[str, ...]:
    contract_path = REPO_ROOT / "core" / "verification" / "contracts.py"
    module_name = "_pulseplate_verification_contracts_for_dry_run"
    spec = importlib.util.spec_from_file_location(module_name, contract_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load verification contract: {contract_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        status_type = getattr(module, "VerificationStatus", None)
        values = tuple(str(value) for value in get_args(status_type))
    finally:
        sys.modules.pop(module_name, None)
    if not values:
        raise RuntimeError("VerificationStatus must define at least one status")
    return values


VERIFICATION_STATUS_VALUES = _load_verification_status_values()


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


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _object_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _reason_code_items(value: object) -> list[str]:
    if not isinstance(value, tuple):
        return []
    return [item for item in value if isinstance(item, str)]


def _case_counts(cases: Iterable[dict[str, object]]) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for case in cases:
        family = str(case.get("claim_family", ""))
        expected = str(case.get("expected", ""))
        counts[(family, expected)] += 1
    return counts


def _expected_dry_run_decisions() -> list[dict[str, object]]:
    decisions: list[dict[str, object]] = []
    for state in VERIFICATION_BUNDLE_STATES:
        decisions.append(
            {
                "id": f"verification-bundle-{state['id']}",
                "admission_class": "verification_bundle_required",
                "verification_bundle_state": state["id"],
                "bundle_present": state["bundle_present"],
                "overall_status": state["overall_status"],
                "admission_allowed": state["admission_allowed"],
                "reason_codes": _reason_code_items(state["reason_codes"]),
                "dry_run_decision": state["dry_run_decision"],
                "cache_read_allowed": False,
                "cache_write_allowed": False,
                "serving_allowed": False,
            }
        )
    for admission_class, decision in GATE_CLOSED_ADMISSION_CLASSES:
        decisions.append(
            {
                "id": f"{admission_class}-gate-closed",
                "admission_class": admission_class,
                "verification_bundle_state": "not_applicable",
                "bundle_present": False,
                "overall_status": None,
                "admission_allowed": False,
                "reason_codes": ["semantic_cache_gate_closed"],
                "dry_run_decision": decision,
                "cache_read_allowed": False,
                "cache_write_allowed": False,
                "serving_allowed": False,
            }
        )
    return decisions


def generate_philosophy_admission_dry_run_report(
    *,
    policy: dict[str, object],
    oracle: dict[str, object],
) -> dict[str, object]:
    """Generate a compact deterministic dry-run report from PR-2 policy/oracle truth."""
    families = _object_items(policy.get("claim_families"))
    oracle_cases = _object_items(oracle.get("cases"))
    counts = _case_counts(oracle_cases)
    family_summaries: list[dict[str, object]] = []
    for family in sorted(families, key=lambda item: str(item.get("id", ""))):
        family_id = str(family.get("id", ""))
        family_summaries.append(
            {
                "claim_family": family_id,
                "risk_rail": str(family.get("risk_rail", "")),
                "forbidden_case_count": counts[(family_id, "forbidden")],
                "allowed_case_count": counts[(family_id, "allowed")],
                "verification_bundle_required": family_id
                == "claim_class_verification_bundle_skipped",
            }
        )

    dry_run_decisions = _expected_dry_run_decisions()

    expected_values = [str(case.get("expected", "")) for case in oracle_cases]
    forbidden_count = expected_values.count("forbidden")
    allowed_count = expected_values.count("allowed")
    return {
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "generated_at": GENERATED_AT,
        "rollout_phase": ROLLOUT_PHASE,
        "gate_status": policy.get("gate_status"),
        "runtime_allowed": policy.get("runtime_allowed"),
        "implementation_allowed": policy.get("implementation_allowed"),
        "source_policy": {
            "policy_id": policy.get("policy_id"),
            "policy_version": policy.get("policy_version"),
            "rollout_phase": policy.get("rollout_phase"),
            "source_contract": policy.get("source_contract"),
        },
        "source_oracle": {
            "oracle_id": oracle.get("oracle_id"),
            "policy_id": oracle.get("policy_id"),
            "policy_version": oracle.get("policy_version"),
            "case_count": len(oracle_cases),
        },
        "verification_bundle_adapter": {
            "adapter_mode": "governance_dry_run_only",
            "source_contract": "core/verification/contracts.py",
            "bundle_required": True,
            "accepted_overall_statuses": ["pass"],
            "admission_allowed_required": True,
            "required_reason_codes": ["verification_checks_pass"],
            "decision_rule": (
                "A passed canonical VerificationBundle is necessary for future "
                "semantic-cache consideration, but never sufficient while the "
                "semantic-cache gate is closed."
            ),
        },
        "summary": {
            "claim_family_count": len(families),
            "oracle_case_count": len(oracle_cases),
            "forbidden_case_count": forbidden_count,
            "allowed_case_count": allowed_count,
            "dry_run_decision_count": len(dry_run_decisions),
            "all_cache_permissions_false": True,
        },
        "claim_family_summaries": family_summaries,
        "dry_run_decisions": dry_run_decisions,
        "research_basis": [
            "W3C PROV-DM: provenance entities and activity lineage inform report traceability.",
            "OPA policy-as-data: decisions are derived from auditable structured inputs.",
            "NIST AI 600-1: red-team framing remains governance evidence, not runtime authority.",
            "Metamorphic testing: missing, denied, and passed bundle states are paired controls.",
        ],
        "out_of_scope_paths": list(FORBIDDEN_RUNTIME_PATHS),
    }


def render_philosophy_admission_dry_run_report(
    *,
    policy_text: str,
    oracle_text: str,
) -> tuple[str, list[str]]:
    policy_obj, policy_errors = _load_json_no_duplicate_keys(
        policy_text,
        invalid_prefix="philosophy admission policy invalid JSON",
        duplicate_prefix="philosophy admission policy duplicate key",
    )
    if policy_errors:
        return "", policy_errors
    oracle_obj, oracle_errors = _load_json_no_duplicate_keys(
        oracle_text,
        invalid_prefix="philosophy admission oracle fixture invalid JSON",
        duplicate_prefix="philosophy admission oracle fixture duplicate key",
    )
    if oracle_errors:
        return "", oracle_errors
    policy, policy_type_errors = _as_object(policy_obj, label="philosophy admission policy")
    if policy_type_errors:
        return "", policy_type_errors
    oracle, oracle_type_errors = _as_object(oracle_obj, label="philosophy admission oracle fixture")
    if oracle_type_errors:
        return "", oracle_type_errors
    report = generate_philosophy_admission_dry_run_report(policy=policy, oracle=oracle)
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n", []


def _validate_report_schema(
    *,
    schema: object,
    report: dict[str, object],
) -> list[str]:
    if not isinstance(schema, dict):
        return ["philosophy admission dry-run schema must be an object"]
    errors: list[str] = []
    if schema.get("type") != "object":
        errors.append("philosophy admission dry-run schema root type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append("philosophy admission dry-run schema must set additionalProperties false")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("philosophy admission dry-run schema required must be a string list")
        required = []
    if not isinstance(properties, dict):
        errors.append("philosophy admission dry-run schema properties must be an object")
        properties = {}
    report_keys = set(report)
    required_keys = set(required)
    property_keys = set(properties)
    for key in sorted(report_keys - required_keys):
        errors.append(f"philosophy admission dry-run key missing from schema required: {key}")
    for key in sorted(required_keys - report_keys):
        errors.append(
            f"philosophy admission dry-run schema required key missing from report: {key}"
        )
    for key in sorted(report_keys - property_keys):
        errors.append(f"philosophy admission dry-run key missing from schema properties: {key}")
    for key in sorted(property_keys - report_keys):
        errors.append(f"philosophy admission dry-run schema property missing from report: {key}")

    for key in (
        "report_id",
        "report_version",
        "rollout_phase",
        "gate_status",
        "runtime_allowed",
        "implementation_allowed",
    ):
        spec = properties.get(key)
        if not isinstance(spec, dict) or "const" not in spec:
            errors.append(f"philosophy admission dry-run schema const missing for {key}")
            continue
        if spec["const"] != report.get(key):
            errors.append(
                f"philosophy admission dry-run schema const mismatch for {key}: "
                f"expected {spec['const']!r}, got {report.get(key)!r}"
            )
    dry_run_spec = properties.get("dry_run_decisions")
    dry_run_items = dry_run_spec.get("items") if isinstance(dry_run_spec, dict) else None
    dry_run_properties = (
        dry_run_items.get("properties") if isinstance(dry_run_items, dict) else None
    )
    if not isinstance(dry_run_properties, dict):
        errors.append("philosophy admission dry-run schema missing decision item properties")
    else:
        for key in ("verification_bundle_state", "dry_run_decision"):
            spec = dry_run_properties.get(key)
            expected_enum = list(DRY_RUN_DECISION_ENUMS[key])
            if not isinstance(spec, dict) or spec.get("enum") != expected_enum:
                errors.append(
                    "philosophy admission dry-run schema enum mismatch for "
                    f"dry_run_decisions.{key}"
                )
        overall_status = dry_run_properties.get("overall_status")
        expected_status_enum = [*VERIFICATION_STATUS_VALUES, None]
        if (
            not isinstance(overall_status, dict)
            or overall_status.get("enum") != expected_status_enum
        ):
            errors.append(
                "philosophy admission dry-run schema enum mismatch for "
                "dry_run_decisions.overall_status"
            )
        reason_codes = dry_run_properties.get("reason_codes")
        reason_items = reason_codes.get("items") if isinstance(reason_codes, dict) else None
        expected_reason_enum = list(DRY_RUN_DECISION_ENUMS["reason_codes"])
        if not isinstance(reason_items, dict) or reason_items.get("enum") != expected_reason_enum:
            errors.append(
                "philosophy admission dry-run schema enum mismatch for "
                "dry_run_decisions.reason_codes"
            )
        for key in ("cache_read_allowed", "cache_write_allowed", "serving_allowed"):
            spec = dry_run_properties.get(key)
            if not isinstance(spec, dict) or spec.get("const") is not False:
                errors.append(
                    "philosophy admission dry-run schema const missing for "
                    f"dry_run_decisions.{key}"
                )
    source_oracle = properties.get("source_oracle")
    source_oracle_properties = (
        source_oracle.get("properties") if isinstance(source_oracle, dict) else None
    )
    if not isinstance(source_oracle_properties, dict):
        errors.append("philosophy admission dry-run schema missing source_oracle properties")
    else:
        report_source_oracle = report.get("source_oracle")
        expected_oracle_id = (
            report_source_oracle.get("oracle_id")
            if isinstance(report_source_oracle, dict)
            else None
        )
        oracle_id = source_oracle_properties.get("oracle_id")
        if not isinstance(oracle_id, dict) or oracle_id.get("const") != expected_oracle_id:
            errors.append(
                "philosophy admission dry-run schema const missing for source_oracle.oracle_id"
            )
    adapter = properties.get("verification_bundle_adapter")
    adapter_properties = adapter.get("properties") if isinstance(adapter, dict) else None
    if not isinstance(adapter_properties, dict):
        errors.append(
            "philosophy admission dry-run schema missing verification_bundle_adapter properties"
        )
    else:
        expected_adapter_consts: dict[str, object] = {
            "adapter_mode": "governance_dry_run_only",
            "source_contract": "core/verification/contracts.py",
            "bundle_required": True,
            "admission_allowed_required": True,
        }
        for key, expected in expected_adapter_consts.items():
            spec = adapter_properties.get(key)
            if not isinstance(spec, dict) or spec.get("const") != expected:
                errors.append(
                    "philosophy admission dry-run schema const missing for "
                    f"verification_bundle_adapter.{key}"
                )
        accepted_statuses = adapter_properties.get("accepted_overall_statuses")
        accepted_items = (
            accepted_statuses.get("items") if isinstance(accepted_statuses, dict) else None
        )
        if not isinstance(accepted_items, dict) or accepted_items.get("const") != "pass":
            errors.append(
                "philosophy admission dry-run schema const missing for "
                "verification_bundle_adapter.accepted_overall_statuses"
            )
        required_reason_codes = adapter_properties.get("required_reason_codes")
        required_reason_items = (
            required_reason_codes.get("items") if isinstance(required_reason_codes, dict) else None
        )
        if (
            not isinstance(required_reason_items, dict)
            or required_reason_items.get("const") != "verification_checks_pass"
        ):
            errors.append(
                "philosophy admission dry-run schema const missing for "
                "verification_bundle_adapter.required_reason_codes"
            )
    summary = properties.get("summary")
    summary_properties = summary.get("properties") if isinstance(summary, dict) else None
    if not isinstance(summary_properties, dict):
        errors.append("philosophy admission dry-run schema missing summary properties")
    else:
        all_cache_permissions_false = summary_properties.get("all_cache_permissions_false")
        if (
            not isinstance(all_cache_permissions_false, dict)
            or all_cache_permissions_false.get("const") is not True
        ):
            errors.append(
                "philosophy admission dry-run schema const missing for "
                "summary.all_cache_permissions_false"
            )
    return errors


def validate_philosophy_admission_dry_run_report(
    *,
    report_text: str,
    schema_text: str,
    policy_text: str,
    policy_schema_text: str,
    oracle_text: str,
) -> list[str]:
    """Validate the canonical PR-3 dry-run report and its PR-2 inputs."""
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
    expected_text, render_errors = render_philosophy_admission_dry_run_report(
        policy_text=policy_text,
        oracle_text=oracle_text,
    )
    errors.extend(render_errors)

    report_obj, report_parse_errors = _load_json_no_duplicate_keys(
        report_text,
        invalid_prefix="philosophy admission dry-run report invalid JSON",
        duplicate_prefix="philosophy admission dry-run report duplicate key",
    )
    errors.extend(report_parse_errors)
    schema_obj, schema_parse_errors = _load_json_no_duplicate_keys(
        schema_text,
        invalid_prefix="philosophy admission dry-run schema invalid JSON",
        duplicate_prefix="philosophy admission dry-run schema duplicate key",
    )
    errors.extend(schema_parse_errors)
    if errors:
        return errors
    report, report_type_errors = _as_object(
        report_obj,
        label="philosophy admission dry-run report",
    )
    errors.extend(report_type_errors)
    if errors:
        return errors

    if expected_text and report_text != expected_text:
        errors.append(
            "philosophy admission dry-run report drift: regenerate from current policy/oracle"
        )
    errors.extend(_validate_report_schema(schema=schema_obj, report=report))

    expected_scalars: dict[str, object] = {
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "generated_at": GENERATED_AT,
        "rollout_phase": ROLLOUT_PHASE,
        "gate_status": "closed",
        "runtime_allowed": False,
        "implementation_allowed": False,
    }
    for key, expected in expected_scalars.items():
        if report.get(key) != expected:
            errors.append(
                f"philosophy admission dry-run {key}: expected {expected!r}, "
                f"got {report.get(key)!r}"
            )

    policy_obj, _policy_errors = _load_json_no_duplicate_keys(
        policy_text,
        invalid_prefix="philosophy admission policy invalid JSON",
        duplicate_prefix="philosophy admission policy duplicate key",
    )
    oracle_obj, _oracle_errors = _load_json_no_duplicate_keys(
        oracle_text,
        invalid_prefix="philosophy admission oracle fixture invalid JSON",
        duplicate_prefix="philosophy admission oracle fixture duplicate key",
    )
    policy = policy_obj if isinstance(policy_obj, dict) else {}
    oracle = oracle_obj if isinstance(oracle_obj, dict) else {}
    families = _object_items(policy.get("claim_families"))
    oracle_cases = _object_items(oracle.get("cases"))
    family_ids = {str(family.get("id", "")) for family in families}

    source_policy = report.get("source_policy")
    if not isinstance(source_policy, dict):
        errors.append("philosophy admission dry-run source_policy must be an object")
    else:
        for key in ("policy_id", "policy_version", "rollout_phase", "source_contract"):
            if source_policy.get(key) != policy.get(key):
                errors.append(f"philosophy admission dry-run source_policy mismatch for {key}")

    source_oracle = report.get("source_oracle")
    if not isinstance(source_oracle, dict):
        errors.append("philosophy admission dry-run source_oracle must be an object")
    else:
        if source_oracle.get("oracle_id") != oracle.get("oracle_id"):
            errors.append("philosophy admission dry-run source_oracle oracle_id mismatch")
        if source_oracle.get("case_count") != len(oracle_cases):
            errors.append("philosophy admission dry-run source_oracle case_count mismatch")

    adapter = report.get("verification_bundle_adapter")
    if not isinstance(adapter, dict):
        errors.append("philosophy admission dry-run verification_bundle_adapter must be an object")
    else:
        if adapter.get("adapter_mode") != "governance_dry_run_only":
            errors.append(
                "philosophy admission dry-run adapter_mode must be governance_dry_run_only"
            )
        if adapter.get("source_contract") != "core/verification/contracts.py":
            errors.append("philosophy admission dry-run adapter source_contract mismatch")
        if adapter.get("bundle_required") is not True:
            errors.append("philosophy admission dry-run adapter must require a bundle")
        if adapter.get("accepted_overall_statuses") != ["pass"]:
            errors.append("philosophy admission dry-run adapter accepted statuses must be ['pass']")
        if adapter.get("admission_allowed_required") is not True:
            errors.append("philosophy admission dry-run adapter must require admission_allowed")
        if "pass" not in VERIFICATION_STATUS_VALUES:
            errors.append("philosophy admission dry-run VerificationStatus must define pass")

    summary = report.get("summary")
    expected_values = [str(case.get("expected", "")) for case in oracle_cases]
    if not isinstance(summary, dict):
        errors.append("philosophy admission dry-run summary must be an object")
    else:
        expected_summary = {
            "claim_family_count": len(families),
            "oracle_case_count": len(oracle_cases),
            "forbidden_case_count": expected_values.count("forbidden"),
            "allowed_case_count": expected_values.count("allowed"),
            "all_cache_permissions_false": True,
        }
        for key, expected in expected_summary.items():
            if summary.get(key) != expected:
                errors.append(
                    f"philosophy admission dry-run summary {key}: "
                    f"expected {expected!r}, got {summary.get(key)!r}"
                )

    family_summaries = _object_items(report.get("claim_family_summaries"))
    if {str(item.get("claim_family", "")) for item in family_summaries} != family_ids:
        errors.append(
            "philosophy admission dry-run claim_family_summaries mismatch policy families"
        )

    decisions = _object_items(report.get("dry_run_decisions"))
    if not decisions:
        errors.append("philosophy admission dry-run decisions must not be empty")
    expected_decisions = _expected_dry_run_decisions()
    if isinstance(summary, dict) and summary.get("dry_run_decision_count") != len(
        expected_decisions
    ):
        errors.append(
            "philosophy admission dry-run summary dry_run_decision_count: "
            f"expected {len(expected_decisions)!r}, got {summary.get('dry_run_decision_count')!r}"
        )
    observed_by_id: dict[str, dict[str, object]] = {}
    for decision in decisions:
        overall_status = decision.get("overall_status")
        if overall_status is not None and overall_status not in VERIFICATION_STATUS_VALUES:
            errors.append(
                f"philosophy admission dry-run decision {decision.get('id')} "
                f"overall_status is not a VerificationStatus: {overall_status!r}"
            )
        decision_id = decision.get("id")
        if not isinstance(decision_id, str):
            errors.append("philosophy admission dry-run decision id must be a string")
        elif decision_id in observed_by_id:
            errors.append(f"philosophy admission dry-run duplicate decision id: {decision_id}")
        else:
            observed_by_id[decision_id] = decision
        for flag in ("cache_read_allowed", "cache_write_allowed", "serving_allowed"):
            if decision.get(flag) is not False:
                errors.append(
                    "philosophy admission dry-run decisions must keep "
                    f"{flag}=false for {decision.get('id')}"
                )
        if (
            decision.get("verification_bundle_state") == "passed_verification_bundle"
            and decision.get("dry_run_decision") != "gate_closed_deferred"
        ):
            errors.append(
                "philosophy admission dry-run passed bundle must remain gate_closed_deferred"
            )
    for expected in expected_decisions:
        expected_id = str(expected["id"])
        observed = observed_by_id.get(expected_id)
        if observed is None:
            errors.append(f"philosophy admission dry-run missing decision: {expected_id}")
            continue
        for key, expected_value in expected.items():
            if observed.get(key) != expected_value:
                errors.append(
                    f"philosophy admission dry-run decision {expected_id} {key}: "
                    f"expected {expected_value!r}, got {observed.get(key)!r}"
                )
    for observed_id in sorted(
        set(observed_by_id) - {str(item["id"]) for item in expected_decisions}
    ):
        errors.append(f"philosophy admission dry-run unexpected decision: {observed_id}")

    out_of_scope_paths = set(_string_items(report.get("out_of_scope_paths")))
    missing_out_of_scope = sorted(set(FORBIDDEN_RUNTIME_PATHS) - out_of_scope_paths)
    for path in missing_out_of_scope:
        errors.append(f"philosophy admission dry-run missing out-of-scope path: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Philosophy admission dry-run report determinism."
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--policy-schema", type=Path, default=DEFAULT_POLICY_SCHEMA)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--report-schema", type=Path, default=DEFAULT_REPORT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    for path, label in (
        (args.policy, "philosophy admission policy"),
        (args.policy_schema, "philosophy admission policy schema"),
        (args.oracle, "philosophy admission oracle fixture"),
        (args.report_schema, "philosophy admission dry-run schema"),
    ):
        if not path.exists():
            print(f"ERROR: {label} missing: {path}", file=sys.stderr)
            return 1
    if not args.write_report and not args.report.exists():
        print(f"ERROR: philosophy admission dry-run report missing: {args.report}", file=sys.stderr)
        return 1

    policy_text = args.policy.read_text(encoding="utf-8")
    oracle_text = args.oracle.read_text(encoding="utf-8")
    policy_schema_text = args.policy_schema.read_text(encoding="utf-8")
    schema_text = args.report_schema.read_text(encoding="utf-8")
    errors: list[str] = []
    if args.write_report:
        rendered, render_errors = render_philosophy_admission_dry_run_report(
            policy_text=policy_text,
            oracle_text=oracle_text,
        )
        errors.extend(render_errors)
        if not errors:
            errors.extend(
                validate_philosophy_admission_dry_run_report(
                    report_text=rendered,
                    schema_text=schema_text,
                    policy_text=policy_text,
                    policy_schema_text=policy_schema_text,
                    oracle_text=oracle_text,
                )
            )
        if not errors:
            report_path = args.report.resolve()
            allowed_root = (REPO_ROOT / "docs" / "orchestration" / "contracts").resolve()
            if not report_path.is_relative_to(allowed_root):
                errors.append(
                    "philosophy admission dry-run report write path must stay under "
                    "docs/orchestration/contracts"
                )
            else:
                args.report.write_text(rendered, encoding="utf-8")

    if args.check or not args.write_report:
        if args.report.exists():
            errors.extend(
                validate_philosophy_admission_dry_run_report(
                    report_text=args.report.read_text(encoding="utf-8"),
                    schema_text=schema_text,
                    policy_text=policy_text,
                    policy_schema_text=policy_schema_text,
                    oracle_text=oracle_text,
                )
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"philosophy admission dry-run report current: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from typing import cast

import pytest

import core.ai.semantic_cache_shadow_admission_harness as harness
from core.ai.semantic_cache_shadow_admission_harness import (
    PATH_IDS,
    PROVENANCE_FIELD_IDS,
    SemanticCacheShadowAdmissionInput,
    SemanticCacheShadowAdmissionReport,
    build_default_semantic_cache_shadow_admission_input,
    compose_semantic_cache_shadow_admission_report,
    to_stable_mapping,
)
from scripts.ci.check_semantic_cache_shadow_admission_harness import (
    render_semantic_cache_shadow_admission_harness_report,
    render_semantic_cache_shadow_admission_harness_schema,
    validate_semantic_cache_shadow_admission_harness_report,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "core" / "ai" / "semantic_cache_shadow_admission_harness.py"
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_semantic_cache_shadow_admission_harness.py"
CORE_AI_INIT = REPO_ROOT / "core" / "ai" / "__init__.py"
REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT.json"
)
REPORT_SCHEMA = REPORT.with_suffix(".schema.json")


def _report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


def _schema_text() -> str:
    return REPORT_SCHEMA.read_text(encoding="utf-8")


def _report_mapping() -> dict[str, object]:
    report = json.loads(_report_text())
    assert isinstance(report, dict)
    return report


def _compose_mapping(
    input_value: SemanticCacheShadowAdmissionInput | None = None,
) -> dict[str, object]:
    report = compose_semantic_cache_shadow_admission_report(
        build_default_semantic_cache_shadow_admission_input()
        if input_value is None
        else input_value
    )
    mapping = to_stable_mapping(report)
    assert isinstance(mapping, dict)
    return dict(mapping)


def _path_result(report: dict[str, object], path_id: str) -> dict[str, object]:
    results = report["path_results"]
    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, dict)
        if item["path_id"] == path_id:
            return item
    raise AssertionError(f"missing path result {path_id}")


def _string_values(value: object) -> list[str]:
    if isinstance(value, dict):
        values: list[str] = []
        for item in value.values():
            values.extend(_string_values(item))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_string_values(item))
        return values
    if isinstance(value, str):
        return [value.lower()]
    return []


def _validate(report_text: str | None = None, schema_text: str | None = None) -> list[str]:
    return validate_semantic_cache_shadow_admission_harness_report(
        report_text=report_text or _report_text(),
        schema_text=schema_text or _schema_text(),
    )


def test_shadow_harness_report_is_current() -> None:
    assert _validate() == []


def test_shadow_harness_report_and_schema_render_byte_stable() -> None:
    rendered_report, errors = render_semantic_cache_shadow_admission_harness_report()
    rendered_schema = render_semantic_cache_shadow_admission_harness_schema()

    assert errors == []
    assert rendered_report == _report_text()
    assert rendered_schema == _schema_text()


def test_shadow_harness_evidence_asset_lineage_is_metadata_only() -> None:
    report = _report_mapping()
    asset = report["evidence_asset"]
    assert isinstance(asset, dict)

    assert asset["asset_type"] == "semantic_cache_shadow_admission_harness_report"
    fingerprint = asset["artifact_fingerprint"]
    assert isinstance(fingerprint, str)
    assert fingerprint.startswith("sha256:")
    assert len(fingerprint.removeprefix("sha256:")) == 64
    assert asset["idempotency_key"].startswith("idem:semantic-cache-shadow-admission-harness:")
    assert asset["replay_behavior"] == "deterministic_static_replay_safe"
    assert asset["admission_behavior"] == "metadata_only_shadow_report_no_runtime_admission"
    upstream_assets = asset["upstream_assets"]
    assert isinstance(upstream_assets, list)
    assert [item["asset_id"] for item in upstream_assets] == [
        "semantic_cache_offline_admission_runner_report",
        "verification_provenance_contracts",
        "semantic_cache_gate_status",
    ]
    assert all(str(item["fingerprint"]).startswith("sha256:") for item in upstream_assets)


def test_shadow_harness_path_specs_and_results_order_are_canonical() -> None:
    default_mapping = _compose_mapping()
    reversed_input = SemanticCacheShadowAdmissionInput(
        produced_at="2026-06-06T00:00:00Z",
        path_ids=tuple(reversed(PATH_IDS)),
    )
    reversed_mapping = _compose_mapping(reversed_input)

    assert default_mapping == reversed_mapping
    assert [item["path_id"] for item in default_mapping["path_specs"]] == list(PATH_IDS)
    assert [item["path_id"] for item in default_mapping["path_results"]] == list(PATH_IDS)


def test_shadow_harness_normalizes_path_ids_before_ordering_specs() -> None:
    spaced_ids = tuple(f" {path_id} " for path_id in reversed(PATH_IDS))
    input_value = SemanticCacheShadowAdmissionInput(
        produced_at="2026-06-06T00:00:00Z",
        path_ids=spaced_ids,
    )

    assert input_value.path_ids == PATH_IDS
    assert _compose_mapping(input_value) == _compose_mapping()


def test_shadow_harness_projects_expected_labels_for_runtime_paths() -> None:
    report = _report_mapping()

    for spec, result in zip(report["path_specs"], report["path_results"], strict=True):
        assert isinstance(spec, dict)
        assert isinstance(result, dict)
        assert result["shadow_label"] == spec["expected_shadow_label"]

    assert (
        _path_result(report, "direct_local_answer_exact_shadow")["shadow_label"]
        == "metadata_only_candidate_gate_closed"
    )
    assert (
        _path_result(report, "rag_pre_generation_fuzzy_shadow")["shadow_label"]
        == "metadata_only_candidate_gate_closed"
    )
    assert (
        _path_result(report, "philosophical_runtime_merged_shadow")["shadow_label"]
        == "metadata_only_candidate_gate_closed"
    )
    assert (
        _path_result(report, "degraded_retrieval_stale_source_shadow")["shadow_label"]
        == "blocked_rag_degraded_shadow"
    )
    assert (
        _path_result(report, "runtime_verification_disabled_passthrough_shadow")["shadow_label"]
        == "verification_disabled_passthrough_shadow"
    )
    assert (
        _path_result(report, "missing_bundle_fail_closed_shadow")["shadow_label"]
        == "blocked_verification_bundle_shadow"
    )
    assert (
        _path_result(report, "kill_switch_request_disabled_shadow")["shadow_label"]
        == "blocked_stop_rule_shadow"
    )
    assert _path_result(report, "policy_mismatch_shadow")["shadow_label"] == (
        "blocked_false_hit_shadow"
    )


def test_shadow_harness_keeps_authority_and_backend_context_closed() -> None:
    report = _report_mapping()

    authority = report["authority_flags"]
    assert isinstance(authority, dict)
    assert authority["semantic_cache_gate_status"] == "closed"
    for key, value in authority.items():
        if key != "semantic_cache_gate_status":
            assert value is False

    for collection_name in ("path_specs", "path_results"):
        collection = report[collection_name]
        assert isinstance(collection, list)
        for item in collection:
            assert isinstance(item, dict)
            assert item["cache_read_allowed"] is False
            assert item["cache_write_allowed"] is False
            assert item["serving_allowed"] is False

    backend = report["backend_label_context"]
    assert isinstance(backend, dict)
    assert backend["runtime_allowed"] is False
    assert backend["implementation_allowed"] is False
    assert backend["cache_read_allowed"] is False
    assert backend["cache_write_allowed"] is False
    assert backend["serving_allowed"] is False
    final_decision = backend["final_decision"]
    assert isinstance(final_decision, dict)
    assert final_decision["decision"] == "no_selection"
    assert final_decision["selected_backend_label"] is None
    assert final_decision["selected_candidate_id"] is None

    final_admission = report["final_admission_decision"]
    assert isinstance(final_admission, dict)
    assert final_admission["decision"] == "shadow_report_only"
    assert final_admission["runtime_allowed"] is False
    assert final_admission["implementation_allowed"] is False
    assert final_admission["cache_read_allowed"] is False
    assert final_admission["cache_write_allowed"] is False
    assert final_admission["serving_allowed"] is False


def test_shadow_harness_provenance_labels_cover_missing_and_malformed_cases() -> None:
    report = _report_mapping()

    direct = _path_result(report, "direct_local_answer_exact_shadow")
    assert direct["provenance_complete"] is True
    assert direct["present_provenance_fields"] == list(PROVENANCE_FIELD_IDS)
    assert direct["missing_required_provenance_fields"] == []

    missing = _path_result(report, "missing_bundle_fail_closed_shadow")
    assert missing["verification_bundle_present"] is False
    assert missing["provenance_complete"] is False
    assert missing["missing_required_provenance_fields"] == list(PROVENANCE_FIELD_IDS)

    blocked = _path_result(report, "blocked_bundle_fail_closed_shadow")
    assert blocked["verification_bundle_present"] is True
    assert blocked["provenance_complete"] is False
    assert blocked["missing_required_provenance_fields"] == ["answer_digest"]


def test_shadow_harness_output_contains_no_raw_runtime_or_operator_material() -> None:
    rendered_values = "\n".join(_string_values(_report_mapping()))

    forbidden_fragments = (
        "plan protein breakfast",
        "breakfast protein plan",
        "reduce evening",
        "hydration walk",
        "/users/",
        "/tmp/",
        "provider_log",
        "workflow_log",
        "slack_payload",
        "operator_artifact",
        "local_path",
        "api_key",
        "secret",
        "healthkit",
        "diagnosis",
        "symptom",
        "medical",
    )
    for fragment in forbidden_fragments:
        assert fragment not in rendered_values


def test_shadow_harness_rejects_bad_inputs_before_rendering() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SemanticCacheShadowAdmissionInput(produced_at="2026-06-06T00:00:00Z", path_ids=())
    with pytest.raises(ValueError, match="must include all default paths"):
        SemanticCacheShadowAdmissionInput(
            produced_at="2026-06-06T00:00:00Z",
            path_ids=PATH_IDS[:-1],
        )
    with pytest.raises(ValueError, match="duplicate"):
        SemanticCacheShadowAdmissionInput(
            produced_at="2026-06-06T00:00:00Z",
            path_ids=(PATH_IDS[0], *PATH_IDS),
        )
    with pytest.raises(ValueError, match="unsupported"):
        SemanticCacheShadowAdmissionInput(
            produced_at="2026-06-06T00:00:00Z",
            path_ids=(*PATH_IDS[:-1], "unknown_path"),
        )
    with pytest.raises(ValueError, match="UTC timestamp"):
        SemanticCacheShadowAdmissionInput(produced_at="2026-06-06", path_ids=PATH_IDS)
    with pytest.raises(ValueError, match="sha256 label"):
        harness._validate_fingerprint("request_fingerprint", "digest:not-sha")
    with pytest.raises(ValueError, match="sha256 label"):
        harness._validate_fingerprint("request_fingerprint", "sha256:")
    with pytest.raises(ValueError, match="unsupported provenance field"):
        harness._ShadowPathSpec(
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
            present_provenance_fields=("raw_prompt",),
            expected_shadow_label="metadata_only_candidate_gate_closed",
            expected_action="shadow_observe_only",
            request_fingerprint="sha256:test-request",
            context_fingerprint="sha256:test-context",
            response_fingerprint="sha256:test-response",
            verification_bundle_fingerprint="sha256:test-bundle",
            reason_codes=("verification_passed",),
        )


def test_shadow_harness_rejects_wrong_report_object_types() -> None:
    with pytest.raises(ValueError, match="SemanticCacheShadowAdmissionInput"):
        compose_semantic_cache_shadow_admission_report(
            cast(SemanticCacheShadowAdmissionInput, "not-input")
        )

    with pytest.raises(ValueError, match="SemanticCacheShadowAdmissionReport"):
        to_stable_mapping(cast(SemanticCacheShadowAdmissionReport, {"not": "a-report"}))


@pytest.mark.parametrize(
    ("value", "match"),
    (
        (123, "must be a string"),
        ("", "must be non-empty"),
        ("bad token", "must not contain whitespace"),
        ("bad/token", "contains unsupported characters"),
    ),
)
def test_shadow_harness_token_validation_rejects_unsafe_values(value: object, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        harness._validate_token("path_id", cast(str, value))


def test_checker_rejects_authority_expansion_and_backend_selection() -> None:
    report = _report_mapping()
    authority = report["authority_flags"]
    assert isinstance(authority, dict)
    authority["runtime_allowed"] = True
    authority["semantic_cache_gate_status"] = "open"
    first_path = report["path_results"][0]
    assert isinstance(first_path, dict)
    first_path["cache_read_allowed"] = True
    backend = report["backend_label_context"]
    assert isinstance(backend, dict)
    final_decision = backend["final_decision"]
    assert isinstance(final_decision, dict)
    final_decision["decision"] = "selected"
    final_decision["selected_backend_label"] = "redis_label"
    final_admission = report["final_admission_decision"]
    assert isinstance(final_admission, dict)
    final_admission["cache_write_allowed"] = True

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert "authority_flags.runtime_allowed must remain false" in errors
    assert "authority_flags.semantic_cache_gate_status must remain closed" in errors
    assert any(
        "path_results." in error and "cache_read_allowed must remain false" in error
        for error in errors
    )
    assert "backend_label_context.final_decision.decision must be no_selection" in errors
    assert "backend_label_context must not select a backend label" in errors
    assert "final_admission_decision.cache_write_allowed must remain false" in errors


def test_checker_rejects_unknown_nested_keys_and_order_drift() -> None:
    report = _report_mapping()
    report["unexpected"] = "value"
    path_specs = report["path_specs"]
    assert isinstance(path_specs, list)
    first_spec = path_specs[0]
    assert isinstance(first_spec, dict)
    first_spec["unexpected"] = "value"
    path_specs.reverse()
    path_results = report["path_results"]
    assert isinstance(path_results, list)
    first_result = path_results[0]
    assert isinstance(first_result, dict)
    first_result["unexpected"] = "value"
    first_result["shadow_label"] = "wrong"

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert "report unknown key: unexpected" in errors
    assert any("path_specs." in error and "unknown key: unexpected" in error for error in errors)
    assert "path_specs order mismatch" in errors
    assert any("path_results." in error and "unknown key: unexpected" in error for error in errors)
    assert any("shadow_label does not match spec" in error for error in errors)


def test_checker_rejects_schema_drift_and_open_schema_claims() -> None:
    schema = json.loads(_schema_text())
    assert isinstance(schema, dict)
    mutated = deepcopy(schema)
    properties = mutated["properties"]
    assert isinstance(properties, dict)
    authority = properties["authority_flags"]
    assert isinstance(authority, dict)
    authority_properties = authority["properties"]
    assert isinstance(authority_properties, dict)
    runtime_allowed = authority_properties["runtime_allowed"]
    assert isinstance(runtime_allowed, dict)
    runtime_allowed["const"] = True
    path_results = properties["path_results"]
    assert isinstance(path_results, dict)
    path_results["items"] = {"type": "object", "additionalProperties": True}

    errors = _validate(schema_text=json.dumps(mutated, indent=2) + "\n")

    assert "semantic cache shadow admission harness schema drift: regenerate schema" in errors


def test_checker_rejects_evidence_asset_drift() -> None:
    report = _report_mapping()
    asset = report["evidence_asset"]
    assert isinstance(asset, dict)
    asset["artifact_fingerprint"] = "sha256:"
    asset["idempotency_key"] = "idem:wrong"
    asset["replay_behavior"] = "runtime_replay"
    upstream = asset["upstream_assets"]
    assert isinstance(upstream, list)
    upstream.reverse()

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert "evidence_asset.artifact_fingerprint must be sha256 label" in errors
    assert "evidence_asset.idempotency_key mismatch" in errors
    assert "evidence_asset.replay_behavior mismatch" in errors
    assert "evidence_asset.upstream_assets order mismatch" in errors


def test_checker_rejects_raw_leak_patterns_and_duplicate_keys() -> None:
    report = _report_mapping()
    path_results = report["path_results"]
    assert isinstance(path_results, list)
    first = path_results[0]
    assert isinstance(first, dict)
    first["raw_query"] = "redacted"
    first["reason_codes"] = ["plan protein breakfast"]
    refs = report["source_refs"]
    assert isinstance(refs, list)
    first_ref = refs[0]
    assert isinstance(first_ref, dict)
    first_ref["path"] = "/Users/example/project/file.py"
    redaction = report["redaction_assertions"]
    assert isinstance(redaction, dict)
    redaction["slack_ids_absent"] = "U123456789"

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")
    duplicate_errors = _validate(
        report_text='{"schema_version":"1.0","schema_version":"1.0"}\n',
        schema_text=_schema_text(),
    )

    assert any("forbidden key" in error and "raw_query" in error for error in errors)
    assert any("raw semantic-cache sample" in error for error in errors)
    assert any("absolute local path" in error for error in errors)
    assert any("slack id" in error for error in errors)
    assert any("duplicate key" in error for error in duplicate_errors)


def test_checker_rejects_source_ref_path_traversal() -> None:
    report = _report_mapping()
    refs = report["source_refs"]
    assert isinstance(refs, list)
    first_ref = refs[0]
    assert isinstance(first_ref, dict)
    first_ref["path"] = "../outside.py"
    first_ref["symbol"] = "bad-symbol"

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert "source_refs[0].path must be repo-relative safe path" in errors
    assert "source_refs[0].symbol must be a simple symbol" in errors


def test_checker_cli_output_is_safe_and_write_path_is_confined(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--check"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "semantic cache shadow admission harness report current" in result.stdout
    assert "/Users/" not in result.stdout
    assert "plan protein breakfast" not in result.stdout.lower()

    outside_report = tmp_path / "outside.json"
    outside_schema = tmp_path / "outside.schema.json"
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--write-report",
            "--write-schema",
            "--report",
            str(outside_report),
            "--report-schema",
            str(outside_schema),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "write path must stay under docs/orchestration/contracts" in result.stderr
    assert "/Users/" not in result.stderr


def test_shadow_harness_is_not_exported_from_core_ai_facade() -> None:
    init_text = CORE_AI_INIT.read_text(encoding="utf-8")

    assert "semantic_cache_shadow_admission_harness" not in init_text


def test_shadow_harness_core_module_uses_no_runtime_or_io_capabilities() -> None:
    assert_no_forbidden_semantic_cache_imports(
        MODULE,
        additional_allowed_imports=("core.ai.semantic_cache_offline_admission_runner",),
    )
    assert_no_forbidden_semantic_cache_calls(MODULE)


def test_offline_runner_import_exception_is_shadow_harness_local(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe_lower_layer_import.py"
    unsafe.write_text(
        "from core.ai.semantic_cache_offline_admission_runner import "
        "compose_semantic_cache_offline_admission_report\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="forbidden semantic-cache imports"):
        assert_no_forbidden_semantic_cache_imports(unsafe)

    assert_no_forbidden_semantic_cache_imports(
        unsafe,
        additional_allowed_imports=("core.ai.semantic_cache_offline_admission_runner",),
    )

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from typing import cast

import pytest

import core.ai.semantic_cache_offline_admission_runner as runner
from core.ai.semantic_cache_offline_admission_runner import (
    PHASE_IDS,
    SCENARIO_IDS,
    SemanticCacheOfflineAdmissionInput,
    SemanticCacheOfflineAdmissionReport,
    build_default_semantic_cache_offline_admission_input,
    compose_semantic_cache_offline_admission_report,
    to_stable_mapping,
)
from scripts.ci.check_semantic_cache_offline_admission_runner import (
    render_semantic_cache_offline_admission_runner_report,
    render_semantic_cache_offline_admission_runner_schema,
    validate_semantic_cache_offline_admission_runner_report,
)
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "core" / "ai" / "semantic_cache_offline_admission_runner.py"
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_semantic_cache_offline_admission_runner.py"
CORE_AI_INIT = REPO_ROOT / "core" / "ai" / "__init__.py"
REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT.json"
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
    input_value: SemanticCacheOfflineAdmissionInput | None = None,
) -> dict[str, object]:
    report = compose_semantic_cache_offline_admission_report(
        build_default_semantic_cache_offline_admission_input()
        if input_value is None
        else input_value
    )
    mapping = to_stable_mapping(report)
    assert isinstance(mapping, dict)
    return dict(mapping)


def _scenario(report: dict[str, object], scenario_id: str) -> dict[str, object]:
    scenarios = report["scenario_results"]
    assert isinstance(scenarios, list)
    for item in scenarios:
        assert isinstance(item, dict)
        if item["scenario_id"] == scenario_id:
            return item
    raise AssertionError(f"missing scenario {scenario_id}")


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
    return validate_semantic_cache_offline_admission_runner_report(
        report_text=report_text or _report_text(),
        schema_text=schema_text or _schema_text(),
    )


def test_semantic_cache_offline_admission_runner_report_is_current() -> None:
    assert _validate() == []


def test_runner_report_and_schema_render_byte_stable() -> None:
    rendered_report, errors = render_semantic_cache_offline_admission_runner_report()
    rendered_schema = render_semantic_cache_offline_admission_runner_schema()

    assert errors == []
    assert rendered_report == _report_text()
    assert rendered_schema == _schema_text()


def test_runner_keeps_scenario_and_phase_order_deterministic() -> None:
    default_mapping = _compose_mapping()
    reversed_input = SemanticCacheOfflineAdmissionInput(
        produced_at="2026-06-05T00:00:00Z",
        scenario_ids=tuple(reversed(SCENARIO_IDS)),
    )
    reversed_mapping = _compose_mapping(reversed_input)

    assert default_mapping == reversed_mapping
    assert [item["phase_id"] for item in default_mapping["phase_results"]] == list(PHASE_IDS)
    assert [item["scenario_id"] for item in default_mapping["scenario_results"]] == list(
        SCENARIO_IDS
    )


def test_runner_normalizes_scenario_ids_before_ordering_specs() -> None:
    spaced_ids = tuple(f" {scenario_id} " for scenario_id in reversed(SCENARIO_IDS))
    input_value = SemanticCacheOfflineAdmissionInput(
        produced_at="2026-06-05T00:00:00Z",
        scenario_ids=spaced_ids,
    )

    assert input_value.scenario_ids == SCENARIO_IDS
    assert _compose_mapping(input_value) == _compose_mapping()


def test_runner_covers_expected_hit_miss_block_and_false_hit_scenarios() -> None:
    report = _report_mapping()

    assert _scenario(report, "exact_safe_hit")["match_mode"] == "exact"
    assert _scenario(report, "exact_safe_hit")["lookup_decision"] == "hit"
    assert _scenario(report, "reordered_token_fuzzy_hit")["match_mode"] == (
        "fuzzy_reordered_tokens"
    )
    assert _scenario(report, "near_duplicate_fuzzy_hit")["match_mode"] == "fuzzy_near_duplicate"
    assert _scenario(report, "lookup_miss_fallback")["lookup_decision"] == "miss"
    assert _scenario(report, "lookup_miss_fallback")["bounded_decision"] == "fallback"
    assert _scenario(report, "stale_source_negative_control")["false_hit_is_false_hit"] is True
    assert (
        "policy_version_mismatch"
        in _scenario(report, "policy_mismatch_negative_control")["false_hit_blocking_reasons"]
    )
    assert (
        "model_version_mismatch"
        in _scenario(report, "model_mismatch_negative_control")["false_hit_blocking_reasons"]
    )
    assert (
        "user_context_leakage"
        in _scenario(report, "tier_mismatch_negative_control")["false_hit_blocking_reasons"]
    )
    assert (
        "user_context_leakage"
        in _scenario(report, "context_leakage_negative_control")["false_hit_blocking_reasons"]
    )
    assert _scenario(report, "admission_blocked_candidate")["bounded_decision"] == "fallback"
    assert _scenario(report, "blocked_surface_candidate")["bounded_decision"] == "fallback"
    assert _scenario(report, "kill_switch_request_disabled")["stop_serving"] is True


def test_runner_keeps_authority_and_backend_selection_closed() -> None:
    report = _report_mapping()

    authority = report["authority_flags"]
    assert isinstance(authority, dict)
    assert authority["semantic_cache_gate_status"] == "closed"
    for key, value in authority.items():
        if key != "semantic_cache_gate_status":
            assert value is False

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
    assert final_admission["decision"] == "offline_report_only"
    assert final_admission["runtime_allowed"] is False
    assert final_admission["implementation_allowed"] is False
    assert final_admission["cache_read_allowed"] is False
    assert final_admission["cache_write_allowed"] is False
    assert final_admission["serving_allowed"] is False


def test_runner_output_contains_no_raw_runtime_or_operator_material() -> None:
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
        "health_data",
        "user_data",
    )
    for fragment in forbidden_fragments:
        assert fragment not in rendered_values


def test_runner_rejects_bad_inputs_before_rendering() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SemanticCacheOfflineAdmissionInput(produced_at="2026-06-05T00:00:00Z", scenario_ids=())
    with pytest.raises(ValueError, match="must include all default scenarios"):
        SemanticCacheOfflineAdmissionInput(
            produced_at="2026-06-05T00:00:00Z",
            scenario_ids=SCENARIO_IDS[:-1],
        )
    with pytest.raises(ValueError, match="duplicate"):
        SemanticCacheOfflineAdmissionInput(
            produced_at="2026-06-05T00:00:00Z",
            scenario_ids=(SCENARIO_IDS[0], *SCENARIO_IDS),
        )
    with pytest.raises(ValueError, match="unsupported"):
        SemanticCacheOfflineAdmissionInput(
            produced_at="2026-06-05T00:00:00Z",
            scenario_ids=(*SCENARIO_IDS[:-1], "unknown_scenario"),
        )
    with pytest.raises(ValueError, match="UTC timestamp"):
        SemanticCacheOfflineAdmissionInput(produced_at="2026-06-05", scenario_ids=SCENARIO_IDS)


def test_runner_rejects_wrong_report_object_types() -> None:
    with pytest.raises(ValueError, match="SemanticCacheOfflineAdmissionInput"):
        compose_semantic_cache_offline_admission_report(
            cast(SemanticCacheOfflineAdmissionInput, "not-input")
        )

    with pytest.raises(ValueError, match="SemanticCacheOfflineAdmissionReport"):
        to_stable_mapping(cast(SemanticCacheOfflineAdmissionReport, {"not": "a-report"}))


@pytest.mark.parametrize(
    ("value", "match"),
    (
        (123, "must be a string"),
        ("", "must be non-empty"),
        ("bad token", "must not contain whitespace"),
        ("bad/token", "contains unsupported characters"),
    ),
)
def test_runner_token_validation_rejects_unsafe_values(value: object, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        runner._validate_token("scenario_id", cast(str, value))


def test_runner_json_helpers_normalize_tuple_values() -> None:
    tuple_value = ("digest:111111111111", {"nested": ("label", "digest:222222222222")})

    assert runner._freeze_json_value(tuple_value) == [
        "digest:111111111111",
        {"nested": ["label", "digest:222222222222"]},
    ]
    assert runner._json_safe_copy(tuple_value) == [
        "digest:111111111111",
        {"nested": ["label", "digest:222222222222"]},
    ]


def test_runner_rejects_malformed_backend_label_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matrix = runner._build_backend_label_context()

    monkeypatch.setattr(
        runner.sc_g5,
        "to_stable_mapping",
        lambda _matrix: {"final_decision": [], "candidate_decisions": []},
    )
    with pytest.raises(ValueError, match="final_decision must be a mapping"):
        runner._backend_label_context(matrix)

    monkeypatch.setattr(
        runner.sc_g5,
        "to_stable_mapping",
        lambda _matrix: {"final_decision": {}, "candidate_decisions": {}},
    )
    with pytest.raises(ValueError, match="candidate_decisions must be a list"):
        runner._backend_label_context(matrix)

    monkeypatch.setattr(
        runner.sc_g5,
        "to_stable_mapping",
        lambda _matrix: {"final_decision": {}, "candidate_decisions": ["not-a-mapping"]},
    )
    with pytest.raises(ValueError, match="candidate_decisions entries must be mappings"):
        runner._backend_label_context(matrix)


def test_checker_rejects_authority_expansion_and_backend_selection() -> None:
    report = _report_mapping()
    authority = report["authority_flags"]
    assert isinstance(authority, dict)
    authority["runtime_allowed"] = True
    authority["semantic_cache_gate_status"] = "open"
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
    assert "backend_label_context.final_decision.decision must be no_selection" in errors
    assert "backend_label_context must not select a backend label" in errors
    assert "final_admission_decision.cache_write_allowed must remain false" in errors


def test_checker_rejects_unknown_nested_keys_and_order_drift() -> None:
    report = _report_mapping()
    report["unexpected"] = "value"
    scenarios = report["scenario_results"]
    assert isinstance(scenarios, list)
    first_scenario = scenarios[0]
    assert isinstance(first_scenario, dict)
    first_scenario["unexpected"] = "value"
    scenarios.reverse()
    phases = report["phase_results"]
    assert isinstance(phases, list)
    first_phase = phases[0]
    assert isinstance(first_phase, dict)
    first_phase["unexpected"] = "value"

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert "report unknown key: unexpected" in errors
    assert any("scenario." in error and "unknown key: unexpected" in error for error in errors)
    assert "scenario_results order mismatch" in errors
    assert any("phase_results." in error and "unknown key: unexpected" in error for error in errors)


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
    phase_results = properties["phase_results"]
    assert isinstance(phase_results, dict)
    phase_results["items"] = {"type": "object", "additionalProperties": True}

    errors = _validate(schema_text=json.dumps(mutated, indent=2) + "\n")

    assert "semantic cache offline admission runner schema drift: regenerate schema" in errors


def test_checker_rejects_raw_leak_patterns() -> None:
    report = _report_mapping()
    scenarios = report["scenario_results"]
    assert isinstance(scenarios, list)
    first = scenarios[0]
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

    assert any("forbidden key" in error and "raw_query" in error for error in errors)
    assert any("raw semantic-cache sample" in error for error in errors)
    assert any("absolute local path" in error for error in errors)
    assert any("slack id" in error for error in errors)


def test_checker_cli_output_is_safe_and_write_path_is_confined(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--check"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "semantic cache offline admission runner report current" in result.stdout
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


def test_runner_is_not_exported_from_core_ai_facade() -> None:
    init_text = CORE_AI_INIT.read_text(encoding="utf-8")

    assert "semantic_cache_offline_admission_runner" not in init_text


def test_runner_core_module_uses_no_runtime_or_io_capabilities() -> None:
    assert_no_forbidden_semantic_cache_imports(MODULE)
    assert_no_forbidden_semantic_cache_calls(MODULE)

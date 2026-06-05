from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import scripts.ci.check_verification_provenance_admission_report as report_check
from scripts.ci.check_verification_provenance_admission_report import (
    render_verification_provenance_admission_report,
    validate_verification_provenance_admission_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_verification_provenance_admission_report.py"
REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "VERIFICATION_PROVENANCE_ADMISSION_REPORT.json"
)
REPORT_SCHEMA = REPORT.with_suffix(".schema.json")


def _report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


def _schema_text() -> str:
    return REPORT_SCHEMA.read_text(encoding="utf-8")


def _report() -> dict[str, object]:
    report = json.loads(_report_text())
    assert isinstance(report, dict)
    return report


def _validate(report_text: str | None = None, schema_text: str | None = None) -> list[str]:
    return validate_verification_provenance_admission_report(
        report_text=report_text or _report_text(),
        schema_text=schema_text or _schema_text(),
    )


def test_verification_provenance_admission_report_is_current() -> None:
    assert _validate() == []


def test_verification_provenance_admission_report_render_is_byte_stable() -> None:
    rendered, errors = render_verification_provenance_admission_report()

    assert errors == []
    assert rendered == _report_text()


def test_report_covers_expected_runtime_and_rag_paths() -> None:
    categories = _report()["path_categories"]
    assert isinstance(categories, list)

    assert [item["id"] for item in categories if isinstance(item, dict)] == [
        "rag_pre_generation",
        "rag_runtime_merged",
        "direct_local_verification_first_answer",
        "runtime_verification_disabled_passthrough",
        "fail_closed_missing_bundle_with_provenance",
    ]
    for category in categories:
        assert isinstance(category, dict)
        assert category["bundle_present"] is True
        assert category["missing_required_provenance_fields"] == []
        assert category["expected_provenance_fields"] == category["present_provenance_fields"]


def test_report_tracks_current_verification_provenance_fields() -> None:
    contract = _report()["provenance_contract"]
    assert isinstance(contract, dict)
    inventory = contract["field_inventory"]
    assert isinstance(inventory, list)

    assert [item["field"] for item in inventory if isinstance(item, dict)] == list(
        report_check.VERIFICATION_PROVENANCE_FIELDS
    )


def test_report_keeps_authority_and_cache_flags_closed() -> None:
    report = _report()
    authority = report["authority_flags"]
    assert isinstance(authority, dict)
    categories = report["path_categories"]
    assert isinstance(categories, list)

    for key, value in authority.items():
        if key == "semantic_cache_gate_status":
            assert value == "closed"
        else:
            assert value is False
    for category in categories:
        assert isinstance(category, dict)
        path_authority = category["authority"]
        assert isinstance(path_authority, dict)
        assert path_authority["semantic_cache_gate_status"] == "closed"
        assert path_authority["cache_read_allowed"] is False
        assert path_authority["cache_write_allowed"] is False
        assert path_authority["serving_allowed"] is False


def test_report_rejects_authority_expansion() -> None:
    report = _report()
    authority = report["authority_flags"]
    assert isinstance(authority, dict)
    authority["public_api_changed"] = True
    authority["semantic_cache_gate_status"] = "open"
    categories = report["path_categories"]
    assert isinstance(categories, list)
    first = categories[0]
    assert isinstance(first, dict)
    path_authority = first["authority"]
    assert isinstance(path_authority, dict)
    path_authority["cache_write_allowed"] = True

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert "authority_flags.public_api_changed must remain false" in errors
    assert "authority_flags.semantic_cache_gate_status must remain closed" in errors
    assert any("cache_write_allowed must remain false" in error for error in errors)


def test_report_rejects_unknown_report_keys() -> None:
    report = _report()
    report["unexpected"] = "value"

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert "report unknown key: unexpected" in errors


def test_report_rejects_schema_drift_and_unknown_schema_properties() -> None:
    schema = json.loads(_schema_text())
    del schema["properties"]["generated_at"]["const"]
    schema["properties"]["unexpected"] = {"type": "string"}

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert "verification provenance admission schema const mismatch for generated_at" in errors
    assert (
        "verification provenance admission schema property missing from report: unexpected"
        in errors
    )


def test_report_rejects_nested_schema_const_drift() -> None:
    schema = json.loads(_schema_text())
    del schema["properties"]["authority_flags"]["properties"]["semantic_cache_allowed"]["const"]
    schema["properties"]["authority_flags"]["properties"]["semantic_cache_allowed"][
        "type"
    ] = "boolean"
    del schema["properties"]["path_categories"]["items"]["properties"]["authority"]["properties"][
        "cache_write_allowed"
    ]["const"]
    schema["properties"]["path_categories"]["items"]["properties"]["authority"]["properties"][
        "cache_write_allowed"
    ]["type"] = "boolean"
    schema["properties"]["path_categories"]["items"]["properties"]["redaction_assertions"][
        "properties"
    ]["secrets_absent"]["const"] = False

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert any("authority_flags.properties.semantic_cache_allowed" in error for error in errors)
    assert any("authority.properties.cache_write_allowed" in error for error in errors)
    assert any("redaction_assertions.properties.secrets_absent" in error for error in errors)


def test_report_rejects_nested_schema_shape_drift() -> None:
    schema = json.loads(_schema_text())
    schema["$defs"]["provenanceFields"]["items"]["enum"].remove("answer_digest")
    schema["properties"]["path_categories"]["items"]["properties"]["expected_provenance_fields"] = {
        "type": "array"
    }
    del schema["properties"]["path_categories"]["items"]["properties"]["redacted_digest_labels"][
        "properties"
    ]["answer_digest"]
    schema["properties"]["path_categories"]["items"]["properties"]["count_labels"]["properties"][
        "prompt_char_count"
    ]["minimum"] = -1

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert any("provenanceFields enum drift" in error for error in errors)
    assert any("expected_provenance_fields ref drift" in error for error in errors)
    assert any("redacted_digest_labels keys drift" in error for error in errors)
    assert any("count_labels integer drift" in error for error in errors)


def test_report_rejects_raw_leak_patterns() -> None:
    report = _report()
    categories = report["path_categories"]
    assert isinstance(categories, list)
    category = categories[0]
    assert isinstance(category, dict)
    reason_labels = category["reason_labels"]
    assert isinstance(reason_labels, list)
    reason_labels.append("workflow_log=xoxb-secret-token")

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert any("forbidden secret token" in error for error in errors)
    assert any("forbidden diagnostic log label" in error for error in errors)


def test_report_rejects_absolute_local_path_leak() -> None:
    report = _report()
    categories = report["path_categories"]
    assert isinstance(categories, list)
    category = categories[0]
    assert isinstance(category, dict)
    source_refs = category["source_refs"]
    assert isinstance(source_refs, list)
    first_ref = source_refs[0]
    assert isinstance(first_ref, dict)
    first_ref["symbol"] = "/Users/example/private.txt"

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert any("forbidden absolute local path" in error for error in errors)


def test_report_rejects_invalid_digest_labels() -> None:
    report = _report()
    categories = report["path_categories"]
    assert isinstance(categories, list)
    category = categories[0]
    assert isinstance(category, dict)
    digest_labels = category["redacted_digest_labels"]
    assert isinstance(digest_labels, dict)
    digest_labels["input_digest"] = "sha256:not-valid"

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert any("input_digest invalid digest label" in error for error in errors)


def test_report_rejects_missing_provenance_coverage() -> None:
    report = _report()
    categories = report["path_categories"]
    assert isinstance(categories, list)
    category = categories[1]
    assert isinstance(category, dict)
    category["present_provenance_fields"] = ["input_digest"]

    errors = _validate(report_text=json.dumps(report, indent=2) + "\n")

    assert any("present_provenance_fields must match expected" in error for error in errors)


def test_checker_cli_passes_without_raw_output() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--check"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout + result.stderr
    assert "verification provenance admission report current" in result.stdout
    for forbidden in (
        "xoxb-",
        "xapp-",
        "/Users/",
        "/Users/example",
        "workflow_log=",
        "provider_log=",
        "raw prompt",
    ):
        assert forbidden not in output


def test_checker_write_report_stays_under_contracts_dir(tmp_path: Path) -> None:
    outside = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--write-report",
            "--report",
            str(outside),
            "--report-schema",
            str(REPORT_SCHEMA),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "write path must stay under docs/orchestration/contracts" in result.stderr
    assert not outside.exists()


def test_checker_avoids_runtime_import_and_dynamic_path_mutation() -> None:
    source = CHECKER.read_text(encoding="utf-8")
    forbidden_patterns = (
        "from core.verification.registry import",
        "import core.verification.registry",
        "sys.path" + ".insert",
        "spec_from_file_location",
        "module_from_spec",
        "exec_module",
        "sys.modules[",
    )

    for pattern in forbidden_patterns:
        assert pattern not in source

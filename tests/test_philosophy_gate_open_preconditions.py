from __future__ import annotations

import json
from pathlib import Path

from pytest import CaptureFixture

import scripts.ci.check_philosophy_gate_open_preconditions as preconditions
from scripts.ci.check_philosophy_gate_open_preconditions import (
    main as preconditions_main,
    render_philosophy_gate_open_preconditions_report,
    validate_touched_paths,
    validate_philosophy_gate_open_preconditions_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json"
)
POLICY_SCHEMA = POLICY.with_suffix(".schema.json")
ORACLE = (
    REPO_ROOT / "tests" / "fixtures" / "orchestration" / "philosophy_admission_claim_oracle.json"
)
DRY_RUN_REPORT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json"
)
DRY_RUN_SCHEMA = DRY_RUN_REPORT.with_suffix(".schema.json")
ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
)
REPORT_SCHEMA = REPORT.with_suffix(".schema.json")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _report() -> dict[str, object]:
    report = json.loads(_read(REPORT))
    assert isinstance(report, dict)
    return report


def _valid_alignment_rule_schema() -> dict[str, object]:
    required = [
        "rule_id",
        "provenance",
        "assertion_hints",
        "schema_version",
        "schema_hash",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://pulseplate.app/schemas/philosophy-alignment-rule.v1.json",
        "title": "PhilosophyAlignmentRule",
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": {key: {"type": "string"} for key in required},
    }


def _validate(
    *,
    report_text: str | None = None,
    schema_text: str | None = None,
    roadmap_text: str | None = None,
    alignment_rule_schema: Path | None = None,
) -> list[str]:
    return validate_philosophy_gate_open_preconditions_report(
        report_text=report_text or _read(REPORT),
        schema_text=schema_text or _read(REPORT_SCHEMA),
        policy_text=_read(POLICY),
        policy_schema_text=_read(POLICY_SCHEMA),
        oracle_text=_read(ORACLE),
        dry_run_text=_read(DRY_RUN_REPORT),
        dry_run_schema_text=_read(DRY_RUN_SCHEMA),
        roadmap_text=roadmap_text or _read(ROADMAP),
        ledger_text=_read(LEDGER),
        alignment_rule_schema=alignment_rule_schema or preconditions.DEFAULT_ALIGNMENT_RULE_SCHEMA,
    )


def test_gate_open_preconditions_report_and_schema_are_current() -> None:
    assert _validate() == []


def test_gate_open_preconditions_report_render_is_byte_stable() -> None:
    rendered, errors = render_philosophy_gate_open_preconditions_report(
        policy_text=_read(POLICY),
        dry_run_text=_read(DRY_RUN_REPORT),
        roadmap_text=_read(ROADMAP),
        ledger_text=_read(LEDGER),
    )

    assert errors == []
    assert rendered == _read(REPORT)


def test_gate_open_preconditions_keep_all_runtime_permissions_false() -> None:
    report = _report()

    assert report["gate_open_allowed"] is False
    assert report["runtime_handoff_allowed"] is False
    assert report["cache_read_allowed"] is False
    assert report["cache_write_allowed"] is False
    assert report["serving_allowed"] is False

    handoff = report["handoff_decision"]
    assert isinstance(handoff, dict)
    assert handoff["runtime_handoff_allowed"] is False
    assert handoff["cache_read_allowed"] is False
    assert handoff["cache_write_allowed"] is False
    assert handoff["serving_allowed"] is False


def test_gate_open_preconditions_block_on_alignment_schema_without_merge_proof() -> None:
    report = _report()
    precondition_rows = report["preconditions"]
    assert isinstance(precondition_rows, list)
    alignment = next(
        item
        for item in precondition_rows
        if isinstance(item, dict) and item["id"] == "pr1789_alignment_rule_schema_landed"
    )

    assert alignment["status"] == "source_present_not_merge_verified"
    assert alignment["blocks_gate_open"] is True
    assert report["runtime_handoff_allowed"] is False


def test_gate_open_preconditions_reject_filename_only_alignment_schema(
    tmp_path: Path,
) -> None:
    alignment_schema = tmp_path / "PHILOSOPHY_ALIGNMENT_RULE.schema.json"
    alignment_schema.write_text("{}", encoding="utf-8")
    rendered, errors = render_philosophy_gate_open_preconditions_report(
        policy_text=_read(POLICY),
        dry_run_text=_read(DRY_RUN_REPORT),
        roadmap_text=_read(ROADMAP),
        ledger_text=_read(LEDGER),
        alignment_rule_schema=alignment_schema,
    )
    assert errors == []

    report = json.loads(rendered)
    alignment = next(
        item
        for item in report["preconditions"]
        if item["id"] == "pr1789_alignment_rule_schema_landed"
    )

    assert alignment["status"] == "pending_external_predecessor"
    assert alignment["blocks_gate_open"] is True
    assert "present but invalid" in alignment["evidence"]
    assert report["runtime_handoff_allowed"] is False

    assert (
        validate_philosophy_gate_open_preconditions_report(
            report_text=rendered,
            schema_text=_read(REPORT_SCHEMA),
            policy_text=_read(POLICY),
            policy_schema_text=_read(POLICY_SCHEMA),
            oracle_text=_read(ORACLE),
            dry_run_text=_read(DRY_RUN_REPORT),
            dry_run_schema_text=_read(DRY_RUN_SCHEMA),
            roadmap_text=_read(ROADMAP),
            ledger_text=_read(LEDGER),
            alignment_rule_schema=alignment_schema,
        )
        == []
    )


def test_gate_open_preconditions_reject_empty_alignment_property_schemas(
    tmp_path: Path,
) -> None:
    alignment_schema = tmp_path / "PHILOSOPHY_ALIGNMENT_RULE.schema.json"
    schema = _valid_alignment_rule_schema()
    required = schema["required"]
    assert isinstance(required, list)
    schema["properties"] = {str(key): {} for key in required}
    alignment_schema.write_text(
        json.dumps(schema, indent=2) + "\n",
        encoding="utf-8",
    )

    rendered, errors = render_philosophy_gate_open_preconditions_report(
        policy_text=_read(POLICY),
        dry_run_text=_read(DRY_RUN_REPORT),
        roadmap_text=_read(ROADMAP),
        ledger_text=_read(LEDGER),
        alignment_rule_schema=alignment_schema,
    )

    assert errors == []
    report = json.loads(rendered)
    alignment = next(
        item
        for item in report["preconditions"]
        if item["id"] == "pr1789_alignment_rule_schema_landed"
    )
    assert alignment["status"] == "pending_external_predecessor"
    assert "property rule_id must not be empty" in alignment["evidence"]
    assert report["runtime_handoff_allowed"] is False


def test_gate_open_preconditions_allow_valid_alignment_schema_without_opening_gate(
    tmp_path: Path,
) -> None:
    alignment_schema = tmp_path / "PHILOSOPHY_ALIGNMENT_RULE.schema.json"
    alignment_schema.write_text(
        json.dumps(_valid_alignment_rule_schema(), indent=2) + "\n",
        encoding="utf-8",
    )
    rendered, errors = render_philosophy_gate_open_preconditions_report(
        policy_text=_read(POLICY),
        dry_run_text=_read(DRY_RUN_REPORT),
        roadmap_text=_read(ROADMAP),
        ledger_text=_read(LEDGER),
        alignment_rule_schema=alignment_schema,
    )
    assert errors == []

    report = json.loads(rendered)
    alignment = next(
        item
        for item in report["preconditions"]
        if item["id"] == "pr1789_alignment_rule_schema_landed"
    )

    assert alignment["status"] == "source_present_not_merge_verified"
    assert alignment["blocks_gate_open"] is True
    assert report["runtime_handoff_allowed"] is False
    assert report["handoff_decision"]["blocking_precondition_count"] == 2


def test_gate_open_preconditions_reject_open_roadmap_markers() -> None:
    roadmap = _read(ROADMAP).replace(
        "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
        "<!-- SEMANTIC_CACHE_GATE_STATUS: open -->",
    )

    errors = _validate(roadmap_text=roadmap)

    assert (
        "philosophy gate-open preconditions marker SEMANTIC_CACHE_GATE_STATUS: "
        "expected 'closed', got 'open'"
    ) in errors
    assert (
        "philosophy gate-open preconditions marker bool gate_status_closed: "
        "expected False, got True"
    ) in errors


def test_gate_open_preconditions_reject_runtime_permission_drift() -> None:
    report = _report()
    report["runtime_handoff_allowed"] = True
    report["cache_write_allowed"] = True
    handoff = report["handoff_decision"]
    assert isinstance(handoff, dict)
    handoff["runtime_handoff_allowed"] = True
    report_text = json.dumps(report, indent=2) + "\n"

    errors = _validate(report_text=report_text)

    assert (
        "philosophy gate-open preconditions runtime_handoff_allowed: " "expected False, got True"
    ) in errors
    assert (
        "philosophy gate-open preconditions handoff decision must keep runtime_handoff_allowed=false"
        in errors
    )


def test_gate_open_preconditions_reject_precondition_blocking_drift() -> None:
    report = _report()
    precondition_rows = report["preconditions"]
    assert isinstance(precondition_rows, list)
    pending = next(
        item
        for item in precondition_rows
        if isinstance(item, dict) and item["id"] == "pr1789_alignment_rule_schema_landed"
    )
    pending["blocks_gate_open"] = False
    report_text = json.dumps(report, indent=2) + "\n"

    errors = _validate(report_text=report_text)

    assert any("blocks_gate_open: expected True" in error for error in errors)


def test_gate_open_preconditions_reject_per_id_status_drift() -> None:
    report = _report()
    precondition_rows = report["preconditions"]
    assert isinstance(precondition_rows, list)
    pr_a1b = next(
        item
        for item in precondition_rows
        if isinstance(item, dict) and item["id"] == "pr_a1b_reconciled"
    )
    pr_a1b["status"] = "source_current"
    pr_a1b["blocks_gate_open"] = False
    handoff = report["handoff_decision"]
    assert isinstance(handoff, dict)
    handoff["blocking_precondition_count"] = 2
    report_text = json.dumps(report, indent=2) + "\n"

    errors = _validate(report_text=report_text)

    assert any(
        "pr_a1b_reconciled status: expected 'merge_verified_closed'" in error for error in errors
    )


def test_gate_open_preconditions_reject_missing_ledger_anchor() -> None:
    ledger_text = _read(LEDGER).replace(
        "docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction",
        "docs/roadmap/BACKLOG_LEDGER.md#removed-ai-bounded-context-extraction",
    )
    rendered, errors = render_philosophy_gate_open_preconditions_report(
        policy_text=_read(POLICY),
        dry_run_text=_read(DRY_RUN_REPORT),
        roadmap_text=_read(ROADMAP),
        ledger_text=ledger_text,
    )
    assert errors == []

    errors = validate_philosophy_gate_open_preconditions_report(
        report_text=rendered,
        schema_text=_read(REPORT_SCHEMA),
        policy_text=_read(POLICY),
        policy_schema_text=_read(POLICY_SCHEMA),
        oracle_text=_read(ORACLE),
        dry_run_text=_read(DRY_RUN_REPORT),
        dry_run_schema_text=_read(DRY_RUN_SCHEMA),
        roadmap_text=_read(ROADMAP),
        ledger_text=ledger_text,
    )

    assert any("missing ledger anchor" in error for error in errors)


def test_gate_open_preconditions_reject_runtime_touched_paths() -> None:
    errors = validate_touched_paths(
        [
            "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
            "core/ai/semantic_cache_backend_selection.py",
            "core/rag/retriever.py",
            "legacy_app.py",
        ]
    )

    assert any("core/ai/semantic_cache_backend_selection.py" in error for error in errors)
    assert any("core/rag/retriever.py" in error for error in errors)
    assert any("legacy_app.py" in error for error in errors)


def test_gate_open_preconditions_normalizes_touched_paths() -> None:
    errors = validate_touched_paths(
        [
            "./app/main.py",
            "docs/../core/rag/retriever.py",
            str(REPO_ROOT / "providers" / "pico.py"),
            "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
        ]
    )

    assert any("normalized app/main.py" in error for error in errors)
    assert any("normalized core/rag/retriever.py" in error for error in errors)
    assert any("normalized providers/pico.py" in error for error in errors)
    assert not any("PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json" in error for error in errors)


def test_gate_open_preconditions_rejects_paths_outside_repo() -> None:
    errors = validate_touched_paths(["/tmp/app/main.py"])

    assert any("outside repo" in error for error in errors)


def test_gate_open_preconditions_cli_rejects_runtime_touched_paths(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = preconditions_main(["--check", "--files", "mcp_pulseplate_server.py"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "forbids runtime path mcp_pulseplate_server.py" in captured.err


def test_gate_open_preconditions_schema_requires_closed_handoff_consts() -> None:
    schema = json.loads(_read(REPORT_SCHEMA))
    del schema["properties"]["handoff_decision"]["properties"]["cache_write_allowed"]["const"]

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert (
        "philosophy gate-open preconditions schema const missing for "
        "handoff_decision.cache_write_allowed"
    ) in errors


def test_gate_open_preconditions_schema_requires_closed_gate_consts() -> None:
    schema = json.loads(_read(REPORT_SCHEMA))
    del schema["properties"]["runtime_allowed"]["const"]
    del schema["properties"]["requires_dedicated_gate"]["const"]

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert "philosophy gate-open preconditions schema const missing for runtime_allowed" in errors
    assert (
        "philosophy gate-open preconditions schema const missing for requires_dedicated_gate"
        in errors
    )


def test_gate_open_preconditions_schema_requires_exact_ledger_anchors() -> None:
    schema = json.loads(_read(REPORT_SCHEMA))
    ledger = schema["properties"]["ledger_anchor_present"]
    ledger["additionalProperties"] = {"type": "boolean"}
    ledger["required"].pop()

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert "philosophy gate-open preconditions schema ledger anchors must reject extras" in errors
    assert "philosophy gate-open preconditions schema ledger required mismatch" in errors


def test_gate_open_preconditions_schema_requires_precondition_order() -> None:
    schema = json.loads(_read(REPORT_SCHEMA))
    schema["properties"]["preconditions"]["prefixItems"][0]["properties"]["id"]["const"] = "wrong"
    schema["properties"]["preconditions"]["maxItems"] = 99

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert "philosophy gate-open preconditions schema maxItems mismatch" in errors
    assert any("schema prefixItems id const missing" in error for error in errors)


def test_gate_open_preconditions_schema_requires_reason_code_coverage() -> None:
    schema = json.loads(_read(REPORT_SCHEMA))
    reason_codes = schema["properties"]["handoff_decision"]["properties"]["reason_codes"]
    reason_codes["allOf"].pop()
    reason_codes["uniqueItems"] = False

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert "philosophy gate-open preconditions schema reason codes must be unique" in errors
    assert "philosophy gate-open preconditions schema reason code coverage mismatch" in errors


def test_gate_open_preconditions_cli_check_passes(capsys: CaptureFixture[str]) -> None:
    exit_code = preconditions_main(["--check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "philosophy gate-open preconditions report current:" in captured.out

from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

from pytest import CaptureFixture
import pytest

from core.verification.contracts import VerificationStatus
import scripts.ci.check_philosophy_admission_dry_run as dry_run
from scripts.ci.check_philosophy_admission_dry_run import (
    main as dry_run_main,
    render_philosophy_admission_dry_run_report,
    validate_philosophy_admission_dry_run_report,
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
REPORT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json"
)
REPORT_SCHEMA = REPORT.with_suffix(".schema.json")


def _policy_text() -> str:
    return POLICY.read_text(encoding="utf-8")


def _policy_schema_text() -> str:
    return POLICY_SCHEMA.read_text(encoding="utf-8")


def _oracle_text() -> str:
    return ORACLE.read_text(encoding="utf-8")


def _report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


def _report_schema_text() -> str:
    return REPORT_SCHEMA.read_text(encoding="utf-8")


def _report() -> dict[str, object]:
    report = json.loads(_report_text())
    assert isinstance(report, dict)
    return report


def _validate(report_text: str | None = None, schema_text: str | None = None) -> list[str]:
    return validate_philosophy_admission_dry_run_report(
        report_text=report_text or _report_text(),
        schema_text=schema_text or _report_schema_text(),
        policy_text=_policy_text(),
        policy_schema_text=_policy_schema_text(),
        oracle_text=_oracle_text(),
    )


def test_dry_run_report_schema_and_fixture_are_current() -> None:
    assert _validate() == []


def test_dry_run_report_render_is_byte_stable() -> None:
    rendered, errors = render_philosophy_admission_dry_run_report(
        policy_text=_policy_text(),
        oracle_text=_oracle_text(),
    )

    assert errors == []
    assert rendered == _report_text()


def test_passed_verification_bundle_remains_gate_closed_deferred() -> None:
    decisions = _report()["dry_run_decisions"]
    assert isinstance(decisions, list)
    passed = [
        item
        for item in decisions
        if isinstance(item, dict)
        and item.get("verification_bundle_state") == "passed_verification_bundle"
    ]

    assert len(passed) == 1
    assert passed[0]["admission_allowed"] is True
    assert passed[0]["dry_run_decision"] == "gate_closed_deferred"
    assert passed[0]["cache_read_allowed"] is False
    assert passed[0]["cache_write_allowed"] is False
    assert passed[0]["serving_allowed"] is False


def test_dry_run_adapter_statuses_track_verification_contract() -> None:
    assert dry_run.VERIFICATION_STATUS_VALUES == tuple(get_args(VerificationStatus))

    decisions = _report()["dry_run_decisions"]
    assert isinstance(decisions, list)
    observed_statuses = {
        decision["overall_status"]
        for decision in decisions
        if isinstance(decision, dict) and decision["overall_status"] is not None
    }

    assert observed_statuses == {"pass", "warn", "fail"}


def test_all_dry_run_decisions_keep_cache_permissions_false() -> None:
    decisions = _report()["dry_run_decisions"]
    assert isinstance(decisions, list)

    for decision in decisions:
        assert isinstance(decision, dict)
        assert decision["cache_read_allowed"] is False
        assert decision["cache_write_allowed"] is False
        assert decision["serving_allowed"] is False


def test_dry_run_report_tracks_every_policy_family() -> None:
    policy = json.loads(_policy_text())
    report = _report()
    policy_family_ids = {item["id"] for item in policy["claim_families"]}
    report_family_ids = {
        item["claim_family"] for item in report["claim_family_summaries"] if isinstance(item, dict)
    }

    assert report_family_ids == policy_family_ids
    assert report["summary"]["claim_family_count"] == len(policy_family_ids)


def test_dry_run_report_rejects_open_gate_claims() -> None:
    report = _report()
    report["gate_status"] = "open"
    report["runtime_allowed"] = True
    report["implementation_allowed"] = True
    report_text = json.dumps(report, indent=2) + "\n"

    errors = _validate(report_text=report_text)

    assert "philosophy admission dry-run gate_status: expected 'closed', got 'open'" in errors
    assert "philosophy admission dry-run runtime_allowed: expected False, got True" in errors
    assert "philosophy admission dry-run implementation_allowed: expected False, got True" in errors


def test_dry_run_report_rejects_cache_permission_drift() -> None:
    report = _report()
    decisions = report["dry_run_decisions"]
    assert isinstance(decisions, list)
    decision = decisions[0]
    assert isinstance(decision, dict)
    decision["cache_write_allowed"] = True
    report_text = json.dumps(report, indent=2) + "\n"

    errors = _validate(report_text=report_text)

    assert any("cache_write_allowed=false" in error for error in errors)


def test_dry_run_report_requires_exact_bundle_state_rows() -> None:
    report = _report()
    decisions = report["dry_run_decisions"]
    assert isinstance(decisions, list)
    report["dry_run_decisions"] = [
        decision
        for decision in decisions
        if isinstance(decision, dict)
        and decision.get("verification_bundle_state") != "warn_verification_bundle"
    ]
    summary = report["summary"]
    assert isinstance(summary, dict)
    summary["dry_run_decision_count"] = len(report["dry_run_decisions"])
    report_text = json.dumps(report, indent=2) + "\n"

    errors = _validate(report_text=report_text)

    assert any(
        "missing decision: verification-bundle-warn_verification_bundle" in error
        for error in errors
    )


def test_dry_run_report_rejects_negative_bundle_state_drift() -> None:
    report = _report()
    decisions = report["dry_run_decisions"]
    assert isinstance(decisions, list)
    failed = next(
        decision
        for decision in decisions
        if isinstance(decision, dict)
        and decision.get("verification_bundle_state") == "failed_verification_bundle"
    )
    assert isinstance(failed, dict)
    failed["admission_allowed"] = True
    failed["reason_codes"] = ["verification_checks_pass"]
    report_text = json.dumps(report, indent=2) + "\n"

    errors = _validate(report_text=report_text)

    assert any(
        "decision verification-bundle-failed_verification_bundle admission_allowed" in error
        for error in errors
    )
    assert any(
        "decision verification-bundle-failed_verification_bundle reason_codes" in error
        for error in errors
    )


def test_dry_run_schema_requires_closed_gate_constants() -> None:
    schema = json.loads(_report_schema_text())
    del schema["properties"]["gate_status"]["const"]

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert "philosophy admission dry-run schema const missing for gate_status" in errors


def test_dry_run_schema_requires_nested_cache_permission_consts() -> None:
    schema = json.loads(_report_schema_text())
    decision_properties = schema["properties"]["dry_run_decisions"]["items"]["properties"]
    del decision_properties["cache_read_allowed"]["const"]

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert (
        "philosophy admission dry-run schema const missing for "
        "dry_run_decisions.cache_read_allowed"
    ) in errors


def test_dry_run_schema_requires_decision_enums() -> None:
    schema = json.loads(_report_schema_text())
    decision_properties = schema["properties"]["dry_run_decisions"]["items"]["properties"]
    del decision_properties["verification_bundle_state"]["enum"]

    errors = _validate(schema_text=json.dumps(schema, indent=2) + "\n")

    assert (
        "philosophy admission dry-run schema enum mismatch for "
        "dry_run_decisions.verification_bundle_state"
    ) in errors


def test_dry_run_report_write_rejects_paths_outside_contract_root(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    outside_contract_root = tmp_path / "PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json"

    exit_code = dry_run_main(["--write-report", "--report", str(outside_contract_root)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert not outside_contract_root.exists()
    assert "write path must stay under docs/orchestration/contracts" in captured.err


def test_dry_run_write_validates_rendered_report_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    contracts_dir = tmp_path / "docs" / "orchestration" / "contracts"
    oracle_dir = tmp_path / "tests" / "fixtures" / "orchestration"
    contracts_dir.mkdir(parents=True)
    oracle_dir.mkdir(parents=True)
    policy = contracts_dir / POLICY.name
    policy_schema = contracts_dir / POLICY_SCHEMA.name
    report_schema = contracts_dir / REPORT_SCHEMA.name
    oracle = oracle_dir / ORACLE.name
    report = contracts_dir / "PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.generated.json"

    policy_data = json.loads(_policy_text())
    policy_data["gate_status"] = "open"
    policy.write_text(json.dumps(policy_data, indent=2) + "\n", encoding="utf-8")
    policy_schema.write_text(_policy_schema_text(), encoding="utf-8")
    report_schema.write_text(_report_schema_text(), encoding="utf-8")
    oracle.write_text(_oracle_text(), encoding="utf-8")
    monkeypatch.setattr(dry_run, "REPO_ROOT", tmp_path)

    exit_code = dry_run_main(
        [
            "--write-report",
            "--policy",
            str(policy),
            "--policy-schema",
            str(policy_schema),
            "--oracle",
            str(oracle),
            "--report-schema",
            str(report_schema),
            "--report",
            str(report),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert not report.exists()
    assert "gate_status" in captured.err

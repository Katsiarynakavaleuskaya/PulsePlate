from __future__ import annotations

import json
from pathlib import Path

from pytest import CaptureFixture

from scripts.ci.check_philosophy_alignment_ledger_closeout import (
    PR1789_MERGE_COMMIT,
    PR1789_MERGED_AT,
    PR1811_MERGE_COMMIT,
    PR1811_MERGED_AT,
    main as closeout_main,
    validate_philosophy_alignment_ledger_closeout,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
PRECONDITION_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _validate(
    *,
    ledger_text: str | None = None,
    roadmap_text: str | None = None,
    precondition_report_text: str | None = None,
) -> list[str]:
    return validate_philosophy_alignment_ledger_closeout(
        ledger_text=ledger_text or _read(LEDGER),
        roadmap_text=roadmap_text or _read(ROADMAP),
        precondition_report_text=precondition_report_text or _read(PRECONDITION_REPORT),
    )


def test_alignment_ledger_closeout_current_repo_docs_pass() -> None:
    assert _validate() == []


def test_alignment_ledger_closeout_rejects_stale_active_row() -> None:
    stale = (
        _read(LEDGER)
        .replace(
            "- [x] P1: Philosophy Epic V2 alignment-rule trust schema",
            "- [ ] P1: Philosophy Epic V2 alignment-rule trust schema",
        )
        .replace("Status: Completed.", "Status: \U0001f7e1 Active branch.")
    )

    errors = _validate(ledger_text=stale)

    assert (
        "alignment ledger closeout missing evidence: "
        "- [x] P1: Philosophy Epic V2 alignment-rule trust schema"
    ) in errors
    assert "alignment ledger closeout still contains stale marker: Active branch" in errors


def test_alignment_ledger_closeout_requires_pr1789_merge_evidence() -> None:
    missing_commit = _read(LEDGER).replace(PR1789_MERGE_COMMIT, "0" * 40)
    missing_date = _read(LEDGER).replace(PR1789_MERGED_AT, "2026-05-21T00:00:00Z")

    assert f"alignment ledger closeout missing evidence: {PR1789_MERGE_COMMIT}" in _validate(
        ledger_text=missing_commit
    )
    assert f"alignment ledger closeout missing evidence: {PR1789_MERGED_AT}" in _validate(
        ledger_text=missing_date
    )


def test_alignment_ledger_closeout_requires_pr1811_reconciliation_evidence() -> None:
    missing_commit = _read(LEDGER).replace(PR1811_MERGE_COMMIT, "0" * 40)
    missing_date = _read(LEDGER).replace(PR1811_MERGED_AT, "2026-05-24T00:00:00Z")

    assert f"alignment ledger closeout missing evidence: {PR1811_MERGE_COMMIT}" in _validate(
        ledger_text=missing_commit
    )
    assert f"alignment ledger closeout missing evidence: {PR1811_MERGED_AT}" in _validate(
        ledger_text=missing_date
    )


def test_alignment_ledger_closeout_rejects_open_semantic_cache_marker() -> None:
    roadmap = _read(ROADMAP).replace(
        "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
        "<!-- SEMANTIC_CACHE_GATE_STATUS: open -->",
    )

    errors = _validate(roadmap_text=roadmap)

    assert (
        "semantic-cache roadmap marker SEMANTIC_CACHE_GATE_STATUS: expected 'closed', got 'open'"
        in errors
    )


def test_alignment_ledger_closeout_rejects_duplicate_semantic_cache_marker() -> None:
    roadmap = _read(ROADMAP).replace(
        "<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->",
        "<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: true -->\n"
        "<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->",
    )

    errors = _validate(roadmap_text=roadmap)

    assert "semantic-cache roadmap marker SEMANTIC_CACHE_ALLOWED_RUNTIME is duplicated" in errors
    assert (
        "semantic-cache roadmap marker SEMANTIC_CACHE_ALLOWED_RUNTIME: "
        "expected 'false', got 'true'"
    ) in errors


def test_alignment_ledger_closeout_rejects_runtime_handoff_flag_drift() -> None:
    report = json.loads(_read(PRECONDITION_REPORT))
    report["runtime_handoff_allowed"] = True
    report["handoff_decision"]["runtime_handoff_allowed"] = True

    errors = _validate(precondition_report_text=json.dumps(report))

    assert "gate-open precondition report must keep runtime_handoff_allowed=false" in errors
    assert (
        "gate-open precondition handoff_decision must keep runtime_handoff_allowed=false" in errors
    )


def test_alignment_ledger_closeout_rejects_duplicate_top_level_report_key() -> None:
    report = _read(PRECONDITION_REPORT).replace(
        '"runtime_handoff_allowed": false,',
        '"runtime_handoff_allowed": true,\n  "runtime_handoff_allowed": false,',
        1,
    )

    errors = _validate(precondition_report_text=report)

    assert "gate-open precondition report duplicate key: runtime_handoff_allowed" in errors


def test_alignment_ledger_closeout_rejects_duplicate_handoff_decision_key() -> None:
    report = _read(PRECONDITION_REPORT).replace(
        '    "runtime_handoff_allowed": false,',
        '    "runtime_handoff_allowed": true,\n    "runtime_handoff_allowed": false,',
        1,
    )

    errors = _validate(precondition_report_text=report)

    assert "gate-open precondition report duplicate key: runtime_handoff_allowed" in errors


def test_alignment_ledger_closeout_cli_passes(capsys: CaptureFixture[str]) -> None:
    assert closeout_main(["--check"]) == 0

    output = capsys.readouterr().out
    assert "philosophy alignment ledger closeout passed" in output

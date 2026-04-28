"""Tests for PulsePlate PR review dry-run report runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration import pr_review_report as report_runner


def _base_context() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "generated_at_utc": "2026-04-28T17:00:00Z",
        "query": {
            "repo": "Katsiarynakavaleuskaya/PulsePlate",
            "pr_number": 1539,
            "base_ref": "base",
            "head_ref": "head",
        },
        "pr": {
            "number": 1539,
            "title": "PR2",
            "state": "open",
            "url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1539",
        },
        "diff": {
            "summary": {"files": 1, "additions": 4, "deletions": 1, "changed_lines": 5},
            "files": [
                {
                    "path": "scripts/orchestration/pr_review_context.py",
                    "additions": 4,
                    "deletions": 1,
                }
            ],
        },
        "agents_discovery": {
            "scoped_agents_md": ["AGENTS.md", "scripts/AGENTS.md"],
            "files_seen": ["scripts/orchestration/pr_review_context.py"],
        },
        "fixed_mapping": {
            "path": "docs/review/PR_1539_FIXED_MAPPING.md",
            "exists": True,
            "entries": {},
            "no_actionable": True,
            "errors": [],
        },
        "test_suggestions": ["python3 scripts/orchestration/check_preflight.py"],
        "warnings": [],
    }


def test_build_report_has_no_findings_for_complete_context() -> None:
    report = report_runner.build_report(
        _base_context(),
        packet_id="packet-1",
        packet_path="artifacts/orchestration/task_packets/packet-1.json",
    )

    assert report["mode"] == "dry-run-report"
    assert report["generated_at_utc"] == "2026-04-28T17:00:00Z"
    assert report["findings"] == []
    assert report["findings_count"] == 0
    assert report["calibration"]["rubric_version"] == "pr4-2026-04-28"
    assert report["calibration"]["case_labels"] == ["clean-context"]
    assert report["calibration"]["posting_eligible"] is False
    assert report["coordinator_packet"]["task_packet_id"] == "packet-1"
    assert report["coordinator_packet"]["role_order"] == report_runner.DEFAULT_ROLE_ORDER
    assert "GitHub posting" in report["scope_reviewed"]["omitted_surfaces"]


def test_build_report_flags_missing_metadata_mapping_and_agents() -> None:
    context = _base_context()
    context["pr"] = None
    context["fixed_mapping"] = {"exists": False}
    context["agents_discovery"] = {"scoped_agents_md": [], "files_seen": []}
    context["warnings"] = ["Cannot read PR metadata: repository slug unavailable."]

    report = report_runner.build_report(context)
    findings = report["findings"]

    assert len(findings) == 4
    assert {finding["role_agent"] for finding in findings} == {
        "agent-coordinator",
        "qa-engineer-agent",
        "architecture-specialist",
    }
    assert all(finding["disposition_candidate"] == "NEEDS-HUMAN" for finding in findings)
    assert report["calibration"]["case_labels"] == [
        "warning-bearing-context",
        "governance-finding",
    ]


def test_build_report_keeps_false_positive_controls_for_benign_context() -> None:
    context = _base_context()
    context["fixed_mapping"] = {
        "path": "docs/review/PR_1539_FIXED_MAPPING.md",
        "exists": True,
        "entries": {
            "https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1539#discussion": {
                "disposition": "NOT-A-BUG",
                "evidence": "docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PR2_CONTEXT_COLLECTOR_PACKET_2026-04-26.md",
            }
        },
        "no_actionable": True,
        "errors": [],
    }

    report = report_runner.build_report(context)

    assert report["findings"] == []
    assert report["calibration"]["case_labels"] == ["clean-context"]
    assert (
        "benign fixed-mapping presence must not become a governance finding"
        in report["calibration"]["false_positive_controls"]
    )


def test_build_report_flags_malformed_fixed_mapping_context() -> None:
    context = _base_context()
    context["fixed_mapping"] = None

    report = report_runner.build_report(context)

    assert report["findings_count"] == 1
    assert report["findings"][0]["role_agent"] == "qa-engineer-agent"
    assert report["findings"][0]["file"] == "docs/review/PR_1539_FIXED_MAPPING.md"
    assert report["calibration"]["case_labels"] == ["governance-finding"]


def test_build_report_flags_large_diff() -> None:
    context = _base_context()
    context["diff"] = {
        "summary": {"files": 12, "additions": 901, "deletions": 4, "changed_lines": 905},
        "files": [
            {"path": "scripts/orchestration/pr_review_report.py", "additions": 901, "deletions": 4}
        ],
    }

    report = report_runner.build_report(context)

    assert report["findings"][0]["role_agent"] == "bug-hunter"
    assert "905 changed lines" in report["findings"][0]["evidence"]
    assert "make validate-changed" in report["gate_plan"]
    assert report["calibration"]["case_labels"] == ["large-diff-risk"]
    assert report["gate_plan"].index("python3 scripts/orchestration/check_preflight.py") < report[
        "gate_plan"
    ].index("make validate-changed")


def test_render_markdown_contains_required_sections() -> None:
    report = report_runner.build_report(_base_context(), packet_id="packet-1")

    markdown = report_runner.render_markdown(report)

    assert "# PulsePlate PR Review Dry-Run Report" in markdown
    assert "## Coordinator Packet" in markdown
    assert "## Scope Reviewed" in markdown
    assert "## Findings" in markdown
    assert "## Calibration" in markdown
    assert "## Deferred / Follow-ups" in markdown
    assert "## Warnings" in markdown
    assert "No deterministic findings" in markdown
    assert "GitHub posting eligible: `false`" in markdown
    assert "agent-coordinator -> architecture-specialist" in markdown


def test_main_writes_json_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_path = tmp_path / "context.json"
    output_path = tmp_path / "report.json"
    context_path.write_text(json.dumps(_base_context()), encoding="utf-8")
    monkeypatch.setattr(
        report_runner.sys,
        "argv",
        [
            "pr_review_report.py",
            "--context",
            str(context_path),
            "--format",
            "json",
            "--output",
            str(output_path),
        ],
    )

    assert report_runner.main() == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["mode"] == "dry-run-report"
    assert payload["findings"] == []


def test_load_context_reports_unreadable_file(tmp_path: Path) -> None:
    missing_context = tmp_path / "missing-context.json"

    with pytest.raises(SystemExit, match="Unable to read context JSON"):
        report_runner._load_context(str(missing_context))

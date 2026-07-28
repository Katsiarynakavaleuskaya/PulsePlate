"""Tests for PulsePlate PR review dry-run report runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration import pr_review_report as report_runner


def _base_context() -> dict[str, object]:
    return {
        "schema_version": "2.0.0",
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
        "material": {
            "base_ref_oid": "c" * 40,
            "material_head_sha": "a" * 40,
            "material_digest": "sha256:" + "b" * 64,
            "merge_base_sha": "d" * 40,
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
        "review_source_status": [
            {
                "source": "github_pr_metadata",
                "status": "available",
                "source_degraded": False,
                "fallback_required": False,
                "blocking": False,
                "reason": "",
                "evidence": "gh api repos/<repo>/pulls/<pr>",
            }
        ],
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
    assert report["base_ref_oid"] == "c" * 40
    assert report["material_head_sha"] == "a" * 40
    assert report["material_digest"] == "sha256:" + "b" * 64
    assert report["merge_base_sha"] == "d" * 40
    assert report["generated_at_utc"] == "2026-04-28T17:00:00Z"
    assert report["findings"] == []
    assert report["findings_count"] == 0
    assert report["actionable_findings_count"] == 0
    assert report["calibration"]["rubric_version"] == "pr4-2026-04-28"
    assert report["calibration"]["case_labels"] == ["clean-context"]
    assert report["calibration"]["posting_eligible"] is False
    assert report["coordinator_packet"]["task_packet_id"] == "packet-1"
    assert report["coordinator_packet"]["role_order"] == report_runner.DEFAULT_ROLE_ORDER
    assert report["review_source_status"][0]["source_degraded"] is False
    assert "GitHub posting" in report["scope_reviewed"]["omitted_surfaces"]


def test_build_report_does_not_flag_mapping_missing_before_closeout() -> None:
    context = _base_context()
    context["pr"] = None
    context["fixed_mapping"] = {"exists": False}
    context["agents_discovery"] = {"scoped_agents_md": [], "files_seen": []}
    context["warnings"] = ["Cannot read PR metadata: repository slug unavailable."]
    context["review_source_status"] = [
        {
            "source": "github_pr_metadata",
            "status": "unavailable",
            "source_degraded": True,
            "fallback_required": True,
            "blocking": False,
            "reason": "PR metadata unavailable",
            "evidence": "",
        }
    ]

    report = report_runner.build_report(context)
    findings = report["findings"]

    assert len(findings) == 3
    assert {finding["role_agent"] for finding in findings} == {
        "agent-coordinator",
        "architecture-specialist",
    }
    assert all(finding["disposition_candidate"] == "NEEDS-HUMAN" for finding in findings)
    assert all(finding["severity"] == "minor" for finding in findings)
    assert report["actionable_findings_count"] == 3
    assert report["calibration"]["case_labels"] == [
        "warning-bearing-context",
        "review-source-degraded",
        "governance-finding",
    ]


def test_build_report_flags_malformed_existing_mapping() -> None:
    context = _base_context()
    context["fixed_mapping"] = {
        "exists": True,
        "repo_path": "docs/review/PR_1539_FIXED_MAPPING.md",
        "errors": ["Existing mapping seal is stale for current head."],
    }

    report = report_runner.build_report(context)

    assert report["findings_count"] == 1
    assert report["findings"][0]["role_agent"] == "qa-engineer-agent"
    assert "stale" in report["findings"][0]["evidence"]


def test_degraded_review_source_status_is_not_a_finding_by_itself() -> None:
    context = _base_context()
    context["review_source_status"] = [
        {
            "source": "coderabbit",
            "status": "rate_limited",
            "source_degraded": True,
            "fallback_required": True,
            "blocking": False,
            "reason": "usage limit reached",
            "evidence": "local dry-run fallback",
        }
    ]

    report = report_runner.build_report(context)

    assert report["findings"] == []
    assert report["calibration"]["case_labels"] == [
        "clean-context",
        "review-source-degraded",
    ]


def test_blocking_review_source_status_becomes_governance_finding() -> None:
    context = _base_context()
    context["review_source_status"] = [
        {
            "source": "coderabbit",
            "status": "actionable_bot_comments",
            "source_degraded": False,
            "fallback_required": True,
            "blocking": True,
            "reason": "bot reported actionable comments",
            "evidence": "review source summary",
        }
    ]

    report = report_runner.build_report(context)

    assert report["findings_count"] == 1
    assert report["findings"][0]["file"] == "scripts/orchestration/review_source_status.py"


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


def test_build_report_accepts_raw_diff_mapping_presence_with_material_only_scope() -> None:
    context = _base_context()
    context["fixed_mapping"] = {
        "repo_path": "docs/review/PR_1539_FIXED_MAPPING.md",
        "exists": True,
        "present_in_pr_diff": True,
        "entries": {},
        "no_actionable": True,
        "errors": [],
    }

    report = report_runner.build_report(context)

    assert report["findings"] == []
    assert report["scope_reviewed"]["changed_files"] == [
        "scripts/orchestration/pr_review_context.py"
    ]
    assert report["calibration"]["case_labels"] == ["clean-context"]


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
    assert report["findings"][0]["severity"] == "note"
    assert report["findings"][0]["diagnostic_code"] == "large_diff_review_risk"
    assert report["findings"][0]["disposition_candidate"] == "NOT-A-BUG"
    assert report["findings_count"] == 1
    assert report["actionable_findings_count"] == 0
    assert "905 changed lines" in report["findings"][0]["evidence"]
    assert "make validate-changed" in report["gate_plan"]
    assert report["calibration"]["case_labels"] == ["large-diff-risk"]
    assert report["gate_plan"].index("python3 scripts/orchestration/check_preflight.py") < report[
        "gate_plan"
    ].index("make validate-changed")


def test_calibration_keys_large_diff_only_from_diagnostic_code() -> None:
    decoy = report_runner.Finding(
        severity="minor",
        diagnostic_code="invalid_changed_lines",
        role_agent="bug-hunter",
        category="tests",
        file="scripts/orchestration/pr_review_context.py",
        line=None,
        evidence="Diff contains 905 changed lines, above review-risk threshold 800.",
        suggested_fix="Regenerate the review context.",
        gate_to_run="make validate-changed",
        disposition_candidate="NEEDS-HUMAN",
    )

    calibration = report_runner._build_calibration(_base_context(), [decoy])

    assert "large-diff-risk" not in calibration["case_labels"]


def test_build_report_handles_non_numeric_changed_lines() -> None:
    context = _base_context()
    context["diff"] = {
        "summary": {"files": 1, "additions": 4, "deletions": 1, "changed_lines": "not-a-number"},
        "files": [
            {"path": "scripts/orchestration/pr_review_report.py", "additions": 4, "deletions": 1}
        ],
    }

    report = report_runner.build_report(context)

    assert report["findings_count"] == 1
    assert report["actionable_findings_count"] == 1
    assert report["findings"][0]["role_agent"] == "qa-engineer-agent"
    assert "changed_lines is not numeric" in report["findings"][0]["evidence"]
    assert report["calibration"]["case_labels"] == ["governance-finding"]


def test_needs_human_diagnostics_cannot_be_demoted_to_notes() -> None:
    context = _base_context()
    context["pr"] = None
    context["warnings"] = ["Required current-head security check is uncertain."]
    context["fixed_mapping"] = {
        "exists": True,
        "errors": ["Existing mapping seal is stale for current head."],
    }
    context["agents_discovery"] = {"scoped_agents_md": [], "files_seen": []}
    context["review_source_status"] = [
        {
            "source": "security",
            "status": "failed",
            "blocking": True,
        }
    ]
    context["diff"] = {
        "summary": {"changed_lines": "unknown"},
        "files": [],
    }

    report = report_runner.build_report(context)
    needs_human = [
        finding
        for finding in report["findings"]
        if finding["disposition_candidate"] == "NEEDS-HUMAN"
    ]

    assert {finding["diagnostic_code"] for finding in needs_human} == {
        "blocking_review_source",
        "context_warning",
        "invalid_changed_lines",
        "invalid_fixed_mapping",
        "missing_pr_metadata",
        "missing_scoped_agents",
    }
    assert all(finding["severity"] in {"critical", "major", "minor"} for finding in needs_human)
    assert report["actionable_findings_count"] == len(needs_human)


def test_render_markdown_contains_required_sections() -> None:
    context = _base_context()
    context["diff"] = {
        "summary": {"files": 12, "additions": 901, "deletions": 4, "changed_lines": 905},
        "files": [
            {"path": "scripts/orchestration/pr_review_report.py", "additions": 901, "deletions": 4}
        ],
    }
    report = report_runner.build_report(context, packet_id="packet-1")

    markdown = report_runner.render_markdown(report)

    assert "# PulsePlate PR Review Dry-Run Report" in markdown
    assert "## Coordinator Packet" in markdown
    assert "## Scope Reviewed" in markdown
    assert "## Findings" in markdown
    assert "## Review Source Status" in markdown
    assert "## Calibration" in markdown
    assert "## Deferred / Follow-ups" in markdown
    assert "## Warnings" in markdown
    assert "Case labels: `large-diff-risk`" in markdown
    assert "GitHub posting eligible: `false`" in markdown
    assert "Posting gate: GitHub posting remains out of scope" in markdown
    assert "False-positive controls:" in markdown
    assert "clean context must produce zero findings" in markdown
    assert "source-degraded `false`; fallback-required `false`; blocking `false`" in markdown
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

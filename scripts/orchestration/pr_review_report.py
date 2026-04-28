#!/usr/bin/env python3
"""Render deterministic dry-run reports for the PulsePlate PR review skill."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROLE_ORDER = [
    "agent-coordinator",
    "architecture-specialist",
    "security-auditor",
    "qa-engineer-agent",
    "bug-hunter",
    "data-scientist-agent",
]

LARGE_DIFF_CHANGED_LINES = 300
VERY_LARGE_DIFF_CHANGED_LINES = 800


@dataclass(frozen=True)
class Finding:
    severity: str
    role_agent: str
    category: str
    file: str
    line: int | None
    evidence: str
    suggested_fix: str
    gate_to_run: str
    disposition_candidate: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_context(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid context JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Invalid context JSON: expected object at top level.")
    return payload


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dedupe_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _context_path(context: dict[str, Any], default: str) -> str:
    query = _as_dict(context.get("query"))
    pr_number = query.get("pr_number")
    if pr_number:
        return f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    return default


def build_findings(context: dict[str, Any]) -> list[Finding]:
    """Build conservative advisory findings from context collector output."""

    findings: list[Finding] = []
    warnings = _dedupe_strings(_as_list(context.get("warnings")))
    for warning in warnings:
        findings.append(
            Finding(
                severity="note",
                role_agent="agent-coordinator",
                category="governance",
                file="scripts/orchestration/pr_review_context.py",
                line=None,
                evidence=warning,
                suggested_fix="Review the warning before using this report as PR evidence.",
                gate_to_run="python3 scripts/orchestration/pr_review_context.py --pr <PR_NUMBER>",
                disposition_candidate="NEEDS-HUMAN",
            )
        )

    if context.get("pr") is None:
        findings.append(
            Finding(
                severity="note",
                role_agent="agent-coordinator",
                category="governance",
                file="scripts/orchestration/pr_review_context.py",
                line=None,
                evidence="PR metadata is unavailable in the supplied context.",
                suggested_fix="Run the context collector with --pr and --repo when a PR exists.",
                gate_to_run="python3 scripts/orchestration/pr_review_context.py --pr <PR_NUMBER> --repo <OWNER/REPO>",
                disposition_candidate="NEEDS-HUMAN",
            )
        )

    fixed_mapping = context.get("fixed_mapping")
    if isinstance(fixed_mapping, dict) and not fixed_mapping.get("exists"):
        findings.append(
            Finding(
                severity="note",
                role_agent="qa-engineer-agent",
                category="governance",
                file=_context_path(context, "docs/review/PR_<N>_FIXED_MAPPING.md"),
                line=None,
                evidence="Fixed-mapping artifact is missing or not available.",
                suggested_fix="Create the canonical fixed-mapping artifact after the PR number is assigned.",
                gate_to_run="python3 scripts/orchestration/check_review_threads_disposition.py --pr-number <PR_NUMBER> --require-auth",
                disposition_candidate="NEEDS-HUMAN",
            )
        )

    agents_discovery = context.get("agents_discovery")
    scoped_agents = []
    if isinstance(agents_discovery, dict):
        scoped_agents = [str(item) for item in _as_list(agents_discovery.get("scoped_agents_md"))]
    if not scoped_agents:
        findings.append(
            Finding(
                severity="note",
                role_agent="architecture-specialist",
                category="architecture",
                file="AGENTS.md",
                line=None,
                evidence="No scoped AGENTS.md files were discovered for the changed files.",
                suggested_fix="Confirm the changed paths and load the applicable scoped AGENTS.md before review.",
                gate_to_run="python3 scripts/orchestration/check_preflight.py",
                disposition_candidate="NEEDS-HUMAN",
            )
        )

    diff = _as_dict(context.get("diff"))
    summary = _as_dict(diff.get("summary"))
    changed_lines = int(summary.get("changed_lines") or 0)
    if changed_lines > LARGE_DIFF_CHANGED_LINES:
        threshold = (
            VERY_LARGE_DIFF_CHANGED_LINES
            if changed_lines > VERY_LARGE_DIFF_CHANGED_LINES
            else LARGE_DIFF_CHANGED_LINES
        )
        findings.append(
            Finding(
                severity="note",
                role_agent="bug-hunter",
                category="tests",
                file="docs/roadmap/BACKLOG_LEDGER.md",
                line=None,
                evidence=f"Diff contains {changed_lines} changed lines, above review-risk threshold {threshold}.",
                suggested_fix="Confirm PR split rationale and targeted deterministic gates before opening review.",
                gate_to_run="make validate-changed",
                disposition_candidate="NEEDS-HUMAN",
            )
        )

    return findings


def _build_role_reviews(findings: list[Finding]) -> list[dict[str, str]]:
    reviews: list[dict[str, str]] = []
    for role in DEFAULT_ROLE_ORDER:
        owned = [finding for finding in findings if finding.role_agent == role]
        if owned:
            summary = f"{role} flagged {len(owned)} advisory finding(s) for human review."
        elif role == "data-scientist-agent":
            summary = (
                "data-scientist-agent has no scoring calibration changes in this dry-run report."
            )
        else:
            summary = f"{role} has no deterministic findings from the supplied context."
        reviews.append({"role_agent": role, "summary": summary})
    return reviews


def _build_scope(context: dict[str, Any]) -> dict[str, Any]:
    diff = _as_dict(context.get("diff"))
    agents = _as_dict(context.get("agents_discovery"))
    files = _as_list(diff.get("files"))
    return {
        "changed_files": [str(item.get("path", "")) for item in files if isinstance(item, dict)],
        "diff_summary": diff.get("summary", {}),
        "scoped_agents_md": agents.get("scoped_agents_md", []),
        "omitted_surfaces": ["GitHub posting", "PR thread resolution", "merge readiness claims"],
    }


def _build_gate_plan(context: dict[str, Any], findings: list[Finding]) -> list[str]:
    suggestions = [str(item) for item in _as_list(context.get("test_suggestions"))]
    base = [
        "python3 scripts/orchestration/check_preflight.py",
        "python3 scripts/orchestration/check_agent_consistency.py",
        "python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q",
    ]
    finding_gates = [finding.gate_to_run for finding in findings if finding.gate_to_run]
    return sorted(set(base + suggestions + finding_gates))


def build_report(
    context: dict[str, Any],
    *,
    packet_id: str = "",
    packet_path: str = "",
) -> dict[str, Any]:
    findings = build_findings(context)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "mode": "dry-run-report",
        "coordinator_packet": {
            "task_packet_id": packet_id,
            "path": packet_path,
            "role_order": DEFAULT_ROLE_ORDER,
        },
        "scope_reviewed": _build_scope(context),
        "findings_count": len(findings),
        "findings": [finding.__dict__ for finding in findings],
        "role_review": _build_role_reviews(findings),
        "gate_plan": _build_gate_plan(context, findings),
        "deferred_followups": [],
        "decision_log": [
            "This report is advisory and side-effect free.",
            "This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.",
            "External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals.",
        ],
        "warnings": _dedupe_strings(_as_list(context.get("warnings"))),
    }


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PulsePlate PR Review Dry-Run Report",
        "",
        "## Coordinator Packet",
    ]
    packet = report["coordinator_packet"]
    lines.append(f"- Task packet: `{packet.get('task_packet_id') or 'unknown'}`")
    lines.append(f"- Packet path: `{packet.get('path') or 'unknown'}`")
    lines.append("- Role order: " + " -> ".join(packet["role_order"]))
    lines.extend(["", "## Scope Reviewed"])
    scope = report["scope_reviewed"]
    summary = scope.get("diff_summary", {})
    lines.append(
        "- Diff summary: "
        f"{summary.get('files', 0)} files, "
        f"{summary.get('additions', 0)} additions, "
        f"{summary.get('deletions', 0)} deletions"
    )
    changed_files = scope.get("changed_files") or []
    lines.append("- Changed files:")
    if changed_files:
        lines.extend(f"  - `{path}`" for path in changed_files)
    else:
        lines.append("  - none discovered")
    lines.extend(["", "## Findings"])
    findings = report.get("findings") or []
    if not findings:
        lines.append("- No deterministic findings from supplied context.")
    for finding in findings:
        location = finding["file"]
        if finding.get("line"):
            location = f"{location}:{finding['line']}"
        lines.extend(
            [
                f"- `{finding['severity']}` `{finding['role_agent']}` `{finding['category']}` at `{location}`",
                f"  - Evidence: {_format_value(finding.get('evidence'))}",
                f"  - Suggested fix: {_format_value(finding.get('suggested_fix'))}",
                f"  - Gate: `{_format_value(finding.get('gate_to_run'))}`",
                f"  - Disposition candidate: `{_format_value(finding.get('disposition_candidate'))}`",
            ]
        )
    lines.extend(["", "## Role Review"])
    for review in report["role_review"]:
        lines.append(f"- `{review['role_agent']}`: {review['summary']}")
    lines.extend(["", "## Gate Plan"])
    lines.extend(f"- `{gate}`" for gate in report["gate_plan"])
    lines.extend(["", "## Deferred / Follow-ups"])
    followups = report.get("deferred_followups") or []
    if followups:
        lines.extend(f"- {item}" for item in followups)
    else:
        lines.append("- None recorded by this dry-run report.")
    lines.extend(["", "## Warnings"])
    warnings = report.get("warnings") or []
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")
    lines.extend(["", "## Decision Log"])
    lines.extend(f"- {entry}" for entry in report["decision_log"])
    return "\n".join(lines) + "\n"


def _validate_output_path(path: str) -> Path:
    output_path = Path(path).resolve()
    try:
        rel = output_path.relative_to(REPO_ROOT)
    except ValueError:
        return output_path
    if rel.parts and rel.parts[0] == "artifacts":
        return output_path
    raise SystemExit("Refusing to write report inside repo outside gitignored artifacts/.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a side-effect-free PulsePlate PR review dry-run report."
    )
    parser.add_argument(
        "--context", help="Path to pr_review_context.py JSON output; stdin if omitted"
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", help="Write report to file instead of stdout")
    parser.add_argument("--packet-id", default="", help="Coordinator task packet id")
    parser.add_argument("--packet-path", default="", help="Coordinator task packet path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    context = _load_context(args.context)
    report = build_report(context, packet_id=args.packet_id, packet_path=args.packet_path)
    rendered = (
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.format == "json"
        else render_markdown(report)
    )
    if args.output:
        _validate_output_path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

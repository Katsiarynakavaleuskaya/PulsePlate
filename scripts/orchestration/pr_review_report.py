#!/usr/bin/env python3
"""Render deterministic dry-run reports for the PulsePlate PR review skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.pr_review_evidence import (
    build_self_review_receipt,
    compute_material_manifest,
    self_review_report_content_digest,
)
from scripts.orchestration.review_source_status import summarize_degraded_sources

SCHEMA_VERSION = "1.0.0"
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
CALIBRATION_RUBRIC_VERSION = "pr4-2026-04-28"
FALSE_POSITIVE_CONTROLS = (
    "clean context must produce zero findings",
    "benign fixed-mapping presence must not become a governance finding",
    "warnings are advisory NEEDS-HUMAN findings, not auto-postable comments",
    "review-source degradation is status/warning only unless an explicit blocking source finding exists",
    "large diff risk is review-planning evidence, not a merge-readiness claim",
)
_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


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


def _load_context(path: str | None) -> dict[str, Any]:
    try:
        raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    except OSError as exc:
        raise SystemExit(f"Unable to read context JSON: {exc}") from exc
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


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _context_path(context: dict[str, Any], default: str) -> str:
    query = _as_dict(context.get("query"))
    pr_number = query.get("pr_number")
    if pr_number:
        return f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    return default


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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

    fixed_mapping = _as_dict(context.get("fixed_mapping"))
    if not fixed_mapping.get("exists"):
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

    review_sources = [
        item for item in _as_list(context.get("review_source_status")) if isinstance(item, dict)
    ]
    for blocking_source in [item for item in review_sources if bool(item.get("blocking"))]:
        findings.append(
            Finding(
                severity="note",
                role_agent="agent-coordinator",
                category="governance",
                file="scripts/orchestration/review_source_status.py",
                line=None,
                evidence=(
                    "Review source has explicit blocking status: "
                    f"{blocking_source.get('source')}={blocking_source.get('status')}"
                ),
                suggested_fix=(
                    "Fix or disposition the underlying fallback finding, failed required check, "
                    "unresolved thread, or actionable bot comment before readiness claims."
                ),
                gate_to_run="python3 scripts/orchestration/pr_review_context.py --pr <PR_NUMBER>",
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
    changed_lines = _coerce_int(summary.get("changed_lines") or 0)
    if changed_lines is None:
        findings.append(
            Finding(
                severity="note",
                role_agent="qa-engineer-agent",
                category="governance",
                file="scripts/orchestration/pr_review_context.py",
                line=None,
                evidence="diff.summary.changed_lines is not numeric; treated as 0 for advisory planning.",
                suggested_fix="Regenerate context or set diff.summary.changed_lines to an integer value.",
                gate_to_run="python3 scripts/orchestration/pr_review_context.py --pr <PR_NUMBER>",
                disposition_candidate="NEEDS-HUMAN",
            )
        )
        changed_lines = 0
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
    return _ordered_unique(base + suggestions + finding_gates)


def _build_calibration(context: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    warnings = _dedupe_strings(_as_list(context.get("warnings")))
    degraded_sources = summarize_degraded_sources(
        [item for item in _as_list(context.get("review_source_status")) if isinstance(item, dict)]
    )
    categories = {finding.category for finding in findings}
    case_labels: list[str] = []
    has_large_diff_risk = any(
        finding.category == "tests"
        and finding.role_agent == "bug-hunter"
        and finding.gate_to_run == "make validate-changed"
        and "changed lines" in finding.evidence
        for finding in findings
    )

    if not findings:
        case_labels.append("clean-context")
    if warnings:
        case_labels.append("warning-bearing-context")
    if degraded_sources:
        case_labels.append("review-source-degraded")
    if "governance" in categories:
        case_labels.append("governance-finding")
    if has_large_diff_risk:
        case_labels.append("large-diff-risk")

    return {
        "rubric_version": CALIBRATION_RUBRIC_VERSION,
        "case_labels": case_labels,
        "false_positive_controls": list(FALSE_POSITIVE_CONTROLS),
        "posting_eligible": False,
        "posting_gate": "GitHub posting remains out of scope until a dedicated calibrated posting PR.",
    }


def _build_self_review_receipt(
    context: dict[str, Any],
    findings: list[Finding],
    report: dict[str, Any],
) -> dict[str, Any] | None:
    """Build exact-material evidence only for a complete Git-backed context."""

    query = _as_dict(context.get("query"))
    base_ref = query.get("base_ref")
    head_ref = query.get("head_ref")
    pr_number = query.get("pr_number")
    if (
        not isinstance(base_ref, str)
        or _FULL_SHA_RE.fullmatch(base_ref) is None
        or not isinstance(head_ref, str)
        or _FULL_SHA_RE.fullmatch(head_ref) is None
        or not isinstance(pr_number, int)
        or isinstance(pr_number, bool)
        or pr_number <= 0
    ):
        return None
    unresolved_actionables = sum(
        finding.severity in {"critical", "major", "minor"}
        and finding.disposition_candidate == "NEEDS-HUMAN"
        for finding in findings
    )
    manifest = compute_material_manifest(
        REPO_ROOT,
        base_ref_oid=base_ref,
        head_ref_oid=head_ref,
        pr_number=pr_number,
    )
    receipt: dict[str, Any] = build_self_review_receipt(
        material_head_sha=head_ref,
        material_digest=manifest.digest,
        completed_at=str(context.get("generated_at_utc") or ""),
        unresolved_actionables=unresolved_actionables,
        report_content_digest=self_review_report_content_digest(report),
    )
    return receipt


def build_report(
    context: dict[str, Any],
    *,
    packet_id: str = "",
    packet_path: str = "",
) -> dict[str, Any]:
    findings = build_findings(context)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": str(context.get("generated_at_utc") or "unknown"),
        "mode": "dry-run-report",
        "coordinator_packet": {
            "task_packet_id": packet_id,
            "path": packet_path,
            "role_order": DEFAULT_ROLE_ORDER,
        },
        "scope_reviewed": _build_scope(context),
        "review_source_status": _as_list(context.get("review_source_status")),
        "findings_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "calibration": _build_calibration(context, findings),
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
    report["self_review_receipt"] = _build_self_review_receipt(context, findings, report)
    return report


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
    lines.extend(["", "## Review Source Status"])
    source_status = report.get("review_source_status") or []
    if source_status:
        for source in source_status:
            if not isinstance(source, dict):
                continue
            lines.append(
                "- "
                f"`{_format_value(source.get('source'))}`: "
                f"`{_format_value(source.get('status'))}`; "
                f"source-degraded `{str(bool(source.get('source_degraded'))).lower()}`; "
                f"fallback-required `{str(bool(source.get('fallback_required'))).lower()}`; "
                f"blocking `{str(bool(source.get('blocking'))).lower()}`"
            )
            reason = _format_value(source.get("reason"))
            if reason:
                lines.append(f"  - Reason: {reason}")
    else:
        lines.append("- No review-source status supplied.")
    lines.extend(["", "## Calibration"])
    calibration = report["calibration"]
    lines.append(f"- Rubric version: `{calibration['rubric_version']}`")
    labels = calibration.get("case_labels") or []
    if labels:
        lines.append("- Case labels: " + ", ".join(f"`{label}`" for label in labels))
    else:
        lines.append("- Case labels: none")
    lines.append(f"- GitHub posting eligible: `{str(calibration['posting_eligible']).lower()}`")
    lines.append(f"- Posting gate: {calibration['posting_gate']}")
    controls = calibration.get("false_positive_controls") or []
    lines.append("- False-positive controls:")
    if controls:
        lines.extend(f"  - {control}" for control in controls)
    else:
        lines.append("  - none")
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

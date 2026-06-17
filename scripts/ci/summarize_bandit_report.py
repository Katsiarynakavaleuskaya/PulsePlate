#!/usr/bin/env python3
"""Summarize Bandit JSON output and enforce the HIGH-severity gate."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, NamedTuple, Sequence

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNDEFINED": 3, "UNKNOWN": 4}


class BanditReportError(ValueError):
    """Raised when a Bandit report is missing or malformed."""


class GroupKey(NamedTuple):
    severity: str
    confidence: str
    test_id: str
    path_bucket: str


class Finding(NamedTuple):
    severity: str
    confidence: str
    test_id: str
    filename: str
    line_number: int
    issue_text: str
    path_bucket: str


def _github_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _display_escape(value: str) -> str:
    return _github_escape(value)


def _annotation(kind: str, message: str) -> str:
    return f"::{kind}::{_github_escape(message)}"


def _normalize_label(value: object, *, fallback: str = "UNKNOWN") -> str:
    if not isinstance(value, str):
        return fallback
    normalized = value.strip().upper()
    return normalized or fallback


def _line_number(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _path_bucket(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized == "legacy_app.py":
        return "legacy_app"
    if normalized.startswith("app/security/"):
        return "app/security"
    if normalized.startswith("app/"):
        return "app"
    if normalized.startswith("scripts/ci/"):
        return "scripts/ci"
    if normalized.startswith("scripts/"):
        return "scripts"
    if normalized.startswith("core/"):
        return "core"
    if normalized.startswith("providers/"):
        return "providers"
    if normalized.startswith("tests/") or normalized == "tests":
        return "tests"
    if normalized.startswith(".github/workflows/"):
        return "github/workflows"
    if normalized.startswith("docs/"):
        return "docs"
    return "other"


def _load_report(path: Path) -> list[Mapping[str, Any]]:
    if not path.is_file():
        raise BanditReportError(f"Bandit report not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BanditReportError(f"Bandit report is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BanditReportError("Bandit report root must be a JSON object")
    results = payload.get("results")
    if not isinstance(results, list):
        raise BanditReportError("Bandit report `.results` must be a list")
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            raise BanditReportError(f"Bandit report `.results[{index}]` must be an object")
    return results


def _finding(item: Mapping[str, Any]) -> Finding:
    filename = str(item.get("filename") or "<unknown>")
    return Finding(
        severity=_normalize_label(item.get("issue_severity"), fallback="UNKNOWN"),
        confidence=_normalize_label(item.get("issue_confidence"), fallback="UNKNOWN"),
        test_id=str(item.get("test_id") or "UNKNOWN").strip() or "UNKNOWN",
        filename=filename,
        line_number=_line_number(item.get("line_number")),
        issue_text=str(item.get("issue_text") or "").strip(),
        path_bucket=_path_bucket(filename),
    )


def _severity_sort_key(severity: str) -> tuple[int, str]:
    return (SEVERITY_ORDER.get(severity, 99), severity)


def _finding_sort_key(finding: Finding) -> tuple[tuple[int, str], str, str, str, int, str]:
    return (
        _severity_sort_key(finding.severity),
        finding.test_id,
        finding.path_bucket,
        finding.filename,
        finding.line_number,
        finding.issue_text,
    )


def _group_sort_key(
    item: tuple[GroupKey, Sequence[Finding]],
) -> tuple[int, tuple[int, str], str, str, str]:
    key, findings = item
    return (
        -len(findings),
        _severity_sort_key(key.severity),
        key.test_id,
        key.confidence,
        key.path_bucket,
    )


def _maybe_display_escape(value: str, *, escape_display: bool) -> str:
    return _display_escape(value) if escape_display else value


def _format_location(finding: Finding, *, escape_display: bool = True) -> str:
    suffix = f":{finding.line_number}" if finding.line_number else ""
    return f"{_maybe_display_escape(finding.filename, escape_display=escape_display)}{suffix}"


def _summary_lines(
    findings: Sequence[Finding], *, top: int, samples: int, escape_display: bool = True
) -> list[str]:
    lower_findings = [finding for finding in findings if finding.severity != "HIGH"]
    if not lower_findings:
        return []

    grouped: dict[GroupKey, list[Finding]] = defaultdict(list)
    for finding in lower_findings:
        grouped[
            GroupKey(
                finding.severity,
                finding.confidence,
                finding.test_id,
                finding.path_bucket,
            )
        ].append(finding)

    lines = ["Bandit lower-severity grouped inventory:"]
    for key, grouped_findings in sorted(grouped.items(), key=_group_sort_key)[:top]:
        sorted_findings = sorted(grouped_findings, key=_finding_sort_key)
        examples = ", ".join(
            _format_location(finding, escape_display=escape_display)
            for finding in sorted_findings[:samples]
        )
        lines.append(
            "- "
            f"{_maybe_display_escape(key.severity, escape_display=escape_display)} | "
            f"{_maybe_display_escape(key.confidence, escape_display=escape_display)} confidence | "
            f"{_maybe_display_escape(key.test_id, escape_display=escape_display)} | "
            f"{_maybe_display_escape(key.path_bucket, escape_display=escape_display)}: "
            f"{len(sorted_findings)}"
            f" (examples: {examples})"
        )
    return lines


def _severity_counts(findings: Iterable[Finding]) -> Counter[str]:
    return Counter(finding.severity for finding in findings)


def _print_analysis(
    findings: Sequence[Finding],
    *,
    github_annotations: bool,
    top: int,
    samples: int,
) -> None:
    counts = _severity_counts(findings)
    high_count = counts.get("HIGH", 0)
    below_high_count = len(findings) - high_count

    print("=== Bandit Report Analysis ===")
    print(f"Total findings: {len(findings)}")
    print(f"HIGH severity findings: {high_count}")

    if high_count:
        message = (
            f"Bandit found {high_count} HIGH severity "
            f"{'issue' if high_count == 1 else 'issues'} that must be addressed"
        )
        print(_annotation("error", message) if github_annotations else f"ERROR: {message}")
        print("HIGH severity samples:")
        for finding in sorted(
            (finding for finding in findings if finding.severity == "HIGH"),
            key=_finding_sort_key,
        )[:samples]:
            print(
                "- "
                f"{_display_escape(finding.test_id)} | "
                f"{_display_escape(finding.confidence)} confidence | "
                f"{_format_location(finding)} | {_display_escape(finding.issue_text)}"
            )

    if below_high_count:
        display_group_lines = _summary_lines(findings, top=top, samples=samples)
        annotation_group_lines = _summary_lines(
            findings,
            top=top,
            samples=samples,
            escape_display=False,
        )
        warning_summary = "; ".join(line.removeprefix("- ") for line in annotation_group_lines[1:4])
        message = f"Bandit reported {below_high_count} findings below HIGH severity" + (
            f": {warning_summary}" if warning_summary else ""
        )
        print(_annotation("warning", message) if github_annotations else f"WARNING: {message}")
        for line in display_group_lines:
            print(line)
    elif not high_count:
        print("No HIGH severity issues found in Bandit report")


def summarize_report(
    report: Path,
    *,
    fail_on_high: bool,
    github_annotations: bool,
    top: int,
    samples: int,
) -> int:
    try:
        findings = [_finding(item) for item in _load_report(report)]
    except BanditReportError as exc:
        message = str(exc)
        print(_annotation("error", message) if github_annotations else f"ERROR: {message}")
        return 2

    _print_analysis(
        findings,
        github_annotations=github_annotations,
        top=top,
        samples=samples,
    )
    if fail_on_high and any(finding.severity == "HIGH" for finding in findings):
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path, help="Bandit JSON report path.")
    parser.add_argument(
        "--fail-on-high",
        action="store_true",
        help="Exit 1 when HIGH severity findings are present.",
    )
    parser.add_argument(
        "--github-annotations",
        action="store_true",
        help="Emit GitHub Actions ::warning::/::error:: command annotations.",
    )
    parser.add_argument("--top", type=int, default=10, help="Maximum grouped rows to print.")
    parser.add_argument("--samples", type=int, default=3, help="Sample locations per group.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return summarize_report(
        args.report,
        fail_on_high=args.fail_on_high,
        github_annotations=args.github_annotations,
        top=args.top,
        samples=args.samples,
    )


if __name__ == "__main__":
    sys.exit(main())

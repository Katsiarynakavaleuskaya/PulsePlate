#!/usr/bin/env python3
"""Deterministic guard for the PR #1789 alignment-rule ledger closeout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
DEFAULT_PRECONDITION_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
)

ALIGNMENT_LEDGER_ANCHOR = '<a id="ledger-p1-philosophy-epic-v2-alignment-rule-trust-schema"></a>'
ALIGNMENT_LEDGER_TITLE = "- [x] P1: Philosophy Epic V2 alignment-rule trust schema"
PR1789_MERGE_COMMIT = "".join(("651c56bb", "510125b4", "df011a6d", "48de6f82", "a8f6e0b7"))
PR1789_MERGED_AT = "2026-05-21T22:14:53Z"
PR1811_MERGE_COMMIT = "".join(("0b324f51", "6b5ba33d", "fc5e65d0", "68cd5aac", "a742b5f8"))
PR1811_MERGED_AT = "2026-05-24T09:39:30Z"

ROADMAP_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

REPORT_FALSE_FLAGS = (
    "gate_open_allowed",
    "runtime_handoff_allowed",
    "cache_read_allowed",
    "cache_write_allowed",
    "serving_allowed",
)


def _roadmap_markers(roadmap_text: str) -> tuple[dict[str, str], list[str]]:
    markers: dict[str, str] = {}
    errors: list[str] = []
    for match in re.finditer(r"<!--\s*([A-Z0-9_]+):\s*([^>]+?)\s*-->", roadmap_text):
        key = match.group(1)
        if key in markers:
            errors.append(f"semantic-cache roadmap marker {key} is duplicated")
            continue
        markers[key] = match.group(2).strip()
    return markers, errors


def _alignment_ledger_block(ledger_text: str) -> tuple[str, list[str]]:
    start = ledger_text.find(ALIGNMENT_LEDGER_ANCHOR)
    if start == -1:
        return "", ["alignment-rule trust schema ledger anchor missing"]

    tail = ledger_text[start + len(ALIGNMENT_LEDGER_ANCHOR) :]
    next_anchor = re.search(r"\n<a id=\"ledger-", tail)
    end = start + len(ALIGNMENT_LEDGER_ANCHOR) + (next_anchor.start() if next_anchor else len(tail))
    return ledger_text[start:end], []


def _validate_alignment_ledger_block(block: str) -> list[str]:
    errors: list[str] = []
    required_snippets = (
        ALIGNMENT_LEDGER_TITLE,
        "Target PR: PR #1789 (`codex/philosophy-alignment-rule-trust-schema`)",
        "Status: Completed.",
        "PR #1789 merged",
        PR1789_MERGE_COMMIT,
        PR1789_MERGED_AT,
        "PR #1811 / PR-4.1",
        PR1811_MERGE_COMMIT,
        PR1811_MERGED_AT,
        "PR-4.2 closes this separate alignment-rule ledger row only",
        "Semantic-cache runtime handoff remains blocked",
        "all gate markers stay closed/false",
        "PR-A1b through PR-A5 plus a later reviewed gate-open PR remain required",
    )
    for snippet in required_snippets:
        if snippet not in block:
            errors.append(f"alignment ledger closeout missing evidence: {snippet}")

    forbidden_snippets = (
        "- [ ] P1: Philosophy Epic V2 alignment-rule trust schema",
        "Active branch",
        "\U0001f7e1",
    )
    for snippet in forbidden_snippets:
        if snippet in block:
            errors.append(f"alignment ledger closeout still contains stale marker: {snippet}")
    return errors


def _validate_roadmap_markers(roadmap_text: str) -> list[str]:
    markers, errors = _roadmap_markers(roadmap_text)
    for key, expected in ROADMAP_MARKERS.items():
        observed = markers.get(key)
        if observed != expected:
            errors.append(
                f"semantic-cache roadmap marker {key}: expected {expected!r}, got {observed!r}"
            )
    return errors


def _json_object(text: str) -> tuple[dict[str, object], list[str]]:
    def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        seen: set[str] = set()
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in seen:
                raise ValueError(f"gate-open precondition report duplicate key: {key}")
            seen.add(key)
            result[key] = value
        return result

    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        return {}, [f"gate-open precondition report invalid JSON: {exc}"]
    except ValueError as exc:
        return {}, [str(exc)]
    if not isinstance(payload, dict):
        return {}, ["gate-open precondition report must be a JSON object"]
    return payload, []


def _validate_precondition_report(report_text: str) -> list[str]:
    report, errors = _json_object(report_text)
    if errors:
        return errors

    for flag in REPORT_FALSE_FLAGS:
        if report.get(flag) is not False:
            errors.append(f"gate-open precondition report must keep {flag}=false")

    decision = report.get("handoff_decision")
    if not isinstance(decision, dict):
        errors.append("gate-open precondition report missing handoff_decision object")
    else:
        if decision.get("decision") != "gate_open_blocked_preconditions_incomplete":
            errors.append("gate-open precondition report decision must remain blocked")
        for flag in REPORT_FALSE_FLAGS[1:]:
            if decision.get(flag) is not False:
                errors.append("gate-open precondition handoff_decision must keep " f"{flag}=false")

    return errors


def validate_philosophy_alignment_ledger_closeout(
    *,
    ledger_text: str,
    roadmap_text: str,
    precondition_report_text: str,
) -> list[str]:
    """Validate that PR #1789 is closed in the ledger without opening the gate."""
    errors: list[str] = []
    block, block_errors = _alignment_ledger_block(ledger_text)
    errors.extend(block_errors)
    if block:
        errors.extend(_validate_alignment_ledger_block(block))
    errors.extend(_validate_roadmap_markers(roadmap_text))
    errors.extend(_validate_precondition_report(precondition_report_text))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Philosophy PR #1789 alignment-rule ledger closeout determinism."
    )
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument(
        "--precondition-report",
        type=Path,
        default=DEFAULT_PRECONDITION_REPORT,
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    for path, label in (
        (args.ledger, "backlog ledger"),
        (args.roadmap, "semantic-cache roadmap"),
        (args.precondition_report, "philosophy gate-open precondition report"),
    ):
        if not path.exists():
            print(f"ERROR: {label} missing: {path}", file=sys.stderr)
            return 1

    errors = validate_philosophy_alignment_ledger_closeout(
        ledger_text=args.ledger.read_text(encoding="utf-8"),
        roadmap_text=args.roadmap.read_text(encoding="utf-8"),
        precondition_report_text=args.precondition_report.read_text(encoding="utf-8"),
    )
    if errors:
        print("ERROR: philosophy alignment-ledger closeout validation failed:", file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("philosophy alignment ledger closeout passed: PR #1789 closed, gate remains closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

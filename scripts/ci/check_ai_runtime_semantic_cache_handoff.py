#!/usr/bin/env python3
"""Fail-closed guard for the semantic-cache runtime prerequisite handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_RAG_ROADMAP = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
)
DEFAULT_SEMANTIC_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)
DEFAULT_PRECONDITIONS_REPORT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json"
)
DEFAULT_PRECONDITIONS_CHECKER = (
    REPO_ROOT / "scripts" / "ci" / "check_philosophy_gate_open_preconditions.py"
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

A4_EVIDENCE = (
    "PR #1203",
    "feat(ai): extract bounded AI runtime ownership into canonical core/ai seam",
    "2026-03-21T06:01:31Z",
    "831d62d8be0da7307e5a0f2673d8c33dbf53ca49",  # pragma: allowlist secret
    "feat/ai-bounded-context-extraction",
)
A4_GATE_EVIDENCE = tuple(token for token in A4_EVIDENCE if not token.startswith("feat(ai):"))
A5_EVIDENCE = (
    "PR #1395",
    "feat(ai): add PR-A5 runtime gates",
    "2026-04-12T11:45:35Z",
    "2f8a9af461cec483aa81a774cce7496c6bf65a8a",  # pragma: allowlist secret
    "feat/pr-a5-runtime-gates",
)
A5_GATE_EVIDENCE = tuple(token for token in A5_EVIDENCE if not token.startswith("feat(ai):"))
SC_G5_EVIDENCE = (
    "PR #1742",
    "feat(ai-runtime): add semantic-cache backend selection contract",
    "2026-05-16T21:03:48Z",
    "cb1db8b40141817b3ca856de570b8fc02e2ae9fa",  # pragma: allowlist secret
)

RUNTIME_PRECONDITION_IDS = (
    "pr_a1b_reconciled",
    "pr_a2_rag_hardening_closed",
    "pr_a3_bounded_context_packet_closed",
    "pr_a4_bounded_context_extraction_closed",
    "pr_a5_llm_reliability_security_closed",
)

MARKER_RE = re.compile(r"<!--\s*(SEMANTIC_CACHE_[A-Z_]+):\s*(.*?)\s*-->")
LEDGER_ANCHOR_RE = re.compile(r'<a id="(?P<anchor>[^"]+)"></a>')
ROADMAP_HEADING_RE = re.compile(r"^##\s+(?P<heading>PR-[A-Z0-9]+)\b", re.M)

STALE_ACTIVE_PATTERNS = (
    (
        "A4/A5 still required",
        re.compile(r"runtime sequence still requires PR-A4 through PR-A5", re.I),
    ),
    (
        "A4 still open",
        re.compile(r"PR-A4[^.\n]{0,180}\b(?:remains|is)\b[^.\n]{0,80}\bopen\b", re.I),
    ),
    ("A5 planned", re.compile(r"PR-A5[^.\n]{0,180}\bplanned\b", re.I)),
    ("A5 TBD target", re.compile(r"PR-TBD-LLM-CI-GATES", re.I)),
    ("A5 missing gate bundle", re.compile(r"no canonical CI gate bundle", re.I)),
)

FORBIDDEN_SCOPE_PATTERNS = (
    (
        "semantic cache prerequisites satisfied",
        re.compile(r"\bsemantic\s+cache\s+prerequisites\s+(?:are\s+)?satisfied\b", re.I),
    ),
    (
        "semantic cache live",
        re.compile(
            r"\bsemantic[-\s]cache\s+(?:is\s+)?(?:active|live|enabled|open|implemented)\b", re.I
        ),
    ),
    (
        "SC0 opens semantic cache",
        re.compile(
            r"\bPR[-\s]?SC0\b[^.\n]{0,160}\b(?:opens|enables|activates|approves)\b[^.\n]{0,80}\bsemantic[-\s]cache\b",
            re.I,
        ),
    ),
    (
        "Redis approved",
        re.compile(
            r"\bredis\s+(?:is\s+)?(?:approved|enabled|active|live|production-ready)\b", re.I
        ),
    ),
    (
        "GPTCache approved",
        re.compile(
            r"\bgpt[-\s]?cache\s+(?:is\s+)?(?:approved|enabled|active|live|production-ready)\b",
            re.I,
        ),
    ),
    (
        "GraphRAG approved",
        re.compile(
            r"\bgraph[-\s]?rag\s+(?:rollout\s+)?(?:is\s+)?(?:approved|enabled|active|live)\b", re.I
        ),
    ),
    (
        "ContextManifest approved",
        re.compile(
            r"\bcontext[-\s]?manifest\s+(?:rollout\s+)?(?:is\s+)?(?:approved|enabled|active|live)\b",
            re.I,
        ),
    ),
    (
        "default activation",
        re.compile(r"\bdefault\s+activation\s+(?:is\s+)?(?:enabled|active|on)\b", re.I),
    ),
)

SAFE_NEGATION_RE = re.compile(
    r"\b("
    r"no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|without|"
    r"blocked|out\s+of\s+scope|remains?\s+closed|remain\s+closed|stay(?:s)?\s+closed|"
    r"until\s+a\s+later\s+reviewed\s+gate[-\s]?open\s+PR|"
    r"must\s+still\s+change|candidate\s+labels"
    r")\b",
    re.I,
)

MAPPING_FIX_SHA_DENYLIST = (
    "1377cd91",
    "dfbeae5d",
    "8d5f7e7bb",
)


def _display(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return "<external-path>"


def _read(path: Path, repo_root: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_display(path, repo_root)}: unable to read: {type(exc).__name__}")
        return ""


def _collapsed(text: str) -> str:
    return " ".join(text.split())


def _require_tokens(label: str, text: str, tokens: tuple[str, ...], errors: list[str]) -> None:
    collapsed = _collapsed(text)
    for token in tokens:
        if _collapsed(token) not in collapsed:
            errors.append(f"{label}: missing required evidence token: {token}")


def _ledger_section(text: str, anchor: str) -> str:
    matches = list(LEDGER_ANCHOR_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group("anchor") == anchor:
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            return text[start:end]
    return ""


def _roadmap_section(text: str, heading: str) -> str:
    matches = list(ROADMAP_HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group("heading") == heading:
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            return text[start:end]
    return ""


def _gate_markers(text: str) -> dict[str, list[str]]:
    markers: dict[str, list[str]] = {}
    for match in MARKER_RE.finditer(text):
        markers.setdefault(match.group(1), []).append(match.group(2).strip())
    return markers


def _check_gate_markers(text: str, errors: list[str]) -> None:
    markers = _gate_markers(text)
    for marker, expected in REQUIRED_GATE_MARKERS.items():
        values = markers.get(marker)
        if not values:
            errors.append(f"semantic-cache gate: missing marker {marker}")
            continue
        if len(values) > 1:
            errors.append(f"semantic-cache gate: duplicate marker {marker}")
            continue
        if values[0] != expected:
            errors.append(f"semantic-cache gate: expected {marker}={expected}, got {values[0]}")


def _unsafe_sentences(text: str) -> list[str]:
    return [
        sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+|\n", text) if sentence.strip()
    ]


def _check_forbidden_scope(label: str, text: str, errors: list[str]) -> None:
    for sentence in _unsafe_sentences(text):
        for pattern_label, pattern in FORBIDDEN_SCOPE_PATTERNS:
            if not pattern.search(sentence):
                continue
            if SAFE_NEGATION_RE.search(sentence):
                continue
            errors.append(f"{label}: forbidden runtime/scope expansion claim: {pattern_label}")


def _load_report(text: str, errors: list[str]) -> dict[str, object]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"preconditions report: invalid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append("preconditions report: root must be an object")
        return {}
    return value


def _check_preconditions_report(report: dict[str, object], errors: list[str]) -> None:
    for flag in (
        "gate_open_allowed",
        "runtime_handoff_allowed",
        "cache_read_allowed",
        "cache_write_allowed",
        "serving_allowed",
    ):
        if report.get(flag) is not False:
            errors.append(f"preconditions report: {flag} must remain false")
    if report.get("report_version") != "2026-05-25":
        errors.append("preconditions report: report_version must be 2026-05-25")
    if report.get("rollout_phase") != "PHILOSOPHY-PR4-SC0-RECONCILED":
        errors.append("preconditions report: rollout_phase must record SC0 reconciliation")

    preconditions = report.get("preconditions")
    if not isinstance(preconditions, list):
        errors.append("preconditions report: preconditions must be an array")
        return
    by_id = {item.get("id"): item for item in preconditions if isinstance(item, dict)}
    for precondition_id in RUNTIME_PRECONDITION_IDS:
        item = by_id.get(precondition_id)
        if not isinstance(item, dict):
            errors.append(f"preconditions report: missing {precondition_id}")
            continue
        if item.get("status") != "merge_verified_closed":
            errors.append(f"preconditions report: {precondition_id} must be merge_verified_closed")
        if item.get("blocks_gate_open") is not False:
            errors.append(f"preconditions report: {precondition_id} must not block gate-open")

    handoff = report.get("handoff_decision")
    if not isinstance(handoff, dict):
        errors.append("preconditions report: handoff_decision must be an object")
        return
    reason_codes = handoff.get("reason_codes")
    if not isinstance(reason_codes, list) or not all(
        isinstance(item, str) for item in reason_codes
    ):
        errors.append("preconditions report: reason_codes must be a string array")
        return
    if "runtime_prerequisites_not_verified" in reason_codes:
        errors.append("preconditions report: runtime prerequisites must no longer be unverified")
    required_codes = {
        "semantic_cache_gate_closed",
        "dedicated_gate_open_pr_absent",
        "alignment_rule_schema_predecessor_pending",
    }
    if set(reason_codes) != required_codes:
        errors.append("preconditions report: reason_codes mismatch for SC0 handoff")
    if handoff.get("blocking_precondition_count") != 2:
        errors.append("preconditions report: blocking_precondition_count must remain 2")
    for flag in (
        "runtime_handoff_allowed",
        "cache_read_allowed",
        "cache_write_allowed",
        "serving_allowed",
    ):
        if handoff.get(flag) is not False:
            errors.append(f"preconditions report: handoff_decision.{flag} must remain false")


def validate_handoff(
    *,
    repo_root: Path,
    ledger: Path,
    rag_roadmap: Path,
    semantic_gate: Path,
    preconditions_report: Path,
    preconditions_checker: Path,
) -> list[str]:
    errors: list[str] = []
    ledger_text = _read(ledger, repo_root, errors)
    rag_text = _read(rag_roadmap, repo_root, errors)
    gate_text = _read(semantic_gate, repo_root, errors)
    report_text = _read(preconditions_report, repo_root, errors)
    checker_text = _read(preconditions_checker, repo_root, errors)

    a4_ledger = _ledger_section(ledger_text, "ledger-p1-ai-bounded-context-extraction")
    a5_ledger = _ledger_section(ledger_text, "ledger-p1-llm-reliability-security-gates")
    a4_roadmap = _roadmap_section(rag_text, "PR-A4")
    a5_roadmap = _roadmap_section(rag_text, "PR-A5")
    if not a4_ledger:
        errors.append("ledger: missing A4 bounded-context extraction anchor")
    if not a5_ledger:
        errors.append("ledger: missing A5 reliability/security gates anchor")
    if not a4_roadmap:
        errors.append("RAG roadmap: missing PR-A4 section")
    if not a5_roadmap:
        errors.append("RAG roadmap: missing PR-A5 section")

    for label, text in (
        ("A4 ledger", a4_ledger),
        ("A4 roadmap", a4_roadmap),
        ("preconditions report", report_text),
    ):
        _require_tokens(label, text, A4_EVIDENCE, errors)
    _require_tokens("semantic-cache gate", gate_text, A4_GATE_EVIDENCE, errors)
    for label, text in (
        ("A5 ledger", a5_ledger),
        ("A5 roadmap", a5_roadmap),
        ("preconditions report", report_text),
    ):
        _require_tokens(label, text, A5_EVIDENCE, errors)
    _require_tokens("semantic-cache gate", gate_text, A5_GATE_EVIDENCE, errors)
    _require_tokens("semantic-cache gate SC-G5 evidence", gate_text, SC_G5_EVIDENCE, errors)

    if "- [x] P1: Extract AI runtime into a dedicated bounded context" not in a4_ledger:
        errors.append("A4 ledger: checkbox must be closed")
    if "- [x] P1: LLM reliability and security CI gates" not in a5_ledger:
        errors.append("A5 ledger: checkbox must be closed")
    if "runtime prerequisite train is closed" not in _collapsed(gate_text).lower():
        errors.append("semantic-cache gate: missing safe handoff phrase")
    if "runtime prerequisite train is closed" not in _collapsed(rag_text).lower():
        errors.append("RAG roadmap: missing safe handoff phrase")

    active_text = "\n".join((a4_ledger, a5_ledger, a4_roadmap, a5_roadmap, gate_text, report_text))
    for label, pattern in STALE_ACTIVE_PATTERNS:
        match = pattern.search(active_text)
        if match:
            errors.append(f"active docs: stale wording remains ({label}): {match.group(0)[:160]}")
    for denied_sha in MAPPING_FIX_SHA_DENYLIST:
        if denied_sha in active_text:
            errors.append(
                f"active docs: review-fix SHA must not be used as merge proof: {denied_sha}"
            )
    _check_forbidden_scope("active handoff docs", active_text, errors)
    _check_gate_markers(gate_text, errors)
    _check_preconditions_report(_load_report(report_text, errors), errors)
    for token in ("merge_verified_closed", "PHILOSOPHY-PR4-SC0-RECONCILED"):
        if token not in checker_text:
            errors.append(f"preconditions checker: missing token {token}")
    return errors


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--rag-roadmap", type=Path, default=DEFAULT_RAG_ROADMAP)
    parser.add_argument("--semantic-gate", type=Path, default=DEFAULT_SEMANTIC_GATE)
    parser.add_argument("--preconditions-report", type=Path, default=DEFAULT_PRECONDITIONS_REPORT)
    parser.add_argument("--preconditions-checker", type=Path, default=DEFAULT_PRECONDITIONS_CHECKER)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    errors = validate_handoff(
        repo_root=args.repo_root,
        ledger=args.ledger,
        rag_roadmap=args.rag_roadmap,
        semantic_gate=args.semantic_gate,
        preconditions_report=args.preconditions_report,
        preconditions_checker=args.preconditions_checker,
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("semantic-cache runtime prerequisite handoff guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

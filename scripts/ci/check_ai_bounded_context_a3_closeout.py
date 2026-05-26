#!/usr/bin/env python3
"""Fail-closed guard for PR-A3 bounded-context packet closeout truth."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PR_NUMBER = "1469"
TITLE = "docs(architecture): define AI bounded-context packet and ownership map"
MERGED_AT = "2026-04-19T11:35:29Z"
MERGE_COMMIT = "f8454715f88e44657cfad1c4675f93ea669dc490"  # pragma: allowlist secret
ORIGINAL_BRANCH = "codex/ai-bounded-context-packet"
MAPPING_FIX_COMMIT = "52bdcccd1"

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
DEFAULT_SEMANTIC_CACHE_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)
DEFAULT_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1469_FIXED_MAPPING.md"
DEFAULT_A3_PACKET = (
    REPO_ROOT / "docs" / "orchestration" / "WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md"
)
DEFAULT_C4_PACKET = (
    REPO_ROOT / "docs" / "architecture" / "C4_AI_BOUNDED_CONTEXT_PACKET_2026-03-20.md"
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

UNICODE_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
        "\u2007": " ",
        "\u202f": " ",
    }
)

MARKER_RE = re.compile(r"<!--\s*(SEMANTIC_CACHE_[A-Z_]+):\s*(.*?)\s*-->")
LEDGER_ANCHOR_RE = re.compile(r'<a id="(?P<anchor>[^"]+)"></a>')
ROADMAP_HEADING_RE = re.compile(r"^##\s+(?P<heading>PR-[A-Z0-9]+)\b", re.M)
MAPPING_STALE_HEADING_RE = re.compile(r"^##\s+Merge Readiness\s*$", re.M)
LOCAL_PATH_RE = re.compile(
    r"(/Users/|[A-Za-z]:\\Users\\|(?:^|[^\w/])worktrees/|(?:^|[^\w/])Worktrees/|"
    r"\\worktrees\\|artifacts/orchestration|artifacts\\orchestration)",
    re.I,
)

STALE_A3_RE = re.compile(
    r"\b(?:PR[-\s]?A3|A3|PR\s*#?\s*1469|#1469)\b.{0,160}\b("
    r"planned|pending|in[-\s]+progress|active\s+(?:implementation|runtime|lane)|"
    r"next\s+runtime|missing\s+packet|still\s+requires\s+PR[-\s]?A3|"
    r"requires\s+PR[-\s]?A3\s+through\s+PR[-\s]?A5|remains\s+required"
    r")\b",
    re.I | re.S,
)
STALE_A3_REVERSED_RE = re.compile(
    r"\b("
    r"planned|pending|in[-\s]+progress|active\s+(?:implementation|runtime|lane)|"
    r"next\s+runtime|missing\s+packet|still\s+requires\s+PR[-\s]?A3|"
    r"requires\s+PR[-\s]?A3\s+through\s+PR[-\s]?A5|remains\s+required"
    r")\b.{0,160}\b(?:PR[-\s]?A3|A3|PR\s*#?\s*1469|#1469)\b",
    re.I | re.S,
)
A4_CLOSE_RE = re.compile(
    r"\b(?:PR[-\s]?A3|A3|PR\s*#?\s*1469|#1469)\b.{0,180}\b("
    r"closes?|closed|satisfies|satisfied|completes?|completed|retires?|retired"
    r")\b.{0,180}\b(?:PR[-\s]?A4|ledger-p1-ai-bounded-context-extraction|extraction)\b",
    re.I | re.S,
)
A4_CLOSE_REVERSED_RE = re.compile(
    r"\b(?:PR[-\s]?A4|ledger-p1-ai-bounded-context-extraction|extraction)\b.{0,180}\b("
    r"closes?|closed|satisfies|satisfied|completes?|completed|retires?|retired"
    r")\b.{0,180}\b(?:PR[-\s]?A3|A3|PR\s*#?\s*1469|#1469)\b",
    re.I | re.S,
)

FORBIDDEN_SURFACE_RE = re.compile(
    r"\b("
    r"semantic[-\s]?cache|redis|gpt[-\s]?cache|graph[-\s]?rag|"
    r"context[-\s]?manifest|contextmanifest|"
    r"(?:db|database)\s+persistence|public\s+(?:routes?|endpoints?|api)|"
    r"openapi|dtos?|provider\s+(?:rewiring|integration|code|runtime|ownership)|"
    r"runtime\s+(?:code|ownership|activation)|product\s+code|"
    r"default\s+activation|default[-\s]?on"
    r")\b",
    re.I,
)
POSITIVE_ACTION_RE = re.compile(
    r"\b("
    r"opens|opened|opening|enables?|enabled|enabling|approves?|approved|"
    r"authorizes?|authorized|permits?|permitted|allows?|allowed|"
    r"activates?|activated|activating|rolls?\s+out|rollout[-\s]?ready|"
    r"production[-\s]?ready|wires?|wired|rewires?|rewired|moves?|moved|"
    r"extracts?|extracted|implements?|implemented|adds?|added|updates?|updated|"
    r"changes?|changed"
    r")\b",
    re.I,
)
ACTIVATION_STATE_RE = re.compile(
    r"\b("
    r"semantic[-\s]?cache|redis|gpt[-\s]?cache|graph[-\s]?rag|"
    r"context[-\s]?manifest|contextmanifest|"
    r"(?:db|database)\s+persistence|public\s+(?:routes?|endpoints?|api)|"
    r"openapi|dtos?|provider\s+(?:rewiring|integration|code|runtime|ownership)|"
    r"runtime\s+(?:code|ownership|activation)|product\s+code|"
    r"default\s+activation|default[-\s]?on"
    r")\b"
    r".{0,80}\b(?:is|are|becomes?|became|now|as)\b"
    r".{0,80}\b(?:live|active|enabled|open|production[-\s]?ready|rollout[-\s]?ready|"
    r"default[-\s]?on|default\s+enabled)\b",
    re.I | re.S,
)
ACTIVATION_PREDICATE_RE = re.compile(
    r"\b(?:is|are|becomes?|became|now|as)\b"
    r".{0,80}\b(?:live|active|enabled|open|production[-\s]?ready|rollout[-\s]?ready|"
    r"default[-\s]?on|default\s+enabled)\b",
    re.I | re.S,
)
NEGATION_RE = re.compile(
    r"\b("
    r"no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|without|"
    r"out\s+of\s+scope|remains?\s+out\s+of\s+scope|stay(?:s)?\s+out\s+of\s+scope|"
    r"remains?\s+closed|stay(?:s)?\s+closed|gate[-\s]?closed|"
    r"until\s+a\s+reviewed\s+gate[-\s]?open\s+PR\s+changes|"
    r"reviewed\s+gate[-\s]?open\s+PR\s+must\s+still\s+change|"
    r"does\s+not\s+claim|is\s+not\s+claimed"
    r")\b",
    re.I,
)
SAFE_FORBIDDEN_NEGATION_RE = re.compile(
    r"\b("
    r"does\s+not\s+(?:open|enable|approve|authorize|permit|allow|activate|roll\s*out|wire|"
    r"rewire|move|extract|implement|add|update|change|claim)|"
    r"is\s+\*{0,2}not\*{0,2}\s+part|"
    r"\*{0,2}not\*{0,2}\s+part\s+of|"
    r"do\s+not\s+(?:open|enable|approve|authorize|permit|allow|activate|roll\s*out|wire|"
    r"rewire|move|extract|implement|add|update|change|claim)|"
    r"must\s+not\s+(?:open|enable|approve|authorize|permit|allow|activate|roll\s*out|wire|"
    r"rewire|move|extract|implement|add|update|change|claim)|"
    r"cannot\s+(?:open|enable|approve|authorize|permit|allow|activate|roll\s*out|wire|"
    r"rewire|move|extract|implement|add|update|change|claim)|"
    r"can't\s+(?:open|enable|approve|authorize|permit|allow|activate|roll\s*out|wire|"
    r"rewire|move|extract|implement|add|update|change|claim)|"
    r"blocked|out\s+of\s+scope|remains?\s+out\s+of\s+scope|stay(?:s)?\s+out\s+of\s+scope|"
    r"remains?\s+closed|stay(?:s)?\s+closed|gate[-\s]?closed|"
    r"(?:is|are)\s+closed\s+via\s+PR\s+#(?:1203|1395|1742)|"
    r"until\s+a\s+reviewed\s+gate[-\s]?open\s+PR\s+changes|"
    r"reviewed\s+gate[-\s]?open\s+PR\s+must\s+still\s+change|"
    r"does\s+not\s+claim|is\s+not\s+claimed"
    r")\b",
    re.I,
)
SAFE_A4_NEGATION_RE = re.compile(
    r"\b("
    r"does\s+not\s+(?:close|satisfy|complete|retire)|"
    r"do\s+not\s+(?:close|satisfy|complete|retire)|"
    r"must\s+not\s+(?:close|satisfy|complete|retire)|"
    r"cannot\s+(?:close|satisfy|complete|retire)|"
    r"can't\s+(?:close|satisfy|complete|retire)|"
    r"does\s+not\s+claim|is\s+not\s+claimed|"
    r"remains?\s+separate|stay(?:s)?\s+separate|remains?\s+open|stay(?:s)?\s+open|"
    r"out\s+of\s+scope|remains?\s+out\s+of\s+scope"
    r")\b",
    re.I,
)
SAFE_A4_FUTURE_GATE_RE = re.compile(
    r"`?PR[-\s]?A4`?\b.{0,180}\bclosed\s+(?:via|by)\s+PR\s+#1203\b|"
    r"`?PR[-\s]?A4`?\b.{0,180}\bclosed\s+via\s+.*ledger-p1-ai-bounded-context-extraction\b|"
    r"\bledger-p1-ai-bounded-context-extraction\b.{0,180}\bclosed\s+via\s+PR\s+#1203\b|"
    r"\bseparate\s+from\s+A3\b.{0,120}\bclosed\s+by\s+PR\s+#1203\b",
    re.I,
)
CLAUSE_SPLIT_RE = re.compile(
    r"([,;]|\b(?:but|however|yet|though|although|whereas|except|unless|therefore|"
    r"notwithstanding|nevertheless|and|also|plus)\b)",
    re.I,
)
CONTRAST_SEPARATOR_RE = re.compile(
    r";|\b(?:but|however|yet|though|although|whereas|except|unless|therefore|"
    r"notwithstanding|nevertheless)\b",
    re.I,
)
SERIAL_SAFE_NEGATION_RE = re.compile(
    r"\b("
    r"does\s+not|do\s+not|must\s+not|cannot|can't"
    r")\s+(?:open|enable|approve|authorize|permit|allow|activate|roll\s*out|wire|"
    r"rewire|move|extract|implement|add|update|change|claim)",
    re.I,
)
EXTRACTION_CLOSE_RE = re.compile(
    r"\b(closes?|closed|satisfies|satisfied|completes?|completed|retires?|retired)\b"
    r".{0,120}\b(PR[-\s]?A4|ledger-p1-ai-bounded-context-extraction|"
    r"extraction(?:\s+lane)?)\b"
    r"|"
    r"\b(PR[-\s]?A4|ledger-p1-ai-bounded-context-extraction|extraction\s+lane)\b"
    r".{0,120}\b(closes?|closed|satisfies|satisfied|completes?|completed|retires?|retired)\b",
    re.I | re.S,
)


def _display(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return "<external-path>"


def _read_text(path: Path, repo_root: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_display(path, repo_root)}: unable to read: {type(exc).__name__}")
        return ""


def _normalize(text: str) -> str:
    return text.translate(UNICODE_TRANSLATION)


def _require_tokens(label: str, text: str, tokens: tuple[str, ...], errors: list[str]) -> None:
    collapsed = " ".join(text.split())
    for token in tokens:
        if " ".join(token.split()) not in collapsed:
            errors.append(f"{label}: missing required evidence token: {token}")


def _section_after_anchor(text: str, anchor: str) -> str:
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


def _heading_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    next_match = re.search(r"^##\s+", text[match.end() :], re.M)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.start() : end]


def _check_local_path_leaks(label: str, text: str, errors: list[str]) -> None:
    match = LOCAL_PATH_RE.search(text)
    if match:
        errors.append(f"{label}: local path leakage: {match.group(0).strip()}")


def _check_gate_markers(text: str, errors: list[str]) -> None:
    values: dict[str, list[str]] = {}
    for match in MARKER_RE.finditer(text):
        values.setdefault(match.group(1), []).append(match.group(2).strip())
    for key, expected in REQUIRED_GATE_MARKERS.items():
        seen = values.get(key)
        if not seen:
            errors.append(f"semantic-cache gate: missing marker: {key}")
            continue
        if len(seen) > 1:
            errors.append(f"semantic-cache gate: duplicate marker: {key}")
            continue
        if seen[0] != expected:
            errors.append(f"semantic-cache gate: invalid marker {key}: {seen[0]}")


def _split_claims(text: str) -> list[str]:
    claims: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for clause in CLAUSE_SPLIT_RE.split(sentence):
            if not clause or CLAUSE_SPLIT_RE.fullmatch(clause):
                continue
            normalized = " ".join(clause.split())
            if normalized:
                claims.append(normalized)
    return claims


def _forbidden_claims_with_context(text: str) -> list[str]:
    claims: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        last_surface = ""
        serial_safe_negation = False
        parts = CLAUSE_SPLIT_RE.split(sentence)
        for index, clause in enumerate(parts):
            if index % 2 == 1:
                if CONTRAST_SEPARATOR_RE.search(clause):
                    serial_safe_negation = False
                continue
            normalized = " ".join(clause.split())
            if not normalized:
                continue
            current_serial_safe = serial_safe_negation
            surface_match = FORBIDDEN_SURFACE_RE.search(normalized)
            explicit_serial_safe = bool(SERIAL_SAFE_NEGATION_RE.search(normalized))
            if explicit_serial_safe:
                serial_safe_negation = True
            if current_serial_safe and (
                POSITIVE_ACTION_RE.search(normalized) or ACTIVATION_PREDICATE_RE.search(normalized)
            ):
                list_item = re.sub(r"^(?:or\s+)?", "", normalized, flags=re.I)
                normalized = f"does not {list_item}"
            if surface_match:
                last_surface = surface_match.group(0)
                claims.append(normalized)
                continue
            if last_surface and (
                POSITIVE_ACTION_RE.search(normalized) or ACTIVATION_PREDICATE_RE.search(normalized)
            ):
                claims.append(f"{last_surface} {normalized}")
                continue
            claims.append(normalized)
    return claims


def _check_forbidden_claims(label: str, text: str, errors: list[str]) -> None:
    for claim in _forbidden_claims_with_context(_normalize(text)):
        if not FORBIDDEN_SURFACE_RE.search(claim):
            continue
        has_activation_state = ACTIVATION_STATE_RE.search(claim)
        if has_activation_state:
            if SAFE_FORBIDDEN_NEGATION_RE.search(claim):
                continue
            errors.append(f"{label}: forbidden runtime/scope expansion claim: {claim[:180]}")
            continue
        if not POSITIVE_ACTION_RE.search(claim):
            continue
        if SAFE_FORBIDDEN_NEGATION_RE.search(claim):
            continue
        errors.append(f"{label}: forbidden runtime/scope expansion claim: {claim[:180]}")


def _check_a4_boundary(label: str, text: str, errors: list[str]) -> None:
    for claim_text in _split_claims(_normalize(text)):
        for pattern in (A4_CLOSE_RE, A4_CLOSE_REVERSED_RE):
            match = pattern.search(claim_text)
            if not match:
                continue
            claim = match.group(0)
            if SAFE_A4_FUTURE_GATE_RE.search(claim_text):
                continue
            if SAFE_A4_NEGATION_RE.search(claim):
                continue
            errors.append(f"{label}: A3 must not close A4/extraction: {claim[:180]}")
        extraction_match = EXTRACTION_CLOSE_RE.search(claim_text)
        if (
            extraction_match
            and not SAFE_A4_FUTURE_GATE_RE.search(claim_text)
            and not SAFE_A4_NEGATION_RE.search(claim_text)
        ):
            errors.append(
                f"{label}: A3 must not close A4/extraction: {extraction_match.group(0)[:180]}"
            )


def _a3_related_text(text: str) -> str:
    return "\n".join(
        unit.strip()
        for unit in re.split(r"(?<=[.!?])\s+|\n", text)
        if re.search(r"\b(?:PR[-\s]?A3|A3|PR\s*#?\s*1469|#1469)\b", unit, re.I)
    )


def _gate_closeout_claim_text(text: str) -> str:
    return "\n".join(
        unit.strip()
        for unit in re.split(r"\n\s*\n", text)
        if (
            re.search(r"\b(?:PR[-\s]?A3|A3|PR\s*#?\s*1469|#1469|closeout)\b", unit, re.I)
            or ACTIVATION_STATE_RE.search(_normalize(unit))
            or FORBIDDEN_SURFACE_RE.search(_normalize(unit))
            or EXTRACTION_CLOSE_RE.search(_normalize(unit))
        )
    )


def validate_closeout(
    *,
    repo_root: Path,
    ledger: Path,
    roadmap: Path,
    semantic_cache_gate: Path,
    mapping: Path,
    a3_packet: Path,
    c4_packet: Path,
) -> list[str]:
    errors: list[str] = []
    ledger_text = _normalize(_read_text(ledger, repo_root, errors))
    roadmap_text = _normalize(_read_text(roadmap, repo_root, errors))
    gate_text = _normalize(_read_text(semantic_cache_gate, repo_root, errors))
    mapping_text = _normalize(_read_text(mapping, repo_root, errors))
    a3_packet_text = _normalize(_read_text(a3_packet, repo_root, errors))
    c4_packet_text = _normalize(_read_text(c4_packet, repo_root, errors))

    a3_ledger = _section_after_anchor(ledger_text, "ledger-p1-ai-bounded-context-packet")
    extraction_ledger = _section_after_anchor(
        ledger_text, "ledger-p1-ai-bounded-context-extraction"
    )
    a3_roadmap = _roadmap_section(roadmap_text, "PR-A3")
    a4_roadmap = _roadmap_section(roadmap_text, "PR-A4")
    mapping_closeout = _heading_section(mapping_text, "Post-Merge Closeout")
    a3_packet_closeout = _heading_section(a3_packet_text, "Closeout Status")
    c4_status = _heading_section(c4_packet_text, "Status")
    gate_hard_gate = _heading_section(gate_text, "Hard Gate")

    if not a3_ledger:
        errors.append("A3 ledger entry: missing anchor ledger-p1-ai-bounded-context-packet")
    if not extraction_ledger:
        errors.append(
            "A4 extraction ledger entry: missing anchor ledger-p1-ai-bounded-context-extraction"
        )
    if not a3_roadmap:
        errors.append("A3 roadmap section: missing heading ## PR-A3")

    merge_tokens = (
        f"PR #{PR_NUMBER}",
        TITLE,
        MERGED_AT,
        MERGE_COMMIT,
        ORIGINAL_BRANCH,
    )
    _require_tokens("A3 ledger entry", a3_ledger, merge_tokens, errors)
    _require_tokens("A3 roadmap section", a3_roadmap, merge_tokens, errors)
    _require_tokens("PR #1469 mapping closeout", mapping_closeout, merge_tokens, errors)
    _require_tokens("A3 orchestration packet closeout", a3_packet_closeout, merge_tokens, errors)
    _require_tokens("C4 A3 packet status", c4_status, merge_tokens, errors)
    _require_tokens("semantic-cache gate hard gate", gate_hard_gate, merge_tokens, errors)

    if "- [x] P1: AI bounded-context packet" not in a3_ledger:
        errors.append("A3 ledger entry: checkbox must be closed")
    if "- [ ] P1: AI bounded-context packet" in a3_ledger:
        errors.append("A3 ledger entry: stale open checkbox remains")
    if "Status: Closed." not in a3_ledger:
        errors.append("A3 ledger entry: missing closed status")
    if MAPPING_FIX_COMMIT in a3_ledger or MAPPING_FIX_COMMIT in a3_roadmap:
        errors.append("A3 active docs: mapping fix commit must not be used as merge proof")

    a4_open = "- [ ] P1: Extract AI runtime into a dedicated bounded context" in extraction_ledger
    a4_closed_by_own_pr = all(
        token in extraction_ledger
        for token in (
            "- [x] P1: Extract AI runtime into a dedicated bounded context",
            "PR #1203",
            "2026-03-21T06:01:31Z",
            "831d62d8be0da7307e5a0f2673d8c33dbf53ca49",  # pragma: allowlist secret
            "feat/ai-bounded-context-extraction",
        )
    )
    if a4_open and a4_closed_by_own_pr:
        errors.append(
            "A4 extraction ledger entry: contradictory state (open and closed-by-#1203 markers present)"
        )
    if not (a4_open or a4_closed_by_own_pr):
        errors.append(
            "A4 extraction ledger entry: extraction item must be open or closed by PR #1203"
        )
    if "PR-A4" not in a4_roadmap:
        errors.append("A4 roadmap section: missing or accidentally removed")

    if "Closeout Status" not in a3_packet_text:
        errors.append("A3 orchestration packet: missing Closeout Status section")
    if "Closeout note" not in c4_packet_text:
        errors.append("C4 A3 packet: missing closeout note")
    if MAPPING_STALE_HEADING_RE.search(mapping_text):
        errors.append("PR #1469 mapping: stale live Merge Readiness heading remains")
    if "Historical Merge Readiness" not in mapping_text:
        errors.append("PR #1469 mapping: missing historical merge-readiness section")
    if "Post-Merge Closeout" not in mapping_text:
        errors.append("PR #1469 mapping: missing post-merge closeout evidence")
    if not mapping_closeout:
        errors.append("PR #1469 mapping: missing Post-Merge Closeout section")
    if not gate_hard_gate:
        errors.append("semantic-cache gate: missing Hard Gate section")

    whole_active_text = "\n".join(
        (ledger_text, roadmap_text, gate_text, mapping_text, a3_packet_text, c4_packet_text)
    )
    for pattern in (STALE_A3_RE, STALE_A3_REVERSED_RE):
        match = pattern.search(whole_active_text)
        if match:
            errors.append(f"active A3 docs: stale planned/pending wording: {match.group(0)[:180]}")

    scanned_texts = {
        "A3 ledger entry": a3_ledger,
        "A3 roadmap section": a3_roadmap,
        "semantic-cache gate": gate_text,
        "PR #1469 mapping": mapping_text,
        "A3 orchestration packet": a3_packet_text,
        "C4 A3 packet": c4_packet_text,
    }
    for label, text in scanned_texts.items():
        _check_local_path_leaks(label, text, errors)

    a3_claim_texts = {
        "A3 ledger entry": a3_ledger,
        "A3 roadmap section": a3_roadmap,
        "semantic-cache gate": _gate_closeout_claim_text(gate_text),
        "PR #1469 mapping closeout": mapping_closeout,
        "A3 orchestration packet closeout": a3_packet_closeout,
        "C4 A3 packet status": c4_status,
    }
    for label, text in a3_claim_texts.items():
        _check_a4_boundary(label, text, errors)
    for label, text in {
        "A3 ledger entry": a3_ledger,
        "A3 roadmap section": a3_roadmap,
        "semantic-cache gate": _gate_closeout_claim_text(gate_text),
        "PR #1469 mapping closeout": mapping_closeout,
        "A3 orchestration packet closeout": a3_packet_closeout,
        "C4 A3 packet status": c4_status,
    }.items():
        _check_forbidden_claims(label, text, errors)

    _check_gate_markers(gate_text, errors)
    return errors


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--semantic-cache-gate", type=Path, default=DEFAULT_SEMANTIC_CACHE_GATE)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--a3-packet", type=Path, default=DEFAULT_A3_PACKET)
    parser.add_argument("--c4-packet", type=Path, default=DEFAULT_C4_PACKET)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    errors = validate_closeout(
        repo_root=args.repo_root,
        ledger=args.ledger,
        roadmap=args.roadmap,
        semantic_cache_gate=args.semantic_cache_gate,
        mapping=args.mapping,
        a3_packet=args.a3_packet,
        c4_packet=args.c4_packet,
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("A3 bounded-context packet closeout guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail-closed guard for PR-A7 recursive-methods W1 closeout truth."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

PR_NUMBER = "1499"
MERGE_DATE = "2026-04-23"
MERGE_TIMESTAMP = "2026-04-23T01:37:29Z"
MERGE_COMMIT = "".join(("1e7166e5", "5c54448c", "0d647533", "8e1b9984", "efd0caf1"))
ORIGINAL_BRANCH = "codex/ai-recursive-methods-w1"

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
DEFAULT_PR1499_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1499_FIXED_MAPPING.md"
DEFAULT_SEMANTIC_CACHE_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)

REQUIRED_RUNTIME_FILES = (
    "core/rag/recursive_retrieval.py",
    "core/rag/orchestration.py",
    "core/ai/insight_runtime.py",
    "app/services/insight_runtime.py",
    "app/services/insight_application_service.py",
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

UNICODE_DASH_TRANSLATION = str.maketrans(
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

PR_A7_PATTERN = r"(?:pr(?:[-\s]+)?a7|pr\s*(?:#|-)?\s*1499|#1499)"
PR_A7_TOKEN_PATTERN = rf"(?<!\w){PR_A7_PATTERN}(?!\w)"
CLAIM_GAP = r"[^.!?\n]*"
SEMANTIC_CACHE_PATTERN = r"semantic[-\s]+cache"
BACKEND_PATTERN = r"(?:redis|gpt[-\s]?cache)"
FORBIDDEN_SURFACE_PATTERN = (
    r"(?:graphrag|context[-\s]*manifest|contextmanifest|embeddings?|"
    r"vector[-\s]+(?:db|database|search)|"
    r"openapi|dto|(?:public\s+)?routes?(?:\s+changes?)?|response[-\s]+shape|"
    r"db\s+(?:persistence|rollout)|(?:vector\s+)?database\s+(?:persistence|rollout)|"
    r"provider[-\s]+side\s+(?:chain|tree)[-\s]+of[-\s]+thought|"
    r"(?:chain|tree)[-\s]+of[-\s]+thought|recursive\s+learning|user[-\s]+feedback)"
)
RAW_CACHEABLE_PATTERN = (
    r"(?:raw\s+(?:(?:user|llm|model|provider|assistant)\s+)?"
    r"(?:prompts?|responses?|answers?)|raw\s+(?:account|healthkit|secret|secrets?|"
    r"credential|credentials?|token|tokens?|pii|sensitive)\s+(?:data|truth|payloads?))"
)
POSITIVE_ACTION_PATTERN = (
    r"(?:opens?|opened|enables?|enabled|implements?|implemented|approves?|approved|"
    r"allows?|allowed|permits?|permitted|authorizes?|authorized|selects?|selected|"
    r"chooses?|chosen|activates?|activated|rolls?\s+out|caches?|cached|caching|"
    r"cacheable|can\s+cache|stores?|stored|storing|"
    r"production[-\s]+ready|rollout[-\s]+ready)"
)
DIRECT_SEMANTIC_CACHE_ACTION_PATTERN = (
    r"(?:opened|enabled|activated|approved|authorized|selected|chosen|cached|"
    r"cacheable|available|supported|production[-\s]+ready|rollout[-\s]+ready)"
)
DIRECT_FORBIDDEN_SURFACE_STATUS_PATTERN = (
    r"(?:approved|enabled|authorized|selected|activated|"
    r"active|open|opened|live|production[-\s]+ready|rollout[-\s]+ready)"
)
DIRECT_FORBIDDEN_SURFACE_BE_STATUS_PATTERN = (
    rf"(?:{DIRECT_FORBIDDEN_SURFACE_STATUS_PATTERN}|implemented|available|supported)"
)
NEGATION_PATTERN = (
    r"(?:no|not|never|does\s+not|doesn't|must\s+not|cannot|can't|"
    r"out\s+of\s+scope|blocked|deferred|remains\s+closed|remained\s+closed)"
)

STALE_ACTIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "PR #1499 in-progress claim",
        re.compile(r"\bin\s+progress\s+via\s+pr\s*#?\s*1499\b", re.I),
    ),
    (
        "A7 active lane claim",
        re.compile(r"\bactive\b.*\bcodex/ai-recursive-methods-w1\b", re.I),
    ),
    (
        "pending final merge-cycle claim",
        re.compile(r"\bfinal\s+merge[-\s]+cycle\s+reconfirmation\s+is\s+still\s+pending\b", re.I),
    ),
    (
        "pending current-head merge-cycle claim",
        re.compile(r"\bcurrent[-\s]+head\b.*\bstill\s+pending\b", re.I),
    ),
    (
        "required-checks pending claim",
        re.compile(r"\brequired\s+checks\s+(?:are\s+)?still\s+pending\b", re.I),
    ),
    (
        "PR-A7 stale active/pending closeout claim",
        re.compile(
            rf"{PR_A7_TOKEN_PATTERN}{CLAIM_GAP}"
            r"\b(?:lane|closeout|closure|implementation|status)\b"
            rf"{CLAIM_GAP}\b(?:active|pending|in\s+progress|open)\b",
            re.I,
        ),
    ),
    (
        "PR-A7 stale active/pending closeout claim",
        re.compile(
            rf"{PR_A7_TOKEN_PATTERN}{CLAIM_GAP}"
            r"\b(?:active|pending|in\s+progress|open)\b"
            rf"{CLAIM_GAP}\b(?:lane|closeout|closure|implementation|tasks?)\b",
            re.I,
        ),
    ),
)

CHECKED_READINESS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "checked current-head CI assertion",
        re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[x\]\s+current[-\s]+head\s+ci\b", re.I | re.M),
    ),
    (
        "checked required-checks assertion",
        re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[x\]\s+(?:all\s+)?required\s+checks\b", re.I | re.M),
    ),
    (
        "checked CI-green assertion",
        re.compile(
            r"^\s*(?:[-*+]|\d+\.)\s*\[x\]\s+(?:current[-\s]+head\s+)?ci\s+green\b", re.I | re.M
        ),
    ),
    (
        "checked review-thread assertion",
        re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[x\]\s+(?:all\s+)?review[-\s]+threads?\b", re.I | re.M),
    ),
    (
        "checked bot-comments assertion",
        re.compile(
            r"^\s*(?:[-*+]|\d+\.)\s*\[x\]\s+no\s+actionable\s+bot\s+comments\b", re.I | re.M
        ),
    ),
    (
        "checked wait-window assertion",
        re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[x\].*\bwait[-\s]+window\b", re.I | re.M),
    ),
    (
        "checked pre-commit assertion",
        re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[x\].*\bpre[-\s]+commit\b", re.I | re.M),
    ),
    (
        "checked make verify assertion",
        re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[x\].*\bmake\s+verify\b", re.I | re.M),
    ),
)

FORBIDDEN_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "PR-A7 opens semantic cache",
        re.compile(
            rf"{PR_A7_TOKEN_PATTERN}{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b"
            rf"{CLAIM_GAP}\b{SEMANTIC_CACHE_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "semantic cache enabled by PR-A7",
        re.compile(
            rf"\b{SEMANTIC_CACHE_PATTERN}\b{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b"
            rf"{CLAIM_GAP}\b(?:by|via|from)\b{CLAIM_GAP}{PR_A7_TOKEN_PATTERN}",
            re.I,
        ),
    ),
    (
        "semantic cache direct activation",
        re.compile(
            rf"\b{SEMANTIC_CACHE_PATTERN}\b"
            r"(?:\s+(?:serving|runtime|gate))?\s+"
            r"(?:(?:is|has\s+been|now|remains?)\s+)?"
            rf"\b{DIRECT_SEMANTIC_CACHE_ACTION_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "semantic cache active status",
        re.compile(
            rf"\b{SEMANTIC_CACHE_PATTERN}\b{CLAIM_GAP}\b"
            r"(?:is|has\s+been|now|remains?)\s+"
            r"(?:active|enabled|open|opened|live|production[-\s]+ready|rollout[-\s]+ready)\b",
            re.I,
        ),
    ),
    (
        "PR-A7 approves Redis/GPTCache",
        re.compile(
            rf"{PR_A7_TOKEN_PATTERN}{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b"
            rf"{CLAIM_GAP}\b{BACKEND_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "Redis/GPTCache rollout approved",
        re.compile(
            rf"\b{BACKEND_PATTERN}\b{CLAIM_GAP}\b"
            r"(?:approved|enabled|selected|authorized|production[-\s]+ready|rollout[-\s]+ready)\b",
            re.I,
        ),
    ),
    (
        "PR-A7 approves forbidden runtime surface",
        re.compile(
            rf"{PR_A7_TOKEN_PATTERN}{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b"
            rf"{CLAIM_GAP}\b{FORBIDDEN_SURFACE_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "forbidden runtime surface approved by PR-A7",
        re.compile(
            rf"\b{FORBIDDEN_SURFACE_PATTERN}\b{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b"
            rf"{CLAIM_GAP}\b(?:by|via|from)\b{CLAIM_GAP}{PR_A7_TOKEN_PATTERN}",
            re.I,
        ),
    ),
    (
        "forbidden runtime surface direct approval",
        re.compile(
            rf"\b{FORBIDDEN_SURFACE_PATTERN}\b"
            r"(?:\s+(?:rollout|serving|runtime|implementation|persistence|changes?)){0,3}"
            r"\s+(?:is|has\s+been|now)?\s*"
            rf"\b{DIRECT_FORBIDDEN_SURFACE_STATUS_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "forbidden runtime surface active status",
        re.compile(
            rf"\b{FORBIDDEN_SURFACE_PATTERN}\b{CLAIM_GAP}\b"
            r"(?:is|has\s+been|now|remains?)\s+"
            rf"{DIRECT_FORBIDDEN_SURFACE_BE_STATUS_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "semantic cache stores raw prompt/response/data",
        re.compile(
            rf"\b{SEMANTIC_CACHE_PATTERN}\b{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b"
            rf"{CLAIM_GAP}\b{RAW_CACHEABLE_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "raw prompt/response/data cache permission",
        re.compile(
            rf"{PR_A7_TOKEN_PATTERN}{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b"
            rf"{CLAIM_GAP}\b{RAW_CACHEABLE_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "raw prompt/response/data cache permission",
        re.compile(
            rf"\b{RAW_CACHEABLE_PATTERN}\b{CLAIM_GAP}\b{POSITIVE_ACTION_PATTERN}\b",
            re.I,
        ),
    ),
)

NEGATABLE_ACTION_PATTERN = rf"(?:{POSITIVE_ACTION_PATTERN}|active|open|live)"
NEGATION_BINDING_BREAK_PATTERN = re.compile(r"\b(?:and|but|however|then)\b|[.,;:]", re.I)
ADVERSATIVE_BREAK_PATTERN = re.compile(r"\b(?:but|however|then)\b|[;:]", re.I)
NON_BINDING_NOT_PATTERN = re.compile(r"\b(?:not|does\s+not|doesn't)\b", re.I)
TRAILING_BLOCKER_PATTERN = re.compile(
    r"^\s*(?:remains?\s+)?"
    r"(?:blocked|closed|deferred|out\s+of\s+scope|forbidden|disallowed|"
    r"not\s+(?:allowed|approved|enabled|open|opened|active|live))"
    r"(?:\s+(?:by|under|per|because|until|unless|for|via)\b.*)?\s*$",
    re.I,
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"missing required file: {path}") from exc


def _normalize_text(text: str) -> str:
    text = text.translate(UNICODE_DASH_TRANSLATION)
    text = re.sub(r"\bpr\s*-\s*\n\s*a7\b", "PR-A7", text, flags=re.I)
    text = re.sub(r"\bpr\s*\n\s*a7\b", "PR-A7", text, flags=re.I)
    text = re.sub(
        rf"({PR_A7_TOKEN_PATTERN})[ \t]*(?:\n[ \t]*)+(?=\b{POSITIVE_ACTION_PATTERN}\b)",
        r"\1 ",
        text,
        flags=re.I,
    )
    text = re.sub(r"\bsemantic\s*\n\s*cache\b", "semantic-cache", text, flags=re.I)
    text = re.sub(
        rf"\b({SEMANTIC_CACHE_PATTERN})\b[ \t]*(?:\n[ \t]*)+(?=\b(?:is|has\s+been|now|remains?)\b)",
        r"\1 ",
        text,
        flags=re.I,
    )
    text = re.sub(
        rf"\b({RAW_CACHEABLE_PATTERN})\b[ \t]*(?:\n[ \t]*)+(?=\b(?:{POSITIVE_ACTION_PATTERN}|are\s+{DIRECT_SEMANTIC_CACHE_ACTION_PATTERN})\b)",
        r"\1 ",
        text,
        flags=re.I,
    )
    text = re.sub(
        rf"\b({POSITIVE_ACTION_PATTERN})\b[ \t]*(?:\n[ \t]*)+"
        rf"(?=\b(?:{SEMANTIC_CACHE_PATTERN}|{BACKEND_PATTERN}|{FORBIDDEN_SURFACE_PATTERN}|{RAW_CACHEABLE_PATTERN})\b)",
        r"\1 ",
        text,
        flags=re.I,
    )
    return text


def _normalize_prose(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize_text(text))


def _section_after_anchor(text: str, *, anchor: str, next_anchor: str = "\n<a id=") -> str:
    start = text.find(anchor)
    if start == -1:
        return ""
    next_start = text.find(next_anchor, start + len(anchor))
    if next_start == -1:
        return text[start:]
    return text[start:next_start]


def _section_between_headings(text: str, *, heading: str, next_prefix: str = "\n## ") -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    next_start = text.find(next_prefix, start + len(heading))
    if next_start == -1:
        return text[start:]
    return text[start:next_start]


def _subsection_between(text: str, *, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    next_heading = re.search(r"\n####\s+", text[start + len(heading) :])
    if not next_heading:
        return text[start:]
    return text[start : start + len(heading) + next_heading.start()]


def _require_contains(errors: list[str], label: str, text: str, needle: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing required evidence `{needle}`")


def _is_negated_claim(text: str, match: re.Match[str]) -> bool:
    local_start = (
        max(
            text.rfind(".", 0, match.start()),
            text.rfind("!", 0, match.start()),
            text.rfind("?", 0, match.start()),
            text.rfind("\n", 0, match.start()),
            text.rfind(";", 0, match.start()),
            text.rfind(":", 0, match.start()),
        )
        + 1
    )
    sentence_end_candidates = [
        pos
        for pos in (
            text.find(".", match.end()),
            text.find("!", match.end()),
            text.find("?", match.end()),
            text.find("\n", match.end()),
            text.find(";", match.end()),
            text.find(":", match.end()),
        )
        if pos != -1
    ]
    sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)
    snippet = text[local_start : match.end()]
    actions = list(re.finditer(rf"\b{NEGATABLE_ACTION_PATTERN}\b", snippet, re.I))
    action = actions[-1] if actions else None
    if not action:
        return re.search(rf"\b{NEGATION_PATTERN}\b", snippet, re.I) is not None

    suffix = text[match.end() : sentence_end]
    if TRAILING_BLOCKER_PATTERN.fullmatch(suffix):
        return True

    prefix = snippet[: action.start()]
    negations = list(re.finditer(rf"\b{NEGATION_PATTERN}\b", prefix, re.I))
    if not negations:
        return False

    negation = negations[-1]
    between = prefix[negation.end() :]
    if re.fullmatch(r"no", negation.group(0), re.I) and not ADVERSATIVE_BREAK_PATTERN.search(
        between
    ):
        if re.match(r"\s*,", between):
            return False
        return True
    if NEGATION_BINDING_BREAK_PATTERN.search(between):
        return False
    return True


def _reject_stale_active_claims(errors: list[str], label: str, text: str) -> None:
    normalized_text = _normalize_prose(text)
    for claim, pattern in STALE_ACTIVE_PATTERNS:
        if pattern.search(normalized_text):
            errors.append(f"{label}: stale active-state claim remains `{claim}`")


def _reject_checked_historical_readiness(errors: list[str], label: str, text: str) -> None:
    for claim, pattern in CHECKED_READINESS_PATTERNS:
        if pattern.search(text):
            errors.append(f"{label}: checked historical readiness assertion remains `{claim}`")


def _validate_forbidden_claims(label: str, text: str) -> list[str]:
    errors: list[str] = []
    normalized_text = _normalize_text(text)
    for claim, pattern in FORBIDDEN_CLAIM_PATTERNS:
        for match in pattern.finditer(normalized_text):
            if not _is_negated_claim(normalized_text, match):
                errors.append(f"{label}: forbidden A7 closeout claim: {claim}")
                break
    return errors


def _has_forbidden_landed_scope_item(text: str) -> bool:
    for line in _normalize_text(text).splitlines():
        match = re.search(
            rf"\b(?:{SEMANTIC_CACHE_PATTERN}|{BACKEND_PATTERN}|{FORBIDDEN_SURFACE_PATTERN})\b",
            line,
            re.I,
        )
        if not match:
            continue
        prefix = line[: match.start()]
        if re.search(rf"\b{NEGATION_PATTERN}\b", prefix, re.I):
            continue
        return True
    return False


def _validate_runtime_files(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relpath in REQUIRED_RUNTIME_FILES:
        if not (repo_root / relpath).is_file():
            errors.append(f"recursive W1 landed runtime evidence missing: {relpath}")
    return errors


def _validate_semantic_cache_gate_markers(text: str) -> list[str]:
    errors: list[str] = []
    for marker, expected in REQUIRED_GATE_MARKERS.items():
        matches = re.findall(rf"<!--\s*{re.escape(marker)}:\s*([^>]+?)\s*-->", text)
        if not matches:
            errors.append(f"semantic-cache gate: missing marker {marker}")
            continue
        if len(matches) > 1:
            errors.append(f"semantic-cache gate: duplicate marker {marker}")
            continue
        actual = matches[0].strip()
        if actual != expected:
            errors.append(
                f"semantic-cache gate: invalid marker {marker}: expected {expected}, got {actual}"
            )
    return errors


def _validate_ledger(text: str) -> list[str]:
    errors: list[str] = []
    block = _section_after_anchor(text, anchor='<a id="ledger-p1-recursive-methods"></a>')
    if not block:
        return ["BACKLOG_LEDGER.md: missing recursive methods ledger anchor block"]

    for needle in (
        "- [ ] P1: Recursive methods for LLM/RAG/AI assistant",
        f"PR #{PR_NUMBER}",
        MERGE_DATE,
        MERGE_COMMIT,
        ORIGINAL_BRANCH,
        "W1 landed",
        "parent P1 checkbox stays open",
        "Parent P1 checkbox stays open",
        "does not duplicate implementation",
        "semantic cache",
        "Redis/GPTCache",
        "GraphRAG",
        "ContextManifest",
        "DB persistence",
        "public routes",
        "public DTOs",
        "recursive learning",
    ):
        _require_contains(errors, "BACKLOG_LEDGER.md recursive methods block", block, needle)

    if "- [x] P1: Recursive methods for LLM/RAG/AI assistant" in block:
        errors.append("BACKLOG_LEDGER.md recursive methods block: parent P1 checkbox is closed")

    _reject_stale_active_claims(errors, "BACKLOG_LEDGER.md recursive methods block", block)
    errors.extend(_validate_forbidden_claims("BACKLOG_LEDGER.md recursive methods block", block))
    return errors


def _validate_roadmap(text: str) -> list[str]:
    errors: list[str] = []
    block = _section_between_headings(text, heading="## PR-A7 - recursive methods W1")
    if not block:
        block = _section_between_headings(text, heading="## PR-A7 \u2014 recursive methods W1")
    if not block:
        return ["PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md: missing PR-A7 block"]

    for needle in (
        "#### Status",
        f"Landed via PR #{PR_NUMBER}",
        MERGE_DATE,
        MERGE_COMMIT,
        ORIGINAL_BRANCH,
        "does not duplicate runtime implementation",
        "parent recursive-methods P1 item remains open",
        "#### Landed W1 scope",
        "bounded recursive RAG",
        "bounded recursive verification",
        "existing `VerificationBundle` truth",
        "#### Out of scope",
        "semantic cache implementation or gate opening",
        "Redis/GPTCache rollout or backend approval",
        "GraphRAG",
        "ContextManifest",
        "DB persistence",
        "public route",
        "OpenAPI",
        "DTO",
        "provider-side tree-of-thought",
        "recursive learning",
    ):
        _require_contains(
            errors,
            "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md PR-A7 block",
            block,
            needle,
        )

    in_scope = _subsection_between(block, heading="#### Landed W1 scope")
    if _has_forbidden_landed_scope_item(in_scope):
        errors.append(
            "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md PR-A7 block: landed scope includes forbidden surface"
        )

    _reject_stale_active_claims(
        errors,
        "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md PR-A7 block",
        block,
    )
    errors.extend(
        _validate_forbidden_claims(
            "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md PR-A7 block",
            block,
        )
    )
    return errors


def _validate_pr1499_mapping(text: str) -> list[str]:
    errors: list[str] = []
    closeout_block = _section_between_headings(text, heading="## Post-Merge Closeout")
    if not closeout_block:
        return ["PR_1499_FIXED_MAPPING.md: missing Post-Merge Closeout section"]

    for needle in (
        "State: `MERGED`",
        f"PR #{PR_NUMBER}",
        MERGE_TIMESTAMP,
        MERGE_COMMIT,
        ORIGINAL_BRANCH,
        "not re-opened",
        "implementation is not duplicated",
        "semantic-cache gate remained closed",
        "Redis/GPTCache",
        "GraphRAG",
        "ContextManifest",
        "DB persistence",
        "public route",
        "OpenAPI",
        "DTO",
    ):
        _require_contains(errors, "PR_1499_FIXED_MAPPING.md closeout block", closeout_block, needle)

    _reject_stale_active_claims(errors, "PR_1499_FIXED_MAPPING.md", text)
    _reject_checked_historical_readiness(errors, "PR_1499_FIXED_MAPPING.md", text)
    errors.extend(_validate_forbidden_claims("PR_1499_FIXED_MAPPING.md", text))
    return errors


def validate_closeout(
    *,
    repo_root: Path = REPO_ROOT,
    ledger_path: Path | None = None,
    roadmap_path: Path | None = None,
    mapping_path: Path | None = None,
    semantic_cache_gate_path: Path | None = None,
) -> list[str]:
    ledger = ledger_path or repo_root / DEFAULT_LEDGER.relative_to(REPO_ROOT)
    roadmap = roadmap_path or repo_root / DEFAULT_ROADMAP.relative_to(REPO_ROOT)
    mapping = mapping_path or repo_root / DEFAULT_PR1499_MAPPING.relative_to(REPO_ROOT)
    semantic_cache_gate = (
        semantic_cache_gate_path or repo_root / DEFAULT_SEMANTIC_CACHE_GATE.relative_to(REPO_ROOT)
    )

    errors: list[str] = []
    try:
        ledger_text = _read_text(ledger)
        roadmap_text = _read_text(roadmap)
        mapping_text = _read_text(mapping)
        gate_text = _read_text(semantic_cache_gate)
    except FileNotFoundError as exc:
        return [str(exc)]

    errors.extend(_validate_runtime_files(repo_root))
    errors.extend(_validate_ledger(ledger_text))
    errors.extend(_validate_roadmap(roadmap_text))
    errors.extend(_validate_pr1499_mapping(mapping_text))
    errors.extend(_validate_semantic_cache_gate_markers(gate_text))
    errors.extend(_validate_forbidden_claims("semantic-cache gate document", gate_text))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--roadmap", type=Path, default=None)
    parser.add_argument("--mapping", type=Path, default=None)
    parser.add_argument("--semantic-cache-gate", type=Path, default=None)
    args = parser.parse_args(argv)

    errors = validate_closeout(
        repo_root=args.repo_root.resolve(),
        ledger_path=args.ledger,
        roadmap_path=args.roadmap,
        mapping_path=args.mapping,
        semantic_cache_gate_path=args.semantic_cache_gate,
    )
    if errors:
        print("ERROR: PR-A7 recursive-methods W1 closeout guard failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("OK: PR-A7 recursive-methods W1 closeout guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

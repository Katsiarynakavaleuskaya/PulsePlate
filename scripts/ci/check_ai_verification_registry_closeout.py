#!/usr/bin/env python3
"""Fail-closed guard for PR-V1 verification-registry closeout truth."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

PR_NUMBER = "1491"
MERGE_DATE = "2026-04-22"
MERGE_TIMESTAMP = "2026-04-22T10:38:04Z"
# Public merge SHA is split to avoid detect-secrets high-entropy false positives.
MERGE_COMMIT = "ce024e7c" "dca3ec94" "bbffb095" "e050010a" "8198e792"
ORIGINAL_BRANCH = "codex/ai-verification-registry-v1"

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
DEFAULT_PR1491_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1491_FIXED_MAPPING.md"
DEFAULT_SEMANTIC_CACHE_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)

REQUIRED_CORE_FILES = (
    "core/verification/__init__.py",
    "core/verification/contracts.py",
    "core/verification/policy.py",
    "core/verification/registry.py",
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

STALE_ACTIVE_PHRASES = (
    "Active execution packet on branch `codex/ai-verification-registry-v1`",
    "write admission still lacks one first-class verification bundle",
    "still lacks one first-class verification bundle",
    "knowledge promotion remains fail-closed by policy/confidence/degraded-path only",
    "current head needs one final current-head CI pass",
    "current head is still waiting on the post-fix CI rerun",
)

SENSITIVE_CACHE_TERMS = (
    r"account\s+data",
    r"sensitive\s+data",
    r"secrets?",
    r"credentials?",
    r"tokens?",
    r"pii",
    r"personal(?:ly)?\s+identifiable\s+information",
)

SENSITIVE_CACHE_TERM_PATTERN = r"(?:{})".format("|".join(SENSITIVE_CACHE_TERMS))
CLAIM_GAP = r"(?:(?!\n\s*(?:[-*]|#))[^.!?])*"
PR_V1_PATTERN = r"pr[- ]?v1"
BACKEND_LABEL_PATTERN = r"(?:redis|gpt[-\s]?cache)"
UNICODE_DASH_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)

FORBIDDEN_PR_V1_CLAIMS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "PR-V1 opens semantic cache",
        re.compile(
            rf"\b{PR_V1_PATTERN}\b{CLAIM_GAP}\bopen(?:s|ed)?\b"
            rf"{CLAIM_GAP}\bsemantic[- ]cache\b",
            re.I,
        ),
    ),
    (
        "PR-V1 enables semantic cache",
        re.compile(
            rf"\b{PR_V1_PATTERN}\b{CLAIM_GAP}\benable(?:s|d)?\b"
            rf"{CLAIM_GAP}\bsemantic[- ]cache\b",
            re.I,
        ),
    ),
    (
        "semantic cache active/open claim",
        re.compile(
            rf"\bsemantic[- ]cache\b{CLAIM_GAP}\b"
            r"(?:active|enabled|open|live|production[- ]ready|approved|approval|"
            r"allowed|permitted|permission)\b",
            re.I,
        ),
    ),
    (
        "PR-V1 makes semantic cache production ready",
        re.compile(
            rf"\b{PR_V1_PATTERN}\b{CLAIM_GAP}\b(?:makes?|marks?)\b{CLAIM_GAP}"
            rf"\bsemantic[- ]cache\b{CLAIM_GAP}\bproduction[- ]ready\b",
            re.I,
        ),
    ),
    (
        "PR-V1 approves semantic cache serving",
        re.compile(
            rf"\b{PR_V1_PATTERN}\b{CLAIM_GAP}\b"
            r"(?:approves?|approved|allows?|allowed|permits?|permitted|"
            r"selects?|selected|approval|permission|grants?\s+permission)"
            rf"\b{CLAIM_GAP}\bsemantic[- ]cache\b",
            re.I,
        ),
    ),
    (
        "semantic cache serving approval verb",
        re.compile(
            r"\b(?:approves?|allows?|permits?|selects?|grants?\s+permission)"
            rf"\b{CLAIM_GAP}\bsemantic[- ]cache\b",
            re.I,
        ),
    ),
    (
        "PR-V1 approves Redis/GPTCache rollout",
        re.compile(
            rf"\b{PR_V1_PATTERN}\b{CLAIM_GAP}\b"
            r"(?:approves?|approved|enables?|enabled|selects?|selected|"
            r"allows?|allowed|permits?|permitted|approval|permission|"
            rf"grants?\s+permission)\b{CLAIM_GAP}"
            rf"\b{BACKEND_LABEL_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "Redis/GPTCache rollout approval",
        re.compile(
            rf"\b{BACKEND_LABEL_PATTERN}\b{CLAIM_GAP}"
            r"\b(?:approved|enabled|rollout[- ]ready|production[- ]ready|"
            r"selected|allowed|permitted|approval|permission)\b",
            re.I,
        ),
    ),
    (
        "raw prompts cacheable",
        re.compile(
            rf"\braw\s+(?:model\s+)?prompts?\b{CLAIM_GAP}\b(?:cache|cached|cacheable)\b",
            re.I,
        ),
    ),
    (
        "raw prompts cacheable",
        re.compile(
            rf"\b(?:cache|caches|cached|cacheable|can\s+cache)\b{CLAIM_GAP}"
            r"\braw\s+(?:model\s+)?prompts?\b",
            re.I,
        ),
    ),
    (
        "raw prompts cacheable",
        re.compile(
            rf"\bcaching\b{CLAIM_GAP}\braw\s+(?:model\s+)?prompts?\b",
            re.I,
        ),
    ),
    (
        "raw responses cacheable",
        re.compile(
            rf"\braw\s+(?:model\s+)?responses?\b{CLAIM_GAP}\b(?:cache|cached|cacheable)\b",
            re.I,
        ),
    ),
    (
        "raw responses cacheable",
        re.compile(
            rf"\b(?:cache|caches|cached|cacheable|can\s+cache)\b{CLAIM_GAP}"
            r"\braw\s+(?:model\s+)?responses?\b",
            re.I,
        ),
    ),
    (
        "raw responses cacheable",
        re.compile(
            rf"\bcaching\b{CLAIM_GAP}\braw\s+(?:model\s+)?responses?\b",
            re.I,
        ),
    ),
    (
        "raw sensitive data cacheable",
        re.compile(
            rf"\braw\s+{SENSITIVE_CACHE_TERM_PATTERN}\b{CLAIM_GAP}"
            r"\b(?:cache|cached|cacheable)\b",
            re.I,
        ),
    ),
    (
        "raw sensitive data cacheable",
        re.compile(
            rf"\b(?:cache|caches|cached|cacheable|can\s+cache)\b{CLAIM_GAP}"
            rf"\braw\s+{SENSITIVE_CACHE_TERM_PATTERN}\b",
            re.I,
        ),
    ),
    (
        "raw sensitive data cacheable",
        re.compile(
            rf"\bcaching\b{CLAIM_GAP}\braw\s+{SENSITIVE_CACHE_TERM_PATTERN}\b",
            re.I,
        ),
    ),
)

NEGATED_FORBIDDEN_CLAIM_PATTERNS = (
    re.compile(
        rf"\b{PR_V1_PATTERN}\b{CLAIM_GAP}\b"
        r"(?:does\s+not(?!\s+only)|doesn't|must\s+not|should\s+not|cannot|can't)\b"
        rf"{CLAIM_GAP}\b(?:open|enable|approve|allow|permit|select|grant\s+permission)\b"
        rf"{CLAIM_GAP}\b(?:semantic[- ]cache|{BACKEND_LABEL_PATTERN})\b",
        re.I,
    ),
    re.compile(
        r"\b(?:does\s+not(?!\s+only)|doesn't|must\s+not|should\s+not|cannot|can't)\b"
        rf"{CLAIM_GAP}\b(?:open|enable|approve|allow|permit|select|grant\s+permission)\b"
        rf"{CLAIM_GAP}\b(?:semantic[- ]cache|{BACKEND_LABEL_PATTERN})\b",
        re.I,
    ),
    re.compile(
        rf"\bsemantic[- ]cache\b{CLAIM_GAP}\b"
        r"(?:is\s+not(?!\s+only)|isn't|has\s+not(?!\s+only)|hasn't|"
        r"lacks?|without|not(?!\s+only))\b"
        rf"{CLAIM_GAP}\b(?:active|enabled|open|live|production[- ]ready|approved|"
        r"allowed|permitted|approval|permission)\b",
        re.I,
    ),
    re.compile(
        rf"\bsemantic[- ]cache\b{CLAIM_GAP}\b(?:has|requires)?\s*no\b"
        rf"{CLAIM_GAP}\b(?:approval|permission)\b",
        re.I,
    ),
    re.compile(
        rf"\bnot\s+(?:a\s+)?semantic[- ]cache\b{CLAIM_GAP}\b"
        r"(?:rollout|activation|approval|permission|backend[- ]selection\s+approval)\b",
        re.I,
    ),
    re.compile(
        rf"\b{BACKEND_LABEL_PATTERN}\b{CLAIM_GAP}\b"
        r"(?:is\s+not(?!\s+only)|isn't|has\s+not(?!\s+only)|hasn't|"
        r"lacks?|without|not(?!\s+only)|has\s+no|no)\b"
        rf"{CLAIM_GAP}\b(?:approved|enabled|rollout[- ]ready|production[- ]ready|"
        r"selected|allowed|permitted|approval|permission)\b",
        re.I,
    ),
    re.compile(
        rf"\braw\s+(?:model\s+)?(?:prompts?|responses?|{SENSITIVE_CACHE_TERM_PATTERN})\b"
        rf"{CLAIM_GAP}\b(?:is|are)?\s*not(?!\s+only)\b{CLAIM_GAP}\b"
        r"(?:cache|caching|cached|cacheable)\b",
        re.I,
    ),
    re.compile(
        rf"\braw\s+(?:model\s+)?(?:prompts?|responses?|{SENSITIVE_CACHE_TERM_PATTERN})\b"
        rf"{CLAIM_GAP}\b(?:cannot|can't|must\s+not|should\s+not|never|"
        r"(?:is|are)\s+never|can\s+never)\b"
        rf"{CLAIM_GAP}\b(?:be\s+)?(?:cache|caching|cached|cacheable)\b",
        re.I,
    ),
    re.compile(
        rf"\braw\s+(?:model\s+)?(?:prompts?|responses?|{SENSITIVE_CACHE_TERM_PATTERN})\b"
        rf"{CLAIM_GAP}\b(?:prohibited|forbidden|barred|blocked)\b"
        rf"{CLAIM_GAP}\bfrom\b{CLAIM_GAP}\b(?:being\s+)?(?:cache|caching|cached|cacheable)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:does\s+not|doesn't|must\s+not|should\s+not|cannot|can't|never)\b"
        rf"{CLAIM_GAP}\b(?:cache|caching)\b{CLAIM_GAP}\braw\s+"
        rf"(?:model\s+)?(?:prompts?|responses?|{SENSITIVE_CACHE_TERM_PATTERN})\b",
        re.I,
    ),
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"missing required file: {path}") from exc


def _normalize_claim_text(text: str) -> str:
    return text.translate(UNICODE_DASH_TRANSLATION)


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


def _require_contains(errors: list[str], label: str, text: str, needle: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing required evidence `{needle}`")


def _reject_contains(errors: list[str], label: str, text: str, needle: str) -> None:
    normalized_text = re.sub(r"\s+", " ", text).casefold()
    normalized_needle = re.sub(r"\s+", " ", needle).casefold()
    if normalized_needle in normalized_text:
        errors.append(f"{label}: stale or forbidden phrase remains `{needle}`")


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


def _validate_forbidden_claims(label: str, text: str) -> list[str]:
    errors: list[str] = []
    text = _normalize_claim_text(text)
    for claim, pattern in FORBIDDEN_PR_V1_CLAIMS:
        for match in pattern.finditer(text):
            if not _is_negated_forbidden_claim(text, match):
                errors.append(f"{label}: forbidden PR-V1 closeout claim: {claim}")
                break
    return errors


CLAUSE_BOUNDARY_RE = re.compile(
    r",|\b(?:and|as|because|but|however|if|since|so|then|though|although|unless|"
    r"when|whereas|while|yet)\b",
    re.I,
)


def _is_negated_forbidden_claim(text: str, match: re.Match[str]) -> bool:
    local_start = (
        max(
            text.rfind(".", 0, match.start()),
            text.rfind("!", 0, match.start()),
            text.rfind("?", 0, match.start()),
            text.rfind("\n", 0, match.start()),
            text.rfind(";", 0, match.start()),
        )
        + 1
    )
    for boundary in CLAUSE_BOUNDARY_RE.finditer(text, local_start, match.start()):
        local_start = boundary.end()
    snippet = text[local_start : match.end()]
    inner_start = 0
    for boundary in CLAUSE_BOUNDARY_RE.finditer(snippet):
        inner_start = boundary.end()
    snippet = snippet[inner_start:]
    return any(pattern.search(snippet) for pattern in NEGATED_FORBIDDEN_CLAIM_PATTERNS)


def _validate_core_files(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relpath in REQUIRED_CORE_FILES:
        if not (repo_root / relpath).is_file():
            errors.append(f"core verification registry evidence missing: {relpath}")
    return errors


def _validate_ledger(text: str) -> list[str]:
    errors: list[str] = []
    block = _section_after_anchor(
        text, anchor='<a id="ledger-p1-verification-registry-admission"></a>'
    )
    if not block:
        return ["BACKLOG_LEDGER.md: missing V1 ledger anchor block"]

    _require_contains(
        errors,
        "BACKLOG_LEDGER.md V1 block",
        block,
        "- [x] P1: Verification registry and verify-before-write admission invariant",
    )
    for needle in (
        f"PR #{PR_NUMBER}",
        MERGE_DATE,
        MERGE_COMMIT,
        ORIGINAL_BRANCH,
        "`core/verification/`",
        "Knowledge writes require an admissible verification bundle",
        "Delayed closeout",
        "semantic cache",
        "Redis/GPTCache",
        "GraphRAG",
        "ContextManifest",
    ):
        _require_contains(errors, "BACKLOG_LEDGER.md V1 block", block, needle)

    for stale in STALE_ACTIVE_PHRASES:
        _reject_contains(errors, "BACKLOG_LEDGER.md V1 block", block, stale)
    errors.extend(_validate_forbidden_claims("BACKLOG_LEDGER.md V1 block", block))
    return errors


def _validate_roadmap(text: str) -> list[str]:
    errors: list[str] = []
    block = _section_between_headings(
        text,
        heading="## PR-V1 — verification registry and verify-before-write admission",
    )
    if not block:
        return ["PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md: missing PR-V1 block"]

    for needle in (
        "#### Status",
        f"Landed via PR #{PR_NUMBER}",
        MERGE_DATE,
        MERGE_COMMIT,
        "closeout",
        "No `core/verification/*` reimplementation",
        "verify-before-write admission for knowledge promotion only",
        "semantic cache implementation or gate opening",
        "Redis/GPTCache",
        "GraphRAG",
        "ContextManifest",
        "DB persistence",
        "route / OpenAPI / public response shape changes",
    ):
        _require_contains(
            errors,
            "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md PR-V1 block",
            block,
            needle,
        )

    for stale in STALE_ACTIVE_PHRASES:
        _reject_contains(
            errors,
            "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md PR-V1 block",
            block,
            stale,
        )
    errors.extend(
        _validate_forbidden_claims(
            "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md PR-V1 block",
            block,
        )
    )
    return errors


def _validate_pr1491_mapping(text: str) -> list[str]:
    errors: list[str] = []
    closeout_block = _section_between_headings(text, heading="## Post-Merge Closeout")
    if not closeout_block:
        return ["PR_1491_FIXED_MAPPING.md: missing Post-Merge Closeout section"]

    for needle in (
        "State: `MERGED`",
        f"PR #{PR_NUMBER}",
        MERGE_TIMESTAMP,
        MERGE_COMMIT,
        ORIGINAL_BRANCH,
        "not re-opened",
        "semantic-cache gate remained closed",
    ):
        _require_contains(errors, "PR_1491_FIXED_MAPPING.md closeout block", closeout_block, needle)

    for stale in STALE_ACTIVE_PHRASES:
        _reject_contains(errors, "PR_1491_FIXED_MAPPING.md closeout block", closeout_block, stale)
    errors.extend(_validate_forbidden_claims("PR_1491_FIXED_MAPPING.md", closeout_block))
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
    mapping = mapping_path or repo_root / DEFAULT_PR1491_MAPPING.relative_to(REPO_ROOT)
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

    errors.extend(_validate_core_files(repo_root))
    errors.extend(_validate_ledger(ledger_text))
    errors.extend(_validate_roadmap(roadmap_text))
    errors.extend(_validate_pr1491_mapping(mapping_text))
    errors.extend(_validate_semantic_cache_gate_markers(gate_text))
    return errors


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate PR-V1 verification-registry closeout reconciliation.",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--roadmap", type=Path, default=None)
    parser.add_argument("--mapping", type=Path, default=None)
    parser.add_argument("--semantic-cache-gate", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    errors = validate_closeout(
        repo_root=args.repo_root,
        ledger_path=args.ledger,
        roadmap_path=args.roadmap,
        mapping_path=args.mapping,
        semantic_cache_gate_path=args.semantic_cache_gate,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: PR-V1 verification registry closeout is reconciled and gate-closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

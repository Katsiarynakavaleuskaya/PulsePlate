#!/usr/bin/env python3
"""Fail-closed guard for the PulsePlate semantic-cache gate document."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOC = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
DEFAULT_CONTRACT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "SEMANTIC_CACHE_ROLLOUT_GATE.md"
)

REQUIRED_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

REQUIRED_PHRASES = (
    "gate-closed",
    "reviewed gate-open PR",
    "product AI runtime rail",
    "not advisory wiki",
    "not workforce memory",
    "not a second source of truth",
    "not billing/auth/entitlement truth",
    "not a compliance/legal output cache",
    "not user-account truth surfaces",
)

ROLLOUT_ORDER = (
    "SC-G1 rollout gate contract",
    "SC-G2 exact/fuzzy cache scaffold",
    "SC-G3 observability and false-hit harness",
    "SC-G4 bounded `/insight` semantic-cache experiment",
    "SC-G5 backend selection",
)

FORBIDDEN_CLAIM_PATTERNS = (
    (
        "semantic cache implemented/active/enabled/open/approved",
        re.compile(
            r"\bsemantic\s+cache\s+(?:(?:is|has\s+been)\s+)?(?:now\s+)?"
            r"(?:implemented|active|enabled|open|approved|ready)\b"
        ),
    ),
    (
        "semantic-cache implemented/active/enabled/open/approved",
        re.compile(
            r"\bsemantic-cache\s+(?:(?:is|has\s+been)\s+)?(?:now\s+)?"
            r"(?:implemented|active|enabled|open|approved|ready)\b"
        ),
    ),
    (
        "semantic cache prerequisites satisfied",
        re.compile(r"\bsemantic\s+cache\s+prerequisites\s+(?:are\s+)?satisfied\b"),
    ),
    (
        "E1-E5 unlock semantic cache",
        re.compile(
            r"\be1\s*(?:-|through|to)\s*e5\s+(?:automatically\s+)?unlock(?:s)?\s+semantic\s+cache\b"
        ),
    ),
    (
        "E1-E5 satisfy semantic cache prerequisites",
        re.compile(
            r"\be1\s*(?:-|through|to)\s*e5\s+satisf(?:y|ies)\s+semantic\s+cache\s+prerequisites\b"
        ),
    ),
    (
        "Evidence Graph unlocks semantic cache",
        re.compile(r"\bevidence\s+graph\s+(?:automatically\s+)?unlock(?:s)?\s+semantic\s+cache\b"),
    ),
    (
        "advisory wiki feeds product cache",
        re.compile(r"\badvisory\s+wiki\s+(?:feeds|can\s+seed|seeds)\s+product\s+cache\b"),
    ),
    ("wiki pages are cache truth", re.compile(r"\bwiki\s+pages\s+are\s+cache\s+truth\b")),
    ("GraphRAG rollout approved", re.compile(r"\bgraphrag\s+rollout\s+(?:is\s+)?approved\b")),
    ("GPTCache rollout approved", re.compile(r"\bgptcache\s+rollout\s+(?:is\s+)?approved\b")),
    (
        "Redis semantic cache approved",
        re.compile(r"\bredis\s+semantic\s+cache\s+(?:is\s+)?approved\b"),
    ),
    ("cache raw prompt", re.compile(r"\bcache\s+raw\s+prompt\b")),
    ("cache raw response", re.compile(r"\bcache\s+raw\s+response\b")),
    ("cache secrets", re.compile(r"\bcache\s+secrets?\b")),
    ("cache user health data", re.compile(r"\bcache\s+user\s+health\s+data\b")),
    ("cache account truth", re.compile(r"\bcache\s+account\s+truth\b")),
    (
        "advisory evidence seeds product cache",
        re.compile(r"\badvisory\s+evidence\s+seeds\s+product\s+cache\b"),
    ),
)

CONTRACT_REQUIRED_PHRASES = (
    "does not open the semantic-cache gate",
    "does not implement semantic cache",
    "gate remains closed",
    "product AI runtime rail only",
    "feature-flagged",
    "off by default",
    "SC-G1 rollout gate contract",
    "SC-G2 exact/fuzzy cache scaffold",
    "SC-G3 observability and false-hit harness",
    "SC-G4 bounded `/insight` semantic-cache experiment",
    "SC-G5 backend selection",
    "exact duplicate hit",
    "normalized fuzzy hit",
    "semantic false positive",
    "stale-source hit",
    "policy-version mismatch hit",
    "model-version mismatch hit",
    "user-context leakage hit",
    "eligible_hit_rate",
    "served_hit_rate",
    "false_hit_rate",
    "cache_precision_proxy",
    "stale_answer_rate",
    "fallback_rate",
    "p50/p95 latency_saved",
    "provider_calls_avoided",
    "cost_saved",
    "quota_consumption_delta",
    "kill switch",
    "no-cache fallback path",
    "purge/invalidation path",
    "blocked cache surfaces",
    "advisory wiki pages as product truth",
    "billing/auth/entitlement",
    "legal/compliance outputs",
    "user-account truth",
    "raw prompts",
    "raw model responses",
    "Evidence Graph linkage",
    "admission decision IDs",
    "promotion/replay lineage",
)

MARKER_RE = re.compile(r"<!--\s*(?P<key>SEMANTIC_CACHE_[A-Z_]+):\s*(?P<value>.*?)\s*-->")


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"[/]+", "/", text)
    return re.sub(r"\s+", " ", text)


def _extract_markers(text: str) -> tuple[dict[str, str], list[str]]:
    markers: dict[str, str] = {}
    duplicates: list[str] = []
    for match in MARKER_RE.finditer(text):
        key = match.group("key")
        if key in markers and key not in duplicates:
            duplicates.append(key)
        markers[key] = match.group("value").strip().lower()
    return markers, duplicates


def _forbidden_claim_errors(text: str) -> list[str]:
    normalized = _normalize_text(text)
    return [
        f"forbidden semantic-cache claim: {label}"
        for label, pattern in FORBIDDEN_CLAIM_PATTERNS
        if pattern.search(normalized)
    ]


def validate_semantic_cache_gate(text: str) -> list[str]:
    """Return stable validation errors for unsafe semantic-cache gate docs."""
    errors: list[str] = []
    markers, duplicates = _extract_markers(text)

    for key in duplicates:
        errors.append(f"duplicate marker: {key}")

    for key, expected in REQUIRED_MARKERS.items():
        actual = markers.get(key)
        if actual is None:
            errors.append(f"missing marker: {key}")
        elif actual != expected:
            errors.append(f"invalid marker {key}: expected {expected}, got {actual}")

    normalized = _normalize_text(text)
    for phrase in REQUIRED_PHRASES:
        if _normalize_text(phrase) not in normalized:
            errors.append(f"missing required phrase: {phrase}")

    normalized_rollout = normalized
    search_start = 0
    previous_index = -1
    for phrase in ROLLOUT_ORDER:
        normalized_phrase = _normalize_text(phrase)
        index = normalized_rollout.find(normalized_phrase, search_start)
        if index == -1:
            errors.append(f"missing rollout order item: {phrase}")
            continue
        if index <= previous_index:
            errors.append(f"rollout order item out of order: {phrase}")
        previous_index = index
        search_start = index + len(normalized_phrase)

    errors.extend(_forbidden_claim_errors(text))

    return errors


def validate_semantic_cache_rollout_contract(text: str) -> list[str]:
    """Return stable validation errors for unsafe semantic-cache rollout contracts."""
    errors: list[str] = []
    normalized = _normalize_text(text)

    for phrase in CONTRACT_REQUIRED_PHRASES:
        if _normalize_text(phrase) not in normalized:
            errors.append(f"rollout contract missing required phrase: {phrase}")

    search_start = 0
    previous_index = -1
    for phrase in ROLLOUT_ORDER:
        normalized_phrase = _normalize_text(phrase)
        index = normalized.find(normalized_phrase, search_start)
        if index == -1:
            errors.append(f"rollout contract missing phase: {phrase}")
            continue
        if index <= previous_index:
            errors.append(f"rollout contract phase out of order: {phrase}")
        previous_index = index
        search_start = index + len(normalized_phrase)

    errors.extend(_forbidden_claim_errors(text))

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check semantic-cache gate markers.")
    parser.add_argument(
        "--doc",
        type=Path,
        default=DEFAULT_DOC,
        help="Semantic-cache gate markdown document to validate.",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
        help="Semantic-cache rollout contract markdown document to validate.",
    )
    args = parser.parse_args(argv)

    doc = args.doc
    if not doc.exists():
        print(f"ERROR: semantic-cache gate document missing: {doc}", file=sys.stderr)
        return 1

    contract = args.contract
    if not contract.exists():
        print(f"ERROR: semantic-cache rollout contract missing: {contract}", file=sys.stderr)
        return 1

    errors = validate_semantic_cache_gate(doc.read_text(encoding="utf-8"))
    errors.extend(validate_semantic_cache_rollout_contract(contract.read_text(encoding="utf-8")))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"semantic-cache gate closed: {doc}")
    print(f"semantic-cache rollout contract closed: {contract}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

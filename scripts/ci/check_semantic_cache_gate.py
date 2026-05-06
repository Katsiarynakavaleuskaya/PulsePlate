#!/usr/bin/env python3
"""Fail-closed guard for the PulsePlate semantic-cache gate document."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOC = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"

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
)

ROLLOUT_ORDER = (
    "docs contract",
    "exact/fuzzy cache",
    "bounded semantic cache for `/insight`",
    "observability / false-hit guardrails",
    "Redis/GPTCache backend only later",
)

FORBIDDEN_CLAIMS = (
    "semantic cache is implemented",
    "semantic cache is active",
    "semantic cache is enabled",
    "semantic cache is now open",
    "e1-e5 unlock semantic cache",
    "evidence graph unlocks semantic cache",
    "advisory wiki feeds product cache",
    "wiki pages are cache truth",
    "graphrag rollout approved",
    "gptcache rollout approved",
    "redis semantic cache approved",
)

MARKER_RE = re.compile(r"<!--\s*(?P<key>SEMANTIC_CACHE_[A-Z_]+):\s*(?P<value>.*?)\s*-->")


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[*_`]+", "", text)
    return re.sub(r"\s+", " ", text)


def _extract_markers(text: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    for match in MARKER_RE.finditer(text):
        markers[match.group("key")] = match.group("value").strip().lower()
    return markers


def validate_semantic_cache_gate(text: str) -> list[str]:
    """Return stable validation errors for unsafe semantic-cache gate docs."""
    errors: list[str] = []
    markers = _extract_markers(text)

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

    for claim in FORBIDDEN_CLAIMS:
        if claim in normalized:
            errors.append(f"forbidden semantic-cache claim: {claim}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check semantic-cache gate markers.")
    parser.add_argument(
        "--doc",
        type=Path,
        default=DEFAULT_DOC,
        help="Semantic-cache gate markdown document to validate.",
    )
    args = parser.parse_args(argv)

    doc = args.doc
    if not doc.exists():
        print(f"ERROR: semantic-cache gate document missing: {doc}", file=sys.stderr)
        return 1

    errors = validate_semantic_cache_gate(doc.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"semantic-cache gate closed: {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

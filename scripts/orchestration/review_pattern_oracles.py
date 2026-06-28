"""Offline deterministic review-pattern oracle helpers.

Review-pattern oracles are advisory inputs for reviewer planning. They are not
review-thread dispositions, fixed-mapping proof, or merge-readiness authority.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re

ORACLE_SCHEMA_VERSION = "review_pattern_oracles.v1"
AUTHORITY_BOUNDARY = "proposal_only_non_canonical"
_SECRETISH_RE = re.compile(
    r"(?i)(github_pat_[a-z0-9_]+|ghs_[a-z0-9_.-]+|gh[opru]_[a-z0-9_]+|"
    r"ghp_[a-z0-9_]+|sk-[a-z0-9_-]+|"
    r"\b(?:token|secret|password|api[_-]?key|github_token|gh_token)\b\s*[:=]\s*[^\s]+)"
)
REVIEW_PATTERN_ORACLE_IDS: tuple[str, ...] = (
    "schema_validator_parity",
    "fail_closed_security_edge",
    "deterministic_content_oracle",
    "canonical_route_ownership_guard",
    "evidence_hygiene_mapping_timing",
    "review_source_degraded",
)


@dataclass(frozen=True)
class ReviewPatternOracle:
    oracle_id: str
    title: str
    trigger_terms: tuple[str, ...]
    required_evidence: tuple[str, ...]
    authority_boundary: str = AUTHORITY_BOUNDARY


DEFAULT_ORACLES: tuple[ReviewPatternOracle, ...] = (
    ReviewPatternOracle(
        oracle_id="schema_validator_parity",
        title="Schema and Python validator parity",
        trigger_terms=("schema", "validator", "json schema", "contract"),
        required_evidence=("schema parity", "negative fixture", "python validator"),
    ),
    ReviewPatternOracle(
        oracle_id="fail_closed_security_edge",
        title="Fail-closed security edge",
        trigger_terms=("security", "token", "auth", "secret", "subprocess"),
        required_evidence=("fail closed", "redaction", "absolute binary", "no side effects"),
    ),
    ReviewPatternOracle(
        oracle_id="deterministic_content_oracle",
        title="Deterministic content oracle",
        trigger_terms=("deterministic", "fixture", "snapshot", "content", "report"),
        required_evidence=("stable sort", "fixture coverage", "repeatable output"),
    ),
    ReviewPatternOracle(
        oracle_id="canonical_route_ownership_guard",
        title="Canonical route ownership guard",
        trigger_terms=("route", "router", "canonical", "legacy", "duplicate"),
        required_evidence=("single owner", "compatibility alias check", "duplicate guard"),
    ),
    ReviewPatternOracle(
        oracle_id="evidence_hygiene_mapping_timing",
        title="Fixed-mapping evidence hygiene",
        trigger_terms=("fixed mapping", "review thread", "merge readiness", "bot comment"),
        required_evidence=("commit-after-comment", "disposition evidence", "no trigger-only proof"),
    ),
    ReviewPatternOracle(
        oracle_id="review_source_degraded",
        title="Degraded review-source fallback",
        trigger_terms=("degraded", "fallback", "coderabbit", "sourcery", "cubic", "review source"),
        required_evidence=("source status", "fallback path", "no merge authority"),
    ),
)


def redact_review_text(value: str) -> str:
    """Redact obvious secret-like assignments from oracle inputs."""

    return _SECRETISH_RE.sub("<redacted>", value)


def match_review_pattern_oracles(
    *,
    text: str,
    changed_paths: list[str],
    oracles: tuple[ReviewPatternOracle, ...] = DEFAULT_ORACLES,
) -> dict[str, object]:
    """Return a stable, side-effect-free oracle match report."""

    redacted_text = redact_review_text(text)
    haystack = " ".join([redacted_text, *changed_paths]).lower()
    matches: list[dict[str, object]] = []
    for oracle in oracles:
        matched_terms = [term for term in oracle.trigger_terms if term.lower() in haystack]
        if not matched_terms:
            continue
        entry = asdict(oracle)
        entry.pop("trigger_terms", None)
        entry["matched_terms"] = matched_terms
        matches.append(entry)

    fingerprint_source = "\n".join([redacted_text, *sorted(changed_paths)])
    return {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "side_effects_allowed": False,
        "posting_allowed": False,
        "thread_resolution_allowed": False,
        "merge_readiness_authority": False,
        "oracle_ids": list(REVIEW_PATTERN_ORACLE_IDS),
        "input_fingerprint": f"sha256:{sha256(fingerprint_source.encode('utf-8')).hexdigest()}",
        "matches": matches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Match PulsePlate advisory review-pattern oracles without side effects."
    )
    parser.add_argument("--text", default="", help="Review text, warning, or task goal to inspect.")
    parser.add_argument(
        "--path",
        dest="changed_paths",
        action="append",
        default=[],
        help="Changed path to include in deterministic oracle matching. Repeatable.",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            match_review_pattern_oracles(text=args.text, changed_paths=args.changed_paths),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by py_compile/CLI smoke gates.
    raise SystemExit(main())

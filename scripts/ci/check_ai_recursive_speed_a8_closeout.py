#!/usr/bin/env python3
"""Fail-closed guard for PR-A8 recursive speed optimization closeout truth."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

TITLE = "feat(ai-runtime): add philosophical speed optimization to recursive stack"
PR_1506 = {
    "number": "1506",
    "merged_at": "2026-04-23T20:41:25Z",
    "merge_date": "2026-04-23",
    "merge_commit": "".join(("19fdbd30", "98a6aef7", "80a71e94", "e94980cb", "3d0f61ee")),
    "branch": "codex/ai-recursive-speed-optimization-w1",
}
PR_1578 = {
    "number": "1578",
    "merged_at": "2026-04-29T20:32:42Z",
    "merge_date": "2026-04-29",
    "merge_commit": "".join(("37995a6e", "8d4e9451", "b85e7e62", "84e9bd0c", "d5afff45")),
    "branch": "codex/wave6-a8-recursive-speed-optimization",
}

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
DEFAULT_PR1506_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1506_FIXED_MAPPING.md"
DEFAULT_PR1578_MAPPING = REPO_ROOT / "docs" / "review" / "PR_1578_FIXED_MAPPING.md"
DEFAULT_SEMANTIC_CACHE_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

REQUIRED_SYMBOLS = {
    "core/ai/insight_runtime.py": (
        "RecursiveRolloutPolicy",
        "_build_recursive_optimization_hints",
    ),
    "core/rag/contracts.py": ("RecursiveOptimizationHints",),
    "core/rag/orchestration.py": ("recursive_optimization_hints",),
    "core/rag/recursive_retrieval.py": (
        "_should_short_circuit_from_hints",
        "early_stop_aggressive_short_circuit",
        "early_stop_pragmatic_usefulness",
    ),
    "app/services/insight_runtime.py": ("recursive_optimization_hints",),
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

NEGATION_RE = re.compile(
    r"\b(no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|"
    r"out\s+of\s+scope|deferred|remains?\s+closed|remained\s+closed|"
    r"gate[-\s]+closed|without|no\s+default)\b",
    re.I,
)
FORBIDDEN_SURFACE_PATTERN = (
    r"semantic[-\s]?(?:cache|caching)|semanticcache|redis|gpt[-\s]?cache|"
    r"graph[-\s]?rag|context[-\s]?manifest|contextmanifest|"
    r"(?:db|database)\s+persistence|public\s+(?:routes?|endpoints?|api)(?:\s+changes?)?|"
    r"openapi|dtos?|recursive\s+learning|chain[-\s]?of[-\s]?thought|"
    r"tree[-\s]?of[-\s]?thought|default\s+activation|default[-\s]?on|"
    r"production[-\s]?ready|rollout[-\s]?ready"
)

LOCAL_NEGATED_CLAIM_RE = re.compile(
    r"\b(no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|"
    r"out\s+of\s+scope|deferred|remains?\s+closed|remained\s+closed|"
    r"gate[-\s]+closed|without|no\s+default)\b"
    r"[^,;.]{0,140}"
    rf"\b({FORBIDDEN_SURFACE_PATTERN})\b",
    re.I,
)
BENCHMARK_CLAIM_RE = re.compile(
    r"(?=.*\b(?:latency|quality|reduction|maintained|accuracy)\b)"
    r"(?=.*(?:\d+(?:-\d+)?%|>=?\s*\d+%|<=?\s*\d+%)).+",
    re.I,
)
FORBIDDEN_SURFACE_RE = re.compile(rf"\b({FORBIDDEN_SURFACE_PATTERN})\b", re.I)
POSITIVE_ACTION_RE = re.compile(
    r"\b(opens?|opened|opening|enables?|enabled|implements?|implemented|approves?|approved|"
    r"authorizes?|authorized|permits?|permitted|allows?|allowed|adds?|added|ships?|shipped|"
    r"selects?|selected|activates?|activated|activating|rolls?\s+out|"
    r"turns?\s+(?:[A-Za-z0-9_/-]+\s+){0,8}on(?:\s+by\s+default)?|"
    r"wired|wires|"
    r"production[-\s]?ready|rollout[-\s]?ready|default[-\s]?on|"
    r"default\s+activation|active|live)\b",
    re.I,
)
A8_REF_RE = re.compile(r"\b(?:pr[-\s]?a8|pr\s*#?\s*(?:1506|1578)|#(?:1506|1578))\b", re.I)
STALE_A8_RE = re.compile(
    r"\b(pr[-\s]?a8|#1506|#1578)\b.*\b(pending|in\s+progress|active|"
    r"next\s+logical|will\s+implement|implementation\s+lane|open\s+runtime)\b",
    re.I,
)
STALE_A8_REVERSED_RE = re.compile(
    r"\b(pending|in\s+progress|active|next\s+logical|will\s+implement|"
    r"implementation\s+lane|open\s+runtime)\b.*\b(pr[-\s]?a8|#1506|#1578)\b",
    re.I,
)
CONTRAST_SPLIT_RE = re.compile(r"\b(?:but|however|though|although|yet|and)\b|[;]", re.I)
OVERCLAIM_RE = re.compile(
    r"\b(proves?|proved|scientifically\s+validated|validated|guarantees?|"
    r"guaranteed|maintains?|maintained|achieves?|achieved|delivers?|delivered)\b",
    re.I,
)


def _read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: unable to read: {exc}")
        return ""


def _normalize(text: str) -> str:
    return text.translate(UNICODE_TRANSLATION)


def _sentences(text: str) -> list[str]:
    normalized = _normalize(text)
    parts: list[str] = []
    for paragraph in re.split(r"\n{2,}", normalized):
        soft_wrapped = re.sub(r"[ \t]*\n[ \t]*", " ", paragraph.strip())
        parts.extend(re.split(r"(?<=[.!?])\s+", soft_wrapped))
    return [part.strip() for part in parts if part.strip()]


def _claim_is_locally_negated(text: str) -> bool:
    return LOCAL_NEGATED_CLAIM_RE.search(_normalize(text)) is not None


def _surface_claim_is_negated(text: str) -> bool:
    normalized = _normalize(text)
    if _claim_is_locally_negated(normalized):
        return True
    return (
        re.search(
            rf"\b({FORBIDDEN_SURFACE_PATTERN})\b[^,;.]{{0,100}}"
            r"\b(?:is|are|was|were|remains?|remained)?\s*"
            r"(?:not|never)\s+"
            r"(?:active|live|enabled|opened|allowed|approved|selected|"
            r"production[-\s]?ready|rollout[-\s]?ready)\b",
            normalized,
            re.I,
        )
        is not None
    )


def _default_repo_path(repo_root: Path, default_path: Path) -> Path:
    return repo_root / default_path.relative_to(REPO_ROOT)


def _find_pr_a8_section(roadmap_text: str) -> str:
    normalized = _normalize(roadmap_text)
    match = re.search(r"^## PR-A8\b.*?(?=^---\s*$|^## PR-A9\b|\Z)", normalized, re.M | re.S)
    return match.group(0) if match else ""


def _find_anchor_section(text: str, anchor: str) -> str:
    normalized = _normalize(text)
    match = re.search(
        rf'^<a id="{re.escape(anchor)}"></a>.*?(?=^<a id="|\Z)',
        normalized,
        re.M | re.S,
    )
    return match.group(0) if match else ""


def _require_contains(text: str, needle: str, label: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"missing {label}: {needle}")


def _validate_pr_evidence(
    *, combined_text: str, mapping_text: str, evidence: dict[str, str], errors: list[str]
) -> None:
    number = evidence["number"]
    _require_contains(combined_text, f"#{number}", f"PR #{number} active evidence", errors)
    for needle, label in (
        (f"#{number}", f"PR #{number} number"),
        (TITLE, f"PR #{number} title"),
        (evidence["merged_at"], f"PR #{number} merge timestamp"),
        (evidence["merge_date"], f"PR #{number} merge date"),
        (evidence["merge_commit"], f"PR #{number} merge commit"),
        (evidence["branch"], f"PR #{number} original branch"),
    ):
        _require_contains(mapping_text, needle, label, errors)


def _validate_required_symbols(repo_root: Path, errors: list[str]) -> None:
    for relpath, symbols in REQUIRED_SYMBOLS.items():
        path = repo_root / relpath
        text = _read_text(path, errors)
        for symbol in symbols:
            _require_contains(text, symbol, f"{relpath} landed symbol", errors)


def _validate_semantic_cache_gate(gate_text: str, errors: list[str]) -> None:
    for marker, expected in REQUIRED_GATE_MARKERS.items():
        pattern = re.compile(rf"{re.escape(marker)}:\s*([A-Za-z0-9_-]+)")
        match = pattern.search(gate_text)
        if match is None:
            errors.append(f"missing semantic-cache marker: {marker}")
            continue
        actual = match.group(1).lower()
        if actual != expected:
            errors.append(f"{marker} expected {expected!r}, got {actual!r}")


def _validate_parent_checkbox(ledger_text: str, errors: list[str]) -> None:
    if not re.search(r"- \[ \] P1: Recursive methods for LLM/RAG/AI assistant", ledger_text):
        errors.append("parent P1 checkbox is closed or missing for recursive methods")


def _validate_roadmap_section(roadmap_text: str, errors: list[str]) -> None:
    section = _find_pr_a8_section(roadmap_text)
    if not section:
        errors.append("missing PR-A8 roadmap section")
        return
    for heading in (
        "#### Current status",
        "#### Landed and hardened scope",
        "#### Benchmark boundary",
        "#### Out of scope",
    ):
        if heading not in section:
            errors.append(f"PR-A8 roadmap section missing heading: {heading}")
    if "#### In scope" in section:
        errors.append("PR-A8 roadmap section still uses implementation in-scope wording")
    _validate_stale_a8_wording(section, errors)


def _validate_stale_a8_wording(active_text: str, errors: list[str]) -> None:
    for sentence in _sentences(active_text):
        sentence_has_a8 = A8_REF_RE.search(sentence) is not None
        for clause in CONTRAST_SPLIT_RE.split(sentence):
            residual_clause = re.sub(
                r"\b(?:not|no|never|does\s+not|do\s+not|must\s+not|cannot|can't)\b"
                r"[^,;.]{0,100}\b(?:pending|in\s+progress|"
                r"active(?:\s+implementation\s+lane)?|implementation\s+lane)\b",
                " ",
                clause,
                flags=re.I,
            )
            contextual_clause = (
                f"PR-A8 {residual_clause}"
                if sentence_has_a8 and not A8_REF_RE.search(residual_clause)
                else residual_clause
            )
            if STALE_A8_RE.search(contextual_clause) or STALE_A8_REVERSED_RE.search(
                contextual_clause
            ):
                errors.append(f"stale PR-A8 active/pending wording: {sentence}")
                break


def _validate_mapping_closeout(mapping_text: str, number: str, errors: list[str]) -> None:
    if "## Post-Merge Closeout" not in mapping_text:
        errors.append(f"PR #{number} mapping missing Post-Merge Closeout section")
    if "historical evidence only" not in mapping_text.lower():
        errors.append(f"PR #{number} mapping must mark old readiness checklist as historical")


def _validate_forbidden_claims(active_text: str, errors: list[str]) -> None:
    for sentence in _sentences(active_text):
        sentence_has_a8 = A8_REF_RE.search(sentence) is not None
        for clause in CONTRAST_SPLIT_RE.split(sentence):
            residual_clause = LOCAL_NEGATED_CLAIM_RE.sub(" ", clause)
            if _surface_claim_is_negated(residual_clause):
                continue
            if not FORBIDDEN_SURFACE_RE.search(residual_clause):
                continue
            has_a8_ref = A8_REF_RE.search(residual_clause) is not None or sentence_has_a8
            if not has_a8_ref:
                continue
            has_direct_forbidden_status = POSITIVE_ACTION_RE.search(residual_clause) is not None
            if has_a8_ref and has_direct_forbidden_status:
                errors.append(f"forbidden PR-A8 runtime expansion claim: {sentence}")
                break
            if (
                re.search(r"\bsemantic[-\s]?cache|semanticcache\b", residual_clause, re.I)
                and has_direct_forbidden_status
            ):
                errors.append(f"semantic cache direct activation claim: {sentence}")
                break
            if re.search(r"\b(redis|gpt[-\s]?cache)\b", residual_clause, re.I) and re.search(
                r"\b(approved|selected|production[-\s]?ready|rollout[-\s]?ready|enabled)\b",
                residual_clause,
                re.I,
            ):
                errors.append(f"backend rollout approval claim: {sentence}")
                break


def _validate_benchmark_claims(active_text: str, errors: list[str]) -> None:
    for sentence in _sentences(active_text):
        if A8_REF_RE.search(sentence) is None:
            continue
        if not BENCHMARK_CLAIM_RE.search(sentence):
            continue
        claim_clauses = [
            clause
            for clause in CONTRAST_SPLIT_RE.split(sentence)
            if BENCHMARK_CLAIM_RE.search(clause)
        ]
        if any(_benchmark_clause_is_overclaim(clause) for clause in claim_clauses):
            errors.append(f"unvalidated benchmark claim: {sentence}")
            continue
        if not all(_benchmark_claim_is_qualified(clause) for clause in claim_clauses):
            errors.append(f"unvalidated benchmark claim: {sentence}")


def _benchmark_claim_is_qualified(text: str) -> bool:
    if _benchmark_clause_is_negated_disclaimer(text):
        return True
    lowered = text.lower()
    has_hypothesis = (
        "hypothesis target" in lowered
        or "hypothesized impact" in lowered
        or "hypothesis" in lowered
        or "гипотез" in lowered
    )
    has_validation = (
        "requires benchmark validation" in lowered
        or "benchmark validation" in lowered
        or "benchmark-validated" in lowered
        or "benchmark hypotheses" in lowered
        or "валидац" in lowered
        or "валидацией" in lowered
    )
    return has_hypothesis and has_validation


def _benchmark_clause_is_overclaim(text: str) -> bool:
    if not _has_unnegated_overclaim(text):
        return False
    if A8_REF_RE.search(text):
        return True
    return not _benchmark_claim_is_qualified(text)


def _benchmark_clause_is_negated_disclaimer(text: str) -> bool:
    return (
        A8_REF_RE.search(text) is not None
        and _has_negated_overclaim(text)
        and not _has_unnegated_overclaim(text)
    )


def _has_negated_overclaim(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        _overclaim_match_is_negated(normalized, match)
        for match in OVERCLAIM_RE.finditer(normalized)
    )


def _has_unnegated_overclaim(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        not _overclaim_match_is_negated(normalized, match)
        for match in OVERCLAIM_RE.finditer(normalized)
    )


def _overclaim_match_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 100) : match.start()]
    return (
        re.search(
            r"\b(?:does\s+not|do\s+not|not|never|cannot|can't|doesn't)\b[^,;.]*$",
            prefix,
            re.I,
        )
        is not None
    )


def validate_closeout(
    *,
    repo_root: Path = REPO_ROOT,
    ledger_path: Path | None = None,
    roadmap_path: Path | None = None,
    mapping1506_path: Path | None = None,
    mapping1578_path: Path | None = None,
    semantic_cache_gate_path: Path | None = None,
) -> list[str]:
    """Return closeout contract errors; empty means pass."""

    errors: list[str] = []
    ledger = _read_text(ledger_path or _default_repo_path(repo_root, DEFAULT_LEDGER), errors)
    roadmap = _read_text(roadmap_path or _default_repo_path(repo_root, DEFAULT_ROADMAP), errors)
    mapping1506 = _read_text(
        mapping1506_path or _default_repo_path(repo_root, DEFAULT_PR1506_MAPPING), errors
    )
    mapping1578 = _read_text(
        mapping1578_path or _default_repo_path(repo_root, DEFAULT_PR1578_MAPPING), errors
    )
    gate = _read_text(
        semantic_cache_gate_path or _default_repo_path(repo_root, DEFAULT_SEMANTIC_CACHE_GATE),
        errors,
    )

    normalized_ledger = _normalize(ledger)
    normalized_roadmap = _normalize(roadmap)
    normalized_mapping1506 = _normalize(mapping1506)
    normalized_mapping1578 = _normalize(mapping1578)
    combined = "\n".join(
        (
            normalized_ledger,
            normalized_roadmap,
            normalized_mapping1506,
            normalized_mapping1578,
        )
    )
    roadmap_a8_section = _find_pr_a8_section(normalized_roadmap)
    recursive_ledger_section = _find_anchor_section(
        normalized_ledger, "ledger-p1-recursive-methods"
    )
    philosophy_ledger_section = _find_anchor_section(
        normalized_ledger, "ledger-p1-philosophical-logic"
    )
    stale_scan_text = "\n".join(
        (
            normalized_roadmap,
            normalized_ledger,
            normalized_mapping1506,
            normalized_mapping1578,
        )
    )
    claim_scan_text = "\n".join(
        (normalized_roadmap, normalized_ledger, normalized_mapping1506, normalized_mapping1578)
    )

    _validate_pr_evidence(
        combined_text=combined,
        mapping_text=normalized_mapping1506,
        evidence=PR_1506,
        errors=errors,
    )
    _validate_pr_evidence(
        combined_text=combined,
        mapping_text=normalized_mapping1578,
        evidence=PR_1578,
        errors=errors,
    )
    _validate_required_symbols(repo_root, errors)
    _validate_semantic_cache_gate(gate, errors)
    _validate_parent_checkbox(normalized_ledger, errors)
    _validate_roadmap_section(normalized_roadmap, errors)
    _validate_stale_a8_wording(stale_scan_text, errors)
    _validate_mapping_closeout(normalized_mapping1506, "1506", errors)
    _validate_mapping_closeout(normalized_mapping1578, "1578", errors)
    _validate_forbidden_claims(claim_scan_text, errors)
    _validate_benchmark_claims(claim_scan_text, errors)

    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--roadmap", type=Path, default=None)
    parser.add_argument("--mapping-1506", type=Path, default=None)
    parser.add_argument("--mapping-1578", type=Path, default=None)
    parser.add_argument("--semantic-cache-gate", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    errors = validate_closeout(
        repo_root=args.repo_root,
        ledger_path=args.ledger,
        roadmap_path=args.roadmap,
        mapping1506_path=args.mapping_1506,
        mapping1578_path=args.mapping_1578,
        semantic_cache_gate_path=args.semantic_cache_gate,
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("OK: PR-A8 recursive speed optimization closeout remains reconciled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

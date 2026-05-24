#!/usr/bin/env python3
"""Fail-closed guard for PR-A1b PRO quota closeout truth."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]

PR_1379 = {
    "number": "1379",
    "title": "feat(ai-runtime): implement insight fallback chain and readiness visibility",
    "merged_at": "2026-04-10T12:08:46Z",
    "merge_date": "2026-04-10",
    "merge_commit": "".join(("1ddf8c67", "78ca1f13", "c2bfce2e", "052db540", "9e8d06ba")),
    "branch": "feat/insight-fallback-chain",
}
PR_1461 = {
    "number": "1461",
    "title": "docs(roadmap): reconcile landed PRO quota truth for Wave 6 A1b",
    "merged_at": "2026-04-19T11:34:45Z",
    "merge_date": "2026-04-19",
    "merge_commit": "".join(("cd01d9c6", "db898132", "02f85b8b", "9f4c8378", "e72380ea")),
    "branch": "codex/wave6-a1b-pro-quota-reconciliation",
}
PR_1466 = {
    "number": "1466",
    "title": "Codex/pr1461 mapping fix",
    "merged_at": "2026-04-19T11:34:46Z",
    "merge_date": "2026-04-19",
    "merge_commit": "".join(("fa0979e7", "34b88575", "e01e3eca", "9ddd4d57", "ade86c05")),
    "branch": "codex/pr1461-mapping-fix",
}

DEFAULT_LEDGER = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
DEFAULT_PACKET = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "WAVE6_A1B_PRO_QUOTA_RECONCILIATION_TASK_PACKET_2026-04-17.md"
)
DEFAULT_MAPPING_1461 = REPO_ROOT / "docs" / "review" / "PR_1461_FIXED_MAPPING.md"
DEFAULT_SEMANTIC_CACHE_GATE = (
    REPO_ROOT / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
)

REQUIRED_GATE_MARKERS = {
    "SEMANTIC_CACHE_GATE_STATUS": "closed",
    "SEMANTIC_CACHE_ALLOWED_RUNTIME": "false",
    "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED": "false",
    "SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE": "true",
}

REQUIRED_RUNTIME_MARKERS = {
    "app/security/llm_monthly_quota.py": (
        'PRO_TIER = "PRO"',
        "PRO_TIER: _PRO_LIMIT_ENV",
        "def require_pro_llm_monthly_limit",
        "def attempt_consume_llm_monthly_quota",
        "tier: str",
    ),
    "app/bootstrap/startup_guards.py": ("require_pro_llm_monthly_limit()",),
    "app/routers/cbt_insight.py": ("Depends(require_pro_tier)",),
    "app/services/fitchef_runtime.py": (
        "attempt_consume_llm_monthly_quota",
        "tier=effective_tier",
    ),
    "tests/test_cbt_insight_api.py": (
        "test_pro_tier_accepted_when_feature_enabled",
        "test_unsafe_query_rejected_before_rag_and_quota",
        "test_missing_transparency_registry_returns_503_without_consuming_quota",
        "test_incomplete_transparency_registry_returns_503_without_consuming_quota",
    ),
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

PR_A1B_TOKEN_RE = re.compile(
    r"\b(?:pr[-\s]?a1b|a1b|pr\s*#?\s*(?:1461|1466)|#(?:1461|1466))\b", re.I
)
CLAUSE_SPLIT_RE = re.compile(
    r"\b(?:but|however|though|although|yet|while|whereas|therefore|thus|so|hence|"
    r"and|also|plus)\b|[;]",
    re.I,
)
SOFT_SPLIT_RE = re.compile(r"[,()]")
NEGATION_RE = re.compile(
    r"\b(no|not|never|does\s+not|do\s+not|must\s+not|cannot|can't|"
    r"without|out\s+of\s+scope|deferred|blocked|closed|remains?\s+closed|"
    r"historical|already[-\s]+landed)\b",
    re.I,
)
SEMANTIC_SURFACE_RE = re.compile(
    r"\b(semantic[-\s]?cache|semanticcache|redis|gpt[-\s]?cache|graph[-\s]?rag|"
    r"context[-\s]?manifest|contextmanifest|embeddings?|vector\s+search|"
    r"db\s+persistence|database\s+persistence|cache\s+serving|serving\s+cache)\b",
    re.I,
)
SEMANTIC_ACTION_RE = re.compile(
    r"\b(opened|opens|enable|enabled|enables|active|activate|activated|"
    r"approved|approves|select|selected|wired|wires|implements?|implemented|"
    r"available|serving[-\s]?ready|production[-\s]?ready|rollout[-\s]?ready|"
    r"default[-\s]?on|default\s+activation|cacheable)\b",
    re.I,
)
RUNTIME_SURFACE_RE = re.compile(
    r"\b(runtime|quota\s+(?:logic|runtime|implementation|enforcement)|"
    r"pro\s+quota|provider|auth|billing|entitlement|openapi|dtos?|"
    r"public\s+(?:route|routes|api|endpoint|endpoints)|db|database)\b",
    re.I,
)
RUNTIME_ACTION_RE = re.compile(
    r"\b(implements?|implemented|adds?|added|changes?|changed|reopens?|reopened|"
    r"wires?|wired|rolls?\s+out|enforces?|enforced|introduces?|introduced|"
    r"activates?|activated|ships?|shipped)\b",
    re.I,
)
LOCAL_PATH_RE = re.compile(r"(/Users/|(?:^|[\s`])worktrees/|artifacts/orchestration)")

STALE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("A1b in-progress status", re.compile(r"\bA1b\b[^.\n]{0,120}\bin\s+progress\b", re.I)),
    (
        "A1b next canonical slice",
        re.compile(r"\bA1b\b[^.\n]{0,160}\bnext\s+canonical\s+slice\b", re.I),
    ),
    (
        "A1b next lane claim",
        re.compile(
            r"\bA1b\b[^.\n]{0,160}\bnext\s+(?:user[-\s]+owned\s+)?(?:Wave\s+6\s+)?lane\b", re.I
        ),
    ),
    ("A1b draft lane claim", re.compile(r"\b(?:draft\s+PR|may\s+open\s+in\s+draft)\b", re.I)),
    (
        "A1b late-rebase active claim",
        re.compile(
            r"\b(?:must\s+late[-\s]+rebase|late[-\s]+rebase\s+onto|merge-readiness\s+is\s+forbidden)\b",
            re.I,
        ),
    ),
    (
        "A1b will reconcile future claim",
        re.compile(r"\bA1b\b[^.\n]{0,160}\bwill\s+reconcile\b", re.I),
    ),
    (
        "A1b active pre-open packet",
        re.compile(r"\bpre[-\s]+open\s+packet\s+for\s+the\s+next\b", re.I),
    ),
)


def _read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_display(path)}: unable to read: {exc}")
        return ""


def _display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return path.name


def _normalize(text: str) -> str:
    return text.translate(UNICODE_TRANSLATION)


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize(text)).strip()


def _slice(text: str, start: str, end_pattern: str, *, label: str, errors: list[str]) -> str:
    start_index = text.find(start)
    if start_index == -1:
        errors.append(f"{label}: missing start anchor {start!r}")
        return ""
    match = re.search(end_pattern, text[start_index + len(start) :])
    if not match:
        errors.append(f"{label}: missing end anchor {end_pattern!r}")
        return text[start_index:]
    end_index = start_index + len(start) + match.start()
    return text[start_index:end_index]


def _optional_slice(text: str, start: str, end_pattern: str) -> str:
    start_index = text.find(start)
    if start_index == -1:
        return ""
    match = re.search(end_pattern, text[start_index + len(start) :])
    if not match:
        return text[start_index:]
    end_index = start_index + len(start) + match.start()
    return text[start_index:end_index]


def _require_tokens(text: str, label: str, tokens: tuple[str, ...], errors: list[str]) -> None:
    compacted = _compact(text).lower()
    for token in tokens:
        if token.lower() not in compacted:
            errors.append(f"{label}: missing {token}")


def _require_pr_evidence(text: str, label: str, pr: dict[str, str], errors: list[str]) -> None:
    _require_tokens(
        text,
        label,
        (
            f"PR #{pr['number']}",
            pr["merge_date"],
            pr["merged_at"],
            pr["merge_commit"],
            pr["branch"],
        ),
        errors,
    )


def _gate_markers(text: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    for match in re.finditer(r"<!--\s*([A-Z0-9_]+):\s*([^>]+?)\s*-->", text):
        markers[match.group(1)] = match.group(2).strip()
    return markers


def _sentences(text: str) -> list[str]:
    normalized = _normalize(text)
    paragraphs = re.split(r"\n{2,}", normalized)
    units: list[str] = []
    for paragraph in paragraphs:
        line = re.sub(r"[ \t]*\n[ \t]*", " ", paragraph.strip())
        units.extend(re.split(r"(?<=[.!?])\s+", line))
    return [unit.strip() for unit in units if unit.strip()]


def _clauses(text: str) -> list[str]:
    clauses: list[str] = []
    for sentence in _sentences(text):
        for part in CLAUSE_SPLIT_RE.split(sentence):
            clauses.extend(SOFT_SPLIT_RE.split(part))
    return [clause.strip() for clause in clauses if clause.strip()]


def _has_local_negation(clause: str) -> bool:
    return bool(NEGATION_RE.search(clause))


def _check_stale_wording(text: str, label: str, errors: list[str]) -> None:
    for name, pattern in STALE_PATTERNS:
        if pattern.search(text):
            errors.append(f"{label}: stale active wording: {name}")


def _check_forbidden_claims(text: str, label: str, errors: list[str]) -> None:
    for sentence in _sentences(text):
        sentence_has_a1b = bool(PR_A1B_TOKEN_RE.search(sentence))
        for part in CLAUSE_SPLIT_RE.split(sentence):
            for clause in SOFT_SPLIT_RE.split(part):
                compacted = _compact(clause)
                if not compacted:
                    continue
                if SEMANTIC_SURFACE_RE.search(compacted) and SEMANTIC_ACTION_RE.search(compacted):
                    if not _has_local_negation(compacted):
                        errors.append(
                            f"{label}: semantic-cache/runtime-expansion claim is not fail-closed: {compacted}"
                        )
                has_a1b_context = sentence_has_a1b or bool(PR_A1B_TOKEN_RE.search(compacted))
                if has_a1b_context and RUNTIME_SURFACE_RE.search(compacted):
                    if RUNTIME_ACTION_RE.search(compacted) and not _has_local_negation(compacted):
                        errors.append(
                            f"{label}: A1b runtime-scope expansion claim is not fail-closed: {compacted}"
                        )


def _check_local_path_leakage(text: str, label: str, errors: list[str]) -> None:
    if LOCAL_PATH_RE.search(text):
        errors.append(f"{label}: closeout text leaks local artifact/worktree path")


def _check_runtime_markers(repo_root: Path, errors: list[str]) -> None:
    for relpath, markers in REQUIRED_RUNTIME_MARKERS.items():
        path = repo_root / relpath
        text = _read_text(path, errors)
        for marker in markers:
            if marker not in text:
                errors.append(f"{relpath}: missing landed runtime/test marker {marker!r}")


def _check_mapping(mapping: str, errors: list[str]) -> None:
    _require_pr_evidence(mapping, "PR_1461_FIXED_MAPPING post-merge", PR_1461, errors)
    _require_pr_evidence(mapping, "PR_1461_FIXED_MAPPING PR #1466 evidence", PR_1466, errors)
    _require_tokens(
        mapping,
        "PR_1461_FIXED_MAPPING",
        (
            "## Post-Merge Closeout",
            "## Historical Merge Readiness",
            "State: `MERGED`",
            "historical evidence only",
            "PR #1466 did not create a separate fixed-mapping artifact",
        ),
        errors,
    )
    if re.search(r"^## Merge Readiness\b", mapping, re.M):
        errors.append("PR_1461_FIXED_MAPPING: stale active ## Merge Readiness section remains")
    if re.search(r"^\s*[-*+]\s+\[\s\]", mapping, re.M):
        errors.append("PR_1461_FIXED_MAPPING: unchecked historical readiness checklist remains")


def validate_closeout(
    *,
    repo_root: Path = REPO_ROOT,
    ledger: Path | None = None,
    roadmap: Path | None = None,
    packet: Path | None = None,
    mapping_1461: Path | None = None,
    semantic_cache_gate: Path | None = None,
) -> list[str]:
    repo_root = repo_root.resolve()
    errors: list[str] = []
    ledger_path = ledger or repo_root / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
    roadmap_path = (
        roadmap or repo_root / "docs" / "roadmap" / "PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md"
    )
    packet_path = (
        packet
        or repo_root
        / "docs"
        / "orchestration"
        / "WAVE6_A1B_PRO_QUOTA_RECONCILIATION_TASK_PACKET_2026-04-17.md"
    )
    mapping_path = mapping_1461 or repo_root / "docs" / "review" / "PR_1461_FIXED_MAPPING.md"
    gate_path = (
        semantic_cache_gate
        or repo_root / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    )

    ledger_text = _read_text(ledger_path, errors)
    roadmap_text = _read_text(roadmap_path, errors)
    packet_text = _read_text(packet_path, errors)
    mapping_text = _read_text(mapping_path, errors)
    gate_text = _read_text(gate_path, errors)

    ledger_item = _slice(
        ledger_text,
        '<a id="ledger-p1-pro-monthly-quota-ledger-reconciliation"></a>',
        r"\n<a id=",
        label="A1b ledger item",
        errors=errors,
    )
    roadmap_section = _slice(
        roadmap_text,
        "## PR-A1b ",
        r"\n---\n\n## PR-A2",
        label="A1b roadmap section",
        errors=errors,
    )

    active_docs = "\n\n".join((ledger_item, roadmap_section, packet_text, mapping_text))
    for label, text in (
        ("A1b ledger item", ledger_item),
        ("A1b roadmap section", roadmap_section),
        ("A1b packet", packet_text),
        ("PR_1461_FIXED_MAPPING", mapping_text),
    ):
        _check_stale_wording(text, label, errors)
        if label == "PR_1461_FIXED_MAPPING":
            post_merge = _optional_slice(
                text,
                "## Post-Merge Closeout",
                r"\n## Historical Merge Readiness",
            )
            _check_forbidden_claims(post_merge, f"{label} post-merge closeout", errors)
        else:
            _check_forbidden_claims(text, label, errors)
        _check_local_path_leakage(text, label, errors)

    _require_tokens(
        ledger_item,
        "A1b ledger item",
        (
            "- [x] P1: Reconcile PRO monthly quota ledger with live runtime truth",
            "Status: Closed",
            "docs/governance closeout only",
            "PR-A1b does not reopen runtime quota logic",
            "closed / false / false / true",
        ),
        errors,
    )
    _require_tokens(
        roadmap_section,
        "A1b roadmap section",
        (
            "Current status",
            "Closed via PR #1461",
            "follow-up PR #1466",
            "docs/governance closeout",
            "PR-A1b does not reopen runtime quota logic",
        ),
        errors,
    )
    _require_tokens(
        packet_text,
        "A1b packet",
        (
            "Historical closeout status",
            "This packet is historical",
            "PR #1461",
            "PR #1466",
            "ready-for-review closeout",
        ),
        errors,
    )

    for section_label, section_text in (
        ("A1b ledger item", ledger_item),
        ("A1b roadmap section", roadmap_section),
    ):
        _require_pr_evidence(section_text, f"{section_label} PR #1379 evidence", PR_1379, errors)
        _require_pr_evidence(section_text, f"{section_label} PR #1461 evidence", PR_1461, errors)
        _require_pr_evidence(section_text, f"{section_label} PR #1466 evidence", PR_1466, errors)

    _check_mapping(mapping_text, errors)

    markers = _gate_markers(gate_text)
    for marker, expected in REQUIRED_GATE_MARKERS.items():
        actual = markers.get(marker)
        if actual != expected:
            errors.append(
                f"semantic-cache gate marker {marker}: expected {expected!r}, got {actual!r}"
            )

    _check_runtime_markers(repo_root, errors)

    if "PR #1466" not in active_docs:
        errors.append("A1b closeout docs: missing PR #1466 evidence")

    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--mapping-1461", type=Path, default=DEFAULT_MAPPING_1461)
    parser.add_argument("--semantic-cache-gate", type=Path, default=DEFAULT_SEMANTIC_CACHE_GATE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_closeout(
        repo_root=args.repo_root,
        ledger=args.ledger,
        roadmap=args.roadmap,
        packet=args.packet,
        mapping_1461=args.mapping_1461,
        semantic_cache_gate=args.semantic_cache_gate,
    )
    if errors:
        print("PR-A1b closeout guard failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("PR-A1b closeout guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

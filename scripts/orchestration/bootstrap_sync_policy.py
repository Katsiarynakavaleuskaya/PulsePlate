"""Canonical sync-policy helpers for task bootstrap.

RU: Централизует sync-policy константы и matcher-правила для bootstrap packet.
EN: Centralizes sync-policy constants and matcher rules for the bootstrap packet.
"""

from __future__ import annotations

BACKLOG_SIGNAL_TERMS: tuple[str, ...] = (
    "backlog",
    "ledger",
    "roadmap",
    "defer",
    "deferred",
    "follow-up",
    "follow up",
)

IMPLEMENTATION_PATH_PREFIXES: tuple[str, ...] = (
    "app/",
    "core/",
    "scripts/",
    "frontend/",
    "ios/",
)

PRIVILEGED_REVIEW_PREFIXES: tuple[str, ...] = (
    ".github/workflows/",
    "ios/fastlane/",
    "scripts/orchestration/",
    "scripts/ci/",
    "docs/orchestration/",
    "docs/review/",
)

AGENT_CONTRACT_PATH_MARKERS: tuple[str, ...] = (
    "AGENTS.md",
    ".cursor/agents/",
    "SKILL.md",
)

BACKLOG_LEDGER_PATH = "docs/roadmap/backlog_ledger.md"
DOCS_PATH_PREFIX = "docs/"


def matches_any_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    """Return True when a path matches a canonical prefix exactly or by subtree.

    RU: Совпадение считается валидным и для корня, и для вложенного пути.
    EN: A match is valid for both the root directory and any nested path.
    """

    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def requires_security_review(candidate_paths: list[str] | tuple[str, ...]) -> bool:
    """Return True when the task touches privileged review surfaces.

    RU: Привилегированные поверхности всегда тянут security-review path.
    EN: Privileged surfaces always force the security-review path.
    """

    return any(matches_any_prefix(path, PRIVILEGED_REVIEW_PREFIXES) for path in candidate_paths)


def needs_backlog_update(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
) -> bool:
    """Return True when backlog bookkeeping markers are present.

    RU: Сигнал определяется по текстовым маркерам и explicit backlog ledger path.
    EN: The signal is derived from text markers plus the explicit backlog ledger path.
    """

    haystack = " ".join(
        [
            goal.strip().lower(),
            task_class.strip().lower(),
            *(path.lower() for path in candidate_paths),
        ]
    )
    if any(term in haystack for term in BACKLOG_SIGNAL_TERMS):
        return True
    return any(BACKLOG_LEDGER_PATH in path.lower() for path in candidate_paths)


def needs_docs_sync(candidate_paths: list[str] | tuple[str, ...]) -> bool:
    """Return True when implementation paths changed without a docs path.

    RU: Кодовые изменения без docs-path должны поднять deterministic docs sync flag.
    EN: Code changes without a docs path must raise the deterministic docs sync flag.
    """

    has_implementation_path = any(
        matches_any_prefix(path, IMPLEMENTATION_PATH_PREFIXES) for path in candidate_paths
    )
    has_docs_path = any(
        path == "docs" or path.startswith(DOCS_PATH_PREFIX) for path in candidate_paths
    )
    return has_implementation_path and not has_docs_path


def needs_agents_sync(candidate_paths: list[str] | tuple[str, ...]) -> bool:
    """Return True when AGENTS or SKILL contract files are in scope.

    RU: Сигнал ограничен каноническими agent-contract путями и не шире.
    EN: The signal is intentionally limited to canonical agent-contract paths.
    """

    return any(
        path == AGENT_CONTRACT_PATH_MARKERS[0]
        or path.endswith(f"/{AGENT_CONTRACT_PATH_MARKERS[0]}")
        or path.startswith(AGENT_CONTRACT_PATH_MARKERS[1])
        or path == AGENT_CONTRACT_PATH_MARKERS[2]
        or path.endswith(f"/{AGENT_CONTRACT_PATH_MARKERS[2]}")
        for path in candidate_paths
    )

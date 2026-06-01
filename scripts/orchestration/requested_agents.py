"""Shared requested-agent helpers for deterministic orchestration routing.

RU: Общие хелперы для requested-agent routing без дрейфа между entrypoints.
EN: Shared helpers that keep requested-agent handling aligned across entrypoints.
"""

from __future__ import annotations

from collections.abc import Iterable

POST_OPEN_QA_AGENT = "qa-engineer-agent"
POST_OPEN_BUG_HUNTER_AGENT = "bug-hunter"
POST_OPEN_SECURITY_AUDITOR_AGENT = "security-auditor"
POST_OPEN_CODEX_SECURITY_SCAN = "Codex Security diff scan / finding discovery"
POST_OPEN_PULSEPLATE_PR_REVIEW = "pulseplate-pr-review"

MANDATORY_POST_OPEN_ORDER: tuple[str, ...] = (
    POST_OPEN_QA_AGENT,
    POST_OPEN_BUG_HUNTER_AGENT,
    POST_OPEN_SECURITY_AUDITOR_AGENT,
)
MANDATORY_POST_OPEN_GATES: tuple[str, ...] = (
    *MANDATORY_POST_OPEN_ORDER,
    POST_OPEN_CODEX_SECURITY_SCAN,
    POST_OPEN_PULSEPLATE_PR_REVIEW,
)
IMPLEMENTATION_OWNER_SLUGS: frozenset[str] = frozenset(
    (
        "app-store-release-agent",
        "backend-engineer",
        "bug-hunter",
        "dev-operator",
        "frontend-engineer",
        "ml-engineer-agent",
        "qa-engineer-agent",
        "security-auditor",
    )
)


def normalize_requested_agents(requested_agents: list[str] | tuple[str, ...]) -> list[str]:
    """Normalize requested agent slugs while preserving order and uniqueness."""

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_agent in requested_agents:
        agent = raw_agent.strip().lower()
        if not agent or agent in seen:
            continue
        seen.add(agent)
        normalized.append(agent)
    return normalized


def normalize_implementation_owner_slugs(values: Iterable[str] | str | None) -> set[str]:
    """Normalize explicit implementation-owner slugs into one internal shape."""

    if values is None:
        return set()
    if isinstance(values, str):
        iterable: Iterable[str] = (values,)
    else:
        iterable = values
    return {
        str(value).strip().lower()
        for value in iterable
        if str(value).strip().lower() in IMPLEMENTATION_OWNER_SLUGS
    }

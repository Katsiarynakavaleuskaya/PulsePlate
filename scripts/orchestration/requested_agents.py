"""Shared requested-agent helpers for deterministic orchestration routing.

RU: Общие хелперы для requested-agent routing без дрейфа между entrypoints.
EN: Shared helpers that keep requested-agent handling aligned across entrypoints.
"""

from __future__ import annotations


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

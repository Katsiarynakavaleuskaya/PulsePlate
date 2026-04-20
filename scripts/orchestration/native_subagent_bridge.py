"""Deterministic bridge between repo agents and native subagent runtimes.

RU: Сохраняет repo-agent slug как каноническую роль и добавляет transport-only
mapping на native subagent runtime для новых Codex/ChatGPT execution flows.
EN: Keeps the repo-agent slug as the canonical role while adding a
transport-only mapping to native subagent runtimes for newer Codex/ChatGPT
execution flows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.orchestration.agent_consistency_loader import load_inventory_agents

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / ".cursor" / "agents"
BRIDGE_PROTOCOL_VERSION = "1.0"
BRIDGE_TRANSPORT = "codex-native-subagents"


@dataclass(frozen=True)
class NativeExecutorProfile:
    """Canonical execution profile for one repo agent.

    RU: Профиль определяет transport-only executor type и режим исполнения.
    EN: The profile defines the transport-only executor type and execution mode.
    """

    native_agent_type: str
    execution_mode: str
    rationale: str


ANALYSIS_PROFILE = NativeExecutorProfile(
    native_agent_type="default",
    execution_mode="advisory",
    rationale=(
        "Analysis-first role; keep native executor generic while canonical "
        "identity stays the repo-agent slug."
    ),
)

CODEBASE_EXPLORER_PROFILE = NativeExecutorProfile(
    native_agent_type="explorer",
    execution_mode="read_only_analysis",
    rationale=(
        "Read-mostly codebase analysis role; use explorer transport for "
        "inspection-heavy tasks before implementation."
    ),
)

IMPLEMENTATION_PROFILE = NativeExecutorProfile(
    native_agent_type="worker",
    execution_mode="read_write",
    rationale=(
        "Implementation-heavy role expected to edit files, run checks, or "
        "prepare merge-ready artifacts."
    ),
)


REPO_AGENT_EXECUTOR_PROFILES: dict[str, NativeExecutorProfile] = {
    "agent-coordinator": ANALYSIS_PROFILE,
    "backend-engineer": IMPLEMENTATION_PROFILE,
    "frontend-engineer": IMPLEMENTATION_PROFILE,
    "bug-hunter": IMPLEMENTATION_PROFILE,
    "dev-operator": IMPLEMENTATION_PROFILE,
    "qa-engineer-agent": IMPLEMENTATION_PROFILE,
    "architecture-specialist": CODEBASE_EXPLORER_PROFILE,
    "security-auditor": IMPLEMENTATION_PROFILE,
    "ai-app-architect": ANALYSIS_PROFILE,
    "ai-innovation-specialist": ANALYSIS_PROFILE,
    "rag-systems-agent": ANALYSIS_PROFILE,
    "web-research-agent": ANALYSIS_PROFILE,
    "data-scientist-agent": ANALYSIS_PROFILE,
    "ml-engineer-agent": IMPLEMENTATION_PROFILE,
    "bayesian-uq-agent": ANALYSIS_PROFILE,
    "cv-agent": ANALYSIS_PROFILE,
    "philosophy-agent": ANALYSIS_PROFILE,
    "logic-agent": ANALYSIS_PROFILE,
    "nutritionist-agent": ANALYSIS_PROFILE,
    "cbt-psychologist-agent": ANALYSIS_PROFILE,
    "epistemology-discovery-agent": ANALYSIS_PROFILE,
    "physics-sensor-agent": ANALYSIS_PROFILE,
    "creative-designer": ANALYSIS_PROFILE,
    "designer-artist-agent": ANALYSIS_PROFILE,
    "sora-prompt-engineer": ANALYSIS_PROFILE,
    "app-store-release-agent": IMPLEMENTATION_PROFILE,
    "marketing-strategist": ANALYSIS_PROFILE,
    "wellness-analyst-agent": ANALYSIS_PROFILE,
    "business-strategist-agent": ANALYSIS_PROFILE,
    "ai-trend-reporter": ANALYSIS_PROFILE,
    "cursor-specialist-agent": CODEBASE_EXPLORER_PROFILE,
    "tutor-mentor-agent": ANALYSIS_PROFILE,
}


def _instruction_path(agent_slug: str) -> str:
    """Return the repo-relative instruction file for a canonical repo agent."""

    return (AGENTS_DIR / f"{agent_slug}.md").relative_to(REPO_ROOT).as_posix()


def _resolve_native_agent_type(*, profile: NativeExecutorProfile, role: str) -> str:
    """Choose the runtime transport type without changing canonical repo identity.

    RU: Reviewer всегда получает read-only transport even if the base role is
    normally write-capable.
    EN: Reviewer always gets a read-only transport even if the base role is
    normally write-capable.
    """

    if role == "reviewer":
        return "explorer"
    return profile.native_agent_type


def validate_native_subagent_bridge_profiles() -> None:
    """Ensure every canonical inventory agent has a transport profile."""

    inventory_agents = load_inventory_agents()
    missing = sorted(inventory_agents - REPO_AGENT_EXECUTOR_PROFILES.keys())
    if missing:
        raise ValueError(
            "Native subagent bridge missing executor profile(s) for: " f"{', '.join(missing)}"
        )


def build_native_subagent_binding(*, agent_slug: str, role: str) -> dict[str, Any]:
    """Build one deterministic runtime binding for a canonical repo agent."""

    if agent_slug not in REPO_AGENT_EXECUTOR_PROFILES:
        raise ValueError(f"Unknown native subagent bridge profile for agent: {agent_slug}")

    profile = REPO_AGENT_EXECUTOR_PROFILES[agent_slug]
    if role == "reviewer":
        execution_mode = "review_read_only"
    else:
        execution_mode = profile.execution_mode

    return {
        "role": role,
        "repo_agent_slug": agent_slug,
        "display_name": agent_slug,
        "native_agent_type": _resolve_native_agent_type(profile=profile, role=role),
        "execution_mode": execution_mode,
        "instruction_path": _instruction_path(agent_slug),
        "transport_rationale": profile.rationale,
        "dispatch_contract": {
            "canonical_identity": "repo_agent_slug",
            "native_executor_name_transport_only": True,
            "load_required_context_from_task_packet": True,
            "load_recommended_skills_from_task_packet": True,
            "announce_identity_as_repo_agent_slug": True,
        },
    }


def build_native_subagent_bridge(
    *,
    primary_agent: str,
    secondary_agents: list[str],
    reviewer: str,
    advisory_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Build transport metadata for runtimes that expose native subagents.

    RU: Канон роли остаётся repo-agent slug; native type нужен только как
    transport hint для нового runtime.
    EN: The canonical role remains the repo-agent slug; the native type is only
    a transport hint for the newer runtime.
    """

    validate_native_subagent_bridge_profiles()
    normalized_advisory_agents = advisory_agents or []
    advisory_bindings: list[dict[str, Any]] = []
    for agent_slug in normalized_advisory_agents:
        advisory_binding = build_native_subagent_binding(
            agent_slug=agent_slug,
            role="advisory",
        )
        advisory_bindings.append(
            {
                **advisory_binding,
                "execution_mode": "advisory_no_spawn",
                "dispatch_contract": {
                    **advisory_binding["dispatch_contract"],
                    "spawn_with_native_subagent": False,
                    "advisory_only": True,
                },
            }
        )
    return {
        "protocol_version": BRIDGE_PROTOCOL_VERSION,
        "transport": BRIDGE_TRANSPORT,
        "dispatch_policy": {
            "canonical_agent_identity": "repo_agent_slug",
            "native_executor_identity": "transport_only",
            "spawn_via_coordinator_only": True,
            "display_repo_agent_slug_in_user_updates": True,
            "instruction_source_of_truth": ".cursor/agents/*.md",
        },
        "primary": build_native_subagent_binding(
            agent_slug=primary_agent,
            role="primary",
        ),
        "secondary": [
            build_native_subagent_binding(agent_slug=agent_slug, role="secondary")
            for agent_slug in secondary_agents
        ],
        "advisory": advisory_bindings,
        "reviewer": build_native_subagent_binding(
            agent_slug=reviewer,
            role="reviewer",
        ),
    }

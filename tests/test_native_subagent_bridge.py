"""Tests for the deterministic native subagent bridge contract."""

from __future__ import annotations

from scripts.orchestration.agent_consistency_loader import load_inventory_agents
from scripts.orchestration.native_subagent_bridge import (
    BRIDGE_PROTOCOL_VERSION,
    BRIDGE_TRANSPORT,
    REPO_AGENT_EXECUTOR_PROFILES,
    build_native_subagent_binding,
    build_native_subagent_bridge,
    validate_native_subagent_bridge_profiles,
)


def test_native_subagent_bridge_covers_inventory_agents() -> None:
    """Every canonical inventory agent must have a native transport profile."""

    inventory_agents = load_inventory_agents()
    assert inventory_agents <= REPO_AGENT_EXECUTOR_PROFILES.keys()
    validate_native_subagent_bridge_profiles()


def test_build_native_subagent_binding_keeps_repo_agent_slug_canonical() -> None:
    """Native executor names are transport-only; repo slug stays canonical."""

    binding = build_native_subagent_binding(
        agent_slug="bug-hunter",
        role="primary",
    )

    assert binding["repo_agent_slug"] == "bug-hunter"
    assert binding["display_name"] == "bug-hunter"
    assert binding["native_agent_type"] == "worker"
    assert binding["instruction_path"] == ".cursor/agents/bug-hunter.md"
    assert binding["dispatch_contract"]["canonical_identity"] == "repo_agent_slug"
    assert binding["dispatch_contract"]["native_executor_name_transport_only"] is True


def test_build_native_subagent_bridge_shapes_primary_secondary_and_reviewer() -> None:
    """Bridge payload must be deterministic for all routed roles."""

    bridge = build_native_subagent_bridge(
        primary_agent="agent-coordinator",
        secondary_agents=["cursor-specialist-agent", "security-auditor"],
        reviewer="architecture-specialist",
    )

    assert bridge["protocol_version"] == BRIDGE_PROTOCOL_VERSION
    assert bridge["transport"] == BRIDGE_TRANSPORT
    assert bridge["dispatch_policy"]["spawn_via_coordinator_only"] is True
    assert bridge["primary"]["repo_agent_slug"] == "agent-coordinator"
    assert bridge["primary"]["native_agent_type"] == "default"
    assert bridge["secondary"][0]["repo_agent_slug"] == "cursor-specialist-agent"
    assert bridge["secondary"][0]["native_agent_type"] == "explorer"
    assert bridge["secondary"][1]["repo_agent_slug"] == "security-auditor"
    assert bridge["secondary"][1]["native_agent_type"] == "worker"
    assert bridge["reviewer"]["repo_agent_slug"] == "architecture-specialist"
    assert bridge["reviewer"]["native_agent_type"] == "explorer"
    assert bridge["reviewer"]["execution_mode"] == "review_read_only"


def test_build_native_subagent_bridge_keeps_advisory_collaborators_non_runnable() -> None:
    """Advisory specialists must stay visible but not spawnable."""

    bridge = build_native_subagent_bridge(
        primary_agent="ai-innovation-specialist",
        secondary_agents=["rag-systems-agent"],
        reviewer="architecture-specialist",
        advisory_agents=["ml-engineer-agent"],
    )

    assert [binding["repo_agent_slug"] for binding in bridge["secondary"]] == ["rag-systems-agent"]
    assert [binding["repo_agent_slug"] for binding in bridge["advisory"]] == ["ml-engineer-agent"]
    assert bridge["advisory"][0]["role"] == "advisory"
    assert bridge["advisory"][0]["execution_mode"] == "advisory_no_spawn"
    assert bridge["advisory"][0]["dispatch_contract"]["spawn_with_native_subagent"] is False

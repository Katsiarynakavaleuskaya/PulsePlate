"""Tests for the deterministic native subagent bridge contract."""

from __future__ import annotations

import pytest

from scripts.orchestration.agent_consistency_loader import load_inventory_agents
from scripts.orchestration.native_subagent_bridge import (
    BRIDGE_PROTOCOL_VERSION,
    BRIDGE_TRANSPORT,
    KIMI_BRIDGE_TRANSPORT,
    REPO_AGENT_EXECUTOR_PROFILES,
    build_kimi_native_subagent_bridge,
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


def test_build_native_subagent_bridge_requires_advisory_role_passes() -> None:
    """Advisory specialists must stay visible and required to run."""

    bridge = build_native_subagent_bridge(
        primary_agent="ai-innovation-specialist",
        secondary_agents=["rag-systems-agent"],
        reviewer="architecture-specialist",
        advisory_agents=["ml-engineer-agent"],
    )

    assert [binding["repo_agent_slug"] for binding in bridge["secondary"]] == ["rag-systems-agent"]
    assert [binding["repo_agent_slug"] for binding in bridge["advisory"]] == ["ml-engineer-agent"]
    assert bridge["advisory"][0]["role"] == "advisory"
    assert bridge["advisory"][0]["native_agent_type"] == "explorer"
    assert bridge["advisory"][0]["execution_mode"] == "advisory_review"
    assert bridge["advisory"][0]["dispatch_contract"]["spawn_with_native_subagent"] is True
    assert bridge["advisory"][0]["dispatch_contract"]["advisory_only"] is False
    assert bridge["advisory"][0]["dispatch_contract"]["required_role_pass"] is True
    assert (
        bridge["advisory"][0]["dispatch_contract"]["write_capability"]
        == "disabled_for_advisory_review"
    )


def test_build_native_subagent_bridge_rejects_unknown_transport() -> None:
    """Direct bridge builders must reject unsupported transport labels."""

    with pytest.raises(ValueError, match="Unsupported native subagent bridge transport"):
        build_native_subagent_bridge(
            primary_agent="agent-coordinator",
            secondary_agents=["bug-hunter"],
            reviewer="architecture-specialist",
            transport="unknown-native-subagents",
        )


def test_build_kimi_native_subagent_bridge_uses_kimi_transport() -> None:
    """Kimi bridge wrapper must set transport to kimi-native-subagents."""

    bridge = build_kimi_native_subagent_bridge(
        primary_agent="agent-coordinator",
        secondary_agents=["cursor-specialist-agent", "security-auditor"],
        reviewer="architecture-specialist",
    )

    assert bridge["transport"] == KIMI_BRIDGE_TRANSPORT
    assert bridge["protocol_version"] == BRIDGE_PROTOCOL_VERSION
    assert bridge["dispatch_policy"]["spawn_via_coordinator_only"] is True
    assert bridge["primary"]["repo_agent_slug"] == "agent-coordinator"
    assert bridge["reviewer"]["native_agent_type"] == "explorer"
    assert bridge["reviewer"]["execution_mode"] == "review_read_only"


def test_kimi_bridge_reuses_cursor_agent_instructions() -> None:
    """Kimi runtime must load instructions from .cursor/agents/, not a separate dir."""

    bridge = build_kimi_native_subagent_bridge(
        primary_agent="backend-engineer",
        secondary_agents=["bug-hunter"],
        reviewer="architecture-specialist",
    )

    assert bridge["primary"]["instruction_path"] == ".cursor/agents/backend-engineer.md"
    assert bridge["secondary"][0]["instruction_path"] == ".cursor/agents/bug-hunter.md"
    assert bridge["reviewer"]["instruction_path"] == ".cursor/agents/architecture-specialist.md"


def test_kimi_and_codex_bridges_are_structurally_identical_except_transport() -> None:
    """The only difference between Codex and Kimi bridges must be the transport label."""

    codex_bridge = build_native_subagent_bridge(
        primary_agent="agent-coordinator",
        secondary_agents=["cursor-specialist-agent"],
        reviewer="architecture-specialist",
    )
    kimi_bridge = build_kimi_native_subagent_bridge(
        primary_agent="agent-coordinator",
        secondary_agents=["cursor-specialist-agent"],
        reviewer="architecture-specialist",
    )

    assert codex_bridge["transport"] == BRIDGE_TRANSPORT
    assert kimi_bridge["transport"] == KIMI_BRIDGE_TRANSPORT

    # Drop transport and compare the rest
    codex_copy = {k: v for k, v in codex_bridge.items() if k != "transport"}
    kimi_copy = {k: v for k, v in kimi_bridge.items() if k != "transport"}
    assert codex_copy == kimi_copy

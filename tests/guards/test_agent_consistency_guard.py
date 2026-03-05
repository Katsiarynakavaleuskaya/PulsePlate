"""Guard: agent docs consistency (inventory, capability matrix, routing graph).

Enforces: routing ⊆ inventory ⊆ capability.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.orchestration.agent_consistency_loader import (
    load_agent_sets,
    load_capability_agents,
    load_inventory_agents,
    load_routing_agents,
)


def test_agent_sets_non_empty() -> None:
    """All three sets must be non-empty."""
    sets_ = load_agent_sets()
    assert sets_.inventory, "Inventory agents must not be empty"
    assert sets_.capability, "Capability agents must not be empty"
    assert sets_.routing, "Routing agents must not be empty"


def test_routing_subset_of_inventory() -> None:
    """Every agent in routing graph must appear in inventory."""
    sets_ = load_agent_sets()
    missing = sets_.routing - sets_.inventory
    assert not missing, f"Routing agents missing from inventory: {sorted(missing)}"


def test_missing_inventory_file_raises(tmp_path: Path) -> None:
    """FileNotFoundError when inventory path does not exist."""
    with pytest.raises(FileNotFoundError, match="Missing inventory file"):
        load_inventory_agents(tmp_path / "nope.md")


def test_missing_capability_file_raises(tmp_path: Path) -> None:
    """FileNotFoundError when capability matrix path does not exist."""
    with pytest.raises(FileNotFoundError, match="Missing capability matrix"):
        load_capability_agents(tmp_path / "nope.md")

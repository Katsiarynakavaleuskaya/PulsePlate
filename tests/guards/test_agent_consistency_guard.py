"""Guard: agent docs consistency across canonical files and docs.

Enforces:
- index == actual agent files
- routing ⊆ inventory
- inventory ⊆ capability
- inventory ⊆ context map
- allowlisted specialists ⊆ inventory
"""

from __future__ import annotations

from pathlib import Path
import json
import sys

import pytest

import scripts.orchestration.check_agent_consistency as check_agent_consistency
from scripts.orchestration.agent_consistency_loader import (
    AgentConsistencySets,
    load_declared_routing_clusters,
    load_agent_file_slugs,
    load_agent_sets,
    load_capability_agents,
    load_context_agents,
    load_index_agents,
    load_inventory_agents,
    load_non_routable_agents,
    load_routing_agents,
    load_routing_clusters,
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


def test_index_matches_agent_files() -> None:
    """docs/agents/index.md must match actual agent files."""
    sets_ = load_agent_sets()
    assert sets_.index == sets_.files


def test_inventory_covers_routable_or_allowlisted_agents() -> None:
    """Inventory must include routing agents and explicit non-routable specialists."""
    sets_ = load_agent_sets()
    expected = sets_.routing | sets_.non_routable
    missing = expected - sets_.inventory
    assert not missing, f"Inventory missing routable/allowlisted agents: {sorted(missing)}"


def test_declared_clusters_non_empty() -> None:
    """Cluster definitions must exist as a non-empty canonical set."""

    sets_ = load_agent_sets()
    assert sets_.declared_clusters, "Declared routing clusters must not be empty"


def test_routing_clusters_subset_of_declared_clusters() -> None:
    """Every routed cluster slug must be declared in the routing graph SoT."""

    sets_ = load_agent_sets()
    missing = sets_.routing_clusters - sets_.declared_clusters
    assert not missing, f"Routing clusters missing from declarations: {sorted(missing)}"


def test_declared_clusters_all_used_by_routed_domains() -> None:
    """Every declared cluster must be referenced by at least one routed domain."""

    sets_ = load_agent_sets()
    unused = sets_.declared_clusters - sets_.routing_clusters
    assert not unused, f"Declared clusters unused by routed domains: {sorted(unused)}"


def test_inventory_subset_of_capability() -> None:
    """Every inventory agent must exist in the capability matrix."""
    sets_ = load_agent_sets()
    missing = sets_.inventory - sets_.capability
    assert not missing, f"Inventory agents missing from capability matrix: {sorted(missing)}"


def test_inventory_subset_of_context_map() -> None:
    """Every file-backed inventory agent must define required context in the context map."""
    sets_ = load_agent_sets()
    missing = (sets_.inventory - sets_.system_exceptions) - sets_.context
    assert not missing, f"Inventory agents missing from context map: {sorted(missing)}"


def test_file_and_index_agents_subset_of_context_map() -> None:
    """Actual agent docs and index entries must map directly to context definitions."""
    sets_ = load_agent_sets()
    file_missing = (sets_.files - sets_.system_exceptions) - sets_.context
    index_missing = (sets_.index - sets_.system_exceptions) - sets_.context
    assert not file_missing, f"Agent files missing from context map: {sorted(file_missing)}"
    assert (
        not index_missing
    ), f"Agent index entries missing from context map: {sorted(index_missing)}"


def test_repo_backed_agents_have_files_and_index_entries() -> None:
    """Routable and allowlisted specialists must exist in repo-backed agent layers."""
    sets_ = load_agent_sets()
    expected = sets_.routing | sets_.non_routable
    assert not (expected - sets_.files)
    assert not (expected - sets_.index)


def test_agent_file_loader_uses_frontmatter_slug_when_filename_matches(tmp_path: Path) -> None:
    """Frontmatter-backed agent docs use the canonical slug declared in frontmatter."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "AGENTS.md").write_text("# scoped instructions\n", encoding="utf-8")
    (agents_dir / "notes.md").write_text("# not an agent doc\n", encoding="utf-8")
    (agents_dir / "canonical-agent.md").write_text(
        "---\nname: canonical-agent\nmodel: auto\n---\n# Alias Agent\n",
        encoding="utf-8",
    )
    (agents_dir / "invalid.md").write_text(
        "---\nmodel: auto\n---\n# Missing name\n",
        encoding="utf-8",
    )

    assert load_agent_file_slugs(agents_dir) == {"canonical-agent"}


def test_agent_file_loader_rejects_filename_frontmatter_mismatch(tmp_path: Path) -> None:
    """Agent docs must keep filename and frontmatter slug aligned."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "alias.md").write_text(
        "---\nname: canonical-agent\nmodel: auto\n---\n# Alias Agent\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="filename/frontmatter mismatch"):
        load_agent_file_slugs(agents_dir)


def test_check_agent_consistency_reports_direct_context_invariant(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI report fails when file/index agents are not backed by context-map entries."""
    synthetic = AgentConsistencySets(
        files={"agent-a"},
        index={"agent-a", "agent-b"},
        inventory={"agent-a", "agent-b"},
        capability={"agent-a", "agent-b"},
        context={"agent-b"},
        routing=set(),
        routing_clusters={"ops"},
        declared_clusters={"ops", "growth"},
        non_routable=set(),
        system_exceptions=set(),
    )
    monkeypatch.setattr(check_agent_consistency, "load_agent_sets", lambda: synthetic)
    monkeypatch.setattr(sys, "argv", ["check_agent_consistency", "--json"])

    exit_code = check_agent_consistency.main()

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["files_missing_in_context"] == ["agent-a"]
    assert report["index_missing_in_context"] == ["agent-a"]
    assert report["declared_clusters_unused"] == ["growth"]


def test_cluster_loaders_match_routing_graph_contract() -> None:
    """Dedicated cluster loaders should stay aligned with the routing graph SoT."""

    declared_clusters = load_declared_routing_clusters()
    assert declared_clusters
    assert load_routing_clusters() == declared_clusters


def test_check_agent_consistency_reports_loader_errors_structured(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI JSON should stay structured when routing loader validation fails."""

    monkeypatch.setattr(
        check_agent_consistency,
        "load_agent_sets",
        lambda: (_ for _ in ()).throw(ValueError("routing cluster mismatch")),
    )
    monkeypatch.setattr(check_agent_consistency, "load_agent_file_slugs", lambda: {"agent-a"})
    monkeypatch.setattr(check_agent_consistency, "load_index_agents", lambda: {"agent-a"})
    monkeypatch.setattr(check_agent_consistency, "load_inventory_agents", lambda: {"agent-a"})
    monkeypatch.setattr(check_agent_consistency, "load_capability_agents", lambda: {"agent-a"})
    monkeypatch.setattr(check_agent_consistency, "load_context_agents", lambda: {"agent-a"})
    monkeypatch.setattr(check_agent_consistency, "load_routing_agents", lambda: set())
    monkeypatch.setattr(check_agent_consistency, "load_routing_clusters_raw", lambda: {"ops"})
    monkeypatch.setattr(check_agent_consistency, "load_declared_routing_clusters", lambda: {"ml"})
    monkeypatch.setattr(check_agent_consistency, "load_non_routable_agents", lambda: set())
    monkeypatch.setattr(sys, "argv", ["check_agent_consistency", "--json"])

    exit_code = check_agent_consistency.main()

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["loader_errors"] == ["agent_sets: routing cluster mismatch"]
    assert report["routing_clusters"] == ["ops"]
    assert report["declared_clusters"] == ["ml"]
    assert report["routing_clusters_undefined"] == ["ops"]
    assert report["declared_clusters_unused"] == ["ml"]


def test_missing_inventory_file_raises(tmp_path: Path) -> None:
    """FileNotFoundError when inventory path does not exist."""
    with pytest.raises(FileNotFoundError, match="Missing inventory file"):
        load_inventory_agents(tmp_path / "nope.md")


def test_missing_capability_file_raises(tmp_path: Path) -> None:
    """FileNotFoundError when capability matrix path does not exist."""
    with pytest.raises(FileNotFoundError, match="Missing capability matrix"):
        load_capability_agents(tmp_path / "nope.md")


def test_missing_agent_dir_raises(tmp_path: Path) -> None:
    """FileNotFoundError when .cursor/agents directory does not exist."""
    with pytest.raises(FileNotFoundError, match="Missing agent directory"):
        load_agent_file_slugs(tmp_path / "agents")


def test_missing_index_raises(tmp_path: Path) -> None:
    """FileNotFoundError when docs/agents/index.md does not exist."""
    with pytest.raises(FileNotFoundError, match="Missing agent index"):
        load_index_agents(tmp_path / "index.md")


def test_missing_non_routable_allowlist_raises(tmp_path: Path) -> None:
    """FileNotFoundError when non-routable specialist allowlist is missing."""
    with pytest.raises(FileNotFoundError, match="Missing non-routable allowlist"):
        load_non_routable_agents(tmp_path / "allowlist.md")


def test_missing_context_map_raises(tmp_path: Path) -> None:
    """FileNotFoundError when context map does not exist."""
    with pytest.raises(FileNotFoundError, match="Missing context map"):
        load_context_agents(tmp_path / "context.md")

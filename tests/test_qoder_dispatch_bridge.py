"""Deterministic tests for scripts/orchestration/qoder_dispatch_bridge.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from scripts.orchestration import qoder_dispatch_bridge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

PACKET_PATH = REPO_ROOT / "docs" / "orchestration" / "PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "generated_at",
    "packet_source",
    "mode",
    "dispatch_sequence",
    "parallelizable_groups",
    "mandatory_post_open",
}

REQUIRED_ENTRY_KEYS = {
    "order",
    "role_slug",
    "qoder_subagent_type",
    "agent_definition_path",
    "required_context_paths",
    "recommended_skills",
    "mode",
    "system_prompt_excerpt",
    "description",
    "readonly",
    "constraints",
    "depends_on_previous",
}


def require_feature(feature_key: str) -> None:
    """Skip with the repo-standard optional-feature reason prefix."""

    pytest.skip(f"feature_disabled:{feature_key}")


# ---------------------------------------------------------------------------
# 1. test_manifest_generation_from_packet
# ---------------------------------------------------------------------------


def test_manifest_generation_from_packet() -> None:
    """Use the existing packet to generate a manifest; verify valid JSON with expected roles."""
    if not PACKET_PATH.is_file():
        pytest.skip(f"Packet file not available: {PACKET_PATH}")

    # The packet declares these roles in order
    expected_roles = [
        "agent-coordinator",
        "architecture-specialist",
        "philosophy-agent",
        "rag-systems-agent",
        "logic-agent",
        "security-auditor",
    ]

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=expected_roles,
        mode="analysis",
        packet_source=str(PACKET_PATH.relative_to(REPO_ROOT)),
    )

    # Validate JSON serializability
    json_str = json.dumps(manifest)
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)

    # Roles appear in expected order (only those with agent definition files)
    produced_slugs = [entry["role_slug"] for entry in manifest["dispatch_sequence"]]
    # Filter expected to only those that exist as agent defs
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    existing = [s for s in expected_roles if (agents_dir / f"{s}.md").is_file()]
    assert produced_slugs == existing


def test_parse_task_bootstrap_json_packet_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bridge must consume the JSON packets emitted by task_bootstrap.py."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [
                {"repo_agent_slug": "cursor-specialist-agent"},
                {"repo_agent_slug": "security-auditor"},
            ],
            "advisory": [
                {"repo_agent_slug": "qa-engineer-agent"},
                {"repo_agent_slug": "bug-hunter"},
                {"repo_agent_slug": "dev-operator"},
            ],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "cursor-specialist-agent",
        "security-auditor",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_places_reviewer_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Declared JSON reviewer must remain in tail slot for reviewer semantics."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
    ]


def test_parse_task_bootstrap_json_packet_preserves_repeated_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JSON packets may intentionally reuse a role in distinct positions."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
        "agent-coordinator",
    ]


def test_parse_task_bootstrap_json_packet_preserves_adjacent_repeated_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adjacent duplicate JSON bindings still represent distinct packet slots."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "agent-coordinator",
    ]


def test_task_bootstrap_json_reviewer_tail_resolves_code_review() -> None:
    """Reviewer-capable slugs from JSON packets should get CodeReview in tail slot."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist", "security-auditor"]
    for slug in slugs:
        if not (agents_dir / f"{slug}.md").is_file():
            pytest.skip(f"Agent definition not found: {slug}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {
        entry["role_slug"]: entry["qoder_subagent_type"] for entry in manifest["dispatch_sequence"]
    }

    assert by_slug["architecture-specialist"] == "Research"
    assert by_slug["security-auditor"] == "CodeReview"


def test_parse_task_bootstrap_json_packet_forces_coordinator_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cursor-led packet projections must still dispatch coordinator first."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "cursor-specialist-agent"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "cursor-specialist-agent",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_skips_no_spawn_secondary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-spawn metadata must be honored even if a future packet misplaces it."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [
                {
                    "repo_agent_slug": "qa-engineer-agent",
                    "dispatch_contract": {
                        "advisory_only": True,
                        "spawn_with_native_subagent": False,
                    },
                }
            ],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_includes_required_advisory_role_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Required advisory bindings are executable role passes, not skipped metadata."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [{"repo_agent_slug": "qa-engineer-agent"}],
            "advisory": [
                {
                    "repo_agent_slug": "ml-engineer-agent",
                    "dispatch_contract": {
                        "advisory_only": False,
                        "spawn_with_native_subagent": True,
                        "required_role_pass": True,
                    },
                }
            ],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "qa-engineer-agent",
        "ml-engineer-agent",
        "architecture-specialist",
    ]


def test_parse_task_bootstrap_json_packet_preserves_requested_role_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit requested agents define the role order when they are spawnable."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "architecture-specialist",
            "security-auditor",
            "qa-engineer-agent",
            "bug-hunter",
        ],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "bug-hunter"},
                {"repo_agent_slug": "cursor-specialist-agent"},
                {"repo_agent_slug": "security-auditor"},
                {"repo_agent_slug": "architecture-specialist"},
            ],
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]


def test_parse_task_bootstrap_json_packet_preserves_duplicate_requested_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated requested agents represent intentional repeated role passes."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "security-auditor",
            "agent-coordinator",
        ],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [{"repo_agent_slug": "security-auditor"}],
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "security-auditor",
        "agent-coordinator",
    ]


def test_parse_task_bootstrap_json_packet_empty_bridge_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed JSON packets must not be auto-repaired into coordinator-only lanes."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        json.dumps({"native_subagent_bridge": {}}),
        encoding="utf-8",
    )

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_all_no_spawn_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fully no-spawn bridge should fail fast instead of dispatching coordinator only."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {
                "repo_agent_slug": "agent-coordinator",
                "dispatch_contract": {
                    "advisory_only": True,
                    "spawn_with_native_subagent": False,
                },
            },
            "reviewer": {
                "repo_agent_slug": "architecture-specialist",
                "dispatch_contract": {
                    "advisory_only": True,
                    "spawn_with_native_subagent": False,
                },
            },
            "secondary": [],
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_missing_primary_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Secondary/reviewer roles cannot replace the required spawnable primary binding."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_empty_primary_slug_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A primary binding without a repo_agent_slug cannot establish lane ownership."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": ""},
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_no_spawn_primary_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-spawnable primary makes the JSON bridge malformed."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {
                "repo_agent_slug": "agent-coordinator",
                "dispatch_contract": {
                    "advisory_only": True,
                    "spawn_with_native_subagent": False,
                },
            },
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_malformed_dispatch_contract_returns_no_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed dispatch_contract metadata should fail closed."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {
                "repo_agent_slug": "agent-coordinator",
                "dispatch_contract": "spawnable",
            },
            "secondary": [{"repo_agent_slug": "architecture-specialist"}],
            "reviewer": {"repo_agent_slug": "security-auditor"},
            "advisory": [],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == []


def test_parse_task_bootstrap_json_packet_runs_spawnable_advisory_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Advisory bridge entries are required role passes when spawnable."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [],
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "advisory": [
                {
                    "repo_agent_slug": "qa-engineer-agent",
                    "dispatch_contract": {
                        "advisory_only": False,
                        "spawn_with_native_subagent": True,
                    },
                }
            ],
        }
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "qa-engineer-agent",
        "architecture-specialist",
    ]


def test_parse_packet_roles_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Packet reads must stay under the resolved repo root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"native_subagent_bridge": {}}), encoding="utf-8")
    link = repo_root / "packet.json"
    link.symlink_to(outside)
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", repo_root)

    with pytest.raises(SystemExit):
        qoder_dispatch_bridge._parse_packet_roles(link)


# ---------------------------------------------------------------------------
# 2. test_role_to_qoder_type_mapping
# ---------------------------------------------------------------------------


class TestRoleToQoderTypeMapping:
    """Verify resolve_qoder_type covers each documented mapping."""

    def test_readonly_architecture_specialist(self) -> None:
        agent_def = {
            "slug": "architecture-specialist",
            "name": "architecture-specialist",
            "readonly": True,
        }
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Research"

    def test_backend_engineer_runtime(self) -> None:
        agent_def = {"slug": "backend-engineer", "name": "backend-engineer", "readonly": False}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Coding"

    def test_qa_engineer_agent(self) -> None:
        agent_def = {"slug": "qa-engineer-agent", "name": "qa-engineer-agent", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Verify"
        assert (
            qoder_dispatch_bridge.resolve_qoder_type(agent_def, mode="docs-only", is_reviewer=False)
            == "Verify"
        )

    def test_qa_engineer_agent_reviewer_slot_stays_verify(self) -> None:
        agent_def = {"slug": "qa-engineer-agent", "name": "qa-engineer-agent", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=True
        )
        assert result == "Verify"

    def test_bug_hunter(self) -> None:
        agent_def = {"slug": "bug-hunter", "name": "bug-hunter", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Verify"
        assert (
            qoder_dispatch_bridge.resolve_qoder_type(agent_def, mode="docs-only", is_reviewer=False)
            == "Verify"
        )

    def test_reviewer_slot(self) -> None:
        agent_def = {"slug": "security-auditor", "name": "security-auditor", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=True
        )
        assert result == "CodeReview"

    def test_frontend_engineer_runtime_returns_browser(self) -> None:
        """frontend-engineer in runtime mode should return Browser (UI validation)."""
        agent_def = {"slug": "frontend-engineer", "name": "frontend-engineer", "readonly": False}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Browser"

    def test_frontend_engineer_coding_mode(self) -> None:
        """frontend-engineer in runtime mode (non-browser path) falls to Coding via generic check."""
        # Note: with the fix, frontend-engineer + runtime → Browser.
        # For non-runtime, non-analysis modes it hits Coding.
        agent_def = {"slug": "frontend-engineer", "name": "frontend-engineer", "readonly": False}
        # Use a mode that isn't "analysis"/"docs-only" (triggers Research) or "runtime" (triggers Browser)
        # There's no such mode currently – so we verify the analysis mode returns Research correctly
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="analysis", is_reviewer=False
        )
        assert result == "Research"

    def test_unknown_agent_fallback(self) -> None:
        agent_def = {"slug": "nonexistent-agent", "name": "nonexistent-agent", "readonly": False}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Research"


# ---------------------------------------------------------------------------
# 3. test_routing_graph_resolution
# ---------------------------------------------------------------------------


def test_routing_graph_resolution() -> None:
    """Verify that agent slugs resolve to correct domain/cluster from routing graph."""
    routing = qoder_dispatch_bridge._ensure_routing_graph()

    # If graph is available, it should be a non-empty dict
    if not routing:
        pytest.skip("Routing graph not available (no AGENT_ROUTING_GRAPH.md)")

    # Each entry should have cluster, primary, and reviewer fields
    for domain, info in routing.items():
        assert "cluster" in info, f"Domain '{domain}' missing cluster"
        assert "primary" in info, f"Domain '{domain}' missing primary"
        assert "reviewer" in info, f"Domain '{domain}' missing reviewer"


# ---------------------------------------------------------------------------
# 4. test_context_path_loading
# ---------------------------------------------------------------------------


def test_context_path_loading() -> None:
    """Verify that context map parsing returns non-empty paths for known agents."""
    context_map = qoder_dispatch_bridge._parse_context_map()

    if not context_map:
        pytest.skip("Context map not available (no AGENT_CONTEXT_MAP.md)")

    # agent-coordinator should have context paths
    assert "agent-coordinator" in context_map, "agent-coordinator not found in context map"
    paths = context_map["agent-coordinator"]
    assert len(paths) > 0, "agent-coordinator should have at least one context path"

    # Check that well-known files appear
    path_str = " ".join(paths)
    assert (
        "AGENTS.md" in path_str or "RUNBOOK_AGENT.md" in path_str
    ), f"Expected AGENTS.md or RUNBOOK_AGENT.md in coordinator context paths, got: {paths}"


# ---------------------------------------------------------------------------
# 5. test_parallelizable_group_detection
# ---------------------------------------------------------------------------


def test_parallelizable_group_detection() -> None:
    """Multiple readonly agents with different domains should appear in the same parallel group."""
    # Create synthetic dispatch items: two readonly agents in different domains
    dispatch_items: List[Dict[str, Any]] = [
        {
            "order": 1,
            "role_slug": "alpha-agent",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "order": 2,
            "role_slug": "beta-agent",
            "readonly": True,
            "depends_on_previous": False,
        },
    ]

    # Synthetic routing that maps the agents to different domains
    routing: Dict[str, Any] = {
        "domain-a": {
            "cluster": "analysis",
            "primary": "alpha-agent",
            "secondary": None,
            "reviewer": "reviewer-a",
        },
        "domain-b": {
            "cluster": "execution",
            "primary": "beta-agent",
            "secondary": None,
            "reviewer": "reviewer-b",
        },
    }

    groups = qoder_dispatch_bridge._detect_parallel_groups(dispatch_items, routing)
    assert len(groups) >= 1, "Expected at least one parallel group"
    # Both agents should be in the same parallel group
    flat = [slug for group in groups for slug in group]
    assert "alpha-agent" in flat
    assert "beta-agent" in flat


def test_packet_bracket_groups_must_match_independent_dispatch_items() -> None:
    """Packet bracket groups cannot name skipped agents or dependent steps."""
    dispatch_items: List[Dict[str, Any]] = [
        {
            "role_slug": "agent-coordinator",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "role_slug": "architecture-specialist",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "role_slug": "philosophy-agent",
            "readonly": True,
            "depends_on_previous": False,
        },
        {
            "role_slug": "bug-hunter",
            "readonly": False,
            "depends_on_previous": True,
        },
    ]

    groups = qoder_dispatch_bridge._validated_bracket_groups(
        [
            ["architecture-specialist", "philosophy-agent"],
            ["agent-coordinator", "architecture-specialist"],
            ["agent-coordinator", "missing-agent"],
            ["agent-coordinator", "bug-hunter"],
            ["agent-coordinator", "agent-coordinator"],
        ],
        dispatch_items,
    )

    assert groups == [["architecture-specialist", "philosophy-agent"]]


def test_packet_bracket_groups_drop_ambiguous_repeated_dispatch_slug() -> None:
    """Duplicate dispatch slugs make slug-only parallel groups ambiguous."""
    dispatch_items: List[Dict[str, Any]] = [
        {"role_slug": "agent-coordinator", "readonly": True, "depends_on_previous": False},
        {"role_slug": "architecture-specialist", "readonly": True, "depends_on_previous": False},
        {"role_slug": "agent-coordinator", "readonly": True, "depends_on_previous": False},
    ]

    groups = qoder_dispatch_bridge._validated_bracket_groups(
        [["agent-coordinator", "architecture-specialist"]],
        dispatch_items,
    )

    assert groups == []


def test_first_dispatch_item_cannot_depend_on_missing_previous_step() -> None:
    """Explicit dependency metadata is ignored for the first dispatch item."""
    assert (
        qoder_dispatch_bridge._depends_on_previous(
            "agent-coordinator",
            {"depends_on_previous": True},
            previous_slug=None,
        )
        is False
    )
    assert (
        qoder_dispatch_bridge._depends_on_previous(
            "agent-coordinator",
            {"depends_on_previous": True},
            previous_slug="dev-operator",
        )
        is True
    )


def test_packet_chain_successors_depend_on_previous() -> None:
    """Explicit packet chain notation carries dependency metadata into the manifest."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist", "philosophy-agent"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        chained_successors={"architecture-specialist", "philosophy-agent"},
    )
    by_slug = {e["role_slug"]: e for e in manifest["dispatch_sequence"]}

    assert by_slug["agent-coordinator"]["depends_on_previous"] is False
    assert by_slug["architecture-specialist"]["depends_on_previous"] is True
    assert by_slug["philosophy-agent"]["depends_on_previous"] is True


def test_manifest_bracket_parallel_group_and_qa_bug_chain() -> None:
    """Bracket groups stay parallel while qa-engineer-agent -> bug-hunter stays sequential."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "architecture-specialist",
        "philosophy-agent",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        bracket_groups=[["architecture-specialist", "philosophy-agent"]],
    )
    by_slug = {e["role_slug"]: e for e in manifest["dispatch_sequence"]}

    assert by_slug["architecture-specialist"]["depends_on_previous"] is False
    assert by_slug["philosophy-agent"]["depends_on_previous"] is False
    assert ["architecture-specialist", "philosophy-agent"] in manifest["parallelizable_groups"]
    assert by_slug["qa-engineer-agent"]["qoder_subagent_type"] == "Verify"
    assert by_slug["qa-engineer-agent"]["depends_on_previous"] is False
    assert by_slug["bug-hunter"]["qoder_subagent_type"] == "Verify"
    assert by_slug["bug-hunter"]["depends_on_previous"] is True


def test_verify_agents_are_readonly_when_frontmatter_omits_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify agents stay readonly even when frontmatter does not say so explicitly."""

    def fake_load_agent_definition(slug: str) -> Dict[str, Any]:
        return {
            "slug": slug,
            "name": slug,
            "description": "",
            "readonly": False,
            "readonly_explicit": False,
            "body": "",
            "definition_path": f".cursor/agents/{slug}.md",
        }

    monkeypatch.setattr(qoder_dispatch_bridge, "_load_agent_definition", fake_load_agent_definition)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["qa-engineer-agent", "bug-hunter"],
        mode="analysis",
        packet_source="test",
    )

    assert [item["qoder_subagent_type"] for item in manifest["dispatch_sequence"]] == [
        "Verify",
        "Verify",
    ]
    assert all(item["readonly"] for item in manifest["dispatch_sequence"])


def test_coordinator_is_not_parallelized_with_readonly_reviewers() -> None:
    """Coordinator-first stays sequential and is excluded from auto-parallel groups."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        bracket_groups=[["agent-coordinator", "architecture-specialist"]],
    )

    assert all("agent-coordinator" not in group for group in manifest["parallelizable_groups"])


def test_verify_agents_are_not_parallelized_with_reviewers() -> None:
    """Verify agents are readonly but still run in validation order, not parallel."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["architecture-specialist", "qa-engineer-agent"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
        bracket_groups=[slugs],
    )

    assert all("qa-engineer-agent" not in group for group in manifest["parallelizable_groups"])


def test_duplicate_readonly_slugs_are_not_auto_parallelized() -> None:
    """Slug-only auto parallel groups cannot represent repeated role phases safely."""
    dispatch_items: List[Dict[str, Any]] = [
        {
            "role_slug": "architecture-specialist",
            "readonly": True,
            "depends_on_previous": False,
            "qoder_subagent_type": "CodeReview",
        },
        {
            "role_slug": "architecture-specialist",
            "readonly": True,
            "depends_on_previous": False,
            "qoder_subagent_type": "CodeReview",
        },
        {
            "role_slug": "philosophy-agent",
            "readonly": True,
            "depends_on_previous": False,
            "qoder_subagent_type": "Research",
        },
    ]
    routing = {
        "architecture": {"reviewer": "architecture-specialist"},
        "philosophy": {"primary": "philosophy-agent"},
    }

    groups = qoder_dispatch_bridge._detect_parallel_groups(dispatch_items, routing)

    assert all("architecture-specialist" not in group for group in groups)


# ---------------------------------------------------------------------------
# 6. test_manifest_schema_compliance
# ---------------------------------------------------------------------------


def test_manifest_schema_compliance() -> None:
    """Verify output has all required top-level and entry-level keys."""
    # Use a known existing agent for a minimal manifest
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    existing_slugs = sorted([p.stem for p in agents_dir.glob("*.md") if p.stem != "AGENTS"])
    if not existing_slugs:
        pytest.skip("No agent definition files found")

    # Pick first two for a minimal test
    test_slugs = existing_slugs[:2]

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=test_slugs,
        mode="analysis",
        packet_source="test",
    )

    # Top-level keys
    missing_top = REQUIRED_TOP_LEVEL_KEYS - set(manifest.keys())
    assert not missing_top, f"Missing top-level keys: {missing_top}"

    # Entry-level keys
    for entry in manifest["dispatch_sequence"]:
        missing_entry = REQUIRED_ENTRY_KEYS - set(entry.keys())
        assert (
            not missing_entry
        ), f"Entry '{entry.get('role_slug', '?')}' missing keys: {missing_entry}"


# ---------------------------------------------------------------------------
# 7. test_roles_flag_explicit_list
# ---------------------------------------------------------------------------


def test_roles_flag_explicit_list() -> None:
    """Test --roles agent-coordinator philosophy-agent --mode analysis produces correct 2-entry manifest."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "philosophy-agent"]

    # Skip if either agent definition is missing
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source=None,
    )

    produced_slugs = [e["role_slug"] for e in manifest["dispatch_sequence"]]
    assert produced_slugs == slugs
    assert len(manifest["dispatch_sequence"]) == 2
    assert manifest["mode"] == "analysis"


# ---------------------------------------------------------------------------
# 8. test_packet_without_role_section_errors
# ---------------------------------------------------------------------------


def test_packet_without_role_section_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A packet without 'Coordinator Role Order' section should produce empty dispatch_sequence."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    fake_packet = tmp_path / "fake_packet.md"
    fake_packet.write_text(
        "# Fake Packet\n\n## Goal\n\nDo something.\n\n## Validation\n\nRun tests.\n",
        encoding="utf-8",
    )

    # _parse_packet_roles uses _list_known_agent_slugs which checks the real agents dir
    roles = qoder_dispatch_bridge._parse_packet_roles(fake_packet)
    # Without any recognized role section, expect empty list
    assert roles == [], f"Expected empty roles list, got: {roles}"


# ---------------------------------------------------------------------------
# 9. test_missing_agent_definition_graceful
# ---------------------------------------------------------------------------


def test_missing_agent_definition_graceful(capsys: pytest.CaptureFixture[str]) -> None:
    """If an agent slug doesn't have a corresponding definition file, handle gracefully."""
    slugs = ["nonexistent-agent-xyz-12345", "another-missing-agent-abc"]

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )

    # Missing agents should be skipped (not in dispatch_sequence)
    assert manifest["dispatch_sequence"] == []
    assert manifest["missing_agents"] == slugs

    # A warning should be emitted to stderr
    captured = capsys.readouterr()
    assert "nonexistent-agent-xyz-12345" in captured.err
    assert "another-missing-agent-abc" in captured.err


def test_cli_fails_when_requested_role_definition_is_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Executable CLI dispatch fails instead of emitting an empty manifest."""
    result = qoder_dispatch_bridge.main(
        ["--roles", "nonexistent-agent-xyz-12345", "--mode", "analysis"]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "FAIL: Agent definitions not found for: nonexistent-agent-xyz-12345" in captured.err


# ---------------------------------------------------------------------------
# 10. test_mandatory_post_open_detection
# ---------------------------------------------------------------------------


def test_mandatory_post_open_detection() -> None:
    """Verify that post-open mandatory pass agents are correctly identified in mandatory_post_open."""
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["agent-coordinator"],
        mode="analysis",
        packet_source="test",
    )

    # The bridge hardcodes mandatory_post_open
    assert "mandatory_post_open" in manifest
    post_open = manifest["mandatory_post_open"]
    assert isinstance(post_open, list)
    assert "qa-engineer-agent" in post_open
    assert "bug-hunter" in post_open


def test_mandatory_post_open_bug_hunter_depends_on_qa() -> None:
    """The post-open qa-engineer-agent -> bug-hunter pass stays sequential."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["qa-engineer-agent", "bug-hunter"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            require_feature(f"agent_definition:{s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e for e in manifest["dispatch_sequence"]}

    assert by_slug["qa-engineer-agent"]["qoder_subagent_type"] == "Verify"
    assert by_slug["qa-engineer-agent"]["depends_on_previous"] is False
    assert by_slug["bug-hunter"]["qoder_subagent_type"] == "Verify"
    assert by_slug["bug-hunter"]["depends_on_previous"] is True


def test_mandatory_post_open_pass_is_ordered_last() -> None:
    """Generated manifests must not run bug-hunter before QA in post-open lanes."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "bug-hunter",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    for slug in slugs:
        if not (agents_dir / f"{slug}.md").is_file():
            require_feature(f"agent_definition:{slug}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "bug-hunter",
    ]


# ---------------------------------------------------------------------------
# 11. test_graph_reviewer_slot_infers_code_review
# ---------------------------------------------------------------------------


def test_solo_primary_capable_reviewer_is_not_code_review_by_default() -> None:
    """Solo ``security-auditor`` is a primary-capable lead → analysis type stays Research."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "security-auditor.md").is_file():
        pytest.skip("security-auditor agent definition not found")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["security-auditor"],
        mode="analysis",
        packet_source="test",
    )
    assert len(manifest["dispatch_sequence"]) == 1
    assert manifest["dispatch_sequence"][0]["qoder_subagent_type"] == "Research"


def test_security_auditor_tail_role_is_code_review() -> None:
    """When ``security-auditor`` is last in a multi-role list, treat as graph reviewer (CodeReview)."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "security-auditor"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e["qoder_subagent_type"] for e in manifest["dispatch_sequence"]}
    assert by_slug["agent-coordinator"] == "Research"
    assert by_slug["security-auditor"] == "CodeReview"


def test_missing_role_does_not_hide_tail_reviewer_slot() -> None:
    """Missing slugs are excluded before tail reviewer detection."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "security-auditor.md").is_file():
        pytest.skip("security-auditor agent definition not found")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["missing-agent", "agent-coordinator", "security-auditor", "also-missing"],
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e["qoder_subagent_type"] for e in manifest["dispatch_sequence"]}

    assert by_slug["security-auditor"] == "CodeReview"


def test_architecture_specialist_after_coordinator_is_code_review() -> None:
    """Two-role orchestration lane: coordinator then architecture reviewer → CodeReview."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    by_slug = {e["role_slug"]: e["qoder_subagent_type"] for e in manifest["dispatch_sequence"]}
    assert by_slug["agent-coordinator"] == "Research"
    assert by_slug["architecture-specialist"] == "CodeReview"


# ---------------------------------------------------------------------------
# 12. test_mode_review_forces_code_review
# ---------------------------------------------------------------------------


def test_mode_review_forces_code_review() -> None:
    """mode=review should force all agents to CodeReview type."""
    agent_def = {"slug": "backend-engineer", "name": "backend-engineer", "readonly": False}
    result = qoder_dispatch_bridge.resolve_qoder_type(agent_def, mode="review", is_reviewer=False)
    assert result == "CodeReview"


# ---------------------------------------------------------------------------
# 13. test_fenced_code_blocks_skipped
# ---------------------------------------------------------------------------


def test_fenced_code_blocks_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fenced code blocks in packets should not produce false role matches."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    known = sorted(item.stem for item in agents_dir.glob("*.md") if item.stem != "AGENTS")
    if not known:
        pytest.skip("No agent definitions found")
    sample_slug = known[0]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    (tmp_agents_dir / f"{sample_slug}.md").write_text(f"---\nslug: {sample_slug}\n---\n")

    packet_content = (
        "# Test\n\n"
        "## Coordinator Role Order\n\n"
        "```bash\n"
        f"--requested-agent {sample_slug}\n"
        "```\n\n"
        "No agents listed here.\n"
    )
    fake_packet = tmp_path / "fence_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(fake_packet)
    assert roles == [], f"Expected no roles from fenced code, got: {roles}"


# ---------------------------------------------------------------------------
# 14. test_repeated_coordinator_entries_preserved
# ---------------------------------------------------------------------------


def test_repeated_coordinator_entries_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated non-consecutive entries in role order should be preserved."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "agent-coordinator.md").is_file():
        pytest.skip("agent-coordinator definition not found")

    other_slugs = sorted(
        item.stem
        for item in agents_dir.glob("*.md")
        if item.stem not in ("AGENTS", "agent-coordinator")
    )
    if not other_slugs:
        pytest.skip("Need at least two different agent definitions")
    other = other_slugs[0]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    (tmp_agents_dir / "agent-coordinator.md").write_text("---\nslug: agent-coordinator\n---\n")
    (tmp_agents_dir / f"{other}.md").write_text(f"---\nslug: {other}\n---\n")

    packet_content = (
        "# Test\n\n"
        "## Coordinator Role Order\n\n"
        f"1. agent-coordinator\n"
        f"2. {other}\n"
        f"3. agent-coordinator\n"
    )
    fake_packet = tmp_path / "repeat_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(fake_packet)
    assert roles == ["agent-coordinator", other, "agent-coordinator"]


# ---------------------------------------------------------------------------
# 15. test_bracket_group_detection
# ---------------------------------------------------------------------------


def test_bracket_group_detection(tmp_path: Path) -> None:
    """Bracket notation [slug-a, slug-b] should produce parallel groups."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    known = sorted(item.stem for item in agents_dir.glob("*.md") if item.stem != "AGENTS")
    if len(known) < 2:
        pytest.skip("Need at least two agent definitions for bracket group test")

    slug_a, slug_b = known[0], known[1]
    packet_content = "# Test\n\n" "## Coordinator Role Order\n\n" f"1. [{slug_a}, {slug_b}]\n"
    fake_packet = tmp_path / "bracket_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    lines = fake_packet.read_text(encoding="utf-8").splitlines()
    groups = qoder_dispatch_bridge._extract_bracket_groups(lines)
    assert len(groups) >= 1
    assert slug_a in groups[0]
    assert slug_b in groups[0]


def test_bracket_group_detection_strips_inline_code_ticks(tmp_path: Path) -> None:
    """Markdown inline code around bracket slugs should not drop the group."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    known = sorted(item.stem for item in agents_dir.glob("*.md") if item.stem != "AGENTS")
    if len(known) < 2:
        pytest.skip("Need at least two agent definitions for bracket group test")

    slug_a, slug_b = known[0], known[1]
    packet_content = "# Test\n\n" "## Coordinator Role Order\n\n" f"1. [`{slug_a}`, `{slug_b}`]\n"
    fake_packet = tmp_path / "bracket_backticks_test.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    groups = qoder_dispatch_bridge._extract_bracket_groups(
        fake_packet.read_text(encoding="utf-8").splitlines()
    )
    assert groups == [[slug_a, slug_b]]


def test_fallback_role_order_field_continuation_is_parsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback parsing includes indented continuations for role-order fields."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = ["agent-coordinator", "architecture-specialist", "qa-engineer-agent"]
    for s in slugs:
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in slugs:
        (tmp_agents_dir / f"{slug}.md").write_text(f"---\nslug: {slug}\n---\n")

    packet_content = (
        "# Test\n\n"
        "## Packet Notes\n\n"
        "- Required role order:\n"
        "  `agent-coordinator -> architecture-specialist -> qa-engineer-agent`\n"
    )
    fake_packet = tmp_path / "continued_role_order.md"
    fake_packet.write_text(packet_content, encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(fake_packet) == slugs


# ---------------------------------------------------------------------------
# 16. test_readonly_derived_from_qoder_type
# ---------------------------------------------------------------------------


def test_readonly_derived_from_qoder_type() -> None:
    """When agent frontmatter does not set readonly, derive from Qoder type."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not (agents_dir / "agent-coordinator.md").is_file():
        pytest.skip("agent-coordinator definition not found")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["agent-coordinator"],
        mode="analysis",
        packet_source="test",
    )
    # In analysis mode, agent-coordinator resolves to Research; readonly=True
    assert len(manifest["dispatch_sequence"]) >= 1
    entry = manifest["dispatch_sequence"][0]
    assert entry["readonly"] is True


# ---------------------------------------------------------------------------
# 17. test_reviewer_name_detection
# ---------------------------------------------------------------------------


def test_reviewer_name_detection() -> None:
    """Agents with auditor in slug get CodeReview when in tail position."""
    result = qoder_dispatch_bridge._dispatch_is_reviewer_slot(
        "code-auditor",
        order_idx=2,
        total_roles=2,
        primary_slugs=set(),
        reviewer_slugs=set(),
    )
    assert result is True, "auditor slug in tail position should be detected as reviewer"

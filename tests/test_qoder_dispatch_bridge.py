"""Deterministic tests for scripts/orchestration/qoder_dispatch_bridge.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from scripts.orchestration import qoder_dispatch_bridge, role_dispatch_bridge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

PACKET_PATH = REPO_ROOT / "docs" / "orchestration" / "PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "manifest_contract_version",
    "generated_at",
    "packet_source",
    "mode",
    "dispatch_sequence",
    "parallelizable_groups",
    "parallel_execution_allowed",
    "parallel_execution_reason",
    "post_open_role_gates",
    "mandatory_post_open",
    "mandatory_post_open_gates",
    "mandatory_post_open_role_agents",
    "compatibility_aliases",
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
    "implementation_owner_override",
    "constraints",
    "depends_on_previous",
}


def test_role_dispatch_bridge_exports_compatibility_main() -> None:
    """The neutral CLI keeps the historical qoder bridge implementation."""
    assert role_dispatch_bridge.main is qoder_dispatch_bridge.main


def test_legacy_qoder_dispatch_bridge_script_help_importable() -> None:
    """Direct legacy script execution must install repo root before package imports."""

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "orchestration" / "qoder_dispatch_bridge.py"),
            "--help",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "usage: role_dispatch_bridge" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


def test_role_dispatch_bridge_help_uses_neutral_name(capsys: pytest.CaptureFixture[str]) -> None:
    """The neutral CLI must not expose the old adapter name as the public command."""
    with pytest.raises(SystemExit) as exc_info:
        role_dispatch_bridge.main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: role_dispatch_bridge" in captured.out
    assert "Generate a JSON role dispatch manifest" in captured.out
    assert "Generate a JSON dispatch manifest for Qoder" not in captured.out


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
    """JSON packets may intentionally reuse the same role in distinct positions."""
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
    """Adjacent duplicate JSON bindings represent distinct packet slots."""
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
            "qa-engineer-agent",
            "bug-hunter",
            "security-auditor",
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
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
        "cursor-specialist-agent",
    ]


def test_manifest_preserves_requested_order_from_json_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit requested order must survive final dispatch manifest generation."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    required_slugs = [
        "agent-coordinator",
        "architecture-specialist",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
        "cursor-specialist-agent",
    ]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in required_slugs:
        qoder_type = "Verify" if slug in {"qa-engineer-agent", "bug-hunter"} else "Research"
        (tmp_agents_dir / f"{slug}.md").write_text(
            f"---\nslug: {slug}\nqoder_type: {qoder_type}\n---\n# {slug}\n",
            encoding="utf-8",
        )
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "architecture-specialist",
            "qa-engineer-agent",
            "bug-hunter",
            "security-auditor",
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

    roles = qoder_dispatch_bridge._parse_packet_roles(packet_path)
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=roles,
        mode="analysis",
        packet_source="packet.json",
        enforce_mandatory_post_open_tail=not (
            qoder_dispatch_bridge._json_packet_requested_order_preserves_mandatory_tail(packet_path)
        ),
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "architecture-specialist",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
        "cursor-specialist-agent",
    ]


def test_manifest_normalizes_requested_order_when_security_precedes_bug_hunter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit requests must still preserve the canonical QA -> bug -> security tail."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    required_slugs = [
        "agent-coordinator",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in required_slugs:
        qoder_type = "Verify" if slug in {"qa-engineer-agent", "bug-hunter"} else "Research"
        (tmp_agents_dir / f"{slug}.md").write_text(
            f"---\nslug: {slug}\nqoder_type: {qoder_type}\n---\n# {slug}\n",
            encoding="utf-8",
        )
    packet = {
        "requested_agents": [
            "agent-coordinator",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
        ],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "security-auditor"},
                {"repo_agent_slug": "bug-hunter"},
            ],
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(packet_path)
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=roles,
        mode="analysis",
        packet_source="packet.json",
        enforce_mandatory_post_open_tail=not (
            qoder_dispatch_bridge._json_packet_requested_order_preserves_mandatory_tail(packet_path)
        ),
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


def test_manifest_enforces_mandatory_tail_for_partial_requested_order_from_json_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Partial requested order must not disable the canonical QA -> bug tail."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    required_slugs = [
        "agent-coordinator",
        "frontend-engineer",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    tmp_agents_dir = tmp_path / ".cursor" / "agents"
    tmp_agents_dir.mkdir(parents=True)
    for slug in required_slugs:
        qoder_type = "Verify" if slug in {"qa-engineer-agent", "bug-hunter"} else "Research"
        (tmp_agents_dir / f"{slug}.md").write_text(
            f"---\nslug: {slug}\nqoder_type: {qoder_type}\n---\n# {slug}\n",
            encoding="utf-8",
        )
    packet = {
        "requested_agents": ["frontend-engineer"],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "bug-hunter"},
                {"repo_agent_slug": "frontend-engineer"},
                {"repo_agent_slug": "security-auditor"},
            ],
            "reviewer": {"repo_agent_slug": "qa-engineer-agent"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    roles = qoder_dispatch_bridge._parse_packet_roles(packet_path)
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=roles,
        mode="analysis",
        packet_source="packet.json",
        enforce_mandatory_post_open_tail=not (
            qoder_dispatch_bridge._json_packet_requested_order_preserves_mandatory_tail(packet_path)
        ),
    )

    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == [
        "agent-coordinator",
        "frontend-engineer",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


def test_requested_order_must_include_security_immediately_after_bug_hunter() -> None:
    """A partial QA -> bug request cannot disable security tail normalization."""

    assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "requested_agents": [
                "qa-engineer-agent",
                "architecture-specialist",
                "bug-hunter",
                "security-auditor",
            ]
        }
    )
    assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "requested_agents": [
                "qa-engineer-agent",
                "bug-hunter",
                "architecture-specialist",
            ]
        }
    )
    assert qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "requested_agents": [
                "qa-engineer-agent",
                "bug-hunter",
                "security-auditor",
                "architecture-specialist",
            ]
        }
    )


def test_pre_open_packet_preserves_requested_custom_role_order() -> None:
    """Pre-open bootstrap order is mandatory and must not get post-open tail sorting."""

    assert qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "pr_phase": "pre_open",
            "requested_agents": [
                "agent-coordinator",
                "architecture-specialist",
                "frontend-engineer",
                "cursor-specialist-agent",
                "security-auditor",
                "qa-engineer-agent",
                "bug-hunter",
            ],
        }
    )


def test_none_phase_packet_does_not_preserve_inverted_mandatory_tail() -> None:
    """Default JSON packets must not bypass the QA -> bug -> security tail."""

    assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
        {
            "pr_phase": "none",
            "requested_agents": [
                "qa-engineer-agent",
                "security-auditor",
                "bug-hunter",
            ],
        }
    )


def test_pre_open_packet_rejects_malformed_requested_agents_before_bypass() -> None:
    """Pre-open order bypass still validates requested_agents is a slug list."""

    malformed_payloads = [
        {"pr_phase": "pre_open", "requested_agents": "frontend-engineer"},
        {"pr_phase": "pre_open", "requested_agents": ["frontend-engineer", 42]},
        {"pr_phase": "pre_open", "requested_agents": ["frontend engineer"]},
    ]

    for payload in malformed_payloads:
        assert not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
            payload
        )


def test_parse_task_bootstrap_json_packet_limits_duplicate_requested_roles_to_spawnable_slots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requested duplicates must not synthesize extra passes beyond bridge slots."""
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
    ]


def test_parse_task_bootstrap_json_packet_requested_roles_keep_required_non_requested_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requested role ordering must not drop required bridge roles."""
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = {
        "requested_agents": ["frontend-engineer"],
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {"repo_agent_slug": "frontend-engineer"},
                {"repo_agent_slug": "security-auditor"},
            ],
            "reviewer": {"repo_agent_slug": "architecture-specialist"},
            "advisory": [],
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert qoder_dispatch_bridge._parse_packet_roles(packet_path) == [
        "agent-coordinator",
        "frontend-engineer",
        "security-auditor",
        "architecture-specialist",
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

    def test_readonly_backend_engineer_runtime_requires_owner_override(self) -> None:
        agent_def = {"slug": "backend-engineer", "name": "backend-engineer", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def, mode="runtime", is_reviewer=False
        )
        assert result == "Research"

        owned_result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def,
            mode="runtime",
            is_reviewer=False,
            implementation_owners={"backend-engineer"},
        )
        assert owned_result == "Coding"

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

    def test_readonly_frontend_engineer_runtime_owner_returns_browser(self) -> None:
        """Runtime Browser dispatch for a readonly frontend role requires explicit ownership."""
        agent_def = {"slug": "frontend-engineer", "name": "frontend-engineer", "readonly": True}
        result = qoder_dispatch_bridge.resolve_qoder_type(
            agent_def,
            mode="runtime",
            is_reviewer=False,
            implementation_owners={"frontend-engineer"},
        )
        assert result == "Browser"

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
    """Bracket groups stay parallel while qa -> bug -> security stays sequential."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "architecture-specialist",
        "philosophy-agent",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
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
    assert manifest["parallelizable_groups"] == []
    assert manifest["parallel_execution_allowed"] is False
    assert "dispatch_sequence order" in manifest["parallel_execution_reason"]
    assert by_slug["qa-engineer-agent"]["qoder_subagent_type"] == "Verify"
    assert by_slug["qa-engineer-agent"]["depends_on_previous"] is False
    assert by_slug["bug-hunter"]["qoder_subagent_type"] == "Verify"
    assert by_slug["bug-hunter"]["depends_on_previous"] is True
    assert by_slug["security-auditor"]["depends_on_previous"] is True
    assert all("security-auditor" not in group for group in manifest["parallelizable_groups"])


def test_mandatory_post_open_order_moves_all_bug_hunter_entries() -> None:
    """Duplicate bug-hunter entries must stay in the QA-led sequential block."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
        "bug-hunter",
    ]
    for s in set(slugs):
        if not (agents_dir / f"{s}.md").is_file():
            pytest.skip(f"Agent definition not found: {s}")

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=slugs,
        mode="analysis",
        packet_source="test",
    )
    dispatch = manifest["dispatch_sequence"]
    manifest_order = [item["role_slug"] for item in dispatch]

    assert manifest_order == [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "bug-hunter",
        "security-auditor",
    ]
    assert dispatch[2]["depends_on_previous"] is True
    assert dispatch[3]["depends_on_previous"] is True
    assert dispatch[4]["depends_on_previous"] is True
    assert all("bug-hunter" not in group for group in manifest["parallelizable_groups"])
    assert all("security-auditor" not in group for group in manifest["parallelizable_groups"])


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


def test_runtime_implementation_owner_override_clears_frontmatter_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit runtime ownership is required to dispatch readonly implementation roles."""

    def fake_load_agent_definition(slug: str) -> Dict[str, Any]:
        return {
            "slug": slug,
            "name": slug,
            "description": "",
            "readonly": True,
            "readonly_explicit": True,
            "body": "",
            "definition_path": f".cursor/agents/{slug}.md",
        }

    monkeypatch.setattr(qoder_dispatch_bridge, "_load_agent_definition", fake_load_agent_definition)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["backend-engineer", "frontend-engineer"],
        mode="runtime",
        packet_source="test",
        implementation_owners={"backend-engineer", "frontend-engineer"},
    )

    by_slug = {entry["role_slug"]: entry for entry in manifest["dispatch_sequence"]}
    assert by_slug["backend-engineer"]["qoder_subagent_type"] == "Coding"
    assert by_slug["frontend-engineer"]["qoder_subagent_type"] == "Browser"
    assert by_slug["backend-engineer"]["readonly"] is False
    assert by_slug["frontend-engineer"]["readonly"] is False
    assert by_slug["backend-engineer"]["implementation_owner_override"] is True
    assert by_slug["frontend-engineer"]["implementation_owner_override"] is True


def test_runtime_verify_owner_override_clears_frontmatter_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read-write QA/bug owner roles keep Verify type while clearing readonly."""

    def fake_load_agent_definition(slug: str) -> Dict[str, Any]:
        return {
            "slug": slug,
            "name": slug,
            "description": "",
            "readonly": True,
            "readonly_explicit": True,
            "body": "",
            "definition_path": f".cursor/agents/{slug}.md",
        }

    monkeypatch.setattr(qoder_dispatch_bridge, "_load_agent_definition", fake_load_agent_definition)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=["qa-engineer-agent", "bug-hunter"],
        mode="runtime",
        packet_source="test",
        implementation_owners={"qa-engineer-agent", "bug-hunter"},
    )

    by_slug = {entry["role_slug"]: entry for entry in manifest["dispatch_sequence"]}
    assert by_slug["qa-engineer-agent"]["qoder_subagent_type"] == "Verify"
    assert by_slug["bug-hunter"]["qoder_subagent_type"] == "Verify"
    assert by_slug["qa-engineer-agent"]["readonly"] is False
    assert by_slug["bug-hunter"]["readonly"] is False
    assert by_slug["qa-engineer-agent"]["implementation_owner_override"] is True
    assert by_slug["bug-hunter"]["implementation_owner_override"] is True


def test_runtime_implementation_owner_cli_requires_packet(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ad-hoc role lists cannot grant runtime write-capable ownership."""
    result = qoder_dispatch_bridge.main(
        [
            "--roles",
            "backend-engineer",
            "--mode",
            "runtime",
            "--implementation-owner",
            "backend-engineer",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "--implementation-owner requires --packet" in captured.err


def test_duplicate_key_json_packet_fails_closed_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(
        "{"
        '"requested_agents":["agent-coordinator"],'
        '"native_subagent_bridge":{"primary":{"repo_agent_slug":"agent-coordinator"},"secondary":[],"advisory":[]},'
        '"creative_pilot_context":null,'
        '"creative_pilot_context":{"phase":"independent"}'
        "}",
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)

    result = qoder_dispatch_bridge.main(["--packet", str(packet_file), "--mode", "analysis"])

    captured = capsys.readouterr()
    assert result == 1
    assert "invalid strict JSON task packet" in captured.err
    assert captured.out == ""


def test_runtime_implementation_owner_cli_packet_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Packet-bound CLI owner override emits a write-capable manifest entry."""
    agents_dir = tmp_path / ".cursor" / "agents"
    agents_dir.mkdir(parents=True)
    coordinator_file = agents_dir / "agent-coordinator.md"
    coordinator_file.write_text(
        "---\n"
        "name: agent-coordinator\n"
        "model: auto\n"
        "description: Agent coordinator\n"
        "readonly: true\n"
        "---\n"
        "\n"
        "# Agent Coordinator\n",
        encoding="utf-8",
    )
    agent_file = agents_dir / "frontend-engineer.md"
    agent_file.write_text(
        "---\n"
        "name: frontend-engineer\n"
        "model: auto\n"
        "description: Frontend engineer\n"
        "readonly: true\n"
        "---\n"
        "\n"
        "# Frontend Engineer\n",
        encoding="utf-8",
    )
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(
        json.dumps(
            {
                "role_agent_dispatch_contract": {
                    "runtime_implementation_owners": ["frontend-engineer"]
                },
                "native_subagent_bridge": {
                    "primary": {
                        "repo_agent_slug": "frontend-engineer",
                        "execution_mode": "read_write",
                    },
                    "secondary": [],
                    "advisory": [],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    result = qoder_dispatch_bridge.main(
        [
            "--packet",
            str(packet_file),
            "--mode",
            "runtime",
            "--implementation-owner",
            "frontend-engineer",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads(captured.out)
    entry = next(
        item for item in manifest["dispatch_sequence"] if item["role_slug"] == "frontend-engineer"
    )
    assert result == 0
    assert manifest["missing_agents"] == []
    assert entry["role_slug"] == "frontend-engineer"
    assert entry["qoder_subagent_type"] == "Browser"
    assert entry["readonly"] is False
    assert entry["implementation_owner_override"] is True


def test_runtime_implementation_owner_cli_rejects_ungranted_packet_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Runtime owner flags must match packet-granted read-write owners."""

    agents_dir = tmp_path / ".cursor" / "agents"
    agents_dir.mkdir(parents=True)
    for slug in ["agent-coordinator", "backend-engineer"]:
        (agents_dir / f"{slug}.md").write_text(
            "---\n"
            f"name: {slug}\n"
            "model: auto\n"
            f"description: {slug}\n"
            "readonly: true\n"
            "---\n"
            f"\n# {slug}\n",
            encoding="utf-8",
        )
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(
        json.dumps(
            {
                "role_agent_dispatch_contract": {
                    "runtime_implementation_owners": ["backend-engineer"]
                },
                "native_subagent_bridge": {
                    "primary": {"repo_agent_slug": "agent-coordinator"},
                    "secondary": [],
                    "advisory": [
                        {
                            "repo_agent_slug": "backend-engineer",
                            "execution_mode": "advisory_review",
                            "dispatch_contract": {
                                "advisory_only": False,
                                "spawn_with_native_subagent": True,
                                "required_role_pass": True,
                            },
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(qoder_dispatch_bridge, "_parse_context_map", lambda: {})
    monkeypatch.setattr(qoder_dispatch_bridge, "_ensure_routing_graph", lambda: {})

    result = qoder_dispatch_bridge.main(
        [
            "--packet",
            str(packet_file),
            "--mode",
            "runtime",
            "--implementation-owner",
            "backend-engineer",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "--implementation-owner not granted by packet for: backend-engineer" in captured.err


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


def test_roles_flag_preserves_explicit_pre_open_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public --roles fallback must not silently apply post-open tail sorting."""

    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "architecture-specialist",
        "frontend-engineer",
        "cursor-specialist-agent",
        "security-auditor",
        "qa-engineer-agent",
        "bug-hunter",
    ]
    for slug in slugs:
        if not (agents_dir / f"{slug}.md").is_file():
            pytest.skip(f"Agent definition not found: {slug}")

    result = role_dispatch_bridge.main(["--roles", *slugs, "--pr-phase", "pre_open", "--pretty"])

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)
    assert [entry["role_slug"] for entry in manifest["dispatch_sequence"]] == slugs


def test_roles_flag_rejects_ambiguous_post_open_order_without_phase(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A full post-open role set cannot bypass ordering via phase-less --roles."""

    result = role_dispatch_bridge.main(
        [
            "--roles",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
        ]
    )

    assert result == 1
    captured = capsys.readouterr()
    assert "Pass --pr-phase pre_open" in captured.err
    assert "--pr-phase post_open_review/merge_ready" in captured.err


def test_roles_flag_post_open_phase_enforces_mandatory_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase-aware explicit post-open dispatch keeps QA -> bug -> security."""

    result = role_dispatch_bridge.main(
        [
            "--roles",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
            "--pr-phase",
            "post_open_review",
            "--pretty",
        ]
    )

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)
    dispatch = manifest["dispatch_sequence"]
    assert [entry["role_slug"] for entry in dispatch] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert dispatch[1]["depends_on_previous"] is True
    assert dispatch[2]["depends_on_previous"] is True


def test_roles_flag_merge_ready_phase_enforces_mandatory_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Merge-ready explicit role dispatch keeps QA -> bug -> security."""

    result = role_dispatch_bridge.main(
        [
            "--roles",
            "qa-engineer-agent",
            "security-auditor",
            "bug-hunter",
            "--pr-phase",
            "merge_ready",
            "--pretty",
        ]
    )

    assert result == 0
    manifest = json.loads(capsys.readouterr().out)
    dispatch = manifest["dispatch_sequence"]
    assert [entry["role_slug"] for entry in dispatch] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert dispatch[1]["depends_on_previous"] is True
    assert dispatch[2]["depends_on_previous"] is True


def _invariant_review_packet(
    *,
    dispatch_role_order: object,
    implementation_authority: object = False,
    merge_authority: object = False,
) -> dict[str, object]:
    return {
        "pr_phase": "pre_open",
        "requested_agents": ["architecture-specialist"],
        "invariant_review": {
            "schema_version": "invariant_review.v1",
            "state": "required_pending",
            "required_roles": ["logic-agent", "philosophy-agent"],
            "implementation_authority": implementation_authority,
            "merge_authority": merge_authority,
        },
        "role_agent_dispatch_contract": {
            "dispatch_role_order": dispatch_role_order,
        },
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "architecture-specialist"},
            "secondary": [
                {"repo_agent_slug": "logic-agent"},
                {"repo_agent_slug": "agent-coordinator"},
                {"repo_agent_slug": "philosophy-agent"},
                {"repo_agent_slug": "security-auditor"},
            ],
            "advisory": [],
            "reviewer": {"repo_agent_slug": "cursor-specialist-agent"},
        },
    }


def test_invariant_review_dispatch_order_replaces_requested_agent_reordering() -> None:
    """System-required order is canonical without mutating requested agents."""

    expected_order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    packet = _invariant_review_packet(dispatch_role_order=expected_order)

    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == expected_order
    assert packet["requested_agents"] == ["architecture-specialist"]


def test_invariant_review_dispatch_order_chains_every_successor() -> None:
    """An accepted G0 order serializes every role after coordinator."""

    order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    parsed_order = qoder_dispatch_bridge._parse_json_packet_roles(
        _invariant_review_packet(dispatch_role_order=order)
    )
    manifest = qoder_dispatch_bridge.build_dispatch_manifest(
        role_slugs=parsed_order,
        mode="analysis",
        packet_source="invariant-review-test",
        chained_successors=set(parsed_order[1:]),
        enforce_mandatory_post_open_tail=False,
    )

    dispatch = manifest["dispatch_sequence"]
    assert dispatch[0]["depends_on_previous"] is False
    assert all(entry["depends_on_previous"] is True for entry in dispatch[1:])


@pytest.mark.parametrize(
    ("dispatch_role_order", "error"),
    [
        (
            [
                "logic-agent",
                "agent-coordinator",
                "philosophy-agent",
                "architecture-specialist",
                "security-auditor",
                "cursor-specialist-agent",
            ],
            "must start with agent-coordinator",
        ),
        (
            [
                "agent-coordinator",
                "logic-agent",
                "philosophy-agent",
                "architecture-specialist",
                "cursor-specialist-agent",
            ],
            "must exactly match spawnable",
        ),
        (
            [
                "agent-coordinator",
                "logic-agent",
                "philosophy-agent",
                "architecture-specialist",
                "security-auditor",
                "cursor-specialist-agent",
                "extra-agent",
            ],
            "must exactly match spawnable",
        ),
        (
            [
                "agent-coordinator",
                "logic-agent",
                "logic-agent",
                "architecture-specialist",
                "security-auditor",
                "cursor-specialist-agent",
            ],
            "must not contain duplicate",
        ),
        ("agent-coordinator", "must be a non-empty JSON list"),
    ],
)
def test_invariant_review_dispatch_order_fails_closed(
    dispatch_role_order: object,
    error: str,
) -> None:
    """Malformed or set-mismatched canonical orders never use legacy fallback."""

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(
            _invariant_review_packet(
                dispatch_role_order=dispatch_role_order,
            )
        )


@pytest.mark.parametrize(
    ("implementation_authority", "merge_authority", "error"),
    [
        (True, False, "must not grant implementation authority"),
        (False, True, "must not grant merge authority"),
        (0, False, "must not grant implementation authority"),
        (False, None, "must not grant merge authority"),
    ],
)
def test_invariant_review_dispatch_rejects_authority_confusion(
    implementation_authority: object,
    merge_authority: object,
    error: str,
) -> None:
    """Authority fields must be exact JSON false values."""

    order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(
            _invariant_review_packet(
                dispatch_role_order=order,
                implementation_authority=implementation_authority,
                merge_authority=merge_authority,
            )
        )


def test_invariant_review_dispatch_rejects_creative_override() -> None:
    """A malicious combined packet cannot replace the pre-fix chain."""

    order = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "architecture-specialist",
        "security-auditor",
        "cursor-specialist-agent",
    ]
    packet = _invariant_review_packet(dispatch_role_order=order)
    packet["creative_pilot_context"] = {"phase": "independent"}

    with pytest.raises(ValueError, match="cannot be combined with creative"):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


@pytest.mark.parametrize("omit_contract", [False, True])
def test_required_pending_invariant_review_requires_dispatch_order(
    omit_contract: bool,
) -> None:
    """Removing the canonical order cannot downgrade a pending review to legacy."""

    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    contract = packet["role_agent_dispatch_contract"]
    assert isinstance(contract, dict)
    if omit_contract:
        packet.pop("role_agent_dispatch_contract")
        error = "requires role_agent_dispatch_contract"
    else:
        contract.pop("dispatch_role_order")
        error = "requires dispatch_role_order"

    with pytest.raises(ValueError, match=error):
        qoder_dispatch_bridge._parse_json_packet_roles(packet)


def test_required_pending_invariant_review_without_order_blocks_creative_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Creative metadata cannot revive a pending packet whose order is missing."""

    monkeypatch.setattr(qoder_dispatch_bridge, "REPO_ROOT", tmp_path)
    packet = _invariant_review_packet(dispatch_role_order=["agent-coordinator"])
    contract = packet["role_agent_dispatch_contract"]
    assert isinstance(contract, dict)
    contract.pop("dispatch_role_order")
    packet["creative_pilot_context"] = {"phase": "independent"}
    packet_path = tmp_path / "pending-without-order.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    result = qoder_dispatch_bridge.main(["--packet", str(packet_path), "--mode", "analysis"])

    assert result == 1
    assert (
        "required_pending invariant review requires dispatch_role_order" in capsys.readouterr().err
    )


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

    assert manifest["schema_version"] == "2.0"
    assert manifest["manifest_contract_version"] == "pulseplate.role-dispatch-manifest/v2"
    assert manifest["post_open_role_gates"] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert "final_material_review_timing" not in manifest
    assert "final_material_review_gates" not in manifest
    assert "codex_security_invocation_policy" not in manifest

    # Every Qoder manifest gate alias remains role-only.
    assert "mandatory_post_open" in manifest
    post_open = manifest["mandatory_post_open"]
    assert isinstance(post_open, list)
    assert post_open == ["qa-engineer-agent", "bug-hunter", "security-auditor"]
    assert manifest["mandatory_post_open_gates"] == post_open
    assert manifest["mandatory_post_open_role_agents"] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert manifest["compatibility_aliases"] == {
        "mandatory_post_open": {
            "canonical_fields": ["post_open_role_gates"],
            "fail_closed": True,
        },
        "mandatory_post_open_role_agents": {
            "canonical_fields": ["post_open_role_gates"],
            "fail_closed": True,
        },
        "mandatory_post_open_gates": {
            "canonical_fields": ["post_open_role_gates"],
            "fail_closed": True,
        },
    }
    dispatched_roles = {entry["role_slug"] for entry in manifest["dispatch_sequence"]}
    assert "pulseplate-pr-review" not in dispatched_roles
    assert "Codex Security diff scan / finding discovery" not in dispatched_roles


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
    """Generated manifests keep the full QA -> bug -> security lane together."""
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
        "qa-engineer-agent",
        "bug-hunter",
        "bug-hunter",
        "security-auditor",
    ]


def test_coordinator_order_keeps_mandatory_qa_bug_pass_adjacent() -> None:
    """The bridge preserves order except for the mandatory QA -> bug handoff."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    slugs = [
        "agent-coordinator",
        "philosophy-agent",
        "architecture-specialist",
        "qa-engineer-agent",
        "security-auditor",
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
        "philosophy-agent",
        "architecture-specialist",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
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

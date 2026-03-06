"""Tests for deterministic coordinator task bootstrap packets."""

from __future__ import annotations

from scripts.orchestration.task_bootstrap import build_task_packet


def test_task_bootstrap_resolves_orchestration_domain() -> None:
    """Scripts/docs orchestration work should resolve to ops/orchestration."""

    packet = build_task_packet(
        goal="Harden orchestration preflight",
        task_class="Orchestration",
        candidate_paths=[
            "scripts/orchestration/check_preflight.py",
            "docs/orchestration/workflow.md",
        ],
    )

    assert packet["schema_version"] == "2.0"
    assert packet["domain"] == "orchestration"
    assert packet["cluster"] == "ops"
    assert packet["primary_agent"]
    assert "AGENTS.md" in packet["required_context"]
    assert "scripts/AGENTS.md" in packet["required_context"]


def test_task_bootstrap_includes_scoped_agents_only_once() -> None:
    """Context pack must be deterministic and de-duplicated."""

    packet = build_task_packet(
        goal="Update frontend release workflow",
        task_class="Release",
        candidate_paths=[
            "frontend/src/components/Button.tsx",
            "frontend/src/config/routes.ts",
        ],
    )

    required_context = packet["required_context"]
    assert required_context == sorted(required_context)
    assert required_context.count("frontend/AGENTS.md") == 1

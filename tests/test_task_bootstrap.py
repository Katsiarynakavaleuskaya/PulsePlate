"""Tests for deterministic coordinator task bootstrap packets."""

from __future__ import annotations

from pathlib import Path

import pytest
import scripts.orchestration.task_bootstrap as task_bootstrap_module
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
    assert "docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md" in packet["required_context"]
    assert "scripts/AGENTS.md" in packet["required_context"]
    assert packet["skill_routing"]["selection_mode"] == "deterministic-weighted"
    assert "pulseplate-workflow" in packet["recommended_skills"]
    assert "docs-sync" in packet["recommended_skills"]
    assert "agents-md" in packet["recommended_skills"]


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
    assert packet["skill_routing"]["recommended"]
    assert "pulseplate-workflow" in packet["recommended_skills"]
    assert "pulseplate-frontend-ui" in packet["recommended_skills"]


def test_task_bootstrap_main_accepts_repo_relative_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI bootstrap should accept repo-relative output paths."""

    monkeypatch.setattr(task_bootstrap_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        task_bootstrap_module,
        "TASK_PACKET_DIR",
        tmp_path / "artifacts" / "orchestration" / "task_packets",
    )

    exit_code = task_bootstrap_module.main(
        [
            "--goal",
            "Prepare orchestration skill policy",
            "--task-class",
            "Orchestration",
            "--path",
            "scripts/orchestration/task_bootstrap.py",
            "--output",
            "artifacts/orchestration/task_packets/relative-task-packet.json",
        ]
    )

    assert exit_code == 0
    assert (
        tmp_path / "artifacts" / "orchestration" / "task_packets" / "relative-task-packet.json"
    ).is_file()

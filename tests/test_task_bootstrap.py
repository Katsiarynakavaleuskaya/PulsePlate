"""Tests for deterministic coordinator task bootstrap packets."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
from scripts.orchestration.task_bootstrap import (
    _resolve_output_path,
    build_task_packet,
    main,
)


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


def test_task_bootstrap_routes_cv_tasks_to_cv_domain() -> None:
    """CV-first tasks should route to the graph-primary CV domain under ML."""

    packet = build_task_packet(
        goal="Evaluate food image recognition reliability for offline CV review",
        task_class="AI / ML",
        candidate_paths=[
            ".cursor/agents/cv-agent.md",
            "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
        ],
    )

    assert packet["domain"] == "cv"
    assert packet["cluster"] == "ml"
    assert packet["primary_agent"] == "cv-agent"
    assert packet["secondary_agents"] == ["data-scientist-agent"]
    assert packet["reviewer"] == "security-auditor"
    assert "docs-sync" in packet["recommended_skills"]
    assert "pulseplate-gates" in packet["recommended_skills"]


def test_task_bootstrap_does_not_treat_cve_or_cvss_as_cv_domain() -> None:
    """Security acronyms must not trigger the CV routing domain."""

    packet = build_task_packet(
        goal="Audit CVE and CVSS handling for auth failures",
        task_class="Security",
        candidate_paths=["app/security/auth.py"],
    )

    assert packet["domain"] == "security"


def test_task_bootstrap_preserves_explicit_security_task_class_over_cv_goal_hint() -> None:
    """Explicit non-CV task classes must win over generic CV goal wording."""

    packet = build_task_packet(
        goal="Audit CV controls for image upload abuse paths",
        task_class="Security",
        candidate_paths=["app/security/auth.py"],
    )

    assert packet["domain"] == "security"


def test_task_bootstrap_routes_cv_path_hints_for_cv_routable_task_class() -> None:
    """CV-specific paths should route to CV for ML/CV-class tasks."""

    packet = build_task_packet(
        goal="Refresh CV protocol references",
        task_class="AI / ML",
        candidate_paths=[
            "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
            ".cursor/agents/cv-agent.md",
        ],
    )

    assert packet["domain"] == "cv"
    assert packet["cluster"] == "ml"
    assert packet["primary_agent"] == "cv-agent"


def test_task_bootstrap_preserves_docs_task_class_over_cv_path_hint() -> None:
    """Explicit docs tasks must not be re-routed by CV-specific candidate paths."""

    packet = build_task_packet(
        goal="Refresh CV protocol references",
        task_class="Documentation",
        candidate_paths=[
            "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
            ".cursor/agents/cv-agent.md",
        ],
    )

    assert packet["domain"] == "docs"
    assert packet["cluster"] == "ops"


def test_normalize_repo_path_preserves_dot_cursor_prefix() -> None:
    """Leading './' removal must not strip the '.cursor' directory name."""

    assert normalize_repo_path("./.cursor/agents/agent-coordinator.md") == (
        ".cursor/agents/agent-coordinator.md"
    )


def test_normalize_repo_path_keeps_absolute_outside_repo() -> None:
    """Absolute paths outside repo should not raise and stay absolute."""

    outside = Path("/tmp/pulseplate-outside/task.json")
    assert normalize_repo_path(outside) == outside.as_posix()


def test_resolve_output_path_anchors_relative_paths_to_repo_root() -> None:
    """Relative --output should resolve within the repository root."""

    out_path = _resolve_output_path("tmp/task-packet.json", "ignored")
    assert out_path == (REPO_ROOT / "tmp/task-packet.json").resolve()


def test_main_rejects_output_outside_repo(tmp_path, capsys) -> None:
    """CLI should fail cleanly when --output targets a path outside the repo."""

    outside = tmp_path / "task-packet.json"
    exit_code = main(
        [
            "--goal",
            "Harden orchestration bootstrap",
            "--task-class",
            "Orchestration",
            "--path",
            "scripts/orchestration/task_bootstrap.py",
            "--output",
            str(outside),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: --output must stay within the repository root" in captured.out


def test_main_writes_relative_output_inside_repo(tmp_path, monkeypatch, capsys) -> None:
    """CLI should write relative --output under repo root and report repo-relative path."""

    relative_output = Path("tmp/task-packet.json")
    repo_output = (REPO_ROOT / relative_output).resolve()
    if repo_output.exists():
        repo_output.unlink()

    packet = {
        "schema_version": "2.0",
        "task_packet_id": "abc123def456",
        "goal": "Test bootstrap write",
        "task_class": "Orchestration",
        "domain": "orchestration",
        "cluster": "ops",
        "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
        "primary_agent": "agent-coordinator",
        "secondary_agents": [],
        "reviewer": "architecture-specialist",
        "required_context": ["AGENTS.md"],
        "recommended_skills": ["pulseplate-workflow"],
        "skill_routing": {
            "policy_version": "2026-03-08",
            "selection_mode": "deterministic-weighted",
            "recommended": [{"skill": "pulseplate-workflow", "score": 100}],
            "blocked": [],
        },
        "routing_rationale": {"source": "canonical_only"},
    }
    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        lambda **_: packet,
    )

    try:
        exit_code = main(
            [
                "--goal",
                "ignored",
                "--task-class",
                "ignored",
                "--output",
                str(relative_output),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        written = json.loads(repo_output.read_text(encoding="utf-8"))
        assert written["task_packet_id"] == "abc123def456"
        assert json.loads(captured.out)["output"] == relative_output.as_posix()
    finally:
        if repo_output.exists():
            repo_output.unlink()


def test_main_writes_repo_root_output_as_relative_path(monkeypatch, capsys) -> None:
    """Direct children of the repo root should still be reported repo-relative."""

    relative_output = Path("task-packet-root.json")
    repo_output = (REPO_ROOT / relative_output).resolve()
    if repo_output.exists():
        repo_output.unlink()

    packet = {
        "schema_version": "2.0",
        "task_packet_id": "rootpacket123",
        "goal": "Test root output write",
        "task_class": "Orchestration",
        "domain": "orchestration",
        "cluster": "ops",
        "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
        "primary_agent": "agent-coordinator",
        "secondary_agents": [],
        "reviewer": "architecture-specialist",
        "required_context": ["AGENTS.md"],
        "recommended_skills": ["pulseplate-workflow"],
        "skill_routing": {
            "policy_version": "2026-03-08",
            "selection_mode": "deterministic-weighted",
            "recommended": [{"skill": "pulseplate-workflow", "score": 100}],
            "blocked": [],
        },
        "routing_rationale": {"source": "canonical_only"},
    }
    monkeypatch.setattr(
        "scripts.orchestration.task_bootstrap.build_task_packet",
        lambda **_: packet,
    )

    try:
        exit_code = main(
            [
                "--goal",
                "ignored",
                "--task-class",
                "ignored",
                "--output",
                str(relative_output),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert repo_output.exists()
        assert json.loads(captured.out)["output"] == relative_output.as_posix()
    finally:
        if repo_output.exists():
            repo_output.unlink()

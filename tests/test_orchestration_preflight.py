"""Tests for mode-aware orchestration preflight."""

from __future__ import annotations

from scripts.orchestration import check_preflight as preflight


def test_analyze_mode_allows_dirty_tree(monkeypatch) -> None:
    """Analyze mode must pass with dirty tree when other checks pass."""

    monkeypatch.setattr(preflight, "check_sot_files", lambda: True)
    monkeypatch.setattr(preflight, "check_worktrees_untracked", lambda: True)
    monkeypatch.setattr(preflight, "check_agent_consistency", lambda: True)
    monkeypatch.setattr(preflight, "check_artifact_gitignore", lambda: True)
    monkeypatch.setattr(preflight, "check_scoped_agents_exist", lambda _paths: True)
    monkeypatch.setattr(
        preflight,
        "_run",
        lambda cmd, cwd=None: (
            (0, " M docs/orchestration/workflow.md") if cmd[:2] == ["git", "status"] else (0, "")
        ),
    )

    assert preflight.main(["--mode", "analyze", "--path", "docs/orchestration/workflow.md"]) == 0


def test_execute_mode_fails_when_dirty_tree_outside_scope(monkeypatch) -> None:
    """Execute mode must fail when repo dirt exists outside explicit task scope."""

    monkeypatch.setattr(preflight, "check_sot_files", lambda: True)
    monkeypatch.setattr(preflight, "check_worktrees_untracked", lambda: True)
    monkeypatch.setattr(preflight, "check_agent_consistency", lambda: True)
    monkeypatch.setattr(preflight, "check_artifact_gitignore", lambda: True)
    monkeypatch.setattr(preflight, "check_scoped_agents_exist", lambda _paths: True)
    monkeypatch.setattr(
        preflight,
        "_run",
        lambda cmd, cwd=None: (0, " M frontend/src/app.tsx\n M docs/orchestration/workflow.md"),
    )

    assert (
        preflight.main(
            [
                "--mode",
                "execute",
                "--path",
                "docs/orchestration",
                "--primary",
                "agent-coordinator",
                "--reviewer",
                "architecture-specialist",
            ]
        )
        == 1
    )


def test_merge_mode_requires_gate_evidence(monkeypatch, tmp_path) -> None:
    """Merge mode must fail when gate evidence file is missing."""

    monkeypatch.setattr(preflight, "check_sot_files", lambda: True)
    monkeypatch.setattr(preflight, "check_worktrees_untracked", lambda: True)
    monkeypatch.setattr(preflight, "check_agent_consistency", lambda: True)
    monkeypatch.setattr(preflight, "check_artifact_gitignore", lambda: True)
    monkeypatch.setattr(preflight, "check_scoped_agents_exist", lambda _paths: True)
    monkeypatch.setattr(preflight, "check_working_tree_clean", lambda: True)
    monkeypatch.setattr(
        preflight,
        "_run",
        lambda cmd, cwd=None: (0, " M docs/orchestration/workflow.md"),
    )

    assert (
        preflight.main(
            [
                "--mode",
                "merge",
                "--path",
                "docs/orchestration",
                "--primary",
                "agent-coordinator",
                "--reviewer",
                "architecture-specialist",
                "--evidence-file",
                str(tmp_path / "missing.log"),
            ]
        )
        == 1
    )

"""Tests for PR review context collector."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.orchestration import pr_review_context as review_ctx


def test_collect_fixed_mapping_state_reports_missing_artifact(tmp_path: Path) -> None:
    state = review_ctx.collect_fixed_mapping_state(repo_root=tmp_path, pr_number=123)

    assert state["exists"] is False
    assert state["path"].endswith("docs/review/PR_123_FIXED_MAPPING.md")
    assert state["entries"] == {}
    assert any("missing" in item.lower() for item in state["errors"])


def test_discover_scoped_agents_collects_root_and_subtree(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("root", encoding="utf-8")
    pkg_root = tmp_path / "src" / "pkg"
    pkg_root.mkdir(parents=True)
    (pkg_root / "AGENTS.md").write_text("pkg", encoding="utf-8")

    discovered = review_ctx.discover_scoped_agents(
        repo_root=tmp_path,
        changed_files=["src/pkg/main.py", "README.md"],
    )

    assert "AGENTS.md" in discovered
    assert "src/pkg/AGENTS.md" in discovered


def test_collect_scope_diff_parses_numstat_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = "12\t3\tsrc/app.py\n-\t-\tlegacy.bin\n"

    def fake_run(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        del args, cwd, check
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=expected, stderr="")

    monkeypatch.setattr(review_ctx, "_run_command", fake_run)

    files, summary, warnings = review_ctx.collect_scope_diff(
        repo_root=tmp_path,
        base_sha="base",
        head_sha="head",
    )

    assert not warnings
    assert len(files) == 2
    assert files[0].path == "src/app.py"
    assert files[0].additions == 12
    assert files[0].deletions == 3
    assert files[1].path == "legacy.bin"
    assert files[1].additions == 0
    assert files[1].deletions == 0
    assert summary["files"] == 2
    assert summary["additions"] == 12
    assert summary["deletions"] == 3
    assert summary["changed_lines"] == 15


def test_collect_review_context_missing_pr_metadata_and_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff_output = "1\t0\tapp.py\n"

    def fake_run(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        del cwd, check
        if args[-1] == "base":
            raise RuntimeError("no-op")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=diff_output, stderr="")

    monkeypatch.setattr(review_ctx, "_run_command", fake_run)
    monkeypatch.setenv("GITHUB_REPOSITORY", "")

    context = review_ctx.collect_review_context(
        repo_root=tmp_path,
        pr_number=777,
        repo=None,
        base_ref="base",
        head_ref="head",
    )

    assert context["pr"] is None
    assert any("Cannot read PR metadata" in warning for warning in context["warnings"])
    assert any("Fixed-mapping artifact is missing" in warning for warning in context["warnings"])
    assert context["fixed_mapping"]["exists"] is False

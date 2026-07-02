"""Tests for mode-aware orchestration preflight."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.orchestration import check_preflight as preflight
from scripts.orchestration.context_pack import find_nearest_agents_file

REPO_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_CLI_PATH = REPO_ROOT / "scripts" / "orchestration" / "check_preflight.py"


def test_analyze_mode_allows_dirty_tree(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_execute_mode_fails_when_dirty_tree_outside_scope(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_execute_mode_preserves_leading_status_space_for_top_level_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Top-level files must not be truncated when porcelain status begins with a space."""

    monkeypatch.setattr(preflight, "check_sot_files", lambda: True)
    monkeypatch.setattr(preflight, "check_worktrees_untracked", lambda: True)
    monkeypatch.setattr(preflight, "check_agent_consistency", lambda: True)
    monkeypatch.setattr(preflight, "check_artifact_gitignore", lambda: True)
    monkeypatch.setattr(preflight, "check_scoped_agents_exist", lambda _paths: True)
    monkeypatch.setattr(
        preflight,
        "_run",
        lambda cmd, cwd=None: (0, " M Makefile\n M docs/orchestration/workflow.md"),
    )

    assert (
        preflight.main(
            [
                "--mode",
                "execute",
                "--path",
                "Makefile",
                "--path",
                "docs/orchestration",
                "--primary",
                "agent-coordinator",
                "--reviewer",
                "architecture-specialist",
            ]
        )
        == 0
    )


def test_merge_mode_requires_gate_evidence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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


def test_merge_mode_fails_cleanly_on_unreadable_evidence(monkeypatch, tmp_path, capsys) -> None:
    """Unreadable evidence files must fail with a clean message, not a traceback."""

    evidence = tmp_path / "evidence.log"
    evidence.write_bytes(b"\xff\xfe\x00")

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

    exit_code = preflight.main(
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
            str(evidence),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: gate evidence files must be readable UTF-8 text:" in captured.out


def test_check_scoped_agents_exist_fails_when_any_path_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preflight,
        "find_nearest_agents_file",
        lambda path: (
            "scripts/AGENTS.md" if path == "scripts/orchestration/check_preflight.py" else None
        ),
    )
    monkeypatch.setattr(preflight, "collect_scoped_agents", lambda paths: ["scripts/AGENTS.md"])

    assert (
        preflight.check_scoped_agents_exist(
            [
                "scripts/orchestration/check_preflight.py",
                "docs/orchestration/AGENT_CONTEXT_MAP.md",
            ]
        )
        is False
    )


def test_find_nearest_agents_file_rejects_truncated_top_level_path() -> None:
    """A typo-truncated top-level path must not silently fall back to root AGENTS.md."""

    assert find_nearest_agents_file("docs/orchestration/AGENTS.md") == (
        "docs/orchestration/AGENTS.md"
    )
    assert find_nearest_agents_file(Path("docs/orchestration/AGENTS.md")) == (
        "docs/orchestration/AGENTS.md"
    )
    assert find_nearest_agents_file("ocs/orchestration") is None
    assert find_nearest_agents_file("ocs/orchestration/AGENTS.md") is None
    assert find_nearest_agents_file("../AGENTS.md") is None
    assert find_nearest_agents_file(Path("../AGENTS.md")) is None
    assert find_nearest_agents_file(".") is None
    assert find_nearest_agents_file(Path(".")) is None
    assert find_nearest_agents_file("AGENTS.md/child") is None


def test_check_gate_evidence_resolves_relative_paths_against_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    evidence = tmp_path / "evidence.log"
    evidence.write_text("ok\n", encoding="utf-8")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    monkeypatch.chdir(tmp_path.parent)

    assert preflight.check_gate_evidence(["evidence.log"]) is True


def test_private_python_index_url_shape_allows_missing_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(preflight.INDEX_ENV_VAR, raising=False)

    assert preflight.check_private_python_index_url_shape("execute", ["requirements.in"])


def test_private_python_index_url_shape_warns_in_analyze_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(
        preflight.INDEX_ENV_VAR,
        "https://packages.pulseplate.app/root/pypi/+simple/",
    )

    assert preflight.check_private_python_index_url_shape("analyze", ["requirements.in"])

    output = capsys.readouterr().out
    assert "WARNING:" in output
    assert "unexpected_index_path" in output
    assert "https://packages.pulseplate.app/root/pulseplate/+simple/" in output


def test_private_python_index_url_shape_fails_dependency_sensitive_execute_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(
        preflight.INDEX_ENV_VAR,
        "https://packages.pulseplate.app/root/pypi/+simple/",
    )

    assert (
        preflight.check_private_python_index_url_shape(
            "execute",
            ["scripts/ci/check_python_dependency_surfaces.py"],
        )
        is False
    )

    output = capsys.readouterr().out
    assert "FAIL:" in output
    assert "unexpected_index_path" in output


def test_private_python_index_url_shape_fails_dependency_sensitive_directory_scope(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(
        preflight.INDEX_ENV_VAR,
        "https://packages.pulseplate.app/root/pypi/+simple/",
    )

    assert preflight.check_private_python_index_url_shape("execute", ["scripts/ci"]) is False
    assert preflight.check_private_python_index_url_shape("execute", [".github/workflows"]) is False

    output = capsys.readouterr().out
    assert output.count("FAIL:") == 2
    assert "unexpected_index_path" in output


def test_private_python_index_url_shape_warns_for_unrelated_execute_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(preflight.INDEX_ENV_VAR, "https://pypi.org/simple/")

    assert preflight.check_private_python_index_url_shape(
        "execute",
        ["docs/orchestration/workflow.md"],
    )

    output = capsys.readouterr().out
    assert "WARNING:" in output
    assert "public_index_url" in output


def test_private_python_index_url_shape_does_not_echo_inline_credentials(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    unsafe_url = "https://user:token@packages.pulseplate.app/root/pulseplate/+simple/"  # pragma: allowlist secret
    monkeypatch.setenv(preflight.INDEX_ENV_VAR, unsafe_url)

    assert preflight.check_private_python_index_url_shape("execute", ["requirements.in"]) is False

    output = capsys.readouterr().out
    assert "credentialed_index_url" in output
    assert unsafe_url not in output


def test_private_python_index_url_shape_accepts_canonical_root(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(
        preflight.INDEX_ENV_VAR,
        "https://packages.pulseplate.app/root/pulseplate/+simple/",
    )

    assert preflight.check_private_python_index_url_shape("execute", ["requirements.in"])

    assert "PASS: private Python index URL shape" in capsys.readouterr().out


def test_role_dispatch_bridge_smoke_fails_closed_when_required_bridge_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The canonical role dispatch bridge is a hard preflight dependency."""

    monkeypatch.setattr(preflight, "ROOT", tmp_path)

    assert preflight._role_dispatch_bridge_smoke() is False
    assert "FAIL: required role_dispatch_bridge not found:" in capsys.readouterr().out


def test_role_dispatch_bridge_smoke_warns_for_missing_compatibility_bridge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The historical qoder entrypoint is compatibility-only."""

    bridge_dir = tmp_path / "scripts" / "orchestration"
    bridge_dir.mkdir(parents=True)
    (bridge_dir / "role_dispatch_bridge.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)

    assert preflight._role_dispatch_bridge_smoke() is True
    output = capsys.readouterr().out
    assert "role_dispatch_bridge: importable" in output
    assert "FAIL:" not in output


@pytest.mark.slow
def test_cli_invocation_works_without_pythonpath() -> None:
    """Plain script invocation must work from repo root without PYTHONPATH."""

    result = subprocess.run(
        [sys.executable, str(PREFLIGHT_CLI_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr

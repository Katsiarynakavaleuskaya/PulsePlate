"""Tests for PR review context collector."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.orchestration import pr_review_context as review_ctx
from scripts.orchestration.pr_review_evidence import MaterialEntry, MaterialManifest


def test_collect_fixed_mapping_state_reports_missing_artifact(tmp_path: Path) -> None:
    state = review_ctx.collect_fixed_mapping_state(repo_root=tmp_path, pr_number=123)

    assert state["exists"] is False
    assert "path" not in state
    assert state["repo_path"] == "docs/review/PR_123_FIXED_MAPPING.md"
    assert str(tmp_path) not in json.dumps(state, sort_keys=True)
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
    expected = "12\t3\tsrc/app.py\0-\t-\tlegacy.bin\0"
    captured_args: list[str] = []

    def fake_run(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        captured_args.extend(args)
        del cwd, check
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=expected, stderr="")

    monkeypatch.setattr(review_ctx, "_run_command", fake_run)

    files, summary, warnings = review_ctx.collect_scope_diff(
        repo_root=tmp_path,
        base_sha="base",
        head_sha="head",
    )

    assert not warnings
    assert "-z" in captured_args
    assert "--no-renames" in captured_args
    assert "--no-ext-diff" in captured_args
    assert "--no-textconv" in captured_args
    assert captured_args[-2:] == ["base..head", "--"]
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


def test_collect_scope_diff_preserves_utf8_rename_paths_as_no_rename_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_path = "docs/старое имя.md"
    new_path = "docs/новое имя.md"
    expected = f"0\t8\t{old_path}\0" f"11\t0\t{new_path}\0"
    captured_args: list[str] = []

    def fake_run(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        captured_args.extend(args)
        del cwd, check
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=expected, stderr="")

    monkeypatch.setattr(review_ctx, "_run_command", fake_run)

    files, summary, warnings = review_ctx.collect_scope_diff(
        repo_root=tmp_path,
        base_sha="base",
        head_sha="head",
    )

    assert warnings == []
    assert "-z" in captured_args
    assert "--no-renames" in captured_args
    assert [entry.path for entry in files] == [old_path, new_path]
    assert [(entry.additions, entry.deletions) for entry in files] == [(0, 8), (11, 0)]
    assert summary == {"files": 2, "additions": 11, "deletions": 8, "changed_lines": 19}


def test_collect_scope_diff_fails_closed_on_malformed_nul_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        del cwd, check
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="1\t0\tsrc/app.py\0malformed\0",
            stderr="",
        )

    monkeypatch.setattr(review_ctx, "_run_command", fake_run)

    files, summary, warnings = review_ctx.collect_scope_diff(
        repo_root=tmp_path,
        base_sha="base",
        head_sha="head",
    )

    assert files == []
    assert summary == {"files": 0, "additions": 0, "deletions": 0, "changed_lines": 0}
    assert warnings == ["Unable to parse NUL-delimited git diff --numstat output."]


def test_run_command_redacts_local_paths_in_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=f"fatal: cannot read {tmp_path}/secret.txt and /etc/pulseplate.conf",
        )

    monkeypatch.setattr(review_ctx.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        review_ctx._run_command(["/usr/bin/git", "-C", str(tmp_path), "status"], cwd=tmp_path)

    message = str(excinfo.value)
    assert str(tmp_path) not in message
    assert "/etc/pulseplate.conf" not in message
    assert "<repo-root>" in message
    assert "<redacted-path>" in message


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
    assert not any(
        "Fixed-mapping artifact is missing" in warning for warning in context["warnings"]
    )
    assert context["fixed_mapping"]["exists"] is False
    by_source = {item["source"]: item for item in context["review_source_status"]}
    assert by_source["github_pr_metadata"]["status"] == "unavailable"
    assert by_source["github_pr_metadata"]["source_degraded"] is True
    assert by_source["github_pr_metadata"]["fallback_required"] is True
    assert by_source["github_pr_metadata"]["blocking"] is False
    assert by_source["fixed_mapping_artifact"]["blocking"] is False


def test_collect_review_context_degrades_local_only_fixed_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = tmp_path / "docs" / "review" / "PR_2028_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(
        "\n".join(
            [
                "# PR 2028 - Fixed in Commit Mapping",
                "",
                "## Fixed in Commit Mapping",
                "- No actionable review comments",
            ]
        ),
        encoding="utf-8",
    )

    def fake_pr_metadata(
        *, repo: str, pr_number: int, repo_root: Path
    ) -> tuple[dict[str, object], list[str]]:
        del repo, pr_number, repo_root
        return {
            "number": 2028,
            "base_sha": "base-sha",
            "head_sha": "remote-head-sha",
        }, []

    def fake_scope_diff(
        *, repo_root: Path, base_sha: str | None, head_sha: str | None
    ) -> tuple[list[review_ctx.DiffStats], dict[str, int], list[str]]:
        del repo_root, base_sha, head_sha
        return (
            [
                review_ctx.DiffStats(
                    path="scripts/orchestration/pr_review_context.py", additions=1, deletions=0
                )
            ],
            {"files": 1, "additions": 1, "deletions": 0, "changed_lines": 1},
            [],
        )

    monkeypatch.setattr(review_ctx, "collect_pr_metadata", fake_pr_metadata)
    monkeypatch.setattr(review_ctx, "collect_scope_diff", fake_scope_diff)
    monkeypatch.setattr(
        review_ctx, "collect_local_head_sha", lambda repo_root: ("local-head-sha", [])
    )

    context = review_ctx.collect_review_context(
        repo_root=tmp_path,
        pr_number=2028,
        repo="owner/repo",
    )

    assert any(
        "Fixed-mapping artifact was read from local HEAD" in warning
        for warning in context["warnings"]
    )
    assert context["fixed_mapping"]["local_head_sha"] == "local-head-sha"
    assert context["fixed_mapping"]["pr_head_sha"] == "remote-head-sha"
    assert context["fixed_mapping"]["present_in_pr_diff"] is False
    assert any(
        "not present in the PR head diff" in error for error in context["fixed_mapping"]["errors"]
    )
    by_source = {item["source"]: item for item in context["review_source_status"]}
    assert by_source["fixed_mapping_artifact"]["source_degraded"] is True
    assert by_source["fixed_mapping_artifact"]["fallback_required"] is True
    assert by_source["fixed_mapping_artifact"]["blocking"] is False


def test_collect_review_context_degrades_mapping_absent_from_pr_diff_even_when_heads_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = tmp_path / "docs" / "review" / "PR_2028_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(
        "\n".join(
            [
                "# PR 2028 - Fixed in Commit Mapping",
                "",
                "## Fixed in Commit Mapping",
                "- No actionable review comments",
            ]
        ),
        encoding="utf-8",
    )

    def fake_pr_metadata(
        *, repo: str, pr_number: int, repo_root: Path
    ) -> tuple[dict[str, object], list[str]]:
        del repo, pr_number, repo_root
        return {
            "number": 2028,
            "base_sha": "base-sha",
            "head_sha": "matching-head-sha",
        }, []

    monkeypatch.setattr(review_ctx, "collect_pr_metadata", fake_pr_metadata)
    monkeypatch.setattr(
        review_ctx,
        "collect_scope_diff",
        lambda **kwargs: (
            [
                review_ctx.DiffStats(
                    path="scripts/orchestration/pr_review_context.py", additions=1, deletions=0
                )
            ],
            {"files": 1, "additions": 1, "deletions": 0, "changed_lines": 1},
            [],
        ),
    )
    monkeypatch.setattr(
        review_ctx,
        "collect_local_head_sha",
        lambda repo_root: ("matching-head-sha", []),
    )

    context = review_ctx.collect_review_context(
        repo_root=tmp_path,
        pr_number=2028,
        repo="owner/repo",
    )

    assert context["fixed_mapping"]["present_in_pr_diff"] is False
    assert any("not present in the PR head diff" in warning for warning in context["warnings"])
    by_source = {item["source"]: item for item in context["review_source_status"]}
    assert by_source["fixed_mapping_artifact"]["source_degraded"] is True


def test_collect_review_context_checks_mapping_presence_against_raw_pr_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping_path = "docs/review/PR_2028_FIXED_MAPPING.md"
    mapping = tmp_path / mapping_path
    mapping.parent.mkdir(parents=True)
    mapping.write_text(
        "\n".join(
            [
                "# PR 2028 - Fixed in Commit Mapping",
                "",
                "## Fixed in Commit Mapping",
                "- No actionable review comments",
            ]
        ),
        encoding="utf-8",
    )

    def fake_collect_pr_metadata(
        *,
        repo: str,
        pr_number: int,
        repo_root: Path,
    ) -> tuple[dict[str, Any], list[str]]:
        del repo, pr_number, repo_root
        return {"number": 2028, "base_sha": "base-sha", "head_sha": "head-sha"}, []

    def fake_compute_material_manifest(
        repo_root: Path,
        *,
        base_ref_oid: str,
        head_ref_oid: str,
        pr_number: int,
    ) -> MaterialManifest:
        del repo_root, base_ref_oid, head_ref_oid, pr_number
        return MaterialManifest(
            base_ref_oid="base-sha",
            head_ref_oid="head-sha",
            merge_base_sha="merge-base-sha",
            pr_number=2028,
            entries=(
                MaterialEntry(
                    status="M",
                    path="scripts/orchestration/pr_review_context.py",
                    base_mode="100644",
                    base_blob_oid="a" * 40,
                    head_mode="100644",
                    head_blob_oid="b" * 40,
                ),
            ),
            digest="sha256:" + "a" * 64,
        )

    def fake_collect_scope_diff(
        *,
        repo_root: Path,
        base_sha: str | None,
        head_sha: str | None,
    ) -> tuple[list[review_ctx.DiffStats], dict[str, Any], list[str]]:
        del repo_root, base_sha, head_sha
        return (
            [
                review_ctx.DiffStats(
                    path="scripts/orchestration/pr_review_context.py",
                    additions=5,
                    deletions=2,
                ),
                review_ctx.DiffStats(path=mapping_path, additions=3, deletions=0),
            ],
            {"files": 2, "additions": 8, "deletions": 2, "changed_lines": 10},
            [],
        )

    def fake_collect_local_head_sha(repo_root: Path) -> tuple[str, list[str]]:
        del repo_root
        return "head-sha", []

    monkeypatch.setattr(
        review_ctx,
        "collect_pr_metadata",
        fake_collect_pr_metadata,
    )
    monkeypatch.setattr(
        review_ctx,
        "compute_material_manifest",
        fake_compute_material_manifest,
    )
    monkeypatch.setattr(
        review_ctx,
        "collect_scope_diff",
        fake_collect_scope_diff,
    )
    monkeypatch.setattr(
        review_ctx,
        "collect_local_head_sha",
        fake_collect_local_head_sha,
    )

    context = review_ctx.collect_review_context(
        repo_root=tmp_path,
        pr_number=2028,
        repo="owner/repo",
    )

    assert context["fixed_mapping"]["present_in_pr_diff"] is True
    assert not any("not present in the PR head diff" in warning for warning in context["warnings"])
    assert context["diff"]["files"] == [
        {
            "path": "scripts/orchestration/pr_review_context.py",
            "additions": 5,
            "deletions": 2,
        }
    ]
    assert context["diff"]["summary"] == {
        "files": 1,
        "additions": 5,
        "deletions": 2,
        "changed_lines": 7,
    }
    assert context["agents_discovery"]["files_seen"] == [
        "scripts/orchestration/pr_review_context.py"
    ]


def test_collect_review_context_uses_repo_relative_mapping_evidence_without_pr_number(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(review_ctx, "infer_repo_name", lambda repo_root: None)
    monkeypatch.setattr(
        review_ctx,
        "collect_scope_diff",
        lambda **kwargs: (
            [
                review_ctx.DiffStats(
                    path="scripts/orchestration/pr_review_context.py", additions=1, deletions=0
                )
            ],
            {"files": 1, "additions": 1, "deletions": 0, "changed_lines": 1},
            [],
        ),
    )

    context = review_ctx.collect_review_context(
        repo_root=tmp_path,
        pr_number=None,
        repo=None,
        base_ref="base",
        head_ref="head",
    )

    by_source = {item["source"]: item for item in context["review_source_status"]}
    assert "path" not in context["fixed_mapping"]
    assert str(tmp_path) not in json.dumps(context["fixed_mapping"], sort_keys=True)
    assert by_source["fixed_mapping_artifact"]["evidence"] == "docs/review/PR_<N>_FIXED_MAPPING.md"
    assert str(tmp_path) not in by_source["fixed_mapping_artifact"]["evidence"]


def test_collect_review_context_degrades_mapping_absent_from_pr_diff_without_sha_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = tmp_path / "docs" / "review" / "PR_2028_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(
        "\n".join(
            [
                "# PR 2028 - Fixed in Commit Mapping",
                "",
                "## Fixed in Commit Mapping",
                "- No actionable review comments",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        review_ctx,
        "collect_pr_metadata",
        lambda **kwargs: ({"number": 2028, "base_sha": "base-sha", "head_sha": ""}, []),
    )
    monkeypatch.setattr(
        review_ctx,
        "collect_scope_diff",
        lambda **kwargs: (
            [
                review_ctx.DiffStats(
                    path="scripts/orchestration/pr_review_context.py", additions=1, deletions=0
                )
            ],
            {"files": 1, "additions": 1, "deletions": 0, "changed_lines": 1},
            [],
        ),
    )
    monkeypatch.setattr(review_ctx, "collect_local_head_sha", lambda repo_root: ("", []))

    context = review_ctx.collect_review_context(
        repo_root=tmp_path,
        pr_number=2028,
        repo="owner/repo",
    )

    assert context["fixed_mapping"]["present_in_pr_diff"] is False
    assert any("not present in the PR head diff" in warning for warning in context["warnings"])


def test_collect_review_context_degrades_mapping_against_explicit_head_without_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = tmp_path / "docs" / "review" / "PR_2028_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(
        "\n".join(
            [
                "# PR 2028 - Fixed in Commit Mapping",
                "",
                "## Fixed in Commit Mapping",
                "- No actionable review comments",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(review_ctx, "collect_pr_metadata", lambda **kwargs: (None, []))
    monkeypatch.setattr(
        review_ctx,
        "collect_scope_diff",
        lambda **kwargs: (
            [
                review_ctx.DiffStats(
                    path="docs/review/PR_2028_FIXED_MAPPING.md",
                    additions=1,
                    deletions=0,
                )
            ],
            {"files": 1, "additions": 1, "deletions": 0, "changed_lines": 1},
            [],
        ),
    )
    monkeypatch.setattr(review_ctx, "collect_local_head_sha", lambda repo_root: ("local-head", []))

    context = review_ctx.collect_review_context(
        repo_root=tmp_path,
        pr_number=2028,
        repo="owner/repo",
        base_ref="base-sha",
        head_ref="remote-head",
    )

    assert context["fixed_mapping"]["local_head_sha"] == "local-head"
    assert context["fixed_mapping"]["pr_head_sha"] == "remote-head"
    assert any(
        "local-head" in warning and "remote-head" in warning for warning in context["warnings"]
    )


def test_main_writes_json_to_stdout_and_warnings_to_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_context(**kwargs: object) -> dict[str, object]:
        del kwargs
        return {
            "schema_version": "2.0.0",
            "warnings": ["degraded source"],
        }

    monkeypatch.setattr(review_ctx, "collect_review_context", fake_context)
    monkeypatch.setattr(
        review_ctx,
        "REPO_ROOT",
        tmp_path,
    )

    assert review_ctx.main([]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["warnings"] == ["degraded source"]
    assert captured.err == "WARNING: degraded source\n"

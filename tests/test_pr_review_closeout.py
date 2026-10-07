"""Registered closeout publication must satisfy its unchanged filesystem consumer."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from scripts.orchestration import pr_review_closeout as closeout
from scripts.orchestration import pr_review_evidence as evidence
from scripts.orchestration.creative_code_patch_workspace import (
    git_env_without_parent_state,
    safe_git_config_args,
)
from scripts.orchestration.pr_commit_identity import PrCommitEvidence, PrSnapshot
from tests.test_pr_review_material_seal import _self_review_report_payload


@pytest.fixture(autouse=True)
def _publication_synthetic_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let mocked credential diagnostics retain a host credential source."""
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GH_TOKEN", "opaque")
    monkeypatch.setenv("GITHUB_TOKEN", "opaque")


def _publication_git(repo: Path, *args: str) -> str:
    """Keep synthetic commits independent of host hooks, signing and Git metadata."""
    git = shutil.which("git")
    assert git is not None
    env = git_env_without_parent_state()
    env.update(
        GIT_AUTHOR_NAME="Publication Test",
        GIT_AUTHOR_EMAIL="publication@example.invalid",
        GIT_COMMITTER_NAME="Publication Test",
        GIT_COMMITTER_EMAIL="publication@example.invalid",
    )
    result = subprocess.run(
        [git, *safe_git_config_args(), "-c", "commit.gpgSign=false", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_closeout_publication_git_omits_ambient_credentials_and_parent_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Observe real Git subprocess isolation using only synthetic hostile parent state."""
    parent = tmp_path / "synthetic-parent"
    parent.mkdir()
    template = tmp_path / "empty-template"
    template.mkdir()
    _publication_git(parent, "init", "-q", f"--template={template}")
    (parent / "tracked.txt").write_text("unchanged parent\n", encoding="utf-8")
    _publication_git(parent, "add", "tracked.txt")
    metadata = parent / ".git"
    before = {name: (metadata / name).read_bytes() for name in ("config", "HEAD", "index")}
    hostile_config = tmp_path / "synthetic-global.config"
    hostile_config.write_text("[user]\n name = Synthetic Wrong Identity\n", encoding="utf-8")
    injected = {
        "PUBLICATION_TEST_CREDENTIAL": "synthetic-credential-only",
        "GH_TOKEN": "synthetic-github-only",
        "GITHUB_TOKEN": "synthetic-github-only",
        "GH_ENTERPRISE_TOKEN": "synthetic-enterprise-only",
        "GITHUB_ENTERPRISE_TOKEN": "synthetic-enterprise-only",
        "GIT_DIR": str(metadata),
        "GIT_WORK_TREE": str(parent),
        "GIT_INDEX_FILE": str(metadata / "index"),
        "GIT_COMMON_DIR": str(metadata),
        "GIT_CONFIG_GLOBAL": str(hostile_config),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "user.name",
        "GIT_CONFIG_VALUE_0": "Synthetic Wrong Identity",
        "GIT_AUTHOR_NAME": "Synthetic Wrong Identity",
    }
    for key, value in injected.items():
        monkeypatch.setenv(key, value)
    real_run = subprocess.run
    observed_names: list[set[str]] = []

    def observe(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        child_env = kwargs["env"]
        names = set(child_env)
        observed_names.append(names)
        excluded = set(injected) - {"GIT_CONFIG_GLOBAL", "GIT_AUTHOR_NAME"}
        assert excluded.isdisjoint(names)
        assert child_env["GIT_CONFIG_GLOBAL"] == os.devnull
        assert child_env["GIT_CONFIG_NOSYSTEM"] == "1"
        assert child_env["GIT_AUTHOR_NAME"] == "Publication Test"
        return real_run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", observe)
    child = tmp_path / "synthetic-child"
    child.mkdir()
    _publication_git(child, "init", "-q", f"--template={template}")
    assert Path(_publication_git(child, "rev-parse", "--show-toplevel")) == child
    assert _publication_git(child, "var", "GIT_AUTHOR_IDENT").startswith(
        "Publication Test <publication@example.invalid> "
    )
    assert len(observed_names) == 3
    assert {name: (metadata / name).read_bytes() for name in before} == before


def _publication_closeout_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Use real draft, material manifest, self-review ingestion and seal rendering."""
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GH_TOKEN", "opaque")
    monkeypatch.setenv("GITHUB_TOKEN", "opaque")
    repo = tmp_path / "publication-repo"
    repo.mkdir()
    empty_template = tmp_path / "empty-git-template"
    empty_template.mkdir()
    _publication_git(repo, "init", "-q", f"--template={empty_template}")
    (repo / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("Synthetic root instructions.\n", encoding="utf-8")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _publication_git(repo, "add", "-A")
    _publication_git(repo, "commit", "-qm", "base")
    base = _publication_git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("material\n", encoding="utf-8")
    _publication_git(repo, "add", "README.md")
    _publication_git(repo, "commit", "-qm", "material")
    head = _publication_git(repo, "rev-parse", "HEAD")
    snapshot = PrSnapshot("owner/repo", 42, base, head, (PrCommitEvidence(head, None),))
    monkeypatch.setattr(closeout, "REPO_ROOT", repo)
    monkeypatch.setattr(closeout, "STATE_ROOT", repo / "artifacts/orchestration/pr_review_closeout")
    monkeypatch.setattr(evidence, "_REPO_ROOT", repo)
    target = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    target.parent.mkdir(parents=True)
    monkeypatch.setenv("REVIEW_MAPPING_ARTIFACT_DIR", str(target.parent))
    monkeypatch.setattr(closeout, "fetch_pr_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(closeout, "assert_snapshot_unchanged", lambda *_a, **_k: None)
    manifest = evidence.compute_material_manifest(
        repo, base_ref_oid=base, head_ref_oid=head, pr_number=42
    )
    report = _self_review_report_payload(
        changed_files=("README.md",),
        base_ref_oid=base,
        merge_base_sha=manifest.merge_base_sha,
        material_head_sha=head,
        material_digest=manifest.digest,
    )
    report["scope_reviewed"]["diff_summary"] = {
        "files": manifest.diff_summary.files,
        "additions": manifest.diff_summary.additions,
        "deletions": manifest.diff_summary.deletions,
        "changed_lines": manifest.diff_summary.additions + manifest.diff_summary.deletions,
    }
    report_path = tmp_path / "self-review.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    freeze = {
        "base_ref_oid": base,
        "digest": manifest.digest,
        "material_head_sha": head,
        "merge_base_sha": manifest.merge_base_sha,
        "policy_version": evidence.MATERIAL_POLICY_VERSION,
    }
    state = {
        "schema_version": closeout.DRAFT_SCHEMA_VERSION,
        "repository": "owner/repo",
        "pr_number": 42,
        "dispositions": [],
        "experiment_result": None,
        "packet": None,
        "freeze": freeze,
    }
    closeout._write_state(state)
    args = Namespace(pr_number=42, repo="owner/repo", self_review_report=str(report_path))
    receipt = evidence.ingest_repo_native_self_review_receipt(
        report_path, material_manifest=manifest
    )
    review, security = evidence.build_provider_no_claim_pair(
        base_revision=manifest.merge_base_sha, head_revision=head, material_digest=manifest.digest
    )
    seal = {
        "authority": evidence.RECEIPT_AUTHORITY,
        "schema_version": evidence.SEAL_SCHEMA_VERSION,
        "repository": "owner/repo",
        "pr_number": 42,
        "material": freeze,
        "code_review": review,
        "codex_security": security,
        "self_review": receipt,
    }
    return {
        "repo": repo,
        "target": target,
        "args": args,
        "state": state,
        "seal": seal,
        "snapshot": snapshot,
        "markdown": closeout._render_mapping(state, seal),
    }


@pytest.mark.parametrize("mask", [0o022, 0o077, 0o777])
def test_closeout_publication_registered_seal_satisfies_strict_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mask: int
) -> None:
    fixture = _publication_closeout_fixture(tmp_path, monkeypatch)
    old_mask = os.umask(mask)
    try:
        closeout._cmd_seal(fixture["args"])
    finally:
        os.umask(old_mask)
    target = fixture["target"]
    raw = evidence.read_closeout_candidate_bytes(fixture["repo"], pr_number=42)
    assert stat.S_IMODE(target.stat().st_mode) == 0o644
    assert raw == fixture["markdown"].encode("utf-8")
    assert stat.S_IMODE(closeout._state_path(42).stat().st_mode) == 0o600


@pytest.mark.parametrize("replace_existing", [False, True])
@pytest.mark.parametrize("mask", [0o000, 0o077])
def test_closeout_publication_private_default_and_state_stay_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replace_existing: bool, mask: int
) -> None:
    monkeypatch.setattr(closeout, "STATE_ROOT", tmp_path / "private-state")
    target = tmp_path / "default.txt"
    state_path = closeout._state_path(42)
    if replace_existing:
        for path in (target, state_path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("prior public bytes", encoding="utf-8")
            path.chmod(0o644)
    old_mask = os.umask(mask)
    try:
        closeout._atomic_write(target, "private default\n")
        closeout._write_state({"pr_number": 42, "value": "private draft"})
    finally:
        os.umask(old_mask)
    assert target.read_bytes() == b"private default\n"
    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "pr_number": 42,
        "value": "private draft",
    }
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600


def test_closeout_publication_descriptor_mode_follows_flush_and_precedes_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "public.md"
    expected = "complete public mapping\n".encode("utf-8")
    real_fchmod, real_fsync, real_replace = os.fchmod, os.fsync, os.replace
    events: list[str] = []

    def set_mode(fd: int, mode: int) -> None:
        assert os.pread(fd, len(expected) + 1, 0) == expected
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o600
        assert not target.exists()
        events.append("mode")
        real_fchmod(fd, mode)

    def sync(fd: int) -> None:
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o644
        events.append("sync")
        real_fsync(fd)

    def replace(source: str, destination: Path) -> None:
        assert Path(source).read_bytes() == expected
        assert stat.S_IMODE(Path(source).stat().st_mode) == 0o644
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(closeout.os, "fchmod", set_mode)
    monkeypatch.setattr(closeout.os, "fsync", sync)
    monkeypatch.setattr(closeout.os, "replace", replace)
    closeout._atomic_write(target, expected.decode("utf-8"), mode=0o644)
    assert events == ["mode", "sync", "replace"]
    assert target.read_bytes() == expected


def test_closeout_publication_mode_failure_preserves_prior_target_and_cleans_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "public.md"
    target.write_bytes(b"prior target\n")
    target.chmod(0o640)
    calls: list[int] = []

    def fail_mode(fd: int, mode: int) -> None:
        assert mode == 0o644
        assert os.pread(fd, 100, 0) == b"complete replacement\n"
        calls.append(mode)
        raise OSError("synthetic descriptor-mode failure")

    monkeypatch.setattr(closeout.os, "fchmod", fail_mode)
    with pytest.raises(OSError, match="synthetic descriptor-mode failure"):
        closeout._atomic_write(target, "complete replacement\n", mode=0o644)
    assert calls == [0o644]
    assert target.read_bytes() == b"prior target\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o640
    assert list(tmp_path.glob(".public.md.*.tmp")) == []

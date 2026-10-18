"""Registered closeout publication must satisfy its unchanged filesystem consumer."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    historical_base_outside: bool = False,
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
    if historical_base_outside:
        _publication_git(repo, "checkout", "-qb", "historical-target", base)
        (repo / "target-only.txt").write_text("historical target advance\n", encoding="utf-8")
        _publication_git(repo, "add", "target-only.txt")
        _publication_git(repo, "commit", "-qm", "historical unmerged target advance")
        base = _publication_git(repo, "rev-parse", "HEAD")
        _publication_git(repo, "checkout", "-q", "--detach", head)
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
    assert manifest.diff_summary is not None
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


def _retirement_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    stale: bool = True,
    historical_base_outside: bool = False,
    current_base_ahead: bool = False,
    historical_material_unreachable: bool = False,
) -> dict[str, Any]:
    """Build real prior/current projections with bounded base and material-history variants."""
    from scripts.orchestration import pr_commit_identity as identity

    fixture = _publication_closeout_fixture(
        tmp_path, monkeypatch, historical_base_outside=historical_base_outside
    )
    repo, target = fixture["repo"], fixture["target"]
    target.write_text(fixture["markdown"], encoding="utf-8")
    target.chmod(0o644)
    _publication_git(repo, "add", str(target.relative_to(repo)))
    _publication_git(repo, "commit", "-qm", "prior canonical closeout")
    prior = _publication_git(repo, "rev-parse", "HEAD")
    if stale:
        (repo / "README.md").write_text("real changed material\n", encoding="utf-8")
        _publication_git(repo, "add", "README.md")
        _publication_git(repo, "commit", "-qm", "genuine material correction")
    head = _publication_git(repo, "rev-parse", "HEAD")
    old = fixture["snapshot"]
    if historical_material_unreachable:
        canonical = target.read_bytes()
        common = _publication_git(repo, "merge-base", old.base_sha, old.head_sha)
        _publication_git(repo, "checkout", "-qb", "independent-pr", common)
        (repo / "README.md").write_text("independent current material\n", encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical)
        target.chmod(0o644)
        _publication_git(repo, "add", "README.md", str(target.relative_to(repo)))
        _publication_git(repo, "commit", "-qm", "independent head retaining historical canonical")
        head = _publication_git(repo, "rev-parse", "HEAD")
    current_base = old.base_sha
    if current_base_ahead:
        _publication_git(repo, "checkout", "-qb", "current-target", old.base_sha)
        (repo / "target-only.txt").write_text("current target advance\n", encoding="utf-8")
        _publication_git(repo, "add", "target-only.txt")
        _publication_git(repo, "commit", "-qm", "current unmerged target advance")
        current_base = _publication_git(repo, "rev-parse", "HEAD")
        _publication_git(repo, "checkout", "-q", "--detach", head)
    snapshot = PrSnapshot(
        old.repository,
        42,
        current_base,
        head,
        tuple(PrCommitEvidence(sha, None) for sha in dict.fromkeys((old.head_sha, prior, head))),
    )
    current = [snapshot]
    monkeypatch.setattr(closeout, "fetch_pr_snapshot", lambda *_a, **_k: current[0])
    real_classify = identity.classify_commit_ref
    real_ancestor = identity.is_ancestor
    classified: list[str] = []
    resolutions: list[identity.CommitResolution] = []
    commit_requests: list[str] = []
    compare_requests: list[tuple[str, str, int]] = []

    def request_json(url: str, *, token: str) -> dict[str, Any]:
        """Supply only synthetic Commit/Compare responses derived from the real fixture graph."""
        assert token == "opaque"
        parsed = urlsplit(url)
        prefix = "/repos/owner/repo/"
        assert parsed.scheme == "https" and parsed.netloc == "api.github.com"
        assert parsed.path.startswith(prefix) and not parsed.fragment
        route = parsed.path.removeprefix(prefix)
        if route.startswith("commits/"):
            assert not parsed.query
            sha = route.removeprefix("commits/")
            resolved = _publication_git(repo, "rev-parse", f"{sha}^{{commit}}")
            assert resolved == sha
            commit_requests.append(sha)
            return {"sha": resolved}
        assert route.startswith("compare/"), "unexpected fixture API endpoint"
        first, second = route.removeprefix("compare/").split("...")
        query = parse_qs(parsed.query, strict_parsing=True)
        assert set(query) == {"per_page", "page"} and query["per_page"] == ["1"]
        assert len(query["page"]) == 1 and query["page"][0].isdigit()
        page = int(query["page"][0])
        assert page > 0
        behind, ahead = (
            int(count)
            for count in _publication_git(
                repo, "rev-list", "--left-right", "--count", f"{first}...{second}"
            ).split()
        )
        commits = _publication_git(
            repo, "rev-list", "--reverse", "--topo-order", f"{first}..{second}"
        ).splitlines()
        assert len(commits) == ahead
        status = (
            "identical"
            if behind == ahead == 0
            else "ahead" if behind == 0 else "behind" if ahead == 0 else "diverged"
        )
        compare_requests.append((first, second, page))
        return {
            "status": status,
            "ahead_by": ahead,
            "behind_by": behind,
            "base_commit": {"sha": first},
            "head_commit": {"sha": second},
            "merge_base_commit": {"sha": _publication_git(repo, "merge-base", first, second)},
            "total_commits": len(commits),
            "commits": [{"sha": sha} for sha in commits[page - 1 : page]],
        }

    def classify(sha: str, observed: PrSnapshot, *, token: str) -> identity.CommitResolution:
        """Run the canonical classifier with explicit supported request injection and record its result."""
        assert observed is current[0]
        resolved = real_classify(sha, observed, token=token, request_json=request_json)
        classified.append(sha)
        resolutions.append(resolved)
        return resolved

    def ancestor(
        first: identity.RepositoryCommitRef,
        second: identity.RepositoryCommitRef,
        *,
        repository: str,
        token: str,
    ) -> bool:
        """Run the canonical Compare validator against the Git-derived paginated transport."""
        return real_ancestor(
            first, second, repository=repository, token=token, request_json=request_json
        )

    monkeypatch.setattr(identity, "classify_commit_ref", classify)
    monkeypatch.setattr(identity, "is_ancestor", ancestor)
    monkeypatch.setattr(closeout, "classify_commit_ref", classify)
    monkeypatch.setattr(closeout, "is_ancestor", ancestor)
    fixture.update(
        snapshot=snapshot,
        prior=prior,
        classified=classified,
        resolutions=resolutions,
        commit_requests=commit_requests,
        compare_requests=compare_requests,
        identity_snapshot=current,
    )
    return fixture


def _assert_real_retirement_identities(fixture: dict[str, Any]) -> None:
    """Verify actual ref kinds and exclusively the required paginated material-to-head relation."""
    from scripts.orchestration import pr_commit_identity as identity

    snapshot = fixture["identity_snapshot"][0]
    historical = fixture["seal"]["material"]
    material, base = historical["material_head_sha"], historical["base_ref_oid"]
    assert fixture["classified"] == [snapshot.head_sha, material, base, snapshot.base_sha]
    assert fixture["commit_requests"] == fixture["classified"]
    assert all(isinstance(ref, identity.RepositoryCommitRef) for ref in fixture["resolutions"])
    assert [ref.kind for ref in fixture["resolutions"]] == [
        identity.CommitRefKind.PR_HEAD,
        identity.CommitRefKind.PR_COMMIT,
        identity.CommitRefKind.REPO_COMMIT_OUTSIDE_PR,
        identity.CommitRefKind.REPO_COMMIT_OUTSIDE_PR,
    ]
    total = int(
        _publication_git(fixture["repo"], "rev-list", "--count", f"{material}..{snapshot.head_sha}")
    )
    pages = [1] if total <= 1 else [1, total]
    assert fixture["compare_requests"] == [(material, snapshot.head_sha, page) for page in pages]


def _retirement_payload_state(fixture: dict[str, Any]) -> tuple[Path, tuple[bytes, ...]]:
    """Stage then dirty a payload and capture canonical, full index, draft and payload bytes."""
    repo = fixture["repo"]
    payload = repo / "README.md"
    payload.write_text("admitted staged payload\n", encoding="utf-8")
    _publication_git(repo, "add", "README.md")
    payload.write_text("admitted unstaged payload\n", encoding="utf-8")
    paths = (fixture["target"], repo / ".git/index", closeout._state_path(42), payload)
    return payload, tuple(path.read_bytes() for path in paths)


@pytest.mark.parametrize(
    "historical_base_outside",
    [False, True],
    ids=["current-base-ahead", "historical-base-outside-head"],
)
def test_retire_stale_accepts_unmerged_base_tips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, historical_base_outside: bool
) -> None:
    """Retire valid stale projections without requiring either target tip to precede head."""
    fixture = _retirement_fixture(
        tmp_path,
        monkeypatch,
        historical_base_outside=historical_base_outside,
        current_base_ahead=True,
    )
    repo, snapshot, seal = fixture["repo"], fixture["snapshot"], fixture["seal"]
    historical = seal["material"]
    historical_base, material = historical["base_ref_oid"], historical["material_head_sha"]
    assert len({historical_base, material, snapshot.base_sha, snapshot.head_sha}) == 4
    assert _publication_git(repo, "rev-list", snapshot.base_sha, f"^{snapshot.head_sha}")
    historical_not_in_head = _publication_git(
        repo, "rev-list", historical_base, f"^{snapshot.head_sha}"
    )
    assert bool(historical_not_in_head) == historical_base_outside
    if historical_base_outside:
        assert _publication_git(repo, "rev-list", historical_base, f"^{material}")
    old_manifest = evidence.compute_material_manifest(
        repo, base_ref_oid=historical_base, head_ref_oid=material, pr_number=42
    )
    evidence._validate_stale_seal_projection(
        fixture["markdown"],
        repo_root=repo,
        manifest=old_manifest,
        repository="owner/repo",
        pr_number=42,
        require_provider_no_claim=True,
    )
    current = evidence.compute_material_manifest(
        repo, base_ref_oid=snapshot.base_sha, head_ref_oid=snapshot.head_sha, pr_number=42
    )
    assert current.merge_base_sha == old_manifest.merge_base_sha
    assert snapshot.base_sha != historical_base
    payload, before = _retirement_payload_state(fixture)
    checked: list[tuple[str, str]] = []
    real_ancestor = closeout._stale_seal_remote_ancestor

    def observe_ancestry(first: Any, second: Any, **kwargs: Any) -> None:
        """Record selected relation operands while retaining the actual ancestry consumer."""
        checked.append((first.sha, second.sha))
        real_ancestor(first, second, **kwargs)

    monkeypatch.setattr(closeout, "_stale_seal_remote_ancestor", observe_ancestry)
    closeout._cmd_retire_stale(fixture["args"])
    assert fixture["classified"] == [
        snapshot.head_sha,
        material,
        historical_base,
        snapshot.base_sha,
    ]
    assert checked == [(material, snapshot.head_sha)]
    _assert_real_retirement_identities(fixture)
    assert not fixture["target"].exists()
    assert (
        (repo / ".git/index").read_bytes(),
        closeout._state_path(42).read_bytes(),
        payload.read_bytes(),
    ) == before[1:]


@pytest.mark.parametrize("base_role", ["historical", "current"])
@pytest.mark.parametrize("classification", ["unknown", "unavailable", "nonrepository"])
def test_retire_stale_rejects_unaddressable_base_tips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, base_role: str, classification: str
) -> None:
    """Reject only the selected base identity uncertainty before deleting any bound bytes."""
    from scripts.orchestration import pr_commit_identity as identity

    fixture = _retirement_fixture(
        tmp_path, monkeypatch, historical_base_outside=True, current_base_ahead=True
    )
    repo, snapshot = fixture["repo"], fixture["snapshot"]
    historical = fixture["seal"]["material"]
    assert (
        len(
            {
                historical["base_ref_oid"],
                historical["material_head_sha"],
                snapshot.base_sha,
                snapshot.head_sha,
            }
        )
        == 4
    )
    selected = historical["base_ref_oid"] if base_role == "historical" else snapshot.base_sha
    real_classify = identity.classify_commit_ref
    observed: list[str] = []

    def classify_selected(sha: str, *args: Any, **kwargs: Any) -> Any:
        """Mutate one classification while proving every other selected identity normally."""
        observed.append(sha)
        if sha != selected:
            return real_classify(sha, *args, **kwargs)
        if classification == "unknown":
            return identity.ReviewExecutionRef(
                sha, identity.CommitRefKind.API_UNKNOWN, "synthetic unknown"
            )
        if classification == "unavailable":
            return identity.ReviewExecutionRef(
                sha, identity.CommitRefKind.REVIEW_REF_UNAVAILABLE, "synthetic unavailable"
            )
        if classification == "nonrepository":
            return None
        raise AssertionError(f"unsupported classification: {classification}")

    monkeypatch.setattr(identity, "classify_commit_ref", classify_selected)
    payload, before = _retirement_payload_state(fixture)
    with pytest.raises(evidence.ReviewEvidenceError) as rejected:
        closeout._cmd_retire_stale(fixture["args"])
    if classification == "unknown":
        expected = "owner stale-seal commit identity is API_UNKNOWN"
    elif classification == "unavailable" and base_role == "current":
        expected = "owner stale-seal snapshot commit identity conflicts with GitHub"
    else:
        expected = "owner stale-seal commit is not a real live PR commit"
    assert str(rejected.value) == expected
    assert observed[-1] == selected
    assert (
        fixture["target"].read_bytes(),
        (repo / ".git/index").read_bytes(),
        closeout._state_path(42).read_bytes(),
        payload.read_bytes(),
    ) == before


@pytest.mark.parametrize("failure", ["membership", "unreachable"])
def test_retire_stale_preserves_historical_material_constraints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Keep historical material PR membership and real head ancestry as distinct obligations."""
    from scripts.orchestration import pr_commit_identity as identity

    fixture = _retirement_fixture(
        tmp_path,
        monkeypatch,
        historical_base_outside=True,
        current_base_ahead=True,
        historical_material_unreachable=failure == "unreachable",
    )
    repo, snapshot = fixture["repo"], fixture["snapshot"]
    material = fixture["seal"]["material"]["material_head_sha"]
    outside_head = _publication_git(repo, "rev-list", material, f"^{snapshot.head_sha}")
    assert bool(outside_head) == (failure == "unreachable")
    historical_base = fixture["seal"]["material"]["base_ref_oid"]
    historical_manifest = evidence.compute_material_manifest(
        repo, base_ref_oid=historical_base, head_ref_oid=material, pr_number=42
    )
    evidence._validate_stale_seal_projection(
        fixture["markdown"],
        repo_root=repo,
        manifest=historical_manifest,
        repository="owner/repo",
        pr_number=42,
        require_provider_no_claim=True,
    )
    current_manifest = evidence.compute_material_manifest(
        repo, base_ref_oid=snapshot.base_sha, head_ref_oid=snapshot.head_sha, pr_number=42
    )
    assert current_manifest.merge_base_sha == historical_manifest.merge_base_sha
    assert snapshot.base_sha != historical_base
    real_classify = identity.classify_commit_ref
    observed: list[str] = []

    def classify_material(sha: str, *args: Any, **kwargs: Any) -> Any:
        """Change only historical membership or retain positive identity for graph rejection."""
        observed.append(sha)
        resolved = real_classify(sha, *args, **kwargs)
        if sha == material and failure == "membership":
            return identity.RepositoryCommitRef(sha, identity.CommitRefKind.REPO_COMMIT_OUTSIDE_PR)
        return resolved

    monkeypatch.setattr(identity, "classify_commit_ref", classify_material)
    payload, before = _retirement_payload_state(fixture)
    with pytest.raises(evidence.ReviewEvidenceError) as rejected:
        closeout._cmd_retire_stale(fixture["args"])
    assert str(rejected.value) == (
        "owner stale-seal commit is not a real live PR commit"
        if failure == "membership"
        else "owner stale-seal commit is not remotely reachable"
    )
    assert observed[-1] == material
    assert (
        fixture["target"].read_bytes(),
        (repo / ".git/index").read_bytes(),
        closeout._state_path(42).read_bytes(),
        payload.read_bytes(),
    ) == before


def test_retire_stale_preserves_dirty_material_index_and_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Prove retirement preserves staged and unstaged material plus exact index and draft bytes."""
    fixture = _retirement_fixture(tmp_path, monkeypatch)
    repo = fixture["repo"]
    dirty = repo / "README.md"
    dirty.write_text("admitted pending code\n", encoding="utf-8")
    _publication_git(repo, "add", "README.md")
    dirty.write_text("admitted unstaged code\n", encoding="utf-8")
    index, draft = repo / ".git/index", closeout._state_path(42)
    before = index.read_bytes(), draft.read_bytes(), dirty.read_bytes()
    args = closeout._parser().parse_args(
        ["retire-stale", "--repo", "owner/repo", "--pr-number", "42"]
    )
    args.handler(args)
    _assert_real_retirement_identities(fixture)
    assert not fixture["target"].exists()
    assert (index.read_bytes(), draft.read_bytes(), dirty.read_bytes()) == before
    assert "no freeze, disposition, publication or readiness claim" in capsys.readouterr().out


@pytest.mark.parametrize(
    "mutation",
    [
        "current",
        "draft-proof",
        "fetch-draft-proof",
        "snapshot-identity",
        "old-proof",
        "unknown-section",
        "redirect",
        "worktree",
        "index",
        "symlink",
        "hardlink",
        "mode",
        "draft-symlink",
        "index-symlink",
        "head-drift",
        "snapshot-drift",
        "terminal-draft-drift",
        "terminal-worktree-drift",
        "terminal-index-drift",
        "no-auth",
        "wrong-repository",
        "unknown-ref",
        "unavailable-ref",
        "unreachable",
        "missing-object",
        "bad-seal",
        "duplicate-draft",
        "nonfinite-draft",
    ],
)
def test_retire_stale_rejects_uncertainty_without_deleting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """Reject each invalid or drifting retirement prerequisite while retaining the canonical entry."""
    from scripts.orchestration import pr_commit_identity as identity

    fixture = _retirement_fixture(tmp_path, monkeypatch, stale=mutation != "current")
    repo, target, args = fixture["repo"], fixture["target"], fixture["args"]
    draft = closeout._state_path(42)
    if mutation == "current":
        pass
    elif mutation == "draft-proof":
        state = fixture["state"] | {"dispositions": [{"disposition": "FIXED", "commit": "a" * 40}]}
        closeout._write_state(state)
    elif mutation == "fetch-draft-proof":

        def add_proof(*_args: Any, **_kwargs: Any) -> PrSnapshot:
            """Insert proof-bearing draft state during the authenticated snapshot observation."""
            closeout._write_state(
                fixture["state"] | {"dispositions": [{"disposition": "FIXED", "commit": "a" * 40}]}
            )
            snapshot = fixture["snapshot"]
            assert isinstance(snapshot, PrSnapshot)
            return snapshot

        monkeypatch.setattr(closeout, "fetch_pr_snapshot", add_proof)
    elif mutation == "snapshot-identity":
        from dataclasses import replace

        monkeypatch.setattr(
            closeout,
            "fetch_pr_snapshot",
            lambda *_a, **_k: replace(fixture["snapshot"], repository="other/repo"),
        )
    elif mutation in {"old-proof", "unknown-section", "bad-seal"}:
        text = target.read_text(encoding="utf-8")
        if mutation == "old-proof":
            proof_state = fixture["state"] | {
                "dispositions": [
                    {
                        "disposition": "NOT-A-BUG",
                        "evidence": "README.md:1",
                        "reason": "Synthetic retained valid ordinary proof",
                        "url": "https://github.com/owner/repo/pull/42#discussion_r701",
                    }
                ]
            }
            text = closeout._render_mapping(proof_state, fixture["seal"])
            assert closeout.validate_mapping_artifact_text(text) == []
        elif mutation == "unknown-section":
            text = text.replace(
                closeout.NO_ACTIONABLE_LINE, closeout.NO_ACTIONABLE_LINE + "\nunknown proof"
            )
        else:
            text = text.replace(fixture["seal"]["material"]["digest"], "sha256:" + "a" * 64)
        target.write_text(text, encoding="utf-8")
        _publication_git(repo, "add", str(target.relative_to(repo)))
        _publication_git(repo, "commit", "-qm", "synthetic invalid canonical")
        snapshot = fixture["snapshot"]
        from dataclasses import replace

        monkeypatch.setattr(
            closeout,
            "fetch_pr_snapshot",
            lambda *_a, **_k: replace(
                snapshot, head_sha=_publication_git(repo, "rev-parse", "HEAD")
            ),
        )
    elif mutation == "redirect":
        redirect = tmp_path / "redirect"
        redirect.mkdir()
        monkeypatch.setenv("REVIEW_MAPPING_ARTIFACT_DIR", str(redirect))
    elif mutation == "worktree":
        target.write_text("changed candidate\n", encoding="utf-8")
    elif mutation == "index":
        target.write_text("staged replacement\n", encoding="utf-8")
        _publication_git(repo, "add", str(target.relative_to(repo)))
        target.write_text(fixture["markdown"], encoding="utf-8")
    elif mutation in {"symlink", "draft-symlink", "index-symlink"}:
        selected = (
            target
            if mutation == "symlink"
            else (draft if mutation == "draft-symlink" else repo / ".git/index")
        )
        carrier = tmp_path / "external-carrier"
        carrier.write_bytes(selected.read_bytes())
        selected.unlink()
        selected.symlink_to(carrier)
    elif mutation == "hardlink":
        os.link(target, tmp_path / "hardlink-alias")
    elif mutation == "mode":
        target.chmod(0o755)
    elif mutation == "head-drift":
        snapshot = fixture["snapshot"]
        from dataclasses import replace

        monkeypatch.setattr(
            closeout, "fetch_pr_snapshot", lambda *_a, **_k: replace(snapshot, head_sha="f" * 40)
        )
    elif mutation in {
        "snapshot-drift",
        "terminal-draft-drift",
        "terminal-worktree-drift",
        "terminal-index-drift",
    }:

        def drift(*_args: Any, **_kwargs: Any) -> None:
            """Change one bound observation after snapshot verification to exercise terminal drift
            checks.
            """
            if mutation == "snapshot-drift":
                raise identity.CommitIdentityError("synthetic authenticated drift")
            if mutation == "terminal-draft-drift":
                draft.write_bytes(draft.read_bytes() + b" ")
            elif mutation == "terminal-worktree-drift":
                target.write_bytes(target.read_bytes() + b" ")
            else:
                (repo / "README.md").write_text("staged concurrent edit\n", encoding="utf-8")
                _publication_git(repo, "add", "README.md")

        monkeypatch.setattr(closeout, "assert_snapshot_unchanged", drift)
    elif mutation == "no-auth":
        monkeypatch.delenv("GH_TOKEN")
        monkeypatch.delenv("GITHUB_TOKEN")
    elif mutation == "wrong-repository":
        args.repo = "other/repo"
    elif mutation in {"unknown-ref", "unavailable-ref"}:
        kind = (
            identity.CommitRefKind.API_UNKNOWN
            if mutation == "unknown-ref"
            else identity.CommitRefKind.REVIEW_REF_UNAVAILABLE
        )
        monkeypatch.setattr(
            identity,
            "classify_commit_ref",
            lambda *_a, **_k: identity.ReviewExecutionRef(
                "f" * 40, kind, "synthetic identity uncertainty"
            ),
        )
    elif mutation == "unreachable":
        monkeypatch.setattr(identity, "is_ancestor", lambda *_a, **_k: False)
    elif mutation == "missing-object":
        monkeypatch.setattr(
            closeout,
            "_stale_seal_material_manifest",
            lambda *_a, **_k: (_ for _ in ()).throw(
                evidence.ReviewEvidenceError("synthetic missing object")
            ),
        )
    elif mutation == "duplicate-draft":
        draft.write_text(
            draft.read_text().replace(
                '"dispositions":[]', '"dispositions":[{"proof":"retained"}],"dispositions":[]'
            ),
            encoding="utf-8",
        )
    elif mutation == "nonfinite-draft":
        draft.write_text(
            draft.read_text().replace('"packet":null', '"packet":NaN'), encoding="utf-8"
        )
    else:
        raise AssertionError(f"unsupported retirement mutation: {mutation}")
    before = target.read_bytes()
    if mutation == "current":
        index = repo / ".git/index"
        state_before = before, index.read_bytes(), draft.read_bytes()
        with pytest.raises(closeout.CloseoutError) as rejected:
            closeout._cmd_retire_stale(args)
        assert str(rejected.value) == (
            "retirement requires positive base, merge-base or digest staleness"
        )
        assert (target.read_bytes(), index.read_bytes(), draft.read_bytes()) == state_before
        return
    with pytest.raises(
        (closeout.CloseoutError, evidence.ReviewEvidenceError, identity.CommitIdentityError)
    ):
        closeout._cmd_retire_stale(args)
    assert target.exists()
    if mutation == "fetch-draft-proof":
        assert closeout._load_state(42)["dispositions"] == [
            {"disposition": "FIXED", "commit": "a" * 40}
        ]
    if mutation != "terminal-worktree-drift":
        assert target.read_bytes() == before


@pytest.mark.parametrize("pr_number", [0, -1, True, False, 42.0, "42", None])
def test_closeout_state_dir_rejects_invalid_pr_numbers(pr_number: object) -> None:
    """Reject nonpositive or non-integer PR identities at the actual directory guard."""
    assert closeout._state_dir(42) == closeout.STATE_ROOT / "PR_42"
    with pytest.raises(closeout.CloseoutError) as rejected:
        closeout._state_dir(cast(int, pr_number))
    assert str(rejected.value) == "pr_number must be positive"


@pytest.mark.parametrize("index_form", ["relative", "absolute"])
def test_retire_stale_local_binding_preserves_real_index_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, index_form: str
) -> None:
    """Bind unchanged canonical, index and draft bytes using either real index-path form."""
    fixture = _retirement_fixture(tmp_path, monkeypatch)
    repo, target = fixture["repo"], fixture["target"]
    real_git = closeout._git
    native_index = Path(real_git("rev-parse", "--git-path", "index"))
    index = native_index if native_index.is_absolute() else repo / native_index
    index = index.resolve(strict=True)
    draft = closeout._state_path(42)
    before = target.read_bytes(), index.read_bytes(), draft.read_bytes()
    observed: list[str] = []

    def render_index_path(*args: str) -> str:
        """Render only the real Git index lookup while every Git operation still executes."""
        response = real_git(*args)
        if args == ("rev-parse", "--git-path", "index"):
            actual = Path(response)
            assert (actual if actual.is_absolute() else repo / actual).resolve(strict=True) == index
            response = str(index) if index_form == "absolute" else os.path.relpath(index, repo)
            assert Path(response).is_absolute() == (index_form == "absolute")
            observed.append(response)
        return response

    monkeypatch.setattr(closeout, "_git", render_index_path)
    bound = closeout._retirement_local_binding(42, fixture["snapshot"].head_sha)
    assert len(observed) == 1
    assert bound == before
    assert (target.read_bytes(), index.read_bytes(), draft.read_bytes()) == before


def _ordinary_retirement_closeout_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Exercise Q_fix retirement, real docs M, freeze M, FIXED-Q_fix and ADD-R."""
    from dataclasses import replace

    fixture = _retirement_fixture(tmp_path, monkeypatch)
    repo, args = fixture["repo"], fixture["args"]
    closeout._cmd_retire_stale(args)
    _assert_real_retirement_identities(fixture)
    (repo / "README.md").write_text(
        "real timestamp and retirement implementation Q\n", encoding="utf-8"
    )
    _publication_git(repo, "add", "README.md", "docs/review/PR_42_FIXED_MAPPING.md")
    _publication_git(
        repo, "commit", "-qm", "fix genuine governance defect and retire stale empty artifact"
    )
    q = _publication_git(repo, "rev-parse", "HEAD")
    (repo / "AGENTS.md").write_text(
        "Synthetic root instructions.\n"
        "The executable fix retires the stale empty artifact before final material freeze.\n"
        "A later real policy commit is material; the seal binds it and FIXED names its fix ancestor.\n",
        encoding="utf-8",
    )
    _publication_git(repo, "add", "AGENTS.md")
    _publication_git(repo, "commit", "-qm", "docs(agents): update retirement instructions")
    material = _publication_git(repo, "rev-parse", "HEAD")
    snapshot = replace(
        fixture["snapshot"],
        head_sha=material,
        commits=(
            *fixture["snapshot"].commits,
            PrCommitEvidence(q, None),
            PrCommitEvidence(material, None),
        ),
    )
    current = fixture["identity_snapshot"]
    current[0] = snapshot
    closeout._cmd_freeze(args)
    root = "https://github.com/owner/repo/pull/42#discussion_r700"
    closeout._cmd_add_disposition(
        Namespace(
            pr_number=42,
            url=root,
            disposition="FIXED",
            commit=q,
            evidence="README.md:1; Q retires stale canonical artifact; R will regenerate it",
            reason=None,
            backlog=None,
            cause=None,
            review_ref=None,
            verified_fix=None,
        )
    )
    manifest = evidence.compute_material_manifest(
        repo, base_ref_oid=snapshot.base_sha, head_ref_oid=material, pr_number=42
    )
    report = _self_review_report_payload(
        changed_files=("AGENTS.md", "README.md"),
        base_ref_oid=snapshot.base_sha,
        merge_base_sha=manifest.merge_base_sha,
        material_head_sha=material,
        material_digest=manifest.digest,
    )
    assert manifest.diff_summary is not None
    report["scope_reviewed"]["diff_summary"] = {
        "files": manifest.diff_summary.files,
        "additions": manifest.diff_summary.additions,
        "deletions": manifest.diff_summary.deletions,
        "changed_lines": manifest.diff_summary.additions + manifest.diff_summary.deletions,
    }
    Path(args.self_review_report).write_text(json.dumps(report), encoding="utf-8")
    closeout._cmd_seal(args)
    _publication_git(repo, "add", "docs/review/PR_42_FIXED_MAPPING.md")
    _publication_git(repo, "commit", "-qm", "canonical ordinary mapping closeout")
    r = _publication_git(repo, "rev-parse", "HEAD")
    current[0] = replace(
        snapshot, head_sha=r, commits=(*snapshot.commits, PrCommitEvidence(r, None))
    )
    fixture.update(q=q, m=material, r=r, root=root, snapshot=current[0])
    return fixture


def test_retire_stale_registered_q_then_normal_mapping_add_r(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bind the seal to docs material M and FIXED to Q_fix before the sole mapping ADD-R."""
    from scripts.orchestration import pr_commit_identity as identity

    fixture = _ordinary_retirement_closeout_fixture(tmp_path, monkeypatch)
    seal = closeout.validate_live_mapping(repository="owner/repo", pr_number=42, token="opaque")
    assert all(isinstance(ref, identity.RepositoryCommitRef) for ref in fixture["resolutions"])
    assert any(
        ref.sha == fixture["q"] and ref.kind is identity.CommitRefKind.PR_COMMIT
        for ref in fixture["resolutions"]
    )
    assert fixture["resolutions"][-1].sha == fixture["m"]
    assert fixture["resolutions"][-1].kind is identity.CommitRefKind.PR_COMMIT
    assert (fixture["q"], fixture["m"], 1) in fixture["compare_requests"]
    assert seal["material"]["material_head_sha"] == fixture["m"]
    assert seal["self_review"]["material_head_sha"] == fixture["m"]
    assert closeout._load_state(42)["freeze"]["material_head_sha"] == fixture["m"]
    repo = fixture["repo"]
    assert _publication_git(repo, "rev-parse", f"{fixture['r']}^") == fixture["m"]
    assert _publication_git(repo, "rev-parse", f"{fixture['m']}^") == fixture["q"]
    assert fixture["m"] != fixture["q"]
    assert (
        _publication_git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", fixture["m"])
        == "AGENTS.md"
    )
    assert (
        _publication_git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", fixture["r"])
        == "A\tdocs/review/PR_42_FIXED_MAPPING.md"
    )
    assert (
        _publication_git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", fixture["q"])
        == "M\tREADME.md\nD\tdocs/review/PR_42_FIXED_MAPPING.md"
    )
    text = fixture["target"].read_text(encoding="utf-8")
    assert f"- {fixture['root']} -> {fixture['q']}" in text
    assert "OWNER INSPECTED" not in text

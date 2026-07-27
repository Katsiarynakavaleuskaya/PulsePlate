from __future__ import annotations

import ast
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from scripts.ci import check_trusted_protected_pr_policy as policy
from scripts.orchestration import pr_review_evidence as evidence_module
from scripts.orchestration.pr_review_evidence import (
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    MaterialDiffSummary,
    ReviewEvidenceError,
    build_provider_no_claim_pair,
    compute_material_manifest,
    render_embedded_review_seal,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/trusted_protected_pr_policy.yml"
VALIDATOR_PATH = ROOT / "scripts/ci/check_trusted_protected_pr_policy.py"


def _git(repo: Path, *args: str) -> str:
    git = shutil.which("git")
    assert git is not None
    run_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    run_env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    completed = subprocess.run(
        [git, *args],
        cwd=repo,
        env=run_env,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_git_helper_ignores_caller_hook_repository_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "hook-caller.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "hook-caller-worktree"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "hook-caller.index"))

    _git(repo, "init", "-q")

    assert Path(_git(repo, "rev-parse", "--show-toplevel")) == repo
    assert Path(policy._git(repo, ("rev-parse", "--show-toplevel")).decode().strip()) == repo


def _self_review_receipt(
    *,
    base_ref_oid: str,
    merge_base_sha: str,
    material_head_sha: str,
    material_digest: str,
    changed_files: tuple[str, ...],
    material_diff_summary: dict[str, int],
) -> dict[str, Any]:
    report = {
        "actionable_findings_count": 0,
        "base_ref_oid": base_ref_oid,
        "calibration": {},
        "coordinator_packet": {},
        "decision_log": [],
        "deferred_followups": [],
        "findings": [],
        "findings_count": 0,
        "gate_plan": [],
        "generated_at_utc": "2026-07-27T00:00:00Z",
        "material_digest": material_digest,
        "material_head_sha": material_head_sha,
        "merge_base_sha": merge_base_sha,
        "mode": "dry-run-report",
        "review_source_status": [],
        "role_review": [],
        "schema_version": "2.0.0",
        "scope_reviewed": {
            "changed_files": list(changed_files),
            "diff_summary": material_diff_summary,
            "fixed_mapping_errors": [],
            "pr_metadata_available": True,
            "scoped_agents_md": evidence_module._applicable_scoped_agents(
                changed_files,
                material_head_sha=material_head_sha,
            ),
        },
        "warnings": [],
    }
    canonical = json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "actionable_findings_count": 0,
        "authority": "repo_native_pulseplate_pr_review_advisory",
        "blocking": False,
        "findings_count": 0,
        "material_digest": material_digest,
        "material_head_sha": material_head_sha,
        "report_payload": report,
        "report_sha256": "sha256:" + hashlib.sha256(canonical).hexdigest(),
        "review_claim": "none",
        "review_tool": "pulseplate-pr-review",
        "schema_version": "pulseplate.self-review-advisory/v1",
        "status": "advisory_report_attached",
    }


def test_workflow_is_base_owned_read_only_and_never_checks_out_pr_code() -> None:
    raw = WORKFLOW_PATH.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    assert set(loaded[True]) == {"pull_request_target"}
    assert loaded[True]["pull_request_target"]["branches"] == ["main"]
    assert loaded[True]["pull_request_target"]["types"] == [
        "opened",
        "reopened",
        "synchronize",
        "ready_for_review",
        "edited",
        "labeled",
        "unlabeled",
    ]
    assert loaded["permissions"] == {
        "actions": "read",
        "checks": "read",
        "contents": "read",
        "pull-requests": "read",
        "statuses": "read",
    }
    assert loaded["concurrency"] == {
        "group": "trusted-protected-pr-policy-${{ github.event.pull_request.number }}",
        "cancel-in-progress": True,
    }
    job = loaded["jobs"]["trusted-protected-pr-policy"]
    assert job["name"] == "trusted-protected-pr-policy"
    assert job["timeout-minutes"] == 50
    checkout = job["steps"][0]
    assert checkout["uses"] == ("actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd")
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    assert checkout["with"]["persist-credentials"] is False
    assert "secrets." not in raw
    assert job["steps"][1]["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "GITHUB_TOKEN": "${{ github.token }}",
    }
    assert "pull_request.head.sha" not in checkout["with"]["ref"]


def test_validator_has_no_pr_module_loading_or_process_execution_surface() -> None:
    source = VALIDATOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "importlib" not in imported
    assert "runpy" not in imported
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not {"eval", "exec"} & called_names
    string_literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not {"checkout", "reset", "switch"} & string_literals
    assert "pull_request_target" in source


def test_unprotected_inventory_passes_without_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("head\n", encoding="utf-8")
    _git(repo, "commit", "-am", "head")
    head = _git(repo, "rev-parse", "HEAD")
    target = policy.PullRequestTarget("owner/repo", 7, base, head)
    assert policy.validate_protected_material(repo, target) == ()


def test_protected_inventory_fails_closed_without_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    workflow = repo / ".github/workflows/example.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    workflow.write_text("name: changed\n", encoding="utf-8")
    _git(repo, "commit", "-am", "head")
    head = _git(repo, "rev-parse", "HEAD")
    target = policy.PullRequestTarget("owner/repo", 8, base, head)
    with pytest.raises(ReviewEvidenceError, match="FIXED_MAPPING.md.*failed"):
        policy.validate_protected_material(repo, target)


def test_event_parser_rejects_non_pr_payload(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"repository": {"full_name": "owner/repo"}}))
    with pytest.raises(ReviewEvidenceError, match="not a pull_request_target"):
        policy.load_pull_request_target(event)


def _protected_repo_with_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, policy.PullRequestTarget, str]:
    repo = tmp_path / "protected"
    repo.mkdir()
    monkeypatch.setattr(evidence_module, "_REPO_ROOT", repo)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    (repo / "scripts").mkdir()
    (repo / "scripts/AGENTS.md").write_text("scripts instructions\n", encoding="utf-8")
    guarded = repo / "scripts/ci/example.py"
    guarded.parent.mkdir(parents=True)
    guarded.write_text("ENFORCED = False\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    guarded.write_text("ENFORCED = True\n", encoding="utf-8")
    _git(repo, "commit", "-am", "material")
    material_head = _git(repo, "rev-parse", "HEAD")
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=base,
        head_ref_oid=material_head,
        pr_number=42,
    )
    review, security = build_provider_no_claim_pair(
        base_revision=manifest.merge_base_sha,
        head_revision=material_head,
        material_digest=manifest.digest,
    )
    assert manifest.diff_summary is not None
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": review,
        "codex_security": security,
        "material": {
            "base_ref_oid": base,
            "digest": manifest.digest,
            "material_head_sha": material_head,
            "merge_base_sha": manifest.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
        },
        "pr_number": 42,
        "repository": "owner/repo",
        "schema_version": "pulseplate.pr-review-seal/v1",
        "self_review": _self_review_receipt(
            base_ref_oid=base,
            merge_base_sha=manifest.merge_base_sha,
            material_head_sha=material_head,
            material_digest=manifest.digest,
            changed_files=("scripts/ci/example.py",),
            material_diff_summary=manifest.diff_summary.as_dict(),
        ),
    }
    mapping = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(render_embedded_review_seal(seal), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "mapping closeout")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, policy.PullRequestTarget("owner/repo", 42, base, head), material_head


def test_protected_material_positive_e2e_and_mapping_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, target, _material_head = _protected_repo_with_mapping(tmp_path, monkeypatch)
    assert policy.validate_protected_material(repo, target) == ("scripts/ci/example.py",)

    mapping = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    mapping.write_text(
        mapping.read_text(encoding="utf-8").replace(
            '"review_claim":"none"',
            '"review_claim":"completed"',
        ),
        encoding="utf-8",
    )
    _git(repo, "commit", "-am", "tamper mapping")
    tampered = policy.PullRequestTarget(
        target.repository,
        target.number,
        target.base_sha,
        _git(repo, "rev-parse", "HEAD"),
    )
    with pytest.raises(ReviewEvidenceError) as exc_info:
        policy.validate_protected_material(repo, tampered)
    assert str(exc_info.value) == (
        "provider-neutral review no-claim receipt is malformed, stale, or escalating"
    )


def test_protected_material_binds_seal_to_derived_diff_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, target, _material_head = _protected_repo_with_mapping(tmp_path, monkeypatch)
    manifest = compute_material_manifest(
        repo,
        base_ref_oid=target.base_sha,
        head_ref_oid=target.head_sha,
        pr_number=target.number,
    )
    assert manifest.diff_summary is not None
    observed: list[MaterialDiffSummary | None] = []
    validate_review_seal = policy.validate_review_seal

    def validate_with_observation(
        seal: Any,
        *,
        material_paths: Iterable[str] | None = None,
        material_diff_summary: MaterialDiffSummary | None = None,
    ) -> dict[str, Any]:
        observed.append(material_diff_summary)
        return validate_review_seal(
            seal,
            material_paths=material_paths,
            material_diff_summary=material_diff_summary,
        )

    monkeypatch.setattr(policy, "validate_review_seal", validate_with_observation)

    assert policy.validate_protected_material(repo, target) == ("scripts/ci/example.py",)
    assert observed == [manifest.diff_summary]


def test_protected_material_rejects_embedded_report_payload_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, target, _material_head = _protected_repo_with_mapping(tmp_path, monkeypatch)
    mapping = repo / "docs/review/PR_42_FIXED_MAPPING.md"
    mapping.write_text(
        mapping.read_text(encoding="utf-8").replace(
            '"generated_at_utc":"2026-07-27T00:00:00Z"',
            '"generated_at_utc":"2026-07-27T00:00:01Z"',
        ),
        encoding="utf-8",
    )
    _git(repo, "commit", "-am", "tamper embedded self-review report")
    tampered = policy.PullRequestTarget(
        target.repository,
        target.number,
        target.base_sha,
        _git(repo, "rev-parse", "HEAD"),
    )

    with pytest.raises(ReviewEvidenceError, match="payload integrity"):
        policy.validate_protected_material(repo, tampered)


def test_candidate_modified_validator_cannot_change_base_owned_execution(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    script = repo / "scripts/ci/check_trusted_protected_pr_policy.py"
    script.parent.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    script.write_text("BASE_OWNED = True\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    target = policy.PullRequestTarget("owner/repo", 42, base, "f" * 40)
    policy.verify_base_owned_execution(repo, target, validator_path=script)

    script.write_text("CANDIDATE_CONTROLLED = True\n", encoding="utf-8")
    with pytest.raises(ReviewEvidenceError, match="differs from the base-owned blob"):
        policy.verify_base_owned_execution(repo, target, validator_path=script)


def test_live_identity_rejects_base_advance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    target = policy.PullRequestTarget("owner/repo", 42, base, "e" * 40)

    def api(url: str, *, token: str) -> dict[str, Any]:
        del token
        if url.endswith("/pulls/42"):
            return {
                "base": {"ref": "main", "sha": base},
                "head": {"sha": target.head_sha},
            }
        return {"object": {"sha": "d" * 40}}

    monkeypatch.setattr(policy, "_api_request", api)
    with pytest.raises(ReviewEvidenceError, match="identity drifted"):
        policy.validate_live_identity(repo, target, token="opaque")


class _FakeApiResponse:
    def __init__(
        self,
        status: int,
        body: bytes,
        *,
        retry_after: str | None = None,
    ) -> None:
        self.status = status
        self.body = body
        self.retry_after = retry_after
        self.read_limits: list[int] = []

    def read(self, amount: int) -> bytes:
        self.read_limits.append(amount)
        return self.body[:amount]

    def getheader(self, name: str) -> str | None:
        return self.retry_after if name.casefold() == "retry-after" else None


class _FakeApiConnection:
    def __init__(self, outcome: _FakeApiResponse | BaseException) -> None:
        self.outcome = outcome
        self.closed = False
        self.headers: dict[str, str] = {}

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str],
    ) -> None:
        assert method == "GET"
        assert path == "/repos/owner/repo"
        self.headers = headers
        if isinstance(self.outcome, BaseException):
            raise self.outcome

    def getresponse(self) -> _FakeApiResponse:
        assert isinstance(self.outcome, _FakeApiResponse)
        return self.outcome

    def close(self) -> None:
        self.closed = True


def _install_fake_api_connections(
    monkeypatch: pytest.MonkeyPatch,
    outcomes: list[_FakeApiResponse | BaseException],
) -> list[_FakeApiConnection]:
    pending = list(outcomes)
    connections: list[_FakeApiConnection] = []

    def connection_factory(host: str, *, timeout: int) -> _FakeApiConnection:
        assert host == "api.github.com"
        assert timeout == 30
        connection = _FakeApiConnection(pending.pop(0))
        connections.append(connection)
        return connection

    monkeypatch.setattr(policy.http.client, "HTTPSConnection", connection_factory)
    return connections


def test_api_request_retries_transport_failures_with_bounded_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "opaque_transport_token"
    success = _FakeApiResponse(200, b'{"ok":true}')
    connections = _install_fake_api_connections(
        monkeypatch,
        [
            OSError(f"socket failure containing {token}"),
            http.client.BadStatusLine(f"bad response containing {token}"),
            success,
        ],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(policy.time, "sleep", sleeps.append)

    assert policy._api_request("https://api.github.com/repos/owner/repo", token=token) == {
        "ok": True
    }
    assert sleeps == [1.0, 2.0]
    assert len(connections) == policy._API_REQUEST_ATTEMPTS
    assert all(connection.closed for connection in connections)
    assert connections[-1].headers["Authorization"] == f"Bearer {token}"
    assert success.read_limits == [policy._MAX_API_RESPONSE_BYTES + 1]


def test_api_request_exhausted_transport_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "opaque_must_not_escape"
    connections = _install_fake_api_connections(
        monkeypatch,
        [
            OSError(f"failure containing {token}"),
            http.client.RemoteDisconnected(f"failure containing {token}"),
            OSError(f"failure containing {token}"),
        ],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(policy.time, "sleep", sleeps.append)

    with pytest.raises(ReviewEvidenceError) as exc_info:
        policy._api_request("https://api.github.com/repos/owner/repo", token=token)

    assert str(exc_info.value) == "GitHub API transport failed after 3 attempts"
    assert token not in str(exc_info.value)
    assert sleeps == [1.0, 2.0]
    assert all(connection.closed for connection in connections)


@pytest.mark.parametrize(
    ("status", "retry_after", "expected_delay"),
    [
        (500, None, 1.0),
        (429, None, 1.0),
        (429, "invalid", 1.0),
        (429, "7", 7.0),
        (403, "3", 3.0),
    ],
)
def test_api_request_retries_transient_http_responses(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retry_after: str | None,
    expected_delay: float,
) -> None:
    connections = _install_fake_api_connections(
        monkeypatch,
        [
            _FakeApiResponse(status, b'{"error":"transient"}', retry_after=retry_after),
            _FakeApiResponse(200, b'{"ok":true}'),
        ],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(policy.time, "sleep", sleeps.append)

    assert policy._api_request("https://api.github.com/repos/owner/repo", token="opaque") == {
        "ok": True
    }
    assert sleeps == [expected_delay]
    assert len(connections) == 2


@pytest.mark.parametrize(
    ("status", "retry_after"),
    [
        (400, None),
        (401, None),
        (403, None),
        (403, "invalid"),
        (403, "61"),
    ],
)
def test_api_request_does_not_retry_terminal_http_responses(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retry_after: str | None,
) -> None:
    connections = _install_fake_api_connections(
        monkeypatch,
        [_FakeApiResponse(status, b'{"error":"terminal"}', retry_after=retry_after)],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(policy.time, "sleep", sleeps.append)

    with pytest.raises(ReviewEvidenceError) as exc_info:
        policy._api_request("https://api.github.com/repos/owner/repo", token="opaque")

    assert str(exc_info.value) == f"GitHub API request failed with HTTP {status}"
    assert sleeps == []
    assert len(connections) == 1


def test_api_request_honors_bounded_retry_after_http_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy.time, "time", lambda: 5.0)

    assert policy._bounded_retry_after_seconds("Thu, 01 Jan 1970 00:00:10 GMT") == 5.0
    assert policy._bounded_retry_after_seconds("Thu, 01 Jan 1970 00:02:00 GMT") is None
    assert policy._bounded_retry_after_seconds("61") is None


@pytest.mark.parametrize(
    ("body", "size_limit", "expected_error"),
    [
        (b"12345", 4, "GitHub API response exceeds size limit"),
        (b"not-json", 8 * 1024 * 1024, "GitHub API returned malformed JSON"),
    ],
)
def test_api_request_preserves_terminal_response_guards(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
    size_limit: int,
    expected_error: str,
) -> None:
    connections = _install_fake_api_connections(
        monkeypatch,
        [_FakeApiResponse(200, body)],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(policy, "_MAX_API_RESPONSE_BYTES", size_limit)
    monkeypatch.setattr(policy.time, "sleep", sleeps.append)

    with pytest.raises(ReviewEvidenceError) as exc_info:
        policy._api_request("https://api.github.com/repos/owner/repo", token="opaque")

    assert str(exc_info.value) == expected_error
    assert sleeps == []
    assert len(connections) == 1


def _successful_check_api(
    target: policy.PullRequestTarget,
    *,
    material_paths: tuple[str, ...],
    tampered_workflow: str = "",
    run_base_ref: str | None = None,
    run_base_sha: str | None = None,
    non_pull_request_sibling_for: str | None = None,
    omit_pull_request_run_for: str | None = None,
    rerun_for: str | None = None,
    pull_request_event: object = "pull_request",
    run_payload_id_delta: int = 0,
) -> Any:
    required = policy._required_contexts(material_paths)
    checks: list[dict[str, Any]] = []
    runs: dict[int, dict[str, Any]] = {}
    jobs: dict[int, dict[str, Any]] = {}
    for index, context in enumerate(required, start=1):
        run_id = 1000 + index
        job_id = 2000 + index
        if context.name != omit_pull_request_run_for:
            run_attempt = 2 if context.name == rerun_for else 1
            checks.append(
                {
                    "app": {"id": 15368, "slug": "github-actions"},
                    "conclusion": "success",
                    "details_url": (
                        f"https://github.com/{target.repository}/actions/runs/{run_id}/job/"
                        f"{job_id}"
                    ),
                    "head_sha": target.head_sha,
                    "id": job_id,
                    "name": context.name,
                    "status": "completed",
                }
            )
            runs[run_id] = {
                "created_at": f"2026-07-27T00:{index:02d}:00Z",
                "event": pull_request_event,
                "head_sha": target.head_sha,
                "id": run_id + run_payload_id_delta,
                "name": context.workflow_name,
                "path": tampered_workflow or context.workflow_path,
                "pull_requests": [
                    {
                        "base": {
                            "ref": target.base_ref if run_base_ref is None else run_base_ref,
                            "sha": target.base_sha if run_base_sha is None else run_base_sha,
                        },
                        "head": {"sha": target.head_sha},
                        "number": target.number,
                    }
                ],
                "run_attempt": run_attempt,
            }
            jobs[job_id] = {
                "check_run_url": (
                    f"https://api.github.com/repos/{target.repository}/check-runs/{job_id}"
                ),
                "id": job_id,
                "run_attempt": run_attempt,
                "run_id": run_id,
            }
            if context.name == rerun_for:
                old_job_id = 4000 + index
                checks.append(
                    {
                        "app": {"id": 15368, "slug": "github-actions"},
                        "conclusion": "success",
                        "details_url": (
                            f"https://github.com/{target.repository}/actions/runs/"
                            f"{run_id}/job/{old_job_id}"
                        ),
                        "head_sha": target.head_sha,
                        "id": old_job_id,
                        "name": context.name,
                        "status": "completed",
                    }
                )
                jobs[old_job_id] = {
                    "check_run_url": (
                        f"https://api.github.com/repos/{target.repository}/check-runs/"
                        f"{old_job_id}"
                    ),
                    "id": old_job_id,
                    "run_attempt": 1,
                    "run_id": run_id,
                }
        if context.name == non_pull_request_sibling_for:
            sibling_run_id = 2000 + index
            sibling_job_id = 3000 + index
            checks.append(
                {
                    "app": {"id": 15368, "slug": "github-actions"},
                    "conclusion": "success",
                    "details_url": (
                        f"https://github.com/{target.repository}/actions/runs/"
                        f"{sibling_run_id}/job/{sibling_job_id}"
                    ),
                    "head_sha": target.head_sha,
                    "id": sibling_job_id,
                    "name": context.name,
                    "status": "completed",
                }
            )
            runs[sibling_run_id] = {
                "created_at": "2026-07-27T23:59:00Z",
                "event": "workflow_dispatch",
                "head_sha": "c" * 40,
                "id": sibling_run_id,
                "name": "Untrusted sibling workflow",
                "path": ".github/workflows/untrusted-sibling.yml",
                "pull_requests": "not-a-pull-request-binding",
                "run_attempt": 99,
            }

    def api(url: str, *, token: str) -> Any:
        del token
        if "/check-runs?" in url:
            return {"check_runs": checks}
        if "/statuses?" in url:
            return []
        item_id = int(url.rsplit("/", maxsplit=1)[-1])
        if "/actions/jobs/" in url:
            return jobs[item_id]
        return runs[item_id]

    return api


def test_current_head_checks_accept_exact_runs_and_reject_candidate_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    paths = ("scripts/ci/example.py",)
    monkeypatch.setattr(
        policy,
        "_api_request",
        _successful_check_api(target, material_paths=paths),
    )
    policy.validate_required_checks(target, token="opaque", material_paths=paths)

    monkeypatch.setattr(
        policy,
        "_api_request",
        _successful_check_api(
            target,
            material_paths=paths,
            tampered_workflow=".github/workflows/candidate.yml",
        ),
    )
    with pytest.raises(ReviewEvidenceError, match="base-allowlisted"):
        policy.validate_required_checks(target, token="opaque", material_paths=paths)


def test_current_head_checks_ignore_non_pull_request_sibling_before_exact_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    paths = ("scripts/ci/example.py",)
    monkeypatch.setattr(
        policy,
        "_api_request",
        _successful_check_api(
            target,
            material_paths=paths,
            non_pull_request_sibling_for="lint",
        ),
    )

    policy.validate_required_checks(target, token="opaque", material_paths=paths)


def test_current_head_checks_rank_same_run_jobs_by_their_own_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    paths = ("scripts/ci/example.py",)
    monkeypatch.setattr(
        policy,
        "_api_request",
        _successful_check_api(
            target,
            material_paths=paths,
            rerun_for="lint",
        ),
    )

    policy.validate_required_checks(target, token="opaque", material_paths=paths)


def test_current_head_checks_require_pr_run_when_only_non_pr_sibling_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    paths = ("scripts/ci/example.py",)
    monkeypatch.setattr(
        policy,
        "_api_request",
        _successful_check_api(
            target,
            material_paths=paths,
            non_pull_request_sibling_for="lint",
            omit_pull_request_run_for="lint",
        ),
    )

    with pytest.raises(policy._ChecksPending, match=r"lint=missing"):
        policy.validate_required_checks(target, token="opaque", material_paths=paths)


@pytest.mark.parametrize(
    ("pull_request_event", "run_payload_id_delta", "expected_error"),
    (
        (None, 0, "event is malformed"),
        ("pull_request", 1, "identity is malformed"),
    ),
)
def test_current_head_checks_reject_malformed_linked_run_identity(
    monkeypatch: pytest.MonkeyPatch,
    pull_request_event: object,
    run_payload_id_delta: int,
    expected_error: str,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    paths = ("scripts/ci/example.py",)
    monkeypatch.setattr(
        policy,
        "_api_request",
        _successful_check_api(
            target,
            material_paths=paths,
            pull_request_event=pull_request_event,
            run_payload_id_delta=run_payload_id_delta,
        ),
    )

    with pytest.raises(ReviewEvidenceError, match=expected_error):
        policy.validate_required_checks(target, token="opaque", material_paths=paths)


@pytest.mark.parametrize(
    ("run_base_ref", "run_base_sha"),
    (
        ("release", "a" * 40),
        ("main", "c" * 40),
    ),
)
def test_current_head_checks_reject_run_bound_to_wrong_base(
    monkeypatch: pytest.MonkeyPatch,
    run_base_ref: str,
    run_base_sha: str,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    paths = ("scripts/ci/example.py",)
    monkeypatch.setattr(
        policy,
        "_api_request",
        _successful_check_api(
            target,
            material_paths=paths,
            run_base_ref=run_base_ref,
            run_base_sha=run_base_sha,
        ),
    )

    with pytest.raises(ReviewEvidenceError, match=r"exact PR/base/head"):
        policy.validate_required_checks(target, token="opaque", material_paths=paths)


def test_check_poll_revalidates_identity_and_settles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    identities: list[int] = []
    attempts: list[int] = []
    sleeps: list[float] = []
    monkeypatch.setattr(
        policy,
        "validate_live_identity",
        lambda *_args, **_kwargs: identities.append(1),
    )

    def validate(*_args: Any, **_kwargs: Any) -> None:
        attempts.append(1)
        if len(attempts) <= 4:
            raise policy._ChecksPending("lint=missing")

    monkeypatch.setattr(policy, "validate_required_checks", validate)
    monkeypatch.setattr(policy.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(policy.time, "sleep", sleeps.append)
    policy.poll_required_checks(
        tmp_path,
        target,
        token="opaque",
        material_paths=("scripts/ci/example.py",),
        timeout_seconds=300,
    )
    assert attempts == [1, 1, 1, 1, 1]
    assert identities == [1, 1]
    assert sleeps == [15.0, 30.0, 60.0, 60.0]


def test_check_poll_reuses_actions_runs_but_refreshes_check_and_status_lists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    paths = ("scripts/ci/example.py",)
    required = policy._required_contexts(paths)
    successful_api = _successful_check_api(target, material_paths=paths)
    api_calls: list[str] = []
    check_list_calls = 0

    def api(url: str, *, token: str) -> Any:
        nonlocal check_list_calls
        api_calls.append(url)
        payload = successful_api(url, token=token)
        if "/check-runs?" in url:
            check_list_calls += 1
            checks = [dict(check) for check in payload["check_runs"]]
            if check_list_calls == 1:
                for check in checks:
                    check["status"] = "in_progress"
                    check["conclusion"] = None
            return {"check_runs": checks}
        return payload

    identities: list[int] = []
    sleeps: list[float] = []
    monkeypatch.setattr(policy, "_api_request", api)
    monkeypatch.setattr(
        policy,
        "validate_live_identity",
        lambda *_args, **_kwargs: identities.append(1),
    )
    monkeypatch.setattr(policy.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(policy.time, "sleep", sleeps.append)

    policy.poll_required_checks(
        tmp_path,
        target,
        token="opaque",
        material_paths=paths,
        timeout_seconds=30,
    )

    assert sum("/check-runs?" in url for url in api_calls) == 2
    assert sum("/statuses?" in url for url in api_calls) == 2
    action_run_calls = [url for url in api_calls if "/actions/runs/" in url]
    assert len(action_run_calls) == len(required)
    assert len(set(action_run_calls)) == len(required)
    action_job_calls = [url for url in api_calls if "/actions/jobs/" in url]
    assert len(action_job_calls) == len(required)
    assert len(set(action_job_calls)) == len(required)
    assert identities == [1, 1]
    assert sleeps == [15.0]


def _trust_root_repo(
    tmp_path: Path,
    *,
    changed_path: str,
    add_path: bool = False,
) -> tuple[Path, policy.PullRequestTarget]:
    repo = tmp_path / changed_path.replace("/", "-").replace(".", "_")
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    target_path = repo / changed_path
    if not add_path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text("BASE = True\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("HEAD = True\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "head")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, policy.PullRequestTarget("owner/repo", 42, base, head)


def test_trust_root_rejects_same_path_modified_workflow_bytes(
    tmp_path: Path,
) -> None:
    repo, target = _trust_root_repo(
        tmp_path,
        changed_path=".github/workflows/ci.yml",
    )
    with pytest.raises(ReviewEvidenceError, match="AUTHORITY_ROTATION_REQUIRED.*ci.yml"):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=(".github/workflows/ci.yml",),
        )


@pytest.mark.parametrize(
    "changed_path",
    (
        "scripts/ci_bandit.sh",
        "scripts/ci_pip_audit.sh",
    ),
)
def test_trust_root_rejects_same_path_modified_root_ci_script(
    tmp_path: Path,
    changed_path: str,
) -> None:
    repo, target = _trust_root_repo(
        tmp_path,
        changed_path=changed_path,
    )
    with pytest.raises(
        ReviewEvidenceError,
        match=rf"AUTHORITY_ROTATION_REQUIRED.*{changed_path}",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=(changed_path,),
        )


@pytest.mark.parametrize(
    "changed_path",
    (
        ".github/actions/python-setup/action.yml",
        "pyrightconfig.json",
    ),
)
def test_trust_root_rejects_added_executable_control(
    tmp_path: Path,
    changed_path: str,
) -> None:
    repo, target = _trust_root_repo(
        tmp_path,
        changed_path=changed_path,
        add_path=True,
    )
    with pytest.raises(ReviewEvidenceError, match="AUTHORITY_ROTATION_REQUIRED"):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=(changed_path,),
        )


@pytest.mark.parametrize(
    "changed_path",
    (
        ".github/actions/npm-ci-with-retry/action.yml",
        ".github/workflows/frontend-ci.yml",
    ),
)
@pytest.mark.parametrize(
    "mutation",
    ("add", "delete", "mode", "modify", "symlink"),
)
def test_active_actions_controls_require_rotation_for_every_git_identity_change(
    tmp_path: Path,
    changed_path: str,
    mutation: str,
) -> None:
    repo = tmp_path / f"actions-{mutation}-{changed_path.replace('/', '-')}"
    target_path = repo / changed_path
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "core.filemode", "true")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    if mutation != "add":
        target_path.parent.mkdir(parents=True)
        target_path.write_text("name: base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if mutation == "add":
        target_path.write_text("name: added\n", encoding="utf-8")
    elif mutation == "delete":
        target_path.unlink()
    elif mutation == "mode":
        target_path.chmod(0o755)
    elif mutation == "modify":
        target_path.write_text("name: changed\n", encoding="utf-8")
    else:
        target_path.unlink()
        target_path.symlink_to("../../README.md")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", mutation)
    head = _git(repo, "rev-parse", "HEAD")
    target = policy.PullRequestTarget("owner/repo", 42, base, head)

    with pytest.raises(
        ReviewEvidenceError,
        match=rf"AUTHORITY_ROTATION_REQUIRED.*{re.escape(changed_path)}",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=(changed_path,),
        )


def _additive_vnext_repo(
    tmp_path: Path,
    *,
    case: str,
    include_workflow: bool = True,
    include_validator: bool = True,
    workflow_bytes: bytes | None = None,
    validator_bytes: bytes | None = None,
    extra_authority_path: str | None = None,
    base_has_vnext: bool = False,
    unsafe_identity_path: str | None = None,
    symlink_identity_path: str | None = None,
    modify_v1_validator: bool = False,
) -> tuple[Path, policy.PullRequestTarget, tuple[str, ...]]:
    contract = policy._ADDITIVE_VNEXT_ADMISSION
    repo = tmp_path / f"additive-vnext-{case}"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "core.filemode", "true")
    source_path = repo / contract.validator_source_path
    workflow_path = repo / contract.workflow_path
    validator_path = repo / contract.validator_path
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"exact base-owned checker\n")
    if base_has_vnext:
        workflow_path.parent.mkdir(parents=True)
        workflow_path.write_bytes(contract.workflow_bytes)
        validator_path.write_bytes(source_path.read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")

    material_paths: list[str] = []
    if include_workflow:
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.write_bytes(
            contract.workflow_bytes if workflow_bytes is None else workflow_bytes
        )
        material_paths.append(contract.workflow_path)
    elif base_has_vnext:
        workflow_path.unlink()
        material_paths.append(contract.workflow_path)
    if include_validator:
        validator_path.parent.mkdir(parents=True, exist_ok=True)
        validator_path.write_bytes(
            source_path.read_bytes() if validator_bytes is None else validator_bytes
        )
        material_paths.append(contract.validator_path)
    elif base_has_vnext:
        validator_path.unlink()
        material_paths.append(contract.validator_path)
    if extra_authority_path is not None:
        extra_path = repo / extra_authority_path
        extra_path.parent.mkdir(parents=True, exist_ok=True)
        extra_path.write_text("name: extra\n", encoding="utf-8")
        material_paths.append(extra_authority_path)
    if unsafe_identity_path is not None:
        unsafe_path = repo / unsafe_identity_path
        unsafe_path.chmod(0o755)
    if symlink_identity_path is not None:
        symlink_path = repo / symlink_identity_path
        symlink_path.unlink()
        symlink_path.symlink_to(source_path)
    if modify_v1_validator:
        source_path.write_bytes(b"candidate-modified v1 checker\n")
        material_paths.append(contract.validator_source_path)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "head")
    head = _git(repo, "rev-parse", "HEAD")
    return (
        repo,
        policy.PullRequestTarget("owner/repo", 42, base, head),
        tuple(material_paths),
    )


def test_exact_additive_vnext_bundle_is_the_only_admitted_authority_change(
    tmp_path: Path,
) -> None:
    repo, target, material_paths = _additive_vnext_repo(tmp_path, case="exact")

    policy.validate_trust_root_unchanged(
        repo,
        target,
        material_paths=material_paths,
    )


@pytest.mark.parametrize(
    ("include_workflow", "include_validator"),
    ((True, False), (False, True)),
)
def test_partial_additive_vnext_bundle_requires_rotation(
    tmp_path: Path,
    include_workflow: bool,
    include_validator: bool,
) -> None:
    repo, target, material_paths = _additive_vnext_repo(
        tmp_path,
        case=f"partial-{include_workflow}-{include_validator}",
        include_workflow=include_workflow,
        include_validator=include_validator,
    )

    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*bundle is partial",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=material_paths,
        )


@pytest.mark.parametrize(
    (
        "case",
        "workflow_bytes",
        "validator_bytes",
        "unsafe_identity_path",
        "symlink_identity_path",
    ),
    (
        (
            "unsafe-workflow",
            policy._ADDITIVE_VNEXT_ADMISSION.workflow_bytes.replace(
                b"contents: read", b"contents: write"
            ),
            None,
            None,
            None,
        ),
        ("modified-validator", None, b"candidate checker\n", None, None),
        (
            "executable-workflow",
            None,
            None,
            policy._ADDITIVE_VNEXT_ADMISSION.workflow_path,
            None,
        ),
        (
            "executable-validator",
            None,
            None,
            policy._ADDITIVE_VNEXT_ADMISSION.validator_path,
            None,
        ),
        (
            "symlink-workflow",
            None,
            None,
            None,
            policy._ADDITIVE_VNEXT_ADMISSION.workflow_path,
        ),
        (
            "symlink-validator",
            None,
            None,
            None,
            policy._ADDITIVE_VNEXT_ADMISSION.validator_path,
        ),
    ),
)
def test_malformed_or_unsafe_additive_vnext_bundle_requires_rotation(
    tmp_path: Path,
    case: str,
    workflow_bytes: bytes | None,
    validator_bytes: bytes | None,
    unsafe_identity_path: str | None,
    symlink_identity_path: str | None,
) -> None:
    repo, target, material_paths = _additive_vnext_repo(
        tmp_path,
        case=case,
        workflow_bytes=workflow_bytes,
        validator_bytes=validator_bytes,
        unsafe_identity_path=unsafe_identity_path,
        symlink_identity_path=symlink_identity_path,
    )

    with pytest.raises(ReviewEvidenceError, match="AUTHORITY_ROTATION_REQUIRED"):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=material_paths,
        )


def test_exact_additive_vnext_bundle_cannot_cover_an_extra_authority_change(
    tmp_path: Path,
) -> None:
    extra_path = ".github/workflows/extra.yml"
    repo, target, material_paths = _additive_vnext_repo(
        tmp_path,
        case="extra",
        extra_authority_path=extra_path,
    )

    with pytest.raises(
        ReviewEvidenceError,
        match=rf"AUTHORITY_ROTATION_REQUIRED.*{re.escape(extra_path)}",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=material_paths,
        )


def test_exact_additive_vnext_bundle_cannot_cover_a_v1_authority_change(
    tmp_path: Path,
) -> None:
    contract = policy._ADDITIVE_VNEXT_ADMISSION
    repo, target, material_paths = _additive_vnext_repo(
        tmp_path,
        case="changed-v1",
        modify_v1_validator=True,
    )

    with pytest.raises(
        ReviewEvidenceError,
        match=rf"AUTHORITY_ROTATION_REQUIRED.*{re.escape(contract.validator_source_path)}",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=material_paths,
        )


def test_additive_vnext_admission_is_not_reusable_after_bundle_exists(
    tmp_path: Path,
) -> None:
    repo, target, material_paths = _additive_vnext_repo(
        tmp_path,
        case="non-reusable",
        base_has_vnext=True,
        workflow_bytes=policy._ADDITIVE_VNEXT_ADMISSION.workflow_bytes.replace(
            b"timeout-minutes: 50", b"timeout-minutes: 51"
        ),
        validator_bytes=b"changed checker\n",
    )

    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*not reusable",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=material_paths,
        )


def test_additive_vnext_contract_adds_no_required_or_merge_authority() -> None:
    contract = policy._ADDITIVE_VNEXT_ADMISSION
    workflow = yaml.load(contract.workflow_bytes, Loader=yaml.BaseLoader)

    assert contract.paths == {
        ".github/workflows/trusted_protected_pr_policy_vnext.yml",
        "scripts/ci/check_trusted_protected_pr_policy_vnext.py",
    }
    assert "trusted-protected-pr-policy-vnext" not in policy._BASE_REQUIRED_CONTEXTS
    assert "trusted-protected-pr-policy-vnext" not in (
        policy._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
    )
    assert workflow["permissions"] == {
        "actions": "read",
        "checks": "read",
        "contents": "read",
        "pull-requests": "read",
        "statuses": "read",
    }
    serialized = contract.workflow_bytes.decode("utf-8")
    assert "pull_request_target" in workflow["on"]
    assert workflow["on"]["pull_request_target"]["branches"] == ["main"]
    assert "pull_request.head" not in serialized
    assert "gh pr merge" not in serialized
    assert "branches: write" not in serialized
    assert contract.validator_path in serialized


def test_exact_additive_vnext_bundle_still_requires_seal_and_current_head_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, target, material_paths = _additive_vnext_repo(tmp_path, case="main")
    calls: list[str] = []
    monkeypatch.setattr(policy, "REPO_ROOT", repo)
    monkeypatch.setattr(
        policy,
        "parse_args",
        lambda _argv: SimpleNamespace(event_path=tmp_path / "event.json"),
    )
    monkeypatch.setattr(policy, "load_pull_request_target", lambda _path: target)
    monkeypatch.setattr(policy, "_github_token", lambda: "opaque")
    monkeypatch.setattr(policy, "verify_base_owned_execution", lambda *_args: None)
    monkeypatch.setattr(policy, "validate_live_identity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(policy, "fetch_exact_pr_head", lambda *_args: None)
    monkeypatch.setattr(
        policy,
        "compute_material_manifest",
        lambda *_args, **_kwargs: SimpleNamespace(
            entries=tuple(SimpleNamespace(path=path) for path in material_paths)
        ),
    )
    monkeypatch.setattr(
        policy,
        "validate_protected_material",
        lambda *_args: calls.append("seal") or material_paths,
    )
    monkeypatch.setattr(
        policy,
        "poll_required_checks",
        lambda *_args, **_kwargs: calls.append("checks"),
    )

    assert policy.main([]) == 0
    assert calls == ["seal", "checks"]


def test_unchanged_trust_root_uses_automatic_path(tmp_path: Path) -> None:
    repo, target = _trust_root_repo(
        tmp_path,
        changed_path="README.md",
    )
    policy.validate_trust_root_unchanged(
        repo,
        target,
        material_paths=("README.md",),
    )


@pytest.mark.parametrize(
    ("context_name", "authority_path"),
    (
        ("Determine changed paths (for conditional jobs)", "scripts/ci/ci_risk_profile.py"),
        ("pr_scope_guard", "scripts/design_guard.py"),
        ("pr_scope_guard", "docs/design/figma-manifest.json"),
        ("Trivy ignore-policy expiry", "scripts/ci/check_react_router_rsc_premise.py"),
        ("Docs Phase1 gates", "core/ai/semantic_cache_backend_selection.py"),
        (
            "PR Body Phase2 gates",
            "scripts/orchestration/check_experiment_runner_identity.py",
        ),
        (
            "Private Python proxy health",
            "scripts/ci/check_emergency_wheel_mirror_parity.py",
        ),
        ("lint", ".github/actions/python-setup/**"),
        ("lint", ".nvmrc"),
        ("lint", "conftest.py"),
        ("lint", "coverage.py"),
        ("lint", "frontend/package-lock.json"),
        ("lint", "frontend/package.json"),
        ("lint", "package-lock.json"),
        ("lint", "package.json"),
        ("lint", "pytest_sharding.py"),
        ("lint", "pytest.py"),
        ("lint", "scripts/ci/check_python_startup_hooks.py"),
        ("lint", "scripts/ci/run_main_test_shards.py"),
        ("lint", "scripts.py"),
        ("lint", "requirements-ci-lite.txt"),
        ("lint", "tests/__init__.py"),
        ("lint", "tests/**/__init__.py"),
        ("lint", "tests/conftest.py"),
        ("lint", "tests/**/conftest.py"),
        ("lint", ".yamllint"),
        ("security", "app/__init__.py"),
        ("security", "bmi_visualization.py"),
        ("security", "core/__init__.py"),
        ("security", "core/bmi/__init__.py"),
        ("security", "app/security/production_invariants.py"),
        ("security", "scripts/ci/summarize_bandit_report.py"),
        ("Analyze (actions)", ".github/codeql/extensions/**"),
        ("Analyze (python)", ".github/workflows/codeql.yml"),
        ("security-scan", "Dockerfile"),
        ("security-scan", ".dockerignore"),
        ("security-scan", "trivy/ignore-policy.rego"),
        ("security-scan", "scripts/ci/fetch_docker_source_artifacts.py"),
        (
            "security-scan",
            "docs/telemetry/docker_image_budget.production.json",
        ),
    ),
)
def test_authority_graph_names_exact_transitive_controls(
    context_name: str,
    authority_path: str,
) -> None:
    assert authority_path in policy._CONTEXT_AUTHORITY_INPUTS[context_name]


def test_authority_graph_has_exact_required_context_inventory() -> None:
    expected_contexts = set(policy._BASE_REQUIRED_CONTEXTS) | set(
        policy._OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES
    )
    assert set(policy._CONTEXT_AUTHORITY_INPUTS) == expected_contexts
    assert set(policy._CONTEXT_AUTHORITY_PROJECTIONS) <= expected_contexts
    assert policy._CONTEXT_AUTHORITY_PROJECTIONS["lint"] == (
        policy.AuthorityProjection(
            path="package.json",
            format="json",
            selectors=(
                ("scripts", "preinstall"),
                ("scripts", "install"),
                ("scripts", "postinstall"),
                ("scripts", "prepublish"),
                ("scripts", "preprepare"),
                ("scripts", "prepare"),
                ("scripts", "postprepare"),
            ),
        ),
        policy.AuthorityProjection(
            path="frontend/package.json",
            format="json",
            selectors=(
                ("scripts", "preinstall"),
                ("scripts", "install"),
                ("scripts", "postinstall"),
                ("scripts", "prepublish"),
                ("scripts", "preprepare"),
                ("scripts", "prepare"),
                ("scripts", "postprepare"),
                ("scripts", "prelint"),
                ("scripts", "lint"),
                ("scripts", "postlint"),
                ("scripts", "pretest"),
                ("scripts", "test"),
                ("scripts", "posttest"),
                ("scripts", "pretest:ci"),
                ("scripts", "test:ci"),
                ("scripts", "posttest:ci"),
                ("scripts", "pretest:precommit"),
                ("scripts", "test:precommit"),
                ("scripts", "posttest:precommit"),
                ("scripts", "pretest:coverage"),
                ("scripts", "test:coverage"),
                ("scripts", "posttest:coverage"),
                ("scripts", "pretest:accessibility"),
                ("scripts", "test:accessibility"),
                ("scripts", "posttest:accessibility"),
                ("scripts", "prebuild"),
                ("scripts", "build"),
                ("scripts", "postbuild"),
                ("scripts", "presmoke:css"),
                ("scripts", "smoke:css"),
                ("scripts", "postsmoke:css"),
            ),
        ),
        policy.AuthorityProjection(
            path="pyproject.toml",
            format="toml",
            selectors=(
                ("tool", "black"),
                ("tool", "isort"),
                ("tool", "mypy"),
                ("tool", "pyright"),
                ("tool", "pytest"),
                ("tool", "ruff"),
            ),
        ),
    )


def test_codeowners_is_protected_authority_and_routes_privileged_security() -> None:
    path = ".github/CODEOWNERS"
    material_paths = (path,)

    assert policy.protected_trust_boundary_paths(material_paths) == material_paths
    assert path in policy._all_blob_authority_inputs(material_paths)
    assert policy._protected_or_authority_paths(material_paths) == material_paths
    assert "security" in {required.name for required in policy._required_contexts(material_paths)}


def test_authority_graph_keeps_declarative_subjects_out_of_blanket_control_set() -> None:
    authority_inputs = {
        authority_input
        for inputs in policy._CONTEXT_AUTHORITY_INPUTS.values()
        for authority_input in inputs
    }
    assert "requirements.txt" not in authority_inputs
    assert "scripts/ci/candidate.py" not in authority_inputs
    assert "pyproject.toml" not in authority_inputs


@pytest.mark.parametrize(
    "changed_path",
    (
        "bandit-backend-related.json",
        "requirements.txt",
        "scripts/ci/candidate.py",
    ),
)
def test_declarative_or_unreferenced_subject_does_not_request_authority_rotation(
    tmp_path: Path,
    changed_path: str,
) -> None:
    repo, target = _trust_root_repo(tmp_path, changed_path=changed_path)
    policy.validate_trust_root_unchanged(
        repo,
        target,
        material_paths=(changed_path,),
    )


@pytest.mark.parametrize(
    "changed_path",
    (
        "scripts/design_guard.py",
        "docs/design/figma-manifest.json",
        "scripts/ci/check_pr_body_phase2_gates.py",
        "scripts/ci/check_production_runtime_invariants.py",
        "scripts/ci/check_python_startup_hooks.py",
        "scripts/ci/emergency_python_wheels.json",
        "scripts/ci/fetch_docker_source_artifacts.py",
        "docs/telemetry/docker_image_budget.production.json",
        "Dockerfile",
        ".dockerignore",
        "trivy/ignore-policy.rego",
        ".trivyignore",
        "app/__init__.py",
        "bmi_visualization.py",
        "conftest.py",
        "coverage.py",
        "core/bmi/__init__.py",
        "core/ai/__init__.py",
        "frontend/package-lock.json",
        "frontend/package.json",
        "package-lock.json",
        "package.json",
        "pytest_sharding.py",
        "pytest.py",
        "scripts.py",
        "scripts/ci/run_main_test_shards.py",
        "tests/__init__.py",
        "tests/edges/__init__.py",
        "tests/conftest.py",
        "tests/edges/conftest.py",
        "constraints.txt",
        "requirements-ci-lite.txt",
        "binding.gyp",
        "sitecustomize.py",
        "usercustomize.py",
        ".github/CODEOWNERS",
        ".github/workflows/trusted_protected_pr_policy.yml",
    ),
)
def test_transitive_or_root_control_change_requires_vnext_rotation(
    tmp_path: Path,
    changed_path: str,
) -> None:
    repo, target = _trust_root_repo(tmp_path, changed_path=changed_path)
    with pytest.raises(
        ReviewEvidenceError,
        match=rf"AUTHORITY_ROTATION_REQUIRED.*{re.escape(changed_path)}",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=(changed_path,),
        )


def _frontend_package_repo(
    tmp_path: Path,
    *,
    base_payload: dict[str, Any],
    head_payload: dict[str, Any],
    package_path: str = "frontend/package.json",
) -> tuple[Path, policy.PullRequestTarget]:
    repo = tmp_path / package_path.replace("/", "-").replace(".", "_")
    package = repo / package_path
    package.parent.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    package.write_text(json.dumps(base_payload, sort_keys=True) + "\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    package.write_text(json.dumps(head_payload, sort_keys=True) + "\n", encoding="utf-8")
    _git(repo, "commit", "-am", "head")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, policy.PullRequestTarget("owner/repo", 42, base, head)


def test_root_package_dependency_change_requires_authority_rotation(tmp_path: Path) -> None:
    repo, target = _frontend_package_repo(
        tmp_path,
        base_payload={"dependencies": {"a": "1"}},
        head_payload={"dependencies": {"a": "2"}},
        package_path="package.json",
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*package.json",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=("package.json",),
        )


@pytest.mark.parametrize("lifecycle_script", ("preinstall", "prepare"))
def test_root_package_install_lifecycle_requires_authority_rotation(
    tmp_path: Path,
    lifecycle_script: str,
) -> None:
    repo, target = _frontend_package_repo(
        tmp_path,
        base_payload={"dependencies": {"a": "1"}},
        head_payload={
            "dependencies": {"a": "1"},
            "scripts": {lifecycle_script: "node candidate-controlled.js"},
        },
        package_path="package.json",
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*package.json",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=("package.json",),
        )


def test_frontend_dependency_change_requires_authority_rotation(tmp_path: Path) -> None:
    repo, target = _frontend_package_repo(
        tmp_path,
        base_payload={"scripts": {"test:precommit": "vitest run"}, "dependencies": {"a": "1"}},
        head_payload={"scripts": {"test:precommit": "vitest run"}, "dependencies": {"a": "2"}},
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*frontend/package.json",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=("frontend/package.json",),
        )


def test_frontend_script_change_requires_authority_rotation(tmp_path: Path) -> None:
    repo, target = _frontend_package_repo(
        tmp_path,
        base_payload={"scripts": {"test:precommit": "vitest run"}, "dependencies": {"a": "1"}},
        head_payload={"scripts": {"test:precommit": "true"}, "dependencies": {"a": "1"}},
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*frontend/package.json",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=("frontend/package.json",),
        )


@pytest.mark.parametrize(
    "lifecycle_script",
    (
        "pretest:precommit",
        "posttest:precommit",
    ),
)
def test_frontend_precommit_lifecycle_script_requires_authority_rotation(
    tmp_path: Path,
    lifecycle_script: str,
) -> None:
    repo, target = _frontend_package_repo(
        tmp_path,
        base_payload={
            "scripts": {"test:precommit": "vitest run"},
            "dependencies": {"a": "1"},
        },
        head_payload={
            "scripts": {
                lifecycle_script: "node candidate-controlled.js",
                "test:precommit": "vitest run",
            },
            "dependencies": {"a": "1"},
        },
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*frontend/package.json",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=("frontend/package.json",),
        )


def test_frontend_unrelated_script_change_requires_authority_rotation(tmp_path: Path) -> None:
    repo, target = _frontend_package_repo(
        tmp_path,
        base_payload={
            "scripts": {"dev": "vite", "test:precommit": "vitest run"},
            "dependencies": {"a": "1"},
        },
        head_payload={
            "scripts": {"dev": "vite --debug", "test:precommit": "vitest run"},
            "dependencies": {"a": "1"},
        },
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*frontend/package.json",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=("frontend/package.json",),
        )


def _pyproject_repo(
    tmp_path: Path,
    *,
    base_text: str,
    head_text: str,
) -> tuple[Path, policy.PullRequestTarget]:
    repo = tmp_path / "pyproject"
    repo.mkdir()
    project = repo / "pyproject.toml"
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    project.write_text(base_text, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    project.write_text(head_text, encoding="utf-8")
    _git(repo, "commit", "-am", "head")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, policy.PullRequestTarget("owner/repo", 42, base, head)


def test_pyproject_dependency_only_change_remains_a_subject(tmp_path: Path) -> None:
    repo, target = _pyproject_repo(
        tmp_path,
        base_text=('[project]\ndependencies = ["a==1"]\n' "[tool.black]\nline-length = 100\n"),
        head_text=('[project]\ndependencies = ["a==2"]\n' "[tool.black]\nline-length = 100\n"),
    )
    policy.validate_trust_root_unchanged(
        repo,
        target,
        material_paths=("pyproject.toml",),
    )


def test_pyproject_tool_change_requires_authority_rotation(tmp_path: Path) -> None:
    repo, target = _pyproject_repo(
        tmp_path,
        base_text="[tool.black]\nline-length = 100\n",
        head_text="[tool.black]\nline-length = 88\n",
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*pyproject.toml",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            target,
            material_paths=("pyproject.toml",),
        )


def test_malformed_semantic_input_uses_terminal_rotation_token(tmp_path: Path) -> None:
    repo, target = _frontend_package_repo(
        tmp_path,
        base_payload={
            "scripts": {"test:precommit": "vitest run"},
            "dependencies": {"a": "1"},
        },
        head_payload={
            "scripts": {"test:precommit": "vitest run"},
            "dependencies": {"a": "2"},
        },
    )
    package = repo / "frontend/package.json"
    package.write_text("{not-json\n", encoding="utf-8")
    _git(repo, "commit", "-am", "malformed")
    malformed_target = policy.PullRequestTarget(
        target.repository,
        target.number,
        target.base_sha,
        _git(repo, "rev-parse", "HEAD"),
    )
    with pytest.raises(
        ReviewEvidenceError,
        match="AUTHORITY_ROTATION_REQUIRED.*frontend/package.json.*parse failed",
    ):
        policy.validate_trust_root_unchanged(
            repo,
            malformed_target,
            material_paths=("frontend/package.json",),
        )


@pytest.mark.parametrize(
    "changed_path",
    (
        ".github/workflows/frontend-ci.yml",
        ".github/CODEOWNERS",
        ".nvmrc",
        "app/__init__.py",
        "conftest.py",
        "coverage.py",
        "frontend/package-lock.json",
        "frontend/package.json",
        "package-lock.json",
        "package.json",
        "pytest_sharding.py",
        "pytest.py",
        "ruff.toml",
        "scripts.py",
        "scripts/ci/run_main_test_shards.py",
        "scripts/orchestration/context_pack.py",
        "tests/__init__.py",
        "tests/edges/__init__.py",
        "tests/conftest.py",
        "tests/edges/conftest.py",
        "tests/guards/test_nosec_policy_guard.py",
        "docs/telemetry/docker_image_budget.production.json",
    ),
)
def test_authority_path_cannot_take_unprotected_skip_branch(changed_path: str) -> None:
    assert changed_path in policy._protected_or_authority_paths((changed_path,))


def test_main_skips_authority_and_mapping_for_unprotected_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    live_calls: list[int] = []
    monkeypatch.setattr(
        policy,
        "parse_args",
        lambda _argv: SimpleNamespace(event_path=tmp_path / "event.json"),
    )
    monkeypatch.setattr(policy, "load_pull_request_target", lambda _path: target)
    monkeypatch.setattr(policy, "_github_token", lambda: "opaque")
    monkeypatch.setattr(policy, "verify_base_owned_execution", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        policy,
        "validate_live_identity",
        lambda *_args, **_kwargs: live_calls.append(1),
    )
    monkeypatch.setattr(policy, "fetch_exact_pr_head", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        policy,
        "compute_material_manifest",
        lambda *_args, **_kwargs: SimpleNamespace(entries=(SimpleNamespace(path="README.md"),)),
    )
    monkeypatch.setattr(policy, "_protected_or_authority_paths", lambda _paths: ())
    monkeypatch.setattr(
        policy,
        "validate_trust_root_unchanged",
        lambda *_args, **_kwargs: pytest.fail("unprotected material reached authority rotation"),
    )
    monkeypatch.setattr(
        policy,
        "validate_protected_material",
        lambda *_args, **_kwargs: pytest.fail("unprotected material reached mapping validation"),
    )

    assert policy.main([]) == 0
    assert live_calls == [1, 1]


def test_main_orders_authority_before_protected_seal_and_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    calls: list[str] = []
    monkeypatch.setattr(
        policy,
        "parse_args",
        lambda _argv: SimpleNamespace(event_path=tmp_path / "event.json"),
    )
    monkeypatch.setattr(policy, "load_pull_request_target", lambda _path: target)
    monkeypatch.setattr(policy, "_github_token", lambda: "opaque")
    monkeypatch.setattr(policy, "verify_base_owned_execution", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(policy, "validate_live_identity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(policy, "fetch_exact_pr_head", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        policy,
        "compute_material_manifest",
        lambda *_args, **_kwargs: SimpleNamespace(
            entries=(SimpleNamespace(path="scripts/ci/example.py"),)
        ),
    )
    monkeypatch.setattr(
        policy,
        "_protected_or_authority_paths",
        lambda _paths: ("scripts/ci/example.py",),
    )
    monkeypatch.setattr(
        policy,
        "validate_trust_root_unchanged",
        lambda *_args, **_kwargs: calls.append("authority"),
    )
    monkeypatch.setattr(
        policy,
        "validate_protected_material",
        lambda *_args, **_kwargs: calls.append("seal") or ("scripts/ci/example.py",),
    )
    monkeypatch.setattr(
        policy,
        "poll_required_checks",
        lambda *_args, **_kwargs: calls.append("checks"),
    )

    assert policy.main([]) == 0
    assert calls == ["authority", "seal", "checks"]


@pytest.mark.parametrize(
    "changed_path",
    (
        ".github/workflows/frontend-ci.yml",
        "tests/__init__.py",
        "tests/edges/__init__.py",
    ),
)
def test_main_stops_at_authority_rotation_before_seal_or_check_polling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    changed_path: str,
) -> None:
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    monkeypatch.setattr(
        policy,
        "parse_args",
        lambda _argv: SimpleNamespace(event_path=tmp_path / "event.json"),
    )
    monkeypatch.setattr(policy, "load_pull_request_target", lambda _path: target)
    monkeypatch.setattr(policy, "_github_token", lambda: "opaque")
    monkeypatch.setattr(policy, "verify_base_owned_execution", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(policy, "validate_live_identity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(policy, "fetch_exact_pr_head", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        policy,
        "compute_material_manifest",
        lambda *_args, **_kwargs: SimpleNamespace(entries=(SimpleNamespace(path=changed_path),)),
    )
    monkeypatch.setattr(
        policy,
        "validate_trust_root_unchanged",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ReviewEvidenceError(
                f"AUTHORITY_ROTATION_REQUIRED: executable controls changed: {changed_path}"
            )
        ),
    )
    monkeypatch.setattr(
        policy,
        "validate_protected_material",
        lambda *_args, **_kwargs: pytest.fail("seal validation ran after authority failure"),
    )
    monkeypatch.setattr(
        policy,
        "poll_required_checks",
        lambda *_args, **_kwargs: pytest.fail("check polling ran after authority failure"),
    )

    assert policy.main([]) == 1
    assert "AUTHORITY_ROTATION_REQUIRED" in capsys.readouterr().err


def test_poll_budget_is_45_minutes_and_final_drift_is_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert policy._DEFAULT_POLL_SECONDS == 45 * 60
    assert policy._POLL_INTERVAL_SECONDS == 15
    assert policy._POLL_MAX_INTERVAL_SECONDS == 60
    target = policy.PullRequestTarget("owner/repo", 42, "a" * 40, "b" * 40)
    identity_calls: list[int] = []

    def identity(*_args: Any, **_kwargs: Any) -> None:
        identity_calls.append(1)
        if len(identity_calls) == 2:
            raise ReviewEvidenceError("event/base/main/checkout/head identity drifted")

    monkeypatch.setattr(policy, "validate_live_identity", identity)
    monkeypatch.setattr(
        policy,
        "validate_required_checks",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(ReviewEvidenceError, match="identity drifted"):
        policy.poll_required_checks(
            tmp_path,
            target,
            token="opaque",
            material_paths=("README.md",),
        )

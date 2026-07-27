#!/usr/bin/env python3
"""Base-owned, read-only policy gate for protected pull-request changes.

The ``pull_request_target`` workflow checks out the event's exact base SHA.
This validator fetches the PR head only into a detached Git ref and treats its
tree as untrusted data: PR Python, actions, and workflows are never imported or
executed.
"""

from __future__ import annotations

import argparse
import email.utils
import http.client
import json
import os
import re
import shutil
import subprocess  # nosec B404: absolute git runs fixed read-only argv (remove-by: 2026-10-31, ref: PR-provider-advisory)
import sys
import time
import tomllib
import urllib.error
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.pr_review_evidence import (  # noqa: E402
    ReviewEvidenceError,
    compute_material_manifest,
    is_provider_no_claim_review_receipt,
    is_provider_no_claim_security_receipt,
    parse_embedded_review_seal,
    protected_trust_boundary_paths,
    validate_mapping_only_closeout_successor,
    validate_review_seal,
)
from scripts.ci.check_pr_merge_readiness import (  # noqa: E402
    _OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES,
)
from scripts.ci.ci_risk_profile import build_risk_profile  # noqa: E402


@dataclass(frozen=True)
class AuthorityProjection:
    """One dual-use file projection whose executable fields are authority."""

    path: str
    format: str
    selectors: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class AdditiveVNextAdmissionContract:
    """Exact one-time bundle that may add, but never activate, a vNext gate."""

    workflow_path: str
    validator_path: str
    validator_source_path: str
    workflow_bytes: bytes

    @property
    def paths(self) -> frozenset[str]:
        return frozenset((self.workflow_path, self.validator_path))


_ADDITIVE_VNEXT_ADMISSION = AdditiveVNextAdmissionContract(
    workflow_path=".github/workflows/trusted_protected_pr_policy_vnext.yml",
    validator_path="scripts/ci/check_trusted_protected_pr_policy_vnext.py",
    validator_source_path="scripts/ci/check_trusted_protected_pr_policy.py",
    workflow_bytes=b"""name: Trusted Protected PR Policy vNext

on:
  pull_request_target:
    branches: [main]
    types: [opened, reopened, synchronize, ready_for_review, edited, labeled, unlabeled]

permissions:
  actions: read
  checks: read
  contents: read
  pull-requests: read
  statuses: read

concurrency:
  group: trusted-protected-pr-policy-vnext-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  trusted-protected-pr-policy-vnext:
    name: trusted-protected-pr-policy-vnext
    runs-on: ubuntu-latest
    timeout-minutes: 50
    steps:
      - name: Checkout trusted base revision
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          fetch-depth: 0
          persist-credentials: false

      - name: Validate protected PR policy from base-owned vNext code
        env:
          GH_TOKEN: ${{ github.token }}
          GITHUB_TOKEN: ${{ github.token }}
        run: >-
          python3 scripts/ci/check_trusted_protected_pr_policy_vnext.py
          --event-path "$GITHUB_EVENT_PATH"
""",
)


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ACTIONS_APP_ID = 15_368
_ACTIONS_APP_SLUG = "github-actions"
_MAX_API_PAGES = 100
_MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024
_API_RETRY_BACKOFF_SECONDS = (1.0, 2.0)
_API_REQUEST_ATTEMPTS = len(_API_RETRY_BACKOFF_SECONDS) + 1
_API_MAX_RETRY_AFTER_SECONDS = 60.0
_DEFAULT_POLL_SECONDS = 2700
_POLL_INTERVAL_SECONDS = 15
_POLL_MAX_INTERVAL_SECONDS = 60
_BASE_REQUIRED_CONTEXTS = (
    "Determine changed paths (for conditional jobs)",
    "pr_scope_guard",
    "Trivy ignore-policy expiry",
    "Ruby jwt/Fastlane unblock guard",
    "Pygments exception seam guard",
    "Docs Phase1 gates",
    "PR Body Phase2 gates",
    "Private Python proxy health",
    "lint",
)
_WORKFLOW_PATHS: Mapping[str, str] = {
    "CI": ".github/workflows/ci.yml",
    "CodeQL Advanced": ".github/workflows/codeql.yml",
    "Docker Build and Push": ".github/workflows/build.yml",
}
_TRUSTED_POLICY_ROOT_INPUTS = (
    ".github/CODEOWNERS",
    ".github/actions/**",
    ".github/workflows/**",
    ".github/workflows/trusted_protected_pr_policy.yml",
    "binding.gyp",
    "scripts/ci/check_current_head_pr_checks.py",
    "scripts/ci/check_pr_merge_readiness.py",
    "scripts/ci/check_trusted_protected_pr_policy.py",
    "scripts/ci/check_trusted_protected_pr_policy_vnext.py",
    "scripts/ci/ci_risk_profile.py",
    "scripts/orchestration/pr_commit_identity.py",
    "scripts/orchestration/pr_review_evidence.py",
    "scripts/orchestration/review_mapping_artifact.py",
    "scripts/orchestration/review_source_status.py",
    "sitecustomize.py",
    "usercustomize.py",
)
_CONTEXT_AUTHORITY_INPUTS: Mapping[str, tuple[str, ...]] = {
    "Determine changed paths (for conditional jobs)": (
        ".github/workflows/ci.yml",
        "scripts/ci/ci_risk_profile.py",
    ),
    "pr_scope_guard": (
        ".github/workflows/ci.yml",
        "scripts/ci/pr_scope_guard.sh",
        "scripts/ci/check_pr_size_governance.py",
        "scripts/design_guard.py",
        "docs/design/figma-manifest.json",
    ),
    "Trivy ignore-policy expiry": (
        ".github/workflows/ci.yml",
        "scripts/ci/check_trivy_ignore_policy_expiry.py",
        "scripts/ci/check_react_router_rsc_premise.py",
    ),
    "Ruby jwt/Fastlane unblock guard": (
        ".github/workflows/ci.yml",
        "scripts/ci/check_jwt_fastlane_unblock.py",
    ),
    "Pygments exception seam guard": (
        ".github/workflows/ci.yml",
        "scripts/ci/check_pygments_exception_guard.py",
    ),
    "Docs Phase1 gates": (
        ".github/workflows/ci.yml",
        ".nvmrc",
        "core/__init__.py",
        "core/ai/__init__.py",
        "scripts/ci/check_docs_phase1_gates.py",
        "scripts/ci/check_philosophy_admission_dry_run.py",
        "scripts/ci/check_philosophy_alignment_rules.py",
        "scripts/ci/check_philosophy_gate_open_preconditions.py",
        "scripts/ci/check_philosophy_source_corpus_index.py",
        "scripts/ci/check_semantic_cache_gate.py",
        "scripts/ci/check_semantic_cache_offline_admission_runner.py",
        "scripts/ci/check_semantic_cache_shadow_admission_harness.py",
        "scripts/ci/check_verification_provenance_admission_report.py",
        "core/ai/bounded_insight_semantic_cache.py",
        "core/ai/cache_observability.py",
        "core/ai/exact_fuzzy_cache.py",
        "core/ai/semantic_cache_backend_selection.py",
        "core/ai/semantic_cache_offline_admission_runner.py",
        "core/ai/semantic_cache_shadow_admission_harness.py",
    ),
    "PR Body Phase2 gates": (
        ".github/workflows/ci.yml",
        "scripts/ci/check_pr_body_phase2_gates.py",
        "scripts/orchestration/check_experiment_runner_identity.py",
        "scripts/orchestration/context_pack.py",
        "scripts/orchestration/experiment_contract.py",
        "scripts/orchestration/pr_commit_identity.py",
        "scripts/orchestration/pr_review_evidence.py",
        "scripts/orchestration/review_mapping_artifact.py",
        "scripts/orchestration/review_source_status.py",
    ),
    "Private Python proxy health": (
        ".github/workflows/ci.yml",
        "scripts/ci/check_emergency_wheel_mirror_parity.py",
        "scripts/ci/check_private_python_proxy_health.py",
    ),
    "lint": (
        ".github/workflows/ci.yml",
        ".github/actions/python-setup/**",
        ".bandit.yaml",
        ".coveragerc",
        "coverage.py",
        ".flake8",
        ".markdownlint.json",
        ".nvmrc",
        ".pre-commit-config.yaml",
        ".ruff.toml",
        ".secrets.baseline",
        ".yamllint",
        "Makefile",
        "conftest.py",
        "frontend/.npmrc",
        "pytest_sharding.py",
        "pytest.py",
        "pytest.ini",
        "pyrightconfig.json",
        "ruff.toml",
        "setup.cfg",
        "tox.ini",
        "constraints.txt",
        "requirements-ci-lite.txt",
        "scripts/ci/check_python_startup_hooks.py",
        "scripts/ci/emergency_python_wheels.json",
        "scripts/ci/install_locked_python_requirements.py",
        "scripts/ci/run_main_test_shards.py",
        "scripts/hooks/repo_python.sh",
        "scripts/run-backend-tests-pre-commit.sh",
        "tests/__init__.py",
        "tests/**/__init__.py",
        "tests/conftest.py",
        "tests/**/conftest.py",
        "tests/fixtures/dependency_security_schema.json",
        "tests/guards/**",
        "tests/test_dependency_security_guard.py",
        "tests/test_repo_policy_guards.py",
    ),
    "security": (
        ".github/workflows/ci.yml",
        ".github/actions/python-setup/**",
        ".bandit",
        "app/__init__.py",
        "app/contracts/__init__.py",
        "app/contracts/vip_contract.py",
        "app/security/__init__.py",
        "app/security/production_invariants.py",
        "app/security/rate_limit.py",
        "app/security/server_salt.py",
        "app/utils/__init__.py",
        "app/utils/feature_flags.py",
        "bmi_visualization.py",
        "constraints.txt",
        "core/__init__.py",
        "core/bmi/__init__.py",
        "core/bmi/engine.py",
        "core/bmi/query.py",
        "core/bmi/risk.py",
        "core/fingerprint_security.py",
        "core/i18n.py",
        "core/server_salt.py",
        "requirements-ci-lite.txt",
        "scripts/ci/check_python_startup_hooks.py",
        "scripts/ci/check_production_runtime_invariants.py",
        "scripts/ci/ci_risk_profile.py",
        "scripts/ci/emergency_python_wheels.json",
        "scripts/ci/install_locked_python_requirements.py",
        "scripts/ci/summarize_bandit_report.py",
        "scripts/ci_bandit.sh",
        "scripts/ci_pip_audit.sh",
        "settings.py",
        "tests/fixtures/dependency_security_schema.json",
    ),
    "Analyze (actions)": (
        ".github/codeql/extensions/**",
        ".github/workflows/codeql.yml",
    ),
    "Analyze (javascript-typescript)": (
        ".github/codeql/extensions/**",
        ".github/workflows/codeql.yml",
    ),
    "Analyze (python)": (
        ".github/codeql/extensions/**",
        ".github/workflows/codeql.yml",
    ),
    "security-scan": (
        ".dockerignore",
        ".github/workflows/build.yml",
        ".trivyignore",
        "Dockerfile",
        "docs/telemetry/docker_image_baseline.production.json",
        "docs/telemetry/docker_image_budget.production.json",
        "scripts/ci/check_docker_image_budget.py",
        "scripts/ci/check_docker_runtime_dependency_surface.py",
        "scripts/ci/check_python_startup_hooks.py",
        "scripts/ci/docker_image_telemetry.py",
        "scripts/ci/fetch_docker_source_artifacts.py",
        "scripts/ci/install_locked_python_requirements.py",
        "trivy/ignore-policy.rego",
    ),
}
_CONTEXT_AUTHORITY_PROJECTIONS: Mapping[str, tuple[AuthorityProjection, ...]] = {
    "lint": (
        AuthorityProjection(
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
        AuthorityProjection(
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
        AuthorityProjection(
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
    ),
}
_PGVECTOR_SELECTION_PATHS = frozenset(
    {
        ".github/workflows/ci.yml",
        "alembic/versions/202602280001_add_rag_feedback_tables.py",
        "alembic/versions/202602280002_enable_pgvector_extension.py",
        "alembic/versions/202602280003_convert_embedding_to_vector768.py",
        "alembic/versions/202603100101_enable_rag_user_rls.py",
        "alembic/versions/202603110001_harden_rag_subject_principal_bigint.py",
        "constraints.txt",
        "core/db_rls.py",
        "core/rag/vector_rag.py",
        "requirements-ci-lite.txt",
        "requirements-rag-vector-cpu.in",
        "requirements-rag-vector-cpu.txt",
        "requirements-rag-vector.in",
        "requirements-rag-vector.txt",
        "requirements-test.in",
        "requirements-test.txt",
        "scripts/ci/emergency_python_wheels.json",
        "scripts/ci/install_locked_python_requirements.py",
        "tests/test_db_rls.py",
        "tests/test_pgvector_compat.py",
        "tests/test_pgvector_embedding_migration.py",
        "tests/test_vector_rag.py",
    }
)
_PGVECTOR_AUTHORITY_INPUTS = (
    "conftest.py",
    "pytest_sharding.py",
    "scripts/ci/install_locked_python_requirements.py",
    "tests/conftest.py",
    "tests/test_db_rls.py",
    "tests/test_pgvector_compat.py",
    "tests/test_pgvector_embedding_migration.py",
    "tests/test_vector_rag.py",
)


@dataclass(frozen=True)
class PullRequestTarget:
    repository: str
    number: int
    base_sha: str
    head_sha: str
    base_ref: str = "main"


@dataclass(frozen=True)
class RequiredContext:
    name: str
    workflow_name: str
    workflow_path: str
    authority_inputs: tuple[str, ...]
    authority_projections: tuple[AuthorityProjection, ...] = ()


class _ChecksPending(ReviewEvidenceError):
    """Trusted upstream checks have not reached a terminal state."""


def _git(repo_root: Path, args: Sequence[str]) -> bytes:
    git = shutil.which("git")
    if git is None:
        raise ReviewEvidenceError("git is unavailable")
    run_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    run_env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    completed = subprocess.run(  # nosec B603: absolute git and fixed argv (remove-by: 2026-10-31, ref: PR-provider-advisory)
        [git, *args],
        cwd=repo_root,
        env=run_env,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewEvidenceError(f"git {' '.join(args[:2])} failed: {stderr}")
    return completed.stdout


def _require_sha(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ReviewEvidenceError(f"{label} must be a full lowercase SHA")
    return value


def load_pull_request_target(event_path: Path) -> PullRequestTarget:
    """Read only immutable identity fields from the GitHub event payload."""

    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewEvidenceError("pull_request_target event is unreadable") from exc
    if not isinstance(payload, dict):
        raise ReviewEvidenceError("pull_request_target event must be an object")
    pull_request = payload.get("pull_request")
    repository = payload.get("repository")
    if not isinstance(pull_request, dict) or not isinstance(repository, dict):
        raise ReviewEvidenceError("event is not a pull_request_target payload")
    full_name = repository.get("full_name")
    number = pull_request.get("number")
    base = pull_request.get("base")
    head = pull_request.get("head")
    if (
        not isinstance(full_name, str)
        or _REPOSITORY_RE.fullmatch(full_name) is None
        or not isinstance(number, int)
        or isinstance(number, bool)
        or number <= 0
        or not isinstance(base, dict)
        or not isinstance(head, dict)
    ):
        raise ReviewEvidenceError("event repository/PR identity is malformed")
    return PullRequestTarget(
        repository=full_name,
        number=number,
        base_sha=_require_sha(base.get("sha"), label="pull_request.base.sha"),
        head_sha=_require_sha(head.get("sha"), label="pull_request.head.sha"),
        base_ref=str(base.get("ref") or ""),
    )


def verify_base_owned_execution(
    repo_root: Path,
    target: PullRequestTarget,
    *,
    validator_path: Path | None = None,
) -> None:
    """Prove the running checkout and validator bytes come from the base SHA."""

    checkout_head = _git(repo_root, ("rev-parse", "HEAD")).decode("ascii").strip()
    if checkout_head != target.base_sha:
        raise ReviewEvidenceError("trusted policy checkout is not the event base SHA")
    script_path = (validator_path or Path(__file__)).resolve()
    relative_script = script_path.relative_to(repo_root.resolve()).as_posix()
    trusted_bytes = _git(repo_root, ("show", f"{target.base_sha}:{relative_script}"))
    if trusted_bytes != script_path.read_bytes():
        raise ReviewEvidenceError("trusted policy validator differs from the base-owned blob")


def fetch_exact_pr_head(repo_root: Path, target: PullRequestTarget) -> None:
    """Fetch the PR head as Git data without checking it out or executing it."""

    destination = f"refs/codex/trusted-protected-pr-policy/{target.number}"
    _git(
        repo_root,
        (
            "fetch",
            "--force",
            "--no-tags",
            "origin",
            f"refs/pull/{target.number}/head:{destination}",
        ),
    )
    fetched = _git(repo_root, ("rev-parse", destination)).decode("ascii").strip()
    if fetched != target.head_sha:
        raise ReviewEvidenceError("fetched PR head differs from the event current head")


def _github_token() -> str:
    """Require the same ephemeral workflow token through both standard names."""

    gh_token = os.environ.get("GH_TOKEN", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not gh_token or gh_token != github_token:
        raise ReviewEvidenceError("GH_TOKEN and GITHUB_TOKEN must be the same non-empty token")
    return gh_token


def _bounded_retry_after_seconds(value: object) -> float | None:
    """Parse a bounded Retry-After delta or HTTP date from an untrusted header."""

    if not isinstance(value, str):
        return None
    header = value.strip()
    if re.fullmatch(r"[0-9]+", header):
        try:
            delay = float(int(header))
        except (OverflowError, ValueError):
            return None
    else:
        try:
            retry_at = email.utils.parsedate_to_datetime(header)
            if retry_at.tzinfo is None:
                return None
            delay = max(0.0, retry_at.timestamp() - time.time())
        except (OSError, OverflowError, TypeError, ValueError):
            return None
    if not 0.0 <= delay <= _API_MAX_RETRY_AFTER_SECONDS:
        return None
    return delay


def _api_request(url: str, *, token: str) -> Any:
    """Read one bounded GitHub API JSON response with bounded transient retries."""

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        raise ReviewEvidenceError("unsupported GitHub API URL")
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    for attempt in range(_API_REQUEST_ATTEMPTS):
        connection: http.client.HTTPSConnection | None = None
        transport_failed = False
        try:
            connection = http.client.HTTPSConnection("api.github.com", timeout=30)
            connection.request(
                "GET",
                path,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "pulseplate-trusted-protected-pr-policy",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response = connection.getresponse()
            raw = response.read(_MAX_API_RESPONSE_BYTES + 1)
            retry_after = response.getheader("Retry-After")
        except (OSError, http.client.HTTPException):
            transport_failed = True
        finally:
            if connection is not None:
                try:
                    connection.close()
                except (OSError, http.client.HTTPException):
                    transport_failed = True

        if transport_failed:
            if attempt + 1 >= _API_REQUEST_ATTEMPTS:
                break
            time.sleep(_API_RETRY_BACKOFF_SECONDS[attempt])
            continue

        if response.status >= 400:
            bounded_retry_after = _bounded_retry_after_seconds(retry_after)
            retryable = (
                response.status == 429
                or response.status >= 500
                or (response.status == 403 and bounded_retry_after is not None)
            )
            if retryable and attempt + 1 < _API_REQUEST_ATTEMPTS:
                delay = (
                    bounded_retry_after
                    if response.status in {403, 429} and bounded_retry_after is not None
                    else _API_RETRY_BACKOFF_SECONDS[attempt]
                )
                time.sleep(delay)
                continue
            raise ReviewEvidenceError(f"GitHub API request failed with HTTP {response.status}")
        if len(raw) > _MAX_API_RESPONSE_BYTES:
            raise ReviewEvidenceError("GitHub API response exceeds size limit")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReviewEvidenceError("GitHub API returned malformed JSON") from exc
    raise ReviewEvidenceError(f"GitHub API transport failed after {_API_REQUEST_ATTEMPTS} attempts")


def _repo_api(target: PullRequestTarget, suffix: str) -> str:
    owner, repository = target.repository.split("/", maxsplit=1)
    return (
        "https://api.github.com/repos/"
        f"{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(repository, safe='')}{suffix}"
    )


def validate_live_identity(
    repo_root: Path,
    target: PullRequestTarget,
    *,
    token: str,
) -> None:
    """Fail when base, main, checkout, or live PR head drift from the event."""

    checkout_head = _git(repo_root, ("rev-parse", "HEAD")).decode("ascii").strip()
    pull = _api_request(
        _repo_api(target, f"/pulls/{target.number}"),
        token=token,
    )
    main_ref = _api_request(
        _repo_api(target, "/git/ref/heads/main"),
        token=token,
    )
    if not isinstance(pull, dict) or not isinstance(main_ref, dict):
        raise ReviewEvidenceError("live PR/main identity response is malformed")
    live_base = pull.get("base")
    live_head = pull.get("head")
    main_object = main_ref.get("object")
    if (
        target.base_ref != "main"
        or not isinstance(live_base, dict)
        or live_base.get("ref") != "main"
        or not isinstance(live_head, dict)
        or not isinstance(main_object, dict)
        or live_base.get("sha") != target.base_sha
        or live_head.get("sha") != target.head_sha
        or main_object.get("sha") != target.base_sha
        or checkout_head != target.base_sha
    ):
        raise ReviewEvidenceError(
            "event/base/main/checkout/head identity drifted; rerun from the new base"
        )


def _required_contexts(material_paths: Sequence[str]) -> tuple[RequiredContext, ...]:
    """Build the base-owned required set, including applicable security jobs."""

    def authority_inputs(name: str) -> tuple[str, ...]:
        inputs = _CONTEXT_AUTHORITY_INPUTS[name]
        if name == "security" and any(path in _PGVECTOR_SELECTION_PATHS for path in material_paths):
            return tuple(sorted(set(inputs) | set(_PGVECTOR_AUTHORITY_INPUTS)))
        return inputs

    contexts = {
        name: RequiredContext(
            name,
            "CI",
            _WORKFLOW_PATHS["CI"],
            authority_inputs(name),
            _CONTEXT_AUTHORITY_PROJECTIONS.get(name, ()),
        )
        for name in _BASE_REQUIRED_CONTEXTS
    }
    protected_inventory = _protected_or_authority_paths(material_paths)
    run_security = build_risk_profile(tuple(material_paths)).run_security or bool(
        protected_inventory
    )
    for name, (
        workflow_name,
        app_id,
        app_slug,
    ) in _OUTAGE_OVERRIDE_REQUIRED_CHECK_IDENTITIES.items():
        if app_id != _ACTIONS_APP_ID or app_slug != _ACTIONS_APP_SLUG:
            raise ReviewEvidenceError("canonical security check identity is unsupported")
        if name == "security" and not run_security:
            continue
        workflow_path = _WORKFLOW_PATHS.get(workflow_name)
        if workflow_path is None:
            raise ReviewEvidenceError(
                f"canonical security workflow is not base-allowlisted: {workflow_name}"
            )
        contexts[name] = RequiredContext(
            name,
            workflow_name,
            workflow_path,
            authority_inputs(name),
            _CONTEXT_AUTHORITY_PROJECTIONS.get(name, ()),
        )
    return tuple(contexts[name] for name in sorted(contexts))


def _tree_blob_identities(repo_root: Path, revision: str) -> dict[str, str]:
    """Return path to mode/type/OID identity for one exact Git tree."""

    raw = _git(
        repo_root,
        ("ls-tree", "-r", "-z", "--full-tree", revision, "--"),
    )
    identities: dict[str, str] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path_raw = record.split(b"\t", maxsplit=1)
            mode, object_type, oid = metadata.decode("ascii").split()
            path = path_raw.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise ReviewEvidenceError("git tree contains malformed authority input") from exc
        if path in identities:
            raise ReviewEvidenceError("git tree contains duplicate authority input path")
        identities[path] = f"{mode}:{object_type}:{oid}"
    return identities


def _matches_authority_input(path: str, patterns: set[str]) -> bool:
    for pattern in patterns:
        if "/**/" in pattern:
            prefix, suffix = pattern.split("/**/", maxsplit=1)
            if path.startswith(f"{prefix}/") and path.endswith(f"/{suffix}"):
                return True
        elif pattern.endswith("/**"):
            if path.startswith(pattern[:-2]):
                return True
        elif path == pattern:
            return True
    return False


def _all_blob_authority_inputs(material_paths: Sequence[str]) -> set[str]:
    """Return the complete base-owned blob-control graph, independent of routing."""

    patterns = set(_TRUSTED_POLICY_ROOT_INPUTS)
    for inputs in _CONTEXT_AUTHORITY_INPUTS.values():
        patterns.update(inputs)
    if any(path in _PGVECTOR_SELECTION_PATHS for path in material_paths):
        patterns.update(_PGVECTOR_AUTHORITY_INPUTS)
    return patterns


def _all_authority_projections() -> tuple[AuthorityProjection, ...]:
    """Return unique dual-use projections attached to required contexts."""

    return tuple(
        sorted(
            {
                projection
                for projections in _CONTEXT_AUTHORITY_PROJECTIONS.values()
                for projection in projections
            },
            key=lambda projection: (
                projection.path,
                projection.format,
                projection.selectors,
            ),
        )
    )


def _protected_or_authority_paths(material_paths: Sequence[str]) -> tuple[str, ...]:
    """Select legacy protected subjects plus every current authority candidate."""

    patterns = _all_blob_authority_inputs(material_paths)
    projected_paths = {projection.path for projection in _all_authority_projections()}
    return tuple(
        sorted(
            set(protected_trust_boundary_paths(material_paths))
            | {
                path
                for path in material_paths
                if path in projected_paths or _matches_authority_input(path, patterns)
            }
        )
    )


def _mapping_at_revision(
    repo_root: Path,
    revision: str,
    projection: AuthorityProjection,
) -> dict[str, Any]:
    """Read one bounded JSON/TOML mapping from an exact Git tree."""

    raw = _git(repo_root, ("show", f"{revision}:{projection.path}"))
    if len(raw) > 1024 * 1024:
        raise ReviewEvidenceError("input exceeds 1 MiB")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReviewEvidenceError("input is not UTF-8") from exc
    try:
        if projection.format == "json":
            payload = json.loads(text)
        elif projection.format == "toml":
            payload = tomllib.loads(text)
        else:
            raise ReviewEvidenceError(
                f"unsupported semantic projection format {projection.format!r}"
            )
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ReviewEvidenceError(f"{projection.format} parse failed") from exc
    if not isinstance(payload, dict):
        raise ReviewEvidenceError("top-level value is not an object")
    return payload


def _selected_value(payload: Mapping[str, Any], selector: tuple[str, ...]) -> tuple[bool, Any]:
    current: Any = payload
    for key in selector:
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def _semantic_authority_changes(
    repo_root: Path,
    target: PullRequestTarget,
    *,
    base_tree: Mapping[str, str],
    head_tree: Mapping[str, str],
) -> dict[str, str]:
    """Return dual-use files whose executable policy fields changed."""

    changed: dict[str, str] = {}
    for projection in _all_authority_projections():
        path = projection.path
        if base_tree.get(path) == head_tree.get(path):
            continue
        if path not in base_tree or path not in head_tree:
            changed[path] = "projected authority input was added or removed"
            continue
        base_mode = base_tree[path].split(":", maxsplit=1)[0]
        head_mode = head_tree[path].split(":", maxsplit=1)[0]
        if base_mode != head_mode:
            changed[path] = "projected authority input mode changed"
            continue
        try:
            base_payload = _mapping_at_revision(repo_root, target.base_sha, projection)
            head_payload = _mapping_at_revision(repo_root, target.head_sha, projection)
        except ReviewEvidenceError as exc:
            changed[path] = str(exc)
            continue
        if any(
            _selected_value(base_payload, selector) != _selected_value(head_payload, selector)
            for selector in projection.selectors
        ):
            changed[path] = "projected authority fields changed"
    return changed


def _admitted_additive_vnext_paths(
    repo_root: Path,
    target: PullRequestTarget,
    *,
    base_tree: Mapping[str, str],
    head_tree: Mapping[str, str],
    changed_authority_paths: set[str],
) -> frozenset[str]:
    """Admit only the exact first addition of the dormant vNext bundle."""

    contract = _ADDITIVE_VNEXT_ADMISSION
    touched = contract.paths & changed_authority_paths
    if not touched:
        return frozenset()
    if touched != contract.paths:
        raise ReviewEvidenceError("AUTHORITY_ROTATION_REQUIRED: additive vNext bundle is partial")
    if any(path in base_tree for path in contract.paths):
        raise ReviewEvidenceError(
            "AUTHORITY_ROTATION_REQUIRED: additive vNext admission is not reusable"
        )
    workflow_identity = head_tree.get(contract.workflow_path)
    validator_identity = head_tree.get(contract.validator_path)
    source_identity = base_tree.get(contract.validator_source_path)
    if workflow_identity is None or not workflow_identity.startswith("100644:blob:"):
        raise ReviewEvidenceError(
            "AUTHORITY_ROTATION_REQUIRED: additive vNext workflow identity is unsafe"
        )
    if (
        source_identity is None
        or not source_identity.startswith("100644:blob:")
        or validator_identity != source_identity
    ):
        raise ReviewEvidenceError(
            "AUTHORITY_ROTATION_REQUIRED: additive vNext validator is not the exact "
            "base-owned checker"
        )
    workflow_bytes = _git(
        repo_root,
        ("show", f"{target.head_sha}:{contract.workflow_path}"),
    )
    if workflow_bytes != contract.workflow_bytes:
        raise ReviewEvidenceError(
            "AUTHORITY_ROTATION_REQUIRED: additive vNext workflow bytes are not exact"
        )
    return contract.paths


def validate_trust_root_unchanged(
    repo_root: Path,
    target: PullRequestTarget,
    *,
    material_paths: Sequence[str],
) -> None:
    """Reject any changed authority input before trusting upstream checks."""

    patterns = _all_blob_authority_inputs(material_paths)
    base_tree = _tree_blob_identities(repo_root, target.base_sha)
    head_tree = _tree_blob_identities(repo_root, target.head_sha)
    trust_paths = {
        path for path in set(base_tree) | set(head_tree) if _matches_authority_input(path, patterns)
    }
    changed_set = {path for path in trust_paths if base_tree.get(path) != head_tree.get(path)}
    admitted_vnext_paths = _admitted_additive_vnext_paths(
        repo_root,
        target,
        base_tree=base_tree,
        head_tree=head_tree,
        changed_authority_paths=changed_set,
    )
    changed = sorted(changed_set - admitted_vnext_paths)
    semantic_changes = _semantic_authority_changes(
        repo_root,
        target,
        base_tree=base_tree,
        head_tree=head_tree,
    )
    details = changed + [f"{path}: {reason}" for path, reason in sorted(semantic_changes.items())]
    if details:
        raise ReviewEvidenceError("AUTHORITY_ROTATION_REQUIRED: " + ", ".join(details))


def _paged_api_list(
    target: PullRequestTarget,
    *,
    token: str,
    suffix: str,
    field: str | None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for page in range(1, _MAX_API_PAGES + 1):
        separator = "&" if "?" in suffix else "?"
        payload = _api_request(
            _repo_api(target, f"{suffix}{separator}per_page=100&page={page}"),
            token=token,
        )
        raw_items = payload.get(field) if field and isinstance(payload, dict) else payload
        if not isinstance(raw_items, list) or any(not isinstance(item, dict) for item in raw_items):
            raise ReviewEvidenceError("GitHub check/status list is malformed")
        items.extend(raw_items)
        if len(raw_items) < 100:
            return items
    raise ReviewEvidenceError("GitHub check/status pagination exceeded limit")


def _actions_run_and_job_ids(
    details_url: object,
    target: PullRequestTarget,
) -> tuple[int, int]:
    if not isinstance(details_url, str):
        raise ReviewEvidenceError("check run details URL is missing")
    parsed = urllib.parse.urlparse(details_url)
    expected_prefix = f"/{target.repository}/actions/runs/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or not parsed.path.startswith(expected_prefix)
    ):
        raise ReviewEvidenceError("check run is not linked to this repository Actions run")
    tail = parsed.path[len(expected_prefix) :].split("/")
    if (
        len(tail) != 3
        or not tail[0].isdigit()
        or int(tail[0]) <= 0
        or tail[1] != "job"
        or not tail[2].isdigit()
        or int(tail[2]) <= 0
    ):
        raise ReviewEvidenceError("check run Actions run/job identity is malformed")
    return int(tail[0]), int(tail[2])


def _validated_action_run(
    check: Mapping[str, Any],
    *,
    required: RequiredContext,
    target: PullRequestTarget,
    token: str,
    run_cache: dict[int, dict[str, Any]],
    job_cache: dict[int, dict[str, Any]],
) -> tuple[str, int] | None:
    run_id, job_id = _actions_run_and_job_ids(check.get("details_url"), target)
    if run_id not in run_cache:
        run = _api_request(
            _repo_api(target, f"/actions/runs/{run_id}"),
            token=token,
        )
        if not isinstance(run, dict):
            raise ReviewEvidenceError("linked Actions run is malformed")
        run_cache[run_id] = run
    run = run_cache[run_id]
    if run.get("id") != run_id:
        raise ReviewEvidenceError(f"{required.name} linked Actions run identity is malformed")
    event = run.get("event")
    if not isinstance(event, str) or not event:
        raise ReviewEvidenceError(f"{required.name} linked Actions run event is malformed")
    if event != "pull_request":
        return None
    pull_requests = run.get("pull_requests")
    if not isinstance(pull_requests, list):
        raise ReviewEvidenceError("linked Actions run PR binding is malformed")
    matching_prs = [
        item
        for item in pull_requests
        if isinstance(item, dict)
        and item.get("number") == target.number
        and isinstance(item.get("head"), dict)
        and item["head"].get("sha") == target.head_sha
        and isinstance(item.get("base"), dict)
        and item["base"].get("ref") == target.base_ref
        and item["base"].get("sha") == target.base_sha
    ]
    if (
        run.get("head_sha") != target.head_sha
        or run.get("name") != required.workflow_name
        or run.get("path") != required.workflow_path
        or len(matching_prs) != 1
    ):
        raise ReviewEvidenceError(
            f"{required.name} is not linked to an exact PR/base/head "
            "base-allowlisted Actions run"
        )
    created_at = run.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        raise ReviewEvidenceError(f"{required.name} linked Actions chronology is malformed")
    if job_id not in job_cache:
        job = _api_request(
            _repo_api(target, f"/actions/jobs/{job_id}"),
            token=token,
        )
        if not isinstance(job, dict):
            raise ReviewEvidenceError("linked Actions job is malformed")
        job_cache[job_id] = job
    job = job_cache[job_id]
    check_id = check.get("id")
    attempt = job.get("run_attempt")
    if (
        not isinstance(check_id, int)
        or isinstance(check_id, bool)
        or check_id <= 0
        or job.get("id") != job_id
        or job.get("run_id") != run_id
        or job.get("check_run_url") != _repo_api(target, f"/check-runs/{check_id}")
        or not isinstance(attempt, int)
        or isinstance(attempt, bool)
        or attempt <= 0
    ):
        raise ReviewEvidenceError(f"{required.name} linked Actions job identity is malformed")
    return created_at, attempt


def validate_required_checks(
    target: PullRequestTarget,
    *,
    token: str,
    material_paths: Sequence[str],
    actions_run_cache: dict[int, dict[str, Any]] | None = None,
    actions_job_cache: dict[int, dict[str, Any]] | None = None,
) -> None:
    """Require trusted, unambiguous current-head GitHub Actions successes."""

    required_contexts = _required_contexts(material_paths)
    checks = _paged_api_list(
        target,
        token=token,
        suffix=f"/commits/{target.head_sha}/check-runs",
        field="check_runs",
    )
    statuses = _paged_api_list(
        target,
        token=token,
        suffix=f"/commits/{target.head_sha}/statuses",
        field=None,
    )
    required_names = {required.name for required in required_contexts}
    spoofed_statuses = sorted(
        {
            str(status.get("context") or "")
            for status in statuses
            if status.get("context") in required_names
        }
    )
    if spoofed_statuses:
        raise ReviewEvidenceError(
            "required names are shadowed by untrusted status contexts: "
            + ", ".join(spoofed_statuses)
        )

    pending: list[str] = []
    run_cache = actions_run_cache if actions_run_cache is not None else {}
    job_cache = actions_job_cache if actions_job_cache is not None else {}
    for required in required_contexts:
        candidates = [check for check in checks if check.get("name") == required.name]
        if not candidates:
            pending.append(f"{required.name}=missing")
            continue
        ranked: list[tuple[tuple[str, int], Mapping[str, Any]]] = []
        for check in candidates:
            app = check.get("app")
            if (
                check.get("head_sha") != target.head_sha
                or not isinstance(app, dict)
                or app.get("id") != _ACTIONS_APP_ID
                or app.get("slug") != _ACTIONS_APP_SLUG
            ):
                raise ReviewEvidenceError(f"{required.name} has a foreign app or head identity")
            ranking = _validated_action_run(
                check,
                required=required,
                target=target,
                token=token,
                run_cache=run_cache,
                job_cache=job_cache,
            )
            if ranking is None:
                continue
            ranked.append((ranking, check))
        if not ranked:
            pending.append(f"{required.name}=missing")
            continue
        newest_rank = max(rank for rank, _check in ranked)
        newest = [check for rank, check in ranked if rank == newest_rank]
        if len(newest) != 1:
            raise ReviewEvidenceError(f"{required.name} has ambiguous latest check runs")
        selected = newest[0]
        status = selected.get("status")
        conclusion = selected.get("conclusion")
        if status in {"queued", "in_progress", "pending", "requested", "waiting"}:
            pending.append(f"{required.name}={status}")
        elif status != "completed" or conclusion != "success":
            raise ReviewEvidenceError(
                f"{required.name}={status or 'missing'}/{conclusion or 'missing'}"
            )
    if pending:
        raise _ChecksPending("trusted current-head checks pending: " + ", ".join(pending))


def poll_required_checks(
    repo_root: Path,
    target: PullRequestTarget,
    *,
    token: str,
    material_paths: Sequence[str],
    timeout_seconds: int = _DEFAULT_POLL_SECONDS,
) -> None:
    """Poll only GitHub check settlement and revalidate immutable identities."""

    if timeout_seconds < 0:
        raise ReviewEvidenceError("check settlement timeout must be non-negative")
    validate_live_identity(repo_root, target, token=token)
    deadline = time.monotonic() + timeout_seconds
    actions_run_cache: dict[int, dict[str, Any]] = {}
    actions_job_cache: dict[int, dict[str, Any]] = {}
    poll_interval = float(_POLL_INTERVAL_SECONDS)
    while True:
        try:
            validate_required_checks(
                target,
                token=token,
                material_paths=material_paths,
                actions_run_cache=actions_run_cache,
                actions_job_cache=actions_job_cache,
            )
            break
        except _ChecksPending as exc:
            remaining = deadline - time.monotonic()
            if timeout_seconds == 0 or remaining <= 0:
                raise ReviewEvidenceError(
                    f"trusted current-head checks did not settle within {timeout_seconds}s: {exc}"
                ) from exc
            time.sleep(min(poll_interval, remaining))
            poll_interval = min(poll_interval * 2.0, float(_POLL_MAX_INTERVAL_SECONDS))
    validate_live_identity(repo_root, target, token=token)


def validate_protected_material(repo_root: Path, target: PullRequestTarget) -> tuple[str, ...]:
    """Validate protected inventory and its exact provider-neutral no-claim seal."""

    manifest = compute_material_manifest(
        repo_root,
        base_ref_oid=target.base_sha,
        head_ref_oid=target.head_sha,
        pr_number=target.number,
    )
    protected: tuple[str, ...] = protected_trust_boundary_paths(
        entry.path for entry in manifest.entries
    )
    if not protected:
        return ()

    mapping_path = f"docs/review/PR_{target.number}_FIXED_MAPPING.md"
    try:
        mapping_text = _git(
            repo_root,
            ("show", f"{target.head_sha}:{mapping_path}"),
        ).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReviewEvidenceError("canonical mapping is not UTF-8") from exc
    seal = parse_embedded_review_seal(mapping_text)
    if seal["repository"] != target.repository or seal["pr_number"] != target.number:
        raise ReviewEvidenceError("canonical mapping seal belongs to another PR")
    material = seal["material"]
    material_head = material["material_head_sha"]
    sealed_manifest = compute_material_manifest(
        repo_root,
        base_ref_oid=target.base_sha,
        head_ref_oid=material_head,
        pr_number=target.number,
    )
    validate_review_seal(
        seal,
        material_paths=(entry.path for entry in sealed_manifest.entries),
        material_diff_summary=manifest.diff_summary,
    )
    if (
        material["base_ref_oid"] != target.base_sha
        or material["merge_base_sha"] != manifest.merge_base_sha
        or material["digest"] != manifest.digest
        or sealed_manifest.digest != manifest.digest
    ):
        raise ReviewEvidenceError("canonical mapping seal is stale for current material")
    if not (
        is_provider_no_claim_review_receipt(seal["code_review"])
        and is_provider_no_claim_security_receipt(seal["codex_security"])
    ):
        raise ReviewEvidenceError("protected changes require the exact symmetric no-claim pair")
    validate_mapping_only_closeout_successor(
        repo_root,
        material_head_sha=material_head,
        live_head_sha=target.head_sha,
        pr_number=target.number,
    )
    return protected


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-path", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        target = load_pull_request_target(args.event_path)
        token = _github_token()
        verify_base_owned_execution(REPO_ROOT, target)
        validate_live_identity(REPO_ROOT, target, token=token)
        fetch_exact_pr_head(REPO_ROOT, target)
        manifest = compute_material_manifest(
            REPO_ROOT,
            base_ref_oid=target.base_sha,
            head_ref_oid=target.head_sha,
            pr_number=target.number,
        )
        material_paths = tuple(entry.path for entry in manifest.entries)
        protected_inventory = _protected_or_authority_paths(material_paths)
        if protected_inventory:
            validate_trust_root_unchanged(
                REPO_ROOT,
                target,
                material_paths=material_paths,
            )
            protected = validate_protected_material(REPO_ROOT, target)
            poll_required_checks(
                REPO_ROOT,
                target,
                token=token,
                material_paths=material_paths,
            )
        else:
            protected = ()
            validate_live_identity(REPO_ROOT, target, token=token)
    except ReviewEvidenceError as exc:
        print(f"TRUSTED_PROTECTED_PR_POLICY_FAILED: {exc}", file=sys.stderr)
        return 1
    if protected:
        print("TRUSTED_PROTECTED_PR_POLICY_PASS protected=" + ",".join(protected))
    else:
        print("TRUSTED_PROTECTED_PR_POLICY_PASS protected=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

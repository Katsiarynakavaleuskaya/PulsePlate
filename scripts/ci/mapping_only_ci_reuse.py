#!/usr/bin/env python3
"""Bounded substitution of native CI test evidence for one mapping successor.

Only authenticated BASE code derives eligibility. JSON documents locate native
Actions evidence; they neither authorize a seal nor replace current merge gates.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import sys
import urllib.parse
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

REPO_ROOT = Path(__file__).resolve().parents[2]
# Standalone -I execution admits only the trusted script's resolved repository.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci import ci_risk_profile
from scripts.orchestration import pr_commit_identity as identity
from scripts.orchestration import pr_review_evidence as evidence

POLICY_VERSION = "pulseplate.mapping-only-ci-reuse/v1"
PLAN_SCHEMA = "pulseplate.ci-test-reuse-plan/v1"
MANIFEST_SCHEMA = "pulseplate.ci-test-execution/v1"
WORKFLOW_PATH = ".github/workflows/ci.yml"
PYTHON_VERSION_PATTERN = r"[1-9][0-9]{0,2}\.(?:0|[1-9][0-9]{0,2})(?:\.(?:0|[1-9][0-9]{0,3}))?"
HELPER_PATH = "scripts/ci/mapping_only_ci_reuse.py"
GITHUB_ACTIONS_APP_ID = 15368
MAX_ARCHIVE_BYTES = 32_000_000
MAX_MEMBER_BYTES = 24_000_000
MAX_MANIFEST_BYTES = 1_000_000
MAX_PAGES = 100
DIRECT_MARKER = "Confirm direct test execution"
REUSED_MARKER = "Confirm verified test reuse"
VERIFY_STEP = "Verify reusable test evidence"
WRITER_NAME = "CI test execution evidence"
WRITER_COLLECT = "Collect authenticated CI test evidence"
WRITER_UPLOAD = "Upload CI test execution evidence"
UPLOAD_PR = "Upload coverage artifact (single coverage runtime)"
UPLOAD_MAIN = "Upload coverage artifact (all Python versions)"
CRITICAL_STEPS: dict[str, tuple[str, ...]] = {
    "test-pr": (
        "Checkout",
        "Critical smoke (deterministic merge blocker)",
        "Finalize coverage artifacts",
        UPLOAD_PR,
    ),
    "test-main": ("Checkout", "Run tests with coverage", UPLOAD_MAIN),
    "ios-tests": (
        "Checkout",
        "Select Xcode (require 26.x for iOS 26 SDK readiness)",
        "Select iOS simulator destination (stable)",
        "iOS App Store repo-local verification",
        "iOS tests (project-based, app scheme)",
        "iOS Release simulator build (unsigned)",
    ),
    "ios-ui-smoke": (
        "Checkout",
        "Select Xcode (require 26.x for iOS 26 SDK readiness)",
        "Select iOS simulator destination (stable)",
        "iOS UI smoke (build-for-testing + test-without-building)",
    ),
}
BASE_CONDITIONS = {
    "test-pr": "github.event_name == 'pull_request' && needs.changes.outputs.run_backend_blocking == 'true'",
    "test-main": "github.ref == 'refs/heads/main' || (github.event_name == 'pull_request' && needs.changes.outputs.run_main_ci_diagnostic == 'true')",
    "ios-tests": "needs.changes.outputs.ios == 'true' && (github.event_name == 'pull_request' || (github.event_name == 'push' && (startsWith(github.ref, 'refs/heads/feat/') || startsWith(github.ref, 'refs/heads/fix/') || startsWith(github.ref, 'refs/heads/feature/') || github.ref == 'refs/heads/main')))",
}
BASE_CONDITIONS["ios-ui-smoke"] = BASE_CONDITIONS["ios-tests"]


class ReuseError(ValueError):
    """Incomplete or contradictory asserted reuse proof."""


class Ineligible(ReuseError):
    """Ordinary execution is required before any reuse assertion."""


@dataclass(frozen=True)
class Cell:
    job_id: str
    matrix_value: str | None
    check_name: str
    coverage_name: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "matrix_value": self.matrix_value,
            "check_name": self.check_name,
            "coverage_name": self.coverage_name,
        }


@dataclass(frozen=True)
class Context:
    repository: str
    pr_number: int
    repository_id: int
    base_sha: str
    head_sha: str
    head_ref: str
    snapshot: identity.PrSnapshot
    head_repository: str
    head_repository_id: int
    base_ref: str
    current_base_sha: str

    @property
    def is_fork(self) -> bool:
        return self.head_repository_id != self.repository_id


@dataclass(frozen=True)
class BasePolicy:
    config_digest: str
    cells: tuple[Cell, ...]
    all_names: frozenset[str]
    critical: Mapping[str, tuple[str, ...]]


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise ReuseError("evidence JSON cannot be serialized safely") from exc


def _digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ReuseError(f"{label} must be an object")
    return value


def _keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ReuseError(f"{label} has missing or unknown fields")


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ReuseError(f"{label} must be a positive integer")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ReuseError(f"{label} must be a lowercase full Git SHA")
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ReuseError(f"{label} must be a SHA256 digest")
    return value


def _time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise ReuseError(f"{label} must be an Actions UTC timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ReuseError(f"{label} timestamp is invalid") from exc


def _json(raw: bytes, *, limit: int = MAX_MANIFEST_BYTES) -> Any:
    if len(raw) > limit:
        raise ReuseError("JSON exceeds byte budget")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ReuseError("JSON has duplicate fields")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ReuseError("JSON has a non-finite constant")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ReuseError("malformed JSON") from exc


def _api(repository: str, path: str, token: str) -> Any:
    return identity.github_api_request(
        f"https://api.github.com/repos/{repository}/{path}", token=token
    )


def _pages(repository: str, path: str, key: str, token: str) -> list[dict[str, Any]]:
    """Complete count-bound pagination, with constructed immutable endpoints."""
    rows: list[dict[str, Any]] = []
    total: int | None = None
    join = "&" if "?" in path else "?"
    for page in range(1, MAX_PAGES + 1):
        payload = _object(
            _api(repository, f"{path}{join}per_page=100&page={page}", token), "API page"
        )
        count = payload.get("total_count")
        if type(count) is not int or not 0 <= count <= MAX_PAGES * 100:
            raise ReuseError("API pagination count is invalid")
        if total is None:
            total = count
        elif total != count:
            raise ReuseError("API pagination changed during proof")
        entries = payload.get(key)
        if not isinstance(entries, list) or len(entries) > 100:
            raise ReuseError("API pagination entries are invalid")
        rows.extend(_object(item, "API entry") for item in entries)
        if len(rows) > count or (not entries and len(rows) != count):
            raise ReuseError("API pagination is incomplete")
        if len(rows) == count:
            ids = [_positive(row.get("id"), "API entry ID") for row in rows]
            if len(ids) != len(set(ids)):
                raise ReuseError("API pagination contains duplicate identities")
            return rows
    raise ReuseError("API pagination exceeded its budget")


def _context(
    repository: str,
    pr_number: int,
    token: str,
    *,
    expected_head: str | None = None,
    expected_base: str | None = None,
) -> Context:
    if (
        not isinstance(repository, str)
        or re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is None
    ):
        raise ReuseError("repository identity is invalid")
    _positive(pr_number, "PR number")
    pr = _object(_api(repository, f"pulls/{pr_number}", token), "PR")
    if pr.get("number") != pr_number or pr.get("state") != "open":
        raise ReuseError("PR is not the requested open PR")
    base, head = _object(pr.get("base"), "PR base"), _object(pr.get("head"), "PR head")
    base_repo, head_repo = _object(base.get("repo"), "base repository"), _object(
        head.get("repo"), "head repository"
    )
    if base_repo.get("full_name") != repository:
        raise ReuseError("PR canonical BASE repository differs")
    repo_id = _positive(base_repo.get("id"), "repository ID")
    base_ref = base.get("ref")
    if (
        not isinstance(base_ref, str)
        or not base_ref
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in base_ref)
    ):
        raise ReuseError("PR base ref is invalid")
    encoded_ref = urllib.parse.quote(base_ref, safe="")
    branch = _object(_api(repository, f"branches/{encoded_ref}", token), "native base branch")
    links = _object(branch.get("_links"), "native branch links")
    branch_url = links.get("self")
    if not isinstance(branch_url, str):
        raise ReuseError("native branch identity is missing")
    parsed_branch = urllib.parse.urlsplit(branch_url)
    if (
        branch.get("name") != base_ref
        or parsed_branch.scheme != "https"
        or parsed_branch.netloc != "api.github.com"
        or parsed_branch.query
        or parsed_branch.fragment
        or urllib.parse.unquote(parsed_branch.path) != f"/repos/{repository}/branches/{base_ref}"
    ):
        raise ReuseError("native branch has foreign or mismatched identity")
    current_commit = _object(branch.get("commit"), "native base commit")
    current_base_sha = _sha(current_commit.get("sha"), "native current base SHA")
    if (
        current_commit.get("url")
        != f"https://api.github.com/repos/{repository}/commits/{current_base_sha}"
    ):
        raise ReuseError("native branch commit has foreign identity")
    head_repo_id = _positive(head_repo.get("id"), "head repository ID")
    head_repository = head_repo.get("full_name")
    if (
        not isinstance(head_repository, str)
        or re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", head_repository) is None
    ):
        raise ReuseError("head repository identity is invalid")
    if (head_repository == repository) != (head_repo_id == repo_id):
        raise ReuseError("repository names and IDs do not agree")
    if head_repo_id != repo_id and head_repo.get("fork") is not True:
        raise ReuseError("foreign head is not an authenticated fork")
    base_sha, head_sha = _sha(base.get("sha"), "base SHA"), _sha(head.get("sha"), "head SHA")
    head_ref = head.get("ref")
    if not isinstance(head_ref, str) or not head_ref or any(c in head_ref for c in "\r\n"):
        raise ReuseError("PR head ref is invalid")
    if (expected_head is not None and head_sha != _sha(expected_head, "expected head")) or (
        expected_base is not None and base_sha != _sha(expected_base, "expected base")
    ):
        raise ReuseError("PR head or base changed")
    snapshot = identity.fetch_pr_snapshot(
        repository, pr_number, token=token, request_json=identity.github_api_request
    )
    if (snapshot.base_sha, snapshot.head_sha) != (base_sha, head_sha):
        raise ReuseError("REST and complete PR graph do not agree")
    return Context(
        repository,
        pr_number,
        repo_id,
        base_sha,
        head_sha,
        head_ref,
        snapshot,
        head_repository,
        head_repo_id,
        base_ref,
        current_base_sha,
    )


def _blob(root: Path, ref: str, path: str) -> bytes:
    blob: bytes = evidence._run_git(root, ["show", f"{ref}:{path}"])
    return blob


def _ensure_git(root: Path, sha: str) -> None:
    try:
        evidence._run_git(root, ["cat-file", "-e", f"{sha}^{{commit}}"])
    except evidence.ReviewEvidenceError:
        evidence._run_git(root, ["fetch", "--no-tags", "origin", sha])
        evidence._run_git(root, ["cat-file", "-e", f"{sha}^{{commit}}"])


def _trusted_base(root: Path, context: Context) -> None:
    if root.resolve(strict=True) != REPO_ROOT:
        raise ReuseError("helper must execute from its own trusted BASE repository")
    checked_out = evidence._run_git(root, ["rev-parse", "HEAD"]).decode("ascii").strip()
    if checked_out != context.base_sha:
        raise ReuseError("reuse authority must execute in the exact BASE checkout")
    # The workflow creates a fresh checkout. Also detect local mutation of any
    # tracked BASE authority, rather than relying on the HEAD label alone.
    changed = evidence._run_git(root, ["diff", "--name-only", "HEAD", "--"])
    if changed:
        raise ReuseError("trusted BASE checkout contains tracked modifications")
    for sha in ((context.base_sha,) if context.is_fork else (context.base_sha, context.head_sha)):
        _ensure_git(root, sha)


class _ClosedYamlLoader(yaml.SafeLoader):
    """Safe YAML with duplicate keys and aliases rejected."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, (str, bool)) or key in result:
                raise Ineligible("unsupported_base_yaml_mapping")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _yaml(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_MANIFEST_BYTES:
        raise Ineligible("base_yaml_exceeds_budget")
    try:
        for event in yaml.parse(raw, Loader=yaml.SafeLoader):
            if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None) is not None:
                raise Ineligible("base_yaml_aliases_unsupported")
        loader = _ClosedYamlLoader(raw)
        try:
            result = loader.get_single_data()
        finally:
            loader.dispose()
    except (yaml.YAMLError, UnicodeError, RecursionError) as exc:
        raise Ineligible("malformed_base_yaml") from exc
    if not isinstance(result, dict):
        raise Ineligible("unsupported_base_yaml")
    return result


def _expression(value: Any) -> str:
    if not isinstance(value, str):
        raise Ineligible("unsupported_base_job_condition")
    return re.sub(r"\s+", "", value.removeprefix("${{").removesuffix("}}").strip())


def _condition(job_id: str, value: Any, needs: Any) -> None:
    original = BASE_CONDITIONS[job_id]
    if (
        not isinstance(needs, list)
        or any(not isinstance(n, str) for n in needs)
        or len(needs) != len(set(needs))
    ):
        raise Ineligible("unsupported_base_job_dependencies")
    original_needs = {
        "test-pr": {"changes", "pr_scope_guard", "private_python_proxy_health"},
        "test-main": {"changes", "private_python_proxy_health"},
        "ios-tests": {"changes"},
        "ios-ui-smoke": {"changes"},
    }[job_id]
    if set(needs) != original_needs | {"ci_test_reuse"}:
        raise Ineligible("unsupported_base_job_dependencies")
    suffix = " && ".join(
        f"needs.{name}.result == 'success'"
        for name in ("private_python_proxy_health", "pr_scope_guard")
        if name in original_needs
    )
    authored = (
        f"!cancelled() && ({original}) && needs.changes.result == 'success' "
        "&& (github.event_name != 'pull_request' || needs.ci_test_reuse.result == 'success')"
    )
    if suffix:
        authored += f" && {suffix}"
    if _expression(value) != _expression(authored):
        raise Ineligible("unsupported_base_job_condition")


def _safe_filter(pattern: Any) -> str:
    if (
        not isinstance(pattern, str)
        or not pattern
        or pattern.startswith(("!", "/"))
        or any(c in pattern for c in "[]{}?\\\r\n")
    ):
        raise Ineligible("unsupported_base_ios_filter")
    if "*" in pattern and (not pattern.endswith("/**") or "*" in pattern[:-3]):
        raise Ineligible("unsupported_base_ios_filter")
    if any(part in {"", ".", ".."} for part in pattern.split("/")):
        raise Ineligible("unsupported_base_ios_filter")
    return pattern


def _filter_matches(path: str, pattern: str) -> bool:
    return path.startswith(pattern[:-2]) if pattern.endswith("/**") else path == pattern


def _coverage_name(cell: Cell, run: dict[str, Any]) -> str | None:
    if cell.coverage_name is None:
        return None
    return f"{cell.coverage_name}-{run['run_id']}-{run['run_attempt']}"


def _job_shape(job_id: str, definition: dict[str, Any]) -> None:
    """Recognize only the six supported native jobs, without evaluating YAML."""
    keys = {"name", "if", "needs", "runs-on", "timeout-minutes", "permissions", "steps"}
    if job_id in {"test-pr", "test-main"}:
        keys.remove("name")
        keys.add("strategy")
    if job_id == "test-main":
        keys.add("env")
    if job_id == "ci_test_reuse":
        keys.add("outputs")
    if set(definition) != keys:
        raise Ineligible("unsupported_base_job_shape")
    expected_runner = "macos-15" if job_id in {"ios-tests", "ios-ui-smoke"} else "ubuntu-latest"
    if definition["runs-on"] != expected_runner:
        raise Ineligible("unsupported_base_runner")
    timeout = definition["timeout-minutes"]
    valid_timeout = type(timeout) is int and 0 < timeout <= 180
    if isinstance(timeout, str):
        expression = _expression(timeout)
        if job_id == "test-main":
            valid_timeout = expression == "matrix.timeout-minutes"
        elif job_id == "ios-tests":
            default = re.fullmatch(
                r"fromJSON\(vars\.IOS_TESTS_JOB_TIMEOUT_MINUTES\|\|'([1-9][0-9]{0,2})'\)",
                expression,
            )
            valid_timeout = default is not None and int(default.group(1)) <= 180
    if not valid_timeout:
        raise Ineligible("unsupported_base_job_timeout")
    permissions = {
        "contents": "read",
        "actions": "write" if job_id == "test-pr" else "read",
        "checks": "read",
        "pull-requests": "read",
    }
    if definition["permissions"] != permissions:
        raise Ineligible("unsupported_base_job_permissions")
    if job_id == "test-main" and definition["env"] != {
        "PULSEPLATE_PYTHON_INDEX_URL": "",
        "PULSEPLATE_PYTHON_TRUSTED_HOST": "",
    }:
        raise Ineligible("unsupported_base_job_environment")
    if job_id in {"test-pr", "test-main"}:
        strategy = _object(definition["strategy"], "BASE strategy")
        if set(strategy) != {"fail-fast", "matrix"} or strategy["fail-fast"] is not False:
            raise Ineligible("unsupported_base_strategy")
    if job_id in {"ci_test_reuse", "ci_test_evidence"}:
        names = (
            [step.get("name") for step in definition["steps"]]
            if isinstance(definition["steps"], list)
            and all(isinstance(step, dict) for step in definition["steps"])
            else []
        )
        expected = (
            [
                "Checkout trusted base",
                "Detect base reuse capability",
                "Setup trusted evidence environment",
                "Plan authenticated CI test reuse",
            ]
            if job_id == "ci_test_reuse"
            else [
                "Checkout trusted base",
                "Require successful reuse admission",
                "Require selected test results",
                "Detect base reuse capability",
                "Setup trusted evidence environment",
                WRITER_COLLECT,
                WRITER_UPLOAD,
            ]
        )
        if names != expected:
            raise Ineligible("unsupported_base_writer_startup")
        needed = (
            {"changes", "private_python_proxy_health"}
            if job_id == "ci_test_reuse"
            else {"changes", "ci_test_reuse", *CRITICAL_STEPS}
        )
        needs = definition["needs"]
        if (
            not isinstance(needs, list)
            or any(not isinstance(name, str) for name in needs)
            or len(needs) != len(set(needs))
            or set(needs) != needed
        ):
            raise Ineligible("unsupported_base_writer_dependencies")
        condition = (
            "github.event_name == 'pull_request'"
            if job_id == "ci_test_reuse"
            else "always() && github.event_name == 'pull_request'"
        )
        if _expression(definition["if"]) != _expression(condition):
            raise Ineligible("unsupported_base_writer_condition")


def _policy(root: Path, context: Context, material: evidence.MaterialManifest) -> BasePolicy:
    if context.is_fork:
        raise Ineligible("fork_pr_ordinary_only")
    try:
        helper = _blob(root, context.base_sha, HELPER_PATH)
    except evidence.ReviewEvidenceError as exc:
        raise Ineligible("base_capability_absent") from exc
    if not helper:
        raise Ineligible("base_capability_absent")
    workflow_raw = _blob(root, context.base_sha, WORKFLOW_PATH)
    workflow = _yaml(workflow_raw)
    if workflow.get("name") != "CI":
        raise Ineligible("unsupported_base_workflow")
    jobs = _object(workflow.get("jobs"), "BASE jobs")
    writer = jobs.get("ci_test_evidence")
    control = jobs.get("ci_test_reuse")
    if (
        not isinstance(writer, dict)
        or writer.get("name") != WRITER_NAME
        or not isinstance(control, dict)
        or control.get("name") != "CI test reuse admission"
    ):
        raise Ineligible("base_capability_absent")
    _job_shape("ci_test_evidence", writer)
    _job_shape("ci_test_reuse", control)
    for trusted in (writer, control):
        steps = trusted.get("steps")
        if not isinstance(steps, list) or not steps or not isinstance(steps[0], dict):
            raise Ineligible("unsupported_base_trusted_checkout")
        checkout = steps[0]
        options = _object(checkout.get("with"), "BASE trusted checkout options")
        if (
            set(checkout) != {"name", "uses", "with"}
            or set(options) != {"ref", "fetch-depth", "persist-credentials"}
            or checkout.get("name") != "Checkout trusted base"
            or not re.fullmatch(r"actions/checkout@[0-9a-f]{40}", str(checkout.get("uses", "")))
            or options.get("ref") != "${{ github.event.pull_request.base.sha }}"
            or options.get("fetch-depth") != 0
            or options.get("persist-credentials") is not False
        ):
            raise Ineligible("unsupported_base_trusted_checkout")
    paths = tuple(entry.path for entry in material.entries)
    risk = ci_risk_profile.build_risk_profile(paths)
    protected = evidence.protected_trust_boundary_paths(paths)
    if protected or risk.workflow_privileged:
        raise Ineligible("whole_pr_protected_material")
    changes_steps = _object(jobs.get("changes"), "BASE changes").get("steps")
    if not isinstance(changes_steps, list):
        raise Ineligible("unsupported_base_changes")
    filters = [
        step for step in changes_steps if isinstance(step, dict) and step.get("id") == "filter"
    ]
    if len(filters) != 1 or not re.fullmatch(
        r"dorny/paths-filter@[0-9a-f]{40}", str(filters[0].get("uses", ""))
    ):
        raise Ineligible("unsupported_base_ios_filter")
    filter_raw = _object(filters[0].get("with"), "BASE filter").get("filters")
    if not isinstance(filter_raw, str):
        raise Ineligible("unsupported_base_ios_filter")
    ios_patterns = _yaml(filter_raw.encode("utf-8")).get("ios")
    if not isinstance(ios_patterns, list) or not 0 < len(ios_patterns) <= 100:
        raise Ineligible("unsupported_base_ios_filter")
    normalized_patterns = tuple(_safe_filter(pattern) for pattern in ios_patterns)
    ios = any(_filter_matches(path, pattern) for path in paths for pattern in normalized_patterns)
    python = _object(workflow.get("env"), "BASE workflow environment").get("PYTHON_VERSION")
    if not isinstance(python, str) or re.fullmatch(PYTHON_VERSION_PATTERN, python) is None:
        raise Ineligible("unsupported_base_python_runtime")
    selected: list[Cell] = []
    all_names: set[str] = set()
    critical: dict[str, tuple[str, ...]] = {}
    for job_id in CRITICAL_STEPS:
        definition = _object(jobs.get(job_id), "BASE test job")
        _job_shape(job_id, definition)
        _condition(job_id, definition.get("if"), definition.get("needs"))
        name = definition.get("name", job_id)
        if not isinstance(name, str) or "${{" in name:
            raise Ineligible("unsupported_base_job_name")
        steps = definition.get("steps")
        if not isinstance(steps, list) or any(not isinstance(s, dict) for s in steps):
            raise Ineligible("unsupported_base_job_steps")
        step_names = [step.get("name") for step in steps if step.get("name") is not None]
        if step_names[:3] != [
            "Checkout trusted base",
            "Setup trusted evidence environment",
            VERIFY_STEP,
        ]:
            raise Ineligible("candidate_step_before_base_reuse_verifier")
        trusted_checkout = steps[0]
        trusted_options = _object(trusted_checkout.get("with"), "BASE projection checkout")
        if (
            set(trusted_checkout) != {"name", "if", "uses", "with"}
            or set(trusted_options) != {"ref", "fetch-depth", "persist-credentials"}
            or re.fullmatch(r"actions/checkout@[0-9a-f]{40}", str(trusted_checkout.get("uses", "")))
            is None
            or trusted_options.get("ref") != "${{ github.event.pull_request.base.sha }}"
            or trusted_options.get("fetch-depth") != 0
            or trusted_options.get("persist-credentials") is not False
        ):
            raise Ineligible("unsupported_base_projection_checkout")
        expected_steps = CRITICAL_STEPS[job_id] + (
            DIRECT_MARKER,
            REUSED_MARKER,
            VERIFY_STEP,
            "Checkout trusted base",
        )
        if any(step_names.count(required) != 1 for required in expected_steps):
            raise Ineligible("unsupported_base_native_step_contract")
        checkout = next(step for step in steps if step.get("name") == "Checkout")
        if (
            set(checkout) != {"name", "if", "uses", "with"}
            or _object(checkout.get("with"), "BASE direct checkout")
            != {"ref": "${{ github.sha }}", "fetch-depth": 0, "persist-credentials": False}
            or re.fullmatch(r"actions/checkout@[0-9a-f]{40}", str(checkout.get("uses", ""))) is None
        ):
            raise Ineligible("base_direct_checkout_not_event_bound")
        critical[job_id] = CRITICAL_STEPS[job_id]
        if job_id == "test-pr" and risk.contract_risk_groups:
            if step_names.count("Contract and risk suites") != 1:
                raise Ineligible("unsupported_base_contract_suite")
            critical[job_id] = (*critical[job_id], "Contract and risk suites")
        critical[job_id] = tuple(name for name in step_names if name in critical[job_id])
        strategy = definition.get("strategy")
        cells: list[Cell] = []
        if job_id == "test-pr":
            matrix = _object(_object(strategy, "BASE test strategy").get("matrix"), "BASE matrix")
            pr_versions = matrix.get("python-version")
            if (
                set(matrix) != {"python-version"}
                or not isinstance(pr_versions, list)
                or len(pr_versions) != 1
                or not isinstance(pr_versions[0], str)
                or re.fullmatch(PYTHON_VERSION_PATTERN, pr_versions[0]) is None
            ):
                raise Ineligible("unsupported_base_test_matrix")
            version = pr_versions[0]
            if version != python and version.split(".") != python.split(".")[:2]:
                raise Ineligible("inconsistent_base_coverage_runtime")
            cells.append(Cell(job_id, version, f"{name} ({version})", f"coverage-xml-{python}"))
        elif job_id == "test-main":
            matrix = _object(_object(strategy, "BASE test strategy").get("matrix"), "BASE matrix")
            if (
                set(matrix) != {"include"}
                or not isinstance(matrix["include"], list)
                or not 0 < len(matrix["include"]) <= 7
            ):
                raise Ineligible("unsupported_base_test_matrix")
            versions: set[str] = set()
            for entry in matrix["include"]:
                entry = _object(entry, "BASE matrix cell")
                if (
                    set(entry) != {"python-version", "timeout-minutes"}
                    or not isinstance(entry["python-version"], str)
                    or re.fullmatch(PYTHON_VERSION_PATTERN, entry["python-version"]) is None
                    or entry["python-version"] in versions
                    or type(entry["timeout-minutes"]) is not int
                    or not 0 < entry["timeout-minutes"] <= 180
                ):
                    raise Ineligible("unsupported_base_test_matrix")
                version = entry["python-version"]
                versions.add(version)
                cells.append(
                    Cell(
                        job_id,
                        version,
                        f"{name} ({version}, {entry['timeout-minutes']})",
                        f"coverage-main-xml-{version}",
                    )
                )
        else:
            if strategy is not None:
                raise Ineligible("unsupported_base_ios_matrix")
            cells.append(Cell(job_id, None, name, None))
        all_names.update(cell.check_name for cell in cells)
        all_names.add(name)
        include = (
            risk.run_backend_blocking
            if job_id == "test-pr"
            else risk.run_main_ci_diagnostic if job_id == "test-main" else ios
        )
        if include:
            selected.extend(cells)
    if not selected:
        raise Ineligible("empty_test_universe")
    # Whole BASE tree is an immutable configuration cut, encompassing workflow,
    # local actions, manifests, selection and test harness inputs without a
    # separately maintained dependency closure inventory.
    tree_sha = (
        evidence._run_git(root, ["rev-parse", f"{context.base_sha}^{{tree}}"])
        .decode("ascii")
        .strip()
    )
    digest = _digest(
        _canonical(
            {
                "base_tree_sha": _sha(tree_sha, "BASE tree"),
                "workflow_sha256": _digest(workflow_raw),
                "policy": POLICY_VERSION,
            }
        )
    )
    return BasePolicy(digest, tuple(selected), frozenset(all_names), critical)


def _run_tuple(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": _positive(run.get("id"), "run ID"),
        "run_attempt": _positive(run.get("run_attempt"), "run attempt"),
        "workflow_id": _positive(run.get("workflow_id"), "workflow ID"),
        "check_suite_id": _positive(run.get("check_suite_id"), "check suite ID"),
        "head_sha": _sha(run.get("head_sha"), "run head"),
    }


def _validate_run(
    run: dict[str, Any], context: Context, head_sha: str, *, require_base: bool = True
) -> dict[str, Any]:
    locator = _run_tuple(run)
    repository = _object(run.get("repository"), "run repository")
    head_repository = _object(run.get("head_repository"), "run head repository")
    _positive(repository.get("id"), "run repository ID")
    _positive(head_repository.get("id"), "run head repository ID")
    if (
        repository.get("full_name") != context.repository
        or repository.get("id") != context.repository_id
        or head_repository.get("full_name") != context.head_repository
        or head_repository.get("id") != context.head_repository_id
    ):
        raise ReuseError("workflow run has foreign repository identity")
    if (
        run.get("name") != "CI"
        or run.get("path") != WORKFLOW_PATH
        or run.get("event") != "pull_request"
        or locator["head_sha"] != head_sha
        or run.get("head_branch") != context.head_ref
    ):
        raise ReuseError("workflow run does not bind the canonical same-PR head")
    linked = run.get("pull_requests")
    if not isinstance(linked, list) or len(linked) != 1:
        raise ReuseError("workflow run does not bind exactly one PR")
    pr = _object(linked[0], "run PR")
    _positive(pr.get("number"), "run PR number")
    base, head = _object(pr.get("base"), "run PR base"), _object(pr.get("head"), "run PR head")
    if (
        pr.get("number") != context.pr_number
        or (require_base and base.get("sha") != context.base_sha)
        or head.get("sha") != head_sha
    ):
        raise ReuseError("workflow run PR/base/head binding differs")
    _sha(base.get("sha"), "workflow run base")
    if (
        run.get("url")
        != f"https://api.github.com/repos/{context.repository}/actions/runs/{locator['run_id']}"
    ):
        raise ReuseError("workflow run URL has foreign identity")
    _time(run.get("created_at"), "run creation")
    _time(run.get("run_started_at"), "attempt start")
    return locator


def _latest_run(context: Context, head_sha: str, token: str) -> dict[str, Any] | None:
    rows = _pages(
        context.repository,
        f"actions/workflows/ci.yml/runs?event=pull_request&head_sha={head_sha}",
        "workflow_runs",
        token,
    )
    matching: list[dict[str, Any]] = []
    for row in rows:
        linked = row.get("pull_requests")
        if not isinstance(linked, list):
            raise ReuseError("workflow run PR inventory is malformed")
        if any(isinstance(pr, dict) and pr.get("number") == context.pr_number for pr in linked):
            _validate_run(row, context, head_sha, require_base=False)
            matching.append(row)
    if not matching:
        return None
    newest = max(
        matching,
        key=lambda row: (
            _time(row.get("run_started_at"), "latest attempt start"),
            _time(row.get("created_at"), "run creation"),
            _positive(row.get("id"), "run ID"),
        ),
    )
    same_start = [
        row for row in matching if row.get("run_started_at") == newest.get("run_started_at")
    ]
    if len(same_start) > 1 and any(row["run_attempt"] > 1 for row in same_start):
        raise Ineligible("latest_attempt_order_ambiguous")
    live = _object(_api(context.repository, f"actions/runs/{newest['id']}", token), "latest run")
    _validate_run(live, context, head_sha, require_base=False)
    if (
        _run_tuple(live) != _run_tuple(newest)
        or live.get("run_started_at") != newest.get("run_started_at")
        or live["pull_requests"] != newest["pull_requests"]
    ):
        raise ReuseError("workflow latest attempt changed during selection")
    if live["pull_requests"][0]["base"]["sha"] != context.base_sha:
        raise Ineligible("latest_source_base_differs")
    return live


def _env_id(name: str) -> int:
    raw = os.environ.get(name)
    if not isinstance(raw, str) or re.fullmatch(r"[1-9][0-9]*", raw) is None:
        raise ReuseError(f"{name} must be a canonical positive Actions ID")
    return int(raw)


def _current_run(context: Context, token: str) -> dict[str, Any]:
    run_id, attempt = _env_id("GITHUB_RUN_ID"), _env_id("GITHUB_RUN_ATTEMPT")
    run = _object(_api(context.repository, f"actions/runs/{run_id}", token), "current run")
    locator = _validate_run(run, context, context.head_sha)
    if locator["run_attempt"] != attempt:
        raise ReuseError("current workflow attempt changed")
    return run


def _refresh(
    context: Context, run: dict[str, Any], token: str, *, source: dict[str, Any] | None = None
) -> None:
    fresh = _context(
        context.repository,
        context.pr_number,
        token,
        expected_head=context.head_sha,
        expected_base=context.base_sha,
    )
    if fresh.base_ref != context.base_ref or fresh.current_base_sha != context.current_base_sha:
        raise ReuseError("native PR base ref or target changed during proof")
    if (
        fresh.repository_id != context.repository_id
        or fresh.head_repository != context.head_repository
        or fresh.head_repository_id != context.head_repository_id
        or fresh.snapshot.commit_shas != context.snapshot.commit_shas
    ):
        raise ReuseError("complete PR graph changed during evidence proof")
    try:
        current = _latest_run(context, context.head_sha, token)
    except Ineligible as exc:
        raise ReuseError("current workflow binding changed during proof") from exc
    if current is None or _run_tuple(current) != _run_tuple(run):
        raise ReuseError("current workflow run or attempt is no longer latest")
    if source is not None:
        try:
            latest_source = _latest_run(context, source["head_sha"], token)
        except Ineligible as exc:
            raise ReuseError("direct source binding changed during proof") from exc
        if (
            latest_source is None
            or _run_tuple(latest_source) != source
            or latest_source.get("status") != "completed"
        ):
            raise ReuseError("direct source run or attempt changed")


def _commit_tree(context: Context, checkout_sha: str, *, tested_head: str, token: str) -> str:
    commit = _object(
        _api(context.repository, f"git/commits/{_sha(checkout_sha, 'event checkout')}", token),
        "synthetic commit",
    )
    parents = commit.get("parents")
    if commit.get("sha") != checkout_sha or not isinstance(parents, list) or len(parents) != 2:
        raise ReuseError("event checkout is not an authenticated synthetic merge")
    if [
        _sha(_object(parent, "synthetic parent").get("sha"), "synthetic parent")
        for parent in parents
    ] != [context.base_sha, tested_head]:
        raise ReuseError("event synthetic merge does not have ordered exact base/head parents")
    tree_sha = _sha(_object(commit.get("tree"), "synthetic tree").get("sha"), "synthetic tree")
    tree = _object(
        _api(context.repository, f"git/trees/{tree_sha}?recursive=1", token), "complete merge tree"
    )
    if (
        tree.get("sha") != tree_sha
        or tree.get("truncated") is not False
        or not isinstance(tree.get("tree"), list)
        or len(tree["tree"]) > 100_000
    ):
        raise ReuseError("recursive merge tree is truncated or incomplete")
    mapping = f"docs/review/PR_{context.pr_number}_FIXED_MAPPING.md"
    leaves: list[dict[str, str]] = []
    paths: set[str] = set()
    for raw in tree["tree"]:
        entry = _object(raw, "merge tree entry")
        path = entry.get("path")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or any(c in path for c in "\x00\r\n")
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or path in paths
        ):
            raise ReuseError("merge tree path is malformed or duplicated")
        paths.add(path)
        mode, kind = entry.get("mode"), entry.get("type")
        sha = _sha(entry.get("sha"), "tree entry SHA")
        if kind == "tree" and mode == "040000":
            continue
        if not (
            (kind == "blob" and mode in {"100644", "100755", "120000"})
            or (kind == "commit" and mode == "160000")
        ):
            raise ReuseError("merge tree has unsupported entry type")
        if path != mapping:
            leaves.append({"path": path, "mode": mode, "type": kind, "sha": sha})
    return _digest(_canonical(sorted(leaves, key=lambda entry: entry["path"])))


def _material(
    root: Path, context: Context, *, successor: bool
) -> tuple[evidence.MaterialManifest, str]:
    if context.base_sha != context.current_base_sha:
        raise Ineligible("snapshot_base_behind_native_target")
    if context.is_fork:
        raise Ineligible("fork_pr_ordinary_only")
    live = evidence.compute_material_manifest(
        root,
        base_ref_oid=context.base_sha,
        head_ref_oid=context.head_sha,
        pr_number=context.pr_number,
    )
    if not successor:
        return live, context.head_sha
    try:
        seal = evidence.parse_embedded_review_seal(
            evidence._stale_seal_mapping_blob(
                root, commit_sha=context.head_sha, pr_number=context.pr_number
            )
        )
    except (evidence.ReviewEvidenceError, UnicodeError) as exc:
        raise Ineligible("canonical_seal_unavailable") from exc
    if not evidence.is_provider_no_claim_review_receipt(
        seal["code_review"]
    ) or not evidence.is_provider_no_claim_security_receipt(seal["codex_security"]):
        raise Ineligible("target_seal_not_provider_neutral")
    sealed = seal["material"]
    material_head = sealed["material_head_sha"]
    if (
        seal["repository"] != context.repository
        or seal["pr_number"] != context.pr_number
        or sealed["base_ref_oid"] != context.base_sha
        or sealed["merge_base_sha"] != live.merge_base_sha
        or sealed["digest"] != live.digest
        or material_head not in context.snapshot.commit_shas
    ):
        raise Ineligible("canonical_seal_context_differs")
    _ensure_git(root, material_head)
    try:
        evidence.validate_mapping_only_closeout_successor(
            root,
            material_head_sha=material_head,
            live_head_sha=context.head_sha,
            pr_number=context.pr_number,
        )
    except evidence.ReviewEvidenceError as exc:
        raise Ineligible("not_single_mapping_successor") from exc
    frozen = evidence.compute_material_manifest(
        root, base_ref_oid=context.base_sha, head_ref_oid=material_head, pr_number=context.pr_number
    )
    if frozen.digest != live.digest or frozen.merge_base_sha != live.merge_base_sha:
        raise Ineligible("sealed_material_differs")
    evidence.validate_review_seal(
        seal,
        material_paths=(entry.path for entry in frozen.entries),
        material_diff_summary=frozen.diff_summary,
    )
    return frozen, material_head


def _steps(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = job.get("steps")
    if not isinstance(raw, list) or len(raw) > 150:
        raise ReuseError("native job step inventory is incomplete")
    result: dict[str, dict[str, Any]] = {}
    numbers: set[int] = set()
    for item in raw:
        item = _object(item, "native step")
        name = item.get("name")
        number = _positive(item.get("number"), "native step number")
        if not isinstance(name, str) or not name or name in result or number in numbers:
            raise ReuseError("native job step identity is duplicated or malformed")
        result[name] = item
        numbers.add(number)
    return result


def _success_step(steps: Mapping[str, dict[str, Any]], name: str) -> dict[str, Any]:
    step = steps.get(name)
    if (
        not isinstance(step, dict)
        or step.get("status") != "completed"
        or step.get("conclusion") != "success"
    ):
        raise Ineligible("required_native_execution_step_not_successful")
    start, end = _time(step.get("started_at"), "step start"), _time(
        step.get("completed_at"), "step completion"
    )
    if start > end:
        raise ReuseError("native step interval is invalid")
    return step


def _job_identity(
    job: dict[str, Any], context: Context, run: dict[str, Any], token: str, *, complete: bool = True
) -> dict[str, dict[str, Any]]:
    locator = _run_tuple(run)
    job_id = _positive(job.get("id"), "native job ID")
    _positive(job.get("run_id"), "native run ID")
    _positive(job.get("run_attempt"), "native run attempt")
    if (
        job.get("run_id") != locator["run_id"]
        or job.get("run_attempt") != locator["run_attempt"]
        or job.get("head_sha") != locator["head_sha"]
        or job.get("workflow_name") != "CI"
    ):
        raise ReuseError("native job is from another run, head or attempt")
    url = f"https://api.github.com/repos/{context.repository}/check-runs/{job_id}"
    if (
        job.get("check_run_url") != url
        or job.get("run_url")
        != f"https://api.github.com/repos/{context.repository}/actions/runs/{locator['run_id']}"
    ):
        raise ReuseError("native job URL does not bind repository identity")
    check = _object(_api(context.repository, f"check-runs/{job_id}", token), "native check")
    app = _object(check.get("app"), "native App")
    suite = _object(check.get("check_suite"), "native check suite")
    _positive(check.get("id"), "native check ID")
    _positive(app.get("id"), "native App ID")
    _positive(suite.get("id"), "native check suite ID")
    if (
        app.get("id") != GITHUB_ACTIONS_APP_ID
        or app.get("slug") != "github-actions"
        or suite.get("id") != locator["check_suite_id"]
        or check.get("id") != job_id
        or check.get("name") != job.get("name")
        or check.get("head_sha") != locator["head_sha"]
    ):
        raise ReuseError("native check App/suite/name/head identity differs")
    if check.get("status") != job.get("status") or check.get("conclusion") != job.get("conclusion"):
        raise ReuseError("native job and check conclusions differ")
    if complete and (job.get("status") != "completed" or job.get("conclusion") != "success"):
        raise Ineligible("selected_native_job_not_successful")
    return _steps(job)


def _jobs(context: Context, run: dict[str, Any], token: str) -> list[dict[str, Any]]:
    locator = _run_tuple(run)
    return _pages(
        context.repository,
        f"actions/runs/{locator['run_id']}/attempts/{locator['run_attempt']}/jobs",
        "jobs",
        token,
    )


def _selected_jobs(
    context: Context, run: dict[str, Any], policy: BasePolicy, token: str, *, direct_only: bool
) -> list[tuple[Cell, dict[str, Any], str]]:
    jobs = _jobs(context, run, token)
    expected = {cell.check_name for cell in policy.cells}
    selected: dict[str, dict[str, Any]] = {}
    for job in jobs:
        name = job.get("name")
        if not isinstance(name, str):
            raise ReuseError("native job name is malformed")
        if name in policy.all_names:
            if name in expected:
                if name in selected:
                    raise ReuseError("supported native matrix cell is duplicated")
                selected[name] = job
            elif job.get("status") != "completed" or job.get("conclusion") != "skipped":
                raise ReuseError("universe omits an executed supported cell")
        elif any(name.startswith(f"{job_id} (") for job_id in ("test-pr", "test-main")):
            raise ReuseError("native test matrix contains an unsupported cell")
    if set(selected) != expected:
        raise Ineligible("native_test_universe_incomplete")
    result: list[tuple[Cell, dict[str, Any], str]] = []
    for cell in policy.cells:
        job = selected[cell.check_name]
        steps = _job_identity(job, context, run, token)
        direct = steps.get(DIRECT_MARKER, {}).get("conclusion") == "success"
        reused = steps.get(REUSED_MARKER, {}).get("conclusion") == "success"
        if not direct and not reused:
            raise Ineligible("native_execution_proof_absent")
        if direct == reused or (direct_only and reused):
            raise ReuseError("native execution markers are contradictory or inherited")
        if direct:
            _success_step(steps, DIRECT_MARKER)
            for name in policy.critical[cell.job_id]:
                _success_step(steps, name)
            ordered = [
                steps[name]["number"] for name in (*policy.critical[cell.job_id], DIRECT_MARKER)
            ]
            if ordered != sorted(ordered):
                raise ReuseError("native direct critical steps are out of order")
            for name in (VERIFY_STEP, REUSED_MARKER):
                if steps.get(name, {}).get("conclusion") != "skipped":
                    raise ReuseError("direct job also asserted reuse")
            mode = "executed"
        else:
            for name in ("Checkout trusted base", VERIFY_STEP, REUSED_MARKER):
                _success_step(steps, name)
            ordered = [
                steps[name]["number"]
                for name in ("Checkout trusted base", VERIFY_STEP, REUSED_MARKER)
            ]
            if ordered != sorted(ordered):
                raise ReuseError("native reused verifier steps are out of order")
            for name in (*policy.critical[cell.job_id], DIRECT_MARKER):
                if name in {UPLOAD_PR, UPLOAD_MAIN}:
                    continue
                if steps.get(name, {}).get("conclusion") != "skipped":
                    raise ReuseError("reused job executed candidate critical steps")
            if cell.coverage_name is not None:
                _success_step(steps, UPLOAD_PR if cell.job_id == "test-pr" else UPLOAD_MAIN)
            mode = "reused"
        result.append((cell, job, mode))
    return result


def _writer(context: Context, run: dict[str, Any], token: str) -> dict[str, Any]:
    writers = [job for job in _jobs(context, run, token) if job.get("name") == WRITER_NAME]
    if not writers:
        raise Ineligible("source_evidence_writer_absent")
    if len(writers) != 1:
        raise ReuseError("source evidence writer is duplicated")
    writer = writers[0]
    steps = _job_identity(writer, context, run, token)
    for name in ("Checkout trusted base", WRITER_COLLECT, WRITER_UPLOAD):
        _success_step(steps, name)
    return writer


def _artifact_ref(metadata: dict[str, Any], member_digest: str) -> dict[str, Any]:
    return {
        "artifact_id": _positive(metadata.get("id"), "artifact ID"),
        "name": metadata.get("name"),
        "archive_digest": _hash(metadata.get("digest"), "artifact archive digest"),
        "member_digest": _hash(member_digest, "artifact member digest"),
    }


def _artifact_metadata(
    context: Context,
    run: dict[str, Any],
    metadata: dict[str, Any],
    *,
    name: str,
    producer: dict[str, Any],
    upload_step: str,
) -> None:
    artifact_id = _positive(metadata.get("id"), "artifact ID")
    if metadata.get("name") != name or type(metadata.get("expired")) is not bool:
        raise ReuseError("artifact identity or expiry flag differs")
    if (
        metadata.get("url")
        != f"https://api.github.com/repos/{context.repository}/actions/artifacts/{artifact_id}"
        or metadata.get("archive_download_url")
        != f"https://api.github.com/repos/{context.repository}/actions/artifacts/{artifact_id}/zip"
    ):
        raise ReuseError("artifact endpoint has foreign identity")
    native = _object(metadata.get("workflow_run"), "artifact run")
    for field in ("id", "repository_id", "head_repository_id"):
        _positive(native.get(field), "artifact run identity")
    if (
        native.get("id") != run["id"]
        or native.get("head_sha") != run["head_sha"]
        or native.get("repository_id") != context.repository_id
        or native.get("head_repository_id") != context.repository_id
    ):
        raise ReuseError("artifact run/repository/head identity differs")
    if metadata["expired"] or _time(metadata.get("expires_at"), "artifact expiry") <= datetime.now(
        timezone.utc
    ):
        raise Ineligible("source_artifact_expired")
    _hash(metadata.get("digest"), "artifact digest")
    size = _positive(metadata.get("size_in_bytes"), "artifact size")
    if size > MAX_ARCHIVE_BYTES:
        raise ReuseError("artifact exceeds archive byte budget")
    step = _success_step(_steps(producer), upload_step)
    created = _time(metadata.get("created_at"), "artifact creation")
    if not _time(step.get("started_at"), "producer upload start") <= created <= _time(
        step.get("completed_at"), "producer upload end"
    ) or created < _time(run.get("run_started_at"), "attempt start"):
        raise ReuseError("artifact is outside its native latest-attempt upload interval")
    updated = _time(metadata.get("updated_at"), "artifact update")
    if updated < created:
        raise ReuseError("artifact timestamps are contradictory")


def _zip_member(raw: bytes, *, expected_member: str, limit: int) -> bytes:
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ReuseError("artifact ZIP exceeds its archive budget")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if len(members) != 1:
                raise ReuseError("artifact ZIP must contain exactly one member")
            member = members[0]
            unix_mode = member.external_attr >> 16
            kind = stat.S_IFMT(unix_mode)
            if (
                member.filename != expected_member
                or member.orig_filename != expected_member
                or member.is_dir()
                or member.flag_bits & 1
                or member.external_attr & 0x10
                or kind not in {0, stat.S_IFREG}
                or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                or not 0 < member.file_size <= limit
                or member.compress_size > MAX_ARCHIVE_BYTES
            ):
                raise ReuseError("artifact ZIP member is unsafe or exceeds its budget")
            with archive.open(member) as handle:
                content = handle.read(limit + 1)
            if len(content) != member.file_size or len(content) > limit:
                raise ReuseError("artifact ZIP expansion is incomplete or over budget")
            return content
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, OSError) as exc:
        raise ReuseError("artifact ZIP is malformed") from exc


def _coverage_xml(raw: bytes) -> None:
    attributes: dict[str, str] | None = None
    stack: list[Any] = []
    nodes = 0
    try:
        for event, element in ElementTree.iterparse(
            io.BytesIO(raw),
            events=("start", "end"),
            forbid_dtd=False,
            forbid_entities=True,
            forbid_external=True,
        ):
            if event == "start":
                nodes += 1
                stack.append(element)
                if nodes > 300_000 or len(stack) > 128:
                    raise ReuseError("coverage XML exceeds its structural budget")
                if attributes is None:
                    if element.tag != "coverage":
                        raise ReuseError("coverage XML has unsupported structure")
                    attributes = dict(element.attrib)
            else:
                stack.pop()
                element.clear()
                if stack:
                    stack[-1].remove(element)
    except (ElementTree.ParseError, DefusedXmlException, UnicodeError, ValueError) as exc:
        raise ReuseError("coverage XML is malformed or unsafe") from exc
    if attributes is None:
        raise ReuseError("coverage XML has unsupported structure")
    for name in ("lines-valid", "lines-covered"):
        value = attributes.get(name)
        if value is None or len(value) > 12 or re.fullmatch(r"[0-9]+", value) is None:
            raise ReuseError("coverage XML counts are malformed")
    if int(attributes["lines-covered"]) > int(attributes["lines-valid"]):
        raise ReuseError("coverage XML counts are contradictory")
    rate = attributes.get("line-rate")
    if (
        rate is None
        or len(rate) > 32
        or re.fullmatch(r"(?:0(?:\.[0-9]+)?|1(?:\.0+)?)", rate) is None
    ):
        raise ReuseError("coverage XML line rate is malformed")


def _artifact(
    context: Context,
    run: dict[str, Any],
    *,
    name: str,
    producer: dict[str, Any],
    upload_step: str,
    member: str,
    token: str,
    asserted: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes]:
    rows = _pages(context.repository, f"actions/runs/{run['id']}/artifacts", "artifacts", token)
    matches = [row for row in rows if row.get("name") == name]
    if not matches:
        raise Ineligible("attempt_specific_artifact_absent")
    if len(matches) != 1:
        raise ReuseError("attempt-specific artifact is duplicated")
    metadata = matches[0]
    _artifact_metadata(
        context, run, metadata, name=name, producer=producer, upload_step=upload_step
    )
    raw = identity.github_artifact_download(
        metadata["archive_download_url"], token=token, max_bytes=MAX_ARCHIVE_BYTES
    )
    if len(raw) != metadata["size_in_bytes"] or _digest(raw) != metadata["digest"]:
        raise ReuseError("artifact archive size or digest differs")
    content = _zip_member(
        raw,
        expected_member=member,
        limit=MAX_MANIFEST_BYTES if member.endswith(".json") else MAX_MEMBER_BYTES,
    )
    if member == "coverage.xml":
        _coverage_xml(content)
    reference = _artifact_ref(metadata, _digest(content))
    if asserted is not None and reference != asserted:
        raise ReuseError("asserted immutable artifact identity or member digest differs")
    fresh = _object(
        _api(context.repository, f"actions/artifacts/{metadata['id']}", token), "fresh artifact"
    )
    try:
        _artifact_metadata(
            context, run, fresh, name=name, producer=producer, upload_step=upload_step
        )
    except Ineligible as exc:
        raise ReuseError("artifact availability changed during proof") from exc
    if fresh != metadata:
        raise ReuseError("artifact metadata changed during proof")
    return reference, content


COMMON_FIELDS = {
    "schema_version",
    "policy_version",
    "asset_type",
    "repository",
    "repository_id",
    "pr_number",
    "base_sha",
    "head_sha",
    "material_head_sha",
    "merge_base_sha",
    "material_digest",
    "config_digest",
    "universe",
    "run",
    "checkout_sha",
    "merge_tree_digest",
    "source",
    "mode",
    "reason",
    "upstream_assets",
    "idempotency_key",
    "fingerprint",
}


def _finish_document(document: dict[str, Any]) -> dict[str, Any]:
    value = dict(document)
    value.pop("fingerprint", None)
    value["fingerprint"] = _digest(_canonical(value))
    return value


def _validate_document(document: Any, *, schema: str) -> dict[str, Any]:
    value = _object(document, "evidence document")
    _keys(
        value,
        COMMON_FIELDS | ({"jobs"} if schema == MANIFEST_SCHEMA else set()),
        "evidence document",
    )
    if (
        value["schema_version"] != schema
        or value["policy_version"] != POLICY_VERSION
        or value["asset_type"]
        != ("ci_test_execution" if schema == MANIFEST_SCHEMA else "ci_test_reuse_plan")
        or not isinstance(value["mode"], str)
        or value["mode"] not in {"executed", "reused"}
    ):
        raise ReuseError("evidence document schema, policy or mode differs")
    if value["fingerprint"] != _finish_document(value)["fingerprint"]:
        raise ReuseError("evidence document fingerprint differs")
    _positive(value["pr_number"], "document PR")
    _positive(value["repository_id"], "document repository")
    for key in ("base_sha", "head_sha"):
        _sha(value[key], key)
    run = _object(value["run"], "document run")
    _keys(
        run, {"run_id", "run_attempt", "workflow_id", "check_suite_id", "head_sha"}, "document run"
    )
    for key in ("run_id", "run_attempt", "workflow_id", "check_suite_id"):
        _positive(run[key], key)
    if _sha(run["head_sha"], "document run head") != value["head_sha"]:
        raise ReuseError("document run and head differ")
    expected_idempotency = f"{POLICY_VERSION}:{value['repository']}:{run['run_id']}:{run['run_attempt']}:{value['asset_type']}"
    if value["idempotency_key"] != expected_idempotency:
        raise ReuseError("document idempotency binding differs")
    if (
        not isinstance(value["upstream_assets"], list)
        or len(value["upstream_assets"]) > 50
        or not isinstance(value["universe"], list)
        or len(value["universe"]) > 10
    ):
        raise ReuseError("document upstream or universe is malformed")
    if not isinstance(value["reason"], str) or re.fullmatch(r"[a-z_]+", value["reason"]) is None:
        raise ReuseError("document reason is malformed")
    if value["mode"] == "reused" and value["source"] is None:
        raise ReuseError("reused document does not name a direct source")
    if schema == MANIFEST_SCHEMA and (
        not isinstance(value["jobs"], list) or not 0 < len(value["jobs"]) <= 10
    ):
        raise ReuseError("manifest job inventory is malformed")
    return value


def _document(
    context: Context,
    run: dict[str, Any],
    *,
    schema: str,
    material: evidence.MaterialManifest | None = None,
    material_head: str | None = None,
    policy: BasePolicy | None = None,
    checkout_sha: str | None = None,
    tree_digest: str | None = None,
    mode: str = "executed",
    reason: str = "ordinary_execution",
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    asset_type = "ci_test_execution" if schema == MANIFEST_SCHEMA else "ci_test_reuse_plan"
    locator = _run_tuple(run)
    value: dict[str, Any] = {
        "schema_version": schema,
        "policy_version": POLICY_VERSION,
        "asset_type": asset_type,
        "repository": context.repository,
        "repository_id": context.repository_id,
        "pr_number": context.pr_number,
        "base_sha": context.base_sha,
        "head_sha": context.head_sha,
        "material_head_sha": material_head,
        "merge_base_sha": material.merge_base_sha if material is not None else None,
        "material_digest": material.digest if material is not None else None,
        "config_digest": policy.config_digest if policy is not None else None,
        "universe": [cell.as_dict() for cell in policy.cells] if policy is not None else [],
        "run": locator,
        "checkout_sha": checkout_sha,
        "merge_tree_digest": tree_digest,
        "source": source,
        "mode": mode,
        "reason": reason,
        "upstream_assets": [],
        "idempotency_key": f"{POLICY_VERSION}:{context.repository}:{locator['run_id']}:{locator['run_attempt']}:{asset_type}",
    }
    if source is not None:
        value["upstream_assets"] = [source]
    return _finish_document(value)


def _binding(
    document: dict[str, Any],
    context: Context,
    run: dict[str, Any],
    material: evidence.MaterialManifest,
    material_head: str,
    policy: BasePolicy,
    *,
    checkout_sha: str,
    tree_digest: str,
) -> None:
    expected = _document(
        context,
        run,
        schema=document["schema_version"],
        material=material,
        material_head=material_head,
        policy=policy,
        checkout_sha=checkout_sha,
        tree_digest=tree_digest,
    )
    for key in (
        "repository",
        "repository_id",
        "pr_number",
        "base_sha",
        "head_sha",
        "material_head_sha",
        "merge_base_sha",
        "material_digest",
        "config_digest",
        "universe",
        "run",
        "checkout_sha",
        "merge_tree_digest",
        "idempotency_key",
    ):
        if document[key] != expected[key]:
            raise ReuseError(
                "asserted document differs from independently derived material/run/test binding"
            )


def _source_locator(run: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    return {"run": _run_tuple(run), "artifact": artifact}


def _coverage_rows(
    context: Context,
    run: dict[str, Any],
    selected: list[tuple[Cell, dict[str, Any], str]],
    token: str,
    *,
    asserted: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    rows: list[dict[str, Any]] = []
    contents: dict[str, bytes] = {}
    if asserted is not None and len(asserted) != len(selected):
        raise ReuseError("manifest native cell inventory differs")
    for index, (cell, job, mode) in enumerate(selected):
        expected_row = asserted[index] if asserted is not None else None
        if expected_row is not None:
            expected_row = _object(expected_row, "manifest job")
            _keys(expected_row, {"cell", "native_job_id", "mode", "coverage"}, "manifest job")
            if (
                expected_row["cell"] != cell.as_dict()
                or expected_row["native_job_id"] != job["id"]
                or expected_row["mode"] != mode
            ):
                raise ReuseError("manifest cell/native execution differs")
        coverage = None
        if cell.coverage_name is not None:
            name = _coverage_name(cell, _run_tuple(run))
            if name is None:
                raise ReuseError("coverage cell has no artifact name")
            if expected_row is not None and not isinstance(expected_row["coverage"], dict):
                raise ReuseError("manifest coverage locator is absent")
            coverage, content = _artifact(
                context,
                run,
                name=name,
                producer=job,
                upload_step=UPLOAD_PR if cell.job_id == "test-pr" else UPLOAD_MAIN,
                member="coverage.xml",
                token=token,
                asserted=expected_row["coverage"] if expected_row is not None else None,
            )
            contents[cell.check_name] = content
        elif expected_row is not None and expected_row["coverage"] is not None:
            raise ReuseError("manifest adds coverage to a non-coverage cell")
        rows.append(
            {"cell": cell.as_dict(), "native_job_id": job["id"], "mode": mode, "coverage": coverage}
        )
    return rows, contents


def _source(
    context: Context,
    material: evidence.MaterialManifest,
    material_head: str,
    policy: BasePolicy,
    token: str,
    *,
    target_tree_digest: str,
    asserted: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    if context.is_fork:
        raise ReuseError("fork PR cannot admit a reusable source")
    if asserted is not None:
        asserted = _object(asserted, "direct source")
        _keys(asserted, {"run", "artifact"}, "direct source")
    run = _latest_run(context, material_head, token)
    if run is None:
        raise Ineligible("source_absent")
    if run.get("status") != "completed" or run.get("conclusion") not in {"success", "failure"}:
        raise Ineligible("latest_source_not_completed")
    if asserted is not None and asserted["run"] != _run_tuple(run):
        raise ReuseError("asserted direct source is no longer latest")
    writer = _writer(context, run, token)
    name = f"ci-test-execution-{run['id']}-{run['run_attempt']}"
    artifact, raw = _artifact(
        context,
        run,
        name=name,
        producer=writer,
        upload_step=WRITER_UPLOAD,
        member="ci-test-execution.json",
        token=token,
        asserted=asserted["artifact"] if asserted is not None else None,
    )
    manifest = _validate_document(_json(raw), schema=MANIFEST_SCHEMA)
    if (
        manifest["mode"] != "executed"
        or manifest["source"] is not None
        or any(
            not isinstance(row, dict) or row.get("mode") != "executed" for row in manifest["jobs"]
        )
    ):
        raise ReuseError("source contains inherited test evidence")
    source_context = Context(
        context.repository,
        context.pr_number,
        context.repository_id,
        context.base_sha,
        material_head,
        context.head_ref,
        context.snapshot,
        context.head_repository,
        context.head_repository_id,
        context.base_ref,
        context.current_base_sha,
    )
    checkout = _sha(manifest["checkout_sha"], "source event checkout")
    tree_digest = _commit_tree(context, checkout, tested_head=material_head, token=token)
    if tree_digest != target_tree_digest:
        raise ReuseError("source and target complete merge material trees differ")
    _binding(
        manifest,
        source_context,
        run,
        material,
        material_head,
        policy,
        checkout_sha=checkout,
        tree_digest=tree_digest,
    )
    selected = _selected_jobs(context, run, policy, token, direct_only=True)
    if not isinstance(manifest["jobs"], list):
        raise ReuseError("source manifest jobs are malformed")
    rows, contents = _coverage_rows(context, run, selected, token, asserted=manifest["jobs"])
    expected_upstreams = [
        {"native_job_id": row["native_job_id"], "coverage": row["coverage"]} for row in rows
    ]
    if (
        manifest["upstream_assets"] != expected_upstreams
        or manifest["reason"] != "native_execution"
    ):
        raise ReuseError("source upstream execution inventory differs")
    _refresh_artifacts(context, run, selected, rows, token, aggregate=artifact, writer=writer)
    # Selection and immutable artifact metadata are refreshed again by each
    # projection/final consumer; no central-plan trust shortcut exists.
    try:
        latest = _latest_run(context, material_head, token)
    except Ineligible as exc:
        raise ReuseError("source availability changed after native proof") from exc
    if (
        latest is None
        or _run_tuple(latest) != _run_tuple(run)
        or latest.get("status") != "completed"
    ):
        raise ReuseError("source latest identity changed after native proof")
    return _source_locator(run, artifact), contents


def _refresh_artifacts(
    context: Context,
    run: dict[str, Any],
    selected: list[tuple[Cell, dict[str, Any], str]],
    rows: list[dict[str, Any]],
    token: str,
    *,
    aggregate: dict[str, Any] | None = None,
    writer: dict[str, Any] | None = None,
) -> None:
    refs = [
        (row["coverage"], job, UPLOAD_PR if cell.job_id == "test-pr" else UPLOAD_MAIN)
        for (cell, job, _mode), row in zip(selected, rows, strict=True)
        if row["coverage"] is not None
    ]
    if aggregate is not None:
        if writer is None:
            raise ReuseError("aggregate refresh has no native writer")
        refs.append((aggregate, writer, WRITER_UPLOAD))
    for reference, producer, upload in refs:
        metadata = _object(
            _api(context.repository, f"actions/artifacts/{reference['artifact_id']}", token),
            "final artifact",
        )
        try:
            _artifact_metadata(
                context,
                run,
                metadata,
                name=reference["name"],
                producer=producer,
                upload_step=upload,
            )
        except Ineligible as exc:
            raise ReuseError(f"artifact availability changed after complete proof: {exc}") from exc
        if (
            metadata["id"] != reference["artifact_id"]
            or metadata["digest"] != reference["archive_digest"]
        ):
            raise ReuseError("immutable artifact identity changed after complete proof")


def _reused_coverage_matches(
    rows: list[dict[str, Any]], source_contents: Mapping[str, bytes]
) -> None:
    for row in rows:
        coverage = row["coverage"]
        if row["mode"] == "reused" and coverage is not None:
            source = source_contents.get(row["cell"]["check_name"])
            if source is None or coverage["member_digest"] != _digest(source):
                raise ReuseError("reused coverage differs from its authenticated direct source")


def _event(path: Path, repository: str | None, pr_number: int | None) -> tuple[str, int, str, str]:
    raw = _object(_json(_safe_read(path, MAX_MANIFEST_BYTES)), "event")
    repo = _object(raw.get("repository"), "event repository").get("full_name")
    pr = _object(raw.get("pull_request"), "event PR")
    number = _positive(pr.get("number"), "event PR number")
    if (
        repository is not None
        and repository != repo
        or pr_number is not None
        and pr_number != number
    ):
        raise ReuseError("event repository or PR differs from command")
    if not isinstance(repo, str):
        raise ReuseError("event repository is malformed")
    return (
        repo,
        number,
        _sha(_object(pr.get("head"), "event head").get("sha"), "event head"),
        _sha(_object(pr.get("base"), "event base").get("sha"), "event base"),
    )


def _open_parent(path: Path) -> tuple[int, str]:
    absolute = path.absolute()
    if any(part in {".", ".."} for part in absolute.parts) or not absolute.name:
        raise ReuseError("local artifact path is malformed")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parent.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor, absolute.name
    except OSError as exc:
        os.close(descriptor)
        raise ReuseError("local artifact parent must be a real directory chain") from exc


def _safe_read(path: Path, limit: int) -> bytes:
    parent, name = _open_parent(path)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ReuseError("local artifact must be a bounded regular file")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                raw = handle.read(limit + 1)
            if len(raw) > limit or len(raw) != info.st_size:
                raise ReuseError("local artifact is incomplete or over budget")
            return raw
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise ReuseError("local artifact cannot be read safely") from exc
    finally:
        os.close(parent)


def _safe_write(path: Path, raw: bytes) -> None:
    parent, name = _open_parent(path)
    try:
        descriptor = os.open(
            name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except FileExistsError:
        if _safe_read(path, MAX_ARCHIVE_BYTES) != raw:
            raise ReuseError("same-run artifact replay differs")
    except OSError as exc:
        raise ReuseError("local artifact cannot be written safely") from exc
    finally:
        os.close(parent)


def _output(path: Path | None, values: Mapping[str, str]) -> None:
    if path is None:
        return
    if any("\n" in value or "\r" in value for value in values.values()):
        raise ReuseError("Actions outputs must be single-line")
    parent, name = _open_parent(path)
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600,
            dir_fd=parent,
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ReuseError("Actions output must be a regular file")
            os.write(
                descriptor,
                "".join(f"{key}={value}\n" for key, value in values.items()).encode("utf-8"),
            )
        finally:
            os.close(descriptor)
    finally:
        os.close(parent)


def plan_reuse(
    *, repo_root: Path, context: Context, run: dict[str, Any], token: str, checkout_sha: str
) -> dict[str, Any]:
    _trusted_base(repo_root, context)
    ordinary = _document(context, run, schema=PLAN_SCHEMA)
    if context.is_fork:
        value = _document(
            context,
            run,
            schema=PLAN_SCHEMA,
            checkout_sha=_sha(checkout_sha, "event checkout"),
            reason="fork_pr_ordinary_only",
        )
        _refresh(context, run, token)
        return value
    try:
        material, material_head = _material(repo_root, context, successor=True)
        policy = _policy(repo_root, context, material)
        tree = _commit_tree(context, checkout_sha, tested_head=context.head_sha, token=token)
        source, _ = _source(
            context, material, material_head, policy, token, target_tree_digest=tree
        )
        value = _document(
            context,
            run,
            schema=PLAN_SCHEMA,
            material=material,
            material_head=material_head,
            policy=policy,
            checkout_sha=checkout_sha,
            tree_digest=tree,
            mode="reused",
            reason="verified_direct_source",
            source=source,
        )
        _refresh(context, run, token, source=source["run"])
    except Ineligible as exc:
        # Missing, expired or insufficient proof selects native execution.
        # Published assertions already count as claims: contradictions and
        # identity races propagate even before a reused plan is emitted.
        ordinary["reason"] = str(exc)
        value = _finish_document(ordinary)
        _refresh(context, run, token)
    return value


def _assert_plan(
    *,
    repo_root: Path,
    context: Context,
    run: dict[str, Any],
    token: str,
    checkout_sha: str,
    plan: dict[str, Any],
) -> tuple[evidence.MaterialManifest, str, BasePolicy, str, dict[str, Any], dict[str, bytes]]:
    _validate_document(plan, schema=PLAN_SCHEMA)
    if plan["mode"] != "reused":
        raise ReuseError("projection requires an asserted reused plan")
    if context.is_fork:
        raise ReuseError("fork PR cannot assert test reuse")
    _trusted_base(repo_root, context)
    try:
        material, material_head = _material(repo_root, context, successor=True)
        policy = _policy(repo_root, context, material)
        tree = _commit_tree(context, checkout_sha, tested_head=context.head_sha, token=token)
        _binding(
            plan,
            context,
            run,
            material,
            material_head,
            policy,
            checkout_sha=checkout_sha,
            tree_digest=tree,
        )
        source, contents = _source(
            context,
            material,
            material_head,
            policy,
            token,
            target_tree_digest=tree,
            asserted=plan["source"],
        )
        if plan["upstream_assets"] != [source] or plan["reason"] != "verified_direct_source":
            raise ReuseError("asserted plan upstream binding differs")
        _refresh(context, run, token, source=source["run"])
        return material, material_head, policy, tree, source, contents
    except (Ineligible, identity.CommitIdentityError, evidence.ReviewEvidenceError) as exc:
        raise ReuseError("asserted reuse is no longer independently admissible") from exc


def project_reuse(
    *,
    repo_root: Path,
    context: Context,
    run: dict[str, Any],
    token: str,
    checkout_sha: str,
    plan: dict[str, Any],
    job_id: str,
    matrix_value: str | None,
    coverage_output: Path | None,
) -> str:
    if plan.get("mode") == "executed":
        _validate_document(plan, schema=PLAN_SCHEMA)
        if plan["source"] is not None:
            raise ReuseError("ordinary plan asserts a reuse source")
        if context.is_fork:
            _trusted_base(repo_root, context)
            _fork_plan_binding(plan, context, run, checkout_sha)
            _refresh(context, run, token)
        return "executed"
    _, _, policy, _, _, contents = _assert_plan(
        repo_root=repo_root,
        context=context,
        run=run,
        token=token,
        checkout_sha=checkout_sha,
        plan=plan,
    )
    cells = [
        cell for cell in policy.cells if cell.job_id == job_id and cell.matrix_value == matrix_value
    ]
    if len(cells) != 1:
        raise ReuseError("projection cell is outside the independently derived universe")
    cell = cells[0]
    if cell.coverage_name is not None:
        if coverage_output is None:
            raise ReuseError("coverage projection requires a safe output path")
        _safe_write(coverage_output, contents[cell.check_name])
    elif coverage_output is not None:
        raise ReuseError("non-coverage projection cannot author coverage")
    return "reused"


def collect_execution(
    *,
    repo_root: Path,
    context: Context,
    run: dict[str, Any],
    token: str,
    checkout_sha: str,
    plan: dict[str, Any],
) -> dict[str, Any] | None:
    _validate_document(plan, schema=PLAN_SCHEMA)
    _trusted_base(repo_root, context)
    if context.is_fork:
        _fork_plan_binding(plan, context, run, checkout_sha)
        _fork_no_reuse(context, run, token)
        _refresh(context, run, token)
        return None
    asserted = plan.get("mode") == "reused"
    source = None
    source_contents: Mapping[str, bytes] = {}
    if asserted:
        material, material_head, policy, tree, source, source_contents = _assert_plan(
            repo_root=repo_root,
            context=context,
            run=run,
            token=token,
            checkout_sha=checkout_sha,
            plan=plan,
        )
    else:
        try:
            material, material_head = _material(repo_root, context, successor=False)
            policy = _policy(repo_root, context, material)
        except ReuseError:
            return None
        _validate_document(plan, schema=PLAN_SCHEMA)
        if (
            plan["source"] is not None
            or plan["run"] != _run_tuple(run)
            or plan["repository"] != context.repository
            or plan["pr_number"] != context.pr_number
            or plan["base_sha"] != context.base_sha
            or plan["head_sha"] != context.head_sha
        ):
            raise ReuseError("ordinary plan contradicts current run binding")
        tree = _commit_tree(context, checkout_sha, tested_head=context.head_sha, token=token)
    selected = _selected_jobs(context, run, policy, token, direct_only=not asserted)
    rows, _ = _coverage_rows(context, run, selected, token)
    _reused_coverage_matches(rows, source_contents)
    _refresh_artifacts(context, run, selected, rows, token)
    modes = {row["mode"] for row in rows}
    if "reused" in modes and source is None:
        raise ReuseError("aggregate contains reuse without direct source")
    mode = "reused" if "reused" in modes else "executed"
    if asserted and mode != "reused":
        raise ReuseError("reused plan produced only direct native markers")
    manifest = _document(
        context,
        run,
        schema=MANIFEST_SCHEMA,
        material=material,
        material_head=material_head,
        policy=policy,
        checkout_sha=checkout_sha,
        tree_digest=tree,
        mode=mode,
        reason="verified_reuse" if mode == "reused" else "native_execution",
        source=source,
    )
    manifest["jobs"] = rows
    manifest["upstream_assets"] = [
        {"native_job_id": row["native_job_id"], "coverage": row["coverage"]} for row in rows
    ] + ([source] if source is not None else [])
    _refresh(context, run, token, source=source["run"] if source is not None else None)
    return _finish_document(manifest)


def verify_current_reuse(
    *,
    repo_root: Path,
    repository: str,
    pr_number: int,
    token: str,
    expected_head_sha: str | None = None,
    expected_base_sha: str | None = None,
) -> None:
    """Refresh native current and direct-source proof from exact BASE code.

    Existing ordinary required-check consumers remain authoritative. This
    additional proof is mandatory only when a native job asserts test reuse.
    """
    context = _context(
        repository,
        pr_number,
        token,
        expected_head=expected_head_sha,
        expected_base=expected_base_sha,
    )
    _trusted_base(repo_root, context)
    if context.is_fork:
        run = _latest_run(context, context.head_sha, token)
        if run is not None:
            _fork_no_reuse(context, run, token)
            _refresh(context, run, token)
        return
    live_material = evidence.compute_material_manifest(
        repo_root,
        base_ref_oid=context.base_sha,
        head_ref_oid=context.head_sha,
        pr_number=context.pr_number,
    )
    run = _latest_run(context, context.head_sha, token)
    if run is None:
        return
    jobs = _jobs(context, run, token)
    claimed = any(_steps(job).get(REUSED_MARKER, {}).get("conclusion") == "success" for job in jobs)
    try:
        policy = _policy(repo_root, context, live_material)
    except ReuseError as exc:
        if claimed:
            raise ReuseError("ineligible whole material asserts native test reuse") from exc
        # Ordinary ineligible runs do not publish substitution evidence.
        return
    artifact_name = f"ci-test-execution-{run['id']}-{run['run_attempt']}"
    artifacts = _pages(
        context.repository, f"actions/runs/{run['id']}/artifacts", "artifacts", token
    )
    has_aggregate = any(artifact.get("name") == artifact_name for artifact in artifacts)
    if not claimed and not has_aggregate:
        return
    writer = _writer(context, run, token)
    aggregate_ref, raw = _artifact(
        context,
        run,
        name=artifact_name,
        producer=writer,
        upload_step=WRITER_UPLOAD,
        member="ci-test-execution.json",
        token=token,
    )
    manifest = _validate_document(_json(raw), schema=MANIFEST_SCHEMA)
    if not claimed:
        if manifest["mode"] != "executed" or manifest["source"] is not None:
            raise ReuseError("aggregate claims reuse without native reused markers")
        return
    material, material_head = _material(repo_root, context, successor=True)
    checkout = _sha(manifest["checkout_sha"], "current event checkout")
    tree = _commit_tree(context, checkout, tested_head=context.head_sha, token=token)
    _binding(
        manifest,
        context,
        run,
        material,
        material_head,
        policy,
        checkout_sha=checkout,
        tree_digest=tree,
    )
    if (
        manifest["mode"] != "reused"
        or manifest["source"] is None
        or manifest["reason"] != "verified_reuse"
    ):
        raise ReuseError("native reuse is missing its direct aggregate proof")
    source, source_contents = _source(
        context,
        material,
        material_head,
        policy,
        token,
        target_tree_digest=tree,
        asserted=manifest["source"],
    )
    selected = _selected_jobs(context, run, policy, token, direct_only=False)
    if not isinstance(manifest["jobs"], list):
        raise ReuseError("current aggregate jobs are malformed")
    rows, _ = _coverage_rows(context, run, selected, token, asserted=manifest["jobs"])
    _reused_coverage_matches(rows, source_contents)
    _refresh_artifacts(context, run, selected, rows, token, aggregate=aggregate_ref, writer=writer)
    upstreams = [
        {"native_job_id": row["native_job_id"], "coverage": row["coverage"]} for row in rows
    ] + [source]
    if manifest["upstream_assets"] != upstreams:
        raise ReuseError("current aggregate upstream bindings differ")
    _refresh(context, run, token, source=source["run"])


def _fork_plan_binding(
    plan: dict[str, Any], context: Context, run: dict[str, Any], checkout_sha: str
) -> None:
    expected = _document(
        context,
        run,
        schema=PLAN_SCHEMA,
        checkout_sha=_sha(checkout_sha, "event checkout"),
        reason="fork_pr_ordinary_only",
    )
    if plan != expected:
        raise ReuseError("fork PR requires the authenticated ordinary-only plan")


def _fork_no_reuse(context: Context, run: dict[str, Any], token: str) -> None:
    for job in _jobs(context, run, token):
        steps = _steps(job)
        for name in (VERIFY_STEP, REUSED_MARKER):
            step = steps.get(name)
            if step is not None and (
                step.get("status") == "in_progress"
                or step.get("conclusion") not in {None, "skipped"}
            ):
                raise ReuseError("fork PR has a native test reuse claim")
    artifacts = _pages(
        context.repository, f"actions/runs/{run['id']}/artifacts", "artifacts", token
    )
    if any(
        row.get("name") == f"ci-test-execution-{run['id']}-{run['run_attempt']}"
        for row in artifacts
    ):
        raise ReuseError("fork PR cannot publish substitution evidence")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "project", "collect", "verify-current"))
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--event-path",
        type=Path,
        default=(
            Path(os.environ["GITHUB_EVENT_PATH"]) if os.environ.get("GITHUB_EVENT_PATH") else None
        ),
    )
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--job-id", choices=tuple(CRITICAL_STEPS))
    parser.add_argument("--matrix-value")
    parser.add_argument("--coverage-output", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if args.command == "verify-current":
            if not args.repo or args.pr_number is None:
                raise ReuseError("verify-current requires repository and PR")
            verify_current_reuse(
                repo_root=args.repo_root,
                repository=args.repo,
                pr_number=args.pr_number,
                token=token,
            )
            print('{"verified":true}')
            return 0
        if args.event_path is None:
            raise ReuseError("CI command requires an immutable PR event")
        repository, number, head, base = _event(args.event_path, args.repo, args.pr_number)
        context = _context(repository, number, token, expected_head=head, expected_base=base)
        run = _current_run(context, token)
        checkout = _sha(os.environ.get("GITHUB_SHA"), "event GITHUB_SHA")
        if args.command == "plan":
            value = plan_reuse(
                repo_root=args.repo_root,
                context=context,
                run=run,
                token=token,
                checkout_sha=checkout,
            )
            compact = _canonical(value).decode("utf-8")
            _output(args.github_output, {"mode": value["mode"], "plan": compact})
            print(compact)
        else:
            raw_plan = os.environ.get("CI_REUSE_PLAN_JSON")
            if not isinstance(raw_plan, str):
                raise ReuseError("CI command requires a declared current plan")
            plan = _object(_json(raw_plan.encode("utf-8")), "current plan")
            if args.command == "project":
                if args.job_id is None:
                    raise ReuseError("project requires a job cell")
                mode = project_reuse(
                    repo_root=args.repo_root,
                    context=context,
                    run=run,
                    token=token,
                    checkout_sha=checkout,
                    plan=plan,
                    job_id=args.job_id,
                    matrix_value=args.matrix_value,
                    coverage_output=args.coverage_output,
                )
                _output(args.github_output, {"mode": mode})
                print(
                    _canonical(
                        {"mode": mode, "source": plan.get("source") if mode == "reused" else None}
                    ).decode("utf-8")
                )
            else:
                if args.output is None:
                    raise ReuseError("collect requires an output path")
                manifest = collect_execution(
                    repo_root=args.repo_root,
                    context=context,
                    run=run,
                    token=token,
                    checkout_sha=checkout,
                    plan=plan,
                )
                if manifest is not None:
                    _safe_write(args.output, _canonical(manifest))
                _output(
                    args.github_output, {"publish": "true" if manifest is not None else "false"}
                )
                print(_canonical({"publish": manifest is not None}).decode("utf-8"))
        return 0
    except (ReuseError, identity.CommitIdentityError, evidence.ReviewEvidenceError, OSError) as exc:
        # All messages are fixed diagnostics. Never emit API error bodies,
        # redirect query strings, raw manifests, event values or credentials.
        message = (
            str(exc)
            if isinstance(exc, ReuseError)
            else "authenticated CI evidence could not be verified"
        )
        print(f"CI test reuse verification failed: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

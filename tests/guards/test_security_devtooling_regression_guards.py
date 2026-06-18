"""Regression guards for security/dev-tooling hotfix classes.

These tests protect the narrow issue classes closed by PRs #1664-#1667:

- Makefile compose project-name shell safety
- optional RAG/vector dependency-profile security coverage
- eval sidecar symlink-safe writes
- eval validity strict validation and defensive copies
- new docs/review local absolute path leakage
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import yaml

from scripts.ci import ci_risk_profile
from scripts.ci import run_safety_audit
from scripts.evals import eval_validity_contract
from scripts.evals import judgment_validity

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
SECURITY_WORKFLOW = REPO_ROOT / ".github/workflows/security.yml"
PYTHON_DEPENDENCY_SUBMISSION = REPO_ROOT / ".github/workflows/python-dependency-submission.yml"
NPM_DEPENDENCY_SUBMISSION = REPO_ROOT / ".github/workflows/npm-dependency-submission.yml"
PIP_AUDIT_HELPER = REPO_ROOT / "scripts/ci_pip_audit.sh"
LOCAL_USERS_PATH_PATTERN = re.compile(r"/Users/(?!\.\.\.)([^/\s`]+)(?:/|$)")
DOCS_LEAKAGE_GUARD_BASE_ENV = "PULSEPLATE_DOCS_LEAKAGE_GUARD_BASE"
DOCS_LEAKAGE_GUARD_FETCH_DEPTH = "200"

SECURITY_DEPENDENCY_PROFILE_FILES: tuple[str, ...] = (
    "requirements-rag-vector.in",
    "requirements-rag-vector.txt",
    "requirements-rag-vector-cpu.in",
    "requirements-rag-vector-cpu.txt",
)
SECURITY_DEPENDENCY_LOCKFILES: tuple[str, ...] = tuple(
    name for name in SECURITY_DEPENDENCY_PROFILE_FILES if name.endswith(".txt")
)
PYTORCH_JIT_SAFETY_ID = "SFTY-20250331-30014"
PYTORCH_JIT_CVE_ID = "CVE-2025-3000"
PYTORCH_JIT_WAIVER_REMOVE_BY = "2026-07-17"
BANDIT_SUMMARY_HELPER = "python3 scripts/ci/summarize_bandit_report.py"
PRODUCTION_RUNTIME_INVARIANT_HELPER = (
    "python3 scripts/ci/check_production_runtime_invariants.py --synthetic-production"
)
CI_BANDIT_EXCLUDES = {
    "tests",
    "tests_strict",
    "htmlcov",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
}
SECURITY_BANDIT_EXCLUDES = {
    "tests",
    "test_cache",
    "cache",
    "frontend/build",
    "htmlcov",
    "releases",
    "data",
    "external",
    "node_modules",
    "dist",
    "build",
    ".venv",
}
FORBIDDEN_BANDIT_EXCLUDES = {
    "app",
    "app/",
    "app/**",
    "app/security",
    "app/security/",
    "app/security/**",
    "core",
    "core/",
    "core/**",
    "scripts",
    "scripts/",
    "scripts/**",
    "scripts/ci",
    "scripts/ci/",
    "scripts/ci/**",
    "legacy_app.py",
}


def _binary(name: str) -> str:
    binary = shutil.which(name)
    assert binary is not None, f"Required executable is unavailable on PATH: {name}"
    return binary


def _makefile_text() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


def _workflow(workflow_path: Path) -> dict[str, Any]:
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict), f"{workflow_path} must be a YAML mapping"
    return workflow


def _workflow_events(workflow_path: Path) -> dict[str, Any]:
    workflow = _workflow(workflow_path)
    events = workflow.get("on", workflow.get(True))
    assert isinstance(events, dict), "workflow events must be a mapping"
    return events


def _workflow_path_filters(
    workflow_path: Path = PYTHON_DEPENDENCY_SUBMISSION,
) -> dict[str, set[str]]:
    events = _workflow_events(workflow_path)
    filters: dict[str, set[str]] = {}
    for event in ("push", "pull_request"):
        event_block = events[event]
        assert isinstance(event_block, dict), f"{event} block must be a mapping"
        filters[event] = set(event_block["paths"])
    return filters


def _job_action_step(workflow: dict[str, Any], *, job_id: str, action_name: str) -> dict[str, Any]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict), "workflow jobs must be a mapping"
    job = jobs[job_id]
    assert isinstance(job, dict), f"{job_id} job must be a mapping"
    steps = job["steps"]
    assert isinstance(steps, list), f"{job_id} steps must be a list"
    for step in steps:
        if isinstance(step, dict) and step.get("uses") == action_name:
            return step
    raise AssertionError(f"missing {action_name} step in {job_id}")


def _job_named_step(workflow: dict[str, Any], *, job_id: str, step_name: str) -> dict[str, Any]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict), "workflow jobs must be a mapping"
    job = jobs[job_id]
    assert isinstance(job, dict), f"{job_id} job must be a mapping"
    steps = job["steps"]
    assert isinstance(steps, list), f"{job_id} steps must be a list"
    for step in steps:
        if isinstance(step, dict) and step.get("name") == step_name:
            return step
    raise AssertionError(f"missing {step_name} step in {job_id}")


def _csv_values(value: object) -> set[str]:
    assert isinstance(value, str), "expected comma-separated string"
    return {item.strip() for item in value.split(",") if item.strip()}


def _shell_assignment_values(script: str, variable_name: str) -> set[str]:
    match = re.search(rf'^\s*{re.escape(variable_name)}="([^"]*)"', script, flags=re.MULTILINE)
    assert match, f"missing shell assignment: {variable_name}"
    return _csv_values(match.group(1))


def _bandit_exclude_values(script: str) -> set[str]:
    match = re.search(r'--exclude\s+"([^"]+)"', script)
    assert match, "missing Bandit --exclude argument"
    return _csv_values(match.group(1))


def _function_source(module_path: Path, function_name: str) -> str:
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            assert node.end_lineno is not None
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])

    raise AssertionError(f"missing function: {function_name}")


def _git_ref_exists(ref: str) -> bool:
    result = subprocess.run(
        [_binary("git"), "rev-parse", "--verify", "--quiet", ref],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return result.returncode == 0


def _github_event_pull_request_base_sha() -> str:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        return ""
    path = Path(event_path)
    if not path.is_file():
        return ""
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return ""
    base = pull_request.get("base")
    if not isinstance(base, dict):
        return ""
    sha = base.get("sha")
    return sha if isinstance(sha, str) else ""


def _docs_diff_base_candidates() -> tuple[str, ...]:
    configured = os.environ.get(DOCS_LEAKAGE_GUARD_BASE_ENV, "").strip()
    github_base_ref = os.environ.get("GITHUB_BASE_REF", "").strip()
    return tuple(
        candidate
        for candidate in (
            configured,
            f"origin/{github_base_ref}" if github_base_ref else "",
            github_base_ref,
            _github_event_pull_request_base_sha(),
            "origin/main",
            "main",
            "HEAD^1",
            "HEAD~1",
        )
        if candidate
    )


def _changed_docs_diff() -> str:
    candidates = _docs_diff_base_candidates()
    attempted: list[str] = []
    for base_ref in candidates:
        attempted.append(base_ref)
        if _git_ref_exists(base_ref):
            result = _changed_docs_diff_from_base(base_ref)
            if result.returncode == 0:
                return result.stdout
        _fetch_base_ref_for_shallow_checkout(base_ref)
        if _git_ref_exists(base_ref):
            result = _changed_docs_diff_from_base(base_ref)
            if result.returncode == 0:
                return result.stdout

    attempted_refs = ", ".join(attempted) or "<none>"
    raise AssertionError(f"no usable git diff base for docs leakage guard: {attempted_refs}")


def _changed_docs_diff_from_base(base_ref: str) -> subprocess.CompletedProcess[str]:
    three_dot = _run_docs_diff(f"{base_ref}...HEAD")
    if three_dot.returncode == 0:
        return three_dot
    if _docs_diff_error_allows_two_dot_fallback(three_dot.stderr):
        return _run_docs_diff(f"{base_ref}..HEAD")
    return three_dot


def _docs_diff_error_allows_two_dot_fallback(stderr: str) -> bool:
    lower_stderr = stderr.casefold()
    return (
        "invalid symmetric difference expression" in lower_stderr or "no merge base" in lower_stderr
    )


def _run_docs_diff(revision_range: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_binary("git"), "diff", "--unified=0", revision_range, "--", "docs", "docs/review"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def _fetch_base_ref_for_shallow_checkout(base_ref: str) -> None:
    fetch_args: list[str]
    github_base_ref = os.environ.get("GITHUB_BASE_REF", "").strip()
    if base_ref.startswith("origin/"):
        branch = base_ref.removeprefix("origin/")
        fetch_args = [
            "fetch",
            "--no-tags",
            f"--depth={DOCS_LEAKAGE_GUARD_FETCH_DEPTH}",
            "origin",
            f"{branch}:refs/remotes/origin/{branch}",
        ]
    elif github_base_ref and base_ref == github_base_ref:
        fetch_args = [
            "fetch",
            "--no-tags",
            f"--depth={DOCS_LEAKAGE_GUARD_FETCH_DEPTH}",
            "origin",
            f"{github_base_ref}:refs/remotes/origin/{github_base_ref}",
        ]
    elif re.fullmatch(r"[0-9a-fA-F]{40}", base_ref):
        fetch_args = [
            "fetch",
            "--no-tags",
            f"--depth={DOCS_LEAKAGE_GUARD_FETCH_DEPTH}",
            "origin",
            base_ref,
        ]
    else:
        return
    subprocess.run(
        [_binary("git"), *fetch_args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def _make_print_compose_project_name(cwd: Path, env: dict[str, str]) -> str:
    probe_makefile = cwd / "probe.mk"
    (cwd / "Makefile").symlink_to(MAKEFILE)
    probe_makefile.write_text(
        "\n".join(
            [
                "include Makefile",
                "",
                ".PHONY: print-compose",
                "print-compose:",
                "\t@printf '%s\\n' \"$(COMPOSE_PROJECT_NAME)\"",
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            _binary("make"),
            "-s",
            "-f",
            str(probe_makefile),
            "-C",
            str(cwd),
            "print-compose",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def test_makefile_compose_project_name_uses_internal_pwd_not_curdir_interpolation() -> None:
    text = _makefile_text()

    assert "$(CURDIR)" not in "\n".join(
        line for line in text.splitlines() if "COMPOSE_PROJECT_NAME" in line
    )
    assert "COMPOSE_PROJECT_NAME_SUFFIX := $(strip $(shell pwd -P | cksum | cut -d' ' -f1))" in text
    assert "COMPOSE_PROJECT_NAME ?= pulseplate-$(COMPOSE_PROJECT_NAME_SUFFIX)" in text
    assert "ifeq ($(origin COMPOSE_PROJECT_NAME), undefined)" in text


def test_makefile_compose_project_name_does_not_execute_malicious_worktree_text(
    tmp_path: Path,
) -> None:
    malicious_dir = tmp_path / "wt;touch SHOULD_NOT_EXIST;$(touch SHOULD_NOT_EXIST_2)"
    malicious_dir.mkdir()
    marker = malicious_dir / "SHOULD_NOT_EXIST"
    marker_2 = malicious_dir / "SHOULD_NOT_EXIST_2"
    env = os.environ.copy()
    env.pop("COMPOSE_PROJECT_NAME", None)
    env.pop("COMPOSE_PROJECT_NAME_SUFFIX", None)

    project_name = _make_print_compose_project_name(malicious_dir, env)

    assert project_name.startswith("pulseplate-")
    assert project_name != "pulseplate"
    assert not marker.exists()
    assert not marker_2.exists()


def test_makefile_compose_project_name_override_is_preserved(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = "custom"
    env.pop("COMPOSE_PROJECT_NAME_SUFFIX", None)

    assert _make_print_compose_project_name(tmp_path, env) == "custom"


def test_optional_rag_vector_dependency_profiles_have_canonical_security_registry() -> None:
    discovered = {
        path.name
        for pattern in ("requirements-rag-vector*.in", "requirements-rag-vector*.txt")
        for path in REPO_ROOT.glob(pattern)
    }

    assert discovered == set(SECURITY_DEPENDENCY_PROFILE_FILES)


def test_dependency_profiles_are_covered_by_all_security_surfaces() -> None:
    safety_manifests = set(run_safety_audit.OPTIONAL_MANIFESTS)
    pip_audit_text = PIP_AUDIT_HELPER.read_text(encoding="utf-8")
    workflow_filters = _workflow_path_filters()
    risk_profile_files = set(ci_risk_profile.BACKEND_SHARED_EXACT)

    for lockfile in SECURITY_DEPENDENCY_LOCKFILES:
        assert lockfile in safety_manifests
        assert lockfile in pip_audit_text

    for profile_file in SECURITY_DEPENDENCY_PROFILE_FILES:
        assert profile_file in workflow_filters["push"]
        assert profile_file in workflow_filters["pull_request"]
        assert profile_file in risk_profile_files

        profile = ci_risk_profile.build_risk_profile([profile_file])
        assert profile.backend_shared is True
        assert profile.run_backend_blocking is True
        assert profile.run_security is True


def test_pytorch_jit_cve_waiver_evidence_is_scoped_and_current() -> None:
    safety_policy = yaml.safe_load((REPO_ROOT / "safety-policy.yaml").read_text(encoding="utf-8"))
    assert isinstance(safety_policy, dict)
    vulnerabilities = safety_policy["report"]["dependency-vulnerabilities"][
        "auto-ignore-in-report"
    ]["vulnerabilities"]
    torch_waiver = vulnerabilities[PYTORCH_JIT_SAFETY_ID]

    assert torch_waiver["expires"] == PYTORCH_JIT_WAIVER_REMOVE_BY

    advisory_text = (REPO_ROOT / "docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md").read_text(
        encoding="utf-8"
    )
    backlog_text = (REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md").read_text(encoding="utf-8")

    for evidence_text in (advisory_text, backlog_text):
        assert PYTORCH_JIT_SAFETY_ID in evidence_text
        assert PYTORCH_JIT_CVE_ID in evidence_text
        assert PYTORCH_JIT_WAIVER_REMOVE_BY in evidence_text
        assert "optional RAG/vector" in evidence_text

    for stable_marker in (
        "requirements-ci-lite.txt",
        "requirements-lock.txt",
        "no direct `torch` pin",
        "Patched versions",
        "none",
    ):
        assert stable_marker in advisory_text


def test_ci_security_job_uses_shared_bandit_summary_helper() -> None:
    workflow = _workflow(CI_WORKFLOW)
    scan_step = _job_named_step(
        workflow,
        job_id="security",
        step_name="Security scan with Bandit",
    )
    gate_step = _job_named_step(
        workflow,
        job_id="security",
        step_name="Enforce Bandit HIGH severity gate",
    )
    scan_script = scan_step["run"]
    gate_script = gate_step["run"]

    assert "bandit-report.json" in scan_script
    assert BANDIT_SUMMARY_HELPER in gate_script
    assert "--report bandit-report.json" in gate_script
    assert "--fail-on-high" in gate_script
    assert "--github-annotations" in gate_script
    assert "json.loads" not in gate_script
    assert "jq " not in gate_script
    assert "continue-on-error" not in gate_script


def test_security_scan_workflow_uses_shared_bandit_summary_helper() -> None:
    workflow = _workflow(SECURITY_WORKFLOW)
    bandit_step = _job_named_step(
        workflow,
        job_id="bandit",
        step_name="Run Bandit (security lint)",
    )
    bandit_script = bandit_step["run"]

    assert "bandit-report.json" in bandit_script
    assert BANDIT_SUMMARY_HELPER in bandit_script
    assert "--report bandit-report.json" in bandit_script
    assert "--fail-on-high" in bandit_script
    assert "--github-annotations" in bandit_script
    assert 'select(.issue_severity == "HIGH")' not in bandit_script
    assert "|| true" not in bandit_script
    assert "continue-on-error" not in bandit_script


def test_security_workflows_run_production_runtime_invariant_guard() -> None:
    for workflow_path, job_id in (
        (CI_WORKFLOW, "security"),
        (SECURITY_WORKFLOW, "bandit"),
    ):
        workflow = _workflow(workflow_path)
        step = _job_named_step(
            workflow,
            job_id=job_id,
            step_name="Production runtime invariant guard",
        )
        script = step["run"]

        assert PRODUCTION_RUNTIME_INVARIANT_HELPER in script
        assert "set -euo pipefail" in script
        assert "|| true" not in script
        assert "continue-on-error" not in step
        assert "continue-on-error" not in script


def test_ci_route_contract_suite_covers_production_runtime_invariants() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "route_contract_safety)" in workflow_text
    assert "tests/test_production_runtime_invariants.py" in workflow_text


def test_bandit_excludes_do_not_widen_in_ci_workflow() -> None:
    workflow = _workflow(CI_WORKFLOW)
    scan_step = _job_named_step(
        workflow,
        job_id="security",
        step_name="Security scan with Bandit",
    )
    excludes = _shell_assignment_values(scan_step["run"], "EXCLUDES")

    assert excludes == CI_BANDIT_EXCLUDES
    assert excludes.isdisjoint(FORBIDDEN_BANDIT_EXCLUDES)


def test_bandit_excludes_do_not_widen_in_security_workflow() -> None:
    workflow = _workflow(SECURITY_WORKFLOW)
    bandit_step = _job_named_step(
        workflow,
        job_id="bandit",
        step_name="Run Bandit (security lint)",
    )
    excludes = _bandit_exclude_values(bandit_step["run"])

    assert excludes == SECURITY_BANDIT_EXCLUDES
    assert excludes.isdisjoint(FORBIDDEN_BANDIT_EXCLUDES)


def test_npm_dependency_submission_covers_root_and_frontend_lockfiles() -> None:
    workflow = _workflow(NPM_DEPENDENCY_SUBMISSION)
    events = _workflow_events(NPM_DEPENDENCY_SUBMISSION)

    assert "pull_request_target" not in events
    assert workflow["permissions"] == {"contents": "write"}

    for event in ("push", "pull_request"):
        event_block = events[event]
        assert isinstance(event_block, dict), f"{event} block must be a mapping"
        paths = set(event_block["paths"])
        assert {
            "package.json",
            "package-lock.json",
            "frontend/package.json",
            "frontend/package-lock.json",
            ".github/workflows/npm-dependency-submission.yml",
        }.issubset(paths)

    action = "advanced-security/component-detection-dependency-submission-action@" + "".join(
        (
            "b876b8cc",
            "341a5397",
            "0394b33e",
            "a0ca4e86",
            "c25542de",
        )
    )
    checkout_action = "actions/checkout@" + "".join(
        (
            "de0fac2e",
            "4500dabe",
            "0009e672",
            "14ff5f54",
            "47ce83dd",
        )
    )
    root_step = _job_action_step(workflow, job_id="dependency-submission", action_name=action)
    frontend_step = _job_action_step(
        workflow,
        job_id="frontend-dependency-submission",
        action_name=action,
    )
    root_checkout = _job_action_step(
        workflow,
        job_id="dependency-submission",
        action_name=checkout_action,
    )
    frontend_checkout = _job_action_step(
        workflow,
        job_id="frontend-dependency-submission",
        action_name=checkout_action,
    )
    frontend_prepare = _job_named_step(
        workflow,
        job_id="frontend-dependency-submission",
        step_name="Prepare frontend npm dependency graph root",
    )

    root_with = root_step["with"]
    frontend_with = frontend_step["with"]
    assert isinstance(root_with, dict)
    assert isinstance(frontend_with, dict)

    jobs = workflow["jobs"]
    pr_validation_job = jobs["dependency-submission-pr-validation"]
    assert pr_validation_job["if"] == "github.event_name == 'pull_request'"
    assert pr_validation_job["permissions"] == {"contents": "read"}
    assert pr_validation_job["timeout-minutes"] == (
        "${{ fromJSON(vars.WORKFLOW_TIMEOUT_MINUTES || '10') }}"
    )
    assert "dependency submission API" in pr_validation_job["steps"][0]["run"]
    assert jobs["dependency-submission"]["if"] == "github.event_name != 'pull_request'"
    assert jobs["frontend-dependency-submission"]["if"] == ("github.event_name != 'pull_request'")
    assert jobs["dependency-submission"]["timeout-minutes"] == (
        "${{ fromJSON(vars.WORKFLOW_TIMEOUT_MINUTES || '10') }}"
    )
    assert jobs["frontend-dependency-submission"]["timeout-minutes"] == (
        "${{ fromJSON(vars.WORKFLOW_TIMEOUT_MINUTES || '10') }}"
    )
    assert root_checkout["with"] == {"persist-credentials": False}
    assert frontend_checkout["with"] == {"persist-credentials": False}
    assert root_with["correlator"] == "npm-dependency-submission-root"
    assert frontend_with["correlator"] == "npm-dependency-submission-frontend"
    assert root_with["correlator"] != frontend_with["correlator"]
    assert root_with["detectorsCategories"] == "Npm"
    assert frontend_with["detectorsCategories"] == "Npm"
    assert root_with["detectorArgs"] == "NpmLockfile3=EnableIfDefaultOff"
    assert frontend_with["detectorArgs"] == "NpmLockfile3=EnableIfDefaultOff"

    root_exclusions = _csv_values(root_with["directoryExclusionList"])
    frontend_exclusions = _csv_values(frontend_with["directoryExclusionList"])
    assert root_exclusions == {"frontend", "node_modules", "worktrees", ".venv"}
    assert root_with.get("filePath") in {None, "", "."}
    assert frontend_prepare["shell"] == "bash"
    prepare_script = str(frontend_prepare["run"])
    assert "pulseplate-frontend-dependency-root" in prepare_script
    assert "mkdir -p" in prepare_script
    assert "frontend/package.json frontend/package-lock.json" in prepare_script
    assert frontend_with["filePath"] == ("${{ runner.temp }}/pulseplate-frontend-dependency-root")
    assert frontend_with["filePath"] != "frontend"
    assert "frontend" not in frontend_exclusions
    assert {"node_modules", "worktrees", ".venv"}.issubset(frontend_exclusions)


def test_judgment_validity_sidecars_only_use_symlink_safe_writer() -> None:
    module_path = REPO_ROOT / "scripts/evals/judgment_validity.py"
    writer_source = _function_source(module_path, "write_judgment_validity_sidecar")
    safe_writer_source = _function_source(module_path, "_safe_write_text")

    assert 'getattr(os, "O_NOFOLLOW", None)' in safe_writer_source
    assert 'raise OSError("Symlink-safe writes are not supported on this platform")' in (
        safe_writer_source
    )
    assert "os.open(path, flags, 0o600)" in safe_writer_source
    assert "_safe_write_text(items_path, items_content)" in writer_source
    assert "_safe_write_text(report_path, report_content)" in writer_source
    assert ".open(" not in writer_source
    assert ".write_text(" not in writer_source


def test_eval_validity_contract_rejects_coercive_validator_patterns() -> None:
    source = (REPO_ROOT / "scripts/evals/eval_validity_contract.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    validator_names = {"validate_eval_variant_record", "validate_eval_outcome_record"}
    coercive_calls = {"str", "list", "dict"}
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in validator_names:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in coercive_calls:
                    violations.append(f"{node.name}:{child.func.id}:line {child.lineno}")

    assert violations == []


def test_eval_validity_contract_requires_defensive_copies_and_value_error() -> None:
    tags = ["rag"]
    payload: dict[str, Any] = {"query": "test"}
    variant = eval_validity_contract.validate_eval_variant_record(
        {
            "canonical_id": "item_001",
            "variant_id": "item_001_canonical",
            "variant_family": "canonical",
            "transform_type": "none",
            "expected_relation": "same_decision",
            "slice_tags": tags,
            "input_payload": payload,
        }
    )
    outcome = eval_validity_contract.validate_eval_outcome_record(
        {
            "canonical_id": "item_001",
            "variant_id": "item_001_canonical",
            "variant_family": "canonical",
            "transform_type": "none",
            "passed": True,
            "score": 1.0,
            "decision": "pass",
            "slice_tags": tags,
        }
    )

    tags.append("mutated")
    payload["query"] = "changed"

    assert variant["slice_tags"] == ["rag"]
    assert variant["input_payload"] == {"query": "test"}
    assert outcome["slice_tags"] == ["rag"]

    for validator, raw in (
        (
            eval_validity_contract.validate_eval_variant_record,
            {
                "canonical_id": "item_001",
                "variant_id": "item_001_canonical",
                "variant_family": "canonical",
                "transform_type": "none",
                "expected_relation": "same_decision",
                "slice_tags": "rag",
                "input_payload": {"query": "test"},
            },
        ),
        (
            eval_validity_contract.validate_eval_outcome_record,
            {
                "canonical_id": "item_001",
                "variant_id": "item_001_canonical",
                "variant_family": "canonical",
                "transform_type": "none",
                "passed": True,
                "score": 1.0,
                "decision": "pass",
                "slice_tags": "rag",
            },
        ),
    ):
        try:
            validator(raw)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed slice_tags must raise ValueError")


def test_changed_docs_do_not_add_local_users_absolute_paths() -> None:
    leaked_lines = [
        line
        for line in _changed_docs_diff().splitlines()
        if line.startswith("+")
        and not line.startswith("+++")
        and LOCAL_USERS_PATH_PATTERN.search(line)
    ]

    assert leaked_lines == []


def test_docs_diff_falls_back_when_shallow_checkout_lacks_merge_base() -> None:
    assert _docs_diff_error_allows_two_dot_fallback("fatal: origin/main...HEAD: no merge base")
    assert _docs_diff_error_allows_two_dot_fallback(
        "fatal: Invalid symmetric difference expression origin/main...HEAD"
    )
    assert not _docs_diff_error_allows_two_dot_fallback("fatal: not a git repository")


def test_judgment_validity_module_exports_expected_sidecar_filenames() -> None:
    assert judgment_validity.JUDGMENT_VALIDITY_ITEMS_FILENAME == "judgment_validity_items.jsonl"
    assert judgment_validity.JUDGMENT_VALIDITY_REPORT_FILENAME == "judgment_validity_report.json"

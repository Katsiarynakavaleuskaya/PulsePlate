"""Regression guards for CI workflow diff-routing contracts."""

from __future__ import annotations

from collections.abc import Iterator
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import cast

import pytest
import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from scripts.ci import ci_risk_profile
from scripts.orchestration.creative_code_patch_workspace import (
    git_env_without_parent_state,
    safe_git_config_args,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIONLINT_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "actionlint.yml"
ACTIONLINT_CONFIG_PATH = REPO_ROOT / ".github" / "actionlint.yaml"
BUILD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "build.yml"
CD_TEST_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd-test.yml"
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CODECOV_UPLOAD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codecov-upload.yml"
CODEQL_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codeql.yml"
FRONTEND_CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "frontend-ci.yml"
FRONTEND_PACKAGE_JSON_PATH = REPO_ROOT / "frontend" / "package.json"
GREENLIGHT_IOS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "greenlight-ios.yml"
IOS_APPSTORE_ASSETS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ios-appstore-assets.yml"
NIGHTLY_FULL_TESTS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "nightly-tests.yml"
NIGHTLY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "nightly.yml"
PRE_COMMIT_CONFIG_PATH = REPO_ROOT / ".pre-commit-config.yaml"
PR_AUTOMATION_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pr-automation.yml"
SECURITY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "security.yml"
TRIVY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "trivy.yml"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
IOS_TEST_TARGETS_PATH = REPO_ROOT / "scripts" / "ios_test_targets.sh"
IOS_SWIFT_SYNTAX_PATH = REPO_ROOT / "scripts" / "ci" / "check_ios_swift_syntax.sh"
MAKEFILE_PATH = REPO_ROOT / "Makefile"
RUNBOOK_PATH = REPO_ROOT / "RUNBOOK_AGENT.md"
ORCHESTRATION_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "orchestration" / "PR_ORCHESTRATION_CONTRACT_MATRIX.md"
)
CHECKOUT_V7_SHA = "".join(
    (
        "3d3c",
        "42e5",
        "aac5",
        "ba80",
        "5825",
        "da76",
        "410c",
        "1812",
        "73ba",
        "90b1",
    )
)
SETUP_NODE_NODE24_SHA = "".join(
    (
        "53b8",
        "3947",
        "a5a9",
        "8c8d",
        "1131",
        "30e5",
        "6537",
        "7fae",
        "1a50",
        "d02f",
    )
)
PATHS_FILTER_NODE24_SHA = "".join(
    (
        "fbd0",
        "ab8f",
        "3e69",
        "293a",
        "f611",
        "ebae",
        "e636",
        "3fc2",
        "5e6d",
        "187d",
    )
)
DOWNLOAD_ARTIFACT_NODE24_SHA = "".join(
    (
        "3e5f",
        "45b2",
        "cfb9",
        "1720",
        "54b4",
        "087a",
        "40e8",
        "e0b5",
        "a546",
        "1e7c",
    )
)
GITHUB_SCRIPT_NODE24_SHA = "".join(
    (
        "3a28",
        "44b7",
        "e9c4",
        "22d3",
        "c10d",
        "287c",
        "8955",
        "73f7",
        "108d",
        "a1b3",
    )
)
CODECOV_ACTION_NODE24_SHA = "".join(
    (
        "57e3",
        "a136",
        "b779",
        "b570",
        "ffcd",
        "bf80",
        "b3bd",
        "c90e",
        "7fab",
        "3de2",
    )
)
DOCKER_SETUP_BUILDX_NODE24_SHA = "".join(
    (
        "d7f5",
        "e7f5",
        "09e4",
        "5cec",
        "5c76",
        "c4d5",
        "afdd",
        "7de9",
        "3d0b",
        "3df5",
    )
)
DOCKER_LOGIN_NODE24_SHA = "".join(
    (
        "6500",
        "06c6",
        "eb7d",
        "ba73",
        "a995",
        "cc03",
        "b0b2",
        "d7f5",
        "ca91",
        "5bee",
    )
)
DOCKER_METADATA_NODE24_SHA = "".join(
    (
        "80c7",
        "e94d",
        "d9b9",
        "319b",
        "d5eb",
        "7a0e",
        "0fe9",
        "291e",
        "23a2",
        "a2e9",
    )
)
TRIVY_ACTION_NODE24_CACHE_SHA = "".join(
    (
        "ed14",
        "2fd0",
        "673e",
        "97e2",
        "3eac",
        "5462",
        "0cfb",
        "913e",
        "5ce3",
        "6c25",
    )
)
TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW = {
    BUILD_WORKFLOW_PATH: "v0.74.0",
    CD_WORKFLOW_PATH: "v0.74.0",
    TRIVY_WORKFLOW_PATH: "v0.74.0",
}
CODEQL_ACTION_V4_37_1_SHA = "".join(
    (
        "7188",
        "fc36",
        "3630",
        "916d",
        "eb70",
        "2c7f",
        "dcf4",
        "e481",
        "b751",
        "f97a",
    )
)
SETUP_GO_NODE24_SHA = "".join(
    (
        "b7ad",
        "1dad",
        "31e0",
        "6c59",
        "25ef",
        "5d2f",
        "c7ad",
        "053e",
        "f454",
        "303e",
    )
)
UPLOAD_ARTIFACT_NODE24_SHA = "".join(
    (
        "043f",
        "b46d",
        "1a93",
        "c77a",
        "ae65",
        "6e7c",
        "1c64",
        "a875",
        "d1fc",
        "6a0a",
    )
)
SBOM_ACTION_NODE24_SHA = "".join(
    (
        "e22c",
        "3899",
        "0414",
        "9dbc",
        "22b5",
        "8101",
        "8060",
        "40fa",
        "8d37",
        "a610",
    )
)
PYTHON_TEST_JOB_NAMES = ("test-pr", "test-feature", "test-main")
OLD_CHECKOUT_NODE20_SHA = "".join(
    (
        "08eb",
        "a0b2",
        "7e82",
        "0071",
        "cde6",
        "df94",
        "9e0b",
        "eb9b",
        "a490",
        "6955",
    )
)
OLD_CHECKOUT_V6_NODE20_SHA = "".join(
    (
        "8e8c",
        "483d",
        "b84b",
        "4bee",
        "98b6",
        "0c05",
        "9352",
        "1ed3",
        "4d99",
        "90e8",
    )
)
OLD_DOWNLOAD_ARTIFACT_SHA = "".join(
    (
        "fa0a",
        "91b8",
        "5d4f",
        "404e",
        "444e",
        "00e0",
        "0597",
        "1372",
        "dc80",
        "1d16",
    )
)
OLD_GITHUB_SCRIPT_SHA = "".join(
    (
        "f28e",
        "40c7",
        "f34b",
        "de8b",
        "3046",
        "d885",
        "e986",
        "cb62",
        "90c5",
        "673b",
    )
)
OLD_CODECOV_ACTION_SHA = "".join(
    (
        "af09",
        "b5e3",
        "94c9",
        "3991",
        "b95a",
        "5e76",
        "46ae",
        "b90c",
        "1917",
        "f78f",
    )
)
OLD_DOCKER_SETUP_BUILDX_SHA = "".join(
    (
        "e468",
        "171a",
        "9de2",
        "16ec",
        "0895",
        "6ac3",
        "ada2",
        "f079",
        "1b6b",
        "d435",
    )
)
OLD_DOCKER_LOGIN_SHA = "".join(
    (
        "5e57",
        "cd11",
        "8135",
        "c172",
        "c367",
        "2efd",
        "75eb",
        "4636",
        "0885",
        "c0ef",
    )
)
OLD_DOCKER_METADATA_SHA = "".join(
    (
        "c1e5",
        "1972",
        "afc2",
        "121e",
        "065a",
        "ed6d",
        "45c6",
        "5596",
        "fe44",
        "5f3f",
    )
)
OLD_TRIVY_ACTION_SHA = "".join(
    (
        "57a9",
        "7c7e",
        "7821",
        "a577",
        "6ceb",
        "c9bb",
        "87c9",
        "84fa",
        "69cb",
        "a8f1",
    )
)
OLD_TRIVY_INTERNAL_CACHE_NODE20_SHA = "".join(
    (
        "0400",
        "d5f6",
        "44dc",
        "7451",
        "3175",
        "e3cd",
        "8d07",
        "132d",
        "d486",
        "0809",
    )
)
OLD_SETUP_GO_SHA = "".join(
    (
        "40f1",
        "582b",
        "2485",
        "089d",
        "de7a",
        "bd97",
        "c152",
        "9aa7",
        "68e1",
        "baff",
    )
)
OLD_UPLOAD_ARTIFACT_SHA = "".join(
    (
        "ea16",
        "5f8d",
        "65b6",
        "e75b",
        "5404",
        "49e9",
        "2b48",
        "86f4",
        "3607",
        "fa02",
    )
)
OLD_UPLOAD_ARTIFACT_V7_SHA = "".join(
    (
        "bbbc",
        "a2dd",
        "aa5d",
        "8fea",
        "a63e",
        "36b7",
        "6fda",
        "ad77",
        "386f",
        "024f",
    )
)
OLD_SBOM_ACTION_SHA = "".join(
    (
        "da16",
        "7eac",
        "915b",
        "4e86",
        "f08b",
        "264d",
        "bdbc",
        "867b",
        "61be",
        "6f0c",
    )
)
GITHUB_SCRIPT_V9_TAG_OBJECT_SHA = "".join(
    (
        "d746",
        "ffe3",
        "5508",
        "b191",
        "7358",
        "783b",
        "479e",
        "04fe",
        "bd2b",
        "8f71",
    )
)


def _extract_section(workflow_text: str, start_anchor: str, end_anchor: str) -> str:
    """Return a stable workflow slice with explicit anchor assertions."""

    assert start_anchor in workflow_text, f"Missing workflow anchor: {start_anchor}"
    section_tail = workflow_text.split(start_anchor, maxsplit=1)[1]
    assert end_anchor in section_tail, f"Missing workflow anchor after {start_anchor}: {end_anchor}"
    return section_tail.split(end_anchor, maxsplit=1)[0]


def _extract_job_section(workflow_text: str, job_anchor: str) -> str:
    """Return a top-level GitHub Actions job block bounded by the next job or EOF."""

    assert job_anchor in workflow_text, f"Missing workflow anchor: {job_anchor}"
    start_index = workflow_text.index(job_anchor)
    section_tail = workflow_text[start_index + len(job_anchor) :]
    next_job_match = re.search(r"\n  [A-Za-z0-9][A-Za-z0-9_-]*:\n", section_tail)
    end_index = (
        start_index + len(job_anchor) + next_job_match.start()
        if next_job_match
        else len(workflow_text)
    )
    return workflow_text[start_index:end_index]


def _load_ci_workflow() -> dict[str, object]:
    return _load_workflow(CI_WORKFLOW_PATH)


def _load_workflow(path: Path) -> dict[str, object]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


_METADATA_MATERIAL_CONCURRENCY_GROUP = (
    "${{ github.workflow }}-${{ github.ref }}-"
    "${{ github.event_name == 'pull_request' && "
    "(github.event.action == 'edited' || github.event.action == 'labeled' || "
    "github.event.action == 'unlabeled') && 'metadata' || 'material' }}"
)
_CONCURRENCY_WORKFLOW_CONTRACTS = (
    (
        CI_WORKFLOW_PATH,
        ("opened", "synchronize", "reopened", "edited", "ready_for_review", "labeled", "unlabeled"),
        ("push", "pull_request"),
        ("edited", "labeled", "unlabeled"),
        ("opened", "synchronize", "reopened", "ready_for_review"),
    ),
    (
        FRONTEND_CI_WORKFLOW_PATH,
        ("opened", "synchronize", "reopened", "edited"),
        ("pull_request", "push", "workflow_dispatch"),
        ("edited",),
        ("opened", "synchronize", "reopened"),
    ),
)


def _assert_metadata_material_concurrency_contract(
    workflow: dict[str, object],
    expected_pr_types: tuple[str, ...],
    expected_events: tuple[str, ...],
) -> None:
    """Require the exact native event partition and unchanged declared trigger inventories."""
    concurrency = workflow["concurrency"]
    assert isinstance(concurrency, dict)
    assert concurrency == {
        "group": _METADATA_MATERIAL_CONCURRENCY_GROUP,
        "cancel-in-progress": True,
    }
    assert concurrency["cancel-in-progress"] is True
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)
    assert set(on_section) == set(expected_events)
    pull_request = on_section["pull_request"]
    assert isinstance(pull_request, dict)
    assert pull_request["types"] == list(expected_pr_types)


@pytest.mark.parametrize(
    ("path", "pr_types", "events", "metadata_actions", "material_actions"),
    _CONCURRENCY_WORKFLOW_CONTRACTS,
    ids=("ci", "frontend"),
)
def test_ci_and_frontend_concurrency_separate_metadata_from_material(
    path: Path,
    pr_types: tuple[str, ...],
    events: tuple[str, ...],
    metadata_actions: tuple[str, ...],
    material_actions: tuple[str, ...],
) -> None:
    """Pin native concurrency source shape without interpreting GitHub expressions."""
    _assert_metadata_material_concurrency_contract(_load_workflow(path), pr_types, events)


@pytest.mark.parametrize(
    ("path", "pr_types", "events", "metadata_actions", "material_actions"),
    _CONCURRENCY_WORKFLOW_CONTRACTS,
    ids=("ci", "frontend"),
)
def test_ci_and_frontend_concurrency_preserve_declared_events(
    path: Path,
    pr_types: tuple[str, ...],
    events: tuple[str, ...],
    metadata_actions: tuple[str, ...],
    material_actions: tuple[str, ...],
) -> None:
    """Preserve declared metadata/material actions and non-PR material fallback triggers."""
    workflow = _load_workflow(path)
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)
    assert set(on_section) == set(events)
    pull_request = on_section["pull_request"]
    assert isinstance(pull_request, dict)
    assert pull_request["types"] == list(pr_types)
    metadata = {"edited", "labeled", "unlabeled"}
    assert set(pr_types).intersection(metadata) == set(metadata_actions)
    assert set(pr_types).difference(metadata) == set(material_actions)
    assert "push" in on_section
    if "workflow_dispatch" in events:
        assert on_section["workflow_dispatch"] is None
    # The exact native expression owns event-name guarding and material fallback.
    # These finite source inventories do not execute or simulate GitHub scheduling.


@pytest.mark.parametrize(
    ("path", "pr_types", "events", "metadata_actions", "material_actions"),
    _CONCURRENCY_WORKFLOW_CONTRACTS,
    ids=("ci", "frontend"),
)
@pytest.mark.parametrize(
    "mutation",
    (
        "old-group",
        "missing-workflow",
        "missing-ref",
        "head-sha",
        "run-id",
        "missing-pr-guard",
        "predicate-or",
        "wrong-fallback",
        "cancel-disabled",
        "cancel-number",
        "extra-key",
        "missing-edited",
        "label-trigger-drift",
        "missing-push",
        "non-pr-trigger-drift",
    ),
)
def test_ci_and_frontend_concurrency_contract_rejects_mutations(
    path: Path,
    pr_types: tuple[str, ...],
    events: tuple[str, ...],
    metadata_actions: tuple[str, ...],
    material_actions: tuple[str, ...],
    mutation: str,
) -> None:
    """Reject bounded group, cancellation and trigger drift through the existing YAML seam."""
    workflow = _load_workflow(path)
    _assert_metadata_material_concurrency_contract(workflow, pr_types, events)
    concurrency = workflow["concurrency"]
    assert isinstance(concurrency, dict)
    group = concurrency["group"]
    assert isinstance(group, str)
    if mutation == "old-group":
        concurrency["group"] = "${{ github.workflow }}-${{ github.ref }}"
    elif mutation == "missing-workflow":
        concurrency["group"] = group.replace("${{ github.workflow }}-", "", 1)
    elif mutation == "missing-ref":
        concurrency["group"] = group.replace("${{ github.ref }}-", "", 1)
    elif mutation == "head-sha":
        concurrency["group"] = group + "-${{ github.event.pull_request.head.sha }}"
    elif mutation == "run-id":
        concurrency["group"] = group + "-${{ github.run_id }}"
    elif mutation == "missing-pr-guard":
        concurrency["group"] = group.replace("github.event_name == 'pull_request' && ", "", 1)
    elif mutation == "predicate-or":
        concurrency["group"] = group.replace("'pull_request' &&", "'pull_request' ||", 1)
    elif mutation == "wrong-fallback":
        concurrency["group"] = group.replace("|| 'material'", "|| 'metadata'", 1)
    elif mutation == "cancel-disabled":
        concurrency["cancel-in-progress"] = False
    elif mutation == "cancel-number":
        concurrency["cancel-in-progress"] = 1
    elif mutation == "extra-key":
        concurrency["unexpected"] = True
    else:
        on_section = workflow.get("on")
        if on_section is None:
            on_section = cast(dict[object, object], workflow).get(True)
        assert isinstance(on_section, dict)
        pull_request = on_section["pull_request"]
        assert isinstance(pull_request, dict)
        types = pull_request["types"]
        assert isinstance(types, list)
        if mutation == "missing-edited":
            types.remove("edited")
        elif mutation == "label-trigger-drift":
            if path == CI_WORKFLOW_PATH:
                types.remove("labeled")
            else:
                types.append("labeled")
        elif mutation == "missing-push":
            del on_section["push"]
        elif mutation == "non-pr-trigger-drift":
            if path == CI_WORKFLOW_PATH:
                on_section["workflow_dispatch"] = None
            else:
                del on_section["workflow_dispatch"]
        else:
            raise AssertionError(f"Unexpected concurrency mutation: {mutation}")
    with pytest.raises(AssertionError):
        _assert_metadata_material_concurrency_contract(workflow, pr_types, events)


_CANCELLATION_JOB_IDS = (
    (
        CI_WORKFLOW_PATH,
        (
            "merge_readiness_gate",
            "lint",
            "security",
            "openapi-sync",
            "test-pr",
            "pgvector_compat",
            "test-feature",
            "test-main",
            "diff-coverage",
        ),
    ),
    (FRONTEND_CI_WORKFLOW_PATH, ("caddy-contract",)),
)
_JOB_CANCELLATION_CONDITIONS = (
    (
        CI_WORKFLOW_PATH,
        "merge_readiness_gate",
        "${{ !cancelled() && github.event_name == 'pull_request' }}",
    ),
    (CI_WORKFLOW_PATH, "lint", "${{ !cancelled() }}"),
    (
        CI_WORKFLOW_PATH,
        "security",
        "${{ !cancelled() && (github.event_name != 'pull_request' || "
        "needs.changes.result != 'success' || needs.changes.outputs.run_security == 'true' || "
        "needs.changes.outputs.pgvector_compat == 'true') }}",
    ),
    (
        CI_WORKFLOW_PATH,
        "openapi-sync",
        "${{ !cancelled() && (github.event_name != 'pull_request' || "
        "needs.changes.result != 'success' || needs.changes.outputs.run_openapi_sync == 'true') }}",
    ),
    (
        CI_WORKFLOW_PATH,
        "test-pr",
        "${{ !cancelled() && github.event_name == 'pull_request' && "
        "(needs.changes.result != 'success' || needs.changes.outputs.run_backend_blocking == 'true') }}",
    ),
    (
        CI_WORKFLOW_PATH,
        "pgvector_compat",
        "${{ !cancelled() && github.event_name == 'pull_request' && "
        "(needs.changes.result != 'success' || needs.changes.outputs.pgvector_compat == 'true') }}",
    ),
    (
        CI_WORKFLOW_PATH,
        "test-feature",
        "${{ !cancelled() && github.event_name == 'push' && "
        "(startsWith(github.ref, 'refs/heads/feat/') || startsWith(github.ref, 'refs/heads/fix/') || "
        "startsWith(github.ref, 'refs/heads/feature/')) && "
        "(needs.changes.result != 'success' || needs.changes.outputs.run_backend_blocking == 'true') }}",
    ),
    (
        CI_WORKFLOW_PATH,
        "test-main",
        "${{ !cancelled() && (github.ref == 'refs/heads/main' || "
        "(github.event_name == 'pull_request' && (needs.changes.result != 'success' || "
        "needs.changes.outputs.run_main_ci_diagnostic == 'true'))) }}",
    ),
    (
        CI_WORKFLOW_PATH,
        "diff-coverage",
        "${{ !cancelled() && github.event_name == 'pull_request' && "
        "(needs.changes.result != 'success' || needs.changes.outputs.run_backend_blocking == 'true') }}",
    ),
    (
        FRONTEND_CI_WORKFLOW_PATH,
        "caddy-contract",
        "${{ !cancelled() && (needs.changes.outputs.caddy == 'true' || "
        "github.event_name == 'workflow_dispatch') }}",
    ),
)


def _assert_selected_workflow_job_cancellation_inventory(
    workflow: dict[str, object], expected_job_ids: tuple[str, ...]
) -> None:
    """Require the exact selected job inventory and reject cancellation-resistant status checks."""
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    observed: set[str] = set()
    for job_id, job in jobs.items():
        assert isinstance(job_id, str)
        assert isinstance(job, dict)
        condition = str(job.get("if", ""))
        assert "always()" not in condition, job_id
        if "!cancelled()" in condition:
            observed.add(job_id)
    assert observed == set(expected_job_ids)


@pytest.mark.parametrize(("path", "job_ids"), _CANCELLATION_JOB_IDS, ids=("ci", "frontend"))
def test_selected_workflow_job_cancellation_inventory_is_exact(
    path: Path, job_ids: tuple[str, ...]
) -> None:
    """Keep all nine CI jobs and the Frontend caddy job in the finite cancellation cohort."""
    expected = tuple(
        job_id for workflow_path, job_id, _ in _JOB_CANCELLATION_CONDITIONS if workflow_path == path
    )
    assert expected == job_ids
    assert len(_JOB_CANCELLATION_CONDITIONS) == 10
    _assert_selected_workflow_job_cancellation_inventory(_load_workflow(path), job_ids)


@pytest.mark.parametrize(("path", "job_id", "expected"), _JOB_CANCELLATION_CONDITIONS)
def test_selected_workflow_job_cancellation_predicates_preserve_complete_tails(
    path: Path, job_id: str, expected: str
) -> None:
    """Pin each complete native condition without evaluating GitHub scheduling expressions."""
    jobs = _load_workflow(path)["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[job_id]
    assert isinstance(job, dict)
    assert job["if"] == expected


@pytest.mark.parametrize(("path", "job_id", "expected"), _JOB_CANCELLATION_CONDITIONS)
@pytest.mark.parametrize(
    "mutation",
    (
        "missing-job",
        "extra-job",
        "always",
        "success-only",
        "redundant-always",
        "or-escape",
        "wrong-operator",
        "lost-parenthesis",
        "missing-braces",
        "lost-tail",
    ),
)
def test_selected_workflow_job_cancellation_contract_rejects_drift(
    path: Path, job_id: str, expected: str, mutation: str
) -> None:
    """Reject finite membership and status/tail drift through the existing YAML source seam."""
    workflow = _load_workflow(path)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[job_id]
    assert isinstance(job, dict)
    assert job["if"] == expected
    if mutation == "missing-job":
        del jobs[job_id]
    elif mutation == "extra-job":
        jobs["unexpected-cancellation-job"] = {"if": "${{ !cancelled() }}"}
    elif mutation == "always":
        job["if"] = expected.replace("!cancelled()", "always()", 1)
    elif mutation == "success-only":
        job["if"] = expected.replace("!cancelled()", "success()", 1)
    elif mutation == "redundant-always":
        job["if"] = expected.replace("!cancelled()", "always() && !cancelled()", 1)
    elif mutation == "or-escape":
        job["if"] = expected.replace("!cancelled()", "!cancelled() || true", 1)
    elif mutation == "wrong-operator":
        job["if"] = (
            expected.replace(" && ", " || ", 1)
            if job_id != "lint"
            else "${{ !cancelled() || true }}"
        )
    elif mutation == "lost-parenthesis":
        job["if"] = (
            expected.replace(" && (", " && ", 1)
            if " && (" in expected
            else expected.replace("!cancelled()", "!cancelled(", 1)
        )
    elif mutation == "missing-braces":
        job["if"] = expected.removeprefix("${{ ").removesuffix(" }}")
    elif mutation == "lost-tail":
        job["if"] = "${{ !cancelled() }}" if job_id != "lint" else "${{ false }}"
    else:
        raise AssertionError(f"Unexpected cancellation mutation: {mutation}")
    expected_job_ids = next(
        ids for workflow_path, ids in _CANCELLATION_JOB_IDS if workflow_path == path
    )
    with pytest.raises(AssertionError):
        _assert_selected_workflow_job_cancellation_inventory(workflow, expected_job_ids)
        for workflow_path, selected_job_id, condition in _JOB_CANCELLATION_CONDITIONS:
            if workflow_path == path:
                assert jobs[selected_job_id]["if"] == condition


def _active_workflow_paths() -> Iterator[Path]:
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    yield from sorted(workflow_dir.glob("*.yml"))
    yield from sorted(workflow_dir.glob("*.yaml"))


def _active_composite_action_paths() -> Iterator[Path]:
    actions_dir = REPO_ROOT / ".github" / "actions"
    yield from sorted(actions_dir.rglob("action.yml"))
    yield from sorted(actions_dir.rglob("action.yaml"))


def _iter_job_steps(path: Path) -> Iterator[tuple[str, dict[str, object]]]:
    workflow = _load_workflow(path)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    for job_id, job in jobs.items():
        assert isinstance(job_id, str)
        assert isinstance(job, dict)
        steps = job.get("steps", [])
        assert isinstance(steps, list)
        for step in steps:
            assert isinstance(step, dict)
            yield job_id, step


def _assert_contains_all_tokens(expression: str, expected_tokens: tuple[str, ...]) -> None:
    """Assert that a workflow expression keeps all required routing tokens."""

    for token in expected_tokens:
        assert (
            token in expression
        ), f"Missing token {token!r} in expression excerpt: {expression[:500]!r}"


def _assert_yaml_mapping_keys_are_unique(source: str) -> None:
    """Reject duplicate YAML keys before safe-load last-key semantics can hide them."""

    document = yaml.compose(source)
    assert isinstance(document, Node)

    def visit(node: Node, path: tuple[str, ...]) -> None:
        if isinstance(node, MappingNode):
            seen: dict[tuple[str, str], int] = {}
            for key_node, value_node in node.value:
                assert isinstance(key_node, ScalarNode)
                identity = (key_node.tag, key_node.value)
                assert identity not in seen, (
                    f"Duplicate YAML key {key_node.value!r} at "
                    f"{'.'.join(path) or '<root>'}:{key_node.start_mark.line + 1}; "
                    f"first declared at line {seen[identity]}"
                )
                seen[identity] = key_node.start_mark.line + 1
                visit(value_node, (*path, key_node.value))
        elif isinstance(node, SequenceNode):
            for index, value_node in enumerate(node.value):
                visit(value_node, (*path, str(index)))

    visit(document, ())


def _iter_uses_source_mappings(node: Node) -> Iterator[tuple[ScalarNode, ScalarNode]]:
    """Visit every parsed uses field, including nested composite action steps."""

    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            if isinstance(key_node, ScalarNode) and key_node.value == "uses":
                assert isinstance(value_node, ScalarNode), "uses must be a YAML scalar"
                assert value_node.tag == "tag:yaml.org,2002:str", "uses must be a string"
                yield key_node, value_node
            yield from _iter_uses_source_mappings(value_node)
    elif isinstance(node, SequenceNode):
        for value_node in node.value:
            yield from _iter_uses_source_mappings(value_node)


def test_all_active_workflows_declare_unique_yaml_keys() -> None:
    """Duplicate keys must not silently override any active workflow configuration."""

    for workflow_path in _active_workflow_paths():
        _assert_yaml_mapping_keys_are_unique(workflow_path.read_text(encoding="utf-8"))


def _assert_no_unsafe_checkout_input(value: object) -> None:
    """Reject the unsafe v7 opt-in regardless of action-input key casing."""

    if isinstance(value, dict):
        assert all(
            not isinstance(key, str) or key.casefold() != "allow-unsafe-pr-checkout"
            for key in value
        )
        for child in value.values():
            _assert_no_unsafe_checkout_input(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_unsafe_checkout_input(child)


@pytest.mark.parametrize("key", ["allow-unsafe-pr-checkout", "Allow-Unsafe-Pr-Checkout"])
def test_checkout_unsafe_input_rejects_case_variants(key: str) -> None:
    """A casing variant cannot bypass the parsed workflow input guard."""

    with pytest.raises(AssertionError):
        _assert_no_unsafe_checkout_input({"jobs": [{"with": {key: True}}]})


def test_all_active_checkout_uses_have_one_exact_v7_pin() -> None:
    """Enumerate checkout uses in every active workflow and local composite action."""

    workflow_paths = list(_active_workflow_paths())
    composite_paths = list(_active_composite_action_paths())
    assert workflow_paths, "Active workflow inventory must not be empty"
    assert len({path.name for path in workflow_paths}) == len(workflow_paths)
    assert len({path.parent for path in composite_paths}) == len(composite_paths)
    workflow_path_set = set(workflow_paths)

    expected_uses = f"actions/checkout@{CHECKOUT_V7_SHA}"
    expected_source_lines = {
        f"uses: {expected_uses} # v7.0.1",
        f"uses: {expected_uses} # v7.0.1 / Node 24",
    }
    observed_checkout_uses: list[tuple[str, int]] = []
    for path in (*workflow_paths, *composite_paths):
        source = path.read_text(encoding="utf-8")
        _assert_yaml_mapping_keys_are_unique(source)
        payload = yaml.safe_load(source)
        assert isinstance(payload, dict), f"{path}: YAML root must be a mapping"
        _assert_no_unsafe_checkout_input(payload)
        if path in workflow_path_set:
            assert (
                isinstance(payload.get("jobs"), dict) and payload["jobs"]
            ), f"{path}: active workflow jobs inventory must be nonempty"
        else:
            runs = payload.get("runs")
            assert isinstance(runs, dict) and runs.get("using") == "composite", path
            assert isinstance(runs.get("steps"), list) and runs["steps"], path
        document = yaml.compose(source)
        assert isinstance(document, MappingNode), f"{path}: YAML root must be a mapping"
        for key_node, value_node in _iter_uses_source_mappings(document):
            uses = value_node.value
            if uses.split("@", maxsplit=1)[0].casefold() != "actions/checkout":
                continue
            relative_path = str(path.relative_to(REPO_ROOT))
            observed_checkout_uses.append((relative_path, key_node.start_mark.line + 1))
            assert uses == expected_uses, f"{relative_path}:{key_node.start_mark.line + 1}: {uses}"
            source_line = source.splitlines()[key_node.start_mark.line].strip().removeprefix("- ")
            assert (
                source_line in expected_source_lines
            ), f"{relative_path}:{key_node.start_mark.line + 1}: {source_line}"

    expected_checkout_workflows = {
        ".github/workflows/accessibility.yml",
        ".github/workflows/actionlint.yml",
        ".github/workflows/build-equivalence-evidence.yml",
        ".github/workflows/build.yml",
        ".github/workflows/cd-test.yml",
        ".github/workflows/cd.yml",
        ".github/workflows/ci-metrics.yml",
        ".github/workflows/ci.yml",
        ".github/workflows/codecov-upload.yml",
        ".github/workflows/codeql.yml",
        ".github/workflows/devcontainer-smoke.yml",
        ".github/workflows/experiment-runner-dispatch.yml",
        ".github/workflows/experiment-runner-slack-socket-smoke.yml",
        ".github/workflows/frontend-ci.yml",
        ".github/workflows/greenlight-ios.yml",
        ".github/workflows/ios-appstore-assets.yml",
        ".github/workflows/nightly-tests.yml",
        ".github/workflows/nightly.yml",
        ".github/workflows/npm-dependency-submission.yml",
        ".github/workflows/python-dependency-submission.yml",
        ".github/workflows/rag-release-gates.yml",
        ".github/workflows/release-control-plane-evidence.yml",
        ".github/workflows/release-manifest-evidence.yml",
        ".github/workflows/security.yml",
        ".github/workflows/trivy.yml",
    }
    assert len(observed_checkout_uses) == 76
    assert {path for path, _ in observed_checkout_uses} == expected_checkout_workflows


def _job_step_by_name(
    workflow: dict[str, object],
    *,
    job_id: str,
    step_name: str,
) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[job_id]
    assert isinstance(job, dict)
    steps = job["steps"]
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"missing step {step_name!r} in {job_id!r}")


def test_backend_test_jobs_run_permanent_npm_dependency_guards() -> None:
    """Both backend PR jobs keep the two npm guard owners in critical smoke."""
    workflow = _load_ci_workflow()
    required_targets = (
        "tests/test_frontend_dependency_guards.py",
        "tests/test_root_npm_dependency_guards.py",
    )

    for job_id in ("test-pr", "test-feature"):
        step = _job_step_by_name(
            workflow,
            job_id=job_id,
            step_name="Critical smoke (deterministic merge blocker)",
        )
        run_script = step.get("run")
        assert isinstance(run_script, str)
        for target in required_targets:
            assert (
                run_script.count(target) == 1
            ), f"{job_id} critical smoke must run {target} exactly once"


def _docker_environment_flags(run_script: str) -> set[str]:
    """Return normalized ``docker run -e`` arguments from a workflow script."""

    flags: set[str] = set()
    for line in run_script.splitlines():
        stripped = line.strip()
        if stripped.startswith("-e "):
            flags.add(stripped.removeprefix("-e ").removesuffix("\\").strip())
    return flags


def _contract_suite_targets_by_group(
    workflow: dict[str, object],
    *,
    job_id: str,
) -> dict[str, tuple[str, ...]]:
    step = _job_step_by_name(
        workflow,
        job_id=job_id,
        step_name="Contract and risk suites",
    )
    run_script = step["run"]
    assert isinstance(run_script, str)
    case_match = re.search(r'case "\$group" in(?P<body>.*?)(?=^\s+\*\))', run_script, re.S | re.M)
    assert case_match is not None, f"missing contract/risk case block in {job_id}"
    case_body = case_match.group("body") + "\n              *)"
    blocks: dict[str, tuple[str, ...]] = {}
    for match in re.finditer(
        r"^\s+(?P<group>[a-z_]+)\)\n(?P<body>.*?)(?=^\s+(?:[a-z_]+|\*)\))",
        case_body,
        re.S | re.M,
    ):
        group = match.group("group")
        lines = match.group("body").splitlines()
        suite_starts = [index for index, line in enumerate(lines) if line.strip() == "add_suite \\"]
        assert len(suite_starts) == 1, f"expected one add_suite command in {group!r} for {job_id!r}"
        targets_list: list[str] = []
        for line in lines[suite_starts[0] + 1 :]:
            argument = line.strip()
            continued = argument.endswith("\\")
            target = argument[:-1].strip() if continued else argument
            assert re.fullmatch(
                r"tests/[A-Za-z0-9_./-]+\.py", target
            ), f"non-test or commented add_suite argument in {group!r} for {job_id!r}: {line!r}"
            targets_list.append(target)
            if not continued:
                break
        else:
            raise AssertionError(f"unterminated add_suite command in {group!r} for {job_id!r}")
        targets = tuple(targets_list)
        assert targets, f"contract/risk group {group!r} in {job_id!r} has no test targets"
        blocks[group] = targets
    return blocks


NODE24_FRONTEND_BUILD_LINE = (
    "FROM node:24.18.1-bookworm-slim@"
    "sha256:235600a8101ab264e117b1768e925532262668dc9b581ef1dd7d96ced463b8e7"
    " AS frontend-build"
)
NODE24_FRONTEND_BUILD_RUN_LINE = "RUN npm run build"
NODE24_FRONTEND_BUILD_COMMAND_ERROR = (
    "frontend-build must end with exactly one canonical npm run build"
)
NODE24_CADDY_BINARY_COPY_LINE = (
    "COPY --from=caddy-build --chmod=0755 /go/bin/caddy /usr/bin/caddy.pulseplate"
)
NODE24_FRONTEND_ASSET_RESET_LINE = 'RUN ["/bin/busybox", "rm", "-rf", "/srv/frontend"]'
NODE24_FRONTEND_ASSET_COPY_LINE = "COPY --from=frontend-build /app/dist /srv/frontend"
NODE24_FRONTEND_ASSET_WRITE_LINES = (
    NODE24_FRONTEND_ASSET_RESET_LINE,
    NODE24_FRONTEND_ASSET_COPY_LINE,
)
NODE24_FINAL_STAGE_COPY_ADD_LINES = (
    NODE24_CADDY_BINARY_COPY_LINE,
    NODE24_FRONTEND_ASSET_COPY_LINE,
)
NODE24_UNSUPPORTED_FROM_ERROR = "FROM stages must use the supported single-line form"
NODE24_UNSUPPORTED_HEREDOC_ERROR = "Docker heredoc instructions are unsupported"
NODE24_SUPPORTED_FROM_RE = re.compile(
    r"\s*FROM(?:\s+--platform=[^\s\\`]+)?\s+[^\s\\`]+" r"(?:\s+AS\s+(?P<alias>[^\s\\`]+))?\s*",
    flags=re.IGNORECASE,
)
NODE24_CONTINUED_FROM_PREFIX_RE = re.compile(
    r"\s*(?:F|FR|FRO|FROM)[\\`]\s*",
    flags=re.IGNORECASE,
)
NODE24_CONTINUED_COPY_ADD_PREFIX_RE = re.compile(
    r"\s*(?:C|CO|COP|COPY|A|AD|ADD)[\\`]\s*",
    flags=re.IGNORECASE,
)


def _docker_logical_instructions(
    dockerfile_lines: list[str],
) -> tuple[list[tuple[int, int, str]], bool]:
    """Return bounded Docker logical instructions and an incomplete-tail flag."""

    escape_character = "\\"
    for line in dockerfile_lines:
        stripped = line.strip()
        if not stripped:
            break
        directive_match = re.fullmatch(
            r"#\s*(syntax|escape|check)\s*=\s*(\S.*)", stripped, re.IGNORECASE
        )
        if directive_match is None:
            break
        if directive_match.group(1).lower() == "escape":
            escape_value = directive_match.group(2).strip()
            if escape_value in {"\\", "`"}:
                escape_character = escape_value

    instructions: list[tuple[int, int, str]] = []
    current_parts: list[str] = []
    current_start: int | None = None
    for line_index, line in enumerate(dockerfile_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current_start is None:
            current_start = line_index
        physical_part = line.rstrip()
        continued = physical_part.endswith(escape_character)
        if continued:
            physical_part = physical_part[: -len(escape_character)]
        current_parts.append(physical_part.strip())
        if continued:
            continue
        instructions.append((current_start, line_index, " ".join(current_parts)))
        current_parts = []
        current_start = None
    return instructions, current_start is not None


def _node24_frontend_builder_contract_errors(dockerfile: str) -> list[str]:
    """Return finite carrier errors for the known Caddy SPA Dockerfile."""

    dockerfile_lines = dockerfile.splitlines()
    from_candidate_lines = [
        line for line in dockerfile_lines if re.match(r"\s*FROM(?:\s|$)", line, flags=re.IGNORECASE)
    ]
    unsupported_from_lines = [
        line for line in from_candidate_lines if NODE24_SUPPORTED_FROM_RE.fullmatch(line) is None
    ]
    has_utf8_bom = dockerfile.startswith("\ufeff")
    has_continued_from_keyword = any(
        NODE24_CONTINUED_FROM_PREFIX_RE.fullmatch(line) is not None for line in dockerfile_lines
    )
    frontend_build_owner_lines = [
        line
        for line in dockerfile_lines
        if re.fullmatch(
            r"\s*FROM(?:\s+--platform=[^\s\\`]+)?\s+[^\s\\`]+" r"\s+AS\s+frontend-build\s*",
            line,
            flags=re.IGNORECASE,
        )
    ]
    node_from_stage_lines = [
        line
        for line in dockerfile_lines
        if re.fullmatch(
            r"\s*FROM(?:\s+--platform=[^\s\\`]+)?\s+node:[^\s\\`]+" r"(?:\s+AS\s+[^\s\\`]+)?\s*",
            line,
            flags=re.IGNORECASE,
        )
    ]
    from_stage_aliases: list[str | None] = []
    from_stage_indices: list[int] = []
    for line_index, line in enumerate(dockerfile_lines):
        stage_match = NODE24_SUPPORTED_FROM_RE.fullmatch(line)
        if stage_match is None:
            continue
        alias = stage_match.group("alias")
        from_stage_aliases.append(alias.lower() if alias else None)
        from_stage_indices.append(line_index)
    frontend_asset_write_lines = [
        line
        for line in dockerfile_lines
        if "/srv/frontend" in line and not line.lstrip().startswith("#")
    ]
    frontend_asset_write_indices = [
        line_index
        for line_index, line in enumerate(dockerfile_lines)
        if "/srv/frontend" in line and not line.lstrip().startswith("#")
    ]
    final_stage_start_index = (
        from_stage_indices[-1] if from_stage_indices else len(dockerfile_lines)
    )
    logical_instructions, has_incomplete_logical_instruction = _docker_logical_instructions(
        dockerfile_lines
    )
    logical_instruction_start_indices = {
        start_index for start_index, _end_index, _instruction in logical_instructions
    }
    has_absorbed_from_stage = any(
        from_stage_index not in logical_instruction_start_indices
        for from_stage_index in from_stage_indices
    )
    dockerfile_has_heredoc = any(
        re.search(r"<\s*<", instruction) is not None
        for _start_index, _end_index, instruction in logical_instructions
    )
    final_stage_logical_instructions = [
        instruction
        for start_index, _end_index, instruction in logical_instructions
        if start_index > final_stage_start_index
    ]
    frontend_build_stage_index = (
        from_stage_indices[from_stage_aliases.index("frontend-build")]
        if "frontend-build" in from_stage_aliases
        else None
    )
    frontend_build_stage_end_index = (
        next(
            (
                stage_index
                for stage_index in from_stage_indices
                if frontend_build_stage_index is not None
                and stage_index > frontend_build_stage_index
            ),
            len(dockerfile_lines),
        )
        if frontend_build_stage_index is not None
        else None
    )
    frontend_build_logical_instructions = [
        instruction
        for start_index, _end_index, instruction in logical_instructions
        if frontend_build_stage_index is not None
        and frontend_build_stage_end_index is not None
        and frontend_build_stage_index < start_index < frontend_build_stage_end_index
    ]
    final_stage_copy_add_entries = [
        (line_index, line)
        for line_index, line in enumerate(dockerfile_lines)
        if line_index > final_stage_start_index
        and re.match(r"\s*(?:COPY|ADD)(?:\s|$)", line, flags=re.IGNORECASE)
    ]
    final_stage_copy_add_lines = [line for _line_index, line in final_stage_copy_add_entries]
    has_absorbed_final_stage_copy_add = any(
        line_index not in logical_instruction_start_indices
        for line_index, _line in final_stage_copy_add_entries
    )
    has_continued_final_stage_copy_add_keyword = any(
        line_index > final_stage_start_index
        and NODE24_CONTINUED_COPY_ADD_PREFIX_RE.fullmatch(line) is not None
        for line_index, line in enumerate(dockerfile_lines)
    )

    errors: list[str] = []
    if (
        has_utf8_bom
        or unsupported_from_lines
        or has_continued_from_keyword
        or has_absorbed_from_stage
    ):
        errors.append(NODE24_UNSUPPORTED_FROM_ERROR)
    if has_incomplete_logical_instruction:
        errors.append("Dockerfile logical instructions must be complete")
    if dockerfile_has_heredoc:
        errors.append(NODE24_UNSUPPORTED_HEREDOC_ERROR)
    if frontend_build_owner_lines != [NODE24_FRONTEND_BUILD_LINE]:
        errors.append("frontend-build must have exactly one immutable Node owner")
    if node_from_stage_lines != [NODE24_FRONTEND_BUILD_LINE]:
        errors.append("the immutable frontend-build line must be the only Node FROM stage")
    if from_stage_aliases != ["caddy-build", "frontend-build", None]:
        errors.append("Dockerfile stage aliases must stay finite and ordered")
    if (
        frontend_build_logical_instructions.count(NODE24_FRONTEND_BUILD_RUN_LINE) != 1
        or not frontend_build_logical_instructions
        or frontend_build_logical_instructions[-1] != NODE24_FRONTEND_BUILD_RUN_LINE
    ):
        errors.append(NODE24_FRONTEND_BUILD_COMMAND_ERROR)
    if (
        final_stage_copy_add_lines != list(NODE24_FINAL_STAGE_COPY_ADD_LINES)
        or has_absorbed_final_stage_copy_add
        or has_continued_final_stage_copy_add_keyword
    ):
        errors.append("final-stage COPY/ADD instructions must stay finite and ordered")
    if frontend_asset_write_lines != list(NODE24_FRONTEND_ASSET_WRITE_LINES):
        errors.append("production frontend assets must come only from frontend-build")
    elif not from_stage_indices or frontend_asset_write_indices[0] <= from_stage_indices[-1]:
        errors.append("production frontend asset handoff must belong to the final stage")
    elif has_utf8_bom or unsupported_from_lines or has_continued_from_keyword:
        pass
    elif NODE24_FRONTEND_ASSET_RESET_LINE not in final_stage_logical_instructions:
        errors.append("production frontend asset reset must be an independent logical instruction")
    elif NODE24_FRONTEND_ASSET_COPY_LINE not in final_stage_logical_instructions:
        errors.append(
            "production frontend asset handoff must be an independent logical instruction"
        )
    elif final_stage_logical_instructions[-1] != NODE24_FRONTEND_ASSET_COPY_LINE:
        errors.append("production frontend asset handoff must be the final executable instruction")
    elif final_stage_logical_instructions[-2:] != list(NODE24_FRONTEND_ASSET_WRITE_LINES):
        errors.append("production frontend asset reset must immediately precede the handoff")
    return errors


def test_node24_runtime_baseline_surfaces_stay_coherent() -> None:
    """Guard the repo Node baseline across local, frontend, Docker, and devcontainer surfaces."""

    nvmrc = (REPO_ROOT / ".nvmrc").read_text(encoding="utf-8").strip()
    frontend_package = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    frontend_lock = json.loads(
        (REPO_ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8")
    )
    devcontainer = json.loads(
        (REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    )
    public_readme = (REPO_ROOT / "README_V2_PUBLIC_DRAFT.md").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")

    assert nvmrc == "24.18.1"
    assert "- Node `24.18.1` for the web client" in public_readme
    assert "`nvm use` reads the repo-root `.nvmrc` and selects Node `24.18.1`." in public_readme
    assert "24.16.0" not in public_readme
    assert frontend_package["engines"]["node"] == ">=24.0.0 <25.0.0"
    assert frontend_lock["packages"][""]["engines"]["node"] == ">=24.0.0 <25.0.0"
    assert frontend_package["overrides"]["ws"] == "8.21.0"
    assert frontend_lock["packages"]["node_modules/ws"]["version"] == "8.21.0"
    assert devcontainer["features"]["ghcr.io/devcontainers/features/node:1"]["version"] == "24"
    contract_errors = _node24_frontend_builder_contract_errors(dockerfile)
    assert contract_errors == [], "\n".join(contract_errors)
    assert "node:22.22.1" not in dockerfile


def test_node24_frontend_builder_guard_rejects_missing_asset_handoff() -> None:
    """The immutable builder must remain the production SPA asset owner."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    assert dockerfile.count(NODE24_FRONTEND_ASSET_COPY_LINE) == 1
    disconnected = dockerfile.replace(NODE24_FRONTEND_ASSET_COPY_LINE, "", 1)

    errors = _node24_frontend_builder_contract_errors(disconnected)

    assert "production frontend assets must come only from frontend-build" in errors


@pytest.mark.parametrize(
    "replacement",
    (
        "RUN vite build",
        "RUN npx vite build",
        "RUN npm exec vite -- build",
        "RUN npm run build || true",
        "RUN npm run build; exit 0",
        "RUN npm run build\nRUN vite build",
        "RUN npm run build\nRUN npm run build",
    ),
)
def test_node24_frontend_builder_guard_rejects_build_command_bypass(
    replacement: str,
) -> None:
    """The shipped SPA builder must finish through the canonical package build."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    mutated = dockerfile.replace(NODE24_FRONTEND_BUILD_RUN_LINE, replacement, 1)

    errors = _node24_frontend_builder_contract_errors(mutated)

    assert NODE24_FRONTEND_BUILD_COMMAND_ERROR in errors


def test_node24_frontend_builder_guard_rejects_alternate_asset_owner() -> None:
    """A decorative pinned stage cannot mask an alternate mutable builder."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    alternate_stage = "\n".join(
        (
            NODE24_FRONTEND_BUILD_LINE,
            "ARG ALT_NODE_IMAGE=node:25-alpine",
            "FROM ${ALT_NODE_IMAGE} AS alternate-frontend-build",
        )
    )
    redirected = dockerfile.replace(
        NODE24_FRONTEND_BUILD_LINE,
        alternate_stage,
        1,
    ).replace(
        NODE24_FRONTEND_ASSET_COPY_LINE,
        "COPY --from=alternate-frontend-build /app/dist /srv/frontend",
        1,
    )

    errors = _node24_frontend_builder_contract_errors(redirected)

    assert "Dockerfile stage aliases must stay finite and ordered" in errors
    assert "production frontend assets must come only from frontend-build" in errors


def test_node24_frontend_builder_guard_rejects_continued_node_stage() -> None:
    """A continued Node stage cannot escape the finite FROM inventory."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    continued_stage = "\n".join(
        (
            dockerfile,
            "FROM node:25-bookworm-slim \\",
            " AS tooling",
        )
    )

    errors = _node24_frontend_builder_contract_errors(continued_stage)

    assert NODE24_UNSUPPORTED_FROM_ERROR in errors


def test_node24_frontend_builder_guard_rejects_continued_canonical_owner() -> None:
    """The canonical builder owner must use the supported single-line form."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    continued_owner = NODE24_FRONTEND_BUILD_LINE.replace(
        " AS frontend-build",
        " \\\n AS frontend-build",
        1,
    )
    continued = dockerfile.replace(NODE24_FRONTEND_BUILD_LINE, continued_owner, 1)

    errors = _node24_frontend_builder_contract_errors(continued)

    assert NODE24_UNSUPPORTED_FROM_ERROR in errors


@pytest.mark.parametrize("escape_character", ("\\", "`"))
@pytest.mark.parametrize("stage_prefix", ("FROM golang:", "FROM node:", "FROM caddy:"))
def test_node24_frontend_builder_guard_rejects_absorbed_from_stage(
    escape_character: str,
    stage_prefix: str,
) -> None:
    """A preceding continuation cannot absorb any physical FROM line."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    if escape_character == "`":
        dockerfile = dockerfile.replace(
            "# syntax=docker/dockerfile:1",
            "# syntax=docker/dockerfile:1\n# escape=`",
            1,
        )
    stage = next(line for line in dockerfile.splitlines() if line.startswith(stage_prefix))
    absorbed = dockerfile.replace(
        stage,
        "\n".join((f"RUN : {escape_character}", stage)),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(absorbed)

    assert NODE24_UNSUPPORTED_FROM_ERROR in errors


def test_node24_frontend_builder_guard_rejects_backtick_continued_stage() -> None:
    """Docker's alternate escape directive cannot hide a continued FROM stage."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    runtime_stage = next(line for line in dockerfile.splitlines() if line.startswith("FROM caddy:"))
    continued = dockerfile.replace(
        "# syntax=docker/dockerfile:1",
        "# syntax=docker/dockerfile:1\n# escape=`",
        1,
    ).replace(
        runtime_stage,
        f"{runtime_stage}`\n AS final-runtime",
        1,
    )

    errors = _node24_frontend_builder_contract_errors(continued)

    assert NODE24_UNSUPPORTED_FROM_ERROR in errors


def test_node24_frontend_builder_guard_rejects_split_from_keyword() -> None:
    """A continued keyword cannot hide a logical FROM instruction."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    for escape_character in ("\\", "`"):
        candidate = dockerfile
        if escape_character == "`":
            candidate = candidate.replace(
                "# syntax=docker/dockerfile:1",
                "# syntax=docker/dockerfile:1\n# escape=`",
                1,
            )
        for continuation_count in (1, 2):
            for split_index in range(1, len("FROM") + 1):
                continuation = f"{escape_character}\n" * continuation_count
                continued_keyword = f"{'FROM'[:split_index]}{continuation}{'FROM'[split_index:]}"
                hidden_stage = (
                    f"{candidate}\n{continued_keyword} node:25-bookworm-slim AS hidden-tooling"
                )

                errors = _node24_frontend_builder_contract_errors(hidden_stage)

                assert errors == [NODE24_UNSUPPORTED_FROM_ERROR], (
                    escape_character,
                    continuation_count,
                    split_index,
                    errors,
                )


def test_node24_frontend_builder_guard_rejects_commented_from_bridge() -> None:
    """A Docker comment cannot hide a continued FROM keyword prefix."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    for escape_character in ("\\", "`"):
        candidate = dockerfile
        if escape_character == "`":
            candidate = candidate.replace(
                "# syntax=docker/dockerfile:1",
                "# syntax=docker/dockerfile:1\n# escape=`",
                1,
            )
        for comment_indent in ("", "  "):
            hidden_stage = "\n".join(
                (
                    candidate,
                    f"FR{escape_character}",
                    f"{comment_indent}# ignored during Docker continuation",
                    "OM node:25-bookworm-slim AS hidden-tooling",
                )
            )

            errors = _node24_frontend_builder_contract_errors(hidden_stage)

            assert errors == [NODE24_UNSUPPORTED_FROM_ERROR], (
                escape_character,
                comment_indent,
                errors,
            )


def test_node24_frontend_builder_guard_rejects_crlf_split_from_keyword() -> None:
    """CRLF line endings cannot hide a continued FROM keyword prefix."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    for escape_character in ("\\", "`"):
        candidate = dockerfile
        if escape_character == "`":
            candidate = candidate.replace(
                "# syntax=docker/dockerfile:1",
                "# syntax=docker/dockerfile:1\n# escape=`",
                1,
            )
        hidden_stage = "\n".join(
            (
                candidate,
                f"FR{escape_character}",
                "OM node:25-bookworm-slim AS hidden-tooling",
            )
        ).replace("\n", "\r\n")

        errors = _node24_frontend_builder_contract_errors(hidden_stage)

        assert errors == [NODE24_UNSUPPORTED_FROM_ERROR], (escape_character, errors)


def test_node24_frontend_builder_guard_rejects_utf8_bom() -> None:
    """Docker's stripped UTF-8 BOM cannot hide an initial FROM instruction."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    bom_prefixed = "\ufeffFROM node:25-bookworm-slim AS hidden-tooling\n" + dockerfile

    errors = _node24_frontend_builder_contract_errors(bom_prefixed)

    assert errors == [NODE24_UNSUPPORTED_FROM_ERROR]


def test_node24_frontend_builder_guard_ignores_non_from_tokens() -> None:
    """Comments and longer identifiers are not Docker FROM instructions."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    non_instructions = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "# FROM node:25-bookworm-slim AS commented-tooling",
                "FROMAGE node:25-bookworm-slim AS identifier-tooling",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    assert _node24_frontend_builder_contract_errors(non_instructions) == []


@pytest.mark.parametrize("escape_character", ("\\", "`"))
def test_node24_frontend_builder_guard_rejects_absorbed_caddy_copy(
    escape_character: str,
) -> None:
    """A preceding continuation cannot absorb the Caddy provenance COPY."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    if escape_character == "`":
        dockerfile = dockerfile.replace(
            "# syntax=docker/dockerfile:1",
            "# syntax=docker/dockerfile:1\n# escape=`",
            1,
        )
    absorbed = dockerfile.replace(
        NODE24_CADDY_BINARY_COPY_LINE,
        "\n".join((f"RUN : {escape_character}", NODE24_CADDY_BINARY_COPY_LINE)),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(absorbed)

    assert "final-stage COPY/ADD instructions must stay finite and ordered" in errors


@pytest.mark.parametrize("escape_character", ("\\", "`"))
@pytest.mark.parametrize("keyword", ("COPY", "ADD"))
@pytest.mark.parametrize("comment_bridge", (False, True))
def test_node24_frontend_builder_guard_rejects_split_copy_add_keyword(
    escape_character: str,
    keyword: str,
    comment_bridge: bool,
) -> None:
    """A continued keyword cannot hide a final-stage COPY or ADD instruction."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    if escape_character == "`":
        dockerfile = dockerfile.replace(
            "# syntax=docker/dockerfile:1",
            "# syntax=docker/dockerfile:1\n# escape=`",
            1,
        )
    for split_index in range(1, len(keyword) + 1):
        hidden_instruction_parts = [f"{keyword[:split_index]}{escape_character}"]
        if comment_bridge:
            hidden_instruction_parts.append("# ignored during Docker continuation")
        hidden_instruction_parts.append(f"{keyword[split_index:]} package.json /usr/bin/caddy")
        hidden = dockerfile.replace(
            NODE24_FRONTEND_ASSET_RESET_LINE,
            "\n".join((*hidden_instruction_parts, NODE24_FRONTEND_ASSET_RESET_LINE)),
            1,
        )

        errors = _node24_frontend_builder_contract_errors(hidden)

        assert "final-stage COPY/ADD instructions must stay finite and ordered" in errors, (
            escape_character,
            keyword,
            comment_bridge,
            split_index,
            errors,
        )


def test_node24_frontend_builder_guard_rejects_asset_overwrite() -> None:
    """A later copy cannot replace a served asset from another stage."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    overwritten = "\n".join(
        (
            dockerfile,
            "COPY --from=caddy-build /usr/bin/caddy /srv/frontend/index.html",
        )
    )

    errors = _node24_frontend_builder_contract_errors(overwritten)

    assert "production frontend assets must come only from frontend-build" in errors


def test_node24_frontend_builder_guard_rejects_post_handoff_run() -> None:
    """No continued RUN may replace an asset after the immutable handoff."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    overwritten = "\n".join(
        (
            dockerfile,
            "RUN printf '<html>alternate</html>' > /srv/front\\",
            "end/index.html",
        )
    )

    errors = _node24_frontend_builder_contract_errors(overwritten)

    assert "production frontend asset handoff must be the final executable instruction" in errors


@pytest.mark.parametrize(
    ("replacement", "expected_error"),
    (
        ("", "production frontend assets must come only from frontend-build"),
        (
            f"{NODE24_FRONTEND_ASSET_RESET_LINE}\nRUN true",
            "production frontend asset reset must immediately precede the handoff",
        ),
    ),
)
def test_node24_frontend_builder_guard_requires_adjacent_asset_reset(
    replacement: str,
    expected_error: str,
) -> None:
    """The final handoff must immediately follow its structural destination reset."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    mutated = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        replacement,
        1,
    )

    errors = _node24_frontend_builder_contract_errors(mutated)

    assert expected_error in errors


def test_node24_frontend_builder_guard_rejects_absorbed_asset_reset() -> None:
    """A prior continuation cannot absorb and short-circuit the reset instruction."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    absorbed = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "WORKDIR /srv",
                "RUN mkdir -p frontend && printf 'seeded' > frontend/extra.js && true || \\",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(absorbed)

    assert "production frontend asset reset must be an independent logical instruction" in errors


def test_node24_frontend_builder_guard_ignores_late_escape_directive() -> None:
    """An escape comment after the header cannot change Docker continuation rules."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    late_escape = dockerfile.replace(
        "# Multi-stage image: pinned Caddy build + Vite build → hardened Caddy SPA shell.",
        "\n".join(
            (
                "# Multi-stage image: pinned Caddy build + Vite build → hardened Caddy SPA shell.",
                "# escape=`",
            )
        ),
        1,
    )
    absorbed = late_escape.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "WORKDIR /srv",
                "RUN mkdir -p frontend && printf 'seeded' > frontend/extra.js && true || \\",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(absorbed)

    assert "production frontend asset reset must be an independent logical instruction" in errors


def test_node24_frontend_builder_guard_rejects_final_stage_heredoc() -> None:
    """Heredoc data cannot impersonate the reset and handoff instructions."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    disguised = dockerfile.replace(
        "\n".join(NODE24_FRONTEND_ASSET_WRITE_LINES),
        "\n".join(
            (
                "RUN <<'#OUTER'",
                ": <<'#INNER'",
                NODE24_FRONTEND_ASSET_RESET_LINE,
                NODE24_FRONTEND_ASSET_COPY_LINE,
                "#INNER",
                "#OUTER",
            )
        ),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(disguised)

    assert NODE24_UNSUPPORTED_HEREDOC_ERROR in errors


def test_node24_frontend_builder_guard_rejects_split_final_stage_heredoc() -> None:
    """A continued heredoc operator cannot turn reset and handoff into data."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    disguised = dockerfile.replace(
        "\n".join(NODE24_FRONTEND_ASSET_WRITE_LINES),
        "\n".join(
            (
                "RUN <\\",
                "<'#OUTER'",
                ": <\\",
                "<'#INNER'",
                NODE24_FRONTEND_ASSET_RESET_LINE,
                NODE24_FRONTEND_ASSET_COPY_LINE,
                "#INNER",
                "#OUTER",
            )
        ),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(disguised)

    assert NODE24_UNSUPPORTED_HEREDOC_ERROR in errors


def test_node24_frontend_builder_guard_rejects_pre_final_stage_heredoc() -> None:
    """A heredoc cannot turn the apparent final stage and handoff into data."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    runtime_stage = next(line for line in dockerfile.splitlines() if line.startswith("FROM caddy:"))
    disguised = dockerfile.replace(
        runtime_stage,
        "\n".join(("RUN <<'#OUTER'", ": <<'#INNER'", runtime_stage)),
        1,
    ).replace(
        NODE24_FRONTEND_ASSET_COPY_LINE,
        "\n".join((NODE24_FRONTEND_ASSET_COPY_LINE, "#INNER", "#OUTER")),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(disguised)

    assert NODE24_UNSUPPORTED_HEREDOC_ERROR in errors


def test_node24_frontend_builder_reset_clears_pre_handoff_seed() -> None:
    """A relative pre-seed remains harmless because the adjacent reset follows it."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    seeded = dockerfile.replace(
        NODE24_FRONTEND_ASSET_RESET_LINE,
        "\n".join(
            (
                "WORKDIR /srv",
                "RUN mkdir -p frontend && printf 'alternate' > front\\",
                "end/extra.js",
                NODE24_FRONTEND_ASSET_RESET_LINE,
            )
        ),
        1,
    )

    assert _node24_frontend_builder_contract_errors(seeded) == []


@pytest.mark.parametrize(
    "asset_write",
    (
        "COPY custom-index.html frontend/index.html",
        "ADD custom-index.html frontend/index.html",
    ),
)
def test_node24_frontend_builder_guard_rejects_relative_asset_overwrite(
    asset_write: str,
) -> None:
    """A final-stage relative COPY or ADD cannot overwrite the served SPA."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    overwritten = dockerfile.replace(
        NODE24_FRONTEND_ASSET_COPY_LINE,
        "\n".join((NODE24_FRONTEND_ASSET_COPY_LINE, "WORKDIR /srv", asset_write)),
        1,
    )

    errors = _node24_frontend_builder_contract_errors(overwritten)

    assert "final-stage COPY/ADD instructions must stay finite and ordered" in errors


def test_node24_frontend_builder_guard_rejects_pre_final_handoff() -> None:
    """The canonical handoff must populate the final production stage."""

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile.caddy-spa").read_text(encoding="utf-8")
    dockerfile_lines = dockerfile.splitlines()
    reset_index = dockerfile_lines.index(NODE24_FRONTEND_ASSET_RESET_LINE)
    handoff_lines = dockerfile_lines[reset_index : reset_index + 2]
    del dockerfile_lines[reset_index : reset_index + 2]
    final_stage_index = max(
        index
        for index, line in enumerate(dockerfile_lines)
        if re.match(r"\s*FROM\s+", line, flags=re.IGNORECASE)
    )
    dockerfile_lines[final_stage_index:final_stage_index] = handoff_lines
    relocated = "\n".join(dockerfile_lines)

    errors = _node24_frontend_builder_contract_errors(relocated)

    assert "production frontend asset handoff must belong to the final stage" in errors


def _github_workflow_glob_matches(value: str, pattern: str) -> bool:
    """Match the bounded GitHub ``*``/``**`` forms without crossing slashes."""

    assert not any(token in pattern for token in ("?", "[", "]", "\\"))
    regex_parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            regex_parts.append(".*")
            index += 2
            continue
        character = pattern[index]
        regex_parts.append("[^/]*" if character == "*" else re.escape(character))
        index += 1
    return re.fullmatch("".join(regex_parts), value) is not None


def _workflow_patterns_match(value: str, patterns: list[object]) -> bool:
    """Return GitHub-style ordered include/exclude matching for one known value."""

    matched = False
    for pattern in patterns:
        assert isinstance(pattern, str)
        excluded = pattern.startswith("!")
        candidate = pattern.removeprefix("!")
        if _github_workflow_glob_matches(value, candidate):
            matched = not excluded
    return matched


def _assert_node24_frontend_builder_workflow_contract(
    workflow: dict[str, object],
) -> None:
    """Assert the finite workflow carriers that keep the Node guard blocking."""

    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)

    workflow_env = workflow["env"]
    assert isinstance(workflow_env, dict)
    assert "PYTEST_ADDOPTS" not in workflow_env

    workflow_defaults = workflow.get("defaults", {})
    assert isinstance(workflow_defaults, dict)
    workflow_run_defaults = workflow_defaults.get("run", {})
    assert isinstance(workflow_run_defaults, dict)
    assert "shell" not in workflow_run_defaults

    dockerfile_path = "frontend/Dockerfile.caddy-spa"
    for event_name in ("pull_request", "push"):
        event = on_section[event_name]
        assert isinstance(event, dict)
        branches = event["branches"]
        assert isinstance(branches, list)
        assert _workflow_patterns_match(
            "main", branches
        ), f"{event_name} must run for the main branch"
        paths = event["paths"]
        assert isinstance(paths, list)
        assert _workflow_patterns_match(
            dockerfile_path, paths
        ), f"{event_name} must route {dockerfile_path} through Frontend CI"

    pull_request_event = on_section["pull_request"]
    assert isinstance(pull_request_event, dict)
    pull_request_types = pull_request_event.get("types")
    if pull_request_types is not None:
        assert isinstance(pull_request_types, list)
        assert {"opened", "synchronize", "reopened"}.issubset(pull_request_types)

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["build-and-test"]
    assert isinstance(job, dict)
    assert "if" not in job
    assert "continue-on-error" not in job

    defaults = job["defaults"]
    assert isinstance(defaults, dict)
    run_defaults = defaults["run"]
    assert isinstance(run_defaults, dict)
    assert "shell" not in run_defaults

    job_env = job["env"]
    assert isinstance(job_env, dict)
    assert "PYTEST_ADDOPTS" not in job_env

    steps = job["steps"]
    assert isinstance(steps, list)
    build_steps = [
        candidate
        for candidate in steps
        if isinstance(candidate, dict) and candidate.get("name") == "Build frontend"
    ]
    assert len(build_steps) == 1
    build_step = build_steps[0]
    assert build_step["run"] == "npm run build"
    for forbidden_key in ("if", "continue-on-error", "shell", "working-directory"):
        assert forbidden_key not in build_step

    step = _job_step_by_name(
        workflow,
        job_id="build-and-test",
        step_name="Run frontend builder governance guard",
    )
    assert set(step) == {"name", "run"}
    assert step["run"] == (
        "cd ..\n"
        "python -m pytest -q \\\n"
        "  tests/test_ci_workflow_pr_size_governance_contract.py \\\n"
        "  -k node24\n"
    )


def test_node24_frontend_builder_guard_runs_for_dockerfile_changes() -> None:
    """Frontend CI must execute the bounded guard on Dockerfile-only changes."""

    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    _assert_node24_frontend_builder_workflow_contract(workflow)


@pytest.mark.parametrize(
    "mutation",
    (
        "pull_request_paths",
        "push_paths",
        "pull_request_path_exclusion",
        "push_path_exclusion",
        "pull_request_root_star_paths",
        "push_root_star_paths",
        "pull_request_branches",
        "push_branches",
        "pull_request_types",
        "step_if",
        "step_continue_on_error",
        "job_continue_on_error",
        "step_shell",
        "job_default_shell",
        "workflow_default_shell",
        "workflow_pytest_collect_only",
        "step_pytest_collect_only",
        "job_pytest_collect_only",
        "build_step_direct_vite",
        "build_step_duplicate",
        "build_step_if",
        "build_step_continue_on_error",
        "build_step_shell",
        "build_step_working_directory",
    ),
)
def test_node24_frontend_builder_workflow_guard_rejects_disabled_wiring(
    mutation: str,
) -> None:
    """Every bounded trigger or fail-open carrier must make the guard fail."""

    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["build-and-test"]
    assert isinstance(job, dict)
    step = _job_step_by_name(
        workflow,
        job_id="build-and-test",
        step_name="Run frontend builder governance guard",
    )
    build_step = _job_step_by_name(
        workflow,
        job_id="build-and-test",
        step_name="Build frontend",
    )

    if mutation in {"pull_request_paths", "push_paths"}:
        event_name = mutation.removesuffix("_paths")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["paths"] = [".nvmrc"]
    if mutation in {"pull_request_path_exclusion", "push_path_exclusion"}:
        event_name = mutation.removesuffix("_path_exclusion")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["paths"] = ["frontend/**", "!frontend/Dockerfile.caddy-spa"]
    if mutation in {"pull_request_root_star_paths", "push_root_star_paths"}:
        event_name = mutation.removesuffix("_root_star_paths")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["paths"] = ["*"]
    if mutation in {"pull_request_branches", "push_branches"}:
        event_name = mutation.removesuffix("_branches")
        event = on_section[event_name]
        assert isinstance(event, dict)
        event["branches"] = ["feat/**"]
    if mutation == "pull_request_types":
        event = on_section["pull_request"]
        assert isinstance(event, dict)
        event["types"] = ["opened", "reopened", "edited"]
    if mutation == "step_if":
        step["if"] = "${{ false }}"
    if mutation == "step_continue_on_error":
        step["continue-on-error"] = True
    if mutation == "job_continue_on_error":
        job["continue-on-error"] = True
    if mutation == "step_shell":
        step["shell"] = "bash -c '{0} || true'"
    if mutation == "job_default_shell":
        defaults = job["defaults"]
        assert isinstance(defaults, dict)
        run_defaults = defaults["run"]
        assert isinstance(run_defaults, dict)
        run_defaults["shell"] = "bash -c '{0} || true'"
    if mutation == "workflow_default_shell":
        workflow["defaults"] = {"run": {"shell": "bash -c '{0} || true'"}}
    if mutation == "workflow_pytest_collect_only":
        workflow_env = workflow["env"]
        assert isinstance(workflow_env, dict)
        workflow_env["PYTEST_ADDOPTS"] = "--collect-only"
    if mutation == "step_pytest_collect_only":
        step["env"] = {"PYTEST_ADDOPTS": "--collect-only"}
    if mutation == "job_pytest_collect_only":
        job_env = job["env"]
        assert isinstance(job_env, dict)
        job_env["PYTEST_ADDOPTS"] = "--collect-only"
    if mutation == "build_step_direct_vite":
        build_step["run"] = "npx vite build"
    if mutation == "build_step_duplicate":
        steps = job["steps"]
        assert isinstance(steps, list)
        steps.append(dict(build_step))
    if mutation == "build_step_if":
        build_step["if"] = "${{ false }}"
    if mutation == "build_step_continue_on_error":
        build_step["continue-on-error"] = True
    if mutation == "build_step_shell":
        build_step["shell"] = "bash -c '{0} || true'"
    if mutation == "build_step_working_directory":
        build_step["working-directory"] = "."

    with pytest.raises(AssertionError):
        _assert_node24_frontend_builder_workflow_contract(workflow)


def _extract_shell_conditional_block(
    script_text: str,
    branch_marker: str,
    next_marker: str,
) -> str:
    """Return the shell branch body between two explicit workflow markers."""

    start_anchor = f"{branch_marker}\n"
    end_anchor = f"\n{next_marker}"
    assert start_anchor in script_text, f"Missing shell branch marker: {branch_marker}"
    branch_tail = script_text.split(start_anchor, maxsplit=1)[1]
    assert end_anchor in branch_tail, f"Missing shell branch boundary after {branch_marker}"
    return branch_tail.split(end_anchor, maxsplit=1)[0]


def test_nightly_full_tests_uses_process_shards_without_xdist() -> None:
    """Nightly full coverage keeps slow tests but avoids xdist worker shutdown hangs."""

    workflow = _load_workflow(NIGHTLY_FULL_TESTS_WORKFLOW_PATH)
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["tests"]
    assert "continue-on-error" not in job

    checkout_step = _job_step_by_name(workflow, job_id="tests", step_name="Checkout")
    assert checkout_step["uses"] == f"actions/checkout@{CHECKOUT_V7_SHA}"
    assert checkout_step["with"]["fetch-depth"] == 0
    assert checkout_step["with"]["persist-credentials"] is False

    test_step = _job_step_by_name(
        workflow,
        job_id="tests",
        step_name="Run full test suite with coverage (include slow/MC)",
    )
    run_script = test_step["run"]
    assert isinstance(run_script, str)
    env = test_step["env"]
    assert isinstance(env, dict)
    assert "continue-on-error" not in test_step

    assert env["BAYESIAN_PERSIST"] == "1"
    assert env["BAYESIAN_HISTORY_PATH"] == "/tmp/test_execution_history.json"
    assert env["MC_SEED"] == "2025"
    assert env["MC_SAMPLES"] == "40"
    assert env["MC_SAMPLES_FEW"] == "15"
    assert env["MAIN_TEST_SHARDS"] == "16"
    assert env["MAIN_TEST_MAX_PARALLEL"] == "4"
    assert env["MAIN_TEST_SHARD_TIMEOUT_SECONDS"] == "4800"
    assert env["MAIN_TEST_COVERAGE_TIMEOUT_SECONDS"] == "1200"

    assert "set -euo pipefail" in run_script
    assert "python scripts/ci/run_main_test_shards.py" in run_script
    assert '--python-version "3.13"' in run_script
    assert '--shard-count "${MAIN_TEST_SHARDS}"' in run_script
    assert '--max-parallel "${MAIN_TEST_MAX_PARALLEL}"' in run_script
    assert '--marker-expression "not demo"' in run_script
    assert '--durations-min "1.0"' in run_script
    assert '--report-chars "fEsxXw"' in run_script
    assert "--htmlcov" in run_script
    assert "TEST_STEP_STARTED_AT=" in run_script
    assert "MAIN_TEST_COVERAGE_TIMEOUT_SECONDS=" in run_script
    assert "TEST_STEP_FINISHED_AT=" in run_script
    assert "set +e" in run_script
    assert "test_exit_code=$?" in run_script
    assert "set -e" in run_script
    assert 'exit "$test_exit_code"' in run_script

    assert "pytest -c pyproject.toml" not in run_script
    assert "-n auto" not in run_script
    assert "--dist=loadgroup" not in run_script
    assert "--cov-fail-under=97" not in run_script

    coverage_upload = _job_step_by_name(
        workflow,
        job_id="tests",
        step_name="Upload coverage artifact",
    )
    html_upload = _job_step_by_name(
        workflow,
        job_id="tests",
        step_name="Upload HTML coverage artifact",
    )
    assert coverage_upload["with"] == {"name": "coverage-xml", "path": "coverage.xml"}
    assert html_upload["with"] == {"name": "htmlcov", "path": "htmlcov"}


def test_pr_size_governance_reruns_when_trusted_approval_labels_change() -> None:
    """Trusted scope labels must trigger fresh PR-size governance event payloads."""

    workflow = _load_ci_workflow()
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)
    pull_request_section = on_section["pull_request"]
    assert isinstance(pull_request_section, dict)
    event_types = pull_request_section["types"]
    assert isinstance(event_types, list)

    assert "labeled" in event_types
    assert "unlabeled" in event_types


def test_pr_size_governance_uses_pull_request_head_sha() -> None:
    """Guard against merge-SHA inflation in PR-size governance diff calculation."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    pr_scope_guard_section = _extract_section(
        workflow_text,
        "pr_scope_guard:",
        "      - name: Design invariant guard",
    )

    assert "permissions:" in pr_scope_guard_section
    assert "contents: read" in pr_scope_guard_section
    assert "pull-requests: read" in pr_scope_guard_section
    assert "python3 scripts/ci/check_pr_size_governance.py \\" in pr_scope_guard_section
    assert '--base-sha "${{ github.event.pull_request.base.sha }}" \\' in pr_scope_guard_section
    assert '--head-sha "${{ github.event.pull_request.head.sha }}" \\' in pr_scope_guard_section
    assert '--event-path "$GITHUB_EVENT_PATH"' in pr_scope_guard_section
    assert '--head-sha "${{ github.sha }}" \\' not in pr_scope_guard_section
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in pr_scope_guard_section
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in pr_scope_guard_section


def test_pr_risk_profile_uses_pull_request_head_sha() -> None:
    """Guard contract-risk routing against merge-SHA based diff calculations."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    risk_profile_section = _extract_section(
        workflow_text,
        "      - name: Build CI risk profile",
        "\n  pr_scope_guard:",
    )

    assert "python3 scripts/ci/ci_risk_profile.py \\" in risk_profile_section
    assert 'BASE_SHA="${{ github.event.pull_request.base.sha }}"' in risk_profile_section
    assert 'HEAD_SHA="${{ github.event.pull_request.head.sha }}"' in risk_profile_section
    assert '--base-sha "${BASE_SHA}" \\' in risk_profile_section
    assert '--head-sha "${HEAD_SHA}" \\' in risk_profile_section


def test_docs_phase1_gates_include_schema_only_contract_changes() -> None:
    """SC-G5 schema-only edits must still run the docs Phase1 validator."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    docs_phase1_section = _extract_job_section(workflow_text, "  docs_phase1_gates:")

    assert "PHASE1_CHANGED_FILES=()" in docs_phase1_section
    assert "'docs/orchestration/contracts/*.schema.json'" in docs_phase1_section
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json'" in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "':(glob)docs/orchestration/contracts/philosophy_alignment_rules/**/*.json'"
        in docs_phase1_section
    )
    assert (
        "docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json" in docs_phase1_section
    )
    assert (
        "'tests/fixtures/orchestration/philosophy_admission_claim_oracle.json'"
        in docs_phase1_section
    )
    assert (
        "No changed markdown or Phase1 schema files; skipping docs Phase1 gates."
        in docs_phase1_section
    )
    assert (
        'if [ "${PR4_PRECONDITION_CHANGED}" -eq 0 ] && [ "${PR5_SOURCE_CORPUS_CHANGED}" -eq 0 ] && [ "${#PHASE1_CHANGED_FILES[@]}" -eq 0 ] && [ "${#LINT_MD[@]}" -eq 0 ]; then'
        in docs_phase1_section
    )
    assert (
        "No changed docs markdown or Phase1 schema files; skipping docs Phase1 validator."
        in docs_phase1_section
    )
    assert (
        'python scripts/ci/check_docs_phase1_gates.py --files "${PHASE1_CHANGED_FILES[@]}"'
        in docs_phase1_section
    )
    assert "PR4_PRECONDITION_CHANGED=0" in docs_phase1_section
    assert "PR5_SOURCE_CORPUS_CHANGED=0" in docs_phase1_section
    assert "git rev-parse HEAD^2 >/dev/null 2>&1" in (docs_phase1_section)
    assert 'BASE_REF="$(git rev-parse HEAD^1)"' in (docs_phase1_section)
    assert 'BASE_REF="${{ github.event.pull_request.base.sha }}"' in (docs_phase1_section)
    assert docs_phase1_section.index("git rev-parse HEAD^2") < (
        docs_phase1_section.index('BASE_REF="$(git rev-parse HEAD^1)"')
    )
    assert docs_phase1_section.index('BASE_REF="$(git rev-parse HEAD^1)"') < (
        docs_phase1_section.index("github.event.pull_request.base.sha")
    )
    assert (
        'git diff --name-status -z --find-renames --find-copies-harder --diff-filter=ACDMRT "$BASE_REF"...HEAD'
        in (docs_phase1_section)
    )
    assert 'case "$status" in' in docs_phase1_section
    assert "R*|C*)" in docs_phase1_section
    assert 'CHANGED_PATHS+=("$old_path" "$new_path")' in docs_phase1_section
    assert 'CHANGED_PATHS+=("$path")' in docs_phase1_section
    for pr4_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json",
        "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json",
        "tests/fixtures/orchestration/philosophy_admission_claim_oracle.json",
        "docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json",
        "docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json",
        "docs/orchestration/contracts/philosophy_alignment_rules/*.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR4_GATE_OPEN_PRECONDITIONS_PACKET_2026-05-21.md",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        "scripts/ci/check_philosophy_gate_open_preconditions.py",
        "tests/test_philosophy_gate_open_preconditions.py",
    ):
        assert pr4_companion_input in docs_phase1_section
    for pr5_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json",
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        "scripts/ci/check_philosophy_source_corpus_index.py",
        "tests/test_philosophy_source_corpus_index.py",
    ):
        assert pr5_companion_input in docs_phase1_section
    pr5_case = _extract_section(
        docs_phase1_section,
        '              case "$path" in\n'
        "                docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json",
        "                  PR5_SOURCE_CORPUS_CHANGED=1",
    )
    for pr5_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        "scripts/ci/check_philosophy_source_corpus_index.py",
        "tests/test_philosophy_source_corpus_index.py",
    ):
        assert pr5_companion_input in pr5_case
    for unrelated_pr5_trigger in (
        "docs/roadmap/BACKLOG_LEDGER.md",
        "scripts/ci/check_docs_phase1_gates.py",
    ):
        assert unrelated_pr5_trigger not in pr5_case
    assert (
        "python scripts/ci/check_philosophy_gate_open_preconditions.py --check --files"
        in docs_phase1_section
    )
    assert (
        'python scripts/ci/check_philosophy_source_corpus_index.py --check \\\n              --base-ref "$BASE_REF" --files "${ALL_CHANGED_FILES[@]}"'
        in docs_phase1_section
    )
    assert (
        'python scripts/ci/check_docs_phase1_gates.py --files "${CHANGED_DOCS[@]}"'
        not in docs_phase1_section
    )


@pytest.mark.parametrize(
    ("operation", "source_path", "expected_trigger"),
    [
        ("copy", "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json", "1"),
        ("copy", "docs/evidence/unrelated.json", "0"),
        ("modify", "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md", "1"),
        (
            "modify",
            "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
            "1",
        ),
        ("modify", "docs/evidence/unrelated.json", "0"),
    ],
)
def test_docs_phase1_corpus_input_discovery_executes_workflow_path_loop(
    tmp_path: Path, operation: str, source_path: str, expected_trigger: str
) -> None:
    git = shutil.which("git")
    bash = shutil.which("bash")
    assert git is not None and bash is not None
    fixture_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    fixture_env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

    def run_git(*args: str) -> str:
        result = subprocess.run(  # nosec B603: resolved Git in test-owned repository (remove-by: 2026-10-31, ref: PR-2446)
            [git, "-C", str(tmp_path), *args],
            check=True,
            capture_output=True,
            text=True,
            env=fixture_env,
        )
        return result.stdout.strip()

    run_git("init", "--quiet")
    source = tmp_path / source_path
    source.parent.mkdir(parents=True)
    source.write_text("safe source corpus evidence\n", encoding="utf-8")
    run_git("add", ".")
    run_git(
        "-c",
        "user.name=CI Test",
        "-c",
        "user.email=ci@example.test",
        "commit",
        "--quiet",
        "-m",
        "base",
    )
    base_ref = run_git("rev-parse", "HEAD")
    destination_path: str | None = None
    if operation == "copy":
        destination_path = "docs/evidence/copied.json"
        destination = tmp_path / destination_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        run_git("add", destination_path)
    else:
        source.write_text("safe updated corpus evidence\n", encoding="utf-8")
        run_git("add", source_path)
    run_git(
        "-c",
        "user.name=CI Test",
        "-c",
        "user.email=ci@example.test",
        "commit",
        "--quiet",
        "-m",
        operation,
    )

    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["docs_phase1_gates"]["steps"]
    run_script = next(step["run"] for step in steps if step.get("name") == "Run Phase1 docs gates")
    start = run_script.index("CHANGED_MD=()")
    end = run_script.index("\n", run_script.index("done < <(git diff --name-status", start))
    path_loop = run_script[start:end]
    assert "--find-copies-harder" in path_loop
    result = subprocess.run(  # nosec B603: resolved Bash runs extracted fixed workflow loop (remove-by: 2026-10-31, ref: PR-2446)
        [
            bash,
            "-c",
            "set -euo pipefail\n"
            + path_loop
            + "\nprintf 'FLAG=%s\\n' \"$PR5_SOURCE_CORPUS_CHANGED\"\n"
            + "printf 'PATH=%s\\n' \"${ALL_CHANGED_FILES[@]}\"\n",
        ],
        cwd=tmp_path,
        env={**fixture_env, "BASE_REF": base_ref},
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"FLAG={expected_trigger}" in result.stdout.splitlines()
    assert f"PATH={source_path}" in result.stdout.splitlines()
    if destination_path is not None:
        assert f"PATH={destination_path}" in result.stdout.splitlines()


def test_semantic_cache_contract_suites_include_philosophy_policy_oracle() -> None:
    """Current-head CI must execute the Philosophy policy/oracle drift regressions."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert workflow_text.count("tests/test_philosophy_admission_dry_run_report.py \\") >= 2
    assert workflow_text.count("tests/test_philosophy_admission_policy_oracle.py \\") >= 2
    assert workflow_text.count("tests/test_verification_provenance_admission_report.py \\") >= 2
    assert (
        workflow_text.count("tests/core/ai/test_semantic_cache_offline_admission_runner.py \\") >= 2
    )
    assert (
        workflow_text.count("tests/core/ai/test_semantic_cache_shadow_admission_harness.py \\") >= 2
    )


def test_changes_job_uses_node24_paths_filter_pin_and_keeps_ios_filters() -> None:
    """Guard the Node 24 paths-filter migration and iOS path-gating contract."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    _assert_yaml_mapping_keys_are_unique(workflow_text)
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    changes = jobs["changes"]
    assert isinstance(changes, dict)
    assert changes["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
    }
    outputs = changes["outputs"]
    assert isinstance(outputs, dict)
    assert outputs["ios"] == "${{ steps.filter.outputs.ios }}"
    steps = changes["steps"]
    assert isinstance(steps, list)

    filter_steps = [step for step in steps if step.get("id") == "filter"]
    assert len(filter_steps) == 1
    filter_step = filter_steps[0]
    assert filter_step["uses"] == f"dorny/paths-filter@{PATHS_FILTER_NODE24_SHA}"

    with_section = filter_step["with"]
    assert isinstance(with_section, dict)
    assert with_section["token"] == "${{ secrets.GITHUB_TOKEN }}"
    filters = with_section["filters"]
    assert isinstance(filters, str)
    _assert_yaml_mapping_keys_are_unique(filters)
    parsed_filters = yaml.safe_load(filters)
    assert isinstance(parsed_filters, dict)
    ios_filters = parsed_filters["ios"]
    assert ios_filters == [
        "ios/**",
        ".github/workflows/**",
        ".github/actions/**",
        "scripts/ios_test_targets.sh",
        "scripts/ci/select_ios_simulator.py",
        "scripts/ci/check_ios_swift_syntax.sh",
        "scripts/release/check_ios_appstore_verify.py",
    ]
    for path, expected in (
        ("scripts/ci/select_ios_simulator.py", True),
        ("scripts/release/check_ios_appstore_verify.py", True),
        ("scripts/release/release_manifest.py", False),
    ):
        assert any(fnmatch.fnmatchcase(path, pattern) for pattern in ios_filters) is expected

    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    for path in ios_filters:
        assert f"`{path}`" in agents_text

    assert "Xcode 27.0 (matches the current iOS SDK lane)" in agents_text
    assert "exact Xcode 27.0 fallback at `/Applications/Xcode.app`" in agents_text
    assert "Xcode 16.x (matches project format)" not in agents_text
    assert "Xcode 16.4 → 16.3 → 16.2" not in agents_text

    for job_id in ("ios-tests", "ios-ui-smoke"):
        job = jobs[job_id]
        assert isinstance(job, dict)
        job_steps = job["steps"]
        assert isinstance(job_steps, list)
        select_xcode_steps = [step for step in job_steps if step.get("id") == "select-xcode"]
        assert len(select_xcode_steps) == 1
        select_xcode_run = select_xcode_steps[0]["run"]
        assert isinstance(select_xcode_run, str)
        executable_xcode_lines = "\n".join(
            line.strip()
            for line in select_xcode_run.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        priority_positions = [
            executable_xcode_lines.index(f'"/Applications/Xcode_{version}.app/Contents/Developer"')
            for version in ("27.0.0", "27.0")
        ]
        assert priority_positions == sorted(priority_positions)
        assert 'if [ "$XCODE_VERSION" != "27.0" ]; then' in executable_xcode_lines
        assert 'if [ "$sdk_version" != "27.0" ]; then' in executable_xcode_lines
        assert "Apple Swift version 6.4" in executable_xcode_lines
        assert (
            'python3 ../scripts/ci/select_ios_simulator.py --family "${{ matrix.family }}"'
            in job_steps[3]["run"]
        )
        assert "simctl list devices" not in job_steps[3]["run"]
        assert job["runs-on"] == "xcode-27"


def test_xcode27_actionlint_preview_label_has_exact_four_job_uses() -> None:
    config = yaml.safe_load(ACTIONLINT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["self-hosted-runner"]["labels"] == ["pulseplate-prod", "xcode-27"]

    expected = {
        (CI_WORKFLOW_PATH, "ios-tests"),
        (CI_WORKFLOW_PATH, "ios-ui-smoke"),
        (IOS_APPSTORE_ASSETS_WORKFLOW_PATH, "validate-assets"),
        (IOS_APPSTORE_ASSETS_WORKFLOW_PATH, "upload-assets"),
    }
    observed = {
        (path, job_id)
        for path in _active_workflow_paths()
        for job_id, job in _load_workflow(path)["jobs"].items()
        if job.get("runs-on") == "xcode-27"
    }
    assert observed == expected


def test_node24_artifact_and_script_action_pins_use_verified_commit_shas() -> None:
    """Guard remaining Node 20 action migrations against tag-object drift."""

    download_workflows = {
        CI_WORKFLOW_PATH: 10,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH: 1,
        NIGHTLY_WORKFLOW_PATH: 1,
    }
    expected_download_line = (
        f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA} # v8.0.1 / Node 24"
    )

    observed_download_steps = 0
    for workflow_path, expected_count in download_workflows.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_download_line) == expected_count
        assert f"actions/download-artifact@{OLD_DOWNLOAD_ARTIFACT_SHA}" not in workflow_text

        for _job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/download-artifact@"):
                observed_download_steps += 1
                assert uses == f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA}"

    assert observed_download_steps == sum(download_workflows.values())

    pr_automation_text = PR_AUTOMATION_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        f"actions/github-script@{GITHUB_SCRIPT_NODE24_SHA} # v9.0.0 / Node 24" in pr_automation_text
    )
    assert f"actions/github-script@{OLD_GITHUB_SCRIPT_SHA}" not in pr_automation_text
    assert GITHUB_SCRIPT_V9_TAG_OBJECT_SHA not in pr_automation_text


def test_codecov_action_pin_uses_node24_transitive_github_script() -> None:
    """Guard Codecov uploads against reintroducing the old Node 20 github-script dependency."""

    expected_codecov_line = (
        f"codecov/codecov-action@{CODECOV_ACTION_NODE24_SHA} "
        "# v6.0.0 / Node 24 transitive github-script"
    )
    workflow_counts = {
        CI_WORKFLOW_PATH: 3,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
    }

    observed_codecov_steps = []
    for workflow_path, expected_count in workflow_counts.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_codecov_line) == expected_count
        assert f"codecov/codecov-action@{OLD_CODECOV_ACTION_SHA}" not in workflow_text

        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("codecov/codecov-action@"):
                observed_codecov_steps.append((workflow_path, job_id, step))
                assert uses == f"codecov/codecov-action@{CODECOV_ACTION_NODE24_SHA}"

    assert len(observed_codecov_steps) == sum(workflow_counts.values())


def test_cd_test_published_image_health_smoke_is_trusted_and_fail_closed() -> None:
    """Keep the privileged published-image smoke exact, bounded, and diagnostic."""

    workflow_text = CD_TEST_WORKFLOW_PATH.read_text(encoding="utf-8")
    trigger_section = _extract_section(
        workflow_text,
        "name: CD-Test\n",
        "\npermissions:\n",
    ).strip()
    assert trigger_section == (
        "on:\n"
        "  workflow_run:\n"
        '    workflows: ["Docker Build and Push"]\n'
        "    types: [completed]\n"
        "    branches: [ main ]\n"
        "  push:\n"
        "    tags:\n"
        "      - 'v*'"
    )

    workflow = _load_workflow(CD_TEST_WORKFLOW_PATH)
    assert workflow["permissions"] == {
        "contents": "read",
        "packages": "read",
        "id-token": "write",
    }

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    validate_job = jobs["validate-environment"]
    assert isinstance(validate_job, dict)
    assert validate_job["timeout-minutes"] == (
        "${{ fromJSON(vars.CD_TEST_VALIDATE_TIMEOUT_MINUTES || '10') }}"
    )
    assert validate_job["environment"] == {"name": "staging"}

    trusted_run_condition = validate_job["if"]
    assert isinstance(trusted_run_condition, str)
    assert trusted_run_condition == (
        "${{\n"
        "  github.event_name == 'workflow_run' &&\n"
        "  github.event.workflow_run.conclusion == 'success' &&\n"
        "  github.event.workflow_run.event == 'push' &&\n"
        "  github.event.workflow_run.head_branch == 'main' &&\n"
        "  github.event.workflow_run.head_repository.full_name == github.repository\n"
        "}}"
    )

    validate_steps = validate_job["steps"]
    assert isinstance(validate_steps, list)
    validate_checkout = validate_steps[0]
    assert isinstance(validate_checkout, dict)
    assert validate_checkout["uses"] == f"actions/checkout@{CHECKOUT_V7_SHA}"
    assert validate_checkout["with"] == {
        "ref": "${{ github.event.workflow_run.head_sha }}",
        "persist-credentials": False,
    }

    exact_image_ref = (
        "ghcr.io/${{ steps.image-name.outputs.image_name }}:"
        "${{ github.event.workflow_run.head_sha }}"
    )
    assert workflow_text.count(exact_image_ref) == 2

    pull_step = _job_step_by_name(
        workflow,
        job_id="validate-environment",
        step_name="Test Docker image pull",
    )
    pull_env = pull_step["env"]
    assert isinstance(pull_env, dict)
    assert pull_env == {
        "GHCR_READ_TOKEN": "${{ secrets.GHCR_READ_TOKEN }}",
        "IMAGE_REF": exact_image_ref,
        "REPOSITORY_OWNER": "${{ github.repository_owner }}",
    }
    pull_script = pull_step["run"]
    assert isinstance(pull_script, str)
    assert pull_step.get("continue-on-error") is None
    assert "|| true" not in pull_script
    assert "|| echo" not in pull_script
    assert "${{ secrets." not in pull_script
    assert "${{ secrets.GHCR_READ_TOKEN }}" not in pull_script
    _assert_contains_all_tokens(
        pull_script,
        (
            'if [ -z "${GHCR_READ_TOKEN:-}" ]',
            "printf '%s' \"$GHCR_READ_TOKEN\"",
            '--username "$REPOSITORY_OWNER"',
            "--password-stdin",
            'docker pull "$IMAGE_REF"',
        ),
    )

    health_step = _job_step_by_name(
        workflow,
        job_id="validate-environment",
        step_name="Test health endpoint locally",
    )
    assert health_step.get("continue-on-error") is None
    assert health_step["env"] == {"IMAGE_REF": exact_image_ref}
    health_script = health_step["run"]
    assert isinstance(health_script, str)
    assert "${{ secrets." not in health_script
    assert "GHCR_READ_TOKEN" not in health_script

    build_workflow = _load_workflow(BUILD_WORKFLOW_PATH)
    build_smoke_step = _job_step_by_name(
        build_workflow,
        job_id="build",
        step_name="Test Docker image",
    )
    build_smoke_script = build_smoke_step["run"]
    assert isinstance(build_smoke_script, str)
    expected_ci_environment = {
        '"${api_key_name}=test_key"',
        '"${allow_dev_api_key_name}=false"',
        '"${export_token_secret_name}=ci-smoke-export-secret"',
        '"${server_salt_name}=StrongServerSaltForCI1234567890!"',
        '"${apple_shared_secret_name}=StrongAppleSharedSecretForCI1234567890!"',
        '"${subscription_db_enabled_name}=true"',
        '"${database_url_name}=sqlite:////app/cache/pulseplate-smoke.db"',
        "APP_ENV=ci",
        "ENVIRONMENT=ci",
    }
    assert _docker_environment_flags(build_smoke_script) == expected_ci_environment
    assert _docker_environment_flags(health_script) == expected_ci_environment
    expected_obfuscated_names = {
        "api_key_name": ("API", "_KEY"),
        "allow_dev_api_key_name": ("ALLOW_DEV_API", "_KEY"),
        "export_token_" + "secret_name": ("EXPORT_TOKEN", "_SECRET"),
        "server_" + "salt_name": ("SERVER", "_SALT"),
        "apple_shared_" + "secret_name": ("APPLE_SHARED", "_SECRET"),
        "subscription_db_enabled_name": ("SUBSCRIPTION_DB", "_ENABLED"),
        "database_" + "url_name": ("DATABASE", "_URL"),
    }
    for variable_name, (prefix, suffix) in expected_obfuscated_names.items():
        assert f'{variable_name}="{prefix}""{suffix}"' in health_script
    _assert_contains_all_tokens(
        health_script,
        (
            "--cap-drop=ALL",
            "--security-opt no-new-privileges",
            '"$IMAGE_REF"',
        ),
    )

    assert "docker run --rm" not in health_script
    assert "-p 127.0.0.1:8000:8000" in health_script
    assert "-p 8000:8000" not in health_script
    assert "Health check failed (expected without frontend)" not in health_script
    assert "|| echo" not in health_script
    assert "|| true" not in health_script
    assert health_script.count("curl -fSs --connect-timeout 2 --max-time 5") == 2
    assert health_script.count("http://localhost:8000/health") == 2
    _assert_contains_all_tokens(
        health_script,
        (
            "trap cleanup EXIT",
            "original_status=$?",
            "trap - EXIT",
            "container_present=false",
            "container_present=true",
            'docker container inspect "$container_name"',
            "docker container ls -a --format '{{.Names}}'",
            'docker rm -f "$container_name"',
            'exit "$original_status"',
            "docker logs --tail 200",
            "max_attempts=30",
            "attempt=1",
            "ready=false",
            'while [ "$attempt" -le "$max_attempts" ]',
            'if [ "$attempt" -eq "$max_attempts" ]',
            "attempt=$((attempt + 1))",
            'if [ "$ready" != "true" ]',
        ),
    )
    assert health_script.index("trap cleanup EXIT") < health_script.index("docker run -d")
    launch_index = health_script.index("if ! docker run -d")
    launch_failure_message_index = health_script.index(
        "Failed to launch health-smoke container",
        launch_index,
    )
    launch_failure_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        launch_failure_message_index,
    )
    launch_failure_exit_index = health_script.index(
        "exit 1",
        launch_failure_diagnostics_index,
    )
    assert launch_index < launch_failure_message_index
    assert launch_failure_message_index < launch_failure_diagnostics_index
    assert launch_failure_diagnostics_index < launch_failure_exit_index
    first_probe_index = health_script.index("if curl -fSs")
    post_probe_liveness_index = health_script.index(
        'if ! docker container inspect "$container_name"',
        first_probe_index,
    )
    early_exit_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        post_probe_liveness_index,
    )
    early_exit_failure_index = health_script.index(
        "exit 1",
        early_exit_diagnostics_index,
    )
    assert first_probe_index < post_probe_liveness_index
    assert post_probe_liveness_index < early_exit_diagnostics_index
    assert early_exit_diagnostics_index < early_exit_failure_index
    timeout_message_index = health_script.index("Health endpoint did not become ready after")
    timeout_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        timeout_message_index,
    )
    timeout_failure_index = health_script.index("exit 1", timeout_diagnostics_index)
    assert timeout_message_index < timeout_diagnostics_index < timeout_failure_index
    final_probe_index = health_script.rindex("curl -fSs --connect-timeout 2 --max-time 5")
    assert final_probe_index > timeout_failure_index
    final_probe_diagnostics_index = health_script.index(
        "show_container_diagnostics",
        final_probe_index,
    )
    final_probe_failure_index = health_script.index(
        "exit 1",
        final_probe_diagnostics_index,
    )
    assert final_probe_index < final_probe_diagnostics_index < final_probe_failure_index

    production_job = jobs["production-validation"]
    assert isinstance(production_job, dict)
    assert production_job["if"] == "startsWith(github.ref, 'refs/tags/v')"
    assert production_job["environment"] == {"name": "production"}
    production_steps = production_job["steps"]
    assert isinstance(production_steps, list)
    production_checkout = production_steps[0]
    assert isinstance(production_checkout, dict)
    assert production_checkout["uses"] == f"actions/checkout@{CHECKOUT_V7_SHA}"
    assert "with" not in production_checkout
    production_validation = _job_step_by_name(
        workflow,
        job_id="production-validation",
        step_name="Validate production environment",
    )
    assert production_validation["env"] == {
        "ENVIRONMENT": "production",
        "GHCR_READ_TOKEN": "${{ secrets.GHCR_READ_TOKEN }}",
        "LLM_ENABLED": "false",
    }


def test_node24_checkout_and_docker_action_pins_use_verified_commit_shas() -> None:
    assert set(TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW) == {
        BUILD_WORKFLOW_PATH,
        CD_WORKFLOW_PATH,
        TRIVY_WORKFLOW_PATH,
    }
    """Guard remaining Node 20 workflow action migrations against regression."""

    active_workflow_text = "\n".join(
        path.read_text(encoding="utf-8") for path in _active_workflow_paths()
    )
    old_node20_shas = (
        OLD_CHECKOUT_NODE20_SHA,
        OLD_CHECKOUT_V6_NODE20_SHA,
        OLD_DOCKER_SETUP_BUILDX_SHA,
        OLD_DOCKER_LOGIN_SHA,
        OLD_DOCKER_METADATA_SHA,
        OLD_TRIVY_ACTION_SHA,
        OLD_TRIVY_INTERNAL_CACHE_NODE20_SHA,
        OLD_SETUP_GO_SHA,
        OLD_UPLOAD_ARTIFACT_SHA,
        OLD_UPLOAD_ARTIFACT_V7_SHA,
    )
    for old_sha in old_node20_shas:
        assert old_sha not in active_workflow_text

    forbidden_override_env_vars = (
        "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION",
        "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24",
        "CI_ALLOW_MERGE_OVERRIDE",
    )
    for env_var in forbidden_override_env_vars:
        assert env_var not in active_workflow_text

    checkout_workflows = {
        ACTIONLINT_WORKFLOW_PATH: 1,
        CD_TEST_WORKFLOW_PATH: 2,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
        CODEQL_WORKFLOW_PATH: 1,
        GREENLIGHT_IOS_WORKFLOW_PATH: 1,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH: 3,
        SECURITY_WORKFLOW_PATH: 1,
    }
    expected_checkout_line = f"actions/checkout@{CHECKOUT_V7_SHA} # v7.0.1 / Node 24"

    observed_checkout_steps = 0
    for workflow_path, expected_count in checkout_workflows.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_checkout_line) == expected_count

        for _job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/checkout@"):
                observed_checkout_steps += 1
                assert uses == f"actions/checkout@{CHECKOUT_V7_SHA}"

    assert observed_checkout_steps == sum(checkout_workflows.values())

    expected_docker_lines = {
        BUILD_WORKFLOW_PATH: {
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA} # v4.1.0 / Node 24": 2,
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA} # v4.2.0 / Node 24": 1,
            f"docker/metadata-action@{DOCKER_METADATA_NODE24_SHA} # v6.1.0 / Node 24": 1,
        },
        CD_WORKFLOW_PATH: {
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA} # v4.1.0 / Node 24": 2,
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA} # v4.2.0 / Node 24": 2,
        },
        TRIVY_WORKFLOW_PATH: {
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA} # v4.1.0 / Node 24": 1,
        },
    }
    for workflow_path, expected_counts in expected_docker_lines.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for expected_line, expected_count in expected_counts.items():
            assert workflow_text.count(expected_line) == expected_count

    expected_trivy_lines = {
        BUILD_WORKFLOW_PATH: {
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA} "
            "# v0.36.0 / Node 24 cache path": 2,
        },
        CD_WORKFLOW_PATH: {
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA} "
            "# v0.36.0 / Node 24 cache path": 2,
        },
        TRIVY_WORKFLOW_PATH: {
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA} "
            "# v0.36.0 / Node 24 cache path": 1,
        },
    }
    for workflow_path, expected_counts in expected_trivy_lines.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for expected_line, expected_count in expected_counts.items():
            assert workflow_text.count(expected_line) == expected_count

    observed_docker_contracts = []
    for workflow_path in (BUILD_WORKFLOW_PATH, CD_WORKFLOW_PATH, TRIVY_WORKFLOW_PATH):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.startswith("docker/"):
                continue
            if uses.startswith("docker/build-push-action@"):
                continue
            observed_docker_contracts.append(
                (
                    str(workflow_path.relative_to(REPO_ROOT)),
                    job_id,
                    step.get("name"),
                    uses,
                    step.get("with"),
                    step.get("if"),
                    step.get("env"),
                    step.get("continue-on-error"),
                )
            )

    assert observed_docker_contracts == [
        (
            ".github/workflows/build.yml",
            "build",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Extract metadata",
            f"docker/metadata-action@{DOCKER_METADATA_NODE24_SHA}",
            {
                "images": ("${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"),
                "tags": (
                    "type=raw,value=${{ github.sha }}\n"
                    "type=raw,value=sha-${{ github.sha }}\n"
                    "type=ref,event=branch\n"
                    "type=semver,pattern={{version}}\n"
                    "type=semver,pattern={{major}}.{{minor}}\n"
                    "type=raw,value=latest,enable={{is_default_branch}}\n"
                ),
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Log in to GHCR",
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA}",
            {
                "registry": "${{ env.REGISTRY }}",
                "username": "${{ github.repository_owner }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Log in to Container Registry",
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA}",
            {
                "registry": "ghcr.io",
                "username": "${{ github.actor }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build-production",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build-production",
            "Log in to Container Registry",
            f"docker/login-action@{DOCKER_LOGIN_NODE24_SHA}",
            {
                "registry": "ghcr.io",
                "username": "${{ github.actor }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/trivy.yml",
            "build",
            "Set up Docker Buildx",
            f"docker/setup-buildx-action@{DOCKER_SETUP_BUILDX_NODE24_SHA}",
            None,
            None,
            None,
            None,
        ),
    ]

    observed_trivy_contracts = []
    for workflow_path in (BUILD_WORKFLOW_PATH, CD_WORKFLOW_PATH, TRIVY_WORKFLOW_PATH):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("aquasecurity/trivy-action@"):
                observed_trivy_contracts.append(
                    (
                        str(workflow_path.relative_to(REPO_ROOT)),
                        job_id,
                        step.get("name"),
                        uses,
                        step.get("with"),
                        step.get("if"),
                        step.get("env"),
                        step.get("continue-on-error"),
                    )
                )

    assert observed_trivy_contracts == [
        (
            ".github/workflows/build.yml",
            "build",
            "Scan production image before publication eligibility",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "version": TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW[BUILD_WORKFLOW_PATH],
                "scan-type": "image",
                "image-ref": "pulseplate:test",
                "cache-dir": "/tmp/trivy-cache",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "trivyignores": ".trivyignore",
                "scanners": "vuln",
                "severity": "CRITICAL,HIGH",
                "exit-code": "1",
                "format": "json",
                "output": "trivy-build-image.json",
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/build.yml",
            "security-scan",
            "Run Trivy vulnerability scanner (filesystem scan)",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "fs",
                "scan-ref": ".",
                "cache-dir": "/tmp/trivy-cache",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "scanners": "vuln",
                "format": "sarif",
                "output": "${{ runner.temp }}/pulseplate-trivy/trivy-results.sarif",
                "skip-dirs": "trivy",
                "severity": "CRITICAL,HIGH",
                "limit-severities-for-sarif": True,
                "exit-code": "1",
                "trivyignores": ".trivyignore",
                "version": TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW[BUILD_WORKFLOW_PATH],
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Run Trivy vulnerability scanner (image scan, fail-closed)",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "${{ steps.image-ref.outputs.ref }}",
                "cache-dir": "/tmp/trivy-cache",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "scanners": "vuln",
                "format": "json",
                "output": "trivy-image.json",
                "severity": "CRITICAL,HIGH",
                "trivyignores": ".trivyignore",
                "exit-code": "1",
                "version": TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW[BUILD_WORKFLOW_PATH],
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Scan staged backend image",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "${{ steps.staging-image-refs.outputs.backend_ref }}",
                "scanners": "vuln,secret",
                "format": "table",
                "vuln-type": "os,library",
                "severity": "CRITICAL,HIGH",
                "exit-code": "1",
                "timeout": "15m",
                "trivyignores": ".trivyignore",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "version": TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW[CD_WORKFLOW_PATH],
                "cache-dir": "/tmp/trivy-cache-staging-backend",
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Scan staged Caddy image",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "${{ steps.staging-image-refs.outputs.caddy_ref }}",
                "scanners": "vuln,secret",
                "format": "table",
                "vuln-type": "os,library",
                "severity": "CRITICAL,HIGH",
                "exit-code": "1",
                "timeout": "15m",
                "trivyignores": ".trivyignore-caddy",
                "version": TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW[CD_WORKFLOW_PATH],
                "cache-dir": "/tmp/trivy-cache-staging-caddy",
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
        (
            ".github/workflows/trivy.yml",
            "build",
            "Run Trivy vulnerability scanner",
            f"aquasecurity/trivy-action@{TRIVY_ACTION_NODE24_CACHE_SHA}",
            {
                "scan-type": "image",
                "image-ref": "pulseplate:trivy-scan-${{ github.sha }}",
                "cache-dir": "/tmp/trivy-cache",
                "scanners": "vuln",
                "timeout": "15m",
                "format": "sarif",
                "output": "trivy-results.sarif",
                "severity": "CRITICAL,HIGH",
                "limit-severities-for-sarif": True,
                "ignore-unfixed": True,
                "trivyignores": ".trivyignore",
                "ignore-policy": ".trivy-ignore-policy.rego",
                "exit-code": "1",
                "version": TRIVY_RUNTIME_VERSIONS_BY_WORKFLOW[TRIVY_WORKFLOW_PATH],
            },
            None,
            {"TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db"},
            None,
        ),
    ]
    assert len(observed_trivy_contracts) == 6


def test_build_workflow_trivy_fs_sarif_is_temp_isolated_before_upload() -> None:
    workflow = _load_workflow(BUILD_WORKFLOW_PATH)
    prepare_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Prepare Trivy SARIF output path and ignore policy",
    )
    scanner_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Run Trivy vulnerability scanner (filesystem scan)",
    )
    sarif_check_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Check Trivy filesystem SARIF output",
    )
    upload_step = _job_step_by_name(
        workflow,
        job_id="security-scan",
        step_name="Upload Trivy scan results to GitHub Security tab",
    )

    prepare_run = str(prepare_step["run"])
    assert "rm -rf -- trivy-results.sarif" in prepare_run
    assert 'rm -rf "${RUNNER_TEMP}/pulseplate-trivy"' in prepare_run
    assert 'mkdir -p "${RUNNER_TEMP}/pulseplate-trivy"' in prepare_run
    assert scanner_step["with"]["exit-code"] == "1"
    assert scanner_step.get("continue-on-error") is None
    assert scanner_step["with"]["output"] == (
        "${{ runner.temp }}/pulseplate-trivy/trivy-results.sarif"
    )

    sarif_check_run = str(sarif_check_step["run"])
    assert sarif_check_step["id"] == "trivy_fs_sarif"
    assert sarif_check_step["if"] == "${{ always() }}"
    assert 'sarif_path="${RUNNER_TEMP}/pulseplate-trivy/trivy-results.sarif"' in sarif_check_run
    assert 'if [ -s "$sarif_path" ]; then' in sarif_check_run
    assert 'cp -- "$sarif_path" trivy-results.sarif' in sarif_check_run
    assert 'echo "present=true" >> "${GITHUB_OUTPUT}"' in sarif_check_run
    assert 'echo "present=false" >> "${GITHUB_OUTPUT}"' in sarif_check_run

    assert upload_step["if"] == (
        "${{ always() && steps.trivy_fs_sarif.outputs.present == 'true' }}"
    )
    assert upload_step["uses"].startswith("github/codeql-action/upload-sarif@")
    assert upload_step["continue-on-error"] is True
    assert upload_step["with"]["sarif_file"] == "trivy-results.sarif"


def test_active_upload_artifact_refs_all_use_node24_sha() -> None:
    """Guard every active upload-artifact use, not only historically touched workflows."""

    expected_uses = f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}"
    expected_line = f"{expected_uses} # v7.0.1 / Node 24"
    observed_upload_steps: list[tuple[str, str, object]] = []

    for workflow_path in _active_workflow_paths():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow_upload_count = 0
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.startswith("actions/upload-artifact@"):
                continue
            workflow_upload_count += 1
            observed_upload_steps.append(
                (str(workflow_path.relative_to(REPO_ROOT)), job_id, step.get("name"))
            )
            assert uses == expected_uses

        if workflow_upload_count:
            assert workflow_text.count(expected_line) == workflow_upload_count

    assert observed_upload_steps


def test_active_sbom_action_refs_use_verified_v0_24_0_sha_and_preserve_contracts() -> None:
    """Guard every active SBOM action use and its fail-closed generation contract."""

    expected_uses = f"anchore/sbom-action@{SBOM_ACTION_NODE24_SHA}"
    expected_line = f"{expected_uses} # v0.24.0"
    expected_counts = {
        ".github/workflows/build.yml": 1,
        ".github/workflows/cd.yml": 3,
    }
    observed_counts: dict[str, int] = {}
    observed_contracts: list[
        tuple[str, str, object, str, object, object, object, object, object]
    ] = []

    for workflow_path in _active_workflow_paths():
        workflow_relative_path = str(workflow_path.relative_to(REPO_ROOT))
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow_lines = workflow_text.splitlines()
        workflow = _load_workflow(workflow_path)
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        assert OLD_SBOM_ACTION_SHA not in workflow_text
        workflow_document = yaml.compose(workflow_text)
        assert isinstance(workflow_document, Node)
        sbom_source_node_count = 0
        for uses_key_node, uses_value_node in _iter_uses_source_mappings(workflow_document):
            uses = uses_value_node.value
            if not uses.casefold().startswith("anchore/sbom-action@"):
                continue

            sbom_source_node_count += 1
            assert uses == expected_uses
            assert workflow_lines[uses_key_node.start_mark.line].strip() == (
                f"uses: {expected_line}"
            )

        workflow_sbom_count = 0
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.casefold().startswith("anchore/sbom-action@"):
                continue

            job = jobs[job_id]
            assert isinstance(job, dict)
            workflow_sbom_count += 1
            assert uses == expected_uses
            assert "continue-on-error" not in job
            assert "if" not in step
            assert "continue-on-error" not in step
            observed_contracts.append(
                (
                    workflow_relative_path,
                    job_id,
                    step.get("name"),
                    uses,
                    step.get("with"),
                    job.get("if"),
                    job.get("continue-on-error"),
                    step.get("if"),
                    step.get("continue-on-error"),
                )
            )

        assert sbom_source_node_count == workflow_sbom_count
        if workflow_sbom_count:
            assert workflow_relative_path in expected_counts
            observed_counts[workflow_relative_path] = workflow_sbom_count

    assert observed_counts == expected_counts
    assert observed_contracts == [
        (
            ".github/workflows/build.yml",
            "publish",
            "Generate SBOM",
            expected_uses,
            {
                "image": "${{ steps.image-ref.outputs.ref }}",
                "format": "spdx-json",
                "output-file": "sbom.spdx.json",
            },
            "github.event_name != 'pull_request' && "
            "(github.event_name != 'workflow_dispatch' || "
            "inputs.mode == 'normal')",
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Generate staged backend image SBOM",
            expected_uses,
            {
                "image": (
                    "${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"
                    "@${{ steps.build.outputs.digest }}"
                ),
                "format": "spdx-json",
                "output-file": "backend-image-sbom.spdx.json",
            },
            "!cancelled() && github.event_name == 'push' && github.ref == 'refs/heads/main' && "
            "needs.prometheus-image-security.result == 'success' && "
            "needs.main-push-admission.result == 'success' && "
            "needs.staging-postgres-native-integration.result == 'success'",
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build",
            "Generate staged Caddy image SBOM",
            expected_uses,
            {
                "image": (
                    "${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"
                    "@${{ steps.build-caddy.outputs.digest }}"
                ),
                "format": "spdx-json",
                "output-file": "caddy-image-sbom.spdx.json",
            },
            "!cancelled() && github.event_name == 'push' && github.ref == 'refs/heads/main' && "
            "needs.prometheus-image-security.result == 'success' && "
            "needs.main-push-admission.result == 'success' && "
            "needs.staging-postgres-native-integration.result == 'success'",
            None,
            None,
            None,
        ),
        (
            ".github/workflows/cd.yml",
            "build-production",
            "Generate production image SBOM",
            expected_uses,
            {
                "image": (
                    "${{ env.REGISTRY }}/${{ steps.image-name.outputs.image_name }}"
                    "@${{ steps.build.outputs.digest }}"
                ),
                "format": "spdx-json",
                "output-file": "docker-image-sbom.spdx.json",
            },
            "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')",
            None,
            None,
            None,
        ),
    ]


def test_active_codeql_action_refs_use_verified_v4_37_1_sha() -> None:
    """Guard every active CodeQL action ref against pin and location drift."""

    expected_uses_by_component = {
        "init": f"github/codeql-action/init@{CODEQL_ACTION_V4_37_1_SHA}",
        "analyze": f"github/codeql-action/analyze@{CODEQL_ACTION_V4_37_1_SHA}",
        "upload-sarif": f"github/codeql-action/upload-sarif@{CODEQL_ACTION_V4_37_1_SHA}",
    }
    expected_comment_counts_by_component = {
        "init": 1,
        "analyze": 1,
        "upload-sarif": 3,
    }
    expected_line_counts = {
        BUILD_WORKFLOW_PATH: {
            f"uses: {expected_uses_by_component['upload-sarif']} # v4.37.1": 2,
        },
        CODEQL_WORKFLOW_PATH: {
            f"uses: {expected_uses_by_component['init']} # v4.37.1": 1,
            f"uses: {expected_uses_by_component['analyze']} # v4.37.1": 1,
        },
        TRIVY_WORKFLOW_PATH: {
            f"uses: {expected_uses_by_component['upload-sarif']} # v4.37.1": 1,
        },
    }
    observed_contracts: list[tuple[str, str, object, str]] = []
    observed_comment_counts_by_component = {
        component: 0 for component in expected_comment_counts_by_component
    }

    for workflow_path in _active_workflow_paths():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow_lines = workflow_text.splitlines()
        expected_source_line_counts = expected_line_counts.get(workflow_path, {})
        observed_source_line_counts = {
            expected_line: 0 for expected_line in expected_source_line_counts
        }
        workflow_document = yaml.compose(workflow_text)
        assert isinstance(workflow_document, Node)
        for uses_key_node, uses_value_node in _iter_uses_source_mappings(workflow_document):
            uses = uses_value_node.value
            normalized_uses = uses.casefold()
            if not normalized_uses.startswith("github/codeql-action/"):
                continue

            assert uses.startswith("github/codeql-action/")
            component = normalized_uses.removeprefix("github/codeql-action/").split(
                "@", maxsplit=1
            )[0]
            assert component in expected_uses_by_component
            observed_comment_counts_by_component[component] += 1
            expected_line = f"uses: {uses} # v4.37.1"
            assert workflow_lines[uses_key_node.start_mark.line].strip() == expected_line
            if expected_line in observed_source_line_counts:
                observed_source_line_counts[expected_line] += 1

        assert observed_source_line_counts == expected_source_line_counts

        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str):
                continue
            normalized_uses = uses.casefold()
            if not normalized_uses.startswith("github/codeql-action/"):
                continue

            assert uses.startswith("github/codeql-action/")
            component = normalized_uses.removeprefix("github/codeql-action/").split(
                "@", maxsplit=1
            )[0]
            assert component in expected_uses_by_component
            assert uses == expected_uses_by_component[component]
            observed_contracts.append(
                (
                    str(workflow_path.relative_to(REPO_ROOT)),
                    job_id,
                    step.get("name"),
                    uses,
                )
            )

    assert observed_comment_counts_by_component == expected_comment_counts_by_component
    assert observed_contracts == [
        (
            ".github/workflows/build.yml",
            "security-scan",
            "Upload Trivy scan results to GitHub Security tab",
            expected_uses_by_component["upload-sarif"],
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Upload Trivy image scan results",
            expected_uses_by_component["upload-sarif"],
        ),
        (
            ".github/workflows/codeql.yml",
            "analyze",
            "Initialize CodeQL",
            expected_uses_by_component["init"],
        ),
        (
            ".github/workflows/codeql.yml",
            "analyze",
            "Perform CodeQL Analysis",
            expected_uses_by_component["analyze"],
        ),
        (
            ".github/workflows/trivy.yml",
            "build",
            "Upload Trivy scan results to GitHub Security tab",
            expected_uses_by_component["upload-sarif"],
        ),
    ]


def test_node24_setup_go_and_upload_artifact_pins_preserve_workflow_contracts() -> None:
    """Guard direct Node 20 setup/upload action migrations in touched workflows."""

    expected_action_lines = {
        BUILD_WORKFLOW_PATH: {
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 6,
        },
        GREENLIGHT_IOS_WORKFLOW_PATH: {
            f"actions/setup-go@{SETUP_GO_NODE24_SHA} # v7.0.0 / Node 24": 1,
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 1,
        },
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH: {
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 1,
        },
        SECURITY_WORKFLOW_PATH: {
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA} # v7.0.1 / Node 24": 1,
        },
    }
    for workflow_path, expected_counts in expected_action_lines.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for expected_line, expected_count in expected_counts.items():
            assert workflow_text.count(expected_line) == expected_count

    observed_contracts = []
    for workflow_path in (
        BUILD_WORKFLOW_PATH,
        GREENLIGHT_IOS_WORKFLOW_PATH,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH,
        SECURITY_WORKFLOW_PATH,
    ):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if not isinstance(uses, str):
                continue
            if not (
                uses.startswith("actions/setup-go@") or uses.startswith("actions/upload-artifact@")
            ):
                continue
            observed_contracts.append(
                (
                    str(workflow_path.relative_to(REPO_ROOT)),
                    job_id,
                    step.get("name"),
                    uses,
                    step.get("with"),
                    step.get("if"),
                    step.get("env"),
                    step.get("continue-on-error"),
                )
            )

    assert observed_contracts == [
        (
            ".github/workflows/build.yml",
            "build",
            "Preserve production image scan evidence",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "production-image-scan",
                "path": (
                    "trivy-build-image.json\ntrivy-build-image.sarif\n"
                    "docker-runtime-dependency-surface.json\n"
                ),
                "if-no-files-found": "error",
                "retention-days": 30,
            },
            "${{ always() }}",
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "build",
            "Upload Docker telemetry artifact",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "docker-image-telemetry-build",
                "path": (
                    "docker-runtime-dependency-surface.json\n"
                    "docker-image-telemetry.json\n"
                    "docker-image-telemetry.md\n"
                ),
                "if-no-files-found": "warn",
                "retention-days": 14,
            },
            "${{ always() }}",
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "build",
            "Upload Docker budget check artifact",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "docker-image-budget-check-build",
                "path": "docker-image-budget-check.json\ndocker-image-budget-check.md\n",
                "if-no-files-found": "warn",
                "retention-days": 14,
            },
            "${{ always() }}",
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Preserve publish image scan evidence",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "publish-image-scan",
                "path": (
                    "trivy-image.json\ntrivy-image.sarif\n"
                    "docker-publish-runtime-dependency-surface.json\n"
                ),
                "if-no-files-found": "error",
                "retention-days": 30,
            },
            "${{ always() }}",
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Upload release-control-plane build digest sources",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "release-control-plane-build-sources",
                "path": (
                    "release-control-plane-build-sources/artifact_digest.txt\n"
                    "release-control-plane-build-sources/sbom_digest.txt\n"
                    "release-control-plane-build-sources/attestation_check_digest.txt\n"
                    "release-control-plane-build-sources/provenance_digest.txt\n"
                    "release-control-plane-build-sources/attestation_status.txt\n"
                ),
                "if-no-files-found": "error",
                "retention-days": 14,
            },
            None,
            None,
            None,
        ),
        (
            ".github/workflows/build.yml",
            "publish",
            "Upload SBOM",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {"name": "sbom", "path": "sbom.spdx.json", "retention-days": 30},
            None,
            None,
            None,
        ),
        (
            ".github/workflows/greenlight-ios.yml",
            "greenlight-ios",
            "Setup Go",
            f"actions/setup-go@{SETUP_GO_NODE24_SHA}",
            {"go-version": "1.24"},
            None,
            None,
            None,
        ),
        (
            ".github/workflows/greenlight-ios.yml",
            "greenlight-ios",
            "Upload Greenlight report artifact",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "greenlight-ios-report",
                "path": "greenlight-report.json",
                "if-no-files-found": "error",
            },
            "always()",
            None,
            None,
        ),
        (
            ".github/workflows/ios-appstore-assets.yml",
            "validate-assets",
            "Upload screenshot artifacts",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "ios-appstore-screenshots",
                "path": "ios/fastlane/screenshots",
                "if-no-files-found": "warn",
            },
            "always()",
            None,
            None,
        ),
        (
            ".github/workflows/security.yml",
            "bandit",
            "Upload security reports",
            f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
            {
                "name": "security-reports",
                "path": ("bandit-report.json\npip-audit-*.json\n"),
                "if-no-files-found": "ignore",
            },
            "always()",
            None,
            None,
        ),
    ]


def test_node24_artifact_migration_preserves_download_contracts() -> None:
    """Guard artifact names, paths, and merge behavior during action runtime bumps."""

    expected_download_contracts = [
        (
            ".github/workflows/ci.yml",
            "coverage-pr",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "diff-coverage",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            None,
        ),
        (
            ".github/workflows/ci.yml",
            "diff-coverage",
            "Download OPS context coverage artifact",
            {
                "name": "coverage-ops-context-${{ env.PYTHON_VERSION }}",
                "path": "./ops-context-coverage",
            },
            None,
        ),
        (
            ".github/workflows/ci.yml",
            "diff-coverage",
            "Download FitChef eval coverage artifact",
            {
                "name": "coverage-fitchef-eval-${{ env.PYTHON_VERSION }}",
                "path": "./fitchef-eval-coverage",
            },
            None,
        ),
        (
            ".github/workflows/ci.yml",
            "diff-coverage",
            "Download orchestration coverage artifact",
            {
                "name": "coverage-orchestration-${{ env.PYTHON_VERSION }}",
                "path": "./orchestration-coverage",
            },
            None,
        ),
        (
            ".github/workflows/ci.yml",
            "diff-coverage",
            "Download FitChef Agent coverage artifact",
            {
                "name": "coverage-fitchef-agent-${{ env.PYTHON_VERSION }}",
                "path": "./fitchef-agent-coverage",
            },
            None,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-feature",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.11)",
            {"name": "coverage-main-xml-3.11", "path": "./coverage-artifacts/3.11"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.12)",
            {"name": "coverage-main-xml-3.12", "path": "./coverage-artifacts/3.12"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.13)",
            {"name": "coverage-main-xml-3.13", "path": "./coverage-artifacts/3.13"},
            True,
        ),
        (
            ".github/workflows/codecov-upload.yml",
            "upload",
            "Download coverage artifact",
            {"name": "${{ inputs['coverage-artifact'] }}", "path": "./coverage-artifact"},
            None,
        ),
        (
            ".github/workflows/nightly.yml",
            "coverage-merge",
            "Download coverage artifacts",
            {
                "pattern": "coverage-reports-shard-*",
                "merge-multiple": True,
                "path": "coverage-artifacts",
            },
            None,
        ),
        (
            ".github/workflows/ios-appstore-assets.yml",
            "upload-assets",
            "Download screenshot artifacts",
            {"name": "ios-appstore-screenshots", "path": "ios/fastlane/screenshots"},
            None,
        ),
    ]

    observed_download_contracts = []
    for workflow_path in (
        CI_WORKFLOW_PATH,
        CODECOV_UPLOAD_WORKFLOW_PATH,
        NIGHTLY_WORKFLOW_PATH,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH,
    ):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/download-artifact@"):
                observed_download_contracts.append(
                    (
                        str(workflow_path.relative_to(REPO_ROOT)),
                        job_id,
                        step.get("name"),
                        step.get("with"),
                        step.get("continue-on-error"),
                    )
                )

    assert observed_download_contracts == expected_download_contracts


def test_node24_github_script_migration_preserves_pr_read_permissions() -> None:
    """Guard the PR automation script runtime bump against permission drift."""

    workflow = _load_workflow(PR_AUTOMATION_WORKFLOW_PATH)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    validate_pr_job = jobs["validate-pr"]
    assert isinstance(validate_pr_job, dict)

    assert validate_pr_job["permissions"] == {"pull-requests": "read"}

    github_script_steps = []
    for _job_id, step in _iter_job_steps(PR_AUTOMATION_WORKFLOW_PATH):
        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith("actions/github-script@"):
            github_script_steps.append(step)

    assert len(github_script_steps) == 1
    script_step = github_script_steps[0]
    assert script_step["uses"] == f"actions/github-script@{GITHUB_SCRIPT_NODE24_SHA}"
    with_section = script_step["with"]
    assert isinstance(with_section, dict)
    assert sorted(with_section) == ["github-token", "script"]
    assert with_section["github-token"] == "${{ secrets.GITHUB_TOKEN }}"
    assert "github.rest.pulls.get" in str(with_section["script"])


def test_feature_push_risk_profile_uses_origin_main_merge_base() -> None:
    """Feature/fix pushes must diff against origin/main merge-base."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    risk_profile_section = _extract_section(
        workflow_text,
        "      - name: Build CI risk profile",
        "\n  pr_scope_guard:",
    )

    assert "git fetch --no-tags --prune origin main" in risk_profile_section
    assert 'BASE_SHA="$(git merge-base origin/main "${GITHUB_SHA}")"' in risk_profile_section
    assert 'HEAD_SHA="${GITHUB_SHA}"' in risk_profile_section
    assert "Risk-profile diff: ${BASE_SHA}...${HEAD_SHA}" in risk_profile_section


def test_feature_push_branches_include_feature_prefix() -> None:
    workflow = _load_ci_workflow()
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
    assert isinstance(on_section, dict)
    push_section = on_section["push"]
    assert isinstance(push_section, dict)
    push_branches = push_section["branches"]
    assert isinstance(push_branches, list)

    assert {"main", "feat/**", "fix/**", "feature/**"}.issubset(set(push_branches))
    representative_branches = (
        "main",
        "feat/design-accessibility-regression-decision-gate",
        "fix/ci-github-token-format-and-run-diagnostics",
        "feature/example",
    )
    for branch in representative_branches:
        assert any(fnmatch.fnmatchcase(branch, pattern) for pattern in push_branches)


def test_feature_push_jobs_use_changes_gate_and_smoke_risk_topology() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    feature_push_tokens = (
        "github.event_name == 'push'",
        "refs/heads/feat/",
        "refs/heads/fix/",
        "refs/heads/feature/",
    )

    test_feature = jobs["test-feature"]
    assert isinstance(test_feature, dict)
    test_feature_needs = test_feature["needs"]
    assert isinstance(test_feature_needs, list)
    assert "changes" in test_feature_needs
    test_feature_if = test_feature["if"]
    assert isinstance(test_feature_if, str)
    _assert_contains_all_tokens(test_feature_if, feature_push_tokens)
    assert "needs.changes.outputs.run_backend_blocking == 'true'" in test_feature_if
    feature_step_names = [step.get("name") for step in test_feature["steps"]]
    assert "Critical smoke (deterministic merge blocker)" in feature_step_names
    assert "Contract and risk suites" in feature_step_names
    assert "Finalize coverage artifacts" in feature_step_names
    assert "Start fast-feedback timing" in feature_step_names
    assert "Summarize fast-feedback budget" in feature_step_names
    assert "Upload fast-feedback budget artifact" in feature_step_names
    test_feature_env = test_feature["env"]
    assert isinstance(test_feature_env, dict)
    assert test_feature_env["FEATURE_FEEDBACK_TARGET_MINUTES"] == "45"

    coverage_feature = jobs["coverage-feature"]
    assert isinstance(coverage_feature, dict)
    coverage_feature_needs = coverage_feature["needs"]
    assert isinstance(coverage_feature_needs, list)
    assert "changes" in coverage_feature_needs
    assert "test-feature" in coverage_feature_needs
    coverage_feature_if = coverage_feature["if"]
    assert isinstance(coverage_feature_if, str)
    _assert_contains_all_tokens(coverage_feature_if, feature_push_tokens)
    assert "needs.changes.outputs.run_backend_blocking == 'true'" in coverage_feature_if
    coverage_feature_step_names = [step.get("name") for step in coverage_feature["steps"]]
    assert (
        "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})"
        in coverage_feature_step_names
    )
    assert "Upload to Codecov" in coverage_feature_step_names


def test_ci_changes_outputs_cover_risk_profile_outputs() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    changes = jobs["changes"]
    assert isinstance(changes, dict)
    outputs = changes["outputs"]
    assert isinstance(outputs, dict)

    risk_output_keys = set(ci_risk_profile.build_risk_profile([]).to_outputs())

    assert risk_output_keys.issubset(outputs)
    assert (
        outputs["operator_plane_slack"] == "${{ steps.risk_profile.outputs.operator_plane_slack }}"
    )


MERGE_GOVERNANCE_OWNER_TARGETS = (
    "tests/test_check_pr_size_governance.py",
    "tests/test_ci_risk_profile.py",
    "tests/test_orchestration_merge_ready.py",
    "tests/test_pr_body_phase2_gates.py",
    "tests/test_pr_merge_readiness_gate.py",
    "tests/test_pr_review_closeout.py",
    "tests/test_review_threads_disposition_strict.py",
)


def test_contract_risk_suite_blocks_stay_in_sync_and_cover_required_targets() -> None:
    workflow = _load_ci_workflow()
    test_pr_groups = _contract_suite_targets_by_group(workflow, job_id="test-pr")
    test_feature_groups = _contract_suite_targets_by_group(workflow, job_id="test-feature")
    expected_rag_owner_targets = (
        "tests/test_insight_rag_response_fields.py",
        "tests/test_philosophy_pipeline.py",
        "tests/test_rag_validation.py",
        "tests/test_rag_vector_feature_flag_guard.py",
    )
    expected_slack_operator_targets = (
        "tests/test_ci_risk_profile.py",
        "tests/test_ci_workflow_pr_size_governance_contract.py",
        "tests/test_experiment_operator_ledger.py",
        "tests/test_experiment_slack_kpp_renderer.py",
        "tests/test_experiment_slack_socket_bridge.py",
        "tests/test_runtime_toolchain_alignment.py",
    )
    expected_db_targets = (
        "tests/test_app_db_fallback_97.py",
        "tests/test_core_db_async_optional.py",
        "tests/test_core_db_comprehensive.py",
        "tests/test_core_db_missing_coverage.py",
        "tests/test_db_engine_reuse_diff_coverage.py",
        "tests/test_db_missing_lines_coverage.py",
    )

    assert test_pr_groups == test_feature_groups
    for job_id, groups in (
        ("test-pr", test_pr_groups),
        ("test-feature", test_feature_groups),
    ):
        for group, targets in groups.items():
            assert len(targets) == len(
                set(targets)
            ), f"contract/risk group {group!r} in {job_id!r} has duplicate test targets"
    assert set(expected_rag_owner_targets).issubset(test_pr_groups["insight_ai"])
    assert "tests/test_admin_scheduler_access.py" in test_pr_groups["food_catalog"]
    assert "tests/test_scheduler_final_coverage.py" in test_pr_groups["food_catalog"]
    assert "tests/test_admin_scheduler_access.py" in test_feature_groups["food_catalog"]
    assert "tests/test_scheduler_final_coverage.py" in test_feature_groups["food_catalog"]
    assert set(ci_risk_profile.ALL_RISK_GROUPS).issubset(test_pr_groups)
    assert test_pr_groups["operator_plane_slack"] == expected_slack_operator_targets
    assert test_pr_groups["merge_governance"] == MERGE_GOVERNANCE_OWNER_TARGETS
    for groups in (test_pr_groups, test_feature_groups):
        route_targets = groups["route_contract_safety"]
        db_targets = tuple(
            target
            for target in route_targets
            if target == "tests/test_app_db_fallback_97.py"
            or target.startswith(("tests/test_core_db_", "tests/test_db_"))
        )
        assert db_targets == expected_db_targets
        assert "tests/test_pgvector_compat.py" not in route_targets
        assert "tests/test_core_db_coverage.py" not in route_targets
    assert "tests/test_bmi_compat_router.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_api_key_dependency_ownership.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_lenient_mode_warning.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_legacy_bmi_shims.py" in test_pr_groups["route_contract_safety"]
    assert (
        "tests/test_legacy_premium_weekly_plan_registration_bootstrap.py"
        in test_pr_groups["route_contract_safety"]
    )
    assert (
        "tests/test_legacy_weekly_menu_builder_access.py" in test_pr_groups["route_contract_safety"]
    )
    assert "tests/test_legacy_weekly_plan_alias_api.py" in test_pr_groups["route_contract_safety"]
    assert "tests/test_route_family_bootstrap.py" in test_pr_groups["route_contract_safety"]


@pytest.mark.parametrize("job_id", ["test-pr", "test-feature"])
@pytest.mark.parametrize("mutation", ["valid", "omitted", "commented"])
def test_closeout_owner_is_an_executed_merge_governance_argument(
    tmp_path: Path, job_id: str, mutation: str
) -> None:
    """Execute each declared group selector and observe its actual pytest argv."""
    import sys

    workflow = _load_ci_workflow()
    step = _job_step_by_name(workflow, job_id=job_id, step_name="Contract and risk suites")
    run = str(step["run"])
    target = "tests/test_pr_review_closeout.py"
    line = next(line for line in run.splitlines(keepends=True) if line.strip() == f"{target} \\")
    assert run.count(line) == 1
    if mutation != "valid":
        run = run.replace(line, "", 1)
        if mutation == "commented":
            header = "merge_governance)\n"
            assert run.count(header) == 1
            run = run.replace(header, f"{header}  # {target}\n", 1)
    step["run"] = run
    parsed = _contract_suite_targets_by_group(workflow, job_id=job_id)["merge_governance"]
    assert (target in parsed) is (mutation == "valid")
    observer = tmp_path / "python"
    observer.write_text(
        "#!"
        + sys.executable
        + "\n"
        + "import json, sys\nfrom pathlib import Path\n"
        + 'Path("observed-argv.json").write_text(json.dumps(sys.argv[1:]))\n',
        encoding="utf-8",
    )
    observer.chmod(0o755)
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", run],
        cwd=tmp_path,
        env={
            "PATH": str(tmp_path) + os.pathsep + os.defpath,
            "CONTRACT_RISK_GROUPS": "merge_governance",
            "GH_TOKEN": "opaque",
            "GITHUB_TOKEN": "opaque",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    argv = json.loads((tmp_path / "observed-argv.json").read_text())
    expected = [
        owner for owner in MERGE_GOVERNANCE_OWNER_TARGETS if mutation == "valid" or owner != target
    ]
    assert argv == [
        "-m",
        "coverage",
        "run",
        "--append",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:xdist",
        *sorted(expected),
        "--junitxml=tests/contract-results-1.xml",
        "-o",
        "junit_family=legacy",
    ]


@pytest.mark.parametrize("job_id", ["test-pr", "test-feature"])
def test_contract_risk_suite_ignores_commented_db_target(job_id: str) -> None:
    workflow = _load_ci_workflow()
    step = _job_step_by_name(workflow, job_id=job_id, step_name="Contract and risk suites")
    run_script = step["run"]
    assert isinstance(run_script, str)
    target = "tests/test_core_db_async_optional.py"
    argument_line = next(
        line for line in run_script.splitlines(keepends=True) if line.strip() == f"{target} \\"
    )
    assert run_script.count(argument_line) == 1
    commented_script = run_script.replace(argument_line, "", 1)
    group_header = "route_contract_safety)\n"
    assert commented_script.count(group_header) == 1
    step["run"] = commented_script.replace(group_header, f"{group_header}  # {target}\n", 1)

    route_targets = _contract_suite_targets_by_group(workflow, job_id=job_id)[
        "route_contract_safety"
    ]
    assert target in str(step["run"])
    assert target not in route_targets


def test_contract_risk_suites_use_bounded_coverage_batches() -> None:
    workflow = _load_ci_workflow()
    for job_id in ("test-pr", "test-feature"):
        step = _job_step_by_name(
            workflow,
            job_id=job_id,
            step_name="Contract and risk suites",
        )
        run_script = step["run"]
        assert isinstance(run_script, str)
        assert "contract_batch_size=24" in run_script
        assert "for ((batch_start=0;" in run_script
        assert "batch_targets=(" in run_script
        assert "python -m coverage run --append -m pytest -q" in run_script
        assert "-p no:xdist" in run_script
        assert '"${batch_targets[@]}"' in run_script
        assert '--junitxml="${junit_path}"' in run_script

        upload_step = _job_step_by_name(
            workflow,
            job_id=job_id,
            step_name="Upload JUnit test report",
        )
        upload_with = upload_step["with"]
        assert isinstance(upload_with, dict)
        assert "tests/contract-results*.xml" in str(upload_with["path"])


def test_ci_workflow_declares_canonical_main_and_feature_push_jobs() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    required_job_ids = {
        "changes",
        "lint",
        "security",
        "test-feature",
        "coverage-feature",
        "test-main",
        "coverage-main",
        "diff-coverage",
    }
    assert required_job_ids <= set(jobs)
    for job_id in required_job_ids:
        job = jobs[job_id]
        assert isinstance(job, dict)
        assert "runs-on" in job or "uses" in job

    test_main = jobs["test-main"]
    assert isinstance(test_main, dict)
    assert "github.ref == 'refs/heads/main'" in str(test_main["if"])

    coverage_main = jobs["coverage-main"]
    assert isinstance(coverage_main, dict)
    assert coverage_main["needs"] == "test-main"
    assert "github.ref == 'refs/heads/main'" in str(coverage_main["if"])


def test_feature_push_fast_feedback_budget_is_warning_only_evidence() -> None:
    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    test_feature_section = _extract_job_section(workflow_text, "  test-feature:")

    assert "Feature/fix fast-feedback exceeded" in test_feature_section
    assert "::warning::Feature/fix fast-feedback exceeded" in test_feature_section
    assert "Fast-feedback timing seed is missing" in test_feature_section
    assert 'status="timing_unavailable"' in test_feature_section
    assert "elapsed_seconds=-1" in test_feature_section
    assert "FEATURE_FEEDBACK_STARTED_AT:-$(date +%s)" not in test_feature_section
    assert "feature-feedback-budget.json" in test_feature_section
    assert "feature-feedback-budget-${{ env.PYTHON_VERSION }}" in test_feature_section
    assert "if-no-files-found: error" in test_feature_section


def test_feature_branch_alias_stays_in_sync_for_ios_push_jobs() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    ios_routing_tokens = (
        "github.event_name == 'pull_request'",
        "refs/heads/feat/",
        "refs/heads/fix/",
        "refs/heads/feature/",
        "refs/heads/main",
    )

    ios_tests = jobs["ios-tests"]
    assert isinstance(ios_tests, dict)
    ios_tests_if = ios_tests["if"]
    assert isinstance(ios_tests_if, str)
    _assert_contains_all_tokens(ios_tests_if, ios_routing_tokens)

    ios_ui_smoke = jobs["ios-ui-smoke"]
    assert isinstance(ios_ui_smoke, dict)
    ios_ui_smoke_if = ios_ui_smoke["if"]
    assert isinstance(ios_ui_smoke_if, str)
    _assert_contains_all_tokens(ios_ui_smoke_if, ios_routing_tokens)


def test_ios_unit_selector_is_the_complete_target_with_local_override_preserved() -> None:
    selector_text = IOS_TEST_TARGETS_PATH.read_text(encoding="utf-8")
    executable_lines = [
        line.strip()
        for line in selector_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert executable_lines == [
        "set -euo pipefail",
        "printf '%s' 'PulsePlateTests'",
    ]
    assert "PulsePlateTests/" not in selector_text
    assert "TESTS=(" not in selector_text

    makefile_text = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert (
        'ONLY_ITEMS="$${IOS_ONLY_TESTING:-$(shell ./scripts/ios_test_targets.sh)}"' in makefile_text
    )


def _assert_frontend_node24_build_and_precommit_contract(
    package: dict[str, object],
    config: dict[str, object],
) -> None:
    """Assert the finite package-script and pre-commit enforcement chain."""

    scripts = package["scripts"]
    assert isinstance(scripts, dict)

    assert scripts["typecheck"] == "tsc -p tsconfig.json --noEmit"
    assert scripts["build"] == "npm run typecheck && vite build"
    assert (
        scripts["test:precommit"]
        == "vitest run --environment jsdom --testTimeout=30000 --reporter=verbose"
    )

    repos = config["repos"]
    assert isinstance(repos, list)
    matching_hooks = [
        hook
        for repo in repos
        if isinstance(repo, dict)
        if repo.get("repo") == "local"
        for hook in repo.get("hooks", [])
        if isinstance(hook, dict)
        if hook.get("id") == "frontend-tests"
    ]
    assert len(matching_hooks) == 1
    hook = matching_hooks[0]
    assert hook["entry"] == 'bash -c "cd frontend && npm run test:precommit"'
    assert hook["language"] == "system"
    assert hook["pass_filenames"] is False
    assert hook["stages"] == ["pre-commit"]
    assert hook["files"] == r"^frontend/.*\.(ts|tsx|js|jsx)$"

    guarded_commands = (hook["entry"], scripts["test:precommit"])
    for forbidden in ("||", "; true", "exit 0", "continue-on-error", "warning::"):
        assert all(
            isinstance(command, str) and forbidden not in command for command in guarded_commands
        )


def test_frontend_node24_production_build_and_precommit_tests_are_fail_closed() -> None:
    package = json.loads(FRONTEND_PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
    config = yaml.safe_load(PRE_COMMIT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(package, dict)
    assert isinstance(config, dict)

    _assert_frontend_node24_build_and_precommit_contract(package, config)


@pytest.mark.parametrize(
    "replacement",
    (
        "vitest",
        "true",
        ":",
        "vitest run || true",
        "vitest run; exit 0",
        None,
    ),
)
def test_frontend_node24_precommit_guard_rejects_inner_script_drift(
    replacement: str | None,
) -> None:
    """The outer hook cannot hide a weakened or missing package test script."""

    package = json.loads(FRONTEND_PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
    config = yaml.safe_load(PRE_COMMIT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(package, dict)
    assert isinstance(config, dict)
    scripts = package["scripts"]
    assert isinstance(scripts, dict)
    if replacement is None:
        scripts.pop("test:precommit")
    else:
        scripts["test:precommit"] = replacement

    with pytest.raises((AssertionError, KeyError)):
        _assert_frontend_node24_build_and_precommit_contract(package, config)


IOS_APPSTORE_VERIFY_STEP_NAME = "iOS App Store repo-local verification"
IOS_APPSTORE_VERIFY_COMMAND = "python3 scripts/release/check_ios_appstore_verify.py"
IOS_UNIT_STEP_NAME = "iOS tests (project-based, app scheme)"
IOS_RELEASE_BUILD_STEP_NAME = "iOS Release simulator build (unsigned)"
IOS_TESTS_JOB_IF = (
    "needs.changes.outputs.ios == 'true' && (\n"
    "  github.event_name == 'pull_request' ||\n"
    "  (github.event_name == 'push' && (startsWith(github.ref, 'refs/heads/feat/') || "
    "startsWith(github.ref, 'refs/heads/fix/') || startsWith(github.ref, "
    "'refs/heads/feature/') || github.ref == 'refs/heads/main'))\n"
    ")\n"
)
# SHA-256 of the exact yaml.safe_load() complete-unit run scalar; no normalization is permitted.
IOS_UNIT_RUN_SHA256 = (
    "db7b3a74ea8066fd3094627b8458c4c02c34178ffd212a35b9d3f32af771fbdb"  # pragma: allowlist secret
)
# SHA-256 of the exact yaml.safe_load() Release run scalar; no normalization is permitted.
IOS_RELEASE_BUILD_RUN_SHA256 = (
    "c3aa3d5582fa3e4261156f9f4aaa8acfbc4d34641bf8842fa3c10b94468910bb"  # pragma: allowlist secret
)
# Non-secret SHA-256 of the exact yaml.safe_load() UI smoke run scalar; no normalization.
IOS_UI_SMOKE_RUN_SHA256 = (
    "bf9a94c226d1e42c30f111737c343591afbca7eb8f7559e3861cadded28cbb65"  # pragma: allowlist secret
)


def _assert_ios_release_build_contract(workflow: dict[str, object]) -> None:
    """Assert the bounded Debug-unit -> Release-build sequence in ios-tests."""

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["defaults"] == {"run": {"shell": "bash"}}
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    ios_tests = jobs["ios-tests"]
    assert isinstance(ios_tests, dict)
    assert set(ios_tests) == {
        "name",
        "runs-on",
        "strategy",
        "timeout-minutes",
        "if",
        "needs",
        "steps",
    }
    assert ios_tests["name"] == "iOS unit tests (${{ matrix.family }}, xcodebuild)"
    assert ios_tests["strategy"] == {"fail-fast": False, "matrix": {"family": ["iphone", "ipad"]}}
    assert ios_tests["runs-on"] == "xcode-27"
    assert ios_tests["needs"] == ["changes"]
    assert ios_tests["if"] == IOS_TESTS_JOB_IF
    assert "continue-on-error" not in ios_tests
    assert ios_tests["timeout-minutes"] == (
        "${{ fromJSON(vars.IOS_TESTS_JOB_TIMEOUT_MINUTES || '60') }}"
    )

    steps = ios_tests["steps"]
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    step_names = [step.get("name") for step in steps]
    assert step_names == [
        "Checkout",
        "Select Xcode (require exact 27.0 and iOS 27 SDK)",
        "Cache SwiftPM packages (SourcePackages only, not Build)",
        "Select iOS simulator destination (stable)",
        IOS_APPSTORE_VERIFY_STEP_NAME,
        IOS_UNIT_STEP_NAME,
        IOS_RELEASE_BUILD_STEP_NAME,
        "Retain iOS unit result bundles and crash diagnostics",
    ]
    assert step_names.count(IOS_APPSTORE_VERIFY_STEP_NAME) == 1
    assert step_names.count(IOS_UNIT_STEP_NAME) == 1
    assert step_names.count(IOS_RELEASE_BUILD_STEP_NAME) == 1
    validator_index = step_names.index(IOS_APPSTORE_VERIFY_STEP_NAME)
    unit_index = step_names.index(IOS_UNIT_STEP_NAME)
    release_index = step_names.index(IOS_RELEASE_BUILD_STEP_NAME)
    assert validator_index + 1 == unit_index
    assert release_index == unit_index + 1
    assert steps[release_index + 1] == {
        "name": "Retain iOS unit result bundles and crash diagnostics",
        "if": "always()",
        "uses": f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}",
        "with": {
            "name": "ios-unit-xcresult-${{ matrix.family }}-${{ github.run_id }}-${{ github.run_attempt }}",
            "path": "ios/.derivedData/Logs/Test/*.xcresult",
            "retention-days": 7,
            "if-no-files-found": "warn",
        },
    }

    validator_step = steps[validator_index]
    assert isinstance(validator_step, dict)
    assert set(validator_step) == {"name", "run"}
    assert validator_step["name"] == IOS_APPSTORE_VERIFY_STEP_NAME
    assert validator_step["run"] == IOS_APPSTORE_VERIFY_COMMAND
    assert (
        sum(
            isinstance(step.get("run"), str) and IOS_APPSTORE_VERIFY_COMMAND in step["run"]
            for step in steps
        )
        == 1
    )

    unit_step = steps[unit_index]
    assert isinstance(unit_step, dict)
    assert set(unit_step) == {"name", "working-directory", "env", "run"}
    assert unit_step["working-directory"] == "ios"
    assert unit_step["env"] == {"DEVELOPER_DIR": "${{ steps.select-xcode.outputs.developer_dir }}"}
    unit_run = unit_step["run"]
    assert isinstance(unit_run, str)
    assert hashlib.sha256(unit_run.encode("utf-8")).hexdigest() == IOS_UNIT_RUN_SHA256
    assert unit_run.index('"xcodebuild", "build-for-testing"') < unit_run.index(
        '"xcodebuild", "test-without-building"'
    )
    assert "result = subprocess.run(cmd, timeout=600, check=True)" in unit_run
    assert "subprocess.run(cmd, timeout=900, check=True)" in unit_run

    release_step = steps[release_index]
    assert isinstance(release_step, dict)
    assert set(release_step) == {"name", "working-directory", "env", "run"}
    assert release_step["name"] == IOS_RELEASE_BUILD_STEP_NAME
    assert release_step["working-directory"] == "ios"
    release_env = release_step["env"]
    assert isinstance(release_env, dict)
    assert release_env == {
        "DEVELOPER_DIR": "${{ steps.select-xcode.outputs.developer_dir }}",
        "DESTINATION": "${{ steps.select-destination.outputs.destination }}",
        "IOS_RELEASE_BUILD_TIMEOUT_SECONDS": 600,
    }
    release_run = release_step["run"]
    assert isinstance(release_run, str)
    assert hashlib.sha256(release_run.encode("utf-8")).hexdigest() == (IOS_RELEASE_BUILD_RUN_SHA256)


def test_ios_release_simulator_build_stays_blocking_after_complete_unit_run() -> None:
    workflow = _load_ci_workflow()

    _assert_ios_release_build_contract(workflow)


def _assert_ios_family_matrix_contract(workflow: dict[str, object]) -> None:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    observed_names: set[str] = set()
    observed_artifacts: set[str] = set()
    for job_id, label, artifact_step in (
        ("ios-tests", "iOS unit tests", "Retain iOS unit result bundles and crash diagnostics"),
        ("ios-ui-smoke", "iOS UI smoke", "Upload xcresult on failure (crash evidence)"),
    ):
        job = jobs[job_id]
        assert isinstance(job, dict)
        assert job["strategy"] == {
            "fail-fast": False,
            "matrix": {"family": ["iphone", "ipad"]},
        }
        assert job["name"] == f"{label} (${{{{ matrix.family }}}}, xcodebuild)"
        assert job["needs"] == ["changes"]
        assert job["if"] == IOS_TESTS_JOB_IF
        assert "continue-on-error" not in job
        assert "permissions" not in job
        steps = job["steps"]
        assert isinstance(steps, list)
        selection = next(step for step in steps if step.get("id") == "select-destination")
        assert selection["working-directory"] == "ios"
        assert selection["env"] == {
            "DEVELOPER_DIR": "${{ steps.select-xcode.outputs.developer_dir }}"
        }
        assert (
            'python3 ../scripts/ci/select_ios_simulator.py --family "${{ matrix.family }}"'
            in selection["run"]
        )
        if job_id == "ios-ui-smoke":
            assert job["timeout-minutes"] == 45
            smoke_step = next(
                step
                for step in steps
                if step.get("name") == "iOS UI smoke (build-for-testing + test-without-building)"
            )
            smoke_run = smoke_step["run"]
            assert isinstance(smoke_run, str)
            assert hashlib.sha256(smoke_run.encode("utf-8")).hexdigest() == IOS_UI_SMOKE_RUN_SHA256
            assert 'DESTINATION="${{ steps.select-destination.outputs.destination }}"' in smoke_run
            assert smoke_run.count('"-destination", destination') == 2
        artifact = next(step for step in steps if step.get("name") == artifact_step)
        artifact_name = artifact["with"]["name"]
        assert "${{ matrix.family }}" in artifact_name
        assert "${{ github.run_id }}" in artifact_name
        assert "${{ github.run_attempt }}" in artifact_name
        for family in ("iphone", "ipad"):
            observed_names.add(job["name"].replace("${{ matrix.family }}", family))
            observed_artifacts.add(artifact_name.replace("${{ matrix.family }}", family))
    assert len(observed_names) == 4
    assert len(observed_artifacts) == 4


def test_ios_family_matrix_has_four_distinct_blocking_checks_and_artifacts() -> None:
    _assert_ios_family_matrix_contract(_load_ci_workflow())


@pytest.mark.parametrize(
    "mutation",
    [
        "hard-code-selector-output",
        "build-default",
        "test-default",
        "build-env-default",
        "test-env-default",
    ],
)
def test_ios_matrix_contract_rejects_ui_destination_bypass(mutation: str) -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    smoke = jobs["ios-ui-smoke"]
    assert isinstance(smoke, dict)
    steps = smoke["steps"]
    assert isinstance(steps, list)
    step = next(
        step
        for step in steps
        if step.get("name") == "iOS UI smoke (build-for-testing + test-without-building)"
    )
    run = step["run"]
    assert isinstance(run, str)
    if mutation == "hard-code-selector-output":
        step["run"] = run.replace(
            'DESTINATION="${{ steps.select-destination.outputs.destination }}"',
            'DESTINATION="platform=iOS Simulator,name=iPhone 16"',
        )
    elif mutation in {"build-env-default", "test-env-default"}:
        before, between, after = run.split('destination = os.environ.get("DESTINATION", "")')
        substituted = 'destination = "platform=iOS Simulator,name=iPhone 16"'
        original = 'destination = os.environ.get("DESTINATION", "")'
        if mutation == "build-env-default":
            step["run"] = before + substituted + between + original + after
        else:
            step["run"] = before + original + between + substituted + after
    else:
        before, between, after = run.split('"-destination", destination')
        substituted = '"-destination", "platform=iOS Simulator,name=iPhone 16"'
        if mutation == "build-default":
            step["run"] = before + substituted + between + '"-destination", destination' + after
        else:
            step["run"] = before + '"-destination", destination' + between + substituted + after

    with pytest.raises(AssertionError):
        _assert_ios_family_matrix_contract(workflow)


def test_ios_matrix_contract_rejects_ui_job_budget_below_sequential_caps() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    smoke = jobs["ios-ui-smoke"]
    assert isinstance(smoke, dict)
    smoke["timeout-minutes"] = 25

    with pytest.raises(AssertionError):
        _assert_ios_family_matrix_contract(workflow)


@pytest.mark.parametrize("mutation", ["drop-ipad", "allow-fail-fast", "collide-artifact"])
def test_ios_matrix_contract_rejects_missing_family_or_artifact_collision(mutation: str) -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    unit = jobs["ios-tests"]
    assert isinstance(unit, dict)
    if mutation == "drop-ipad":
        unit["strategy"]["matrix"]["family"] = ["iphone"]
    elif mutation == "allow-fail-fast":
        unit["strategy"]["fail-fast"] = True
    else:
        artifact = next(
            step
            for step in unit["steps"]
            if step.get("name") == "Retain iOS unit result bundles and crash diagnostics"
        )
        artifact["with"]["name"] = "ios-unit-xcresult-${{ github.run_id }}"

    with pytest.raises(AssertionError):
        _assert_ios_release_build_contract(workflow)


@pytest.mark.parametrize(
    ("scope", "key", "value"),
    (
        ("job", "defaults", {"run": {"shell": "bash -c '{0} || true'"}}),
        ("job", "environment", "production"),
        ("job", "permissions", {"contents": "write", "id-token": "write"}),
        ("job", "name", "optional iOS check"),
        ("job", "runs-on", "self-hosted"),
        (
            "job",
            "steps",
            {"name": "Archive", "run": "xcodebuild archive && xcodebuild -exportArchive"},
        ),
        ("workflow", "permissions", {"contents": "write"}),
        ("workflow", "defaults", {"run": {"shell": "bash -c '{0} || true'"}}),
    ),
)
def test_ios_job_rejects_extra_execution_and_authority(scope: str, key: str, value: object) -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["ios-tests"]
    assert isinstance(job, dict)
    if key == "steps":
        steps = job["steps"]
        assert isinstance(steps, list)
        steps.append(value)
    else:
        target = workflow if scope == "workflow" else job
        target[key] = value

    with pytest.raises(AssertionError):
        _assert_ios_release_build_contract(workflow)


@pytest.mark.parametrize(
    "mutation",
    ("remove", "duplicate", "after-unit", "continue-on-error", "mask-exit"),
)
def test_ios_appstore_validator_stays_single_blocking_before_unit_run(mutation: str) -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    ios_tests = jobs["ios-tests"]
    assert isinstance(ios_tests, dict)
    steps = ios_tests["steps"]
    assert isinstance(steps, list)
    validator_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == IOS_APPSTORE_VERIFY_STEP_NAME
    )

    if mutation == "remove":
        steps.pop(validator_index)
    elif mutation == "duplicate":
        steps.insert(validator_index, dict(steps[validator_index]))
    elif mutation == "after-unit":
        validator_step = steps.pop(validator_index)
        unit_index = next(
            index for index, step in enumerate(steps) if step.get("name") == IOS_UNIT_STEP_NAME
        )
        steps.insert(unit_index + 1, validator_step)
    elif mutation == "continue-on-error":
        steps[validator_index]["continue-on-error"] = True
    else:
        steps[validator_index]["run"] = f"{IOS_APPSTORE_VERIFY_COMMAND} || true"

    with pytest.raises(AssertionError):
        _assert_ios_release_build_contract(workflow)


@pytest.mark.parametrize(
    "mutation",
    (
        "unit-continue-on-error",
        "unit-if-false",
        "build-check-false",
        "test-check-false",
        "build-cmd-rebound",
        "test-cmd-rebound",
        "unit-developer-dir-drift",
        "job-continue-on-error",
        "job-if-forced-false",
    ),
)
def test_ios_unit_and_job_reject_false_green_blocking_mutations(mutation: str) -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    ios_tests = jobs["ios-tests"]
    assert isinstance(ios_tests, dict)
    steps = ios_tests["steps"]
    assert isinstance(steps, list)
    unit_step = next(step for step in steps if step.get("name") == IOS_UNIT_STEP_NAME)
    assert isinstance(unit_step, dict)

    if mutation == "unit-continue-on-error":
        unit_step["continue-on-error"] = True
    elif mutation == "unit-if-false":
        unit_step["if"] = "false"
    elif mutation == "build-check-false":
        unit_run = unit_step["run"]
        assert isinstance(unit_run, str)
        unit_step["run"] = unit_run.replace(
            "result = subprocess.run(cmd, timeout=600, check=True)",
            "result = subprocess.run(cmd, timeout=600, check=False)",
            1,
        )
    elif mutation == "test-check-false":
        unit_run = unit_step["run"]
        assert isinstance(unit_run, str)
        unit_step["run"] = unit_run.replace(
            "subprocess.run(cmd, timeout=900, check=True)",
            "subprocess.run(cmd, timeout=900, check=False)",
            1,
        )
    elif mutation == "build-cmd-rebound":
        unit_run = unit_step["run"]
        assert isinstance(unit_run, str)
        unit_step["run"] = unit_run.replace(
            "result = subprocess.run(cmd, timeout=600, check=True)",
            'cmd = ["/usr/bin/true"]\n              '
            "result = subprocess.run(cmd, timeout=600, check=True)",
            1,
        )
    elif mutation == "test-cmd-rebound":
        unit_run = unit_step["run"]
        assert isinstance(unit_run, str)
        unit_step["run"] = unit_run.replace(
            "subprocess.run(cmd, timeout=900, check=True)",
            'cmd = ["/usr/bin/true"]\n              '
            "subprocess.run(cmd, timeout=900, check=True)",
            1,
        )
    elif mutation == "unit-developer-dir-drift":
        unit_step["env"] = {"DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer"}
    elif mutation == "job-continue-on-error":
        ios_tests["continue-on-error"] = True
    else:
        ios_tests["if"] = f"{IOS_TESTS_JOB_IF.rstrip()} && false\n"

    with pytest.raises(AssertionError):
        _assert_ios_release_build_contract(workflow)


def test_ios_release_build_run_digest_rejects_appended_command() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    ios_tests = jobs["ios-tests"]
    assert isinstance(ios_tests, dict)
    steps = ios_tests["steps"]
    assert isinstance(steps, list)
    release_step = next(step for step in steps if step.get("name") == IOS_RELEASE_BUILD_STEP_NAME)
    assert isinstance(release_step, dict)
    release_run = release_step["run"]
    assert isinstance(release_run, str)
    release_step["run"] = release_run + "\necho unexpected-release-command\n"

    with pytest.raises(AssertionError):
        _assert_ios_release_build_contract(workflow)


def test_ios_unit_tests_stay_in_blocking_ios_job() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    def active_run_for(job_id: str, step_name: str) -> str:
        job = jobs[job_id]
        assert isinstance(job, dict)
        assert job["needs"] == ["changes"]
        assert "needs.changes.outputs.ios == 'true'" in str(job["if"])
        steps = job["steps"]
        assert isinstance(steps, list)
        matching_steps = [step for step in steps if step.get("name") == step_name]
        assert len(matching_steps) == 1
        run = matching_steps[0]["run"]
        assert isinstance(run, str)
        active_lines = [
            line.strip()
            for line in run.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        return "\n".join(active_lines)

    ios_tests_run = active_run_for("ios-tests", "iOS tests (project-based, app scheme)")
    ios_ui_smoke_run = active_run_for(
        "ios-ui-smoke", "iOS UI smoke (build-for-testing + test-without-building)"
    )

    assert 'ONLY_TESTING="$(../scripts/ios_test_targets.sh)"' in ios_tests_run
    assert "::error::ONLY_TESTING is empty" in ios_tests_run
    assert "no test targets were found" in ios_tests_run
    assert '"xcodebuild", "test-without-building"' in ios_tests_run
    assert '"-skip-testing:PulsePlateUITests"' in ios_tests_run
    assert "exit 0" not in ios_tests_run
    assert 'ONLY_TESTING="$(../scripts/ios_test_targets.sh)"' not in ios_ui_smoke_run
    assert '"-only-testing:PulsePlateUITests/UISmokeTests/testLaunch"' in ios_ui_smoke_run
    assert "exit 0" not in ios_ui_smoke_run


def test_ios_swift_syntax_hook_is_direct_and_fail_closed_on_macos() -> None:
    pre_commit_text = PRE_COMMIT_CONFIG_PATH.read_text(encoding="utf-8")
    _assert_yaml_mapping_keys_are_unique(pre_commit_text)
    config = yaml.safe_load(pre_commit_text)
    assert isinstance(config, dict)
    repos = config["repos"]
    assert isinstance(repos, list)
    matching_hooks = [
        item
        for repo in repos
        if repo.get("repo") == "local"
        for item in repo.get("hooks", [])
        if item.get("id") == "ios-syntax-check"
    ]
    assert len(matching_hooks) == 1
    hook = matching_hooks[0]
    assert hook == {
        "id": "ios-syntax-check",
        "name": "ios syntax check (swift)",
        "entry": "scripts/ci/check_ios_swift_syntax.sh",
        "language": "system",
        "pass_filenames": True,
        "stages": ["pre-commit"],
        "files": r"(?s)^ios/.*\.swift$",
    }
    for accepted_path in (
        "ios/regular.swift",
        "ios/name with spaces.swift",
        "ios/line\nbreak.swift",
        "ios/-dash.swift",
    ):
        assert re.search(hook["files"], accepted_path)
    for rejected_path in (
        "ios/not-swift.txt",
        "frontend/not-ios.swift",
        "ios/directory.swift/nested.txt",
    ):
        assert re.search(hook["files"], rejected_path) is None

    script_text = IOS_SWIFT_SYNTAX_PATH.read_text(encoding="utf-8")
    assert IOS_SWIFT_SYNTAX_PATH.stat().st_mode & 0o111
    assert script_text.splitlines()[0] == "#!/usr/bin/env bash"
    executable_lines = [
        line.strip()
        for line in script_text.splitlines()[1:]
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert executable_lines == [
        "set -euo pipefail",
        'if [[ "$(/usr/bin/uname -s)" != "Darwin" ]]; then',
        'echo "SKIP: iOS Swift syntax check requires macOS; no syntax or build claim."',
        "exit 0",
        "fi",
        "if (( $# == 0 )); then",
        'echo "ERROR: iOS Swift syntax check requires at least one .swift file."',
        "exit 2",
        "fi",
        'for file in "$@"; do',
        'if [[ -z "$file" || "$file" != *.swift || ! -f "$file" ]]; then',
        'echo "ERROR: expected an existing .swift file: $file"',
        "exit 2",
        "fi",
        'if /usr/bin/xcrun swiftc -swift-version 5 -parse -- "$file"; then',
        "continue",
        "else",
        "status=$?",
        'exit "$status"',
        "fi",
        "done",
    ]

    for forbidden in (
        "swift build",
        "/dev/null",
        "2>&1",
        ">&",
        "eval ",
        "|| true",
        "|| echo",
    ):
        assert forbidden not in script_text


def test_machine_heavy_local_verify_deferral_contract_is_documented() -> None:
    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    runbook_text = RUNBOOK_PATH.read_text(encoding="utf-8")
    contract_text = ORCHESTRATION_CONTRACT_PATH.read_text(encoding="utf-8")

    required_tokens = (
        "Machine-heavy PR exception",
        "operator-approved",
        "`make verify` by default",
        "canonical current-head CI parity",
        "`lint`",
        "required/current-head checks",
        "relevant `test-main` matrix",
        "`diff-coverage`",
        "≥97%",
        "security/governance checks",
        "`check_merge_ready.py --require-auth`",
        "`make validate-changed`",
        "`pre-commit run --all-files`",
    )
    _assert_contains_all_tokens(agents_text, required_tokens)

    runbook_tokens = (
        "Machine-heavy CI/tooling PRs",
        "operator explicitly defers full local",
        "canonical current-head CI parity",
        "`lint`",
        "required/current-head checks",
        "relevant `test-main` matrix",
        "`diff-coverage` at ≥97%",
        "security/governance checks",
        "`check_merge_ready.py --require-auth`",
        "documented narrow bundle",
    )
    _assert_contains_all_tokens(runbook_text, runbook_tokens)

    contract_tokens = (
        "Operator-approved machine-heavy deferral",
        "fixed mapping document the deferral",
        "canonical current-head CI parity is green",
        "relevant `test-main` matrix",
        "`diff-coverage` ≥97%",
        "security/governance checks",
    )
    _assert_contains_all_tokens(contract_text, contract_tokens)


def test_ci_lint_all_files_pre_commit_uses_full_history_checkout() -> None:
    workflow = _load_ci_workflow()

    checkout_step = _job_step_by_name(workflow, job_id="lint", step_name="Checkout")
    assert checkout_step["uses"] == f"actions/checkout@{CHECKOUT_V7_SHA}"
    assert checkout_step["with"]["fetch-depth"] == 0

    pre_commit_step = _job_step_by_name(
        workflow,
        job_id="lint",
        step_name="Pre-commit (lint/format/security quick checks)",
    )
    assert "pre-commit run --all-files" in pre_commit_step["run"]


def test_ci_main_matrix_uses_full_history_for_git_evidence_guards() -> None:
    workflow = _load_ci_workflow()

    checkout_step = _job_step_by_name(workflow, job_id="test-main", step_name="Checkout")
    assert checkout_step["uses"] == f"actions/checkout@{CHECKOUT_V7_SHA}"
    assert checkout_step["with"]["fetch-depth"] == 0


@pytest.mark.parametrize("job_id", ("test-pr", "test-feature"))
def test_ci_history_jobs_do_not_persist_checkout_credentials(job_id: str) -> None:
    workflow = _load_ci_workflow()
    checkout_step = _job_step_by_name(workflow, job_id=job_id, step_name="Checkout")
    assert checkout_step == {
        "name": "Checkout",
        "uses": f"actions/checkout@{CHECKOUT_V7_SHA}",
        "with": {"fetch-depth": 0, "persist-credentials": False},
    }


def test_ci_lint_all_files_pre_commit_uses_project_node_version() -> None:
    workflow = _load_ci_workflow()

    setup_node_step = _job_step_by_name(workflow, job_id="lint", step_name="Setup Node.js")
    assert setup_node_step["uses"] == f"actions/setup-node@{SETUP_NODE_NODE24_SHA}"
    assert setup_node_step["with"]["node-version-file"] == "${{ env.FRONTEND_NODE_VERSION_FILE }}"

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    lint_steps = jobs["lint"]["steps"]
    step_names = [step.get("name") for step in lint_steps]
    assert step_names.index("Setup Node.js") < step_names.index(
        "Pre-commit (lint/format/security quick checks)"
    )


def _assert_ci_lint_node24_frontend_hook_dependency_contract(
    workflow: dict[str, object],
) -> None:
    """Assert the finite locked frontend dependency chain in the lint job."""

    assert workflow["defaults"] == {"run": {"shell": "bash"}}
    assert workflow["permissions"] == {"contents": "read"}

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    lint_job = jobs["lint"]
    assert isinstance(lint_job, dict)
    assert lint_job.get("if") == "${{ !cancelled() }}"
    for forbidden_key in (
        "continue-on-error",
        "defaults",
        "permissions",
        "environment",
    ):
        assert forbidden_key not in lint_job
    lint_steps = lint_job["steps"]
    assert isinstance(lint_steps, list)
    assert all(isinstance(step, dict) for step in lint_steps)
    health_gate = lint_steps[0]
    assert health_gate["name"] == "Enforce prerequisite results"
    assert health_gate["env"] == {
        "PRIVATE_PYTHON_PROXY_HEALTH_RESULT": ("${{ needs.private_python_proxy_health.result }}")
    }
    assert '"$PRIVATE_PYTHON_PROXY_HEALTH_RESULT" != "success"' in health_gate["run"]

    def unique_step(step_name: str) -> dict[str, object]:
        matches = [step for step in lint_steps if step.get("name") == step_name]
        assert len(matches) == 1
        return matches[0]

    checkout_step = unique_step("Checkout")
    assert checkout_step == {
        "name": "Checkout",
        "uses": f"actions/checkout@{CHECKOUT_V7_SHA}",
        "with": {"fetch-depth": 0, "persist-credentials": False},
    }

    setup_node_step = unique_step("Setup Node.js")
    assert setup_node_step == {
        "name": "Setup Node.js",
        "uses": f"actions/setup-node@{SETUP_NODE_NODE24_SHA}",
        "with": {
            "node-version-file": "${{ env.FRONTEND_NODE_VERSION_FILE }}",
            "cache": "npm",
            "cache-dependency-path": "frontend/package-lock.json",
        },
    }

    install_steps = [
        step for step in lint_steps if step.get("uses") == "./.github/actions/npm-ci-with-retry"
    ]
    assert len(install_steps) == 1
    install_step = install_steps[0]
    assert install_step == {
        "uses": "./.github/actions/npm-ci-with-retry",
        "with": {"working-directory": "frontend"},
    }

    pre_commit_step = unique_step("Pre-commit (lint/format/security quick checks)")
    assert pre_commit_step == {
        "name": "Pre-commit (lint/format/security quick checks)",
        "run": "pre-commit run --all-files --show-diff-on-failure",
        "env": {"SKIP": "no-commit-to-branch"},
    }

    checkout_index = lint_steps.index(checkout_step)
    setup_node_index = lint_steps.index(setup_node_step)
    assert checkout_index < setup_node_index
    assert lint_steps[setup_node_index + 1 : setup_node_index + 3] == [
        install_step,
        pre_commit_step,
    ]


def test_ci_lint_node24_frontend_hook_dependency_precedes_precommit() -> None:
    workflow = _load_ci_workflow()

    _assert_ci_lint_node24_frontend_hook_dependency_contract(workflow)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_install",
        "duplicate_install",
        "reordered_install",
        "conditional_install",
        "nonblocking_install",
        "wrong_directory",
        "cache_path_drift",
        "cache_mode_drift",
        "extra_install_input",
        "wrong_install_action",
        "alternate_install_run",
        "persisted_checkout_credentials",
        "decoy_npm_prefix_install",
        "decoy_absolute_npm_ci",
        "decoy_pnpm_install",
        "job_if",
        "job_continue_on_error",
        "job_defaults",
        "workflow_defaults",
        "workflow_permissions",
        "job_permissions",
        "job_environment",
    ),
)
def test_ci_lint_node24_frontend_hook_dependency_guard_rejects_drift(
    mutation: str,
) -> None:
    """Every bounded install, order, cache, or privilege drift must fail closed."""

    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    lint_job = jobs["lint"]
    assert isinstance(lint_job, dict)
    lint_steps = lint_job["steps"]
    assert isinstance(lint_steps, list)
    checkout_step = next(step for step in lint_steps if step.get("name") == "Checkout")
    setup_node_step = next(step for step in lint_steps if step.get("name") == "Setup Node.js")
    install_step = next(
        step for step in lint_steps if step.get("uses") == "./.github/actions/npm-ci-with-retry"
    )
    pre_commit_step = next(
        step
        for step in lint_steps
        if step.get("name") == "Pre-commit (lint/format/security quick checks)"
    )

    if mutation == "missing_install":
        lint_steps.remove(install_step)
    if mutation == "duplicate_install":
        lint_steps.append(dict(install_step))
    if mutation == "reordered_install":
        lint_steps.remove(install_step)
        lint_steps.insert(lint_steps.index(pre_commit_step) + 1, install_step)
    if mutation == "conditional_install":
        install_step["if"] = "${{ false }}"
    if mutation == "nonblocking_install":
        install_step["continue-on-error"] = True
    if mutation == "wrong_directory":
        install_with = install_step["with"]
        assert isinstance(install_with, dict)
        install_with["working-directory"] = "."
    if mutation == "cache_path_drift":
        setup_with = setup_node_step["with"]
        assert isinstance(setup_with, dict)
        setup_with["cache-dependency-path"] = "package-lock.json"
    if mutation == "cache_mode_drift":
        setup_with = setup_node_step["with"]
        assert isinstance(setup_with, dict)
        setup_with["cache"] = "yarn"
    if mutation == "extra_install_input":
        install_with = install_step["with"]
        assert isinstance(install_with, dict)
        install_with["npm-command"] = "install"
    if mutation == "wrong_install_action":
        install_step["uses"] = "actions/setup-node@untrusted"
    if mutation == "alternate_install_run":
        lint_steps.insert(lint_steps.index(pre_commit_step), {"name": "Alternate", "run": "npm ci"})
    if mutation == "persisted_checkout_credentials":
        checkout_with = checkout_step["with"]
        assert isinstance(checkout_with, dict)
        checkout_with["persist-credentials"] = True
    if mutation == "decoy_npm_prefix_install":
        lint_steps.insert(
            lint_steps.index(pre_commit_step),
            {"name": "Decoy", "run": "npm --prefix frontend install"},
        )
    if mutation == "decoy_absolute_npm_ci":
        lint_steps.insert(
            lint_steps.index(pre_commit_step),
            {"name": "Decoy", "run": "/usr/bin/npm ci --prefix frontend"},
        )
    if mutation == "decoy_pnpm_install":
        lint_steps.insert(
            lint_steps.index(pre_commit_step),
            {"name": "Decoy", "run": "corepack pnpm install --dir frontend"},
        )
    if mutation == "job_if":
        lint_job["if"] = "${{ false }}"
    if mutation == "job_continue_on_error":
        lint_job["continue-on-error"] = True
    if mutation == "job_defaults":
        lint_job["defaults"] = {"run": {"shell": "bash -c '{0} || true'"}}
    if mutation == "workflow_defaults":
        workflow["defaults"] = {"run": {"shell": "bash -c '{0} || true'"}}
    if mutation == "workflow_permissions":
        workflow["permissions"] = {"contents": "write"}
    if mutation == "job_permissions":
        lint_job["permissions"] = {"contents": "write"}
    if mutation == "job_environment":
        lint_job["environment"] = "production"

    with pytest.raises(AssertionError):
        _assert_ci_lint_node24_frontend_hook_dependency_contract(workflow)


def test_main_branch_python_sharded_runner_preserves_required_check_policy() -> None:
    workflow = _load_ci_workflow()
    workflow_env = workflow["env"]
    assert workflow_env["PULSEPLATE_PYTHON_INDEX_URL"] == "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
    assert (
        workflow_env["PULSEPLATE_PYTHON_TRUSTED_HOST"]
        == "${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
    )

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    test_main = jobs["test-main"]
    assert isinstance(test_main, dict)
    test_main_needs = test_main["needs"]
    assert isinstance(test_main_needs, list)
    assert "changes" in test_main_needs
    test_main_if = test_main["if"]
    assert isinstance(test_main_if, str)
    assert "github.ref == 'refs/heads/main'" in test_main_if
    assert "needs.changes.outputs.run_main_ci_diagnostic == 'true'" in test_main_if

    permissions = test_main["permissions"]
    assert permissions == {"contents": "read", "actions": "read"}

    test_main_env = test_main["env"]
    assert test_main_env == {
        "PULSEPLATE_PYTHON_INDEX_URL": "",
        "PULSEPLATE_PYTHON_TRUSTED_HOST": "",
    }

    steps = test_main["steps"]
    assert isinstance(steps, list)
    step_names = [step["name"] for step in steps]
    assert step_names.index("Resolve PR diagnostic package proxy") < step_names.index(
        "Setup Python environment"
    )
    assert step_names.index("Resolve protected package proxy") < step_names.index(
        "Setup Python environment"
    )

    pr_proxy_step = next(
        step for step in steps if step["name"] == "Resolve PR diagnostic package proxy"
    )
    assert pr_proxy_step["if"] == "github.event_name == 'pull_request'"
    assert pr_proxy_step["env"] == {
        "PULSEPLATE_PR_PYTHON_INDEX_URL": "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}",
        "PULSEPLATE_PR_PYTHON_TRUSTED_HOST": ("${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"),
    }
    pr_proxy_script = pr_proxy_step["run"]
    assert "secrets." not in pr_proxy_script
    assert "PULSEPLATE_PR_PYTHON_INDEX_URL" in pr_proxy_script
    assert 'if [[ -z "$resolved_index" ]]; then' in pr_proxy_script
    assert "credential-free diagnostic package proxy" in pr_proxy_script
    assert "must be credential-free" in pr_proxy_script
    assert "*://*@*)" in pr_proxy_script
    assert "DEVPI_CI_USER/DEVPI_CI_PASSWORD" in pr_proxy_script
    assert "exit 1" in pr_proxy_script
    assert "*$'\\n'*|*$'\\r'*)" in pr_proxy_script
    assert "must be single-line values" in pr_proxy_script
    assert "$GITHUB_ENV" in pr_proxy_script

    protected_proxy_step = next(
        step for step in steps if step["name"] == "Resolve protected package proxy"
    )
    assert protected_proxy_step["if"] == "github.event_name != 'pull_request'"
    assert protected_proxy_step["env"] == {
        "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL": "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}",
        "PULSEPLATE_PROTECTED_PYTHON_TRUSTED_HOST": ("${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"),
    }
    protected_proxy_script = protected_proxy_step["run"]
    assert "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL" in protected_proxy_script
    assert 'if [[ -z "$resolved_index" ]]; then' in protected_proxy_script
    assert "Set PULSEPLATE_PYTHON_INDEX_URL repository variable" in protected_proxy_script
    assert "exit 1" in protected_proxy_script
    assert "*://*@*)" in protected_proxy_script
    assert "PULSEPLATE_PYTHON_INDEX_URL must be credential-free" in protected_proxy_script
    assert "DEVPI_CI_USER/DEVPI_CI_PASSWORD" in protected_proxy_script
    assert "*$'\\n'*|*$'\\r'*)" in protected_proxy_script
    assert "must be single-line values" in protected_proxy_script
    assert "$GITHUB_ENV" in protected_proxy_script

    setup_python_step = next(step for step in steps if step["name"] == "Setup Python environment")
    assert setup_python_step["env"] == {
        "DEVPI_CI_USER": (
            "${{ github.event_name != 'pull_request' && "
            "github.ref == 'refs/heads/main' && secrets.DEVPI_CI_USER || '' }}"
        ),
        "DEVPI_CI_PASSWORD": (
            "${{ github.event_name != 'pull_request' && "
            "github.ref == 'refs/heads/main' && secrets.DEVPI_CI_PASSWORD || '' }}"
        ),
    }

    matrix = test_main["strategy"]["matrix"]["include"]
    assert isinstance(matrix, list)

    timeouts = {entry["python-version"]: entry["timeout-minutes"] for entry in matrix}
    assert timeouts == {"3.11": 60, "3.12": 90, "3.13": 90}

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    test_main_section = _extract_job_section(workflow_text, "  test-main:")
    assert "https://pypi.org/simple" not in test_main_section
    assert "pypi.org" not in test_main_section
    assert (
        "python-version: ${{ matrix.python-version == '3.13' && env.PYTHON_VERSION || "
        "matrix.python-version }}"
    ) in test_main_section

    py311_block = _extract_shell_conditional_block(
        test_main_section,
        'if [[ "$PYVER" == 3.11* ]]; then',
        '          elif [[ "$PYVER" == 3.12* ]]; then',
    )
    py312_block = _extract_shell_conditional_block(
        test_main_section,
        '          elif [[ "$PYVER" == 3.12* ]]; then',
        '          elif [[ "$PYVER" == 3.13* ]]; then',
    )
    py313_block = _extract_shell_conditional_block(
        test_main_section,
        '          elif [[ "$PYVER" == 3.13* ]]; then',
        "          else",
    )
    default_block = _extract_shell_conditional_block(
        test_main_section,
        "          else",
        "          fi",
    )
    shared_shard_runner_block = _extract_shell_conditional_block(
        test_main_section,
        '          if [[ -n "${MAIN_TEST_SHARDS:-}" ]]; then',
        '          echo "PYTEST_XDIST_ARGS=${PYTEST_XDIST_ARGS[*]}"',
    )

    assert "MAIN_TEST_SHARDS=4" in py311_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py311_block
    assert "export MAIN_TEST_SHARD_TIMEOUT_SECONDS=2400" in py311_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py311_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py311_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py311_block

    assert "MAIN_TEST_SHARDS=16" in py312_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py312_block
    assert "export MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800" in py312_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py312_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py312_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py312_block
    assert "TEST_STEP_STARTED_AT=" in test_main_section
    assert "TEST_STEP_FINISHED_AT=" in shared_shard_runner_block

    assert "MAIN_TEST_SHARDS=8" in py313_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py313_block
    assert "export MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800" in py313_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py313_block

    assert "python scripts/ci/run_main_test_shards.py" in shared_shard_runner_block
    assert '--python-version "${PYVER}"' in shared_shard_runner_block
    assert '--shard-count "${MAIN_TEST_SHARDS}"' in shared_shard_runner_block
    assert '--max-parallel "${MAIN_TEST_MAX_PARALLEL}"' in shared_shard_runner_block
    assert 'echo "MAIN_TEST_SHARDS=${MAIN_TEST_SHARDS}"' in shared_shard_runner_block
    assert 'echo "MAIN_TEST_MAX_PARALLEL=${MAIN_TEST_MAX_PARALLEL}"' in shared_shard_runner_block
    assert (
        'echo "MAIN_TEST_SHARD_TIMEOUT_SECONDS=${MAIN_TEST_SHARD_TIMEOUT_SECONDS:-default}"'
        in shared_shard_runner_block
    )
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in shared_shard_runner_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in shared_shard_runner_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in shared_shard_runner_block

    assert '-m "not slow"' in test_main_section
    assert '-m "not serial and not slow"' not in test_main_section
    assert '-m "serial and not slow"' not in test_main_section
    assert "--cov-append" not in test_main_section
    assert "tests/results-serial.xml" not in test_main_section
    assert "tests/results-py312-shard-*.xml" in test_main_section
    assert "tests/results-py313-shard-*.xml" in test_main_section
    assert (
        "name: coverage-main-xml-${{ matrix.python-version }}\n"
        "          path: coverage.xml\n"
        "          if-no-files-found: ignore\n"
        "          overwrite: true"
    ) in test_main_section
    assert (
        "name: junit-main-${{ matrix.python-version }}\n"
        "          path: |\n"
        "            tests/results.xml\n"
        "            tests/results-py311-shard-*.xml\n"
        "            tests/results-py312-shard-*.xml\n"
        "            tests/results-py313-shard-*.xml\n"
        "          if-no-files-found: ignore\n"
        "          overwrite: true"
    ) in test_main_section
    coverage_main_section = _extract_job_section(workflow_text, "  coverage-main:")
    assert "name: coverage-main-xml-3.11" in coverage_main_section
    assert "name: coverage-main-xml-3.12" in coverage_main_section
    assert "name: coverage-main-xml-3.13" in coverage_main_section

    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" in default_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in default_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in default_block


def test_python_test_jobs_install_frontend_dependencies_before_pytest() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    for job_name in PYTHON_TEST_JOB_NAMES:
        steps = jobs[job_name]["steps"]
        step_names = [step.get("name") for step in steps]
        root_index = step_names.index("Install root Node dependencies")
        frontend_index = step_names.index("Install frontend dependencies")
        clean_index = step_names.index("Clean Python cache")

        root_step = steps[root_index]
        frontend_step = steps[frontend_index]
        assert root_step["uses"] == "./.github/actions/npm-ci-with-retry"
        assert root_step["with"]["working-directory"] == "."
        assert frontend_step["uses"] == "./.github/actions/npm-ci-with-retry"
        assert frontend_step["with"]["working-directory"] == "frontend"
        assert root_index < frontend_index < clean_index


def test_ops_context_coverage_is_separate_and_required_by_diff_gate() -> None:
    """All four OPS CLIs must feed the canonical diff gate."""
    workflow = _load_ci_workflow()
    measure = _job_step_by_name(workflow, job_id="test-pr", step_name="Measure OPS CLI coverage")
    run = str(measure["run"])
    assert "--rcfile=/dev/null --branch" in run
    assert (
        "--include='scripts/ops/ops_context_report.py,scripts/ops/staging_runtime_diagnostics.py,scripts/ops/resource_cost_report.py,scripts/ops/resource_evidence_report.py'"
        in run
    )
    assert "--data-file=.coverage.ops-context -m pytest -q -p no:xdist" in run
    assert "tests/test_ops_context_report.py" in run
    assert "tests/test_staging_runtime_diagnostics.py" in run
    assert "tests/test_resource_cost_report.py" in run
    assert "tests/test_resource_evidence_report.py" in run
    assert "--data-file=.coverage.ops-context -o coverage-ops-context.xml" in run
    assert "--append" not in run
    assert "continue-on-error" not in measure and "if" not in measure
    upload = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Upload OPS context coverage artifact"
    )
    assert upload["with"] == {
        "name": "coverage-ops-context-${{ env.PYTHON_VERSION }}",
        "path": "coverage-ops-context.xml",
        "if-no-files-found": "error",
        "retention-days": 7,
    }
    assert "continue-on-error" not in upload and "if" not in upload
    download = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Download OPS context coverage artifact"
    )
    assert download["with"] == {
        "name": "coverage-ops-context-${{ env.PYTHON_VERSION }}",
        "path": "./ops-context-coverage",
    }
    assert "continue-on-error" not in download and "if" not in download
    gate = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Enforce diff coverage >= 97%"
    )
    assert gate["env"] == {"COVERAGE_THRESHOLD": 97}
    gate_run = str(gate["run"])
    assert "diff-cover ./coverage-artifacts/coverage.xml" in gate_run
    assert "./ops-context-coverage/coverage-ops-context.xml" in gate_run
    assert '--fail-under "${{ env.COVERAGE_THRESHOLD }}"' in gate_run
    assert "--exclude 'scripts" not in gate_run
    upload_application = _job_step_by_name(
        workflow, job_id="coverage-pr", step_name="Upload to Codecov"
    )
    application_with = upload_application["with"]
    assert isinstance(application_with, dict)
    assert application_with["files"] == "./coverage-artifacts/coverage.xml"


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "zero_hit",
        "missing",
        "malformed",
        "empty",
        "no_class",
        "wrong",
        "duplicate",
        "missing_staging",
        "missing_resource",
        "empty_resource",
        "missing_evidence",
        "empty_evidence",
    ],
)
def test_ops_context_workflow_rejects_missing_line_inventory(tmp_path: Path, case: str) -> None:
    """Execute the workflow's actual producer check with controlled XML documents."""
    import subprocess
    import sys

    workflow = _load_ci_workflow()
    measure = _job_step_by_name(workflow, job_id="test-pr", step_name="Measure OPS CLI coverage")
    run = str(measure["run"])
    marker = "python - <<'PY'\n"
    assert run.count(marker) == 1
    check = run.split(marker, 1)[1].rsplit("\nPY", 1)[0]
    filename = "other.py" if case == "wrong" else "scripts/ops/ops_context_report.py"
    hits = "0" if case == "zero_hit" else "1"
    lines = "" if case == "empty" else f'<line number="1" hits="{hits}"/>'
    cls = f'<class filename="{filename}"><lines>{lines}</lines></class>'
    staging = f'<class filename="scripts/ops/staging_runtime_diagnostics.py"><lines>{lines}</lines></class>'
    raw = "<coverage><packages><package><classes>" + ("" if case == "no_class" else cls)
    if case == "duplicate":
        raw += cls
    if case != "missing_staging":
        raw += staging
    if case != "missing_resource":
        resource_lines = "" if case == "empty_resource" else lines
        raw += (
            '<class filename="scripts/ops/resource_cost_report.py"><lines>'
            + resource_lines
            + "</lines></class>"
        )
    if case != "missing_evidence":
        evidence_lines = "" if case == "empty_evidence" else lines
        raw += (
            '<class filename="scripts/ops/resource_evidence_report.py"><lines>'
            + evidence_lines
            + "</lines></class>"
        )
    raw += "</classes></package></packages></coverage>"
    if case == "malformed":
        raw = "<coverage"
    if case != "missing":
        (tmp_path / "coverage-ops-context.xml").write_text(raw, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", check], cwd=tmp_path, capture_output=True, timeout=5, check=False
    )
    assert (result.returncode == 0) is (case in {"valid", "zero_hit"})


def test_fitchef_eval_coverage_is_separate_and_required_by_numeric_diff_gate() -> None:
    workflow = _load_ci_workflow()
    measure = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Measure FitChef eval CLI coverage"
    )
    run = str(measure["run"])
    assert "--rcfile=/dev/null --branch" in run
    assert (
        "--include='scripts/evals/collect_fitchef_answers.py,scripts/evals/fitchef_claim_assurance_eval.py'"
        in run
    )
    assert "--data-file=.coverage.fitchef-eval -m pytest -q -p no:xdist" in run
    assert "tests/test_fitchef_claim_assurance_eval.py" in run
    assert "--data-file=.coverage.fitchef-eval -o coverage-fitchef-eval.xml" in run
    assert measure["env"]["BLOCK_TEST_NETWORK"] == "true"
    assert "--append" not in run
    assert "continue-on-error" not in measure and "if" not in measure
    upload = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Upload FitChef eval coverage artifact"
    )
    assert upload["uses"] == f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}"
    assert upload["with"] == {
        "name": "coverage-fitchef-eval-${{ env.PYTHON_VERSION }}",
        "path": "coverage-fitchef-eval.xml",
        "if-no-files-found": "error",
        "retention-days": 7,
    }
    download = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Download FitChef eval coverage artifact"
    )
    assert download["uses"] == f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA}"
    assert download["with"] == {
        "name": "coverage-fitchef-eval-${{ env.PYTHON_VERSION }}",
        "path": "./fitchef-eval-coverage",
    }
    for step in (upload, download):
        assert "continue-on-error" not in step and "if" not in step
    gate = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Enforce diff coverage >= 97%"
    )
    assert gate["env"] == {"COVERAGE_THRESHOLD": 97}
    assert "./fitchef-eval-coverage/coverage-fitchef-eval.xml" in gate["run"]
    assert "--exclude 'scripts" not in gate["run"]
    assert '--fail-under "${{ env.COVERAGE_THRESHOLD }}"' in gate["run"]


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "zero_hit",
        "missing",
        "malformed",
        "empty",
        "no_class",
        "wrong",
        "duplicate",
        "extra",
        "missing_evaluator",
        "bad_line",
        "negative_hits",
        "duplicate_line",
    ],
)
def test_fitchef_eval_workflow_executes_exact_file_and_line_inventory_checker(
    tmp_path: Path,
    case: str,
) -> None:
    import subprocess
    import sys

    measure = _job_step_by_name(
        _load_ci_workflow(), job_id="test-pr", step_name="Measure FitChef eval CLI coverage"
    )
    marker = "python - <<'PY'\n"
    run = str(measure["run"])
    assert run.count(marker) == 1
    checker = run.split(marker, 1)[1].rsplit("\nPY", 1)[0]
    filename = "other.py" if case == "wrong" else "scripts/evals/collect_fitchef_answers.py"
    hits = "0" if case == "zero_hit" else "-1" if case == "negative_hits" else "1"
    number = "bad" if case == "bad_line" else "1"
    lines = "" if case == "empty" else f'<line number="{number}" hits="{hits}"/>'
    if case == "duplicate_line":
        lines += lines
    first = f'<class filename="{filename}"><lines>{lines}</lines></class>'
    second = f'<class filename="scripts/evals/fitchef_claim_assurance_eval.py"><lines>{lines}</lines></class>'
    raw = "<coverage><sources><source>.</source></sources><packages><package><classes>"
    if case != "no_class":
        raw += first
        if case == "duplicate":
            raw += first
        if case == "extra":
            raw += '<class filename="extra.py"><lines><line number="1" hits="1"/></lines></class>'
        if case != "missing_evaluator":
            raw += second
    raw += "</classes></package></packages></coverage>"
    if case == "malformed":
        raw = "<coverage"
    if case != "missing":
        (tmp_path / "coverage-fitchef-eval.xml").write_text(raw, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", checker], cwd=tmp_path, capture_output=True, timeout=5, check=False
    )
    assert (result.returncode == 0) is (case in {"valid", "zero_hit"})
    if case == "zero_hit":
        _assert_zero_hit_diff_consumer_rejects(tmp_path)


def _assert_zero_hit_diff_consumer_rejects(tmp_path: Path) -> None:
    import shutil
    import subprocess
    import sys

    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, *safe_git_config_args(), "init", "-q"],
        cwd=tmp_path,
        env=git_env_without_parent_state(),
        check=True,
        timeout=5,
    )
    source = tmp_path / "scripts/evals/collect_fitchef_answers.py"
    source.parent.mkdir(parents=True)
    source.write_text("after = 1\n", encoding="utf-8")
    patch = tmp_path / "changed.patch"
    patch.write_text(
        "diff --git a/scripts/evals/collect_fitchef_answers.py b/scripts/evals/collect_fitchef_answers.py\n"
        "--- a/scripts/evals/collect_fitchef_answers.py\n+++ b/scripts/evals/collect_fitchef_answers.py\n"
        "@@ -1 +1 @@\n-before = 0\n+after = 1\n",
        encoding="utf-8",
    )
    consumed = subprocess.run(
        [
            sys.executable,
            "-m",
            "diff_cover.diff_cover_tool",
            "coverage-fitchef-eval.xml",
            "--diff-file",
            str(patch),
            "--fail-under",
            "97",
        ],
        cwd=tmp_path,
        env=git_env_without_parent_state(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert consumed.returncode != 0
    assert "Coverage: 0%" in consumed.stdout + consumed.stderr


def test_fitchef_zero_hit_git_fixture_preserves_an_inherited_synthetic_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import shutil
    import subprocess

    git = shutil.which("git")
    assert git is not None
    parent = tmp_path / "synthetic-parent"
    parent.mkdir()
    clean = git_env_without_parent_state()
    subprocess.run(
        [git, *safe_git_config_args(), "init", "-q"], cwd=parent, env=clean, check=True, timeout=5
    )
    tracked = parent / "tracked.txt"
    tracked.write_text("synthetic unchanged parent\n", encoding="utf-8")
    subprocess.run(
        [git, *safe_git_config_args(), "add", "--", tracked.name],
        cwd=parent,
        env=clean,
        check=True,
        timeout=5,
    )
    metadata = parent / ".git"
    before = {name: (metadata / name).read_bytes() for name in ("config", "HEAD", "index")}
    inherited = {
        "GIT_DIR": str(metadata),
        "GIT_WORK_TREE": str(parent),
        "GIT_INDEX_FILE": str(metadata / "index"),
        "GIT_COMMON_DIR": str(metadata),
    }
    for name, value in inherited.items():
        monkeypatch.setenv(name, value)
    child = tmp_path / "synthetic-child"
    child.mkdir()
    xml = "<coverage><sources><source>.</source></sources><packages><package><classes>"
    for filename in (
        "scripts/evals/collect_fitchef_answers.py",
        "scripts/evals/fitchef_claim_assurance_eval.py",
    ):
        xml += f'<class filename="{filename}"><lines><line number="1" hits="0"/></lines></class>'
    xml += "</classes></package></packages></coverage>"
    (child / "coverage-fitchef-eval.xml").write_text(xml, encoding="utf-8")
    _assert_zero_hit_diff_consumer_rejects(child)
    assert {name: (metadata / name).read_bytes() for name in before} == before


ORCHESTRATION_COVERAGE_OWNERS = {
    "scripts/orchestration/pr_oracle_attachment.py": "tests/test_pr_oracle_attachment.py",
    "scripts/orchestration/experiment_runner_dispatch.py": "tests/test_experiment_runner_dispatch.py",
    "scripts/orchestration/qoder_dispatch_bridge.py": "tests/test_qoder_dispatch_bridge.py",
    "scripts/orchestration/task_bootstrap.py": "tests/test_task_bootstrap.py",
    "scripts/orchestration/render_codex_start_prompt.py": "tests/test_render_codex_start_prompt.py",
    "scripts/orchestration/experiment_runner.py": "tests/test_experiment_runner.py",
    "scripts/orchestration/experiment_runner_pr_creative_context.py": (
        "tests/test_experiment_runner_pr_creative_context.py"
    ),
    "scripts/orchestration/pr_review_evidence.py": "tests/test_pr_merge_readiness_gate.py",
    "scripts/orchestration/pr_review_closeout.py": "tests/test_pr_review_closeout.py",
    "scripts/orchestration/experiment_runner_pr_creative_context_contract.py": (
        "tests/test_experiment_runner_pr_creative_context.py"
    ),
}
ORCHESTRATION_COVERAGE_FILES = tuple(ORCHESTRATION_COVERAGE_OWNERS)


def test_orchestration_coverage_uses_isolated_required_same_run_numeric_report() -> None:
    """Bind producer ownership, existing test aliases and mandatory same-run numeric inputs."""
    workflow = _load_ci_workflow()
    measure = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Measure orchestration CLI coverage"
    )
    run = str(measure["run"])
    assert "--rcfile=/dev/null --branch" in run
    assert f"--include='{','.join(ORCHESTRATION_COVERAGE_FILES)}'" in run
    assert "--data-file=.coverage.orchestration -m pytest -q -p no:xdist" in run
    for target in ORCHESTRATION_COVERAGE_OWNERS.values():
        assert target in run
    assert "--data-file=.coverage.orchestration -o coverage-orchestration.xml" in run
    assert "--append" not in run
    assert measure["env"]["BLOCK_TEST_NETWORK"] == "true"
    upload = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Upload orchestration coverage artifact"
    )
    assert upload["uses"] == f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}"
    assert upload["with"] == {
        "name": "coverage-orchestration-${{ env.PYTHON_VERSION }}",
        "path": "coverage-orchestration.xml",
        "if-no-files-found": "error",
        "retention-days": 7,
    }
    download = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Download orchestration coverage artifact"
    )
    assert download["uses"] == f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA}"
    assert download["with"] == {
        "name": "coverage-orchestration-${{ env.PYTHON_VERSION }}",
        "path": "./orchestration-coverage",
    }
    for step in (measure, upload, download):
        assert "if" not in step and "continue-on-error" not in step
    gate = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Enforce diff coverage >= 97%"
    )
    assert gate["env"] == {"COVERAGE_THRESHOLD": 97}
    assert "./orchestration-coverage/coverage-orchestration.xml" in gate["run"]
    assert "--exclude 'scripts" not in gate["run"]
    assert '--fail-under "${{ env.COVERAGE_THRESHOLD }}"' in gate["run"]


@pytest.mark.parametrize("filename", ORCHESTRATION_COVERAGE_FILES)
@pytest.mark.parametrize(
    "mutation", ["valid", "omit-target", "comment-target", "omit-source", "comment-source"]
)
def test_orchestration_producer_executes_actual_source_owner_arguments(
    tmp_path: Path, filename: str, mutation: str
) -> None:
    """Observe real shell argv; the existing native XML checker executes unchanged."""
    import sys

    step = _job_step_by_name(
        _load_ci_workflow(), job_id="test-pr", step_name="Measure orchestration CLI coverage"
    )
    run = str(step["run"])
    token = filename if mutation.endswith("source") else ORCHESTRATION_COVERAGE_OWNERS[filename]
    if mutation != "valid":
        if mutation.endswith("source"):
            includes = ",".join(ORCHESTRATION_COVERAGE_FILES)
            replacement = ",".join(
                path for path in ORCHESTRATION_COVERAGE_FILES if path != filename
            )
            assert run.count(includes) == 1
            run = run.replace(includes, replacement, 1)
        else:
            assert run.count(token) == 1
            run = run.replace(token, "", 1)
        if mutation.startswith("comment"):
            run += f"\n# {token}\n"
    sources = list(ORCHESTRATION_COVERAGE_OWNERS)
    targets = list(dict.fromkeys(ORCHESTRATION_COVERAGE_OWNERS.values()))
    observer = tmp_path / "python"
    observer.write_text(
        "#!"
        + sys.executable
        + "\n"
        + "import json, os, subprocess, sys\nfrom pathlib import Path\n"
        + "from xml.etree import ElementTree\n"
        + f"sources = {sources!r}\ntargets = {targets!r}\n"
        + """
args = sys.argv[1:]
if args == ["-"]:
    result = subprocess.run([os.environ["ORCHESTRATION_TEST_PYTHON"], "-"], input=sys.stdin.buffer.read(), check=False)
    raise SystemExit(result.returncode)
if args[:3] == ["-m", "coverage", "run"]:
    if [arg for arg in args if arg.startswith("--include=")] != ["--include=" + ",".join(sources)]:
        raise SystemExit(41)
    if args[args.index("pytest") + 1:] != ["-q", "-p", "no:xdist", *targets]:
        raise SystemExit(42)
    Path("observed-targets.json").write_text(json.dumps(targets))
elif args[:3] == ["-m", "coverage", "xml"]:
    root = ElementTree.Element("coverage")
    classes = ElementTree.SubElement(root, "classes")
    for source in sources:
        lines = ElementTree.SubElement(ElementTree.SubElement(classes, "class", filename=source), "lines")
        ElementTree.SubElement(lines, "line", number="1", hits="0")
    ElementTree.ElementTree(root).write("coverage-orchestration.xml")
else:
    raise SystemExit(43)
""",
        encoding="utf-8",
    )
    observer.chmod(0o755)
    bash = shutil.which("bash", path=os.defpath)
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", run],
        cwd=tmp_path,
        env={
            "PATH": str(tmp_path) + os.pathsep + os.defpath,
            "ORCHESTRATION_TEST_PYTHON": sys.executable,
            "GH_TOKEN": "opaque",
            "GITHUB_TOKEN": "opaque",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    expected = 0 if mutation == "valid" else 41 if mutation.endswith("source") else 42
    assert result.returncode == expected, result.stderr
    if mutation == "valid":
        assert json.loads((tmp_path / "observed-targets.json").read_text()) == targets


@pytest.mark.parametrize("filename", ORCHESTRATION_COVERAGE_FILES)
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "zero_hit",
        "missing_xml",
        "malformed_xml",
        "missing_class",
        "duplicate_class",
        "extra_class",
        "empty",
        "bad_number",
        "zero_number",
        "duplicate_line",
        "bad_hits",
        "negative_hits",
        "missing_number",
        "missing_hits",
    ],
)
def test_orchestration_workflow_executes_exact_native_line_inventory_checker(
    tmp_path: Path, filename: str, case: str
) -> None:
    import sys
    from xml.etree import ElementTree

    run = str(
        _job_step_by_name(
            _load_ci_workflow(), job_id="test-pr", step_name="Measure orchestration CLI coverage"
        )["run"]
    )
    marker = "python - <<'PY'\n"
    assert run.count(marker) == 1
    checker = run.split(marker, 1)[1].rsplit("\nPY", 1)[0]
    tree = ElementTree.Element("coverage")
    classes = ElementTree.SubElement(tree, "classes")
    for path in ORCHESTRATION_COVERAGE_FILES:
        if path == filename and case == "missing_class":
            continue
        cls = ElementTree.SubElement(classes, "class", filename=path)
        lines = ElementTree.SubElement(cls, "lines")
        if path == filename and case == "empty":
            continue
        attrs = {"number": "1", "hits": "0" if case == "zero_hit" else "1"}
        if path == filename:
            if case in {"bad_number", "zero_number"}:
                attrs["number"] = "bad" if case == "bad_number" else "0"
            if case in {"bad_hits", "negative_hits"}:
                attrs["hits"] = "bad" if case == "bad_hits" else "-1"
            if case == "missing_number":
                attrs.pop("number")
            if case == "missing_hits":
                attrs.pop("hits")
        ElementTree.SubElement(lines, "line", **attrs)
        if path == filename and case == "duplicate_line":
            ElementTree.SubElement(lines, "line", **attrs)
    if case in {"duplicate_class", "extra_class"}:
        ElementTree.SubElement(
            classes, "class", filename=filename if case == "duplicate_class" else "extra.py"
        )
    raw = ElementTree.tostring(tree, encoding="unicode")
    if case == "malformed_xml":
        raw = "<coverage"
    if case != "missing_xml":
        (tmp_path / "coverage-orchestration.xml").write_text(raw, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", checker], cwd=tmp_path, capture_output=True, timeout=5, check=False
    )
    assert (result.returncode == 0) is (case in {"valid", "zero_hit"})


def _consume_orchestration_diff_fixture(
    tmp_path: Path,
    inventories: dict[str, list[int]],
    *,
    coverage_args: tuple[str, ...] | None = None,
    report_files: tuple[str, ...] = ("coverage-orchestration.xml",),
    report_error: tuple[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Delegate arithmetic to real diff-cover; synthetic lines are measurement controls."""
    import sys
    from xml.etree import ElementTree

    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, *safe_git_config_args(), "init", "-q"],
        cwd=tmp_path,
        env=git_env_without_parent_state(),
        check=True,
        timeout=5,
    )
    tree = ElementTree.Element("coverage")
    ElementTree.SubElement(ElementTree.SubElement(tree, "sources"), "source").text = "."
    classes = ElementTree.SubElement(tree, "classes")
    patches = []
    for filename, hits in inventories.items():
        source = tmp_path / filename
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("after = 1\n" * len(hits), encoding="utf-8")
        lines = ElementTree.SubElement(
            ElementTree.SubElement(classes, "class", filename=filename), "lines"
        )
        for number, hit in enumerate(hits, 1):
            ElementTree.SubElement(lines, "line", number=str(number), hits=str(hit))
        patches.append(
            f"diff --git a/{filename} b/{filename}\n--- a/{filename}\n+++ b/{filename}\n"
            f"@@ -1,{len(hits)} +1,{len(hits)} @@\n"
            + "-before = 0\n" * len(hits)
            + "+after = 1\n" * len(hits)
        )
    for filename in report_files:
        xml = tmp_path / filename
        xml.parent.mkdir(parents=True, exist_ok=True)
        xml.write_bytes(ElementTree.tostring(tree))
    if report_error is not None:
        filename, error = report_error
        assert filename in report_files
        if error == "missing":
            (tmp_path / filename).unlink()
        else:
            assert error == "malformed"
            (tmp_path / filename).write_text("<coverage>", encoding="utf-8")
    patch = tmp_path / "changed.patch"
    patch.write_text("".join(patches), encoding="utf-8")
    args = (
        coverage_args
        if coverage_args is not None
        else (*(str(tmp_path / name) for name in report_files), "--fail-under", "97")
    )
    return subprocess.run(
        [sys.executable, "-m", "diff_cover.diff_cover_tool", *args, "--diff-file", str(patch)],
        cwd=tmp_path,
        env=git_env_without_parent_state(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize("filename", ORCHESTRATION_COVERAGE_FILES)
def test_orchestration_numeric_diff_consumer_rejects_each_zero_hit_owner(
    tmp_path: Path, filename: str
) -> None:
    result = _consume_orchestration_diff_fixture(tmp_path, {filename: [0]})
    assert result.returncode != 0
    assert "Total:   1 line" in result.stdout
    assert "Coverage: 0%" in result.stdout


@pytest.mark.parametrize("uncovered,expected_pass", [(3, True), (4, False)])
def test_orchestration_numeric_diff_consumer_retains_aggregate_97_percent(
    tmp_path: Path, uncovered: int, expected_pass: bool
) -> None:
    result = _consume_orchestration_diff_fixture(
        tmp_path,
        {
            ORCHESTRATION_COVERAGE_FILES[0]: [0] * uncovered,
            ORCHESTRATION_COVERAGE_FILES[1]: [1] * (100 - uncovered),
        },
    )
    assert (result.returncode == 0) is expected_pass
    assert "Total:   100 lines" in result.stdout
    assert f"Coverage: {100 - uncovered}%" in result.stdout


CI_DIFF_COVERAGE_REPORTS = (
    "./coverage-artifacts/coverage.xml",
    "./ops-context-coverage/coverage-ops-context.xml",
    "./fitchef-eval-coverage/coverage-fitchef-eval.xml",
    "./orchestration-coverage/coverage-orchestration.xml",
    "./fitchef-agent-coverage/coverage-fitchef-agent.xml",
)
CI_DIFF_COVERAGE_RUN = r"""coverage_root="$(pwd -P)"
coverage_excludes=(
  "${coverage_root}/frontend/**"
  "${coverage_root}/alembic/**"
  "${coverage_root}/releases/**"
  "${coverage_root}/cache/**"
  "${coverage_root}/data/**"
  "${coverage_root}/external/**"
  "${coverage_root}/htmlcov/**"
  "${coverage_root}/coverage/**"
  'conftest.py'
  "${coverage_root}/tests/**"
  '*.json'
  '*.lock'
  '*.md'
  '*.yml'
  '*.yaml'
  '*.toml'
  '*.txt'
)
diff-cover ./coverage-artifacts/coverage.xml \
  ./ops-context-coverage/coverage-ops-context.xml \
  ./fitchef-eval-coverage/coverage-fitchef-eval.xml \
  ./orchestration-coverage/coverage-orchestration.xml \
  ./fitchef-agent-coverage/coverage-fitchef-agent.xml \
  --compare-branch "${{ github.base_ref }}" \
  --fail-under "${{ env.COVERAGE_THRESHOLD }}" \
  --exclude "${coverage_excludes[@]}"
"""


def _assert_ci_diff_coverage_exclusion_contract(workflow: dict[str, object]) -> None:
    """Bind the actual ordered carrier and blocking seam; do not interpret Bash."""
    jobs = cast(dict[str, object], workflow["jobs"])
    job = cast(dict[str, object], jobs["diff-coverage"])
    assert "continue-on-error" not in job and "defaults" not in job
    assert workflow["defaults"] == {"run": {"shell": "bash"}}
    assert job["if"] == (
        "${{ !cancelled() && github.event_name == 'pull_request' && "
        "(needs.changes.result != 'success' || "
        "needs.changes.outputs.run_backend_blocking == 'true') }}"
    )
    assert job["needs"] == ["changes", "pr_scope_guard", "private_python_proxy_health", "test-pr"]
    steps = cast(list[dict[str, object]], job["steps"])
    matching = [step for step in steps if step.get("name") == "Enforce diff coverage >= 97%"]
    assert len(matching) == 1
    gate = matching[0]
    assert gate == {
        "name": "Enforce diff coverage >= 97%",
        "env": {"COVERAGE_THRESHOLD": 97},
        "run": CI_DIFF_COVERAGE_RUN,
    }
    downloads = [
        step
        for step in steps
        if step.get("uses") == f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA}"
    ]
    assert [step["with"] for step in downloads] == [
        {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
        {
            "name": "coverage-ops-context-${{ env.PYTHON_VERSION }}",
            "path": "./ops-context-coverage",
        },
        {
            "name": "coverage-fitchef-eval-${{ env.PYTHON_VERSION }}",
            "path": "./fitchef-eval-coverage",
        },
        {
            "name": "coverage-orchestration-${{ env.PYTHON_VERSION }}",
            "path": "./orchestration-coverage",
        },
        {
            "name": "coverage-fitchef-agent-${{ env.PYTHON_VERSION }}",
            "path": "./fitchef-agent-coverage",
        },
    ]
    assert all("if" not in step and "continue-on-error" not in step for step in downloads)
    assert all(steps.index(step) < steps.index(gate) for step in downloads)
    base = _job_step_by_name(workflow, job_id="diff-coverage", step_name="Fetch base branch")
    assert base == {
        "name": "Fetch base branch",
        "run": (
            "git fetch --no-tags --prune origin "
            '"${{ github.base_ref }}":"${{ github.base_ref }}"\n'
            'git branch --force base "${{ github.base_ref }}"\n'
        ),
    }
    assert steps.index(base) < steps.index(gate)


def test_ci_diff_coverage_node24_preserves_exact_exclusions_and_required_inputs() -> None:
    """Bind the reviewed exclusion vector and mandatory coverage-report wiring."""
    _assert_ci_diff_coverage_exclusion_contract(_load_ci_workflow())


@pytest.mark.parametrize(
    "mutation",
    (
        "repeated",
        "missing",
        "duplicate",
        "extra",
        "relative",
        "broad",
        "unquoted",
        "report",
        "threshold",
        "base",
        "optional",
        "masked",
        "duplicate_step",
        "job_optional",
        "job_if",
        "job_defaults",
        "workflow_defaults",
        "download",
    ),
)
def test_ci_diff_coverage_node24_rejects_carrier_or_blocking_drift(mutation: str) -> None:
    """Reject finite carrier mutations and optional or error-masked coverage wiring."""
    workflow = _load_ci_workflow()
    jobs = cast(dict[str, object], workflow["jobs"])
    job = cast(dict[str, object], jobs["diff-coverage"])
    steps = cast(list[dict[str, object]], job["steps"])
    gate = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Enforce diff coverage >= 97%"
    )
    run = cast(str, gate["run"])
    changes = {
        "repeated": ('--exclude "${coverage_excludes[@]}"', "--exclude '*.json' --exclude '*.txt'"),
        "missing": ('  "${coverage_root}/frontend/**"\n', ""),
        "duplicate": ("  '*.txt'\n", "  '*.txt'\n  '*.txt'\n"),
        "extra": ("  '*.txt'\n", "  '*.txt'\n  '*.py'\n"),
        "relative": ('"${coverage_root}/frontend/**"', "'frontend/**'"),
        "broad": ('"${coverage_root}/frontend/**"', "'*/frontend/**'"),
        "unquoted": ('"${coverage_excludes[@]}"', "${coverage_excludes[@]}"),
        "report": ("  ./ops-context-coverage/coverage-ops-context.xml \\\n", ""),
        "threshold": ('--fail-under "${{ env.COVERAGE_THRESHOLD }}"', "--fail-under 96"),
        "base": ('--compare-branch "${{ github.base_ref }}"', "--compare-branch HEAD"),
        "masked": (
            '--exclude "${coverage_excludes[@]}"',
            '--exclude "${coverage_excludes[@]}" || true',
        ),
    }
    if mutation in changes:
        before, after = changes[mutation]
        assert before in run
        gate["run"] = run.replace(before, after, 1)
    elif mutation == "optional":
        gate["if"] = "${{ false }}"
    elif mutation == "duplicate_step":
        steps.append(dict(gate))
    elif mutation == "job_optional":
        job["continue-on-error"] = True
    elif mutation == "job_if":
        job["if"] = "${{ false }}"
    elif mutation == "job_defaults":
        job["defaults"] = {"run": {"working-directory": "frontend"}}
    elif mutation == "workflow_defaults":
        workflow["defaults"] = {"run": {"shell": "bash {0} || true"}}
    else:
        assert mutation == "download"
        steps.remove(
            _job_step_by_name(
                workflow,
                job_id="diff-coverage",
                step_name="Download OPS context coverage artifact",
            )
        )
    with pytest.raises(AssertionError):
        _assert_ci_diff_coverage_exclusion_contract(workflow)


def _native_ci_diff_coverage_args(root: Path) -> tuple[str, ...]:
    """Run actual production Bash, capturing argv without a coverage result claim."""
    bash = shutil.which("bash")
    assert bash is not None
    gate = _job_step_by_name(
        _load_ci_workflow(), job_id="diff-coverage", step_name="Enforce diff coverage >= 97%"
    )
    run = (
        cast(str, gate["run"])
        .replace("${{ github.base_ref }}", "base")
        .replace("${{ env.COVERAGE_THRESHOLD }}", "97")
    )
    result = subprocess.run(
        [bash, "--noprofile", "--norc", "-c", "diff-cover() { printf '%s\\0' \"$@\"; }\n" + run],
        cwd=root,
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stderr == "" and result.stdout.endswith("\0")
    return tuple(result.stdout[:-1].split("\0"))


def test_ci_diff_coverage_native_parser_and_path_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Check actual CI argv and native matching across the declared path boundaries."""
    from diff_cover.diff_cover_tool import parse_coverage_args
    from diff_cover.diff_reporter import GitDiffReporter

    root = tmp_path / "working root with spaces"
    root.mkdir()
    monkeypatch.chdir(root)
    argv = _native_ci_diff_coverage_args(root)
    assert argv.count("--exclude") == 1
    parsed = parse_coverage_args(list(argv))
    directories = (
        "frontend",
        "alembic",
        "releases",
        "cache",
        "data",
        "external",
        "htmlcov",
        "coverage",
    )
    expected = [f"{root.resolve()}/{name}/**" for name in directories]
    expected += [
        "conftest.py",
        f"{root.resolve()}/tests/**",
        "*.json",
        "*.lock",
        "*.md",
        "*.yml",
        "*.yaml",
        "*.toml",
        "*.txt",
    ]
    assert parsed["exclude"] == expected and len(parsed["exclude"]) == 17
    assert parsed["coverage_files"] == list(CI_DIFF_COVERAGE_REPORTS)
    assert parsed["compare_branch"] == "base" and parsed["fail_under"] == 97
    reporter = GitDiffReporter(exclude=parsed["exclude"])
    excluded = [f"{name}/nested/helper.py" for name in (*directories, "tests")]
    excluded += [
        "app/nested/conftest.py",
        *(f"app/item.{suffix}" for suffix in ("json", "lock", "md", "yml", "yaml", "toml", "txt")),
    ]
    retained = [
        "app/helper.py",
        "app/frontend/helper.py",
        "scripts/ops/ops_context_report.py",
        "scripts/evals/collect_fitchef_answers.py",
        *ORCHESTRATION_COVERAGE_FILES,
    ]
    retained += [f"{name}-backup/helper.py" for name in (*directories, "tests")]
    retained += [f"app/{name}/helper.py" for name in (*directories, "tests")]
    retained += [f"../outside/{name}/helper.py" for name in (*directories, "tests")]
    retained += [str(root.resolve()) + "-prefix/frontend/helper.py", "app/helper with spaces.py"]
    for name in excluded:
        assert reporter._is_path_excluded(name), name
        assert reporter._is_path_excluded(os.path.abspath(name)), name
    for name in retained:
        assert not reporter._is_path_excluded(name), name
        assert not reporter._is_path_excluded(os.path.abspath(name)), name
    repeated = parse_coverage_args(
        [*argv[: argv.index("--exclude")], "--exclude", *expected[:-1], "--exclude", expected[-1]]
    )
    assert repeated["exclude"] == ["*.txt"]
    assert not GitDiffReporter(exclude=repeated["exclude"])._is_path_excluded("frontend/helper.py")
    assert not GitDiffReporter(exclude=["frontend/**"])._is_path_excluded("frontend/helper.py")
    assert GitDiffReporter(exclude=["*/frontend/**"])._is_path_excluded("app/frontend/helper.py")


@pytest.mark.parametrize(
    "filename",
    (
        "frontend/helper.py",
        "alembic/helper.py",
        "releases/helper.py",
        "cache/helper.py",
        "data/helper.py",
        "external/helper.py",
        "htmlcov/helper.py",
        "coverage/helper.py",
        "conftest.py",
        "tests/helper.py",
        "app/item.json",
        "app/item.lock",
        "app/item.md",
        "app/item.yml",
        "app/item.yaml",
        "app/item.toml",
        "app/item.txt",
    ),
)
def test_ci_diff_coverage_native_cli_excludes_each_intended_class(
    tmp_path: Path, filename: str
) -> None:
    """Prove each class is measurable unfiltered before its excluded no-lines result."""
    args = _native_ci_diff_coverage_args(tmp_path)
    unfiltered = _consume_orchestration_diff_fixture(
        tmp_path,
        {filename: [0]},
        coverage_args=args[: args.index("--exclude")],
        report_files=CI_DIFF_COVERAGE_REPORTS,
    )
    assert unfiltered.returncode == 1, (unfiltered.stdout, unfiltered.stderr)
    assert "Total:   1 line" in unfiltered.stdout
    assert "Coverage: 0%" in unfiltered.stdout
    assert "Failure. Coverage is below 97%." in unfiltered.stderr
    result = _consume_orchestration_diff_fixture(
        tmp_path, {filename: [0]}, coverage_args=args, report_files=CI_DIFF_COVERAGE_REPORTS
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "No lines with coverage information in this diff." in result.stdout
    assert "Coverage: 100%" not in result.stdout


@pytest.mark.parametrize(
    "filename",
    (
        "app/helper.py",
        "app/frontend/helper.py",
        "frontend-backup/helper.py",
        "scripts/ops/ops_context_report.py",
        "scripts/evals/collect_fitchef_answers.py",
        *ORCHESTRATION_COVERAGE_FILES,
    ),
)
def test_ci_diff_coverage_native_cli_retains_zero_hit_owners(tmp_path: Path, filename: str) -> None:
    """Keep zero-hit application and dedicated tooling sources measurable."""
    args = _native_ci_diff_coverage_args(tmp_path)
    result = _consume_orchestration_diff_fixture(
        tmp_path, {filename: [0]}, coverage_args=args, report_files=CI_DIFF_COVERAGE_REPORTS
    )
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "Total:   1 line" in result.stdout and "Coverage: 0%" in result.stdout
    assert "Failure. Coverage is below 97%." in result.stderr


@pytest.mark.parametrize("uncovered,expected_pass", ((3, True), (4, False)))
def test_ci_diff_coverage_native_cli_preserves_97_boundary(
    tmp_path: Path, uncovered: int, expected_pass: bool
) -> None:
    """Check native 97% acceptance and 96% refusal at a working root with spaces."""
    root = tmp_path / "root with spaces"
    root.mkdir()
    args = _native_ci_diff_coverage_args(root)
    result = _consume_orchestration_diff_fixture(
        root,
        {"app/helper.py": [0] * uncovered + [1] * (100 - uncovered)},
        coverage_args=args,
        report_files=CI_DIFF_COVERAGE_REPORTS,
    )
    assert (result.returncode == 0) is expected_pass, (result.stdout, result.stderr)
    assert "Total:   100 lines" in result.stdout
    assert f"Coverage: {100 - uncovered}%" in result.stdout


@pytest.mark.parametrize("report", CI_DIFF_COVERAGE_REPORTS)
@pytest.mark.parametrize(
    "error,diagnostic", (("missing", "FileNotFoundError"), ("malformed", "ParseError"))
)
def test_ci_diff_coverage_native_cli_refuses_each_invalid_report(
    tmp_path: Path, report: str, error: str, diagnostic: str
) -> None:
    """Reject each missing or malformed mandatory XML without coverage-success output."""
    args = _native_ci_diff_coverage_args(tmp_path)
    result = _consume_orchestration_diff_fixture(
        tmp_path,
        {"app/helper.py": [1]},
        coverage_args=args,
        report_files=CI_DIFF_COVERAGE_REPORTS,
        report_error=(report, error),
    )
    assert result.returncode != 0 and diagnostic in result.stderr, (result.stdout, result.stderr)
    assert "Coverage:" not in result.stdout
    assert "No lines with coverage information" not in result.stdout


@pytest.mark.parametrize(
    "case,diagnostic",
    (
        ("cli", "invalid float value"),
        ("config", "FileNotFoundError"),
        ("git", "Could not find the branch to compare to. Does 'base' exist?"),
        ("import", "No module named 'diff_cover'"),
    ),
)
def test_ci_diff_coverage_native_prerequisites_are_not_coverage_rejection(
    tmp_path: Path, case: str, diagnostic: str
) -> None:
    """Distinguish CLI, config, Git, and import failures from coverage-threshold refusal."""
    import sys

    args = _native_ci_diff_coverage_args(tmp_path)
    prepared = _consume_orchestration_diff_fixture(
        tmp_path, {"app/helper.py": [1]}, coverage_args=args, report_files=CI_DIFF_COVERAGE_REPORTS
    )
    assert prepared.returncode == 0, (prepared.stdout, prepared.stderr)
    python_flags = ("-I", "-S") if case == "import" else ()
    if case == "cli":
        args += ("--fail-under", "invalid")
    elif case == "config":
        args += ("--config-file", "missing-config.toml")
    result = subprocess.run(
        [sys.executable, *python_flags, "-m", "diff_cover.diff_cover_tool", *args],
        cwd=tmp_path,
        env=git_env_without_parent_state(),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode != 0 and diagnostic in result.stderr, (result.stdout, result.stderr)
    assert "Coverage:" not in result.stdout
    assert "Failure. Coverage is below 97%." not in result.stderr


FOUNDATION_LINT_COMMAND = (
    'eslint --config eslint.config.js "src/api/*.ts" "src/api/premium/*.ts" '
    "src/lib/analytics.ts --max-warnings=0"
)
FOUNDATION_NATIVE_STEP = "Verify foundation ESLint native controls"
FOUNDATION_LINT_STEP = "Lint API and foundation scope"
UI_LINT_COMMAND = (
    'eslint --config eslint.config.js "src/components/ui/**/*.{ts,tsx}" --max-warnings=0'
)
UI_LINT_STEP = "Lint UI primitives"
# Public SHA256 integrity digests bind the tracked config/workflow, not credentials.
# Native ESLint/npm execution supplies tool semantics; Python does not interpret JS or shell.
FOUNDATION_CONFIG_SHA256 = (
    "33c678e5f8a86963dae24419a2d2e4f798d300c477ff7756046539edbe3c1214"  # pragma: allowlist secret
)
FOUNDATION_NATIVE_RUN_SHA256 = (
    "540e1b891e7980920587e5d47806ddc1e8c8b45e7ffb0b3e7ec85729b7768739"  # pragma: allowlist secret
)


def _assert_frontend_node24_foundation_contract(
    package: dict[str, object], workflow: dict[str, object], config_source: str
) -> None:
    """Bind the existing exact production command and reviewed CI control carriers."""
    scripts = package["scripts"]
    dependencies = package["devDependencies"]
    assert isinstance(scripts, dict)
    assert isinstance(dependencies, dict)
    assert scripts["lint:foundation"] == FOUNDATION_LINT_COMMAND
    assert scripts["lint:ui"] == UI_LINT_COMMAND
    assert dependencies["@eslint/js"] == "9.39.3"
    assert dependencies["typescript-eslint"] == "8.71.0"
    assert "type" not in package
    assert hashlib.sha256(config_source.encode("utf-8")).hexdigest() == FOUNDATION_CONFIG_SHA256
    workflow_defaults = workflow.get("defaults", {})
    assert isinstance(workflow_defaults, dict)
    workflow_run = workflow_defaults.get("run", {})
    assert isinstance(workflow_run, dict)
    assert "shell" not in workflow_run
    workflow_env = workflow.get("env", {})
    assert isinstance(workflow_env, dict)
    assert not {"NODE_OPTIONS", "NODE_PATH"}.intersection(workflow_env)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["build-and-test"]
    assert isinstance(job, dict)
    assert "if" not in job and "continue-on-error" not in job
    assert job["defaults"] == {"run": {"working-directory": "frontend"}}
    job_env = job.get("env", {})
    assert isinstance(job_env, dict)
    assert not {"NODE_OPTIONS", "NODE_PATH"}.intersection(job_env)
    steps = job["steps"]
    assert isinstance(steps, list)
    installs = [
        step
        for step in steps
        if isinstance(step, dict)
        and (
            step.get("name") == "Install dependencies"
            or step.get("uses") == "./.github/actions/npm-ci-with-retry"
        )
    ]
    assert len(installs) == 1
    install = installs[0]
    assert install == {
        "name": "Install dependencies",
        "uses": "./.github/actions/npm-ci-with-retry",
        "with": {"working-directory": "frontend"},
    }
    native_steps = [
        step
        for step in steps
        if isinstance(step, dict)
        and (
            step.get("name") == FOUNDATION_NATIVE_STEP
            or isinstance(step.get("run"), str)
            and hashlib.sha256(cast(str, step["run"]).encode("utf-8")).hexdigest()
            == FOUNDATION_NATIVE_RUN_SHA256
        )
    ]
    assert len(native_steps) == 1
    native = native_steps[0]
    assert set(native) == {"name", "env", "run"}
    assert native["env"] == {"ESLINT_CONTROL_TIMEOUT_MS": "15000"}
    assert native["name"] == FOUNDATION_NATIVE_STEP
    assert isinstance(native["run"], str)
    assert hashlib.sha256(native["run"].encode("utf-8")).hexdigest() == FOUNDATION_NATIVE_RUN_SHA256
    lint_steps = [
        step
        for step in steps
        if isinstance(step, dict)
        and (
            step.get("name") == FOUNDATION_LINT_STEP or step.get("run") == "npm run lint:foundation"
        )
    ]
    assert len(lint_steps) == 1
    lint = lint_steps[0]
    assert lint == {"name": FOUNDATION_LINT_STEP, "run": "npm run lint:foundation"}
    ui_steps = [
        step
        for step in steps
        if isinstance(step, dict)
        and (step.get("name") == UI_LINT_STEP or step.get("run") == "npm run lint:ui")
    ]
    assert len(ui_steps) == 1
    ui = ui_steps[0]
    assert ui == {"name": UI_LINT_STEP, "run": "npm run lint:ui"}
    assert steps.index(install) < steps.index(native) < steps.index(lint) < steps.index(ui)
    for name, command in (
        ("Run vitest suite", "npm run test -- --coverage"),
        ("Build frontend", "npm run build"),
    ):
        consumers = [
            step
            for step in steps
            if isinstance(step, dict) and (step.get("name") == name or step.get("run") == command)
        ]
        assert len(consumers) == 1
        consumer = consumers[0]
        assert consumer["name"] == name and consumer["run"] == command
        assert not {"if", "continue-on-error", "shell", "working-directory"}.intersection(consumer)
        consumer_env = consumer.get("env", {})
        assert isinstance(consumer_env, dict)
        assert not {"NODE_OPTIONS", "NODE_PATH"}.intersection(consumer_env)
        assert steps.index(ui) < steps.index(consumer)


def test_frontend_node24_foundation_command_and_native_controls_are_blocking() -> None:
    """Structural wiring remains runnable on a Python-only nightly worker."""
    package = json.loads(FRONTEND_PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    config_source = (REPO_ROOT / "frontend/eslint.config.js").read_text(encoding="utf-8")
    _assert_frontend_node24_foundation_contract(package, workflow, config_source)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_script",
        "optional_script",
        "masked_script",
        "implicit_config",
        "empty_selector",
        "missing_premium",
        "missing_analytics",
        "warnings_allowed",
        "missing_dependency",
        "global_module_mode",
        "broad_ignore",
        "weakened_rule",
        "missing_native",
        "duplicate_native",
        "renamed_duplicate_native",
        "missing_lint",
        "duplicate_lint",
        "renamed_duplicate_lint",
        "install_if",
        "install_optional",
        "native_if",
        "native_optional",
        "native_shell",
        "native_cwd",
        "native_env",
        "lint_if",
        "lint_optional",
        "lint_shell",
        "lint_cwd",
        "lint_optional_command",
        "lint_masked_command",
        "controls_before_install",
        "lint_before_controls",
        "job_if",
        "job_optional",
        "job_cwd",
        "job_shell",
        "workflow_shell",
        "job_startup_env",
        "workflow_startup_env",
        "missing_clean_control",
        "missing_error_control",
        "missing_warning_control",
        "missing_script_control",
        "missing_config_control",
        "missing_empty_control",
        "missing_ignored_control",
        "ambient_child_env",
    ),
)
def test_frontend_node24_foundation_guard_rejects_weakened_wiring(mutation: str) -> None:
    """Reject the finite declared drift classes without an npm/JS/shell interpreter."""
    package = json.loads(FRONTEND_PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    config_source = (REPO_ROOT / "frontend/eslint.config.js").read_text(encoding="utf-8")
    scripts = package["scripts"]
    job = cast(dict[str, object], cast(dict[str, object], workflow["jobs"])["build-and-test"])
    steps = cast(list[dict[str, object]], job["steps"])
    install = next(step for step in steps if step.get("name") == "Install dependencies")
    native = next(step for step in steps if step.get("name") == FOUNDATION_NATIVE_STEP)
    lint = next(step for step in steps if step.get("name") == FOUNDATION_LINT_STEP)
    if mutation == "missing_script":
        scripts.pop("lint:foundation")
    elif mutation in {
        "optional_script",
        "masked_script",
        "implicit_config",
        "empty_selector",
        "missing_premium",
        "missing_analytics",
        "warnings_allowed",
    }:
        replacements = {
            "optional_script": FOUNDATION_LINT_COMMAND + " --if-present",
            "masked_script": FOUNDATION_LINT_COMMAND + " || true",
            "implicit_config": FOUNDATION_LINT_COMMAND.replace("--config eslint.config.js ", ""),
            "empty_selector": FOUNDATION_LINT_COMMAND.replace('"src/api/*.ts"', '"absent/*.ts"'),
            "missing_premium": FOUNDATION_LINT_COMMAND.replace(' "src/api/premium/*.ts"', ""),
            "missing_analytics": FOUNDATION_LINT_COMMAND.replace(" src/lib/analytics.ts", ""),
            "warnings_allowed": FOUNDATION_LINT_COMMAND.replace(
                "--max-warnings=0", "--max-warnings=1"
            ),
        }
        scripts["lint:foundation"] = replacements[mutation]
    elif mutation == "missing_dependency":
        package["devDependencies"].pop("typescript-eslint")
    elif mutation == "global_module_mode":
        package["type"] = "module"
    elif mutation == "broad_ignore":
        config_source = config_source.replace("'src/api/schema.ts'", "'src/api/**'")
    elif mutation == "weakened_rule":
        config_source = config_source.replace(
            "'no-duplicate-imports': 'error'", "'no-duplicate-imports': 'off'"
        )
    elif mutation in {"missing_native", "missing_lint"}:
        steps.remove(native if mutation == "missing_native" else lint)
    elif mutation in {
        "duplicate_native",
        "renamed_duplicate_native",
        "duplicate_lint",
        "renamed_duplicate_lint",
    }:
        duplicate = dict(native if "native" in mutation else lint)
        if mutation.startswith("renamed_"):
            duplicate["name"] = "Duplicate renamed control"
        steps.append(duplicate)
    elif mutation in {"install_if", "native_if", "lint_if"}:
        {"install_if": install, "native_if": native, "lint_if": lint}[mutation][
            "if"
        ] = "${{ false }}"
    elif mutation in {"install_optional", "native_optional", "lint_optional"}:
        {"install_optional": install, "native_optional": native, "lint_optional": lint}[mutation][
            "continue-on-error"
        ] = True
    elif mutation in {"native_shell", "lint_shell"}:
        (native if mutation == "native_shell" else lint)["shell"] = "bash -c '{0} || true'"
    elif mutation in {"native_cwd", "lint_cwd"}:
        (native if mutation == "native_cwd" else lint)["working-directory"] = "."
    elif mutation == "native_env":
        native["env"] = {"NODE_OPTIONS": "--require untrusted.cjs"}
    elif mutation == "lint_optional_command":
        lint["run"] = "npm run lint:foundation --if-present"
    elif mutation == "lint_masked_command":
        lint["run"] = "npm run lint:foundation || true"
    elif mutation == "controls_before_install":
        steps.remove(native)
        steps.insert(steps.index(install), native)
    elif mutation == "lint_before_controls":
        steps.remove(lint)
        steps.insert(steps.index(native), lint)
    elif mutation == "job_if":
        job["if"] = "${{ false }}"
    elif mutation == "job_optional":
        job["continue-on-error"] = True
    elif mutation == "job_cwd":
        job["defaults"] = {"run": {"working-directory": "."}}
    elif mutation == "job_shell":
        job["defaults"] = {
            "run": {"working-directory": "frontend", "shell": "bash -c '{0} || true'"}
        }
    elif mutation == "workflow_shell":
        workflow["defaults"] = {"run": {"shell": "bash -c '{0} || true'"}}
    elif mutation == "job_startup_env":
        cast(dict[str, object], job["env"])["NODE_PATH"] = "untrusted"
    elif mutation == "workflow_startup_env":
        cast(dict[str, object], workflow["env"])["NODE_OPTIONS"] = "--require untrusted.cjs"
    else:
        changes = {
            "missing_clean_control": ("['clean',", "['disabled-clean',"),
            "missing_error_control": ("'no-duplicate-imports', 2, 1", "null, 0, 0"),
            "missing_warning_control": ("'@typescript-eslint/no-explicit-any', 1, 1", "null, 0, 0"),
            "missing_script_control": ("['run', 'lint:foundation']", "['--version']"),
            "missing_config_control": ("missing-eslint.config.cjs", "eslint.config.js"),
            "missing_empty_control": ("absent/*.ts", "clean.ts"),
            "missing_ignored_control": ("ignores: ['src/api/*.ts']", "ignores: []"),
            "ambient_child_env": ("const env = {", "const env = { ...process.env,"),
        }
        old, new = changes[mutation]
        source = cast(str, native["run"])
        assert old in source
        native["run"] = source.replace(old, new)
    with pytest.raises((AssertionError, KeyError)):
        _assert_frontend_node24_foundation_contract(package, workflow, config_source)


@pytest.mark.parametrize("omitted_index", [None, 0, 1, 2, 3])
@pytest.mark.parametrize("omit_source", [False, True])
def test_ops_context_producer_executes_four_real_test_targets(
    tmp_path: Path, omitted_index: int | None, omit_source: bool
) -> None:
    """Run the actual finite producer shell; comments cannot substitute for pytest argv."""
    import sys

    step = _job_step_by_name(
        _load_ci_workflow(), job_id="test-pr", step_name="Measure OPS CLI coverage"
    )
    run = str(step["run"])
    if omitted_index is not None:
        suffix = (
            "ops_context_report",
            "staging_runtime_diagnostics",
            "resource_cost_report",
            "resource_evidence_report",
        )[omitted_index]
        token = "scripts/ops/" + suffix + ".py" if omit_source else "tests/test_" + suffix + ".py"
        run = (
            run.replace(token + ",", "", 1)
            if omit_source and omitted_index < 3
            else run.replace("," + token, "", 1) if omit_source else run.replace(token, "", 1)
        )
        run += "\n# " + token + "\n"
    observer = tmp_path / "python"
    observer.write_text(
        "#!" + sys.executable + "\n" + """
import json
import os
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree

args = sys.argv[1:]
sources = ["scripts/ops/ops_context_report.py", "scripts/ops/staging_runtime_diagnostics.py", "scripts/ops/resource_cost_report.py", "scripts/ops/resource_evidence_report.py"]
tests = ["tests/test_ops_context_report.py", "tests/test_staging_runtime_diagnostics.py", "tests/test_resource_cost_report.py", "tests/test_resource_evidence_report.py"]
if args == ["-"]:
    result = subprocess.run([os.environ["OPS_TEST_PYTHON"], "-"], input=sys.stdin.buffer.read(), check=False)
    raise SystemExit(result.returncode)
if args[:3] == ["-m", "coverage", "run"]:
    if [arg for arg in args if arg.startswith("--include=")] != ["--include=" + ",".join(sources)]:
        raise SystemExit(41)
    if args[args.index("pytest") + 1:] != ["-q", "-p", "no:xdist", *tests]:
        raise SystemExit(42)
    Path("observed-targets.json").write_text(json.dumps(tests))
elif args[:3] == ["-m", "coverage", "xml"]:
    root = ElementTree.Element("coverage")
    classes = ElementTree.SubElement(root, "classes")
    for source in sources:
        cls = ElementTree.SubElement(classes, "class", filename=source)
        lines = ElementTree.SubElement(cls, "lines")
        ElementTree.SubElement(lines, "line", number="1", hits="1")
    ElementTree.ElementTree(root).write("coverage-ops-context.xml")
else:
    raise SystemExit(43)
""",
        encoding="utf-8",
    )
    observer.chmod(0o755)
    bash = shutil.which("bash", path=os.defpath)
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", run],
        cwd=tmp_path,
        env={"PATH": str(tmp_path) + os.pathsep + os.defpath, "OPS_TEST_PYTHON": sys.executable},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (
        result.returncode == (41 if omit_source else 42)
        if omitted_index is not None
        else result.returncode == 0
    ), result.stderr
    if omitted_index is None:
        assert json.loads((tmp_path / "observed-targets.json").read_text()) == [
            "tests/test_ops_context_report.py",
            "tests/test_staging_runtime_diagnostics.py",
            "tests/test_resource_cost_report.py",
            "tests/test_resource_evidence_report.py",
        ]


def test_frontend_node24_ui_command_and_native_controls_are_blocking() -> None:
    """UI and foundation share the reviewed carrier; native execution is separate evidence."""
    package = json.loads(FRONTEND_PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    config_source = (REPO_ROOT / "frontend/eslint.config.js").read_text(encoding="utf-8")
    _assert_frontend_node24_foundation_contract(package, workflow, config_source)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_ui_script",
        "optional_ui_script",
        "masked_ui_script",
        "implicit_ui_config",
        "shallow_ui_selector",
        "empty_ui_selector",
        "wrong_ui_selector",
        "ui_warnings_allowed",
        "missing_ui_step",
        "duplicate_ui_step",
        "renamed_duplicate_ui_step",
        "ui_if",
        "ui_optional",
        "ui_shell",
        "ui_cwd",
        "ui_env",
        "ui_optional_command",
        "ui_masked_command",
        "ui_before_install",
        "ui_before_native",
        "ui_after_vitest",
        "ui_after_build",
        "renamed_duplicate_install",
        "missing_install",
        "missing_vitest",
        "missing_build",
        "outer_relative_node",
        "missing_recursion",
        "missing_nonempty",
        "missing_nonignore",
        "collapsed_results",
        "missing_equality",
        "missing_nested",
        "missing_omitted",
        "missing_single_ignore",
        "missing_all_ignore",
        "missing_empty_directory",
        "missing_declaration_directory",
        "missing_clean_tsx",
        "missing_error_tsx",
        "missing_warning_tsx",
        "missing_ui_script_control",
        "missing_ui_unmatched",
        "missing_fatal_check",
        "missing_clean_error_count",
        "missing_clean_warning_count",
        "missing_message_fatal_check",
        "missing_cleanup",
        "missing_restored_inventory",
        "ambient_ui_child_env",
        "unbounded_ui_child",
        "vitest_if",
        "vitest_optional",
        "vitest_shell",
        "vitest_cwd",
        "vitest_startup_env",
        "renamed_duplicate_vitest",
        "build_if",
        "build_optional",
        "build_shell",
        "build_cwd",
        "build_startup_env",
        "renamed_duplicate_build",
    ),
)
def test_frontend_node24_ui_guard_rejects_weakened_wiring(mutation: str) -> None:
    """Finite carrier mutations run without Node and cannot claim ESLint execution."""
    package = json.loads(FRONTEND_PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
    workflow = _load_workflow(FRONTEND_CI_WORKFLOW_PATH)
    config_source = (REPO_ROOT / "frontend/eslint.config.js").read_text(encoding="utf-8")
    scripts = package["scripts"]
    job = cast(dict[str, object], cast(dict[str, object], workflow["jobs"])["build-and-test"])
    steps = cast(list[dict[str, object]], job["steps"])
    install = next(step for step in steps if step.get("name") == "Install dependencies")
    native = next(step for step in steps if step.get("name") == FOUNDATION_NATIVE_STEP)
    ui = next(step for step in steps if step.get("name") == UI_LINT_STEP)
    vitest = next(step for step in steps if step.get("name") == "Run vitest suite")
    build = next(step for step in steps if step.get("name") == "Build frontend")
    script_replacements = {
        "optional_ui_script": ("--max-warnings=0", "--max-warnings=0 --if-present"),
        "masked_ui_script": ("--max-warnings=0", "--max-warnings=0 || true"),
        "implicit_ui_config": ("--config eslint.config.js ", ""),
        "shallow_ui_selector": ("ui/**/*.{ts,tsx}", "ui/*.{ts,tsx}"),
        "empty_ui_selector": ("src/components/ui/**/*.{ts,tsx}", "absent/**/*.{ts,tsx}"),
        "wrong_ui_selector": ("src/components/ui/**/*.{ts,tsx}", "src/api/*.ts"),
        "ui_warnings_allowed": ("--max-warnings=0", "--max-warnings=1"),
    }
    if mutation == "missing_ui_script":
        scripts.pop("lint:ui")
    elif mutation in script_replacements:
        old, new = script_replacements[mutation]
        assert old in scripts["lint:ui"]
        scripts["lint:ui"] = scripts["lint:ui"].replace(old, new)
    elif mutation in {"missing_ui_step", "missing_install", "missing_vitest", "missing_build"}:
        steps.remove(
            {
                "missing_ui_step": ui,
                "missing_install": install,
                "missing_vitest": vitest,
                "missing_build": build,
            }[mutation]
        )
    elif mutation in {
        "duplicate_ui_step",
        "renamed_duplicate_ui_step",
        "renamed_duplicate_install",
    }:
        duplicate = dict(install if mutation == "renamed_duplicate_install" else ui)
        if mutation.startswith("renamed_"):
            duplicate["name"] = "Renamed duplicate UI carrier"
        steps.append(duplicate)
    elif mutation in {"ui_if", "ui_optional", "ui_shell", "ui_cwd", "ui_env"}:
        settings: dict[str, tuple[str, object]] = {
            "ui_if": ("if", "${{ false }}"),
            "ui_optional": ("continue-on-error", True),
            "ui_shell": ("shell", "bash -c '{0} || true'"),
            "ui_cwd": ("working-directory", "."),
            "ui_env": ("env", {"NODE_OPTIONS": "--require untrusted.cjs"}),
        }
        key, value = settings[mutation]
        ui[key] = value
    elif mutation in {"ui_optional_command", "ui_masked_command"}:
        ui["run"] = "npm run lint:ui" + (
            " --if-present" if mutation == "ui_optional_command" else " || true"
        )
    elif mutation in {"ui_before_install", "ui_before_native", "ui_after_vitest", "ui_after_build"}:
        target = {
            "ui_before_install": install,
            "ui_before_native": native,
            "ui_after_vitest": vitest,
            "ui_after_build": build,
        }[mutation]
        steps.remove(ui)
        steps.insert(steps.index(target) + (1 if mutation.startswith("ui_after_") else 0), ui)
    elif mutation in {
        "vitest_if",
        "vitest_optional",
        "vitest_shell",
        "vitest_cwd",
        "vitest_startup_env",
        "renamed_duplicate_vitest",
        "build_if",
        "build_optional",
        "build_shell",
        "build_cwd",
        "build_startup_env",
        "renamed_duplicate_build",
    }:
        consumer = vitest if "vitest" in mutation else build
        if mutation.startswith("renamed_duplicate_"):
            duplicate = dict(consumer)
            duplicate["name"] = "Renamed duplicate validation consumer"
            steps.append(duplicate)
        elif mutation.endswith("_startup_env"):
            env = dict(cast(dict[str, object], consumer.get("env", {})))
            env["NODE_OPTIONS"] = "--require untrusted.cjs"
            consumer["env"] = env
        else:
            consumer_settings: dict[str, tuple[str, object]] = {
                "if": ("if", "${{ false }}"),
                "optional": ("continue-on-error", True),
                "shell": ("shell", "bash -c '{0} || true'"),
                "cwd": ("working-directory", "."),
            }
            key, value = consumer_settings[mutation.split("_", 1)[1]]
            consumer[key] = value
    else:
        replacements = {
            "outer_relative_node": ('"$node_binary" -', "node -"),
            "missing_recursion": ("files.push(...enumerateUI(file))", "files.push(file)"),
            "missing_nonempty": ("assert.ok(files.length > 0,", "assert.ok(true,"),
            "missing_nonignore": (
                "assert.ok((await engine.isPathIgnored(file)) === false,",
                "assert.ok(true,",
            ),
            "collapsed_results": (
                "report.map(result => result.filePath).sort()",
                "[...new Set(report.map(result => result.filePath))].sort()",
            ),
            "missing_equality": (
                "actual.length === inventory.length && "
                "actual.every((file, index) => file === inventory[index])",
                "true",
            ),
            "missing_nested": (
                "await assertUIMembership(eslint, [uiPattern], nestedUI)",
                "await eslint.lintFiles(originalUI)",
            ),
            "missing_omitted": ("originalUI.slice(1), originalUI", "originalUI, originalUI"),
            "missing_single_ignore": ("ignores: [ignoredMember]", "ignores: []"),
            "missing_all_ignore": ("ignores: ['src/components/ui/**']", "ignores: []"),
            "missing_empty_directory": (
                "assert.throws(() => requireUISelection(directory)",
                "assert.throws(() => requireUISelection(uiRoot)",
            ),
            "missing_declaration_directory": ("name.endsWith('.d.ts')", "name.endsWith('.never')"),
            "missing_clean_tsx": ("['ui-clean',", "['disabled-ui-clean',"),
            "missing_error_tsx": ("['ui-error',", "['disabled-ui-error',"),
            "missing_warning_tsx": ("['ui-warning',", "['disabled-ui-warning',"),
            "missing_ui_script_control": ("['run', 'lint:ui']", "['--version']"),
            "missing_ui_unmatched": ("absent-ui/**/*.tsx", "ui-clean.tsx"),
            "missing_fatal_check": (
                "assert.equal(report[0].fatalErrorCount, 0)",
                "assert.ok(true)",
            ),
            "missing_clean_error_count": (
                "assert.equal(report[0].errorCount, severity === 2 ? 1 : 0)",
                "assert.ok(true)",
            ),
            "missing_clean_warning_count": (
                "assert.equal(report[0].warningCount, severity === 1 ? 1 : 0)",
                "assert.ok(true)",
            ),
            "missing_message_fatal_check": (
                "assert.notEqual(messages[0].fatal, true)",
                "assert.ok(true)",
            ),
            "missing_cleanup": (
                "if (uiFixtures) fs.rmSync(uiFixtures, { recursive: true, force: true })",
                "if (uiFixtures) console.log('left fixture')",
            ),
            "missing_restored_inventory": (
                "assert.deepEqual(restoredUI, originalUI)",
                "assert.ok(true)",
            ),
            "ambient_ui_child_env": ("const env = {", "const env = { ...process.env,"),
            "unbounded_ui_child": (
                "encoding: 'utf8', timeout, maxBuffer: 1024 * 1024",
                "encoding: 'utf8'",
            ),
        }
        old, new = replacements[mutation]
        source = cast(str, native["run"])
        assert old in source, mutation
        native["run"] = source.replace(old, new)
    with pytest.raises((AssertionError, KeyError)):
        _assert_frontend_node24_foundation_contract(package, workflow, config_source)


def test_fitchef_agent_coverage_is_separate_and_required_by_existing_diff_gate() -> None:
    """Bind the sole provider producer and mandatory artifact to the 97% gate."""
    import shlex

    workflow = _load_ci_workflow()
    measure = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Measure FitChef Agent provider coverage"
    )
    run = str(measure["run"])
    commands = run.split("python - <<'PY'\n", 1)[0].replace("\\\n", "").splitlines()
    assert [shlex.split(command) for command in commands] == [
        ["set", "-euo", "pipefail"],
        [
            "python",
            "-m",
            "coverage",
            "run",
            "--rcfile=/dev/null",
            "--branch",
            "--include=providers/perplexity_agent.py",
            "--data-file=.coverage.fitchef-agent",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:xdist",
            "tests/test_perplexity_agent_provider.py",
        ],
        [
            "python",
            "-m",
            "coverage",
            "xml",
            "--rcfile=/dev/null",
            "--data-file=.coverage.fitchef-agent",
            "-o",
            "coverage-fitchef-agent.xml",
        ],
    ]
    assert measure["env"] == {
        "PYTHONPATH": "${{ github.workspace }}:${{ github.workspace }}/tests",
        "BLOCK_TEST_NETWORK": "true",
    }
    assert "if" not in measure and "continue-on-error" not in measure
    upload = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Upload FitChef Agent coverage artifact"
    )
    assert upload["uses"] == f"actions/upload-artifact@{UPLOAD_ARTIFACT_NODE24_SHA}"
    assert upload["with"] == {
        "name": "coverage-fitchef-agent-${{ env.PYTHON_VERSION }}",
        "path": "coverage-fitchef-agent.xml",
        "if-no-files-found": "error",
        "retention-days": 7,
    }
    assert "if" not in upload and "continue-on-error" not in upload
    download = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Download FitChef Agent coverage artifact"
    )
    assert download["uses"] == f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA}"
    assert download["with"] == {
        "name": "coverage-fitchef-agent-${{ env.PYTHON_VERSION }}",
        "path": "./fitchef-agent-coverage",
    }
    assert "if" not in download and "continue-on-error" not in download
    gate = _job_step_by_name(
        workflow, job_id="diff-coverage", step_name="Enforce diff coverage >= 97%"
    )
    assert gate["env"] == {"COVERAGE_THRESHOLD": 97}
    assert "if" not in gate and "continue-on-error" not in gate
    assert "./coverage-artifacts/coverage.xml" in str(gate["run"])
    assert "./ops-context-coverage/coverage-ops-context.xml" in str(gate["run"])
    assert "./fitchef-agent-coverage/coverage-fitchef-agent.xml" in str(gate["run"])
    assert '--fail-under "${{ env.COVERAGE_THRESHOLD }}"' in str(gate["run"])


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "zero_hit",
        "missing",
        "malformed",
        "empty",
        "no_class",
        "wrong",
        "duplicate",
        "extra",
    ],
)
def test_fitchef_agent_workflow_executes_exact_singleton_inventory_check(
    tmp_path: Path,
    case: str,
) -> None:
    """Run the actual embedded checker, retaining zero hits as structural evidence."""
    import subprocess
    import sys

    measure = _job_step_by_name(
        _load_ci_workflow(), job_id="test-pr", step_name="Measure FitChef Agent provider coverage"
    )
    run = str(measure["run"])
    marker = "python - <<'PY'\n"
    assert run.count(marker) == 1
    check = run.split(marker, 1)[1].rsplit("\nPY", 1)[0]
    filename = "providers/other.py" if case == "wrong" else "providers/perplexity_agent.py"
    hits = "0" if case == "zero_hit" else "1"
    lines = "" if case == "empty" else f'<line number="1" hits="{hits}"/>'
    cls = f'<class filename="{filename}"><lines>{lines}</lines></class>'
    raw = "<coverage><packages><package><classes>" + ("" if case == "no_class" else cls)
    if case == "duplicate":
        raw += cls
    if case == "extra":
        raw += '<class filename="providers/other.py"><lines><line number="1" hits="1"/></lines></class>'
    raw += "</classes></package></packages></coverage>"
    if case == "malformed":
        raw = "<coverage"
    if case != "missing":
        (tmp_path / "coverage-fitchef-agent.xml").write_text(raw, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", check],
        cwd=tmp_path,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is (case in {"valid", "zero_hit"})


@pytest.mark.parametrize("hits", [0, 1])
def test_fitchef_agent_structural_acceptance_still_requires_numeric_diff_coverage(
    tmp_path: Path,
    hits: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Feed retained zero/positive hits through the actual canonical diff command."""
    import shutil
    import subprocess
    import sys

    from scripts.orchestration.creative_code_patch_workspace import (
        git_env_without_parent_state,
        safe_git_config_args,
    )

    git = shutil.which("git")
    diff_cover = shutil.which("diff-cover", path=str(Path(sys.executable).parent))
    assert git is not None and diff_cover is not None
    parent_repo = tmp_path / "protected-parent"
    parent_repo.mkdir()
    parent_env = git_env_without_parent_state()
    for args in (
        ["init", "--initial-branch=protected"],
        ["config", "user.name", "Protected Parent Fixture"],
        ["config", "user.email", "protected-parent@example.invalid"],
    ):
        subprocess.run(
            [git, *safe_git_config_args(), *args],
            cwd=parent_repo,
            env=parent_env,
            capture_output=True,
            timeout=10,
            check=True,
        )
    (parent_repo / "protected.txt").write_text("protected fixture content\n", encoding="utf-8")
    subprocess.run(
        [git, *safe_git_config_args(), "add", "protected.txt"],
        cwd=parent_repo,
        env=parent_env,
        capture_output=True,
        timeout=10,
        check=True,
    )
    parent_git = parent_repo / ".git"
    protected_paths = (parent_git / "config", parent_git / "HEAD", parent_git / "index")
    parent_before = {path: path.read_bytes() for path in protected_paths}
    for name, value in {
        "GIT_DIR": str(parent_git),
        "GIT_COMMON_DIR": str(parent_git),
        "GIT_WORK_TREE": str(parent_repo),
        "GIT_INDEX_FILE": str(parent_git / "index"),
        "GIT_PREFIX": "protected-parent/",
    }.items():
        monkeypatch.setenv(name, value)
    fixture_env = git_env_without_parent_state()
    source = tmp_path / "providers" / "perplexity_agent.py"
    source.parent.mkdir()
    source.write_text("baseline = 0\n", encoding="utf-8")
    for args in (
        ["init", "--initial-branch=base"],
        ["config", "user.name", "Coverage Fixture"],
        ["config", "user.email", "coverage-fixture@example.invalid"],
        ["add", "providers/perplexity_agent.py"],
        ["commit", "-m", "fixture base"],
    ):
        subprocess.run(
            [git, *safe_git_config_args(), *args],
            cwd=tmp_path,
            env=fixture_env,
            capture_output=True,
            timeout=10,
            check=True,
        )
    source.write_text("baseline = 0\nfirst_changed = 1\nsecond_changed = 2\n", encoding="utf-8")
    lines = "".join(f'<line number="{number}" hits="{hits}"/>' for number in (1, 2, 3))
    raw = (
        "<coverage><sources><source>.</source></sources><packages><package><classes>"
        '<class filename="providers/perplexity_agent.py"><lines>'
        + lines
        + "</lines></class></classes></package></packages></coverage>"
    )
    workflow = _load_ci_workflow()
    measure = _job_step_by_name(
        workflow, job_id="test-pr", step_name="Measure FitChef Agent provider coverage"
    )
    check = str(measure["run"]).split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    (tmp_path / "coverage-fitchef-agent.xml").write_text(raw, encoding="utf-8")
    subprocess.run(
        [sys.executable, "-c", check], cwd=tmp_path, capture_output=True, timeout=5, check=True
    )
    for report in (
        "coverage-artifacts/coverage.xml",
        "ops-context-coverage/coverage-ops-context.xml",
        "fitchef-eval-coverage/coverage-fitchef-eval.xml",
        "orchestration-coverage/coverage-orchestration.xml",
        "fitchef-agent-coverage/coverage-fitchef-agent.xml",
    ):
        path = tmp_path / report
        path.parent.mkdir()
        path.write_text(
            (
                raw
                if report.startswith("fitchef-agent-")
                else "<coverage><sources><source>.</source></sources><packages/></coverage>"
            ),
            encoding="utf-8",
        )
    argv = _native_ci_diff_coverage_args(tmp_path)
    result = subprocess.run(
        [diff_cover, *argv],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=fixture_env,
    )
    assert result.returncode == (1 if hits == 0 else 0), result.stdout + result.stderr
    assert "providers/perplexity_agent.py" in result.stdout
    assert "No lines with coverage information" not in result.stdout
    assert f"Coverage: {0 if hits == 0 else 100}%" in result.stdout
    assert {path: path.read_bytes() for path in protected_paths} == parent_before

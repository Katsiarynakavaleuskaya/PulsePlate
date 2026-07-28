"""Deterministic tests for Tier 1 PR risk-profile routing."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import scripts.ci.ci_risk_profile as risk_profile
from scripts.orchestration.pr_review_evidence import (
    _DEPENDENCY_MANIFEST_BASENAMES as TRUST_BOUNDARY_DEPENDENCY_MANIFEST_BASENAMES,
    _ROOT_REQUIREMENTS_MANIFEST_RE as TRUST_BOUNDARY_REQUIREMENTS_MANIFEST_RE,
    OPERATOR_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS,
    OPERATOR_OUTAGE_TRUST_BOUNDARY_PREFIXES,
    protected_trust_boundary_paths,
)


def test_empty_changed_files_uses_default_risk_profile() -> None:
    profile = risk_profile.build_risk_profile([])

    assert profile.changed_files == ()
    assert profile.docs_only is False
    assert profile.frontend_only is False
    assert profile.ios_only is False
    assert profile.workflow_privileged is False
    assert profile.backend_shared is False
    assert profile.run_backend_blocking is False
    assert profile.run_main_ci_diagnostic is False
    assert profile.run_security is False
    assert profile.run_openapi_sync is False
    assert profile.billing_entitlement is False
    assert profile.insight_ai is False
    assert profile.openapi_contract is False
    assert profile.food_catalog is False
    assert profile.route_contract_safety is False
    assert profile.operator_plane_slack is False
    assert profile.merge_governance is False
    assert profile.contract_risk_groups == ()


def test_docs_only_changes_skip_backend_blocking() -> None:
    profile = risk_profile.build_risk_profile(
        ["docs/release/notes.md", "README.md"],
    )

    assert profile.docs_only is True
    assert profile.run_backend_blocking is False
    assert profile.contract_risk_groups == ()


def test_frontend_only_changes_skip_backend_blocking() -> None:
    profile = risk_profile.build_risk_profile(
        ["frontend/src/components/Card.tsx"],
    )

    assert profile.frontend_only is True
    assert profile.run_backend_blocking is False
    assert profile.run_openapi_sync is False


def test_workflow_privileged_docs_force_full_contract_suites() -> None:
    profile = risk_profile.build_risk_profile(
        ["docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md"],
    )

    assert profile.workflow_privileged is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


def test_hidden_workflow_path_preserves_leading_dot_for_routing() -> None:
    profile = risk_profile.build_risk_profile(
        ["./.github/workflows/ci.yml"],
    )

    assert profile.workflow_privileged is True
    assert profile.merge_governance is True
    assert profile.run_backend_blocking is True
    assert profile.run_main_ci_diagnostic is True
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


@pytest.mark.parametrize(
    "changed_file",
    (
        "scripts/orchestration/experiment_slack_socket_bridge.py",
        "scripts/orchestration/experiment_slack_bridge_config.py",
        "scripts/orchestration/experiment_operator_ledger.py",
        "tests/test_experiment_slack_socket_bridge.py",
        "tests/test_experiment_operator_ledger.py",
        "tests/test_experiment_slack_kpp_renderer.py",
        "tests/test_runtime_toolchain_alignment.py",
    ),
)
def test_operator_plane_slack_surfaces_hit_operator_group(changed_file: str) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.backend_shared is True
    assert profile.operator_plane_slack is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.contract_risk_groups == ("operator_plane_slack",)


def test_operator_plane_slack_backlog_surface_runs_operator_group() -> None:
    profile = risk_profile.build_risk_profile(["docs/roadmap/BACKLOG_LEDGER.md"])

    assert profile.docs_only is True
    assert profile.operator_plane_slack is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.contract_risk_groups == ("operator_plane_slack",)


@pytest.mark.parametrize(
    "changed_file",
    (
        ".github/workflows/experiment-runner-dispatch.yml",
        ".github/workflows/experiment-runner-slack-socket-smoke.yml",
        "docs/orchestration/EXPERIMENT_RUNNER_SLACK_SOCKET_OPERATOR_RUNBOOK.md",
    ),
)
def test_operator_plane_slack_privileged_surfaces_keep_full_contract_groups(
    changed_file: str,
) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.workflow_privileged is True
    assert profile.operator_plane_slack is True
    assert profile.run_backend_blocking is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


def test_main_ci_diagnostic_is_scoped_to_main_ci_surfaces() -> None:
    positive_profile = risk_profile.build_risk_profile(
        [
            "scripts/ci/run_main_test_shards.py",
            "scripts/ci/run_py312_main_shards.py",
            "tests/test_main_test_shards.py",
        ],
    )
    negative_profile = risk_profile.build_risk_profile(
        ["scripts/ci/check_docs_phase1_gates.py"],
    )

    assert positive_profile.workflow_privileged is True
    assert positive_profile.run_main_ci_diagnostic is True
    assert negative_profile.workflow_privileged is True
    assert negative_profile.run_main_ci_diagnostic is False


def test_security_audit_helper_path_is_workflow_privileged() -> None:
    profile = risk_profile.build_risk_profile(
        ["scripts/ci_pip_audit.sh"],
    )

    assert profile.workflow_privileged is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS
    assert profile.backend_shared is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.to_outputs()["workflow_privileged"] == "true"
    assert profile.to_outputs()["backend_shared"] == "true"
    assert profile.to_outputs()["run_security"] == "true"


@pytest.mark.parametrize(
    "changed_file",
    tuple(sorted(OPERATOR_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS)),
)
def test_every_protected_exact_path_routes_security(changed_file: str) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.run_security is True


@pytest.mark.parametrize(
    "changed_file",
    tuple(prefix + "authority-probe" for prefix in OPERATOR_OUTAGE_TRUST_BOUNDARY_PREFIXES),
)
def test_every_protected_prefix_routes_security(changed_file: str) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.run_security is True


@pytest.mark.parametrize(
    "changed_file",
    (
        "requirements-dev.in",
        "requirements-dev.txt",
        "requirements.in",
        "requirements-lock.txt",
        "requirements-test.in",
        "requirements-test.txt",
        "REQUIREMENTS.md",
        "docs/DEPENDENCY_MANAGEMENT.md",
        "docs/contracts/PYTHON_DEPENDENCY_SURFACES.md",
    ),
)
def test_python_dependency_surfaces_route_backend_blocking(changed_file: str) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.backend_shared is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True


@pytest.mark.parametrize(
    "changed_file",
    (".github/dependabot.yml", ".github/dependabot.yaml"),
)
def test_dependabot_config_routes_bounded_backend_and_governance(
    changed_file: str,
) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.workflow_privileged is False
    assert profile.backend_shared is True
    assert profile.merge_governance is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.contract_risk_groups == ("merge_governance",)


@pytest.mark.parametrize(
    "changed_file",
    (
        "requirements.in",
        "requirements.txt",
        "requirements-dev.in",
        "requirements-rag-vector-cpu.txt",
    ),
)
def test_every_sampled_protected_python_manifest_routes_security(
    changed_file: str,
) -> None:
    assert protected_trust_boundary_paths((changed_file,)) == (changed_file,)
    assert risk_profile.build_risk_profile([changed_file]).run_security is True


def test_dependency_manifest_basename_rules_match_trust_boundary_policy() -> None:
    assert (
        risk_profile._DEPENDENCY_MANIFEST_BASENAMES == TRUST_BOUNDARY_DEPENDENCY_MANIFEST_BASENAMES
    )
    assert (
        risk_profile._REQUIREMENTS_MANIFEST_RE.pattern
        == TRUST_BOUNDARY_REQUIREMENTS_MANIFEST_RE.pattern
    )


@pytest.mark.parametrize(
    "basename",
    (
        *sorted(TRUST_BOUNDARY_DEPENDENCY_MANIFEST_BASENAMES),
        "requirements-dev.in",
        "requirements.in",
        "requirements-rag-vector-cpu.txt",
    ),
)
def test_nested_protected_dependency_manifests_route_backend_and_security(
    basename: str,
) -> None:
    changed_file = f"nested/dependencies/{basename}"

    assert protected_trust_boundary_paths((changed_file,)) == (changed_file,)
    profile = risk_profile.build_risk_profile([changed_file])
    assert profile.backend_shared is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True


@pytest.mark.parametrize(
    "changed_file",
    (
        "nested/Dockerfile",
        "nested/REQUIREMENTS.md",
        "nested/package.json.bak",
        "nested/pyproject.toml.bak",
        "nested/requirements--dev.in",
        "nested/requirements-dev.in.bak",
        "nested/requirements.md",
    ),
)
def test_nested_dependency_manifest_lookalikes_remain_unrouted(changed_file: str) -> None:
    assert protected_trust_boundary_paths((changed_file,)) == ()
    profile = risk_profile.build_risk_profile([changed_file])
    assert profile.backend_shared is False
    assert profile.run_backend_blocking is False
    assert profile.run_security is False


def test_pull_request_template_is_workflow_privileged() -> None:
    profile = risk_profile.build_risk_profile(
        [".github/pull_request_template.md"],
    )

    assert profile.workflow_privileged is True
    assert profile.docs_only is False
    assert profile.merge_governance is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


def test_governance_tests_hit_merge_governance_group() -> None:
    profile = risk_profile.build_risk_profile(
        ["tests/test_ci_risk_profile.py"],
    )

    assert profile.backend_shared is True
    assert profile.merge_governance is True
    assert profile.contract_risk_groups == ("merge_governance",)


def test_billing_router_change_hits_billing_and_openapi_groups() -> None:
    profile = risk_profile.build_risk_profile(
        ["app/routers/billing.py"],
    )

    assert profile.backend_shared is True
    assert profile.billing_entitlement is True
    assert profile.openapi_contract is True
    assert profile.food_catalog is False
    assert profile.route_contract_safety is True
    assert profile.contract_risk_groups == (
        "billing_entitlement",
        "openapi_contract",
        "route_contract_safety",
    )


def test_payment_reconciliation_contract_test_hits_billing_group() -> None:
    profile = risk_profile.build_risk_profile(
        ["tests/test_payment_reconciliation_api.py"],
    )

    assert profile.billing_entitlement is True
    assert profile.backend_shared is True
    assert profile.route_contract_safety is False
    assert profile.contract_risk_groups == ("billing_entitlement",)


def test_openapi_only_change_still_runs_blocking_and_sync() -> None:
    profile = risk_profile.build_risk_profile(
        ["scripts/generate_openapi.py"],
    )

    assert profile.backend_shared is False
    assert profile.openapi_contract is True
    assert profile.run_backend_blocking is True
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == ("openapi_contract",)


@pytest.mark.parametrize(
    "changed_file",
    ["app/application_metadata.py", "app/bootstrap/openapi.py"],
)
def test_canonical_openapi_owner_change_selects_openapi_contract(
    changed_file: str,
) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.backend_shared is True
    assert profile.openapi_contract is True
    assert profile.route_contract_safety is True
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == (
        "openapi_contract",
        "route_contract_safety",
    )


def test_insight_runtime_change_hits_insight_group_only() -> None:
    profile = risk_profile.build_risk_profile(
        ["core/insight/fitchef_companion.py"],
    )

    assert profile.backend_shared is True
    assert profile.insight_ai is True
    assert profile.route_contract_safety is True
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == (
        "insight_ai",
        "route_contract_safety",
    )


def test_fitchef_structured_source_change_hits_insight_openapi_and_route_groups() -> None:
    profile = risk_profile.build_risk_profile(
        [
            "app/routers/fitchef_structured.py",
            "app/services/fitchef_runtime.py",
            "app/schemas/fitchef_coaching.py",
        ],
    )

    assert profile.backend_shared is True
    assert profile.insight_ai is True
    assert profile.openapi_contract is True
    assert profile.route_contract_safety is True
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == (
        "insight_ai",
        "openapi_contract",
        "route_contract_safety",
    )


def test_rag_runtime_change_hits_insight_and_route_groups() -> None:
    profile = risk_profile.build_risk_profile(
        ["core/rag/orchestration.py", "tests/test_rag_orchestration.py"],
    )

    assert profile.backend_shared is True
    assert profile.insight_ai is True
    assert profile.route_contract_safety is True
    assert profile.run_backend_blocking is True
    assert profile.contract_risk_groups == (
        "insight_ai",
        "route_contract_safety",
    )


def test_generic_backend_change_hits_route_contract_safety_group() -> None:
    profile = risk_profile.build_risk_profile(
        ["app/dependencies.py"],
    )

    assert profile.backend_shared is True
    assert profile.food_catalog is False
    assert profile.route_contract_safety is True
    assert profile.run_backend_blocking is True
    assert profile.contract_risk_groups == ("route_contract_safety",)


@pytest.mark.parametrize(
    "changed_file",
    (
        "requirements-rag-vector-cpu.in",
        "requirements-rag-vector-cpu.txt",
    ),
)
def test_cpu_rag_manifest_change_routes_backend_and_security(changed_file: str) -> None:
    profile = risk_profile.build_risk_profile(
        [changed_file],
    )

    assert profile.backend_shared is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.to_outputs()["backend_shared"] == "true"
    assert profile.to_outputs()["run_backend_blocking"] == "true"
    assert profile.to_outputs()["run_security"] == "true"


def test_security_audit_helper_change_routes_backend_and_security() -> None:
    profile = risk_profile.build_risk_profile(["scripts/ci_pip_audit.sh"])

    assert profile.workflow_privileged is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS
    assert profile.backend_shared is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.to_outputs()["workflow_privileged"] == "true"
    assert profile.to_outputs()["backend_shared"] == "true"
    assert profile.to_outputs()["run_backend_blocking"] == "true"
    assert profile.to_outputs()["run_security"] == "true"


EXPECTED_ROOT_BACKEND_SHARED_MODULES = (
    "bmi_visualization.py",
    "llm.py",
    "main.py",
    "secure_config.py",
    "settings.py",
    "signed_links.py",
)


def test_root_backend_shared_module_contract_matches_classifier_constant() -> None:
    # Keep an explicit oracle here so membership regressions fail
    # even if the production constant changes.
    assert risk_profile.ROOT_BACKEND_SHARED_MODULES == EXPECTED_ROOT_BACKEND_SHARED_MODULES


@pytest.mark.parametrize(
    "changed_file",
    [*EXPECTED_ROOT_BACKEND_SHARED_MODULES, "providers/ollama.py"],
)
def test_root_and_provider_backend_surfaces_are_backend_shared(
    changed_file: str,
) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.backend_shared is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.route_contract_safety is True
    assert profile.contract_risk_groups == ("route_contract_safety",)


def test_food_schema_change_hits_food_catalog_openapi_and_route_groups() -> None:
    profile = risk_profile.build_risk_profile(
        ["app/schemas/food.py"],
    )

    assert profile.backend_shared is True
    assert profile.openapi_contract is True
    assert profile.food_catalog is True
    assert profile.route_contract_safety is True
    assert profile.contract_risk_groups == (
        "openapi_contract",
        "food_catalog",
        "route_contract_safety",
    )


def test_off_nutrition_core_change_hits_food_catalog_and_route_groups() -> None:
    profile = risk_profile.build_risk_profile(
        ["core/off_nutrition/resolver.py"],
    )

    assert profile.backend_shared is True
    assert profile.openapi_contract is False
    assert profile.food_catalog is True
    assert profile.route_contract_safety is True
    assert profile.contract_risk_groups == (
        "food_catalog",
        "route_contract_safety",
    )


def test_food_provenance_core_change_hits_food_catalog_and_route_groups() -> None:
    profile = risk_profile.build_risk_profile(
        ["core/food_provenance_verification.py"],
    )

    assert profile.backend_shared is True
    assert profile.openapi_contract is False
    assert profile.food_catalog is True
    assert profile.route_contract_safety is True
    assert profile.contract_risk_groups == (
        "food_catalog",
        "route_contract_safety",
    )


def test_build_food_db_script_only_still_runs_backend_blocking_for_food_catalog() -> None:
    """scripts/build_food_db.py is not under BACKEND_SHARED_PREFIXES; food_catalog must gate CI."""
    profile = risk_profile.build_risk_profile(
        ["scripts/build_food_db.py"],
    )

    assert profile.backend_shared is False
    assert profile.food_catalog is True
    assert profile.run_backend_blocking is True
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == ("food_catalog",)


def test_mixed_backend_surface_keeps_openapi_and_route_contract_groups() -> None:
    profile = risk_profile.build_risk_profile(
        ["app/main.py", "app/dependencies.py"],
    )

    assert profile.openapi_contract is True
    assert profile.route_contract_safety is True
    assert profile.contract_risk_groups == (
        "openapi_contract",
        "route_contract_safety",
    )


def test_cli_writes_github_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    github_output = tmp_path / "github_output.txt"

    result = risk_profile.main(
        [
            "--file",
            "app/middleware/api_tiers.py",
            "--github-output",
            str(github_output),
            "--as-json",
        ],
    )

    assert result == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["billing_entitlement"] is True
    written = github_output.read_text(encoding="utf-8")
    assert "run_backend_blocking=true" in written
    assert "run_main_ci_diagnostic=false" in written
    assert "billing_entitlement=true" in written
    assert "operator_plane_slack=false" in written


def test_collect_changed_files_fails_fast_on_git_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["git", "diff"], timeout=60)

    monkeypatch.setattr(risk_profile, "GIT_BINARY", "/usr/bin/git")
    monkeypatch.setattr(risk_profile.subprocess, "run", _raise_timeout)

    with pytest.raises(
        RuntimeError,
        match="git diff --no-renames --name-only -z timed out after 60 seconds",
    ):
        risk_profile.collect_changed_files(base_sha="base", head_sha="head")


def test_collect_changed_files_disables_rename_collapse_and_parses_nul_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def _run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout="docs/old.md\0app/main.py\0docs/élan.md\0".encode(),
            stderr=b"",
        )

    monkeypatch.setattr(risk_profile, "GIT_BINARY", "/usr/bin/git")
    monkeypatch.setattr(risk_profile.subprocess, "run", _run)

    changed = risk_profile.collect_changed_files(base_sha="base", head_sha="head")

    assert changed == ("docs/old.md", "app/main.py", "docs/élan.md")
    assert observed["argv"] == [
        "/usr/bin/git",
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        "base...head",
    ]
    assert observed["kwargs"] == {
        "cwd": risk_profile.REPO_ROOT,
        "check": True,
        "capture_output": True,
        "text": False,
        "timeout": risk_profile.GIT_DIFF_TIMEOUT_SECONDS,
    }


@pytest.mark.parametrize(
    "changed_file",
    ("conftest.py", "pytest_sharding.py", "tests/conftest.py"),
)
def test_pytest_control_paths_route_privileged_security(changed_file: str) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.workflow_privileged is True
    assert profile.backend_shared is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


@pytest.mark.parametrize(
    "changed_file",
    (
        ".coveragerc",
        ".nvmrc",
        ".ruff.toml",
        "frontend/.npmrc",
        "pytest.ini",
        "ruff.toml",
        "setup.cfg",
        "tox.ini",
    ),
)
def test_alternate_tool_configs_route_privileged_security(changed_file: str) -> None:
    profile = risk_profile.build_risk_profile([changed_file])

    assert profile.workflow_privileged is True
    assert profile.run_backend_blocking is True
    assert profile.run_security is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--base-sha"], "Missing value for --base-sha."),
        (["--base-sha", "--head-sha"], "Missing value for --base-sha."),
        (["--head-sha"], "Missing value for --head-sha."),
        (["--file"], "Missing value for --file."),
        (["--github-output"], "Missing value for --github-output."),
    ],
)
def test_cli_fails_cleanly_when_flag_value_is_missing(
    argv: list[str],
    message: str,
) -> None:
    with pytest.raises(SystemExit, match=message):
        risk_profile.main(argv)

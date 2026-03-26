"""Deterministic tests for Tier 1 PR risk-profile routing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.ci.ci_risk_profile as risk_profile


def test_empty_changed_files_uses_default_risk_profile() -> None:
    profile = risk_profile.build_risk_profile([])

    assert profile.changed_files == ()
    assert profile.docs_only is False
    assert profile.frontend_only is False
    assert profile.ios_only is False
    assert profile.workflow_privileged is False
    assert profile.backend_shared is False
    assert profile.run_backend_blocking is False
    assert profile.run_security is False
    assert profile.run_openapi_sync is False
    assert profile.billing_entitlement is False
    assert profile.insight_ai is False
    assert profile.openapi_contract is False
    assert profile.route_contract_safety is False
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
        ["frontend/src/components/Card.tsx", "frontend/package.json"],
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
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


def test_hidden_github_scripts_path_is_workflow_privileged() -> None:
    profile = risk_profile.build_risk_profile(
        ["./.github/scripts/parse-safety-report.py"],
    )

    assert profile.workflow_privileged is True
    assert profile.merge_governance is True
    assert profile.run_backend_blocking is True
    assert profile.contract_risk_groups == risk_profile.ALL_RISK_GROUPS


def test_billing_router_change_hits_billing_and_openapi_groups() -> None:
    profile = risk_profile.build_risk_profile(
        ["app/routers/billing.py"],
    )

    assert profile.backend_shared is True
    assert profile.billing_entitlement is True
    assert profile.openapi_contract is True
    assert profile.route_contract_safety is True
    assert profile.contract_risk_groups == (
        "billing_entitlement",
        "openapi_contract",
        "route_contract_safety",
    )


def test_openapi_only_change_still_runs_blocking_and_sync() -> None:
    profile = risk_profile.build_risk_profile(
        ["scripts/generate_openapi.py"],
    )

    assert profile.backend_shared is False
    assert profile.openapi_contract is True
    assert profile.run_backend_blocking is True
    assert profile.run_openapi_sync is True
    assert profile.contract_risk_groups == ("openapi_contract",)


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


def test_generic_backend_change_hits_route_contract_safety_group() -> None:
    profile = risk_profile.build_risk_profile(
        ["app/dependencies.py"],
    )

    assert profile.backend_shared is True
    assert profile.route_contract_safety is True
    assert profile.run_backend_blocking is True
    assert profile.contract_risk_groups == ("route_contract_safety",)


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
    assert "billing_entitlement=true" in written


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--base-sha"], "Missing value for --base-sha."),
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

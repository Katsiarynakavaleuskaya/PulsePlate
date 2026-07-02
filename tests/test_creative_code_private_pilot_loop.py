from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_private_pilot_loop_operator as operator
from scripts.orchestration.creative_code_private_pilot_loop_contract import (
    AUTHORITY_FALSE_KEYS,
    ARTIFACT_REF_TYPES,
    DEFAULT_TARGET_SURFACE,
    REVIEW_SOURCE_STATUSES,
    CreativeCodePrivatePilotContractError,
    build_candidate_plan,
    build_current_head_check_summary,
    build_private_pilot_state,
    classify_review_capacity,
    decide_next_action,
    read_json_object,
    validate_candidate_plan,
    validate_private_pilot_state,
)
from scripts.orchestration.github_app_private_pilot_capability import (
    AUTHORITY_KEYS as GITHUB_APP_CAPABILITY_AUTHORITY_KEYS,
    CAPABILITY_STATUSES as GITHUB_APP_CAPABILITY_STATUSES,
    REQUIRED_READ_PERMISSIONS,
    WORKFLOW_DISPATCH_LABELS,
    GithubAppPrivatePilotCapabilityError,
    github_app_capability_state_from_report,
    read_github_app_private_pilot_capability_report,
    reject_unsafe_report_value,
    validate_github_app_private_pilot_capability_report,
)
from scripts.orchestration.creative_code_review_disposition_contract import (
    build_creative_code_review_disposition_packet,
    build_creative_code_review_feedback_record,
)

HEAD_SHA = "a" * 40
OLD_HEAD_SHA = "b" * 40
GENERATED_AT = "2026-07-01T12:00:00Z"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _source_pr() -> dict[str, Any]:
    return {
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "pr_number": 2056,
        "url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2056",
        "state": "open",
        "draft": False,
        "base_ref": "main",
        "base_sha": "c" * 40,
        "head_sha": HEAD_SHA,
    }


def _raw_check(
    name: str,
    *,
    conclusion: str = "success",
    status: str = "completed",
    head_sha: str = HEAD_SHA,
    completed_at: str = "2026-07-01T12:10:00Z",
) -> dict[str, Any]:
    return {
        "name": name,
        "workflow": "CI",
        "status": status,
        "conclusion": conclusion,
        "head_sha": head_sha,
        "details_url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/1",
        "completed_at": completed_at,
    }


def _checks(
    raw_checks: list[dict[str, Any]] | None = None,
    *,
    required_names: tuple[str, ...] = ("lint", "test-main"),
) -> dict[str, Any]:
    return build_current_head_check_summary(
        pr_head_sha=HEAD_SHA,
        raw_checks=raw_checks
        or [
            _raw_check("lint"),
            _raw_check("test-main"),
            _raw_check(
                "stale-lint",
                conclusion="failure",
                head_sha=OLD_HEAD_SHA,
                completed_at="2026-07-01T11:00:00Z",
            ),
        ],
        required_check_names=required_names,
        required_metadata_available=True,
    )


def _review_capacity(friction: str = "none") -> dict[str, Any]:
    if friction == "none":
        return classify_review_capacity(
            [
                {
                    "source": "github_pr_metadata",
                    "status": "available",
                    "source_degraded": False,
                    "blocking": False,
                }
            ]
        )
    if friction == "high":
        return classify_review_capacity(
            [
                {
                    "source": "github_pr_metadata",
                    "status": "degraded",
                    "source_degraded": True,
                    "blocking": False,
                },
                {
                    "source": "fixed_mapping_artifact",
                    "status": "partial",
                    "source_degraded": True,
                    "blocking": False,
                },
            ]
        )
    return {
        "friction": friction,
        "sources": [
            {
                "source": "github_pr_metadata",
                "status": "available",
                "source_degraded": False,
                "blocking": False,
            }
        ],
    }


def _blockers(**overrides: Any) -> dict[str, Any]:
    payload = {
        "actionable_review_count": 0,
        "security_blocker_count": 0,
        "governance_blocker_count": 0,
        "fixed_mapping_required": True,
        "fixed_mapping_present": True,
    }
    payload.update(overrides)
    return payload


def _artifact_ref(artifact_type: str, path: str) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "repo_path": path,
        "exists": True,
        "fingerprint": "sha256:" + "d" * 64,
    }


def _governance_refs(**overrides: Any) -> dict[str, Any]:
    payload = {
        "target_surface": [DEFAULT_TARGET_SURFACE],
        "fixed_mapping": {
            "required": True,
            "present": True,
            "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
            "entry_count": 1,
            "no_actionable": False,
        },
        "pr4_telemetry_refs": [
            _artifact_ref(
                "creative_code_telemetry_event",
                "artifacts/orchestration/creative_code/telemetry/event.json",
            )
        ],
        "pr5_disposition_refs": [
            _artifact_ref(
                "creative_code_review_disposition_packet",
                "artifacts/orchestration/creative_code/review_disposition/packet.json",
            )
        ],
        "pr6_run_plan_refs": [
            _artifact_ref(
                "creative_code_applied_candidate_run_plan",
                "artifacts/orchestration/creative_code/applied_candidates/cv/run_plan.json",
            )
        ],
    }
    payload.update(overrides)
    return payload


def _github_app_capability_report(
    *,
    pull_requests: str = "read",
    checks: str = "read",
    contents: str = "none",
    actions: str = "none",
    workflow_dispatch: bool = False,
) -> dict[str, Any]:
    permissions = {
        "metadata": "read",
        "pull_requests": pull_requests,
        "checks": checks,
        "contents": contents,
        "actions": actions,
        "workflows": "none",
        "administration": "none",
        "organization_administration": "none",
        "members": "none",
        "secrets": "none",  # pragma: allowlist secret
    }
    capabilities = {
        "pull_requests_read": pull_requests == "read",
        "checks_read": checks == "read",
        "metadata_read": True,
        "contents_read": contents == "read",
        "actions_read": actions == "write",
        "workflow_dispatch": actions == "write" and workflow_dispatch,
    }
    authority = {key: False for key in sorted(GITHUB_APP_CAPABILITY_AUTHORITY_KEYS)}
    authority.update(
        {
            "read_pull_requests": capabilities["pull_requests_read"],
            "read_checks": capabilities["checks_read"],
            "read_metadata": capabilities["metadata_read"],
            "read_contents": capabilities["contents_read"],
            "read_actions": capabilities["actions_read"],
            "workflow_dispatch": capabilities["workflow_dispatch"],
        }
    )
    return {
        "schema_version": "1.0",
        "artifact_type": "github_app_private_pilot_capability_report",
        "policy_version": "github-app-private-pilot-capability-report",
        "generated_at_utc": GENERATED_AT,
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "permissions": permissions,
        "capabilities": capabilities,
        "workflow_dispatch": {
            "enabled": workflow_dispatch,
            "label": (
                "workflow_dispatch_actions_write_optional" if workflow_dispatch else "manual_only"
            ),
        },
        "authority": authority,
        "sanitized": True,
    }


def _state(
    *,
    checks: dict[str, Any] | None = None,
    blockers: dict[str, Any] | None = None,
    review_capacity: dict[str, Any] | None = None,
    governance_refs: dict[str, Any] | None = None,
    github_app_capability: dict[str, Any] | None = None,
    external_dependencies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_private_pilot_state(
        generated_at_utc=GENERATED_AT,
        source_pr=_source_pr(),
        current_head_checks=checks or _checks(),
        review_capacity=review_capacity or _review_capacity(),
        blockers=blockers or _blockers(),
        governance_refs=governance_refs or _governance_refs(),
        github_app_capability=github_app_capability,
        external_dependencies=external_dependencies,
    )


def test_state_validation_ignores_stale_failed_checks() -> None:
    state = _state()

    assert state["decision"] == "prepare_next_candidate_plan"
    assert state["current_head_checks"]["stale_diagnostics"]["wrong_head_sha"] == 1
    assert state["current_head_checks"]["stale_diagnostics"]["failed"] == 1
    assert decide_next_action(state) == "prepare_next_candidate_plan"
    assert validate_private_pilot_state(state) == state


def test_superseded_same_head_failure_is_diagnostic_only() -> None:
    checks = _checks(
        [
            _raw_check("lint", conclusion="failure", completed_at="2026-07-01T12:00:00Z"),
            _raw_check("lint", conclusion="success", completed_at="2026-07-01T12:05:00Z"),
            _raw_check("test-main"),
        ],
    )
    state = _state(checks=checks)

    assert state["decision"] == "prepare_next_candidate_plan"
    assert state["current_head_checks"]["stale_diagnostics"]["superseded"] == 1
    assert state["current_head_checks"]["stale_diagnostics"]["failed"] == 1


def test_external_status_details_url_is_not_persisted() -> None:
    checks = _checks(
        [
            {
                **_raw_check("lint"),
                "details_url": "https://example.invalid/status/lint",
            },
            _raw_check("test-main"),
        ]
    )

    assert checks["current"][0]["details_url"] is None
    assert _state(checks=checks)["decision"] == "prepare_next_candidate_plan"


def test_required_metadata_unavailable_waits_for_ci_even_when_visible_checks_pass() -> None:
    checks = build_current_head_check_summary(
        pr_head_sha=HEAD_SHA,
        raw_checks=[_raw_check("lint"), _raw_check("test-main")],
        required_check_names=(),
        required_metadata_available=False,
    )
    state = _state(checks=checks)

    assert state["current_head_checks"]["overall"] == "unknown"
    assert state["current_head_checks"]["required_metadata_available"] is False
    assert state["decision"] == "wait_for_ci"


def test_required_app_check_missing_is_not_satisfied_by_optional_same_name() -> None:
    checks = build_current_head_check_summary(
        pr_head_sha=HEAD_SHA,
        raw_checks=[
            {
                **_raw_check("lint"),
                "workflow": "optional-app",
                "app_id": "999",
            },
            _raw_check("test-main"),
        ],
        required_check_names=("app_id:123:lint", "name:test-main"),
        required_metadata_available=True,
    )

    assert checks["summary"]["required_missing"] == 1
    assert checks["overall"] == "missing"
    assert _state(checks=checks)["decision"] == "wait_for_ci"


def test_app_id_less_required_check_run_is_not_satisfied_by_status_context() -> None:
    checks = build_current_head_check_summary(
        pr_head_sha=HEAD_SHA,
        raw_checks=[
            {
                **_raw_check("build"),
                "workflow": "status_context",
            },
            _raw_check("test-main"),
        ],
        required_check_names=("check_run:build", "name:test-main"),
        required_metadata_available=True,
    )

    assert checks["summary"]["required_missing"] == 1
    assert checks["overall"] == "missing"
    assert _state(checks=checks)["decision"] == "wait_for_ci"


def test_name_only_required_check_conflict_blocks_on_duplicate_sources() -> None:
    checks = build_current_head_check_summary(
        pr_head_sha=HEAD_SHA,
        raw_checks=[
            _raw_check("lint"),
            {
                **_raw_check("lint"),
                "workflow": "optional-app",
                "app_id": "999",
            },
            _raw_check("test-main"),
        ],
        required_check_names=("name:lint", "name:test-main"),
        required_metadata_available=True,
    )

    assert checks["summary"]["required_missing"] == 1
    assert "required-check-identity-conflict:lint" in checks["degraded_reasons"]
    assert _state(checks=checks)["decision"] == "wait_for_ci"


def test_duplicate_current_head_checks_with_missing_timestamps_fail_closed() -> None:
    checks = build_current_head_check_summary(
        pr_head_sha=HEAD_SHA,
        raw_checks=[
            {
                **_raw_check(
                    "lint",
                    conclusion="success",
                    completed_at="",
                ),
                "details_url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/z",
            },
            {
                **_raw_check(
                    "lint",
                    conclusion="failure",
                    completed_at="",
                ),
                "details_url": "https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/a",
            },
            _raw_check("test-main"),
        ],
    )
    state = _state(checks=checks)
    lint_entry = next(entry for entry in checks["current"] if entry["name"] == "lint")

    assert lint_entry["state"] == "failed"
    assert "missing-check-timestamp:lint" in checks["degraded_reasons"]
    assert checks["summary"]["current_failing"] == 1
    assert state["decision"] == "fix_current_pr"


@pytest.mark.parametrize(
    ("checks", "expected"),
    [
        (
            _checks(
                [
                    _raw_check("lint", status="in_progress", conclusion=""),
                    _raw_check("test-main"),
                ]
            ),
            "wait_for_ci",
        ),
        (
            _checks([_raw_check("lint", conclusion="failure"), _raw_check("test-main")]),
            "fix_current_pr",
        ),
        (
            _checks([_raw_check("lint", conclusion="skipped"), _raw_check("test-main")]),
            "fix_current_pr",
        ),
        (
            _checks([_raw_check("lint", status="error", conclusion=""), _raw_check("test-main")]),
            "fix_current_pr",
        ),
        (
            _checks([_raw_check("lint", conclusion=""), _raw_check("test-main")]),
            "wait_for_ci",
        ),
    ],
)
def test_pending_and_failing_current_head_decisions(
    checks: dict[str, Any],
    expected: str,
) -> None:
    assert _state(checks=checks)["decision"] == expected


def test_duplicate_check_names_across_workflows_do_not_hide_required_failure() -> None:
    checks = _checks(
        [
            _raw_check("lint", conclusion="failure", completed_at="2026-07-01T12:00:00Z"),
            {
                **_raw_check("lint", conclusion="success", completed_at="2026-07-01T12:05:00Z"),
                "workflow": "advisory",
            },
            _raw_check("test-main"),
        ],
    )
    state = _state(checks=checks)

    assert checks["summary"]["current_failing"] == 1
    assert checks["stale_diagnostics"]["superseded"] == 0
    assert state["decision"] == "fix_current_pr"


def test_review_capacity_friction_waits_for_review() -> None:
    state = _state(review_capacity=_review_capacity("high"))

    assert state["review_capacity"]["friction"] == "high"
    assert state["decision"] == "wait_for_review"


def test_security_blocker_holds_for_security() -> None:
    state = _state(blockers=_blockers(security_blocker_count=1))

    assert state["decision"] == "hold_for_security"


def test_governance_blocker_count_holds_for_governance() -> None:
    state = _state(blockers=_blockers(governance_blocker_count=1))

    assert state["decision"] == "hold_for_governance"


def test_actionable_review_count_fixes_current_pr() -> None:
    state = _state(blockers=_blockers(actionable_review_count=1))

    assert state["decision"] == "fix_current_pr"


def test_fixed_mapping_missing_holds_for_governance() -> None:
    state = _state(
        blockers=_blockers(fixed_mapping_present=False),
        governance_refs=_governance_refs(
            fixed_mapping={
                "required": True,
                "present": False,
                "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
                "entry_count": 0,
                "no_actionable": False,
            }
        ),
    )

    assert state["decision"] == "hold_for_governance"


def test_degraded_fixed_mapping_evidence_holds_for_governance() -> None:
    fixed_mapping = operator._fixed_mapping_ref(
        {
            "fixed_mapping": {
                "exists": True,
                "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
                "entries": {},
                "no_actionable": True,
                "errors": ["Fixed-mapping artifact was read from stale local HEAD."],
                "present_in_pr_diff": True,
            }
        },
        pr_number=2056,
    )
    state = _state(
        blockers=_blockers(fixed_mapping_present=fixed_mapping["present"]),
        governance_refs=_governance_refs(fixed_mapping=fixed_mapping),
    )

    assert fixed_mapping["present"] is False
    assert state["decision"] == "hold_for_governance"


def test_fixed_mapping_without_diff_proof_holds_for_governance() -> None:
    fixed_mapping = operator._fixed_mapping_ref(
        {
            "fixed_mapping": {
                "exists": True,
                "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
                "entries": {"https://github.com/example/repo/pull/1#discussion_r1": "a" * 40},
                "no_actionable": False,
                "errors": [],
            }
        },
        pr_number=2056,
    )
    state = _state(
        blockers=_blockers(fixed_mapping_present=fixed_mapping["present"]),
        governance_refs=_governance_refs(fixed_mapping=fixed_mapping),
    )

    assert fixed_mapping["present"] is False
    assert state["decision"] == "hold_for_governance"


def test_fixed_mapping_without_entries_or_no_actionable_holds_for_governance() -> None:
    fixed_mapping = operator._fixed_mapping_ref(
        {
            "fixed_mapping": {
                "exists": True,
                "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
                "entries": {},
                "no_actionable": False,
                "errors": [],
                "present_in_pr_diff": True,
            }
        },
        pr_number=2056,
    )
    state = _state(
        blockers=_blockers(fixed_mapping_present=fixed_mapping["present"]),
        governance_refs=_governance_refs(fixed_mapping=fixed_mapping),
    )

    assert fixed_mapping["entry_count"] == 0
    assert fixed_mapping["present"] is False
    assert state["decision"] == "hold_for_governance"


def test_source_pr_allows_safe_slash_base_refs() -> None:
    source = _source_pr()
    source["base_ref"] = "release/1.0"
    state = build_private_pilot_state(
        generated_at_utc=GENERATED_AT,
        source_pr=source,
        current_head_checks=_checks(),
        review_capacity=_review_capacity(),
        blockers=_blockers(),
        governance_refs=_governance_refs(),
    )

    assert state["source_pr"]["base_ref"] == "release/1.0"


def test_draft_source_pr_waits_for_review() -> None:
    source = _source_pr()
    source["draft"] = True
    state = build_private_pilot_state(
        generated_at_utc=GENERATED_AT,
        source_pr=source,
        current_head_checks=_checks(),
        review_capacity=_review_capacity(),
        blockers=_blockers(),
        governance_refs=_governance_refs(),
    )

    assert state["decision"] == "wait_for_review"


def test_closed_unmerged_source_pr_holds_for_governance() -> None:
    source = _source_pr()
    source["state"] = "closed"
    state = build_private_pilot_state(
        generated_at_utc=GENERATED_AT,
        source_pr=source,
        current_head_checks=_checks(),
        review_capacity=_review_capacity(),
        blockers=_blockers(),
        governance_refs=_governance_refs(),
    )

    assert state["decision"] == "hold_for_governance"


def test_hotfix_dependency_can_wait_for_main_when_required() -> None:
    state = _state(
        external_dependencies={
            "hotfix_main_required": True,
            "hotfix_main_merged": False,
            "reference": "PR-2056",
        }
    )

    assert state["decision"] == "wait_for_hotfix_main"


def test_github_app_capability_default_is_manual_only_and_nonblocking() -> None:
    state = _state()

    assert state["github_app_capability"]["status"] == "manual_only"
    assert state["github_app_capability"]["report_present"] is False
    assert state["github_app_capability"]["workflow_dispatch_label"] == "not_checked"
    assert state["github_app_capability"]["missing_permissions"] == []
    assert state["decision"] == "prepare_next_candidate_plan"
    assert decide_next_action(state) == "prepare_next_candidate_plan"


def test_github_app_capability_report_with_read_permissions_allows_candidate_plan() -> None:
    capability = github_app_capability_state_from_report(_github_app_capability_report())
    state = _state(github_app_capability=capability)

    assert state["github_app_capability"]["status"] == "read_only_capable"
    assert state["github_app_capability"]["report_present"] is True
    assert state["github_app_capability"]["read_only"]["pull_requests_read"] is True
    assert state["github_app_capability"]["read_only"]["checks_read"] is True
    assert state["github_app_capability"]["workflow_dispatch_label"] == "manual_only"
    assert state["github_app_capability"]["authority"]["workflow_dispatch"] is False
    assert state["decision"] == "prepare_next_candidate_plan"
    assert build_candidate_plan(state)["decision"] == "prepare_next_candidate_plan"


@pytest.mark.parametrize(
    ("permission", "expected_missing"),
    [
        ("pull_requests", ["pull_requests:read"]),
        ("checks", ["checks:read"]),
    ],
)
def test_github_app_capability_missing_required_read_permission_blocks_candidate_plan(
    permission: str,
    expected_missing: list[str],
) -> None:
    report = _github_app_capability_report()
    report["permissions"][permission] = "none"
    report["capabilities"][f"{permission}_read"] = False
    report["authority"][f"read_{permission}"] = False
    capability = github_app_capability_state_from_report(report)
    state = _state(github_app_capability=capability)

    assert state["github_app_capability"]["status"] == "missing_required_read_permissions"
    assert state["github_app_capability"]["missing_permissions"] == expected_missing
    assert state["decision"] == "hold_for_governance"
    with pytest.raises(CreativeCodePrivatePilotContractError, match="prepare_next_candidate_plan"):
        build_candidate_plan(state)


def test_github_app_capability_gate_does_not_shadow_security_blockers() -> None:
    report = _github_app_capability_report(checks="none")
    report["capabilities"]["checks_read"] = False
    report["authority"]["read_checks"] = False
    state = _state(
        blockers=_blockers(security_blocker_count=1),
        github_app_capability=github_app_capability_state_from_report(report),
    )

    assert state["github_app_capability"]["missing_permissions"] == ["checks:read"]
    assert state["decision"] == "hold_for_security"


def test_github_app_capability_actions_write_is_optional_dispatch_only() -> None:
    without_actions = _state(
        github_app_capability=github_app_capability_state_from_report(
            _github_app_capability_report(actions="none")
        )
    )
    with_dispatch = _state(
        github_app_capability=github_app_capability_state_from_report(
            _github_app_capability_report(actions="write", workflow_dispatch=True)
        )
    )

    assert without_actions["github_app_capability"]["status"] == "read_only_capable"
    assert without_actions["github_app_capability"]["authority"]["workflow_dispatch"] is False
    assert without_actions["decision"] == "prepare_next_candidate_plan"
    assert with_dispatch["github_app_capability"]["status"] == "read_only_with_workflow_dispatch"
    assert (
        with_dispatch["github_app_capability"]["workflow_dispatch_label"]
        == "workflow_dispatch_actions_write_optional"
    )
    assert with_dispatch["github_app_capability"]["authority"]["workflow_dispatch"] is True
    assert with_dispatch["decision"] == "prepare_next_candidate_plan"


@pytest.mark.parametrize("permission", ["pull_requests", "checks", "contents"])
def test_github_app_capability_report_rejects_read_surface_write_permissions(
    permission: str,
) -> None:
    report = _github_app_capability_report()
    report["permissions"][permission] = "write"

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match=permission):
        validate_github_app_private_pilot_capability_report(report)


@pytest.mark.parametrize(
    ("permission", "value"),
    [
        ("contents", "read"),
        ("actions", "read"),
    ],
)
def test_github_app_capability_report_rejects_unneeded_read_authority(
    permission: str,
    value: str,
) -> None:
    report = _github_app_capability_report()
    report["permissions"][permission] = value
    report["capabilities"][f"{permission}_read"] = True
    report["authority"][f"read_{permission}"] = True

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match=permission):
        validate_github_app_private_pilot_capability_report(report)


@pytest.mark.parametrize("permission", ["workflows", "administration", "secrets"])
def test_github_app_capability_report_rejects_privileged_permissions(permission: str) -> None:
    report = _github_app_capability_report()
    report["permissions"][permission] = "read"

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match=permission):
        validate_github_app_private_pilot_capability_report(report)


def test_github_app_capability_report_rejects_actions_write_without_dispatch() -> None:
    report = _github_app_capability_report(actions="write", workflow_dispatch=False)
    report["capabilities"]["actions_read"] = True
    report["authority"]["read_actions"] = True

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match="workflow_dispatch"):
        validate_github_app_private_pilot_capability_report(report)


def test_github_app_capability_report_rejects_permission_capability_mismatch() -> None:
    report = _github_app_capability_report()
    report["capabilities"]["pull_requests_read"] = False

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match="capabilities"):
        validate_github_app_private_pilot_capability_report(report)


def test_github_app_capability_report_rejects_permission_authority_mismatch() -> None:
    report = _github_app_capability_report()
    report["authority"]["read_pull_requests"] = False

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match="authority"):
        validate_github_app_private_pilot_capability_report(report)


def test_github_app_capability_report_schema_documents_runtime_mismatch_guards() -> None:
    schema = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "orchestration"
            / "contracts"
            / "github_app_private_pilot_capability_report.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    schema_text = json.dumps(schema)

    for marker in (
        "actions",
        "workflow_dispatch",
        "read_actions",
        "permission_actions",
        "permission_none",
    ):
        assert marker in schema_text

    mismatched_capability = _github_app_capability_report()
    mismatched_capability["capabilities"]["pull_requests_read"] = False
    mismatched_authority = _github_app_capability_report()
    mismatched_authority["authority"]["read_checks"] = False

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match="capabilities"):
        validate_github_app_private_pilot_capability_report(mismatched_capability)
    with pytest.raises(GithubAppPrivatePilotCapabilityError, match="authority"):
        validate_github_app_private_pilot_capability_report(mismatched_authority)


def test_github_app_capability_state_rejects_dispatch_without_actions_capability() -> None:
    capability = github_app_capability_state_from_report(
        _github_app_capability_report(actions="write", workflow_dispatch=True)
    )
    capability["read_only"]["actions_read"] = False
    capability["authority"]["read_actions"] = False

    payload = _state(
        github_app_capability=github_app_capability_state_from_report(
            _github_app_capability_report()
        )
    )
    payload["github_app_capability"] = capability

    with pytest.raises(CreativeCodePrivatePilotContractError, match="actions"):
        validate_private_pilot_state(payload, validate_identity=False)


def test_github_app_capability_state_rejects_report_present_not_checked() -> None:
    capability = github_app_capability_state_from_report(_github_app_capability_report())
    capability["workflow_dispatch_label"] = "not_checked"
    capability["status"] = "read_only_capable"

    payload = _state(
        github_app_capability=github_app_capability_state_from_report(
            _github_app_capability_report()
        )
    )
    payload["github_app_capability"] = capability

    with pytest.raises(CreativeCodePrivatePilotContractError, match="not_checked|checked"):
        validate_private_pilot_state(payload, validate_identity=False)


@pytest.mark.parametrize(
    ("field", "match"),
    [
        ("contents_read", "contents read"),
        ("actions_read", "actions read"),
    ],
)
def test_github_app_capability_state_rejects_inflated_read_authority(
    field: str,
    match: str,
) -> None:
    payload = _state(
        github_app_capability=github_app_capability_state_from_report(
            _github_app_capability_report()
        )
    )
    payload["github_app_capability"]["read_only"][field] = True
    payload["github_app_capability"]["authority"][f"read_{field.removesuffix('_read')}"] = True

    with pytest.raises(CreativeCodePrivatePilotContractError, match=match):
        validate_private_pilot_state(payload, validate_identity=False)


def test_github_app_capability_report_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    report = tmp_path / "github_app_capability.json"
    report.write_text(
        '{"schema_version":"bad","schema_version":"1.0"}',
        encoding="utf-8",
    )

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match="duplicate key"):
        read_github_app_private_pilot_capability_report(report)


def test_github_app_capability_duplicate_key_error_redacts_sensitive_key(
    tmp_path: Path,
) -> None:
    sensitive_key = "GH_TOKEN=ghs_secretsecretsecret"
    report = tmp_path / "github_app_capability.json"
    report.write_text(
        '{"' + sensitive_key + '":"bad","' + sensitive_key + '":"bad"}',
        encoding="utf-8",
    )

    with pytest.raises(GithubAppPrivatePilotCapabilityError) as exc_info:
        read_github_app_private_pilot_capability_report(report)

    error = str(exc_info.value)
    assert sensitive_key not in error
    assert "<redacted-key>" in error


def test_github_app_capability_extra_key_error_redacts_sensitive_key() -> None:
    sensitive_key = "/Users/katsiaryna_kavaleuskaya/private/path"
    report = _github_app_capability_report()
    report[sensitive_key] = "bad"

    with pytest.raises(GithubAppPrivatePilotCapabilityError) as exc_info:
        validate_github_app_private_pilot_capability_report(report)

    error = str(exc_info.value)
    assert sensitive_key not in error
    assert "<redacted-key>" in error


def test_github_app_capability_report_rejects_symlink_parent(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    report = target / "github_app_capability.json"
    report.write_text(json.dumps(_github_app_capability_report()), encoding="utf-8")

    with pytest.raises(GithubAppPrivatePilotCapabilityError, match="symlinks"):
        read_github_app_private_pilot_capability_report(link / "github_app_capability.json")


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "GH_TOKEN=ghs_secretsecretsecret",
        "private_key",
        "/Users/katsiaryna_kavaleuskaya/private/path",
    ],
)
def test_github_app_capability_report_rejects_tokens_private_keys_and_paths(
    unsafe_value: str,
) -> None:
    with pytest.raises(GithubAppPrivatePilotCapabilityError):
        reject_unsafe_report_value(unsafe_value, label="capability")


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda payload: payload["governance_refs"].__setitem__(
                "target_surface", ["scripts/orchestration/experiment_runner.py"]
            ),
            "target_surface",
        ),
        (
            lambda payload: payload["authority"].__setitem__("push", True),
            "authority.push",
        ),
        (
            lambda payload: payload["source_pr"].__setitem__("body", "raw PR body"),
            "unsupported fields",
        ),
        (
            lambda payload: payload["current_head_checks"]["current"][0].__setitem__(
                "head_sha", OLD_HEAD_SHA
            ),
            "head SHA",
        ),
    ],
)
def test_state_rejects_unsafe_or_drifting_payloads(mutate: Any, match: str) -> None:
    payload = deepcopy(_state())
    mutate(payload)

    with pytest.raises(CreativeCodePrivatePilotContractError, match=match):
        validate_private_pilot_state(payload)


def test_state_validation_recomputes_check_summary_and_overall() -> None:
    payload = deepcopy(_state())
    payload["current_head_checks"]["current"][0]["state"] = "failed"

    with pytest.raises(CreativeCodePrivatePilotContractError, match="summary does not match"):
        validate_private_pilot_state(payload)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "raw_body: full review text",
        "diff --git a/file b/file",
        "raw prompt text",
        "provider payload",
        "oracle stdout",
        "GH_TOKEN=ghs_secretsecretsecret",
        "/Users/katsiaryna_kavaleuskaya/private/path",
        "this is merge-ready",
    ],
)
def test_state_rejects_raw_body_patch_prompt_secret_paths_and_readiness_wording(
    unsafe_value: str,
) -> None:
    payload = deepcopy(_state())
    payload["current_head_checks"]["degraded_reasons"].append(unsafe_value)

    with pytest.raises(CreativeCodePrivatePilotContractError):
        validate_private_pilot_state(payload)


def test_candidate_plan_is_checklist_only_and_cannot_execute_train() -> None:
    plan = build_candidate_plan(_state())

    assert plan["target_surface"] == [DEFAULT_TARGET_SURFACE]
    assert plan["decision"] == "prepare_next_candidate_plan"
    assert plan["authority"]["emit_candidate_plan"] is True
    for key in AUTHORITY_FALSE_KEYS:
        assert plan["authority"][key] is False
        assert key in plan["blocked_authority"]
    for item in plan["checklist"]:
        assert item["checklist_only"] is True
        assert item["executes_in_operator"] is False
        assert item["requires_human_gate"] is True
    assert validate_candidate_plan(plan) == plan


def test_state_requires_generated_at_utc_timestamp() -> None:
    payload = deepcopy(_state())
    payload["generated_at_utc"] = None

    with pytest.raises(CreativeCodePrivatePilotContractError, match="UTC timestamp"):
        validate_private_pilot_state(payload)


def test_candidate_plan_requires_canonical_blocked_authority_order() -> None:
    plan = build_candidate_plan(_state())
    plan["blocked_authority"] = list(reversed(plan["blocked_authority"]))

    with pytest.raises(CreativeCodePrivatePilotContractError, match="canonical sorted order"):
        validate_candidate_plan(plan)


def test_candidate_plan_requires_prepare_decision() -> None:
    waiting_state = _state(
        checks=_checks([_raw_check("lint", status="in_progress"), _raw_check("test-main")])
    )

    with pytest.raises(CreativeCodePrivatePilotContractError, match="prepare_next_candidate_plan"):
        build_candidate_plan(waiting_state)


def test_state_rejects_duplicated_fixed_mapping_blocker_drift() -> None:
    payload = deepcopy(_state())
    payload["blockers"]["fixed_mapping_present"] = True
    payload["governance_refs"]["fixed_mapping"]["present"] = False

    with pytest.raises(CreativeCodePrivatePilotContractError, match="fixed_mapping_present"):
        validate_private_pilot_state(payload)


def test_state_rejects_fixed_mapping_present_without_proof_counts() -> None:
    payload = deepcopy(_state())
    payload["governance_refs"]["fixed_mapping"]["entry_count"] = 0
    payload["governance_refs"]["fixed_mapping"]["no_actionable"] = False

    with pytest.raises(CreativeCodePrivatePilotContractError, match="mapping entries"):
        validate_private_pilot_state(payload)


def test_operator_help_matches_documented_entrypoint(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        operator.main(["--help"])

    captured = capsys.readouterr()
    assert excinfo.value.code == 0
    assert "collect" in captured.out
    assert "status" in captured.out
    assert "decide-next" in captured.out
    assert "prepare-next-candidate" in captured.out
    with pytest.raises(SystemExit) as collect_excinfo:
        operator.main(["collect", "--help"])
    collect_help = capsys.readouterr()
    assert collect_excinfo.value.code == 0
    assert "--github-app-capability-report" in collect_help.out


def test_state_schema_matches_closed_contract_enums() -> None:
    schema = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "orchestration"
            / "contracts"
            / "creative_code_private_pilot_state.v1.schema.json"
        ).read_text(encoding="utf-8")
    )

    review_status = schema["$defs"]["review_source"]["properties"]["status"]
    artifact_type = schema["$defs"]["artifact_ref"]["properties"]["artifact_type"]
    details_url = schema["$defs"]["check_entry"]["properties"]["details_url"]
    external_reference = schema["$defs"]["external_dependencies"]["properties"]["reference"]
    base_ref = schema["$defs"]["source_pr"]["properties"]["base_ref"]
    github_app_capability = schema["$defs"]["github_app_capability"]
    capability_status = github_app_capability["properties"]["status"]
    capability_missing = github_app_capability["properties"]["missing_permissions"]
    capability_dispatch = github_app_capability["properties"]["workflow_dispatch_label"]

    assert sorted(review_status["enum"]) == sorted(REVIEW_SOURCE_STATUSES)
    assert sorted(artifact_type["enum"]) == sorted(ARTIFACT_REF_TYPES)
    assert sorted(capability_status["enum"]) == sorted(GITHUB_APP_CAPABILITY_STATUSES)
    assert sorted(capability_missing["items"]["enum"]) == sorted(REQUIRED_READ_PERMISSIONS)
    assert sorted(capability_dispatch["enum"]) == sorted(WORKFLOW_DISPATCH_LABELS)
    assert len(github_app_capability["allOf"]) == 4
    assert "workflow_dispatch_actions_write_optional" in json.dumps(github_app_capability["allOf"])
    assert base_ref == {"$ref": "#/$defs/git_ref"}
    assert details_url["anyOf"] == [
        {"$ref": "#/$defs/github_url"},
        {"type": "null"},
    ]
    assert external_reference["anyOf"] == [
        {"$ref": "#/$defs/safe_text"},
        {"type": "null"},
    ]


def test_safe_text_schema_denylist_matches_runtime_leak_markers() -> None:
    state_schema = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "orchestration"
            / "contracts"
            / "creative_code_private_pilot_state.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    plan_schema = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "orchestration"
            / "contracts"
            / "creative_code_private_pilot_candidate_plan.v1.schema.json"
        ).read_text(encoding="utf-8")
    )

    unsafe_examples = [
        "/home/runner/work/PulsePlate",
        "C:\\Users\\runner\\work",
        "review_thread_body",
        "pull_request_body",
        "oracle_output",
        "RAW_BODY",
        "Oracle_Output",
    ]
    for schema in (state_schema, plan_schema):
        pattern = re.compile(schema["$defs"]["safe_text"]["not"]["pattern"])
        for unsafe in unsafe_examples:
            assert pattern.search(unsafe)
    capability_schema = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "orchestration"
            / "contracts"
            / "github_app_private_pilot_capability_report.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    capability_text = json.dumps(capability_schema)
    for unsafe_marker in ("secrets", "workflows", "administration", "write_contents"):
        assert unsafe_marker in capability_text
    assert len(capability_schema["allOf"]) == 8
    assert "workflow_dispatch_actions_write_optional" in json.dumps(capability_schema["allOf"])


def test_candidate_plan_schema_requires_exact_blocked_authority_set() -> None:
    schema = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "orchestration"
            / "contracts"
            / "creative_code_private_pilot_candidate_plan.v1.schema.json"
        ).read_text(encoding="utf-8")
    )

    blocked = schema["properties"]["blocked_authority"]

    assert [item["const"] for item in blocked["prefixItems"]] == sorted(AUTHORITY_FALSE_KEYS)
    assert blocked["minItems"] == len(AUTHORITY_FALSE_KEYS)
    assert blocked["maxItems"] == len(AUTHORITY_FALSE_KEYS)


def test_read_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    payload = tmp_path / "pilot_state.json"
    payload.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(CreativeCodePrivatePilotContractError, match="duplicate key"):
        read_json_object(payload)


def _configure_operator_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    root = repo / "artifacts" / "orchestration" / "creative_code"
    private = root / "private_pilot"
    monkeypatch.setattr(operator, "REPO_ROOT", repo)
    monkeypatch.setattr(operator, "CREATIVE_CODE_ROOT", root)
    monkeypatch.setattr(operator, "PRIVATE_PILOT_ROOT", private)
    return private


def test_collect_private_pilot_state_uses_base_sha_for_review_diff_and_branch_for_checks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private = _configure_operator_root(monkeypatch, tmp_path)
    repo = private.parents[3]
    captured: dict[str, Any] = {}
    required_call: dict[str, Any] = {}

    monkeypatch.setattr(
        operator.pr_review_context,
        "infer_repo_name",
        lambda repo_root: "Katsiarynakavaleuskaya/PulsePlate",
    )
    monkeypatch.setattr(
        operator,
        "_gh_pr_view",
        lambda *, pr_number, repo_root: {
            "url": f"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/{pr_number}",
            "state": "OPEN",
            "isDraft": False,
            "baseRefName": "release/1.0",
            "baseRefOid": "c" * 40,
            "headRefOid": HEAD_SHA,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "",
        },
    )

    def fake_collect_review_context(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "review_source_status": [
                {
                    "source": "github_pr_metadata",
                    "status": "available",
                    "source_degraded": False,
                    "blocking": False,
                }
            ],
            "fixed_mapping": {
                "exists": True,
                "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
                "entries": {},
                "no_actionable": True,
                "present_in_pr_diff": True,
            },
        }

    monkeypatch.setattr(
        operator.pr_review_context, "collect_review_context", fake_collect_review_context
    )

    def fake_required_check_names(**kwargs: Any) -> tuple[list[str], bool, bool]:
        required_call.update(kwargs)
        return (["name:lint", "name:test-main"], True, False)

    monkeypatch.setattr(operator, "_required_check_names", fake_required_check_names)
    monkeypatch.setattr(
        operator,
        "_current_head_raw_checks",
        lambda *, repo, head_sha, repo_root: [_raw_check("lint"), _raw_check("test-main")],
    )
    monkeypatch.setattr(operator, "_typed_artifact_refs", lambda **kwargs: [])
    monkeypatch.setattr(operator, "_artifact_refs", lambda **kwargs: [])

    state_path, state = operator.collect_private_pilot_state(
        pr_number=2056,
        output_dir=private / "2056",
        repo_root=repo,
    )

    assert state_path == private / "2056" / "pilot_state.json"
    assert captured["base_ref"] == "c" * 40
    assert captured["head_ref"] == HEAD_SHA
    assert required_call["base_ref"] == "release/1.0"
    assert state["source_pr"]["base_ref"] == "release/1.0"


def test_collect_private_pilot_state_embeds_github_app_capability_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private = _configure_operator_root(monkeypatch, tmp_path)
    repo = private.parents[3]
    report_path = tmp_path / "github_app_capability.json"
    report = _github_app_capability_report(checks="none")
    report["capabilities"]["checks_read"] = False
    report["authority"]["read_checks"] = False
    report_path.write_text(json.dumps(report), encoding="utf-8")

    monkeypatch.setattr(
        operator.pr_review_context,
        "infer_repo_name",
        lambda repo_root: "Katsiarynakavaleuskaya/PulsePlate",
    )
    monkeypatch.setattr(
        operator,
        "_gh_pr_view",
        lambda *, pr_number, repo_root: {
            "url": f"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/{pr_number}",
            "state": "OPEN",
            "isDraft": False,
            "baseRefName": "main",
            "baseRefOid": "c" * 40,
            "headRefOid": HEAD_SHA,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "",
        },
    )
    monkeypatch.setattr(
        operator.pr_review_context,
        "collect_review_context",
        lambda **kwargs: {
            "review_source_status": [
                {
                    "source": "github_pr_metadata",
                    "status": "available",
                    "source_degraded": False,
                    "blocking": False,
                }
            ],
            "fixed_mapping": {
                "exists": True,
                "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
                "entries": {},
                "no_actionable": True,
                "present_in_pr_diff": True,
            },
        },
    )
    monkeypatch.setattr(
        operator,
        "_required_check_names",
        lambda **kwargs: (["name:lint", "name:test-main"], True, False),
    )
    monkeypatch.setattr(
        operator,
        "_current_head_raw_checks",
        lambda *, repo, head_sha, repo_root: [_raw_check("lint"), _raw_check("test-main")],
    )
    monkeypatch.setattr(operator, "_typed_artifact_refs", lambda **kwargs: [])
    monkeypatch.setattr(operator, "_artifact_refs", lambda **kwargs: [])

    _state_path, state = operator.collect_private_pilot_state(
        pr_number=2056,
        output_dir=private / "2056",
        github_app_capability_report=report_path,
        repo_root=repo,
    )

    assert state["github_app_capability"]["report_present"] is True
    assert state["github_app_capability"]["missing_permissions"] == ["checks:read"]
    assert state["decision"] == "hold_for_governance"


def test_collect_private_pilot_state_rejects_capability_report_repo_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private = _configure_operator_root(monkeypatch, tmp_path)
    repo = private.parents[3]
    report_path = tmp_path / "github_app_capability.json"
    report = _github_app_capability_report()
    report["repository"] = "OtherOwner/OtherRepo"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    monkeypatch.setattr(
        operator.pr_review_context,
        "infer_repo_name",
        lambda repo_root: "Katsiarynakavaleuskaya/PulsePlate",
    )
    monkeypatch.setattr(
        operator,
        "_gh_pr_view",
        lambda *, pr_number, repo_root: {
            "url": f"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/{pr_number}",
            "state": "OPEN",
            "isDraft": False,
            "baseRefName": "main",
            "baseRefOid": "c" * 40,
            "headRefOid": HEAD_SHA,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "",
        },
    )
    monkeypatch.setattr(
        operator.pr_review_context,
        "collect_review_context",
        lambda **kwargs: {
            "review_source_status": [
                {
                    "source": "github_pr_metadata",
                    "status": "available",
                    "source_degraded": False,
                    "blocking": False,
                }
            ],
            "fixed_mapping": {
                "exists": True,
                "repo_path": "docs/review/PR_2056_FIXED_MAPPING.md",
                "entries": {},
                "no_actionable": True,
                "present_in_pr_diff": True,
            },
        },
    )
    monkeypatch.setattr(
        operator,
        "_required_check_names",
        lambda **kwargs: (["name:lint", "name:test-main"], True, False),
    )
    monkeypatch.setattr(
        operator,
        "_current_head_raw_checks",
        lambda *, repo, head_sha, repo_root: [_raw_check("lint"), _raw_check("test-main")],
    )
    monkeypatch.setattr(operator, "_typed_artifact_refs", lambda **kwargs: [])
    monkeypatch.setattr(operator, "_artifact_refs", lambda **kwargs: [])

    with pytest.raises(operator.CreativeCodePrivatePilotOperatorError, match="repository"):
        operator.collect_private_pilot_state(
            pr_number=2056,
            output_dir=private / "2056",
            github_app_capability_report=report_path,
            repo_root=repo,
        )


def test_collect_cli_forwards_github_app_capability_report_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(operator, "REPO_ROOT", tmp_path)
    report_path = tmp_path / "github_app_capability.json"
    captured: dict[str, Any] = {}

    def fake_collect_private_pilot_state(**kwargs: Any) -> tuple[Path, dict[str, Any]]:
        captured.update(kwargs)
        output_path = (
            tmp_path
            / "artifacts"
            / "orchestration"
            / "creative_code"
            / "private_pilot"
            / "2056"
            / "pilot_state.json"
        )
        return output_path, {}

    monkeypatch.setattr(operator, "collect_private_pilot_state", fake_collect_private_pilot_state)

    exit_code = operator.main(
        [
            "collect",
            "--pr-number",
            "2056",
            "--output-dir",
            "2056",
            "--github-app-capability-report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert captured["pr_number"] == 2056
    assert captured["output_dir"] == Path("2056")
    assert captured["github_app_capability_report"] == report_path
    assert str(report_path) not in capsys.readouterr().out


def test_collect_cli_reports_capability_report_errors_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_collect_private_pilot_state(**kwargs: Any) -> tuple[Path, dict[str, Any]]:
        raise operator.CreativeCodePrivatePilotOperatorError("capability report invalid")

    monkeypatch.setattr(operator, "collect_private_pilot_state", fake_collect_private_pilot_state)

    exit_code = operator.main(
        [
            "collect",
            "--pr-number",
            "2056",
            "--output-dir",
            "2056",
            "--github-app-capability-report",
            str(tmp_path / "bad.json"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.strip() == "ERROR: capability report invalid"


def test_required_check_names_preserve_source_identity_and_encode_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, str] = {}

    def fake_gh_api_json(path: str, *, repo_root: Path) -> dict[str, Any]:
        captured["path"] = path
        return {
            "contexts": ["legacy-status"],
            "checks": [
                {"context": "lint", "app_id": 123},
                {"context": "build"},
            ],
            "strict": True,
        }

    monkeypatch.setattr(operator, "_gh_api_json", fake_gh_api_json)

    names, available, strict = operator._required_check_names(
        repo="Katsiarynakavaleuskaya/PulsePlate",
        base_ref="release/1.0",
        repo_root=tmp_path,
    )

    assert available is True
    assert strict is True
    assert "branches/release%2F1.0/protection" in captured["path"]
    assert names == ["app_id:123:lint", "check_run:build", "status_context:legacy-status"]


def test_strict_branch_protection_merge_state_waits_for_ci() -> None:
    raw_checks = [_raw_check("lint"), _raw_check("test-main")]
    if operator._strict_merge_state_requires_wait(strict_required=True, merge_state="BEHIND"):
        raw_checks.append(
            operator._strict_merge_state_check(pr_url=_source_pr()["url"], head_sha=HEAD_SHA)
        )
    checks = build_current_head_check_summary(
        pr_head_sha=HEAD_SHA,
        raw_checks=raw_checks,
        required_check_names=("name:lint", "name:test-main"),
        required_metadata_available=True,
    )
    state = _state(checks=checks)

    assert checks["summary"]["required_pending"] == 1
    assert state["decision"] == "wait_for_ci"


def test_pr_review_decision_changes_requested_waits_for_review() -> None:
    sources = operator._github_pr_review_sources(
        {"reviewDecision": "CHANGES_REQUESTED", "mergeStateStatus": "CLEAN"},
        strict_required=False,
    )
    state = _state(review_capacity=classify_review_capacity(sources))

    assert state["review_capacity"]["friction"] == "blocked"
    assert state["decision"] == "wait_for_review"


def _pr5_source_context(*, pr_number: int = 2056) -> dict[str, Any]:
    return {
        "source_kind": "github_fixture",
        "source_id": f"fixture:{pr_number}",
        "source_fingerprint": fingerprint_payload({"fixture": pr_number}),
        "context_path": None,
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "pr_number": pr_number,
    }


def _pr5_record(
    source_id: str,
    *,
    candidate_disposition: str,
    reason_code: str,
    requires_repair: bool,
    repair_priority: int,
) -> dict[str, Any]:
    return build_creative_code_review_feedback_record(
        source_kind="github_fixture",
        source_id=source_id,
        source_fingerprint=fingerprint_payload({"source": source_id}),
        excerpt=f"sanitized finding for {source_id}",
        feedback_kind="review_thread",
        severity="high" if candidate_disposition == "security_blocker" else "medium",
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2056,
        head_sha=HEAD_SHA,
        path=DEFAULT_TARGET_SURFACE,
        line=1,
        side="right",
        classification={
            "candidate_disposition": candidate_disposition,
            "reason_code": reason_code,
            "requires_human_decision": True,
            "requires_repair": requires_repair,
            "repair_priority": repair_priority,
        },
    )


def test_operator_derives_blocker_counts_from_valid_pr5_disposition_refs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packet_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "review_disposition"
        / "packet.json"
    )
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _pr5_record(
                "actionable",
                candidate_disposition="creative_repair_candidate",
                reason_code="test_failure",
                requires_repair=True,
                repair_priority=2,
            ),
            _pr5_record(
                "security",
                candidate_disposition="security_blocker",
                reason_code="security_sensitive",
                requires_repair=True,
                repair_priority=3,
            ),
            _pr5_record(
                "governance",
                candidate_disposition="out_of_scope",
                reason_code="fixed_mapping_governance",
                requires_repair=False,
                repair_priority=0,
            ),
        ],
        source_context=_pr5_source_context(),
        expected_head_sha=HEAD_SHA,
        actual_head_sha=HEAD_SHA,
        classify=False,
    )
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refs = [
        {
            "artifact_type": "creative_code_review_disposition_packet",
            "repo_path": "artifacts/orchestration/creative_code/review_disposition/packet.json",
            "exists": True,
            "fingerprint": "sha256:" + "d" * 64,
        }
    ]

    counts = operator._blocker_counts_from_pr5_refs(
        repo_root=repo,
        refs=refs,
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2056,
        head_sha=HEAD_SHA,
    )

    assert counts == {
        "actionable_review_count": 1,
        "security_blocker_count": 1,
        "governance_blocker_count": 1,
    }


def test_operator_pr5_ref_discovery_ignores_valid_non_disposition_sidecars(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    review_root = repo / "artifacts" / "orchestration" / "creative_code" / "review_disposition"
    review_root.mkdir(parents=True)
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _pr5_record(
                "actionable",
                candidate_disposition="creative_repair_candidate",
                reason_code="test_failure",
                requires_repair=True,
                repair_priority=2,
            )
        ],
        source_context=_pr5_source_context(),
        expected_head_sha=HEAD_SHA,
        actual_head_sha=HEAD_SHA,
        classify=False,
    )
    (review_root / "collection.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "artifact_type": "creative_code_review_feedback_collection",
                "sanitized": True,
            }
        ),
        encoding="utf-8",
    )
    (review_root / "disposition.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (review_root / "launch.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "packet_type": "creative_code_repair_launch_packet",
                "sanitized": True,
            }
        ),
        encoding="utf-8",
    )

    refs = operator._typed_artifact_refs(
        repo_root=repo,
        pattern="review_disposition/*.json",
        artifact_type="creative_code_review_disposition_packet",
        type_key="packet_type",
    )

    assert [Path(ref["repo_path"]).name for ref in refs] == ["disposition.json"]
    assert operator._blocker_counts_from_pr5_refs(
        repo_root=repo,
        refs=refs,
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2056,
        head_sha=HEAD_SHA,
    ) == {
        "actionable_review_count": 1,
        "security_blocker_count": 0,
        "governance_blocker_count": 0,
    }


def test_operator_pr5_ref_discovery_scans_beyond_display_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    review_root = repo / "artifacts" / "orchestration" / "creative_code" / "review_disposition"
    review_root.mkdir(parents=True)
    for index in range(25):
        (review_root / f"{index:02d}_launch.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "packet_type": "creative_code_repair_launch_packet",
                    "sanitized": True,
                }
            ),
            encoding="utf-8",
        )
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _pr5_record(
                "late-actionable",
                candidate_disposition="creative_repair_candidate",
                reason_code="test_failure",
                requires_repair=True,
                repair_priority=2,
            )
        ],
        source_context=_pr5_source_context(),
        expected_head_sha=HEAD_SHA,
        actual_head_sha=HEAD_SHA,
        classify=False,
    )
    (review_root / "zz_disposition.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    refs = operator._typed_artifact_refs(
        repo_root=repo,
        pattern="review_disposition/*.json",
        artifact_type="creative_code_review_disposition_packet",
        type_key="packet_type",
    )

    assert [Path(ref["repo_path"]).name for ref in refs] == ["zz_disposition.json"]
    assert (
        operator._blocker_counts_from_pr5_refs(
            repo_root=repo,
            refs=refs,
            repository="Katsiarynakavaleuskaya/PulsePlate",
            pr_number=2056,
            head_sha=HEAD_SHA,
        )["actionable_review_count"]
        == 1
    )


def test_operator_pr5_ref_discovery_rejects_symlinked_artifact_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    review_parent = repo / "artifacts" / "orchestration" / "creative_code"
    review_parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (review_parent / "review_disposition").symlink_to(outside, target_is_directory=True)
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _pr5_record(
                "outside-actionable",
                candidate_disposition="creative_repair_candidate",
                reason_code="test_failure",
                requires_repair=True,
                repair_priority=2,
            )
        ],
        source_context=_pr5_source_context(),
        expected_head_sha=HEAD_SHA,
        actual_head_sha=HEAD_SHA,
        classify=False,
    )
    (outside / "packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert (
        operator._typed_artifact_refs(
            repo_root=repo,
            pattern="review_disposition/*.json",
            artifact_type="creative_code_review_disposition_packet",
            type_key="packet_type",
        )
        == []
    )


def test_operator_counts_pr5_simple_fix_as_actionable_blocker(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packet_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "review_disposition"
        / "packet.json"
    )
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _pr5_record(
                "simple-fix",
                candidate_disposition="simple_fix",
                reason_code="documentation",
                requires_repair=False,
                repair_priority=0,
            )
        ],
        source_context=_pr5_source_context(),
        expected_head_sha=HEAD_SHA,
        actual_head_sha=HEAD_SHA,
        classify=False,
    )
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert operator._blocker_counts_from_pr5_refs(
        repo_root=repo,
        refs=[
            {
                "artifact_type": "creative_code_review_disposition_packet",
                "repo_path": "artifacts/orchestration/creative_code/review_disposition/packet.json",
                "exists": True,
                "fingerprint": "sha256:" + "d" * 64,
            }
        ],
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2056,
        head_sha=HEAD_SHA,
    ) == {
        "actionable_review_count": 1,
        "security_blocker_count": 0,
        "governance_blocker_count": 0,
    }


def test_operator_ignores_pr5_disposition_refs_for_other_pr(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packet_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "review_disposition"
        / "packet.json"
    )
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _pr5_record(
                "other-pr-actionable",
                candidate_disposition="creative_repair_candidate",
                reason_code="test_failure",
                requires_repair=True,
                repair_priority=2,
            )
        ],
        source_context=_pr5_source_context(pr_number=9999),
        expected_head_sha=HEAD_SHA,
        actual_head_sha=HEAD_SHA,
        classify=False,
    )
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refs = [
        {
            "artifact_type": "creative_code_review_disposition_packet",
            "repo_path": "artifacts/orchestration/creative_code/review_disposition/packet.json",
            "exists": True,
            "fingerprint": "sha256:" + "d" * 64,
        }
    ]

    assert operator._blocker_counts_from_pr5_refs(
        repo_root=repo,
        refs=refs,
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2056,
        head_sha=HEAD_SHA,
    ) == {
        "actionable_review_count": 0,
        "security_blocker_count": 0,
        "governance_blocker_count": 0,
    }


def test_operator_treats_same_pr_stale_pr5_head_as_governance_blocker(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packet_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "review_disposition"
        / "packet.json"
    )
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _pr5_record(
                "stale-pr-actionable",
                candidate_disposition="creative_repair_candidate",
                reason_code="test_failure",
                requires_repair=True,
                repair_priority=2,
            )
        ],
        source_context=_pr5_source_context(),
        expected_head_sha=HEAD_SHA,
        actual_head_sha=OLD_HEAD_SHA,
        classify=False,
    )
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refs = [
        {
            "artifact_type": "creative_code_review_disposition_packet",
            "repo_path": "artifacts/orchestration/creative_code/review_disposition/packet.json",
            "exists": True,
            "fingerprint": "sha256:" + "d" * 64,
        }
    ]

    assert operator._blocker_counts_from_pr5_refs(
        repo_root=repo,
        refs=refs,
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2056,
        head_sha=HEAD_SHA,
    ) == {
        "actionable_review_count": 0,
        "security_blocker_count": 0,
        "governance_blocker_count": 1,
    }


def test_operator_treats_invalid_pr5_ref_as_governance_blocker(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packet_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "review_disposition"
        / "packet.json"
    )
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text('{"unsafe": true}\n', encoding="utf-8")
    refs = [
        {
            "artifact_type": "creative_code_review_disposition_packet",
            "repo_path": "artifacts/orchestration/creative_code/review_disposition/packet.json",
            "exists": True,
            "fingerprint": "sha256:" + "d" * 64,
        }
    ]

    assert operator._blocker_counts_from_pr5_refs(
        repo_root=repo,
        refs=refs,
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2056,
        head_sha=HEAD_SHA,
    ) == {
        "actionable_review_count": 0,
        "security_blocker_count": 0,
        "governance_blocker_count": 1,
    }


def test_operator_writes_state_and_candidate_plan_under_private_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private = _configure_operator_root(monkeypatch, tmp_path)
    state = _state()
    output_dir = private / "2056"
    output_dir.mkdir(parents=True)
    state_path = output_dir / "pilot_state.json"

    operator._write_json_atomic(state_path, state, expected_filename="pilot_state.json")
    assert operator.read_pilot_state(state_path) == state

    plan_path, plan = operator.write_candidate_plan(state_path=state_path)
    assert plan_path == output_dir / "candidate_plan.json"
    assert json.loads(plan_path.read_text(encoding="utf-8")) == plan


def test_run_command_times_out_stalled_gh_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout"))

    monkeypatch.setattr(operator.subprocess, "run", fake_run)

    with pytest.raises(operator.CreativeCodePrivatePilotOperatorError, match="timed out"):
        operator._run_command(["/usr/bin/gh", "api", "repos/example/repo"], cwd=tmp_path)


def test_main_returns_stable_error_for_contract_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_collect(**kwargs: Any) -> tuple[Path, dict[str, Any]]:
        raise CreativeCodePrivatePilotContractError(
            "state.generated_at_utc must be a UTC timestamp."
        )

    monkeypatch.setattr(operator, "collect_private_pilot_state", fail_collect)

    exit_code = operator.main(
        [
            "collect",
            "--pr-number",
            "2056",
            "--output-dir",
            str(tmp_path / "2056"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "ERROR: state.generated_at_utc must be a UTC timestamp." in captured.err


def test_operator_rejects_output_path_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_operator_root(monkeypatch, tmp_path)

    with pytest.raises(operator.CreativeCodePrivatePilotOperatorError, match="stay under"):
        operator._resolve_output_dir(tmp_path / "outside" / "2056", pr_number=2056, create=True)


def test_operator_rejects_symlink_artifact_parent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private = _configure_operator_root(monkeypatch, tmp_path)
    private.mkdir(parents=True)
    target = tmp_path / "target"
    target.mkdir()
    link = private / "2056"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(operator.CreativeCodePrivatePilotOperatorError, match="symlinks"):
        operator._resolve_artifact_file(
            link / "pilot_state.json", expected_filename="pilot_state.json", for_write=False
        )

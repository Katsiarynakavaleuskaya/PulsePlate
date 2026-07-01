from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
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


def _state(
    *,
    checks: dict[str, Any] | None = None,
    blockers: dict[str, Any] | None = None,
    review_capacity: dict[str, Any] | None = None,
    governance_refs: dict[str, Any] | None = None,
    external_dependencies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_private_pilot_state(
        generated_at_utc=GENERATED_AT,
        source_pr=_source_pr(),
        current_head_checks=checks or _checks(),
        review_capacity=review_capacity or _review_capacity(),
        blockers=blockers or _blockers(),
        governance_refs=governance_refs or _governance_refs(),
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
    ],
)
def test_pending_and_failing_current_head_decisions(
    checks: dict[str, Any],
    expected: str,
) -> None:
    assert _state(checks=checks)["decision"] == expected


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


def test_hotfix_dependency_can_wait_for_main_when_required() -> None:
    state = _state(
        external_dependencies={
            "hotfix_main_required": True,
            "hotfix_main_merged": False,
            "reference": "PR-2056",
        }
    )

    assert state["decision"] == "wait_for_hotfix_main"


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


def test_candidate_plan_requires_prepare_decision() -> None:
    waiting_state = _state(
        checks=_checks([_raw_check("lint", status="in_progress"), _raw_check("test-main")])
    )

    with pytest.raises(CreativeCodePrivatePilotContractError, match="prepare_next_candidate_plan"):
        build_candidate_plan(waiting_state)


def test_operator_help_matches_documented_entrypoint(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        operator.main(["--help"])

    captured = capsys.readouterr()
    assert excinfo.value.code == 0
    assert "collect" in captured.out
    assert "status" in captured.out
    assert "decide-next" in captured.out
    assert "prepare-next-candidate" in captured.out


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

    assert sorted(review_status["enum"]) == sorted(REVIEW_SOURCE_STATUSES)
    assert sorted(artifact_type["enum"]) == sorted(ARTIFACT_REF_TYPES)
    assert details_url["anyOf"] == [
        {"$ref": "#/$defs/github_url"},
        {"type": "null"},
    ]
    assert external_reference["anyOf"] == [
        {"$ref": "#/$defs/safe_text"},
        {"type": "null"},
    ]


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

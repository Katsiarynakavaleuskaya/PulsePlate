from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.creative_code_contract import validate_creative_code_candidate_packet
from scripts.orchestration import creative_code_applied_candidate_pr6 as pr6
from scripts.orchestration.creative_code_review_disposition_contract import (
    build_creative_code_repair_launch_packet,
    build_creative_code_review_disposition_packet,
    build_creative_code_review_feedback_record,
)


def _source_context() -> dict[str, Any]:
    return {
        "source_kind": "github_fixture",
        "source_id": "fixture:2048",
        "source_fingerprint": fingerprint_payload({"fixture": 2048}),
        "context_path": None,
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "pr_number": 2048,
    }


def _launch_packet() -> dict[str, Any]:
    record = build_creative_code_review_feedback_record(
        source_kind="github_fixture",
        source_id="review-comment:cv-program",
        source_fingerprint=fingerprint_payload({"source": "review-comment:cv-program"}),
        excerpt=("coverage guard failed on offline CV program review-disposition integration"),
        feedback_kind="review_thread",
        severity="medium",
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2048,
        head_sha="a" * 40,
        path="docs/prompts/cv/program.md",
        line=1,
        side="right",
    )
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[record],
        source_context=_source_context(),
        expected_head_sha="a" * 40,
        actual_head_sha="a" * 40,
    )
    return build_creative_code_repair_launch_packet(packet)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _configure_artifact_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    root = repo / "artifacts" / "orchestration" / "creative_code"
    applied = root / "applied_candidates"
    monkeypatch.setattr(pr6, "REPO_ROOT", repo)
    monkeypatch.setattr(pr6, "CREATIVE_CODE_ROOT", root)
    monkeypatch.setattr(pr6, "APPLIED_CANDIDATES_ROOT", applied)
    return applied


def _refresh_run_plan_identity(plan: dict[str, Any]) -> dict[str, Any]:
    run_plan_id, idempotency_key = pr6._run_plan_identity(plan)
    plan["run_plan_id"] = run_plan_id
    plan["idempotency_key"] = idempotency_key
    return plan


def test_valid_pr5_launch_packet_is_accepted(tmp_path: Path) -> None:
    launch_path = tmp_path / "launch.json"
    _write_json(launch_path, _launch_packet())

    launch = pr6.load_and_validate_launch_packet(
        launch_path,
        target="docs/prompts/cv/program.md",
    )

    assert launch["target_pr1_specification"]["allowed"] is True
    assert launch["authority"] == {
        "create_pr1_specification": True,
        "edit_fixed_mapping": False,
        "generate_patch": False,
        "merge": False,
        "open_pr": False,
        "push": False,
        "resolve_threads": False,
        "write_branch": False,
    }


def test_launch_packet_requires_create_pr1_specification() -> None:
    launch = _launch_packet()
    launch["authority"]["create_pr1_specification"] = False

    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match="create_pr1_specification",
    ):
        pr6.build_run_plan(launch_packet=launch, target="docs/prompts/cv/program.md")


@pytest.mark.parametrize(
    "authority_key",
    [
        "generate_patch",
        "write_branch",
        "push",
        "open_pr",
        "resolve_threads",
        "edit_fixed_mapping",
        "merge",
    ],
)
def test_mutation_authority_is_rejected(authority_key: str) -> None:
    launch = _launch_packet()
    launch["authority"][authority_key] = True

    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match=authority_key,
    ):
        pr6.build_run_plan(launch_packet=launch, target="docs/prompts/cv/program.md")


def test_target_surface_must_be_cv_program_doc() -> None:
    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match="target surface must be exactly",
    ):
        pr6.build_run_plan(
            launch_packet=_launch_packet(),
            target="core/rag/orchestration.py",
        )


def test_target_surface_must_be_allowed_by_experiment_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_surface(paths: list[str]) -> list[str]:
        raise ValueError(f"blocked surface: {paths[0]}")

    monkeypatch.setattr(pr6, "validate_mutable_candidate_surface", reject_surface)

    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match="blocked surface",
    ):
        pr6.build_run_plan(
            launch_packet=_launch_packet(),
            target="docs/prompts/cv/program.md",
        )


def test_run_plan_is_local_only_and_checklist_only() -> None:
    plan = pr6.build_run_plan(
        launch_packet=_launch_packet(),
        target="docs/prompts/cv/program.md",
    )

    assert pr6.validate_run_plan(plan) == plan
    assert (plan["run_plan_id"], plan["idempotency_key"]) == pr6._run_plan_identity(plan)
    assert plan["target_surface"] == ["docs/prompts/cv/program.md"]
    assert plan["target_surface_policy"] == {
        "required_exact_target": "docs/prompts/cv/program.md",
        "validated_by": "validate_mutable_candidate_surface",
        "generated_candidate_may_modify_scripts_orchestration": False,
        "generated_candidate_may_modify_tests": False,
        "generated_candidate_may_modify_governance_docs": False,
    }
    assert plan["candidate_limits"]["allowed_existing_paths"] == ["docs/prompts/cv/program.md"]
    assert plan["candidate_limits"]["allowed_new_paths"] == []
    assert plan["candidate_limits"]["generation_attempts"] == 1
    assert plan["candidate_limits"]["max_changed_lines"] == 120
    assert plan["candidate_limits"]["line_metric"] == "numstat_added_plus_deleted_v1"
    assert "max_diff_lines" not in plan["candidate_limits"]
    assert plan["candidate_limits"]["network_budget"] == 0
    assert plan["authority"]["validate_launch_packet"] is True
    assert plan["authority"]["emit_run_plan"] is True
    assert plan["authority"]["launch_pr1_specification"] is True
    for key in pr6.WRAPPER_FALSE_AUTHORITY_KEYS:
        assert plan["authority"][key] is False
    for commands in plan["commands"].values():
        for command in commands:
            assert command["checklist_only"] is True
            assert command["executes_in_wrapper"] is False
            assert command["command"].startswith(("<repo-python> -m ", "manual: "))
    assert [command["label"] for command in plan["commands"]["pr1_specification"]] == [
        "prepare_specification",
        "record_skeptic_review_decisions",
        "finalize_specification",
    ]
    assert [command["label"] for command in plan["commands"]["pr2_patch_builder"]] == [
        "record_human_patch_admission",
        "build_and_prepare_patch_admission",
        "validate_generation_gate",
        "generate_patch_candidate",
        "dispatch_patch_candidate",
        "finalize_dispatched_result",
    ]
    pr2_commands = [row["command"] for row in plan["commands"]["pr2_patch_builder"]]
    assert "build-and-prepare --finalize-receipt" in pr2_commands[1]
    assert "--human-admission REVIEWED_HUMAN_ADMISSION_REF" in pr2_commands[1]
    assert "validate-run-plan --admission" in pr2_commands[2]
    assert "generate-candidate --gate" in pr2_commands[3]
    assert pr2_commands[4] == (
        "<repo-python> -m scripts.orchestration.experiment_runner_dispatch run "
        "--backend apple-container --packet "
        f"artifacts/orchestration/creative_code/patch_runs/{plan['candidate_id']}-patch/"
        "experiment_packet.json --candidate-patch VERIFIED_PATCH_REF "
        "--image REVIEWED_IMMUTABLE_IMAGE --output REVIEWED_RESULT_FILE.json"
    )
    assert pr2_commands[5] == (
        "<repo-python> -m scripts.orchestration.creative_code_patch_generation "
        "finalize-dispatched-result --gate "
        f"artifacts/orchestration/creative_code/patch_generation/{plan['candidate_id']}-patch/"
        "generation_gate.json --dispatch-result "
        "artifacts/orchestration/experiments/results/REVIEWED_RESULT_FILE.json"
    )
    assert not any("creative_code_patch_builder evaluate" in command for command in pr2_commands)
    assert [row["label"] for row in plan["commands"]["pr3_promotion"]] == [
        "plan_promotion",
        "validate_promotion",
        "promote_non_draft_pr",
    ]
    for row in plan["commands"]["pr3_promotion"][1:]:
        assert "--trusted-dispatch-result" in row["command"]
        assert "--trusted-generation-receipt" in row["command"]
    promote = plan["commands"]["pr3_promotion"][-1]
    assert promote["authority_owner"] == "creative_code_pr_promotion_pr3"
    assert promote["authority_effects"] == [
        "fresh_local_validation",
        "requires_tty_approval",
        "github_write",
        "network",
        "push",
        "open_non_draft_pr",
    ]
    assert promote["requires_human_gate"] is True


def test_historical_direct_evaluate_plan_is_rejected_after_identity_recalculation() -> None:
    plan = pr6.build_run_plan(launch_packet=_launch_packet(), target="docs/prompts/cv/program.md")
    old_plan = deepcopy(plan)
    old_plan["commands"]["pr2_patch_builder"][4]["command"] = (
        "<repo-python> -m scripts.orchestration.creative_code_patch_builder "
        "evaluate --run-dir cv-program-offline-eval-001-patch"
    )
    _refresh_run_plan_identity(old_plan)
    with pytest.raises(pr6.CreativeCodeAppliedCandidatePR6Error, match="commands"):
        pr6.validate_run_plan(old_plan)


@pytest.mark.parametrize("backend", ["REVIEWED_BACKEND", "docker", "auto", "native-linux"])
def test_run_plan_rejects_non_apple_backend_after_identity_recalculation(backend: str) -> None:
    plan = pr6.build_run_plan(launch_packet=_launch_packet(), target="docs/prompts/cv/program.md")
    stale_plan = deepcopy(plan)
    dispatch = stale_plan["commands"]["pr2_patch_builder"][4]
    dispatch["command"] = dispatch["command"].replace(
        "--backend apple-container", f"--backend {backend}"
    )
    _refresh_run_plan_identity(stale_plan)

    assert stale_plan["run_plan_id"] != plan["run_plan_id"]
    assert stale_plan["idempotency_key"] != plan["idempotency_key"]
    with pytest.raises(pr6.CreativeCodeAppliedCandidatePR6Error, match="commands"):
        pr6.validate_run_plan(stale_plan)


def test_read_run_plan_rejects_persisted_stale_generic_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    applied = _configure_artifact_root(monkeypatch, tmp_path)
    plan = pr6.build_run_plan(launch_packet=_launch_packet(), target="docs/prompts/cv/program.md")
    stale_plan = deepcopy(plan)
    dispatch = stale_plan["commands"]["pr2_patch_builder"][4]
    dispatch["command"] = dispatch["command"].replace(
        "--backend apple-container", "--backend REVIEWED_BACKEND"
    )
    _refresh_run_plan_identity(stale_plan)
    plan_path = applied / plan["candidate_id"] / "run_plan.json"
    _write_json(plan_path, stale_plan)

    with pytest.raises(pr6.CreativeCodeAppliedCandidatePR6Error, match="commands"):
        pr6.read_run_plan(plan_path)


def test_run_plan_contains_no_raw_review_body_patch_prompt_or_secret() -> None:
    plan_text = json.dumps(
        pr6.build_run_plan(
            launch_packet=_launch_packet(),
            target="docs/prompts/cv/program.md",
        ),
        sort_keys=True,
    ).lower()

    for forbidden in (
        "raw_body",
        "raw prompt",
        "raw_patch",
        "candidate.patch",
        "chain-of-thought",
        "oracle stdout",
        "oracle stderr",
        "github_token",
        "gh_token",
        "sk-",
        "/users/",
        "/tmp/",
        ".venv/",
    ):
        assert forbidden not in plan_text


def test_run_plan_writer_stays_under_local_artifact_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    applied = _configure_artifact_root(monkeypatch, tmp_path)
    plan = pr6.build_run_plan(
        launch_packet=_launch_packet(),
        target="docs/prompts/cv/program.md",
        candidate_id="cv-program-offline-eval-001",
    )

    output = pr6.write_run_plan(run_plan=plan, output_dir=Path("cv-program-offline-eval-001"))

    assert output == applied / "cv-program-offline-eval-001" / "run_plan.json"
    assert pr6.read_run_plan(output) == plan
    assert (plan["run_plan_id"], plan["idempotency_key"]) == pr6._run_plan_identity(
        pr6.read_run_plan(output)
    )
    packet_path = applied / "cv-program-offline-eval-001" / "candidate_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert validate_creative_code_candidate_packet(packet)["candidate_id"] == (
        "cv-program-offline-eval-001"
    )


def test_output_directory_must_match_candidate_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_artifact_root(monkeypatch, tmp_path)
    plan = pr6.build_run_plan(
        launch_packet=_launch_packet(),
        target="docs/prompts/cv/program.md",
        candidate_id="cv-program-offline-eval-001",
    )

    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match="candidate_id",
    ):
        pr6.write_run_plan(run_plan=plan, output_dir=Path("other-candidate"))


def test_output_directory_must_stay_under_artifact_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_artifact_root(monkeypatch, tmp_path)
    plan = pr6.build_run_plan(
        launch_packet=_launch_packet(),
        target="docs/prompts/cv/program.md",
    )

    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match="output directory must stay",
    ):
        pr6.write_run_plan(run_plan=plan, output_dir=tmp_path / "outside")


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda plan: plan["candidate_limits"].__setitem__("network_budget", 1),
            "candidate_limits",
        ),
        (
            lambda plan: plan["expected_artifacts"].__setitem__(
                "pr1_source_candidate_packet",
                "artifacts/orchestration/creative_code/applied_candidates/wrong/candidate_packet.json",
            ),
            "expected_artifacts",
        ),
        (
            lambda plan: plan["commands"]["pr3_promotion"][-1].__setitem__(
                "authority_effects",
                [],
            ),
            "commands",
        ),
    ],
)
def test_run_plan_rejects_nested_tampering_after_identity_refresh(
    mutate: Any,
    match: str,
) -> None:
    plan = pr6.build_run_plan(
        launch_packet=_launch_packet(),
        target="docs/prompts/cv/program.md",
    )
    tampered = deepcopy(plan)
    mutate(tampered)
    _refresh_run_plan_identity(tampered)

    with pytest.raises(pr6.CreativeCodeAppliedCandidatePR6Error, match=match):
        pr6.validate_run_plan(tampered)


def test_read_run_plan_rejects_duplicate_json_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    applied = _configure_artifact_root(monkeypatch, tmp_path)
    plan_dir = applied / "cv-program-offline-eval-001"
    plan_dir.mkdir(parents=True)
    plan_path = plan_dir / "run_plan.json"
    plan_path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(pr6.CreativeCodeAppliedCandidatePR6Error, match="duplicate key"):
        pr6.read_run_plan(plan_path)


def test_run_plan_rejects_tampered_command_execution_flag() -> None:
    plan = pr6.build_run_plan(
        launch_packet=_launch_packet(),
        target="docs/prompts/cv/program.md",
    )
    tampered = deepcopy(plan)
    tampered["commands"]["pr2_patch_builder"][0]["executes_in_wrapper"] = True

    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match="commands",
    ):
        pr6.validate_run_plan(tampered)


def test_run_plan_rejects_unknown_authority_flags() -> None:
    plan = pr6.build_run_plan(
        launch_packet=_launch_packet(),
        target="docs/prompts/cv/program.md",
    )
    tampered = deepcopy(plan)
    tampered["authority"]["new_provider_write"] = True

    with pytest.raises(
        pr6.CreativeCodeAppliedCandidatePR6Error,
        match="new_provider_write",
    ):
        pr6.validate_run_plan(tampered)


def test_cli_plan_run_writes_run_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    applied = _configure_artifact_root(monkeypatch, tmp_path)
    launch_path = tmp_path / "launch.json"
    _write_json(launch_path, _launch_packet())

    exit_code = pr6.main(
        [
            "plan-run",
            "--launch-packet",
            str(launch_path),
            "--target",
            "docs/prompts/cv/program.md",
            "--candidate-id",
            "cv-program-offline-eval-001",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert pr6.SUCCESS_PLAN_OUTPUT in captured.out
    assert (applied / "cv-program-offline-eval-001" / "run_plan.json").is_file()
    packet_path = applied / "cv-program-offline-eval-001" / "candidate_packet.json"
    assert validate_creative_code_candidate_packet(
        json.loads(packet_path.read_text(encoding="utf-8"))
    )["target_surface"] == ["docs/prompts/cv/program.md"]

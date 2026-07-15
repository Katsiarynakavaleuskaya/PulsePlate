from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import (
    creative_code_patch_builder,
    creative_code_patch_contract,
    creative_code_patch_executor,
    creative_code_patch_workspace,
    experiment_runner,
)
from scripts.orchestration.creative_code_patch_builder import CreativeCodePatchBuilderError
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
    build_creative_code_patch_build_request,
    build_creative_code_patch_result,
    read_creative_code_patch_build_request,
    validate_creative_code_patch_build_request,
    validate_creative_code_patch_result,
)
from scripts.orchestration import creative_code_specification
from scripts.orchestration.creative_code_specification import (
    build_creative_code_specification_bundle,
    build_default_specification_variants,
    build_pending_skeptic_reviews,
    read_creative_code_specification_bundle,
)
from scripts.orchestration.experiment_contract import validate_cv_context

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_BUNDLE = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.json"
REQUEST_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_patch_request.v1.schema.json"
)
RESULT_SCHEMA = REPO_ROOT / "docs/orchestration/contracts/creative_code_patch_result.v1.schema.json"


def _git(repo: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    if not git_binary:
        raise AssertionError("git binary is required for creative-code patch tests.")
    if git_binary.endswith("/usr/libexec/git-core/git"):
        git_binary = "/usr/bin/git"
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(
        [git_binary, *args],
        cwd=str(repo),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_patch_repo(tmp_path: Path, *, include_target_file: bool = True) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    (repo / "core" / "rag").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "docs" / "orchestration").mkdir(parents=True)
    (repo / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
    if include_target_file:
        (repo / "core" / "rag" / "orchestration.py").write_text(
            "def value() -> int:\n    return 1\n",
            encoding="utf-8",
        )
    (repo / "tests" / "test_creative_code_patch_builder.py").write_text(
        "def test_placeholder() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (repo / "docs" / "orchestration" / "GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md").write_text(
        "# Contract\n",
        encoding="utf-8",
    )
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", base_sha)
    return repo, base_sha


def _patch_modules_to_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    artifact_root = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs"
    monkeypatch.setattr(creative_code_patch_workspace, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_patch_workspace, "ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(creative_code_patch_builder, "REPO_ROOT", repo)


def _reference_bundle() -> dict[str, Any]:
    return read_creative_code_specification_bundle(REFERENCE_BUNDLE)


def _fingerprint_review(review: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: review[key]
        for key in sorted(
            creative_code_specification.REVIEW_KEYS - {"review_id", "review_fingerprint"}
        )
    }
    review["review_fingerprint"] = fingerprint_payload(payload)
    return review


def _cv_reference_bundle() -> dict[str, Any]:
    packet = json.loads(
        (REPO_ROOT / "docs/orchestration/contracts/creative_code_candidate.v1.json").read_text(
            encoding="utf-8"
        )
    )
    packet["candidate_id"] = "cv-program-offline-eval-001"
    packet["idempotency_key"] = "cv-program-offline-eval-001-v1"
    packet["source_creative_research"] = {
        "bundle_id": "creative-research-cv-program-offline-eval",
        "candidate_id": "creative-research-cv-program-offline-eval-001",
        "promotion_decision": "promote",
        "fingerprint": "sha256:" + ("8" * 64),
        "evidence_ref": "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md",
    }
    packet["target_surface"] = ["docs/prompts/cv/program.md"]
    packet["immutable_oracles"] = ["tests/test_creative_code_patch_builder.py"]
    packet["evidence_bundle"] = {
        "artifact_refs": [
            "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md",
            "docs/prompts/cv/program.md",
        ],
        "required_tests": ["tests/test_creative_code_patch_builder.py"],
        "negative_controls": [
            "runtime_photo_upload_not_authorized",
            "medical_claim_wording_rejected",
            "raw_image_retention_not_authorized",
        ],
    }
    variants = build_default_specification_variants(packet)
    reviews: list[dict[str, Any]] = []
    for review in build_pending_skeptic_reviews(source_packet=packet, variants=variants):
        review = dict(review)
        if review["variant_id"] == variants[0]["variant_id"]:
            review["decision"] = "pass"
            review["blockers"] = []
        else:
            review["blockers"] = ["non_selected_candidate_variant"]
        reviews.append(_fingerprint_review(review))
    return build_creative_code_specification_bundle(
        source_packet=packet,
        variants=variants,
        skeptic_reviews=reviews,
    )


def _reference_request() -> dict[str, Any]:
    return _request_for_base("a" * 40)


def _reference_result() -> dict[str, Any]:
    return build_creative_code_patch_result(
        request=_reference_request(),
        changed_paths=["core/rag/orchestration.py"],
        patch_fingerprint="sha256:" + ("b" * 64),
        patch_bytes=128,
        diff_lines=8,
        runner_result={
            "experiment_id": "exp-pr2-reference",
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["core/rag/orchestration.py"],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
            },
            "oracle_results": [{"status": "passed"}],
            "shared_tree_untouched": True,
        },
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
    )


def _request_for_base(base_sha: str) -> dict[str, Any]:
    return build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha=base_sha,
        approval_ref="PR-2-test-approval",
        allowed_existing_paths=["core/rag/orchestration.py"],
        allowed_new_paths=[],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=[
            "candidate patch stays inside allowlisted surface",
            "candidate patch preserves immutable oracle commands",
        ],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )


def _write_generated_run(
    *,
    run_id: str,
    base_sha: str,
) -> Path:
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=True)
    assert isinstance(run_dir, Path)
    request = _request_for_base(base_sha)
    patch_text = "diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py\n"
    state = {
        "run_id": run_id,
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": base_sha,
        "workspace": {"origin_removed": True},
        "candidate_patch_generated": True,
        "checkout_destroyed": True,
    }
    metadata = {
        "changed_paths": ["core/rag/orchestration.py"],
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    creative_code_patch_workspace.write_json_atomic(run_dir / "request.json", request)
    creative_code_patch_workspace.write_json_atomic(
        run_dir / "source_bundle.json", _reference_bundle()
    )
    creative_code_patch_workspace.write_json_atomic(run_dir / "state.json", state)
    creative_code_patch_workspace.write_json_atomic(run_dir / "patch_metadata.json", metadata)
    (run_dir / "candidate.patch").write_text(patch_text, encoding="utf-8")
    return run_dir


def test_generation_prompt_includes_budget_and_no_test_contract() -> None:
    bundle = _reference_bundle()
    request = _reference_request()
    variant = creative_code_patch_builder._selected_variant(bundle)

    prompt = creative_code_patch_builder._build_generation_prompt(
        request=request,
        variant=variant,
    )

    assert "Hard mutation budget:" in prompt
    assert f"- max_changed_files: {request['budgets']['max_changed_files']}" in prompt
    assert f"- max_diff_lines: {request['budgets']['max_diff_lines']}" in prompt
    assert f"- max_patch_bytes: {request['budgets']['max_patch_bytes']}" in prompt
    assert "Do not run tests, package managers, broad repository searches" in prompt
    assert "inspect only the allowed existing paths" in prompt
    assert "Finish immediately after the allowed file edits" in prompt
    assert "single file edit" not in prompt
    assert "The wrapper will validate and export the patch." in prompt


def test_pr2_experiment_budget_overrides_follow_normalized_request() -> None:
    request = _reference_request()

    assert creative_code_patch_builder.build_pr2_experiment_budget_overrides(request) == {
        "wall_clock_seconds": 60,
        "retry_budget": 1,
        "max_changed_files": 3,
        "network_budget": 0,
        "benchmark_budget": 1,
        "test_budget": 1,
    }


def test_pr2_experiment_packet_binds_builder_owned_semantics() -> None:
    request = _reference_request()
    bundle = _reference_bundle()
    selected_variant = creative_code_patch_builder._selected_variant(bundle)

    packet = creative_code_patch_builder.build_pr2_experiment_packet(
        request=request,
        source_bundle=bundle,
        changed_paths=["core/rag/orchestration.py"],
    )

    assert packet["decision_question"] == selected_variant["problem_statement"]
    assert packet["task_class"] == "Experimentation"
    assert packet["negative_controls"] == selected_variant["negative_controls"]
    assert packet["promotion_target"] == "audit_artifact"
    assert packet["creative_research_origin"] == {
        key: bundle["source_creative_research"][key]
        for key in ("bundle_id", "candidate_id", "promotion_decision")
    }


def test_generation_prompt_uses_single_file_wording_for_single_file_budget() -> None:
    bundle = _reference_bundle()
    request = deepcopy(_reference_request())
    request["budgets"]["max_changed_files"] = 1
    variant = creative_code_patch_builder._selected_variant(bundle)

    prompt = creative_code_patch_builder._build_generation_prompt(
        request=request,
        variant=variant,
    )

    assert "Finish immediately after the single allowed file edit" in prompt
    assert "- max_changed_files: 1" in prompt


@pytest.mark.parametrize(
    "name_status",
    [
        "M",
        "M\t",
        "M\tcore/rag/orchestration.py\textra",
        "M\t../orchestration.py",
        "M\t/abs/orchestration.py",
        "M\tcore\\rag\\orchestration.py",
        "M\tcore/rag/orchestration.py\nA\tcore/rag/orchestration.py",
    ],
)
def test_name_status_parser_rejects_malformed_or_ambiguous_paths(name_status: str) -> None:
    with pytest.raises(CreativeCodePatchBuilderError):
        creative_code_patch_builder._parse_name_status(name_status)


def test_reference_patch_contracts_validate_and_schema_is_closed() -> None:
    request = _reference_request()
    result = _reference_result()
    bundle = _reference_bundle()
    request_schema = json.loads(REQUEST_SCHEMA.read_text(encoding="utf-8"))
    result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))

    assert validate_creative_code_patch_build_request(request, source_bundle=bundle) == request
    assert validate_creative_code_patch_result(result) == result
    assert request_schema["additionalProperties"] is False
    assert result_schema["additionalProperties"] is False
    assert request_schema["$defs"]["authority"]["additionalProperties"] is False
    assert request_schema["$defs"]["executor"]["additionalProperties"] is False
    assert result_schema["$defs"]["runner_summary"]["additionalProperties"] is False
    assert result_schema["$defs"]["authority"]["properties"]["write_repository"]["const"] is False
    assert result_schema["$defs"]["failure_class"]["enum"] == [
        None,
        "timeout",
        "oom",
        "metric_regression",
        "guard_failure",
        "policy_violation",
        "unchanged_result",
        "capability_mismatch",
        "infra_flake",
    ]
    assert set(result_schema["$defs"]["failure_class"]["enum"][1:]) == (
        creative_code_patch_contract.FAILURE_CLASSES
    )
    assert result_schema["properties"]["failure_class"]["$ref"].endswith("failure_class")
    assert result_schema["$defs"]["runner_summary"]["properties"]["failure_class"]["$ref"].endswith(
        "failure_class"
    )
    assert result_schema["allOf"][0]["then"]["properties"]["runner_summary"] == {
        "$ref": "#/$defs/accepted_runner_proof"
    }
    accepted_runner_proof = result_schema["$defs"]["accepted_runner_proof"]
    assert accepted_runner_proof["properties"]["status"] == {"const": "accepted"}
    assert accepted_runner_proof["properties"]["failure_class"] == {"const": None}
    assert accepted_runner_proof["properties"]["shared_tree_untouched"] == {"const": True}
    accepted_oracle_pairs = {
        (
            pair["properties"]["oracle_commands_configured"]["const"],
            pair["properties"]["oracle_commands_executed"]["const"],
        )
        for pair in accepted_runner_proof["oneOf"]
    }
    assert accepted_oracle_pairs == {(count, count) for count in range(1, 21)}
    ordered_failure_classes = result_schema["$defs"]["failure_class"]["enum"][1:]
    assert result_schema["allOf"][1]["then"]["properties"]["failure_class"]["enum"] == (
        ordered_failure_classes
    )
    assert result_schema["allOf"][2]["if"]["properties"]["failure_class"] == {
        "const": "capability_mismatch"
    }
    root_runner_rule = result_schema["allOf"][2]["then"]["properties"]["runner_summary"]
    assert root_runner_rule["required"] == ["status", "failure_class"]
    root_retry_rule = root_runner_rule["properties"]
    assert root_retry_rule["status"] == {"const": "rejected"}
    assert root_retry_rule["failure_class"] == {"const": "capability_mismatch"}
    assert root_retry_rule["attempts"] == {"enum": [0, 1]}
    assert root_retry_rule["retries_consumed"] == {"const": 0}
    rejected_pair_rule = result_schema["allOf"][3]
    assert rejected_pair_rule["if"]["properties"]["status"] == {"const": "rejected"}
    assert rejected_pair_rule["if"]["properties"]["runner_summary"]["properties"]["status"] == {
        "const": "rejected"
    }
    rejected_pairs = {
        (
            pair["properties"]["failure_class"]["const"],
            pair["properties"]["runner_summary"]["properties"]["failure_class"]["const"],
        )
        for pair in rejected_pair_rule["then"]["oneOf"]
    }
    assert rejected_pairs == {(failure, failure) for failure in ordered_failure_classes}
    runner_rules = result_schema["$defs"]["runner_summary"]["allOf"]
    assert runner_rules[0]["then"]["properties"]["failure_class"] == {"const": None}
    assert runner_rules[1]["then"]["properties"]["failure_class"]["enum"] == (
        ordered_failure_classes
    )
    assert runner_rules[2]["if"]["properties"]["failure_class"] == {"const": "capability_mismatch"}
    assert runner_rules[2]["then"]["properties"]["attempts"] == {"enum": [0, 1]}
    assert runner_rules[2]["then"]["properties"]["retries_consumed"] == {"const": 0}
    zero_attempt_rule = runner_rules[3]
    assert zero_attempt_rule["if"]["required"] == ["failure_class", "attempts"]
    assert zero_attempt_rule["if"]["properties"] == {
        "failure_class": {"const": "capability_mismatch"},
        "attempts": {"const": 0},
    }
    assert zero_attempt_rule["then"]["properties"] == {
        "mutated_path_count": {"const": 0},
        "oracle_commands_executed": {"const": 0},
    }
    assert "oracle_commands_configured" not in zero_attempt_rule["then"]["properties"]
    assert (
        result_schema["$defs"]["authority"]["properties"]["candidate_patch_generated"]["const"]
        is True
    )
    assert (
        result_schema["$defs"]["authority"]["properties"]["candidate_patch_evaluated"]["const"]
        is True
    )
    assert request_schema["properties"]["allowed_existing_paths"]["$ref"].endswith(
        "path_array_allow_empty"
    )
    leak_pattern = re.compile(
        request_schema["$defs"]["non_empty_string_array"]["items"]["not"]["pattern"],
        re.IGNORECASE,
    )
    for blocked in (
        "authorization: bearer token",
        "private key material",
        "api key value",
    ):
        assert leak_pattern.search(blocked), blocked


def test_patch_result_rejects_workspace_base_sha_mismatch() -> None:
    result = _reference_result()
    result["workspace_summary"]["detached_base_sha"] = "b" * 40

    with pytest.raises(CreativeCodePatchContractError, match="detached_base_sha"):
        validate_creative_code_patch_result(result)


def test_build_result_rejects_malformed_runner_summary_inputs() -> None:
    request = _reference_request()
    runner_result: dict[str, Any] = {
        "experiment_id": "exp-pr2-reference",
        "status": "rejected",
        "failure_class": "guard_failure",
        "mutated_paths": ["core/rag/orchestration.py"],
        "budget_observations": {
            "oracle_commands_configured": "1",
            "attempts": 1,
            "retries_consumed": 0,
        },
        "oracle_results": [],
        "shared_tree_untouched": True,
    }

    with pytest.raises(CreativeCodePatchContractError, match="oracle_commands_configured"):
        build_creative_code_patch_result(
            request=request,
            changed_paths=["core/rag/orchestration.py"],
            patch_fingerprint="sha256:" + ("b" * 64),
            patch_bytes=128,
            diff_lines=8,
            runner_result=runner_result,
            checkout_destroyed=True,
            origin_removed=True,
            shared_tree_untouched=True,
            failure_class="guard_failure",
        )

    runner_result["budget_observations"]["oracle_commands_configured"] = 1
    runner_result["mutated_paths"] = "core/rag/orchestration.py"

    with pytest.raises(CreativeCodePatchContractError, match="mutated_paths"):
        build_creative_code_patch_result(
            request=request,
            changed_paths=["core/rag/orchestration.py"],
            patch_fingerprint="sha256:" + ("b" * 64),
            patch_bytes=128,
            diff_lines=8,
            runner_result=runner_result,
            checkout_destroyed=True,
            origin_removed=True,
            shared_tree_untouched=True,
            failure_class="guard_failure",
        )


def test_build_result_rejects_accepted_capability_mismatch() -> None:
    runner_result = {
        "experiment_id": "exp-pr2-capability-mismatch",
        "status": "accepted",
        "failure_class": "capability_mismatch",
        "mutated_paths": ["core/rag/orchestration.py"],
        "budget_observations": {
            "oracle_commands_configured": 1,
            "attempts": 1,
            "retries_consumed": 0,
        },
        "oracle_results": [],
        "shared_tree_untouched": True,
    }

    with pytest.raises(
        CreativeCodePatchContractError,
        match="accepted runner summaries must not have failure_class",
    ):
        build_creative_code_patch_result(
            request=_reference_request(),
            changed_paths=["core/rag/orchestration.py"],
            patch_fingerprint="sha256:" + ("b" * 64),
            patch_bytes=128,
            diff_lines=8,
            runner_result=runner_result,
            checkout_destroyed=True,
            origin_removed=True,
            shared_tree_untouched=True,
        )


def test_patch_result_rejects_incoherent_runner_status_and_preserves_wrapper_rejection() -> None:
    accepted_with_rejected_runner = _reference_result()
    accepted_with_rejected_runner["runner_summary"]["status"] = "rejected"
    accepted_with_rejected_runner["runner_summary"]["failure_class"] = "guard_failure"
    accepted_with_rejected_runner["workspace_summary"]["origin_removed"] = False

    with pytest.raises(
        CreativeCodePatchContractError,
        match="accepted results require an accepted runner summary",
    ):
        validate_creative_code_patch_result(accepted_with_rejected_runner)

    rejected_runner_without_failure = _reference_result()
    rejected_runner_without_failure["runner_summary"]["status"] = "rejected"

    with pytest.raises(
        CreativeCodePatchContractError,
        match="rejected runner summaries require failure_class",
    ):
        validate_creative_code_patch_result(rejected_runner_without_failure)

    wrapper_rejection = _reference_result()
    wrapper_rejection["status"] = "rejected"
    wrapper_rejection["failure_class"] = "guard_failure"
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(
        wrapper_rejection
    )
    wrapper_rejection["result_id"] = result_id
    wrapper_rejection["idempotency_key"] = idempotency_key

    assert validate_creative_code_patch_result(wrapper_rejection) == wrapper_rejection

    capability_without_runner_proof = _reference_result()
    capability_without_runner_proof["status"] = "rejected"
    capability_without_runner_proof["failure_class"] = "capability_mismatch"
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(
        capability_without_runner_proof
    )
    capability_without_runner_proof["result_id"] = result_id
    capability_without_runner_proof["idempotency_key"] = idempotency_key

    with pytest.raises(
        CreativeCodePatchContractError,
        match="capability_mismatch results require a rejected runner summary",
    ):
        validate_creative_code_patch_result(capability_without_runner_proof)


@pytest.mark.parametrize(
    "runner_updates",
    [
        {"shared_tree_untouched": False},
        {"oracle_commands_configured": 0, "oracle_commands_executed": 0},
        {"oracle_commands_configured": 2, "oracle_commands_executed": 1},
    ],
)
def test_patch_result_rejects_incomplete_accepted_runner_proof(
    runner_updates: dict[str, Any],
) -> None:
    result = _reference_result()
    result["runner_summary"].update(runner_updates)

    with pytest.raises(
        CreativeCodePatchContractError,
        match="accepted results require complete runner oracle and shared-tree proof",
    ):
        validate_creative_code_patch_result(result)


@pytest.mark.parametrize(
    ("result_failure", "runner_failure"),
    [
        ("capability_mismatch", "infra_flake"),
        ("infra_flake", "capability_mismatch"),
    ],
)
def test_patch_result_rejects_mismatched_rejected_failures(
    result_failure: str,
    runner_failure: str,
) -> None:
    tampered = _reference_result()
    tampered["status"] = "rejected"
    tampered["failure_class"] = result_failure
    tampered["runner_summary"].update(
        {
            "status": "rejected",
            "failure_class": runner_failure,
            "attempts": 1,
            "retries_consumed": 0,
        }
    )
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(tampered)
    tampered["result_id"] = result_id
    tampered["idempotency_key"] = idempotency_key

    with pytest.raises(
        CreativeCodePatchContractError,
        match="rejected result and runner summary failure_class values must match",
    ):
        validate_creative_code_patch_result(tampered)


def test_patch_result_rejects_capability_mismatch_retry_tamper() -> None:
    tampered = _reference_result()
    tampered["status"] = "rejected"
    tampered["failure_class"] = "capability_mismatch"
    tampered["runner_summary"].update(
        {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "attempts": 2,
            "retries_consumed": 1,
        }
    )
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(tampered)
    tampered["result_id"] = result_id
    tampered["idempotency_key"] = idempotency_key

    with pytest.raises(
        CreativeCodePatchContractError,
        match="capability_mismatch must use attempts 0 or 1 and retries_consumed 0",
    ):
        validate_creative_code_patch_result(tampered)

    top_level_tamper = _reference_result()
    top_level_tamper["status"] = "rejected"
    top_level_tamper["failure_class"] = "capability_mismatch"
    top_level_tamper["runner_summary"]["attempts"] = 2
    top_level_tamper["runner_summary"]["retries_consumed"] = 1
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(
        top_level_tamper
    )
    top_level_tamper["result_id"] = result_id
    top_level_tamper["idempotency_key"] = idempotency_key

    with pytest.raises(
        CreativeCodePatchContractError,
        match="capability_mismatch results require a rejected runner summary",
    ):
        validate_creative_code_patch_result(top_level_tamper)

    compound_tamper = _reference_result()
    compound_tamper["failure_class"] = "capability_mismatch"
    compound_tamper["runner_summary"].update(
        {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "attempts": 2,
            "retries_consumed": 1,
        }
    )
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(
        compound_tamper
    )
    compound_tamper["result_id"] = result_id
    compound_tamper["idempotency_key"] = idempotency_key

    with pytest.raises(
        CreativeCodePatchContractError,
        match="accepted results must not have failure_class",
    ):
        validate_creative_code_patch_result(compound_tamper)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        (
            "mutated_path_count",
            "capability_mismatch with attempts 0 must use mutated_path_count 0",
        ),
        (
            "oracle_commands_executed",
            "capability_mismatch with attempts 0 must use oracle_commands_executed 0",
        ),
    ],
)
def test_patch_result_rejects_zero_attempt_capability_execution_evidence(
    field: str,
    message: str,
) -> None:
    tampered = _reference_result()
    tampered["status"] = "rejected"
    tampered["failure_class"] = "capability_mismatch"
    tampered["runner_summary"].update(
        {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "mutated_path_count": 0,
            "oracle_commands_executed": 0,
            "attempts": 0,
            "retries_consumed": 0,
        }
    )
    tampered["runner_summary"][field] = 1
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(tampered)
    tampered["result_id"] = result_id
    tampered["idempotency_key"] = idempotency_key

    with pytest.raises(CreativeCodePatchContractError, match=message):
        validate_creative_code_patch_result(tampered)


@pytest.mark.parametrize(
    ("attempts", "mutated_path_count", "oracle_commands_executed"),
    [(0, 0, 0), (1, 1, 1)],
)
def test_patch_result_accepts_coherent_capability_execution_evidence(
    attempts: int,
    mutated_path_count: int,
    oracle_commands_executed: int,
) -> None:
    result = _reference_result()
    result["status"] = "rejected"
    result["failure_class"] = "capability_mismatch"
    result["runner_summary"].update(
        {
            "status": "rejected",
            "failure_class": "capability_mismatch",
            "mutated_path_count": mutated_path_count,
            "oracle_commands_configured": 1,
            "oracle_commands_executed": oracle_commands_executed,
            "attempts": attempts,
            "retries_consumed": 0,
        }
    )
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(result)
    result["result_id"] = result_id
    result["idempotency_key"] = idempotency_key

    assert validate_creative_code_patch_result(result) == result


def test_patch_path_schemas_match_validator_for_forbidden_surfaces() -> None:
    request_schema = json.loads(REQUEST_SCHEMA.read_text(encoding="utf-8"))
    result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    request_pattern = re.compile(request_schema["$defs"]["repo_path"]["pattern"])
    result_pattern = re.compile(result_schema["$defs"]["repo_path"]["pattern"])
    forbidden_paths = [
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        ".github/workflows/ci.yml",
        ".mypy_cache/cache.json",
        ".pytest_cache/v/cache/nodeids",
        ".ruff_cache/cache",
        ".venv/bin/python",
        "artifacts/orchestration/result.json",
        "build/output.txt",
        "dist/package.whl",
        "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md",
        "docs/review/PR_2022_FIXED_MAPPING.md",
        "frontend/src/App.tsx",
        "ios/PulsePlate/App.swift",
        "node_modules/pkg/index.js",
        "scripts/ci/check.py",
        "tests/test_example.py",
        "worktrees/lane/file.py",
    ]
    allowed_path = "core/rag/orchestration.py"

    for path in forbidden_paths:
        assert not request_pattern.fullmatch(path), path
        assert not result_pattern.fullmatch(path), path
        request = _reference_request()
        request["allowed_existing_paths"] = [path]
        with pytest.raises(CreativeCodePatchContractError, match="forbidden patch surface"):
            validate_creative_code_patch_build_request(
                request,
                source_bundle=_reference_bundle(),
            )

    assert request_pattern.fullmatch(allowed_path)
    assert result_pattern.fullmatch(allowed_path)


def test_patch_request_allows_allowed_new_only_requests() -> None:
    request = build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha="a" * 40,
        approval_ref="PR-2-test-approval",
        allowed_existing_paths=[],
        allowed_new_paths=["core/rag/orchestration.py"],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=["candidate patch supports allowed-new-only requests"],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )

    validated = validate_creative_code_patch_build_request(
        request,
        source_bundle=_reference_bundle(),
    )

    assert validated["allowed_existing_paths"] == []
    assert validated["allowed_new_paths"] == ["core/rag/orchestration.py"]


def test_patch_request_rejects_duplicate_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "request.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(CreativeCodePatchContractError, match="duplicate JSON key"):
        read_creative_code_patch_build_request(str(duplicate))


def test_patch_request_requires_human_admission_and_bundle_fingerprint() -> None:
    request = _reference_request()
    bundle = _reference_bundle()
    request["source_bundle_fingerprint"] = "sha256:" + "0" * 64

    with pytest.raises(CreativeCodePatchContractError, match="source_bundle_fingerprint"):
        validate_creative_code_patch_build_request(request, source_bundle=bundle)

    request = _reference_request()
    admission = request["human_admission"]
    assert isinstance(admission, dict)
    admission["decision"] = "pending"

    with pytest.raises(CreativeCodePatchContractError, match="approved_for_sandbox_generation"):
        validate_creative_code_patch_build_request(request, source_bundle=bundle)


def test_patch_result_rejects_truthy_strings_and_invalid_runner_fingerprint() -> None:
    result = _reference_result()
    result["workspace_summary"]["origin_removed"] = "true"

    with pytest.raises(CreativeCodePatchContractError, match="origin_removed"):
        validate_creative_code_patch_result(result)

    result = _reference_result()
    result["runner_summary"]["runner_error_present"] = True
    result["runner_summary"]["runner_error_fingerprint"] = "raw runner error"

    with pytest.raises(CreativeCodePatchContractError, match="runner_error_fingerprint"):
        validate_creative_code_patch_result(result)


def test_executor_builds_fixed_argv_and_strips_secret_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout='{"ok": true}\n', stderr=""
        )

    monkeypatch.setattr(creative_code_patch_executor, "resolve_codex_binary", lambda: "/bin/codex")
    monkeypatch.setattr(creative_code_patch_executor.subprocess, "run", fake_run)
    openai_key_name = "OPENAI_" + "API_KEY"
    gh_token_name = "GH_" + "TOKEN"

    metadata = creative_code_patch_executor.run_codex_exec(
        checkout=checkout,
        prompt="build patch",
        timeout_seconds=5,
        env={
            "PATH": "/bin",
            "HOME": "/home/test",
            openai_key_name: "redacted",
            gh_token_name: "redacted",
            "CODEX_HOME": "/tmp/codex-home",
        },
    )

    argv = captured["args"][0]
    kwargs = captured["kwargs"]
    assert metadata["returncode"] == 0
    assert argv == [
        "/bin/codex",
        "exec",
        "--ignore-user-config",
        "-c",
        'approval_policy="never"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'web_search="disabled"',
        "-c",
        "apps._default.enabled=false",
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "--json",
        "--cd",
        str(checkout),
        "-",
    ]
    assert "build patch" not in argv
    assert kwargs["input"] == "build patch"
    assert "shell" not in kwargs
    assert openai_key_name not in kwargs["env"]
    assert gh_token_name not in kwargs["env"]
    assert "CODEX_HOME" not in kwargs["env"]


def test_executor_honors_explicitly_empty_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/home/parent")
    monkeypatch.setenv("PATH", "/bin")
    monkeypatch.setenv("OPENAI_API_KEY", "redacted")

    assert creative_code_patch_executor.sanitized_codex_env({}) == {"PATH": ""}


def test_binary_resolvers_return_absolute_executables_for_relative_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    codex = tools / "codex"
    git = tools / "git"
    codex.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    git.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "tools")

    assert creative_code_patch_executor.resolve_codex_binary() == str(codex.resolve())
    assert creative_code_patch_workspace.resolve_git_binary() == str(git.resolve())


def test_git_env_strips_secret_and_parent_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "tools")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LANG", "C.UTF-8")
    monkeypatch.setenv("GH_TOKEN", "redacted")
    monkeypatch.setenv("GITHUB_TOKEN", "redacted")
    monkeypatch.setenv("OPENAI_API_KEY", "redacted")
    monkeypatch.setenv("CODEX_HOME", "/tmp/codex")
    monkeypatch.setenv("PYTHONPATH", "/tmp/python")
    monkeypatch.setenv("DATABASE_URL", "postgres://example")
    monkeypatch.setenv("SESSION_COOKIE", "redacted")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/gitconfig")

    env = creative_code_patch_workspace.git_env_without_parent_state()

    assert env["HOME"] == str(tmp_path)
    assert env["LANG"] == "C.UTF-8"
    assert env["PATH"] == str(tools.resolve())
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    for forbidden in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "CODEX_HOME",
        "PYTHONPATH",
        "DATABASE_URL",
        "SESSION_COOKIE",
    ):
        assert forbidden not in env


def test_run_git_overrides_checkout_local_execution_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    marker = tmp_path / "external-diff-ran"
    helper = tmp_path / "external_diff.sh"
    helper.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n", encoding="utf-8")
    helper.chmod(0o755)
    _git(repo, "config", "diff.external", str(helper))
    _git(repo, "config", "core.fsmonitor", str(helper))
    _git(repo, "config", "core.hooksPath", str(tmp_path))
    (repo / "core" / "rag" / "orchestration.py").write_text(
        "def value() -> int:\n    return 2\n",
        encoding="utf-8",
    )

    diff = creative_code_patch_workspace.run_git(
        ["diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD"],
        cwd=repo,
    ).stdout

    assert "return 2" in diff
    assert not marker.exists()


def test_experiment_runner_uses_sanitized_git_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setenv("GH_TOKEN", "redacted")
    monkeypatch.setenv("GITHUB_TOKEN", "redacted")
    monkeypatch.setenv("OPENAI_API_KEY", "redacted")
    monkeypatch.setenv("CODEX_HOME", "/tmp/codex")
    monkeypatch.setenv("PYTHONPATH", "/tmp/python")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/unsafe-gitconfig")
    monkeypatch.setattr(experiment_runner, "_resolve_git_binary", lambda: "/usr/bin/git")
    monkeypatch.setattr(experiment_runner.subprocess, "run", fake_run)

    experiment_runner._run_git(["status", "--short"], cwd=repo)

    argv = captured["args"][0]
    assert argv[:2] == ["/usr/bin/git", "-c"]
    assert "diff.external=" in argv
    assert "core.fsmonitor=false" in argv
    assert f"core.hooksPath={os.devnull}" in argv
    env = captured["kwargs"]["env"]
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    for forbidden in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "CODEX_HOME",
        "PYTHONPATH",
    ):
        assert forbidden not in env


def test_workspace_creates_detached_no_remote_checkout_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("workspace-test", create=True)

    summary = creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir,
        base_commit_sha=base_sha,
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)

    assert summary["detached_base_sha"] == base_sha
    assert _git(checkout, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "HEAD"
    assert _git(checkout, "remote").stdout.strip() == ""
    assert creative_code_patch_workspace.destroy_generation_checkout(run_dir) is True
    creative_code_patch_workspace.cleanup_run_dir("workspace-test")
    assert not run_dir.exists()


def test_workspace_json_rejects_duplicate_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("duplicate-json", create=True)
    duplicate = run_dir / "state.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(
        creative_code_patch_workspace.CreativeCodePatchWorkspaceError,
        match="duplicate key",
    ):
        creative_code_patch_workspace.read_json(duplicate)


def test_workspace_json_write_rejects_paths_outside_creative_code_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)

    with pytest.raises(
        creative_code_patch_workspace.CreativeCodePatchWorkspaceError,
        match="creative-code artifacts",
    ):
        creative_code_patch_workspace.write_json_atomic(tmp_path / "outside.json", {})


def test_patch_metadata_accepts_allowed_modified_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    bundle = _reference_bundle()
    request = _request_for_base(base_sha)
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-accept", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    (checkout / "core" / "rag" / "orchestration.py").write_text(
        "def value() -> int:\n    return 2\n",
        encoding="utf-8",
    )

    metadata = creative_code_patch_builder._patch_metadata(
        checkout=checkout,
        run_dir=run_dir,
        request=request,
        bundle=bundle,
    )

    assert metadata["changed_paths"] == ["core/rag/orchestration.py"]
    assert metadata["patch_fingerprint"].startswith("sha256:")
    assert (run_dir / "candidate.patch").is_file()


def test_patch_metadata_ignores_candidate_local_external_diff_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    bundle = _reference_bundle()
    request = _request_for_base(base_sha)
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-no-ext-diff", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    marker = tmp_path / "candidate-external-diff-ran"
    helper = tmp_path / "candidate_external_diff.sh"
    helper.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n", encoding="utf-8")
    helper.chmod(0o755)
    _git(checkout, "config", "diff.external", str(helper))
    _git(checkout, "config", "core.fsmonitor", str(helper))
    _git(checkout, "config", "core.hooksPath", str(tmp_path))
    (checkout / "core" / "rag" / "orchestration.py").write_text(
        "def value() -> int:\n    return 2\n",
        encoding="utf-8",
    )

    metadata = creative_code_patch_builder._patch_metadata(
        checkout=checkout,
        run_dir=run_dir,
        request=request,
        bundle=bundle,
    )

    assert metadata["changed_paths"] == ["core/rag/orchestration.py"]
    assert not marker.exists()


def test_patch_metadata_rejects_unapproved_untracked_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    request = _request_for_base(base_sha)
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-untracked", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    (checkout / "core" / "rag" / "extra.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(CreativeCodePatchBuilderError, match="untracked path is not allowed"):
        creative_code_patch_builder._patch_metadata(
            checkout=checkout,
            run_dir=run_dir,
            request=request,
            bundle=_reference_bundle(),
        )


def test_patch_metadata_rejects_symlink_mode_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    request = _request_for_base(base_sha)
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-symlink", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    target = checkout / "core" / "rag" / "orchestration.py"
    target.unlink()
    target.symlink_to("target.py")

    with pytest.raises(CreativeCodePatchBuilderError, match="forbidden"):
        creative_code_patch_builder._patch_metadata(
            checkout=checkout,
            run_dir=run_dir,
            request=request,
            bundle=_reference_bundle(),
        )


def test_patch_metadata_rejects_new_executable_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path, include_target_file=False)
    _patch_modules_to_repo(monkeypatch, repo)
    request = build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha=base_sha,
        approval_ref="PR-2-test-approval",
        allowed_existing_paths=[],
        allowed_new_paths=["core/rag/orchestration.py"],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=["candidate patch rejects executable new files"],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-executable", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    target = checkout / "core" / "rag" / "orchestration.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/usr/bin/env python3\nprint('x')\n", encoding="utf-8")
    target.chmod(0o755)

    with pytest.raises(CreativeCodePatchBuilderError, match="forbidden mode"):
        creative_code_patch_builder._patch_metadata(
            checkout=checkout,
            run_dir=run_dir,
            request=request,
            bundle=_reference_bundle(),
        )


def test_evaluate_writes_sanitized_result_without_runner_leaks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("eval-sanitize", create=True)
    request = _request_for_base(base_sha)
    state = {
        "run_id": "eval-sanitize",
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": base_sha,
        "workspace": {"origin_removed": True},
        "candidate_patch_generated": True,
        "checkout_destroyed": True,
    }
    patch_text = "diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py\n"
    metadata = {
        "changed_paths": ["core/rag/orchestration.py"],
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    creative_code_patch_workspace.write_json_atomic(run_dir / "request.json", request)
    creative_code_patch_workspace.write_json_atomic(
        run_dir / "source_bundle.json", _reference_bundle()
    )
    creative_code_patch_workspace.write_json_atomic(run_dir / "state.json", state)
    creative_code_patch_workspace.write_json_atomic(run_dir / "patch_metadata.json", metadata)
    (run_dir / "candidate.patch").write_text(patch_text, encoding="utf-8")

    def fake_evaluate_candidate(
        packet: dict[str, Any], candidate_patch_path: Path
    ) -> dict[str, Any]:
        return {
            "experiment_id": packet["experiment_id"],
            "runner_mode": "candidate_patch",
            "candidate_patch": str(candidate_patch_path),
            "status": "rejected",
            "failure_class": "guard_failure",
            "mutated_paths": ["core/rag/orchestration.py"],
            "oracle_results": [
                {
                    "command": "pytest -q tests/test_creative_code_patch_builder.py",
                    "returncode": 1,
                    "timed_out": False,
                    "truncated": False,
                    "stdout": "/Users/example/raw output sk-secretsecretsecret",
                    "stderr": "diff --git leak",
                    "cwd": "/Users/example/checkout",
                }
            ],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
                "runner_error": "/Users/example/ghp_secretsecretsecret",
            },
            "shared_tree_untouched": True,
        }

    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fake_evaluate_candidate)

    result = creative_code_patch_builder.evaluate(run_id="eval-sanitize")
    encoded = json.dumps(result, sort_keys=True)

    assert result["status"] == "rejected"
    assert result["runner_summary"]["runner_error_present"] is True
    assert "/Users/example" not in encoded
    assert "sk-secret" not in encoded
    assert "diff --git leak" not in encoded


def test_evaluate_supplies_cv_context_for_cv_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _ = _init_patch_repo(tmp_path, include_target_file=False)
    (repo / "docs" / "prompts" / "cv").mkdir(parents=True)
    (repo / "docs" / "prompts" / "cv" / "program.md").write_text(
        "# CV Offline Evaluation Program\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "add cv program")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", base_sha)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "eval-cv-context"
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=True)
    bundle = _cv_reference_bundle()
    request = build_creative_code_patch_build_request(
        source_bundle=bundle,
        base_commit_sha=base_sha,
        approval_ref="PR-2-test-approval",
        allowed_existing_paths=["docs/prompts/cv/program.md"],
        allowed_new_paths=[],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=["candidate patch preserves offline CV governance"],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 1,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )
    state = {
        "run_id": run_id,
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": base_sha,
        "workspace": {"origin_removed": True},
        "candidate_patch_generated": True,
        "checkout_destroyed": True,
    }
    patch_text = (
        "diff --git a/docs/prompts/cv/program.md b/docs/prompts/cv/program.md\n"
        "index e69de29..4b825dc 100644\n"
        "--- a/docs/prompts/cv/program.md\n"
        "+++ b/docs/prompts/cv/program.md\n"
        "@@ -1 +1,2 @@\n"
        " # CV Offline Evaluation Program\n"
        "+Offline evaluation remains documentation-only.\n"
    )
    metadata = {
        "changed_paths": ["docs/prompts/cv/program.md"],
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    creative_code_patch_workspace.write_json_atomic(run_dir / "request.json", request)
    creative_code_patch_workspace.write_json_atomic(run_dir / "source_bundle.json", bundle)
    creative_code_patch_workspace.write_json_atomic(run_dir / "state.json", state)
    creative_code_patch_workspace.write_json_atomic(run_dir / "patch_metadata.json", metadata)
    (run_dir / "candidate.patch").write_text(patch_text, encoding="utf-8")

    def fake_evaluate_candidate(
        packet: dict[str, Any], candidate_patch_path: Path
    ) -> dict[str, Any]:
        assert validate_cv_context(packet["cv_context"]) == packet["cv_context"]
        assert packet["cv_context"]["privacy_packet"]["raw_image_retention"] == "forbidden"
        return {
            "experiment_id": packet["experiment_id"],
            "runner_mode": "candidate_patch",
            "candidate_patch": str(candidate_patch_path),
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["docs/prompts/cv/program.md"],
            "oracle_results": [{"returncode": 0, "timed_out": False, "truncated": False}],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
            },
            "shared_tree_untouched": True,
        }

    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fake_evaluate_candidate)

    result = creative_code_patch_builder.evaluate(run_id=run_id)

    assert result["status"] == "accepted"
    packet = json.loads((run_dir / "experiment_packet.json").read_text(encoding="utf-8"))
    assert packet["cv_context"]["dataset"]["id"] == (
        "creative-research-cv-program-offline-eval-001"
    )
    assert packet["cv_context"]["uncertainty_band_policy"]["bands"] == [
        "high",
        "medium",
        "low",
        "unknown",
    ]


def test_evaluate_fallback_stores_error_class_not_raw_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("eval-error-class", create=True)
    request = _request_for_base(base_sha)
    state = {
        "run_id": "eval-error-class",
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": base_sha,
        "workspace": {"origin_removed": True},
        "candidate_patch_generated": True,
        "checkout_destroyed": True,
    }
    patch_text = "diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py\n"
    metadata = {
        "changed_paths": ["core/rag/orchestration.py"],
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    creative_code_patch_workspace.write_json_atomic(run_dir / "request.json", request)
    creative_code_patch_workspace.write_json_atomic(
        run_dir / "source_bundle.json", _reference_bundle()
    )
    creative_code_patch_workspace.write_json_atomic(run_dir / "state.json", state)
    creative_code_patch_workspace.write_json_atomic(run_dir / "patch_metadata.json", metadata)
    (run_dir / "candidate.patch").write_text(patch_text, encoding="utf-8")

    def fake_evaluate_candidate(
        packet: dict[str, Any], candidate_patch_path: Path
    ) -> dict[str, Any]:
        raise RuntimeError("/Users/example/ghp_secretsecretsecret")

    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fake_evaluate_candidate)

    result = creative_code_patch_builder.evaluate(run_id="eval-error-class")
    encoded = json.dumps(result, sort_keys=True)

    assert result["status"] == "rejected"
    assert result["failure_class"] == "infra_flake"
    assert result["runner_summary"]["runner_error_present"] is True
    assert "/Users/example" not in encoded
    assert "ghp_secret" not in encoded


def test_evaluate_capability_signal_fails_closed_without_result_or_cli_leak(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "eval-capability-signal"
    run_dir = _write_generated_run(run_id=run_id, base_sha=base_sha)
    canary = "/Users/example/ghp_capability_canary"

    def raise_capability_signal(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise experiment_runner.RunnerCapabilitySignal(canary)

    monkeypatch.setattr(
        creative_code_patch_builder,
        "evaluate_candidate",
        raise_capability_signal,
    )

    with pytest.raises(
        CreativeCodePatchBuilderError,
        match="^Experiment Runner capability unavailable; trusted dispatch is required\\.$",
    ) as exc_info:
        creative_code_patch_builder.evaluate(run_id=run_id)

    assert exc_info.value.__cause__ is None
    assert canary not in str(exc_info.value)
    assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()
    state = json.loads((run_dir / creative_code_patch_builder.STATE_FILE).read_text())
    assert state.get("candidate_patch_evaluated") is not True

    assert creative_code_patch_builder.main(["evaluate", "--run-dir", run_id]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "FAIL: Experiment Runner capability unavailable; trusted dispatch is required.\n"
    )
    assert canary not in captured.err
    assert "Traceback" not in captured.err
    assert not (run_dir / creative_code_patch_builder.RESULT_FILE).exists()
    state = json.loads((run_dir / creative_code_patch_builder.STATE_FILE).read_text())
    assert state.get("candidate_patch_evaluated") is not True


def test_evaluate_rejects_tampered_candidate_patch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("eval-tamper", create=True)
    request = _request_for_base(base_sha)
    original_patch = "diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py\n"
    metadata = {
        "changed_paths": ["core/rag/orchestration.py"],
        "patch_fingerprint": fingerprint_payload({"candidate_patch": original_patch}),
        "patch_bytes": len(original_patch.encode("utf-8")),
        "diff_lines": len(original_patch.splitlines()),
    }
    state = {
        "run_id": "eval-tamper",
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": base_sha,
        "workspace": {"origin_removed": True},
        "candidate_patch_generated": True,
        "checkout_destroyed": True,
    }
    creative_code_patch_workspace.write_json_atomic(run_dir / "request.json", request)
    creative_code_patch_workspace.write_json_atomic(
        run_dir / "source_bundle.json", _reference_bundle()
    )
    creative_code_patch_workspace.write_json_atomic(run_dir / "state.json", state)
    creative_code_patch_workspace.write_json_atomic(run_dir / "patch_metadata.json", metadata)
    (run_dir / "candidate.patch").write_text(original_patch + "# tampered\n", encoding="utf-8")

    def fail_if_called(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("evaluate_candidate must not run for tampered patches")

    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fail_if_called)

    with pytest.raises(CreativeCodePatchBuilderError, match="metadata does not match"):
        creative_code_patch_builder.evaluate(run_id="eval-tamper")


def test_prepare_rejects_non_empty_run_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "prepare-stale"
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=True)
    (run_dir / "candidate.patch").write_text("stale\n", encoding="utf-8")
    request = _request_for_base(base_sha)
    bundle_path = tmp_path / "bundle.json"
    request_path = tmp_path / "request.json"
    bundle_path.write_text(json.dumps(_reference_bundle()), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")

    with pytest.raises(CreativeCodePatchBuilderError, match="run directory must be empty"):
        creative_code_patch_builder.prepare(
            spec_bundle_path=bundle_path,
            request_path=request_path,
            run_id=run_id,
        )


def test_cli_prepare_generate_evaluate_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "cli-roundtrip"
    request = _request_for_base(base_sha)
    bundle_path = tmp_path / "bundle.json"
    request_path = tmp_path / "request.json"
    bundle_path.write_text(json.dumps(_reference_bundle()), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")

    def fake_run_codex_exec(
        *,
        checkout: Path,
        prompt: str,
        timeout_seconds: int,
    ) -> dict[str, int]:
        assert "local candidate patch" in prompt
        assert timeout_seconds == request["budgets"]["generation_timeout_seconds"]
        (checkout / "core" / "rag" / "orchestration.py").write_text(
            "def value() -> int:\n    return 3\n",
            encoding="utf-8",
        )
        return {"returncode": 0, "stdout_lines": 1, "stderr_lines": 0}

    def fake_evaluate_candidate(
        packet: dict[str, Any], candidate_patch_path: Path
    ) -> dict[str, Any]:
        assert packet["runner_mode"] == "candidate_patch"
        assert candidate_patch_path.name == "candidate.patch"
        return {
            "experiment_id": packet["experiment_id"],
            "runner_mode": "candidate_patch",
            "candidate_patch": str(candidate_patch_path),
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["core/rag/orchestration.py"],
            "oracle_results": [{"returncode": 0, "timed_out": False, "truncated": False}],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
            },
            "shared_tree_untouched": True,
        }

    monkeypatch.setattr(creative_code_patch_builder, "run_codex_exec", fake_run_codex_exec)
    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fake_evaluate_candidate)

    assert (
        creative_code_patch_builder.main(
            [
                "prepare",
                "--spec-bundle",
                str(bundle_path),
                "--request",
                str(request_path),
                "--run-dir",
                run_id,
            ]
        )
        == 0
    )
    assert creative_code_patch_builder.main(["generate", "--run-dir", run_id]) == 0
    assert creative_code_patch_builder.main(["evaluate", "--run-dir", run_id]) == 0
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id)
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "accepted"
    assert result["authority"]["open_pull_request"] is False
    assert creative_code_patch_builder.main(["cleanup", "--run-dir", run_id]) == 0
    assert not run_dir.exists()

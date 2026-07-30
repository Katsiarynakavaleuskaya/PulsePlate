from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_patch_contract, creative_code_telemetry
from scripts.orchestration.creative_code_patch_contract import (
    build_creative_code_patch_build_request,
    build_creative_code_patch_result,
)
from scripts.orchestration.creative_code_pr_promotion_contract import (
    build_creative_code_pr_promotion_approval,
    build_creative_code_pr_promotion_plan,
    build_creative_code_pr_promotion_receipt,
    build_creative_code_pr_promotion_validation,
    promotion_plan_fingerprint,
)
from scripts.orchestration.creative_code_specification import (
    read_creative_code_specification_bundle,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    CreativeCodeTelemetryContractError,
    build_creative_code_rejection_taxonomy,
    build_creative_code_telemetry_rollup_v2,
    build_creative_code_terminal_telemetry_event,
    build_creative_code_telemetry_event,
    build_creative_code_telemetry_rollup,
    default_cost_metadata,
    default_metrics,
    read_json_object,
    validate_creative_code_rejection_taxonomy,
    validate_creative_code_telemetry_event_any,
    validate_creative_code_telemetry_rollup_any,
)
from scripts.orchestration.creative_code_terminal_outcome_contract import (
    build_creative_code_terminal_outcome,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_FILE = creative_code_telemetry.PLAN_FILE
VALIDATION_FILE = creative_code_telemetry.VALIDATION_FILE
APPROVAL_FILE = creative_code_telemetry.APPROVAL_FILE
RECEIPT_FILE = creative_code_telemetry.RECEIPT_FILE
REFERENCE_BUNDLE = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.json"
EVENT_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_telemetry_event.v1.schema.json"
)
ROLLUP_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_telemetry_rollup.v1.schema.json"
)
EVENT_V2_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_telemetry_event.v2.schema.json"
)
ROLLUP_V2_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_telemetry_rollup.v2.schema.json"
)
TAXONOMY_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_rejection_taxonomy.v1.schema.json"
)
REFERENCE_TAXONOMY = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_rejection_taxonomy.v1.json"
)


def _reference_bundle() -> dict[str, Any]:
    return read_creative_code_specification_bundle(REFERENCE_BUNDLE)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _configure_artifact_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    root = repo / "artifacts" / "orchestration" / "creative_code"
    spec_runs = root / "spec_runs"
    patch_runs = root / "patch_runs"
    promotions = root / "promotions"
    telemetry = root / "telemetry"
    monkeypatch.setattr(creative_code_telemetry, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_telemetry, "CREATIVE_CODE_ROOT", root)
    monkeypatch.setattr(creative_code_telemetry, "SPEC_RUNS_DIR", spec_runs)
    monkeypatch.setattr(creative_code_telemetry, "PATCH_RUNS_DIR", patch_runs)
    monkeypatch.setattr(creative_code_telemetry, "PROMOTIONS_DIR", promotions)
    monkeypatch.setattr(creative_code_telemetry, "TELEMETRY_ROOT", telemetry)
    return root, spec_runs, patch_runs, promotions, telemetry


def _reference_request(base_sha: str) -> dict[str, Any]:
    return build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha=base_sha,
        approval_ref="PR-4-test-approval",
        allowed_existing_paths=["core/rag/orchestration.py"],
        allowed_new_paths=[],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=["candidate patch remains measurable without raw patch capture"],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )


def _reference_patch_result(
    *,
    accepted: bool = True,
    rejection_failure_class: str = "guard_failure",
) -> dict[str, Any]:
    request = _reference_request("a" * 40)
    patch_text = """diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py
index 8f11111..8f22222 100644
--- a/core/rag/orchestration.py
+++ b/core/rag/orchestration.py
@@ -1,2 +1,2 @@
 def value() -> int:
-    return 1
+    return 2
"""
    pre_oracle_rejection = not accepted and rejection_failure_class in {
        "capability_mismatch",
        "policy_violation",
    }
    runner_result = {
        "experiment_id": "exp-pr4-telemetry",
        "status": "accepted" if accepted else "rejected",
        "failure_class": None if accepted else rejection_failure_class,
        "mutated_paths": [] if pre_oracle_rejection else ["core/rag/orchestration.py"],
        "budget_observations": {
            "oracle_commands_configured": 1,
            "attempts": 1,
            "retries_consumed": 0,
        },
        "oracle_results": [{"status": "passed"}] if accepted else [],
        "shared_tree_untouched": True,
    }
    return build_creative_code_patch_result(
        request=request,
        changed_paths=["core/rag/orchestration.py"],
        patch_fingerprint=fingerprint_payload({"candidate_patch": patch_text}),
        patch_bytes=len(patch_text.encode("utf-8")),
        diff_lines=len(patch_text.splitlines()),
        runner_result=runner_result,
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
        failure_class=None if accepted else rejection_failure_class,
    )


def _promotion_artifacts(
    result: dict[str, Any],
    *,
    partial_failure: str | None = None,
) -> dict[str, dict[str, Any]]:
    promotion_id = "pr4-telemetry-test"
    target_branch = "experiment/pr4-telemetry-test"
    patch_fingerprint = result["patch_summary"]["patch_fingerprint"]
    plan = build_creative_code_pr_promotion_plan(
        promotion_id=promotion_id,
        source_result_id=result["result_id"],
        source_request_id=result["request_id"],
        source_bundle_id=result["source_bundle_id"],
        source_bundle_fingerprint=result["source_bundle_fingerprint"],
        selected_variant_id=result["selected_variant_id"],
        selected_variant_fingerprint=result["selected_variant_fingerprint"],
        patch_fingerprint=patch_fingerprint,
        base_commit_sha=result["base_commit_sha"],
        changed_paths=result["changed_paths"],
        target_head_branch=target_branch,
        pull_request_title="feat(orchestration): add creative-code telemetry test",
        pull_request_body_fingerprint=fingerprint_payload({"body": "safe promotion body"}),
    )
    plan_fingerprint = promotion_plan_fingerprint(plan)
    validation = build_creative_code_pr_promotion_validation(
        promotion_id=promotion_id,
        plan_fingerprint=plan_fingerprint,
        patch_fingerprint=patch_fingerprint,
        base_commit_sha=result["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
        oracle_evidence_source="direct_evaluation",
        oracle_executed_during_validation=True,
        oracle_result_fingerprint=fingerprint_payload({"result": "telemetry-test"}),
        experiment_packet_fingerprint=fingerprint_payload({"packet": "telemetry-test"}),
        generation_gate_fingerprint=None,
        generation_receipt_fingerprint=None,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id=promotion_id,
        plan_fingerprint=plan_fingerprint,
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=patch_fingerprint,
        confirmed_base_commit_sha=result["base_commit_sha"],
        confirmed_target_branch=target_branch,
    )
    receipt = build_creative_code_pr_promotion_receipt(
        promotion_id=promotion_id,
        plan_fingerprint=plan_fingerprint,
        validation_fingerprint=validation["validation_fingerprint"],
        approval_id=approval["approval_id"],
        source_result_id=result["result_id"],
        patch_fingerprint=patch_fingerprint,
        head_branch=target_branch,
        commit_sha="b" * 40,
        pull_request_number=2040,
        pull_request_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2040",
        approved_by_login="Katsiarynakavaleuskaya",
        partial_failure=partial_failure,
    )
    return {
        PLAN_FILE: plan,
        VALIDATION_FILE: validation,
        APPROVAL_FILE: approval,
        RECEIPT_FILE: receipt,
    }


def test_reference_taxonomy_and_schemas_are_closed() -> None:
    event_schema = json.loads(EVENT_SCHEMA.read_text(encoding="utf-8"))
    rollup_schema = json.loads(ROLLUP_SCHEMA.read_text(encoding="utf-8"))
    taxonomy_schema = json.loads(TAXONOMY_SCHEMA.read_text(encoding="utf-8"))
    reference_taxonomy = read_json_object(REFERENCE_TAXONOMY)

    assert validate_creative_code_rejection_taxonomy(reference_taxonomy) == (
        build_creative_code_rejection_taxonomy()
    )
    assert event_schema["additionalProperties"] is False
    assert rollup_schema["additionalProperties"] is False
    assert taxonomy_schema["additionalProperties"] is False
    assert event_schema["$defs"]["authority"]["additionalProperties"] is False
    assert event_schema["$defs"]["metrics"]["additionalProperties"] is False
    assert rollup_schema["$defs"]["funnel"]["additionalProperties"] is False
    assert taxonomy_schema["$defs"]["taxonomy_class"]["additionalProperties"] is False
    assert "github_transport_failed" in event_schema["$defs"]["taxonomy_code"]["enum"]
    assert taxonomy_schema["properties"]["classes"]["const"] == reference_taxonomy["classes"]
    taxonomy_codes = {row["code"] for row in reference_taxonomy["classes"]}
    assert (
        set(rollup_schema["$defs"]["taxonomy_count_map"]["propertyNames"]["enum"]) == taxonomy_codes
    )
    assert rollup_schema["properties"]["rejections_by_class"]["$ref"].endswith("taxonomy_count_map")
    assert rollup_schema["properties"]["events_by_stage"]["$ref"].endswith("stage_count_map")
    assert rollup_schema["properties"]["events_by_status"]["$ref"].endswith("status_count_map")
    unsafe_text_pattern = re.compile(
        event_schema["$defs"]["safe_id"]["not"]["pattern"],
        re.IGNORECASE,
    )
    rollup_unsafe_text_pattern = re.compile(
        rollup_schema["$defs"]["safe_id"]["not"]["pattern"],
        re.IGNORECASE,
    )
    assert unsafe_text_pattern.search("/Users/example/repo")
    for unsafe_token in (
        "oracle_stdout",
        "oracle-stderr",
        "provider_payload",
        "GITHUB_TOKEN",
        "worktrees:creative-code",
    ):
        assert unsafe_text_pattern.search(unsafe_token)
        assert rollup_unsafe_text_pattern.search(unsafe_token)


def test_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"GITHUB_TOKEN":"first","GITHUB_TOKEN":"second"}',
        encoding="utf-8",
    )

    with pytest.raises(CreativeCodeTelemetryContractError, match="duplicate key") as error:
        read_json_object(duplicate)
    assert "GITHUB_TOKEN" not in str(error.value)

    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    event["GITHUB_TOKEN"] = "untrusted"
    with pytest.raises(
        CreativeCodeTelemetryContractError,
        match="unsupported fields",
    ) as error:
        validate_creative_code_telemetry_event_any(event)
    assert "GITHUB_TOKEN" not in str(error.value)


def test_event_rejects_raw_patch_leaks_and_mutating_authority() -> None:
    source_fingerprint = "sha256:" + ("a" * 64)

    for unsafe_source_artifact_id in (
        "candidate.patch",
        "oracle_stdout",
        "oracle-stderr",
        "provider_payload",
        "GITHUB_TOKEN",
        "worktrees:creative-code",
    ):
        with pytest.raises(CreativeCodeTelemetryContractError, match="unsafe telemetry text"):
            build_creative_code_telemetry_event(
                lane_stage="specification",
                source_artifact_type="creative_code_specification",
                source_artifact_id=unsafe_source_artifact_id,
                source_fingerprint=source_fingerprint,
                candidate_ids={
                    "source_packet_id": None,
                    "source_bundle_id": None,
                    "selected_variant_id": None,
                    "request_id": None,
                    "result_id": None,
                    "promotion_id": None,
                },
                status="blocked",
                rejection_class="leak_detected",
                failure_class="leak_detected",
                taxonomy_codes=["leak_detected"],
                metrics=default_metrics(),
            )

    event = build_creative_code_telemetry_event(
        lane_stage="specification",
        source_artifact_type="creative_code_specification",
        source_artifact_id="source-bundle",
        source_fingerprint=source_fingerprint,
        candidate_ids={
            "source_packet_id": None,
            "source_bundle_id": None,
            "selected_variant_id": None,
            "request_id": None,
            "result_id": None,
            "promotion_id": None,
        },
        status="accepted",
        metrics=default_metrics(),
    )
    event["authority"]["opens_pr"] = True

    with pytest.raises(CreativeCodeTelemetryContractError, match="authority.opens_pr"):
        build_creative_code_telemetry_rollup([event], input_roots=["spec_runs"])


def test_collect_events_and_rollup_counts_are_deterministic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, spec_runs, patch_runs, promotions, _ = _configure_artifact_roots(monkeypatch, tmp_path)
    patch_result = _reference_patch_result()
    _write_json(spec_runs / "run-a" / "bundle.json", _reference_bundle())
    _write_json(patch_runs / "run-a" / "result.json", patch_result)
    for filename, payload in _promotion_artifacts(patch_result).items():
        _write_json(promotions / "promotion-a" / filename, payload)

    first = creative_code_telemetry.collect_events(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
    )
    second = creative_code_telemetry.collect_events(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
    )
    rollup = build_creative_code_telemetry_rollup(
        first,
        input_roots=["spec_runs", "patch_runs", "promotions"],
    )

    assert first == second
    assert rollup["event_count"] == 6
    assert rollup["funnel"]["specification_bundles"] == 1
    assert rollup["funnel"]["patch_results_accepted"] == 1
    assert rollup["funnel"]["promotion_plans"] == 1
    assert rollup["funnel"]["promotion_validations_passed"] == 1
    assert rollup["funnel"]["promotion_approvals"] == 1
    assert rollup["funnel"]["pull_requests_opened"] == 1
    assert rollup["rates"]["promotion_rate_bps"] == 10000
    assert Counter(event["lane_stage"] for event in first) == {
        "specification": 1,
        "patch_evaluation": 1,
        "promotion_plan": 1,
        "promotion_validation": 1,
        "promotion_approval": 1,
        "pr_open": 1,
    }


def test_capability_mismatch_telemetry_preserves_non_retryable_class(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, spec_runs, patch_runs, promotions, _ = _configure_artifact_roots(
        monkeypatch,
        tmp_path,
    )
    patch_result = _reference_patch_result(
        accepted=False,
        rejection_failure_class="capability_mismatch",
    )
    _write_json(patch_runs / "run-capability-mismatch" / "result.json", patch_result)

    events = creative_code_telemetry.collect_events(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
    )
    event = events[0]
    taxonomy = build_creative_code_rejection_taxonomy()
    taxonomy_row = next(row for row in taxonomy["classes"] if row["code"] == "capability_mismatch")

    assert len(events) == 1
    assert patch_result["changed_paths"] == ["core/rag/orchestration.py"]
    assert patch_result["runner_summary"]["mutated_path_count"] == 0
    assert patch_result["runner_summary"]["oracle_commands_executed"] == 0
    assert event["lane_stage"] == "patch_evaluation"
    assert event["status"] == "rejected"
    assert event["rejection_class"] == "capability_mismatch"
    assert event["failure_class"] == "capability_mismatch"
    assert event["taxonomy_codes"] == ["capability_mismatch"]
    assert taxonomy_row == {
        "code": "capability_mismatch",
        "stage": "patch_evaluation",
        "severity": "medium",
        "retryability": "not_retryable",
        "likely_owner": "dev-operator",
    }


def test_telemetry_rejects_mismatched_result_and_runner_failures() -> None:
    patch_result = _reference_patch_result(
        accepted=False,
        rejection_failure_class="capability_mismatch",
    )
    patch_result["runner_summary"]["failure_class"] = "infra_flake"
    result_id, idempotency_key = creative_code_patch_contract._build_result_identity(patch_result)
    patch_result["result_id"] = result_id
    patch_result["idempotency_key"] = idempotency_key

    with pytest.raises(
        creative_code_patch_contract.CreativeCodePatchContractError,
        match="rejected result and runner summary failure_class values must match",
    ):
        creative_code_telemetry.event_from_patch_result(patch_result)


def test_collect_and_write_outputs_local_only_sanitized_sidecars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, spec_runs, patch_runs, promotions, telemetry_root = _configure_artifact_roots(
        monkeypatch,
        tmp_path,
    )
    patch_result = _reference_patch_result()
    _write_json(spec_runs / "run-a" / "bundle.json", _reference_bundle())
    _write_json(patch_runs / "run-a" / "result.json", patch_result)
    for filename, payload in _promotion_artifacts(patch_result).items():
        _write_json(promotions / "promotion-a" / filename, payload)

    rollup = creative_code_telemetry.collect_and_write(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
        output_dir=telemetry_root,
    )
    emitted = "\n".join(
        (telemetry_root / filename).read_text(encoding="utf-8")
        for filename in (
            creative_code_telemetry.EVENTS_FILE,
            creative_code_telemetry.ROLLUP_FILE,
            creative_code_telemetry.SUMMARY_FILE,
            creative_code_telemetry.TAXONOMY_FILE,
        )
    )

    assert rollup["event_count"] == 6
    assert "diff --git" not in emitted
    assert "candidate.patch" not in emitted
    assert "raw_prompt" not in emitted
    assert "provider_payload" not in emitted
    assert "/Users/" not in emitted
    assert str(tmp_path) not in emitted
    assert "ghp_" not in emitted
    assert "not merge-readiness evidence" in emitted.lower()


def test_telemetry_import_does_not_load_promotion_runtime_module() -> None:
    probe = """
import json
import sys

from scripts.orchestration import creative_code_telemetry

runtime_module = "scripts.orchestration.creative_code_pr_promotion"
print(json.dumps({"promotion_runtime_loaded": runtime_module in sys.modules}))
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    stdout_tail = result.stdout[-1000:]
    stderr_tail = result.stderr[-2000:]
    assert result.returncode == 0, (
        "fresh telemetry import probe failed "
        f"returncode={result.returncode}\nstdout:\n{stdout_tail}\nstderr:\n{stderr_tail}"
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            "fresh telemetry import probe emitted malformed JSON "
            f"stdout:\n{stdout_tail}\nstderr:\n{stderr_tail}"
        ) from exc
    assert payload == {"promotion_runtime_loaded": False}, (
        "creative_code_telemetry import loaded promotion runtime module "
        f"in a fresh interpreter payload={payload!r}\n"
        f"stdout:\n{stdout_tail}\nstderr:\n{stderr_tail}"
    )


def test_cli_accepts_repo_relative_artifact_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, spec_runs, patch_runs, promotions, telemetry_root = _configure_artifact_roots(
        monkeypatch,
        tmp_path,
    )
    patch_result = _reference_patch_result()
    _write_json(spec_runs / "run-a" / "bundle.json", _reference_bundle())
    _write_json(patch_runs / "run-a" / "result.json", patch_result)
    for filename, payload in _promotion_artifacts(patch_result).items():
        _write_json(promotions / "promotion-a" / filename, payload)

    exit_code = creative_code_telemetry.main(
        [
            "--spec-runs-dir",
            "artifacts/orchestration/creative_code/spec_runs",
            "--patch-runs-dir",
            "artifacts/orchestration/creative_code/patch_runs",
            "--promotions-dir",
            "artifacts/orchestration/creative_code/promotions",
            "--output-dir",
            "artifacts/orchestration/creative_code/telemetry",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == creative_code_telemetry.SUCCESS_OUTPUT
    assert captured.err == ""
    assert (telemetry_root / creative_code_telemetry.ROLLUP_FILE).is_file()
    assert not (root / "telemetry" / "artifacts").exists()


def test_promotion_receipt_readback_failure_uses_specific_taxonomy() -> None:
    receipt = _promotion_artifacts(
        _reference_patch_result(),
        partial_failure="created PR failed non-draft readback verification",
    )[RECEIPT_FILE]

    event = creative_code_telemetry.event_from_promotion_receipt(receipt)

    assert event["status"] == "blocked"
    assert event["rejection_class"] == "pr_readback_failed"
    assert event["failure_class"] == "pr_readback_failed"
    assert event["taxonomy_codes"] == ["pr_readback_failed"]
    assert event["metrics"]["pull_requests_opened"] == 0


def test_malformed_patch_artifact_becomes_safe_error_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, spec_runs, patch_runs, promotions, _ = _configure_artifact_roots(monkeypatch, tmp_path)
    (spec_runs / "empty").mkdir(parents=True)
    (promotions / "empty").mkdir(parents=True)
    bad_result = patch_runs / "bad-run" / "result.json"
    bad_result.parent.mkdir(parents=True)
    bad_result.write_text('{"result_type":"x","result_type":"y"}', encoding="utf-8")

    events = creative_code_telemetry.collect_events(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
    )

    assert len(events) == 1
    event = events[0]
    assert event["lane_stage"] == "artifact_read_error"
    assert event["source_artifact_type"] == "creative_code_artifact_read_error"
    assert event["source_artifact_id"].startswith("read-error:")
    assert event["failure_class"] == "malformed_artifact"
    assert event["taxonomy_codes"] == ["malformed_artifact"]
    assert str(bad_result) not in json.dumps(event, sort_keys=True)


def test_malformed_artifacts_with_same_basename_keep_distinct_identities(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, spec_runs, patch_runs, promotions, _ = _configure_artifact_roots(monkeypatch, tmp_path)
    (spec_runs / "empty").mkdir(parents=True)
    (promotions / "empty").mkdir(parents=True)
    for run_id in ("run-a", "run-b"):
        bad_result = patch_runs / run_id / "result.json"
        bad_result.parent.mkdir(parents=True)
        bad_result.write_text('{"result_type":"x","result_type":"y"}', encoding="utf-8")

    events = creative_code_telemetry.collect_events(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
    )
    rollup = build_creative_code_telemetry_rollup(events, input_roots=["patch_runs"])

    assert len(events) == 2
    assert len({event["event_id"] for event in events}) == 2
    assert len({event["source_artifact_id"] for event in events}) == 2
    assert len({event["source_fingerprint"] for event in events}) == 2
    assert rollup["event_count"] == 2
    assert len(rollup["source_artifacts"]) == 2
    emitted = json.dumps({"events": events, "rollup": rollup}, sort_keys=True)
    assert str(tmp_path) not in emitted
    assert "/Users/" not in emitted


def test_malformed_spec_artifact_becomes_safe_error_event_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, spec_runs, patch_runs, promotions, _ = _configure_artifact_roots(monkeypatch, tmp_path)
    (patch_runs / "empty").mkdir(parents=True)
    (promotions / "empty").mkdir(parents=True)
    bad_bundle = spec_runs / "bad-run" / "bundle.json"
    bad_bundle.parent.mkdir(parents=True)
    bad_bundle.write_text('{"bundle_type":"x","bundle_type":"y"}', encoding="utf-8")

    events = creative_code_telemetry.collect_events(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
    )

    assert len(events) == 1
    event = events[0]
    assert event["lane_stage"] == "artifact_read_error"
    assert event["source_artifact_type"] == "creative_code_artifact_read_error"
    assert event["failure_class"] == "malformed_artifact"
    assert event["taxonomy_codes"] == ["malformed_artifact"]
    assert str(bad_bundle) not in json.dumps(event, sort_keys=True)


def test_artifact_json_symlinks_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, spec_runs, patch_runs, promotions, _ = _configure_artifact_roots(monkeypatch, tmp_path)
    (patch_runs / "empty").mkdir(parents=True)
    (promotions / "empty").mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(_reference_bundle()), encoding="utf-8")
    link = spec_runs / "linked-run" / "bundle.json"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(creative_code_telemetry.CreativeCodeTelemetryError, match="symlinks"):
        creative_code_telemetry.collect_events(
            spec_runs_dir=spec_runs,
            patch_runs_dir=patch_runs,
            promotions_dir=promotions,
        )


def test_artifact_roots_must_stay_inside_creative_code_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, _, patch_runs, promotions, _ = _configure_artifact_roots(monkeypatch, tmp_path)

    with pytest.raises(creative_code_telemetry.CreativeCodeTelemetryError, match="must stay"):
        creative_code_telemetry.collect_events(
            spec_runs_dir=tmp_path / "outside",
            patch_runs_dir=patch_runs,
            promotions_dir=promotions,
        )


def _terminal_outcome(
    patch_result: dict[str, Any],
    *,
    closure_epoch: int = 1,
    terminal_state: str = "merged",
) -> dict[str, Any]:
    promotion = _promotion_artifacts(patch_result)
    plan = promotion[PLAN_FILE]
    receipt = promotion[RECEIPT_FILE]
    closed = terminal_state == "closed_unmerged"
    observation = {
        "promotion_id": receipt["promotion_id"],
        "repository": receipt["repository"],
        "pull_request_number": receipt["pull_request_number"],
        "promoted_head_sha": receipt["commit_sha"],
        "closure_epoch": closure_epoch,
        "terminal_state": terminal_state,
        "merge_sha": None if closed else "c" * 40,
        "reason_code": "rescoped" if closed else None,
        "review": {
            "collection_state": "complete",
            "inventory_fingerprint": fingerprint_payload({"review": "inventory"}),
            "review_seal_fingerprint": fingerprint_payload({"review": "seal"}),
            "sources_configured": 3,
            "sources_observed": 3,
            "findings_total": 1,
            "fixed": 1,
            "not_a_bug": 0,
            "deferred": 0,
            "unresolved_actionable": 0,
        },
        "post_merge": (
            {
                "validation_inventory_fingerprint": None,
                "commands_configured": 0,
                "commands_executed": 0,
                "commands_passed": 0,
                "current_main_ci": "not_observed",
                "current_main_sha": None,
            }
            if closed
            else {
                "validation_inventory_fingerprint": fingerprint_payload(
                    {"post_merge": "inventory"}
                ),
                "commands_configured": 2,
                "commands_executed": 2,
                "commands_passed": 2,
                "current_main_ci": "not_observed",
                "current_main_sha": None,
            }
        ),
        "process": {
            "review_cycles": 2,
            "repair_cycles": 1,
            "validation_attempts": 3,
        },
        "cost_metadata": {
            **default_cost_metadata(),
            "available": True,
            "input_tokens": 100,
            "output_tokens": 20,
        },
        "sanitized": True,
    }
    return build_creative_code_terminal_outcome(
        promotion_plan=plan,
        promotion_receipt=receipt,
        observation=observation,
    )


def test_v1_schema_bytes_remain_unchanged() -> None:
    assert hashlib.sha256(EVENT_SCHEMA.read_bytes()).hexdigest() == (
        "55580c49c8192b99d20e09c3887513e51cc77cbeab237406b97cb6c03a0a9c91"  # pragma: allowlist secret
    )
    assert hashlib.sha256(ROLLUP_SCHEMA.read_bytes()).hexdigest() == (
        "24938480fa2cc78e85937938218ddd5cd1ffa3dcb64ca6c9d054b28dad53fd1f"  # pragma: allowlist secret
    )


def test_one_terminal_outcome_projects_to_exactly_one_v2_event() -> None:
    outcome = _terminal_outcome(_reference_patch_result())

    event = build_creative_code_terminal_telemetry_event(outcome)

    assert validate_creative_code_telemetry_event_any(event) == event
    assert event["schema_version"] == "2.0"
    assert event["policy_version"] == "creative-code-telemetry-v2"
    assert event["lane_stage"] == "pr_terminal"
    assert event["status"] == "merged"
    assert event["terminal_projection"]["review_observation"] == ("no_actionables_observed")
    emitted = json.dumps(event, sort_keys=True)
    for forbidden in (
        "merge_sha",
        "reason_code",
        "inventory_fingerprint",
        "findings_total",
        "commands_configured",
        "conformant",
        "post_merge_validation",
        '"passed"',
    ):
        assert forbidden not in emitted


def test_v2_event_rejects_noncanonical_promotion_id() -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    event["terminal_projection"]["promotion_id"] = "promotion:forged"

    with pytest.raises(
        CreativeCodeTelemetryContractError,
        match="promotion_id has invalid format",
    ):
        validate_creative_code_telemetry_event_any(event)


def test_mixed_v1_v2_rollup_counts_terminal_cost_and_process_once() -> None:
    patch_result = _reference_patch_result()
    legacy_events = [
        creative_code_telemetry.event_from_patch_result(patch_result),
        creative_code_telemetry.event_from_promotion_plan(
            _promotion_artifacts(patch_result)[PLAN_FILE]
        ),
    ]
    terminal_event = build_creative_code_terminal_telemetry_event(_terminal_outcome(patch_result))

    rollup = build_creative_code_telemetry_rollup_v2(
        [*legacy_events, terminal_event],
        input_roots=["patch_runs", "promotions", "terminal_outcomes"],
    )

    assert validate_creative_code_telemetry_rollup_any(rollup) == rollup
    assert rollup["event_count"] == 3
    assert rollup["legacy_event_count"] == 2
    assert rollup["terminal"] == {
        "outcome_count": 1,
        "merged": 1,
        "closed_unmerged": 0,
        "review_observations": {
            "actionables_observed": 0,
            "evidence_unavailable": 0,
            "no_actionables_observed": 1,
        },
        "governance_observations": {
            "blockers_observed": 0,
            "evidence_unavailable": 0,
            "no_blockers_observed": 1,
        },
        "post_merge_observations": {
            "complete_observed": 1,
            "evidence_unavailable": 0,
            "incomplete_observed": 0,
            "not_applicable": 0,
        },
        "process": {
            "repair_cycles": 1,
            "review_cycles": 2,
            "validation_attempts": 3,
        },
    }
    assert rollup["rates"]["merge_rate_bps"] == 10_000
    assert rollup["rates"]["post_merge_complete_rate_bps"] == 10_000
    assert rollup["cost"]["terminal_cost_metadata_available_count"] == 1
    assert rollup["cost"]["terminal_token_usage_available_count"] == 1
    assert rollup["cost"]["cost_metadata_available_count"] == 1
    assert rollup["cost"]["token_usage_available_count"] == 1


def test_closed_unmerged_projects_not_applicable_and_zero_merge_rate() -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(
            _reference_patch_result(),
            terminal_state="closed_unmerged",
        )
    )

    rollup = build_creative_code_telemetry_rollup_v2(
        [event],
        input_roots=["terminal_outcomes"],
    )

    assert event["status"] == "closed_unmerged"
    assert event["terminal_projection"]["post_merge_observation"] == "not_applicable"
    assert rollup["terminal"]["merged"] == 0
    assert rollup["terminal"]["closed_unmerged"] == 1
    assert rollup["rates"]["merge_rate_bps"] == 0
    assert rollup["rates"]["post_merge_complete_rate_bps"] is None


def test_v2_rollup_rejects_unpaired_review_and_governance_counts() -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    rollup = build_creative_code_telemetry_rollup_v2(
        [event],
        input_roots=["terminal_outcomes"],
    )
    governance = rollup["terminal"]["governance_observations"]
    governance["no_blockers_observed"] = 0
    governance["blockers_observed"] = 1

    with pytest.raises(
        CreativeCodeTelemetryContractError,
        match="review and governance observation counts must stay paired",
    ):
        validate_creative_code_telemetry_rollup_any(rollup)


def test_v2_rollup_rejects_closed_outcome_with_post_merge_completion() -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(
            _reference_patch_result(),
            terminal_state="closed_unmerged",
        )
    )
    rollup = build_creative_code_telemetry_rollup_v2(
        [event],
        input_roots=["terminal_outcomes"],
    )
    post_merge = rollup["terminal"]["post_merge_observations"]
    post_merge["not_applicable"] = 0
    post_merge["complete_observed"] = 1
    rollup["rates"]["post_merge_complete_rate_bps"] = 10_000

    with pytest.raises(
        CreativeCodeTelemetryContractError,
        match="closed_unmerged outcomes require not_applicable",
    ):
        validate_creative_code_telemetry_rollup_any(rollup)


def test_v2_rollup_requires_terminal_source_partition() -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    rollup = build_creative_code_telemetry_rollup_v2(
        [event],
        input_roots=["terminal_outcomes"],
    )
    rollup["source_artifacts"][0]["source_artifact_type"] = "creative_code_specification"

    with pytest.raises(
        CreativeCodeTelemetryContractError,
        match="terminal source artifact count",
    ):
        validate_creative_code_telemetry_rollup_any(rollup)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("funnel", "patch_results", 1),
        ("rates", "oracle_pass_rate_bps", 0),
        ("rejections_by_class", "unknown", 1),
        ("failures_by_class", "unknown", 1),
    ],
)
def test_v2_zero_legacy_partition_rejects_legacy_aggregates(
    section: str,
    key: str,
    value: int,
) -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    rollup = build_creative_code_telemetry_rollup_v2(
        [event],
        input_roots=["terminal_outcomes"],
    )
    rollup[section][key] = value

    with pytest.raises(
        CreativeCodeTelemetryContractError,
        match="zero legacy events require empty legacy aggregates",
    ):
        validate_creative_code_telemetry_rollup_any(rollup)


@pytest.mark.parametrize(
    "cost_patch",
    [
        {
            "cost_metadata_available_count": 2,
            "token_usage_available_count": 1,
            "terminal_cost_metadata_available_count": 1,
            "terminal_token_usage_available_count": 1,
        },
        {
            "cost_metadata_available_count": 1,
            "token_usage_available_count": 1,
            "terminal_cost_metadata_available_count": 0,
            "terminal_token_usage_available_count": 0,
        },
        {
            "cost_metadata_available_count": 1,
            "token_usage_available_count": 1,
            "terminal_cost_metadata_available_count": 1,
            "terminal_token_usage_available_count": 0,
        },
    ],
)
def test_v2_rollup_cost_counts_must_fit_event_partitions(
    cost_patch: dict[str, int],
) -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    rollup = build_creative_code_telemetry_rollup_v2(
        [event],
        input_roots=["terminal_outcomes"],
    )
    rollup["cost"].update(cost_patch)

    with pytest.raises(
        CreativeCodeTelemetryContractError,
        match="cost availability counts are inconsistent with represented events",
    ):
        validate_creative_code_telemetry_rollup_any(rollup)


def test_terminal_duplicate_and_source_drift_fail_closed() -> None:
    patch_result = _reference_patch_result()
    first = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(patch_result, closure_epoch=1)
    )
    changed_same_lineage = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(patch_result, closure_epoch=2)
    )

    with pytest.raises(CreativeCodeTelemetryContractError, match="duplicate telemetry event_id"):
        build_creative_code_telemetry_rollup_v2(
            [first, first],
            input_roots=["terminal_outcomes"],
        )
    with pytest.raises(CreativeCodeTelemetryContractError, match="source fingerprint drift"):
        build_creative_code_telemetry_rollup_v2(
            [first, changed_same_lineage],
            input_roots=["terminal_outcomes"],
        )


def test_unknown_v2_versions_fail_without_coercion() -> None:
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    event["schema_version"] = "2.1"
    with pytest.raises(CreativeCodeTelemetryContractError, match="unsupported"):
        validate_creative_code_telemetry_event_any(event)


def test_collector_with_terminal_input_emits_mixed_v2_rollup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root, spec_runs, patch_runs, promotions, telemetry_root = _configure_artifact_roots(
        monkeypatch,
        tmp_path,
    )
    terminal_root = root / "terminal_outcomes"
    patch_result = _reference_patch_result()
    _write_json(patch_runs / "run-a" / "result.json", patch_result)
    for filename, payload in _promotion_artifacts(patch_result).items():
        _write_json(promotions / "promotion-a" / filename, payload)
    outcome = _terminal_outcome(patch_result)
    _write_json(
        terminal_root / outcome["outcome_id"] / "terminal_outcome.json",
        outcome,
    )

    rollup = creative_code_telemetry.collect_and_write(
        spec_runs_dir=spec_runs,
        patch_runs_dir=patch_runs,
        promotions_dir=promotions,
        terminal_outcomes_dir=terminal_root,
        output_dir=telemetry_root,
    )
    events = [
        json.loads(line)
        for line in (telemetry_root / creative_code_telemetry.EVENTS_FILE)
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert rollup["schema_version"] == "2.0"
    assert rollup["terminal"]["outcome_count"] == 1
    assert Counter(event["lane_stage"] for event in events)["pr_terminal"] == 1


def test_terminal_collector_requires_canonical_outcome_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root, spec_runs, patch_runs, promotions, _ = _configure_artifact_roots(
        monkeypatch,
        tmp_path,
    )
    terminal_root = root / "terminal_outcomes"
    outcome = _terminal_outcome(_reference_patch_result())
    _write_json(
        terminal_root / "misplaced-outcome" / "terminal_outcome.json",
        outcome,
    )

    with pytest.raises(
        creative_code_telemetry.CreativeCodeTelemetryError,
        match="canonical outcome directory",
    ):
        creative_code_telemetry.collect_events(
            spec_runs_dir=spec_runs,
            patch_runs_dir=patch_runs,
            promotions_dir=promotions,
            terminal_outcomes_dir=terminal_root,
        )


def test_v2_schemas_align_on_closed_shape_and_finite_vocabulary() -> None:
    event_schema = json.loads(EVENT_V2_SCHEMA.read_text(encoding="utf-8"))
    rollup_schema = json.loads(ROLLUP_V2_SCHEMA.read_text(encoding="utf-8"))
    event = build_creative_code_terminal_telemetry_event(
        _terminal_outcome(_reference_patch_result())
    )
    rollup = build_creative_code_telemetry_rollup_v2(
        [event],
        input_roots=["terminal_outcomes"],
    )

    assert event_schema["additionalProperties"] is False
    assert rollup_schema["additionalProperties"] is False
    assert event_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert rollup_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(event_schema["required"]) == set(event)
    assert set(rollup_schema["required"]) == set(rollup)
    assert event_schema["properties"]["lane_stage"]["const"] == "pr_terminal"
    assert event_schema["properties"]["status"]["enum"] == [
        "merged",
        "closed_unmerged",
    ]
    assert event_schema["$defs"]["terminal_projection"]["properties"]["promotion_id"] == {
        "$ref": "#/$defs/promotion_id"
    }
    review_implications = [
        clause
        for clause in event_schema["allOf"]
        if "terminal_projection" in clause.get("if", {}).get("properties", {})
    ]
    assert [
        (
            clause["if"]["properties"]["terminal_projection"]["properties"]["review_observation"][
                "const"
            ],
            clause["then"]["properties"]["terminal_projection"]["properties"][
                "governance_observation"
            ]["const"],
        )
        for clause in review_implications
    ] == [
        ("actionables_observed", "blockers_observed"),
        ("no_actionables_observed", "no_blockers_observed"),
        ("evidence_unavailable", "evidence_unavailable"),
    ]
    assert rollup_schema["properties"]["policy_version"]["const"] == "creative-code-telemetry-v2"
    assert validate_creative_code_telemetry_event_any(event) == event
    assert validate_creative_code_telemetry_rollup_any(rollup) == rollup

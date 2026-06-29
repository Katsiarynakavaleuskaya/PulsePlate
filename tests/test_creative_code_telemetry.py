from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_telemetry
from scripts.orchestration.creative_code_patch_contract import (
    build_creative_code_patch_build_request,
    build_creative_code_patch_result,
)
from scripts.orchestration.creative_code_pr_promotion import (
    APPROVAL_FILE,
    PLAN_FILE,
    RECEIPT_FILE,
    VALIDATION_FILE,
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
    build_creative_code_telemetry_event,
    build_creative_code_telemetry_rollup,
    default_metrics,
    read_json_object,
    validate_creative_code_rejection_taxonomy,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_BUNDLE = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.json"
EVENT_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_telemetry_event.v1.schema.json"
)
ROLLUP_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_telemetry_rollup.v1.schema.json"
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


def _reference_patch_result(*, accepted: bool = True) -> dict[str, Any]:
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
    runner_result = {
        "experiment_id": "exp-pr4-telemetry",
        "status": "accepted" if accepted else "rejected",
        "failure_class": None if accepted else "guard_failure",
        "mutated_paths": ["core/rag/orchestration.py"],
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
        failure_class=None if accepted else "guard_failure",
    )


def _promotion_artifacts(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
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
    assert unsafe_text_pattern.search("/Users/example/repo")


def test_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"2.0"}', encoding="utf-8")

    with pytest.raises(CreativeCodeTelemetryContractError, match="duplicate key"):
        read_json_object(duplicate)


def test_event_rejects_raw_patch_leaks_and_mutating_authority() -> None:
    source_fingerprint = "sha256:" + ("a" * 64)

    with pytest.raises(CreativeCodeTelemetryContractError, match="unsafe telemetry text"):
        build_creative_code_telemetry_event(
            lane_stage="specification",
            source_artifact_type="creative_code_specification",
            source_artifact_id="candidate.patch",
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

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import uuid

import pytest

from scripts.orchestration import (
    creative_hypothesis_spec_bridge as bridge_cli,
    creative_spec_learning_rollup as rollup_cli,
    creative_specification_skeptic_review as review_cli,
)
from scripts.orchestration.agent_learning_loop import (
    AUTHORITY_BOUNDARY,
    build_agent_learning_record,
)
from scripts.orchestration.creative_spec_learning_rollup_contract import (
    CreativeSpecLearningRollupError,
    ROLLUP_ARTIFACT_TYPE,
    build_coordinator_advisory_hints,
    build_creative_spec_learning_rollup,
    validate_coordinator_advisory_hints,
    validate_creative_spec_learning_rollup,
    _set_identity as set_creative_learning_identity,
)
from tests.test_creative_specification_skeptic_review import (
    REPO_ROOT,
    _prepared_bridge,
    _read_json,
    _review_input,
    _refresh_receipt_identity,
    _write_review_input,
)


def _finalized_artifacts(
    capsys: pytest.CaptureFixture[str],
    *,
    suffix: str,
    all_rejected: bool = False,
) -> tuple[Path, Path, dict[str, dict[str, object]]]:
    output_dir, input_dir = _prepared_bridge(capsys, suffix=suffix)
    reviews_path = _write_review_input(
        output_dir,
        _review_input(output_dir, all_rejected=all_rejected),
    )
    assert (
        review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    reviewed_dir = output_dir / "spec_finalize_reviewed"
    attachment_path = reviewed_dir / review_cli.ATTACHMENT_FILENAME
    assert review_cli.main(["finalize", "--attachment", str(attachment_path)]) == 0
    capsys.readouterr()
    return (
        output_dir,
        input_dir,
        {
            "bridge_metrics": _read_json(output_dir / bridge_cli.METRICS_FILENAME),
            "skeptic_attachment": _read_json(attachment_path),
            "finalize_receipt": _read_json(reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME),
            "bundle": _read_json(reviewed_dir / review_cli.BUNDLE_FILENAME),
        },
    )


def test_collect_selected_variant_builds_success_learning_rollup_and_hints(
    capsys: pytest.CaptureFixture[str],
) -> None:
    suffix = f"learning-selected-{uuid.uuid4().hex[:8]}"
    output_dir, input_dir, artifacts = _finalized_artifacts(capsys, suffix=suffix)
    rollup_dir = rollup_cli.LEARNING_ROLLUP_ROOT / f"pytest-{suffix}"
    shutil.rmtree(rollup_dir, ignore_errors=True)
    try:
        exit_code = rollup_cli.main(
            [
                "collect",
                "--bridge-metrics",
                str(output_dir / bridge_cli.METRICS_FILENAME),
                "--skeptic-attachment",
                str(output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME),
                "--finalize-receipt",
                str(output_dir / "spec_finalize_reviewed" / review_cli.FINALIZE_RECEIPT_FILENAME),
                "--bundle",
                str(output_dir / "spec_finalize_reviewed" / review_cli.BUNDLE_FILENAME),
                "--output-dir",
                str(rollup_dir),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0, captured.out
        assert rollup_cli.COLLECT_SUCCESS_OUTPUT in captured.out

        rollup = validate_creative_spec_learning_rollup(
            _read_json(rollup_dir / rollup_cli.ROLLUP_FILENAME)
        )
        hints = validate_coordinator_advisory_hints(
            _read_json(rollup_dir / rollup_cli.HINTS_FILENAME)
        )
        records = rollup["learning_records"]
        assert rollup["outcomes"]["synthesis_status"] == "selected"
        assert rollup["learning_summary"]["successful_iteration_count"] == 1
        assert any(record["pattern_kind"] == "successful_iteration" for record in records)
        for record in records:
            metrics = record["learning_metrics"]
            assert record["human_review_required"] is True
            assert metrics["authority_boundary"] == AUTHORITY_BOUNDARY
            assert metrics["semantic_cache_used"] is False
            assert metrics["graph_truth_updated"] is False
            assert metrics["product_runtime_truth"] is False
        success_records = [
            record for record in records if record["pattern_kind"] == "successful_iteration"
        ]
        assert success_records[0]["learning_metrics"]["primary_metric"] == (
            "successful_pattern_reuse"
        )
        assert hints["reuse_lesson_ids"] == rollup["learning_summary"]["reuse_lesson_ids"]
        assert hints["avoid_lesson_ids"] == rollup["learning_summary"]["avoid_lesson_ids"]
        assert hints["authority"]["advisory_only"] is True
        assert hints["authority"]["force_agent_routing"] is False
        assert hints["authority"]["execute_agents"] is False
        assert hints["source_rollup_id"] == rollup["rollup_id"]
        assert artifacts["finalize_receipt"]["synthesis_status"] == "selected"
    finally:
        shutil.rmtree(rollup_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_all_rejected_builds_failure_records_without_reuse_hints(
    capsys: pytest.CaptureFixture[str],
) -> None:
    suffix = f"learning-all-rejected-{uuid.uuid4().hex[:8]}"
    output_dir, input_dir, artifacts = _finalized_artifacts(
        capsys,
        suffix=suffix,
        all_rejected=True,
    )
    try:
        rollup = build_creative_spec_learning_rollup(**artifacts)
        hints = build_coordinator_advisory_hints(rollup)
        assert rollup["outcomes"]["synthesis_status"] == "all_rejected"
        assert rollup["outcomes"]["selected_variant_id"] is None
        assert rollup["learning_summary"]["successful_iteration_count"] == 0
        assert rollup["learning_summary"]["failure_count"] == rollup["outcomes"]["variant_count"]
        assert all(record["pattern_kind"] == "failure" for record in rollup["learning_records"])
        assert all(
            record["learning_metrics"]["primary_metric"] == "repeat_failure_reduction"
            for record in rollup["learning_records"]
        )
        assert hints["reuse_lesson_ids"] == []
        assert hints["avoid_lesson_ids"] == rollup["learning_summary"]["avoid_lesson_ids"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_rollup_rejects_tampered_finalize_bundle_fingerprint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    suffix = f"learning-tampered-{uuid.uuid4().hex[:8]}"
    output_dir, input_dir, artifacts = _finalized_artifacts(capsys, suffix=suffix)
    try:
        tampered_receipt = deepcopy(artifacts["finalize_receipt"])
        tampered_receipt["bundle_fingerprint"] = "sha256:" + ("a" * 64)
        tampered_receipt = _refresh_receipt_identity(tampered_receipt)
        with pytest.raises(CreativeSpecLearningRollupError, match="fingerprint_mismatch"):
            build_creative_spec_learning_rollup(
                bridge_metrics=artifacts["bridge_metrics"],
                skeptic_attachment=artifacts["skeptic_attachment"],
                finalize_receipt=tampered_receipt,
                bundle=artifacts["bundle"],
            )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_hints_reject_unsafe_text_and_authority_widening(
    capsys: pytest.CaptureFixture[str],
) -> None:
    suffix = f"learning-unsafe-{uuid.uuid4().hex[:8]}"
    output_dir, input_dir, artifacts = _finalized_artifacts(capsys, suffix=suffix)
    try:
        hints = build_coordinator_advisory_hints(build_creative_spec_learning_rollup(**artifacts))

        unsafe_hints = deepcopy(hints)
        unsafe_hints["recommended_role_focus"][0]["reason"] = "raw prompt leaked"
        with pytest.raises(CreativeSpecLearningRollupError, match="unsafe"):
            validate_coordinator_advisory_hints(unsafe_hints)

        widened_hints = deepcopy(hints)
        widened_hints["authority"]["force_agent_routing"] = True
        with pytest.raises(CreativeSpecLearningRollupError, match="invalid authority"):
            validate_coordinator_advisory_hints(widened_hints)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_rollup_rejects_semantic_cache_and_graph_truth_claims(
    capsys: pytest.CaptureFixture[str],
) -> None:
    suffix = f"learning-cache-claim-{uuid.uuid4().hex[:8]}"
    output_dir, input_dir, artifacts = _finalized_artifacts(capsys, suffix=suffix)
    try:
        rollup = build_creative_spec_learning_rollup(**artifacts)
        unsafe_record = build_agent_learning_record(
            source="creative_spec_finalize:finalize-test:selected:variant-test",
            pattern="Selected variant reused semantic cache used and graph truth updated.",
            severity="low",
            affected_surfaces=["scripts/orchestration/creative_spec_learning_rollup.py"],
            root_cause="Unsafe authority claim must remain outside creative learning records.",
            required_oracle="deterministic_content_oracle",
            promotion_target="docs/orchestration/AGENT_LEARNING_LOOP.md",
            pattern_kind="successful_iteration",
        )
        rollup["learning_records"] = [unsafe_record]
        rollup["learning_summary"] = {
            "learning_record_count": 1,
            "successful_iteration_count": 1,
            "failure_count": 0,
            "reuse_lesson_ids": [unsafe_record["lesson_id"]],
            "avoid_lesson_ids": [],
        }
        set_creative_learning_identity(
            rollup,
            id_key="rollup_id",
            asset_type=ROLLUP_ARTIFACT_TYPE,
            upstream_ids=(
                str(rollup["source"]["finalize_id"]),
                str(rollup["source"]["bundle_id"]),
                str(rollup["source"]["bridge_metrics_id"]),
            ),
        )

        with pytest.raises(CreativeSpecLearningRollupError, match="unsafe"):
            validate_creative_spec_learning_rollup(rollup)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_collect_rejects_duplicate_json_keys_before_validation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    suffix = f"learning-duplicate-{uuid.uuid4().hex[:8]}"
    output_dir, input_dir, _artifacts = _finalized_artifacts(capsys, suffix=suffix)
    duplicate_metrics = output_dir / "duplicate_metrics.json"
    duplicate_metrics.write_text(
        '{"schema_version": "1.0", "schema_version": "1.0"}\n',
        encoding="utf-8",
    )
    try:
        exit_code = rollup_cli.main(
            [
                "collect",
                "--bridge-metrics",
                str(duplicate_metrics),
                "--skeptic-attachment",
                str(output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME),
                "--finalize-receipt",
                str(output_dir / "spec_finalize_reviewed" / review_cli.FINALIZE_RECEIPT_FILENAME),
                "--bundle",
                str(output_dir / "spec_finalize_reviewed" / review_cli.BUNDLE_FILENAME),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "duplicate key" in captured.out
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_learning_rollup_schemas_are_closed() -> None:
    for schema_name in (
        "creative_spec_learning_rollup.v1.schema.json",
        "creative_spec_coordinator_advisory_hints.v1.schema.json",
    ):
        schema = json.loads(
            (REPO_ROOT / "docs" / "orchestration" / "contracts" / schema_name).read_text(
                encoding="utf-8"
            )
        )
        assert schema["additionalProperties"] is False
        for definition in schema.get("$defs", {}).values():
            if definition.get("type") == "object":
                assert definition["additionalProperties"] is False

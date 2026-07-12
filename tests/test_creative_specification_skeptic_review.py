from __future__ import annotations

import ast
from collections.abc import Callable
from copy import deepcopy
import errno
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any
import uuid

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import (
    creative_hypothesis_spec_bridge as bridge_cli,
    creative_pilot_workspace_contract as pilot_contract,
    creative_specification_skeptic_review as review_cli,
    creative_specification_skeptic_review_contract as review_contract,
)
from scripts.orchestration.creative_code_specification import (
    REQUIRED_SKEPTIC_REVIEWERS,
    read_creative_code_specification_bundle,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    PREPARE_FILENAMES,
    build_creative_hypothesis_spec_bridge_bundle,
)
from scripts.orchestration.creative_specification_skeptic_review_contract import (
    ATTACHMENT_ARTIFACT_TYPE,
    FINALIZE_RECEIPT_ARTIFACT_TYPE,
    CreativeSpecificationSkepticReviewError,
    build_skeptic_review_attachment,
    default_review_input_authority,
    validate_agent_skeptic_reviews_input,
    validate_finalize_receipt,
    validate_skeptic_review_attachment,
)
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    COORDINATOR_DISPATCH_POLICY_VERSION,
    COORDINATOR_DISPATCH_TYPE,
    HYPOTHESIS_PACKET_TYPE,
    _artifact_identity,
    build_creative_hypothesis_agent_routing,
    build_creative_hypothesis_approval,
    build_creative_hypothesis_coordinator_dispatch,
    build_creative_hypothesis_packet,
    build_creative_protocol_context_map,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SHA256_D = "sha256:" + ("d" * 64)
SCHEMA_FILES = (
    "creative_specification_agent_skeptic_reviews.v1.schema.json",
    "creative_specification_skeptic_review_attachment.v1.schema.json",
    "creative_specification_finalize_receipt.v1.schema.json",
)


def test_typed_json_object_narrows_mapping_and_rejects_non_string_keys() -> None:
    assert review_cli._require_typed_json_object({"receipt_id": "receipt-1"}, label="receipt") == {
        "receipt_id": "receipt-1"
    }
    with pytest.raises(
        review_cli.CreativeSpecificationSkepticReviewCliError,
        match="must be a JSON object",
    ):
        review_cli._require_typed_json_object([], label="receipt")
    with pytest.raises(
        review_cli.CreativeSpecificationSkepticReviewCliError,
        match="must use string keys",
    ):
        review_cli._require_typed_json_object({1: "invalid"}, label="receipt")


def _context() -> dict[str, Any]:
    return build_creative_protocol_context_map(
        changed_paths=[
            "scripts/orchestration/creative_specification_skeptic_review.py",
            "scripts/orchestration/creative_specification_skeptic_review_contract.py",
            "tests/test_creative_specification_skeptic_review.py",
        ],
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2072,
        base_ref="main",
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        task_packet_id="task:spec-skeptic-review-finalize",
        generated_at_utc="2026-07-04T00:00:00Z",
        nearby_repo_refs=["scripts/orchestration/creative_code_spec_pipeline.py"],
        test_refs=["tests/test_creative_specification_skeptic_review.py"],
        contract_refs=["docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md"],
        backlog_refs=["docs/roadmap/BACKLOG_LEDGER.md"],
        review_source_refs=["artifacts/orchestration/experiments/results/oracle-result.json"],
        capability_state_ref=(
            "artifacts/orchestration/experiments/creative_context/capability_state.json"
        ),
        philosophical_context_refs=["docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md"],
        cross_domain_candidate_refs=[
            "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md"
        ],
        label_enabled=False,
        marker_enabled=False,
        manual_enabled=False,
        sealed_codex_security_scan_ref=(
            "artifacts/orchestration/experiments/creative_context/codex-security.json"
        ),
        sealed_codex_security_scan_fingerprint=SHA256_D,
        security_relevant_diff_changed=False,
    )


def _refresh_packet_identity(packet: dict[str, Any]) -> dict[str, Any]:
    body = {
        key: value for key, value in packet.items() if key not in {"packet_id", "idempotency_key"}
    }
    packet_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=HYPOTHESIS_PACKET_TYPE,
        upstream_ids=(str(packet["context_map_id"]),),
    )
    packet["packet_id"] = packet_id
    packet["idempotency_key"] = idempotency_key
    return packet


def _chain(
    hypothesis_suffix: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    context = _context()
    packet = build_creative_hypothesis_packet(context, hypothesis_count=3)
    hypothesis = dict(packet["hypotheses"][0])
    hypothesis["hypothesis_id"] = f"{hypothesis['hypothesis_id']}-{hypothesis_suffix}"
    hypothesis["target_surfaces"] = sorted(
        [
            "docs/prompts/cv/program.md",
            "scripts/orchestration/creative_specification_skeptic_review.py",
            "scripts/orchestration/creative_specification_skeptic_review_contract.py",
            "tests/test_creative_specification_skeptic_review.py",
        ]
    )
    hypothesis["tests_or_oracles"] = sorted(
        [
            "tests/test_creative_specification_skeptic_review.py",
            "docs/orchestration/contracts/creative_specification_agent_skeptic_reviews.v1.schema.json",
        ]
    )
    hypothesis["negative_controls"] = sorted(
        [
            "patch_authority_rejected",
            "provider_call_rejected",
            "runtime_truth_rejected",
        ]
    )
    packet["hypotheses"][0] = hypothesis
    packet = _refresh_packet_identity(packet)
    routing = build_creative_hypothesis_agent_routing(packet)
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )
    approval = build_creative_hypothesis_approval(
        hypothesis_id=hypothesis["hypothesis_id"],
        decision="approve_for_pr1_specification",
        hypothesis_packet=packet,
        approved_target_surfaces=list(hypothesis["target_surfaces"]),
        approved_agents=[dispatch["dispatch"][0]["primary_agent"]],
        next_step="create_pr1_specification",
    )
    return context, packet, dispatch, approval


def _write_creative_context_inputs(
    *,
    leaf: str,
    context: dict[str, Any],
    packet: dict[str, Any],
    dispatch: dict[str, Any],
    approval: dict[str, Any],
) -> tuple[Path, Path, Path, Path, Path]:
    input_dir = bridge_cli.CREATIVE_CONTEXT_ROOT / leaf
    shutil.rmtree(input_dir, ignore_errors=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    paths = (
        input_dir / "context_map.json",
        input_dir / "hypothesis_packet.json",
        input_dir / "coordinator_dispatch.json",
        input_dir / "approval.json",
    )
    for path, payload in zip(paths, (context, packet, dispatch, approval), strict=True):
        _write_json(path, payload)
    return input_dir, *paths


def _prepared_bridge(
    capsys: pytest.CaptureFixture[str],
    *,
    suffix: str,
) -> tuple[Path, Path]:
    context, packet, dispatch, approval = _chain(hypothesis_suffix=suffix)
    expected_bundle = build_creative_hypothesis_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        coordinator_dispatch=dispatch,
        approval=approval,
        variant_count=3,
    )
    output_dir = bridge_cli.SPEC_BRIDGE_ROOT / str(expected_bundle["bridge"]["bridge_id"])
    shutil.rmtree(output_dir, ignore_errors=True)
    input_dir, context_path, packet_path, dispatch_path, approval_path = (
        _write_creative_context_inputs(
            leaf=f"pytest-spec-review-{suffix}",
            context=context,
            packet=packet,
            dispatch=dispatch,
            approval=approval,
        )
    )
    exit_code = bridge_cli.main(
        [
            "build-and-prepare",
            "--context-map",
            str(context_path),
            "--hypothesis-packet",
            str(packet_path),
            "--coordinator-dispatch",
            str(dispatch_path),
            "--approval",
            str(approval_path),
            "--variant-count",
            "3",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    assert captured.out.strip() == bridge_cli.SUCCESS_BUILD_PREPARE_OUTPUT
    return output_dir, input_dir


def _review_input(output_dir: Path, *, all_rejected: bool = False) -> dict[str, Any]:
    bridge = _read_json(output_dir / bridge_cli.BRIDGE_FILENAME)
    candidate = _read_json(output_dir / bridge_cli.CANDIDATE_FILENAME)
    spec_prepare = output_dir / "spec_prepare"
    source_packet = _read_json(spec_prepare / "source_packet.json")
    variants = _read_json(spec_prepare / "variants.json")
    reviews: list[dict[str, Any]] = []
    for variant_index, variant in enumerate(variants):
        for reviewer in REQUIRED_SKEPTIC_REVIEWERS:
            decision = "reject" if all_rejected or variant_index != 0 else "pass"
            reviews.append(
                {
                    "variant_id": variant["variant_id"],
                    "reviewer_role": reviewer,
                    "decision": decision,
                    "blockers": [] if decision == "pass" else ["skeptic_rejected_variant"],
                    "unsafe_authority_flags": [],
                    "duplicate_reason": "none",
                    "required_revision": "none",
                }
            )
    return {
        "schema_version": "1.0",
        "artifact_type": "creative_specification_agent_skeptic_reviews",
        "policy_version": "creative-specification-skeptic-review-finalize-v1",
        "source_bridge_id": bridge["bridge_id"],
        "source_bridge_fingerprint": fingerprint_payload(bridge),
        "source_candidate_id": candidate["candidate_id"],
        "source_candidate_fingerprint": fingerprint_payload(candidate),
        "source_packet_fingerprint": fingerprint_payload(source_packet),
        "variants_fingerprint": fingerprint_payload(variants),
        "reviews": reviews,
        "authority": default_review_input_authority(),
        "sanitized": True,
    }


def _write_review_input(output_dir: Path, payload: dict[str, Any]) -> Path:
    path = output_dir / "agent_skeptic_reviews.json"
    _write_json(path, payload)
    return path


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _refresh_attachment_identity(attachment: dict[str, Any]) -> dict[str, Any]:
    attachment["attachment_id"] = "pending"
    attachment["idempotency_key"] = "pending"
    review_contract._set_identity(
        attachment,
        id_key="attachment_id",
        asset_type=ATTACHMENT_ARTIFACT_TYPE,
    )
    return attachment


def _refresh_receipt_identity(receipt: dict[str, Any]) -> dict[str, Any]:
    receipt["finalize_id"] = "pending"
    receipt["idempotency_key"] = "pending"
    review_contract._set_identity(
        receipt,
        id_key="finalize_id",
        asset_type=FINALIZE_RECEIPT_ARTIFACT_TYPE,
    )
    return receipt


def _rebuild_attachment(
    attachment: dict[str, Any],
    *,
    source_overrides: dict[str, Any] | None = None,
    reviewed_overrides: dict[str, Any] | None = None,
    normalized_reviews: list[dict[str, Any]] | None = None,
    variant_count: int | None = None,
) -> dict[str, Any]:
    source = dict(attachment["source"])
    reviewed = dict(attachment["reviewed_run"])
    if source_overrides:
        source.update(source_overrides)
    if reviewed_overrides:
        reviewed.update(reviewed_overrides)
    reviews = (
        normalized_reviews
        if normalized_reviews is not None
        else _read_json(REPO_ROOT / reviewed["skeptic_reviews_ref"])
    )
    return build_skeptic_review_attachment(
        bridge_id=source["bridge_id"],
        bridge_fingerprint=source["bridge_fingerprint"],
        bridge_ref=source["bridge_ref"],
        candidate_id=source["candidate_id"],
        candidate_fingerprint=source["candidate_fingerprint"],
        candidate_ref=source["candidate_ref"],
        metrics_id=source["metrics_id"],
        metrics_fingerprint=source["metrics_fingerprint"],
        metrics_ref=source["metrics_ref"],
        spec_prepare_ref=source["spec_prepare_ref"],
        source_packet_ref=source["source_packet_ref"],
        source_packet_fingerprint=source["source_packet_fingerprint"],
        variants_ref=source["variants_ref"],
        variants_fingerprint=source["variants_fingerprint"],
        pending_reviews_ref=source["pending_reviews_ref"],
        pending_reviews_fingerprint=source["pending_reviews_fingerprint"],
        context_pack_ref=source["context_pack_ref"],
        context_pack_fingerprint=source["context_pack_fingerprint"],
        reviewed_run_dir_ref=reviewed["run_dir_ref"],
        reviewed_source_packet_ref=reviewed["source_packet_ref"],
        reviewed_variants_ref=reviewed["variants_ref"],
        reviewed_reviews_ref=reviewed["skeptic_reviews_ref"],
        reviewed_context_pack_ref=reviewed["context_pack_ref"],
        normalized_reviews=reviews,
        variant_count=(
            variant_count if variant_count is not None else attachment["coverage"]["variant_count"]
        ),
    )


def test_attach_validate_finalize_preserves_original_spec_prepare(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="happy")
    try:
        spec_prepare = output_dir / "spec_prepare"
        original_fingerprints = {
            filename: fingerprint_payload(_read_json(spec_prepare / filename))
            for filename in PREPARE_FILENAMES
        }
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
        assert captured.out.strip() == review_cli.ATTACH_SUCCESS_OUTPUT

        reviewed_dir = output_dir / "spec_finalize_reviewed"
        attached_identity = (reviewed_dir.stat().st_dev, reviewed_dir.stat().st_ino)
        attachment_path = reviewed_dir / review_cli.ATTACHMENT_FILENAME
        attachment = validate_skeptic_review_attachment(_read_json(attachment_path))
        assert attachment["reviewed_run"]["run_dir_ref"].endswith("/spec_finalize_reviewed")
        assert not (reviewed_dir / review_cli.BUNDLE_FILENAME).exists()
        assert {
            filename: fingerprint_payload(_read_json(spec_prepare / filename))
            for filename in PREPARE_FILENAMES
        } == original_fingerprints

        exit_code = review_cli.main(["validate", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
        assert captured.out.strip() == review_cli.VALIDATE_SUCCESS_OUTPUT

        exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
        assert captured.out.strip() == review_cli.FINALIZE_SUCCESS_OUTPUT
        first_finalized_identity = (reviewed_dir.stat().st_dev, reviewed_dir.stat().st_ino)
        assert first_finalized_identity != attached_identity
        retained_before_replay = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert len(retained_before_replay) == 1
        assert {path.name for path in retained_before_replay[0].iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
        review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)
        forged_retained = output_dir / ".spec_finalize_reviewed.aaaaaaaaaaaaaaaa.pre-finalize"
        forged_retained.mkdir()
        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="at most one retained pre-finalize run",
        ):
            review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)
        forged_retained.rmdir()
        retained_source = retained_before_replay[0] / "source_packet.json"
        retained_source_bytes = retained_source.read_bytes()
        retained_source.write_text("{}\n", encoding="utf-8")
        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="adaptive retained source_packet.json diverges from canonical",
        ):
            review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)
        retained_source.write_bytes(retained_source_bytes)
        review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)
        real_read_json_at = review_cli._read_json_at
        content_reads = 0

        def mutate_retained_content_after_comparison(directory_fd: int, filename: str) -> Any:
            nonlocal content_reads
            payload = real_read_json_at(directory_fd, filename)
            content_reads += 1
            if content_reads == 10:
                retained_source.write_text("{}\n", encoding="utf-8")
            return payload

        with monkeypatch.context() as context:
            context.setattr(
                review_cli,
                "_read_json_at",
                mutate_retained_content_after_comparison,
            )
            with pytest.raises(
                review_cli.CreativeSpecificationSkepticReviewCliError,
                match="adaptive retained pre-finalize lineage changed during validation",
            ):
                review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)
        assert content_reads == 10
        retained_source.write_bytes(retained_source_bytes)
        review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)

        replacement = output_dir / ".retained-replacement"
        detached_retained = output_dir / ".detached-valid-retained"
        replacement.mkdir()
        pinned_reads = 0

        def swap_retained_after_pinned_reads(directory_fd: int, filename: str) -> Any:
            nonlocal pinned_reads
            payload = real_read_json_at(directory_fd, filename)
            pinned_reads += 1
            if pinned_reads == 10:
                retained_before_replay[0].rename(detached_retained)
                replacement.rename(retained_before_replay[0])
            return payload

        with monkeypatch.context() as context:
            context.setattr(review_cli, "_read_json_at", swap_retained_after_pinned_reads)
            with pytest.raises(
                review_cli.CreativeSpecificationSkepticReviewCliError,
                match="adaptive retained pre-finalize lineage changed during validation",
            ):
                review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)
        assert pinned_reads == 10
        assert list(retained_before_replay[0].iterdir()) == []
        assert {path.name for path in detached_retained.iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
        retained_before_replay[0].rename(replacement)
        detached_retained.rename(retained_before_replay[0])
        replacement.rmdir()
        review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)

        external_replacement = input_dir / ".external-empty-retained"
        external_detached = input_dir / ".external-detached-valid"
        external_replacement.mkdir()
        real_stat = review_cli.os.stat
        retained_stat_reads = 0

        def swap_during_terminal_lineage_snapshot(
            path: Any,
            *args: Any,
            **kwargs: Any,
        ) -> os.stat_result:
            nonlocal retained_stat_reads
            observed = real_stat(path, *args, **kwargs)
            if path == retained_before_replay[0].name and kwargs.get("dir_fd") is not None:
                retained_stat_reads += 1
                if retained_stat_reads == 2:
                    retained_before_replay[0].rename(external_detached)
                    external_replacement.rename(retained_before_replay[0])
            return observed

        with monkeypatch.context() as context:
            context.setattr(review_cli.os, "stat", swap_during_terminal_lineage_snapshot)
            with pytest.raises(
                review_cli.CreativeSpecificationSkepticReviewCliError,
                match="bridge changed during lineage snapshot",
            ):
                review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)
        assert retained_stat_reads == 2
        assert list(retained_before_replay[0].iterdir()) == []
        assert {path.name for path in external_detached.iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
        retained_before_replay[0].rename(external_replacement)
        external_detached.rename(retained_before_replay[0])
        external_replacement.rmdir()
        review_cli._validate_adaptive_retained_pre_finalize_run(output_dir)

        bundle = validate_creative_code_specification_bundle(
            read_creative_code_specification_bundle(reviewed_dir / review_cli.BUNDLE_FILENAME)
        )
        receipt = validate_finalize_receipt(
            _read_json(reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME)
        )
        assert bundle["synthesis"]["selected_variant_id"] is not None
        assert receipt["synthesis_status"] == "selected"
        assert receipt["next_allowed_action"] == "human_review_for_patch_builder"
        assert receipt["counts"]["selected_variant_count"] == 1
        finalized_fingerprints = {
            filename: fingerprint_payload(_read_json(reviewed_dir / filename))
            for filename in (review_cli.BUNDLE_FILENAME, review_cli.FINALIZE_RECEIPT_FILENAME)
        }
        exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
        assert captured.out.strip() == review_cli.FINALIZE_SUCCESS_OUTPUT
        assert reviewed_dir.is_dir()
        assert (reviewed_dir.stat().st_dev, reviewed_dir.stat().st_ino) == first_finalized_identity
        assert {
            filename: fingerprint_payload(_read_json(reviewed_dir / filename))
            for filename in (review_cli.BUNDLE_FILENAME, review_cli.FINALIZE_RECEIPT_FILENAME)
        } == finalized_fingerprints
        retained_after_replay = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert retained_after_replay == retained_before_replay
        assert len(list(retained_after_replay[0].iterdir())) == 5
        _assert_schema_artifact_refs_accept_generated_attachment_and_receipt(
            attachment=attachment,
            receipt=receipt,
        )

        exit_code = bridge_cli.main(
            ["validate", "--bridge", str(output_dir / bridge_cli.BRIDGE_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
        assert captured.out.strip() == bridge_cli.SUCCESS_VALIDATE_OUTPUT
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_rejects_noncanonical_bridge_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="noncanonical-bridge-file")
    try:
        bridge_copy = output_dir / "copy.json"
        shutil.copyfile(output_dir / bridge_cli.BRIDGE_FILENAME, bridge_copy)
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(bridge_copy),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert f"canonical {bridge_cli.BRIDGE_FILENAME}" in captured.err
        assert not (output_dir / "spec_finalize_reviewed").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def _assert_schema_artifact_refs_accept_generated_attachment_and_receipt(
    *,
    attachment: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    attachment_schema = json.loads(
        (
            REPO_ROOT
            / "docs/orchestration/contracts/creative_specification_skeptic_review_attachment.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    receipt_schema = json.loads(
        (
            REPO_ROOT
            / "docs/orchestration/contracts/creative_specification_finalize_receipt.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    attachment_artifact_ref = re.compile(attachment_schema["$defs"]["artifact_ref"]["pattern"])
    attachment_reviewed_run_ref = re.compile(
        attachment_schema["$defs"]["reviewed_run_ref"]["pattern"]
    )
    receipt_artifact_ref = re.compile(receipt_schema["$defs"]["artifact_ref"]["pattern"])
    receipt_reviewed_run_ref = re.compile(receipt_schema["$defs"]["reviewed_run_ref"]["pattern"])

    for key, value in attachment["source"].items():
        if key.endswith("_ref"):
            assert attachment_artifact_ref.fullmatch(value), key
    assert attachment_reviewed_run_ref.fullmatch(attachment["reviewed_run"]["run_dir_ref"])
    for key, value in attachment["reviewed_run"].items():
        if key.endswith("_ref") and key != "run_dir_ref":
            assert attachment_artifact_ref.fullmatch(value), key
    assert receipt_artifact_ref.fullmatch(receipt["source_attachment_ref"])
    assert receipt_artifact_ref.fullmatch(receipt["bundle_ref"])
    assert receipt_reviewed_run_ref.fullmatch(receipt["reviewed_run_dir_ref"])


def test_finalize_receipt_records_all_rejected_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="all-rejected")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir, all_rejected=True))
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
        attachment_path = output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        assert review_cli.main(["finalize", "--attachment", str(attachment_path)]) == 0
        capsys.readouterr()

        receipt = validate_finalize_receipt(
            _read_json(output_dir / "spec_finalize_reviewed" / review_cli.FINALIZE_RECEIPT_FILENAME)
        )
        assert receipt["selected_variant_id"] is None
        assert receipt["synthesis_status"] == "all_rejected"
        assert receipt["next_allowed_action"] == "human_review_for_discard_or_defer"
        assert receipt["counts"]["selected_variant_count"] == 0
        assert receipt["counts"]["rejected_variant_count"] == receipt["counts"]["variant_count"]
        assert receipt["counts"]["rejection_record_count"] == receipt["counts"]["variant_count"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_noncanonical_attachment_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="noncanonical-attachment")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        alternate_path = reviewed_dir / "alternate_attachment.json"
        alternate_path.write_text(attachment_path.read_text(encoding="utf-8"), encoding="utf-8")

        exit_code = review_cli.main(["validate", "--attachment", str(alternate_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert f"canonical {review_cli.ATTACHMENT_FILENAME}" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_adaptive_validate_stale_base_returns_stable_cli_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    attachment = tmp_path / review_cli.ATTACHMENT_FILENAME
    attachment.write_text("{}\n", encoding="utf-8")
    reviewed_dir = tmp_path / "spec_finalize_reviewed"
    reviewed_dir.mkdir()

    def stale_base(_path: Path) -> tuple[dict[str, object], Path]:
        raise pilot_contract.CreativePilotContractError(
            "adaptive_base_drift: current origin/main advanced"
        )

    monkeypatch.setattr(review_cli, "_validate_attachment_artifacts", stale_base)
    assert review_cli.main(["validate", "--attachment", str(attachment)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "FAIL: adaptive_base_drift: current origin/main advanced\n"
    assert not (reviewed_dir / review_cli.BUNDLE_FILENAME).exists()
    assert not (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).exists()


def test_adaptive_finalize_stale_base_returns_stable_cli_failure_without_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reviewed_dir = tmp_path / "spec_finalize_reviewed"
    reviewed_dir.mkdir()
    attachment = reviewed_dir / review_cli.ATTACHMENT_FILENAME
    attachment.write_text("{}\n", encoding="utf-8")

    def stale_base(_path: Path) -> tuple[dict[str, object], Path]:
        raise pilot_contract.CreativePilotContractError(
            "adaptive_base_drift: current origin/main advanced"
        )

    monkeypatch.setattr(review_cli, "_validate_attachment_artifacts", stale_base)
    assert review_cli.main(["finalize", "--attachment", str(attachment)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "FAIL: adaptive_base_drift: current origin/main advanced\n"
    assert not (reviewed_dir / review_cli.BUNDLE_FILENAME).exists()
    assert not (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).exists()


def test_adaptive_layout_accepts_only_retained_pre_finalize_directories(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="adaptive-retained-layout")
    retained_name = ".spec_finalize_reviewed.0123456789abcdef.pre-finalize"
    retained_path = output_dir / retained_name
    try:
        retained_path.mkdir()
        allowed = {path.name for path in output_dir.iterdir() if path.name != retained_name}
        review_cli._reject_unexpected_entries(
            output_dir,
            allowed=allowed,
            label="adaptive resume",
            allow_retained_pre_finalize=True,
        )

        retained_path.rmdir()
        retained_path.write_text("not a directory\n", encoding="utf-8")
        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="retained pre-finalize artifact.*must be directories",
        ):
            review_cli._reject_unexpected_entries(
                output_dir,
                allowed=allowed,
                label="adaptive resume",
                allow_retained_pre_finalize=True,
            )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_rejects_prepared_child_symlink_before_read(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="prepared-child-symlink")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
        spec_prepare = output_dir / "spec_prepare"
        source_packet_path = spec_prepare / "source_packet.json"
        symlink_target = tmp_path / "source_packet.json"
        symlink_target.write_text(source_packet_path.read_text(encoding="utf-8"), encoding="utf-8")
        source_packet_path.unlink()
        source_packet_path.symlink_to(symlink_target)

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "spec_prepare contains symlink artifact(s): source_packet.json" in captured.err
        assert not (output_dir / "spec_finalize_reviewed").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_entry_scan_fails_closed_when_child_disappears_after_listing(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="entry-disappearance")
    try:
        spec_prepare = output_dir / "spec_prepare"
        (spec_prepare / "vanish").write_text("{}", encoding="utf-8")
        (spec_prepare / "evil").write_text("{}", encoding="utf-8")
        real_stat = review_cli.os.stat

        def disappear_on_stat(
            path: Any,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            if path == "vanish":
                raise FileNotFoundError("simulated child disappearance")
            return real_stat(path, *args, **kwargs)

        monkeypatch.setattr(review_cli.os, "stat", disappear_on_stat)
        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="changed during inspection",
        ):
            review_cli._reject_unexpected_entries(
                spec_prepare,
                allowed=set(PREPARE_FILENAMES),
                label="spec_prepare",
            )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_reviewed_run_creation_pins_parent_across_path_swap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    detached = bridge_dir.with_name(f"{bridge_dir.name}-detached")
    outside = tmp_path / "outside"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    real_open_parent = review_cli.creative_code_spec_pipeline._open_pinned_parent
    swapped = False
    parent_fd = -1
    reviewed_fd = -1
    try:
        bridge_dir.mkdir(parents=True)
        outside.mkdir()

        def swap_after_parent_open(*args: Any, **kwargs: Any) -> tuple[int, str, Path]:
            nonlocal swapped
            result = real_open_parent(*args, **kwargs)
            if not swapped:
                swapped = True
                bridge_dir.rename(detached)
                bridge_dir.symlink_to(outside, target_is_directory=True)
            return result

        monkeypatch.setattr(
            review_cli.creative_code_spec_pipeline,
            "_open_pinned_parent",
            swap_after_parent_open,
        )
        parent_fd, reviewed_fd, identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )
        assert swapped
        assert (detached / staging_name).is_dir()
        assert not (detached / review_contract.REVIEWED_RUN_DIRNAME).exists()
        assert not (outside / review_contract.REVIEWED_RUN_DIRNAME).exists()
        quarantine_name = review_cli._quarantine_pinned_reviewed_run(
            parent_fd,
            name=staging_name,
            expected_identity=identity,
        )
        assert not (detached / staging_name).exists()
        assert (detached / quarantine_name).is_dir()
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        if bridge_dir.is_symlink():
            bridge_dir.unlink()
        shutil.rmtree(detached, ignore_errors=True)
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_run_cleanup_pins_original_parent_across_path_swap(
    tmp_path: Path,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    detached = bridge_dir.with_name(f"{bridge_dir.name}-detached")
    outside = tmp_path / "outside"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    parent_fd = -1
    reviewed_fd = -1
    try:
        bridge_dir.mkdir(parents=True)
        outside.mkdir()
        parent_fd, reviewed_fd, identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )
        bridge_dir.rename(detached)
        bridge_dir.symlink_to(outside, target_is_directory=True)
        outside_reviewed = outside / review_contract.REVIEWED_RUN_DIRNAME
        outside_reviewed.mkdir()
        sentinel = outside_reviewed / "sentinel.json"
        sentinel.write_text("{}", encoding="utf-8")

        quarantine_name = review_cli._quarantine_pinned_reviewed_run(
            parent_fd,
            name=staging_name,
            expected_identity=identity,
        )

        assert not (detached / staging_name).exists()
        assert (detached / quarantine_name).is_dir()
        assert sentinel.read_text(encoding="utf-8") == "{}"
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        if bridge_dir.is_symlink():
            bridge_dir.unlink()
        shutil.rmtree(detached, ignore_errors=True)
        shutil.rmtree(bridge_dir, ignore_errors=True)


@pytest.mark.parametrize("failure_point", ["stat", "open", "open_persistent", "fstat"])
def test_reviewed_run_creation_cleans_exact_directory_after_post_mkdir_failure(
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    try:
        bridge_dir.mkdir(parents=True)
        if failure_point == "stat":
            real_stat = review_cli.os.stat
            fail_next_stat = True

            def fail_created_stat(*args: Any, **kwargs: Any) -> Any:
                nonlocal fail_next_stat
                path = args[0] if args else kwargs.get("path")
                if (
                    fail_next_stat
                    and isinstance(path, str)
                    and path.startswith(f".{review_contract.REVIEWED_RUN_DIRNAME}.")
                    and path.endswith(".staging")
                ):
                    fail_next_stat = False
                    raise OSError("simulated reviewed stat failure")
                return real_stat(*args, **kwargs)

            monkeypatch.setattr(review_cli.os, "stat", fail_created_stat)
        elif failure_point in {"open", "open_persistent"}:
            real_open = review_cli.os.open
            fail_next_open = True

            def fail_reviewed_open(
                path: Any,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal fail_next_open
                if (
                    isinstance(path, str)
                    and path.startswith(f".{review_contract.REVIEWED_RUN_DIRNAME}.")
                    and path.endswith(".staging")
                    and dir_fd is not None
                    and (fail_next_open or failure_point == "open_persistent")
                ):
                    if failure_point == "open":
                        fail_next_open = False
                    raise OSError(errno.EMFILE, "simulated descriptor exhaustion")
                return real_open(path, flags, mode, dir_fd=dir_fd)

            monkeypatch.setattr(review_cli.os, "open", fail_reviewed_open)
        else:
            real_fstat = review_cli.os.fstat
            fail_next = True

            def fail_reviewed_fstat(descriptor: int) -> Any:
                nonlocal fail_next
                if fail_next:
                    fail_next = False
                    raise OSError("simulated reviewed fstat failure")
                return real_fstat(descriptor)

            monkeypatch.setattr(review_cli.os, "fstat", fail_reviewed_fstat)

        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="could not be created safely",
        ):
            review_cli._create_pinned_reviewed_run(reviewed)
        staging_paths = list(bridge_dir.glob(f".{review_contract.REVIEWED_RUN_DIRNAME}.*.staging"))
        retained_paths = list(bridge_dir.glob(f".{review_contract.REVIEWED_RUN_DIRNAME}.*.failed"))
        if failure_point == "stat":
            assert len(staging_paths) == 1
            assert retained_paths == []
        else:
            assert staging_paths == []
            assert len(retained_paths) == 1
        assert not reviewed.exists()
    finally:
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_run_creation_rejects_entry_swap_after_identity_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    detached = bridge_dir / "detached-created"
    real_open = review_cli.os.open
    swapped = False
    try:
        bridge_dir.mkdir(parents=True)

        def swap_before_reviewed_open(
            path: Any,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            nonlocal swapped
            if (
                isinstance(path, str)
                and path.startswith(f".{review_contract.REVIEWED_RUN_DIRNAME}.")
                and path.endswith(".staging")
                and dir_fd is not None
                and not swapped
            ):
                swapped = True
                staging_path = bridge_dir / path
                staging_path.rename(detached)
                staging_path.mkdir()
            return real_open(path, flags, mode, dir_fd=dir_fd)

        monkeypatch.setattr(review_cli.os, "open", swap_before_reviewed_open)
        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="identity changed",
        ):
            review_cli._create_pinned_reviewed_run(reviewed)
        assert swapped
        assert detached.is_dir()
        assert not reviewed.exists()
        assert len(list(bridge_dir.glob(f".{reviewed.name}.*.staging"))) == 1
    finally:
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_run_stat_capture_failure_never_deletes_unowned_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    detached = bridge_dir / "detached-created"
    real_stat = review_cli.os.stat
    swapped = False
    try:
        bridge_dir.mkdir(parents=True)

        def swap_during_identity_capture(*args: Any, **kwargs: Any) -> Any:
            nonlocal swapped
            path = args[0] if args else kwargs.get("path")
            if (
                not swapped
                and isinstance(path, str)
                and path.startswith(f".{review_contract.REVIEWED_RUN_DIRNAME}.")
                and path.endswith(".staging")
            ):
                swapped = True
                staging_path = bridge_dir / path
                staging_path.rename(detached)
                staging_path.mkdir()
                raise OSError("simulated identity capture failure")
            return real_stat(*args, **kwargs)

        with monkeypatch.context() as context:
            context.setattr(review_cli.os, "stat", swap_during_identity_capture)
            with pytest.raises(
                review_cli.CreativeSpecificationSkepticReviewCliError,
                match="cleanup identity unavailable",
            ):
                review_cli._create_pinned_reviewed_run(reviewed)
        assert swapped
        assert detached.is_dir()
        assert not reviewed.exists()
        assert len(list(bridge_dir.glob(f".{reviewed.name}.*.staging"))) == 1
    finally:
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_run_publication_rejects_canonical_collision_without_overwrite() -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    parent_fd = -1
    reviewed_fd = -1
    try:
        bridge_dir.mkdir(parents=True)
        parent_fd, reviewed_fd, identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )
        reviewed.mkdir()
        sentinel = reviewed / "sentinel.json"
        sentinel.write_text("{}", encoding="utf-8")

        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="already exists",
        ):
            review_cli._publish_pinned_reviewed_run(
                parent_fd,
                staging_name=staging_name,
                destination_name=reviewed.name,
                expected_identity=identity,
            )

        assert sentinel.read_text(encoding="utf-8") == "{}"
        assert (bridge_dir / staging_name).is_dir()
        quarantine_name = review_cli._quarantine_pinned_reviewed_run(
            parent_fd,
            name=staging_name,
            expected_identity=identity,
        )
        assert (bridge_dir / quarantine_name).is_dir()
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_run_publication_rejects_staging_identity_swap() -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    detached = bridge_dir / "detached-staging"
    parent_fd = -1
    reviewed_fd = -1
    try:
        bridge_dir.mkdir(parents=True)
        parent_fd, reviewed_fd, identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )
        staging_path = bridge_dir / staging_name
        staging_path.rename(detached)
        staging_path.mkdir()

        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="staging identity changed",
        ):
            review_cli._publish_pinned_reviewed_run(
                parent_fd,
                staging_name=staging_name,
                destination_name=reviewed.name,
                expected_identity=identity,
            )

        assert detached.is_dir()
        assert staging_path.is_dir()
        assert not reviewed.exists()
        quarantine_name = review_cli._quarantine_pinned_reviewed_run(
            parent_fd,
            name=detached.name,
            expected_identity=identity,
        )
        assert (bridge_dir / quarantine_name).is_dir()
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_run_quarantine_retains_children_without_path_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    parent_fd = -1
    reviewed_fd = -1
    try:
        bridge_dir.mkdir(parents=True)
        parent_fd, reviewed_fd, identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )
        review_cli._write_json_at(reviewed_fd, "owned.json", {"owned": True})

        def forbid_path_deletion(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("failure quarantine must not delete pathname entries")

        with monkeypatch.context() as context:
            context.setattr(review_cli.os, "unlink", forbid_path_deletion)
            context.setattr(review_cli.os, "rmdir", forbid_path_deletion)
            quarantine_name = review_cli._quarantine_pinned_reviewed_run(
                parent_fd,
                name=staging_name,
                expected_identity=identity,
            )

        retained_child = bridge_dir / quarantine_name / "owned.json"
        assert json.loads(retained_child.read_text(encoding="utf-8")) == {"owned": True}
        assert not (bridge_dir / staging_name).exists()
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_run_quarantine_preserves_unknown_directory_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    detached = bridge_dir / "detached-owned-staging"
    parent_fd = -1
    reviewed_fd = -1
    real_rename_noreplace = review_cli._kernel_rename_noreplace
    quarantine_name: str | None = None
    try:
        bridge_dir.mkdir(parents=True)
        parent_fd, reviewed_fd, identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )

        def swap_source_during_quarantine(
            directory_fd: int,
            source_name: str,
            destination_name: str,
            **kwargs: Any,
        ) -> None:
            nonlocal quarantine_name
            quarantine_name = destination_name
            review_cli.os.rename(
                source_name,
                detached.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            review_cli.os.mkdir(source_name, mode=0o700, dir_fd=directory_fd)
            real_rename_noreplace(
                directory_fd,
                source_name,
                destination_name,
                **kwargs,
            )

        monkeypatch.setattr(
            review_cli,
            "_kernel_rename_noreplace",
            swap_source_during_quarantine,
        )
        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="identity changed during quarantine",
        ):
            review_cli._quarantine_pinned_reviewed_run(
                parent_fd,
                name=staging_name,
                expected_identity=identity,
            )

        assert detached.is_dir()
        assert quarantine_name is not None
        assert (bridge_dir / quarantine_name).is_dir()
        assert not (bridge_dir / staging_name).exists()
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_artifact_write_failure_retains_temp_without_path_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    parent_fd = -1
    reviewed_fd = -1
    try:
        bridge_dir.mkdir(parents=True)
        parent_fd, reviewed_fd, _identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )
        real_fsync = review_cli.os.fsync
        fail_next_fsync = True

        def fail_file_fsync_once(descriptor: int) -> None:
            nonlocal fail_next_fsync
            if fail_next_fsync:
                fail_next_fsync = False
                raise OSError("simulated reviewed artifact fsync failure")
            real_fsync(descriptor)

        def forbid_unlink(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("failed reviewed artifacts must not be unlinked")

        with monkeypatch.context() as context:
            context.setattr(review_cli.os, "fsync", fail_file_fsync_once)
            context.setattr(review_cli.os, "unlink", forbid_unlink)
            with pytest.raises(
                review_cli.CreativeSpecificationSkepticReviewCliError,
                match="failure_artifact_retained=.*owned.json.*tmp",
            ):
                review_cli._write_json_at(reviewed_fd, "owned.json", {"owned": True})

        staging_dir = bridge_dir / staging_name
        retained_temps = list(staging_dir.glob(".owned.json.*.tmp"))
        assert len(retained_temps) == 1
        assert not (staging_dir / "owned.json").exists()
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_reviewed_artifact_publication_preserves_unknown_source_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_dir = review_cli.SPEC_BRIDGE_ROOT / f"pytest-{uuid.uuid4().hex}"
    reviewed = bridge_dir / review_contract.REVIEWED_RUN_DIRNAME
    parent_fd = -1
    reviewed_fd = -1
    detached_name = ".detached-owned-json"
    real_rename_noreplace = review_cli._kernel_rename_noreplace
    try:
        bridge_dir.mkdir(parents=True)
        parent_fd, reviewed_fd, _identity, staging_name = review_cli._create_pinned_reviewed_run(
            reviewed
        )

        def swap_temp_during_publication(
            directory_fd: int,
            source_name: str,
            destination_name: str,
            **kwargs: Any,
        ) -> None:
            review_cli.os.rename(
                source_name,
                detached_name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            replacement_fd = review_cli.os.open(
                source_name,
                review_cli.os.O_WRONLY | review_cli.os.O_CREAT | review_cli.os.O_EXCL,
                0o600,
                dir_fd=directory_fd,
            )
            review_cli.os.close(replacement_fd)
            real_rename_noreplace(
                directory_fd,
                source_name,
                destination_name,
                **kwargs,
            )

        with monkeypatch.context() as context:
            context.setattr(
                review_cli,
                "_kernel_rename_noreplace",
                swap_temp_during_publication,
            )
            with pytest.raises(
                review_cli.CreativeSpecificationSkepticReviewCliError,
                match="identity changed during publication",
            ):
                review_cli._write_json_at(reviewed_fd, "owned.json", {"owned": True})

        staging_dir = bridge_dir / staging_name
        assert (staging_dir / detached_name).is_file()
        assert (staging_dir / "owned.json").is_file()
    finally:
        review_cli.creative_code_spec_pipeline._close_descriptors(reviewed_fd, parent_fd)
        shutil.rmtree(bridge_dir, ignore_errors=True)


def test_finalize_directory_exchange_fails_closed_on_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as context:
        context.setattr(review_cli.sys, "platform", "unsupported")
        with pytest.raises(
            review_cli.CreativeSpecificationSkepticReviewCliError,
            match="requires kernel directory exchange",
        ):
            review_cli._kernel_rename_exchange(0, "source", "destination")


def test_attach_preserves_unknown_replacement_published_during_staging_swap(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="attach-publish-swap")
    reviews_path = _write_review_input(output_dir, _review_input(output_dir))
    reviewed_dir = output_dir / review_contract.REVIEWED_RUN_DIRNAME
    detached_name = ".detached-reviewed-staging"
    real_rename_noreplace = review_cli._kernel_rename_noreplace
    swapped = False

    def swap_staging_before_kernel_rename(
        parent_fd: int,
        source_name: str,
        destination_name: str,
        **kwargs: Any,
    ) -> None:
        nonlocal swapped
        if destination_name == review_contract.REVIEWED_RUN_DIRNAME and not swapped:
            swapped = True
            review_cli.os.rename(
                source_name,
                detached_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            review_cli.os.mkdir(source_name, mode=0o700, dir_fd=parent_fd)
        real_rename_noreplace(parent_fd, source_name, destination_name, **kwargs)

    monkeypatch.setattr(
        review_cli,
        "_kernel_rename_noreplace",
        swap_staging_before_kernel_rename,
    )
    try:
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
            == 1
        )
        captured = capsys.readouterr()
        assert "identity changed during publication" in captured.err
        assert swapped
        assert reviewed_dir.is_dir()
        assert (output_dir / detached_name).is_dir()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_fails_closed_when_bridge_parent_moves_before_reviewed_writes(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="attach-parent-move")
    detached = output_dir.with_name(f"{output_dir.name}-detached")
    reviews_path = _write_review_input(output_dir, _review_input(output_dir))
    real_write_json_at = review_cli._write_json_at
    moved = False

    def move_parent_before_first_write(
        directory_fd: int,
        filename: str,
        payload: Any,
    ) -> None:
        nonlocal moved
        if not moved:
            moved = True
            output_dir.rename(detached)
        real_write_json_at(directory_fd, filename, payload)

    monkeypatch.setattr(review_cli, "_write_json_at", move_parent_before_first_write)
    try:
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
            == 1
        )
        captured = capsys.readouterr()
        assert "reviewed finalize run canonical identity changed" in captured.err
        assert moved
        assert not output_dir.exists()
        assert not (detached / review_contract.REVIEWED_RUN_DIRNAME).exists()
    finally:
        if detached.exists() and not output_dir.exists():
            detached.rename(output_dir)
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_rejects_unexpected_sidecar_added_during_reviewed_writes(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="attach-extra-sidecar")
    reviews_path = _write_review_input(output_dir, _review_input(output_dir))
    reviewed_dir = output_dir / review_contract.REVIEWED_RUN_DIRNAME
    real_write_json_at = review_cli._write_json_at
    writes = 0

    def add_sidecar_after_writes(
        directory_fd: int,
        filename: str,
        payload: Any,
    ) -> None:
        nonlocal writes
        real_write_json_at(directory_fd, filename, payload)
        writes += 1
        if writes == 5:
            real_write_json_at(directory_fd, "unexpected.json", {})

    monkeypatch.setattr(review_cli, "_write_json_at", add_sidecar_after_writes)
    try:
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
            == 1
        )
        captured = capsys.readouterr()
        assert "exact initial artifact set" in captured.err
        assert not reviewed_dir.exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_parent_symlink_swap_during_reviewed_ref_is_stable_and_local(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="attach-ref-symlink-swap")
    detached = output_dir.with_name(f"{output_dir.name}-detached")
    outside = tmp_path / "outside"
    outside.mkdir()
    reviews_path = _write_review_input(output_dir, _review_input(output_dir))
    real_artifact_ref = review_cli._artifact_ref
    swapped = False

    def swap_parent_on_reviewed_ref(path: Path) -> str:
        nonlocal swapped
        if review_contract.REVIEWED_RUN_DIRNAME in path.parts and not swapped:
            swapped = True
            output_dir.rename(detached)
            output_dir.symlink_to(outside, target_is_directory=True)
        return real_artifact_ref(path)

    monkeypatch.setattr(review_cli, "_artifact_ref", swap_parent_on_reviewed_ref)
    try:
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
            == 1
        )
        captured = capsys.readouterr()
        assert "reviewed finalize run canonical identity changed" in captured.err
        assert "Traceback" not in captured.err
        assert swapped
        assert not (outside / review_contract.REVIEWED_RUN_DIRNAME).exists()
        assert not (detached / review_contract.REVIEWED_RUN_DIRNAME).exists()
    finally:
        if output_dir.is_symlink():
            output_dir.unlink()
        if detached.exists() and not output_dir.exists():
            detached.rename(output_dir)
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_rechecks_canonical_identity_after_exact_payload_snapshot(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="attach-late-parent-move")
    detached = output_dir.with_name(f"{output_dir.name}-detached")
    reviews_path = _write_review_input(output_dir, _review_input(output_dir))
    real_assert_exact = review_cli._assert_exact_reviewed_run_payloads
    moved = False

    def move_parent_after_exact_snapshot(*args: Any, **kwargs: Any) -> None:
        nonlocal moved
        real_assert_exact(*args, **kwargs)
        if not moved:
            moved = True
            output_dir.rename(detached)
            output_dir.mkdir()

    monkeypatch.setattr(
        review_cli,
        "_assert_exact_reviewed_run_payloads",
        move_parent_after_exact_snapshot,
    )
    try:
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
            == 1
        )
        captured = capsys.readouterr()
        assert "reviewed finalize run canonical identity changed" in captured.err
        assert moved
        assert not (detached / review_contract.REVIEWED_RUN_DIRNAME).exists()
        assert not (output_dir / review_contract.REVIEWED_RUN_DIRNAME).exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        if detached.exists():
            detached.rename(output_dir)
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_reviewed_child_symlink_before_read(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="reviewed-child-symlink")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        variants_path = reviewed_dir / "variants.json"
        symlink_target = tmp_path / "variants.json"
        symlink_target.write_text(variants_path.read_text(encoding="utf-8"), encoding="utf-8")
        variants_path.unlink()
        variants_path.symlink_to(symlink_target)

        exit_code = review_cli.main(
            ["validate", "--attachment", str(reviewed_dir / review_cli.ATTACHMENT_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reviewed finalize run contains symlink artifact(s): variants.json" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_hidden_reviewed_run_sidecar(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="reviewed-sidecar")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        _write_json(reviewed_dir / "unexpected.json", {"extra": True})

        exit_code = review_cli.main(
            ["validate", "--attachment", str(reviewed_dir / review_cli.ATTACHMENT_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reviewed finalize run contains unexpected artifact(s): unexpected.json" in (
            captured.err
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_relocated_reviewed_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="relocated-reviewed")
    relocated_parent = output_dir.parent / f"{output_dir.name}-relocated"
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment = validate_skeptic_review_attachment(
            _read_json(reviewed_dir / review_cli.ATTACHMENT_FILENAME)
        )
        relocated_dir = relocated_parent / "spec_finalize_reviewed"
        relocated_dir.mkdir(parents=True)
        for filename in (
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
        ):
            shutil.copyfile(reviewed_dir / filename, relocated_dir / filename)

        source = attachment["source"]
        normalized_reviews = _read_json(reviewed_dir / "skeptic_reviews.json")
        relocated_attachment = build_skeptic_review_attachment(
            bridge_id=source["bridge_id"],
            bridge_fingerprint=source["bridge_fingerprint"],
            bridge_ref=source["bridge_ref"],
            candidate_id=source["candidate_id"],
            candidate_fingerprint=source["candidate_fingerprint"],
            candidate_ref=source["candidate_ref"],
            metrics_id=source["metrics_id"],
            metrics_fingerprint=source["metrics_fingerprint"],
            metrics_ref=source["metrics_ref"],
            spec_prepare_ref=source["spec_prepare_ref"],
            source_packet_ref=source["source_packet_ref"],
            source_packet_fingerprint=source["source_packet_fingerprint"],
            variants_ref=source["variants_ref"],
            variants_fingerprint=source["variants_fingerprint"],
            pending_reviews_ref=source["pending_reviews_ref"],
            pending_reviews_fingerprint=source["pending_reviews_fingerprint"],
            context_pack_ref=source["context_pack_ref"],
            context_pack_fingerprint=source["context_pack_fingerprint"],
            reviewed_run_dir_ref=relocated_dir.relative_to(REPO_ROOT).as_posix(),
            reviewed_source_packet_ref=(relocated_dir / "source_packet.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            reviewed_variants_ref=(relocated_dir / "variants.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            reviewed_reviews_ref=(relocated_dir / "skeptic_reviews.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            reviewed_context_pack_ref=(relocated_dir / "context_pack.json")
            .relative_to(REPO_ROOT)
            .as_posix(),
            normalized_reviews=normalized_reviews,
            variant_count=attachment["coverage"]["variant_count"],
        )
        _write_json(relocated_dir / review_cli.ATTACHMENT_FILENAME, relocated_attachment)

        exit_code = review_cli.main(
            ["validate", "--attachment", str(relocated_dir / review_cli.ATTACHMENT_FILENAME)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reviewed_run_dir_ref must be the sibling of the source bridge artifact" in (
            captured.err
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(relocated_parent, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_noncanonical_source_bridge_ref(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="fake-bridge-ref")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment = validate_skeptic_review_attachment(_read_json(attachment_path))
        fake_bridge = output_dir / "fake_bridge.json"
        shutil.copyfile(output_dir / bridge_cli.BRIDGE_FILENAME, fake_bridge)
        fake_attachment = _rebuild_attachment(
            attachment,
            source_overrides={"bridge_ref": fake_bridge.relative_to(REPO_ROOT).as_posix()},
        )
        _write_json(attachment_path, fake_attachment)

        exit_code = review_cli.main(["validate", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert f"canonical {bridge_cli.BRIDGE_FILENAME}" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_recovered_attachment_for_unprepared_bridge(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="recovered-unprepared-bridge")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        bridge_path = output_dir / bridge_cli.BRIDGE_FILENAME
        bridge_payload = _read_json(bridge_path)
        bridge_payload["spec_prepare"]["prepared"] = False
        bridge_payload["spec_prepare"]["next_allowed_action"] = "prepare_specification"
        _write_json(bridge_path, bridge_payload)

        attachment_path = output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        exit_code = review_cli.main(["validate", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "prepared and waiting for agent_skeptic_review" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_noncanonical_source_spec_prepare_ref(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="staging-spec-prepare")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment = validate_skeptic_review_attachment(_read_json(attachment_path))
        staging_prepare = output_dir / "staging"
        shutil.copytree(output_dir / "spec_prepare", staging_prepare)
        staging_attachment = _rebuild_attachment(
            attachment,
            source_overrides={
                "spec_prepare_ref": staging_prepare.relative_to(REPO_ROOT).as_posix(),
                "source_packet_ref": (staging_prepare / "source_packet.json")
                .relative_to(REPO_ROOT)
                .as_posix(),
                "variants_ref": (staging_prepare / "variants.json")
                .relative_to(REPO_ROOT)
                .as_posix(),
                "pending_reviews_ref": (staging_prepare / "skeptic_reviews.json")
                .relative_to(REPO_ROOT)
                .as_posix(),
                "context_pack_ref": (staging_prepare / "context_pack.json")
                .relative_to(REPO_ROOT)
                .as_posix(),
            },
        )
        _write_json(attachment_path, staging_attachment)

        exit_code = review_cli.main(["validate", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "source spec_prepare ref does not match bridge" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_source_spec_prepare_sidecar(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="source-prepare-sidecar")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        _write_json(output_dir / "spec_prepare" / "raw_provider_output.json", {"raw": True})

        exit_code = review_cli.main(
            [
                "validate",
                "--attachment",
                str(output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert (
            "spec_prepare contains unexpected artifact(s): raw_provider_output.json" in captured.err
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_validate_rejects_attachment_coverage_mismatch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="coverage-mismatch")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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

        attachment_path = output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        attachment = validate_skeptic_review_attachment(_read_json(attachment_path))
        tampered_attachment = deepcopy(attachment)
        tampered_attachment["coverage"]["reject_review_count"] = 0
        _write_json(attachment_path, _refresh_attachment_identity(tampered_attachment))

        exit_code = review_cli.main(["validate", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "attachment coverage does not match reviewed artifacts" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_retains_partial_outputs_on_receipt_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-cleanup")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment_path = output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME

        def _fail_receipt(**_: Any) -> dict[str, Any]:
            raise CreativeSpecificationSkepticReviewError("synthetic receipt failure")

        def forbid_unlink(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("failed finalize artifacts must not be unlinked")

        with monkeypatch.context() as context:
            context.setattr(review_cli, "build_finalize_receipt", _fail_receipt)
            context.setattr(Path, "unlink", forbid_unlink)
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "synthetic receipt failure" in captured.err
        assert "failure_artifact_retained=" in captured.err
        reviewed_dir = output_dir / "spec_finalize_reviewed"
        assert reviewed_dir.is_dir()
        assert {path.name for path in reviewed_dir.iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
        assert list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize")) == []
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_lock_contention_preserves_canonical_reviewed_run(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-lock")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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

        def reject_lock(*args: Any, **kwargs: Any) -> None:
            raise BlockingIOError("simulated concurrent finalize")

        with monkeypatch.context() as context:
            context.setattr(review_cli.fcntl, "flock", reject_lock)
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reviewed finalize is already in progress" in captured.err
        assert reviewed_dir.is_dir()
        assert not (reviewed_dir / review_cli.BUNDLE_FILENAME).exists()
        assert not (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).exists()
        assert list(output_dir.glob(".spec_finalize_reviewed.*.failed")) == []

        exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
        assert (reviewed_dir / review_cli.BUNDLE_FILENAME).is_file()
        assert (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).is_file()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_parent_lock_serializes_directory_exchange(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-parent-lock")
    parent_fd = -1
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        parent_fd = review_cli.os.open(
            output_dir,
            review_cli.creative_code_spec_pipeline._directory_flags(),
        )
        review_cli.fcntl.flock(parent_fd, review_cli.fcntl.LOCK_EX | review_cli.fcntl.LOCK_NB)

        exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reviewed finalize is already in progress" in captured.err
        assert {path.name for path in reviewed_dir.iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
        assert list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize")) == []

        review_cli.fcntl.flock(parent_fd, review_cli.fcntl.LOCK_UN)
        review_cli.os.close(parent_fd)
        parent_fd = -1
        assert review_cli.main(["finalize", "--attachment", str(attachment_path)]) == 0
        capsys.readouterr()
        assert (reviewed_dir / review_cli.BUNDLE_FILENAME).is_file()
        assert (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).is_file()
    finally:
        if parent_fd >= 0:
            review_cli.fcntl.flock(parent_fd, review_cli.fcntl.LOCK_UN)
            review_cli.os.close(parent_fd)
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_revalidates_pinned_inputs_after_lock(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-post-lock-mutation")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        reviewed_reviews = reviewed_dir / "skeptic_reviews.json"
        real_flock = review_cli.fcntl.flock
        mutated = False

        def mutate_after_lock(descriptor: int, operation: int) -> None:
            nonlocal mutated
            real_flock(descriptor, operation)
            if not mutated and operation & review_cli.fcntl.LOCK_EX:
                mutated = True
                reviewed_reviews.write_text("{}\n", encoding="utf-8")

        with monkeypatch.context() as context:
            context.setattr(review_cli.fcntl, "flock", mutate_after_lock)
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "pinned reviewed skeptic_reviews.json changed after validation" in captured.err
        assert mutated
        assert reviewed_dir.is_dir()
        assert not (reviewed_dir / review_cli.BUNDLE_FILENAME).exists()
        assert not (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).exists()
        assert list(output_dir.glob(".spec_finalize_reviewed.*.failed")) == []
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_rejects_canonical_reviewed_directory_swap_after_lock(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-directory-swap")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        detached = output_dir / ".detached-reviewed-finalize"
        attachment_path = reviewed_dir / review_cli.ATTACHMENT_FILENAME
        real_flock = review_cli.fcntl.flock
        swapped = False

        def swap_canonical_after_lock(descriptor: int, operation: int) -> None:
            nonlocal swapped
            real_flock(descriptor, operation)
            if not swapped and operation & review_cli.fcntl.LOCK_EX:
                swapped = True
                reviewed_dir.rename(detached)
                reviewed_dir.mkdir()
                (reviewed_dir / "unknown.marker").write_text("unknown\n", encoding="utf-8")

        with monkeypatch.context() as context:
            context.setattr(review_cli.fcntl, "flock", swap_canonical_after_lock)
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reviewed finalize run canonical identity changed" in captured.err
        assert swapped
        assert (reviewed_dir / "unknown.marker").read_text(encoding="utf-8") == "unknown\n"
        assert detached.is_dir()
        assert not (detached / review_cli.BUNDLE_FILENAME).exists()
        assert not (detached / review_cli.FINALIZE_RECEIPT_FILENAME).exists()
        assert list(output_dir.glob(".spec_finalize_reviewed.*.failed")) == []
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_revalidates_outputs_at_terminal_input_seam(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-output-mutation")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        receipt_path = reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME
        real_read_inputs = review_cli._read_pinned_reviewed_inputs
        calls = 0

        def corrupt_receipt_before_terminal_read(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            if calls == 2:
                receipt_path.write_text("{}\n", encoding="utf-8")
            return real_read_inputs(*args, **kwargs)

        with monkeypatch.context() as context:
            context.setattr(
                review_cli,
                "_read_pinned_reviewed_inputs",
                corrupt_receipt_before_terminal_read,
            )
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert review_cli.FINALIZE_SUCCESS_OUTPUT not in captured.out
        assert calls == 2
        assert reviewed_dir.is_dir()
        assert receipt_path.read_text(encoding="utf-8") == "{}\n"
        retained_runs = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert len(retained_runs) == 1
        assert (retained_runs[0] / review_cli.FINALIZE_RECEIPT_FILENAME).is_file()
        assert (retained_runs[0] / review_cli.BUNDLE_FILENAME).is_file()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_revalidates_payloads_after_atomic_exchange(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="post-exchange-payload-mutation")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        real_exchange = review_cli._kernel_rename_exchange

        def mutate_bundle_after_exchange(
            parent_fd: int,
            source_name: str,
            destination_name: str,
        ) -> None:
            real_exchange(parent_fd, source_name, destination_name)
            (reviewed_dir / review_cli.BUNDLE_FILENAME).write_text("{}\n", encoding="utf-8")

        with monkeypatch.context() as context:
            context.setattr(review_cli, "_kernel_rename_exchange", mutate_bundle_after_exchange)
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert review_cli.FINALIZE_SUCCESS_OUTPUT not in captured.out
        assert "exchange_state=published" in captured.err
        assert (reviewed_dir / review_cli.BUNDLE_FILENAME).read_text(encoding="utf-8") == "{}\n"
        retained_runs = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert len(retained_runs) == 1
        assert {path.name for path in retained_runs[0].iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_rechecks_outputs_after_terminal_retained_read(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="terminal-retained-output-seam")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        bundle_path = reviewed_dir / review_cli.BUNDLE_FILENAME
        real_read_inputs = review_cli._read_pinned_reviewed_inputs
        calls = 0

        def mutate_bundle_after_retained_read(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal calls
            payload = real_read_inputs(*args, **kwargs)
            calls += 1
            if calls == 3:
                bundle_path.write_text("{}\n", encoding="utf-8")
            return payload

        with monkeypatch.context() as context:
            context.setattr(
                review_cli,
                "_read_pinned_reviewed_inputs",
                mutate_bundle_after_retained_read,
            )
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert review_cli.FINALIZE_SUCCESS_OUTPUT not in captured.out
        assert calls == 3
        assert bundle_path.read_text(encoding="utf-8") == "{}\n"
        assert "exchange_state=published" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_open_pinned_finalize_output_preserves_primary_and_close_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory_fd = os.open(tmp_path, os.O_RDONLY)
    try:
        with monkeypatch.context() as context:
            context.setattr(
                review_cli.creative_code_spec_pipeline,
                "_close_descriptors",
                lambda *_descriptors: OSError("injected close failure"),
            )
            with pytest.raises(
                review_cli.CreativeSpecificationSkepticReviewCliError,
                match=("No such file or directory.*cleanup_diagnostic=" ".*injected close failure"),
            ):
                review_cli._open_pinned_finalize_output(directory_fd, "missing.json")
    finally:
        os.close(directory_fd)


def test_finalize_rejects_bundle_mutation_between_terminal_output_reads(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-inter-output-mutation")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        real_read_output = review_cli._read_json_from_pinned_finalize_output
        reads: list[str] = []

        def corrupt_bundle_between_output_reads(file_fd: int, filename: str) -> Any:
            if filename == review_cli.FINALIZE_RECEIPT_FILENAME and reads == [
                review_cli.BUNDLE_FILENAME
            ]:
                staging_dirs = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
                assert len(staging_dirs) == 1
                (staging_dirs[0] / review_cli.BUNDLE_FILENAME).write_text("{}\n", encoding="utf-8")
            payload = real_read_output(file_fd, filename)
            reads.append(filename)
            return payload

        with monkeypatch.context() as context:
            context.setattr(
                review_cli,
                "_read_json_from_pinned_finalize_output",
                corrupt_bundle_between_output_reads,
            )
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert review_cli.FINALIZE_SUCCESS_OUTPUT not in captured.out
        assert reads[:2] == [
            review_cli.BUNDLE_FILENAME,
            review_cli.FINALIZE_RECEIPT_FILENAME,
        ]
        assert reviewed_dir.is_dir()
        assert not (reviewed_dir / review_cli.BUNDLE_FILENAME).exists()
        retained_runs = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert len(retained_runs) == 1
        assert (retained_runs[0] / review_cli.BUNDLE_FILENAME).read_text(encoding="utf-8") == "{}\n"
        assert (retained_runs[0] / review_cli.FINALIZE_RECEIPT_FILENAME).is_file()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_exchange_failure_preserves_canonical_and_staged_evidence(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-exchange-failure")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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

        def fail_exchange(*args: Any, **kwargs: Any) -> None:
            raise review_cli.CreativeSpecificationSkepticReviewCliError(
                "simulated atomic exchange failure"
            )

        with monkeypatch.context() as context:
            context.setattr(review_cli, "_kernel_rename_exchange", fail_exchange)
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert review_cli.FINALIZE_SUCCESS_OUTPUT not in captured.out
        assert "simulated atomic exchange failure" in captured.err
        assert "exchange_state=not_published" in captured.err
        assert reviewed_dir.is_dir()
        assert {path.name for path in reviewed_dir.iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
        retained_runs = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert len(retained_runs) == 1
        assert {path.name for path in retained_runs[0].iterdir()} == set(
            review_cli.REVIEWED_RUN_FILENAMES
        )
        assert (retained_runs[0] / review_cli.BUNDLE_FILENAME).is_file()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_exchange_preserves_unknown_canonical_replacement(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-terminal-canonical-swap")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        detached = output_dir / ".detached-terminal-reviewed"
        attachment_path = reviewed_dir / review_cli.ATTACHMENT_FILENAME
        real_assert_identity = review_cli._assert_canonical_reviewed_run_identity
        identity_checks = 0

        def swap_canonical_after_composite_identity(*args: Any, **kwargs: Any) -> None:
            nonlocal identity_checks
            identity_checks += 1
            real_assert_identity(*args, **kwargs)
            if identity_checks == 2:
                reviewed_dir.rename(detached)
                reviewed_dir.mkdir()
                (reviewed_dir / "unknown.marker").write_text("unknown\n", encoding="utf-8")

        with monkeypatch.context() as context:
            context.setattr(
                review_cli,
                "_assert_canonical_reviewed_run_identity",
                swap_canonical_after_composite_identity,
            )
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert review_cli.FINALIZE_SUCCESS_OUTPUT not in captured.out
        assert "reviewed finalize retained pre-finalize run identity changed" in captured.err
        assert "exchange_state=published" in captured.err
        assert identity_checks == 2
        assert (reviewed_dir / review_cli.BUNDLE_FILENAME).is_file()
        assert (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).is_file()
        assert not (detached / review_cli.BUNDLE_FILENAME).exists()
        retained_runs = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert len(retained_runs) == 1
        assert (retained_runs[0] / "unknown.marker").read_text(encoding="utf-8") == "unknown\n"
        assert list(output_dir.glob(".spec_finalize_reviewed.*.failed")) == []
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_exchange_preserves_unknown_staging_replacement(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-staging-source-swap")
    detached_staging_name = ".detached-finalize-staging"
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        real_exchange = review_cli._kernel_rename_exchange

        def swap_staging_inside_exchange(
            parent_fd: int,
            source_name: str,
            destination_name: str,
        ) -> None:
            review_cli.os.rename(
                source_name,
                detached_staging_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            review_cli.os.mkdir(source_name, mode=0o700, dir_fd=parent_fd)
            replacement_fd = review_cli.os.open(
                source_name,
                review_cli.creative_code_spec_pipeline._directory_flags(),
                dir_fd=parent_fd,
            )
            try:
                marker_fd = review_cli.os.open(
                    "unknown.marker",
                    review_cli.os.O_WRONLY | review_cli.os.O_CREAT | review_cli.os.O_EXCL,
                    0o600,
                    dir_fd=replacement_fd,
                )
                review_cli.os.close(marker_fd)
            finally:
                review_cli.os.close(replacement_fd)
            real_exchange(parent_fd, source_name, destination_name)

        with monkeypatch.context() as context:
            context.setattr(review_cli, "_kernel_rename_exchange", swap_staging_inside_exchange)
            exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert review_cli.FINALIZE_SUCCESS_OUTPUT not in captured.out
        assert "reviewed finalize published run identity changed" in captured.err
        assert "exchange_state=published" in captured.err
        assert (reviewed_dir / "unknown.marker").is_file()
        retained_runs = list(output_dir.glob(".spec_finalize_reviewed.*.pre-finalize"))
        assert len(retained_runs) == 1
        assert {path.name for path in retained_runs[0].iterdir()} == {
            "source_packet.json",
            "variants.json",
            "skeptic_reviews.json",
            "context_pack.json",
            review_cli.ATTACHMENT_FILENAME,
        }
        detached_staging = output_dir / detached_staging_name
        assert {path.name for path in detached_staging.iterdir()} == set(
            review_cli.REVIEWED_RUN_FILENAMES
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_preserves_preexisting_partial_outputs_without_quarantine(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="finalize-partial-existing")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        partial_bundle = reviewed_dir / review_cli.BUNDLE_FILENAME
        partial_bundle.write_text("{}\n", encoding="utf-8")

        exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "reviewed finalize outputs are partial" in captured.err
        assert reviewed_dir.is_dir()
        assert partial_bundle.read_text(encoding="utf-8") == "{}\n"
        assert not (reviewed_dir / review_cli.FINALIZE_RECEIPT_FILENAME).exists()
        assert list(output_dir.glob(".spec_finalize_reviewed.*.failed")) == []
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_receipt_rejects_inconsistent_selected_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="receipt-count-mismatch")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment_path = output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        assert review_cli.main(["finalize", "--attachment", str(attachment_path)]) == 0
        capsys.readouterr()
        receipt_path = output_dir / "spec_finalize_reviewed" / review_cli.FINALIZE_RECEIPT_FILENAME
        receipt = validate_finalize_receipt(_read_json(receipt_path))
        tampered_receipt = deepcopy(receipt)
        tampered_receipt["counts"]["selected_variant_count"] = 0

        with pytest.raises(CreativeSpecificationSkepticReviewError, match="selected_variant_id"):
            validate_finalize_receipt(_refresh_receipt_identity(tampered_receipt))
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_finalize_receipt_rejects_all_rejected_without_rejection_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="all-rejected-count-mismatch")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir, all_rejected=True))
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
        attachment_path = output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        assert review_cli.main(["finalize", "--attachment", str(attachment_path)]) == 0
        capsys.readouterr()
        receipt_path = output_dir / "spec_finalize_reviewed" / review_cli.FINALIZE_RECEIPT_FILENAME
        receipt = validate_finalize_receipt(_read_json(receipt_path))
        tampered_receipt = deepcopy(receipt)
        tampered_receipt["counts"]["rejected_variant_count"] = 0
        tampered_receipt["counts"]["rejection_record_count"] = 0

        with pytest.raises(CreativeSpecificationSkepticReviewError, match="when all rejected"):
            validate_finalize_receipt(_refresh_receipt_identity(tampered_receipt))
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


@pytest.mark.parametrize(
    ("field_name", "replacement_suffix"),
    [
        (
            "source_attachment_ref",
            "skeptic_review_attachment.json",
        ),
        (
            "bundle_ref",
            "creative_code_specification_bundle.json",
        ),
    ],
)
def test_finalize_receipt_refs_must_bind_to_reviewed_run(
    capsys: pytest.CaptureFixture[str],
    field_name: str,
    replacement_suffix: str,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix=f"receipt-ref-{field_name}")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment_path = output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        assert review_cli.main(["finalize", "--attachment", str(attachment_path)]) == 0
        capsys.readouterr()
        receipt_path = output_dir / "spec_finalize_reviewed" / review_cli.FINALIZE_RECEIPT_FILENAME
        receipt = validate_finalize_receipt(_read_json(receipt_path))
        tampered_receipt = deepcopy(receipt)
        tampered_receipt[field_name] = (
            "artifacts/orchestration/creative_code/spec_bridge/other-bridge/"
            f"spec_finalize_reviewed/{replacement_suffix}"
        )

        with pytest.raises(CreativeSpecificationSkepticReviewError, match="reviewed_run_dir_ref"):
            validate_finalize_receipt(_refresh_receipt_identity(tampered_receipt))
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


@pytest.mark.parametrize(
    ("case_slug", "mutator", "expected_error"),
    [
        (
            "overlong-text",
            lambda payload: payload["reviews"][0].update({"duplicate_reason": "x" * 513}),
            "at most 512 characters",
        ),
        (
            "too-many-blockers",
            lambda payload: payload["reviews"][0].update(
                {"blockers": [f"blocker_{index}" for index in range(11)]}
            ),
            "at most 10 items",
        ),
        (
            "too-many-unsafe-flags",
            lambda payload: payload["reviews"][0].update(
                {"unsafe_authority_flags": [f"flag_{index}" for index in range(11)]}
            ),
            "at most 10 items",
        ),
    ],
)
def test_review_input_validator_matches_schema_caps(
    capsys: pytest.CaptureFixture[str],
    case_slug: str,
    mutator: Callable[[dict[str, Any]], None],
    expected_error: str,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix=f"schema-caps-{case_slug}")
    try:
        payload = _review_input(output_dir, all_rejected=True)
        mutator(payload)

        with pytest.raises(CreativeSpecificationSkepticReviewError, match=expected_error):
            validate_agent_skeptic_reviews_input(payload)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


@pytest.mark.parametrize(
    ("case_slug", "mutator", "expected_error"),
    [
        (
            "missing-role",
            lambda payload: payload["reviews"].pop(),
            "cover every required reviewer",
        ),
        (
            "duplicate-role",
            lambda payload: payload["reviews"].append(deepcopy(payload["reviews"][0])),
            "must not repeat a reviewer",
        ),
        (
            "bad-decision",
            lambda payload: payload["reviews"][0].update({"decision": "maybe"}),
            "decision is unsupported",
        ),
        (
            "unsafe-path",
            lambda payload: payload["reviews"][0].update(
                {
                    "decision": "revise",
                    "required_revision": "Inspect /Users/example/.env before review.",
                }
            ),
            "local absolute paths",
        ),
        (
            "secret-token",
            lambda payload: payload["reviews"][0].update(
                {"blockers": ["ghp_12345678901234567890"]}
            ),
            "secret-shaped",
        ),
        (
            "stale-variants",
            lambda payload: payload.update({"variants_fingerprint": "sha256:" + "e" * 64}),
            "fingerprint_mismatch",
        ),
        (
            "wrong-role",
            lambda payload: payload["reviews"][0].update({"reviewer_role": "bug-hunter"}),
            "reviewer_role is not required",
        ),
    ],
)
def test_attach_rejects_bad_review_inputs(
    capsys: pytest.CaptureFixture[str],
    case_slug: str,
    mutator: Callable[[dict[str, Any]], None],
    expected_error: str,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix=f"bad-{case_slug}")
    try:
        payload = _review_input(output_dir)
        mutator(payload)
        reviews_path = _write_review_input(output_dir, payload)

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert expected_error in captured.err
        assert not (output_dir / "spec_finalize_reviewed").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_accepts_bounded_aggregate_blocker_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="aggregate-blockers")
    try:
        payload = _review_input(output_dir, all_rejected=True)
        for review in payload["reviews"]:
            review["blockers"] = [
                "skeptic_rejected_variant",
                "unsafe_layout",
                "missing_evidence",
                "needs_contract_sync",
            ]
        reviews_path = _write_review_input(output_dir, payload)

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
        attachment = validate_skeptic_review_attachment(
            _read_json(output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME)
        )
        assert attachment["coverage"]["blocker_count"] == 36
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_rejects_duplicate_json_keys(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="duplicate-json")
    try:
        reviews_path = output_dir / "agent_skeptic_reviews.json"
        reviews_path.write_text('{"schema_version":"1.0","schema_version":"1.0"}\n', "utf-8")

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "duplicate key: schema_version" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_rejects_tampered_candidate_before_writing_reviewed_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="candidate-tamper")
    try:
        candidate_path = output_dir / bridge_cli.CANDIDATE_FILENAME
        candidate = _read_json(candidate_path)
        candidate["fallback"] = "Tampered fallback without changing bridge fingerprint."
        _write_json(candidate_path, candidate)
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "candidate fingerprint does not match bridge" in captured.err
        assert not (output_dir / "spec_finalize_reviewed").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attach_rejects_symlink_reviewed_run(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="symlink-run")
    try:
        (output_dir / "spec_finalize_reviewed").symlink_to(tmp_path, target_is_directory=True)
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))

        exit_code = review_cli.main(
            [
                "attach",
                "--bridge",
                str(output_dir / bridge_cli.BRIDGE_FILENAME),
                "--reviews",
                str(reviews_path),
            ]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "must not traverse symlinks" in captured.err
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attachment_contract_rejects_unsafe_artifact_ref_component(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="bad-artifact-ref-component")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment = _read_json(
            output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        )
        attachment["source"]["bridge_ref"] = (
            "artifacts/orchestration/creative_code/spec_bridge/-bad/"
            f"{bridge_cli.BRIDGE_FILENAME}"
        )

        with pytest.raises(CreativeSpecificationSkepticReviewError, match="safe artifact"):
            validate_skeptic_review_attachment(attachment)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_attachment_contract_requires_exact_reviewer_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix="bad-reviewer-count")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment = _read_json(
            output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        )
        attachment["coverage"]["required_reviewer_count"] = 2

        with pytest.raises(CreativeSpecificationSkepticReviewError, match="must equal 3"):
            validate_skeptic_review_attachment(attachment)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


@pytest.mark.parametrize("count_key", ["variant_count", "review_count"])
def test_attachment_contract_rejects_zero_coverage_counts(
    capsys: pytest.CaptureFixture[str],
    count_key: str,
) -> None:
    output_dir, input_dir = _prepared_bridge(capsys, suffix=f"zero-{count_key}")
    try:
        reviews_path = _write_review_input(output_dir, _review_input(output_dir))
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
        attachment = _read_json(
            output_dir / "spec_finalize_reviewed" / review_cli.ATTACHMENT_FILENAME
        )
        attachment["coverage"][count_key] = 0

        with pytest.raises(CreativeSpecificationSkepticReviewError, match="between 1"):
            validate_skeptic_review_attachment(_refresh_attachment_identity(attachment))
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(input_dir, ignore_errors=True)


def test_reviewed_finalize_parser_has_no_combined_command() -> None:
    parser = review_cli.build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["attach-and-finalize"])


def test_reviewed_finalize_schemas_are_strict() -> None:
    for filename in SCHEMA_FILES:
        schema = json.loads(
            (REPO_ROOT / "docs/orchestration/contracts" / filename).read_text(encoding="utf-8")
        )
        assert schema["additionalProperties"] is False
        assert "attach-and-finalize" not in json.dumps(schema)
    review_input_schema = json.loads(
        (
            REPO_ROOT
            / "docs/orchestration/contracts/creative_specification_agent_skeptic_reviews.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    unsafe_text_pattern = review_input_schema["$defs"]["safe_text"]["allOf"][0]["not"]["pattern"]
    for blocked_phrase in (
        "Apply patch",
        "create branch",
        "open PR",
        "mark ready for review",
        "provider call",
        "Write to repository",
        "Commit changes",
        "open pr",
        "create pr",
    ):
        assert re.search(unsafe_text_pattern, blocked_phrase), blocked_phrase
    unsafe_token_pattern = review_input_schema["$defs"]["safe_token"]["not"]["pattern"]
    assert re.search(unsafe_token_pattern, "GHP_12345678901234567890")
    unsafe_path_pattern = review_input_schema["$defs"]["safe_text"]["allOf"][1]["not"]["pattern"]
    assert re.search(unsafe_path_pattern, "Inspect /Users/example/.env")
    attachment_schema = json.loads(
        (
            REPO_ROOT
            / "docs/orchestration/contracts/creative_specification_skeptic_review_attachment.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    attachment_artifact_pattern = attachment_schema["$defs"]["artifact_ref"]["pattern"]
    assert re.fullmatch(
        attachment_artifact_pattern,
        (
            "artifacts/orchestration/creative_code/spec_bridge/bridge-1/"
            "spec_finalize_reviewed/source_packet.json"
        ),
    )
    assert attachment_schema["$defs"]["reviewed_source_packet_ref"]["pattern"].endswith(
        "/spec_finalize_reviewed/source_packet\\.json$"
    )
    assert attachment_schema["$defs"]["reviewed_variants_ref"]["pattern"].endswith(
        "/spec_finalize_reviewed/variants\\.json$"
    )
    attachment_review_count_conditions = [
        branch["then"]["properties"]["review_count"]["const"]
        for branch in attachment_schema["$defs"]["coverage"]["allOf"]
    ]
    assert sorted(attachment_review_count_conditions) == [3, 6, 9, 12, 15]
    assert attachment_schema["$defs"]["coverage"]["properties"]["blocker_count"]["maximum"] == 150
    assert (
        attachment_schema["$defs"]["attachment_authority"]["properties"][
            "finalize_specification_bundle"
        ]["const"]
        is False
    )
    receipt_schema = json.loads(
        (
            REPO_ROOT
            / "docs/orchestration/contracts/creative_specification_finalize_receipt.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        receipt_schema["properties"]["source_attachment_ref"]["$ref"]
        == "#/$defs/reviewed_attachment_ref"
    )
    assert receipt_schema["properties"]["bundle_ref"]["$ref"] == "#/$defs/reviewed_bundle_ref"
    assert (
        "skeptic_review_attachment" in receipt_schema["$defs"]["reviewed_attachment_ref"]["pattern"]
    )
    assert (
        "creative_code_specification_bundle"
        in receipt_schema["$defs"]["reviewed_bundle_ref"]["pattern"]
    )
    selected_count_conditions = [
        branch["then"]["properties"]["counts"]["properties"]["selected_variant_count"]["const"]
        for branch in receipt_schema["allOf"]
        if "selected_variant_count"
        in branch["then"]["properties"].get("counts", {}).get("properties", {})
    ]
    assert sorted(selected_count_conditions) == [0, 1]
    rejected_count_conditions = [
        branch["then"]["properties"]["counts"]["properties"]["rejected_variant_count"]["const"]
        for branch in receipt_schema["allOf"]
        if "rejected_variant_count"
        in branch["then"]["properties"].get("counts", {}).get("properties", {})
    ]
    assert sorted(rejected_count_conditions) == [1, 2, 3, 4, 5]
    assert (
        receipt_schema["$defs"]["finalize_authority"]["properties"][
            "finalize_specification_bundle"
        ]["const"]
        is True
    )
    assert (
        receipt_schema["$defs"]["counts"]["properties"]["unresolved_blocker_count"]["maximum"]
        == 150
    )


def test_reviewed_finalize_modules_do_not_import_mutation_surfaces() -> None:
    banned_prefixes = (
        "app",
        "httpx",
        "requests",
        "slack",
        "github",
        "scripts.orchestration.creative_code_patch",
        "scripts.orchestration.creative_code_pr_promotion",
    )
    banned_exact = {
        "scripts.orchestration.experiment_runner",
        "scripts.orchestration.experiment_pipeline",
    }
    for module_path in (
        REPO_ROOT / "scripts/orchestration/creative_specification_skeptic_review.py",
        REPO_ROOT / "scripts/orchestration/creative_specification_skeptic_review_contract.py",
    ):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not [
            imported
            for imported in imports
            if imported in banned_exact or imported.startswith(banned_prefixes)
        ]

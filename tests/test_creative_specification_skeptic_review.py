from __future__ import annotations

import ast
from collections.abc import Callable
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import (
    creative_hypothesis_spec_bridge as bridge_cli,
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
        assert "source spec_prepare contains unexpected artifact(s): raw_provider_output.json" in (
            captured.err
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


def test_finalize_cleans_partial_outputs_on_receipt_failure(
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

        monkeypatch.setattr(review_cli, "build_finalize_receipt", _fail_receipt)
        exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "synthetic receipt failure" in captured.err
        assert not (output_dir / "spec_finalize_reviewed" / review_cli.BUNDLE_FILENAME).exists()
        assert not (
            output_dir / "spec_finalize_reviewed" / review_cli.FINALIZE_RECEIPT_FILENAME
        ).exists()

        monkeypatch.undo()
        exit_code = review_cli.main(["finalize", "--attachment", str(attachment_path)])
        captured = capsys.readouterr()
        assert exit_code == 0, captured.err
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

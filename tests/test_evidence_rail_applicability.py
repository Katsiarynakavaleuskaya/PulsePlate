"""Deterministic contract tests for packet-bound evidence-rail applicability."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
from pathlib import Path
from typing import Any, cast
import uuid

import pytest

import scripts.orchestration.evidence_rail_applicability as applicability
from scripts.orchestration.evidence_rail_applicability import (
    EvidenceRailApplicabilityError,
    RailTreatment,
    build_evidence_rail_applicability,
    canonical_evidence_rail_json,
    extract_applicability_signals,
    read_task_packet_snapshot,
    validate_evidence_rail_applicability,
)
from scripts.orchestration.design_lane_contract import (
    DesignLanePacketProjection,
    normalize_design_lane_packet_projection,
)
import scripts.orchestration.review_invariant_family_relations as invariant_relations
import scripts.orchestration.task_bootstrap as task_bootstrap


@pytest.fixture
def packet_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Give the strict reader an isolated fixed repository root."""

    monkeypatch.setattr(applicability, "REPO_ROOT", tmp_path)
    root = tmp_path / "artifacts/orchestration/task_packets"
    root.mkdir(parents=True)
    return root


def _base_packet(
    tmp_path: Path,
    *,
    goal: str = "Exercise evidence rail projection",
    task_class: str = "Orchestration",
    candidate_paths: list[str] | None = None,
    pr_phase: str = "pre_open",
    invariant_change_classes: list[str] | None = None,
    **design: Any,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        task_bootstrap.build_task_packet(
            goal=goal,
            task_class=task_class,
            candidate_paths=candidate_paths or ["core/example.py"],
            pr_phase=pr_phase,
            invariant_change_classes=invariant_change_classes or [],
            telemetry_path=tmp_path / "missing-telemetry.json",
            **design,
        ),
    )


def _write_packet(packet_root: Path, packet: dict[str, Any], *, salt: str) -> str:
    packet = copy.deepcopy(packet)
    identity = hashlib.sha256(
        (salt + json.dumps(packet, sort_keys=True, default=str)).encode("utf-8")
    ).hexdigest()[:12]
    packet["task_packet_id"] = identity
    path = packet_root / f"{identity}.json"
    path.write_text(
        json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return f"artifacts/orchestration/task_packets/{identity}.json"


def _snapshot(
    packet_root: Path,
    packet: dict[str, Any],
    *,
    salt: str,
) -> applicability.TaskPacketSnapshot:
    return read_task_packet_snapshot(_write_packet(packet_root, packet, salt=salt))


def _treatments(result: applicability.EvidenceRailApplicability) -> dict[str, Any]:
    return cast(dict[str, Any], result.to_mapping()["treatments"])


def _canonical_v2_packet() -> dict[str, Any]:
    input_root = (
        task_bootstrap.REPO_ROOT / "artifacts/orchestration/review_invariant_family_relations"
    )
    input_root.mkdir(parents=True, exist_ok=True)
    input_path = input_root / f"applicability-{uuid.uuid4().hex}.json"
    authority = {field: False for field in invariant_relations.AUTHORITY_FIELDS}
    input_path.write_bytes(
        json.dumps(
            {
                "schema_version": invariant_relations.SNAPSHOT_SCHEMA_VERSION,
                "universe_finding_ids": ["finding_a", "finding_b"],
                "families": [
                    {
                        "family_id": "family_alpha",
                        "finding_ids": ["finding_a", "finding_b"],
                    }
                ],
                **authority,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    try:
        return cast(
            dict[str, Any],
            task_bootstrap.build_task_packet(
                goal="Review a canonical repeated invariant family",
                task_class="Orchestration",
                candidate_paths=["core/example.py"],
                pr_phase="post_open_review",
                review_invariant_family_relations_input=input_path.relative_to(
                    task_bootstrap.REPO_ROOT
                ).as_posix(),
                telemetry_path=task_bootstrap.REPO_ROOT / "artifacts/missing-telemetry.json",
            ),
        )
    finally:
        input_path.unlink(missing_ok=True)


def test_actual_packet_shape_selects_exact_high_assurance_projection(
    packet_root: Path, tmp_path: Path
) -> None:
    """The admitted ORCH-RAIL packet is the expected I+S oracle."""

    packet = _base_packet(
        tmp_path,
        candidate_paths=["scripts/orchestration/evidence_rail_applicability.py"],
        invariant_change_classes=["parser", "validator", "guard", "authority"],
    )
    snapshot = _snapshot(packet_root, packet, salt="actual-oracle")
    result = build_evidence_rail_applicability(snapshot)

    assert extract_applicability_signals(snapshot) == applicability.ApplicabilitySignals(
        invariant_review=True,
        security_review=True,
        design_lane=False,
        docs_only=False,
    )
    assert result.rule_id == "higher_assurance"
    assert result.applicable_sidecar_rails == ("euler", "experiment_runner", "teleology")
    assert _treatments(result) == {
        "teleology": {
            "treatment": "full",
            "reasons": ["invariant_review_required", "security_review_required"],
        },
        "euler": {
            "treatment": "finite_review",
            "reasons": ["invariant_review_required", "security_review_required"],
        },
        "experiment_runner": {
            "treatment": "required",
            "reasons": ["runner_required_by_existing_pr_policy"],
        },
        "creative": {
            "treatment": "not_applicable",
            "reasons": ["creative_scope_not_selected"],
        },
    }


@pytest.mark.parametrize(
    ("candidate_paths", "invariant_classes", "expected_reasons"),
    [
        (["core/example.py"], ["guard"], ["invariant_review_required"]),
        ([".github/workflows/ci.yml"], [], ["security_review_required"]),
        (
            ["scripts/orchestration/check_merge_ready.py"],
            ["guard"],
            ["invariant_review_required", "security_review_required"],
        ),
    ],
)
def test_high_assurance_signal_combinations(
    packet_root: Path,
    tmp_path: Path,
    candidate_paths: list[str],
    invariant_classes: list[str],
    expected_reasons: list[str],
) -> None:
    packet = _base_packet(
        tmp_path,
        candidate_paths=candidate_paths,
        invariant_change_classes=invariant_classes,
    )
    result = build_evidence_rail_applicability(
        _snapshot(packet_root, packet, salt="high-" + "-".join(expected_reasons))
    )

    assert result.rule_id == "higher_assurance"
    assert _treatments(result)["teleology"]["reasons"] == expected_reasons
    assert _treatments(result)["euler"]["reasons"] == expected_reasons
    assert _treatments(result)["creative"]["reasons"] == ["creative_scope_not_selected"]


def test_design_packet_recommends_creative_but_never_sidecar(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Implement approved Figma screen",
        task_class="Design",
        candidate_paths=["docs/design/example.md"],
        design_source="code_native_brief",
        target_surface="web-home",
        task_mode="implement",
        code_native_design_brief_path="docs/design/example.md",
    )
    result = build_evidence_rail_applicability(_snapshot(packet_root, packet, salt="design"))

    assert result.rule_id == "design"
    assert _treatments(result)["creative"] == {
        "treatment": "recommend",
        "reasons": ["design_lane_applicable"],
    }
    assert "creative" not in result.applicable_sidecar_rails


def test_public_design_packet_projection_is_frozen_and_packet_local(
    tmp_path: Path,
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Implement an approved code-native design",
        task_class="Design",
        candidate_paths=["docs/design/example.md"],
        design_source="code_native_brief",
        target_surface="web-home",
        task_mode="implement",
        code_native_design_brief_path="docs/design/example.md",
    )

    projection = normalize_design_lane_packet_projection(
        design_lane_mode=packet["design_lane_mode"],
        design_lane_contract=packet["design_lane_contract"],
        design_lane_enabled=packet["automation_flags"]["design_lane_enabled"],
    )

    assert projection == DesignLanePacketProjection(
        mode="implement",
        blockers=(),
        enabled=True,
        execution_ready=True,
    )
    with pytest.raises(FrozenInstanceError):
        setattr(projection, "mode", "read_only")


def test_execution_ready_design_contract_requires_exact_design_task_label(
    packet_root: Path,
    tmp_path: Path,
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Review an otherwise execution-ready design contract",
        task_class="Review",
        candidate_paths=["core/example.py"],
        design_source="code_native_brief",
        target_surface="web-home",
        task_mode="implement",
        code_native_design_brief_path="docs/design/example.md",
    )
    assert packet["skill_routing"]["task_classification"]["label"] == "review"

    result = build_evidence_rail_applicability(
        _snapshot(packet_root, packet, salt="ready-design-review-label")
    )

    assert result.rule_id == "conservative"
    assert _treatments(result)["creative"] == {
        "treatment": "not_applicable",
        "reasons": ["creative_scope_not_selected"],
    }


def test_design_packet_projection_rejects_noncanonical_and_contradictory_inputs(
    tmp_path: Path,
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Implement an approved code-native design",
        task_class="Design",
        candidate_paths=["docs/design/example.md"],
        design_source="code_native_brief",
        target_surface="web-home",
        task_mode="implement",
        code_native_design_brief_path="docs/design/example.md",
    )
    contract = packet["design_lane_contract"]
    variants = [
        ("implement", {**contract, "unexpected": "value"}, True),
        ("implement", {**contract, "target_surface": " web-home"}, True),
        ("implement", {**contract, "blockers": ["stale", "stale"]}, True),
        ("read_only", contract, True),
        ("implement", contract, False),
        (
            "implement",
            {**contract, "code_native_design_brief_required": False},
            True,
        ),
    ]

    for mode, candidate_contract, enabled in variants:
        with pytest.raises(ValueError):
            normalize_design_lane_packet_projection(
                design_lane_mode=mode,
                design_lane_contract=candidate_contract,
                design_lane_enabled=enabled,
            )


@pytest.mark.parametrize("control", ("\n", "\t", "\x7f"))
def test_design_text_control_rejection_matches_producer_and_projection(
    tmp_path: Path,
    control: str,
) -> None:
    invalid_target = f"web{control}home"
    with pytest.raises(ValueError) as producer_error:
        _base_packet(
            tmp_path,
            goal="Build a design packet with invalid text",
            task_class="Design",
            candidate_paths=["docs/design/example.md"],
            design_source="code_native_brief",
            target_surface=invalid_target,
            task_mode="implement",
            code_native_design_brief_path="docs/design/example.md",
        )
    assert str(producer_error.value) == "design text contains control characters"
    assert invalid_target not in str(producer_error.value)

    packet = _base_packet(
        tmp_path,
        goal="Build a canonical design packet",
        task_class="Design",
        candidate_paths=["docs/design/example.md"],
        design_source="code_native_brief",
        target_surface="web-home",
        task_mode="implement",
        code_native_design_brief_path="docs/design/example.md",
    )
    invalid_contract = {
        **packet["design_lane_contract"],
        "target_surface": invalid_target,
    }
    with pytest.raises(ValueError) as projection_error:
        normalize_design_lane_packet_projection(
            design_lane_mode=packet["design_lane_mode"],
            design_lane_contract=invalid_contract,
            design_lane_enabled=packet["automation_flags"]["design_lane_enabled"],
        )
    assert str(projection_error.value) == "design text contains control characters"
    assert invalid_target not in str(projection_error.value)


def test_design_text_normalization_preserves_unicode_and_internal_spaces(
    tmp_path: Path,
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Build a Unicode design packet",
        task_class="Design",
        candidate_paths=["docs/design/example.md"],
        design_source="code_native_brief",
        target_surface="  web.Главная experience  ",
        task_mode="implement",
        code_native_design_brief_path="  docs/design/Главный экран.md  ",
    )

    contract = packet["design_lane_contract"]
    assert contract["target_surface"] == "web.Главная experience"
    assert contract["code_native_design_brief_path"] == "docs/design/Главный экран.md"
    assert normalize_design_lane_packet_projection(
        design_lane_mode=packet["design_lane_mode"],
        design_lane_contract=contract,
        design_lane_enabled=packet["automation_flags"]["design_lane_enabled"],
    ) == DesignLanePacketProjection(
        mode="implement",
        blockers=(),
        enabled=True,
        execution_ready=True,
    )


def test_high_assurance_preempts_design_with_specific_reason(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Implement approved Figma workflow surface",
        task_class="Design",
        candidate_paths=[".github/workflows/design.yml"],
        design_source="code_native_brief",
        target_surface="web-home",
        task_mode="implement",
        code_native_design_brief_path="docs/design/example.md",
    )
    result = build_evidence_rail_applicability(
        _snapshot(packet_root, packet, salt="design-security")
    )

    assert result.rule_id == "higher_assurance"
    assert _treatments(result)["creative"]["reasons"] == [
        "higher_assurance_scope_preempts_creative"
    ]


def test_incomplete_or_read_only_design_does_not_recommend_creative(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Verify design reference",
        task_class="Design",
        candidate_paths=["README.md"],
        design_source="figma_design",
        target_surface="web-home",
        task_mode="verify",
        figma_lane_tool="figma_native",
    )
    result = build_evidence_rail_applicability(
        _snapshot(packet_root, packet, salt="blocked-design")
    )

    assert result.rule_id == "docs_only"
    assert _treatments(result)["creative"]["treatment"] == "not_applicable"


def test_docs_only_defaults_and_effective_additive_normalization(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(
        tmp_path,
        goal="Update a documentation contract",
        task_class="Documentation",
        candidate_paths=["README.md"],
    )
    snapshot = _snapshot(packet_root, packet, salt="docs")
    baseline = build_evidence_rail_applicability(snapshot)
    upgraded = build_evidence_rail_applicability(
        snapshot,
        additive_rails=("euler", "euler", "teleology", "experiment_runner"),
    )

    assert baseline.rule_id == "docs_only"
    assert baseline.applicable_sidecar_rails == ("experiment_runner", "teleology")
    assert _treatments(baseline)["teleology"]["treatment"] == "compact"
    assert _treatments(baseline)["euler"]["treatment"] == "not_applicable"
    assert upgraded.additive_rails == ("euler",)
    assert upgraded.applicable_sidecar_rails == (
        "euler",
        "experiment_runner",
        "teleology",
    )
    assert _treatments(upgraded)["euler"] == {
        "treatment": "finite_review",
        "reasons": ["manual_additive_upgrade"],
    }


def test_redundant_additive_flags_are_byte_identical_noops(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(tmp_path, candidate_paths=["core/example.py"])
    snapshot = _snapshot(packet_root, packet, salt="conservative")

    baseline = canonical_evidence_rail_json(build_evidence_rail_applicability(snapshot))
    redundant = canonical_evidence_rail_json(
        build_evidence_rail_applicability(
            snapshot,
            additive_rails=("teleology", "experiment_runner", "euler", "euler"),
        )
    )

    assert baseline == redundant


def test_post_open_v1_invariant_is_phase_stable_when_local_flag_is_false(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(
        tmp_path,
        candidate_paths=["core/example.py"],
        invariant_change_classes=["validator"],
        pr_phase="post_open_review",
    )
    assert packet["automation_flags"]["invariant_class_review_required"] is False

    signals = extract_applicability_signals(_snapshot(packet_root, packet, salt="post-open-v1"))

    assert signals.invariant_review is True


def test_valid_v2_repeated_family_is_phase_stable(packet_root: Path) -> None:
    packet = _canonical_v2_packet()
    assert (
        packet["invariant_review"]["schema_version"]
        == task_bootstrap.INVARIANT_REVIEW_V2_SCHEMA_VERSION
    )

    signals = extract_applicability_signals(_snapshot(packet_root, packet, salt="v2"))

    assert signals.invariant_review is True


def test_raw_goal_and_task_class_do_not_choose_treatments(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(tmp_path, candidate_paths=["core/example.py"])
    changed = copy.deepcopy(packet)
    changed["goal"] = "Figma security emergency prose that must not be reclassified"
    changed["task_class"] = "opaque future label"
    first = build_evidence_rail_applicability(_snapshot(packet_root, packet, salt="raw-a"))
    second = build_evidence_rail_applicability(_snapshot(packet_root, changed, salt="raw-b"))

    assert first.rule_id == second.rule_id == "conservative"
    assert first.treatments == second.treatments
    assert first.applicable_sidecar_rails == second.applicable_sidecar_rails
    assert first.task_packet_fingerprint != second.task_packet_fingerprint


def test_canonical_replay_and_cross_binding_are_exact(packet_root: Path, tmp_path: Path) -> None:
    packet = _base_packet(tmp_path, candidate_paths=["core/example.py"])
    snapshot = _snapshot(packet_root, packet, salt="replay")
    result = build_evidence_rail_applicability(snapshot)
    canonical = canonical_evidence_rail_json(result)

    assert validate_evidence_rail_applicability(canonical, snapshot) == result
    assert validate_evidence_rail_applicability(canonical + "\n", snapshot) == result
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        validate_evidence_rail_applicability(json.dumps(result.to_mapping(), indent=2), snapshot)

    forged = result.to_mapping()
    forged["task_packet_fingerprint"] = "sha256:" + "f" * 64
    forged_raw = json.dumps(forged, sort_keys=True, separators=(",", ":"))
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        validate_evidence_rail_applicability(forged_raw, snapshot)


def test_projection_rejects_authority_unknowns_and_unsupported_treatments(
    packet_root: Path, tmp_path: Path
) -> None:
    snapshot = _snapshot(
        packet_root,
        _base_packet(tmp_path, candidate_paths=["core/example.py"]),
        salt="forged",
    )
    baseline = build_evidence_rail_applicability(snapshot).to_mapping()
    variants = []
    authority = copy.deepcopy(baseline)
    authority["authority"]["merge_authority"] = True
    variants.append(authority)
    unknown_reason = copy.deepcopy(baseline)
    unknown_reason["treatments"]["creative"]["reasons"] = ["unknown"]
    variants.append(unknown_reason)
    enrollment = copy.deepcopy(baseline)
    enrollment["treatments"]["euler"]["treatment"] = "recommend_enrollment"
    variants.append(enrollment)
    extra = copy.deepcopy(baseline)
    extra["unexpected"] = False
    variants.append(extra)

    for variant in variants:
        raw = json.dumps(variant, sort_keys=True, separators=(",", ":"))
        with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
            validate_evidence_rail_applicability(raw, snapshot)


@pytest.mark.parametrize(
    "raw_path",
    (
        "",
        "/tmp/aaaaaaaaaaaa.json",
        "artifacts/orchestration/task_packets/../aaaaaaaaaaaa.json",
        "artifacts/orchestration/task_packets/nested/aaaaaaaaaaaa.json",
        "artifacts/orchestration/task_packets/AAAAAAAAAAAA.json",
        "artifacts/orchestration/task_packets/aaaaaaaaaaaa.txt",
    ),
)
def test_reader_rejects_noncanonical_packet_paths(packet_root: Path, raw_path: str) -> None:
    del packet_root
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot(raw_path)


@pytest.mark.parametrize(
    "raw",
    (
        b"",
        b"\xef\xbb\xbf{}",
        b"\xff",
        b"[]",
        b'{"schema_version":"3.1","task_packet_id":"aaaaaaaaaaaa",'
        b'"task_packet_id":"aaaaaaaaaaaa"}',
        b'{"schema_version":"3.1","task_packet_id":"aaaaaaaaaaaa","x":NaN}',
        b"{}{}",
    ),
)
def test_reader_rejects_strict_json_failures(packet_root: Path, raw: bytes) -> None:
    path = packet_root / "aaaaaaaaaaaa.json"
    path.write_bytes(raw)

    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/aaaaaaaaaaaa.json")


@pytest.mark.parametrize("overflow_number", ("1e999", "-1e999"))
def test_strict_json_parser_rejects_finite_overflow_numbers(overflow_number: str) -> None:
    raw = f'{{"value":{overflow_number}}}'.encode("ascii")

    with pytest.raises(EvidenceRailApplicabilityError) as error:
        applicability._strict_json_bytes(raw, limit=len(raw))
    assert error.value.category == "INVALID_INPUT"


def test_reader_rejects_excessive_depth_and_candidate_paths(
    packet_root: Path, tmp_path: Path
) -> None:
    deep = b"[" * 70 + b"]" * 70
    (packet_root / "aaaaaaaaaaaa.json").write_bytes(deep)
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/aaaaaaaaaaaa.json")

    bounded_packet = _base_packet(
        tmp_path,
        candidate_paths=[f"docs/item-{index}.md" for index in range(256)],
    )
    bounded_snapshot = _snapshot(packet_root, bounded_packet, salt="bounded-paths")
    assert len(bounded_snapshot.packet["candidate_paths"]) == 256

    producer_packet = _base_packet(
        tmp_path,
        candidate_paths=[f"docs/item-{index}.md" for index in range(257)],
    )
    assert len(producer_packet["candidate_paths"]) == 257
    raw_path = _write_packet(packet_root, producer_packet, salt="too-many-paths")
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot(raw_path)


def test_enabled_design_packet_rejects_missing_trigger_blocker(
    packet_root: Path,
    tmp_path: Path,
) -> None:
    producer_packet = _base_packet(
        tmp_path,
        goal="Reject a contradictory enabled design packet",
        task_class="Design",
        candidate_paths=["docs/design/example.md"],
        design_source="code_native_brief",
        target_surface="web-home",
        task_mode="verify",
        design_blockers=["missing_design_trigger"],
        code_native_design_brief_path="docs/design/example.md",
    )
    assert producer_packet["automation_flags"]["design_lane_enabled"] is True
    assert producer_packet["design_lane_contract"]["blockers"] == ["missing_design_trigger"]

    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        _snapshot(packet_root, producer_packet, salt="contradictory-missing-trigger")


def test_reader_rejects_file_symlink_hardlink_fifo_and_id_mismatch(
    packet_root: Path, tmp_path: Path
) -> None:
    packet = _base_packet(tmp_path, candidate_paths=["core/example.py"])
    valid_path = _write_packet(packet_root, packet, salt="file-kinds")
    valid = packet_root / Path(valid_path).name

    mismatch = json.loads(valid.read_text(encoding="utf-8"))
    mismatch["task_packet_id"] = "bbbbbbbbbbbb"
    mismatch_path = packet_root / "cccccccccccc.json"
    mismatch_path.write_text(json.dumps(mismatch), encoding="utf-8")
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/cccccccccccc.json")

    symlink = packet_root / "dddddddddddd.json"
    symlink.symlink_to(valid.name)
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/dddddddddddd.json")

    hardlink = packet_root / "eeeeeeeeeeee.json"
    os.link(valid, hardlink)
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/eeeeeeeeeeee.json")

    fifo = packet_root / "ffffffffffff.json"
    os.mkfifo(fifo)
    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/ffffffffffff.json")


def test_reader_rejects_directory_packet_path(packet_root: Path) -> None:
    (packet_root / "aaaaaaaaaaaa.json").mkdir()

    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/aaaaaaaaaaaa.json")


def test_reader_rejects_deterministic_pre_post_metadata_drift(
    packet_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _base_packet(tmp_path, candidate_paths=["core/example.py"])
    packet_path = _write_packet(packet_root, packet, salt="metadata-drift")
    real_fstat = applicability.os.fstat
    fstat_calls = 0

    def drifting_fstat(descriptor: int) -> os.stat_result:
        nonlocal fstat_calls
        metadata = real_fstat(descriptor)
        fstat_calls += 1
        if fstat_calls != 2:
            return metadata
        values = list(metadata)
        values[8] = metadata.st_mtime + 1
        return os.stat_result(values)

    monkeypatch.setattr(applicability.os, "fstat", drifting_fstat)

    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot(packet_path)
    assert fstat_calls == 2


def test_reader_rejects_deterministic_pathname_replacement(
    packet_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _base_packet(tmp_path, candidate_paths=["core/example.py"])
    packet_path = _write_packet(packet_root, packet, salt="pathname-replacement")
    packet_file = packet_root / Path(packet_path).name
    original_bytes = packet_file.read_bytes()
    real_stat = applicability.os.stat
    replaced = False

    def replacing_stat(path: str, *args: Any, **kwargs: Any) -> os.stat_result:
        nonlocal replaced
        if not replaced and path == packet_file.name and kwargs.get("dir_fd") is not None:
            packet_file.unlink()
            packet_file.write_bytes(original_bytes)
            replaced = True
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(applicability.os, "stat", replacing_stat)

    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot(packet_path)
    assert replaced is True


def test_reader_rejects_symlinked_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(applicability, "REPO_ROOT", tmp_path)
    alternate = tmp_path / "alternate/orchestration/task_packets"
    alternate.mkdir(parents=True)
    (tmp_path / "artifacts").symlink_to(tmp_path / "alternate", target_is_directory=True)

    with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/aaaaaaaaaaaa.json")


def test_reader_fails_closed_when_no_follow_is_unavailable(
    packet_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del packet_root
    monkeypatch.delattr(applicability.os, "O_NOFOLLOW")

    with pytest.raises(EvidenceRailApplicabilityError, match="STORAGE_UNAVAILABLE"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/aaaaaaaaaaaa.json")


def test_reader_reports_storage_unavailable_for_missing_safe_open_primitive(
    packet_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del packet_root

    def unavailable_open(*_args: Any, **_kwargs: Any) -> int:
        raise NotImplementedError

    monkeypatch.setattr(applicability.os, "open", unavailable_open)

    with pytest.raises(EvidenceRailApplicabilityError, match="STORAGE_UNAVAILABLE"):
        read_task_packet_snapshot("artifacts/orchestration/task_packets/aaaaaaaaaaaa.json")


def test_packet_projection_recomputes_security_docs_and_phase_flags(
    packet_root: Path, tmp_path: Path
) -> None:
    base = _base_packet(tmp_path, candidate_paths=["README.md"])
    forged_packets = []
    security = copy.deepcopy(base)
    security["automation_flags"]["security_review_required"] = True
    forged_packets.append(security)
    envelope = copy.deepcopy(base)
    envelope["skill_routing"]["envelope_mode_hint"] = "analysis"
    forged_packets.append(envelope)
    phase = copy.deepcopy(base)
    phase["automation_flags"]["invariant_class_review_required"] = True
    forged_packets.append(phase)
    design = copy.deepcopy(base)
    design["automation_flags"]["design_lane_enabled"] = True
    forged_packets.append(design)

    for index, forged in enumerate(forged_packets):
        path = _write_packet(packet_root, forged, salt=f"forged-packet-{index}")
        with pytest.raises(EvidenceRailApplicabilityError, match="INVALID_INPUT"):
            read_task_packet_snapshot(path)


def test_cli_errors_are_sanitized_and_do_not_echo_input(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sensitive_marker = "opaque-marker-outside-packet-root"

    result = applicability.main(["build", "--packet", sensitive_marker])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == "INVALID_INPUT\n"
    assert sensitive_marker not in captured.err


def test_public_treatment_enum_has_no_enrollment_or_runner_na_values() -> None:
    assert {item.value for item in RailTreatment} == {
        "full",
        "compact",
        "finite_review",
        "required",
        "recommend",
        "not_applicable",
    }

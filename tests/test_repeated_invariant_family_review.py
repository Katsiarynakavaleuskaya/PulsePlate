"""Bounded L2 consumer tests for repeated explicit invariant families."""

from __future__ import annotations

import json
import os
import socket
import traceback
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import scripts.orchestration.bootstrap_sync_policy as bootstrap_sync_policy
import scripts.orchestration.qoder_dispatch_bridge as qoder_dispatch_bridge
import scripts.orchestration.review_invariant_family_relations as relations
import scripts.orchestration.task_bootstrap as task_bootstrap

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = REPO_ROOT / "artifacts/orchestration/review_invariant_family_relations"
CONTRACT = (
    REPO_ROOT
    / "docs/orchestration/contracts/REPEATED_INVARIANT_FAMILY_ABSTRACTION_REVIEW_CONTRACT.md"
)


def _snapshot(*, repeated: bool = True) -> dict[str, object]:
    authority = {field: False for field in relations.AUTHORITY_FIELDS}
    return {
        "schema_version": relations.SNAPSHOT_SCHEMA_VERSION,
        "universe_finding_ids": ["finding_a", "finding_b", "finding_c", "unknown_d"],
        "families": [
            {
                "family_id": "family_alpha",
                "finding_ids": ["finding_a", "finding_b"] if repeated else ["finding_a"],
            },
            {"family_id": "family_beta", "finding_ids": ["finding_b"]},
            {
                "family_id": "family_gamma",
                "finding_ids": ["finding_b", "finding_c"] if repeated else ["finding_c"],
            },
        ],
        **authority,
    }


@contextmanager
def _relations_input(*, repeated: bool = True) -> Iterator[str]:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = INPUT_ROOT / f"pytest-{uuid.uuid4().hex}.json"
    path.write_bytes(
        json.dumps(_snapshot(repeated=repeated), separators=(",", ":")).encode("ascii")
    )
    try:
        yield path.relative_to(REPO_ROOT).as_posix()
    finally:
        path.unlink(missing_ok=True)


def _build(
    input_path: str | None = None,
    *,
    requested_agents: list[str] | None = None,
) -> dict[str, Any]:
    return task_bootstrap.build_task_packet(
        goal="Review repeated explicit invariant families",
        task_class="Orchestration",
        candidate_paths=["scripts/orchestration/task_bootstrap.py"],
        requested_agents=requested_agents or ["agent-coordinator"],
        review_invariant_family_relations_input=input_path,
        pr_phase="post_open_review",
    )


def test_repeated_family_input_projects_exact_v2_and_exact_role_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    real_process = relations.process_input_bytes

    def counted_process(raw: bytes) -> bytes:
        nonlocal calls
        calls += 1
        return real_process(raw)

    monkeypatch.setattr(task_bootstrap, "process_input_bytes", counted_process)
    with _relations_input() as input_path:
        packet = _build(input_path)

    assert calls == 1
    review = packet["invariant_review"]
    assert set(review) == task_bootstrap.INVARIANT_REVIEW_V2_FIELDS
    assert CONTRACT.relative_to(REPO_ROOT).as_posix() in packet["required_context"]
    assert review["schema_version"] == "invariant_review.v2"
    assert review["state"] == "required_pending"
    assert review["coverage_claim"] == "explicit_normalized_snapshot_membership_only"
    assert "change_classes" not in review
    assert "trigger_evidence" not in review
    assert review["required_roles"] == ["logic-agent", "philosophy-agent"]
    assert review["implementation_authority"] is False
    assert review["merge_authority"] is False
    assert task_bootstrap.INVARIANT_REVIEW_RECOMMENDED_RESOLUTIONS == (
        "bounded_object_fix",
        "family_fix",
        "mechanism_fix",
        "authority_rescope",
        "no_change_required",
        "unknown_requires_human",
    )
    family_repeat = review["family_repeat"]
    assert family_repeat["trigger_rule"] == "explicit_family_cardinality_gte_2"
    assert family_repeat["membership_source"] == "explicit_input_only"
    assert [row["family_id"] for row in family_repeat["repeated_families"]] == [
        "family_alpha",
        "family_gamma",
    ]
    assert family_repeat["unknown_findings_present"] is True
    repeated_ids = {"family_alpha", "family_gamma"}
    assert all(
        row["left_family_id"] in repeated_ids or row["right_family_id"] in repeated_ids
        for row in family_repeat["relations_touching_repeated_families"]
    )
    assert packet["role_agent_dispatch_contract"]["dispatch_role_order"] == [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]
    assert packet["role_agent_dispatch_contract"]["runtime_implementation_owners"] == []
    assert (
        "--implementation-owner"
        not in packet["role_agent_dispatch_contract"]["dispatch_manifest_command"]
    )


def test_cardinality_below_two_retains_ordinary_post_open_tail() -> None:
    with _relations_input(repeated=False) as input_path:
        packet = _build(input_path)

    review = packet["invariant_review"]
    assert review["schema_version"] == "invariant_review.v2"
    assert review["state"] == "not_required"
    assert review["required_roles"] == []
    assert review["family_repeat"]["repeated_families"] == []
    assert "dispatch_role_order" not in packet["role_agent_dispatch_contract"]
    bridge_roles = [
        packet["native_subagent_bridge"]["primary"]["repo_agent_slug"],
        *[row["repo_agent_slug"] for row in packet["native_subagent_bridge"]["secondary"]],
        packet["native_subagent_bridge"]["reviewer"]["repo_agent_slug"],
    ]
    assert bridge_roles[:3] == [
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
    ]


def test_no_input_preserves_exact_existing_v1_packet_and_identity() -> None:
    packet = _build()

    assert packet["task_packet_id"] == "54bddc0ef1ba"
    assert packet["invariant_review"] == {
        "schema_version": "invariant_review.v1",
        "state": "not_required",
        "change_classes": ["authority"],
        "trigger_evidence": [
            {
                "change_class": "authority",
                "source": "bounded_path_hint",
                "path": "scripts/orchestration/task_bootstrap.py",
            }
        ],
        "coverage_claim": "explicit_plus_bounded_positive_triggers_only",
        "required_roles": [],
        "boundary_classes": [
            "finite_closed_world",
            "bounded_surface",
            "delegated_recognizer",
            "open_world_stop",
        ],
        "required_output_fields": [
            "invariant_statement",
            "boundary_class",
            "canonical_sot",
            "completeness_claim",
            "counterexample_families",
            "fail_closed_behavior",
            "stop_condition",
            "residual_risk",
        ],
        "stop_condition": (
            "second_materially_novel_carrier_same_open_world_invariant_requires_rescope"
        ),
        "implementation_authority": False,
        "merge_authority": False,
    }
    assert packet["primary_agent"] == "qa-engineer-agent"
    assert packet["secondary_agents"] == [
        "bug-hunter",
        "security-auditor",
        "agent-coordinator",
        "cursor-specialist-agent",
    ]
    assert packet["reviewer"] == "architecture-specialist"
    assert packet["requested_agents"] == ["agent-coordinator"]
    assert packet["requested_agent_disposition"] == [
        {
            "agent": "agent-coordinator",
            "status": "honored_secondary",
            "reason": "Requested agent stayed honored in secondary after PR lifecycle synthesis.",
        }
    ]
    bridge = packet["native_subagent_bridge"]
    assert bridge["primary"]["repo_agent_slug"] == "qa-engineer-agent"
    assert [row["repo_agent_slug"] for row in bridge["secondary"]] == [
        "bug-hunter",
        "security-auditor",
        "agent-coordinator",
        "cursor-specialist-agent",
    ]
    assert bridge["advisory"] == []
    assert bridge["reviewer"]["repo_agent_slug"] == "architecture-specialist"
    dispatch = packet["role_agent_dispatch_contract"]
    assert "dispatch_role_order" not in dispatch
    assert dispatch["dispatch_manifest_command"] == (
        "python3 scripts/orchestration/role_dispatch_bridge.py --packet <packet> --pretty"
    )
    assert dispatch["runtime_implementation_owner_flags_required"] is False
    assert dispatch["runtime_implementation_owners"] == []
    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == [
        "agent-coordinator",
        "qa-engineer-agent",
        "bug-hunter",
        "security-auditor",
        "cursor-specialist-agent",
        "architecture-specialist",
    ]


def test_v2_identity_chooses_l2_binder_directly_from_independent_base_id() -> None:
    with _relations_input() as input_path:
        first = _build(input_path)
        replay = _build(input_path)

    candidate_paths = ["scripts/orchestration/task_bootstrap.py"]
    v1_decision = task_bootstrap.classify_invariant_review(
        candidate_paths=candidate_paths,
        explicit_classes=(),
    )
    assert v1_decision.fingerprint
    base_packet_id = task_bootstrap.compute_task_packet_id(
        goal="Review repeated explicit invariant families",
        task_class="Orchestration",
        domain=str(first["domain"]),
        candidate_paths=candidate_paths,
        requested_agents=["agent-coordinator"],
        pr_phase="post_open_review",
        design_fingerprint=task_bootstrap._design_fingerprint(
            design_lane_mode=str(first["design_lane_mode"]),
            design_lane_contract=first["design_lane_contract"],
        ),
        creative_learning_hints_fingerprint=first["creative_learning_hints"][
            "source_hints_fingerprint"
        ],
    )
    family_repeat = first["invariant_review"]["family_repeat"]
    expected_l2_id = bootstrap_sync_policy.compute_invariant_family_review_packet_id(
        goal="Review repeated explicit invariant families",
        task_class="Orchestration",
        domain=str(first["domain"]),
        candidate_paths=candidate_paths,
        requested_agents=["agent-coordinator"],
        pr_phase="post_open_review",
        design_lane_mode=str(first["design_lane_mode"]),
        design_lane_contract=first["design_lane_contract"],
        creative_learning_hints_fingerprint=first["creative_learning_hints"][
            "source_hints_fingerprint"
        ],
        creative_learning_hints_projection=first["creative_learning_hints"],
        recommended_skills=first["recommended_skills"],
        skill_routing=first["skill_routing"],
        artifact_fingerprint=family_repeat["artifact_fingerprint"],
        invariant_review_projection=first["invariant_review"],
        required_context=first["required_context"],
        primary_agent=first["primary_agent"],
        secondary_agents=first["secondary_agents"],
        reviewer=first["reviewer"],
        requested_agent_disposition=first["requested_agent_disposition"],
    )
    independently_framed_id = str(
        task_bootstrap.fingerprint_payload(
            {
                "base_task_packet_id": base_packet_id,
                "identity_schema": (bootstrap_sync_policy.INVARIANT_FAMILY_REVIEW_IDENTITY_SCHEMA),
                "artifact_fingerprint": family_repeat["artifact_fingerprint"],
                "trigger_rule": bootstrap_sync_policy.INVARIANT_FAMILY_REPEAT_TRIGGER_RULE,
                "creative_learning_hints_projection_fingerprint": (
                    task_bootstrap.fingerprint_payload(first["creative_learning_hints"])
                ),
                "invariant_review_projection_fingerprint": (
                    task_bootstrap.fingerprint_payload(first["invariant_review"])
                ),
                "required_context_projection_fingerprint": (
                    task_bootstrap.fingerprint_payload(first["required_context"])
                ),
                "recommended_skills_projection_fingerprint": (
                    task_bootstrap.fingerprint_payload(first["recommended_skills"])
                ),
                "skill_routing_projection_fingerprint": task_bootstrap.fingerprint_payload(
                    first["skill_routing"]
                ),
                "role_assignment_projection_fingerprint": task_bootstrap.fingerprint_payload(
                    {
                        "primary_agent": first["primary_agent"],
                        "secondary_agents": first["secondary_agents"],
                        "reviewer": first["reviewer"],
                        "requested_agent_disposition": first["requested_agent_disposition"],
                    }
                ),
            }
        )
    ).removeprefix("sha256:")[:12]

    assert first["task_packet_id"] == replay["task_packet_id"]
    assert first["task_packet_id"] == expected_l2_id
    assert first["task_packet_id"] == independently_framed_id
    assert len(first["task_packet_id"]) == 12


def test_v2_identity_binds_final_judgment_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activation = task_bootstrap.BootstrapLaneActivation(
        lane=task_bootstrap.REQUIRED_BOOTSTRAP_LANE,
        signal_terms=("repeated explicit invariant",),
        decision_mode=task_bootstrap.SUPPORTED_JUDGMENT_DECISION_MODE,
    )
    monkeypatch.setattr(
        task_bootstrap,
        "load_bootstrap_lane_activations",
        lambda: {task_bootstrap.REQUIRED_BOOTSTRAP_LANE: activation},
    )

    with _relations_input() as input_path:
        packet = _build(input_path)

    assert set(task_bootstrap.JUDGMENT_REQUIRED_CONTEXT_FILES).issubset(packet["required_context"])
    assert qoder_dispatch_bridge._parse_json_packet_roles(packet) == list(
        task_bootstrap.INVARIANT_FAMILY_REVIEW_ROLE_ORDER
    )


@pytest.mark.parametrize(
    ("goal", "task_class"),
    [("alpha\nbeta", "gamma"), ("alpha", "beta\ngamma")],
)
def test_v2_identity_rejects_control_character_delimiter_collisions(
    goal: str,
    task_class: str,
) -> None:
    with _relations_input() as input_path:
        with pytest.raises(ValueError, match="control characters"):
            task_bootstrap.build_task_packet(
                goal=goal,
                task_class=task_class,
                candidate_paths=["scripts/orchestration/task_bootstrap.py"],
                requested_agents=["agent-coordinator"],
                review_invariant_family_relations_input=input_path,
                pr_phase="post_open_review",
            )


def test_v2_identity_rejects_delimiter_collision_in_creative_fingerprint() -> None:
    with _relations_input() as input_path:
        packet = _build(input_path)

    family_repeat = packet["invariant_review"]["family_repeat"]
    with pytest.raises(ValueError, match="control characters"):
        bootstrap_sync_policy.compute_invariant_family_review_packet_id(
            goal="alpha",
            task_class="beta",
            domain=packet["domain"],
            candidate_paths=["gamma"],
            requested_agents=packet["requested_agents"],
            pr_phase=packet["pr_phase"],
            design_lane_mode=packet["design_lane_mode"],
            design_lane_contract=packet["design_lane_contract"],
            creative_learning_hints_fingerprint="delta\nepsilon",
            creative_learning_hints_projection=packet["creative_learning_hints"],
            recommended_skills=packet["recommended_skills"],
            skill_routing=packet["skill_routing"],
            artifact_fingerprint=family_repeat["artifact_fingerprint"],
            invariant_review_projection=packet["invariant_review"],
            required_context=packet["required_context"],
            primary_agent=packet["primary_agent"],
            secondary_agents=packet["secondary_agents"],
            reviewer=packet["reviewer"],
            requested_agent_disposition=packet["requested_agent_disposition"],
        )


def test_active_review_rejects_extra_requested_roles() -> None:
    with _relations_input() as input_path:
        with pytest.raises(ValueError, match="rejects extra requested agents"):
            _build(input_path, requested_agents=["agent-coordinator", "architecture-specialist"])


@pytest.mark.parametrize(
    "raw_path",
    [
        "/tmp/input.json",
        "artifacts/orchestration/review_invariant_family_relations/nested/input.json",
        "artifacts/orchestration/review_invariant_family_relations/input.txt",
        "artifacts/orchestration/review_invariant_family_relations/../input.json",
        "artifacts/orchestration/other/input.json",
    ],
)
def test_input_path_must_be_exact_repo_relative_direct_child_json(raw_path: str) -> None:
    with pytest.raises(ValueError, match="direct-child JSON"):
        _build(raw_path)


@pytest.mark.parametrize("pr_phase", ["none", "pre_open", "merge_ready"])
def test_input_is_limited_to_post_open_review(pr_phase: str) -> None:
    with pytest.raises(ValueError, match="requires --pr-phase post_open_review"):
        task_bootstrap.build_task_packet(
            goal="Review repeated families",
            task_class="Orchestration",
            candidate_paths=["README.md"],
            review_invariant_family_relations_input=(
                "artifacts/orchestration/review_invariant_family_relations/input.json"
            ),
            pr_phase=pr_phase,
        )


def test_input_is_incompatible_with_explicit_v1_change_classes() -> None:
    with pytest.raises(ValueError, match="incompatible with --invariant-change-class"):
        task_bootstrap.build_task_packet(
            goal="Review repeated families",
            task_class="Orchestration",
            candidate_paths=["scripts/orchestration/task_bootstrap.py"],
            invariant_change_classes=["guard"],
            review_invariant_family_relations_input=(
                "artifacts/orchestration/review_invariant_family_relations/input.json"
            ),
            pr_phase="post_open_review",
        )


def test_symlink_input_fails_closed() -> None:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    target = INPUT_ROOT / f"pytest-target-{uuid.uuid4().hex}.json"
    link = INPUT_ROOT / f"pytest-link-{uuid.uuid4().hex}.json"
    target.write_text(json.dumps(_snapshot()), encoding="utf-8")
    os.symlink(target.name, link)
    try:
        with pytest.raises(ValueError, match="could not be read safely"):
            _build(link.relative_to(REPO_ROOT).as_posix())
    finally:
        link.unlink(missing_ok=True)
        target.unlink(missing_ok=True)


def test_missing_input_fails_closed() -> None:
    missing = INPUT_ROOT / f"pytest-missing-{uuid.uuid4().hex}.json"

    with pytest.raises(ValueError, match="could not be read safely") as exc_info:
        _build(missing.relative_to(REPO_ROOT).as_posix())
    rendered = "".join(
        traceback.format_exception(
            type(exc_info.value), exc_info.value, exc_info.value.__traceback__
        )
    )
    assert exc_info.value.__cause__ is None
    assert missing.name not in rendered
    assert "Errno" not in rendered


def test_directory_input_fails_closed_as_non_regular() -> None:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    directory = INPUT_ROOT / f"pytest-directory-{uuid.uuid4().hex}.json"
    directory.mkdir()
    try:
        with pytest.raises(ValueError, match="must be a regular file"):
            _build(directory.relative_to(REPO_ROOT).as_posix())
    finally:
        directory.rmdir()


@pytest.mark.parametrize("nonregular_kind", ["fifo", "socket"])
def test_fifo_and_socket_inputs_fail_closed_with_nonblocking_open(
    monkeypatch: pytest.MonkeyPatch,
    nonregular_kind: str,
) -> None:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = INPUT_ROOT / f"n-{uuid.uuid4().hex[:8]}.json"
    unix_socket: socket.socket | None = None
    if nonregular_kind == "fifo":
        os.mkfifo(path, 0o600)
    else:
        unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        monkeypatch.chdir(REPO_ROOT)
        unix_socket.bind(path.relative_to(REPO_ROOT).as_posix())

    real_open = os.open
    final_open_seen = False

    def assert_nonblocking_open(
        opened_path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal final_open_seen
        if opened_path == path.name:
            final_open_seen = True
            assert flags & os.O_NONBLOCK
        return real_open(opened_path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(task_bootstrap.os, "open", assert_nonblocking_open)
    try:
        with pytest.raises(ValueError, match="regular file|could not be read safely"):
            task_bootstrap._read_invariant_family_relations_input(
                path.relative_to(REPO_ROOT).as_posix()
            )
        assert final_open_seen
    finally:
        if unix_socket is not None:
            unix_socket.close()
        path.unlink(missing_ok=True)


@pytest.mark.parametrize("missing_flag", ["O_NONBLOCK", "O_CLOEXEC"])
def test_missing_required_open_capability_fails_before_open(
    monkeypatch: pytest.MonkeyPatch,
    missing_flag: str,
) -> None:
    monkeypatch.delattr(task_bootstrap.os, missing_flag)

    def unexpected_open(*_args: object, **_kwargs: object) -> int:
        pytest.fail("os.open must not run without every required descriptor flag")

    monkeypatch.setattr(task_bootstrap.os, "open", unexpected_open)

    with pytest.raises(ValueError, match=rf"requires {missing_flag} support"):
        task_bootstrap._read_invariant_family_relations_input(
            "artifacts/orchestration/review_invariant_family_relations/input.json"
        )


def test_equal_size_rewrite_with_restored_mtime_fails_closed_on_ctime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _relations_input() as input_path:
        path = REPO_ROOT / input_path
        original_stat = path.stat()
        real_read = os.read
        rewritten = False

        def rewrite_after_read(file_descriptor: int, size: int) -> bytes:
            nonlocal rewritten
            chunk = real_read(file_descriptor, size)
            if not rewritten:
                rewritten = True
                original = path.read_bytes()
                replacement = original.replace(b"finding_a", b"finding_z", 1)
                assert len(replacement) == len(original)
                path.write_bytes(replacement)
                os.utime(
                    path,
                    ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
                )
            return chunk

        monkeypatch.setattr(task_bootstrap.os, "read", rewrite_after_read)

        with pytest.raises(ValueError, match="changed or exceeded"):
            _build(input_path)
        assert rewritten


def test_descriptor_cleanup_error_suppresses_untrusted_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_filename = "/private/operator/review-input.json"
    with _relations_input() as input_path:
        real_close = os.close

        def close_then_fail(file_descriptor: int) -> None:
            real_close(file_descriptor)
            raise OSError(5, "operator filesystem detail", secret_filename)

        monkeypatch.setattr(task_bootstrap.os, "close", close_then_fail)
        with pytest.raises(ValueError, match="descriptor cleanup failed") as exc_info:
            _build(input_path)

    rendered = "".join(
        traceback.format_exception(
            type(exc_info.value), exc_info.value, exc_info.value.__traceback__
        )
    )
    assert exc_info.value.__cause__ is None
    assert secret_filename not in rendered
    assert "Errno" not in rendered


def test_symlinked_fixed_root_component_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orchestration_root = tmp_path / "artifacts/orchestration"
    real_input_root = tmp_path / "real-input-root"
    orchestration_root.mkdir(parents=True)
    real_input_root.mkdir()
    (real_input_root / "input.json").write_text("{}", encoding="ascii")
    (orchestration_root / "review_invariant_family_relations").symlink_to(
        real_input_root, target_is_directory=True
    )
    monkeypatch.setattr(task_bootstrap, "REPO_ROOT", tmp_path)

    with pytest.raises(ValueError, match="could not be read safely"):
        task_bootstrap._read_invariant_family_relations_input(
            "artifacts/orchestration/review_invariant_family_relations/input.json"
        )


def test_limit_plus_one_input_fails_closed_before_l1() -> None:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = INPUT_ROOT / f"pytest-oversize-{uuid.uuid4().hex}.json"
    path.write_bytes(b"x" * (relations.MAX_STDIN_BYTES + 1))
    try:
        with pytest.raises(ValueError, match="exceeds the L1 bound"):
            _build(path.relative_to(REPO_ROOT).as_posix())
    finally:
        path.unlink(missing_ok=True)


def test_contract_freezes_consumer_boundary_and_outcome_vocabulary() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    for required in (
        "--review-invariant-family-relations-input",
        "explicit_family_cardinality_gte_2",
        "explicit_input_only",
        "no_change_required",
        "unknown_requires_human",
        "one joint abstraction pass",
        "one separate assessment record per repeated family",
        "at most one joint pass",
        "implementation remains blocked",
        "canonical source-of-truth conflict",
        "_read_invariant_family_relations_input",
        "_validate_invariant_review_v2",
    ):
        assert required.casefold() in normalized_text.casefold()
    assert not any(
        token.startswith("scripts/orchestration/") and token.rpartition(":")[2].isdigit()
        for token in text.replace("`", "").split()
    )
    assert "NOT-A-BUG" not in text

"""Bounded L2 consumer tests for repeated explicit invariant families."""

from __future__ import annotations

import json
import os
import socket
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

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


def _build(input_path: str | None = None, *, requested_agents: list[str] | None = None):
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
    implicit = _build()
    explicit_none = _build(None)

    assert implicit == explicit_none
    assert implicit["invariant_review"]["schema_version"] == "invariant_review.v1"


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
    )
    family_repeat = first["invariant_review"]["family_repeat"]
    expected_l2_id = task_bootstrap._bind_invariant_family_review_packet_id(
        base_packet_id,
        artifact_fingerprint=family_repeat["artifact_fingerprint"],
    )
    incorrectly_double_bound_id = task_bootstrap._bind_invariant_family_review_packet_id(
        task_bootstrap._bind_invariant_review_packet_id(
            base_packet_id,
            invariant_review_fingerprint=v1_decision.fingerprint,
        ),
        artifact_fingerprint=family_repeat["artifact_fingerprint"],
    )

    assert first["task_packet_id"] == replay["task_packet_id"]
    assert first["task_packet_id"] == expected_l2_id
    assert first["task_packet_id"] != incorrectly_double_bound_id
    assert len(first["task_packet_id"]) == 12


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

    with pytest.raises(ValueError, match="could not be read safely"):
        _build(missing.relative_to(REPO_ROOT).as_posix())


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

    for required in (
        "--review-invariant-family-relations-input",
        "explicit_family_cardinality_gte_2",
        "explicit_input_only",
        "no_change_required",
        "unknown_requires_human",
        "_read_invariant_family_relations_input",
        "_validate_invariant_review_v2",
    ):
        assert required in text
    assert not any(
        token.startswith("scripts/orchestration/") and token.rpartition(":")[2].isdigit()
        for token in text.replace("`", "").split()
    )
    assert "NOT-A-BUG" not in text

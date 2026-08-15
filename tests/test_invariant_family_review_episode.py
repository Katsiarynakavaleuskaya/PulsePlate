from __future__ import annotations

import copy
import errno
import fcntl
import json
import operator
import os
import socket
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts.orchestration import invariant_family_review_episode as episode

CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs/orchestration/contracts/INVARIANT_FAMILY_REVIEW_EPISODE_CONTRACT.md"
)


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _policy_block() -> dict[str, object]:
    text = CONTRACT.read_text(encoding="utf-8")
    start = text.index("POLICY_PROJECTION_BEGIN\n") + len("POLICY_PROJECTION_BEGIN\n")
    end = text.index("\nPOLICY_PROJECTION_END", start)
    return json.loads(text[start:end])


def _enrollment(
    pr_number: int = 17, *, episode_class: str = "prospective_primary"
) -> dict[str, object]:
    l2_digest = "b" * 64
    l1_hex = "c" * 64
    return {
        "schema_version": "invariant_family_review_episode.enrollment_input.v1",
        "episode_class": episode_class,
        "pull_request_number": pr_number,
        "trigger_observed_at": "2026-08-15T10:00:00Z",
        "enrollment_recorded_at": "2026-08-15T10:01:00Z",
        "material_head_sha": "a" * 40,
        "source": {
            "l2_task_packet_id": l2_digest[:12],
            "l2_task_packet_digest": l2_digest,
            "l1_artifact_fingerprint": f"sha256:{l1_hex}",
            "l1_idempotency_key": f"review-invariant-family-relations.v1:{l1_hex}",
            "trigger_rule": "explicit_family_cardinality_gte_2",
            "membership_source": "explicit_input_only",
        },
        "identity_classes": [
            {"identity_class_id": "class_b", "trigger_finding_id": "finding_b"},
            {"identity_class_id": "class_a", "trigger_finding_id": "finding_a"},
        ],
        "families": [
            {
                "family_key": "family_key_a",
                "trigger_family_id": "trigger_family_a",
                "trigger_identity_class_ids": ["class_b", "class_a"],
            }
        ],
    }


def _baseline(enrollment_ack: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": "invariant_family_review_episode.joint_pass_baseline_input.v1",
        "episode_digest": enrollment_ack["episode_digest"],
        "enrollment_receipt_digest": enrollment_ack["enrollment_receipt_digest"],
        "joint_pass_completed_at": "2026-08-15T10:02:00Z",
        "identity_classes": [
            {
                "identity_class_id": "class_a",
                "phase_bindings": [
                    {"phase": "trigger", "finding_id": "finding_a"},
                    {"phase": "joint_pass", "finding_id": "joint_a"},
                ],
            },
            {
                "identity_class_id": "class_b",
                "phase_bindings": [
                    {"phase": "trigger", "finding_id": "finding_b"},
                    {"phase": "joint_pass", "finding_id": "joint_b"},
                ],
            },
            {
                "identity_class_id": "class_c",
                "phase_bindings": [{"phase": "joint_pass", "finding_id": "joint_c"}],
            },
        ],
        "families": [
            {
                "family_key": "family_key_a",
                "joint_pass_family_id": "joint_family_a",
                "joint_pass_cumulative_identity_class_ids": [
                    "class_c",
                    "class_a",
                    "class_b",
                ],
                "recommended_resolution": "family_fix",
            }
        ],
    }


def _terminal_available(
    enrollment_ack: Mapping[str, object],
    baseline: Mapping[str, object],
    baseline_ack: Mapping[str, object],
    *,
    positive: bool = True,
    extra_trigger_digest: bool = False,
) -> dict[str, object]:
    identities: list[dict[str, object]] = [
        {
            "identity_class_id": "class_a",
            "phase_bindings": [
                {"phase": "trigger", "finding_id": "finding_a"},
                {"phase": "joint_pass", "finding_id": "joint_a"},
                {"phase": "terminal", "finding_id": "terminal_a"},
            ],
        },
        {
            "identity_class_id": "class_b",
            "phase_bindings": [
                {"phase": "trigger", "finding_id": "finding_b"},
                {"phase": "joint_pass", "finding_id": "joint_b"},
                {"phase": "terminal", "finding_id": "terminal_b"},
            ],
        },
        {
            "identity_class_id": "class_c",
            "phase_bindings": [
                {"phase": "joint_pass", "finding_id": "joint_c"},
                {"phase": "terminal", "finding_id": "terminal_c"},
            ],
        },
    ]
    cumulative = ["class_a", "class_b", "class_c"]
    if positive:
        identities.append(
            {
                "identity_class_id": "class_d",
                "phase_bindings": [{"phase": "terminal", "finding_id": "terminal_d"}],
            }
        )
        cumulative.append("class_d")
    observed = ["b" * 64]
    if extra_trigger_digest:
        observed.append("d" * 64)
    return {
        "schema_version": "invariant_family_review_episode.terminal_input.v1",
        "episode_digest": enrollment_ack["episode_digest"],
        "enrollment_receipt_digest": enrollment_ack["enrollment_receipt_digest"],
        "terminal_state": "merged",
        "terminal_event_at": "2026-08-15T10:03:00Z",
        "terminal_recorded_at": "2026-08-15T10:04:00Z",
        "terminal_material_head_sha": "d" * 40,
        "observed_l2_identity_digests": observed,
        "joint_pass": {
            "status": "completed_baseline_available",
            "baseline": copy.deepcopy(baseline),
            "joint_pass_baseline_digest": baseline_ack["joint_pass_baseline_digest"],
            "identity_classes": identities,
            "family_observations": [
                {
                    "status": "confirmed",
                    "reason": "same_scope_confirmed",
                    "family_key": "family_key_a",
                    "terminal_family_id": "terminal_family_a",
                    "terminal_cumulative_identity_class_ids": cumulative,
                }
            ],
        },
    }


def _report_request(as_of: str = "2026-08-15T10:05:00Z") -> dict[str, object]:
    return {
        "schema_version": "invariant_family_review_episode.report_request.v1",
        "cohort_as_of": as_of,
    }


def _terminal_without_available_baseline(
    enrollment_ack: Mapping[str, object], *, completed: bool
) -> dict[str, object]:
    joint_pass: dict[str, object]
    if completed:
        joint_pass = {
            "status": "completed_baseline_unavailable",
            "reason": "joint_pass_baseline_unavailable",
            "joint_pass_completed_at": "2026-08-15T10:02:00Z",
        }
    else:
        joint_pass = {
            "status": "not_completed",
            "reason": "not_completed_before_terminal",
        }
    return {
        "schema_version": "invariant_family_review_episode.terminal_input.v1",
        "episode_digest": enrollment_ack["episode_digest"],
        "enrollment_receipt_digest": enrollment_ack["enrollment_receipt_digest"],
        "terminal_state": "closed_unmerged",
        "terminal_event_at": "2026-08-15T10:03:00Z",
        "terminal_recorded_at": "2026-08-15T10:04:00Z",
        "terminal_material_head_sha": "d" * 40,
        "observed_l2_identity_digests": ["b" * 64],
        "joint_pass": joint_pass,
    }


class _Anchor:
    def __init__(self, path: Path) -> None:
        self.path = path
        flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
        self.fd = os.open(path, flags)

    def close(self) -> None:
        os.close(self.fd)


@pytest.fixture
def anchor(tmp_path: Path) -> _Anchor:
    value = _Anchor(tmp_path)
    try:
        yield value
    finally:
        value.close()


def _run(anchor: _Anchor, verb: str, document: Mapping[str, object]) -> dict[str, object]:
    return episode._run_operation(verb, copy.deepcopy(dict(document)), anchor.fd)


def _receipt_path(anchor: _Anchor, lane: str, digest: object) -> Path:
    return (
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes"
        / lane
        / str(digest)
        / "receipt.json"
    )


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="ascii"))


def test_contract_policy_projection_is_exact_and_recursively_frozen() -> None:
    thawed = _thaw(episode.POLICY_PROJECTION)
    contract_policy = _policy_block()
    assert thawed == contract_policy
    assert json.dumps(thawed, sort_keys=True, separators=(",", ":")) == json.dumps(
        contract_policy, sort_keys=True, separators=(",", ":")
    )
    assert episode.POLICY_PROJECTION["policy_version"] == (
        "invariant_family_review_episode.policy.v1"
    )
    assert isinstance(episode.POLICY_PROJECTION["schemas"], Mapping)
    assert isinstance(episode.POLICY_PROJECTION["authority_fields"], tuple)
    with pytest.raises(TypeError):
        operator.setitem(episode.POLICY_PROJECTION, "policy_version", "changed")


def test_policy_closes_authority_transport_and_public_verbs() -> None:
    policy = _policy_block()
    assert len(policy["authority_fields"]) == 16
    assert policy["transport_capability"] == "fixed_local_create_only"
    assert policy["cli"]["verbs"] == ["enroll", "terminal", "validate", "report"]
    forbidden = CONTRACT.read_text(encoding="utf-8")
    assert "post_merge_regression" not in _policy_block()["enums"]
    assert "automatic L3" in forbidden


def test_required_descriptor_flags_are_present_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert episode._DIRECTORY_FLAGS & os.O_CLOEXEC
    assert episode._LEAF_READ_FLAGS & os.O_CLOEXEC
    assert episode._LEAF_READ_FLAGS & os.O_NONBLOCK
    assert episode._LEAF_CREATE_FLAGS & os.O_CLOEXEC
    assert episode._LEAF_CREATE_FLAGS & os.O_NONBLOCK

    for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK"):
        with monkeypatch.context() as scoped:
            scoped.delattr(episode.os, name)
            with pytest.raises(episode.EpisodeError, match="E_PUBLISH_UNSUPPORTED"):
                episode._required_open_flag(name)
        with monkeypatch.context() as scoped:
            scoped.setattr(episode.os, name, True)
            with pytest.raises(episode.EpisodeError, match="E_PUBLISH_UNSUPPORTED"):
                episode._required_open_flag(name)


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"\xef\xbb\xbf{}", "E_JSON_INVALID"),
        (b'{"a":1,"a":2}', "E_JSON_INVALID"),
        (b"{} trailing", "E_JSON_INVALID"),
        (b"\xff", "E_JSON_INVALID"),
        (b'{"x":1.0}', "E_JSON_INVALID"),
        (b'{"x":1e2}', "E_JSON_INVALID"),
        (b'{"x":NaN}', "E_JSON_INVALID"),
        (b'{"x":Infinity}', "E_JSON_INVALID"),
        (b'{"x":null}', "E_JSON_INVALID"),
    ],
)
def test_strict_json_rejects_ambiguous_documents(raw: bytes, code: str) -> None:
    with pytest.raises(episode.EpisodeError) as raised:
        episode._strict_json_document(raw)
    assert raised.value.code == code


def test_stdin_depth_node_and_scalar_limits_cover_exact_maximum_and_plus_one() -> None:
    exact_stdin = b"{}" + b" " * (episode.MAX_STDIN_BYTES - 2)
    assert episode._strict_json_document(exact_stdin) == {}
    with pytest.raises(episode.EpisodeError, match="E_INPUT_TOO_LARGE"):
        episode._strict_json_document(exact_stdin + b" ")

    exact_depth: object = 0
    for _index in range(11):
        exact_depth = [exact_depth]
    assert episode._strict_json_document(json.dumps(exact_depth).encode("ascii"))
    too_deep = [exact_depth]
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._strict_json_document(json.dumps(too_deep).encode("ascii"))

    exact_nodes = [0] * (episode.MAX_JSON_NODES - 1)
    assert len(episode._strict_json_document(json.dumps(exact_nodes).encode("ascii"))) == (
        episode.MAX_JSON_NODES - 1
    )
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._strict_json_document(json.dumps(exact_nodes + [0]).encode("ascii"))

    exact_scalar = "x" * episode.MAX_SCALAR_ASCII_BYTES
    assert episode._strict_json_document(json.dumps(exact_scalar).encode("ascii")) == (exact_scalar)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._strict_json_document(json.dumps(exact_scalar + "x").encode("ascii"))


@pytest.mark.parametrize("pull_request_number", [1, 2_147_483_647])
def test_pull_request_bounds_accept_exact_edges(pull_request_number: int) -> None:
    normalized = episode._normalize_enrollment_input(_enrollment(pull_request_number))
    assert normalized["pull_request_number"] == pull_request_number


@pytest.mark.parametrize("pull_request_number", [0, -1, 2_147_483_648, True])
def test_pull_request_bounds_reject_outside_or_boolean(
    pull_request_number: object,
) -> None:
    document = _enrollment()
    document["pull_request_number"] = pull_request_number
    with pytest.raises(episode.EpisodeError, match="E_SCHEMA"):
        episode._normalize_enrollment_input(document)


def test_id_and_timestamp_exact_boundaries() -> None:
    document = _enrollment()
    exact_id = "a" * episode.MAX_ID_ASCII_BYTES
    document["identity_classes"][0]["identity_class_id"] = exact_id
    document["families"][0]["trigger_identity_class_ids"][0] = exact_id
    normalized = episode._normalize_enrollment_input(document)
    assert exact_id in {row["identity_class_id"] for row in normalized["identity_classes"]}

    too_long = _enrollment()
    too_long["identity_classes"][0]["identity_class_id"] = exact_id + "a"
    with pytest.raises(episode.EpisodeError, match="E_IDENTITY"):
        episode._normalize_enrollment_input(too_long)

    invalid_calendar = _enrollment()
    invalid_calendar["trigger_observed_at"] = "2026-02-30T10:00:00Z"
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        episode._normalize_enrollment_input(invalid_calendar)


def test_identity_row_family_and_membership_exact_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(episode, "MAX_IDENTITY_ROWS", 4)
    monkeypatch.setattr(episode, "MAX_FAMILIES", 2)
    monkeypatch.setattr(episode, "MAX_FAMILY_MEMBERSHIP_REFS", 8)
    document = _enrollment()
    document["identity_classes"] = [
        {"identity_class_id": f"class_{index}", "trigger_finding_id": f"finding_{index}"}
        for index in range(4)
    ]
    document["families"] = [
        {
            "family_key": f"family_key_{family}",
            "trigger_family_id": f"trigger_family_{family}",
            "trigger_identity_class_ids": [f"class_{index}" for index in range(4)],
        }
        for family in range(2)
    ]
    normalized = episode._normalize_enrollment_input(document)
    assert len(normalized["identity_classes"]) == 4
    assert len(normalized["families"]) == 2

    too_many_rows = copy.deepcopy(document)
    too_many_rows["identity_classes"].append(
        {"identity_class_id": "class_4", "trigger_finding_id": "finding_4"}
    )
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._normalize_enrollment_input(too_many_rows)

    too_many_families = copy.deepcopy(document)
    too_many_families["families"].append(
        {
            "family_key": "family_key_2",
            "trigger_family_id": "trigger_family_2",
            "trigger_identity_class_ids": ["class_0", "class_1"],
        }
    )
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._normalize_enrollment_input(too_many_families)

    too_many_memberships = copy.deepcopy(document)
    monkeypatch.setattr(episode, "MAX_FAMILY_MEMBERSHIP_REFS", 7)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._normalize_enrollment_input(too_many_memberships)


def test_enrollment_normalizes_order_and_rejects_closed_schema_violations() -> None:
    normalized = episode._normalize_enrollment_input(_enrollment())
    assert [row["identity_class_id"] for row in normalized["identity_classes"]] == [
        "class_a",
        "class_b",
    ]
    assert normalized["families"][0]["trigger_identity_class_ids"] == [
        "class_a",
        "class_b",
    ]

    boolean_pr = _enrollment()
    boolean_pr["pull_request_number"] = True
    with pytest.raises(episode.EpisodeError, match="E_SCHEMA"):
        episode._normalize_enrollment_input(boolean_pr)

    extra = _enrollment()
    extra["notes"] = "arbitrary prose"
    with pytest.raises(episode.EpisodeError, match="E_SCHEMA"):
        episode._normalize_enrollment_input(extra)


@pytest.mark.parametrize(
    "bad_id",
    [
        "../escape",
        "/absolute",
        "C:\\Windows",
        "https://example.invalid",
        "token_value",
        "ghs_secretlikevalue123456",
        "AIza_shape",
        "AKIA_shape",
        "glpat-shape",
        "github_pat_shape",
        "sk-aaaaaaaaaaaa",
        "contains space",
        "unicodé",
    ],
)
def test_sensitive_or_path_like_ids_are_rejected_without_echo(bad_id: str) -> None:
    document = _enrollment()
    document["identity_classes"][0]["identity_class_id"] = bad_id
    with pytest.raises(episode.EpisodeError) as raised:
        episode._normalize_enrollment_input(document)
    assert raised.value.code == "E_IDENTITY"
    assert bad_id not in str(raised.value)


def test_first_enrollment_and_exact_replay_are_immutable(anchor: _Anchor) -> None:
    ack = _run(anchor, "enroll", _enrollment())
    assert ack == {
        "schema_version": "invariant_family_review_episode.ack.v1",
        "status": "ok",
        "operation": "enroll",
        "episode_digest": ack["episode_digest"],
        "enrollment_receipt_digest": ack["enrollment_receipt_digest"],
    }
    path = _receipt_path(anchor, "enrollments", ack["episode_digest"])
    before = path.stat()
    before_bytes = path.read_bytes()
    replay = _run(anchor, "enroll", _enrollment())
    after = path.stat()
    assert replay == ack
    assert path.read_bytes() == before_bytes
    assert (after.st_ino, after.st_mode, after.st_nlink, after.st_mtime_ns) == (
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_mtime_ns,
    )
    receipt = _load_json(path)
    assert receipt["claims"] == {
        "causal_status": "not_assessed",
        "claim_type": "descriptive_observation",
        "observation_basis": "human_digest_referenced",
    }
    assert set(receipt["downstream_grants"].values()) == {False}
    assert len(receipt["downstream_grants"]) == 16


def test_divergent_enrollment_preserves_first_receipt(anchor: _Anchor) -> None:
    ack = _run(anchor, "enroll", _enrollment())
    path = _receipt_path(anchor, "enrollments", ack["episode_digest"])
    before = path.read_bytes()
    divergent = _enrollment()
    divergent["material_head_sha"] = "e" * 40
    with pytest.raises(episode.EpisodeError, match="E_REPLAY_DIVERGENT"):
        _run(anchor, "enroll", divergent)
    assert path.read_bytes() == before


def test_enrollment_rejects_preexisting_orphan_terminal_bundle(anchor: _Anchor) -> None:
    document = _enrollment()
    episode_digest = episode._episode_digest(document["pull_request_number"])
    with episode._StoreSession(anchor.fd, exclusive=True, create=True):
        pass
    terminal_bundle = (
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/terminals"
        / episode_digest
    )
    terminal_bundle.mkdir(mode=0o700)
    receipt = terminal_bundle / "receipt.json"
    receipt.write_bytes(b"{}\n")
    receipt.chmod(0o600)

    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "enroll", document)
    assert not _receipt_path(anchor, "enrollments", episode_digest).exists()


def test_validate_binds_enrollment_and_never_writes(anchor: _Anchor) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    store = anchor.path / "artifacts/orchestration/review_invariant_family_episodes"
    before = sorted(
        (str(path.relative_to(store)), path.stat().st_mtime_ns) for path in store.rglob("*")
    )
    baseline = _baseline(enrollment_ack)
    ack = _run(anchor, "validate", baseline)
    after = sorted(
        (str(path.relative_to(store)), path.stat().st_mtime_ns) for path in store.rglob("*")
    )
    assert ack["operation"] == "validate"
    assert ack["episode_digest"] == enrollment_ack["episode_digest"]
    assert len(ack["joint_pass_baseline_digest"]) == 64
    assert before == after

    wrong = _baseline(enrollment_ack)
    wrong["enrollment_receipt_digest"] = "f" * 64
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, "validate", wrong)


def test_terminal_positive_recurrence_is_c_minus_j(anchor: _Anchor) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    terminal = _terminal_available(enrollment_ack, baseline, baseline_ack)
    ack = _run(anchor, "terminal", terminal)
    receipt = _load_json(_receipt_path(anchor, "terminals", enrollment_ack["episode_digest"]))
    assert ack["operation"] == "terminal"
    assert receipt["recurrence"] == {
        "status": "observed",
        "reason": "positive",
        "value": True,
    }
    family = receipt["joint_pass"]["family_observations"][0]
    assert family["post_joint_same_family_first_observed_identity_class_ids"] == ["class_d"]
    assert family["post_joint_same_family_first_observed_count"] == 1
    assert "class_c" not in family["post_joint_same_family_first_observed_identity_class_ids"]


def test_terminal_zero_is_observed_false_and_replay_is_immutable(anchor: _Anchor) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    terminal = _terminal_available(enrollment_ack, baseline, baseline_ack, positive=False)
    ack = _run(anchor, "terminal", terminal)
    path = _receipt_path(anchor, "terminals", enrollment_ack["episode_digest"])
    before = path.stat()
    receipt = _load_json(path)
    assert receipt["recurrence"] == {
        "status": "observed",
        "reason": "zero",
        "value": False,
    }
    assert (
        receipt["joint_pass"]["family_observations"][0][
            "post_joint_same_family_first_observed_count"
        ]
        == 0
    )
    assert _run(anchor, "terminal", terminal) == ack
    after = path.stat()
    assert (before.st_ino, before.st_mtime_ns, before.st_ctime_ns) == (
        after.st_ino,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )

    enrollment_path = _receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])
    enrollment_before = enrollment_path.stat()
    assert _run(anchor, "enroll", _enrollment()) == enrollment_ack
    enrollment_after = enrollment_path.stat()
    assert (
        enrollment_after.st_ino,
        enrollment_after.st_mode,
        enrollment_after.st_nlink,
        enrollment_after.st_mtime_ns,
    ) == (
        enrollment_before.st_ino,
        enrollment_before.st_mode,
        enrollment_before.st_nlink,
        enrollment_before.st_mtime_ns,
    )

    enrollment_receipt = _load_json(enrollment_path)
    forged_terminal = copy.deepcopy(receipt)
    forged_terminal["joint_pass"]["family_observations"][0][
        "post_joint_same_family_first_observed_count"
    ] = False
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        episode._validate_terminal_receipt(forged_terminal, enrollment_receipt)


def test_multi_trigger_precedence_keeps_complete_validated_terminal(anchor: _Anchor) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    terminal = _terminal_available(
        enrollment_ack, baseline, baseline_ack, extra_trigger_digest=True
    )
    _run(anchor, "terminal", terminal)
    receipt = _load_json(_receipt_path(anchor, "terminals", enrollment_ack["episode_digest"]))
    assert receipt["recurrence"] == {
        "status": "non_comparable",
        "reason": "multi_trigger",
    }

    malformed = _terminal_available(
        enrollment_ack, baseline, baseline_ack, extra_trigger_digest=True
    )
    malformed["joint_pass"]["baseline"]["families"][0][
        "joint_pass_cumulative_identity_class_ids"
    ] = ["class_a"]
    with pytest.raises(episode.EpisodeError):
        episode._normalize_terminal_input(
            malformed,
            _load_json(_receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])),
        )


@pytest.mark.parametrize(
    ("completed", "expected"),
    [
        (
            True,
            {
                "status": "unknown",
                "reason": "joint_pass_baseline_unavailable",
            },
        ),
        (
            False,
            {
                "status": "not_applicable",
                "reason": "not_completed_before_terminal",
            },
        ),
    ],
)
def test_terminal_closed_branches_never_fabricate_j_or_zero(
    anchor: _Anchor, completed: bool, expected: dict[str, object]
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    terminal = _terminal_without_available_baseline(enrollment_ack, completed=completed)
    _run(anchor, "terminal", terminal)
    receipt = _load_json(_receipt_path(anchor, "terminals", enrollment_ack["episode_digest"]))
    assert receipt["recurrence"] == expected
    assert "families" not in receipt["joint_pass"]
    assert "value" not in receipt["recurrence"]


@pytest.mark.parametrize(
    ("family_status", "reason", "episode_reason"),
    [
        (
            "unknown",
            "terminal_cumulative_inventory_incomplete",
            "family_observation_unknown",
        ),
        (
            "non_comparable",
            "non_bijective_identity",
            "family_observation_non_comparable",
        ),
    ],
)
def test_family_unknown_and_non_comparable_have_no_fake_inventory_or_count(
    anchor: _Anchor,
    family_status: str,
    reason: str,
    episode_reason: str,
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    terminal = _terminal_available(enrollment_ack, baseline, baseline_ack, positive=False)
    terminal["joint_pass"]["family_observations"] = [
        {
            "status": family_status,
            "reason": reason,
            "family_key": "family_key_a",
        }
    ]
    _run(anchor, "terminal", terminal)
    receipt = _load_json(_receipt_path(anchor, "terminals", enrollment_ack["episode_digest"]))
    assert receipt["recurrence"] == {
        "status": family_status,
        "reason": episode_reason,
    }
    observation = receipt["joint_pass"]["family_observations"][0]
    assert set(observation) == {"status", "reason", "family_key"}


def test_equal_bare_ids_do_not_create_implicit_cross_phase_identity(
    anchor: _Anchor,
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline["identity_classes"][0]["phase_bindings"] = [
        {"phase": "joint_pass", "finding_id": "finding_a"}
    ]
    with pytest.raises(episode.EpisodeError, match="E_IDENTITY"):
        _run(anchor, "validate", baseline)


def test_terminal_rejects_wrong_baseline_digest_and_non_monotone_cumulative_set(
    anchor: _Anchor,
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    wrong_digest = _terminal_available(enrollment_ack, baseline, baseline_ack)
    wrong_digest["joint_pass"]["joint_pass_baseline_digest"] = "f" * 64
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, "terminal", wrong_digest)

    non_monotone = _terminal_available(enrollment_ack, baseline, baseline_ack)
    non_monotone["joint_pass"]["family_observations"][0][
        "terminal_cumulative_identity_class_ids"
    ] = ["class_a", "class_b"]
    with pytest.raises(episode.EpisodeError, match="E_IDENTITY"):
        _run(anchor, "terminal", non_monotone)


def test_equal_timestamp_boundaries_allow_zero_but_reject_positive_empty_interval(
    anchor: _Anchor,
) -> None:
    enrollment_document = _enrollment()
    enrollment_document["trigger_observed_at"] = "2026-08-15T10:01:00Z"
    enrollment_ack = _run(anchor, "enroll", enrollment_document)
    baseline = _baseline(enrollment_ack)
    baseline["joint_pass_completed_at"] = "2026-08-15T10:01:00Z"
    baseline_ack = _run(anchor, "validate", baseline)

    zero = _terminal_available(enrollment_ack, baseline, baseline_ack, positive=False)
    zero["terminal_event_at"] = "2026-08-15T10:01:00Z"
    zero["terminal_recorded_at"] = "2026-08-15T10:01:00Z"
    normalized = episode._normalize_terminal_input(
        zero,
        _load_json(_receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])),
    )
    assert normalized["recurrence"]["reason"] == "zero"

    positive = _terminal_available(enrollment_ack, baseline, baseline_ack)
    positive["terminal_event_at"] = "2026-08-15T10:01:00Z"
    positive["terminal_recorded_at"] = "2026-08-15T10:01:00Z"
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        episode._normalize_terminal_input(
            positive,
            _load_json(_receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("terminal_state", "inconclusive"),
        ("post_merge_regression", True),
        ("merge_readiness", "PASS"),
        ("effectiveness", "GO"),
    ],
)
def test_terminal_rejects_inconclusive_post_merge_and_decision_fields(
    anchor: _Anchor, field: str, value: object
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    terminal = _terminal_without_available_baseline(enrollment_ack, completed=False)
    terminal[field] = value
    expected = "E_SCHEMA"
    with pytest.raises(episode.EpisodeError, match=expected):
        _run(anchor, "terminal", terminal)


def test_terminal_source_reference_budget_counts_embedded_and_full_crosswalk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enrollment = episode._build_enrollment_receipt(_enrollment())
    enrollment_ack = {
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
    }
    baseline = _baseline(enrollment_ack)
    normalized_baseline = episode._normalize_joint_pass_baseline(baseline, enrollment)
    baseline_ack = {
        "joint_pass_baseline_digest": episode._joint_pass_baseline_digest(normalized_baseline)
    }
    terminal = _terminal_available(enrollment_ack, baseline, baseline_ack)
    monkeypatch.setattr(episode, "MAX_SOURCE_FINDING_IDS", 14)
    assert (
        episode._normalize_terminal_input(terminal, enrollment)["recurrence"]["reason"]
        == "positive"
    )
    monkeypatch.setattr(episode, "MAX_SOURCE_FINDING_IDS", 13)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._normalize_terminal_input(terminal, enrollment)


def test_observed_l2_digest_limit_accepts_sixteen_and_rejects_seventeen() -> None:
    enrollment = episode._build_enrollment_receipt(_enrollment())
    enrollment_ack = {
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
    }
    baseline = _baseline(enrollment_ack)
    baseline_ack = {
        "joint_pass_baseline_digest": episode._joint_pass_baseline_digest(
            episode._normalize_joint_pass_baseline(baseline, enrollment)
        )
    }
    terminal = _terminal_available(enrollment_ack, baseline, baseline_ack)
    digests = {"b" * 64}
    digests.update(f"{index:064x}" for index in range(1, 16))
    terminal["observed_l2_identity_digests"] = sorted(digests)
    normalized = episode._normalize_terminal_input(terminal, enrollment)
    assert len(normalized["observed_l2_identity_digests"]) == 16
    terminal["observed_l2_identity_digests"] = sorted(digests | {f"{16:064x}"})
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._normalize_terminal_input(terminal, enrollment)


def test_confirmed_family_correspondence_is_one_to_one() -> None:
    enrollment_input = _enrollment()
    enrollment_input["families"].append(
        {
            "family_key": "family_key_b",
            "trigger_family_id": "trigger_family_b",
            "trigger_identity_class_ids": ["class_a", "class_b"],
        }
    )
    enrollment = episode._build_enrollment_receipt(enrollment_input)
    enrollment_ack = {
        "episode_digest": enrollment["episode_digest"],
        "enrollment_receipt_digest": enrollment["enrollment_receipt_digest"],
    }
    baseline = _baseline(enrollment_ack)
    baseline["families"].append(
        {
            "family_key": "family_key_b",
            "joint_pass_family_id": "joint_family_b",
            "joint_pass_cumulative_identity_class_ids": [
                "class_a",
                "class_b",
                "class_c",
            ],
            "recommended_resolution": "family_fix",
        }
    )
    normalized_baseline = episode._normalize_joint_pass_baseline(baseline, enrollment)
    baseline_ack = {
        "joint_pass_baseline_digest": episode._joint_pass_baseline_digest(normalized_baseline)
    }
    terminal = _terminal_available(enrollment_ack, baseline, baseline_ack, positive=False)
    duplicate_terminal_id = terminal["joint_pass"]["family_observations"][0]["terminal_family_id"]
    terminal["joint_pass"]["family_observations"].append(
        {
            "status": "confirmed",
            "reason": "same_scope_confirmed",
            "family_key": "family_key_b",
            "terminal_family_id": duplicate_terminal_id,
            "terminal_cumulative_identity_class_ids": [
                "class_a",
                "class_b",
                "class_c",
            ],
        }
    )
    with pytest.raises(episode.EpisodeError, match="E_IDENTITY"):
        episode._normalize_terminal_input(terminal, enrollment)


def test_validate_after_terminal_and_terminal_without_enrollment_fail(anchor: _Anchor) -> None:
    orphan = {
        "schema_version": "invariant_family_review_episode.terminal_input.v1",
        "episode_digest": "a" * 64,
        "enrollment_receipt_digest": "b" * 64,
        "terminal_state": "closed_unmerged",
        "terminal_event_at": "2026-08-15T10:03:00Z",
        "terminal_recorded_at": "2026-08-15T10:04:00Z",
        "terminal_material_head_sha": "d" * 40,
        "observed_l2_identity_digests": ["b" * 64],
        "joint_pass": {
            "status": "not_completed",
            "reason": "not_completed_before_terminal",
        },
    }
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, "terminal", orphan)

    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    _run(anchor, "terminal", _terminal_available(enrollment_ack, baseline, baseline_ack))
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        _run(anchor, "validate", baseline)


def test_missing_terminal_remains_unknown_in_primary_denominator(anchor: _Anchor) -> None:
    _run(anchor, "enroll", _enrollment())
    report_ack = _run(anchor, "report", _report_request())
    report_path = (
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/reports"
        / str(report_ack["report_digest"])
        / "report.json"
    )
    report = _load_json(report_path)
    primary = report["prospective_primary"]
    assert primary["enrollment_count"] == 1
    assert primary["unknown_count"] == 1
    assert primary["eligible_denominator_count"] == 1
    assert primary["zero_count"] == 0
    assert primary["recurrence_lower_bound_ratio"] == {
        "status": "defined",
        "numerator": 0,
        "denominator": 1,
    }
    assert primary["recurrence_upper_bound_ratio"] == {
        "status": "defined",
        "numerator": 1,
        "denominator": 1,
    }
    assert report["manifest"][0]["terminal_receipt_digest"] == "missing_terminal"
    assert report["manifest"][0]["observation_reason"] == "missing_terminal"


def test_reports_are_deterministic_cross_bound_and_do_not_mutate_receipts(
    anchor: _Anchor,
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    _run(anchor, "terminal", _terminal_available(enrollment_ack, baseline, baseline_ack))
    enrollment_path = _receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])
    terminal_path = _receipt_path(anchor, "terminals", enrollment_ack["episode_digest"])
    receipt_state = [
        (path.read_bytes(), path.stat().st_mtime_ns) for path in (enrollment_path, terminal_path)
    ]
    first = _run(anchor, "report", _report_request())
    second = _run(
        anchor,
        "report",
        {
            "cohort_as_of": "2026-08-15T10:05:00Z",
            "schema_version": "invariant_family_review_episode.report_request.v1",
        },
    )
    assert first == second
    bundle = (
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/reports"
        / str(first["report_digest"])
    )
    report_json = _load_json(bundle / "report.json")
    markdown = (bundle / "report.md").read_bytes()
    assert episode._plain_sha256(markdown) == report_json["markdown_sha256"]

    forged_report = copy.deepcopy(report_json)
    forged_report["prospective_primary"]["positive_count"] = False
    with pytest.raises(episode.EpisodeError, match="E_REPORT_MANIFEST"):
        episode._validate_report_bundle(
            {
                "report.json": episode._canonical_json_bytes(forged_report, trailing_lf=True),
                "report.md": markdown,
            },
            {enrollment_ack["episode_digest"]: _load_json(enrollment_path)},
            {enrollment_ack["episode_digest"]: _load_json(terminal_path)},
        )
    assert report_json["report_digest"] == first["report_digest"]
    assert report_json["claims"]["all_eligible_episodes_claim"] is False
    assert [
        (path.read_bytes(), path.stat().st_mtime_ns) for path in (enrollment_path, terminal_path)
    ] == receipt_state


def test_retrospective_reference_is_excluded_from_primary_ratios(anchor: _Anchor) -> None:
    _run(anchor, "enroll", _enrollment(17))
    _run(anchor, "enroll", _enrollment(18, episode_class="retrospective_reference"))
    report = _run(anchor, "report", _report_request())
    report_json = _load_json(
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/reports"
        / str(report["report_digest"])
        / "report.json"
    )
    assert report_json["prospective_primary"]["enrollment_count"] == 1
    assert report_json["retrospective_reference"]["enrollment_count"] == 1
    assert "recurrence_lower_bound_ratio" not in report_json["retrospective_reference"]


def test_zero_denominators_are_tagged_not_applicable(anchor: _Anchor) -> None:
    report = _run(anchor, "report", _report_request())
    report_json = _load_json(
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/reports"
        / str(report["report_digest"])
        / "report.json"
    )
    for name in (
        "recurrence_lower_bound_ratio",
        "recurrence_upper_bound_ratio",
        "terminal_coverage_ratio",
        "identified_coverage_ratio",
    ):
        assert report_json["prospective_primary"][name] == {
            "status": "not_applicable",
            "reason": "zero_denominator",
        }


def test_as_of_is_consistency_boundary_not_historical_filter(anchor: _Anchor) -> None:
    _run(anchor, "enroll", _enrollment())
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        _run(anchor, "report", _report_request("2026-08-15T10:00:30Z"))


@pytest.mark.parametrize(
    ("identified_count", "expected_band"),
    [
        (4, "collecting_lt_5"),
        (5, "interim_5_to_9"),
        (9, "interim_5_to_9"),
        (10, "target_count_gte_10"),
    ],
)
def test_accrual_bands_use_identified_episode_count_only(
    anchor: _Anchor, identified_count: int, expected_band: str
) -> None:
    for index in range(identified_count):
        enrollment_ack = _run(anchor, "enroll", _enrollment(100 + index))
        baseline = _baseline(enrollment_ack)
        baseline_ack = _run(anchor, "validate", baseline)
        _run(
            anchor,
            "terminal",
            _terminal_available(enrollment_ack, baseline, baseline_ack, positive=False),
        )
    report_ack = _run(anchor, "report", _report_request())
    report = _load_json(
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/reports"
        / str(report_ack["report_digest"])
        / "report.json"
    )
    primary = report["prospective_primary"]
    assert primary["identified_episode_count"] == identified_count
    assert primary["accrual_band"] == expected_band


def test_report_partition_keeps_multi_trigger_missing_and_not_applicable_distinct(
    anchor: _Anchor,
) -> None:
    _run(anchor, "enroll", _enrollment(201))

    not_applicable_ack = _run(anchor, "enroll", _enrollment(202))
    _run(
        anchor,
        "terminal",
        _terminal_without_available_baseline(not_applicable_ack, completed=False),
    )

    multi_ack = _run(anchor, "enroll", _enrollment(203))
    multi_baseline = _baseline(multi_ack)
    multi_baseline_ack = _run(anchor, "validate", multi_baseline)
    _run(
        anchor,
        "terminal",
        _terminal_available(
            multi_ack,
            multi_baseline,
            multi_baseline_ack,
            extra_trigger_digest=True,
        ),
    )

    report_ack = _run(anchor, "report", _report_request())
    report = _load_json(
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/reports"
        / str(report_ack["report_digest"])
        / "report.json"
    )
    primary = report["prospective_primary"]
    assert primary["enrollment_count"] == 3
    assert primary["unknown_count"] == 1
    assert primary["non_comparable_count"] == 1
    assert primary["not_applicable_count"] == 1
    assert primary["eligible_denominator_count"] == 2
    assert (
        primary["positive_count"]
        + primary["zero_count"]
        + primary["unknown_count"]
        + primary["non_comparable_count"]
        + primary["not_applicable_count"]
        == primary["enrollment_count"]
    )


def test_store_rejects_orphan_stage_symlink_and_unsafe_mode(anchor: _Anchor) -> None:
    ack = _run(anchor, "enroll", _enrollment())
    root = anchor.path / "artifacts/orchestration/review_invariant_family_episodes"
    os.mkdir(root / "terminals" / ".stage-orphan", 0o700)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())
    os.rmdir(root / "terminals" / ".stage-orphan")

    receipt = _receipt_path(anchor, "enrollments", ack["episode_digest"])
    receipt.chmod(0o644)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())


def test_partial_and_unexpected_bundles_are_not_missing(anchor: _Anchor) -> None:
    ack = _run(anchor, "enroll", _enrollment())
    terminal_bundle = (
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/terminals"
        / str(ack["episode_digest"])
    )
    terminal_bundle.mkdir(mode=0o700)
    (terminal_bundle / "unexpected.json").write_text("{}\n", encoding="ascii")
    (terminal_bundle / "unexpected.json").chmod(0o600)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())


@pytest.mark.parametrize("component", ["shared", "module_root", "lane", "bundle", "leaf"])
def test_symlinks_fail_closed_at_every_store_level(anchor: _Anchor, component: str) -> None:
    target = anchor.path / "symlink-target"
    target.mkdir(mode=0o700)
    if component == "shared":
        os.symlink(target, anchor.path / "artifacts")
        with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
            _run(anchor, "report", _report_request())
        return

    artifacts = anchor.path / "artifacts"
    artifacts.mkdir(mode=0o700)
    orchestration = artifacts / "orchestration"
    orchestration.mkdir(mode=0o700)
    module_root = orchestration / "review_invariant_family_episodes"
    if component == "module_root":
        os.symlink(target, module_root)
        with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
            _run(anchor, "report", _report_request())
        return

    enrollment_ack = _run(anchor, "enroll", _enrollment())
    if component == "lane":
        lane = module_root / "terminals"
        lane.rmdir()
        os.symlink(target, lane)
    elif component == "bundle":
        os.symlink(
            target,
            module_root / "terminals" / str(enrollment_ack["episode_digest"]),
        )
    else:
        receipt = _receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])
        preserved = target / "receipt.json"
        preserved.write_bytes(receipt.read_bytes())
        preserved.chmod(0o600)
        receipt.unlink()
        os.symlink(preserved, receipt)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())


@pytest.mark.parametrize("replacement", ["directory", "fifo", "socket", "hardlink"])
def test_non_regular_and_hardlinked_receipts_fail_closed(anchor: _Anchor, replacement: str) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    receipt = _receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])
    original = receipt.read_bytes()
    if replacement == "hardlink":
        os.link(receipt, anchor.path / "second-link")
    else:
        receipt.unlink()
        if replacement == "directory":
            receipt.mkdir(mode=0o700)
        elif replacement == "fifo":
            os.mkfifo(receipt, mode=0o600)
        else:
            with tempfile.TemporaryDirectory(prefix="el2-", dir="/tmp") as short_root:
                short_anchor = _Anchor(Path(short_root))
                try:
                    socket_component = short_anchor.path / "artifacts"
                    unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    try:
                        unix_socket.bind(str(socket_component))
                        with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
                            _run(short_anchor, "report", _report_request())
                    finally:
                        unix_socket.close()
                finally:
                    short_anchor.close()
            return
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())
    assert original


def test_changed_during_read_is_detected_even_when_mtime_is_restored(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    receipt = _receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])
    original_bytes = receipt.read_bytes()
    original_stat = receipt.stat()
    real_read = episode.os.read
    changed = False

    def changing_read(descriptor: int, size: int) -> bytes:
        nonlocal changed
        result = real_read(descriptor, size)
        if result and not changed:
            changed = True
            receipt.write_bytes(original_bytes)
            receipt.chmod(0o600)
            os.utime(
                receipt,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )
        return result

    monkeypatch.setattr(episode.os, "read", changing_read)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())


def test_lock_contention_is_nonblocking_and_sanitized(anchor: _Anchor) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    root = anchor.path / "artifacts/orchestration/review_invariant_family_episodes"
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(episode.EpisodeError, match="E_LOCK_BUSY"):
            _run(anchor, "validate", _baseline(enrollment_ack))
    finally:
        os.close(root_fd)


def test_short_write_fails_and_cleans_owned_stage(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_write = episode.os.write

    def zero_write(_descriptor: int, _data: bytes) -> int:
        return 0

    monkeypatch.setattr(episode.os, "write", zero_write)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", _enrollment())
    monkeypatch.setattr(episode.os, "write", real_write)
    lane = anchor.path / "artifacts/orchestration/review_invariant_family_episodes/enrollments"
    assert list(lane.iterdir()) == []


def test_file_fsync_failure_before_publish_leaves_no_canonical_bundle(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(anchor, "enroll", _enrollment(301))
    real_fsync = episode.os.fsync
    failed = False

    def failing_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("synthetic fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(episode.os, "fsync", failing_fsync)
    document = _enrollment(302)
    expected_digest = episode._episode_digest(302)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", document)
    assert not _receipt_path(anchor, "enrollments", expected_digest).exists()


def test_parent_fsync_failure_after_rename_preserves_published_bundle(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(anchor, "enroll", _enrollment(401))
    real_fsync = episode.os.fsync
    call_count = 0

    def failing_fourth_fsync(descriptor: int) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 4:
            raise OSError("synthetic parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(episode.os, "fsync", failing_fourth_fsync)
    document = _enrollment(402)
    expected_digest = episode._episode_digest(402)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", document)
    published = _receipt_path(anchor, "enrollments", expected_digest)
    assert published.is_file()
    monkeypatch.setattr(episode.os, "fsync", real_fsync)
    assert _run(anchor, "enroll", document)["episode_digest"] == expected_digest


def test_unsupported_no_replace_fails_closed_and_cleans_stage(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unsupported(_lane_fd: int, _stage: str, _final: str) -> None:
        raise episode.EpisodeError("E_PUBLISH_UNSUPPORTED")

    monkeypatch.setattr(episode, "_kernel_rename_noreplace", unsupported)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_UNSUPPORTED"):
        _run(anchor, "enroll", _enrollment())
    lane = anchor.path / "artifacts/orchestration/review_invariant_family_episodes/enrollments"
    assert list(lane.iterdir()) == []


def test_identical_concurrent_winner_returns_state_independent_ack(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_kernel_publish = episode._kernel_rename_noreplace

    def publish_winner_then_collide(lane_fd: int, stage_name: str, final_name: str) -> None:
        os.mkdir(final_name, 0o700, dir_fd=lane_fd)
        stage_fd = os.open(stage_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=lane_fd)
        final_fd = os.open(final_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=lane_fd)
        try:
            os.fchmod(final_fd, 0o700)
            for name in os.listdir(stage_fd):
                source_fd = os.open(name, os.O_RDONLY, dir_fd=stage_fd)
                winner_fd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=final_fd,
                )
                try:
                    os.fchmod(winner_fd, 0o600)
                    while True:
                        chunk = os.read(source_fd, 65_536)
                        if not chunk:
                            break
                        offset = 0
                        while offset < len(chunk):
                            written = os.write(winner_fd, chunk[offset:])
                            assert written > 0
                            offset += written
                finally:
                    os.close(source_fd)
                    os.close(winner_fd)
        finally:
            os.close(stage_fd)
            os.close(final_fd)
        raise OSError(errno.EEXIST, "synthetic winner")

    monkeypatch.setattr(episode, "_kernel_rename_noreplace", publish_winner_then_collide)
    document = _enrollment()
    collision_ack = _run(anchor, "enroll", document)
    monkeypatch.setattr(episode, "_kernel_rename_noreplace", real_kernel_publish)
    replay_ack = _run(anchor, "enroll", document)
    assert collision_ack == replay_ack
    lane = anchor.path / "artifacts/orchestration/review_invariant_family_episodes/enrollments"
    assert all(not entry.name.startswith(".stage-") for entry in lane.iterdir())


@pytest.mark.parametrize("corruption", ["missing_markdown", "changed_markdown", "changed_json"])
def test_prior_report_corruption_blocks_new_generation(anchor: _Anchor, corruption: str) -> None:
    _run(anchor, "enroll", _enrollment())
    report_ack = _run(anchor, "report", _report_request())
    bundle = (
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/reports"
        / str(report_ack["report_digest"])
    )
    if corruption == "missing_markdown":
        (bundle / "report.md").unlink()
    elif corruption == "changed_markdown":
        (bundle / "report.md").write_text("changed\n", encoding="ascii")
        (bundle / "report.md").chmod(0o600)
    else:
        report = _load_json(bundle / "report.json")
        report["cohort_as_of"] = "2026-08-15T10:06:00Z"
        (bundle / "report.json").write_bytes(
            episode._canonical_json_bytes(report, trailing_lf=True)
        )
        (bundle / "report.json").chmod(0o600)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE|E_REPORT_MANIFEST"):
        _run(anchor, "report", _report_request("2026-08-15T10:06:00Z"))


def test_environment_cwd_and_input_key_order_do_not_change_artifact_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    unrelated = tmp_path / "unrelated"
    first_root.mkdir(mode=0o700)
    second_root.mkdir(mode=0o700)
    unrelated.mkdir(mode=0o700)
    first_anchor = _Anchor(first_root)
    second_anchor = _Anchor(second_root)
    try:
        first_document = _enrollment()
        second_document = dict(reversed(list(_enrollment().items())))
        first_ack = _run(first_anchor, "enroll", first_document)
        monkeypatch.chdir(unrelated)
        monkeypatch.setenv("HOME", str(unrelated))
        monkeypatch.setenv("TZ", "Pacific/Kiritimati")
        second_ack = _run(second_anchor, "enroll", second_document)
        assert first_ack == second_ack
        assert (
            _receipt_path(first_anchor, "enrollments", first_ack["episode_digest"]).read_bytes()
            == _receipt_path(
                second_anchor, "enrollments", second_ack["episode_digest"]
            ).read_bytes()
        )
    finally:
        first_anchor.close()
        second_anchor.close()


def test_repository_anchor_resolves_a_symlinked_module_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actual_module = Path(episode.__file__).resolve()
    alias = tmp_path / "invariant_family_review_episode.py"
    alias.symlink_to(actual_module)
    monkeypatch.setattr(episode, "__file__", str(alias))

    descriptor = episode._open_repository_anchor()
    try:
        expected = actual_module.parents[2].stat()
        observed = os.fstat(descriptor)
        assert (observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino)
    finally:
        os.close(descriptor)


def test_cli_diagnostics_do_not_echo_input_path_prose_or_traceback() -> None:
    module = (
        Path(__file__).resolve().parents[1]
        / "scripts/orchestration/invariant_family_review_episode.py"
    )
    submitted = b'{"notes":"arbitrary review prose","path":"/Users/private"}'
    completed = subprocess.run(
        [sys.executable, str(module), "enroll"],
        input=submitted,
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr in {
        b"E_SCHEMA\n",
        b"E_IDENTITY\n",
        b"E_JSON_INVALID\n",
    }
    assert b"arbitrary review prose" not in completed.stderr
    assert b"/Users/private" not in completed.stderr
    assert b"Traceback" not in completed.stderr


def test_aggregate_receipt_scan_limit_is_shared_across_both_lanes(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    _run(anchor, "terminal", _terminal_available(enrollment_ack, baseline, baseline_ack))
    enrollment_path = _receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])
    terminal_path = _receipt_path(anchor, "terminals", enrollment_ack["episode_digest"])
    exact_total = enrollment_path.stat().st_size + terminal_path.stat().st_size
    monkeypatch.setattr(episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", exact_total)
    _run(anchor, "report", _report_request())
    monkeypatch.setattr(episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", exact_total - 1)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "report", _report_request("2026-08-15T10:06:00Z"))


def test_report_generation_cap_allows_replay_but_rejects_new_generation(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_request = _report_request()
    first = _run(anchor, "report", first_request)
    monkeypatch.setattr(episode, "MAX_REPORT_GENERATIONS", 1)
    assert _run(anchor, "report", first_request) == first
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "report", _report_request("2026-08-15T10:06:00Z"))


def test_oversize_existing_receipt_is_store_unsafe(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    receipt = _receipt_path(anchor, "enrollments", enrollment_ack["episode_digest"])
    monkeypatch.setattr(episode, "MAX_ENROLLMENT_RECEIPT_BYTES", receipt.stat().st_size - 1)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())


def test_missing_platform_symbol_and_unsupported_errno_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingSymbol:
        pass

    monkeypatch.setattr(episode.sys, "platform", "darwin")
    monkeypatch.setattr(episode.ctypes, "CDLL", lambda _name, use_errno: MissingSymbol())
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_UNSUPPORTED"):
        episode._kernel_rename_noreplace(1, "stage", "final")

    class UnsupportedCall:
        argtypes: object = None
        restype: object = None

        def __call__(self, *_args: object) -> int:
            return -1

    class UnsupportedLibrary:
        renameat2 = UnsupportedCall()

    monkeypatch.setattr(episode.sys, "platform", "linux")
    monkeypatch.setattr(episode.ctypes, "CDLL", lambda _name, use_errno: UnsupportedLibrary())
    monkeypatch.setattr(episode.ctypes, "get_errno", lambda: errno.ENOSYS)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_UNSUPPORTED"):
        episode._kernel_rename_noreplace(1, "stage", "final")


def test_capacity_bound_allows_exact_replay_but_rejects_new_bundle(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(episode, "MAX_ENROLLMENT_BUNDLES", 1)
    first = _enrollment(17)
    _run(anchor, "enroll", first)
    _run(anchor, "enroll", first)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "enroll", _enrollment(18))


@pytest.mark.parametrize("verb", ["amend", "reopen", "supersede", "repair", "delete", "list"])
def test_unsupported_public_verbs_are_usage_errors(verb: str) -> None:
    with pytest.raises(episode.EpisodeError, match="E_USAGE"):
        episode._require_public_verb(verb)


def test_canonical_ack_is_ascii_bounded_and_has_one_lf() -> None:
    ack = {
        "schema_version": "invariant_family_review_episode.ack.v1",
        "status": "ok",
        "operation": "enroll",
        "episode_digest": "a" * 64,
        "enrollment_receipt_digest": "b" * 64,
    }
    rendered = episode._canonical_json_bytes(ack, trailing_lf=True)
    assert rendered.endswith(b"\n")
    assert rendered.count(b"\n") == 1
    assert len(rendered) <= 4096
    rendered.decode("ascii")


def test_permissions_are_private(anchor: _Anchor) -> None:
    ack = _run(anchor, "enroll", _enrollment())
    root = anchor.path / "artifacts/orchestration/review_invariant_family_episodes"
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE((root / "enrollments").stat().st_mode) == 0o700
    assert (
        stat.S_IMODE(_receipt_path(anchor, "enrollments", ack["episode_digest"]).stat().st_mode)
        == 0o600
    )


def test_wrong_owner_and_group_writable_module_root_fail_closed(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(anchor, "enroll", _enrollment())
    root = anchor.path / "artifacts/orchestration/review_invariant_family_episodes"
    root.chmod(0o770)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())
    root.chmod(0o700)

    real_euid = os.geteuid()
    monkeypatch.setattr(episode.os, "geteuid", lambda: real_euid + 1)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())


@pytest.mark.parametrize("failing_call", [2, 3])
def test_stage_and_prepublication_parent_fsync_failures_leave_no_final(
    anchor: _Anchor,
    monkeypatch: pytest.MonkeyPatch,
    failing_call: int,
) -> None:
    _run(anchor, "enroll", _enrollment(501))
    real_fsync = episode.os.fsync
    call_count = 0

    def failing_fsync(descriptor: int) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == failing_call:
            raise OSError("synthetic fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(episode.os, "fsync", failing_fsync)
    expected_digest = episode._episode_digest(502)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", _enrollment(502))
    assert not _receipt_path(anchor, "enrollments", expected_digest).exists()


def test_staging_name_attempts_stop_after_exact_bound(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(anchor, "enroll", _enrollment(601))
    real_mkdir = episode.os.mkdir
    collisions = 0

    def colliding_mkdir(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal collisions
        if isinstance(path, str) and path.startswith(".stage-"):
            collisions += 1
            raise FileExistsError
        real_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(episode.os, "mkdir", colliding_mkdir)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", _enrollment(602))
    assert collisions == episode.MAX_STAGING_ATTEMPTS == 32


def test_cleanup_identity_drift_leaves_orphan_and_never_deletes_replacement(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(anchor, "enroll", _enrollment(701))

    def drift_then_fail(lane_fd: int, stage_name: str, _final_name: str) -> None:
        stolen_name = ".stolen-stage"
        os.rename(stage_name, stolen_name, src_dir_fd=lane_fd, dst_dir_fd=lane_fd)
        os.mkdir(stage_name, 0o700, dir_fd=lane_fd)
        raise episode.EpisodeError("E_PUBLISH_UNSUPPORTED")

    monkeypatch.setattr(episode, "_kernel_rename_noreplace", drift_then_fail)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", _enrollment(702))
    lane = anchor.path / "artifacts/orchestration/review_invariant_family_episodes/enrollments"
    names = {path.name for path in lane.iterdir()}
    assert ".stolen-stage" in names
    assert any(name.startswith(".stage-") for name in names)


def test_stdout_sink_failure_has_only_stable_error_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(episode.os, "write", lambda _descriptor, _data: 0)
    with pytest.raises(episode.EpisodeError, match="E_STDOUT"):
        episode._write_ack(
            {
                "schema_version": "invariant_family_review_episode.ack.v1",
                "status": "ok",
                "operation": "enroll",
                "episode_digest": "a" * 64,
                "enrollment_receipt_digest": "b" * 64,
            }
        )

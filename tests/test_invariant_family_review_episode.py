from __future__ import annotations

import copy
import errno
import fcntl
import hashlib
import json
import operator
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator, Mapping
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
def anchor(tmp_path: Path) -> Iterator[_Anchor]:
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
    enums = policy["enums"]
    assert isinstance(enums, dict)
    assert enums["family_observation_statuses"] == [
        "confirmed",
        "unknown",
        "non_comparable",
    ]
    assert enums["family_confirmed_reasons"] == ["same_scope_confirmed"]
    assert enums["episode_observation_statuses"] == [
        "observed",
        "unknown",
        "non_comparable",
        "not_applicable",
    ]
    assert enums["ratio_statuses"] == ["defined", "not_applicable"]
    assert tuple(enums["family_observation_statuses"]) == episode.FAMILY_OBSERVATION_STATUSES
    assert tuple(enums["family_confirmed_reasons"]) == episode.FAMILY_CONFIRMED_REASONS
    assert tuple(enums["episode_observation_statuses"]) == (episode.EPISODE_OBSERVATION_STATUSES)
    assert tuple(enums["ratio_statuses"]) == episode.RATIO_STATUSES
    contract_text = CONTRACT.read_text(encoding="utf-8")
    assert "post_merge_regression" not in enums
    enum_values: list[object] = []
    for values in enums.values():
        assert isinstance(values, list)
        enum_values.extend(values)
    assert "post_merge_regression" not in enum_values
    assert "automatic L3" in contract_text


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


def test_extreme_json_nesting_has_stable_public_and_stored_error_classes() -> None:
    raw = b"[" * 10_000 + b"0" + b"]" * 10_000
    assert len(raw) < episode.MAX_STDIN_BYTES
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._strict_json_document(raw)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        episode._strict_stored_json(raw + b"\n", maximum_bytes=len(raw) + 1)

    module = (
        Path(__file__).resolve().parents[1]
        / "scripts/orchestration/invariant_family_review_episode.py"
    )
    completed = subprocess.run(
        [sys.executable, str(module), "enroll"],
        input=raw,
        check=False,
        capture_output=True,
        timeout=60,
    )
    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr == b"E_LIMIT\n"


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
        "GITHUB_TOKEN",
        "API_KEY",
        "Authorization",
        "gItHuB_tOkEn",
        "ghs_secretlikevalue123456",
        "AIza_shape",
        "AKIA_shape",
        "glpat-shape",
        "github_pat_shape",
        "sk-aaaaaaaaaaaa",
        "xoxd-secretlike",
        "xoxe-secretlike",
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


def test_exact_enrollment_replay_rejects_orphan_lane_entry(anchor: _Anchor) -> None:
    document = _enrollment()
    ack = _run(anchor, "enroll", document)
    path = _receipt_path(anchor, "enrollments", ack["episode_digest"])
    before = path.stat()
    before_bytes = path.read_bytes()
    lane = path.parent.parent
    orphan = lane / ".stage-orphan"
    orphan.mkdir(mode=0o700)

    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "enroll", document)

    after = path.stat()
    assert path.read_bytes() == before_bytes
    assert (after.st_ino, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    assert orphan.is_dir()


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


def test_exact_and_divergent_terminal_replays_preserve_first_receipt(
    anchor: _Anchor,
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    terminal = _terminal_available(enrollment_ack, baseline, baseline_ack)
    _run(anchor, "terminal", terminal)
    path = _receipt_path(anchor, "terminals", enrollment_ack["episode_digest"])
    before = path.read_bytes()

    divergent = copy.deepcopy(terminal)
    divergent["terminal_material_head_sha"] = "e" * 40
    with pytest.raises(episode.EpisodeError, match="E_REPLAY_DIVERGENT"):
        _run(anchor, "terminal", divergent)
    assert path.read_bytes() == before

    orphan = path.parent.parent / ".stage-orphan"
    orphan.mkdir(mode=0o700)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "terminal", terminal)
    assert path.read_bytes() == before
    assert orphan.is_dir()


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


def test_wrong_depth_store_object_fails_closed(anchor: _Anchor) -> None:
    ack = _run(anchor, "enroll", _enrollment())
    terminal_bundle = (
        anchor.path
        / "artifacts/orchestration/review_invariant_family_episodes/terminals"
        / str(ack["episode_digest"])
    )
    nested = terminal_bundle / "nested"
    nested.mkdir(parents=True, mode=0o700)
    nested_receipt = nested / "receipt.json"
    nested_receipt.write_bytes(b"{}\n")
    nested_receipt.chmod(0o600)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
        _run(anchor, "report", _report_request())


def test_device_leaf_fails_closed(anchor: _Anchor, monkeypatch: pytest.MonkeyPatch) -> None:
    device_fd = os.open(os.devnull, os.O_RDONLY | os.O_NONBLOCK)
    try:
        assert stat.S_ISCHR(os.fstat(device_fd).st_mode)
        monkeypatch.setattr(
            episode.os,
            "open",
            lambda *_args, **_kwargs: os.dup(device_fd),
        )
        with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
            episode._read_stable_leaf(
                anchor.fd,
                "receipt.json",
                maximum_bytes=episode.MAX_ENROLLMENT_RECEIPT_BYTES,
            )
    finally:
        os.close(device_fd)


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


def test_cold_store_initialization_is_serialized_before_root_visibility(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_open_verified_directory = episode._open_verified_directory
    root_visible = threading.Event()
    release_creator = threading.Event()
    creator_results: list[dict[str, object]] = []
    creator_errors: list[Exception] = []

    def pausing_open_verified_directory(
        parent_fd: int,
        name: str,
        *,
        create: bool,
        exact_mode: bool,
    ) -> tuple[int, bool]:
        result: tuple[int, bool] = real_open_verified_directory(
            parent_fd,
            name,
            create=create,
            exact_mode=exact_mode,
        )
        if (
            name == episode.STORE_COMPONENTS[-1]
            and result[1]
            and threading.current_thread().name == "store-creator"
        ):
            root_visible.set()
            if not release_creator.wait(timeout=5):
                raise AssertionError("creator release was not signaled")
        return result

    def create_store() -> None:
        try:
            creator_results.append(_run(anchor, "enroll", _enrollment()))
        except Exception as error:
            creator_errors.append(error)

    monkeypatch.setattr(
        episode,
        "_open_verified_directory",
        pausing_open_verified_directory,
    )
    creator = threading.Thread(target=create_store, name="store-creator")
    creator.start()
    try:
        assert root_visible.wait(timeout=5)
        with pytest.raises(episode.EpisodeError, match="E_LOCK_BUSY"):
            _run(anchor, "enroll", _enrollment(18))
    finally:
        release_creator.set()
        creator.join(timeout=5)

    assert not creator.is_alive()
    assert creator_errors == []
    assert len(creator_results) == 1
    assert _run(anchor, "enroll", _enrollment()) == creator_results[0]


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
    file_fsync_failed = False

    def failing_fsync(descriptor: int) -> None:
        nonlocal file_fsync_failed
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            file_fsync_failed = True
            raise OSError("synthetic fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(episode.os, "fsync", failing_fsync)
    document = _enrollment(302)
    expected_digest = episode._episode_digest(302)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", document)
    assert file_fsync_failed
    assert not _receipt_path(anchor, "enrollments", expected_digest).exists()


def test_parent_fsync_failure_after_rename_preserves_published_bundle(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(anchor, "enroll", _enrollment(401))
    real_fsync = episode.os.fsync
    lane = anchor.path / "artifacts/orchestration/review_invariant_family_episodes/enrollments"
    lane_metadata = lane.stat()
    document = _enrollment(402)
    expected_digest = episode._episode_digest(402)
    published = _receipt_path(anchor, "enrollments", expected_digest)
    parent_fsync_failed = False

    def failing_post_rename_parent_fsync(descriptor: int) -> None:
        nonlocal parent_fsync_failed
        metadata = os.fstat(descriptor)
        if (metadata.st_dev, metadata.st_ino) == (
            lane_metadata.st_dev,
            lane_metadata.st_ino,
        ) and published.is_file():
            parent_fsync_failed = True
            raise OSError("synthetic parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(episode.os, "fsync", failing_post_rename_parent_fsync)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", document)
    assert parent_fsync_failed
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


def test_divergent_concurrent_winner_is_preserved_and_loser_fails(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested = _enrollment()
    winner_document = _enrollment()
    winner_document["material_head_sha"] = "e" * 40
    winner_bytes = episode._canonical_json_bytes(
        episode._build_enrollment_receipt(winner_document),
        trailing_lf=True,
    )

    def publish_divergent_winner(lane_fd: int, _stage_name: str, final_name: str) -> None:
        os.mkdir(final_name, 0o700, dir_fd=lane_fd)
        final_fd = os.open(final_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=lane_fd)
        try:
            os.fchmod(final_fd, 0o700)
            winner_fd = os.open(
                "receipt.json",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=final_fd,
            )
            try:
                os.fchmod(winner_fd, 0o600)
                offset = 0
                while offset < len(winner_bytes):
                    written = os.write(winner_fd, winner_bytes[offset:])
                    assert written > 0
                    offset += written
            finally:
                os.close(winner_fd)
        finally:
            os.close(final_fd)
        raise OSError(errno.EEXIST, "synthetic divergent winner")

    monkeypatch.setattr(
        episode,
        "_kernel_rename_noreplace",
        publish_divergent_winner,
    )
    with pytest.raises(episode.EpisodeError, match="E_REPLAY_DIVERGENT"):
        _run(anchor, "enroll", requested)
    winner_path = _receipt_path(anchor, "enrollments", episode._episode_digest(17))
    assert winner_path.read_bytes() == winner_bytes
    assert all(not entry.name.startswith(".stage-") for entry in winner_path.parent.iterdir())


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
        timeout=60,
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


def test_stdout_and_stderr_bounds_cover_exact_maximum_and_plus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ack = {
        "schema_version": "invariant_family_review_episode.ack.v1",
        "status": "ok",
        "operation": "enroll",
        "episode_digest": "a" * 64,
        "enrollment_receipt_digest": "b" * 64,
    }
    rendered_ack = episode._canonical_json_bytes(ack, trailing_lf=True)
    writes: list[bytes] = []
    original_write = os.write
    captured_descriptor = sys.stdout.fileno()

    def capture_write(descriptor: int, data: bytes) -> int:
        if descriptor == captured_descriptor:
            writes.append(bytes(data))
            return len(data)
        return original_write(descriptor, data)

    monkeypatch.setattr(episode.os, "write", capture_write)
    monkeypatch.setattr(episode, "MAX_STDOUT_BYTES", len(rendered_ack))
    episode._write_ack(ack)
    assert b"".join(writes) == rendered_ack

    writes.clear()
    monkeypatch.setattr(episode, "MAX_STDOUT_BYTES", len(rendered_ack) - 1)
    with pytest.raises(episode.EpisodeError, match="E_STDOUT"):
        episode._write_ack(ack)
    assert writes == []

    rendered_error = b"E_SCHEMA\n"
    captured_descriptor = sys.stderr.fileno()
    monkeypatch.setattr(episode, "MAX_STDERR_BYTES", len(rendered_error))
    episode._write_error("E_SCHEMA")
    assert writes == [rendered_error]

    writes.clear()
    monkeypatch.setattr(episode, "MAX_STDERR_BYTES", len(rendered_error) - 1)
    episode._write_error("E_SCHEMA")
    assert writes == []


def test_enrollment_receipt_publish_bound_accepts_exact_and_rejects_plus_one(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    exact_document = _enrollment(801)
    exact_bytes = episode._canonical_json_bytes(
        episode._build_enrollment_receipt(exact_document),
        trailing_lf=True,
    )
    monkeypatch.setattr(episode, "MAX_ENROLLMENT_RECEIPT_BYTES", len(exact_bytes))
    _run(anchor, "enroll", exact_document)

    oversized_document = _enrollment(802)
    oversized_bytes = episode._canonical_json_bytes(
        episode._build_enrollment_receipt(oversized_document),
        trailing_lf=True,
    )
    monkeypatch.setattr(
        episode,
        "MAX_ENROLLMENT_RECEIPT_BYTES",
        len(oversized_bytes) - 1,
    )
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "enroll", oversized_document)


def test_terminal_receipt_publish_bound_accepts_exact_and_rejects_plus_one(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_enrollment = _run(anchor, "enroll", _enrollment(811))
    first_baseline = _baseline(first_enrollment)
    first_baseline_ack = _run(anchor, "validate", first_baseline)
    first_terminal = _terminal_available(
        first_enrollment,
        first_baseline,
        first_baseline_ack,
    )
    first_receipt = episode._build_terminal_receipt(
        first_terminal,
        episode._build_enrollment_receipt(_enrollment(811)),
    )
    first_bytes = episode._canonical_json_bytes(first_receipt, trailing_lf=True)
    monkeypatch.setattr(episode, "MAX_TERMINAL_RECEIPT_BYTES", len(first_bytes))
    _run(anchor, "terminal", first_terminal)

    second_enrollment = _run(anchor, "enroll", _enrollment(812))
    second_baseline = _baseline(second_enrollment)
    second_baseline_ack = _run(anchor, "validate", second_baseline)
    second_terminal = _terminal_available(
        second_enrollment,
        second_baseline,
        second_baseline_ack,
    )
    second_receipt = episode._build_terminal_receipt(
        second_terminal,
        episode._build_enrollment_receipt(_enrollment(812)),
    )
    second_bytes = episode._canonical_json_bytes(second_receipt, trailing_lf=True)
    monkeypatch.setattr(episode, "MAX_TERMINAL_RECEIPT_BYTES", len(second_bytes) - 1)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "terminal", second_terminal)


def test_report_artifact_bounds_accept_exact_and_reject_plus_one(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrollment_ack = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrollment_ack)
    baseline_ack = _run(anchor, "validate", baseline)
    _run(anchor, "terminal", _terminal_available(enrollment_ack, baseline, baseline_ack))
    with episode._StoreSession(anchor.fd, exclusive=False, create=False) as session:
        enrollments, aggregate_bytes = episode._scan_enrollments(session)
        terminals, _ = episode._scan_terminals(session, enrollments, aggregate_bytes)
    _, report_json, markdown = episode._build_report_artifacts(
        "2026-08-15T10:05:00Z",
        enrollments,
        terminals,
    )
    boundaries = (
        ("MAX_REPORT_JSON_BYTES", len(report_json)),
        ("MAX_REPORT_MARKDOWN_BYTES", len(markdown)),
        ("MAX_REPORT_BUNDLE_BYTES", len(report_json) + len(markdown)),
    )
    for attribute, exact_size in boundaries:
        with monkeypatch.context() as scoped:
            scoped.setattr(episode, attribute, exact_size)
            episode._build_report_artifacts(
                "2026-08-15T10:05:00Z",
                enrollments,
                terminals,
            )
        with monkeypatch.context() as scoped:
            scoped.setattr(episode, attribute, exact_size - 1)
            with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
                episode._build_report_artifacts(
                    "2026-08-15T10:05:00Z",
                    enrollments,
                    terminals,
                )


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


def test_terminal_capacity_bound_allows_replay_but_rejects_new_bundle(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_enrollment = _run(anchor, "enroll", _enrollment(821))
    first_baseline = _baseline(first_enrollment)
    first_baseline_ack = _run(anchor, "validate", first_baseline)
    first_terminal = _terminal_available(
        first_enrollment,
        first_baseline,
        first_baseline_ack,
    )
    first_ack = _run(anchor, "terminal", first_terminal)

    second_enrollment = _run(anchor, "enroll", _enrollment(822))
    second_baseline = _baseline(second_enrollment)
    second_baseline_ack = _run(anchor, "validate", second_baseline)
    second_terminal = _terminal_available(
        second_enrollment,
        second_baseline,
        second_baseline_ack,
    )

    monkeypatch.setattr(episode, "MAX_TERMINAL_BUNDLES", 1)
    assert _run(anchor, "terminal", first_terminal) == first_ack
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "terminal", second_terminal)


def test_joint_terminal_crosswalk_and_combined_membership_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enrollment = episode._build_enrollment_receipt(_enrollment())
    baseline = _baseline(enrollment)

    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_IDENTITY_ROWS", 3)
        normalized_baseline = episode._normalize_joint_pass_baseline(baseline, enrollment)
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_IDENTITY_ROWS", 2)
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            episode._normalize_joint_pass_baseline(baseline, enrollment)

    baseline_ack = {
        "joint_pass_baseline_digest": episode._joint_pass_baseline_digest(normalized_baseline)
    }
    terminal = _terminal_available(enrollment, baseline, baseline_ack)
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_IDENTITY_ROWS", 4)
        scoped.setattr(episode, "MAX_FAMILY_MEMBERSHIP_REFS", 7)
        episode._normalize_terminal_input(terminal, enrollment)
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_IDENTITY_ROWS", 3)
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            episode._normalize_terminal_input(terminal, enrollment)
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_FAMILY_MEMBERSHIP_REFS", 6)
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            episode._normalize_terminal_input(terminal, enrollment)


def test_lane_scanner_stops_after_exact_maximum_plus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Entry:
        def __init__(self, name: str) -> None:
            self.name = name

    class CountedScandir:
        def __init__(self, names: list[str]) -> None:
            self.names = names
            self.yielded = 0

        def __enter__(self) -> CountedScandir:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> CountedScandir:
            return self

        def __next__(self) -> Entry:
            if self.yielded >= len(self.names):
                raise StopIteration
            name = self.names[self.yielded]
            self.yielded += 1
            return Entry(name)

    exact_names = [f"{index:064x}" for index in range(3)]
    exact_scan = CountedScandir(list(reversed(exact_names)))
    monkeypatch.setattr(episode.os, "scandir", lambda _descriptor: exact_scan)
    assert episode._scan_lane_names(123, 3) == exact_names
    assert exact_scan.yielded == 3

    overflow_scan = CountedScandir([f"{index:064x}" for index in range(5)])
    monkeypatch.setattr(episode.os, "scandir", lambda _descriptor: overflow_scan)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        episode._scan_lane_names(123, 3)
    assert overflow_scan.yielded == 4


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


@pytest.mark.parametrize("failure_target", ["stage_directory", "lane_before_publish"])
def test_stage_and_prepublication_parent_fsync_failures_leave_no_final(
    anchor: _Anchor,
    monkeypatch: pytest.MonkeyPatch,
    failure_target: str,
) -> None:
    _run(anchor, "enroll", _enrollment(501))
    real_fsync = episode.os.fsync
    lane = anchor.path / "artifacts/orchestration/review_invariant_family_episodes/enrollments"
    lane_metadata = lane.stat()
    expected_digest = episode._episode_digest(502)
    final_path = _receipt_path(anchor, "enrollments", expected_digest)
    targeted_fsync_failed = False

    def failing_fsync(descriptor: int) -> None:
        nonlocal targeted_fsync_failed
        metadata = os.fstat(descriptor)
        is_lane = (metadata.st_dev, metadata.st_ino) == (
            lane_metadata.st_dev,
            lane_metadata.st_ino,
        )
        should_fail = (
            failure_target == "stage_directory" and stat.S_ISDIR(metadata.st_mode) and not is_lane
        ) or (failure_target == "lane_before_publish" and is_lane and not final_path.exists())
        if should_fail:
            targeted_fsync_failed = True
            raise OSError("synthetic fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(episode.os, "fsync", failing_fsync)
    with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
        _run(anchor, "enroll", _enrollment(502))
    assert targeted_fsync_failed
    assert not final_path.exists()


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


# Supervision uses the existing v1 inputs and the same fixed-store publisher.
def _status_request(pr_number: int = 17) -> dict[str, object]:
    return {
        "schema_version": "invariant_family_review_episode.status_request.v1",
        "pull_request_number": pr_number,
    }


def _complete_request(
    terminal: Mapping[str, object], as_of: str = "2026-08-15T10:05:00Z"
) -> dict[str, object]:
    return {
        "schema_version": "invariant_family_review_episode.complete_input.v1",
        "terminal": copy.deepcopy(dict(terminal)),
        "report_request": _report_request(as_of),
    }


def _supervised_episode(
    anchor: _Anchor, pr_number: int = 17
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    enrolled = _run(anchor, "enroll", _enrollment(pr_number))
    baseline = _baseline(enrolled)
    checkpoint = _run(anchor, "checkpoint", baseline)
    terminal = _terminal_available(enrolled, baseline, checkpoint)
    return enrolled, baseline, terminal


def _store_snapshot(anchor: _Anchor) -> dict[str, tuple[int, int, int, bytes]]:
    root = anchor.path / "artifacts"
    result: dict[str, tuple[int, int, int, bytes]] = {}
    for path in sorted(root.rglob("*")) if root.exists() else []:
        metadata = path.lstat()
        result[str(path.relative_to(anchor.path))] = (
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_mtime_ns,
            path.read_bytes() if path.is_file() and not path.is_symlink() else b"",
        )
    return result


def test_supervision_projection_is_separate_frozen_and_contract_bound() -> None:
    original = json.dumps(_thaw(episode.POLICY_PROJECTION), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(original.encode()).hexdigest() == (
        "a1f725bbe336416c9038f7baa2303dd3830380709fdbcae7ec72c08568300d4b"
    )
    extension = _thaw(episode.SUPERVISION_PROJECTION)
    contract = CONTRACT.read_text(encoding="utf-8")
    marker = "SUPERVISION_PROJECTION_BEGIN\n"
    start = contract.index(marker) + len(marker)
    end = contract.index("\nSUPERVISION_PROJECTION_END", start)
    assert extension == json.loads(contract[start:end])
    assert extension["verbs"] == ["checkpoint", "status", "complete"]
    assert extension["downstream_grants"] == dict.fromkeys(episode.AUTHORITY_FIELDS, False)
    assert len(extension["downstream_grants"]) == 16
    with pytest.raises(TypeError):
        operator.setitem(episode.SUPERVISION_PROJECTION, "verbs", ())


@pytest.mark.parametrize("ancestors", [0, 1, 2])
def test_status_absent_store_never_creates_storage(anchor: _Anchor, ancestors: int) -> None:
    current = anchor.path
    for name in ("artifacts", "orchestration")[:ancestors]:
        current = current / name
        current.mkdir(mode=0o700)
    before = _store_snapshot(anchor)
    result = _run(anchor, "status", _status_request())
    assert result["lifecycle"] == "absent"
    assert result["report_status"] == "absent"
    assert "enrollment_receipt_digest" not in result
    assert _store_snapshot(anchor) == before
    assert all(value is False for value in result["downstream_grants"].values())
    assert None not in result.values()


@pytest.mark.parametrize("bad_pr", [True, 0, -1, "17", None])
def test_status_rejects_noncanonical_identity(anchor: _Anchor, bad_pr: object) -> None:
    request = _status_request()
    request["pull_request_number"] = bad_pr
    with pytest.raises(episode.EpisodeError, match="E_SCHEMA|E_IDENTITY"):
        _run(anchor, "status", request)
    assert _store_snapshot(anchor) == {}


@pytest.mark.parametrize("verb", ["status", "complete", "checkpoint"])
def test_supervision_rejects_extra_input_fields(anchor: _Anchor, verb: str) -> None:
    enrolled = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrolled)
    terminal = _terminal_without_available_baseline(enrolled, completed=False)
    document = {
        "status": _status_request(),
        "checkpoint": baseline,
        "complete": _complete_request(terminal),
    }[verb]
    document["unexpected"] = "invalid"
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_SCHEMA"):
        _run(anchor, verb, document)
    assert _store_snapshot(anchor) == before


def test_checkpoint_requires_accepted_enrollment_and_validated_binding(anchor: _Anchor) -> None:
    proposed = episode._build_enrollment_receipt(_enrollment())
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, "checkpoint", _baseline(proposed))
    assert _store_snapshot(anchor) == {}
    enrolled = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrolled)
    baseline["enrollment_receipt_digest"] = "e" * 64
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, "checkpoint", baseline)
    assert _store_snapshot(anchor) == before


def test_checkpoint_persists_normalized_j_and_validate_ack_replays_after_terminal(
    anchor: _Anchor,
) -> None:
    enrolled = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrolled)
    validate_ack = _run(anchor, "validate", baseline)
    report_before = _run(anchor, "report", _report_request())
    checkpoint_ack = _run(anchor, "checkpoint", baseline)
    checkpoint_path = _receipt_path(anchor, "checkpoints", enrolled["episode_digest"])
    checkpoint = _load_json(checkpoint_path)
    assert checkpoint["validate_acknowledgement"] == validate_ack
    assert checkpoint["baseline"]["families"][0]["joint_pass_cumulative_identity_class_ids"] == [
        "class_a",
        "class_b",
        "class_c",
    ]
    assert checkpoint["joint_pass_baseline_digest"] == validate_ack["joint_pass_baseline_digest"]
    assert stat.S_IMODE(checkpoint_path.stat().st_mode) == 0o600
    assert _run(anchor, "report", _report_request()) == report_before
    assert _run(anchor, "status", _status_request())["lifecycle"] == "enrolled_awaiting_terminal"
    before = _store_snapshot(anchor)
    assert _run(anchor, "checkpoint", baseline) == checkpoint_ack
    assert _store_snapshot(anchor) == before
    _run(anchor, "terminal", _terminal_available(enrolled, baseline, validate_ack))
    before = _store_snapshot(anchor)
    assert _run(anchor, "checkpoint", baseline) == checkpoint_ack
    assert _store_snapshot(anchor) == before


def test_checkpoint_divergence_and_validate_agreement_fail_without_writes(anchor: _Anchor) -> None:
    _enrolled, baseline, _terminal = _supervised_episode(anchor)
    baseline["joint_pass_completed_at"] = "2026-08-15T10:02:01Z"
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_REPLAY_DIVERGENT"):
        _run(anchor, "checkpoint", baseline)
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, "validate", baseline)
    assert _store_snapshot(anchor) == before


@pytest.mark.parametrize("completed", [False, True])
def test_honest_completion_without_checkpoint_preserves_observation(
    anchor: _Anchor, completed: bool
) -> None:
    enrolled = _run(anchor, "enroll", _enrollment())
    terminal = _terminal_without_available_baseline(enrolled, completed=completed)
    result = _run(anchor, "complete", _complete_request(terminal))
    status = _run(anchor, "status", _status_request())
    assert result["lifecycle"] == status["lifecycle"] == "complete"
    assert status["observation_status"] == ("unknown" if completed else "not_applicable")
    assert "checkpoint_receipt_digest" not in status
    before = _store_snapshot(anchor)
    assert _run(anchor, "complete", _complete_request(terminal)) == result
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        _run(anchor, "checkpoint", _baseline(enrolled))
    assert _store_snapshot(anchor) == before


def test_available_complete_requires_checkpoint_but_legacy_terminal_does_not(
    anchor: _Anchor,
) -> None:
    enrolled = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrolled)
    acknowledged = _run(anchor, "validate", baseline)
    terminal = _terminal_available(enrolled, baseline, acknowledged)
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, "complete", _complete_request(terminal))
    assert _store_snapshot(anchor) == before
    _run(anchor, "terminal", terminal)
    _run(anchor, "report", _report_request())
    assert _run(anchor, "status", _status_request())["lifecycle"] == "complete"
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        _run(anchor, "checkpoint", baseline)


@pytest.mark.parametrize("verb", ["terminal", "complete"])
@pytest.mark.parametrize("claim", ["unavailable", "not_completed", "divergent"])
def test_checkpoint_rejects_contradictory_terminal_before_multi_trigger_precedence(
    anchor: _Anchor, verb: str, claim: str
) -> None:
    enrolled, baseline, terminal = _supervised_episode(anchor)
    if claim != "divergent":
        terminal = _terminal_without_available_baseline(enrolled, completed=claim == "unavailable")
    else:
        baseline["families"][0]["recommended_resolution"] = "mechanism_fix"
        enrollment_receipt = _load_json(
            _receipt_path(anchor, "enrollments", enrolled["episode_digest"])
        )
        normalized = episode._normalize_joint_pass_baseline(baseline, enrollment_receipt)
        terminal["joint_pass"]["baseline"] = baseline
        terminal["joint_pass"]["joint_pass_baseline_digest"] = episode._joint_pass_baseline_digest(
            normalized
        )
    terminal["observed_l2_identity_digests"].append("d" * 64)
    document = _complete_request(terminal) if verb == "complete" else terminal
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
        _run(anchor, verb, document)
    assert _store_snapshot(anchor) == before


def test_orphan_checkpoint_cannot_be_repaired_by_enrollment(anchor: _Anchor) -> None:
    enrolled, _baseline_value, _terminal = _supervised_episode(anchor)
    path = _receipt_path(anchor, "enrollments", enrolled["episode_digest"])
    path.unlink()
    path.parent.rmdir()
    before = _store_snapshot(anchor)
    for verb, document in (
        ("enroll", _enrollment()),
        ("status", _status_request()),
        ("report", _report_request()),
    ):
        with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
            _run(anchor, verb, document)
    assert _store_snapshot(anchor) == before


@pytest.mark.parametrize("corruption", ["ack", "baseline", "digest", "grant", "extra"])
def test_checkpoint_receipt_is_fully_revalidated(anchor: _Anchor, corruption: str) -> None:
    enrolled, baseline, terminal = _supervised_episode(anchor)
    path = _receipt_path(anchor, "checkpoints", enrolled["episode_digest"])
    receipt = _load_json(path)
    if corruption == "ack":
        receipt["validate_acknowledgement"]["joint_pass_baseline_digest"] = "f" * 64
    elif corruption == "baseline":
        receipt["baseline"]["joint_pass_completed_at"] = "2026-08-15T10:02:01Z"
    elif corruption == "digest":
        receipt["checkpoint_receipt_digest"] = "f" * 64
    elif corruption == "grant":
        receipt["downstream_grants"]["merge_authority"] = True
    else:
        receipt["extra"] = "invalid"
    path.write_bytes(episode._canonical_json_bytes(receipt, trailing_lf=True))
    before = _store_snapshot(anchor)
    for verb, document in (
        ("status", _status_request()),
        ("checkpoint", baseline),
        ("terminal", terminal),
        ("report", _report_request()),
    ):
        with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
            _run(anchor, verb, document)
    assert _store_snapshot(anchor) == before


def test_status_uses_entire_current_store_and_latest_matching_report(anchor: _Anchor) -> None:
    first, _baseline_value, terminal = _supervised_episode(anchor)
    assert _run(anchor, "status", _status_request())["report_status"] == "absent"
    _run(anchor, "complete", _complete_request(terminal))
    later = _run(anchor, "report", _report_request("2026-08-15T10:06:00Z"))
    status = _run(anchor, "status", _status_request())
    assert status["lifecycle"] == "complete"
    assert status["report_digest"] == later["report_digest"]
    second = _run(anchor, "enroll", _enrollment(18))
    status = _run(anchor, "status", _status_request())
    assert status["lifecycle"] == "terminal_awaiting_report"
    assert status["report_status"] == "stale"
    report = _run(anchor, "report", _report_request("2026-08-15T10:07:00Z"))
    assert _run(anchor, "status", _status_request())["report_digest"] == report["report_digest"]
    assert (
        _run(anchor, "status", _status_request(18))["lifecycle"] == "enrolled_awaiting_checkpoint"
    )
    _run(anchor, "terminal", _terminal_without_available_baseline(second, completed=False))
    assert _run(anchor, "status", _status_request())["report_status"] == "stale"
    assert (
        _run(anchor, "status", _status_request())["enrollment_receipt_digest"]
        == first["enrollment_receipt_digest"]
    )


def test_complete_prevalidates_cutoff_and_report_capacity_before_terminal(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enrolled, _baseline_value, terminal = _supervised_episode(anchor)
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        _run(anchor, "complete", _complete_request(terminal, "2026-08-15T10:03:00Z"))
    assert _store_snapshot(anchor) == before
    _run(anchor, "report", _report_request())
    before = _store_snapshot(anchor)
    monkeypatch.setattr(episode, "MAX_REPORT_GENERATIONS", 1)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "complete", _complete_request(terminal))
    assert _store_snapshot(anchor) == before


def test_complete_and_checkpoint_exact_replay_at_capacity(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrolled, baseline, terminal = _supervised_episode(anchor)
    result = _run(anchor, "complete", _complete_request(terminal))
    for limit in ("MAX_TERMINAL_BUNDLES", "MAX_CHECKPOINT_BUNDLES", "MAX_REPORT_GENERATIONS"):
        monkeypatch.setattr(episode, limit, 1)
    before = _store_snapshot(anchor)
    assert _run(anchor, "complete", _complete_request(terminal)) == result
    _run(anchor, "checkpoint", baseline)
    assert _store_snapshot(anchor) == before
    other = _run(anchor, "enroll", _enrollment(18))
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "checkpoint", _baseline(other))
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(
            anchor,
            "complete",
            _complete_request(_terminal_without_available_baseline(other, completed=False)),
        )
    assert _store_snapshot(anchor) == before
    assert enrolled["episode_digest"] != other["episode_digest"]


def test_checkpoint_bytes_share_aggregate_scan_budget(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrolled, _baseline_value, terminal = _supervised_episode(anchor)
    _run(anchor, "complete", _complete_request(terminal))
    total = sum(
        _receipt_path(anchor, lane, enrolled["episode_digest"]).stat().st_size
        for lane in ("enrollments", "checkpoints", "terminals")
    )
    monkeypatch.setattr(episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", total)
    assert _run(anchor, "status", _status_request())["lifecycle"] == "complete"
    monkeypatch.setattr(episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", total - 1)
    for verb, request in (
        ("status", _status_request()),
        ("report", _report_request()),
        ("complete", _complete_request(terminal)),
    ):
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, verb, request)


@pytest.mark.parametrize("failed_lane", ["terminals", "reports"])
def test_complete_resumes_after_publication_and_fsync_failure(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch, failed_lane: str
) -> None:
    _enrolled, _baseline_value, terminal = _supervised_episode(anchor)
    original_publish = episode._publish_bundle
    failed = False

    def publish_then_fail(*args: object, **kwargs: object) -> None:
        nonlocal failed
        original_publish(*args, **kwargs)
        if kwargs["lane_name"] == failed_lane and not failed:
            failed = True
            raise episode.EpisodeError("E_PUBLISH_FAILED")

    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "_publish_bundle", publish_then_fail)
        with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
            _run(anchor, "complete", _complete_request(terminal))
    status = _run(anchor, "status", _status_request())
    assert status["lifecycle"] == (
        "complete" if failed_lane == "reports" else "terminal_awaiting_report"
    )
    stored_terminal = _receipt_path(anchor, "terminals", terminal["episode_digest"])
    before = (stored_terminal.stat().st_ino, stored_terminal.read_bytes())
    completed = _run(anchor, "complete", _complete_request(terminal))
    assert completed["lifecycle"] == "complete"
    assert (stored_terminal.stat().st_ino, stored_terminal.read_bytes()) == before


def test_complete_report_failure_and_advanced_store_rejects_stale_retry(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enrolled, _baseline_value, terminal = _supervised_episode(anchor)

    def failed_report(*_args: object, **_kwargs: object) -> None:
        raise episode.EpisodeError("E_PUBLISH_FAILED")

    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "_publish_report", failed_report)
        with pytest.raises(episode.EpisodeError, match="E_PUBLISH_FAILED"):
            _run(anchor, "complete", _complete_request(terminal))
    later_enrollment = _enrollment(18)
    later_enrollment["enrollment_recorded_at"] = "2026-08-15T10:06:00Z"
    _run(anchor, "enroll", later_enrollment)
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_ORDER"):
        _run(anchor, "complete", _complete_request(terminal))
    assert _store_snapshot(anchor) == before
    assert (
        _run(anchor, "complete", _complete_request(terminal, "2026-08-15T10:07:00Z"))["lifecycle"]
        == "complete"
    )


def test_complete_holds_one_exclusive_lock_across_both_publications(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enrolled, _baseline_value, terminal = _supervised_episode(anchor)
    entered = threading.Barrier(2)
    release = threading.Barrier(2)
    original_publish = episode._publish_terminal
    errors: list[Exception] = []
    results: list[dict[str, object]] = []

    def paused_terminal(*args: object, **kwargs: object) -> None:
        original_publish(*args, **kwargs)
        entered.wait(timeout=10)
        release.wait(timeout=10)

    def complete() -> None:
        try:
            results.append(_run(anchor, "complete", _complete_request(terminal)))
        except Exception as error:
            errors.append(error)

    monkeypatch.setattr(episode, "_publish_terminal", paused_terminal)
    worker = threading.Thread(target=complete)
    worker.start()
    try:
        entered.wait(timeout=10)
        for verb, request in (
            ("status", _status_request()),
            ("complete", _complete_request(terminal)),
        ):
            with pytest.raises(episode.EpisodeError, match="E_LOCK_BUSY"):
                _run(anchor, verb, request)
    finally:
        release.wait(timeout=10)
        worker.join(timeout=10)
    assert not worker.is_alive()
    assert errors == []
    assert results[0]["lifecycle"] == "complete"


class _SupervisionSequence:
    """Independent local lifecycle model for the finite operation recipes below."""

    def __init__(self, anchor: _Anchor, case: int) -> None:
        self.anchor = anchor
        self.pr_number = 100 + 2 * case
        self.completed_without_baseline = case % 2 == 0
        self.positive = case % 3 == 0
        self.enrolled: dict[str, object] = {}
        self.baseline: dict[str, object] = {}
        self.checkpoint: dict[str, object] = {}
        self.terminal: dict[str, object] = {}
        self.report_state = "absent"
        self.other_enrolled = False

    def lifecycle(self) -> str:
        if self.terminal:
            return "complete" if self.report_state == "current" else "terminal_awaiting_report"
        if self.checkpoint:
            return "enrolled_awaiting_terminal"
        return "enrolled_awaiting_checkpoint" if self.enrolled else "absent"

    def terminal_input(self) -> dict[str, object]:
        if self.terminal:
            return self.terminal
        if self.checkpoint:
            return _terminal_available(
                self.enrolled, self.baseline, self.checkpoint, positive=self.positive
            )
        return _terminal_without_available_baseline(
            self.enrolled, completed=self.completed_without_baseline
        )

    def step(self, operation: str) -> str:
        before = _store_snapshot(self.anchor)
        no_write = False
        label = operation
        if operation == "status":
            _run(self.anchor, "status", _status_request(self.pr_number))
            no_write = True
        elif operation == "enroll":
            no_write = bool(self.enrolled)
            label = "enroll_replay" if no_write else "enroll_first"
            actual = _run(self.anchor, "enroll", _enrollment(self.pr_number))
            if self.enrolled:
                assert actual == self.enrolled
            else:
                self.enrolled = actual
                self.baseline = _baseline(actual)
                if self.report_state == "current":
                    self.report_state = "stale"
        elif operation == "other_enroll":
            no_write = self.other_enrolled
            label = "other_enroll_replay" if no_write else "other_enroll_first"
            _run(self.anchor, "enroll", _enrollment(self.pr_number + 1))
            self.other_enrolled = True
            if not no_write and self.report_state == "current":
                self.report_state = "stale"
        elif operation == "checkpoint":
            assert self.enrolled
            no_write = bool(self.checkpoint) or bool(self.terminal)
            if self.terminal and not self.checkpoint:
                label = "checkpoint_after_terminal_rejected"
                with pytest.raises(episode.EpisodeError, match="E_ORDER"):
                    _run(self.anchor, "checkpoint", self.baseline)
            else:
                label = (
                    "checkpoint_after_terminal_replay"
                    if self.terminal
                    else "checkpoint_replay" if self.checkpoint else "checkpoint_first"
                )
                actual = _run(self.anchor, "checkpoint", self.baseline)
                if self.checkpoint:
                    assert actual == self.checkpoint
                self.checkpoint = actual
        elif operation in ("checkpoint_divergent", "enroll_divergent", "complete_divergent"):
            no_write = True
            label += "_rejected"
            if operation == "checkpoint_divergent":
                assert self.checkpoint
                verb, document = "checkpoint", copy.deepcopy(self.baseline)
                document["joint_pass_completed_at"] = "2026-08-15T10:02:01Z"
            elif operation == "enroll_divergent":
                assert self.enrolled
                verb, document = "enroll", _enrollment(self.pr_number)
                document["material_head_sha"] = "f" * 40
            else:
                assert self.terminal
                changed = copy.deepcopy(self.terminal)
                changed["terminal_material_head_sha"] = "a" * 40
                verb, document = "complete", _complete_request(changed)
            with pytest.raises(episode.EpisodeError, match="E_REPLAY_DIVERGENT"):
                _run(self.anchor, verb, document)
        elif operation == "complete_absent":
            assert not self.enrolled
            no_write = True
            label = "complete_absent_rejected"
            proposed = episode._build_enrollment_receipt(_enrollment(self.pr_number))
            terminal = _terminal_without_available_baseline(proposed, completed=False)
            with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
                _run(self.anchor, "complete", _complete_request(terminal))
        elif operation == "complete_cutoff":
            no_write = True
            label = "complete_cutoff_rejected"
            with pytest.raises(episode.EpisodeError, match="E_ORDER"):
                _run(
                    self.anchor,
                    "complete",
                    _complete_request(self.terminal_input(), "2026-08-15T10:03:00Z"),
                )
        elif operation in ("terminal", "complete"):
            assert self.enrolled
            terminal = self.terminal_input()
            if operation == "terminal":
                no_write = bool(self.terminal)
                label = "terminal_replay" if no_write else "terminal_first"
                _run(self.anchor, "terminal", terminal)
                if not no_write and self.report_state == "current":
                    self.report_state = "stale"
            else:
                no_write = bool(self.terminal) and self.report_state == "current"
                label = (
                    "complete_replay"
                    if no_write
                    else (
                        "complete_resume"
                        if self.terminal
                        else (
                            "complete_first_with_checkpoint"
                            if self.checkpoint
                            else "complete_first_without_checkpoint"
                        )
                    )
                )
                _run(self.anchor, "complete", _complete_request(terminal))
                self.report_state = "current"
            self.terminal = terminal
        elif operation == "report":
            no_write = self.report_state == "current"
            _run(self.anchor, "report", _report_request())
            self.report_state = "current"
        else:
            raise AssertionError(f"unknown sequence operation: {operation}")
        if no_write:
            assert _store_snapshot(self.anchor) == before
        return label

    def assert_status(self) -> None:
        before = _store_snapshot(self.anchor)
        result = _run(self.anchor, "status", _status_request(self.pr_number))
        assert result["lifecycle"] == self.lifecycle()
        assert result["report_status"] == self.report_state
        assert ("enrollment_receipt_digest" in result) == bool(self.enrolled)
        assert ("checkpoint_receipt_digest" in result) == bool(self.checkpoint)
        assert ("terminal_receipt_digest" in result) == bool(self.terminal)
        assert ("report_digest" in result) == (self.report_state == "current")
        assert result["downstream_grants"] == dict.fromkeys(episode.AUTHORITY_FIELDS, False)
        assert len(result["downstream_grants"]) == 16
        assert None not in result.values()
        assert _store_snapshot(self.anchor) == before


# Five fixed schedules vary PR identity, honest missing-baseline status and
# positive/zero observations across 25 isolated cases. No exploration/shrinking claim.
_SUPERVISION_SEQUENCES = (
    (
        "status",
        "enroll",
        "enroll",
        "checkpoint",
        "checkpoint",
        "checkpoint_divergent",
        "complete",
        "complete",
        "checkpoint",
        "complete_divergent",
        "status",
        "enroll",
        "other_enroll",
        "status",
        "report",
        "report",
        "complete",
        "checkpoint",
        "enroll_divergent",
        "status",
    ),
    (
        "status",
        "complete_absent",
        "enroll",
        "enroll",
        "complete",
        "checkpoint",
        "complete",
        "complete_divergent",
        "status",
        "other_enroll",
        "status",
        "report",
        "report",
        "complete",
        "enroll",
        "status",
        "checkpoint",
        "complete",
        "enroll_divergent",
        "status",
    ),
    (
        "status",
        "enroll",
        "checkpoint",
        "complete_cutoff",
        "status",
        "terminal",
        "status",
        "checkpoint",
        "complete_cutoff",
        "complete",
        "complete",
        "checkpoint",
        "other_enroll",
        "status",
        "report",
        "complete",
        "enroll",
        "status",
        "report",
        "status",
    ),
    (
        "status",
        "report",
        "enroll",
        "status",
        "report",
        "checkpoint",
        "status",
        "report",
        "checkpoint_divergent",
        "terminal",
        "status",
        "report",
        "complete",
        "complete_divergent",
        "checkpoint",
        "other_enroll",
        "status",
        "complete",
        "status",
        "report",
    ),
    (
        "status",
        "enroll",
        "report",
        "status",
        "terminal",
        "status",
        "checkpoint",
        "complete",
        "complete",
        "complete_divergent",
        "enroll",
        "other_enroll",
        "status",
        "report",
        "complete",
        "checkpoint",
        "status",
        "report",
        "terminal",
        "status",
    ),
)


def test_supervision_deterministic_sequences_cover_required_transitions() -> None:
    transitions: set[tuple[str, str, str]] = set()
    report_states: set[str] = set()
    operations = 0
    for case in range(25):
        recipe = _SUPERVISION_SEQUENCES[case % len(_SUPERVISION_SEQUENCES)]
        assert len(recipe) == 20
        with tempfile.TemporaryDirectory(prefix="euler-supervision-") as directory:
            anchor = _Anchor(Path(directory))
            model = _SupervisionSequence(anchor, case)
            try:
                model.assert_status()
                for step, operation in enumerate(recipe):
                    try:
                        before = model.lifecycle()
                        label = model.step(operation)
                        model.assert_status()
                        transitions.add((before, label, model.lifecycle()))
                        report_states.add(model.report_state)
                        operations += 1
                    except Exception as error:
                        raise AssertionError(
                            f"sequence={case}, step={step}, operation={operation}"
                        ) from error
            finally:
                anchor.close()
    required = {
        ("absent", "status", "absent"),
        ("absent", "complete_absent_rejected", "absent"),
        ("absent", "enroll_first", "enrolled_awaiting_checkpoint"),
        ("enrolled_awaiting_checkpoint", "enroll_replay", "enrolled_awaiting_checkpoint"),
        ("enrolled_awaiting_checkpoint", "checkpoint_first", "enrolled_awaiting_terminal"),
        ("enrolled_awaiting_terminal", "checkpoint_replay", "enrolled_awaiting_terminal"),
        (
            "enrolled_awaiting_terminal",
            "checkpoint_divergent_rejected",
            "enrolled_awaiting_terminal",
        ),
        ("enrolled_awaiting_terminal", "complete_cutoff_rejected", "enrolled_awaiting_terminal"),
        ("enrolled_awaiting_terminal", "complete_first_with_checkpoint", "complete"),
        ("enrolled_awaiting_checkpoint", "complete_first_without_checkpoint", "complete"),
        ("complete", "checkpoint_after_terminal_replay", "complete"),
        ("complete", "checkpoint_after_terminal_rejected", "complete"),
        ("complete", "complete_replay", "complete"),
        ("complete", "complete_divergent_rejected", "complete"),
        ("complete", "enroll_divergent_rejected", "complete"),
        ("complete", "other_enroll_first", "terminal_awaiting_report"),
        ("terminal_awaiting_report", "complete_resume", "complete"),
        ("terminal_awaiting_report", "report", "complete"),
    }
    assert required <= transitions, sorted(required - transitions)
    assert report_states == {"absent", "stale", "current"}
    assert operations == 25 * 20


# Captured from unmodified base 863d16ea2328dd32fa6fec6cef4d8f117b6edf85.
# Original six-case corpus SHA256:
# 0a248bfc4f10d71cd50b3a91fc6fb7ae6c55afce06341bd6b0407ca51a596205
# Keep expected acknowledgements and file hashes independent of candidate code.
_V1_GOLDEN = {
    "baseline_unavailable": {
        "report_ack": {
            "cohort_id": "8e58c3b12d4e54f51e6c6be1195610eab1667ec6eaff5dd0ac0f297996707b91",
            "markdown_sha256": "ae040ef76ddcef1186b2f85debcd847082490b3409624a7919661c53eb675bee",
            "operation": "report",
            "report_digest": "0bd6a7678c7a60e3826230f5d374a579eab2a525f1c65c50c236cdfd0f4521ba",
            "schema_version": "invariant_family_review_episode.ack.v1",
            "status": "ok",
        },
        "sha256": {
            "enrollments/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "b4d721b2c9dc0e7ed3284d671ecbed3f9cfda6a3af159ec08bc5641d6861989b",
            "reports/0bd6a7678c7a60e3826230f5d374a579eab2a525f1c65c50c236cdfd0f4521ba/report.json": "ab6506a4da73d3711a830c6dc18c9d1cab5e8dff5942fdb017730d2a6b945773",
            "reports/0bd6a7678c7a60e3826230f5d374a579eab2a525f1c65c50c236cdfd0f4521ba/report.md": "ae040ef76ddcef1186b2f85debcd847082490b3409624a7919661c53eb675bee",
            "terminals/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "338d4788212592805c494760ec3cbadc098ab09cc5305caa36d936bdccb5384a",
        },
        "terminal_digest": "5e90ca50139336409074de0ab42548202952038d3874432d602bd87e5f1f6c41",
    },
    "missing_terminal": {
        "report_ack": {
            "cohort_id": "7f588e0c456ca2ad757e2b3aa8138949d422da84c4d49e754958549ddf411e2d",
            "markdown_sha256": "c6bf10602fc23a3cfc0376e21e3b47fda8580eff71fdc4a2e4363a7d094ab68d",
            "operation": "report",
            "report_digest": "cd866dd00596e1c83feca8b9b1e5f02f0308cfcd817b0503cf9ed713e5f3316a",
            "schema_version": "invariant_family_review_episode.ack.v1",
            "status": "ok",
        },
        "sha256": {
            "enrollments/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "b4d721b2c9dc0e7ed3284d671ecbed3f9cfda6a3af159ec08bc5641d6861989b",
            "reports/cd866dd00596e1c83feca8b9b1e5f02f0308cfcd817b0503cf9ed713e5f3316a/report.json": "d0a8d8766da490ab2bd4c0f189027aca870ed3da1f1b10fc4231227108c03536",
            "reports/cd866dd00596e1c83feca8b9b1e5f02f0308cfcd817b0503cf9ed713e5f3316a/report.md": "c6bf10602fc23a3cfc0376e21e3b47fda8580eff71fdc4a2e4363a7d094ab68d",
        },
    },
    "multi_trigger": {
        "report_ack": {
            "cohort_id": "3430bb6b97052bc8040b6002882ab9585f36771b2c24affc90d592c11a39a383",
            "markdown_sha256": "34be3df93de80df77228d6ddb74ff980abae50e308569346ee8eb511a1487367",
            "operation": "report",
            "report_digest": "44d58bd87479fcf0ab68245b4d4fa0b44d4300b3f0e6d4de19284a07bd7de516",
            "schema_version": "invariant_family_review_episode.ack.v1",
            "status": "ok",
        },
        "sha256": {
            "enrollments/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "b4d721b2c9dc0e7ed3284d671ecbed3f9cfda6a3af159ec08bc5641d6861989b",
            "reports/44d58bd87479fcf0ab68245b4d4fa0b44d4300b3f0e6d4de19284a07bd7de516/report.json": "0bb592be7452fd3966165bab39cc3aeee1c35f0a1e0c954780f70dc4015c11a9",
            "reports/44d58bd87479fcf0ab68245b4d4fa0b44d4300b3f0e6d4de19284a07bd7de516/report.md": "34be3df93de80df77228d6ddb74ff980abae50e308569346ee8eb511a1487367",
            "terminals/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "247a9dad857e240b29b5361d43d5438dfb4f694413e8eb348bed336bc26cacb3",
        },
        "terminal_digest": "a0d7edad1724861a900566b3d256eba527fd8009f5078cbcedf2007c84763ba2",
    },
    "not_completed": {
        "report_ack": {
            "cohort_id": "834a4c22e83dc1df938192ecaa1c26e540b79f4cc77d551ac17b5865e8d69eac",
            "markdown_sha256": "9d8915998a5da5e1f8ca8b490d9b1a07c489b69b19e0ec1987ec34b5ee2d6615",
            "operation": "report",
            "report_digest": "9306f68bad67d8ae3f77e2e5f321bf7561528bd67fc73d9d3b73136710a9ad79",
            "schema_version": "invariant_family_review_episode.ack.v1",
            "status": "ok",
        },
        "sha256": {
            "enrollments/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "b4d721b2c9dc0e7ed3284d671ecbed3f9cfda6a3af159ec08bc5641d6861989b",
            "reports/9306f68bad67d8ae3f77e2e5f321bf7561528bd67fc73d9d3b73136710a9ad79/report.json": "ba92da35647d040bf1209787bd32ad494eea25dc85c7ad9ed5e78a875c73cb3c",
            "reports/9306f68bad67d8ae3f77e2e5f321bf7561528bd67fc73d9d3b73136710a9ad79/report.md": "9d8915998a5da5e1f8ca8b490d9b1a07c489b69b19e0ec1987ec34b5ee2d6615",
            "terminals/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "61c3373373b4bc7358db23fb6e3a575fedbd41bae10223c10dc2795da1f8807d",
        },
        "terminal_digest": "65b59199a40191201355fe3f5a0ced52170f30eeaed0f13fbd6dcc4632a0f00d",
    },
    "positive": {
        "report_ack": {
            "cohort_id": "748684f5d25a6a4b70d28a1554b0f4591ee1dc09df2bf52c42d2627e2c01e3d7",
            "markdown_sha256": "0919b8cd8fd36c3d64d8b2c73b444ea46a5e35db468da365ea0cc22e19391928",
            "operation": "report",
            "report_digest": "bacf4f9eca365c7db5b9cb6dbde6b03c2146360de79b86658482788a443321f7",
            "schema_version": "invariant_family_review_episode.ack.v1",
            "status": "ok",
        },
        "sha256": {
            "enrollments/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "b4d721b2c9dc0e7ed3284d671ecbed3f9cfda6a3af159ec08bc5641d6861989b",
            "reports/bacf4f9eca365c7db5b9cb6dbde6b03c2146360de79b86658482788a443321f7/report.json": "9043c242e224af16c401dab6465504bb632f9dbf4f01c0183ea7b56ebf6469aa",
            "reports/bacf4f9eca365c7db5b9cb6dbde6b03c2146360de79b86658482788a443321f7/report.md": "0919b8cd8fd36c3d64d8b2c73b444ea46a5e35db468da365ea0cc22e19391928",
            "terminals/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "36af114c88a9b0235378c0d7b2e2048fb4336c47ec306de1da72b289bc2dbfcc",
        },
        "terminal_digest": "495d01bf69ebfb5bb896d193dfcd5b41deee22d612bcb5a58e5876843a0f5192",
    },
    "zero": {
        "report_ack": {
            "cohort_id": "e1e54727033e2a0b2dbfac1fd2690d2cbde8c3135baf5013ed1692d974986b65",
            "markdown_sha256": "6d94f58838afbe3e2cbd3c6c2ad2685b8e08d6b253b76ed9e42d12cb52883376",
            "operation": "report",
            "report_digest": "e6820a6ee4c72dda2eddbae42584cdc1a172209782da24e3e0d1aa6660bf853b",
            "schema_version": "invariant_family_review_episode.ack.v1",
            "status": "ok",
        },
        "sha256": {
            "enrollments/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "b4d721b2c9dc0e7ed3284d671ecbed3f9cfda6a3af159ec08bc5641d6861989b",
            "reports/e6820a6ee4c72dda2eddbae42584cdc1a172209782da24e3e0d1aa6660bf853b/report.json": "eb08c2996b60ab058bd8f0d1b5da3b9135050ba3a28a0db7c8652b9320fb6e45",
            "reports/e6820a6ee4c72dda2eddbae42584cdc1a172209782da24e3e0d1aa6660bf853b/report.md": "6d94f58838afbe3e2cbd3c6c2ad2685b8e08d6b253b76ed9e42d12cb52883376",
            "terminals/d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359/receipt.json": "22fa43785cd7666529f415c963894b2cb12b7c20825b5504989d274bab2e5c2f",
        },
        "terminal_digest": "e8a0fbcef9535bf335a545d791cccdd60401f22573174712f0f5496a7ffce59d",
    },
}


@pytest.mark.parametrize("kind", tuple(_V1_GOLDEN))
def test_original_v1_corpus_bytes_and_acknowledgements_remain_exact(
    anchor: _Anchor, kind: str
) -> None:
    expected = _V1_GOLDEN[kind]
    enrolled = _run(anchor, "enroll", _enrollment())
    assert enrolled == {
        "schema_version": "invariant_family_review_episode.ack.v1",
        "status": "ok",
        "operation": "enroll",
        "episode_digest": "d985ac9e24ec07fc552d62bc327a8f6a553e1d782dc239d6e02a6e877d638359",
        "enrollment_receipt_digest": "d266404d7527864f34ac7b61369efef703e86968ec021353ef328bf01d040470",
    }
    if kind != "missing_terminal":
        if kind in ("not_completed", "baseline_unavailable"):
            terminal = _terminal_without_available_baseline(
                enrolled, completed=kind == "baseline_unavailable"
            )
        else:
            baseline = _baseline(enrolled)
            validated = _run(anchor, "validate", baseline)
            assert validated == {
                "schema_version": "invariant_family_review_episode.ack.v1",
                "status": "ok",
                "operation": "validate",
                "episode_digest": enrolled["episode_digest"],
                "joint_pass_baseline_digest": "b15d6222be852e49cc315ce4bbabbe44abfff44813954fe8d9c739c7435f318c",
            }
            terminal = _terminal_available(
                enrolled,
                baseline,
                validated,
                positive=kind != "zero",
                extra_trigger_digest=kind == "multi_trigger",
            )
        acknowledgement = _run(anchor, "terminal", terminal)
        assert acknowledgement == {
            "schema_version": "invariant_family_review_episode.ack.v1",
            "status": "ok",
            "operation": "terminal",
            "episode_digest": enrolled["episode_digest"],
            "terminal_receipt_digest": expected["terminal_digest"],
        }
    assert _run(anchor, "report", _report_request()) == expected["report_ack"]
    root = anchor.path / "artifacts/orchestration/review_invariant_family_episodes"
    actual = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }
    assert actual == expected["sha256"]
    # Original v1 does not constrain unrelated root entries; preserve this on rollback.
    (root / "retained-note.txt").write_text("retained local note\n", encoding="ascii")
    before = _store_snapshot(anchor)
    assert _run(anchor, "report", _report_request()) == expected["report_ack"]
    assert _store_snapshot(anchor) == before


@pytest.mark.parametrize("damage", ["symlink", "hardlink", "mode", "partial", "orphan_stage"])
def test_status_and_complete_fail_on_unsafe_checkpoint_storage(
    anchor: _Anchor, damage: str
) -> None:
    enrolled, _baseline_value, terminal = _supervised_episode(anchor)
    path = _receipt_path(anchor, "checkpoints", enrolled["episode_digest"])
    if damage == "symlink":
        target = anchor.path / "retained.json"
        path.rename(target)
        path.symlink_to(target)
    elif damage == "hardlink":
        os.link(path, anchor.path / "additional-link")
    elif damage == "mode":
        path.chmod(0o644)
    elif damage == "partial":
        path.unlink()
    else:
        (path.parent.parent / ".stage-orphan").mkdir(mode=0o700)
    before = _store_snapshot(anchor)
    for verb, request in (("status", _status_request()), ("complete", _complete_request(terminal))):
        with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE"):
            _run(anchor, verb, request)
    assert _store_snapshot(anchor) == before


@pytest.mark.parametrize("damage", ["missing_lane", "partial_report", "corrupt_report"])
def test_status_rejects_broken_legacy_storage_instead_of_absence(
    anchor: _Anchor, damage: str
) -> None:
    _run(anchor, "enroll", _enrollment())
    root = anchor.path / "artifacts/orchestration/review_invariant_family_episodes"
    if damage == "missing_lane":
        (root / "terminals").rmdir()
    else:
        report = _run(anchor, "report", _report_request())
        markdown = root / "reports" / str(report["report_digest"]) / "report.md"
        if damage == "partial_report":
            markdown.unlink()
        else:
            markdown.write_bytes(b"corrupt\n")
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_STORE_UNSAFE|E_REPORT_MANIFEST"):
        _run(anchor, "status", _status_request())
    assert _store_snapshot(anchor) == before


def test_status_rejects_existing_checkpoint_terminal_disagreement(anchor: _Anchor) -> None:
    enrolled, _baseline_value, _terminal = _supervised_episode(anchor)
    # Simulate an older writer that cannot enforce the optional checkpoint contract.
    enrollment_receipt = _load_json(
        _receipt_path(anchor, "enrollments", enrolled["episode_digest"])
    )
    terminal = episode._build_terminal_receipt(
        _terminal_without_available_baseline(enrolled, completed=False), enrollment_receipt
    )
    path = _receipt_path(anchor, "terminals", enrolled["episode_digest"])
    path.parent.mkdir(mode=0o700)
    path.write_bytes(episode._canonical_json_bytes(terminal, trailing_lf=True))
    path.chmod(0o600)
    before = _store_snapshot(anchor)
    for verb, request in (("status", _status_request()), ("report", _report_request())):
        with pytest.raises(episode.EpisodeError, match="E_DEPENDENCY"):
            _run(anchor, verb, request)
    assert _store_snapshot(anchor) == before


def test_complete_prevalidates_report_size_and_new_terminal_aggregate_size(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enrolled, _baseline_value, terminal = _supervised_episode(anchor)
    before = _store_snapshot(anchor)
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_REPORT_JSON_BYTES", 1)
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, "complete", _complete_request(terminal))
    assert _store_snapshot(anchor) == before
    current_bytes = sum(len(value[3]) for value in before.values())
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", current_bytes)
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, "complete", _complete_request(terminal))
    assert _store_snapshot(anchor) == before


def test_checkpoint_leaf_limit_and_aggregate_prevalidation_are_exact(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrolled = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrolled)
    enrollment_receipt = _load_json(
        _receipt_path(anchor, "enrollments", enrolled["episode_digest"])
    )
    expected = episode._build_checkpoint_receipt(baseline, enrollment_receipt)
    exact_size = len(episode._canonical_json_bytes(expected, trailing_lf=True))
    before = _store_snapshot(anchor)
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "MAX_CHECKPOINT_RECEIPT_BYTES", exact_size - 1)
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, "checkpoint", baseline)
    assert _store_snapshot(anchor) == before
    enrollment_size = (
        _receipt_path(anchor, "enrollments", enrolled["episode_digest"]).stat().st_size
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", enrollment_size + exact_size - 1
        )
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, "checkpoint", baseline)
    assert _store_snapshot(anchor) == before
    monkeypatch.setattr(episode, "MAX_CHECKPOINT_RECEIPT_BYTES", exact_size)
    monkeypatch.setattr(episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", enrollment_size + exact_size)
    _run(anchor, "checkpoint", baseline)
    before = _store_snapshot(anchor)
    _run(anchor, "checkpoint", baseline)
    assert _store_snapshot(anchor) == before


@pytest.mark.parametrize("operation", ["checkpoint", "complete"])
def test_lost_stdout_acknowledgement_preserves_published_evidence(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    enrolled = _run(anchor, "enroll", _enrollment())
    baseline = _baseline(enrolled)
    if operation == "complete":
        checkpoint = _run(anchor, "checkpoint", baseline)
        request = _complete_request(_terminal_available(enrolled, baseline, checkpoint))
    else:
        request = baseline

    def fail_ack(_value: object) -> None:
        raise episode.EpisodeError("E_STDOUT")

    observed_errors: list[str] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(episode, "_open_repository_anchor", lambda: os.dup(anchor.fd))
        scoped.setattr(episode, "_read_bounded_stdin", lambda: json.dumps(request).encode())
        scoped.setattr(episode, "_write_ack", fail_ack)
        scoped.setattr(episode, "_write_error", observed_errors.append)
        assert episode.main([operation]) == 1
    assert observed_errors == ["E_STDOUT"]
    before = _store_snapshot(anchor)
    assert _run(anchor, operation, request)["status"] == "ok"
    assert _store_snapshot(anchor) == before


def test_supervision_cli_uses_owning_module_store_and_sanitized_errors(tmp_path: Path) -> None:
    module = tmp_path / "scripts/orchestration/invariant_family_review_episode.py"
    module.parent.mkdir(parents=True)
    module.write_bytes(Path(episode.__file__).read_bytes())

    def invoke(verb: str, request: Mapping[str, object]) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(module), verb],
            input=json.dumps(request).encode(),
            capture_output=True,
            check=False,
            timeout=30,
            cwd=CONTRACT.parent,
        )
        assert result.returncode == 0, result.stderr.decode()
        assert result.stderr == b""
        return json.loads(result.stdout)

    assert invoke("status", _status_request())["lifecycle"] == "absent"
    assert not (tmp_path / "artifacts").exists()
    enrolled = invoke("enroll", _enrollment())
    baseline = _baseline(enrolled)
    checkpoint = invoke("checkpoint", baseline)
    terminal = _terminal_available(enrolled, baseline, checkpoint)
    result = invoke("complete", _complete_request(terminal))
    assert invoke("status", _status_request())["report_digest"] == result["report_digest"]
    failed = subprocess.run(
        [sys.executable, str(module), "status"],
        input=b'{"private": "untrusted-value"}',
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert failed.returncode == 1
    assert failed.stdout == b""
    assert failed.stderr == b"E_SCHEMA\n"


@pytest.mark.parametrize("verb", ["enroll", "terminal"])
@pytest.mark.parametrize("headroom", [-1, 0, 1])
def test_supervised_legacy_append_preflights_aggregate_without_stranding_store(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch, verb: str, headroom: int
) -> None:
    enrolled, _baseline_value, terminal = _supervised_episode(anchor)
    receipt = _load_json(_receipt_path(anchor, "enrollments", enrolled["episode_digest"]))
    document = _enrollment(18) if verb == "enroll" else terminal
    pending = (
        episode._build_enrollment_receipt(document)
        if verb == "enroll"
        else episode._build_terminal_receipt(document, receipt)
    )
    additional = len(episode._canonical_json_bytes(pending, trailing_lf=True))
    before = _store_snapshot(anchor)
    aggregate = sum(len(row[3]) for row in before.values())
    monkeypatch.setattr(
        episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", aggregate + additional + headroom
    )
    if headroom < 0:
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, verb, document)
        assert _store_snapshot(anchor) == before
        assert (
            _run(anchor, "status", _status_request())["lifecycle"] == "enrolled_awaiting_terminal"
        )
        assert _store_snapshot(anchor) == before
    else:
        ack = _run(anchor, verb, document)
        after = _store_snapshot(anchor)
        assert _run(anchor, verb, document) == ack
        assert _store_snapshot(anchor) == after
    report = _run(anchor, "report", _report_request())
    assert _run(anchor, "status", _status_request())["report_digest"] == report["report_digest"]


def test_v1_only_legacy_append_keeps_original_aggregate_admission_behavior(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch
) -> None:
    enrolled = _run(anchor, "enroll", _enrollment())
    monkeypatch.setattr(episode, "MAX_AGGREGATE_RECEIPT_SCAN_BYTES", 1)
    _run(anchor, "enroll", _enrollment(18))
    terminal = _terminal_without_available_baseline(enrolled, completed=True)
    ack = _run(anchor, "terminal", terminal)
    before = _store_snapshot(anchor)
    assert _run(anchor, "terminal", terminal) == ack
    assert _store_snapshot(anchor) == before
    assert not (
        anchor.path / "artifacts/orchestration/review_invariant_family_episodes/checkpoints"
    ).exists()


def _representability_inputs(
    *, pr_number: int = 17, families: int = 1, identities: int = 4, id_width: int = 8
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    enrollment = _enrollment(pr_number)
    class_ids = [f"i{index:04d}".ljust(id_width, "x") for index in range(identities)]
    trigger_ids = [f"t{index:04d}".ljust(id_width, "x") for index in range(identities)]
    joint_ids = [f"j{index:04d}".ljust(id_width, "x") for index in range(identities)]
    enrollment["identity_classes"] = [
        {"identity_class_id": identifier, "trigger_finding_id": trigger}
        for identifier, trigger in zip(class_ids, trigger_ids)
    ]
    enrollment["families"] = [
        {
            "family_key": f"family{index}",
            "trigger_family_id": f"trigger{index}",
            "trigger_identity_class_ids": class_ids,
        }
        for index in range(families)
    ]
    receipt = episode._build_enrollment_receipt(enrollment)
    baseline = _baseline(receipt)
    baseline["identity_classes"] = [
        {
            "identity_class_id": identifier,
            "phase_bindings": [
                {"phase": "trigger", "finding_id": trigger},
                {"phase": "joint_pass", "finding_id": joint},
            ],
        }
        for identifier, trigger, joint in zip(class_ids, trigger_ids, joint_ids)
    ]
    baseline["families"] = [
        {
            "family_key": f"family{index}",
            "joint_pass_family_id": f"joint{index}",
            "joint_pass_cumulative_identity_class_ids": class_ids,
            "recommended_resolution": "family_fix",
        }
        for index in range(families)
    ]
    return enrollment, receipt, baseline


def _representability_terminal(
    receipt: Mapping[str, object], baseline: Mapping[str, object], *, alternative: str
) -> dict[str, object]:
    checkpoint = episode._build_checkpoint_receipt(baseline, receipt)
    terminal = _terminal_available(receipt, baseline, checkpoint)
    terminal["joint_pass"]["identity_classes"] = copy.deepcopy(baseline["identity_classes"])
    observations: list[dict[str, object]] = []
    for index, family in enumerate(baseline["families"]):
        if alternative == "confirmed":
            observations.append(
                {
                    "status": "confirmed",
                    "reason": "same_scope_confirmed",
                    "family_key": family["family_key"],
                    "terminal_family_id": f"terminal{index}",
                    "terminal_cumulative_identity_class_ids": family[
                        "joint_pass_cumulative_identity_class_ids"
                    ],
                }
            )
        else:
            unknown = alternative == "one_unknown" and index == 0
            observations.append(
                {
                    "status": "unknown" if unknown else "non_comparable",
                    "reason": ("human_correspondence_unresolved" if unknown else "family_missing"),
                    "family_key": family["family_key"],
                }
            )
    terminal["joint_pass"]["family_observations"] = observations
    if alternative == "confirmed":
        for index, row in enumerate(terminal["joint_pass"]["identity_classes"]):
            row["phase_bindings"].append({"phase": "terminal", "finding_id": f"c{index}"})
    if alternative == "multi_trigger":
        terminal["observed_l2_identity_digests"].append("e" * 64)
    return terminal


@pytest.mark.parametrize("family_count", [1, 3])
@pytest.mark.parametrize("id_width", [8, 64])
@pytest.mark.parametrize("pr_number", [1, 2147483647])
def test_structural_terminal_envelope_matches_real_v1_normalizer(
    family_count: int, id_width: int, pr_number: int
) -> None:
    _raw, receipt, baseline = _representability_inputs(
        pr_number=pr_number, families=family_count, id_width=id_width
    )
    checkpoint = episode._build_checkpoint_receipt(baseline, receipt)
    predicted = episode._minimum_terminal_receipt_bytes(checkpoint, receipt)
    sizes: dict[str, int] = {}
    for alternative in ("all_non_comparable", "one_unknown", "confirmed", "multi_trigger"):
        terminal = episode._build_terminal_receipt(
            _representability_terminal(receipt, baseline, alternative=alternative), receipt
        )
        rendered = episode._canonical_json_bytes(terminal, trailing_lf=True)
        episode._validate_terminal_bundle({"receipt.json": rendered}, receipt)
        sizes[alternative] = len(rendered)
    assert predicted == min(sizes.values()) == sizes["one_unknown"]
    assert sizes["all_non_comparable"] == predicted + 4
    assert sizes["confirmed"] > predicted
    assert sizes["multi_trigger"] > predicted


@pytest.mark.parametrize("headroom", [-1, 0, 1])
@pytest.mark.parametrize("families", [1, 3])
def test_first_checkpoint_terminal_byte_envelope_admits_exact_and_rejects_over(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch, headroom: int, families: int
) -> None:
    raw, receipt, baseline = _representability_inputs(families=families, id_width=64)
    _run(anchor, "enroll", raw)
    terminal_input = _representability_terminal(receipt, baseline, alternative="one_unknown")
    real_terminal = episode._build_terminal_receipt(terminal_input, receipt)
    exact_size = len(episode._canonical_json_bytes(real_terminal, trailing_lf=True))
    monkeypatch.setattr(episode, "MAX_TERMINAL_RECEIPT_BYTES", exact_size + headroom)
    before = _store_snapshot(anchor)
    if headroom < 0:
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, "checkpoint", baseline)
        assert _store_snapshot(anchor) == before
    else:
        ack = _run(anchor, "checkpoint", baseline)
        _run(anchor, "terminal", terminal_input)
        after = _store_snapshot(anchor)
        assert _run(anchor, "checkpoint", baseline) == ack
        assert _store_snapshot(anchor) == after


def _json_depth(value: object) -> int:
    children = (
        list(value.values())
        if isinstance(value, dict)
        else value if isinstance(value, list) else []
    )
    return 1 + max((_json_depth(child) for child in children), default=0)


@pytest.mark.parametrize("limit_name", ["MAX_JSON_NODES", "MAX_JSON_DEPTH"])
@pytest.mark.parametrize("headroom", [-1, 0])
def test_first_checkpoint_terminal_shape_boundaries(
    anchor: _Anchor, monkeypatch: pytest.MonkeyPatch, limit_name: str, headroom: int
) -> None:
    raw, receipt, baseline = _representability_inputs(families=3)
    _run(anchor, "enroll", raw)
    real_terminal = episode._build_terminal_receipt(
        _representability_terminal(receipt, baseline, alternative="one_unknown"), receipt
    )
    exact = (
        episode._count_json_shape(real_terminal)
        if limit_name == "MAX_JSON_NODES"
        else _json_depth(real_terminal)
    )
    monkeypatch.setattr(episode, limit_name, exact + headroom)
    before = _store_snapshot(anchor)
    if headroom < 0:
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            _run(anchor, "checkpoint", baseline)
        assert _store_snapshot(anchor) == before
    else:
        _run(anchor, "checkpoint", baseline)
        assert (
            _run(anchor, "status", _status_request())["lifecycle"] == "enrolled_awaiting_terminal"
        )


def test_unrepresentable_512_identity_checkpoint_rejected_before_lane_creation(
    anchor: _Anchor,
) -> None:
    raw, receipt, baseline = _representability_inputs(identities=512, id_width=64)
    _run(anchor, "enroll", raw)
    checkpoint = episode._build_checkpoint_receipt(baseline, receipt)
    checkpoint_bytes = episode._canonical_json_bytes(checkpoint, trailing_lf=True)
    assert len(checkpoint_bytes) < episode.MAX_CHECKPOINT_RECEIPT_BYTES
    episode._validate_checkpoint_bundle({"receipt.json": checkpoint_bytes}, receipt)
    baseline_table_bytes = len(episode._canonical_json_bytes(baseline["identity_classes"]))
    assert 2 * baseline_table_bytes > episode.MAX_TERMINAL_RECEIPT_BYTES
    before = _store_snapshot(anchor)
    with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
        _run(anchor, "checkpoint", baseline)
    assert _store_snapshot(anchor) == before
    assert _run(anchor, "status", _status_request())["lifecycle"] == "enrolled_awaiting_checkpoint"
    _run(anchor, "report", _report_request())


def _expanded_terminal_boundary_inputs(
    extra_joint_members: int,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    # Fixed production-limit witness from the ordered post-open QA pass.
    ids = [f"i{index:03x}" for index in range(512)]
    raw = _enrollment()
    raw["identity_classes"] = [
        {"identity_class_id": ids[index], "trigger_finding_id": f"t{index:03x}"}
        for index in range(256)
    ]
    raw["families"] = [
        {
            "family_key": f"f{index}",
            "trigger_family_id": f"tf{index}",
            "trigger_identity_class_ids": ids[32 * index : 32 * (index + 1)],
        }
        for index in range(8)
    ]
    receipt = episode._build_enrollment_receipt(raw)
    baseline = _baseline(receipt)
    baseline["identity_classes"] = [
        {
            "identity_class_id": ids[index],
            "phase_bindings": (
                [{"phase": "trigger", "finding_id": f"t{index:03x}"}] if index < 256 else []
            )
            + [{"phase": "joint_pass", "finding_id": f"j{index:03x}"}],
        }
        for index in range(512)
    ]
    baseline["families"] = [
        {
            "family_key": f"f{index}",
            "joint_pass_family_id": f"jf{index}",
            "joint_pass_cumulative_identity_class_ids": (
                ids[32 * index : 32 * (index + 1)] + ids[256 + 32 * index : 256 + 32 * (index + 1)]
            ),
            "recommended_resolution": "family_fix",
        }
        for index in range(8)
    ]
    memberships = []
    for index, family in enumerate(baseline["families"]):
        own = set(family["joint_pass_cumulative_identity_class_ids"])
        others = [identifier for identifier in ids if identifier not in own]
        memberships.append(sorted(own | set(others[: 37 if index == 0 else 384])))
    baseline["families"][0]["joint_pass_cumulative_identity_class_ids"].extend(
        ids[32 : 32 + extra_joint_members]
    )
    checkpoint = episode._build_checkpoint_receipt(baseline, receipt)
    terminal = _terminal_available(receipt, baseline, checkpoint)
    terminal["joint_pass"]["identity_classes"] = copy.deepcopy(baseline["identity_classes"])
    for index, row in enumerate(terminal["joint_pass"]["identity_classes"]):
        row["phase_bindings"].append({"phase": "terminal", "finding_id": f"c{index:03x}"})
    terminal["joint_pass"]["family_observations"] = [
        {
            "status": "confirmed",
            "reason": "same_scope_confirmed",
            "family_key": f"f{index}",
            "terminal_family_id": f"cf{index}",
            "terminal_cumulative_identity_class_ids": members,
        }
        for index, members in enumerate(memberships)
    ]
    return raw, receipt, baseline, terminal


def _json_node_count(value: object) -> int:
    children = (
        value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    )
    return 1 + sum(_json_node_count(child) for child in children)


@pytest.mark.parametrize("verb", ["complete", "terminal"])
@pytest.mark.parametrize("extra_joint_members", [0, 1, 2])
def test_actual_normalized_terminal_node_boundary_is_prepublication(
    anchor: _Anchor, verb: str, extra_joint_members: int
) -> None:
    raw, receipt, baseline, terminal = _expanded_terminal_boundary_inputs(extra_joint_members)
    request = _complete_request(terminal) if verb == "complete" else terminal
    parsed = episode._strict_json_document(json.dumps(request).encode())
    expected_input_nodes = (13080 if verb == "complete" else 13075) + extra_joint_members
    assert _json_node_count(parsed) == expected_input_nodes
    normalized = episode._build_terminal_receipt(terminal, receipt)
    terminal_nodes = _json_node_count(normalized)
    assert terminal_nodes == 16383 + extra_joint_members
    assert episode.MAX_JSON_NODES == 16384
    assert (
        len(episode._canonical_json_bytes(normalized, trailing_lf=True))
        < episode.MAX_TERMINAL_RECEIPT_BYTES
    )
    # Closed normalizer expansion adds sibling fields, not deeper containers.
    assert _json_depth(normalized) == _json_depth(terminal) <= episode.MAX_JSON_DEPTH
    _run(anchor, "enroll", raw)
    _run(anchor, "checkpoint", baseline)
    before = _store_snapshot(anchor)
    if terminal_nodes > episode.MAX_JSON_NODES:
        with pytest.raises(episode.EpisodeError, match="E_LIMIT"):
            episode._run_operation(verb, parsed, anchor.fd)
        assert _store_snapshot(anchor) == before
        assert not _receipt_path(anchor, "terminals", receipt["episode_digest"]).exists()
        assert (
            _run(anchor, "status", _status_request())["lifecycle"] == "enrolled_awaiting_terminal"
        )
        assert _store_snapshot(anchor) == before
    else:
        ack = episode._run_operation(verb, parsed, anchor.fd)
        stored = _receipt_path(anchor, "terminals", receipt["episode_digest"])
        assert _load_json(stored) == normalized
        after = _store_snapshot(anchor)
        assert episode._run_operation(verb, parsed, anchor.fd) == ack
        assert _store_snapshot(anchor) == after
    report = _run(anchor, "report", _report_request())
    status = _run(anchor, "status", _status_request())
    assert status["report_digest"] == report["report_digest"]
    assert status["lifecycle"] == (
        "enrolled_awaiting_terminal" if terminal_nodes > episode.MAX_JSON_NODES else "complete"
    )

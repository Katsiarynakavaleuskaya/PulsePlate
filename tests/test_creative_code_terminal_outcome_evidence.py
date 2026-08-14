from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import inspect
import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
from typing import Any

import pytest

from core.evidence.events import build_eval_event_id, create_eval_event_producer
from core.evidence.fingerprints import build_idempotency_key, fingerprint_payload
from core.evidence.policies import normalize_upstream_ids
from scripts.orchestration import creative_code_terminal_outcome as cli
from scripts.orchestration.creative_code_pr_promotion_contract import (
    build_creative_code_pr_promotion_plan,
    build_creative_code_pr_promotion_receipt,
    promotion_plan_fingerprint,
)
from scripts.orchestration.creative_code_telemetry_contract import default_cost_metadata
from scripts.orchestration.creative_code_terminal_outcome_contract import (
    EVIDENCE_PROJECTION_POLICY_VERSION,
    EVIDENCE_PROJECTION_SOURCE_ARTIFACT,
    MAX_EVIDENCE_PROJECTION_BYTES,
    OUTCOME_KEYS,
    CreativeCodeTerminalOutcomeError,
    build_creative_code_terminal_outcome,
    build_terminal_evidence_events,
    canonical_json_bytes,
    terminal_evidence_projection_bytes,
    terminal_outcome_fingerprint,
    validate_terminal_evidence_projection,
)


def _review(*, unavailable: bool = False, unresolved: int = 0) -> dict[str, Any]:
    if unavailable:
        return {
            "collection_state": "unavailable",
            "inventory_fingerprint": None,
            "review_seal_fingerprint": None,
            "sources_configured": None,
            "sources_observed": None,
            "findings_total": None,
            "fixed": None,
            "not_a_bug": None,
            "deferred": None,
            "unresolved_actionable": None,
        }
    return {
        "collection_state": "complete",
        "inventory_fingerprint": fingerprint_payload({"review": "inventory"}),
        "review_seal_fingerprint": fingerprint_payload({"review": "seal"}),
        "sources_configured": 3,
        "sources_observed": 3,
        "findings_total": 2 + unresolved,
        "fixed": 1,
        "not_a_bug": 1,
        "deferred": 0,
        "unresolved_actionable": unresolved,
    }


def _post_merge(
    *,
    ci: str = "success",
    configured: int = 2,
    executed: int = 2,
    passed: int = 2,
) -> dict[str, Any]:
    observed = configured > 0 or ci != "not_observed"
    return {
        "validation_inventory_fingerprint": (
            fingerprint_payload({"post_merge": "inventory"}) if observed else None
        ),
        "commands_configured": configured,
        "commands_executed": executed,
        "commands_passed": passed,
        "current_main_ci": ci,
        "current_main_sha": None if ci == "not_observed" else "d" * 40,
    }


def _outcome(
    *,
    terminal_state: str = "merged",
    review: dict[str, Any] | None = None,
    post_merge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = build_creative_code_pr_promotion_plan(
        promotion_id="terminal-evidence-test",
        source_result_id="result-terminal-evidence",
        source_request_id="request-terminal-evidence",
        source_bundle_id="bundle-terminal-evidence",
        source_bundle_fingerprint=fingerprint_payload({"bundle": "terminal-evidence"}),
        selected_variant_id="variant-terminal-evidence",
        selected_variant_fingerprint=fingerprint_payload({"variant": "terminal-evidence"}),
        patch_fingerprint=fingerprint_payload({"patch": "terminal-evidence"}),
        base_commit_sha="a" * 40,
        changed_paths=["scripts/orchestration/creative_code_terminal_outcome.py"],
        target_head_branch="experiment/terminal-evidence-test",
        pull_request_title="feat: terminal evidence test",
        pull_request_body_fingerprint=fingerprint_payload({"body": "terminal-evidence"}),
    )
    receipt = build_creative_code_pr_promotion_receipt(
        promotion_id=plan["promotion_id"],
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=fingerprint_payload({"validation": "terminal-evidence"}),
        approval_id="approval-terminal-evidence",
        source_result_id=plan["source_result_id"],
        patch_fingerprint=plan["patch_fingerprint"],
        head_branch=plan["target_head_branch"],
        commit_sha="b" * 40,
        pull_request_number=2202,
        pull_request_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2202",
        approved_by_login="Katsiarynakavaleuskaya",
    )
    closed = terminal_state == "closed_unmerged"
    observation = {
        "promotion_id": receipt["promotion_id"],
        "repository": receipt["repository"],
        "pull_request_number": receipt["pull_request_number"],
        "promoted_head_sha": receipt["commit_sha"],
        "closure_epoch": 1,
        "terminal_state": terminal_state,
        "merge_sha": None if closed else "c" * 40,
        "reason_code": "abandoned" if closed else None,
        "review": review if review is not None else _review(),
        "post_merge": (
            post_merge
            if post_merge is not None
            else (
                _post_merge(ci="not_observed", configured=0, executed=0, passed=0)
                if closed
                else _post_merge()
            )
        ),
        "process": {"review_cycles": 2, "repair_cycles": 1, "validation_attempts": 3},
        "cost_metadata": default_cost_metadata(),
        "sanitized": True,
    }
    return build_creative_code_terminal_outcome(
        promotion_plan=plan,
        promotion_receipt=receipt,
        observation=observation,
    )


def _write_outcome(root: Path, outcome: dict[str, Any]) -> Path:
    outcome_dir = root / outcome["outcome_id"]
    outcome_dir.mkdir(parents=True)
    outcome_path = outcome_dir / cli.OUTCOME_FILE
    outcome_path.write_bytes(canonical_json_bytes(outcome))
    return outcome_path


def _recompute_outcome_key(outcome: dict[str, Any]) -> None:
    outcome["idempotency_key"] = fingerprint_payload(
        {key: outcome[key] for key in sorted(OUTCOME_KEYS - {"idempotency_key"})}
    )


def _projection_payload(
    outcome: dict[str, Any], produced_at: str = "2026-08-14T12:00:00Z"
) -> list[dict[str, Any]]:
    return [
        event.to_dict()
        for event in build_terminal_evidence_events(outcome, produced_at=produced_at)
    ]


def _file_snapshot(path: Path) -> tuple[bytes, tuple[int, ...]]:
    info = path.stat()
    return path.read_bytes(), (
        info.st_ino,
        info.st_nlink,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _assert_file_snapshot(path: Path, snapshot: tuple[bytes, tuple[int, ...]]) -> None:
    assert _file_snapshot(path) == snapshot


def test_builder_emits_exact_fixed_bundle_and_normalizes_timestamp() -> None:
    outcome = _outcome()
    events = build_terminal_evidence_events(outcome, produced_at="2026-08-14T15:00:00+03:00")
    payload = [event.to_dict() for event in events]

    assert [row["event_type"] for row in payload] == [
        "item_metadata",
        "gate_metric",
        "gate_decision",
    ]
    assert {row["rail"] for row in payload} == {"control_plane"}
    assert {row["produced_at"] for row in payload} == {"2026-08-14T12:00:00Z"}
    assert {row["validation_status"] for row in payload} == {"valid"}
    assert {row["source_artifact"] for row in payload} == {EVIDENCE_PROJECTION_SOURCE_ARTIFACT}
    assert {row["policy_version"] for row in payload} == {EVIDENCE_PROJECTION_POLICY_VERSION}
    assert all(row["asset_refs"] == [] for row in payload)
    expected_upstreams = sorted(
        [
            outcome["outcome_id"],
            outcome["lineage"]["promotion_id"],
            outcome["lineage"]["receipt_id"],
        ]
    )
    assert all(row["upstream_ids"] == expected_upstreams for row in payload)
    bundle_fingerprints = {row["metadata"]["projection_bundle_fingerprint"] for row in payload}
    assert len(bundle_fingerprints) == 1
    assert set(payload[0]["metadata"]) == {
        "projection_bundle_fingerprint",
        "terminal_outcome_fingerprint",
        "terminal_state",
        "review_observation",
        "governance_observation",
        "post_merge_observation",
        "reason_code_present",
        "terminal_policy_version",
    }
    assert set(payload[1]["metadata"]) == {
        "projection_bundle_fingerprint",
        "terminal_outcome_fingerprint",
        "sources_configured",
        "sources_observed",
        "findings_total",
        "fixed",
        "not_a_bug",
        "deferred",
        "unresolved_actionable",
        "review_cycles",
        "repair_cycles",
        "validation_attempts",
        "post_merge_commands_configured",
        "post_merge_commands_executed",
        "post_merge_commands_passed",
    }
    assert set(payload[2]["metadata"]) == {
        "projection_bundle_fingerprint",
        "terminal_outcome_fingerprint",
        "decision",
        "review_observation",
        "governance_observation",
        "post_merge_observation",
        "current_main_ci",
        "current_main_sha",
        "validation_inventory_fingerprint",
        "reason_code",
    }


def test_identity_is_timestamp_independent_but_bytes_are_not() -> None:
    outcome = _outcome()
    first = build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    second = build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:01Z")

    assert [(e.fingerprint, e.idempotency_key, e.event_id) for e in first] == [
        (e.fingerprint, e.idempotency_key, e.event_id) for e in second
    ]
    assert terminal_evidence_projection_bytes(first) != terminal_evidence_projection_bytes(second)


def test_event_fingerprint_idempotency_and_id_oracles_are_direct() -> None:
    outcome = _outcome()
    events = build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    outcome_fingerprint = terminal_outcome_fingerprint(outcome)
    bundle_fingerprint = fingerprint_payload(
        {
            "projection_policy_version": EVIDENCE_PROJECTION_POLICY_VERSION,
            "terminal_outcome_fingerprint": outcome_fingerprint,
        }
    )
    upstream_ids = normalize_upstream_ids(
        (
            outcome["outcome_id"],
            outcome["lineage"]["promotion_id"],
            outcome["lineage"]["receipt_id"],
        )
    )
    producer = create_eval_event_producer(name="creative_code_terminal_outcome", version="1.0")

    for event in events:
        expected_fingerprint = fingerprint_payload(
            {
                "projection_bundle_fingerprint": bundle_fingerprint,
                "event_type": event.event_type,
                "metadata": event.metadata,
            }
        )
        expected_key = build_idempotency_key(
            asset_type=event.event_type,
            rail="control_plane",
            version="1.0",
            policy_version=EVIDENCE_PROJECTION_POLICY_VERSION,
            fingerprint=expected_fingerprint,
            upstream_ids=upstream_ids,
        )
        expected_event_id = build_eval_event_id(
            event_type=event.event_type,
            rail="control_plane",
            source_artifact=EVIDENCE_PROJECTION_SOURCE_ARTIFACT,
            asset_refs=(),
            upstream_ids=upstream_ids,
            fingerprint=expected_fingerprint,
            idempotency_key=expected_key,
            policy_version=EVIDENCE_PROJECTION_POLICY_VERSION,
            producer=producer,
            validation_status=event.validation_status,
        )
        assert event.fingerprint == expected_fingerprint
        assert event.idempotency_key == expected_key
        assert event.event_id == expected_event_id


@pytest.mark.parametrize(
    "produced_at",
    [
        "",
        "2026-08-14",
        "2026-08-14T12:00:00",
        "2026-08-14 12:00:00Z",
        "2026-08-14T12:00:00-00:00",
        "2026-02-30T12:00:00Z",
        "2026-08-14T25:00:00Z",
        "2026-08-14T12:00:60Z",
        "not-time",
    ],
)
def test_builder_requires_explicit_rfc3339_offset(produced_at: str) -> None:
    with pytest.raises(CreativeCodeTerminalOutcomeError, match="produced_at"):
        build_terminal_evidence_events(_outcome(), produced_at=produced_at)


@pytest.mark.parametrize(
    ("produced_at", "expected"),
    [
        ("2026-08-14T12:00:00Z", "2026-08-14T12:00:00Z"),
        ("2026-08-14T12:00:00+03:00", "2026-08-14T09:00:00Z"),
        ("2026-08-14T12:00:00-04:30", "2026-08-14T16:30:00Z"),
        ("2026-08-14T12:00:00.123456+02:00", "2026-08-14T10:00:00.123456Z"),
        ("2026-08-14T12:00:00.123456789Z", "2026-08-14T12:00:00.123456789Z"),
        (
            "2026-08-14T12:00:00.123456789+02:00",
            "2026-08-14T10:00:00.123456789Z",
        ),
        (
            "2026-08-14T12:00:00.000000001-04:30",
            "2026-08-14T16:30:00.000000001Z",
        ),
    ],
)
def test_timestamp_positive_normalization_table(produced_at: str, expected: str) -> None:
    outcome = _outcome()
    events = build_terminal_evidence_events(outcome, produced_at=produced_at)
    assert {event.produced_at for event in events} == {expected}
    projection = terminal_evidence_projection_bytes(events)
    assert len(projection) <= MAX_EVIDENCE_PROJECTION_BYTES
    assert validate_terminal_evidence_projection(outcome, projection) == events


def test_high_precision_fraction_difference_is_divergent_replay(tmp_path: Path) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, replayed = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00.123456789Z",
        terminal_outcomes_root=root,
    )
    before = _file_snapshot(sidecar)

    assert replayed is False
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="^divergent_replay$"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00.123456788Z",
            terminal_outcomes_root=root,
        )
    _assert_file_snapshot(sidecar, before)


def test_high_precision_timestamp_cannot_exceed_sidecar_bound(tmp_path: Path) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    produced_at = "2026-08-14T12:00:00." + ("1" * 25_000) + "Z"

    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^evidence_projection_too_large$",
    ):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at=produced_at,
            terminal_outcomes_root=root,
        )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()


def test_unknown_rfc3339_offset_marker_fails_cli_without_sidecar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())

    assert (
        cli.main(
            [
                "project-evidence",
                "--outcome",
                str(outcome_path),
                "--produced-at",
                "2026-08-14T12:00:00-00:00",
            ],
            terminal_outcomes_root=root,
        )
        == 1
    )
    assert capsys.readouterr().out == (
        "FAIL: produced_at must include an explicit known UTC offset.\n"
    )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()


@pytest.mark.parametrize(
    "produced_at",
    ["0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"],
)
def test_timestamp_utc_conversion_overflow_is_a_controlled_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    produced_at: str,
) -> None:
    outcome = _outcome()
    with pytest.raises(CreativeCodeTerminalOutcomeError, match="^produced_at is invalid\\.$"):
        build_terminal_evidence_events(outcome, produced_at=produced_at)

    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, outcome)
    assert (
        cli.main(
            [
                "project-evidence",
                "--outcome",
                str(outcome_path),
                "--produced-at",
                produced_at,
            ],
            terminal_outcomes_root=root,
        )
        == 1
    )
    assert capsys.readouterr().out == "FAIL: produced_at is invalid.\n"
    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    assert not sidecar.exists()

    rows = _projection_payload(outcome)
    for row in rows:
        row["produced_at"] = produced_at
    raw = (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with pytest.raises(CreativeCodeTerminalOutcomeError, match="^produced_at is invalid\\.$"):
        validate_terminal_evidence_projection(outcome, raw)
    sidecar.write_bytes(raw)
    sidecar.chmod(0o600)
    assert (
        cli.main(
            ["validate-evidence-projection", "--outcome", str(outcome_path)],
            terminal_outcomes_root=root,
        )
        == 1
    )
    assert capsys.readouterr().out == "FAIL: produced_at is invalid.\n"


def test_builder_defensively_copies_outcome_and_metadata() -> None:
    outcome = _outcome()
    events = build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    original = events[1].metadata
    outcome["process"]["review_cycles"] = 999
    exposed = events[1].metadata
    exposed["review_cycles"] = 777
    assert events[1].metadata == original


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (_outcome(terminal_state="closed_unmerged"), "deferred"),
        (_outcome(review=_review(unavailable=True)), "degraded"),
        (_outcome(review=_review(unresolved=1)), "degraded"),
        (_outcome(post_merge=_post_merge(executed=1, passed=1)), "degraded"),
        (_outcome(post_merge=_post_merge(ci="failure")), "degraded"),
        (_outcome(post_merge=_post_merge(ci="not_observed")), "degraded"),
    ],
)
def test_status_truth_table(outcome: dict[str, Any], expected: str) -> None:
    assert {
        event.validation_status
        for event in build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    } == {expected}


@pytest.mark.parametrize(
    "mutator",
    [
        lambda rows: rows.pop(),
        lambda rows: rows.append(deepcopy(rows[0])),
        lambda rows: rows.reverse(),
        lambda rows: rows[0].update({"extra": True}),
        lambda rows: rows[0].update({"event_type": "gate_metric"}),
        lambda rows: rows[0].update({"rail": "advisory"}),
        lambda rows: rows[0].update({"validation_status": "degraded"}),
        lambda rows: rows[0].update({"produced_at": "2026-08-14T12:00:01Z"}),
        lambda rows: rows[0].update({"fingerprint": "sha256:" + "0" * 64}),
        lambda rows: rows[0].update({"idempotency_key": "idem:wrong"}),
        lambda rows: rows[0].update({"event_id": "eval-event:wrong"}),
        lambda rows: rows[0].update({"producer": {"name": "wrong", "version": "1.0"}}),
        lambda rows: rows[0]["metadata"].update({"reason_code_present": 0}),
        lambda rows: rows[0].update({"upstream_ids": ["wrong"]}),
        lambda rows: rows[0].update({"policy_version": "wrong"}),
        lambda rows: rows[0].update({"source_artifact": "docs/wrong.json"}),
    ],
)
def test_exact_validator_rejects_missing_extra_reordered_or_mutated_events(mutator: Any) -> None:
    outcome = _outcome()
    rows = _projection_payload(outcome)
    mutator(rows)
    raw = (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with pytest.raises(CreativeCodeTerminalOutcomeError):
        validate_terminal_evidence_projection(outcome, raw)


@pytest.mark.parametrize(
    "raw",
    [
        b"\xef\xbb\xbf[]",
        b'[{"produced_at":NaN}]',
        b"[] trailing",
        b"\xff",
        b'[{"x":1,"x":2}]',
    ],
)
def test_projection_decoder_rejects_unsafe_json(raw: bytes) -> None:
    with pytest.raises(CreativeCodeTerminalOutcomeError):
        validate_terminal_evidence_projection(_outcome(), raw)


def test_projection_validator_rejects_noncanonical_bytes() -> None:
    outcome = _outcome()
    rows = _projection_payload(outcome)
    raw = json.dumps(rows, indent=2).encode()
    with pytest.raises(CreativeCodeTerminalOutcomeError, match="canonical"):
        validate_terminal_evidence_projection(outcome, raw)


@pytest.mark.parametrize(
    "raw_factory",
    [
        lambda outcome: b"not-json",
        lambda outcome: b"\xef\xbb\xbf" + canonical_json_bytes(outcome),
        lambda outcome: canonical_json_bytes(outcome).replace(
            b'"closure_epoch":1', b'"closure_epoch":1,"closure_epoch":1'
        ),
        lambda outcome: canonical_json_bytes(outcome).replace(
            b'"closure_epoch":1', b'"closure_epoch":NaN'
        ),
        lambda outcome: b"x" * 1_048_577,
    ],
)
def test_malformed_or_oversized_outcome_publishes_nothing(tmp_path: Path, raw_factory: Any) -> None:
    outcome = _outcome()
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, outcome)
    outcome_path.write_bytes(raw_factory(outcome))
    with pytest.raises((CreativeCodeTerminalOutcomeError, cli.CreativeCodeTerminalOutcomeIOError)):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()


@pytest.mark.parametrize("defect", ["sanitized_int", "contradictory_review"])
def test_wrong_type_or_contradictory_outcome_publishes_nothing(tmp_path: Path, defect: str) -> None:
    outcome = _outcome()
    if defect == "sanitized_int":
        outcome["sanitized"] = 1
    else:
        outcome["review_observation"] = "actionables_observed"
    _recompute_outcome_key(outcome)
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, outcome)

    with pytest.raises(CreativeCodeTerminalOutcomeError):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()


def test_missing_outcome_publishes_nothing(tmp_path: Path) -> None:
    root = tmp_path / "terminal_outcomes"
    root.mkdir()
    missing = root / ("missing" * 6) / cli.OUTCOME_FILE
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError):
        cli.project_terminal_evidence(
            outcome_path=missing,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not missing.with_name(cli.EVIDENCE_EVENTS_FILE).exists()


def test_project_and_validate_cli_are_sibling_only_and_replay_is_no_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    outcome_before = outcome_path.stat()

    assert (
        cli.main(
            [
                "project-evidence",
                "--outcome",
                str(outcome_path),
                "--produced-at",
                "2026-08-14T12:00:00Z",
            ],
            terminal_outcomes_root=root,
        )
        == 0
    )
    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    assert sidecar.exists()
    assert sidecar.stat().st_mode & 0o777 == 0o600
    first = sidecar.stat()
    first_bytes = sidecar.read_bytes()
    first_hash = hashlib.sha256(first_bytes).hexdigest()
    fsync_paths: list[Path] = []
    original_fsync_directory = cli._fsync_directory

    def forbidden_mutation(*_: Any, **__: Any) -> Any:
        pytest.fail("serial replay must not write, link, unlink, or chmod")

    def record_directory_fsync(path: Path) -> None:
        fsync_paths.append(path)
        original_fsync_directory(path)

    with monkeypatch.context() as replay_patch:
        replay_patch.setattr(cli.os, "write", forbidden_mutation)
        replay_patch.setattr(cli.os, "link", forbidden_mutation)
        replay_patch.setattr(cli.os, "unlink", forbidden_mutation)
        replay_patch.setattr(cli.os, "chmod", forbidden_mutation)
        replay_patch.setattr(cli, "_fsync_directory", record_directory_fsync)
        assert cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        ) == (sidecar, True)
    assert (
        cli.main(
            [
                "project-evidence",
                "--outcome",
                str(outcome_path),
                "--produced-at",
                "2026-08-14T12:00:00Z",
            ],
            terminal_outcomes_root=root,
        )
        == 0
    )
    second = sidecar.stat()
    assert fsync_paths == [sidecar.parent]
    assert (
        second.st_ino,
        second.st_mode,
        second.st_size,
        second.st_mtime_ns,
        second.st_ctime_ns,
    ) == (first.st_ino, first.st_mode, first.st_size, first.st_mtime_ns, first.st_ctime_ns)
    assert sidecar.read_bytes() == first_bytes
    assert hashlib.sha256(sidecar.read_bytes()).hexdigest() == first_hash
    assert (
        cli.main(
            ["validate-evidence-projection", "--outcome", str(outcome_path)],
            terminal_outcomes_root=root,
        )
        == 0
    )
    outcome_after = outcome_path.stat()
    assert outcome_path.read_bytes() == canonical_json_bytes(_outcome())
    assert (
        outcome_after.st_ino,
        outcome_after.st_mode,
        outcome_after.st_size,
        outcome_after.st_mtime_ns,
        outcome_after.st_ctime_ns,
    ) == (
        outcome_before.st_ino,
        outcome_before.st_mode,
        outcome_before.st_size,
        outcome_before.st_mtime_ns,
        outcome_before.st_ctime_ns,
    )
    output = capsys.readouterr().out
    assert cli.SUCCESS_PROJECT_OUTPUT in output
    assert cli.SUCCESS_VALIDATE_PROJECTION_OUTPUT in output
    assert "replay=identical" in output


def test_different_timestamp_is_divergent_and_preserves_winner(tmp_path: Path) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, _ = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    )
    before = sidecar.read_bytes()
    info = sidecar.stat()
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="divergent_replay"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:01Z",
            terminal_outcomes_root=root,
        )
    after = sidecar.stat()
    assert sidecar.read_bytes() == before
    assert (after.st_ino, after.st_mtime_ns, after.st_ctime_ns) == (
        info.st_ino,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def test_existing_sidecar_wrong_mode_fails_without_repair(tmp_path: Path) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, _ = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    )
    sidecar.chmod(0o640)
    before = sidecar.stat()

    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="mode_invalid"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="mode_invalid"):
        cli.validate_projected_terminal_evidence(
            outcome_path=outcome_path,
            terminal_outcomes_root=root,
        )
    after = sidecar.stat()
    assert stat.S_IMODE(after.st_mode) == 0o640
    assert (after.st_ino, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )


@pytest.mark.parametrize("operation", ["validate", "replay"])
def test_actual_sidecar_swap_after_validation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, _ = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    )
    original_validator = cli.validate_terminal_evidence_projection
    swapped = False

    def validate_then_swap(outcome: dict[str, Any], raw: bytes) -> Any:
        nonlocal swapped
        result = original_validator(outcome, raw)
        if not swapped:
            replacement = sidecar.with_name("replacement.json")
            replacement.write_bytes(raw)
            replacement.chmod(0o600)
            os.replace(replacement, sidecar)
            swapped = True
        return result

    monkeypatch.setattr(cli, "validate_terminal_evidence_projection", validate_then_swap)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="evidence_projection_changed_after_read",
    ):
        if operation == "validate":
            cli.validate_projected_terminal_evidence(
                outcome_path=outcome_path,
                terminal_outcomes_root=root,
            )
        else:
            cli.project_terminal_evidence(
                outcome_path=outcome_path,
                produced_at="2026-08-14T12:00:00Z",
                terminal_outcomes_root=root,
            )


def test_read_only_validator_requires_final_source_identity_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, _ = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    )
    outcome_before = outcome_path.stat()
    sidecar_before = sidecar.stat()
    outcome_bytes = outcome_path.read_bytes()
    sidecar_bytes = sidecar.read_bytes()

    def fail_final_source_seal(**_: Any) -> None:
        raise cli.CreativeCodeTerminalOutcomeIOError("terminal_outcome_changed_before_projection")

    monkeypatch.setattr(cli, "_recheck_projection_source_identity", fail_final_source_seal)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^terminal_outcome_changed_before_projection$",
    ):
        cli.validate_projected_terminal_evidence(
            outcome_path=outcome_path,
            terminal_outcomes_root=root,
        )

    outcome_after = outcome_path.stat()
    sidecar_after = sidecar.stat()
    assert outcome_path.read_bytes() == outcome_bytes
    assert sidecar.read_bytes() == sidecar_bytes
    assert (
        outcome_after.st_ino,
        outcome_after.st_mode,
        outcome_after.st_size,
        outcome_after.st_mtime_ns,
        outcome_after.st_ctime_ns,
    ) == (
        outcome_before.st_ino,
        outcome_before.st_mode,
        outcome_before.st_size,
        outcome_before.st_mtime_ns,
        outcome_before.st_ctime_ns,
    )
    assert (
        sidecar_after.st_ino,
        sidecar_after.st_mode,
        sidecar_after.st_size,
        sidecar_after.st_mtime_ns,
        sidecar_after.st_ctime_ns,
    ) == (
        sidecar_before.st_ino,
        sidecar_before.st_mode,
        sidecar_before.st_size,
        sidecar_before.st_mtime_ns,
        sidecar_before.st_ctime_ns,
    )


def test_read_only_validator_waits_for_transient_winner_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, _ = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    )
    winner_staging = sidecar.with_name(".validator-winner.staging")
    os.link(sidecar, winner_staging, follow_symlinks=False)
    waiting = threading.Event()
    release = threading.Event()

    def controlled_sleep(_: float) -> None:
        waiting.set()
        assert release.wait(timeout=5)

    def forbid_validator_fsync(_: Path) -> None:
        pytest.fail("read-only validator must not fsync")

    monkeypatch.setattr(cli.time, "sleep", controlled_sleep)
    monkeypatch.setattr(cli, "_fsync_directory", forbid_validator_fsync)
    with ThreadPoolExecutor(max_workers=1) as pool:
        validation = pool.submit(
            cli.validate_projected_terminal_evidence,
            outcome_path=outcome_path,
            terminal_outcomes_root=root,
        )
        assert waiting.wait(timeout=5)
        assert sidecar.stat().st_nlink == 2
        winner_staging.unlink()
        settled = _file_snapshot(sidecar)
        release.set()
        assert validation.result(timeout=5) is None

    _assert_file_snapshot(sidecar, settled)


def test_read_only_validator_accepts_exact_lstat_fstat_link_settle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, _ = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    )
    winner_staging = sidecar.with_name(".validator-open-winner.staging")
    os.link(sidecar, winner_staging, follow_symlinks=False)
    original_open = cli.os.open
    target_open_calls = 0
    settled: tuple[bytes, tuple[int, ...]] | None = None

    def settle_between_lstat_and_fstat(path: Any, flags: int, *args: Any) -> int:
        nonlocal settled, target_open_calls
        descriptor = original_open(path, flags, *args)
        if Path(path) == sidecar:
            target_open_calls += 1
            if target_open_calls == 1:
                winner_staging.unlink()
                settled = _file_snapshot(sidecar)
        return descriptor

    monkeypatch.setattr(cli.os, "open", settle_between_lstat_and_fstat)
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        cli,
        "_fsync_directory",
        lambda _: pytest.fail("read-only validator must not fsync"),
    )
    cli.validate_projected_terminal_evidence(
        outcome_path=outcome_path,
        terminal_outcomes_root=root,
    )

    assert target_open_calls == 2
    assert settled is not None
    _assert_file_snapshot(sidecar, settled)


@pytest.mark.parametrize("case", ["stable", "malformed", "persistent_hardlink"])
def test_read_only_validator_syscall_and_metadata_immutability_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar, _ = cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    )
    persistent_link: Path | None = None
    if case == "malformed":
        sidecar.write_bytes(b"not-json")
        sidecar.chmod(0o600)
    elif case == "persistent_hardlink":
        persistent_link = sidecar.with_name("persistent-validator-link.json")
        os.link(sidecar, persistent_link, follow_symlinks=False)
        monkeypatch.setattr(cli, "_COLLISION_STABILIZATION_ATTEMPTS", 2)
        monkeypatch.setattr(cli, "_COLLISION_STABILIZATION_DELAY_SECONDS", 0.0)

    outcome_before = _file_snapshot(outcome_path)
    sidecar_before = _file_snapshot(sidecar)

    def forbidden_mutation(*_: Any, **__: Any) -> Any:
        pytest.fail("read-only validator must not fsync, write, link, unlink, or chmod")

    with monkeypatch.context() as validation_patch:
        validation_patch.setattr(cli, "_fsync_directory", forbidden_mutation)
        validation_patch.setattr(cli.os, "write", forbidden_mutation)
        validation_patch.setattr(cli.os, "link", forbidden_mutation)
        validation_patch.setattr(cli.os, "unlink", forbidden_mutation)
        validation_patch.setattr(cli.os, "chmod", forbidden_mutation)
        if case == "stable":
            cli.validate_projected_terminal_evidence(
                outcome_path=outcome_path,
                terminal_outcomes_root=root,
            )
        elif case == "malformed":
            with pytest.raises(CreativeCodeTerminalOutcomeError):
                cli.validate_projected_terminal_evidence(
                    outcome_path=outcome_path,
                    terminal_outcomes_root=root,
                )
        else:
            with pytest.raises(
                cli.CreativeCodeTerminalOutcomeIOError,
                match="^evidence_projection_hardlink_rejected$",
            ):
                cli.validate_projected_terminal_evidence(
                    outcome_path=outcome_path,
                    terminal_outcomes_root=root,
                )

    _assert_file_snapshot(outcome_path, outcome_before)
    _assert_file_snapshot(sidecar, sidecar_before)
    if persistent_link is not None:
        assert persistent_link.exists()


@pytest.mark.parametrize("replay_path", ["early_existing", "eexist_collision"])
def test_actual_outcome_swap_during_replay_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replay_path: str,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    if replay_path == "early_existing":
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    else:

        def collide(staging: Path, target: Path) -> None:
            os.link(staging, target, follow_symlinks=False)
            raise FileExistsError("injected EEXIST")

        monkeypatch.setattr(cli, "_link_staging_file_noreplace", collide)

    original_validator = cli.validate_terminal_evidence_projection
    swapped = False

    def validate_then_swap(source_outcome: dict[str, Any], raw: bytes) -> Any:
        nonlocal swapped
        result = original_validator(source_outcome, raw)
        if not swapped:
            replacement = outcome_path.with_name("replacement-outcome.json")
            replacement.write_bytes(canonical_json_bytes(source_outcome))
            replacement.chmod(stat.S_IMODE(outcome_path.stat().st_mode))
            os.replace(replacement, outcome_path)
            swapped = True
        return result

    monkeypatch.setattr(cli, "validate_terminal_evidence_projection", validate_then_swap)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="terminal_outcome_changed_before_projection",
    ):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    assert sidecar.exists()
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_parent_directory_swap_to_symlink_before_publish_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    original_parent = outcome_path.parent
    moved_parent = root / f"{original_parent.name}.moved"
    original_builder = cli.build_terminal_evidence_events

    def build_then_swap(outcome: dict[str, Any], *, produced_at: str) -> Any:
        events = original_builder(outcome, produced_at=produced_at)
        original_parent.rename(moved_parent)
        original_parent.symlink_to(moved_parent, target_is_directory=True)
        return events

    monkeypatch.setattr(cli, "build_terminal_evidence_events", build_then_swap)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="symlink_rejected"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not (moved_parent / cli.EVIDENCE_EVENTS_FILE).exists()
    assert not list(moved_parent.glob(".evidence_events.*.staging"))


@pytest.mark.parametrize("bad_name", ["outcome.json", "../terminal_outcome.json"])
def test_wrong_basename_or_traversal_fails_without_sidecar(tmp_path: Path, bad_name: str) -> None:
    root = tmp_path / "terminal_outcomes"
    canonical = _write_outcome(root, _outcome())
    candidate = canonical.with_name(bad_name) if "/" not in bad_name else root / bad_name
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError):
        cli.project_terminal_evidence(
            outcome_path=candidate,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not canonical.with_name(cli.EVIDENCE_EVENTS_FILE).exists()


def test_symlink_and_hardlink_inputs_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "terminal_outcomes"
    canonical = _write_outcome(root, _outcome())
    original = canonical.with_suffix(".original")
    canonical.rename(original)
    canonical.symlink_to(original)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="symlink"):
        cli.project_terminal_evidence(
            outcome_path=canonical,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    canonical.unlink()
    os.link(original, canonical)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="hardlink"):
        cli.project_terminal_evidence(
            outcome_path=canonical,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )


@pytest.mark.parametrize("kind", ["directory", "fifo"])
def test_non_regular_inputs_fail_without_blocking(tmp_path: Path, kind: str) -> None:
    outcome = _outcome()
    root = tmp_path / "terminal_outcomes"
    outcome_dir = root / outcome["outcome_id"]
    outcome_dir.mkdir(parents=True)
    target = outcome_dir / cli.OUTCOME_FILE
    if kind == "directory":
        target.mkdir()
    else:
        os.mkfifo(target)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError):
        cli.project_terminal_evidence(
            outcome_path=target,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )


def test_socket_input_fails_without_blocking() -> None:
    with tempfile.TemporaryDirectory(prefix="ccoe-", dir="/tmp") as raw_root:
        root = Path(raw_root) / "terminal_outcomes"
        outcome = _outcome()
        outcome_dir = root / outcome["outcome_id"]
        outcome_dir.mkdir(parents=True)
        target = outcome_dir / cli.OUTCOME_FILE
        sock = socket.socket(socket.AF_UNIX)
        short_socket = Path(raw_root) / "s"
        sock.bind(str(short_socket))
        short_socket.rename(target)
        try:
            with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError):
                cli.project_terminal_evidence(
                    outcome_path=target,
                    produced_at="2026-08-14T12:00:00Z",
                    terminal_outcomes_root=root,
                )
        finally:
            sock.close()


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_non_regular_or_symlinked_sidecar_fails_without_mutation(tmp_path: Path, kind: str) -> None:
    root = tmp_path / kind / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    if kind == "symlink":
        referent = outcome_path.with_name("projection-referent.json")
        referent.write_bytes(b"[]\n")
        referent.chmod(0o600)
        sidecar.symlink_to(referent)
    elif kind == "directory":
        sidecar.mkdir()
    else:
        os.mkfifo(sidecar)

    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert sidecar.exists() or sidecar.is_symlink()


def test_socket_sidecar_and_real_device_are_rejected_without_blocking() -> None:
    with tempfile.TemporaryDirectory(prefix="ccoe-output-", dir="/tmp") as raw_root:
        root = Path(raw_root) / "terminal_outcomes"
        outcome_path = _write_outcome(root, _outcome())
        sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
        sock = socket.socket(socket.AF_UNIX)
        short_socket = Path(raw_root) / "s"
        sock.bind(str(short_socket))
        short_socket.rename(sidecar)
        try:
            with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError):
                cli.project_terminal_evidence(
                    outcome_path=outcome_path,
                    produced_at="2026-08-14T12:00:00Z",
                    terminal_outcomes_root=root,
                )
        finally:
            sock.close()

    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="must_be_regular"):
        cli._read_bounded_regular_bytes(
            Path("/dev/null"),
            label="evidence_projection",
            max_bytes=MAX_EVIDENCE_PROJECTION_BYTES,
            require_single_link=True,
            required_mode=0o600,
        )


def test_malformed_oversized_or_hardlinked_sidecar_is_never_repaired(tmp_path: Path) -> None:
    cases = (
        (b"not-json", "evidence_projection_decode_failed"),
        (b"x" * (MAX_EVIDENCE_PROJECTION_BYTES + 1), "evidence_projection_too_large"),
    )
    for index, (content, expected_error) in enumerate(cases):
        root = tmp_path / str(index) / "terminal_outcomes"
        outcome_path = _write_outcome(root, _outcome())
        sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
        sidecar.write_bytes(content)
        sidecar.chmod(0o600)
        before = sidecar.stat()
        with pytest.raises(
            (CreativeCodeTerminalOutcomeError, cli.CreativeCodeTerminalOutcomeIOError),
            match=expected_error,
        ):
            cli.project_terminal_evidence(
                outcome_path=outcome_path,
                produced_at="2026-08-14T12:00:00Z",
                terminal_outcomes_root=root,
            )
        assert sidecar.read_bytes() == content
        after = sidecar.stat()
        assert (
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) == (
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )

    root = tmp_path / "hardlink" / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    sidecar.write_bytes(
        terminal_evidence_projection_bytes(
            build_terminal_evidence_events(_outcome(), produced_at="2026-08-14T12:00:00Z")
        )
    )
    os.link(sidecar, sidecar.with_suffix(".link"))
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="hardlink"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )


def test_injected_preinstall_failure_leaves_no_sidecar_or_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())

    def fail_recheck(**_: Any) -> None:
        raise cli.CreativeCodeTerminalOutcomeIOError("injected_toctou")

    monkeypatch.setattr(cli, "_recheck_projection_source_identity", fail_recheck)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="injected_toctou"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_injected_before_write_failure_touches_no_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())

    def fail_before_write(_: Path, __: bytes) -> Path:
        raise cli.CreativeCodeTerminalOutcomeIOError("injected_before_write")

    monkeypatch.setattr(cli, "_write_projection_staging_file", fail_before_write)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="injected_before_write"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_post_install_source_replacement_fails_with_complete_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    original_recheck = cli._recheck_projection_source_identity
    recheck_calls = 0

    def replace_source_after_install(**kwargs: Any) -> None:
        nonlocal recheck_calls
        recheck_calls += 1
        if recheck_calls == 3:
            replacement = outcome_path.with_name("replacement-outcome.json")
            replacement.write_bytes(outcome_path.read_bytes())
            replacement.chmod(stat.S_IMODE(outcome_path.stat().st_mode))
            os.replace(replacement, outcome_path)
        original_recheck(**kwargs)

    monkeypatch.setattr(cli, "_recheck_projection_source_identity", replace_source_after_install)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^terminal_outcome_changed_before_projection$",
    ):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )

    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    assert recheck_calls == 3
    assert sidecar.read_bytes() == terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    assert sidecar.stat().st_nlink == 1
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_injected_write_or_install_failure_cleans_private_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    original_mkstemp = cli.tempfile.mkstemp
    original_write = cli.os.write
    staging_descriptor: int | None = None
    staging_writes = 0

    def capture_staging_descriptor(*args: Any, **kwargs: Any) -> tuple[int, str]:
        nonlocal staging_descriptor
        descriptor, path = original_mkstemp(*args, **kwargs)
        staging_descriptor = descriptor
        return descriptor, path

    def fail_second_write(descriptor: int, content: bytes) -> int:
        nonlocal staging_writes
        if descriptor != staging_descriptor:
            return original_write(descriptor, content)
        staging_writes += 1
        if staging_writes == 1:
            return original_write(descriptor, content[: max(1, len(content) // 2)])
        raise OSError("injected write failure")

    monkeypatch.setattr(cli.tempfile, "mkstemp", capture_staging_descriptor)
    monkeypatch.setattr(cli.os, "write", fail_second_write)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="staging_io_failed"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))

    monkeypatch.setattr(cli.os, "write", original_write)

    def fail_install(_: Path, __: Path) -> None:
        raise cli.CreativeCodeTerminalOutcomeIOError("injected_install_failure")

    monkeypatch.setattr(cli, "_link_staging_file_noreplace", fail_install)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="injected_install_failure"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_staging_file_fsync_failure_closes_fd_and_publishes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    original_mkstemp = cli.tempfile.mkstemp
    original_fsync = cli.os.fsync
    staging_descriptor: int | None = None
    injected = False

    def capture_staging_descriptor(*args: Any, **kwargs: Any) -> tuple[int, str]:
        nonlocal staging_descriptor
        descriptor, path = original_mkstemp(*args, **kwargs)
        staging_descriptor = descriptor
        return descriptor, path

    def fail_staging_file_fsync(descriptor: int) -> None:
        nonlocal injected
        if descriptor == staging_descriptor and not injected:
            injected = True
            raise OSError("injected staging fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(cli.tempfile, "mkstemp", capture_staging_descriptor)
    monkeypatch.setattr(cli.os, "fsync", fail_staging_file_fsync)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^evidence_projection_staging_io_failed$",
    ):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )

    assert injected is True
    assert staging_descriptor is not None
    with pytest.raises(OSError):
        os.fstat(staging_descriptor)
    assert not outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).exists()
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_cleanup_failure_is_attempted_once_and_preserves_first_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    original_cleanup = cli._cleanup_projection_staging
    cleanup_calls = 0

    def cleanup_then_fail(staging_file: Path) -> None:
        nonlocal cleanup_calls
        cleanup_calls += 1
        original_cleanup(staging_file)
        if cleanup_calls == 1:
            raise cli.CreativeCodeTerminalOutcomeIOError("first_cleanup_error")
        raise cli.CreativeCodeTerminalOutcomeIOError("second_cleanup_error")

    monkeypatch.setattr(cli, "_cleanup_projection_staging", cleanup_then_fail)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="^first_cleanup_error$"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    assert cleanup_calls == 1
    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    assert sidecar.read_bytes() == terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    assert sidecar.stat().st_nlink == 1
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


@pytest.mark.parametrize("failing_call", [1, 2])
def test_directory_fsync_failure_after_link_preserves_complete_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_call: int,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    original_fsync_directory = cli._fsync_directory
    fsync_calls = 0

    def fail_selected_directory_fsync(path: Path) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == failing_call:
            raise cli.CreativeCodeTerminalOutcomeIOError("directory_fsync_failed")
        original_fsync_directory(path)

    monkeypatch.setattr(cli, "_fsync_directory", fail_selected_directory_fsync)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^directory_fsync_failed$",
    ):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )

    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    assert fsync_calls == failing_call
    assert sidecar.read_bytes() == terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    assert sidecar.stat().st_nlink == 1
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_actual_staging_unlink_failure_preserves_target_and_private_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    expected = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    original_unlink = Path.unlink

    def fail_private_staging_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.name.startswith(".evidence_events.") and path.name.endswith(".staging"):
            raise OSError("injected unlink failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_private_staging_unlink)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^evidence_projection_staging_cleanup_failed$",
    ):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )

    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    staging_files = list(outcome_path.parent.glob(".evidence_events.*.staging"))
    assert len(staging_files) == 1
    staging = staging_files[0]
    assert sidecar.read_bytes() == expected
    assert staging.read_bytes() == expected
    assert sidecar.stat().st_ino == staging.stat().st_ino
    assert sidecar.stat().st_nlink == staging.stat().st_nlink == 2
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600


def test_concurrent_identical_and_divergent_publishers_have_one_winner(tmp_path: Path) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: cli.project_terminal_evidence(
                    outcome_path=outcome_path,
                    produced_at="2026-08-14T12:00:00Z",
                    terminal_outcomes_root=root,
                ),
                range(2),
            )
        )
    assert sorted(replayed for _, replayed in results) == [False, True]
    outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE).unlink()

    def publish(timestamp: str) -> str:
        try:
            cli.project_terminal_evidence(
                outcome_path=outcome_path,
                produced_at=timestamp,
                terminal_outcomes_root=root,
            )
        except cli.CreativeCodeTerminalOutcomeIOError as exc:
            return str(exc)
        return "winner"

    with ThreadPoolExecutor(max_workers=2) as pool:
        divergent = list(pool.map(publish, ["2026-08-14T12:00:00Z", "2026-08-14T12:00:01Z"]))
    assert sorted(divergent) == ["divergent_replay", "winner"]


@pytest.mark.parametrize("winner_timestamp", ["2026-08-14T12:00:00Z", "2026-08-14T12:00:01Z"])
def test_injected_real_eexist_collision_validates_external_winner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    winner_timestamp: str,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    requested_timestamp = "2026-08-14T12:00:00Z"

    def collide(staging: Path, target: Path) -> None:
        if winner_timestamp == requested_timestamp:
            os.link(staging, target, follow_symlinks=False)
        else:
            winner = target.with_name("external-winner.staging")
            winner.write_bytes(
                terminal_evidence_projection_bytes(
                    build_terminal_evidence_events(outcome, produced_at=winner_timestamp)
                )
            )
            winner.chmod(0o600)
            os.link(winner, target, follow_symlinks=False)
            winner.unlink()
        raise FileExistsError("injected EEXIST")

    monkeypatch.setattr(cli, "_link_staging_file_noreplace", collide)
    if winner_timestamp == requested_timestamp:
        target, replayed = cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at=requested_timestamp,
            terminal_outcomes_root=root,
        )
        assert replayed is True
        assert target.stat().st_nlink == 1
    else:
        with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="divergent_replay"):
            cli.project_terminal_evidence(
                outcome_path=outcome_path,
                produced_at=requested_timestamp,
                terminal_outcomes_root=root,
            )
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


@pytest.mark.parametrize("divergent", [False, True])
def test_collision_reader_waits_for_winner_private_link_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    divergent: bool,
) -> None:
    outcome = _outcome()
    requested = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    winner = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(
            outcome,
            produced_at=("2026-08-14T12:00:01Z" if divergent else "2026-08-14T12:00:00Z"),
        )
    )
    parent = tmp_path / "collision"
    parent.mkdir()
    staging = parent / ".winner.staging"
    target = parent / cli.EVIDENCE_EVENTS_FILE
    staging.write_bytes(winner)
    staging.chmod(0o600)
    os.link(staging, target, follow_symlinks=False)
    waiting = threading.Event()
    release = threading.Event()

    def controlled_sleep(_: float) -> None:
        waiting.set()
        assert release.wait(timeout=5)

    def validate_loser() -> str:
        try:
            cli._validate_existing_projection(
                outcome=outcome,
                target_file=target,
                expected_content=requested,
                collision_winner=True,
            )
        except cli.CreativeCodeTerminalOutcomeIOError as exc:
            return str(exc)
        return "identical"

    monkeypatch.setattr(cli.time, "sleep", controlled_sleep)
    with ThreadPoolExecutor(max_workers=1) as pool:
        loser = pool.submit(validate_loser)
        assert waiting.wait(timeout=5)
        assert target.stat().st_nlink == 2
        staging.unlink()
        release.set()
        result = loser.result(timeout=5)
    assert result == ("divergent_replay" if divergent else "identical")
    assert target.stat().st_nlink == 1
    assert target.read_bytes() == winner


def test_collision_reader_does_not_repair_persistent_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome = _outcome()
    content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    staging = tmp_path / ".external.staging"
    target = tmp_path / cli.EVIDENCE_EVENTS_FILE
    staging.write_bytes(content)
    staging.chmod(0o600)
    os.link(staging, target, follow_symlinks=False)
    before = target.stat()
    monkeypatch.setattr(cli, "_COLLISION_STABILIZATION_ATTEMPTS", 2)
    monkeypatch.setattr(cli, "_COLLISION_STABILIZATION_DELAY_SECONDS", 0.0)

    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="hardlink_rejected"):
        cli._validate_existing_projection(
            outcome=outcome,
            target_file=target,
            expected_content=content,
            collision_winner=True,
        )
    after = target.stat()
    assert target.read_bytes() == content
    assert staging.exists()
    assert (after.st_ino, after.st_nlink, after.st_mode, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_nlink,
        before.st_mode,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )


def test_lstat_to_open_identity_drift_is_not_collision_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome = _outcome()
    content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    target = tmp_path / cli.EVIDENCE_EVENTS_FILE
    target.write_bytes(content)
    target.chmod(0o600)
    displaced = tmp_path / "displaced-evidence-events.json"
    original_open = cli.os.open
    open_calls = 0

    def replace_between_lstat_and_open(path: Any, flags: int, *args: Any) -> int:
        nonlocal open_calls
        if Path(path) == target:
            open_calls += 1
            if open_calls == 1:
                target.rename(displaced)
                target.write_bytes(content)
                target.chmod(0o600)
        return original_open(path, flags, *args)

    monkeypatch.setattr(cli.os, "open", replace_between_lstat_and_open)
    monkeypatch.setattr(
        cli.time,
        "sleep",
        lambda _: pytest.fail("general identity drift must not enter collision retry"),
    )
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^evidence_projection_changed_during_read$",
    ):
        cli._read_collision_winner_projection_bytes(target)
    assert open_calls == 1


def test_before_to_after_fstat_identity_drift_is_not_collision_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome = _outcome()
    content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    target = tmp_path / cli.EVIDENCE_EVENTS_FILE
    target.write_bytes(content)
    target.chmod(0o600)
    original_open = cli.os.open
    original_read = cli.os.read
    target_descriptor: int | None = None
    target_open_calls = 0
    target_read_calls = 0
    mutated = False

    def capture_exact_target_descriptor(path: Any, flags: int, *args: Any) -> int:
        nonlocal target_descriptor, target_open_calls
        descriptor = original_open(path, flags, *args)
        if Path(path) == target:
            target_descriptor = descriptor
            target_open_calls += 1
        return descriptor

    def mutate_after_first_read(descriptor: int, size: int) -> bytes:
        nonlocal mutated, target_read_calls
        if descriptor != target_descriptor:
            return original_read(descriptor, size)
        target_read_calls += 1
        chunk = original_read(descriptor, size)
        if chunk and not mutated:
            mutated = True
            info = target.stat()
            os.utime(
                target,
                ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000),
            )
        return chunk

    monkeypatch.setattr(cli.os, "open", capture_exact_target_descriptor)
    monkeypatch.setattr(cli.os, "read", mutate_after_first_read)
    monkeypatch.setattr(
        cli.time,
        "sleep",
        lambda _: pytest.fail("post-open identity drift must not enter collision retry"),
    )
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^evidence_projection_changed_during_read$",
    ):
        cli._read_collision_winner_projection_bytes(target)
    assert target_open_calls == 1
    assert target_read_calls == 2
    assert mutated is True


@pytest.mark.parametrize(
    ("path_changes", "descriptor_changes", "expected"),
    [
        ({}, {}, True),
        ({"changed_ns": 4}, {"changed_ns": 9}, True),
        ({"device": 9}, {}, False),
        ({}, {"inode": 9}, False),
        ({"mode": stat.S_IFDIR | 0o600}, {}, False),
        ({}, {"mode": stat.S_IFREG | 0o640}, False),
        ({"size": 9}, {}, False),
        ({}, {"modified_ns": 9}, False),
        ({"links": 3}, {}, False),
        ({}, {"links": 2}, False),
    ],
)
def test_collision_link_settled_classifier_is_a_closed_matrix(
    path_changes: dict[str, int],
    descriptor_changes: dict[str, int],
    expected: bool,
) -> None:
    path_values = {
        "device": 1,
        "inode": 2,
        "mode": stat.S_IFREG | 0o600,
        "links": 2,
        "size": 3,
        "modified_ns": 4,
        "changed_ns": 5,
    }
    descriptor_values = {**path_values, "links": 1}
    path_values.update(path_changes)
    descriptor_values.update(descriptor_changes)

    assert (
        cli._is_collision_link_settled_during_open(
            cli._RegularFileIdentity(**path_values),
            cli._RegularFileIdentity(**descriptor_values),
        )
        is expected
    )


@pytest.mark.parametrize("divergent", [False, True])
def test_public_replay_retries_only_link_settled_during_open_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    divergent: bool,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    requested_timestamp = "2026-08-14T12:00:00Z"
    winner_timestamp = "2026-08-14T12:00:01Z" if divergent else requested_timestamp
    target = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    winner_content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at=winner_timestamp)
    )
    winner_staging = outcome_path.with_name(".actual-winner.staging")
    winner_staging.write_bytes(winner_content)
    winner_staging.chmod(0o600)
    os.link(winner_staging, target, follow_symlinks=False)
    original_open = cli.os.open
    target_open_calls = 0

    def unlink_winner_between_lstat_and_fstat(path: Any, flags: int, *args: Any) -> int:
        nonlocal target_open_calls
        descriptor = original_open(path, flags, *args)
        if Path(path) == target:
            target_open_calls += 1
            if target_open_calls == 1:
                winner_staging.unlink()
        return descriptor

    monkeypatch.setattr(cli.os, "open", unlink_winner_between_lstat_and_fstat)
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    if divergent:
        with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="^divergent_replay$"):
            cli.project_terminal_evidence(
                outcome_path=outcome_path,
                produced_at=requested_timestamp,
                terminal_outcomes_root=root,
            )
    else:
        assert cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at=requested_timestamp,
            terminal_outcomes_root=root,
        ) == (target, True)
    assert target_open_calls == 2
    assert target.read_bytes() == winner_content
    assert target.stat().st_nlink == 1
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not winner_staging.exists()


@pytest.mark.parametrize("replay_path", ["early_existing", "eexist_collision"])
def test_replay_fsyncs_validated_parent_before_final_source_seal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replay_path: str,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    target = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    winner_unlinked_without_fsync = False

    if replay_path == "early_existing":
        winner = target.with_name(".early-unfsynced-winner.staging")
        winner.write_bytes(content)
        winner.chmod(0o600)
        os.link(winner, target, follow_symlinks=False)
        winner.unlink()
        winner_unlinked_without_fsync = True
    else:

        def publish_unfsynced_winner_then_collide(_: Path, destination: Path) -> None:
            nonlocal winner_unlinked_without_fsync
            winner = destination.with_name(".eexist-unfsynced-winner.staging")
            winner.write_bytes(content)
            winner.chmod(0o600)
            os.link(winner, destination, follow_symlinks=False)
            winner.unlink()
            winner_unlinked_without_fsync = True
            raise FileExistsError("injected EEXIST before winner directory fsync")

        monkeypatch.setattr(
            cli, "_link_staging_file_noreplace", publish_unfsynced_winner_then_collide
        )

    sequence: list[str] = []
    original_validate = cli._validate_existing_projection
    original_fsync_directory = cli._fsync_directory
    original_source_seal = cli._recheck_projection_source_identity

    def record_validation(**kwargs: Any) -> bool:
        result = original_validate(**kwargs)
        sequence.append("validated")
        return result

    def record_directory_fsync(path: Path) -> None:
        sequence.append("parent_fsync")
        original_fsync_directory(path)

    def record_source_seal(**kwargs: Any) -> None:
        original_source_seal(**kwargs)
        sequence.append("source_seal")

    monkeypatch.setattr(cli, "_validate_existing_projection", record_validation)
    monkeypatch.setattr(cli, "_fsync_directory", record_directory_fsync)
    monkeypatch.setattr(cli, "_recheck_projection_source_identity", record_source_seal)

    assert cli.project_terminal_evidence(
        outcome_path=outcome_path,
        produced_at="2026-08-14T12:00:00Z",
        terminal_outcomes_root=root,
    ) == (target, True)
    assert winner_unlinked_without_fsync is True
    assert sequence[-3:] == ["validated", "parent_fsync", "source_seal"]
    assert target.read_bytes() == content
    assert target.stat().st_nlink == 1
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


@pytest.mark.parametrize("replay_path", ["early_existing", "eexist_collision"])
def test_replay_parent_fsync_failure_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replay_path: str,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    target = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    failing_fsync_call = 1
    expected_source_seals = 0
    if replay_path == "early_existing":
        target.write_bytes(content)
        target.chmod(0o600)
    else:
        failing_fsync_call = 2
        expected_source_seals = 2

        def collide(staging: Path, destination: Path) -> None:
            os.link(staging, destination, follow_symlinks=False)
            raise FileExistsError("injected EEXIST")

        monkeypatch.setattr(cli, "_link_staging_file_noreplace", collide)

    original_fsync_directory = cli._fsync_directory
    original_source_seal = cli._recheck_projection_source_identity
    fsync_calls = 0
    source_seals = 0

    def fail_replay_fsync(path: Path) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == failing_fsync_call:
            raise cli.CreativeCodeTerminalOutcomeIOError("directory_fsync_failed")
        original_fsync_directory(path)

    def count_source_seals(**kwargs: Any) -> None:
        nonlocal source_seals
        original_source_seal(**kwargs)
        source_seals += 1

    monkeypatch.setattr(cli, "_fsync_directory", fail_replay_fsync)
    monkeypatch.setattr(cli, "_recheck_projection_source_identity", count_source_seals)
    with pytest.raises(
        cli.CreativeCodeTerminalOutcomeIOError,
        match="^directory_fsync_failed$",
    ):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )

    assert fsync_calls == failing_fsync_call
    assert source_seals == expected_source_seals
    assert target.read_bytes() == content
    assert target.stat().st_nlink == 1
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


@pytest.mark.parametrize("divergent", [False, True])
def test_public_replay_waits_for_early_visible_winner_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    divergent: bool,
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    requested_timestamp = "2026-08-14T12:00:00Z"
    winner_timestamp = "2026-08-14T12:00:01Z" if divergent else requested_timestamp
    winner_content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at=winner_timestamp)
    )
    winner_staging = outcome_path.with_name(".early-winner.staging")
    target = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    winner_staging.write_bytes(winner_content)
    winner_staging.chmod(0o600)
    os.link(winner_staging, target, follow_symlinks=False)
    waiting = threading.Event()
    release = threading.Event()

    def controlled_sleep(_: float) -> None:
        waiting.set()
        assert release.wait(timeout=5)

    def replay_loser() -> tuple[Path, bool] | str:
        try:
            return cli.project_terminal_evidence(
                outcome_path=outcome_path,
                produced_at=requested_timestamp,
                terminal_outcomes_root=root,
            )
        except cli.CreativeCodeTerminalOutcomeIOError as exc:
            return str(exc)

    monkeypatch.setattr(cli.time, "sleep", controlled_sleep)
    with ThreadPoolExecutor(max_workers=1) as pool:
        loser = pool.submit(replay_loser)
        assert waiting.wait(timeout=5)
        assert target.stat().st_nlink == 2
        winner_staging.unlink()
        release.set()
        result = loser.result(timeout=5)

    if divergent:
        assert result == "divergent_replay"
    else:
        assert result == (target, True)
    assert target.read_bytes() == winner_content
    assert target.stat().st_nlink == 1
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_public_replay_does_not_repair_persistent_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    outcome_path = _write_outcome(root, outcome)
    content = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(outcome, produced_at="2026-08-14T12:00:00Z")
    )
    external_link = outcome_path.with_name("external-sidecar-link.json")
    target = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    external_link.write_bytes(content)
    external_link.chmod(0o600)
    os.link(external_link, target, follow_symlinks=False)
    before = target.stat()
    monkeypatch.setattr(cli, "_COLLISION_STABILIZATION_ATTEMPTS", 2)
    monkeypatch.setattr(cli, "_COLLISION_STABILIZATION_DELAY_SECONDS", 0.0)

    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="hardlink_rejected"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    after = target.stat()
    assert target.read_bytes() == content
    assert external_link.exists()
    assert (after.st_ino, after.st_nlink, after.st_mode, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_nlink,
        before.st_mode,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )


def test_injected_after_collision_failure_preserves_complete_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    expected = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(_outcome(), produced_at="2026-08-14T12:00:00Z")
    )

    def collide(staging: Path, target: Path) -> None:
        os.link(staging, target, follow_symlinks=False)
        raise FileExistsError("injected EEXIST")

    def fail_after_collision(**_: Any) -> bool:
        raise cli.CreativeCodeTerminalOutcomeIOError("injected_after_collision")

    monkeypatch.setattr(cli, "_link_staging_file_noreplace", collide)
    monkeypatch.setattr(cli, "_validate_existing_projection", fail_after_collision)
    with pytest.raises(cli.CreativeCodeTerminalOutcomeIOError, match="injected_after_collision"):
        cli.project_terminal_evidence(
            outcome_path=outcome_path,
            produced_at="2026-08-14T12:00:00Z",
            terminal_outcomes_root=root,
        )
    sidecar = outcome_path.with_name(cli.EVIDENCE_EVENTS_FILE)
    assert sidecar.read_bytes() == expected
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    assert sidecar.stat().st_nlink == 1
    assert not list(outcome_path.parent.glob(".evidence_events.*.staging"))


def test_projection_contains_only_sanitized_allowlisted_values_and_imports() -> None:
    rendered = terminal_evidence_projection_bytes(
        build_terminal_evidence_events(_outcome(), produced_at="2026-08-14T12:00:00Z")
    ).decode()
    forbidden = (
        "pull_request_body",
        "review prose",
        "candidate.patch",
        "raw_prompt",
        "completion",
        "command_output",
        "secret",
        "environment",
        "/Users/",
        "76-tshusv",
    )
    assert all(token not in rendered for token in forbidden)

    contract_tree = ast.parse(
        Path(cli.__file__)
        .with_name("creative_code_terminal_outcome_contract.py")
        .read_text(encoding="utf-8")
    )
    cli_tree = ast.parse(Path(cli.__file__).read_text(encoding="utf-8"))
    imports = {
        alias.name
        for tree in (contract_tree, cli_tree)
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for tree in (contract_tree, cli_tree)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(
        fragment in imported
        for imported in imports
        for fragment in (
            "requests",
            "httpx",
            "urllib",
            "subprocess",
            "github",
            "sqlalchemy",
            "psycopg",
            "boto",
            "rag",
        )
    )

    adapter_source = "\n".join(
        inspect.getsource(function)
        for function in (
            build_terminal_evidence_events,
            validate_terminal_evidence_projection,
            cli._load_canonical_projection_outcome,
            cli._read_existing_projection_bytes,
            cli._validate_existing_projection,
            cli._project_terminal_evidence_locked,
            cli.project_terminal_evidence,
            cli.validate_projected_terminal_evidence,
        )
    ).lower()
    assert all(
        token not in adapter_source
        for token in (
            "telemetry",
            "provider",
            "network",
            "github",
            "database",
            "evidence_graph",
            "os.replace",
            ".chmod(",
        )
    )

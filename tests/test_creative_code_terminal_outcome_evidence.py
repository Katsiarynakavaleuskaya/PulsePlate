from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
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
    ["", "2026-08-14", "2026-08-14T12:00:00", "2026-08-14 12:00:00Z", "not-time"],
)
def test_builder_requires_explicit_rfc3339_offset(produced_at: str) -> None:
    with pytest.raises(CreativeCodeTerminalOutcomeError, match="produced_at"):
        build_terminal_evidence_events(_outcome(), produced_at=produced_at)


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
    assert (
        second.st_ino,
        second.st_mode,
        second.st_size,
        second.st_mtime_ns,
        second.st_ctime_ns,
    ) == (first.st_ino, first.st_mode, first.st_size, first.st_mtime_ns, first.st_ctime_ns)
    assert sidecar.read_bytes() == first_bytes
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
    assert "replay=identical" in capsys.readouterr().out


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


def test_injected_write_or_install_failure_cleans_private_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "terminal_outcomes"
    outcome_path = _write_outcome(root, _outcome())
    original_write = cli.os.write
    writes = 0

    def fail_second_write(descriptor: int, content: bytes) -> int:
        nonlocal writes
        writes += 1
        if writes == 1:
            return original_write(descriptor, content[: max(1, len(content) // 2)])
        raise OSError("injected write failure")

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

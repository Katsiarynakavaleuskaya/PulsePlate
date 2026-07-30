from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import errno
import json
from pathlib import Path
import re
import threading
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_terminal_outcome
from scripts.orchestration import creative_code_terminal_outcome_contract
from scripts.orchestration.creative_code_pr_promotion_contract import (
    build_creative_code_pr_promotion_plan,
    build_creative_code_pr_promotion_receipt,
    promotion_plan_fingerprint,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    default_cost_metadata,
)
from scripts.orchestration.creative_code_terminal_outcome_contract import (
    CANONICAL_REPOSITORY,
    CreativeCodeTerminalOutcomeError,
    MAX_JSON_OBJECT_BYTES,
    OUTCOME_KEYS,
    POST_MERGE_KEYS,
    REVIEW_KEYS,
    build_creative_code_terminal_outcome,
    canonical_json_bytes,
    normalize_terminal_observation,
    read_json_object,
    terminal_outcome_id,
    validate_creative_code_terminal_outcome,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_terminal_outcome.v1.schema.json"
)
CONTRACT_SOURCE = REPO_ROOT / "scripts/orchestration/creative_code_terminal_outcome_contract.py"
CLI_SOURCE = REPO_ROOT / "scripts/orchestration/creative_code_terminal_outcome.py"


def _promotion_lineage() -> tuple[dict[str, Any], dict[str, Any]]:
    plan = build_creative_code_pr_promotion_plan(
        promotion_id="terminal-test",
        source_result_id="result-terminal-test",
        source_request_id="request-terminal-test",
        source_bundle_id="bundle-terminal-test",
        source_bundle_fingerprint=fingerprint_payload({"bundle": "terminal"}),
        selected_variant_id="variant-terminal-test",
        selected_variant_fingerprint=fingerprint_payload({"variant": "terminal"}),
        patch_fingerprint=fingerprint_payload({"patch": "terminal"}),
        base_commit_sha="a" * 40,
        changed_paths=["core/rag/orchestration.py"],
        target_head_branch="experiment/terminal-test",
        pull_request_title="feat: terminal outcome test",
        pull_request_body_fingerprint=fingerprint_payload({"body": "terminal"}),
    )
    receipt = build_creative_code_pr_promotion_receipt(
        promotion_id=plan["promotion_id"],
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=fingerprint_payload({"validation": "terminal"}),
        approval_id="approval-terminal-test",
        source_result_id=plan["source_result_id"],
        patch_fingerprint=plan["patch_fingerprint"],
        head_branch=plan["target_head_branch"],
        commit_sha="b" * 40,
        pull_request_number=2201,
        pull_request_url=("https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201"),
        approved_by_login="Katsiarynakavaleuskaya",
    )
    return plan, receipt


def _complete_review(*, unresolved: int = 0, with_seal: bool = True) -> dict[str, Any]:
    return {
        "collection_state": "complete",
        "inventory_fingerprint": fingerprint_payload({"review": "inventory"}),
        "review_seal_fingerprint": (fingerprint_payload({"review": "seal"}) if with_seal else None),
        "sources_configured": 3,
        "sources_observed": 3,
        "findings_total": 2 + unresolved,
        "fixed": 1,
        "not_a_bug": 1,
        "deferred": 0,
        "unresolved_actionable": unresolved,
    }


def _unavailable_review() -> dict[str, Any]:
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


def _complete_post_merge() -> dict[str, Any]:
    return {
        "validation_inventory_fingerprint": fingerprint_payload({"post_merge": "inventory"}),
        "commands_configured": 2,
        "commands_executed": 2,
        "commands_passed": 2,
        "current_main_ci": "not_observed",
        "current_main_sha": None,
    }


def _not_observed_post_merge() -> dict[str, Any]:
    return {
        "validation_inventory_fingerprint": None,
        "commands_configured": 0,
        "commands_executed": 0,
        "commands_passed": 0,
        "current_main_ci": "not_observed",
        "current_main_sha": None,
    }


def _observation(
    *,
    terminal_state: str = "merged",
    review: dict[str, Any] | None = None,
    post_merge: dict[str, Any] | None = None,
    closure_epoch: int = 1,
    reason_code: str | None = None,
) -> dict[str, Any]:
    _, receipt = _promotion_lineage()
    closed = terminal_state == "closed_unmerged"
    return {
        "promotion_id": receipt["promotion_id"],
        "repository": receipt["repository"],
        "pull_request_number": receipt["pull_request_number"],
        "promoted_head_sha": receipt["commit_sha"],
        "closure_epoch": closure_epoch,
        "terminal_state": terminal_state,
        "merge_sha": None if closed else "c" * 40,
        "reason_code": ("abandoned" if reason_code is None else reason_code) if closed else None,
        "review": review if review is not None else _complete_review(),
        "post_merge": (
            post_merge
            if post_merge is not None
            else (_not_observed_post_merge() if closed else _complete_post_merge())
        ),
        "process": {
            "review_cycles": 2,
            "repair_cycles": 1,
            "validation_attempts": 3,
        },
        "cost_metadata": default_cost_metadata(),
        "sanitized": True,
    }


def _outcome(**observation_overrides: Any) -> dict[str, Any]:
    plan, receipt = _promotion_lineage()
    return build_creative_code_terminal_outcome(
        promotion_plan=plan,
        promotion_receipt=receipt,
        observation=_observation(**observation_overrides),
    )


def _write_build_inputs(input_root: Path) -> dict[str, Path]:
    plan, receipt = _promotion_lineage()
    fixture_root = input_root / "fixture"
    fixture_root.mkdir(parents=True)
    paths = {
        "promotion_plan": fixture_root / "plan.json",
        "promotion_receipt": fixture_root / "receipt.json",
        "observation": fixture_root / "observation.json",
    }
    payloads = {
        "promotion_plan": plan,
        "promotion_receipt": receipt,
        "observation": _observation(),
    }
    for label, path in paths.items():
        path.write_text(json.dumps(payloads[label]), encoding="utf-8")
    return paths


@pytest.mark.parametrize(
    ("terminal_state", "reason_code", "post_merge_observation"),
    [
        ("merged", None, "complete_observed"),
        ("closed_unmerged", "superseded", "not_applicable"),
        ("closed_unmerged", "abandoned", "not_applicable"),
        ("closed_unmerged", "validation_failed", "not_applicable"),
        ("closed_unmerged", "governance_blocked", "not_applicable"),
        ("closed_unmerged", "rescoped", "not_applicable"),
        ("closed_unmerged", "unknown", "not_applicable"),
    ],
)
def test_terminal_branches_and_closed_reason_codes(
    terminal_state: str,
    reason_code: str | None,
    post_merge_observation: str,
) -> None:
    outcome = _outcome(
        terminal_state=terminal_state,
        reason_code=reason_code,
    )

    assert outcome["terminal_state"] == terminal_state
    assert outcome["post_merge_observation"] == post_merge_observation
    assert validate_creative_code_terminal_outcome(outcome) == outcome


@pytest.mark.parametrize(
    ("review", "expected_review", "expected_governance"),
    [
        (_complete_review(unresolved=1), "actionables_observed", "blockers_observed"),
        (
            _complete_review(unresolved=0, with_seal=True),
            "no_actionables_observed",
            "no_blockers_observed",
        ),
        (
            _complete_review(unresolved=0, with_seal=False),
            "evidence_unavailable",
            "evidence_unavailable",
        ),
        (
            _unavailable_review(),
            "evidence_unavailable",
            "evidence_unavailable",
        ),
    ],
)
def test_review_and_governance_are_derived_without_authority_claims(
    review: dict[str, Any],
    expected_review: str,
    expected_governance: str,
) -> None:
    outcome = _outcome(review=review)

    assert outcome["review_observation"] == expected_review
    assert outcome["governance_observation"] == expected_governance
    emitted = json.dumps(outcome, sort_keys=True)
    assert "conformant" not in emitted
    assert '"passed"' not in emitted


@pytest.mark.parametrize(
    ("post_merge", "expected"),
    [
        (_complete_post_merge(), "complete_observed"),
        (
            {
                **_complete_post_merge(),
                "commands_executed": 1,
                "commands_passed": 1,
            },
            "incomplete_observed",
        ),
        (
            {
                **_complete_post_merge(),
                "current_main_ci": "failure",
                "current_main_sha": "d" * 40,
            },
            "incomplete_observed",
        ),
        (
            {
                **_not_observed_post_merge(),
                "validation_inventory_fingerprint": fingerprint_payload(
                    {"post_merge": "ci-inventory"}
                ),
                "current_main_ci": "success",
                "current_main_sha": "d" * 40,
            },
            "complete_observed",
        ),
        (_not_observed_post_merge(), "evidence_unavailable"),
    ],
)
def test_post_merge_observations_are_closed_and_evidence_bound(
    post_merge: dict[str, Any],
    expected: str,
) -> None:
    outcome = _outcome(post_merge=post_merge)
    assert outcome["post_merge_observation"] == expected


def test_terminal_unavailable_is_collection_error_and_emits_no_outcome(
    tmp_path: Path,
) -> None:
    observation = _observation()
    observation["terminal_state"] = "unavailable"
    paths = _write_build_inputs(tmp_path)
    paths["observation"].write_text(json.dumps(observation), encoding="utf-8")
    output_root = tmp_path / "terminal_outcomes"

    with pytest.raises(
        CreativeCodeTerminalOutcomeError,
        match="terminal_evidence_unavailable",
    ):
        creative_code_terminal_outcome.build_and_publish(
            promotion_plan_path=paths["promotion_plan"],
            promotion_receipt_path=paths["promotion_receipt"],
            observation_path=paths["observation"],
            input_root=tmp_path,
            output_root=output_root,
        )
    assert not output_root.exists()


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: value.update(merge_sha=None), "requires merge_sha"),
        (
            lambda value: value["review"].update(sources_observed=2),
            "fully observed",
        ),
        (
            lambda value: value["review"].update(findings_total=99),
            "disposition counters",
        ),
        (
            lambda value: value["review"].update(sources_configured=True),
            "must be an integer",
        ),
        (
            lambda value: value["process"].update(review_cycles=-1),
            "between 0",
        ),
        (
            lambda value: value["process"].update(validation_attempts=1_000_001),
            "between 0",
        ),
        (
            lambda value: value["post_merge"].update(commands_passed=3),
            "passed <= executed",
        ),
        (
            lambda value: value["post_merge"].update(
                current_main_ci="success",
                current_main_sha=None,
            ),
            "requires current_main_sha",
        ),
    ],
)
def test_impossible_and_malformed_observations_fail_closed(
    mutator: Any,
    message: str,
) -> None:
    observation = _observation()
    mutator(observation)
    with pytest.raises(CreativeCodeTerminalOutcomeError, match=message):
        normalize_terminal_observation(observation)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda value: value["review"].update(sources_observed=2),
            "fully observed",
        ),
        (
            lambda value: value["review"].update(findings_total=99),
            "disposition counters",
        ),
        (
            lambda value: value["post_merge"].update(commands_passed=3),
            "passed <= executed",
        ),
        (
            lambda value: value["post_merge"].update(commands_executed=3),
            "passed <= executed",
        ),
    ],
)
def test_python_validator_is_normative_for_cross_property_arithmetic(
    mutator: Any,
    message: str,
) -> None:
    observation = _observation()
    mutator(observation)

    with pytest.raises(CreativeCodeTerminalOutcomeError, match=message):
        normalize_terminal_observation(observation)


@pytest.mark.parametrize(
    ("field", "forged_value", "message"),
    [
        (
            "review_observation",
            "actionables_observed",
            "review_observation does not match",
        ),
        (
            "governance_observation",
            "blockers_observed",
            "governance_observation does not match",
        ),
        (
            "post_merge_observation",
            "incomplete_observed",
            "post_merge_observation does not match",
        ),
    ],
)
def test_python_validator_rederives_observation_tokens(
    field: str,
    forged_value: str,
    message: str,
) -> None:
    outcome = _outcome()
    outcome[field] = forged_value

    with pytest.raises(CreativeCodeTerminalOutcomeError, match=message):
        validate_creative_code_terminal_outcome(outcome)


def test_lineage_mismatches_fail_before_outcome_creation() -> None:
    plan, receipt = _promotion_lineage()
    cases: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    changed_receipt = deepcopy(receipt)
    changed_receipt["source_result_id"] = "different-result"
    cases.append((plan, changed_receipt, _observation()))
    changed_observation = _observation()
    changed_observation["pull_request_number"] = 2202
    cases.append((plan, receipt, changed_observation))
    changed_head = _observation()
    changed_head["promoted_head_sha"] = "e" * 40
    cases.append((plan, receipt, changed_head))

    for candidate_plan, candidate_receipt, observation in cases:
        with pytest.raises(
            CreativeCodeTerminalOutcomeError,
            match="lineage",
        ):
            build_creative_code_terminal_outcome(
                promotion_plan=candidate_plan,
                promotion_receipt=candidate_receipt,
                observation=observation,
            )


def test_repository_is_exact_across_observation_lineage_and_identity() -> None:
    forged_repository = "another-owner/another-repo"
    observation = _observation()
    observation["repository"] = forged_repository
    with pytest.raises(
        CreativeCodeTerminalOutcomeError,
        match="repository must equal",
    ):
        normalize_terminal_observation(observation)

    forged_outcome = _outcome()
    forged_outcome["lineage"]["repository"] = forged_repository
    with pytest.raises(
        CreativeCodeTerminalOutcomeError,
        match="repository must equal",
    ):
        validate_creative_code_terminal_outcome(forged_outcome)

    with pytest.raises(
        CreativeCodeTerminalOutcomeError,
        match="repository must equal",
    ):
        terminal_outcome_id(
            repository=forged_repository,
            pull_request_number=2201,
            promotion_id="terminal-test",
            promoted_head_sha="b" * 40,
        )


def test_duplicate_keys_and_unsafe_content_fail_closed(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"GITHUB_TOKEN":"first","GITHUB_TOKEN":"second"}',
        encoding="utf-8",
    )
    with pytest.raises(CreativeCodeTerminalOutcomeError, match="duplicate key") as error:
        read_json_object(duplicate)
    assert "GITHUB_TOKEN" not in str(error.value)

    outcome = _outcome()
    outcome["GITHUB_TOKEN"] = "untrusted"
    with pytest.raises(CreativeCodeTerminalOutcomeError, match="unsupported fields") as error:
        validate_creative_code_terminal_outcome(outcome)
    assert "GITHUB_TOKEN" not in str(error.value)

    observation = _observation()
    observation["promotion_id"] = "candidate.patch"
    with pytest.raises(CreativeCodeTerminalOutcomeError):
        normalize_terminal_observation(observation)


def test_identical_and_divergent_replay_preserve_original_bytes_and_mtime(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "terminal_outcomes"
    original = _outcome(closure_epoch=1)
    target, replayed = creative_code_terminal_outcome.publish_terminal_outcome(
        original,
        output_root=output_root,
    )
    original_bytes = target.read_bytes()
    original_mtime = target.stat().st_mtime_ns

    replay_target, replayed_again = creative_code_terminal_outcome.publish_terminal_outcome(
        original,
        output_root=output_root,
    )
    assert replayed is False
    assert replayed_again is True
    assert replay_target == target
    assert target.read_bytes() == original_bytes
    assert target.stat().st_mtime_ns == original_mtime

    divergent = _outcome(closure_epoch=2)
    assert divergent["outcome_id"] == original["outcome_id"]
    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match="divergent_replay",
    ):
        creative_code_terminal_outcome.publish_terminal_outcome(
            divergent,
            output_root=output_root,
        )
    assert target.read_bytes() == original_bytes
    assert target.stat().st_mtime_ns == original_mtime


def test_prelink_failure_leaves_only_reusable_empty_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    target_dir = output_root / outcome["outcome_id"]
    target_file = target_dir / creative_code_terminal_outcome.OUTCOME_FILE
    real_link = creative_code_terminal_outcome._link_staging_file_noreplace

    def fail_before_link(staging_file: Path, canonical_file: Path) -> None:
        assert staging_file.parent == output_root
        assert canonical_file == target_file
        assert staging_file.is_file()
        raise creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError(
            "injected_prepublication_failure"
        )

    monkeypatch.setattr(
        creative_code_terminal_outcome,
        "_link_staging_file_noreplace",
        fail_before_link,
    )
    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match="injected_prepublication_failure",
    ):
        creative_code_terminal_outcome.publish_terminal_outcome(
            outcome,
            output_root=output_root,
        )
    assert target_dir.is_dir()
    assert list(target_dir.iterdir()) == []
    assert list(output_root.iterdir()) == [target_dir]

    monkeypatch.setattr(
        creative_code_terminal_outcome,
        "_link_staging_file_noreplace",
        real_link,
    )
    target, replayed = creative_code_terminal_outcome.publish_terminal_outcome(
        outcome,
        output_root=output_root,
    )
    assert replayed is False
    assert target.read_bytes() == canonical_json_bytes(outcome)


def test_unsupported_hardlink_fails_closed_and_retry_recovers_empty_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    target_dir = output_root / outcome["outcome_id"]
    target_file = target_dir / creative_code_terminal_outcome.OUTCOME_FILE
    real_link = creative_code_terminal_outcome.os.link

    def unsupported_link(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(errno.EXDEV, "injected cross-device hardlink")

    monkeypatch.setattr(creative_code_terminal_outcome.os, "link", unsupported_link)
    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match="terminal_outcome_hardlink_unsupported",
    ):
        creative_code_terminal_outcome.publish_terminal_outcome(
            outcome,
            output_root=output_root,
        )

    assert target_dir.is_dir()
    assert not target_file.exists()
    assert list(target_dir.iterdir()) == []
    assert list(output_root.iterdir()) == [target_dir]

    monkeypatch.setattr(creative_code_terminal_outcome.os, "link", real_link)
    target, replayed = creative_code_terminal_outcome.publish_terminal_outcome(
        outcome,
        output_root=output_root,
    )
    assert replayed is False
    assert target == target_file
    assert target.read_bytes() == canonical_json_bytes(outcome)


def test_concurrent_identical_publication_is_atomic_and_replay_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    real_link = creative_code_terminal_outcome._link_staging_file_noreplace
    publication_barrier = threading.Barrier(2)

    def synchronized_link(staging_file: Path, target_file: Path) -> None:
        publication_barrier.wait(timeout=5)
        real_link(staging_file, target_file)

    monkeypatch.setattr(
        creative_code_terminal_outcome,
        "_link_staging_file_noreplace",
        synchronized_link,
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                creative_code_terminal_outcome.publish_terminal_outcome,
                outcome,
                output_root=output_root,
            )
            for _index in range(2)
        ]
        results = [future.result(timeout=10) for future in futures]

    assert sorted(replayed for _path, replayed in results) == [False, True]
    assert {path for path, _replayed in results} == {
        output_root / outcome["outcome_id"] / creative_code_terminal_outcome.OUTCOME_FILE
    }
    assert results[0][0].read_bytes() == canonical_json_bytes(outcome)
    assert list(output_root.iterdir()) == [output_root / outcome["outcome_id"]]


def test_empty_namespace_is_reused_without_directory_replacement(tmp_path: Path) -> None:
    output_root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    target_dir = output_root / outcome["outcome_id"]
    target_dir.mkdir(parents=True)
    namespace_identity = (target_dir.stat().st_dev, target_dir.stat().st_ino)

    target, replayed = creative_code_terminal_outcome.publish_terminal_outcome(
        outcome,
        output_root=output_root,
    )

    assert replayed is False
    assert (target_dir.stat().st_dev, target_dir.stat().st_ino) == namespace_identity
    assert target.read_bytes() == canonical_json_bytes(outcome)


def test_nonempty_namespace_without_canonical_file_is_ambiguous(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    target_dir = output_root / outcome["outcome_id"]
    target_dir.mkdir(parents=True)
    marker = target_dir / "foreign.marker"
    marker.write_text("preserve\n", encoding="utf-8")

    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match="terminal_outcome_namespace_ambiguous",
    ):
        creative_code_terminal_outcome.publish_terminal_outcome(
            outcome,
            output_root=output_root,
        )

    assert marker.read_text(encoding="utf-8") == "preserve\n"
    assert not (target_dir / creative_code_terminal_outcome.OUTCOME_FILE).exists()
    assert list(output_root.iterdir()) == [target_dir]


def test_file_link_linearization_preserves_existing_canonical_bytes(
    tmp_path: Path,
) -> None:
    staging = tmp_path / ".terminal.staging"
    target_dir = tmp_path / "terminal"
    target_dir.mkdir()
    target = target_dir / creative_code_terminal_outcome.OUTCOME_FILE
    staging.write_bytes(b"candidate\n")
    target.write_bytes(b"original\n")
    target_identity = (target.stat().st_dev, target.stat().st_ino)

    with pytest.raises(FileExistsError):
        creative_code_terminal_outcome._link_staging_file_noreplace(
            staging,
            target,
        )

    assert target.read_bytes() == b"original\n"
    assert (target.stat().st_dev, target.stat().st_ino) == target_identity
    assert staging.read_bytes() == b"candidate\n"


def test_existing_replay_survives_other_publisher_crash_after_link(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "terminal_outcomes"
    outcome = _outcome()
    target_dir = output_root / outcome["outcome_id"]
    target_dir.mkdir(parents=True)
    target = target_dir / creative_code_terminal_outcome.OUTCOME_FILE
    abandoned_staging = output_root / ".other-publisher.staging"
    abandoned_staging.write_bytes(canonical_json_bytes(outcome))
    creative_code_terminal_outcome._link_staging_file_noreplace(
        abandoned_staging,
        target,
    )
    target_mtime = target.stat().st_mtime_ns

    replay_target, replayed = creative_code_terminal_outcome.publish_terminal_outcome(
        outcome,
        output_root=output_root,
    )

    assert replayed is True
    assert replay_target == target
    assert target.read_bytes() == canonical_json_bytes(outcome)
    assert target.stat().st_mtime_ns == target_mtime
    assert abandoned_staging.is_file()


def test_cli_build_and_validate_accept_contained_inputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_root = tmp_path / "creative_code"
    output_root = input_root / "terminal_outcomes"
    paths = _write_build_inputs(input_root)

    assert (
        creative_code_terminal_outcome.main(
            [
                "build",
                "--promotion-plan",
                str(paths["promotion_plan"]),
                "--promotion-receipt",
                str(paths["promotion_receipt"]),
                "--observation",
                str(paths["observation"]),
            ],
            input_root=input_root,
            terminal_outcomes_root=output_root,
        )
        == 0
    )
    assert creative_code_terminal_outcome.SUCCESS_BUILD_OUTPUT in capsys.readouterr().out
    outcomes = list(output_root.glob(f"*/{creative_code_terminal_outcome.OUTCOME_FILE}"))
    assert len(outcomes) == 1

    assert (
        creative_code_terminal_outcome.main(
            ["validate", "--outcome", str(outcomes[0])],
            terminal_outcomes_root=output_root,
        )
        == 0
    )
    assert creative_code_terminal_outcome.SUCCESS_VALIDATE_OUTPUT in capsys.readouterr().out


def test_build_inputs_reject_absolute_outside_and_traversal_paths(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "creative_code"
    paths = _write_build_inputs(input_root)
    outside_plan = tmp_path / "outside-plan.json"
    outside_plan.write_bytes(paths["promotion_plan"].read_bytes())
    cases = [
        (outside_plan, "promotion_plan_outside_allowed_root"),
        (
            input_root / ".." / outside_plan.name,
            "promotion_plan_traversal_rejected",
        ),
    ]

    for candidate, expected_error in cases:
        with pytest.raises(
            creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
            match=expected_error,
        ):
            creative_code_terminal_outcome.build_and_publish(
                promotion_plan_path=candidate,
                promotion_receipt_path=paths["promotion_receipt"],
                observation_path=paths["observation"],
                input_root=input_root,
                output_root=tmp_path / "terminal_outcomes",
            )


def test_validate_cli_rejects_outside_and_traversal_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    terminal_root = tmp_path / "terminal_outcomes"
    terminal_root.mkdir()
    outside = tmp_path / "outside-outcome.json"
    outside.write_bytes(canonical_json_bytes(_outcome()))
    cases = [
        (outside, "terminal_outcome_outside_allowed_root"),
        (
            terminal_root / ".." / outside.name,
            "terminal_outcome_traversal_rejected",
        ),
    ]

    for candidate, expected_error in cases:
        assert (
            creative_code_terminal_outcome.main(
                ["validate", "--outcome", str(candidate)],
                terminal_outcomes_root=terminal_root,
            )
            == 1
        )
        assert expected_error in capsys.readouterr().out


def test_containment_rejects_symlink_escape_before_read(tmp_path: Path) -> None:
    input_root = tmp_path / "creative_code"
    input_root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    escaped = input_root / "escaped.json"
    try:
        escaped.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match="promotion_plan_symlink_rejected",
    ):
        creative_code_terminal_outcome._read_regular_json(
            escaped,
            label="promotion_plan",
            allowed_root=input_root,
        )


@pytest.mark.parametrize(
    ("oversized_input", "expected_error"),
    [
        ("promotion_plan", "promotion_plan_too_large"),
        ("promotion_receipt", "promotion_receipt_too_large"),
        ("observation", "observation_too_large"),
    ],
)
def test_build_inputs_reject_oversized_json_before_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    oversized_input: str,
    expected_error: str,
) -> None:
    input_root = tmp_path / "creative_code"
    paths = _write_build_inputs(input_root)
    paths[oversized_input].write_bytes(b"{" + b" " * MAX_JSON_OBJECT_BYTES)

    real_reader = creative_code_terminal_outcome.read_json_object

    def guarded_parse(path: str | Path) -> dict[str, Any]:
        if Path(path) == paths[oversized_input]:
            raise AssertionError("oversized JSON reached parser")
        return real_reader(path)

    monkeypatch.setattr(
        creative_code_terminal_outcome,
        "read_json_object",
        guarded_parse,
    )
    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match=expected_error,
    ):
        creative_code_terminal_outcome.build_and_publish(
            promotion_plan_path=paths["promotion_plan"],
            promotion_receipt_path=paths["promotion_receipt"],
            observation_path=paths["observation"],
            input_root=input_root,
            output_root=tmp_path / "terminal_outcomes",
        )


def test_validate_input_and_contract_reader_reject_oversized_json_before_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    oversized = tmp_path / "terminal_outcome.json"
    oversized.write_bytes(b"{" + b" " * MAX_JSON_OBJECT_BYTES)

    assert (
        creative_code_terminal_outcome.main(
            ["validate", "--outcome", str(oversized)],
            terminal_outcomes_root=tmp_path,
        )
        == 1
    )
    assert "terminal_outcome_too_large" in capsys.readouterr().out

    def unexpected_loads(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("oversized JSON reached parser")

    monkeypatch.setattr(
        creative_code_terminal_outcome_contract.json,
        "loads",
        unexpected_loads,
    )
    with pytest.raises(
        CreativeCodeTerminalOutcomeError,
        match="terminal_json_too_large",
    ):
        read_json_object(oversized)


def test_cli_rejects_symlink_and_non_regular_inputs(tmp_path: Path) -> None:
    source = tmp_path / "observation.json"
    source.write_text(json.dumps(_observation()), encoding="utf-8")
    link = tmp_path / "observation-link.json"
    try:
        link.symlink_to(source)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match="symlink",
    ):
        creative_code_terminal_outcome._read_regular_json(
            link,
            label="observation",
            allowed_root=tmp_path,
        )
    with pytest.raises(
        creative_code_terminal_outcome.CreativeCodeTerminalOutcomeIOError,
        match="regular",
    ):
        creative_code_terminal_outcome._read_regular_json(
            tmp_path,
            label="observation",
            allowed_root=tmp_path,
        )


def test_runtime_and_schema_closed_shape_finite_implication_alignment() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    outcome = _outcome()

    assert "normative semantic validator" in schema["$comment"]
    assert "$data" not in json.dumps(schema, sort_keys=True)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == OUTCOME_KEYS
    assert set(schema["$defs"]["review_evidence"]["required"]) == REVIEW_KEYS
    assert set(schema["$defs"]["post_merge_evidence"]["required"]) == POST_MERGE_KEYS
    complete_review_shape = schema["$defs"]["review_evidence"]["allOf"][0]["else"]["properties"]
    assert complete_review_shape["sources_configured"]["minimum"] == 1
    assert complete_review_shape["sources_observed"]["minimum"] == 1
    assert schema["properties"]["terminal_state"]["enum"] == [
        "merged",
        "closed_unmerged",
    ]
    assert schema["properties"]["review_observation"]["enum"] == [
        "actionables_observed",
        "no_actionables_observed",
        "evidence_unavailable",
    ]
    assert schema["$defs"]["lineage"]["properties"]["repository"]["const"] == CANONICAL_REPOSITORY
    unsafe_pattern = schema["$defs"]["safe_id"]["not"]["pattern"]
    assert schema["$defs"]["promotion_id"]["not"] == {"pattern": unsafe_pattern}
    assert re.search(unsafe_pattern, "GH_TOKEN", re.IGNORECASE)
    unavailable_cost_implication = schema["$defs"]["cost_metadata"]["allOf"][0]
    assert unavailable_cost_implication["if"]["properties"]["available"] == {"const": False}
    assert unavailable_cost_implication["then"]["properties"] == {
        "input_tokens": {"type": "null"},
        "cached_input_tokens": {"type": "null"},
        "output_tokens": {"type": "null"},
        "reasoning_output_tokens": {"type": "null"},
        "estimated": {"const": False},
    }

    review_implications = [
        clause
        for clause in schema["allOf"]
        if "review_evidence" in clause.get("if", {}).get("properties", {})
    ]
    assert len(review_implications) == 4
    review_conditions = [
        clause["if"]["properties"]["review_evidence"]["properties"]
        for clause in review_implications
    ]
    assert review_conditions[0]["collection_state"] == {"const": "unavailable"}
    assert review_conditions[1]["unresolved_actionable"] == {
        "type": "integer",
        "minimum": 1,
    }
    assert review_conditions[2]["unresolved_actionable"] == {"const": 0}
    assert review_conditions[2]["review_seal_fingerprint"] == {"$ref": "#/$defs/sha256"}
    assert review_conditions[3]["unresolved_actionable"] == {"const": 0}
    assert review_conditions[3]["review_seal_fingerprint"] == {"type": "null"}
    assert [
        (
            clause["then"]["properties"]["review_observation"]["const"],
            clause["then"]["properties"]["governance_observation"]["const"],
        )
        for clause in review_implications
    ] == [
        ("evidence_unavailable", "evidence_unavailable"),
        ("actionables_observed", "blockers_observed"),
        ("no_actionables_observed", "no_blockers_observed"),
        ("evidence_unavailable", "evidence_unavailable"),
    ]

    post_merge_shape_implications = schema["$defs"]["post_merge_evidence"]["allOf"]
    assert len(post_merge_shape_implications) == 4
    assert post_merge_shape_implications[1]["then"]["properties"] == {
        "commands_executed": {"const": 0},
        "commands_passed": {"const": 0},
    }
    assert post_merge_shape_implications[2]["then"]["properties"] == {
        "commands_passed": {"const": 0}
    }
    assert post_merge_shape_implications[3]["then"]["properties"][
        "validation_inventory_fingerprint"
    ] == {"$ref": "#/$defs/sha256"}

    post_merge_implications = [
        clause
        for clause in schema["allOf"]
        if (
            "post_merge_evidence" in clause.get("if", {}).get("properties", {})
            or "post_merge_observation" in clause.get("if", {}).get("properties", {})
        )
    ]
    assert len(post_merge_implications) == 5
    assert post_merge_implications[0]["then"]["properties"]["post_merge_observation"] == {
        "const": "evidence_unavailable"
    }
    assert post_merge_implications[1]["then"]["properties"]["post_merge_observation"] == {
        "const": "incomplete_observed"
    }
    assert post_merge_implications[2]["then"]["properties"]["post_merge_evidence"]["properties"][
        "validation_inventory_fingerprint"
    ] == {"$ref": "#/$defs/sha256"}
    assert post_merge_implications[3]["then"]["properties"]["post_merge_evidence"]["properties"][
        "current_main_ci"
    ] == {"enum": ["success", "not_observed"]}
    assert post_merge_implications[4]["then"]["properties"]["post_merge_evidence"][
        "properties"
    ] == {
        "commands_configured": {"const": 0},
        "commands_executed": {"const": 0},
        "commands_passed": {"const": 0},
        "current_main_ci": {"const": "not_observed"},
    }

    assert set(outcome) == set(schema["required"])
    assert validate_creative_code_terminal_outcome(outcome) == outcome
    assert canonical_json_bytes(outcome).endswith(b"\n")


def test_terminal_modules_have_no_network_provider_runtime_or_subprocess_calls() -> None:
    forbidden_import_roots = {
        "app",
        "httpx",
        "requests",
        "subprocess",
        "urllib",
        "github",
    }
    for path in (CONTRACT_SOURCE, CLI_SOURCE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        assert imports.isdisjoint(forbidden_import_roots)
        source = path.read_text(encoding="utf-8")
        assert "EvidenceGraph" not in source
        assert "provider_call" not in source

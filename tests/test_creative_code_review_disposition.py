from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_review_disposition as disposition_cli
from scripts.orchestration.creative_code_review_disposition_contract import (
    CreativeCodeReviewDispositionContractError,
    build_creative_code_repair_launch_packet,
    build_creative_code_review_disposition_packet,
    build_creative_code_review_feedback_record,
    classify_feedback_record,
    read_json_object,
    validate_creative_code_repair_launch_packet,
    validate_creative_code_review_disposition_packet,
    validate_creative_code_review_feedback_record,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "docs" / "orchestration" / "contracts"
FEEDBACK_SCHEMA = SCHEMA_ROOT / "creative_code_review_feedback_record.v1.schema.json"
DISPOSITION_SCHEMA = SCHEMA_ROOT / "creative_code_review_disposition_packet.v1.schema.json"
LAUNCH_SCHEMA = SCHEMA_ROOT / "creative_code_repair_launch_packet.v1.schema.json"
CLI_SOURCE = REPO_ROOT / "scripts" / "orchestration" / "creative_code_review_disposition.py"


def _assert_object_schemas_are_closed(schema_fragment: Any) -> None:
    if isinstance(schema_fragment, dict):
        if schema_fragment.get("type") == "object":
            assert schema_fragment["additionalProperties"] is False
        for value in schema_fragment.values():
            _assert_object_schemas_are_closed(value)
    elif isinstance(schema_fragment, list):
        for value in schema_fragment:
            _assert_object_schemas_are_closed(value)


def _record(
    *,
    excerpt: str = "coverage guard failed on review-disposition integration",
    feedback_kind: str = "review_thread",
    severity: str = "medium",
) -> dict[str, Any]:
    return build_creative_code_review_feedback_record(
        source_kind="github_fixture",
        source_id="review-comment:1",
        source_fingerprint=fingerprint_payload({"source": "review-comment:1"}),
        excerpt=excerpt,
        feedback_kind=feedback_kind,
        severity=severity,
        source_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2045#discussion_r1",
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2045,
        head_sha="a" * 40,
        path="scripts/orchestration/creative_code_review_disposition.py",
        line=42,
        side="right",
    )


def _source_context() -> dict[str, Any]:
    return {
        "source_kind": "github_fixture",
        "source_id": "fixture:2045",
        "source_fingerprint": fingerprint_payload({"fixture": 2045}),
        "context_path": None,
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "pr_number": 2045,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _configure_cli_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "repo" / "artifacts" / "orchestration" / "creative_code"
    review_root = root / "review_disposition"
    monkeypatch.setattr(disposition_cli, "CREATIVE_CODE_ROOT", root)
    monkeypatch.setattr(disposition_cli, "REVIEW_DISPOSITION_ROOT", review_root)
    return review_root


def test_review_disposition_schemas_are_closed_and_finite() -> None:
    feedback_schema = json.loads(FEEDBACK_SCHEMA.read_text(encoding="utf-8"))
    disposition_schema = json.loads(DISPOSITION_SCHEMA.read_text(encoding="utf-8"))
    launch_schema = json.loads(LAUNCH_SCHEMA.read_text(encoding="utf-8"))

    for schema in (feedback_schema, disposition_schema, launch_schema):
        _assert_object_schemas_are_closed(schema)

    disposition_enum = feedback_schema["$defs"]["classification"]["properties"][
        "candidate_disposition"
    ]["enum"]
    assert disposition_enum == [
        "simple_fix",
        "creative_repair_candidate",
        "not_a_bug_candidate",
        "defer_candidate",
        "out_of_scope",
        "security_blocker",
    ]
    assert (
        launch_schema["$defs"]["authority"]["properties"]["create_pr1_specification"]["const"]
        is True
    )
    for key, schema in launch_schema["$defs"]["authority"]["properties"].items():
        if key != "create_pr1_specification":
            assert schema["const"] is False


def test_feedback_disposition_and_launch_packets_validate() -> None:
    classified = classify_feedback_record(_record())
    assert classified["classification"] == {
        "candidate_disposition": "creative_repair_candidate",
        "reason_code": "test_failure",
        "requires_human_decision": True,
        "requires_repair": True,
        "repair_priority": 2,
    }

    packet = build_creative_code_review_disposition_packet(
        feedback_records=[classified],
        source_context=_source_context(),
        expected_head_sha="a" * 40,
        actual_head_sha="a" * 40,
    )
    assert validate_creative_code_review_disposition_packet(packet)["summary"] == {
        "blocked_by_head_drift": 0,
        "deferred_candidates": 0,
        "highest_repair_priority": 2,
        "not_actionable": 0,
        "records_total": 1,
        "repair_candidates": 1,
    }

    launch = build_creative_code_repair_launch_packet(packet)
    validated = validate_creative_code_repair_launch_packet(launch)
    assert validated["target_pr1_specification"]["allowed"] is True
    assert validated["authority"] == {
        "create_pr1_specification": True,
        "edit_fixed_mapping": False,
        "generate_patch": False,
        "merge": False,
        "open_pr": False,
        "push": False,
        "resolve_threads": False,
        "write_branch": False,
    }


def test_repair_launch_packet_sorts_candidates_before_identity() -> None:
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[
            _record(excerpt="test fail in lower-priority validator"),
            _record(excerpt="credential issue in sanitized review summary", severity="critical"),
        ],
        source_context=_source_context(),
        expected_head_sha="a" * 40,
        actual_head_sha="a" * 40,
    )

    launch = validate_creative_code_repair_launch_packet(
        build_creative_code_repair_launch_packet(packet)
    )
    assert [candidate["repair_priority"] for candidate in launch["repair_candidates"]] == [3, 2]


def test_json_duplicate_keys_and_unknown_fields_are_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"1.0"}\n', encoding="utf-8")

    with pytest.raises(
        CreativeCodeReviewDispositionContractError,
        match="duplicate key: schema_version",
    ):
        read_json_object(duplicate)

    record = _record()
    record["unknown"] = "not allowed"
    with pytest.raises(
        CreativeCodeReviewDispositionContractError,
        match="unsupported fields: unknown",
    ):
        validate_creative_code_review_feedback_record(record)


@pytest.mark.parametrize(
    "excerpt",
    [
        "raw_body: please keep the original review body",
        "credential GH_TOKEN leaked in review text",
        "see local file /Users/example/private.txt",
    ],
)
def test_raw_body_secret_and_local_path_leakage_are_rejected(excerpt: str) -> None:
    with pytest.raises(
        CreativeCodeReviewDispositionContractError,
        match="unsafe review-disposition text",
    ):
        _record(excerpt=excerpt)


def test_head_sha_drift_blocks_repair_launch() -> None:
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[_record()],
        source_context=_source_context(),
        expected_head_sha="a" * 40,
        actual_head_sha="b" * 40,
    )

    assert packet["head_sha_drift"] is True
    assert packet["summary"]["blocked_by_head_drift"] == 1
    assert packet["feedback_records"][0]["classification"] == {
        "candidate_disposition": "out_of_scope",
        "reason_code": "head_sha_drift",
        "requires_human_decision": True,
        "requires_repair": False,
        "repair_priority": 0,
    }
    with pytest.raises(
        CreativeCodeReviewDispositionContractError,
        match="head SHA drift is present",
    ):
        build_creative_code_repair_launch_packet(packet)


def test_local_pr_review_context_collect_classify_launch_and_summarize(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    review_root = _configure_cli_root(monkeypatch, tmp_path)
    context_path = tmp_path / "pr_review_context.json"
    _write_json(
        context_path,
        {
            "generated_at_utc": "2026-06-29T12:00:00Z",
            "pr": {"head_sha": "a" * 40, "number": 2045},
            "query": {
                "head_ref": "a" * 40,
                "pr_number": 2045,
                "repo": "Katsiarynakavaleuskaya/PulsePlate",
            },
            "review_source_status": [
                {
                    "blocking": False,
                    "reason": "CodeRabbit source available",
                    "source": "coderabbit",
                    "source_degraded": False,
                    "status": "available",
                }
            ],
            "warnings": ["coverage guard failed for changed review-disposition CLI"],
        },
    )

    assert (
        disposition_cli.main(
            ["collect", "--review-context", str(context_path), "--output", "collection.json"]
        )
        == 0
    )
    collection_path = review_root / "collection.json"
    assert collection_path.exists()

    assert (
        disposition_cli.main(
            [
                "classify",
                "--input",
                str(collection_path),
                "--output",
                "disposition.json",
                "--expected-head-sha",
                "a" * 40,
                "--actual-head-sha",
                "a" * 40,
            ]
        )
        == 0
    )
    disposition_path = review_root / "disposition.json"
    packet = validate_creative_code_review_disposition_packet(read_json_object(disposition_path))
    assert packet["summary"]["repair_candidates"] == 1

    assert (
        disposition_cli.main(
            [
                "prepare-launch",
                "--disposition-packet",
                str(disposition_path),
                "--output",
                "launch.json",
            ]
        )
        == 0
    )
    launch = validate_creative_code_repair_launch_packet(
        read_json_object(review_root / "launch.json")
    )
    assert launch["target_pr1_specification"]["allowed"] is True

    assert disposition_cli.main(["summarize", "--disposition-packet", str(disposition_path)]) == 0
    captured = capsys.readouterr()
    assert "Creative-Code Review Disposition Summary" in captured.out
    assert "Repair candidates: 1" in captured.out

    assert (
        disposition_cli.main(
            ["summarize", "--disposition-packet", str(disposition_path), "--output", "summary.md"]
        )
        == 0
    )
    assert (
        (review_root / "summary.md")
        .read_text(encoding="utf-8")
        .startswith("# Creative-Code Review Disposition Summary")
    )


def test_summary_output_rejects_existing_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink support is required for this path guard test")

    review_root = _configure_cli_root(monkeypatch, tmp_path)
    review_root.mkdir(parents=True)
    packet = build_creative_code_review_disposition_packet(
        feedback_records=[_record()],
        source_context=_source_context(),
        expected_head_sha="a" * 40,
        actual_head_sha="a" * 40,
    )
    packet_path = review_root / "packet.json"
    _write_json(packet_path, packet)
    outside_target = tmp_path / "outside.md"
    outside_target.write_text("outside stays unchanged\n", encoding="utf-8")
    try:
        (review_root / "summary.md").symlink_to(outside_target)
    except OSError as exc:
        pytest.skip(f"symlink setup failed: {exc}")

    assert (
        disposition_cli.main(
            ["summarize", "--disposition-packet", str(packet_path), "--output", "summary.md"]
        )
        == 1
    )
    assert outside_target.read_text(encoding="utf-8") == "outside stays unchanged\n"


def test_github_fixture_collects_sanitized_feedback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    review_root = _configure_cli_root(monkeypatch, tmp_path)
    fixture_path = tmp_path / "github_fixture.json"
    _write_json(
        fixture_path,
        {
            "head_sha": "a" * 40,
            "issue_comments": [],
            "pr_number": 2045,
            "repository": "Katsiarynakavaleuskaya/PulsePlate",
            "review_comments": [
                {
                    "body_excerpt_sanitized": "coverage guard failed in PR-5 fixture",
                    "feedback_kind": "review_thread",
                    "html_url": (
                        "https://github.com/Katsiarynakavaleuskaya/PulsePlate/"
                        "pull/2045#discussion_r2"
                    ),
                    "id": 2,
                    "line": 55,
                    "path": "tests/test_creative_code_review_disposition.py",
                    "severity": "medium",
                    "side": "RIGHT",
                }
            ],
            "reviews": [],
        },
    )

    assert (
        disposition_cli.main(
            ["collect", "--github-fixture", str(fixture_path), "--output", "github.json"]
        )
        == 0
    )
    collection = read_json_object(review_root / "github.json")
    assert collection["feedback_records"][0]["sanitized_excerpt"]["text"] == (
        "coverage guard failed in PR-5 fixture"
    )


@pytest.mark.parametrize(
    "raw_field",
    ["raw_body", "body", "body_text", "body_html", "body_markdown"],
)
def test_github_fixture_rejects_raw_body_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    raw_field: str,
) -> None:
    _configure_cli_root(monkeypatch, tmp_path)
    fixture_path = tmp_path / "github_fixture.json"
    _write_json(
        fixture_path,
        {
            "head_sha": "a" * 40,
            "issue_comments": [],
            "pr_number": 2045,
            "repository": "Katsiarynakavaleuskaya/PulsePlate",
            "review_comments": [
                {
                    "body_excerpt_sanitized": "coverage guard failed in PR-5 fixture",
                    "feedback_kind": "review_thread",
                    "id": 2,
                    raw_field: "raw review body is forbidden",
                }
            ],
            "reviews": [],
        },
    )

    assert disposition_cli.main(["collect", "--github-fixture", str(fixture_path)]) == 1


def test_github_fixture_requires_explicit_sanitized_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_cli_root(monkeypatch, tmp_path)
    fixture_path = tmp_path / "github_fixture.json"
    _write_json(
        fixture_path,
        {
            "head_sha": "a" * 40,
            "issue_comments": [],
            "pr_number": 2045,
            "repository": "Katsiarynakavaleuskaya/PulsePlate",
            "review_comments": [{"feedback_kind": "review_thread", "id": 2}],
            "reviews": [],
        },
    )

    assert disposition_cli.main(["collect", "--github-fixture", str(fixture_path)]) == 1


def test_github_fixture_summary_sanitized_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    review_root = _configure_cli_root(monkeypatch, tmp_path)
    fixture_path = tmp_path / "github_fixture.json"
    _write_json(
        fixture_path,
        {
            "head_sha": "a" * 40,
            "issue_comments": [
                {
                    "feedback_kind": "bot_comment",
                    "html_url": (
                        "https://github.com/Katsiarynakavaleuskaya/PulsePlate/"
                        "issues/2045#issuecomment-123"
                    ),
                    "id": 3,
                    "severity": "low",
                    "summary_sanitized": "docs wording should mention PR-5 boundary",
                }
            ],
            "pr_number": 2045,
            "repository": "Katsiarynakavaleuskaya/PulsePlate",
            "review_comments": [],
            "reviews": [],
        },
    )

    assert (
        disposition_cli.main(
            ["collect", "--github-fixture", str(fixture_path), "--output", "summary.json"]
        )
        == 0
    )
    collection = read_json_object(review_root / "summary.json")
    assert collection["feedback_records"][0]["sanitized_excerpt"]["text"] == (
        "docs wording should mention PR-5 boundary"
    )
    assert collection["feedback_records"][0]["source"]["source_url"] == (
        "https://github.com/Katsiarynakavaleuskaya/PulsePlate/issues/2045#issuecomment-123"
    )


def test_github_fixture_rejects_legacy_plain_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_cli_root(monkeypatch, tmp_path)
    fixture_path = tmp_path / "github_fixture.json"
    _write_json(
        fixture_path,
        {
            "head_sha": "a" * 40,
            "issue_comments": [{"feedback_kind": "bot_comment", "id": 3, "summary": "ambiguous"}],
            "pr_number": 2045,
            "repository": "Katsiarynakavaleuskaya/PulsePlate",
            "review_comments": [],
            "reviews": [],
        },
    )

    assert disposition_cli.main(["collect", "--github-fixture", str(fixture_path)]) == 1


def test_github_fixture_rejects_raw_body_even_with_valid_excerpt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_cli_root(monkeypatch, tmp_path)
    fixture_path = tmp_path / "github_fixture.json"
    _write_json(
        fixture_path,
        {
            "head_sha": "a" * 40,
            "issue_comments": [],
            "pr_number": 2045,
            "repository": "Katsiarynakavaleuskaya/PulsePlate",
            "review_comments": [
                {
                    "body": "raw review body is forbidden",
                    "body_excerpt_sanitized": "safe excerpt",
                    "feedback_kind": "review_thread",
                    "id": 2,
                }
            ],
            "reviews": [],
        },
    )

    assert disposition_cli.main(["collect", "--github-fixture", str(fixture_path)]) == 1


def test_github_fixture_rejects_raw_body_field_in_existing_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_cli_root(monkeypatch, tmp_path)
    fixture_path = tmp_path / "github_fixture.json"
    _write_json(
        fixture_path,
        {
            "head_sha": "a" * 40,
            "issue_comments": [],
            "pr_number": 2045,
            "repository": "Katsiarynakavaleuskaya/PulsePlate",
            "review_comments": [
                {
                    "body_excerpt_sanitized": "coverage guard failed in PR-5 fixture",
                    "feedback_kind": "review_thread",
                    "id": 2,
                }
            ],
            "reviews": [],
        },
    )

    raw_fixture = tmp_path / "github_raw_fixture.json"
    raw_payload = dict(read_json_object(fixture_path))
    raw_payload["review_comments"] = [dict(raw_payload["review_comments"][0])]
    raw_payload["review_comments"][0]["raw_body"] = "raw review body is forbidden"
    _write_json(raw_fixture, raw_payload)
    assert disposition_cli.main(["collect", "--github-fixture", str(raw_fixture)]) == 1


def test_classification_is_deterministic_for_candidate_dispositions() -> None:
    examples = {
        "simple_fix": _record(excerpt="docs wording should mention the local CLI"),
        "creative_repair_candidate": _record(excerpt="test fail in contract validator"),
        "not_a_bug_candidate": _record(excerpt="not a bug because contract already covers it"),
        "defer_candidate": _record(excerpt="defer this idea to the backlog"),
        "out_of_scope": _record(excerpt="style nit outside this PR surface"),
        "security_blocker": _record(excerpt="do not resolve review thread from this lane"),
    }

    assert {
        expected: classify_feedback_record(record)["classification"]["candidate_disposition"]
        for expected, record in examples.items()
    } == {
        "simple_fix": "simple_fix",
        "creative_repair_candidate": "creative_repair_candidate",
        "not_a_bug_candidate": "not_a_bug_candidate",
        "defer_candidate": "defer_candidate",
        "out_of_scope": "out_of_scope",
        "security_blocker": "security_blocker",
    }


def test_cli_contains_no_github_mutation_or_review_resolution_commands() -> None:
    source = CLI_SOURCE.read_text(encoding="utf-8")
    forbidden_fragments = (
        "gh pr create",
        "gh pr edit",
        "gh pr ready",
        "gh pr review",
        "gh pr merge",
        "gh pr close",
        "gh api -X POST",
        "gh api -X PATCH",
        "gh api -X PUT",
        "gh api -X DELETE",
        "resolveReviewThread",
        "mutation {",
        "createPullRequest",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source

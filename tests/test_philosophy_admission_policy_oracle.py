from __future__ import annotations

import json
from pathlib import Path

from pytest import CaptureFixture

import scripts.ci.check_docs_phase1_gates as docs_phase1
from scripts.ci.check_semantic_cache_gate import (
    compile_philosophy_admission_policy_patterns,
    main as semantic_cache_gate_main,
    render_philosophy_admission_oracle_fixture,
    validate_philosophy_admission_oracle_fixture,
    validate_philosophy_semantic_cache_admission_downstream_text,
    validate_philosophy_semantic_cache_admission_policy,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json"
)
POLICY_SCHEMA = POLICY.with_suffix(".schema.json")
ORACLE_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "orchestration" / "philosophy_admission_claim_oracle.json"
)
REL_POLICY = "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json"
REL_POLICY_SCHEMA = (
    "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json"
)
REL_ORACLE_FIXTURE = "tests/fixtures/orchestration/philosophy_admission_claim_oracle.json"


def _policy_text() -> str:
    return POLICY.read_text(encoding="utf-8")


def _policy() -> dict[str, object]:
    policy = json.loads(_policy_text())
    assert isinstance(policy, dict)
    return policy


def _oracle_fixture() -> dict[str, object]:
    fixture = json.loads(ORACLE_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(fixture, dict)
    return fixture


def _assert_no_regex_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            assert "regex" not in key.lower()
            _assert_no_regex_keys(nested_value)
    elif isinstance(value, list):
        for item in value:
            _assert_no_regex_keys(item)


def test_policy_schema_and_oracle_fixture_are_current() -> None:
    errors = validate_philosophy_semantic_cache_admission_policy(
        policy_text=_policy_text(),
        schema_text=POLICY_SCHEMA.read_text(encoding="utf-8"),
    )
    assert errors == []

    fixture_errors = validate_philosophy_admission_oracle_fixture(
        policy_text=_policy_text(),
        fixture_text=ORACLE_FIXTURE.read_text(encoding="utf-8"),
    )
    assert fixture_errors == []


def test_oracle_render_is_byte_stable() -> None:
    rendered, errors = render_philosophy_admission_oracle_fixture(_policy_text())

    assert errors == []
    assert rendered == ORACLE_FIXTURE.read_text(encoding="utf-8")


def test_policy_contains_no_json_regex_or_runtime_activation() -> None:
    policy = _policy()

    _assert_no_regex_keys(policy)
    assert policy["gate_status"] == "closed"
    assert policy["runtime_allowed"] is False
    assert policy["implementation_allowed"] is False


def test_policy_generated_patterns_cover_forbidden_oracle_cases() -> None:
    policy = _policy()
    patterns = compile_philosophy_admission_policy_patterns(policy)
    fixture = _oracle_fixture()
    cases = fixture["cases"]
    assert isinstance(cases, list)

    forbidden_cases = [case for case in cases if case["expected"] == "forbidden"]
    allowed_cases = [case for case in cases if case["expected"] == "allowed"]
    assert forbidden_cases
    assert allowed_cases
    assert len(patterns) == len(forbidden_cases)


def test_oracle_cases_match_downstream_checker_behavior() -> None:
    fixture = _oracle_fixture()
    cases = fixture["cases"]
    assert isinstance(cases, list)
    misses: list[tuple[str, str, list[str]]] = []
    false_hits: list[tuple[str, str, list[str]]] = []

    for case in cases:
        assert isinstance(case, dict)
        claim = case["claim"]
        expected = case["expected"]
        family = case["claim_family"]
        detector_label = case["expected_detector_label"]
        assert isinstance(claim, str)
        assert isinstance(family, str)
        assert isinstance(detector_label, str)
        errors = validate_philosophy_semantic_cache_admission_downstream_text(claim)
        if expected == "forbidden":
            if not any(detector_label in error or family in error for error in errors):
                misses.append((claim, detector_label, errors))
        else:
            if any(detector_label in error or family in error for error in errors):
                false_hits.append((claim, detector_label, errors))

    assert misses == []
    assert false_hits == []


def test_post_open_qa_modal_temporal_false_green_regressions_are_blocked() -> None:
    claims = [
        "PR-2 may open the semantic-cache gate.",
        "The claim-family oracle may enable the global gate.",
        "The admission policy may write cache entries.",
        "PR-2 has to authorize backend selection.",
        "Billing truth became cache eligible for semantic-cache admission.",
        "PR-2 approves Redis rollout for philosophy admission.",
        "PR-2 approves GPTCache rollout for philosophy admission.",
        "The admission policy approves provider-backed cache runtime.",
    ]

    for claim in claims:
        errors = validate_philosophy_semantic_cache_admission_downstream_text(claim)
        assert errors, claim


def test_oracle_fixture_drift_is_rejected() -> None:
    fixture = _oracle_fixture()
    cases = fixture["cases"]
    assert isinstance(cases, list)
    fixture["cases"] = cases[1:]

    errors = validate_philosophy_admission_oracle_fixture(
        policy_text=_policy_text(),
        fixture_text=json.dumps(fixture, indent=2) + "\n",
    )

    assert (
        "philosophy admission oracle fixture drift: regenerate from "
        "PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json"
    ) in errors


def test_policy_duplicate_keys_are_rejected() -> None:
    policy_text = _policy_text().replace(
        '  "gate_status": "closed",',
        '  "gate_status": "open",\n  "gate_status": "closed",',
        1,
    )

    errors = validate_philosophy_semantic_cache_admission_policy(
        policy_text=policy_text,
        schema_text=POLICY_SCHEMA.read_text(encoding="utf-8"),
    )

    assert "philosophy admission policy duplicate key: gate_status" in errors


def test_oracle_write_rejects_paths_outside_fixture_root(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    outside_fixture_root = tmp_path / "philosophy_admission_claim_oracle.json"

    exit_code = semantic_cache_gate_main(
        [
            "--write-philosophy-admission-oracle",
            "--philosophy-admission-oracle",
            str(outside_fixture_root),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert not outside_fixture_root.exists()
    assert "philosophy admission oracle write path must stay" in captured.err


def test_phase1_docs_gate_wires_policy_schema_and_oracle() -> None:
    errors = docs_phase1.check_docs_phase1_guards(
        markdown_files=[REL_POLICY, REL_POLICY_SCHEMA, REL_ORACLE_FIXTURE]
    )

    assert errors == []

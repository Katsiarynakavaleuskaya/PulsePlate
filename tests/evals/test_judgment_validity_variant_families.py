"""Tests for judgment validity variant fixture families.

Validates that the judgment eval validity variant fixture set:
- contains all three families (canonical, invariance, mutation)
- has exactly one canonical row per canonical_id group
- invariance rows preserve the canonical decision (same_decision)
- mutation rows demonstrate controlled score/decision drop
- validity report has non-trivial metrics
- output is deterministic across repeated runs
- fixtures contain no LLM-generated or provider/network metadata
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.evals.eval_validity_contract import (
    VARIANT_FAMILIES,
    build_validity_report,
    validate_eval_outcome_record,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANT_FIXTURE_PATH = (
    _REPO_ROOT / "data" / "evals" / "pulseplate_judgment_eval_validity_variants.jsonl"
)


def _load_fixture() -> list[dict[str, Any]]:
    """Load and parse variant fixture rows."""
    assert VARIANT_FIXTURE_PATH.exists(), f"Missing fixture: {VARIANT_FIXTURE_PATH}"
    rows: list[dict[str, Any]] = []
    for line in VARIANT_FIXTURE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_validated_outcomes() -> list[dict[str, Any]]:
    """Load fixture rows as validated EvalOutcomeRecords."""
    rows = _load_fixture()
    return [validate_eval_outcome_record(r) for r in rows]


# ------------------------------------------------------------------
# Fixture file basics
# ------------------------------------------------------------------


def test_judgment_variant_fixture_file_exists() -> None:
    assert VARIANT_FIXTURE_PATH.exists(), f"Missing: {VARIANT_FIXTURE_PATH}"


def test_judgment_variant_fixture_parses() -> None:
    rows = _load_fixture()
    assert len(rows) > 0, "Fixture file is empty"
    for i, row in enumerate(rows):
        assert isinstance(row, dict), f"Row {i} is not a dict"
        assert "canonical_id" in row, f"Row {i} missing canonical_id"
        assert "variant_family" in row, f"Row {i} missing variant_family"


def test_judgment_variant_fixture_has_required_families() -> None:
    rows = _load_fixture()
    families = {r["variant_family"] for r in rows}
    for fam in VARIANT_FAMILIES:
        assert fam in families, f"Missing variant_family: {fam}"


# ------------------------------------------------------------------
# Uniqueness and canonical group structure
# ------------------------------------------------------------------


def test_all_variant_ids_are_unique() -> None:
    rows = _load_fixture()
    ids = [r["variant_id"] for r in rows]
    duplicates = [vid for vid in ids if ids.count(vid) > 1]
    assert not duplicates, f"Duplicate variant_ids: {sorted(set(duplicates))}"


def test_each_canonical_group_has_exactly_one_canonical_row() -> None:
    rows = _load_fixture()
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r["canonical_id"], []).append(r)

    assert len(groups) >= 3, "Need at least 3 canonical groups"
    for cid, members in groups.items():
        canonical_rows = [m for m in members if m["variant_family"] == "canonical"]
        assert (
            len(canonical_rows) == 1
        ), f"canonical_id={cid} has {len(canonical_rows)} canonical rows, expected 1"


# ------------------------------------------------------------------
# Invariance: same_decision relation
# ------------------------------------------------------------------


def test_invariance_rows_preserve_expected_same_decision_relation() -> None:
    rows = _load_fixture()
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r["canonical_id"], []).append(r)

    invariance_checked = 0
    for cid, members in groups.items():
        canonical = [m for m in members if m["variant_family"] == "canonical"]
        if not canonical:
            continue
        canonical_decision = canonical[0]["decision"]
        for m in members:
            if m["variant_family"] == "invariance":
                assert m["decision"] == canonical_decision, (
                    f"Invariance row {m['variant_id']} decision={m['decision']!r} "
                    f"differs from canonical decision={canonical_decision!r}"
                )
                invariance_checked += 1

    assert invariance_checked > 0, "No invariance rows found to check"


# ------------------------------------------------------------------
# Mutation: controlled drop
# ------------------------------------------------------------------


def test_mutation_rows_have_controlled_drop_or_expected_instability() -> None:
    rows = _load_fixture()
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r["canonical_id"], []).append(r)

    mutation_checked = 0
    for cid, members in groups.items():
        canonical = [m for m in members if m["variant_family"] == "canonical"]
        if not canonical:
            continue
        canonical_score = canonical[0]["score"]
        for m in members:
            if m["variant_family"] == "mutation":
                # Mutation rows should have lower or equal score vs canonical
                assert m["score"] <= canonical_score, (
                    f"Mutation row {m['variant_id']} score={m['score']} "
                    f"exceeds canonical score={canonical_score}"
                )
                mutation_checked += 1

    assert mutation_checked > 0, "No mutation rows found to check"


# ------------------------------------------------------------------
# Canonical-fail invariance: fail -> fail stability
# ------------------------------------------------------------------


def test_judgment_variant_fixture_has_canonical_fail_group() -> None:
    """At least one canonical row must have decision == 'fail' (canonical-fail group)."""
    rows = _load_fixture()
    canonical_rows = [r for r in rows if r["variant_family"] == "canonical"]
    canonical_fail_rows = [r for r in canonical_rows if r["decision"] == "fail"]
    assert len(canonical_fail_rows) >= 1, (
        "No canonical-fail rows found. " "At least one canonical row must have decision='fail'."
    )
    for r in canonical_fail_rows:
        assert (
            "canonical_fail" in r["slice_tags"]
        ), f"Canonical-fail row {r['variant_id']} missing 'canonical_fail' slice tag"
        assert (
            r["passed"] is False
        ), f"Canonical-fail row {r['variant_id']} must have passed=False, got {r['passed']}"


def test_judgment_canonical_fail_invariance_preserves_failure_decision() -> None:
    """Invariance rows in canonical-fail groups must preserve the failing decision."""
    rows = _load_fixture()
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r["canonical_id"], []).append(r)

    fail_invariance_checked = 0
    for cid, members in groups.items():
        canonical = [m for m in members if m["variant_family"] == "canonical"]
        if not canonical:
            continue
        canonical_decision = canonical[0]["decision"]
        if canonical_decision != "fail":
            continue  # only check canonical-fail groups
        canonical_passed = canonical[0]["passed"]
        assert (
            canonical_passed is False
        ), f"Canonical-fail group {cid} must have canonical passed=False, got {canonical_passed}"
        for m in members:
            if m["variant_family"] == "invariance":
                assert m["decision"] == canonical_decision, (
                    f"Canonical-fail invariance row {m['variant_id']} "
                    f"decision={m['decision']!r} differs from canonical "
                    f"decision={canonical_decision!r}"
                )
                assert m["passed"] == canonical_passed, (
                    f"Canonical-fail invariance row {m['variant_id']} "
                    f"passed={m['passed']} differs from canonical "
                    f"passed={canonical_passed}"
                )
                fail_invariance_checked += 1

    assert fail_invariance_checked > 0, "No fail-invariance rows found in canonical-fail groups"


def test_judgment_canonical_fail_group_does_not_leak_unsupported_fields() -> None:
    """Canonical-fail rows must not introduce unsupported fixture fields."""
    rows = _load_fixture()
    allowed_keys = {
        "canonical_id",
        "variant_id",
        "variant_family",
        "transform_type",
        "passed",
        "score",
        "decision",
        "slice_tags",
    }
    for r in rows:
        if "canonical_fail" in r.get("slice_tags", []):
            extra = set(r.keys()) - allowed_keys
            assert (
                not extra
            ), f"Canonical-fail row {r['variant_id']} has unsupported fields: {extra}"


# ------------------------------------------------------------------
# Validity report metrics
# ------------------------------------------------------------------


def test_judgment_variant_report_has_non_empty_slice_support() -> None:
    outcomes = _load_validated_outcomes()
    report = build_validity_report(outcomes)
    assert isinstance(report["slice_support"], dict)
    assert len(report["slice_support"]) > 0, "slice_support is empty"


def test_judgment_variant_report_has_non_trivial_mutation_drop() -> None:
    outcomes = _load_validated_outcomes()
    report = build_validity_report(outcomes)
    mutation_drop = report["mutation_drop"]
    assert isinstance(mutation_drop, dict)
    overall = mutation_drop.get("overall")
    assert overall is not None, "mutation_drop.overall is missing"
    assert overall > 0.0, f"mutation_drop.overall={overall} is not positive (trivial)"


def test_judgment_variant_report_has_meaningful_invariance_score() -> None:
    outcomes = _load_validated_outcomes()
    report = build_validity_report(outcomes)
    score = report["invariance_score"]
    assert score > 0.0, f"invariance_score={score} is zero (canonical-only coverage)"
    assert score <= 1.0, f"invariance_score={score} exceeds 1.0"


def test_judgment_variant_report_has_deterministic_unstable_items() -> None:
    outcomes = _load_validated_outcomes()
    report_a = build_validity_report(outcomes)
    report_b = build_validity_report(outcomes)
    assert (
        report_a["unstable_items"] == report_b["unstable_items"]
    ), "unstable_items differs across two runs"
    # At least some items should be unstable (mutation rows change decisions)
    assert len(report_a["unstable_items"]) > 0, "No unstable items detected"


def test_judgment_variant_report_is_deterministic_across_two_runs() -> None:
    outcomes = _load_validated_outcomes()
    report_a = build_validity_report(outcomes)
    report_b = build_validity_report(outcomes)
    # Compare JSON serialization for full determinism
    json_a = json.dumps(report_a, sort_keys=True)
    json_b = json.dumps(report_b, sort_keys=True)
    assert json_a == json_b, "Validity report is not deterministic"


# ------------------------------------------------------------------
# Forbidden content guards
# ------------------------------------------------------------------

_LLM_METADATA_PATTERNS = [
    "generated_by_llm",
    "generated_by_model",
    "llm_provider",
    "model_name",
    "model_version",
    "openai",
    "anthropic",
    "claude",
    "gpt-4",
    "gpt-3",
]

_NETWORK_PROVIDER_PATTERNS = [
    "api_key",
    "secret",
    "token",
    "password",
    "http://",
    "https://",
    "email",
]


def test_judgment_variant_fixtures_do_not_contain_llm_generated_metadata() -> None:
    content = VARIANT_FIXTURE_PATH.read_text(encoding="utf-8").lower()
    for pattern in _LLM_METADATA_PATTERNS:
        assert pattern not in content, f"Fixture contains LLM metadata pattern: {pattern!r}"


def test_judgment_variant_fixtures_do_not_contain_network_or_provider_fields() -> None:
    content = VARIANT_FIXTURE_PATH.read_text(encoding="utf-8").lower()
    for pattern in _NETWORK_PROVIDER_PATTERNS:
        assert pattern not in content, f"Fixture contains network/provider pattern: {pattern!r}"

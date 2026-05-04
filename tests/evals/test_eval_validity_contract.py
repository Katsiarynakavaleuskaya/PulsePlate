"""Deterministic tests for the eval validity contract module.

RU: Тесты для контракта eval validity — парсеры, метрики, группировка.
EN: Tests for eval validity contract — parsers, metrics, grouping.

No network.  No model calls.  Pure offline deterministic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.evals.eval_validity_contract import (
    EvalOutcomeRecord,
    build_validity_report,
    compute_invariance_score,
    compute_item_instability_index,
    compute_mutation_drop,
    compute_worst_case_error_rate,
    group_outcomes_by_canonical_id,
    validate_eval_outcome_record,
    validate_eval_variant_record,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_variant_raw(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "canonical_id": "item_001",
        "variant_id": "item_001_canonical",
        "variant_family": "canonical",
        "transform_type": "none",
        "expected_relation": "same_decision",
        "slice_tags": ["rag"],
        "input_payload": {"query": "test"},
    }
    base.update(overrides)
    return base


def _make_outcome_raw(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "canonical_id": "item_001",
        "variant_id": "item_001_canonical",
        "variant_family": "canonical",
        "transform_type": "none",
        "passed": True,
        "score": 1.0,
        "decision": "pass",
        "slice_tags": ["rag"],
    }
    base.update(overrides)
    return base


def _sample_outcomes() -> list[EvalOutcomeRecord]:
    """Minimal multi-item set with invariance and mutation variants."""
    return [
        validate_eval_outcome_record(
            _make_outcome_raw(
                canonical_id="A",
                variant_id="A_canon",
                variant_family="canonical",
                score=1.0,
                decision="pass",
            )
        ),
        validate_eval_outcome_record(
            _make_outcome_raw(
                canonical_id="A",
                variant_id="A_fmt",
                variant_family="invariance",
                transform_type="format",
                score=1.0,
                decision="pass",
            )
        ),
        validate_eval_outcome_record(
            _make_outcome_raw(
                canonical_id="A",
                variant_id="A_mut",
                variant_family="mutation",
                transform_type="missing_evidence",
                score=0.6,
                decision="pass",
                passed=True,
            )
        ),
        validate_eval_outcome_record(
            _make_outcome_raw(
                canonical_id="B",
                variant_id="B_canon",
                variant_family="canonical",
                score=1.0,
                decision="pass",
            )
        ),
        validate_eval_outcome_record(
            _make_outcome_raw(
                canonical_id="B",
                variant_id="B_para",
                variant_family="invariance",
                transform_type="paraphrase_curated",
                score=0.3,
                decision="fail",
                passed=False,
            )
        ),
    ]


# ---------------------------------------------------------------------------
# Variant record validation
# ---------------------------------------------------------------------------


class TestValidateEvalVariantRecord:

    def test_valid_record(self) -> None:
        raw = _make_variant_raw()
        rec = validate_eval_variant_record(raw)
        assert rec["canonical_id"] == "item_001"
        assert rec["variant_family"] == "canonical"

    def test_rejects_invalid_family(self) -> None:
        raw = _make_variant_raw(variant_family="bogus")
        with pytest.raises(ValueError, match="Invalid variant_family"):
            validate_eval_variant_record(raw)

    def test_rejects_missing_key(self) -> None:
        raw = _make_variant_raw()
        del raw["canonical_id"]
        with pytest.raises(ValueError, match="missing keys"):
            validate_eval_variant_record(raw)

    def test_rejects_invalid_expected_relation(self) -> None:
        raw = _make_variant_raw(expected_relation="wrong")
        with pytest.raises(ValueError, match="Invalid expected_relation"):
            validate_eval_variant_record(raw)

    def test_rejects_non_string_identifiers_and_transform_type(self) -> None:
        raw = _make_variant_raw(canonical_id=["item_001"], variant_id={"id": "v"}, transform_type=123)
        with pytest.raises(ValueError, match="EvalVariantRecord.canonical_id must be str"):
            validate_eval_variant_record(raw)

    def test_rejects_invalid_slice_tags_and_input_payload_types(self) -> None:
        raw = _make_variant_raw(slice_tags="rag", input_payload=["x"])
        with pytest.raises(ValueError, match="EvalVariantRecord.slice_tags must be list\[str\]"):
            validate_eval_variant_record(raw)


# ---------------------------------------------------------------------------
# Outcome record validation
# ---------------------------------------------------------------------------


class TestValidateEvalOutcomeRecord:

    def test_valid_record(self) -> None:
        raw = _make_outcome_raw()
        rec = validate_eval_outcome_record(raw)
        assert rec["passed"] is True
        assert rec["score"] == 1.0

    def test_rejects_invalid_family(self) -> None:
        raw = _make_outcome_raw(variant_family="bogus")
        with pytest.raises(ValueError, match="Invalid variant_family"):
            validate_eval_outcome_record(raw)

    def test_rejects_missing_key(self) -> None:
        raw = _make_outcome_raw()
        del raw["score"]
        with pytest.raises(ValueError, match="missing keys"):
            validate_eval_outcome_record(raw)

    def test_rejects_non_bool_passed(self) -> None:
        raw = _make_outcome_raw(passed="yes")
        with pytest.raises(ValueError, match="must be bool"):
            validate_eval_outcome_record(raw)

    def test_rejects_non_numeric_score(self) -> None:
        raw = _make_outcome_raw(score="high")
        with pytest.raises(ValueError, match="must be numeric"):
            validate_eval_outcome_record(raw)

    def test_rejects_bool_score(self) -> None:
        raw = _make_outcome_raw(score=True)
        with pytest.raises(ValueError, match="got bool"):
            validate_eval_outcome_record(raw)

    def test_rejects_nan_score(self) -> None:
        raw = _make_outcome_raw(score=float("nan"))
        with pytest.raises(ValueError, match="must be finite"):
            validate_eval_outcome_record(raw)

    def test_rejects_infinity_score(self) -> None:
        raw = _make_outcome_raw(score=float("inf"))
        with pytest.raises(ValueError, match="must be finite"):
            validate_eval_outcome_record(raw)

    def test_rejects_neg_infinity_score(self) -> None:
        raw = _make_outcome_raw(score=float("-inf"))
        with pytest.raises(ValueError, match="must be finite"):
            validate_eval_outcome_record(raw)

    def test_rejects_non_string_fields(self) -> None:
        raw = _make_outcome_raw(canonical_id=["item_001"], transform_type={"kind": "none"}, decision=["pass"])
        with pytest.raises(ValueError, match="EvalOutcomeRecord.canonical_id must be str"):
            validate_eval_outcome_record(raw)

    def test_rejects_invalid_slice_tags_type_with_value_error(self) -> None:
        raw = _make_outcome_raw(slice_tags="rag")
        with pytest.raises(ValueError, match="EvalOutcomeRecord.slice_tags must be list\[str\]"):
            validate_eval_outcome_record(raw)


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


class TestGroupOutcomes:

    def test_groups_by_canonical_id(self) -> None:
        outcomes = _sample_outcomes()
        groups = group_outcomes_by_canonical_id(outcomes)
        assert set(groups.keys()) == {"A", "B"}
        assert len(groups["A"]) == 3
        assert len(groups["B"]) == 2

    def test_empty_input(self) -> None:
        assert group_outcomes_by_canonical_id([]) == {}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestInvarianceScore:

    def test_with_sample(self) -> None:
        outcomes = _sample_outcomes()
        score = compute_invariance_score(outcomes)
        # A_fmt agrees (pass==pass), B_para disagrees (fail!=pass)
        assert score == 0.5

    def test_no_invariance_rows(self) -> None:
        outcomes = [
            validate_eval_outcome_record(_make_outcome_raw()),
        ]
        assert compute_invariance_score(outcomes) == 0.0


class TestMutationDrop:

    def test_with_sample(self) -> None:
        outcomes = _sample_outcomes()
        result = compute_mutation_drop(outcomes)
        assert result["overall"] == 0.4  # 1.0 - 0.6
        assert "missing_evidence" in result["by_transform"]

    def test_no_mutation_rows(self) -> None:
        outcomes = [
            validate_eval_outcome_record(_make_outcome_raw()),
        ]
        result = compute_mutation_drop(outcomes)
        assert result["overall"] == 0.0
        assert result["by_transform"] == {}

    def test_rejects_mutation_without_canonical_baseline(self) -> None:
        """Mutation row with no matching canonical row must raise."""
        outcomes = [
            validate_eval_outcome_record(
                _make_outcome_raw(
                    canonical_id="orphan",
                    variant_id="orphan_mut",
                    variant_family="mutation",
                    transform_type="missing_evidence",
                    score=0.5,
                )
            ),
        ]
        with pytest.raises(ValueError, match="no canonical baseline"):
            compute_mutation_drop(outcomes)


class TestWorstCaseErrorRate:

    def test_with_sample(self) -> None:
        outcomes = _sample_outcomes()
        rate = compute_worst_case_error_rate(outcomes)
        # Group B: 1 fail out of 2 = 0.5
        assert rate == 0.5

    def test_empty(self) -> None:
        assert compute_worst_case_error_rate([]) == 0.0


class TestItemInstabilityIndex:

    def test_with_sample(self) -> None:
        outcomes = _sample_outcomes()
        idx = compute_item_instability_index(outcomes)
        # A is stable (all pass), B is unstable (para=fail)
        assert idx == 0.5

    def test_empty(self) -> None:
        assert compute_item_instability_index([]) == 0.0


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------


class TestBuildValidityReport:

    def test_report_shape(self) -> None:
        outcomes = _sample_outcomes()
        report = build_validity_report(outcomes)
        assert "schema_version" in report
        assert "invariance_score" in report
        assert "mutation_drop" in report
        assert "worst_case_error_rate" in report
        assert "item_instability_index" in report
        assert "slice_support" in report
        assert "unstable_items" in report
        assert "slice_breakdown" in report

    def test_unstable_items_deterministic(self) -> None:
        outcomes = _sample_outcomes()
        r1 = build_validity_report(outcomes)
        r2 = build_validity_report(outcomes)
        assert r1["unstable_items"] == r2["unstable_items"]
        assert r1["unstable_items"] == ["B"]

    def test_empty_outcomes(self) -> None:
        report = build_validity_report([])
        assert report["invariance_score"] == 0.0
        assert report["worst_case_error_rate"] == 0.0
        assert report["unstable_items"] == []


# ---------------------------------------------------------------------------
# Security: no network imports in contract module
# ---------------------------------------------------------------------------


class TestNoNetworkImports:

    def test_contract_module_has_no_network_deps(self) -> None:
        """Ensure eval_validity_contract does not import network libs."""
        import scripts.evals.eval_validity_contract as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        for lib in ("requests", "httpx", "urllib.request", "aiohttp"):
            assert f"import {lib}" not in source, f"eval_validity_contract.py must not import {lib}"

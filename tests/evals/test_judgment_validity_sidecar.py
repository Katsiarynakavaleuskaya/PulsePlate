"""Tests for the judgment replay validity sidecar adapter.

Verifies that FitChef judgment replay results are correctly mapped to
validity-compatible EvalOutcomeRecord rows and that sidecar artifacts
are written deterministically.

Hard rules:
- No network calls / no model calls.
- Sidecar does not change promote/defer/discard decisions.
- Sidecar is informational / measurement-validity layer only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.evals.judgment_validity as judgment_validity
from scripts.evals.judgment_validity import (
    JUDGMENT_DECISION_SCORES,
    JUDGMENT_VALIDITY_ITEMS_FILENAME,
    JUDGMENT_VALIDITY_REPORT_FILENAME,
    result_to_eval_outcome,
    results_to_eval_outcomes,
    write_judgment_validity_sidecar,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_PROMOTE_RESULT: dict[str, object] = {
    "case_id": "case_promote_001",
    "decision": "promote",
    "boundary_class": "wellness_coaching",
    "hard_fail_reasons": [],
    "scores": {"personalization_relevance": 4, "emotional_attunement": 4},
}

_DEFER_RESULT: dict[str, object] = {
    "case_id": "case_defer_002",
    "decision": "defer",
    "boundary_class": "wellness_coaching",
    "hard_fail_reasons": [],
    "scores": {"personalization_relevance": 3, "emotional_attunement": 3},
}

_DISCARD_RESULT: dict[str, object] = {
    "case_id": "case_discard_003",
    "decision": "discard",
    "boundary_class": "high_distress_boundary",
    "hard_fail_reasons": ["forbidden_pattern:skip_the_next_meal"],
    "scores": {"personalization_relevance": 1, "emotional_attunement": 1},
}

_ALL_RESULTS: list[dict[str, object]] = [
    _PROMOTE_RESULT,
    _DEFER_RESULT,
    _DISCARD_RESULT,
]


# ---------------------------------------------------------------------------
# Unit tests: result_to_eval_outcome mapping
# ---------------------------------------------------------------------------


class TestResultToEvalOutcome:
    """Verify deterministic mapping from judgment decisions to EvalOutcomeRecord."""

    def test_promote_result(self) -> None:
        rec = result_to_eval_outcome(_PROMOTE_RESULT)

        assert rec["canonical_id"] == "case_promote_001"
        assert rec["variant_id"] == "case_promote_001"
        assert rec["variant_family"] == "canonical"
        assert rec["transform_type"] == "none"
        assert rec["passed"] is True
        assert rec["score"] == 1.0
        assert rec["decision"] == "promote"

    def test_defer_result(self) -> None:
        rec = result_to_eval_outcome(_DEFER_RESULT)

        assert rec["canonical_id"] == "case_defer_002"
        assert rec["passed"] is True
        assert rec["score"] == 0.5
        assert rec["decision"] == "defer"

    def test_discard_result(self) -> None:
        rec = result_to_eval_outcome(_DISCARD_RESULT)

        assert rec["canonical_id"] == "case_discard_003"
        assert rec["passed"] is False
        assert rec["score"] == 0.0
        assert rec["decision"] == "discard"

    def test_slice_tags_include_boundary_class(self) -> None:
        rec = result_to_eval_outcome(_PROMOTE_RESULT)

        assert "judgment" in rec["slice_tags"]
        assert "wellness_coaching" in rec["slice_tags"]

    def test_slice_tags_include_hard_fail_when_present(self) -> None:
        rec = result_to_eval_outcome(_DISCARD_RESULT)

        assert "hard_fail" in rec["slice_tags"]
        assert "high_distress_boundary" in rec["slice_tags"]

    def test_slice_tags_exclude_hard_fail_when_empty(self) -> None:
        rec = result_to_eval_outcome(_PROMOTE_RESULT)

        assert "hard_fail" not in rec["slice_tags"]

    def test_decision_score_constants_cover_all_judgments(self) -> None:
        """Verify the score mapping covers all canonical judgment decisions."""
        assert set(JUDGMENT_DECISION_SCORES.keys()) == {"promote", "defer", "discard"}

    def test_unknown_decision_defaults_to_zero_score(self) -> None:
        """Unknown decisions default to score=0.0 and passed=False."""
        result: dict[str, object] = {
            "case_id": "unknown_decision",
            "decision": "unknown_value",
            "boundary_class": "wellness_coaching",
            "hard_fail_reasons": [],
        }
        rec = result_to_eval_outcome(result)

        assert rec["score"] == 0.0
        assert rec["passed"] is False
        assert rec["decision"] == "unknown_value"


# ---------------------------------------------------------------------------
# Unit tests: batch conversion
# ---------------------------------------------------------------------------


class TestResultsToEvalOutcomes:
    """Verify batch conversion preserves order and count."""

    def test_batch_preserves_insertion_order(self) -> None:
        outcomes = results_to_eval_outcomes(_ALL_RESULTS)

        assert len(outcomes) == 3
        assert outcomes[0]["canonical_id"] == "case_promote_001"
        assert outcomes[1]["canonical_id"] == "case_defer_002"
        assert outcomes[2]["canonical_id"] == "case_discard_003"

    def test_empty_results_returns_empty_list(self) -> None:
        outcomes = results_to_eval_outcomes([])

        assert outcomes == []


# ---------------------------------------------------------------------------
# Integration tests: sidecar writing
# ---------------------------------------------------------------------------


class TestWriteJudgmentValiditySidecar:
    """Verify sidecar file creation, content validity, and determinism."""

    def test_creates_expected_files(self, tmp_path: Path) -> None:
        paths = write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)

        items_path = tmp_path / JUDGMENT_VALIDITY_ITEMS_FILENAME
        report_path = tmp_path / JUDGMENT_VALIDITY_REPORT_FILENAME

        assert items_path.exists()
        assert report_path.exists()
        assert paths["validity_items"] == str(items_path)
        assert paths["validity_report"] == str(report_path)

    def test_jsonl_lines_are_valid_records(self, tmp_path: Path) -> None:
        write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)

        items_path = tmp_path / JUDGMENT_VALIDITY_ITEMS_FILENAME
        lines = items_path.read_text(encoding="utf-8").strip().split("\n")

        assert len(lines) == 3
        for line in lines:
            rec = json.loads(line)
            assert "canonical_id" in rec
            assert "variant_id" in rec
            assert "variant_family" in rec
            assert "passed" in rec
            assert "score" in rec
            assert "decision" in rec
            assert "slice_tags" in rec
            assert isinstance(rec["passed"], bool)
            assert isinstance(rec["score"], (int, float))

    def test_report_has_expected_keys(self, tmp_path: Path) -> None:
        write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)

        report_path = tmp_path / JUDGMENT_VALIDITY_REPORT_FILENAME
        report = json.loads(report_path.read_text(encoding="utf-8"))

        expected_keys = {
            "schema_version",
            "invariance_score",
            "mutation_drop",
            "worst_case_error_rate",
            "item_instability_index",
            "slice_support",
            "unstable_items",
            "slice_breakdown",
        }
        assert expected_keys.issubset(set(report.keys()))
        assert report["schema_version"] == "1.0"

    def test_report_canonical_only_metrics(self, tmp_path: Path) -> None:
        """Canonical-only rows must not be misrepresented as invariance coverage."""
        write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)

        report_path = tmp_path / JUDGMENT_VALIDITY_REPORT_FILENAME
        report = json.loads(report_path.read_text(encoding="utf-8"))

        # With only canonical rows, invariance_score is 0.0 and
        # mutation_drop.overall is 0.0 -- honest about missing coverage.
        assert report["invariance_score"] == 0.0
        assert report["mutation_drop"]["overall"] == 0.0
        assert report["item_instability_index"] == 0.0

    def test_sidecar_determinism(self, tmp_path: Path) -> None:
        """Two runs with the same input must produce byte-identical output."""
        dir_a = tmp_path / "run_a"
        dir_b = tmp_path / "run_b"

        write_judgment_validity_sidecar(dir_a, _ALL_RESULTS)
        write_judgment_validity_sidecar(dir_b, _ALL_RESULTS)

        items_a = (dir_a / JUDGMENT_VALIDITY_ITEMS_FILENAME).read_bytes()
        items_b = (dir_b / JUDGMENT_VALIDITY_ITEMS_FILENAME).read_bytes()
        assert items_a == items_b

        report_a = (dir_a / JUDGMENT_VALIDITY_REPORT_FILENAME).read_bytes()
        report_b = (dir_b / JUDGMENT_VALIDITY_REPORT_FILENAME).read_bytes()
        assert report_a == report_b

    def test_empty_results_produces_clean_output(self, tmp_path: Path) -> None:
        """Empty results list should produce empty JSONL and a report with zeros."""
        write_judgment_validity_sidecar(tmp_path, [])

        items_path = tmp_path / JUDGMENT_VALIDITY_ITEMS_FILENAME
        report_path = tmp_path / JUDGMENT_VALIDITY_REPORT_FILENAME

        assert items_path.read_text(encoding="utf-8") == ""

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["schema_version"] == "1.0"
        assert report["worst_case_error_rate"] == 0.0

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested_dir = tmp_path / "deep" / "nested" / "dir"
        paths = write_judgment_validity_sidecar(nested_dir, _ALL_RESULTS)

        assert Path(paths["validity_items"]).exists()
        assert Path(paths["validity_report"]).exists()

    def test_slice_support_reflects_tags(self, tmp_path: Path) -> None:
        write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)

        report_path = tmp_path / JUDGMENT_VALIDITY_REPORT_FILENAME
        report = json.loads(report_path.read_text(encoding="utf-8"))

        slice_support = report["slice_support"]
        assert "judgment" in slice_support
        assert slice_support["judgment"] == 3

    def test_rejects_preexisting_symlink_sidecar_target(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside.txt"
        outside.write_text("safe", encoding="utf-8")
        (tmp_path / JUDGMENT_VALIDITY_ITEMS_FILENAME).symlink_to(outside)

        with pytest.raises(OSError):
            write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)
        assert outside.read_text(encoding="utf-8") == "safe"

    def test_rejects_preexisting_symlink_report_sidecar_target(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside_report.txt"
        outside.write_text("safe", encoding="utf-8")
        (tmp_path / JUDGMENT_VALIDITY_REPORT_FILENAME).symlink_to(outside)

        with pytest.raises(OSError):
            write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)
        assert outside.read_text(encoding="utf-8") == "safe"

    def test_fails_closed_without_no_follow_support(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr(judgment_validity.os, "O_NOFOLLOW", raising=False)

        with pytest.raises(OSError, match="Symlink-safe writes are not supported on this platform"):
            write_judgment_validity_sidecar(tmp_path, _ALL_RESULTS)


# ---------------------------------------------------------------------------
# Guard tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case coverage for missing or unusual result keys."""

    def test_missing_case_id_defaults_to_unknown(self) -> None:
        result: dict[str, object] = {
            "decision": "promote",
            "boundary_class": "wellness_coaching",
            "hard_fail_reasons": [],
        }
        rec = result_to_eval_outcome(result)

        assert rec["canonical_id"] == "unknown"
        assert rec["variant_id"] == "unknown"

    def test_missing_decision_defaults_to_empty(self) -> None:
        result: dict[str, object] = {
            "case_id": "no_decision",
            "boundary_class": "wellness_coaching",
            "hard_fail_reasons": [],
        }
        rec = result_to_eval_outcome(result)

        assert rec["decision"] == ""
        assert rec["passed"] is False
        assert rec["score"] == 0.0

    def test_hard_fail_reasons_none_treated_as_empty(self) -> None:
        result: dict[str, object] = {
            "case_id": "null_hfr",
            "decision": "promote",
            "boundary_class": "wellness_coaching",
            "hard_fail_reasons": None,
        }
        rec = result_to_eval_outcome(result)

        assert "hard_fail" not in rec["slice_tags"]

    def test_hard_fail_reasons_non_list_treated_as_empty(self) -> None:
        """Non-list values (e.g. string) must not trigger hard_fail tag."""
        result: dict[str, object] = {
            "case_id": "str_hfr",
            "decision": "promote",
            "boundary_class": "wellness_coaching",
            "hard_fail_reasons": "unexpected_string_value",
        }
        rec = result_to_eval_outcome(result)

        assert "hard_fail" not in rec["slice_tags"]


class TestValidationBoundary:
    """Verify that malformed inputs propagate validator errors correctly."""

    def test_non_bool_passed_raises(self) -> None:
        """If score mapping produced a non-bool passed, validator must reject."""
        import scripts.evals.eval_validity_contract as evc

        raw: dict[str, object] = {
            "canonical_id": "bad",
            "variant_id": "bad",
            "variant_family": "canonical",
            "transform_type": "none",
            "passed": "yes",  # non-bool
            "score": 1.0,
            "decision": "promote",
            "slice_tags": ["judgment"],
        }
        with pytest.raises(ValueError, match="passed"):
            evc.validate_eval_outcome_record(raw)

    def test_non_finite_score_raises(self) -> None:
        import math

        import scripts.evals.eval_validity_contract as evc

        raw: dict[str, object] = {
            "canonical_id": "bad",
            "variant_id": "bad",
            "variant_family": "canonical",
            "transform_type": "none",
            "passed": True,
            "score": math.inf,
            "decision": "promote",
            "slice_tags": ["judgment"],
        }
        with pytest.raises(ValueError, match="score"):
            evc.validate_eval_outcome_record(raw)


class TestNoNetworkImports:
    """Guard: sidecar adapter must not import networking libraries."""

    def test_no_network_imports_in_module_source(self) -> None:
        import scripts.evals.judgment_validity as jv_mod

        source = Path(jv_mod.__file__).read_text(encoding="utf-8")

        for forbidden in ("import urllib", "import requests", "import httpx", "import aiohttp"):
            assert (
                forbidden not in source
            ), f"Forbidden network import found in judgment_validity.py: {forbidden}"

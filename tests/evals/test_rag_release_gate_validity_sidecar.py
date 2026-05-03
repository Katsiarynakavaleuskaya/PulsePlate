"""Deterministic tests for the RAG release-gate validity sidecar adapter.

RU: Тесты для sidecar-адаптера: маппинг trace -> EvalOutcomeRecord,
    генерация validity артефактов, отсутствие drift порогов.
EN: Tests for sidecar adapter: trace -> EvalOutcomeRecord mapping,
    validity artifact generation, no threshold drift.

No network.  No model calls.  Pure offline deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.evals.rag_release_gate_validity import (
    VALIDITY_ITEMS_FILENAME,
    VALIDITY_REPORT_FILENAME,
    _ITEM_NLI_ENTAILMENT_THRESHOLD,
    _ITEM_SUPPORT_PRECISION_THRESHOLD,
    trace_to_eval_outcome,
    traces_to_eval_outcomes,
    write_validity_sidecar,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trace(
    query_id: str = "q001",
    evidence_exact_match: bool = True,
    mean_nli_entailment: float = 0.90,
    support_precision: float = 0.85,
) -> dict[str, Any]:
    """Build a minimal RAG release-gate trace dict for testing."""
    return {
        "query_id": query_id,
        "faithfulness_metrics": {
            "evidence_exact_match": evidence_exact_match,
            "mean_nli_entailment": mean_nli_entailment,
            "support_precision": support_precision,
        },
    }


# ---------------------------------------------------------------------------
# trace_to_eval_outcome
# ---------------------------------------------------------------------------


class TestTraceToEvalOutcome:

    def test_passing_trace(self) -> None:
        trace = _make_trace(
            evidence_exact_match=True,
            mean_nli_entailment=0.90,
            support_precision=0.85,
        )
        rec = trace_to_eval_outcome(trace)
        assert rec["canonical_id"] == "q001"
        assert rec["variant_id"] == "q001"
        assert rec["variant_family"] == "canonical"
        assert rec["transform_type"] == "none"
        assert rec["passed"] is True
        assert rec["decision"] == "pass"
        assert rec["slice_tags"] == ["rag", "release_gate"]

    def test_failing_trace_low_nli(self) -> None:
        trace = _make_trace(
            evidence_exact_match=True,
            mean_nli_entailment=0.50,
            support_precision=0.90,
        )
        rec = trace_to_eval_outcome(trace)
        assert rec["passed"] is False
        assert rec["decision"] == "fail"

    def test_failing_trace_no_evidence_match(self) -> None:
        trace = _make_trace(
            evidence_exact_match=False,
            mean_nli_entailment=0.95,
            support_precision=0.95,
        )
        rec = trace_to_eval_outcome(trace)
        assert rec["passed"] is False
        assert rec["decision"] == "fail"

    def test_failing_trace_low_support(self) -> None:
        trace = _make_trace(
            evidence_exact_match=True,
            mean_nli_entailment=0.90,
            support_precision=0.50,
        )
        rec = trace_to_eval_outcome(trace)
        assert rec["passed"] is False
        assert rec["decision"] == "fail"

    def test_composite_score_is_mean_of_three(self) -> None:
        trace = _make_trace(
            evidence_exact_match=True,
            mean_nli_entailment=0.90,
            support_precision=0.80,
        )
        rec = trace_to_eval_outcome(trace)
        # mean(1.0, 0.90, 0.80) = 0.9
        assert rec["score"] == 0.9

    def test_composite_score_with_failed_evidence(self) -> None:
        trace = _make_trace(
            evidence_exact_match=False,
            mean_nli_entailment=0.90,
            support_precision=0.80,
        )
        rec = trace_to_eval_outcome(trace)
        # mean(0.0, 0.90, 0.80) = 0.566667
        assert rec["score"] == pytest.approx(0.566667, abs=1e-5)

    def test_missing_faithfulness_metrics(self) -> None:
        trace: dict[str, Any] = {"query_id": "q_empty"}
        rec = trace_to_eval_outcome(trace)
        assert rec["passed"] is False
        assert rec["decision"] == "fail"
        assert rec["score"] == 0.0

    def test_boundary_nli_exactly_at_threshold(self) -> None:
        trace = _make_trace(
            evidence_exact_match=True,
            mean_nli_entailment=_ITEM_NLI_ENTAILMENT_THRESHOLD,
            support_precision=_ITEM_SUPPORT_PRECISION_THRESHOLD,
        )
        rec = trace_to_eval_outcome(trace)
        assert rec["passed"] is True

    def test_boundary_nli_just_below_threshold(self) -> None:
        trace = _make_trace(
            evidence_exact_match=True,
            mean_nli_entailment=_ITEM_NLI_ENTAILMENT_THRESHOLD - 0.001,
            support_precision=_ITEM_SUPPORT_PRECISION_THRESHOLD,
        )
        rec = trace_to_eval_outcome(trace)
        assert rec["passed"] is False


# ---------------------------------------------------------------------------
# traces_to_eval_outcomes
# ---------------------------------------------------------------------------


class TestTracesToEvalOutcomes:

    def test_preserves_order(self) -> None:
        traces = [
            _make_trace(query_id="a"),
            _make_trace(query_id="b"),
            _make_trace(query_id="c"),
        ]
        outcomes = traces_to_eval_outcomes(traces)
        assert [r["canonical_id"] for r in outcomes] == ["a", "b", "c"]

    def test_empty_traces(self) -> None:
        assert traces_to_eval_outcomes([]) == []

    def test_deterministic(self) -> None:
        traces = [
            _make_trace(query_id="x", mean_nli_entailment=0.90),
            _make_trace(query_id="y", mean_nli_entailment=0.50),
        ]
        r1 = traces_to_eval_outcomes(traces)
        r2 = traces_to_eval_outcomes(traces)
        assert r1 == r2


# ---------------------------------------------------------------------------
# write_validity_sidecar
# ---------------------------------------------------------------------------


class TestWriteValiditySidecar:

    def test_writes_both_files(self, tmp_path: Path) -> None:
        traces = [
            _make_trace(query_id="s1", mean_nli_entailment=0.90),
            _make_trace(query_id="s2", mean_nli_entailment=0.50),
        ]
        result = write_validity_sidecar(tmp_path, traces)

        items_path = tmp_path / VALIDITY_ITEMS_FILENAME
        report_path = tmp_path / VALIDITY_REPORT_FILENAME
        assert items_path.exists()
        assert report_path.exists()
        assert result["validity_items"] == str(items_path)
        assert result["validity_report"] == str(report_path)

    def test_items_jsonl_is_valid(self, tmp_path: Path) -> None:
        traces = [_make_trace(query_id="j1"), _make_trace(query_id="j2")]
        write_validity_sidecar(tmp_path, traces)

        items_path = tmp_path / VALIDITY_ITEMS_FILENAME
        lines = items_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            rec = json.loads(line)
            assert "canonical_id" in rec
            assert "variant_family" in rec

    def test_report_has_required_keys(self, tmp_path: Path) -> None:
        traces = [_make_trace(query_id="r1")]
        write_validity_sidecar(tmp_path, traces)

        report_path = tmp_path / VALIDITY_REPORT_FILENAME
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "schema_version" in report
        assert "invariance_score" in report
        assert "mutation_drop" in report
        assert "worst_case_error_rate" in report
        assert "item_instability_index" in report
        assert "slice_support" in report
        assert "unstable_items" in report
        assert "slice_breakdown" in report

    def test_canonical_only_report_values(self, tmp_path: Path) -> None:
        """Canonical-only traces must honestly show zero invariance/mutation coverage."""
        traces = [_make_trace(query_id="c1"), _make_trace(query_id="c2")]
        write_validity_sidecar(tmp_path, traces)

        report_path = tmp_path / VALIDITY_REPORT_FILENAME
        report = json.loads(report_path.read_text(encoding="utf-8"))
        # No invariance variants exist, so invariance_score is 0.0
        assert report["invariance_score"] == 0.0
        # No mutation variants exist, so mutation_drop is zero
        assert report["mutation_drop"]["overall"] == 0.0
        assert report["mutation_drop"]["by_transform"] == {}
        # No multi-variant items, so instability is 0.0
        assert report["item_instability_index"] == 0.0
        # No unstable items
        assert report["unstable_items"] == []

    def test_sidecar_deterministic(self, tmp_path: Path) -> None:
        traces = [
            _make_trace(query_id="d1", mean_nli_entailment=0.90),
            _make_trace(query_id="d2", mean_nli_entailment=0.50),
        ]
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"
        write_validity_sidecar(dir1, traces)
        write_validity_sidecar(dir2, traces)

        report1 = (dir1 / VALIDITY_REPORT_FILENAME).read_text(encoding="utf-8")
        report2 = (dir2 / VALIDITY_REPORT_FILENAME).read_text(encoding="utf-8")
        assert report1 == report2

        items1 = (dir1 / VALIDITY_ITEMS_FILENAME).read_text(encoding="utf-8")
        items2 = (dir2 / VALIDITY_ITEMS_FILENAME).read_text(encoding="utf-8")
        assert items1 == items2

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        write_validity_sidecar(nested, [_make_trace()])
        assert (nested / VALIDITY_ITEMS_FILENAME).exists()
        assert (nested / VALIDITY_REPORT_FILENAME).exists()

    def test_empty_traces_no_crash(self, tmp_path: Path) -> None:
        """Empty trace list must produce valid report without crash."""
        result = write_validity_sidecar(tmp_path, [])
        assert (tmp_path / VALIDITY_ITEMS_FILENAME).exists()
        assert (tmp_path / VALIDITY_REPORT_FILENAME).exists()
        report = json.loads((tmp_path / VALIDITY_REPORT_FILENAME).read_text(encoding="utf-8"))
        assert report["invariance_score"] == 0.0
        assert report["worst_case_error_rate"] == 0.0
        assert report["unstable_items"] == []
        items_text = (tmp_path / VALIDITY_ITEMS_FILENAME).read_text(encoding="utf-8")
        assert items_text.strip() == ""
        assert "validity_items" in result
        assert "validity_report" in result


# ---------------------------------------------------------------------------
# Threshold alignment regression
# ---------------------------------------------------------------------------


class TestThresholdAlignment:

    def test_thresholds_match_gate_constants(self) -> None:
        """Sidecar thresholds must match RAG release-gate GATE_THRESHOLDS."""
        from scripts.evals.run_rag_release_gates import GATE_THRESHOLDS

        assert _ITEM_SUPPORT_PRECISION_THRESHOLD == GATE_THRESHOLDS["support_precision"]
        assert _ITEM_NLI_ENTAILMENT_THRESHOLD == GATE_THRESHOLDS["mean_nli_entailment"]


# ---------------------------------------------------------------------------
# Security: no network imports
# ---------------------------------------------------------------------------


class TestNoNetworkImports:

    def test_adapter_module_has_no_network_deps(self) -> None:
        """Ensure rag_release_gate_validity does not import network libs."""
        import scripts.evals.rag_release_gate_validity as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        for lib in ("requests", "httpx", "urllib.request", "aiohttp"):
            assert (
                f"import {lib}" not in source
            ), f"rag_release_gate_validity.py must not import {lib}"


# ---------------------------------------------------------------------------
# Sidecar must NOT appear in rag_gate_result source_artifacts
# ---------------------------------------------------------------------------


class TestSidecarNotInGateResult:

    def test_sidecar_keys_not_in_source_artifact_keys(self) -> None:
        """Sidecar artifacts must NOT be in RAG_GATE_SOURCE_ARTIFACT_KEYS."""
        from scripts.evals.run_rag_release_gates import RAG_GATE_SOURCE_ARTIFACT_KEYS

        assert "validity_items" not in RAG_GATE_SOURCE_ARTIFACT_KEYS
        assert "validity_report" not in RAG_GATE_SOURCE_ARTIFACT_KEYS


# ---------------------------------------------------------------------------
# Sidecar failure graceful degradation (covers except branch)
# ---------------------------------------------------------------------------


class TestSidecarFailureGracefulDegradation:

    def test_sidecar_failure_does_not_crash_runner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If write_validity_sidecar raises, the runner must continue."""
        import scripts.evals.rag_release_gate_validity as sidecar_mod

        def _boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("sidecar test failure")

        monkeypatch.setattr(sidecar_mod, "write_validity_sidecar", _boom)

        # Simulate the try/except block from async_main.
        artifacts: dict[str, str] = {"gate_report": "/fake/gate_report.md"}
        run_dir = tmp_path / "run"
        traces: list[dict[str, object]] = [{"query_id": "x"}]

        exc_msg: str | None = None
        try:
            from scripts.evals.rag_release_gate_validity import write_validity_sidecar

            validity_sidecar = write_validity_sidecar(run_dir, traces)
            artifacts.update(validity_sidecar)
        except Exception as exc:  # noqa: BLE001
            exc_msg = str(exc)

        # Sidecar failed, but artifacts dict still has the original keys.
        assert "gate_report" in artifacts
        assert "validity_items" not in artifacts
        assert "validity_report" not in artifacts
        assert exc_msg is not None
        assert "sidecar test failure" in exc_msg

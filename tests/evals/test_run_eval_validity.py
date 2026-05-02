"""Deterministic tests for the eval validity runner CLI.

RU: Тесты для runner-а eval validity — запись отчёта, ошибки, детерминизм.
EN: Tests for eval validity runner — report writing, errors, determinism.

No network.  No model calls.  Pure offline deterministic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.run_eval_validity import main as runner_main  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RAG_SAMPLE = REPO_ROOT / "data" / "evals" / "pulseplate_rag_eval_validity_sample.jsonl"
JUDGMENT_SAMPLE = REPO_ROOT / "data" / "evals" / "pulseplate_judgment_eval_validity_sample.jsonl"


def _read_report(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Runner integration
# ---------------------------------------------------------------------------


class TestRunnerWritesReport:

    def test_rag_sample(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        runner_main(["--input", str(RAG_SAMPLE), "--output", str(out)])
        assert out.exists()
        report = _read_report(out)
        assert "invariance_score" in report
        assert "mutation_drop" in report
        assert "worst_case_error_rate" in report
        assert "item_instability_index" in report
        assert "slice_support" in report
        assert "unstable_items" in report

    def test_judgment_sample(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        runner_main(["--input", str(JUDGMENT_SAMPLE), "--output", str(out)])
        assert out.exists()
        report = _read_report(out)
        assert isinstance(report["unstable_items"], list)

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "dir" / "report.json"
        runner_main(["--input", str(RAG_SAMPLE), "--output", str(out)])
        assert out.exists()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestReportDeterminism:

    def test_same_input_same_output(self, tmp_path: Path) -> None:
        out1 = tmp_path / "r1.json"
        out2 = tmp_path / "r2.json"
        runner_main(["--input", str(RAG_SAMPLE), "--output", str(out1)])
        runner_main(["--input", str(RAG_SAMPLE), "--output", str(out2)])
        assert out1.read_text() == out2.read_text()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRunnerErrorHandling:

    def test_malformed_jsonl(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.jsonl"
        bad.write_text("this is not json\n", encoding="utf-8")
        out = tmp_path / "out.json"
        with pytest.raises(ValueError, match="invalid JSON"):
            runner_main(["--input", str(bad), "--output", str(out)])

    def test_missing_field_jsonl(self, tmp_path: Path) -> None:
        bad = tmp_path / "missing.jsonl"
        bad.write_text(
            '{"canonical_id": "x", "variant_id": "y"}\n',
            encoding="utf-8",
        )
        out = tmp_path / "out.json"
        with pytest.raises(ValueError, match="missing keys"):
            runner_main(["--input", str(bad), "--output", str(out)])

    def test_nonexistent_input(self, tmp_path: Path) -> None:
        out = tmp_path / "out.json"
        with pytest.raises(FileNotFoundError):
            runner_main(["--input", str(tmp_path / "nope.jsonl"), "--output", str(out)])

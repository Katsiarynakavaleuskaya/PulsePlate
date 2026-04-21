"""Runner contract tests for the offline RAGAS bootstrap lane."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def _write_dataset(path: Path) -> None:
    """Write a deterministic JSONL fixture for runner tests."""

    rows = [
        {
            "question": "How can I recover from all-or-nothing thinking after dessert?",
            "answer": "Treat dessert as one event and return to the next planned meal.",
            "contexts": [
                "All-or-nothing thinking often escalates one food choice into a global failure.",
                "Returning to the next planned meal supports recovery without punishment.",
            ],
            "reference": "Reframe the dessert as one event and continue with the next planned meal.",
        },
        {
            "question": "What helps when I skip lunch and overeat later?",
            "answer": "Use a predictable lunch anchor to reduce long hunger gaps.",
            "contexts": [
                "Long gaps without food can increase hunger intensity later in the day.",
                "A predictable meal anchor can reduce rebound overeating pressure.",
            ],
            "ground_truth": "Add a lunch anchor to reduce long hunger gaps and late overeating.",
        },
    ]
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_runner_module_imports_without_ragas() -> None:
    """Importing the runner must not require ragas to be installed."""

    module = importlib.import_module("evals.ragas.run_ragas_eval")

    assert module.REPORT_ONLY_MODE is True
    assert callable(module.parse_args)


def test_parse_args_supports_bootstrap_cli_contract() -> None:
    """The CLI parser must accept dataset and optional output paths."""

    runner = importlib.import_module("evals.ragas.run_ragas_eval")

    args = runner.parse_args(
        [
            "--dataset",
            "evals/ragas/testset.jsonl",
            "--output-json",
            "/tmp/ragas_report.json",
            "--output-md",
            "/tmp/ragas_report.md",
        ]
    )

    assert args.dataset == Path("evals/ragas/testset.jsonl")
    assert args.output_json == Path("/tmp/ragas_report.json")
    assert args.output_md == Path("/tmp/ragas_report.md")


def test_run_report_is_deterministic_and_lazy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The runner must build a stable report without loading ragas during tests."""

    runner = importlib.import_module("evals.ragas.run_ragas_eval")
    dataset_path = tmp_path / "testset.jsonl"
    _write_dataset(dataset_path)

    def _boom() -> tuple[object, object, object]:
        raise AssertionError("ragas import path should stay lazy in this test")

    def _fake_evaluator(
        rows: list[dict[str, object]],
        metric_names: tuple[str, ...],
    ) -> dict[str, float]:
        assert len(rows) == 2
        assert metric_names == (
            "faithfulness",
            "answer_relevancy",
            "context_precision",
        )
        return {
            "faithfulness": 0.84,
            "answer_relevancy": 0.79,
            "context_precision": 0.88,
        }

    monkeypatch.setattr(runner, "_load_ragas_dependencies", _boom)

    report = runner.run_report(dataset_path, evaluator=_fake_evaluator)
    summary = runner.render_markdown_summary(report)

    assert report == {
        "dataset_path": str(dataset_path.resolve()),
        "sample_count": 2,
        "report_only": True,
        "metrics": {
            "faithfulness": 0.84,
            "answer_relevancy": 0.79,
            "context_precision": 0.88,
        },
    }
    assert "Metric | Score" in summary
    assert "faithfulness | 0.84" in summary
    assert "answer_relevancy | 0.79" in summary
    assert "context_precision | 0.88" in summary
    assert "PASS" not in summary
    assert "NO-GO" not in summary

"""RU: Offline RAGAS runner. EN: Offline RAGAS runner."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Mapping

from evals.ragas.metrics_config import DEFAULT_RAGAS_METRICS, REPORT_ONLY_MODE

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = REPO_ROOT / "evals" / "ragas" / "testset.jsonl"

REQUIRED_METRIC_NAMES: tuple[str, ...] = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
)


MetricEvaluator = Callable[[list[dict[str, Any]], tuple[str, ...]], Mapping[str, float]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """RU: Разобрать CLI-аргументы. EN: Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Run the report-only RAGAS bootstrap on a local curated dataset.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Local JSONL dataset path. Defaults to evals/ragas/testset.jsonl.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help=(
            "Optional JSON report output path. Default output is stdout-only; "
            "prefer /tmp or artifacts/rag_eval/<experiment_id>/."
        ),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help=(
            "Optional Markdown summary output path. Default output is stdout-only; "
            "prefer /tmp or artifacts/rag_eval/<experiment_id>/."
        ),
    )
    return parser.parse_args(argv)


def _display_path(path: Path) -> str:
    """RU: Нормализовать путь для отчёта. EN: Normalize a report path."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _normalize_string(value: Any, *, field_name: str, row_number: int) -> str:
    """RU: Проверить строковое поле. EN: Validate a string field."""

    if not isinstance(value, str):
        raise ValueError(f"Row {row_number}: '{field_name}' must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"Row {row_number}: '{field_name}' must be non-empty.")
    return normalized


def _normalize_contexts(value: Any, *, row_number: int) -> list[str]:
    """RU: Проверить contexts. EN: Validate contexts."""

    if not isinstance(value, list) or not value:
        raise ValueError(f"Row {row_number}: 'contexts' must be a non-empty list.")

    contexts: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str):
            raise ValueError(
                f"Row {row_number}: 'contexts[{index}]' must be a string.",
            )
        normalized = item.strip()
        if not normalized:
            raise ValueError(
                f"Row {row_number}: 'contexts[{index}]' must be non-empty.",
            )
        contexts.append(normalized)
    return contexts


def _normalize_row(raw_row: dict[str, Any], row_number: int) -> dict[str, Any]:
    """RU: Нормализовать строку датасета. EN: Normalize one dataset row."""

    question = _normalize_string(
        raw_row.get("question"),
        field_name="question",
        row_number=row_number,
    )
    answer = _normalize_string(
        raw_row.get("answer"),
        field_name="answer",
        row_number=row_number,
    )
    contexts = _normalize_contexts(raw_row.get("contexts"), row_number=row_number)

    reference_value = raw_row.get("reference")
    ground_truth_value = raw_row.get("ground_truth")
    if reference_value is None and ground_truth_value is None:
        raise ValueError(
            f"Row {row_number}: one of 'reference' or 'ground_truth' is required.",
        )

    reference_text = _normalize_string(
        reference_value if reference_value is not None else ground_truth_value,
        field_name="reference" if reference_value is not None else "ground_truth",
        row_number=row_number,
    )

    return {
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "reference_text": reference_text,
        "reference": reference_text,
        "ground_truth": reference_text,
    }


def load_dataset_rows(dataset_path: Path) -> list[dict[str, Any]]:
    """RU: Загрузить локальный JSONL датасет. EN: Load the local JSONL dataset."""

    if dataset_path.suffix != ".jsonl":
        raise ValueError("Dataset must be a .jsonl file.")
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    rows: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for row_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Row {row_number}: invalid JSON.") from exc
            if not isinstance(parsed, dict):
                raise ValueError(f"Row {row_number}: JSON value must be an object.")
            rows.append(_normalize_row(parsed, row_number))

    if not rows:
        raise ValueError("Dataset is empty.")
    return rows


def _validate_metric_names(metric_names: tuple[str, ...]) -> tuple[str, ...]:
    """RU: Проверить metric contract. EN: Validate the metric contract."""

    if metric_names != REQUIRED_METRIC_NAMES:
        raise ValueError(
            "Bootstrap metric contract drift detected. "
            f"Expected {REQUIRED_METRIC_NAMES!r}, got {metric_names!r}.",
        )
    if not REPORT_ONLY_MODE:
        raise ValueError("Bootstrap runner must stay in report-only mode.")
    return metric_names


def _load_ragas_dependencies() -> tuple[Any, Any, Mapping[str, Any]]:
    """RU: Lazy import RAGAS deps. EN: Lazy import RAGAS dependencies."""

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, faithfulness
    except ImportError as exc:
        raise RuntimeError(
            "RAGAS dependencies are not installed. "
            "Install requirements-evals.txt before running this command.",
        ) from exc

    metric_map = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
    }
    return Dataset, evaluate, metric_map


def _extract_metric_scores(
    result: Any,
    metric_names: tuple[str, ...],
) -> dict[str, float]:
    """RU: Вытащить агрегированные metric scores. EN: Extract aggregate metric scores."""

    if isinstance(result, Mapping):
        return _validate_metric_scores(result, metric_names, source="mapping result")

    if hasattr(result, "to_pandas"):
        frame = result.to_pandas()
        aggregated = {name: float(frame[name].mean()) for name in metric_names if name in frame}
        return _validate_metric_scores(aggregated, metric_names, source="pandas result")

    scores = getattr(result, "scores", None)
    if scores is not None and hasattr(scores, "to_list"):
        rows = scores.to_list()
        if not rows:
            raise RuntimeError("Metric result from score rows is empty.")
        aggregated = {
            name: float(mean(float(row[name]) for row in rows))
            for name in metric_names
            if all(name in row for row in rows)
        }
        return _validate_metric_scores(aggregated, metric_names, source="score rows")

    raise RuntimeError("Could not extract metric scores from the RAGAS result.")


def _validate_metric_scores(
    scores: Mapping[str, Any],
    metric_names: tuple[str, ...],
    *,
    source: str,
) -> dict[str, float]:
    """RU: Проверить полноту metric payload. EN: Validate metric payload completeness."""

    missing = [name for name in metric_names if name not in scores]
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(
            f"Metric result from {source} is missing required scores: {missing_text}.",
        )

    validated: dict[str, float] = {}
    for name in metric_names:
        value = float(scores[name])
        if not math.isfinite(value):
            raise RuntimeError(
                f"Metric result from {source} contains a non-finite score for {name}.",
            )
        validated[name] = value
    return validated


def evaluate_records(
    rows: list[dict[str, Any]],
    metric_names: tuple[str, ...],
    *,
    evaluator: MetricEvaluator | None = None,
) -> dict[str, float]:
    """RU: Посчитать метрики. EN: Evaluate metrics for normalized rows."""

    if evaluator is not None:
        scores = evaluator(rows, metric_names)
        return _validate_metric_scores(scores, metric_names, source="custom evaluator")

    dataset_cls, evaluate, metric_map = _load_ragas_dependencies()
    ragas_rows = [
        {
            "question": row["question"],
            "answer": row["answer"],
            "contexts": row["contexts"],
            "reference": row["reference"],
            "ground_truth": row["ground_truth"],
        }
        for row in rows
    ]
    dataset = dataset_cls.from_list(ragas_rows)
    metrics = [metric_map[name] for name in metric_names]

    try:
        result = evaluate(dataset=dataset, metrics=metrics, show_progress=False)
    except TypeError:
        result = evaluate(dataset=dataset, metrics=metrics)

    return _extract_metric_scores(result, metric_names)


def build_report(
    dataset_path: Path,
    rows: list[dict[str, Any]],
    metric_scores: Mapping[str, float],
) -> dict[str, Any]:
    """RU: Собрать JSON report. EN: Build the JSON report payload."""

    return {
        "dataset_path": _display_path(dataset_path),
        "sample_count": len(rows),
        "report_only": REPORT_ONLY_MODE,
        "metrics": {name: float(metric_scores[name]) for name in DEFAULT_RAGAS_METRICS},
    }


def format_score(value: float) -> str:
    """RU: Стабильно отформатировать score. EN: Format a score stably."""

    return f"{value:.4f}".rstrip("0").rstrip(".")


def render_markdown_summary(report: Mapping[str, Any]) -> str:
    """RU: Собрать Markdown summary. EN: Render the Markdown summary."""

    lines = ["Metric | Score", "--- | ---:"]
    metrics = report["metrics"]
    for name in DEFAULT_RAGAS_METRICS:
        lines.append(f"{name} | {format_score(float(metrics[name]))}")
    return "\n".join(lines)


def write_outputs(
    report: Mapping[str, Any],
    markdown_summary: str,
    *,
    output_json: Path | None,
    output_md: Path | None,
) -> None:
    """RU: Записать optional outputs. EN: Write optional outputs."""

    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(markdown_summary + "\n", encoding="utf-8")


def run_report(
    dataset_path: Path,
    *,
    evaluator: MetricEvaluator | None = None,
) -> dict[str, Any]:
    """RU: Выполнить report-only eval. EN: Execute the report-only evaluation."""

    metric_names = _validate_metric_names(DEFAULT_RAGAS_METRICS)
    rows = load_dataset_rows(dataset_path)
    scores = evaluate_records(rows, metric_names, evaluator=evaluator)
    return build_report(dataset_path, rows, scores)


def main(argv: list[str] | None = None) -> int:
    """RU: CLI entrypoint. EN: CLI entrypoint."""

    args = parse_args(argv)
    try:
        report = run_report(args.dataset)
        markdown_summary = render_markdown_summary(report)
        print(markdown_summary)
        write_outputs(
            report,
            markdown_summary,
            output_json=args.output_json,
            output_md=args.output_md,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

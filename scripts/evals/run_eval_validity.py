#!/usr/bin/env python3
"""Deterministic validity report runner for eval outcome JSONL.

RU: Запускает расчёт validity-метрик из JSONL-файла eval-outcome записей.
EN: Computes validity metrics from a JSONL file of eval outcome records.

No network calls.  No model invocations.  Pure offline computation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.eval_validity_contract import (  # noqa: E402
    build_validity_report,
    validate_eval_outcome_record,
)

DEFAULT_INPUT_PATH = REPO_ROOT / "data" / "evals" / "pulseplate_rag_eval_validity_sample.jsonl"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "evals" / "validity_report.json"


def _load_outcomes(path: Path) -> list[dict[str, object]]:
    """Load and validate outcome records from a JSONL file.

    Raises on first malformed line.
    """
    outcomes: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(raw, dict):
                raise ValueError(
                    f"{path}:{lineno}: expected JSON object, " f"got {type(raw).__name__}"
                )
            outcomes.append(validate_eval_outcome_record(raw))
    return outcomes


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compute evaluation validity report from outcome JSONL.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to JSONL file of EvalOutcomeRecord rows.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write the JSON validity report.",
    )
    args = parser.parse_args(argv)

    outcomes = _load_outcomes(args.input)
    report = build_validity_report(outcomes)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")

    print(f"Validity report written to {args.output}")
    print(f"  invariance_score:      {report['invariance_score']}")
    print(f"  mutation_drop.overall: {report['mutation_drop']['overall']}")
    print(f"  worst_case_error_rate: {report['worst_case_error_rate']}")
    print(f"  item_instability:      {report['item_instability_index']}")
    print(f"  unstable_items:        {report['unstable_items']}")


if __name__ == "__main__":
    main()

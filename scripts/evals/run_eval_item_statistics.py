#!/usr/bin/env python3
"""CLI runner for evaluation item statistics baseline.

RU: CLI для генерации описательной статистики eval-элементов.
EN: Computes descriptive item-level statistics from the item metadata
    registry and curated fixture outcomes.

No network calls.  No model invocations.  Pure offline computation.
No IRT.  No psychometric scoring.  No adaptive item selection.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.eval_item_registry import load_eval_item_registry  # noqa: E402
from scripts.evals.eval_item_statistics import (  # noqa: E402
    build_item_statistics,
    build_item_statistics_report,
    load_fixture_outcomes,
    write_item_statistics_report,
)
from scripts.evals.eval_validity_contract import EvalOutcomeRecord  # noqa: E402

DEFAULT_REGISTRY_PATH = REPO_ROOT / "data" / "evals" / "eval_item_metadata_registry.jsonl"
DEFAULT_FIXTURES = [
    REPO_ROOT / "data" / "evals" / "pulseplate_judgment_eval_validity_variants.jsonl",
    REPO_ROOT / "data" / "evals" / "pulseplate_rag_release_gate_validity_variants.jsonl",
]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "evals" / "item_statistics_report.json"


def main(argv: list[str] | None = None) -> None:
    """Entry point for the item statistics CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Compute descriptive item-level statistics from the item "
            "metadata registry and curated fixture outcomes."
        ),
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Path to the item metadata registry JSONL file.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        action="append",
        default=None,
        dest="fixtures",
        help=(
            "Path to an EvalOutcomeRecord JSONL fixture file.  Can be "
            "repeated.  Defaults to judgment + RAG variant fixtures."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write the JSON item statistics report.",
    )
    args = parser.parse_args(argv)

    fixture_paths: list[Path] = args.fixtures if args.fixtures else list(DEFAULT_FIXTURES)

    # Load registry
    registry_records = load_eval_item_registry(args.registry)

    # Load all fixture outcomes
    all_outcomes: list[EvalOutcomeRecord] = []
    for fp in fixture_paths:
        all_outcomes.extend(load_fixture_outcomes(fp))

    # Build statistics
    items = build_item_statistics(all_outcomes, registry_records)
    report = build_item_statistics_report(items)

    # Write report
    write_item_statistics_report(report, args.output)

    # Print compact summary
    print(f"Item statistics report written to {args.output}")
    print(f"  item_count:         {report['item_count']}")
    print(f"  lane_counts:        {report['lane_counts']}")
    print(f"  anchor_item_count:  {report['anchor_item_count']}")
    print(f"  unstable_items:     {report['unstable_item_count']}")


if __name__ == "__main__":
    main()

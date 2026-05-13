"""CLI for the deterministic PR14 recipe/dish corpus governance gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.food_sources.recipe_dish_corpus import build_recipe_dish_corpus_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--onboarding", required=True, type=Path)
    parser.add_argument("--coverage", required=True, type=Path)
    parser.add_argument("--chain-public-nutrition", required=True, type=Path)
    parser.add_argument("--per-chain-legal", required=True, type=Path)
    parser.add_argument("--governance", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    report = build_recipe_dish_corpus_report(
        catalog_path=args.catalog,
        onboarding_path=args.onboarding,
        coverage_path=args.coverage,
        chain_public_nutrition_path=args.chain_public_nutrition,
        per_chain_legal_path=args.per_chain_legal,
        governance_path=args.governance,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["success"]:
        print("food_source_recipe_dish_corpus: PASS")
    else:
        print("food_source_recipe_dish_corpus: FAIL")
        print("Validation errors:")
        errors = report.get("validation_errors", [])
        if not isinstance(errors, list):
            errors = [str(errors)]
        for error in errors:
            print(f"- {error}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

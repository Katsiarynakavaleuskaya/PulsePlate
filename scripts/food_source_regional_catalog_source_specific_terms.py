"""CLI for the deterministic PR19 regional catalog source-specific terms gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.food_sources.regional_catalog_source_specific_terms import (
    build_regional_catalog_source_specific_terms_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json"),
    )
    parser.add_argument(
        "--onboarding",
        type=Path,
        default=Path("docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json"),
    )
    parser.add_argument(
        "--coverage",
        type=Path,
        default=Path("docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json"),
    )
    parser.add_argument(
        "--recipe-dish-corpus",
        type=Path,
        default=Path("docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json"),
    )
    parser.add_argument(
        "--preference-mapping",
        type=Path,
        default=Path("docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json"),
    )
    parser.add_argument(
        "--pr16-closeout",
        type=Path,
        default=Path(
            "docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_2026-05-19.json"
        ),
    )
    parser.add_argument(
        "--pr17-identity",
        type=Path,
        default=Path(
            "docs/architecture/FOOD_DATA_REGIONAL_CATALOG_IDENTITY_LICENSE_PR17_2026-05-19.json"
        ),
    )
    parser.add_argument(
        "--pr18-provider-terms",
        type=Path,
        default=Path(
            "docs/architecture/"
            "FOOD_DATA_REGIONAL_CATALOG_PROVIDER_TERMS_MATRIX_PR18_2026-05-21.json"
        ),
    )
    parser.add_argument(
        "--source-specific-terms",
        type=Path,
        default=Path(
            "docs/architecture/"
            "FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json"
        ),
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    report = build_regional_catalog_source_specific_terms_report(
        catalog_path=args.catalog,
        onboarding_path=args.onboarding,
        coverage_path=args.coverage,
        recipe_dish_corpus_path=args.recipe_dish_corpus,
        preference_mapping_path=args.preference_mapping,
        pr16_closeout_path=args.pr16_closeout,
        pr17_identity_path=args.pr17_identity,
        pr18_provider_terms_path=args.pr18_provider_terms,
        source_specific_terms_path=args.source_specific_terms,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["success"]:
        print("food_source_regional_catalog_source_specific_terms: PASS")
    else:
        print("food_source_regional_catalog_source_specific_terms: FAIL")
        print("Validation errors:")
        errors = report.get("validation_errors", [])
        if not isinstance(errors, list):
            errors = [str(errors)]
        for error in errors:
            print(f"- {error}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

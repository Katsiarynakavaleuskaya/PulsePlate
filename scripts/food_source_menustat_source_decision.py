"""CLI for the deterministic PR10 MenuStat source-decision gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.food_sources.menustat_source_decision import (
    build_menustat_source_decision_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--onboarding", required=True, type=Path)
    parser.add_argument("--replacement", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    report = build_menustat_source_decision_report(
        catalog_path=args.catalog,
        onboarding_path=args.onboarding,
        replacement_path=args.replacement,
        decision_path=args.decision,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["success"]:
        print("menustat_source_decision: PASS")
    else:
        print("menustat_source_decision: FAIL")
        print("Validation errors:")
        errors = report.get("validation_errors", [])
        if not isinstance(errors, list):
            errors = [str(errors)]
        for error in errors:
            print(f"- {error}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

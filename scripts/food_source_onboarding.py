#!/usr/bin/env python3
"""
Dry-run food source onboarding gate.

RU: Файловая проверка onboarding-политики без сети, БД и ingest.
EN: File-only onboarding policy check with no network, database, or ingest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.food_sources.source_onboarding import build_source_onboarding_report


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate food source onboarding decisions without ingesting data.",
    )
    parser.add_argument(
        "--catalog",
        required=True,
        type=Path,
        help="Validated source catalog JSON.",
    )
    parser.add_argument(
        "--onboarding",
        required=True,
        type=Path,
        help="Source onboarding decision JSON.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        required=True,
        help="Emit the deterministic JSON report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    report = build_source_onboarding_report(
        catalog_path=args.catalog,
        onboarding_path=args.onboarding,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("success") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

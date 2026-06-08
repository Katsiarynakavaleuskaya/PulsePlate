#!/usr/bin/env python3
"""Emit a USDA/FDC source manifest from local files only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.food_sources.usda_fdc_manifest import (
    USDA_FDC_MANIFEST_CONTRACTS,
    USDAFDCSource,
    build_usda_fdc_manifest,
    source_manifest_to_json_dict,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a file-only USDA/FDC manifest in the source_preflight contract.",
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=sorted(USDA_FDC_MANIFEST_CONTRACTS),
        help="USDA/FDC source family.",
    )
    parser.add_argument(
        "--artifact-path",
        required=True,
        type=Path,
        help="Local downloaded artifact or CSV file used for checksum/size.",
    )
    parser.add_argument(
        "--schema-csv",
        type=Path,
        help="Optional local CSV used for schema fields and row count.",
    )
    parser.add_argument(
        "--source-version",
        required=True,
        help="Source release version, e.g. fdc-foundation-2026-04.",
    )
    parser.add_argument(
        "--retrieved-on",
        required=True,
        help="Retrieval date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        required=True,
        help="Required safety flag. Emit deterministic JSON to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    manifest = build_usda_fdc_manifest(
        source=cast(USDAFDCSource, args.source),
        artifact_path=args.artifact_path,
        schema_csv_path=args.schema_csv,
        source_version=args.source_version,
        retrieved_on=args.retrieved_on,
    )
    print(json.dumps(source_manifest_to_json_dict(manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

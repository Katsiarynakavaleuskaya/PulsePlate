#!/usr/bin/env python3
"""
Dry-run food source manifest preflight.

RU: Файловая preflight-проверка без сети, БД и runtime cutover.
EN: File-only preflight check with no network, database, or runtime cutover.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.food_sources.source_preflight import build_source_preflight_report


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and diff food source manifests without ingesting data.",
    )
    parser.add_argument(
        "--current-manifest",
        required=True,
        type=Path,
        help="Current accepted source manifest JSON.",
    )
    parser.add_argument(
        "--incoming-manifest",
        required=True,
        type=Path,
        help="Incoming candidate source manifest JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        required=True,
        help="Required safety flag. The command never writes or ingests data.",
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
    report = build_source_preflight_report(
        current_manifest=args.current_manifest,
        incoming_manifest=args.incoming_manifest,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("success") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

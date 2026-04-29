#!/usr/bin/env python3
"""
Dry-run JPTN source identity/license gate.

RU: Файловая проверка JPTN без сети, БД и ingest.
EN: File-only JPTN gate check with no network, database, or ingest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from core.food_sources.jptn_identity import build_jptn_identity_report


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the file-only JPTN identity gate."""
    parser = argparse.ArgumentParser(
        description="Validate the JPTN source identity/license gate without ingesting data.",
    )
    parser.add_argument("--catalog", required=True, type=Path, help="Source catalog JSON.")
    parser.add_argument("--onboarding", required=True, type=Path, help="Onboarding gate JSON.")
    parser.add_argument("--identity", required=True, type=Path, help="JPTN identity gate JSON.")
    parser.add_argument("--json", action="store_true", help="Emit the deterministic JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the JPTN identity validator and return a process exit code."""
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    report = build_jptn_identity_report(
        catalog_path=args.catalog,
        onboarding_path=args.onboarding,
        identity_path=args.identity,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        success = report.get("success") is True
        status = "PASS" if success else "FAIL"
        print(f"jptn_identity: {status}")
        if not success:
            validation_errors = report.get("validation_errors") or []
            if validation_errors:
                print("Validation errors:")
                for error in validation_errors:
                    print(f"- {error}")
    return 0 if report.get("success") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

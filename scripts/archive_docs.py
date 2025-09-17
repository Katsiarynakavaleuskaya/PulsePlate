#!/usr/bin/env python3
"""
Archive selected markdown/TODO files into docs/archive/YYYY-MM-DD.

Usage:
  python scripts/archive_docs.py            # dry run, prints plan
  python scripts/archive_docs.py --execute  # actually move files
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import List


CANDIDATES = [
    "AUTOMATION_ERRORS_REPORT.md",
    "AUTOMATION_SUMMARY.md",
    "CHANGES_SUMMARY.md",
    "CODE_CHANGES.md",
    "CODE_TEMPLATES_ES_LOCALIZATION.md",
    "NEXT_SESSION_PLAN.md",
    "PROJECT_TODO.md",
    "QUICK_GUIDE.md",
    "QUICK_START.md",
    "SPANISH_EXAMPLES.md",
    "SPANISH_IMPLEMENTATION_SUMMARY.md",
    "SPORTS_NUTRITION_SUMMARY.md",
    "TODO.md",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="perform the moves")
    args = ap.parse_args()

    root = Path(".").resolve()
    today = date.today().isoformat()
    dest_dir = root / "docs" / "archive" / today
    dest_dir.mkdir(parents=True, exist_ok=True)

    planned: List[str] = []
    moved: List[str] = []
    for name in CANDIDATES:
        src = root / name
        if not src.exists():
            continue
        dst = dest_dir / name
        planned.append(f"{src} -> {dst}")
        if args.execute:
            dst.write_bytes(src.read_bytes())
            src.unlink()
            moved.append(f"{src} -> {dst}")

    index = root / "docs" / "archive" / "ARCHIVE_INDEX.md"
    if args.execute and moved:
        index.parent.mkdir(parents=True, exist_ok=True)
        with index.open("a", encoding="utf-8") as f:
            f.write(f"\nMoved on: {today}\n")
            for line in moved:
                f.write(f"- {line}\n")

    print("Archive plan:")
    for line in planned:
        print("  ", line)
    if args.execute:
        print("Moved:")
        for line in moved:
            print("  ", line)
    else:
        print("(dry-run) add --execute to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


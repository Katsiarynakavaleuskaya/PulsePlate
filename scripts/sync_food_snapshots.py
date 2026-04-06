#!/usr/bin/env python3
"""
CLI: sync Open Food Facts raw snapshots into the local snapshot tree.

RU: CLI для загрузки сырых снапшотов OFF.
EN: CLI to download OFF raw snapshots into ``data/raw/snapshots``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.food_apis.snapshot_sync import (  # noqa: E402
    default_raw_snapshot_root,
    sync_openfoodfacts_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Open Food Facts raw snapshots.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Snapshot base directory (default: env PULSEPLATE_FOOD_RAW_SNAPSHOT_ROOT or "
        "data/raw/snapshots under project root)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync even when delta policy would skip.",
    )
    args = parser.parse_args()
    project_root = _ROOT
    display_root = (
        args.root.expanduser().resolve()
        if args.root is not None
        else default_raw_snapshot_root(project_root)
    )
    meta = sync_openfoodfacts_snapshot(
        args.root,
        project_root=project_root,
        force=args.force,
    )
    if meta is None:
        print(f"No new snapshot written under {display_root} (already up to date).")
        return 0
    print(f"Recorded snapshot: {meta.file_path} mode={meta.mode} records={meta.record_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

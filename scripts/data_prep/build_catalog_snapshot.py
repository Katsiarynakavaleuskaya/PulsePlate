#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build catalog snapshot script (PR-7).

RU: Скрипт для построения SQLite snapshots из loaders.
EN: Script to build SQLite snapshots from loaders.

Usage:
    python scripts/data_prep/build_catalog_snapshot.py --loader carrefour_es --output data/catalog/snapshots/catalog_es_carrefour.sqlite
    python scripts/data_prep/build_catalog_snapshot.py --loader walmart_us --output data/catalog/snapshots/catalog_us_walmart.sqlite
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from core.catalog.loaders.carrefour_es import CarrefourESLoader
from core.catalog.loaders.walmart_us import WalmartUSLoader
from core.catalog.storage.sqlite_writer import write_snapshot


def main() -> None:
    """Build catalog snapshot from loader."""
    parser = argparse.ArgumentParser(description="Build catalog SQLite snapshot from loader")
    parser.add_argument(
        "--loader",
        choices=["carrefour_es", "walmart_us"],
        required=True,
        help="Loader to use",
    )
    parser.add_argument(
        "--raw-path",
        type=Path,
        required=True,
        help="Path to raw CSV file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output SQLite file path",
    )

    args = parser.parse_args()

    # Validate raw file exists
    if not args.raw_path.exists():
        print(f"Error: Raw file not found: {args.raw_path}", file=sys.stderr)
        sys.exit(1)

    if not args.raw_path.is_file():
        print(f"Error: Path is not a file: {args.raw_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Select loader using dict mapping (argparse choices already validate loader name)
        loader_mapping: dict[str, type[CarrefourESLoader | WalmartUSLoader]] = {
            "carrefour_es": CarrefourESLoader,
            "walmart_us": WalmartUSLoader,
        }
        loader_class = loader_mapping[args.loader]
        loader = loader_class(args.raw_path)

        # Load snapshot
        print(f"Loading catalog from {loader.source_name}...")
        try:
            snapshot = loader.load()
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: Failed to load catalog data: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Unexpected error during catalog loading: {e}", file=sys.stderr)
            sys.exit(1)

        print(
            f"Loaded: {len(snapshot.regions)} regions, {len(snapshot.stores)} stores, "
            f"{len(snapshot.skus)} SKUs, {len(snapshot.aliases)} aliases"
        )

        # Write to SQLite
        print(f"Writing to {args.output}...")
        try:
            write_snapshot(args.output, snapshot)
        except (ValueError, sqlite3.Error, OSError) as e:
            print(f"Error: Failed to write SQLite snapshot: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Unexpected error during snapshot write: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"✓ Snapshot written to {args.output}")

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

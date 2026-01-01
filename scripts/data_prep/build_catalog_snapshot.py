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

    # Select loader
    if args.loader == "carrefour_es":
        loader: CarrefourESLoader | WalmartUSLoader = CarrefourESLoader(args.raw_path)
    elif args.loader == "walmart_us":
        loader = WalmartUSLoader(args.raw_path)
    else:
        raise ValueError(f"Unknown loader: {args.loader}")

    # Load snapshot
    print(f"Loading catalog from {loader.source_name}...")
    snapshot = loader.load()
    print(
        f"Loaded: {len(snapshot.regions)} regions, {len(snapshot.stores)} stores, {len(snapshot.skus)} SKUs, {len(snapshot.aliases)} aliases"
    )

    # Write to SQLite
    print(f"Writing to {args.output}...")
    write_snapshot(args.output, snapshot)
    print(f"✓ Snapshot written to {args.output}")


if __name__ == "__main__":
    main()

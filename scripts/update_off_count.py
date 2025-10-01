#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path("cache/food_db")
VERS = ROOT / "database_versions.json"
SQLITE = ROOT / "off.sqlite"
CANDIDATES = [
    ROOT / "off.jsonl",
    ROOT / "off.ndjson",
    ROOT / "products.jsonl",
    ROOT / "products.csv",
]

# Configuration constants
SAMPLE_SIZE_MULTIPLIER_THRESHOLD = 2  # Adjust sample_size if it's more than 2x record_count


def count_sqlite(db: Path) -> int:
    if not db.exists():
        return 0
    try:
        conn = sqlite3.connect(str(db))
        try:
            cur = conn.execute("SELECT COUNT(*) FROM products")
            (n,) = cur.fetchone()
            return int(n or 0)
        finally:
            conn.close()
    except Exception:
        return 0


def count_lines(p: Path) -> int:
    n = 0
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        for _ in f:
            n += 1
    # для CSV вычтем хедер
    return max(0, n - 1) if p.suffix.lower() == ".csv" else n


def compute_total() -> int:
    total = count_sqlite(SQLITE)
    if total > 0:
        return total
    for p in CANDIDATES:
        if p.exists():
            total = count_lines(p)
            if total > 0:
                return total
    return 0


def calculate_checksum(data: dict) -> str:
    """Calculate checksum for data integrity."""
    # Create a copy without the checksum field to avoid circular dependency
    data_copy = {k: v for k, v in data.items() if k != "checksum"}
    # Convert to sorted JSON string for consistent hashing
    json_str = json.dumps(data_copy, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


def update_record_count(off: dict, total: int) -> tuple[int, int]:
    """Update record_count and return original values for comparison."""
    original_record_count = off.get("record_count", 0)
    off["record_count"] = int(total)
    return original_record_count, total


def update_sample_size(off: dict, total: int) -> tuple[int, int]:
    """Update sample_size if needed and return original values for comparison."""
    if "metadata" not in off:
        off["metadata"] = {}

    original_sample_size = off.get("metadata", {}).get("sample_size", 0)

    # Update sample_size whenever it no longer equals the freshly computed total
    if original_sample_size > total * SAMPLE_SIZE_MULTIPLIER_THRESHOLD:
        off["metadata"]["sample_size"] = total
        print(
            f"WARNING: Adjusted sample_size from {original_sample_size} to {total} to match record_count"
        )
    elif original_sample_size != total:
        off["metadata"]["sample_size"] = total

    return original_sample_size, off["metadata"]["sample_size"]


def update_json_file(meta: dict, off: dict) -> None:
    """Update the JSON file with new metadata."""
    # Remove old checksum before computing new one
    if "checksum" in off:
        del off["checksum"]
    off["checksum"] = calculate_checksum(off)
    meta["openfoodfacts"] = off
    VERS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if not VERS.exists():
        print(f"WARNING: {VERS} missing, creating default", file=sys.stderr)
        # Create default database_versions.json if it doesn't exist
        VERS.parent.mkdir(parents=True, exist_ok=True)
        default_meta = {
            "openfoodfacts": {
                "source": "openfoodfacts",
                "version": "unknown",
                "last_updated": "1970-01-01T00:00:00.000000+00:00",
                "record_count": 0,
                "checksum": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                "metadata": {
                    "update_type": "default",
                    "api_source": "Open Food Facts",
                    "sample_size": 0,
                },
            }
        }
        VERS.write_text(json.dumps(default_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    total = compute_total()

    # Validation: ensure record_count > 0 for non-empty ingestions
    if total == 0:
        print(
            "WARNING: No records found in database. This may indicate an empty cache.",
            file=sys.stderr,
        )
        print("Consider running the ingestion pipeline to populate the database.", file=sys.stderr)
        return 2

    try:
        meta = json.loads(VERS.read_text(encoding="utf-8"))
        off = meta.get("openfoodfacts") or {}

        # Update record count and sample size using helper functions
        original_record_count, new_record_count = update_record_count(off, total)
        original_sample_size, new_sample_size = update_sample_size(off, total)

        # Update JSON file with new metadata
        update_json_file(meta, off)

        print(f"OFF record_count updated from {original_record_count} to {new_record_count}")
        print(f"Checksum recalculated: {off['checksum'][:16]}...")

        return 0

    except Exception as e:
        print(f"ERROR: Failed to update database_versions.json: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json
import sys
import sqlite3

ROOT = Path("cache/food_db")
VERS = ROOT / "database_versions.json"
SQLITE = ROOT / "off.sqlite"
CANDIDATES = [
    ROOT / "off.jsonl",
    ROOT / "off.ndjson",
    ROOT / "products.jsonl",
    ROOT / "products.csv",
]


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


def main() -> int:
    if not VERS.exists():
        print(f"ERROR: {VERS} missing", file=sys.stderr)
        return 1
    total = compute_total()
    meta = json.loads(VERS.read_text(encoding="utf-8"))
    off = meta.get("openfoodfacts") or {}
    off["record_count"] = int(total)
    meta["openfoodfacts"] = off
    VERS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OFF record_count set to {total}")
    # код 0 — всё ок; 2 — данных не найдено (пусть валидатор потом уронит джоб)
    return 0 if total > 0 else 2


if __name__ == "__main__":
    sys.exit(main())

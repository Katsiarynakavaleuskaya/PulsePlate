#!/usr/bin/env python3
# RU: Удаляет точные дубликаты строк alias,canonical, сохраняя первое вхождение.
# EN: Removes duplicate alias,canonical rows, keeping the first occurrence.
import csv
import sys
from pathlib import Path

CSV_PATH = Path("data/food_aliases.csv")


def main() -> int:
    rows = list(csv.reader(CSV_PATH.open("r", encoding="utf-8")))
    if not rows:
        print("aliases: empty file")
        return 0
    header = rows[0]
    out = [header]
    seen = set()
    for r in rows[1:]:
        key = tuple(x.strip().lower() for x in r[:2])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(out)
    print(f"aliases: deduped, kept {len(out) - 1} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

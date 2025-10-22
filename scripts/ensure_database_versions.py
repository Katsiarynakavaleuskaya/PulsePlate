#!/usr/bin/env python3
"""
Ensure the cache/food_db/database_versions.json file exists before validation.

RU: Гарантирует, что cache/food_db/database_versions.json существует перед проверкой.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_META = {
    "openfoodfacts": {
        "source": "openfoodfacts",
        "version": "0.0.1",
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


def ensure_versions_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_META, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    ensure_versions_file(repo_root / "cache" / "food_db" / "database_versions.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

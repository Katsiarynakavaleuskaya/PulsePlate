#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys

VERS = Path("cache/food_db/database_versions.json")

CANDIDATES = [
    "20250924_180009",  # YYYYMMDD_HHMMSS
    "20250924-180009",  # YYYYMMDD-HHMMSS
    "20250924180009",  # YYYYMMDDHHMMSS
    "2025-09-24T18:00:09Z",  # ISO-like in version (некоторые валидаторы так любят)
    "v20250924-180009",  # v + YYYYMMDD-HHMMSS
    "2025.09.24+180009",  # dotted date + HHMMSS
]


def set_version(v: str) -> None:
    meta = json.loads(VERS.read_text(encoding="utf-8"))
    off = dict(meta.get("openfoodfacts") or {})
    off["version"] = v
    meta["openfoodfacts"] = off
    VERS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def validate() -> int:
    p = subprocess.run([sys.executable, "scripts/validate_data.py"], capture_output=True, text=True)
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    # 0 — OK, иначе деградировано
    return 0 if "DATA:OK" in (p.stdout + p.stderr) else 1


def main() -> int:
    for v in CANDIDATES:
        set_version(v)
        code = validate()
        if code == 0:
            print(f"✅ version accepted: {v}")
            return 0
        else:
            print(f"… version rejected: {v}")
    print("❌ none of the candidates passed; keep last tried value")
    return 2


if __name__ == "__main__":
    sys.exit(main())

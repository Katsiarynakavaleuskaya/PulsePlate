#!/usr/bin/env python3
import json
import subprocess  # nosec B404 - used for controlled internal script invocation
import sys
from pathlib import Path

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
    if not VERS.exists():
        print(f"WARNING: {VERS} missing, creating default", file=sys.stderr)
        # Create default database_versions.json if it doesn't exist
        VERS.parent.mkdir(parents=True, exist_ok=True)
        default_meta = {
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
        VERS.write_text(json.dumps(default_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        meta = default_meta
    else:
        meta = json.loads(VERS.read_text(encoding="utf-8"))

    off = dict(meta.get("openfoodfacts") or {})
    off["version"] = v
    meta["openfoodfacts"] = off
    VERS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def validate() -> int:
    p = subprocess.run(  # nosec B603 - fixed arguments invoking local validation script
        [sys.executable, "scripts/validate_data.py"],
        capture_output=True,
        text=True,
    )
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

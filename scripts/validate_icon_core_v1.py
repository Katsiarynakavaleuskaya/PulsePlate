#!/usr/bin/env python3
"""Validate canonical icon core v1.0 directory structure.

Default mode is intentionally lightweight:
- fail on unexpected files in core/v1.0
- require governance files (README.md + meta.json)

Strict mode additionally requires canonical masters to exist.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CORE_DIR = Path("assets/brand/icon/core/v1.0")

GOVERNANCE_REQUIRED = {"README.md", "meta.json"}

CANONICAL_MASTER_SET = {
    "icon_core_v1.svg",
    "icon_core_v1_1024.png",
    "icon_core_v1_60.png",
}

ALLOWED_FILES = GOVERNANCE_REQUIRED | CANONICAL_MASTER_SET


def validate(strict: bool) -> list[str]:
    errors: list[str] = []

    if not CORE_DIR.exists():
        return [f"missing directory: {CORE_DIR}"]
    if not CORE_DIR.is_dir():
        return [f"not a directory: {CORE_DIR}"]

    files = sorted(p.name for p in CORE_DIR.iterdir() if p.is_file())
    file_set = set(files)

    unexpected = sorted(file_set - ALLOWED_FILES)
    if unexpected:
        errors.append(f"unexpected files in {CORE_DIR}: {', '.join(unexpected)}")

    missing_governance = sorted(GOVERNANCE_REQUIRED - file_set)
    if missing_governance:
        errors.append(f"missing required governance files: {', '.join(missing_governance)}")

    if strict:
        missing_masters = sorted(CANONICAL_MASTER_SET - file_set)
        if missing_masters:
            errors.append(f"missing canonical masters (strict mode): {', '.join(missing_masters)}")

    meta_path = CORE_DIR / "meta.json"
    if meta_path.exists():
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                meta = json.load(f)
            if not isinstance(meta, dict):
                errors.append("meta.json must be a JSON object")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid meta.json: {exc}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate icon core v1.0 directory structure.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require canonical master files to exist.",
    )
    args = parser.parse_args()

    errors = validate(strict=args.strict)
    if errors:
        for line in errors:
            print(line)
        raise SystemExit(1)

    mode = "strict" if args.strict else "default"
    print(f"OK: icon core v1.0 structure valid ({mode} mode)")


if __name__ == "__main__":
    main()

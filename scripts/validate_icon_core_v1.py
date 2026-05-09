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

REQUIRED_META_TOP_LEVEL_FIELDS = {
    "contract_id",
    "version",
    "master_policy",
    "figma_source_type",
    "figma_design_url",
    "figma_file_key",
    "figma_node_id",
    "assets",
    "hashes",
}

LOCK_PLACEHOLDER_VALUE = "TBD_AFTER_WINNER_LOCK"


ALLOWED_FILES = GOVERNANCE_REQUIRED | CANONICAL_MASTER_SET
REQUIRED_ASSET_KEYS = {
    "svg_master",
    "png_master_1024",
    "png_master_60",
    "png_derived_120",
    "png_derived_32",
    "png_derived_24",
}
REQUIRED_HASH_KEYS = {
    "master_svg_sha256",
    "master_png_1024_sha256",
    "master_png_60_sha256",
    "silhouette_mask_sha256_1024",
    "silhouette_mask_sha256_60",
}


def _find_placeholder_values(data: dict[str, object]) -> list[str]:
    """Return flattened placeholder-like values from known lock fields."""

    placeholders: list[str] = []
    for key in ("figma_design_url", "figma_file_key", "figma_node_id"):
        value = data.get(key)
        if value == LOCK_PLACEHOLDER_VALUE:
            placeholders.append(f"{key}={LOCK_PLACEHOLDER_VALUE}")

    assets = data.get("assets")
    if isinstance(assets, dict):
        for key, value in assets.items():
            if value == LOCK_PLACEHOLDER_VALUE:
                placeholders.append(f"assets.{key}={LOCK_PLACEHOLDER_VALUE}")

    hashes = data.get("hashes")
    if isinstance(hashes, dict):
        for key, value in hashes.items():
            if value == LOCK_PLACEHOLDER_VALUE:
                placeholders.append(f"hashes.{key}={LOCK_PLACEHOLDER_VALUE}")

    return placeholders


def validate(strict: bool, *, require_lock_values: bool = False) -> list[str]:
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
                return errors
        except json.JSONDecodeError as exc:
            errors.append(f"invalid meta.json: {exc}")
            return errors

        missing_meta_fields = sorted(REQUIRED_META_TOP_LEVEL_FIELDS - set(meta.keys()))
        if missing_meta_fields:
            errors.append(
                f"meta.json missing required top-level fields: {', '.join(missing_meta_fields)}"
            )

        assets = meta.get("assets")
        if not isinstance(assets, dict):
            errors.append("meta.json must define assets as an object")
        else:
            missing_asset_keys = sorted(REQUIRED_ASSET_KEYS - set(assets.keys()))
            if missing_asset_keys:
                errors.append(
                    f"meta.json assets missing required keys: {', '.join(missing_asset_keys)}"
                )

        hashes = meta.get("hashes")
        if not isinstance(hashes, dict):
            errors.append("meta.json must define hashes as an object")
        else:
            missing_hash_keys = sorted(REQUIRED_HASH_KEYS - set(hashes.keys()))
            if missing_hash_keys:
                errors.append(
                    f"meta.json hashes missing required keys: {', '.join(missing_hash_keys)}"
                )

        if require_lock_values:
            placeholders = _find_placeholder_values(meta)
            if placeholders:
                errors.append("meta.json lock placeholders found: " + ", ".join(placeholders))
        return errors

    else:
        errors.append("missing required governance file: meta.json")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate icon core v1.0 directory structure.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require canonical master files to exist.",
    )
    parser.add_argument(
        "--require-lock-values",
        action="store_true",
        help="Require TBD lock placeholders to be replaced with concrete values.",
    )
    args = parser.parse_args()

    errors = validate(strict=args.strict, require_lock_values=args.require_lock_values)
    if errors:
        for line in errors:
            print(line)
        raise SystemExit(1)

    mode = "strict" if args.strict else "default"
    print(f"OK: icon core v1.0 structure valid ({mode} mode)")


if __name__ == "__main__":
    main()

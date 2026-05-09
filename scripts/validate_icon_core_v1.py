#!/usr/bin/env python3
"""Validate canonical icon core v1.0 directory structure.

Default mode is intentionally lightweight:
- fail on unexpected files in core/v1.0
- require governance files (README.md + meta.json)

Strict mode validates required metadata fields and canonical asset paths.
Canonical files and confirmed lock values are required only when explicitly
requested because the current repo contract may still be pre-lock.
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
CANONICAL_DERIVED_SET = {
    "icon_core_v1_120.png",
    "icon_core_v1_32.png",
    "icon_core_v1_24.png",
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
PLACEHOLDER_VALUES = {
    "",
    "TBD",
    "TODO",
    "UNKNOWN",
    "UNSPECIFIED",
    LOCK_PLACEHOLDER_VALUE,
}


ALLOWED_FILES = GOVERNANCE_REQUIRED | CANONICAL_MASTER_SET | CANONICAL_DERIVED_SET
REQUIRED_ASSET_KEYS = {
    "svg_master",
    "png_master_1024",
    "png_master_60",
    "png_derived_120",
    "png_derived_32",
    "png_derived_24",
}
REQUIRED_ASSET_PATHS = {
    "svg_master": "assets/brand/icon/core/v1.0/icon_core_v1.svg",
    "png_master_1024": "assets/brand/icon/core/v1.0/icon_core_v1_1024.png",
    "png_master_60": "assets/brand/icon/core/v1.0/icon_core_v1_60.png",
    "png_derived_120": "assets/brand/icon/core/v1.0/icon_core_v1_120.png",
    "png_derived_32": "assets/brand/icon/core/v1.0/icon_core_v1_32.png",
    "png_derived_24": "assets/brand/icon/core/v1.0/icon_core_v1_24.png",
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
        if not _is_concrete_lock_value(value):
            placeholders.append(f"{key}={value!r}")

    assets = data.get("assets")
    if isinstance(assets, dict):
        for key, value in assets.items():
            if not _is_concrete_lock_value(value):
                placeholders.append(f"assets.{key}={value!r}")

    hashes = data.get("hashes")
    if isinstance(hashes, dict):
        for key, value in hashes.items():
            if not _is_concrete_hash_value(value):
                placeholders.append(f"hashes.{key}={value!r}")

    return placeholders


def _is_concrete_lock_value(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    return bool(normalized) and normalized.upper() not in PLACEHOLDER_VALUES


def _is_concrete_hash_value(value: object) -> bool:
    if not _is_concrete_lock_value(value):
        return False
    normalized = str(value).strip()
    return normalized.startswith("sha256:") and len(normalized) > len("sha256:")


def validate(
    *,
    strict: bool = False,
    require_lock_values: bool = False,
    require_canonical_masters: bool = False,
) -> list[str]:
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

    if require_canonical_masters:
        missing_masters = sorted(CANONICAL_MASTER_SET - file_set)
        if missing_masters:
            errors.append(
                "missing canonical masters (require-canonical-masters mode): "
                + ", ".join(missing_masters)
            )

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

        validate_meta_contract = strict or require_lock_values
        if validate_meta_contract:
            missing_meta_fields = sorted(REQUIRED_META_TOP_LEVEL_FIELDS - set(meta.keys()))
            if missing_meta_fields:
                errors.append(
                    "meta.json missing required top-level fields: " + ", ".join(missing_meta_fields)
                )

            if "assets" in meta:
                assets = meta["assets"]
                if not isinstance(assets, dict):
                    errors.append("meta.json must define assets as an object")
                else:
                    missing_asset_keys = sorted(REQUIRED_ASSET_KEYS - set(assets.keys()))
                    if missing_asset_keys:
                        errors.append(
                            "meta.json assets missing required keys: "
                            + ", ".join(missing_asset_keys)
                        )
                    for key, expected_path in sorted(REQUIRED_ASSET_PATHS.items()):
                        if assets.get(key) != expected_path:
                            errors.append(f"meta.json assets.{key} must be {expected_path}")

            if "hashes" in meta:
                hashes = meta["hashes"]
                if not isinstance(hashes, dict):
                    errors.append("meta.json must define hashes as an object")
                else:
                    missing_hash_keys = sorted(REQUIRED_HASH_KEYS - set(hashes.keys()))
                    if missing_hash_keys:
                        errors.append(
                            "meta.json hashes missing required keys: "
                            + ", ".join(missing_hash_keys)
                        )

        if require_lock_values:
            placeholders = _find_placeholder_values(meta)
            if placeholders:
                errors.append("meta.json lock placeholders found: " + ", ".join(placeholders))
        return errors

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate icon core v1.0 directory structure.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Validate required metadata fields and canonical asset paths.",
    )
    parser.add_argument(
        "--require-canonical-masters",
        action="store_true",
        help="Require canonical master asset files to exist.",
    )
    parser.add_argument(
        "--require-lock-values",
        action="store_true",
        help="Require TBD lock placeholders to be replaced with concrete values.",
    )
    args = parser.parse_args()

    errors = validate(
        strict=args.strict,
        require_lock_values=args.require_lock_values,
        require_canonical_masters=args.require_canonical_masters,
    )
    if errors:
        for line in errors:
            print(line)
        raise SystemExit(1)

    mode = "strict" if args.strict else "default"
    print(f"OK: icon core v1.0 structure valid ({mode} mode)")


if __name__ == "__main__":
    main()

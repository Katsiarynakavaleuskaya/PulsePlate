#!/usr/bin/env python3
"""Design invariant guard for Figma export contracts.

This guard enforces:
- palette drift prevention,
- token parity with CSS source-of-truth,
- core SVG lock hash integrity,
- manifest export metadata integrity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")
VERSION_RE = re.compile(r"^v\d+\.\d+$")
LOCK_TYPES = {"L1", "L2", "L3", "L4"}
CONTRACT_STATES = {"bootstrap", "locked"}
REQUIRED_EXPORT_FIELDS = (
    "path",
    "figma_url",
    "node_id",
    "version",
    "lock_type",
    "palette_hexes",
)


def _norm_hex(value: str) -> str:
    return value.strip().upper()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_css_hexes(css_path: Path) -> set[str]:
    text = css_path.read_text(encoding="utf-8")
    return {_norm_hex(match.group(0)) for match in HEX_COLOR_RE.finditer(text)}


def _as_dict(value: Any, field_name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{field_name} must be an object")
        return {}
    return value


def _as_list(value: Any, field_name: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{field_name} must be an array")
        return []
    return value


def validate_manifest(manifest: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []

    manifest_version = manifest.get("manifest_version")
    if not isinstance(manifest_version, str) or not manifest_version:
        errors.append("manifest_version must be a non-empty string")

    contract_status = manifest.get("contract_status")
    if contract_status not in CONTRACT_STATES:
        errors.append("contract_status must be one of: bootstrap, locked")

    token_source = manifest.get("token_source")
    if not isinstance(token_source, str) or not token_source:
        errors.append("token_source must be a non-empty string path")
        token_path = None
    else:
        token_path = repo_root / token_source
        if not token_path.exists():
            errors.append(f"token_source path not found: {token_source}")
            token_path = None

    allowed_palette_raw = _as_list(
        manifest.get("allowed_palette_hex"), "allowed_palette_hex", errors
    )
    allowed_palette: set[str] = set()
    for item in allowed_palette_raw:
        if not isinstance(item, str) or not HEX_COLOR_RE.fullmatch(item):
            errors.append(f"allowed_palette_hex contains invalid hex value: {item!r}")
            continue
        allowed_palette.add(_norm_hex(item))

    if not allowed_palette:
        errors.append("allowed_palette_hex must contain at least one hex color")

    if token_path is not None:
        css_hexes = _extract_css_hexes(token_path)
        for hex_value in sorted(allowed_palette):
            if hex_value not in css_hexes:
                errors.append(
                    f"token drift: allowed palette color {hex_value} is not present in {token_source}"
                )

    core_lock = _as_dict(manifest.get("core_lock"), "core_lock", errors)
    core_path_value = core_lock.get("path")
    core_sha_value = core_lock.get("svg_sha256")
    core_lock_type = core_lock.get("lock_type")
    core_figma_url = core_lock.get("figma_url")
    core_version = core_lock.get("version")
    core_node_id = core_lock.get("node_id")

    if contract_status == "locked":
        required_core_fields = {
            "path": core_path_value,
            "svg_sha256": core_sha_value,
            "lock_type": core_lock_type,
            "figma_url": core_figma_url,
            "version": core_version,
            "node_id": core_node_id,
        }
        missing_core = [key for key, value in required_core_fields.items() if not value]
        if missing_core:
            errors.append(
                f"core_lock missing required fields for locked state: {', '.join(missing_core)}"
            )

        if core_lock_type and core_lock_type != "L4":
            errors.append("core_lock.lock_type must be L4 in locked state")

    if (
        isinstance(core_figma_url, str)
        and core_figma_url
        and "figma.com/design/" not in core_figma_url
    ):
        errors.append("core_lock.figma_url must reference figma.com/design/")
    if isinstance(core_version, str) and core_version and not VERSION_RE.fullmatch(core_version):
        errors.append("core_lock.version must match v<major>.<minor> format")
    if isinstance(core_lock_type, str) and core_lock_type and core_lock_type not in LOCK_TYPES:
        errors.append("core_lock.lock_type must be one of L1/L2/L3/L4")

    if isinstance(core_path_value, str) and core_path_value:
        should_enforce_core_hash = contract_status == "locked" or bool(core_sha_value)
        if should_enforce_core_hash:
            core_path = repo_root / core_path_value
            if not core_path.exists():
                errors.append(f"core mutation check failed: file not found: {core_path_value}")
            elif isinstance(core_sha_value, str) and core_sha_value:
                computed = _file_sha256(core_path)
                if computed.lower() != core_sha_value.lower():
                    errors.append(
                        "core mutation check failed: svg_sha256 mismatch "
                        f"(manifest={core_sha_value}, actual={computed})"
                    )
            elif contract_status == "locked":
                errors.append(
                    "core mutation check failed: core_lock.svg_sha256 is empty in locked state"
                )

    exports = _as_list(manifest.get("exports"), "exports", errors)
    if contract_status == "locked" and not exports:
        errors.append("manifest integrity: locked state requires at least one export entry")

    for idx, export in enumerate(exports):
        prefix = f"exports[{idx}]"
        if not isinstance(export, dict):
            errors.append(f"{prefix} must be an object")
            continue

        for field in REQUIRED_EXPORT_FIELDS:
            value = export.get(field)
            if value in (None, "", []):
                errors.append(f"manifest integrity: {prefix}.{field} is required")

        lock_type = export.get("lock_type")
        if lock_type and lock_type not in LOCK_TYPES:
            errors.append(f"manifest integrity: {prefix}.lock_type must be one of L1/L2/L3/L4")

        version = export.get("version")
        if isinstance(version, str) and version and not VERSION_RE.fullmatch(version):
            errors.append(f"manifest integrity: {prefix}.version must match v<major>.<minor>")

        figma_url = export.get("figma_url")
        if isinstance(figma_url, str) and figma_url and "figma.com/design/" not in figma_url:
            errors.append(
                f"manifest integrity: {prefix}.figma_url must reference figma.com/design/"
            )

        palette_hexes_raw = export.get("palette_hexes")
        palette_hexes = _as_list(palette_hexes_raw, f"{prefix}.palette_hexes", errors)
        for palette_hex in palette_hexes:
            if not isinstance(palette_hex, str) or not HEX_COLOR_RE.fullmatch(palette_hex):
                errors.append(
                    f"palette drift: {prefix}.palette_hexes contains invalid hex: {palette_hex!r}"
                )
                continue
            normalized = _norm_hex(palette_hex)
            if normalized not in allowed_palette:
                errors.append(
                    f"palette drift: {prefix}.palette_hexes contains disallowed color {normalized}"
                )

        export_path_value = export.get("path")
        if isinstance(export_path_value, str) and export_path_value:
            export_path = repo_root / export_path_value
            if not export_path.exists():
                errors.append(f"manifest integrity: {prefix}.path not found: {export_path_value}")
            else:
                export_sha = export.get("sha256")
                if export_sha:
                    if not isinstance(export_sha, str):
                        errors.append(f"manifest integrity: {prefix}.sha256 must be a string")
                    else:
                        actual_sha = _file_sha256(export_path)
                        if actual_sha.lower() != export_sha.lower():
                            errors.append(
                                f"manifest integrity: {prefix}.sha256 mismatch "
                                f"(manifest={export_sha}, actual={actual_sha})"
                            )
                elif contract_status == "locked":
                    errors.append(
                        f"manifest integrity: {prefix}.sha256 is required in locked state"
                    )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Run design invariant guard checks.")
    parser.add_argument(
        "--manifest",
        default="docs/design/figma-manifest.json",
        help="Path to figma manifest JSON.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    manifest_path = repo_root / args.manifest
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {args.manifest}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("manifest root must be a JSON object")

    errors = validate_manifest(data, repo_root=repo_root)
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)

    exports = data.get("exports", [])
    print(f"OK: design guard passed (manifest={args.manifest}, exports={len(exports)})")


if __name__ == "__main__":
    main()

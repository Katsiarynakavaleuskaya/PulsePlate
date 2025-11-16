#!/usr/bin/env python3
"""
Lightweight data validator for CI.

RU: Быстрые проверки целостности данных (CSV/JSON) без сетевых вызовов.
EN: Fast CI checks for local data consistency (CSV/JSON) without network calls.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

_VERSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),  # YYYY-MM-DD
    re.compile(r"^v?\d+(?:\.\d+){1,2}$"),  # semantic version, optional leading v
    re.compile(r"^\d{8}_\d{6}$"),  # YYYYMMDD_HHMMSS timestamp format
)


def _is_valid_version(value: str) -> bool:
    """Check that the version string matches an allowed pattern."""
    return any(pattern.match(value) for pattern in _VERSION_PATTERNS)


def validate_food_aliases(file_path: Path) -> list[str]:
    errors: list[str] = []
    if not file_path.exists():
        errors.append(f"Missing file: {file_path}")
        return errors
    try:
        with file_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required = {"alias", "canonical"}
            if not required.issubset(reader.fieldnames or set()):
                errors.append(
                    f"{file_path}: required headers {sorted(required)} not found; got {reader.fieldnames}"
                )
            seen: set[tuple[str, str]] = set()
            for i, row in enumerate(reader, start=2):
                alias = (row.get("alias") or "").strip()
                canonical = (row.get("canonical") or "").strip()
                if not alias or not canonical:
                    errors.append(f"{file_path}:{i} empty alias/canonical")
                key = (alias.lower(), canonical.lower())
                if key in seen:
                    errors.append(f"{file_path}:{i} duplicate mapping {alias} -> {canonical}")
                else:
                    seen.add(key)
    except Exception as e:  # pragma: no cover
        errors.append(f"{file_path}: exception {e}")
    return errors


def validate_cache_versions(file_path: Path) -> list[str]:
    errors: list[str] = []
    if not file_path.exists():
        # Create default cache file if missing (for CI environments)
        print(f"WARNING: {file_path} missing, creating default", file=sys.stderr)
        file_path.parent.mkdir(parents=True, exist_ok=True)
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
        file_path.write_text(
            json.dumps(default_meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Created default {file_path}", file=sys.stderr)
        # Fail CI after creating default file to surface missing cache condition
        raise ValueError(
            f"Missing cache file {file_path} - created default but validation should fail"
        )
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            errors.append(f"{file_path}: expected JSON object, got {type(data)!r}")
        for k, v in data.items():
            if not isinstance(k, str) or not k:
                errors.append(f"{file_path}: invalid key {k!r}")
                continue

            if isinstance(v, (str, int)):
                version_value = str(v)
                if not _is_valid_version(version_value):
                    errors.append(
                        f"{file_path}: unsupported version format for {k}: {version_value!r}"
                    )
                continue

            if isinstance(v, dict):
                version_value = v.get("version", "")
                if not isinstance(version_value, str):
                    errors.append(
                        f"{file_path}: missing or invalid version field for {k}: {version_value!r}"
                    )
                elif not _is_valid_version(version_value):
                    errors.append(
                        f"{file_path}: unsupported version format for {k}: {version_value!r}"
                    )
                continue

            errors.append(f"{file_path}: invalid version entry for {k}: {v!r}")
    except json.JSONDecodeError as e:
        errors.append(f"{file_path}: invalid JSON: {e}")
    except Exception as e:  # pragma: no cover
        errors.append(f"{file_path}: exception {e}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate data files (CSV/JSON)")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON result instead of text messages",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    issues: list[str] = []
    issues += validate_food_aliases(repo_root / "data" / "food_aliases.csv")
    try:
        issues += validate_cache_versions(
            repo_root / "cache" / "food_db" / "database_versions.json"
        )
    except ValueError as e:
        # Preserve JSON contract: collect error instead of exiting
        issues.append(str(e))
    except Exception as e:  # pragma: no cover
        issues.append(str(e))

    if args.json:
        # Structured JSON output (to stdout only)
        result = {
            "success": len(issues) == 0,
            "issues": issues,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1

    # Legacy text output (backward compatible)
    if issues:
        print("DATA VALIDATION: DEGRADED", file=sys.stderr)
        for msg in issues:
            print(f"- {msg}", file=sys.stderr)
        return 1
    print("DATA VALIDATION: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Lightweight data validator for CI.

RU: Быстрые проверки целостности данных (CSV/JSON) без сетевых вызовов.
EN: Fast CI checks for local data consistency (CSV/JSON) without network calls.
"""
from __future__ import annotations

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
        # Not fatal for CI; treat as warning-equivalent error
        errors.append(f"Missing cache file: {file_path}")
        return errors
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
    repo_root = Path(__file__).resolve().parents[1]
    issues: list[str] = []
    issues += validate_food_aliases(repo_root / "data" / "food_aliases.csv")
    issues += validate_cache_versions(repo_root / "cache" / "food_db" / "database_versions.json")

    if issues:
        print("DATA VALIDATION: DEGRADED", file=sys.stderr)
        for msg in issues:
            print(f"- {msg}", file=sys.stderr)
        return 1
    print("DATA VALIDATION: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

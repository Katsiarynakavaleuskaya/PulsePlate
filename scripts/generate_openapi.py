#!/usr/bin/env python3
"""
Generate OpenAPI schema from canonical FastAPI entrypoint and write it to:
  frontend/src/api/openapi.json

Canonical entrypoint: app.main:app (bootstrap + metrics applied).
This file must be the single source of truth for OpenAPI generation in CI and locally.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Union

# Keys where list order is semantically significant (do not sort)
_DO_NOT_SORT_LIST_KEYS = {
    "required",
    "enum",
    "allOf",
    "anyOf",
    "oneOf",
    "prefixItems",
    "examples",
}


def _normalize_dict_recursive(  # noqa: ANN401, ANN101
    obj: Union[dict[str, Any], list[Any], Any],  # noqa: ANN401
    *,
    parent_key: str | None = None,
) -> Union[dict[str, Any], list[Any], Any]:  # noqa: ANN401
    """Recursively normalize dicts for deterministic OpenAPI JSON output.

    Rules:
    - Dict keys are always sorted.
    - Lists are normalized recursively, but NOT re-ordered for semantically ordered keys
      (required/enum/allOf/anyOf/oneOf/etc).
    """
    if isinstance(obj, dict):
        result: dict[str, Any] = {
            k: _normalize_dict_recursive(v, parent_key=k) for k, v in sorted(obj.items())
        }
        return result
    if isinstance(obj, list):
        normalized: list[Any] = [_normalize_dict_recursive(x, parent_key=parent_key) for x in obj]
        if parent_key in _DO_NOT_SORT_LIST_KEYS:
            return normalized
        # Optional: keep ONLY scalar-list sorting (safe-ish) for non-semantic keys
        if all(isinstance(x, (str, int, float, bool, type(None))) for x in normalized):
            normalized.sort(key=lambda x: (type(x).__name__, str(x)))
        return normalized
    return obj


def normalize_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Make FastAPI OpenAPI output deterministic by normalizing all dicts/lists.

    This recursively sorts all dictionary keys and normalizes list order
    to ensure identical output across runs.
    """
    # First pass: normalize structure recursively
    normalized_raw = _normalize_dict_recursive(schema)

    # Second pass: special handling for OpenAPI-specific structures
    if not isinstance(normalized_raw, dict):
        return schema  # Fallback if normalization failed

    normalized: dict[str, Any] = normalized_raw

    # Sort paths by path string
    paths = normalized.get("paths")
    if isinstance(paths, dict):
        normalized["paths"] = dict(sorted(paths.items()))

    # Sort top-level tags by name
    tags = normalized.get("tags")
    if isinstance(tags, list):
        tags.sort(key=lambda t: (t.get("name") or "") if isinstance(t, dict) else str(t))

    # Sort operations within each path
    paths = normalized.get("paths")
    if isinstance(paths, dict):
        for path_key, ops in paths.items():
            if isinstance(ops, dict):
                # Sort operations by method (get, post, etc.)
                normalized["paths"][path_key] = dict(sorted(ops.items()))

    return normalized


def main() -> int:
    # Make OpenAPI generation deterministic across dev/CI.
    #
    # IMPORTANT (PR-631): This is FULL schema mode.
    # OpenAPI generation must not rely on schema-only router skips or import-time ORM hacks.
    #
    # CI uses APP_ENV=test/ENVIRONMENT=test, so we align here.
    os.environ["APP_ENV"] = "test"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["ENABLE_TEST_ROUTES"] = "1"
    # Enable feature-flagged routers during schema generation to produce a full schema.
    # RU: Включаем фичи для полной схемы (только для генерации OpenAPI).
    # EN: Enable features for full OpenAPI schema generation (generator-only).
    os.environ["FEATURE_PREMIUM_WEEK_ENABLED"] = "true"
    os.environ["FEATURE_BMI_PRO_ENABLED"] = "true"
    os.environ["BUSINESS_MODULE_ENABLED"] = "true"

    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "frontend" / "src" / "api" / "openapi.json"

    # IMPORTANT: canonical entrypoint (applies register_metrics bootstrap)
    from app.main import (
        app,
    )  # noqa: WPS433, ANN401 (intentional runtime import, dynamic typing needed)

    schema = app.openapi()
    schema = normalize_openapi_schema(schema)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            schema,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"✅ OpenAPI schema generated: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

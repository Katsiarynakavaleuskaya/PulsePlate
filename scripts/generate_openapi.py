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
    # Make OpenAPI generation deterministic across dev/CI
    # Enable schema-only mode to avoid SQLAlchemy model double-loading
    # This prevents "Table already defined" errors and ensures deterministic schema
    os.environ["PULSEPLATE_OPENAPI"] = "1"

    # Hard pin environment and feature flags for schema-only mode
    # IMPORTANT: This is schema-only mode (temporary). Premium/pro routers are disabled
    # because they import SQLAlchemy models at module level, causing double-load errors.
    # Follow-up PR-509: eliminate import-time ORM dependencies to enable full schema.
    # CI uses APP_ENV=test/ENVIRONMENT=test, so we align here
    os.environ["APP_ENV"] = "test"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["ENABLE_TEST_ROUTES"] = "1"
    # Disable routers that import SQLAlchemy models at module level (temporary)
    # These will be re-enabled in PR-509 after moving models to lazy imports or app/schemas
    os.environ["FEATURE_PREMIUM_WEEK_ENABLED"] = "false"
    os.environ["FEATURE_BMI_PRO_ENABLED"] = "false"
    os.environ["BUSINESS_MODULE_ENABLED"] = "false"

    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "frontend" / "src" / "api" / "openapi.json"

    # IMPORTANT: canonical entrypoint (applies register_metrics bootstrap)
    # PULSEPLATE_OPENAPI=1 must be set BEFORE importing app to prevent SQLAlchemy double-loading
    from app.main import (
        app,
    )  # noqa: WPS433, ANN401 (intentional runtime import, dynamic typing needed)

    schema = app.openapi()
    schema = normalize_openapi_schema(schema)

    # Add explicit marker for schema-only mode (transparency for reviewers/consumers)
    if "info" not in schema:
        schema["info"] = {}
    schema["info"]["x-openapi-mode"] = "schema-only"
    schema["info"]["x-excluded-routers"] = ["premium_week", "pro"]
    if "description" in schema["info"]:
        schema["info"]["description"] += (
            "\n\n⚠️ **Schema-only mode**: Premium/pro routers excluded due to import-time ORM dependencies. "
            "Full schema will be restored in PR-509 after eliminating import-time ORM deps."
        )
    else:
        schema["info"]["description"] = (
            "⚠️ **Schema-only mode**: Premium/pro routers excluded due to import-time ORM dependencies. "
            "Full schema will be restored in PR-509 after eliminating import-time ORM deps."
        )

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

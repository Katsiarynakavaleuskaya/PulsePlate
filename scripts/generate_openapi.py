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
from typing import Any


def _sort_list_in_place(value: Any) -> None:
    """Sort simple scalar lists deterministically."""
    if isinstance(value, list) and all(
        isinstance(x, (str, int, float, bool, type(None))) for x in value
    ):
        value.sort(key=lambda x: (str(type(x)), str(x)))


def _normalize_dict_recursive(obj: Any) -> Any:
    """Recursively normalize dicts and lists for deterministic output."""
    if isinstance(obj, dict):
        # Sort dict keys and normalize values recursively
        return {k: _normalize_dict_recursive(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        # For lists, normalize items and try to sort if all are comparable
        normalized = [_normalize_dict_recursive(item) for item in obj]
        # Try to sort if all items are simple types
        if all(isinstance(x, (str, int, float, bool, type(None))) for x in normalized):
            normalized.sort(key=lambda x: (str(type(x)), str(x)))
        elif all(isinstance(x, dict) for x in normalized):
            # Sort dicts by their string representation (for tags, etc.)
            normalized.sort(key=lambda x: json.dumps(x, sort_keys=True))
        return normalized
    else:
        return obj


def normalize_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Make FastAPI OpenAPI output deterministic by normalizing all dicts/lists.

    This recursively sorts all dictionary keys and normalizes list order
    to ensure identical output across runs.
    """
    # First pass: normalize structure recursively
    normalized = _normalize_dict_recursive(schema)

    # Second pass: special handling for OpenAPI-specific structures
    if isinstance(normalized, dict):
        # Sort paths by path string
        paths = normalized.get("paths")
        if isinstance(paths, dict):
            normalized["paths"] = dict(sorted(paths.items()))

        # Sort top-level tags by name
        tags = normalized.get("tags")
        if isinstance(tags, list):
            tags.sort(
                key=lambda t: (t.get("name") or "") if isinstance(t, dict) else str(t)
            )

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
    from app.main import app  # noqa: WPS433 (intentional runtime import)

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

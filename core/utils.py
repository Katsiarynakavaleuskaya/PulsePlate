"""Core utilities shared across endpoints.

- get_activity_factor: unified mapping for activity multipliers.
- resolve_attr: safe dynamic attribute resolver respecting test-time patches.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Iterable, Optional


def get_activity_factor(activity: str) -> float:
    """Return standard activity multiplier.

    Values match usage across premium endpoints and tests.
    Defaults to "moderate" (1.55) if unknown.
    """
    mapping = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    return mapping.get(str(activity), 1.55)


def resolve_attr(name: str, local_default: Any, candidates: Optional[Iterable[Any]] = None) -> Any:
    """Resolve attribute by searching candidate modules before falling back.

    Args:
        name: attribute name to retrieve
        local_default: value to return if not found in candidates
        candidates: optional iterable of modules or module names to search.
            If None, defaults to [sys.modules.get("app"),
            sys.modules.get("_app_top_module")]

    Returns:
        Resolved attribute value or local_default when not found.
    """
    if candidates is None:
        candidates = [sys.modules.get("app"), sys.modules.get("_app_top_module")]
    for m in candidates:
        try:
            if m is None:
                continue
            # If candidate is a module name string, fetch module object
            if isinstance(m, str):
                m = sys.modules.get(m)
                if m is None:
                    continue

            # Prefer explicit attributes to avoid Mock auto-created attrs.
            dct = getattr(m, "__dict__", None)
            if isinstance(dct, dict) and name in dct:
                return dct[name]

            # Avoid triggering unittest.mock auto-creation of attributes
            # If it's a mock-like object and attribute isn't explicitly set, skip it
            try:
                is_mock_like = (
                    getattr(m, "_mock_children", None) is not None
                    or m.__class__.__name__ in {"Mock", "MagicMock", "AsyncMock"}
                    or getattr(m, "__module__", "").startswith("unittest.mock")
                )
            except Exception:
                is_mock_like = False
            if is_mock_like:
                # Only return values that are explicitly present in __dict__ for mocks
                # If not present, continue searching other candidates
                continue

            # Fallback: if it's a real module, allow getattr
            if isinstance(m, types.ModuleType) and hasattr(m, name):
                return getattr(m, name)
        except Exception:  # nosec B112
            # Ignore any errors from broken modules; continue searching
            continue
    return local_default


# Constant for marking untestable edge cases in coverage reports
# Usage: add comment "# pragma: no cover" after lines that are difficult to test
UNTESTABLE_EDGE_CASE = None

"""Core utilities shared across endpoints.

- get_activity_factor: unified mapping for activity multipliers.
- resolve_attr: safe dynamic attribute resolver respecting test-time patches.
"""

from __future__ import annotations

import logging
import sys
import types
from typing import Any, Iterable, Optional

from core.bmr import PAL_FACTORS

logger = logging.getLogger(__name__)


def get_activity_factor(activity: str) -> float:
    """Return standard activity multiplier.

    Values match usage across premium endpoints and tests.
    Defaults to "moderate" (1.55) if unknown.
    """
    # RU: Держим один источник истины для коэффициентов активности в `core.bmr`.
    # EN: Keep a single source of truth for PAL factors in `core.bmr`.
    key = str(activity).strip().lower()
    return PAL_FACTORS.get(key, PAL_FACTORS["moderate"])


def _resolve_module_candidate(candidate: Any) -> Optional[Any]:
    """Resolve a candidate to a module/object, handling string names and None values.

    Safely converts string module names to actual module objects from sys.modules.
    For non-string candidates, returns the candidate as-is (preserving original behavior
    that allows any object type, not just ModuleType).
    Handles defensive guards for __getattribute__ hooks that may raise exceptions
    during type checking.

    Args:
        candidate: Module object, any object, string module name, or None

    Returns:
        Resolved module/object, or None if candidate is None, is a string that cannot
        be resolved, or raises exception during type checking
    """
    if candidate is None:
        return None

    # Check if candidate is string, handling exceptions during type checking
    try:
        is_string = isinstance(candidate, str)
    except (TypeError, AttributeError):
        # If type checking itself raises (e.g., custom __getattribute__),
        # skip this candidate
        return None

    if is_string:
        return sys.modules.get(candidate)

    # Return candidate as-is (could be any object type, not just ModuleType)
    return candidate


def _is_mock_like(module: Any) -> bool:
    """Check if a module/object appears to be a unittest.mock object.

    Uses safe attribute access to avoid triggering mock auto-creation.
    Catches all exceptions defensively to avoid breaking the resolution flow.

    Args:
        module: Module or object to check

    Returns:
        True if the object appears mock-like, False otherwise (or on any exception)
    """
    try:
        mock_children = getattr(module, "_mock_children", None)
        module_name = getattr(module, "__module__", "")
        class_name = getattr(module.__class__, "__name__", "")
        return (
            mock_children is not None
            or class_name in {"Mock", "MagicMock", "AsyncMock"}
            or module_name.startswith("unittest.mock")
        )
    except Exception:  # noqa: BLE001 - catch all for defensive behavior
        return False


def _get_attr_from_module(module: Any, name: str) -> tuple[bool, Any]:
    """Get attribute from module/object, preferring explicit __dict__ entries.

    Prefers explicit attributes in __dict__ to avoid Mock auto-created attributes.
    Falls back to getattr if not found in __dict__ and module is a ModuleType.

    Args:
        module: Module object or any object to search
        name: Attribute name to retrieve

    Returns:
        Tuple of (found: bool, value: Any). found is True if attribute exists,
        False otherwise. value is the attribute value if found, None otherwise.
    """
    # Prefer explicit attributes to avoid Mock auto-created attrs.
    dct = getattr(module, "__dict__", None)
    if isinstance(dct, dict) and name in dct:
        return (True, dct[name])

    # Avoid triggering unittest.mock auto-creation of attributes
    if _is_mock_like(module):
        return (False, None)

    # Only use getattr for ModuleType objects (preserves original behavior)
    if isinstance(module, types.ModuleType) and hasattr(module, name):
        return (True, getattr(module, name))

    return (False, None)


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
    for candidate in candidates:
        try:
            module = _resolve_module_candidate(candidate)
            if module is None:
                continue

            found, value = _get_attr_from_module(module, name)
            if found:
                return value
        except (
            AttributeError,
            TypeError,
            ImportError,
        ) as resolve_err:
            logger.debug("resolve_attr ignored %s while inspecting %s", resolve_err, candidate)
            continue
    return local_default


# Usage: add comment "# pragma: no cover" after lines that are difficult to test
# when marking untestable edge cases in coverage reports

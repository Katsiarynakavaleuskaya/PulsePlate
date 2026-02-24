"""Core utilities shared across endpoints.

- get_activity_factor: unified mapping for activity multipliers.
- resolve_attr: safe dynamic attribute resolver respecting test-time patches.
- safe_float/safe_int/slugify: safe parsing and text utilities.
- format_number/generate_id/sanitize_html/validate_email: formatting and validation.
"""

from __future__ import annotations

import logging
import re
import sys
import types
import uuid
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


# ---------------------------------------------------------------------------
# Thin facades for utils_pack feature key (PR-880)
# ---------------------------------------------------------------------------


def safe_float(value: object, default: float | None = None) -> float | None:
    """Safely convert value to float, returning default on failure.

    Args:
        value: Value to convert (string, number, or None).
        default: Value to return if conversion fails.

    Returns:
        Converted float or default value.
    """
    if value is None:
        return default
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, (str, bytes, bytearray)):
            return float(value)
        return float(str(value))
    except (ValueError, TypeError, OverflowError):
        return default


def safe_int(value: object, default: int | None = None) -> int | None:
    """Safely convert value to int, returning default on failure.

    Args:
        value: Value to convert (string, number, or None).
        default: Value to return if conversion fails.

    Returns:
        Converted int or default value.
    """
    if value is None:
        return default
    try:
        # Handle float strings like "123.45" by converting to float first
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, (str, bytes, bytearray)):
            return int(float(value))
        return int(float(str(value)))
    except (ValueError, TypeError, OverflowError):
        return default


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: object) -> str:
    """Convert text to URL-safe slug.

    Args:
        text: Text to convert (string or None).

    Returns:
        Lowercase slug with non-alphanumeric characters replaced by hyphens.
    """
    if text is None:
        return ""
    s = str(text).lower().strip()
    s = _SLUG_RE.sub("-", s)
    return s.strip("-")


def format_number(value: object, decimals: int = 2) -> str:
    """Format a number with specified decimal places.

    Args:
        value: Number to format.
        decimals: Number of decimal places.

    Returns:
        Formatted string representation.
    """
    try:
        return f"{float(value):.{decimals}f}"  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return str(value)


def generate_id() -> str:
    """Generate a unique identifier string.

    Returns:
        UUID4 string without hyphens.
    """
    return uuid.uuid4().hex


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_html(html: object) -> str:
    """Remove HTML tags from input string.

    Note: This is a simple tag-stripping utility, not a security-grade
    sanitizer. For untrusted user input, use a dedicated library like
    bleach or html-sanitizer.

    Args:
        html: HTML string to sanitize. Non-string inputs are coerced via str().
              None returns empty string.

    Returns:
        Plain text with HTML tags removed.
    """
    if html is None:
        return ""
    return _HTML_TAG_RE.sub("", str(html))


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(email: object) -> bool:
    """Validate email address format.

    Args:
        email: Email address to validate.

    Returns:
        True if valid email format, False otherwise.
    """
    if not email:
        return False
    return bool(_EMAIL_RE.match(str(email)))

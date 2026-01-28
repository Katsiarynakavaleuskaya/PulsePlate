"""Feature flag helpers.

Keep parsing logic centralized to avoid drift across modules.
"""

from __future__ import annotations

from typing import Optional

import os

_TRUTHY = {"1", "true", "yes", "on"}


def _is_truthy(value: Optional[str]) -> bool:
    """Check if a string value is truthy.

    Returns True if value (after strip/lower) is in {"1", "true", "yes", "on"}.
    Preserves exact behavior from legacy_app.py.
    """
    return str(value).strip().lower() in _TRUTHY


def is_vip_module_enabled() -> bool:
    """Check if VIP module is enabled via environment variable."""
    return _is_truthy(os.getenv("VIP_MODULE_ENABLED", "true"))


__all__ = ["is_vip_module_enabled", "_is_truthy"]

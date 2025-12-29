"""Feature flag helpers.

Keep parsing logic centralized to avoid drift across modules.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def is_vip_module_enabled() -> bool:
    raw = os.getenv("VIP_MODULE_ENABLED", "true").strip().lower()
    return raw in _TRUTHY


__all__ = ["is_vip_module_enabled"]

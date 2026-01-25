from __future__ import annotations

"""
Test-only helper: controlled sys.modules purging.

We intentionally mutate sys.modules here to avoid half-loaded import states in tests.
This is an approved exception for CI stability; protected prefixes are excluded by default.
"""

import sys
from collections.abc import Iterable

# RU: Критичные модули, которые НИКОГДА нельзя purge-ить.
# EN: Critical modules that must never be purged.
_DEFAULT_EXCLUDE_PREFIXES: tuple[str, ...] = (
    "app.models",
    "core.db",
)


def purge_modules(*, prefixes: Iterable[str], exclude_prefixes: Iterable[str] = ()) -> None:
    """
    RU: Аккуратно чистим sys.modules по префиксам, не оставляя "полу-состояния".
    EN: Safely purge sys.modules by prefixes without leaving half-loaded packages.
    """
    prefixes_t = tuple(p for p in prefixes if p)
    if not prefixes_t:
        # Fail-safe: empty/invalid prefixes => no-op.
        return

    exclude_t = _DEFAULT_EXCLUDE_PREFIXES + tuple(p for p in exclude_prefixes if p)

    for name in list(sys.modules.keys()):
        if any(name == p or name.startswith(f"{p}.") for p in prefixes_t):
            if any(name == e or name.startswith(f"{e}.") for e in exclude_t):
                continue
            sys.modules.pop(name, None)

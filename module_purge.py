from __future__ import annotations

import sys
from collections.abc import Iterable


def purge_modules(*, prefixes: Iterable[str], exclude_prefixes: Iterable[str] = ()) -> None:
    """
    RU: Аккуратно чистим sys.modules по префиксам, не оставляя "полу-состояния".
    EN: Safely purge sys.modules by prefixes without leaving half-loaded packages.
    """
    prefixes_t = tuple(prefixes)
    exclude_t = tuple(exclude_prefixes)

    for name in list(sys.modules.keys()):
        if any(name == p or name.startswith(p + ".") for p in prefixes_t):
            if any(name == e or name.startswith(e + ".") for e in exclude_t):
                continue
            sys.modules.pop(name, None)

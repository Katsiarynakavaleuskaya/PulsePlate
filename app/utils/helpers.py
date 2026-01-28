"""Utility helpers extracted from legacy_app.py for thin-proxy cleanup.

These functions are pure utilities with no dependencies on legacy_app.py
or runtime initialization logic.
"""

from __future__ import annotations

import re
import sys
from typing import Any, Callable, Optional, cast

# Regex for validating hex digest (used by _short_git_sha)
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def _resolve_app_callable(
    attr_name: str, default: Optional[Callable[..., Any]] = None
) -> Optional[Callable[..., Any]]:
    """Return callable attribute from app_module or app package if available."""
    for module_name in ("app", "app_module"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        candidate = getattr(module, attr_name, None)
        if callable(candidate):
            return cast(Optional[Callable[..., Any]], candidate)
    return default


def _short_git_sha(raw: str | None) -> str:
    """
    RU: Нормализует git SHA / image digest для /health.
    EN: Normalize git sha / image digest for /health.

    Accepts:
      - "sha256:<digest>"
      - "ghcr.io/...@sha256:<digest>"
      - "<sha>"
    Returns:
      - first 12 hex chars when possible, "unknown" if empty/invalid
    """
    if not raw:
        return "unknown"

    s = raw.strip()
    if not s:
        return "unknown"

    # If this is a repo digest, keep only the digest part after '@'
    if "@sha256:" in s:
        s = s.split("@sha256:", 1)[1]
    elif s.startswith("sha256:"):
        s = s.split("sha256:", 1)[1]

    s = s.strip()
    if not s:
        return "unknown"

    # Validate hex digest (reasonable minimum length)
    if len(s) < 12 or not _HEX_RE.fullmatch(s):
        return "unknown"

    return s[:12]

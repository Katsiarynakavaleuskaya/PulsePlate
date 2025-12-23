# flake8: noqa: F401
"""App package - shim facade for legacy_app backward compatibility.

This module uses PEP 562 __getattr__ to forward ALL attribute lookups
to legacy_app, ensuring `import app` works exactly as before the refactor.
"""
from __future__ import annotations

import sys
from typing import Any

import legacy_app as _legacy

# CRITICAL: app instance MUST be from legacy_app (routes are registered there)
app = _legacy.app

# Legacy compatibility aliases
app_module = _legacy  # Tests expect this alias
_mod = _legacy  # Fallback tests expect this

# Explicit re-exports for IDE/static analysis (optional but helpful)
from core.utils import resolve_attr
from core.menu_engine import make_weekly_menu
from core.recommendations import build_nutrition_targets

# Optional visualization (safe import)
try:
    from bmi_visualization import MATPLOTLIB_AVAILABLE, generate_bmi_visualization
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    generate_bmi_visualization = None

# Subpackages
from app import routers, scheduler_helpers


def __getattr__(name: str) -> Any:
    """PEP 562: Forward ALL attribute lookups to legacy_app.

    This restores full legacy API surface without manually listing 200+ symbols.
    """
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    """Include both local and legacy_app symbols for hasattr/dir stability."""
    return sorted(set(globals().keys()) | set(dir(_legacy)))


# Ensure sys.modules["app"] binding is correct
sys.modules["app"] = sys.modules[__name__]
sys.modules.setdefault("app_module", _legacy)

# Public exports for static analysis
__all__ = [
    "app",
    "resolve_attr",
    "make_weekly_menu",
    "build_nutrition_targets",
    "MATPLOTLIB_AVAILABLE",
    "generate_bmi_visualization",
    "routers",
    "scheduler_helpers",
]

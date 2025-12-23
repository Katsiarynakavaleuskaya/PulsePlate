"""App package entrypoint.

Deterministic imports only - re-exports legacy public API for backward compatibility.

NOTE: Some exports may be None if optional dependencies are not installed.
This is intentional for legacy compatibility; callers must guard usage.

NOTE: Underscore-prefixed symbols (_is_truthy, _macros_to_kcal, _alias_micros)
are legacy public API relied upon by tests and are intentionally exported.
"""

# flake8: noqa: F401

from typing import Any, Optional

# Core FastAPI app instance
from app.main import app

# Legacy public API - functions and utilities from legacy_app.py
from legacy_app import (
    get_api_key,
    calc_bmi,
    normalize_flags,
    _is_truthy,  # legacy public (used by tests)
    add_visualization_if_requested,
    legacy_category_label,
    lifespan,
    _macros_to_kcal,  # legacy public (used by tests)
    _alias_micros,  # legacy public (used by tests)
    get_update_scheduler,  # async scheduler getter
)

# Utility functions from core
from core.utils import resolve_attr
from core.menu_engine import make_weekly_menu
from core.recommendations import build_nutrition_targets

# Visualization flags (optional - from bmi_visualization)
MATPLOTLIB_AVAILABLE: bool = False
generate_bmi_visualization: Optional[Any] = None
try:
    from bmi_visualization import MATPLOTLIB_AVAILABLE
    from bmi_visualization import generate_bmi_visualization
except ImportError:
    pass  # Use fallback values above

# Prometheus metrics (optional)
Counter: Optional[type] = None
Histogram: Optional[type] = None
generate_latest: Optional[Any] = None

try:
    from prometheus_client import Counter, Histogram, generate_latest
except ImportError:
    pass

# Schemas (optional - commonly imported by tests)
BMIRequest: Optional[type] = None
BMIRequestV1: Optional[type] = None

try:
    from app.schemas.bmi import BMIRequest
except ImportError:
    pass

try:
    from app.schemas.bmi_v1 import BMIRequestV1
except ImportError:
    pass

# Routers
from app import routers

vip_router: Optional[Any] = None
try:
    from app.routers.vip import router as vip_router
except ImportError:
    pass

# Scheduler helpers
from app import scheduler_helpers

# Waist risk function (optional - if exists in legacy_app)
waist_risk: Optional[Any] = None
try:
    from legacy_app import waist_risk
except (ImportError, AttributeError):
    pass

# dotenv (if tests import it from app)
dotenv: Optional[Any] = None
try:
    import dotenv
except ImportError:
    pass

# Public API exports - deduplicated to survive merges
_PUBLIC_EXPORTS = [
    "app",
    "get_api_key",
    "calc_bmi",
    "normalize_flags",
    "_is_truthy",
    "add_visualization_if_requested",
    "legacy_category_label",
    "lifespan",
    "_macros_to_kcal",
    "_alias_micros",
    "get_update_scheduler",
    "resolve_attr",
    "make_weekly_menu",
    "build_nutrition_targets",
    "MATPLOTLIB_AVAILABLE",
    "generate_bmi_visualization",
    "Counter",
    "Histogram",
    "generate_latest",
    "BMIRequest",
    "BMIRequestV1",
    "routers",
    "vip_router",
    "scheduler_helpers",
    "waist_risk",
    "dotenv",
]

# Deduplicate while preserving order (survives merge conflicts)
__all__ = list(dict.fromkeys(_PUBLIC_EXPORTS))

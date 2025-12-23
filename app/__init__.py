"""App package entrypoint.

Deterministic imports only - re-exports legacy public API for backward compatibility.

NOTE: Some exports may be None if optional dependencies are not installed.
This is intentional for legacy compatibility; callers must guard usage.

NOTE: Underscore-prefixed symbols (_is_truthy, _macros_to_kcal, _alias_micros)
are legacy public API relied upon by tests and are intentionally exported.
"""

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
)

# Utility functions from core
from core.utils import resolve_attr

# Prometheus metrics (optional)
Counter: Optional[type] = None
Histogram: Optional[type] = None
generate_latest: Optional[Any] = None

try:
    from prometheus_client import Counter, Histogram, generate_latest  # type: ignore[no-redef]
except ImportError:
    pass

# Schemas (optional - commonly imported by tests)
BMIRequest: Optional[type] = None
BMIRequestV1: Optional[type] = None

try:
    from app.schemas.bmi import BMIRequest  # type: ignore[no-redef]
except ImportError:
    pass

try:
    from app.schemas.bmi_v1 import BMIRequestV1  # type: ignore[no-redef]
except ImportError:
    pass

# Routers
from app import routers

vip_router: Optional[Any] = None
try:
    from app.routers.vip import router as vip_router  # type: ignore[no-redef]
except ImportError:
    pass

# Scheduler helpers
from app import scheduler_helpers

# Waist risk function (optional - if exists in legacy_app)
waist_risk: Optional[Any] = None
try:
    from legacy_app import waist_risk  # type: ignore[no-redef]
except (ImportError, AttributeError):
    pass

# dotenv (if tests import it from app)
dotenv: Optional[Any] = None
try:
    import dotenv  # type: ignore[no-redef]
except ImportError:
    pass

__all__ = [
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
    "resolve_attr",
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

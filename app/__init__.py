"""App package entrypoint.

Deterministic imports only - re-exports legacy public API for backward compatibility.

NOTE: Some exports may be None if optional dependencies are not installed.
This is intentional for legacy compatibility; callers must guard usage.

NOTE: Underscore-prefixed symbols (_is_truthy, _macros_to_kcal, _alias_micros)
are legacy public API relied upon by tests and are intentionally exported.
"""

# flake8: noqa: F401

from typing import Any, Optional
import sys as _sys

# Core FastAPI app instance
from app.main import app

import legacy_app as _legacy_app

# Legacy public API - functions and utilities from legacy_app.py
get_api_key = _legacy_app.get_api_key
calc_bmi = _legacy_app.calc_bmi
normalize_flags = _legacy_app.normalize_flags
_is_truthy = _legacy_app._is_truthy  # legacy public (used by tests)
add_visualization_if_requested = _legacy_app.add_visualization_if_requested
legacy_category_label = _legacy_app.legacy_category_label
lifespan = _legacy_app.lifespan
_macros_to_kcal = _legacy_app._macros_to_kcal  # legacy public (used by tests)
_alias_micros = _legacy_app._alias_micros  # legacy public (used by tests)
get_update_scheduler = _legacy_app.get_update_scheduler  # async scheduler getter
calculate_all_bmr = _legacy_app.calculate_all_bmr
calculate_all_tdee = _legacy_app.calculate_all_tdee
_calculate_all_bmr_wrapper = _legacy_app._calculate_all_bmr_wrapper
_calculate_all_tdee_wrapper = _legacy_app._calculate_all_tdee_wrapper
make_plate = _legacy_app.make_plate
start_background_updates = _legacy_app.start_background_updates
stop_background_updates = _legacy_app.stop_background_updates
_scheduler_getter = _legacy_app._scheduler_getter
_test_scheduler_override = _legacy_app._test_scheduler_override
_resolve_app_callable = _legacy_app._resolve_app_callable
_scheduler_start_background_updates = _legacy_app._scheduler_start_background_updates
_scheduler_stop_background_updates = _legacy_app._scheduler_stop_background_updates
_is_rate_limiting_available = _legacy_app._is_rate_limiting_available
VIP_MODULE_ENABLED = _legacy_app.VIP_MODULE_ENABLED
get_bodyfat_router = _legacy_app.get_bodyfat_router
bmi_pro_router = _legacy_app.bmi_pro_router
premium_week_router = _legacy_app.premium_week_router
admin_status = _legacy_app.admin_status
targets_disabled = _legacy_app.targets_disabled
reset_targets_cache = _legacy_app.reset_targets_cache
_targets_disabled_cache = _legacy_app._targets_disabled_cache
_targets_disabled_cache_time = _legacy_app._targets_disabled_cache_time
_plate_deps = _legacy_app._plate_deps
PlateRequest = _legacy_app.PlateRequest
PlateResponse = _legacy_app.PlateResponse
_convert_db_nutrients_to_alias_format = _legacy_app._convert_db_nutrients_to_alias_format
to_csv_day = _legacy_app.to_csv_day
to_csv_week = _legacy_app.to_csv_week
to_pdf_day = _legacy_app.to_pdf_day
to_pdf_week = _legacy_app.to_pdf_week
export_pdf_generic = getattr(_legacy_app, "export_pdf_generic", None)
reset_safety_failure_count = _legacy_app.reset_safety_failure_count
_safety_failure_count = _legacy_app._safety_failure_count
api_key_header = _legacy_app.api_key_header
get_session = _legacy_app.get_session
HTTPException = _legacy_app.HTTPException

_sys.modules.setdefault("app_module", _legacy_app)

# Utility functions from core
from core.utils import resolve_attr

make_weekly_menu: Optional[Any] = None
build_nutrition_targets: Optional[Any] = None
try:
    from core.menu_engine import make_weekly_menu
except ImportError:
    pass
try:
    from core.recommendations import build_nutrition_targets
except ImportError:
    pass

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
try:
    from app.schemas.bmi import BMIRequest
except ImportError:
    BMIRequest = None  # noqa: N816

try:
    from app.schemas.bmi_v1 import BMIRequestV1
except ImportError:
    BMIRequestV1 = None  # noqa: N816

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

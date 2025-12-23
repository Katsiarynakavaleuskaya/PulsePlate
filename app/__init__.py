"""
App package entrypoint.

Deterministic imports only - re-exports legacy public API for backward compatibility.
"""

# Core FastAPI app instance
from app.main import app

# Legacy public API - functions and utilities from legacy_app.py
from legacy_app import (
    get_api_key,
    calc_bmi,
    normalize_flags,
    _is_truthy,
    add_visualization_if_requested,
    legacy_category_label,
    lifespan,
    _macros_to_kcal,
    _alias_micros,
)

# Prometheus metrics (if imported by tests)
try:
    from prometheus_client import Counter, Histogram, generate_latest
except ImportError:
    Counter = None  # type: ignore
    Histogram = None  # type: ignore
    generate_latest = None  # type: ignore

# Schemas (commonly imported by tests)
try:
    from app.schemas.bmi import BMIRequest
except ImportError:
    BMIRequest = None  # type: ignore

try:
    from app.schemas.bmi_v1 import BMIRequestV1
except ImportError:
    BMIRequestV1 = None  # type: ignore

# Routers
from app import routers

try:
    from app.routers.vip import router as vip_router
except ImportError:
    vip_router = None  # type: ignore

# Scheduler helpers
from app import scheduler_helpers

# Waist risk function (if exists in legacy_app)
try:
    from legacy_app import waist_risk
except (ImportError, AttributeError):
    waist_risk = None  # type: ignore

# dotenv (if tests import it from app)
try:
    import dotenv
except ImportError:
    dotenv = None  # type: ignore

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

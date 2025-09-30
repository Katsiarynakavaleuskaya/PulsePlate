#!/usr/bin/env python3
"""
App module initialization
"""

import importlib.util
import os

# Import FastAPI app and functions from the main module
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the main app.py file directly
spec = importlib.util.spec_from_file_location("app_module", "app.py")
if spec is None or spec.loader is None:
    app = None
    get_api_key = None
    get_update_scheduler = None
    HTTPException = None
    admin_status = None
    add_visualization_if_requested = None
    to_pdf_day = None
    export_pdf_generic = None
    make_weekly_menu = None
    _mod = None
else:
    _app_module = importlib.util.module_from_spec(spec)
    # Register module in sys.modules BEFORE executing to handle circular refs
    sys.modules["app_module"] = _app_module
    spec.loader.exec_module(_app_module)
    app = _app_module.app
    get_api_key = _app_module.get_api_key
    get_update_scheduler = _app_module.get_update_scheduler
    HTTPException = _app_module.HTTPException
    admin_status = _app_module.admin_status
    add_visualization_if_requested = getattr(_app_module, "add_visualization_if_requested", None)
    to_pdf_day = getattr(_app_module, "to_pdf_day", None)
    export_pdf_generic = getattr(_app_module, "export_pdf_generic", None)
    make_weekly_menu = getattr(_app_module, "make_weekly_menu", None)
    _mod = _app_module

# Create a module spec for this package
from importlib.machinery import ModuleSpec

_spec: ModuleSpec | None = importlib.util.spec_from_loader(__name__, loader=None)
if _spec is not None:
    _spec.name = __name__
    _spec.submodule_search_locations = [os.path.dirname(__file__)]
    __spec__ = _spec
else:
    # Fallback if spec creation fails
    __spec__ = None  # type: ignore[assignment]

# Export the app and key functions for easy importing
__all__ = [
    "app",
    "get_api_key",
    "get_update_scheduler",
    "HTTPException",
    "admin_status",
    "add_visualization_if_requested",
    "to_pdf_day",
    "export_pdf_generic",
    "make_weekly_menu",
    "_mod",
    "app_module",
]

# Alias for backward compatibility
app_module = _mod


def __getattr__(name):
    """Allow access to attributes from the underlying module"""
    if _mod is not None and hasattr(_mod, name):
        return getattr(_mod, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

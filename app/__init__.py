#!/usr/bin/env python3
"""
App module initialization
"""

# Import FastAPI app and functions from the main module
import sys
import os
import importlib.util

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
else:
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    app = app_module.app
    get_api_key = app_module.get_api_key
    get_update_scheduler = app_module.get_update_scheduler
    HTTPException = app_module.HTTPException
    admin_status = app_module.admin_status

# Export the app and key functions for easy importing
__all__ = ["app", "get_api_key", "get_update_scheduler", "HTTPException", "admin_status"]

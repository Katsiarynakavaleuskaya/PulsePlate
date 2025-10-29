"""
Shared test helpers for the PulsePlate project.
"""

import importlib.util
import os
import sys
from typing import Any


class AppLoadError(ImportError):
    """Raised when app.py cannot be loaded."""

    pass


def load_app() -> Any:
    """
    Load FastAPI app dynamically from app.py file.

    Returns:
        FastAPI app instance

    Raises:
        AppLoadError: If app.py cannot be loaded
    """
    # Ensure project root is in Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Ensure the package 'app' (directory) is imported first to avoid app.py shadowing
    try:
        __import__("app")
    except Exception:
        pass

    # Load app.py dynamically
    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    if spec is None or spec.loader is None:
        raise AppLoadError()

    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    return app_module.app

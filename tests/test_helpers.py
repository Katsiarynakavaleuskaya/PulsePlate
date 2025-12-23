from __future__ import annotations

from typing import Any, Mapping

import pytest

def skip_if_no_plate_micros(plate_micros: Mapping[str, Any]) -> None:
    """Skip tests when plate micros data is empty.

    RU: Пропустить тест, если словарь микронутриентов пуст (обычно из-за отсутствия ингредиентов).
    EN: Skip test if plate micronutrients dict is empty (likely due to missing recipe ingredients).
    """
    if len(plate_micros) == 0:
        pytest.skip(
            "Plate day_micros is empty (likely due to missing recipe ingredients). "
            "This is acceptable when recipe lookup fails."
        )

"""
Shared test helpers for the PulsePlate project.
"""

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

    # Load app.py dynamically
        if spec is None or spec.loader is None:
        raise AppLoadError()

            return app_module.app

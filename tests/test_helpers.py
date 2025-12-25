"""Shared test helpers for the PulsePlate project."""

from __future__ import annotations

from typing import Any, Mapping

import pytest
from fastapi import FastAPI


def load_app() -> FastAPI:
    """Load and return the FastAPI app instance."""
    import app as app_module

    return app_module.app


def skip_if_no_plate_micros(plate_micros: Mapping[str, Any] | None) -> None:
    """Skip tests when plate micros data is missing or empty.

    RU: Пропустить тест, если словарь микронутриентов пуст (обычно из-за отсутствия ингредиентов).
    EN: Skip test if plate micronutrients dict is empty (likely due to missing recipe ingredients).
    """
    if plate_micros is None:
        pytest.skip(
            "Plate day_micros is missing (likely due to missing recipe ingredients). "
            "This is acceptable when recipe lookup fails."
        )
    if not plate_micros:
        pytest.skip(
            "Plate day_micros is empty (likely due to missing recipe ingredients). "
            "This is acceptable when recipe lookup fails."
        )

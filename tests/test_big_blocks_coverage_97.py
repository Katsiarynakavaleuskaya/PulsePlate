"""
Тесты для покрытия больших непокрытых блоков в main.py.
Цель: покрыть блоки 668-677, 698-709, 750-760 (~33 строки).
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Shared TestClient with isolated environment per test.

    Uses monkeypatch to set and auto-restore environment variables to avoid
    cross-test side effects and keep tests hermetic.
    """
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    import sys

    # Import the FastAPI app from app.py file
    import importlib.util

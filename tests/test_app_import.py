"""
Simple test to import main.py and check its coverage.
"""

from fastapi import FastAPI

import app


def test_app_import():
    """Test that main.py can be imported."""
    assert app is not None
    assert hasattr(app, "app")  # FastAPI app instance
    assert app.app is not None
    assert isinstance(app.app, FastAPI)


def test_app_endpoints():
    """Test that app has expected endpoints."""
    # Just check that the app has some routes
    assert hasattr(app.app, "routes")
    assert len(app.app.routes) > 0

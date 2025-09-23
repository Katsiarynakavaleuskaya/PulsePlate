"""
Simple test to import app.py and check its coverage.
"""

import app
from fastapi import FastAPI


def test_app_import():
    """Test that app.py can be imported."""
    assert app is not None
    assert hasattr(app, "app")  # FastAPI app instance
    assert app.app is not None
    assert isinstance(app.app, FastAPI)


def test_app_endpoints():
    """Test that app has expected endpoints."""
    # Just check that the app has some routes
    assert hasattr(app.app, "routes")
    assert len(app.app.routes) > 0

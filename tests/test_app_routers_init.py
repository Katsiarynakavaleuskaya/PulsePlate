"""Test app/routers/__init__.py coverage."""

import pytest


def test_routers_init_getattr_valid_names():
    """Test __getattr__ with valid router names."""
    from app.routers import bmi_pro, foods, premium_week, recipes, users, vip

    # These should not raise AttributeError
    assert bmi_pro is not None
    assert foods is not None
    assert premium_week is not None
    assert recipes is not None
    assert users is not None
    assert vip is not None


def test_routers_init_getattr_invalid_name():
    """Test __getattr__ with invalid router name to cover line 24."""
    import app.routers as routers_module

    # This should raise AttributeError for line 24 coverage
    with pytest.raises(AttributeError, match="invalid_router"):
        _ = routers_module.invalid_router


def test_routers_init_all_exported():
    """Test that __all__ contains expected router names."""
    import app.routers as routers_module

    expected_routers = ["bmi_pro", "foods", "premium_week", "recipes", "users", "vip"]
    assert routers_module.__all__ == expected_routers

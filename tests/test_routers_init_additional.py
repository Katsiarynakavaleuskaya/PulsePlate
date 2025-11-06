from __future__ import annotations

from app import routers


def test_routers_getattr_returns_module():
    foods_module = routers.__getattr__("foods")
    assert foods_module.__name__ == "app.routers.foods"


def test_routers_getattr_invalid():
    try:
        routers.__getattr__("unknown")
    except AttributeError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("AttributeError expected")

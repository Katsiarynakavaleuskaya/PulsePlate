"""
VIP auth and adapter edge tests to raise coverage for app/routers/vip.py.
"""

import os

from fastapi import HTTPException
import pytest


def _clear(keys):
    for k in keys:
        os.environ.pop(k, None)


def test_require_api_key_allow_anonymous_nonprod():
    from app.routers.vip import _require_api_key

    # Non-production, explicit allow
    os.environ["APP_ENV"] = "development"
    os.environ["DEBUG"] = "true"
    os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "true"
    _clear(["API_KEY"])  # ensure no env API_KEY

    assert _require_api_key(None) == "anonymous"


def test_require_api_key_dev_fallback_returns_test_key():
    from app.routers.vip import _require_api_key

    # Non-production, no explicit allow/deny → fallback to dev test key
    os.environ["APP_ENV"] = "local"
    os.environ["DEBUG"] = "true"
    _clear(["ALLOW_ANONYMOUS_API_KEYS", "API_KEY"])  # default behavior

    assert _require_api_key(None) == "test_key"


def test_require_api_key_strict_missing_key_raises():
    from app.routers.vip import _require_api_key_strict

    os.environ["APP_ENV"] = "development"
    os.environ["DEBUG"] = "true"
    with pytest.raises(HTTPException) as ei:
        _require_api_key_strict(None)
    assert ei.value.status_code == 401


def test_require_api_key_dev_legacy_nonprod_and_prod_allow():
    from app.routers.vip import _require_api_key_dev_legacy

    # Dev/local: anonymous
    os.environ["APP_ENV"] = "dev"
    os.environ["DEBUG"] = "true"
    _clear(["ALLOW_ANONYMOUS_API_KEYS", "API_KEY"])  # default
    assert _require_api_key_dev_legacy(None) == "anonymous"

    # Production with explicit anonymous allow
    os.environ["APP_ENV"] = "production"
    os.environ["DEBUG"] = "false"
    os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "true"
    assert _require_api_key_dev_legacy(None) == "anonymous"


def test_adapter_make_weekly_menu_no_profile_path():
    from app.routers.vip import _adapter_make_weekly_menu

    # Pass kwargs without any profile-like fields → expect None (echo path)
    out = _adapter_make_weekly_menu(dummy=1, data={"foo": "bar"})
    assert out is None

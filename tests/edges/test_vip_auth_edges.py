# -*- coding: utf-8 -*-
"""
VIP auth and adapter edge tests to raise coverage for app/routers/vip.py.
"""

import os

import pytest
from fastapi import HTTPException


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
    from fastapi import Request
    from unittest.mock import MagicMock

    os.environ["APP_ENV"] = "development"
    os.environ["DEBUG"] = "true"
    # Create a mock Request with no API key headers
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = None
    with pytest.raises(HTTPException) as ei:
        _require_api_key_strict(mock_request)
    assert ei.value.status_code == 403  # VIP = feature-gate, returns 403
    assert "vip" in ei.value.detail.lower() or "access" in ei.value.detail.lower()


def test_require_api_key_dev_legacy_nonprod_and_prod_allow():
    from app.routers.vip import _require_api_key_dev_legacy, TEST_KEY
    from fastapi import Request
    from unittest.mock import MagicMock

    # Dev/local: returns TEST_KEY (not anonymous) when no explicit flag
    os.environ["APP_ENV"] = "dev"
    os.environ["DEBUG"] = "true"
    _clear(["ALLOW_ANONYMOUS_API_KEYS", "API_KEY"])  # default
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = None
    assert _require_api_key_dev_legacy(mock_request) == TEST_KEY

    # Production with explicit anonymous allow - should raise 403 (no anonymous in prod)
    os.environ["APP_ENV"] = "production"
    os.environ["DEBUG"] = "false"
    os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "true"
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = None
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        _require_api_key_dev_legacy(mock_request)
    assert ei.value.status_code == 403


def test_adapter_make_weekly_menu_no_profile_path():
    from app.routers.vip import _adapter_make_weekly_menu

    # Pass kwargs without any profile-like fields → expect None (echo path)
    out = _adapter_make_weekly_menu(dummy=1, data={"foo": "bar"})
    assert out is None

import asyncio

import pytest
from fastapi import HTTPException


def test_get_api_key_strict_and_dev_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.api_key import get_api_key

    # Strict mode with expected key
    monkeypatch.setenv("API_KEY", "secret")
    assert get_api_key("secret") == "secret"
    with pytest.raises(HTTPException):
        get_api_key("wrong")

    # No API key configured, strict required → 403
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    with pytest.raises(HTTPException):
        get_api_key("abcd")

    # Dev/test mode lenient, but token must be non-trivial
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("APP_ENV", "test")
    assert get_api_key("abcd") == "abcd"
    with pytest.raises(HTTPException):
        get_api_key("bad")


def test_admin_status_scheduler_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import admin_operations

    async def _none_scheduler():  # noqa: D401
        return None

    monkeypatch.setattr(admin_operations, "get_update_scheduler", _none_scheduler)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(admin_operations.admin_status())
    assert ei.value.status_code == 503

    class DummyScheduler:
        pass

    async def _ok_scheduler():
        return DummyScheduler()

    monkeypatch.setattr(admin_operations, "get_update_scheduler", _ok_scheduler)
    out = asyncio.run(admin_operations.admin_status())
    assert out["status"] == "ok" and out["scheduler"] == "available"


def test_targets_get_minimum_maximum_unknown_raises():
    from core.targets import MicronutrientTargets

    t = MicronutrientTargets(
        iron_mg=(8.0, 18.0, 45.0),
        calcium_mg=(800.0, 1000.0, 2500.0),
        magnesium_mg=(300.0, 400.0, 700.0),
        zinc_mg=(8.0, 11.0, 40.0),
        potassium_mg=(2000.0, 3500.0, 5000.0),
        iodine_ug=(90.0, 150.0, 600.0),
        selenium_ug=(30.0, 55.0, 400.0),
        folate_ug=(200.0, 400.0, 1000.0),
        b12_ug=(1.0, 2.4, 100.0),
        vitamin_d_iu=(400.0, 600.0, 4000.0),
        vitamin_a_ug=(500.0, 700.0, 3000.0),
        vitamin_c_mg=(45.0, 90.0, 2000.0),
    )

    with pytest.raises(ValueError):
        t.get_minimum("unknown_nutrient")
    with pytest.raises(ValueError):
        t.get_maximum("unknown_nutrient")

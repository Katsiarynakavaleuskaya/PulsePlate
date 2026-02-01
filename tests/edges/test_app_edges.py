from typing import Any

import pytest


def test_get_api_key_strict_and_dev_modes(monkeypatch: pytest.MonkeyPatch):
    import app as appmod

    # Strict mode with expected key
    monkeypatch.setenv("API_KEY", "secret")
    assert appmod.get_api_key("secret") == "secret"
    with pytest.raises(appmod.HTTPException):
        appmod.get_api_key("wrong")

    # No API key configured, strict required → 403
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    with pytest.raises(appmod.HTTPException):
        appmod.get_api_key("abcd")

    # Dev/test mode lenient, but token must be non-trivial
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("APP_ENV", "test")
    assert appmod.get_api_key("abcd") == "abcd"
    with pytest.raises(appmod.HTTPException):
        appmod.get_api_key("bad")


@pytest.mark.asyncio
async def test_admin_status_scheduler_branches(monkeypatch: pytest.MonkeyPatch):
    import app as appmod

    async def _none_scheduler():  # noqa: D401
        return None

    monkeypatch.setattr(appmod, "get_update_scheduler", _none_scheduler)
    with pytest.raises(appmod.HTTPException) as ei:
        await appmod.admin_status()
    assert ei.value.status_code == 503

    class DummyScheduler:
        pass

    async def _ok_scheduler():
        return DummyScheduler()

    monkeypatch.setattr(appmod, "get_update_scheduler", _ok_scheduler)
    out = await appmod.admin_status()
    assert out["status"] == "ok" and out["scheduler"] == "available"


def test_add_visualization_if_requested_fallback(monkeypatch: pytest.MonkeyPatch):
    import app as appmod
    import bmi_visualization as vizmod

    class Req:
        include_chart = True
        age = 30
        gender = "male"
        pregnant = False
        athlete = False
        lang = "en"

    def fake_viz(**kwargs: Any):  # noqa: D401
        return {"available": False}

    # Patch the default provider used inside add_visualization_if_requested
    monkeypatch.setattr(vizmod, "generate_bmi_visualization", fake_viz)

    result: dict[str, Any] = {"bmi": 22.0}
    appmod.add_visualization_if_requested(result, Req())
    assert "visualization" in result


@pytest.mark.asyncio
async def test_export_pdf_generic_missing_function(monkeypatch: pytest.MonkeyPatch):
    import app as appmod
    from starlette.requests import Request

    # Ensure to_pdf_day is missing/non-callable
    monkeypatch.setattr(appmod, "to_pdf_day", None)
    with pytest.raises(appmod.HTTPException) as ei:
        req = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/export/pdf",
                "headers": [],
                "client": ("testclient", 1234),
                "server": ("testserver", 80),
                "scheme": "http",
            }
        )
        await appmod.export_pdf_generic(req, {"meals": []})
    assert ei.value.status_code == 503


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

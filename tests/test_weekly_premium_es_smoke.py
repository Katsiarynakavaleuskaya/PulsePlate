import importlib.util
import os

from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("app", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
client = TestClient(app_module.app)


def test_weekly_premium_es_smoke_open_or_protected():
    payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 175,
        "weight_kg": 70,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "es",
    }
    headers = {}
    if os.getenv("API_KEY"):
        headers["X-API-Key"] = os.getenv("API_KEY")
    r = client.post("/api/v1/premium/plan/week", json=payload, headers=headers)
    assert r.status_code in (200, 503, 403)
    if r.status_code == 200:
        data = r.json()
        # Should contain premium-compatible days
        assert "days" in data
        days = data["days"]
        assert isinstance(days, list) and len(days) == 7
        # Check Spanish translation presence in at least one meal
        spanish_markers = ["Desayuno", "Almuerzo", "Cena", "Merienda", "Avena", "Arroz", "Salmón", "Yogur", "Lentejas"]
        any_es = False
        for d in days:
            for m in d.get("meals", []):
                tt = m.get("title_translated", "")
                if isinstance(tt, str) and any(x in tt for x in spanish_markers):
                    any_es = True
                    break
            if any_es:
                break
        assert any_es, "expected at least one Spanish-translated meal title"

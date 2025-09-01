import importlib

import pytest
from fastapi.testclient import TestClient

app = importlib.import_module("app").app
client = TestClient(app)

def test_v0_bmi_pregnant_branches_en():
    r = client.post("/bmi", json={
        "weight_kg": 70, "height_m": 1.70,
        "age": 30, "gender": "female",
        "pregnant": "yes", "athlete": "no",
        "waist_cm": 80, "lang": "en", "premium": False
    })
    assert r.status_code == 200
    j = r.json()
    assert j["category"] is None
    assert "pregnancy" in j["note"].lower()

def test_v0_bmi_athlete_note_en():
    r = client.post("/bmi", json={
        "weight_kg": 80, "height_m": 1.75,
        "age": 25, "gender": "male",
        "pregnant": "no", "athlete": "yes",
        "waist_cm": 85, "lang": "en", "premium": False
    })
    assert r.status_code == 200
    assert "overestimate body fat" in r.json()["note"].lower()

@pytest.mark.parametrize("waist,gender_male,expect_sub", [
    (79,  False, ""),       # female < warn (80)
    (80,  False, "risk"),   # female warn
    (88,  False, "high"),   # female high
    (93,  True,  ""),       # male < warn (94)
    (94,  True,  "risk"),   # male warn
    (102, True,  "high"),   # male high
])
def test_waist_risk_unit(waist, gender_male, expect_sub):
    from app import waist_risk
    out = waist_risk(waist, gender_male, lang="en")
# sourcery skip: no-conditionals-in-tests
    if expect_sub == "":
        assert out == ""
    else:
        assert expect_sub in out.lower()



def test_debug_env_true_false(monkeypatch):
    j = client.get("/debug_env").json()
    assert j["insight_enabled"] in ("True", "False")
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    j2 = client.get("/debug_env").json()
    assert j2["insight_enabled"] == "True"

def test_insight_disabled_503(monkeypatch):
    monkeypatch.delenv("FEATURE_INSIGHT", raising=False)
    r = client.post("/insight", json={"text": "x"})
    assert r.status_code == 503


def test_insight_no_provider_503(monkeypatch):
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    r = client.post("/insight", json={"text": "x"})
    assert r.status_code == 503
    assert "No LLM provider configured" in r.json()["detail"]

@pytest.mark.parametrize("lang,premium,has_premium", [
    ("ru", False, False),
    ("ru", True,  True),
    ("en", False, False),
    ("en", True,  True),
])
def test_v0_plan_variants(lang, premium, has_premium):
    r = client.post("/plan", json={
        "weight_kg": 70, "height_m": 1.70,
        "age": 30, "gender": "female",
        "pregnant": "no", "athlete": "no",
        "waist_cm": None, "lang": lang, "premium": premium
    })
    assert r.status_code == 200
    j = r.json()
    assert "summary" in j and "healthy_bmi" in j
    assert ("premium_reco" in j) is has_premium


def test__bmi_value_raises_on_zero_height():
    from app import _bmi_value
    with pytest.raises(ValueError):
        _bmi_value(70, 0)


def test__bmi_value_valid():
    from app import _bmi_value
    assert _bmi_value(70, 170) == 24.2


def test__bmi_category():
    from app import _bmi_category
    assert _bmi_category(17) == "Underweight"
    assert _bmi_category(22) == "Normal"
    assert _bmi_category(27) == "Overweight"
    assert _bmi_category(32) == "Obese"


def test__interpretation():
    from app import _interpretation
    assert _interpretation(22, "general") == "Normal"
    expected_athlete = "Normal (мышечная масса может искажать BMI)"
    assert _interpretation(22, "athlete") == expected_athlete
    expected_pregnant = "BMI не применим при беременности"
    assert _interpretation(22, "pregnant") == expected_pregnant
    expected_elderly = "Normal (возрастные изменения состава тела)"
    assert _interpretation(22, "elderly") == expected_elderly
    expected_teen = "Используйте педиатрические перцентили BMI"
    assert _interpretation(22, "teen") == expected_teen

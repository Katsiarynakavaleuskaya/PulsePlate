import importlib

import pytest
from fastapi.testclient import TestClient

app = importlib.import_module("app").app
client = TestClient(app)


def test_v0_bmi_pregnant_branches_en():
    r = client.post(
        "/bmi",
        json={
            "weight_kg": 70,
            "height_m": 1.70,
            "age": 30,
            "gender": "female",
            "pregnant": "yes",
            "athlete": "no",
            "waist_cm": 80,
            "lang": "en",
            "premium": False,
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j["category"] is None
    assert "pregnancy" in j["note"].lower()


def test_v0_bmi_athlete_note_en():
    r = client.post(
        "/bmi",
        json={
            "weight_kg": 80,
            "height_m": 1.75,
            "age": 25,
            "gender": "male",
            "pregnant": "no",
            "athlete": "yes",
            "waist_cm": 85,
            "lang": "en",
            "premium": False,
        },
    )
    assert r.status_code == 200
    assert "overestimate body fat" in r.json()["note"].lower()


@pytest.mark.parametrize(
    "waist,gender_male,expect_sub",
    [
        (79, False, ""),  # female < warn (80)
        (80, False, "risk"),  # female warn
        (88, False, "high"),  # female high
        (93, True, ""),  # male < warn (94)
        (94, True, "risk"),  # male warn
        (102, True, "high"),  # male high
    ],
)
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


@pytest.mark.parametrize(
    "lang,premium,has_premium",
    [
        ("ru", False, False),
        ("ru", True, True),
        ("en", False, False),
        ("en", True, True),
    ],
)
def test_v0_plan_variants(lang, premium, has_premium):
    r = client.post(
        "/plan",
        json={
            "weight_kg": 70,
            "height_m": 1.70,
            "age": 30,
            "gender": "female",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": None,
            "lang": lang,
            "premium": premium,
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert "summary" in j and "healthy_bmi" in j
    assert ("premium_reco" in j) is has_premium


def test__bmi_value_raises_on_zero_height():
    from bmi_core import bmi_value

    with pytest.raises(ValueError):
        bmi_value(70, 0)


def test__bmi_value_valid():
    from bmi_core import bmi_value

    assert bmi_value(70, 1.70) == 24.2


def test__bmi_category():
    from bmi_core import bmi_category

    assert bmi_category(17, "en") == "Underweight"
    assert bmi_category(22, "en") == "Normal weight"
    assert bmi_category(27, "en") == "Overweight"
    assert bmi_category(32, "en") == "Obese Class I"


def test__interpretation():
    from bmi_core import interpret_group

    assert interpret_group(22, "general", "en") == "Normal weight"
    expected_athlete = (
        "Normal weight. For athletes, BMI may overestimate body fat due to muscle mass"
    )
    assert interpret_group(22, "athlete", "en") == expected_athlete
    expected_pregnant = "Normal weight. BMI is not valid during pregnancy"
    assert interpret_group(22, "pregnant", "en") == expected_pregnant
    expected_elderly = (
        "Normal weight. In older adults, BMI can underestimate body fat (sarcopenia)"
    )
    assert interpret_group(22, "elderly", "en") == expected_elderly
    expected_teen = "Normal weight. Teenage years: consider pubertal development stage"
    assert interpret_group(22, "teen", "en") == expected_teen

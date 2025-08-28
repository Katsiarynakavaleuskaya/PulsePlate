from fastapi.testclient import TestClient
from app import app as fastapi_app

client = TestClient(fastapi_app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_bmi_en():
    r = client.post("/bmi", json={
        "weight_kg": 70,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 80,
        "lang": "en"
    })
    assert r.status_code == 200
    data = r.json()
    assert round(data["bmi"], 1) == 22.9
    assert data["category"] == "Healthy weight"
    assert data["group"] == "general"

def test_bmi_ru_athlete():
    r = client.post("/bmi", json={
        "weight_kg": 85,
        "height_m": 1.80,
        "age": 28,
        "gender": "муж",
        "pregnant": "нет",
        "athlete": "спортсмен",
        "waist_cm": 82,
        "lang": "ru"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["group"] == "athlete"
    assert "Избыточный вес" in data["category"]

def test_plan():
    r = client.post("/plan", json={
        "weight_kg": 85,
        "height_m": 1.80,
        "age": 28,
        "gender": "муж",
        "pregnant": "нет",
        "athlete": "спортсмен",
        "waist_cm": 82,
        "lang": "ru",
        "premium": True
    })
    assert r.status_code == 200
    data = r.json()
    assert "healthy_bmi" in data
    assert "action" in data

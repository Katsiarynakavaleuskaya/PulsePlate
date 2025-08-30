import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict) and data.get("status") == "ok"


def test_bmi_smoke_ok():
    payload = {
        "height_m": 1.70,
        "weight_kg": 65,
        "age": 28,
        "gender": "female",
        "pregnant": "no",
        "athlete": "no",
        "user_group": "general",
        "language": "en",
    }
    r = client.post("/bmi", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "bmi" in data and 0 < float(data["bmi"]) < 100

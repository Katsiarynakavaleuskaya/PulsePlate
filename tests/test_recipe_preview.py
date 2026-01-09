from fastapi.testclient import TestClient
from tests._client import get_client

import app as app_module

client = get_client()


def test_recipe_preview_basic():
    payload = {
        "title": "Тост с йогуртом",
        "servings": 2,
        "ingredients": [
            {"food_id": "yogurt_plain_2pct", "grams": 200},
            {"food_id": "olive_oil_extra", "grams": 10},
        ],
    }
    r = client.post("/api/v1/recipes/preview", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["servings"] == 2
    assert data["total_g"] == 210
    assert data["per_serving"]["kcal"] >= 0

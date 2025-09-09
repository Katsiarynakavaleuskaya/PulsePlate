from fastapi.testclient import TestClient

import app as app_module

client = TestClient(app_module.app)


def test_search_foods_smoke():
    r = client.get("/api/v1/foods", params={"limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_food_card_404():
    r = client.get("/api/v1/foods/__nope__")
    assert r.status_code == 404

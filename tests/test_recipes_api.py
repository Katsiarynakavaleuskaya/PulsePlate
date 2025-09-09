from fastapi.testclient import TestClient

import app as app_module

client = TestClient(app_module.app)


def test_list_recipes_smoke():
    r = client.get("/api/v1/recipes", params={"query": "salad", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_recipe_404():
    r = client.get("/api/v1/recipes/NON_EXISTENT")
    assert r.status_code == 404

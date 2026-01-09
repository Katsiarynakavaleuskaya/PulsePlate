from fastapi.testclient import TestClient
from tests._client import get_client

import app as app_module

client = get_client()


def test_list_recipes_smoke():
    r = client.get("/api/v1/recipes", params={"query": "salad", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_recipe_404():
    r = client.get("/api/v1/recipes/NON_EXISTENT")
    assert r.status_code == 404

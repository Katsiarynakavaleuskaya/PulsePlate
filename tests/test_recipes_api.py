from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_list_recipes_smoke(client: "TestClient") -> None:
    r = client.get("/api/v1/recipes", params={"query": "salad", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_recipe_404(client: "TestClient") -> None:
    r = client.get("/api/v1/recipes/NON_EXISTENT")
    assert r.status_code == 404

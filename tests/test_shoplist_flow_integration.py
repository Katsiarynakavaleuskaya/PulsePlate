from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient


def _without_generated_at(payload: dict[str, object]) -> dict[str, object]:
    """Drop volatile timestamp field for deterministic comparisons."""
    normalized = deepcopy(payload)
    normalized.pop("generated_at", None)
    return normalized


def test_plan_to_shoplist_flow_is_deterministic(
    client: TestClient, pro_headers: dict[str, str]
) -> None:
    """Same logical plan must produce stable shoplist output."""
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "late_meal",
                        # Deliberately unsorted keys: extractor should normalize deterministic ordering.
                        "grams": {"rice": 150.0, "chicken_breast": 120.0, "banana": 90.0},
                    },
                    {
                        "title": "early_meal",
                        "grams": {"banana": 60.0, "rice": 50.0},
                    },
                ]
            }
        ]
    }

    payload = {
        "plan_data": plan_data,
        "preferences": {
            "group_by": "category",
            "unit_system": "metric",
            "exclude_items": [],
            "dietary_tags": [],
            "round_quantities": True,
        },
    }

    first = client.post("/api/v1/pro/meal/shopping-list", json=payload, headers=pro_headers)
    second = client.post("/api/v1/pro/meal/shopping-list", json=payload, headers=pro_headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.headers["content-type"].startswith("application/json")
    assert second.headers["content-type"].startswith("application/json")

    first_body = first.json()
    second_body = second.json()

    # Volatile timestamp is excluded; all functional fields must be stable.
    assert _without_generated_at(first_body) == _without_generated_at(second_body)

    reordered_plan_data = deepcopy(plan_data)
    original_meals = reordered_plan_data["daily_menus"][0]["meals"]
    reordered_plan_data["daily_menus"][0]["meals"] = list(reversed(original_meals))

    for meal in reordered_plan_data["daily_menus"][0]["meals"]:
        grams = meal.get("grams")
        if isinstance(grams, dict):
            meal["grams"] = {key: value for key, value in reversed(list(grams.items()))}

    reordered_payload = deepcopy(payload)
    reordered_payload["plan_data"] = reordered_plan_data
    reordered = client.post(
        "/api/v1/pro/meal/shopping-list", json=reordered_payload, headers=pro_headers
    )
    assert reordered.status_code == 200, reordered.text
    assert reordered.headers["content-type"].startswith("application/json")
    reordered_body = reordered.json()
    assert _without_generated_at(first_body) == _without_generated_at(reordered_body)

    categories = first_body["categories"]
    category_titles = [category["title"] for category in categories]
    assert category_titles == sorted(category_titles)

    for category in categories:
        item_names = [item["name"] for item in category["items"]]
        assert item_names == sorted(item_names)
        for item in category["items"]:
            assert item["recipe_refs"] == sorted(item["recipe_refs"])

"""Fast-lane coverage for USDA/FDC parser compatibility branches."""

from __future__ import annotations

import asyncio

from core.food_apis.usda_client import USDAClient


def _close_client(client: USDAClient) -> None:
    asyncio.run(client.close())


def test_usda_client_normalizes_current_fdc_payload_variants() -> None:
    client = USDAClient()
    try:
        food_item = client._parse_food_item(
            {
                "fdcId": 2650000,
                "description": "Example branded cereal",
                "dataType": "Branded",
                "publishedDate": "2026-04-01",
                "brandedFoodCategory": "Breakfast Cereals",
                "brandOwner": "Example Foods LLC",
                "brandName": "EXAMPLE",
                "gtinUPC": "00011122233344",
                "foodNutrients": [
                    {"nutrient": {"id": "1003"}, "amount": "8.0"},
                    {"nutrientId": 1004, "value": 2.5},
                    {"nutrientId": "1005", "value": "0"},
                    {"nutrientId": "1008", "value": "160"},
                    {"nutrientId": "999999", "value": "ignored"},
                    {"nutrientId": "not-an-id", "value": "5.0"},
                ],
            }
        )

        assert food_item is not None
        assert food_item.fdc_id == 2650000
        assert food_item.description == "Example branded cereal"
        assert food_item.data_type == "Branded"
        assert food_item.publication_date == "2026-04-01"
        assert food_item.food_category == "Breakfast Cereals"
        assert food_item.brand_owner == "Example Foods LLC"
        assert food_item.brand_name == "EXAMPLE"
        assert food_item.gtin_upc == "00011122233344"
        assert food_item.nutrients_per_100g == {
            "protein_g": 8.0,
            "fat_g": 2.5,
            "carbs_g": 0.0,
            "kcal": 160.0,
        }
    finally:
        _close_client(client)


def test_usda_client_rejects_malformed_or_sparse_fdc_payloads() -> None:
    client = USDAClient()
    try:
        assert client._parse_food_item(None) is None
        assert client._parse_food_item("not-a-mapping") is None
        assert client._parse_food_item({"fdcId": True}) is None
        assert client._parse_food_item({"fdcId": "not-an-int"}) is None

        malformed_amount = {
            "fdcId": "2650001",
            "description": 123,
            "dataType": None,
            "foodCategory": {"description": "Foundation Foods"},
            "foodNutrients": [
                {"nutrientId": "1003", "value": "8.0"},
                {"nutrientId": "1004", "value": "bad-value"},
                {"nutrientId": "1005", "value": "0"},
                {"nutrientId": "1008", "value": "160"},
            ],
        }
        assert client._parse_food_item(malformed_amount) is None

        sparse_amount = {
            "fdcId": "2650002",
            "foodCategory": "Foundation Foods",
            "foodNutrients": [
                {"nutrientId": "1003"},
                {"nutrient": {"id": True}, "amount": "9"},
                {"nutrient": "bad-shape", "amount": "10"},
            ],
        }
        assert client._parse_food_item(sparse_amount) is None
    finally:
        _close_client(client)

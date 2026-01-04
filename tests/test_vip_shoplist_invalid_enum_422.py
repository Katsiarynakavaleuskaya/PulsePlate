# -*- coding: utf-8 -*-
"""Parametrized tests for invalid enum → 422 (daily/weekly endpoints).

RU: Параметризованные тесты на invalid enum → 422 для daily/weekly.
EN: Parametrized tests for invalid enum → 422 for daily/weekly endpoints.

This test ensures that invalid enum values return 422 (not 500) consistently
across daily/weekly endpoints, matching /generate behavior.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import _enable_vip


def _valid_payload_for_daily() -> dict[str, Any]:
    """Valid payload for daily endpoint."""
    return {
        "items": [
            {"food_id": "chicken", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "chicken",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }


def _valid_payload_for_weekly() -> dict[str, Any]:
    """Valid payload for weekly endpoint."""
    return {
        "days": [
            {
                "items": [
                    {"food_id": "chicken", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"},
                ],
                "packaging_rules": [
                    {
                        "food_id": "chicken",
                        "pack_size": {"value": "500", "unit": "G"},
                        "rounding": "CEIL",
                        "min_packs": 1,
                    },
                ],
            },
        ],
    }


def _inject_invalid_enum(payload: dict, field: str, value: str, endpoint: str) -> None:
    """
    Inject invalid enum value into payload.

    RU: Вставляет невалидное значение enum в payload для тестирования 422.
    EN: Injects invalid enum value into payload for 422 testing.
    """
    if endpoint == "/api/v1/vip/shoplist/daily":
        if field == "unit":
            payload["items"][0]["qty"]["unit"] = value
        elif field == "form":
            payload["items"][0]["form"] = value
        elif field == "rounding":
            payload["packaging_rules"][0]["rounding"] = value
        elif field == "pack_size_unit":
            payload["packaging_rules"][0]["pack_size"]["unit"] = value
    elif endpoint == "/api/v1/vip/shoplist/weekly":
        if field == "unit":
            payload["days"][0]["items"][0]["qty"]["unit"] = value
        elif field == "form":
            payload["days"][0]["items"][0]["form"] = value
        elif field == "rounding":
            payload["days"][0]["packaging_rules"][0]["rounding"] = value
        elif field == "pack_size_unit":
            payload["days"][0]["packaging_rules"][0]["pack_size"]["unit"] = value


@pytest.mark.parametrize(
    "endpoint,payload_factory",
    [
        ("/api/v1/vip/shoplist/daily", _valid_payload_for_daily),
        ("/api/v1/vip/shoplist/weekly", _valid_payload_for_weekly),
    ],
)
@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("unit", "INVALID_UNIT"),
        ("form", "INVALID_FORM"),
        ("rounding", "INVALID_ROUNDING"),
        ("pack_size_unit", "INVALID_UNIT"),
    ],
)
def test_vip_shoplist_invalid_enum_returns_422(
    endpoint: str,
    payload_factory: Callable[..., dict[str, Any]],
    field: str,
    bad_value: str,
    client_with_vip_access: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Invalid enum should return 422 (not 500), consistent for daily/weekly.

    RU: Невалидный enum должен возвращать 422 (не 500), одинаково для daily/weekly.
    EN: Invalid enum must return 422 (not 500), consistent for daily/weekly.
    """
    _enable_vip(monkeypatch)

    payload = payload_factory()
    _inject_invalid_enum(payload, field, bad_value, endpoint)

    r = client_with_vip_access.post(endpoint, json=payload)

    assert (
        r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    ), f"Expected 422 for invalid {field}={bad_value}, got {r.status_code}: {r.text}"

    # Verify error structure (Pydantic validation)
    data = r.json()
    errors = data.get("detail", [])
    assert isinstance(errors, list) or isinstance(data.get("detail"), str)

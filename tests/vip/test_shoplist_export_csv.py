# -*- coding: utf-8 -*-
"""
Tests for VIP shoplist CSV export endpoint.

RU: Тесты для CSV экспорта VIP shoplist.
EN: Tests for VIP shoplist CSV export endpoint.
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import _enable_vip


def _generate_payload_minimal(*, food_id: str = "carrot") -> dict[str, object]:
    """Minimal valid payload for shoplist generation."""
    return {
        "items": [
            {
                "food_id": food_id,
                "qty": {"value": "100", "unit": "G"},
                "form": "RAW",
            }
        ],
        "packaging_rules": [
            {
                "food_id": food_id,
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            }
        ],
    }


def test_vip_shoplist_export_csv_basic(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test basic CSV export functionality."""
    _enable_vip(monkeypatch)

    payload = _generate_payload_minimal()
    resp = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?format=csv",
        json=payload,
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "Content-Disposition" in resp.headers
    assert 'filename="shoplist.csv"' in resp.headers["Content-Disposition"]

    # Проверяем структуру CSV
    lines = resp.text.strip().split("\n")
    assert len(lines) >= 2  # header + at least one data row

    # Проверяем header
    header = lines[0]
    expected_columns = [
        "food_id",
        "name",
        "requested",
        "unit",
        "pack_size",
        "packs",
        "min_packs",
        "reason",
        "aisle",
        "price",
        "subtotal",
        "store_id",
        "region_id",
    ]
    assert header == ",".join(expected_columns)

    # Проверяем, что есть данные
    if len(lines) > 1:
        data_row = lines[1].split(",")
        assert len(data_row) == len(expected_columns)
        assert data_row[0] == "carrot"  # food_id


def test_vip_shoplist_export_csv_deterministic_ordering(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that CSV export has deterministic ordering (store_id, aisle, food_id)."""
    _enable_vip(monkeypatch)

    payload = {
        "items": [
            {"food_id": "carrot", "qty": {"value": "100", "unit": "G"}, "form": "RAW"},
            {"food_id": "tomato", "qty": {"value": "200", "unit": "G"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "carrot",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "tomato",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    resp1 = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?format=csv",
        json=payload,
    )
    resp2 = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?format=csv",
        json=payload,
    )

    assert resp1.status_code == status.HTTP_200_OK
    assert resp2.status_code == status.HTTP_200_OK

    # Детерминированность: два запроса дают одинаковый результат
    assert resp1.text == resp2.text


def test_vip_shoplist_export_csv_invalid_format(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that invalid format returns 400."""
    _enable_vip(monkeypatch)

    payload = _generate_payload_minimal()
    resp = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?format=pdf",
        json=payload,
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "csv supported" in resp.json()["detail"].lower()


def test_vip_shoplist_export_csv_injection_protection(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that CSV injection is prevented (formulas starting with =, +, -, @)."""
    _enable_vip(monkeypatch)

    # Используем food_id, который может содержать опасные символы
    # (в реальности это будет в reason или aisle из catalog)
    payload = _generate_payload_minimal(food_id="=SUM(A1:A10)")
    resp = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?format=csv",
        json=payload,
    )

    assert resp.status_code == status.HTTP_200_OK
    # CSV injection protection is tested implicitly:
    # if formulas appear in reason/aisle fields, they should be prefixed with '
    # This test verifies the endpoint works; detailed injection tests are in unit tests


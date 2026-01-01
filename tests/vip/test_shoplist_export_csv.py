# -*- coding: utf-8 -*-
"""
Tests for VIP shoplist CSV export endpoint.

RU: Тесты для CSV экспорта VIP shoplist.
EN: Tests for VIP shoplist CSV export endpoint.
"""

from __future__ import annotations

import csv
import io

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

    # Парсим CSV через csv.reader
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert len(rows) >= 2  # header + at least one data row

    # Проверяем header
    header = rows[0]
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
    assert header == expected_columns

    # Проверяем, что есть данные
    assert len(rows) > 1, "CSV must contain at least one data row"
    data_row = rows[1]
    assert len(data_row) == len(expected_columns)
    assert data_row[0] == "carrot"  # food_id


def test_vip_shoplist_export_csv_deterministic_ordering(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that CSV export has deterministic ordering (empty values last)."""
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

    resp = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?format=csv",
        json=payload,
    )

    assert resp.status_code == status.HTTP_200_OK

    # Парсим CSV
    rows = list(csv.reader(io.StringIO(resp.text)))
    header = rows[0]
    data = rows[1:]

    # Проверяем сортировку: empty values last
    store_i = header.index("store_id")
    aisle_i = header.index("aisle")
    food_i = header.index("food_id")

    # Извлекаем ключи сортировки
    keys = [(r[store_i], r[aisle_i], r[food_i]) for r in data]

    # Проверяем, что сортировка соответствует правилу: empty last
    expected_keys = sorted(keys, key=lambda k: (k[0] == "", k[0], k[1] == "", k[1], k[2]))
    assert keys == expected_keys, "Sorting should put empty values last"


def test_vip_shoplist_export_csv_invalid_format(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that invalid format returns 400."""
    _enable_vip(monkeypatch)

    payload = _generate_payload_minimal()
    resp = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?export_format=json",
        json=payload,
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    detail = resp.json()["detail"].lower()
    assert "csv" in detail or "pdf" in detail


def test_vip_shoplist_export_csv_injection_protection(
    monkeypatch: pytest.MonkeyPatch,
    client_with_vip_access: TestClient,
) -> None:
    """Test that CSV injection is prevented (formulas starting with =, +, -, @)."""
    _enable_vip(monkeypatch)

    # Используем food_id с опасными символами (проверяем sanitize для food_id)
    payload = _generate_payload_minimal(food_id="=SUM(A1:A10)")
    resp = client_with_vip_access.post(
        "/api/v1/vip/shoplist/export?format=csv",
        json=payload,
    )

    assert resp.status_code == status.HTTP_200_OK

    # Парсим CSV
    rows = list(csv.reader(io.StringIO(resp.text)))
    header = rows[0]
    data = rows[1:]

    assert len(data) > 0, "CSV must contain data rows"

    # Проверяем, что food_id с формулой экранирован
    food_i = header.index("food_id")
    food_id_cell = data[0][food_i]

    # Главное: проверяем, что добавился апостроф для защиты от CSV injection
    assert food_id_cell.startswith("'="), f"CSV injection not prevented: {food_id_cell}"

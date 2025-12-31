# -*- coding: utf-8 -*-
"""Tests for VIP shoplist generate endpoint (ShoplistEngine v1).

RU: Тесты для VIP endpoint генерации списка покупок (ShoplistEngine v1).
EN: Tests for VIP shoplist generation endpoint (ShoplistEngine v1).
"""

from __future__ import annotations

import pytest


def test_vip_shoplist_generate_happy_path(client_with_vip_access, monkeypatch):
    """Test happy path: generate shoplist with packaging rules."""
    # VIP enabled - patch in router module where it's imported
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1.5", "unit": "KG"}, "form": "RAW"},
            {"food_id": "flour", "qty": {"value": "500", "unit": "G"}, "form": "RAW"},
            {"food_id": "eggs", "qty": {"value": "6", "unit": "PCS"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "flour",
                "pack_size": {"value": "1000", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "eggs",
                "pack_size": {"value": "6", "unit": "PCS"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    assert "packed" in data and "unpacked" in data
    assert len(data["unpacked"]) == 0
    assert len(data["packed"]) == 2

    flour = next(p for p in data["packed"] if p["food_id"] == "flour")
    eggs = next(p for p in data["packed"] if p["food_id"] == "eggs")

    assert flour["packs"] == 2
    assert flour["provided"]["value"] == "2000"
    # Verify unit mapping (G for flour)
    assert flour["requested"]["unit"] == "G"
    assert flour["pack_size"]["unit"] == "G"
    assert flour["provided"]["unit"] == "G"
    assert flour["overage"]["unit"] == "G"
    # Verify rounding and min_packs
    assert flour["rounding"] == "CEIL"
    assert flour["min_packs"] == 1

    assert eggs["packs"] == 1
    assert eggs["provided"]["value"] == "6"
    # Verify unit mapping (PCS for eggs)
    assert eggs["requested"]["unit"] == "PCS"
    assert eggs["pack_size"]["unit"] == "PCS"
    assert eggs["provided"]["unit"] == "PCS"
    assert eggs["overage"]["unit"] == "PCS"
    # Verify rounding and min_packs
    assert eggs["rounding"] == "CEIL"
    assert eggs["min_packs"] == 1


def test_vip_shoplist_generate_vip_disabled_404(client_with_vip_access, monkeypatch):
    """Test that VIP disabled returns 404."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: False)

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json={"items": []})
    assert r.status_code == 404


def test_vip_shoplist_generate_validation_422(client_with_vip_access, monkeypatch):
    """Test validation errors return 422."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    # Negative value forbidden by schema (Decimal ge=0)
    r = client_with_vip_access.post(
        "/api/v1/vip/shoplist/generate",
        json={"items": [{"food_id": "x", "qty": {"value": "-1", "unit": "G"}, "form": "RAW"}]},
    )
    assert r.status_code == 422


def test_vip_shoplist_generate_empty_items(client_with_vip_access, monkeypatch):
    """Test empty items list returns empty result."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json={"items": []})
    assert r.status_code == 200
    data = r.json()
    assert data["packed"] == []
    assert data["unpacked"] == []


def test_vip_shoplist_generate_no_packaging_rules(client_with_vip_access, monkeypatch):
    """Test items without packaging rules go to unpacked."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "500", "unit": "G"}, "form": "RAW"},
            {"food_id": "eggs", "qty": {"value": "6", "unit": "PCS"}, "form": "RAW"},
        ],
        "packaging_rules": [],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["packed"]) == 0
    assert len(data["unpacked"]) == 2


def test_vip_shoplist_generate_partial_packaging(client_with_vip_access, monkeypatch):
    """Test partial packaging: some items packed, some unpacked."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

    payload = {
        "items": [
            {"food_id": "flour", "qty": {"value": "1000", "unit": "G"}, "form": "RAW"},
            {"food_id": "eggs", "qty": {"value": "6", "unit": "PCS"}, "form": "RAW"},
            {"food_id": "milk", "qty": {"value": "500", "unit": "ML"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "flour",
                "pack_size": {"value": "1000", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client_with_vip_access.post("/api/v1/vip/shoplist/generate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["packed"]) == 1
    assert len(data["unpacked"]) == 2
    assert data["packed"][0]["food_id"] == "flour"
    assert {u["food_id"] for u in data["unpacked"]} == {"eggs", "milk"}

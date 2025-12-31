# -*- coding: utf-8 -*-
"""Diff-coverage tests for VIP shoplist router and schemas.

RU: Тесты только для закрытия веток/строк, которые видит diff-cover в PR.
EN: Tests dedicated to covering PR-changed lines (diff-coverage guard).

These tests intentionally target:
- app/routers/vip_shoplist.py: KeyError -> HTTP 422 branches in mapping helpers
- app/schemas/vip_shoplist.py: defaults/serialization branches
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _enable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable VIP module for tests."""
    # Важно: monkeypatch по модулю роутера (иначе может не сработать из-за import binding)
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)


def test_map_unit_invalid_returns_422() -> None:
    """Cover _map_unit KeyError -> HTTPException(422) branch."""
    from fastapi import HTTPException, status
    from app.routers.vip_shoplist import _map_unit

    # Pydantic validates DTO before reaching _map_unit, so test function directly
    with pytest.raises(HTTPException) as exc_info:
        _map_unit("INVALID_UNIT")
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid unit" in exc_info.value.detail


def test_map_rounding_invalid_returns_422() -> None:
    """Cover _map_rounding KeyError -> HTTPException(422) branch."""
    from fastapi import HTTPException, status
    from app.routers.vip_shoplist import _map_rounding

    # Pydantic validates DTO before reaching _map_rounding, so test function directly
    with pytest.raises(HTTPException) as exc_info:
        _map_rounding("INVALID_ROUNDING")
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid rounding" in exc_info.value.detail


def test_vip_shoplist_schemas_defaults_and_serialization() -> None:
    """Cover schema defaults + model_dump paths for diff-coverage."""
    from app.schemas.vip_shoplist import (
        PackedLineDTO,
        QuantityDTO,
        ShoplistGenerateRequest,
        ShoplistGenerateResponse,
        UnpackedLineDTO,
    )

    # 1) default branch for packaging_rules (field omitted)
    req1 = ShoplistGenerateRequest(
        items=[{"food_id": "x", "qty": {"value": "1", "unit": "G"}, "form": "RAW"}]
    )
    assert req1.items[0].food_id == "x"
    assert req1.packaging_rules is None

    # 2) explicit empty list branch
    req2 = ShoplistGenerateRequest(
        items=[{"food_id": "x", "qty": {"value": "1", "unit": "G"}, "form": "RAW"}],
        packaging_rules=[],
    )
    assert req2.packaging_rules == []

    # 3) response model_dump branch
    resp = ShoplistGenerateResponse(
        packed=[
            PackedLineDTO(
                food_id="x",
                requested=QuantityDTO(value="1", unit="G"),
                pack_size=QuantityDTO(value="1", unit="G"),
                packs=1,
                provided=QuantityDTO(value="1", unit="G"),
                overage=QuantityDTO(value="0", unit="G"),
                rounding="CEIL",
                min_packs=0,
            )
        ],
        unpacked=[
            UnpackedLineDTO(
                food_id="y",
                requested=QuantityDTO(value="2", unit="PCS"),
            )
        ],
    )
    dumped = resp.model_dump()
    assert dumped["packed"][0]["food_id"] == "x"
    assert dumped["unpacked"][0]["food_id"] == "y"

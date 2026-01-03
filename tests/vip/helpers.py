# -*- coding: utf-8 -*-
"""Shared helpers for VIP tests."""

from __future__ import annotations

from decimal import Decimal

from app.schemas.vip_shoplist import QuantityDTO, UnitDTO


def qty(value: str, unit: UnitDTO = "G") -> QuantityDTO:
    return QuantityDTO(value=Decimal(value), unit=unit)

# -*- coding: utf-8 -*-
"""
RU: Экспорт shoplist (CSV/PDF) — слой сервисов (без FastAPI).
EN: Shoplist export utilities (CSV/PDF) — service layer (no FastAPI).
"""

from __future__ import annotations

from app.services.shoplist_export.csv_export import export_shoplist_to_csv

__all__ = ["export_shoplist_to_csv"]

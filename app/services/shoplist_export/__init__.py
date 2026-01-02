# -*- coding: utf-8 -*-
"""
RU: Экспорт shoplist (CSV/PDF) — слой сервисов (без FastAPI).
EN: Shoplist export utilities (CSV/PDF) — service layer (no FastAPI).
"""

from __future__ import annotations

from typing import Any

from app.services.shoplist_export.csv_export import export_shoplist_to_csv


def export_shoplist_to_pdf(*args: Any, **kwargs: Any) -> bytes:
    """
    RU: Экспортирует VIP shoplist в PDF. Импортируется лениво, чтобы:
      - не падать при старте приложения из-за необязательных зависимостей,
      - не ловить ImportError на import-time (особенно в Docker/CI).
    EN: Exports VIP shoplist to PDF. Lazy import to avoid import-time failures.
    """
    try:
        from app.services.shoplist_export.pdf_export import export_shoplist_to_pdf as _impl
    except ImportError as e:  # pragma: no cover
        # reportlab отсутствует или модуль не собран — отдаём ясную ошибку по месту вызова
        raise ImportError("PDF export is unavailable (missing pdf_export or reportlab).") from e

    return _impl(*args, **kwargs)


__all__ = ["export_shoplist_to_csv", "export_shoplist_to_pdf"]

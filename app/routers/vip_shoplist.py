"""VIP shoplist preview endpoint (offline/deterministic).

Contract:
- VIP tier gated
- VIP_MODULE_ENABLED feature-flag gated (OFF -> 404)
- No DB, no persistence, no external calls
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.api_tiers import require_vip_tier
from app.schemas.vip_shoplist import ShoplistPreviewItem, ShoplistPreviewResponse
from core.shoplist_preview.preview_service import ShoplistPreviewService

router = APIRouter(prefix="/shoplist", tags=["vip"])


def _vip_module_enabled() -> bool:
    raw = os.getenv("VIP_MODULE_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def require_vip_module_enabled() -> None:
    if not _vip_module_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


@router.get("/preview", response_model=ShoplistPreviewResponse)
async def vip_shoplist_preview(
    _enabled: Annotated[None, Depends(require_vip_module_enabled)],
    _vip: Annotated[Any, Depends(require_vip_tier)],
) -> ShoplistPreviewResponse:
    preview = ShoplistPreviewService().build_preview()
    return ShoplistPreviewResponse(
        items=[
            ShoplistPreviewItem(category=i.category, name=i.name, quantity=i.quantity)
            for i in preview.items
        ]
    )


__all__ = ["router"]

"""VIP shoplist preview endpoint (offline/deterministic).

Contract:
- VIP tier gated
- VIP_MODULE_ENABLED feature-flag gated (OFF -> 404)
- No DB, no persistence, no external calls
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.api_tiers import require_vip_tier
from app.schemas.vip_shoplist import ShoplistPreviewItem, ShoplistPreviewResponse
from app.utils.feature_flags import is_vip_module_enabled
from core.shoplist_preview.preview_service import build_preview

router = APIRouter(prefix="/shoplist", tags=["vip"])


def require_vip_module_enabled() -> None:
    if not is_vip_module_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


@router.get("/preview", response_model=ShoplistPreviewResponse)
async def vip_shoplist_preview(
    _enabled: Annotated[None, Depends(require_vip_module_enabled)],
    _vip: Annotated[str, Depends(require_vip_tier)],
) -> ShoplistPreviewResponse:
    preview = build_preview()
    return ShoplistPreviewResponse(
        items=[
            ShoplistPreviewItem(category=i.category, name=i.name, quantity=i.quantity)
            for i in preview.items
        ]
    )


__all__ = ["router"]

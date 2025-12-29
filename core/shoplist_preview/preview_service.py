from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ShoplistPreviewItem", "ShoplistPreview", "build_preview"]


@dataclass(frozen=True)
class ShoplistPreviewItem:
    category: str
    name: str
    quantity: str


@dataclass(frozen=True)
class ShoplistPreview:
    items: tuple[ShoplistPreviewItem, ...]


def build_preview() -> ShoplistPreview:
    """Build a deterministic shopping list preview.

    Offline by construction: no DB, time, or network.
    """

    items = (
        ShoplistPreviewItem(category="vegetables", name="Tomatoes", quantity="500 g"),
        ShoplistPreviewItem(category="protein", name="Eggs", quantity="10 pcs"),
        ShoplistPreviewItem(category="dairy", name="Greek yogurt", quantity="500 g"),
        ShoplistPreviewItem(category="grains", name="Rice", quantity="1 kg"),
    )
    return ShoplistPreview(items=items)

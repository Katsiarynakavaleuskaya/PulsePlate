# -*- coding: utf-8 -*-
"""
VIP Shoplist Schemas

RU: Схемы для VIP списка покупок (preview и generate endpoints).
EN: Schemas for VIP shopping list (preview and generate endpoints).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.catalog import CatalogInfoDTO

# RU: DTO слой — адаптер над core моделями. Здесь можно использовать Decimal.
# EN: DTO layer — adapter over core models. Decimal is allowed.

# RU: Константа для explainability (один источник правды).
# EN: Constant for explainability (single source of truth).
REASON_NO_PACKAGING_RULE = "no_packaging_rule"

# RU: Decimal сериализуется в JSON как строка автоматически (Pydantic v2).
# EN: Decimal is automatically serialized as string in JSON (Pydantic v2).

UnitDTO = Literal["G", "ML", "PCS", "KG", "L"]  # расширишь по мере надобности / expand as needed
FoodFormDTO = Literal[
    "RAW", "COOKED", "FROZEN", "DRIED", "CANNED"
]  # расширится позже / will expand later
RoundingModeDTO = Literal["CEIL", "NEAREST", "NONE"]  # rounding mode


class QuantityDTO(BaseModel):
    """Quantity with value and unit (deterministic, no prices)."""

    value: Decimal = Field(
        ...,
        ge=0,
        description="Decimal value (serialized as string in JSON, no floats). Example: '100', '12.5'",
        examples=[Decimal("100"), Decimal("150.5"), Decimal("0")],
    )
    unit: UnitDTO = Field(..., description="Measurement unit", examples=["G", "ML", "PCS"])


class ShoplistItemDTO(BaseModel):
    """Shopping list item specification (food, quantity, form)."""

    food_id: str = Field(..., min_length=1, examples=["carrot", "tomato"])
    qty: QuantityDTO = Field(..., description="Requested quantity")
    form: FoodFormDTO = Field(default="RAW", description="Food form", examples=["RAW", "COOKED"])


class PackageRuleDTO(BaseModel):
    """Packaging rule for a food item (pack size, rounding mode, minimum packs)."""

    food_id: str = Field(..., min_length=1, examples=["carrot", "tomato"])
    pack_size: QuantityDTO = Field(..., description="Pack size for this food")
    rounding: RoundingModeDTO = Field(
        default="CEIL",
        description="Rounding mode (CEIL=never undersupply, NEAREST=prefer oversupply)",
    )
    min_packs: int = Field(1, ge=1, description="Minimum packs to buy (>=1)", examples=[1, 2])


class ShoplistGenerateRequest(BaseModel):
    """Request payload for POST /api/v1/vip/shoplist/generate."""

    items: list[ShoplistItemDTO] = Field(
        default_factory=list, description="Shopping list items (can be empty)"
    )
    packaging_rules: list[PackageRuleDTO] | None = Field(
        default=None,
        description="Optional. If missing/None, items without rules go to 'unpacked'.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {
                            "food_id": "carrot",
                            "qty": {"value": "100", "unit": "G"},
                            "form": "RAW",
                        }
                    ],
                    "packaging_rules": [
                        {
                            "food_id": "carrot",
                            "pack_size": {"value": "500", "unit": "G"},
                            "rounding": "CEIL",
                            "min_packs": 1,
                        }
                    ],
                }
            ]
        }
    }


class ShoplistDailyRequest(BaseModel):
    """Request payload for POST /api/v1/vip/shoplist/daily.

    Same contract as ShoplistGenerateRequest.
    """

    items: list[ShoplistItemDTO] = Field(
        default_factory=list, description="Shopping list items (can be empty)"
    )
    packaging_rules: list[PackageRuleDTO] | None = Field(
        default=None,
        description="Optional. If missing/None, items without rules go to 'unpacked'.",
    )


class ShoplistWeeklyDayRequest(BaseModel):
    """Request payload for one day in weekly shoplist.

    Same contract as ShoplistGenerateRequest per day.
    """

    items: list[ShoplistItemDTO] = Field(
        default_factory=list, description="Shopping list items for this day (can be empty)"
    )
    packaging_rules: list[PackageRuleDTO] | None = Field(
        default=None,
        description="Optional. If missing/None, items without rules go to 'unpacked'.",
    )


class ShoplistWeeklyRequest(BaseModel):
    """Request payload for POST /api/v1/vip/shoplist/weekly."""

    days: list[ShoplistWeeklyDayRequest] = Field(
        ...,
        description="One element per day. Contract: length = as requested by client (no fixed 7-day requirement).",
    )


# --- Response DTOs ---


class PackedLineDTO(BaseModel):
    """Packed shopping list line with packaging details and explainability reasons."""

    food_id: str = Field(..., examples=["carrot", "tomato"])
    requested: QuantityDTO = Field(..., description="Requested quantity")
    pack_size: QuantityDTO = Field(..., description="Pack size used")
    packs: int = Field(..., ge=1, description="Number of packs to buy", examples=[1, 2])
    provided: QuantityDTO = Field(..., description="Total quantity provided (packs * pack_size)")
    overage: QuantityDTO = Field(..., description="Overage (provided - requested)")
    rounding: RoundingModeDTO = Field(..., description="Rounding mode applied")
    min_packs: int = Field(..., ge=1, description="Minimum packs enforced")
    reasons: list[str] = Field(
        default_factory=list,
        description="Explainability reasons (stable order, deterministic)",
        examples=[
            ["rounding=CEIL", "min_packs=1", "requested=100 G", "provided=500 G", "overage=400 G"]
        ],
    )
    catalog: Optional[CatalogInfoDTO] = Field(
        default=None,
        description="Optional catalog enrichment (adapter-only, fail-soft).",
    )


class UnpackedLineDTO(BaseModel):
    """Unpacked shopping list line (no packaging rule available)."""

    food_id: str = Field(..., examples=["carrot", "tomato"])
    requested: QuantityDTO = Field(..., description="Requested quantity")
    # RU: Default, чтобы не ломать старые конструкторы и гарантировать стабильный API контракт.
    # EN: Default to keep backward compatibility and stable API contract.
    reason: str = Field(
        default=REASON_NO_PACKAGING_RULE,
        description="Why item is unpacked",
        examples=[REASON_NO_PACKAGING_RULE],
    )
    catalog: Optional[CatalogInfoDTO] = Field(
        default=None,
        description="Optional catalog enrichment (adapter-only, fail-soft).",
    )


class ShoplistAnalyticsDTO(BaseModel):
    """Analytics summary for shoplist generation (deterministic, no prices)."""

    total_lines: int = Field(..., ge=0, description="Total items (packed + unpacked)")
    packed_lines: int = Field(..., ge=0, description="Items with packaging rules applied")
    unpacked_lines: int = Field(..., ge=0, description="Items without packaging rules")

    # RU: Decimal отдаём строкой → стабильный JSON, без float.
    # EN: Return Decimal totals as strings for stable JSON and no floats.
    total_overage_by_unit: dict[UnitDTO, str] = Field(
        default_factory=dict,
        description="Aggregated overage per unit type (Decimal values serialized as strings)",
        examples=[{"G": "150", "ML": "0"}],
    )


class ShoplistGenerateResponse(BaseModel):
    """Response for POST /api/v1/vip/shoplist/generate (deterministic, no prices)."""

    packed: list[PackedLineDTO] = Field(
        default_factory=list, description="Items with packaging rules applied"
    )
    unpacked: list[UnpackedLineDTO] = Field(
        default_factory=list, description="Items without packaging rules"
    )

    # RU: Optional для backward-compat (старые конструкторы/тесты).
    # EN: Optional for backward compatibility with older constructors/tests.
    # NOTE: generate/daily/weekly SHOULD include analytics for contract parity.
    analytics: ShoplistAnalyticsDTO | None = Field(
        default=None,
        description="Analytics summary (included by default in generate/daily/weekly endpoints)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "packed": [
                        {
                            "food_id": "carrot",
                            "requested": {"value": "100", "unit": "G"},
                            "pack_size": {"value": "500", "unit": "G"},
                            "packs": 1,
                            "provided": {"value": "500", "unit": "G"},
                            "overage": {"value": "400", "unit": "G"},
                            "rounding": "CEIL",
                            "min_packs": 1,
                            "reasons": [
                                "rounding=CEIL",
                                "min_packs=1",
                                "requested=100 G",
                                "provided=500 G",
                                "overage=400 G",
                            ],
                        }
                    ],
                    "unpacked": [],
                    "analytics": {
                        "total_lines": 1,
                        "packed_lines": 1,
                        "unpacked_lines": 0,
                        "total_overage_by_unit": {"G": "400"},
                    },
                }
            ]
        }
    }


class ShoplistWeeklyResponse(BaseModel):
    """Response for POST /api/v1/vip/shoplist/weekly."""

    days: list[ShoplistGenerateResponse] = Field(
        default_factory=list,
        description="One response per day (length = as requested by client)",
    )


# --- Preview schemas (legacy) ---


class ShoplistPreviewItem(BaseModel):
    """One shopping list preview item (deterministic, no prices)."""

    category: str = Field(..., examples=["vegetables"])
    name: str = Field(..., examples=["Tomatoes"])
    quantity: str = Field(..., examples=["500 g"])


class ShoplistPreviewMeta(BaseModel):
    """Preview metadata; explicitly states that prices are not included."""

    preview: bool = True
    currency: str | None = None
    prices_included: bool = False


class ShoplistPreviewResponse(BaseModel):
    """Response for GET /api/v1/vip/shoplist/preview."""

    items: list[ShoplistPreviewItem]
    meta: ShoplistPreviewMeta = Field(default_factory=ShoplistPreviewMeta)

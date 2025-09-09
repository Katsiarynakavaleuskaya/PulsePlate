# -*- coding: utf-8 -*-
"""
VIP Schemas

RU: Схемы для VIP функций - микронутриентные цели, авто-ремонт, региональные настройки.
EN: Schemas for VIP features - micronutrient goals, auto-repair, regional settings.
"""

from enum import Enum
from typing import List, Set

from pydantic import BaseModel, Field


class Region(str, Enum):
    """RU: Поддерживаемые регионы; EN: Supported regions."""

    ES = "es"  # Spain
    US = "us"  # United States


class Currency(str, Enum):
    """RU: Поддерживаемые валюты; EN: Supported currencies."""

    EUR = "EUR"
    USD = "USD"


class MicronutrientGoal(BaseModel):
    """
    RU: Цель по микронутриенту с приоритетом.
    EN: Micronutrient goal with priority.
    """

    nutrient: str = Field(..., description="Nutrient name (e.g., 'Fe_mg', 'VitD_IU')")
    target_daily: float = Field(
        ..., gt=0, description="Daily target in appropriate units"
    )
    priority: int = Field(
        default=1, ge=1, le=5, description="Priority 1-5 (5 = highest)"
    )
    deficiency_threshold: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Deficiency threshold (0.8 = 80% of target)",
    )


class AutoRepairConfig(BaseModel):
    """
    RU: Конфигурация авто-ремонта меню.
    EN: Auto-repair menu configuration.
    """

    enabled: bool = Field(default=True, description="Enable auto-repair")
    max_replacements: int = Field(
        default=3, ge=1, le=10, description="Max ingredient replacements per meal"
    )
    preserve_flags: Set[str] = Field(
        default_factory=set, description="Dietary flags to preserve (VEG, GF, etc.)"
    )
    prefer_local_products: bool = Field(
        default=True, description="Prefer local/regional products"
    )


class RegionalConfig(BaseModel):
    """
    RU: Региональная конфигурация.
    EN: Regional configuration.
    """

    region: Region = Field(..., description="Target region")
    currency: Currency = Field(..., description="Local currency")
    language: str = Field(default="en", description="Language code")
    units_system: str = Field(
        default="metric", description="Units system (metric/imperial)"
    )
    local_brands: List[str] = Field(
        default_factory=list, description="Preferred local brands"
    )


class ShoplistConfig(BaseModel):
    """
    RU: Конфигурация списка покупок.
    EN: Shopping list configuration.
    """

    round_to_packages: bool = Field(
        default=True, description="Round quantities to package sizes"
    )
    include_alternatives: bool = Field(
        default=True, description="Include product alternatives"
    )
    group_by_category: bool = Field(
        default=True, description="Group items by food category"
    )
    show_prices: bool = Field(default=True, description="Show estimated prices")


class RecipeGenerationConfig(BaseModel):
    """
    RU: Конфигурация генерации рецептов.
    EN: Recipe generation configuration.
    """

    max_ingredients: int = Field(
        default=8, ge=3, le=15, description="Max ingredients per recipe"
    )
    cooking_time_max: int = Field(
        default=60, ge=15, le=180, description="Max cooking time in minutes"
    )
    difficulty_levels: List[str] = Field(
        default=["easy", "medium"], description="Allowed difficulty levels"
    )
    cuisine_styles: List[str] = Field(
        default_factory=list, description="Preferred cuisine styles"
    )


class VIPConfig(BaseModel):
    """
    RU: Основная конфигурация VIP функций.
    EN: Main VIP features configuration.
    """

    micronutrient_goals: List[MicronutrientGoal] = Field(default_factory=list)
    auto_repair: AutoRepairConfig = Field(default_factory=AutoRepairConfig)
    regional: RegionalConfig = Field(
        default_factory=lambda: RegionalConfig(region=Region.US, currency=Currency.USD)
    )
    shoplist: ShoplistConfig = Field(default_factory=ShoplistConfig)
    recipe_generation: RecipeGenerationConfig = Field(
        default_factory=RecipeGenerationConfig
    )
    enabled_features: Set[str] = Field(
        default_factory=set, description="Enabled VIP features"
    )


class VIPFeatureFlags(BaseModel):
    """
    RU: Флаги функций VIP.
    EN: VIP feature flags.
    """

    micronutrient_goals_enabled: bool = Field(default=False)
    auto_repair_enabled: bool = Field(default=False)
    regional_pricing_enabled: bool = Field(default=False)
    smart_shoplist_enabled: bool = Field(default=False)
    recipe_generation_enabled: bool = Field(default=False)
    i18n_enabled: bool = Field(default=False)

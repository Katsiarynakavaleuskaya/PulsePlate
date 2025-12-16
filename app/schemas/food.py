"""
Food Schemas

RU: Базовая модель продукта с нутриентами, ценой и происхождением.
EN: Base food model with nutrients, pricing and provenance.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class FoodItem(BaseModel):
    """
    RU: Полная модель продукта с прослеживаемостью.
    EN: Complete food model with provenance tracking.
    """

    id: str
    canonical_name: str
    group: Optional[str] = None
    per_g: float = 100.0  # RU: норма на 100 г; EN: per 100g baseline
    kcal: float
    # Primary macronutrients: defaults to 0.0 for sources that omit them
    # (e.g., USDA may omit carbs_g for pure protein/fat foods like chicken breast)
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    fiber_g: float = 0.0
    Fe_mg: float = 0.0
    Ca_mg: float = 0.0
    K_mg: float = 0.0
    Mg_mg: float = 0.0
    VitD_IU: float = 0.0
    B12_ug: float = 0.0
    Folate_ug: float = 0.0
    Iodine_ug: float = 0.0
    flags: List[str] = Field(default_factory=list)  # e.g. ["VEG","GF"]
    brand: Optional[str] = None
    gtin: Optional[str] = None
    fdc_id: Optional[str] = None
    source: str = "USDA"  # Changed from "USDA|OFF" - use single source identifier
    source_priority: int = 0
    version_date: str
    price_per_100g: float = 0.0


class FoodHit(BaseModel):
    """
    RU: Результат поиска (минимум данных для списка).
    EN: Search hit for list views.
    """

    id: str
    name: str
    kcal: float
    # Macronutrients: defaults to 0.0 for consistency with FoodItem
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0

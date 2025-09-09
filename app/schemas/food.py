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
    protein_g: float
    fat_g: float
    carbs_g: float
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
    source: str = "USDA|OFF"
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
    protein_g: float
    fat_g: float
    carbs_g: float

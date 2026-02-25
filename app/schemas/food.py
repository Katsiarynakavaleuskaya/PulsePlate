"""
Food Schemas

RU: Базовая модель продукта с нутриентами, ценой и происхождением.
EN: Base food model with nutrients, pricing and provenance.
"""

from __future__ import annotations

import ast
import json
import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _normalize_food_flags(value: object) -> List[str]:
    """
    Normalize legacy flags payloads to canonical list[str].

    RU: Нормализует legacy-представления flags в канонический список строк.
    EN: Normalizes legacy flags payloads to canonical list of strings.
    """
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw.lower() in {"null", "none"} or raw == "[]":
            return []

        # Attempt list-like payload parsing: JSON first, then Python literal style.
        if raw.startswith("[") and raw.endswith("]"):
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(raw)
                except (TypeError, ValueError, SyntaxError, json.JSONDecodeError):
                    continue
                if isinstance(parsed, (list, tuple, set)):
                    return [str(item).strip() for item in parsed if str(item).strip()]

        # Fallback for "VEG,GF" / "VEG;GF" / "VEG|GF".
        parts = [part.strip().strip("'\"") for part in re.split(r"[;,|]", raw)]
        normalized = [part for part in parts if part]
        return normalized if normalized else []

    return []


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

    @field_validator("flags", mode="before")
    @classmethod
    def _parse_legacy_flags(cls, value: object) -> List[str]:
        """
        Support backward-compatible flags parsing for DB-backed rows.

        RU: Поддерживает backward-compatible парсинг flags для строк из БД.
        EN: Supports backward-compatible flags parsing for DB-backed rows.
        """
        return _normalize_food_flags(value)


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

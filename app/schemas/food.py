"""
Food Schemas

RU: Базовая модель продукта с нутриентами, ценой и происхождением.
EN: Base food model with nutrients, pricing and provenance.
"""

from __future__ import annotations

import ast
import json
import math
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
                except (TypeError, ValueError, SyntaxError):
                    continue
                if isinstance(parsed, (list, tuple, set)):
                    return [str(item).strip() for item in parsed if str(item).strip()]

        # Fallback for "VEG,GF" / "VEG;GF" / "VEG|GF".
        parts = [part.strip().strip("'\"") for part in re.split(r"[;,|]", raw)]
        normalized = [part for part in parts if part]
        return normalized if normalized else []

    return []


def _parse_json_mapping(value: object) -> dict[str, str]:
    """
    Parse JSON/dict payloads into dict[str, str].

    RU: Парсит JSON/dict в dict[str, str].
    EN: Parses JSON/dict payloads into dict[str, str].
    """

    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw.lower() in {"null", "none"}:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if isinstance(parsed, dict):
            return {str(key): str(item) for key, item in parsed.items()}
    return {}


def _parse_json_float_dict(value: object) -> dict[str, float]:
    """
    Parse JSON/dict payloads into dict[str, float] for per-nutrient confidence.

    RU: Парсит JSON/dict в dict[str, float] для confidence по нутриентам.
    EN: Parses JSON/dict into dict[str, float] for per-nutrient confidence.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        out: dict[str, float] = {}
        for key, item in value.items():
            sk = str(key)
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                coerced = float(item)
                if math.isfinite(coerced) and coerced >= 0.0:
                    out[sk] = coerced
                continue
            if isinstance(item, str):
                raw = item.strip()
                if not raw:
                    continue
                try:
                    coerced = float(raw)
                except ValueError:
                    continue
                if math.isfinite(coerced) and coerced >= 0.0:
                    out[sk] = coerced
        return out
    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw.lower() in {"null", "none"}:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if isinstance(parsed, dict):
            return _parse_json_float_dict(parsed)
        return {}
    return {}


def _parse_json_inputs(value: object) -> List[dict[str, object]]:
    """Parse JSON/list payloads into list[dict[str, object]].

    RU: Парсит JSON/list в список словарей.
    EN: Parses JSON/list payloads into list of dictionaries.
    """

    if value is None:
        return []
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw.lower() in {"null", "none"}:
            return []
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return []
        if isinstance(parsed, list):
            return [dict(item) for item in parsed if isinstance(item, dict)]
    return []


class FoodItem(BaseModel):
    """RU: Полная модель продукта с прослеживаемостью. EN: Complete food model."""

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
    nutrition_inputs: List[dict[str, object]] = Field(default_factory=list)
    nutrition_provenance: dict[str, str] = Field(default_factory=dict)
    nutrition_confidence: float = 0.0
    nutrition_nutrient_confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("flags", mode="before")
    @classmethod
    def _parse_legacy_flags(cls, value: object) -> List[str]:
        """
        Support backward-compatible flags parsing for DB-backed rows.

        RU: Поддерживает backward-compatible парсинг flags для строк из БД.
        EN: Supports backward-compatible flags parsing for DB-backed rows.
        """
        return _normalize_food_flags(value)

    @field_validator("nutrition_inputs", mode="before")
    @classmethod
    def _parse_nutrition_inputs(cls, value: object) -> List[dict[str, object]]:
        return _parse_json_inputs(value)

    @field_validator("nutrition_provenance", mode="before")
    @classmethod
    def _parse_nutrition_provenance(cls, value: object) -> dict[str, str]:
        return _parse_json_mapping(value)

    @field_validator("nutrition_confidence", mode="before")
    @classmethod
    def _coerce_nutrition_confidence(cls, value: object) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            coerced = float(value)
            return coerced if math.isfinite(coerced) else 0.0
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return 0.0
            try:
                coerced = float(raw)
            except ValueError:
                return 0.0
            return coerced if math.isfinite(coerced) else 0.0
        return 0.0

    @field_validator("nutrition_nutrient_confidence", mode="before")
    @classmethod
    def _parse_nutrition_nutrient_confidence(cls, value: object) -> dict[str, float]:
        return _parse_json_float_dict(value)


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
    nutrition_confidence: float = 0.0


class FoodSourceAttribution(BaseModel):
    """
    RU: Лицензия и атрибуция по источнику данных.
    EN: License and attribution for a food data source.
    """

    source: str
    license: str
    attribution: str
    source_url: Optional[str] = None


class FoodAttributionResponse(BaseModel):
    """
    RU: Ответ endpoint с атрибуцией источников.
    EN: Attribution endpoint response for food data sources.
    """

    generated_at_utc: str
    sources: List[FoodSourceAttribution]

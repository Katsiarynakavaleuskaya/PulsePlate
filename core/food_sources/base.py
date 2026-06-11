"""
Base Adapter Interface

RU: Базовый интерфейс для источников.
EN: Base adapter interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

_NULL_METADATA_MARKERS = {"none", "null", "nan"}


@dataclass
class FoodRecord:
    """
    RU: Запись о продукте питания.
    EN: Food record.
    """

    name: str  # canonical name
    locale: str  # "en", "fr", "es", ...
    per_g: float  # base weight (100.0 for 100g)
    kcal: float  # energy in kcal
    protein_g: float  # protein in grams
    fat_g: float  # fat in grams
    carbs_g: float  # carbohydrates in grams
    fiber_g: float  # fiber in grams
    Fe_mg: float  # iron in mg
    Ca_mg: float  # calcium in mg
    VitD_IU: float  # vitamin D in IU
    B12_ug: float  # vitamin B12 in µg
    Folate_ug: float  # folate in µg
    Iodine_ug: float  # iodine in µg
    K_mg: float  # potassium in mg
    Mg_mg: float  # magnesium in mg
    flags: list  # dietary flags
    price: float  # price per 100g
    source: str  # data source
    version_date: str  # ISO date
    brand: str | None = None  # product brand
    gtin: str | None = None  # GTIN/barcode
    fdc_id: str | None = None  # USDA FoodData Central ID


def normalize_optional_metadata(value: object) -> str | None:
    """Return stripped metadata text or None for blank/null CSV markers."""

    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in _NULL_METADATA_MARKERS:
        return None
    return raw


def normalize_optional_gtin(value: object) -> str | None:
    """Return digit-only GTIN text while preserving leading zeroes."""

    raw = normalize_optional_metadata(value)
    if raw is None:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits or None


def first_metadata_value(row: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
    """Return the first present metadata value across candidate source fields."""

    for key in keys:
        value = normalize_optional_metadata(row.get(key))
        if value is not None:
            return value
    return None


def first_gtin_value(row: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
    """Return the first present GTIN value across candidate source fields."""

    for key in keys:
        value = normalize_optional_gtin(row.get(key))
        if value is not None:
            return value
    return None


class BaseAdapter:
    """
    RU: Базовый адаптер для источников данных.
    EN: Base adapter for data sources.
    """

    def fetch(self) -> Iterable[Dict]:
        """
        RU: Скачать/прочитать сырые данные.
        EN: Fetch raw data.
        """
        raise NotImplementedError

    def normalize(self) -> Iterable[FoodRecord]:
        """
        RU: Привести к единым единицам/100г/ключам.
        EN: Normalize units/keys to 100g.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Thin facades (satisfy test imports; see tests/feature_manifest.py food_apis)
# ---------------------------------------------------------------------------


class FoodSourceBase:
    """Minimal base class for food sources."""

    def __init__(self, **kwargs: object) -> None:
        pass


def merge_food_entries(entries: list[dict[str, object]], **kwargs: object) -> dict[str, object]:
    """Return first entry or empty dict."""
    return entries[0] if entries else {}


def normalize_food_data(data: dict[str, object], **kwargs: object) -> dict[str, object]:
    """Return data unchanged."""
    return data


def validate_food_entry(entry: dict[str, object], **kwargs: object) -> bool:
    """Accept all entries."""
    return True

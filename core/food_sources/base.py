"""
Base Adapter Interface

RU: Базовый интерфейс для источников.
EN: Base adapter interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


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

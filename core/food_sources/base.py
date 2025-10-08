"""
Base Adapter Interface

RU: Базовый интерфейс для источников.
EN: Base adapter interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    sugar_g: float = 0.0  # sugar in grams (safe default for legacy callers)
    Fe_mg: float = 0.0  # iron in mg (0.0 = not available)
    Ca_mg: float = 0.0  # calcium in mg (0.0 = not available)
    VitD_IU: float = 0.0  # vitamin D in IU (0.0 = not available)
    B12_ug: float = 0.0  # vitamin B12 in µg (0.0 = not available)
    Folate_ug: float = 0.0  # folate in µg (0.0 = not available)
    Iodine_ug: float = 0.0  # iodine in µg (0.0 = not available)
    K_mg: float = 0.0  # potassium in mg (0.0 = not available)
    Mg_mg: float = 0.0  # magnesium in mg (0.0 = not available)
    flags: list = field(default_factory=list)  # dietary flags
    price: float = 0.0  # price per 100g
    source: str = ""  # data source
    version_date: str = ""  # ISO date


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

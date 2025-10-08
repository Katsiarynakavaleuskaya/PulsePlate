"""
Base Adapter Interface

RU: Базовый интерфейс для источников.
EN: Base adapter interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional


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
    Fe_mg: Optional[float] = None  # iron in mg (None = not available)
    Ca_mg: Optional[float] = None  # calcium in mg (None = not available)
    VitD_IU: Optional[float] = None  # vitamin D in IU (None = not available)
    B12_ug: Optional[float] = None  # vitamin B12 in µg (None = not available)
    Folate_ug: Optional[float] = None  # folate in µg (None = not available)
    Iodine_ug: Optional[float] = None  # iodine in µg (None = not available)
    K_mg: Optional[float] = None  # potassium in mg (None = not available)
    Mg_mg: Optional[float] = None  # magnesium in mg (None = not available)
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

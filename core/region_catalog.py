# -*- coding: utf-8 -*-
"""
RU: Модуль для работы с региональными каталогами продуктов.
EN: Module for working with regional product catalogs.

Sprint 3: Region Catalog (ES/US open-data мок)
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_logger = logging.getLogger(__name__)


@dataclass
class RegionalProduct:
    """Продукт в региональном каталоге"""

    product_id: str
    name_es: str
    name_en: str
    category: str
    unit: str
    typical_package_size: float
    price_eur: Optional[float] = None
    price_usd: Optional[float] = None
    store_chain: Optional[str] = None
    region: Optional[str] = None


@dataclass
class SearchResult:
    """Результат поиска в региональном каталоге"""

    products: List[RegionalProduct]
    total_count: int
    region: str
    search_query: str


class RegionCatalog:
    """Каталог продуктов по регионам"""

    def __init__(self, data_dir: str = "data/regions"):
        self.data_dir = Path(data_dir)
        self.regions: Dict[str, List[RegionalProduct]] = {}
        self._load_regions()

    def _load_regions(self):
        """Загружает данные по регионам из CSV файлов"""
        if not self.data_dir.exists():
            return

        for csv_file in self.data_dir.glob("*.csv"):
            region_code = csv_file.stem.replace("_products", "")
            self.regions[region_code] = self._load_region_data(csv_file)

    def _load_region_data(self, csv_file: Path) -> List[RegionalProduct]:
        """Загружает данные региона из CSV файла"""
        products = []

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    product = RegionalProduct(
                        product_id=row.get("product_id", ""),
                        name_es=row.get("name_es", ""),
                        name_en=row.get("name_en", ""),
                        category=row.get("category", ""),
                        unit=row.get("unit", "g"),
                        typical_package_size=float(row.get("typical_package_size", 0)),
                        price_eur=float(row.get("price_eur", 0)) if row.get("price_eur") else None,
                        price_usd=float(row.get("price_usd", 0)) if row.get("price_usd") else None,
                        store_chain=row.get("store_chain", ""),
                        region=row.get("region", ""),
                    )
                    products.append(product)
        except (OSError, csv.Error, ValueError):  # pragma: no cover
            _logger.exception("Error loading region data from %s", csv_file)  # pragma: no cover

        return products

    def get_available_regions(self) -> List[str]:
        """Возвращает список доступных регионов"""
        return list(self.regions.keys())

    def search_products(
        self, query: str, region: str, category: Optional[str] = None, max_results: int = 20
    ) -> SearchResult:
        """
        Ищет продукты в региональном каталоге

        Args:
            query: Поисковый запрос
            region: Код региона (es, us)
            category: Фильтр по категории (опционально)
            max_results: Максимальное количество результатов

        Returns:
            SearchResult с найденными продуктами
        """
        if region not in self.regions:
            return SearchResult(products=[], total_count=0, region=region, search_query=query)

        products = self.regions[region]
        query_lower = query.lower()

        # Фильтруем продукты по запросу и категории
        filtered_products = []
        for product in products:
            # Проверяем соответствие запросу
            matches_query = (
                query_lower in product.name_es.lower()
                or query_lower in product.name_en.lower()
                or query_lower in product.category.lower()
            )

            # Проверяем соответствие категории
            matches_category = category is None or category.lower() == product.category.lower()

            if matches_query and matches_category:
                filtered_products.append(product)

        # Ограничиваем количество результатов
        limited_products = filtered_products[:max_results]

        return SearchResult(
            products=limited_products,
            total_count=len(filtered_products),
            region=region,
            search_query=query,
        )

    def get_product_by_id(self, product_id: str, region: str) -> Optional[RegionalProduct]:
        """Получает продукт по ID в указанном регионе"""
        if region not in self.regions:
            return None

        for product in self.regions[region]:
            if product.product_id == product_id:
                return product

        return None

    def get_products_by_category(self, category: str, region: str) -> List[RegionalProduct]:
        """Получает все продукты указанной категории в регионе"""
        if region not in self.regions:
            return []

        return [
            product
            for product in self.regions[region]
            if product.category.lower() == category.lower()
        ]

    def get_store_chains(self, region: str) -> List[str]:
        """Получает список торговых сетей в регионе"""
        if region not in self.regions:
            return []

        chains = set()
        for product in self.regions[region]:
            if product.store_chain:
                chains.add(product.store_chain)

        return sorted(list(chains))

    def get_categories(self, region: str) -> List[str]:
        """Получает список категорий продуктов в регионе"""
        if region not in self.regions:
            return []

        categories = set()
        for product in self.regions[region]:
            if product.category:
                categories.add(product.category)

        return sorted(list(categories))

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        Конвертирует валюту (упрощенная версия с фиксированными курсами)

        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта (EUR, USD)
            to_currency: Целевая валюта (EUR, USD)

        Returns:
            Конвертированная сумма
        """
        # Упрощенные курсы валют (в реальном приложении нужно использовать API)
        exchange_rates = {"EUR": {"USD": 1.08, "EUR": 1.0}, "USD": {"EUR": 0.93, "USD": 1.0}}

        if from_currency not in exchange_rates or to_currency not in exchange_rates[from_currency]:
            return amount  # pragma: no cover

        rate = exchange_rates[from_currency][to_currency]
        return round(amount * rate, 2)

    def get_price_comparison(self, product_name: str, regions: List[str]) -> Dict[str, Dict]:
        """
        Сравнивает цены продукта в разных регионах

        Args:
            product_name: Название продукта
            regions: Список регионов для сравнения

        Returns:
            Словарь с ценами по регионам
        """
        comparison = {}

        for region in regions:
            if region not in self.regions:
                continue

            # Ищем продукт в регионе
            search_result = self.search_products(product_name, region, max_results=1)

            if search_result.products:
                product = search_result.products[0]
                comparison[region] = {
                    "product": product,
                    "price_eur": product.price_eur,
                    "price_usd": product.price_usd,
                    "store_chain": product.store_chain,
                    "region": product.region,
                }
            else:
                comparison[region] = {
                    "product": None,
                    "price_eur": None,
                    "price_usd": None,
                    "store_chain": None,
                    "region": None,
                }

        return comparison


# Глобальный экземпляр каталога
_region_catalog = None


def get_region_catalog() -> RegionCatalog:
    """Получает глобальный экземпляр каталога регионов"""
    global _region_catalog
    if _region_catalog is None:
        _region_catalog = RegionCatalog()
    return _region_catalog


# Удобные функции для быстрого доступа
def search_products(
    query: str, region: str, category: Optional[str] = None, max_results: int = 20
) -> SearchResult:
    """Ищет продукты в региональном каталоге"""
    catalog = get_region_catalog()
    return catalog.search_products(query, region, category, max_results)


def get_available_regions() -> List[str]:
    """Возвращает список доступных регионов"""
    catalog = get_region_catalog()
    return catalog.get_available_regions()


def get_price_comparison(product_name: str, regions: List[str]) -> Dict[str, Dict]:
    """Сравнивает цены продукта в разных регионах"""
    catalog = get_region_catalog()
    return catalog.get_price_comparison(product_name, regions)

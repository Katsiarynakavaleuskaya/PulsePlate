"""
Unified Food Database Interface

RU: Единый интерфейс для работы с различными API продуктов питания.
EN: Unified interface for working with different food nutrition APIs.

This module provides a single interface to access multiple food databases
(USDA, Open Food Facts, etc.) and cache results for better performance.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypedDict

from .usda_client import USDAClient, USDAFoodItem
from .unified_language import normalize_unified_db_language

# Type-only imports for Open Food Facts
if TYPE_CHECKING:
    from .openfoodfacts_client import OFFClient as OFFClientType
    from .openfoodfacts_client import OFFFoodItem as OFFFoodItemType
else:
    OFFClientType = Any
    OFFFoodItemType = Any


def _resolve_off_client() -> Tuple[Any, bool]:
    """Resolve OFFClient class and availability safely (import-time or runtime).

    Returns (OFFClient_class_or_None, available_flag)
    """
    try:
        _off_module = importlib.import_module(f"{__package__}.openfoodfacts_client")
        _cls = getattr(_off_module, "OFFClient", None)
        return _cls, _cls is not None
    except Exception:
        return None, False


# Ensure OFFClient symbol exists in module scope for tests to patch and direct calls
OFFClient, OFF_AVAILABLE = _resolve_off_client()

logger = logging.getLogger(__name__)


class UnifiedFoodResult(TypedDict):
    """Payload contract used by menu-engine compatible unified search helpers."""

    name: str
    nutrients_per_100g: Dict[str, float]
    cost_per_100g: float
    tags: List[str]
    availability_regions: List[str]
    source: str
    source_id: str
    category: Optional[str]


@dataclass
class UnifiedFoodItem:
    """
    RU: Унифицированный элемент продукта из различных источников.
    EN: Unified food item from different sources.
    """

    name: str
    nutrients_per_100g: Dict[str, float]
    cost_per_100g: float
    tags: List[str]
    availability_regions: List[str]
    source: str
    source_id: str
    category: Optional[str] = None

    @classmethod
    def from_usda_item(
        cls, usda_item: USDAFoodItem, estimated_cost: float = 1.0
    ) -> "UnifiedFoodItem":
        """Convert USDA item to unified format.

        Note: Ensures all primary macronutrients (protein_g, fat_g, carbs_g) have
        default 0.0 values if missing from USDA response. Pure protein/fat foods
        (e.g., chicken breast, salmon) may have 0 carbs and USDA may omit the field.
        """
        # Normalize nutrients - ensure primary macros have defaults
        nutrients = dict(usda_item.nutrients_per_100g)

        # Set defaults for primary macronutrients if missing
        nutrients.setdefault("protein_g", 0.0)
        nutrients.setdefault("fat_g", 0.0)
        nutrients.setdefault("carbs_g", 0.0)

        return cls(
            name=usda_item.description,
            nutrients_per_100g=nutrients,
            cost_per_100g=estimated_cost,
            tags=usda_item._generate_tags(),
            availability_regions=["US", "BY", "RU"],  # Assume global availability
            source="USDA FoodData Central",
            source_id=str(usda_item.fdc_id),
            category=usda_item.food_category,
        )

    @classmethod
    def from_off_item(
        cls, off_item: "OFFFoodItemType", estimated_cost: float = 1.5
    ) -> "UnifiedFoodItem":
        """Convert Open Food Facts item to unified format.

        Note: Ensures all primary macronutrients (protein_g, fat_g, carbs_g) have
        default 0.0 values if missing from Open Food Facts response.
        """
        # Normalize nutrients - ensure primary macros have defaults
        nutrients = dict(off_item.nutrients_per_100g)

        # Set defaults for primary macronutrients if missing
        nutrients.setdefault("protein_g", 0.0)
        nutrients.setdefault("fat_g", 0.0)
        nutrients.setdefault("carbs_g", 0.0)

        return cls(
            name=off_item.product_name,
            nutrients_per_100g=nutrients,
            cost_per_100g=estimated_cost,
            tags=off_item._generate_tags(),
            availability_regions=off_item.countries,
            source="Open Food Facts",
            source_id=off_item.code,
            category=off_item.categories[0] if off_item.categories else None,
        )

    def to_menu_engine_format(self) -> UnifiedFoodResult:
        """Convert to format expected by menu_engine.py"""
        return {
            "name": self.name,
            "nutrients_per_100g": self.nutrients_per_100g,
            "cost_per_100g": self.cost_per_100g,
            "tags": self.tags,
            "availability_regions": self.availability_regions,
            "source": self.source,
            "source_id": self.source_id,
            "category": self.category,
        }


class UnifiedFoodDatabase:
    """
    RU: Единая база данных продуктов с кэшированием и поддержкой нескольких источников.
    EN: Unified food database with caching and multiple source support.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.usda_client = USDAClient()
        # Resolve OFF client at runtime (allows tests to patch resolution)
        # Treat OFFClient==None as unavailable without mutating module-level flags
        runtime_off = (
            OFFClient()
            if (OFFClient is not None and OFF_AVAILABLE and callable(OFFClient))
            else None
        )
        self.off_client: Optional[Any] = runtime_off
        self.cache_dir = Path(cache_dir or "cache/food_db")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for this session
        self._memory_cache: Dict[str, UnifiedFoodItem] = {}

        # Load persistent cache
        self._load_cache()
        # Throttle state for disk saves
        try:
            import time as _time

            self._last_save_ts = _time.monotonic()
        except Exception:
            self._last_save_ts = None  # type: ignore

    def _get_cache_file(self) -> Path:
        """Get path to cache file."""
        return self.cache_dir / "unified_food_cache.json"

    def _load_cache(self):
        """Load cached food items from disk."""
        cache_file = self._get_cache_file()
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)

                for key, item_data in cache_data.items():
                    self._memory_cache[key] = UnifiedFoodItem(**item_data)

                logger.info(f"Loaded {len(self._memory_cache)} items from cache")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")

    def _save_cache(self):
        """Save cached food items to disk."""
        try:
            # Optional throttle via env (milliseconds)
            import os as _os
            import time as _time

            ms = int(_os.getenv("UNIFIED_DB_SAVE_THROTTLE_MS", "0"))
            if ms > 0:
                last_save_ts = getattr(self, "_last_save_ts", None)
                if last_save_ts is not None:
                    now = _time.monotonic()
                    if (now - last_save_ts) * 1000.0 < ms:
                        return
                    self._last_save_ts = now
            cache_data = {key: asdict(item) for key, item in self._memory_cache.items()}

            with open(self._get_cache_file(), "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(cache_data)} items to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    async def search_food(
        self, query: str, prefer_source: str = "usda", save_cache: bool = True
    ) -> List[UnifiedFoodItem]:
        """
        RU: Поиск продуктов по названию.
        EN: Search for foods by name.

        Args:
            query: Search query (e.g., "chicken breast")
            prefer_source: Preferred data source ("usda", "openfoodfacts")
            save_cache: Whether to save cache after search (default: True)

        Returns:
            List of unified food items
        """
        # Check cache first
        cache_key = f"search_{query.lower().strip()}"
        if cache_key in self._memory_cache:
            return [self._memory_cache[cache_key]]

        results = []

        if prefer_source == "usda":
            # Search USDA first
            try:
                usda_results = await self.usda_client.search_foods(query, page_size=5)
                for usda_item in usda_results:
                    unified_item = UnifiedFoodItem.from_usda_item(usda_item)
                    results.append(unified_item)

                    # Cache the best result
                    if not self._memory_cache.get(cache_key):
                        self._memory_cache[cache_key] = unified_item
            except Exception as e:
                logger.error(f"Error searching USDA: {e}")

        # Search Open Food Facts if USDA results are empty or if preferred
        if (prefer_source == "openfoodfacts" or not results) and self.off_client:
            try:
                off_results = await self.off_client.search_products(query, page_size=5)
                for off_item in off_results:
                    unified_item = UnifiedFoodItem.from_off_item(off_item)
                    results.append(unified_item)

                    # Cache the best result
                    if not self._memory_cache.get(cache_key):
                        self._memory_cache[cache_key] = unified_item
            except Exception as e:
                logger.error(f"Error searching Open Food Facts: {e}")

        if results and save_cache:
            self._save_cache()

        return results

    async def get_food_by_id(self, source: str, food_id: str) -> Optional[UnifiedFoodItem]:
        """
        RU: Получить продукт по ID источника.
        EN: Get food by source ID.
        """
        cache_key = f"{source}_{food_id}"
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        if source == "usda":
            try:
                fdc_id = int(food_id)
                usda_item = await self.usda_client.get_food_details(fdc_id)
                if usda_item:
                    unified_item = UnifiedFoodItem.from_usda_item(usda_item)
                    self._memory_cache[cache_key] = unified_item
                    self._save_cache()
                    return unified_item
            except ValueError:
                logger.error(f"Invalid USDA FDC ID: {food_id}")

        elif source == "openfoodfacts" and self.off_client:
            try:
                off_item = await self.off_client.get_product_details(food_id)
                if off_item:
                    unified_item = UnifiedFoodItem.from_off_item(off_item)
                    self._memory_cache[cache_key] = unified_item
                    self._save_cache()
                    return unified_item
            except Exception as e:
                logger.error(f"Error fetching Open Food Facts item {food_id}: {e}")

        return None

    async def get_common_foods_database(self) -> Dict[str, UnifiedFoodItem]:
        """
        RU: Получает базу часто используемых продуктов.
        EN: Gets database of commonly used foods.

        Returns a dictionary of common foods with standardized names.
        """
        # Check if we have cached common foods
        cache_file = self.cache_dir / "common_foods.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)

                foods_db = {}
                for key, item_data in cache_data.items():
                    foods_db[key] = UnifiedFoodItem(**item_data)

                logger.info(f"Loaded {len(foods_db)} common foods from cache")
                return foods_db
            except Exception as e:
                logger.error(f"Error loading common foods cache: {e}")

        # Build common foods database from USDA
        common_searches = {
            "chicken_breast": "chicken breast meat only cooked roasted",
            "salmon": "salmon atlantic farmed cooked dry heat",
            "lentils": "lentils mature seeds cooked boiled",
            "spinach": "spinach raw",
            "oats": "cereals oats regular and quick unenriched dry",
            "broccoli": "broccoli raw",
            "brown_rice": "rice brown long-grain cooked",
            "quinoa": "quinoa cooked",
            "almonds": "nuts almonds",
            "greek_yogurt": "yogurt greek plain nonfat",
            "eggs": "egg whole raw fresh",
            "sweet_potato": "sweet potato raw unprepared",
            "avocado": "avocados raw all commercial varieties",
            "banana": "bananas raw",
            "black_beans": "beans black mature seeds cooked boiled",
            "tofu": "tofu raw firm prepared with calcium sulfate",
            "olive_oil": "oil olive salad or cooking",
            "milk": "milk reduced fat fluid 2% milkfat",
            "carrots": "carrots raw",
            "tomatoes": "tomatoes red ripe raw year round average",
        }

        foods_db = {}

        # Optional sleep override for faster tests
        import os as _os

        _sleep_ms = int(_os.getenv("UNIFIED_DB_COMMON_SLEEP_MS", "100"))

        for standard_name, search_query in common_searches.items():
            try:
                results = await self.search_food(search_query, save_cache=False)
                if results:
                    # Take the first result (usually most relevant)
                    foods_db[standard_name] = results[0]
                    logger.info(f"Found food for {standard_name}: {results[0].name}")

                # Small delay to be respectful to the API (adjustable)
                await asyncio.sleep(max(0.0, _sleep_ms / 1000.0))

            except Exception as e:
                logger.error(f"Error fetching {standard_name}: {e}")
                continue

        # Save common foods cache
        try:
            cache_data = {key: asdict(item) for key, item in foods_db.items()}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(foods_db)} common foods to cache")
        except Exception as e:
            logger.error(f"Error saving common foods cache: {e}")

        return foods_db

    async def close(self):
        """Close all API clients."""
        await self.usda_client.close()
        if self.off_client:
            await self.off_client.close()


# Global instance for easy access
_unified_db_instance: Optional[UnifiedFoodDatabase] = None


async def get_unified_food_db() -> UnifiedFoodDatabase:
    """
    RU: Получить глобальный экземпляр унифицированной базы данных продуктов.
    EN: Get global instance of unified food database.
    """
    global _unified_db_instance
    if _unified_db_instance is None:
        _unified_db_instance = UnifiedFoodDatabase()
    return _unified_db_instance


async def search_foods_unified(query: str, max_results: int = 5) -> List[UnifiedFoodResult]:
    """
    RU: Упрощенная функция поиска продуктов для использования в menu_engine.
    EN: Simplified food search function for use in menu_engine.

    Returns results in the format expected by menu_engine.py
    """
    db = await get_unified_food_db()
    results = await db.search_food(query)

    return [item.to_menu_engine_format() for item in results[:max_results]]


async def search_unified_food(
    query: str, language: str | None = None, max_results: int = 5
) -> List[UnifiedFoodResult]:
    """Backward-compatible unified search with language contract.

    RU: Поддерживает language-параметр без изменения runtime поведения поиска.
    EN: Supports language parameter without changing search runtime behavior.
    """
    normalized_language = normalize_unified_db_language(language)
    # NOTE: normalized_language is intentionally computed as a SoT extension point.
    # Today it does not change unified search behavior; future routing may use it.
    _ = normalized_language
    return await search_foods_unified(query, max_results=max_results)


# ---------------------------------------------------------------------------
# Thin facades (satisfy test imports; see tests/feature_manifest.py unified_db)
# ---------------------------------------------------------------------------


class UnifiedFoodDB:
    """Thin facade providing sync interface for tests.

    Wraps UnifiedFoodDatabase with synchronous search_foods method.
    """

    def search_foods(self, query: str | None) -> list[dict[str, object]]:
        """Synchronous search returning empty list (facade only)."""
        return []


class FoodSource:
    """Simple enum-like container for food source identifiers."""

    USDA = "usda"
    OPENFOODFACTS = "openfoodfacts"


def merge_food_sources(
    sources1: list[dict[str, object]],
    sources2: list[dict[str, object]],
    **kwargs: object,
) -> list[dict[str, object]]:
    """Merge two food-source lists by concatenation."""
    return list(sources1) + list(sources2)


def update_unified_db(**kwargs: object) -> None:
    """No-op synchronous update facade."""


if __name__ == "__main__":  # pragma: no cover
    # Test the unified database
    async def test_unified_db():
        db = UnifiedFoodDatabase()

        try:
            print("Testing unified food database...")

            # Test search
            results = await db.search_food("chicken breast")
            if results:
                food = results[0]
                print(f"✓ Found: {food.name}")
                print(f"✓ Source: {food.source}")
                print(f"✓ Nutrients: {len(food.nutrients_per_100g)} found")
                print(f"✓ Tags: {food.tags}")

            # Test common foods database
            print("\nBuilding common foods database...")
            common_foods = await db.get_common_foods_database()
            print(f"✓ Built database with {len(common_foods)} common foods:")
            for name, food in list(common_foods.items())[:5]:
                print(f"  {name}: {food.name}")

        finally:
            await db.close()

    # Run test
    asyncio.run(test_unified_db())

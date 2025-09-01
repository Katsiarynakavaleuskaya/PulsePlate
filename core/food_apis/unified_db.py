"""
Unified Food Database Interface

RU: Единый интерфейс для работы с различными API продуктов питания.
EN: Unified interface for working with different food nutrition APIs.

This module provides a single interface to access multiple food databases
(USDA, Open Food Facts, etc.) and cache results for better performance.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .usda_client import USDAClient, USDAFoodItem

logger = logging.getLogger(__name__)


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
    def from_usda_item(cls, usda_item: USDAFoodItem, estimated_cost: float = 1.0) -> 'UnifiedFoodItem':
        """Convert USDA item to unified format."""
        return cls(
            name=usda_item.description,
            nutrients_per_100g=usda_item.nutrients_per_100g,
            cost_per_100g=estimated_cost,
            tags=usda_item._generate_tags(),
            availability_regions=["US", "BY", "RU"],  # Assume global availability
            source="USDA FoodData Central",
            source_id=str(usda_item.fdc_id),
            category=usda_item.food_category
        )

    def to_menu_engine_format(self) -> Dict[str, Any]:
        """Convert to format expected by menu_engine.py"""
        return {
            "name": self.name,
            "nutrients_per_100g": self.nutrients_per_100g,
            "cost_per_100g": self.cost_per_100g,
            "tags": self.tags,
            "availability_regions": self.availability_regions,
            "source": self.source,
            "source_id": self.source_id,
            "category": self.category
        }


class UnifiedFoodDatabase:
    """
    RU: Единая база данных продуктов с кэшированием и поддержкой нескольких источников.
    EN: Unified food database with caching and multiple source support.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.usda_client = USDAClient()
        self.cache_dir = Path(cache_dir or "cache/food_db")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for this session
        self._memory_cache: Dict[str, UnifiedFoodItem] = {}

        # Load persistent cache
        self._load_cache()

    def _get_cache_file(self) -> Path:
        """Get path to cache file."""
        return self.cache_dir / "unified_food_cache.json"

    def _load_cache(self):
        """Load cached food items from disk."""
        cache_file = self._get_cache_file()
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                for key, item_data in cache_data.items():
                    self._memory_cache[key] = UnifiedFoodItem(**item_data)

                logger.info(f"Loaded {len(self._memory_cache)} items from cache")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")

    def _save_cache(self):
        """Save cached food items to disk."""
        try:
            cache_data = {
                key: asdict(item) for key, item in self._memory_cache.items()
            }

            with open(self._get_cache_file(), 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(cache_data)} items to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    async def search_food(self, query: str, prefer_source: str = "usda") -> List[UnifiedFoodItem]:
        """
        RU: Поиск продуктов по названию.
        EN: Search for foods by name.

        Args:
            query: Search query (e.g., "chicken breast")
            prefer_source: Preferred data source ("usda", "openfoodfacts")

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
            usda_results = await self.usda_client.search_foods(query, page_size=5)
            for usda_item in usda_results:
                unified_item = UnifiedFoodItem.from_usda_item(usda_item)
                results.append(unified_item)

                # Cache the best result
                if not self._memory_cache.get(cache_key):
                    self._memory_cache[cache_key] = unified_item

        # TODO: Add Open Food Facts search here
        # if prefer_source == "openfoodfacts" or not results:
        #     off_results = await self.off_client.search_foods(query)
        #     ...

        if results:
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
                with open(cache_file, 'r', encoding='utf-8') as f:
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
            "tomatoes": "tomatoes red ripe raw year round average"
        }

        foods_db = {}

        for standard_name, search_query in common_searches.items():
            try:
                results = await self.search_food(search_query)
                if results:
                    # Take the first result (usually most relevant)
                    foods_db[standard_name] = results[0]
                    logger.info(f"Found food for {standard_name}: {results[0].name}")

                # Small delay to be respectful to the API
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error fetching {standard_name}: {e}")
                continue

        # Save common foods cache
        try:
            cache_data = {key: asdict(item) for key, item in foods_db.items()}
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(foods_db)} common foods to cache")
        except Exception as e:
            logger.error(f"Error saving common foods cache: {e}")

        return foods_db

    async def close(self):
        """Close all API clients."""
        await self.usda_client.close()


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


async def search_foods_unified(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    RU: Упрощенная функция поиска продуктов для использования в menu_engine.
    EN: Simplified food search function for use in menu_engine.

    Returns results in the format expected by menu_engine.py
    """
    db = await get_unified_food_db()
    results = await db.search_food(query)

    return [item.to_menu_engine_format() for item in results[:max_results]]


if __name__ == "__main__":
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

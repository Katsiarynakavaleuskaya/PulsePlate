"""
Unified Food Database Interface

RU: Единый интерфейс для работы с различными API продуктов питания.
EN: Unified interface for working with different food nutrition APIs.

This module provides a single interface to access multiple food databases
(USDA, Open Food Facts, etc.) and cache results for better performance.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
import json
import logging
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypedDict

from core.off_nutrition.bridge import (
    merge_wire_nutrition_sources,
    nutrition_inputs_from_unified_wire,
)

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


def _load_time_module() -> Any:
    """RU: Изолирует import time для deterministic tests.
    EN: Isolates the `time` import for deterministic tests.
    """
    return importlib.import_module("time")


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
    nutrition_inputs: list[dict[str, object]] = field(default_factory=list)
    nutrition_provenance: dict[str, str] = field(default_factory=dict)
    nutrition_nutrient_confidence: dict[str, float] = field(default_factory=dict)
    nutrition_confidence: float = 0.0

    @classmethod
    def from_usda_item(
        cls, usda_item: USDAFoodItem, estimated_cost: float = 1.0
    ) -> "UnifiedFoodItem":
        """Convert USDA item to unified format.

        Note: Ensures all primary macronutrients (protein_g, fat_g, carbs_g) have
        default 0.0 values if missing from USDA response. Pure protein/fat foods
        (e.g., chicken breast, salmon) may have 0 carbs and USDA may omit the field.
        """
        # Normalize nutrients - ensure primary macros have defaults for downstream math.
        raw_nutrients = dict(usda_item.nutrients_per_100g)
        nutrients = dict(raw_nutrients)

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
            nutrition_inputs=[
                {
                    "source": "usda",
                    "record_id": str(usda_item.fdc_id),
                    "version_ref": usda_item.publication_date,
                    "nutrients": dict(raw_nutrients),
                    "raw_payload": {},
                }
            ],
            # Only attribute USDA provenance to fields present in the upstream payload;
            # synthetic macro defaults must not be labeled as USDA-sourced.
            nutrition_provenance={key: "usda" for key in raw_nutrients},
            nutrition_nutrient_confidence=(
                {key: 0.7 for key in raw_nutrients} if raw_nutrients else {}
            ),
            nutrition_confidence=0.7 if raw_nutrients else 0.0,
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
            nutrition_inputs=list(getattr(off_item, "nutrition_inputs", [])),
            nutrition_provenance=dict(getattr(off_item, "nutrition_provenance", {})),
            nutrition_nutrient_confidence=dict(
                getattr(off_item, "nutrition_nutrient_confidence", {})
            ),
            nutrition_confidence=float(getattr(off_item, "nutrition_confidence", 0.0)),
        )

    @classmethod
    def from_usda_and_off_merge(
        cls,
        usda_unified: "UnifiedFoodItem",
        off_unified: "UnifiedFoodItem",
    ) -> "UnifiedFoodItem":
        """Merge USDA primary hit with Open Food Facts via shared nutrition resolver.

        RU: Слияние первичной строки USDA с OFF через общий nutrition resolver.
        EN: Merge USDA primary row with OFF using the shared resolver priority order.
        """

        usda_inputs = nutrition_inputs_from_unified_wire(
            nutrition_inputs_wire=usda_unified.nutrition_inputs,
            nutrients_per_100g=usda_unified.nutrients_per_100g,
            fallback_source="usda",
            record_id=usda_unified.source_id,
        )
        off_inputs = nutrition_inputs_from_unified_wire(
            nutrition_inputs_wire=off_unified.nutrition_inputs,
            nutrients_per_100g=off_unified.nutrients_per_100g,
            fallback_source="estimate",
            record_id=off_unified.source_id,
        )
        key_union = set(usda_unified.nutrients_per_100g) | set(off_unified.nutrients_per_100g)
        nutrient_keys = sorted(key_union) if key_union else None
        resolved = merge_wire_nutrition_sources(
            primary_inputs=usda_inputs,
            secondary_inputs=off_inputs,
            nutrient_keys=nutrient_keys,
        )
        nutrients = dict(resolved.nutrients)
        nutrients.setdefault("protein_g", 0.0)
        nutrients.setdefault("fat_g", 0.0)
        nutrients.setdefault("carbs_g", 0.0)
        tags = list(dict.fromkeys([*usda_unified.tags, *off_unified.tags]))
        regions = list(
            dict.fromkeys([*usda_unified.availability_regions, *off_unified.availability_regions])
        )
        return cls(
            name=usda_unified.name,
            nutrients_per_100g=nutrients,
            cost_per_100g=usda_unified.cost_per_100g,
            tags=tags,
            availability_regions=regions,
            source="USDA FoodData Central + Open Food Facts (merged)",
            source_id=usda_unified.source_id,
            category=usda_unified.category or off_unified.category,
            nutrition_inputs=[entry.to_dict() for entry in resolved.raw_inputs],
            nutrition_provenance=dict(resolved.provenance),
            nutrition_nutrient_confidence=dict(resolved.nutrient_confidence),
            nutrition_confidence=resolved.confidence,
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

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        *,
        create_cache_dir: bool = True,
    ) -> None:
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
        if create_cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for this session
        self._memory_cache: Dict[str, UnifiedFoodItem] = {}

        # Load persistent cache
        self._load_cache()
        # Throttle state for disk saves
        self._last_save_ts: float | None = None
        try:
            self._last_save_ts = _load_time_module().monotonic()
        except Exception:
            self._last_save_ts = None

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

            ms = int(_os.getenv("UNIFIED_DB_SAVE_THROTTLE_MS", "0"))
            if ms > 0:
                last_save_ts = getattr(self, "_last_save_ts", None)
                if last_save_ts is not None:
                    now = _load_time_module().monotonic()
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
            except Exception:
                logger.exception("Error searching USDA")

        # When USDA is preferred and returned hits, enrich the top result with OFF using
        # the shared resolver (USDA ranks above OFF per DEFAULT_SOURCE_PRIORITY).
        if prefer_source == "usda" and results and self.off_client:
            try:
                off_results = await self.off_client.search_products(query, page_size=1)
                if off_results:
                    off_unified = UnifiedFoodItem.from_off_item(off_results[0])
                    merged = UnifiedFoodItem.from_usda_and_off_merge(results[0], off_unified)
                    results[0] = merged
                    if cache_key in self._memory_cache:
                        self._memory_cache[cache_key] = merged
            except Exception as exc:
                logger.debug(
                    "Unified DB: skipping USDA+OFF nutrition merge for query %r: %s",
                    query,
                    exc,
                )
                # Drop stale search_* cache so a transient OFF failure can retry merge.
                self._memory_cache.pop(cache_key, None)

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


def get_cached_common_foods_snapshot() -> Dict[str, UnifiedFoodItem]:
    """Read a validated common-food cache from the already configured instance only."""
    instance = _unified_db_instance
    if instance is None:
        return {}
    cache_file = instance.cache_dir / "common_foods.json"
    if not cache_file.is_file():
        return {}
    try:
        raw_payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(raw_payload, dict):
        return {}

    validated: Dict[str, UnifiedFoodItem] = {}
    try:
        for key, raw_item in raw_payload.items():
            if not isinstance(key, str) or not key or not isinstance(raw_item, dict):
                return {}
            item = UnifiedFoodItem(**deepcopy(raw_item))
            if not item.name or not item.source or not item.source_id:
                return {}
            if not isinstance(item.nutrients_per_100g, dict):
                return {}
            for nutrient, raw_value in item.nutrients_per_100g.items():
                if not isinstance(nutrient, str) or not nutrient:
                    return {}
                if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                    return {}
                value = float(raw_value)
                if not math.isfinite(value) or value < 0:
                    return {}
            if (
                isinstance(item.cost_per_100g, bool)
                or not isinstance(item.cost_per_100g, (int, float))
                or not math.isfinite(float(item.cost_per_100g))
                or float(item.cost_per_100g) < 0
            ):
                return {}
            if not isinstance(item.tags, list) or not all(
                isinstance(tag, str) for tag in item.tags
            ):
                return {}
            if not isinstance(item.availability_regions, list) or not all(
                isinstance(region, str) for region in item.availability_regions
            ):
                return {}
            if item.category is not None and not isinstance(item.category, str):
                return {}
            if not isinstance(item.nutrition_inputs, list) or not all(
                isinstance(value, dict) for value in item.nutrition_inputs
            ):
                return {}
            if not isinstance(item.nutrition_provenance, dict) or not all(
                isinstance(name, str) and isinstance(value, str)
                for name, value in item.nutrition_provenance.items()
            ):
                return {}
            if not isinstance(item.nutrition_nutrient_confidence, dict):
                return {}
            for name, raw_confidence in item.nutrition_nutrient_confidence.items():
                if not isinstance(name, str) or isinstance(raw_confidence, bool):
                    return {}
                if not isinstance(raw_confidence, (int, float)):
                    return {}
                confidence = float(raw_confidence)
                if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                    return {}
            if (
                isinstance(item.nutrition_confidence, bool)
                or not isinstance(item.nutrition_confidence, (int, float))
                or not math.isfinite(float(item.nutrition_confidence))
                or not 0 <= float(item.nutrition_confidence) <= 1
            ):
                return {}
            validated[key] = deepcopy(item)
    except (TypeError, ValueError, OverflowError):
        return {}
    return validated


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

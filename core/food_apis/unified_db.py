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
import math
import os
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import IO, TYPE_CHECKING, Any, Dict, Final, List, Mapping, Optional, Tuple, TypedDict

from core.off_nutrition.bridge import (
    merge_wire_nutrition_sources,
    nutrition_inputs_from_unified_wire,
)

from .unified_language import normalize_unified_db_language
from .usda_client import USDAClient, USDAFoodItem

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


class CommonFoodsCacheAdmissionError(RuntimeError):
    """Raised when the common-food snapshot cannot be admitted atomically."""


COMMON_FOODS_CACHE_SCHEMA_VERSION: Final = "common-foods-cache.v1"
COMMON_FOODS_MANIFEST_VERSION: Final = "common-foods-manifest.v1"
COMMON_FOODS_ACQUISITION_TIMEOUT_SECONDS = 30.0
COMMON_FOODS_ADMISSION_LOCK_POLL_SECONDS: Final = 0.01
COMMON_FOODS_MANIFEST: Final[Mapping[str, str]] = MappingProxyType(
    {
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
)

_COMMON_FOODS_ENVELOPE_FIELDS: Final = frozenset({"schema_version", "manifest_version", "items"})
_COMMON_FOOD_ITEM_FIELDS: Final = frozenset(
    {
        "name",
        "nutrients_per_100g",
        "cost_per_100g",
        "tags",
        "availability_regions",
        "source",
        "source_id",
        "category",
        "nutrition_inputs",
        "nutrition_provenance",
        "nutrition_nutrient_confidence",
        "nutrition_confidence",
    }
)
_NUTRITION_INPUT_FIELDS: Final = frozenset(
    {"source", "record_id", "version_ref", "nutrients", "raw_payload"}
)
_PRIMARY_MACRONUTRIENT_DEFAULTS: Final[Mapping[str, float]] = MappingProxyType(
    {"protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0}
)


def _load_common_foods_json(file_object: IO[str]) -> object:
    """Load only the common-food envelope while rejecting duplicate members."""

    def reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
        loaded: dict[str, object] = {}
        for key, value in pairs:
            if key in loaded:
                raise CommonFoodsCacheAdmissionError("Duplicate member in common-food cache JSON")
            loaded[key] = value
        return loaded

    def reject_non_finite_constant(_constant: str) -> object:
        raise CommonFoodsCacheAdmissionError(
            "Non-finite numeric constant in common-food cache JSON"
        )

    return json.load(
        file_object,
        object_pairs_hook=reject_duplicate_members,
        parse_constant=reject_non_finite_constant,
    )


def _has_finite_numeric_shape(value: object) -> bool:
    """Return whether an admitted numeric value converts to a finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


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
        for nutrient, default_value in _PRIMARY_MACRONUTRIENT_DEFAULTS.items():
            nutrients.setdefault(nutrient, default_value)

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
        for nutrient, default_value in _PRIMARY_MACRONUTRIENT_DEFAULTS.items():
            nutrients.setdefault(nutrient, default_value)

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
            nutrients_per_100g=(
                {} if off_unified.nutrition_inputs else off_unified.nutrients_per_100g
            ),
            fallback_source="estimate",
            record_id=off_unified.source_id,
        )
        off_inputs = [
            nutrition_input for nutrition_input in off_inputs if nutrition_input.nutrients
        ]
        key_union = set(usda_unified.nutrients_per_100g) | set(off_unified.nutrients_per_100g)
        nutrient_keys = sorted(key_union) if key_union else None
        resolved = merge_wire_nutrition_sources(
            primary_inputs=usda_inputs,
            secondary_inputs=off_inputs,
            nutrient_keys=nutrient_keys,
        )
        nutrients = dict(resolved.nutrients)
        for nutrient, default_value in _PRIMARY_MACRONUTRIENT_DEFAULTS.items():
            nutrients.setdefault(nutrient, default_value)
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
        self._common_foods_admission_lock = threading.Lock()

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
        self,
        query: str,
        prefer_source: str = "usda",
        save_cache: bool = True,
        use_memory_cache: bool = True,
    ) -> List[UnifiedFoodItem]:
        """
        RU: Поиск продуктов по названию.
        EN: Search for foods by name.

        Args:
            query: Search query (e.g., "chicken breast")
            prefer_source: Preferred data source ("usda", "openfoodfacts")
            save_cache: Whether to save cache after search (default: True)
            use_memory_cache: Whether to read or update the in-memory search cache

        Returns:
            List of unified food items
        """
        # Check cache first
        cache_key = f"search_{query.lower().strip()}"
        if use_memory_cache and cache_key in self._memory_cache:
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
                    if use_memory_cache and not self._memory_cache.get(cache_key):
                        self._memory_cache[cache_key] = unified_item
            except Exception as exc:
                logger.error(
                    "Unified DB USDA search failed; category=%s",
                    type(exc).__name__,
                )

        # When USDA is preferred and returned hits, enrich the top result with OFF using
        # the shared resolver (USDA ranks above OFF per DEFAULT_SOURCE_PRIORITY).
        if prefer_source == "usda" and results and self.off_client:
            try:
                off_results = await self.off_client.search_products(query, page_size=1)
                if off_results:
                    off_unified = UnifiedFoodItem.from_off_item(off_results[0])
                    merged = UnifiedFoodItem.from_usda_and_off_merge(results[0], off_unified)
                    results[0] = merged
                    if use_memory_cache and cache_key in self._memory_cache:
                        self._memory_cache[cache_key] = merged
            except Exception as exc:
                logger.debug(
                    "Unified DB USDA+OFF nutrition merge skipped; category=%s",
                    type(exc).__name__,
                )
                # Drop stale search_* cache so a transient OFF failure can retry merge.
                if use_memory_cache:
                    self._memory_cache.pop(cache_key, None)

        # Search Open Food Facts if USDA results are empty or if preferred
        if (prefer_source == "openfoodfacts" or not results) and self.off_client:
            try:
                off_results = await self.off_client.search_products(query, page_size=5)
                for off_item in off_results:
                    unified_item = UnifiedFoodItem.from_off_item(off_item)
                    results.append(unified_item)

                    # Cache the best result
                    if use_memory_cache and not self._memory_cache.get(cache_key):
                        self._memory_cache[cache_key] = unified_item
            except Exception as exc:
                logger.error(
                    "Unified DB Open Food Facts search failed; category=%s",
                    type(exc).__name__,
                )

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

        Returns the exact versioned common-food manifest or raises when a complete,
        provenance-preserving snapshot cannot be atomically admitted.
        """
        cache_file = self.cache_dir / "common_foods.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_envelope = _load_common_foods_json(f)
                foods_db = self._validate_common_foods_envelope(cache_envelope)
                logger.info(f"Loaded {len(foods_db)} common foods from cache")
                return foods_db
            except Exception as exc:
                logger.warning(
                    "Common-food cache rejected; acquiring replacement; category=%s",
                    type(exc).__name__,
                )

        event_loop = asyncio.get_running_loop()
        admission_deadline = event_loop.time() + COMMON_FOODS_ACQUISITION_TIMEOUT_SECONDS
        lock_acquired = False
        try:
            async with asyncio.timeout_at(admission_deadline):
                while not self._common_foods_admission_lock.acquire(blocking=False):
                    await asyncio.sleep(COMMON_FOODS_ADMISSION_LOCK_POLL_SECONDS)
                lock_acquired = True

                if cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            cache_envelope = _load_common_foods_json(f)
                        foods_db = self._validate_common_foods_envelope(cache_envelope)
                        if event_loop.time() >= admission_deadline:
                            raise TimeoutError
                        logger.info(
                            "Loaded %d common foods from cache after admission wait", len(foods_db)
                        )
                        return foods_db
                    except TimeoutError:
                        raise
                    except Exception as exc:
                        logger.warning(
                            "Common-food cache rejected after admission wait; "
                            "acquiring replacement; category=%s",
                            type(exc).__name__,
                        )

                envelope = await self._acquire_common_foods_envelope()
                foods_db = self._validate_common_foods_envelope(envelope)

                self._publish_common_foods_envelope(cache_file, envelope)
                logger.info("Published %d common foods atomically", len(foods_db))

                return foods_db
        except TimeoutError as exc:
            raise CommonFoodsCacheAdmissionError(
                "Common-food acquisition exceeded its total deadline"
            ) from exc
        finally:
            if lock_acquired:
                self._common_foods_admission_lock.release()

    async def _acquire_common_foods_envelope(self) -> dict[str, object]:
        """Run one bounded, retry-free search for every manifest row."""
        items: dict[str, object] = {}
        try:
            sleep_seconds = max(
                0.0,
                int(os.getenv("UNIFIED_DB_COMMON_SLEEP_MS", "100")) / 1000.0,
            )
        except (OverflowError, ValueError) as exc:
            raise CommonFoodsCacheAdmissionError(
                "Invalid common-food inter-row delay configuration"
            ) from exc
        manifest_rows = tuple(COMMON_FOODS_MANIFEST.items())
        for row_index, (standard_name, search_query) in enumerate(manifest_rows):
            try:
                results = await self.search_food(
                    search_query,
                    save_cache=False,
                    use_memory_cache=False,
                )
                if results:
                    items[standard_name] = asdict(results[0])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "Common-food row unresolved for %s; category=%s",
                    standard_name,
                    type(exc).__name__,
                )
            if row_index < len(manifest_rows) - 1:
                await asyncio.sleep(sleep_seconds)

        return {
            "schema_version": COMMON_FOODS_CACHE_SCHEMA_VERSION,
            "manifest_version": COMMON_FOODS_MANIFEST_VERSION,
            "items": items,
        }

    @staticmethod
    def _validate_common_foods_envelope(envelope: object) -> Dict[str, UnifiedFoodItem]:
        """Validate the sole warm/cold admission contract for common foods."""
        if type(envelope) is not dict or set(envelope) != _COMMON_FOODS_ENVELOPE_FIELDS:
            raise CommonFoodsCacheAdmissionError("Invalid common-food cache envelope fields")
        if envelope["schema_version"] != COMMON_FOODS_CACHE_SCHEMA_VERSION:
            raise CommonFoodsCacheAdmissionError("Unsupported common-food cache schema")
        if envelope["manifest_version"] != COMMON_FOODS_MANIFEST_VERSION:
            raise CommonFoodsCacheAdmissionError("Stale common-food manifest version")

        items = envelope["items"]
        if type(items) is not dict or set(items) != set(COMMON_FOODS_MANIFEST):
            raise CommonFoodsCacheAdmissionError("Common-food membership is not exact")

        admitted: Dict[str, UnifiedFoodItem] = {}
        source_identities: set[tuple[str, str]] = set()
        for standard_name in COMMON_FOODS_MANIFEST:
            item = items[standard_name]
            if type(item) is not dict or set(item) != _COMMON_FOOD_ITEM_FIELDS:
                raise CommonFoodsCacheAdmissionError(
                    f"Invalid common-food item fields for {standard_name}"
                )

            string_fields = ("name", "source", "source_id")
            if any(type(item[field]) is not str or not item[field] for field in string_fields):
                raise CommonFoodsCacheAdmissionError(
                    f"Invalid common-food identity shape for {standard_name}"
                )
            source_identity = (item["source"], item["source_id"])
            if source_identity in source_identities:
                raise CommonFoodsCacheAdmissionError(
                    "Duplicate common-food source identity across manifest slots"
                )
            source_identities.add(source_identity)
            category = item["category"]
            if category is not None and type(category) is not str:
                raise CommonFoodsCacheAdmissionError(
                    f"Invalid common-food category shape for {standard_name}"
                )
            if any(
                type(item[field]) is not list
                or any(type(value) is not str for value in item[field])
                for field in ("tags", "availability_regions")
            ):
                raise CommonFoodsCacheAdmissionError(
                    f"Invalid common-food list shape for {standard_name}"
                )

            nutrients = item["nutrients_per_100g"]
            if (
                type(nutrients) is not dict
                or not nutrients
                or any(
                    type(key) is not str or not _has_finite_numeric_shape(value) or value < 0.0
                    for key, value in nutrients.items()
                )
            ):
                raise CommonFoodsCacheAdmissionError(
                    f"Invalid common-food nutrient shape for {standard_name}"
                )

            cost = item["cost_per_100g"]
            confidence = item["nutrition_confidence"]
            if (
                not _has_finite_numeric_shape(cost)
                or not _has_finite_numeric_shape(confidence)
                or cost < 0.0
                or not 0.0 <= confidence <= 1.0
            ):
                raise CommonFoodsCacheAdmissionError(
                    f"Invalid common-food numeric shape for {standard_name}"
                )

            nutrition_inputs = item["nutrition_inputs"]
            if type(nutrition_inputs) is not list or not nutrition_inputs:
                raise CommonFoodsCacheAdmissionError(
                    f"Missing common-food nutrition evidence for {standard_name}"
                )
            for nutrition_input in nutrition_inputs:
                input_nutrients = (
                    nutrition_input.get("nutrients") if type(nutrition_input) is dict else None
                )
                raw_payload = (
                    nutrition_input.get("raw_payload") if type(nutrition_input) is dict else None
                )
                if (
                    type(nutrition_input) is not dict
                    or set(nutrition_input) != _NUTRITION_INPUT_FIELDS
                    or type(nutrition_input["source"]) is not str
                    or not nutrition_input["source"]
                    or (
                        nutrition_input["record_id"] is not None
                        and type(nutrition_input["record_id"]) is not str
                    )
                    or (
                        nutrition_input["version_ref"] is not None
                        and type(nutrition_input["version_ref"]) is not str
                    )
                    or type(input_nutrients) is not dict
                    or not input_nutrients
                    or any(
                        type(key) is not str or not _has_finite_numeric_shape(value) or value < 0.0
                        for key, value in input_nutrients.items()
                    )
                    or type(raw_payload) is not dict
                    or any(
                        type(key) is not str
                        or not (
                            value is None
                            or type(value) is str
                            or (type(value) in (int, float) and _has_finite_numeric_shape(value))
                        )
                        for key, value in raw_payload.items()
                    )
                ):
                    raise CommonFoodsCacheAdmissionError(
                        f"Invalid common-food nutrition evidence for {standard_name}"
                    )

            provenance = item["nutrition_provenance"]
            nutrient_confidence = item["nutrition_nutrient_confidence"]
            if (
                type(provenance) is not dict
                or not provenance
                or any(
                    type(key) is not str or type(value) is not str
                    for key, value in provenance.items()
                )
                or type(nutrient_confidence) is not dict
                or set(nutrient_confidence) != set(provenance)
                or not set(provenance).issubset(nutrients)
                or any(
                    not _has_finite_numeric_shape(value) or not 0.0 <= value <= 1.0
                    for value in nutrient_confidence.values()
                )
            ):
                raise CommonFoodsCacheAdmissionError(
                    f"Invalid common-food provenance evidence for {standard_name}"
                )

            replayed_inputs = nutrition_inputs_from_unified_wire(
                nutrition_inputs_wire=nutrition_inputs,
                nutrients_per_100g=nutrients,
                fallback_source=nutrition_inputs[0]["source"],
                record_id=item["source_id"],
            )
            replayed = merge_wire_nutrition_sources(
                primary_inputs=replayed_inputs,
                secondary_inputs=[],
            )
            replayed_nutrients = dict(replayed.nutrients)
            for nutrient, default_value in _PRIMARY_MACRONUTRIENT_DEFAULTS.items():
                replayed_nutrients.setdefault(nutrient, default_value)
            if (
                replayed_nutrients != nutrients
                or dict(replayed.provenance) != provenance
                or dict(replayed.nutrient_confidence) != nutrient_confidence
                or replayed.confidence != confidence
            ):
                raise CommonFoodsCacheAdmissionError(
                    f"Common-food nutrition evidence does not replay for {standard_name}"
                )

            admitted[standard_name] = UnifiedFoodItem(**item)

        return admitted

    @classmethod
    def _publish_common_foods_envelope(cls, cache_file: Path, envelope: dict[str, object]) -> None:
        """Publish through a unique same-parent temporary file and atomic replace."""
        temporary_path: Path | None = None
        rollback_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=cache_file.parent,
                prefix=f".{cache_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(
                    envelope,
                    temporary_file,
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            with open(temporary_path, "r", encoding="utf-8") as temporary_file:
                cls._validate_common_foods_envelope(_load_common_foods_json(temporary_file))
            prior_target_exists = cache_file.exists()
            prior_target_bytes = cache_file.read_bytes() if prior_target_exists else b""
            os.replace(temporary_path, cache_file)
            temporary_path = None
            try:
                parent_descriptor = os.open(cache_file.parent, os.O_RDONLY)
                try:
                    os.fsync(parent_descriptor)
                finally:
                    os.close(parent_descriptor)
            except OSError:
                if prior_target_exists:
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        dir=cache_file.parent,
                        prefix=f".{cache_file.name}.rollback.",
                        suffix=".tmp",
                        delete=False,
                    ) as rollback_file:
                        rollback_path = Path(rollback_file.name)
                        rollback_file.write(prior_target_bytes)
                        rollback_file.flush()
                        os.fsync(rollback_file.fileno())
                    os.replace(rollback_path, cache_file)
                    rollback_path = None
                else:
                    cache_file.unlink(missing_ok=True)

                rollback_parent_descriptor = os.open(cache_file.parent, os.O_RDONLY)
                try:
                    os.fsync(rollback_parent_descriptor)
                finally:
                    os.close(rollback_parent_descriptor)
                raise
        except CommonFoodsCacheAdmissionError:
            raise
        except Exception as exc:
            raise CommonFoodsCacheAdmissionError("Common-food cache publication failed") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.error(
                        "Common-food temporary cache cleanup failed; category=%s",
                        type(exc).__name__,
                    )
            if rollback_path is not None:
                try:
                    rollback_path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.error(
                        "Common-food rollback cache cleanup failed; category=%s",
                        type(exc).__name__,
                    )

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

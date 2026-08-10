"""
USDA FoodData Central API Client

RU: Клиент для работы с API USDA FoodData Central.
EN: Client for USDA FoodData Central API integration.

This module provides access to the USDA's comprehensive nutrition database
with detailed macro and micronutrient information for foods.

API Documentation: https://fdc.nal.usda.gov/api-guide
Data License: Public Domain (CC0 1.0 Universal)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import httpx

from ._testing import is_test_runtime

logger = logging.getLogger(__name__)


def _log_network_error(operation: str, exc: Exception) -> None:
    if is_test_runtime():
        logger.info(
            "USDA request failed; operation=%s; category=%s",
            operation,
            type(exc).__name__,
        )
        return
    logger.error(
        "USDA request failed; operation=%s; category=%s",
        operation,
        type(exc).__name__,
    )


@dataclass
class USDAFoodItem:
    """
    RU: Элемент из базы данных USDA с полной питательной информацией.
    EN: USDA food item with complete nutritional information.
    """

    fdc_id: int
    description: str
    food_category: Optional[str]
    nutrients_per_100g: Dict[str, float]  # Nutrient name -> amount per 100g
    data_type: str  # "Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"
    publication_date: Optional[str]
    brand_owner: Optional[str] = None
    brand_name: Optional[str] = None
    gtin_upc: Optional[str] = None

    def to_menu_engine_format(self) -> Dict[str, Any]:
        """
        RU: Конвертирует в формат для menu_engine.
        EN: Converts to menu_engine format.
        """
        return {
            "name": self.description,
            "nutrients_per_100g": self.nutrients_per_100g,
            "cost_per_100g": 1.0,  # Default cost - can be overridden
            "tags": self._generate_tags(),
            "availability_regions": ["US", "BY", "RU"],  # Assume global availability
            "source": "USDA FoodData Central",
            "fdc_id": self.fdc_id,
        }

    def _generate_tags(self) -> List[str]:
        """Generate diet tags based on food description and nutrients."""
        tags = []
        description_lower = self.description.lower()

        # Vegetarian/Vegan detection
        animal_keywords = [
            "chicken",
            "beef",
            "pork",
            "fish",
            "salmon",
            "tuna",
            "meat",
            "egg",
        ]
        if not any(keyword in description_lower for keyword in animal_keywords):
            tags.append("VEG")

        # Check if likely vegan (no dairy either)
        dairy_keywords = ["milk", "cheese", "yogurt", "butter", "cream"]
        if "VEG" in tags and not any(keyword in description_lower for keyword in dairy_keywords):
            tags.append("VEGAN")

        # Gluten-free approximation (this would need more sophisticated logic)
        gluten_keywords = ["wheat", "bread", "pasta", "cereal", "flour"]
        if not any(keyword in description_lower for keyword in gluten_keywords):
            tags.append("GF")

        return tags


class USDAClient:
    """
    RU: Клиент для работы с USDA FoodData Central API.
    EN: Client for USDA FoodData Central API.

    Provides methods to search foods and get detailed nutrition information.
    Official API guide limit is 1,000 requests/hour per IP. DEMO_KEY is much
    lower at 30 requests/hour and 50 requests/day, so CI must stay offline.
    """

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    DEFAULT_RATE_LIMIT_PER_HOUR = 1000
    DEMO_KEY_RATE_LIMIT_PER_HOUR = 30
    DEMO_KEY_RATE_LIMIT_PER_DAY = 50
    DEFAULT_SEARCH_DATA_TYPES = ("Foundation", "SR Legacy")

    # Type alias for httpx param values
    ParamValue = Union[
        str,
        int,
        float,
        bool,
        None,
        Sequence[Union[str, int, float, bool, None]],
    ]

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize USDA client.

        Args:
            api_key: Optional API key. If None, will use demo key with limitations.
        """
        self.api_key = (
            api_key or "DEMO_KEY"
        )  # nosec B105: USDA public DEMO_KEY fallback for API demos (remove-by: 2027-06-30, ref: ledger-phase2-nosec-migration)
        self.client = httpx.AsyncClient()

        # Common nutrient mappings (USDA nutrient IDs to our standard names)
        self.nutrient_mapping = {
            # Macronutrients
            1003: "protein_g",
            1004: "fat_g",
            1005: "carbs_g",
            1079: "fiber_g",
            # Energy
            1008: "kcal",
            # Minerals (mg)
            1087: "calcium_mg",
            1089: "iron_mg",
            1090: "magnesium_mg",
            1095: "zinc_mg",
            1092: "potassium_mg",
            # Trace elements (μg)
            1140: "selenium_ug",
            1100: "iodine_ug",  # Less common in USDA data
            # Vitamins
            1106: "vitamin_a_ug",  # Vitamin A, RAE
            1114: "vitamin_d_iu",  # Vitamin D (D2 + D3)
            1162: "vitamin_c_mg",  # Vitamin C
            1175: "folate_ug",  # Folate, total
            1178: "b12_ug",  # Vitamin B-12
            # B-vitamins
            1165: "thiamin_mg",  # Thiamin (B1)
            1166: "riboflavin_mg",  # Riboflavin (B2)
            1167: "niacin_mg",  # Folate, total
            1179: "b6_mg",  # Vitamin B-6
        }

    async def search_foods(self, query: str, page_size: int = 25) -> List[USDAFoodItem]:
        """
        RU: Поиск продуктов по названию.
        EN: Search foods by name.

        Args:
            query: Search query (e.g., "chicken breast")
            page_size: Number of results to return (max 200)

        Returns:
            List of USDAFoodItem objects
        """
        try:
            url = f"{self.BASE_URL}/foods/search"
            # Ensure param types match httpx expectations
            params: Dict[str, USDAClient.ParamValue] = {
                "query": query,
                "pageSize": min(page_size, 200),
                "api_key": self.api_key,
                "dataType": list(self.DEFAULT_SEARCH_DATA_TYPES),
                "sortBy": "dataType.keyword",
                "sortOrder": "asc",
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            foods = []
            for food_data in data.get("foods", []):
                food_item = self._parse_food_item(food_data)
                if food_item:
                    foods.append(food_item)

            logger.info(
                "USDA request succeeded; operation=search_foods; result_count=%d",
                len(foods),
            )
            return foods

        except Exception as exc:
            _log_network_error("search_foods", exc)
            return []

    async def get_food_details(self, fdc_id: int) -> Optional[USDAFoodItem]:
        """
        RU: Получить детальную информацию о продукте по FDC ID.
        EN: Get detailed food information by FDC ID.

        Args:
            fdc_id: FoodData Central ID

        Returns:
            USDAFoodItem or None if not found
        """
        try:
            url = f"{self.BASE_URL}/food/{fdc_id}"
            params = {"api_key": self.api_key}

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            food_item = self._parse_food_item(data)
            logger.info(
                "USDA request succeeded; operation=get_food_details; result_count=%d",
                int(food_item is not None),
            )
            return food_item

        except Exception as exc:
            _log_network_error("get_food_details", exc)
            return None

    async def get_multiple_foods(self, fdc_ids: List[int]) -> List[USDAFoodItem]:
        """
        RU: Получить информацию о нескольких продуктах одним запросом.
        EN: Get information about multiple foods in one request.

        Args:
            fdc_ids: List of FoodData Central IDs

        Returns:
            List of USDAFoodItem objects
        """
        try:
            url = f"{self.BASE_URL}/foods"
            payload = {
                "fdcIds": fdc_ids[:20],  # Limit to 20 IDs per request
                "format": "abridged",
                "nutrients": list(self.nutrient_mapping.keys()),
            }

            response = await self.client.post(url, json=payload, params={"api_key": self.api_key})
            response.raise_for_status()
            data = response.json()

            foods = []
            for food_data in data:
                food_item = self._parse_food_item(food_data)
                if food_item:
                    foods.append(food_item)

            logger.info(
                "USDA request succeeded; operation=get_multiple_foods; "
                "result_count=%d; batch_count=%d",
                len(foods),
                min(len(fdc_ids), 20),
            )
            return foods

        except Exception as exc:
            _log_network_error("get_multiple_foods", exc)
            return []

    def _validate_fdc_id(self, fdc_id_raw: object) -> Optional[int]:
        """
        RU: Валидирует и нормализует FDC ID.
        EN: Validates and normalizes FDC ID.

        Args:
            fdc_id_raw: Raw FDC ID value from API (can be int, str, or other)

        Returns:
            Validated FDC ID as int, or None if invalid
        """
        if isinstance(fdc_id_raw, str):
            try:
                return int(fdc_id_raw)
            except ValueError as exc:
                logger.warning(
                    "USDA identifier rejected; operation=parse_food_item; category=%s",
                    type(exc).__name__,
                )
                return None
        elif isinstance(fdc_id_raw, int) and not isinstance(fdc_id_raw, bool):
            return fdc_id_raw
        else:
            logger.warning("USDA identifier rejected; operation=parse_food_item")
            return None

    def _normalize_nutrient_id(self, nutrient_id_raw: object) -> Optional[int]:
        """Normalize USDA nutrient IDs from search and detail payload variants."""
        if isinstance(nutrient_id_raw, int) and not isinstance(nutrient_id_raw, bool):
            return nutrient_id_raw
        if isinstance(nutrient_id_raw, str):
            try:
                return int(nutrient_id_raw)
            except ValueError:
                return None
        return None

    def _extract_nutrient_id(self, nutrient_data: Mapping[str, Any]) -> Optional[int]:
        """Extract nutrient ID from flat search payloads or nested detail payloads."""
        nutrient_id = self._normalize_nutrient_id(nutrient_data.get("nutrientId"))
        if nutrient_id is not None:
            return nutrient_id
        nested_nutrient = nutrient_data.get("nutrient")
        if isinstance(nested_nutrient, Mapping):
            return self._normalize_nutrient_id(nested_nutrient.get("id"))
        return None

    def _extract_nutrient_amount(self, nutrient_data: Mapping[str, Any]) -> Optional[float]:
        """Extract a numeric nutrient amount while preserving valid zero values."""
        amount_raw = (
            nutrient_data.get("value") if "value" in nutrient_data else nutrient_data.get("amount")
        )
        if amount_raw is None:
            return None
        try:
            return float(amount_raw)
        except (TypeError, ValueError):
            raise ValueError(f"invalid USDA nutrient amount: {amount_raw!r}")

    def _parse_food_item(self, food_data: object | None) -> Optional[USDAFoodItem]:
        """
        RU: Парсит данные продукта из API ответа.
        EN: Parse food item from API response.
        """
        if not isinstance(food_data, Mapping):
            return None

        try:
            # Extract basic info
            fdc_id_raw = food_data.get("fdcId")
            fdc_id = self._validate_fdc_id(fdc_id_raw)
            if fdc_id is None:
                return None
            description_raw = food_data.get("description")
            description = description_raw if isinstance(description_raw, str) else "Unknown Food"
            data_type_raw = food_data.get("dataType")
            data_type = data_type_raw if isinstance(data_type_raw, str) else "Unknown"
            publication_date_raw = food_data.get("publicationDate") or food_data.get(
                "publishedDate"
            )
            publication_date = (
                publication_date_raw if isinstance(publication_date_raw, str) else None
            )

            # Extract food category
            food_category = None
            if "foodCategory" in food_data:
                food_category_data = food_data["foodCategory"]
                if isinstance(food_category_data, dict):
                    food_category = food_category_data.get("description")
                elif isinstance(food_category_data, str):
                    food_category = food_category_data
            if food_category is None:
                branded_category = food_data.get("brandedFoodCategory")
                if isinstance(branded_category, str):
                    food_category = branded_category

            brand_owner_raw = food_data.get("brandOwner")
            brand_name_raw = food_data.get("brandName")
            gtin_upc_raw = food_data.get("gtinUpc") or food_data.get("gtinUPC")
            brand_owner = brand_owner_raw if isinstance(brand_owner_raw, str) else None
            brand_name = brand_name_raw if isinstance(brand_name_raw, str) else None
            gtin_upc = gtin_upc_raw if isinstance(gtin_upc_raw, str) else None

            # Extract nutrients
            nutrients_per_100g = {}
            for nutrient_data in food_data.get("foodNutrients", []):
                # Handle different API response formats
                if isinstance(nutrient_data, dict):
                    nutrient_id = self._extract_nutrient_id(nutrient_data)
                    if nutrient_id not in self.nutrient_mapping:
                        continue
                    amount = self._extract_nutrient_amount(nutrient_data)
                    if amount is None:
                        continue
                    nutrient_name = self.nutrient_mapping[nutrient_id]
                    nutrients_per_100g[nutrient_name] = amount

            # Only return foods with substantial nutrition data
            if len(nutrients_per_100g) < 3:
                logger.warning("USDA item rejected; operation=parse_food_item")
                return None

            return USDAFoodItem(
                fdc_id=fdc_id,
                description=description,
                food_category=food_category,
                nutrients_per_100g=nutrients_per_100g,
                data_type=data_type,
                publication_date=publication_date,
                brand_owner=brand_owner,
                brand_name=brand_name,
                gtin_upc=gtin_upc,
            )

        except Exception as exc:
            logger.error(
                "USDA item parse failed; operation=parse_food_item; category=%s",
                type(exc).__name__,
            )
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        try:
            await self.client.aclose()
        except RuntimeError as exc:
            # Mirror OFFClient.close: suppress only when the loop is already closed.
            # (This can happen during interpreter shutdown / pytest teardown.)
            error_msg = str(exc).lower()
            if "event loop" in error_msg and "closed" in error_msg:
                logger.debug(
                    "USDA close suppressed; operation=close; category=%s",
                    type(exc).__name__,
                )
                return
            raise


# Convenience functions for common foods
async def get_common_foods_database() -> Dict[str, USDAFoodItem]:
    """
    RU: Получает базу часто используемых продуктов из USDA.
    EN: Gets database of commonly used foods from USDA.

    Returns a dictionary of common foods with standardized names.
    """
    client = USDAClient()

    try:
        # Common foods with their likely USDA descriptions
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
        }

        foods_db = {}

        for standard_name, search_query in common_searches.items():
            try:
                search_results = await client.search_foods(search_query, page_size=5)
                if search_results:
                    # Take the first result (usually most relevant)
                    best_match = search_results[0]
                    foods_db[standard_name] = best_match
                    logger.info(
                        "USDA common-food row resolved; operation=fetch_common_foods; "
                        "result_count=1"
                    )

                # Small delay to be respectful to the API
                await asyncio.sleep(0.1)

            except Exception as exc:
                logger.error(
                    "USDA common-food row failed; operation=fetch_common_foods; category=%s",
                    type(exc).__name__,
                )
                continue

        logger.info(
            "USDA common-food fetch completed; operation=fetch_common_foods; result_count=%d",
            len(foods_db),
        )
        return foods_db

    finally:
        await client.close()


if __name__ == "__main__":  # pragma: no cover
    # Test the USDA client
    async def test_usda_client() -> None:
        client = USDAClient()

        try:
            # Test search
            print("Testing USDA search for 'chicken breast'...")
            results = await client.search_foods("chicken breast", page_size=3)

            for result in results:
                print(f"\nFound: {result.description}")
                print(f"FDC ID: {result.fdc_id}")
                print(f"Category: {result.food_category}")
                print(f"Key nutrients: {list(result.nutrients_per_100g.keys())}")

                # Show some key nutrition values
                nutrients = result.nutrients_per_100g
                print(f"Protein: {nutrients.get('protein_g', 'N/A')}g")
                print(f"Iron: {nutrients.get('iron_mg', 'N/A')}mg")
                print(f"Calcium: {nutrients.get('calcium_mg', 'N/A')}mg")

        finally:
            await client.close()

    # Run test
    asyncio.run(test_usda_client())

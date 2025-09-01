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
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


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
            "fdc_id": self.fdc_id
        }

    def _generate_tags(self) -> List[str]:
        """Generate diet tags based on food description and nutrients."""
        tags = []
        description_lower = self.description.lower()

        # Vegetarian/Vegan detection
        animal_keywords = ["chicken", "beef", "pork", "fish", "salmon", "tuna", "meat", "egg"]
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
    Rate limits: No explicit limits mentioned, but we'll implement reasonable delays.
    """

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize USDA client.

        Args:
            api_key: Optional API key. If None, will use demo key with limitations.
        """
        self.api_key = api_key or "DEMO_KEY"  # USDA provides demo access
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
            1175: "folate_ug",     # Folate, total
            1178: "b12_ug",        # Vitamin B-12

            # B-vitamins
            1165: "thiamin_mg",    # Thiamin (B1)
            1166: "riboflavin_mg", # Riboflavin (B2)
            1167: "niacin_mg",     # Folate, total
            1179: "b6_mg",         # Vitamin B-6
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
            params = {
                "query": query,
                "pageSize": min(page_size, 200),
                "api_key": self.api_key,
                "dataType": ["Foundation", "SR Legacy"],  # Focus on most reliable data
                "sortBy": "dataType.keyword",
                "sortOrder": "asc"
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            foods = []
            for food_data in data.get("foods", []):
                food_item = self._parse_food_item(food_data)
                if food_item:
                    foods.append(food_item)

            logger.info(f"Found {len(foods)} foods for query: {query}")
            return foods

        except Exception as e:
            logger.error(f"Error searching USDA foods for '{query}': {e}")
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

            return self._parse_food_item(data)

        except Exception as e:
            logger.error(f"Error getting USDA food details for FDC ID {fdc_id}: {e}")
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
                "nutrients": list(self.nutrient_mapping.keys())
            }

            response = await self.client.post(
                url,
                json=payload,
                params={"api_key": self.api_key}
            )
            response.raise_for_status()
            data = response.json()

            foods = []
            for food_data in data:
                food_item = self._parse_food_item(food_data)
                if food_item:
                    foods.append(food_item)

            return foods

        except Exception as e:
            logger.error(f"Error getting multiple USDA foods: {e}")
            return []

    def _parse_food_item(self, food_data: Dict) -> Optional[USDAFoodItem]:
        """
        RU: Парсит данные продукта из API ответа.
        EN: Parse food item from API response.
        """
        try:
            # Debug: Check if food_data is actually a dict
            if not isinstance(food_data, dict):
                logger.error(f"Expected dict, got {type(food_data)}: {food_data}")
                return None

            # Extract basic info
            fdc_id = food_data.get("fdcId")
            description = food_data.get("description", "Unknown Food")
            data_type = food_data.get("dataType", "Unknown")
            publication_date = food_data.get("publicationDate") or food_data.get("publishedDate")

            # Extract food category
            food_category = None
            if "foodCategory" in food_data:
                food_category_data = food_data["foodCategory"]
                if isinstance(food_category_data, dict):
                    food_category = food_category_data.get("description")
                elif isinstance(food_category_data, str):
                    food_category = food_category_data

            # Extract nutrients
            nutrients_per_100g = {}
            for nutrient_data in food_data.get("foodNutrients", []):
                # Handle different API response formats
                if isinstance(nutrient_data, dict):
                    # Search API uses 'nutrientId', details API might use 'nutrient.id'
                    nutrient_id = nutrient_data.get("nutrientId") or nutrient_data.get("nutrient", {}).get("id")
                    amount = nutrient_data.get("value") or nutrient_data.get("amount")

                    if nutrient_id in self.nutrient_mapping and amount is not None:
                        nutrient_name = self.nutrient_mapping[nutrient_id]
                        nutrients_per_100g[nutrient_name] = float(amount)

            # Only return foods with substantial nutrition data
            if len(nutrients_per_100g) < 3:
                logger.warning(f"Food {description} has insufficient nutrition data ({len(nutrients_per_100g)} nutrients)")
                return None

            return USDAFoodItem(
                fdc_id=fdc_id,
                description=description,
                food_category=food_category,
                nutrients_per_100g=nutrients_per_100g,
                data_type=data_type,
                publication_date=publication_date
            )

        except Exception as e:
            logger.error(f"Error parsing USDA food item: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


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
            "black_beans": "beans black mature seeds cooked boiled"
        }

        foods_db = {}

        for standard_name, search_query in common_searches.items():
            try:
                search_results = await client.search_foods(search_query, page_size=5)
                if search_results:
                    # Take the first result (usually most relevant)
                    best_match = search_results[0]
                    foods_db[standard_name] = best_match
                    logger.info(f"Found USDA food for {standard_name}: {best_match.description}")

                # Small delay to be respectful to the API
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error fetching {standard_name}: {e}")
                continue

        return foods_db

    finally:
        await client.close()


if __name__ == "__main__":
    # Test the USDA client
    async def test_usda_client():
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

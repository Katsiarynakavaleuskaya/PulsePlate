"""
Open Food Facts API Client

RU: Клиент для работы с API Open Food Facts.
EN: Client for Open Food Facts API integration.

This module provides access to the Open Food Facts database with product information,
nutritional data, ingredients, and packaging information.

API Documentation: https://world.openfoodfacts.org/data
Data License: Open Database License (ODbL)
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .http_config import HTTPClientConfig

logger = logging.getLogger(__name__)

# Flag to indicate if Open Food Facts client is available
OFF_AVAILABLE = True


@dataclass
class OFFFoodItem:
    """
    RU: Элемент из базы данных Open Food Facts с полной информацией.
    EN: Open Food Facts food item with complete information.
    """

    code: str  # Barcode
    product_name: str
    categories: List[str]
    nutrients_per_100g: Dict[str, float]
    ingredients_text: Optional[str]
    brands: Optional[str]
    labels: List[str]
    countries: List[str]
    packaging: List[str]
    image_url: Optional[str]
    last_modified_t: int  # Unix timestamp

    def to_menu_engine_format(self) -> Dict[str, Any]:
        """
        RU: Конвертирует в формат для menu_engine.
        EN: Converts to menu_engine format.
        """
        return {
            "name": self.product_name,
            "nutrients_per_100g": self.nutrients_per_100g,
            "cost_per_100g": 1.5,  # Default cost - can be overridden
            "tags": self._generate_tags(),
            "availability_regions": self.countries,
            "source": "Open Food Facts",
            "source_id": self.code,
        }

    def _generate_tags(self) -> List[str]:
        """Generate diet tags based on labels and categories."""
        tags = []

        # Convert labels and categories to lowercase for matching
        all_labels = [label.lower() for label in self.labels]
        all_categories = [cat.lower() for cat in self.categories]

        # Organic
        if any("organic" in label or "bio" in label for label in all_labels):
            tags.append("ORGANIC")

        # Vegetarian/Vegan detection
        if any("vegetarian" in label for label in all_labels):
            tags.append("VEG")

        if any("vegan" in label for label in all_labels):
            tags.append("VEGAN")

        # Gluten-free
        # Gluten-free
        gluten_free_labels = ["gluten-free", "sans gluten", "gluten free"]
        if any(label in gluten_free_labels for label in all_labels):
            tags.append("GF")

        # Low cost
        if any("discount" in cat or "value" in cat for cat in all_categories):
            tags.append("LOW_COST")

        return tags


class OFFClient:
    """
    RU: Клиент для работы с Open Food Facts API.
    EN: Client for Open Food Facts API.

    Provides methods to search products and get detailed information.
    Rate limits: 100 requests/minute for anonymous users, higher for API accounts.
    """

    # Note: Using v0 API on .org domain due to v2 API returning 504 Gateway Timeout errors
    # on .org domain. The official v2 API on .net domain works but requires migration.
    # TODO: Consider migrating to https://world.openfoodfacts.net/api/v2/ for better
    # performance and modern REST endpoints when .org infrastructure is stable.
    BASE_URL = "https://world.openfoodfacts.org/api/v0"
    CGI_BASE_URL = "https://world.openfoodfacts.org/cgi"

    def __init__(self) -> None:
        """
        Initialize Open Food Facts client.

        Lifecycle:
            The underlying async HTTP client must be explicitly closed by
            the caller (use `await client.close()`), or use OFFClient as an
            async context manager to ensure automatic cleanup:

                async with OFFClient() as off:
                    items = await off.search_products("apple")
        """
        # Underlying async HTTP client with centralized configuration
        self.client = HTTPClientConfig.create_client()

        # Common nutrient mappings (Open Food Facts nutrient names to our standard names)
        self.nutrient_mapping = {
            # Macronutrients
            "proteins_100g": "protein_g",
            "fat_100g": "fat_g",
            "carbohydrates_100g": "carbs_g",
            "fiber_100g": "fiber_g",
            "energy-kcal_100g": "kcal",
            # Minerals (mg)
            "calcium_100g": "calcium_mg",
            "iron_100g": "iron_mg",
            "magnesium_100g": "magnesium_mg",
            "zinc_100g": "zinc_mg",
            "potassium_100g": "potassium_mg",
            # Trace elements (μg)
            "selenium_100g": "selenium_ug",
            "iodine_100g": "iodine_ug",
            # Vitamins
            "vitamin-a_100g": "vitamin_a_ug",
            "vitamin-d_100g": "vitamin_d_iu",
            "vitamin-c_100g": "vitamin_c_mg",
            "folates_100g": "folate_ug",
            "vitamin-b12_100g": "b12_ug",
            # B-vitamins
            "vitamin-b1_100g": "thiamin_mg",
            "vitamin-b2_100g": "riboflavin_mg",
            "vitamin-pp_100g": "niacin_mg",
            "vitamin-b6_100g": "b6_mg",
        }

    async def search_products(self, query: str, page_size: int = 25) -> List[OFFFoodItem]:
        """
        RU: Поиск продуктов по названию.
        EN: Search products by name.

        Args:
            query: Search query (e.g., "chocolate")
            page_size: Number of results to return (max 100)

        Returns:
            List of OFFFoodItem objects
        """
        try:
            # Use the CGI search endpoint for better compatibility
            url = f"{self.CGI_BASE_URL}/search.pl"
            params = {
                "search_terms": query,
                "page_size": str(min(page_size, 100)),
                "search_simple": "1",
                "action": "process",
                "json": "1",
                # Note: CGI In core/food_apis/openfoodfacts_client.py around lines 112 to 117, the __init__ docstring must document the HTTP client's lifecycle because HTTPClientConfig.create_client() requires explicit cleanup; update the __init__ docstring to add a brief lifecycle note that callers must call close() when finished (or prefer using the client as an async context manager), and implement async __aenter__ and __aexit__ methods on the class that return self and call await self.close() respectively so callers can use "async with" and avoid resource leaks.search.pl endpoint ignores fields parameter, so we omit it
            }

            response = await self.client.get(url, params=params)
            # Support both sync and async mocks for tests
            maybe = response.raise_for_status()
            if inspect.isawaitable(maybe):
                await maybe
            res = response.json()
            data = await res if inspect.isawaitable(res) else res

            products = []
            for product_data in data.get("products", []):
                food_item = self._parse_product_item(product_data)
                if food_item:
                    products.append(food_item)

            logger.info(f"Found {len(products)} products for query: {query}")
            return products

        except Exception as e:
            logger.error(f"Error searching Open Food Facts products for '{query}': {e}")
            return []

    async def get_product_details(self, barcode: str) -> Optional[OFFFoodItem]:
        """
        RU: Получить детальную информацию о продукте по штрихкоду.
        EN: Get detailed product information by barcode.

        Args:
            barcode: Product barcode

        Returns:
            OFFFoodItem or None if not found
        """
        try:
            url = f"{self.BASE_URL}/product/{barcode}"
            params = {
                "fields": (
                    "code,product_name,nutriments,categories,ingredients_text,"
                    "brands,labels,countries,packaging,image_url,last_modified_t"
                )
            }

            response = await self.client.get(url, params=params)
            maybe = response.raise_for_status()
            if inspect.isawaitable(maybe):
                await maybe
            res = response.json()
            data = await res if inspect.isawaitable(res) else res

            if data.get("status") == 1:  # Product found
                return self._parse_product_item(data.get("product", {}))

        except Exception as e:
            logger.error(
                f"Error getting Open Food Facts product details for barcode {barcode}: {e}"
            )
            return None

        # Explicitly return None when product is not found
        return None

    async def close(self) -> None:
        """Close underlying HTTP client."""
        try:
            await self.client.aclose()
        except Exception:
            pass

    async def __aenter__(self) -> "OFFClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def _parse_product_item(self, product_data: Dict[str, Any]) -> Optional[OFFFoodItem]:
        """
        RU: Парсит данные продукта из формата Open Food Facts.
        EN: Parses product data from Open Food Facts format.
        """
        try:
            code = product_data.get("code", "")
            if not code:
                return None

            product_name = product_data.get("product_name", "").strip()
            if not product_name:
                return None

            # Parse nutrients
            nutrients_raw = product_data.get("nutriments", {})
            nutrients_per_100g = {}

            for off_nutrient, standard_name in self.nutrient_mapping.items():
                value = nutrients_raw.get(off_nutrient)
                if value is not None and isinstance(value, (int, float)):
                    nutrients_per_100g[standard_name] = float(value)

            # Parse categories
            categories_raw = product_data.get("categories", "")
            categories = (
                [cat.strip() for cat in categories_raw.split(",") if cat.strip()]
                if categories_raw
                else []
            )

            # Parse labels
            labels_raw = product_data.get("labels", "")
            labels = (
                [label.strip() for label in labels_raw.split(",") if label.strip()]
                if labels_raw
                else []
            )

            # Parse countries
            countries_raw = product_data.get("countries", "")
            countries = (
                [country.strip() for country in countries_raw.split(",") if country.strip()]
                if countries_raw
                else ["World"]
            )

            # Parse packaging
            packaging_raw = product_data.get("packaging", "")
            packaging = (
                [pkg.strip() for pkg in packaging_raw.split(",") if pkg.strip()]
                if packaging_raw
                else []
            )

            return OFFFoodItem(
                code=code,
                product_name=product_name,
                categories=categories,
                nutrients_per_100g=nutrients_per_100g,
                ingredients_text=product_data.get("ingredients_text"),
                brands=product_data.get("brands"),
                labels=labels,
                countries=countries,
                packaging=packaging,
                image_url=product_data.get("image_url"),
                last_modified_t=product_data.get("last_modified_t", 0),
            )

        except Exception as e:
            logger.error(f"Error parsing Open Food Facts product data: {e}")
            return None

    async def get_multiple_products(self, barcodes: List[str]) -> List[OFFFoodItem]:
        """
        RU: Получить информацию о нескольких продуктах по штрихкодам.
        EN: Get information for multiple products by barcodes.
        """
        tasks = [self.get_product_details(barcode) for barcode in barcodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and None values
        valid_results: List[OFFFoodItem] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.error(f"Error fetching product: {result}")
            elif result is not None:
                valid_results.append(result)

        return valid_results

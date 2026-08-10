"""
Tests for Open Food Facts Client

RU: Тесты для клиента Open Food Facts.
EN: Tests for Open Food Facts client.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.food_apis.openfoodfacts_client import OFFClient, OFFFoodItem


class TestOFFClient:
    """Test Open Food Facts client functionality."""

    def setup_method(self):
        """Set up test client."""
        self.client = OFFClient()

    def teardown_method(self):
        """Clean up test environment."""
        pass

    def test_off_food_item_creation(self):
        """Test OFFFoodItem creation and tag generation."""
        # Create a sample OFFFoodItem
        item = OFFFoodItem(
            code="123456789",
            product_name="Organic Chocolate Bar",
            categories=["Snacks", "Sweets"],
            nutrients_per_100g={"protein_g": 5.0, "fat_g": 30.0, "carbs_g": 55.0},
            ingredients_text="Cocoa butter, sugar, milk powder",
            brands="ChocoCorp",
            labels=["Organic", "Fair Trade"],
            countries=["France", "World"],
            packaging=["Plastic"],
            image_url="https://example.com/image.jpg",
            last_modified_t=1640995200,
        )

        # Test tag generation
        tags = item._generate_tags()
        assert "ORGANIC" in tags
        assert "LOW_COST" not in tags  # Not a discount product

        # Test menu engine format conversion
        menu_format = item.to_menu_engine_format()
        assert menu_format["name"] == "Organic Chocolate Bar"
        assert menu_format["source"] == "Open Food Facts"
        assert "ORGANIC" in menu_format["tags"]

    def test_off_food_item_vegan_tag(self):
        """Test vegan tag generation."""
        # Create a sample OFFFoodItem with vegan label
        item = OFFFoodItem(
            code="123456789",
            product_name="Vegan Protein Powder",
            categories=["Supplements"],
            nutrients_per_100g={"protein_g": 80.0, "fat_g": 5.0, "carbs_g": 5.0},
            ingredients_text="Pea protein isolate",
            brands="VeganFit",
            labels=["Vegan", "Gluten Free"],
            countries=["USA", "World"],
            packaging=["Tub"],
            image_url="https://example.com/image2.jpg",
            last_modified_t=1640995200,
        )

        # Test tag generation
        tags = item._generate_tags()
        assert "VEGAN" in tags
        assert "GF" in tags

    def test_off_food_item_gluten_free_tag(self):
        """Test gluten-free tag generation."""
        # Create a sample OFFFoodItem with gluten-free label
        item = OFFFoodItem(
            code="987654321",
            product_name="Gluten Free Bread",
            categories=["Bakery"],
            nutrients_per_100g={
                "protein_g": 8.0,
                "fat_g": 3.0,
                "carbs_g": 45.0,
                "fiber_g": 6.0,
            },
            ingredients_text="Rice flour, water, yeast",
            brands="GlutenFree Co",
            labels=["Gluten Free"],
            countries=["USA", "Canada"],
            packaging=["Bag"],
            image_url="https://example.com/image3.jpg",
            last_modified_t=1640995200,
        )

        # Test tag generation
        tags = item._generate_tags()
        assert "GF" in tags

    def test_nutrient_mapping(self):
        """Test that nutrient mapping is correctly defined."""
        # Check that we have the basic nutrient mappings
        assert "proteins_100g" in self.client.nutrient_mapping
        assert "fat_100g" in self.client.nutrient_mapping
        assert "carbohydrates_100g" in self.client.nutrient_mapping
        assert "energy-kcal_100g" in self.client.nutrient_mapping

        # Check that mappings convert to our standard names
        assert self.client.nutrient_mapping["proteins_100g"] == "protein_g"
        assert self.client.nutrient_mapping["fat_100g"] == "fat_g"
        assert self.client.nutrient_mapping["carbohydrates_100g"] == "carbs_g"
        assert self.client.nutrient_mapping["energy-kcal_100g"] == "kcal"

    def test_parse_product_item(self):
        """Test parsing of product data."""
        # Sample product data from Open Food Facts
        sample_data = {
            "code": "123456789",
            "product_name": "Test Product",
            "nutriments": {
                "proteins_100g": 10.0,
                "fat_100g": 5.0,
                "carbohydrates_100g": 20.0,
                "energy-kcal_100g": 150.0,
            },
            "categories": "Snacks, Sweets",
            "labels": "Organic, Vegan",
            "countries": "France, World",
        }

        # Test parsing
        item = self.client._parse_product_item(sample_data)
        assert item is not None
        assert item.code == "123456789"
        assert item.product_name == "Test Product"
        assert "protein_g" in item.nutrients_per_100g
        assert item.nutrients_per_100g["protein_g"] == 10.0
        assert item.nutrition_inputs[0]["source"] == "estimate"
        assert item.nutrition_provenance["protein_g"] == "estimate"
        assert item.nutrition_nutrient_confidence["protein_g"] == pytest.approx(0.4)
        assert 0.0 <= item.nutrition_confidence <= 1.0
        assert "VEGAN" in item._generate_tags()

    def test_parse_product_item_rejects_boolean_nutrient_scalars(self) -> None:
        """Boolean OFF fields are neither nutrients nor retained raw scalar evidence."""
        item = self.client._parse_product_item(
            {
                "code": "boolean-scalars",
                "product_name": "Boolean Scalars",
                "nutriments": {
                    "proteins_100g": True,
                    "fat_100g": 5.0,
                    "unknown_boolean_flag": False,
                    "unknown_numeric_value": 3,
                    "unknown_text_value": "trace",
                },
            }
        )

        assert item is not None
        assert "protein_g" not in item.nutrients_per_100g
        assert item.nutrients_per_100g["fat_g"] == 5.0
        raw_payload = item.nutrition_inputs[0]["raw_payload"]
        assert isinstance(raw_payload, dict)
        assert "proteins_100g" not in raw_payload
        assert "unknown_boolean_flag" not in raw_payload
        assert raw_payload["unknown_numeric_value"] == 3
        assert raw_payload["unknown_text_value"] == "trace"

    def test_parse_product_item_missing_data(self):
        """Test parsing with missing required data."""
        # Sample product data with missing code
        sample_data = {
            "product_name": "Test Product"
            # Missing "code" field
        }

        # Should return None for invalid data
        item = self.client._parse_product_item(sample_data)
        assert item is None

        # Sample product data with missing name
        sample_data = {
            "code": "123456789"
            # Missing "product_name" field
        }

        # Should return None for invalid data
        item = self.client._parse_product_item(sample_data)
        assert item is None

    def test_parse_product_item_empty_values(self):
        """Test parsing with empty values."""
        # Sample product data with empty name
        sample_data = {
            "code": "123456789",
            "product_name": "",  # Empty name
            "nutriments": {"proteins_100g": 10.0},
        }

        # Should return None for invalid data
        item = self.client._parse_product_item(sample_data)
        assert item is None

    def test_parse_product_item_complex_nutrients(self):
        """Test parsing with complex nutrient data."""
        # Sample product data with various nutrient formats
        sample_data = {
            "code": "111111111",
            "product_name": "Complex Nutrition Product",
            "nutriments": {
                "proteins_100g": 15.5,
                "fat_100g": 7.2,
                "carbohydrates_100g": 25.8,
                "energy-kcal_100g": 200.0,
                "calcium_100g": 120.0,
                "iron_100g": 2.5,
                "vitamin-c_100g": 45.0,
                "fiber_100g": 8.5,
            },
            "categories": "Health Foods, Supplements",
            "labels": "Organic, Non-GMO",
            "countries": "USA, Canada, UK",
            "ingredients_text": "Organic ingredients, natural flavors",
            "brands": "HealthFirst",
            "packaging": "Bottle, Recyclable",
            "image_url": "https://example.com/complex.jpg",
            "last_modified_t": 1640995200,
        }

        # Test parsing
        item = self.client._parse_product_item(sample_data)
        assert item is not None
        assert item.code == "111111111"
        assert item.product_name == "Complex Nutrition Product"

        # Check nutrients
        nutrients = item.nutrients_per_100g
        assert nutrients["protein_g"] == 15.5
        assert nutrients["fat_g"] == 7.2
        assert nutrients["carbs_g"] == 25.8
        assert nutrients["kcal"] == 200.0
        assert nutrients["calcium_mg"] == 120.0
        assert nutrients["iron_mg"] == 2.5
        assert nutrients["vitamin_c_mg"] == 45.0
        assert nutrients["fiber_g"] == 8.5

        # Check other fields
        assert "Health Foods" in item.categories
        assert "Organic" in item.labels
        assert "USA" in item.countries
        assert item.brands == "HealthFirst"

    def test_generate_tags_edge_cases(self):
        """Test tag generation with edge cases."""
        # Test with no labels
        item = OFFFoodItem(
            code="111",
            product_name="Basic Product",
            categories=[],
            nutrients_per_100g={},
            ingredients_text=None,
            brands=None,
            labels=[],
            countries=["World"],
            packaging=[],
            image_url=None,
            last_modified_t=0,
        )

        tags = item._generate_tags()
        assert len(tags) == 0  # No tags should be generated

        # Test with discount category
        item.categories = ["Discount", "Snacks"]
        tags = item._generate_tags()
        assert "LOW_COST" in tags

    @pytest.mark.asyncio
    async def test_search_products_success(self):
        """Test search products functionality with successful response."""
        # Mock the HTTP client
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock response (httpx.Response methods are synchronous)
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "products": [
                        {
                            "code": "12345",
                            "product_name": "Test Product",
                            "nutriments": {"proteins_100g": 10.0},
                        }
                    ]
                }
            )
            mock_get.return_value = mock_response

            # Test search
            results = await self.client.search_products("test")
            assert len(results) == 1
            assert results[0].code == "12345"
            assert results[0].product_name == "Test Product"

    @pytest.mark.asyncio
    async def test_search_products_error(self) -> None:
        """Test search products functionality with error response."""
        # Mock the HTTP client to raise an exception
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Test search
            results = await self.client.search_products("test")
            assert len(results) == 0

    def test_concrete_logging_sinks_are_secret_safe(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Concrete OFF operations log only stable labels, counts, and categories."""
        query_marker = "off-query-marker-bd17"
        barcode_marker = "off-barcode-marker-7259"
        body_marker = "off-body-marker-70a4"
        exception_marker = "off-exception-marker-9e13"
        credential_url_marker = "https://off-credential-url-marker.invalid/private"
        token_marker = "off-token-marker-6c02"
        exception_text = (
            f"{exception_marker} {credential_url_marker}?token={token_marker} "
            f"body={body_marker} barcode={barcode_marker}"
        )
        monkeypatch.setattr(self.client, "BASE_URL", credential_url_marker)

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "products": [
                {
                    "code": barcode_marker,
                    "product_name": body_marker,
                    "nutriments": {"proteins_100g": 10.0},
                }
            ]
        }
        request_get = AsyncMock(return_value=response)
        close_http = AsyncMock()
        monkeypatch.setattr(self.client.client, "get", request_get)
        monkeypatch.setattr(self.client.client, "aclose", close_http)
        caplog.set_level(logging.DEBUG, logger="core.food_apis.openfoodfacts_client")

        async def exercise_logging_paths() -> None:
            results = await self.client.search_products(query_marker, page_size=1)
            assert len(results) == 1

            request_get.side_effect = RuntimeError(exception_text)
            assert await self.client.get_product_details(barcode_marker) is None

            assert (
                self.client._parse_product_item(
                    {
                        "code": barcode_marker,
                        "product_name": body_marker,
                        "nutriments": body_marker,
                    }
                )
                is None
            )

            batch_lookup = AsyncMock(side_effect=[RuntimeError(exception_text), None])
            monkeypatch.setattr(self.client, "get_product_details", batch_lookup)
            assert await self.client.get_multiple_products([barcode_marker, token_marker]) == []

            close_http.side_effect = RuntimeError(f"event loop is closed; {exception_text}")
            await self.client.close()

        asyncio.run(exercise_logging_paths())

        client_records = [
            record
            for record in caplog.records
            if record.name == "core.food_apis.openfoodfacts_client"
        ]
        rendered_messages = [record.getMessage() for record in client_records]
        assert (
            "OFF request succeeded; operation=search_products; result_count=1" in rendered_messages
        )
        assert (
            "OFF request failed; operation=get_product_details; category=RuntimeError"
            in rendered_messages
        )
        assert (
            "OFF item parse failed; operation=parse_product_item; category=TypeError"
            in rendered_messages
        )
        assert (
            "OFF batch item failed; operation=get_multiple_products; category=RuntimeError"
            in rendered_messages
        )
        assert (
            "OFF batch completed; operation=get_multiple_products; result_count=0; batch_count=2"
            in rendered_messages
        )
        assert "OFF close suppressed; operation=close; category=RuntimeError" in rendered_messages

        sensitive_markers = (
            query_marker,
            barcode_marker,
            body_marker,
            exception_marker,
            credential_url_marker,
            token_marker,
        )
        rendered_args = "\n".join(repr(record.args) for record in client_records)
        for marker in sensitive_markers:
            assert marker not in caplog.text
            assert marker not in rendered_args
        failure_records = [
            record
            for record in client_records
            if " failed; " in record.getMessage() or " suppressed; " in record.getMessage()
        ]
        assert len(failure_records) == 4
        assert all(record.exc_info is None for record in failure_records)

    @pytest.mark.asyncio
    async def test_search_products_filters_invalid_items(self) -> None:
        """search_products should skip items that fail parsing (food_item is None)."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            # Product data missing required fields so _parse_product_item returns None
            mock_response.json = MagicMock(return_value={"products": [{"product_name": ""}]})
            mock_get.return_value = mock_response

            results = await self.client.search_products("test")
            assert results == []

    @pytest.mark.asyncio
    async def test_get_product_details_success(self) -> None:
        """Test get product details functionality with successful response."""
        # Mock the HTTP client
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock response (httpx.Response methods are synchronous)
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "status": 1,
                    "product": {
                        "code": "12345",
                        "product_name": "Test Product",
                        "nutriments": {"proteins_100g": 10.0},
                    },
                }
            )
            mock_get.return_value = mock_response

            # Test get product details
            result = await self.client.get_product_details("12345")
            assert result is not None
            assert result.code == "12345"
            assert result.product_name == "Test Product"

    @pytest.mark.asyncio
    async def test_get_product_details_not_found(self) -> None:
        """Test get product details when product not found."""
        # Mock the HTTP client
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock response for not found (httpx.Response methods are synchronous)
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"status": 0})  # Product not found
            mock_get.return_value = mock_response

            # Test get product details
            result = await self.client.get_product_details("99999")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_product_details_error(self) -> None:
        """Test get product details functionality with error response."""
        # Mock the HTTP client to raise an exception
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Test get product details
            result = await self.client.get_product_details("12345")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_multiple_products(self) -> None:
        """Test get multiple products functionality."""
        # Mock the get_product_details method
        with patch.object(self.client, "get_product_details") as mock_get_details:
            # Mock responses
            mock_get_details.side_effect = [
                OFFFoodItem(
                    code="1",
                    product_name="Product 1",
                    categories=[],
                    nutrients_per_100g={"protein_g": 10.0},
                    ingredients_text=None,
                    brands=None,
                    labels=[],
                    countries=["World"],
                    packaging=[],
                    image_url=None,
                    last_modified_t=0,
                ),
                OFFFoodItem(
                    code="2",
                    product_name="Product 2",
                    categories=[],
                    nutrients_per_100g={"protein_g": 20.0},
                    ingredients_text=None,
                    brands=None,
                    labels=[],
                    countries=["World"],
                    packaging=[],
                    image_url=None,
                    last_modified_t=0,
                ),
            ]

            # Test get multiple products
            results = await self.client.get_multiple_products(["1", "2"])
            assert len(results) == 2
            assert results[0].code == "1"
            assert results[1].code == "2"

    @pytest.mark.asyncio
    async def test_close_client(self) -> None:
        """Test closing the HTTP client."""
        # Mock the HTTP client
        with patch.object(self.client.client, "aclose") as mock_aclose:
            # Test close
            await self.client.close()
            mock_aclose.assert_called_once()

    def test_parse_product_item_error_handling(self):
        """Test error handling in _parse_product_item method."""
        # Test with invalid data that causes an exception
        invalid_data = {
            "code": "12345",
            "product_name": "Test Product",
            "nutriments": "invalid_data",  # This should cause an exception
        }

        # Should return None when an exception occurs
        item = self.client._parse_product_item(invalid_data)
        assert item is None

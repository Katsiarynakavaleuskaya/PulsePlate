"""
Tests for Open Food Facts Client

RU: Тесты для клиента Open Food Facts.
EN: Tests for Open Food Facts client.
"""

from unittest.mock import AsyncMock, patch

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
            last_modified_t=1640995200
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
            last_modified_t=1640995200
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
            nutrients_per_100g={"protein_g": 8.0, "fat_g": 3.0, "carbs_g": 45.0, "fiber_g": 6.0},
            ingredients_text="Rice flour, water, yeast",
            brands="GlutenFree Co",
            labels=["Gluten Free"],
            countries=["USA", "Canada"],
            packaging=["Bag"],
            image_url="https://example.com/image3.jpg",
            last_modified_t=1640995200
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
                "energy-kcal_100g": 150.0
            },
            "categories": "Snacks, Sweets",
            "labels": "Organic, Vegan",
            "countries": "France, World"
        }

        # Test parsing
        item = self.client._parse_product_item(sample_data)
        assert item is not None
        assert item.code == "123456789"
        assert item.product_name == "Test Product"
        assert "protein_g" in item.nutrients_per_100g
        assert item.nutrients_per_100g["protein_g"] == 10.0
        assert "VEGAN" in item._generate_tags()

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
            "nutriments": {
                "proteins_100g": 10.0
            }
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
                "fiber_100g": 8.5
            },
            "categories": "Health Foods, Supplements",
            "labels": "Organic, Non-GMO",
            "countries": "USA, Canada, UK",
            "ingredients_text": "Organic ingredients, natural flavors",
            "brands": "HealthFirst",
            "packaging": "Bottle, Recyclable",
            "image_url": "https://example.com/complex.jpg",
            "last_modified_t": 1640995200
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
            last_modified_t=0
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
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock response
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "products": [
                    {
                        "code": "12345",
                        "product_name": "Test Product",
                        "nutriments": {"proteins_100g": 10.0}
                    }
                ]
            })
            mock_get.return_value = mock_response

            # Test search
            results = await self.client.search_products("test")
            assert len(results) == 1
            assert results[0].code == "12345"
            assert results[0].product_name == "Test Product"

    @pytest.mark.asyncio
    async def test_search_products_error(self):
        """Test search products functionality with error response."""
        # Mock the HTTP client to raise an exception
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Test search
            results = await self.client.search_products("test")
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_product_details_success(self):
        """Test get product details functionality with successful response."""
        # Mock the HTTP client
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock response
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "status": 1,
                "product": {
                    "code": "12345",
                    "product_name": "Test Product",
                    "nutriments": {"proteins_100g": 10.0}
                }
            })
            mock_get.return_value = mock_response

            # Test get product details
            result = await self.client.get_product_details("12345")
            assert result is not None
            assert result.code == "12345"
            assert result.product_name == "Test Product"

    @pytest.mark.asyncio
    async def test_get_product_details_not_found(self):
        """Test get product details when product not found."""
        # Mock the HTTP client
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock response for not found
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "status": 0  # Product not found
            })
            mock_get.return_value = mock_response

            # Test get product details
            result = await self.client.get_product_details("99999")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_product_details_error(self):
        """Test get product details functionality with error response."""
        # Mock the HTTP client to raise an exception
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Test get product details
            result = await self.client.get_product_details("12345")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_multiple_products(self):
        """Test get multiple products functionality."""
        # Mock the get_product_details method
        with patch.object(self.client, 'get_product_details') as mock_get_details:
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
                    last_modified_t=0
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
                    last_modified_t=0
                )
            ]

            # Test get multiple products
            results = await self.client.get_multiple_products(["1", "2"])
            assert len(results) == 2
            assert results[0].code == "1"
            assert results[1].code == "2"

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the HTTP client."""
        # Mock the HTTP client
        with patch.object(self.client.client, 'aclose') as mock_aclose:
            # Test close
            await self.client.close()
            mock_aclose.assert_called_once()

    def test_parse_product_item_error_handling(self):
        """Test error handling in _parse_product_item method."""
        # Test with invalid data that causes an exception
        invalid_data = {
            "code": "12345",
            "product_name": "Test Product",
            "nutriments": "invalid_data"  # This should cause an exception
        }

        # Should return None when an exception occurs
        item = self.client._parse_product_item(invalid_data)
        assert item is None

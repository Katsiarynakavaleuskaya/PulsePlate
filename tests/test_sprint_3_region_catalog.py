"""
Tests for Sprint 3: Region Catalog functionality

RU: Тесты для функциональности региональных каталогов
EN: Tests for regional catalog functionality
"""

from pathlib import Path
from unittest.mock import mock_open, patch

from core.region_catalog import (
    RegionalProduct,
    RegionCatalog,
    SearchResult,
    get_available_regions,
    get_price_comparison,
    get_region_catalog,
    search_products,
)


class TestRegionalProduct:
    """Тесты для класса RegionalProduct"""

    def test_regional_product_creation(self):
        """Тест создания регионального продукта"""
        product = RegionalProduct(
            product_id="1",
            name_es="Tomate",
            name_en="Tomato",
            category="vegetables",
            unit="g",
            typical_package_size=500,
            price_eur=1.50,
            price_usd=1.62,
            store_chain="Mercadona",
            region="Valencia",
        )

        assert product.product_id == "1"
        assert product.name_es == "Tomate"
        assert product.name_en == "Tomato"
        assert product.category == "vegetables"
        assert product.unit == "g"
        assert product.typical_package_size == 500
        assert product.price_eur == 1.50
        assert product.price_usd == 1.62
        assert product.store_chain == "Mercadona"
        assert product.region == "Valencia"


class TestSearchResult:
    """Тесты для класса SearchResult"""

    def test_search_result_creation(self):
        """Тест создания результата поиска"""
        products = [RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500)]

        result = SearchResult(products=products, total_count=1, region="es", search_query="tomato")

        assert len(result.products) == 1
        assert result.total_count == 1
        assert result.region == "es"
        assert result.search_query == "tomato"


class TestRegionCatalog:
    """Тесты для класса RegionCatalog"""

    def test_init_with_default_data_dir(self):
        """Тест инициализации с директорией по умолчанию"""
        catalog = RegionCatalog()

        assert catalog.data_dir == Path("data/regions")
        assert isinstance(catalog.regions, dict)

    def test_init_with_custom_data_dir(self):
        """Тест инициализации с пользовательской директорией"""
        catalog = RegionCatalog("custom/regions")

        assert catalog.data_dir == Path("custom/regions")
        assert isinstance(catalog.regions, dict)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictReader")
    def test_load_region_data(self, mock_csv_reader, mock_file, mock_exists):
        """Тест загрузки данных региона"""
        mock_exists.return_value = True

        # Мокаем CSV данные
        mock_csv_reader.return_value = [
            {
                "product_id": "1",
                "name_es": "Tomate",
                "name_en": "Tomato",
                "category": "vegetables",
                "unit": "g",
                "typical_package_size": "500",
                "price_eur": "1.50",
                "price_usd": "",
                "store_chain": "Mercadona",
                "region": "Valencia",
            }
        ]

        catalog = RegionCatalog()
        products = catalog._load_region_data(Path("test.csv"))

        assert len(products) == 1
        assert products[0].product_id == "1"
        assert products[0].name_es == "Tomate"
        assert products[0].price_eur == 1.50
        assert products[0].price_usd is None

    def test_get_available_regions(self):
        """Тест получения доступных регионов"""
        catalog = RegionCatalog()
        catalog.regions = {"es": [], "us": []}

        regions = catalog.get_available_regions()

        assert "es" in regions
        assert "us" in regions
        assert len(regions) == 2

    def test_search_products_existing_region(self):
        """Тест поиска продуктов в существующем регионе"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500),
                RegionalProduct("2", "Lechuga", "Lettuce", "vegetables", "g", 300),
            ]
        }

        result = catalog.search_products("tomato", "es")

        assert result.region == "es"
        assert result.search_query == "tomato"
        assert len(result.products) == 1
        assert result.products[0].name_en == "Tomato"
        assert result.total_count == 1

    def test_search_products_nonexistent_region(self):
        """Тест поиска продуктов в несуществующем регионе"""
        catalog = RegionCatalog()
        catalog.regions = {"es": []}

        result = catalog.search_products("tomato", "nonexistent")

        assert result.region == "nonexistent"
        assert result.search_query == "tomato"
        assert len(result.products) == 0
        assert result.total_count == 0

    def test_search_products_with_category_filter(self):
        """Тест поиска продуктов с фильтром по категории"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500),
                RegionalProduct("2", "Pollo", "Chicken", "meat", "g", 1000),
            ]
        }

        result = catalog.search_products("tomato", "es", category="vegetables")

        assert len(result.products) == 1
        assert result.products[0].category == "vegetables"

    def test_search_products_with_max_results(self):
        """Тест поиска продуктов с ограничением результатов"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500),
                RegionalProduct("2", "Lechuga", "Lettuce", "vegetables", "g", 300),
                RegionalProduct("3", "Pepino", "Cucumber", "vegetables", "g", 400),
            ]
        }

        result = catalog.search_products("vegetables", "es", max_results=2)

        assert len(result.products) == 2
        assert result.total_count == 3

    def test_get_product_by_id_existing(self):
        """Тест получения продукта по ID (существующий)"""
        catalog = RegionCatalog()
        catalog.regions = {"es": [RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500)]}

        product = catalog.get_product_by_id("1", "es")

        assert product is not None
        assert product.product_id == "1"
        assert product.name_es == "Tomate"

    def test_get_product_by_id_nonexistent(self):
        """Тест получения продукта по ID (несуществующий)"""
        catalog = RegionCatalog()
        catalog.regions = {"es": []}

        product = catalog.get_product_by_id("999", "es")

        assert product is None

    def test_get_products_by_category(self):
        """Тест получения продуктов по категории"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500),
                RegionalProduct("2", "Pollo", "Chicken", "meat", "g", 1000),
                RegionalProduct("3", "Lechuga", "Lettuce", "vegetables", "g", 300),
            ]
        }

        vegetables = catalog.get_products_by_category("vegetables", "es")

        assert len(vegetables) == 2
        assert all(p.category == "vegetables" for p in vegetables)

    def test_get_store_chains(self):
        """Тест получения торговых сетей"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct(
                    "1",
                    "Tomate",
                    "Tomato",
                    "vegetables",
                    "g",
                    500,
                    store_chain="Mercadona",
                ),
                RegionalProduct(
                    "2",
                    "Lechuga",
                    "Lettuce",
                    "vegetables",
                    "g",
                    300,
                    store_chain="Carrefour",
                ),
                RegionalProduct(
                    "3", "Pollo", "Chicken", "meat", "g", 1000, store_chain="Mercadona"
                ),
            ]
        }

        chains = catalog.get_store_chains("es")

        assert "Mercadona" in chains
        assert "Carrefour" in chains
        assert len(chains) == 2

    def test_get_categories(self):
        """Тест получения категорий"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500),
                RegionalProduct("2", "Pollo", "Chicken", "meat", "g", 1000),
                RegionalProduct("3", "Leche", "Milk", "dairy", "ml", 1000),
            ]
        }

        categories = catalog.get_categories("es")

        assert "vegetables" in categories
        assert "meat" in categories
        assert "dairy" in categories
        assert len(categories) == 3

    def test_convert_currency(self):
        """Тест конвертации валют"""
        catalog = RegionCatalog()

        # EUR to USD
        usd_amount = catalog.convert_currency(1.0, "EUR", "USD")
        assert usd_amount == 1.08

        # USD to EUR
        eur_amount = catalog.convert_currency(1.0, "USD", "EUR")
        assert eur_amount == 0.93

        # Same currency
        same_amount = catalog.convert_currency(1.0, "EUR", "EUR")
        assert same_amount == 1.0

    def test_get_price_comparison(self):
        """Тест сравнения цен"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500, price_eur=1.50)
            ],
            "us": [RegionalProduct("1", "Tomato", "Tomato", "vegetables", "lb", 1, price_usd=2.50)],
        }

        comparison = catalog.get_price_comparison("tomato", ["es", "us"])

        assert "es" in comparison
        assert "us" in comparison
        assert comparison["es"]["product"] is not None
        assert comparison["us"]["product"] is not None
        assert comparison["es"]["price_eur"] == 1.50
        assert comparison["us"]["price_usd"] == 2.50


class TestConvenienceFunctions:
    """Тесты для удобных функций"""

    @patch("core.region_catalog._region_catalog")
    def test_get_region_catalog(self, mock_catalog):
        """Тест получения глобального каталога"""
        mock_catalog_instance = RegionCatalog()
        mock_catalog.return_value = mock_catalog_instance

        catalog = get_region_catalog()

        assert catalog is not None

    @patch("core.region_catalog.get_region_catalog")
    def test_search_products_function(self, mock_get_catalog):
        """Тест функции поиска продуктов"""
        mock_catalog = RegionCatalog()
        mock_catalog.regions = {
            "es": [RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500)]
        }
        mock_get_catalog.return_value = mock_catalog

        result = search_products("tomato", "es")

        assert result.region == "es"
        assert result.search_query == "tomato"
        assert len(result.products) == 1

    @patch("core.region_catalog.get_region_catalog")
    def test_get_available_regions_function(self, mock_get_catalog):
        """Тест функции получения доступных регионов"""
        mock_catalog = RegionCatalog()
        mock_catalog.regions = {"es": [], "us": []}
        mock_get_catalog.return_value = mock_catalog

        regions = get_available_regions()

        assert "es" in regions
        assert "us" in regions

    @patch("core.region_catalog.get_region_catalog")
    def test_get_price_comparison_function(self, mock_get_catalog):
        """Тест функции сравнения цен"""
        mock_catalog = RegionCatalog()
        mock_catalog.regions = {
            "es": [RegionalProduct("1", "Tomate", "Tomato", "vegetables", "g", 500, price_eur=1.50)]
        }
        mock_get_catalog.return_value = mock_catalog

        comparison = get_price_comparison("tomato", ["es"])

        assert "es" in comparison
        assert comparison["es"]["price_eur"] == 1.50


class TestIntegration:
    """Интеграционные тесты"""

    def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        catalog = RegionCatalog()
        catalog.regions = {
            "es": [
                RegionalProduct(
                    "1",
                    "Tomate",
                    "Tomato",
                    "vegetables",
                    "g",
                    500,
                    price_eur=1.50,
                    store_chain="Mercadona",
                ),
                RegionalProduct(
                    "2",
                    "Lechuga",
                    "Lettuce",
                    "vegetables",
                    "g",
                    300,
                    price_eur=0.80,
                    store_chain="Carrefour",
                ),
            ],
            "us": [
                RegionalProduct(
                    "1",
                    "Tomato",
                    "Tomato",
                    "vegetables",
                    "lb",
                    1,
                    price_usd=2.50,
                    store_chain="Whole Foods",
                )
            ],
        }

        # Поиск продуктов
        es_result = catalog.search_products("tomato", "es")
        us_result = catalog.search_products("tomato", "us")

        assert len(es_result.products) == 1
        assert len(us_result.products) == 1

        # Получение категорий
        es_categories = catalog.get_categories("es")
        us_categories = catalog.get_categories("us")

        assert "vegetables" in es_categories
        assert "vegetables" in us_categories

        # Получение торговых сетей
        es_stores = catalog.get_store_chains("es")
        us_stores = catalog.get_store_chains("us")

        assert "Mercadona" in es_stores
        assert "Whole Foods" in us_stores

        # Сравнение цен
        comparison = catalog.get_price_comparison("tomato", ["es", "us"])

        assert "es" in comparison
        assert "us" in comparison
        assert comparison["es"]["price_eur"] == 1.50
        assert comparison["us"]["price_usd"] == 2.50

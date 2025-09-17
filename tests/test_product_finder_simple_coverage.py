import os

# -*- coding: utf-8 -*-
"""
Simple Product Finder Coverage Tests
Простые тесты для покрытия недостающих строк в core/product_finder.py
"""

from unittest.mock import Mock

from core.product_finder import ProductFinder, ProductSearchResult


class TestProductFinderSimpleCoverage:
    """Простые тесты для покрытия недостающих строк в ProductFinder"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def setup_method(self):
        """Настройка для каждого теста"""
        self.finder = ProductFinder()
        # Мокаем адаптеры
        self.finder.usda_adapter = Mock()
        self.finder.off_adapter = Mock()

    def test_search_product_usda_success_coverage(self):
        """Тест успешного поиска в USDA для покрытия"""
        mock_food = Mock()
        mock_food.name = "apple"
        mock_food.protein_g = 0.3
        mock_food.fat_g = 0.2
        mock_food.carbs_g = 14.0
        mock_food.calories = 52

        self.finder.usda_adapter.normalize.return_value = [mock_food]

        result = self.finder._search_in_usda("apple")

        assert result.found is True
        assert result.source == "USDA"
        assert result.food_record == mock_food
        assert result.confidence > 0.3

    def test_search_product_usda_no_match_coverage(self):
        """Тест поиска в USDA без совпадений для покрытия"""
        self.finder.usda_adapter.normalize.return_value = []

        result = self.finder._search_in_usda("nonexistent")

        assert result.found is False
        assert result.error_message == "USDA search failed"

    def test_search_product_usda_low_confidence_coverage(self):
        """Тест поиска в USDA с низкой уверенностью для покрытия"""
        mock_food = Mock()
        mock_food.name = "completely different"
        mock_food.protein_g = 0.3
        mock_food.fat_g = 0.2
        mock_food.carbs_g = 14.0
        mock_food.calories = 52

        self.finder.usda_adapter.normalize.return_value = [mock_food]

        result = self.finder._search_in_usda("apple")

        assert result.found is False
        assert result.error_message == "USDA search failed"

    def test_search_product_usda_exception_coverage(self):
        """Тест исключения при поиске в USDA для покрытия"""
        self.finder.usda_adapter.normalize.side_effect = Exception("USDA error")

        result = self.finder._search_in_usda("apple")

        assert result.found is False
        assert result.error_message == "USDA search failed"

    def test_search_product_off_success_coverage(self):
        """Тест успешного поиска в Open Food Facts для покрытия"""
        mock_food = Mock()
        mock_food.name = "banana"
        mock_food.protein_g = 1.1
        mock_food.fat_g = 0.3
        mock_food.carbs_g = 23.0
        mock_food.calories = 89

        self.finder.off_adapter.normalize.return_value = [mock_food]

        result = self.finder._search_in_off("banana")

        assert result.found is True
        assert result.source == "OFF"
        assert result.food_record == mock_food
        assert result.confidence > 0.3

    def test_search_product_off_no_match_coverage(self):
        """Тест поиска в OFF без совпадений для покрытия"""
        self.finder.off_adapter.normalize.return_value = []

        result = self.finder._search_in_off("nonexistent")

        assert result.found is False
        assert result.error_message == "OFF search failed"

    def test_search_product_off_low_confidence_coverage(self):
        """Тест поиска в OFF с низкой уверенностью для покрытия"""
        mock_food = Mock()
        mock_food.name = "completely different"
        mock_food.protein_g = 1.1
        mock_food.fat_g = 0.3
        mock_food.carbs_g = 23.0
        mock_food.calories = 89

        self.finder.off_adapter.normalize.return_value = [mock_food]

        result = self.finder._search_in_off("banana")

        assert result.found is False
        assert result.error_message == "OFF search failed"

    def test_search_product_off_exception_coverage(self):
        """Тест исключения при поиске в OFF для покрытия"""
        self.finder.off_adapter.normalize.side_effect = Exception("OFF error")

        result = self.finder._search_in_off("banana")

        assert result.found is False
        assert result.error_message == "OFF search failed"

    def test_calculate_confidence_exact_match_coverage(self):
        """Тест точного совпадения для покрытия"""
        confidence = self.finder._calculate_confidence("apple", "apple")
        assert confidence == 1.0

    def test_calculate_confidence_contains_match_coverage(self):
        """Тест совпадения по содержанию для покрытия"""
        confidence = self.finder._calculate_confidence("apple", "red apple")
        assert confidence == 0.8

    def test_calculate_confidence_reverse_contains_match_coverage(self):
        """Тест обратного совпадения по содержанию для покрытия"""
        confidence = self.finder._calculate_confidence("red apple", "apple")
        assert confidence == 0.8

    def test_calculate_confidence_no_match_coverage(self):
        """Тест отсутствия совпадения для покрытия"""
        confidence = self.finder._calculate_confidence("apple", "banana")
        assert confidence == 0.0

    def test_calculate_confidence_with_spaces_and_underscores_coverage(self):
        """Тест совпадения с пробелами и подчеркиваниями для покрытия"""
        confidence = self.finder._calculate_confidence("red_apple", "red apple")
        assert confidence == 1.0

    def test_search_product_fallback_to_off_coverage(self):
        """Тест fallback на OFF после неудачи USDA для покрытия"""
        # USDA не находит продукт
        self.finder.usda_adapter.normalize.return_value = []

        # OFF находит продукт
        mock_food = Mock()
        mock_food.name = "orange"
        mock_food.protein_g = 0.9
        mock_food.fat_g = 0.1
        mock_food.carbs_g = 12.0
        mock_food.calories = 47

        self.finder.off_adapter.normalize.return_value = [mock_food]

        result = self.finder.search_product("orange")

        assert result.found is True
        assert result.source == "OFF"
        assert result.food_record == mock_food

    def test_search_product_both_sources_fail_coverage(self):
        """Тест когда оба источника не находят продукт для покрытия"""
        self.finder.usda_adapter.normalize.return_value = []
        self.finder.off_adapter.normalize.return_value = []

        result = self.finder.search_product("nonexistent")

        assert result.found is False
        assert result.error_message == "Product not found in any source"

    def test_search_product_usda_exception_fallback_to_off_coverage(self):
        """Тест fallback на OFF после исключения в USDA для покрытия"""
        # USDA выбрасывает исключение
        self.finder.usda_adapter.normalize.side_effect = Exception("USDA error")

        # OFF находит продукт
        mock_food = Mock()
        mock_food.name = "grape"
        mock_food.protein_g = 0.6
        mock_food.fat_g = 0.2
        mock_food.carbs_g = 16.0
        mock_food.calories = 62

        self.finder.off_adapter.normalize.return_value = [mock_food]

        result = self.finder.search_product("grape")

        assert result.found is True
        assert result.source == "OFF"
        assert result.food_record == mock_food

    def test_search_product_off_exception_after_usda_fail_coverage(self):
        """Тест исключения в OFF после неудачи USDA для покрытия"""
        # USDA не находит продукт
        self.finder.usda_adapter.normalize.return_value = []

        # OFF выбрасывает исключение
        self.finder.off_adapter.normalize.side_effect = Exception("OFF error")

        result = self.finder.search_product("nonexistent")

        assert result.found is False
        assert result.error_message == "Product not found in any source"

    def test_search_product_both_sources_exception_coverage(self):
        """Тест исключений в обоих источниках для покрытия"""
        # Оба источника выбрасывают исключения
        self.finder.usda_adapter.normalize.side_effect = Exception("USDA error")
        self.finder.off_adapter.normalize.side_effect = Exception("OFF error")

        result = self.finder.search_product("nonexistent")

        assert result.found is False
        assert result.error_message == "Product not found in any source"

    def test_product_search_result_creation_coverage(self):
        """Тест создания ProductSearchResult для покрытия"""
        result = ProductSearchResult(
            product_name="test",
            found=True,
            source="USDA",
            food_record=Mock(),
            confidence=0.9,
        )

        assert result.product_name == "test"
        assert result.found is True
        assert result.source == "USDA"
        assert result.confidence == 0.9
        assert result.error_message is None

    def test_product_search_result_not_found_coverage(self):
        """Тест создания ProductSearchResult для не найденного продукта для покрытия"""
        result = ProductSearchResult(product_name="test", found=False, error_message="Not found")

        assert result.product_name == "test"
        assert result.found is False
        assert result.error_message == "Not found"
        assert result.source is None
        assert result.food_record is None
        assert result.confidence == 0.0

    def test_search_product_with_special_characters_coverage(self):
        """Тест поиска продукта со специальными символами для покрытия"""
        mock_food = Mock()
        mock_food.name = "test product"
        mock_food.protein_g = 1.0
        mock_food.fat_g = 0.5
        mock_food.carbs_g = 10.0
        mock_food.calories = 50

        self.finder.usda_adapter.normalize.return_value = [mock_food]

        result = self.finder._search_in_usda("test product")

        assert result.found is True
        assert result.source == "USDA"

    def test_search_product_with_unicode_coverage(self):
        """Тест поиска продукта с Unicode для покрытия"""
        mock_food = Mock()
        mock_food.name = "тест"
        mock_food.protein_g = 1.0
        mock_food.fat_g = 0.5
        mock_food.carbs_g = 10.0
        mock_food.calories = 50

        self.finder.usda_adapter.normalize.return_value = [mock_food]

        result = self.finder._search_in_usda("тест")

        assert result.found is True
        assert result.source == "USDA"

    def test_search_product_with_case_sensitivity_coverage(self):
        """Тест поиска продукта с учетом регистра для покрытия"""
        mock_food = Mock()
        mock_food.name = "Apple"
        mock_food.protein_g = 0.3
        mock_food.fat_g = 0.2
        mock_food.carbs_g = 14.0
        mock_food.calories = 52

        self.finder.usda_adapter.normalize.return_value = [mock_food]

        result = self.finder._search_in_usda("apple")

        assert result.found is True
        assert result.source == "USDA"

    def test_search_product_with_multiple_matches_coverage(self):
        """Тест поиска продукта с несколькими совпадениями для покрытия"""
        mock_food1 = Mock()
        mock_food1.name = "apple"
        mock_food1.protein_g = 0.3
        mock_food1.fat_g = 0.2
        mock_food1.carbs_g = 14.0
        mock_food1.calories = 52

        mock_food2 = Mock()
        mock_food2.name = "apple pie"
        mock_food2.protein_g = 2.0
        mock_food2.fat_g = 10.0
        mock_food2.carbs_g = 30.0
        mock_food2.calories = 200

        self.finder.usda_adapter.normalize.return_value = [mock_food1, mock_food2]

        result = self.finder._search_in_usda("apple")

        assert result.found is True
        assert result.source == "USDA"
        # Should select the exact match (mock_food1)
        assert result.food_record == mock_food1

    def test_search_product_with_empty_name_coverage(self):
        """Тест поиска продукта с пустым именем для покрытия"""
        result = self.finder.search_product("")

        assert result.found is False
        assert result.error_message == "Product not found in any source"

    def test_search_product_with_none_name_coverage(self):
        """Тест поиска продукта с None именем для покрытия"""
        result = self.finder.search_product(None)

        assert result.found is False
        assert result.error_message == "Product not found in any source"

    def test_search_product_with_very_long_name_coverage(self):
        """Тест поиска продукта с очень длинным именем для покрытия"""
        long_name = "a" * 1000

        result = self.finder.search_product(long_name)

        assert result.found is False
        assert result.error_message == "Product not found in any source"

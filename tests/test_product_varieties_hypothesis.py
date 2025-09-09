# -*- coding: utf-8 -*-
# flake8: noqa: W503,W504
"""
RU: Hypothesis тесты для системы сортов продуктов.
EN: Hypothesis tests for product varieties system.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from core.product_varieties import ProductVarietiesManager, ProductVariety


class TestProductVarietiesHypothesis:
    """Test product varieties system with Hypothesis."""

    def setup_method(self):
        """Set up test environment."""
        self.manager = ProductVarietiesManager()

    @given(
        product_name=st.sampled_from(
            [
                "Молоко",
                "Сыр",
                "Йогурт",
                "Творог",
                "Хлеб",
                "Макароны",
                "Мясо",
                "Рыба",
                "Овощи",
                "Фрукты",
            ]
        )
    )
    @settings(deadline=None)
    def test_get_varieties_hypothesis(self, product_name: str):
        """Test getting product varieties with Hypothesis."""
        varieties = self.manager.get_varieties(product_name)

        # Проверяем, что возвращается список
        assert isinstance(varieties, list)

        # Если есть сорта, проверяем их структуру
        for variety in varieties:
            assert isinstance(variety, ProductVariety)
            assert variety.name == product_name
            assert isinstance(variety.variety, str)
            assert isinstance(variety.brand, str)
            assert variety.protein_g >= 0
            assert variety.fat_g >= 0
            assert variety.carbs_g >= 0
            assert variety.sugar_g >= 0

    @given(
        product_name=st.sampled_from(["Молоко", "Сыр", "Йогурт", "Творог", "Хлеб"]),
        criteria=st.sampled_from(["balanced", "low_sugar", "high_protein", "low_fat"]),
    )
    @settings(deadline=None)
    def test_get_best_variety_hypothesis(self, product_name: str, criteria: str):
        """Test getting best variety with Hypothesis."""
        best_variety = self.manager.get_best_variety(product_name, criteria)

        if best_variety:
            assert isinstance(best_variety, ProductVariety)
            assert best_variety.name == product_name

            # Проверяем, что выбранный сорт соответствует критериям
            if criteria == "low_sugar":
                varieties = self.manager.get_varieties(product_name)
                if varieties:
                    min_sugar = min(v.sugar_g for v in varieties)
                    assert best_variety.sugar_g == min_sugar
            elif criteria == "high_protein":
                varieties = self.manager.get_varieties(product_name)
                if varieties:
                    max_protein = max(v.protein_g for v in varieties)
                    assert best_variety.protein_g == max_protein

    @given(
        product_name=st.sampled_from(["Молоко", "Сыр", "Йогурт", "Творог"]),
        variety_name=st.text(
            min_size=1,
            max_size=10,
            alphabet=st.characters(
                min_codepoint=ord("а"),
                max_codepoint=ord("я"),
                whitelist_categories=("Lu", "Ll"),
            ),
        ),
    )
    @settings(deadline=None)
    def test_search_varieties_hypothesis(self, product_name: str, variety_name: str):
        """Test searching varieties with Hypothesis."""
        if not variety_name:
            return

        results = self.manager.search_varieties(product_name, variety_name)

        # Проверяем, что возвращается список
        assert isinstance(results, list)

        # Проверяем, что все результаты содержат искомое название сорта
        for variety in results:
            assert variety_name.lower() in variety.variety.lower()

    def test_nutritional_comparison(self):
        """Test nutritional comparison functionality."""
        # Тестируем с продуктом, который должен быть в базе
        comparison = self.manager.get_nutritional_comparison("Молоко")

        if comparison:
            # Проверяем структуру сравнения
            assert isinstance(comparison, dict)
            assert len(comparison) > 0

            for variety_name, nutrition in comparison.items():
                assert isinstance(variety_name, str)
                assert isinstance(nutrition, dict)
                assert "calories" in nutrition
                assert "protein" in nutrition
                assert "fat" in nutrition
                assert "carbs" in nutrition
                assert "sugar" in nutrition

                # Проверяем, что значения неотрицательные
                assert nutrition["calories"] >= 0
                assert nutrition["protein"] >= 0
                assert nutrition["fat"] >= 0
                assert nutrition["carbs"] >= 0
                assert nutrition["sugar"] >= 0

    @given(
        product_name=st.sampled_from(["Молоко", "Сыр", "Йогурт", "Творог"]),
        low_sugar=st.booleans(),
        low_fat=st.booleans(),
        high_protein=st.booleans(),
        vegetarian=st.booleans(),
        gluten_free=st.booleans(),
    )
    @settings(deadline=None)
    def test_recommend_variety_hypothesis(
        self,
        product_name: str,
        low_sugar: bool,
        low_fat: bool,
        high_protein: bool,
        vegetarian: bool,
        gluten_free: bool,
    ):
        """Test variety recommendation with Hypothesis."""
        preferences = {
            "low_sugar": low_sugar,
            "low_fat": low_fat,
            "high_protein": high_protein,
            "vegetarian": vegetarian,
            "gluten_free": gluten_free,
        }

        recommended = self.manager.recommend_variety(product_name, preferences)

        if recommended:
            assert isinstance(recommended, ProductVariety)
            assert recommended.name == product_name

            # Проверяем, что рекомендация соответствует предпочтениям
            # (если есть подходящие варианты)
            # Система может вернуть лучший доступный вариант, если точного соответствия нет
            if low_sugar:
                # Проверяем, что если есть низкосахарные варианты,
                # то выбран один из них
                low_sugar_varieties = [
                    v
                    for v in self.manager.get_varieties(product_name)
                    if v.is_low_sugar()
                ]
                if low_sugar_varieties:
                    assert recommended.is_low_sugar()

            if low_fat:
                low_fat_varieties = [
                    v
                    for v in self.manager.get_varieties(product_name)
                    if v.is_low_fat()
                ]
                if low_fat_varieties:
                    assert recommended.is_low_fat()

            if high_protein:
                high_protein_varieties = [
                    v
                    for v in self.manager.get_varieties(product_name)
                    if v.is_high_protein()
                ]
                if high_protein_varieties:
                    assert recommended.is_high_protein()

            if vegetarian:
                veg_varieties = [
                    v
                    for v in self.manager.get_varieties(product_name)
                    if "VEG" in v.flags
                ]
                if veg_varieties:
                    assert "VEG" in recommended.flags

            if gluten_free:
                gf_varieties = [
                    v
                    for v in self.manager.get_varieties(product_name)
                    if "GF" in v.flags
                ]
                if gf_varieties:
                    assert "GF" in recommended.flags

    def test_product_variety_methods(self):
        """Test ProductVariety class methods."""
        # Создаем тестовый сорт продукта
        variety = ProductVariety(
            name="Тестовый продукт",
            variety="тестовый сорт",
            brand="тестовая марка",
            protein_g=20.0,
            fat_g=5.0,
            carbs_g=10.0,
            fiber_g=2.0,
            sugar_g=3.0,
            Fe_mg=1.0,
            Ca_mg=100.0,
            VitD_IU=50.0,
            B12_ug=1.0,
            Folate_ug=50.0,
            Iodine_ug=10.0,
            K_mg=200.0,
            Mg_mg=30.0,
            flags={"GF", "VEG"},
            notes="тестовый продукт",
        )

        # Тестируем методы
        assert variety.get_calories() == (20.0 * 4) + (10.0 * 4) + (
            5.0 * 9
        )  # 80 + 40 + 45 = 165
        assert variety.get_sugar_content() == 3.0
        assert variety.is_low_sugar()  # 3.0 <= 5.0
        assert variety.is_high_protein()  # 20.0 >= 20.0
        assert not variety.is_low_fat()  # 5.0 > 3.0

        # Тестируем конвертацию в FoodItem
        food_item = variety.to_food_item()
        assert food_item.name == "Тестовый продукт (тестовый сорт)"
        assert food_item.protein_g == 20.0
        assert food_item.fat_g == 5.0
        assert food_item.carbs_g == 10.0

    def test_manager_statistics(self):
        """Test manager statistics."""
        stats = self.manager.get_statistics()

        assert isinstance(stats, dict)
        assert "total_products" in stats
        assert "total_varieties" in stats
        assert "avg_varieties_per_product" in stats

        assert stats["total_products"] >= 0
        assert stats["total_varieties"] >= 0
        assert stats["avg_varieties_per_product"] >= 0

    def test_get_all_products(self):
        """Test getting all products."""
        products = self.manager.get_all_products()

        assert isinstance(products, list)
        assert len(products) > 0

        # Проверяем, что все элементы - строки
        for product in products:
            assert isinstance(product, str)
            assert len(product) > 0

    def test_variety_validation(self):
        """Test variety data validation."""
        # Получаем все продукты и проверяем их сорта
        all_products = self.manager.get_all_products()

        for product_name in all_products[:5]:  # Проверяем первые 5 продуктов
            varieties = self.manager.get_varieties(product_name)

            for variety in varieties:
                # Проверяем, что все числовые значения неотрицательные
                assert variety.protein_g >= 0
                assert variety.fat_g >= 0
                assert variety.carbs_g >= 0
                assert variety.fiber_g >= 0
                assert variety.sugar_g >= 0
                assert variety.Fe_mg >= 0
                assert variety.Ca_mg >= 0
                assert variety.VitD_IU >= 0
                assert variety.B12_ug >= 0
                assert variety.Folate_ug >= 0
                assert variety.Iodine_ug >= 0
                assert variety.K_mg >= 0
                assert variety.Mg_mg >= 0

                # Проверяем, что строковые поля не пустые
                assert variety.name
                assert variety.variety
                assert variety.brand
                assert isinstance(variety.flags, set)
                assert isinstance(variety.notes, str)

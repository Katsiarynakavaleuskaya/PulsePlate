import os

import pytest


"""
Тесты для модуля core/units.py
Покрытие конвертации единиц измерения для витаминов и микроэлементов
"""

from core.units import iu_vitd_from_ug, mg_from_g, mg_from_ug


class TestUnitsConversion:
    """Тесты конвертации единиц измерения"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_iu_vitd_from_ug_standard_values(self):
        """Тест конвертации витамина D µg → IU стандартные значения"""
        # 1 µg = 40 IU стандартная конвертация
        assert iu_vitd_from_ug(1.0) == pytest.approx(40.0)
        assert iu_vitd_from_ug(2.5) == pytest.approx(100.0)
        assert iu_vitd_from_ug(10.0) == pytest.approx(400.0)
        assert iu_vitd_from_ug(25.0) == pytest.approx(1000.0)

    def test_iu_vitd_from_ug_edge_cases(self):
        """Тест edge cases витамина D конвертации"""
        assert iu_vitd_from_ug(0.0) == pytest.approx(0.0)
        assert iu_vitd_from_ug(0.125) == pytest.approx(5.0)  # очень малые дозы
        assert iu_vitd_from_ug(100.0) == pytest.approx(4000.0)  # высокие дозы

    def test_iu_vitd_from_ug_negative_input(self):
        """Тест обработки отрицательных значений"""
        # Функция должна работать с отрицательными числами (хотя биологически бессмысленно)
        assert iu_vitd_from_ug(-5.0) == pytest.approx(-200.0)

    def test_mg_from_ug_standard_conversions(self):
        """Тест конвертации µg → mg"""
        assert mg_from_ug(1000.0) == pytest.approx(1.0)
        assert mg_from_ug(500.0) == pytest.approx(0.5)
        assert mg_from_ug(100.0) == pytest.approx(0.1)
        assert mg_from_ug(1.0) == pytest.approx(0.001)

    def test_mg_from_ug_precision(self):
        """Тест точности конвертации µg → mg"""
        assert mg_from_ug(2500.0) == pytest.approx(2.5)
        assert mg_from_ug(750.0) == pytest.approx(0.75)
        assert mg_from_ug(1) == pytest.approx(0.001)

    def test_mg_from_ug_edge_cases(self):
        """Тест edge cases µg → mg"""
        assert mg_from_ug(0.0) == pytest.approx(0.0)
        assert mg_from_ug(10000.0) == pytest.approx(10.0)  # большие значения

    def test_mg_from_g_standard_conversions(self):
        """Тест конвертации г → мг"""
        assert mg_from_g(1.0) == pytest.approx(1000.0)
        assert mg_from_g(0.5) == pytest.approx(500.0)
        assert mg_from_g(0.1) == pytest.approx(100.0)
        assert mg_from_g(2.5) == pytest.approx(2500.0)

    def test_mg_from_g_precision(self):
        """Тест точности конвертации г → мг"""
        assert mg_from_g(0.025) == pytest.approx(25.0)
        assert mg_from_g(1.5) == pytest.approx(1500.0)
        assert mg_from_g(0.001) == pytest.approx(1.0)

    def test_mg_from_g_edge_cases(self):
        """Тест edge cases г → мг"""
        assert mg_from_g(0.0) == pytest.approx(0.0)
        assert mg_from_g(10.0) == pytest.approx(10000.0)  # большие значения

    def test_all_functions_with_float_types(self):
        """Тест что все функции принимают и возвращают float"""
        # Проверяем что функции правильно конвертируют типы
        assert isinstance(iu_vitd_from_ug(5), float)
        assert isinstance(mg_from_ug(1000), float)
        assert isinstance(mg_from_g(1), float)

    def test_realistic_nutrition_scenarios(self):
        """Тест реалистических сценариев питания"""
        # Витамин D: типичная дневная доза 15 µg = 600 IU
        assert iu_vitd_from_ug(15.0) == pytest.approx(600.0)

        # B12: типичная доза 2.4 µg = 0.0024 mg
        assert mg_from_ug(2.4) == pytest.approx(0.0024)

        # Кальций: типичная доза 1.2 г = 1200 мг
        assert mg_from_g(1.2) == pytest.approx(1200.0)

    def test_chain_conversions(self):
        """Тест цепочки конвертаций"""
        # Можем ли мы делать последовательные конвертации
        original_g = 0.005  # 5 мг в граммах
        mg_value = mg_from_g(original_g)  # должно быть 5.0 мг
        assert mg_value == pytest.approx(5.0)

        # Обратная конвертация через деление
        back_to_g = mg_value / 1000.0
        assert back_to_g == pytest.approx(original_g)

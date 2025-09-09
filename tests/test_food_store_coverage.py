# -*- coding: utf-8 -*-
"""
Тесты для покрытия недостающих строк в app/services/food_store.py
"""
from unittest.mock import MagicMock, patch

from app.services.food_store import expand_query, get_food, nutrients_for, search_foods


class TestFoodStoreCoverage:
    """Тесты для покрытия недостающих строк в food_store.py"""

    def test_expand_query_empty_string(self):
        """Тест expand_query с пустой строкой"""
        result = expand_query("")
        assert result == []

    def test_expand_query_none(self):
        """Тест expand_query с None"""
        result = expand_query(None)
        assert result == []

    def test_expand_query_whitespace(self):
        """Тест expand_query с пробелами"""
        result = expand_query("   ")
        assert result == []

    def test_expand_query_known_alias(self):
        """Тест expand_query с известным алиасом"""
        result = expand_query("йогурт")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

    def test_expand_query_english_alias(self):
        """Тест expand_query с английским алиасом"""
        result = expand_query("yogurt")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

    def test_expand_query_unknown_term(self):
        """Тест expand_query с неизвестным термином"""
        result = expand_query("unknown_food")
        assert result == ["unknown_food"]

    @patch("app.services.food_store._connect")
    def test_search_foods_empty_query(self, mock_connect):
        """Тест search_foods с пустым запросом"""
        mock_con = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_con
        mock_con.execute.return_value.fetchall.return_value = [
            {"id": "1", "canonical_name": "test", "kcal": 100}
        ]

        result = search_foods("")
        assert len(result) == 1
        mock_con.execute.assert_called_once()

    @patch("app.services.food_store._connect")
    def test_search_foods_none_query(self, mock_connect):
        """Тест search_foods с None запросом"""
        mock_con = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_con
        mock_con.execute.return_value.fetchall.return_value = [
            {"id": "1", "canonical_name": "test", "kcal": 100}
        ]

        result = search_foods(None)
        assert len(result) == 1
        mock_con.execute.assert_called_once()

    @patch("app.services.food_store._connect")
    def test_search_foods_with_terms(self, mock_connect):
        """Тест search_foods с терминами"""
        mock_con = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_con
        mock_con.execute.return_value.fetchall.return_value = [
            {"id": "1", "canonical_name": "yogurt", "kcal": 100}
        ]

        result = search_foods("йогурт")
        assert len(result) == 1
        # Проверяем, что SQL содержит OR условия для алиасов
        call_args = mock_con.execute.call_args
        assert "OR" in call_args[0][0]

    @patch("app.services.food_store._connect")
    def test_get_food_not_found(self, mock_connect):
        """Тест get_food когда еда не найдена"""
        mock_con = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_con
        mock_con.execute.return_value.fetchone.return_value = None

        result = get_food("nonexistent_id")
        assert result is None

    @patch("app.services.food_store._connect")
    def test_get_food_found(self, mock_connect):
        """Тест get_food когда еда найдена"""
        mock_con = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_con
        mock_row = {"id": "1", "canonical_name": "test", "kcal": 100}
        mock_con.execute.return_value.fetchone.return_value = mock_row

        result = get_food("1")
        assert result == mock_row

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_missing_food(self, mock_get_food):
        """Тест nutrients_for с отсутствующей едой"""
        mock_get_food.return_value = None

        ingredients = [{"food_id": "missing", "grams": 100}]
        result = nutrients_for(ingredients)

        # Все значения должны быть 0.0
        for value in result.values():
            assert value == 0.0

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_with_per_g_override(self, mock_get_food):
        """Тест nutrients_for с переопределением per_g"""
        mock_food = {
            "kcal": 100,
            "protein_g": 10,
            "fat_g": 5,
            "carbs_g": 15,
            "Fe_mg": 1,
            "Ca_mg": 50,
            "K_mg": 200,
            "Mg_mg": 20,
            "VitD_IU": 10,
            "B12_ug": 1,
            "Folate_ug": 5,
            "Iodine_ug": 2,
            "per_g": 50,  # Переопределяем стандартное значение 100
        }
        mock_get_food.return_value = mock_food

        ingredients = [{"food_id": "1", "grams": 100}]
        result = nutrients_for(ingredients)

        # Проверяем, что расчеты учитывают per_g = 50
        assert result["kcal"] == 200.0  # 100 * (100/50)
        assert result["protein_g"] == 20.0  # 10 * (100/50)

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_missing_nutrients(self, mock_get_food):
        """Тест nutrients_for с отсутствующими нутриентами"""
        mock_food = {
            "kcal": 100,
            "protein_g": 10,
            # Остальные нутриенты отсутствуют
        }
        mock_get_food.return_value = mock_food

        ingredients = [{"food_id": "1", "grams": 100}]
        result = nutrients_for(ingredients)

        # Проверяем, что отсутствующие нутриенты обрабатываются как 0.0
        assert result["kcal"] == 100.0
        assert result["protein_g"] == 10.0
        assert result["fat_g"] == 0.0
        assert result["Fe_mg"] == 0.0

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_multiple_ingredients(self, mock_get_food):
        """Тест nutrients_for с несколькими ингредиентами"""

        def mock_get_food_side_effect(food_id):
            if food_id == "1":
                return {
                    "kcal": 100,
                    "protein_g": 10,
                    "fat_g": 5,
                    "carbs_g": 15,
                    "Fe_mg": 1,
                    "Ca_mg": 50,
                    "K_mg": 200,
                    "Mg_mg": 20,
                    "VitD_IU": 10,
                    "B12_ug": 1,
                    "Folate_ug": 5,
                    "Iodine_ug": 2,
                }
            elif food_id == "2":
                return {
                    "kcal": 200,
                    "protein_g": 20,
                    "fat_g": 10,
                    "carbs_g": 30,
                    "Fe_mg": 2,
                    "Ca_mg": 100,
                    "K_mg": 400,
                    "Mg_mg": 40,
                    "VitD_IU": 20,
                    "B12_ug": 2,
                    "Folate_ug": 10,
                    "Iodine_ug": 4,
                }
            return None

        mock_get_food.side_effect = mock_get_food_side_effect

        ingredients = [{"food_id": "1", "grams": 100}, {"food_id": "2", "grams": 50}]
        result = nutrients_for(ingredients)

        # Проверяем, что нутриенты суммируются
        assert result["kcal"] == 200.0  # 100 + 200*0.5
        assert result["protein_g"] == 20.0  # 10 + 20*0.5

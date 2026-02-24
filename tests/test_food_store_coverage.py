# -*- coding: utf-8 -*-
"""
Тесты для покрытия недостающих строк в app/services/food_store.py

RU: Тесты используют monkeypatch вместо @patch для совместимости с Python 3.12+
EN: Tests use monkeypatch instead of @patch for Python 3.12+ compatibility
"""

from typing import Any, Dict, List, Optional
from types import TracebackType

import pytest

from app.services import food_store
from app.services.food_store import expand_query, nutrients_for


class _MockCursor:
    """Mock cursor for database operations."""

    def __init__(
        self,
        fetchall_result: Optional[List[Dict[str, Any]]] = None,
        fetchone_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._fetchall_result = fetchall_result or []
        self._fetchone_result = fetchone_result

    def fetchall(self) -> List[Dict[str, Any]]:
        return self._fetchall_result

    def fetchone(self) -> Optional[Dict[str, Any]]:
        return self._fetchone_result


class _MockConnection:
    """Mock connection that tracks execute calls."""

    def __init__(
        self,
        fetchall_result: Optional[List[Dict[str, Any]]] = None,
        fetchone_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._fetchall_result = fetchall_result
        self._fetchone_result = fetchone_result
        self.execute_calls: List[tuple[str, Any]] = []

    def execute(self, sql: str, params: Any = None) -> _MockCursor:
        self.execute_calls.append((sql, params))
        return _MockCursor(self._fetchall_result, self._fetchone_result)

    def __enter__(self) -> "_MockConnection":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return None


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set test environment variables using monkeypatch for proper isolation."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")


class TestFoodStoreCoverage:
    """Тесты для покрытия недостающих строк в food_store.py"""

    def test_expand_query_empty_string(self) -> None:
        """Тест expand_query с пустой строкой"""
        result = expand_query("")
        assert result == []

    def test_expand_query_none(self) -> None:
        """Тест expand_query с None"""
        result = expand_query(None)  # type: ignore[arg-type]
        assert result == []

    def test_expand_query_whitespace(self) -> None:
        """Тест expand_query с пробелами"""
        result = expand_query("   ")
        assert result == []

    def test_expand_query_known_alias(self) -> None:
        """Тест expand_query с известным алиасом"""
        result = expand_query("йогурт")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

    def test_expand_query_english_alias(self) -> None:
        """Тест expand_query с английским алиасом"""
        result = expand_query("yogurt")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

    def test_expand_query_unknown_term(self) -> None:
        """Тест expand_query с неизвестным термином"""
        result = expand_query("unknown_food")
        assert result == ["unknown_food"]

    def test_search_foods_empty_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест search_foods с пустым запросом"""
        conn = _MockConnection(fetchall_result=[{"id": "1", "canonical_name": "test", "kcal": 100}])
        monkeypatch.setattr(food_store, "_connect", lambda: conn)

        result = food_store.search_foods("")
        assert len(result) == 1
        assert len(conn.execute_calls) == 1

    def test_search_foods_none_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест search_foods с None запросом"""
        conn = _MockConnection(fetchall_result=[{"id": "1", "canonical_name": "test", "kcal": 100}])
        monkeypatch.setattr(food_store, "_connect", lambda: conn)

        result = food_store.search_foods(None)  # type: ignore[arg-type]
        assert len(result) == 1
        assert len(conn.execute_calls) == 1

    def test_search_foods_with_terms(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест search_foods с терминами"""
        conn = _MockConnection(
            fetchall_result=[{"id": "1", "canonical_name": "yogurt", "kcal": 100}]
        )
        monkeypatch.setattr(food_store, "_connect", lambda: conn)

        result = food_store.search_foods("йогурт")
        assert len(result) == 1
        # Проверяем, что SQL содержит OR условия для алиасов
        sql = conn.execute_calls[0][0]
        assert "OR" in sql

    def test_get_food_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест get_food когда еда не найдена"""
        conn = _MockConnection(fetchone_result=None)
        monkeypatch.setattr(food_store, "_connect", lambda: conn)

        result = food_store.get_food("nonexistent_id")
        assert result is None

    def test_get_food_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест get_food когда еда найдена"""
        mock_row = {"id": "1", "canonical_name": "test", "kcal": 100}
        conn = _MockConnection(fetchone_result=mock_row)
        monkeypatch.setattr(food_store, "_connect", lambda: conn)

        result = food_store.get_food("1")
        assert result == mock_row

    def test_nutrients_for_missing_food(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест nutrients_for с отсутствующей едой"""
        monkeypatch.setattr(food_store, "get_food", lambda food_id: None)

        ingredients = [{"food_id": "missing", "grams": 100}]
        result = nutrients_for(ingredients)

        # Все значения должны быть 0.0
        for value in result.values():
            assert value == 0.0

    def test_nutrients_for_with_per_g_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
        monkeypatch.setattr(food_store, "get_food", lambda food_id: mock_food)

        ingredients = [{"food_id": "1", "grams": 100}]
        result = nutrients_for(ingredients)

        # Проверяем, что расчеты учитывают per_g = 50
        assert result["kcal"] == 200.0  # 100 * (100/50)
        assert result["protein_g"] == 20.0  # 10 * (100/50)

    def test_nutrients_for_missing_nutrients(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест nutrients_for с отсутствующими нутриентами"""
        mock_food = {
            "kcal": 100,
            "protein_g": 10,
            # Остальные нутриенты отсутствуют
        }
        monkeypatch.setattr(food_store, "get_food", lambda food_id: mock_food)

        ingredients = [{"food_id": "1", "grams": 100}]
        result = nutrients_for(ingredients)

        # Проверяем, что отсутствующие нутриенты обрабатываются как 0.0
        assert result["kcal"] == 100.0
        assert result["protein_g"] == 10.0
        assert result["fat_g"] == 0.0
        assert result["Fe_mg"] == 0.0

    def test_nutrients_for_multiple_ingredients(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест nutrients_for с несколькими ингредиентами"""

        def mock_get_food(food_id: str) -> Optional[Dict[str, Any]]:
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

        monkeypatch.setattr(food_store, "get_food", mock_get_food)

        ingredients = [{"food_id": "1", "grams": 100}, {"food_id": "2", "grams": 50}]
        result = nutrients_for(ingredients)

        # Проверяем, что нутриенты суммируются
        assert result["kcal"] == 200.0  # 100 + 200*0.5
        assert result["protein_g"] == 20.0  # 10 + 20*0.5

    def test_search_foods_with_terms_sql_construction(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Тест search_foods с терминами - проверка SQL конструкции (строки 41, 50)"""
        conn = _MockConnection(fetchall_result=[])
        monkeypatch.setattr(food_store, "_connect", lambda: conn)

        # Тест с терминами - должен использовать FTS
        food_store.search_foods("apple banana", limit=10, offset=5)

        # Проверяем, что SQL содержит JOIN и MATCH
        sql, params = conn.execute_calls[0]
        assert "JOIN foods_fts" in sql
        assert "MATCH ?" in sql
        assert "LIMIT ? OFFSET ?" in sql

        # Проверяем параметры
        assert params[-2] == 10  # limit
        assert params[-1] == 5  # offset

    def test_search_foods_without_terms_sql_construction(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Тест search_foods без терминов - проверка SQL конструкции (строка 50)"""
        conn = _MockConnection(fetchall_result=[])
        monkeypatch.setattr(food_store, "_connect", lambda: conn)

        # Тест без терминов - должен использовать простой SELECT
        food_store.search_foods("", limit=15, offset=10)

        # Проверяем, что SQL не содержит JOIN
        sql, params = conn.execute_calls[0]
        assert "JOIN" not in sql
        assert "MATCH" not in sql
        assert "LIMIT ? OFFSET ?" in sql

        # Проверяем параметры
        assert params == [15, 10]  # limit, offset

    def test_nutrients_for_food_not_found_continue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест nutrients_for когда get_food возвращает None - строка 89-91"""

        def mock_get_food(food_id: str) -> Optional[Dict[str, Any]]:
            if food_id == "missing":
                return None  # Это должно вызвать continue
            return {
                "per_g": 100.0,
                "kcal": 100,
                "protein_g": 10,
                "fat_g": 5,
                "carbs_g": 15,
                "Fe_mg": 1,
                "Ca_mg": 50,
                "K_mg": 200,
                "Mg_mg": 30,
                "VitD_IU": 10,
                "B12_ug": 0.5,
                "Folate_ug": 20,
                "Iodine_ug": 15,
            }

        monkeypatch.setattr(food_store, "get_food", mock_get_food)

        ingredients = [
            {"food_id": "missing", "grams": 100},  # Это должно быть пропущено
            {"food_id": "found", "grams": 100},  # Это должно быть обработано
        ]
        result = nutrients_for(ingredients)

        # Проверяем, что только найденная еда учтена
        assert result["kcal"] == 100.0
        assert result["protein_g"] == 10.0

    def test_nutrients_for_per_g_calculation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест nutrients_for с расчетом per_g - строка 90"""
        mock_food = {
            "per_g": 50.0,  # Не стандартные 100г
            "kcal": 200,
            "protein_g": 20,
            "fat_g": 10,
            "carbs_g": 30,
            "Fe_mg": 2,
            "Ca_mg": 100,
            "K_mg": 400,
            "Mg_mg": 60,
            "VitD_IU": 20,
            "B12_ug": 1,
            "Folate_ug": 40,
            "Iodine_ug": 30,
        }
        monkeypatch.setattr(food_store, "get_food", lambda food_id: mock_food)

        ingredients = [{"food_id": "test", "grams": 100}]  # 100г при per_g=50 означает ratio=2
        result = nutrients_for(ingredients)

        # Проверяем, что ratio = grams / per_g = 100 / 50 = 2
        assert result["kcal"] == 400.0  # 200 * 2
        assert result["protein_g"] == 40.0  # 20 * 2

    def test_nutrients_for_missing_nutrient_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест nutrients_for с отсутствующими ключами нутриентов - строка 91"""
        mock_food = {
            "per_g": 100.0,
            "kcal": 100,
            "protein_g": 10,
            # Отсутствуют некоторые нутриенты
            "Fe_mg": 1,
            # Ca_mg отсутствует
            "K_mg": 200,
            # Mg_mg отсутствует
        }
        monkeypatch.setattr(food_store, "get_food", lambda food_id: mock_food)

        ingredients = [{"food_id": "test", "grams": 100}]
        result = nutrients_for(ingredients)

        # Проверяем, что отсутствующие нутриенты имеют значение 0.0
        assert result["Ca_mg"] == 0.0
        assert result["Mg_mg"] == 0.0
        # А присутствующие нутриенты должны быть учтены
        assert result["Fe_mg"] == 1.0

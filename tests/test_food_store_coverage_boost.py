# -*- coding: utf-8 -*-
"""
RU: Тесты для повышения покрытия app/services/food_store.py
EN: Coverage boost tests for app/services/food_store.py

RU: Тесты используют monkeypatch вместо @patch для совместимости с Python 3.12+
EN: Tests use monkeypatch instead of @patch for Python 3.12+ compatibility
"""

from types import TracebackType
from typing import Any, Callable, Dict, List, Optional

import pytest

try:
    from app.services import food_store
except ImportError as exc:
    pytest.skip(f"Import failed: {exc}", allow_module_level=True)


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
    ) -> bool | None:
        return False


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set test environment variables using monkeypatch for proper isolation."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")


class TestFoodStoreCoverage:
    """Test class for food_store coverage boost."""

    def test_expand_query_empty_string(self) -> None:
        """Test expand_query with empty string."""
        result = food_store.expand_query("")
        assert result == []

    def test_expand_query_none(self) -> None:
        """Test expand_query with None."""
        # Intentional: testing None handling, not type conversion
        result = food_store.expand_query(None)  # type: ignore[arg-type]
        assert result == []

    def test_expand_query_whitespace(self) -> None:
        """Test expand_query with whitespace only."""
        result = food_store.expand_query("   ")
        assert result == []

    def test_expand_query_basic_term(self) -> None:
        """Test expand_query with basic term."""
        result = food_store.expand_query("yogurt")
        assert "yogurt" in result

    def test_expand_query_with_aliases(self) -> None:
        """Test expand_query with aliases."""
        result = food_store.expand_query("йогурт")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

    def test_expand_query_alias_variant(self) -> None:
        """Test expand_query with alias variant."""
        result = food_store.expand_query("yoghurt")
        assert "yoghurt" in result
        assert "йогурт" in result
        assert "yogurt" in result

    def test_expand_query_olive_oil(self) -> None:
        """Test expand_query with olive oil."""
        result = food_store.expand_query("масло оливковое")
        assert "масло оливковое" in result
        assert "olive oil" in result
        assert "aceite de oliva" in result

    def test_expand_query_cottage_cheese(self) -> None:
        """Test expand_query with cottage cheese."""
        result = food_store.expand_query("творог")
        assert "творог" in result
        assert "cottage cheese" in result
        assert "queso cottage" in result

    def test_search_foods_with_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search_foods with query."""
        mock_con = _MockConnection(
            fetchall_result=[
                {
                    "id": "1",
                    "canonical_name": "apple",
                    "kcal": 52,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbs_g": 14.0,
                }
            ],
        )
        monkeypatch.setattr(food_store, "_connect", lambda: mock_con)

        result = food_store.search_foods("apple", limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["canonical_name"] == "apple"
        assert len(mock_con.execute_calls) == 1

    def test_search_foods_without_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search_foods without query."""
        mock_con = _MockConnection(
            fetchall_result=[
                {
                    "id": "1",
                    "canonical_name": "apple",
                    "kcal": 52,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbs_g": 14.0,
                }
            ],
        )
        monkeypatch.setattr(food_store, "_connect", lambda: mock_con)

        result = food_store.search_foods("", limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["canonical_name"] == "apple"
        assert len(mock_con.execute_calls) == 1

    def test_search_foods_none_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search_foods with None query."""
        mock_con = _MockConnection(fetchall_result=[])
        monkeypatch.setattr(food_store, "_connect", lambda: mock_con)

        # Intentional: testing None handling, not type conversion
        result = food_store.search_foods(None, limit=10, offset=0)  # type: ignore[arg-type]

        assert result == []
        assert len(mock_con.execute_calls) == 1

    def test_get_food_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_food when food is found."""
        mock_con = _MockConnection(
            fetchone_result={
                "id": "1",
                "canonical_name": "apple",
                "kcal": 52,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
                "per_g": 100.0,
            },
        )
        monkeypatch.setattr(food_store, "_connect", lambda: mock_con)

        result = food_store.get_food("1")

        assert result is not None
        assert result["canonical_name"] == "apple"
        assert result["kcal"] == 52

    def test_get_food_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_food when food is not found."""
        mock_con = _MockConnection(fetchone_result=None)
        monkeypatch.setattr(food_store, "_connect", lambda: mock_con)

        result = food_store.get_food("999")

        assert result is None

    def test_nutrients_for_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test nutrients_for with empty ingredients list."""
        monkeypatch.setattr(food_store, "get_food", lambda food_id: None)

        result = food_store.nutrients_for([])

        expected_keys = [
            "kcal",
            "protein_g",
            "fat_g",
            "carbs_g",
            "Fe_mg",
            "Ca_mg",
            "K_mg",
            "Mg_mg",
            "VitD_IU",
            "B12_ug",
            "Folate_ug",
            "Iodine_ug",
        ]

        for key in expected_keys:
            assert result[key] == 0.0

    def test_nutrients_for_single_ingredient(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test nutrients_for with single ingredient."""
        mock_food: Dict[str, Any] = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "Fe_mg": 0.1,
            "Ca_mg": 6.0,
            "K_mg": 107.0,
            "Mg_mg": 5.0,
            "VitD_IU": 0,
            "B12_ug": 0,
            "Folate_ug": 3.0,
            "Iodine_ug": 0,
            "per_g": 100.0,
        }
        monkeypatch.setattr(food_store, "get_food", lambda food_id: mock_food)

        ingredients = [{"food_id": "1", "grams": 200.0}]
        result = food_store.nutrients_for(ingredients)

        # 200g of apple (per 100g) = 2x the values
        assert result["kcal"] == 104.0  # 52 * 2
        assert result["protein_g"] == 0.6  # 0.3 * 2
        assert result["fat_g"] == 0.4  # 0.2 * 2
        assert result["carbs_g"] == 28.0  # 14.0 * 2

    def test_nutrients_for_multiple_ingredients(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test nutrients_for with multiple ingredients."""

        def mock_get_food_side_effect(food_id: str) -> Optional[Dict[str, Any]]:
            if food_id == "1":
                return {
                    "id": "1",
                    "canonical_name": "apple",
                    "kcal": 52,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbs_g": 14.0,
                    "Fe_mg": 0.1,
                    "Ca_mg": 6.0,
                    "K_mg": 107.0,
                    "Mg_mg": 5.0,
                    "VitD_IU": 0,
                    "B12_ug": 0,
                    "Folate_ug": 3.0,
                    "Iodine_ug": 0,
                    "per_g": 100.0,
                }
            elif food_id == "2":
                return {
                    "id": "2",
                    "canonical_name": "banana",
                    "kcal": 89,
                    "protein_g": 1.1,
                    "fat_g": 0.3,
                    "carbs_g": 23.0,
                    "Fe_mg": 0.3,
                    "Ca_mg": 5.0,
                    "K_mg": 358.0,
                    "Mg_mg": 27.0,
                    "VitD_IU": 0,
                    "B12_ug": 0,
                    "Folate_ug": 20.0,
                    "Iodine_ug": 0,
                    "per_g": 100.0,
                }
            return None

        monkeypatch.setattr(food_store, "get_food", mock_get_food_side_effect)

        ingredients = [
            {"food_id": "1", "grams": 100.0},  # 100g apple
            {"food_id": "2", "grams": 150.0},  # 150g banana
        ]
        result = food_store.nutrients_for(ingredients)

        # Apple: 100g = 1x values
        # Banana: 150g = 1.5x values
        assert result["kcal"] == 52 + (89 * 1.5)  # 52 + 133.5 = 185.5
        assert result["protein_g"] == 0.3 + (1.1 * 1.5)  # 0.3 + 1.65 = 1.95
        assert result["fat_g"] == 0.2 + (0.3 * 1.5)  # 0.2 + 0.45 = 0.65

    def test_nutrients_for_missing_food(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test nutrients_for with missing food."""
        monkeypatch.setattr(food_store, "get_food", lambda food_id: None)

        ingredients = [{"food_id": "999", "grams": 100.0}]
        result = food_store.nutrients_for(ingredients)

        # All values should be 0.0 since food was not found
        expected_keys = [
            "kcal",
            "protein_g",
            "fat_g",
            "carbs_g",
            "Fe_mg",
            "Ca_mg",
            "K_mg",
            "Mg_mg",
            "VitD_IU",
            "B12_ug",
            "Folate_ug",
            "Iodine_ug",
        ]

        for key in expected_keys:
            assert result[key] == 0.0

    def test_nutrients_for_custom_per_g(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test nutrients_for with custom per_g value."""
        mock_food: Dict[str, Any] = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "Fe_mg": 0.1,
            "Ca_mg": 6.0,
            "K_mg": 107.0,
            "Mg_mg": 5.0,
            "VitD_IU": 0,
            "B12_ug": 0,
            "Folate_ug": 3.0,
            "Iodine_ug": 0,
            "per_g": 50.0,  # Custom per_g value
        }
        monkeypatch.setattr(food_store, "get_food", lambda food_id: mock_food)

        ingredients = [{"food_id": "1", "grams": 100.0}]
        result = food_store.nutrients_for(ingredients)

        # 100g of apple (per 50g) = 2x the values
        assert result["kcal"] == 104.0  # 52 * 2
        assert result["protein_g"] == 0.6  # 0.3 * 2

    def test_nutrients_for_missing_nutrient_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test nutrients_for with missing nutrient values."""
        mock_food: Dict[str, Any] = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            # Missing some nutrient values
            "per_g": 100.0,
        }
        monkeypatch.setattr(food_store, "get_food", lambda food_id: mock_food)

        ingredients = [{"food_id": "1", "grams": 100.0}]
        result = food_store.nutrients_for(ingredients)

        # Should handle missing values gracefully
        assert result["kcal"] == 52.0
        assert result["protein_g"] == 0.3
        assert result["Fe_mg"] == 0.0  # Missing value defaults to 0.0
        assert result["Ca_mg"] == 0.0  # Missing value defaults to 0.0

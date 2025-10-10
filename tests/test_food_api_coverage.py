"""
Тесты для покрытия Food API в app/routers/foods.py и app/services/food_store.py
"""

from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest


class TestFoodAPICoverage:
    """Тесты для покрытия Food API"""

    def setup_method(self):
        """Настройка для каждого теста"""
        # Создаем временную базу данных
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
        self.temp_db.close()

        # Создаем тестовую базу данных
        self._create_test_db()

        # Мокаем путь к базе данных
        self.db_patch = patch("app.services.food_store.DB_PATH", Path(self.temp_db.name))

    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self, "db_patch"):
            self.db_patch.stop()
        Path(self.temp_db.name).unlink(missing_ok=True)

    def _create_test_db(self):
        """Создает тестовую базу данных с данными"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        # Создаем таблицы
        cursor.execute("""
            CREATE TABLE foods (
                id TEXT PRIMARY KEY,
                canonical_name TEXT,
                group_name TEXT,
                per_g REAL DEFAULT 100.0,
                kcal REAL,
                protein_g REAL,
                fat_g REAL,
                carbs_g REAL,
                fiber_g REAL DEFAULT 0.0,
                Fe_mg REAL DEFAULT 0.0,
                Ca_mg REAL DEFAULT 0.0,
                K_mg REAL DEFAULT 0.0,
                Mg_mg REAL DEFAULT 0.0,
                VitD_IU REAL DEFAULT 0.0,
                B12_ug REAL DEFAULT 0.0,
                Folate_ug REAL DEFAULT 0.0,
                Iodine_ug REAL DEFAULT 0.0,
                flags TEXT DEFAULT '',
                brand TEXT,
                gtin TEXT,
                fdc_id TEXT,
                source TEXT DEFAULT 'USDA',
                source_priority INTEGER DEFAULT 0,
                version_date TEXT,
                price_per_100g REAL DEFAULT 0.0
            )
        """)

        # Создаем FTS таблицу
        cursor.execute("""
            CREATE VIRTUAL TABLE foods_fts USING fts5(
                canonical_name,
                content='foods',
                content_rowid='rowid'
            )
        """)

        # Добавляем тестовые данные
        test_foods = [
            (
                "apple_001",
                "Apple",
                "Fruits",
                100.0,
                52.0,
                0.3,
                0.2,
                14.0,
                2.4,
                0.1,
                6.0,
                107.0,
                5.0,
                0.0,
                0.0,
                3.0,
                0.0,
                "VEG",
                "Generic",
                None,
                "12345",
                "USDA",
                1,
                "2024-01-01",
                0.5,
            ),
            (
                "chicken_001",
                "Chicken Breast",
                "Meat",
                100.0,
                165.0,
                31.0,
                3.6,
                0.0,
                0.0,
                0.7,
                15.0,
                256.0,
                29.0,
                0.0,
                0.6,
                4.0,
                0.0,
                "",
                "Generic",
                None,
                "67890",
                "USDA",
                1,
                "2024-01-01",
                2.0,
            ),
            (
                "yogurt_001",
                "Greek Yogurt",
                "Dairy",
                100.0,
                59.0,
                10.0,
                0.4,
                3.6,
                0.0,
                0.0,
                110.0,
                141.0,
                11.0,
                0.0,
                0.5,
                7.0,
                0.0,
                "VEG",
                "Generic",
                None,
                "11111",
                "USDA",
                1,
                "2024-01-01",
                1.5,
            ),
        ]

        for food in test_foods:
            cursor.execute(
                """
                INSERT INTO foods VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                food,
            )

            # Добавляем в FTS
            cursor.execute(
                """
                INSERT INTO foods_fts(canonical_name) VALUES (?)
            """,
                (food[1],),
            )

        conn.commit()
        conn.close()

    def test_list_foods_success(self):
        """Тест успешного получения списка продуктов"""
        from app.services import food_store

        with self.db_patch:
            # Тест без запроса
            foods = food_store.search_foods("", 10, 0)
            assert len(foods) == 3
            assert foods[0]["id"] == "apple_001"

            # Тест с запросом
            foods = food_store.search_foods("apple", 10, 0)
            assert len(foods) == 1
            assert foods[0]["canonical_name"] == "Apple"

    def test_list_foods_with_aliases(self):
        """Тест поиска продуктов с алиасами"""
        from app.services import food_store

        with self.db_patch:
            # Тест функции expand_query напрямую
            terms = food_store.expand_query("йогурт")
            assert "йогурт" in terms
            assert "yogurt" in terms
            assert "yoghurt" in terms

    def test_get_food_success(self):
        """Тест получения конкретного продукта"""
        from app.services import food_store

        with self.db_patch:
            food = food_store.get_food("apple_001")
            assert food is not None
            assert food["canonical_name"] == "Apple"
            assert food["kcal"] == 52.0

    def test_get_food_not_found(self):
        """Тест получения несуществующего продукта"""
        from app.services import food_store

        with self.db_patch:
            food = food_store.get_food("nonexistent")
            assert food is None

    def test_nutrients_for_function(self):
        """Тест функции расчета нутриентов"""
        from app.services import food_store

        with self.db_patch:
            ingredients = [
                {"food_id": "apple_001", "grams": 100},
                {"food_id": "chicken_001", "grams": 150},
            ]

            nutrients = food_store.nutrients_for(ingredients)

            assert nutrients["kcal"] > 0
            assert nutrients["protein_g"] > 0
            assert nutrients["fat_g"] > 0
            assert nutrients["carbs_g"] > 0

    def test_nutrients_for_missing_food(self):
        """Тест расчета нутриентов с отсутствующим продуктом"""
        from app.services import food_store

        with self.db_patch:
            ingredients = [
                {"food_id": "apple_001", "grams": 100},
                {"food_id": "nonexistent", "grams": 100},
            ]

            nutrients = food_store.nutrients_for(ingredients)

            # Должен рассчитать только для существующего продукта
            assert nutrients["kcal"] > 0

    def test_expand_query_function(self):
        """Тест функции расширения запроса"""
        from app.services import food_store

        # Тест пустого запроса
        terms = food_store.expand_query("")
        assert terms == []

        # Тест обычного запроса
        terms = food_store.expand_query("apple")
        assert "apple" in terms

        # Тест запроса с алиасом
        terms = food_store.expand_query("йогурт")
        assert "йогурт" in terms
        assert "yogurt" in terms

    def test_food_api_endpoints(self):
        """Тест API эндпоинтов для продуктов - упрощенная версия"""
        from app.routers.foods import get_food, list_foods
        from app.services import food_store

        # Мокаем функции food_store
        with (
            patch.object(food_store, "search_foods") as mock_search,
            patch.object(food_store, "get_food") as mock_get,
        ):
            # Настраиваем моки
            mock_search.return_value = [
                {
                    "id": "apple_001",
                    "canonical_name": "Apple",
                    "kcal": 52.0,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbs_g": 14.0,
                }
            ]

            mock_get.return_value = {
                "id": "apple_001",
                "canonical_name": "Apple",
                "kcal": 52.0,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
                "group": "Fruits",
                "per_g": 100.0,
                "fiber_g": 2.4,
                "Fe_mg": 0.1,
                "Ca_mg": 6.0,
                "K_mg": 107.0,
                "Mg_mg": 5.0,
                "VitD_IU": 0.0,
                "B12_ug": 0.0,
                "Folate_ug": 3.0,
                "Iodine_ug": 0.0,
                "flags": ["VEG"],
                "brand": "Generic",
                "gtin": None,
                "fdc_id": "12345",
                "source": "USDA",
                "source_priority": 1,
                "version_date": "2024-01-01",
                "price_per_100g": 0.5,
            }

            # Тест функции list_foods
            foods = list_foods("", 10, 0)
            assert len(foods) == 1
            assert foods[0].id == "apple_001"

            # Тест функции get_food
            food = get_food("apple_001")
            assert food.id == "apple_001"
            assert food.canonical_name == "Apple"

    def test_food_api_validation(self):
        """Тест валидации параметров API"""
        from app import app

        with self.db_patch:
            client = TestClient(app)

            # Тест некорректного limit
            response = client.get("/api/v1/foods?limit=0")
            assert response.status_code == 422

            response = client.get("/api/v1/foods?limit=101")
            assert response.status_code == 422

            # Тест корректного limit
            response = client.get("/api/v1/foods?limit=50")
            assert response.status_code == 200

    def test_food_store_database_connection_error(self):
        """Тест обработки ошибок подключения к базе данных"""
        from app.services import food_store

        # Мокаем подключение к базе данных, чтобы вызвать ошибку
        with patch("app.services.food_store._connect") as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database connection failed")

            # Тест должен обработать ошибку
            with pytest.raises(sqlite3.Error):
                food_store.search_foods("test", 10, 0)

    def test_food_store_fts_error(self):
        """Тест обработки ошибок FTS"""
        from app.services import food_store

        with self.db_patch:
            # Создаем базу без FTS таблицы
            conn = sqlite3.connect(self.temp_db.name)
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS foods_fts")
            conn.commit()
            conn.close()

            # Тест должен работать без FTS - используем пустой запрос
            foods = food_store.search_foods("", 10, 0)
            # Должен вернуть результаты из обычной таблицы
            assert isinstance(foods, list)
            assert len(foods) == 3

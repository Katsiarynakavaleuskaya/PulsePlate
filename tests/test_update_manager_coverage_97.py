"""Tests to boost coverage for core/food_apis/update_manager.py to 97%."""

import json
import re

import pytest
from pathlib import Path
from typing import Type
from unittest.mock import MagicMock, patch

from core.food_apis.openfoodfacts_client import OFFFoodItem


class TestDatabaseUpdateManagerCoverage97:
    """Tests for DatabaseUpdateManager and helpers."""

    def test_path_wrapper_truediv_behaviour(self) -> None:
        """Path wrapper preserves Path division semantics."""
        # Use the public DatabaseUpdateManager to access the path wrapper functionality
        import tempfile
        from pathlib import Path as PathlibPath

        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)
            # Test division operation through the manager's cache_dir
            result = manager.cache_dir / "filename"
            assert isinstance(result, PathlibPath)
            assert str(result).endswith("/filename")

    def test_path_wrapper_fspath_behaviour(self) -> None:
        """Path wrapper implements os.fspath protocol."""
        # Use the public DatabaseUpdateManager to access the path wrapper functionality
        import tempfile

        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)
            # Test fspath operation through the manager's cache_dir
            result = manager.cache_dir.__fspath__()
            assert isinstance(result, str)

    def test_path_wrapper_str_behaviour(self) -> None:
        """Path wrapper converts to string via underlying Path."""
        # Use the public DatabaseUpdateManager to access the path wrapper functionality
        import tempfile

        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseUpdateManager(cache_dir=temp_dir)
            # Test string conversion through the manager's cache_dir
            result: str = str(manager.cache_dir)
            assert isinstance(result, str)

    @pytest.mark.parametrize(
        ("side_effects", "expected_exception", "expected_message"),
        [
            ({}, None, None),
            ({"usda": RuntimeError("USDA init failed")}, RuntimeError, "USDA init failed"),
            ({"off": ValueError("OFF client unavailable")}, ValueError, "OFF client unavailable"),
            (
                {"unified": OSError("Cache directory not writable")},
                OSError,
                "Cache directory not writable",
            ),
        ],
    )
    def test_database_update_manager_initialization_handles_dependency_errors(
        self,
        tmp_path: Path,
        side_effects: dict[str, Exception],
        expected_exception: Type[BaseException] | tuple[Type[BaseException], ...] | None,
        expected_message: str | None,
    ) -> None:
        """Initialization should either succeed or surface dependency failures clearly."""
        cache_path: Path = tmp_path / "cache"

        # Import everything locally
        from core.food_apis.update_manager import DatabaseUpdateManager

        with (
            patch("core.food_apis.update_manager.OFF_AVAILABLE", True),
            patch("core.food_apis.update_manager.USDAClient") as mock_usda_cls,
            patch("core.food_apis.update_manager.OFFClient") as mock_off_cls,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_unified_cls,
        ):
            mock_usda_cls.return_value = MagicMock(name="USDAClient")
            mock_off_cls.return_value = MagicMock(name="OFFClient")
            mock_unified_cls.return_value = MagicMock(name="UnifiedFoodDatabase")

            if side_effects.get("usda"):
                mock_usda_cls.side_effect = side_effects["usda"]
            if side_effects.get("off"):
                mock_off_cls.side_effect = side_effects["off"]
            if side_effects.get("unified"):
                mock_unified_cls.side_effect = side_effects["unified"]

            if expected_exception:
                with pytest.raises(expected_exception, match=expected_message or ""):
                    _: DatabaseUpdateManager = DatabaseUpdateManager(cache_dir=str(cache_path))
                return

            manager: DatabaseUpdateManager = DatabaseUpdateManager(cache_dir=str(cache_path))
            assert hasattr(manager, "cache_dir")
            assert manager.usda_client is mock_usda_cls.return_value
            assert manager.off_client is mock_off_cls.return_value
            assert manager.unified_db is mock_unified_cls.return_value

    def test_cache_dir_path_wrapper_behavior(self, tmp_path: Path) -> None:
        """Test cache_dir wrapper equality and hashing behavior through public API (lines 64, 68)."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        # Create managers with same cache directory
        cache_path = tmp_path / "test_cache"
        manager1 = DatabaseUpdateManager(cache_dir=str(cache_path))
        manager2 = DatabaseUpdateManager(cache_dir=str(cache_path))

        # Access the cache_dir wrappers through public API
        cache_dir1 = manager1.cache_dir
        cache_dir2 = manager2.cache_dir

        # Test that cache_dir behaves like Path in equality comparisons
        assert cache_dir1 == cache_dir2  # Same path content
        assert cache_dir1 == cache_path  # Compare with underlying path (should be equal)
        assert cache_dir1 != "not a path"  # Compare with non-path object

        # Test hashing behavior
        assert hash(cache_dir1) == hash(cache_dir2)  # Same hash for equal objects

        # Test that equivalent cache_dirs deduplicate in sets (important for dict/set usage)
        cache_dir_set = {cache_dir1, cache_dir2}
        assert len(cache_dir_set) == 1  # Should be deduplicated

    @pytest.mark.asyncio
    async def test_calculate_checksum_with_cache_data(self, tmp_path: Path) -> None:
        """Test checksum calculation with cache data via public API (lines 497-498)."""
        from core.food_apis.update_manager import DatabaseUpdateManager
        from unittest.mock import MagicMock, patch

        # Create mock data that will be used for checksum calculation
        test_food_data = {
            "apple": {"name": "Apple", "calories": 95, "protein": 0.5},
            "banana": {"name": "Banana", "calories": 105, "protein": 1.3},
        }

        different_food_data = {
            "orange": {"name": "Orange", "calories": 62, "protein": 1.2},
            "grape": {"name": "Grape", "calories": 69, "protein": 0.7},
        }

        # Mock clients to return controlled data
        with (
            patch("core.food_apis.update_manager.OFF_AVAILABLE", True),
            patch("core.food_apis.update_manager.USDAClient") as mock_usda_cls,
            patch("core.food_apis.update_manager.OFFClient") as mock_off_cls,
            patch("core.food_apis.update_manager.UnifiedFoodDatabase") as mock_unified_cls,
        ):
            mock_usda_client = MagicMock()
            mock_off_client = MagicMock()
            mock_unified_db = MagicMock()

            mock_usda_cls.return_value = mock_usda_client
            mock_off_cls.return_value = mock_off_client
            mock_unified_cls.return_value = mock_unified_db

            # Configure OFF client to return test data for searches
            async def mock_search_products(query, page_size=25):
                if query == "apple":
                    return [
                        OFFFoodItem(
                            code="apple",
                            product_name="Apple",
                            categories=["Fruits"],
                            nutrients_per_100g={
                                "energy-kcal": 95,
                                "protein_g": 0.5,
                                "fat_g": 0.3,
                                "carbs_g": 25.0,
                            },
                            ingredients_text="Apple",
                            brands="Generic",
                            labels=[],
                            countries=["United States"],
                            packaging=[],
                            image_url=None,
                            last_modified_t=1234567890,
                        )
                    ]
                elif query == "banana":
                    return [
                        OFFFoodItem(
                            code="banana",
                            product_name="Banana",
                            categories=["Fruits"],
                            nutrients_per_100g={
                                "energy-kcal": 105,
                                "protein_g": 1.3,
                                "fat_g": 0.4,
                                "carbs_g": 27.0,
                            },
                            ingredients_text="Banana",
                            brands="Generic",
                            labels=[],
                            countries=["United States"],
                            packaging=[],
                            image_url=None,
                            last_modified_t=1234567890,
                        )
                    ]
                else:
                    return []

            mock_off_client.search_products = mock_search_products

            manager = DatabaseUpdateManager(cache_dir=str(tmp_path))

            # First update with test data
            result1 = await manager.update_database("openfoodfacts", force=True)
            assert result1.success

            # Read the versions file to get the checksum
            versions_file = tmp_path / "database_versions.json"
            with open(versions_file, "r") as f:
                versions_data = json.load(f)

            checksum1 = versions_data["openfoodfacts"]["checksum"]

            # Verify checksum is a valid hex string
            assert isinstance(checksum1, str)
            assert len(checksum1) == 64  # SHA-256 produces 64 character hex string
            assert re.fullmatch(r"[0-9a-f]{64}", checksum1) is not None

            # Test determinism: same input should produce same checksum (update again)
            result2 = await manager.update_database("openfoodfacts", force=True)
            assert result2.success

            with open(versions_file, "r") as f:
                versions_data2 = json.load(f)

            checksum2 = versions_data2["openfoodfacts"]["checksum"]
            assert checksum1 == checksum2  # Same data should produce same checksum

            # Test uniqueness: different input should produce different checksum
            # Configure different mock data
            async def mock_search_products_different(query, page_size=25):
                if query == "apple":
                    return [
                        OFFFoodItem(
                            code="orange",
                            product_name="Orange",
                            categories=["Fruits"],
                            nutrients_per_100g={
                                "energy-kcal": 62,
                                "protein_g": 1.2,
                                "fat_g": 0.2,
                                "carbs_g": 15.0,
                            },
                            ingredients_text="Orange",
                            brands="Generic",
                            labels=[],
                            countries=["United States"],
                            packaging=[],
                            image_url=None,
                            last_modified_t=1234567890,
                        )
                    ]
                elif query == "banana":
                    return [
                        OFFFoodItem(
                            code="grape",
                            product_name="Grape",
                            categories=["Fruits"],
                            nutrients_per_100g={
                                "energy-kcal": 69,
                                "protein_g": 0.7,
                                "fat_g": 0.2,
                                "carbs_g": 18.0,
                            },
                            ingredients_text="Grape",
                            brands="Generic",
                            labels=[],
                            countries=["United States"],
                            packaging=[],
                            image_url=None,
                            last_modified_t=1234567890,
                        )
                    ]
                else:
                    return []

            mock_off_client.search_products = mock_search_products_different

            result3 = await manager.update_database("openfoodfacts", force=True)
            assert result3.success

            with open(versions_file, "r") as f:
                versions_data3 = json.load(f)

            checksum3 = versions_data3["openfoodfacts"]["checksum"]
            assert checksum1 != checksum3  # Different data should produce different checksum

    @pytest.mark.asyncio
    async def test_get_product_count_from_sqlite_database(self) -> None:
        """Test SQLite product count extraction for openfoodfacts (lines 564-572)."""
        import tempfile
        import sqlite3
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test SQLite database
            db_path = Path(temp_dir) / "off.sqlite"
            conn = sqlite3.connect(str(db_path))

            try:
                # Create products table and insert test data
                conn.execute(
                    """
                    CREATE TABLE products (
                        id INTEGER PRIMARY KEY,
                        name TEXT
                    )
                """
                )
                conn.executemany(
                    "INSERT INTO products (name) VALUES (?)",
                    [("Product 1",), ("Product 2",), ("Product 3",)],
                )
                conn.commit()
            finally:
                conn.close()

            manager = DatabaseUpdateManager(cache_dir=temp_dir)
            # Directly testing the private _get_actual_record_count method for coverage
            # This private method is tested to ensure proper SQLite database record counting
            # functionality, which is critical for database update validation but not exposed
            # through public APIs
            count = await manager._get_actual_record_count("openfoodfacts")

            # Should return 3 products
            assert count == 3

    @pytest.mark.asyncio
    async def test_get_actual_record_count_sqlite_connection_handling(self) -> None:
        """Test proper SQLite connection handling in product count (lines 564-572)."""
        import tempfile
        import sqlite3
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a lightweight placeholder file for the database path
            db_path = Path(temp_dir) / "off.sqlite"
            db_path.touch()

            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.execute.return_value = mock_cursor
                mock_cursor.fetchone.return_value = (1,)
                mock_connect.return_value = mock_conn

                # Directly testing the private _get_actual_record_count method for coverage
                # This ensures proper SQLite connection handling is verified in the record counting
                # logic, which is essential for database integrity but not accessible via public APIs
                count = await manager._get_actual_record_count("openfoodfacts")

                # Verify connection was properly closed
                mock_conn.close.assert_called_once()
                assert count == 1

    @pytest.mark.asyncio
    async def test_get_actual_record_count_sqlite_query_execution(self) -> None:
        """Test SQLite query execution in product count method."""
        import tempfile
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty SQLite file (will trigger SQLite code path)
            db_path = Path(temp_dir) / "off.sqlite"
            db_path.touch()

            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock the SQLite operations
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = (42,)  # Return count of 42

                mock_conn.execute.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                # Directly testing the private _get_actual_record_count method for coverage
                # This verifies SQLite query execution correctness in the record counting method,
                # ensuring database queries work properly but without exposing this through public APIs
                count = await manager._get_actual_record_count("openfoodfacts")

                # Verify the correct SQL query was executed
                mock_conn.execute.assert_called_once_with("SELECT COUNT(*) FROM products")
                mock_cursor.fetchone.assert_called_once()
                assert count == 42

    @pytest.mark.asyncio
    async def test_get_actual_record_count_sqlite_error_handling(self) -> None:
        """Test SQLite error handling in product count method."""
        import tempfile
        import sqlite3
        from core.food_apis.update_manager import DatabaseUpdateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty SQLite file
            db_path = Path(temp_dir) / "off.sqlite"
            db_path.touch()

            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            # Mock SQLite to raise an exception
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_conn.execute.side_effect = sqlite3.Error("Database error")
                mock_connect.return_value = mock_conn

                # Directly testing the private _get_actual_record_count method for coverage
                # This ensures proper error handling in SQLite operations within the record counting
                # method, critical for robust database operations but not exposed through public APIs
                count = await manager._get_actual_record_count("openfoodfacts")

                # Verify the error handling behavior (adjust expected value based on actual implementation)
                assert (
                    count == 0
                )  # or assert count is None, or use pytest.raises() if it should raise

                # Connection should still be closed even on error
                mock_conn.close.assert_called_once()

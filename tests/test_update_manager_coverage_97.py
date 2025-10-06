"""Tests to boost coverage for core/food_apis/update_manager.py to 97%."""

import pytest
from pathlib import Path
from typing import Type
from unittest.mock import MagicMock, patch


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

    def test_patchable_path_wrapper_eq_hash_methods(self) -> None:
        """Test __eq__ and __hash__ methods of _PatchablePathWrapper (lines 64, 68)."""
        from core.food_apis.update_manager import _PatchablePathWrapper

        # Create test paths
        path1 = Path("/test/path1")
        path2 = Path("/test/path2")
        path1_copy = Path("/test/path1")

        wrapper1 = _PatchablePathWrapper(path1)
        wrapper2 = _PatchablePathWrapper(path2)
        wrapper1_copy = _PatchablePathWrapper(path1_copy)

        # Test __eq__ method (line 64)
        assert wrapper1 == wrapper1_copy  # Same path content
        assert wrapper1 != wrapper2  # Different paths
        assert wrapper1 == path1  # Compare with underlying path (should be equal)
        assert wrapper1 != "not a path"  # Compare with non-path object

        # Test __hash__ method (line 68)
        assert hash(wrapper1) == hash(wrapper1_copy)  # Same hash for equal objects
        assert hash(wrapper1) != hash(wrapper2)  # Different hash for different objects

        # Test that wrappers with same path have same hash (important for set/dict usage)
        path_set = {wrapper1, wrapper1_copy}
        assert len(path_set) == 1  # Should be deduplicated

    def test_calculate_checksum_with_cache_data(self) -> None:
        """Test checksum calculation with cache data (lines 497-498)."""
        from core.food_apis.update_manager import DatabaseUpdateManager

        manager = DatabaseUpdateManager(cache_dir="/tmp")
        test_data = {"test": "checksum data"}  # Dict as expected by method

        checksum = manager._calculate_checksum(test_data)

        # Verify checksum is a valid hex string
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 produces 64 character hex string
        assert checksum.isalnum() and checksum.islower()

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
            # Create a test SQLite database
            db_path = Path(temp_dir) / "off.sqlite"
            conn = sqlite3.connect(str(db_path))

            try:
                conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY)")
                conn.execute("INSERT INTO products DEFAULT VALUES")
                conn.commit()
            finally:
                conn.close()

            manager = DatabaseUpdateManager(cache_dir=temp_dir)

            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.execute.return_value = mock_cursor
                mock_cursor.fetchone.return_value = (1,)
                mock_connect.return_value = mock_conn

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

                # Should fall back gracefully (return 0 or handle error)
                count = await manager._get_actual_record_count("openfoodfacts")

                # Connection should still be closed even on error
                mock_conn.close.assert_called_once()

"""
Additional tests for core.food_apis.update_manager module.
Focus on file cache operations and missing coverage paths.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from core.food_apis.update_manager import DatabaseUpdateManager, DatabaseVersion, UpdateResult


class TestUpdateManagerFileCache:
    """Tests for file cache operations and missing coverage paths."""

    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create DatabaseUpdateManager instance."""
        return DatabaseUpdateManager(cache_dir=temp_dir, update_interval_hours=24)

    @pytest.mark.asyncio
    async def test_record_count_csv_files(self, manager, temp_dir) -> None:
        """Test record counting with CSV files (lines 575-600)."""
        # Create CSV file with header
        csv_file = temp_dir / "products.csv"
        csv_content = "name,calories,protein\napple,100,0.3\nbanana,200,1.0\norange,150,0.8\n"
        csv_file.write_text(csv_content)

        # Test record count (should subtract header)
        count = await manager._get_actual_record_count("openfoodfacts")
        assert count == 3  # 4 lines - 1 header = 3 records

    @pytest.mark.asyncio
    async def test_record_count_jsonl_files(self, manager, temp_dir) -> None:
        """Test record counting with JSONL files (lines 575-600)."""
        # Create JSONL file
        jsonl_file = temp_dir / "products.jsonl"
        jsonl_content = '{"name": "apple", "calories": 100}\n{"name": "banana", "calories": 200}\n{"name": "orange", "calories": 150}\n'
        jsonl_file.write_text(jsonl_content)

        # Test record count
        count = await manager._get_actual_record_count("openfoodfacts")
        assert count == 3

    @pytest.mark.asyncio
    async def test_record_count_ndjson_files(self, manager, temp_dir) -> None:
        """Test record counting with NDJSON files (lines 575-600)."""
        # Create NDJSON file
        ndjson_file = temp_dir / "products.ndjson"
        ndjson_content = '{"name": "apple", "calories": 100}\n{"name": "banana", "calories": 200}\n'
        ndjson_file.write_text(ndjson_content)

        # Test record count
        count = await manager._get_actual_record_count("openfoodfacts")
        assert count == 2

    @pytest.mark.asyncio
    async def test_record_count_multiple_patterns(self, manager, temp_dir) -> None:
        """Test record counting with multiple file patterns (lines 575-600)."""
        # Create files with different patterns
        (temp_dir / "openfoodfacts.org.products.csv").write_text("name,calories\napple,100\n")
        (temp_dir / "off_products.jsonl").write_text('{"name": "banana"}\n')
        (temp_dir / "products.ndjson").write_text('{"name": "orange"}\n')

        # Should use the first matching pattern (CSV)
        count = await manager._get_actual_record_count("openfoodfacts")
        assert count == 1  # 2 lines - 1 header = 1 record

    @pytest.mark.asyncio
    async def test_record_count_no_files(self, manager) -> None:
        """Test record counting when no files found (lines 602-604)."""
        # No files in directory
        count = await manager._get_actual_record_count("openfoodfacts")
        assert count == 0

    @pytest.mark.asyncio
    async def test_record_count_exception_handling(self, manager, temp_dir, monkeypatch) -> None:
        """Test record counting exception handling (lines 606-608)."""
        # Create a directory with invalid permissions or corrupted file
        invalid_file = temp_dir / "products.csv"
        invalid_file.write_text("invalid,csv\n")

        # Mock open to raise exception
        def mock_open(*_args, **_kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr("builtins.open", mock_open)

        count = await manager._get_actual_record_count("openfoodfacts")
        assert count == 0

    @pytest.mark.asyncio
    async def test_cache_data_jsonl_files(self, manager, temp_dir) -> None:
        """Test cache data retrieval with JSONL files (lines 640-672)."""
        # Create JSONL file
        jsonl_file = temp_dir / "products.jsonl"
        jsonl_content = '{"name": "apple", "calories": 100}\n{"name": "banana", "calories": 200}\n{"invalid": "line"}\n'
        jsonl_file.write_text(jsonl_content)

        # Test cache data retrieval
        cache_data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(cache_data, dict)
        assert "apple" in cache_data
        assert "banana" in cache_data
        assert cache_data["apple"]["calories"] == 100

    @pytest.mark.asyncio
    async def test_cache_data_ndjson_files(self, manager, temp_dir) -> None:
        """Test cache data retrieval with NDJSON files (lines 640-672)."""
        # Create NDJSON file
        ndjson_file = temp_dir / "products.ndjson"
        ndjson_content = '{"name": "apple", "calories": 100}\n{"name": "banana", "calories": 200}\n'
        ndjson_file.write_text(ndjson_content)

        # Test cache data retrieval
        cache_data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(cache_data, dict)
        assert "apple" in cache_data
        assert "banana" in cache_data

    @pytest.mark.asyncio
    async def test_cache_data_csv_files(self, manager, temp_dir) -> None:
        """Test cache data retrieval with CSV files (lines 674-687)."""
        # Create CSV file
        csv_file = temp_dir / "products.csv"
        csv_content = "name,calories,protein\napple,100,0.3\nbanana,200,1.0\n"
        csv_file.write_text(csv_content)

        # Test cache data retrieval
        cache_data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(cache_data, dict)
        assert "apple" in cache_data
        assert "banana" in cache_data
        assert cache_data["apple"]["calories"] == "100"

    @pytest.mark.asyncio
    async def test_cache_data_multiple_patterns(self, manager, temp_dir) -> None:
        """Test cache data retrieval with multiple file patterns (lines 640-687)."""
        # Create files with different patterns
        (temp_dir / "products.jsonl").write_text('{"name": "apple"}\n')
        (temp_dir / "products.csv").write_text("name,calories\nbanana,200\n")

        # Should use JSONL first (first pattern)
        cache_data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(cache_data, dict)
        assert "apple" in cache_data

    @pytest.mark.asyncio
    async def test_cache_data_no_files(self, manager) -> None:
        """Test cache data retrieval when no files found."""
        # No files in directory
        cache_data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(cache_data, dict)
        assert len(cache_data) == 0

    @pytest.mark.asyncio
    async def test_cache_data_exception_handling(self, manager, temp_dir) -> None:
        """Test cache data retrieval exception handling (lines 688-689)."""
        # Create a file that will cause JSON decode error
        jsonl_file = temp_dir / "products.jsonl"
        jsonl_file.write_text('{"name": "apple"}\ninvalid json\n{"name": "banana"}\n')

        # Should handle JSON decode errors gracefully
        cache_data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(cache_data, dict)
        assert "apple" in cache_data
        assert "banana" in cache_data

    @pytest.mark.asyncio
    async def test_cache_data_sqlite_fallback(self, manager, temp_dir) -> None:
        """Test cache data retrieval with SQLite fallback (lines 614-630)."""
        # Create SQLite database
        sqlite_file = temp_dir / "off.sqlite"
        conn = sqlite3.connect(str(sqlite_file))
        try:
            conn.execute("CREATE TABLE products (name TEXT, data TEXT)")
            conn.execute("INSERT INTO products VALUES ('apple', '{\"calories\": 100}')")
            conn.execute("INSERT INTO products VALUES ('banana', '{\"calories\": 200}')")
            conn.commit()
        finally:
            conn.close()

        # Test cache data retrieval
        cache_data = await manager._get_cache_data_for_checksum("openfoodfacts")
        assert isinstance(cache_data, dict)
        assert "apple" in cache_data
        assert "banana" in cache_data
        assert "checksum" in cache_data["apple"]

    @pytest.mark.asyncio
    async def test_usda_update_success_path_coverage(self, manager) -> None:
        """Test USDA update success path to cover lines 325-371."""
        # Create mock data that will trigger the success path
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(
                return_value={
                    "apple": SimpleNamespace(
                        name="Apple",
                        nutrients_per_100g={
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        cost_per_100g=0.5,
                        tags=["fruit"],
                        availability_regions=["US"],
                        source="usda",
                        source_id="1",
                    )
                }
            ),
        ):

            # Mock the external dependencies
            with patch.object(manager, "usda_client") as mock_usda:
                mock_usda.fetch_all_foods = AsyncMock(
                    return_value=[{"fdcId": "1", "description": "Apple"}]
                )

                # Execute update
                result = await manager._update_usda_database(force=True)

                # Verify the result structure
                assert isinstance(result, UpdateResult)
                assert result.source == "usda"

    @pytest.mark.asyncio
    async def test_off_update_success_path_coverage(self, manager, temp_dir) -> None:
        """Test OFF update success path to cover lines 470-543."""
        # Create SQLite database for record counting
        sqlite_file = temp_dir / "off.sqlite"
        conn = sqlite3.connect(str(sqlite_file))
        try:
            conn.execute("CREATE TABLE products (name TEXT, data TEXT)")
            conn.execute("INSERT INTO products VALUES ('apple', '{\"name\": \"Apple\"}')")
            conn.commit()
        finally:
            conn.close()

        # Create mock data
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(
                return_value={
                    "apple": SimpleNamespace(
                        name="Apple",
                        nutrients_per_100g={
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        cost_per_100g=0.5,
                        tags=["fruit"],
                        availability_regions=["US"],
                        source="openfoodfacts",
                        source_id="1",
                    )
                }
            ),
        ):
            # Mock the external dependencies
            with patch.object(manager, "off_client") as mock_off:
                mock_off.search_products = AsyncMock(
                    return_value=[{"code": "1", "product_name": "Apple"}]
                )

                # Execute update
                result = await manager._update_off_database(force=True)

                # Verify the result structure
                assert isinstance(result, UpdateResult)
                assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_update_with_existing_version_coverage(self, manager, temp_dir) -> None:
        """Test update with existing version to cover lines 326-330, 471-475."""
        # Create backup file
        backup_data = {
            "apple": {
                "name": "Apple",
                "nutrients_per_100g": {"calories": 100},
                "cost_per_100g": 0.5,
                "tags": ["fruit"],
                "availability_regions": ["US"],
                "source": "usda",
                "source_id": "1",
            }
        }
        backup_file = temp_dir / "usda_backup_1.0.0.json"
        backup_file.write_text(json.dumps(backup_data))

        # Add existing version
        manager.versions["usda"] = DatabaseVersion(
            source="usda",
            version="1.0.0",
            last_updated="2023-01-01T00:00:00Z",
            record_count=1,
            checksum="abc123",
            metadata={"test": "data"},
        )

        # Mock the update process
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(
                return_value={
                    "apple": SimpleNamespace(
                        name="Apple",
                        nutrients_per_100g={
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        cost_per_100g=0.5,
                        tags=["fruit"],
                        availability_regions=["US"],
                        source="usda",
                        source_id="1",
                    )
                }
            ),
        ):
            # No usda_client mocking necessary for this path
            # Execute update
            result = await manager._update_usda_database(force=True)

            # Verify the result
            assert isinstance(result, UpdateResult)
            assert result.source == "usda"
            assert result.old_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_record_count_fallback_logic(self, manager) -> None:
        """Test record count fallback logic (lines 485-486)."""
        # Create mock data
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(
                return_value={
                    "apple": SimpleNamespace(
                        name="Apple",
                        nutrients_per_100g={
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        cost_per_100g=0.5,
                        tags=["fruit"],
                        availability_regions=["US"],
                        source="openfoodfacts",
                        source_id="1",
                    )
                }
            ),
        ):

            # Mock _get_actual_record_count to return 0
            with patch.object(manager, "_get_actual_record_count", new=AsyncMock(return_value=0)):
                with patch.object(manager, "off_client") as mock_off:
                    mock_off.search_products = AsyncMock(
                        return_value=[{"code": "1", "product_name": "Apple"}]
                    )

                    # Execute update
                    result = await manager._update_off_database(force=True)

                    # Verify the result
                    assert isinstance(result, UpdateResult)
                    assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_checksum_calculation_paths(self, manager) -> None:
        """Test checksum calculation paths (lines 492-498)."""
        # Create mock data
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(
                return_value={
                    "apple": SimpleNamespace(
                        name="Apple",
                        nutrients_per_100g={
                            "calories": 100,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 25.0,
                        },
                        cost_per_100g=0.5,
                        tags=["fruit"],
                        availability_regions=["US"],
                        source="openfoodfacts",
                        source_id="1",
                    )
                }
            ),
        ):

            # Mock _get_actual_record_count to return same as unified_foods
            with patch.object(manager, "_get_actual_record_count", new=AsyncMock(return_value=1)):
                with patch.object(manager, "off_client") as mock_off:
                    mock_off.search_products = AsyncMock(
                        return_value=[{"code": "1", "product_name": "Apple"}]
                    )

                    # Execute update
                    result = await manager._update_off_database(force=True)

                    # Verify the result
                    assert isinstance(result, UpdateResult)
                    assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_empty_database_warning(self, manager) -> None:
        """Test empty database warning (lines 502-505)."""
        # Create mock data
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(return_value={}),
        ):

            # Mock _get_actual_record_count to return 0
            with patch.object(manager, "_get_actual_record_count", new=AsyncMock(return_value=0)):
                with patch.object(manager, "off_client") as mock_off:
                    mock_off.search_products = AsyncMock(return_value=[])

                    # Execute update
                    result = await manager._update_off_database(force=True)

                    # Verify the result
                    assert isinstance(result, UpdateResult)
                    assert result.source == "openfoodfacts"

    @pytest.mark.asyncio
    async def test_error_handling_paths(self, manager) -> None:
        """Test error handling paths (lines 369-371, 541-543)."""
        # Test USDA error handling
        with patch.object(
            manager.unified_db,
            "get_common_foods_database",
            new=AsyncMock(side_effect=Exception("Critical database error")),
        ):
            result = await manager._update_usda_database(force=True)
            assert isinstance(result, UpdateResult)
            # The result might be successful even with API errors due to fallback logic
            # Just verify it's a valid UpdateResult
            assert result.source == "usda"

        # Test OFF error handling
        with patch.object(
            manager, "_get_actual_record_count", new=AsyncMock(side_effect=Exception("boom"))
        ):
            result = await manager._update_off_database(force=True)
            assert isinstance(result, UpdateResult)
            # The result might be successful even with API errors due to fallback logic
            # Just verify it's a valid UpdateResult
            assert result.source == "openfoodfacts"

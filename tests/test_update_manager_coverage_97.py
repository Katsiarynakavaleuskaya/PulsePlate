"""Tests to boost coverage for core/food_apis/update_manager.py to 97%."""

from pathlib import Path
from typing import Type
from unittest.mock import MagicMock, patch

import pytest


class TestDatabaseUpdateManagerCoverage97:
    """Tests for DatabaseUpdateManager and helpers."""

    def test_path_wrapper_truediv_behaviour(self) -> None:
        """Path wrapper preserves Path division semantics."""
        # Use the public DatabaseUpdateManager to access the path wrapper functionality
        from pathlib import Path as PathlibPath
        import tempfile

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
        expected_exception: type[BaseException] | tuple[type[BaseException], ...] | None,
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

"""Deterministic coverage tests for core_db / food_apis / unified_db facades.

Exercises every thin facade added to satisfy feature-key imports.
"""

from __future__ import annotations

from typing import Any


class TestCoreDbFacades:
    """Cover facades added to core/db.py."""

    def test_get_db_yields_session(self) -> None:
        from core.db import get_db

        gen = get_db()
        session = next(gen)
        assert session is not None
        gen.close()

    def test_create_tables_callable(self) -> None:
        from core.db import create_tables

        create_tables()  # idempotent; must not raise

    def test_init_database_callable(self) -> None:
        from core.db import init_database

        result = init_database()
        assert result is not None  # returns Engine

    def test_get_unified_food_db_returns_object_or_none(self) -> None:
        from core.db import get_unified_food_db

        result = get_unified_food_db()
        # Facade may return UnifiedFoodDatabase or None depending on import success
        assert result is None or hasattr(result, "search_food")


class TestFoodApisBaseFacades:
    """Cover core/food_apis/base.py."""

    def test_food_api_base_instantiation(self) -> None:
        from core.food_apis.base import FoodAPIBase

        obj = FoodAPIBase()
        assert obj is not None

    def test_food_data_provider_search(self) -> None:
        from core.food_apis.base import FoodDataProvider

        provider = FoodDataProvider()
        result = provider.search_food("apple")
        assert isinstance(result, list)


class TestFoodApisReexports:
    """Cover re-export modules (usda.py, openfoodfacts.py)."""

    def test_usda_client_reexport(self) -> None:
        from core.food_apis.usda import USDAClient

        assert USDAClient is not None
        client = USDAClient()
        assert client is not None

    def test_openfoodfacts_client_reexport(self) -> None:
        from core.food_apis.openfoodfacts import OpenFoodFactsClient

        assert OpenFoodFactsClient is not None


class TestSchedulerFacades:
    """Cover facades added to core/food_apis/scheduler.py."""

    def test_food_api_scheduler_alias(self) -> None:
        from core.food_apis.scheduler import FoodAPIScheduler

        assert FoodAPIScheduler is not None

    def test_check_update_status(self) -> None:
        from core.food_apis.scheduler import check_update_status

        result = check_update_status()
        assert isinstance(result, dict)

    def test_schedule_update(self) -> None:
        from core.food_apis.scheduler import schedule_update

        schedule_update()  # no-op; must not raise


class TestUnifiedDbFacades:
    """Cover facades added to core/food_apis/unified_db.py."""

    def test_unified_food_db_alias(self) -> None:
        from core.food_apis.unified_db import UnifiedFoodDB

        assert UnifiedFoodDB is not None

    def test_food_source_constants(self) -> None:
        from core.food_apis.unified_db import FoodSource

        assert FoodSource.USDA == "usda"
        assert FoodSource.OPENFOODFACTS == "openfoodfacts"

    def test_merge_food_sources(self) -> None:
        from core.food_apis.unified_db import merge_food_sources

        merged = merge_food_sources([{"a": 1}], [{"b": 2}])
        assert len(merged) == 2

    def test_update_unified_db(self) -> None:
        from core.food_apis.unified_db import update_unified_db

        update_unified_db()  # no-op; must not raise


class TestFoodSourcesFacades:
    """Cover core/food_sources additions."""

    def test_openfood_source(self) -> None:
        from core.food_sources.openfood_source import OpenFoodSource

        src = OpenFoodSource()
        assert src.search("test") == []

    def test_usda_source(self) -> None:
        from core.food_sources.usda_source import USDASource

        src = USDASource()
        assert src.get_food_data("123") is None

    def test_food_source_base(self) -> None:
        from core.food_sources.base import FoodSourceBase

        obj = FoodSourceBase()
        assert obj is not None

    def test_merge_food_entries(self) -> None:
        from core.food_sources.base import merge_food_entries

        assert merge_food_entries([{"name": "apple"}]) == {"name": "apple"}
        assert merge_food_entries([]) == {}

    def test_normalize_food_data(self) -> None:
        from core.food_sources.base import normalize_food_data

        data: dict[str, Any] = {"name": "apple"}
        assert normalize_food_data(data) == data

    def test_validate_food_entry(self) -> None:
        from core.food_sources.base import validate_food_entry

        assert validate_food_entry({"name": "apple"}) is True


class TestFoodCategoriesFacades:
    """Cover core/food_categories.py."""

    def test_classify_food(self) -> None:
        from core.food_categories import classify_food

        assert classify_food("apple") is None

    def test_get_food_category(self) -> None:
        from core.food_categories import get_food_category

        assert get_food_category("apple") is None

    def test_list_categories(self) -> None:
        from core.food_categories import list_categories

        assert list_categories() == []

    def test_validate_category(self) -> None:
        from core.food_categories import validate_category

        assert validate_category("fruit") is False


class TestCoreDbExceptionPaths:
    """Cover exception paths in core/db.py facades."""

    def test_get_unified_food_db_returns_none_on_exception(self) -> None:
        """Cover lines 964-965: exception path returns None."""
        from unittest.mock import patch

        # Mock UnifiedFoodDatabase to raise on import
        with patch(
            "core.food_apis.unified_db.UnifiedFoodDatabase",
            side_effect=ImportError("Module not available"),
        ):
            from core.db import get_unified_food_db

            result = get_unified_food_db()
            # When ImportError is raised, should return None
            assert result is None


class TestSchedulerInstancePath:
    """Cover _scheduler_instance paths in scheduler.py."""

    def test_check_update_status_with_scheduler_instance(self) -> None:
        """Cover line 338: when _scheduler_instance is not None."""
        from unittest.mock import MagicMock, patch

        import core.food_apis.scheduler as sched_module

        mock_scheduler = MagicMock()
        mock_scheduler.get_status.return_value = {"status": "running"}

        with patch.object(sched_module, "_scheduler_instance", mock_scheduler):
            from core.food_apis.scheduler import check_update_status

            result = check_update_status()
            assert result == {"status": "running"}
            mock_scheduler.get_status.assert_called_once()

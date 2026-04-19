from unittest.mock import patch

import pytest


def test_resolve_off_client_import_error_path():
    # RU: Форсируем ImportError, чтобы покрыть исключение в _resolve_off_client
    # EN: Force ImportError to cover the exception path in _resolve_off_client
    with patch("importlib.import_module", side_effect=ImportError("boom")):
        from core.food_apis import unified_db as U

        cls, available = U._resolve_off_client()
        assert cls is None and available is False


def test_unified_db_last_save_ts_import_time_failure(monkeypatch: pytest.MonkeyPatch, tmp_path):
    # RU: Подменяем импорт time внутри unified_db.__init__, чтобы попасть в except и _last_save_ts=None
    # EN: Make importing time fail within __init__ to hit except and set _last_save_ts=None
    import core.food_apis.unified_db as U

    def boom() -> None:
        raise ImportError("no time")

    # Avoid httpx/httpcore constructing by stubbing both clients before import hook
    with (
        patch("core.food_apis.unified_db.USDAClient"),
        patch("core.food_apis.unified_db.OFFClient", new=None),
    ):
        monkeypatch.setattr(U, "_load_time_module", boom)
        from core.food_apis.unified_db import UnifiedFoodDatabase

        db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
        assert getattr(db, "_last_save_ts", None) is None


def test_unified_db_save_cache_throttle_early_return(monkeypatch: pytest.MonkeyPatch, tmp_path):
    # RU: Включаем троттлинг и выставляем _last_save_ts так, чтобы сработал ранний выход
    # EN: Enable throttling and set _last_save_ts to trigger early return
    monkeypatch.setenv("UNIFIED_DB_SAVE_THROTTLE_MS", "100000")
    from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

    db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
    # Seed cache and set a recent last save timestamp
    db._memory_cache["k"] = UnifiedFoodItem(
        name="X",
        nutrients_per_100g={"protein_g": 1.0, "fat_g": 1.0, "carbs_g": 1.0},
        cost_per_100g=1.0,
        tags=[],
        availability_regions=[],
        source="test",
        source_id="id",
    )
    # Ensure the attribute exists and is recent
    import time

    db._last_save_ts = time.monotonic()
    # Should return early without exceptions
    db._save_cache()

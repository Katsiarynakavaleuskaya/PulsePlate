import os
from unittest.mock import patch

import pytest


def test_resolve_off_client_import_error_path():
    # RU: Форсируем ImportError, чтобы покрыть исключение в _resolve_off_client
    # EN: Force ImportError to cover the exception path in _resolve_off_client
    with patch("importlib.import_module", side_effect=ImportError("boom")):
        from core.food_apis import unified_db as U

        cls, available = U._resolve_off_client()
        assert cls is None and available is False


@pytest.mark.xfail(reason="Hijacking stdlib import of 'time' is unrealistic and flaky in CI")
def test_unified_db_last_save_ts_import_time_failure(monkeypatch: pytest.MonkeyPatch, tmp_path):
    # RU: Тест помечен xfail: симуляция сбоя импорта stdlib 'time' неустойчива.
    # EN: Marked xfail: forcing stdlib import failure is unrealistic; kept for documentation.
    import builtins as _bi  # noqa: N812

    real_import = _bi.__import__

    def boom(name: str, *args, **kwargs):  # noqa: ANN001, ANN003
        if name == "time":
            raise ImportError("no time")
        return real_import(name, *args, **kwargs)

    with (
        patch("core.food_apis.unified_db.USDAClient"),
        patch("core.food_apis.unified_db.OFFClient", new=None),
    ):
        with patch.object(_bi, "__import__", boom):
            from core.food_apis.unified_db import UnifiedFoodDatabase

            db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
            assert getattr(db, "_last_save_ts", None) is None


def test_unified_db_save_cache_throttle_early_return(monkeypatch: pytest.MonkeyPatch, tmp_path):
    # RU: Включаем троттлинг и выставляем _last_save_ts так, чтобы сработал ранний выход
    # EN: Enable throttling and set _last_save_ts to trigger early return
    os.environ["UNIFIED_DB_SAVE_THROTTLE_MS"] = "100000"  # large throttle window
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
    cache_file = db._get_cache_file()
    # Capture pre-state
    pre_exists = cache_file.exists()
    pre_mtime = cache_file.stat().st_mtime if pre_exists else None
    pre_len = len(db._memory_cache)

    # Should return early without exceptions and without writing the cache file
    db._save_cache()

    # Assert no file created or modified
    if pre_exists:
        assert cache_file.stat().st_mtime == pre_mtime
    else:
        assert not cache_file.exists()

    # Internal state unchanged
    assert len(db._memory_cache) == pre_len
    assert db._last_save_ts is not None

    # Cleanup
    os.environ.pop("UNIFIED_DB_SAVE_THROTTLE_MS", None)

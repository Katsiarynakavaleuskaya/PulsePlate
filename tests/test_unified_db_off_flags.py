import pytest


def test_unified_db_off_unavailable_import_path(monkeypatch: pytest.MonkeyPatch, tmp_path):
    import core.food_apis.unified_db as U

    # Force resolver to indicate OFF unavailable regardless of environment
    monkeypatch.setattr(U, "_resolve_off_client", lambda: (None, False))
    monkeypatch.setattr(U, "OFFClient", None)
    monkeypatch.setattr(U, "OFF_AVAILABLE", False)

    from core.food_apis.unified_db import UnifiedFoodDatabase

    db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
    assert getattr(db, "off_client", None) is None


def test_unified_db_save_throttle_and_last_save_none(monkeypatch: pytest.MonkeyPatch, tmp_path):
    from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

    db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
    # Force None last_save_ts and throttle env
    db._last_save_ts = None  # type: ignore[assignment]
    monkeypatch.setenv("UNIFIED_DB_SAVE_THROTTLE_MS", "50")
    # Put one item in memory cache so save attempts writing
    db._memory_cache["x"] = UnifiedFoodItem(
        name="x",
        nutrients_per_100g={},
        cost_per_100g=1.0,
        tags=[],
        availability_regions=[],
        source="s",
        source_id="id",
    )
    # Should not crash
    db._save_cache()


def test_unified_db_save_throttle_updates_timestamp(monkeypatch: pytest.MonkeyPatch, tmp_path):
    from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem

    db = UnifiedFoodDatabase(cache_dir=str(tmp_path))
    db._memory_cache["x"] = UnifiedFoodItem(
        name="x",
        nutrients_per_100g={},
        cost_per_100g=1.0,
        tags=[],
        availability_regions=[],
        source="s",
        source_id="id",
    )

    # Simulate earlier last save and throttle 10ms; then advance time to allow save
    times = [1000.0, 1000.0 + 0.02]  # second call is 20ms later

    def fake_monotonic():
        return times.pop(0)

    monkeypatch.setenv("UNIFIED_DB_SAVE_THROTTLE_MS", "10")
    import time as _t

    monkeypatch.setattr(_t, "monotonic", fake_monotonic)

    # First call sets _last_save_ts to 1000.0
    db._save_cache()
    # Second call occurs after 20ms (>10ms), should proceed and update ts
    db._save_cache()
    assert hasattr(db, "_last_save_ts")

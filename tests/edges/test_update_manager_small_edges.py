from pathlib import Path
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_update_manager_close_paths(tmp_path: Path):
    # RU: Покрываем ветки close() при разных состояниях клиентов
    # EN: Cover close() branches under different client states
    from core.food_apis.update_manager import DatabaseUpdateManager

    m = DatabaseUpdateManager(cache_dir=tmp_path)
    # Ensure all close methods exist
    m.usda_client.close = AsyncMock()
    m.unified_db.close = AsyncMock()

    # OFF client may be None; simulate present and None states
    if m.off_client is not None:
        m.off_client.close = AsyncMock()
    await m.close()  # no raise

    # Now force off_client None and close again
    m.off_client = None
    m.usda_client.close = AsyncMock()
    m.unified_db.close = AsyncMock()
    await m.close()

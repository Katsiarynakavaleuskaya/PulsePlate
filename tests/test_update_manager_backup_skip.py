import json
from pathlib import Path

import pytest

from core.food_apis.update_manager import DatabaseUpdateManager


@pytest.mark.asyncio
async def test_load_backup_skips_malformed(tmp_path: Path) -> None:
    """Verify that valid entries are loaded and malformed entries are skipped."""
    cache_dir = tmp_path
    mgr = DatabaseUpdateManager(cache_dir=cache_dir)

    data = {
        # valid
        "chicken": {
            "name": "Chicken Breast",
            "nutrients_per_100g": {"protein_g": 31.0},
            "cost_per_100g": 2.5,
            "tags": ["protein"],
            "availability_regions": ["US"],
            "source": "USDA",
            "source_id": "12345",
        },
        # malformed (missing required keys)
        "broken": {"name": "X"},
    }
    backup_file = cache_dir / "usda_backup_1.json"
    backup_file.write_text(json.dumps(data), encoding="utf-8")

    foods = await mgr._load_backup("usda", "1")
    assert "chicken" in foods
    assert "broken" not in foods

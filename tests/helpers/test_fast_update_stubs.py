from __future__ import annotations

import asyncio

from tests.helpers.fast_update_stubs import make_scheduler_stub


def test_fast_update_stubs_smoke() -> None:
    """Smoke-test helper stubs in a dedicated test module."""
    scheduler = make_scheduler_stub()
    force_update = getattr(scheduler, "force_update")
    result_default = asyncio.run(force_update())
    result_with_source = asyncio.run(force_update("usda"))
    assert "usda" in result_default
    assert "usda" in result_with_source
    source_result = result_default["usda"]
    assert hasattr(source_result, "success")
    assert hasattr(source_result, "old_version")

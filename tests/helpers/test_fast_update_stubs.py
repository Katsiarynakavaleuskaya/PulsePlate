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
    assert result_default["usda"] == {"ok": True, "status": "stubbed"}
    assert result_with_source["usda"] == {"ok": True, "status": "stubbed"}


def test_make_scheduler_stub_allows_falsy_payload() -> None:
    """Explicit falsy payload must not be replaced by default stub."""
    scheduler = make_scheduler_stub(usda_result={})
    force_update = getattr(scheduler, "force_update")
    result = asyncio.run(force_update("usda"))
    assert result["usda"] == {}

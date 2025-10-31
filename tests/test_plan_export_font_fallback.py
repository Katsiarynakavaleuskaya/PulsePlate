from pathlib import Path

from app.routers import plan_export as pe


def test_register_font_fallback_when_font_missing(monkeypatch):
    # Force FONT_PATH.exists() to be False to hit the Helvetica fallback
    monkeypatch.setattr(pe, "FONT_PATH", Path("/__no_such__/DejaVuSans.ttf"), raising=False)
    assert pe._register_font() == "Helvetica"

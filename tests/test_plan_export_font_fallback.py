import logging
from pathlib import Path

import pytest

from app.routers import plan_export as pe


def test_register_font_fallback_when_font_missing(monkeypatch, caplog):
    # Force FONT_PATH to a non-existent path to hit the Helvetica fallback
    fake_path = Path("/__no_such__/DejaVuSans.ttf")
    monkeypatch.setattr(pe, "FONT_PATH", fake_path, raising=False)
    # Make exists() return True for the fake path so it attempts registration,
    # which will fail and trigger the warning when trying to register a non-existent font file
    original_exists = Path.exists

    def mock_exists(self):
        if str(self) == str(fake_path):
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)
    with caplog.at_level(logging.WARNING):
        assert pe._register_font() == "Helvetica"
    assert "Failed to register font" in caplog.text

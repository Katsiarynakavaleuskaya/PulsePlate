"""Tests for font fallback behavior in plan export functionality.

This module verifies that the plan export router correctly handles font registration
failures by falling back to a default font (Helvetica) when the primary font file
cannot be found or registered.
"""

import logging
from pathlib import Path

import pytest

from app.routers import plan_export as pe


def test_register_font_fallback_when_font_missing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Force FONT_PATH to a non-existent path to hit the Helvetica fallback
    fake_path = Path("/__no_such__/DejaVuSans.ttf")
    monkeypatch.setattr(pe, "FONT_PATH", fake_path)

    # Make exists() return True for the fake path so it attempts registration,
    # which will fail and trigger the warning when trying to register a non-existent font file
    def mock_exists(path_instance):
        if path_instance == fake_path:
            return True
        return False

    monkeypatch.setattr(Path, "exists", mock_exists)
    with caplog.at_level(logging.WARNING):
        assert pe._register_font() == "Helvetica"
    assert "Failed to register font" in caplog.text

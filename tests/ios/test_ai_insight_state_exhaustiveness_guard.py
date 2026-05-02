"""Guard: AIInsightView must handle all AIInsightState cases explicitly.

The switch over vm.state in AIInsightView.swift must handle every enum case
without using ``default:`` or ``@unknown default`` to hide missing branches.

Evidence anchors:
- ios/PulsePlate/Views/AIInsightView.swift
- ios/PulsePlate/ViewModels/AIInsightViewModel.swift (AIInsightState enum)
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_VIEW = REPO_ROOT / "ios" / "PulsePlate" / "Views" / "AIInsightView.swift"


def test_ai_insight_view_handles_consent_required_state() -> None:
    """AIInsightView must contain an explicit case .consentRequired branch."""
    text = AI_VIEW.read_text(encoding="utf-8")
    assert (
        "case .consentRequired" in text
    ), "AIInsightView.swift must handle .consentRequired in switch vm.state"
    assert "switch vm.state" in text, "AIInsightView.swift must contain switch vm.state"


def test_ai_insight_view_does_not_hide_state_exhaustiveness_with_default() -> None:
    """switch vm.state must not use default: or @unknown default for internal enum."""
    text = AI_VIEW.read_text(encoding="utf-8")
    switch_start = text.index("switch vm.state")
    # Read enough of the switch block to cover all cases
    switch_block = text[switch_start : switch_start + 1500]
    assert (
        "default:" not in switch_block
    ), "switch vm.state must not use default: to hide enum exhaustiveness"
    assert (
        "@unknown default" not in switch_block
    ), "switch vm.state must not use @unknown default for internal enum"

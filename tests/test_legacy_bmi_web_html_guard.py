"""Guard: legacy embedded BMI page must not inject API fields via innerHTML (XSS)."""

from __future__ import annotations

from pathlib import Path


def test_legacy_bmi_calculator_template_avoids_innerhtml_for_results() -> None:
    """Regression for bug-hunter P1: /bmi JSON fields must reach DOM via textContent only."""
    root = Path(__file__).resolve().parents[1]
    path = root / "app" / "bootstrap" / "legacy_bmi_web_html.py"
    text = path.read_text(encoding="utf-8")
    assert (
        "innerHTML" not in text
    ), "legacy BMI HTML must use DOM textContent for user-visible API fields, not innerHTML"
    assert (
        "onchange=" not in text
    ), "legacy BMI HTML must bind events from the nonce'd script (CSP), not inline handlers"
    assert "response.ok" in text, "legacy BMI fetch must branch on HTTP ok before parsing JSON"

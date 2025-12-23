"""Unit tests for Beta-Binomial adherence model.

RU: Юнит-тесты для математической модели adherence.
EN: Unit tests for core adherence math (Beta-Binomial).
"""

from __future__ import annotations

import pytest

from core.bayes.adherence_model import AdherenceState, update_state


class TestAdherenceModel:
    """Test core mathematical model logic."""

    def test_update_state_rejects_zero_weight(self) -> None:
        """Test that zero weight is rejected."""
        state = AdherenceState.default()
        with pytest.raises(ValueError, match="weight must be > 0"):
            update_state(state, event_type="meal_logged", weight=0.0)

    def test_update_state_rejects_negative_weight(self) -> None:
        """Test that negative weight is rejected."""
        state = AdherenceState.default()
        with pytest.raises(ValueError, match="weight must be > 0"):
            update_state(state, event_type="meal_logged", weight=-1.0)

    def test_update_state_meal_logged_increases_alpha(self) -> None:
        """Test that meal_logged event increases alpha by weight."""
        state = AdherenceState.default()  # alpha=1.0, beta=1.0
        updated = update_state(state, event_type="meal_logged", weight=2.0)

        assert updated.alpha == 3.0  # 1.0 + 2.0
        assert updated.beta == 1.0  # unchanged
        assert updated.n == 1

    def test_update_state_slip_increases_beta(self) -> None:
        """Test that slip event increases beta by weight."""
        state = AdherenceState.default()  # alpha=1.0, beta=1.0
        updated = update_state(state, event_type="slip", weight=1.5)

        assert updated.alpha == 1.0  # unchanged
        assert updated.beta == 2.5  # 1.0 + 1.5
        assert updated.n == 1

    def test_from_payload_rejects_non_positive_alpha_beta(self) -> None:
        """Reject non-positive alpha/beta values from payload."""
        payload = {"alpha": 0.0, "beta": 1.0, "n": 0}
        with pytest.raises(ValueError, match="alpha and beta must be positive"):
            AdherenceState.from_payload(payload)

    def test_from_payload_rejects_negative_n(self) -> None:
        """Reject negative n values from payload."""
        payload = {"alpha": 1.0, "beta": 1.0, "n": -1}
        with pytest.raises(ValueError, match="n must be non-negative"):
            AdherenceState.from_payload(payload)

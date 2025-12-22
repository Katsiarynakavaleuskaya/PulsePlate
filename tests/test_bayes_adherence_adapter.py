"""Tests for adherence domain event adapter.

RU: Тесты для адаптера доменных событий adherence.
EN: Tests for adherence domain event adapter.
"""

from __future__ import annotations

import pytest

from core.bayes.adherence_adapter import DomainEvent, to_adherence_event


class TestAdherenceAdapter:
    """Test adherence adapter mappings."""

    def test_meal_logged_family_maps_to_meal_logged(self) -> None:
        """Test events that map to meal_logged are normalized."""
        for name in ("meal_logged", "day_completed", "workout_logged"):
            event = DomainEvent(name=name, weight=2.5)
            event_type, weight = to_adherence_event(event)
            assert event_type == "meal_logged"
            assert weight == 2.5

    def test_slip_maps_to_slip(self) -> None:
        """Test slip event mapping."""
        event = DomainEvent(name="slip", weight=1.0)
        event_type, weight = to_adherence_event(event)
        assert event_type == "slip"
        assert weight == 1.0

    def test_unsupported_event_raises(self) -> None:
        """Test unsupported domain event raises ValueError."""
        event = DomainEvent(name="unknown", weight=1.0)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Unsupported domain event"):
            to_adherence_event(event)

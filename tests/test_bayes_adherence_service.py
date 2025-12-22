"""Tests for adherence service retry behavior.

RU: Тесты для retry-логики сервиса adherence.
EN: Tests for adherence service retry behavior.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.analyzer.store import AnalyzerState
from core.bayes.adherence_model import AdherenceState
from core.bayes.adherence_service import AdherenceService


class _RetryStore:
    """Minimal store stub that simulates optimistic lock retries."""

    def __init__(self, user_id: int, analyzer_key: str, fail_times: int) -> None:
        self._user_id = user_id
        self._analyzer_key = analyzer_key
        self._fail_times = fail_times
        self.update_calls = 0
        self._state = self._make_state(
            state_version=1, payload=AdherenceState.default().to_payload()
        )

    def _make_state(self, state_version: int, payload: dict[str, object]) -> AnalyzerState:
        return AnalyzerState(
            user_id=self._user_id,
            analyzer_key=self._analyzer_key,
            state_schema_version=1,
            payload=payload,
            state_version=state_version,
            updated_at=datetime.now(timezone.utc),
        )

    def get_state(self, user_id: int, analyzer_key: str) -> AnalyzerState | None:
        return self._state

    def upsert_state(
        self,
        user_id: int,
        analyzer_key: str,
        state_schema_version: int,
        payload: dict[str, object],
    ) -> AnalyzerState:
        raise AssertionError("upsert_state should not be called for retry tests")

    def update_if_version_matches(
        self,
        user_id: int,
        analyzer_key: str,
        expected_version: int,
        state_schema_version: int,
        payload: dict[str, object],
    ) -> AnalyzerState | None:
        self.update_calls += 1
        if self.update_calls <= self._fail_times:
            return None
        self._state = self._make_state(state_version=expected_version + 1, payload=payload)
        return self._state


class TestAdherenceServiceRetries:
    """Test optimistic locking retry behavior."""

    def test_record_event_retries_then_succeeds(self) -> None:
        """Test a version mismatch retry followed by success."""
        store = _RetryStore(user_id=7, analyzer_key="v1:adherence", fail_times=1)
        service = AdherenceService(store=store)

        result = service.record_event(user_id=7, event_type="meal_logged", weight=1.0)

        assert store.update_calls == 2
        assert result.user_id == 7
        assert result.alpha == 2.0
        assert result.beta == 1.0
        assert result.n == 1

    def test_record_event_raises_after_retries_exhausted(self) -> None:
        """Test retries exhausted raises RuntimeError."""
        store = _RetryStore(user_id=7, analyzer_key="v1:adherence", fail_times=3)
        service = AdherenceService(store=store)

        with pytest.raises(RuntimeError, match="Failed to update adherence state after 3 retries"):
            service.record_event(user_id=7, event_type="meal_logged", weight=1.0)
        assert store.update_calls == 3

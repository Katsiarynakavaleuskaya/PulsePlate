"""Adherence service wired to AnalyzerStore.

RU: Сервис микромодели adherence, использующий AnalyzerStore (Postgres source of truth + optional TTL cache).
EN: Adherence micro-model service using AnalyzerStore.

This is the layer that:
- loads state from AnalyzerStore
- applies O(1) update
- saves it back with optimistic locking
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analyzer.store import AnalyzerState, AnalyzerStore

from .adherence_adapter import DomainEvent, to_adherence_event
from .adherence_model import (
    AdherenceEventType,
    AdherenceState,
    compute_metrics,
    update_state,
)

DEFAULT_ANALYZER_KEY = "v1:adherence"
DEFAULT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class AdherenceResult:
    """Result returned to API.

    RU: Результат для API.
    EN: Result returned to API.
    """

    user_id: int
    analyzer_key: str
    alpha: float
    beta: float
    n: int
    risk_slip: float
    confidence: float
    needs_more_data: bool


class AdherenceService:
    """Service facade for adherence state updates and reads."""

    def __init__(self, store: AnalyzerStore) -> None:
        """Initialize service with analyzer store.

        Args:
            store: AnalyzerStore implementation (SQLAlchemy + optional TTL cache)
        """
        self._store = store

    def get(self, user_id: int, analyzer_key: str = DEFAULT_ANALYZER_KEY) -> AdherenceResult:
        """Get current adherence risk and confidence for user.

        Args:
            user_id: User ID
            analyzer_key: Analyzer key (default: v1:adherence)

        Returns:
            AdherenceResult with current metrics
        """
        state = self._load_state(user_id=user_id, analyzer_key=analyzer_key)
        risk, confidence, needs_more_data = compute_metrics(state)
        return AdherenceResult(
            user_id=user_id,
            analyzer_key=analyzer_key,
            alpha=state.alpha,
            beta=state.beta,
            n=state.n,
            risk_slip=risk,
            confidence=confidence,
            needs_more_data=needs_more_data,
        )

    def record_domain_event(  # pragma: no cover
        self,
        user_id: int,
        domain_event: DomainEvent,
        analyzer_key: str = DEFAULT_ANALYZER_KEY,
    ) -> AdherenceResult:
        """Record a domain event (meal_logged, slip, etc).

        Args:
            user_id: User ID
            domain_event: Domain event to record
            analyzer_key: Analyzer key (default: v1:adherence)

        Returns:
            Updated AdherenceResult
        """
        event_type: AdherenceEventType
        event_type, weight = to_adherence_event(domain_event)
        return self.record_event(
            user_id, event_type=event_type, weight=weight, analyzer_key=analyzer_key
        )

    def record_event(
        self,
        user_id: int,
        event_type: AdherenceEventType,
        weight: float,
        analyzer_key: str = DEFAULT_ANALYZER_KEY,
    ) -> AdherenceResult:
        """Record an adherence event with optimistic locking retry.

        Args:
            user_id: User ID
            event_type: AdherenceEventType ("meal_logged" or "slip")
            weight: Event weight (default: 1.0)
            analyzer_key: Analyzer key (default: v1:adherence)

        Returns:
            Updated AdherenceResult

        Raises:
            RuntimeError: If optimistic lock fails after 3 retries
        """
        # Retry up to 3 times on optimistic lock conflict
        max_retries = 3
        for attempt in range(max_retries):
            existing = self._store.get_state(user_id=user_id, analyzer_key=analyzer_key)
            current = AdherenceState.from_payload(dict(existing.payload) if existing else None)

            updated = update_state(current, event_type=event_type, weight=weight)

            saved: AnalyzerState | None
            if existing is None:
                # First event for this user/key - simple upsert
                saved = self._store.upsert_state(
                    user_id=user_id,
                    analyzer_key=analyzer_key,
                    payload=updated.to_payload(),
                    state_schema_version=DEFAULT_SCHEMA_VERSION,
                )
            else:
                # Update with optimistic locking
                saved = self._store.update_if_version_matches(
                    user_id=user_id,
                    analyzer_key=analyzer_key,
                    expected_version=existing.state_version,
                    state_schema_version=DEFAULT_SCHEMA_VERSION,
                    payload=updated.to_payload(),
                )
                if saved is None:
                    # Version mismatch - retry with fresh state
                    if attempt < max_retries - 1:
                        continue
                    # All retries exhausted - raise error
                    raise RuntimeError(
                        f"Failed to update adherence state after {max_retries} retries "
                        f"due to concurrent modifications (user_id={user_id}, key={analyzer_key})"
                    )

            # Success - compute metrics and return
            assert saved is not None  # nosec B101 # Type narrowing after optimistic lock retry
            saved_state = AdherenceState.from_payload(dict(saved.payload))
            risk, confidence, needs_more_data = compute_metrics(saved_state)
            return AdherenceResult(
                user_id=user_id,
                analyzer_key=analyzer_key,
                alpha=saved_state.alpha,
                beta=saved_state.beta,
                n=saved_state.n,
                risk_slip=risk,
                confidence=confidence,
                needs_more_data=needs_more_data,
            )

        # Should never reach here due to raise in loop, but satisfy type checker
        raise RuntimeError("Unexpected: retry loop exhausted without return")  # pragma: no cover

    def _load_state(self, user_id: int, analyzer_key: str) -> AdherenceState:
        """Load state from store or return default if not found."""
        existing = self._store.get_state(user_id=user_id, analyzer_key=analyzer_key)
        return AdherenceState.from_payload(dict(existing.payload) if existing else None)

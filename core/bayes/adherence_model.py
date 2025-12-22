"""Adherence micro-model (Beta-Binomial).

RU: Микромодель соблюдения/срывов на Beta-Binomial.
EN: Adherence/slip risk micro-model based on Beta-Binomial.

Key idea:
- Store sufficient stats only (alpha/beta + n).
- O(1) update per event.
- Fast path: compute risk/confidence synchronously (no heavy inference, no LLM).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Tuple

AdherenceEventType = Literal["meal_logged", "slip"]


@dataclass(frozen=True)
class AdherenceState:
    """Immutable adherence state.

    RU: Состояние модели (immutable).
    EN: Immutable model state.
    """

    alpha: float
    beta: float
    n: int
    last_event_at: str | None = None

    @staticmethod
    def default() -> "AdherenceState":
        """Return symmetric Beta(1,1) prior state."""
        return AdherenceState(alpha=1.0, beta=1.0, n=0, last_event_at=None)

    @staticmethod
    def from_payload(payload: Dict[str, Any] | None) -> "AdherenceState":
        """Deserialize state from store payload."""
        if not payload:
            return AdherenceState.default()

        alpha = float(payload.get("alpha", 1.0))
        beta = float(payload.get("beta", 1.0))
        n = int(payload.get("n", 0))
        last_event_at = payload.get("last_event_at")
        return AdherenceState(alpha=alpha, beta=beta, n=n, last_event_at=last_event_at)

    def to_payload(self) -> Dict[str, Any]:
        """Serialize state to store payload."""
        return {
            "alpha": float(self.alpha),
            "beta": float(self.beta),
            "n": int(self.n),
            "last_event_at": self.last_event_at,
        }


def _now_utc_iso() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def update_state(
    state: AdherenceState, event_type: AdherenceEventType, weight: float = 1.0
) -> AdherenceState:
    """Update Beta-Binomial sufficient stats with a new event.

    RU: Обновить состояние по событию.
    EN: Update state given an adherence event.

    Args:
        state: current state
        event_type: "meal_logged" or "slip"
        weight: event weight (>0). Use 1.0 for default.

    Returns:
        New updated state (immutable).

    Raises:
        ValueError: If weight <= 0 or event_type is invalid
    """
    if weight <= 0:
        raise ValueError("weight must be > 0")

    alpha = state.alpha
    beta = state.beta

    if event_type == "meal_logged":
        alpha += weight
    elif event_type == "slip":
        beta += weight
    else:
        # Should not happen due to typing, but keep defensive.
        raise ValueError(f"Unsupported event_type: {event_type}")

    return AdherenceState(
        alpha=alpha,
        beta=beta,
        n=state.n + 1,
        last_event_at=_now_utc_iso(),
    )


def compute_metrics(state: AdherenceState) -> Tuple[float, float, bool]:
    """Compute slip risk and confidence.

    RU: Рассчитать риск срыва и confidence.
    EN: Compute slip risk and confidence.

    Returns:
        (risk_slip, confidence, needs_more_data)

    Notes:
        This is intentionally simple to keep fast path stable.
        We treat n < 7 as low confidence.
    """
    denom = state.alpha + state.beta
    if denom <= 0:
        # Shouldn't happen, but be safe.
        p_adherence = 0.5
    else:
        p_adherence = state.alpha / denom

    risk_slip = 1.0 - p_adherence

    # Simple confidence schedule: increase confidence as we observe more events.
    # n < 7 -> needs more data (low confidence)
    needs_more_data = state.n < 7
    confidence = 0.35 if needs_more_data else 0.85

    # Clamp just in case
    risk_slip = max(0.0, min(1.0, risk_slip))
    confidence = max(0.0, min(1.0, confidence))

    return risk_slip, confidence, needs_more_data

from __future__ import annotations

from app.routers.realtime_ws import _BurstLimiter


def test_limiter_allows_up_to_max_then_denies() -> None:
    """Exactly max_events are allowed; next event is denied."""
    t = 0.0
    limiter = _BurstLimiter(window_seconds=10, max_events=3, clock=lambda: t)

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_limiter_resets_after_full_window_passes() -> None:
    """Limiter allows events again after full-window eviction."""
    t = 0.0
    limiter = _BurstLimiter(window_seconds=10, max_events=2, clock=lambda: t)

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False

    t = 100.0
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_limiter_sliding_window_not_tumbling() -> None:
    """Sliding window evicts old events individually."""
    t = 0.0
    limiter = _BurstLimiter(window_seconds=10, max_events=2, clock=lambda: t)

    assert limiter.allow() is True
    t = 5.0
    assert limiter.allow() is True
    assert limiter.allow() is False

    t = 11.0
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_limiter_single_event_max() -> None:
    """Single-slot limiter denies until event leaves window."""
    t = 0.0
    limiter = _BurstLimiter(window_seconds=10, max_events=1, clock=lambda: t)

    assert limiter.allow() is True
    assert limiter.allow() is False

    t = 10.5
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_limiter_events_expire_exactly_at_boundary() -> None:
    """Boundary behavior must be deterministic around cutoff."""
    t = 0.0
    limiter = _BurstLimiter(window_seconds=10, max_events=1, clock=lambda: t)

    assert limiter.allow() is True
    t = 10.0
    assert limiter.allow() is False

    t = 10.001
    assert limiter.allow() is True


def test_limiter_instances_are_independent() -> None:
    """Separate websocket connections must not share limiter state."""
    t = 0.0
    clock = lambda: t  # noqa: E731
    limiter_a = _BurstLimiter(window_seconds=10, max_events=2, clock=clock)
    limiter_b = _BurstLimiter(window_seconds=10, max_events=2, clock=clock)

    assert limiter_a.allow() is True
    assert limiter_a.allow() is True
    assert limiter_a.allow() is False

    assert limiter_b.allow() is True
    assert limiter_b.allow() is True
    assert limiter_b.allow() is False

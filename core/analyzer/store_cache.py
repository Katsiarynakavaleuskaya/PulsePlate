"""Per-worker TTL cache wrapper for analyzer state.

RU: Обёртка-кэш с TTL для ускорения чтения состояния анализатора.
EN: Per-worker in-memory TTL cache for AnalyzerStore (optimization, not source of truth).

This cache provides read acceleration for analyzer state without violating consistency:
- Short TTL (default 30s) ensures staleness is minimal
- Writes always go to underlying store (write-through)
- Cache is per-worker (no cross-process coordination needed)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

from core.analyzer.store import AnalyzerState, AnalyzerStore


@dataclass
class _CacheItem:
    """Internal cache entry with expiration."""

    value: AnalyzerState
    expires_at: float


class TTLCacheAnalyzerStore(AnalyzerStore):
    """Per-worker TTL cache wrapper for AnalyzerStore.

    RU: Обёртка-кэш. Не источник истины, только ускорение чтения.
    EN: In-memory cache with TTL for read acceleration. Writes are always passed through.

    Thread-safety: Not thread-safe. Use per-worker or per-request scope.
    """

    def __init__(self, inner: AnalyzerStore, ttl_seconds: int = 30) -> None:
        """Initialize cache wrapper.

        Args:
            inner: Underlying AnalyzerStore (source of truth)
            ttl_seconds: Time-to-live for cached entries (default 30s)
        """
        self._inner = inner
        self._ttl = ttl_seconds
        self._cache: Dict[Tuple[int, str], _CacheItem] = {}

    def _now(self) -> float:
        """Get monotonic time for expiration checks."""
        return time.monotonic()

    def get_state(self, user_id: int, analyzer_key: str) -> Optional[AnalyzerState]:
        """Get state from cache or underlying store, populating cache on miss."""
        key = (user_id, analyzer_key)
        item = self._cache.get(key)
        if item and item.expires_at > self._now():
            return item.value

        value = self._inner.get_state(user_id, analyzer_key)
        if value is not None:
            self._cache[key] = _CacheItem(value=value, expires_at=self._now() + self._ttl)
        return value

    def upsert_state(
        self,
        user_id: int,
        analyzer_key: str,
        state_schema_version: int,
        payload: Mapping[str, Any],
    ) -> AnalyzerState:
        """Upsert state to underlying store and update cache (write-through)."""
        value = self._inner.upsert_state(user_id, analyzer_key, state_schema_version, payload)
        self._cache[(user_id, analyzer_key)] = _CacheItem(
            value=value, expires_at=self._now() + self._ttl
        )
        return value

    def update_if_version_matches(
        self,
        user_id: int,
        analyzer_key: str,
        expected_version: int,
        state_schema_version: int,
        payload: Mapping[str, Any],
    ) -> Optional[AnalyzerState]:
        """Update with optimistic locking and refresh cache on success."""
        value = self._inner.update_if_version_matches(
            user_id, analyzer_key, expected_version, state_schema_version, payload
        )
        if value is not None:
            self._cache[(user_id, analyzer_key)] = _CacheItem(
                value=value, expires_at=self._now() + self._ttl
            )
        else:
            self._cache.pop((user_id, analyzer_key), None)
        return value

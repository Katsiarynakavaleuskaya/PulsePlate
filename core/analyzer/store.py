"""Analyzer state storage interfaces and types.

RU: Интерфейсы и типы для хранения состояния байес-анализатора.
EN: Storage interfaces and types for Bayesian analyzer state management.

This module defines the core contract for analyzer state persistence, enabling
backend injection (Postgres/SQLite) as source of truth with optional per-worker caching.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional, Protocol


@dataclass(frozen=True)
class AnalyzerState:
    """Analyzer state snapshot for a specific user and analyzer key.

    RU: Снапшот состояния анализатора для конкретного пользователя и ключа.
    EN: Immutable snapshot of analyzer state with versioning for concurrency control.
    """

    user_id: int
    analyzer_key: str
    state_schema_version: int
    payload: Mapping[str, Any]
    state_version: int
    updated_at: datetime


class AnalyzerStore(Protocol):
    """Source-of-truth storage protocol for analyzer state.

    RU: Протокол хранилища состояния анализатора (source of truth).
    EN: Protocol defining persistence contract for analyzer state across workers/replicas.
    """

    def get_state(self, user_id: int, analyzer_key: str) -> Optional[AnalyzerState]:
        """Retrieve analyzer state or None if not found."""
        ...

    def upsert_state(
        self,
        user_id: int,
        analyzer_key: str,
        state_schema_version: int,
        payload: Mapping[str, Any],
    ) -> AnalyzerState:
        """Insert or update analyzer state, returning the persisted state."""
        ...

    def update_if_version_matches(
        self,
        user_id: int,
        analyzer_key: str,
        expected_version: int,
        state_schema_version: int,
        payload: Mapping[str, Any],
    ) -> Optional[AnalyzerState]:
        """Optimistic locking update. Returns None if version mismatch.

        RU: Обновление с оптимистической блокировкой. None = версия не совпала.
        """
        ...

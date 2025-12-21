"""SQLAlchemy-based analyzer state storage implementation.

RU: Реализация хранилища состояния анализатора на sync SQLAlchemy Session.
EN: Sync SQLAlchemy implementation of AnalyzerStore (works on SQLite dev/CI and Postgres prod).

This implementation provides cross-database UPSERT (Postgres + SQLite) and optimistic locking
for safe concurrent state updates across multiple workers/replicas.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session

from core.analyzer.store import AnalyzerState, AnalyzerStore
from core.models import AnalyzerStateModel


class SQLAlchemyAnalyzerStore(AnalyzerStore):
    """Sync SQLAlchemy implementation of AnalyzerStore.

    RU: Реализация AnalyzerStore на sync SQLAlchemy Session.
    EN: Works on SQLite (dev/CI) and Postgres (prod) with dialect-specific UPSERT.

    Provides:
    - Cross-database UPSERT (Postgres ON CONFLICT, SQLite INSERT OR REPLACE semantics)
    - Optimistic locking via state_version
    - Automatic version increment on updates
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._engine: Engine = session.get_bind()  # type: ignore[assignment]

    def get_state(self, user_id: int, analyzer_key: str) -> Optional[AnalyzerState]:
        """Retrieve analyzer state or None if not found."""
        stmt = select(AnalyzerStateModel).where(
            AnalyzerStateModel.user_id == user_id,
            AnalyzerStateModel.analyzer_key == analyzer_key,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None

        return AnalyzerState(
            user_id=row.user_id,
            analyzer_key=row.analyzer_key,
            state_schema_version=row.state_schema_version,
            payload=row.payload,
            state_version=row.state_version,
            updated_at=row.updated_at,
        )

    def upsert_state(
        self,
        user_id: int,
        analyzer_key: str,
        state_schema_version: int,
        payload: Mapping[str, Any],
    ) -> AnalyzerState:
        """Insert or update analyzer state, returning persisted state with incremented version."""
        dialect = self._engine.dialect.name

        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = (
                pg_insert(AnalyzerStateModel)
                .values(
                    user_id=user_id,
                    analyzer_key=analyzer_key,
                    state_schema_version=state_schema_version,
                    payload=dict(payload),
                    state_version=1,
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "analyzer_key"],
                    set_={
                        "state_schema_version": state_schema_version,
                        "payload": dict(payload),
                        "state_version": AnalyzerStateModel.state_version + 1,
                    },
                )
                .returning(AnalyzerStateModel)
            )
            row = self._session.execute(stmt).scalar_one()
            self._session.commit()
            return AnalyzerState(
                user_id=row.user_id,
                analyzer_key=row.analyzer_key,
                state_schema_version=row.state_schema_version,
                payload=row.payload,
                state_version=row.state_version,
                updated_at=row.updated_at,
            )

        # SQLite (dev/CI): use SQLite-specific INSERT OR REPLACE semantics
        if dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            sqlite_stmt = sqlite_insert(AnalyzerStateModel).values(
                user_id=user_id,
                analyzer_key=analyzer_key,
                state_schema_version=state_schema_version,
                payload=dict(payload),
                state_version=1,
            )
            sqlite_stmt_upsert = sqlite_stmt.on_conflict_do_update(
                index_elements=["user_id", "analyzer_key"],
                set_={
                    "state_schema_version": state_schema_version,
                    "payload": dict(payload),
                    "state_version": AnalyzerStateModel.state_version + 1,
                },
            )
            self._session.execute(sqlite_stmt_upsert)
            self._session.commit()

            # SQLite may not support RETURNING reliably in all versions → read after write
            result = self.get_state(user_id, analyzer_key)
            if result is None:
                raise RuntimeError(
                    "SQLite UPSERT succeeded but state could not be reloaded. "
                    "This indicates a database integrity issue."
                )
            return result

        raise RuntimeError(f"Unsupported DB dialect for analyzer store: {dialect}")

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
        stmt = (
            update(AnalyzerStateModel)
            .where(
                AnalyzerStateModel.user_id == user_id,
                AnalyzerStateModel.analyzer_key == analyzer_key,
                AnalyzerStateModel.state_version == expected_version,
            )
            .values(
                state_schema_version=state_schema_version,
                payload=dict(payload),
                state_version=AnalyzerStateModel.state_version + 1,
            )
        )

        result = cast(CursorResult, self._session.execute(stmt))
        if result.rowcount == 0:
            # Version mismatch - let caller handle transaction
            return None

        self._session.commit()
        return self.get_state(user_id, analyzer_key)

"""Helpers for PostgreSQL row-level security session context.

RU: Хелперы для установки session-local контекста PostgreSQL RLS.
EN: Helpers for setting PostgreSQL session-local context for RLS.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

RLS_CURRENT_USER_SETTING = "app.current_user_id"


def _is_postgres_session(session: Session) -> bool:
    """Return True when the SQLAlchemy session is bound to PostgreSQL."""
    get_bind = getattr(session, "get_bind", None)
    if get_bind is None:
        return False
    bind = get_bind()
    return bool(bind is not None and bind.dialect.name == "postgresql")


def apply_user_rls_context(session: Session, *, user_id: int) -> None:
    """Apply the current user id as a transaction-local PostgreSQL setting.

    RU: Устанавливает `app.current_user_id` только для текущей транзакции.
    EN: Sets `app.current_user_id` only for the current transaction.

    SQLite/test backends intentionally no-op here because they cannot enforce
    PostgreSQL RLS policies. Runtime app-layer filtering remains in place.
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer for DB RLS context")
    if not _is_postgres_session(session):
        return
    session.execute(
        text("SELECT set_config(:setting_name, :user_id, true)"),
        {
            "setting_name": RLS_CURRENT_USER_SETTING,
            "user_id": str(user_id),
        },
    )

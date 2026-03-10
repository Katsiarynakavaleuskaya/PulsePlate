"""Deterministic tests for PostgreSQL RLS session-context helpers.

RU: Проверки helper-слоя и DDL-контракта для RLS.
EN: Checks helper behavior and migration DDL contract for RLS.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.db_rls import apply_user_rls_context


def _make_session(dialect_name: str) -> MagicMock:
    session = MagicMock()
    bind = MagicMock()
    bind.dialect.name = dialect_name
    session.get_bind.return_value = bind
    return session


def test_apply_user_rls_context_uses_set_config_on_postgres() -> None:
    """Postgres path must set a transaction-local current user id."""
    session = _make_session("postgresql")

    apply_user_rls_context(session, user_id=42)

    session.execute.assert_called_once()
    stmt = session.execute.call_args.args[0]
    params = session.execute.call_args.args[1]
    assert "set_config" in str(stmt)
    assert params["setting_name"] == "app.current_user_id"
    assert params["user_id"] == "42"


def test_apply_user_rls_context_is_noop_on_sqlite() -> None:
    """SQLite path must remain a no-op because DB RLS is Postgres-only."""
    session = _make_session("sqlite")

    apply_user_rls_context(session, user_id=7)

    session.execute.assert_not_called()


def test_apply_user_rls_context_rejects_non_positive_user_id() -> None:
    """Invalid user ids must fail before any DB call."""
    session = _make_session("postgresql")

    with pytest.raises(ValueError):
        apply_user_rls_context(session, user_id=0)

    session.execute.assert_not_called()


def test_rls_migration_contains_enable_force_and_policy_contract() -> None:
    """The new migration must enable/force RLS for both user-bound tables."""
    repo_root = Path(__file__).resolve().parents[1]
    migration_path = repo_root / "alembic/versions/202603100001_enable_rag_user_rls.py"
    migration_text = migration_path.read_text(encoding="utf-8")

    assert "ALTER TABLE rag_feedback ENABLE ROW LEVEL SECURITY" in migration_text
    assert "ALTER TABLE rag_feedback FORCE ROW LEVEL SECURITY" in migration_text
    assert "ALTER TABLE user_knowledge ENABLE ROW LEVEL SECURITY" in migration_text
    assert "ALTER TABLE user_knowledge FORCE ROW LEVEL SECURITY" in migration_text
    assert "current_setting('app.current_user_id', true)" in migration_text
    assert "rag_feedback_user_isolation" in migration_text
    assert "user_knowledge_user_isolation" in migration_text

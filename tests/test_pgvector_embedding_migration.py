"""Regression checks for the pgvector embedding conversion migration.

RU: Фиксирует PostgreSQL-safe контракт для ревизии 202602280003.
EN: Locks the PostgreSQL-safe contract for revision 202602280003.
"""

from __future__ import annotations

from pathlib import Path


def test_pgvector_embedding_migration_avoids_subquery_transform_expression() -> None:
    """The migration must avoid subqueries inside ALTER COLUMN ... USING."""
    repo_root = Path(__file__).resolve().parents[1]
    migration_path = repo_root / "alembic/versions/202602280003_convert_embedding_to_vector768.py"
    migration_text = migration_path.read_text(encoding="utf-8")
    executable_sql = migration_text.split('op.execute("""', maxsplit=1)[1]

    assert "ALTER TABLE user_knowledge" in migration_text
    assert "ALTER COLUMN embedding TYPE vector(768)" in migration_text
    assert "regexp_replace(embedding, '\\\\s+', '', 'g')::vector(768)" in executable_sql
    assert "json_array_elements_text" not in executable_sql
    assert "SELECT ('[' || string_agg" not in executable_sql

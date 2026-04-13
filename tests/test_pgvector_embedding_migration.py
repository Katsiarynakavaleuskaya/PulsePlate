"""Regression checks for the pgvector embedding conversion migration.

RU: Фиксирует PostgreSQL-safe контракт для ревизии 202602280003.
EN: Locks the PostgreSQL-safe contract for revision 202602280003.
"""

from __future__ import annotations

from pathlib import Path
import re


def test_pgvector_embedding_migration_avoids_subquery_transform_expression() -> None:
    """The migration must avoid subqueries inside ALTER COLUMN ... USING."""
    repo_root = Path(__file__).resolve().parents[1]
    migration_path = repo_root / "alembic/versions/202602280003_convert_embedding_to_vector768.py"
    migration_text = migration_path.read_text(encoding="utf-8")
    normalized_cast_pattern = re.compile(
        r"regexp_replace\(\s*embedding\s*,\s*'\\\\s\+'\s*,\s*''\s*,\s*'g'\s*\)\s*::\s*vector\(768\)",
        re.MULTILINE,
    )
    normalized_null_guard_pattern = re.compile(
        r"NULLIF\(\s*regexp_replace\(\s*embedding\s*,\s*'\\\\s\+'\s*,\s*''\s*,\s*'g'\s*\)\s*,\s*''\s*\)\s+IS\s+NULL",
        re.MULTILINE,
    )

    assert "ALTER TABLE user_knowledge" in migration_text
    assert "ALTER COLUMN embedding TYPE vector(768)" in migration_text
    assert migration_text.count('op.execute("""') >= 1
    assert normalized_cast_pattern.search(migration_text)
    assert normalized_null_guard_pattern.search(migration_text)
    assert "json_array_elements_text" not in migration_text
    assert "SELECT ('[' || string_agg" not in migration_text

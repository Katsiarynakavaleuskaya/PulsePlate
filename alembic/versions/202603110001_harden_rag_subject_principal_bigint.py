"""harden RAG subject principal to bigint-owned rows

Revision ID: 202603110001
Revises: 202603100001
Create Date: 2026-03-11

Hardens the user-bound RAG tables so PostgreSQL RLS uses a bigint subject
principal instead of a narrowed int4 hash.  The runtime principal is derived
from authenticated API-key subject_id, not from users.id, so the old foreign
keys were semantically incorrect and are removed here.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202603110001"
down_revision = "202603100001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    op.execute("DROP POLICY IF EXISTS user_knowledge_user_isolation ON user_knowledge")
    op.execute("DROP POLICY IF EXISTS rag_feedback_user_isolation ON rag_feedback")

    op.execute("ALTER TABLE rag_feedback DROP CONSTRAINT IF EXISTS fk_rag_feedback_user")
    op.execute("ALTER TABLE user_knowledge DROP CONSTRAINT IF EXISTS fk_user_knowledge_user")

    op.execute("ALTER TABLE rag_feedback ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    op.execute("ALTER TABLE user_knowledge ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")

    op.execute("""
        CREATE POLICY rag_feedback_user_isolation ON rag_feedback
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
        )
    """)
    op.execute("""
        CREATE POLICY user_knowledge_user_isolation ON user_knowledge
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
        )
    """)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    op.execute("DROP POLICY IF EXISTS user_knowledge_user_isolation ON user_knowledge")
    op.execute("DROP POLICY IF EXISTS rag_feedback_user_isolation ON rag_feedback")

    # RU: При rollback удаляем subject-owned строки, которые не могут удовлетворить
    # старому FK-контракту на `users.id`.
    # EN: On rollback, delete subject-owned rows that cannot satisfy the legacy
    # `users.id` foreign-key contract.
    op.execute("""
        DELETE FROM rag_feedback
        WHERE NOT EXISTS (
            SELECT 1 FROM users WHERE users.id = rag_feedback.user_id
        )
    """)
    op.execute("""
        DELETE FROM user_knowledge
        WHERE NOT EXISTS (
            SELECT 1 FROM users WHERE users.id = user_knowledge.user_id
        )
    """)
    op.execute(
        "ALTER TABLE user_knowledge ALTER COLUMN user_id TYPE INTEGER USING user_id::integer"
    )
    op.execute("ALTER TABLE rag_feedback ALTER COLUMN user_id TYPE INTEGER USING user_id::integer")
    # RU: Восстанавливаем исходные FK при rollback к int4 users.id контракту.
    # EN: Restore the original FKs when rolling back to the int4 users.id contract.
    op.execute("""
        ALTER TABLE rag_feedback
        ADD CONSTRAINT fk_rag_feedback_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE user_knowledge
        ADD CONSTRAINT fk_user_knowledge_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    """)

    op.execute("""
        CREATE POLICY rag_feedback_user_isolation ON rag_feedback
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
    """)
    op.execute("""
        CREATE POLICY user_knowledge_user_isolation ON user_knowledge
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
    """)

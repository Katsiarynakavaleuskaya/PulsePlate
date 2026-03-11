"""enable PostgreSQL RLS for rag_feedback and user_knowledge

Revision ID: 202603100101
Revises: 202602280003
Create Date: 2026-03-10

Enables PostgreSQL row-level security for the user-bound RAG tables.
SQLite remains unchanged for tests; runtime app-layer filtering still applies.

See:
- docs/contracts/RAG_CONTRACT.md (§8 Security Notes)
- docs/db/rag_feedback_schema.md
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202603100101"
down_revision = "202602280003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    op.execute("ALTER TABLE rag_feedback ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE rag_feedback FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rag_feedback_user_isolation ON rag_feedback
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
    """)

    op.execute("ALTER TABLE user_knowledge ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_knowledge FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_knowledge_user_isolation ON user_knowledge
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
        )
    """)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    op.execute("DROP POLICY IF EXISTS user_knowledge_user_isolation ON user_knowledge")
    op.execute("ALTER TABLE user_knowledge NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_knowledge DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS rag_feedback_user_isolation ON rag_feedback")
    op.execute("ALTER TABLE rag_feedback NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE rag_feedback DISABLE ROW LEVEL SECURITY")

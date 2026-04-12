"""convert user_knowledge embedding to vector(768)

Revision ID: 202602280003
Revises: 202602280002
Create Date: 2026-02-28

Converts user_knowledge.embedding from TEXT (JSON array) to pgvector VECTOR(768)
on PostgreSQL for native cosine similarity search.  No-op on SQLite (tests
keep TEXT column and use application-level cosine).

The existing embeddings are stored as JSON arrays rendered as text
(e.g., "[0.1, 0.2, ...]").  PostgreSQL normalizes whitespace and casts the
string directly to pgvector format during the type conversion.

IVFFlat index is deferred until sufficient data (>1000 rows).

See:
- docs/contracts/RAG_CONTRACT.md (Feedback Schema §7, VECTOR(768))
- app/models/rag_feedback.py (UserKnowledge model)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202602280003"
down_revision = "202602280002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        # RU: PostgreSQL запрещает подзапросы внутри ALTER COLUMN ... USING.
        # EN: PostgreSQL rejects subqueries inside ALTER COLUMN ... USING.
        #
        # RU: Данные уже хранятся как JSON-массив в текстовом виде, например
        # "[0.1, 0.2, ...]". После удаления пробелов строка совместима с pgvector.
        # EN: Existing values are already JSON-array text like "[0.1, 0.2, ...]".
        # After whitespace normalization the string is pgvector-compatible.
        op.execute("""
            ALTER TABLE user_knowledge
            ALTER COLUMN embedding TYPE vector(768)
            USING (
                CASE
                    WHEN embedding IS NULL OR embedding = '' THEN NULL
                    ELSE regexp_replace(embedding, '\\s+', '', 'g')::vector(768)
                END
            )
            """)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        # Convert vector back to JSON array text.
        op.execute("""
            ALTER TABLE user_knowledge
            ALTER COLUMN embedding TYPE text
            USING (
                CASE
                    WHEN embedding IS NULL THEN NULL
                    ELSE embedding::text
                END
            )
            """)

"""convert user_knowledge embedding to vector(768)

Revision ID: 202602280003
Revises: 202602280002
Create Date: 2026-02-28

Converts user_knowledge.embedding from TEXT to pgvector VECTOR(768) on
PostgreSQL for native cosine similarity search.  No-op on SQLite (tests
keep TEXT column and use application-level cosine).

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
        op.execute(
            "ALTER TABLE user_knowledge "
            "ALTER COLUMN embedding TYPE vector(768) "
            "USING embedding::vector"
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "ALTER TABLE user_knowledge "
            "ALTER COLUMN embedding TYPE text "
            "USING embedding::text"
        )

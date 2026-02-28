"""convert user_knowledge embedding to vector(768)

Revision ID: 202602280003
Revises: 202602280002
Create Date: 2026-02-28

Converts user_knowledge.embedding from TEXT (JSON array) to pgvector VECTOR(768)
on PostgreSQL for native cosine similarity search.  No-op on SQLite (tests
keep TEXT column and use application-level cosine).

The existing embeddings are stored as JSON arrays (e.g., "[0.1, 0.2, ...]").
PostgreSQL's json_array_elements_text extracts array elements, and array_agg
reconstructs them into pgvector's text format before casting to vector.

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
        # Convert JSON array text to pgvector format.
        # The embedding column stores JSON arrays like "[0.1, 0.2, ...]".
        # We parse the JSON and reconstruct as pgvector text format.
        op.execute("""
            ALTER TABLE user_knowledge
            ALTER COLUMN embedding TYPE vector(768)
            USING (
                CASE
                    WHEN embedding IS NULL OR embedding = '' THEN NULL
                    ELSE (
                        SELECT ('[' || string_agg(elem::text, ',') || ']')::vector(768)
                        FROM json_array_elements_text(embedding::json) AS elem
                    )
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

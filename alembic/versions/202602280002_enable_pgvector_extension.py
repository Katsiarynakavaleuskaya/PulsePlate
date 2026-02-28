"""enable pgvector extension for vector retrieval

Revision ID: 202602280002
Revises: 202602280001
Create Date: 2026-02-28

Enables the pgvector extension on PostgreSQL for cosine similarity search
on user_knowledge.embedding.  No-op on SQLite (tests).

See: docs/contracts/RAG_CONTRACT.md (§4, Vector + rerank SLA)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202602280002"
down_revision = "202602280001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS vector")

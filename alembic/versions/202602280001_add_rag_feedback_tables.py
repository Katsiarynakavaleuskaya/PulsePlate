"""add rag_feedback and user_knowledge tables

Revision ID: 202602280001
Revises: 202602050001
Create Date: 2026-02-28

Migration from RAG_CONTRACT.md schema (§7) with adaptations:
- Integer PK (not UUID) for consistency with existing tables
- Integer user_id FK (users.id is Integer)
- No RLS policies (application-layer security only)
- JSONB via SQLAlchemy variant for SQLite compatibility
- user_knowledge.embedding uses TEXT for SQLite compatibility;
  pgvector VECTOR(768) should be used on Postgres production

See:
- docs/contracts/RAG_CONTRACT.md (Feedback Schema §7)
- docs/db/rag_feedback_schema.md
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202602280001"
down_revision = "202602050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### rag_feedback table ###
    op.create_table(
        "rag_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("retrieved_chunks", sa.Text(), nullable=True),  # JSONEncodedDict
        sa.Column("llm_response", sa.Text(), nullable=True),
        sa.Column("user_rating", sa.SmallInteger(), nullable=True),
        sa.Column("user_correction", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("hops", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("user_rating BETWEEN 1 AND 5", name="ck_rag_feedback_rating"),
        sa.CheckConstraint("confidence BETWEEN 0.0 AND 1.0", name="ck_rag_feedback_confidence"),
        sa.CheckConstraint("hops >= 0", name="ck_rag_feedback_hops"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_rag_feedback_user"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_rag_feedback_user_id", "rag_feedback", ["user_id"], unique=False)
    op.create_index(
        "idx_rag_feedback_user_created",
        "rag_feedback",
        ["user_id", "created_at"],
        unique=False,
    )
    # Note: Partial index (WHERE agent_id IS NOT NULL) is Postgres-specific
    # SQLite will create a regular index
    op.create_index(
        "idx_rag_feedback_agent",
        "rag_feedback",
        ["agent_id"],
        unique=False,
    )

    # ### user_knowledge table ###
    op.create_table(
        "user_knowledge",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # embedding: TEXT for SQLite compatibility
        # For Postgres production, consider ALTER COLUMN to VECTOR(768)
        # after enabling pgvector extension
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("source", sa.String(256), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_user_knowledge_user",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_user_knowledge_user", "user_knowledge", ["user_id"], unique=False)
    op.create_index("idx_user_knowledge_source", "user_knowledge", ["source"], unique=False)


def downgrade() -> None:
    # Drop user_knowledge
    op.drop_index("idx_user_knowledge_source", table_name="user_knowledge")
    op.drop_index("idx_user_knowledge_user", table_name="user_knowledge")
    op.drop_table("user_knowledge")

    # Drop rag_feedback
    op.drop_index("idx_rag_feedback_agent", table_name="rag_feedback")
    op.drop_index("idx_rag_feedback_user_created", table_name="rag_feedback")
    op.drop_index("idx_rag_feedback_user_id", table_name="rag_feedback")
    op.drop_table("rag_feedback")

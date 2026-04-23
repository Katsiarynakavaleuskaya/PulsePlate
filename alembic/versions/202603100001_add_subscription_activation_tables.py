"""add subscriptions and subscription activation audit tables

Revision ID: 202603100001
Revises: 202602280003
Create Date: 2026-03-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202603100001"
down_revision = "202602280003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable subscription current-state and audit tables."""

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("provider_receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("product_id", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_amount_minor", sa.Integer(), nullable=True),
        sa.Column("submitted_currency", sa.String(length=8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source", name="uq_subscriptions_user_source"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)

    op.create_table(
        "subscription_activation_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("provider_receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("product_id", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_amount_minor", sa.Integer(), nullable=True),
        sa.Column("submitted_currency", sa.String(length=8), nullable=True),
        sa.Column("evidence_summary", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_subscription_activation_audit_user_key",
        ),
    )
    op.create_index(
        "ix_subscription_activation_audit_subscription_id",
        "subscription_activation_audit",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_activation_audit_user_id",
        "subscription_activation_audit",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_activation_audit_source",
        "subscription_activation_audit",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    """Drop durable subscription activation persistence tables."""

    op.drop_index(
        "ix_subscription_activation_audit_source",
        table_name="subscription_activation_audit",
    )
    op.drop_index(
        "ix_subscription_activation_audit_user_id",
        table_name="subscription_activation_audit",
    )
    op.drop_index(
        "ix_subscription_activation_audit_subscription_id",
        table_name="subscription_activation_audit",
    )
    op.drop_table("subscription_activation_audit")

    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

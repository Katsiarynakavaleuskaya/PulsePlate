"""Add vip_llm_monthly_usage table (VIP LLM hard monthly quota).

RU: Таблица vip_llm_monthly_usage для жёсткой месячной квоты VIP LLM (requests/month).
EN: Add vip_llm_monthly_usage table for VIP LLM monthly hard quota (requests/month).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602050001"
down_revision = "20251225001838"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Создаём usage-таблицу для месячного счётчика VIP LLM.

    EN: Create usage table for VIP LLM monthly counters.
    """
    op.create_table(
        "vip_llm_monthly_usage",
        sa.Column("key_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("month_start_date", sa.Date(), nullable=False),
        sa.Column("used_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("key_fingerprint", "month_start_date"),
    )


def downgrade() -> None:
    """RU: Удаляем usage-таблицу.

    EN: Drop usage table.
    """
    op.drop_table("vip_llm_monthly_usage")

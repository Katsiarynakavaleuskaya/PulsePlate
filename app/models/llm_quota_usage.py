"""LLM monthly usage models (VIP hard quota).

RU: Модели учёта использования LLM по месячным корзинам (для hard quota).
EN: Models for monthly LLM usage accounting (hard quota enforcement).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class VipLlmMonthlyUsage(Base):
    """Monthly usage counter per VIP key fingerprint.

    RU: Счётчик запросов по VIP ключу (fingerprint) и месяцу (UTC calendar month).
    EN: Usage counter keyed by VIP key fingerprint and UTC calendar month.
    """

    __tablename__ = "vip_llm_monthly_usage"

    key_fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    month_start_date: Mapped[date] = mapped_column(Date, primary_key=True)
    used_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

"""Shared billing truth policy helpers.

RU: Общие policy-хелперы для backend billing truth.
EN: Shared policy helpers for backend billing truth.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

MANUAL_MONTHLY_ENTITLEMENT_DURATION = timedelta(days=30)
LEGACY_MANUAL_COMPAT_CUTOFF = datetime(2026, 3, 22, tzinfo=timezone.utc)


def normalize_utc_datetime(value: datetime) -> datetime:
    """Normalize naive or aware datetimes to UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def manual_monthly_entitlement_expires_at(*, activated_at: datetime) -> datetime:
    """Return bounded expiry for manual monthly entitlements.

    RU: Нормализует activation timestamp в UTC и строит bounded monthly expiry.
    EN: Normalizes activation timestamp to UTC and derives bounded monthly expiry.
    """

    return normalize_utc_datetime(activated_at) + MANUAL_MONTHLY_ENTITLEMENT_DURATION


def is_legacy_manual_compat_row(*, created_at: datetime) -> bool:
    """Return True only for manual rows created before the close-out rollout cutoff.

    RU: Compat-path применяется только к строкам, созданным до rollout close-out.
    EN: Compat path is limited to rows created before the close-out rollout cutoff.
    """

    return normalize_utc_datetime(created_at) < LEGACY_MANUAL_COMPAT_CUTOFF

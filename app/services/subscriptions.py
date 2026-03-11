"""Persistence helpers for billing subscriptions.

RU: Низкоуровневые DB-хелперы для subscriptions и activation audit.
EN: Low-level DB helpers for subscriptions and activation audit records.
"""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Subscription, SubscriptionActivationAudit
from app.schemas.payments import PaymentSource


def get_subscription_for_user_source(
    *,
    session: Session,
    user_id: int,
    source: PaymentSource,
) -> Subscription | None:
    """Return current subscription state for the given user/source pair."""

    statement = select(Subscription).where(
        Subscription.user_id == user_id,
        Subscription.source == source.value,
    )
    subscription: Subscription | None
    subscription = session.execute(statement).scalar_one_or_none()
    return subscription


def list_subscriptions_for_user(
    *,
    session: Session,
    user_id: int,
) -> list[Subscription]:
    """Return all persisted subscription rows for the given user.

    RU: Возвращает все persisted subscriptions пользователя.
    EN: Returns all persisted subscriptions for a user.
    """

    statement = (
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(
            desc(Subscription.updated_at),
            desc(Subscription.created_at),
            desc(Subscription.id),
        )
    )
    subscriptions = list(session.execute(statement).scalars().all())
    return subscriptions


def get_audit_by_user_key(
    *,
    session: Session,
    user_id: int,
    idempotency_key: str,
) -> SubscriptionActivationAudit | None:
    """Return activation audit row by deterministic idempotency identity."""

    statement = select(SubscriptionActivationAudit).where(
        SubscriptionActivationAudit.user_id == user_id,
        SubscriptionActivationAudit.idempotency_key == idempotency_key,
    )
    audit: SubscriptionActivationAudit | None
    audit = session.execute(statement).scalar_one_or_none()
    return audit


def get_audit_by_id(
    *,
    session: Session,
    activation_id: str,
) -> SubscriptionActivationAudit | None:
    """Return activation audit row by public activation id."""

    audit: SubscriptionActivationAudit | None
    audit = session.get(SubscriptionActivationAudit, activation_id)
    return audit


def get_subscription_by_id(
    *,
    session: Session,
    subscription_id: str,
) -> Subscription | None:
    """Return subscription row by primary key."""

    subscription: Subscription | None
    subscription = session.get(Subscription, subscription_id)
    return subscription


def get_latest_audit_for_subscription(
    *,
    session: Session,
    subscription_id: str,
) -> SubscriptionActivationAudit | None:
    """Return the latest audit event for a subscription."""

    statement = (
        select(SubscriptionActivationAudit)
        .where(SubscriptionActivationAudit.subscription_id == subscription_id)
        .order_by(
            desc(SubscriptionActivationAudit.created_at),
            desc(SubscriptionActivationAudit.id),
        )
        .limit(1)
    )
    audit: SubscriptionActivationAudit | None
    audit = session.execute(statement).scalar_one_or_none()
    return audit

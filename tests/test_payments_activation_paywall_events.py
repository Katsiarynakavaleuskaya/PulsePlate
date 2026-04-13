from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import delete, select

from app.models import PaywallExposureLedger
from app.schemas.payments import ActivateSubscriptionRequest
from app.services import payments_activation
from core import db as core_db


@pytest.fixture(autouse=True)
def _reset_payments_state() -> None:
    payments_activation.reset_state()


@pytest.fixture(autouse=True)
def _reset_paywall_ledger() -> None:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        session.execute(delete(PaywallExposureLedger))
        session.commit()
    finally:
        session.close()


def _manual_payload(
    *,
    source: str = "erip_qr",
    source_reference: str = "ERIP-LEDGER-0001",
) -> dict[str, Any]:
    return {
        "source": source,
        "payload": {
            "source_reference": source_reference,
            "submitted_amount": "9.99",
            "submitted_currency": "BYN",
        },
    }


def _load_rows() -> list[PaywallExposureLedger]:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        rows = (
            session.execute(
                select(PaywallExposureLedger).order_by(PaywallExposureLedger.created_at.asc())
            )
            .scalars()
            .all()
        )
        for row in rows:
            session.expunge(row)
        return rows
    finally:
        session.close()


def test_activation_records_upgrade_started_and_completed() -> None:
    payload = ActivateSubscriptionRequest.model_validate(
        _manual_payload(source_reference="ERIP-LEDGER-START-1")
    )

    payments_activation.activate_subscription(payload=payload, user_id=101)

    rows = _load_rows()
    assert [row.event_name for row in rows] == ["upgrade_started", "upgrade_completed"]
    assert rows[0].source_surface == "erip_qr"
    assert rows[0].trigger_reason == "activation_flow"
    assert rows[1].source_surface == "erip_qr"
    assert rows[1].trigger_reason == "activation_flow"


def test_activation_replay_does_not_duplicate_upgrade_completed() -> None:
    payload = ActivateSubscriptionRequest.model_validate(
        _manual_payload(source_reference="ERIP-LEDGER-REPLAY-1")
    )

    payments_activation.activate_subscription(payload=payload, user_id=202)
    payments_activation.activate_subscription(payload=payload, user_id=202)

    rows = _load_rows()
    assert [row.event_name for row in rows] == ["upgrade_started", "upgrade_completed"]


def test_activation_succeeds_when_ledger_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = ActivateSubscriptionRequest.model_validate(
        _manual_payload(source_reference="ERIP-LEDGER-FAILOPEN-1")
    )

    def _raise_ledger_failure(**_: Any) -> None:
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(
        payments_activation,
        "record_activation_lifecycle_event",
        _raise_ledger_failure,
    )

    response = payments_activation.activate_subscription(payload=payload, user_id=303)

    assert response.plan is not None
    assert response.activation_id
    assert _load_rows() == []

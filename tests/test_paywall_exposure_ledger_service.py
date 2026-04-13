from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from app.models import PaywallExposureLedger
from app.schemas.paywall_analytics import PaywallExposureEventName
from app.services.paywall_exposure_ledger import (
    PaywallExposureAuthContext,
    PaywallExposureRecordInput,
    record_paywall_exposure_event,
)
from core import db as core_db


@pytest.fixture(autouse=True)
def _reset_paywall_ledger() -> None:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        session.execute(delete(PaywallExposureLedger))
        session.commit()
    finally:
        session.close()


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


def test_record_paywall_exposure_event_persists_metadata_and_auth_context() -> None:
    row, created = record_paywall_exposure_event(
        record=PaywallExposureRecordInput(
            client_event_id="svc-event-0001",
            exposure_id="svc-exposure-0001",
            event_name=PaywallExposureEventName.shown,
            source_surface="bmi_soft_paywall",
            trigger_reason="post_bmi_result",
            via="pro_page",
            metadata={"step": "bmi_result"},
        ),
        auth_context=PaywallExposureAuthContext(
            subject_id=42,
            auth_source="cookie",
            tier_snapshot="PRO",
        ),
    )

    assert created is True
    assert row.client_event_id == "svc-event-0001"

    rows = _load_rows()
    assert len(rows) == 1
    assert rows[0].metadata_json == {"step": "bmi_result"}
    assert rows[0].subject_id == 42
    assert rows[0].auth_source == "cookie"
    assert rows[0].tier_snapshot == "PRO"


def test_record_paywall_exposure_event_is_idempotent() -> None:
    first, created_first = record_paywall_exposure_event(
        record=PaywallExposureRecordInput(
            client_event_id="svc-event-0002",
            exposure_id="svc-exposure-0002",
            event_name=PaywallExposureEventName.cta_clicked,
            source_surface="bmi_soft_paywall",
            trigger_reason="post_bmi_result",
        )
    )
    second, created_second = record_paywall_exposure_event(
        record=PaywallExposureRecordInput(
            client_event_id="svc-event-0002",
            exposure_id="svc-exposure-0002",
            event_name=PaywallExposureEventName.cta_clicked,
            source_surface="bmi_soft_paywall",
            trigger_reason="post_bmi_result",
        )
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id

    rows = _load_rows()
    assert len(rows) == 1

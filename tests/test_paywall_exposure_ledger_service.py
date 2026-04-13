from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models import PaywallExposureLedger
from app.schemas.paywall_analytics import PaywallExposureEventName
from app.services import paywall_exposure_ledger
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


def test_record_paywall_exposure_event_recovers_from_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_row = SimpleNamespace(id="existing-row")

    class _ExecuteResult:
        def __init__(self, row: object | None) -> None:
            self._row = row

        def scalar_one_or_none(self) -> object | None:
            return self._row

    class _FakeSession:
        def __init__(self) -> None:
            self._execute_calls = 0
            self.rollback_called = False
            self.closed = False

        def execute(self, _statement: object) -> _ExecuteResult:
            self._execute_calls += 1
            if self._execute_calls == 1:
                return _ExecuteResult(None)
            return _ExecuteResult(existing_row)

        def add(self, _row: object) -> None:
            return None

        def commit(self) -> None:
            raise IntegrityError("insert", {}, RuntimeError("duplicate"))

        def refresh(self, _row: object) -> None:
            return None

        def rollback(self) -> None:
            self.rollback_called = True

        def expunge(self, _row: object) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    fake_session = _FakeSession()
    monkeypatch.setattr(
        paywall_exposure_ledger,
        "get_session_factory",
        lambda: lambda: fake_session,
    )

    row, created = record_paywall_exposure_event(
        record=PaywallExposureRecordInput(
            client_event_id="svc-event-0003",
            exposure_id="svc-exposure-0003",
            event_name=PaywallExposureEventName.dismissed,
            source_surface="bmi_soft_paywall",
            trigger_reason="post_bmi_result",
        ),
        auth_context=PaywallExposureAuthContext(),
    )

    assert created is False
    assert row is existing_row
    assert fake_session.rollback_called is True
    assert fake_session.closed is True

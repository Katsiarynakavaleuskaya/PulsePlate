from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select

from app.models import PaywallExposureLedger
from app.middleware.api_tiers import derive_subject_id_from_api_key
from core import db as core_db

ROUTE_PATH = "/api/v1/internal/paywall/events"


@pytest.fixture(autouse=True)
def _reset_paywall_ledger() -> None:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        session.execute(delete(PaywallExposureLedger))
        session.commit()
    finally:
        session.close()


def _payload(
    *,
    client_event_id: str = "event-0001",
    exposure_id: str = "exposure-0001",
    event_name: str = "shown",
    source_surface: str = "bmi_soft_paywall",
    trigger_reason: str = "post_bmi_result",
    via: str | None = "pro_page",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "client_event_id": client_event_id,
        "exposure_id": exposure_id,
        "event_name": event_name,
        "source_surface": source_surface,
        "trigger_reason": trigger_reason,
    }
    if via is not None:
        body["via"] = via
    if metadata is not None:
        body["metadata"] = metadata
    return body


def _load_events() -> list[PaywallExposureLedger]:
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


def test_paywall_event_hidden_route_is_registered_but_not_in_openapi(client: TestClient) -> None:
    from app.main import app

    runtime_routes = {
        str(getattr(route, "path", "")): getattr(route, "include_in_schema", True)
        for route in app.routes
    }

    assert ROUTE_PATH in runtime_routes
    assert runtime_routes[ROUTE_PATH] is False
    assert ROUTE_PATH not in app.openapi().get("paths", {})


def test_paywall_shown_event_persists_for_anonymous_request(client: TestClient) -> None:
    response = client.post(ROUTE_PATH, json=_payload())

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}

    rows = _load_events()
    assert len(rows) == 1
    assert rows[0].event_name == "shown"
    assert rows[0].source_surface == "bmi_soft_paywall"
    assert rows[0].trigger_reason == "post_bmi_result"
    assert rows[0].subject_id is None
    assert rows[0].auth_source is None
    assert rows[0].tier_snapshot is None


def test_paywall_dismissed_event_keeps_shared_exposure_id(client: TestClient) -> None:
    response_shown = client.post(
        ROUTE_PATH,
        json=_payload(
            client_event_id="event-1001", exposure_id="exposure-1000", event_name="shown"
        ),
    )
    response_dismissed = client.post(
        ROUTE_PATH,
        json=_payload(
            client_event_id="event-1002",
            exposure_id="exposure-1000",
            event_name="dismissed",
            metadata={"dismissal_method": "escape"},
        ),
    )

    assert response_shown.status_code == 200, response_shown.text
    assert response_dismissed.status_code == 200, response_dismissed.text

    rows = _load_events()
    assert [row.event_name for row in rows] == ["shown", "dismissed"]
    assert rows[0].exposure_id == "exposure-1000"
    assert rows[1].exposure_id == "exposure-1000"
    assert rows[1].metadata_json == {"dismissal_method": "escape"}


def test_paywall_cta_clicked_is_idempotent_by_client_event_id(client: TestClient) -> None:
    first = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-2001", event_name="cta_clicked"),
    )
    second = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-2001", event_name="cta_clicked"),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    rows = _load_events()
    assert len(rows) == 1
    assert rows[0].client_event_id == "event-2001"


def test_paywall_event_rejects_invalid_event_name(client: TestClient) -> None:
    response = client.post(
        ROUTE_PATH,
        json=_payload(event_name="not_real"),
    )

    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "field_name,bad_value",
    [
        ("source_surface", "bmi-soft-paywall"),
        ("trigger_reason", "post bmi result"),
    ],
)
def test_paywall_event_rejects_invalid_slug_fields(
    client: TestClient,
    field_name: str,
    bad_value: str,
) -> None:
    body = _payload()
    body[field_name] = bad_value

    response = client.post(ROUTE_PATH, json=body)

    assert response.status_code == 422, response.text


def test_paywall_event_records_cookie_auth_context(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    exchange_response = client.post("/api/v1/pro/session/exchange", headers=vip_headers)
    assert exchange_response.status_code == 200, exchange_response.text

    response = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-3001", event_name="shown"),
    )

    assert response.status_code == 200, response.text

    rows = _load_events()
    assert len(rows) == 1
    expected_subject_id = derive_subject_id_from_api_key(vip_headers["X-API-Key"])
    assert rows[0].subject_id == expected_subject_id
    assert rows[0].auth_source == "cookie"
    assert rows[0].tier_snapshot == "VIP"

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select
from starlette.requests import Request

from app.models import PaywallExposureLedger
from app.middleware.api_tiers import derive_subject_id_from_api_key
from app.routers import paywall_analytics
from core import db as core_db

ROUTE_PATH = "/api/v1/internal/paywall/events"
FIRST_PARTY_ORIGIN = "https://app.pulseplate.test"


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


def _first_party_headers(origin: str = FIRST_PARTY_ORIGIN) -> dict[str, str]:
    return {"Origin": origin}


def _request(
    *,
    headers: dict[str, str] | None = None,
    scheme: str = "https",
    server: tuple[str, int] = ("api.pulseplate.test", 443),
) -> Request:
    encoded_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": ROUTE_PATH,
        "raw_path": ROUTE_PATH.encode("ascii"),
        "headers": encoded_headers,
        "scheme": scheme,
        "server": server,
        "client": ("127.0.0.1", 12345),
        "query_string": b"",
    }
    return Request(scope)


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


def test_resolve_optional_auth_context_propagates_unexpected_resolver_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(headers={"cookie": "pp_web_session=fake"})

    def _boom(**_: object) -> None:
        raise RuntimeError("broken auth resolver")

    monkeypatch.setattr(paywall_analytics, "resolve_pro_auth_context", _boom)

    with pytest.raises(RuntimeError, match="broken auth resolver"):
        paywall_analytics._resolve_optional_auth_context(
            request=request,
            x_api_key="broken-auth-header",  # pragma: allowlist secret
        )


def test_resolve_optional_auth_context_returns_none_on_expected_auth_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(headers={"cookie": "pp_web_session=fake"})

    def _reject(**_: object) -> None:
        raise HTTPException(status_code=401, detail="invalid")

    monkeypatch.setattr(paywall_analytics, "resolve_pro_auth_context", _reject)

    assert (
        paywall_analytics._resolve_optional_auth_context(
            request=request,
            x_api_key="broken-auth-header",  # pragma: allowlist secret
        )
        is None
    )


def test_paywall_shown_event_persists_for_authenticated_request(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(ROUTE_PATH, json=_payload(), headers=pro_headers)

    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json() == {"status": "ok"}

    rows = _load_events()
    assert len(rows) == 1
    assert rows[0].event_name == "shown"
    assert rows[0].source_surface == "bmi_soft_paywall"
    assert rows[0].trigger_reason == "post_bmi_result"
    expected_subject_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])
    assert rows[0].subject_id == expected_subject_id
    assert rows[0].auth_source == "header"
    assert rows[0].tier_snapshot == "PRO"


def test_paywall_dismissed_event_keeps_shared_exposure_id(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response_shown = client.post(
        ROUTE_PATH,
        json=_payload(
            client_event_id="event-1001", exposure_id="exposure-1000", event_name="shown"
        ),
        headers=pro_headers,
    )
    response_dismissed = client.post(
        ROUTE_PATH,
        json=_payload(
            client_event_id="event-1002",
            exposure_id="exposure-1000",
            event_name="dismissed",
            metadata={"dismissal_method": "escape"},
        ),
        headers=pro_headers,
    )

    assert response_shown.status_code == 200, response_shown.text
    assert response_dismissed.status_code == 200, response_dismissed.text

    rows = _load_events()
    assert [row.event_name for row in rows] == ["shown", "dismissed"]
    assert rows[0].exposure_id == "exposure-1000"
    assert rows[1].exposure_id == "exposure-1000"
    assert rows[1].metadata_json == {"dismissal_method": "escape"}


def test_paywall_cta_clicked_is_idempotent_by_client_event_id(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    first = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-2001", event_name="cta_clicked"),
        headers=pro_headers,
    )
    second = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-2001", event_name="cta_clicked"),
        headers=pro_headers,
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    rows = _load_events()
    assert len(rows) == 1
    assert rows[0].client_event_id == "event-2001"


@pytest.mark.parametrize(
    "headers",
    [
        None,
        _first_party_headers(),
        _first_party_headers("https://evil.example.com"),
        {"Referer": f"{FIRST_PARTY_ORIGIN}/pro"},
    ],
)
def test_paywall_event_noops_without_authentication(
    client: TestClient,
    headers: dict[str, str] | None,
) -> None:
    response = client.post(ROUTE_PATH, json=_payload(), headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}
    assert _load_events() == []


def test_paywall_event_noops_when_explicit_api_key_is_invalid(client: TestClient) -> None:
    response = client.post(
        ROUTE_PATH,
        json=_payload(),
        headers={"X-API-Key": "invalid-paywall-key"},  # pragma: allowlist secret
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}
    assert _load_events() == []


def test_anonymous_noop_does_not_block_later_authenticated_idempotent_write(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    body = _payload(client_event_id="event-noop-then-auth")

    anonymous_response = client.post(ROUTE_PATH, json=body, headers=_first_party_headers())
    authenticated_response = client.post(ROUTE_PATH, json=body, headers=pro_headers)

    assert anonymous_response.status_code == 200, anonymous_response.text
    assert authenticated_response.status_code == 200, authenticated_response.text

    rows = _load_events()
    assert len(rows) == 1
    assert rows[0].client_event_id == "event-noop-then-auth"
    assert rows[0].auth_source == "header"


def test_paywall_event_rejects_invalid_event_name(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        ROUTE_PATH,
        json=_payload(event_name="not_real"),
        headers=pro_headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("event_name", ["upgrade_started", "upgrade_completed"])
def test_paywall_event_rejects_server_authored_upgrade_events(
    client: TestClient,
    pro_headers: dict[str, str],
    event_name: str,
) -> None:
    response = client.post(
        ROUTE_PATH,
        json=_payload(event_name=event_name),
        headers=pro_headers,
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
    pro_headers: dict[str, str],
    field_name: str,
    bad_value: str,
) -> None:
    body = _payload()
    body[field_name] = bad_value

    response = client.post(ROUTE_PATH, json=body, headers=pro_headers)

    assert response.status_code == 422, response.text


def test_paywall_event_records_cookie_auth_context(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    exchange_response = client.post("/api/v1/pro/session/exchange", headers=pro_headers)
    assert exchange_response.status_code == 200, exchange_response.text

    response = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-3001", event_name="shown"),
    )

    assert response.status_code == 200, response.text

    rows = _load_events()
    assert len(rows) == 1
    expected_subject_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])
    assert rows[0].subject_id == expected_subject_id
    assert rows[0].auth_source == "cookie"
    assert rows[0].tier_snapshot == "PRO"


def test_paywall_event_records_cookie_auth_context_vip_compat(
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    exchange_response = client.post("/api/v1/pro/session/exchange", headers=vip_headers)
    assert exchange_response.status_code == 200, exchange_response.text

    response = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-3001-vip", event_name="shown"),
    )

    assert response.status_code == 200, response.text

    rows = _load_events()
    assert len(rows) == 1
    expected_subject_id = derive_subject_id_from_api_key(vip_headers["X-API-Key"])
    assert rows[0].subject_id == expected_subject_id
    assert rows[0].auth_source == "cookie"
    assert rows[0].tier_snapshot == "VIP"

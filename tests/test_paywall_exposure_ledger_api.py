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


@pytest.fixture(autouse=True)
def _set_allowed_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYWALL_ANALYTICS_ALLOWED_ORIGINS", FIRST_PARTY_ORIGIN)


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


@pytest.mark.parametrize("raw_value", [None, "", "   ", "not-a-url"])
def test_normalized_origin_rejects_empty_or_invalid_values(raw_value: str | None) -> None:
    assert paywall_analytics._normalized_origin(raw_value) is None


def test_local_environment_helper_uses_app_or_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert paywall_analytics._is_local_or_test_environment() is False

    monkeypatch.setenv("ENVIRONMENT", "test")
    assert paywall_analytics._is_local_or_test_environment() is True


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


def test_trusted_browser_origin_uses_local_request_host_when_allowlist_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PAYWALL_ANALYTICS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("WORKER_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    request = _request(headers={"Origin": "https://api.pulseplate.test"})

    assert paywall_analytics._trusted_browser_origin(request) == "https://api.pulseplate.test"


def test_trusted_browser_origin_returns_none_when_local_base_origin_cannot_be_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(paywall_analytics, "_configured_allowed_origins", lambda: set())
    monkeypatch.setattr(paywall_analytics, "_is_local_or_test_environment", lambda: True)

    original_normalized_origin = paywall_analytics._normalized_origin

    def _normalized_origin(value: str | None) -> str | None:
        if value == "https://api.pulseplate.test":
            return "https://api.pulseplate.test"
        if value == "https://api.pulseplate.test/":
            return None
        return original_normalized_origin(value)

    monkeypatch.setattr(paywall_analytics, "_normalized_origin", _normalized_origin)

    request = _request(headers={"Origin": "https://api.pulseplate.test"})

    assert paywall_analytics._trusted_browser_origin(request) is None


def test_paywall_shown_event_persists_for_anonymous_request(client: TestClient) -> None:
    response = client.post(ROUTE_PATH, json=_payload(), headers=_first_party_headers())

    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/json")
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
        headers=_first_party_headers(),
    )
    response_dismissed = client.post(
        ROUTE_PATH,
        json=_payload(
            client_event_id="event-1002",
            exposure_id="exposure-1000",
            event_name="dismissed",
            metadata={"dismissal_method": "escape"},
        ),
        headers=_first_party_headers(),
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
        headers=_first_party_headers(),
    )
    second = client.post(
        ROUTE_PATH,
        json=_payload(client_event_id="event-2001", event_name="cta_clicked"),
        headers=_first_party_headers(),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    rows = _load_events()
    assert len(rows) == 1
    assert rows[0].client_event_id == "event-2001"


def test_paywall_event_rejects_anonymous_request_without_first_party_provenance(
    client: TestClient,
) -> None:
    response = client.post(ROUTE_PATH, json=_payload())

    assert response.status_code == 403, response.text
    assert _load_events() == []


def test_paywall_event_rejects_untrusted_origin(client: TestClient) -> None:
    response = client.post(
        ROUTE_PATH,
        json=_payload(),
        headers=_first_party_headers("https://evil.example.com"),
    )

    assert response.status_code == 403, response.text
    assert _load_events() == []


def test_paywall_event_rejects_invalid_event_name(client: TestClient) -> None:
    response = client.post(
        ROUTE_PATH,
        json=_payload(event_name="not_real"),
        headers=_first_party_headers(),
    )

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("event_name", ["upgrade_started", "upgrade_completed"])
def test_paywall_event_rejects_server_authored_upgrade_events(
    client: TestClient,
    event_name: str,
) -> None:
    response = client.post(
        ROUTE_PATH,
        json=_payload(event_name=event_name),
        headers=_first_party_headers(),
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

    response = client.post(ROUTE_PATH, json=body, headers=_first_party_headers())

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

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient
import pytest


@pytest.fixture(autouse=True)
def _reset_partner_store() -> None:
    from app.services import restaurant_partner_orders

    restaurant_partner_orders.reset_state()


def _sample_draft() -> dict[str, object]:
    return {
        "restaurant_id": "resto-001",
        "currency": "usd",
        "fulfillment": "pickup",
        "items": [
            {
                "menu_item_id": "menu-1",
                "title": "Chicken Bowl",
                "qty": 2,
                "unit_price_minor": 1299,
            }
        ],
        "service_fee_minor": 99,
        "delivery_fee_minor": 0,
        "customer_note": "No peanuts",
        "dietary_tags": ["high-protein"],
        "allergens": ["nuts"],
        "consent": {
            "consent_share_with_partner": True,
            "consent_version": "v1",
        },
        "attribution_source": "pulseplate-v1",
    }


def _json(response: Any) -> dict[str, object]:
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    return response.json()


def test_partner_orders_require_pro_tier(client: TestClient) -> None:
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        json={"draft": _sample_draft()},
    )
    assert response.status_code in {401, 403}


def test_preview_partner_order_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": _sample_draft()},
    )
    assert response.status_code == 200, response.text
    payload = _json(response)
    assert payload["currency"] == "USD"
    assert payload["totals"]["subtotal_minor"] == 2598
    assert payload["totals"]["total_minor"] == 2697
    assert payload["warnings"] == []


def test_preview_partner_order_validation_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    draft = _sample_draft()
    draft["items"] = []
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": draft},
    )
    assert response.status_code == 422


def test_create_partner_order_and_get(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    create = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-1"},
    )
    assert create.status_code == 201, create.text
    created = _json(create)
    assert created["status"] == "pending_partner"
    order_id = created["id"]
    created_version = created["version"]
    assert created_version == 1

    get_resp = client.get(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}",
        headers=pro_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    assert _json(get_resp)["id"] == order_id


def test_create_partner_order_idempotent_replay(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    payload = {"draft": _sample_draft(), "client_event_id": "evt-create-2"}
    first = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json=payload,
    )
    second = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json=payload,
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert _json(first)["id"] == _json(second)["id"]


def test_create_partner_order_idempotency_conflict_409(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    base = {"draft": _sample_draft(), "client_event_id": "evt-create-3"}
    first = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json=base,
    )
    assert first.status_code == 201, first.text

    conflict = {"draft": _sample_draft(), "client_event_id": "evt-create-3"}
    conflict["draft"]["items"][0]["qty"] = 3
    second = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json=conflict,
    )
    assert second.status_code == 409


def test_get_partner_order_not_found_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/pro/restaurants/partner/orders/missing-order",
        headers=pro_headers,
    )
    assert response.status_code == 404


def test_confirm_partner_order_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-4"},
    )
    assert created.status_code == 201, created.text
    created_payload = _json(created)
    order_id = created_payload["id"]

    confirm = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json={"confirmed_by": "partner-user-1", "client_event_id": "evt-confirm-1"},
    )
    assert confirm.status_code == 200, confirm.text
    payload = _json(confirm)
    assert payload["status"] == "confirmed"
    assert payload["confirmed_by"] == "partner-user-1"
    assert payload["confirmed_at"] is not None
    assert payload["version"] == created_payload["version"] + 1


def test_confirm_partner_order_idempotent_replay(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-5"},
    )
    created_payload = _json(created)
    order_id = created_payload["id"]
    created_version = created_payload["version"]

    body = {"confirmed_by": "partner-user-2", "client_event_id": "evt-confirm-2"}
    first = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json=body,
    )
    second = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json=body,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_payload = _json(first)
    second_payload = _json(second)
    assert first_payload["status"] == "confirmed"
    assert second_payload["status"] == "confirmed"
    assert first_payload["version"] == created_version + 1
    assert second_payload["version"] == created_version + 1


def test_confirm_partner_order_invalid_transition_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-6"},
    )
    order_id = _json(created)["id"]

    first = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json={"confirmed_by": "partner-user-3"},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json={"confirmed_by": "partner-user-3"},
    )
    assert second.status_code == 422


def test_confirm_partner_order_not_found_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/missing/confirm",
        headers=pro_headers,
        json={"confirmed_by": "partner-user-4"},
    )
    assert response.status_code == 404


def test_confirm_partner_order_idempotency_conflict_409(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-7"},
    )
    order_id = _json(created)["id"]

    first = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json={
            "confirmed_by": "partner-user-5",
            "client_event_id": "evt-confirm-conflict",
            "note": "Partner accepted with note",
        },
    )
    assert first.status_code == 200, first.text
    assert _json(first)["customer_note"] == "Partner accepted with note"

    second = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json={
            "confirmed_by": "partner-user-5",
            "client_event_id": "evt-confirm-conflict",
            "note": "Different note",
        },
    )
    assert second.status_code == 409


def test_preview_partner_order_invalid_currency_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    draft = _sample_draft()
    draft["currency"] = "US1"
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": draft},
    )
    assert response.status_code == 422


def test_preview_partner_order_null_schedule_is_accepted(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    draft = _sample_draft()
    draft["scheduled_for"] = None
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": draft},
    )
    assert response.status_code == 200, response.text


def test_preview_partner_order_past_schedule_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    draft = _sample_draft()
    draft["scheduled_for"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": draft},
    )
    assert response.status_code == 422


def test_preview_partner_order_future_schedule_200(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    draft = _sample_draft()
    draft["scheduled_for"] = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": draft},
    )
    assert response.status_code == 200, response.text


def test_preview_partner_order_rejects_naive_schedule_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    draft = _sample_draft()
    draft["scheduled_for"] = datetime.now().replace(microsecond=0).isoformat()
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": draft},
    )
    assert response.status_code == 422


def test_preview_partner_order_requires_explicit_partner_consent_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    draft = _sample_draft()
    draft["consent"]["consent_share_with_partner"] = False
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/preview",
        headers=pro_headers,
        json={"draft": draft},
    )
    assert response.status_code == 422


def test_create_partner_order_rejects_empty_client_event_id_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": ""},
    )
    assert response.status_code == 422


def test_confirm_partner_order_rejects_empty_client_event_id_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-8"},
    )
    order_id = _json(created)["id"]
    response = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json={"confirmed_by": "partner-user-6", "client_event_id": ""},
    )
    assert response.status_code == 422


def test_issue_handoff_share_happy_path(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-9"},
    )
    order_id = _json(created)["id"]

    issue = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        headers=pro_headers,
        json={
            "issuer": "user-1",
            "partner_id": "partner-1",
            "expires_in_minutes": 60,
        },
    )
    assert issue.status_code == 201, issue.text
    payload = _json(issue)
    assert payload["order_id"] == order_id
    assert payload["issuer"] == "user-1"
    assert payload["partner_id"] == "partner-1"
    assert payload["issued_at"] is not None
    assert payload["expires_at"] is not None
    assert payload["revoked_at"] is None
    assert payload["status"] == "active"


def test_issue_handoff_share_requires_pro_tier(client: TestClient) -> None:
    response = client.post(
        "/api/v1/pro/restaurants/partner/orders/order-1/handoff/shares",
        json={
            "issuer": "user-2",
            "partner_id": "partner-2",
            "expires_in_minutes": 60,
        },
    )
    assert response.status_code in {401, 403}


def test_issue_handoff_share_unknown_order_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    issue = client.post(
        "/api/v1/pro/restaurants/partner/orders/missing-order/handoff/shares",
        headers=pro_headers,
        json={
            "issuer": "user-1",
            "partner_id": "partner-1",
            "expires_in_minutes": 60,
        },
    )
    assert issue.status_code == 404


def test_get_handoff_share_status_revoked_403(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-10"},
    )
    order_id = _json(created)["id"]

    issue = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        headers=pro_headers,
        json={
            "issuer": "user-2",
            "partner_id": "partner-2",
            "expires_in_minutes": 60,
        },
    )
    share_id = _json(issue)["share_id"]

    revoke = client.post(
        f"/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        headers=pro_headers,
    )
    assert revoke.status_code == 200, revoke.text

    status_resp = client.get(
        f"/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        headers=pro_headers,
    )
    assert status_resp.status_code == 403


def test_get_handoff_share_status_active_200(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-10b"},
    )
    order_id = _json(created)["id"]
    issue = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        headers=pro_headers,
        json={
            "issuer": "user-2b",
            "partner_id": "partner-2b",
            "expires_in_minutes": 60,
        },
    )
    share_id = _json(issue)["share_id"]
    status_resp = client.get(
        f"/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        headers=pro_headers,
    )
    assert status_resp.status_code == 200, status_resp.text
    assert _json(status_resp)["status"] == "active"


def test_revoke_handoff_share_idempotent_200(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-11"},
    )
    order_id = _json(created)["id"]
    issue = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        headers=pro_headers,
        json={
            "issuer": "user-3",
            "partner_id": "partner-3",
            "expires_in_minutes": 60,
        },
    )
    share_id = _json(issue)["share_id"]

    first = client.post(
        f"/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        headers=pro_headers,
    )
    second = client.post(
        f"/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        headers=pro_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert _json(first)["status"] == "revoked"
    assert _json(second)["status"] == "revoked"
    assert _json(second)["revoked_at"] is not None


def test_revoke_handoff_share_not_found_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/pro/restaurants/partner/handoff/shares/missing-share/revoke",
        headers=pro_headers,
    )
    assert response.status_code == 404


def test_get_handoff_share_status_expired_410(
    client: TestClient,
    pro_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-12"},
    )
    order_id = _json(created)["id"]
    issue = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        headers=pro_headers,
        json={
            "issuer": "user-4",
            "partner_id": "partner-4",
            "expires_in_minutes": 1,
        },
    )
    share_payload = _json(issue)
    share_id = share_payload["share_id"]
    expires_at = datetime.fromisoformat(str(share_payload["expires_at"]))

    from app.services import restaurant_partner_orders

    monkeypatch.setattr(
        restaurant_partner_orders,
        "_utc_now",
        lambda: expires_at + timedelta(seconds=1),
    )
    status_resp = client.get(
        f"/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        headers=pro_headers,
    )
    assert status_resp.status_code == 410


def test_get_handoff_share_status_not_found_404(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/pro/restaurants/partner/handoff/shares/missing-share/status",
        headers=pro_headers,
    )
    assert response.status_code == 404

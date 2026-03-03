from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
    payload = response.json()
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
    created = create.json()
    assert created["status"] == "pending_partner"
    order_id = created["id"]

    get_resp = client.get(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}",
        headers=pro_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["id"] == order_id


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
    assert first.json()["id"] == second.json()["id"]


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
    order_id = created.json()["id"]

    confirm = client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        headers=pro_headers,
        json={"confirmed_by": "partner-user-1", "client_event_id": "evt-confirm-1"},
    )
    assert confirm.status_code == 200, confirm.text
    payload = confirm.json()
    assert payload["status"] == "confirmed"
    assert payload["confirmed_by"] == "partner-user-1"
    assert payload["confirmed_at"] is not None


def test_confirm_partner_order_idempotent_replay(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-5"},
    )
    order_id = created.json()["id"]

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
    assert first.json()["status"] == "confirmed"
    assert second.json()["status"] == "confirmed"


def test_confirm_partner_order_invalid_transition_422(
    client: TestClient,
    pro_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=pro_headers,
        json={"draft": _sample_draft(), "client_event_id": "evt-create-6"},
    )
    order_id = created.json()["id"]

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
    order_id = created.json()["id"]

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
    assert first.json()["customer_note"] == "Partner accepted with note"

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

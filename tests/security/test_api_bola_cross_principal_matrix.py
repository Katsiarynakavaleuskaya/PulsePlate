from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from fastapi.testclient import TestClient
from httpx import Response
import pytest
from sqlalchemy import select

from app.http_error_details import (
    ACTIVATION_ACCESS_FORBIDDEN_DETAIL,
    ORDER_ACCESS_FORBIDDEN_DETAIL,
    SHARE_ACCESS_FORBIDDEN_DETAIL,
)
from app.middleware.api_tiers import derive_subject_id_from_api_key
from app.models import Subscription, SubscriptionActivationAudit
from app.routers import pro_restaurant_partner
from app.schemas.payments import (
    ActivateSubscriptionRequest,
    ManualRailIntentRequest,
    SubscriptionActivationResponse,
)
from app.services import payments_activation, restaurant_partner_orders
from core import db as core_db
from tests.security._api_authz_contracts import (
    API_AUTHZ_CONTRACTS,
    CONTRACT_BY_KEY,
    RouteKey,
    is_bola_v1_eligible_contract,
)

pytestmark = pytest.mark.usefixtures("reset_payments_state")

MANUAL_FOREIGN_SERVICE_SEED = "bola-manual-foreign-service-seed"

PaymentRow = tuple[tuple[str, object], ...]
PaymentTableSnapshot = tuple[str, tuple[PaymentRow, ...]]
PaymentStateSnapshot = tuple[PaymentTableSnapshot, ...]
RestaurantStateSnapshot = dict[str, object]
BoundActor = Literal["owner", "foreign"]
BoundTargetCall = tuple[BoundActor, RouteKey]


@dataclass(frozen=True)
class BolaExecutionContext:
    client: TestClient
    pro_headers: dict[str, str]
    vip_headers: dict[str, str]
    manual_billing_headers: dict[str, str]
    bound_target_calls: list[BoundTargetCall]


@dataclass(frozen=True)
class BolaScenario:
    oracle_id: str
    route_key: RouteKey
    execute: Callable[[BolaExecutionContext, RouteKey], None]


@pytest.fixture(autouse=True)
def _reset_restaurant_state() -> Iterator[None]:
    restaurant_partner_orders.reset_state()
    with pro_restaurant_partner._ISSUER_LOCK:  # noqa: SLF001 - test-only state reset
        pro_restaurant_partner._ISSUER_BY_API_KEY.clear()  # noqa: SLF001
    yield
    restaurant_partner_orders.reset_state()
    with pro_restaurant_partner._ISSUER_LOCK:  # noqa: SLF001 - test-only state reset
        pro_restaurant_partner._ISSUER_BY_API_KEY.clear()  # noqa: SLF001


def _assert_json_response(
    response: Response,
    *,
    status_code: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    assert response.status_code == status_code, response.text
    response_payload = response.json()
    assert isinstance(response_payload, dict)
    if payload is not None:
        assert response_payload == payload
    return response_payload


def _request_bound_target(
    context: BolaExecutionContext,
    route_key: RouteKey,
    *,
    actor: BoundActor,
    path_parameters: Mapping[str, str],
    headers: dict[str, str],
    json_body: dict[str, object] | None = None,
) -> Response:
    method, path_template = route_key
    path = path_template.format_map(path_parameters)
    assert "{" not in path and "}" not in path
    context.bound_target_calls.append((actor, route_key))
    return context.client.request(
        method,
        path,
        headers=headers,
        json=json_body,
    )


def _expected_foreign_object_status(route_key: RouteKey) -> int:
    status = CONTRACT_BY_KEY[route_key].foreign_object_status
    assert status is not None
    return int(status)


def _payment_model_snapshot(
    model: type[Subscription] | type[SubscriptionActivationAudit],
) -> PaymentTableSnapshot:
    session_factory = core_db.get_session_factory()
    session = session_factory()
    try:
        primary_key_columns = tuple(model.__table__.primary_key.columns)
        rows = session.execute(select(model).order_by(*primary_key_columns)).scalars().all()
        column_names = tuple(column.key for column in model.__table__.columns)
        serialized_rows: tuple[PaymentRow, ...] = tuple(
            tuple(
                (column_name, deepcopy(getattr(row, column_name))) for column_name in column_names
            )
            for row in rows
        )
        return model.__tablename__, serialized_rows
    finally:
        session.close()


def _payment_state_snapshot() -> PaymentStateSnapshot:
    return (
        _payment_model_snapshot(Subscription),
        _payment_model_snapshot(SubscriptionActivationAudit),
    )


def _restaurant_state_snapshot() -> RestaurantStateSnapshot:
    with pro_restaurant_partner._ISSUER_LOCK:  # noqa: SLF001 - test-only auth state oracle
        issuer_by_api_key = deepcopy(pro_restaurant_partner._ISSUER_BY_API_KEY)  # noqa: SLF001
    with restaurant_partner_orders._LOCK:  # noqa: SLF001 - test-only complete state oracle
        return deepcopy(
            {
                "issuer_by_api_key": issuer_by_api_key,
                "orders": restaurant_partner_orders._ORDERS,  # noqa: SLF001
                "create_events": restaurant_partner_orders._CREATE_EVENTS,  # noqa: SLF001
                "confirm_events": restaurant_partner_orders._CONFIRM_EVENTS,  # noqa: SLF001
                "shares": restaurant_partner_orders._SHARES,  # noqa: SLF001
            }
        )


def _manual_activation_request(*, suffix: str) -> ActivateSubscriptionRequest:
    payload = ManualRailIntentRequest.model_validate(
        {
            "source": "swift_manual",
            "plan": "pro_monthly",
            "client_event_id": f"evt-bola-{suffix}",
            "external_txn_id": f"txn-bola-{suffix}",
            "amount_minor": 2999,
            "currency": "BYN",
        }
    )
    return payments_activation.build_manual_intent_request(payload=payload)


def _seed_manual_activation(*, issuer: str, suffix: str) -> str:
    result = payments_activation.activate_subscription(
        issuer=issuer,
        payload=_manual_activation_request(suffix=suffix),
    )
    assert isinstance(result, tuple)
    activation, is_new = result
    assert isinstance(activation, SubscriptionActivationResponse)
    assert is_new is True
    return activation.activation_id


def _assert_distinct_api_key_principals(
    owner_headers: dict[str, str],
    foreign_headers: dict[str, str],
) -> None:
    owner_key = owner_headers["X-API-Key"]
    foreign_key = foreign_headers["X-API-Key"]
    assert owner_key != foreign_key
    assert derive_subject_id_from_api_key(owner_key) != derive_subject_id_from_api_key(foreign_key)
    assert payments_activation.issuer_from_api_key(
        owner_key
    ) != payments_activation.issuer_from_api_key(foreign_key)


def _sample_partner_draft() -> dict[str, object]:
    return {
        "restaurant_id": "resto-bola-001",
        "currency": "usd",
        "fulfillment": "pickup",
        "items": [
            {
                "menu_item_id": "menu-bola-1",
                "title": "BOLA control bowl",
                "qty": 1,
                "unit_price_minor": 1299,
            }
        ],
        "service_fee_minor": 99,
        "delivery_fee_minor": 0,
        "customer_note": "No substitutions",
        "dietary_tags": ["high-protein"],
        "allergens": [],
        "consent": {
            "consent_share_with_partner": True,
            "consent_version": "v1",
        },
        "attribution_source": "pulseplate-bola-v1",
    }


def _create_partner_order(
    context: BolaExecutionContext,
    *,
    event_id: str,
    headers: dict[str, str] | None = None,
) -> str:
    response = context.client.post(
        "/api/v1/pro/restaurants/partner/orders",
        headers=headers or context.pro_headers,
        json={"draft": _sample_partner_draft(), "client_event_id": event_id},
    )
    payload = _assert_json_response(response, status_code=201)
    order_id = payload.get("id")
    assert isinstance(order_id, str) and order_id
    return order_id


def _issue_partner_share(
    context: BolaExecutionContext,
    *,
    order_id: str,
    partner_id: str,
) -> str:
    response = context.client.post(
        f"/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        headers=context.pro_headers,
        json={"partner_id": partner_id, "expires_in_minutes": 60},
    )
    payload = _assert_json_response(response, status_code=201)
    share_id = payload.get("share_id")
    assert isinstance(share_id, str) and share_id
    return share_id


def _establish_restaurant_principal_mappings(
    context: BolaExecutionContext,
    *,
    event_id: str,
) -> None:
    _create_partner_order(
        context,
        event_id=event_id,
        headers=context.vip_headers,
    )
    pro_key = context.pro_headers["X-API-Key"]
    vip_key = context.vip_headers["X-API-Key"]
    with pro_restaurant_partner._ISSUER_LOCK:  # noqa: SLF001 - test-only auth state oracle
        pro_issuer = pro_restaurant_partner._ISSUER_BY_API_KEY.get(pro_key)  # noqa: SLF001
        vip_issuer = pro_restaurant_partner._ISSUER_BY_API_KEY.get(vip_key)  # noqa: SLF001
    assert isinstance(pro_issuer, str) and pro_issuer
    assert isinstance(vip_issuer, str) and vip_issuer
    assert pro_issuer != vip_issuer


def _execute_activation_read(context: BolaExecutionContext, route_key: RouteKey) -> None:
    _assert_distinct_api_key_principals(context.pro_headers, context.vip_headers)
    owner_key = context.pro_headers["X-API-Key"]
    activation_id = _seed_manual_activation(
        issuer=payments_activation.issuer_from_api_key(owner_key),
        suffix="activation-read",
    )

    owner_response = _request_bound_target(
        context,
        route_key,
        actor="owner",
        path_parameters={"activation_id": activation_id},
        headers=context.pro_headers,
    )
    owner_payload = _assert_json_response(owner_response, status_code=200)
    assert owner_payload["activation_id"] == activation_id

    before = _payment_state_snapshot()
    foreign_response = _request_bound_target(
        context,
        route_key,
        actor="foreign",
        path_parameters={"activation_id": activation_id},
        headers=context.vip_headers,
    )
    _assert_json_response(
        foreign_response,
        status_code=_expected_foreign_object_status(route_key),
        payload={
            "status": "error",
            "code": "forbidden",
            "message": "Activation access forbidden",
            "detail": ACTIVATION_ACCESS_FORBIDDEN_DETAIL,
        },
    )
    assert _payment_state_snapshot() == before


def _execute_manual_intent_status(context: BolaExecutionContext, route_key: RouteKey) -> None:
    requester_key = context.manual_billing_headers["X-API-Key"]
    requester_issuer = payments_activation.issuer_from_api_key(requester_key)
    foreign_service_issuer = payments_activation.issuer_from_api_key(MANUAL_FOREIGN_SERVICE_SEED)
    assert requester_issuer != foreign_service_issuer
    owner_intent_id = _seed_manual_activation(
        issuer=requester_issuer,
        suffix="manual-status-owner",
    )
    foreign_intent_id = _seed_manual_activation(
        issuer=foreign_service_issuer,
        suffix="manual-status-foreign",
    )

    owner_response = _request_bound_target(
        context,
        route_key,
        actor="owner",
        path_parameters={"intent_id": owner_intent_id},
        headers=context.manual_billing_headers,
    )
    owner_payload = _assert_json_response(owner_response, status_code=200)
    assert owner_payload["activation_id"] == owner_intent_id

    before = _payment_state_snapshot()
    foreign_response = _request_bound_target(
        context,
        route_key,
        actor="foreign",
        path_parameters={"intent_id": foreign_intent_id},
        headers=context.manual_billing_headers,
    )
    _assert_json_response(
        foreign_response,
        status_code=_expected_foreign_object_status(route_key),
        payload={
            "status": "error",
            "code": "forbidden",
            "message": "Activation access forbidden",
            "detail": "issuer_access_denied",
        },
    )
    assert _payment_state_snapshot() == before


def _execute_restaurant_order_read(context: BolaExecutionContext, route_key: RouteKey) -> None:
    _assert_distinct_api_key_principals(context.pro_headers, context.vip_headers)
    order_id = _create_partner_order(context, event_id="evt-bola-order-read")
    _establish_restaurant_principal_mappings(
        context,
        event_id="evt-bola-order-read-foreign-control",
    )

    owner_response = _request_bound_target(
        context,
        route_key,
        actor="owner",
        path_parameters={"order_id": order_id},
        headers=context.pro_headers,
    )
    owner_payload = _assert_json_response(owner_response, status_code=200)
    assert owner_payload["id"] == order_id

    before = _restaurant_state_snapshot()
    foreign_response = _request_bound_target(
        context,
        route_key,
        actor="foreign",
        path_parameters={"order_id": order_id},
        headers=context.vip_headers,
    )
    _assert_json_response(
        foreign_response,
        status_code=_expected_foreign_object_status(route_key),
        payload={"detail": ORDER_ACCESS_FORBIDDEN_DETAIL},
    )
    assert _restaurant_state_snapshot() == before


def _execute_restaurant_order_confirm(context: BolaExecutionContext, route_key: RouteKey) -> None:
    _assert_distinct_api_key_principals(context.pro_headers, context.vip_headers)
    control_id = _create_partner_order(context, event_id="evt-bola-confirm-control-create")
    target_id = _create_partner_order(context, event_id="evt-bola-confirm-target-create")
    _establish_restaurant_principal_mappings(
        context,
        event_id="evt-bola-confirm-foreign-control",
    )

    owner_response = _request_bound_target(
        context,
        route_key,
        actor="owner",
        path_parameters={"order_id": control_id},
        headers=context.pro_headers,
        json_body={
            "confirmed_by": "owner-control",
            "client_event_id": "evt-bola-confirm-control",
        },
    )
    owner_payload = _assert_json_response(owner_response, status_code=200)
    assert owner_payload["status"] == "confirmed"

    before = _restaurant_state_snapshot()
    foreign_response = _request_bound_target(
        context,
        route_key,
        actor="foreign",
        path_parameters={"order_id": target_id},
        headers=context.vip_headers,
        json_body={
            "confirmed_by": "spoofed-owner",
            "client_event_id": "evt-bola-confirm-foreign-spoof",
            "note": "payload identity must not authorize",
        },
    )
    _assert_json_response(
        foreign_response,
        status_code=_expected_foreign_object_status(route_key),
        payload={"detail": ORDER_ACCESS_FORBIDDEN_DETAIL},
    )
    assert _restaurant_state_snapshot() == before


def _execute_restaurant_handoff_issue(context: BolaExecutionContext, route_key: RouteKey) -> None:
    _assert_distinct_api_key_principals(context.pro_headers, context.vip_headers)
    control_id = _create_partner_order(context, event_id="evt-bola-issue-control-create")
    target_id = _create_partner_order(context, event_id="evt-bola-issue-target-create")
    _establish_restaurant_principal_mappings(
        context,
        event_id="evt-bola-issue-foreign-control",
    )

    owner_response = _request_bound_target(
        context,
        route_key,
        actor="owner",
        path_parameters={"order_id": control_id},
        headers=context.pro_headers,
        json_body={"partner_id": "partner-control", "expires_in_minutes": 60},
    )
    owner_payload = _assert_json_response(owner_response, status_code=201)
    assert owner_payload["order_id"] == control_id

    before = _restaurant_state_snapshot()
    foreign_response = _request_bound_target(
        context,
        route_key,
        actor="foreign",
        path_parameters={"order_id": target_id},
        headers=context.vip_headers,
        json_body={"partner_id": "spoofed-partner-owner", "expires_in_minutes": 60},
    )
    _assert_json_response(
        foreign_response,
        status_code=_expected_foreign_object_status(route_key),
        payload={"detail": SHARE_ACCESS_FORBIDDEN_DETAIL},
    )
    assert _restaurant_state_snapshot() == before


def _execute_restaurant_handoff_status(context: BolaExecutionContext, route_key: RouteKey) -> None:
    _assert_distinct_api_key_principals(context.pro_headers, context.vip_headers)
    order_id = _create_partner_order(context, event_id="evt-bola-status-create")
    share_id = _issue_partner_share(
        context,
        order_id=order_id,
        partner_id="partner-status-owner",
    )
    _establish_restaurant_principal_mappings(
        context,
        event_id="evt-bola-status-foreign-control",
    )

    owner_response = _request_bound_target(
        context,
        route_key,
        actor="owner",
        path_parameters={"share_id": share_id},
        headers=context.pro_headers,
    )
    owner_payload = _assert_json_response(owner_response, status_code=200)
    assert owner_payload["status"] == "active"

    before = _restaurant_state_snapshot()
    foreign_response = _request_bound_target(
        context,
        route_key,
        actor="foreign",
        path_parameters={"share_id": share_id},
        headers=context.vip_headers,
    )
    _assert_json_response(
        foreign_response,
        status_code=_expected_foreign_object_status(route_key),
        payload={"detail": SHARE_ACCESS_FORBIDDEN_DETAIL},
    )
    assert _restaurant_state_snapshot() == before


def _execute_restaurant_handoff_revoke(context: BolaExecutionContext, route_key: RouteKey) -> None:
    _assert_distinct_api_key_principals(context.pro_headers, context.vip_headers)
    control_order_id = _create_partner_order(
        context,
        event_id="evt-bola-revoke-control-create",
    )
    target_order_id = _create_partner_order(
        context,
        event_id="evt-bola-revoke-target-create",
    )
    control_share_id = _issue_partner_share(
        context,
        order_id=control_order_id,
        partner_id="partner-revoke-control",
    )
    target_share_id = _issue_partner_share(
        context,
        order_id=target_order_id,
        partner_id="partner-revoke-target",
    )
    _establish_restaurant_principal_mappings(
        context,
        event_id="evt-bola-revoke-foreign-control",
    )

    owner_response = _request_bound_target(
        context,
        route_key,
        actor="owner",
        path_parameters={"share_id": control_share_id},
        headers=context.pro_headers,
    )
    owner_payload = _assert_json_response(owner_response, status_code=200)
    assert owner_payload["status"] == "revoked"

    before = _restaurant_state_snapshot()
    foreign_response = _request_bound_target(
        context,
        route_key,
        actor="foreign",
        path_parameters={"share_id": target_share_id},
        headers=context.vip_headers,
    )
    _assert_json_response(
        foreign_response,
        status_code=_expected_foreign_object_status(route_key),
        payload={"detail": SHARE_ACCESS_FORBIDDEN_DETAIL},
    )
    assert _restaurant_state_snapshot() == before


BOLA_SCENARIOS: tuple[BolaScenario, ...] = (
    BolaScenario(
        oracle_id="payments.activation.read",
        route_key=("GET", "/api/v1/pro/payments/activations/{activation_id}"),
        execute=_execute_activation_read,
    ),
    BolaScenario(
        oracle_id="payments.manual_intent.status",
        route_key=("GET", "/api/v1/pro/payments/ru-by/reconcile/{intent_id}"),
        execute=_execute_manual_intent_status,
    ),
    BolaScenario(
        oracle_id="restaurant.order.read",
        route_key=("GET", "/api/v1/pro/restaurants/partner/orders/{order_id}"),
        execute=_execute_restaurant_order_read,
    ),
    BolaScenario(
        oracle_id="restaurant.order.confirm",
        route_key=("POST", "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm"),
        execute=_execute_restaurant_order_confirm,
    ),
    BolaScenario(
        oracle_id="restaurant.handoff.issue",
        route_key=(
            "POST",
            "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        ),
        execute=_execute_restaurant_handoff_issue,
    ),
    BolaScenario(
        oracle_id="restaurant.handoff.status",
        route_key=(
            "GET",
            "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        ),
        execute=_execute_restaurant_handoff_status,
    ),
    BolaScenario(
        oracle_id="restaurant.handoff.revoke",
        route_key=(
            "POST",
            "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        ),
        execute=_execute_restaurant_handoff_revoke,
    ),
)


def test_bola_scenario_registry_exactly_covers_finite_v1_contracts() -> None:
    eligible_pairs = {
        (contract.bola_oracle_id, contract.key)
        for contract in API_AUTHZ_CONTRACTS
        if is_bola_v1_eligible_contract(contract)
    }
    scenario_pairs = {(scenario.oracle_id, scenario.route_key) for scenario in BOLA_SCENARIOS}

    assert eligible_pairs
    assert len(scenario_pairs) == len(BOLA_SCENARIOS)
    assert len({scenario.oracle_id for scenario in BOLA_SCENARIOS}) == len(BOLA_SCENARIOS)
    assert len({scenario.route_key for scenario in BOLA_SCENARIOS}) == len(BOLA_SCENARIOS)
    assert scenario_pairs == eligible_pairs


@pytest.mark.parametrize("scenario", BOLA_SCENARIOS, ids=lambda scenario: scenario.oracle_id)
def test_cross_principal_bola_oracle(
    scenario: BolaScenario,
    client: TestClient,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
    manual_billing_headers: dict[str, str],
) -> None:
    context = BolaExecutionContext(
        client=client,
        pro_headers=pro_headers,
        vip_headers=vip_headers,
        manual_billing_headers=manual_billing_headers,
        bound_target_calls=[],
    )
    scenario.execute(context, scenario.route_key)
    assert context.bound_target_calls == [
        ("owner", scenario.route_key),
        ("foreign", scenario.route_key),
    ]

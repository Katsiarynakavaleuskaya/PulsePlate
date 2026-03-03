# -*- coding: utf-8 -*-
"""In-memory partner order store for contract-first restaurant integration.

RU: Временное in-memory хранилище для contract-first фазы (без миграций БД).
EN: Temporary in-memory store for contract-first phase (no DB migrations).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import threading
from typing import Any
from uuid import uuid4

from app.schemas.restaurant_partner import (
    PartnerOrderDraft,
    PartnerOrderItemPreview,
    PartnerOrderPreviewResponse,
    PartnerOrderResponse,
    PartnerOrderStatus,
    PartnerOrderTotals,
)

_LOCK = threading.Lock()
_ORDERS: dict[str, dict[str, Any]] = {}
_CREATE_EVENTS: dict[tuple[str, str], tuple[str, str]] = {}
_CONFIRM_EVENTS: dict[tuple[str, str], tuple[str, str]] = {}


def _utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _payload_hash(payload: dict[str, Any]) -> str:
    """Build deterministic payload hash for idempotency checks."""
    dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _build_preview_items(draft: PartnerOrderDraft) -> list[PartnerOrderItemPreview]:
    """Convert request items to preview rows with computed line totals."""
    items: list[PartnerOrderItemPreview] = []
    for item in draft.items:
        items.append(
            PartnerOrderItemPreview(
                menu_item_id=item.menu_item_id,
                title=item.title,
                qty=item.qty,
                unit_price_minor=item.unit_price_minor,
                line_total_minor=item.qty * item.unit_price_minor,
                note=item.note,
            )
        )
    return items


def _compute_totals(draft: PartnerOrderDraft) -> PartnerOrderTotals:
    """Compute server-side totals from draft items + fees."""
    subtotal = sum(item.qty * item.unit_price_minor for item in draft.items)
    total = subtotal + draft.service_fee_minor + draft.delivery_fee_minor
    return PartnerOrderTotals(
        subtotal_minor=subtotal,
        service_fee_minor=draft.service_fee_minor,
        delivery_fee_minor=draft.delivery_fee_minor,
        total_minor=total,
    )


def preview_order(draft: PartnerOrderDraft) -> PartnerOrderPreviewResponse:
    """Build preview response without persisting order state."""
    return PartnerOrderPreviewResponse(
        restaurant_id=draft.restaurant_id,
        currency=draft.currency,
        fulfillment=draft.fulfillment,
        items=_build_preview_items(draft),
        totals=_compute_totals(draft),
        warnings=[],
    )


def create_order(
    *,
    draft: PartnerOrderDraft,
    client_event_id: str | None,
) -> tuple[PartnerOrderResponse, bool]:
    """Create order or return idempotent replay.

    Returns:
        (order_response, created_new)
    """
    draft_payload = draft.model_dump(mode="json")
    draft_hash = _payload_hash(draft_payload)
    now = _utc_now()

    with _LOCK:
        if client_event_id:
            create_key = (draft.restaurant_id, client_event_id)
            existing = _CREATE_EVENTS.get(create_key)
            if existing is not None:
                existing_order_id, existing_hash = existing
                if existing_hash != draft_hash:
                    raise ValueError("client_event_id conflict: payload mismatch")
                replay = _ORDERS[existing_order_id]
                return PartnerOrderResponse.model_validate(deepcopy(replay)), False

        order_id = str(uuid4())
        preview = preview_order(draft)
        consent_payload = draft.consent.model_dump(mode="json")
        if consent_payload.get("accepted_at_utc") is None:
            consent_payload["accepted_at_utc"] = now.isoformat()
        order_payload: dict[str, Any] = {
            "id": order_id,
            "status": PartnerOrderStatus.pending_partner.value,
            "restaurant_id": preview.restaurant_id,
            "currency": preview.currency,
            "fulfillment": preview.fulfillment.value,
            "items": [item.model_dump(mode="json") for item in preview.items],
            "totals": preview.totals.model_dump(mode="json"),
            "customer_note": draft.customer_note,
            "dietary_tags": draft.dietary_tags,
            "allergens": draft.allergens,
            "consent": consent_payload,
            "attribution_source": draft.attribution_source,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "confirmed_at": None,
            "confirmed_by": None,
            "version": 1,
        }
        _ORDERS[order_id] = order_payload

        if client_event_id:
            _CREATE_EVENTS[(draft.restaurant_id, client_event_id)] = (order_id, draft_hash)

        created = PartnerOrderResponse.model_validate(deepcopy(order_payload))
        return created, True


def get_order(order_id: str) -> PartnerOrderResponse | None:
    """Return stored order by ID."""
    with _LOCK:
        payload = _ORDERS.get(order_id)
        if payload is None:
            return None
        return PartnerOrderResponse.model_validate(deepcopy(payload))


def confirm_order(
    *,
    order_id: str,
    confirmed_by: str,
    client_event_id: str | None,
    note: str | None,
) -> tuple[PartnerOrderResponse, bool]:
    """Confirm pending order with idempotent replay support.

    Returns:
        (order_response, changed_state)
    """
    confirm_payload = {
        "order_id": order_id,
        "confirmed_by": confirmed_by,
        "note": note,
    }
    confirm_hash = _payload_hash(confirm_payload)

    with _LOCK:
        payload = _ORDERS.get(order_id)
        if payload is None:
            raise KeyError("order not found")

        if client_event_id:
            confirm_key = (order_id, client_event_id)
            existing = _CONFIRM_EVENTS.get(confirm_key)
            if existing is not None:
                _, existing_hash = existing
                if existing_hash != confirm_hash:
                    raise ValueError("client_event_id conflict: confirm payload mismatch")
                return PartnerOrderResponse.model_validate(deepcopy(payload)), False

        current = payload["status"]
        if current != PartnerOrderStatus.pending_partner.value:
            raise RuntimeError("invalid transition: only pending_partner can be confirmed")

        now = _utc_now().isoformat()
        payload["status"] = PartnerOrderStatus.confirmed.value
        payload["confirmed_at"] = now
        payload["confirmed_by"] = confirmed_by
        payload["updated_at"] = now
        payload["version"] = int(payload.get("version", 1)) + 1
        if note:
            payload["customer_note"] = note

        if client_event_id:
            _CONFIRM_EVENTS[(order_id, client_event_id)] = (order_id, confirm_hash)

        return PartnerOrderResponse.model_validate(deepcopy(payload)), True


def reset_state() -> None:
    """Reset in-memory store for deterministic tests."""
    with _LOCK:
        _ORDERS.clear()
        _CREATE_EVENTS.clear()
        _CONFIRM_EVENTS.clear()

# -*- coding: utf-8 -*-
"""In-memory partner order store for contract-first restaurant integration.

RU: Временное in-memory хранилище для contract-first фазы (без миграций БД).
EN: Temporary in-memory store for contract-first phase (no DB migrations).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import threading
from typing import Any
from uuid import uuid4

from app.schemas.restaurant_partner import (
    PartnerOrderDraft,
    PartnerHandoffShareResponse,
    PartnerHandoffShareStatus,
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
_SHARES: dict[str, dict[str, Any]] = {}


class OrderNotFoundError(KeyError):
    """Raised when partner flow references unknown order."""


class ShareNotFoundError(KeyError):
    """Raised when handoff share is missing."""


class PartnerConsentRequiredError(PermissionError):
    """Raised when partner handoff consent is missing."""


class ShareRevokedError(PermissionError):
    """Raised when handoff share is revoked."""


class ShareExpiredError(TimeoutError):
    """Raised when handoff share is expired."""


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
                replay_response: PartnerOrderResponse = PartnerOrderResponse.model_validate(
                    deepcopy(replay)
                )
                return replay_response, False

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
        order: PartnerOrderResponse = PartnerOrderResponse.model_validate(deepcopy(payload))
        return order


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
                replay_response: PartnerOrderResponse = PartnerOrderResponse.model_validate(
                    deepcopy(payload)
                )
                return replay_response, False

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

        confirmed_response: PartnerOrderResponse = PartnerOrderResponse.model_validate(
            deepcopy(payload)
        )
        return confirmed_response, True


def reset_state() -> None:
    """Reset in-memory store for deterministic tests."""
    with _LOCK:
        _ORDERS.clear()
        _CREATE_EVENTS.clear()
        _CONFIRM_EVENTS.clear()
        _SHARES.clear()


def issue_handoff_share(
    *,
    order_id: str,
    issuer: str,
    partner_id: str,
    expires_in_minutes: int,
) -> PartnerHandoffShareResponse:
    """Issue consent-based partner handoff share with audit fields."""
    with _LOCK:
        order_payload = _ORDERS.get(order_id)
        if order_payload is None:
            raise OrderNotFoundError("order not found")

        consent_payload = order_payload.get("consent") or {}
        if not bool(consent_payload.get("consent_share_with_partner")):
            raise PartnerConsentRequiredError("partner consent required")
        if expires_in_minutes <= 0:
            raise ValueError("expires_in_minutes must be > 0")

        now = _utc_now()
        expires_at = now + timedelta(minutes=expires_in_minutes)
        share_id = str(uuid4())

        share_payload: dict[str, Any] = {
            "share_id": share_id,
            "order_id": order_id,
            "issuer": issuer,
            "partner_id": partner_id,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "revoked_at": None,
            "status": PartnerHandoffShareStatus.active.value,
        }
        _SHARES[share_id] = share_payload
        # Keep order updated for audit trace in contract-first seam.
        order_payload["updated_at"] = now.isoformat()

        issued_response: PartnerHandoffShareResponse = PartnerHandoffShareResponse.model_validate(
            deepcopy(share_payload)
        )
        return issued_response


def get_handoff_share_status(share_id: str) -> PartnerHandoffShareResponse:
    """Read handoff share status with fail-closed revoked/expired behavior."""
    with _LOCK:
        payload = _SHARES.get(share_id)
        if payload is None:
            raise ShareNotFoundError("share not found")

        if payload.get("revoked_at") is not None:
            payload["status"] = PartnerHandoffShareStatus.revoked.value
            raise ShareRevokedError("share revoked")

        expires_at = datetime.fromisoformat(payload["expires_at"])
        if expires_at <= _utc_now():
            payload["status"] = PartnerHandoffShareStatus.expired.value
            raise ShareExpiredError("share expired")

        payload["status"] = PartnerHandoffShareStatus.active.value
        status_response: PartnerHandoffShareResponse = PartnerHandoffShareResponse.model_validate(
            deepcopy(payload)
        )
        return status_response


def revoke_handoff_share(share_id: str) -> PartnerHandoffShareResponse:
    """Revoke handoff share (idempotent)."""
    with _LOCK:
        payload = _SHARES.get(share_id)
        if payload is None:
            raise ShareNotFoundError("share not found")

        if payload.get("revoked_at") is None:
            payload["revoked_at"] = _utc_now().isoformat()
        payload["status"] = PartnerHandoffShareStatus.revoked.value

        revoked_response: PartnerHandoffShareResponse = PartnerHandoffShareResponse.model_validate(
            deepcopy(payload)
        )
        return revoked_response

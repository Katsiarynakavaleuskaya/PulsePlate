from __future__ import annotations

# Shared client-facing error details for sanitized HTTP responses.
# These values are part of the stable response contract and must stay
# consistent across routers, legacy shims, and tests.

INVALID_WEEKLY_PLAN_ADAPTER_PAYLOAD_DETAIL = "invalid_weekly_plan_adapter_payload"
CREATE_ORDER_CONFLICT_DETAIL = "client_event_id conflict: payload mismatch"
ORDER_ACCESS_FORBIDDEN_DETAIL = "order access forbidden"
ORDER_GONE_DETAIL = "order gone"
CONFIRM_ORDER_CONFLICT_DETAIL = "client_event_id conflict: confirm payload mismatch"
INVALID_ORDER_TRANSITION_DETAIL = "invalid transition"
SHARE_ACCESS_FORBIDDEN_DETAIL = "share access forbidden"
PARTNER_CONSENT_REQUIRED_DETAIL = "partner consent required"
INVALID_HANDOFF_PAYLOAD_DETAIL = "invalid_handoff_payload"
SHARE_REVOKED_DETAIL = "share revoked"
SHARE_EXPIRED_DETAIL = "share expired"

TRANSPORT_AUTH_REQUIRED_DETAIL = "transport_auth_required"
DETERMINISTIC_ACTIVATION_CONFLICT_DETAIL = "deterministic_activation_conflict"
ACTIVATION_ACCESS_FORBIDDEN_DETAIL = "activation_access_forbidden"
BILLING_SIGNATURE_INVALID = "BILLING_SIGNATURE_INVALID"

INVALID_SUBMISSION_DETAIL = "Invalid submission"
INVALID_SUBMISSION_TRANSITION_DETAIL = "Invalid submission transition"
MALFORMED_BARCODE_DETAIL = "Malformed barcode"
INVALID_BMI_INPUT_DETAIL = "Invalid BMI input"

INVALID_PREMIUM_PLATE_INPUT_DETAIL = "Invalid premium plate input"
ENHANCED_PLATE_GENERATION_FAILED_DETAIL = "Enhanced plate generation failed"

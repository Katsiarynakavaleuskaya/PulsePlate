# Security Audit Report: PR #1185 (feat/billing) Apple Verify Activation Contract

**Branch:** feat/b2-apple-verify-activation-contract
**Scope:** `app/schemas/payments.py`, `app/services/payments_activation.py`, `app/routers/billing.py`, `app/routers/pro_payments.py`, tests, docs
**Auditor:** security-auditor agent
**Date:** 2026-03-17

---

## Executive Summary

The PR normalizes Apple receipt verification response into the activation contract (`IOSVerifiedActivationResult`). The originally identified critical/high/medium findings are now closed on-branch: iOS activation re-verifies `receipt_data` server-side before persistence, the Apple verify route is rate-limited, and receipt-size bounds are enforced in both verify and activate schemas. The remaining informational finding is explicitly accepted as not-a-bug because the contract exposes transaction metadata only, not raw receipts or provider secrets.

---

## Critical Vulnerabilities (P0)

### [VULN-001] Activation Endpoint Trusts Client-Provided Verification Result Without Re-Verification

**Status:** FIXED

| Field | Value |
|-------|-------|
| **Location** | `app/services/payments_activation.py:315-365`, `app/services/payments_activation.py:490-495` |
| **Severity** | Critical |
| **CVSS** | 9.1 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N) |
| **Attack Vector** | Attacker with valid PRO API key can forge `IOSVerifiedActivationResult` and activate subscription without valid Apple purchase |

**Description:**
The `activate_subscription` flow for `ios_app_store` accepts `IOSAppStoreActivationPayload` containing `verification_result` (client-provided) and `receipt_data`. The server uses `verification_result` directly in `_normalize_canonical_ios_activation` without re-verifying the receipt with Apple. An attacker can:

1. Obtain a valid PRO API key (e.g., via legitimate subscription or leaked key)
2. Call `POST /api/v1/pro/payments/activate` with forged payload:
   ```json
   {
     "source": "ios_app_store",
     "payload": {
       "verification_result": {
         "transaction_id": "forged-txn-123",
         "original_transaction_id": "forged-orig-123",
         "product_id": "com.pulseplate.premium.monthly",
         "subscription_tier": "pro",
         "status": "active",
         "expires_at": "2030-01-01T00:00:00Z",
         "platform": "ios"
       },
       "receipt_data": "any-base64-string"
     }
   }
   ```
3. Receive a persisted subscription activation.

**Evidence:**

```python
# app/services/payments_activation.py:315-365
def _normalize_canonical_ios_activation(
    *,
    payload: ActivateSubscriptionRequest,
    verification_result: IOSVerifiedActivationResult,  # client-provided, not re-verified
) -> NormalizedActivation:
    ...
    tier=verification_result.subscription_tier,  # trusted from client
    status=SubscriptionStatus(verification_result.status.value),
```

```python
# app/services/payments_activation.py:490-495
# activation uses payload.get_ios_payload().verification_result directly
verification_result=payload.get_ios_payload().verification_result,
```

**Remediation Applied:**
- Server-side re-verification now happens inside `activate_subscription_async()`: the handler reads `payload.receipt_data`, calls `verify_apple_receipt(receipt_data)`, rejects when `activation_payload is None`, and persists only the server-verified contract (`app/services/payments_activation.py`).
- Regression coverage rejects a forged `verification_result` paired with invalid `receipt_data` (`tests/test_subscription_activation_api.py`).

**Testing:** Add test that sends forged `verification_result` with invalid receipt and asserts 403 or rejection.

---

## High Vulnerabilities (P1)

### [VULN-002] No Rate Limiting on Apple Verify Endpoint

**Status:** FIXED

| Field | Value |
|-------|-------|
| **Location** | `app/routers/billing.py:218-239` |
| **Severity** | High |
| **Attack Vector** | DoS via repeated requests to Apple API; cost amplification (Apple API calls per request) |

**Description:**
`POST /api/v1/billing/apple/verify-receipt` has no `@limit_if_available(RATE_LIMIT_*)`. Each request triggers an outbound call to Apple’s verifyReceipt API. An attacker can exhaust Apple API quota or cause DoS.

**Evidence:**

```python
# app/routers/billing.py:218-239
@billing_router.post("/apple/verify-receipt", ...)
async def verify_apple_receipt(
    payload: AppleReceiptVerificationRequest,
    _x_api_key: str = Depends(_require_billing_transport_key),
) -> AppleReceiptVerificationResponse | JSONResponse:
    # No rate limit decorator
```

**Remediation Applied:**
`POST /api/v1/billing/apple/verify-receipt` now uses `@limit_if_available(RATE_LIMIT_APPLE_VERIFY)` and advertises 429 responses in OpenAPI (`app/routers/billing.py`, `app/security/rate_limit.py`).

**Note:** AGENTS.md mandates rate limiting for LLM and export endpoints; Apple verify is a similar cost/DoS vector and should be rate-limited.

---

## Medium Vulnerabilities (P2)

### [VULN-003] No Max Length on Receipt Data (DoS / Memory)

**Status:** FIXED

| Field | Value |
|-------|-------|
| **Location** | `app/schemas/payments.py:276-286`, `app/schemas/payments.py:167` |
| **Severity** | Medium |
| **Attack Vector** | Large `receipt_data` payloads cause memory pressure or upstream Apple API abuse |

**Description:**
`AppleReceiptVerificationRequest.receipt_data` and `IOSAppStoreActivationPayload.receipt_data` have `min_length=8` (or `min_length=1`) but no `max_length`. Apple receipts are typically under 100KB; unbounded input can cause DoS.

**Evidence:**

```python
# app/schemas/payments.py:276-286
receipt_data: str = Field(
    ...,
    min_length=8,
    # No max_length
)
```

**Remediation Applied:**
Both `AppleReceiptVerificationRequest.receipt_data` and `IOSAppStoreActivationPayload.receipt_data` now enforce `max_length=512_000`, with API tests covering 422 rejection for oversized receipts on verify and activate (`app/schemas/payments.py`, `tests/test_ios_receipt_verification_api.py`, `tests/test_subscription_activation_api.py`).

---

### [VULN-004] Sensitive Data in IOSVerifiedActivationResult

**Status:** NOT-A-BUG

| Field | Value |
|-------|-------|
| **Location** | `app/schemas/payments.py:125-161` |
| **Severity** | Low (informational) |
| **Risk** | Low |

**Description:**
`IOSVerifiedActivationResult` exposes: `transaction_id`, `original_transaction_id`, `product_id`, `subscription_tier`, `status`, `expires_at`, `platform`. No raw receipt or secrets. Exposure risk is low; these are transaction identifiers for activation flow.

**Recommendation:** No change required; continue to avoid exposing raw receipt or Apple tokens.

---

## Verified Invariants

### 1. No Alias Route Under `/api/v1/pro/payments/apple/*`

**Evidence:** `tests/test_billing_openapi_contract.py:27` asserts `/api/v1/pro/payments/apple/verify-receipt` is not in OpenAPI paths. Baseline forbids this alias.

### 2. Server-Side Verify-Only Invariant

**Evidence:** `app/services/payments_activation.py:1119-1120` — `verify_apple_receipt` calls Apple server-side. `activation_payload` is built from Apple’s response in `_build_activation_contract_from_entry`; tier is derived from `product_id` via `_subscription_tier_for_product`, not from client input. **Caveat:** The verify endpoint itself is correct; the activation endpoint trusts client-provided verification_result without re-verification (see VULN-001).

### 3. Webhook Signature Validation

**Evidence:** `app/services/payments_activation.py:135-167` — `validate_webhook_signature()` uses HMAC-SHA256, `hmac.compare_digest`, and fail-closed behavior. Covered by `test_payment_webhook_signature_api.py`.

### 4. Credential Handling

**Evidence:** `APPLE_SHARED_SECRET` is required via `require_apple_shared_secret()` in `settings.py`. Used in `_apple_request_body` (`payments_activation.py:722-727`) and not logged.

### 5. Billing Transport Key Required

**Evidence:** `app/routers/billing.py:237` — `_require_billing_transport_key` enforces API key for verify endpoint.

---

## Recommendations

| Priority | Action |
|----------|--------|
| Closed | VULN-001: iOS activation now re-verifies with Apple before persistence |
| Closed | VULN-002: Apple verify route now has rate limiting and 429 OpenAPI docs |
| Closed | VULN-003: `receipt_data` fields now enforce `max_length=512_000` |

---

## Trivial Fixes Applied

- **Receipt max_length (VULN-003):** Added `max_length=512_000` to `AppleReceiptVerificationRequest.receipt_data` (`app/schemas/payments.py:279`) and `IOSAppStoreActivationPayload.receipt_data` (`app/schemas/payments.py:167`) to mitigate DoS risk. Evidence: `app/schemas/payments.py`.

---

## Files Audited

| File | Lines Reviewed |
|------|----------------|
| `app/schemas/payments.py` | 125-340, 368-430 |
| `app/services/payments_activation.py` | 135-167, 315-365, 490-495, 722-727, 1084-1120 |
| `app/routers/billing.py` | 195-240 |
| `app/routers/pro_payments.py` | 1-150 |
| `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md` | Full |
| `tests/test_billing_openapi_contract.py` | 27 |
| `tests/test_ios_receipt_verification_api.py` | Sample |
| `tests/test_subscription_activation_api.py` | 60-90 |

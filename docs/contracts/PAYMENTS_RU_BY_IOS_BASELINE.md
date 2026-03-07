# Payments RU/BY + iOS Baseline Contract

- Status: Contract-first (docs-only), runtime implementation follows in dedicated PRs.
- Owner: `@katsiaryna_kavaleuskaya`
- Canonical dependency: `docs/contracts/PRODUCT_TIER_MAP.md`
- Program phase: P0 revenue continuity baseline.
- ADR: `docs/architecture/ADR_PAYMENTS_RU_BY_IOS_BASELINE_2026-03-05.md`
- Backlog SoT: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`

## 1. Canonical Payment Sources

```text
ios_app_store
erip_qr
swift_manual
```

Rules:
1. Payment source is immutable per transaction record (evidence: `docs/audit/PR_PAYMENTS_RUBY_IOS_CONTRACT_AUDIT.md:9`).
2. Any source-specific payload must normalize into one canonical activation decision (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:32`).
3. Manual rails (`erip_qr`, `swift_manual`) require reconciliation status lifecycle and explicit audit events (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:63`, `docs/audit/PR_PAYMENTS_RUBY_IOS_CONTRACT_AUDIT.md:14`).

## 2. Canonical API Surface (additive, non-breaking)

Planned endpoints (contract-first; final path lock happens in runtime PR):

1. `POST /api/v1/pro/payments/apple/verify-receipt`
2. `POST /api/v1/pro/payments/ru-by/manual-intent`
3. `POST /api/v1/pro/payments/ru-by/reconcile`
4. `GET /api/v1/pro/payments/ru-by/reconcile/{intent_id}`

Legacy behavior remains unchanged until runtime migration is merged.

## 3. Activation Contract (`activate_subscription`)

Input envelope (source-specific payload inside one canonical contract):

```json
{
  "user_id": "uuid",
  "source": "ios_app_store | erip_qr | swift_manual",
  "plan": "pro_monthly | vip_monthly",
  "verification_payload": {
    "receipt": "...",
    "external_txn_id": "...",
    "amount_minor": 999,
    "currency": "USD"
  }
}
```

Output envelope (source-agnostic):

```json
{
  "status": "activated | pending_reconciliation | rejected",
  "subscription_tier": "pro | vip",
  "source": "ios_app_store | erip_qr | swift_manual",
  "audit_id": "uuid",
  "effective_at": "ISO-8601",
  "reason_code": "optional"
}
```

`subscription_tier` reflects the requested paid tier implied by `plan`, not a fallback effective access tier.

## 4. Reconciliation Status Lifecycle

For manual rails (`erip_qr`, `swift_manual`):

```text
draft_intent -> pending_reconciliation -> verified -> activated
                                 \-> rejected
```

Lifecycle invariants:
1. `verified` can be reached only with immutable `external_txn_id` and evidence payload.
2. `activated` is idempotent for identical `(user_id, source, external_txn_id, plan)`.
3. Reconcile retry is safe and cannot duplicate entitlements.

## 5. Webhook/Signature and Idempotency Contract

1. iOS verification path is automated and server-side validated.
2. Any webhook/event handler must validate signature before state transition.
3. Idempotency key precedence:
   - provider event id (if exists), else
   - deterministic hash of `(source, external_txn_id, plan, amount_minor, currency)`.
4. Duplicate events return previous activation outcome (no double-upgrade).
5. Corrections/refunds must use a new provider event id and explicit adjustment type; they must not overwrite prior activation event identity.

## 6. Error Envelope (canonical)

```json
{
  "status": "error",
  "code": "BILLING_VALIDATION_ERROR | BILLING_RECONCILE_PENDING | BILLING_DUPLICATE_EVENT | BILLING_SIGNATURE_INVALID",
  "detail": "human-readable message",
  "request_id": "uuid"
}
```

Semantic note:
1. In activation responses, `status` is business-state (`activated | pending_reconciliation | rejected`).
2. In error responses, `status` is transport-state (`error`), while `code` is machine-readable error type.

## 7. Security and Compliance Notes

1. Do not store raw payment credentials in app DB.
2. Retain only minimum proof fields for reconciliation and audit.
3. Manual rails have increased fraud risk; require reviewer/audit trace.
4. Keep Apple digital-goods policy compliance in scope for iOS rails.
5. RU/BY manual rails are operational fallback, not anonymous bypass path.

## 8. Runtime Test Plan (must be green in runtime PR)

1. `tests/test_payment_source_contract_api.py`
2. `tests/test_subscription_activation_api.py`
3. `tests/test_ios_receipt_verification_api.py`
4. `tests/test_payment_webhook_signature_api.py`
5. `tests/test_payment_reconciliation_api.py`

Required runtime PR gates:
- `make openapi`
- `make openapi-check`
- `make verify`

## 9. Rollout / Backward Compatibility

1. Keep existing client contracts intact while additive billing routes roll out.
2. Feature-flag runtime activation paths until reconciliation flow is validated on staging.
3. Promote manual rails only after deterministic reconciliation tests are stable.

## 10. Backlog / Action Items (temporary seam control)

1. Primary implementation track: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`.
2. Apple verify runtime path: `PR-TBD-BILLING-APPLE-VERIFY`.
3. iOS subscription manager integration path: `PR-TBD-IOS-SUBSCRIPTION-MANAGER`.
4. Blockers before completion:
   - runtime handlers are not merged yet,
   - reconciliation tests are not merged yet,
   - OpenAPI billing surfaces are not yet generated from runtime code.

## 11. Exit Criteria

1. Runtime implementation PR for `#ledger-p0-payments-ruby-ios` is merged.
2. Runtime tests listed in section 8 are green in CI.
3. `make openapi` + `make openapi-check` + `make verify` pass on runtime billing PR.
4. Backlog item state is updated from in-progress to done with merge evidence.

## 12. Runtime W1 Namespace Lock

1. Runtime billing surfaces live under `/api/v1/pro/payments/*` to respect the
   canonical public namespace policy (`/api/v1/bmi`, `/api/v1/pro`, `/api/v1/vip`).
2. Earlier docs-only drafts used `/api/v1/billing/*`; that path is not canonical
   under the current namespace guards and must not be reintroduced.

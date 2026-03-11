# ADR: Payments RU/BY + iOS Baseline (Contract-First)

- Date: 2026-03-05
- Status: Accepted (docs contract), runtime pending
- Owners: `@katsiaryna_kavaleuskaya`

## Context

PulsePlate monetization must support the current operational reality:
1. iOS automated billing path.
2. RU/BY manual rails (`eRIP QR`, `SWIFT manual`) as supported fallback.
3. Non-breaking rollout with deterministic reconciliation and auditability.

## Decision

1. Canonical payment source model is fixed to `ios_app_store`, `erip_qr`, `swift_manual` (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:12`, `docs/contracts/API_CANONICAL_MAP.md:40`).
2. Billing runtime rollout is additive via canonical `/api/v1/pro/payments/*` endpoints (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`, `docs/contracts/API_CANONICAL_MAP.md:49`, `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`).
3. Activation contract remains source-agnostic (`activate_subscription` normalized decision) (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:34`, `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:52`).
4. Manual rails require explicit reconciliation lifecycle before entitlement activation (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:65`, `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:75`).

## Consequences

1. Runtime implementation is split into dedicated PRs; this ADR acts as seam control (evidence: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`).
2. iOS/Web remain thin clients: transport only, no billing decision logic on clients (evidence: `docs/IOS_API_INTEGRATION.md:113`).
3. Deferred global/Android rails are tracked in backlog, not mixed into this baseline wave (evidence: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`).

## Exit Criteria (seam removal)

1. Runtime billing contract PR merged with deterministic tests:
   - `test_payment_source_contract_api`
   - `test_subscription_activation_api`
   - `test_ios_receipt_verification_api`
   - `test_payment_webhook_signature_api`
   - `test_payment_reconciliation_api`
2. `make openapi`, `make openapi-check`, `make verify` pass for runtime PR.
3. Reconciliation status transitions and idempotency behavior are verified in CI.
4. Backlog item `#ledger-p0-payments-ruby-ios` moves from in-progress to done with merged runtime PR link.

## Backlog Linkage

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`

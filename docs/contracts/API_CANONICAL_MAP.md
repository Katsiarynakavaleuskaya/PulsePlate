# API Canonical Map

**Status:** Canonical baseline (PR-508)
**Source of truth:** OpenAPI generated from `app.main.app` (see `scripts/generate_openapi.py`)

## Rules

1. **Canonical contracts live in backend OpenAPI**.
2. Frontend + iOS **generate types/models from OpenAPI** (no manual duplication).
3. Legacy `/api/v1/premium/*` endpoints are **compatibility aliases** (deprecated).

## Canonical vs Compat Endpoints (as of PR-508)

| Feature | Canonical endpoint | Method | Compat (legacy) endpoint | Method | Notes |
|---|---|---:|---|---:|---|
| Targets | (missing) `/api/v1/pro/nutrition/targets` | POST | `/api/v1/premium/targets` | POST | Canonical endpoint does not exist yet. Implement in PR-509. |
| Daily / Plate | `/api/v1/pro/nutrition/daily` | GET | `/api/v1/premium/plate` | POST | Compat differs by method. Long-term: FE/iOS move to canonical GET. |
| Weekly Plan | `/api/v1/pro/meal/weekly` | POST | `/api/v1/premium/plan/week` | POST | Compat delegates to canonical (policy). |
| BMR | `/api/v1/premium/bmr` | POST | (same) | POST | BMR endpoint is stable; no migration needed. |

## Non-goals for PR-508

- Do not add new product logic or new endpoints.
- Keep business rules unchanged (behavior must remain identical).
- Do not refactor legacy entrypoints (`app:app` -> `app.main:app`) in this PR.

## Follow-up PRs (vertical slices)

- **PR-509:** Implement `/api/v1/pro/nutrition/targets` + compat alias behavior and contract tests.
- **PR-510:** Align Plate/Daily contracts and FE usage; keep compat.
- **PR-511:** Type WeekPlan response models (if needed) + contract tests + FE adjustments.

## Payments Canonical Map (P0 baseline, implemented in PR #999)

Source of truth for implemented payment baseline:
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:21`
- `docs/audit/PR_PAYMENTS_RUBY_IOS_CONTRACT_AUDIT.md:9`
- `docs/architecture/ADR_PAYMENTS_RU_BY_IOS_BASELINE_2026-03-05.md:37`
- `app/routers/billing.py:94`
- `app/schemas/payments.py:61`
- `app/services/payments_activation.py:194`
- `app/main.py:29`

Canonical source enum:
- `ios_app_store`
- `erip_qr`
- `swift_manual`

Implemented additive endpoints (non-breaking):

| Feature | Canonical endpoint | Method | Compat (legacy) endpoint | Method | Notes | Ledger |
|---|---|---:|---|---:|---|---|
| Apple receipt verification | `/api/v1/pro/payments/apple/verify-receipt` | POST | none (new) | - | Implemented automated iOS verification baseline with deterministic activation contract | `#ledger-p0-payments-ruby-ios` (owner: @katsiaryna_kavaleuskaya, P0, target: `PR #999`) |
| RU/BY payment intent | `/api/v1/pro/payments/ru-by/manual-intent` | POST | none (new) | - | Implemented manual payment intent creation with pending reconciliation lifecycle | `#ledger-p0-payments-ruby-ios` (DoD: reconciliation lifecycle + non-breaking contract) |
| RU/BY reconciliation | `/api/v1/pro/payments/ru-by/reconcile` | POST | none (new) | - | Implemented deterministic reconcile transition for manual rails | `#ledger-p0-payments-ruby-ios` (DoD: deterministic audit + status lifecycle) |
| RU/BY reconciliation status | `/api/v1/pro/payments/ru-by/reconcile/{intent_id}` | GET | none (new) | - | Implemented read-only manual lifecycle status surface | `#ledger-p0-payments-ruby-ios` (OpenAPI + runtime verified) |

Compatibility policy:
1. Existing PRO/VIP activation flows remain backward-compatible; payment routes are additive.
2. Payment routes are additive and must preserve current response envelopes for unchanged endpoints.
3. iOS/Web clients remain thin adapters; no client-side billing decision logic.
4. Runtime payment surfaces must stay under `/api/v1/pro/*` to satisfy namespace guard policy.
5. Runtime handlers exist under the canonical PRO namespace and are verified by OpenAPI/tests.
6. Evidence anchors for these assertions are captured in:
   - `app/routers/billing.py:94`
   - `app/services/payments_activation.py:194`
   - `tests/test_billing_openapi_contract.py:11`
   - `tests/test_payment_source_contract_api.py:113`
   - `tests/test_payment_reconciliation_api.py:53`

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

## Payments Canonical Map (P0 baseline, contract-first)

Source of truth for planned payment baseline:
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:1`
- `docs/audit/PR_PAYMENTS_RUBY_IOS_CONTRACT_AUDIT.md:1`
- `docs/architecture/ADR_PAYMENTS_RU_BY_IOS_BASELINE_2026-03-05.md:1`

Canonical source enum:
- `ios_app_store`
- `erip_qr`
- `swift_manual`

Planned additive endpoints (non-breaking; finalized in runtime PR):

| Feature | Canonical endpoint | Method | Compat (legacy) endpoint | Method | Notes | Ledger |
|---|---|---:|---|---:|---|---|
| Apple receipt verification | `/api/v1/pro/payments/apple/verify-receipt` | POST | none (new) | - | Automated iOS path; server-side verification | `#ledger-p0-payments-ruby-ios` (owner: @katsiaryna_kavaleuskaya, P0, target: `PR-TBD-PAYMENTS-RUBY-IOS-BASELINE`) |
| RU/BY payment intent | `/api/v1/pro/payments/ru-by/manual-intent` | POST | none (new) | - | Creates manual payment intent and reconciliation state | `#ledger-p0-payments-ruby-ios` (DoD: reconciliation lifecycle + non-breaking contract) |
| RU/BY reconciliation | `/api/v1/pro/payments/ru-by/reconcile` | POST | none (new) | - | Manual review/system reconciliation endpoint | `#ledger-p0-payments-ruby-ios` (DoD: deterministic audit + status lifecycle) |
| RU/BY reconciliation status | `/api/v1/pro/payments/ru-by/reconcile/{intent_id}` | GET | none (new) | - | Read-only status lifecycle surface | `#ledger-p0-payments-ruby-ios` (implemented in active runtime PR; merge pending) |

Compatibility policy:
1. Existing PRO/VIP activation flows remain unchanged until runtime migration PR.
2. Payment routes are additive and must preserve current response envelopes for unchanged endpoints.
3. iOS/Web clients remain thin adapters; no client-side billing decision logic.
4. Runtime payment surfaces must stay under `/api/v1/pro/*` to satisfy namespace guard policy.
5. This section is implementation-target contract guidance, not a statement that runtime handlers already exist in `app/routers/*`.
6. Evidence anchors for these assertions are captured in:
   - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:21`
   - `docs/audit/PR_PAYMENTS_RUBY_IOS_CONTRACT_AUDIT.md:9`

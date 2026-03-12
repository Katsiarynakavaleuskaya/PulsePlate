# API Canonical Map

**Status:** Canonical operator map (docs sync baseline, 2026-03-08)

## Source of truth

Use these sources in order:

1. Backend OpenAPI generated from `app.main.app` for routes currently exposed in schema
2. `docs/contracts/PRODUCT_TIER_MAP.md` for tier and namespace semantics
3. `docs/contracts/OPENAPI_PATHS_AUDIT.md` for historical audit evidence
4. `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`, `app/routers/billing.py:215`, and `legacy_app.py:709` for the additive Apple verify seam `/api/v1/billing/apple/verify-receipt`
5. `docs/roadmap/BACKLOG_LEDGER.md` for planned or deferred target-state work

Billing evidence note:
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27` is the contract lock for the additive Apple verify seam, runtime exposure is implemented in `app/routers/billing.py:215`, OpenAPI exposure is gated in `legacy_app.py:709`, and the temporary seam exit remains tracked in `docs/architecture/ADR_PAYMENTS_RU_BY_IOS_BASELINE_2026-03-05.md:27` plus `docs/roadmap/BACKLOG_LEDGER.md:61`.

## Rules

1. Repo-wide canonical namespaces are `/api/v1/bmi/*` (FREE), `/api/v1/pro/*` (PRO), and `/api/v1/vip/*` (VIP); `/api/v1/insight` and the additive Apple verify seam `/api/v1/billing/apple/verify-receipt` are canonical exceptions outside the tier namespace families (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`, `app/routers/billing.py:215`, `legacy_app.py:709`, `docs/roadmap/BACKLOG_LEDGER.md:61`).
2. `/api/v1/premium/*` is a compatibility surface only. It is not a separate product tier and must delegate to canonical paths when a canonical replacement exists.
3. Planned routes must stay marked as planned or additive until runtime rollout and OpenAPI exposure are real.
4. README may summarize capability areas, but this file is the operator-facing route map.
5. Web and iOS remain thin adapters and must not invent alternative route semantics.
6. FitChef umbrella foundation work must preserve the live `/api/v1/insight/fitchef*` canon until a dedicated additive contract PR promotes future structured-coach paths.

## Canonical Runtime Now

These routes are the current canonical operator surface.

| Capability | Endpoint | Method | Tier | Notes |
|---|---|---:|---|---|
| Weekly meal planning | `/api/v1/pro/meal/weekly` | POST | PRO | Canonical PRO weekly-planning route |
| Daily nutrition / plate | `/api/v1/pro/nutrition/daily` | GET | PRO | Canonical PRO nutrition-day route |
| Nutrition targets | `/api/v1/pro/nutrition/targets` | POST | PRO | Canonical PRO targets route |
| Payment activation | `/api/v1/pro/payments/activate` | POST | PRO | Canonical payment activation route |
| Payment activation status | `/api/v1/pro/payments/activations/{activation_id}` | GET | PRO | Canonical payment status route |
| Apple receipt verification | `/api/v1/billing/apple/verify-receipt` | POST | Billing transport seam | Implemented verify-only iOS receipt baseline; server-side only, production-first with single `21007` sandbox fallback, no activation side effects (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`, `app/routers/billing.py:215`, `app/services/payments_activation.py:424`, `legacy_app.py:709`, `docs/roadmap/BACKLOG_LEDGER.md:61`) |
| RU/BY payment intent | `/api/v1/pro/payments/ru-by/manual-intent` | POST | PRO | Implemented manual payment intent route |
| RU/BY reconciliation | `/api/v1/pro/payments/ru-by/reconcile` | POST | PRO | Implemented manual reconciliation route |
| RU/BY reconciliation status | `/api/v1/pro/payments/ru-by/reconcile/{intent_id}` | GET | PRO | Implemented reconciliation status route |
| Weekly menu planning | `/api/v1/vip/menu/weekly/plan` | POST | VIP | Canonical VIP weekly-planning route |
| Weekly menu repair | `/api/v1/vip/menu/weekly/repair` | POST | VIP | Canonical VIP repair route |
| Shoplist export | `/api/v1/vip/shoplist/export` | POST | VIP | Canonical VIP export surface |
| Recipe synthesis | `/api/v1/vip/recipes/synthesize` | POST | VIP | Canonical VIP recipe synthesis route |
| Insight | `/api/v1/insight` | POST | VIP-only (`require_vip_tier()`) | AI insight route; API-key access is enforced through VIP middleware, and bounded-context extraction remains planned |
| FitChef mascot insight | `/api/v1/insight/fitchef` | POST | VIP-only (`require_vip_tier()`) | Canonical FitChef mascot coaching route under the insight namespace; feature-gated by `FEATURE_FITCHEF_MASCOT` |
| FitChef weekly reflection | `/api/v1/insight/fitchef/weekly-reflection` | POST | VIP-only (`require_vip_tier()`) | Canonical FitChef weekly reflection route under the insight namespace; feature-gated by `FEATURE_FITCHEF_MASCOT` |
| FitChef slip support | `/api/v1/insight/fitchef/slip-support` | POST | VIP-only (`require_vip_tier()`) | Canonical FitChef slip-support route under the insight namespace; feature-gated by `FEATURE_FITCHEF_MASCOT` |

FitChef initiative note:
- The live mascot routes above remain canonical during the FitChef umbrella foundation and visual/App Store waves.
- Future structured-coach surfaces under `/api/v1/pro/fitchef/*` and `/api/v1/vip/fitchef/*` remain planned-only until a dedicated additive contract PR lands.
- Canonical reference: `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`.

## Deprecated Alias / Proxy-Only Surface

These routes remain for compatibility and migration. They must not be described as an alternative canonical namespace. When no canonical replacement is documented yet, keep the route marked as legacy-compatible rather than inventing a target path.

| Compatibility route | Method | Current tier semantics | Canonical target | Status |
|---|---:|---|---|---|
| `/api/v1/premium/plan/week-flexible` | POST | PRO | `/api/v1/pro/meal/weekly` | Deprecated PRO bridge |
| `/api/v1/premium/bmr` | POST | Legacy premium compatibility | No canonical `/api/v1/pro/*` replacement documented yet | Legacy-compatible endpoint retained until a canonical migration target is committed |
| `/api/v1/premium/tdee` | POST | Legacy premium compatibility | No canonical `/api/v1/pro/*` replacement documented yet | Legacy-compatible endpoint retained until a canonical migration target is committed |
| `/api/v1/premium/targets` | POST | PRO | `/api/v1/pro/nutrition/targets` | Legacy shim |
| `/api/v1/premium/plate` | POST | PRO | `/api/v1/pro/nutrition/plate` | Legacy shim; preserves plate request/response semantics |
| `/api/v1/premium/plan/week` | POST | VIP | `/api/v1/vip/menu/weekly/plan` | Broken naming compatibility route under deprecated namespace |
| `/api/v1/premium/exports/*` | POST | VIP | `/api/v1/vip/shoplist/export` | Wrong-namespace compatibility exports |
| `/api/v1/vip/weekly-plan` | POST | VIP | `/api/v1/vip/menu/weekly/plan` | Deprecated VIP alias |

### Compatibility Notes

- `/api/v1/premium/plan/week` is the most important namespace mismatch: it requires VIP semantics while living under `/premium/*`.
- `/api/v1/premium/plate` and `/api/v1/premium/targets` still exist for migration compatibility, but product docs should direct operators and clients toward `/api/v1/pro/*`.
- `/api/v1/premium/bmr` and `/api/v1/premium/tdee` remain legacy-compatible premium endpoints. No committed `/api/v1/pro/bmr` or `/api/v1/pro/tdee` replacement is documented yet, so they remain legacy-compatible rather than migrated.

## Historical Audit vs Current Map

- `docs/contracts/OPENAPI_PATHS_AUDIT.md` remains the historical evidence pack for the earlier `/premium/*` exposure snapshot.
- `docs/contracts/PRODUCT_TIER_MAP.md` remains the detailed tier/audit specification.
- This file is the current operator-facing route map to use in README, runbooks, and migration notes.

## Planned / Target-State Follow-Ups

- OpenAPI workflow hardening for backend/frontend split targets: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-openapi-decoupling-split`
- `docker compose` v2 migration for repo command surfaces: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-compose-v2-migration`
- AI runtime extraction into a dedicated bounded context: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`
- FitChef umbrella foundation and preserved live-canon policy: `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`

## Legacy Compatibility Guidance

- Legacy or shim routes may stay available for migration and client stability, but they should be documented as proxy-only or deprecated.
- When public route semantics change, update this file and `README.md` together, then confirm whether `docs/contracts/PRODUCT_TIER_MAP.md` also requires a tier/audit update.
- If a target-state is not implemented in runtime yet, keep it in the backlog instead of promoting it to the canonical runtime table.

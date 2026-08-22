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
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md` is the contract lock for B1 baseline. Apple verify seam: `app/routers/billing.py`, `legacy_app.py:709`. RU/BY manual rails: `app/routers/pro_payments.py`. Webhook signature contract: `app/services/payments_activation.validate_webhook_signature`. B1 scope closed; B2 (Apple verify full activation) deferred.

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
| Generated plate | `/api/v1/pro/nutrition/plate` | POST | PRO | Canonical PRO generated-plate route |
| BMR and TDEE | `/api/v1/pro/nutrition/bmr` | POST | PRO | Canonical PRO BMR/TDEE route; uses `BMRRequest` and `BMRResponse` |
| Nutrient gaps | `/api/v1/pro/nutrition/gaps` | POST | PRO | Canonical PRO nutrient-gap route; uses `NutrientGapsRequest` and `NutrientGapsResponse` |
| Payment activation | `/api/v1/pro/payments/activate` | POST | PRO | Canonical payment activation route |
| Payment activation status | `/api/v1/pro/payments/activations/{activation_id}` | GET | PRO | Canonical payment status route |
| FitChef structured explain | `/api/v1/pro/fitchef/explain` | POST | PRO | Feature-gated PRO structured Distortion Simulator route landed via PR #1215; additive to the live mascot canon |
| FitChef support handoff | `/api/v1/pro/fitchef/recommend` | POST | PRO | Implemented in PR #2320 as a feature-gated deterministic descriptor-only candidate; merge-bound until merge and post-merge verification, with no execution or plan-mutation authority |
| FitChef structured insight | `/api/v1/vip/fitchef/insight` | POST | VIP | Feature-gated VIP structured Identity Loop Mapper route landed via PR #1870; additive to the live mascot canon |
| Apple receipt verification | `/api/v1/billing/apple/verify-receipt` | POST | Billing transport seam | Implemented verify-only iOS receipt baseline; server-side only, production-first with single `21007` sandbox fallback, no activation side effects (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`, `app/routers/billing.py:215`, `app/services/payments_activation.py:424`, `legacy_app.py:709`, `docs/roadmap/BACKLOG_LEDGER.md:61`) |
| RU/BY payment intent | `/api/v1/pro/payments/ru-by/manual-intent` | POST | PRO | Implemented manual payment intent route |
| RU/BY reconciliation | `/api/v1/pro/payments/ru-by/reconcile` | POST | PRO | Implemented manual reconciliation route |
| RU/BY reconciliation status | `/api/v1/pro/payments/ru-by/reconcile/{intent_id}` | GET | PRO | Implemented reconciliation status route |
| Weekly menu planning | `/api/v1/vip/menu/weekly/plan` | POST | VIP | Canonical VIP weekly-planning route |
| Weekly menu repair | `/api/v1/vip/menu/weekly/repair` | POST | VIP | Canonical VIP repair route |
| Shoplist export | `/api/v1/vip/shoplist/export` | POST | VIP | Canonical VIP export surface |
| Recipe synthesis | `/api/v1/vip/recipes/synthesize` | POST | VIP | Canonical VIP recipe synthesis route |
| Insight | `/api/v1/insight` | POST | VIP-only (`require_vip_tier()`) | AI insight route; API-key access is enforced through VIP middleware. Route ownership lives in `app/routers/legacy_insight.py` (registered via `app/main.py` route-family bootstrap); execution orchestration stays in `app/services/insight_application_service.py` |
| FitChef mascot insight | `/api/v1/insight/fitchef` | POST | VIP-only (`require_vip_tier()`) | Canonical FitChef mascot coaching route under the insight namespace; feature-gated by `FEATURE_FITCHEF_MASCOT` |
| FitChef weekly reflection | `/api/v1/insight/fitchef/weekly-reflection` | POST | VIP-only (`require_vip_tier()`) | Canonical FitChef weekly reflection route under the insight namespace; feature-gated by `FEATURE_FITCHEF_MASCOT` |
| FitChef slip support | `/api/v1/insight/fitchef/slip-support` | POST | VIP-only (`require_vip_tier()`) | Canonical FitChef slip-support route under the insight namespace; feature-gated by `FEATURE_FITCHEF_MASCOT` |

FitChef initiative note:
- The live mascot routes above remain canonical during the FitChef umbrella foundation and visual/App Store waves.
- The live mascot routes above remain canonical after the structured-coach contract freeze as well; they are not migrated by that phase.
- `POST /api/v1/pro/fitchef/explain` is now a feature-gated PRO structured runtime and OpenAPI-exposed route, landed via PR #1215 / `70bdbd9e51d977d440b605eed3064c71212cff97`.
- `POST /api/v1/pro/fitchef/recommend` is implemented in PR #2320 as a feature-gated deterministic support-handoff candidate and remains merge-bound until merge and post-merge verification. Its `target_surface` is an opaque backend-owned product-surface slug, not proof of client navigation or downstream execution. The route accepts only an exact case-insensitive `application/json` base media type before the first `;`; every rejected media type uses the stable JSON `422` envelope.
- `POST /api/v1/vip/fitchef/insight` is now a feature-gated VIP structured Identity Loop Mapper runtime and OpenAPI-exposed route, landed via PR #1870 / `7802ed25e99e0a4f346d14487270a037bb5ec97a`.
- `POST /api/v1/vip/fitchef/chat` and `POST /api/v1/vip/fitchef/week-repair` remain contract-frozen additive follow-ups.
- Canonical reference: `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`.
- Contract freeze reference: `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`.

## Deprecated Alias / Proxy-Only Surface

These routes remain for compatibility and migration. They must not be described as an alternative canonical namespace. When no canonical replacement is documented yet, keep the route marked as legacy-compatible rather than inventing a target path.

| Compatibility route | Method | Current tier semantics | Canonical target | Status |
|---|---:|---|---|---|
| `/api/v1/premium/plan/week-flexible` | POST | PRO | `/api/v1/pro/meal/weekly` | Deprecated PRO bridge |
| `/api/v1/premium/bmr` | POST | Legacy premium compatibility | `/api/v1/pro/nutrition/bmr` | Retained during the production telemetry window |
| `/api/v1/premium/gaps` | POST | Legacy premium compatibility | `/api/v1/pro/nutrition/gaps` | Retained during the production telemetry window |
| `/api/v1/premium/targets` | POST | PRO | `/api/v1/pro/nutrition/targets` | Legacy shim |
| `/api/v1/premium/plate` | POST | PRO | `/api/v1/pro/nutrition/plate` | Legacy shim; preserves plate request/response semantics |
| `/premium_bmr` | POST | Historical public compatibility | `/api/v1/pro/nutrition/bmr` | Retained pending a separate auth and consumer-sunset decision |
| `/premium_targets` | POST | Legacy app-client credential | `/api/v1/pro/nutrition/targets` | Retained pending a separate root-alias sunset decision |
| `/api/v1/premium/plan/week` | POST | VIP | `/api/v1/vip/menu/weekly/plan` | Broken naming compatibility route under deprecated namespace |
| `/api/v1/vip/weekly-plan` | POST | VIP | `/api/v1/vip/menu/weekly/plan` | Deprecated VIP alias |
| `/insight` | POST | VIP | `/api/v1/insight` | Hidden deprecated legacy alias; owned by `app/routers/legacy_insight.py` |

### Compatibility Notes

- `/api/v1/premium/plan/week` is the most important namespace mismatch: it requires VIP semantics while living under `/premium/*`.
- The repository-owned Web Nutrition Setup calls `/api/v1/pro/nutrition/bmr`; all four versioned nutrition aliases remain callable while their 30-day production traffic window is incomplete.
- `/api/v1/premium/tdee` is not a registered runtime route. TDEE remains part of `BMRResponse` from `/api/v1/pro/nutrition/bmr`; requests to the stale standalone path receive the ordinary FastAPI 404.
- `/premium_bmr` and `/premium_targets` are separate root-namespace compatibility decisions and are not authorized for removal by the versioned-alias telemetry window.
- The hidden day/week CSV test/demo aliases under `/api/v1/premium/exports/*`
  are retired, are no longer compatibility surface, and return the ordinary
  FastAPI 404. Both canonical export families remain registered behind the
  canonical API-key dependency: plan sign/weekly CSV/PDF (`POST
  /api/v1/export/sign`, `GET /api/v1/plan/week/export.{csv,pdf}`) and shoplist
  JSON/CSV/PDF (`GET /api/v1/shoplist`, `GET
  /api/v1/shoplist/export.{csv,pdf}`). `PRIVATE_EXPORTS_ENABLED` additionally
  enforces signed tokens only for weekly plan CSV/PDF; it controls neither
  route-family registration nor any shoplist route.

## Historical Audit vs Current Map

- `docs/contracts/OPENAPI_PATHS_AUDIT.md` remains the historical evidence pack for the earlier `/premium/*` exposure snapshot.
- `docs/contracts/PRODUCT_TIER_MAP.md` remains the detailed tier/audit specification.
- This file is the current operator-facing route map to use in README, runbooks, and migration notes.

## Planned / Target-State Follow-Ups

- OpenAPI workflow hardening for backend/frontend split targets: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-openapi-decoupling-split`
- `docker compose` v2 migration for repo command surfaces: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-compose-v2-migration`
- AI runtime extraction into a dedicated bounded context: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`
- FitChef umbrella foundation and preserved live-canon policy: `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`
- Structured coach target-state follow-ups kept planned after the landed PRO routes:
  - `POST /api/v1/vip/fitchef/chat`
  - `POST /api/v1/vip/fitchef/week-repair`

## Legacy Compatibility Guidance

- Legacy or shim routes may stay available for migration and client stability, but they should be documented as proxy-only or deprecated.
- When public route semantics change, update this file and `README.md` together, then confirm whether `docs/contracts/PRODUCT_TIER_MAP.md` also requires a tier/audit update.
- If a target-state is not implemented in runtime yet, keep it in the backlog instead of promoting it to the canonical runtime table.

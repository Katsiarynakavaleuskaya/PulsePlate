<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Engineering Overview (Профессиональный Язык)

Дата версии: 19 февраля 2026 года (`America/New_York`)

## 1) Product/Tech Context
PulsePlate — multi-client wellness platform с FastAPI backend и доменной логикой в `core/`. Основной runtime ориентирован на:
- BMI/body composition workflows,
- nutrition/plate/menu planning,
- tiered product access (`FREE/PRO/VIP`),
- guarded expensive operations (LLM/export),
- compatibility support через legacy adapter layer.

## 2) Repo Topology (Ключевые Boundaries)
- `app/` — HTTP/transport layer: routers, middleware, schemas, bootstrap.
- `core/` — domain/business logic: BMI engine, risk, menu, recommendations, food pipeline.
- `frontend/` — React thin adapter client to `/api/v1/*`.
- `ios/` — SwiftUI thin adapter client.
- `tests/` — policy guards + behavioral tests.
- `deploy/` — docker/caddy/infra configs.

Центральная boundary-идея: бизнес-логика концентрируется в `core/`, клиенты не дублируют доменные вычисления.

## 3) Runtime Composition

### Entrypoint
- `app/main.py` реэкспортирует FastAPI app из `legacy_app.py`.
- В `app/main.py` регистрируются observability/bootstrap hooks (`register_metrics`, `register_pro_contract_routes`).

### Why this split
- `legacy_app.py` сохраняет compatibility behavior.
- Наблюдаемость и инфраструктурные регистрации вынесены в bootstrap level, чтобы legacy слой не превращался в точку хаоса.

## 4) Router + Middleware Architecture

### Router domains (`app/routers/*`)
- `bmi.py`, `bmi_pro.py` — BMI flows.
- `pro.py`, `vip.py` — tier-specific premium capabilities.
- `plan_export.py`, `shoplist_export.py`, `vip_shoplist.py` — export/shoplist pipelines.
- `users.py`, `foods.py`, `recipes.py`, `catalog.py` — user/data access routes.

### Access control
- `app/middleware/api_tiers.py` определяет `SubscriptionTier = FREE/PRO/VIP`.
- `require_pro_tier` и `require_vip_tier` enforce доступ на route-level.
- Tier resolution поддерживает DB-backed lookup + env fallback (с fail-closed behavior при critical DB tier errors).

## 5) Domain Layer (Core) Responsibilities

### Canonical BMI
- `core/bmi/engine.py` — canonical BMI orchestrator + group/category interpretation.
- `core/bmi/risk.py` — waist/WHR risk thresholds, localized notes.
- Anti-duplication policy: BMI formulas/thresholds не должны расползаться вне `core/bmi/*`.

### Nutrition & Planning
- `core/menu_engine.py`, `core/plate.py`, `core/recommendations.py` — weekly/daily nutrition planning pipeline.
- `core/shoplist*` modules — shopping list generation/export support.

### Food Data Pipeline
- `core/food_sources/usda.py` и `core/food_sources/off.py` — source adapters.
- `core/food_merge.py` — canonical merge rules.
- `scripts/build_food_db.py` + scheduler scripts — operational data refresh.

## 6) Expensive Endpoint Guardrails

### Rate limiting
- `app/security/rate_limit.py` обеспечивает:
  - proxy-aware client fingerprinting,
  - optional SlowAPI wiring,
  - standardized 429 OpenAPI responses (`RATE_LIMIT_429_RESPONSES`),
  - route decorator `limit_if_available(...)`.

### LLM monthly hard quota
- `app/security/llm_monthly_quota.py`:
  - hard-stop before provider call,
  - atomic quota consume via DB upsert,
  - server-salted fingerprint of VIP key,
  - fail-fast requirements for critical env vars (`SERVER_SALT`).

### Insight routes
- `legacy_app.py` defines `/api/v1/insight` (+ legacy alias `/insight`).
- Flow: feature-flag gate -> quota consume -> provider call.
- Expensive endpoints wrapped in rate limit + quota semantics.

## 7) Client Architecture Contracts

### Web (`frontend/`)
- API calls centralized in `frontend/src/api/client.ts`.
- URL normalization avoids duplicated `/api` / `/api/v1` path bugs.
- Generated schema types (`src/api/schema.ts`) are SoT for frontend DTO typing.
- Thin-client guard policy forbids direct business logic leakage into UI/network layers.

### iOS (`ios/`)
- `APIClient.swift` + `HTTPClient.swift` implement transport-only networking.
- Guard tests enforce no BMI calculations on-device.
- iOS consumes backend fields as-is; category/risk inference must remain server-side.

## 8) Health/Readiness Operational Semantics
- `/health` — liveness (always 200 when process alive, no external dependency requirement).
- `/ready` — readiness alias to DB check semantics (can return 503 when dependency unavailable).
- `/health/db` — explicit DB connectivity/degradation endpoint.

Это разделение нужно для корректной orchestration behavior (restart vs stop-routing).

## 9) Quality Gates And Engineering Workflow

### Hard gates
- Canonical pass command: `make verify`.
- Composition: lint -> typecheck -> test-fast -> diff-cov.
- Merge claims without local gate evidence are invalid by policy.

### Test determinism
- deterministic smoke subset for `test-fast`.
- guard tests enforce architecture/import hygiene/thin-client invariants.

### Pre-commit
- `pre-commit run --all-files` required before push.
- hook-induced file changes must be committed (including generated artifacts like `.secrets.baseline`).

## 10) Why This Architecture Is Viable
- Centralized domain math reduces drift and regulatory risk.
- Tier middleware creates clean monetization and capability boundaries.
- Thin adapters keep clients lightweight and contract-driven.
- Guard tests convert architecture decisions into enforceable CI policy.

## 11) Extension Map (How To Add New Capability Safely)
1. Add/extend domain logic in `core/`.
2. Add transport adapter in `app/routers/` with explicit tier/security/rate constraints.
3. Sync OpenAPI/contracts and client types.
4. Add deterministic tests (including 429/quota tests for expensive endpoints).
5. Re-run hard gates.

## 12) Known Tradeoffs
- legacy compatibility layer increases surface area and test load.
- strict guard policy increases PR friction but reduces long-term architecture entropy.
- mixed module age (new core + legacy paths) requires disciplined invariants and continuous refactoring.

## Security Notes
- Apply fail-closed defaults for tier lookup and feature gating on expensive operations.
- Enforce rate limits + hard quota for any LLM/export endpoint before release.
- Preserve thin-client boundary to avoid duplicated risk logic across platforms.
- Keep `/health` independent from external systems; keep `/ready` dependency-aware.

## Marketing & GTM
- Engineering artifacts should expose proof points for GTM: reliability gates, deterministic tests, and security controls.
- For sales/marketing claims use only capabilities already enforced by code/tests.
- Prefer "controlled AI + operational guardrails" narrative over generic "AI-powered" statements.

# ✅ PulsePlate — API Alignment Checklist (FREE/PRO/VIP tiers, deprecated premium namespace)

**Status:** Canonical alignment protocol
**Last updated:** 2026-01-11
**Owner:** Backend + Frontend teams

---

## 0) Principles (invariants — do not start without them)

### English

* **Single source of truth for contracts:** OpenAPI from `app.main.app` + `normalize_openapi_schema()`.
* **Product tiers are FREE / PRO / VIP** (per `SubscriptionTier` enum in `app/middleware/api_tiers.py`).
* **VIP ≠ PRO:** VIP (weekly/micro/shoplist/auto-repair) and PRO (nutrition/plans) are **different domain contours**; do not mix.
* **BMI core is canonical:** the BMI calculation engine is the single source of truth; routers/legacy are thin adapters.
* **`/premium/*` is a deprecated namespace** (aliases only), not a tier. All `/premium/*` endpoints must delegate to canonical `/pro/*` or `/vip/*`.
* **Canonical namespaces:** `/api/v1/bmi/*` (FREE), `/api/v1/pro/*` (PRO), `/api/v1/vip/*` (VIP).
* **Forbidden:** adding manual frontend types when the type already exists in OpenAPI.
* **Forbidden:** business logic in `legacy_app.py` (except compatibility endpoints and thin adapters).
* **OpenAPI determinism is a gate:** every contract must be deterministic and safe.
* **Any new endpoint** → decide immediately: is it public in the schema or intentionally hidden.
* **OpenAPI must not expose deprecated aliases by default** (hide `/premium/*` from schema to prevent frontend from generating types for wrong paths).

**Gates (must pass):**

* `make openapi` → `git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts`
* `pytest` + `diff-cover`
* No new "silent" feature-flag branches that change the contract without being reflected in docs.

### Русский

* **Один источник правды по контрактам:** OpenAPI из `app.main.app` + `normalize_openapi_schema()`.
* **Уровни продукта: FREE / PRO / VIP** (по `SubscriptionTier` enum в `app/middleware/api_tiers.py`).
* **VIP ≠ PRO:** VIP (неделя/микро/шоплист/авто-ремонт) и PRO (питание/планы) — **разные доменные контуры**, не смешиваем.
* **BMI core — канон:** движок расчёта BMI — единый источник; роутеры/legacy — тонкие адаптеры.
* **`/premium/*` — deprecated namespace** (только aliases), не уровень подписки. Все `/premium/*` endpoints должны делегировать в канонические `/pro/*` или `/vip/*`.
* **Канонические namespaces:** `/api/v1/bmi/*` (FREE), `/api/v1/pro/*` (PRO), `/api/v1/vip/*` (VIP).
* **Запрещено:** новые ручные типы на фронте, если тип уже есть в OpenAPI.
* **Запрещено:** бизнес-логика в `legacy_app.py` (кроме совместимых эндпоинтов и тонких адаптеров).
* **Детерминизм OpenAPI — жёсткий гейт:** любой контракт должен быть детерминированным и безопасным.
* **Любой новый эндпоинт** → сразу решаем: он в schema публично или скрыт.
* **OpenAPI не должен показывать deprecated aliases по умолчанию** (скрыть `/premium/*` из схемы, чтобы фронт не генерировал типы для неправильных путей).

**Гейт (должно пройти):**

* `make openapi` → `git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts`
* `pytest` + `diff-cover`
* нет новых "тихих" веток с фича-флагами, которые меняют контракт без отражения в документации.

---

## 1) Схема и безопасность OpenAPI (сначала это, иначе фронт генерит мусор)

### 1.1 Public schema hygiene (обязательное)

**Цель:** если `/openapi.json` публичный — он не должен палить internal surface и deprecated aliases.

* [ ] Все admin endpoints → `include_in_schema=False`
  * `/api/v1/admin/*`, `/admin/*` (status/db-status/check-updates/rollback/force-update/logs/cleanup)
* [ ] Test router → **не в schema**
  * либо schema-only guard, либо сам router `include_in_schema=False`
* [ ] Export/demo endpoints → **не в schema**, пока не "productized"
  * `/api/v1/premium/exports/*`, `/api/v1/export/pdf` и т.п.
* [ ] Debug endpoints (`/debug_env`) → не в schema
* [ ] **Deprecated `/premium/*` aliases → скрыть из schema по умолчанию**
  * чтобы фронт не генерил типы для deprecated путей
  * оставить только canonical `/pro/*` и `/vip/*`

**DoD:** в `frontend/src/api/openapi.json` нет `admin`, `test`, `debug`, `exports` путей, и нет `/premium/*` (или они явно помечены deprecated).

---

### 1.2 Unified schema-only mode (обязательное)

**Цель:** schema generation не должен импортить ORM и падать "Table already defined".

* [ ] Один `is_schema_only_mode()` (например `app/utils/openapi_mode.py`)
* [ ] Его уважают **все** conditional registration места:
  * VIP registration
  * test router
  * bodyfat router
  * bmi-pro router
  * business router
  * exports endpoints

**DoD:** `make openapi` не зависит от "удачи", без флейков и без ORM double-load.

---

### 1.3 VIP default enabled — фиксируем поведение в schema-gen

Сейчас `VIP_MODULE_ENABLED` default `true` → VIP цепочкой может тянуть premium_week и ORM.

* [ ] В `scripts/generate_openapi.py` явно ставим `VIP_MODULE_ENABLED=false` **или** VIP registration уважает schema-only.
* [ ] Убираем `ENABLE_TEST_ROUTES=1` из schema-gen (или делаем чтобы оно не влияло на schema).

**DoD:** schema-gen всегда минимально безопасный.

---

## 2) Контракт: "FREE / PRO / VIP tiers, `/premium/*` deprecated namespace" (закрываем путаницу имен/эндпоинтов)

### 2.1 Канонические namespaces (единый mapping)

**Важно:** VIP и PRO — **разные доменные контуры**. Не смешиваем логику.

**Canonical namespaces (source of truth):**

* `/api/v1/bmi/*` → FREE tier
* `/api/v1/pro/*` → PRO tier
* `/api/v1/vip/*` → VIP tier

**Deprecated namespace (aliases only):**

* `/api/v1/premium/*` → deprecated aliases, делегируют в `/pro/*` или `/vip/*`

Составляем 1 каноническую таблицу:

* [ ] **Weekly plan**
  * VIP canonical: `/api/v1/vip/menu/weekly/plan` (фактический VIP endpoint)
  * PRO canonical: `/api/v1/pro/meal/weekly` (фактический PRO endpoint)
  * Premium alias (deprecated): `/api/v1/premium/plan/week` → **делегирует** в VIP (по факту требует VIP_MODULE_ENABLED)
* [ ] **Targets**
  * PRO canonical: `/api/v1/pro/nutrition/targets` (planned)
  * Premium alias (deprecated): `/api/v1/premium/targets` → делегирует в PRO canonical
* [ ] **Daily plate**
  * PRO canonical: `/api/v1/pro/nutrition/daily` (GET)
  * Premium alias (deprecated): `/api/v1/premium/plate` → делегирует в PRO canonical

**Правило:** VIP и PRO могут иметь **разную логику** (VIP = микро/регион/шоплист, PRO = питание/планы), но `/premium/*` aliases **не дублируют** ни одну из них.

**DoD:** в репо есть один файл-истина (`docs/contracts/PRODUCT_TIER_MAP.md`) и он совпадает с OpenAPI.

---

### 2.2 `/premium/*` endpoints — только aliases, никакой логики

* [ ] Любой `/api/v1/premium/*` endpoint:
  * не считает нутриенты сам
  * не строит неделю сам
  * не содержит "rules"
  * только вызывает canonical handler (`/pro/*` или `/vip/*`) и делает маппинг ответа (если надо)
  * помечен `deprecated=True` и/или `include_in_schema=False`

**DoD:** grep по `legacy_app.py`/premium endpoints — нет "тяжёлых" функций, только delegation/adapter.

---

## 3) Legacy app extraction (если вы сейчас в ветке 511A/511B — это сюда)

### 3.1 PR-511A (extraction only) — invariants

* [ ] `legacy_app.py` не создаёт `FastAPI()`
* [ ] router registration в одном месте (registration module)
* [ ] `legacy_app.py` хранит:
  * публичные атрибуты `premium_week_router/pro_router/vip_router` (если нужны тестам)
  * legacy endpoints `/api/nutrition/{date}`, `/plan`, `/bmi` (если ещё держим)

**DoD:** OpenAPI byte-identical после normalize.

### 3.2 PR-511B (guards) — закрываем ORM risks + schema hygiene

* [ ] unified schema-only guards применены
* [ ] admin/test/export скрыты из схемы

**DoD:** openapi-sync зелёный, без флейков.

---

## 4) Frontend: типы и эндпоинты (после того как schema стала "правдой")

### 4.1 Generated types становятся единственными

* [ ] Удаляем/запрещаем ручные типы-дубли (`frontend/src/api/premium/types.ts`)
* [ ] Все клиенты импортируют из `frontend/src/api/schema.ts`
* [ ] Если нужна runtime валидация — Zod схемы строятся поверх generated типов, но **не заменяют** их.

**DoD:** нет расхождений "тип есть в premium/types.ts, но другой в schema.ts".

---

### 4.2 Миграция endpoint paths в одном PR (и тесты)

* [ ] `weekly-plan.ts`: premium → canonical (или premium shim, но бьёт в правильный URL)
* [ ] `targets.ts`
* [ ] `plate.ts` (учесть смену метода POST→GET если это правда по контракту)
* [ ] `mocks/handlers.ts` обновлён под новые пути
* [ ] интеграционные тесты обновлены

**DoD:** `npm run test` и `npm run build` зелёные.

---

## 5) Anti-duplication enforcement (чтобы путаница не вернулась)

### 5.1 Repo-policy guard tests

* [ ] Тест/линт: "запрещено" импортировать/вычислять нутриенты в `/premium/*` alias слоях
* [ ] Тест: "запрещено" объявлять ручные типы для схем, которые есть в OpenAPI
* [ ] Документируем в `AGENTS.md` правила (✅ уже добавлено в секцию "Product tiers and API namespaces"):
  * Tiers are: FREE / PRO / VIP (per `SubscriptionTier` enum)
  * `/premium/*` is a deprecated namespace (aliases only), not a tier
  * VIP endpoints MUST live under `/api/v1/vip/*`
  * PRO endpoints MUST live under `/api/v1/pro/*`
  * OpenAPI must not expose deprecated aliases by default
  * File naming must not imply tier unless enforced
  * VIP ≠ PRO (разные доменные контуры)
  * BMI core — канон; роутеры — thin adapters
  * `/premium/*` aliases = delegation only (no business logic)
  * schema-only guards required
  * admin/test/export hidden from schema
  * OpenAPI determinism — gate для любого контракта

**DoD:** новый участник не сможет случайно "написать вторую реализацию" или использовать deprecated namespace как canonical.

---

## Мини-скрипт проверки перед каждым PR (короткий, но железный)

1. `make openapi && git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts`
2. `pytest` + `diff-cover`
3. Если PR трогает API:
   * в описании PR есть "Contract impact" (что меняется в OpenAPI)
   * есть ссылка на `docs/API_CONTRACT_MAP.md`

---

## Приоритет выполнения

1. **Сначала:** Секция 1 (OpenAPI hygiene + schema-only guards) — без этого фронт будет генерить типы из небезопасной схемы.
2. **Потом:** Секция 2 (контракты) — фиксируем mapping premium→canonical.
3. **Параллельно/после:** Секция 3 (legacy extraction) — PR-511A/511B.
4. **В конце:** Секция 4 (frontend migration) — только после того, как schema стала "правдой".

---

**See also:**
- `docs/audit/PR_510_AUDIT_EVIDENCE_PACK.md` — детальный анализ legacy_app.py
- `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping (source of truth)
- `docs/contracts/OPENAPI_PATHS_AUDIT.md` — фактический список путей из OpenAPI
- `docs/contracts/API_CANONICAL_MAP.md` — текущий mapping (требует обновления)
- `AGENTS.md` — правила репозитория (секция "Product tiers and API namespaces")

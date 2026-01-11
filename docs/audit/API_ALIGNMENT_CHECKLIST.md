# ✅ PulsePlate — API Alignment Checklist (VIP-first, premium=shim, zero-duplication)

**Status:** Canonical alignment protocol
**Last updated:** 2026-01-11
**Owner:** Backend + Frontend teams

---

## 0) Принципы (инварианты, без которых не начинаем)

* **Один источник правды по контрактам:** OpenAPI из `app.main.app` + `normalize_openapi_schema()`.
* **VIP ≠ PRO:** VIP (неделя/микро/шоплист/авто-ремонт) и PRO (питание/планы) — **разные доменные контуры**, не смешиваем.
* **BMI core — канон:** BMI calculation engine — единый источник; роутеры/legacy — thin adapters.
* **premium = compat shim:** premium endpoints могут жить, но **не содержат бизнес-логики**, только делегирование/адаптация.
* **Запрещено:** новые ручные типы на фронте, если тип уже есть в OpenAPI.
* **Запрещено:** бизнес-логика в `legacy_app.py` (кроме compatibility endpoints и тонких адаптеров).
* **OpenAPI determinism — gate:** любой контракт должен быть детерминированным и безопасным.
* **Любой новый endpoint** → сразу решаем: он в schema публично или скрыт.

**Gate (must pass):**

* `make openapi` → `git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts`
* `pytest` + `diff-cover`
* нет новых "тихих" feature-flag веток, которые меняют контракт без отражения в docs.

---

## 1) Схема и безопасность OpenAPI (сначала это, иначе фронт генерит мусор)

### 1.1 Public schema hygiene (обязательное)

**Цель:** если `/openapi.json` публичный — он не должен палить internal surface.

* [ ] Все admin endpoints → `include_in_schema=False`
  * `/api/v1/admin/*`, `/admin/*` (status/db-status/check-updates/rollback/force-update/logs/cleanup)
* [ ] Test router → **не в schema**
  * либо schema-only guard, либо сам router `include_in_schema=False`
* [ ] Export/demo endpoints → **не в schema**, пока не "productized"
  * `/api/v1/premium/exports/*`, `/api/v1/export/pdf` и т.п.
* [ ] Debug endpoints (`/debug_env`) → не в schema

**DoD:** в `frontend/src/api/openapi.json` нет `admin`, `test`, `debug`, `exports` путей.

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

## 2) Контракт: "VIP ≠ PRO, premium=shim" (закрываем путаницу имен/эндпоинтов)

### 2.1 Таблица контрактов (единый mapping)

**Важно:** VIP и PRO — **разные доменные контуры**. Не смешиваем логику.

Составляем 1 каноническую таблицу:

* [ ] **Weekly plan**
  * VIP canonical: `/api/v1/vip/meal/weekly` (или фактический VIP endpoint)
  * PRO canonical: `/api/v1/pro/meal/weekly` (если остаётся как отдельный контур)
  * Premium shim: `/api/v1/premium/plan/week` → **делегирует** в VIP или PRO (по продуктовой логике)
* [ ] **Targets**
  * VIP canonical: `/api/v1/vip/nutrition/targets` (если микро-constraints)
  * PRO canonical: `/api/v1/pro/nutrition/targets` (если отдельный контур)
  * Premium shim: `/api/v1/premium/targets` → делегирует в соответствующий canonical
* [ ] **Daily plate**
  * PRO canonical: `/api/v1/pro/nutrition/daily` (GET)
  * Premium shim: `/api/v1/premium/plate` (если нужен) → делегирует / адаптирует

**Правило:** VIP и PRO могут иметь **разную логику** (VIP = микро/регион/шоплист, PRO = питание/планы), но premium shim **не дублирует** ни одну из них.

**DoD:** в репо есть один файл-истина (например `docs/API_CONTRACT_MAP.md`) и он совпадает с OpenAPI.

---

### 2.2 Premium endpoints — только shim, никакой логики

* [ ] Любой `/api/v1/premium/*` endpoint:
  * не считает нутриенты сам
  * не строит неделю сам
  * не содержит "rules"
  * только вызывает canonical handler и делает маппинг ответа (если надо)

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

* [ ] Тест/линт: "запрещено" импортировать/вычислять нутриенты в premium shim слоях
* [ ] Тест: "запрещено" объявлять ручные типы для схем, которые есть в OpenAPI
* [ ] Документируем в `AGENTS.md` правила:
  * VIP ≠ PRO (разные доменные контуры)
  * BMI core — канон; роутеры — thin adapters
  * premium=shim only (no business logic)
  * schema-only guards required
  * admin/test/export hidden from schema
  * OpenAPI determinism — gate для любого контракта

**DoD:** новый участник не сможет случайно "написать вторую реализацию".

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
- `docs/contracts/API_CANONICAL_MAP.md` — текущий mapping (требует обновления)
- `AGENTS.md` — правила репозитория

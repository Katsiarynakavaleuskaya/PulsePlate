# 📊 PulsePlate — Canonical Product Tier Map (v1)

**Status:** Canonical (audit-driven, based on actual codebase)
**Last updated:** 2026-06-15
**Canonical reference (derived from code):** `app/middleware/api_tiers.py`, `app/routers/*.py`, `legacy_app.py`

---

## Уровни продукта (зафиксировано на основе кода)

| Уровень     | Статус | Роль                            | Код-доказательство                                    |
| ----------- | ------ | ------------------------------- | ----------------------------------------------------- |
| **FREE**    | канон  | вход в продукт, скрининг        | `SubscriptionTier.FREE` (`app/middleware/api_tiers.py:47`) |
| **PRO**     | канон  | платное питание и цели          | `SubscriptionTier.PRO` (`app/middleware/api_tiers.py:48`), `require_pro_tier()` |
| **VIP**     | канон  | продвинутые планы, микро-логика | `SubscriptionTier.VIP` (`app/middleware/api_tiers.py:49`), `require_vip_tier()` |

> ⚠️ **Важно:**
> `pro_*` в именах файлов/функций — **техническое legacy-название**.
> **PRO — реальный продуктовый уровень** (определён в `SubscriptionTier` enum).
> `/premium/*` — **deprecated API namespace**; он требует PRO tier (а для части legacy aliases — VIP), но не является отдельным уровнем.

---

## Current public channel contract

The tier and entitlement model below remains canonical backend product truth. It does not
authorize a purchase surface in every client channel.

- The current public Web surface is free to use and offers no purchase, subscription,
  upgrade, trial, restore, or entitlement-acquisition action.
- The public `/pro` URL remains a compatibility route, but its Web content is
  information-only and links only to the free BMI calculator and the marketing page.
- More advanced FitChef capabilities are an Apple-device product direction. This wording
  does not prove availability on iPhone, iPad, Mac, or any individual device family.
- An App Store link may appear only after its public availability and exact destination are
  verified. Until then, the Web UI contains no external Store link or download claim.
- “The website is free to use” records the current channel posture. It is not a perpetual
  commercial promise, legal conclusion, or certification of tax or employment status.
- A future paid Web channel requires a separate exact human GO, server-authoritative billing
  and entitlement architecture, and its own reviewed carrier. This contract does not forbid
  that separately admitted future work.

Backend billing, Apple receipt verification, StoreKit, entitlement persistence, product-tier
enums, API routes, and generated OpenAPI truth are unchanged by the current Web presentation
boundary.

---

## 1️⃣ FREE — BMI / Screening

### Бизнес-смысл

- Бесплатный вход
- Диагностика / скрининг
- Основа всей системы

### Канонический домен

`core/bmi/*`

### API (канон)

| Тип            | Endpoint                | Статус      | Код-доказательство                          |
| -------------- | ----------------------- | ----------- | ------------------------------------------- |
| BMI calculate  | `/api/v1/bmi/calculate` | ✅ canonical | `app/routers/bmi.py`                        |
| BMI compat     | `/bmi`, `/plan`, `/api/v1/bmi` | ⚠️ shim | `app/routers/bmi_compat.py`                 |
| Foods          | `/api/v1/foods/*`       | ✅ canonical | `app/routers/foods.py`                      |
| Recipes        | `/api/v1/recipes/*`     | ✅ canonical | `app/routers/recipes.py`                     |
| Users          | `/api/v1/users/*`       | ✅ canonical | `app/routers/users.py`                      |

### Правила

- ❌ никакой логики вне `core/bmi`
- ❌ никаких premium/vip зависимостей
- ✅ legacy endpoints = thin proxy

---

## 2️⃣ PRO — Nutrition / Targets / Daily Plate

### Средний платный сегмент

### Бизнес-смысл

- Питание
- Калории / нутриенты
- Day-level планы
- Без микро-ремонта и shoplist

### Канонический домен

**PRO Nutrition** (`app/routers/pro.py`)

> ✅ **Фактическое состояние:**
> PRO — это **реальный уровень подписки**, определённый в `SubscriptionTier.PRO`.
> Все endpoints требуют `require_pro_tier()` middleware.

### API (канон)

| Функция             | Endpoint                      | Статус      | Требует tier | Код-доказательство                    |
| -------------------- | ----------------------------- | ----------- | ------------ | ------------------------------------- |
| Weekly plan          | `/api/v1/pro/meal/weekly`     | ✅ canonical | PRO          | `app/routers/pro.py:245`              |
| Targets (WHO)       | `/api/v1/pro/nutrition/targets` | ✅ canonical | PRO          | `app/routers/pro_nutrition_contracts.py:35` |
| Generated plate     | `/api/v1/pro/nutrition/plate` | ✅ canonical | PRO          | `app/routers/pro_nutrition_contracts.py:46` |
| BMR and TDEE        | `/api/v1/pro/nutrition/bmr` | ✅ canonical | PRO + `FEATURE_PREMIUM_NUTRITION` | `app/routers/pro_nutrition_contracts.py:56` |
| Nutrient gaps       | `/api/v1/pro/nutrition/gaps` | ✅ canonical | PRO          | `app/routers/pro_nutrition_contracts.py:66` |
| Daily plate          | `/api/v1/pro/nutrition/daily` | ✅ canonical | PRO          | `app/routers/pro.py:369`              |
| Shopping list (PRO)  | `/api/v1/pro/meal/shopping-list` | ✅ canonical | PRO          | `app/routers/shopping_list_pro.py:19` |
| Shoplist day        | `/api/v1/pro/shoplist/*`      | ✅ canonical | PRO          | `app/routers/shoplist_day.py:22`      |
| Nutrition log       | `/api/v1/pro/nutrition/log/*` | ✅ canonical | PRO          | `app/routers/nutrition_log.py:27`     |
| Bayes adherence     | `/api/v1/pro/bayes/*`         | ✅ canonical | PRO          | `app/routers/bayes_adherence.py:23`   |

### Deprecated PRO-class compatibility routes

| Функция        | Endpoint                        | Статус           | Runtime guard / tier classification | Код-доказательство                        |
| -------------- | ------------------------------- | ---------------- | ----------------------------------- | ----------------------------------------- |
| Weekly plan    | `/api/v1/premium/plan/week-flexible` | ⚠️ deprecated | PRO tier bridge | `app/routers/premium_week.py:290`         |
| Targets        | `/api/v1/premium/targets`       | ⚠️ legacy shim   | PRO-class; legacy API-key guard | `app/routers/legacy_premium_nutrition.py:75` |
| Daily plate    | `/api/v1/premium/plate`         | ⚠️ legacy shim   | PRO-class; legacy API-key guard | `app/routers/legacy_premium_nutrition.py:35` |
| BMR            | `/api/v1/premium/bmr`           | ⚠️ legacy shim   | Legacy API-key guard + `FEATURE_PREMIUM_NUTRITION` | `app/routers/legacy_premium_nutrition.py` |
| Nutrient gaps  | `/api/v1/premium/gaps`          | ⚠️ legacy shim   | PRO-class; legacy API-key guard | `app/routers/legacy_premium_nutrition.py` |
| BMR root alias | `/premium_bmr`                  | ⚠️ legacy public exception | No API-key dependency; `FEATURE_PREMIUM_NUTRITION` required | `app/routers/legacy_premium_nutrition.py` |
| Targets root alias | `/premium_targets`            | ⚠️ legacy shim   | Legacy API-key guard | `app/routers/legacy_premium_nutrition.py` |

> ⚠️ **Примечание:** Endpoints под `/premium/*`, которые **фактически требуют VIP tier**, не относятся к PRO и перечислены в разделе VIP (см. секцию "Deprecated aliases with wrong namespace").
>
> ⚠️ **Ключевое понимание:**
> `/premium/*` endpoints are deprecated PRO-class compatibility surfaces unless
> explicitly listed in the VIP wrong-namespace section. Runtime enforcement on
> this legacy family is the legacy API-key guard, not `require_pro_tier()`,
> except for `/premium_bmr`, which remains a historical public route-shape
> exception.
> `/premium_bmr` is a historical root alias and remains a route-shape compatibility
> exception until a dedicated auth/contract migration PR owns that behavior change.
> All three canonical/retained BMR routes share the same request-time feature gate and canonical service;
> the public exception does not bypass feature availability.
> The Web Nutrition Setup now consumes canonical `/api/v1/pro/nutrition/bmr`.
> The four versioned aliases remain live until the separately tracked 30-day
> exact-zero traffic gate passes; the two root aliases have a separate sunset decision.

### Что НЕ входит

- ❌ weekly plan с авто-ремонтом (это VIP)
- ❌ shoplist с региональной логикой (это VIP)
- ❌ микро-constraints (это VIP)

### Правила

- PRO endpoints используют `require_pro_tier()` middleware
- `pro_registration.py` = **технический модуль регистрации**, не бизнес-уровень
- `premium_week.py` = **deprecated**, мигрирует на `pro.py`

### FitChef structured coach follow-up

| Функция | Endpoint | Статус | Требует tier | Canonical reference |
| --- | --- | --- | --- | --- |
| FitChef explain | `/api/v1/pro/fitchef/explain` | ✅ feature-gated runtime | PRO | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |
| FitChef recommend | `/api/v1/pro/fitchef/recommend` | ✅ feature-gated deterministic runtime | PRO | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |

> `POST /api/v1/pro/fitchef/explain` is the landed first bounded structured runtime for the CBT Coaching Wave: `Distortion Simulator` (PR #1215 / `70bdbd9e51d977d440b605eed3064c71212cff97`).
> `POST /api/v1/pro/fitchef/recommend` landed via PR #2320 on 2026-08-25 at `f95a329d899d5ac4fa73f198e90cfed44d0fc45c`: `daily_structure` maps to `pro_daily_plate`, while `weekly_structure` maps to `pro_weekly_plan`. It accepts only the exact case-insensitive `application/json` base media type before the first `;`, uses canonical PRO auth and the shared structured-coach flag, grants no navigation, execution, or plan-mutation authority, implements no VIP planning logic, and has unmeasured product utility.

---

## 3️⃣ VIP — Weekly / Micro / Shoplist

### Высший платный сегмент

### Бизнес-смысл

- Weekly plan с микро-constraints
- Auto-repair
- Shoplist / region
- Recipe synthesis
- Exports

### Канонический домен

**VIP Planning Engine** (`app/routers/vip.py`, `app/routers/vip_shoplist.py`)

### API (канон)

| Функция              | Endpoint                           | Статус      | Требует tier | Код-доказательство                        |
| -------------------- | ---------------------------------- | ----------- | ------------ | ----------------------------------------- |
| Weekly plan          | `/api/v1/vip/menu/weekly/plan`     | ✅ canonical | VIP          | `app/routers/vip.py` (main endpoint)      |
| Weekly plan (legacy) | `/api/v1/vip/weekly-plan`         | ⚠️ deprecated | VIP        | `app/routers/vip.py:733` (deprecated)     |
| Insight              | `/api/v1/insight`                 | ⚠️ flag     | VIP          | `app/routers/legacy_insight.py` via `app/main.py` route-family bootstrap (`FEATURE_INSIGHT`, VIP guard) |
| FitChef mascot insight | `/api/v1/insight/fitchef`       | ⚠️ flag     | VIP          | `app/routers/fitchef_insight.py` (`FEATURE_FITCHEF_MASCOT`) |
| FitChef weekly reflection | `/api/v1/insight/fitchef/weekly-reflection` | ⚠️ flag | VIP | `app/routers/fitchef_insight.py` (`FEATURE_FITCHEF_MASCOT`) |
| FitChef slip support | `/api/v1/insight/fitchef/slip-support` | ⚠️ flag | VIP | `app/routers/fitchef_insight.py` (`FEATURE_FITCHEF_MASCOT`) |
| Shoplist generate    | `/api/v1/vip/shoplist/generate`   | ✅ canonical | VIP          | `app/routers/vip_shoplist.py:364`          |
| Shoplist preview     | `/api/v1/vip/shoplist/preview`     | ✅ canonical | VIP          | `app/routers/vip_shoplist.py:299`          |
| Shoplist daily       | `/api/v1/vip/shoplist/daily`      | ✅ canonical | VIP          | `app/routers/vip_shoplist.py:402`          |
| Shoplist weekly      | `/api/v1/vip/shoplist/weekly`     | ✅ canonical | VIP          | `app/routers/vip_shoplist.py:442`          |
| Recipe synthesize    | `/api/v1/vip/recipes/synthesize`  | ✅ canonical | VIP          | `app/routers/vip.py`                      |
| Auto-repair          | `/api/v1/vip/auto-repair/*`        | ✅ canonical | VIP          | `app/routers/vip.py` (via core.auto_repair) |

### Deprecated aliases with wrong namespace (требуют VIP tier)

| Функция       | Endpoint                     | Статус        | Требует tier | Проблема | Канонический endpoint | Код-доказательство                |
| ------------- | ---------------------------- | ------------- | ------------ | -------- | --------------------- | ---------------------------------- |
| Weekly plan   | `/api/v1/premium/plan/week`  | 🔴 **broken naming** | VIP (через VIP_MODULE_ENABLED) | Wrong namespace (`/premium/*` вместо `/vip/*`) | `/api/v1/vip/menu/weekly/plan` | `app/routers/legacy_premium_weekly_plan.py:23` |

> ⚠️ **Ключевая проблема:**
> `/api/v1/premium/plan/week` требует **VIP tier**, но живёт под `/premium/*` namespace (deprecated PRO namespace) → **архитектурная путаница**.
> **Remediation:** See `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md` (PR-C: delegation pattern).

### Правила

- VIP ≠ PRO
- VIP может зависеть от PRO данных
- ❌ PRO не может реализовывать VIP-логику
- VIP endpoints используют `require_vip_tier()` middleware

### FitChef structured coach follow-up

| Функция | Endpoint | Статус | Требует tier | Canonical reference |
| --- | --- | --- | --- | --- |
| FitChef insight | `/api/v1/vip/fitchef/insight` | ✅ feature-gated runtime | VIP | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |
| FitChef chat | `/api/v1/vip/fitchef/chat` | 🧭 contract-frozen | VIP | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |
| FitChef week repair | `/api/v1/vip/fitchef/week-repair` | 🧭 contract-frozen | VIP | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |

> `POST /api/v1/vip/fitchef/insight` is the first bounded VIP structured runtime for the CBT Coaching Wave: `Identity Loop Mapper`, feature-gated by `FEATURE_FITCHEF_STRUCTURED_COACH`, and landed via PR #1870 / `7802ed25e99e0a4f346d14487270a037bb5ec97a`.
> `chat` and `week-repair` remain additive contract-frozen follow-ups; live `/api/v1/insight/fitchef*` family remains canonical and unmigrated.
> VIP structured `chat` and `week-repair` are not runtime/OpenAPI surfaces until later reviewed implementation PRs register them.

---

## 4️⃣ Legacy / Shim слой (явно признаём)

### Что сюда относится

- `legacy_app.py` compatibility shims and remaining legacy-owned endpoints
- `/premium_*` (без `/api/v1/`)
- `/api/nutrition/{date}`
- `/bmi`, `/plan`, `/api/v1/bmi` (canonical compatibility owner: `app/routers/bmi_compat.py`)
- `/premium_bmr`

### Назначение

- Совместимость
- Переходный слой

### Жёсткое правило

> #### Shim = delegation only
> ❌ никакой бизнес-логики
> ❌ никаких расчётов
> ✅ только вызов канона + адаптация ответа

---

## 5️⃣ Терминология — фиксируем раз и навсегда

| Термин          | Значение                                    | Код-доказательство                                    |
| --------------- | ------------------------------------------- | ----------------------------------------------------- |
| **FREE**        | продуктовый уровень                         | `SubscriptionTier.FREE` (`api_tiers.py:47`)           |
| **PRO**         | продуктовый уровень (платный, средний)      | `SubscriptionTier.PRO` (`api_tiers.py:48`)             |
| **VIP**         | продуктовый уровень (платный, высший)       | `SubscriptionTier.VIP` (`api_tiers.py:49`)            |
| `pro_*`         | ❗ техническое legacy-название в коде       | `pro_registration.py`, `pro_router`, `shopping_list_pro.py` |
| `/premium/*`    | ⚠️ deprecated API namespace (требует PRO или VIP, зависит от endpoint)  | `premium_week.py:31`, `legacy_app.py:3980, 4685, 4706`     |
| `/api/v1/pro/*` | ✅ canonical PRO namespace                   | `app/routers/pro.py:37`                               |
| `/api/v1/vip/*` | ✅ canonical VIP namespace                   | `app/routers/vip.py`, `app/routers/vip_shoplist.py`  |

> ❗ **Запрещено** использовать "Premium" как название отдельного тарифа в документации.
> "Premium" = deprecated namespace, который требует PRO tier.

---

## 6️⃣ Аудит по наименованиям (фактические находки)

### ✅ Правильные паттерны

1. **`app/middleware/api_tiers.py`**:
   - ✅ `SubscriptionTier.FREE`, `SubscriptionTier.PRO`, `SubscriptionTier.VIP` — канонические уровни
   - ✅ `require_pro_tier()`, `require_vip_tier()` — чёткие middleware

2. **`app/routers/pro.py`**:
   - ✅ Комментарии: "PRO Tier Router", "PRO subscription tier"
   - ✅ Endpoints: `/api/v1/pro/*`
   - ✅ Требует: `require_pro_tier()`

3. **`app/routers/vip.py`**:
   - ✅ Комментарии: "VIP Module Router"
   - ✅ Endpoints: `/api/v1/vip/*`
   - ✅ Требует: `require_vip_tier()` (через `api_key_header`)

### ⚠️ Источники путаницы

1. **`app/routers/premium_week.py`**:
   - ⚠️ Название файла: `premium_week.py`
   - ⚠️ Namespace: `/api/v1/premium/*`
   - ✅ Но требует: `require_pro_tier()` (PRO tier)
   - ✅ Комментарий: "DEPRECATED: Use app.routers.pro instead"

2. **`app/routers/pro_registration.py`**:
   - ⚠️ Название: `pro_registration.py`
   - ✅ Регистрирует: PRO router + premium_week router
   - ✅ Комментарий: "PRO and premium_week router registration"

3. **`legacy_app.py`**:
   - ⚠️ Много endpoints под `/api/v1/premium/*`
   - ⚠️ Некоторые требуют VIP_MODULE_ENABLED (VIP tier)
   - ⚠️ Некоторые требуют PRO tier
   - ⚠️ Нет единообразия

### 🔴 Критические несоответствия

1. **`/api/v1/premium/plan/week`** (`app/routers/legacy_premium_weekly_plan.py:23`):
   - Требует: `VIP_MODULE_ENABLED` (VIP tier)
   - Но namespace: `/premium/*` (deprecated PRO namespace)
   - **Путаница:** premium namespace, но VIP tier

2. **Retired `/api/v1/premium/exports/*` test/demo aliases**:
   - Day/week CSV aliases no longer have a runtime route or tier contract.
   - Former `FEATURE_EXPORTS`, test, debug, and app-environment carriers do not
     restore them; requests receive the ordinary FastAPI 404.
   - Both canonical export families remain registered behind the canonical
     API-key dependency: plan sign/weekly CSV/PDF (`POST /api/v1/export/sign`,
     `GET /api/v1/plan/week/export.{csv,pdf}`) and shoplist JSON/CSV/PDF (`GET
     /api/v1/shoplist`, `GET /api/v1/shoplist/export.{csv,pdf}`).
   - `PRIVATE_EXPORTS_ENABLED` additionally enforces signed tokens only for
     weekly plan CSV/PDF; it controls neither route-family registration nor any
     shoplist route.

3. **`premium_week.py`**:
   - Файл называется `premium_week.py`
   - Но требует PRO tier (не "premium tier")
   - **Путаница:** название файла не соответствует tier

---

## 7️⃣ Каноническая модель (на основе кода)

### Продуктовые уровни (как определено в коде)

```text
FREE → PRO → VIP
```

#### Где определено
- `app/middleware/api_tiers.py:40-49` — `SubscriptionTier` enum

### Технические термины (legacy)

```text
pro_* = техническое имя (файлы, функции, переменные)
premium_* = deprecated namespace или legacy файлы
```

#### Где используется
- `pro_registration.py` — регистрация PRO routes
- `premium_week.py` — deprecated router (требует PRO tier)
- `shopping_list_pro.py` — PRO shopping list (требует PRO tier)

### API Namespaces (фактические)

```text
/api/v1/pro/*     → PRO tier (canonical)
/api/v1/vip/*     → VIP tier (canonical)
/api/v1/premium/* → deprecated (требует PRO или VIP, зависит от endpoint)
```

---

## Remediation Roadmap

This document is a **contract/specification** (what IS), not a remediation plan.

For action items, PR sequencing, and remediation steps, see:
- `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md`

---

## 🔟 Связь с другими документами

- `docs/audit/PR_510_AUDIT_EVIDENCE_PACK.md` — детальный анализ legacy_app.py
- `docs/audit/API_ALIGNMENT_CHECKLIST.md` — checklist для alignment
- `docs/contracts/API_CANONICAL_MAP.md` — текущий операторский mapping
- `app/middleware/api_tiers.py` — source of truth для уровней подписки

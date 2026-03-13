# 📊 PulsePlate — Canonical Product Tier Map (v1)

**Status:** Canonical (audit-driven, based on actual codebase)
**Last updated:** 2026-03-14
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

## 1️⃣ FREE — BMI / Screening

### Бизнес-смысл

* Бесплатный вход
* Диагностика / скрининг
* Основа всей системы

### Канонический домен

`core/bmi/*`

### API (канон)

| Тип            | Endpoint                | Статус      | Код-доказательство                          |
| -------------- | ----------------------- | ----------- | ------------------------------------------- |
| BMI calculate  | `/api/v1/bmi/calculate` | ✅ canonical | `app/routers/bmi_pro.py` (но FREE, не PRO)  |
| BMI legacy     | `/bmi`, `/api/v1/bmi`   | ⚠️ shim     | `legacy_app.py:2097, 2316`                  |
| Foods          | `/api/v1/foods/*`       | ✅ canonical | `app/routers/foods.py`                      |
| Recipes        | `/api/v1/recipes/*`     | ✅ canonical | `app/routers/recipes.py`                     |
| Users          | `/api/v1/users/*`       | ✅ canonical | `app/routers/users.py`                      |

### Правила

* ❌ никакой логики вне `core/bmi`
* ❌ никаких premium/vip зависимостей
* ✅ legacy endpoints = thin proxy

---

## 2️⃣ PRO — Nutrition / Targets / Daily Plate

### Средний платный сегмент

### Бизнес-смысл

* Питание
* Калории / нутриенты
* Day-level планы
* Без микро-ремонта и shoplist

### Канонический домен

**PRO Nutrition** (`app/routers/pro.py`)

> ✅ **Фактическое состояние:**
> PRO — это **реальный уровень подписки**, определённый в `SubscriptionTier.PRO`.
> Все endpoints требуют `require_pro_tier()` middleware.

### API (канон)

| Функция             | Endpoint                      | Статус      | Требует tier | Код-доказательство                    |
| -------------------- | ----------------------------- | ----------- | ------------ | ------------------------------------- |
| Weekly plan          | `/api/v1/pro/meal/weekly`     | ✅ canonical | PRO          | `app/routers/pro.py:245`              |
| Targets (WHO)       | `/api/v1/pro/nutrition/targets` | ✅ canonical | PRO          | `frontend/src/api/openapi.json:8158`  |
| Daily plate          | `/api/v1/pro/nutrition/daily` | ✅ canonical | PRO          | `app/routers/pro.py:369`              |
| Shopping list (PRO)  | `/api/v1/pro/meal/shopping-list` | ✅ canonical | PRO          | `app/routers/shopping_list_pro.py:19` |
| Shoplist day        | `/api/v1/pro/shoplist/*`      | ✅ canonical | PRO          | `app/routers/shoplist_day.py:22`      |
| Nutrition log       | `/api/v1/pro/nutrition/log/*` | ✅ canonical | PRO          | `app/routers/nutrition_log.py:27`     |
| Bayes adherence     | `/api/v1/pro/bayes/*`         | ✅ canonical | PRO          | `app/routers/bayes_adherence.py:23`   |

### Deprecated (но требует PRO tier)

| Функция        | Endpoint                        | Статус           | Требует tier | Код-доказательство                        |
| -------------- | ------------------------------- | ---------------- | ------------ | ----------------------------------------- |
| Weekly plan    | `/api/v1/premium/plan/week-flexible` | ⚠️ deprecated | PRO          | `app/routers/premium_week.py:290`         |
| Targets        | `/api/v1/premium/targets`       | ⚠️ legacy shim   | PRO          | `legacy_app.py:4685`                      |
| Daily plate    | `/api/v1/premium/plate`         | ⚠️ legacy shim   | PRO          | `legacy_app.py:3980`                      |
| BMR            | `/premium_bmr`                  | ⚠️ legacy        | PRO          | `legacy_app.py:4148`                      |

> ⚠️ **Примечание:** Endpoints под `/premium/*`, которые **фактически требуют VIP tier**, не относятся к PRO и перечислены в разделе VIP (см. секцию "Deprecated aliases with wrong namespace").
>
> ⚠️ **Ключевое понимание:**
> `/premium/*` endpoints **требуют PRO tier** (через `require_pro_tier()`);
> namespace `/premium/*` при этом **deprecated**, мигрирует на `/api/v1/pro/*`.

### Что НЕ входит

* ❌ weekly plan с авто-ремонтом (это VIP)
* ❌ shoplist с региональной логикой (это VIP)
* ❌ микро-constraints (это VIP)

### Правила

* PRO endpoints используют `require_pro_tier()` middleware
* `pro_registration.py` = **технический модуль регистрации**, не бизнес-уровень
* `premium_week.py` = **deprecated**, мигрирует на `pro.py`

### FitChef structured coach follow-up (contract-frozen, not live)

| Функция | Endpoint | Статус | Требует tier | Canonical reference |
| --- | --- | --- | --- | --- |
| FitChef explain | `/api/v1/pro/fitchef/explain` | 🧭 contract-frozen | PRO | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |
| FitChef recommend | `/api/v1/pro/fitchef/recommend` | 🧭 contract-frozen | PRO | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |

> Эти endpoints ещё не реализованы. PR-4 фиксирует только route family и tier semantics для будущего PRO structured coach runtime.

---

## 3️⃣ VIP — Weekly / Micro / Shoplist

### Высший платный сегмент

### Бизнес-смысл

* Weekly plan с микро-constraints
* Auto-repair
* Shoplist / region
* Recipe synthesis
* Exports

### Канонический домен

**VIP Planning Engine** (`app/routers/vip.py`, `app/routers/vip_shoplist.py`)

### API (канон)

| Функция              | Endpoint                           | Статус      | Требует tier | Код-доказательство                        |
| -------------------- | ---------------------------------- | ----------- | ------------ | ----------------------------------------- |
| Weekly plan          | `/api/v1/vip/menu/weekly/plan`     | ✅ canonical | VIP          | `app/routers/vip.py` (main endpoint)      |
| Weekly plan (legacy) | `/api/v1/vip/weekly-plan`         | ⚠️ deprecated | VIP        | `app/routers/vip.py:733` (deprecated)     |
| Insight              | `/api/v1/insight`                 | ⚠️ flag     | VIP          | `legacy_app.py:2443` (`FEATURE_INSIGHT`, VIP guard) |
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
| Weekly plan   | `/api/v1/premium/plan/week`  | 🔴 **broken naming** | VIP (через VIP_MODULE_ENABLED) | Wrong namespace (`/premium/*` вместо `/vip/*`) | `/api/v1/vip/menu/weekly/plan` | `legacy_app.py:4706`               |
| Exports       | `/api/v1/premium/exports/*`  | ⚠️ legacy     | VIP          | Wrong namespace | `/api/v1/vip/shoplist/export` | `legacy_app.py:5194, 5440, 5525`  |

> ⚠️ **Ключевая проблема:**
> Эти endpoints требуют **VIP tier**, но живут под `/premium/*` namespace (deprecated PRO namespace) → **архитектурная путаница**.
> **Remediation:** See `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md` (PR-C: delegation pattern).

### Правила

* VIP ≠ PRO
* VIP может зависеть от PRO данных
* ❌ PRO не может реализовывать VIP-логику
* VIP endpoints используют `require_vip_tier()` middleware

### FitChef structured coach follow-up (contract-frozen, not live)

| Функция | Endpoint | Статус | Требует tier | Canonical reference |
| --- | --- | --- | --- | --- |
| FitChef insight | `/api/v1/vip/fitchef/insight` | 🧭 contract-frozen | VIP | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |
| FitChef chat | `/api/v1/vip/fitchef/chat` | 🧭 contract-frozen | VIP | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |
| FitChef week repair | `/api/v1/vip/fitchef/week-repair` | 🧭 contract-frozen | VIP | `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md` |

> Эти endpoints ещё не реализованы. PR-4 фиксирует additive structured coach contract, при этом live `/api/v1/insight/fitchef*` family остаётся каноном.

---

## 4️⃣ Legacy / Shim слой (явно признаём)

### Что сюда относится

* `legacy_app.py` endpoints
* `/premium_*` (без `/api/v1/`)
* `/plan`, `/api/nutrition/{date}`
* `/bmi`, `/premium_bmr`

### Назначение

* Совместимость
* Переходный слой

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

1. **`/api/v1/premium/plan/week`** (`legacy_app.py:4706`):
   - Требует: `VIP_MODULE_ENABLED` (VIP tier)
   - Но namespace: `/premium/*` (deprecated PRO namespace)
   - **Путаница:** premium namespace, но VIP tier

2. **`/api/v1/premium/exports/*`** (`legacy_app.py:5194, 5440, 5525`):
   - Требует: `EXPORTS_ENABLED` flag
   - Но namespace: `/premium/*`
   - **Путаница:** неясно, какой tier требуется

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

* `docs/audit/PR_510_AUDIT_EVIDENCE_PACK.md` — детальный анализ legacy_app.py
* `docs/audit/API_ALIGNMENT_CHECKLIST.md` — checklist для alignment
* `docs/contracts/API_CANONICAL_MAP.md` — текущий операторский mapping
* `app/middleware/api_tiers.py` — source of truth для уровней подписки

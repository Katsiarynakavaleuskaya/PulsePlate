# 📋 Текущий статус работы - PulsePlate

**Дата обновления**: 2025-12-14
**Текущая ветка**: `fix/calorie-distributor-lazy-init`

---

## 🎯 Две основные задачи

### 1. 🔬 Фикс байесовского модуля (Issue #286)

**Документ**: `BAYESIAN_ROLLOUT_PLAN_SMALL_PRS.md`

**Статус**: 3/10 PRs завершено ✅

#### ✅ Завершенные PRs

- **PR #287** - CI/CD Infrastructure ✅
- **PR #293** - Database Models ✅
- **PR #294** - Core Bayesian Modules ✅

#### 🔄 В процессе / Частично готово

- Business Analyzers & API (`app/routers/business.py`) - работает, но нужно проверить полноту

#### 📋 Осталось сделать (7 PRs)

**Phase 4: Enhanced Nutrition Features** (3 PRs)

- **PR 4.1**: Nutrition Core Utilities (~15 files) - ✅ ЗАВЕРШЕНО (PR #327, #330, #334)
- **PR 4.2**: Meal Planning Engine (~18 files) - ✅ ЗАВЕРШЕНО (PR #335)
- **PR 4.3**: Nutrition API Endpoints (~12 files) - ⚠️ **В ПРОЦЕССЕ**

**Phase 5: Business Features Verification** (1 PR)

- **PR 5.1**: Business Analyzer Audit (~10 files) - ❌ **НЕ НАЧАТО**

**Phase 6: API Integration Completion** (1 PR)

- **PR 6.1**: Additional Bayesian Endpoints (~15 files) - ❌ **НЕ НАЧАТО**

**Phase 7-10**: Migrations, Docs, Tests, Cleanup (4 PRs) - ❌ **НЕ НАЧАТО**

---

### 2. 🔄 Дублирование эндпойнтов и стандартизация для iOS (VIP/PRO)

**Документ**: `ENDPOINT_AUDIT_MOBILE_FOCUS.md`

**Статус**: Частично решено в PR #336 "Feat/api consolidation mobile"

#### ✅ Уже сделано (PR #336)

- [x] Создан API tier middleware (`app/middleware/api_tiers.py`) ✅
- [x] Добавлены deprecation warnings для legacy endpoints ✅
- [x] Добавлена API key validation для premium endpoints ✅
- [x] Удален duplicate endpoint `/vip/recipe/synthesize` ✅
- [x] Созданы comprehensive tests для middleware (22 теста) ✅

#### ⚠️ Проблемы, которые остались

**Issue #1: Дублирование Meal Planning Endpoints**

```plaintext
1. /api/v1/premium/plan/week-flexible   (premium_week.py) - ✅ Теперь с API KEY
2. /api/v1/vip/menu/weekly/plan         (vip.py) - ✅ STRICT API KEY
3. /api/v1/vip/weekly-plan              (vip.py) - ⚠️ DEPRECATED, но еще существует
```

**Рекомендация**:

- ✅ `/api/v1/vip/weekly-plan` помечен как deprecated
- ❓ Нужно решить: удалить полностью или оставить для обратной совместимости?

**Issue #2: Несогласованность структуры для iOS**

**Текущая структура**:

```plaintext
/api/v1/bmi/*        (FREE)
/api/v1/foods/*      (FREE)
/api/v1/recipes/*    (FREE)
/api/v1/users/*      (Internal, API key, hidden from public OpenAPI)
/api/v1/premium/*    (PRO) ✅ Теперь с API key
/api/v1/vip/*        (VIP) ✅ С API key
```

**Предложенная структура для iOS** (из ENDPOINT_AUDIT):

```plaintext
/api/v1/pro/bmi/advanced    - BMI Pro с WHR, WHTR, FFMI
/api/v1/pro/meal/weekly     - Weekly meal plan (macros only)
/api/v1/pro/meal/daily      - Daily meal plan
/api/v1/pro/nutrition/targets - WHO-based nutrition goals

/api/v1/vip/meal/weekly/plan     - Weekly plan с micronutrients
/api/v1/vip/meal/weekly/repair   - Auto-repair meal plans
/api/v1/vip/shoplist/generate    - AI shopping list
```

**Проблема**: Текущая структура использует `/premium/*` для PRO, но для iOS лучше `/pro/*`

---

## 🎯 План действий

### ✅ Приоритет 1: Завершить стандартизацию эндпойнтов для iOS - ЗАВЕРШЕНО

**Задача**: Привести эндпойнты к стандартам iOS приложения

**✅ Выполненные шаги**:

1. ✅ **Создан `/api/v1/pro/*` роутер** (`app/routers/pro.py`)
   - ✅ Перемещена логика из `/premium/*` в `/pro/*`
   - ✅ Используется `require_pro_tier` middleware
   - ✅ Сохранена обратная совместимость через deprecation warning

2. ⚠️ **Унифицировать структуру VIP endpoints** (частично)
   - ✅ `/api/v1/vip/weekly-plan` помечен как deprecated
   - ❓ Нужно решить: удалить полностью или оставить для обратной совместимости

3. ✅ **Обновлена документация**
   - ✅ Обновлен `ENDPOINT_AUDIT_MOBILE_FOCUS.md` с новой структурой
   - ✅ Добавлена информация о миграции

4. ✅ **Тесты**
   - ✅ Создан `tests/test_pro_router.py` с comprehensive тестами
   - ✅ Проверена обратная совместимость

**✅ Измененные файлы**:

- ✅ `app/routers/pro.py` (создан)
- ✅ `app/routers/premium_week.py` (помечен как deprecated)
- ✅ `app/routers/vip.py` (уже имеет deprecated `/weekly-plan`)
- ✅ `app.py` (добавлен новый роутер)
- ✅ `app/routers/__init__.py` (добавлен экспорт)
- ✅ `tests/test_pro_router.py` (создан)
- ✅ `ENDPOINT_AUDIT_MOBILE_FOCUS.md` (обновлен)

**Новые endpoints**:

- ✅ `POST /api/v1/pro/meal/weekly` - Weekly meal plan (PRO tier)

**Deprecated endpoints** (все еще работают):

- ⚠️ `POST /api/v1/premium/plan/week-flexible` - DEPRECATED, используйте `/api/v1/pro/meal/weekly`
- ⚠️ `POST /api/v1/vip/weekly-plan` - DEPRECATED, используйте `/api/v1/vip/menu/weekly/plan`

---

### Приоритет 2: Завершить байесовский модуль

**Задача**: Завершить интеграцию байесовского модуля согласно плану

**Следующие шаги**:

1. **PR 4.3: Nutrition API Endpoints** (~12 files)
   - Создать `app/routers/nutrition.py`
   - Добавить endpoints для nutrition planning
   - Интегрировать с существующими VIP/PRO endpoints

2. **PR 5.1: Business Analyzer Audit** (~10 files)
   - Проверить полноту `app/routers/business.py`
   - Убедиться, что все features из оригинального PR #266 присутствуют
   - Добавить недостающую логику (если есть)

3. **PR 6.1: Additional Bayesian Endpoints** (~15 files)
   - Создать `app/routers/bayesian.py`
   - Добавить endpoints для Bayesian analysis
   - Интегрировать с subscription tiers

---

## 📝 Текущие изменения в ветке

**Ветка**: `fix/calorie-distributor-lazy-init`

**Изменения**:

- `.cursor-settings.json` - оптимизированы настройки редактора
- `scripts/fix_qoder_hang.sh` - скрипт для исправления зависаний Qoder
- `scripts/setup_qoder.sh` - скрипт для настройки Qoder

**Последние коммиты**:

- `9bce5925` - fix: test_test_router.py failures
- `7b331be7` - fix: address all CodeRabbit feedback
- `89a60e0f` - refactor: improve lazy initialization (Sourcery AI feedback)
- `228f12ab` - refactor: revert to lazy initialization for `_meal_lookup` cache

---

## 🤔 Вопросы для обсуждения

1. **Deprecated endpoint `/api/v1/vip/weekly-plan`**:
   - Удалить полностью или оставить для обратной совместимости?
   - Какой timeline для миграции iOS app?

2. **Структура PRO endpoints**:
   - Переименовать `/premium/*` в `/pro/*` или оставить как есть?
   - Нужна ли обратная совместимость?

3. **Приоритеты**:
   - Что важнее сейчас: завершить байесовский модуль или стандартизировать endpoints для iOS?
   - Можно ли работать параллельно?

---

## 📚 Связанные документы

- `BAYESIAN_ROLLOUT_PLAN_SMALL_PRS.md` - План интеграции байесовского модуля
- `ENDPOINT_AUDIT_MOBILE_FOCUS.md` - Аудит эндпойнтов для мобильного приложения
- `PREMIUM_TARGETS_API.md` - Документация Premium Targets API
- `VIP_API_KEY_CONFIGURATION.md` - Конфигурация VIP API ключей
- `docs/MOBILE_API_MIGRATION_GUIDE.md` - Гайд по миграции для мобильных разработчиков

---

## ✅ Чеклист для следующего PR

### ✅ Вариант A: Стандартизация эндпойнтов для iOS - ЗАВЕРШЕНО

- [x] Создать `app/routers/pro.py` с PRO endpoints ✅
- [x] Переместить логику из `premium_week.py` в `pro.py` ✅
- [x] Добавить deprecation warning для обратной совместимости ✅
- [x] Пометить `/api/v1/vip/weekly-plan` как deprecated ✅
- [x] Обновить документацию ✅
- [x] Добавить тесты ✅
- [x] Обновить `ENDPOINT_AUDIT_MOBILE_FOCUS.md` ✅

**Следующие шаги** (опционально):

- [ ] Добавить остальные PRO endpoints (BMI advanced, daily meal, nutrition targets)
- [ ] Решить судьбу deprecated endpoints (удалить или оставить)
- [ ] Обновить iOS app для использования новых endpoints

### Вариант B: Завершение байесовского модуля (PR 4.3)

- [ ] Создать `app/routers/nutrition.py`
- [ ] Добавить nutrition planning endpoints
- [ ] Интегрировать с VIP/PRO tiers
- [ ] Добавить тесты
- [ ] Обновить документацию
- [ ] Обновить `BAYESIAN_ROLLOUT_PLAN_SMALL_PRS.md`

---

**Следующий шаг**: Решить, с какой задачи начать (стандартизация endpoints или байесовский модуль)

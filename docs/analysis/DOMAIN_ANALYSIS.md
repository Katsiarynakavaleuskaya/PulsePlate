# 📊 PulsePlate — Детальный анализ субдоменов

**Дата:** 2026-01-28
**Статус:** Канонический анализ архитектуры
**Версия:** 1.0

---

## 🎯 Обзор

Проект PulsePlate разбит на **10 основных субдоменов**, каждый из которых отвечает за отдельную бизнес-область. Этот документ содержит детальный анализ каждого субдомена: архитектура, компоненты, зависимости, тесты, проблемы и рекомендации.

---

## 📋 Содержание

1. [BMI Calculation Domain](#1-bmi-calculation-domain)
2. [Nutrition Planning Domain](#2-nutrition-planning-domain)
3. [Food Database Domain](#3-food-database-domain)
4. [Meal Planning Domain](#4-meal-planning-domain)
5. [Shopping List Domain](#5-shopping-list-domain)
6. [VIP Features Domain](#6-vip-features-domain)
7. [User Management Domain](#7-user-management-domain)
8. [Analytics/Bayesian Domain](#8-analyticsbayesian-domain)
9. [Catalog Domain](#9-catalog-domain)
10. [Recipe Domain](#10-recipe-domain)

---

## 1. BMI Calculation Domain

### 🎯 Назначение

**Единый источник истины** для всех расчетов BMI, категоризации и оценки рисков по окружности талии.

### 📁 Структура

```
core/bmi/
├── __init__.py          # Public API экспорт
├── engine.py            # Основной BMI engine (canonical)
├── risk.py              # Оценка рисков по талии (WHR, WHtR)
└── compat_plan.py       # Совместимость с legacy планами
```

### 🔑 Ключевые компоненты

#### `core/bmi/engine.py`
- **`BMICalculateResult`** — канонический результат расчета
- **`calculate_bmi()`** — основная функция расчета
- **`get_bmi_category()`** — категоризация (underweight, normal, overweight, obesity_1/2/3)
- **`get_bmi_visual_ranges()`** — диапазоны для визуализации
- **Поддержка групп:** `general`, `child`, `teen`, `athlete`, `elderly`, `pregnant`

#### `core/bmi/risk.py`
- **`WaistRiskResult`** — результат оценки риска по талии
- **`calculate_waist_risk()`** — расчет WHtR и уровня риска
- **Пороги риска:**
  - FREE/Simple: 0.90 (male), 0.85 (female)
  - PRO: 0.95 (male), 0.80 (female)

### 🛡️ Архитектурные инварианты

1. **Один BMI Engine** — все расчеты только через `core/bmi/engine.py`
2. **Запрет дублирования** — guard-тесты блокируют BMI-математику вне `core/bmi/*`
3. **Legacy = thin proxy** — `legacy_app.py` только делегирует, без логики

### 🔗 Зависимости

**Зависит от:**
- `core.i18n` — локализация сообщений
- `core.bmi.risk` — расчет рисков

**Используется:**
- `app/routers/bmi.py` — FREE tier endpoints
- `app/routers/bmi_pro.py` — PRO tier endpoints (расширенный BMI)
- `legacy_app.py` — legacy shims

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/bmi/calculate` | FREE | ✅ canonical | `app/routers/bmi.py` |
| `/api/v1/pro/bmi` | PRO | ✅ canonical | `app/routers/bmi_pro.py` |
| `/bmi`, `/api/v1/bmi` | FREE | ⚠️ legacy shim | `legacy_app.py` |

### 🧪 Тестирование

**Guard-тесты:**
- `tests/test_bmi_canonical_guard.py` — один BMI Engine
- `tests/test_no_bmi_math_outside_core.py` — запрет дублирования

**Unit-тесты:**
- `tests/test_bmi_engine.py` — основные расчеты
- `tests/test_bmi_risk.py` — оценка рисков
- `tests/test_bmi_extras_pro_coverage.py` — PRO tier расширения

**Coverage:** ≥97% (enforced)

### ⚠️ Проблемы

1. **Legacy endpoints** — `/bmi`, `/api/v1/bmi` еще работают (deprecated)
2. **Дублирование в legacy** — `bmi_core.py` (legacy shim) требует поддержки

### ✅ Рекомендации

1. ✅ **Завершено:** Консолидация в `core/bmi/engine.py`
2. 📋 **В планах:** Удаление legacy endpoints после миграции клиентов
3. 📋 **Оптимизация:** Кэширование результатов для одинаковых входных данных

---

## 2. Nutrition Planning Domain

### 🎯 Назначение

Расчет персональных целей по питанию на основе рекомендаций ВОЗ/EFSA/DRI, включая макро- и микронутриенты.

### 📁 Структура

```
core/
├── targets.py              # UserProfile, NutritionTargets, MacroTargets, MicroTargets
├── recommendations.py       # build_nutrition_targets() — основной entry point
├── rules_who.py            # WHO/EFSA/DRI правила и константы
├── plate.py                # Визуализация тарелки (My Plate)
├── daily_plate.py          # Daily plate generation
└── nutrition_constants.py  # Константы питания
```

### 🔑 Ключевые компоненты

#### `core/targets.py`
- **`UserProfile`** — профиль пользователя (sex, age, height, weight, activity, goal)
- **`NutritionTargets`** — полные цели (макро + микро + гидратация + активность)
- **`MacroTargets`** — белки, жиры, углеводы, клетчатка
- **`MicronutrientTargets`** — микронутриенты с диапазонами (min, target, max)
- **`ActivityTargets`** — цели по физической активности

#### `core/recommendations.py`
- **`build_nutrition_targets(profile: UserProfile) -> NutritionTargets`**
  - Расчет BMR/TDEE (через `nutrition_core`)
  - Расчет макронутриентов (WHO guidelines)
  - Расчет микронутриентов (RDA/UL)
  - Расчет гидратации
  - Адаптация под цели (loss/maintain/gain)

#### `core/rules_who.py`
- **`get_micronutrient_rda()`** — RDA для микронутриентов
- **`get_fiber_target()`** — целевое потребление клетчатки
- **`calculate_hydration_target()`** — целевое потребление воды
- **`GOAL_MACRO_ADJUSTMENTS`** — корректировки макро под цели

### 🛡️ Архитектурные принципы

1. **Детерминированность** — одинаковые входы → одинаковые выходы
2. **WHO-based** — все рекомендации основаны на международных стандартах
3. **Tier-specific** — FREE vs PRO vs VIP используют разные уровни детализации

### 🔗 Зависимости

**Зависит от:**
- `nutrition_core` — расчет BMR/TDEE (Harris-Benedict, Mifflin-St Jeor, Katch-McArdle)
- `core.time_utils` — временные утилиты

**Используется:**
- `app/routers/pro.py` — PRO tier endpoints (`/api/v1/pro/nutrition/targets`, `/api/v1/pro/nutrition/daily`)
- `app/routers/premium_week.py` — deprecated PRO endpoints
- `core/menu_engine.py` — генерация меню на основе целей

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/pro/nutrition/targets` | PRO | ✅ canonical | `app/routers/pro.py` |
| `/api/v1/pro/nutrition/daily` | PRO | ✅ canonical | `app/routers/pro.py` |
| `/api/v1/premium/targets` | PRO | ⚠️ legacy shim | `legacy_app.py` |
| `/api/v1/premium/plate` | PRO | ⚠️ legacy shim | `legacy_app.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_targets.py` — валидация профилей и целей
- `tests/test_recommendations.py` — расчет целей
- `tests/test_rules_who.py` — WHO правила
- `tests/test_plate.py` — визуализация тарелки

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Legacy endpoints** — `/premium/targets`, `/premium/plate` требуют миграции
2. **Дублирование** — `daily_plate.py` vs `plate.py` (частичное перекрытие)

### ✅ Рекомендации

1. ✅ **Завершено:** Консолидация в `core/targets.py` и `core/recommendations.py`
2. 📋 **В планах:** Удаление legacy endpoints
3. 📋 **Рефакторинг:** Объединение `daily_plate.py` и `plate.py` в единый модуль

---

## 3. Food Database Domain

### 🎯 Назначение

Управление базой данных продуктов питания с автоматическим слиянием данных из USDA FoodData Central и Open Food Facts.

### 📁 Структура

```
core/food_apis/
├── __init__.py
├── unified_db.py          # Единый интерфейс к базам данных
├── usda_client.py         # USDA FoodData Central клиент
├── openfoodfacts_client.py # Open Food Facts клиент
├── update_manager.py      # Управление обновлениями (checksum, кэш)
└── scheduler.py            # Автоматические обновления (CRON)

core/food_sources/
├── base.py                # Базовый адаптер
├── usda.py                # USDA адаптер
└── off.py                 # Open Food Facts адаптер

core/
├── food_merge.py          # Логика слияния данных
├── aliases.py             # Каноническое маппинг имен
└── units.py               # Конвертация единиц измерения
```

### 🔑 Ключевые компоненты

#### `core/food_apis/unified_db.py`
- **`UnifiedFoodItem`** — унифицированный формат продукта
- **`UnifiedFoodDB`** — единый интерфейс к базам данных
- **`from_usda_item()`**, **`from_off_item()`** — конвертация форматов

#### `core/food_apis/update_manager.py`
- **`DatabaseUpdateManager`** — управление обновлениями
- **Checksum validation** — проверка изменений перед обновлением
- **Caching** — кэширование для производительности

#### `core/food_apis/scheduler.py`
- **`DatabaseUpdateScheduler`** — автоматические еженедельные обновления
- **CRON integration** — интеграция с системным планировщиком

#### `core/food_merge.py`
- **`merge_food_data()`** — слияние данных из разных источников
- **Priority rules** — приоритеты источников (USDA > OFF)
- **Conflict resolution** — разрешение конфликтов данных

### 🛡️ Архитектурные принципы

1. **Unified interface** — единый интерфейс для всех источников
2. **Lazy loading** — данные загружаются по требованию
3. **Caching** — агрессивное кэширование для производительности
4. **Automatic updates** — еженедельные автоматические обновления

### 🔗 Зависимости

**Зависит от:**
- `httpx` — HTTP клиент для API запросов
- `core.aliases` — каноническое маппинг имен
- `core.units` — конвертация единиц

**Используется:**
- `app/routers/foods.py` — FREE tier endpoints (`/api/v1/foods/*`)
- `core/menu_engine.py` — генерация меню
- `core/meal_planner.py` — планирование питания

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/foods/search` | FREE | ✅ canonical | `app/routers/foods.py` |
| `/api/v1/foods/{food_id}` | FREE | ✅ canonical | `app/routers/foods.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_food_apis_unified_db.py` — unified interface
- `tests/test_food_merge.py` — слияние данных
- `tests/test_food_apis_update_manager.py` — управление обновлениями
- `tests/test_food_apis_scheduler.py` — автоматические обновления

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Производительность** — большие объемы данных могут замедлять загрузку
2. **Конфликты данных** — разрешение конфликтов между источниками требует улучшения
3. **Кэширование** — стратегия кэширования может быть оптимизирована

### ✅ Рекомендации

1. ✅ **Завершено:** Unified interface и автоматические обновления
2. 📋 **Оптимизация:** Индексация базы данных для быстрого поиска
3. 📋 **Масштабирование:** Потенциальная миграция на PostgreSQL для больших объемов

---

## 4. Meal Planning Domain

### 🎯 Назначение

Генерация ежедневных и еженедельных планов питания на основе целей пользователя и доступных продуктов.

### 📁 Структура

```
core/
├── menu_engine.py          # Основной engine генерации меню
├── meal_planner.py         # Планировщик питания
├── meal_optimizer.py       # Оптимизация меню
├── meal_types.py           # Типы блюд и приемов пищи
├── calorie_distributor.py  # Распределение калорий по приемам
├── dietary_constraints.py  # Диетические ограничения (VEG, GF, etc.)
└── weekly_plan.py          # Еженедельные планы (legacy)
```

### 🔑 Ключевые компоненты

#### `core/menu_engine.py`
- **`make_daily_menu()`** — генерация дневного меню
- **`make_weekly_menu()`** — генерация недельного меню
- **`analyze_nutrient_gaps()`** — анализ пробелов в питании
- **`repair_week_plan()`** — авто-ремонт недельного плана (VIP)
- **`DayMenu`**, **`WeekMenu`** — структуры данных меню

#### `core/meal_planner.py`
- **`MealPlanner`** — планировщик питания
- **`plan_meals()`** — планирование приемов пищи
- **`optimize_nutrient_coverage()`** — оптимизация покрытия нутриентов

#### `core/meal_optimizer.py`
- **`MealOptimizer`** — оптимизатор меню
- **`optimize_for_goals()`** — оптимизация под цели пользователя

#### `core/calorie_distributor.py`
- **`CalorieDistributor`** — распределение калорий
- **`distribute_calories()`** — распределение по приемам пищи

### 🛡️ Архитектурные принципы

1. **Profile-driven** — все планы основаны на `UserProfile`
2. **Goal-oriented** — адаптация под цели (loss/maintain/gain)
3. **Constraint-aware** — учет диетических ограничений
4. **Nutrient coverage** — анализ покрытия нутриентов

### 🔗 Зависимости

**Зависит от:**
- `core.targets` — цели питания
- `core.food_apis` — база данных продуктов
- `core.recipe_db` — база рецептов

**Используется:**
- `app/routers/pro.py` — PRO tier endpoints (`/api/v1/pro/meal/weekly`)
- `app/routers/vip.py` — VIP tier endpoints (`/api/v1/vip/menu/weekly/plan`)
- `app/routers/premium_week.py` — deprecated PRO endpoints

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/pro/meal/weekly` | PRO | ✅ canonical | `app/routers/pro.py` |
| `/api/v1/vip/menu/weekly/plan` | VIP | ✅ canonical | `app/routers/vip.py` |
| `/api/v1/premium/plan/week-flexible` | PRO | ⚠️ deprecated | `app/routers/premium_week.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_menu_engine.py` — генерация меню
- `tests/test_meal_planner.py` — планирование питания
- `tests/test_meal_optimizer.py` — оптимизация меню
- `tests/test_calorie_distributor.py` — распределение калорий

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Дублирование** — `menu_engine.py` vs `menu_engine_new.py` (legacy)
2. **Производительность** — генерация недельных планов может быть медленной
3. **Сложность** — логика оптимизации сложна для понимания

### ✅ Рекомендации

1. ✅ **Завершено:** Консолидация в `core/menu_engine.py`
2. 📋 **Рефакторинг:** Удаление `menu_engine_new.py` после полной миграции
3. 📋 **Оптимизация:** Кэширование часто используемых планов
4. 📋 **Упрощение:** Разбиение сложной логики на более мелкие функции

---

## 5. Shopping List Domain

### 🎯 Назначение

Генерация списков покупок на основе планов питания с агрегацией ингредиентов, нормализацией единиц и упаковкой.

### 📁 Структура

```
core/shoplist_engine/
├── __init__.py            # Public API
├── models.py              # Доменные модели (Unit, Quantity, FoodRef, IngredientSpec, ShoplistLine)
├── engine.py              # ShoplistEngine orchestrator
├── normalizer.py          # Нормализация единиц и количеств
├── aggregator.py          # Агрегация ингредиентов
└── packager.py            # Упаковка (округление до упаковок)

app/core/shopping_list/
├── extractor.py           # Извлечение ингредиентов из планов
├── generator.py           # Генератор списков покупок
├── categories.py           # Категоризация продуктов
└── normalize.py           # Нормализация для API

app/core/shoplist_day/
├── day_generator.py       # Генерация дневных списков
├── flatten.py             # Уплощение структуры
└── provider.py            # Provider для дневных списков
```

### 🔑 Ключевые компоненты

#### `core/shoplist_engine/models.py`
- **`Unit`** — единицы измерения (G, KG, ML, L, PCS)
- **`Quantity`** — количество с единицей
- **`FoodRef`** — ссылка на продукт (food_id)
- **`IngredientSpec`** — спецификация ингредиента (вход в engine)
- **`ShoplistLine`** — строка списка покупок (выход)
- **`PackageRule`** — правила упаковки
- **`PackPlan`** — план упаковки

#### `core/shoplist_engine/engine.py`
- **`ShoplistEngine`** — stateless orchestrator
- **`generate_shoplist()`** — генерация списка покупок
- **Pipeline:** normalize → aggregate → package

#### `core/shoplist_engine/normalizer.py`
- **`normalize_specs()`** — нормализация ингредиентов
- **`normalize_quantity()`** — нормализация количеств к базовым единицам
- **`normalize_ingredient()`** — нормализация ингредиентов

#### `core/shoplist_engine/aggregator.py`
- **`aggregate_specs()`** — агрегация ингредиентов по food_id
- **Суммирование** — объединение одинаковых продуктов

#### `core/shoplist_engine/packager.py`
- **`apply_packaging()`** — применение правил упаковки
- **`compute_packs()`** — расчет количества упаковок
- **`RoundingMode`** — режимы округления (UP, DOWN, NEAREST)

### 🛡️ Архитектурные принципы

1. **Offline-first** — детерминированная логика без I/O
2. **Pure functions** — все функции чистые (no side effects)
3. **Decimal math** — точные расчеты с Decimal
4. **Immutable models** — все модели frozen dataclasses

### 🔗 Зависимости

**Зависит от:**
- `core.food_apis` — база данных продуктов (для food_id resolution)
- `core.menu_engine` — планы питания (источник ингредиентов)

**Используется:**
- `app/routers/vip_shoplist.py` — VIP tier endpoints
- `app/routers/shopping_list_pro.py` — PRO tier endpoints
- `app/routers/shoplist_day.py` — дневные списки
- `app/services/shoplist_export/` — экспорт (CSV, PDF)

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/vip/shoplist/generate` | VIP | ✅ canonical | `app/routers/vip_shoplist.py` |
| `/api/v1/vip/shoplist/preview` | VIP | ✅ canonical | `app/routers/vip_shoplist.py` |
| `/api/v1/vip/shoplist/daily` | VIP | ✅ canonical | `app/routers/vip_shoplist.py` |
| `/api/v1/vip/shoplist/weekly` | VIP | ✅ canonical | `app/routers/vip_shoplist.py` |
| `/api/v1/pro/meal/shopping-list` | PRO | ✅ canonical | `app/routers/shopping_list_pro.py` |
| `/api/v1/pro/shoplist/*` | PRO | ✅ canonical | `app/routers/shoplist_day.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_shoplist_engine.py` — engine логика
- `tests/test_shoplist_normalizer.py` — нормализация
- `tests/test_shoplist_aggregator.py` — агрегация
- `tests/test_shoplist_packager.py` — упаковка

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Сложность** — много слоев (normalize → aggregate → package)
2. **Тестирование** — сложность тестирования интеграции всех слоев
3. **Документация** — не хватает примеров использования

### ✅ Рекомендации

1. ✅ **Завершено:** Чистая доменная модель с immutable models
2. 📋 **Документация:** Добавить примеры использования в docstrings
3. 📋 **Тестирование:** Добавить интеграционные тесты для полного pipeline

---

## 6. VIP Features Domain

### 🎯 Назначение

Продвинутые функции VIP уровня: микронутриентные цели, авто-ремонт меню, региональные списки покупок, синтез рецептов.

### 📁 Структура

```
app/routers/
├── vip.py                 # Основной VIP router
├── vip_shoplist.py        # VIP списки покупок
├── vip_registration.py    # Регистрация VIP routes

core/
├── auto_repair.py         # Авто-ремонт недельных планов
├── shoplist_preview/      # Preview списков покупок
│   └── preview_service.py
└── region_catalog.py      # Региональные каталоги
```

### 🔑 Ключевые компоненты

#### `app/routers/vip.py`
- **`/api/v1/vip/menu/weekly/plan`** — недельное планирование с микронутриентами
- **`/api/v1/vip/recipes/synthesize`** — синтез рецептов
- **`/api/v1/vip/auto-repair/*`** — авто-ремонт планов
- **`require_vip_tier()`** — middleware для проверки VIP tier

#### `app/routers/vip_shoplist.py`
- **`/api/v1/vip/shoplist/generate`** — генерация списков покупок
- **`/api/v1/vip/shoplist/preview`** — preview списков
- **`/api/v1/vip/shoplist/daily`** — дневные списки
- **`/api/v1/vip/shoplist/weekly`** — недельные списки
- **Интеграция с каталогами** — обогащение списков ценами и магазинами

#### `core/auto_repair.py`
- **`repair_week_plan()`** — авто-ремонт недельного плана
- **Стратегии ремонта:**
  - Boosters — добавление продуктов-бустеров
  - Replace — замена блюд
  - Snacks — добавление перекусов

#### `core/shoplist_preview/preview_service.py`
- **`build_preview()`** — построение preview списка покупок
- **Аналитика** — статистика по списку (стоимость, категории)

### 🛡️ Архитектурные принципы

1. **VIP-only** — функции доступны только VIP tier
2. **Feature flags** — `VIP_MODULE_ENABLED` для включения/выключения
3. **Contract-driven** — строгие контракты для VIP endpoints
4. **Offline-first** — детерминированная логика без внешних зависимостей

### 🔗 Зависимости

**Зависит от:**
- `core.menu_engine` — генерация меню
- `core.shoplist_engine` — генерация списков покупок
- `core.catalog` — региональные каталоги
- `core.recipe_synth` — синтез рецептов

**Используется:**
- VIP клиенты (iOS, Web)

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/vip/menu/weekly/plan` | VIP | ✅ canonical | `app/routers/vip.py` |
| `/api/v1/vip/shoplist/generate` | VIP | ✅ canonical | `app/routers/vip_shoplist.py` |
| `/api/v1/vip/recipes/synthesize` | VIP | ✅ canonical | `app/routers/vip.py` |
| `/api/v1/vip/auto-repair/*` | VIP | ✅ canonical | `app/routers/vip.py` |
| `/api/v1/vip/weekly-plan` | VIP | ⚠️ deprecated | `app/routers/vip.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_vip_router.py` — VIP endpoints
- `tests/test_vip_shoplist.py` — VIP списки покупок
- `tests/test_auto_repair.py` — авто-ремонт
- `tests/test_vip_coverage_working_extended.py` — coverage тесты

**Guard-тесты:**
- `tests/test_vip_tier_guard_matrix.py` — проверка VIP tier guards

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Сложность** — много взаимосвязанных компонентов
2. **Тестирование** — сложность тестирования интеграции
3. **Документация** — не хватает примеров использования VIP функций

### ✅ Рекомендации

1. ✅ **Завершено:** VIP tier guards и feature flags
2. 📋 **Документация:** Добавить примеры использования в API docs
3. 📋 **Тестирование:** Добавить E2E тесты для VIP workflows

---

## 7. User Management Domain

### 🎯 Назначение

Управление пользователями, регистрация, аутентификация, профили.

### 📁 Структура

```
app/routers/
├── users.py                # User endpoints
├── pro_registration.py     # PRO tier регистрация
└── vip_registration.py     # VIP tier регистрация

app/models/
└── events.py               # User events (nutrition logs)

core/
└── models.py               # SQLAlchemy models (User)
```

### 🔑 Ключевые компоненты

#### `app/routers/users.py`
- **`POST /api/v1/users`** — создание пользователя
- **`GET /api/v1/users`** — список пользователей
- **`GET /api/v1/users/{user_id}`** — получение пользователя

#### `app/models/events.py`
- **`NutritionEvent`** — события питания пользователя
- **`EventCollector`** — сбор событий

### 🛡️ Архитектурные принципы

1. **Simple CRUD** — базовые операции с пользователями
2. **Event-driven** — события питания для аналитики
3. **Tier-agnostic** — базовые операции доступны всем tier

### 🔗 Зависимости

**Зависит от:**
- `core.db` — база данных
- `app.models` — SQLAlchemy models

**Используется:**
- Все tier endpoints (для user_id)

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/users` | FREE | ✅ canonical | `app/routers/users.py` |
| `/api/v1/users/{user_id}` | FREE | ✅ canonical | `app/routers/users.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_users.py` — user endpoints
- `tests/test_nutrition_events.py` — события питания

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Простота** — базовая функциональность, может быть расширена
2. **Аутентификация** — нет полноценной системы аутентификации (только API keys)

### ✅ Рекомендации

1. 📋 **Расширение:** Добавить полноценную систему аутентификации (JWT, OAuth)
2. 📋 **Профили:** Расширить профили пользователей (preferences, history)

---

## 8. Analytics/Bayesian Domain

### 🎯 Назначение

Байесовский анализ приверженности планам питания, бизнес-аналитика, техническая аналитика.

### 📁 Структура

```
core/bayes/
├── __init__.py
├── adherence_model.py      # Байесовская модель приверженности
├── adherence_adapter.py    # Адаптер для domain events
└── adherence_service.py    # Сервис приверженности

core/analyzer/
├── store.py                # AnalyzerStore (Postgres + TTL cache)
├── store_sqlalchemy.py     # SQLAlchemy implementation
└── store_cache.py          # TTL cache implementation

core/
├── bayesian_recommendations.py
├── bayesian_test_analyzer.py
├── business_bayesian_analyzer.py
├── nutrition_bayesian_analyzer.py
└── comprehensive_bayesian_analyzer.py
```

### 🔑 Ключевые компоненты

#### `core/bayes/adherence_model.py`
- **`AdherenceState`** — состояние приверженности (alpha, beta, n)
- **`update_state()`** — обновление состояния на основе событий
- **`compute_metrics()`** — расчет метрик (risk_slip, confidence)

#### `core/bayes/adherence_service.py`
- **`AdherenceService`** — сервис приверженности
- **`get()`** — получение метрик приверженности
- **`update()`** — обновление состояния на основе событий

#### `core/analyzer/store.py`
- **`AnalyzerStore`** — хранилище состояний анализаторов
- **`get_state()`** — получение состояния
- **`save_state()`** — сохранение состояния (optimistic locking)

#### `core/business_bayesian_analyzer.py`
- **`BusinessBayesianAnalyzer`** — бизнес-аналитика
- Анализ монетизации, роста, эффективности

### 🛡️ Архитектурные принципы

1. **Bayesian approach** — байесовский подход к анализу
2. **Event-driven** — анализ на основе событий
3. **Optimistic locking** — предотвращение race conditions
4. **TTL caching** — кэширование для производительности

### 🔗 Зависимости

**Зависит от:**
- `core.db` — база данных
- `app.models.events` — события питания

**Используется:**
- `app/routers/bayes_adherence.py` — PRO tier endpoints
- `app/routers/business.py` — бизнес-аналитика

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/pro/bayes/adherence` | PRO | ✅ canonical | `app/routers/bayes_adherence.py` |
| `/api/v1/business/analyze` | PRO | ✅ canonical | `app/routers/business.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_bayes_adherence.py` — байесовская модель
- `tests/test_analyzer_store.py` — хранилище состояний
- `tests/test_business_analyzer.py` — бизнес-аналитика

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Сложность** — байесовские модели сложны для понимания
2. **Производительность** — расчеты могут быть медленными для больших объемов данных
3. **Документация** — не хватает объяснения математики

### ✅ Рекомендации

1. ✅ **Завершено:** Базовые байесовские модели
2. 📋 **Документация:** Добавить объяснение математики в docstrings
3. 📋 **Оптимизация:** Оптимизировать расчеты для больших объемов данных

---

## 9. Catalog Domain

### 🎯 Назначение

Управление региональными каталогами магазинов, продуктами, ценами, доступностью.

### 📁 Структура

```
core/catalog/
├── __init__.py
├── models.py               # Модели каталога (Product, Store, Region)
├── provider.py             # CatalogProvider interface
├── service.py              # CatalogService
├── types.py                # Типы каталога
├── loaders/                # Загрузчики каталогов
│   ├── base.py
│   ├── carrefour_es.py
│   └── walmart_us.py
├── sources/                # Источники данных
│   ├── base.py
│   ├── carrefour_stub.py
│   ├── off_stub.py
│   └── walmart_stub.py
├── normalize/              # Нормализация данных
│   ├── alias.py
│   └── common.py
└── storage/               # Хранилище
    ├── schema.sql
    └── sqlite_writer.py

app/services/
└── catalog_adapter.py      # Адаптер для интеграции с роутерами
```

### 🔑 Ключевые компоненты

#### `core/catalog/models.py`
- **`Product`** — продукт в каталоге
- **`Store`** — магазин
- **`Region`** — регион
- **`Price`** — цена продукта

#### `core/catalog/provider.py`
- **`CatalogProvider`** — интерфейс провайдера каталога
- **`get_products()`** — получение продуктов
- **`search_products()`** — поиск продуктов
- **`get_price_comparison()`** — сравнение цен

#### `core/catalog/service.py`
- **`CatalogService`** — сервис каталога
- **`get_available_regions()`** — получение доступных регионов
- **`get_region_catalog()`** — получение каталога региона

#### `app/services/catalog_adapter.py`
- **`CatalogProvider`** — адаптер для роутеров
- **`enrich_shoplist_response()`** — обогащение списков покупок ценами

### 🛡️ Архитектурные принципы

1. **Provider pattern** — абстракция над различными источниками
2. **Region-aware** — поддержка региональных каталогов
3. **Lazy loading** — загрузка данных по требованию
4. **Normalization** — нормализация данных из разных источников

### 🔗 Зависимости

**Зависит от:**
- `core.db` — база данных (SQLite для каталогов)
- `core.food_apis` — база продуктов (для маппинга)

**Используется:**
- `app/routers/vip_shoplist.py` — обогащение списков покупок
- `app/routers/catalog.py` — endpoints каталога

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/vip/regions` | VIP | ✅ canonical | `app/routers/vip.py` |
| `/api/v1/vip/regions/{region}/catalog` | VIP | ✅ canonical | `app/routers/vip.py` |
| `/api/v1/vip/price-comparison` | VIP | ✅ canonical | `app/routers/vip.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_catalog_provider.py` — провайдер каталога
- `tests/test_catalog_service.py` — сервис каталога
- `tests/test_catalog_coverage.py` — coverage тесты

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Источники данных** — в основном stub-источники, нужны реальные интеграции
2. **Производительность** — поиск по каталогу может быть медленным
3. **Синхронизация** — обновление каталогов требует улучшения

### ✅ Рекомендации

1. ✅ **Завершено:** Базовая архитектура каталогов
2. 📋 **Интеграции:** Добавить реальные интеграции с магазинами
3. 📋 **Оптимизация:** Индексация для быстрого поиска
4. 📋 **Синхронизация:** Автоматическое обновление каталогов

---

## 10. Recipe Domain

### 🎯 Назначение

Управление рецептами, синтез рецептов, база рецептов.

### 📁 Структура

```
core/
├── recipe_db.py            # База рецептов (legacy)
├── recipe_db_new.py        # Новая база рецептов
├── recipe_synth.py         # Синтез рецептов (VIP)
└── product_finder.py      # Поиск продуктов для рецептов

app/routers/
└── recipes.py              # Recipe endpoints
```

### 🔑 Ключевые компоненты

#### `core/recipe_synth.py`
- **`RecipeSynthesizer`** — синтезатор рецептов
- **`synthesize_recipe()`** — синтез рецепта на основе ингредиентов
- **VIP feature** — доступно только VIP tier

#### `app/routers/recipes.py`
- **`GET /api/v1/recipes`** — список рецептов
- **`GET /api/v1/recipes/{recipe_id}`** — получение рецепта
- **`POST /api/v1/recipes`** — создание рецепта

### 🛡️ Архитектурные принципы

1. **Recipe-first** — рецепты как основа планирования
2. **Synthesis** — синтез рецептов для VIP tier
3. **Integration** — интеграция с планами питания

### 🔗 Зависимости

**Зависит от:**
- `core.food_apis` — база продуктов
- `core.menu_engine` — генерация меню

**Используется:**
- `app/routers/vip.py` — синтез рецептов
- `core/menu_engine.py` — использование рецептов в меню

### 📊 API Endpoints

| Endpoint | Tier | Статус | Файл |
|----------|------|--------|------|
| `/api/v1/recipes` | FREE | ✅ canonical | `app/routers/recipes.py` |
| `/api/v1/recipes/{recipe_id}` | FREE | ✅ canonical | `app/routers/recipes.py` |
| `/api/v1/vip/recipes/synthesize` | VIP | ✅ canonical | `app/routers/vip.py` |

### 🧪 Тестирование

**Unit-тесты:**
- `tests/test_recipes.py` — recipe endpoints
- `tests/test_recipe_synth.py` — синтез рецептов

**Coverage:** ≥97%

### ⚠️ Проблемы

1. **Дублирование** — `recipe_db.py` vs `recipe_db_new.py` (legacy)
2. **Синтез** — синтез рецептов может быть улучшен
3. **Интеграция** — интеграция с планами питания требует улучшения

### ✅ Рекомендации

1. ✅ **Завершено:** Базовая функциональность рецептов
2. 📋 **Рефакторинг:** Удаление `recipe_db.py` после миграции
3. 📋 **Улучшение:** Улучшение синтеза рецептов (AI-based)
4. 📋 **Интеграция:** Улучшение интеграции с планами питания

---

## 📊 Сводная таблица субдоменов

| Субдомен | Tier | Endpoints | Тесты | Coverage | Статус |
|----------|------|-----------|-------|----------|--------|
| BMI Calculation | FREE/PRO | 3 | ✅ | ≥97% | ✅ Stable |
| Nutrition Planning | PRO | 4 | ✅ | ≥97% | ✅ Stable |
| Food Database | FREE | 2 | ✅ | ≥97% | ✅ Stable |
| Meal Planning | PRO/VIP | 3 | ✅ | ≥97% | ✅ Stable |
| Shopping List | PRO/VIP | 6 | ✅ | ≥97% | ✅ Stable |
| VIP Features | VIP | 5+ | ✅ | ≥97% | ✅ Stable |
| User Management | FREE | 2 | ✅ | ≥97% | ✅ Stable |
| Analytics/Bayesian | PRO | 2 | ✅ | ≥97% | 🔄 In Progress |
| Catalog | VIP | 3 | ✅ | ≥97% | 🔄 In Progress |
| Recipe | FREE/VIP | 3 | ✅ | ≥97% | ✅ Stable |

---

## 🎯 Общие рекомендации

### Архитектурные

1. **Консолидация legacy** — удаление дублирующихся модулей (`*_new.py` vs старые)
2. **Унификация endpoints** — миграция с `/premium/*` на `/pro/*` и `/vip/*`
3. **Документация** — улучшение docstrings и примеров использования

### Производительность

1. **Кэширование** — агрессивное кэширование часто используемых данных
2. **Индексация** — индексация баз данных для быстрого поиска
3. **Оптимизация** — оптимизация медленных запросов

### Тестирование

1. **Интеграционные тесты** — добавление E2E тестов для полных workflows
2. **Performance тесты** — тесты производительности для критических путей
3. **Contract тесты** — тесты контрактов между субдоменами

---

## 📚 Связанные документы

- `docs/contracts/PRODUCT_TIER_MAP.md` — карта продуктовых уровней
- `docs/architecture/` — архитектурная документация
- `AGENTS.md` — правила разработки
- `docs/ENGINEERING_LESSONS.md` — уроки инженерии

---

**Последнее обновление:** 2026-01-28
**Версия:** 1.0

# 🎯 Глобальный план модернизации PulsePlate 2025

> Update (2026-02-20): active strategic execution track is documented in
> `docs/roadmap/PROGRAM_6M_BALANCED_2026H1.md` and `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`.

## 📋 Обзор проекта

**Цель квартала:**

1. **Стабильный зелёный CI/CD** (lint → typecheck → test → build; артефакты покрытия)
2. **Вертикальные релизы**: WHO Targets → Weekly Plan → Shopping List → Auto-Repair (все через OpenAPI и фичефлаги)
3. **HIG-чистый UX**: a11y AA, 44pt, фокус-ловушки, i18n RU/EN/ES
4. **Готовность к монетизации**: CTA-потоки к paywall из ключевых экранов

## 🏗️ Принципов разработки

- **Thin slices**: каждый PR — полный вертикальный срез (API→UI→тесты→i18n→a11y), ≤600 строк
- **Source-of-truth**: типы и моки генерим из **OpenAPI**
- **Feature flags**: все VIP-модули за `VITE_VIP_MODULE_ENABLED`
- **Diff coverage ≥90%** (по изменённым файлам), не тотальная
- **Design = Trust**: минимализм, читаемость, предсказуемые жесты/переходы

## 🧪 Стратегия тестирования и моков

### Моки по модулям (не по классам)

- **Принцип**: Мокаем модули целиком, а не отдельные классы
- **Пример**: `vi.mock('../telemetry')` вместо `vi.mock('../telemetry', { SomeClass: ... })`
- **Преимущества**: Более стабильные тесты, меньше coupling с внутренней структурой

### Моки по функциям (не по классам)

- **Принцип**: Мокаем функции и хуки, а не классы
- **Пример**: `vi.mocked(useVipModule).mockReturnValue(true)` вместо мока класса
- **Преимущества**: Лучшая изоляция, проще поддержка

### Избегание моков классов

- **Проблема**: Моки классов создают tight coupling и хрупкие тесты
- **Решение**: Используем функциональный подход с моками модулей/функций
- **Пример**: Вместо `vi.mock('./SomeClass')` используем `vi.mock('./module')`

---

## 🚀 ФАЗА 1: Стабилизация платформы (Week 1) ✅ ЗАВЕРШЕНО

### ✅ PR #1: Fix Frontend CI Tests

- **Статус**: ЗАВЕРШЕНО ✅
- **Проблема**: `Invalid Chai property: toHaveNoViolations`
- **Решение**:
  - Удалены дублирующиеся setup файлы
  - Создан единый `test/setup.ts` с jest-axe матчерами
  - Добавлены TypeScript типы в `vitest.d.ts`
  - Добавлен fallback в Accessibility тестах
  - Обновлен GitHub Actions workflow

**Результат**: 176/177 тестов проходят ✅

### ✅ PR #2.1: Feature Flags Setup

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Базовая инфраструктура для VIP модулей через feature flags
- **Решение**:
  - Создан `src/config/features.ts` с типизированными флагами
  - Добавлены React хуки: `useFeatureFlag()`, `useVipModule()`, `useAnalytics()`
  - Созданы VIP компоненты: `VipFeature`, `VipBadge`, `VipGate`
  - Интеграция с TabBar для условного отображения VIP табов
  - **Ключевое решение**: Мок по модулям вместо мока `import.meta.env` (Vite-специфичный подход)
- **Тестирование**: 25 тестов покрывают всю функциональность

**Результат**: Полная инфраструктура feature flags готова ✅

---

## ✅ ФАЗА 2: OpenAPI Infrastructure (Week 2) - ЗАВЕРШЕНО

### ✅ PR #2.2: Design Tokens Foundation

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Единая система дизайн-токенов для консистентного UI
- **Решение**:
  - Создан `src/styles/tokens.css` с полной системой дизайн-токенов
  - Реализованы цвета: Navy (#0F172A), Blue (#339FFF), Accent Green (#20C997), Heart Red (#FF5D5D)
  - Добавлены размеры и spacing с touch-friendly targets (44×44pt)
  - Typography tokens для консистентной типографики
  - CSS custom properties с поддержкой темной темы
  - Comprehensive тесты для design tokens (21 тест)
  - **Ключевое решение**: Использование CSS custom properties вместо JS токенов для лучшей производительности

**Результат**: Полная система дизайн-токенов готова ✅

### ✅ PR #2.3: VIP Components Base

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Базовые VIP компоненты для условного отображения
- **Решение**:
  - Создан `VipGate` компонент с поддержкой `inert` атрибута и fallback
  - Реализован `VipBadge` компонент с размерами и вариантами
  - Добавлены `VipPageHeader`, `VipFeatureCard`, `VipSection` компоненты
  - Интеграция с `useInert` хуком для accessibility
  - Локализация всех VIP компонентов (RU/EN/ES)
  - Comprehensive тесты (25 тестов) покрывают все сценарии
  - **Ключевое решение**: Извлечение `inert` логики в переиспользуемый `useInert` хук

**Результат**: Полная база VIP компонентов готова ✅

### ✅ PR #2.4: Telemetry Foundation

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Комплексная система телеметрии для VIP событий
- **Решение**:
  - Создан `useTelemetry()` хук с полным набором VIP событий
  - Реализован `useVipModuleTracking()` для автоматического отслеживания
  - Добавлены session tracking и feature flag capture
  - 7 типов VIP событий: module_viewed, feature_clicked, paywall_viewed, paywall_dismissed, upgrade_clicked, gate_interacted, badge_viewed
  - Comprehensive тесты (56 тестов) покрывают все сценарии
  - **Ключевое решение**: Type-safe система событий с автоматическим обогащением sessionId и featureFlags

**Результат**: Полная система телеметрии готова ✅

### ✅ PR #2.5: VIP i18n Keys

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Добавить VIP-related переводы для новых компонентов
- **Решение**:
  - Добавлены VIP термины в cspell словарь (VIP, vip)
  - Создана centralized terminology mapping для VIP переводов
  - Добавлены comprehensive тесты для VIP translation quality (2 новых теста)
  - Исправлена TypeScript ошибка с типами локалей (as const assertion)
  - Применена object destructuring в тестах для лучшей читаемости
  - **Ключевое решение**: Централизованное сопоставление VIP терминологии вместо hard-coded строк

**Ожидаемый результат**: Полная локализация VIP компонентов с centralized terminology mapping

### ✅ PR #2.6: i18n Validation & Quality - ЗАВЕРШЕНО

- **Цель**: Улучшить валидацию и качество переводов
- **Критерии**: Валидация работает; качество переводов проверено

#### Задачи i18n Validation

- [ ] **Улучшить валидацию** в `locales.test.ts`
- [ ] **Добавить проверки качества** (длина, терминология)
- [ ] **Обновить cspell словарь** для новых терминов

### ✅ PR #2.7: iOS-Frontend Sync Preparation - ЗАВЕРШЕНО

- **Цель**: Синхронизация с iOS приложением
- **Критерии**: Консистентность текстов и навигации; iOS team review

#### Задачи iOS Sync

- [ ] **Синхронизировать тексты** с iOS локалями
- [ ] **Выровнять навигацию** и naming conventions
- [ ] **Добавить iOS-specific ключи** если нужно

---

## 📋 ФАЗА 3: WHO Targets E2E (Week 3) - В ПРОЦЕССЕ

### ✅ PR #3.1: WHO Targets Component Foundation

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Базовый компонент WHO Targets панели с состояниями
- **Решение**:
  - Создан `WhoTargetsPanel` компонент с loading/error/empty states
  - Добавлены comprehensive CSS стили с responsive design
  - Поддержка всех WHO targets данных: calories, macros, hydration, activity
  - Реализовано proper state management и error handling
  - Добавлены accessibility features и focus management
  - Включено отображение warnings для special conditions
  - **Ключевое решение**: Модульная архитектура готова для i18n интеграции

**Результат**: Базовый компонент WHO Targets готов ✅

### ✅ PR #3.2: WHO Targets i18n & Localization

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Полная локализация WHO Targets компонента
- **Критерии**: Все тексты локализованы (RU/EN/ES); тесты локализации проходят

#### Задачи WHO Targets i18n

- [x] **Add i18n keys** для WHO Targets (RU/EN/ES)
- [x] **Localize all texts** и сообщения
- [x] **Add localization tests** для consistency
- [x] **Validate text lengths** для UI layout

**Результат**: Полная локализация WHO Targets готова ✅

### ✅ PR #3.3: WHO Targets Accessibility & UX

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Полная accessibility compliance и UX оптимизация
- **Критерии**: a11y-тест проходит; keyboard navigation работает; screen reader support

#### Задачи WHO Targets a11y

- [x] **Add accessibility tests** (a11y AA compliance) - 25/25 тестов проходят
- [x] **Implement keyboard navigation** для всех элементов - userEvent integration
- [x] **Add screen reader support** с proper ARIA labels - aria-busy, aria-live, sr-only
- [x] **Optimize focus management** и tab order - proper focus indicators
- [x] **Fix remaining CodeRabbit feedback** from previous PRs - nitpicks resolved
- [x] **Add comprehensive component tests** for WHO Targets - full coverage
- [x] **Improve code quality** and performance - userEvent, better test structure
- [x] **Achieve 97% test coverage** for changed files - accessibility tests added

**Результат**: Полная accessibility compliance достигнута ✅

### ✅ PR #3.4: WHO Targets Integration & Testing

- **Статус**: ЗАВЕРШЕНО ✅
- **Цель**: Полная интеграция и comprehensive тестирование
- **Критерии**: сценарии 200/401/422 покрыты; CTA интеграция работает

#### Задачи WHO Targets Integration

- [x] **WHO Targets API client** integration - модульная система API готова
- [x] **Weekly Plan API client** integration - создан и протестирован
- [x] **Comprehensive testing** (200/401/422 scenarios) - 23 теста проходят
- [x] **Add CTA** "Save & Get Weekly Plan" интеграция - IntegratedWhoTargetsPanel готов
- [x] **API integration tests** - 34 теста проходят (23 API + 11 компонент)
- [ ] **E2E тесты** - планируется

**Результат**: Полная интеграция WHO Targets с Weekly Plan API готова ✅

---

## 📋 ФАЗА 4: Weekly Plan Reader (Week 4) - ПЛАНИРУЕТСЯ

### 📋 PR-B: Weekly Plan (reader)

- **Цель**: Генерация плана → просмотр по дням (свайпы/кнопки) → скелетоны
- **Критерии**: загрузка/ошибка/пусто покрыты; VoiceOver читает корректно; FCP < 1.5s

#### Задачи Weekly Plan Reader

- [ ] **Weekly Plan API client** integration
- [ ] **Create Weekly Plan viewer** с day navigation (swipes/buttons)
- [ ] **Add loading skeletons** для plan generation
- [ ] **Add VoiceOver compatibility** и keyboard navigation
- [ ] **Optimize for FCP < 1.5s** на plan screen

---

## 📋 ФАЗА 5: Shopping List (Week 5) - ПЛАНИРУЕТСЯ

### 📋 PR-C: Shopping List (read-only, за флагом)

- **Цель**: Генерация из плана; группировка по отделам; чекбоксы; offline (localStorage)
- **Критерии**: offline работает; диф-покрытие ≥90%; CTA к paywall предусмотрен

#### Задачи Shopping List

- [ ] **Shopping List API client** (behind VIP flag)
- [ ] **Generate shopping list** из weekly plan
- [ ] **Group items** по store departments
- [ ] **Add offline support** с localStorage
- [ ] **Show Shopping List tab** только при VIP_MODULE_ENABLED=true
- [ ] **Add CTA to paywall** из shopping list

---

## 📋 ФАЗА 6: Auto-Repair (Week 6) - ПЛАНИРУЕТСЯ

### 📋 PR-D: Auto-Repair (за флагом)

- **Цель**: Анализ дефицитов → кнопка Auto-repair → дифф до/после → откат
- **Критерии**: включается/выключается флагом без ребилда; UX прост; тесты стабильны

#### Задачи Auto-Repair

- [ ] **Auto-Repair API client** (behind VIP flag)
- [ ] **Analyze nutrient deficiencies** из current plan
- [ ] **Add simple 'Auto-repair' button**
- [ ] **Show before/after diff** plan changes
- [ ] **Add rollback functionality**
- [ ] **Ensure feature works** только при VIP_MODULE_ENABLED=true

---

## 🔄 ПАРАЛЛЕЛЬНЫЕ ДОРОЖКИ

> **Непрерывная работа параллельно с основными фазами**

### 🎨 Design System & a11y

> **Владелец**: Frontend Team | **Каденция**: Еженедельно

- [ ] **Build UI components**: Button, Card, TabBar, Skeleton, ErrorState, EmptyState, SwipeContainer
- [ ] **Set up Storybook** с @storybook/test для interactive component tests
- [ ] **Ensure WCAG 2.1 Level AA** compliance (contrast ≥ 4.5:1, focus traps)
- [ ] **Design tokens**: See PR #2.2 Design Tokens Foundation (Phase 2 deliverable)

### 📱 iOS Synchronization

> **Владелец**: iOS Team | **Каденция**: По мере необходимости

#### ✅ Frontend Ready (PR #2.7 Completed)

- [x] **iOS-compatible localization keys** added to all locales (EN/RU/ES)
- [x] **Chart, week, health, units sections** prepared for iOS sync
- [x] **Language, profile, mascot, settings keys** aligned with iOS format
- [x] **Accessibility labels** ready for iOS integration

#### 📋 Detailed iOS Development Plan

> **See**: [IOS_DEVELOPMENT_ROADMAP.md](./IOS_DEVELOPMENT_ROADMAP.md) for complete iOS development phases and tasks

**Quick Status**: Frontend ready for iOS synchronization. iOS team can resume development using prepared localization structure.

### 📊 Telemetry & Product Metrics

> **Владелец**: Product Team | **Каденция**: Еженедельно

- [ ] **Track events**: open_targets, generate_plan, open_shoplist, click_autorepair, paywall_view
- [ ] **Create dashboard**: conversion от Targets → Shoplist → Paywall
- [ ] **Telemetry foundation**: See PR #2.4 Telemetry Foundation (Phase 2 deliverable)

---

## 🔧 БЭКЕНД: Покрытие тестами до 97%

### Текущее состояние

- **Начальное**: 51% покрытие app.py
- **Текущее**: 55% покрытие app.py (373/676 строк)
- **Цель**: 97% покрытие (656/676 строк)
- **Осталось**: 283 строки до цели

### Задачи Backend Coverage

- [ ] **Fix validation issues** в тестах (добавить pregnant/athlete поля)
- [ ] **Cover large blocks**: HTML UI (395-609), Premium endpoints (1077-1150)
- [ ] **Final push to 97%** coverage (283 lines remaining)

---

## 🚀 БЭКЕНД: DLT Integration

### Цель: Масштабирование nutrition data

- **От**: 105 записей (статические CSV)
- **К**: миллионы записей (USDA FDC API + OpenFoodFacts API)

### Задачи DLT Integration

- [ ] **Setup DLT**: pip install dlt[postgres,parquet]
- [ ] **Get USDA API credentials** и configure
- [ ] **Create pipeline structure** и test на sample data
- [ ] **Integrate с admin endpoints** для monitoring

---

## 🎯 Качество и гейты

### Code Quality

- [ ] **ESLint/Prettier** configuration и rules
- [ ] **TypeScript strict mode** и type safety
- [ ] **Diff coverage ≥90%** на changed files (не total 95%)
- [ ] **Performance**: lazy-loading, code-splitting, React Query cache
- [ ] **Security**: API key via header, no secrets в repo, 401 handling

### Change Management

- [ ] **Branch strategy**: feature/* с rebase на main before PR
- [ ] **PR size limit**: ≤600 lines, one feature/flag
- [ ] **SLA review**: до 24 hours, PR template с checklist
- [ ] **Feature flags**: все VIP features disableable on-the-fly, default OFF

---

## 📊 KPI (Success Metrics)

### CI

- [ ] **0 red runs** неделю подряд; build < 5 мин

### Code

- [ ] **0 ESLint/TS errors**; diff-coverage ≥90% в новых PR

### UX

- [ ] **Lighthouse ≥ 90**; FCP < 1.5s; TTI < 3s

### Product

- [ ] **≥60% пользователей** доходят от Targets до Weekly Plan
- [ ] **≥20% открывают Shoplist** при включённом флаге

### 💰 Monetization

- [ ] **Paywall visibility**: ≥80% пользователей видят CTA при переходе Shopping List/Auto-Repair
- [ ] **CTA engagement**: ≥15% click-through rate на "Upgrade to VIP" промпты
- [ ] **Conversion rate**: ≥5% пользователей завершают purchase flow после просмотра paywall
- [ ] **Revenue readiness**: 100% payment integration touchpoints протестированы и задокументированы

---

## 🚨 Риски → Митигация

- **Скоп ползёт** → Лимит на дифф + «один вертикальный сценарий»
- **Контракты плывут** → OpenAPI-генерация + контрактные тесты
- **Регрессии a11y** → Единый setup + тесты на loading/success/error
- **Задержки ревью** → Малые PR + GIF + чек-лист

---

## 🎉 Текущий статус

- ✅ **ФАЗА 1 ЗАВЕРШЕНА**: CI стабилизирован, все тесты проходят
- ✅ **ФАЗА 2 ЗАВЕРШЕНА**: OpenAPI Infrastructure & iOS Preparation
  - ✅ **PR #2.1 ЗАВЕРШЕН**: Feature Flags Setup (25 тестов, мок по модулям)
  - ✅ **PR #2.2 ЗАВЕРШЕН**: Design Tokens Foundation (21 тест, CSS custom properties)
  - ✅ **PR #2.3 ЗАВЕРШЕН**: VIP Components Base (25 тестов, useInert хук)
  - ✅ **PR #2.4 ЗАВЕРШЕН**: Telemetry Foundation (56 тестов, type-safe события)
  - ✅ **PR #2.5 ЗАВЕРШЕН**: VIP i18n Keys (35 тестов, centralized terminology mapping)
  - ✅ **PR #2.6 ЗАВЕРШЕН**: i18n Validation & Quality (35 тестов, language-specific patterns)
  - ✅ **PR #2.7 ЗАВЕРШЕН**: iOS-Frontend Sync Preparation (iOS-compatible keys)
- 📋 **ФАЗЫ 3-6 ПЛАНИРУЮТСЯ**: Вертикальные срезы по неделям

**Текущий этап**: Готов к ФАЗЕ 3 (WHO Targets E2E) 🚀

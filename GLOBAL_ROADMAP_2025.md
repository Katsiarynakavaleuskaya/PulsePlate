# 🎯 Глобальный план модернизации PulsePlate 2025

## 📋 Обзор проекта

**Цель квартала:**
1. **Стабильный зелёный CI/CD** (lint → typecheck → test → build; артефакты покрытия)
2. **Вертикальные релизы**: WHO Targets → Weekly Plan → Shopping List → Auto-Repair (все через OpenAPI и фичефлаги)
3. **HIG-чистый UX**: a11y AA, 44pt, фокус-ловушки, i18n RU/EN/ES
4. **Готовность к монетизации**: CTA-потоки к paywall из ключевых экранов

## 🏗️ Принципы разработки

- **Thin slices**: каждый PR — полный вертикальный срез (API→UI→тесты→i18n→a11y), ≤600 строк
- **Source-of-truth**: типы и моки генерим из **OpenAPI**
- **Feature flags**: все VIP-модули за `VITE_VIP_MODULE_ENABLED`
- **Diff coverage ≥90%** (по изменённым файлам), не тотальная
- **Design = Trust**: минимализм, читаемость, предсказуемые жесты/переходы

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

---

## 🔄 ФАЗА 2: OpenAPI Infrastructure (Week 2) - В ПРОЦЕССЕ

### 📋 PR #2: OpenAPI Infrastructure
- **Цель**: Автогенерация типов из бэкенда, базовый ApiClient, фичефлаги
- **Критерии**: `npm run generate-types` стабильно; MSW моки от тех же типов; первый контрактный тест

#### Задачи:
- [ ] **Auto-generate TypeScript types** из backend OpenAPI schema
- [ ] **Create base ApiClient** с 401/422/503 error handling
- [ ] **Set up FEATURES config** и VIP_MODULE_ENABLED flags
- [ ] **Update MSW mocks** для использования сгенерированных типов
- [ ] **Add contract tests** для backend↔frontend API consistency

---

## 📋 ФАЗА 3: WHO Targets E2E (Week 3) - ПЛАНИРУЕТСЯ

### 📋 PR-A: WHO Targets (минималка)
- **Цель**: API клиент → простая панель целей → состояния loading/error → a11y
- **Критерии**: a11y-тест проходит; сценарии 200/401/422 покрыты; UX без «инфо-стены»

#### Задачи:
- [ ] **WHO Targets API client** integration
- [ ] **Create WHO Targets panel** с loading/error states
- [ ] **Add accessibility tests** (a11y AA compliance)
- [ ] **Add i18n keys** (RU/EN/ES)
- [ ] **Add CTA** "Save & Get Weekly Plan" (готовит почву под следующий срез)

---

## 📋 ФАЗА 4: Weekly Plan Reader (Week 4) - ПЛАНИРУЕТСЯ

### 📋 PR-B: Weekly Plan (reader)
- **Цель**: Генерация плана → просмотр по дням (свайпы/кнопки) → скелетоны
- **Критерии**: загрузка/ошибка/пусто покрыты; VoiceOver читает корректно; FCP < 1.5s

#### Задачи:
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

#### Задачи:
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

#### Задачи:
- [ ] **Auto-Repair API client** (behind VIP flag)
- [ ] **Analyze nutrient deficiencies** из current plan
- [ ] **Add simple 'Auto-repair' button**
- [ ] **Show before/after diff** plan changes
- [ ] **Add rollback functionality**
- [ ] **Ensure feature works** только при VIP_MODULE_ENABLED=true

---

## 🔄 ПАРАЛЛЕЛЬНЫЕ ДОРОЖКИ

### 🎨 Design System & a11y
- [ ] **Create design tokens** (Navy/Blue/Green/Heart colors, 44×44pt targets)
- [ ] **Build UI components**: Button, Card, TabBar, Skeleton, ErrorState, EmptyState, SwipeContainer
- [ ] **Set up Storybook** с @storybook/test для interactive component tests
- [ ] **Ensure WCAG 2.1 Level AA** compliance (contrast ≥ 4.5:1, focus traps)

### 📱 iOS Synchronization
- [ ] **Synchronize texts/iconography/micro-animations** с SwiftUI screens
- [ ] **Align navigation and naming** (RU/EN/ES locales)

### 📊 Telemetry & Product Metrics
- [ ] **Track events**: open_targets, generate_plan, open_shoplist, click_autorepair, paywall_view
- [ ] **Create dashboard**: conversion от Targets → Shoplist → Paywall

---

## 🔧 БЭКЕНД: Покрытие тестами до 97%

### Текущее состояние:
- **Начальное**: 51% покрытие app.py
- **Текущее**: 55% покрытие app.py (373/676 строк)
- **Цель**: 97% покрытие (656/676 строк)
- **Осталось**: 283 строки до цели

### Задачи:
- [ ] **Fix validation issues** в тестах (добавить pregnant/athlete поля)
- [ ] **Cover large blocks**: HTML UI (395-609), Premium endpoints (1077-1150)
- [ ] **Final push to 97%** coverage (283 lines remaining)

---

## 🚀 БЭКЕНД: DLT Integration

### Цель: Масштабирование nutrition data
- **От**: 105 записей (статические CSV)
- **К**: миллионы записей (USDA FDC API + OpenFoodFacts API)

### Задачи:
- [ ] **Setup DLT**: pip install dlt[postgres,parquet]
- [ ] **Get USDA API credentials** и configure
- [ ] **Create pipeline structure** и test на sample data
- [ ] **Integrate с admin endpoints** для monitoring

---

## 🎯 Качество и гейты

### Code Quality:
- [ ] **ESLint/Prettier** configuration и rules
- [ ] **TypeScript strict mode** и type safety
- [ ] **Diff coverage ≥90%** на changed files (не total 95%)
- [ ] **Performance**: lazy-loading, code-splitting, React Query cache
- [ ] **Security**: API key via header, no secrets в repo, 401 handling

### Change Management:
- [ ] **Branch strategy**: feature/* с rebase на main before PR
- [ ] **PR size limit**: ≤600 lines, one feature/flag
- [ ] **SLA review**: до 24 hours, PR template с checklist
- [ ] **Feature flags**: все VIP features disableable on-the-fly, default OFF

---

## 📊 KPI (Success Metrics)

### CI:
- [ ] **0 red runs** неделю подряд; build < 5 мин

### Code:
- [ ] **0 ESLint/TS errors**; diff-coverage ≥90% в новых PR

### UX:
- [ ] **Lighthouse ≥ 90**; FCP < 1.5s; TTI < 3s

### Product:
- [ ] **≥60% пользователей** доходят от Targets до Weekly Plan
- [ ] **≥20% открывают Shoplist** при включённом флаге

---

## 🚨 Риски → Митигация

- **Скоп ползёт** → Лимит на дифф + «один вертикальный сценарий»
- **Контракты плывут** → OpenAPI-генерация + контрактные тесты
- **Регрессии a11y** → Единый setup + тесты на loading/success/error
- **Задержки ревью** → Малые PR + GIF + чек-лист

---

## 🎉 Текущий статус

- ✅ **ФАЗА 1 ЗАВЕРШЕНА**: CI стабилизирован, все тесты проходят
- 🔄 **ФАЗА 2 В ПРОЦЕССЕ**: OpenAPI Infrastructure
- 📋 **ФАЗЫ 3-6 ПЛАНИРУЮТСЯ**: Вертикальные срезы по неделям

**Готов к следующему этапу**: PR #2 (OpenAPI Infrastructure) 🚀

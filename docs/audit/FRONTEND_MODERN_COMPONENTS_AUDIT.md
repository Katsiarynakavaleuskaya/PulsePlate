# Frontend Modern Components Audit & Recommendations

**Date:** 2026-01-15
**Status:** Current state analysis + recommendations
**Scope:** Frontend architecture, component library, design system

---

## 📊 Current State Analysis

### ✅ What We Have (Good Foundation)

#### Core Stack
- **React 18.3.1** — современная версия
- **TypeScript 5.4.5** — строгая типизация
- **Vite 6.3.4** — быстрый build tool
- **Tailwind CSS 3.4.4** — utility-first CSS
- **React Router 7.12.0** — routing

#### Form & Validation
- **React Hook Form 7.53.0** — управление формами
- **Zod 3.23.8** — schema validation
- **@hookform/resolvers 3.9.0** — интеграция RHF + Zod

#### UI Libraries (Partial)
- **@headlessui/react 2.1.2** — только Dialog (MobileMenu)
- **lucide-react 0.544.0** — иконки
- **react-hot-toast 2.4.1** — уведомления
- **recharts 3.2.1** — графики

#### Testing
- **Vitest 3.2.4** — unit testing
- **@testing-library/react 16.0.0** — компонентные тесты
- **MSW 2.11.3** — API mocking

#### Design System (Partial)
- **Design tokens** (`tokens.ts`, `tokens.css`) — цвета, spacing, typography
- **Custom components**: GlassCard, FormField, Toast, Skeleton, Toggle
- **No Storybook** — нет изолированной разработки компонентов

---

## 🔴 Critical Gaps (P0 — Blocking Modern Development)

### 1. Form Components (Missing)

**Problem:** Используются нативные `<input>`, `<select>` без единого стиля и поведения.

**Missing Components:**
- ❌ **Input** — нет унифицированного компонента (сейчас inline className)
- ❌ **NumberInput** — нет валидации чисел, локализация (RU comma → dot)
- ❌ **Select** — нет кастомного dropdown (сейчас нативный `<select>`)
- ❌ **RadioGroup** — нет компонента для radio buttons
- ❌ **Checkbox** — нет унифицированного checkbox
- ❌ **Textarea** — нет компонента для многострочного ввода
- ❌ **DatePicker** — нет выбора даты
- ❌ **Slider** — нет слайдера для числовых значений

**Impact:**
- BMI форма ломается на `75,1` (comma вместо dot)
- Нет единообразия стилей
- Сложно поддерживать accessibility

---

### 2. Layout & Navigation (Missing)

**Missing Components:**
- ❌ **Button** — нет унифицированного компонента (сейчас inline стили)
- ❌ **Card** — есть GlassCard, но нет базового Card
- ❌ **Dialog/Modal** — Headless UI есть, но нет обёртки
- ❌ **Dropdown Menu** — нет выпадающих меню
- ❌ **Tabs** — нет табов (есть TabBar, но это навигация)
- ❌ **Accordion** — нет раскрывающихся секций
- ❌ **Breadcrumbs** — нет хлебных крошек

**Impact:**
- Нет единообразия в кнопках
- Сложно создавать модальные окна
- Нет стандартных паттернов навигации

---

### 3. Feedback & Status (Partial)

**Have:**
- ✅ Toast (react-hot-toast)
- ✅ Skeleton (loading states)
- ✅ EmptyState
- ✅ ErrorBoundary

**Missing:**
- ❌ **Alert** — нет компонента для предупреждений/ошибок
- ❌ **Badge** — нет бейджей (есть VipBadge, но не универсальный)
- ❌ **Progress** — нет progress bar
- ❌ **Spinner** — нет спиннера (есть Skeleton, но не для inline)
- ❌ **Tooltip** — нет подсказок
- ❌ **Popover** — нет всплывающих окон

---

### 4. Data Display (Missing)

**Missing Components:**
- ❌ **Table** — нет таблиц данных
- ❌ **Pagination** — нет пагинации
- ❌ **DataTable** — нет таблиц с сортировкой/фильтрацией
- ❌ **List** — нет унифицированных списков
- ❌ **Avatar** — нет аватаров пользователей

---

### 5. Development Tools (Missing)

**Missing:**
- ❌ **Storybook** — нет изолированной разработки компонентов
- ❌ **Component documentation** — нет автогенерации docs
- ❌ **Design system docs** — нет централизованной документации

**Impact:**
- Сложно разрабатывать компоненты изолированно
- Нет визуального каталога компонентов
- Сложно онбордить новых разработчиков

---

## 🎯 Recommended Solution: shadcn/ui + Headless UI Hybrid

### Why shadcn/ui?

1. **Copy-paste components** — не зависимость, а код в репозитории
2. **Tailwind CSS** — уже используется
3. **Radix UI primitives** — accessibility из коробки
4. **TypeScript** — полная типизация
5. **Customizable** — легко адаптировать под дизайн-систему

### Why Hybrid?

- **Headless UI** уже есть (Dialog) — оставляем для простых случаев
- **shadcn/ui** для сложных компонентов (Select, DatePicker, Table)
- **Custom components** для специфичных (GlassCard, VipBadge)

---

## 📦 Recommended Components to Add (Priority Order)

### Phase 1: P0 — Form Components (Fix BMI Form)

**Priority:** Highest (блокирует BMI форму)

1. **Input** (`components/ui/input.tsx`)
   - Number parsing (RU comma → dot)
   - Validation states
   - Accessibility (ARIA)

2. **NumberInput** (`components/ui/number-input.tsx`)
   - Локализация чисел
   - Min/max validation
   - Step controls

3. **Select** (`components/ui/select.tsx`)
   - Кастомный dropdown (не нативный)
   - Search/filter
   - Accessibility

4. **Button** (`components/ui/button.tsx`)
   - Variants (primary, secondary, ghost)
   - Sizes (sm, md, lg)
   - Loading states
   - Icon support

**Estimated time:** 2-3 days

---

### Phase 2: P1 — Layout & Navigation

**Priority:** High (улучшает UX)

5. **Card** (`components/ui/card.tsx`)
   - Base card component
   - Header, body, footer slots

6. **Dialog** (`components/ui/dialog.tsx`)
   - Обёртка над Headless UI Dialog
   - Стандартизация API

7. **Dropdown Menu** (`components/ui/dropdown-menu.tsx`)
   - Выпадающие меню
   - Keyboard navigation

8. **Tabs** (`components/ui/tabs.tsx`)
   - Табы для контента
   - Keyboard navigation

**Estimated time:** 3-4 days

---

### Phase 3: P2 — Feedback & Status

**Priority:** Medium (улучшает UX)

9. **Alert** (`components/ui/alert.tsx`)
   - Success, warning, error, info
   - Dismissible

10. **Badge** (`components/ui/badge.tsx`)
    - Универсальные бейджи
    - Variants

11. **Progress** (`components/ui/progress.tsx`)
    - Progress bar
    - Indeterminate state

12. **Tooltip** (`components/ui/tooltip.tsx`)
    - Подсказки
    - Accessibility

**Estimated time:** 2-3 days

---

### Phase 4: P3 — Data Display

**Priority:** Low (для будущих фич)

13. **Table** (`components/ui/table.tsx`)
14. **Pagination** (`components/ui/pagination.tsx`)
15. **DataTable** (`components/ui/data-table.tsx`)

**Estimated time:** 4-5 days

---

### Phase 5: Development Tools

**Priority:** Medium (ускоряет разработку)

16. **Storybook Setup**
    - Изолированная разработка
    - Визуальный каталог
    - Документация компонентов

**Estimated time:** 1-2 days setup + ongoing

---

## 🛠 Implementation Plan

### Step 1: Install shadcn/ui CLI

```bash
cd frontend
npx shadcn@latest init
```

**Configuration:**
- Style: New York (или Default)
- Base color: Navy (соответствует дизайн-системе)
- CSS variables: Yes (уже есть в `tokens.css`)

### Step 2: Add Core Components (Phase 1)

```bash
npx shadcn@latest add input
npx shadcn@latest add button
npx shadcn@latest add select
npx shadcn@latest add label
```

### Step 3: Customize for Design System

**File:** `components/ui/input.tsx`

**Customizations:**
- Использовать design tokens из `tokens.css`
- Добавить number parsing (RU locale)
- Интеграция с React Hook Form

**Example:**
```typescript
// Custom number input with RU locale support
export function NumberInput({ value, onChange, ...props }) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    // Normalize: "75,1" → "75.1"
    const normalized = raw.replace(',', '.');
    const num = parseFloat(normalized);
    onChange(isNaN(num) ? '' : num);
  };
  // ...
}
```

### Step 4: Migrate Existing Forms

**Priority files:**
1. `pages/NutritionSetup/SetupForm.tsx` — BMI/nutrition form
2. `pages/Onboarding/EnterKey.tsx` — API key input
3. `features/plan/WeeklyPlanViewer.tsx` — если есть формы

### Step 5: Setup Storybook (Optional, but Recommended)

```bash
cd frontend
npx storybook@latest init
```

**Stories to create:**
- `Input.stories.tsx`
- `Button.stories.tsx`
- `Select.stories.tsx`
- `FormField.stories.tsx`

---

## 📋 Component Migration Checklist

### Form Components

- [ ] **Input** — заменить все `<input>` на `<Input>`
- [ ] **NumberInput** — для weight, height, age
- [ ] **Select** — заменить `<select>` на `<Select>`
- [ ] **Button** — заменить все `<button>` на `<Button>`
- [ ] **Label** — использовать `<Label>` вместо `<label>`

### Layout Components

- [ ] **Card** — базовый компонент (если нужен)
- [ ] **Dialog** — стандартизировать модальные окна

### Feedback Components

- [ ] **Alert** — для ошибок/предупреждений
- [ ] **Badge** — универсальные бейджи
- [ ] **Tooltip** — подсказки

---

## 🎨 Design System Integration

### Current Design Tokens

**File:** `frontend/src/styles/tokens.css`

**Available:**
- Colors: navy, blue, green, heart (red), gray
- Spacing: 0-24 (4px base unit)
- Touch targets: 44px, 56px

**Integration with shadcn/ui:**
- shadcn/ui использует CSS variables
- Можно маппить существующие tokens на shadcn variables
- Или использовать shadcn tokens как основу

**Recommended approach:**
```css
/* Map existing tokens to shadcn variables */
:root {
  --primary: var(--color-blue-600);
  --primary-foreground: #fff;
  --background: var(--color-bg);
  --foreground: var(--color-text);
  /* ... */
}
```

---

## 📊 Component Library Comparison

| Feature | shadcn/ui | Headless UI | MUI | Ant Design |
|---------|-----------|-------------|-----|------------|
| **Copy-paste** | ✅ | ❌ | ❌ | ❌ |
| **Tailwind** | ✅ | ✅ | ❌ | ❌ |
| **Accessibility** | ✅ (Radix) | ✅ | ✅ | ✅ |
| **Bundle size** | Small | Small | Large | Large |
| **Customization** | High | High | Medium | Medium |
| **TypeScript** | ✅ | ✅ | ✅ | ✅ |
| **Storybook** | Community | Community | Built-in | Community |

**Winner:** shadcn/ui (best fit for current stack)

---

## 🚀 Quick Start (Minimal Viable)

### For BMI Form Fix (P0)

**Minimum required:**
1. `Input` component with number parsing
2. `Button` component
3. `Label` component

**Time:** 1 day

**Files to update:**
- `pages/NutritionSetup/SetupForm.tsx`
- `components/ui/input.tsx` (new)
- `components/ui/button.tsx` (new)

---

## 📝 Recommended Package Additions

### Required (for shadcn/ui)

```json
{
  "dependencies": {
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-select": "^2.1.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "@radix-ui/react-tooltip": "^1.1.0",
    "@radix-ui/react-popover": "^1.1.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",  // ✅ Already installed
    "tailwind-merge": "^2.4.0"  // ✅ Already installed
  }
}
```

### Optional (for advanced features)

```json
{
  "dependencies": {
    "@radix-ui/react-accordion": "^1.2.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-progress": "^1.1.0",
    "@radix-ui/react-alert-dialog": "^1.1.0",
    "@tanstack/react-table": "^8.20.0"  // For DataTable
  }
}
```

---

## 🎯 Success Criteria

### Phase 1 (P0) — Form Components
- [ ] BMI form работает с RU locale (comma → dot)
- [ ] Все формы используют унифицированные компоненты
- [ ] Accessibility проверен (ARIA, keyboard navigation)
- [ ] TypeScript типы полные

### Phase 2 (P1) — Layout
- [ ] Все кнопки используют `<Button>`
- [ ] Модальные окна стандартизированы
- [ ] Навигация единообразна

### Phase 3 (P2) — Feedback
- [ ] Ошибки отображаются через `<Alert>`
- [ ] Подсказки через `<Tooltip>`
- [ ] Loading states через `<Spinner>` или `<Skeleton>`

---

## 🔗 Resources

- **shadcn/ui:** https://ui.shadcn.com/
- **Radix UI:** https://www.radix-ui.com/
- **Headless UI:** https://headlessui.com/
- **Tailwind CSS:** https://tailwindcss.com/
- **React Hook Form:** https://react-hook-form.com/

---

## 📌 Next Steps

1. **Immediate (P0):** Add Input + NumberInput + Button (fix BMI form)
2. **Short-term (P1):** Add Select, Dialog, Dropdown Menu
3. **Medium-term (P2):** Add Alert, Badge, Tooltip
4. **Long-term (P3):** Setup Storybook, add Table/Pagination

---

**Last updated:** 2026-01-15
**Status:** Ready for implementation

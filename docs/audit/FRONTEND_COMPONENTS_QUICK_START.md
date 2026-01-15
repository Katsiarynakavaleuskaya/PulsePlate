# Frontend Modern Components — Quick Start Guide

**Date:** 2026-01-15
**Purpose:** Быстрый старт для добавления современных компонентов
**Target:** Fix BMI form + улучшить UX

---

## 🎯 Immediate Action (P0 — Fix BMI Form)

### Problem
BMI форма ломается на:
- `75,1` (comma) → должно быть `75.1` (dot)
- Нет единообразия в input/button стилях
- Нет валидации чисел

### Solution: Add 3 Core Components

**1. Install shadcn/ui CLI**

```bash
cd frontend
npx shadcn@latest init
```

**Questions:**
- **Style:** `New York` (или `Default`)
- **Base color:** `blue` ⚠️ **NOT "Navy"** — shadcn doesn't support custom color names
- **CSS variables:** `Yes` (уже есть в `tokens.css`)

**Note:** We'll map "Navy" via CSS variables in `tokens.css` (see `PR_526_SHADCN_COMPONENTS_PATCH.md` Step 3).

**2. Add Core Components**

```bash
npx shadcn@latest add input
npx shadcn@latest add button
npx shadcn@latest add label
```

**3. ⚠️ IMPORTANT: NumberInput Requires Controller Pattern**

**Problem:** `register()` expects DOM `onChange(event)`, but custom `NumberInput` uses `onValueChange(value)`. Direct `{...register()}` will break.

**Solution:** Use RHF `Controller` pattern (see PR-526 for full implementation).

**For P0 (Quick Fix):** Use `setValueAs` instead (see `PR_525_BMI_FIX_PATCH.md`).

**For P1 (Proper Components):** Use `Controller` + `NumberInput` (see `PR_526_SHADCN_COMPONENTS_PATCH.md`).

**Quick Example (P1 approach):**
```typescript
import { Controller } from "react-hook-form";
import { NumberInput } from "@/components/ui/number-input";

<Controller
  name="weight_kg"
  control={control}
  render={({ field }) => (
    <NumberInput
      value={field.value ?? ""}
      onValueChange={field.onChange}   // (number | "") => void
      onBlur={field.onBlur}
      locale={lang === "ru" ? "ru" : "en"}
      placeholder="65"
    />
  )}
/>
```

**Full NumberInput implementation:** See `PR_526_SHADCN_COMPONENTS_PATCH.md` (Step 4).

---

## 📦 Recommended Components (Priority Order)

### Phase 1: P0 — Form Components (1-2 days)

```bash
npx shadcn@latest add input
npx shadcn@latest add button
npx shadcn@latest add label
npx shadcn@latest add select
```

**Custom components to create:**
- `NumberInput` (см. выше)
- `FormField` wrapper (уже есть, но можно улучшить)

---

### Phase 2: P1 — Layout & Navigation (2-3 days)

```bash
npx shadcn@latest add card
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
npx shadcn@latest add tabs
```

---

### Phase 3: P2 — Feedback (1-2 days)

```bash
npx shadcn@latest add alert
npx shadcn@latest add badge
npx shadcn@latest add tooltip
npx shadcn@latest add progress
```

---

## 🎨 Design System Integration

### Map Existing Tokens to shadcn Variables

**File:** `frontend/src/styles/tokens.css` (add to :root)

```css
:root {
  /* shadcn/ui variables mapped to existing tokens */
  --primary: var(--color-blue-600);
  --primary-foreground: #fff;
  --secondary: var(--color-navy-100);
  --secondary-foreground: var(--color-navy-900);
  --background: var(--color-bg);
  --foreground: var(--color-text);
  --muted: var(--color-surface-muted);
  --muted-foreground: var(--color-text-muted);
  --accent: var(--color-accent);
  --accent-foreground: #fff;
  --destructive: var(--color-heart-500);
  --destructive-foreground: #fff;
  --border: var(--color-border);
  --input: var(--color-border);
  --ring: var(--color-focus);
  --radius: 0.5rem;
}
```

---

## 📋 Migration Checklist

### Forms (P0)

- [ ] Install shadcn/ui CLI
- [ ] Add Input, Button, Label components
- [ ] Create NumberInput with RU locale support
- [ ] Update `SetupForm.tsx` to use new components
- [ ] Test BMI form with `75,1` → `75.1` conversion
- [ ] Verify accessibility (keyboard, screen reader)

### Buttons (P0)

- [ ] Replace all `<button>` with `<Button>`
- [ ] Standardize button variants (primary, secondary, ghost)
- [ ] Add loading states where needed

### Select (P1)

- [ ] Add Select component
- [ ] Replace native `<select>` in SetupForm
- [ ] Add search/filter if needed

---

## 🚀 Quick Commands

### Setup shadcn/ui

```bash
cd frontend
npx shadcn@latest init
# Answer: New York, Navy, Yes (CSS vars)
```

### Add Components

```bash
# Phase 1 (P0)
npx shadcn@latest add input button label select

# Phase 2 (P1)
npx shadcn@latest add card dialog dropdown-menu tabs

# Phase 3 (P2)
npx shadcn@latest add alert badge tooltip progress
```

### Verify

```bash
cd frontend
npm run build  # Should pass
npm test       # Should pass
```

---

## 📝 Example: BMI Form with New Components

**Before:**
```tsx
<input
  type="number"
  {...register('weight_kg', { valueAsNumber: true })}
  className="w-full px-4 py-3 border..."
/>
```

**After:**
```tsx
import { NumberInput } from '@/components/ui/number-input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

<Label htmlFor="weight_kg">{t('nutrition.weight_kg')}</Label>
<NumberInput
  id="weight_kg"
  {...register('weight_kg', { valueAsNumber: true })}
  locale={getClientLocale() === 'ru' ? 'ru' : 'en'}
  placeholder="65"
/>
{errors.weight_kg && (
  <p className="text-sm text-destructive">{errors.weight_kg.message}</p>
)}

<Button type="submit" className="w-full">
  {t('nutrition.calculate')}
</Button>
```

---

## 🎯 Success Metrics

### Phase 1 (P0)
- ✅ BMI form accepts `75,1` and converts to `75.1`
- ✅ All forms use unified components
- ✅ No inline className for inputs/buttons
- ✅ Accessibility verified

### Phase 2 (P1)
- ✅ All buttons use `<Button>` component
- ✅ Modals use `<Dialog>` component
- ✅ Navigation is consistent

### Phase 3 (P2)
- ✅ Errors use `<Alert>` component
- ✅ Tooltips available where needed
- ✅ Loading states standardized

---

## 🔗 Next Steps After Components

1. **Storybook Setup** (optional, but recommended)
   ```bash
   npx storybook@latest init
   ```

2. **Component Documentation**
   - Add JSDoc comments
   - Create Storybook stories
   - Document design tokens

3. **Accessibility Audit**
   - Run axe-core tests
   - Verify keyboard navigation
   - Test with screen readers

---

**Last updated:** 2026-01-15
**Ready for implementation**

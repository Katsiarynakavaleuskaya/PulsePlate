# Frontend Fixes — PR Plan

**Date:** 2026-01-15
**Status:** Ready for implementation

---

## 🎯 Overview

Three sequential PRs to fix BMI form and modernize component system:

1. **PR-525** (P0): Fix BMI form — numeric parsing + height units + error display
2. **PR-526** (P1): Introduce shadcn components + RHF Controller pattern
3. **PR-527** (P2): Storybook setup (later)

---

## PR-525: Fix BMI UI (P0 — Critical)

**Priority:** P0 (Blocks launch)
**Time:** 1 day
**Scope:** Minimal fixes to make BMI form work

### Changes

1. **Number parsing with `setValueAs`**
   - Fix RU locale: `75,1` → `75.1`
   - Use RHF `setValueAs` (no custom components needed for P0)

2. **Height units — explicit "cm"**
   - Update labels: "Рост (см)" instead of "Рост (m)"
   - Ensure backend receives `height_cm` correctly

3. **Error display**
   - Replace "undefined" with proper error messages
   - Add validation feedback

### Files Changed

- `frontend/src/pages/NutritionSetup/SetupForm.tsx`
- `frontend/src/locales/ru.json` (and `en.json`, `es.json`)
- `frontend/src/pages/NutritionSetup/ResultView.tsx` (if BMI displayed separately)

### Full Patch

See: `PR_525_BMI_FIX_PATCH.md`

---

## PR-526: shadcn Components (P1 — After PR-525)

**Priority:** P1 (Enhancement)
**Time:** 2-3 days
**Scope:** Modern component system with proper RHF integration

### Changes

1. **Install shadcn/ui**
   - Add Input, Button, Label components
   - Map design tokens to shadcn CSS variables

2. **Create RHF-friendly NumberInput**
   - Use `Controller` pattern (not `register()`)
   - Proper locale parsing
   - Smooth typing experience

3. **Update forms to use new components**
   - Migrate SetupForm to Controller + NumberInput
   - Standardize button styles

### Files Changed

- `frontend/src/components/ui/input.tsx` (shadcn)
- `frontend/src/components/ui/button.tsx` (shadcn)
- `frontend/src/components/ui/label.tsx` (shadcn)
- `frontend/src/components/ui/number-input.tsx` (new, custom)
- `frontend/src/styles/tokens.css` (add shadcn variable mapping)
- `frontend/src/pages/NutritionSetup/SetupForm.tsx` (migrate to Controller)

### Full Patch

See: `PR_526_SHADCN_COMPONENTS_PATCH.md`

---

## PR-527: Storybook (P2 — Later)

**Priority:** P2 (Nice to have)
**Time:** 1-2 days
**Scope:** Component documentation and isolated development

### Changes

1. Setup Storybook
2. Create stories for key components
3. Document design tokens

**Note:** Only after 2-3 screens are stable and there's something to showcase.

---

## 🔄 Dependencies

```
PR-525 (P0) → PR-526 (P1) → PR-527 (P2)
```

**PR-525 must be merged first** (fixes critical bug).

**PR-526 can be done in parallel** with other frontend work, but should come after PR-525.

**PR-527 is optional** and can wait.

---

## ✅ Verification Checklist

### PR-525

- [ ] RU locale: `75,1` → `75.1` works
- [ ] Height label shows "cm" explicitly
- [ ] Invalid input shows error, not "undefined"
- [ ] Network request sends correct `height_cm` and `weight_kg`

### PR-526

- [ ] NumberInput works with Controller pattern
- [ ] Design tokens mapped correctly (Navy/Blue colors)
- [ ] Forms use new components consistently
- [ ] Accessibility verified (labels, keyboard nav)

---

## 📝 Commit Messages

### PR-525

```
fix(frontend): BMI form numeric parsing + height units + error display

- Fix RU locale number parsing (comma → dot) using setValueAs
- Explicitly label height as "cm" to prevent unit confusion
- Replace "undefined" with proper error messages
- Add input validation ranges (50-250 cm, 20-300 kg)

Fixes BMI calculation breaking on RU locale input (75,1 → NaN).
Fixes height unit confusion (label "m" but user enters cm).

P0 fix for BMI form usability.
```

### PR-526

```
feat(ui): introduce shadcn input/button/label + token mapping

- Add shadcn/ui Input, Button, Label components
- Create RHF-friendly NumberInput with Controller pattern
- Map PulsePlate design tokens to shadcn CSS variables
- Update SetupForm to use new components

P1 enhancement for consistent UI components.
Depends on PR-525 (BMI form fixes).
```

---

## 🚨 Important Notes

1. **PR-525 uses `setValueAs`** — simpler, no custom components needed for P0
2. **PR-526 uses `Controller`** — proper pattern for custom components
3. **Don't mix approaches** — PR-525 is quick fix, PR-526 is proper solution
4. **Test both RU and EN locales** — ensure comma parsing works

---

**Last updated:** 2026-01-15

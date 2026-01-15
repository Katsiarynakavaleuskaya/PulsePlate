# PR-525: Fix BMI UI — Locale Numbers + Height Units + Never Undefined

## What

Fixes critical BMI form bugs that cause "undefined" results on production:
- RU locale number parsing (`75,1` → `75.1`)
- Height unit confusion (label "m" but user enters cm)
- Error display (replace "undefined" with proper validation messages)

## Why

**P0 blocker:** BMI form is broken on production (`pulseplate.app`):
- Users entering `75,1` get `NaN` (comma not parsed)
- Height label says "m" but users enter "160" (thinking cm) → validation fails
- UI shows "undefined" instead of helpful error messages

**Impact:** Core functionality (BMI calculation) doesn't work for RU users.

## Changes

### 1. Number Parsing with `setValueAs`

**File:** `frontend/src/pages/NutritionSetup/SetupForm.tsx`

- Replace `type="number"` with `type="text"` + `inputMode="decimal"`
- Use RHF `setValueAs` to normalize locale (comma → dot)
- Add validation ranges (50-250 cm, 20-300 kg)

**Before:**
```typescript
<input
  type="number"
  {...register('weight_kg', { valueAsNumber: true })}
/>
```

**After:**
```typescript
<input
  type="text"
  inputMode="decimal"
  {...register('weight_kg', {
    setValueAs: (v) => {
      const s = String(v ?? "").trim().replace(/,/g, ".");
      const n = Number(s);
      return Number.isFinite(n) && n > 0 ? n : undefined;
    },
  })}
/>
```

### 2. Height Units — Explicit "cm"

**Files:** `frontend/src/locales/ru.json`, `en.json`, `es.json`

- Update labels: `"height_cm": "Рост (см)"` (explicitly cm)
- Ensure backend receives `height_cm` correctly

### 3. Error Display

**File:** `frontend/src/pages/NutritionSetup/ResultView.tsx` (or wherever BMI is displayed)

- Replace "undefined" with proper error messages
- Show validation errors from RHF
- Add i18n keys for error states

## Testing

### Manual Testing Checklist

- [ ] **RU locale parsing:**
  - Enter `75,1` in weight → should parse to `75.1`
  - Enter `170,5` in height → should parse to `170.5`
- [ ] **Height units:**
  - Label shows "Рост (см)" (explicitly cm)
  - Enter `160` → should send `height_cm: 160` to backend
- [ ] **Error display:**
  - Enter invalid data → should show error message, not "undefined"
  - Enter valid data → should show BMI result
- [ ] **Network check:**
  - Open DevTools → Network
  - Submit form
  - Verify request to `/api/v1/bmi/calculate` (or correct endpoint)
  - Verify payload: `{ height_cm: 170, weight_kg: 75.1, ... }` (numbers, not strings)

### Unit Tests

- [ ] Parser test: `"75,1" -> 75.1`
- [ ] Integration test: submit form → API call → render result

## Risks

**Low risk:**
- Uses RHF `setValueAs` (standard pattern, no custom components)
- No breaking changes to API contract
- Backward compatible (EN locale still works)

**Mitigation:**
- Test both RU and EN locales
- Verify network payload matches backend schema

## Related

- Depends on: PR-524 (weekly plan migration)
- Follow-up: PR-526 (shadcn components + Controller pattern)

## Reviewer Guide

**Focus areas:**
1. **Number parsing logic** — verify `setValueAs` handles edge cases (empty, NaN, negative)
2. **Locale handling** — ensure RU comma → dot conversion works
3. **Error states** — verify no "undefined" in UI
4. **API contract** — verify request payload format matches backend schema

**Quick verification:**
```bash
# Test RU locale parsing
cd frontend
npm test -- --grep "number.*parsing"
```

---

**Priority:** P0 (Critical)
**Estimated time:** 1 day
**Ready for review:** ✅

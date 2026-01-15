# PR-525: Fix BMI UI — Numeric Parsing + Height Units + No Undefined

**Priority:** P0 (Critical)
**Scope:** Frontend BMI form fixes
**Estimated time:** 1 day

---

## 🎯 Problem Statement

1. **RU locale parsing:** `75,1` → `NaN` (comma not converted to dot)
2. **Height units confusion:** Label says "m" but user enters "160" (thinking cm), backend expects `height_cm`
3. **Undefined display:** BMI shows "undefined" instead of error message

---

## 🔧 Solution

### Fix 1: Number Parsing with `setValueAs`

**Approach:** Use RHF `setValueAs` instead of custom NumberInput (avoids Controller complexity for P0).

**File:** `frontend/src/pages/NutritionSetup/SetupForm.tsx`

```typescript
// BEFORE
<input
  type="number"
  {...register('weight_kg', { valueAsNumber: true })}
  placeholder="65"
  className="..."
/>

// AFTER
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
  placeholder="65"
  className="..."
/>
```

**Same for `height_cm` and `age`.**

---

### Fix 2: Height Label — Explicitly "cm"

**File:** `frontend/src/locales/ru.json` (and `en.json`, `es.json`)

```json
{
  "nutrition": {
    "height_cm": "Рост (см)",
    "weight_kg": "Вес (кг)",
    "age": "Возраст (лет)"
  }
}
```

**File:** `frontend/src/pages/NutritionSetup/SetupForm.tsx`

```typescript
// Ensure label explicitly shows units
<label className="block text-sm font-medium text-text">
  {t('nutrition.height_cm')} {/* Will show "Рост (см)" */}
</label>
```

---

### Fix 3: Error Display Instead of "undefined"

**File:** `frontend/src/pages/NutritionSetup/ResultView.tsx` (or wherever BMI is displayed)

```typescript
// BEFORE
<div>BMI: {bmi ?? "undefined"}</div>

// AFTER
{bmi != null && Number.isFinite(bmi) ? (
  <div>BMI: {bmi.toFixed(1)}</div>
) : (
  <div className="text-red-600 text-sm">
    {t('nutrition.bmi.error')} {/* "Введите рост и вес корректно" */}
  </div>
)}
```

**Add to locales:**
```json
{
  "nutrition": {
    "bmi": {
      "error": "Введите рост (см) и вес (кг) корректно"
    }
  }
}
```

---

## 📋 Complete Patch

### 1. Update SetupForm.tsx

```typescript
// frontend/src/pages/NutritionSetup/SetupForm.tsx

// ... existing imports ...

export default function SetupForm({ onSubmit }: SetupFormProps) {
  // ... existing code ...

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      {/* ... existing header ... */}

      <form onSubmit={handleSubmit(submit)} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Age */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">
              {t('nutrition.age')}
            </label>
            <input
              type="text"
              inputMode="numeric"
              {...register('age', {
                setValueAs: (v) => {
                  const s = String(v ?? "").trim().replace(/,/g, ".");
                  const n = Number(s);
                  return Number.isFinite(n) && n > 0 && n <= 120 ? n : undefined;
                },
              })}
              placeholder="30"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.age && <p className="text-sm text-red-600">{errors.age.message}</p>}
          </div>

          {/* Height (cm) - EXPLICIT */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">
              {t('nutrition.height_cm')}
            </label>
            <input
              type="text"
              inputMode="decimal"
              {...register('height_cm', {
                setValueAs: (v) => {
                  const s = String(v ?? "").trim().replace(/,/g, ".");
                  const n = Number(s);
                  // Validate: 50-250 cm (reasonable human height range)
                  return Number.isFinite(n) && n >= 50 && n <= 250 ? n : undefined;
                },
              })}
              placeholder="170"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.height_cm && <p className="text-sm text-red-600">{errors.height_cm.message}</p>}
          </div>

          {/* Weight (kg) */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">
              {t('nutrition.weight_kg')}
            </label>
            <input
              type="text"
              inputMode="decimal"
              {...register('weight_kg', {
                setValueAs: (v) => {
                  const s = String(v ?? "").trim().replace(/,/g, ".");
                  const n = Number(s);
                  // Validate: 20-300 kg (reasonable human weight range)
                  return Number.isFinite(n) && n >= 20 && n <= 300 ? n : undefined;
                },
              })}
              placeholder="65"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.weight_kg && <p className="text-sm text-red-600">{errors.weight_kg.message}</p>}
          </div>
        </div>

        {/* ... rest of form ... */}
      </form>
    </div>
  );
}
```

---

### 2. Update Locales

**File:** `frontend/src/locales/ru.json`

```json
{
  "nutrition": {
    "age": "Возраст (лет)",
    "height_cm": "Рост (см)",
    "weight_kg": "Вес (кг)",
    "bmi": {
      "error": "Введите рост (см) и вес (кг) корректно",
      "invalid": "Некорректные данные для расчета BMI"
    }
  }
}
```

**File:** `frontend/src/locales/en.json`

```json
{
  "nutrition": {
    "age": "Age (years)",
    "height_cm": "Height (cm)",
    "weight_kg": "Weight (kg)",
    "bmi": {
      "error": "Please enter valid height (cm) and weight (kg)",
      "invalid": "Invalid data for BMI calculation"
    }
  }
}
```

**File:** `frontend/src/locales/es.json`

```json
{
  "nutrition": {
    "age": "Edad (años)",
    "height_cm": "Altura (cm)",
    "weight_kg": "Peso (kg)",
    "bmi": {
      "error": "Por favor ingrese altura (cm) y peso (kg) válidos",
      "invalid": "Datos inválidos para el cálculo de IMC"
    }
  }
}
```

---

### 3. Update Result Display (if BMI is shown separately)

**File:** `frontend/src/pages/NutritionSetup/ResultView.tsx` (or wherever BMI is displayed)

```typescript
// If BMI is calculated/displayed separately
const displayBMI = (bmi: number | null | undefined) => {
  if (bmi == null || !Number.isFinite(bmi)) {
    return (
      <div className="text-red-600 text-sm" role="alert">
        {t('nutrition.bmi.error')}
      </div>
    );
  }
  return <div>BMI: {bmi.toFixed(1)}</div>;
};
```

---

## ✅ Verification Steps

1. **RU locale parsing:**
   - Enter `75,1` in weight → should parse to `75.1`
   - Enter `170,5` in height → should parse to `170.5`

2. **Height units:**
   - Label shows "Рост (см)" (explicitly cm)
   - Enter `160` → should send `height_cm: 160` to backend
   - Enter `1.60` → should send `height_cm: 1.60` (but warn user this is too small)

3. **Error display:**
   - Enter invalid data → should show error message, not "undefined"
   - Enter valid data → should show BMI result

4. **Network check:**
   - Open DevTools → Network
   - Submit form
   - Verify request to `/api/v1/bmi/calculate` (or correct endpoint)
   - Verify payload: `{ height_cm: 170, weight_kg: 75.1, ... }`

---

## 🚨 Important Notes

1. **No custom NumberInput for P0:** Using `setValueAs` is simpler and avoids RHF integration issues.

2. **Type safety:** `setValueAs` returns `number | undefined`, which Zod schema should handle.

3. **Validation:** Added reasonable ranges (50-250 cm, 20-300 kg) to prevent obvious errors.

4. **Future:** PR-526 will add proper NumberInput with Controller for better UX (visual feedback, step controls).

---

## 📝 Commit Message

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

---

**Last updated:** 2026-01-15

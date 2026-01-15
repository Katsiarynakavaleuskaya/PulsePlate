# PR-525: Ready Checklist

**Priority:** P0-A1 (Critical — First PR that makes product "alive")

---

## ✅ Must-Have Criteria (Minimum)

### 1. Number Parsing with `setValueAs`

- [ ] `weight_kg` field uses `setValueAs` for locale parsing
- [ ] `height_cm` field uses `setValueAs` for locale parsing
- [ ] `age` field (if present) uses `setValueAs` for locale parsing
- [ ] `75,1` → `75.1` (RU comma converted to dot)
- [ ] Invalid input (NaN, negative, empty) → `undefined` → validation error

**Verification:**
```typescript
// Test cases:
"75,1" → 75.1 ✅
"75.1" → 75.1 ✅
"abc" → undefined → error ✅
"" → undefined → error ✅
"-5" → undefined → error ✅
```

---

### 2. Clear Units in UI

- [ ] Height label explicitly says "Рост (см)" (not "m")
- [ ] Placeholder shows example: `170` (cm)
- [ ] Backend receives `height_cm` correctly

**Verification:**
- Label text: "Рост (см)" or "Height (cm)"
- Placeholder: `170` (not `1.70`)
- Network request: `{ height_cm: 170, ... }` (number, not string)

---

### 3. Error Display (No "undefined")

- [ ] If form invalid → show validation error message (not "undefined")
- [ ] If API error → show error message (not "undefined")
- [ ] If no data → show "Enter data and click Calculate" (not "undefined")
- [ ] If BMI calculated → show result (not "undefined")

**Verification:**
- Invalid form → Error message under field ✅
- API 422 → Error message displayed ✅
- API 200 with data → BMI result displayed ✅
- Empty state → "Enter data..." message ✅

---

## 🔍 Diagnostic Checklist (When Testing)

### Network Request Check

1. **Open DevTools → Network tab**
2. **Submit BMI form**
3. **Check request:**
   - URL: `/api/v1/bmi/calculate` (or correct endpoint)
   - Method: `POST`
   - Payload: `{ height_cm: 170, weight_kg: 75.1, ... }` (numbers, not strings)

### Response Check

1. **Check response status:**
   - **422** → Form sends wrong data → Fix parsing/fields
   - **200, but BMI null/undefined** → Render/field mapping broken
   - **403** → API key/gate issue (not BMI math)
   - **500** → Server error (check logs)

2. **Check response body:**
   - First fields: `{ bmi: 26.5, category: "overweight", ... }`
   - If `bmi: null` or missing → Backend issue
   - If `bmi: 26.5` but UI shows "undefined" → Frontend render issue

---

## 📋 Pre-Merge Checklist

- [ ] All must-have criteria met
- [ ] Manual testing: RU locale (`75,1` works)
- [ ] Manual testing: EN locale (`75.1` works)
- [ ] Manual testing: Invalid input shows error (not "undefined")
- [ ] Network check: Request payload is correct (numbers, not strings)
- [ ] Network check: Response is correctly rendered
- [ ] No "undefined" in UI (anywhere)
- [ ] Unit tests pass (if added)
- [ ] Integration test: Submit form → API call → Render result

---

## 🎯 Success Criteria

**PR-525 is ready when:**
1. ✅ User can enter `75,1` in weight → it works
2. ✅ User can enter `160` in height (cm) → it works
3. ✅ BMI result is displayed (not "undefined")
4. ✅ Invalid input shows error message (not "undefined")
5. ✅ Network request has correct payload format

**This is the first PR that makes the product "alive" — it must work perfectly.**

---

**Last updated:** 2026-01-15

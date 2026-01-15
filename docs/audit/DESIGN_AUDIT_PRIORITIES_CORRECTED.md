# Design Audit — Corrected Priorities & Realistic Assessment

**Date:** 2026-01-15
**Status:** Corrected priorities based on functional readiness
**Key Insight:** Brand/Design implementation ≠ Product readiness

---

## 🎯 Core Principle

**Brand/Design implementation ≠ readiness.**

Real readiness for public launch is determined by:
- ✅ BMI calculates correctly
- ✅ Forms validate properly
- ✅ API contracts match
- ✅ Onboarding explains value
- ✅ App Store assets exist

**Not by:**
- ❌ Brand slogan visibility
- ❌ ECG visual elements
- ❌ Typography strategy
- ❌ Animation polish

---

## 📊 Realistic Assessment

### Previous Assessment: 62% Implemented ❌

**Problem:** Overestimated based on visual/brand foundation, ignored functional gaps.

### Corrected Assessment: **40% Product Ready** ✅

**Breakdown:**
- **Visual Foundation:** 70% (colors, tokens, basic components)
- **Functional Core:** 30% (BMI broken, forms need fixes, API contracts need verification)
- **Brand Elements:** 50% (FitChef iOS only, no slogan, no ECG)
- **App Store Readiness:** 20% (no screenshots, no video)

**Overall:** Foundation is solid, but **product layer is broken** (BMI undefined = P0 blocker).

---

## 🔴 Corrected P0 Priorities

### P0-A: "Product Works" (Functional)

1. **BMI Form Fix** (P0-A1)
   - ✅ Locale parsing: `75,1` → `75.1`
   - ✅ Height units: explicit "cm", label "Height (cm)"
   - ✅ Error handling: no "undefined", show proper errors
   - ✅ API contract: verify `/api/v1/bmi/calculate` call and response mapping

2. **API Contract Sanity** (P0-A2)
   - ✅ Frontend calls correct endpoint
   - ✅ Request payload matches backend schema
   - ✅ Response mapping to UI fields is correct
   - ✅ Error states handled (422, 500, network errors)

3. **Language Switch** (P0-A3)
   - ✅ Number format changes with locale (RU: comma, EN: dot)
   - ✅ All UI text translates correctly

### P0-B: "Can Publish to Store" (Launch Blockers)

4. **App Store Screenshots** (P0-B1)
   - ✅ 5 key screenshots (6.7″, 6.1″)
   - ✅ Templates for future updates
   - **Blocking:** Cannot publish without screenshots

5. **Basic Onboarding** (P0-B2)
   - ✅ At least 2 screens: value proposition + "how to use"
   - ✅ Explains what app does
   - **Blocking:** Users won't understand value without onboarding

---

## ⚠️ P1: "Brand Magic" (Post-Launch Enhancement)

6. **Brand Slogan** (P1)
   - "Держим руку на пульсе" / "Always on your Pulse"
   - Add to onboarding, splash screen, App Store description
   - **Not blocking:** Nice to have, but not required for launch

7. **ECG / Pulse Visuals** (P1)
   - Red ECG line in logo/icon variants
   - Pulsing animations
   - **Not blocking:** Brand enhancement, not functional requirement

8. **FitChef on Web** (P1)
   - Add FitChef component to frontend
   - Use in onboarding, empty states
   - **Not blocking:** iOS has it, web can wait

9. **Tone of Voice** (P1)
   - Rewrite UI copy with brand personality
   - **Not blocking:** Current copy works, can be improved later

10. **Animations** (P1)
    - Smooth transitions, pulse effects
    - **Not blocking:** Functional first, polish later

---

## 📋 PR Plan (Sequential, Controlled)

### PR-525 (Frontend): `fix(bmi-ui): locale numbers + height units + never undefined`

**Priority:** P0-A1 (Critical)
**Goal:** "BMI undefined" screen disappears forever
**Time:** 1 day

**Scope (minimal, but ironclad):**
- Weight: accept `75,1` and `75.1`
- Height: make it **cm**, label "Height (cm)", payload `height_cm`
- Age: number parsing
- Validation: show error under field, not "undefined"
- Result: if no data → show state ("Enter data and click Calculate")

**Tests (minimum):**
- Unit test parser: `"75,1" -> 75.1`
- Integration test: submit form → API call → render result

**Important:** If using custom `NumberInput`, use RHF `Controller` pattern (see `PR_525_BMI_FIX_PATCH.md`).

---

### PR-526 (Frontend): `feat(ui): shadcn input/button/label + token mapping`

**Priority:** P1 (After PR-525)
**Goal:** Visual consistency, but **not mixed with bugfix**
**Time:** 2-3 days

**Scope:**
- `shadcn init`
- `input/button/label/select` components
- Map CSS vars to `tokens.css`
- Replace inline `<input>` / `<button>` with components

**Note:** Separate PR to avoid mixing bugfix with enhancement.

---

### PR-527 (Web Brand): `feat(brand): slogan + FitChef asset + empty states`

**Priority:** P1 (Post-launch)
**Goal:** Brand elements on web
**Time:** 2-3 days

**Scope:**
- Slogan in 1-2 places (header / onboarding screen)
- FitChef on web (at least static image + 1 empty state)
- **No ECG wave yet** (P2)

---

### PR-528 (iOS/Web): `docs(assets): app store screenshot kit`

**Priority:** P0-B1 (Launch blocker)
**Goal:** App Store assets ready
**Time:** 2-3 days

**Scope:**
- Templates + checklist + screen list
- Process for 6.7″ / 6.1″ screenshots
- Documentation for future updates

---

## 🔍 What We Need to Diagnose "BMI undefined"

To say exactly why BMI is undefined (without guessing), need 2 things from DevTools (Network):

1. **Request to BMI:**
   - URL
   - Payload (JSON)

2. **Response:**
   - Status code
   - Body (first few fields)

After this, can say exactly where the break is:
- Units/locale on client
- Contract and mapping
- Backend schema mismatch
- UI rendering wrong field

---

## 📊 Corrected Scorecard

| Category | Previous | Corrected | Reason |
|----------|----------|-----------|--------|
| **Color Palette** | 100% | 100% | ✅ Complete |
| **Typography** | 70% | 70% | ⚠️ Good (P2, not P0) |
| **Spacing & Layout** | 90% | 90% | ✅ Good |
| **Apple HIG** | 85% | 85% | ✅ Good |
| **Accessibility** | 80% | 80% | ✅ Good |
| **App Store Assets** | 40% | 20% | 🔴 Critical gap |
| **Onboarding** | 30% | 20% | 🔴 Critical gap |
| **Premium Conversion** | 85% | 85% | ✅ Good |
| **Data Visualization** | 75% | 60% | ⚠️ Needs API connection |
| **i18n** | 95% | 90% | ✅ Good (number format needs fix) |
| **Component System** | 50% | 40% | ⚠️ Needs modernization |
| **Animation System** | 40% | 30% | 🔴 Incomplete (P1) |
| **Brand Voice** | 20% | 20% | 🔴 Missing (P1) |
| **Functional Core** | N/A | 30% | 🔴 **BMI broken = P0** |

**Overall: 40% Product Ready** (down from 62% "implemented")

---

## 🎯 Success Criteria (Corrected)

### Minimum Viable Launch (P0)

- [ ] BMI form works with RU locale (`75,1` → `75.1`)
- [ ] Height units explicit (cm), no confusion
- [ ] No "undefined" in UI (proper error states)
- [ ] API contract verified (request/response match)
- [ ] App Store screenshots ready (5 key screens)
- [ ] Basic onboarding (2 screens: value + how to use)

### Post-Launch Enhancement (P1)

- [ ] Brand slogan visible
- [ ] FitChef on web
- [ ] ECG/pulse visuals
- [ ] Tone of voice updated
- [ ] Animations polished

---

## 📝 Key Corrections to Previous Audit

### 1. "60% Implemented" → "40% Product Ready"

**Reason:** Visual foundation ≠ functional readiness. BMI undefined = P0 blocker.

### 2. Typography Gap → P2 (Not P0)

**Reason:** SF Pro (iOS) + Inter (Web) is fine. "Luxury typography strategy" is P2 enhancement.

### 3. ECG/Pulse → P1 (Not P0)

**Reason:** Great brand feature, but if BMI doesn't work, it's not P0. It's "brand enhancement."

### 4. Brand Slogan → P1 (Not P0)

**Reason:** Important for brand, but not blocking launch. Functional fixes come first.

---

## 🚨 Current Status

**Waiting for:** PR-524 (weekly plan migration) to be green and approved.

**Next:** PR-525 (BMI form fix) — P0-A1, critical.

**After PR-525:** PR-526 (shadcn components) — P1, enhancement.

---

## 📚 Related Documents

- `PR_525_BMI_FIX_PATCH.md` — BMI form fix (P0)
- `PR_526_SHADCN_COMPONENTS_PATCH.md` — Component system (P1)
- `PR_PLAN_FRONTEND_FIXES.md` — Full PR plan
- `DESIGN_CONCEPT_IMPLEMENTATION_AUDIT.md` — Original audit (needs priority correction)

---

**Last updated:** 2026-01-15
**Status:** Priorities corrected, waiting for PR-524

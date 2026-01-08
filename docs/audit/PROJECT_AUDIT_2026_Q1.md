# Project Audit: Q1 2026 — Detailed Analysis & Recommendations

## Executive Summary

**Status:** Backend BMI features complete, clients need integration.  
**Recommendation:** Sprint B (BMI contract docs) → Sprint C (i18n + iOS) → Sprint D (PRO/VIP UI).

**Rationale:** Document contract first, then bootstrap clients, then integrate existing PRO/VIP endpoints.

**PR-492 Decision:** ❌ **SKIP** — Security alert #495 resolved, Docker verification not needed.

---

## 1. PR-492 Decision: Skip Docker Verification

### Current State

- ✅ Security alert #495 **resolved** (disappeared after PR-487 merge)
- ✅ `requirements-dev.txt` contains `urllib3==2.6.3`
- ✅ PR-487 merged successfully
- ✅ No active security alerts

### Analysis

**Code Evidence:**
```bash
# requirements-dev.txt
urllib3==2.6.3  # ✅ Updated

# Git history
f63037fc Merge pull request #487 from .../dependabot/pip/urllib3-2.6.3
```

**Conclusion:** Docker image verification PR-492 is **not needed** because:
1. Security alert resolved = actual environment updated
2. No evidence of version mismatch
3. Adding verification now = "checking what's already confirmed"

### Recommendation

**Skip PR-492** (Docker verification). If you want future protection:
- Add minimal CI guard (1-line check) in a later cleanup PR
- Don't create a full PR just for verification of already-confirmed state

---

## 2. Sprint B: BMI Contract Polish + Docs — **HIGH PRIORITY**

### Current State Analysis

#### ✅ What Exists

1. **Backend Implementation:**
   - `app/schemas/bmi.py`: `BMICalculateResponse` with `visualization: BMIScaleV1Spec | None`
   - `app/services/bmi_visualization.py`: `build_bmi_scale_v1()` with group-aware ranges
   - `app/routers/bmi.py`: Endpoint returns visualization spec
   - `core/bmi/engine.py`: `get_bmi_visual_ranges()` for group-specific thresholds

2. **Tests:**
   - `tests/test_bmi_visualization_spec.py`: Spec builder tests, group-aware tests
   - `tests/test_bmi_calculate_endpoint.py`: Endpoint integration tests
   - `tests/test_bmi_schemas.py`: Schema structure tests (minimal)

#### ❌ What's Missing

1. **Documentation:**
   - ❌ No `docs/bmi/visualization.md` or similar
   - ❌ No JSON examples for different groups
   - ❌ No explanation of `visualization: null` cases
   - ❌ No fallback behavior documentation

2. **Contract Tests:**
   - ❌ No JSON schema validation tests
   - ❌ No contract tests verifying response structure across groups
   - ❌ No tests ensuring visualization ranges match core thresholds (parity exists, but not as "contract")

### Code Evidence

**Current Schema (app/schemas/bmi.py):**
```python
class BMICalculateResponse(BaseModel):
    bmi: float
    category: str | None
    group: str
    # ... other fields ...
    visualization: BMIScaleV1Spec | None = None  # ✅ Exists
```

**Current Tests:**
- `test_bmi_visualization_spec.py`: Tests builder logic ✅
- `test_bmi_schemas.py`: Tests minimal response structure ✅
- **Missing:** Contract tests for visualization field structure ❌

### Recommendation: **DO Sprint B**

**Why:**
1. **iOS/Web need documented contract** to implement visualization
2. **Contract tests prevent regressions** when backend changes
3. **Examples speed up client development** (copy-paste ready JSON)
4. **Low risk, high value** (docs + tests, no production changes)

**Scope:**
- `docs/bmi/visualization.md` — contract documentation
- `tests/test_bmi_contract.py` — JSON schema + structure validation
- Examples for adult/athlete/elderly/child groups

**Time Estimate:** 2-3 hours

---

## 3. Sprint C: i18n + iOS Bootstrap — **MEDIUM-HIGH PRIORITY**

### Current State Analysis

#### i18n: What Exists

**Backend:**
- `core/meal_i18n.py`: Language enum and translation functions
- `app/routers/bmi.py`: Uses `lang` parameter, returns localized strings
- `app/routers/plan_export.py`: Has `SLOGAN` dict with RU/EN/DE

**iOS:**
- `ios/PulsePlate/en.lproj/Localizable.strings` — exists
- `ios/PulsePlate/ru.lproj/Localizable.strings` — exists
- `ios/PulsePlate/es.lproj/Localizable.strings` — exists
- `ios/PulsePlate/Models/LocalizationManager.swift` — exists

**Code Evidence:**
```swift
// ios/PulsePlate/Models/LocalizationManager.swift exists
// ios/PulsePlate/*.lproj/Localizable.strings exist
```

#### i18n: What's Missing

1. **Centralized Key Registry:**
   - ❌ No single source of truth for all i18n keys
   - ❌ No validation that all keys exist in all languages
   - ❌ No contract tests for i18n completeness

2. **BMI Visualization Keys:**
   - ❌ No `bmi.underweight`, `bmi.normal`, `bmi.overweight`, `bmi.obesity` in iOS strings
   - ❌ No documented i18n key structure

#### iOS: What Exists

**Structure:**
- ✅ `ios/PulsePlate/Services/` — API services exist (ShoppingListService, WeeklyPlanService)
- ✅ `ios/PulsePlate/Models/` — Models exist (NutritionData, ShoppingList, WeeklyPlan)
- ✅ `ios/PulsePlate/ViewModels/` — ViewModels exist
- ✅ `ios/PulsePlate/Views/` — Views exist (32 files)
- ✅ `ios/PulsePlate/Screens/` — Screens exist (ShoppingListReaderScreen)

**API Client:**
- ✅ `AppConfig.swift` — base URL configuration
- ✅ `ShoppingListService.swift` — example API client pattern
- ✅ `WeeklyPlanService.swift` — example API client pattern

#### iOS: What's Missing for BMI

1. **BMI Models:**
   - ❌ No `BMICalculateRequest.swift`
   - ❌ No `BMICalculateResponse.swift`
   - ❌ No `BMIScaleV1Spec.swift`

2. **BMI Service:**
   - ❌ No `BMIService.swift` (API client for `/api/v1/bmi/calculate`)

3. **BMI Screen:**
   - ❌ No `BMICalculateScreen.swift`
   - ❌ No BMI visualization component

4. **BMI i18n:**
   - ❌ No BMI keys in `Localizable.strings`

### Code Evidence

**iOS Service Pattern (exists):**
```swift
// ios/PulsePlate/Services/ShoppingListService.swift
public func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO
// ✅ Pattern exists, can replicate for BMI
```

**iOS Model Pattern (exists):**
```swift
// ios/PulsePlate/Models/NutritionData.swift
struct NutritionData: Codable { ... }
// ✅ Pattern exists, can replicate for BMI
```

**Missing:**
- No BMI-specific files in `ios/PulsePlate/Models/`
- No BMI-specific files in `ios/PulsePlate/Services/`
- No BMI-specific files in `ios/PulsePlate/Screens/`

### Recommendation: **DO Sprint C**

**Why:**
1. **i18n audit needed** — prevent missing translations
2. **iOS structure exists** — just need BMI models/service/screen
3. **Patterns established** — can replicate ShoppingList/WeeklyPlan patterns
4. **Foundation for Sprint D** — need iOS client before PRO/VIP integration

**Scope:**
- **C.1 (i18n):** Audit + centralize keys, add BMI keys, contract tests
- **C.2 (iOS):** BMI models, service, screen, visualization component

**Time Estimate:** 4-6 hours total

---

## 4. Sprint D: PRO/VIP UI Integration — **MEDIUM PRIORITY**

### Current State Analysis

#### PRO Endpoints (Backend)

**Found:**
- `app/routers/pro.py`: `/api/v1/pro/meal/weekly`, `/api/v1/pro/nutrition/targets`, `/api/v1/pro/nutrition/daily`
- `app/routers/bmi_pro.py`: `/api/v1/bmi/pro` (BMI Pro analysis)
- `app/routers/nutrition_log.py`: `/api/v1/nutrition-log/meal-log`, `/api/v1/nutrition-log/day-close`
- `app/routers/shopping_list_pro.py`: `/api/v1/shopping-list/pro`

**Code Evidence:**
```python
# app/routers/pro.py
router = APIRouter(prefix="/api/v1/pro", tags=["pro"])
@router.post("/meal/weekly", dependencies=[Depends(require_pro_tier)])

# app/routers/bmi_pro.py
@router.post("/pro", response_model=BMIProResponse)

# app/routers/nutrition_log.py
@router.post("/meal-log", summary="Log meal event (PRO)")
```

#### VIP Endpoints (Backend)

**Found:**
- `app/routers/vip.py`: `/api/v1/vip/*` (multiple VIP endpoints)
- `app/routers/vip_shoplist.py`: `/api/v1/vip/shoplist/*` (VIP shoplist)
- `app/routers/vip_registration.py`: Centralized VIP route registration

**Code Evidence:**
```python
# app/routers/vip.py
router = APIRouter(prefix="/api/v1/vip", tags=["vip"])
# Multiple VIP endpoints exist

# app/routers/vip_shoplist.py
router = APIRouter(prefix="/shoplist", tags=["VIP Shoplist"])
```

#### iOS: PRO/VIP Integration Status

**What Exists:**
- ✅ `ios/PulsePlate/Services/ProKeyProvider.swift` — PRO key management
- ✅ `ios/PulsePlate/Models/StoreKitManager.swift` — StoreKit integration
- ✅ Shopping list and weekly plan services (can check PRO/VIP)

**What's Missing:**
- ❌ No PRO/VIP UI screens (except shopping list/weekly plan)
- ❌ No BMI Pro screen
- ❌ No nutrition log screen
- ❌ No VIP-specific UI

### Recommendation: **DO Sprint D (after C)**

**Why:**
1. **Backend ready** — PRO/VIP endpoints exist and tested
2. **iOS foundation needed first** — need basic BMI client before PRO features
3. **Incremental approach** — add PRO/VIP features one by one
4. **High value** — monetization features

**Scope:**
- Connect existing PRO endpoints to iOS/web UI
- Add subscription checks
- Create PRO/VIP screens

**Time Estimate:** 6-8 hours

---

## 5. Detailed Recommendations with Code Evidence

### Recommendation 1: Sprint B First (BMI Contract Docs)

**Priority:** HIGH  
**Risk:** LOW  
**Value:** HIGH

**Why:**
- iOS/Web developers need documented contract
- Contract tests prevent regressions
- Examples speed development

**Evidence:**
```python
# Current: visualization exists but undocumented
class BMICalculateResponse(BaseModel):
    visualization: BMIScaleV1Spec | None = None  # ✅ Exists

# Missing: docs explaining what this means
# Missing: JSON examples for different groups
# Missing: contract tests
```

**Action Items:**
1. Create `docs/bmi/visualization.md` with:
   - What `visualization` field means
   - JSON examples for adult/athlete/elderly
   - `visualization: null` explanation
   - Fallback behavior

2. Create `tests/test_bmi_contract.py` with:
   - JSON schema validation
   - Response structure validation
   - Group-specific range validation

**Time:** 2-3 hours

---

### Recommendation 2: Sprint C.1 (i18n Audit)

**Priority:** MEDIUM-HIGH  
**Risk:** LOW  
**Value:** MEDIUM-HIGH

**Why:**
- Prevent missing translations
- Centralize key management
- Enable client development

**Evidence:**
```swift
// iOS has localization files but no centralized registry
ios/PulsePlate/en.lproj/Localizable.strings  // ✅ Exists
ios/PulsePlate/ru.lproj/Localizable.strings  // ✅ Exists
ios/PulsePlate/es.lproj/Localizable.strings  // ✅ Exists

// Missing: centralized key registry
// Missing: validation that all keys exist
// Missing: BMI visualization keys
```

**Action Items:**
1. Create `core/i18n/keys.py` (or similar) with:
   - All i18n keys as constants
   - Key structure documentation

2. Add BMI keys to iOS `Localizable.strings`:
   ```
   "bmi.underweight" = "Underweight";
   "bmi.normal" = "Normal";
   "bmi.overweight" = "Overweight";
   "bmi.obesity" = "Obesity";
   ```

3. Add contract tests:
   - All keys exist in all languages
   - No missing translations

**Time:** 2-3 hours

---

### Recommendation 3: Sprint C.2 (iOS BMI Bootstrap)

**Priority:** HIGH  
**Risk:** LOW  
**Value:** HIGH

**Why:**
- iOS structure exists, just need BMI-specific files
- Patterns established (ShoppingList, WeeklyPlan)
- Foundation for PRO/VIP integration

**Evidence:**
```swift
// Pattern exists:
ios/PulsePlate/Services/ShoppingListService.swift  // ✅
ios/PulsePlate/Models/ShoppingList/  // ✅
ios/PulsePlate/Screens/ShoppingListReaderScreen.swift  // ✅

// Missing for BMI:
ios/PulsePlate/Services/BMIService.swift  // ❌
ios/PulsePlate/Models/BMICalculateRequest.swift  // ❌
ios/PulsePlate/Models/BMICalculateResponse.swift  // ❌
ios/PulsePlate/Screens/BMICalculateScreen.swift  // ❌
```

**Action Items:**
1. Create BMI models (matching backend schemas):
   - `BMICalculateRequest.swift`
   - `BMICalculateResponse.swift`
   - `BMIScaleV1Spec.swift`

2. Create `BMIService.swift`:
   - API client for `/api/v1/bmi/calculate`
   - Error handling
   - Follow ShoppingListService pattern

3. Create `BMICalculateScreen.swift`:
   - Basic UI
   - Form inputs
   - Result display

4. Create BMI visualization component:
   - SVG rendering (or SwiftUI equivalent)
   - Use i18n keys from spec

**Time:** 3-4 hours

---

### Recommendation 4: Sprint D (PRO/VIP Integration)

**Priority:** MEDIUM  
**Risk:** LOW  
**Value:** HIGH (monetization)

**Why:**
- Backend endpoints ready
- iOS foundation needed first (Sprint C)
- Incremental approach

**Evidence:**
```python
# Backend ready:
app/routers/pro.py  # ✅ Multiple PRO endpoints
app/routers/vip.py  # ✅ Multiple VIP endpoints
app/routers/bmi_pro.py  # ✅ BMI Pro endpoint

# iOS needs:
ios/PulsePlate/Services/ProKeyProvider.swift  # ✅ Exists
# Missing: PRO/VIP UI screens
# Missing: Subscription flow integration
```

**Action Items:**
1. Audit existing PRO/VIP endpoints
2. Create PRO/VIP UI screens
3. Integrate subscription checks
4. Connect to backend endpoints

**Time:** 6-8 hours

---

## 6. Final Recommendation: Execution Order

### Option 1: Recommended (Sequential)

1. **Sprint B** (2-3h) — BMI contract docs
   - Documents contract for clients
   - Contract tests prevent regressions
   - Examples speed development

2. **Sprint C.1** (2-3h) — i18n audit
   - Centralize keys
   - Add BMI keys
   - Validation tests

3. **Sprint C.2** (3-4h) — iOS BMI bootstrap
   - Models, service, screen
   - Visualization component
   - Uses documented contract

4. **Sprint D** (6-8h) — PRO/VIP integration
   - Connect existing endpoints
   - Subscription flows
   - Monetization features

**Total:** 13-18 hours

### Option 2: Parallel (Faster)

1. **Sprint B** (2-3h) + **Sprint C.1** (2-3h) — parallel
2. **Sprint C.2** (3-4h)
3. **Sprint D** (6-8h)

**Total:** 11-16 hours

---

## 7. Code Evidence Summary

### What's Ready

- ✅ Backend BMI visualization (PR-490B merged)
- ✅ Backend PRO/VIP endpoints exist
- ✅ iOS structure exists (services, models, screens)
- ✅ iOS localization files exist

### What's Missing

- ❌ BMI visualization documentation
- ❌ BMI contract tests
- ❌ Centralized i18n key registry
- ❌ BMI i18n keys in iOS
- ❌ iOS BMI models/service/screen
- ❌ PRO/VIP UI integration

---

## 8. Decision Matrix

| Sprint | Priority | Risk | Value | Dependencies | Time |
|--------|----------|------|-------|--------------|------|
| B (Docs) | HIGH | LOW | HIGH | None | 2-3h |
| C.1 (i18n) | MEDIUM-HIGH | LOW | MEDIUM-HIGH | None | 2-3h |
| C.2 (iOS) | HIGH | LOW | HIGH | B, C.1 | 3-4h |
| D (PRO/VIP) | MEDIUM | LOW | HIGH | C.2 | 6-8h |

**Recommended Order:** B → C.1 → C.2 → D

---

## 9. Next Steps

1. **Start Sprint B** — Create BMI visualization documentation
2. **In parallel:** Start Sprint C.1 — i18n audit
3. **After B+C.1:** Start Sprint C.2 — iOS BMI bootstrap
4. **After C.2:** Start Sprint D — PRO/VIP integration

**Skip:** PR-492 (Docker verification) — not needed, security alert resolved.

